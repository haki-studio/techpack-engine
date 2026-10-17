"""F1 factory-requests page + factory profile (process: strike-off, frames, thread card, quote basis)."""
import json, os, tempfile
import factory

SO = [dict(file="HAKI_X_01_back_M.dst", piece="back", stitches=127339, trims=298)]
TH = [dict(name="Moon taupe", code="Polyneon 1234", de=6.2), dict(name="Cream", code="Polyneon 1001", de=1.1)]
PC = [dict(piece="back", w=420, h=505, hoopings=4), dict(piece="chest", w=200, h=180, hoopings=1)]

def _prof(**kw):
    p = os.path.join(tempfile.mkdtemp(), "factory.json"); json.dump(kw, open(p, "w")); return factory.load(p)

def test_page_asks_for_what_is_unknown():
    svg = factory.requests_page("Test jacket", SO, TH, PC, prof=_prof())[0]
    assert "HAKI_X_01_back_M.dst" in svg and "127,339" in svg
    assert "Moon taupe" in svg and "Cream" not in svg          # only weak thread matches go on the dip list
    assert "4 hoopings" in svg and "chest" not in svg          # only multi-hooping pieces listed
    assert "confirm" in svg                                    # frames not confirmed -> asked

def test_confirmed_frames_are_not_asked_again():
    svg = factory.requests_page("Test", SO, TH, PC, prof=_prof(frames_mm=[[360, 360], [300, 520]], frames_confirmed=True))[0]
    assert "Frames on file" in svg and "hoopings today" not in svg

def test_largest_frame_and_profile_file():
    assert factory.largest_frame(_prof(frames_mm=[[360, 360], [300, 520]])) == (300, 520)
    assert factory.load()["spm"] > 0                           # repo factory.json parses

def test_page_renders():
    import cairosvg
    png = cairosvg.svg2png(bytestring=factory.requests_page("Test", SO, TH, PC)[0].encode())
    assert len(png) > 5000


def test_thread_limit_from_profile():
    """manufacturer limit (12 colours per file) comes from factory.json, and a file over it is refused"""
    import tempfile, os, dst2, tech
    from test_stitch_engine import motif
    assert factory.max_threads() == factory.load()["needles"]
    vis = dst2.clean_vis(motif()); stops = dst2.merge_stops(tech.stops(vis, tech.STITCH_LAYER))
    pat, _ = dst2.make_pattern(vis, stops, (40, 20)); b = os.path.join(tempfile.mkdtemp(), "t"); dst2.write(pat, b)
    assert factory.check_threads(b + ".pes") == 3
    import pytest
    with pytest.raises(ValueError):
        factory.check_threads(b + ".pes", prof=_prof(needles=2))
