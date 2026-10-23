"""Konpeito factory wording: the B8 G7 provenance line (PR #58) fails the leak gate raw and passes once scrubbed."""
import os, sys
ROOT = os.path.join(os.path.dirname(__file__), "..")
for p in (os.path.join(ROOT, "engine"), os.path.join(ROOT, "projects", "konpeito-jeans")):
    if p not in sys.path: sys.path.insert(0, p)
import factory_copy as FC
from kjfactory_words import EXTRA, KJ_SCRUB

B8_G7 = ("Rev B8 (founder 22 Oct): limbs, eye size and gaze from a hand-read art table of the low-res mockup "
         "(~1 mm per px)  [proposed — confirm on the sew-out].")
INTERNAL = ["Founder 21 Oct (J5): the soot sprites are kept"]


def test_b8_g7_line_red_raw_green_scrubbed():
    raw = FC.leak_gate([B8_G7], INTERNAL, EXTRA, current_rev="Rev B8")
    assert not raw["ok"] and raw["factory_hits"] >= 1
    out = FC.scrub_text(B8_G7, FC.BASE_SCRUB + KJ_SCRUB)
    assert out == "Limbs, eye size and gaze as drawn on this page and in the stitch file [proposed — confirm on the sew-out]."
    g = FC.leak_gate([out], INTERNAL, EXTRA, current_rev="Rev B8")
    assert g["ok"], g["factory"]
