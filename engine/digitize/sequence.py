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


def is_open(p):
    """an OPEN layer (blend / shading, rule 8) lies ON TOP of the fill below it: nothing is cut under it"""
    if not p.technique: return False
    from digitize import techniques
    return bool(techniques.get(p.technique).sequencing.get("open_layer"))


def cut_under(parts, keep=1.0):
    """a part keeps only `keep` mm under every higher part that covers it (rule 6). Cut against the ORIGINAL higher
    geometry, so an overlap kept under one part is never cut by another part lower still. Open layers (blend / shading,
    is_open) cut nothing: they are sewn over the fill they shade."""
    if not parts: return parts
    orig = [clean(p.geom) for p in parts]; tree = STRtree(orig); new = {}; opn = [is_open(p) for p in parts]
    for i, p in enumerate(parts):
        hi = [j for j in tree.query(orig[i], predicate="intersects") if parts[j].z > p.z and not opn[j]]
        if not hi: continue
        cover = unary_union([orig[j].buffer(-keep) for j in hi])
        if not cover.is_empty: new[i] = clean(orig[i].difference(cover))
    for i, g in new.items(): parts[i].geom = g
    return parts


LINE_KINDS = ("stratum_crack",)
KEEP_SMALL = ("cloud_wisp", "cloud_shade")      # deliberately small parts: a wisp, a shade layer (never a speck, never a target)


def merge_specks(parts, min_mm2=20.0, protected=(), min_protected_mm2=4.0, touch=0.3, line_kinds=LINE_KINDS, keep_small=KEEP_SMALL):
    """rule 1 (parts, not colours; LESSONS A22): a traced part smaller than min_mm2 (protected accents: min_protected_mm2)
    is a SPECK: merged into the touching part it shares the most border with, whatever zone that is (a navy shadow
    between leaves, a rock speck left between zones). Smallest first; a speck that touches nothing is kept. Line parts
    (cracks) and deliberately small parts (keep_small: wisps, shade layers) neither merge nor take specks.
    Returns (parts, [(speck id, into id)])."""
    from shapely.strtree import STRtree
    if not parts: return parts, []
    lim = lambda p: min_protected_mm2 if p.thread in protected else min_mm2
    fixed = set(line_kinds) | set(keep_small)
    alive = [True] * len(parts); geoms = [clean(p.geom) for p in parts]
    tree = STRtree(geoms); moves = []
    for i in sorted(range(len(parts)), key=lambda i: geoms[i].area):
        if parts[i].kind in fixed or parts[i].meta.get("keep_small") or not alive[i] or geoms[i].area >= lim(parts[i]): continue
        g = geoms[i].buffer(touch); best = None
        for j in tree.query(g, predicate="intersects"):
            j = int(j)
            if j == i or not alive[j] or parts[j].kind in fixed or parts[j].meta.get("keep_small"): continue
            share = g.intersection(geoms[j].buffer(touch)).area
            if share > 0 and (best is None or share > best[0]): best = (share, j)
        if best is None: continue
        j = best[1]; geoms[j] = clean(unary_union([geoms[j], geoms[i].buffer(min(touch, 0.15))]))
        alive[i] = False; moves.append((parts[i].id, parts[j].id))
    out = []
    for p, g, a in zip(parts, geoms, alive):
        if a: p.geom = g; out.append(p)
    return out, moves


def absorb_fragments(parts, min_mm2=2.0):
    """drop the pieces of a part smaller than min_mm2 (slivers left by cut_under: they sit under a neighbour's edge, or
    are too small to sew); a part left with nothing is removed. Returns (parts, dropped ids)."""
    from digitize.techniques import polys
    keep, dropped = [], []
    for p in parts:
        lim = float(p.meta.get("min_fragment_mm2", min_mm2))      # M3a: a deliberate small part (a 1-1.5 mm stud) states its own
        ps = [q for q in polys(p.geom) if q.area >= lim]
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
