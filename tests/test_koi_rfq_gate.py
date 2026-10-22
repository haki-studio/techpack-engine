"""Koi blossom factory copy (Rev D, Rev E, Rev F) (projects/koi-blossom-hoodie/rfqgate.py on fc_shim = mirror of engine/factory_copy.py):
the leak gate is red on every planted internal string and green on clean factory text; it refuses when the internal
copy has no hits (blind); the Koi scrub rules turn the real block / engine wording into text the gate passes; and the
page table passes summary_gate; a file name of ours ("ref.png") is caught only because of the Rev E path pattern in rfqgate.EXTRA;
the Rev F method gate is red on every Rev E page that told the factory to embroider the CUT panel and green on the Rev F wording.
Red-then-green (skill prove-the-guard)."""
import os, sys
import cairosvg
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.join(ROOT, "projects", "koi-blossom-hoodie")
if PROJ not in sys.path: sys.path.insert(0, PROJ)
import rfqgate as G
import fc_shim as FC

CLEAN = "Blossom Tetra Hooded Jacket · Rev F · 22 Oct 2026 · art stops 10 mm above the hem band [proposed — confirm]"
PLANTED = ["confirmed by the founder 19 Oct", "FOUNDER DECISION 19 Oct", "Frame (factory.json)", "traced from inputs/front.png",
           "Rev C is built for fidelity", "the approved Drum Island jacket", "(LESSONS A11)", "AI close-up", "engine hoodie.py block",
           "Rev A koi 43,470", "read back by fidelity.py", "Claude", "the trims gate passes", "Mandy said yes",
           "see ref.png", "art from closeup.jpg"]
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


PATH_RX = r"\.(png|jpe?g|py|json|pkl)\b"


@pytest.mark.parametrize("s", ["see ref.png", "art from closeup.jpg", "the ref.jpeg crop"])
def test_file_names_caught_only_by_the_path_pattern(s):
    """review SHOULD 2 (Rev D): the shim's base patterns miss a bare file name; rfqgate.EXTRA's path pattern catches it"""
    assert PATH_RX in G.EXTRA
    without = [x for x in G.EXTRA if x != PATH_RX]
    assert FC.leak_gate([CLEAN, s], PLANTED, extra_patterns=without, current_rev=G.REV)["factory_hits"] == 0, "red: base list alone should miss it"
    assert gate([CLEAN, s], PLANTED)["factory_hits"], f"green: path pattern should catch {s!r}"


def test_page_table_passes_summary_gate():
    """the TABLE in rfq.py, read without importing it (rfq.py needs the full build): every Page(...) line"""
    import ast
    src = open(os.path.join(PROJ, "rfq.py")).read()
    pages = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "Page":
            a = [ast.literal_eval(x) if not isinstance(x, ast.Name) else {"FACTORY": FC.FACTORY, "INT": FC.INTERNAL}[x.id] for x in node.args]
            pages.append(FC.Page(*a))
    assert len(pages) >= 24
    assert FC.summary_gate(pages) == []
    bad = [FC.Page(p.id, p.kind, p.title, FC.FACTORY) if p.id == "TBD" else p for p in pages]
    assert any("internal-only" in x for x in FC.summary_gate(bad))                             # red: a decisions page tagged factory


# ---------------------------------------------------------------- Rev F: one embroidery method (td-chair C-01)
E0_METHOD = ["Embroider an oversized block of shell, not the cut panel: the piece's cut outline + 30 mm all round, chalked with CF, the welt box and the keep-out lines from the 1:1 plot.",
             "After embroidery, lay the 1:1 pattern piece on the sewn block, align CF + the welt box, and re-cut. A cut front is narrower than the frame and the art sits "
             "15 mm from CF, so a cut panel has nothing to clamp; the wearer's right front also pulls up more than the left."]
# exactly what the shipped Rev E factory PDFs said (summary CI; techpack CI, T7, G5, G6, element specs 01 + 02)
REV_E_CUT = ["1 Embroider the cut front + sleeve panels first (E0). Fuse the facings K01 / K02 and the welts P01.",
             "Embroider the cut panels flat before assembly (fronts before zip + welts, sleeves before the underarm seam + cuff band).",
             "1. Mark CF / sleeve centre + split line on the\n    cut panel (chalk) from the pattern.",
             "Needle start = centre of each file's design (origin of the DST/PES). Mark it on the cut panel from the pattern (DXF layer 13 + layer 8 cross).",
             "Direct embroidery on both cut front panels (F02 wearer's right, F01 wearer's left) · mm, finished size · art files 1:1",
             "Direct embroidery on the front half of both cut sleeves (S01 wearer's right, S02 wearer's left) · mm, finished size · art files 1:1",
             "PRODUCTION Embroider the cut panels flat, BEFORE zip, welts, side seams, sleeve seams and hem band / cuffs."]
REV_F = ["1 Embroider the fronts + sleeves first, each as an oversized block of shell, then re-cut on the 1:1 pattern piece (E0; or your method, QF2 m).",
         "Embroider each front + sleeve as an oversized block of shell (cut outline + 30 mm), then re-cut on the 1:1 pattern piece (E0); fronts before zip + welts.",
         "1. Chalk CF / sleeve centre + split line on the\n    oversized block (E0) from the 1:1 plot.",
         "Chalk it on the oversized block (E0) from the 1:1 plot (DXF layer 13 + layer 8 cross).",
         "Embroidery on both fronts, sewn as oversized blocks + re-cut (F02 wearer's right, F01 wearer's left) · mm, finished size",
         "Embroidery on the front half of both sleeves, sewn as oversized blocks + re-cut (S01 wearer's right, S02 wearer's left)",
         "PRODUCTION Embroider an oversized block of shell, then re-cut (E0); BEFORE zip, welts, seams, hem band + cuffs.",
         "Before cutting, send us your pattern print or a measured sheet of the cut pieces (size M)."]


@pytest.mark.parametrize("s", REV_E_CUT)
def test_method_gate_red_on_each_rev_e_cut_panel_page(s):
    assert G.method_hits(E0_METHOD + [s]), f"method gate missed: {s!r}"                       # red


def test_method_gate_green_on_rev_f_wording():
    assert G.method_hits(E0_METHOD + REV_F) == []                                            # green (E0's own contrast sentences pass)


def test_method_gate_silent_without_the_oversized_block_method():
    """a pack whose method IS the cut panel (no 'oversized block' anywhere) has nothing to contradict"""
    assert G.method_hits(REV_E_CUT) == []
    assert G.method_hits(["Embroider an oversized block (E0)."] + REV_E_CUT)                   # one mention of the method arms it


def test_method_gate_reads_rendered_pdfs(tmp_path):
    def pdf(name, lines):
        body = "".join(f'<text x="10" y="{20 + 12 * i}" font-size="6" font-family="Liberation Sans">{l}</text>' for i, l in enumerate(lines))
        p = str(tmp_path / name)
        cairosvg.svg2pdf(bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="400">{body}</svg>'.encode(), write_to=p)
        return p
    summ = pdf("s.pdf", E0_METHOD[:1]); bad, good = pdf("b.pdf", [REV_E_CUT[0]]), pdf("g.pdf", [REV_F[0]])
    assert G.method_gate([summ, bad])[bad]                                                    # red: the method on one PDF, the cut panel on the other
    assert not any(G.method_gate([summ, good]).values())                                      # green
