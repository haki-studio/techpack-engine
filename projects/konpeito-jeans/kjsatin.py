# Copied from projects/keep-clean-our-space-hoodie/kcsatin.py (19 Oct 2026) — satin columns for lettering / line art. Unchanged.
"""Rev B satin columns (review Rev A items 1-3, 6, 9): every satin in this jacket is a COLUMN = centreline + width.

Rev A split font OUTLINES into tiles and sewed each tile with a turning satin that skipped rows to avoid fans: the DST
showed long diagonal stitches (skipped rows), fans at round ends, gaps at junctions and odd-angle fallback satins.
Rev B models every stroke as a column instead (how a hand digitizer sets lettering):
  glyph_columns(poly)  : font glyph -> skeleton graph -> strokes (spurs pruned, straight-through branches joined,
                         split at corners > CORNER deg) -> [dict(cl, w, caps, closed)], width = the font's stroke width
                         per stroke, free ends reach the outline (ray cast), junction ends stop on the crossing stroke's
                         centre so strokes overlap there (no gaps, no junction crumbs).
  ring_columns(poly,rw): closed rim columns just inside an outline (puff rims), cut at corners.
  column_pts(...)      : zig-zag satin along a column: every stitch crosses the column perpendicular to the smoothed
                         centreline, consecutive stitches never cross (an inner-curve end pivots instead), round caps
                         shrink as a semicircle, tapered columns (sparkle arms) follow a width profile, rows > 7 mm
                         are split with staggered split points (no visible split line).
Regions carry the column in r["col_cl"], r["col_w"], r["col_caps"], r["col_closed"], r["col_prof"]; r["geom"] is the
column's outline (used for knockout, coverage, routing and QA)."""
import math, random
import numpy as np
from shapely.geometry import LineString, Polygon, Point
from shapely.ops import unary_union
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
from PIL import Image, ImageDraw

CORNER = 50.0          # split a stroke where its centreline turns more than this (deg) within ~one stroke width
RNG = random.Random(4)

# ------------------------------------------------------------------ polyline helpers
def _resample(pts, step, closed=False):
    if closed and pts[0] != pts[-1]: pts = list(pts) + [pts[0]]
    ls = LineString(pts); L = ls.length
    if L < 1e-6: return [tuple(pts[0])], 0.0
    n = max(2, int(math.ceil(L / step)))
    out = [ls.interpolate(L * i / n).coords[0] for i in range(n if closed else n + 1)]
    return out, L

def _smooth(pts, k, closed=False, keep_ends=True):
    if k < 1 or len(pts) < 3: return pts
    a = np.array(pts, float); n = len(a); out = a.copy()
    for i in range(n):
        if closed: idx = [(i + j) % n for j in range(-k, k + 1)]
        else:
            if keep_ends and (i == 0 or i == n - 1): continue
            kk = min(k, i, n - 1 - i); idx = list(range(i - kk, i + kk + 1))
        out[i] = a[idx].mean(axis=0)
    return [tuple(p) for p in out]

def poly_len(pts): return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))

def _at(pts, cum, s):
    s = min(max(s, 0.0), cum[-1]); i = int(np.searchsorted(cum, s, side="right")) - 1; i = min(max(i, 0), len(pts) - 2)
    seg = cum[i + 1] - cum[i]; t = 0.0 if seg < 1e-9 else (s - cum[i]) / seg
    return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t)

def _cum(pts):
    c = [0.0]
    for a, b in zip(pts, pts[1:]): c.append(c[-1] + math.dist(a, b))
    return np.array(c)

def extend(pts, start=0.0, end=0.0):
    """extend an open polyline straight along its end tangents (tangent measured over ~1 mm)."""
    pts = list(pts)
    def tang(a_pts):
        cum = _cum(a_pts); p0 = a_pts[0]; p1 = _at(a_pts, cum, min(1.0, cum[-1]))
        d = np.array(p0) - np.array(p1); n = np.linalg.norm(d); return d / n if n > 1e-9 else np.array([0.0, 0.0])
    if start > 0:
        t = tang(pts); pts.insert(0, tuple(np.array(pts[0]) + t * start))
    if end > 0:
        t = tang(pts[::-1]); pts.append(tuple(np.array(pts[-1]) + t * end))
    return pts

def trim(pts, start=0.0, end=0.0):
    cum = _cum(pts); L = cum[-1]
    if start + end >= L - 0.05: return pts
    a, b = start, L - end
    out = [_at(pts, cum, a)] + [p for p, c in zip(pts, cum) if a < c < b] + [_at(pts, cum, b)]
    return out

# ------------------------------------------------------------------ satin column stitches
def _split_long(a, b, maxlen=7.0, step=6.0):
    d = math.dist(a, b)
    if d <= maxlen: return [b]
    m = int(math.ceil(d / step)); out = []
    for i in range(1, m):
        f = (i + RNG.uniform(-0.18, 0.18)) / m
        out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
    return out + [b]

def _cross(p1, p2, q1, q2):
    def o(a, b, c): return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return o(p1, p2, q1) * o(p1, p2, q2) < 0 and o(q1, q2, p1) * o(q1, q2, p2) < 0

def _prof(prof):
    """width profile: None | callable(t) | ("taper", power, floor) = concave double taper (sparkle arm pairs)"""
    if prof is None or callable(prof): return prof
    if prof[0] == "taper":
        pw, fl = prof[1], prof[2]; return lambda t: max(fl, (1 - abs(2 * t - 1))) ** pw
    if prof[0] == "table":                 # traced width multipliers along the column (closed rings: t = 0..1 round)
        v = np.asarray(prof[1], float); tt = np.linspace(0, 1, len(v)); return lambda t: float(np.interp(t, tt, v))
    raise ValueError(prof)

def rows(cl, w, sp, pull=0.0, caps=("round", "round"), closed=False, prof=None):
    """[(A, B)] satin rows along the column (A = left side), perpendicular to the smoothed centreline."""
    prof = _prof(prof)
    pts, L = _resample(cl, 0.2, closed)
    if L < 0.2: return []
    pts = _smooth(pts, max(1, int(round(0.25 * w / 0.2))), closed)
    if closed: pts = pts + [pts[0]]
    cum = _cum(pts); L = cum[-1]
    n = max(2, int(math.ceil(L / sp))); h = max(0.45, 0.45 * w)
    out = []; prev = None
    for k in range(n if closed else n + 1):
        s = L * k / n
        if closed:
            a = _at(pts, cum, (s - h) % L); b = _at(pts, cum, (s + h) % L)
        else:
            a = _at(pts, cum, max(0, s - h)); b = _at(pts, cum, min(L, s + h))
        c = _at(pts, cum, s); t = np.array(b) - np.array(a); tn = np.linalg.norm(t)
        if tn < 1e-9: continue
        t /= tn; nrm = np.array([-t[1], t[0]])
        ww = w * (prof(s / L) if prof else 1.0)
        hw = ww / 2
        if not closed:
            r = w / 2
            if caps[0] == "round" and s < r: hw *= math.sqrt(max(0.0, 1 - ((r - s) / r) ** 2))
            if caps[1] == "round" and L - s < r: hw *= math.sqrt(max(0.0, 1 - ((r - (L - s)) / r) ** 2))
        hw = max(0.12, hw) + pull
        A = (c[0] + nrm[0] * hw, c[1] + nrm[1] * hw); B = (c[0] - nrm[0] * hw, c[1] - nrm[1] * hw)
        if prev is not None:
            # an end that would move backwards (tight inner curve) stays where it was: the rows pivot, they never cross
            if (np.array(A) - np.array(prev[0])) @ t < 0 and _cross(prev[0], prev[1], A, B): A = prev[0]
            if (np.array(B) - np.array(prev[1])) @ t < 0 and _cross(prev[0], prev[1], A, B): B = prev[1]
        out.append((A, B)); prev = (A, B)
    return out

def column_pts(cl, w, sp, pull=0.0, caps=("round", "round"), closed=False, prof=None, reverse=False):
    """zig-zag satin: B0, A0, B1, A1 ... alternating sides, so every stitch crosses the column once."""
    rr = rows(cl[::-1] if reverse else cl, w, sp, pull, caps[::-1] if reverse else caps, closed, prof)
    if not rr: return []
    seq = [rr[0][1]]
    for k, (A, B) in enumerate(rr): seq.append(A if k % 2 == 0 else B)
    last = rr[-1]; seq.append(last[1] if (len(rr) - 1) % 2 == 0 else last[0])
    out = [seq[0]]
    for q in seq[1:]: out += _split_long(out[-1], q)
    return out

def column_geom(cl, w, caps=("round", "round"), closed=False, prof=None):
    """outline of what the column sews: flat body + a semicircle at each round end (the end point is ON the outline)."""
    if closed and prof is not None:       # closed column with a width table: the outline of its rows
        rr = rows(cl, w, 0.15, 0.0, caps, True, prof)
        outer = Polygon([a for a, b in rr]).buffer(0); inner = Polygon([b for a, b in rr]).buffer(0)
        if outer.area < inner.area: outer, inner = inner, outer
        return outer.difference(inner).buffer(0)
    if closed:
        return LineString(list(cl) + [cl[0]]).buffer(w / 2, cap_style="round", join_style="round").buffer(0)
    if prof is not None:          # tapered column: union of row quads
        rr = rows(cl, w, 0.15, 0.0, caps, False, prof)
        if len(rr) < 2: return LineString(cl).buffer(max(0.1, w / 4))
        qs = [Polygon([a0, b0, b1, a1]).buffer(0.01) for (a0, b0), (a1, b1) in zip(rr, rr[1:])]
        return unary_union(qs).buffer(0.02).buffer(0)
    r = w / 2; L = poly_len(cl)
    t0 = r if caps[0] == "round" else 0.0; t1 = r if caps[1] == "round" else 0.0
    if t0 + t1 >= L - 0.05:
        return Point(_at(cl, _cum(cl), L / 2)).buffer(max(r, L / 2) * 0.98, quad_segs=12)
    body = trim(cl, t0, t1)
    g = LineString(body).buffer(r, cap_style="flat", join_style="round")
    if t0: g = g.union(Point(body[0]).buffer(r, quad_segs=12))
    if t1: g = g.union(Point(body[-1]).buffer(r, quad_segs=12))
    return g.buffer(0)

def column_region(col, code, cl, w, caps=("round", "round"), closed=False, prof=None, **kw):
    g = column_geom(cl, w, caps, closed, prof)
    d = dict(col=col, geom=g, st="satin", ang="col", grp=code, col_cl=[tuple(p) for p in cl], col_w=float(w),
             col_caps=tuple(caps), col_closed=bool(closed), col_prof=prof, nok=True, ko=True, kob=0.0)
    d.update(kw); return d

# ------------------------------------------------------------------ glyph -> columns (skeleton graph)
_N8 = [(-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1)]

def _raster(P, ppm, m=6):
    x0, y0, x1, y1 = P.bounds
    W, H = int((x1 - x0) * ppm) + 2 * m, int((y1 - y0) * ppm) + 2 * m
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    T = lambda cs: [((x - x0) * ppm + m, (y - y0) * ppm + m) for x, y in cs]
    for p in ([P] if P.geom_type == "Polygon" else list(P.geoms)):
        d.polygon(T(p.exterior.coords), fill=255)
        for r in p.interiors: d.polygon(T(r.coords), fill=0)
    return np.array(im) > 127, (x0, y0, m)

def _graph(sk):
    H, W = sk.shape; on = lambda y, x: 0 <= y < H and 0 <= x < W and sk[y, x]
    ys, xs = np.nonzero(sk); pix = set(zip(ys.tolist(), xs.tolist()))
    def nbrs(p): return [(p[0] + dy, p[1] + dx) for dy, dx in _N8 if on(p[0] + dy, p[1] + dx)]
    def crossings(p):
        v = [1 if on(p[0] + dy, p[1] + dx) else 0 for dy, dx in _N8]; return sum(1 for i in range(8) if v[i] == 0 and v[(i + 1) % 8] == 1)
    kind = {}
    for p in pix:
        nb = nbrs(p)
        if len(nb) == 1: kind[p] = "end"
        elif crossings(p) >= 3: kind[p] = "junc"
    # junction clusters (8-connected junction pixels, + 1 px) -> one node each
    jm = np.zeros_like(sk)
    for p, k in kind.items():
        if k == "junc": jm[p] = True
    jl, nj = ndi.label(ndi.binary_dilation(jm, structure=np.ones((3, 3)), iterations=1) & sk, structure=np.ones((3, 3)))
    node_of = {}; nodes = {}
    for j in range(1, nj + 1):
        ps = list(zip(*np.nonzero(jl == j)))
        for p in ps: node_of[(int(p[0]), int(p[1]))] = ("j", j)
        nodes[("j", j)] = dict(kind="junc", c=(float(np.mean([p[1] for p in ps])), float(np.mean([p[0] for p in ps]))))
    for p, k in kind.items():
        if k == "end" and p not in node_of:
            node_of[p] = ("e", p); nodes[("e", p)] = dict(kind="end", c=(float(p[1]), float(p[0])))
    edges = []; used = set()
    for p0, nd in list(node_of.items()):
        for q in nbrs(p0):
            if q in node_of or q in used: continue
            path = [p0, q]; used.add(q); prev, cur = p0, q; end = None
            while True:
                cand = [r for r in nbrs(cur) if r != prev and r not in used and r not in path[-3:]]
                hit = [r for r in nbrs(cur) if r in node_of and r != p0 or (r in node_of and node_of[r] != nd)]
                hit = [r for r in hit if not (node_of[r] == nd and len(path) < 4)]
                if hit:
                    end = node_of[hit[0]]; path.append(hit[0]); break
                if not cand: break
                cand.sort(key=lambda r: abs(r[0] - cur[0]) + abs(r[1] - cur[1]))
                prev, cur = cur, cand[0]; used.add(cur); path.append(cur)
            edges.append(dict(a=nd, b=end, px=path))
    # loops without nodes
    rest = pix - used - set(node_of)
    while rest:
        s = rest.pop(); path = [s]; prev = None; cur = s
        while True:
            cand = [r for r in nbrs(cur) if r in rest]
            if not cand: break
            cand.sort(key=lambda r: abs(r[0] - cur[0]) + abs(r[1] - cur[1]))
            cur = cand[0]; rest.discard(cur); path.append(cur)
        if len(path) > 6: edges.append(dict(a=None, b=None, px=path, loop=True))
    return nodes, edges

def _turns(pts, w):
    """turning angle (deg) at every vertex of a resampled polyline, measured over +-d"""
    cum = _cum(pts); L = cum[-1]; d = max(0.7, 0.8 * w); out = []
    for i, s in enumerate(cum):
        if s < d * 0.6 or L - s < d * 0.6: out.append(0.0); continue
        a = np.array(_at(pts, cum, s - d)); b = np.array(pts[i]); c = np.array(_at(pts, cum, s + d))
        u, v = b - a, c - b; nu, nv = np.linalg.norm(u), np.linalg.norm(v)
        if nu < 1e-9 or nv < 1e-9: out.append(0.0); continue
        out.append(math.degrees(math.acos(max(-1, min(1, float(u @ v) / (nu * nv))))))
    return out

def split_at_corners(st, corner=CORNER):
    """[stroke] -> strokes cut where the centreline turns > corner; each piece runs w/2 past the corner (flat end)."""
    pts, w = st["cl"], st["w"]
    rs, L = _resample(pts, 0.2, st.get("closed", False))
    if st.get("closed"): rs = rs + [rs[0]]
    tr = _turns(rs, w)
    if st.get("closed"):          # turning on a loop: wrap
        n = len(rs) - 1; ext = rs[-int(2 * w / 0.2) - 2:-1] + rs + rs[1:int(2 * w / 0.2) + 2]
        te = _turns(ext, w); off = int(2 * w / 0.2) + 1; tr = te[off:off + n] + [te[off]]
    cand = [i for i in range(1, len(rs) - 1) if tr[i] > corner and tr[i] >= max(tr[max(0, i - 4):i + 5])]
    sel = []
    for i in cand:
        if not sel or i - sel[-1] > max(3, int(0.9 * w / 0.2)): sel.append(i)
    if not sel: return [st]
    out = []
    if st.get("closed"):
        n = len(rs) - 1
        for k, i in enumerate(sel):
            j = sel[(k + 1) % len(sel)]
            seg = rs[i:j + 1] if j > i else rs[i:n] + rs[:j + 1]
            if poly_len(seg) < 0.3: continue
            out.append(dict(st, cl=extend(seg, w / 2, w / 2), caps=("flat", "flat"), closed=False))
        return out
    bounds = [0] + sel + [len(rs) - 1]
    for k in range(len(bounds) - 1):
        seg = rs[bounds[k]:bounds[k + 1] + 1]
        if poly_len(seg) < 0.3: continue
        c0 = st["caps"][0] if k == 0 else "flat"; c1 = st["caps"][1] if k == len(bounds) - 2 else "flat"
        e0 = 0.0 if k == 0 else w / 2; e1 = 0.0 if k == len(bounds) - 2 else w / 2
        out.append(dict(st, cl=extend(seg, e0, e1), caps=(c0, c1), closed=False))
    return out

def _reach(e, junc_node, bnd):
    """distance from the junction end of branch e to the outline, measured along the branch and on past its free end"""
    pts = e["pts"] if e["b"] == junc_node else e["pts"][::-1]          # junction end first
    p0 = pts[-1]; cum = _cum(pts); q = _at(pts, cum, max(0.0, cum[-1] - 1.0))
    t = np.array(p0) - np.array(q); tn = np.linalg.norm(t); ext = 0.0
    if tn > 1e-9:
        t /= tn; ray = LineString([p0, tuple(np.array(p0) + t * 12)]).intersection(bnd)
        ds = [Point(p0).distance(Point(c)) for g in getattr(ray, "geoms", [ray]) if not g.is_empty for c in g.coords]
        if ds: ext = min(ds)
    return math.dist(pts[0], p0) + ext

def _dir(e, nd):
    pts = e["pts"] if e["a"] == nd else e["pts"][::-1]; cum = _cum(pts)
    q = _at(pts, cum, min(cum[-1], max(1.2, 1.2 * e["w"]))); v = np.array(q) - np.array(pts[0]); n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v

def glyph_columns(P, cap="round", ppm=20.0, corner=CORNER, join_angle=140.0):
    """font glyph polygon -> list of strokes dict(cl=[(x, y)], w, caps, closed). Strokes tile the glyph with overlap."""
    mask, (x0, y0, m) = _raster(P, ppm)
    if mask.sum() < 30: return []
    sk = skeletonize(mask); dt = ndi.distance_transform_edt(mask) / ppm
    nodes, edges = _graph(sk)
    mm = lambda p: ((p[1] - m) / ppm + x0, (p[0] - m) / ppm + y0)
    def ncent(nd): c = nodes[nd]["c"]; return ((c[0] - m) / ppm + x0, (c[1] - m) / ppm + y0)
    E = []
    for e in edges:
        px = e["px"]; w = 2 * float(np.median([dt[p] for p in px])) if px else 1.0
        pts = [mm(p) for p in px]
        if e.get("loop"):
            E.append(dict(a=None, b=None, pts=pts, w=w, loop=True)); continue
        if e["a"] and nodes[e["a"]]["kind"] == "junc": pts[0] = ncent(e["a"])
        if e["b"] and nodes[e["b"]]["kind"] == "junc": pts[-1] = ncent(e["b"])
        E.append(dict(a=e["a"], b=e["b"], pts=pts, w=w))
    def deg(nd): return sum((x["a"] == nd) + (x["b"] == nd) for x in E if not x.get("loop"))
    # prune spurs. At one junction: two or more short free branches = the fork of a square / angled stroke end (prune
    # them all; that node becomes a free end); one short free branch = a spur only if it does not reach out past the
    # parent stroke (a real short stroke, e.g. the 宀 tick, does)
    def deg_e(nd): return [x for x in E if not x.get("loop") and nd in (x["a"], x["b"])]
    for _ in range(4):
        changed = False
        for nd in [k for k, v in nodes.items() if v["kind"] == "junc"]:
            inc = deg_e(nd)
            if len(inc) < 3: continue
            def is_free(x):
                o = x["b"] if x["a"] == nd else x["a"]; return o is None or nodes[o]["kind"] == "end"
            wn = max(x["w"] for x in inc)
            short = [x for x in inc if is_free(x) and poly_len(x["pts"]) < 0.95 * wn]
            # two short branches pointing opposite ways are a short bar crossing the stroke (王, 土), not a fork
            opp = set()
            for i in range(len(short)):
                for j in range(i + 1, len(short)):
                    if float(_dir(short[i], nd) @ _dir(short[j], nd)) < -0.75: opp |= {i, j}
            short = [x for i, x in enumerate(short) if i not in opp]
            if len(short) >= 2 and len(short) < len(inc):
                for x in short: E.remove(x)
                changed = True
            elif len(short) == 1 and _reach(short[0], nd, P.boundary) < 0.85 * wn:
                E.remove(short[0]); changed = True
        # merge through degree-2 nodes
        for nd in list(nodes):
            inc = [x for x in E if not x.get("loop") and nd in (x["a"], x["b"])]
            if len(inc) == 2 and inc[0] is not inc[1]:
                p, q = inc
                pp = p["pts"] if p["b"] == nd else p["pts"][::-1]; pa = p["a"] if p["b"] == nd else p["b"]
                qq = q["pts"] if q["a"] == nd else q["pts"][::-1]; qb = q["b"] if q["a"] == nd else q["a"]
                L1, L2 = poly_len(pp), poly_len(qq)
                E.remove(p); E.remove(q)
                E.append(dict(a=pa, b=qb, pts=pp + qq[1:], w=(p["w"] * L1 + q["w"] * L2) / max(L1 + L2, 1e-9))); changed = True
            elif len(inc) == 1 and inc[0]["a"] == nd and inc[0]["b"] == nd:      # self loop through one node
                x = inc[0]; E.remove(x); E.append(dict(a=None, b=None, pts=x["pts"], w=x["w"], loop=True)); changed = True
        if not changed: break
    # join straight-through pairs at junctions
    def dir_at(e, nd):
        pts = e["pts"] if e["a"] == nd else e["pts"][::-1]; cum = _cum(pts)
        q = _at(pts, cum, min(cum[-1], max(1.2, 1.2 * e["w"]))); v = np.array(q) - np.array(pts[0]); n = np.linalg.norm(v)
        return v / n if n > 1e-9 else v
    for nd in [k for k, v in nodes.items() if v["kind"] == "junc"]:
        inc = [x for x in E if not x.get("loop") and nd in (x["a"], x["b"]) and x["a"] != x["b"]]
        pairs = []
        for i in range(len(inc)):
            for j in range(i + 1, len(inc)):
                a_ = math.degrees(math.acos(max(-1, min(1, float(dir_at(inc[i], nd) @ dir_at(inc[j], nd))))))
                if a_ >= join_angle and abs(inc[i]["w"] - inc[j]["w"]) < 0.45 * max(inc[i]["w"], inc[j]["w"]): pairs.append((a_, i, j))
        done = set()
        for a_, i, j in sorted(pairs, reverse=True):
            if i in done or j in done: continue
            done |= {i, j}; p, q = inc[i], inc[j]
            pp = p["pts"] if p["b"] == nd else p["pts"][::-1]; pa = p["a"] if p["b"] == nd else p["b"]
            qq = q["pts"] if q["a"] == nd else q["pts"][::-1]; qb = q["b"] if q["a"] == nd else q["a"]
            L1, L2 = poly_len(pp), poly_len(qq)
            E.remove(p); E.remove(q)
            E.append(dict(a=pa, b=qb, pts=pp + qq[1:], w=(p["w"] * L1 + q["w"] * L2) / max(L1 + L2, 1e-9), joined=nd))
    out = []
    bnd = P.boundary
    for e in E:
        w = min(8.0, max(0.9, e["w"]))
        if e.get("loop"):
            pts = LineString(e["pts"]).simplify(0.12).coords[:]
            if len(pts) < 4: continue
            out += split_at_corners(dict(cl=list(pts), w=w, caps=("flat", "flat"), closed=True), corner); continue
        pts = list(LineString(e["pts"]).simplify(0.12).coords)
        if len(pts) < 2 or poly_len(pts) < 0.25: continue
        ca = []
        for end, nd in ((0, e["a"]), (1, e["b"])):
            junc = nd is not None and nodes[nd]["kind"] == "junc" and len(deg_e(nd)) >= 2
            if junc:
                # skeleton hooks toward the junction centre: replace the last 0.6 w with a straight run to the centre
                L = poly_len(pts); cut = min(0.6 * w, 0.3 * L)
                tgt = pts[0] if end == 0 else pts[-1]
                pts = trim(pts, cut, 0) if end == 0 else trim(pts, 0, cut)
                pts = extend(pts, cut, 0) if end == 0 else extend(pts, 0, cut)
                ca.append("flat")
            else:
                # free end: run on to the outline (ray cast along the end tangent)
                cum = _cum(pts); p0 = pts[0] if end == 0 else pts[-1]
                q = _at(pts, cum, min(cum[-1], 1.0)) if end == 0 else _at(pts, cum, max(0.0, cum[-1] - 1.0))
                t = np.array(p0) - np.array(q); tn = np.linalg.norm(t)
                ext = 0.0
                if tn > 1e-9:
                    t /= tn; ray = LineString([p0, tuple(np.array(p0) + t * (2 * w + 3))]).intersection(bnd)
                    ds = [Point(p0).distance(Point(c)) for g in getattr(ray, "geoms", [ray]) if not g.is_empty for c in g.coords]
                    if ds: ext = min(min(ds), w)
                pts = extend(pts, ext, 0) if end == 0 else extend(pts, 0, ext)
                ca.append(cap)
        out += split_at_corners(dict(cl=pts, w=w, caps=tuple(ca), closed=False), corner)
    return out

def ring_columns(P, rw, corner=CORNER):
    """rim columns: the outline of P (outer + holes) inset by rw/2, closed, cut at corners."""
    out = []
    inner = P.buffer(-rw / 2, join_style="mitre", mitre_limit=2.0)
    for p in ([inner] if inner.geom_type == "Polygon" else list(getattr(inner, "geoms", []))):
        if p.is_empty or p.area < 0.2: continue
        for ring in [p.exterior] + list(p.interiors):
            cs = list(LineString(ring.coords).simplify(0.08).coords)[:-1]
            if len(cs) < 3 or LineString(cs + [cs[0]]).length < 1.5: continue
            out += split_at_corners(dict(cl=cs, w=rw, caps=("flat", "flat"), closed=True), corner)
    return out

def strokes_geom(sts):
    return unary_union([column_geom(s["cl"], s["w"], s["caps"], s.get("closed", False), s.get("prof")) for s in sts]).buffer(0)

def move(r, s=1.0, origin=(0.0, 0.0), d=(0.0, 0.0)):
    """region r scaled by s about origin then translated by d — column data (centreline, width) included."""
    from shapely import affinity
    ox, oy = origin; f = lambda p: (ox + (p[0] - ox) * s + d[0], oy + (p[1] - oy) * s + d[1])
    g = affinity.translate(affinity.scale(r["geom"], s, s, origin=(ox, oy)), d[0], d[1]) if s != 1.0 else affinity.translate(r["geom"], d[0], d[1])
    r2 = dict(r, geom=g.buffer(0))
    if r.get("col_cl"): r2["col_cl"] = [f(p) for p in r["col_cl"]]; r2["col_w"] = r["col_w"] * s
    if r.get("run_pts"): r2["run_pts"] = [f(p) for p in r["run_pts"]]
    if isinstance(r.get("ang"), tuple):
        c = f((r["ang"][1], r["ang"][2])); r2["ang"] = (r["ang"][0], c[0], c[1])
    return r2
