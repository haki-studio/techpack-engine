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


B9_G7 = ("Rev B9 (founder 23 Oct): each arm leaves the side of the body facing the candy it holds (about eye height), "
         "runs out, then goes UP to the underside of the candy.")


def test_b9_g7_arm_line_reads_as_an_instruction():
    """B9: without the rule the factory copy kept a bare 'Rev B9 :' prefix (the base scrub drops the founder date)."""
    base = FC.scrub_text(B9_G7, FC.BASE_SCRUB)
    assert base.startswith("Rev B9")                                           # red: the stub without the KJ rule
    out = FC.scrub_text(B9_G7, FC.BASE_SCRUB + KJ_SCRUB)
    assert out.startswith("Arms: each arm leaves the side of the body") and "Rev B" not in out and "founder" not in out
    assert FC.leak_gate([out], INTERNAL, EXTRA, current_rev="Rev B9")["ok"]
