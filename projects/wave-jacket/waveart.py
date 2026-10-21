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
import mockmap as MM, pieces as PC, wavetrace as WT, wrap as WR
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
            out.append(dict(kind="dot", anchor=c["filled"].centroid.coords[0], parts=parts, inner=inner, blue=blue, outline=c["filled"], hr=c.get("hr")))
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
                # Rev B seam-true wrap: harmonic map, render armhole -> cap by seam length (wrap.py). The sleeve's render
                # region is bounded by this size's armhole drawn back into the render, the same curve the body map uses.
                sm = WR.sleeve_map(view, SLEEVE_SIDE[P], size)
                quads[P] = sm.quad_px
                out[(view, P)] = (sm, sm.quad_px, "sleeve")
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

@functools.lru_cache(maxsize=None)
def lobe_owner(size, view):
    """lobe index -> piece: the piece whose render region holds the anchor, else the one its outline overlaps most"""
    maps = piece_maps(size); regs = {P: maps[(view, P)][1] for P in VIEW_PIECES[view]}; out = {}
    for i, lb in enumerate(traced(view)["lobes"]):
        a = Point(lb["anchor"]); hit = [P for P, r in regs.items() if r.contains(a)]
        if hit: out[i] = hit[0]; continue
        ov = {P: r.intersection(lb["outline"]).area for P, r in regs.items()}
        P = max(ov, key=ov.get)
        if ov[P] > 0: out[i] = P
    return out

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
        own = lobe_owner(size, view)
        for i, lb in enumerate(tr["lobes"]):
            if own.get(i) != P: continue                        # Rev B: every motif belongs to ONE piece; wrap.transfer carries its overflow
            a = lb["anchor"]
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

def keep_unit_slivers(before, after):
    """fix round 3 (PR #27 review 2, A14 drops): dst2.clean_vis deletes fill fragments < 1.5 mm2 or < 0.7 mm wide. Inside a
    small rigid motif that removed real parts of it - a spray drop's shade and grey crescents (2-8 mm2 of a 20 mm2 drop) -
    and its morphological close let the stripe UNDER the drop grow back over the hole, so the drop came out small and
    the stripe showed through. Every piece of a motif's pre-clean area that is no longer covered by the motif itself or by
    anything ABOVE it goes back to the motif: to the touching surviving region of the same thread family (cream / grey ->
    the drop body, blues -> the blue underside), longest shared edge; if the motif has no such region (a drop traced all
    grey) the piece is restored as its own region in its own thread, thickened to the 0.7 mm sewable minimum.
    Returns (after, n pieces kept, mm2 kept)."""
    from collections import defaultdict
    FAMS = lambda c: "foam" if c in ("w1", "w2", "w3", "g1") else "blue"
    pre = defaultdict(list)
    for r in before:
        if r.get("unit") and r["st"] not in ("bean", "run"): pre[r["unit"]].append(r)
    geoms = [r["geom"] for r in after]; tree = shapely.STRtree(geoms)
    by_u = defaultdict(list)
    for i, r in enumerate(after):
        if r.get("unit") and r["st"] not in ("bean", "run"): by_u[r["unit"]].append(i)
    n = 0; area = 0.0; extra = []
    for u, rs in pre.items():
        P0 = unary_union([r["geom"] for r in rs]).buffer(0); zmax = max(r["z"] for r in rs)
        near = [int(j) for j in tree.query(P0)]
        cover = [geoms[j] for j in near if after[j].get("unit") == u or after[j]["z"] > zmax]
        lost = P0.difference(unary_union(cover).buffer(0)) if cover else P0
        for q in polys(lost.buffer(0)):
            if q.area < 0.05: continue
            src = max(rs, key=lambda r: r["geom"].intersection(q).area)
            best, bl = None, 0.0
            for i in by_u.get(u, []):
                g = after[i]["geom"]
                if FAMS(after[i]["col"]) != FAMS(src["col"]) or g.distance(q) > 0.3: continue
                l = q.buffer(0.15).intersection(g).area
                if best is None or l > bl: best, bl = i, l
            if best is not None:
                after[best] = dict(after[best], geom=unary_union([after[best]["geom"], q.buffer(0.02)]).buffer(0))
            elif q.area >= 1.0:
                extra.append(dict(src, geom=q.buffer(0.1).buffer(0), st="satin"))
            else: continue
            n += 1; area += q.area
    return after + extra, n, round(area, 1)

def drop_angles(vis):
    """fix round 3 (PR #27 review 2, A16): a spray drop is a small CONSTRUCTED blob, so it gets one declared direction for the
    whole motif: satin stitches ALONG its long axis (minimum rotated rectangle of the drop's union: w1 + shade + grey +
    blue underside), never the turning / 'auto' satin across it. Stored as r['ang'] (degrees, hatch convention) with
    r['decl'] = 'drop long axis'; wavecore sews it as one fixed-angle satin (split > 7 mm)."""
    from collections import defaultdict
    import stitchrender as SR
    du = defaultdict(list)
    for r in vis:
        if r.get("unit") and r["grp"] == "DR": du[r["unit"]]
    for r in vis:
        if r.get("unit") in du and r["st"] not in ("bean", "run"): du[r["unit"]].append(r["geom"])
    ang = {}
    for u, gs in du.items():
        g = unary_union(gs).convex_hull
        if g.area <= 0: continue
        ang[u] = round(float(SR.auto_angle(g) - 90.0) % 180.0, 1)
    n = 0
    for i, r in enumerate(vis):
        if r.get("unit") in ang and r["st"] not in ("bean", "run"):
            vis[i] = dict(r, st="satin", ang=ang[r["unit"]], decl="drop long axis"); n += 1
    return vis, len(ang)

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
    eyes = {}
    for r in vis:
        if r["grp"] == "FM-gr" and r.get("unit") in U:
            e = eyes.get(r["unit"])
            if e is None or r["geom"].area > e[1]: eyes[r["unit"]] = (r["geom"].centroid, r["geom"].area)
    eyes = {k: v[0] for k, v in eyes.items()}
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
            # Rev B (review item 4): ONE continuous curl cord per curl - a spiral from the curl's eye (its grey hollow, else
            # its innermost point) out to 0.8 mm inside the edge, 1.4 turns, the longest unbroken piece kept
            eye = eyes.get(u)
            inner = g.buffer(-0.8)
            if inner.is_empty: continue
            c = eye if (eye is not None and inner.contains(eye)) else inner.representative_point()
            Rm = max(1.0, float(c.distance(g.exterior)) if g.geom_type == "Polygon" else 0.42 * math.sqrt(g.area / math.pi))
            Rm = max(Rm, 0.42 * math.sqrt(g.area / math.pi))
            hand = 1 if (sum(map(ord, str(u))) % 2) else -1
            th = np.linspace(0, 2 * math.pi * 1.4, 160)
            rr = 0.9 + (Rm * 0.95 - 0.9) * th / th[-1]
            sp = LineString([(c.x + r_ * math.cos(hand * t_), c.y + r_ * math.sin(hand * t_)) for r_, t_ in zip(rr, th)])
            sp = sp.intersection(inner)
            segs = [x for x in getattr(sp, "geoms", [sp]) if x.geom_type == "LineString" and not x.is_empty]
            if not segs: continue
            seg = max(segs, key=lambda x: x.length)
            if seg.length < 4: continue
            q = seg.buffer(0.35, cap_style="round")
            for p in polys(q.intersection(g)):
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

def aspect(p):
    mrr = p.minimum_rotated_rectangle
    if mrr.geom_type != "Polygon": return 1.0
    cs = list(mrr.exterior.coords); a = math.dist(cs[0], cs[1]); b = math.dist(cs[1], cs[2])
    return max(a, b) / max(min(a, b), 1e-6)

def curl_direction(vis):
    """LESSONS A16: stitch direction is a design decision for every motif. Foam rows run ALONG THE CURL: each padded curl
    is cut into sectors around its eye (its grey hollow, else its centre) and every sector is tatami along the tangent of
    the curl there (concentric rows = the curl cord / loop look, coherent with the loop spiral and the curl cord sewn on top).
    Blob-shaped shades / hollows / inner blues (aspect < 2.5) get the same tangential tatami instead of 'auto' satin."""
    by = {}
    for r in vis:
        if r.get("unit"): by.setdefault(r["unit"], []).append(r)
    eye = {}
    for u, rs in by.items():
        gr = [r["geom"] for r in rs if r["grp"] == "FM-gr"]
        fm = [r["geom"] for r in rs if r["grp"] == "FM"]
        if gr: eye[u] = max(gr, key=lambda g: g.area).centroid
        elif fm: eye[u] = unary_union(fm).centroid
    out = []
    for r in vis:
        u = r.get("unit"); e = eye.get(u)
        tang = lambda c: (math.degrees(math.atan2(c.y - e.y, c.x - e.x)) + 90.0) % 180.0
        if e is not None and r["grp"] == "FM" and r["st"] == "padded":
            g = r["geom"]; R_ = max(math.dist((e.x, e.y), xy) for p in polys(g) for xy in p.exterior.coords) + 2
            n = int(np.clip(round(g.length / 14.0), 4, 12))
            for k in range(n):
                a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
                wedge = Polygon([(e.x, e.y)] + [(e.x + R_ * math.cos(t), e.y + R_ * math.sin(t)) for t in np.linspace(a0, a1, 6)])
                q = g.intersection(wedge)
                for pq in polys(q):
                    if pq.area < 0.3: continue
                    out.append(dict(r, geom=pq, ang=tang(pq.centroid)))
            continue
        if e is not None and r["grp"] in ("FM-sh", "FM-gr", "FM-in") and r["st"] == "satin":
            g = r["geom"]
            if aspect(g) < 2.5 and g.area > 1.0:
                out.append(dict(r, st="tatami", ang=tang(g.centroid))); continue
        out.append(r)
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


def drop_fold_highlight(its):
    """the render's sleeve-fold highlight traced as tiny 'drops' on the fold (QA 19 Oct): rigid units < 20 mm2 within 6 mm
    of the sleeve centre line"""
    units = {}
    for r in its:
        if r.get("unit"): units.setdefault(r["unit"], []).append(r)
    drop = {u for u, rs in units.items() if (lambda g: g.area < 20 and abs(g.centroid.x) < 6)(unary_union([r["geom"] for r in rs]))}
    def dash(r):          # the fold highlight traced as short thin stripe / rope dashes ON the centre line (SL Rev A review)
        if r.get("unit") or r["grp"] not in ("WV", "RP"): return False
        b = r["geom"].bounds
        return abs(r["geom"].centroid.x) < 8 and (b[2] - b[0]) < 6 and width(r["geom"]) < 3.0
    def sliver(r):        # the fold highlight traced as thin foam / stripe slivers along the centre line (SL cap, Rev B)
        g = r["geom"]; w_ = width(g)
        return abs(g.centroid.x) < 10 and w_ < 1.3 and (g.length / 2) / max(w_, 0.1) > 8
    return [r for r in its if r.get("unit") not in drop and not dash(r) and not sliver(r)]

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

# ---------------------------------------------------------------- Rev B structure (review items 4 + 5, LESSONS A13)
FLECK_W, FLECK_A = 2.0, 30.0        # stand-alone flecks
HOLE_W, HOLE_A = 3.2, 90.0          # dark dashes INSIDE a band (the render's stitch shadows) - closed into the band
def clean_flecks(its):
    """stripes = continuous cords (review item 5): drop the render's sub-2 mm tone flecks and close the dark dashes inside
    the pale bands (holes < 3.2 mm wide or < 90 mm2: the render's stitch texture, not art) into the band around them;
    pieces of another tone that sat in such a hole are dropped"""
    out = []; n = 0; filled = []
    for r in its:
        if r["grp"] != "WV" or r.get("cont"): out.append(r); continue
        for p in polys(r["geom"]):
            if width(p) < FLECK_W and p.area < FLECK_A: n += 1; continue
            keep, gone = [], []
            for h in p.interiors:
                hp = Polygon(h)
                (gone if (hp.area < HOLE_A or width(hp) < HOLE_W) else keep).append(hp)
            if gone: p = Polygon(p.exterior, [k.exterior for k in keep]); filled += [(g, r["col"]) for g in gone]
            out.append(dict(r, geom=p))
    if filled:
        F = shapely.STRtree([g for g, _ in filled]); res = []
        for r in out:
            if r["grp"] == "WV" and not r.get("cont") and r["geom"].area < HOLE_A:
                hit = [filled[int(j)] for j in F.query(r["geom"])]
                if any(c != r["col"] and g.buffer(0.3).intersection(r["geom"]).area > 0.8 * r["geom"].area for g, c in hit): n += 1; continue
            res.append(r)
        out = res
    # bare slits BETWEEN two tones of a band (the render's dark stitch shadows read as fabric): closed into the
    # neighbouring tone with the longest shared edge
    bands = [r for r in out if r["grp"] == "WV"]
    if bands:
        U = unary_union([r["geom"] for r in bands])
        others = unary_union([r["geom"] for r in out if r["grp"] != "WV"]) if any(r["grp"] != "WV" for r in out) else Polygon()
        slits = U.buffer(1.3, join_style=2).buffer(-1.3, join_style=2).difference(U).difference(others)
        T = shapely.STRtree([r["geom"] for r in bands]); add = []
        for g in polys(slits):
            if g.area < 0.5 or g.area > 150: continue
            best, bl = None, 0.0
            for j in T.query(g.buffer(0.2)):
                l_ = bands[int(j)]["geom"].buffer(0.2).intersection(g.boundary).length
                if l_ > bl: best, bl = bands[int(j)], l_
            if best is not None: add.append(dict(best, geom=g.buffer(0.15).buffer(0)))
        out += add; n += len(add)
    return out, n

def rope_lines(its, half=1.2, join=16.0, max_turn=32.0):
    """rope lines = continuous 2.4 mm cream cords: each traced rope fragment -> its centre line; fragment ends that point
    at each other (gap <= join, turn <= max_turn deg) and whose bridge lies on the stripes are joined; every line is then
    one uniform-width satin cord (half-width `half`)"""
    rp = [r for r in its if r["grp"] == "RP"]; rest = [r for r in its if r["grp"] != "RP"]
    if not rp: return its, 0
    bands = unary_union([r["geom"] for r in its if r["grp"] == "WV"]).buffer(1.5)
    lines = []
    for r in rp:
        for p in polys(r["geom"]):
            if p.area < 1.0: continue
            ln = dst2.centreline(p) if (p.length / 2) / max(width(p), 0.1) > 2.0 else None
            if ln is None or ln.length < 1.5:
                b = p.minimum_rotated_rectangle.exterior.coords
                e = sorted([LineString([b[i], b[i + 1]]) for i in range(4)], key=lambda l: -l.length)[0]
                c = p.centroid; dx, dy = (e.coords[1][0] - e.coords[0][0]) / 2, (e.coords[1][1] - e.coords[0][1]) / 2
                ln = LineString([(c.x - dx, c.y - dy), (c.x + dx, c.y + dy)])
            lines.append([tuple(map(float, q)) for q in ln.coords])
    def tang(l, end):
        a, b = (np.array(l[0]), np.array(l[min(3, len(l) - 1)])) if end == 0 else (np.array(l[-1]), np.array(l[max(0, len(l) - 4)]))
        v = a - b; n_ = np.hypot(*v); return v / n_ if n_ > 1e-6 else v
    from scipy.spatial import cKDTree
    E = [(i, e, np.array(l[0] if e == 0 else l[-1]), tang(l, e)) for i, l in enumerate(lines) for e in (0, 1)]
    cand = []
    if len(E) > 1:
        for a, b in cKDTree(np.array([x[2] for x in E])).query_pairs(join):
            (i, ei, pi, ti), (j, ej, pj, tj) = E[a], E[b]
            if i == j: continue
            v = pj - pi; d = float(np.hypot(*v))
            if d < 0.3: continue
            v = v / d
            if np.degrees(np.arccos(np.clip(ti @ v, -1, 1))) > max_turn or np.degrees(np.arccos(np.clip(-tj @ v, -1, 1))) > max_turn: continue
            cand.append((d, a, b))
    cand.sort(); used = set(); parent = list(range(len(lines))); link = {}
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    joined = 0
    for d, a, b in cand:
        if a in used or b in used: continue
        i, j = E[a][0], E[b][0]
        if find(i) == find(j): continue
        if not bands.contains(LineString([E[a][2], E[b][2]])): continue
        used |= {a, b}; parent[find(i)] = find(j); link[a] = b; link[b] = a; joined += 1
    # walk chains: start at a free end (endpoint index 2*i + e), alternate line body -> link
    seen = set(); chains = []
    for start in range(len(E)):
        li = E[start][0]
        if li in seen or start in link: continue
        cur, pts = start, []
        while True:
            i, e = E[cur][0], E[cur][1]; seen.add(i)
            body = lines[i] if e == 0 else lines[i][::-1]; pts += body
            other = 2 * i + (1 - e)
            if other in link: cur = link[other]
            else: break
        chains.append(pts)
    for i, l in enumerate(lines):
        if i not in seen: chains.append(l)
    lines = chains
    out = list(rest)
    z = Z["rope"]
    for l in lines:
        g = LineString(l).simplify(0.2)
        if g.length < 2.0: continue
        p = g.buffer(half, cap_style="round", join_style="round")
        for q in polys(p): out.append(dict(R("w1", q, "tatami", "auto", "RP"), z=z, unit=None))     # A16: rows ALONG the cord
    return out, joined

def grey_ridges(its, w=1.1):
    """the curl hollows: flat grey blobs -> the close-up's thin RIDGED grey lines. Each grey blob wider than 1.6 mm becomes
    a 1.1 mm grey satin ridge along its centre line; the rest of the blob is foam shade (it stays a hollow, in shade)"""
    out = []; n = 0
    for r in its:
        if r["grp"] != "FM-gr" or width(r["geom"]) < 0.8 * w * 1.45: out.append(r); continue
        for p in polys(r["geom"]):
            ln = dst2.centreline(p) if p.area > 1.5 else None
            if ln is None:
                out.append(dict(r, geom=p)); continue
            ridge = ln.buffer(w / 2, cap_style="round").intersection(p).buffer(0)
            sh = p.difference(ridge.buffer(0.05)).buffer(0)
            for q in polys(ridge):
                if q.area > 0.3: out.append(dict(r, geom=q, st="satin"))
            for q in polys(sh):
                if q.area > 0.4: out.append(dict(r, col="w3", grp="FM-sh", geom=q, st="satin"))
            n += 1
    return out, n

# ---------------------------------------------------------------- under the collar fall (founder 19 Oct)
def under_collar(art, size):
    """The render hides the front under the collar points, so the art stopped at the collar-point V. Founder: embroider under
    the collar fall up to the neckline keep-out (6 mm). GENERATED (A12: nothing in any reference shows it): the art beside
    the V is mirrored across the V's outer edge (collar point -> shoulder end of the collar), so every stripe and crest that
    meets that edge continues into the V without a break; the copy is clipped to the V minus the neck keep-out. Also keeps
    the front continuous when the collar is worn up. Items carry gen='under collar'. Returns {P: items added}."""
    import front as FRT
    out = {}
    for P, C in (("FL", FRT.COLLAR_L), ("FR", FRT.COLLAR_R)):
        sg = 1 if P == "FL" else -1
        a, b = np.array([sg * 72.0, 66.0]), np.array([sg * 176.0, -76.0])          # V point -> shoulder end of the collar
        H = C.intersection(PC.panel(size, P)).difference(PC.refs(size, P)["neck"].buffer(6.0)).buffer(0)
        t = (b - a) / np.hypot(*(b - a)); ang = np.degrees(np.arctan2(t[1], t[0]))
        def refl(g):
            g = affinity.rotate(affinity.translate(g, -a[0], -a[1]), -ang, origin=(0, 0))
            g = affinity.scale(g, 1, -1, origin=(0, 0))
            return affinity.translate(affinity.rotate(g, ang, origin=(0, 0)), a[0], a[1])
        Hm = refl(H); add = []
        for r in art[P]:
            if r.get("gen") or not r["geom"].intersects(Hm): continue
            g = r["geom"].intersection(Hm)
            if g.is_empty or g.area < 0.3: continue
            g = refl(g).intersection(H).buffer(0)
            if g.is_empty or g.area < 0.3: continue
            add.append(dict(r, geom=g, gen="under collar", unit=(r["unit"] + "~uc") if r.get("unit") else None))
        art[P] += add; out[P] = len(add)
    return out

# ---------------------------------------------------------------- build
def build(size):
    t0 = time.time(); res = {"info": dict(size=size, grade=MM.GRADE[size][0], scale=MM.GRADE[size][1])}
    art = {P: items_for(size, P) for P in PC.PIECES}
    for P in SLEEVE_SIDE: art[P] = drop_fold_highlight(art[P])
    res["info"]["silhouette_seams"] = WR.silhouettes(art, size)          # smooth seam warp (seamwarp.py)
    res["warp_grid"] = res["info"]["silhouette_seams"].pop("grid")
    res["info"]["transfer"] = WR.transfer(art, size)                       # overflow across every seam
    res["info"]["under_collar"] = under_collar(art, size)
    res["info"]["maps"] = {f"{v}/{s}": dict(fold_frac=round(WR.sleeve_map(v, s, size).fold_frac, 4)) for v in ("back", "front") for s in "LR"}
    st_log = {}
    for P in PC.PIECES:
        art[P], nf = clean_flecks(art[P]); art[P], nj = rope_lines(art[P]); art[P], ng = grey_ridges(art[P])
        st_log[P] = dict(flecks_dropped=nf, rope_joins=nj, grey_blobs_to_ridges=ng)
    res["info"]["structure"] = st_log
    for P in PC.PIECES:
        clip = PC.clip_for(size, P).buffer(-0.4)        # 0.4 inside the keep-out: cleaning never crosses it
        its = art[P]
        vis = visible(its, clip)
        vis0 = vis
        vis = dst2.clean_vis(vis)
        vis, nk, ak = keep_unit_slivers(vis0, vis); st_log[P]["unit_slivers_kept"] = (nk, ak)
        vis = [dict(r, geom=r["geom"].intersection(clip).buffer(0)) for r in vis]
        vis = [r for r in vis if not r["geom"].is_empty and r["geom"].area > 0.3]
        vis = add_loops(vis)
        vis = curl_direction(vis)
        vis, nd = drop_angles(vis); st_log[P]["drops_declared"] = nd
        for r in vis: r["layer"] = layer_of(r)
        res[P] = vis
        u = unary_union([r["geom"] for r in vis]) if vis else Polygon()
        res["info"][P] = dict(objects=len(vis), area=round(u.area), bbox=[round(v, 1) for v in u.bounds] if vis else None,
                              lobes=len({r["unit"] for r in vis if r.get("unit") and r["grp"] == "FM"}),
                              drops=len({r["unit"] for r in vis if r.get("unit") and r["grp"] == "DR"}))
    res["info"]["wrap"] = {"seams": len(WR.seams(size))}
    res["marks"] = WR.match_marks({P: res[P] for P in PC.PIECES}, size)
    pickle.dump(res, open(f"art_{size}.pkl", "wb"))
    print(size, {P: (res["info"][P]["objects"], res["info"][P]["area"], res["info"][P]["lobes"], res["info"][P]["drops"]) for P in PC.PIECES},
          res["info"]["silhouette_seams"], res["info"]["transfer"], res["info"]["maps"], f"{time.time()-t0:.0f}s", flush=True)
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
