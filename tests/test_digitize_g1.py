"""ENGINE_PLAN G1: the labels contract, the generic primitive recognisers, the labels -> Parts compiler, and the
dst2 / compile block-join guard (LESSONS B39). Every guard here was proven red first (RECAP-2026-10-20-engine-g1.md)."""
import json, math, os
import numpy as np
import pytest
from shapely.geometry import LineString, box, Point

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ------------------------------------------------------------------ B39: a part's blocks never joined over its own rows
def _rows(x0, x1, y0, y1, sp=0.4, start_left=True):
    """horizontal tatami-like rows (boustrophedon), one stitch per row end"""
    pts = []; y = y0; k = 0 if start_left else 1
    while y <= y1 + 1e-9:
        pts += [(x0, y), (x1, y)] if k % 2 == 0 else [(x1, y), (x0, y)]
        y += sp; k += 1
    return pts


def _travel_over(pat_stats, pat, origin, footprint, planned, ex=0.4):  # ex=0.0: any overlap
    """sewn segments that are NOT one of the planned block segments (travel / hops between blocks) lying on
    `footprint` for more than ex mm. A hop is labelled with the stitch it ends on, so labels cannot tell it apart: the
    planned segments (consecutive points inside one block, 0.1 mm grid) can."""
    import pyembroidery as pe
    ox, oy = origin; prev = None; bad = []
    key = lambda a, b: (round(a[0], 1), round(a[1], 1), round(b[0], 1), round(b[1], 1))
    plan = {key(a, b) for bl in planned for a, b in zip(bl, bl[1:])} | {key(b, a) for bl in planned for a, b in zip(bl, bl[1:])}
    for x, y, c in pat.stitches:
        cmd = c & pe.COMMAND_MASK
        if cmd == pe.STITCH:
            q = (x / 10.0 + ox, y / 10.0 + oy)
            if prev is not None and math.dist(prev, q) > 0.3 and key(prev, q) not in plan:
                ln = LineString([prev, q])
                if ln.length > 1.0:                              # the hop starts on the row it leaves: 0.5 mm each end forgiven
                    from shapely.ops import substring
                    ln = substring(ln, 0.5, ln.length - 0.5)
                L = ln.intersection(footprint).length
                if L > ex or (ex == 0.0 and L > 0): bad.append((prev, q, round(L, 2)))
            prev = q
        else: prev = None
    return bad


def _interiors(bl, half=0.2, row_end=0.6):
    """the B39 footprint of sewn rows: each stitch's INTERIOR (row_end mm off both ends), buffered half"""
    from shapely.ops import substring, unary_union
    gs = [substring(LineString([p, q]), row_end, math.dist(p, q) - row_end).buffer(half) for p, q in zip(bl, bl[1:]) if math.dist(p, q) > 2 * row_end + 0.1]
    return unary_union(gs)


def _two_block_region(b2_start_left=True, b1_rows=(0.2, 3.8), b2=(6.5, 11.5)):
    import dst2
    g = box(0, 0, 12, 4)
    b1 = _rows(0.5, 5.5, *b1_rows)                         # 10 rows -> ends on the LEFT side at the top (0.5, 3.8)
    b2p = _rows(b2[0], b2[1], 0.2, 3.8, start_left=b2_start_left)
    r = dict(col="#336699", geom=g, st="tatami", ang=0.0, grp="t", part="P1", blocks=[b1, b2p], block_roles=["top", "top"], join_guard="all")
    return g, b1, b2p, r


def test_block_join_parallel_hop_over_own_rows_is_never_sewn():
    """B39 as seen on the crop (default mode "parallel"): the hop from block 1's end runs ALONG the rows (4 deg off),
    over block 1's sewn rows, to block 2 beside it: sewn, it is one more row among the rows and the run reads as satin."""
    import dst2
    from digitize import compile as CP
    g = box(0, 0, 12, 4)
    b1 = _rows(0.5, 5.5, 0.2, 3.8)                                    # ends at (0.5, 3.8)
    b2p = list(reversed(_rows(6.5, 11.5, 0.2, 3.4)))                  # starts at the top right of block 2: (6.5 or 11.5, 3.4)
    if b2p[0][0] > 9: b2p = [(6.5 + 11.5 - x, y) for x, y in b2p]      # make it start at (6.5, 3.4)
    r = dict(col="#336699", geom=g, st="tatami", ang=0.0, grp="t", part="P1", blocks=[b1, b2p], block_roles=["top", "top"])
    pat, st = dst2.make_pattern([r], [dict(col=r["col"], regions=[r])], (6.0, 2.0), builder=CP.prebuilt, keep_order=True)
    long_ = [h for h in _travel_over(st, pat, (6.0, 2.0), _interiors(b1), r["blocks"], ex=0.0) if math.dist(h[0], h[1]) > 1.6]
    assert long_ == []                                         # no long stitch along the rows: a short run hides in them
    assert st.get("join_runs", 0) == 1 and st["trims"] == 0


def test_block_join_parallel_mode_leaves_a_crossing_hop_to_the_travel_gate():
    """mode "parallel" judges only hops along the rows; a hop ACROSS them (31 deg here) is a travel line for the M4s
    travel-on-fill gate (strict mode "all" trims it: the next test). Measured on the crop: strict 156 -> 722 trims."""
    import dst2
    from digitize import compile as CP
    g, b1, b2p, r = _two_block_region(); r["join_guard"] = "parallel"
    pat, st = dst2.make_pattern([r], [dict(col=r["col"], regions=[r])], (6.0, 2.0), builder=CP.prebuilt, keep_order=True)
    assert st.get("join_trims", 0) + st.get("join_routes", 0) + st.get("join_runs", 0) == 0


def test_block_join_never_sews_over_the_parts_own_rows():
    """B39: two TOP blocks of one part; the hop from the first block's end to the second's start runs diagonally across
    the first block's sewn rows (inside the part, so the old router sewed it as a 7 mm travel stitch on top: a zig-zag
    that reads back as satin). It must be a trim (or a travel that stays off the visible rows)."""
    import dst2
    from digitize import compile as CP
    g, b1, b2p, r = _two_block_region()
    stops = [dict(col=r["col"], regions=[r])]
    pat, st = dst2.make_pattern([r], stops, (6.0, 2.0), builder=CP.prebuilt, keep_order=True)
    foot = _interiors(b1)
    assert _travel_over(st, pat, (6.0, 2.0), foot, r["blocks"]) == []


def test_block_join_routes_round_the_sewn_rows_through_the_unsewn_part():
    """the guard first looks for a hidden path through what is still UNSEWN of the part (here a corridor above the first
    block, sewn later by a third block): no trim, and still nothing sewn over the first block's rows (PR review: a trim
    per guarded hop cost the crop 156 -> 1,445 trims)"""
    import dst2
    from digitize import compile as CP
    g = box(0, 0, 12, 7)
    b1 = _rows(0.5, 5.5, 0.2, 3.8)                         # ends at (0.5, 3.8)
    b2p = _rows(6.5, 11.5, 0.2, 3.8)                       # starts at (6.5, 0.2)
    b3 = _rows(0.5, 11.5, 4.6, 6.6)                        # the corridor y 4.2..6.8, sewn last
    r = dict(col="#336699", geom=g, st="tatami", ang=0.0, grp="t", part="P1", blocks=[b1, b2p, b3], block_roles=["top"] * 3, join_guard="all")
    pat, st = dst2.make_pattern([r], [dict(col=r["col"], regions=[r])], (6.0, 3.5), builder=CP.prebuilt, keep_order=True)
    assert _travel_over(st, pat, (6.0, 3.5), _interiors(b1), r["blocks"]) == []
    assert st.get("join_routes", 0) >= 1 and st["trims"] == 0


def test_block_join_guard_keeps_a_hop_over_unsewn_rows():
    """the guard only refuses hops over rows ALREADY sewn: a hop that runs over the second block's (not yet sewn) area
    stays a hidden travel (no extra trim)"""
    import dst2
    from digitize import compile as CP
    g = box(0, 0, 12, 4)
    b1 = _rows(0.5, 5.5, 0.2, 3.6)                          # 9 rows -> ends on the RIGHT at (5.5, 3.4)
    b2p = _rows(6.5, 11.5, 0.2, 3.8, start_left=False)     # starts at (11.5, 0.2): the hop crosses block 2's own area
    r = dict(col="#336699", geom=g, st="tatami", ang=0.0, grp="t", part="P1", blocks=[b1, b2p], block_roles=["top", "top"])
    pat, st = dst2.make_pattern([r], [dict(col=r["col"], regions=[r])], (6.0, 2.0), builder=CP.prebuilt, keep_order=True)
    assert st["trims"] == 0


def test_block_join_guard_is_off_without_block_roles():
    """default preservation: regions without block_roles (every caller before G1, dst2's own builder) route as before"""
    import dst2
    from digitize import compile as CP
    g, b1, b2p, r = _two_block_region()
    r.pop("block_roles")
    pat, st = dst2.make_pattern([r], [dict(col=r["col"], regions=[r])], (6.0, 2.0), builder=CP.prebuilt, keep_order=True)
    assert _travel_over(st, pat, (6.0, 2.0), _interiors(b1), r["blocks"]) != []      # the old behaviour, unchanged


def test_compile_regions_carry_block_roles():
    from digitize import compile as CP
    from digitize.schema import ObjectPlan, Part, DirSpec, Block
    p = Part(id="a", kind="plane", geom=box(0, 0, 5, 5), thread="t", z=1, dir=DirSpec(0.0), technique="tatami")
    plan = ObjectPlan(name="x", parts=[p], stops=[dict(thread="t", parts=["a"])],
                      blocks={"a": [Block("a", "underlay", [(0, 0), (1, 1)]), Block("a", "top", [(0, 0), (5, 0)])]})
    regs = CP.regions(plan)
    assert regs[0]["regions"][0]["block_roles"] == ["underlay", "top"] and regs[0]["regions"][0]["join_guard"] == "parallel"


# ------------------------------------------------------------------ the labels contract
PAL = {"navy": "#22355C", "white": "#EEEAE0", "pink": "#DE8EA6", "rose": "#B4506F", "gold": "#D3A63F", "grn": "#5A7240"}


def _labels(**part):
    p = dict(id="a", primitive="plane", z=1, confidence=0.9, direction={"intent": "angle", "angle": 30},
             hint={"polygons": [[[0, 0], [10, 0], [10, 10]]]}, tones=["navy"])
    p.update(part)
    return {"schema": "techpack.labels/1", "motifs": [{"id": "m", "parts": [p]}]}


@pytest.mark.parametrize("bad, why", [
    (dict(direction={"intent": "auto"}), "never 'auto'"),
    (dict(primitive="cord", direction={"intent": "angle", "angle": 0}), "takes direction"),
    (dict(direction={"intent": "angle"}), "needs a number"),
    (dict(confidence=1.5), "confidence"),
    (dict(hint={}), "hint.polygons"),
    (dict(tones=["teal"]), "not in the run palette"),
    (dict(primitive="blob"), "not in"),
    (dict(hint={"polygons": [[[0, 0], [1, 1]]]}), ">= 3"),
    (dict(hint={"polygons": [[[0, 0], [10, 0], [10, 10]]], "except": ["m.zz"]}), "unknown part"),
    (dict(colour="teal"), "colour"),
    (dict(z="high"), "z must be a number"),
    (dict(alternatives=["fish"]), "not a primitive"),
    (dict(shape="fish"), "unknown keys"),
])
def test_labels_schema_rejects(bad, why):
    from digitize.labels import schema as LS
    with pytest.raises(LS.LabelsError, match=why):
        LS.validate(_labels(**bad), PAL)


def test_labels_schema_accepts_and_defaults_the_intent():
    from digitize.labels import schema as LS
    d = _labels(primitive="cord", direction=None)
    d["motifs"][0]["parts"][0].pop("direction")
    LS.validate(d, PAL)
    assert LS.intent_of(d["motifs"][0]["parts"][0]) == "along"


def test_labels_schema_one_rest_and_duplicate_ids():
    from digitize.labels import schema as LS
    d = _labels(); p = dict(d["motifs"][0]["parts"][0])
    d["motifs"][0]["parts"].append(dict(p))                          # duplicate id
    with pytest.raises(LS.LabelsError, match="duplicate"): LS.validate(d, PAL)
    d = _labels(rest=True); q = dict(d["motifs"][0]["parts"][0], id="b", rest=True)
    d["motifs"][0]["parts"].append(q)
    with pytest.raises(LS.LabelsError, match="more than one rest"): LS.validate(d, PAL)


def test_castle_labels_file_validates_against_its_run_palette():
    from digitize import config
    from digitize.labels import schema as LS
    cfg = config.load(os.path.join(ROOT, "projects", "castle-falls-jacket", "bench", "run_bk_crop_labels.yaml"))
    d = LS.load(config.path(cfg, cfg["labels"]), palette=cfg["threads"]["palette"])
    prims = {p["primitive"] for _, p in LS.iter_parts(d)}
    assert {"cord", "band", "lobe", "plane", "radial", "stroke", "dot"} <= prims


def test_low_confidence_labels_become_review_questions_and_answers_change_the_next_compile():
    from digitize.labels import compile as LC
    from digitize import review as RV
    d = _labels(confidence=0.4, alternatives=["band"], question="is this a far roof row?")
    qs = LC.questions(d)
    assert [q["id"] for q in qs] == ["label:m.a"] and qs[0]["default"] == "plane"
    assert qs[0]["options"] == ["plane", "band", "drop"] and "far roof row" in qs[0]["text"]
    assert LC.questions(_labels(confidence=0.9)) == []                 # sure parts ask nothing
    cfg, rep = RV.apply_answers({"x": 1}, {"label:m.a": "band"}, qs)
    assert cfg["review"]["labels"] == {"m.a": "band"}
    R = LC.resolve(d, cfg["review"]["labels"])
    assert R[0]["primitive"] == "band" and R[0]["intent"] in ("along", "angle")   # the label's own intent if the new primitive takes it
    assert LC.resolve(d, {"m.a": "drop"}) == []
    with pytest.raises(RV.AnswerError):
        RV.apply_answers({}, {"label:m.a": "fish"}, qs)


# ------------------------------------------------------------------ primitives on synthetic evidence
def _ctx(img_fn, W=60, H=60, ppm_ref=8):
    """a Ctx over a synthetic reference: img_fn(X, Y) -> palette key per pixel (garment mm)"""
    from digitize.extract.evidence import Evidence, hex_rgb
    from digitize.extract.splitters import Ctx
    from digitize.rulebook import Rulebook
    xs = (np.arange(W * ppm_ref) + 0.5) / ppm_ref; ys = (np.arange(H * ppm_ref) + 0.5) / ppm_ref
    X, Y = np.meshgrid(xs, ys); key = img_fn(X, Y)
    rgb = np.zeros(X.shape + (3,))
    for k, h in PAL.items(): rgb[key == k] = hex_rgb(h)
    rng = np.random.default_rng(0); rgb = rgb + rng.normal(0, 2.0, rgb.shape)
    ref = dict(rgb=rgb, grey=rgb @ np.array([0.299, 0.587, 0.114]), bounds=(0, 0, W, H), ppm=ppm_ref, closeup_weight=None)
    ev = Evidence(ref, PAL, ppm=4.0, smooth_mm=0.2, mode_mm=0.3)
    cfg = dict(stub=dict(min_part_mm2=20.0, min_protected_mm2=4.0), direction=dict(sigma_mm=2.0, fill_sigma_mm=6.0, min_coh=0.2))
    return Ctx(ev, Rulebook(), cfg, {k: k for k in PAL}, ())


def _lp(prim, intent=None, angle=None, tones="all", params=None, colour="auto"):
    from digitize.labels import schema as LS
    return dict(pid=f"t.{prim}", motif="t", primitive=prim, intent=intent or LS.PRIMITIVES[prim][0], angle=angle, z=1.0,
                colour=colour, confidence=0.9, params=params or {}, tones=tones, seeds=[], what="")


def _claim(ctx, keys):
    return np.isin(ctx.ev.tone, [ctx.ev.keys.index(k) for k in keys])


def _audit(parts):
    from digitize import audit
    from digitize.schema import ObjectPlan
    from digitize.rulebook import Rulebook
    return audit.angle_audit(ObjectPlan(name="t", parts=parts), Rulebook())


def test_cord_runs_along_a_vertical_mass_with_constructed_audited_angles():
    from digitize import primitives
    ctx = _ctx(lambda X, Y: np.where((X > 20) & (X < 40), "white", "navy"))
    parts, used = primitives.get("cord")(ctx, _lp("cord", params=dict(cord_mm=5, cords_min=2)), 3.0, _claim(ctx, ["white"]))
    assert len(parts) >= 3 and all(p.kind == "cord" for p in parts)
    assert all(abs(((p.dir.angle - 90) + 90) % 180 - 90) < 5 for p in parts)          # along the fall: vertical
    assert all(p.dir.source == "splitter" and p.meta["construct"]["rule"] == "axis" for p in parts)
    assert _audit(parts)["random_angles"] == 0
    parts[0].dir.angle = (parts[0].dir.angle + 30) % 180                                 # a typed-in angle is caught
    assert _audit(parts)["random_angles"] == 1


def test_band_along_follows_the_mass_run_and_cuts_strips_by_tone():
    from digitize import primitives
    def img(X, Y):
        return np.where((Y > 10) & (Y < 18), "white", np.where((Y >= 18) & (Y < 26), "pink", "navy"))
    ctx = _ctx(img)
    parts, _ = primitives.get("band")(ctx, _lp("band", params=dict(min_band_mm=3)), 0.0, _claim(ctx, ["white", "pink"]))
    assert {p.thread for p in parts} == {"white", "pink"}
    assert all(min(p.dir.angle, 180 - p.dir.angle) < 5 for p in parts)                 # horizontal run
    assert _audit(parts)["random_angles"] == 0


def test_plane_takes_the_labelled_angle_and_the_audit_reads_it():
    from digitize import primitives, audit
    ctx = _ctx(lambda X, Y: np.where((X > 10) & (X < 40) & (Y > 10) & (Y < 40), "navy", "white"))
    parts, _ = primitives.get("plane")(ctx, _lp("plane", angle=100.0), 5.0, _claim(ctx, ["navy"]))
    assert len(parts) == 1 and parts[0].dir.source == "label" and parts[0].dir.angle == 100.0
    assert audit.bucket(parts[0].dir.source) == "independent"
    assert _audit(parts)["random_angles"] == 0
    parts[0].meta["label_angle"] = 10.0                                                  # angle and its record disagree
    assert _audit(parts)["random_angles"] == 1


def test_lobe_outline_angle_is_rebuilt_from_geometry_and_reported_as_outline():
    from digitize import primitives, audit
    from shapely.affinity import rotate
    ctx = _ctx(lambda X, Y: np.where(((X - 30) / 18) ** 2 + ((Y - 30) / 7) ** 2 < 1, "grn", "navy"))
    parts, _ = primitives.get("lobe")(ctx, _lp("lobe", params=dict(lobe_sep_mm=40, min_lobe_mm2=20)), 2.0, _claim(ctx, ["grn"]))
    assert len(parts) == 1 and parts[0].meta["construct"]["rule"] == "long_axis"
    assert min(parts[0].dir.angle, 180 - parts[0].dir.angle) < 5                        # the ellipse's long axis
    assert audit.bucket_of(parts[0]) == "outline"
    assert _audit(parts)["random_angles"] == 0
    parts[0].geom = parts[0].geom.buffer(1.0)                                            # sequencing reshapes it: still rebuilds
    assert _audit(parts)["random_angles"] == 0                                            # from the recorded outline
    parts[0].dir.angle = (parts[0].dir.angle + 30) % 180                                 # a typed-in angle is caught
    assert _audit(parts)["random_angles"] == 1
    parts[0].dir.angle = (parts[0].dir.angle - 30) % 180
    parts[0].meta["construct"]["of"] = [[x + 40, y] for x, y in parts[0].meta["construct"]["of"]]   # an outline elsewhere
    assert _audit(parts)["random_angles"] == 1


def test_radial_finds_lit_centres_and_sews_rays_with_beads_and_a_knocked_out_ground():
    from digitize import primitives
    cs = [(15, 15), (30, 15), (45, 15), (15, 32), (30, 32), (45, 32)]
    def img(X, Y):
        out = np.where((X > 6) & (X < 54) & (Y > 6) & (Y < 41), "rose", "navy").astype(object)
        for cx, cy in cs: out[(X - cx) ** 2 + (Y - cy) ** 2 < 3.0 ** 2] = "pink"
        for cx, cy in cs: out[(X - cx) ** 2 + (Y - cy) ** 2 < 0.8 ** 2] = "white"
        return out
    ctx = _ctx(img)
    lp = _lp("radial", tones=["pink", "rose", "white"], params=dict(sep_mm=6, ground="grain", r_max=4.0, prominence=2.0))
    parts, _ = primitives.get("radial")(ctx, lp, 7.0, _claim(ctx, ["pink", "rose", "white"]))
    fl = [p for p in parts if p.kind == "radial"]; bd = [p for p in parts if p.kind == "bead"]; gr = [p for p in parts if p.meta.get("ground")]
    assert len(fl) == len(cs) and len(bd) == len(cs) and len(gr) == 1
    for p in fl:
        c = p.meta["centre"]; assert min(math.dist(c, q) for q in cs) < 1.0
        assert p.dir.mode == "radial" and p.meta["knockout_of"] == gr[0].id
    assert _audit(parts)["random_angles"] == 0


def test_stroke_gives_back_blobs_and_columns_strokes():
    from digitize import primitives
    def img(X, Y):
        out = np.where((np.abs(Y - 15) < 1.5) & (X > 5) & (X < 55), "gold", "navy").astype(object)
        out[(X - 30) ** 2 + (Y - 42) ** 2 < 8 ** 2] = "gold"                            # a round blob: not a stroke
        return out
    ctx = _ctx(img)
    claim = _claim(ctx, ["gold"])
    parts, used = primitives.get("stroke")(ctx, _lp("stroke"), 5.0, claim)
    assert len(parts) == 1 and parts[0].kind == "stroke" and parts[0].dir.mode == "contour"
    assert abs(parts[0].dir.angle - 90) < 5                                             # across a horizontal stroke
    blob = ctx.ev.mask(Point(30, 42).buffer(6))
    assert not (used & blob).any()                                                      # the blob went back
    assert _audit(parts)["random_angles"] == 0


def test_dot_beads_small_components_and_line_follows_a_thin_mark():
    from digitize import primitives
    def img(X, Y):
        out = np.full(X.shape, "navy", object)
        for cx in (10, 20, 30): out[(X - cx) ** 2 + (Y - 10) ** 2 < 0.8 ** 2] = "gold"
        out[(np.abs(Y - 40) < 0.5) & (X > 10) & (X < 50)] = "white"
        return out
    ctx = _ctx(img)
    beads, _ = primitives.get("dot")(ctx, _lp("dot"), 5.6, _claim(ctx, ["gold"]))
    assert len(beads) == 3 and all(p.kind == "bead" and 1.0 <= p.meta["knots"][0][2] <= 3.0 for p in beads)
    lines, _ = primitives.get("line")(ctx, _lp("line"), 5.6, _claim(ctx, ["white"]))
    assert len(lines) == 1 and lines[0].kind == "line" and min(lines[0].dir.angle, 180 - lines[0].dir.angle) < 5
    assert _audit(beads + lines)["random_angles"] == 0


def test_compile_claims_highest_z_first_and_seeds_keep_only_their_component():
    from digitize.labels import compile as LC
    ctx = _ctx(lambda X, Y: np.where(((X - 15) ** 2 + (Y - 15) ** 2 < 36) | ((X - 45) ** 2 + (Y - 45) ** 2 < 36), "pink", "navy"))
    d = {"schema": "techpack.labels/1", "motifs": [{"id": "m", "parts": [
        {"id": "seeded", "primitive": "plane", "z": 5, "confidence": 0.9, "direction": {"intent": "angle", "angle": 45},
         "hint": {"polygons": [[[0, 0], [60, 0], [60, 60], [0, 60]]], "seeds": [[15, 15]]}, "tones": ["pink"]},
        {"id": "low", "primitive": "plane", "z": 1, "confidence": 0.9, "direction": {"intent": "angle", "angle": 0},
         "hint": {"polygons": [[[0, 0], [60, 0], [60, 60], [0, 60]]]}, "tones": ["pink"]},
        {"id": "rest", "primitive": "plane", "z": 0, "confidence": 0.9, "rest": True, "direction": {"intent": "angle", "angle": 90}}]}]}
    from digitize.labels import schema as LS
    LS.validate(d, PAL)
    parts, log, qs = LC.extract(ctx, ctx.ev, d)
    by = {}
    for p in parts: by.setdefault(p.meta["label"], []).append(p)
    assert by["m.seeded"][0].geom.distance(Point(15, 15)) == 0 and by["m.seeded"][0].geom.distance(Point(45, 45)) > 10
    assert by["m.low"][0].geom.distance(Point(45, 45)) == 0 and by["m.low"][0].geom.distance(Point(15, 15)) > 10
    assert by["m.rest"][0].thread == "navy" and qs == []
    assert all(p.meta["splitter"] == "labels" and p.zone == "m" for p in parts)


# ------------------------------------------------------------------ no subject code in the generic engine
SUBJECT_WORDS = ("fall", "waterfall", "sky", "cloud", "castle", "temple", "pagoda", "blossom", "cherry", "floret", "crown",
                 "trunk", "branch", "roof", "wall", "window", "fish", "koi", "lily", "tree", "leaf", "flower", "petal", "stratum",
                 "cliff", "rock", "building", "village", "pool", "foam", "canopy", "knot", "stud", "eave")


def _code_words(path):
    """identifiers and string constants of a module, minus docstrings, comments and import paths"""
    import ast, re
    tree = ast.parse(open(path).read()); docs = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body and isinstance(n.body[0], ast.Expr) \
                and isinstance(getattr(n.body[0], "value", None), ast.Constant) and isinstance(n.body[0].value.value, str):
            docs.add(id(n.body[0].value))
    out = []
    for n in ast.walk(tree):
        if isinstance(n, (ast.Import, ast.ImportFrom)): continue
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs: out.append(n.value)
        elif isinstance(n, ast.Name): out.append(n.id)
        elif isinstance(n, ast.Attribute): out.append(n.attr)
        elif isinstance(n, ast.FunctionDef): out.append(n.name)
        elif isinstance(n, ast.arg): out.append(n.arg)
        elif isinstance(n, ast.keyword) and n.arg: out.append(n.arg)
    words = set()
    for s in out: words |= set(re.findall(r"[a-z]+", s.lower()))
    return words


def test_primitives_and_labels_carry_no_subject_code():
    import glob
    files = glob.glob(os.path.join(ROOT, "engine", "digitize", "primitives", "*.py")) + \
        glob.glob(os.path.join(ROOT, "engine", "digitize", "labels", "*.py"))
    assert len(files) >= 11
    hits = {os.path.basename(f): sorted(w for w in _code_words(f) if w in SUBJECT_WORDS) for f in files}
    assert {f: h for f, h in hits.items() if h} == {}


def test_subject_word_guard_catches_a_subject_branch(tmp_path):
    p = tmp_path / "x.py"
    p.write_text('"""a generic module about falls"""\nfrom digitize.extract.splitters.fall import cords\n'
                 'def f(lp):\n    if lp["what"] == "koi": return 1\n')
    w = _code_words(str(p))
    assert "koi" in w and "falls" not in w and "fall" not in w            # docstring + import path ignored, the branch caught
