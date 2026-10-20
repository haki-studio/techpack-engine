"""KCOS Rev C gates (PR #20 review): each proven red on a synthetic failing file and green on a passing one.
foam_gates (LESSONS B40), the foam travel mask in the project's make_pattern patch (B40), straight_chains (B41) and the
per-glyph text gate glyph_check (A32)."""
import os, sys, math, tempfile
import numpy as np
import pyembroidery as pe
from shapely.geometry import box, Polygon
from shapely.ops import unary_union

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJ = os.path.join(ROOT, "projects", "keep-clean-our-space-hoodie")
if PROJ not in sys.path: sys.path.insert(0, PROJ)
import kcgates as G


def write_dst(stops):
    """stops: [[(x, y), ...] per stop] in mm, origin 0 -> a DST path"""
    p = pe.EmbPattern()
    for i, pts in enumerate(stops):
        if i: p.add_command(pe.COLOR_CHANGE)
        p.add_thread(pe.EmbThread("#FF0000" if i else "#00FF00"))
        p.add_stitch_absolute(pe.JUMP, pts[0][0] * 10, pts[0][1] * 10)
        for x, y in pts: p.add_stitch_absolute(pe.STITCH, x * 10, y * 10)
        p.add_command(pe.TRIM)
    p.add_command(pe.END)
    path = os.path.join(tempfile.mkdtemp(), "t.dst"); pe.write_dst(p, path); return path


PUFF = box(10, 0, 30, 10)
PER_STOP = [dict(stop=1, puff=False, codes=["GLOW"], col="kc_glow"), dict(stop=2, puff=True, codes=["PF-STR"], col="kc_red")]
PUFF_PTS = [(x, y) for x in np.arange(11, 29, 1.0) for y in (1, 9)]

def test_foam_gate_red_on_flat_stitches_inside_the_foam():
    flat_through = [(float(x), 5.0) for x in np.arange(0, 41, 1.5)]          # a flat run crossing the puff footprint
    g = G.foam_gates(write_dst([flat_through, PUFF_PTS]), PER_STOP, PUFF, (0, 0))
    assert g["foam_stop_ok"] and not g["base_under_puff_ok"] and sum(g["base_under_puff"].values()) >= 10

def test_foam_gate_green_inside_the_keep_band_and_outside():
    flat_ok = [(float(x), 5.0) for x in np.arange(0, 10.9, 1.0)] + [(10.8, 5.0)]     # ends 0.8 mm inside the puff edge
    g = G.foam_gates(write_dst([flat_ok, PUFF_PTS]), PER_STOP, PUFF, (0, 0))
    assert g["foam_stop_ok"] and g["base_under_puff_ok"]

def test_foam_gate_red_on_flat_stop_after_the_puff_and_on_mixed_stops():
    ps = PER_STOP + [dict(stop=3, puff=False, codes=["DOT"], col="kc_white")]
    g = G.foam_gates(write_dst([[(0, 0), (1, 0)], PUFF_PTS, [(50, 0), (51, 0)]]), ps, PUFF, (0, 0))
    assert not g["foam_stop_ok"] and g["flat_after_puff"] == [3]
    ps2 = [PER_STOP[0], dict(stop=2, puff=True, codes=["PF-STR", "DOT"], col="kc_red")]
    assert not G.foam_gates(write_dst([[(0, 0), (1, 0)], PUFF_PTS]), ps2, PUFF, (0, 0))["foam_stop_ok"]


def test_straight_chain_red_on_a_stipple_bridge_green_on_stipple():
    rng = np.random.default_rng(1)
    walk = [(0.0, 0.0)]
    for _ in range(300):
        a = rng.uniform(0, 2 * math.pi); walk.append((walk[-1][0] + 0.8 * math.cos(a), walk[-1][1] + 0.8 * math.sin(a)))
    bridge = [(walk[-1][0] + 1.6 * i, walk[-1][1]) for i in range(1, 25)]           # a 38 mm straight hop, 1.6 mm stitches
    ps = [dict(stop=1, codes=["GLOW"])]
    assert G.straight_chains(write_dst([walk]), ps) == []
    red = G.straight_chains(write_dst([walk + bridge]), ps)
    assert len(red) == 1 and red[0][1] >= 35
    assert G.straight_chains(write_dst([walk + bridge]), [dict(stop=1, codes=["TXC"])]) == []   # text strokes are not sheer


def tian(w=20.0, s=2.0, cross=True):
    """田 (cross=True) or 日-like box with only the horizontal bar (the Rev B/C 界 bug)"""
    outer = box(0, 0, w, w); inner = box(s, s, w - s, w - s)
    g = outer.difference(inner).union(box(0, w / 2 - s / 2, w, w / 2 + s / 2))
    if cross: g = g.union(box(w / 2 - s / 2, 0, w / 2 + s / 2, w))
    return g

def test_glyph_check_red_on_a_dropped_stroke_green_on_the_glyph():
    ref = tian(); bb = (-2, -2, 22, 22); ppm = 8.0
    good = G.glyph_check(ref, G.raster(ref.buffer(0.1), bb, ppm), bb, ppm)
    assert good["ok"] and good["counters"] == (4, 4), good
    bad = G.glyph_check(ref, G.raster(tian(cross=False), bb, ppm), bb, ppm)
    assert not bad["ok"] and bad["counters"][1] < 4 and bad["miss_mm2"] > 3.0, bad
    assert bad["iou"] > 0.80                       # the case IoU alone lets through (界 read 0.81 on the Rev C file)


def test_foam_mask_keeps_flat_travel_out_of_the_foam():
    """the project's make_pattern patch (kccore): a flat stop with two pieces either side of a later puff block may not
    route its travel under the puff (Rev C FR M: 12 points before the mask, 0 after). KC_FOAM_MASK=0 = the old router."""
    cwd = os.getcwd()
    try:
        import kccore, tech, specbase as SB
        dst2 = kccore.patch_dst2()
        miss = [k for k in kccore.KC_KEYS if k not in SB.TH]      # specbase may have been imported by an earlier test
        if miss: SB.TH.update(tech.thread_table(miss))
        flat = [dict(col="kc_glow", geom=box(0, 0, 10.0, 10), st="tatami", ang=0, grp="GLOW-D", layer=20, z=1, el="t"),
                dict(col="kc_glow", geom=box(30.0, 0, 40, 10), st="tatami", ang=0, grp="GLOW-D", layer=20, z=2, el="t")]
        puff = [dict(col="kc_red", geom=box(9, 0, 31, 10), st="satin", ang=90, grp="PF-STR", layer=31, z=3, el="t")]
        def build(mask):
            os.environ["KC_FOAM_MASK"] = "1" if mask else "0"
            stops = [dict(col="kc_glow", regions=flat, puff=False, top=False), dict(col="kc_red", regions=puff, puff=True, top=False)]
            pat, _ = dst2.make_pattern(flat + puff, stops, (0, 0))
            path = os.path.join(tempfile.mkdtemp(), "m"); dst2.write(pat, path)
            ps = [dict(stop=1, puff=False, codes=["GLOW-D"]), dict(stop=2, puff=True, codes=["PF-STR"])]
            return G.foam_gates(path + ".dst", ps, unary_union([r["geom"] for r in puff]), (0, 0), keep=1.0)
        old, new = build(False), build(True)
        assert not old["base_under_puff_ok"], old             # RED: travel hidden under the later puff
        assert new["base_under_puff_ok"], new                 # GREEN: trimmed / routed round it instead
    finally:
        os.environ.pop("KC_FOAM_MASK", None); os.chdir(cwd)
