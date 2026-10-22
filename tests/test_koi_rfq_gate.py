"""Koi blossom Rev D factory copy (projects/koi-blossom-hoodie/rfqgate.py on fc_shim = mirror of engine/factory_copy.py):
the leak gate is red on every planted internal string and green on clean factory text; it refuses when the internal
copy has no hits (blind); the Koi scrub rules turn the real block / engine wording into text the gate passes; and the
Rev D page table passes summary_gate. Red-then-green (skill prove-the-guard)."""
import os, sys
import cairosvg
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.join(ROOT, "projects", "koi-blossom-hoodie")
if PROJ not in sys.path: sys.path.insert(0, PROJ)
import rfqgate as G
import fc_shim as FC

CLEAN = "Blossom Tetra Hooded Jacket · Rev D · 22 Oct 2026 · art stops 10 mm above the hem band [proposed — confirm]"
PLANTED = ["confirmed by the founder 19 Oct", "FOUNDER DECISION 19 Oct", "Frame (factory.json)", "traced from inputs/front.png",
           "Rev C is built for fidelity", "the approved Drum Island jacket", "(LESSONS A11)", "AI close-up", "engine hoodie.py block",
           "Rev A koi 43,470", "read back by fidelity.py", "Claude", "the trims gate passes", "Mandy said yes"]
# wording the block / engine pages really print (T2, T3, T6b, G3, G6), as the factory copy must NOT show it
REAL = ["Main + care label = the Haki standard labels (founder 22 Oct 2026), artwork right at 1 : 1, files in the zip labels/.",
        "Size M, front and back. Body and sleeve are the approved Drum Island jacket; numbered notes are the hoodie changes.",
        "Chart in cm. Body + sleeve rows are the approved Drum Island chart, unchanged.",
        "Welt pockets, pocket bags, shoulder / armhole / side seams, facings and body lining: exactly as the Drum Island jacket.",
        "Frame 360 × 360 mm (factory.json, PROPOSED). Piece coords in mm.",
        "Clearances measured on the pattern (LESSONS A3/C8). Files: G5/G6."]


def gate(fac, internal): return FC.leak_gate(fac, internal, extra_patterns=G.EXTRA, current_rev=G.REV)


def test_clean_factory_text_passes():
    g = gate([CLEAN], PLANTED)
    assert g["ok"] and g["factory_hits"] == 0 and g["internal_hits"] > 0


@pytest.mark.parametrize("s", PLANTED)
def test_each_planted_internal_string_is_caught(s):
    assert gate([CLEAN, s], PLANTED)["factory_hits"], f"gate missed: {s!r}"


def test_blind_gate_fails():
    g = gate([CLEAN], [CLEAN])
    assert g["blind"] and not g["ok"]


@pytest.mark.parametrize("s", REAL)
def test_real_block_wording_leaks_raw_and_is_clean_after_scrub(s):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg"><text x="1" y="1">{s}</text></svg>'
    assert gate([s], PLANTED)["factory_hits"], f"raw wording should be caught: {s!r}"           # red
    out = G.scrub(svg)
    assert gate([out], PLANTED)["factory_hits"] == 0, out                                      # green after scrub


def test_check_reads_rendered_pdfs(tmp_path):
    def pdf(name, lines):
        body = "".join(f'<text x="10" y="{20 + 12 * i}" font-size="8" font-family="Liberation Sans">{l}</text>' for i, l in enumerate(lines))
        p = str(tmp_path / name)
        cairosvg.svg2pdf(bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400">{body}</svg>'.encode(), write_to=p)
        return p
    clean, leak = pdf("c.pdf", [CLEAN]), pdf("l.pdf", [CLEAN, PLANTED[0]])
    assert G.check([clean], leak)["ok"]
    assert not G.check([leak], leak)["ok"]
    assert not G.check([clean], clean)["ok"]


def test_rev_d_page_table_passes_summary_gate():
    """the TABLE in rfq.py, read without importing it (rfq.py needs the full build): every Page(...) line"""
    import ast
    src = open(os.path.join(PROJ, "rfq.py")).read()
    pages = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "Page":
            a = [ast.literal_eval(x) if not isinstance(x, ast.Name) else {"FACTORY": FC.FACTORY, "INT": FC.INTERNAL}[x.id] for x in node.args]
            pages.append(FC.Page(*a))
    assert len(pages) >= 20
    assert FC.summary_gate(pages) == []
    bad = [FC.Page(p.id, p.kind, p.title, FC.FACTORY) if p.id == "TBD" else p for p in pages]
    assert any("internal-only" in x for x in FC.summary_gate(bad))                             # red: a decisions page tagged factory
