"""Lessons from the first live TD run (Godspeed track pants, 2026-10-22; LESSONS T1-T3): rise POMs say whether the
waistband is included (one method per table); a HOLD list prints numbers only from the signed master POM; an
elastic-waist family must carry waist relaxed AND stretched."""
import copy, json, os, tempfile
import pytest
import yaml
import pom_rules
from td import schema, render as R
from td.schema import TDInputError
from family.spec import Spec, SpecError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(ROOT, "tests", "fixtures", "td", "round2.json")
FAM = os.path.join(ROOT, "families", "tee")
ALA = os.path.join(FAM, "variants", "alabasta.yaml")


def raw(): return json.load(open(FIX))
def row(d, rid): return next(r for r in d["rows"] if r["id"] == rid)


# ----------------------------------------------------------------------------- T1 rise + incl_waistband
def test_red_case_front_rise_with_waistband_next_to_unlabelled_back_rise():
    d = raw(); row(d, "F1")["incl_waistband"] = True; row(d, "F2").pop("incl_waistband")
    with pytest.raises(TDInputError, match="rise POM 'F2 back rise M' must say incl_waistband: true or false"):
        schema.parse(d)


def test_mixed_rise_methods_in_one_table_fail():
    d = raw(); row(d, "F1")["incl_waistband"] = True
    with pytest.raises(TDInputError, match="mixed rise methods — with waistband: F1 front rise M; without: F2 back rise M"):
        schema.parse(d)
    assert schema.parse(raw())                              # both false: one method, passes


def test_non_rise_rows_need_no_label():
    assert pom_rules.rise_check([("thigh M", None), ("waist", None), ("riser tape", None)]) == []
    assert pom_rules.rise_check([("Front Rise", "yes")])[0].endswith("(got 'yes')")


def fam_with(**poms_extra):
    f = yaml.safe_load(open(os.path.join(FAM, "family.yaml")))
    for k, v in poms_extra.items(): f["pom_chart"]["base"]["poms"][k] = v
    return f


def spec_from(f):
    d = tempfile.mkdtemp(); yaml.safe_dump(f, open(os.path.join(d, "family.yaml"), "w"), allow_unicode=True)
    return Spec(d, ALA)


def rise(name, **kw): return dict(name=name, how="seam to waist", half=False, values=["10"] * 6, **kw)


def test_family_chart_rise_rules():
    with pytest.raises(SpecError, match="rise POM 'R1 Front rise' must say incl_waistband"):
        spec_from(fam_with(R1=rise("Front rise")))
    with pytest.raises(SpecError, match="mixed rise methods"):
        spec_from(fam_with(R1=rise("Front rise", incl_waistband=True), R2=rise("Back rise", incl_waistband=False)))
    sp = spec_from(fam_with(R1=rise("Front rise", incl_waistband=True), R2=rise("Back rise", incl_waistband=True)))
    assert "R1" in sp.chart.poms
    Spec(FAM, ALA)                                          # the real tee chart has no rise: unchanged


# ----------------------------------------------------------------------------- T2 HOLD numbers only from the signed master
def hold_lines(d): return [s for _, s in R.sheet_lines(schema.parse(d))]


def test_hold_numbers_come_only_from_the_signed_master():
    assert "back rise M: keep at 36.5 cm" in hold_lines(raw())          # pom_signed.csv is the signed master
    d = raw(); row(d, "F2")["ref"] = "tests/fixtures/td/measured_sheet_r1.csv#E3"        # a measured sheet, not signed
    L = hold_lines(d)
    assert "back rise M: change nothing, wait for the next sheet" in L and not any("36.5" in s for s in L)
    d = raw(); d.pop("signed_master")                                     # nothing signed yet
    L = hold_lines(d)
    assert "thigh M: change nothing, wait for the next sheet" in L and "back rise M: change nothing, wait for the next sheet" in L
    d = raw(); row(d, "F3").update(source="photo_estimate", ref="IMG_1")
    assert "thigh M: change nothing, wait for the next sheet" in hold_lines(d)


# ----------------------------------------------------------------------------- T3 elastic waist needs relaxed + stretched
def test_elastic_waist_family_needs_relaxed_and_stretched_waist():
    assert pom_rules.required_missing(["A", "Waist relaxed"], {"waist": "elastic"}) == ["waist_stretched"]
    f = fam_with(); f["waist"] = "elastic"
    with pytest.raises(SpecError, match="missing required POM\\(s\\) waist_relaxed, waist_stretched"):
        spec_from(f)
    f = fam_with(W1=dict(name="Waist relaxed", how="1/2 relaxed", half=True, values=["15"] * 6),
                 W2=dict(name="Waist stretched", how="1/2 fully stretched", half=True, values=["20"] * 6))
    f["waist"] = "elastic"
    assert spec_from(f).chart.poms["W2"].name == "Waist stretched"
    f = fam_with(); f["pom_required"] = ["inseam"]
    with pytest.raises(SpecError, match="missing required POM\\(s\\) inseam"):
        spec_from(f)


def test_pack_page_note_hides_an_unsigned_hold_number():
    from td import render as R
    from sheet import header, doc, t
    page = doc(header("T3", "sub", "T3") + [t(20, 150, "x", 2)])
    d = raw(); row(d, "F3").update(source="photo_estimate", ref="IMG_1", page="T3")     # reviewer's case
    td = schema.parse(d)
    out = R.annotate(page, td.page_rows("T3"), td)
    assert "thigh M — HOLD: change nothing, wait for the next sheet" in out and "33" not in out
    d = raw(); row(d, "F3")["page"] = "T3"; td = schema.parse(d)                         # signed master: number shown
    out = R.annotate(page, td.page_rows("T3"), td)
    assert "thigh M = 33 cm" in out and "HOLD (do not change)" in out


def test_rise_rule_covers_other_rise_names():
    for n in ("crotch depth", "Front crotch", "CF seam length", "CB length", "back rise"):
        assert pom_rules.rise_check([(n, None)]), n
    assert pom_rules.rise_check([("crotch point", None), ("cuff length", None)]) == []
