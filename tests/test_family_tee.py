"""Tee family: one block + data-only variants (docs/FAMILIES.md). Every number on a page comes from family.yaml / the
variant; unknowns print amber "[proposed — confirm]" and are listed on F1; a bad variant fails with a clear message."""
import copy, os, re, tempfile
import pytest
import yaml
from family.spec import Spec, SpecError, V, TAG
from family import tee_pages as TP
from family.build import build
from family.draw import PROP

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAM = os.path.join(ROOT, "families", "tee")
ALA = os.path.join(FAM, "variants", "alabasta.yaml")
SHD = os.path.join(FAM, "variants", "from-the-shadows.yaml")
EXA = os.path.join(ROOT, "tests", "fixtures", "tee_example_back_dtf_embroidery.yaml")


def spec(var=ALA, **over):
    """Spec with top-level family.yaml keys REPLACED (written to a temp family folder, as an operator would edit it)"""
    if not over: return Spec(FAM, var)
    fam = yaml.safe_load(open(os.path.join(FAM, "family.yaml"))); fam.update(over)
    d = tempfile.mkdtemp(); yaml.safe_dump(fam, open(os.path.join(d, "family.yaml"), "w"), allow_unicode=True)
    return Spec(d, var)


def svgs(sp): return {code: "".join(pages) for code, _, pages in TP.pages(sp)}


def base_poms():
    return yaml.safe_load(open(os.path.join(FAM, "family.yaml")))["pom_chart"]


# ----------------------------------------------------------------------------- C2 half measures
def test_half_measures_are_converted_explicitly():
    sp = spec(); fl = sp.flat("M"); ch = sp.chart
    assert ch["B"].show("M") == "22 3/4" and float(ch["B"].raw("M")) == 22.75
    assert fl.chest_flat == pytest.approx(22.75 * 25.4)            # half (flat) chest = full width of the flat
    assert fl.chest2 == pytest.approx(22.75 * 25.4 / 2)            # CF -> side seam = half of that, never doubled
    assert fl.bottom2 == pytest.approx(ch.mm("D", "M") / 2)
    # the drawn bicep (perpendicular from underarm to the sleeve top line) equals the half bicep on the chart
    import numpy as np
    r = np.array(fl.ua) - np.array(fl.sp); d = fl.u[0] * r[1] - fl.u[1] * r[0]
    assert abs(d) == pytest.approx(ch.mm("G", "M"), abs=0.5)


def test_block_refuses_a_full_chest_marked_as_not_half():
    pc = base_poms(); pc["base"]["poms"]["B"]["half"] = False
    with pytest.raises(SpecError, match="HALF"):
        spec(pom_chart=pc).flat("M")


def test_every_pom_must_declare_half():
    pc = base_poms(); del pc["base"]["poms"]["A"]["half"]
    with pytest.raises(SpecError, match="half"):
        spec(pom_chart=pc)


# ----------------------------------------------------------------------------- base + deltas
def test_recorded_delta_size_is_confirmed_and_other_sizes_are_derived_amber():
    ch = spec().chart
    assert ch["A"].show("L") == "27" and not ch.cell_proposed("A", "L")       # recorded at L (2026-02-27)
    assert ch["A"].show("M") == "26" and ch.cell_proposed("A", "M")           # base 26 1/2 - 1/2, derived
    assert ch["F"].show("L") == "10 1/4" and ch["H"].show("L") == "7 5/8"
    assert all(ch.cell_proposed("C", s) for s in ch.sizes)                     # drop shoulder width never recorded
    assert ch["P"].show("L") == "4" and ch["P"].show("M") == "3 5/8"           # new POM graded like E (3/8)
    assert not any(ch.cell_proposed("B", s) for s in ch.sizes)                 # untouched base rows stay confirmed


def test_replacing_the_chart_in_one_place_drops_every_derived_flag():
    pc = base_poms(); pc.pop("deltas"); pc.pop("status")
    ch = spec(pom_chart=pc).chart
    assert not any(c.proposed for p in ch.poms.values() for c in p.cells.values())
    assert ch["A"].show("L") == "27 1/2" and "P" not in ch.poms


# ----------------------------------------------------------------------------- numbers come from family.yaml
def test_changing_one_pom_changes_table_sketch_and_placement():
    a = spec(); sa = svgs(a)
    pc = base_poms()
    pc["base"]["poms"]["K"]["values"] = ["5 1/8", "5 1/4", "5 3/8", "5 1/2", "5 5/8", "5 3/4"]   # front neck drop +1 in
    pc["base"]["poms"]["B"]["values"] = ["21 3/4", "22 3/4", "23 3/4", "24 3/4", "25 3/4", "26 3/4"]
    b = spec(pom_chart=pc); sb = svgs(b)
    assert "5 3/8" in sb["T3"] and "5 3/8" not in sa["T3"]                    # POM table
    assert b.flat("M").fnd == pytest.approx(a.flat("M").fnd + 25.4)            # sketch geometry
    assert sa["T2"] != sb["T2"]
    # Alabasta's art is set from the CF neck seam: its HPS distance moves by exactly the FND change
    assert b.decorations[0].box_mm("M")[1] == pytest.approx(a.decorations[0].box_mm("M")[1] + 25.4)
    assert "18.3" in sa["D1"] and "20.8" in sb["D1"]                          # Top below HPS, size M, on the page
    ca = a.flat("M").clearances(a.decorations[0].box_mm("M")); cb = b.flat("M").clearances(b.decorations[0].box_mm("M"))
    assert cb["side seam"] > ca["side seam"] + 5                             # wider chest -> side seam further from the art


def test_placement_keepout_failure_is_shown_red():
    var = yaml.safe_load(open(ALA)); var["decorations"][0]["width_cm"] = 52
    p = os.path.join(tempfile.mkdtemp(), "wide.yaml"); yaml.safe_dump(var, open(p, "w"))
    sv = svgs(Spec(FAM, p))["D1"]
    assert "PLACEMENT FAILS A KEEP-OUT" in sv and "ALL SIZES CLEAR" not in sv


# ----------------------------------------------------------------------------- proposed values
TEXT = re.compile(r'<text [^>]*fill="([^"]+)"[^>]*>([^<]*)</text>')


@pytest.mark.parametrize("var", [ALA, SHD, EXA])
def test_every_proposed_tag_is_amber_and_every_proposed_value_is_on_f1(var):
    sp = spec(var); allsvg = svgs(sp)
    tagged = [(fill, s) for code, sv in allsvg.items() for fill, s in TEXT.findall(sv) if "[proposed" in s]
    assert tagged and all(fill == PROP for fill, _ in tagged)
    f1 = allsvg["F1"]; items = TP.open_items(sp)
    assert len(items) >= 30
    flat_f1 = re.sub(r"\s+", " ", " ".join(s for _, s in TEXT.findall(f1)))
    for grp, label, v in items:
        assert TP.wrap(label, 92, 1.55)[0] in flat_f1, label
        assert TP.wrap(v.text(tag=False), 150, 1.55)[0].replace("&", "+").replace("<", "‹").replace(">", "›") in flat_f1, label
    assert "full graded measurement chart" in flat_f1                       # the top factory question


def test_a_new_proposed_value_reaches_f1_and_a_confirmed_one_leaves_it():
    before = {lab for _, lab, _ in TP.open_items(spec())}
    assert "knit" in before
    blank = yaml.safe_load(open(os.path.join(FAM, "family.yaml")))["blank"]
    sp = spec(blank=dict(blank, knit="single jersey 20s/1 (Mandy, test)"))
    after = {lab for _, lab, _ in TP.open_items(sp)}
    assert "knit" not in after
    sp2 = spec(blank=dict(blank, care={"proposed": "hang dry, iron inside out"}))
    assert "care" in {lab for _, lab, _ in TP.open_items(sp2)}


# ----------------------------------------------------------------------------- variant validation
def _var(**kw):
    var = yaml.safe_load(open(ALA)); var["decorations"][0].update(kw)
    p = os.path.join(tempfile.mkdtemp(), "v.yaml"); yaml.safe_dump(var, open(p, "w")); return p


def test_unknown_method_fails_with_a_clear_error():
    with pytest.raises(SpecError, match=r"unknown method 'foil'.*Known methods: screen, dtg, dtf, puff_print, embroidery"):
        Spec(FAM, _var(method="foil"))


def test_unknown_spec_field_and_missing_placement_fail_clearly():
    with pytest.raises(SpecError, match="not defined for method 'screen'"):
        Spec(FAM, _var(spec={"pressure": "high"}))
    var = yaml.safe_load(open(ALA)); del var["decorations"][0]["width_cm"]
    p = os.path.join(tempfile.mkdtemp(), "v.yaml"); yaml.safe_dump(var, open(p, "w"))
    with pytest.raises(SpecError, match="missing 'width_cm:'"):
        Spec(FAM, p)


# ----------------------------------------------------------------------------- builds
@pytest.mark.parametrize("var", [ALA, SHD, EXA])
def test_variant_builds_a_full_pack(var):
    out = tempfile.mkdtemp()
    r = build(var, out_root=out, png=False, family_dir=FAM)
    codes = [c for c, _, _ in r["pages"]]
    assert codes[:6] == ["T1", "T2", "T3", "T4", "T5", "T6"] and "R1" in codes and any(c.startswith("F1") for c in codes)
    assert sum(c.startswith("D") for c in codes) == len(r["spec"].decorations)
    from pypdf import PdfReader
    assert len(PdfReader(r["pdf"]).pages) == len(codes)


def test_no_prices_or_our_numbers_on_factory_pages():
    for var in (ALA, SHD, EXA):
        text = " ".join(s for sv in svgs(spec(var)).values() for _, s in TEXT.findall(sv)).lower()
        for bad in ("$", "usd", "rmb", "¥", "price", "cost", "margin", "po-26", "moq"):
            assert bad not in text, (var, bad)


def test_template_example_uses_back_view_and_embroidery_stub():
    sp = spec(EXA); d1, d2 = sp.decorations
    assert d1.view == "back" and d1.method == "dtf" and d2.stub
    assert d1.box_mm("M")[2] - d1.box_mm("M")[0] == pytest.approx(280) and d1.box_mm("XL")[2] - d1.box_mm("XL")[0] == pytest.approx(300)
    sv = svgs(sp)
    assert "stitch files are made by the techpack-engine stitch path" in sv["D2"]
    assert "max 12 colours per file" in sv["D2"]                              # read from factory.json
