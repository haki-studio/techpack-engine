"""Haki standard labels on a pack page (engine/labelsheet.py, LESSONS D7): a shell with no fibre % prints MISSING and
never a care label; a 100 % cotton shell shows the 100-cotton care label front + back."""
import os, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import labelsheet as LS

# shells as recorded on 22 Oct 2026: KCOS, Koi, Pixel Sky have no fibre % -> MISSING
UNKNOWN = ["12 oz cotton duck canvas, washed black (pre-washed before embroidery)", "washed navy 12 oz duck",
           "12 oz cotton duck canvas, washed (colour per design)", "jacquard sherpa, fibre content: mill to state"]
JACKET = "12 oz (407 g/m²) 100% cotton duck canvas, 150 cm, washed"


@pytest.mark.parametrize("shell", UNKNOWN)
def test_no_fibre_percent_prints_missing_and_no_care_art(shell, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert LS.care_fibre(shell) is None
    assert LS.MISSING in LS.care_bom(shell) and LS.MISSING in LS.care_desc(shell)
    svg = "".join(LS.panel(0, 0, 86, shell, "main here", "care here")[0])
    assert LS.MISSING in svg and svg.count("<image") == 1          # the main label only, no care label art
    assert [os.path.basename(p) for p in LS.files(shell)] == ["main-label-6.5x2cm-white.pdf"]


def test_cotton_shell_shows_the_cotton_care_label(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert LS.care_fibre(JACKET) == "100 % cotton"
    svg = "".join(LS.panel(0, 0, 86, JACKET, "main here", "care here")[0])
    assert LS.MISSING not in svg and svg.count("<image") == 3        # main + care front + care back
    assert "100 % cotton" in LS.care_bom(JACKET)
    got = LS.export(str(tmp_path / "labels"), JACKET)
    assert "main-label-6.5x2cm-white.pdf" in got and "haki-studios-care-label-100-cotton-white.pdf" in got


def test_export_drops_a_stale_care_label(tmp_path):
    d = str(tmp_path / "labels")
    LS.export(d, JACKET)
    assert LS.export(d, UNKNOWN[0]) == ["main-label-6.5x2cm-white.pdf"]


def test_proposed_fibre_is_amber_and_says_so(tmp_path, monkeypatch):
    """the jackets' '100% cotton duck' is our own proposal: the care label is shown, but as proposed, never as confirmed."""
    monkeypatch.chdir(tmp_path)
    svg = "".join(LS.panel(0, 0, 86, JACKET, "m", "c")[0])
    assert "[proposed — confirm fibre: 100 % cotton]" in svg and LS.AMBER in svg and LS.MISSING not in svg
    assert "[proposed — confirm fibre: 100 % cotton]" in LS.care_bom(JACKET)
    ok = "".join(LS.panel(0, 0, 86, JACKET, "m", "c", fibre_confirmed=True)[0])
    assert "confirm fibre" not in ok and "confirm fibre" not in LS.care_bom(JACKET, fibre_confirmed=True)


# ---- review nits on PR #54 (27 Oct 2026): every label mention is only as sure as the fibre / the factory ----
import re
import labels as LB

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
STATES = [  # (shell, fibre_confirmed, state)
    (JACKET, False, "proposed"), (JACKET, True, "confirmed"), (UNKNOWN[0], False, "missing"), (UNKNOWN[1], True, "missing")]


def _heading_fill(svg, start):
    m = re.search(r'<text [^>]*fill="([^"]+)"[^>]*>' + re.escape(start), svg)
    assert m, f"no heading starting {start!r}"
    return m.group(1)


@pytest.mark.parametrize("shell,ok,state", STATES)
def test_care_desc_suffix_follows_the_fibre_state(shell, ok, state):
    d, b = LS.care_desc(shell, fibre_confirmed=ok), LS.care_bom(shell, fibre_confirmed=ok)
    if state == "proposed":
        assert d.startswith("Haki standard care label, 100 % cotton [proposed — confirm fibre: 100 % cotton]:")
        assert b.endswith("[proposed — confirm fibre: 100 % cotton]") and LS.MISSING not in d + b
    elif state == "confirmed":
        assert d.startswith("Haki standard care label, 100 % cotton:") and "[proposed" not in d + b and LS.MISSING not in d + b
    else:
        assert LS.MISSING in d and LS.MISSING in b and "[proposed" not in d + b and "cotton]" not in d + b
        assert "satin" not in d + b                                        # never describes a label it cannot pick


@pytest.mark.parametrize("shell,ok,state", STATES)
def test_care_heading_is_amber_unless_the_fibre_is_confirmed(shell, ok, state, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    want = LS.GREEN if state == "confirmed" else LS.AMBER
    svg = "".join(LS.panel(0, 0, 86, shell, "m", "c", fibre_confirmed=ok)[0])
    assert _heading_fill(svg, "CARE LABEL — ") == want
    hp = "".join(LS.hoodie_page(lambda *a: [], shell, fibre_confirmed=ok))
    assert _heading_fill(hp, "CARE LABEL — ") == want


@pytest.mark.parametrize("shell,ok,state", STATES)
def test_patches_row_says_no_more_than_we_know(shell, ok, state):
    r = LS.patches_row(shell, ok)
    assert r.startswith("no embroidered patches or labels — Haki standard main label; care label ")
    assert "woven" not in r and "printed" not in r                       # construction + print are not confirmed here
    assert {"proposed": "[proposed — confirm fibre: 100 % cotton]", "confirmed": "care label 100 % cotton (",
            "missing": LS.MISSING}[state] in r
    assert LS.flagged(r) == (state != "confirmed")


# every embroidery pack's Patches / labels row, from its own garment builder's SHELL_MAT (no copied string)
PACKS = {"castle-falls-jacket": "proposed", "drum-island-plum-pine": "proposed", "forestball": "proposed",
         "grand-line-jacket": "proposed", "moon": "proposed", "wave-jacket": "proposed",
         "comet-city-hoodie": "missing", "koi-blossom-hoodie": "missing", "red-beast-hoodie": "missing"}


@pytest.mark.parametrize("proj,state", sorted(PACKS.items()))
def test_each_pack_row_reads_its_own_shell(proj, state):
    d = os.path.join(ROOT, "projects", proj)
    assert LS.garment_shell(d), f"{proj}: no SHELL_MAT found in {LS.SHELL_SOURCES}"
    r = LS.pack_patches_row(d)
    assert (LS.MISSING in r) == (state == "missing") and ("[proposed — confirm fibre" in r) == (state == "proposed")
    src = open(os.path.join(d, "pack.py"), encoding="utf-8").read()
    assert "LS.pack_patches_row(" in src and "printed care label = Haki standard" not in src


def test_main_label_construction_is_proposed_until_a_factory_confirms(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert LS.main_weave() == LB.MAIN_WEAVE + " [proposed — confirm]"
    assert LS.PROPOSED in LS.main_bom() and LS.PROPOSED in LS.main_desc() and LS.flagged(LS.main_bom())
    svg = "".join(LS.panel(0, 0, 86, JACKET, "m", "c")[0])
    assert _heading_fill(svg, LB.MAIN_WEAVE) == LS.AMBER
    monkeypatch.setattr(LB, "MAIN_WEAVE_CONFIRMED", True)              # factory confirms -> every mark goes
    assert LS.main_weave() == LB.MAIN_WEAVE and LS.PROPOSED not in LS.main_bom() + LS.main_desc()
    assert _heading_fill("".join(LS.panel(0, 0, 86, JACKET, "m", "c")[0]), LB.MAIN_WEAVE) == LS.INK
    # one place only: labelsheet words it from labels.MAIN_WEAVE, never its own copy
    assert "damask" not in open(os.path.join(ROOT, "engine", "labelsheet.py"), encoding="utf-8").read()


def test_jacket_bom_main_label_row_is_flagged_proposed():
    for proj in [p for p, s in PACKS.items() if s == "proposed"]:
        src = open(os.path.join(ROOT, "projects", proj, "gtp.py"), encoding="utf-8").read()
        assert '("Main label", LS.main_bom(), "white / black", "CB neck facing", "Haki file", "1", LS.main_proposed()),' in src, proj
