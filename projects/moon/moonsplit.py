"""Hoop split on an nx × ny grid (dst2.split_clip only does 2 × 2; the moon back is 593–695 mm wide because the wires
run to the side seams, so L–3XL need 3 columns). Same production rules as dst2.split_clip (LESSONS B10/B12):
motif clusters < whole_max go whole to one section; larger fills are cut at the split with `overlap` mm sewn into both
sections (lines are cut without overlap); split positions minimise the length cut through fill art; basting
registration crosses sit on bare fabric ON the split lines (inside the art bounds, so they never widen a section);
every section incl. its crosses fits the frame − 2 × margin."""
import math, itertools
import numpy as np
import shapely
from shapely.geometry import box, LineString, Point
from shapely.ops import unary_union
import dst2

FILL = ("tatami", "padded", "satin")

def _polys(g): return dst2.polys(g)

def grid_split(vis, frame=(360.0, 360.0), margin=8.0, overlap=1.2, whole_max=70.0, arm=6.0, clear=5.0, xs=None, ys=None, groups=None):
    fw, fh = frame[0] - 2 * margin, frame[1] - 2 * margin
    U = unary_union([r["geom"] for r in vis]); b = U.bounds; W, H = b[2] - b[0], b[3] - b[1]
    F = unary_union([r["geom"] for r in vis if r["st"] in FILL])
    pad = 8.0                                        # room for whole motifs overhanging a cut + crosses
    def cand(n, lo, L, f):
        if n == 1: return [()] if L <= f - pad else []
        step = L / n; out = []
        rngs = [np.linspace(lo + step * k - step * 0.25, lo + step * k + step * 0.25, 9) for k in range(1, n)]
        for c in itertools.product(*rngs):
            edges = [lo] + list(c) + [lo + L]
            if all(0 < edges[i + 1] - edges[i] <= f - pad for i in range(n)): out.append(c)
        return out
    from shapely.prepared import prep
    Fs = F.simplify(0.3); CX, CY = {}, {}
    def cxl(x):
        if x not in CX: CX[x] = Fs.intersection(LineString([(x, b[1]), (x, b[3])])).length
        return CX[x]
    def cyl(y):
        if y not in CY: CY[y] = Fs.intersection(LineString([(b[0], y), (b[2], y)])).length
        return CY[y]
    best = None
    if xs is not None and ys is not None:          # preset layout (e.g. moon + box whole in one hooping, pole in another)
        best = ((len(xs) + 1) * (len(ys) + 1), sum(cxl(x) for x in xs) + sum(cyl(y) for y in ys)), tuple(xs), tuple(ys)
    for nx in ((1, 2, 3, 4) if best is None else ()):
        for ny in (1, 2, 3):
            cx = cand(nx, b[0], W, fw); cy = cand(ny, b[1], H, fh)
            if not cx or not cy: continue
            for xs in cx:
                for ys in cy:
                    cut = sum(cxl(x) for x in xs) + sum(cyl(y) for y in ys)
                    score = (nx * ny, cut)
                    if best is None or score < best[0]: best = (score, xs, ys)
        if best is not None: break
    _, xs, ys = best
    XE = [b[0] - 50] + list(xs) + [b[2] + 50]; YE = [b[1] - 50] + list(ys) + [b[3] + 50]
    nx, ny = len(XE) - 1, len(YE) - 1
    keys = [(i, j) for j in range(ny) for i in range(nx)]
    def rect(k, ov=0.0):
        i, j = k
        return box(XE[i] - (ov if i > 0 else 0), YE[j] - (ov if j > 0 else 0), XE[i + 1] + (ov if i < nx - 1 else 0), YE[j + 1] + (ov if j < ny - 1 else 0))
    def key_of(pt):
        i = max(0, min(nx - 1, int(np.searchsorted(XE, pt.x) - 1))); j = max(0, min(ny - 1, int(np.searchsorted(YE, pt.y) - 1)))
        return (i, j)
    # allowed box per section: its nominal cell clipped to the art bounds, grown on the inner sides to the frame size
    def allowed(k):
        i, j = k
        x0, x1 = max(XE[i], b[0]), min(XE[i + 1], b[2]); y0, y1 = max(YE[j], b[1]), min(YE[j + 1], b[3])
        sx_ = fw - (x1 - x0); sy_ = fh - (y1 - y0)
        l = sx_ / 2 if 0 < i < nx - 1 else (sx_ if i > 0 else 0); r_ = sx_ / 2 if 0 < i < nx - 1 else (sx_ if i < nx - 1 else 0)
        tp = sy_ / 2 if 0 < j < ny - 1 else (sy_ if j > 0 else 0); bt = sy_ / 2 if 0 < j < ny - 1 else (sy_ if j < ny - 1 else 0)
        return box(x0 - l, y0 - tp, x1 + r_, y1 + bt)
    AL = {k: allowed(k) for k in keys}
    # motif clusters (small connected groups travel together)
    small = []
    for r in vis:
        for p in _polys(r["geom"]):
            pb = p.bounds
            if max(pb[2] - pb[0], pb[3] - pb[1]) <= whole_max: small.append(p)
    cl = _polys(unary_union([p.buffer(0.6) for p in small])) if small else []
    tree = shapely.STRtree(cl) if cl else None
    def home(p):
        c = p.representative_point()
        if tree is not None:
            for i in tree.query(c):
                q = cl[int(i)]
                if q.contains(c):
                    qb = q.bounds
                    if max(qb[2] - qb[0], qb[3] - qb[1]) <= whole_max * 1.2:
                        k = key_of(q.centroid)
                        if AL[k].buffer(0.01).contains(q): return k
                    break
        k = key_of(c)
        return k if AL[k].buffer(0.01).contains(p) else None
    secs = {k: [] for k in keys}
    # whole groups (predicate on a region): every piece goes to the one section that can hold the group's bounds
    ghome = {}
    for gname, pred in (groups or {}).items():
        gs = [r["geom"] for r in vis if pred(r)]
        if not gs: continue
        gb = unary_union(gs).bounds; gc = Point((gb[0] + gb[2]) / 2, (gb[1] + gb[3]) / 2)
        k = key_of(gc)
        if AL[k].buffer(0.01).contains(box(*gb)): ghome[gname] = k
    for r in vis:
        gk = next((ghome[n] for n, pred in (groups or {}).items() if n in ghome and pred(r)), None)
        if gk is not None:
            secs[gk].append(r); continue
        parts = {k: [] for k in keys}
        ov = overlap if r["st"] in FILL else 0.0
        for p in _polys(r["geom"]):
            pb = p.bounds
            h = home(p) if max(pb[2] - pb[0], pb[3] - pb[1]) <= whole_max else None
            if h is not None: parts[h].append(p); continue
            for k in keys:
                q = p.intersection(rect(k, ov))
                if not q.is_empty and q.area > 0.3: parts[k] += _polys(q)
        for k in keys:
            if parts[k]: secs[k].append(dict(r, geom=unary_union(parts[k])))
    secs = {k: v for k, v in secs.items() if v}
    # registration crosses on the split lines, on bare fabric, inside the art bounds, shared by the neighbours
    allp = [p for k in secs for r in secs[k] for p in _polys(r["geom"])]; st = shapely.STRtree(allp)
    def dist(pt):
        _, d = st.query_nearest(Point(pt), return_distance=True); return float(d[0]) if len(d) else 1e9
    marks = {k: [] for k in secs}
    def put(pts, ks):
        ok = [p for p in pts if dist(p) >= clear]
        sel = [ok[0], ok[-1]] if len(ok) > 1 else (ok or [pts[0], pts[-1]])
        for k in ks:
            if k in marks: marks[k] += [tuple(s) for s in sel]
    for i in range(1, nx):
        for j in range(ny):
            y0, y1 = max(YE[j], b[1]) + arm, min(YE[j + 1], b[3]) - arm
            put([(XE[i], y) for y in np.linspace(y0, y1, 80)], [(i - 1, j), (i, j)])
    for j in range(1, ny):
        for i in range(nx):
            x0, x1 = max(XE[i], b[0]) + arm, min(XE[i + 1], b[2]) - arm
            put([(x, YE[j]) for x in np.linspace(x0, x1, 80)], [(i, j - 1), (i, j)])
    bbs, fits = {}, {}
    for k in secs:
        bb = unary_union([r["geom"] for r in secs[k]] + [Point(m).buffer(arm) for m in marks[k]]).bounds
        bbs[k] = bb; fits[k] = (bb[2] - bb[0] <= fw + 1e-6 and bb[3] - bb[1] <= fh + 1e-6)
    cut = best[0][1]
    names = {k: f"S{n + 1}_r{k[1] + 1}c{k[0] + 1}" for n, k in enumerate(sorted(secs, key=lambda k: (k[1], k[0])))}
    return dict(xs=list(xs), ys=list(ys), nx=nx, ny=ny, secs=secs, marks=marks, bbs=bbs, fits=fits, cut=cut, names=names, bounds=b, allowed=AL)
