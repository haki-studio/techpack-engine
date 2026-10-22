"""Haki standard labels (engine/labels.py, LESSONS D7): the care label follows the fibre, anything else is FLAGGED."""
import os, sys
import pytest
from pypdf import PdfReader
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import labels as LB

MM = 72 / 25.4


@pytest.mark.parametrize("text,key", [
    ("RHT 3x1 denim 12 oz, 100 % cotton", "100-cotton"),
    ("100% Cotton", "100-cotton"),
    ("fleece 90% cotton, 10% polyester", "90-cotton-10-polyester"),
    ("90 % COTTON / 10 % POLYESTER", "90-cotton-10-polyester"),
])
def test_care_label_follows_the_fibre(text, key):
    assert LB.care_key(text) == key
    p = LB.care_label(text)
    assert os.path.basename(p) == f"haki-studios-care-label-{key}-white.pdf" and os.path.exists(p)


@pytest.mark.parametrize("text", [
    "80% cotton, 20% polyester", "95% cotton, 5% elastane", "100% polyester",
    "98% cotton, 2% elastane", "cotton twill", "", "90% cotton, 10% polyester, 5% elastane",
])
def test_any_other_fibre_is_flagged_never_guessed(text):
    assert LB.care_key(text) is None and LB.care_label(text) is None


def test_files_exist_at_the_stated_size():
    mb = PdfReader(LB.MAIN).pages[0].mediabox
    assert (round(float(mb.width) / MM), round(float(mb.height) / MM)) == LB.MAIN_MM
    for key in ("100-cotton", "90-cotton-10-polyester"):
        for f in LB.files_for("100% cotton" if key == "100-cotton" else "90% cotton 10% polyester"):
            assert os.path.exists(f), f
        r = PdfReader(os.path.join(LB.ROOT, f"haki-studios-care-label-{key}-white.pdf"))
        assert len(r.pages) == 2                    # front + back
        mb = r.pages[0].mediabox
        assert (round(float(mb.width) / MM), round(float(mb.height) / MM)) == LB.CARE_MM
