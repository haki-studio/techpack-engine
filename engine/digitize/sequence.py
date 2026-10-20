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


KEEP_TINY = ("knot",)                           # M3b: a bead is a designed 1 mm2 object, not a cut-under sliver
NO_UNDERLAP = KEEP_TINY                         # M3b: beads sew their declared knots: their outline never grows
SEAM_MM = {"floret": 0.3}                       # M3b: a floret is knocked out of the canopy, so the full 1 mm underlap is a
                                                # SECOND layer ring under it (PR #10 review: florets 9.4 mm/mm2); 0.3 mm
                                                # closes the seam (no-underlap left 9 gaps >= 0.1 mm2 at floret edges)
SEAM_MM["crown_clump_lit"] = 0.3                # --- M4c --- lit pieces are knocked out of their dark clump the same way
                                                # (PR #14 review: grown lit pieces' 1 mm underlap, density flags 167 -> 181)


def underlap(parts, keep=1.0):
    """each part grows `keep` mm into any HIGHER part it borders (traced partitions have no overlap; a seam needs one)"""
    if not parts: return parts
    for p in parts: p.geom = clean(p.geom)
    tree = STRtree([p.geom for p in parts]); grow = {}
    for i, p in enumerate(parts):
        if p.kind in NO_UNDERLAP: continue                  # M3b: beads sew their knots
        k = SEAM_MM.get(p.kind, keep)                       # M3b: florets only overlap their knocked-out canopy by a seam
        hi = _higher(parts, i, tree, pad=k)
        if hi:
            band = clean(p.geom.buffer(k).intersection(unary_union([parts[j].geom for j in hi])))
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
KEEP_SMALL += ("floret", "knot", "branch", "trunk_strip", "crown_clump_lit")   # M3b: floret parts, branches, lit clump sides are motifs


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


def absorb_fragments(parts, min_mm2=2.0, tiny_kinds=KEEP_TINY, tiny_mm2=0.5):
    """drop the pieces of a part smaller than min_mm2 (slivers left by cut_under: they sit under a neighbour's edge, or
    are too small to sew); a part left with nothing is removed. Returns (parts, dropped ids)."""
    from digitize.techniques import polys
    keep, dropped = [], []
    for p in parts:
        lim = float(p.meta.get("min_fragment_mm2", tiny_mm2 if p.kind in tiny_kinds else min_mm2))   # M3a per-part limit, else M3b bead floor
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


# ================================================================== M4g: full sequencing (ENGINE_PLAN M4)
# Rule 5 (back to front with hidden travel, planned entry / exit, knocked-out details before their fill) and rule 6
# (cut what is covered keeping 1 mm, min fragment, <= 2 stacked layers, stitch budget), colour stops minimised without
# breaking the z-DAG. sequence.order / dag above are the M1 v0 and stay unchanged (svgrun.order_complete uses dag).
#
#   SQ.apply_hints(parts)                       meta["z"], meta["knockout_of"] (see HINTS below)
#   SQ.limit_stack(parts, max_layers=2)         cut the LOWEST part wherever 3+ fill parts overlap
#   SQ.order_v1(parts)                          z-DAG (+ hint edges) -> colour stops, fewest stops first
#   SQ.sequence_blocks(plan)                    in-stop part order + each part's block order / orientation by its
#                                               planned entry and exit (the needle's real position)
#   SQ.budget(plan, stitches_max)               stitch estimate vs the budget (rule 6)
#   SQ.report(plan)                             stops, colour changes, z-DAG violations (must be 0), hints honoured
#
# HINTS (the contract for splitters, e.g. M3a buildings / M3b trees; all optional, read from Part.meta):
#   meta["z"]            float: replaces part.z for sequencing (sew depth: lower sews first where parts touch)
#   meta["seq_after"]    [selector]: this part sews AFTER every part matching a selector, touching or not
#   meta["seq_before"]   [selector]: this part sews BEFORE every part matching a selector
#                        selector = a part id, "kind:<kind>", "zone:<zone>" or "group:<meta group>"
#   meta["knockout_of"]  part id (or [ids]): this detail is KNOCKED OUT of that fill (rule 5): the fill gets a hole
#                        (fill minus the detail), the detail's z is set just below the fill's, so it sews first and the
#                        fill covers its edge by the underlap keep (1 mm)
#   meta["group"]        str: parts of one group (a building, a tree) are sewn together inside a stop when the DAG allows
#   meta["entry"]        (x, y) mm: preferred needle-in point of the part (planned entry)
# A hint that names no part raises HintError (a typo must not silently drop an order the splitter asked for); a hint
# cycle raises too. A hint wins over a contradicting z edge (seq_after on a part that is lower).
import numpy as _np

SEQ_DEFAULTS = dict(planner="m4", keep_mm=1.0, min_fragment_mm2=2.0, max_layers=2, stack_reach_mm=1.0, stack_keep_band_mm=None, touch=0.5, orient=True, stop_lookahead=True,
                    inner_travel=True, group_bonus_mm=3.0)
LINE_STYPES = ("run", "bean")


class HintError(ValueError):
    pass


from digitize.techniques.specialty import FOAM      # M6 (PR #7): a puff thread / stop key ends in "+foam"


def is_foam(thread):
    return isinstance(thread, str) and thread.endswith(FOAM)


def _stype(p):
    if not p.technique: return "tatami"
    from digitize import techniques
    return techniques.get(p.technique).stype


def _ids(v): return [v] if isinstance(v, str) else list(v or [])


def _select(parts, sel, me=None):
    if sel.startswith("kind:"): out = [i for i, p in enumerate(parts) if p.kind == sel[5:]]
    elif sel.startswith("zone:"): out = [i for i, p in enumerate(parts) if p.zone == sel[5:]]
    elif sel.startswith("group:"): out = [i for i, p in enumerate(parts) if p.meta.get("group") == sel[6:]]
    else: out = [i for i, p in enumerate(parts) if p.id == sel]
    out = [i for i in out if i != me]
    if not out:              # a typo ("kind:rooff") must not silently drop an order the splitter asked for (PR #8 review)
        raise HintError(f"sequence hint {sel!r} (on part {parts[me].id if me is not None else '?'}) matches no other part")
    return out


def apply_hints(parts):
    """meta["z"] and meta["knockout_of"] (HINTS). Returns dict(z=[ids], knockouts=[(detail, fill)])."""
    rep = dict(z=[], knockouts=[])
    for p in parts:
        if "z" in p.meta: p.z = float(p.meta["z"]); rep["z"].append(p.id)
    by_id = {p.id: p for p in parts}
    for p in parts:
        for f in _ids(p.meta.get("knockout_of")):
            if f not in by_id: raise HintError(f"part {p.id}: knockout_of {f!r} names no part")
            fill = by_id[f]
            fill.geom = clean(fill.geom.difference(p.geom))
            p.z = min(p.z, fill.z - 1e-3); rep["knockouts"].append((p.id, f))
    return rep


def _over_k(g, others, k):
    """the part of g covered by at least k of `others`"""
    from itertools import combinations
    pieces = [clean(g.intersection(o)) for o in others]
    pieces = [q for q in pieces if not q.is_empty]
    acc = []
    for c in combinations(range(len(pieces)), k):
        q = pieces[c[0]]
        for j in c[1:]:
            q = q.intersection(pieces[j])
            if q.is_empty: break
        if not q.is_empty: acc.append(q)
    return clean(unary_union(acc)) if acc else None


def limit_stack(parts, max_layers=2, min_mm2=0.05, reach=0.0, keep_band=0.0):
    """rule 6: never more than max_layers stacked fill layers. Wherever more overlap (the 1 mm underlap bands of two
    lower parts meeting under a third, a neighbour's band under a lobe + its open shade), the LOWEST part loses that
    area: it is buried under max_layers others there, so nothing visible changes and no gap opens (by induction from the
    top, every cut point keeps max_layers parts above it). Line parts (run / bean) are not layers. Order = (z, index),
    the total order the z-DAG uses.
    reach > 0: the file gate counts layers per 1 mm CELL (qa.stack_map), so a lower part's band under the SEAM of two
    higher parts (each of them within `reach` mm) is a third layer in that cell although no point has three. With reach,
    the lower part also loses the band it has UNDER a higher part within `reach` of a second higher part (only area that
    is already covered: its visible area is never cut). keep_band > 0 (PR #8 review, rule 6 "keep ~1 mm"): the reach cut
    never takes the band within keep_band mm of the lower part's VISIBLE edge, so its seams keep their underlap; only a
    point that is really 3 fill parts deep (the exact cut above) loses it. Returns [(part id, mm2 cut)]."""
    lay = [i for i, p in enumerate(parts) if _stype(p) not in LINE_STYPES]
    if not lay: return []
    geoms = {i: clean(parts[i].geom) for i in lay}
    rank = {i: (parts[i].z, i) for i in lay}
    tree = STRtree([geoms[i] for i in lay]); cut = []
    for i in sorted(lay, key=lambda i: rank[i]):
        g = geoms[i]
        if g.is_empty: continue
        q = g.buffer(reach) if reach else g
        hi = [lay[int(j)] for j in tree.query(q, predicate="intersects") if rank[lay[int(j)]] > rank[i]]
        hi = [j for j in hi if q.intersection(geoms[j]).area > min_mm2]
        if len(hi) < max_layers: continue
        hs = [geoms[j] for j in hi]
        over = _over_k(g, hs, max_layers)
        if reach:
            near = _over_k(g, [h.buffer(reach) for h in hs], max_layers)
            if near is not None:
                H = unary_union(hs)
                near = clean(near.intersection(H))                        # only where it is already under a higher part
                if keep_band and not near.is_empty:                       # rule 6: the seam keeps its underlap band
                    near = clean(near.difference(clean(g.difference(H)).buffer(keep_band)))
                over = near if over is None else clean(unary_union([over, near]))
        if over is None or over.area <= min_mm2: continue
        ng = clean(g.difference(over))
        cut.append((parts[i].id, round(g.area - ng.area, 2))); geoms[i] = ng
    for i in lay: parts[i].geom = geoms[i]
    return cut


def seam_report(parts, min_depth=0.5, near=0.3, visible=True, any_lower=False):
    """rule 6 (keep ~1 mm under a seam), measured on the plan geometry: for every pair of touching FILL parts of
    different z, the seam = the higher part's outline within `near` mm of the lower part; the seam HAS underlap where the
    lower part runs at least `min_depth` mm under the higher one there (the overlap, opened by min_depth, reaches the
    outline). any_lower=True: the seam is backed by ANY lower fill running min_depth under the higher part there (what
    keeps bare fabric out when the upper edge pulls in), not only by the pair's own lower part. visible=True: seam stretches covered by a third, higher part are left out (buried, not on the garment).
    Equal-z neighbours (a traced partition: neither sews first) are reported apart. Returns dict(seam_mm,
    without_mm, pct_without, equal_z_seam_mm, pairs, pairs_without)."""
    lay = [p for p in parts if _stype(p) not in LINE_STYPES and not clean(p.geom).is_empty]
    G = [clean(p.geom) for p in lay]; tree = STRtree(G)
    seam = without = eq = 0.0; pairs = pw = 0; vis = {}
    for i, p in enumerate(lay):
        for j in tree.query(G[i].buffer(near), predicate="intersects"):
            j = int(j)
            if j <= i: continue
            lo, hi = (i, j) if lay[i].z < lay[j].z else (j, i)
            S = G[hi].boundary.intersection(G[lo].buffer(near))
            if S.is_empty or S.length < 0.05: continue
            if lay[i].z != lay[j].z:                       # the seam is where the LOWER part's VISIBLE area meets the higher
                if lo not in vis:                          # outline, not where it runs under this or another higher part
                    up = [G[int(k)] for k in tree.query(G[lo], predicate="intersects") if lay[int(k)].z > lay[lo].z]
                    vis[lo] = clean(G[lo].difference(unary_union(up))) if up else G[lo]
                S = S.intersection(vis[lo].buffer(near))
                if S.is_empty or S.length < 0.05: continue
            if visible:                                   # a seam buried under a third, higher part is not a seam on the garment
                top = [G[int(k)] for k in tree.query(S, predicate="intersects") if lay[int(k)].z > lay[hi].z]
                if top: S = S.difference(unary_union(top))
                if S.is_empty or S.length < 0.05: continue
            if lay[i].z == lay[j].z: eq += S.length; continue
            if any_lower:
                low = [G[int(k)] for k in tree.query(G[hi].buffer(near), predicate="intersects") if lay[int(k)].z < lay[hi].z]
                U = unary_union(low).intersection(G[hi]) if low else G[lo].intersection(G[hi])
            else: U = G[lo].intersection(G[hi])
            deep = U.buffer(-min_depth / 2).buffer(min_depth / 2 + 0.15)   # +0.15: square corners survive the opening if not U.is_empty else U
            cov = S.intersection(deep).length if not deep.is_empty else 0.0
            seam += S.length; without += S.length - cov; pairs += 1; pw += (cov < 0.05 * S.length)
    return dict(seam_mm=round(seam, 1), without_mm=round(without, 1), pct_without=round(100 * without / max(seam, 1e-9), 1),
                equal_z_seam_mm=round(eq, 1), pairs=pairs, pairs_without=pw, min_depth=min_depth, visible=visible, any_lower=any_lower)


def stack_count(parts):
    """max number of fill parts over any point (exact, from the part geometry): the plan-level rule 6 check"""
    lay = [clean(p.geom) for p in parts if _stype(p) not in LINE_STYPES]
    lay = [g for g in lay if not g.is_empty]
    if not lay: return 0
    tree = STRtree(lay); best = 1
    for i, g in enumerate(lay):
        nb = [lay[int(j)] for j in tree.query(g, predicate="intersects") if int(j) > i]
        nb = [o for o in nb if g.intersection(o).area > 0.05]
        k = 1
        while k <= len(nb):
            o = _over_k(g, nb, k)
            if o is None or o.area <= 0.05: break
            k += 1
        best = max(best, k)
    return best


def dag_v1(parts, touch=0.5):
    """sequence.dag (lower z first where parts touch) + the hint edges seq_after / seq_before. pred[i] = parts that sew
    before i. A hint wins over the z edge it contradicts. Raises HintError on a cycle."""
    pred = dag(parts, touch); hinted = set()
    # M6 puff contract: a foam stop (thread key ending in FOAM) is where the operator lays foam: every FLAT part touching
    # a puff part sews before it, whatever the z (a flat stitch after the foam would sew through it). Stops are batched
    # by the exact thread key, so a '+foam' stop never merges with the flat stop of the same colour.
    foam = [i for i, p in enumerate(parts) if is_foam(p.thread)]
    if foam:
        tree = STRtree([p.geom for p in parts])
        for i in foam:
            for j in tree.query(parts[i].geom.buffer(touch), predicate="intersects"):
                j = int(j)
                if j != i and not is_foam(parts[j].thread): hinted.add((j, i))
    for i, p in enumerate(parts):
        for s in _ids(p.meta.get("seq_after")):
            for j in _select(parts, s, i): hinted.add((j, i))
        for s in _ids(p.meta.get("seq_before")):
            for j in _select(parts, s, i): hinted.add((i, j))
    for a, b in hinted:
        if (b, a) in hinted: raise HintError(f"sequence hints: {parts[a].id} and {parts[b].id} are asked to sew both before and after each other")
        pred[b].add(a); pred[a].discard(b)
    _check_acyclic(parts, pred)
    return pred


def _check_acyclic(parts, pred):
    n = len(parts); indeg = {i: len(pred[i]) for i in range(n)}; succ = defaultdict(set)
    for i in range(n):
        for j in pred[i]: succ[j].add(i)
    q = [i for i in range(n) if not indeg[i]]; seen = 0
    while q:
        i = q.pop(); seen += 1
        for k in succ[i]:
            indeg[k] -= 1
            if not indeg[k]: q.append(k)
    if seen < n:
        stuck = [parts[i].id for i in range(n) if indeg[i]][:8]
        raise HintError(f"sequence: cycle in the z-DAG + hints (parts {stuck} ...): check the seq_after / seq_before / z hints")


class _Kahn:
    """z-DAG state for colour batching: sew(thread) takes every free part of that thread, repeatedly, until none of it is
    free (one colour stop); copy() for look-ahead"""
    def __init__(self, parts, pred):
        self.parts = parts; self.th = [p.thread for p in parts]; n = len(parts)
        self.succ = defaultdict(list)
        for i in range(n):
            for j in pred[i]: self.succ[j].append(i)
        self.indeg = [len(pred[i]) for i in range(n)]; self.done = [False] * n; self.left = n
        self.free = defaultdict(set)
        for i in range(n):
            if not self.indeg[i]: self.free[self.th[i]].add(i)

    def copy(self):
        k = _Kahn.__new__(_Kahn); k.parts, k.th, k.succ = self.parts, self.th, self.succ
        k.indeg = list(self.indeg); k.done = list(self.done); k.left = self.left; k.free = defaultdict(set, {t: set(v) for t, v in self.free.items()})
        return k

    def sew(self, t):
        out = []
        while self.free.get(t):
            batch = sorted(self.free[t], key=lambda i: (self.parts[i].z, self.parts[i].id)); self.free[t] = set()
            for i in batch:
                self.done[i] = True; self.left -= 1; out.append(i)
                for k in self.succ[i]:
                    self.indeg[k] -= 1
                    if not self.indeg[k]: self.free[self.th[k]].add(k)
        return out

    def candidates(self):
        return [t for t, v in self.free.items() if v]

    def key(self, t):
        """the v1 greedy choice: a thread that empties now, then the deepest free part, then the most free area"""
        rest = [i for i in range(len(self.parts)) if not self.done[i] and self.th[i] == t]
        empties = all(self.indeg[i] == 0 or all(self.th[j] == t for j in self._pred_left(i)) for i in rest)
        fr = self.free[t]
        return (empties, -min(self.parts[i].z for i in fr), sum(self.parts[i].area for i in fr), t)

    def _pred_left(self, i):
        return [j for j in self._pred[i] if not self.done[j]]


def order_v1(parts, touch=0.5, pred=None, lookahead=True):
    """Kahn's algorithm on dag_v1 with colour batching (keep sewing the current thread while any of its parts is free).
    When the current thread has nothing free, the next thread is chosen to need the FEWEST colour stops overall:
      greedy key (v1): 1. a thread whose remaining parts wait on no other thread (sewing it now empties it), 2. the
      deepest free part (back to front: later fills hide the travel), 3. the most free area;
      lookahead=True: every candidate thread is rolled out to the end with the greedy key, and the candidate whose
      rollout ends with the fewest stops wins (ties: the greedy key). The DAG is never broken: only free parts sew.
    Returns stops [dict(thread, parts=[ids])]; the in-stop order is planned by sequence_blocks."""
    pred = dag_v1(parts, touch) if pred is None else pred
    st = _Kahn(parts, pred); st._pred = pred
    def greedy(s):
        n = 0
        while s.left:
            c = s.candidates()
            if not c: raise RuntimeError("sequence: cycle in the z-DAG")
            s.sew(max(c, key=s.key)); n += 1
        return n
    stops = []
    while st.left:
        c = st.candidates()
        if not c: raise RuntimeError("sequence: cycle in the z-DAG")
        if lookahead and len(c) > 1:
            def roll(t):
                s = st.copy(); s._pred = pred; s.sew(t); return 1 + greedy(s)
            best = min(c, key=lambda t: (roll(t), tuple(-v if isinstance(v, (int, float)) else 0 for v in st.key(t)[:3]), t))
        else:
            best = max(c, key=st.key)
        ids = st.sew(best)
        if stops and stops[-1]["thread"] == best: stops[-1]["parts"] += [parts[i].id for i in ids]
        else: stops.append(dict(thread=best, parts=[parts[i].id for i in ids]))
    return stops


# ------------------------------------------------------------------ planned entry / exit
def _kind(pts):
    """a closed ring (an edge run) may start at any vertex; an open block may be sewn backwards"""
    return "ring" if len(pts) > 3 and math.dist(pts[0], pts[-1]) <= 0.05 else "line"


def _start_dist(pts, cur):
    if cur is None: return 0.0
    if _kind(pts) == "ring":
        a = _np.asarray(pts[:-1], float); return float(_np.sqrt(((a - _np.asarray(cur)) ** 2).sum(1).min()))
    return min(math.dist(cur, pts[0]), math.dist(cur, pts[-1]))


def _best_variant(pts, cur):
    """the block's points re-ordered to start as close to cur as possible (same stitches, same geometry)"""
    if cur is None: return list(pts)
    if _kind(pts) == "ring":
        ring = list(pts[:-1]); a = _np.asarray(ring, float); k = int(_np.argmin(((a - _np.asarray(cur)) ** 2).sum(1)))
        r = ring[k:] + ring[:k]; return r + [r[0]]
    return list(pts) if math.dist(cur, pts[0]) <= math.dist(cur, pts[-1]) else list(reversed(pts))


def _units(bl):
    """a role group's blocks as units: a closed ring alone (it may start anywhere), or a CHAIN of consecutive open
    blocks kept in the technique's order (the tatami / guided cell walk, LESSONS B23: reordering its cells makes the
    travel between them cross cells already sewn, on top of the fill), which may only be sewn whole and backwards"""
    units = []
    for b in bl:
        if _kind(b.pts) == "ring": units.append(("ring", [b]))
        elif units and units[-1][0] == "chain": units[-1][1].append(b)
        else: units.append(("chain", [b]))
    return units


def _unit_dist(u, cur):
    kind, bl = u
    if cur is None: return 0.0
    if kind == "ring": return _start_dist(bl[0].pts, cur)
    return min(math.dist(cur, bl[0].pts[0]), math.dist(cur, bl[-1].pts[-1]))


def _unit_exit(kind, bl, at):
    """where the needle ends after a unit entered from `at` (nearest-start orientation)"""
    if kind == "ring": return tuple(bl[0].pts[-1]) if at is None else tuple(_ring_from(bl[0].pts, at)[-1])
    if at is None: return tuple(bl[-1].pts[-1])
    return tuple(bl[0].pts[0]) if math.dist(at, bl[-1].pts[-1]) < math.dist(at, bl[0].pts[0]) else tuple(bl[-1].pts[-1])


def _ring_from(pts, cur):
    ring = list(pts[:-1]); a = _np.asarray(ring, float); k = int(_np.argmin(((a - _np.asarray(cur)) ** 2).sum(1)))
    r = ring[k:] + ring[:k]; return r + [r[0]]


def orient_part(blocks, cur):
    """one part's blocks with a planned entry and exit (rule 5). The technique's unit order is kept (underlay before
    top, edge run before lattice, the cell walk inside a chain, _units); what is planned is HOW each unit is entered: a
    chain forwards or whole-backwards, a closed edge run from its vertex nearest the needle. The choice minimises the
    part's whole needle travel from `cur` (entry) through every unit (a 2-state dynamic programme per chain: the hop
    from the lattice underlay to the top rows was up to ~100 mm across a big part when each was sewn as planned).
    Same blocks, same stitches. Returns (blocks, exit point)."""
    from digitize.schema import Block
    units = []
    for b in blocks:
        if len(b.pts) < 2: continue
        if units and units[-1][0] == b.role: units[-1][1].append(b)
        else: units.append((b.role, [b]))
    # UNDERLAY units may be re-ordered: whatever travel joins them is buried under the part's own top layer. A group's
    # units are taken nearest-next; the top chains keep the technique's order (only their direction is planned).
    U = []
    for gi, (role, g) in enumerate(units):
        us = _units(g)
        if role == "underlay" and len(us) > 1:          # (the DP below then plans every unit's direction, lookahead included)
            at = cur; rest = list(us); seq = []
            while rest:
                k = min(range(len(rest)), key=lambda k: _unit_dist(rest[k], at))
                kind, bl = rest.pop(k); seq.append((kind, bl))
                at = _unit_exit(kind, bl, at)
            us = seq
        U += [(role, kind, bl) for kind, bl in us]
    if not U: return [], cur
    # states: (cost, exit point, choices) for "last chain forwards" / "backwards"; rings carry the state through
    states = [(0.0, cur, [])]
    for role, kind, bl in U:
        nxt = []
        for cost, at, ch in states:
            if kind == "ring":
                if at is None: nxt.append((cost, tuple(bl[0].pts[-1]), ch + [("ring", None)]))
                else:
                    pts = _ring_from(bl[0].pts, at); nxt.append((cost + math.dist(at, pts[0]), tuple(pts[-1]), ch + [("ring", at)]))
                continue
            s0, e0 = tuple(bl[0].pts[0]), tuple(bl[-1].pts[-1])
            for rev, (s, e) in ((False, (s0, e0)), (True, (e0, s0))):
                nxt.append((cost + (math.dist(at, s) if at is not None else 0.0), e, ch + [("chain", rev)]))
        best = {}                                   # keep the cheapest path per exit point (2 per chain)
        for st in nxt:
            k = (round(st[1][0], 3), round(st[1][1], 3))
            if k not in best or st[0] < best[k][0]: best[k] = st
        states = list(best.values())
    cost, exit_, ch = min(states, key=lambda s: s[0])
    out = []
    for (role, kind, bl), (ck, arg) in zip(U, ch):
        if ck == "ring":
            pts = bl[0].pts if arg is None else _ring_from(bl[0].pts, arg)
            out.append(Block(bl[0].part, bl[0].role, [tuple(q) for q in pts]))
        elif arg:
            out += [Block(b.part, b.role, [tuple(q) for q in reversed(b.pts)]) for b in reversed(bl)]
        else:
            out += [Block(b.part, b.role, [tuple(q) for q in b.pts]) for b in bl]
    return out, exit_


class InnerRouter:
    """needle paths INSIDE one geometry (inset by `inset` mm): cheapest 8-connected routes on a ppm raster, simplified,
    checked to stay inside geom + 0.25 mm (dst2.OWN_HALO) and resampled every `step` mm. The raster is built once."""
    def __init__(self, geom, ppm=2.0, inset=0.3, step=4.0, max_px=4_000_000):
        from skimage.draw import polygon as _poly
        from digitize.techniques import polys
        self.geom, self.ppm, self.step = geom, ppm, step; self.own = geom.buffer(0.25); self.ok = False
        q = geom.buffer(-inset) if inset else geom
        if q.is_empty: return
        x0, y0, x1, y1 = q.bounds; W = int(math.ceil((x1 - x0) * ppm)) + 3; H = int(math.ceil((y1 - y0) * ppm)) + 3
        if W * H > max_px: return
        m = _np.zeros((H, W), bool)
        for p in polys(q):
            r, c = _poly([(y - y0) * ppm + 1 for x, y in p.exterior.coords], [(x - x0) * ppm + 1 for x, y in p.exterior.coords], (H, W)); m[r, c] = True
            for h in p.interiors:
                r, c = _poly([(y - y0) * ppm + 1 for x, y in h.coords], [(x - x0) * ppm + 1 for x, y in h.coords], (H, W)); m[r, c] = False
        if not m.any(): return
        self.m, self.x0, self.y0, self.H, self.W = m, x0, y0, H, W
        self.cost = _np.where(m, 1.0, _np.inf); self.ys, self.xs = _np.nonzero(m); self.ok = True

    def _px(self, pt):
        pp = (min(self.H - 1, max(0, int(round((pt[1] - self.y0) * self.ppm + 1)))), min(self.W - 1, max(0, int(round((pt[0] - self.x0) * self.ppm + 1)))))
        if self.m[pp]: return pp
        k = int(_np.argmin((self.ys - pp[0]) ** 2 + (self.xs - pp[1]) ** 2))
        return (int(self.ys[k]), int(self.xs[k])) if math.hypot(self.ys[k] - pp[0], self.xs[k] - pp[1]) <= 1.5 * self.ppm else None

    def route(self, a, b):
        from shapely.geometry import LineString
        from skimage.graph import route_through_array
        if not self.ok: return None
        pa, pb = self._px(a), self._px(b)
        if pa is None or pb is None: return None
        try:
            path, c = route_through_array(self.cost, pa, pb, fully_connected=True, geometric=True)
        except Exception:
            return None
        if not _np.isfinite(c): return None
        pts = [((cc - 1) / self.ppm + self.x0, (rr - 1) / self.ppm + self.y0) for rr, cc in path]
        ln = LineString([tuple(a)] + pts + [tuple(b)]).simplify(0.5 / self.ppm)
        if not ln.within(self.own): return None
        n = max(1, int(math.ceil(ln.length / self.step)))
        return [tuple(ln.interpolate(ln.length * k / n).coords[0]) for k in range(n + 1)]


def inner_path(geom, a, b, ppm=2.0, inset=0.3, step=4.0):
    """one path from a to b inside geom (InnerRouter); None when a or b is not inside or no route exists"""
    return InnerRouter(geom, ppm, inset, step).route(a, b)


def plan_inner_travel(blocks, geom, halo=0.25, min_mm=1.0):
    """planned travel (rule 5): a move INTO an underlay block, or from the underlay into the top layer, that would
    leave the part (straight line not inside geom + halo) becomes a path through the part's inside (inset 0.3 mm, else
    through necks narrower than that on a finer raster), inserted as a role "travel" block: it sews before the part's
    top, which hides it. Without it dst2 trims there when its router finds no hidden way (between the inset pieces of
    an edge run around a narrow neck), and a trim inside a part splits it into two RUNS: the file's stack gate then
    counts its underlay and its top as two layers. Moves between TOP blocks are left to dst2: a path through the part
    there would lie on rows already sewn (tried: coherence 50 -> 56 fails, trims unchanged). Returns (blocks, n paths)."""
    from shapely.geometry import LineString
    from digitize.schema import Block
    own = geom.buffer(halo); out = []; n = 0; prev = None; R = {}
    def router(k):
        if k not in R: R[k] = InnerRouter(geom, 2.0, 0.3) if k == 0 else InnerRouter(geom, 5.0, 0.0)
        return R[k]
    for b in blocks:
        at = tuple(prev.pts[-1]) if prev is not None else None
        if at is not None and (b.role == "underlay" or prev.role in ("underlay", "travel")) and math.dist(at, b.pts[0]) > min_mm:
            if not LineString([at, tuple(b.pts[0])]).within(own):
                path = router(0).route(at, tuple(b.pts[0])) or router(1).route(at, tuple(b.pts[0]))
                if path and len(path) > 1: out.append(Block(b.part, "travel", path)); n += 1
        out.append(b); prev = b
    return out, n


def _entry_dist(plan, pid, cur):
    bl = [b for b in (plan.blocks.get(pid) or []) if len(b.pts) > 1]
    if cur is None or not bl: return 0.0
    return min(_start_dist(b.pts, cur) for b in bl if b.role == bl[0].role)


def sequence_blocks(plan, touch=0.5, group_bonus_mm=3.0, pred=None, inner_travel=True):
    """rule 5, planned entry / exit: inside each stop, parts are sewn nearest-next from where the needle IS (the end of
    the last block sewn), among the parts whose z-DAG predecessors are already sewn; parts of the current meta["group"]
    get a bonus (finish a building / a tree while one of its parts is free); meta["entry"] replaces the needle position
    for that part. Each part's blocks are then oriented by orient_part. Stops keep their thread and their parts; the
    DAG is never broken. Returns dict(travel_mm_before, travel_mm_after) (straight-line needle moves between blocks)."""
    idx = {p.id: i for i, p in enumerate(plan.parts)}
    pred = dag_v1(plan.parts, touch) if pred is None else pred
    before = travel_mm(plan); cur = None; grp = None; n_inner = 0
    for s in plan.stops:
        todo = list(s["parts"]); tset = set(todo); new = []
        while todo:
            ok = [pid for pid in todo if not any(plan.parts[j].id in tset for j in pred[idx[pid]])]
            if not ok: raise RuntimeError(f"sequence_blocks: stop {s['thread']} has a DAG cycle among {todo[:5]}")
            def cost(pid):
                p = plan.parts[idx[pid]]; e = p.meta.get("entry")
                d = _entry_dist(plan, pid, tuple(e) if e else cur)
                if grp is not None and p.meta.get("group") == grp: d -= group_bonus_mm
                return (d, p.z, pid)
            pid = min(ok, key=cost); todo.remove(pid); tset.discard(pid); new.append(pid)
            p = plan.parts[idx[pid]]; e = p.meta.get("entry")
            if plan.blocks.get(pid):
                plan.blocks[pid], cur = orient_part(plan.blocks[pid], tuple(e) if e else cur)
                if inner_travel: plan.blocks[pid], k = plan_inner_travel(plan.blocks[pid], p.geom); n_inner += k
            grp = p.meta.get("group")
        s["parts"] = new
    return dict(travel_mm_before=round(before, 1), travel_mm_after=round(travel_mm(plan), 1), inner_paths=n_inner)


def travel_mm(plan):
    """straight-line needle moves between consecutive blocks, in sew order (what dst2 has to travel or trim)"""
    cur = None; t = 0.0
    for s in plan.stops:
        for pid in s["parts"]:
            for b in plan.blocks.get(pid, []):
                if len(b.pts) < 2: continue
                if cur is not None: t += math.dist(cur, b.pts[0])
                cur = b.pts[-1]
    return t


def budget(plan, stitches_max=None):
    """rule 6: the planned needle points of every block vs the stitch budget. Returns dict(planned, max, ok)."""
    n = sum(len(b.pts) for bl in plan.blocks.values() for b in bl)
    return dict(planned=n, max=stitches_max, ok=stitches_max is None or n <= stitches_max)


def report(plan, pred=None, touch=0.5):
    """sequence facts for gates.json: stops, distinct threads, repeated threads, z-DAG violations (a part sewn before one
    of its predecessors: must be 0), parts carrying hints."""
    pred = dag_v1(plan.parts, touch) if pred is None else pred
    pos = {}; k = 0
    for s in plan.stops:
        for pid in s["parts"]: pos[pid] = k; k += 1
    viol = [(plan.parts[j].id, p.id) for i, p in enumerate(plan.parts) for j in pred[i]
            if p.id in pos and plan.parts[j].id in pos and pos[plan.parts[j].id] > pos[p.id]]
    th = [s["thread"] for s in plan.stops]
    hints = sum(1 for p in plan.parts if any(k in p.meta for k in ("seq_after", "seq_before", "knockout_of", "group", "entry", "z")))
    return dict(stops=len(th), threads=len(set(th)), colour_changes=max(0, len(th) - 1), repeated_threads=len(th) - len(set(th)),
                dag_violations=len(viol), violations=viol[:10], parts_with_hints=hints)


def plan_sequence(plan, sq, P, stitches_max=None, log=print):
    """the whole M4 sequence for run.make_plan, BEFORE the technique plugins: hints -> underlap -> cut-under ->
    <= max_layers -> fragments -> (caller: field refresh, separation, checks) ... see sequence_after_blocks."""
    sq = dict(SEQ_DEFAULTS, **(sq or {}))
    hints = apply_hints(plan.parts)
    underlap(plan.parts, sq["keep_mm"]); cut_under(plan.parts, sq["keep_mm"])
    band = sq.get("stack_keep_band_mm"); band = float(sq["keep_mm"] if band is None else band)
    cut = limit_stack(plan.parts, int(sq.get("max_layers", P.get("max_stacked_layers", 2))), reach=float(sq.get("stack_reach_mm", 0.0)),
                      keep_band=band)
    plan.parts, dropped = absorb_fragments(plan.parts, sq["min_fragment_mm2"])
    return dict(hints=hints, stack_cut=cut, dropped=dropped)
