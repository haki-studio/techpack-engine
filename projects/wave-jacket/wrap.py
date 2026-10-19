"""Seam-true wrap for the wave jacket (founder, 19 Oct 2026: "the wave must look seamless").

Everything is driven by the PATTERN seam curves of the size (pattern.draft), so a revised block re-runs as is.

1. HarmonicSleeveMap: render sleeve half (armhole curve drawn back into the render, inner edge, cuff, outer fold) ->
   sleeve pattern half (cap half, underarm seam, cuff half, centre line). Boundary points correspond by SEAM LENGTH:
   a render armhole point lands on the cap at the same fraction of the seam as the body map puts it on the body armhole
   (cap ease spread evenly), so art crossing the armhole on the render meets itself across the sewn seam. The interior is
   a discrete harmonic map (Laplace, Dirichlet boundary), fold-free for a convex target; det J is checked.
2. SEAMS: every sewn seam with art near it (armholes, sides, shoulders, sleeve underarm) + the sleeve centre line where
   the back view's half meets the front view's half. 'view' seams are continuous in one render view (armhole: body and
   sleeve come from the same image); 'silhouette' seams sit on the render's outline in two different views.
3. Silhouette seams: each side is stretched along the seam normal so its art reaches the seam (the trace drops the
   render's edge shading, ~10-20 mm), then the follower side is warped ALONG the seam (dynamic time warping of the colour
   sequence 1.5 mm inside the seam) so stripes of the same tone meet; the warp fades out over WARP_W mm.
4. Overflow: every motif belongs to ONE piece (the one whose render region holds its anchor); the part beyond that
   piece's seam is carried across into the partner piece by seam coordinates (arc fraction s, distance e beyond the seam
   -> e inside the partner), so curls that straddle a seam continue on the other side.
5. Match marks: where art meets each seam (start / end of every art run along the seam), on both pieces.
"""
import functools, math
import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely.validation import make_valid
from shapely import affinity
import mockmap as MM

CODE = {"BK": "B01", "FR": "F02", "FL": "F01", "SR": "S01", "SL": "S02"}
GAP = 3.0            # art stops this far short of every seam line
STRETCH_D = 60.0     # silhouette stretch acts within this distance of the seam
WARP_W = 40.0        # DTW warp fades out over this distance from the seam
WARP_MAX = 30.0      # max shift along the seam (mm)

def _arc(pts):
    pts = np.asarray(pts, float); return np.r_[0, np.cumsum(np.hypot(*np.diff(pts, axis=0).T))]

def _resample(pts, u):
    pts = np.asarray(pts, float); d = _arc(pts); t = d / d[-1]
    return np.c_[np.interp(u, t, pts[:, 0]), np.interp(u, t, pts[:, 1])]

def edge(size, P, name):
    g, mt = MM.draft(size); return [tuple(map(float, p)) for p in next(e for e in g[CODE[P]].edges if e.name == name).pts]

def cap_halves(size, P):
    """(back half, front half) of the cap, each from the cap notch (top) down to its underarm point"""
    g, mt = MM.draft(size); cap = np.asarray(edge(size, P, "cap"), float); d = _arc(cap)
    cb = mt["cap_b"]; k = np.searchsorted(d, cb)
    notch = cap[k - 1] + (cap[k] - cap[k - 1]) * (cb - d[k - 1]) / max(d[k] - d[k - 1], 1e-9)
    back = np.r_[cap[:k], [notch]][::-1]; front = np.r_[[notch], cap[k:]]
    return back, front

# ------------------------------------------------------------------ 1. harmonic sleeve map
class HarmonicSleeveMap:
    def __init__(self, view, side, size="M", h=1.0):
        from scipy import sparse
        from scipy.sparse.linalg import spsolve
        from scipy import ndimage as ndi
        self.view, self.side, self.size = view, side, size
        piece, sgn = MM.HALF[(view, side)]; self.piece, self.sgn = piece, sgn
        P = "SR" if piece == "S01" else "SL"; self.P = P
        f, finv = MM.body_tf(view, size); g, mt = MM.draft(size)
        arm_mm = np.asarray(MM.armhole_mm(view, side, size), float)            # shoulder point -> underarm
        ax, ay = finv(arm_mm[:, 0], arm_mm[:, 1]); arm_px = np.c_[ax, ay]
        co, ci = MM.CUFF_PX[(view, side)]
        oc = MM.outer_contour(view, side, arm_px[0][1] + 25, co[1] - 8)
        outer = np.asarray([tuple(arm_px[0])] + oc + [tuple(co)], float)        # shoulder -> outer cuff corner
        # source boundary (render px), counter-clockwise order not needed: 4 sides with their own parameter u in [0,1]
        u_arm = _arc(arm_mm) / _arc(arm_mm)[-1]                                  # SEAM LENGTH on the body armhole
        S = [(arm_px, u_arm),
             (np.asarray([arm_px[-1], ci], float), None),
             (np.asarray([ci, co], float), None),
             (outer[::-1], None)]                                               # outer cuff corner -> shoulder
        back, front = cap_halves(size, P)
        capH = back if view == "back" else front                                # notch -> underarm (this half)
        ua = capH[-1]; W, Ww, Lu = mt["W"], mt["Ww"], mt["Lu"]
        cuffc = np.array([sgn * Ww, Lu]); cen = np.array([0.0, Lu])
        T = [capH, np.asarray([ua, cuffc]), np.asarray([cuffc, cen]), np.asarray([cen, capH[0]])]
        self.quad_px = Polygon(np.r_[arm_px, [ci], outer[::-1][:-1]]).buffer(0)
        self.target = Polygon(np.r_[capH, [cuffc], [cen]]).buffer(0)
        self.arm_px, self.capH = arm_px, capH
        segs = [LineString(s) for s, _ in S]
        def tgt(pt):
            dists = [sg.distance(Point(pt)) for sg in segs]; k = int(np.argmin(dists)); sg = segs[k]
            a = sg.project(Point(pt)); src, u = S[k]
            dpx = _arc(src)
            uu = np.interp(a, dpx, u) if u is not None else a / max(dpx[-1], 1e-9)
            return _resample(T[k], [uu])[0]
        self._tgt = tgt
        # grid
        b = self.quad_px.bounds; x0, y0 = b[0] - 3, b[1] - 3
        nx, ny = int((b[2] - x0) / h) + 4, int((b[3] - y0) / h) + 4
        XX, YY = np.meshgrid(x0 + np.arange(nx) * h, y0 + np.arange(ny) * h)
        import shapely
        inside = shapely.contains_xy(self.quad_px, XX.ravel(), YY.ravel()).reshape(XX.shape)
        idx = -np.ones(XX.shape, int); idx[inside] = np.arange(inside.sum())
        n = inside.sum(); rows, cols, vals = [], [], []; bx = np.zeros(n); by = np.zeros(n)
        bcache = {}
        iy, ix = np.nonzero(inside)
        for k in range(n):
            r, c = iy[k], ix[k]; rows.append(k); cols.append(k); vals.append(4.0)
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                rr, cc = r + dr, c + dc
                j = idx[rr, cc] if (0 <= rr < ny and 0 <= cc < nx) else -1
                if j >= 0: rows.append(k); cols.append(j); vals.append(-1.0)
                else:
                    key = (rr, cc)
                    if key not in bcache: bcache[key] = tgt((x0 + cc * h, y0 + rr * h))
                    t_ = bcache[key]; bx[k] += t_[0]; by[k] += t_[1]
        A = sparse.csr_matrix((vals, (rows, cols)), shape=(n, n))
        sx, sy = spsolve(A, bx), spsolve(A, by)
        GX = np.full(XX.shape, np.nan); GY = np.full(XX.shape, np.nan); GX[inside] = sx; GY[inside] = sy
        for (rr, cc), t_ in bcache.items():
            if 0 <= rr < ny and 0 <= cc < nx: GX[rr, cc], GY[rr, cc] = t_
        ok = ~np.isnan(GX)
        _, (ir, ic) = ndi.distance_transform_edt(~ok, return_indices=True)
        self.GX, self.GY = GX[ir, ic], GY[ir, ic]; self.x0, self.y0, self.h = x0, y0, h; self.inside = inside
        # fold check
        jx = np.gradient(self.GX, h); jy = np.gradient(self.GY, h)
        det = jx[1] * jy[0] - jx[0] * jy[1]
        dm = det[inside]; self.det_sign = float(np.sign(np.median(dm)))
        self.fold_frac = float((dm * self.det_sign <= 0).mean())
        self._inv = None
    def __call__(self, px, py):
        from scipy.ndimage import map_coordinates
        px = np.atleast_1d(np.asarray(px, float)); py = np.atleast_1d(np.asarray(py, float))
        c = [(py.ravel() - self.y0) / self.h, (px.ravel() - self.x0) / self.h]
        X = map_coordinates(self.GX, c, order=1, mode="nearest"); Y = map_coordinates(self.GY, c, order=1, mode="nearest")
        return X.reshape(px.shape), Y.reshape(py.shape)
    def jac(self, px, py, h=2.0):
        x0 = np.array(self(px, py)).ravel(); xa = np.array(self(px + h, py)).ravel(); xb = np.array(self(px, py + h)).ravel()
        return np.c_[(xa - x0) / h, (xb - x0) / h], x0
    def inv(self, Pm):
        if self._inv is None:
            from scipy.interpolate import LinearNDInterpolator
            m = self.inside; XX, YY = np.meshgrid(self.x0 + np.arange(m.shape[1]) * self.h, self.y0 + np.arange(m.shape[0]) * self.h)
            self._inv = LinearNDInterpolator(np.c_[self.GX[m], self.GY[m]], np.c_[XX[m], YY[m]])
        r = self._inv(np.atleast_2d(Pm)); return r

@functools.lru_cache(maxsize=None)
def sleeve_map(view, side, size="M"): return HarmonicSleeveMap(view, side, size)

# ------------------------------------------------------------------ 2. seams of a size (from the pattern)
@functools.lru_cache(maxsize=None)
def seams(size):
    """list of dict(name, kind, A=(P, pts), B=(P, pts)); A and B run the same way (s = 0 at the same seam end)"""
    out = []
    bk_sh_L = edge(size, "BK", "shoulder L"); bk_sh_R = edge(size, "BK", "shoulder R")[::-1]       # neck -> shoulder point
    for side, F, S, sh in (("L", "FL", "SL", bk_sh_L), ("R", "FR", "SR", bk_sh_R)):
        back, front = cap_halves(size, S)
        out.append(dict(name=f"armhole back {side}", kind="view", A=("BK", MM.armhole_mm("back", side, size)), B=(S, back)))
        out.append(dict(name=f"armhole front {side}", kind="view", A=(F, MM.armhole_mm("front", side, size)), B=(S, front)))
        top_down = lambda pts: pts if pts[0][1] <= pts[-1][1] else pts[::-1]          # both sides from the underarm down
        out.append(dict(name=f"side {side}", kind="silhouette", A=("BK", top_down(edge(size, "BK", f"side {side}"))), B=(F, top_down(edge(size, F, "side")))))
        out.append(dict(name=f"shoulder {side}", kind="silhouette", A=("BK", sh), B=(F, edge(size, F, "shoulder"))))
        ub = edge(size, S, "underarm back")[::-1]; uf = edge(size, S, "underarm front")                 # underarm point -> cuff
        out.append(dict(name=f"underarm {side}", kind="silhouette", A=(S, ub), B=(S, uf)))
        g, mt = MM.draft(size)
        out.append(dict(name=f"sleeve centre {side}", kind="internal", A=(S, [tuple(back[0]), (0.0, mt["Lu"])]), B=(S, [tuple(back[0]), (0.0, mt["Lu"])])))
    for s in out:
        L = LineString(s["A"][1]); s["len_A"] = L.length; s["len_B"] = LineString(s["B"][1]).length
    return out

def half_sign(size, P):
    """sleeve: sign of x of the back half (S01 back half x < 0, S02 back half x > 0)"""
    return MM.HALF[("back", "R" if P == "SR" else "L")][1]

class SeamSide:
    """seam coordinates on one side: point -> (s in [0,1], d signed: + = inside this side's art area)"""
    def __init__(self, size, seam, which):
        self.P, pts = seam[which]; self.line = LineString(pts); self.L = self.line.length; self.seam = seam; self.which = which
        import pieces as PC
        self.panel = PC.panel(size, self.P)
        if seam["kind"] == "internal":
            sg = half_sign(size, self.P) * (1 if which == "A" else -1); self.region = box(0, -1e4, 1e4, 1e4) if sg > 0 else box(-1e4, -1e4, 0, 1e4)
            self.region = self.region.intersection(self.panel)
        elif seam["kind"] == "silhouette" and seam["A"][0] == seam["B"][0]:          # underarm: back half / front half
            sg = half_sign(size, self.P) * (1 if which == "A" else -1)
            self.region = (box(0, -1e4, 1e4, 1e4) if sg > 0 else box(-1e4, -1e4, 0, 1e4)).intersection(self.panel)
        else: self.region = self.panel
    def normal_in(self, s):
        if len(self.line.coords) == 2:                                   # straight seam: one normal
            if getattr(self, "_n", None) is None: self._n = self._normal(0.5)
            return self._n
        return self._normal(s)
    def _normal(self, s):
        from shapely import prepared
        if getattr(self, "_rb", None) is None: self._rb = prepared.prep(self.region.buffer(0.01))
        a = self.line.interpolate(max(0, s - 0.002), normalized=True); b = self.line.interpolate(min(1, s + 0.002), normalized=True)
        t = np.array([b.x - a.x, b.y - a.y]); t /= max(np.hypot(*t), 1e-9); n = np.array([-t[1], t[0]])
        c = self.line.interpolate(s, normalized=True)
        if not self._rb.contains(Point(c.x + n[0] * 2.0, c.y + n[1] * 2.0)): n = -n
        return n
    def point(self, s, d):
        c = self.line.interpolate(s, normalized=True); n = self.normal_in(s); return (c.x + n[0] * d, c.y + n[1] * d)

# ------------------------------------------------------------------ geometry helpers
def polys_of(g):
    if g is None or g.is_empty: return []
    return [g] if g.geom_type == "Polygon" else [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]

def map_pts(geom, fn, densify=0.8):
    if geom is None or geom.is_empty: return geom
    g = MM.map_geom(geom, fn, densify=densify)
    try: return make_valid(g).buffer(0)
    except Exception: return g.buffer(0)

def _sd(side, X, Y):
    """vectorised (s, d) for points: s = projection fraction, d = signed distance (+ inside) for a STRAIGHT seam line"""
    p0 = np.array(side.line.coords[0]); p1 = np.array(side.line.coords[-1]); t = p1 - p0; L = np.hypot(*t); t = t / L
    n = side.normal_in(0.5); rx, ry = X - p0[0], Y - p0[1]
    return (rx * t[0] + ry * t[1]) / L, rx * n[0] + ry * n[1], p0, t, n, L

# ------------------------------------------------------------------ 3a. silhouette stretch
G_MAX = 35.0
def stretch(items, side, unit_c, gap=GAP + 1.0, row=5.0):
    """move one side's art toward a straight seam row by row: the render's outline (and the trace's dropped edge shading)
    leaves the art g(s) short of the seam, g varying along it (slanted outline). g(s) = innermost art per 5 mm row (rows
    without art within STRETCH_D: interpolated from rows <= 30 mm away, else no stretch), capped G_MAX, median-smoothed;
    d in [g(s), D] -> [gap, D]. Returns (items, median g)."""
    from scipy.ndimage import median_filter
    D = STRETCH_D
    near = [r for r in items if r["geom"].intersects(side.region) and side.line.distance(r["geom"]) < D]
    if not near: return items, 0.0
    U = unary_union([r["geom"] for r in near]).intersection(side.region.buffer(0.5))
    n_rows = max(1, int(np.ceil(side.L / row))); gs = np.full(n_rows, np.nan)
    nrm = side.normal_in(0.5)
    for k in range(n_rows):
        a = side.point(k * row / side.L, 0); b = side.point(min((k + 1) * row, side.L) / side.L, 0)
        strip = Polygon([a, b, (b[0] + nrm[0] * D, b[1] + nrm[1] * D), (a[0] + nrm[0] * D, a[1] + nrm[1] * D)])
        q = U.intersection(strip)
        if not q.is_empty and q.area > 1.0: gs[k] = min(side.line.distance(q), G_MAX)
    ok = ~np.isnan(gs)
    if not ok.any(): return items, 0.0
    idx = np.arange(n_rows); filled = np.interp(idx, idx[ok], gs[ok])
    dist_ok = np.array([np.min(np.abs(idx[ok] - i)) for i in idx]) * row
    g_s = np.where(dist_ok <= 30.0, filled, gap)
    g_s = median_filter(g_s, size=5, mode="nearest"); g_s = np.maximum(g_s, gap)
    centres = (idx + 0.5) * row / side.L
    def fn(x, y):
        X, Y = np.asarray(x, float), np.asarray(y, float); s, d, p0, t, n, L = _sd(side, X, Y)
        g = np.interp(np.clip(s, 0, 1), centres, g_s)
        w = np.clip(np.minimum(s, 1 - s) * L / 15.0, 0, 1)
        dn = np.where(d >= g, D - (D - d) * (D - gap) / np.maximum(D - g, 1e-6), gap + (d - g) * 0.0)
        dd = np.where((d > -1) & (d < D), (dn - d) * w, 0.0)
        return X + n[0] * dd, Y + n[1] * dd
    out = []
    for r in items:
        if not r["geom"].intersects(side.region) or side.line.distance(r["geom"]) >= D: out.append(r); continue
        if r.get("unit"):
            c = unit_c[r["unit"]]; nx_, ny_ = fn(np.array([c[0]]), np.array([c[1]]))
            out.append(dict(r, geom=affinity.translate(r["geom"], float(nx_[0] - c[0]), float(ny_[0] - c[1]))))
        else:
            gm = map_pts(r["geom"], fn)
            if not gm.is_empty: out.append(dict(r, geom=gm))
    return out, float(np.median(g_s))

# ------------------------------------------------------------------ 3b. DTW warp along the seam
TONES = ["b0", "b1", "b2", "b3", "b4", "b5", "g1", "w3", "w1"]
def labels(items, side, d0, step=1.0):
    import shapely
    geoms = [r["geom"] for r in items]; tree = shapely.STRtree(geoms) if geoms else None
    out = []
    for s0 in np.arange(0, side.L + 1e-6, step):
        p = Point(side.point(min(s0 / side.L, 1.0), d0)); best = None
        if tree is not None:
            for j in tree.query(p, predicate="intersects"):
                r = items[int(j)]
                if best is None or r["z"] > best["z"]: best = r
        out.append(best["col"] if best else None)
    return out

def _cost(a, b):
    if a == b: return 0.0
    if a is None or b is None: return 1.0
    ia, ib = (TONES.index(a) if a in TONES else 4), (TONES.index(b) if b in TONES else 4)
    return 0.35 + 0.08 * abs(ia - ib)

def dtw_shift(la, lb, band=int(WARP_MAX)):
    n, m = len(la), len(lb); INF = 1e18
    D = np.full((n + 1, m + 1), INF); D[0, 0] = 0
    for i in range(1, n + 1):
        lo, hi = max(1, i - band), min(m, i + band)
        for j in range(lo, hi + 1):
            D[i, j] = _cost(la[i - 1], lb[j - 1]) + min(D[i - 1, j], D[i, j - 1], D[i - 1, j - 1])
    i, j = n, m; pairs = []
    while i > 0 and j > 0:
        pairs.append((i - 1, j - 1)); k = np.argmin([D[i - 1, j - 1], D[i - 1, j], D[i, j - 1]])
        if k == 0: i, j = i - 1, j - 1
        elif k == 1: i -= 1
        else: j -= 1
    acc = {}
    for a, b in pairs: acc.setdefault(b, []).append(a)
    sa = np.array([np.mean(acc.get(j, [j])) for j in range(m)], float)
    from scipy.ndimage import gaussian_filter1d
    sh = gaussian_filter1d(sa - np.arange(m), 4.0); return np.clip(sh, -WARP_MAX, WARP_MAX)

def warp(items, side, shift, unit_c):
    """shift B's art along the seam by shift(s) (mm), fading to 0 at WARP_W from the seam"""
    L = side.L; ss = np.linspace(0, 1, len(shift))
    def fn(x, y):
        X, Y = np.asarray(x, float), np.asarray(y, float); s, d, p0, t, n, L_ = _sd(side, X, Y)
        w = np.clip(1 - d / WARP_W, 0, 1) * (d > -2) * np.clip(np.minimum(s, 1 - s) * L / 10.0, 0, 1)
        ds = np.interp(np.clip(s, 0, 1), ss, shift) * w
        return X + t[0] * ds, Y + t[1] * ds
    out = []
    for r in items:
        if not r["geom"].intersects(side.region) or side.line.distance(r["geom"]) >= WARP_W: out.append(r); continue
        if r.get("unit"):
            c = unit_c[r["unit"]]; nx_, ny_ = fn(np.array([c[0]]), np.array([c[1]]))
            out.append(dict(r, geom=affinity.translate(r["geom"], float(nx_[0] - c[0]), float(ny_[0] - c[1]))))
        else:
            gm = map_pts(r["geom"], fn)
            if not gm.is_empty: out.append(dict(r, geom=gm))
    return out

def art_match(la, lb):
    """share of seam positions with art on either side where both sides carry the SAME tone"""
    both = [(x, y) for x, y in zip(la, lb) if x is not None or y is not None]
    return float(np.mean([x == y for x, y in both])) if both else 1.0

CONT_E = 28.0
def continue_across(art, src, dst, E=CONT_E):
    """every stripe / rope line of `src` that reaches the seam continues straight across it into `dst` (same angle to the
    seam, the band part translated along its own direction) and tapers to a point over E mm: no stripe ends in a hard
    cut at a seam, whatever the other view shows there. Added above dst's own stripes (z + 0.5). Returns count."""
    near = src.line.buffer(E).intersection(src.region)
    n = 0; L = src.L
    for r in list(art[src.P]):
        if r["grp"] not in ("WV", "RP") or not r["geom"].intersects(near): continue
        q_all = r["geom"].intersection(near)
        for q in polys_of(q_all):
            if q.area < 2.0 or src.line.distance(q) > GAP + 1.5: continue
            X, Y = np.asarray(q.exterior.coords).T; s_, d_, p0, t, nn, L_ = _sd(src, X, Y)
            S, Dd = s_ * L, d_
            M = np.c_[S - S.mean(), Dd - Dd.mean()]
            w, V = np.linalg.eigh(M.T @ M); v = V[:, -1]
            if v[1] > 0: v = -v                                           # pointing toward the seam (d decreasing)
            if abs(v[1]) < 0.3: continue                                   # runs along the seam: does not cross it
            k = E / abs(v[1])
            def fn(x, y, v=v, k=k):
                X_, Y_ = np.asarray(x, float), np.asarray(y, float)
                s2, d2, *_ = _sd(src, X_, Y_)
                Se = s2 * L + k * v[0]; depth = np.clip(-(d2 + k * v[1]), -1.0, E + 1)
                frac = np.clip(Se / L, -0.05, 1.05)
                base = np.array([dst.point(min(max(f_, 0), 1), 0) for f_ in frac.ravel()])
                tang = np.array(dst.line.coords[-1]) - np.array(dst.line.coords[0]); tang = tang / np.hypot(*tang)
                over = (frac.ravel() - np.clip(frac.ravel(), 0, 1)) * dst.L
                nrm = np.array([dst.normal_in(min(max(f_, 0), 1)) for f_ in frac.ravel()])
                out = base + nrm * depth.ravel()[:, None] + tang[None, :] * over[:, None]
                return out[:, 0].reshape(X_.shape), out[:, 1].reshape(Y_.shape)
            # taper wedge in dst seam coords: crossing interval at depth 0 -> point at depth E along the stripe direction
            on = q.intersection(src.line.buffer(GAP + 1.6))
            if on.is_empty: continue
            ss = [src.line.project(Point(c)) for g_ in polys_of(on) for c in g_.exterior.coords]
            s0, s1 = min(ss), max(ss); sc = 0.5 * (s0 + s1); slope = v[0] / abs(v[1])
            tip = sc + slope * E
            wedge_sd = [(s0 - 1.0, -1.0), (s1 + 1.0, -1.0), (tip + 0.3, E), (tip - 0.3, E)]
            wedge = Polygon([dst.point(min(max(a_ / L, 0), 1), b_) for a_, b_ in wedge_sd]).buffer(0)
            gm = map_pts(q, fn, densify=1.5)
            if gm is None or gm.is_empty: continue
            gm = gm.intersection(wedge).intersection(dst.region)
            for p in polys_of(gm):
                if p.area > 1.0:
                    art[dst.P].append(dict(r, geom=p, z=r["z"] + 0.5, unit=None)); n += 1
    return n

def unit_centres(items):
    acc = {}
    for r in items:
        if r.get("unit"): acc.setdefault(r["unit"], []).append(r["geom"])
    return {u: unary_union(g).centroid.coords[0] for u, g in acc.items()}

def silhouettes(art, size):
    """stretch both sides of every silhouette / internal seam, then DTW-warp side B onto side A. Edits art {P: items}."""
    log = {}
    for sm in seams(size):
        if sm["kind"] not in ("silhouette", "internal"): continue
        A, B = SeamSide(size, sm, "A"), SeamSide(size, sm, "B")
        gs = []
        for sd in (A, B):
            its = art[sd.P]; art[sd.P], g = stretch(its, sd, unit_centres(its)); gs.append(round(g, 1))
        keys = sorted({r["col"] for P_ in art for r in art[P_] if r["grp"] in BAND_GRPS})
        q = quilt(art, A, B, keys) if sm["kind"] != "silhouette" or sm["name"].split()[0] != "shoulder" else dict(cut=None)
        log[sm["name"]] = dict(gap=gs, **q)
    return log

# ------------------------------------------------------------------ 4. overflow transfer
def transfer(art, size):
    """parts of each piece's items beyond one of its seams -> partner piece (seam coordinates). Edits art in place."""
    import pieces as PC
    sides = []
    for sm in seams(size):
        if sm["kind"] == "internal": continue
        sides.append((SeamSide(size, sm, "A"), SeamSide(size, sm, "B"))); sides.append((sides[-1][1], sides[-1][0]))
    moved = {}
    add = {P: [] for P in art}
    for P, its in art.items():
        pan = PC.panel(size, P); mine = [(a, b) for a, b in sides if a.P == P]
        if not mine: continue
        keep = []
        for r in its:
            g = r["geom"]
            if pan.buffer(0.01).contains(g): keep.append(r); continue
            ov = g.difference(pan)
            inside_part = g.intersection(pan)
            if not inside_part.is_empty: keep.append(dict(r, geom=inside_part.buffer(0)))
            for p in (ov.geoms if hasattr(ov, "geoms") else [ov]):
                if p.is_empty or p.area < 0.3: continue
                # the seam this part crossed: nearest seam line of this piece (sleeve underarm: matching half)
                a, b = min(mine, key=lambda ab: ab[0].line.distance(p))
                if a.line.distance(p) > 2.0: continue                                  # beyond hem / CF / neck / cuff: dropped
                def fn(x, y, a=a, b=b):
                    X, Y = np.asarray(x, float), np.asarray(y, float); outX, outY = np.empty_like(X), np.empty_like(Y)
                    for k in range(X.size):
                        q = Point(X.flat[k], Y.flat[k]); s = a.line.project(q, normalized=True); e = a.line.distance(q)
                        sb = s if a.which == "A" or b.which == "A" else s
                        px_, py_ = b.point(sb, e); outX.flat[k], outY.flat[k] = px_, py_
                    return outX, outY
                gm = map_pts(p, fn, densify=0.6)
                if gm is None or gm.is_empty: continue
                add[b.P].append(dict(r, geom=gm, unit=(r.get("unit") or "") + f">{b.P}", z=r["z"] + 0.00001))
                moved[(P, b.P)] = moved.get((P, b.P), 0) + 1
        art[P] = keep
    for P, rs in add.items(): art[P] = art[P] + rs
    return {f"{a}->{b}": n for (a, b), n in moved.items()}

# ------------------------------------------------------------------ 5. match marks
def match_marks(vis, size, min_run=6.0):
    """{seam name: [s_mm, ...]} where art starts / ends along the seam (sampled GAP+1 mm inside side A, and side B)"""
    out = {}
    for sm in seams(size):
        if sm["kind"] == "internal": continue
        A, B = SeamSide(size, sm, "A"), SeamSide(size, sm, "B"); marks = []
        for sd in (A, B):
            its = [r for r in vis[sd.P] if r["geom"].intersects(sd.region)]
            lab = labels(its, sd, GAP + 1.0)
            run = None
            for k, l in enumerate(lab + [None]):
                if l is not None and run is None: run = k
                if l is None and run is not None:
                    if k - run >= min_run: marks += [run, k - 1]
                    run = None
        # merge marks closer than 4 mm
        ms = sorted(marks); mm_ = []
        for m in ms:
            if not mm_ or m - mm_[-1] > 4: mm_.append(m)
        out[sm["name"]] = dict(s_mm=[float(m) for m in mm_], A=sm["A"][0], B=sm["B"][0], len_A=round(A.L, 1), len_B=round(B.L, 1),
                              pts_A=[A.point(min(m / A.L, 1), 0) for m in mm_], pts_B=[B.point(min(m * B.L / A.L / B.L, 1), 0) for m in mm_])
    return out

# ------------------------------------------------------------------ 3c. seam quilting (Rev B, replaces DTW + tails)
Q_PPM = 2.0          # px per mm of the unrolled seam grid
Q_W = 60.0           # follower band depth (mm) in which the cut is searched
Q_DMIN = 10.0        # the continuation runs at least this far into the follower
BAND_GRPS = ("WV", "RP")

def _label_raster(items, bb, ppm, keys):
    """tone label image (0 = fabric, k = keys[k-1]) of WV/RP items, top z wins, in piece coords"""
    from PIL import Image, ImageDraw
    W, H = int((bb[2] - bb[0]) * ppm) + 2, int((bb[3] - bb[1]) * ppm) + 2
    im = Image.new("I", (W, H), 0); d = ImageDraw.Draw(im)
    for r in sorted([r for r in items if r["grp"] in BAND_GRPS], key=lambda r: r["z"]):
        k = keys.index(r["col"]) + 1
        for q in polys_of(r["geom"]):
            d.polygon([((x - bb[0]) * ppm, (y - bb[1]) * ppm) for x, y in q.exterior.coords], fill=k)
            for h in q.interiors: d.polygon([((x - bb[0]) * ppm, (y - bb[1]) * ppm) for x, y in h.coords], fill=0)
    return np.asarray(im, np.int32)

def _unroll(lab, bb, ppm, side, ss, ds):
    from scipy.ndimage import map_coordinates
    s, d, p0, t, n, L = _sd(side, np.array([0.0]), np.array([0.0]))
    S, D = np.meshgrid(ss, ds)                                    # rows = depth, cols = arc
    X = p0[0] + S * t[0] + D * n[0]; Y = p0[1] + S * t[1] + D * n[1]
    return map_coordinates(lab, [(Y - bb[1]) * ppm, (X - bb[0]) * ppm], order=0, mode="constant", cval=0)

def quilt(art, A, B, keys):
    """B's band = straight continuation of A's seam colours up to a min-mismatch cut, B's own art beyond. Returns info."""
    from scipy.ndimage import gaussian_filter, gaussian_filter1d
    import trace as TR
    L = min(A.L, B.L); ppm = Q_PPM
    ss = np.arange(0, L, 1 / ppm); ds = np.arange(0, Q_W, 1 / ppm)
    bbA = A.region.bounds; bbB = B.region.bounds
    LA = _unroll(_label_raster(art[A.P], bbA, ppm, keys), bbA, ppm, A, ss * A.L / L, ds)
    LB = _unroll(_label_raster(art[B.P], bbB, ppm, keys), bbB, ppm, B, ss * B.L / L, ds)
    if not (LA[: int(15 * ppm)] > 0).any(): return dict(cut=None)
    # stripe direction on A near the seam (structure tensor of the tone image), pointing toward the seam
    T = gaussian_filter(np.where(LA > 0, LA, 0).astype(float), 1.5)
    gy, gx = np.gradient(T)                                       # gy along depth, gx along s
    r0, r1 = int(3 * ppm), int(25 * ppm)
    Jxx = gaussian_filter1d((gx * gx)[r0:r1].sum(0), 8 * ppm); Jyy = gaussian_filter1d((gy * gy)[r0:r1].sum(0), 8 * ppm)
    Jxy = gaussian_filter1d((gx * gy)[r0:r1].sum(0), 8 * ppm)
    ang = 0.5 * np.arctan2(2 * Jxy, Jxx - Jyy)                    # gradient direction
    vs, vd = -np.sin(ang), np.cos(ang)                            # stripe direction = perpendicular to the gradient
    flip = vd > 0; vs = np.where(flip, -vs, vs); vd = np.where(flip, -vd, vd)
    vd = np.minimum(vd, -0.35); slope = vs / np.abs(vd)          # s-shift per mm of depth
    d0 = int(round((GAP + 1.5) * ppm))
    seamcol = np.where(LA[d0] == LA[d0 + int(4 * ppm)], LA[d0], 0)   # genuine crossings only (same tone 4 mm deeper)
    S_idx = np.arange(len(ss))[None, :] - (ds[:, None] + GAP + 1.5) * slope[None, :] * ppm
    C = seamcol[np.clip(np.round(S_idx).astype(int), 0, len(ss) - 1)]
    C[(S_idx < 0) | (S_idx > len(ss) - 1)] = 0
    # min-mismatch cut: DP over s of the switch depth
    cost = (C != LB).astype(float) * np.where((C == 0) | (LB == 0), 1.0, 0.6)
    cost[: int(Q_DMIN * ppm)] = 1e3                                # the continuation always runs Q_DMIN
    cost = cost + 0.004 * np.arange(cost.shape[0])[:, None]        # prefer a short continuation: B keeps its own art
    ncol = cost.shape[1]; nd = cost.shape[0]; acc = np.cumsum(cost, 0)  # cost of a cut at depth k = mismatch on the path itself
    E = cost.copy(); back = np.zeros((nd, ncol), int); step = 2
    for j in range(1, ncol):
        prev = E[:, j - 1]; best = np.full(nd, np.inf); arg = np.zeros(nd, int)
        for dk in range(-step, step + 1):
            sh = np.roll(prev, dk); 
            if dk > 0: sh[:dk] = np.inf
            elif dk < 0: sh[dk:] = np.inf
            m = sh < best; best[m] = sh[m]; arg[m] = (np.arange(nd) - dk)[m]
        E[:, j] = cost[:, j] + best; back[:, j] = arg
    k = int(np.argmin(E[:, -1])); cut = np.zeros(ncol, int)
    for j in range(ncol - 1, -1, -1): cut[j] = k; k = back[k, j]
    zone_mask = np.arange(nd)[:, None] < cut[None, :]
    newlab = np.where(zone_mask, C, 0)
    # back to piece coords: zone polygon + one polygon set per tone
    s_, d_, p0, t, n, LL = _sd(B, np.array([0.0]), np.array([0.0]))
    sc = B.L / L
    def to_piece(g):
        return affinity.affine_transform(g, [t[0] * sc, n[0], t[1] * sc, n[1], p0[0], p0[1]])
    zone = TR.polys_of(zone_mask, ppm, (0.0, 0.0), min_px=1, simplify=0.1)
    zone = to_piece(zone).buffer(0)
    added = 0
    keepB = []
    for r in art[B.P]:
        if r["grp"] in BAND_GRPS and r["geom"].intersects(zone):
            g = r["geom"].difference(zone)
            if not g.is_empty and g.area > 0.3: keepB.append(dict(r, geom=g.buffer(0)))
        else: keepB.append(r)                                        # curls / drops of B are all kept (foam sits above stripes)
    for kk in np.unique(newlab):
        if kk == 0: continue
        g = TR.polys_of(newlab == kk, ppm, (0.0, 0.0), min_px=2, simplify=0.15)
        g = to_piece(g).buffer(0).intersection(B.region)
        col = keys[kk - 1]
        for p in polys_of(g):
            if p.area < 0.6: continue
            grp = "RP" if col == "w1" else "WV"
            st = "satin" if (grp == "RP" or (not p.interiors and 2 * p.area / max(p.length, 1e-6) < 3.0)) else "tatami"
            keepB.append(dict(col=col, geom=p, st=st, ang="auto", grp=grp, z=(1 if grp == "RP" else 0) + 0.25, unit=None)); added += 1
    # drop B's curls that the zone cut in half? (kept: foam sits above the stripes)
    art[B.P] = keepB
    return dict(cut_mm=[round(float(cut.min()) / ppm, 1), round(float(np.median(cut)) / ppm, 1), round(float(cut.max()) / ppm, 1)],
                mismatch_on_cut=round(float(np.mean([cost[cut[j], j] for j in range(ncol)])), 2), added=added)
