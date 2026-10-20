"""CHENILLE (loop / moss fill + chain outline) as a PLAN (ENGINE_PLAN M6). Promoted from projects/wave-jacket/chenille.py
(moss spirals 2.0 mm apart, 2.5 mm path stitches, chain cord), minus its DST writer.

Chenille is sewn on a dedicated chenille head (Tajima TMCE, Barudan BEMR ...) whose machine reads its own file and
needle settings: the head forms the loops (moss) or the chain from the same path, and the LOOP HEIGHT is a needle-height
setting, not a stitch (Wilcom chenille help: "needle height controls the height of the loop ... in a moss stitch";
"stitch length should be constant ... else the height of moss loops and width of chain loops will vary").
factory.json says chenille: true but not which machine or file format, so this plugin NEVER writes a machine file:
  plan(part)       -> blocks (the paths, for previews, the contract and estimates)
  detail(part)     -> dict(moss=[paths], chain=[paths], spec=dict(loop_height_mm, yarn, needle heights, mode ...))
  specialty.export_chenille(...) raises FactoryFormatNeeded (F1) until factory.json gives chenille_format
  specialty.chenille_gates(part)  constant stitch length, moss coverage without pile-up, chain outline closed on the edge
compile.write refuses a chenille-machine part in a lock-stitch file (sequencing machine="chenille").

Moss modes: "spiral" (inward offset rings chained into one path per island: Wilcom recommends open spiral / offset
fills so chenille yarn does not pile up) or "zigzag" (boustrophedon rows at the part's angle, `spacing` apart).
Numbers [proposed - confirm] with the factory's chenille operator: spacing 2.0, moss_len 2.5 (Wave), chain_len 2.0,
outline inset 0.8, loop height 4.0 mm."""
import math
import numpy as np
from shapely.geometry import LineString, LinearRing, Point
from shapely import affinity
from digitize.schema import Block
from digitize.techniques import Technique, register, polys


def _chord_walk(D, L):
    """needle points on the densely sampled path D, each exactly L (chord) from the last: the needle steps the chord,
    not the arc, so on a curve an arc-length resample sews short stitches (uneven loops, Wilcom)"""
    out = [D[0]]; cur = np.array(D[0]); i = 1
    while i < len(D):
        while i < len(D) and np.linalg.norm(D[i] - cur) < L: i += 1
        if i >= len(D): break
        a, b = D[i - 1], D[i]; d = b - a; f = a - cur                     # |a + t d - cur| = L, t in [0, 1]
        A, B, Cc = d @ d, 2 * f @ d, f @ f - L * L
        t = (-B + math.sqrt(max(B * B - 4 * A * Cc, 0.0))) / (2 * A) if A > 1e-12 else 0.0
        cur = a + min(max(t, 0.0), 1.0) * d; out.append(cur)
    return out


def resample_const(pts, L, closed=False):
    """needle points at a CONSTANT stitch (chord) length L along the path; an open path ends with one shorter stitch
    on its end point; a closed loop's length is tuned (within +-15 %) so its last stitch closes the loop evenly"""
    if closed and tuple(pts[0]) != tuple(pts[-1]): pts = list(pts) + [pts[0]]
    ls = LineString(pts); T = ls.length
    if T < 1e-6: return [tuple(pts[0])]
    n = max(2, int(T / 0.05)); D = np.array([ls.interpolate(T * i / n).coords[0] for i in range(n + 1)])
    end = D[-1]
    if not closed:
        out = _chord_walk(D, L)
        if np.linalg.norm(out[-1] - end) > 1e-6: out.append(end)
        return [tuple(map(float, p)) for p in out]
    best = None
    for Lk in np.linspace(0.85 * L, 1.15 * L, 61):
        out = _chord_walk(D, Lk); rem = float(np.linalg.norm(out[-1] - end))
        if rem < 0.3 * Lk: out = out[:-1]; rem = float(np.linalg.norm(out[-1] - end))   # a tiny last stitch: drop the point
        score = abs(rem - Lk) + abs(Lk - L) * 0.2
        if best is None or score < best[0]: best = (score, out)
    out = best[1] + [end]
    return [tuple(map(float, p)) for p in out]


def spiral_paths(p, spacing, min_ring=6.0, handover=None, sample=0.5):
    """offset (contour) rings of p, `spacing` apart, INCLUDING the rings round holes (waveart.ring_chain followed only
    the exterior and so sewed across holes), chained into spiral paths: from the end of one ring the needle steps to
    the nearest unused ring (normally the next one in, ~spacing away), starts there and goes round it, leaving
    `handover` mm (default = spacing) open so it never sews over its own start. A step longer than 1.6 x spacing, or
    one that leaves the part, starts a new path (a trim on the chenille head)."""
    handover = spacing if handover is None else handover
    rings = []; k = 0
    while True:
        cur = p if k == 0 else p.buffer(-k * spacing)
        ps = [r for r in polys(cur) if r.area > 1.0]
        if not ps: break
        for r in ps:
            for ring in [r.exterior] + list(r.interiors):
                if ring.length < min_ring: continue
                cs = list(ring.coords)
                if not LinearRing(cs).is_ccw: cs = cs[::-1]                   # one travel direction for every ring
                rings.append(LineString(cs))
        k += 1
    paths = []; used = [False] * len(rings); path = []
    hold = p.buffer(0.05)
    while not all(used):
        if path:
            e = Point(path[-1]); j = min((i for i in range(len(rings)) if not used[i]), key=lambda i: rings[i].distance(e))
            s0 = rings[j].project(e); start = rings[j].interpolate(s0).coords[0]
            if math.dist(path[-1], start) > 1.6 * spacing or not hold.contains(LineString([path[-1], start])):
                paths.append(path); path = []; continue
        else:
            j = next(i for i in range(len(rings)) if not used[i]); s0 = 0.0
        used[j] = True; R = rings[j]; L = R.length
        path = path + [R.interpolate((s0 + t) % L).coords[0] for t in np.arange(0, L - handover, sample)]
    if path: paths.append(path)
    return [pp for pp in paths if len(pp) > 4]


def zigzag_paths(p, spacing, ang):
    """boustrophedon rows across p at ang, `spacing` apart, joined row end to row start (one path per run of rows)"""
    c = p.centroid; q = affinity.rotate(p, -ang, origin=c, use_radians=False)
    x0, y0, x1, y1 = q.bounds; rows = []; k = 0
    y = y0 + spacing / 2
    while y < y1:
        seg = LineString([(x0 - 1, y), (x1 + 1, y)]).intersection(q)
        parts = [g for g in getattr(seg, "geoms", [seg]) if g.geom_type == "LineString" and g.length > 0.5]
        for g in sorted(parts, key=lambda g: g.coords[0][0]):
            cs = list(g.coords); rows.append((k, cs if k % 2 == 0 else cs[::-1]))
        k += 1; y += spacing
    paths = []; cur = []; last_k = None
    for k, cs in rows:
        pts = [affinity.rotate(Point(x, yy), ang, origin=c).coords[0] for x, yy in cs]
        if cur and last_k == k - 1 and math.dist(cur[-1], pts[0]) <= 2.5 * spacing: cur += pts
        else:
            if cur: paths.append(cur)
            cur = list(pts)
        last_k = k
    if cur: paths.append(cur)
    return paths


def spec_of(part):
    P = part.stitch.params if part.stitch else {}
    s = dict(mode=P.get("mode", "spiral"), spacing=float(part.stitch.spacing if part.stitch else 2.0),
             moss_len=float(P.get("moss_len", 2.5)), chain_len=float(P.get("chain_len", 2.0)),
             outline_inset=float(P.get("outline_inset", 0.8)), loop_height_mm=P.get("loop_height_mm", 4.0),
             yarn=P.get("yarn", "chenille yarn [proposed - confirm]"), moss_needle_height=P.get("moss_needle_height"),
             chain_needle_height=P.get("chain_needle_height"), outline=bool(P.get("outline", True)),
             outline_dir=P.get("outline_dir", "ccw"))
    s.update(part.meta.get("chenille") or {})
    return s


def detail(part):
    """the chenille plan: moss paths (loop mode) + chain outline paths (chain mode) + the head settings"""
    s = spec_of(part); moss, chain = [], []
    for p in polys(part.geom):
        if s["outline"]:
            ring = p.buffer(-s["outline_inset"])
            for q in polys(ring):
                rings = [list(q.exterior.coords)] + [list(r.coords) for r in q.interiors]
                for r in rings:
                    ls = LineString(r)
                    if ls.length < 3: continue
                    pts = list(ls.coords)
                    if LinearRing(pts).is_ccw != (s["outline_dir"] == "ccw"): pts = pts[::-1]
                    chain.append(resample_const(pts, s["chain_len"], closed=True))
        inner = p.buffer(-(s["outline_inset"] + s["spacing"])) if s["outline"] else p.buffer(-s["spacing"] / 2)
        for q in polys(inner):
            if q.area < 2.0: continue
            raw = spiral_paths(q, s["spacing"]) if s["mode"] == "spiral" else zigzag_paths(q, s["spacing"], part.dir.angle)
            moss += [resample_const(pp, s["moss_len"]) for pp in raw]
    return dict(moss=[m for m in moss if len(m) > 1], chain=[c for c in chain if len(c) > 1], spec=s)


@register
class Chenille(Technique):
    name = "chenille"; stype = "run"
    sequencing = {"machine": "chenille", "after_fill": True}

    def check(self, part, principles):
        s = spec_of(part); out = []
        w = principles.get("chenille_min_w_mm", 2 * (s["outline_inset"] + s["spacing"]))
        if part.geom.buffer(-w / 2).is_empty:
            out.append(self.issue(part, f"chenille part narrower than {w:.1f} mm everywhere: no room for moss inside the chain outline", rule=4))
        if not isinstance(s["loop_height_mm"], (int, float)): out.append(self.issue(part, "chenille loop height not declared", rule=4))
        if s["mode"] not in ("spiral", "zigzag"): out.append(self.issue(part, f"chenille moss mode {s['mode']!r} unknown", rule=4))
        return out

    def plan(self, part):
        d = detail(part)
        return [Block(part.id, "top", pp) for pp in d["moss"] + d["chain"]]
