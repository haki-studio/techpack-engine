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

EDGE_IN = 2.0                   # Rev E2: the close-up's outer border is placed this far inside the keep-out (edge lobes regrown inside)
DARKER = {"gl_pale": "gl_cream", "gl_cream": "gl_sand", "gl_sand": "gl_sage", "gl_sagelt": "gl_sage", "gl_sage": "gl_slate",
          "gl_slate": "gl_shadow", "gl_shadow": "gl_slate"}

ANCHOR = {"FR": (955.0, -11.0, 0.0), "FL": (360.0, 62.0, None)}       # (u of the inner bank end, its x in mm, u of the outer border)
SCALE_SMOOTH, SCALE_MIN = 25.0, 0.95     # Rev E2: per-row scale smoothed over 25 mm and never < 95 % of the median (no tower lobes)

def mapping(P, XX, YY, Wc):
    """garment mm (size M) -> close-up px (U, V). The inner bank end stays on the mockup anchor; the scale per row is the one
    that puts the close-up's outer border EDGE_IN inside the keep-out, smoothed and clamped so no row is squeezed (review E5)."""
    import scene_lim
    from scipy.ndimage import gaussian_filter1d
    cx, cy, _ = fit(P)
    lim = scene_lim.LIM_ALL["R" if P == "FR" else "L"]
    uA, xA, uE = ANCHOR[P]; uE = float(Wc) if uE is None else uE
    ys = YY[:, 0]
    def outer(y):
        seg = lim.intersection(LineString([(-400, y), (400, y)]))
        if seg.is_empty: return np.nan
        b = seg.bounds; return (b[0] + EDGE_IN) if P == "FR" else (b[2] - EDGE_IN)
    xo = pd_ffill(np.array([outer(y) for y in ys]))
    raw = (xA - xo) / (uA - uE)
    sc = gaussian_filter1d(raw, SCALE_SMOOTH * PPM, mode="nearest")
    sc = np.maximum(sc, SCALE_MIN * np.median(raw))
    U = uA + (XX - xA) / sc[:, None]
    V = (YY - cy[0]) / cy[1]
    return U, V, sc

def tone_of_lab(lab):
    """nearest cloud thread for a lobe's median CIELAB (bright 60 % of its pixels): warm = cream / sand, green = sage, cool = slate"""
    L_, a_, b_ = lab
    if b_ > 11.0 and a_ > -4.5:                       # warm
        return "gl_pale" if L_ > 90 else ("gl_cream" if L_ > 74 else "gl_sand")
    if b_ > 5.5 and a_ < -2.0:                       # green
        return "gl_sagelt" if L_ > 72 else ("gl_sage" if L_ > 50 else "gl_shadow")
    if L_ > 78: return "gl_cream" if b_ > 6 else "gl_sagelt"
    return "gl_slate" if L_ > 44 else "gl_shadow"

def trace(P, seed=1):
    """Rev E2: banks traced LOBE BY LOBE from the close-up.
    silhouette = close-up cloud pixels (row fit, see mapping); wherever a bank meets the keep-out or the close-up border it is
    cut back ~11 mm and regrown with whole round lobes (varied radius and depth, no straight edge);
    lobes = luminance watershed of the close-up (the bright domes split by the darker valleys) + the regrown edge lobes;
    tone = ONE thread per lobe from its traced colour, ordered per bank (sage tops, slate middle, cream / sand base), plus a
    clean darker crescent under the larger lobes; stitches = concentric rows per lobe (fan of 14 deg sectors), arc rows on the
    sage / slate lobes, a few round pinholes in the cream lobes (review E1-E6)."""
    import scene_lim
    from skimage.segmentation import watershed
    from skimage.feature import peak_local_max
    import shapely.vectorized as SV
    rng = np.random.default_rng(seed)
    cx, cy, res = fit(P)
    side = "R" if P == "FR" else "L"; lim = scene_lim.LIM_ALL[side]
    B = np.array(Image.open(FILES[P]).convert("RGB")).astype(np.float32) / 255
    Hc, Wc = B.shape[:2]
    y0, y1 = cy[0], cy[0] + cy[1]*Hc
    x0, x1 = (-300.0, 45.0) if P == "FR" else (-45.0, 300.0)
    W, H = int((x1 - x0)*PPM), int((y1 - y0)*PPM)
    ys = y0 + (np.arange(H) + 0.5)/PPM; xs = x0 + (np.arange(W) + 0.5)/PPM
    XX, YY = np.meshgrid(xs, ys)
    U, V, sc = mapping(P, XX, YY, Wc)
    inside = (U >= 0) & (U <= Wc - 1) & (V >= 0) & (V <= Hc - 1)
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
    inlim = SV.contains(lim.buffer(-0.6), XX, YY)
    lost_mm2 = float((keep & ~inlim).sum()) / PPM**2              # traced cloud that falls outside the keep-out (regrown inside)
    # ---- whole lobes wherever the bank meets the keep-out or the close-up border (review E4)
    allowed = inside & inlim
    cut = keep & allowed
    Dal = ndi.distance_transform_edt(np.pad(allowed, 1))[1:-1, 1:-1] / PPM          # mm to the edge of the allowed area
    contact = cut & (Dal < 1.2) & ndi.binary_dilation(keep & ~allowed, structure=disk(1.6))
    Dc = ndi.distance_transform_edt(~contact) / PPM if contact.any() else np.full(cut.shape, 1e9)
    ZR = 11.0
    zone = cut & (Dal < ZR) & (Dc < ZR + 3)
    core = cut & ~zone
    Ds = ndi.gaussian_filter(Dal, 2.0*PPM); gy, gx = np.gradient(Ds)
    cpts = np.argwhere(contact); rng.shuffle(cpts)
    discs = []; SPC = 8.0
    for r, c in cpts:
        if any((r - a)**2 + (c - b)**2 < (SPC*PPM)**2 for a, b, _ in discs): continue
        nrm = np.hypot(gx[r, c], gy[r, c])
        if nrm < 1e-6: continue
        R = rng.uniform(5.5, 9.5); dep = rng.uniform(0.6, 3.8)
        rc = r + gy[r, c]/nrm*(R + dep)*PPM; cc = c + gx[r, c]/nrm*(R + dep)*PPM
        ri, ci = int(round(rc)), int(round(cc))
        if not (0 <= ri < H and 0 <= ci < W) or not keep[ri, ci]: continue
        discs.append((rc, cc, R))
    yy_, xx_ = np.ogrid[:H, :W]
    dlab = np.zeros((H, W), int); dbest = np.full((H, W), np.inf)
    for k, (rc, cc, R) in enumerate(discs, 1):
        d = np.sqrt((yy_ - rc)**2 + (xx_ - cc)**2) / (R*PPM)
        m = (d <= 1.0) & (d < dbest) & inlim
        dlab[m] = k; dbest[m] = d[m]
    grown = core | (dlab > 0)
    grown = ndi.binary_fill_holes(grown) & inlim
    grown = ndi.binary_opening(grown, structure=disk(1.0))
    dlab[~grown] = 0
    # ---- lobes: watershed of the close-up luminance + the regrown edge discs (each its own lobe)
    lum_s = ndi.gaussian_filter(np.where(grown, lum, 0), 1.8*PPM)
    pk = peak_local_max(np.where(dlab > 0, 0, lum_s), min_distance=int(5.5*PPM), labels=(grown & (dlab == 0)).astype(int), exclude_border=False)
    mk = np.zeros(lum_s.shape, int)
    for i, (r, c) in enumerate(pk, 1): mk[r, c] = i
    nW = len(pk)
    ws_ = watershed(-lum_s, mk, mask=grown & (dlab == 0))
    lobes = np.where(dlab > 0, dlab + nW, ws_)
    lobes = np.where(grown & (lobes == 0), 0, lobes)
    # ---- tone per lobe from the close-up (bright 60 % of its traced pixels), cool pixels never cream
    Lab = color.rgb2lab(img)
    srcpix = inside & (lum >= 0.235) & keep
    nl = int(lobes.max()); tone = {}; cen = {}
    objs = ndi.find_objects(lobes)
    for j, sl in enumerate(objs, 1):
        if sl is None: continue
        m = lobes[sl] == j
        ys_, xs_ = np.nonzero(m)
        cen[j] = (sl[0].start + ys_.mean(), sl[1].start + xs_.mean(), sl[0].start + ys_.min(), sl[0].start + ys_.max())
        s = m & srcpix[sl]
        if s.sum() < 0.3*m.sum() or s.sum() < 10: continue
        l = lum[sl][s]; k = l >= np.percentile(l, 40)
        tone[j] = tone_of_lab(np.median(Lab[sl][s][k], axis=0))
    if tone:            # lobes with too little traced pixel (regrown edge discs) take the tone of the nearest traced lobe
        known = np.array([cen[j][:2] for j in tone]); kj = list(tone)
        for j in cen:
            if j not in tone:
                d = np.hypot(known[:, 0] - cen[j][0], known[:, 1] - cen[j][1]); tone[j] = tone[kj[int(d.argmin())]]
    # ---- order per bank (review E1): sage on top, slate in the middle, sand / cream at the base
    gl, ng = ndi.label(grown); tops = {}; sage_lowleft = 0
    for g, sl in enumerate(ndi.find_objects(gl), 1):
        m = gl[sl] == g
        top = np.where(m.any(0), m.argmax(0), 0) + sl[0].start; bot = np.where(m.any(0), m.shape[0] - 1 - m[::-1].argmax(0), 0) + sl[0].start
        tops[g] = (sl[1].start, top, bot)
    for j, (rc, cc, rt, rb) in cen.items():
        g = gl[int(rc), int(cc)] or gl[int(rt), int(cc)]
        if not g: continue
        c0, top, bot = tops[g]; ci = min(max(int(cc) - c0, 0), len(top) - 1)
        t = (rc - top[ci]) / max(bot[ci] - top[ci], 8*PPM)
        tn = tone[j]; xmm = x0 + cc / PPM
        if t < 0.30:
            tn = {"gl_pale": "gl_sagelt", "gl_cream": "gl_sagelt", "gl_sand": "gl_sage", "gl_shadow": "gl_slate"}.get(tn, tn)
        elif t > 0.64:
            lowleft = P == "FR" and xmm < -235
            tn = {"gl_slate": "gl_sand", "gl_shadow": "gl_sand"}.get(tn, tn)
            if tn in ("gl_sage", "gl_sagelt"):
                if lowleft: sage_lowleft += 1
                else: tn = "gl_cream"
        else:
            tn = {"gl_pale": "gl_cream"}.get(tn, tn)
        tone[j] = tn
    # ---- polygons per lobe: body + crescent, concentric rows (14 deg sectors), arcs / pinholes
    def to_poly(mask):
        sub = np.pad(mask, 1); out = []
        for c in measure.find_contours(sub.astype(float), 0.5):
            if len(c) < 6: continue
            p = Polygon([(x0 + (xx - 1 + 0.5)/PPM, y0 + (yy - 1 + 0.5)/PPM) for yy, xx in c]).buffer(0)
            if p.area > 0.05: out.append(p)
        if not out: return Polygon()
        out.sort(key=lambda p: -p.area); g = out[0]
        for r_ in out[1:]:
            g = g.difference(r_) if g.contains(r_.representative_point()) else g.union(r_)
        return g.buffer(0)
    limp = lim.buffer(-0.6)
    regions = []; arcs = 0; holes = 0; crescents = 0; nlobe = 0
    def polys_(g): return [g] if g.geom_type == "Polygon" else [q for q in getattr(g, "geoms", []) if q.geom_type == "Polygon"]
    def fan_fill(p, tone_, fx, fy, grp):
        Rm = max(math.hypot(px_ - fx, py_ - fy) for q in polys_(p) for px_, py_ in q.exterior.coords) + 2
        for a0 in np.arange(-180, 0, 14.0):
            wedge = Polygon([(fx, fy)] + [(fx + Rm*math.cos(math.radians(a_)), fy + Rm*math.sin(math.radians(a_))) for a_ in np.linspace(a0, a0 + 14, 5)])
            for qq in polys_(p.intersection(wedge)):
                if qq.area >= 0.6: regions.append(dict(col=tone_, geom=qq, st="tatami", ang=float(a0 + 7 + 90), grp=grp, ko=True, kob=0.0, unit=None))
        for qq in polys_(p.intersection(box(-400, fy, 400, 900))):
            if qq.area >= 0.6: regions.append(dict(col=tone_, geom=qq, st="tatami", ang=0.0, grp=grp, ko=True, kob=0.0, unit=None))
    for j, sl in enumerate(objs, 1):
        if sl is None or j not in tone: continue
        full = np.zeros_like(grown); full[sl] = lobes[sl] == j
        if full.sum() / PPM**2 < 2.0: continue
        p = to_poly(full).buffer(0.5).buffer(-0.5).intersection(limp).buffer(0)
        if p.is_empty or p.area < 2.0: continue
        p = p.simplify(0.2); nlobe += 1
        tn = tone[j]; b_ = p.bounds; hgt = b_[3] - b_[1]
        fx = (b_[0] + b_[2]) / 2; fy = b_[3] + 0.15*hgt                        # rows are concentric about the lobe base
        grp = "CL" if tn not in ("gl_slate", "gl_shadow") else "CL-shade"
        body = p; cres = Polygon()
        if p.area > 40 and tn != "gl_shadow":                                   # clean darker crescent under the lobe
            up = affinity.translate(p, 0, -0.26*hgt)
            cres = p.difference(up).buffer(-0.4).buffer(0.4).intersection(p)
            if cres.area < 3.0: cres = Polygon()
            else: body = p.difference(cres).buffer(0); crescents += 1
        if tn in ("gl_cream", "gl_pale") and p.area > 60 and rng.random() < 0.4:       # a few real round pinholes, in an arc
            R = 0.55*hgt; nh = int(rng.integers(2, 4)); a0 = rng.uniform(-130, -50 - 12*nh)
            for k in range(nh):
                a = math.radians(a0 + 12*k); q = Point(fx + 1.15*R*math.cos(a), fy + R*math.sin(a))
                if body.buffer(-1.6).contains(q): body = body.difference(q.buffer(0.55, quad_segs=8)); holes += 1
        fan_fill(body, tn, fx, fy, grp)
        if not cres.is_empty: fan_fill(cres, DARKER[tn], fx, fy, "CL-shade")
        if tn in ("gl_sage", "gl_sagelt", "gl_slate") and p.area > 35:           # arc rows (the close-up's stitch rows), sewn on top
            lg = body.buffer(-0.8); Rr = max(3.0, hgt)
            for rad in np.arange(0.38*Rr, 0.95*Rr, 2.7):
                pts = [(fx + rad*1.15*math.cos(a), fy + rad*math.sin(a)) for a in np.radians(np.linspace(-165, -15, 40))]
                g_ = LineString(pts).intersection(lg)
                for gg in ([g_] if g_.geom_type == "LineString" else [x for x in getattr(g_, "geoms", []) if x.geom_type == "LineString"]):
                    if gg.length < 3.0: continue
                    regions.append(dict(col=DARKER[tn], geom=gg.buffer(0.25, cap_style="round"), st="run", ang=None, grp="CL-scale",
                                        ko=False, kob=0.0, unit=None, sub="scale")); arcs += 1
    region = unary_union([r["geom"] for r in regions if r["st"] == "tatami"]).buffer(0)
    info = dict(fit_resid_mm=[round(float(r), 2) for r in res], fit=dict(y=list(map(float, cy))),
                row_fit=dict(anchor=ANCHOR[P], edge_in=EDGE_IN, scale_mm_per_px=[round(float(sc.min()), 3), round(float(np.median(sc)), 3), round(float(sc.max()), 3)]),
                kept_mm2=round(region.area), lost_to_keepout_mm2=round(lost_mm2), edge_lobes=len(discs), lobes=nlobe, arcs=arcs, pinholes=holes,
                crescents=crescents, sage_low_left=sage_lowleft,
                tone_mm2={t: round(sum(r["geom"].area for r in regions if r["col"] == t and r["st"] == "tatami")) for t in TONES})
    return dict(regions=regions, info=info, sil=region, region=region, lobe_tone={int(k): v for k, v in tone.items()})

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
