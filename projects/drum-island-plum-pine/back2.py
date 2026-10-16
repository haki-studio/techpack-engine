"""01 Back scene v2 — mockup-fidelity composition in GARMENT coordinates (mm):
x from CB (+ = wearer's right, which is viewer's right on a back view), y down from the CB collar seam.
Fitted to the Drum Island block (size M, drum.py). Mockup px -> garment mm: x = (px - 1295) * SX, y = (py - 205) * SY;
motif sizes (radii, blossom/fan/leaf sizes) scale by S so shapes stay round while the layout fits the boxier panel."""
import random, math, json
import numpy as np
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union, nearest_points
from shapely import affinity
from motifs import catmull, sweep, taper
import motifs2 as M

S, SX, SY = 0.80, 0.86, 0.779
def warp_x(px, py):
    # left cluster sits on/over the side seam in the mockup: compress it inward (side seams don't wrap)
    if px < 1065: px = 1065 - (1065 - px) * 0.62
    return px
def P(px, py): return ((warp_x(px, py) - 1295) * SX, (py - 205) * SY)
def PR(pts): return [(*P(x, y), r * S) for x, y, r in pts]
def PT(pts, r0, r1, power=1.0): return taper([P(x, y) for x, y in pts], r0 * S, r1 * S, power)

# ---------------------------------------------------------------- garment model (Drum Island block, size M)
import drum
BLK = drum.Block("M")
HEM = BLK.b_hem; RIB = BLK.rib
PANEL = BLK.back_panel()
ARM_R_LINE = BLK.back_arm_line(+1)
KEEP_SIDE = 15.0; KEEP_HEM = 10.0; WRAP_BACK = 3.0; WRAP_SLEEVE = 3.0
_arm = list(ARM_R_LINE.coords)
SLEEVE_R = Polygon(_arm + [(BLK.b_ua[0] + 120, BLK.b_ua[1]), (BLK.b_sp[0] + 160, BLK.b_sp[1] - 40), (BLK.b_sp[0], BLK.b_sp[1] - 40)]).buffer(0)

items = []
def add(regs, layer):
    for r in regs:
        if r["geom"] is not None and not r["geom"].is_empty:
            r = dict(r); r["z"] = len(items); r["layer"] = layer; items.append(r)

rng = random.Random(11)

# ---------------------------------------------------------------- 1 mist
for (x, y, L, rows) in [(972, 598, 110, 3), (1002, 652, 90, 2), (1478, 650, 115, 3), (1290, 695, 135, 2),
                        (1232, 806, 95, 3), (1470, 900, 70, 2), (1150, 470, 70, 2)]:
    regs, _ = M.mist(*P(x, y), L*S, rows, 3.6, random.Random(x + y))
    add(regs, 1)

# ---------------------------------------------------------------- 2 pine branches + red pine (behind)
def pine_branch(pts, r0, r1, seed, snow=True):
    regs, poly, Sm = M.limb_regions(PT(pts, r0, r1), random.Random(seed), grp="PB")
    add(regs, 2)
    if snow:
        sr, _ = M.snow_regions(Sm, 0.05, 0.85, random.Random(seed + 50), size=1.1, min_r=1.8, gap_p=0.3, grp="PB-SN")
        add(sr, 2)
pine_branch([(1586, 858), (1560, 836), (1528, 818), (1490, 808), (1452, 806)], 8, 4.5, 1)
RED = [(1388, 812, 44, -20), (1546, 800, 42, 16), (1497, 772, 52, 7), (1442, 776, 55, -6), (1474, 826, 40, 2)]
red_union = []
for hx, hy, R_, rot in RED:
    regs, fan = M.pine_fan(*P(hx, hy), R_*S, "red", rot)
    add(regs, 3); red_union.append(fan)

# ---------------------------------------------------------------- 3 white pine
pine_branch([(1252, 940), (1300, 924), (1352, 910), (1410, 912), (1466, 928), (1515, 942)], 7, 3.5, 3)
WHITE = [(1296, 912, 42, -16), (1480, 918, 42, 16), (1420, 896, 50, 6), (1356, 882, 55, -5), (1392, 936, 34, 0)]
white_union = []
for hx, hy, R_, rot in WHITE:
    regs, fan = M.pine_fan(*P(hx, hy), R_*S, "white", rot)
    add(regs, 4); white_union.append(fan)
PINES = unary_union(red_union + white_union)

# ---------------------------------------------------------------- 4 plum tree
limb_list = []
def gnarl(rr, amp, seed, rad_noise=0.12, sub=2):
    """densify + crooked: perpendicular zig-zag offsets and radius bulges (plum wood grows in kinks)."""
    g = random.Random(seed)
    out = []
    for i in range(len(rr) - 1):
        (x0, y0, r0_), (x1, y1, r1_) = rr[i], rr[i+1]
        for k in range(sub):
            tt = k / sub
            out.append((x0 + (x1-x0)*tt, y0 + (y1-y0)*tt, r0_ + (r1_-r0_)*tt))
    out.append(rr[-1])
    res = [out[0]]
    for i in range(1, len(out) - 1):
        x, y, r = out[i]
        dx, dy = out[i+1][0] - out[i-1][0], out[i+1][1] - out[i-1][1]
        L = math.hypot(dx, dy) or 1
        nx, ny = -dy/L, dx/L
        o = g.uniform(-1, 1) * amp * (0.5 + r/12)
        res.append((x + nx*o, y + ny*o, r * (1 + g.uniform(-rad_noise, rad_noise))))
    res.append(out[-1])
    return res

def limb(pts_r=None, pts=None, r0=None, r1=None, snow=None, power=1.0, seed=0):
    rr = PR(pts_r) if pts_r is not None else PT(pts, r0, r1, power)
    k = len(limb_list)
    rr = gnarl(rr, 3.4 if k == 0 else (3.0 if k < 3 else 3.2), 900 + k, rad_noise=0.18 if k < 3 else 0.10, sub=3 if k < 3 else 2)
    regs, poly, Sm = M.limb_regions(rr, random.Random(seed or len(limb_list) + 3), grp="TR" if len(limb_list) < 3 else "LM")
    add(regs, 5); limb_list.append((poly, Sm, snow))
    return Sm

TRUNK = [(1033, 950, 42), (1050, 900, 40), (1082, 852, 35), (1127, 806, 32), (1177, 769, 29), (1232, 736, 27),
         (1287, 706, 25), (1337, 673, 22), (1382, 636, 19), (1416, 592, 16), (1436, 546, 14), (1443, 500, 13),
         (1451, 456, 12), (1469, 416, 10.5), (1493, 376, 9), (1516, 336, 7), (1538, 302, 5.5), (1555, 282, 4), (1568, 268, 2.4)]
limb(TRUNK, snow=(0.02, 0.82, 3.2))
limb([(1058, 902, 24), (1022, 862, 18), (996, 822, 14), (980, 786, 11), (972, 750, 8), (975, 705, 6), (983, 665, 4), (993, 632, 2.6)],
     snow=(0.0, 0.66, 2.6))
limb([(1052, 918, 18), (1016, 908, 13), (988, 914, 8), (972, 928, 5)], snow=(0.0, 0.92, 2.6))
limb(pts=[(1160, 778), (1146, 722), (1133, 671), (1123, 620), (1116, 571), (1111, 526), (1108, 492)], r0=13, r1=2.2, snow=(0.0, 0.8, 2.2))
limb(pts=[(1255, 714), (1258, 660), (1258, 610), (1255, 560), (1250, 515), (1242, 470), (1233, 430), (1228, 405)], r0=12, r1=2.0, snow=(0.0, 0.72, 2.2))
limb(pts=[(1449, 472), (1421, 446), (1396, 421), (1371, 403), (1346, 393), (1316, 388), (1290, 386)], r0=8, r1=2.0, snow=(0.0, 0.8, 2.2))
limb(pts=[(1400, 425), (1398, 390), (1395, 355), (1392, 322)], r0=3.5, r1=2.0)
limb(pts=[(1437, 541), (1470, 531), (1500, 516), (1525, 504), (1550, 500), (1566, 505)], r0=7, r1=2.0, snow=(0.0, 0.65, 1.4))
limb(pts=[(1420, 586), (1455, 598), (1490, 610), (1520, 620), (1548, 630), (1570, 640)], r0=8, r1=2.0, snow=(0.0, 0.62, 1.4))
limb(pts=[(1396, 629), (1426, 656), (1461, 690), (1496, 720), (1526, 748), (1556, 772), (1580, 788)], r0=8, r1=2.0, snow=(0.0, 0.8, 2.2))
limb(pts=[(1300, 706), (1330, 731), (1356, 752), (1381, 770)], r0=6, r1=2.0, snow=(0.0, 0.6, 1.3))
limb(pts=[(1492, 376), (1520, 393), (1548, 411), (1575, 428), (1600, 442), (1622, 452)], r0=6, r1=2.0, snow=(0.0, 0.62, 1.4))
limb(pts=[(1516, 336), (1540, 346), (1565, 361), (1590, 380), (1610, 396)], r0=5, r1=2.0, snow=(0.0, 0.6, 1.3))
limb(pts=[(1538, 302), (1520, 286), (1500, 276), (1484, 272)], r0=4, r1=2.0)
limb(pts=[(1555, 282), (1580, 290), (1602, 310), (1615, 335)], r0=3.5, r1=2.0)
TW = [
    ([(1133, 671), (1100, 660), (1076, 651), (1058, 640)], 3.2, 1.8), ([(1123, 620), (1146, 600), (1162, 584)], 3, 1.8),
    ([(1116, 571), (1091, 561), (1068, 566)], 2.8, 1.8), ([(1258, 610), (1285, 586), (1305, 561), (1312, 531), (1315, 500)], 3.4, 1.8),
    ([(1255, 560), (1229, 531), (1206, 513), (1188, 505)], 3, 1.8), ([(1305, 561), (1331, 541)], 2.4, 1.8),
    ([(1461, 690), (1471, 726), (1481, 760)], 3.2, 1.8), ([(1526, 748), (1546, 731), (1561, 716)], 2.6, 1.8),
    ([(1470, 531), (1492, 556), (1512, 572)], 2.8, 1.8), ([(980, 786), (962, 762)], 3, 1.8),
    ([(975, 705), (996, 690), (1014, 690)], 2.8, 1.8), ([(1356, 752), (1352, 780), (1350, 800)], 2.4, 1.8),
    ([(1548, 411), (1562, 440), (1570, 460)], 2.6, 1.8), ([(1371, 403), (1352, 372), (1340, 350)], 2.6, 1.8),
    ([(1250, 515), (1270, 492), (1282, 470)], 2.6, 1.8), ([(1111, 526), (1128, 500), (1140, 485)], 2.4, 1.8),
    ([(1490, 610), (1505, 645), (1512, 670)], 2.6, 1.8), ([(1420, 586), (1395, 560), (1385, 540)], 3, 1.8),
]
for pts, r0, r1 in TW: limb(pts=pts, r0=r0, r1=r1)
for kx, ky, rx, ry, rot in [(1062, 905, 4.0, 2.4, 30), (1150, 790, 3.2, 1.9, -35), (1330, 683, 2.6, 1.6, -30), (1420, 600, 2.2, 1.4, -60)]:
    add(M.knot(*P(kx, ky), rx, ry, rot), 5)
# secondary sprays: short crooked twigs off every limb, ending in bud clusters
SPRAYS = []
_primary = list(limb_list)
for li, (poly, Sm, sn) in enumerate(_primary):
    if li < 1: continue
    g = random.Random(500 + li)
    acc = 0.0; side = 1; every = g.uniform(11, 17)
    for k in range(1, len(Sm) - 2):
        acc += math.hypot(Sm[k+1][0]-Sm[k][0], Sm[k+1][1]-Sm[k][1])
        x, y, r = Sm[k]
        if acc < every or r > 9 or k < len(Sm)*0.15: continue
        acc = 0.0; every = g.uniform(11, 17)
        tx, ty = Sm[k+1][0]-Sm[k-1][0], Sm[k+1][1]-Sm[k-1][1]; L = math.hypot(tx, ty) or 1; tx, ty = tx/L, ty/L
        a = math.atan2(ty, tx) + side*math.radians(g.uniform(35, 65)); side = -side
        ln = g.uniform(12, 30)
        p0 = (x + math.cos(a)*r*0.6, y + math.sin(a)*r*0.6)
        pts = [p0]
        for j in range(1, 4):
            aa = a + g.uniform(-0.35, 0.35)
            pts.append((pts[-1][0] + math.cos(aa)*ln/3, pts[-1][1] + math.sin(aa)*ln/3))
        if any(Point(p).buffer(3).intersects(PINES) for p in pts): continue
        regs, tp, tS = M.limb_regions(taper(pts, 1.25, 0.95), g, grp="TW")
        add(regs, 5); limb_list.append((tp, tS, (0.0, 0.75, 1.15) if g.random() < 0.7 else None)); SPRAYS.append(tS)
for li in range(3):
    poly, Sm, _ = limb_list[li]; gk = random.Random(77 + li); acc = 0.0
    from motifs import normals as _nm
    Nk = _nm(Sm)
    for k in range(2, len(Sm) - 2):
        acc += math.hypot(Sm[k+1][0]-Sm[k][0], Sm[k+1][1]-Sm[k][1]); x, y, r = Sm[k]
        if acc > gk.uniform(26, 40) and r > 7:
            acc = 0.0
            off = gk.uniform(-0.55, -0.1)
            cx, cy = x + Nk[k][0]*r*off, y + Nk[k][1]*r*off
            ang = math.degrees(math.atan2(Sm[k+1][1]-Sm[k-1][1], Sm[k+1][0]-Sm[k-1][0]))
            add(M.knot(cx, cy, min(5.0, r*0.32), min(2.6, r*0.16), ang), 5)
BARK = unary_union([l[0] for l in limb_list])

# snow on limbs
snow_union = []
for i, (poly, Sm, sn) in enumerate(limb_list):
    if sn:
        t0, t1, size = sn
        tw = Sm[0][2] < 2.0
        regs, g = M.snow_regions(Sm, t0, t1, random.Random(200 + i), size=size, min_r=1.4 if tw else (2.2 if i < 3 else 2.4),
                                 gap_p=0.45 if tw else (0.18 if i < 3 else 0.28), grp="SN")
        add(regs, 6); snow_union.append(g)
SNOW = unary_union(snow_union)

# leaves — every cluster grows FROM the bark: hub snapped onto the nearest limb surface,
# fan centred on the direction away from the limb (drooping 20° with gravity), short petiole.
LEAF_PTS = [(1208, 752, 46, 5), (1140, 655, 38, 4), (1398, 426, 34, 3), (1008, 826, 38, 4),
            (1012, 716, 28, 3), (1352, 372, 26, 2)]
LEAF_BASES = []
for (x, y, L, n) in LEAF_PTS:
    c = Point(P(x, y))
    near, _ = nearest_points(BARK, c)
    if near.distance(c) > 30: continue                      # nothing to grow from: drop
    # outward direction = from limb centre-ish toward the cluster position
    inside = BARK.buffer(-1.5)
    v = np.array([c.x - near.x, c.y - near.y])
    if np.linalg.norm(v) < 1e-6:
        q, _ = nearest_points(BARK.boundary, c); v = np.array([c.x - q.x, c.y - q.y])
    v = v / (np.linalg.norm(v) or 1)
    out = math.degrees(math.atan2(v[1], v[0]))
    # gravity: pull the fan centre 20° toward straight down (90°)
    dd = ((90 - out + 180) % 360) - 180
    centre = out + max(-20, min(20, dd))
    spread = 26 if n > 3 else 30
    angs = [centre + spread*(i - (n - 1)/2) for i in range(n)]
    base = (near.x + v[0]*0.5, near.y + v[1]*0.5)
    hub = (base[0] + math.cos(math.radians(centre))*4.0, base[1] + math.sin(math.radians(centre))*4.0)
    stem, _, _ = M.limb_regions(taper([base, hub], 1.0, 0.9), random.Random(int(x)), grp="TW")
    add(stem, 7)
    regs, _ = M.leaf_cluster(*hub, L*S, angs, random.Random(x*3 + y))
    add(regs, 7); LEAF_BASES.append((base, hub, centre))

# ---------------------------------------------------------------- blossoms + buds from the mockup's own positions
BLOBS = json.load(open("blobs_back.json"))
occupied = [PINES.buffer(1.0)]
placed = []
def free(c, r):
    disc = Point(c).buffer(r)
    return not any(disc.intersects(o) for o in occupied[1:]) and not disc.intersects(occupied[0])
for (bx, by, bd) in sorted(BLOBS, key=lambda b: -b[2]):
    c = P(bx, by)
    if bd >= 19:     d = min(56, max(36, bd * 1.45)) * S; kind = "L"
    elif bd >= 12.0: d = max(26, bd * 1.8) * S; kind = "S"
    else:            d = max(6.4, bd * 0.98 * S); kind = "B"
    if not free(c, d/2 + 0.6): continue
    placed.append((c, d, kind)); occupied.append(Point(c).buffer(d/2 + 0.8))

# twigs to anything not touching a limb
for c, d, kind in placed:
    pt = Point(c)
    dist = BARK.distance(pt) - d/2
    if dist > 1.2:
        a, _ = nearest_points(BARK, pt)
        if dist < 18:
            v = np.array(c) - np.array([a.x, a.y]); L = np.linalg.norm(v); u = v / L
            mid = np.array([a.x, a.y]) + v*0.5 + np.array([-u[1], u[0]]) * L * 0.12
            end = np.array(c) - u * d * 0.3
            regs, poly, Sm = M.limb_regions(taper([(a.x, a.y), tuple(mid), tuple(end)], 1.1, 0.9), random.Random(int(c[0])), grp="TW")
            add(regs, 5)

placed = [(c, d, k) for c, d, k in placed if BARK.distance(Point(c)) - d/2 < 18 or k == "L"]
# nothing may straddle the sleeve-wrap gap at the right armhole
GAPBAND = ARM_R_LINE.buffer(WRAP_BACK + 1.0).union(ARM_R_LINE.buffer(WRAP_SLEEVE + 1.0))
fixed = []
for c, d, k in placed:
    disc = Point(c).buffer(d/2)
    if disc.intersects(GAPBAND):
        p, _ = nearest_points(ARM_R_LINE, Point(c))
        side = 1 if SLEEVE_R.contains(Point(c)) else -1
        v = np.array(c) - np.array([p.x, p.y]); n = np.linalg.norm(v) or 1; v = v / n
        if side == -1 and np.dot(v, [1, 0]) > 0: v = -v
        need = (WRAP_BACK if side == -1 else WRAP_SLEEVE) + d/2 + 1.5
        c = tuple(np.array([p.x, p.y]) + v * need)
    fixed.append((c, d, k))
placed = fixed
from motifs import normals as _normals
extra = []
for li, (poly, Sm, sn) in enumerate(limb_list):
    if li < 3: continue
    N = _normals(Sm); acc = 0.0; side = 1; rr_ = random.Random(li * 7)
    every = rr_.uniform(6.5, 9.0)
    for k in range(len(Sm) - 1):
        acc += math.hypot(Sm[k+1][0]-Sm[k][0], Sm[k+1][1]-Sm[k][1])
        x, y, r = Sm[k]
        if acc > every and r < 5.0 and k > len(Sm) * 0.25:
            d = rr_.uniform(6.2, 7.6)
            c = (x + N[k][0]*side*(r + d*0.42), y + N[k][1]*side*(r + d*0.42))
            extra.append((c, d, "B")); side = -side; acc = 0.0; every = rr_.uniform(6.5, 9.0)
    x, y, r = Sm[-1]                        # tip
    tdir = np.array(Sm[-1][:2]) - np.array(Sm[-3][:2]); tdir = tdir / (np.linalg.norm(tdir) or 1)
    if rr_.random() < 0.35:
        extra.append((tuple(np.array([x, y]) + tdir*9.0), rr_.uniform(17, 21), "S"))
    else:
        extra.append((tuple(np.array([x, y]) + tdir*3.2), 7.2, "B"))
for c, d, k in extra:
    disc = Point(c).buffer(d/2 + 0.7)
    if disc.intersects(PINES) or disc.intersects(SNOW.buffer(0.3)) or disc.intersects(GAPBAND): continue
    if any(Point(c).distance(Point(pc)) < (d + pd)/2 + 0.8 for pc, pd, _ in placed): continue
    placed.append((c, d, k))
for i, (c, d, kind) in enumerate(placed):
    rot = random.Random(i).uniform(-20, 20)
    if kind in ("L", "S"):
        regs, _ = M.blossom(*c, d, rot); add(regs, 8)
    else:
        a, _ = nearest_points(BARK, Point(c))
        ang = math.degrees(math.atan2(a.y - c[1], a.x - c[0]))
        regs, _ = M.bud(*c, d, ang); add(regs, 9)

# ---------------------------------------------------------------- bamboo (front, bottom-left)
# Dwarf bamboo (sasa) growing out of a snow drift at the trunk base, as in the mockup:
# ground drift -> culm stems rising from it -> drooping blade clusters at the stem tops.
GROUND_Y = HEM - KEEP_HEM - 1.5
BAMBOO = [(1080, 876, 80, [64, 86, 108, 130, 152, 172]), (1204, 884, 74, [8, 30, 52, 76, 100, 122]),
          (1036, 900, 52, [78, 104, 130, 156]), (1156, 906, 50, [28, 54, 150])]
xs = [P(x, y)[0] for x, y, _, _ in BAMBOO]
gx0, gx1 = min(xs) - 40, max(xs) + 30
gpath = taper([(gx0 + (gx1 - gx0)*k/24, GROUND_Y + 2.0*math.sin(k*1.3)) for k in range(25)], 3.2, 3.2)
_, gS = sweep(gpath)
regs, ground = M.snow_regions(gS, 0.0, 1.0, random.Random(55), size=3.4, min_r=3.0, gap_p=0.0, grp="SN")
add([r for r in regs if r["grp"] != "SN-shadow"], 10)          # drift sits on fabric: no cast shadow on bark
for i, (x, y, L, angs) in enumerate(BAMBOO):
    hx, hy = P(x, y)
    g = random.Random(60 + i)
    root = (hx + g.uniform(-4, 4), GROUND_Y - 1.0)
    mid = ((root[0] + hx)/2 + g.uniform(-2, 2), (root[1] + hy)/2)
    culm = LineString([root, mid, (hx, hy)]).buffer(1.1, cap_style="round")
    nodes = unary_union([LineString([(mid[0] - 1.6, mid[1]), (mid[0] + 1.6, mid[1])]).buffer(0.35)])
    add([M.R("indigo", culm, "satin", "auto", "BB-shade"), M.R("lavender", nodes.intersection(culm), "satin", 0, "BB-light"),
         M.R("barkdk", culm.boundary.buffer(0.35), "bean", None, "BB-outline")], 10)
    regs, _ = M.bamboo_cluster(hx, hy, L*S, angs, random.Random(x + 7))
    add(regs, 10)

# ---------------------------------------------------------------- pieces
SLEEVE_GAP_BACK = ARM_R_LINE.buffer(WRAP_BACK)
inner = PANEL.buffer(-KEEP_SIDE, join_style="mitre")
inner = inner.union(affinity.translate(inner, 0, KEEP_SIDE - KEEP_HEM).intersection(box(-400, 0, 400, HEM - KEEP_HEM)))
# right armhole: back side may run to WRAP_BACK from the seam (wrap), not KEEP_SIDE
arm_zone = PANEL.intersection(box(150, 0, 400, 334)).difference(SLEEVE_GAP_BACK)
BACK_CLIP = inner.union(arm_zone.intersection(box(0, 0, 400, 334))).intersection(PANEL).difference(SLEEVE_GAP_BACK)
BACK_CLIP = BACK_CLIP.intersection(box(-400, -100, 400, HEM - KEEP_HEM))
SLEEVE_CLIP = SLEEVE_R.difference(ARM_R_LINE.buffer(WRAP_SLEEVE))

def build(clip):
    vis = []; above = Polygon()
    for r in reversed(items):
        g = r["geom"].intersection(clip)
        v = g.difference(above); above = above.union(g)
        rr = dict(r); rr["geom"] = v; vis.append(rr)
    vis.reverse()
    vis = [v for v in vis if not v["geom"].is_empty and v["geom"].area > 0.02]
    return absorb_slivers(vis)

def absorb_slivers(vis):
    """Knockout leaves slivers narrower than the stitch minimum. Each sliver is handed to the neighbouring
    region it touches most (preferring the one above it), so no object is left with an unstitchable strip."""
    from shapely.strtree import STRtree
    geoms = [v["geom"] for v in vis]
    tree = STRtree(geoms)
    give = {}
    for i, v in enumerate(vis):
        line = v["st"] in ("bean", "run")
        h = 0.3 if line else 0.4
        clean = v["geom"].buffer(-h).buffer(h).intersection(v["geom"])
        sl = v["geom"].difference(clean)
        if sl.is_empty or sl.area < 0.01: continue
        keep = clean
        for piece in ([sl] if sl.geom_type == "Polygon" else [p for p in getattr(sl, "geoms", []) if p.geom_type == "Polygon"]):
            if piece.area < 0.004: continue
            best, bl = None, 0.0
            for j in tree.query(piece.buffer(0.05)):
                j = int(j)
                if j == i: continue
                if vis[j]["st"] in ("bean", "run") and not line: continue
                L = piece.buffer(0.05).intersection(geoms[j]).area
                L *= 1.5 if j > i else 1.0
                if L > bl: best, bl = j, L
            if best is None: keep = keep.union(piece)           # nothing to give it to: keep (rare)
            else: give.setdefault(best, []).append(piece)
        vis[i] = dict(v, geom=keep)
    for j, pcs in give.items():
        vis[j] = dict(vis[j], geom=unary_union([vis[j]["geom"]] + pcs))
    return [v for v in vis if not v["geom"].is_empty and v["geom"].area > 0.02]
