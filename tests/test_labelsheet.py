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
