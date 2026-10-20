"""ENGINE_PLAN M2: organic parts (direction field, guided / contour fill, blends, stratum + cloud splitters), plus the M1
review follow-ups. Each guard was proven RED by a mutation of the code it guards (scratchpad mutate_m2.py, recorded in
RECAP-2026-10-20-engine-m2-organic.md) and is GREEN on this branch."""
import json, math, os, re
import numpy as np
import pytest
from shapely.geometry import box, LineString, Point, Polygon
import qa
from digitize.schema import Part, DirSpec, ObjectPlan, StitchSpec
from digitize.rulebook import Rulebook
from digitize import techniques, threads, audit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _spec(tech, **over):
    d = dict(Rulebook().data["techniques"][tech]); d.update(over)
    return StitchSpec(technique=tech, spacing=d.get("spacing", 0.45), stitch_len=d.get("stitch_len", 3.5), underlay=d.get("underlay", []),
                      pull_comp=d.get("pull_comp", 0.2), params={k: v for k, v in d.items() if k not in ("spacing", "stitch_len", "underlay", "pull_comp")})


def _segs(blocks, role=None):
    return [tuple(a) + tuple(b) for blk in blocks if role is None or blk.role == role for a, b in zip(blk.pts, blk.pts[1:]) if tuple(a) != tuple(b)]


# ================================================================== M1 review follow-ups
def test_random_angles_are_derived_not_asserted():
    """follow-up 1: random_angles was the constant 0. Every declared angle is now re-derived from its source; an angle
    from rng.uniform has no basis and is counted. Mutation (angle_audit skips the comparison) -> red."""
    rb = Rulebook()
    ok_rule = Part(id="pool.1", kind="pool", geom=box(0, 0, 10, 10), thread="t", z=3.5, dir=rb.direction("pool"))
    ok_field = Part(id="stub.1", kind="zone_stub", geom=box(20, 0, 30, 10), thread="t", z=1, dir=rb.direction("zone_stub", field=37.5),
                    meta=dict(field_angle=37.5))
    sep = Part(id="stub.2", kind="zone_stub", geom=box(40, 0, 50, 10), thread="t", z=1, dir=DirSpec(57.5, source="field-mean"),
               meta=dict(field_angle=37.5, sep_deg=20.0))
    rnd = Part(id="stub.3", kind="zone_stub", geom=box(60, 0, 70, 10), thread="t", z=1, dir=DirSpec(np.random.default_rng(7).uniform(0, 180), source="field-mean"),
               meta=dict(field_angle=37.5))
    nob = Part(id="pool.2", kind="pool", geom=box(80, 0, 90, 10), thread="t", z=3.5, dir=DirSpec(33.0, source="rule"))
    big = Part(id="stub.4", kind="zone_stub", geom=box(0, 20, 10, 30), thread="t", z=1, dir=DirSpec(77.5, source="field-mean"),
               meta=dict(field_angle=37.5, sep_deg=40.0))                     # a "separation" beyond the house limit
    r = audit.angle_audit(ObjectPlan(name="t", parts=[ok_rule, ok_field, sep, rnd, nob, big]), rb)
    assert r["random_angles"] == 3, r
    assert {u["part"] for u in r["unexplained"]} == {"stub.3", "pool.2", "stub.4"}, r


def _rows_fixed(w, h, ang, phases=None, min_pieces=2, sp=0.42):
    """a fixed-angle split-satin cord as the plugin plans it (rows along the cord, split with staggered pieces)"""
    p = Part(id="c", kind="fall_cord", geom=box(0, 0, w, h), thread="t", z=3, dir=DirSpec(ang)); p.technique = "split_satin"
    p.stitch = _spec("split_satin", underlay=[], pull_comp=0.0)
    return _segs(techniques.get("split_satin").plan(p))


def test_cord_gate_reads_split_rows_from_segments():
    """follow-up 2: satin_runs is blind to split satin (its pieces do not reverse every stitch), so a cord gate reads the
    rows: pieces <= 7 mm, split points staggered. Our plugin passes; equal split points (dst2.turning_satin style) are a
    seam; an unsplit 9 mm row is too long. Mutation (split PHASES = (0, 0, 0)) -> our cord shows a seam -> red;
    mutation (gate ignores seam_frac) -> the aligned cord passes -> red."""
    from digitize.techniques.split_satin import split_row
    ours = qa.split_satin_rows(_rows_fixed(6.0, 40.0, 90.0))
    assert qa.satin_runs(_rows_fixed(6.0, 40.0, 90.0)) == []                  # the blindness this gate exists for
    assert ours["ok"] and ours["rows"] >= 12 and ours["aligned"] < 0.3 and ours["max_piece"] <= 7.0, ours
    assert 4.5 < ours["column_w"] < 6.5 and ours["pieces_med"] >= 6, ours
    pts = []; x = 0.0                                                         # aligned splits: same phase every row
    for k in range(30):
        a, b = ((x, 0.0), (x, 40.0)) if k % 2 == 0 else ((x, 40.0), (x, 0.0))
        pts += [a] + split_row(a, b, 0, 5.5, 0.0, min_pieces=2); x += 0.42
    seam = qa.split_satin_rows([pts[i] + pts[i + 1] for i in range(len(pts) - 1)])
    assert [f["kind"] for f in seam["flags"]] == ["seam"] and seam["aligned"] > 0.9, seam
    long = qa.split_satin_rows([(0.0, 0.0, 0.0, 9.0), (0.0, 9.0, 0.4, 9.0), (0.4, 9.0, 0.4, 0.0)] * 1)
    assert "too-long" in [f["kind"] for f in long["flags"]], long


def _tiny_plan():
    rb = Rulebook()
    parts = []
    for i, (x, ang) in enumerate(((0.0, 0.0), (20.0, 90.0))):
        p = Part(id=f"p{i}", kind="pool", geom=box(x, 0, x + 12, 10), thread="t1", z=3.5, dir=DirSpec(ang, source="rule" if ang == 0 else "answer"),
                 meta=dict(answer_angle=ang))
        p.technique = "tatami"; p.stitch = rb.stitch_spec("pool"); parts.append(p)
    plan = ObjectPlan(name="t", parts=parts, threads={"t1": dict(hex="#B23F2E", name="red")}, stops=[dict(thread="t1", parts=["p0", "p1"])])
    from digitize import compile as CP
    CP.plan_blocks(plan)
    return plan


def test_gates_read_the_written_dst(tmp_path):
    """follow-up 4: gates judge the FILE. compile.labelled_dst carries the part ids onto the DST's own segments; every
    planned stitch must be found in the file in sew order. A plan stitch the file does not contain raises.
    Mutation (labelled_dst stops checking for missing planned segments) -> red."""
    from digitize import compile as CP
    plan = _tiny_plan(); res = CP.write(plan, str(tmp_path / "t"), (0.0, 0.0))
    D, L, rep = CP.labelled_dst(str(tmp_path / "t.dst"), (0.0, 0.0), res["segs"], res["seg_parts"])
    assert len(D) == len(qa.dst_segments(str(tmp_path / "t.dst"))) and rep["matched"] + rep["skipped_subgrid"] == len(res["segs"])
    assert {l for l in L if l} == {"p0", "p1"} and rep["writer_added"] <= 0.05 * len(D) + 12, rep
    for pid, ang in (("p0", 0.0), ("p1", 90.0)):                               # the file's p1 stitches really are vertical
        S = [s for s, l in zip(D, L) if l == pid and math.hypot(s[2] - s[0], s[3] - s[1]) > 1.0]
        a = np.degrees(np.arctan2([s[3] - s[1] for s in S], [s[2] - s[0] for s in S])) % 180
        assert np.mean([min(abs(v - ang), 180 - abs(v - ang)) for v in a]) < 20, pid
    bad = list(res["segs"]); bad.insert(len(bad) // 2, (5.0, 5.0, 9.0, 9.0))  # a stitch the file does not have
    with pytest.raises(CP.ReadbackMismatch):
        CP.labelled_dst(str(tmp_path / "t.dst"), (0.0, 0.0), bad, list(res["seg_parts"][:len(bad) // 2]) + ["p0"] + list(res["seg_parts"][len(bad) // 2:]))


def test_direction_tiles_split_by_source():
    """follow-up 3: a tile whose top part took its angle from the reference grain (field-mean / field) is SELF-DERIVED:
    graded against the pixels it came from. It is reported apart from independent (rule / answer / depth) tiles.
    Mutation (bucket() puts field-mean with the independent ones) -> red."""
    rule = Part(id="r", kind="pool", geom=box(0, 0, 16, 16), thread="t", z=3, dir=DirSpec(0.0, source="rule"))
    fm = Part(id="f", kind="zone_stub", geom=box(16, 0, 32, 16), thread="t", z=1, dir=DirSpec(10.0, source="field-mean"))
    gf = Part(id="g", kind="stratum_band", geom=box(32, 0, 48, 16), thread="t", z=1, dir=DirSpec(10.0, mode="field", source="field"))
    ct = Part(id="c", kind="cloud_lobe", geom=box(48, 0, 64, 16), thread="t", z=4, dir=DirSpec(0.0, mode="contour", source="outline"))
    def at(c):
        for p in (rule, fm, gf, ct):
            if p.geom.contains(Point(c)): return p
        return None
    dm = dict(ok_tiles=[(4, 4), (12, 12), (20, 4), (36, 4), (52, 4)], fail_dev=[dict(at_mm=(28, 12))], fail_chaos=[dict(at_mm=(60, 12)), dict(at_mm=(80, 8))])
    r = audit.direction_by_source(dm, at)
    assert r["independent"] == dict(tiles=2, ok=2, dev=0, chaos=0, pct_ok=100.0, pct_chaos=0.0), r
    assert r["self-derived"]["tiles"] == 3 and r["self-derived"]["ok"] == 2 and r["self-derived"]["dev"] == 1, r
    assert r["outline"]["tiles"] == 2 and r["outline"]["chaos"] == 1 and r["bare"]["tiles"] == 1, r


def test_importance_keeps_a_small_tone_a_motif_depends_on():
    """follow-up 5: area-weighted merging dropped both water blues (small area, the whole read of the falls).
    threads.importance multiplies a tone's weight in the merge cost. Without importance the blue is merged first; with
    it, the blue survives and a cheaper pair merges instead. Mutation (importance ignored in the cost) -> red."""
    pal = {"navy": "#22355C", "slate": "#566577", "sky": "#3F6FA9", "mist": "#9EA3A6", "cream": "#D4CABA"}
    w = {"navy": 7000, "slate": 5000, "sky": 1200, "mist": 2200, "cream": 2100}
    base = threads.plan(w, pal, needles=4)
    assert base["map"]["sky"] != "sky", base["merges"]
    imp = threads.plan(w, pal, needles=4, importance={"sky": 3})
    assert imp["map"]["sky"] == "sky" and imp["threads"]["sky"]["importance"] == 3.0, imp["merges"]
    assert threads.plan(w, pal, needles=4, importance={}) == base               # default-preserving
    with pytest.raises(threads.ThreadError): threads.plan(w, pal, needles=4, importance={"nope": 2})


def test_bench_append_is_idempotent(tmp_path):
    """follow-up 6: re-running the bench stage for the same label + git sha replaces its row (json and BENCH.md line)
    instead of stacking duplicates; another sha appends. Mutation (always append) -> red."""
    from digitize import bench
    def row(label, sha, ok):
        return dict(date="2026-10-20", label=label, git_sha=sha, direction=dict(pct_ok=ok, pct_chaos=1.0, pct_ok_all_stitches=50.0),
                    angle_coherence=dict(ok=True), density=dict(mean=1, p95=2, flags=0), trims=dict(per_100cm2=10.0, trims=3),
                    satin=dict(satins=0, blob=0, too_wide=0, too_narrow=0, fans=0), stack=dict(max=2, over_cm2=0.0),
                    colours=dict(threads_in_file=12, red=True, gold=True), verdict=dict(a=True))
    bench.append(row("M2", "abc", 80.0), str(tmp_path)); bench.append(row("M2", "abc", 85.0), str(tmp_path))
    rows = json.load(open(tmp_path / "bench" / "SCOREBOARD.json")); md = open(tmp_path / "bench" / "BENCH.md").read()
    assert len(rows) == 1 and rows[0]["direction"]["pct_ok"] == 85.0, rows
    assert md.count("| M2 |") == 1 and "| 85.0 |" in md and "| 80.0 |" not in md
    bench.append(row("M2", "def", 86.0), str(tmp_path))
    assert len(json.load(open(tmp_path / "bench" / "SCOREBOARD.json"))) == 2 and open(tmp_path / "bench" / "BENCH.md").read().count("| M2 |") == 2


def test_digitize_satin_has_no_random_jitter():
    """LOW follow-up: column.py's legacy _split_long jitters split points with a random number generator; the digitize
    satin plugins must never reach it (rule 2: never random). Two plans of the same wide column are identical even when
    the shared RNG has moved on. Mutation (satin plan via column.column_pts) -> red."""
    from digitize.techniques import column as C
    p = Part(id="s", kind="pool", geom=box(0, 0, 9, 40), thread="t", z=0, dir=DirSpec(0.0), meta=dict(cl=[(4.5, 0.0), (4.5, 40.0)], w=9.0))
    p.technique = "satin"; p.stitch = _spec("satin")
    a = _segs(techniques.get("satin").plan(p)); C.RNG.random(); C.RNG.random()
    b = _segs(techniques.get("satin").plan(p))
    assert a == b and len(a) > 50
