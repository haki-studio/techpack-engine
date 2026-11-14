"""Koi blossom hooded jacket care label (lead ruling 2026-11-04, LESSONS D7): the shell "washed navy 12 oz duck" is cotton
duck, so the pack's care row resolves to the Haki standard 100 % cotton care label, shown AMBER as
"[proposed — confirm fibre: 100 % cotton]" (fibre_confirmed=False), exactly like the six jackets. Not MISSING, not green.
The factory copy (rfq.py) keeps asking for the fibre % but no longer says the care label is held / MISSING.
Red on origin/main (SHELL_MAT had no fibre % -> MISSING), green on koi-care-proposed. Skill prove-the-guard."""
import ast, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KOI = os.path.join(ROOT, "projects", "koi-blossom-hoodie")
sys.path.insert(0, os.path.join(ROOT, "engine"))
import labelsheet as LS


def koi_shell():
    """the value garment.py assigns to ZB.SHELL_MAT (read from source: importing garment.py builds the whole pack)."""
    tree = ast.parse(open(os.path.join(KOI, "garment.py")).read())
    hits = [n.value.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
            and any(isinstance(tg, ast.Attribute) and tg.attr == "SHELL_MAT" for tg in n.targets)]
    assert len(hits) == 1, hits
    return hits[0]


def header(title, sub, page): return [f"<!-- {page} {title} -->"]


def test_koi_care_row_is_proposed_100_cotton():
    shell = koi_shell()
    assert LS.care_fibre(shell) == "100 % cotton"
    bom = LS.care_bom(shell, "T6b")                  # the BOM row the block's T6/T8 table prints for the Koi pack
    assert LS.MISSING not in bom and "100 % cotton" in bom and LS.unconfirmed("100 % cotton") in bom


def test_koi_labels_page_is_amber_not_missing_not_green(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    shell = koi_shell()
    svg = "".join(LS.hoodie_page(header, shell))     # exactly what ZB.p_labels() renders for T6b (fibre_confirmed default False)
    assert LS.MISSING not in svg and "[MISSING]" not in svg
    assert "CARE LABEL — Haki standard, 100 % cotton [proposed — confirm fibre: 100 % cotton]" in svg
    head = next(s for s in svg.split("<text")[1:] if "CARE LABEL — Haki standard" in s)
    assert LS.AMBER in head and LS.GREEN not in head
    assert svg.count("<image") == 3                  # main + care front + care back art at 1:1
    assert sorted(os.path.basename(p) for p in LS.files(shell)) != ["main-label-6.5x2cm-white.pdf"]


def test_koi_factory_copy_no_longer_holds_the_care_label():
    src = open(os.path.join(KOI, "rfq.py")).read()
    for stale in ["care label is held", "held until the fibre content is confirmed", "The care label waits",
                  "labelsheet MISSING state", "Never a guessed %", "care label follows once the fibre content is confirmed"]:
        assert stale not in src, stale
    assert "Fibre % — shell" in src                   # the RFQ still asks the factory for the fibre (Q1)
    assert "proposed 100 % cotton" in src
