"""01 Back scene — mossy branch with leaf sprays, sheer light rays from the top right, stream, mossy rocks, grass;
the LICENSED orb in the stream is a marked placeholder box only (nothing drawn inside, water runs around it).
GARMENT coords (mm): x from CB (+ = wearer's right = viewer's right on a back view), y down from the CB neck seam.
Mockup inputs/back.png (726 x 870 px) -> mm: x = (px - 350) * SX, y = (py - 70) * SY (Drum Island block, size M)."""
import random, math
import numpy as np
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union, nearest_points
from shapely import affinity
import fbcore
from motifs import taper
import motifs2 as M
import fmotifs as FM
import drum

SX, SY = 1.10, 0.933
def warp_x(px):
    # mockup art runs over the side seams: compress the outer 30 px each side inward (side seams don't carry art)
    if px < 110: px = 110 - (110 - px) * 0.55
    if px > 600: px = 600 + (px - 600) * 0.55
    return px
def P(px, py): return ((warp_x(px) - 350) * SX, (py - 70) * SY)
S = 1.0                                  # motif size scale

# ---------------------------------------------------------------- garment model (Drum Island block, size M)
BLK = drum.Block("M")
HEM = BLK.b_hem
PANEL = BLK.back_panel()
ARM_L, ARM_R = BLK.back_arm_line(-1), BLK.back_arm_line(+1)
SIDE_L, SIDE_R = BLK.back_side_line(-1), BLK.back_side_line(+1)
SH_L = LineString([(-BLK.b_hps[0], BLK.b_hps[1]), (-BLK.b_sp[0], BLK.b_sp[1])])
SH_R = LineString([(BLK.b_hps[0], BLK.b_hps[1]), (BLK.b_sp[0], BLK.b_sp[1])])
NECK = LineString(drum.curve((-BLK.neck2, -BLK.bnd), (0, 0), 6, 12)[:-1] + drum.curve((0, 0), (BLK.neck2, -BLK.bnd), -6, 12))
KEEP_SIDE, KEEP_ARM, KEEP_SH, KEEP_HEM, KEEP_COLLAR = 15.0, 15.0, 15.0, 10.0, 6.0
CLIP_MARGIN = 0.6                        # clip 0.6 mm inside every keep-out so the pattern check reads >= 15.0, not 14.7 (Rev B)
COLLAR_FALL = 45.0                       # PROPOSED: back collar lying flat covers ~45 mm below the CB neck seam
_nk = list(NECK.coords)
COLLAR_B = Polygon(_nk + [(x, y + COLLAR_FALL * (1 - 0.35 * abs(x) / BLK.neck2)) for x, y in _nk[::-1]]).buffer(0)

CLIP = PANEL.difference(unary_union([ARM_L, ARM_R]).buffer(KEEP_ARM + CLIP_MARGIN)).difference(unary_union([SIDE_L, SIDE_R]).buffer(KEEP_SIDE + CLIP_MARGIN))
CLIP = CLIP.difference(unary_union([SH_L, SH_R]).buffer(KEEP_SH + CLIP_MARGIN)).difference(COLLAR_B.buffer(KEEP_COLLAR + CLIP_MARGIN))
CLIP = CLIP.intersection(box(-400, -100, 400, HEM - KEEP_HEM - CLIP_MARGIN)).buffer(0)

items = []
def add(regs, layer):
    for r in regs:
        if r["geom"] is not None and not r["geom"].is_empty:
            r = dict(r, col=fbcore.col(r["col"])); r["z"] = len(items); r["layer"] = layer; items.append(r)

# ---------------------------------------------------------------- 2 stream + licensed placeholder
STREAM_PX = [(200, 590), (240, 568), (300, 556), (360, 548), (395, 530), (420, 512), (470, 506), (530, 510),
             (560, 528), (556, 552), (520, 566), (500, 590), (510, 620), (500, 650), (460, 668), (400, 676), (330, 680),
             (260, 676), (210, 660), (190, 625)]
STREAM = Polygon([P(*p) for p in STREAM_PX]).buffer(4).buffer(-4)
DEEP = unary_union([Polygon([P(*p) for p in [(250, 612), (330, 600), (420, 610), (460, 625), (400, 645), (300, 648), (240, 635)]]),
                    Polygon([P(*p) for p in [(430, 548), (500, 552), (510, 562), (450, 566)]])]).buffer(3).buffer(-3)
PH_C = P(467, 533); PH_W, PH_H = 54.0, 48.0          # mockup orb ⌀ ≈ 44 px + margin (PROPOSED — confirm with licensor art)
PH_BOX, PH_OUT = FM.placeholder(*PH_C, PH_W, PH_H)
STREAM = STREAM.union(PH_BOX.buffer(9, join_style='round')).buffer(2).buffer(-2)    # water continues around the placeholder
add(FM.stream(STREAM, random.Random(7), deep=None, nrip=90, nglint=30), 2)

# ---------------------------------------------------------------- 3 grass behind the rocks (sewn with the front grass, layer 8)
for (x, y, h, n, lean) in [(330, 525, 52, 9, 8), (380, 512, 46, 7, -6), (470, 470, 50, 9, 6), (520, 462, 44, 8, -4),
                           (560, 455, 40, 7, 4), (425, 498, 40, 6, 0), (300, 480, 58, 10, 6), (350, 470, 50, 9, -4),
                           (440, 476, 46, 8, 8), (500, 455, 52, 9, -6)]:
    add(FM.grass_tuft(*P(x, y), h, n, random.Random(x * 3 + y), lean=lean)[0], 8)

# ---------------------------------------------------------------- 4 mossy bank: overlapping rounded mounds (Rev B: no floating slabs)
ROCKS = [(330, 505, 175, 85, 8), (400, 512, 110, 70, 10), (290, 560, 140, 80, 1), (385, 588, 125, 70, 3), (525, 585, 125, 95, 2),
         (470, 615, 95, 60, 4), (205, 668, 170, 90, 5), (335, 690, 150, 60, 6), (462, 690, 125, 60, 7), (548, 655, 95, 80, 9)]
rock_polys = []
for (x, y, w, h, sd) in ROCKS:
    rp = FM.blob(*P(x, y), w, h, random.Random(sd * 13), k=11, rough=0.16)
    rr_, rg_ = FM.mossy_rock(rp, random.Random(sd * 7)); add([dict(r) for r in rr_], 2); rock_polys.append(rg_)
for r in items:                          # rock moss sews with the limb moss (one moss pass, fewer colour revisits)
    if r["grp"].startswith("RM"): r["layer"] = 6
ROCKS_U = unary_union(rock_polys)
# water ring around the licensed placeholder sits above the mounds, so the stream visibly continues round the box
RING = PH_BOX.buffer(9, join_style="round").difference(PH_BOX).intersection(STREAM.buffer(30))
add(FM.stream(PH_BOX.buffer(9, join_style="round"), random.Random(17), deep=None, nrip=6, nglint=3), 2)

# ---------------------------------------------------------------- 5/6 bark + moss: main limb, right trunk, upper limbs
limbs = []
def limb(pts_r, grp="TR", moss=(0.0, 1.0), cover=0.72, seed=0, gap_p=0.06, size=1.3):
    rr = [(*P(x, y), r * S) for x, y, r in pts_r]
    regs, mr, poly, Sm, mg = FM.mossy_limb(rr, random.Random(seed or 50 + len(limbs)), grp=grp, moss=moss, cover=cover, gap_p=gap_p, size=size)
    add(regs, 5); add(mr, 6); limbs.append((poly, Sm))
    return Sm

limb([(150, 245, 9), (160, 220, 7.5), (170, 198, 6), (180, 178, 4.5), (190, 160, 3.2)], grp="LM", seed=13, cover=0.85)
limb([(300, 357, 7), (322, 335, 6), (348, 316, 5), (378, 300, 4.2), (410, 290, 3.4)], grp="LM", seed=14, cover=0.8)
limb([(470, 460, 6.5), (500, 440, 5.5), (530, 420, 4.8), (560, 400, 4), (590, 385, 3.2)], grp="LM", seed=15, cover=0.8)
limb([(580, 476, 8), (548, 500, 7), (520, 512, 6), (490, 518, 4.5)], grp="LM", seed=16, cover=0.85)
# main limb + trunk last: they cover the bases of the side limbs (no outline rings at the joints)
MAIN = [(84, 205, 19), (110, 214, 20), (140, 238, 21), (170, 266, 21), (200, 292, 21), (235, 318, 21), (270, 340, 20),
        (305, 360, 20), (340, 382, 19), (372, 402, 19), (402, 424, 18), (430, 446, 18), (462, 460, 17), (500, 468, 16),
        (540, 474, 15), (578, 478, 15)]
limb(MAIN, seed=11, cover=0.7, size=1.5)     # Rev B: blue chain underside shows, as the mockup
TRUNK = [(515, 700, 34), (535, 640, 33), (560, 585, 31), (583, 530, 28), (597, 480, 25), (606, 430, 21), (610, 385, 17), (612, 345, 12)]
limb(TRUNK, seed=12, cover=0.8, size=1.6)
BARK = unary_union([l[0] for l in limbs])

# thin twigs (navy satin) carrying the leaf sprays
TWIGS = [  # px polyline
    [(410, 290), (450, 282), (490, 285), (530, 296), (570, 312), (604, 322)],
    [(590, 385), (610, 360), (622, 330)],
    [(190, 160), (198, 142), (212, 130)],
    [(200, 292), (186, 330), (176, 360), (165, 392)],
    [(235, 318), (232, 352), (226, 385), (215, 420), (205, 452)],
    [(340, 382), (330, 410), (318, 435), (300, 462)],
    [(430, 446), (440, 420), (452, 398)],
    [(500, 468), (512, 445)],
    [(612, 345), (600, 300), (585, 262), (566, 228), (545, 200), (522, 178)],
    [(566, 228), (590, 205), (612, 192)],
    [(545, 200), (520, 160), (500, 138)],
]
twig_lines = []
for tw in TWIGS:
    pts = [P(*p) for p in tw]
    regs, tp, Sm = FM.twig(pts, 1.6, 1.0); add(regs, 5); twig_lines.append(LineString(pts))
SUPPORT = unary_union([BARK] + [l.buffer(1.0) for l in twig_lines])

# ---------------------------------------------------------------- 7 leaf sprays (each grows from a twig/limb: base snapped to it — LESSONS A1)
SPRAYS = [  # px base guess, angle deg, length mm
    ((196, 150), -60, 36), ((168, 200), -150, 34), ((150, 225), -40, 38), ((178, 178), 160, 30),
    ((188, 325), 170, 34), ((180, 350), 120, 30), ((170, 385), 150, 32), ((228, 370), 160, 34),
    ((222, 400), 40, 36), ((212, 435), 150, 30), ((205, 452), 110, 34), ((326, 415), 20, 32), ((305, 455), 140, 30),
    ((320, 340), -80, 32), ((352, 318), -60, 30),
    ((430, 284), -100, 30), ((470, 283), -70, 34), ((505, 288), -110, 30), ((540, 300), -60, 32), ((560, 308), 70, 34),
    ((600, 322), -30, 30), ((450, 400), -80, 30), ((512, 445), -60, 30), ((540, 420), 60, 30), ((575, 395), -40, 30),
    ((585, 262), -20, 34), ((566, 228), 160, 32), ((590, 205), -50, 30), ((545, 200), 180, 30), ((505, 142), -140, 32),
    ((520, 160), -40, 30), ((610, 196), 10, 26), ((600, 300), 170, 32), ((620, 332), -80, 26), ((150, 300), 160, 34), ((128, 330), 120, 30), ((165, 300), 100, 30),
]
for i, ((bx, by), ang, L) in enumerate(SPRAYS):
    c = Point(P(bx, by)); a, _ = nearest_points(SUPPORT, c)
    regs, _ = FM.leaf_spray((a.x, a.y), ang, L * 1.2, random.Random(100 + i), leaf=10.5)
    add(regs, 7)
# sprays along every twig: alternate sides every ~20 mm (mockup density: ~30 sprays, 7-11 leaves each)
for ti, ln in enumerate(twig_lines):
    g = random.Random(400 + ti); side = 1; s_ = 10.0
    while s_ < ln.length - 6:
        p0 = ln.interpolate(s_); p1 = ln.interpolate(min(ln.length, s_ + 1.0))
        ta = math.degrees(math.atan2(p1.y - p0.y, p1.x - p0.x))
        add(FM.leaf_spray((p0.x, p0.y), ta + side * g.uniform(35, 60), g.uniform(28, 38), g, leaf=10.5)[0], 7)
        side = -side; s_ += g.uniform(17, 24)
    e = ln.interpolate(ln.length); e0 = ln.interpolate(ln.length - 2)
    add(FM.leaf_spray((e.x, e.y), math.degrees(math.atan2(e.y - e0.y, e.x - e0.x)), 26, g, leaf=12.0)[0], 7)

# ---------------------------------------------------------------- 8 grass in front
for (x, y, h, n, lean) in [(95, 695, 150, 18, 6), (115, 695, 135, 16, -4), (140, 690, 125, 15, 10), (165, 695, 115, 14, -8), (190, 690, 90, 11, -6),
                           (560, 695, 140, 16, 6), (590, 695, 130, 15, -4), (612, 690, 110, 12, 2),
                           (250, 695, 80, 9, -8), (300, 695, 70, 8, 6), (395, 698, 60, 8, -6), (440, 690, 60, 7, 8),
                           (500, 695, 95, 10, -10), (545, 695, 120, 12, 4), (580, 690, 130, 12, -6), (608, 690, 100, 10, 4),
                           (480, 700, 55, 7, 4), (110, 640, 70, 8, 0)]:
    add(FM.grass_tuft(*P(x, y), h, n, random.Random(x * 7 + y), lean=lean, spread=26)[0], 8)

# ---------------------------------------------------------------- 11 light rays: 6 broad sheer bands from the top right down to the lower left,
# sewn LAST over the art (overlay: they cross the limb and rocks as in the mockup, nothing is knocked out under them)
RAY_D = np.array([-0.56, 0.83])
RAYS = [((470, 92), 620, 16, 30), ((520, 96), 650, 20, 40), ((560, 100), 650, 18, 34), ((615, 140), 600, 30, 56),
        ((650, 200), 520, 20, 38), ((682, 262), 420, 16, 30)]
for i, (p0, L, w0, w1) in enumerate(RAYS):
    regs, _ = FM.light_ray(P(*p0), RAY_D, L, w0, w1, random.Random(30 + i), core=0.45 if i in (1, 3) else 0.3)
    add([dict(r, overlay=True) for r in regs], 11)

# ---------------------------------------------------------------- 0 placeholder outline (sewn first, removable)
VOID = PH_BOX.buffer(1.0)                # nothing is stitched inside the box; art keeps 1 mm clear of its outline
add([PH_OUT], 0)
PH_ITEM_Z = items[-1]["z"]

# ---------------------------------------------------------------- build
def build(clip=None, voids=None):
    clip = CLIP if clip is None else clip
    voids = VOID if voids is None else voids
    vis = []; above = voids
    for r in reversed(items):
        if r["grp"] == "PH": g = r["geom"]
        elif r.get("overlay"): g = r["geom"].intersection(clip).difference(voids)     # sheer run on top: knocks nothing out
        else:
            g = r["geom"].intersection(clip)
            v = g.difference(above); above = above.union(g)
            g = v
        vis.append(dict(r, geom=g))
    vis.reverse()
    vis = [v for v in vis if not v["geom"].is_empty and v["geom"].area > 0.02]
    return absorb_slivers(vis)

def absorb_slivers(vis):
    """(Drum Island back2.absorb_slivers) knockout slivers narrower than the stitch minimum go to the neighbour."""
    from shapely.strtree import STRtree
    geoms = [v["geom"] for v in vis]; tree = STRtree(geoms); give = {}
    for i, v in enumerate(vis):
        line = v["st"] in ("bean", "run")
        if v["grp"] == "PH": continue
        h = 0.3 if line else 0.4
        clean = v["geom"].buffer(-h).buffer(h).intersection(v["geom"])
        sl = v["geom"].difference(clean)
        if sl.is_empty or sl.area < 0.01: continue
        keep = clean
        for piece in FM.polys(sl):
            if piece.area < 0.004: continue
            best, bl = None, 0.0
            for j in tree.query(piece.buffer(0.05)):
                j = int(j)
                if j == i or vis[j]["grp"] == "PH": continue
                if vis[j]["st"] in ("bean", "run") and not line: continue
                L = piece.buffer(0.05).intersection(geoms[j]).area * (1.5 if j > i else 1.0)
                if L > bl: best, bl = j, L
            if best is None: keep = keep.union(piece)
            else: give.setdefault(best, []).append(piece)
        vis[i] = dict(v, geom=keep)
    for j, pcs in give.items():
        vis[j] = dict(vis[j], geom=unary_union([vis[j]["geom"]] + pcs))
    return [v for v in vis if not v["geom"].is_empty and v["geom"].area > 0.02]
