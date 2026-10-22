"""pattern_diff (TD design §4 "Pattern version"): read a DXF / vector 1:1 PDF, check the scale on BOTH axes, walk the
seam pairs a TD maps, report crotch depth + length, and diff against the signed pattern. Tested on our own DXF writer
(pattern_out) with a planted 3 mm front-rise error, and on the real Drum Island pattern against pattern_out.measure."""
import math, os, types
import pytest
import ezdxf
import pattern as PT
import pattern_out as PO
import pattern_diff as PD

TMP = None


def bez(p0, p1, p2, p3, n=24):
    return [tuple((1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t ** 3 * d
                  for a, b, c, d in zip(p0, p1, p2, p3)) for t in (i / n for i in range(n + 1))]


def trouser(rise_plant=0.0):
    """a small 2-piece trouser block (mm, y down): edges waist, side, hem, inseam, rise. rise_plant raises the CF waist."""
    def piece(code, name, cf_top, side_top, ext, depth, hem_in, hem_out, waist_w):
        cw = (0.0, cf_top); sw = (waist_w, side_top)
        crotch = (-ext, depth)
        rise = [cw, (0.0, depth - 80)] + bez((0.0, depth - 80), (0.0, depth - 25), (-ext * 0.45, depth), crotch)[1:]
        edges = [PT.Edge("waist", [cw, sw], 10), PT.Edge("side", [sw, (waist_w - 15, 1000.0)], 10),
                 PT.Edge("hem", [(waist_w - 15, 1000.0), (hem_in, 1000.0)], 30),
                 PT.Edge("inseam", [(hem_in, 1000.0), crotch], 10), PT.Edge("rise", rise[::-1], 10)]
        return PT.Piece(code, name, 2, "denim", edges, ((waist_w / 2, 300.0), (waist_w / 2, 700.0)))
    g = {"F01": piece("F01", "FRONT", -rise_plant, 0.0, 55.0, 260.0, 15.0, 0, 240.0),
         "B01": piece("B01", "BACK", -35.0, 0.0, 110.0, 275.0, -15.0, 0, 250.0)}
    return types.SimpleNamespace(draft=lambda size: (g, {}), ORDER=["F01", "B01"])


def write(tmp, name, blk, pdf=False):
    p = os.path.join(tmp, name)
    if pdf: PO.plot_pdf("M", p, blk=blk, style="TD-TROUSER", emb=False)
    else: PO.write_dxf(["M"], p, blk=blk, style="TD-TROUSER", emb=False)
    return p


MAP = {"pieces": {"front": {"name": "F01"}, "back": {"name": "B01"}},
       "seams": [{"name": "side seam", "a": ["front", 1], "b": ["back", 1], "ease_mm": 0, "tol_mm": 2},
                 {"name": "inseam", "a": ["front", 3], "b": ["back", 3], "ease_mm": 0, "tol_mm": 40}],
       "curves": [{"name": "front crotch", "piece": "front", "edge": 4}, {"name": "back crotch", "piece": "back", "edge": 4}]}


def rise_map(target):
    return dict(MAP, poms=[{"name": "front rise", "piece": "front", "edge": 4, "target_mm": target, "tol_mm": 2,
                             "source": "signed POM, round 1"}])


def test_reads_our_dxf_and_maps_the_trouser(tmp_path):
    pat = PD.read(write(str(tmp_path), "r1.dxf", trouser()))
    assert [p.label.split()[0] for p in pat.pieces] == ["F01", "B01"] and all(p.line == "sew line" for p in pat.pieces)
    assert [len(p.edges) for p in pat.pieces] == [5, 5]
    rise = PD.alen(pat.pieces[0].edges[4]); want = PT.alen(trouser().draft("M")[0]["F01"].edges[4].pts)
    assert rise == pytest.approx(want, abs=0.05)                   # the file says what the block drew
    rep = PD.run(pat, rise_map(round(rise, 1)))
    assert rep.ok, rep.lines()
    c = PD.crotch(pat.pieces[0].edges[4])
    assert c["depth"] == pytest.approx(260, abs=0.1) and c["extension"] == pytest.approx(55, abs=0.1)
    assert any(l.startswith("curve front crotch: depth 260.0 mm, extension 55.0 mm") for l in rep.lines())


def test_planted_3mm_front_rise_error_is_flagged(tmp_path):
    signed = PD.read(write(str(tmp_path), "signed.dxf", trouser()))
    target = round(PD.alen(signed.pieces[0].edges[4]), 1)
    new = PD.read(write(str(tmp_path), "factory_r2.dxf", trouser(rise_plant=3.0)))
    rep = PD.run(new, rise_map(target), signed=signed)
    flags = "\n".join(rep.flags)
    assert not rep.ok
    assert f"POM front rise: pattern {target + 3:.1f} mm vs signed {target:g} mm -> +3.0 mm (tol ±2)" in flags
    assert "vs signed: front edge 4:" in flags and "(+3.0) — unsigned change over tolerance" in flags
    assert "side seam" not in flags                                 # the neighbours did not move


def test_vector_pdf_two_axis_scale_and_same_numbers_as_dxf(tmp_path):
    d = PD.read(write(str(tmp_path), "r1.dxf", trouser()))
    p = PD.read(write(str(tmp_path), "r1.pdf", trouser(), pdf=True))
    assert p.scale["x"] == pytest.approx(100, abs=0.05) and p.scale["y"] == pytest.approx(100, abs=0.05)
    assert [round(PD.alen(e), 1) for e in p.pieces[0].edges] == [round(PD.alen(e), 1) for e in d.pieces[0].edges]


def scaled_pdf(src, dst, sx, sy):
    from pypdf import PdfReader, PdfWriter, Transformation
    w = PdfWriter()
    for pg in PdfReader(src).pages:
        w.add_page(pg).add_transformation(Transformation().scale(sx, sy))
    w.write(dst)


@pytest.mark.parametrize("sx,sy,axis", [(0.97, 0.97, "x"), (1.0, 0.97, "y")])
def test_a_scaled_plot_cant_be_diffed(tmp_path, sx, sy, axis):
    src = write(str(tmp_path), "r1.pdf", trouser(), pdf=True); dst = os.path.join(str(tmp_path), "scaled.pdf")
    scaled_pdf(src, dst, sx, sy)
    with pytest.raises(PD.CantDiff, match=rf"can't diff: need vector PDF or DXF — scale check failed: the 100 mm reference measures 97.0 mm on {axis}"):
        PD.read(dst)


def test_no_units_no_ruler_or_a_photo_cant_be_diffed(tmp_path):
    doc = ezdxf.new("R12"); doc.layers.add("1")
    doc.modelspace().add_polyline2d([(0, 0), (500, 0), (500, 900), (0, 900)], close=True, dxfattribs={"layer": "1"})
    p = os.path.join(str(tmp_path), "nounits.dxf"); doc.saveas(p)
    with pytest.raises(PD.CantDiff, match="the drawing unit is not stated"): PD.read(p)
    doc.modelspace().add_text("Units: mm", dxfattribs={"insert": (10, 10), "height": 5})
    doc.modelspace().add_line((0, -50), (97, -50)); doc.modelspace().add_text("100 mm", dxfattribs={"insert": (20, -45), "height": 4})
    doc.saveas(p)
    with pytest.raises(PD.CantDiff, match="the 100 mm ruler measures 97.0 mm on x"): PD.read(p)
    with pytest.raises(PD.CantDiff, match="not a DXF or a vector PDF"): PD.read(os.path.join(str(tmp_path), "IMG_2231.jpg"))
    pdf = os.path.join(str(tmp_path), "noruler.pdf")
    import cairosvg
    cairosvg.svg2pdf(bytestring=b'<svg xmlns="http://www.w3.org/2000/svg" width="300mm" height="300mm" viewBox="0 0 300 300">'
                     b'<path d="M10,10 L250,10 L250,280 L10,280 Z" fill="none" stroke="#000"/></svg>', write_to=pdf)
    with pytest.raises(PD.CantDiff, match="no scale box \\+ vertical 100 mm ruler"): PD.read(pdf)


def test_real_drum_island_pattern_matches_pattern_out_measure(tmp_path):
    PO.write_dxf(["M"], os.path.join(str(tmp_path), "drum.dxf"), emb=False)
    pat = PD.read(os.path.join(str(tmp_path), "drum.dxf"))
    m = {"pieces": {"back": {"name": "B01"}, "front": {"name": "F01"}},
         "seams": [{"name": "side", "a": ["back", 4], "b": ["front", 4], "tol_mm": 1.5},
                   {"name": "shoulder", "a": ["back", 2], "b": ["front", 2], "tol_mm": 1.5}]}
    rep = PD.run(pat, m)
    _, walks, _ = PO.measure("M")
    w = {n: (a, b) for n, a, b, _ in walks}
    side = PD.alen(PD.edge_pts(pat, m, "back", 4)[1]); sh_b = PD.alen(PD.edge_pts(pat, m, "back", 2)[1])
    assert side == pytest.approx(w["Side seam: back vs front"][0], abs=0.05)
    assert sh_b == pytest.approx(w["Shoulder: back vs front"][0], abs=0.05)
    assert rep.ok, rep.lines()
