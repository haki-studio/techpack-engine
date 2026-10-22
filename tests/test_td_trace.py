"""Numeral-trace gate (design §1): every number a TD supplies must resolve to a real file + cell holding it, and every
numeral printed on the TD comment sheet / TD notes must trace to one of those numbers. Scope: tables + callouts."""
import json, os
import pytest
from td import schema, render as R, trace as T

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures", "td", "round2.json")


def raw(): return json.load(open(FIX))
def row(d, rid): return next(r for r in d["rows"] if r["id"] == rid)


def run(d, extra_svgs=()):
    td = schema.parse(d, FIX)
    return T.check(td, R.comment_sheet(td) + list(extra_svgs))


def test_fixture_traces_and_says_what_it_checked():
    rep = run(raw())
    assert rep.ok, rep.summary()
    assert len(rep.resolved) == 5 and rep.numerals == 7 and rep.pages == 1     # 36.5 33 26.5 26.2 0.3 0.5 41
    assert "5 input numbers resolved to files, 7 numerals checked on 1 page(s) — PASS" in rep.summary()


def test_photo_estimate_mislabelled_file_cell_fails():
    d = raw(); s2 = row(d, "S2")
    s2.update(source="file+cell", ref="tests/fixtures/td/measured_sheet_r1.csv#E5")    # the waist cell holds 40, not 41
    rep = run(d)
    assert not rep.ok and any("measured_sheet_r1.csv#E5 holds 40, the row says 41" in f for f in rep.failures)
    s2.update(ref="IMG_2231#waist")                                                   # a photo passed off as a file
    rep = run(d)
    assert any("file 'IMG_2231' not found" in f for f in rep.failures)


def test_wrong_value_in_a_pattern_change_fails():
    d = raw(); row(d, "F1")["baseline"]["value"] = 26.0
    rep = run(d)
    assert any("baseline" in f and "holds 26.5, the row says 26" in f for f in rep.failures)


@pytest.mark.parametrize("field,text,n", [("comment", "pocket mouth sits 2 cm too low", "2"),
                                          ("location", "lower the CF rise 3 mm", "3"),
                                          ("method", "measure 2.5 cm below the crotch", "2.5")])
def test_numeral_typed_into_free_text_fails(field, text, n):
    d = raw(); (row(d, "M1") if field == "comment" else row(d, "F1"))[field] = text
    rep = run(d)
    assert [f for f in rep.failures if f.startswith(f"numeral {n} ") and "does not trace" in f], rep.summary()


def test_number_the_renderer_typed_fails():
    td = schema.parse(raw(), FIX)
    pages = R.comment_sheet(td)
    planted = pages[0].replace("</svg>", '<text x="10" y="10">waist M: keep at 99 cm</text></svg>')
    rep = T.check(td, [planted])
    assert [f for f in rep.failures if f.startswith("numeral 99 ")]


def test_inch_chart_cell_converts_to_the_rows_unit():
    ref = "families/tee/family.yaml#pom_chart.base.poms.B.values.2@in"             # chest M = 22 3/4 in = 57.785 cm
    d = {"product": "alabasta", "round": "r1", "rev": "A", "rows": [
        {"id": "P1", "kind": "pom", "point": "Chest", "size": "M", "lens": "fit", "severity": "low",
         "value": 57.8, "unit": "cm", "source": "file+cell", "ref": ref}]}
    assert run(d).ok
    d["rows"][0]["value"] = 57.9
    assert any("holds 57.785 cm (converted from in), the row says 57.9" in f for f in run(d).failures)
    d["rows"][0].update(value=1, ref="families/tee/family.yaml#pom_chart.base.poms.B.tol")   # {proposed: 1} leaf
    assert run(d).ok


def test_unreadable_source_fails_never_skips():
    d = raw(); row(d, "F2")["ref"] = "tests/fixtures/td/round2.json#rows.99.value"
    assert any("not an item of a 6-item list" in f for f in run(d).failures)
    d = raw(); row(d, "F2")["ref"] = "projects/x/measured.xlsx#C7"
    assert not run(d).ok
    open_ = os.path.join(ROOT, "tests", "fixtures", "td", "measured_sheet_r1.csv")
    assert T.read_cell(open_, "E2") == 26.5
    with pytest.raises(ValueError, match="cannot read a .dxf"): T.read_cell(open_.replace(".csv", ".dxf"), "x")


def test_nothing_to_check_fails():
    rep = T.check(schema.parse(raw(), FIX), [])
    assert not rep.ok and "nothing to check" in rep.failures[0]


def test_annotated_page_scope_is_the_notes_band():
    from sheet import header, doc, t
    td = schema.parse(raw(), FIX)
    page = doc(header("T3", "sub", "T3") + [t(20, 150, "chest 57.8 cm from the engine's own table", 2)])
    ann = R.annotate(page, td.page_rows("T3"))
    rep = T.check(td, [ann])
    assert rep.ok, rep.summary()                                   # 57.8 is the page's own number: outside the scope
    d = raw(); row(d, "S2")["comment"] = "re-measure 5 cm lower"
    td2 = schema.parse(d, FIX)
    rep = T.check(td2, [R.annotate(page, td2.page_rows("T3"))])
    assert any(f.startswith("numeral 5 ") for f in rep.failures)


def test_family_build_fails_on_an_untraced_number(tmp_path):
    from family.build import build
    ala = os.path.join(ROOT, "families", "tee", "variants", "alabasta.yaml")
    td = {"product": "alabasta", "round": "fit sample round 1", "rev": "A", "rows": [
        {"id": "S1", "kind": "tolerance", "point": "Chest", "lens": "spec", "severity": "medium", "page": "T3",
         "value": 2, "unit": "cm", "source": "file+cell", "ref": "families/tee/family.yaml#pom_chart.base.poms.B.tol"}]}
    with pytest.raises(T.TraceError, match="holds 1, the row says 2"):
        build(ala, out_root=str(tmp_path), png=False, td=td)
    td["rows"][0]["value"] = 1
    r = build(ala, out_root=str(tmp_path), png=False, td=td)
    assert r["td_trace"].ok and r["td_trace"].pages == 2
