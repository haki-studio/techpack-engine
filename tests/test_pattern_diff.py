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


def trouser(rise_plant=0.0, side_plant=0.0):
    """a small 2-piece trouser block (mm, y down): edges waist, side, hem, inseam, rise. rise_plant raises the CF waist;
    side_plant lowers the front side-seam top (front side seam that much shorter)."""
    def piece(code, name, cf_top, side_top, ext, depth, hem_in, hem_out, waist_w):
        cw = (0.0, cf_top); sw = (waist_w, side_top)
        crotch = (-ext, depth)
        rise = [cw, (0.0, depth - 80)] + bez((0.0, depth - 80), (0.0, depth - 25), (-ext * 0.45, depth), crotch)[1:]
        edges = [PT.Edge("waist", [cw, sw], 10), PT.Edge("side", [sw, (waist_w - 15, 1000.0)], 10),
                 PT.Edge("hem", [(waist_w - 15, 1000.0), (hem_in, 1000.0)], 30),
                 PT.Edge("inseam", [(hem_in, 1000.0), crotch], 10), PT.Edge("rise", rise[::-1], 10)]
        return PT.Piece(code, name, 2, "denim", edges, ((waist_w / 2, 300.0), (waist_w / 2, 700.0)))
    g = {"F01": piece("F01", "FRONT", -rise_plant, side_plant, 55.0, 260.0, 15.0, 0, 240.0),
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


def test_a_photo_or_a_pdf_without_rulers_cant_be_diffed(tmp_path):
    with pytest.raises(PD.CantDiff, match="not a DXF or a vector PDF"): PD.read(os.path.join(str(tmp_path), "IMG_2231.jpg"))
    pdf = os.path.join(str(tmp_path), "noruler.pdf")
    import cairosvg
    cairosvg.svg2pdf(bytestring=b'<svg xmlns="http://www.w3.org/2000/svg" width="300mm" height="300mm" viewBox="0 0 300 300">'
                     b'<path d="M10,10 L250,10 L250,280 L10,280 Z" fill="none" stroke="#000"/></svg>', write_to=pdf)
    with pytest.raises(PD.CantDiff, match="need scale check on both axes"): PD.read(pdf)


def dxf(tmp, name="t.dxf", insunits=None, units_text="Units: mm", xr=100.0, yr=100.0, extra=(), draw=1.0):
    """one 500 x 900 mm piece (drawn at `draw` units per mm) + optional x / y 100 mm references (None = not drawn)"""
    doc = ezdxf.new("R2000"); msp = doc.modelspace()
    doc.header["$INSUNITS"] = 0 if insunits is None else insunits      # ezdxf's R2000 default is 6 (metres)
    for ln in ("1", "7", "8", "15"): doc.layers.add(ln)
    msp.add_lwpolyline([(0, 0), (500 * draw, 0), (500 * draw, 900 * draw), (0, 900 * draw)], close=True, dxfattribs={"layer": "1"})
    if units_text: msp.add_text(units_text, dxfattribs={"insert": (10, 10), "height": 5, "layer": "15"})
    if xr: msp.add_line((0, -50 * draw), (xr * draw, -50 * draw), dxfattribs={"layer": "8"})
    msp.add_text("100 mm", dxfattribs={"insert": (20 * draw, -45 * draw), "height": 4, "layer": "15"})
    if yr: msp.add_line((-40 * draw, -150 * draw), (-40 * draw, (-150 + yr) * draw), dxfattribs={"layer": "8"})
    msp.add_text("100 mm", dxfattribs={"insert": (-37 * draw, -100 * draw), "height": 4, "layer": "15"})
    for lay, a, b in extra: msp.add_line(a, b, dxfattribs={"layer": lay})
    p = os.path.join(tmp, name); doc.saveas(p); return p


def test_dxf_needs_units_and_both_axes(tmp_path):
    t = str(tmp_path)
    pat = PD.read(dxf(t)); e = pat.pieces[0].edges
    assert sorted(round(PD.alen(x)) for x in e) == [500, 500, 900, 900] and pat.scale["fx"] == pytest.approx(1.0)
    with pytest.raises(PD.CantDiff, match="the drawing unit is not stated"): PD.read(dxf(t, units_text=None))
    with pytest.raises(PD.CantDiff, match="need scale check on both axes.*found x: 1, y: 0"): PD.read(dxf(t, yr=None))
    with pytest.raises(PD.CantDiff, match="need scale check on both axes.*found x: 0, y: 1"): PD.read(dxf(t, xr=None))
    with pytest.raises(PD.CantDiff, match="need scale check on both axes.*found x: 0, y: 0"): PD.read(dxf(t, xr=None, yr=None))


@pytest.mark.parametrize("axis", ["x", "y"])
def test_dxf_ruler_off_scale_is_refused_on_either_axis(tmp_path, axis):
    p = dxf(str(tmp_path), **{axis + "r": 97.0})
    with pytest.raises(PD.CantDiff, match=f"the 100 mm reference measures 97.0 mm on {axis}"): PD.read(p)


def test_dxf_claiming_cm_drawn_in_mm_and_unit_conflicts_are_refused(tmp_path):
    t = str(tmp_path)
    with pytest.raises(PD.CantDiff, match="need scale check on both axes"):              # ruler reads 1000 mm
        PD.read(dxf(t, insunits=5, units_text=None))
    assert PD.read(dxf(t, insunits=5, units_text=None, draw=0.1)).pieces              # drawn in cm, says cm: fine
    with pytest.raises(PD.CantDiff, match="\$INSUNITS says 1 mm per unit but the piece text says 'Units: cm'"):
        PD.read(dxf(t, insunits=4, units_text="Units: cm"))


def test_ambiguous_ruler_refused_and_grain_line_ignored(tmp_path):
    t = str(tmp_path)
    with pytest.raises(PD.CantDiff, match="ambiguous scale reference on x: 100.00 / 103.00 mm"):
        PD.read(dxf(t, extra=[("8", (0, -42), (103, -42))]))                           # a ~100 mm edge by the label
    assert PD.read(dxf(t, extra=[("7", (0, -42), (103, -42))])).pieces                # the same line on the grain layer


def test_small_scale_error_is_corrected_not_passed_on(tmp_path):
    src = write(str(tmp_path), "r1.pdf", trouser(), pdf=True); dst = os.path.join(str(tmp_path), "y1004.pdf")
    scaled_pdf(src, dst, 1.0, 1.004)                                                   # 0.4 % on y: inside the 0.5 mm band
    ref = PD.read(src); got = PD.read(dst)
    assert got.scale["y"] == pytest.approx(100.4, abs=0.01) and got.scale["fy"] == pytest.approx(1 / 1.004, abs=1e-4)
    side_ref, side_got = PD.alen(ref.pieces[0].edges[1]), PD.alen(got.pieces[0].edges[1])
    assert side_ref > 990 and abs(side_got - side_ref) < 0.05                          # uncorrected it would be +4 mm
    assert "corrected x 1.0000 / y 0.9960" in PD.run(got, {"pieces": {}}).lines()[0]


def test_rotated_pdf_page_reads_the_same(tmp_path):
    from pypdf import PdfReader, PdfWriter
    src = write(str(tmp_path), "r1.pdf", trouser(), pdf=True); dst = os.path.join(str(tmp_path), "rot.pdf")
    w = PdfWriter()
    for pg in PdfReader(src).pages: w.add_page(pg).rotate(90)
    w.write(dst)
    a, b = PD.read(src), PD.read(dst)
    assert [round(PD.alen(e), 1) for e in a.pieces[0].edges] == [round(PD.alen(e), 1) for e in b.pieces[0].edges]


# ----------------------------------------------------------------------------- seam maths (review #45 finding 1)
def test_planted_side_seam_error_flags(tmp_path):
    rep = PD.run(PD.read(write(str(tmp_path), "s.dxf", trouser(side_plant=5.0))), MAP)
    f = [x for x in rep.flags if x.startswith("seam side seam:")]
    assert f and "mismatch -5.0 mm (tol ±2)" in f[0]
    assert PD.run(PD.read(write(str(tmp_path), "ok.dxf", trouser())), MAP).ok


def test_ease_is_applied_with_its_sign(tmp_path):
    pat = PD.read(write(str(tmp_path), "e.dxf", trouser()))
    la = PD.alen(PD.edge_pts(pat, MAP, "front", 3)[1]); lb = PD.alen(PD.edge_pts(pat, MAP, "back", 3)[1])
    ease = round(la - lb, 1)                                                           # front inseam longer by this much
    def one(e, tol):
        return PD.run(pat, {"pieces": MAP["pieces"], "seams": [{"name": "inseam", "a": ["front", 3], "b": ["back", 3],
                                                                   "ease_mm": e, "tol_mm": tol}]})
    assert one(ease, 1).ok                                                             # at the intended ease: no flag
    r0 = one(0, 2); assert not r0.ok and f"mismatch +{la - lb:.1f} mm" in r0.flags[0]
    rn = one(-ease, 2); assert not rn.ok and f"mismatch +{la - lb + ease:.1f} mm" in rn.flags[0]   # wrong sign doubles


def test_cli_exit_codes(tmp_path, capsys):
    import json
    t = str(tmp_path)
    ok = write(t, "ok.dxf", trouser()); bad = write(t, "bad.dxf", trouser(side_plant=5.0))
    m = os.path.join(t, "map.json"); json.dump(MAP, open(m, "w"))
    assert PD.main([ok]) == 0 and "edge 4:" in capsys.readouterr().out                 # no map: the piece table
    assert PD.main([ok, "--map", m]) == 0
    assert PD.main([bad, "--map", m]) == 1 and "FLAG seam side seam" in capsys.readouterr().out
    pdf = write(t, "r1.pdf", trouser(), pdf=True); sc = os.path.join(t, "sc.pdf"); scaled_pdf(pdf, sc, 0.97, 0.97)
    assert PD.main([sc, "--map", m]) == 2 and "can't diff" in capsys.readouterr().out


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
