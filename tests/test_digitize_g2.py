"""ENGINE_PLAN G2: generic primitive pieces the session-written labels on an UNSEEN mockup needed (Koi FR, zero subject
code). Every guard here was proven red first (RECAP-2026-10-22-engine-g2.md)."""
import math
import numpy as np
from shapely.geometry import Polygon

from test_digitize_g1 import _ctx, _lp, _claim, _audit

FAN = Polygon([(10, 29), (10, 31), (34, 44), (36, 30), (34, 16)])     # a fan: narrow root at x 10, wide at x ~35


def _fan_img(X, Y):
    from shapely import contains_xy as contains
    return np.where(contains(FAN, X, Y), "white", "navy")


def _fan_parts(**params):
    from digitize import primitives
    ctx = _ctx(_fan_img)
    lp = _lp("radial", tones=["white"], params=dict(centres="seeds", bead=False, **params))
    lp["seeds"] = [(10.5, 30.0)]
    parts, used = primitives.get("radial")(ctx, lp, 4.0, _claim(ctx, ["white"]))
    return parts, used


def test_radial_traced_fan_sews_the_whole_traced_shape_from_its_root_seed():
    parts, used = _fan_parts(shape="traced")
    fl = [p for p in parts if p.kind == "radial"]
    assert len(fl) == 1
    p = fl[0]
    assert p.geom.area >= 0.9 * FAN.area                         # the traced shape, not a capped disc at the root
    assert p.geom.symmetric_difference(FAN).area <= 0.15 * FAN.area
    assert math.dist(p.meta["centre"], (10.5, 30.0)) < 1e-6     # rays from the labelled root
    assert p.dir.mode == "radial" and p.meta["construct"]["rule"] == "radial"
    assert _audit(fl)["random_angles"] == 0


def test_radial_default_shape_still_caps_the_floret_at_its_centre():
    parts, _ = _fan_parts()                                      # lobed (default): a root on the edge fits no floret
    assert sum(p.geom.area for p in parts if p.kind == "radial") < 0.2 * FAN.area


def test_radial_traced_fan_stitches_stay_on_rays_and_short():
    import dst2
    parts, _ = _fan_parts(shape="traced")
    p = next(q for q in parts if q.kind == "radial")
    cx, cy = p.meta["centre"]
    pts = dst2.radial_satin(p.geom, cx, cy, sp=0.45, pull=0.0, fan=p.meta["fan"])
    seg = [(a, b) for a, b in zip(pts, pts[1:]) if math.dist(a, b) > 0.3]
    assert max(math.dist(a, b) for a, b in seg) <= 7.0 + 1e-6    # a 25 mm fan is cut into <= 7 mm stitches (dst2 split)


def test_a_floret_round_its_centre_keeps_its_ray_order_and_every_piece():
    import dst2, stitchrender as SR
    from shapely.geometry import Point
    disc = Point(0, 0).buffer(3.0, 64)
    segs = SR.radial(disc, 0.2, -0.1, 0.45)
    rays, fan = dst2._fan_order(segs, 0.2, -0.1)
    assert fan is False and rays is segs                        # florets (M5 konpeito, Castle) sew exactly as before


def test_fan_order_starts_after_the_empty_sector_and_drops_the_stubs_behind_the_root():
    import dst2, stitchrender as SR
    rays, fan = dst2._fan_order(SR.radial(FAN, 10.5, 30.0, 0.45), 10.5, 30.0)
    assert fan is True and min(r.length for r in rays) >= 1.0
    ang = [math.degrees(math.atan2(r.centroid.y - 30.0, r.centroid.x - 10.5)) for r in rays]
    steps = [abs(b - a) for a, b in zip(ang, ang[1:])]
    assert max(steps) < 10.0                                     # one sweep across the fan, no wrap


def test_an_edge_centred_floret_without_the_fan_flag_sews_exactly_as_before(monkeypatch):
    import dst2
    from shapely.geometry import Point
    disc = Point(0, 0).buffer(3.0, 64)                           # centre near the edge: an empty sector > 30 deg
    assert dst2._fan_order(__import__("stitchrender").radial(disc, 2.6, 0.0, 0.45), 2.6, 0.0)[1] is True
    now = dst2.radial_satin(disc, 2.6, 0.0, sp=0.45)
    monkeypatch.setattr(dst2, "_fan_order", lambda segs, cx, cy, **k: (segs, False))
    assert now == dst2.radial_satin(disc, 2.6, 0.0, sp=0.45)    # Castle's 79 such florets keep their hash (identity_check)


def test_the_traced_fan_part_carries_the_fan_flag_to_the_stitcher():
    parts, _ = _fan_parts(shape="traced")
    assert next(q for q in parts if q.kind == "radial").meta.get("fan") is True
    parts, _ = _fan_parts()
    assert all("fan" not in q.meta for q in parts if q.kind == "radial")
