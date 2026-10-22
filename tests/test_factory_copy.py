"""engine/factory_copy.py — leak gate red-then-green, summary page-kind gate, SVG scrub (LESSONS E15)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import factory_copy as FC
from factory_copy import Page, FACTORY, INTERNAL

CLEAN = ["Konpeito Jeans — Rev B8 · 22 Oct 2026 · waist sizes 26-40",
         "Sew-out on the production twill before bulk. Embroider the cut pocket before hemming; tearaway backing."]


def test_leak_gate_red_on_planted_internal_string():
    planted = [CLEAN[0], CLEAN[1] + " Edge red (confirmed by the founder 19 Oct)."]
    g = FC.leak_gate(planted, planted)
    assert not g["ok"] and g["factory_hits"] >= 2          # "founder" + the decision date
    pats = {h[1] for h in g["factory"]}
    assert r"[Ff]ounder" in pats


def test_leak_gate_green_on_clean_text():
    internal = CLEAN + ["E · FIDELITY (LESSONS A14) — motif_match per family, min IoU 0.74 PASS"]
    g = FC.leak_gate(CLEAN, internal, current_rev="Rev B8")
    assert g["ok"] and g["factory_hits"] == 0 and g["internal_hits"] > 0


def test_leak_gate_blind_when_internal_copy_has_no_hits():
    # red-then-green built in: a gate that finds nothing in the internal copy proves nothing about the factory copy
    g = FC.leak_gate(CLEAN, CLEAN)
    assert g["blind"] and not g["ok"]


def test_leak_gate_rev_history_and_extra_patterns():
    g = FC.leak_gate(["included from Rev B6", "Rev B8 cover"], ["x founder"], current_rev="Rev B8")
    assert g["factory_hits"] == 1 and "B6" in g["factory"][0][2]
    g = FC.leak_gate(["ask Mandy"], ["Mandy"], extra_patterns=[r"Mandy"], patterns=[])
    assert g["factory_hits"] == 1 and g["internal_hits"] == 1


def test_full_build_date_is_not_a_decision_date():
    assert not FC.scan("Rev B8 · 22 Oct 2026", FC.BASE_PATTERNS)
    assert FC.scan("kept (founder 21 Oct)", FC.BASE_PATTERNS)


def _pages():
    order = ["cover", "flats", "measurements", "bom", "construction", "labels_packing",
             "artwork_placement", "artwork_summary", "artwork_element", "factory_questions"]
    pages = [Page(f"P{i}", k, k, FACTORY) for i, k in enumerate(order)]
    return pages + [Page("C1", "compare", "compare", INTERNAL), Page("Q1", "decisions", "log", INTERNAL)]


def test_summary_gate_green_on_complete_set():
    assert FC.summary_gate(_pages()) == []
    assert [p.kind for p in FC.factory_pages(_pages())][0] == "cover"


def test_summary_gate_red_on_missing_kind_internal_kind_and_order():
    pages = [p for p in _pages() if p.kind != "measurements"]
    assert any("measurements" in s for s in FC.summary_gate(pages))
    pages = _pages(); pages[-2] = Page("C1", "compare", "compare", FACTORY)
    assert any("internal-only" in s for s in FC.summary_gate(pages))
    pages = _pages(); pages[0], pages[1] = pages[1], pages[0]
    assert any("out of order" in s for s in FC.summary_gate(pages))
    pages = [p for p in _pages() if not p.kind.startswith("artwork")]
    assert FC.summary_gate(pages, decorated=False) == [] and FC.summary_gate(pages)


def test_scrub_svg_rewrites_and_drops():
    svg = ('<svg><text x="1" y="2">Position CONFIRMED (founder 20 Oct).</text>'
           '<text x="1" y="5">Generated, not traced: one stroke width</text>'
           '<text x="1" y="8">main label = the Haki standard labels (founder 22 Oct); 1 : 1 file</text></svg>')
    out = FC.scrub_svg(svg, FC.BASE_SCRUB)
    assert "Position CONFIRMED." in out and "Generated" not in out
    assert "labels; 1 : 1 file" in out and "founder" not in out
    assert not FC.scan(out, FC.BASE_PATTERNS)
