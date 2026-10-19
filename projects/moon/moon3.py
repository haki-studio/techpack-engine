"""Rev C (final) moon — the close-up's STITCH STRUCTURE (LESSONS A13), replacing the Rev C WIP tile ground (moon2.py),
whose 7 mm tiles read as a grid with navy gaps (review item 3).

  ground  — FLOW ROWS: evenly spaced streamlines (0.45 mm apart, Jobard-Lefer) of the close-up's stitch-direction field
            (structure tensor of the thread rows), cut by the close-up's tone map (5 warm tones incl. the grey-green maria)
            and sewn as tatami rows ALONG the streamlines (3.5 mm stitches, staggered) -> the swirling thread rows of the
            close-up, one continuous ground, no tiles, no navy between tones (tones overlap 0.3 mm).
  cells   — every raised oval cell of the close-up (Hessian blobs, 2 scales): own satin along its long axis, tone from its
            own pixels, light rim run upper-left + shadow run lower-right (the dark gap between cells in the close-up).
  stars   — the 3 star craters as FILLED grey-green star silhouettes (11-13 spikes measured off the close-up), radial satin,
            spike centre lines in dark grey, pale centre disc + ring (review item 2).
  rim     — 2.2 mm radial satin ring in pale gold.
Close-up px -> back mm: centre (724.5, 295.5) -> (0, 244), r 275 px -> 120 mm (K = 0.436 mm/px)."""
import math
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import Point, Polygon, LineString, MultiLineString, box
from shapely.ops import unary_union, transform
from shapely import affinity
import shapely
from skimage import morphology
from motifs2 import R
import trace as TR

CX, CY, RPX = 724.5, 295.5, 275.0
RMM = 120.0; K = RMM / RPX; MCY = 244.0
def to_mm(x, y): return ((np.asarray(x) - CX) * K, MCY + (np.asarray(y) - CY) * K)
def to_px(x, y): return (CX + np.asarray(x) / K, CY + (np.asarray(y) - MCY) / K)
def TA_map(g): return transform(lambda x, y, z=None: to_mm(x, y), g)

# ground tones: close-up k-means of the moon disc (inputs/closeups/closeup_back.png) -> thread
GROUND = {"m1": (247, 231, 204), "m2": (240, 212, 172), "m3": (224, 189, 143), "m4": (196, 160, 118), "m5": (172, 156, 126)}
CODE = {"m1": "MN-hl", "m2": "MN", "m3": "MN-warm", "m4": "MN-crater", "m5": "MN-mare"}
# star craters read off the close-up (px): centre, outer radius, spikes, rotation
STARS = [(650, 128, 40, 11, 0.10), (652, 234, 34, 12, 0.35), (848, 240, 40, 12, 0.0)]
DSEP, STEP = 0.40, 0.30          # 0.40 rows: Rev C compare showed navy between 0.45 rows at the swirl

def lab(c): return TR.lab_img(np.array(c, float)[None, None, :])[0, 0]
def polys(g):
    if g is None or g.is_empty: return []
    if g.geom_type == "Polygon": return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]

# ------------------------------------------------------------------ direction field
def field(a):
    lum = a.mean(2)
    g = ndi.gaussian_filter(lum, 1.2); gx = ndi.sobel(g, 1); gy = ndi.sobel(g, 0)
    Jxx = ndi.gaussian_filter(gx * gx, 6); Jyy = ndi.gaussian_filter(gy * gy, 6); Jxy = ndi.gaussian_filter(gx * gy, 6)
    th = 0.5 * np.arctan2(2 * Jxy, Jxx - Jyy) + np.pi / 2           # along the rows (perpendicular to the gradient)
    coh = np.sqrt((Jxx - Jyy) ** 2 + 4 * Jxy ** 2) / (Jxx + Jyy + 1e-6)
    return th, coh

class Field:
    """orientation field sampled in mm (doubled-angle vectors, so 0/180 deg never cancel)"""
    def __init__(self, th, fig):
        H, W = th.shape; yy, xx = np.mgrid[0:H, 0:W]
        conc = np.arctan2(yy - CY, xx - CX) + np.pi / 2              # concentric rows where the figure hides the close-up
        th = np.where(fig, conc, th)
        self.c = ndi.gaussian_filter(np.cos(2 * th), 2.0); self.s = ndi.gaussian_filter(np.sin(2 * th), 2.0)
        self.H, self.W = H, W
    def __call__(self, x, y):
        px, py = to_px(x, y)
        px = min(max(px, 0), self.W - 1.001); py = min(max(py, 0), self.H - 1.001)
        i, j = int(py), int(px); fy, fx = py - i, px - j
        def bl(A): return (A[i, j] * (1 - fx) * (1 - fy) + A[i, j + 1] * fx * (1 - fy) + A[i + 1, j] * (1 - fx) * fy + A[i + 1, j + 1] * fx * fy)
        t = 0.5 * math.atan2(bl(self.s), bl(self.c)); return math.cos(t), math.sin(t)

# ------------------------------------------------------------------ evenly spaced streamlines (Jobard & Lefer 1997)
def streamlines(F, inside, bounds, dsep=DSEP, dtest=0.5, h=STEP, min_len=1.2, max_pts=4000):
    cs = dsep; grid = {}
    def key(x, y): return (int(math.floor(x / cs)), int(math.floor(y / cs)))
    def near(x, y, d, lid=None, lpts=None):
        i, j = key(x, y); d2 = d * d
        for a in (i - 1, i, i + 1):
            for b in (j - 1, j, j + 1):
                for (px, py, l) in grid.get((a, b), ()):
                    if (px - x) ** 2 + (py - y) ** 2 < d2: return True
        return False
    def trace1(x, y, sgn, own):
        pts = []; vx0, vy0 = F(x, y); vx0, vy0 = vx0 * sgn, vy0 * sgn; px_, py_ = vx0, vy0
        for _ in range(max_pts):
            vx, vy = F(x, y)
            if vx * px_ + vy * py_ < 0: vx, vy = -vx, -vy
            mx, my = x + vx * h / 2, y + vy * h / 2                     # midpoint (RK2)
            wx, wy = F(mx, my)
            if wx * vx + wy * vy < 0: wx, wy = -wx, -wy
            nx, ny = x + wx * h, y + wy * h
            if not inside(nx, ny) or near(nx, ny, dsep * dtest): break
            # own line: stop on a loop (closer than dtest to a point traced > 8 steps ago)
            if len(own) > 12 and any((ox - nx) ** 2 + (oy - ny) ** 2 < (dsep * dtest) ** 2 for ox, oy in own[:-10][-400:]): break
            pts.append((nx, ny)); own.append((nx, ny)); x, y = nx, ny; px_, py_ = wx, wy
        return pts
    def line_from(x, y):
        if not inside(x, y) or near(x, y, dsep * 0.98): return None
        own = [(x, y)]
        f = trace1(x, y, 1, own); b = trace1(x, y, -1, own)
        pts = b[::-1] + [(x, y)] + f
        L = sum(math.hypot(q[0] - p[0], q[1] - p[1]) for p, q in zip(pts, pts[1:]))
        if L < min_len: return None
        return pts
    lines = []
    def add(pts):
        lid = len(lines); lines.append(pts)
        for (x, y) in pts: grid.setdefault(key(x, y), []).append((x, y, lid))
    x0, y0, x1, y1 = bounds
    seeds = [((x0 + x1) / 2, (y0 + y1) / 2)]
    # global seed lattice so every region is reached (singular points of the field stop the queue otherwise)
    lattice = [(x, y) for y in np.arange(y0, y1, dsep * 4) for x in np.arange(x0, x1, dsep * 4)]
    li = 0; qi = 0
    while True:
        if qi < len(lines):
            pts = lines[qi]; qi += 1
            for k in range(0, len(pts), 2):
                if k + 1 >= len(pts): break
                (ax, ay), (bx, by) = pts[k], pts[k + 1]; dl = math.hypot(bx - ax, by - ay) or 1
                nx, ny = -(by - ay) / dl, (bx - ax) / dl
                for s in (1, -1):
                    p = line_from(ax + s * nx * dsep, ay + s * ny * dsep)
                    if p: add(p)
            continue
        if seeds:
            p = line_from(*seeds.pop());
            if p: add(p)
            continue
        if li < len(lattice):
            p = line_from(*lattice[li]); li += 1
            if p: add(p)
            continue
        break
    return lines

# ------------------------------------------------------------------ build
def build(img):
    a = np.asarray(img.convert("RGB")).astype(float); H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]; d = np.hypot(xx - CX, yy - CY)
    inside_px = d < RPX - 1
    fig = (np.abs(xx - 725) < 92) & (yy > 300)                   # licensed figure + pole top: never traced
    disc = Point(0, MCY).buffer(RMM, 360)
    vis = []
    # ---- tone map (ground): smoothed close-up -> nearest ground tone; figure pixels take the nearest traced tone
    sm = np.stack([ndi.gaussian_filter(a[..., i], 3.0) for i in range(3)], -1)
    keys = list(GROUND); P = np.stack([lab(GROUND[k]) for k in keys]); Lsm = TR.lab_img(sm)
    best = np.argmin(((Lsm[:, :, None, :] - P[None, None]) ** 2).sum(-1), -1)
    blue = (a[..., 2] > a[..., 0] + 8) | (a.mean(2) < 80)
    bad = fig | blue | ~inside_px
    # hidden pixels (figure, cloud tails over the moon): tone from the surrounding moon (normalised convolution, 25 px)
    ok = (~bad).astype(float); sm2 = np.stack([ndi.gaussian_filter(a[..., i] * ok, 25) for i in range(3)], -1) / (ndi.gaussian_filter(ok, 25)[..., None] + 1e-6)
    best2 = np.argmin(((TR.lab_img(sm2)[:, :, None, :] - P[None, None]) ** 2).sum(-1), -1)
    best = np.where(bad, best2, best)
    best = ndi.median_filter(best, size=9)
    # ---- flow rows
    th, coh = field(a)
    F = Field(th, fig | blue)
    inside = lambda x, y: (x * x + (y - MCY) ** 2) < (RMM - 0.4) ** 2
    rows = streamlines(F, inside, (-RMM, MCY - RMM, RMM, MCY + RMM))
    ML = MultiLineString([r for r in rows if len(r) > 1])
    n_rows = len(rows); row_len = ML.length
    for i, k in enumerate(keys):
        g = TA_map(TR.polys_of((best == i) & inside_px, 1, (0, 0, W, H), 40)).buffer(0.6).buffer(-0.6)
        g = g.buffer(0.3).intersection(disc)                       # tones overlap 0.3 mm: no fabric between them
        for p in polys(g):
            if p.area < 0.6: continue
            rr = ML.intersection(p.buffer(0.15))
            r = R(k, p, "tatami", 0, CODE[k]); r["under"] = True; r["rows"] = rr; vis.append(r)
    cov = unary_union([r["geom"] for r in vis])
    for p in polys(disc.buffer(-1.0).difference(cov).buffer(0.35).intersection(disc)):   # pixel islands dropped by every tone
        if p.area < 0.2: continue
        r = R("m2", p, "tatami", 0, CODE["m2"]); r["under"] = True; r["rows"] = ML.intersection(p.buffer(0.15)); vis.append(r)
    vis.append(R("m3", disc.difference(disc.buffer(-2.2)), "satin", ("radial", 0.0, MCY), "MN-warm"))
    # ---- star craters: silhouettes TRACED from the close-up (grey-green pixels within 1.15 r of each star centre; LESSONS
    # A14 — no generated star shapes), pale centre traced (bright pixels near the centre), dark spike lines traced
    starg = []
    smc = np.stack([ndi.gaussian_filter(a[..., i], 1.2) for i in range(3)], -1)
    greym = ((smc[..., 0] - smc[..., 2]) < 62) & (smc.mean(2) < 208) & ~blue & ~fig
    for (sx, sy, sr, n, rot) in STARS:
        X0, Y0 = (float(v) for v in to_mm(sx, sy))
        win = (np.hypot(xx - sx, yy - sy) < sr * 1.15)
        m = morphology.binary_opening(greym & win, morphology.disk(1))
        lab_, nl = ndi.label(m)
        if nl == 0: continue
        cen = np.hypot(xx - sx, yy - sy) < sr * 0.45
        k_ = np.bincount(lab_[cen & (lab_ > 0)]).argmax() if (cen & (lab_ > 0)).any() else np.bincount(lab_[lab_ > 0]).argmax()
        m = ndi.binary_fill_holes(lab_ == k_)
        st = TA_map(TR.polys_of(m, 1, (0, 0, W, H), 20, simplify=0.3)).buffer(0.3).buffer(-0.3).intersection(disc.buffer(-2.5))
        if st.is_empty: continue
        starg.append(st)
        vis.append(R("m5", st, "satin", ("radial", X0, Y0), "MN-mare"))
        dk = TR.dark_lines(img, (int(sx - sr * 1.2), int(sy - sr * 1.2), int(sx + sr * 1.2), int(sy + sr * 1.2)), size=7, thr=26, min_len_px=9,
                           mask=lambda X_, Y_: m[np.clip(Y_, 0, H - 1), np.clip(X_, 0, W - 1)])
        for l in dk:
            g_ = TA_map(l).intersection(st.buffer(-0.6))
            if not g_.is_empty and g_.length > 1.5:
                r_ = R("p3", g_.buffer(0.3), "run", None, "MN-ray"); r_["top"] = True; vis.append(r_)
        pale = ~greym & (smc.mean(2) > 150) & (np.hypot(xx - sx, yy - sy) < sr * 0.32) & ~blue      # the warm centre inside the grey star
        pl_, npl = ndi.label(pale)
        if npl:
            kk = np.bincount(pl_[pl_ > 0]).argmax(); pm = ndi.binary_fill_holes(pl_ == kk)
            cg = TA_map(TR.polys_of(pm, 1, (0, 0, W, H), 6, simplify=0.2)).buffer(0.3).buffer(-0.3)
            for p in polys(cg):
                if p.area < 1.0: continue
                r_ = R("m1", p, "satin", ("radial", p.centroid.x, p.centroid.y), "MN-hl"); r_["top"] = True; vis.append(r_)
                r_ = R("m4", p.exterior.buffer(0.3), "run", None, "MN-ray"); r_["top"] = True; vis.append(r_)
    stars = unary_union(starg)
    # ---- raised oval cells (bright isotropic blobs of the close-up)
    from skimage.feature import peak_local_max, hessian_matrix, hessian_matrix_eigvals
    lum = a.mean(2)
    allowed = inside_px & ~fig & ~ndi.binary_dilation(blue, iterations=4) & (d < RPX - 6)
    # cells only where the close-up has them: density of the dark gaps between cells (the smooth swirl ground has none)
    loc = ndi.uniform_filter(lum, 25); gap = ndi.uniform_filter(((lum < loc - 22) & ~blue).astype(float), 21)
    allowed &= gap >= 0.10
    cells = []
    for sg in (5.0, 3.5):
        Hm = hessian_matrix(lum, sigma=sg, order="rc", use_gaussian_derivatives=True); e = hessian_matrix_eigvals(Hm)
        st_ = np.where(e[0] < 0, -e[0] * sg * sg, 0)
        for y, x in peak_local_max(st_, min_distance=int(sg * 1.6), threshold_abs=5, labels=allowed.astype(int)):
            if any(math.hypot(x - cx_, y - cy_) < (sg + s_) * 1.2 for cx_, cy_, s_, _, _ in cells): continue
            hrr, hrc, hcc = Hm[0][y, x], Hm[1][y, x], Hm[2][y, x]
            w_, v_ = np.linalg.eigh(np.array([[hrr, hrc], [hrc, hcc]]))
            vr, vc = v_[:, 1]; rot = math.degrees(math.atan2(vr, vc))
            el = min(1.8, math.sqrt(max(w_[0], -1e9) / min(w_[1], -1e-9))) if w_[1] < 0 else 1.6
            cells.append((x, y, sg, rot, el))
    CT = {"m1": GROUND["m1"], "m2": GROUND["m2"], "m3": GROUND["m3"], "m4": GROUND["m4"]}
    n_cell = 0
    for x, y, sg, rot, el in cells:
        X0, Y0 = (float(v) for v in to_mm(x, y))
        if stars.buffer(0.8).contains(Point(X0, Y0)): continue        # star craters stay clean grey-green
        if any(math.hypot(x - sx, y - sy) < 1.5 * sr for (sx, sy, sr, _, _) in STARS[1:]): continue   # close-up: smooth ground round stars 2 + 3
        b_ = max(1.0, sg * 1.45 * K); a_ = b_ * el
        ell = affinity.rotate(affinity.scale(Point(X0, Y0).buffer(1, 24), a_, b_), rot, origin=(X0, Y0)).intersection(disc.buffer(-1.5))
        if ell.is_empty or ell.area < 1.2: continue
        r_ = int(max(2, sg)); col = a[max(0, y - r_):y + r_ + 1, max(0, x - r_):x + r_ + 1].reshape(-1, 3).mean(0)
        L = lab(col); tone = min(CT, key=lambda k: float(((lab(CT[k]) - L) ** 2).sum()))
        vis.append(R(tone, ell, "satin", rot + 90, CODE[tone]))
        ring = ell.exterior
        lit = ring.intersection(box(X0 - 40, Y0 - 40, X0 + 0.25 * a_, Y0 + 0.25 * b_))       # upper-left: light rim
        shd = ring.intersection(box(X0 - 0.25 * a_, Y0 - 0.25 * b_, X0 + 40, Y0 + 40))       # lower-right: shadow gap
        if not lit.is_empty and lit.length > 1.5:
            vis.append(R("m1" if tone != "m1" else "m2", lit.buffer(0.3, cap_style="round"), "run", None, "MN-ray"))
        if not shd.is_empty and shd.length > 1.5:
            vis.append(R("m4" if tone in ("m1", "m2") else "m5", shd.buffer(0.3, cap_style="round"), "run", None, "MN-ray"))
        n_cell += 1
    # painter order: ground (under), rim, stars, cells + their rims on top
    rank = lambda r: 0 if r.get("under") else (1 if r["grp"] == "MN-warm" and isinstance(r["ang"], tuple) and r["ang"][1] == 0.0 and r["ang"][2] == MCY else 2)
    vis.sort(key=rank)
    stats = dict(rows=n_rows, row_mm=round(row_len), cells=n_cell, stars=len(STARS))
    return vis, disc, stats

if __name__ == "__main__":
    import time, pickle
    from PIL import Image
    t = time.time(); v, disc, s = build(Image.open("inputs/closeups/closeup_back.png"))
    print(s, len(v), f"{time.time()-t:.0f}s")
    pickle.dump(v, open("out/_moon3_test.pkl", "wb"))
