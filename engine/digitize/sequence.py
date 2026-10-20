"""Sequence v0 (ENGINE_PLAN M1; DIGITIZING_PRINCIPLES rules 5 and 6): back to front, cut what is covered.

  parts = sequence.underlap(parts, keep=1.0)      # exclusive (traced) neighbours: the lower one runs 1 mm under the upper
  parts = sequence.cut_under(parts, keep=1.0)     # overlaps removed except a keep-mm band under the upper part's edge
  parts, dropped = sequence.absorb_fragments(parts, min_mm2=2.0)
  stops = sequence.order(parts)                    # z-DAG -> [dict(thread, parts=[ids])], colour-batched

z-DAG: part a must sew before part b when a.z < b.z and they touch (within 0.5 mm). Parts that do not touch carry no
constraint, so a later same-colour part may join an earlier stop (fewer colour changes, like dst2.merge_stops). Kahn's
algorithm with colour batching: keep sewing the current thread while any part of it is free; then switch to the thread
with the most free area. Inside a stop, nearest-next from where the needle is."""
import math
from collections import defaultdict
from shapely.ops import unary_union
from shapely.strtree import STRtree


def clean(g):
    """valid, polygonal only (WKT rounding and set operations can leave invalid rings, lines or points)"""
    from shapely import make_valid
    from shapely.geometry import Polygon, MultiPolygon
    if g.is_empty: return Polygon()
    g = make_valid(g)
    ps = [q for q in ([g] if g.geom_type in ("Polygon", "MultiPolygon") else getattr(g, "geoms", [])) if q.geom_type in ("Polygon", "MultiPolygon")]
    if not ps: return Polygon()
    u = unary_union(ps).buffer(0)
    return u if u.geom_type in ("Polygon", "MultiPolygon") else Polygon()


def _higher(parts, i, tree, pad=0.0):
    p = parts[i]
    return [j for j in tree.query(p.geom.buffer(pad) if pad else p.geom, predicate="intersects") if parts[j].z > p.z]


def underlap(parts, keep=1.0):
    """each part grows `keep` mm into any HIGHER part it borders (traced partitions have no overlap; a seam needs one)"""
    if not parts: return parts
    for p in parts: p.geom = clean(p.geom)
    tree = STRtree([p.geom for p in parts]); grow = {}
    for i, p in enumerate(parts):
        hi = _higher(parts, i, tree, pad=keep)
        if hi:
            band = clean(p.geom.buffer(keep).intersection(unary_union([parts[j].geom for j in hi])))
            if not band.is_empty: grow[i] = clean(p.geom.union(band))
    for i, g in grow.items(): parts[i].geom = g
    return parts


def cut_under(parts, keep=1.0):
    """a part keeps only `keep` mm under every higher part that covers it (rule 6). Cut against the ORIGINAL higher
    geometry, so an overlap kept under one part is never cut by another part lower still."""
    if not parts: return parts
    orig = [clean(p.geom) for p in parts]; tree = STRtree(orig); new = {}
    for i, p in enumerate(parts):
        hi = [j for j in tree.query(orig[i], predicate="intersects") if parts[j].z > p.z]
        if not hi: continue
        cover = unary_union([orig[j].buffer(-keep) for j in hi])
        if not cover.is_empty: new[i] = clean(orig[i].difference(cover))
    for i, g in new.items(): parts[i].geom = g
    return parts


def absorb_fragments(parts, min_mm2=2.0):
    """drop the pieces of a part smaller than min_mm2 (slivers left by cut_under: they sit under a neighbour's edge, or
    are too small to sew); a part left with nothing is removed. Returns (parts, dropped ids)."""
    from digitize.techniques import polys
    keep, dropped = [], []
    for p in parts:
        ps = [q for q in polys(p.geom) if q.area >= min_mm2]
        if not ps: dropped.append(p.id); continue
        p.geom = unary_union(ps) if len(ps) > 1 else ps[0]; keep.append(p)
    return keep, dropped


def dag(parts, touch=0.5):
    tree = STRtree([p.geom for p in parts]); pred = defaultdict(set)
    for i, p in enumerate(parts):
        for j in tree.query(p.geom.buffer(touch), predicate="intersects"):
            if parts[j].z < p.z: pred[i].add(int(j))
    return pred


def order(parts, touch=0.5):
    pred = dag(parts, touch); n = len(parts); done = [False] * n; stops = []; pos = None
    left = {i: set(pred[i]) for i in range(n)}
    def free(): return [i for i in range(n) if not done[i] and not left[i]]
    cur = None
    while not all(done):
        f = free()
        if not f: raise RuntimeError("sequence: cycle in the z-DAG")
        same = [i for i in f if parts[i].thread == cur]
        if not same:
            area = defaultdict(float)
            for i in f: area[parts[i].thread] += parts[i].area
            minz = min(parts[i].z for i in f)                       # prefer the deepest free layer, then the most area
            cand = {parts[i].thread for i in f if parts[i].z == minz}
            cur = max(cand, key=lambda t: (area[t], t)); stops.append(dict(thread=cur, parts=[])); continue
        c = lambda i: parts[i].geom.representative_point().coords[0]
        i = min(same, key=lambda i: (math.dist(pos, c(i)) if pos else 0.0, parts[i].z, parts[i].id))
        done[i] = True; stops[-1]["parts"].append(parts[i].id); pos = c(i)
        for j in range(n):
            left[j].discard(i)
    return [s for s in stops if s["parts"]]
