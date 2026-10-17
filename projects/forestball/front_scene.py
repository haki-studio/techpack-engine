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
            r = dict(r, col=fbcore.col(r["col"])); r["z"] = len(items); r["layer"] = layer; r["el"] = el; items.append(r)

limbs = []
def limb(pts_r, grp="TR", cover=0.9, seed=0, size=1.4):
    rr = [(*P(x, y), r * (1.35 if grp == 'TR' else 1.0)) for x, y, r in pts_r]
    # Rev B (close-up b): braided chain-stitch limb — rows of links in royal blue / navy / greens, cream specks on top
    regs, poly, Sm = FM.chain_limb(rr, random.Random(seed or 60 + len(limbs)), grp=grp, link=5.0 if grp == "TR" else 3.6)
    add(regs, 5); limbs.append((poly, Sm))

# side limbs first, main limb last (covers their bases)
limb([(300, 282, 6), (292, 252, 5), (285, 225, 4.2), (282, 200, 3.4)], grp="LM", seed=21, cover=0.8)
limb([(430, 352, 5.5), (448, 322, 4.8), (470, 298, 4), (500, 280, 3.3)], grp="LM", seed=22, cover=0.75)
# Rev B: limb runs level across the zip (centre y and width equal at x = ±15) so 02R and 02L meet as one branch
MAIN = [(150, 138, 13), (176, 168, 15), (205, 204, 15.5), (240, 238, 15), (270, 260, 14.5), (300, 280, 13.5), (330, 300, 12.5),
        (350, 316, 11.5), (362, 320, 11), (375, 321, 11), (388, 322, 11), (402, 326, 10.5), (420, 342, 9), (445, 362, 8.5), (475, 382, 7.5), (505, 398, 6.5), (540, 410, 5.5),
        (575, 419, 4.6), (605, 426, 3.6)]
limb(MAIN, seed=20, cover=0.6, size=1.3)   # Rev B: blue chain bark shows below the moss, as the mockup
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
        add(FM.leaf_spray((p0.x, p0.y), ta + side * g.uniform(35, 60), g.uniform(26, 36), g, leaf=11.0)[0], 7)
        side = -side; s_ += g.uniform(7, 9.5)
    e = ln.interpolate(ln.length); e0 = ln.interpolate(ln.length - 2)
    add(FM.leaf_spray((e.x, e.y), math.degrees(math.atan2(e.y - e0.y, e.x - e0.x)), 28, g, leaf=11.0)[0], 7)
# sprays straight off the main limb (mockup: leaves all along the limb), bases snapped to the bark (LESSONS A1)
SPR = [((215, 190), -70), ((255, 245), 140), ((282, 262), -60), ((230, 215), -100), ((262, 240), -40), ((320, 300), 120), ((340, 300), -50),
       ((300, 290), 150), ((250, 250), 110), ((380, 330), 100), ((205, 180), 160), ((345, 310), -80), ((360, 330), 120), ((405, 345), -70),
       ((465, 372), -60), ((500, 400), 100), ((520, 402), -80), ((560, 415), -50), ((185, 160), -100)]
SUPPORT = unary_union([BARK] + [l.buffer(1.0) for l in twig_lines])
for i, ((bx, by), ang) in enumerate(SPR):
    a, _ = nearest_points(SUPPORT, Point(P(bx, by)))
    add(FM.leaf_spray((a.x, a.y), ang, 32, random.Random(600 + i), leaf=11.0)[0], 7)

# hanging moss over the wearer's right shoulder: strands hang FROM the main limb (anchors on its underside)
main_poly = limbs[-1][0]
anchors = []
for px in np.linspace(138, 222, 22):
    x = P(px, 0)[0]; col = main_poly.intersection(LineString([(x, -200), (x, 400)]))
    if col.is_empty: continue
    anchors.append((x, col.bounds[3] - 2.5))
ROPES = [  # px (front.png) + radius mm, traced from the 4x crop: 3 ropes bend over the limb at the shoulder and hang down
    ([(170, 140, 9), (160, 175, 10), (150, 215, 10), (142, 260, 10), (137, 310, 9.5), (136, 360, 8.5), (140, 400, 6.5), (146, 430, 4)], "navy"),
    ([(200, 150, 10), (192, 190, 11.5), (186, 230, 12), (180, 280, 11.5), (172, 330, 10.5), (164, 380, 9), (158, 415, 6.5), (156, 440, 4)], "bark"),
    ([(226, 168, 7), (215, 215, 8), (206, 260, 8), (198, 305, 7.5), (192, 350, 6.5), (190, 385, 4.5), (192, 405, 3)], "navy"),
    ([(150, 152, 5), (143, 200, 6), (133, 250, 6), (128, 300, 5.5), (128, 345, 4.5), (132, 380, 3)], "bark")]
ROPE_UP = ["leaf", "mosslt", "leaf", "moss"]; ROPE_MID = ["royal", "leaf", "mosslt", "navy", "royal"]; ROPE_LOW = ["navy", "royal", "mossdk"]
HM = []; rope_lines = []
for ri, (pts, c) in enumerate(ROPES):
    rr = [(*P(x, y), r) for x, y, r in pts]
    regs, rp, rS = FM.chain_limb(rr, random.Random(70 + ri), grp="HM", link=4.2, up=ROPE_UP, mid=ROPE_MID, low=ROPE_LOW, cream=0.04)
    HM += regs; rope_lines.append((rp, rS))
# free looping chain strands (close-up c texture): thin loop chains hanging along + below the ropes, yellow-green + blue
gl = random.Random(91)
for k in range(16):
    rp, rS = rope_lines[k % len(rope_lines)]
    j = gl.randint(2, max(3, len(rS) // 2)); x0, y0, r0 = rS[j]; side = gl.choice((-1, 1))
    L = gl.uniform(60, 150); ph = gl.uniform(0, 6.3); dx0 = side * r0 * gl.uniform(0.4, 1.1)
    pts = [(x0 + dx0 + 3.0*math.sin(ph + t*7) + side*t*gl.uniform(2, 8), y0 + t*L) for t in np.linspace(0, 1, 30)]
    HM.append(FM.loop_chain(pts, gl, ["leaf", "mosslt", "royal", "leaf", "moss"][k % 5], ring=gl.uniform(0.9, 1.4)))
add(HM, 6)          # sews with the limb moss (same threads, fewer stops)
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
        inter = bark.intersection(LineString([(xx * 1.04, -150), (xx * 1.04, 900)]))   # 0.6 inside the art edge (art ends at ±15.3)
        segs = [inter] if inter.geom_type == "LineString" else [g for g in getattr(inter, "geoms", []) if g.geom_type == "LineString"]
        for s in segs:
            ys = [c[1] for c in s.coords]
            if max(ys) - min(ys) > 1.5: out.append((xx, min(ys), max(ys)))
    return out
