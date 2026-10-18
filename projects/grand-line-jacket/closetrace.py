"""Rev D: cloud banks TRACED from Devin's close-ups (LESSONS A12), not generated.
1. Placement: per-piece affine close-up px -> garment mm (size M), fitted on the horizon line, the bank tops/bottoms and the
   side banks of the mockup (the mockup wins on placement; the close-up gives shape, tones and stitch direction).
2. Silhouette: cloud pixels of the close-up (bright, low saturation), holes filled; banks = large components.
3. Tones: every pixel -> nearest cloud thread in CIELAB (pale, cream, sand, sage light, sage, slate, shadow);
   navy pinholes inside the silhouette take the nearest cloud tone; majority filter removes islands < ~1 mm.
4. Stitch direction: structure tensor of the close-up's own stitch texture (strand direction), averaged per 5 mm cell.
5. Keep-outs: banks are cut 8 mm inside each size-independent keep-out and re-grown with whole round lobes (r 7) along
   that edge, so no bank ends in a straight clip.
Output: closetrace.pkl {P: {"regions": [...], "info": {...}}} in size-M garment mm."""
import glcore
import json, pickle, math
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import measure, color
from shapely.geometry import Polygon, Point, box, LineString
from shapely.ops import unary_union
from shapely import affinity, prepared
import tech, front as F
from motifs2 import HEX

FILES = {"FR": "inputs/closeups/closeup_front_right.png", "FL": "inputs/closeups/closeup_front_left.png"}
# affine close-up px -> mm:  x = ax + bx*u, y = ay + by*v   (fit, see FIT below)
FIT = {
 # FR: close-up horizon v=725 -> 199 mm; bank top v=205 -> 80 mm (mockup bank top); bank right end u=955 -> -11 mm;
 #     close-up left edge u=0 -> -300 mm (mockup bank reaches the side seam)
 "FR": dict(pairs=[((0, 725), (-300.0, 199.0)), ((955, 205), (-11.0, 80.0)), ((955, 725), (-11.0, 199.0)), ((0, 915), (-300.0, 242.5)),
                   ((245, 1270), (-226.0, 323.0))]),
 # FL: horizon v=626 -> 199; bank top v=180 -> 103; bank left end u=360 -> 62 mm; right edge u=1122 -> 292 mm (side bank)
 "FL": dict(pairs=[((360, 626), (62.0, 199.0)), ((1122, 180), (292.0, 103.0)), ((1122, 626), (292.0, 199.0)), ((900, 780), (225.0, 232.0)),
                   ((970, 1250), (246.0, 334.0))]),
}
def fit(P):
    uv = np.array([p[0] for p in FIT[P]["pairs"]], float); xy = np.array([p[1] for p in FIT[P]["pairs"]], float)
    Ax = np.c_[np.ones(len(uv)), uv[:, 0]]; Ay = np.c_[np.ones(len(uv)), uv[:, 1]]
    cx, *_ = np.linalg.lstsq(Ax, xy[:, 0], rcond=None); cy, *_ = np.linalg.lstsq(Ay, xy[:, 1], rcond=None)
    res = np.hypot(Ax @ cx - xy[:, 0], Ay @ cy - xy[:, 1])
    return cx, cy, res

TONES = ["gl_pale", "gl_cream", "gl_sand", "gl_sagelt", "gl_sage", "gl_slate", "gl_shadow"]
# tone centres measured on the close-ups (k-means of the bank pixels): cream highlights, sand only in shadow (review D4)
CLOSE_T = ["#F3EBD6", "#DDCFB2", "#BFB296", "#A2A187", "#737866", "#5C7488", "#3C4240"]
def lab_of(hexs): return color.rgb2lab(np.array([[[int(h[i:i+2], 16)/255 for i in (1, 3, 5)] for h in hexs]]))[0]
PPM = 5.0

def trace(P):
    cx, cy, res = fit(P)
    B = np.array(Image.open(FILES[P]).convert("RGB")).astype(np.float32) / 255
    Hc, Wc = B.shape[:2]
    x0, x1 = sorted([cx[0], cx[0] + cx[1]*Wc]); y0, y1 = cy[0], cy[0] + cy[1]*Hc
    W, H = int((x1 - x0)*PPM), int((y1 - y0)*PPM)
    XX, YY = np.meshgrid(x0 + (np.arange(W) + 0.5)/PPM, y0 + (np.arange(H) + 0.5)/PPM)
    U = (XX - cx[0]) / cx[1]; V = (YY - cy[0]) / cy[1]
    img = np.stack([ndi.map_coordinates(B[..., k], [V, U], order=1, mode="nearest") for k in range(3)], -1)
    lum = img @ np.array([0.3, 0.59, 0.11]); mx, mn = img.max(2), img.min(2); sat = (mx - mn) / np.maximum(mx, 1e-3)
    teal = (img[..., 1] > img[..., 0] + 0.08) & (img[..., 2] > img[..., 0] + 0.06) & (sat > 0.35)
    cloud = (lum > 0.235) & ~teal
    if P == "FL":           # the close-up's own half sun + glitter column (one sun only, built from the mockup)
        sun_u, sun_v = 192, 597
        cloud &= ~((((U - sun_u)/150)**2 + ((V - sun_v)/150)**2 < 1) | ((U < 330) & (V > sun_v - 10)))
    disk = lambda mm: (lambda r: (lambda y, x: x*x + y*y <= r*r)(*np.ogrid[-r:r+1, -r:r+1]))(int(round(mm*PPM)))
    cloud = ndi.binary_closing(cloud, structure=disk(0.8)); cloud = ndi.binary_fill_holes(cloud)
    cloud = ndi.binary_opening(cloud, structure=disk(2.2))          # drops the close-up horizon line + star arms
    lab_, n = ndi.label(cloud); sizes = ndi.sum(cloud, lab_, range(1, n+1)) / PPM**2
    sl_ = ndi.find_objects(lab_)
    def is_bank(i):         # sky banks (reach above the horizon) + side-seam sea banks; mid-sea islets come from the mockup
        if sizes[i] < 350: return False
        r0 = y0 + sl_[i][0].start / PPM; c0 = x0 + sl_[i][1].start / PPM; c1 = x0 + sl_[i][1].stop / PPM
        return r0 < 195 or (P == "FR" and c0 < -255) or (P == "FL" and c1 > 255)
    keep = np.isin(lab_, [i + 1 for i in range(n) if is_bank(i)])
    # tones
    L = color.rgb2lab(img); pal = lab_of(CLOSE_T)       # classify against the close-up's own tone centres, then map to threads
    d = ((L[..., None, :] - pal[None, None]) ** 2).sum(-1)
    cool = (img[..., 1] > img[..., 0] + 0.012) | (img[..., 2] > img[..., 0] + 0.02)    # greenish / bluish pixels are never cream/sand
    d[..., :3] += np.where(cool, 250.0, 0.0)[..., None]
    lbl = d.argmin(-1)
    dark = lum < 0.235                                                             # navy pinholes inside the silhouette
    if dark.any():
        idx = ndi.distance_transform_edt(dark | ~keep, return_distances=False, return_indices=True)
        lbl = lbl[idx[0], idx[1]]
    oh = np.stack([ndi.gaussian_filter((lbl == k).astype(np.float32), 0.7*PPM) for k in range(len(TONES))], -1)
    lbl = oh.argmax(-1)
    for k in range(len(TONES)):                      # tone specks < 3 mm2 join their surroundings (no pinholes, no speckle)
        lk, nk = ndi.label(lbl == k)
        if not nk: continue
        sz = ndi.sum(np.ones_like(lk), lk, range(1, nk + 1)) / PPM**2
        small = np.isin(lk, [i + 1 for i, v in enumerate(sz) if v < 3.0])
        if small.any():
            idx = ndi.distance_transform_edt(small, return_distances=False, return_indices=True); lbl = lbl[idx[0], idx[1]]
    # strand direction from the close-up texture (structure tensor)
    g = ndi.gaussian_filter(lum, 0.5)
    gx = ndi.sobel(g, 1); gy = ndi.sobel(g, 0)
    s = 1.5*PPM
    Jxx = ndi.gaussian_filter(gx*gx, s); Jyy = ndi.gaussian_filter(gy*gy, s); Jxy = ndi.gaussian_filter(gx*gy, s)
    # keep-outs (size-independent, M coords): cut 8 inside, re-grow whole lobes
    side = "R" if P == "FR" else "L"
    import scene_lim
    lim = scene_lim.LIM_ALL[side]
    def to_polys(mask, simplify=0.25, min_area=1.2):
        """mask -> polygons WITH holes (contour nesting parity), per connected component"""
        out = []
        labm, nm = ndi.label(mask)
        for j, sl in enumerate(ndi.find_objects(labm), 1):
            sub = np.pad(labm[sl] == j, 1)
            if sub.sum() / PPM**2 < min_area: continue
            rings = []
            for c in measure.find_contours(sub.astype(float), 0.5):
                if len(c) < 6: continue
                p = Polygon([(x0 + (sl[1].start + xx - 1 + 0.5)/PPM, y0 + (sl[0].start + yy - 1 + 0.5)/PPM) for yy, xx in c]).buffer(0)
                if p.area > 0.05: rings.append(p)
            if not rings: continue
            rings.sort(key=lambda p: -p.area); g = rings[0]
            for r_ in rings[1:]:
                g = g.difference(r_) if g.contains(r_.representative_point()) else g.union(r_)
            g = g.buffer(0)
            if g.area >= min_area: out.append(g.simplify(simplify))
        return out
    sil_parts = [p for p in to_polys(keep, 0.3, 50) if p.area > 50]
    sil = unary_union(sil_parts).buffer(0)
    RL, CUT = 8.0, 9.0
    core0 = sil.intersection(lim.buffer(-CUT)).buffer(0)
    # no towers: parts narrower than 20 mm that the keep-out leaves standing in the sky are dropped (review D1)
    core = unary_union([core0.buffer(-10).buffer(10, join_style="round").intersection(core0), core0.intersection(box(-400, 175, 400, 900))]).buffer(0)
    core = unary_union([g for g in (getattr(core, "geoms", [core])) if g.area > 30])
    edge = core.boundary.intersection(lim.buffer(-CUT).boundary.buffer(0.6))       # where the bank was cut by the keep-out
    lobes = []
    for ln in [edge] if edge.geom_type in ("LineString",) else list(getattr(edge, "geoms", [])):
        if ln.length < 3: continue
        k = max(1, int(round(ln.length / (1.6 * RL))))
        for t in np.linspace(0, 1, k + 1):
            pt = ln.interpolate(t, normalized=True); lobes.append(Point(pt.x, pt.y).buffer(RL, quad_segs=16))
    grow = unary_union(lobes).intersection(sil).intersection(lim.buffer(-0.6)) if lobes else Polygon()
    region = unary_union([core, grow]).buffer(0)
    regions = []
    angle_at = lambda px, py: math.degrees(0.5*math.atan2(2*Jxy[py, px], Jxx[py, px] - Jyy[py, px])) + 90.0
    def rows_cols(p):
        b = p.bounds; return int((b[0]-x0)*PPM), int((b[1]-y0)*PPM), int((b[2]-x0)*PPM)+1, int((b[3]-y0)*PPM)+1
    for k, tone in enumerate(TONES):
        m = (lbl == k) & keep
        if not m.any(): continue
        for p in to_polys(m):
            p = p.intersection(region).buffer(0)
            if p.is_empty or p.area < 1.2: continue
            b = p.bounds
            for gy0 in np.arange(b[1] - 2.5*((int(b[0]) // 5) % 2), b[3], 5.0):          # staggered 5 mm cells: own angle each
                for gx0 in np.arange(b[0], b[2], 5.0):
                    q = p.intersection(box(gx0, gy0, gx0 + 5.0, gy0 + 5.0))
                    for qq in ([q] if q.geom_type == "Polygon" else [g_ for g_ in getattr(q, "geoms", []) if g_.geom_type == "Polygon"]):
                        if qq.area < 0.6: continue
                        c0, r0, c1, r1 = rows_cols(qq)
                        c0, r0 = max(c0, 0), max(r0, 0); c1, r1 = min(c1, W), min(r1, H)
                        jxx, jyy, jxy = Jxx[r0:r1, c0:c1].mean(), Jyy[r0:r1, c0:c1].mean(), Jxy[r0:r1, c0:c1].mean()
                        ang = math.degrees(0.5*math.atan2(2*jxy, jxx - jyy)) + 90.0
                        regions.append(dict(col=tone, geom=qq, st="tatami", ang=float(ang), grp="CL" if tone not in ("gl_slate", "gl_shadow") else "CL-shade",
                                            ko=True, kob=0.0, unit=None))
    info = dict(fit_resid_mm=[round(float(r), 2) for r in res], fit=dict(x=list(map(float, cx)), y=list(map(float, cy))),
                sil_mm2=round(sil.area), kept_mm2=round(region.area), lost_to_keepout_mm2=round(sil.area - region.area),
                edge_lobes=len(lobes), tone_mm2={t: round(sum(r["geom"].area for r in regions if r["col"] == t)) for t in TONES})
    return dict(regions=regions, info=info, sil=sil, region=region)

if __name__ == "__main__":
    out = {P: trace(P) for P in ("FR", "FL")}
    pickle.dump(out, open("closetrace.pkl", "wb"))
    print(json.dumps({P: v["info"] for P, v in out.items()}, indent=1))
