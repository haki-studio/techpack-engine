"""Motifs for the Castle Falls jacket (candidates for the engine library — ENGINE_NOTES.md).
Units mm, y down. Every function returns Region dicts like motifs2 (col, geom, st, ang, grp) + optional keys:
  ko=False  overlay sewn on top of the trace, does not knock it out;  unit = id of the motif (dropped whole at a keep-out)."""
import math
import numpy as np
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union
from shapely import affinity

def R(col, geom, st, ang, grp, **kw):
    d = dict(col=col, geom=geom, st=st, ang=ang, grp=grp); d.update(kw); return d

def polys(g):
    if g is None or g.is_empty: return []
    if g.geom_type == "Polygon": return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]

# ---------------------------------------------------------------- sakura
def floret(cx, cy, d, rot, col, centre="cf_cream", unit=None):
    """5-petal cherry floret, each petal notched at the tip; one radial satin + a centre dot (overlay on the blossom ground)"""
    r = d / 2; pets = []
    for k in range(5):
        a = math.radians(rot + k * 72); ux, uy = math.cos(a), math.sin(a)
        c = (cx + ux * r * 0.52, cy + uy * r * 0.52)
        e = affinity.rotate(affinity.scale(Point(c).buffer(1.0, quad_segs=10), r * 0.50, r * 0.36), math.degrees(a), origin=c)
        notch = Point(cx + ux * r * 1.04, cy + uy * r * 1.04).buffer(r * 0.16)
        pets.append(e.difference(notch))
    body = unary_union(pets).buffer(0.05).buffer(-0.05)
    cd = max(1.2, d * 0.24)
    ctr = Point(cx, cy).buffer(cd / 2, quad_segs=8)
    return [R(col, body.difference(ctr.buffer(0.15)), "satin", ("radial", cx, cy), "BL", unit=unit, ko=False),
            R(centre, ctr, "satin", "auto", "BL-c", unit=unit, ko=False)]

def petal(cx, cy, L, ang, col, unit=None):
    """falling petal: teardrop with a notch at the wide end (satin across)"""
    W = L * 0.62
    pts = []
    for t in np.linspace(0, 2 * math.pi, 40):
        x = L / 2 * math.cos(t); y = W / 2 * math.sin(t) * (0.55 + 0.45 * (1 + math.cos(t)) / 2)
        pts.append((x, y))
    p = Polygon(pts).difference(Point(L / 2 + 0.15, 0).buffer(L * 0.14))
    out = []
    if L >= 4.0:      # deeper-rose base at the stalk end (close-up strip, panel 2)
        base = p.intersection(box(-L / 2 - 1, -W, -L / 2 + 1.5, W))
        if base.area > 0.8:
            out.append(R("cf_rose", affinity.translate(affinity.rotate(base, ang, origin=(0, 0)), cx, cy).buffer(0), "satin", ang + 90, "PT", unit=unit))
            p = p.difference(base.buffer(0.05))
    p = affinity.translate(affinity.rotate(p, ang, origin=(0, 0)), cx, cy)
    return [R(col, p.buffer(0), "satin", ang + 90, "PT", unit=unit)] + out

# ---------------------------------------------------------------- original castle (IP: not the mockup's castle)
def _roof(cx, top, bot, w_top, w_eave, lift=3.0, n=24):
    """flared hip roof: ridge w_top wide at y=top, concave slopes to eave tips lifted by `lift` at y=bot"""
    L, Rr = cx - w_eave / 2, cx + w_eave / 2
    left = [(cx - w_top / 2 - (w_eave - w_top) / 2 * (t ** 1.7), top + (bot - top) * t - lift * t ** 6) for t in np.linspace(0, 1, n)]
    right = [(2 * cx - x, y) for x, y in left][::-1]
    under = [(L + 2.5, bot + 1.2), (Rr - 2.5, bot + 1.2)]
    return Polygon(left + under + right).buffer(0)

def castle(cx, y0, unit=None):
    """3-tier castle on a stone base, drawn for this jacket (original design). y0 = ridge top of the upper roof.
    Returns regions (layer set by the caller) + the outline used to knock the trace out."""
    regs = []
    tiers = [  # (roof h, wall h, ridge w, eave w, wall w)
        (22.0, 15.0, 30.0, 84.0, 56.0),
        (26.0, 20.0, 52.0, 124.0, 90.0),
        (30.0, 24.0, 78.0, 150.0, 120.0)]
    y = y0
    # roof ornaments: a pair of small gold shachi (fish) curls on the top ridge
    for s in (-1, 1):
        x = cx + s * 12
        body = LineString([(x, y + 0.5), (x + s * 1.2, y - 4.5), (x - s * 1.4, y - 7.5)]).buffer(1.25, cap_style="round")
        tail = Point(x - s * 2.2, y - 8.0).buffer(1.5)
        regs.append(R("cf_gold", unary_union([body, tail]), "satin", "auto", "ORN", unit=unit))
    outline = []
    for i, (rh, wh, rw, ew, ww) in enumerate(tiers):
        roof = _roof(cx, y, y + rh, rw, ew)
        regs.append(R("cf_navy", roof, "tatami", 0.0, "ROOF", unit=unit))
        # tile courses: 3 sky lines following the roof, gold eave line
        for f in (0.30, 0.55, 0.78):
            yy = y + rh * f; half = rw / 2 + (ew - rw) / 2 * (f ** 1.7) - 2.5
            ln = LineString([(cx - half, yy - (3.0 * f ** 6)), (cx + half, yy - (3.0 * f ** 6))]).buffer(0.55, cap_style="flat")
            regs.append(R("cf_sky", ln.intersection(roof.buffer(-0.6)), "satin", 90.0, "ROOF-ln", unit=unit, ko=False))
        eave = LineString([(cx - ew / 2 + 1, y + rh - 2.6), (cx - ew / 2 + 6, y + rh - 0.4), (cx + ew / 2 - 6, y + rh - 0.4), (cx + ew / 2 - 1, y + rh - 2.6)]).buffer(0.75)
        regs.append(R("cf_gold", eave, "satin", "auto", "ORN", unit=unit, ko=False))
        # gable (chidori-hafu) on the middle + lower roofs: white triangle with a gold edge
        if i >= 1:
            gw = 26.0 if i == 1 else 34.0
            for gx in ((cx,) if i == 1 else (cx - 34, cx + 34)):
                tri = Polygon([(gx - gw / 2, y + rh * 0.86), (gx, y + rh * 0.22), (gx + gw / 2, y + rh * 0.86)])
                regs.append(R("cf_white", tri.buffer(-1.0), "satin", 90.0, "WALL", unit=unit, ko=False))
                edge = LineString([(gx - gw / 2, y + rh * 0.86), (gx, y + rh * 0.22), (gx + gw / 2, y + rh * 0.86)]).buffer(0.7)
                regs.append(R("cf_gold", edge, "satin", "auto", "ORN", unit=unit, ko=False))
                regs.append(R("cf_gold", Point(gx, y + rh * 0.48).buffer(1.1), "satin", "auto", "DOT", unit=unit, ko=False))
        outline.append(roof)
        y += rh
        wall = box(cx - ww / 2, y - 0.5, cx + ww / 2, y + wh)
        regs.append(R("cf_white", wall, "tatami", 0.0, "WALL", unit=unit))
        # gold studs under the eave + window row
        n = int(ww / 7.5)
        for k in range(n):
            x = cx - ww / 2 + (k + 0.5) * ww / n
            regs.append(R("cf_gold", Point(x, y + 2.0).buffer(0.75), "satin", "auto", "DOT", unit=unit, ko=False))
            if k % 2 == 0 or i == 0:
                regs.append(R("cf_navy", box(x - 1.4, y + 4.6, x + 1.4, y + 4.6 + min(6.5, wh - 7)), "satin", 90.0, "WIN", unit=unit, ko=False))
        # base band of the wall (timber line)
        regs.append(R("cf_slate", box(cx - ww / 2, y + wh - 2.2, cx + ww / 2, y + wh), "satin", 90.0, "TMB", unit=unit, ko=False))
        outline.append(wall)
        y += wh
    # stone base (ishigaki): battered trapezoid, slate fill with mist course lines
    bt, bb = y - 0.5, y + 32.0
    base = Polygon([(cx - 64, bt), (cx + 64, bt), (cx + 74, bb), (cx - 74, bb)])
    regs.append(R("cf_slate", base, "tatami", 0.0, "STONE", unit=unit))
    for k, f in enumerate((0.22, 0.45, 0.68, 0.9)):
        yy = bt + (bb - bt) * f; hw = 64 + 10 * f
        regs.append(R("cf_mist", LineString([(cx - hw + 1.5, yy), (cx + hw - 1.5, yy)]).buffer(0.45), "bean", None, "STONE-ln", unit=unit, ko=False))
        for j in range(-6, 7):
            xx = cx + j * 11 + (5.5 if k % 2 else 0)
            if abs(xx - cx) < hw - 3:
                y_a = bt + (bb - bt) * (f - 0.21 if k else 0.02)
                regs.append(R("cf_mist", LineString([(xx, y_a), (xx, yy)]).buffer(0.45), "bean", None, "STONE-ln", unit=unit, ko=False))
    outline.append(base)
    return regs, unary_union(outline).buffer(0.6), bb
