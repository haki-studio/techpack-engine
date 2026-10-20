"""LESSONS A16 gate, red-then-green on the Castle Falls Rev B village (founder, 19 Oct 2026): house walls traced as
colour blobs, each sewn at its own 'auto' satin angle or a random tatami angle -> stitch directions all over a wall."""
import random, qa
from shapely.geometry import box, Polygon

def test_chaotic_wall_fails_constructed_wall_passes():
    rng = random.Random(1)
    blobs = [dict(geom=box(x, 0, x + 3, 3), stype="satin", angle="auto", grp="WALL", unit="house1") for x in range(0, 30, 4)]
    frags = [dict(geom=box(x, 4, x + 6, 10), stype="tatami", angle=rng.uniform(0, 180), grp="WALL", unit="house1") for x in range(0, 30, 7)]
    bad = qa.angle_coherence(blobs + frags)
    assert any(b["kind"] == "satin-on-blob" for b in bad) and any(b["kind"] == "angle-spread" for b in bad), bad   # RED
    good = [dict(geom=box(0, 0, 30, 10), stype="tatami", angle=0.0, grp="WALL", unit="house1"),
            dict(geom=Polygon([(0, 0), (15, -6), (30, 0)]), stype="tatami", angle=90.0, grp="ROOF", unit="house1"),
            dict(geom=box(4, 2, 4.8, 8), stype="satin", angle="auto", grp="WALL", unit="house1")]                 # a mullion: stroke
    assert qa.angle_coherence(good) == []                                                                          # GREEN

def test_dstlive_renders(tmp_path):
    import pyembroidery as pe, dstlive
    p = pe.EmbPattern()
    for i in range(20): p.add_stitch_absolute(pe.STITCH, (i % 2) * 100, i * 4)
    p.add_command(pe.END); f = str(tmp_path / "t.dst"); pe.write_dst(p, f)
    im = dstlive.render(f, ["#ffffff"], ppm=8)
    assert im.size[0] > 50 and im.getextrema()[0][1] > 150


def _stripes(ang_deg, W=200, H=200, ppm=4.0, period_mm=0.8):
    import numpy as np, math
    y, x = np.mgrid[0:H, 0:W] / ppm; a = math.radians(ang_deg)
    # threads along ang -> intensity varies across them
    return 128 + 100 * np.sin(2 * math.pi * (-x * math.sin(a) + y * math.cos(a)) / period_mm)

def _rows(ang_deg, n=400, L=3.0, rng=None, W=50.0):
    import math, random
    rng = rng or random.Random(0); out = []
    for _ in range(n):
        x, y = rng.uniform(2, W - 2), rng.uniform(2, W - 2); a = math.radians(ang_deg if ang_deg is not None else rng.uniform(0, 180))
        out.append((x, y, x + L * math.cos(a), y + L * math.sin(a)))
    return out

def test_direction_match_red_then_green():
    """any motif: stitches along the reference thread grain pass; wrong angle or chaotic (fan / random) fail."""
    ref = _stripes(30)
    good = qa.direction_match(ref, 4.0, _rows(30))
    assert good["pct_ok"] >= 90, good                                          # GREEN: along the grain
    wrong = qa.direction_match(ref, 4.0, _rows(100))
    assert wrong["pct_ok"] < 20 and wrong["fail_dev"], wrong                   # RED: 70 deg off the grain
    chaos = qa.direction_match(ref, 4.0, _rows(None))
    assert chaos["pct_ok"] < 20 and chaos["fail_chaos"], chaos                 # RED: every which way
