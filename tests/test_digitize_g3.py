"""ENGINE_PLAN G3 (labels contract): two generic features the Koi FR labels needed, both proven red first
(RECAP-2026-10-22-engine-g3.md).

1. hint.each: a labelled part whose windows are each ONE piece (one window per petal / lobe / panel), listed back to
   front. A soft reference area with no edge between its pieces cannot be split by lobe params (G2 runs 3-4); the
   labeller's windows split it, and each piece takes its own direction.
2. reference: a motif (or one part) names its own reference picture that the motif_match grade uses instead of the
   mockup crop; default = the mockup (unchanged)."""
import json, math, os
import numpy as np
import pytest
from shapely.geometry import Point

from test_digitize_g1 import _ctx, PAL

# an L of one soft tone: a long horizontal arm and a long vertical arm, no edge between them in the pixels
def _l_img(X, Y):
    arm_h = (X >= 8) & (X <= 52) & (Y >= 40) & (Y <= 50)
    arm_v = (X >= 8) & (X <= 18) & (Y >= 6) & (Y <= 50)
    return np.where(arm_h | arm_v, "white", "navy")


WIN_V = [[6, 4], [20, 4], [20, 39], [6, 39]]              # back piece: the vertical arm
WIN_H = [[6, 38], [54, 38], [54, 52], [6, 52]]            # front piece: the horizontal arm (overlaps WIN_V by 1 mm)


def _labels(each=True, confidence=0.9, **hint):
    h = {"polygons": [WIN_V, WIN_H]}; h.update(hint)
    if each is not None: h["each"] = each
    return {"schema": "techpack.labels/1", "motifs": [{"id": "m", "parts": [
        {"id": "p", "primitive": "lobe", "z": 2.0, "confidence": confidence, "direction": {"intent": "outline"},
         "hint": h, "tones": ["white"], "params": {"lobe_sep_mm": 60, "min_lobe_mm2": 10}, "alternatives": ["band"]},
        {"id": "ground", "primitive": "plane", "z": 0.0, "confidence": 0.9, "rest": True,
         "direction": {"intent": "angle", "angle": 0}}]}]}


def _extract(d):
    from digitize.labels import compile as LC, schema as LS
    LS.validate(d, PAL)
    ctx = _ctx(_l_img)
    return LC.extract(ctx, ctx.ev, d)


def _lobes(parts):
    return sorted([p for p in parts if p.meta["label"] == "m.p"], key=lambda p: p.z)


def test_each_window_is_its_own_piece_with_its_own_direction():
    parts, log, qs = _extract(_labels())
    L = _lobes(parts)
    assert len(L) == 2                                                   # one per window, not one slab
    back, front = L
    assert back.geom.distance(Point(13, 20)) == 0 and front.geom.distance(Point(40, 45)) == 0
    assert back.z < front.z                                              # listed order = sew order (back first)
    ang = lambda p: p.dir.angle % 180.0
    assert min(abs(ang(back) - 90), abs(ang(back) + 90)) < 15          # vertical arm along its own length
    assert min(ang(front), 180 - ang(front)) < 15                        # horizontal arm along its own length
    assert all(p.meta["label"] == "m.p" for p in L)                     # review / answers still see ONE labelled part
    assert sorted(p.meta["label_piece"] for p in L) == [1, 2]
    assert sorted(r["zone"] for r in log if r["zone"].startswith("m.p")) == ["m.p#1", "m.p#2"]


def test_without_each_the_same_windows_make_one_slab():
    parts, _, _ = _extract(_labels(each=None))
    assert len(_lobes(parts)) == 1                                       # the G2 behaviour, unchanged by default


def test_overlapping_windows_give_the_overlap_to_the_front_piece():
    parts, _, _ = _extract(_labels())
    back, front = _lobes(parts)
    ov = Point(13, 38.5).buffer(0.3)                                     # inside both windows, on the white arm
    assert front.geom.intersection(ov).area > 0.9 * ov.area and back.geom.intersection(ov).area < 0.1 * ov.area


def test_each_part_asks_one_question_and_an_answer_applies_to_every_piece():
    from digitize.labels import compile as LC
    d = _labels(confidence=0.4)
    qs = LC.questions(d)
    assert [q["id"] for q in qs] == ["label:m.p"]
    R = LC.resolve(d, {"m.p": "band"})
    assert [r["primitive"] for r in R if r["pid"] == "m.p"] == ["band", "band"]
    assert [r for r in LC.resolve(d, {"m.p": "drop"}) if r["pid"] == "m.p"] == []


def test_except_naming_an_each_part_cuts_all_its_windows():
    from digitize.labels import compile as LC
    d = _labels()
    d["motifs"][0]["parts"].append({"id": "over", "primitive": "plane", "z": 1.0, "confidence": 0.9,
                                    "direction": {"intent": "angle", "angle": 45}, "tones": ["white"],
                                    "hint": {"polygons": [[[0, 0], [60, 0], [60, 60], [0, 60]]], "except": ["m.p"]}})
    g = [r for r in LC.resolve(d) if r["pid"] == "m.over"][0]["geoms"][0]
    assert g.distance(Point(13, 20)) > 0 and g.distance(Point(40, 45)) > 0 and g.distance(Point(40, 20)) == 0


@pytest.mark.parametrize("hint, why", [
    (dict(each="yes"), "each must be true or false"),
    (dict(each=True, polygons=[WIN_V]), "each needs >= 2 windows"),
])
def test_schema_rejects_a_bad_each(hint, why):
    from digitize.labels import schema as LS
    d = _labels(each=None); d["motifs"][0]["parts"][0]["hint"].update(hint)
    with pytest.raises(LS.LabelsError, match=why):
        LS.validate(d, PAL)


# ------------------------------------------------------------------ 2. motif reference image
SQUARE = (20, 20, 40, 40)          # the stitched square (garment mm) in the grading tests


def _ref_img(X, Y):
    x0, y0, x1, y1 = SQUARE
    return np.where((X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1), "white", "navy")


def _grade_labels(ref=None, part_ref=None):
    m = {"id": "m", "parts": [{"id": "body", "primitive": "lobe", "z": 1.0, "confidence": 0.9, "direction": {"intent": "outline"},
                               "hint": {"polygons": [[[15, 15], [45, 15], [45, 45], [15, 45]]]}, "tones": ["white"]}]}
    if ref: m["reference"] = ref
    if part_ref: m["parts"][0]["reference"] = part_ref
    return {"schema": "techpack.labels/1", "motifs": [m]}


def _png(tmp_path, name, shape):
    """an RGBA picture 100 x 100 px whose opaque pixels are `shape` ('square' = all, 'bar' = a left third)"""
    from PIL import Image
    a = np.zeros((100, 100, 4), np.uint8); a[..., :3] = 200
    if shape == "square": a[..., 3] = 255
    else: a[:, :33, 3] = 255
    Image.fromarray(a).save(tmp_path / name); return name


def _out(ev):
    """the 'stitched' mask: exactly the square, on the evidence grid"""
    from shapely.geometry import box
    return ev.mask(box(*SQUARE))


def test_default_reference_is_the_mockup_crop_and_a_faithful_square_passes(tmp_path):
    from digitize.labels import refgrade as RG, schema as LS
    ctx = _ctx(_ref_img); d = _grade_labels(); LS.validate(d, PAL)
    rows = RG.grade(d, str(tmp_path), ctx.ev, _out(ctx.ev))
    assert [r["unit"] for r in rows] == ["m"] and rows[0]["reference"] == "mockup"
    assert rows[0]["ok"] and rows[0]["iou"] > 0.9


def test_a_named_reference_image_replaces_the_mockup_for_its_motif(tmp_path):
    from digitize.labels import refgrade as RG, schema as LS
    ctx = _ctx(_ref_img)
    same = _grade_labels(ref={"image": _png(tmp_path, "sq.png", "square"), "box": list(SQUARE)})
    other = _grade_labels(ref={"image": _png(tmp_path, "big.png", "square"), "box": [10, 10, 50, 50]})   # 4 x the stitches
    for d in (same, other): LS.validate(d, PAL)
    r1 = RG.grade(same, str(tmp_path), ctx.ev, _out(ctx.ev))[0]
    r2 = RG.grade(other, str(tmp_path), ctx.ev, _out(ctx.ev))[0]
    assert r1["reference"] == "sq.png" and r1["ok"]
    assert r2["reference"] == "big.png" and not r2["ok"] and r2["iou"] < 0.5      # graded on the picture, not the mockup


def test_a_part_reference_is_graded_as_its_own_unit(tmp_path):
    from digitize.labels import refgrade as RG, schema as LS
    ctx = _ctx(_ref_img)
    d = _grade_labels(part_ref={"image": _png(tmp_path, "bar.png", "bar"), "box": list(SQUARE)}); LS.validate(d, PAL)
    rows = RG.grade(d, str(tmp_path), ctx.ev, _out(ctx.ev))
    assert [(r["unit"], r["reference"]) for r in rows] == [("m.body", "bar.png")]


def test_reference_does_not_change_what_is_extracted(tmp_path):
    from digitize.labels import compile as LC
    ctx = _ctx(_ref_img)
    a, _, _ = LC.extract(ctx, ctx.ev, _grade_labels())
    ctx = _ctx(_ref_img)
    b, _, _ = LC.extract(ctx, ctx.ev, _grade_labels(ref={"image": "nowhere.png", "box": list(SQUARE)}))
    assert [(p.kind, p.thread, round(p.geom.area, 3), round(p.dir.angle, 3)) for p in a] == \
           [(p.kind, p.thread, round(p.geom.area, 3), round(p.dir.angle, 3)) for p in b]


@pytest.mark.parametrize("ref, why", [
    ({"box": [0, 0, 1, 1]}, "reference.image"),
    ({"image": "a.png"}, "reference.box"),
    ({"image": "a.png", "box": [5, 5, 1, 1]}, "reference.box"),
    ({"image": "a.png", "box": [0, 0, 1, 1], "fit": "x"}, "unknown keys"),
])
def test_schema_rejects_a_bad_reference(ref, why):
    from digitize.labels import schema as LS
    with pytest.raises(LS.LabelsError, match=why):
        LS.validate(_grade_labels(ref=ref), PAL)
    with pytest.raises(LS.LabelsError, match=why):
        LS.validate(_grade_labels(part_ref=ref), PAL)


def test_missing_reference_image_is_named_not_silently_mockup(tmp_path):
    from digitize.labels import refgrade as RG
    ctx = _ctx(_ref_img)
    with pytest.raises(FileNotFoundError, match="nowhere.png"):
        RG.grade(_grade_labels(ref={"image": "nowhere.png", "box": list(SQUARE)}), str(tmp_path), ctx.ev, _out(ctx.ev))


# ------------------------------------------------------------------ 3. rule 3 separation at exactly sep[0] (found on the G3 Koi run)
def _sq_part(pid, x0, angle, thread="corn"):
    from shapely.geometry import box
    from digitize.schema import Part, DirSpec
    return Part(id=pid, kind="lobe", geom=box(x0, 0, x0 + 10, 10), thread=thread, z=1.0, dir=DirSpec(angle, source="splitter"), meta={})


def test_a_turn_to_exactly_the_minimum_separation_survives_the_angle_rounding():
    """DirSpec keeps angles to 0.01 deg: 140.01 - 15 = 125.01, and 140.01 - 125.01 = 14.999999999999986 in floats.
    The separation pass turned the leaf to exactly 15 deg, the report then read it as < 15 (a failed gate on a pair the
    pass had separated) and a second pass 'turned -0.0 deg'."""
    from digitize import direction as DR
    big = _sq_part("big", 0, 140.01); small = _sq_part("small", 10, 133.0)
    big.geom = big.geom.union(_sq_part("x", 0, 0).geom.buffer(2))                   # bigger: fixed first
    parts = [big, small]
    moves = DR.separate(parts, sep=(15.0, 25.0), kinds={"lobe"})
    assert len(moves) == 1 and round(DR.axial_diff(small.dir.angle, big.dir.angle), 2) == 15.0
    assert DR.separation_report(parts, sep=15.0)["close"] == 0
    assert DR.separate(parts, sep=(15.0, 25.0), kinds={"lobe"}) == []               # a second pass has nothing to turn


def test_separation_report_still_flags_a_real_clash():
    from digitize import direction as DR
    assert DR.separation_report([_sq_part("a", 0, 140.0), _sq_part("b", 10, 125.02)], sep=15.0)["close"] == 1   # 14.98 deg
    assert DR.separation_report([_sq_part("a", 0, 140.0), _sq_part("b", 10, 125.0)], sep=15.0)["close"] == 0
