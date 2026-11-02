"""KCOS is the Rev M pullover (product lead 29 Oct 2026, card standard-labels-fibre-pct): French Terry 350 GSM 100 %
cotton self, rib 95/5. Its standard care label must be the 100 % cotton art, picked from the Rev M BOM (pv_bom.SELF),
never the Rev J zip-jacket shell '12 oz cotton duck canvas' (no fibre % -> MISSING). Finding ed8f0135."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.join(ROOT, "projects", "keep-clean-our-space-hoodie")
if PROJ not in sys.path: sys.path.insert(0, PROJ)
import pv_bom as BOM
import labelsheet as LS

CARE_100 = ["haki-studios-care-label-100-cotton-white.pdf", "haki-studios-care-label-100-cotton.ai",
            "haki-studios-care-label-100-cotton.pdf", "main-label-6.5x2cm-white.pdf"]


def test_care_label_follows_the_rev_m_self_fabric():
    assert "French Terry" in BOM.CARE_SHELL and "350 GSM" in BOM.CARE_SHELL and "duck" not in BOM.CARE_SHELL.lower()
    assert LS.care_fibre(BOM.CARE_SHELL) == "100 % cotton"


def test_k1_fabric_lines_and_label_source_are_one_string():
    """the care label is picked from the same line K1 prints as Self (no second copy that can drift)."""
    assert dict(BOM.FABRIC_ROWS)["Self"] is BOM.CARE_SHELL
    assert "95% Cotton 5% Elastane" in dict(BOM.FABRIC_ROWS)["Rib (cuffs + body hem)"]


def test_rev_m_bom_rows_say_100_cotton_confirmed():
    rows = dict(BOM.label_rows())
    assert list(rows) == ["Labels"] and "main label" in rows["Labels"]
    assert "100 % cotton" in rows["Labels"]
    assert LS.MISSING not in rows["Labels"] and "confirm fibre" not in rows["Labels"]


def test_rev_m_zip_carries_the_100_cotton_care_art(tmp_path):
    assert BOM.export_labels(str(tmp_path / "labels")) == CARE_100
