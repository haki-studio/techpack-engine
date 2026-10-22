"""ENGINE_PLAN G4 (labels contract): a motif reference that GOVERNS the sewing, not only the grade (founder 2026-10-22 on
the Koi fish: "we want the tetra"; LESSONS A39). Proven red first (RECAP-2026-10-22-engine-g4.md).

1. reference.governs ["silhouette", "colour"] composites the picture into the EXTRACTION source (labels.refsource): its
   colours replace the mockup's inside its pixels, the motif's windows read as bare shell outside them. [] (default) =
   G3 grading only, the source is untouched.
2. refgrade grades a colour-governed unit on the sewn COLOURS too (colour_grade, per colour group): the Koi fish gate
   fails koi-coloured fish and passes the tetra, on the real committed tetra pictures."""
import json, os
import numpy as np
import pytest

from test_digitize_g1 import _ctx, PAL

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KOI = os.path.join(ROOT, "projects/koi-blossom-hoodie/bench")
PAL_B = dict(PAL, bare="#121B2A")


def _pic(tmp_path, name="ref.png", size=(40, 20), stripe=True):
    """an RGBA picture: a white body (alpha 255) with a red stripe in its lower half; corners transparent"""
    from PIL import Image
    a = np.zeros(size[::-1] + (4,), np.uint8)
    a[2:-2, 2:-2] = (238, 234, 224, 255)                       # PAL white
    if stripe: a[12:16, 8:32] = (180, 80, 111, 255)            # PAL rose
    Image.fromarray(a, "RGBA").save(tmp_path / name)
    return name


def _ref_src(fill="#5A7240", W=60, H=60, ppm=4.0):
    """a synthetic extraction source (register.reference shape): one flat colour everywhere"""
    from digitize.extract.evidence import hex_rgb
    rgb = np.zeros((int(H * ppm), int(W * ppm), 3)) + hex_rgb(fill)
    return dict(rgb=rgb, grey=rgb @ np.array([0.299, 0.587, 0.114]), bounds=(0, 0, W, H), ppm=ppm,
                closeup_weight=np.ones(rgb.shape[:2]), source_ppm_median=ppm)


def _labels(image, governs=None, box=(10, 10, 50, 30), window=((5, 5), (55, 5), (55, 35), (5, 35))):
    ref = {"image": image, "box": list(box)}
    if governs is not None: ref["governs"] = governs
    return {"schema": "techpack.labels/1", "motifs": [{"id": "m", "reference": ref, "parts": [
        {"id": "p", "primitive": "lobe", "z": 2.0, "confidence": 0.9, "direction": {"intent": "outline"},
         "hint": {"polygons": [list(map(list, window))]}, "tones": ["white", "rose"], "params": {"lobe_sep_mm": 60}}]}]}


def _at(ref, x, y):
    return ref["rgb"][int(y * ref["ppm"]), int(x * ref["ppm"])]


# ---------------------------------------------------------------- 1. governs -> the extraction source
def test_governing_reference_recolours_inside_and_bares_outside(tmp_path):
    from digitize.labels import refsource, schema as LS
    from digitize.extract.evidence import hex_rgb
    d = LS.validate(_labels(_pic(tmp_path), ["silhouette", "colour"]), PAL_B)
    src = _ref_src()
    out, rows = refsource.composite(src, d, str(tmp_path), PAL_B, bare=("bare",))
    assert np.allclose(_at(out, 20, 15), (238, 234, 224))          # picture body (box px 10..50 -> pic col 10/40*40)
    assert np.allclose(_at(out, 25, 24), (180, 80, 111))           # picture stripe
    assert np.allclose(_at(out, 7, 7), hex_rgb("#121B2A"))         # in the window, off the picture -> bare
    assert np.allclose(_at(out, 58, 58), hex_rgb("#5A7240"))       # outside the window: untouched
    assert out["closeup_weight"][int(15 * 4), int(20 * 4)] == 0    # the picture, not a close-up, informs there
    assert np.allclose(out["grey"], out["rgb"] @ np.array([0.299, 0.587, 0.114]))
    assert np.allclose(src["rgb"], hex_rgb("#5A7240"))              # the input dict is not modified
    assert rows[0]["unit"] == "m" and rows[0]["bared_mm2"] > 0 and rows[0]["recoloured_mm2"] > 0


@pytest.mark.parametrize("governs", [None, []])
def test_grading_only_reference_leaves_the_source_untouched(tmp_path, governs):
    from digitize.labels import refsource, schema as LS
    d = LS.validate(_labels(_pic(tmp_path), governs), PAL_B)
    src = _ref_src(); out, rows = refsource.composite(src, d, str(tmp_path), PAL_B, bare=("bare",))
    assert out is src and rows == []


def test_colour_only_keeps_the_source_outside_the_picture(tmp_path):
    from digitize.labels import refsource, schema as LS
    from digitize.extract.evidence import hex_rgb
    d = LS.validate(_labels(_pic(tmp_path), ["colour"]), PAL_B)
    out, _ = refsource.composite(_ref_src(), d, str(tmp_path), PAL_B, bare=("bare",))
    assert np.allclose(_at(out, 7, 7), hex_rgb("#5A7240")) and np.allclose(_at(out, 25, 24), (180, 80, 111))


def test_silhouette_without_a_bare_tone_is_an_error(tmp_path):
    from digitize.labels import refsource, schema as LS
    d = LS.validate(_labels(_pic(tmp_path), ["silhouette"]), PAL_B)
    with pytest.raises(ValueError, match="bare"):
        refsource.composite(_ref_src(), d, str(tmp_path), PAL_B, bare=())


@pytest.mark.parametrize("g", ["colour", ["shape"], ["colour", "colour"]])
def test_schema_rejects_a_bad_governs(tmp_path, g):
    from digitize.labels import schema as LS
    with pytest.raises(LS.LabelsError, match="governs"):
        LS.validate(_labels("x.png", g), PAL_B)


@pytest.mark.parametrize("governs", [["silhouette", "colour"], []])
def test_governing_reference_changes_what_is_extracted(tmp_path, governs):
    """end to end through labels.compile: the source shows a white motif in the window's lower right (the mockup's
    koi); the picture shows a white + rose motif in the upper left (the tetra). Governed: the part is the picture's;
    grading only: the source's, as before."""
    from shapely.geometry import Point
    from digitize.labels import refsource, compile as LC, schema as LS
    from digitize.extract.evidence import Evidence
    d = LS.validate(_labels(_pic(tmp_path), governs, box=(6, 6, 38, 22)), PAL_B)
    ctx = _ctx(lambda X, Y: np.where((X > 30) & (X < 54) & (Y > 24) & (Y < 34), "white", "navy"))
    ref = dict(rgb=ctx.ev.rgb, grey=ctx.ev.rgb @ np.array([0.299, 0.587, 0.114]), bounds=ctx.ev.bounds, ppm=ctx.ev.ppm, closeup_weight=None)
    comp, _ = refsource.composite(ref, d, str(tmp_path), PAL_B, bare=("bare",))
    ctx.ev = Evidence(comp, PAL_B, ppm=4.0, smooth_mm=0.2, mode_mm=0.3)
    parts, log, _ = LC.extract(ctx, ctx.ev, d)
    g = __import__("shapely.ops", fromlist=["unary_union"]).unary_union([p.geom for p in parts])
    if governs:
        assert g.distance(Point(12, 10)) == 0 and g.distance(Point(50, 30)) > 1     # the picture's place, not the source's
        assert 0.8 * 28.8 * 12.8 < g.area < 1.2 * 28.8 * 12.8                        # the picture's body (32 x 16 box, 2 px in)
    else:
        assert g.distance(Point(50, 30)) == 0 and g.distance(Point(12, 10)) > 1


# ---------------------------------------------------------------- 2. the colour grade
def _ev(W=60, H=60):
    from digitize.extract.evidence import Evidence
    return Evidence(_ref_src(W=W, H=H), PAL_B, ppm=4.0, smooth_mm=0, mode_mm=0)


def test_colour_grade_passes_the_pictures_colours_and_fails_a_missing_stripe(tmp_path):
    from digitize.labels import refgrade as RG, schema as LS
    from digitize.extract.evidence import hex_rgb
    d = LS.validate(_labels(_pic(tmp_path), ["silhouette", "colour"]), PAL_B)
    ev = _ev(); m, pic = RG.place(d["motifs"][0]["reference"], str(tmp_path), ev.to_px, (ev.H, ev.W))
    red = m & (np.abs(pic - (180, 80, 111)).sum(-1) < 5)
    good = {0: m & ~red, 1: red}; hexes = [PAL["white"], PAL["rose"]]
    rows = RG.grade(d, str(tmp_path), ev, m, bare=("bare",), stops=(good, hexes), palette=PAL_B)
    assert rows[0]["ok"] and rows[0]["colour_ok"] and rows[0]["colour_match"] > 0.95
    allwhite = {0: m}                                                # the right outline, but no stripe
    rows = RG.grade(d, str(tmp_path), ev, m, bare=("bare",), stops=(allwhite, hexes[:1]), palette=PAL_B)
    assert rows[0]["shape_ok"] and not rows[0]["colour_ok"] and not rows[0]["ok"]
    assert rows[0]["groups"]["rose"]["recall"] == 0.0


def test_colour_governed_grade_needs_the_stop_colours(tmp_path):
    from digitize.labels import refgrade as RG, schema as LS
    d = LS.validate(_labels(_pic(tmp_path), ["colour"]), PAL_B); ev = _ev()
    with pytest.raises(ValueError, match="stops"):
        RG.grade(d, str(tmp_path), ev, np.ones((ev.H, ev.W), bool), bare=("bare",))


def test_tone_groups_join_shades_and_keep_accents_apart():
    from digitize.labels import refgrade as RG
    import yaml
    pal = yaml.safe_load(open(os.path.join(KOI, "run_fr_labels.yaml")))["threads"]["palette"]
    g = RG.tone_groups(pal, bare=("kb_duck", "kb_duck_lt"))
    blues = {g[k] for k in ("kb_navy", "kb_cobalt", "kb_royal", "kb_corn", "kb_sky", "kb_ice", "kb_white", "kb_lav")}
    assert len(blues) == 1 and len({g["kb_white"], g["kb_cyan"], g["kb_red"], g["kb_black"]}) == 4
    assert "kb_duck" not in g


# ---------------------------------------------------------------- 3. the real Koi fish gate (committed inputs only)
def _koi():
    import yaml
    from digitize.extract.evidence import Evidence
    from digitize.labels import schema as LS
    pal = yaml.safe_load(open(os.path.join(KOI, "run_fr_labels.yaml")))["threads"]["palette"]
    lab = LS.load(os.path.join(KOI, "labels_FR.json"), palette=pal)
    koi = LS.load(os.path.join(KOI, "labels_FR_mockup.json"), palette=pal)
    src = _ref_src(W=170, H=270); src["bounds"] = (-220, 30, -50, 300)
    return pal, lab, koi, Evidence(src, pal, ppm=4.0, smooth_mm=0, mode_mm=0)


def test_koi_fish_gate_fails_koi_coloured_fish_and_passes_the_tetra():
    """the five Koi fish on the founder's tetra pictures. TETRA = each picture pixel sewn in its nearest thread;
    KOI-COLOURED = the same outline sewn the way G3 sewed the koi: silver body + red where the mockup koi is red
    (labels_FR_mockup.json stripe windows), no cyan."""
    from digitize.labels import refgrade as RG, schema as LS
    from digitize.extract.evidence import to_lab, hex_rgb, delta_e
    pal, lab, koi, ev = _koi(); bare = ("kb_duck", "kb_duck_lt")
    fish = [m for m in lab["motifs"] if "reference" in m]
    assert len(fish) == 5 and all(LS.governs(m["reference"]) == ["silhouette", "colour"] for m in fish)
    keys = [k for k in pal if k not in bare]; hexes = [pal[k] for k in keys]
    lab_p = to_lab(np.array([[hex_rgb(h) for h in hexes]], float))[0]
    tetra, koic = {}, {0: np.zeros((ev.H, ev.W), bool), keys.index("kb_red"): np.zeros((ev.H, ev.W), bool)}
    sewn = np.zeros((ev.H, ev.W), bool)
    for m in fish:
        msk, pic = RG.place(m["reference"], KOI, ev.to_px, (ev.H, ev.W)); sewn |= msk
        near = np.stack([delta_e(to_lab(pic[msk][None])[0], np.broadcast_to(lab_p[i], (int(msk.sum()), 3))) for i in range(len(keys))], -1).argmin(-1)
        for i in np.unique(near):
            t = tetra.setdefault(int(i), np.zeros((ev.H, ev.W), bool)); t[np.nonzero(msk)[0][near == i], np.nonzero(msk)[1][near == i]] = True
        red = ev.mask(__import__("shapely.geometry", fromlist=["Polygon"]).Polygon(
            next(p for p in next(k for k in koi["motifs"] if k["id"] == m["id"])["parts"] if p["id"] == "stripe")["hint"]["polygons"][0]).buffer(0)) \
            if any(p["id"] == "stripe" for p in next(k for k in koi["motifs"] if k["id"] == m["id"])["parts"]) else np.zeros_like(msk)
        koic[0] |= msk; koic[keys.index("kb_red")] |= msk & red
    white = keys.index("kb_white"); koic = {white if k == 0 else k: v for k, v in koic.items()}
    rows_t = [r for r in RG.grade(lab, KOI, ev, sewn, bare=bare, stops=(tetra, hexes), palette=pal) if r["motif"].startswith("fish")]
    rows_k = [r for r in RG.grade(lab, KOI, ev, sewn, bare=bare, stops=(koic, hexes), palette=pal) if r["motif"].startswith("fish")]
    assert [r["ok"] for r in rows_t] == [True] * 5, [(r["unit"], r["colour_match"], r["groups"]) for r in rows_t]
    assert [r["ok"] for r in rows_k] == [False] * 5, [(r["unit"], r["colour_match"], r["groups"]) for r in rows_k]
    assert all(r["shape_ok"] for r in rows_k)                        # same outline: colour alone fails them
    assert all(r["groups"]["kb_cyan"]["recall"] == 0.0 for r in rows_k)
