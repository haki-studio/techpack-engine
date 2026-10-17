"""Hooded variant of the Drum Island block (collar -> 3-panel hood + sherpa lining + facing, rib -> self-fabric bands),
and proof that the default variant is unchanged (LESSONS C9-C11)."""
import json, copy
import pytest, drum, pattern as PT, pattern_out as PO
import dxf_golden

HOODED_POMS = [k for k in drum.POM_CM if k not in PO.COLLAR_POMS]

@pytest.fixture
def hooded(monkeypatch):
    monkeypatch.setattr(PO, "VARIANT", "hooded"); monkeypatch.setattr(PO, "HOOD", None)

# ---------------------------------------------------------------- default variant: byte-identical DXFs
def test_default_dxf_unchanged():
    golden = json.load(open(dxf_golden.GOLDEN))
    assert dxf_golden.current() == golden, "default-variant DXF changed (if intended: python3 tests/dxf_golden.py --write)"

def test_default_has_no_hood():
    g, mt = PT.draft("M")
    assert "C01" in g and "H01" not in g and "variant" not in mt
    assert g["R01"].category == "RIB" and g["R02"].category == "RIB"

# ---------------------------------------------------------------- hooded: pieces, chart, walks, shapes
def test_hooded_pieces():
    g, mt = PT.draft("M", variant="hooded")
    assert set(g) == set(PT.ORDER_HOODED)
    assert not {"C01", "C02", "IC01"} & set(g)
    for c in ("R01", "R02"):
        assert g[c].category == "BAND" and g[c].material.startswith("Shell"), c
    assert g["H05"].category == g["H06"].category == "LINING" and "Sherpa" in g["H05"].material
    assert all(e.sa == mt["hood"]["sa_lining"] for e in g["H05"].edges + g["H06"].edges)

@pytest.mark.parametrize("size", drum.SIZES)
def test_hooded_measurements_match_chart(size, hooded):
    m, walks, mt = PO.measure(size)
    assert not set(PO.COLLAR_POMS) & set(m)
    for k in HOODED_POMS:
        name, how, vals, tol = drum.POM_CM[k]
        assert abs(m[k] / 10 - vals[drum.SIZES.index(size)]) <= tol, f"{size} {k} {name}: {m[k]/10:.2f}"

@pytest.mark.parametrize("size", drum.SIZES)
def test_hood_matches_proposed_dims(size, hooded):
    _, _, mt = PO.measure(size); d = PT.hood_dims(size)
    for k, v in mt["hood_measured"].items():
        assert abs(v - d[k]) <= 1.0, f"{size} hood {k}: {v:.1f} vs {d[k]:.1f}"

@pytest.mark.parametrize("size", drum.SIZES)
def test_hooded_seam_walks(size, hooded):
    _, walks, mt = PO.measure(size)
    names = [w[0] for w in walks]
    for must in ("Hood neck vs body neck (CF to CF)", "Sherpa + facing neck vs body neck (CF to CF)",
                 "Hem band vs body hem (woven, 1:1)", "Cuff vs shell sleeve opening (woven, 1:1)"):
        assert must in names
    for nm, a, b, tol in walks:
        if tol is not None: assert abs(a - b) <= tol, f"{size} {nm}: {a:.1f} vs {b:.1f}"
    assert 8 <= mt["cap"] - mt["AH"] <= 16

@pytest.mark.parametrize("size", drum.SIZES)
def test_hooded_shape_checks(size, hooded):
    res = PO.shape_checks(size)
    bad = [c for c in res if not c[1]]
    assert not bad, bad
    names = " ".join(c[0] for c in res)
    for must in ("hood neck convex", "corner neck / centre seam", "corner centre seam / face", "turn-of-cloth", "woven cuff", "woven hem band"):
        assert must in names, must

# ---------------------------------------------------------------- overrides (a project can resize the hood)
def test_hood_override_is_local():
    before = copy.deepcopy(PT.HOOD)
    g, mt = PT.draft("M", "hooded", hood={"height": 360.0, "face_opening": 800.0})
    assert PT.HOOD == before
    sp = g["H01"].sew()
    assert abs(-min(p[1] for p in sp) - 360.0) <= 1.0
    assert abs(mt["hood_face"] - 800.0) <= 0.5
    assert PT.proposed("hooded", {"height": 360.0})["Hood height (CF neck point to crown, flat)"].startswith("36.0 cm")
    assert "Collar neck rise at front" not in PT.proposed("hooded") and PT.proposed() is PT.PROPOSED

def test_hood_impossible_dims_raise():
    with pytest.raises(ValueError): PT.draft("M", "hooded", hood={"face_opening": 1100.0})     # face edge taller than the hood
    with pytest.raises(ValueError): PT.draft("M", "hooded", hood={"width": 120.0})             # hood narrower than its neck
    with pytest.raises(ValueError): PT.draft("M", variant="hoodie")

# ---------------------------------------------------------------- the guards catch what they are for (red cases)
def test_band_check_red():
    g, _ = PT.draft("M", "hooded"); gd, _ = PT.draft("M")
    opening = g["S01"].edges[2].length
    assert PO.band_check(g["R02"], opening)[1]
    assert not PO.band_check(g["R02"], opening * 1.25)[1]               # woven cuff on a rib-ratio sleeve
    assert PO.band_check(gd["R02"], gd["S01"].edges[2].length)[1]       # knit rib still judged as rib
    assert not PO.band_check(gd["R02"], gd["R02"].edges[0].length)[1]   # rib with no stretch

def test_hood_neck_convex_red():
    g, _ = PT.draft("M", "hooded", hood={"neck_bow": -10.0})           # neck bowing INTO the hood
    assert not dict((c[0], c[1]) for c in PO.hood_checks(g))["H01 hood neck convex (chord inside piece)"]

def test_hood_corner_red():
    g, _ = PT.draft("M", "hooded")
    e = PO.edge(g["H01"], "centre seam"); p0, p1 = e.pts[0], e.pts[1]
    e.pts[1] = (p1[0] + abs(p1[1] - p0[1]), p1[1])                       # kink the seam 45° where it leaves the neck
    ok = dict((c[0], c[1]) for c in PO.hood_checks(g))
    assert not ok["H01 corner neck / centre seam square (90 ± 3°)"]

def test_turn_of_cloth_red():
    g, _ = PT.draft("M", "hooded", hood={"toc": 0.0})
    ok = dict((c[0], c[1]) for c in PO.hood_checks(g))
    assert not ok["H05+H03 sherpa + facing smaller than the shell side (turn-of-cloth)"]

def test_sew_simple_red():
    g, _ = PT.draft("M", "hooded"); pc = g["H05"]
    assert PO.sew_simple(pc)
    nk = PO.edge(pc, "neck"); nk.pts[len(nk.pts)//2] = (nk.pts[0][0] + 400, nk.pts[0][1] - 200)   # spike across the piece
    assert not PO.sew_simple(pc)

def test_hood_neck_walk_red(hooded, monkeypatch):
    real = PO.draft
    def wide_centre(size):
        g, mt = real(size); e = PO.edge(g["H02"], "neck end"); e.pts = [(e.pts[0][0] + 10, e.pts[0][1]), e.pts[1]]
        return g, mt
    monkeypatch.setattr(PO, "draft", wide_centre)
    _, walks, _ = PO.measure("M")
    nm, a, b, tol = next(w for w in walks if w[0] == "Hood neck vs body neck (CF to CF)")
    assert abs(a - b) > tol
