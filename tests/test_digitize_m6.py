"""ENGINE_PLAN M6: puff, chenille and chain technique plugins. Swatch-level (synthetic shapes); puff and faux chain are
judged on the WRITTEN DST (compile.write + labelled_dst), chenille / true chain on their plan (no machine file until the
factory gives the format, F1). Every gate has a red case here: the broken plan the gate exists to catch."""
import json, math, os, tempfile
import pytest
from shapely.geometry import LineString, Point, box
from digitize import compile as CP, sequence as SQ, techniques, config
from digitize.schema import ObjectPlan, Part, DirSpec
from digitize.rulebook import Rulebook, RulebookError
from digitize.techniques import specialty as SP, puff as PF, chenille as CH, chain as CN
from digitize import swatch_m6 as SW

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOG = config.DEFAULTS["techniques"]


def _puff(pid="puff.s", cl=((12.0, 18.0), (48.0, 18.0)), w=5.0, closed=False, thread="cream", **meta):
    m = dict(cl=[list(c) for c in cl], w=w, closed=closed); m.update(meta)
    return Part(id=pid, kind="puff_column", geom=SW.column_geom(list(cl), w, closed), thread=thread, z=2, dir=DirSpec(90.0), meta=m)


def _compile(parts, rb=None, technique=None, isolate=True, spec=None):
    """plan + compile + read the file back: (plan, {part id: file segments})"""
    rb = rb or Rulebook(toggles=TOG)
    for p in parts:
        p.technique = (technique or {}).get(p.id) or rb.technique_for(p.kind)
        p.stitch = rb.stitch_spec(p.kind, p.technique)
        for k, v in (spec or {}).get(p.id, {}).items(): setattr(p.stitch, k, v) if hasattr(p.stitch, k) and k != "params" else p.stitch.params.update(v)
    plan = ObjectPlan(name="t", parts=parts, threads={k: dict(v) for k, v in SW.THREADS.items()})
    if isolate: SP.isolate_foam(plan)
    plan.stops = SQ.order(plan.parts); CP.plan_blocks(plan)
    base = os.path.join(tempfile.mkdtemp(), "m6")
    w = CP.write(plan, base, SW.ORIGIN)
    D, lab, _ = CP.labelled_dst(base + ".dst", SW.ORIGIN, w["segs"], w["seg_parts"])
    by = {}
    for s, l in zip(D, lab):
        if l is not None: by.setdefault(l, []).append(s)
    return plan, by, w


def _bad(G): return sorted(k for k, v in G.items() if not v["ok"])


# ------------------------------------------------------------------ toggles
def test_toggles_choose_chain_and_none_enabled_raises():
    assert Rulebook(toggles=TOG).technique_for("chain_line") == "faux_chain"          # default: no chenille format -> Brother
    assert Rulebook(toggles=dict(TOG, chain=True)).technique_for("chain_line") == "chain"
    with pytest.raises(RulebookError, match="disabled"): Rulebook(toggles=dict(TOG, chain=False, faux_chain=False)).technique_for("chain_line")
    with pytest.raises(RulebookError, match="disabled"): Rulebook(toggles=dict(TOG, puff=False)).technique_for("puff_column")
    with pytest.raises(RulebookError, match="disabled"): Rulebook(toggles=dict(TOG, chenille=False)).technique_for("chenille_fill")
    assert Rulebook().rule("puff_column")["techniques"] == ["puff"]                   # never a tatami fallback for foam


# ------------------------------------------------------------------ puff
def test_puff_swatch_passes_every_gate_on_the_file():
    parts = [Part(id="base", kind="pool", geom=box(5, 5, 55, 32), thread="navy", z=0, dir=DirSpec(0.0)), _puff(),
             _puff("puff.arc", [(10 + i, 48 - 9 * math.sin(math.pi * i / 40)) for i in range(41)], 6.0),
             _puff("puff.ring", [(85 + 9 * math.cos(2 * math.pi * i / 72), 20 + 9 * math.sin(2 * math.pi * i / 72)) for i in range(72)], 4.0, True)]
    plan, by, w = _compile(parts)
    assert _bad(SP.plan_gates(plan)) == []
    for pid in ("puff.s", "puff.arc", "puff.ring"):
        G = SP.puff_gates(plan.part(pid), by[pid])
        assert _bad(G) == [], (pid, {k: v["value"] for k, v in G.items()})
        assert G["density"]["value"] <= 0.30 and G["satin_only"]["value"] == 0.0
    ends = SP.puff_gates(plan.part("puff.s"), by["puff.s"])["ends_closed"]["value"]
    assert len(ends) == 2 and all(e["perforated"] and e["capped"] for e in ends)
    assert SP.puff_gates(plan.part("puff.ring"), by["puff.ring"])["ends_closed"]["value"] == []      # a ring has no ends


def test_puff_gate_red_on_tatami():
    """the same column sewn as tatami: penetrations inside the foam body + the plan gate names the part"""
    plan, by, _ = _compile([_puff()], technique={"puff.s": "tatami"}, isolate=False)
    G = SP.puff_gates(plan.part("puff.s"), by["puff.s"])
    assert "satin_only" in _bad(G) and G["satin_only"]["value"] > 0.3
    assert "puff_no_fill" in _bad(SP.plan_gates(plan))


def test_puff_gate_red_on_flat_density():
    plan, by, _ = _compile([_puff()], spec={"puff.s": dict(spacing=0.42)})
    G = SP.puff_gates(plan.part("puff.s"), by["puff.s"])
    assert _bad(G) == ["density"] and G["density"]["value"] > 0.4


def test_puff_gate_red_on_open_ends(monkeypatch):
    """mutations: no cap / no perforation -> ends_closed red (each alone)"""
    monkeypatch.setattr(PF, "cap", lambda *a, **k: [])
    plan, by, _ = _compile([_puff()])
    G = SP.puff_gates(plan.part("puff.s"), by["puff.s"])
    assert _bad(G) == ["ends_closed"] and not any(e["capped"] for e in G["ends_closed"]["value"])
    monkeypatch.undo()
    monkeypatch.setattr(PF, "perforation", lambda *a, **k: [])
    plan, by, _ = _compile([_puff()])
    G = SP.puff_gates(plan.part("puff.s"), by["puff.s"])
    assert _bad(G) == ["ends_closed"] and not any(e["perforated"] for e in G["ends_closed"]["value"])


def test_puff_underlay_over_foam_red_tack_green():
    """a tack (edge run on the cut line) is allowed; a centre-run underlay across the foam is not"""
    plan, by, _ = _compile([_puff()], spec={"puff.s": dict(underlay=["tack"])})
    assert _bad(SP.puff_gates(plan.part("puff.s"), by["puff.s"])) == []
    orig = PF.Puff.plan
    def with_centre_run(self, part):
        from digitize.schema import Block
        import dst2
        return [Block(part.id, "underlay", dst2.path_resample(part.meta["cl"], 2.0))] + orig(self, part)
    PF.Puff.plan = with_centre_run
    try:
        plan, by, _ = _compile([_puff()])
    finally:
        PF.Puff.plan = orig
    assert "satin_only" in _bad(SP.puff_gates(plan.part("puff.s"), by["puff.s"]))


def test_puff_width_and_foam_limits():
    narrow = _puff(w=2.5); rb = Rulebook(toggles=TOG)
    plan, by, _ = _compile([narrow])
    G = SP.puff_gates(plan.part("puff.s"), by["puff.s"])
    assert "width_in_range" in _bad(G)
    assert any("over-compresses" in i["text"] for i in techniques.get("puff").check(plan.part("puff.s"), rb.principles))
    thick = _puff(foam=dict(thickness_mm=6.0, colour="cream"))
    plan, by, _ = _compile([thick])
    assert _bad(SP.puff_gates(plan.part("puff.s"), by["puff.s"])) == ["foam_spec"]


def test_puff_width_cap_is_the_house_stitch_cap():
    """7 mm column: one stitch per row across the foam, green. 9 mm: dst2 splits every row at > 7.4 mm (LESSONS B17),
    which perforates the foam mid-column - the file gate sees the split points (satin_only) and width_in_range is red"""
    plan, by, w = _compile([_puff(w=7.0)])
    G = SP.puff_gates(plan.part("puff.s"), by["puff.s"])
    assert _bad(G) == [] and 7.0 <= G["row_len"]["value"] <= PF.ROW_MAX and G["satin_only"]["value"] == 0.0
    plan, by, w = _compile([_puff(w=9.0)])
    G = SP.puff_gates(plan.part("puff.s"), by["puff.s"])
    assert {"width_in_range", "satin_only"} <= set(_bad(G)) and G["satin_only"]["value"] > 0.3


def test_foam_stop_gate():
    """puff in the same thread as the flat base: without isolate_foam they share a stop (no machine stop to lay the
    foam) -> red; isolate_foam gives the puff its own stop after the base -> green"""
    base = lambda: Part(id="base", kind="pool", geom=box(5, 5, 55, 32), thread="cream", z=0, dir=DirSpec(0.0))
    plan, _, _ = _compile([base(), _puff()], isolate=False)
    assert "foam_stop" in _bad(SP.plan_gates(plan))
    plan, _, w = _compile([base(), _puff()], isolate=True)
    assert _bad(SP.plan_gates(plan)) == [] and w["readback"]["stops"] == 2
    far = Part(id="far", kind="pool", geom=box(70, 60, 90, 75), thread="cream", z=0, dir=DirSpec(0.0))   # does not touch the puff
    plan, _, _ = _compile([far, _puff()], isolate=False)
    G = SP.plan_gates(plan)["foam_stop"]
    assert not G["ok"] and G["value"]["mixed_stops"] and not G["value"]["flat_after_puff"]          # mixed stop alone is red


# ------------------------------------------------------------------ faux chain (Brother)
def _wave(y=46.0):
    pts = [(62 + 0.5 * i, y + 3 * math.sin(i / 6.0)) for i in range(101)]
    return Part(id="chain.l", kind="chain_line", geom=LineString(pts).buffer(0.3), thread="red", z=1,
                dir=DirSpec(0.0, mode="contour", source="outline"), meta=dict(line=[list(c) for c in pts]))


def test_faux_chain_reads_as_chain_on_the_file():
    plan, by, _ = _compile([_wave()])
    assert plan.part("chain.l").technique == "faux_chain"
    G = SP.faux_chain_gates(plan.part("chain.l"), by["chain.l"])
    assert _bad(G) == [], {k: v["value"] for k, v in G.items()}


def test_faux_chain_gate_red_on_run_and_bean():
    for t in ("run", "bean"):
        p = _wave(); plan, by, _ = _compile([p], technique={"chain.l": t})
        q = plan.part("chain.l"); q.stitch = Rulebook().stitch_spec("chain_line", "faux_chain")       # judge by the chain's numbers
        G = SP.faux_chain_gates(q, by["chain.l"])
        assert "reads_as_chain" in _bad(G) and G["reads_as_chain"]["value"] < 0.2, (t, G["reads_as_chain"])


# ------------------------------------------------------------------ chenille / true chain (chenille head, plan only)
def _blob():
    rb = Rulebook(toggles=TOG); p = SW.head_parts()[0]
    p.technique = rb.technique_for(p.kind); p.stitch = rb.stitch_spec(p.kind, p.technique); return p


def test_chenille_plan_gates_green():
    p = _blob(); d = CH.detail(p); G = SP.chenille_gates(p, d)
    assert _bad(G) == [], {k: v["value"] for k, v in G.items()}
    assert len(d["chain"]) == 2                                   # outline + the hole
    for poly in d["moss"]:                                        # moss never crosses the hole
        assert not LineString(poly).intersects(Point(31, 67).buffer(2.0))


def test_chenille_zigzag_mode_green():
    p = _blob(); p.stitch.params["mode"] = "zigzag"
    assert _bad(SP.chenille_gates(p, CH.detail(p))) == []


def test_chenille_gates_red(monkeypatch):
    p = _blob(); d = CH.detail(p)
    # arc-length resample (short chords on curves = uneven loops)
    def arc(pts, L, closed=False):
        ls = LineString(list(pts) + ([pts[0]] if closed else [])); n = max(1, int(ls.length // L))
        return [ls.interpolate(i * L).coords[0] for i in range(n + 1)]
    from digitize.techniques import polys
    raw = [pp for q in polys(p.geom.buffer(-(0.8 + 2.0))) for pp in CH.spiral_paths(q, 2.0)]
    d2 = dict(d, moss=[arc(q, 2.5) for q in raw])                      # moss only, from the raw spirals; chain stays chord-resampled
    G = SP.chenille_gates(p, d2)
    assert "const_stitch_len" in _bad(G) and G["const_stitch_len"]["value"]["moss"] > 0.10
    d3 = dict(d, moss=d["moss"][::2])                              # every other path missing: bare patches
    assert "moss_coverage" in _bad(SP.chenille_gates(p, d3))
    d4 = dict(d, moss=d["moss"] + [[(x + 0.3, y) for x, y in q] for q in d["moss"]])    # paths sewn twice: pile-up
    assert "moss_no_pileup" in _bad(SP.chenille_gates(p, d4))
    d5 = dict(d, chain=d["chain"][:1])                             # the hole has no chain
    assert "chain_outline" in _bad(SP.chenille_gates(p, d5))
    p.stitch.params["loop_height_mm"] = None
    assert "head_settings" in _bad(SP.chenille_gates(p, CH.detail(p)))


def test_true_chain_plan_gates():
    p = _wave(); rb = Rulebook(toggles=dict(TOG, chain=True))
    p.technique = rb.technique_for(p.kind); p.stitch = rb.stitch_spec(p.kind, p.technique)
    assert p.technique == "chain"
    d = techniques.get("chain").detail(p)
    assert _bad(SP.chain_gates(p, d)) == []
    zz = [(i * 3.0, (i % 2) * 3.0) for i in range(12)]                # sharp turns: an arc-length resample cuts the corners
    q = Part(id="z", kind="chain_line", geom=LineString(zz).buffer(0.3), thread="red", z=1, dir=DirSpec(0.0, mode="contour", source="outline"),
             meta=dict(line=[list(c) for c in zz])); q.technique, q.stitch = p.technique, p.stitch
    assert _bad(SP.chain_gates(q, techniques.get("chain").detail(q))) == []
    ls = LineString(zz); n = int(ls.length // 2.0)
    d2 = dict(chain=[[ls.interpolate(i * 2.0).coords[0] for i in range(n + 1)]], moss=[], spec=d["spec"])
    assert "const_stitch_len" in _bad(SP.chain_gates(q, d2))


def test_chenille_export_needs_the_factory_format():
    p = _blob(); items = [(p, CH.detail(p))]
    with pytest.raises(SP.FactoryFormatNeeded, match=r"F1\).*TMCE"): SP.export_chenille(items, "/nonexistent/x", prof=dict(chenille=True))
    with pytest.raises(SP.FactoryFormatNeeded, match="no writer"): SP.export_chenille(items, "/nonexistent/x", prof=dict(chenille=True, chenille_format="tajima-tcf"))
    assert json.load(open(os.path.join(ROOT, "factory.json"))).get("chenille_format") is None      # repo: still open
    f = SP.write_chenille_plan(items, os.path.join(tempfile.mkdtemp(), "c.json"))
    J = json.load(open(f)); assert J["parts"][0]["moss"] and J["parts"][0]["spec"]["loop_height_mm"] == 4.0


def test_chenille_part_never_enters_a_lockstitch_file():
    p = _blob(); plan = ObjectPlan(name="t", parts=[p], threads={"moss": SW.THREADS["moss"]})
    plan.stops = SQ.order(plan.parts); CP.plan_blocks(plan)
    with pytest.raises(SP.OtherMachine, match="chenille head"): CP.write(plan, os.path.join(tempfile.mkdtemp(), "x"), SW.ORIGIN)
    q = _wave(); rb = Rulebook(toggles=dict(TOG, chain=True)); q.technique = "chain"; q.stitch = rb.stitch_spec("chain_line", "chain")
    plan = ObjectPlan(name="t", parts=[q], threads={"red": SW.THREADS["red"]}); plan.stops = SQ.order(plan.parts); CP.plan_blocks(plan)
    with pytest.raises(SP.OtherMachine): CP.write(plan, os.path.join(tempfile.mkdtemp(), "x"), SW.ORIGIN)


def test_factory_page_asks_chenille_format():
    import factory
    SO = [dict(file="a.dst", piece="back", stitches=1000, trims=3)]
    svg = factory.requests_page("T", SO, [], [], prof=dict(factory.load(), chenille=True, chenille_format=None))[0]
    assert "Chenille machine + file format" in svg and "TMCE" in svg
    svg = factory.requests_page("T", SO, [], [], prof=dict(factory.load(), chenille=True, chenille_format="x"))[0]
    assert "Chenille machine" not in svg


# ------------------------------------------------------------------ the swatch run (previews)
def test_swatch_run_all_gates_and_previews(tmp_path):
    cfg = config.load(os.path.join(ROOT, "engine", "digitize", "swatches", "m6.yaml"))
    r = SW.build(cfg, str(tmp_path))
    assert r["chain_line_technique"] == "faux_chain" and all(r["verdict"].values()), [k for k, v in r["verdict"].items() if not v]
    assert r["chenille_export"].startswith("FactoryFormatNeeded")
    for k, f in r["png"].items(): assert os.path.getsize(f) > 3000, k
