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
def _cgrid(geom, deg, pad=2.0):
    """a stored field grid of constant direction over geom's bounds (what a splitter writes into meta["field"])"""
    x0, y0, x1, y1 = geom.bounds; nx, ny = int(x1 - x0 + 2 * pad) + 2, int(y1 - y0 + 2 * pad) + 2
    return dict(x0=x0 - pad, y0=y0 - pad, step=1.0, nx=nx, ny=ny, deg=[float(deg)] * (nx * ny))


def test_random_angles_are_derived_not_asserted():
    """follow-up 1: random_angles was the constant 0. Every declared angle is now re-derived from its source; an angle
    from rng.uniform has no basis and is counted. Mutation (angle_audit skips the comparison) -> red."""
    rb = Rulebook()
    ok_rule = Part(id="pool.1", kind="pool", geom=box(0, 0, 10, 10), thread="t", z=3.5, dir=rb.direction("pool"))
    G = lambda g: _cgrid(g, 37.5)
    g1, g2, g3, g4 = box(20, 0, 30, 10), box(40, 0, 50, 10), box(60, 0, 70, 10), box(0, 20, 10, 30)
    ok_field = Part(id="stub.1", kind="zone_stub", geom=g1, thread="t", z=1, dir=rb.direction("zone_stub", field=37.5),
                    meta=dict(field_angle=37.5, field=G(g1)))
    sep = Part(id="stub.2", kind="zone_stub", geom=g2, thread="t", z=1, dir=DirSpec(57.5, source="field-mean"),
               meta=dict(field_angle=37.5, sep_deg=20.0, field=G(g2)))
    rnd = Part(id="stub.3", kind="zone_stub", geom=g3, thread="t", z=1, dir=DirSpec(np.random.default_rng(7).uniform(0, 180), source="field-mean"),
               meta=dict(field_angle=37.5, field=G(g3)))
    nob = Part(id="pool.2", kind="pool", geom=box(80, 0, 90, 10), thread="t", z=3.5, dir=DirSpec(33.0, source="rule"))
    big = Part(id="stub.4", kind="zone_stub", geom=g4, thread="t", z=1, dir=DirSpec(77.5, source="field-mean"),
               meta=dict(field_angle=37.5, sep_deg=40.0, field=G(g4)))         # a "separation" beyond the house limit
    r = audit.angle_audit(ObjectPlan(name="t", parts=[ok_rule, ok_field, sep, rnd, nob, big]), rb)
    assert r["random_angles"] == 3, r
    assert {u["part"] for u in r["unexplained"]} == {"stub.3", "pool.2", "stub.4"}, r


def test_field_basis_is_recomputed_not_trusted():
    """PR #6 review: a field-sourced angle used to pass whenever meta["field_mean"] / ["field_angle"] agreed with it, and
    the splitter writes both. The basis is now RECOMPUTED from the stored field grid over the part: a random angle with a
    matching hand-written field_mean is caught, and so is a part with no grid. Mutation (basis read from meta) -> red."""
    rb = Rulebook(); g = box(0, 0, 20, 10); forged = float(np.random.default_rng(3).uniform(60, 120))
    honest = Part(id="s.1", kind="stratum_band", geom=g, thread="t", z=1, dir=DirSpec(40.0, mode="field", source="field"),
                  meta=dict(field=_cgrid(g, 30.0), field_mean=30.0, band_offset_deg=10.0))
    fake = Part(id="s.2", kind="stratum_band", geom=box(30, 0, 50, 10), thread="t", z=1, dir=DirSpec(forged, mode="field", source="field"),
                meta=dict(field=_cgrid(box(30, 0, 50, 10), 30.0), field_mean=forged))
    stub = Part(id="z.1", kind="zone_stub", geom=box(60, 0, 80, 10), thread="t", z=1, dir=DirSpec(forged, source="field-mean"),
                meta=dict(field=_cgrid(box(60, 0, 80, 10), 30.0), field_angle=forged))
    nogrid = Part(id="z.2", kind="zone_stub", geom=box(90, 0, 99, 10), thread="t", z=1, dir=DirSpec(30.0, source="field-mean"),
                  meta=dict(field_angle=30.0))
    r = audit.angle_audit(ObjectPlan(name="t", parts=[honest, fake, stub, nogrid]), rb)
    assert {u["part"] for u in r["unexplained"]} == {"s.2", "z.1", "z.2"}, r
    assert DR.refresh_field_basis([fake]) == 1 and DR.axial_diff(fake.dir.angle, 30.0) < 0.1     # refresh re-measures it


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


def _brow(label, ok=80.0, **kw):
    r = dict(date="2026-10-20", label=label, direction=dict(tiles=625, pct_ok=ok, pct_chaos=1.0, pct_ok_all_stitches=50.0),
             angle_coherence=dict(ok=True), density=dict(mean=1, p95=2, flags=0), trims=dict(per_100cm2=10.0, trims=3),
             satin=dict(satins=0, blob=0, too_wide=0, too_narrow=0, fans=0), stack=dict(max=2, over_cm2=0.0),
             colours=dict(threads_in_file=12, red=True, gold=True), verdict=dict(a=True))
    r.update(kw); return r


def test_bench_rerun_on_same_commit_through_real_git(tmp_path):
    """PR #6 review: the key came from git_sha(), which appended '+dirty' as soon as the first bench run had rewritten the
    tracked bench/SCOREBOARD.json + BENCH.md, so a re-run on the SAME commit got a new key and a duplicate row. Through
    the real git_sha() on a real repo: re-run -> still one row; an engine change outside bench/ -> '+dirty', a new row.
    Mutation (bench/ not excluded from the dirty check) -> red."""
    import subprocess
    from digitize import bench
    repo = tmp_path / "repo"; proj = repo / "proj"; (proj / "bench").mkdir(parents=True)
    (proj / "engine.py").write_text("x = 1\n")
    git = lambda *a: subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *a], check=True, capture_output=True)
    git("init", "-q"); git("add", "."); git("commit", "-q", "-m", "engine")
    bench.append(_brow("M2", 80.0), str(proj))
    git("add", "."); git("commit", "-q", "-m", "first bench row")             # the bench outputs are tracked, as on the branch
    sha = bench.git_sha(str(proj)); assert "+dirty" not in sha and sha != "unknown"
    bench.append(_brow("M2", 81.0), str(proj))                               # rewrites the tracked bench files ...
    bench.append(_brow("M2", 82.0), str(proj))                               # ... which are now modified: still the same key
    rows = json.load(open(proj / "bench" / "SCOREBOARD.json"))
    assert [r["git_sha"] for r in rows] == [sha] and rows[0]["direction"]["pct_ok"] == 82.0, rows
    assert open(proj / "bench" / "BENCH.md").read().count("| M2 |") == 1
    (proj / "engine.py").write_text("x = 2\n")                               # a real engine change, uncommitted
    bench.append(_brow("M2", 83.0), str(proj))
    rows = json.load(open(proj / "bench" / "SCOREBOARD.json"))
    assert [r["git_sha"] for r in rows] == [sha, sha + "+dirty"], rows


def test_direction_verdict_gates_on_independent_tiles():
    """PR #6 review: the combined direction rate counts self-derived tiles (graded against the pixels their angle was
    read from). The gate reads the INDEPENDENT tiles only and needs them to cover >= half the judged tiles; chaos stays
    on all tiles (read from the DST alone). Rule 3 is a verdict line: touching same-thread pairs < 15 deg (stubs
    included). Mutations (gate on the combined rate; separation line dropped) -> red."""
    from digitize import bench
    T = json.load(open(os.path.join(ROOT, "projects", "castle-falls-jacket", "bench", "bench.json")))["targets"]
    src = lambda n, ok: {"independent": dict(tiles=n, pct_ok=ok), "self-derived": dict(tiles=625 - n, pct_ok=89.0)}
    assert bench.verdict(_brow("x", 90.1, direction_by_source=src(73, 97.3)), T)["direction_ok"] is False     # the M2 crop
    assert bench.verdict(_brow("x", 90.1, direction_by_source=src(400, 97.3)), T)["direction_ok"] is True
    assert bench.verdict(_brow("x", 95.0, direction_by_source=src(400, 80.0)), T)["direction_ok"] is False
    assert bench.verdict(_brow("x", 95.0), T)["direction_ok"] is False                                      # no sources: not evidenced
    v = bench.verdict(_brow("x", separation=dict(close=29, pairs=118)), T)
    assert v["separation"] is False and bench.verdict(_brow("x", separation=dict(close=0, pairs=118)), T)["separation"] is True
    assert "separation" not in bench.verdict(_brow("x"), T)                    # older rows keep their 8 lines


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


# ================================================================== M2: organic parts
from digitize import direction as DR, sequence


def _stripes(W_mm, H_mm, ppm, ang_of, period=0.8):
    """grey image of thread rows running along ang_of(x, y) (deg): luminance varies ACROSS the threads"""
    y, x = np.mgrid[0:int(H_mm * ppm), 0:int(W_mm * ppm)] / ppm
    a = np.radians(ang_of(x, y)); n = -x * np.sin(a) + y * np.cos(a)
    return 128 + 60 * np.sin(2 * math.pi * n / period)


def test_field_reads_the_reference_grain():
    """direction.Field: threads run ACROSS the luminance gradient, so stripes along 20 deg read 20 deg (not 110), and an
    area with no grain is flagged by low coherence and filled from the wider field. Mutation (thread = gradient, the
    +90 dropped) -> red."""
    ppm = 12.0; g = _stripes(60, 30, ppm, lambda x, y: np.where(x < 30, 20.0, 110.0))
    g[:, int(26 * ppm):int(34 * ppm)] = 128.0                                     # a flat strip: no grain at all
    F = DR.Field.from_grey(g, (0, 0, 60, 30), ppm)
    a1, c1 = F.at(10.0, 15.0); a2, c2 = F.at(50.0, 15.0)
    assert DR.axial_diff(a1, 20.0) < 3 and DR.axial_diff(a2, 110.0) < 3 and c1 > 0.8 and c2 > 0.8, (a1, a2, c1, c2)
    a3, c3 = F.at(30.0, 15.0)
    assert c3 < 0.25 and math.isfinite(a3), (a3, c3)
    with pytest.raises(ValueError): F.mean(np.zeros(F.c2.shape, bool))


def _grid(fn, x0=-2.0, y0=-2.0, nx=36, ny=26):
    X = x0 + np.arange(nx); Y = y0 + np.arange(ny); XX, YY = np.meshgrid(X, Y)
    return dict(x0=x0, y0=y0, step=1.0, nx=nx, ny=ny, deg=np.asarray(fn(XX, YY), float).ravel().tolist())


def _guided(geom, grid, angle_offset=0.0, spacing=0.45):
    fm = DR.grid_mean(grid, geom)
    p = Part(id="g", kind="stratum_band", geom=geom, thread="t", z=1, dir=DirSpec(fm + angle_offset, mode="field", source="field"),
             meta=dict(field=grid, field_mean=fm, band_offset_deg=angle_offset))
    p.technique = "guided_fill"; p.stitch = _spec("guided_fill", underlay=[], pull_comp=0.0, spacing=spacing)
    return p


def _dev_from_field(segs, grid, off=0.0, min_len=1.0):
    d = []
    for s in segs:
        if math.hypot(s[2] - s[0], s[3] - s[1]) < min_len: continue
        want = DR.grid_angle(grid, (s[0] + s[2]) / 2, (s[1] + s[3]) / 2, off)
        d.append(DR.axial_diff(math.degrees(math.atan2(s[3] - s[1], s[2] - s[0])), want))
    return np.array(d)


def test_guided_fill_rows_follow_a_turning_field():
    """guided_fill: rows are level sets of the phase field, so stitches follow the field where it turns 0 -> 40 deg
    (a straight tatami at the mean angle is ~10 deg off on average), stay ~one spacing apart (density like tatami), and
    honour the declared offset (rule 3 separation / stratum bands). Mutations (rows from a straight hatch; offset
    ignored) -> red."""
    g = box(0, 0, 30, 20); grid = _grid(lambda X, Y: 40.0 * np.clip(X / 30.0, 0, 1))
    top = _segs(techniques.get("guided_fill").plan(_guided(g, grid)), "top")
    d = _dev_from_field(top, grid)
    assert np.median(d) < 3 and np.percentile(d, 95) < 8, (np.median(d), np.percentile(d, 95))
    ref = Part(id="t", kind="pool", geom=g, thread="t", z=1, dir=DirSpec(20.0)); ref.technique = "tatami"
    ref.stitch = _spec("tatami", underlay=[], pull_comp=0.0)
    flat = _segs(techniques.get("tatami").plan(ref), "top")
    assert np.median(_dev_from_field(flat, grid)) > 7                             # what an M1 stub did
    dg, dt = qa.density_map(top, (0, 0, 30, 20)), qa.density_map(flat, (0, 0, 30, 20))
    assert abs(dg["mean"] - dt["mean"]) / dt["mean"] < 0.15 and not dg["flags"], (dg["mean"], dt["mean"])
    turned = _segs(techniques.get("guided_fill").plan(_guided(g, grid, 20.0)), "top")
    assert np.median(_dev_from_field(turned, grid, 20.0)) < 3 and np.median(_dev_from_field(turned, grid)) > 15
    assert qa.satin_shape(top)["counts"]["blob"] == 0 and max(math.hypot(s[2] - s[0], s[3] - s[1]) for s in top) <= 7.0


def _links(blocks, along=0.0, row_sp=0.45):
    """stitches inside blocks that move from one row to another (displacement ACROSS the rows >= 2/3 of a spacing):
    the row-to-row links, whatever their angle"""
    a0 = math.radians(along); nx, ny = -math.sin(a0), math.cos(a0)
    return [math.dist(a, c) for b in blocks for a, c in zip(b.pts, b.pts[1:]) if abs((c[0] - a[0]) * nx + (c[1] - a[1]) * ny) >= 0.66 * row_sp]


def test_guided_fill_blocks_never_jump():
    """the cell walk (LESSONS B23 on curved rows): a row joins the next level's neighbour only when its nearer end is
    within hop mm, so a link stitch never runs far across the fill. A U is sewn cell by cell (arms are their own cells);
    on a steeply slanted strip, where each row end sits ~2.3 mm along from the last, rows are NOT linked by long
    diagonals. Mutation (the hop limit dropped) -> red."""
    from shapely.geometry import Polygon
    U = Polygon([(0, 0), (24, 0), (24, 20), (16, 20), (16, 6), (8, 6), (8, 20), (0, 20)])
    grid = _grid(lambda X, Y: np.zeros_like(X))
    bl = [b for b in techniques.get("guided_fill").plan(_guided(U, grid)) if b.role == "top"]
    assert 2 <= len(bl) <= 6 and max(_links(bl)) <= 1.6, (len(bl), max(_links(bl)))
    S = Polygon([(0, 0), (10, 0), (40, 6), (30, 6)])                             # slanted strip: rows at 0 deg
    bl = [b for b in techniques.get("guided_fill").plan(_guided(S, _grid(lambda X, Y: np.zeros_like(X), nx=45, ny=10))) if b.role == "top"]
    assert max(_links(bl) or [0.0]) <= 1.6, max(_links(bl))


def test_contour_fill_follows_the_outline():
    """contour_fill: rows are rings inset one spacing at a time, so on a disc every stitch runs tangent to the circle
    (perpendicular to the radius), r / spacing rings. Mutation (rings from a straight hatch) -> red."""
    d = Point(0, 0).buffer(8.0, quad_segs=32)
    p = Part(id="c", kind="cloud_lobe", geom=d, thread="t", z=4, dir=DirSpec(0.0, mode="contour", source="outline"), meta=dict(outline_angle=0.0))
    p.technique = "contour_fill"; p.stitch = _spec("contour_fill", underlay=[], pull_comp=0.0)
    top = [s for s in _segs(techniques.get("contour_fill").plan(p), "top") if math.hypot(s[2] - s[0], s[3] - s[1]) > 1.0]
    dev = []
    for s in top:
        mx, my = (s[0] + s[2]) / 2, (s[1] + s[3]) / 2
        if math.hypot(mx, my) < 1.5: continue
        dev.append(DR.axial_diff(math.degrees(math.atan2(s[3] - s[1], s[2] - s[0])), math.degrees(math.atan2(my, mx)) + 90))
    assert len(dev) > 50 and np.median(dev) < 8, np.median(dev)
    from digitize.techniques.contour_fill import rings
    assert abs(len(rings(d, 0.45)) - 8.0 / 0.45) <= 2


def test_blend_is_an_open_layer_nothing_cut_under_it():
    """blend (rules 7, 8): no underlay, and sequence.cut_under never cuts the fill BELOW an open layer (a shade sewn over
    a cut-away hole would show the fabric). Feather rows start on the source edge and thin out. Mutations (is_open
    always False; feather rows not turned to the source side) -> red."""
    lobe = Part(id="lobe", kind="cloud_lobe", geom=box(0, 0, 20, 12), thread="w", z=4.0, dir=DirSpec(0.0)); lobe.technique = "guided_fill"
    shade = Part(id="sh", kind="cloud_shade", geom=box(4, 6, 16, 12), thread="m", z=4.3, dir=DirSpec(0.0, source="field-mean"), meta=dict(field_angle=0.0))
    shade.technique = "blend"; shade.stitch = Rulebook().stitch_spec("cloud_shade", "blend")
    sequence.cut_under([lobe, shade], keep=1.0)
    assert abs(lobe.geom.area - 240.0) < 0.5, lobe.geom.area                      # the lobe is whole under its shade
    assert techniques.get("blend").check(shade, Rulebook().principles) == [] and shade.stitch.underlay == []
    shade.stitch.underlay = ["edge_run"]
    assert any(i["rule"] == 7 for i in techniques.get("blend").check(shade, Rulebook().principles))
    for edge, near, far_ in ((10.0, lambda y: y < 10.3, lambda y: y > 12.7), (13.0, lambda y: y > 12.7, lambda y: y < 10.3)):
        fb = Part(id="fb", kind="sky_blend", geom=box(0, 10, 40, 13), thread="s", z=0.5, dir=DirSpec(90.0), meta=dict(blend_from=[[-1, edge], [41, edge]]))
        fb.technique = "blend"; fb.stitch = Rulebook().stitch_spec("sky_blend", "blend")
        pts = [q for b in techniques.get("blend").plan(fb) for q in b.pts]
        n_src = sum(1 for q in pts if near(q[1])); n_far = sum(1 for q in pts if far_(q[1]))
        assert n_src > 2 * n_far and n_far > 0, (edge, n_src, n_far)            # dense at the source edge, thinning out


def test_neighbour_separation_turns_within_limits():
    """rule 3: touching same-thread parts closer than 15 deg are turned to >= 15 deg apart, never more than 25 deg off
    their own evidence; other threads and contour parts are left alone; the audit accepts the turn. Mutation (clash
    threshold 0) -> red."""
    A, B, C = box(0, 0, 20, 20), box(20, 0, 30, 20), box(30, 0, 40, 20)
    a = Part(id="a", kind="stratum_band", geom=A, thread="t", z=1, dir=DirSpec(80.0, mode="field", source="field"), meta=dict(field_mean=80.0, field=_cgrid(A, 80.0)))
    b = Part(id="b", kind="stratum_band", geom=B, thread="t", z=1, dir=DirSpec(86.0, mode="field", source="field"), meta=dict(field_mean=86.0, field=_cgrid(B, 86.0)))
    c = Part(id="c", kind="stratum_band", geom=C, thread="u", z=1, dir=DirSpec(88.0, mode="field", source="field"), meta=dict(field_mean=88.0, field=_cgrid(C, 88.0)))
    e = Part(id="e", kind="cloud_lobe", geom=box(0, 20, 20, 30), thread="t", z=1, dir=DirSpec(80.0, mode="contour", source="outline"), meta=dict(outline_angle=80.0))
    moves = DR.separate([a, b, c, e], sep=(15, 25))
    assert [m[0] for m in moves] == ["b"], moves
    assert DR.axial_diff(a.dir.angle, b.dir.angle) >= 15 and abs(b.meta["sep_deg"]) <= 25 and c.dir.angle == 88.0 and e.dir.angle == 80.0
    assert audit.angle_audit(ObjectPlan(name="t", parts=[a, b, c, e]), Rulebook())["random_angles"] == 0
    assert DR.separation_report([a, b, c, e])["close"] == 0


def test_merge_specks_keeps_wisps_and_cracks():
    """rule 1 / LESSONS A19: a speck (< 20 mm2; protected accents < 4 mm2) merges into the touching part it shares most
    border with; wisps, shade layers and crack lines are deliberate small parts and stay. Mutation (keep_small
    ignored) -> red."""
    big = Part(id="big", kind="zone_stub", geom=box(0, 0, 20, 20), thread="g", z=2, dir=DirSpec(0.0))
    other = Part(id="other", kind="zone_stub", geom=box(20, 0, 22, 20), thread="h", z=2, dir=DirSpec(0.0))
    speck = Part(id="speck", kind="stratum_band", geom=box(21.5, 8, 26, 11), thread="n", z=1.5, dir=DirSpec(0.0))
    gold = Part(id="gold", kind="zone_stub", geom=box(5, 5, 7, 7.5), thread="cf_gold", z=5, dir=DirSpec(0.0))
    wisp = Part(id="wisp", kind="cloud_wisp", geom=box(-6, 2, 0, 3.5), thread="w", z=4, dir=DirSpec(0.0))
    crack = Part(id="crack", kind="stratum_crack", geom=LineString([(2, 2), (2, 10)]).buffer(0.3), thread="n", z=2.1, dir=DirSpec(90.0))
    out, moves = sequence.merge_specks([big, other, speck, gold, wisp, crack], 20.0, protected=["cf_gold"], min_protected_mm2=4.0)
    ids = {p.id for p in out}
    assert ids == {"big", "gold", "wisp", "crack"} | {"other"}, (ids, moves)
    assert ("speck", "other") in moves and other.geom.area > 50.0, moves
    assert not [m for m in moves if m[0] in ("wisp", "crack") or m[1] in ("wisp", "crack")], moves


def test_zone_except_cuts_other_windows(tmp_path):
    """zones: "except" cuts other zones' windows out of a whole-crop window (the cliffs no longer swallow the sky's
    pixels before the sky claims them). Mutation (except ignored) -> red."""
    from digitize.extract import zones as ZN
    f = tmp_path / "z.json"
    f.write_text(json.dumps(dict(zones=[dict(id="sky", splitter="sky", windows=[[[0, 0], [10, 0], [10, 10], [0, 10]]]),
                                        {"id": "rock", "splitter": "stratum", "windows": [[[0, 0], [30, 0], [30, 30], [0, 30]]], "except": ["sky"]}])))
    zs = ZN.load(str(f)); rock = ZN.window(zs["zones"][1])
    assert abs(rock.area - (900 - 100)) < 1e-6 and not rock.contains(Point(5, 5))


def test_audit_field_adherence_reads_the_planned_field():
    """audit.sewn_angles judges guided parts per stitch against THEIR planned field (a turning field), not one angle:
    the guided plan scores ~100 %, the same part sewn as straight tatami far lower. Mutation (compare to the part's
    mean angle) -> red."""
    g = box(0, 0, 30, 20); grid = _grid(lambda X, Y: 50.0 * np.clip(X / 30.0, 0, 1))
    p = _guided(g, grid); plan = ObjectPlan(name="t", parts=[p])
    segs = _segs(techniques.get("guided_fill").plan(p), "top")
    ok = audit.sewn_angles(plan, segs, ["g"] * len(segs), (0, 0, 30, 20))["field_adherence"]
    t = Part(id="x", kind="pool", geom=g, thread="t", z=1, dir=DirSpec(p.dir.angle)); t.technique = "tatami"; t.stitch = _spec("tatami", underlay=[], pull_comp=0.0)
    flat = _segs(techniques.get("tatami").plan(t), "top")
    bad = audit.sewn_angles(plan, flat, ["g"] * len(flat), (0, 0, 30, 20))["field_adherence"]
    assert ok["pct_within"] > 95 and bad["pct_within"] < 75, (ok, bad)


def test_rulebook_m2_kinds_match_principles():
    """the M2 kinds carry the playbook's numbers, read from docs/DIGITIZING_PRINCIPLES.md (editing either alone -> red):
    strata bands differ by 15-25 deg (2 x band_offset), wisps at the sky angle at half density, shading layers without
    underlay, clouds may use contour fill or split satin, strata guided tatami first, cracks as run."""
    doc = open(os.path.join(ROOT, "docs", "DIGITIZING_PRINCIPLES.md")).read(); K = Rulebook().data["kinds"]; T = Rulebook().data["techniques"]
    lo, hi = (int(v) for v in re.search(r"along the bedding plane, ±(\d+)–(\d+)° between bands", doc).groups())
    assert lo <= 2 * K["stratum_band"]["band_offset_deg"] <= hi
    assert "wisps at the sky angle, half density" in doc
    assert K["cloud_wisp"]["dir"] == K["sky_band"]["dir"] and K["cloud_wisp"]["spacing"] == 2 * T["tatami"]["spacing"]
    assert "shade as an open layer" in doc and K["cloud_shade"]["underlay"] == [] and K["cloud_shade"]["params"]["mode"] == "open"
    assert T["blend"]["underlay"] == [] and K["sky_blend"]["underlay"] == []
    assert "contour/turning fill or near-vertical split satin" in doc
    assert {"contour_fill", "split_satin"} <= set(K["cloud_lobe"]["techniques"]) and 60 <= K["cloud_lobe"]["alt_dir"] <= 90
    assert "cracks as run on top" in doc and K["stratum_crack"]["techniques"][0] == "run"
    assert "guided tatami" in doc and K["stratum_band"]["techniques"][0] == "guided_fill"
    assert Rulebook(toggles={"guided_fill": False}).direction("stratum_band", field=40.0, technique="tatami").angle == K["stratum_band"]["alt_dir"]


# ------------------------------------------------------------------ splitters on synthetic evidence
NAVY, SLATE, WHITE, MIST = (34, 53, 92), (86, 101, 119), (238, 234, 224), (158, 163, 166)
PAL = {"n": "#22355C", "s": "#566577", "w": "#EEEAE0", "m": "#9EA3A6"}


def _ctx(rgb, grey, bounds, ppm=12.0):
    from digitize.extract import evidence
    from digitize.extract.splitters import Ctx
    from digitize import config
    ref = dict(bounds=bounds, ppm=ppm, rgb=rgb, grey=grey, closeup_weight=np.ones(grey.shape))
    ev = evidence.build(ref, PAL, ppm=4.0)
    return Ctx(ev, Rulebook(), config.merge(config.DEFAULTS, {}), {k: k for k in PAL}, []), ev


def test_stratum_splitter_bands_along_the_grain():
    """stratum.split on a synthetic cliff: rows of thread at 60 deg, two tones in alternating 10 mm strips ALONG the
    grain. Each part is a guided band with the grain as its field (mean ~60), bands alternate +10 / -10 so neighbouring
    bands differ ~20 deg (playbook +-15-25), both tones kept. Mutation (band sign never alternates) -> red."""
    from digitize.extract.splitters import stratum
    ppm = 12.0; W, H = 60, 40
    y, x = np.mgrid[0:H * int(ppm), 0:W * int(ppm)] / ppm
    a = math.radians(60.0); n = -x * math.sin(a) + y * math.cos(a)
    band = (np.floor(n / 10.0) % 2).astype(int)
    rgb = np.where(band[..., None] == 0, np.array(NAVY, float), np.array(SLATE, float)) * (1 + 0.08 * np.sin(2 * math.pi * n / 0.8))[..., None]
    grey = rgb @ np.array([0.299, 0.587, 0.114])
    ctx, ev = _ctx(rgb, grey, (0, 0, W, H))
    parts, used = stratum.split(ctx, {"id": "rock"}, 1.5, np.ones((ev.H, ev.W), bool))
    bands = [p for p in parts if p.kind == "stratum_band"]
    assert len({p.meta["band"] for p in bands}) >= 3 and used.all()
    for p in bands:
        assert p.dir.mode == "field" and DR.axial_diff(p.meta["field_mean"], 60.0) < 6, (p.id, p.meta["field_mean"])
        assert abs(p.meta["band_offset_deg"]) == 10.0
    from shapely.strtree import STRtree
    tree = STRtree([p.geom for p in bands]); pairs = 0
    for p in bands:
        for j in tree.query(p.geom.buffer(0.3), predicate="intersects"):
            q = bands[int(j)]
            if q.meta["band"] == p.meta["band"] + 1:
                pairs += 1; assert DR.axial_diff(p.dir.angle, q.dir.angle) >= 15, (p.dir.angle, q.dir.angle)
    assert pairs >= 2
    assert {p.thread for p in bands} == {"n", "s"}
    assert audit.angle_audit(ObjectPlan(name="t", parts=bands), Rulebook())["random_angles"] == 0


def test_cloud_splitter_lobes_back_to_front_shade_and_wisp():
    """cloud.split on a synthetic cloud: three overlapping round lobes at different heights, a darker shade in the lowest
    one and a thin trailing wisp. One part per lobe in the lit thread; the lobe whose lowest point is higher on the
    garment sews first (lower z); the shade is an open layer above the lobes; the wisp is at the sky angle. Mutation
    (lobe order reversed) -> red."""
    from digitize.extract.splitters import cloud
    ppm = 12.0; W, H = 70, 40
    y, x = np.mgrid[0:H * int(ppm), 0:W * int(ppm)] / ppm
    disc = lambda cx, cy, r: (x - cx) ** 2 + (y - cy) ** 2 <= r * r
    L1, L2, L3 = disc(18, 16, 8), disc(32, 13, 9), disc(46, 22, 8)
    shade = L3 & (y > 24)
    wisp = (np.abs(y - 26.5) < 0.9) & (x > 52) & (x < 66)
    cl = L1 | L2 | L3 | wisp
    rgb = np.where(cl[..., None], np.array(WHITE, float), np.array(NAVY, float))
    rgb = np.where(shade[..., None], np.array(MIST, float), rgb)
    grey = (rgb @ np.array([0.299, 0.587, 0.114])) * (1 + 0.05 * np.sin(2 * math.pi * y / 0.8))
    ctx, ev = _ctx(rgb, grey, (0, 0, W, H))
    claim = np.isin(ev.tone, [ev.keys.index("w"), ev.keys.index("m")])
    parts, used = cloud.split(ctx, {"id": "cloud"}, 4.0, claim)
    lobes = [p for p in parts if p.kind == "cloud_lobe"]; shades = [p for p in parts if p.kind == "cloud_shade"]
    wisps = [p for p in parts if p.kind == "cloud_wisp"]
    assert len(lobes) >= 3, [p.geom.bounds for p in lobes]
    low = sorted(lobes, key=lambda p: p.geom.bounds[3])
    assert [p.z for p in low] == sorted(p.z for p in lobes) and low[0].z < low[-1].z
    assert shades and all(s.thread == "m" and s.z > max(l.z for l in lobes) for s in shades)
    assert wisps and all(w.dir.angle == Rulebook().rule("sky_band")["dir"] for w in wisps)
    assert all(p.thread == "w" for p in lobes)
