"""Zip hoodie block (engine/hoodie.py): derived from the approved Drum Island jacket — every size on the hoodie chart,
seam walks equal, shapes valid, and the inherited body/sleeve pieces identical to the jacket's (LESSONS C8)."""
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
