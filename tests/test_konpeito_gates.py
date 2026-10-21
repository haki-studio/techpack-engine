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
    assert len([d for d in st if not d['clipped']]) == 14 and len(st) == 17
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


def test_clipped_side_seam_candies_mapped(monkeypatch):
    """green: all 3 clipped candies on the side-seam edge are on the map, moved in to the keep-out.
    red: without the edge-sliver pass (the Rev B4 trace) two of the three go missing."""
    import kjfront
    G = kjfront.geometry(); st = kjfront.trace(G)
    assert _clipped_found(st) == [c for c, _ in CLIPPED_MOCKUP]
    for d in st:
        if d["clipped"]:
            assert d["moved_in_mm"] and d["x_from_side_mm"] >= kjfront.SIDE_KO + kjfront.STAR_D / 2 - 0.01
    monkeypatch.setattr(kjfront, "edge_slivers", lambda *a, **k: [])
    assert len(_clipped_found(kjfront.trace(G))) == 1                 # only the old S10 survives: the Rev B4 bug
