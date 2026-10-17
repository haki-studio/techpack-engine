"""Stitch engine smoke test on a synthetic motif: file writes, max stitch, few trims, ≤ factory thread limit (LESSONS B5)."""
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
    import factory
    assert v["colour_changes"] + 1 <= factory.max_threads()
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


def test_stops_raises_on_unknown_colour():
    """LESSONS B18: a region whose colour is not in tech.COLOUR_ORDER must stop the build, not vanish."""
    import pytest
    vis = motif() + [dict(col="not-a-thread", geom=Point(10, 40).buffer(4), st="tatami", ang=0, grp="TR", layer=5, z=4)]
    with pytest.raises(ValueError, match="not-a-thread"):
        tech.stops(vis, tech.STITCH_LAYER)
    assert sum(len(s["regions"]) for s in tech.stops(motif(), tech.STITCH_LAYER)) == len(motif())


def test_pull_reads_rules_added_after_import():
    """dst2 used to freeze pull comp at import; a rule a project adds later must be honoured."""
    code = "ZZTEST"
    row = list(next(iter(tech.RULES.values()))); row[6] = "0.35"
    tech.RULES[code] = tuple(row) if isinstance(next(iter(tech.RULES.values())), tuple) else row
    try:
        assert dst2.pull_for(code) == 0.35
    finally:
        del tech.RULES[code]


def test_split_fit_counts_cross_arm_on_split_line():
    """LESSONS B16: a section reported 'fits' by split_clip must fit with its registration crosses as written:
    outer crosses `ext` mm beyond the art and a 6 mm cross arm on each split line."""
    # a 2 x 1 field just under 2 x the usable frame: the old check passed sections that were 6 mm too wide
    w = 2 * (344 - 18.5) - 4
    vis = [dict(col="bark", geom=box(0, 0, w, 120), st="tatami", ang=0, grp="TR", layer=5, z=1)]
    sp = dst2.split_clip(vis)
    for k, bb in sp["bbs"].items():
        i, _ = k
        x0 = sp["bounds"][0] - 18.5 if i == 0 else min(bb[0], sp["sx"] - 6)
        x1 = sp["bounds"][2] + 18.5 if i == 1 else max(bb[2], sp["sx"] + 6)
        assert sp["fits"][k] == (x1 - x0 <= 344), (k, x1 - x0, sp["fits"][k])
    assert not all(sp["fits"].values())      # 647 mm of solid art cannot go into two 344 mm sections with crosses



def test_readback_per_stop_sums_to_file():
    """LESSONS B20: per-stop tables are read from the DST and add up to the file totals."""
    import readback
    vis = dst2.clean_vis(motif())
    stops = dst2.merge_stops(tech.stops(vis, tech.STITCH_LAYER))
    pat, _ = dst2.make_pattern(vis, stops, (40, 20))
    d = tempfile.mkdtemp(); base = os.path.join(d, "t"); dst2.write(pat, base)
    rb = readback.dst(base + ".dst")
    assert rb["stops"] == len(stops) and len(rb["per_stop"]) == len(stops)
    assert sum(s["stitches"] for s in rb["per_stop"]) == rb["stitches"] > 500
    assert all(s["stitches"] > 0 for s in rb["per_stop"])
    assert abs(rb["stitches"] - dst2.verify(base)["stitches"]) <= 2
