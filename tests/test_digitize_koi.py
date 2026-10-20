"""Koi engine trial (tag koi, 2026-10-20): the guards added for the first real-design trial of the parts-based engine on
Koi Blossom (projects/koi-blossom-hoodie/bench/TRIAL.md). Each was proven red by a mutation (listed in the PR and in
RECAP-2026-10-20-engine-trial-koi.md), then green."""
import math, os, sys
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

from shapely.geometry import Polygon, box
from digitize.schema import Part, DirSpec


# ------------------------------------------------------------------ lily: the petal fan
def _fan(n_petals=5, R=20.0, r_w=0.35, seed=0):
    """pixels (theta deg, r mm) of a synthetic n-petal flower: petal k is a lobe around angle k*360/n reaching R"""
    rng = np.random.default_rng(seed); th = rng.uniform(0, 360, 60000); r = rng.uniform(0, R, 60000)
    tips = np.arange(n_petals) * 360.0 / n_petals + 10.0
    d = np.min(np.abs(((th[:, None] - tips[None]) + 180) % 360 - 180), axis=1)
    reach = R * np.clip(1 - (d / (360.0 / n_petals / 2)) ** 2 / (1 - r_w), 0.25, 1)   # each petal narrows to its tip
    keep = r <= reach
    return th[keep], r[keep], tips


def test_lily_petal_fan_finds_each_petal_and_its_tip():
    """a 5-petal fan seen from its heart -> 5 sectors whose tips lie on the petal axes (within 6 deg), every pixel in a
    sector. Mutation (min_prom default 1.0: no peak stands out) -> one sector -> red."""
    from digitize.extract.splitters.lily import petal_sectors, DEFAULTS
    th, r, tips = _fan(5)
    sec, got, _ = petal_sectors(th, r, DEFAULTS["bin_deg"], DEFAULTS["smooth_deg"], DEFAULTS["reach_q"], DEFAULTS["min_prom"], DEFAULTS["min_sep_deg"])
    assert len(got) == 5
    for t in tips:
        assert min(abs(((g - t) + 180) % 360 - 180) for g in got) <= 6.0
    assert (sec >= 0).all()


def test_ray_rule_one_angle_per_petal_and_outline_bucket():
    """construct rule "ray": a tone piece ON its petal's heart -> tip ray rebuilds to that ray's angle; a piece 5 mm off
    the ray does not (it is not on that petal); the angle is reported in the OUTLINE bucket (the tip is read off the
    traced outline), never as independent evidence. Mutations: (a) RAY_OFF_MM 10 -> the off piece rebuilds -> red;
    (b) "ray" dropped from OUTLINE_RULES -> bucket independent -> red."""
    from digitize.extract.splitters import construct as C
    con = dict(rule="ray", **{"from": [0.0, 0.0], "to": [20.0, 20.0]})
    on = Part(id="a", kind="lily_petal", geom=box(9, 9, 13, 13), thread="t", z=0, dir=DirSpec(45.0, source="splitter"), meta=dict(construct=con))
    off = Part(id="b", kind="lily_petal", geom=box(15, 3, 18, 6), thread="t", z=0, dir=DirSpec(45.0, source="splitter"), meta=dict(construct=con))
    a, why = C.basis(on); assert a == pytest.approx(45.0) and why is None
    a2, why2 = C.basis(off); assert a2 is None and "off its ray" in why2
    assert C.bucket_of(on) == "outline"


# ------------------------------------------------------------------ fish: pose + template placement
def _fish_mask(head_right=True, H=60, W=160):
    """a synthetic fish on a px grid: elliptical body + forked tail joined by a thin peduncle; eye near the head"""
    yy, xx = np.mgrid[0:H, 0:W]; cy = H / 2
    body = ((xx - 90) / 45.0) ** 2 + ((yy - cy) / 14.0) ** 2 <= 1
    ped = (xx >= 35) & (xx <= 48) & (np.abs(yy - cy) <= 3)
    tail = (xx >= 15) & (xx <= 36) & (np.abs(yy - cy) <= (36 - xx) * 0.9 + 2)
    m = body | ped | tail; eye = (128.0, cy - 2)
    if not head_right: m = m[:, ::-1]; eye = (W - eye[0], eye[1])
    return m, eye


@pytest.mark.parametrize("head_right", [True, False])
@pytest.mark.parametrize("use_eye", [True, False])
def test_fish_pose_head_from_eye_or_peduncle(head_right, use_eye):
    """head = the end nearer the eye, else the blunt end (the peduncle, the thinnest cross-section 10-35 % from the tail,
    is at the tail). Both orientations. Mutation (head_is_lo inverted in the peduncle rule) -> red on use_eye=False."""
    from digitize.extract.splitters.fish import pose
    m, eye = _fish_mask(head_right)
    P = pose(m, eye if use_eye else None)
    assert (P["head"][0] > P["tail"][0]) == head_right
    assert P["length"] == pytest.approx(m.any(0).sum(), abs=3)


def test_fish_template_dorsal_faces_up_the_garment(tmp_path):
    """the founder's tetra template is laid on a garment pose with its DORSAL side (the neon stripe) up the garment
    (-y), whichever way the fish swims, head on the pose's head, at length_factor x the pose length. Mutation (dorsal
    sign ignored in placement) -> the stripe lands below the axis for one heading -> red."""
    from PIL import Image
    from digitize.extract.splitters import fish
    m, eye = _fish_mask(True)
    img = np.zeros(m.shape + (3,), np.uint8); img[:] = (10, 15, 40)
    img[m] = (190, 190, 225)
    yy, xx = np.mgrid[0:m.shape[0], 0:m.shape[1]]
    stripe = m & (yy < m.shape[0] / 2 - 6) & (xx > 60) & (xx < 125); img[stripe] = (63, 182, 224)    # cyan line, dorsal (image top)
    e = (xx - eye[0]) ** 2 + (yy - eye[1]) ** 2 <= 9; img[e] = (15, 15, 20)
    big = np.zeros((m.shape[0] + 40, m.shape[1] + 40, 3), np.uint8); big[:] = (10, 15, 40); big[20:-20, 20:-20] = img
    pal = {"kb_lav": "#B9B5CC", "kb_cyan": "#3FB6E0", "kb_black": "#15181F", "kb_navy": "#23396F"}
    sc = dict(fish.DEFAULTS); dorsals = set()
    for flip in (False, True):                                          # the template upright AND upside down (dorsal +/- normal)
        p = tmp_path / f"ref_fish_{int(flip)}.png"; Image.fromarray(big[::-1] if flip else big).save(p)
        fish._TEMPLATE.clear(); T = fish.template(str(p), pal, sc); dorsals.add(T["dorsal"])
        ys, xs = np.nonzero((T["tone"] == T["keys"].index("kb_cyan")) & T["mask"])
        assert len(xs) > 50
        for heading in (20.0, 160.0, 200.0, 340.0):                     # swimming down-right, down-left, up-left, up-right
            a = math.radians(heading); ax = np.array([math.cos(a), math.sin(a)])
            head = np.array([50.0, 50.0]) + 15 * ax; tail = np.array([50.0, 50.0]) - 15 * ax
            P = dict(head=head, tail=tail, axis=-ax, length=30.0, centre=np.array([50.0, 50.0]))
            fn, s, _ = fish.placement(T, P, 0.82)
            X, Y = fn(xs + 0.5, ys + 0.5)
            assert Y.mean() < 50.0, (flip, heading)                     # dorsal stripe above the axis (up the garment)
            hx, hy = fn(*T["pose"]["head"]); assert math.dist((float(hx), float(hy)), head - (1 - 0.82) * 15 * ax) < 1.5
            assert s * T["pose"]["length"] == pytest.approx(0.82 * 30.0, rel=1e-6)
    assert dorsals == {1.0, -1.0}                                       # both template sides were exercised


# ------------------------------------------------------------------ run / bench additions
def test_bare_tones_never_become_threads():
    """threads.bare (Koi's navy duck): the tone keeps its evidence pixels but gets zero weight, so the planner maps it
    to NO thread, even when it is the biggest tone in the crop. Default (no bare) = unchanged weights.
    Mutation (zero_bare returns w unchanged) -> the duck becomes a thread -> red."""
    from digitize.run import zero_bare
    from digitize import threads as TH
    keys = ["duck", "blue", "red"]; pal = {"duck": "#121B2A", "blue": "#4A73B0", "red": "#D8262E"}
    w = zero_bare([5000.0, 300.0, 20.0], keys, ["duck"])
    tp = TH.plan(dict(zip(keys, w.tolist())), pal, needles=12, protected=["red"])
    assert tp["map"]["duck"] is None and "duck" not in tp["threads"] and set(tp["threads"]) == {"blue", "red"}
    assert list(zero_bare([5000.0, 300.0, 20.0], keys, None)) == [5000.0, 300.0, 20.0]
    with pytest.raises(SystemExit): zero_bare([1.0], ["a"], ["nope"])


def test_colour_gate_reads_this_designs_accents():
    """bench.verdict colours: Koi has red and no gold, so its bench.json targets.accents = [red] passes on red alone;
    without accents the Castle default (red AND gold) still applies. Mutation (accents ignored) -> red."""
    from digitize.bench import verdict
    row = dict(direction=dict(pct_ok=0, pct_chaos=100, tiles=1), angle_coherence={}, density=dict(flags=0), trims=dict(per_100cm2=0),
               satin=dict(blob=0, too_wide=0, too_narrow=0), stack=dict(max=1), colours=dict(threads_in_file=10, red=True, gold=False))
    T = dict(direction_pct_ok_min=85, direction_pct_chaos_max=5, stack_max_layers=2, trims_per_100cm2_max=25, satin_blobs_max=0, colours_max=12, density_flags_max=0)
    assert verdict(row, dict(T, accents=["red"]))["colours"] is True
    assert verdict(row, T)["colours"] is False


def test_koi_kinds_in_the_rulebook():
    """the trial's kinds say what the brief asked: lily petals tatami along the petal (construct), fish body tatami along
    the axis, stripes a satin column (split_satin column mode, never split under 7 mm), fins fanned tatami, the eye a bead"""
    from digitize.rulebook import Rulebook
    rb = Rulebook(); K = rb.data["kinds"]
    assert rb.technique_for("lily_petal") == "tatami" and K["lily_petal"]["dir"] == "construct"
    assert rb.technique_for("fish_body") == "tatami" and rb.technique_for("fish_fin") == "tatami"
    assert rb.technique_for("fish_stripe") == "split_satin" and K["fish_stripe"]["params"]["mode"] == "column" and K["fish_stripe"]["stitch_len"] <= 7.0
    assert rb.technique_for("fish_eye") == "dot" and K["fish_eye"]["dir"] == 0
