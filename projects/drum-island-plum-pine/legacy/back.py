"""01 Back scene — composition. Traced layout from the mockup (px), built in mm.
Option A (full back) = 0.75 mm per mockup px."""
import random, math, os
import numpy as np
from shapely.geometry import Point, Polygon, LineString
from shapely.ops import unary_union
from shapely import affinity
from motifs import *

S = float(os.environ.get('BACK_S', 0.75))
OX, OY = 965, 262
W_A = round((1600 - OX) * S, 1)
H_A = round((945 - OY) * S, 1)

def P(x, y): return ((x - OX) * S, (y - OY) * S)
def PR(pts): return [(*P(x, y), r * S) for x, y, r in pts]
def PT(pts, r0, r1, power=1.0): return taper([P(x, y) for x, y in pts], r0 * S, r1 * S, power)

items = []       # (z, colour, geometry, role)
def add(col, g, role):
    if g is not None and not g.is_empty: items.append((len(items), col, g, role))

rng = random.Random(7)

# ------------------------------------------------------------ 1 mist (furthest back)
for (x, y, L, rows) in [(972, 598, 100, 3), (1002, 650, 80, 2), (1488, 652, 105, 3), (1290, 695, 125, 2),
                        (1238, 805, 85, 2), (1532, 908, 55, 2)]:
    add("shadow", mist(*P(x, y), L * S, rows, 3.4, random.Random(x)), "mist")

# ------------------------------------------------------------ 2 red pine (behind white pine)
def pine_branch(pts, r0, r1, seed):
    poly, Sm = sweep(PT(pts, r0, r1))
    add("bark", poly, "pine branch"); add("barkdk", poly.exterior.buffer(OUTLINE/2), "pine branch outline")
    return poly
pine_branch([(1598, 846), (1572, 826), (1540, 812), (1505, 806)], 6.5, 4, 1)
red, red_occ = canopy([(*P(1405, 815), 44*S, -20), (*P(1566, 804), 44*S, 18), (*P(1512, 776), 52*S, 7),
                       (*P(1458, 780), 54*S, -6), (*P(1488, 828), 40*S, 2)], "red")
add("vermilion", red["vermilion_body"], "red pine fan"); add("gold", red["needle"], "red pine needles")
add("orange", red["hub"], "pine hub"); add("snow", red["snow"], "pine snow"); add("barkdk", red["outline"], "pine outline")

# ------------------------------------------------------------ 3 white pine

wp, wp_occ = canopy([(*P(1300, 915), 42*S, -16), (*P(1478, 920), 42*S, 16), (*P(1420, 898), 50*S, 6),
                     (*P(1358, 884), 54*S, -5), (*P(1395, 935), 34*S, 0)], "white")
add("snow", wp["snow_body"], "white pine fan"); add("gold", wp["gold_inner"], "white pine inner")
add("barkdk", wp["needle"], "white pine needles"); add("orange", wp["hub"], "pine hub")
add("snow", wp["snow"], "pine snow"); add("shadow", wp["outline"], "white pine outline")

# ------------------------------------------------------------ 4 plum tree
limbs = []   # (poly, samples, snow t0, t1, snow size)
def limb(pts_r=None, pts=None, r0=None, r1=None, snow=None, power=1.0):
    if pts_r is not None: poly, Sm = sweep(PR(pts_r))
    else: poly, Sm = sweep(PT(pts, r0, r1, power))
    limbs.append((poly, Sm, snow))
    return Sm

TRUNK = [(1035, 948, 40), (1050, 900, 38), (1082, 852, 34), (1127, 806, 31), (1177, 769, 28), (1232, 736, 26),
         (1287, 706, 24), (1337, 673, 21), (1382, 636, 18), (1416, 592, 15), (1436, 546, 13), (1443, 500, 12),
         (1451, 456, 11), (1469, 416, 10), (1493, 376, 8), (1516, 336, 6.5), (1538, 302, 5), (1555, 282, 3.5), (1566, 270, 2)]
limb(TRUNK, snow=(0.03, 0.74, 1.35))
limb([(1056, 902, 22), (1024, 862, 17), (1001, 822, 13), (988, 786, 10), (983, 750, 7), (986, 705, 5), (993, 665, 3.5), (1003, 632, 2.4)],
     snow=(0.0, 0.5, 1.1))
limb([(1050, 916, 16), (1018, 906, 11), (992, 912, 7), (980, 925, 4)], snow=(0.0, 0.85, 1.2))
B1 = limb(pts=[(1160, 778), (1146, 722), (1133, 671), (1123, 620), (1116, 571), (1111, 526), (1108, 492)], r0=12, r1=2, snow=(0.0, 0.6, 0.75))
B2 = limb(pts=[(1255, 714), (1258, 660), (1258, 610), (1255, 560), (1250, 515), (1242, 470), (1233, 430), (1228, 405)], r0=11, r1=1.6, snow=(0.0, 0.5, 0.75))
B3 = limb(pts=[(1449, 472), (1421, 446), (1396, 421), (1371, 403), (1346, 393), (1316, 388), (1290, 386)], r0=7, r1=1.6, snow=(0.0, 0.6, 0.75))
limb(pts=[(1400, 425), (1398, 390), (1395, 355), (1392, 322)], r0=3, r1=1.6)
B4 = limb(pts=[(1437, 541), (1470, 531), (1500, 516), (1525, 504), (1550, 500), (1566, 505)], r0=6, r1=1.5, snow=(0.0, 0.5, 0.7))
B5 = limb(pts=[(1420, 586), (1455, 598), (1490, 610), (1520, 620), (1548, 630), (1570, 640)], r0=7, r1=1.6, snow=(0.0, 0.45, 0.7))
B6 = limb(pts=[(1396, 629), (1426, 656), (1461, 690), (1496, 720), (1526, 748), (1556, 772), (1582, 790)], r0=7, r1=1.5, snow=(0.0, 0.6, 0.75))
limb(pts=[(1300, 706), (1330, 731), (1356, 752), (1381, 770)], r0=5, r1=1.6)
B8a = limb(pts=[(1492, 376), (1520, 393), (1548, 411), (1575, 428), (1594, 440)], r0=5, r1=1.5, snow=(0.0, 0.5, 0.7))
B8b = limb(pts=[(1516, 336), (1540, 346), (1565, 361), (1586, 380)], r0=4, r1=1.5)
B8c = limb(pts=[(1538, 302), (1520, 286), (1500, 276)], r0=3, r1=1.5)
TW = [
    ([(1133, 671), (1100, 660), (1076, 651), (1060, 641)], 3, 1.5),
    ([(1123, 620), (1146, 600), (1161, 585)], 2.8, 1.5),
    ([(1116, 571), (1091, 561), (1069, 568)], 2.6, 1.5),
    ([(1258, 610), (1285, 586), (1305, 561), (1312, 531), (1315, 500)], 3.2, 1.5),
    ([(1255, 560), (1229, 531), (1206, 513), (1189, 506)], 2.8, 1.5),
    ([(1305, 561), (1331, 541)], 2.0, 1.5),
    ([(1461, 690), (1471, 726), (1481, 760)], 3, 1.5),
    ([(1526, 748), (1546, 731), (1561, 716)], 2.2, 1.5),
    ([(1470, 531), (1492, 556), (1512, 572)], 2.6, 1.5),
    ([(988, 786), (972, 762)], 3, 1.5),
    ([(986, 705), (1004, 690), (1020, 690)], 2.6, 1.5),
]
for pts, r0, r1 in TW: limb(pts=pts, r0=r0, r1=r1)

def buds_along(Sm, every=11.0, start=0.35, rng=None):
    rng = rng or random.Random(0); out = []
    N = normals(Sm); acc = 0.0; side = 1
    L = sum(np.hypot(Sm[k+1][0]-Sm[k][0], Sm[k+1][1]-Sm[k][1]) for k in range(len(Sm)-1))
    for k in range(len(Sm)-1):
        acc += np.hypot(Sm[k+1][0]-Sm[k][0], Sm[k+1][1]-Sm[k][1])
        if acc > every and k/len(Sm) > start and Sm[k][2] < 3.2:
            x, y, r = Sm[k]; d = rng.uniform(5.6, 7.0)
            nx, ny = N[k] * side
            out.append((x + nx*(r + d*0.35), y + ny*(r + d*0.35), d, math.degrees(math.atan2(-ny, -nx))))
            side = -side; acc = 0.0
    return out
AUTO_BUDS = []
for i, (poly, Sm, sn) in enumerate(limbs[3:]):
    AUTO_BUDS += buds_along(Sm, every=rng.uniform(9, 13), rng=random.Random(i))

bark_poly = unary_union([l[0] for l in limbs])
add("bark", bark_poly, "plum bark")
tex = unary_union([bark_lines(Sm, poly, random.Random(i)) for i, (poly, Sm, _) in enumerate(limbs[:3])] +
                  [knot(*P(1062, 905), 3.2, 2.0, 30), knot(*P(1150, 790), 2.6, 1.6, -35), knot(*P(1330, 683), 2.2, 1.3, -30)])
add("barkdk", tex, "bark texture")
add("barkdk", bark_poly.boundary.buffer(OUTLINE/2), "bark outline")

snow_all = []
for i, (poly, Sm, sn) in enumerate(limbs):
    if sn:
        t0, t1, size = sn
        big = i < 3
        snow_all.append(snow_ridge(Sm, t0, t1, random.Random(100 + i), size=size if big else 1.15, lift=0.8,
                                   min_r=2.0 if big else 2.4, gap_p=0.12 if big else 0.35))
snow_g = unary_union(snow_all)
add("shadow", affinity.translate(snow_g, 0.7, 2.0).intersection(snow_g.buffer(1.8)).difference(snow_g), "snow shadow")
add("snow", snow_g, "snow")

# leaves
for (x, y, L, angs) in [(1208, 752, 40, [58, 84, 110, 136]), (1140, 655, 34, [130, 160, 192, 222]),
                        (1398, 426, 30, [104, 134, 164]), (998, 828, 34, [96, 124, 152, 180]),
                        (1192, 856, 32, [54, 82, 112]), (1010, 716, 24, [200, 234, 266])]:
    lc = leaf_cluster(*P(x, y), L*S, angs, rng=random.Random(x + y))
    add("leaf", lc["leaf"], "plum leaf"); add("leaflt", lc["leaflt"], "leaf vein")
    add("snow", lc["snow"], "leaf snow cap"); add("barkdk", lc["outline"], "leaf outline")

# blossoms
BL = [(1262, 700, 58, 5), (1236, 746, 46, -12), (1466, 418, 52, 8), (1046, 772, 40, 0), (1462, 585, 40, -6),
      (1518, 611, 40, 12), (1522, 503, 32, -8), (1003, 707, 32, 10), (1155, 552, 30, 0), (1160, 836, 30, -10),
      (1486, 348, 26, 0), (1534, 314, 24, 6), (1309, 591, 24, 0), (1578, 386, 22, 0), (1378, 640, 22, 4), (1110, 520, 22, -5),
      (1088, 662, 24, 10), (1213, 508, 22, -4), (1300, 528, 22, 6), (1553, 718, 24, -8), (1338, 398, 22, 0), (1015, 742, 26, 6), (1476, 742, 22, 4)]
for x, y, d, rot in BL:
    b = blossom(*P(x, y), d*S, rot)
    add("plum", b["plum"], "blossom petals"); add("petal", b["petal"], "blossom rims")
    add("plumdk", b["plumdk"], "blossom outline"); add("gold", b["gold"], "blossom stamens"); add("gold", b["goldline"], "stamen needles"); add("orange", b["orange"], "blossom eye")

# buds: twig tips + along twigs
BUDS = [(1060, 641), (1161, 585), (1069, 568), (1315, 500), (1189, 506), (1331, 541), (1481, 760), (1561, 716),
        (1512, 572), (972, 762), (1020, 690), (1108, 492), (1228, 405), (1290, 386), (1392, 322), (1566, 505), (1570, 640),
        (1582, 790), (1594, 440), (1586, 380), (1500, 276), (1566, 270), (1381, 770), (1003, 632),
        (1084, 672), (1310, 525), (1253, 468), (1342, 401), (1395, 383), (1549, 432), (1553, 384), (1503, 292),
        (1533, 551), (1550, 826), (1414, 650), (1353, 765), (1088, 556), (1012, 655), (1296, 552), (1530, 704)]
for i, (x, y) in enumerate(BUDS):
    d = (10 if i < 24 else 8) * S * random.Random(i).uniform(0.9, 1.1)
    bd = bud(*P(x, y), max(d, 5.6), ang=random.Random(i*3).uniform(60, 150))
    add("plum", bd["plum"], "bud"); add("plumdk", bd["plumdk"], "bud calyx"); add("petal", bd["petal"], "bud highlight")
for x, y, d, ang in AUTO_BUDS:
    bd = bud(x, y, d, ang)
    add("plum", bd["plum"], "bud"); add("plumdk", bd["plumdk"], "bud calyx"); add("petal", bd["petal"], "bud highlight")

# ------------------------------------------------------------ 5 bamboo (front, bottom left)
for (x, y, L, angs) in [(1078, 878, 70, [68, 92, 116, 140, 164]), (1200, 884, 66, [10, 34, 58, 84, 110]),
                        (1030, 905, 42, [96, 124, 150])]:
    bc = bamboo_cluster(*P(x, y), L*S, angs, rng=random.Random(x))
    add("indigo", bc["indigo"], "bamboo blade"); add("lavender", bc["lavender"], "bamboo highlight")
    add("snow", bc["snow"], "bamboo snow"); add("barkdk", bc["outline"], "bamboo outline")

# ------------------------------------------------------------ knockout + clip
def build(clip_box=None):
    """Return visible geometry per item (later items knock out earlier ones)."""
    vis = []
    above = Polygon()
    for z, col, g, role in reversed(items):
        if clip_box is not None: g = g.intersection(clip_box)
        v = g.difference(above)
        above = above.union(g)
        vis.append((z, col, v, role))
    vis.reverse()
    return vis

def bounds():
    u = unary_union([g for _, _, g, _ in items]); return u.bounds
