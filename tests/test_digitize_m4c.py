"""ENGINE_PLAN M4c: radial-floret exemption for the 8 mm chaos gate (engine/digitize/gates_radial.py) and crown clumps
(extract/splitters/crown.py). Every guard here was proven RED by a mutation of the code it guards (scratchpad
m4c/mutate.py, listed in RECAP-2026-10-20-engine-m4c.md) and is GREEN on this branch.

The chaos tiles are produced by the real gate (qa.direction_match on the visible layer of synthetic stitches over a flat
reference: no reference grain, so only chaos can fail), never typed in."""
import json, math, os
import numpy as np
import pytest
from shapely.geometry import Point, box
import qa
from digitize.schema import Part, DirSpec
from digitize.rulebook import Rulebook
from digitize import gates_radial as GR, bench

PPM = 12.0
ORIGIN = (-40.0, 300.0)               # a crop that does not start at 0, 0 (garment mm), like the bench crop
SIZE = 16.0                           # 2 x 2 tiles of 8 mm


def floret(pid, c, r=3.0, mode="radial", centre=True):
    meta = dict(construct=dict(rule="radial"))
    if centre: meta["centre"] = [c[0], c[1]]
    return Part(id=pid, kind="floret", geom=Point(c).buffer(r, 32).difference(Point(c).buffer(0.75)), thread="cf_pink", z=0,
                dir=DirSpec(0.0, mode=mode, source="splitter"), meta=meta)


def fill(pid, geom):
    return Part(id=pid, kind="canopy", geom=geom, thread="cf_rose", z=1, dir=DirSpec(30.0, source="field-mean"), meta={})


def rays(c, r, n=36, r0=0.8, step=7.0):
    """radial satin from the centre: ray stitches in short pieces (a real floret's rows)"""
    out = []
    for k in range(n):
        t = 2 * math.pi * k / n; ca, sa = math.cos(t), math.sin(t); a = r0
        while a < r - 1e-6:
            b = min(r, a + step); out.append((c[0] + a * ca, c[1] + a * sa, c[0] + b * ca, c[1] + b * sa)); a = b
    return out


def random_stitches(c, r, n, rng, L=1.0):
    out = []
    for _ in range(n):
        rr = r * math.sqrt(rng.random()) * 0.9; t = rng.random() * 2 * math.pi; a = rng.random() * math.pi
        x, y = c[0] + rr * math.cos(t), c[1] + rr * math.sin(t)
        out.append((x - L / 2 * math.cos(a), y - L / 2 * math.sin(a), x + L / 2 * math.cos(a), y + L / 2 * math.sin(a)))
    return out


def parallel(x0, y0, x1, y1, ang=30.0, sp=0.45, L=2.0):
    """a fixed-angle fill over a box: segments of length L along ang"""
    out = []; ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    for y in np.arange(y0, y1, sp):
        for x in np.arange(x0, x1, L):
            out.append((x, y, x + L * ca, y + L * sa))
    return out


def judge(groups, parts, cfg=None):
    """groups: [(part id, segs)] in sew order (garment mm). -> (dm, exemption) through the real chaos gate"""
    segs, labels = [], []
    for pid, ss in groups:
        segs += ss; labels += [pid] * len(ss)
    x0, y0 = ORIGIN; ref = np.full((int(SIZE * PPM), int(SIZE * PPM)), 128.0)
    local = [(a - x0, b - y0, c - x0, d - y0) for a, b, c, d in segs]
    dm = qa.direction_match(ref, PPM, local)
    vis, idx = qa.visible_segments(segs, (x0, y0, x0 + SIZE, y0 + SIZE), ppm=PPM, return_index=True)
    return dm, GR.exempt(dm, vis, [labels[i] for i in idx], parts, cfg, PPM, origin=ORIGIN)


def at(tx, ty):
    return (ORIGIN[0] + 8 * tx + 4.0, ORIGIN[1] + 8 * ty + 4.0)


def floret_tile(tx, ty, r=2.8, prefix="f"):
    """4 florets in one 8 mm tile (2 x 2, 4 mm apart): rays in every direction -> chaotic by construction"""
    cx, cy = at(tx, ty); parts, groups = [], []
    for i, (dx, dy) in enumerate(((-2, -2), (2, -2), (-2, 2), (2, 2))):
        c = (cx + dx, cy + dy); p = floret(f"{prefix}{tx}{ty}.{i}", c, r); parts.append(p); groups.append((p.id, rays(c, r)))
    return parts, groups


# ---------------------------------------------------------------- the exemption
def test_floret_tiles_are_chaotic_raw_and_exempt_when_proven():
    parts, groups = floret_tile(0, 0)
    dm, ex = judge(groups, parts)
    assert len(dm["fail_chaos"]) == 1 and dm["tiles"] == 1                   # the raw gate does call it chaos
    assert ex["n_exempt"] == 1 and ex["chaos_raw"] == 1 and ex["chaos_after"] == 0
    assert ex["pct_chaos_raw"] == 100.0 and ex["pct_chaos_after"] == 0.0       # raw figure kept next to the exempted one
    t = ex["exempt"][0]; assert t["share"] >= 0.99 and t["adherence"] >= 99.0


def test_non_floret_radial_blob_with_random_stitches_stays_chaotic():
    """review (i): a LARGE radial-mode blob is not floret size: never exempt, even sewn perfectly radial; sewn at random it
    also fails the plan-wide radial adherence"""
    from digitize.extract.splitters import blossom
    from digitize.schema import ObjectPlan
    c = at(0, 0); big = floret("blob", c, r=6.0)
    rng = np.random.default_rng(1)
    dm, ex = judge([("blob", random_stitches(c, 6.0, 400, rng))], [big])
    assert len(dm["fail_chaos"]) >= 1 and ex["n_exempt"] == 0 and ex["chaos_after"] == ex["chaos_raw"]
    assert ex["n_radial_not_eligible"] == 1 and "not floret size" in ex["radial_parts_not_eligible"][0]["why"]
    dm2, ex2 = judge([("blob", rays(c, 6.0, n=90))], [big])                     # perfectly radial but too big: still chaos
    assert len(dm2["fail_chaos"]) >= 1 and ex2["n_exempt"] == 0
    segs = random_stitches(c, 6.0, 400, np.random.default_rng(1))
    plan = ObjectPlan(name="t", parts=[big])
    ra = blossom.radial_adherence(plan, segs, ["blob"] * len(segs), (ORIGIN[0], ORIGIN[1], ORIGIN[0] + SIZE, ORIGIN[1] + SIZE))
    assert not ra["ok"] and ra["pct_within"] < 85.0


def test_floret_size_parts_with_random_stitches_are_not_exempt():
    """review (ii): the adherence condition carries the exemption; without it random stitches in floret-size parts pass"""
    rng = np.random.default_rng(2); parts, groups = floret_tile(0, 0)
    groups = [(pid, random_stitches(p.meta["centre"], 2.8, 60, rng)) for (pid, _), p in zip(groups, parts)]
    dm, ex = judge(groups, parts)
    assert len(dm["fail_chaos"]) == 1 and ex["n_exempt"] == 0
    assert ex["n_refused"] == 1 and "adherence" in ex["candidates_refused"][0]["why"]


def test_tile_under_70_pct_radial_is_not_exempt():
    """review (iii): half the tile's visible thread is a random-angle fill -> not exempt; the florets alone are"""
    rng = np.random.default_rng(3); cx, cy = at(0, 0)
    parts = [floret("f0", (cx, cy), 2.8)]; groups = [("f0", rays((cx, cy), 2.8))]
    filler = fill("can", box(cx - 4, cy - 4, cx + 4, cy + 4))
    cen = [p.meta["centre"] for p in parts]
    ring = [s for s in random_stitches((cx, cy), 5.6, 4000, rng)
            if abs((s[0] + s[2]) / 2 - cx) < 4 and abs((s[1] + s[3]) / 2 - cy) < 4
            and min(math.dist(((s[0] + s[2]) / 2, (s[1] + s[3]) / 2), q) for q in cen) > 3.0]
    dm, ex = judge([("can", ring)] + groups, parts + [filler])
    assert len(dm["fail_chaos"]) == 1
    sh = (ex["candidates_refused"] + ex["exempt"])[0]["share"]
    assert 0.3 < sh < 0.70, f"fixture should be between 30 and 70 % radial, got {sh}"
    assert ex["n_exempt"] == 0 and "radial share" in ex["candidates_refused"][0]["why"]
    dm2, ex2 = judge(groups, parts)                                           # the same florets without the fill: exempt
    assert ex2["n_exempt"] == 1


def test_part_without_centre_and_non_radial_mode_are_not_eligible():
    parts, groups = floret_tile(0, 0)
    noc = [floret(p.id, p.meta["centre"], 2.8, centre=False) for p in parts]
    dm, ex = judge(groups, noc)
    assert ex["n_exempt"] == 0 and ex["eligible_parts"] == 0 and all(r["why"] == "no centre" for r in ex["radial_parts_not_eligible"])
    fixed = [Part(id=p.id, kind="floret", geom=p.geom, thread="x", z=0, dir=DirSpec(0.0, source="splitter"), meta=dict(p.meta)) for p in parts]
    dm, ex = judge(groups, fixed)
    assert ex["n_exempt"] == 0 and ex["eligible_parts"] == 0


def test_tiles_map_through_the_crop_origin():
    """a floret tile in the SECOND tile column is exempt there, and a chaotic non-radial tile next to it is not"""
    rng = np.random.default_rng(4)
    parts, groups = floret_tile(1, 0)
    c = at(0, 1); junk = fill("junk", box(c[0] - 4, c[1] - 4, c[0] + 4, c[1] + 4))
    dm, ex = judge(groups + [("junk", random_stitches(c, 5.0, 300, rng))], parts + [junk])
    assert len(dm["fail_chaos"]) == 2
    assert [tuple(t["at_mm"]) for t in ex["exempt"]] == [(12.0, 4.0)] and ex["chaos_after"] == 1


def test_house_numbers_and_threshold_unchanged():
    d = GR.config(Rulebook())
    assert (d["min_radial_share"], d["min_adherence_pct"], d["floret_r_max_mm"], d["max_dev_deg"]) == (0.70, 85.0, 4.0, 15.0)
    b = json.load(open(os.path.join(os.path.dirname(__file__), "..", "projects", "castle-falls-jacket", "bench", "bench.json")))
    assert b["targets"]["direction_pct_chaos_max"] == 5.0


def _row(pct_raw, ex=None):
    row = dict(direction=dict(tiles=100, pct_ok=50.0, pct_chaos=pct_raw), angle_coherence=dict(ok=False),
               density=dict(flags=0), trims=dict(per_100cm2=0), satin=dict(blob=0, too_wide=0, too_narrow=0),
               stack=dict(max=1), colours=dict(threads_in_file=12, red=True, gold=True))
    if ex is not None: row["radial_exemption"] = ex
    return row


def test_verdict_reads_chaos_after_exemption_at_the_same_threshold():
    T = dict(direction_pct_ok_min=85.0, direction_pct_chaos_max=5.0, stack_max_layers=2, trims_per_100cm2_max=25, satin_blobs_max=0,
             colours_max=12, density_flags_max=0)
    assert not bench.verdict(_row(12.0), T)["direction_chaos"]
    assert bench.verdict(_row(12.0, dict(pct_chaos_after=4.0, pct_chaos_raw=12.0, n_exempt=8)), T)["direction_chaos"]
    assert not bench.verdict(_row(12.0, dict(pct_chaos_after=6.0, pct_chaos_raw=12.0, n_exempt=6)), T)["direction_chaos"]
    assert not bench.verdict(_row(3.0, dict(pct_chaos_after=5.1, pct_chaos_raw=5.1, n_exempt=0)), T)["direction_chaos"]


def test_exempt_tiles_go_to_their_own_bucket_never_independent_ok():
    parts, groups = floret_tile(0, 0)
    dm, ex = judge(groups, parts)
    by = {"independent": dict(tiles=10, ok=5, dev=2, chaos=3, pct_ok=50.0, pct_chaos=30.0)}
    GR.tag_buckets(ex, lambda c: parts[0])                                     # the floret's own bucket is "independent"
    assert ex["exempt"][0]["bucket"] == "independent"
    out = GR.rebucket(by, ex)
    assert out["radial"]["tiles"] == 1 and out["radial"]["ok"] == 0
    assert out["independent"]["ok"] == 5 and out["independent"]["tiles"] == 9 and out["independent"]["chaos"] == 2
    assert sum(v["tiles"] for v in out.values()) == 10                         # a partition: no tile counted twice
    with pytest.raises(ValueError):
        GR.rebucket(by, dict(exempt=[dict(at_mm=(4, 4))]))                     # an untagged tile is an error, not a guess


def test_panel_and_scoreboard_show_raw_and_after():
    """the real title / scoreboard builders (a first version crashed in panel.fields with the bench.json labels)"""
    from digitize import panel
    b = json.load(open(os.path.join(os.path.dirname(__file__), "..", "projects", "castle-falls-jacket", "bench", "bench.json")))
    ex = dict(pct_chaos_after=21.0, pct_chaos_raw=24.8, n_exempt=23)
    row = _row(24.8, ex)
    row["direction"].update(n_dev=3, pct_ok_all_stitches=40.0); row.update(crop_min_closeup_weight=0.65, stitches_in_crop=1000, date="d", label="l")
    row["trims"].update(trims=5, area_cm2=1.0); row["density"].update(mean=4.0, p95=8.0, threshold=7.0, covered_cm2=1.0, over_cm2=0.0)
    row["satin"].update(satins=1, fans=0); row["stack"].update(over_cm2=0.0); row["angle_coherence"].update(fails=1)
    row["verdict"] = {"direction_chaos": False}
    for L in (panel.labels(row, b), panel.labels(row, dict(b, panel_labels={}))):
        assert "24.8% raw" in L["heat"] and "after it 21.0" in L["heat"] and "23 tiles" in L["heat"], L["heat"]
    md = bench.md_row(row)
    assert "24.8 raw; 21.0 after radial exemption (23 tiles)" in md
    plain = _row(24.8); plain.update({k: row[k] for k in row if k not in ("direction", "radial_exemption")}); plain["direction"] = dict(row["direction"])
    assert "| 24.8 |" in bench.md_row(plain) and "raw" not in panel.labels(plain, b)["heat"]   # no exemption: unchanged


# ---------------------------------------------------------------- crown clumps (extract/splitters/crown.py)
from shapely.geometry import Polygon
from digitize.schema import ObjectPlan
from digitize.direction import axial_diff
from digitize import audit


def _crown(paint):
    from test_digitize_m3b import _canvas, _ctx, _paint
    from digitize.extract.splitters import crown
    x, y, rgb = _canvas(70, 45)
    paint(x, y, rgb, _paint)
    ctx, ev = _ctx(rgb, (0, 0, 70, 45))
    claim = np.isin(ev.tone, [ev.keys.index("cf_grndk"), ev.keys.index("cf_grn")])
    parts, _ = crown.split(ctx, {"id": "foliage", "tones": ["cf_grndk", "cf_grn"]}, 2.0, claim)
    return parts, ctx.stats["foliage"]


def _two_clumps(x, y, rgb, P):
    """a slanted clump and a wide one touching it: their own long axes are ~55-65 deg apart"""
    tall = (np.abs((x - 14) - (29 - y) * 0.6) < 5) & (y > 2) & (y <= 29); wide = (x >= 12) & (x < 62) & (y > 28) & (y < 40)
    P(rgb, tall | wide, "cf_grndk")
    P(rgb, (np.hypot(x - 22, (y - 14) / 2.0) < 3.0), "cf_grn")              # one lit top per clump
    P(rgb, (np.hypot((x - 45) / 2.5, y - 32) < 3.0), "cf_grn")


def test_crown_fan_is_smooth_across_touching_clumps_and_lit_shares_it():
    """rule 2: one deliberate angle per clump (dark AND its lit side), a smooth fan across the crown: touching clumps whose
    own axes are ~90 deg apart end up closer; every angle rebuilds in the audit. Mutations: (a) smoothing off -> red;
    (b) lit pieces keep their own long axis -> red."""
    from digitize.extract.splitters import crown
    parts, st = _crown(_two_clumps)
    dark = [p for p in parts if p.kind == "crown_clump_dark"]; lit = [p for p in parts if p.kind == "crown_clump_lit"]
    assert len(dark) == 2 and len(lit) >= 2, (len(dark), len(lit))
    own = [crown.smooth_angle(p.meta["construct"]["axes"][:1]) for p in dark]
    raw, smooth = axial_diff(*own), axial_diff(dark[0].dir.angle, dark[1].dir.angle)
    assert raw > 45 and smooth < raw - 15, (raw, smooth)
    for l in lit:
        d = next(p for p in dark if p.id == l.meta["lit_of"])
        assert axial_diff(l.dir.angle, d.dir.angle) < 0.01, (l.dir.angle, d.dir.angle)
    assert audit.angle_audit(ObjectPlan(name="t", parts=parts), Rulebook())["random_angles"] == 0
    assert st["smoothed"] == 2


def _specks(x, y, rgb, P):
    """one clump with a big lit top and a small (~10 mm2) lit speck near its edge"""
    m = (x > 10) & (x < 50) & (y > 10) & (y < 32)
    P(rgb, m, "cf_grndk")
    P(rgb, (np.hypot((x - 22) / 2, y - 18) < 3.5), "cf_grn")
    P(rgb, (np.hypot(x - 42, y - 27) < 1.8), "cf_grn")


def test_small_lit_highlight_is_grown_to_a_visible_size_not_dropped():
    """fidelity first (A11): a lit speck too small to hold a visible tatami (< 20 mm2 or < 2.5 mm wide) is GROWN inside its
    clump, never dropped; lit and dark do not overlap. Mutations: (a) small pieces dropped -> red; (b) growth off -> red."""
    parts, st = _crown(_specks)
    lit = [p for p in parts if p.kind == "crown_clump_lit"]; dark = [p for p in parts if p.kind == "crown_clump_dark"]
    near = [p for p in lit if p.geom.distance(Point(42, 27)) < 0.5]
    assert near, "the small highlight was dropped"
    sp = near[0].geom
    assert sp.area >= 20.0 - 0.5 and not sp.buffer(-1.2).is_empty, (sp.area,)
    assert st["lit_grown"] >= 1
    from shapely.ops import unary_union
    for d in dark:
        mine = [p.geom for p in lit if p.meta["lit_of"] == d.id]
        assert unary_union(mine).intersection(d.geom).area < 0.5


def _edge_lit(x, y, rgb, P):
    """a lit top 0.3 mm short of the clump's edge: the dark between them is a sliver"""
    m = (x > 10) & (x < 50) & (y > 10) & (y < 32)
    P(rgb, m, "cf_grndk")
    P(rgb, m & (x > 14) & (x < 30) & (y > 10.3) & (y < 18), "cf_grn")


def test_dark_slivers_join_the_lit_piece():
    """a dark sliver (< 0.5 mm) between a lit piece and the clump edge sews as short edge stitches at every angle (part of
    the M3b angle spread): it joins the lit piece; lit and dark do not overlap. Mutation (sliver step off) -> red."""
    parts, st = _crown(_edge_lit)
    dark = [p for p in parts if p.kind == "crown_clump_dark"][0]
    lit = [p for p in parts if p.kind == "crown_clump_lit"]
    opened = dark.geom.buffer(-0.25).buffer(0.25)
    assert dark.geom.difference(opened).area < 0.6, dark.geom.difference(opened).area
    from shapely.ops import unary_union
    whole = unary_union([dark.geom] + [p.geom for p in lit])
    assert abs(whole.area - (dark.geom.area + sum(p.geom.area for p in lit))) < 0.5        # no overlap
    assert st["slivers_to_lit_mm2"] > 0


def test_fan_smooth_is_rebuilt_by_the_audit_and_reported_as_outline():
    """the smoothed angle is RE-BUILT from the stored axes (a typed-in angle is random, A23); a dark clump whose own axis
    starts far from it does not touch its support; a neighbour axis 40 mm away is not a neighbour; a lit piece must hold
    its `at` point; the bucket is outline (A24). Mutations: (a) audit trusts the declared angle -> red; (b) neighbour
    distance check off -> red; (c) fan_smooth removed from OUTLINE_RULES -> red."""
    from digitize.extract.splitters import crown
    g = Polygon([(0, 0), (12, 0), (12, 6), (0, 6)])
    own = {"from": [0.5, 3.0], "to": [6.0, 3.0], "w": 72.0}; nb = {"from": [14.0, 0.0], "to": [14.0, 6.0], "w": 20.0}
    far = {"from": [52.0, 0.0], "to": [52.0, 3.0], "w": 20.0}
    def mk(pid, ang, axes, kind="crown_clump_dark", **m):
        return Part(id=pid, kind=kind, geom=g, thread="t", z=2, dir=DirSpec(ang, source="splitter"),
                    meta=dict(construct=dict(rule="fan_smooth", axes=axes, **m)))
    a = crown.smooth_angle([own, nb]); assert 0 < a < 90
    good = mk("good", a, [own, nb]); forged = mk("forged", a + 30.0, [own, nb])
    far_nb = mk("far", crown.smooth_angle([own, far]), [own, far])
    unsupported = mk("unsup", 0.0, [{"from": [-20.0, 3.0], "to": [6.0, 3.0], "w": 72.0}])
    lit_ok = mk("lit", a, [own, nb], kind="crown_clump_lit", at=[3.0, 3.0]); lit_noat = mk("lit_noat", a, [own, nb], kind="crown_clump_lit")
    r = audit.angle_audit(ObjectPlan(name="t", parts=[good, forged, far_nb, unsupported, lit_ok, lit_noat]), Rulebook())
    assert {b["part"] for b in r["unexplained"]} == {"forged", "far", "unsup", "lit_noat"}, r["unexplained"]
    assert audit.bucket_of(good) == "outline" and audit.bucket_of(lit_ok) == "outline"


def test_dark_clump_axis_middle_may_sit_in_its_own_lit_piece():
    """the clump's axis middle can fall in a lit piece knocked out of the dark (M4c crop r1: foliage.216 counted as a
    random angle). The audit checks the dark's own axis against the dark part PLUS the lit pieces that name it in lit_of
    (plan peers), never a stranger's. Mutation (peers ignored) -> red."""
    from digitize.extract.splitters import crown
    clump = Polygon([(0, 0), (16, 0), (16, 6), (0, 6)]); hole = Polygon([(5, 0), (11, 0), (11, 6), (5, 6)])
    own = {"from": [0.5, 3.0], "to": [8.0, 3.0], "w": 96.0}
    a = crown.smooth_angle([own])
    dark = Part(id="d", kind="crown_clump_dark", geom=clump.difference(hole), thread="t", z=2, dir=DirSpec(a, source="splitter"),
                meta=dict(construct=dict(rule="fan_smooth", axes=[own])))
    lit = Part(id="l", kind="crown_clump_lit", geom=hole, thread="u", z=1.7, dir=DirSpec(a, source="splitter"),
               meta=dict(lit_of="d", construct=dict(rule="fan_smooth", axes=[own], at=[8.0, 3.0])))
    stranger = Part(id="s", kind="crown_clump_lit", geom=hole, thread="u", z=1.7, dir=DirSpec(a, source="splitter"),
                    meta=dict(lit_of="other", construct=dict(rule="fan_smooth", axes=[own], at=[8.0, 3.0])))
    assert audit.angle_audit(ObjectPlan(name="t", parts=[dark, lit]), Rulebook())["random_angles"] == 0
    r = audit.angle_audit(ObjectPlan(name="t", parts=[dark, stranger]), Rulebook())
    assert r["random_angles"] == 1 and r["unexplained"][0]["part"] == "d", r


def test_rule3_wins_over_smoothing(monkeypatch):
    """a clump that rule 3 cannot separate from its smoothed neighbours keeps its OWN fan axis (crop r1: smoothing alone
    took the crown's close pairs 4 -> 10). Mutation (fallback off) -> red."""
    from digitize import direction as DR
    from digitize.extract.splitters import crown
    real = DR.separate
    def fake(parts, sep=(15.0, 25.0), **k):
        out = real(parts, sep, **k)
        for p in parts[:1]: p.meta["sep_unresolved"] = "x"                 # the first clump cannot be separated
        return out
    monkeypatch.setattr(DR, "separate", fake)
    parts, st = _crown(_two_clumps)
    dark = [p for p in parts if p.kind == "crown_clump_dark"]
    lone = [p for p in dark if len(p.meta["construct"]["axes"]) == 1]
    assert st["unsmoothed_rule3"] >= 1 and len(lone) == 1, st
    assert abs(lone[0].dir.angle - round(crown.smooth_angle(lone[0].meta["construct"]["axes"]), 2)) < 0.01
    assert audit.angle_audit(ObjectPlan(name="t", parts=parts), Rulebook())["random_angles"] == 0
