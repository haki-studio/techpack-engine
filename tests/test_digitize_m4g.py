"""ENGINE_PLAN M4g: thread planner, full sequencing, the review step (question flow). Each guard was proven RED by a
mutation of the code it guards (scratchpad m4g/mutate_m4g.py, listed in RECAP-2026-10-20-engine-m4g.md) and is GREEN
on this branch."""
import json, math
from collections import Counter
import numpy as np
import pytest
from shapely.geometry import box, Polygon
from shapely.ops import unary_union
from digitize.schema import Part, DirSpec, ObjectPlan, Block, StitchSpec
from digitize.rulebook import Rulebook
from digitize import sequence as SQ, threads as TH, review as RV, audit


def P(id_, g, thread="a", z=0.0, kind="pool", **meta):
    return Part(id=id_, kind=kind, geom=g, thread=thread, z=z, dir=DirSpec(0), meta=dict(meta))


# ================================================================== rule 6: <= 2 stacked layers
def test_limit_stack_cuts_the_lowest_and_opens_no_gap():
    """three fills over one spot (the 1 mm underlap bands of two lower parts meeting under a third): the LOWEST loses
    that area, the two above are untouched, and the covered area is the same (no gap). Mutations: no cut -> stack 3;
    cut the highest instead -> the visible top part changes."""
    lo = P("lo", box(0, 0, 20, 20), z=0); mid = P("mid", box(10, 0, 30, 20), "b", z=1); top = P("top", box(15, 0, 40, 20), "c", z=2)
    parts = [lo, mid, top]; cover0 = unary_union([p.geom for p in parts]); top0 = top.geom
    assert SQ.stack_count(parts) == 3
    cut = SQ.limit_stack(parts, max_layers=2)
    assert SQ.stack_count(parts) == 2, cut
    assert [c[0] for c in cut] == ["lo"] and abs(cut[0][1] - 100.0) < 0.5, cut             # x 15..20 of lo (5 x 20 mm)
    assert top.geom.equals(top0) and abs(mid.geom.area - 400) < 1e-6
    assert abs(unary_union([p.geom for p in parts]).area - cover0.area) < 1e-6           # nothing became bare


def test_stack_reach_removes_a_band_under_the_seam_of_two_higher_parts():
    """the file gate counts layers per 1 mm CELL: a lower band under the seam of two abutting higher parts is 3 runs in
    one cell. reach=1 removes the band under A within 1 mm of B (and vice versa), never the lower part's VISIBLE area.
    Mutations: reach ignored -> band stays; cut not restricted to covered area -> L's visible area shrinks."""
    L = P("L", box(0, 0, 20, 11), z=0)                                   # its top 1 mm (y 10..11) runs under A and B
    A = P("A", box(0, 10, 10, 20), "b", z=1); B = P("B", box(10, 10, 20, 20), "c", z=1)
    vis0 = L.geom.difference(unary_union([A.geom, B.geom]))
    SQ.limit_stack([L, A, B], max_layers=2, reach=0.0)
    assert abs(L.geom.area - 220) < 1e-6                                 # without reach nothing is 3-deep: no cut
    SQ.limit_stack([L, A, B], max_layers=2, reach=1.0)
    band = L.geom.intersection(box(9, 10, 11, 11)).area
    assert band < 0.05, band                                             # the band under the seam is gone (2 x 1 mm)
    assert abs(L.geom.intersection(box(0, 10, 8, 11)).area - 8.0) < 0.05   # ... but stays under A away from the seam
    assert L.geom.difference(unary_union([A.geom, B.geom])).symmetric_difference(vis0).area < 1e-6


# ================================================================== rule 5: z-DAG, hints, colour stops
def test_order_v1_lookahead_saves_a_stop_and_never_breaks_the_dag():
    """found by random search (scratchpad m4g/find_la.py): greedy (deepest first) sews c, b, c, b = 4 stops; the
    rollout sews b, c, b = 3. Both keep every z edge. Mutation: lookahead ignored -> 4 stops."""
    parts = [P("p0", box(0, 10, 12, 22), "b", 1.0), P("p1", box(10, 10, 22, 22), "c", 2.0),
             P("p2", box(20, 0, 32, 12), "b", 4.0), P("p3", box(30, 10, 42, 22), "c", 0.0)]
    g = SQ.order_v1(parts, lookahead=False); la = SQ.order_v1(parts, lookahead=True)
    assert len(g) == 4 and len(la) == 3, (g, la)
    for st in (g, la):
        rep = SQ.report(ObjectPlan(name="t", parts=parts, stops=st))
        assert rep["dag_violations"] == 0 and sorted(i for s in st for i in s["parts"]) == ["p0", "p1", "p2", "p3"], rep


def test_sequence_hints_seq_after_knockout_and_errors():
    """the M3a/M3b contract: seq_after orders parts that do not touch; knockout_of cuts the hole in the fill and sews the
    detail first; a hint naming no part raises; a hint cycle raises. Mutations: hint edges ignored -> order follows z;
    knockout without the hole -> the fill still covers the detail."""
    a = P("wall", box(0, 0, 10, 10), "a", z=1); b = P("roof", box(50, 0, 60, 10), "b", z=0, seq_after=["wall"])
    st = SQ.order_v1([a, b])
    assert [s["parts"] for s in st] == [["wall"], ["roof"]], st                 # without the hint: roof (z 0) first
    fill = P("wall2", box(0, 0, 20, 20), "a", z=2); win = P("win", box(5, 5, 9, 9), "b", z=3, knockout_of="wall2")
    rep = SQ.apply_hints([fill, win])
    assert rep["knockouts"] == [("win", "wall2")] and win.z < fill.z
    assert fill.geom.intersection(win.geom).area < 1e-6 and abs(fill.geom.area - 384) < 1e-6
    SQ.underlap([fill, win], 1.0)                                               # the fill (higher) covers the window edge
    assert win.geom.intersection(fill.geom).area > 10
    assert SQ.order_v1([fill, win])[0]["parts"] == ["win"]
    with pytest.raises(SQ.HintError): SQ.dag_v1([P("x", box(0, 0, 1, 1), seq_after=["nope"])])
    c1 = P("c1", box(0, 0, 1, 1), seq_after=["c2"]); c2 = P("c2", box(5, 5, 6, 6), "b", seq_after=["c1"])
    with pytest.raises(SQ.HintError): SQ.dag_v1([c1, c2])
    k1 = P("k1", box(0, 0, 1, 1), group="g1"); k2 = P("k2", box(5, 5, 6, 6), "b", seq_before=["group:g1"])
    assert SQ.order_v1([k1, k2])[0]["parts"] == ["k2"]


# ================================================================== planned entry / exit
def _segset(blocks):
    return Counter(tuple(sorted([tuple(np.round(a, 6)), tuple(np.round(b, 6))])) for bl in blocks for a, b in zip(bl.pts, bl.pts[1:]))


def test_orient_part_same_stitches_less_travel_and_keeps_the_cell_walk():
    """planned entry: the edge run starts at its vertex nearest the needle, the underlay chain and the top chain may be
    sewn backwards, never re-ordered inside. Same stitches. Mutations: no reversal / no ring rotation -> more travel;
    re-ordering cells inside the top chain -> the cell walk is broken."""
    ring = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
    lat = [Block("p", "underlay", [(1, y), (9, y)]) for y in (2, 4, 6, 8)]
    top = [Block("p", "top", [(1, 1), (9, 1), (9, 1.5), (1, 1.5)]), Block("p", "top", [(1, 9), (9, 9)]), Block("p", "top", [(1, 5), (9, 5)])]
    # (the walk A y1 -> B y9 -> C y5 on purpose: nearest-next from A would take C first)
    blocks = [Block("p", "underlay", ring)] + lat + top
    entry = (10, 10.5)
    def travel(bl, cur):
        t = 0.0
        for b in bl: t += math.dist(cur, b.pts[0]); cur = b.pts[-1]
        return t
    out, exit_ = SQ.orient_part(blocks, entry)
    assert _segset(out) == _segset(blocks)                                    # the same stitches
    assert out[0].pts[0] == (10, 10) and out[0].pts[-1] == (10, 10)           # the ring starts nearest the needle
    assert travel(out, entry) < travel(blocks, entry) - 10, (travel(out, entry), travel(blocks, entry))
    tops = [b for b in out if b.role == "top"]                                # the cell walk: forwards or whole-backwards
    ys = [b.pts[0][1] for b in tops]
    assert ys in ([1, 9, 5], [5, 9, 1.5]), ys
    assert [b.role for b in out] == ["underlay"] * 5 + ["top"] * 3


def test_inner_travel_runs_inside_the_part_around_a_bend():
    """a U-shaped part: a move from one arm's underlay to the other arm's would cross the gap (bare fabric, so dst2
    trims, and the trim splits the part into two runs the stack gate counts twice). The planned path stays inside.
    Mutation: path = the straight line -> it leaves the part."""
    U = Polygon([(0, 0), (30, 0), (30, 30), (20, 30), (20, 10), (10, 10), (10, 30), (0, 30)])
    bl = [Block("u", "underlay", [(5, 28), (5, 2)]), Block("u", "underlay", [(25, 28), (25, 2)]), Block("u", "top", [(2, 2), (28, 2)])]
    out, n = SQ.plan_inner_travel(bl, U)
    assert n == 1 and out[1].role == "travel", [b.role for b in out]
    from shapely.geometry import LineString
    path = LineString(out[1].pts)
    assert path.within(U.buffer(0.25)) and math.dist(out[1].pts[0], (5, 2)) < 1e-6 and math.dist(out[1].pts[-1], (25, 28)) < 1e-6
    assert max(math.dist(a, b) for a, b in zip(out[1].pts, out[1].pts[1:])) <= 4.0 + 1e-6


def test_sequence_blocks_keeps_dag_inside_a_stop_and_follows_the_needle():
    """inside one stop the next part is the one nearest the needle among those whose predecessors are sewn: 'far' is
    nearer to the end of 'a' than 'b' is, but 'far' lies on top of 'b' (touching, higher z) so it must wait.
    Mutation: DAG ignored inside the stop -> 'far' before 'b'."""
    rb = Rulebook()
    def part(id_, g, z):
        p = P(id_, g, "a", z); p.technique = "tatami"; p.stitch = rb.stitch_spec("pool", "tatami"); return p
    a = part("a", box(0, 0, 10, 10), 0); b = part("b", box(40, 0, 50, 10), 1); far = part("far", box(12, 0, 41, 10), 2)
    plan = ObjectPlan(name="t", parts=[a, b, far]); plan.stops = [dict(thread="a", parts=["a", "b", "far"])]
    from digitize import compile as CP
    CP.plan_blocks(plan)
    SQ.sequence_blocks(plan)
    assert plan.stops[0]["parts"] == ["a", "b", "far"], plan.stops
    assert SQ.report(plan)["dag_violations"] == 0


# ================================================================== threads: keep, mix, salience, the trade-off
PAL = {"navy": "#22355C", "slate": "#566577", "sky": "#3F6FA9", "mist": "#9EA3A6", "cream": "#D4CABA", "red": "#B23F2E"}
W8 = {"navy": 7000, "slate": 5000, "sky": 1200, "mist": 2200, "cream": 2100, "red": 30}


def test_keep_and_alternatives_put_the_tradeoff_in_the_report():
    """keep=[t] never absorbs t; alternatives() lists, per visible merge, the plan that keeps both tones and what it
    merges instead; plan_from_config applies threads.choice and refuses an unknown one; choice 'default' == the plain
    plan (default-preserving). Mutations: keep ignored -> the kept tone merges; alternatives keep one tone only -> the
    option just flips the merge (nothing 'lost' that the default kept)."""
    base = TH.plan(W8, PAL, needles=4, protected=["red"])
    m = max(base["merges"], key=lambda m: m["cost"])
    kept = TH.plan(W8, PAL, needles=4, protected=["red"], keep=[m["src"], m["dst"]])
    assert kept["map"][m["src"]] == m["src"] and kept["map"][m["dst"]] == m["dst"], kept["merges"]
    opts = TH.alternatives(W8, PAL, 4, ["red"], alt_min_dE=5.0)
    o = {x["id"]: x for x in opts}
    assert "default" in o and f"keep_{m['src']}" in o, list(o)
    alt = o[f"keep_{m['src']}"]
    assert alt["lost"] and all(m["src"] not in l.split(" -> ")[0] for l in alt["lost"]), alt
    assert set(alt["threads"]) >= {m["src"], m["dst"], "red"}
    T = dict(palette=PAL, protected=["red"])
    d = TH.plan_from_config(W8, dict(T), 4)
    assert {k: v for k, v in d.items() if k != "tradeoff"} == base
    c = TH.plan_from_config(W8, dict(T, choice=f"keep_{m['src']}"), 4)
    assert c["map"][m["src"]] == m["src"] and c["tradeoff"]["choice"] == f"keep_{m['src']}"
    with pytest.raises(TH.ThreadError): TH.plan_from_config(W8, dict(T, choice="nope"), 4)


def test_optical_mix_and_salience():
    """optical_mix finds the two kept threads whose open-layer mix reads closest (black + white -> the grey between,
    in linear RGB); protected accents are never offered as mixing threads; salience ranks a tone that stands out of its
    surroundings above one that blends into them. Mutations: mix in sRGB -> the grey lands off; protected offered;
    salience ignores contrast."""
    mx = TH.optical_mix("#BCBCBC", {"k": "#000000", "w": "#FFFFFF", "r": "#FF0000"})
    assert {mx["a"], mx["b"]} == {"k", "w"} and mx["ratio"] == 0.5 and mx["dE"] < 3.0, mx
    tp = TH.plan({"a": 100, "b": 100, "c": 5, "acc": 5}, {"a": "#FF0000", "b": "#0000FF", "c": "#00C000", "acc": "#00FF00"},
                 needles=3, protected=["acc"])                        # the green accent would be the best partner for c
    mixes = [m["mix"] for m in tp["merges"] if m.get("mix")]
    assert mixes and all("acc" not in (x["a"], x["b"]) for x in mixes), tp["merges"]
    pal = {"bg": "#808080", "near": "#868686", "pop": "#FFE000"}
    t = np.zeros((40, 40), int); t[5:10, 5:10] = 1; t[25:30, 25:30] = 2
    s = TH.salience(t, list(pal), pal, ppm=4.0)
    assert s["pop"]["x"] > s["near"]["x"] and s["pop"]["contrast"] > 3 * s["near"]["contrast"], s


# ================================================================== the review step: questions -> answers -> next run
def _review_plan():
    rb = Rulebook(); parts = []
    for i in range(3):
        g = box(i * 12, 0, i * 12 + 10, 10)
        p = Part(id=f"village.{i}", kind="zone_stub", geom=g, thread="a", z=5, zone="village", dir=DirSpec(30.0, source="field-mean"),
                 meta=dict(coherence=0.05 if i < 2 else 0.6))
        p.technique = "tatami"; p.stitch = rb.stitch_spec("zone_stub", "tatami"); parts.append(p)
    q = Part(id="ground.0", kind="zone_stub", geom=box(0, 20, 10, 30), thread="b", z=1, zone="ground", dir=DirSpec(10.0, source="field-mean"),
             meta=dict(coherence=0.6))
    parts.append(q)
    plan = ObjectPlan(name="t", parts=parts, threads={"a": dict(hex="#22355C", name="Navy", protected=False, absorbed=["c"]),
                                                       "b": dict(hex="#B23F2E", name="Red", protected=True, absorbed=[])})
    plan.meta["thread_tradeoff"] = dict(choice="default", options=[dict(id="default", label="as planned", merges=["c -> a (dE 9)"], worst_dE=9.0),
                                                                   dict(id="keep_c", label="keep c", merges=["d -> b (dE 12)"], worst_dE=12.0)])
    return plan


def test_review_round_trip_answers_override_defaults_and_report_the_rest():
    """questions have STABLE ids; answers.json overrides defaults in the next run (thread choice, a zone left out, an
    angle for the low-grain parts, sewn with source 'answer' and audited as derived); a missing answer keeps the default
    and is reported; an answer to an unknown question is reported; an answer outside the options raises.
    Mutations: answers ignored -> the angle stays 30; missing answers not reported; option check dropped."""
    plan = _review_plan()
    qs = RV.questions(plan, [])
    ids = [x["id"] for x in qs]
    assert ids == [x["id"] for x in RV.questions(_review_plan(), [])]          # stable across runs
    assert {"zone_stub:village", "zone_stub:ground", "direction:low_grain:village", "threads.accent:b", "threads.tradeoff"} <= set(ids), ids
    tq = next(x for x in qs if x["id"] == "threads.tradeoff")
    assert tq["options"] == ["default", "keep_c"] and tq["default"] == "default"
    ans = {"threads.tradeoff": "keep_c", "zone_stub:ground": "leave out", "direction:low_grain:village": "45 deg", "q999": "yes"}
    cfg, rep = RV.apply_answers({"threads": {"palette": {}}}, ans, qs)
    assert cfg["threads"]["choice"] == "keep_c"
    assert cfg["review"]["drop_zones"] == ["ground"] and cfg["review"]["angles"] == {"village.0": 45.0, "village.1": 45.0}
    assert rep["unknown"] == ["q999"]
    assert ("zone_stub:village", "accept stub") in rep["defaulted"] and ("threads.accent:b", "confirm") in rep["defaulted"], rep
    assert len(rep["answered"]) == 3
    # the next run: extract drops the zone, plan sews the answered angle (source answer, audited)
    parts, dropped = RV.apply_extract(cfg, plan.parts)
    assert dropped == ["ground.0"] and all(p.zone != "ground" for p in parts)
    plan.parts = parts; rb = Rulebook()
    out = RV.apply_plan(cfg, plan, rb)
    assert out["angles"] == ["village.0", "village.1"]
    v0 = plan.part("village.0")
    assert v0.dir.angle == 45.0 and v0.dir.source == "answer" and v0.meta["answer_angle"] == 45.0
    assert plan.part("village.2").dir.angle == 30.0                           # not asked about: unchanged
    assert audit.basis(v0, rb) == 45.0
    with pytest.raises(RV.AnswerError): RV.apply_answers({}, {"zone_stub:village": "burn it"}, qs)
    with pytest.raises(RV.AnswerError):
        c2, _ = RV.apply_answers({}, {"house-min:dot:x": "satin"}, [dict(id="house-min:dot:x", topic="house-min", part_ids=["village.0"],
                                                                        options=["keep", "satin"], default="keep")])
        RV.apply_plan(c2, _review_plan(), Rulebook(toggles={"satin": False}))   # an answer cannot enable a disabled technique


def test_answers_file_formats(tmp_path):
    p = tmp_path / "answers.json"
    p.write_text(json.dumps({"answers": {"a": "x"}})); assert RV.load_answers(str(p)) == {"a": "x"}
    p.write_text(json.dumps({"a": "y"})); assert RV.load_answers(str(p)) == {"a": "y"}


def test_foam_stop_never_merges_with_its_flat_colour_and_sews_after_touching_flat_work():
    """M6 puff contract: a '+foam' thread key is its own stop (the operator lays foam there): stop batching never merges
    it with the flat stop of the same colour, and every flat part TOUCHING a puff part sews before it, whatever the z
    (here the flat part is higher, so plain z order would sew it on top of the foam). Mutation: foam edges dropped ->
    the flat part sews after the foam."""
    foam = SQ.FOAM
    puff = P("puff", box(0, 0, 10, 10), "a" + foam, z=1)
    flat_on = P("flat_on", box(9, 0, 20, 10), "a", z=2)            # touches the puff, higher z
    flat_off = P("flat_off", box(50, 0, 60, 10), "a", z=0)         # elsewhere, same colour
    for la in (False, True):
        st = SQ.order_v1([puff, flat_on, flat_off], lookahead=la)
        assert all(not (SQ.is_foam(s["thread"]) and any(p != "puff" for p in s["parts"])) for s in st), st
        assert [s["thread"] for s in st].count("a" + foam) == 1
        order = [p for s in st for p in s["parts"]]
        assert order.index("flat_on") < order.index("puff"), st
