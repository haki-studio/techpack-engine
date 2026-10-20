"""ENGINE_PLAN M3a: constructed parts (buildings). Building template fitter (extract/building_fit.py) + splitter
(extract/splitters/building.py) on synthetic buildings, the audit's construct basis, and the two sequence.py hooks.
Each guard was proven RED by a mutation of the code it guards (scratchpad m3a/mutate_m3a.py, listed in
RECAP-2026-10-20-engine-m3a.md) and is GREEN on this branch."""
import math
import numpy as np
import pytest
from shapely.geometry import Polygon, box, Point, LineString
import qa
from digitize.schema import Part, DirSpec, ObjectPlan
from digitize.rulebook import Rulebook
from digitize import audit, sequence, techniques
from digitize import direction as DR
from digitize.extract import building_fit as BF

PAL = {"n": "#22355C", "b": "#3F6FA9", "c": "#EEEAE0", "d": "#4E3F31", "g": "#D3A63F", "r": "#B23F2E", "f": "#5A7240"}
ROLES = {"roof": ["n", "b"], "wall": ["c", "d"], "member": ["r"], "ornament": ["g"]}
PPM = 12.0


def _hex(h): h = h.lstrip("#"); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)


def _paint(W, H, layers):
    """layers: [(tone key, shapely geometry)] painted in order over foliage, at 12 ppm -> (rgb, grey)"""
    from digitize.direction import raster
    rgb = np.empty((int(H * PPM), int(W * PPM), 3)); rgb[:] = _hex(PAL["f"])
    for k, g in layers:
        m = raster(g, (0, 0, W, H), PPM)[: rgb.shape[0], : rgb.shape[1]]
        rgb[m] = _hex(PAL[k])
    grey = rgb @ np.array([0.299, 0.587, 0.114])
    return rgb, grey


def _ctx(rgb, grey, W, H, **bcfg):
    from digitize.extract import evidence
    from digitize.extract.splitters import Ctx
    from digitize import config
    ref = dict(bounds=(0, 0, W, H), ppm=PPM, rgb=rgb, grey=grey, closeup_weight=np.ones(grey.shape))
    ev = evidence.build(ref, PAL, ppm=4.0)
    cfg = config.merge(config.DEFAULTS, {"building": dict(roles=ROLES, **bcfg)})
    return Ctx(ev, Rulebook(), cfg, {k: k for k in PAL}, []), ev


ROOF_NEAR = Polygon([(10, 36), (26, 10), (54, 10), (70, 36)])            # 26 mm tier: NEAR (house near_tier_mm 22)


def _near_scene(occlude=None):
    """a near temple: trapezoid roof (navy, light-blue tile streaks down the slope), cream wall with a row of four dark
    windows and a red post, two gold studs above the ridge, a gold ornament blob above the right end"""
    W, H = 80, 64
    streaks = [box(x, 12, x + 0.8, 34) for x in np.arange(28, 52, 3.0)]
    layers = [("c", box(14, 36, 66, 52)), ("n", ROOF_NEAR)] + [("b", s.intersection(ROOF_NEAR)) for s in streaks]
    layers += [("d", box(x, 42, x + 2.5, 44.5)) for x in (20, 25, 30, 35)]
    layers += [("r", box(60, 37, 61.5, 51)), ("g", Point(30, 7.5).buffer(0.8)), ("g", Point(50, 7.5).buffer(0.8)),
               ("g", box(58, 2, 63, 5))]
    rgb, grey = _paint(W, H, layers)
    ctx, ev = _ctx(rgb, grey, W, H)
    claim = np.ones((ev.H, ev.W), bool)
    if occlude is not None: claim &= ~ev.mask(occlude)                  # a higher zone (blossom) took these pixels
    return ctx, ev, claim, {"id": "bld", "geoms": [box(0, 0, W, H)]}


def _split(ctx, zone, claim):
    from digitize.extract.splitters import building
    return building.split(ctx, zone, 5.0, claim)


# ================================================================== the fitter on a near building
def test_near_building_parts_follow_the_rule_tables():
    """rule 2 + playbook on a synthetic near temple: roof planes down the slope (front perpendicular to the eave, hips
    fanned 20 deg to their own side), the wall square to the eave of the roof above (near: across the courses), a row of
    windows as ONE satin band across it in the window tone, the red post a member satin across its width, an eave satin
    and bean tile lines in the second roof tone, studs 1-1.5 mm in gold. Every angle is source "rule" and the audit
    re-derives all of them (random_angles 0); same-thread neighbours are >= 15 deg apart (rule 3).
    Mutations (front plane along the eave; hips not fanned; wall along the courses under a near roof) -> red."""
    ctx, ev, claim, zone = _near_scene()
    parts, used = _split(ctx, zone, claim)
    by = {}
    for p in parts: by.setdefault(p.kind, []).append(p)
    assert {"roof", "wall", "eave", "roof_tile_line", "window", "member", "stud"} <= set(by), sorted(by)
    roofs = {p.meta["side"]: p for p in by["roof"]}
    assert set(roofs) == {-1, 0, 1}, [(p.meta["side"], p.geom.bounds) for p in by["roof"]]
    assert abs(roofs[0].dir.angle - 90.0) < 2.0, roofs[0].dir
    assert 108.0 <= roofs[-1].dir.angle <= 135.0 and 45.0 <= roofs[1].dir.angle <= 72.0, (roofs[-1].dir, roofs[1].dir)
    assert all(p.thread == "n" and p.dir.source == "rule" for p in by["roof"])
    wall = max(by["wall"], key=lambda p: p.area)
    assert wall.thread == "c" and abs(wall.dir.angle - 90.0) < 2.0, wall.dir        # near roof above: across the courses
    (win,) = by["window"]
    assert win.thread == "d" and win.meta["n_windows"] == 4 and abs(win.dir.angle - 90.0) < 1.0
    L = math.dist(*win.meta["cl"]); assert L / (win.meta["w"] + 0.25) >= 3.0 and 1.0 <= win.meta["w"] <= 7.0
    (mem,) = by["member"]
    assert mem.thread == "r" and DR.axial_diff(mem.dir.angle, 0.0) < 2.0, mem.dir   # vertical post: satin across = 0 deg
    assert all(t.thread == "b" for t in by["roof_tile_line"]) and len(by["roof_tile_line"]) >= 1   # planes with a second roof tone
    for t in by["roof_tile_line"]:
        assert t.dir.angle == next(p for p in by["roof"] if p.id == t.meta["plane"]).dir.angle
    (eave,) = by["eave"]
    assert eave.thread == "b" and abs(eave.dir.angle - 90.0) < 2.0
    studs = by["stud"]
    assert all(p.thread == "g" and 1.0 <= p.meta["knots"][0][2] <= 1.5 for p in studs) and len(studs) >= 3
    assert audit.angle_audit(ObjectPlan(name="t", parts=parts), Rulebook())["random_angles"] == 0
    assert DR.separation_report(parts)["close"] == 0, DR.separation_report(parts)
    assert not used[ev.tone == ev.keys.index("f")].any()                 # foliage pixels go back to the zones below


def test_building_z_order_walls_roofs_eaves_tiles_windows_studs():
    """playbook: build walls -> roofs bottom-up -> eaves -> tile lines -> windows / members -> studs last, through the
    z values the EXISTING sequence.py z-DAG reads (no sequence rewrite). Mutation (studs below windows) -> red."""
    ctx, ev, claim, zone = _near_scene()
    parts, _ = _split(ctx, zone, claim)
    z = {k: {p.z for p in parts if p.kind == k} for k in ("wall", "roof", "eave", "roof_tile_line", "window", "member", "stud")}
    order = ["wall", "roof", "eave", "roof_tile_line", "window", "stud"]
    for a, b in zip(order, order[1:]):
        assert max(z[a]) < min(z[b]), (a, z[a], b, z[b])
    assert max(z["member"]) < min(z["stud"])
    stops = sequence.order(parts)
    seq = [pid for s in stops for pid in s["parts"]]; pos = {pid: i for i, pid in enumerate(seq)}
    kind = {p.id: p.kind for p in parts}
    wall = [pos[i] for i in pos if kind[i] == "wall"]; roof = [pos[i] for i in pos if kind[i] == "roof"]
    win = [pos[i] for i in pos if kind[i] == "window"]
    assert max(wall) < min(roof) and max(roof) < min(win), (wall, roof, win)
    # M4g hint contract (optional meta): one group per building; tile lines / eaves sew after the plane(s) they lie on
    ids = {p.id for p in parts}
    assert {p.meta.get("group") for p in parts} == {"bld.b0"}
    for p in parts:
        if p.kind in ("roof_tile_line", "eave"):
            assert p.meta["seq_after"] and set(p.meta["seq_after"]) <= ids and all(kind[i] == "roof" for i in p.meta["seq_after"])


def test_studs_never_touch_each_other():
    """rule 3 / rule 9: an ornament too big for one stud becomes a chain of 1-1.5 mm studs whose centres are at least
    max_d + 0.5 mm apart, so no two same-thread studs touch (separation would flag them at 0 deg). Mutation (old
    chain count int(L // pitch) + 1) -> red."""
    ctx, ev, claim, zone = _near_scene()
    parts, _ = _split(ctx, zone, claim)
    studs = [p for p in parts if p.kind == "stud"]
    for i, a in enumerate(studs):
        for b in studs[i + 1:]:
            assert a.geom.distance(b.geom) > 0.3, (a.meta["knots"], b.meta["knots"])


# ================================================================== far tier (rule 3 depth)
def _two_buildings(k=1.0):
    """one zone, two building windows: a big near temple (26 mm tier) and a small far house (8 mm tier, eave sloped 5
    deg) with a wall under it; every length scaled by k"""
    s = math.tan(math.radians(5.0)); W, H = 160 * k, 64 * k
    sc = lambda g: __import__("shapely.affinity", fromlist=["scale"]).scale(g, k, k, origin=(0, 0))
    big = Polygon([(10, 36), (26, 10), (54, 10), (70, 36)])
    small = Polygon([(90, 22), (150, 22 + 60 * s), (150, 30 + 60 * s), (90, 30)])
    wall = Polygon([(92, 30), (148, 30 + 56 * s), (148, 42 + 56 * s), (92, 42)])
    rgb, grey = _paint(W, H, [("c", sc(box(14, 36, 66, 52))), ("n", sc(big)), ("c", sc(wall)), ("n", sc(small))])
    ctx, ev = _ctx(rgb, grey, W, H)
    zone = {"id": "bld", "geoms": [sc(box(0, 0, 80, 64)), sc(box(80, 0, 160, 64))]}
    return _split(ctx, zone, np.ones((ev.H, ev.W), bool))[0]


def test_far_tier_is_relative_to_the_largest_tier_and_runs_along_its_eave():
    """rule 3 depth RELATIVE to scale (review of PR #9: an absolute 22 mm was picked on the crop): roof tiers of one
    style shrink with distance, so a tier under near_tier_rel x the zone's largest tier is FAR: one plane with rows
    ALONG its fitted eave (here sloped 5 deg), no tile lines; the wall under it runs along the courses; the big tier
    stays near (down the slope). The same scene at half size classifies the same way (scale-invariant). Mutations
    (depth rule ignored; an absolute mm threshold) -> red."""
    for k in (1.0, 0.5):
        parts = _two_buildings(k)
        roofs = [p for p in parts if p.kind == "roof"]
        far = [p for p in roofs if p.meta["building"] == 1]; near = [p for p in roofs if p.meta["building"] == 0]
        assert len(far) == 1 and far[0].meta["far"] and abs(far[0].dir.angle - 5.0) < 1.5, (k, [(p.dir.angle, p.meta.get("tier_h_mm")) for p in roofs])
        assert near and not any(p.meta["far"] for p in near) and any(abs(p.dir.angle - 90.0) < 2 for p in near), (k, [p.dir for p in near])
        assert not [p for p in parts if p.kind == "roof_tile_line" and p.meta["building"] == 1]
        wall = max([p for p in parts if p.kind == "wall" and p.meta["building"] == 1], key=lambda p: p.area)
        assert abs(wall.dir.angle - 5.0) < 1.5, (k, wall.dir)
        assert audit.angle_audit(ObjectPlan(name="t", parts=parts), Rulebook())["random_angles"] == 0


# ================================================================== occlusion
def test_occluded_eave_is_not_fitted():
    """a blossom crown (another zone, higher) covering the left 40 % of the eave raises the roof's bottom edge there; that
    edge is the blossom's, not the roof's, so the eave line is fitted on the unoccluded columns only (eave points all at
    the real eave, front plane exactly down the slope). Mutation (occlusion ignored: every bottom pixel fitted) -> red."""
    occ = box(0, 28, 34, 64)
    ctx, ev, claim, zone = _near_scene(occlude=occ)
    from digitize.extract.splitters import building
    sc = building._cfg(ctx)
    roof = np.isin(ev.tone, [ev.keys.index("n"), ev.keys.index("b")]) & claim
    from scipy import ndimage as ndi
    lab, n = ndi.label(roof); comp = lab == np.bincount(lab.ravel())[1:].argmax() + 1
    fit = BF.fit_roof(ev, comp, sc, free=claim)
    assert fit["eave_visible"] and max(abs(y - 36.0) for _, y in fit["eave_pts"]) < 0.6, fit["eave_pts"][:6]
    assert abs(BF.eave_angle(fit["eave_pts"])) < 1.0


def test_split_tiers_cuts_stacked_roofs_joined_by_a_post():
    """two roof tiers joined by a 1 mm blue post read as one component; the rows where < 25 % of the component is roof,
    with full roof rows above and below, are the gap: two tiers after the cut. Mutation (no cut) -> red."""
    m = np.zeros((80, 100), bool); m[10:30, 10:90] = True; m[50:70, 5:95] = True; m[30:50, 48:52] = True
    from scipy import ndimage as ndi
    assert ndi.label(m)[1] == 1 and ndi.label(BF.split_tiers(m))[1] == 2


# ================================================================== audit: construct basis
def _roof_part(angle, eave_pts, top_pts, side=0, hip_pts=None, kind="roof", **meta):
    return Part(id=f"{kind}{angle}", kind=kind, geom=box(0, 0, 40, 10), thread="n", z=5.1, dir=DirSpec(angle, source="rule"),
                meta=dict(eave_pts=eave_pts, top_pts=top_pts, hip_pts=hip_pts, side=side, **meta))


def test_construct_angles_are_rederived_from_the_fitted_points():
    """digitize.audit re-derives a constructed part's angle from the fitted points it stores (building_fit.rule_basis):
    a near roof plane over a horizontal eave must be 90, a far one 0, a wall under a near roof 90, a satin member its
    chord + 90. An angle typed into the part (60 on a near roof, 0 on a near wall) is counted as random.
    Mutations (audit hook trusts the declared angle; far / near swapped) -> red."""
    eave = [[x, 30.0] for x in range(0, 41, 4)]
    near_top = [[x, 4.0] for x in range(0, 41, 4)]; far_top = [[x, 24.0] for x in range(0, 41, 4)]
    ok = [_roof_part(90.0, eave, near_top), _roof_part(0.0, eave, far_top),
          Part(id="w", kind="wall", geom=box(0, 30, 40, 40), thread="c", z=5.0, dir=DirSpec(90.0), meta=dict(eave_pts=eave, top_pts=near_top)),
          Part(id="m", kind="member", geom=box(0, 0, 2, 10), thread="r", z=5.5, dir=DirSpec(0.0), meta=dict(cl=[[1, 0], [1, 10]], w=1.5))]
    assert audit.angle_audit(ObjectPlan(name="t", parts=ok), Rulebook())["random_angles"] == 0
    bad = [_roof_part(60.0, eave, near_top),
           Part(id="w", kind="wall", geom=box(0, 30, 40, 40), thread="c", z=5.0, dir=DirSpec(0.0), meta=dict(eave_pts=eave, top_pts=near_top))]
    r = audit.angle_audit(ObjectPlan(name="t", parts=bad), Rulebook())
    assert r["random_angles"] == 2, r
    bare = Part(id="x", kind="roof", geom=box(0, 0, 4, 4), thread="n", z=5.1, dir=DirSpec(90.0), meta={})
    assert audit.angle_audit(ObjectPlan(name="t", parts=[bare]), Rulebook())["random_angles"] == 1   # no points: no basis


def test_hip_planes_fan_within_house_limits():
    """near hip planes fan halfway between the front's fall line and their hip line, clamped to hip_min..hip_max off the
    front on their own side; far hips follow their hip line inside the same limits. Pure function of the points."""
    eave = [[x, 30.0] for x in range(0, 61, 5)]
    left = [[0.0, 30.0], [8.0, 15.0], [16.0, 0.0]]                       # rises to the right: a left hip edge (~118 deg)
    right = [[44.0, 0.0], [52.0, 15.0], [60.0, 30.0]]
    a_l, a_r = BF.roof_angle(eave, left, -1), BF.roof_angle(eave, right, 1)
    assert 110.0 <= a_l <= 135.0 and 45.0 <= a_r <= 70.0, (a_l, a_r)
    steep = [[0.0, 30.0], [1.0, 15.0], [2.0, 0.0]]                       # nearly vertical edge: clamp to the 20 deg minimum
    assert BF.roof_angle(eave, steep, -1) == pytest.approx(110.0, abs=0.01)
    f_l = BF.roof_angle(eave, left, -1, far=True)
    assert 135.0 <= f_l <= 160.0, f_l                                      # far: along the hip line, 20-45 deg off the eave


# ================================================================== satin features read back as strokes
def test_window_bands_read_back_as_strokes_not_blobs():
    """rule 4 / LESSONS A16: every window band the splitter makes must read back from its stitches as a satin column
    with aspect >= 2.5 (qa.satin_shape: 0 blobs). A band's width is capped at length / band_aspect MINUS the 0.25 mm a
    column reads back wider (pull comp both sides + grid). Mutation (no allowance for the sewn width) -> red."""
    from digitize.extract.splitters import building
    sc = dict(building.DEFAULTS); rb = Rulebook()
    blobs = 0; n = 0
    for L in np.arange(3.0, 7.01, 0.25):
        for h in (1.2, 1.6, 2.4):
            f = dict(geom=box(0, 0, L, h), course=0.0, thread="d")
            band = building._band([f], sc)
            if band is None: continue
            cl, w, th = band; n += 1
            p = Part(id="w", kind="window", geom=LineString(cl).buffer(w / 2, cap_style=2), thread="d", z=5.5,
                     dir=DirSpec(BF.across_angle(cl)), meta=dict(cl=[list(c) for c in cl], w=w, caps=["flat", "flat"]))
            p.technique = rb.technique_for("window"); p.stitch = rb.stitch_spec("window", p.technique)
            segs = [tuple(a) + tuple(b) for blk in techniques.get(p.technique).plan(p) for a, b in zip(blk.pts, blk.pts[1:]) if tuple(a) != tuple(b)]
            segs = [tuple(round(v, 1) for v in s) for s in segs]                 # the DST's 0.1 mm grid
            blobs += qa.satin_shape(segs)["counts"]["blob"]
    assert n >= 10 and blobs == 0, (n, blobs)


def test_satin_feature_is_clipped_clear_of_lower_underlaps():
    """rule 6: inside a wall plane, a satin band within seam_keep_mm of a LOWER region's border (a 1 mm underlap sits
    there) would be a third layer; its centreline is clipped to the stretch clear of it, and kept whole where only a
    HIGHER plane (the roof, which the wall runs under) is near. Mutation (no clearance from lower borders) -> red."""
    from digitize.extract.splitters import building
    from digitize.extract import evidence
    ev = type("E", (), dict(bounds=(0.0, 0.0, 40.0, 20.0), ppm=4.0))()
    lab = np.zeros((80, 160), np.int32); lab[8:72, 0:120] = 1; lab[0:8, 0:160] = 2   # wall (k=1), roof above (k=2), lower zone right of x=30
    zk = np.array([0.0, 5.0, 5.1])
    cl = [(2.0, 3.5), (29.5, 3.5)]                                                 # 1.5 mm below the roof, runs into the lower zone at x=30
    out = building._clear_cl(ev, lab, zk, cl, 0.85, 1.75)
    assert out is not None and out[0][0] <= 2.6 and 27.5 <= out[1][0] <= 28.4, out


# ================================================================== sequence hooks (additive, default-preserving)
def test_sequence_keeps_deliberate_small_parts():
    """a 1.5 mm stud (1.77 mm2) is a deliberate part: meta keep_small keeps it out of merge_specks (neither merged nor
    absorbing a speck) and meta min_fragment_mm2 keeps absorb_fragments from dropping it. Without the meta, the defaults
    are unchanged (merged / dropped). Mutations (either hook removed) -> red."""
    wall = Part(id="wall", kind="wall", geom=box(0, 0, 20, 20), thread="c", z=5.0, dir=DirSpec(0.0))
    stud = Part(id="stud", kind="stud", geom=Point(10, 10).buffer(0.75, 16), thread="g", z=5.6, dir=DirSpec(0.0),
                meta=dict(keep_small=True, min_fragment_mm2=0.5))
    plain = Part(id="plain", kind="stud", geom=Point(5, 5).buffer(0.75, 16), thread="g", z=5.6, dir=DirSpec(0.0))
    out, moves = sequence.merge_specks([wall, stud, plain], 20.0)
    assert "stud" in {p.id for p in out} and ("plain", "wall") in moves, moves
    kept, dropped = sequence.absorb_fragments([stud, Part(id="p2", kind="stud", geom=Point(5, 5).buffer(0.75, 16), thread="g", z=5.6,
                                                           dir=DirSpec(0.0))], 2.0)
    assert [p.id for p in kept] == ["stud"] and dropped == ["p2"]


def test_house_yaml_m3a_kinds_follow_the_playbook():
    """the M3a kinds in rules/house.yaml say what the playbook says: walls / roofs tatami by construct rules, eave /
    window / member satin (same-side density, column_satin first), tile lines bean, studs dot within the principles'
    stud_mm. Pinned so a rule change is a visible change."""
    rb = Rulebook(); K = rb.data["kinds"]; P = rb.principles
    assert K["wall"]["construct"] == "course" and K["roof"]["construct"] == "down_slope" and K["roof_tile_line"]["construct"] == "down_slope"
    assert all(K[k]["construct"] == "across" and K[k]["techniques"][0] == "column_satin" for k in ("eave", "window", "member"))
    assert rb.technique_for("roof_tile_line") == "bean" and rb.technique_for("wall") == "tatami" and rb.technique_for("stud") == "dot"
    lo, hi = P["stud_mm"]; sp = K["stud"]["params"]
    assert lo <= sp["min_d"] <= sp["max_d"] <= hi
    assert 15 <= K["roof"]["params"]["hip_min_sep"] <= K["roof"]["params"]["hip_max_sep"] <= 45


# ================================================================== PR #9 review fixes
def test_referenced_plane_survives_merge_specks():
    """review 1: a roof plane named in a tile line's / eave's seq_after must survive merge_specks, or the M4g sequencer
    meets an id that names no part (HintError). Here the referenced hip plane is shrunk to a 9 mm2 speck touching the
    wall, which merge_specks WOULD merge: protect_referenced keeps it, and every seq_after id still resolves.
    Mutation (protect_referenced a no-op) -> red."""
    ctx, ev, claim, zone = _near_scene()
    parts, _ = _split(ctx, zone, claim)
    ref = {i for p in parts for i in (p.meta.get("seq_after") or [])}
    byid = {p.id: p for p in parts}
    hip = next(byid[i] for i in sorted(ref) if byid[i].kind == "roof" and byid[i].meta["side"] != 0)
    wall = max([p for p in parts if p.kind == "wall"], key=lambda p: p.area)
    x0, y0, x1, y1 = wall.geom.bounds
    hip.geom = box(x0 - 3.0, y0, x0, y0 + 3.0)                        # a speck touching the wall's corner
    out, moves = sequence.merge_specks(parts, 20.0)
    ids = {p.id for p in out}
    assert hip.id in ids, moves
    assert all(set(p.meta.get("seq_after") or []) <= ids for p in out)


def _wall_scene(layers, W=80, H=64, **bcfg):
    rgb, grey = _paint(W, H, layers)
    ctx, ev = _ctx(rgb, grey, W, H, **bcfg)
    return ctx, ev, np.ones((ev.H, ev.W), bool), {"id": "bld", "geoms": [box(0, 0, W, H)]}


def test_details_are_kept_at_underlaps_and_small_ones_are_suggested():
    """review 2 (fidelity first): a row of windows on the wall's lower edge (a 1 mm underlap with the zone below lies
    there) is KEPT by default (the stack cost is reported, the sequencer cuts it); a single window too small for a
    satin band is not silently dropped: it is listed in report["suggest"] (plan meta building_suggest).
    Mutations (underlap clearance on by default; suggestion not recorded) -> red."""
    layers = [("c", box(14, 36, 66, 52)), ("n", ROOF_NEAR)] + [("d", box(x, 49.5, x + 2.5, 52)) for x in (20, 25, 30, 35)]
    layers += [("d", box(55, 42, 57, 44))]
    ctx, ev, claim, zone = _wall_scene(layers)
    parts, _ = _split(ctx, zone, claim)
    wins = [p for p in parts if p.kind == "window"]
    assert any(p.meta.get("n_windows") == 4 for p in wins), [(p.meta.get("n_windows"), p.meta["cl"]) for p in wins]
    sug = ctx.building_report["suggest"]
    assert any(s["kind"] == "window" and abs(s["at"][0] - 56) < 1.5 and abs(s["at"][1] - 43) < 1.5 for s in sug), sug


def test_wall_ground_is_the_plaster_not_the_frame():
    """review 4: a plaster wall drawn with a heavy red timber frame (red is ~70 % of the face) takes the PLASTER as its
    ground (the mean of its brightest pixels, nearest thread), and the frame becomes members: rails along the courses
    (satin across = 90 deg) and posts across them (0 deg), not one red wall slab. Mutations (ground = the most frequent
    thread; no frame decomposition) -> red."""
    layers = [("c", box(14, 20, 66, 36))]
    layers += [("r", box(14, y, 66, y + 2.5)) for y in (20, 25, 30, 33.5)]
    layers += [("r", box(x, 20, x + 3.0, 36)) for x in (14, 26, 38.5, 51, 63)]
    ctx, ev, claim, zone = _wall_scene(layers)
    parts, _ = _split(ctx, zone, claim)
    wall = max([p for p in parts if p.kind == "wall"], key=lambda p: p.area)
    assert wall.thread == "c", wall.thread
    mem = [p for p in parts if p.kind == "member" and p.thread == "r"]
    rails = [p for p in mem if DR.axial_diff(p.dir.angle, 90.0) < 5]; posts = [p for p in mem if DR.axial_diff(p.dir.angle, 0.0) < 5]
    assert len(rails) >= 3 and len(posts) >= 3, [(p.dir.angle, p.meta["cl"]) for p in mem]
