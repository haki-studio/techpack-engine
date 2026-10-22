"""Colour count vs the supplier's max + BOM special-trim flags (engine/supplier_gate.py; TD feasibility matrix).
A limit nobody recorded is NOT RECORDED, never a pass."""
import copy, os, tempfile
import pytest
import yaml
import factory as FAC
import supplier_gate as SG
from family.spec import Spec, SpecError

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAM = os.path.join(ROOT, "families", "tee")
EXA = os.path.join(ROOT, "tests", "fixtures", "tee_example_back_dtf_embroidery.yaml")


def one(design, prof=None): return SG.colour_check([design], prof or FAC.load())[0]


def test_rainbow_hat_10_colours_fails_at_emmies_9():
    r = one(dict(name="Rainbow hat front", method="embroidery", supplier="emmie", colours=10))
    assert r["status"] == SG.FAIL and "10 colours vs Emmie (Aungcrown, hat factory) max 9 per design — 1 over" in r["text"]
    assert "2026-03-15" in r["text"]                                    # the limit carries its source
    assert one(dict(name="x", method="embroidery", supplier="emmie", colours=9))["status"] == SG.PASS


def test_unrecorded_limits_never_pass():
    for d in (dict(name="hat", method="screen", supplier="emmie", colours=2),          # method not recorded
              dict(name="hat", method="embroidery", supplier="newco", colours=1),       # supplier not recorded
              dict(name="hat", method="embroidery", supplier=None, colours=1)):         # supplier not named
        r = one(d); assert r["status"] == SG.NOT_RECORDED and "not recorded" in r["text"], r
    prof = dict(FAC.load(), needles_confirmed=False)
    assert one(dict(name="tee", method="embroidery", supplier="mandy", colours=3), prof)["status"] == SG.NOT_RECORDED
    assert one(dict(name="tee", method="embroidery", supplier="mandy", colours=None))["status"] == SG.NOT_RECORDED


def test_mandy_embroidery_limit_is_the_confirmed_needles():
    assert one(dict(name="d", method="embroidery", supplier="mandy", colours=12))["status"] == SG.PASS
    r = one(dict(name="d", method="embroidery", supplier="mandy", colours=13))
    assert r["status"] == SG.FAIL and "max 12 per stitch file" in r["text"]
    assert one(dict(name="d", method="dtg", supplier="mandy", colours=40))["status"] == SG.NA


def test_colour_counting():
    assert SG.count_colours([{"name": "Process CMYK (desert)"}, {"name": "magenta"}]) == 5
    assert SG.count_colours([{"name": "gradient", "count": 3}, "black"]) == 4
    assert SG.count_colours([]) == 0 and SG.count_colours(None) is None


def test_special_trims_flag_missing_moq_lead_time_and_maker():
    fl = SG.trim_flags([{"item": "Custom metal zip puller, engraved"}, {"item": "Cotton tape"},
                        {"item": "Cord lock", "moq": 1000, "lead_time_days": 25, "made": "subcontracted"},
                        {"item": "Elastic", "special": True, "moq": 500}])
    assert [f["item"] for f in fl] == ["Custom metal zip puller, engraved", "Cord lock", "Elastic"]   # tape is not special
    assert fl[0]["status"] == SG.FLAG and "MOQ; lead time (days); made in-house or subcontracted" in fl[0]["text"]
    assert fl[1]["status"] == SG.PASS
    assert fl[2]["status"] == SG.FLAG and "MOQ" not in fl[2]["text"].split("—")[1]


def variant_with(**dec2):
    v = yaml.safe_load(open(EXA)); v["decorations"][1].update(dec2)
    for d in v["decorations"]:
        if isinstance(d.get("artwork"), dict) and d["artwork"].get("file"):
            d["artwork"]["file"] = os.path.join(os.path.dirname(EXA), d["artwork"]["file"])
    p = os.path.join(tempfile.mkdtemp(), "v.yaml"); yaml.safe_dump(v, open(p, "w"), allow_unicode=True)
    return p


def test_family_build_stops_on_too_many_colours(tmp_path):
    from family.build import build
    p = variant_with(colours=[{"name": f"thread {i}"} for i in range(13)])
    with pytest.raises(SpecError, match="13 colours vs Mandy's factory .* max 12 per stitch file — 1 over"):
        build(p, out_root=str(tmp_path), png=False, family_dir=FAM)
    p = variant_with(colours=[{"name": f"thread {i}"} for i in range(12)])
    r = build(p, out_root=str(tmp_path), png=False, family_dir=FAM)
    assert [x["status"] for x in r["supplier"][0]] == [SG.NA, SG.PASS]


def test_f1_asks_what_is_not_recorded():
    from family import tee_pages as TP
    sp = Spec(FAM, os.path.join(FAM, "variants", "alabasta.yaml"))
    f1 = "".join("".join(p) for c, _, p in TP.pages(sp) if c == "F1")
    assert "NOT RECORDED: D1 Alabasta desert scene (screen, 5 colours)" in f1 and "max screen colours not recorded" in f1
