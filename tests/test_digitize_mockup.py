"""The garment MOCKUP governs, close-ups only inform (founder ruling 2026-10-20; generic parts salvaged from the Koi
engine trial, PR #13). Every guard here was proven red by a mutation (listed in the PR), then green."""
import json, math, os, sys
import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))

from shapely.geometry import box
from digitize.schema import Part, DirSpec

FAB = (20, 30, 50)


# ------------------------------------------------------------------ inform: per-motif fit, mockup silhouette, mean colour
def _inform_scene(tmp_path):
    """a 1 px/mm mockup with ONE blue disc at (40, 40) mm; a 2 px/mm close-up whose copy of that disc is shifted 20 mm in x
    and striped (interior detail), plus an EXTRA striped disc at (75, 75) mm that the mockup does not have"""
    from PIL import Image
    fab = np.array(FAB, np.uint8); blue = np.array([60, 100, 200], np.uint8)
    yy, xx = np.mgrid[0:100, 0:100]
    mk = np.zeros((100, 100, 3), np.uint8); mk[:] = fab; mk[(xx - 40) ** 2 + (yy - 40) ** 2 <= 100] = blue
    Y, X = np.mgrid[0:200, 0:200]; cu = np.zeros((200, 200, 3), np.uint8); cu[:] = fab
    stripes = (Y // 4) % 2 == 0
    for cx, cy in ((120, 80), (150, 150)):                              # (40 + 20, 40) mm and (75, 75) mm at 2 px/mm
        d = (X - cx) ** 2 + (Y - cy) ** 2 <= 400
        cu[d & stripes] = (150, 180, 240); cu[d & ~stripes] = (40, 70, 160)
    Image.fromarray(mk).save(tmp_path / "mock.png"); Image.fromarray(cu).save(tmp_path / "cu.png")
    reg = {"flat": str(tmp_path / "mock.png"), "views": {"F": {"ox": 0.0, "oy": 0.0, "sx": 1.0, "sy": 1.0}},
           "closeups": [{"name": "c", "view": "F", "file": str(tmp_path / "cu.png"), "mode": "inform", "motifs": []}]}
    return reg, mk, cu


def _informed(tmp_path, reg, sim, fit=None):
    from digitize.extract import register
    reg = json.loads(json.dumps(reg)); m = dict(name="m", window=[5, 5, 98, 98], sim=sim)
    if fit is not None: m["fit"] = fit
    reg["closeups"][0]["motifs"] = [m]
    p = tmp_path / "reg.json"; json.dump(reg, open(p, "w")); register._CACHE.clear()
    return register.reference(register.load(str(p)), "F", (0, 0, 100, 100), ppm=4)


def test_closeup_motif_missing_from_the_mockup_is_never_sewn(tmp_path):
    """a motif the close-up has and the MOCKUP does not (the extra disc) never enters the reference the engine traces:
    only duck there, so no zone can claim it and nothing is stitched. Mutation (inform.composite samples the whole
    window, not only the mockup's own silhouette) -> the extra disc appears -> red."""
    from digitize.extract import inform
    reg, mk, cu = _inform_scene(tmp_path)
    r = _informed(tmp_path, reg, [2.0, 0.0, 40.0, 0.0])                # the correct per-motif fit (20 mm shift)
    m = inform.motif_like(r["rgb"], np.array(FAB, float))
    yy, xx = np.mgrid[0:400, 0:400] / 4.0
    extra = ((xx - 55) ** 2 + (yy - 75) ** 2) <= 64                       # where this fit puts the close-up-only disc
    assert not m[extra].any() and r["closeup_weight"][extra].max() == 0
    assert not (m & (((xx - 40) ** 2 + (yy - 40) ** 2) > 121)).any()        # motif pixels ONLY on the mockup's own disc


def test_closeup_motif_shifted_20mm_is_sewn_at_the_mockup_position(tmp_path):
    """the close-up draws the disc 20 mm to the right: the per-motif fit (fit_similarity) recovers the shift, the
    stripes (interior detail) land INSIDE the mockup's disc at (40, 40), and the silhouette, position and colour stay the
    mockup's. Mutations: (a) no translation search (max_shift 0) -> red; (b) colour shift off -> red."""
    from digitize.extract import inform
    reg, mk, cu = _inform_scene(tmp_path)
    f = inform.fit_similarity(mk.astype(float), cu.astype(float), [15, 15, 65, 65], [2.0, 0.0, 0.0, 0.0], rot_deg=4.0, rot_step=2.0,
                              scale_rel=0.0, scale_step=0.05, max_shift=25)
    assert f["iou"] > 0.7 and abs(f["sim"][2] - 40.0) <= 2.0             # 20 mm = 40 close-up px
    r = _informed(tmp_path, reg, f["sim"], fit=dict(iou=f["iou"]))
    yy, xx = np.mgrid[0:400, 0:400] / 4.0
    disc = ((xx - 40) ** 2 + (yy - 40) ** 2) <= 64; shifted = ((xx - 60) ** 2 + (yy - 40) ** 2) <= 36
    m = inform.motif_like(r["rgb"], np.array(FAB, float))
    assert m[disc].mean() > 0.95 and not m[shifted].any()                # the mockup's position and silhouette
    assert r["closeup_weight"][disc].mean() > 0.9                       # the close-up informs it ...
    assert r["grey"][disc].std() > 15                                   # ... with its stripes (the mockup disc is flat)
    assert np.abs(r["rgb"][disc].mean(0) - np.array([60, 100, 200], float)).max() < 12   # ... in the MOCKUP's colour


def test_poorly_fitting_closeup_motif_does_not_inform(tmp_path):
    """a motif whose best fit overlays the mockup motif with IoU < 0.5 (MIN_IOU) is not informed: the close-up does not
    show that mockup motif, so the mockup stays as it is. Mutation (acceptance check removed) -> detail used -> red."""
    from digitize.extract import inform
    reg, mk, cu = _inform_scene(tmp_path)
    r = _informed(tmp_path, reg, [2.0, 0.0, 40.0, 0.0], fit=dict(iou=0.41))
    assert r["closeup_weight"].max() == 0
    from digitize.extract import register
    p = tmp_path / "reg_mock.json"; json.dump(dict(reg, closeups=[]), open(p, "w")); register._CACHE.clear()
    assert np.allclose(r["rgb"], register.reference(register.load(str(p)), "F", (0, 0, 100, 100), ppm=4)["rgb"])   # = the mockup
    assert inform.MIN_IOU == 0.5


# ------------------------------------------------------------------ bench: mockup-only gate reference
def test_bench_gates_on_a_mockup_only_reference(tmp_path):
    """bench.json closeup null: the gates read the mockup alone, with no close-up feather mask (every tile is judged;
    with the mask a mockup-only crop would mask every tile and the direction gate would judge nothing).
    Mutation (feather mask kept when closeup is null) -> 0 judged tiles -> red."""
    import pyembroidery as pe
    from digitize import bench
    reg, mk, cu = _inform_scene(tmp_path)
    reg = dict(reg, closeups=[]); json.dump(reg, open(tmp_path / "reg_mock.json", "w"))
    p = pe.EmbPattern(); y = 30.0; k = 0
    while y <= 50.0:                                                    # horizontal tatami-like rows over the disc
        xs = (30.0, 50.0) if k % 2 == 0 else (50.0, 30.0)
        for x in np.linspace(xs[0], xs[1], 7): p.add_stitch_absolute(pe.STITCH, x * 10, y * 10)
        y += 0.45; k += 1
    p.add_command(pe.END); dst = str(tmp_path / "t.dst"); pe.write_dst(p, dst)
    cfg_b = dict(name="t", crop=[24, 24, 56, 56], view="F", ppm=12, registration="reg_mock.json", closeup=None, min_weight=0.6)
    row, aux = bench.run_gates(cfg_b, str(tmp_path), dst, (0.0, 0.0))
    assert row["crop_min_closeup_weight"] is None
    assert row["direction"]["masked"] == 0 and row["direction"]["tiles"] > 0


# ------------------------------------------------------------------ sequence: tone pieces of one motif
def test_tone_pieces_of_one_motif_overlap_by_a_seam_not_the_underlap():
    """abutting tone pieces of ONE motif (meta tone_group: a petal's shades, a body's bands) grow only
    sequence.TONE_SEAM_MM (0.3 mm) into each other; against another motif the house 1 mm underlap stays; parts without
    a tone_group are unchanged. Mutation (tone_group ignored) -> 1 mm into its own motif's piece -> red."""
    from digitize import sequence as SQ
    def part(pid, g, z, tg):
        return Part(id=pid, kind="zone_stub", geom=g, thread="t", z=z, dir=DirSpec(0.0), meta=dict(tone_group=tg) if tg else {})
    a, b, c = part("a", box(0, 0, 10, 10), 0.0, "f1"), part("b", box(10, 0, 20, 10), 0.1, "f1"), part("c", box(0, 10, 10, 20), 0.1, "f2")
    SQ.underlap([a, b, c], keep=1.0)
    assert a.geom.intersection(box(10, 0, 20, 10)).area / 10.0 == pytest.approx(SQ.TONE_SEAM_MM, abs=0.05)
    assert a.geom.intersection(box(0, 10, 10, 20)).area / 10.0 == pytest.approx(1.0, abs=0.05)
    d, e = part("d", box(0, 0, 10, 10), 0.0, None), part("e", box(10, 0, 20, 10), 0.1, None)
    SQ.underlap([d, e], keep=1.0)
    assert d.geom.intersection(box(10, 0, 20, 10)).area / 10.0 == pytest.approx(1.0, abs=0.05)


# ------------------------------------------------------------------ run / bench options
def test_bare_tones_never_become_threads():
    """run.yaml threads.bare (fabric left unsewn between motifs): the tone keeps its evidence pixels but gets zero
    weight, so the planner maps it to NO thread, even as the biggest tone in the crop; default = unchanged.
    Mutation (zero_bare a no-op) -> the fabric becomes a thread -> red."""
    from digitize.run import zero_bare
    from digitize import threads as TH
    keys = ["duck", "blue", "red"]; pal = {"duck": "#121B2A", "blue": "#4A73B0", "red": "#D8262E"}
    w = zero_bare([5000.0, 300.0, 20.0], keys, ["duck"])
    tp = TH.plan(dict(zip(keys, w.tolist())), pal, needles=12, protected=["red"])
    assert tp["map"]["duck"] is None and set(tp["threads"]) == {"blue", "red"}
    assert list(zero_bare([5000.0, 300.0, 20.0], keys, None)) == [5000.0, 300.0, 20.0]
    with pytest.raises(SystemExit): zero_bare([1.0], ["a"], ["nope"])


def test_colour_gate_reads_this_designs_accents():
    """bench.verdict colours: targets.accents lists the accents a design has (a red-only design passes without gold);
    without it the Castle default (red AND gold) applies. Mutation (accents ignored) -> red."""
    from digitize.bench import verdict
    row = dict(direction=dict(pct_ok=0, pct_chaos=100, tiles=1), angle_coherence={}, density=dict(flags=0), trims=dict(per_100cm2=0),
               satin=dict(blob=0, too_wide=0, too_narrow=0), stack=dict(max=1), colours=dict(threads_in_file=10, red=True, gold=False))
    T = dict(direction_pct_ok_min=85, direction_pct_chaos_max=5, stack_max_layers=2, trims_per_100cm2_max=25, satin_blobs_max=0, colours_max=12, density_flags_max=0)
    assert verdict(row, dict(T, accents=["red"]))["colours"] is True
    assert verdict(row, T)["colours"] is False
