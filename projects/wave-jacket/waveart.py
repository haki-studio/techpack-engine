"""Per-size wave art on the five embroidered pieces (BK back, FR/FL fronts, SR/SL sleeves), from the traced render.

For each size (LESSONS A5 — wrap art is rebuilt per size, never scaled as one file):
  1. render-px regions of each piece: the body piece drawn back into the render (mockmap.body_tf of that size) minus the
     visible sleeve halves (the sleeves lie on top of the body sides in the flat lay); each sleeve half's Coons patch
  2. wave stripes + rope lines: mapped point by point (non-rigid) onto every piece they overlap
  3. foam crests are cut into LOBES (watershed of the cream mass, one lobe per curl); each lobe + its interior (shade
     cream, grey hollow, blue claws) and every spray drop move as a RIGID motif: its anchor follows the piece map, its
     shape keeps the render's proportions at the local mean scale (no oval curls on the anisotropic map)
  4. painter's order (stripes < rope lines < foam details < foam < drops), clip to the size's keep-outs, clean
  5. loop texture (FM-loop) drawn on the visible foam: scalloped contour rings, the chenille look of the render
  6. wrap check: art meeting each armhole / cap seam, as arc fractions on both pieces (match marks)
usage: ./py.sh waveart.py M [S L ...]  ->  art_<size>.pkl  + out/art/<size>_<view>.png"""
import wavecore as WC
import math, os, pickle, sys, time, functools
import numpy as np
import shapely
from shapely.geometry import Point, Polygon, LineString, MultiLineString, box
from shapely.ops import unary_union
from shapely import affinity
from shapely.validation import make_valid
import mockmap as MM, pieces as PC, wavetrace as WT
from motifs2 import R
import dst2
WC.patch_dst2()

VIEW_PIECES = {"back": ["BK", "SL", "SR"], "front": ["FR", "FL", "SR", "SL"]}
SLEEVE_SIDE = {"SR": "R", "SL": "L"}
Z = dict(band=0, rope=1, fdet=2, foam=3, dropb=4, drop=5)
CODE_OF = {"w1": "FM", "w3": "FM-sh", "g1": "FM-gr"}

def polys(g):
    if g is None or g.is_empty: return []
    if g.geom_type == "Polygon": return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]

def width(p): return 2 * p.area / max(p.length, 1e-6)

@functools.lru_cache(maxsize=None)
def traced(view):
    tr = pickle.load(open(f"trace_{view}.pkl", "rb"))
    tr["lobes"] = lobes(tr)
    return tr

def rasterize(g, b, k):
    """polygon(s) -> bool mask over bounds b at k px per unit (px rows/cols from b[0], b[1]); same convention as trace.polys_of"""
    from PIL import Image, ImageDraw
    W, H = int(math.ceil((b[2] - b[0]) * k)) + 2, int(math.ceil((b[3] - b[1]) * k)) + 2
    im = Image.new("1", (W, H), 0); d = ImageDraw.Draw(im)
    for p in polys(g):
        d.polygon([((x - b[0]) * k - 0.5, (y - b[1]) * k - 0.5) for x, y in p.exterior.coords], fill=1)
        for h in p.interiors: d.polygon([((x - b[0]) * k - 0.5, (y - b[1]) * k - 0.5) for x, y in h.coords], fill=0)
    return np.array(im, bool)

# ---------------------------------------------------------------- crest -> lobes (rigid motifs)
def lobes(tr, min_dist_px=7.0):
    """split every crest into curls: watershed of the distance map of its filled outline (render px)"""
    from skimage.segmentation import watershed
    from skimage.feature import peak_local_max
    out = []
    for c in tr["foam"]:
        parts = {"w1": c["mass"].difference(c["shade"]).difference(c["grey"]), "w3": c["shade"], "g1": c["grey"]}
        inner = c["inner"]; blue = c.get("blue", {})
        if c["kind"] == "dot":
            out.append(dict(kind="dot", anchor=c["filled"].centroid.coords[0], parts=parts, inner=inner, blue=blue, outline=c["filled"]))
            continue
        F = c["filled"]; b = F.bounds; k = 4.0
        m = rasterize(F, b, k)
        from scipy import ndimage as ndi
        dt = ndi.distance_transform_edt(m)
        pk = peak_local_max(dt, min_distance=int(min_dist_px * k), threshold_abs=2.0 * k, labels=m.astype(int), exclude_border=False)
        if len(pk) <= 1:
            out.append(dict(kind="lobe", anchor=F.centroid.coords[0], parts=parts, inner=inner, blue={}, outline=F)); continue
        mk = np.zeros(m.shape, int)
        for i, (r, cc) in enumerate(pk, 1): mk[r, cc] = i
        ws = watershed(-dt, mk, mask=m)
        import trace as TR
        for i in range(1, len(pk) + 1):
            cell = TR.polys_of(ws == i, k, (b[0], b[1]), min_px=1, simplify=0.05)
            if cell.is_empty: continue
            cell = cell.buffer(1.2).intersection(F)             # neighbouring curls overlap 1.2 px: no slit between them after the rigid move
            pp = {t: g.intersection(cell) for t, g in parts.items()}
            ii = {t: g.intersection(cell) for t, g in inner.items()}
            out.append(dict(kind="lobe", anchor=cell.centroid.coords[0], parts=pp, inner=ii, blue={}, outline=cell))
    return out

# ---------------------------------------------------------------- per-size maps
@functools.lru_cache(maxsize=None)
def piece_maps(size):
    """{(view, P): (f(px,py)->mm, region_px, kind)}"""
    out = {}
    for view, Ps in VIEW_PIECES.items():
        f, finv = MM.body_tf(view, size)
        quads = {}
        for P in Ps:
            if P in SLEEVE_SIDE:
                sm = MM.sleeve_map(view, SLEEVE_SIDE[P], size)
                # the render region that belongs to the sleeve is the SIZE-M one on every size (grading review 19 Oct): the
                # per-size armhole moved the sleeve/body boundary in the render, so curls near it switched piece size to size
                # (SL motifs 60/53/61/55/49/56/53 XS..3XL) and sleeve art boxes were not monotonic. Placement stays per size.
                q = MM.sleeve_map(view, SLEEVE_SIDE[P], "M").quad_px
                quads[P] = q
                out[(view, P)] = (sm, q, "sleeve")
        for P in Ps:
            if P in SLEEVE_SIDE: continue
            pan = PC.panel(size, P)
            c = np.array(pan.exterior.segmentize(4).coords); X, Y = finv(c[:, 0], c[:, 1])
            reg = Polygon(np.c_[X, Y]).buffer(0)
            for q in quads.values(): reg = reg.difference(q)
            out[(view, P)] = (f, make_valid(reg).buffer(0), "body")
    return out

def lin_at(m, kind, view, size, a):
    """local similarity (2x2) of the piece map at render point a: body = mean scale S; sleeve = polar part of the Jacobian"""
    if kind == "body":
        s = MM.S_of(view) * MM.GRADE[size][1]; return np.array([[s, 0.0], [0.0, s]])
    J, _ = m.jac(a[0], a[1])
    if not np.all(np.isfinite(J)): return None
    U, sv, Vt = np.linalg.svd(J); Rm = U @ Vt
    if np.linalg.det(Rm) < 0: U[:, -1] *= -1; Rm = U @ Vt
    # scale: the body's mean scale (the patch Jacobian blows up near the folded cap; curls keep the size they have on the body)
    return Rm * MM.S_of(view) * MM.GRADE[size][1]

def pt_map(m, kind):
    if kind == "body": return lambda x, y: m(x, y)
    return lambda x, y: m(x, y)

def rigid(g, a, A, a_mm):
    if g is None or g.is_empty: return g
    return affinity.affine_transform(g, [A[0, 0], A[0, 1], A[1, 0], A[1, 1], a_mm[0] - A[0, 0] * a[0] - A[0, 1] * a[1], a_mm[1] - A[1, 0] * a[0] - A[1, 1] * a[1]]).buffer(0)

def nonrigid(g, m):
    if g is None or g.is_empty: return g
    out = MM.map_geom(g, lambda x, y: m(x, y), densify=1.0)
    try: return make_valid(out).buffer(0)
    except Exception: return out.buffer(0)

# ---------------------------------------------------------------- items per piece
def items_for(size, P):
    its = []
    def add(col, geom, st, ang, grp, z, unit=None):
        for p in polys(geom):
            if p.area < 0.3: continue
            r = R(col, p, st, ang, grp); r["z"] = z; r["unit"] = unit; its.append(r)
    for view in ("back", "front"):
        if P not in VIEW_PIECES[view]: continue
        tr = traced(view); m, reg, kind = piece_maps(size)[(view, P)]
        regb = reg.buffer(0.01)
        # stripes + rope lines (non-rigid)
        for tone, g in tr["bands"].items():
            q = g.intersection(regb)
            if q.is_empty: continue
            mm_ = nonrigid(q, m)
            for p in polys(mm_):
                if kind == "sleeve" and width(p) < 2.5 and p.length > 60 and p.intersection(box(-8, -200, 8, 600)).area > 0.6 * p.area:
                    continue                                  # the render's sleeve-fold highlight, not art
                # turning satin follows ONE centreline: on stripes with holes or branches it left 5-15 % bare (DST
                # coverage check, M BK). Satin only for narrow simple stripes; everything else tatami along the stripe.
                st = "satin" if (not p.interiors and width(p) < 3.0) else "tatami"
                add(tone, p, st, "auto", "WV", Z["band"])
        q = tr["lines"].intersection(regb)
        if not q.is_empty:
            for p in polys(nonrigid(q, m)): add("w1", p, "satin", "auto", "RP", Z["rope"])
        # rigid motifs: foam lobes + drops
        for i, lb in enumerate(tr["lobes"]):
            if not lb["outline"].intersects(regb): continue
            a = lb["anchor"]
            if kind == "sleeve" and not reg.buffer(6).contains(Point(a)): continue
            A = lin_at(m, kind, view, size, a)
            a_mm = m(np.array([a[0]]), np.array([a[1]]))
            a_mm = (float(np.ravel(a_mm[0])[0]), float(np.ravel(a_mm[1])[0]))
            if A is None or not all(map(math.isfinite, a_mm)): continue
            unit = f"{view}{i}"
            dz = 0.0001 * i
            for t, g in lb["inner"].items():
                code = "FM-in" if t in WT.BLUES else ("FM-gr" if t == "g1" else "FM-sh")
                add(t if t != "w2" else "w3", rigid(g, a, A, a_mm), "satin", "auto", code, Z["fdet"] + dz, unit)
            for t in ("w3", "g1"):
                add(t, rigid(lb["parts"][t], a, A, a_mm), "satin", "auto", CODE_OF[t], Z["fdet"] + dz, unit)
            if lb["kind"] == "dot":
                for t, g in lb["blue"].items(): add(t, rigid(g, a, A, a_mm), "satin", "auto", "DR-b", Z["dropb"] + dz, unit)
                add("w1", rigid(lb["parts"]["w1"], a, A, a_mm), "satin", "auto", "DR", Z["drop"] + dz, unit)
            else:
                g = rigid(lb["parts"]["w1"], a, A, a_mm)
                for p in polys(g):
                    add("w1", p, "padded" if width(p) >= 2.4 else "satin", "auto", "FM", Z["foam"] + dz, unit)
    return its

def visible(items, clip):
    """z-ordered knockout inside clip (higher z covers lower)"""
    its = [r for r in items if r["geom"].intersects(clip)]
    its.sort(key=lambda r: -r["z"])
    geoms = [r["geom"] for r in its]
    tree = shapely.STRtree(geoms); out = []
    for i, r in enumerate(its):
        try: g = r["geom"].intersection(clip)
        except Exception: g = make_valid(r["geom"]).buffer(0).intersection(clip)
        if g.is_empty: continue
        hits = [int(j) for j in tree.query(g) if int(j) < i and its[int(j)]["z"] > r["z"]]
        if hits:
            try: g = g.difference(unary_union([geoms[j] for j in hits]))
            except Exception: g = make_valid(g).buffer(0).difference(make_valid(unary_union([geoms[j] for j in hits])).buffer(0))
        g = g.buffer(0)
        if not g.is_empty and g.area > 0.2: out.append(dict(r, geom=g))
    out.reverse()
    return out

# ---------------------------------------------------------------- loop texture (chenille look)
def scallop(line, r=0.75, step=1.5):
    """a line drawn as a row of small arcs (non-self-intersecting loops)"""
    L = line.length
    if L < 2 * step: return line
    pts = []; n = int(L / step)
    for k in range(n):
        s0, s1 = k * L / n, (k + 1) * L / n
        p0 = line.interpolate(s0); p1 = line.interpolate(s1)
        dx, dy = p1.x - p0.x, p1.y - p0.y; d = math.hypot(dx, dy) or 1
        nx, ny = -dy / d, dx / d
        for t in np.linspace(0, 1, 6, endpoint=False):
            h = math.sin(math.pi * t) * r
            pts.append((p0.x + dx * t + nx * h, p0.y + dy * t + ny * h))
    pts.append(line.coords[-1])
    return LineString(pts)

def ring_chain(p, spacing):
    """inward contour rings of p joined into open spiral-like paths (each ring left open 3 mm where it hands over to
    the next ring), so one path = one run object whose buffer has no holes"""
    paths = []
    def walk(q, path):
        ring = LineString(q.exterior.coords)
        if ring.length < 6: 
            if path: paths.append(path)
            return
        if path:
            e = Point(path[-1]); s0 = ring.project(e)
        else: s0 = 0.0
        L = ring.length; seg = []
        for t in np.arange(0, L - 3.0, 0.6): seg.append(ring.interpolate((s0 + t) % L).coords[0])
        path = path + seg
        inner = [r for r in polys(q.buffer(-spacing)) if r.area > 3.0]
        if len(inner) == 1: walk(inner[0], path)
        else:
            paths.append(path)
            for r in inner: walk(r, [])
    walk(p, [])
    return [LineString(pp) for pp in paths if len(pp) > 4]

def loops_for(foam_geom, spacing=2.1, inset=0.9):
    """scalloped contour spirals inside the visible foam: the render's looped (chenille) texture"""
    out = []
    for p in polys(foam_geom.buffer(-inset)):
        if p.area < 3.0: continue
        for ln in ring_chain(p, spacing):
            s = scallop(ln.simplify(0.15))
            out.append(s.buffer(0.22, cap_style="round", join_style="round"))
    return out

def curl_lines(vis):
    """the render's curl separations: a fine shade line where one curl overlaps the next, and the C-curl of every
    larger lobe (240 deg arc, open to the underside where the hollow is)"""
    foam = [r for r in vis if r["grp"] == "FM"]; out = []
    by = {}
    for r in foam: by.setdefault(r.get("unit"), []).append(r["geom"])
    U = {u: unary_union(g) for u, g in by.items()}
    keys = list(U); tree = shapely.STRtree([U[k] for k in keys])
    for i, u in enumerate(keys):
        g = U[u]
        others = [U[keys[j]] for j in tree.query(g.buffer(0.8)) if j != i]
        if others:
            seam = g.boundary.intersection(unary_union(others).buffer(0.7))
            for ln in getattr(seam, "geoms", [seam]):
                if ln.geom_type == "LineString" and ln.length > 2.5:
                    q = ln.buffer(0.35, cap_style="round").intersection(g)
                    for p in polys(q):
                        if p.area > 0.4: out.append(dict(R("w3", p, "bean", None, "FM-curl"), z=Z["foam"] + 0.6, unit=u))
        if g.area > 55:
            c = g.representative_point(); rr = 0.42 * math.sqrt(g.area / math.pi)
            arc = LineString([(c.x + rr * math.cos(t), c.y + rr * math.sin(t)) for t in np.radians(np.linspace(120, 360, 30))])
            q = arc.buffer(0.35, cap_style="round").intersection(g.buffer(-0.8))
            for p in polys(q):
                if p.area > 0.6: out.append(dict(R("w3", p, "bean", None, "FM-curl"), z=Z["foam"] + 0.6, unit=u))
    return out

def close_foam_gaps(vis):
    """rigid curls moved a little apart leave fabric slits between them: fill slits < 2.4 mm inside a crest with foam"""
    foam = unary_union([r["geom"] for r in vis if r["grp"] == "FM"])
    if foam.is_empty: return vis
    closed = foam.buffer(1.2, join_style=2).buffer(-1.2, join_style=2)
    gaps = closed.difference(unary_union([r["geom"] for r in vis]).buffer(0.05))
    out = list(vis)
    for p in polys(gaps):
        if p.area > 0.3 and width(p) > 0.5: out.append(dict(R("w1", p, "satin", "auto", "FM"), z=Z["foam"], unit=None))
    return out

def add_loops(vis):
    vis = close_foam_gaps(vis)
    foam = [r for r in vis if r["grp"] == "FM" and r["st"] == "padded"]
    out = list(vis) + curl_lines(vis)
    curls = unary_union([r["geom"] for r in out if r["grp"] == "FM-curl"]) if any(r["grp"] == "FM-curl" for r in out) else Polygon()
    for r in foam:
        for p in polys(r["geom"]):
            for lp in loops_for(p):
                lp = lp.intersection(p.buffer(-0.3)).difference(curls.buffer(0.3))
                for q in polys(lp):
                    if q.area > 0.5: out.append(dict(R("w3", q, "run", None, "FM-loop"), z=Z["foam"] + 0.5, unit=r.get("unit")))
    return out

def layer_of(r):
    return {"RP": WC.L_ROPE, "WV": WC.L_BAND, "FM-sh": WC.L_FDET, "FM-gr": WC.L_FDET, "FM-in": WC.L_FDET, "FM": WC.L_FOAM,
            "FM-loop": WC.L_LOOP, "FM-curl": WC.L_LOOP, "DR-b": WC.L_DROPB, "DR": WC.L_DROP}[r["grp"]]

# ---------------------------------------------------------------- wrap marks
SEAMS = {"BK": [("armhole L", "SL"), ("armhole R", "SR")], "FR": [("armhole", "SR")], "FL": [("armhole", "SL")], "SR": [("cap", None)], "SL": [("cap", None)]}
def seam_marks(vis, size, P, edge, band=4.5):
    """art touching a seam: [(s0, s1)] arc-length intervals (mm from the seam's top end) of art within `band` mm of it"""
    ln = PC.refs(size, P)[edge]
    pts = list(ln.coords)
    if P in ("SR", "SL"): pass
    U = unary_union([r["geom"] for r in vis if r["grp"] != "FM-loop"]).buffer(0.01)
    zone = ln.buffer(band); hit = U.intersection(zone)
    iv = []
    for p in polys(hit):
        ss = [ln.project(Point(c)) for c in p.exterior.coords]
        iv.append((min(ss), max(ss)))
    iv.sort(); merged = []
    for a, b in iv:
        if merged and a <= merged[-1][1] + 1.0: merged[-1][1] = max(merged[-1][1], b)
        else: merged.append([a, b])
    return [(round(a, 1), round(b, 1)) for a, b in merged if b - a > 1.0], ln.length

def wrap_check(res, size):
    """for each body armhole: art intervals on the body side vs on the sleeve cap (same seam, arc fraction of the seam
    from the shoulder point / cap top). Interval pairs that overlap (±6 mm on the body scale) count as aligned."""
    g, mt = MM.draft(size); out = {}
    for P, lst in SEAMS.items():
        if P in ("SR", "SL"): continue
        for edge, S in lst:
            bm, bl = seam_marks(res[P], size, P, edge)
            # body edges: back 'armhole R' runs ua -> sp; others sp -> ua. measure from the shoulder point
            pts = PC.refs(size, P)[edge].coords
            top_first = pts[0][1] < pts[-1][1]
            bfr = [((a / bl) if top_first else (1 - b / bl), (b / bl) if top_first else (1 - a / bl)) for a, b in bm]
            # sleeve cap: the half that sews to this armhole (back half for BK, front half for FR/FL)
            cap = PC.refs(size, S)["cap"]; cpts = list(cap.coords); top = min(range(len(cpts)), key=lambda i: cpts[i][1])
            view = "back" if P == "BK" else "front"; sgn = MM.HALF[(view, SLEEVE_SIDE[S])][1]
            half = LineString(cpts[top::-1] if cpts[0][0] * sgn > 0 else cpts[top:])
            U = unary_union([r["geom"] for r in res[S] if r["grp"] != "FM-loop"]).buffer(0.01)
            hit = U.intersection(half.buffer(4.5)); iv = []
            for p in polys(hit):
                ss = [half.project(Point(c)) for c in p.exterior.coords]; iv.append((min(ss) / half.length, max(ss) / half.length))
            iv.sort(); sm = []
            for a, b in iv:
                if sm and a <= sm[-1][1] + 0.005: sm[-1][1] = max(sm[-1][1], b)
                else: sm.append([a, b])
            sm = [(a, b) for a, b in sm if (b - a) * half.length > 1.0]
            tol = 6.0 / bl
            ok = [any(not (b1 < a0 - tol or a1 > b0 + tol) for a1, b1 in sm) for a0, b0 in bfr]
            out[f"{P} {edge} / {S} cap"] = dict(body=[(round(a, 3), round(b, 3)) for a, b in bfr], sleeve=[(round(a, 3), round(b, 3)) for a, b in sm],
                                               aligned=sum(ok), total=len(ok), body_len=round(bl, 1), cap_len=round(half.length, 1))
    return out


# ---------------------------------------------------------------- sleeve fold (QA 19 Oct: 20-50 mm bare band on the centre line)
def close_fold(its, P):
    """The render's sleeve art reaches the silhouette edge (the fold) in both views, but the trace drops the edge shading,
    so each mapped half stopped g = 8-25 mm short of the centre line and the sewn sleeve got a bare vertical band.
    Per half: g = 25th percentile of the innermost art per 10 mm row; the half is stretched from its underarm side
    (|x| = Xu fixed, |x| = g -> 0; stripes + rope lines point-mapped, curls + drops moved rigidly so they stay round).
    The fold highlight (tiny 'drops' within 6 mm of the centre line) is dropped. Returns (items, {sign: g})."""
    units = {}
    for r in its:
        if r.get("unit"): units.setdefault(r["unit"], []).append(r)
    drop = set()
    for u, rs in units.items():
        g_ = unary_union([r["geom"] for r in rs]); 
        if g_.area < 20 and abs(g_.centroid.x) < 6: drop.add(u)
    its = [r for r in its if r.get("unit") not in drop]
    out = []; G = {}
    for sgn in (1, -1):
        half = [r for r in its if r["geom"].centroid.x * sgn > 0]
        if not half: continue
        U = unary_union([r["geom"] for r in half]); b = U.bounds; rows = []
        for y in np.arange(b[1], b[3], 10.0):
            q = U.intersection(box(-400, y, 400, y + 10))
            if q.is_empty: continue
            xs = [min(abs(c[0]) for c in (p.exterior.coords)) for p in polys(q) if p.area > 2]
            if xs: rows.append(min(xs))
        g = float(np.clip(np.percentile(rows, 25), 0, 25)) if rows else 0.0
        Xu = max(abs(b[0]), abs(b[2])); G[sgn] = round(g, 1)
        if g < 1.0: out += half; continue
        def f(ax): return np.maximum(Xu - (Xu - ax) * Xu / (Xu - g), 0.0)
        side = box(0, -1000, 1000, 1000) if sgn > 0 else box(-1000, -1000, 0, 1000)
        moved = {}
        for r in half:
            if r.get("unit"):
                u = r["unit"]
                if u not in moved:
                    c = unary_union([q["geom"] for q in units[u]]).centroid; moved[u] = sgn * (float(f(abs(c.x))) - abs(c.x))
                out.append(dict(r, geom=affinity.translate(r["geom"], moved[u], 0)))
            else:
                gm = MM.map_geom(r["geom"], lambda x, y: (np.sign(x) * f(np.abs(x)), y), densify=1.0)
                gm = make_valid(gm).buffer(0).intersection(side)
                if not gm.is_empty: out.append(dict(r, geom=gm))
    return out, G

# ---------------------------------------------------------------- build
def build(size):
    t0 = time.time(); res = {"info": dict(size=size, grade=MM.GRADE[size][0], scale=MM.GRADE[size][1])}
    for P in PC.PIECES:
        clip = PC.clip_for(size, P).buffer(-0.4)        # 0.4 inside the keep-out: cleaning never crosses it
        its = items_for(size, P)
        if P in SLEEVE_SIDE: its, res.setdefault("fold_gap", {})[P] = close_fold(its, P)
        vis = visible(its, clip)
        vis = dst2.clean_vis(vis)
        vis = [dict(r, geom=r["geom"].intersection(clip).buffer(0)) for r in vis]
        vis = [r for r in vis if not r["geom"].is_empty and r["geom"].area > 0.3]
        vis = add_loops(vis)
        for r in vis: r["layer"] = layer_of(r)
        res[P] = vis
        u = unary_union([r["geom"] for r in vis]) if vis else Polygon()
        res["info"][P] = dict(objects=len(vis), area=round(u.area), bbox=[round(v, 1) for v in u.bounds] if vis else None,
                              lobes=len({r["unit"] for r in vis if r.get("unit") and r["grp"] == "FM"}),
                              drops=len({r["unit"] for r in vis if r.get("unit") and r["grp"] == "DR"}))
    res["info"]["wrap"] = wrap_check(res, size)
    pickle.dump(res, open(f"art_{size}.pkl", "wb"))
    print(size, {P: (res["info"][P]["objects"], res["info"][P]["area"], res["info"][P]["lobes"], res["info"][P]["drops"]) for P in PC.PIECES},
          {k: f"{v['aligned']}/{v['total']}" for k, v in res["info"]["wrap"].items()}, f"{time.time()-t0:.0f}s", flush=True)
    return res

def flat_png(size, res, path, ppm=1.6):
    """all five pieces laid out flat (pattern coords), art in thread colours, keep-out clip dashed"""
    from render import geom_to_path
    from motifs2 import HEX
    import cairosvg
    off = {"BK": (0, 0), "FR": (-640, 700), "FL": (-20, 700), "SR": (700, 160), "SL": (-700, 160)}
    o = []; bx = []
    for P in PC.PIECES:
        dx, dy = off[P]
        pan = affinity.translate(PC.panel(size, P), dx, dy); bx.append(pan.bounds)
        o.append(f'<path d="{geom_to_path(pan)}" fill="{WC.FABRIC}" stroke="#555" stroke-width="0.8"/>')
        o.append(f'<path d="{geom_to_path(affinity.translate(PC.clip_for(size, P), dx, dy))}" fill="none" stroke="#FF4040" stroke-width="0.5" stroke-dasharray="3 2"/>')
        for r in sorted(res[P], key=lambda r: r["layer"]):
            o.append(f'<path d="{geom_to_path(affinity.translate(r["geom"], dx, dy))}" fill="{HEX[r["col"]]}" fill-rule="evenodd"/>')
        o.append(f'<text x="{pan.bounds[0]}" y="{pan.bounds[1]-8}" font-size="16" font-family="Liberation Sans" fill="#333">{P} {PC.NAME[P]}</text>')
    x0 = min(b[0] for b in bx) - 20; y0 = min(b[1] for b in bx) - 40; x1 = max(b[2] for b in bx) + 20; y1 = max(b[3] for b in bx) + 20
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {x1-x0} {y1-y0}" width="{int((x1-x0)*ppm)}" height="{int((y1-y0)*ppm)}"><rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#fff"/>' + "".join(o) + \
          f'<text x="{x0+10}" y="{y0+24}" font-size="20" font-family="Liberation Sans">size {size} · grade {res["info"]["grade"]} ({res["info"]["scale"]*100:.0f} %)</text></svg>'
    cairosvg.svg2png(bytestring=svg.encode(), write_to=path)

if __name__ == "__main__":
    os.makedirs("out/art", exist_ok=True)
    for sz in sys.argv[1:] or WC.SIZES:
        r = build(sz); flat_png(sz, r, f"out/art/{sz}_flat.png")
