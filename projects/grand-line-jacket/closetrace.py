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

RL, EDGE_IN = 8.0, 9.5          # edge lobe radius; the close-up's outer border is placed this far inside the keep-out
DARKER = {"gl_pale": "gl_cream", "gl_cream": "gl_sand", "gl_sand": "gl_sage", "gl_sagelt": "gl_sage", "gl_sage": "gl_slate",
          "gl_slate": "gl_shadow", "gl_shadow": "gl_slate"}

def trace(P, seed=1):
    """Rev E: row-wise fit of the close-up into the allowed area (outer border EDGE_IN inside the keep-out, inner bank end on the
    mockup anchor), tones smoothed + vertically ordered, lobes from a luminance watershed, fan tatami + arc rows per lobe."""
    import scene_lim
    from skimage.segmentation import watershed
    from skimage.feature import peak_local_max
    rng = np.random.default_rng(seed)
    cx, cy, res = fit(P)
    side = "R" if P == "FR" else "L"; lim = scene_lim.LIM_ALL[side]
    B = np.array(Image.open(FILES[P]).convert("RGB")).astype(np.float32) / 255
    Hc, Wc = B.shape[:2]
    y0, y1 = cy[0], cy[0] + cy[1]*Hc
    # inner anchor (mockup): FR bank end u=955 -> x=-11; FL bank start u=360 -> x=62
    uA, xA, uE = (955.0, -11.0, 0.0) if P == "FR" else (360.0, 62.0, float(Wc))
    def outer(y):               # keep-out boundary on the seam side at row y
        seg = lim.intersection(LineString([(-400, y), (400, y)]))
        if seg.is_empty: return None
        b = seg.bounds; return (b[0] + EDGE_IN) if P == "FR" else (b[2] - EDGE_IN)
    x0, x1 = (-300.0, 45.0) if P == "FR" else (-45.0, 300.0)
    W, H = int((x1 - x0)*PPM), int((y1 - y0)*PPM)
    ys = y0 + (np.arange(H) + 0.5)/PPM; xs = x0 + (np.arange(W) + 0.5)/PPM
    XX, YY = np.meshgrid(xs, ys)
    xo = np.array([outer(y) if outer(y) is not None else np.nan for y in ys])
    ffill = pd_ffill(xo)
    scale = (xA - ffill) / (uA - uE)                                   # mm per close-up px, per row
    U = uE + (XX - ffill[:, None]) / scale[:, None]
    V = (YY - cy[0]) / cy[1]
    inside = (U >= 0) & (U <= Wc - 1)
    img = np.stack([ndi.map_coordinates(B[..., k], [V, U], order=1, mode="nearest") for k in range(3)], -1)
    lum = img @ np.array([0.3, 0.59, 0.11]); mx, mn = img.max(2), img.min(2); sat = (mx - mn) / np.maximum(mx, 1e-3)
    teal = (img[..., 1] > img[..., 0] + 0.08) & (img[..., 2] > img[..., 0] + 0.06) & (sat > 0.35)
    cloud = (lum > 0.235) & ~teal & inside
    if P == "FL":           # the close-up's own half sun + glitter column (one sun only, built from the mockup)
        sun_u, sun_v = 192, 597
        cloud &= ~((((U - sun_u)/150)**2 + ((V - sun_v)/150)**2 < 1) | ((U < 330) & (V > sun_v - 10)))
    disk = lambda mm: (lambda r: (lambda y, x: x*x + y*y <= r*r)(*np.ogrid[-r:r+1, -r:r+1]))(int(round(mm*PPM)))
    cloud = ndi.binary_closing(cloud, structure=disk(0.8)); cloud = ndi.binary_fill_holes(cloud)
    cloud = ndi.binary_opening(cloud, structure=disk(2.2))
    lab_, n = ndi.label(cloud); sizes = ndi.sum(cloud, lab_, range(1, n+1)) / PPM**2
    sl_ = ndi.find_objects(lab_)
    def is_bank(i):
        if sizes[i] < 350: return False
        r0 = y0 + sl_[i][0].start / PPM; c0 = x0 + sl_[i][1].start / PPM; c1 = x0 + sl_[i][1].stop / PPM
        return r0 < 195 or (P == "FR" and c0 < -250) or (P == "FL" and c1 > 250)
    keep = np.isin(lab_, [i + 1 for i in range(n) if is_bank(i)])
    # ---- whole lobes along the close-up border (where the bank runs off the image edge, now EDGE_IN inside the keep-out)
    edge_col = np.clip(((ffill - x0) * PPM).astype(int), 0, W - 1)
    border = np.zeros_like(keep)
    for r in range(H):
        c = edge_col[r]
        win = keep[r, max(0, c - 3):c + 4] if P == "FR" else keep[r, max(0, c - 3):c + 4]
        if win.any(): border[r, c] = True
    lobe_c = []; rows = np.nonzero(border.any(1))[0]; last = -1e9
    for r in rows:
        if (r - last) / PPM >= 1.55 * RL: lobe_c.append((r, edge_col[r])); last = r
    grown = keep.copy()
    yy_, xx_ = np.ogrid[:H, :W]
    for (r, c) in lobe_c:
        rr = RL * PPM * rng.uniform(0.85, 1.0)
        grown |= ((yy_ - r)**2 + (xx_ - c)**2 <= rr*rr)
    # never outside the keep-out (0.6 inside); straight image border inside the lobes is covered by them
    import shapely.vectorized as SV
    inlim = SV.contains(lim.buffer(-0.6), XX, YY)
    lost_mm2 = float((keep & ~inlim).sum()) / PPM**2              # traced cloud that still falls outside the keep-out
    grown &= inlim
    # ---- tones: nearest close-up tone centre (cool pixels never cream/sand), navy pinholes filled
    L = color.rgb2lab(img); pal = lab_of(CLOSE_T)
    d = ((L[..., None, :] - pal[None, None]) ** 2).sum(-1)
    cool = (img[..., 1] > img[..., 0] + 0.012) | (img[..., 2] > img[..., 0] + 0.02)
    d[..., :3] += np.where(cool, 250.0, 0.0)[..., None]
    lbl = d.argmin(-1)
    src = keep & (lum >= 0.235)
    idx = ndi.distance_transform_edt(~src, return_distances=False, return_indices=True)
    lbl = lbl[idx[0], idx[1]]                                   # dark pinholes + grown lobes take the nearest traced tone
    T = {t: k for k, t in enumerate(TONES)}
    def mode(lbl, sigma_mm):
        oh = np.stack([ndi.gaussian_filter(((lbl == k) & grown).astype(np.float32), sigma_mm*PPM) for k in range(len(TONES))], -1)
        return oh.argmax(-1)
    def merge_small(lbl, min_mm2):
        for _ in range(3):
            changed = False
            for k in range(len(TONES)):
                lk, nk = ndi.label((lbl == k) & grown)
                if not nk: continue
                sz = ndi.sum(np.ones_like(lk), lk, range(1, nk + 1)) / PPM**2
                small = np.isin(lk, [i + 1 for i, v in enumerate(sz) if v < min_mm2])
                if small.any():
                    keepm = grown & ~small
                    ix = ndi.distance_transform_edt(~keepm, return_distances=False, return_indices=True)
                    lbl = np.where(small, lbl[ix[0], ix[1]], lbl); changed = True
            if not changed: break
        return lbl
    lbl = mode(lbl, 1.0)
    # vertical order per bank (review E1): sage on top, slate mid, sand / cream at the base
    gl, ng = ndi.label(grown)
    for j, sl in enumerate(ndi.find_objects(gl), 1):
        m = gl[sl] == j
        top = np.where(m.any(0), m.argmax(0), 0); bot = np.where(m.any(0), m.shape[0] - 1 - m[::-1].argmax(0), 0)
        rr = np.arange(m.shape[0])[:, None]
        t = (rr - top[None, :]) / np.maximum(bot - top, 8*PPM)[None, :]
        sub = lbl[sl]; xcol = x0 + (np.arange(sl[1].start, sl[1].stop) + 0.5) / PPM
        upper = m & (t < 0.32); lower = m & (t > 0.66)
        sub = np.where(upper & np.isin(sub, [T["gl_pale"], T["gl_cream"]]), T["gl_sagelt"], sub)
        sub = np.where(upper & (sub == T["gl_sand"]), T["gl_sage"], sub)
        sage_ok = (xcol < -235)[None, :] if P == "FR" else np.zeros((1, m.shape[1]), bool)   # sage tint only lower-left FR (close-up)
        sub = np.where(lower & np.isin(sub, [T["gl_slate"], T["gl_shadow"]]), T["gl_sand"], sub)
        sub = np.where(lower & np.isin(sub, [T["gl_sage"], T["gl_sagelt"]]) & ~sage_ok, T["gl_cream"], sub)
        lbl[sl] = np.where(m, sub, lbl[sl])
    lbl = merge_small(lbl, 18.0)
    # ---- lobes: watershed of the close-up luminance (lobes are bright domes split by darker valleys)
    lum_s = ndi.gaussian_filter(np.where(grown, lum, 0), 1.6*PPM)
    pk = peak_local_max(lum_s, min_distance=int(4.0*PPM), labels=grown.astype(int), exclude_border=False)
    mk = np.zeros(lum_s.shape, int)
    for i, (r, c) in enumerate(pk, 1): mk[r, c] = i
    lobes = watershed(-lum_s, mk, mask=grown)
    def to_polys(mask, simplify=0.25, min_area=1.2, ox=0, oy=0):
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
    regions = []; arcs = 0; holes = 0
    limp = lim.buffer(-0.6)
    for j, sl in enumerate(ndi.find_objects(lobes), 1):
        if sl is None: continue
        m = lobes[sl] == j
        if m.sum() / PPM**2 < 2.0: continue
        ys_, xs_ = np.nonzero(m)
        lcx = x0 + (sl[1].start + xs_.mean() + 0.5) / PPM
        ybot = y0 + (sl[0].start + ys_.max() + 1) / PPM; ytop = y0 + (sl[0].start + ys_.min()) / PPM
        fan = ("radial", float(lcx), float(ybot + 0.15*(ybot - ytop)))         # stitches fan up from the lobe base
        sub_l = lbl[sl]
        dom = TONES[np.bincount(sub_l[m], minlength=len(TONES)).argmax()]
        lobe_geom = []
        for k, tone in enumerate(TONES):
            mm = m & (sub_l == k)
            if not mm.any(): continue
            full = np.zeros_like(lobes, bool); full[sl] = mm
            for p in to_polys(full):
                p = p.intersection(limp).buffer(0)
                if p.is_empty or p.area < 1.2: continue
                if tone in ("gl_cream", "gl_pale") and p.area > 60 and rng.random() < 0.35:     # a few real round pinholes
                    q = p.buffer(-2.5)
                    if not q.is_empty:
                        c_ = q.representative_point(); p = p.difference(Point(c_.x, c_.y).buffer(0.75, quad_segs=8)); holes += 1
                # fan as 14-degree sectors, each an even straight fill pointing at the fan centre (radial fills leave gaps, review E2)
                fx, fy = fan[1], fan[2]; Rm = max(math.hypot(px_ - fx, py_ - fy) for px_, py_ in p.exterior.coords) + 2
                for a0 in np.arange(-180, 0, 14.0):
                    wedge = Polygon([(fx, fy)] + [(fx + Rm*math.cos(math.radians(a_)), fy + Rm*math.sin(math.radians(a_))) for a_ in np.linspace(a0, a0 + 14, 5)])
                    q = p.intersection(wedge)
                    for qq in ([q] if q.geom_type == "Polygon" else [g_ for g_ in getattr(q, "geoms", []) if g_.geom_type == "Polygon"]):
                        if qq.area < 0.6: continue
                        regions.append(dict(col=tone, geom=qq, st="tatami", ang=float(a0 + 7 + 90), grp="CL" if tone not in ("gl_slate", "gl_shadow") else "CL-shade",
                                            ko=True, kob=0.0, unit=None))
                below = p.intersection(box(-400, fy, 400, 900))          # anything under the fan centre: plain rows
                for qq in ([below] if below.geom_type == "Polygon" else [g_ for g_ in getattr(below, "geoms", []) if g_.geom_type == "Polygon"]):
                    if qq.area >= 0.6: regions.append(dict(col=tone, geom=qq, st="tatami", ang=0.0, grp="CL", ko=True, kob=0.0, unit=None))
                lobe_geom.append(p)
        # arc rows (the close-up's overlapping stitch rows), one tone darker, sewn on top
        if lobe_geom and m.sum() / PPM**2 > 35:
            lg = unary_union(lobe_geom).buffer(-0.8)
            R = max(3.0, ybot - ytop)
            for rad in np.arange(0.38*R, 0.95*R, 2.7):
                pts = [(fan[1] + rad*1.15*math.cos(a), fan[2] + rad*math.sin(a)) for a in np.radians(np.linspace(-165, -15, 40))]
                g_ = LineString(pts).intersection(lg)
                for gg in ([g_] if g_.geom_type == "LineString" else [x for x in getattr(g_, "geoms", []) if x.geom_type == "LineString"]):
                    if gg.length < 3.0: continue
                    regions.append(dict(col=DARKER[dom], geom=gg.buffer(0.25, cap_style="round"), st="run", ang=None, grp="CL-scale",
                                        ko=False, kob=0.0, unit=None, sub="scale")); arcs += 1
    region = unary_union([r["geom"] for r in regions if r["st"] == "tatami"]).buffer(0)
    sil = region
    info = dict(fit_resid_mm=[round(float(r), 2) for r in res], fit=dict(y=list(map(float, cy))), row_fit=dict(u_border=uE, u_anchor=uA, x_anchor=xA, edge_in=EDGE_IN),
                kept_mm2=round(region.area), lost_to_keepout_mm2=round(lost_mm2), edge_lobes=len(lobe_c), lobes=int(lobes.max()), arcs=arcs, pinholes=holes,
                tone_mm2={t: round(sum(r["geom"].area for r in regions if r["col"] == t and r["st"] == "tatami")) for t in TONES})
    return dict(regions=regions, info=info, sil=sil, region=region)

def pd_ffill(a):
    a = a.copy(); idx = np.where(~np.isnan(a))[0]
    if not len(idx): return np.zeros_like(a)
    a[:idx[0]] = a[idx[0]]
    for i in range(1, len(a)):
        if np.isnan(a[i]): a[i] = a[i-1]
    return a

if __name__ == "__main__":
    out = {P: trace(P) for P in ("FR", "FL")}
    pickle.dump(out, open("closetrace.pkl", "wb"))
    print(json.dumps({P: v["info"] for P, v in out.items()}, indent=1))
