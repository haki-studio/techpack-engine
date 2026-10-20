"""ENGINE_PLAN M3b: trees, crowns and florets (extract/splitters/trunk.py, crown.py, blossom.py, construct.py) and the
gate plumbing they need. Each guard was proven RED by a mutation of the code it guards (scratchpad m3b/mutate.py,
listed in RECAP-2026-10-20-engine-m3b.md) and is GREEN on this branch."""
import math
import numpy as np
import pytest
from shapely.geometry import box, Point, LineString, Polygon
from digitize.schema import Part, DirSpec, ObjectPlan, StitchSpec
from digitize.rulebook import Rulebook
from digitize import techniques, audit, sequence as SQ, direction as DR

PAL = {"cf_navy": "#22355C", "cf_rose": "#B4506F", "cf_pink": "#DE8EA6", "cf_pinklt": "#F2C3CE", "cf_brown": "#4E3F31",
       "cf_grndk": "#2F402D", "cf_grn": "#5A7240"}
RGB = {k: tuple(int(v.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) for k, v in PAL.items()}
BLOSSOM = ["cf_pinklt", "cf_pink", "cf_rose"]


def _ctx(rgb, bounds, ppm=12.0, cfg=None):
    from digitize.extract import evidence
    from digitize.extract.splitters import Ctx
    from digitize import config
    grey = (rgb @ np.array([0.299, 0.587, 0.114]))
    ref = dict(bounds=bounds, ppm=ppm, rgb=rgb, grey=grey, closeup_weight=np.ones(grey.shape))
    ev = evidence.build(ref, PAL, ppm=4.0)
    return Ctx(ev, Rulebook(), config.merge(config.DEFAULTS, cfg or {}), {k: k for k in PAL}, []), ev


def _canvas(W, H, ppm=12.0, fill="cf_navy"):
    y, x = np.mgrid[0:H * int(ppm), 0:W * int(ppm)] / ppm + 0.5 / ppm
    return x, y, np.zeros(x.shape + (3,)) + np.array(RGB[fill], float)


def _paint(rgb, m, key): rgb[m] = RGB[key]


def _spec(tech, **over):
    d = dict(Rulebook().data["techniques"][tech]); d.update(over)
    return StitchSpec(technique=tech, spacing=d.get("spacing", 0.45), stitch_len=d.get("stitch_len", 3.5), underlay=d.get("underlay", []),
                      pull_comp=d.get("pull_comp", 0.2), params={k: v for k, v in d.items() if k not in ("spacing", "stitch_len", "underlay", "pull_comp")})


def _segs(blocks):
    return [tuple(a) + tuple(b) for blk in blocks for a, b in zip(blk.pts, blk.pts[1:]) if tuple(a) != tuple(b)]


# ------------------------------------------------------------------ constructed angles are audited, never asserted
def test_constructed_angles_are_rebuilt_by_the_audit():
    """a splitter-made angle (trunk axis, branch column, clump fan, floret) is RE-BUILT from meta["construct"]: an
    honest part passes, a random angle with the same construction is counted, a part with no construction is counted,
    and a fan whose origin is far from the clump ("does not touch its support") is counted. Mutation (audit.basis
    returns the declared angle for source splitter) -> red."""
    rb = Rulebook(); g = box(0, 0, 30, 4); cl = [[0.0, 2.0], [30.0, 2.0]]
    honest = Part(id="t.1", kind="trunk_strip", geom=g, thread="t", z=1, dir=DirSpec(0.0, source="splitter"),
                  meta=dict(construct=dict(rule="axis", line=cl)))
    banded = Part(id="t.2", kind="trunk_strip", geom=box(0, 10, 30, 14), thread="t", z=1, dir=DirSpec(10.0, source="splitter"),
                  meta=dict(construct=dict(rule="axis", line=[[0.0, 12.0], [30.0, 12.0]]), band_offset_deg=10.0))
    forged = Part(id="t.3", kind="trunk_strip", geom=box(0, 20, 30, 24), thread="t", z=1,
                  dir=DirSpec(float(np.random.default_rng(5).uniform(30, 150)), source="splitter"),
                  meta=dict(construct=dict(rule="axis", line=[[0.0, 22.0], [30.0, 22.0]])))
    bare = Part(id="t.4", kind="branch", geom=box(0, 30, 30, 32), thread="t", z=1, dir=DirSpec(90.0, mode="contour", source="splitter"))
    col = Part(id="b.1", kind="branch", geom=box(0, 40, 30, 42), thread="t", z=1, dir=DirSpec(90.0, mode="contour", source="splitter"),
               meta=dict(construct=dict(rule="column", cl=[[0.0, 41.0], [15.0, 41.0], [30.0, 41.0]])))
    clump = Point(50, 10).buffer(4)
    fan = Part(id="c.1", kind="crown_clump_dark", geom=clump, thread="t", z=2, dir=DirSpec(90.0, source="splitter"),
               meta=dict(construct={"rule": "fan", "from": [50.0, 6.0], "to": [50.0, 10.0]}))
    far = Part(id="c.2", kind="crown_clump_dark", geom=Point(50, 30).buffer(4), thread="t", z=2, dir=DirSpec(90.0, source="splitter"),
               meta=dict(construct={"rule": "fan", "from": [50.0, 10.0], "to": [50.0, 30.0]}))
    fl = Part(id="f.1", kind="floret", geom=Point(70, 10).buffer(3).difference(Point(70, 10).buffer(0.75)), thread="t", z=7,
              dir=DirSpec(0.0, mode="radial", source="splitter"), meta=dict(construct=dict(rule="radial", centre=[70.0, 10.0])))
    r = audit.angle_audit(ObjectPlan(name="t", parts=[honest, banded, forged, bare, col, fan, far, fl]), rb)
    assert {u["part"] for u in r["unexplained"]} == {"t.3", "t.4", "c.2"}, r
    assert any("support" in u["why"] for u in r["unexplained"] if u["part"] == "c.2")


def test_fan_angles_are_outline_not_independent():
    """A24: a clump's fan is read off its traced outline, so its direction tiles are reported as "outline", never as
    independent evidence; trunk axes and rule angles stay independent. Mutation (OUTLINE_RULES emptied) -> red."""
    fan = Part(id="c", kind="crown_clump_dark", geom=Point(0, 0).buffer(3), thread="t", z=2, dir=DirSpec(90.0, source="splitter"),
               meta=dict(construct={"rule": "fan", "from": [0.0, -3.0], "to": [0.0, 0.0]}))
    ax = Part(id="a", kind="trunk_strip", geom=box(0, 0, 20, 3), thread="t", z=1, dir=DirSpec(0.0, source="splitter"),
              meta=dict(construct=dict(rule="axis", line=[[0.0, 1.5], [20.0, 1.5]])))
    assert audit.bucket_of(fan) == "outline" and audit.bucket_of(ax) == "independent"
    dm = dict(ok_tiles=[(0, 0), (10, 1)], fail_dev=[], fail_chaos=[])
    r = audit.direction_by_source(dm, lambda c: fan if c == (0, 0) else ax)
    assert r["outline"]["tiles"] == 1 and r["independent"]["tiles"] == 1


# ------------------------------------------------------------------ blossom splitter
def _blossom_scene():
    """a deep-rose mass (10..54 x 8..32 mm) holding 6 x 3 pale domes 7 mm apart (pink, a pale centre), on navy"""
    x, y, rgb = _canvas(64, 40)
    mass = (x > 10) & (x < 54) & (y > 8) & (y < 32)
    _paint(rgb, mass, "cf_rose")
    cs = [(13.5 + 7 * i, 13.0 + 7 * j) for i in range(6) for j in range(3)]
    for cx, cy in cs:
        d = np.hypot(x - cx, y - cy)
        _paint(rgb, mass & (d < 2.9), "cf_pink"); _paint(rgb, mass & (d < 1.1), "cf_pinklt")
    return rgb, cs


def test_blossom_splitter_florets_match_the_reference_count():
    """A2 / A14: one floret per dome in the reference (18 of 18, each centred within 0.6 mm), every floret RADIAL with a
    bead knot in the pale thread, the canopy in the deep thread, the florets and knots sewn BEFORE the canopy and
    knocked out of it (B2). Mutations: (a) floret centres every 2 x floret_sep (min_distance doubled) -> red on the
    count; (b) florets not knocked out of the canopy -> red; (c) florets sewn after the canopy -> red."""
    from digitize.extract.splitters import blossom
    rgb, cs = _blossom_scene()
    ctx, ev = _ctx(rgb, (0, 0, 64, 40))
    claim = np.isin(ev.tone, [ev.keys.index(k) for k in BLOSSOM])
    parts, used = blossom.split(ctx, {"id": "blossom", "tones": BLOSSOM}, 7.0, claim)
    fl = [p for p in parts if p.kind == "floret"]; kn = [p for p in parts if p.kind == "knot"]; can = [p for p in parts if p.kind == "canopy"]
    assert len(fl) == len(cs) == 18 and len(kn) == 18 and len(can) == 1, (len(fl), len(kn), len(can))
    for c in cs:
        assert min(math.dist(c, p.meta["centre"]) for p in fl) < 0.6
    assert all(p.dir.mode == "radial" and p.thread == "cf_pink" for p in fl)
    assert all(k.thread == "cf_pinklt" for k in kn) and can[0].thread == "cf_rose"
    assert all(p.z < can[0].z for p in fl + kn)
    assert can[0].geom.intersection(DR_union(fl + kn)).area < 0.5
    assert ctx.stats["blossom"]["florets"] == 18
    assert all(p.meta["knockout_of"] == can[0].id for p in fl + kn)            # M4g hint contract


def DR_union(ps):
    from shapely.ops import unary_union
    return unary_union([p.geom for p in ps])


def test_radial_adherence_reads_rays_on_the_file():
    """a radial floret sewn by the radial plugin: >= 95 % of its visible stitches lie on rays from its centre; the same
    part labelled radial but sewn as a fixed-angle satin scores low. Mutation (rays replaced by the declared 0 deg) ->
    red."""
    from digitize.extract.splitters import blossom
    g = Point(10, 10).buffer(3.2).difference(Point(10, 10).buffer(0.75))
    p = Part(id="f", kind="floret", geom=g, thread="t", z=7, dir=DirSpec(0.0, mode="radial", source="splitter"), meta=dict(centre=[10.0, 10.0]))
    p.technique = "radial"; p.stitch = _spec("radial")
    segs = _segs(techniques.get("radial").plan(p))
    plan = ObjectPlan(name="t", parts=[p])
    r = blossom.radial_adherence(plan, segs, ["f"] * len(segs), (0, 0, 20, 20))
    assert r["stitches"] > 30 and r["pct_within"] >= 95.0, r
    q = Part(id="f", kind="floret", geom=g, thread="t", z=7, dir=DirSpec(30.0), meta={}); q.technique = "satin"; q.stitch = _spec("satin")
    bad = _segs(techniques.get("satin").plan(q))
    r2 = blossom.radial_adherence(plan, bad, ["f"] * len(bad), (0, 0, 20, 20))
    assert r2["pct_within"] < 50.0, r2


# ------------------------------------------------------------------ trunk splitter
def test_trunk_splitter_keeps_held_strokes_along_their_axis():
    """a 2 mm bark stroke at 30 deg inside a blossom mass becomes ONE branch column (across the stroke: 120 deg) and a
    7 mm stroke a set of trunk strips along its axis (30 deg, same-thread strips alternating +-10); a bark stroke on
    bare rock (no crown around it) is NOT taken. Mutation (support check off) -> red."""
    from digitize.extract.splitters import trunk
    x, y, rgb = _canvas(90, 60)
    _paint(rgb, (x > 2) & (x < 50) & (y > 2) & (y < 40), "cf_pink")
    a = math.radians(30.0); ux, uy = math.cos(a), math.sin(a)
    def stroke(cx, cy, L, w):
        t = (x - cx) * ux + (y - cy) * uy; n = -(x - cx) * uy + (y - cy) * ux
        return (np.abs(t) < L / 2) & (np.abs(n) < w / 2)
    _paint(rgb, stroke(16, 14, 22, 2.0), "cf_brown")
    _paint(rgb, stroke(34, 27, 24, 7.0), "cf_brown")
    _paint(rgb, stroke(72, 45, 22, 2.0), "cf_brown")                 # on navy rock: no crown around it
    ctx, ev = _ctx(rgb, (0, 0, 90, 60))
    claim = ev.tone == ev.keys.index("cf_brown")
    parts, used = trunk.split(ctx, {"id": "trunks", "tones": ["cf_brown"]}, 6.5, claim)
    br = [p for p in parts if p.kind == "branch"]; ts = [p for p in parts if p.kind == "trunk_strip"]
    assert all(p.geom.centroid.x < 55 for p in parts), "the rock stroke has no crown around it: not a trunk"
    assert len(br) == 1 and DR.axial_diff(br[0].dir.angle, 120.0) < 6 and br[0].dir.mode == "contour", [(p.dir.angle, p.dir.mode) for p in br]
    assert len(ts) >= 2 and all(DR.axial_diff(p.dir.angle, 30.0) <= 10.0 + 6 for p in ts), [p.dir.angle for p in ts]
    assert not used[ev.mask(box(60, 38, 85, 55))].any()
    r = audit.angle_audit(ObjectPlan(name="t", parts=parts), Rulebook())
    assert r["random_angles"] == 0, r


def test_column_adherence_reads_across_the_centreline():
    """a curved branch sewn as a split-satin column: >= 90 % of its visible stitches lie across its centreline; the same
    part sewn as fixed-angle rows scores low. Mutation (along instead of across: tangent + 0) -> red."""
    from digitize.extract.splitters import trunk
    cl = [(2 + t, 10 + 6 * math.sin(t / 8.0)) for t in np.linspace(0, 26, 40)]
    g = LineString(cl).buffer(1.1, cap_style=2)
    p = Part(id="b", kind="branch", geom=g, thread="t", z=6.5, dir=DirSpec(90.0, mode="contour", source="splitter"),
             meta=dict(cl=[list(c) for c in cl], w=2.2)); p.technique = "split_satin"; p.stitch = _spec("split_satin", mode="column")
    p.stitch.params["mode"] = "column"
    segs = _segs(techniques.get("split_satin").plan(p)); plan = ObjectPlan(name="t", parts=[p])
    r = trunk.column_adherence(plan, segs, ["b"] * len(segs), (0, 0, 32, 22))
    assert r["stitches"] > 30 and r["pct_within"] >= 90.0, r
    q = Part(id="b", kind="branch", geom=g, thread="t", z=6.5, dir=DirSpec(0.0)); q.technique = "tatami"; q.stitch = _spec("tatami", underlay=[])
    bad = _segs(techniques.get("tatami").plan(q))
    assert trunk.column_adherence(plan, bad, ["b"] * len(bad), (0, 0, 32, 22))["pct_within"] < 60.0


# ------------------------------------------------------------------ crown splitter
def test_crown_splitter_clumps_from_lit_tops_dark_after_lit():
    """three lit highlights on a dark foliage mass -> three clumps; each clump's lit piece sews BEFORE its dark part and
    is knocked out of it (B2), every clump's fan rebuilds in the audit (it touches its support). Mutations: (a) lit not
    knocked out of the dark -> red; (b) lit sewn after the dark (lit_z > 0) -> red."""
    from digitize.extract.splitters import crown
    x, y, rgb = _canvas(60, 40)
    mass = (x > 8) & (x < 52) & (y > 10) & (y < 30)
    _paint(rgb, mass, "cf_grndk")
    for cx in (16, 30, 44): _paint(rgb, mass & (np.hypot(x - cx, (y - 17) * 1.6) < 4.0), "cf_grn")
    ctx, ev = _ctx(rgb, (0, 0, 60, 40))
    claim = np.isin(ev.tone, [ev.keys.index("cf_grndk"), ev.keys.index("cf_grn")])
    parts, used = crown.split(ctx, {"id": "foliage", "tones": ["cf_grndk", "cf_grn"]}, 2.0, claim)
    dark = [p for p in parts if p.kind == "crown_clump_dark"]; lit = [p for p in parts if p.kind == "crown_clump_lit"]
    assert len(dark) == 3 and len(lit) == 3, (len(dark), len(lit))
    for l in lit:
        d = next(p for p in dark if p.id == l.meta["lit_of"])
        assert l.z < d.z and d.geom.intersection(l.geom).area < 0.5 and l.meta["knockout_of"] == d.id
    assert audit.angle_audit(ObjectPlan(name="t", parts=parts), Rulebook())["random_angles"] == 0


# ------------------------------------------------------------------ plumbing
def test_florets_by_part_map_refiles_only_radial_runs(monkeypatch):
    """qa.satin_shape cannot tell a floret from a fan; the part map can. A flagged run labelled with a RADIAL part is
    re-filed as a floret fan, a < 1 mm run inside a bead (its cross underlay) as a bead; a blob on a fixed-angle part
    stays flagged. Mutation (re-file every flag) -> red."""
    import qa
    from digitize import run as RN
    flags = [dict(kind="blob", i0=0, i1=5, at_mm=(1.0, 1.0)), dict(kind="blob", i0=6, i1=11, at_mm=(2.0, 2.0)),
             dict(kind="too-narrow", i0=0, i1=5, at_mm=(1.0, 1.0))]
    monkeypatch.setattr(qa, "satin_shape", lambda segs, **k: dict(flags=flags))
    fl = Part(id="f", kind="floret", geom=Point(1, 1).buffer(2), thread="t", z=7, dir=DirSpec(0.0, mode="radial", source="splitter"))
    st = Part(id="s", kind="zone_stub", geom=box(0, 0, 4, 4), thread="t", z=1, dir=DirSpec(0.0)); st.technique = "tatami"
    kn = Part(id="k", kind="knot", geom=Point(3, 3).buffer(0.75), thread="t", z=7, dir=DirSpec(18.0, source="splitter")); kn.technique = "dot"
    flags.append(dict(kind="too-narrow", i0=12, i1=17, at_mm=(3.0, 3.0), width_mm=0.34))
    for f in flags: f.setdefault("width_mm", 2.0)
    row = dict(satin=dict(blob=2, too_narrow=2, too_wide=0))
    RN.florets_by_part_map(row, [(0, 0, 1, 1)] * 18, ["f"] * 6 + ["s"] * 6 + ["k"] * 6, ObjectPlan(name="t", parts=[fl, st, kn]), (0, 0, 10, 10))
    assert row["satin"]["blob"] == 1 and row["satin"]["too_narrow"] == 0, row
    assert row["satin"]["bead_runs_by_part_map"]["too-narrow"] == 1


def test_beads_neither_grow_nor_drop():
    """a 1.5 mm bead (knot) sews its declared knots: underlap must not grow it 1 mm into the canopy (it would touch its
    neighbours and read as one blob for rule 3), and absorb_fragments must not drop it as a < 2 mm2 sliver. Mutations:
    (a) underlap skip removed -> red; (b) tiny-kind floor removed -> red."""
    k = Part(id="k", kind="knot", geom=Point(5, 5).buffer(0.75, 16), thread="p", z=6.8, dir=DirSpec(18.0, source="splitter"))
    c = Part(id="c", kind="canopy", geom=box(0, 0, 10, 10).difference(Point(5, 5).buffer(0.75, 16)), thread="r", z=7, dir=DirSpec(30.0))
    a0 = k.geom.area
    SQ.underlap([k, c], 1.0)
    assert abs(k.geom.area - a0) < 0.05, k.geom.area
    kept, dropped = SQ.absorb_fragments([k, c], 2.0)
    assert "k" not in dropped and len(kept) == 2


def test_radial_parts_are_a_different_texture_for_rule_3():
    """rule 3: same-colour neighbours differ >= 15 deg OR use a different texture. Two touching radial florets (declared
    0 deg by convention) are not a clash; two touching fixed fills at the same angle still are. Mutation
    (NO_SINGLE_ANGLE without radial) -> red."""
    f1 = Part(id="a", kind="floret", geom=Point(0, 0).buffer(3), thread="p", z=7, dir=DirSpec(0.0, mode="radial", source="splitter"))
    f2 = Part(id="b", kind="floret", geom=Point(5.8, 0).buffer(3), thread="p", z=7, dir=DirSpec(0.0, mode="radial", source="splitter"))
    s1 = Part(id="c", kind="canopy", geom=box(20, 0, 30, 10), thread="p", z=7, dir=DirSpec(40.0))
    s2 = Part(id="d", kind="canopy", geom=box(30, 0, 40, 10), thread="p", z=7, dir=DirSpec(45.0))
    r = DR.separation_report([f1, f2, s1, s2])
    assert r["close"] == 1 and r["examples"][0][:2] == ("c", "d"), r


def test_rulebook_m3b_kinds_follow_the_playbook():
    """the M3b kinds say what the playbook says: trunk strips split satin, branches a column that follows its line,
    clumps tatami, florets radial (and radial allowed only on florets), knots beads."""
    rb = Rulebook(); K = rb.data["kinds"]
    assert K["trunk_strip"]["techniques"][0] == "split_satin" and K["branch"]["params"]["mode"] == "column"
    assert "split_satin" in K["branch"]["follows"]
    assert rb.technique_for("floret") == "radial" and "floret" in rb.data["techniques"]["radial"]["allowed_kinds"]
    assert "canopy" not in rb.data["techniques"]["radial"]["allowed_kinds"] and rb.technique_for("knot") == "dot"
    assert K["crown_clump_dark"]["techniques"] == ["tatami"] and K["canopy"]["dir"] == "field-mean"


def test_limbs_cut_forks_not_square_ends():
    """a branching bark stroke is cut into one limb per skeleton branch (a Y: 3 limbs), while the medial-axis forks
    into the corners of a square-ended stroke are spurs, not limbs (a 7 x 24 mm bar at 30 deg: 1 limb, not 5). Mutation (spurs kept)
    -> red."""
    from digitize.extract.splitters import trunk
    x, y, rgb = _canvas(60, 50)
    ctx, ev = _ctx(rgb, (0, 0, 60, 50))
    from shapely import affinity
    bar = affinity.rotate(box(18, 6.5, 42, 13.5), 30)              # square ends, off the pixel grid
    assert len(trunk.limbs(ctx, ev.mask(bar), 2.0)) == 1
    knob = box(15, 30, 45, 37).union(box(20, 29, 22, 38))          # a bump on the outline is not a limb either
    assert len(trunk.limbs(ctx, ev.mask(knob), 2.0)) == 1
    seg = lambda a, b, w: LineString([a, b]).buffer(w / 2)
    yy = seg((30, 45), (30, 32), 3).union(seg((30, 32), (20, 22), 2.5)).union(seg((30, 32), (40, 22), 2.5))
    assert len(trunk.limbs(ctx, ev.mask(yy), 2.0)) == 3
