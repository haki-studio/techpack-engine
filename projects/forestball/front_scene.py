"""02 Chest mossy branch, split at the CF zip: 02R (wearer's right: limb from the shoulder + hanging moss) and
02L (wearer's left: limb end + upper twigs). Garment coords as front.py; mockup px -> mm via front.P."""
import random, math
import numpy as np
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union, nearest_points
import fbcore
import fmotifs as FM
from front import *          # geometry, keep-outs, clip_for, P

items = []
def add(regs, layer, el="02"):
    for r in regs:
        if r["geom"] is not None and not r["geom"].is_empty:
            r = dict(r); r["z"] = len(items); r["layer"] = layer; r["el"] = el; items.append(r)

limbs = []
def limb(pts_r, grp="TR", cover=0.9, seed=0, size=1.4):
    rr = [(*P(x, y), r * (1.35 if grp == 'TR' else 1.0)) for x, y, r in pts_r]
    regs, mr, poly, Sm, mg = FM.mossy_limb(rr, random.Random(seed or 60 + len(limbs)), grp=grp, cover=cover, size=size)
    add(regs, 5); add(mr, 6); limbs.append((poly, Sm))

# side limbs first, main limb last (covers their bases)
limb([(300, 282, 6), (292, 252, 5), (285, 225, 4.2), (282, 200, 3.4)], grp="LM", seed=21, cover=0.8)
limb([(430, 352, 5.5), (448, 322, 4.8), (470, 298, 4), (500, 280, 3.3)], grp="LM", seed=22, cover=0.75)
MAIN = [(150, 138, 13), (176, 168, 15), (205, 204, 15.5), (240, 238, 15), (270, 260, 14.5), (300, 280, 13.5), (330, 300, 12.5),
        (358, 318, 11.5), (385, 334, 10.5), (415, 346, 9), (445, 362, 8.5), (475, 382, 7.5), (505, 398, 6.5), (540, 410, 5.5),
        (575, 419, 4.6), (605, 426, 3.6)]
limb(MAIN, seed=20, cover=0.95, size=1.5)
BARK = unary_union([l[0] for l in limbs])

TWIGS = [[(500, 280), (535, 262), (570, 240), (600, 222), (622, 212)],
         [(282, 200), (284, 180), (290, 160)],
         [(240, 238), (232, 266), (226, 292), (214, 318)],
         [(300, 280), (292, 310), (282, 338), (268, 364)],
         [(330, 296), (338, 326), (334, 352)],
         [(445, 362), (452, 390), (448, 414)],
         [(540, 410), (556, 436), (566, 452)],
         [(590, 423), (612, 440), (622, 452)],
         [(570, 240), (582, 262), (600, 282), (608, 300)]]
twig_lines = []
for tw in TWIGS:
    pts = [P(*p) for p in tw]; add(FM.twig(pts, 1.4, 1.0)[0], 5); twig_lines.append(LineString(pts))
for ti, ln in enumerate(twig_lines):
    g = random.Random(500 + ti); side = 1; s_ = 8.0
    while s_ < ln.length - 5:
        p0 = ln.interpolate(s_); p1 = ln.interpolate(min(ln.length, s_ + 1.0))
        ta = math.degrees(math.atan2(p1.y - p0.y, p1.x - p0.x))
        add(FM.leaf_spray((p0.x, p0.y), ta + side * g.uniform(35, 60), g.uniform(26, 34), g, leaf=12.5)[0], 7)
        side = -side; s_ += g.uniform(8, 11)
    e = ln.interpolate(ln.length); e0 = ln.interpolate(ln.length - 2)
    add(FM.leaf_spray((e.x, e.y), math.degrees(math.atan2(e.y - e0.y, e.x - e0.x)), 24, g, leaf=11.0)[0], 7)
# sprays straight off the main limb (mockup: leaves all along the limb), bases snapped to the bark (LESSONS A1)
SPR = [((215, 190), -70), ((255, 245), 140), ((282, 262), -60), ((345, 310), -80), ((360, 330), 120), ((405, 345), -70),
       ((465, 372), -60), ((500, 400), 100), ((520, 402), -80), ((560, 415), -50), ((185, 160), -100)]
SUPPORT = unary_union([BARK] + [l.buffer(1.0) for l in twig_lines])
for i, ((bx, by), ang) in enumerate(SPR):
    a, _ = nearest_points(SUPPORT, Point(P(bx, by)))
    add(FM.leaf_spray((a.x, a.y), ang, 30, random.Random(600 + i), leaf=11.0)[0], 7)

# hanging moss over the wearer's right shoulder: strands hang FROM the main limb (anchors on its underside)
main_poly = limbs[-1][0]
anchors = []
for px in np.linspace(150, 245, 15):
    x = P(px, 0)[0]; col = main_poly.intersection(LineString([(x, -200), (x, 400)]))
    if col.is_empty: continue
    anchors.append((x, col.bounds[3] - 2.5))
HM, HMU = FM.hanging_moss(anchors, random.Random(9), length=(120, 240), wmin=3.6, wmax=5.6, sway=14.0)
add(HM, 10)
# moss highlights on the strands (light run of the mockup's yellow-green chain stitch)
ANCH = anchors

PIECES = {"02R": ("02", "R"), "02L": ("02", "L")}
def build(piece):
    el, side = PIECES[piece]
    clip = clip_for(side)
    vis = []; above = Polygon()
    for r in reversed([r for r in items if r["el"] == el]):
        g = r["geom"].intersection(clip)
        v = g.difference(above); above = above.union(g)
        vis.append(dict(r, geom=v))
    vis.reverse()
    vis = [v for v in vis if not v["geom"].is_empty and v["geom"].area > 0.02]
    import back
    return back.absorb_slivers(vis)

def zip_marks():
    bark = limbs[-1][0]; out = []
    for xx in (-KEEP_CF, KEEP_CF):
        inter = bark.intersection(LineString([(xx, -150), (xx, 900)]))
        segs = [inter] if inter.geom_type == "LineString" else [g for g in getattr(inter, "geoms", []) if g.geom_type == "LineString"]
        for s in segs:
            ys = [c[1] for c in s.coords]
            if max(ys) - min(ys) > 1.5: out.append((xx, min(ys), max(ys)))
    return out
