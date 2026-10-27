"""Konpeito jeans gates (PR #30 review items 2-4): each proven red on a synthetic failing case and green on a passing one.
- outline gate (kjcompare.candy_metrics / OUTLINE_MAX): a 5-point star of the konpeito's size passes IoU but must fail;
  a slightly fat konpeito must pass; with the outline check disabled the star passes (mutation: the outline is what
  catches it).
- border dots (kjcompare.dot_rows): needle span vs the art Ø, centre offset.
- border areas (kjcompare.area_gates): a bare 2 x 2 mm square in the red band fails.
- konpeito position (kjcompare.candy_position): a candy sewn 2 mm off its independent centre fails."""
import os, sys, math, tempfile
import numpy as np
import pytest
import pyembroidery as pe
from PIL import Image, ImageDraw
from shapely.geometry import Polygon
from shapely import affinity

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.join(ROOT, "projects", "konpeito-jeans")
if PROJ not in sys.path: sys.path.insert(0, PROJ)
PPM = 20


@pytest.fixture(autouse=True)
def in_project(monkeypatch):
    monkeypatch.chdir(PROJ)          # kjsvg reads inputs/svg relative to the project
    # the C5 map out/front_stars.json is build output (git-ignored); a fresh worktree gets the committed copy
    if not os.path.exists("out/front_stars.json"):
        import shutil; os.makedirs("out", exist_ok=True)
        shutil.copy(os.path.join(ROOT, "tests", "fixtures", "konpeito_front_stars.json"), "out/front_stars.json")


def raster(g, W=16.0, H=16.0, ppm=PPM):
    im = Image.new("L", (int(W * ppm), int(H * ppm)), 0); d = ImageDraw.Draw(im)
    for P in (g.geoms if hasattr(g, "geoms") else [g]):
        d.polygon([(x * ppm, y * ppm) for x, y in P.exterior.coords], fill=255)
    return np.asarray(im) > 0


def star5(width=10.0, inner=0.7, tip=0.15, rot=18.0):
    """puffy 5-point star (rounded tips), same size as the konpeito: the Rev B-like shape that IoU alone passes."""
    pts = [((1 if i % 2 == 0 else inner) * math.cos(math.radians(-90 + 36 * i)),
            (1 if i % 2 == 0 else inner) * math.sin(math.radians(-90 + 36 * i))) for i in range(10)]
    g = Polygon(pts).buffer(-tip, join_style="round").buffer(tip, join_style="round")
    b = g.bounds; s = width / max(b[2] - b[0], b[3] - b[1])
    return affinity.rotate(affinity.scale(g, s, s, origin=(0, 0)), rot, origin=(0, 0))


def konpeito_pair():
    import kjsvg
    body, tint, sp = kjsvg.konpeito_geoms(8.0, 8.0, 10.0)
    from shapely.ops import unary_union
    return raster(unary_union([body, tint] + sp))


def test_outline_gate_red_green(monkeypatch):
    import kjcompare as C
    from scipy import ndimage as ndi
    ref = konpeito_pair()
    fat = ndi.binary_dilation(ref, iterations=3)                    # +0.15 mm all round: a real DST is a bit fatter
    b = ref.any(axis=0).nonzero()[0]; w = (b[-1] - b[0] + 1) / PPM
    star = raster(affinity.translate(star5(w * 1.05), 8.0, 8.0))
    *_, ok_fat = C.candy_metrics(ref, fat)
    iou_s, wr, hr, p90_s, ok_star = C.candy_metrics(ref, star)
    assert ok_fat, "a slightly fat konpeito must pass"
    assert not ok_star, f"a 5-point star must fail (IoU {iou_s:.2f}, outline p90 {p90_s} mm)"
    # the star is close enough that IoU + extents alone pass it: only the outline catches it
    assert iou_s >= 0.70 and min(wr, 1 / wr, hr, 1 / hr) >= 0.80
    assert p90_s > C.OUTLINE_MAX
    # mutation: with the outline check off, the star passes -> the outline is the guard
    monkeypatch.setattr(C, "OUTLINE_MAX", 99.0)
    *_, ok_star_no_outline = C.candy_metrics(ref, star)
    assert ok_star_no_outline


def write_svg(circles):
    """circles: [(cx, cy, r)] -> SVG with the border layer id of the founder's files."""
    els = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#FBF8F1"/>' for x, y, r in circles)
    s = (f'<svg xmlns="http://www.w3.org/2000/svg" width="20mm" height="10mm" viewBox="0 0 20 10">'
         f'<g id="03_border_motifs_WHITE">{els}</g></svg>')
    p = os.path.join(tempfile.mkdtemp(), "b.svg"); open(p, "w").write(s); return p


def write_dots(dots):
    """dots: [(cx, cy, span)] -> one-stop DST of satin zigzags spanning `span` mm across each dot."""
    p = pe.EmbPattern(); p.add_thread(pe.EmbThread("#FBF8F1"))
    for cx, cy, span in dots:
        p.add_stitch_absolute(pe.JUMP, cx * 10, cy * 10)
        for k in range(9):
            a = math.radians(20 * k); h = span / 2
            for sgn in (1, -1):
                p.add_stitch_absolute(pe.STITCH, (cx + sgn * h * math.cos(a)) * 10, (cy + sgn * h * math.sin(a)) * 10)
        p.add_command(pe.TRIM)
    p.add_command(pe.END)
    path = os.path.join(tempfile.mkdtemp(), "d.dst"); pe.write_dst(p, path); return path


def test_dot_rows_red_green():
    import kjcompare as C
    svg = write_svg([(4, 5, 0.75), (10, 5, 0.75), (16, 5, 0.75)])
    rj = dict(origin_mm=[0.0, 0.0])
    good = write_dots([(4, 5, 1.7), (10, 5, 1.7), (16, 5, 1.7)])
    assert all(r["ok"] for r in C.dot_rows(good, rj, svg, [1]))
    bad = write_dots([(4, 5, 1.1), (10.6, 5, 1.7), (16, 5, 2.4)])     # too small, 0.6 mm off, too big
    assert [r["ok"] for r in C.dot_rows(bad, rj, svg, [1])] == [False, False, False]
    missing = write_dots([(4, 5, 1.7)])
    assert [r["ok"] for r in C.dot_rows(missing, rj, svg, [1])] == [True, False, False]


def test_area_gates_red_green():
    import kjcompare as C, kjsvg
    B = kjsvg.border_refs("inputs/svg/HAKI_coin-pocket_konpeito_ART.svg", 76.0, 56.0)
    rj = dict(per_stop=[dict(col="kj_red", codes=["BAND"]), dict(col="kj_cream", codes=["FIELD"]), dict(col="kj_red", codes=["EDGE"])])
    M = {0: B["band"].copy(), 1: B["field"].copy(), 2: B["edge"].copy()}
    areas, unc = C.area_gates(B, M, rj)
    assert all(a["ok"] for a in areas) and not unc
    ys, xs = np.nonzero(B["band"]); y, x = ys[len(ys) // 2], xs[len(xs) // 2]
    M[0][y - 20:y + 20, x - 20:x + 20] = False                        # 2 x 2 mm bare in the band
    areas, unc = C.area_gates(B, M, rj)
    assert not next(a for a in areas if a["area"] == "red band")["ok"] and unc


def test_candy_position_red_green():
    import kjcompare as C
    ref = konpeito_pair()
    rj = dict(per_stop=[dict(col="kj_pink", codes=["STAR"])])
    to_px = lambda x, y: (x * PPM, y * PPM)
    p = dict(col="kj_pink", cx=8.0, cy=8.0)
    assert C.candy_position({0: ref}, rj, p, to_px) <= C.POS_MAX
    shifted = np.roll(ref, 2 * PPM, axis=1)                          # sewn 2 mm off
    e = C.candy_position({0: shifted}, rj, p, to_px)
    assert e > C.POS_MAX and abs(e - 2.0) < 0.2


# ---- PR #34 review item 1: a pink + a yellow konpeito that touch were traced as ONE blob (S06, size 15 px) -------------
def _blob(x, y, w, h):
    return ("pink", (slice(y, y + h), slice(x, x + w)), np.ones((h, w), bool))


def test_merge_guard_red_green():
    import kjfront
    ok = [_blob(10 * i, 0, 10, 10) for i in range(8)] + [_blob(100, 0, 9, 11)]
    kjfront.check_merges(ok)                                     # green: every blob within 1.3 x the median
    with pytest.raises(ValueError, match="merged"):
        kjfront.check_merges(ok + [_blob(200, 0, 15, 10)])       # red: the Rev B3 S06 case (15 px vs median 10)


def test_front_trace_splits_the_touching_pair_and_guard_catches_the_old_way():
    """real mockup: the 4th soot sprite carries a pink AND a yellow konpeito. The per-colour trace must return both;
    the Rev B3 all-hue labelling of the same pixels must trip the merge guard (the guard catches the original bug)."""
    import kjfront, classify as CL
    from scipy import ndimage as ndi
    G = kjfront.geometry(); st = kjfront.trace(G)
    near = [d for d in st if math.dist(d["px"], (897, 279)) < 8]
    assert sorted(d["col"] for d in near) == ["pink", "yellow"], near
    assert len([d for d in st if not d['clipped']]) == 14 and len(st) == 17      # detected (trace); the map drops the 3 clipped (J4)
    a = np.asarray(Image.open(kjfront.SRC).convert("RGB")).astype(float); h, s, v = CL.hsv(a)
    m = (s > 0.45) & (v > 0.5) & (((h > 300) | (h < 15)) | ((h > 180) & (h < 215)) | ((h > 35) & (h < 65)))
    m[:, :770] = False; m[:, 1000:] = False; m[60:186, 893:992] = False
    lab, _ = ndi.label(ndi.binary_dilation(m, iterations=1))
    blobs = [("x", sl, lab[sl] == i) for i, sl in enumerate(ndi.find_objects(lab), 1) if (lab[sl] == i).sum() >= 6]
    with pytest.raises(ValueError, match="merged"):
        kjfront.check_merges(blobs)


# ---- PR #34 round 2: candies clipped by the side seam on the mockup (1-3 px slivers) were under the 6 px floor ---------
CLIPPED_MOCKUP = [("blue", (831, 343)), ("yellow", (830, 352)), ("yellow", (824, 400))]   # reviewer's zoom, mockup px


def _clipped_found(st):
    return [c for c, xy in CLIPPED_MOCKUP if any(d["col"] == c and d["clipped"] and math.dist(d["px"], xy) < 4 for d in st)]


def test_clipped_side_seam_candies_detected_and_excluded(monkeypatch):
    """founder 21 Oct (J4): the 3 clipped side-seam candies are DROPPED from this product, but the engine edge pass must
    still DETECT them. green: trace finds all 3 (flagged clipped), product_map excludes exactly those 3 -> 14 whole,
    renumbered S01..S14, none clipped. red: (a) without the edge pass only 1 of 3 is detected (the Rev B4 bug);
    (b) with EXCLUDE_CLIPPED off the map is 17 again (the exclusion is what drops them)."""
    import kjfront
    G = kjfront.geometry(); st = kjfront.trace(G)
    assert _clipped_found(st) == [c for c, _ in CLIPPED_MOCKUP]                       # detected
    kept, dropped = kjfront.product_map(st)
    assert len(kept) == 14 and not any(d["clipped"] for d in kept)                    # excluded
    assert len(dropped) == 3 and _clipped_found(dropped) == [c for c, _ in CLIPPED_MOCKUP]
    assert [d["id"] for d in kept] == [f"S{k:02d}" for k in range(1, 15)]
    # the shipped map (out/front_stars.json) is the product map
    import json
    F = json.load(open("out/front_stars.json"))
    assert len(F["stars"]) == 14 and not any(d["clipped"] for d in F["stars"]) and len(F["excluded_clipped"]) == 3
    monkeypatch.setattr(kjfront, "EXCLUDE_CLIPPED", False)
    assert len(kjfront.product_map(st)[0]) == 17                                       # red (b)
    monkeypatch.setattr(kjfront, "edge_slivers", lambda *a, **k: [])
    assert len(_clipped_found(kjfront.trace(G))) == 1                                  # red (a): the Rev B4 bug


def test_soot_sprites_traced_and_gated():
    """founder 21 Oct (J5): the soot sprites are kept. The trace finds the 9 sprites of the mockup (one per eye pair);
    the sprite gate passes the shipped DSTs and fails a sprite moved 2 mm (red)."""
    import json, kjfront, kjsoot
    G = kjfront.geometry(); soot = kjfront.trace_soot(G)
    assert len(soot) == 9
    for q in soot:
        assert all(math.hypot(*e) + kjfront.SOOT_EYE[0] * q["d_mm"] / 2 <= q["d_mm"] / 2 for e in q["eyes_mm"])   # eyes inside the body
    rows = kjsoot.run()
    assert len(rows) == 9 and all(r["ok"] for r in rows)
    import kjcompare as C
    F = json.load(open("out/front_stars.json")); q = dict(F["soot"][0]); q["x_from_side_mm"] += 2.0
    stem = kjsoot.FILES["front1"]; rj = json.load(open(f"out/stitch/{stem}.json"))
    x0, y0 = q["x_from_side_mm"] - 16, q["y_from_waist_mm"] - 16
    to_px = lambda x, y: ((x - x0) * C.PPM, (y - y0) * C.PPM); shape = (32 * C.PPM, 32 * C.PPM)
    M = C.dst_masks_on(f"out/stitch/{stem}.dst", rj["origin_mm"], shape, to_px)
    r = kjsoot.sprite_gate(q, M, to_px, shape)
    assert not r["ok"] and r["pos_mm"] > kjsoot.POS_MAX


def test_soot_art_gates_red_on_b7_green_on_b8(tmp_path):
    """Rev B8 (founder 22 Oct: 'the eyes all look crazy and cracked out; some limbs are missing'). The B7 gate passed 9/9
    because it counted white blobs. The art gate checks the DST against inputs/soot_art.json (hand-read from the mockup):
    limbs, shared gaze, eye size, eye satin density/split. Red: the shipped Rev B7 DSTs (tests/fixtures/konpeito_b7) fail
    on EVERY new check for every sprite; green: the B8 build passes 9/9; mutations of the table turn single checks red."""
    import copy, json, kjsoot, kjfront
    b7_dir = os.path.join(ROOT, "tests", "fixtures", "konpeito_b7")
    red = kjsoot.run(b7_dir, str(tmp_path / "g7.json"), str(tmp_path / "c7.png"))
    assert len(red) == 9 and not any(r["ok"] for r in red)
    assert not any(r["limbs_ok"] for r in red)                                    # (a) limbs: B7 = 2 fixed stub legs
    assert all(r["gaze_agree_mm"] > kjsoot.GAZE_AGREE for r in red)               # (b) pupils look different ways
    assert all(r["eye_area_err_pct"] > 100 * kjsoot.EYE_AREA_TOL for r in red)    # (c) eyes too small
    assert all(r["row_gap_mm"] > kjsoot.ROW_GAP_MAX for r in red)                 # (d) open satin = the "cracks"
    assert all(r["pos_mm"] <= kjsoot.POS_MAX and r["eyes"] == 2 for r in red)     # ... while the old checks still pass
    green = kjsoot.run(out=str(tmp_path / "g8.json"), sheet_png=str(tmp_path / "c8.png"))
    assert len(green) == 9 and all(r["ok"] for r in green)
    # mutations on the B8 DST: drop a limb from the table / turn one sprite's gaze -> that sprite goes red
    art = copy.deepcopy(kjfront.soot_art()); art["sprites"]["K01"]["limbs"].pop(0)
    art["sprites"]["K05"]["eyes"]["gaze"] = [0.65, 0.0]
    rows = {r["id"]: r for r in kjsoot.run(out=str(tmp_path / "gm.json"), sheet_png=str(tmp_path / "cm.png"), art=art)}
    assert not rows["K01"]["limbs_ok"] and rows["K01"]["limbs_dst"] == 4 and rows["K01"]["limbs_art"] == 3
    assert not rows["K05"]["ok"] and rows["K05"]["gaze_err_mm"] > kjsoot.GAZE_MAX
    assert rows["K09"]["ok"]


# ---- Rev B9 (founder 23 Oct: "a lot of the arms are upside down of the soot sprites ... k9, 8 5, and 1") -------------
def _arm_mask(pts, ppm=PPM, W=40, H=40):
    im = Image.new("L", (W * ppm, H * ppm), 0); d = ImageDraw.Draw(im)
    d.line([(x * ppm, y * ppm) for x, y in pts], fill=255, width=int(0.35 * ppm) + 1)
    return np.asarray(im) > 0


def test_arm_shape_catches_root_and_arch():
    """kjsoot.arm_shape on drawn arms (body centre (20, 20), R 7.1, candy up-right at (31, 8)):
    the reference "J" (shoulder, out, up) passes; B8's antenna (off the top, over, down to the candy) fails the root
    band AND the arch; an arm on the side away from the candy fails the side test."""
    import kjsoot
    c, cand = (20 * PPM, 20 * PPM), (31 * PPM, 8 * PPM)
    ok = lambda r: r["side"] and abs(r["elev_deg"]) <= kjsoot.ROOT_BAND_DEG and r["arch_mm"] <= kjsoot.ARCH_TOL
    J = kjsoot.arm_shape(_arm_mask([(28.5, 19), (30, 19), (30.5, 18), (30.5, 12)]), c, cand)
    assert ok(J) and J["arch_mm"] < 0.2 and abs(J["elev_deg"]) < 10
    n = kjsoot.arm_shape(_arm_mask([(22, 11.5), (24, 6), (28, 5), (30, 9)]), c, cand)          # inverted "n"
    assert not ok(n) and n["elev_deg"] > kjsoot.ROOT_BAND_DEG and n["arch_mm"] > kjsoot.ARCH_TOL
    back = kjsoot.arm_shape(_arm_mask([(11.5, 19), (10, 19), (9.5, 12)]), c, cand)          # shoulder on the far side
    assert not back["side"] and not ok(back)


def test_soot_arms_red_on_b8_green_on_b9(tmp_path):
    """B8 passed 'limbs 3/3' with the arms upside down: a limb count doesn't check direction. Red: the shipped B8 DSTs
    (tests/fixtures/konpeito_b8, md5 = the B8 SAMPLE READY zip) with the B8 art table fail the arm check on exactly the
    sprites the founder named (K01, K05, K08, K09) while every older check still passes on them. Green: B9 9/9."""
    import json, kjsoot
    b8 = os.path.join(ROOT, "tests", "fixtures", "konpeito_b8")
    red = {r["id"]: r for r in kjsoot.run(b8, str(tmp_path / "g8.json"), str(tmp_path / "c8.png"),
                                         art=json.load(open(os.path.join(b8, "soot_art_b8.json"))))}
    assert sorted(i for i, r in red.items() if not r["arms_ok"]) == ["K01", "K05", "K08", "K09"]
    for i, r in red.items():
        assert r["limbs_ok"] and r["ok"] == r["arms_ok"]                             # only the arm check turns them red
    b9 = os.path.join(ROOT, "tests", "fixtures", "konpeito_b9")
    green = kjsoot.run(b9, str(tmp_path / "g9.json"), str(tmp_path / "c9.png"))
    assert len(green) == 9 and all(r["ok"] and r["arms_ok"] for r in green)
    for r in green:
        for l in r["limb_detail"]:
            if l["kind"] == "arm" and r["id"] != "K06":                              # K06: raised empty arms, no candy
                assert abs(l["elev_deg"]) <= 15 and l["arch_mm"] <= kjsoot.ARCH_TOL
