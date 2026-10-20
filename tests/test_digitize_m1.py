"""ENGINE_PLAN M1: the parts-based digitizing skeleton, plus the M0 review follow-ups. Each test was proven RED by a
mutation of the code it guards (recorded in RECAP-2026-10-19-engine-m1-skeleton.md) and is GREEN on this branch."""
import math, os, re
import numpy as np
import pytest
from shapely.geometry import box, LineString, Point
import qa

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ================================================================== M0 follow-ups (review of PR #3)
def _fill(ang_deg, x0, y0, x1, y1, spacing=0.4, stitch=3.0):
    segs = []; vertical = abs(ang_deg - 90) < 1
    lo, hi = (x0, x1) if vertical else (y0, y1); a0, a1 = (y0, y1) if vertical else (x0, x1)
    k = 0; t = lo + spacing / 2; prev = None
    while t < hi:
        xs = list(np.arange(a0, a1, stitch)) + [a1]
        if k % 2: xs = xs[::-1]
        pts = [((t, s) if vertical else (s, t)) for s in xs]
        if prev is not None: segs.append(prev + pts[0])
        segs += [pts[i] + pts[i + 1] for i in range(len(pts) - 1)]
        prev = pts[-1]; t += spacing; k += 1
    return segs


def test_stack_map_travel_line_is_not_a_layer():
    """a long thin travel line (its own run) across a fill adds ~1 mm/mm2 in the cells it crosses: below layer_min, so
    still ONE layer. Mutation layer_min=0.5 makes the line a layer (max 2) -> red."""
    fill = _fill(0, 0, 0, 30, 30)
    travel = [(1.0 + 7 * i * 0.97, 15.3, 1.0 + 7 * (i + 1) * 0.97, 15.3 + 0.2) for i in range(4)]   # 7 mm hidden-travel stitches
    r = qa.stack_map([fill, travel], (0, 0, 30, 30))
    assert r["max"] == 1, r["max"]
    # and a real second layer over the same cells still counts
    assert qa.stack_map([fill, _fill(90, 10, 10, 20, 20)], (0, 0, 30, 30))["max"] == 2


def _chain(pts): return [pts[i] + pts[i + 1] for i in range(len(pts) - 1)]


def test_satin_runs_rejects_bean_and_tight_zigzag():
    """a collinear bean (triple) run reverses every stitch and then goes on straight: never a column. A tight zig-zag
    turning ~100 deg (a decorative zig-zag run, stitches 0.6 mm) is not a satin either: satin rows reverse (> turn_deg
    120). Mutation turn_deg=90 turns the zig-zag into a 'satin' -> red. The bean is guarded twice (its forward stitches
    neither reverse nor stay within max_adv_mm): dropping BOTH the reversal test and the advance limit -> red."""
    pts = [(0.0, 0.0)]
    for k in range(1, 16):                                            # bean: a->b, b->a, a->b, then on to c
        a = (2.0 * (k - 1), 0.0); b = (2.0 * k, 0.0); pts += [b, a, b]
    assert qa.satin_runs(_chain(pts)) == []
    zz = [(0.0, 0.0)]; L = 0.6; up = math.radians(50)
    for k in range(40):                                               # +-50 deg about x: 100 deg turn at every point
        a = up if k % 2 == 0 else -up; x, y = zz[-1]; zz.append((x + L * math.cos(a), y + L * math.sin(a)))
    assert qa.satin_runs(_chain(zz)) == []
    zz_sharp = [(0.0, 0.0)]                                           # same walk at +-80 deg: 160 deg turns = a satin column
    for k in range(40):
        a = math.radians(80) if k % 2 == 0 else -math.radians(80); x, y = zz_sharp[-1]; zz_sharp.append((x + 2 * math.cos(a), y + 2 * math.sin(a)))
    assert len(qa.satin_runs(_chain(zz_sharp))) == 1


def test_satin_runs_rejects_mismatched_lengths():
    """reversing stitches 1.0 then 0.3 mm (a back-stitch run creeping along): every pair reverses (162 deg) and advances
    < 0.8 mm, but the lengths differ 3.3x > len_ratio 2.5: not a satin. Mutation len_ratio=4 -> red."""
    pts = [(0.0, 0.0)]
    for k in range(30):
        x, y = pts[-1]
        pts.append((x + 1.0, y + 0.0) if k % 2 == 0 else (x - 0.29, y + 0.05))
    assert qa.satin_runs(_chain(pts)) == []
    eq = [(0.0, 0.0)]                                                 # control: same walk with equal lengths is a column
    for k in range(30):
        x, y = eq[-1]; eq.append((x + 1.0, y + 0.2) if k % 2 == 0 else (x - 1.0, y + 0.2))
    assert len(qa.satin_runs(_chain(eq))) == 1


def test_angle_coherence_flags_part_without_visible_stitches():
    """a constructed part fully buried under a later fill shows < min_segs visible stitches: it cannot be checked, so it
    is flagged, never passed silently. Mutation (drop the flag) -> red."""
    walls = [dict(geom=box(0, 0, 20, 20), stype="tatami", angle=0.0, grp="WALL", part="big"),
             dict(geom=box(5, 5, 9, 9), stype="tatami", angle=90.0, grp="WALL", part="buried")]
    segs = _fill(90, 5, 5, 9, 9) + _fill(0, 0, 0, 20, 20)            # the small wall sews first, the big one covers it
    vis, idx = qa.visible_segments(segs, (0, 0, 20, 20), return_index=True)
    lab = (["buried"] * len(_fill(90, 5, 5, 9, 9)) + ["big"] * len(_fill(0, 0, 0, 20, 20)))
    bad = qa.angle_coherence(walls, segs=vis, seg_parts=[lab[i] for i in idx])
    assert [b for b in bad if b["kind"] == "no-visible-stitches" and b["part"] == "buried"], bad
    assert not [b for b in bad if b["part"] == "big"], bad


def test_angle_coherence_seg_parts_attributes_by_part_id():
    """wall A at 0 deg; wall B (90 deg) is sewn after it and keeps a 1 mm cut-under overlap ON TOP of A's edge.
    Measured by geometry, B's visible stitches inside A's outline make A's spread fail; attributed by part id, A is
    judged on its own stitches only and passes."""
    A = dict(geom=box(0, 0, 30, 20), stype="tatami", angle=0.0, grp="WALL", part="A")
    B = dict(geom=box(27, 0, 45, 20), stype="tatami", angle=90.0, grp="WALL", part="B")
    sa = _fill(0, 0, 0, 30, 20); sb = _fill(90, 27, 0, 45, 20)
    vis, idx = qa.visible_segments(sa + sb, (0, 0, 45, 20), return_index=True)
    lab = ["A"] * len(sa) + ["B"] * len(sb)
    by_geom = qa.angle_coherence([A, B], segs=vis)
    assert any(b["kind"] == "angle-spread" and b["part"] == "A" for b in by_geom), by_geom    # the problem
    by_part = qa.angle_coherence([A, B], segs=vis, seg_parts=[lab[i] for i in idx])
    assert by_part == [], by_part


def test_direction_match_masks_low_closeup_weight():
    """tiles whose reference pixels are only the upscaled mockup (close-up weight < 0.6) are masked, not judged.
    Mutation (ignore weight) -> the deviating left half counts again -> red."""
    ppm = 12.0; n = int(48 * ppm); y, x = np.mgrid[0:n, 0:n] / ppm
    ref = 128 + 100 * np.sin(2 * math.pi * y / 0.8)                   # threads along x
    segs = _fill(90, 1, 1, 24, 47) + _fill(0, 24, 1, 47, 47)          # left half wrong (90 deg), right half right
    w = np.ones((n, n)); w[:, :int(24 * ppm)] = 0.2                   # left half: no close-up there
    r0 = qa.direction_match(ref, ppm, segs)
    r1 = qa.direction_match(ref, ppm, segs, weight=w)
    assert r0["fail_dev"] and r0["pct_ok"] < 70, r0["pct_ok"]
    assert r1["masked"] >= 0.4 * r0["tiles"] and r1["pct_ok"] >= 90 and not r1["fail_dev"], (r1["masked"], r1["pct_ok"])


def test_reference_reports_source_detail():
    from digitize.extract import register
    cfg = register.load(os.path.join(ROOT, "projects", "castle-falls-jacket", "bench", "registration.json"))
    r = register.reference(cfg, "B", (-60, 450, -40, 470), ppm=12)
    assert r["closeup_weight"].shape == r["grey"].shape and r["closeup_weight"].min() > 0.6
    mock = 1 / math.sqrt(1.26 * 1.12)
    assert r["source_ppm"].shape == r["grey"].shape
    assert mock * 1.5 < r["source_ppm_median"] < 12, r["source_ppm_median"]    # real close-up detail, well under the 12 ppm grid


# ================================================================== M1 skeleton
from digitize.schema import Part, DirSpec, PlanError, ObjectPlan, Block
from digitize.rulebook import Rulebook, RulebookError
from digitize import techniques, sequence, threads


def _spec(tech):
    from digitize.schema import StitchSpec
    d = Rulebook().data["techniques"][tech]
    return StitchSpec(technique=tech, spacing=d.get("spacing", 0.45), stitch_len=d.get("stitch_len", 3.5), underlay=d.get("underlay", []),
                      pull_comp=d.get("pull_comp", 0.2), params={k: v for k, v in d.items() if k not in ("spacing", "stitch_len", "underlay", "pull_comp")})


def test_dirspec_never_auto():
    with pytest.raises(PlanError): DirSpec("auto")
    with pytest.raises(PlanError): DirSpec(None)
    with pytest.raises(PlanError): DirSpec(0.0, mode="auto")
    assert DirSpec(190.0).angle == 10.0


SYNTH = {"tatami": (box(0, 0, 30, 20), 30.0), "split_satin": (box(0, 0, 6, 40), 90.0), "satin": (box(0, 0, 3, 25), 0.0),
         "run": (box(0, 0, 0.6, 20), 0.0), "bean": (box(0, 0, 0.6, 20), 0.0),
         # M2 plugins: guided_fill needs its field (a constant 30 deg grid here), contour_fill / blend plan from the shape
         "guided_fill": (box(0, 0, 30, 20), 30.0), "contour_fill": (box(0, 0, 20, 14), 0.0), "blend": (box(0, 0, 30, 6), 0.0)}
SYNTH_META = {"guided_fill": dict(field=dict(x0=-2.0, y0=-2.0, step=1.0, nx=35, ny=25, deg=[30.0] * (35 * 25)), field_mean=30.0),
              "blend": dict(blend_from=[[-1.0, 0.0], [31.0, 0.0]])}
SYNTH.update({"column_satin": (box(0, 0, 2, 20), 0.0), "dot": (Point(5, 5).buffer(0.8), 30.0),       # M5 patch plugins
              "radial": (Point(5, 5).buffer(3.0), 0.0), "turning_satin": (box(0, 0, 3, 12), 0.0)})
# --- M6 --- specialty plugins (puff column, chenille moss + chain outline, chain / faux_chain lines)
SYNTH.update({"puff": (box(0, 0, 5, 25), 0.0), "chenille": (box(0, 0, 20, 14), 0.0), "chain": (box(0, 0, 0.6, 20), 0.0),
              "faux_chain": (box(0, 0, 0.6, 20), 0.0)})


def test_registry_contract():
    """every registered plugin plans a synthetic part: non-empty blocks, underlay before top, every needle point within
    1 mm of the part, every stitch <= 7 mm, check() returns a list, estimate() > 0"""
    names = techniques.names()
    assert set(names) >= {"tatami", "satin", "split_satin", "run", "bean"}, names
    for n in names:
        g, ang = SYNTH[n]; t = techniques.get(n)
        p = Part(id=f"syn.{n}", kind="pool", geom=g, thread="t1", z=0, dir=DirSpec(ang), meta=dict(SYNTH_META.get(n, {})))
        p.technique = n; p.stitch = _spec(n)
        bl = t.plan(p)
        assert bl and all(isinstance(b, Block) and b.part == p.id and len(b.pts) > 1 for b in bl), n
        roles = [b.role for b in bl]
        assert roles == sorted(roles, key=lambda r: r != "underlay") or n in ("tatami",), (n, roles)   # tatami: per piece
        assert "top" in roles, n
        G = g.buffer(1.0)
        for b in bl:
            assert all(G.contains(Point(q)) for q in b.pts), n
            assert max(math.dist(a, c) for a, c in zip(b.pts, b.pts[1:])) <= 7.0 + 1e-6, n
        assert isinstance(t.check(p, Rulebook().principles), list) and t.estimate(p) > 0 and t.stype in ("tatami", "satin", "run", "bean")


def _rows_by_y(pts, lo, hi):
    """interior penetrations (lo < x < hi) of each across-stitch, in sew order: a row ends at a side point"""
    rows = []; cur = []
    for x, y in pts:
        if lo < x < hi: cur.append(x)
        else:
            if cur: rows.append(cur)
            cur = []
    return rows


def _aligned(rows, tol=0.3):
    hit = tot = 0
    for r0, r1 in zip(rows, rows[1:]):
        for x in r0:
            tot += 1; hit += any(abs(x - x2) < tol for x2 in r1)
    return hit / max(tot, 1)


def test_split_satin_staggers():
    """a 12 mm wide column: dst2.turning_satin splits every row into equal pieces, so the split points line up row
    after row (a visible seam) - the RED reference; split_satin staggers them. Mutation PHASES=(0, 0, 0) -> red."""
    import dst2
    from digitize.techniques.split_satin import column_rows
    p = box(0, 0, 12, 40); cl = [(6.0, 0.0), (6.0, 40.0)]
    ref = dst2.turning_satin(p, LineString(cl), pull=0.0, short=False)
    ours = column_rows(cl, 12.0, 0.42)
    r_ref, r_ours = _rows_by_y(ref, 0.5, 11.5), _rows_by_y(ours, 0.5, 11.5)
    assert len(r_ref) > 50 and len(r_ours) > 50
    assert _aligned(r_ref) > 0.9, _aligned(r_ref)                    # dst2: aligned splits (the seam)
    assert _aligned(r_ours) < 0.1, _aligned(r_ours)                  # staggered
    assert max(math.dist(a, b) for a, b in zip(ours, ours[1:])) <= 7.0


def test_cut_under_keeps_1mm_overlap():
    lo = Part(id="lo", kind="pool", geom=box(0, 0, 20, 20), thread="a", z=0, dir=DirSpec(0))
    hi = Part(id="hi", kind="pool", geom=box(5, 5, 15, 15), thread="b", z=1, dir=DirSpec(0))
    sequence.cut_under([lo, hi], keep=1.0)
    ov = lo.geom.intersection(hi.geom).area
    assert abs(ov - (100 - 64)) < 0.5, ov                             # a 1 mm ring under the upper part's edge
    assert lo.geom.intersection(box(6.05, 6.05, 13.95, 13.95)).area < 1e-6
    assert abs(lo.geom.area - (400 - 64)) < 0.5 and hi.geom.area == 100   # the upper part is untouched


def test_underlap_then_cut_gives_exclusive_neighbours_1mm():
    a = Part(id="a", kind="pool", geom=box(0, 0, 10, 10), thread="a", z=0, dir=DirSpec(0))
    b = Part(id="b", kind="pool", geom=box(10, 0, 20, 10), thread="b", z=1, dir=DirSpec(0))
    sequence.underlap([a, b], 1.0); sequence.cut_under([a, b], 1.0)
    assert abs(a.geom.intersection(b.geom).area - 10.0) < 0.3 and b.geom.area == 100


def test_protected_tone_never_merged():
    """red is tiny and close to rose: the cheapest merge of all. Protected, it survives; every other tone merges down
    to the needle limit. Mutation (protected ignored) -> red merged away -> red."""
    pal = {"navy": "#22355C", "rose": "#B4506F", "red": "#B23F2E", "mist": "#9EA3A6", "slate": "#566577"}
    w = {"navy": 5000, "rose": 3000, "red": 20, "mist": 400, "slate": 900}
    tp = threads.plan(w, pal, needles=3, protected=["red"])
    assert len(tp["threads"]) == 3 and "red" in tp["threads"] and tp["map"]["red"] == "red", tp
    assert tp["threads"]["red"]["protected"] and not tp["threads"]["red"]["absorbed"]
    assert all(m["src"] != "red" and m["dst"] != "red" for m in tp["merges"]), tp["merges"]
    unprot = threads.plan(w, pal, needles=3, protected=[])
    assert unprot["map"]["red"] != "red"                              # the control: without protection it goes first
    with pytest.raises(threads.ThreadError): threads.plan(w, pal, needles=1, protected=["red", "navy"])


def test_disabled_only_technique_raises():
    rb = Rulebook(toggles={"tatami": False})
    with pytest.raises(RulebookError, match="disabled"): rb.technique_for("pool")
    assert Rulebook(toggles={"split_satin": False}).technique_for("fall_cord") == "tatami"   # first ENABLED wins
    assert Rulebook().technique_for("fall_cord") == "split_satin"
    with pytest.raises(RulebookError): Rulebook(toggles={"split_satin": False, "tatami": False}).technique_for("fall_cord")
    with pytest.raises(RulebookError): Rulebook().technique_for("no_such_kind")


def test_rulebook_matches_principles():
    """the founder numbers in rules/house.yaml equal docs/DIGITIZING_PRINCIPLES.md (read from the document, so editing
    either one alone turns this red)."""
    P = Rulebook().principles
    doc = open(os.path.join(ROOT, "docs", "DIGITIZING_PRINCIPLES.md")).read()
    m = re.search(r"Satin only on stroke-like parts (\d+)–(\d+) mm wide; split it above (\d+) mm", doc)
    assert (P["satin_min_w_mm"], P["satin_max_w_mm"]) == (float(m[1]), float(m[2])) and float(m[3]) == P["satin_max_w_mm"]
    assert P["fill_min_w_mm"] == float(re.search(r"Fill only where the part is ≥ ~(\d+) mm wide", doc)[1])
    assert P["run_max_w_mm"] == float(re.search(r"Run or bean below (\d+) mm", doc)[1])
    m = re.search(r"differ by ≥ (\d+)–(\d+)°", doc); assert P["neighbour_sep_deg"] == [int(m[1]), int(m[2])]
    assert P["cut_keep_mm"] == float(re.search(r"Remove overlaps, keeping ~(\d+) mm", doc)[1])
    assert P["max_stacked_layers"] == int(re.search(r"Never more than (\d+) stacked top layers", doc)[1])
    m = re.search(r"full jacket back is ~(\d+)–(\d+)k", doc); assert P["budget_back_stitches"] == [int(m[1]) * 1000, int(m[2]) * 1000]
    assert P["pull_comp_mm"] == float(re.search(r"~(\d+\.\d+) mm pull compensation on duck", doc)[1])
    assert P["text_min_mm"] == float(re.search(r"text ≥ (\d+) mm", doc)[1])
    m = re.search(r"studs (\d+(?:\.\d+)?)–(\d+(?:\.\d+)?) mm", doc); assert P["stud_mm"] == [float(m[1]), float(m[2])]
    assert P["satin_min_aspect"] == 2.5 and P["shading_underlay"] is False
    kinds = Rulebook().data["kinds"]
    assert kinds["sky_band"]["dir"] == 0 and kinds["pool"]["dir"] == 0 and kinds["fall_cord"]["dir"] == 90   # motif playbook
    assert kinds["sky_blend"]["underlay"] == []                                                            # rule 7


# ------------------------------------------------------------------ dst2 hooks
def _regions():
    sq = lambda x, y: [(x + i * 0.8, y + (j % 2) * 3.0) for j in range(6) for i in ([0, 1, 2] if j % 2 == 0 else [2, 1, 0])]
    pos = {"A": (0.0, 0.0), "B": (100.0, 0.0), "C": (10.0, 0.0)}
    regs = []
    for pid in ("A", "B", "C"):
        x, y = pos[pid]
        blk = [sq(x, y)]
        regs.append(dict(col="t1", geom=box(x - 0.5, y - 0.5, x + 2.5, y + 3.5), st="satin" if pid == "B" else "tatami", ang=0.0,
                         grp="pool", part=pid, blocks=blk))
    return regs


THREADS = {"t1": dict(hex="#B23F2E", description="test red", catalog="T1", brand="test")}


def _labelled(pat, labels):
    import pyembroidery as pe
    out = []; k = 0
    for x, y, c in pat.stitches:
        if c & pe.COMMAND_MASK == pe.STITCH:
            if labels[k] is not None: out.append((labels[k], round(x / 10, 1), round(y / 10, 1)))
            k += 1
    assert k == len(labels)
    return out


def test_make_pattern_prebuilt_emits_exactly_the_planned_blocks():
    import dst2
    regs = _regions()
    pat, st = dst2.make_pattern(regs, [dict(col="t1", regions=regs)], (0.0, 0.0), builder=lambda r, e: r["blocks"], keep_order=True,
                                threads=THREADS)
    got = _labelled(pat, st["labels"])
    want = [(r["part"], round(x, 1), round(y, 1)) for r in regs for b in r["blocks"] for x, y in b]
    assert got == want
    assert pat.threadlist[0].hex_color().lower() == "#b23f2e" and pat.threadlist[0].description == "test red"


def test_keep_order_preserves_rank():
    import dst2
    regs = _regions()
    order = lambda **kw: [p for p, _, _ in _labelled(*_mp(dst2, regs, **kw))]
    seq = lambda o: [p for i, p in enumerate(o) if i == 0 or o[i - 1] != p]
    assert seq(order(keep_order=True)) == ["A", "B", "C"]
    assert seq(order(keep_order=False)) == ["A", "C", "B"]           # the default sorts tatami before satin, nearest-first


def _mp(dst2, regs, **kw):
    pat, st = dst2.make_pattern(regs, [dict(col="t1", regions=regs)], (0.0, 0.0), builder=lambda r, e: r["blocks"], threads=THREADS, **kw)
    return pat, st["labels"]


def test_plan_json_roundtrip(tmp_path):
    p = Part(id="x.001", kind="pool", geom=box(0, 0, 5, 5), thread="t1", z=3.5, dir=DirSpec(0.0), zone="pool")
    p.technique = "tatami"; p.stitch = _spec("tatami")
    plan = ObjectPlan(name="t", parts=[p], threads={"t1": dict(hex="#000000")}, stops=[dict(thread="t1", parts=["x.001"])])
    techniques  # noqa
    from digitize import compile as CP
    CP.plan_blocks(plan); f = plan.to_json(str(tmp_path / "plan.json"))
    q = ObjectPlan.from_json(f)
    assert q.parts[0].dir.angle == 0.0 and q.parts[0].stitch.spacing == p.stitch.spacing and abs(q.parts[0].area - 25) < 1e-6
    assert len(q.blocks["x.001"]) == len(plan.blocks["x.001"])


def test_config_json_fallback(tmp_path, monkeypatch):
    from digitize import config
    f = tmp_path / "run.json"; f.write_text('{"name": "x", "techniques": {"satin": false}}')
    import builtins
    real = builtins.__import__
    def no_yaml(name, *a, **k):
        if name == "yaml": raise ImportError("no yaml")
        return real(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", no_yaml)
    cfg = config.load(str(f))
    assert cfg["techniques"]["satin"] is False and cfg["techniques"]["tatami"] is True
    g = tmp_path / "run.yaml"; g.write_text("name: x\n")
    with pytest.raises(SystemExit, match="PyYAML"): config.load(str(g))


def test_short_rows_never_sew_as_satin_blobs():
    """rows shorter than one stitch are ONE stitch each; a run of them reverses like a satin and read back as 31 blob
    satins on the first crop run (tatami stub parts, fall-cord ends). Tatami and fixed split satin give every such row a
    staggered penetration. Mutation (split_short / min_pieces off) -> red."""
    def segs(bl): return [tuple(a) + tuple(b) for blk in bl for a, b in zip(blk.pts, blk.pts[1:]) if tuple(a) != tuple(b)]
    for n, g, ang in (("tatami", box(0, 0, 3.0, 3.2), 0.0), ("tatami", box(0, 0, 1.0, 6.0), 0.0), ("split_satin", box(0, 0, 5.0, 3.0), 90.0)):
        p = Part(id="s", kind="pool", geom=g, thread="t1", z=0, dir=DirSpec(ang)); p.technique = n; p.stitch = _spec(n)
        top = [b for b in techniques.get(n).plan(p) if b.role == "top"]
        r = qa.satin_shape(segs(top))
        assert r["counts"]["blob"] == 0 and r["satins"] == 0, (n, r["counts"])
