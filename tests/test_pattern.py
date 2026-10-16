"""Pattern QA: every size within the chart tolerance, seam walks equal, shape checks pass (LESSONS C1-C3)."""
import pytest, drum, pattern as PT, pattern_out as PO

@pytest.mark.parametrize("size", drum.SIZES)
def test_measurements_match_chart(size):
    m, walks, mt = PO.measure(size)
    for k, (name, how, vals, tol) in drum.POM_CM.items():
        assert abs(m[k] / 10 - vals[drum.SIZES.index(size)]) <= tol, f"{size} {k} {name}"

@pytest.mark.parametrize("size", drum.SIZES)
def test_seam_walks(size):
    _, walks, mt = PO.measure(size)
    for nm, a, b, tol in walks:
        if tol is not None: assert abs(a - b) <= tol, nm
    assert 8 <= mt["cap"] - mt["AH"] <= 16          # cap ease

@pytest.mark.parametrize("size", ["XS", "M", "3XL"])
def test_shape_checks(size):
    bad = [c for c in PO.shape_checks(size) if not c[1]]
    assert not bad, bad
