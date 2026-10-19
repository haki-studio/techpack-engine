"""Zip hoodie block (engine/hoodie.py): derived from the approved Drum Island jacket — every size on the hoodie chart,
seam walks equal, shapes valid, and the inherited body/sleeve pieces identical to the jacket's (LESSONS C9)."""
import pytest, drum, pattern as PT, hoodie as HD

@pytest.mark.parametrize("size", drum.SIZES)
def test_hoodie_measurements_match_chart(size):
    m, walks, mt = HD.measure(size); ch = HD.chart()
    for k, (name, how, vals, tol, src) in ch.items():
        assert abs(m[k] / 10 - vals[drum.SIZES.index(size)]) <= tol, f"{size} {k} {name}"

@pytest.mark.parametrize("size", drum.SIZES)
def test_hoodie_seam_walks_and_shapes(size):
    _, walks, mt = HD.measure(size)
    for nm, a, b, tol in walks:
        if tol is not None: assert abs(a - b) <= tol, nm
    bad = [c for c in HD.shape_checks(size) if not c[1]]
    assert not bad, bad

@pytest.mark.parametrize("size", ["XS", "M", "3XL"])
def test_hoodie_inherits_jacket_body(size):
    gj, _ = PT.draft(size); gh, _ = HD.draft(size)
    for code in ("B01", "F01", "F02", "K01", "K02", "L01", "L02"):
        assert gj[code].sew() == gh[code].sew(), code          # body pieces are the approved jacket's, unchanged
    assert not any(c in gh for c in ("C01", "C02", "IC01"))     # collar removed
    assert all(c in gh for c in ("H01", "H02", "H03", "H04"))


def _welt(g, code="F01"):
    import numpy as np
    pts = np.array(dict(g[code].internal)["WELT POCKET"][:4])
    c = pts.mean(axis=0); d = pts[1] - pts[0]
    return c, abs(np.degrees(np.arctan2(d[1], d[0])))

@pytest.mark.parametrize("size", ["XS", "M", "3XL"])
def test_hoodie_welt_override(size):
    """per-design welt (LESSONS: mockup welts at 54-61 deg on the hooded designs): default unchanged, override moves only the welt."""
    g0, _ = HD.draft(size); gd, _ = PT.draft(size)
    assert dict(g0["F01"].internal) == dict(gd["F01"].internal)          # default = the Drum Island welt
    w = dict(cx=245.0, cy=400.0, angle=58.0)
    g1, _ = HD.draft(size, welt=w); gv, _ = HD.Variant(welt=w).draft(size)
    c, ang = _welt(g1)
    assert abs(ang - 58.0) < 0.5 or abs(ang - 122.0) < 0.5
    if size == "M": assert abs(abs(c[0]) - 245.0) < 0.5 and abs(c[1] - 400.0) < 0.5
    assert dict(g1["F01"].internal) == dict(gv["F01"].internal)
    for code in ("B01", "F01", "F02"):
        assert g0[code].sew() == g1[code].sew(), code                     # outlines untouched
    _, walks, _ = HD.measure(size)
