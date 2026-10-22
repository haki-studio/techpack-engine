"""TD input JSON + renderer (design §1 rule of the partnership, §5 comment sheet): TDs write rows with a source on
every number; the engine renders the "TD: ..." page notes and the factory comment sheet; a photo estimate is labelled
as one and can never drive a PATTERN change."""
import copy, json, os, re
import pytest
from td import schema
from td.schema import TDInputError, PHOTO
from td import render as R
from sheet import SW, SH

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures", "td", "round2.json")


def raw(): return json.load(open(FIX))


def row(d, rid): return next(r for r in d["rows"] if r["id"] == rid)


def texts(svg): return [re.sub(r"<[^>]+>", "", m) for m in re.findall(r"<text[^>]*>.*?</text>", svg, re.S)]


# ----------------------------------------------------------------------------- schema
def test_fixture_loads_with_every_number_sourced():
    td = schema.load(FIX)
    assert [r.id for r in td.rows] == ["F1", "F2", "F3", "S1", "S2", "M1"]
    for r in td.rows:
        for n in r.nums(): assert n.source in schema.SOURCES and n.ref
    f1 = td.rows[0]
    assert f1.change() == pytest.approx(-0.3)           # computed from target - baseline, never typed
    assert f1.baseline.ref.endswith("#E2") and f1.target.ref.endswith("#C2")


@pytest.mark.parametrize("where", ["row", "baseline", "target"])
def test_photo_estimate_refused_in_a_pattern_change(where):
    d = raw(); f1 = row(d, "F1")
    if where == "row": f1["source"] = "photo_estimate"; f1["baseline"].pop("source", None)
    else: f1[where]["source"] = "photo_estimate"
    with pytest.raises(TDInputError, match="photo_estimate refused in a PATTERN-change row"):
        schema.parse(d)


def test_stated_change_from_photo_refused():
    d = raw(); f1 = row(d, "F1"); del f1["target"]
    f1.update(value=-0.3, source="photo_estimate", ref="IMG_9"); f1["baseline"]["source"] = "file+cell"
    with pytest.raises(TDInputError, match="photo_estimate refused"):
        schema.parse(d)


@pytest.mark.parametrize("field,bad,msg", [
    ("source", "guess", "source 'guess' is not one of"),
    ("lens", None, "missing 'lens'"),
    ("severity", "urgent", "severity 'urgent' is not one of"),
    ("value", "36.5", "value must be a number"),
    ("unit", "in", "unit 'in' is not one of"),
    ("ref", "measured_sheet.csv", "a file\\+cell ref is '<file>#<cell>'"),
])
def test_bad_rows_name_the_field(field, bad, msg):
    d = raw(); r = row(d, "F2")
    if bad is None: r.pop(field)
    else: r[field] = bad
    with pytest.raises(TDInputError, match=msg):
        schema.parse(d)


def test_contradictions_refused():
    d = raw(); row(d, "M1")["hold"] = True
    with pytest.raises(TDInputError, match="only a pom row can be held"): schema.parse(d)
    d = raw(); d["rows"].append(dict(row(d, "F2"), id="F9", point="front rise"))
    with pytest.raises(TDInputError, match="both a PATTERN change and on the HOLD list"): schema.parse(d)
    d = raw(); d["rows"].append(dict(row(d, "F2")))
    with pytest.raises(TDInputError, match="used twice"): schema.parse(d)
    d = raw(); row(d, "F1").update(value=-0.3, ref="tests/fixtures/td/pom_signed.csv#C2")
    with pytest.raises(TDInputError, match="not both"): schema.parse(d)
    d = raw(); row(d, "F1").pop("location")
    with pytest.raises(TDInputError, match="needs 'location'"): schema.parse(d)
    d = raw(); row(d, "M1").pop("ref")
    with pytest.raises(TDInputError, match="photo or page reference"): schema.parse(d)


# ----------------------------------------------------------------------------- comment sheet
def test_comment_sheet_hold_first_then_pattern_with_standing_lines():
    L = R.sheet_lines(schema.load(FIX))
    heads = [s for k, s in L if k == "h"]
    assert heads[0].startswith("HOLD") and heads[1].startswith("PATTERN")
    text = [s for _, s in L]
    assert "Rev C — supersedes Rev B" in text
    assert "back rise M: keep at 36.5 cm" in text and "thigh M: keep at 33 cm" in text
    pat = next(s for s in text if s.startswith("front rise M ·"))
    assert "26.5 cm → 26.2 cm" in pat and "change -0.3 cm" in pat and "lower the CF rise" in pat
    assert any("CHECK after this change: thigh, front crotch curve" in s for s in text)
    assert R.STANDING_PATTERN.format(points="front rise M") in text
    assert text[-1] == R.STANDING_SA
    m1 = next(s for s in text if s.startswith("back pocket:"))
    assert "see photo IMG_2240" in m1


def test_photo_estimate_rendered_as_approx_everywhere():
    td = schema.load(FIX)
    s2 = next(s for _, s in R.sheet_lines(td) if s.startswith("waist M"))
    assert PHOTO in s2 and "≈ 41 cm" in s2
    note = R.note_text(next(r for r in td.rows if r.id == "S2"))
    assert PHOTO in note and "photo IMG_2231" in note


def test_pattern_change_without_hold_list_never_reaches_a_factory():
    d = raw(); d["rows"] = [r for r in d["rows"] if not r.get("hold")]
    with pytest.raises(TDInputError, match="no HOLD list"):
        R.sheet_lines(schema.parse(d))


def test_pattern_change_without_measured_baseline_is_flagged_red():
    d = raw(); f1 = row(d, "F1"); f1.pop("baseline"); f1.pop("target")
    f1.update(value=-0.3, source="file+cell", ref="tests/fixtures/td/pom_signed.csv#C2")
    L = R.sheet_lines(schema.parse(d))
    k, s = next((k, s) for k, s in L if s.startswith("front rise M ·"))
    assert k == "warn" and "NO MEASURED SHEET ON FILE" in s and "change -0.3 cm" in s


def test_comment_sheet_pages_and_overflow():
    td = schema.load(FIX)
    pages = R.comment_sheet(td)
    assert len(pages) == 1 and "TD comment sheet — td-fixture-trouser" in "".join(texts(pages[0]))
    d = raw(); d["rows"] += [dict(row(d, "M1"), id=f"M{i + 2}", comment=f"loose thread at the hem, point {chr(65 + i % 26)}")
                             for i in range(80)]
    many = R.comment_sheet(schema.parse(d))
    assert len(many) >= 2 and "C1_2" in "".join(texts(many[1]))
    allt = "".join("".join(texts(p)) for p in many)
    assert allt.count("loose thread at the hem") == 80          # nothing dropped at a page break


# ----------------------------------------------------------------------------- annotations
def page_svg():
    from sheet import header, doc, t
    return doc(header("T3 test page", "sub", "T3") + [t(20, 190, "content at the foot", 2, 400)])


def test_annotation_band_scales_page_and_lists_notes():
    td = schema.load(FIX)
    out = R.annotate(page_svg(), td.page_rows("T3"))
    tx = texts(out)
    notes = [s for s in tx if s.startswith("TD (")]
    assert len(notes) == 3                                       # F1, S1, S2 carry page T3
    assert notes[0].startswith("TD (fit · high): PATTERN front rise M: 26.5 → 26.2 cm (change -0.3 cm)")
    assert any(PHOTO in s for s in tx)
    m = re.search(r'scale\(([\d.]+)\)', out); k = float(m.group(1))
    assert 0.8 < k < 1                                            # content shrunk uniformly to make room, not covered
    assert "content at the foot" in tx
    assert R.annotate(page_svg(), []) == page_svg()


def test_annotation_refuses_a_non_a4_page():
    with pytest.raises(TDInputError, match="not an engine A4 page"):
        R.annotate('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"></svg>', schema.load(FIX).rows)


def test_annotation_overflow_says_how_many_more():
    d = raw(); d["rows"] += [dict(row(d, "M1"), id=f"M{i + 2}", page="T3") for i in range(20)]
    tx = texts(R.annotate(page_svg(), schema.parse(d).page_rows("T3")))
    assert any(re.match(r"\+ \d+ more lines — see the TD comment sheet", s) for s in tx)


def test_pages_render_to_png():
    import cairosvg
    td = schema.load(FIX)
    for svg in R.comment_sheet(td) + [R.annotate(page_svg(), td.page_rows("T3"))]:
        assert cairosvg.svg2png(bytestring=svg.encode(), output_width=600)[:4] == b"\x89PNG"


# ----------------------------------------------------------------------------- family pack integration
def tee_td(page="T3"):
    return {"product": "alabasta", "round": "fit sample round 1", "rev": "A", "rows": [
        {"id": "S1", "kind": "tolerance", "point": "Chest", "lens": "spec", "severity": "medium", "page": page,
         "value": 1, "unit": "cm", "source": "file+cell", "ref": "families/tee/family.yaml#pom_chart.base.poms.B.tol"},
        {"id": "M1", "kind": "comment", "point": "shoulder seam", "lens": "make", "severity": "high", "page": "T4",
         "comment": "send a close-up of the visible shoulder seam finish", "ref": "page T4"}]}


def test_family_pack_carries_td_notes_and_the_comment_sheet(tmp_path):
    from family.build import build
    from family.spec import SpecError
    ala = os.path.join(ROOT, "families", "tee", "variants", "alabasta.yaml")
    r = build(ala, out_root=str(tmp_path), png=False, td=tee_td())
    assert os.path.exists(r["td_sheet"]) and r["td_sheet"].endswith("alabasta_td_comment_sheet_RevA.pdf")
    from pypdf import PdfReader
    pdf = PdfReader(r["pdf"]); codes = [c for c, _, _ in r["pages"]]
    t3 = pdf.pages[codes.index("T3")].extract_text(); t4 = pdf.pages[codes.index("T4")].extract_text()
    assert "TD (spec · medium): tolerance Chest" in t3 and "TD (make · high)" in t4
    assert "TD (" not in pdf.pages[codes.index("T5")].extract_text()
    with pytest.raises(SpecError, match="pages this pack does not have: T99"):
        build(ala, out_root=str(tmp_path), png=False, td=tee_td("T99"))


def test_bad_td_sheet_stops_the_build_before_any_pack_file_is_written(tmp_path):
    from family.build import build
    ala = os.path.join(ROOT, "families", "tee", "variants", "alabasta.yaml")
    d = raw(); d["product"] = "alabasta"
    for r in d["rows"]: r.pop("page", None)
    d["rows"] = [r for r in d["rows"] if not r.get("hold")]                  # PATTERN change, no HOLD list
    with pytest.raises(TDInputError, match="no HOLD list"):
        build(ala, out_root=str(tmp_path), png=False, td=d)
    assert not any(f.endswith(".pdf") for _, _, fs in os.walk(str(tmp_path)) for f in fs)


def test_cli_keeps_tracebacks_for_real_bugs(monkeypatch, tmp_path):
    from family import build as B
    ala = os.path.join(ROOT, "families", "tee", "variants", "alabasta.yaml")
    def boom(*a, **k): raise ValueError("a bug, not an input mistake")
    monkeypatch.setattr(B, "build", boom)
    with pytest.raises(ValueError, match="a bug"):
        B.main([ala, "--out", str(tmp_path)])
    def bad_input(*a, **k): raise TDInputError("rows[0]: missing 'lens'")
    monkeypatch.setattr(B, "build", bad_input)
    assert B.main([ala, "--out", str(tmp_path)]) == 1
