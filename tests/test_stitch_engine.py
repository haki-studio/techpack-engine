"""Stitch engine smoke test on a synthetic motif: file writes, max stitch, few trims, ≤ 15 threads (LESSONS B)."""
import os, tempfile
from shapely.geometry import Point, LineString, box
import dst2, tech

def motif():
    trunk = LineString([(0, 0), (40, 30), (80, 35)]).buffer(4)
    leaf = Point(60, 20).buffer(6).difference(trunk)
    vein = LineString([(56, 18), (64, 22)]).buffer(0.35)
    return [dict(col="bark", geom=trunk, st="tatami", ang="auto", grp="TR", layer=5, z=1),
            dict(col="slate", geom=leaf, st="satin", ang="auto", grp="LF-shade", layer=7, z=2),
            dict(col="barkdk", geom=vein, st="bean", ang=None, grp="LF-vein", layer=7, z=3)]

def test_engine_writes_valid_files():
    vis = dst2.clean_vis(motif())
    stops = dst2.merge_stops(tech.stops(vis, tech.STITCH_LAYER))
    pat, st = dst2.make_pattern(vis, stops, (40, 20))
    d = tempfile.mkdtemp(); base = os.path.join(d, "t")
    dst2.write(pat, base); v = dst2.verify(base)
    assert os.path.exists(base + ".dst") and os.path.exists(base + ".pes")
    assert v["max_stitch"] <= 7.6
    assert v["colour_changes"] + 1 <= 15
    assert st["trims"] <= 3
    assert v["stitches"] > 500


def _blobs(n=40):
    import random
    random.seed(1)
    return [Point(random.uniform(0, 200), random.uniform(0, 120)).buffer(random.uniform(3, 15)) for _ in range(n)]

def test_fast_geometry_matches_union():
    """LESSONS B13: bounds_of / cut_length / Tones.clip replace whole-design unions — same answers."""
    from shapely.ops import unary_union
    gs = _blobs(); U = unary_union(gs)
    assert all(abs(a - b) < 1e-9 for a, b in zip(dst2.bounds_of(gs), U.bounds))
    for x in (30.0, 77.7, 150.0):
        line = LineString([(x, -10), (x, 140)])
        assert abs(dst2.cut_length(gs, line) - U.intersection(line).length) < 1e-6
    T = dst2.Tones(); [T.add(g) for g in gs[:25]]; E = unary_union(gs[:25])
    for g in gs[25:]:
        ring = g.buffer(2.5).difference(g)
        assert abs(T.clip(ring).area - ring.intersection(E).area) < 1e-6
    assert dst2.Tones().is_empty and dst2.Tones().clip(box(0, 0, 1, 1)).is_empty
