"""ENGINE_PLAN M4s: the part-based stack gate and the travel-on-sewn-fill gate (engine/digitize/gates_stack.py), read
from the LABELLED written file. Each guard was proven RED by a mutation of the code it guards (scratchpad
m4s/mutate_m4s.py, listed in RECAP-2026-10-20-engine-m4s.md) and is GREEN on this branch. The real-file proof (M2 file /
limit_stack-off run FAIL, M4g file PASS) is in projects/castle-falls-jacket/bench/BENCH_m4s.md."""
import pytest
from types import SimpleNamespace
from shapely.geometry import box
from digitize import gates_stack as GS, bench
from digitize.schema import Block

B = (-5.0, -5.0, 45.0, 45.0)


def rows(x0, y0, x1, y1, sp=0.4, horizontal=True):
    """a tatami-like fill: parallel rows sp mm apart joined end to end (boustrophedon), as segments"""
    out = []; k = 0; prev = None
    if horizontal:
        y = y0
        while y <= y1 + 1e-9:
            a, b = ((x0, y), (x1, y)) if k % 2 == 0 else ((x1, y), (x0, y))
            if prev: out.append((*prev, *a))
            out.append((*a, *b)); prev = b; y += sp; k += 1
    else:
        x = x0
        while x <= x1 + 1e-9:
            a, b = ((x, y0), (x, y1)) if k % 2 == 0 else ((x, y1), (x, y0))
            if prev: out.append((*prev, *a))
            out.append((*a, *b)); prev = b; x += sp; k += 1
    return out


def sew(*items):
    """items: (label, segments) in sew order -> (segs, labels)"""
    segs, lab = [], []
    for l, s in items: segs += s; lab += [l] * len(s)
    return segs, lab


def travel(x0, y0, x1, y1, step=3.0):
    """a straight travel line cut into ~step mm stitches"""
    import math
    n = max(1, int(math.ceil(math.dist((x0, y0), (x1, y1)) / step)))
    pts = [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n) for i in range(n + 1)]
    return [(*a, *b) for a, b in zip(pts[:-1], pts[1:])]


# ================================================================== part-based stack (rule 6 by parts)
def test_three_parts_over_one_area_fail_and_two_pass():
    """three fills over a 10 x 10 mm area are 3 layers there: the gate measures ~100 mm2 over 2 and fails; with the
    third part moved off, the same two parts overlapping pass with 0 mm2. Mutation: max_parts 2 -> 3 (or layers
    counted per segment run) -> RED."""
    a = rows(0, 0, 20, 20); b = rows(10, 0, 30, 20, horizontal=False); c = rows(10, 10, 20, 30)
    segs, lab = sew(("A", a), ("B", b), ("C", c))
    r = GS.part_stack(segs, lab, B)
    assert 70.0 <= r["over_mm2"] <= 110.0 and r["max"] == 3 and not r["ok"], {k: r[k] for k in ("over_mm2", "max", "pct_over")}
    segs, lab = sew(("A", a), ("B", b), ("C", rows(32, 25, 42, 40)))
    r2 = GS.part_stack(segs, lab, B)
    assert r2["over_mm2"] == 0.0 and r2["max"] == 2 and r2["ok"]


def test_a_seam_next_to_an_overlap_is_not_a_third_layer():
    """B lies under A's edge by a 1 mm underlap band (y 9..10); C sits on B next to A, its pull comp lapping A's edge
    by 0.3 mm (y 9.7..10): only a 0.3 mm sliver is 3 deep, the seam spill every junction has. A window straddling the
    seam sees all three for its whole 20 mm length; the 1-cell erosion (a part is a layer where it is SOLID) removes
    that. Without erosion the gate flags the seam (the M4g file: 1,532 such cells, 67 really 3 deep in plan geometry).
    Mutation: erode_cells default 1 -> 0 -> RED."""
    segs, lab = sew(("B", rows(0, 9, 20, 16, horizontal=False)), ("A", rows(0, 0, 20, 10)), ("C", rows(0, 9.7, 20, 16)))
    r = GS.part_stack(segs, lab, B)
    assert r["over_mm2"] == 0.0 and r["raw_over_mm2"] <= 0.5, (r["over_mm2"], r["raw_over_mm2"])
    raw = GS.part_stack(segs, lab, B, erode_cells=0)
    assert raw["over_mm2"] > 4.0, "fixture must show the seam artefact the erosion exists for"


def test_a_junction_speck_is_reported_but_not_gated():
    """three parts meeting with a 1.5 x 1.5 mm triple overlap (pull comp of three parts at a junction): reported in
    raw_over_mm2, but a region under min_region_mm2 (4 mm2, the strict gate's flag size) does not count; a 3 x 3 mm
    triple overlap does. Mutation: region filter dropped -> RED (first assert); filter on the wrong side -> RED."""
    a = rows(0, 0, 11.5, 11.5); b = rows(10, 0, 20, 11.5, horizontal=False); c = rows(0, 10, 20, 20)
    r = GS.part_stack(*sew(("A", a), ("B", b), ("C", c)), B)
    assert r["raw_over_mm2"] > 0 and r["over_mm2"] == 0.0, (r["raw_over_mm2"], r["over_mm2"])
    a = rows(0, 0, 13, 13); b = rows(10, 0, 20, 13, horizontal=False); c = rows(0, 10, 20, 20)
    r = GS.part_stack(*sew(("A", a), ("B", b), ("C", c)), B)
    assert r["over_mm2"] >= 4.0 and r["n_flags"] == 1, (r["raw_over_mm2"], r["over_mm2"])


def test_travel_and_line_parts_are_never_layers():
    """over a 2-part overlap: dense hidden travel (label None) and a run part's triple run are not a third layer.
    Mutations: travel counted as a part; line_parts ignored -> RED."""
    a = rows(0, 0, 20, 20); b = rows(0, 0, 20, 20, horizontal=False)
    tr = rows(5, 5, 15, 15, sp=0.3)                      # a travel scribble as dense as a fill
    run = rows(5, 5, 15, 15, sp=0.3, horizontal=False)   # a line part sewn as dense as a fill
    segs, lab = sew(("A", a), ("B", b), (None, tr), ("R", run))
    r = GS.part_stack(segs, lab, B, line_parts=["R"])
    assert r["over_mm2"] == 0.0 and r["max"] == 2, r["over_mm2"]


def test_stack_gate_that_saw_nothing_cannot_pass():
    """nothing sewn inside the bounds (or only travel): raise, never a silent 0 % (prove-the-guard #5 / #9)"""
    with pytest.raises(ValueError):
        GS.part_stack([], [], B)
    with pytest.raises(ValueError):
        GS.part_stack([(100, 100, 120, 100)], ["A"], B)


# ================================================================== travel on sewn fill
def test_travel_on_top_of_earlier_fill_is_exposed():
    """fill A sewn, THEN a same-thread travel line across it to the next part: ~20 mm of travel lie on sewn fill and
    nothing later buries them. Mutation: the time test dropped (fill sewn any time counts) is caught by the next test;
    exposure threshold min_ex raised past the stitch -> RED here."""
    segs, lab = sew(("A", rows(0, 0, 20, 20)), (None, travel(-2, 10, 25, 10)), ("D", rows(26, 0, 36, 20)))
    r = GS.travel_on_fill(segs, lab, B)
    assert r["n_exposed"] >= 6 and 17.0 <= r["exposed_mm"] <= 23.0 and not r["ok"], (r["n_exposed"], r["exposed_mm"])
    assert r["per_100cm2"] > 0 and r["covered_mm2"] > 600


def test_travel_sewn_before_the_fill_is_hidden():
    """the same travel sewn BEFORE fill A (underpath, rule 5): A covers it -> 0 exposed. Mutation: 'sewn before' test
    dropped -> RED."""
    segs, lab = sew((None, travel(-2, 10, 25, 10)), ("A", rows(0, 0, 20, 20)), ("D", rows(26, 0, 36, 20)))
    r = GS.travel_on_fill(segs, lab, B)
    assert r["n_exposed"] == 0 and r["exposed_mm"] == 0.0 and r["ok"], r["exposed"][:3]


def test_travel_on_fill_buried_by_a_later_fill_is_hidden():
    """travel on top of A, then part C sewn over the travel path: buried, 0 exposed (a later top layer hides it).
    Mutation: burial test dropped -> RED."""
    segs, lab = sew(("A", rows(0, 0, 20, 20)), (None, travel(-2, 10, 25, 10)), ("C", rows(-3, 8, 26, 12, horizontal=False)))
    r = GS.travel_on_fill(segs, lab, B)
    assert r["n_exposed"] == 0, r["exposed"][:3]


def test_travel_over_bare_fabric_is_not_this_gate():
    """travel over bare fabric is qa.exposed_stitches / dst2.exposed_travel's job; this gate is travel ON fill only"""
    segs, lab = sew(("A", rows(0, 0, 10, 10)), (None, travel(0, 30, 40, 30)), ("D", rows(30, 0, 40, 10)))
    assert GS.travel_on_fill(segs, lab, B)["n_exposed"] == 0


def test_planned_travel_blocks_count_as_travel():
    """a planned role 'travel' block carries its part's id on the file; travel_segment_index finds it from the plan's
    blocks and the gate treats it as travel. Mutations: index returns []; travel_segs ignored -> RED."""
    tr = travel(-2, 10, 25, 10)
    segs, lab = sew(("A", rows(0, 0, 20, 20)), ("D", tr), ("D", rows(26, 0, 36, 20)))
    pts = [(s[0], s[1]) for s in tr] + [(tr[-1][2], tr[-1][3])]
    idx = GS.travel_segment_index(segs, lab, {"D": [Block("D", "travel", pts), Block("D", "top", [(26, 0), (36, 0)])]})
    assert len(idx) == len(tr), idx
    assert GS.travel_on_fill(segs, lab, B)["n_exposed"] == 0                  # labelled D: a fill without the index
    assert GS.travel_on_fill(segs, lab, B, travel_segs=idx)["n_exposed"] >= 6


def test_travel_gate_that_saw_nothing_cannot_pass():
    with pytest.raises(ValueError):
        GS.travel_on_fill([], [], B)


# ================================================================== verdict: two NEW lines, old 9 kept visible
T = dict(direction_pct_ok_min=85.0, direction_pct_chaos_max=5.0, stack_max_layers=2, trims_per_100cm2_max=25.0, satin_blobs_max=0,
         colours_max=12, density_flags_max=0, separation_close_max=0)


def _row(**kw):
    r = dict(direction=dict(pct_ok=90.0, pct_chaos=1.0, tiles=10), angle_coherence=dict(ok=True), density=dict(flags=0),
             trims=dict(per_100cm2=10.0), satin=dict(blob=0, too_wide=0, too_narrow=0), stack=dict(max=2),
             colours=dict(threads_in_file=12, red=True, gold=True), separation=dict(close=0))
    r.update(kw); return r


def test_verdict_has_eleven_lines_with_m4s_and_nine_without():
    """a row with the M4s measurements gets 11 lines (stack_parts, travel_on_fill after the old 9); an older row keeps
    9, and summary() reports both totals. Mutations: verdict_lines not called / cap ignored / exposed target ignored
    -> RED."""
    old = bench.verdict(_row(), T)
    assert len(old) == 9 and "stack_parts" not in old
    v = bench.verdict(_row(stack_parts=dict(per_100cm2=5.9), travel_on_fill=dict(n_exposed=0)), T)
    assert len(v) == 11 and v["stack_parts"] is False and v["travel_on_fill"] is True
    v2 = bench.verdict(_row(stack_parts=dict(per_100cm2=0.0), travel_on_fill=dict(n_exposed=1800)), T)
    assert v2["stack_parts"] is True and v2["travel_on_fill"] is False
    assert bench.verdict(_row(stack_parts=dict(per_100cm2=5.9)), dict(T, stack_parts_per_100cm2_max=6.0))["stack_parts"] is True
    assert bench.verdict(_row(stack_parts=dict(per_100cm2=2.6)), T)["stack_parts"] is False         # default cap 2.5
    s = GS.summary(v2)
    assert s.startswith("9/11") and "old 9: 8/9" in s, s


def test_run_hook_measures_the_labelled_file_with_line_parts_and_planned_travel():
    """run_hook (the digitize.run gates stage) reads line parts from the plan's techniques and planned travel from its
    blocks: a run part over two fills is not a third layer, and a planned travel block on sewn fill is exposed.
    Mutations: line parts not passed; planned travel not passed -> RED."""
    from digitize.schema import Part, DirSpec
    tr = travel(-2, 10, 25, 10)
    pts = [(s[0], s[1]) for s in tr] + [(tr[-1][2], tr[-1][3])]
    parts = [Part("A", "pool", box(0, 0, 20, 20), "a", 0, DirSpec(0), technique="tatami"),
             Part("B", "pool", box(0, 0, 20, 20), "a", 1, DirSpec(90), technique="tatami"),
             Part("R", "line", box(5, 5, 15, 15), "a", 2, DirSpec(0), technique="run"),
             Part("D", "pool", box(26, 0, 36, 20), "a", 3, DirSpec(0), technique="tatami")]
    plan = SimpleNamespace(parts=parts, blocks={"D": [Block("D", "travel", pts)]})
    segs, lab = sew(("A", rows(0, 0, 20, 20)), ("B", rows(0, 0, 20, 20, horizontal=False)), ("R", rows(5, 5, 15, 15, sp=0.3)),
                    ("D", tr), ("D", rows(26, 0, 36, 20)))
    row = GS.run_hook({}, plan, segs, lab, B)
    assert row["stack_parts"]["over_mm2"] == 0.0 and "grid" not in row["stack_parts"]
    assert row["travel_on_fill"]["n_exposed"] >= 6 and row["travel_on_fill"]["planned_travel_segs"] == len(tr)
