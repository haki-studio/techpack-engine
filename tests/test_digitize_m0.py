"""ENGINE_PLAN M0: honest gates. Each test below was RED against the gates on main before M0 (19 Oct 2026) and is GREEN
after it. What each one catches:
  - direction_match judged every stitch, so a 90-degree underlay under a 0-degree fill dragged a perfect fill into
    'chaotic' tiles: the gate measured the hidden layer, not what the eye sees.
  - angle_coherence grouped by `unit`; with no unit, unrelated walls pooled into one group and a small wall at a
    completely different angle hid behind a big one's area. Undeclared ("auto") fill angles were skipped silently.
  - at 4 ppm a thread is under 2 px: the reference grain is blur, the z-buffer cannot separate rows.
  - nothing measured density, stacking or satin shape on the file."""
import math, os, random
import numpy as np
import pytest
import qa
from shapely.geometry import box

PPM = 12.0


def _stripes(ang_deg, size_mm=48.0, ppm=PPM, period_mm=0.8):
    n = int(size_mm * ppm); y, x = np.mgrid[0:n, 0:n] / ppm; a = math.radians(ang_deg)
    return 128 + 100 * np.sin(2 * math.pi * (-x * math.sin(a) + y * math.cos(a)) / period_mm)


def _fill(ang_deg, x0, y0, x1, y1, spacing=0.4, stitch=3.0):
    """a boustrophedon tatami-like fill: rows at ang_deg (0 = along x, 90 = along y), connected, in sew order"""
    segs = []; vertical = abs(ang_deg - 90) < 1
    lo, hi = (x0, x1) if vertical else (y0, y1); a0, a1 = (y0, y1) if vertical else (x0, x1)
    k = 0; t = lo + spacing / 2; prev = None
    while t < hi:
        xs = list(np.arange(a0, a1, stitch)) + [a1]
        if k % 2: xs = xs[::-1]
        pts = [((t, s) if vertical else (s, t)) for s in xs]
        if prev is not None: segs.append(prev + pts[0])
        segs += [pts[i] + pts[i + 1] for i in range(len(pts) - 1)]
        prev = pts[-1]; t += spacing; k += 1
    return segs


# ------------------------------------------------------------------ direction_match: the visible layer only
def test_underlay_under_fill_does_not_lower_direction_ok():
    ref = _stripes(0)                                                    # threads along x everywhere
    fill = _fill(0, 1, 1, 47, 47, spacing=0.4)
    underlay = _fill(90, 1, 1, 47, 47, spacing=1.2)                      # 90-degree lattice underlay, sewn FIRST
    alone = qa.direction_match(ref, PPM, fill)
    both = qa.direction_match(ref, PPM, underlay + fill)
    assert alone["pct_ok"] >= 90, alone
    # RED on main: every stitch counted -> the underlay made the tiles 'chaotic' (R < 0.55), pct_ok fell to ~0
    assert both["pct_ok"] >= alone["pct_ok"], (both["pct_ok"], alone["pct_ok"], len(both["fail_chaos"]))


def test_underlay_on_top_is_still_judged():
    """the z-buffer is sew order: a 90-degree layer sewn AFTER the fill is the visible top and must fail"""
    ref = _stripes(0)
    top = _fill(0, 1, 1, 47, 47, spacing=0.4) + _fill(90, 1, 1, 47, 47, spacing=0.4)
    r = qa.direction_match(ref, PPM, top)
    assert r["pct_ok"] < 20 and r["fail_dev"], r


def test_direction_match_refuses_low_ppm():
    ref = _stripes(0, ppm=4.0)
    with pytest.raises(ValueError, match="12"):                          # RED on main: ran at 4 ppm and returned a score
        qa.direction_match(ref, 4.0, _fill(0, 1, 1, 47, 47))


def test_visible_segments_drops_buried_underlay():
    fill = _fill(0, 1, 1, 21, 21, spacing=0.4); under = _fill(90, 1, 1, 21, 21, spacing=1.2)
    vis = qa.visible_segments(under + fill, (0, 0, 22, 22), ppm=PPM)
    ang = [abs(math.degrees(math.atan2(s[3] - s[1], s[2] - s[0]))) % 180 for s in vis if math.hypot(s[2] - s[0], s[3] - s[1]) >= 0.6]
    vert = sum(1 for a in ang if 60 < a < 120)
    assert vert <= 0.02 * len(ang), (vert, len(ang))


# ------------------------------------------------------------------ angle_coherence: per part, declared angles
def test_walls_without_part_id_raise():
    """two walls, unit=None, very different angles: a 300 mm2 wall at 0 deg and an 8 mm2 wall at 90 deg. On main they
    pooled into one (None, WALL) group and the small wall hid behind the big one's area (spread 9.4 < 10 -> PASS)."""
    walls = [dict(geom=box(0, 0, 30, 10), stype="tatami", angle=0.0, grp="WALL", unit=None),
             dict(geom=box(40, 0, 44, 2), stype="tatami", angle=90.0, grp="WALL", unit=None)]
    with pytest.raises(ValueError, match="part id"):
        qa.angle_coherence(walls)
    # with part ids they are two walls, each with its own deliberate direction: that is correct
    ok = [dict(w, part=f"wall{i}") for i, w in enumerate(walls)]
    assert qa.angle_coherence(ok) == []


def test_constructed_part_with_auto_angle_fails():
    regs = [dict(geom=box(0, 0, 30, 10), stype="tatami", angle="auto", grp="WALL", part="house1.wall.front"),
            dict(geom=box(0, 10, 30, 20), stype="tatami", angle=None, grp="ROOF", part="house1.roof")]
    bad = qa.angle_coherence(regs)                                       # RED on main: 'auto' fills were skipped -> []
    kinds = [b["kind"] for b in bad]
    assert kinds.count("undeclared-angle") == 2, bad


def test_angle_spread_measured_on_visible_dst():
    """declared 0 deg, but the file sews the wall at two angles: the measured (DST) spread fails the part"""
    wall = [dict(geom=box(0, 0, 40, 20), stype="tatami", angle=0.0, grp="WALL", part="w")]
    good = _fill(0, 0, 0, 40, 20)
    assert qa.angle_coherence(wall, segs=qa.visible_segments(good, (0, 0, 40, 20))) == []
    mixed = _fill(0, 0, 0, 20, 20) + _fill(90, 20, 0, 40, 20)
    bad = qa.angle_coherence(wall, segs=qa.visible_segments(mixed, (0, 0, 40, 20)))
    assert any(b["kind"] == "angle-spread" and b["source"] == "dst" for b in bad), bad


# ------------------------------------------------------------------ new file gates
def test_density_map_flags_triple_stack():
    base = _fill(0, 0, 0, 60, 60, spacing=0.4)                           # one layer everywhere: 2.5 mm/mm2
    stack = _fill(90, 20, 20, 32, 32, spacing=0.4) + _fill(0, 20, 20, 32, 32, spacing=0.4)   # + 2 more on a 12 mm square
    one = qa.density_map(base, (0, 0, 60, 60))
    assert one["ok"] and 2.0 <= one["mean"] <= 3.0, (one["mean"], one["flags"])
    three = qa.density_map(base + stack, (0, 0, 60, 60))
    assert not three["ok"], three["flags"]
    f = three["flags"][0]
    assert 20 <= f["at_mm"][0] <= 32 and 20 <= f["at_mm"][1] <= 32 and f["area_mm2"] >= 50, f
    two = qa.density_map(base + _fill(90, 20, 20, 32, 32, spacing=0.4), (0, 0, 60, 60))
    assert two["ok"], two["flags"]                                       # two layers are allowed (rule 6)


def test_stack_map_counts_layers_not_underlay():
    under = _fill(90, 0, 0, 30, 30, spacing=1.5)
    runs = [under + _fill(0, 0, 0, 30, 30)]                              # one run: underlay + fill = ONE layer
    assert qa.stack_map(runs, (0, 0, 30, 30))["max"] == 1
    runs3 = runs + [_fill(90, 5, 5, 20, 20), _fill(0, 8, 8, 18, 18)]
    r = qa.stack_map(runs3, (0, 0, 30, 30))
    assert r["max"] == 3 and not r["ok"] and r["flags"], r["flags"]
    assert qa.stack_map(runs3[:2], (0, 0, 30, 30))["ok"]


def _satin(x0, y0, width, length, spacing=0.4):
    """vertical column: stitches zigzag across x (width), advancing along y (length), in sew order"""
    pts = []; t = 0.0; k = 0
    while t <= length:
        pts.append((x0 + (width if k % 2 else 0.0), y0 + t)); t += spacing / 2; k += 1
    return [pts[i] + pts[i + 1] for i in range(len(pts) - 1)]


def test_satin_shape_flags_blob():
    blob = qa.satin_shape(_satin(0, 0, 2.0, 2.0))
    assert not blob["ok"] and blob["counts"]["blob"] == 1, blob
    stroke = qa.satin_shape(_satin(0, 0, 2.0, 12.0))
    assert stroke["ok"] and stroke["satins"] == 1, stroke
    wide = qa.satin_shape(_satin(0, 0, 9.0, 40.0))
    assert wide["counts"]["too-wide"] == 1, wide
    narrow = qa.satin_shape(_satin(0, 0, 0.7, 10.0))
    assert narrow["counts"]["too-narrow"] == 1, narrow
    stud = qa.satin_shape(_satin(0, 0, 1.2, 1.2))                         # a 1.2 mm stud (rule 9) is allowed
    assert stud["ok"], stud
    assert qa.satin_runs(_fill(0, 0, 0, 30, 30)) == []                   # tatami rows are not satin
    assert qa.satin_runs(_satin(0, 0, 3.0, 20.0, spacing=2.0)) == []     # zigzag underlay (2 mm spacing) is not satin
    hub = (10.0, 10.0); fan = []                                          # radial satin: out and back to one hub point
    for k in range(20):
        a = math.radians(k * 6); tip = (hub[0] + 3 * math.cos(a), hub[1] + 3 * math.sin(a))
        fan += [hub + tip, tip + hub]
    fs = qa.satin_shape(fan)
    assert fs["counts"]["fan"] == 1 and fs["satins"] == 0 and fs["ok"], fs        # listed apart: floret or not needs parts


def test_satin_shape_reads_dst2_satins():
    """the stitches the engine really writes: dst2 satins put a 0.42 mm edge step between across stitches"""
    import dst2
    from shapely.geometry import LineString, Point
    def segs(pts): return [tuple(pts[i]) + tuple(pts[i + 1]) for i in range(len(pts) - 1) if tuple(pts[i]) != tuple(pts[i + 1])]
    stroke = qa.satin_shape(segs(dst2.turning_satin(box(0, 0, 2, 14), LineString([(1, 0), (1, 14)]))))
    assert stroke["ok"] and stroke["satins"] == 1, stroke
    blob = qa.satin_shape(segs(dst2.turning_satin(box(0, 0, 3, 3), LineString([(1.5, 0), (1.5, 3)]))))
    assert blob["counts"]["blob"] == 1, blob
    assert qa.satin_shape(segs(dst2.fixed_satin(box(0, 0, 3, 3), 0.0)))["counts"]["blob"] == 1
    assert qa.satin_shape(segs(dst2.radial_satin(Point(0, 0).buffer(3), 0, 0)))["counts"]["fan"] == 1
    under = [p for row in dst2.join_rows(dst2.tatami_rows(box(0, 0, 3.5, 30), 0.0, 2.0, 4.0)) for p in row]
    assert len(under) > 20 and qa.satin_runs(segs(under)) == []           # 2 mm underlay rows, one stitch each: not satin


def _write_dst(tmp_path, cmds):
    import pyembroidery as pe
    p = pe.EmbPattern()
    for c, x, y in cmds: p.add_stitch_absolute(c, x, y)
    p.add_command(pe.END); f = str(tmp_path / "t.dst"); pe.write_dst(p, f); return f


def test_trims_and_runs_from_readback(tmp_path):
    import pyembroidery as pe, readback
    cmds = [(pe.STITCH, i * 20, 0) for i in range(10)] + [(pe.TRIM, 180, 0)] + \
           [(pe.STITCH, 500 + i * 20, 300) for i in range(10)] + [(pe.TRIM, 680, 300)] + \
           [(pe.COLOR_CHANGE, 680, 300)] + [(pe.STITCH, 900, 900 + i * 20) for i in range(10)]
    f = _write_dst(tmp_path, cmds)
    rb = readback.dst(f); pts = readback.trim_points(f)
    assert len(pts) == rb["trims"] >= 2, (pts, rb["trims"])
    t = qa.trims_per_area(f, bounds=(-100, -100, 100, 100))
    assert t["trims"] == rb["trims"] and t["per_100cm2"] > 0
    runs = qa.dst_runs(f)
    assert sum(len(r["segs"]) for r in runs) == len(qa.dst_segments(f)) and len(runs) >= 3
    assert runs[-1]["stop"] == 1


# ------------------------------------------------------------------ registration (config as data)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(ROOT, "projects", "castle-falls-jacket", "bench", "registration.json")


def test_registration_tps_hits_matched_points():
    from digitize.extract import register
    cfg = register.load(REG)
    cu = next(c for c in cfg["closeups"] if c["name"] == "back_left")
    f = register.tps_map(cu, cfg)
    flat = np.array([p[1] for p in cu["pts"]], float); clo = np.array([p[0] for p in cu["pts"]], float)
    err = np.hypot(*(f(flat) - clo).T)
    assert np.median(err) < 25, err                                      # smoothed spline: close to, not on, the points


def test_registration_reference_is_12ppm_and_feathered():
    from digitize.extract import register
    cfg = register.load(REG)
    r = register.reference(cfg, "B", (-60, 450, -40, 470), ppm=12)
    assert r["rgb"].shape == (240, 240, 3) and r["ppm"] == 12
    assert r["weights"]["back_left"].min() > 0.6                         # inside the back_left close-up
