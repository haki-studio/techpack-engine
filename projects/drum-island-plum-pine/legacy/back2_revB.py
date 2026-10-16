"""01 Back scene v2 — mockup-fidelity composition in GARMENT coordinates (mm):
x from CB (+ = wearer's right, which is viewer's right on a back view), y down from the CB collar seam.
Mockup px -> garment mm: x = (px - 1295) * 0.87, y = (py - 205) * 0.87."""
import random, math, json
import numpy as np
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union, nearest_points
from shapely import affinity
from motifs import catmull, sweep, taper
import motifs2 as M

S = 0.87
def warp_x(px, py):
    # left cluster sits on/over the side seam in the mockup: compress it inward (side seams don't wrap)
    if px < 1065: px = 1065 - (1065 - px) * 0.62
    return px
def P(px, py): return ((warp_x(px, py) - 1295) * S, (py - 205) * S)
def PR(pts): return [(*P(x, y), r * S) for x, y, r in pts]
def PT(pts, r0, r1, power=1.0): return taper([P(x, y) for x, y in pts], r0 * S, r1 * S, power)

# ---------------------------------------------------------------- garment model (traced from the mockup)
HEM = 652.0; RIB = 40.0
R_ARM = [(200, 50), (226, 117), (244, 187), (257, 265), (265, 334)]
R_SIDE = [(265, 334), (272, 500), (277, HEM)]
NECK = [(-85, -14), (-40, -3), (0, 0), (40, -3), (85, -14)]
SHOULDER_R = [(85, -14), (200, 50)]
def mirror(pts): return [(-x, y) for x, y in pts]
def panel():
    right = SHOULDER_R + R_ARM[1:] + R_SIDE[1:]
    left = mirror(right)[::-1]
    return Polygon([p for p in NECK] + right[1:] + [(277, HEM), (-277, HEM)] + left[:-1])
PANEL = panel()
ARM_R_LINE = LineString(catmull(R_ARM, 10))
KEEP_SIDE = 15.0; KEEP_HEM = 10.0; WRAP_BACK = 3.0; WRAP_SLEEVE = 3.0
# sleeve region (right, beyond the armhole seam) for the wrap piece
SLEEVE_R = Polygon([(200, 50)] + [tuple(p) for p in catmull(R_ARM, 10)][1:] + [(265, 334), (380, 334), (380, 0), (230, 0)])

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
    rr = gnarl(rr, 1.6 if k == 0 else 2.6, 900 + k, rad_noise=0.10 if k == 0 else 0.08, sub=2 if k == 0 else 2)
    regs, poly, Sm = M.limb_regions(rr, random.Random(seed or len(limb_list) + 3), grp="TR" if len(limb_list) < 3 else "LM")
    add(regs, 5); limb_list.append((poly, Sm, snow))
    return Sm

TRUNK = [(1033, 950, 42), (1050, 900, 40), (1082, 852, 35), (1127, 806, 32), (1177, 769, 29), (1232, 736, 27),
         (1287, 706, 25), (1337, 673, 22), (1382, 636, 19), (1416, 592, 16), (1436, 546, 14), (1443, 500, 13),
         (1451, 456, 12), (1469, 416, 10.5), (1493, 376, 9), (1516, 336, 7), (1538, 302, 5.5), (1555, 282, 4), (1568, 268, 2.4)]
limb(TRUNK, snow=(0.02, 0.8, 2.5))
limb([(1058, 902, 24), (1022, 862, 18), (996, 822, 14), (980, 786, 11), (972, 750, 8), (975, 705, 6), (983, 665, 4), (993, 632, 2.6)],
     snow=(0.0, 0.62, 2.0))
limb([(1052, 918, 18), (1016, 908, 13), (988, 914, 8), (972, 928, 5)], snow=(0.0, 0.9, 2.0))
limb(pts=[(1160, 778), (1146, 722), (1133, 671), (1123, 620), (1116, 571), (1111, 526), (1108, 492)], r0=13, r1=2.2, snow=(0.0, 0.75, 1.7))
limb(pts=[(1255, 714), (1258, 660), (1258, 610), (1255, 560), (1250, 515), (1242, 470), (1233, 430), (1228, 405)], r0=12, r1=2.0, snow=(0.0, 0.68, 1.7))
limb(pts=[(1449, 472), (1421, 446), (1396, 421), (1371, 403), (1346, 393), (1316, 388), (1290, 386)], r0=8, r1=2.0, snow=(0.0, 0.75, 1.7))
limb(pts=[(1400, 425), (1398, 390), (1395, 355), (1392, 322)], r0=3.5, r1=2.0)
limb(pts=[(1437, 541), (1470, 531), (1500, 516), (1525, 504), (1550, 500), (1566, 505)], r0=7, r1=2.0, snow=(0.0, 0.6, 0.95))
limb(pts=[(1420, 586), (1455, 598), (1490, 610), (1520, 620), (1548, 630), (1570, 640)], r0=8, r1=2.0, snow=(0.0, 0.55, 0.95))
limb(pts=[(1396, 629), (1426, 656), (1461, 690), (1496, 720), (1526, 748), (1556, 772), (1580, 788)], r0=8, r1=2.0, snow=(0.0, 0.75, 1.7))
limb(pts=[(1300, 706), (1330, 731), (1356, 752), (1381, 770)], r0=6, r1=2.0, snow=(0.0, 0.5, 0.9))
limb(pts=[(1492, 376), (1520, 393), (1548, 411), (1575, 428), (1600, 442), (1622, 452)], r0=6, r1=2.0, snow=(0.0, 0.55, 0.95))
limb(pts=[(1516, 336), (1540, 346), (1565, 361), (1590, 380), (1610, 396)], r0=5, r1=2.0, snow=(0.0, 0.5, 0.9))
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
    acc = 0.0; side = 1; every = g.uniform(18, 26)
    for k in range(1, len(Sm) - 2):
        acc += math.hypot(Sm[k+1][0]-Sm[k][0], Sm[k+1][1]-Sm[k][1])
        x, y, r = Sm[k]
        if acc < every or r > 9 or k < len(Sm)*0.15: continue
        acc = 0.0; every = g.uniform(18, 26)
        tx, ty = Sm[k+1][0]-Sm[k-1][0], Sm[k+1][1]-Sm[k-1][1]; L = math.hypot(tx, ty) or 1; tx, ty = tx/L, ty/L
        a = math.atan2(ty, tx) + side*math.radians(g.uniform(35, 65)); side = -side
        ln = g.uniform(14, 28)
        p0 = (x + math.cos(a)*r*0.6, y + math.sin(a)*r*0.6)
        pts = [p0]
        for j in range(1, 4):
            aa = a + g.uniform(-0.35, 0.35)
            pts.append((pts[-1][0] + math.cos(aa)*ln/3, pts[-1][1] + math.sin(aa)*ln/3))
        if any(Point(p).buffer(3).intersects(PINES) for p in pts): continue
        regs, tp, tS = M.limb_regions(taper(pts, 1.25, 0.95), g, grp="TW")
        add(regs, 5); limb_list.append((tp, tS, (0.0, 0.7, 1.0) if g.random() < 0.45 else None)); SPRAYS.append(tS)
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

# leaves
for (x, y, L, angs) in [(1208, 752, 46, [56, 80, 104, 128, 152]), (1140, 655, 38, [128, 156, 186, 216]),
                        (1398, 426, 34, [100, 130, 160]), (1008, 826, 38, [80, 106, 132, 160]),
                        (1192, 856, 36, [50, 78, 106]), (1012, 716, 28, [200, 232, 262]), (1352, 372, 26, [200, 236])]:
    regs, _ = M.leaf_cluster(*P(x, y), L*S, angs, random.Random(x*3 + y))
    add(regs, 7)

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
for (x, y, L, angs) in [(1080, 876, 80, [64, 86, 108, 130, 152, 172]), (1204, 884, 74, [8, 30, 52, 76, 100, 122]),
                        (1040, 902, 50, [80, 108, 136]), (1150, 912, 46, [20, 48, 160])]:
    regs, _ = M.bamboo_cluster(*P(x, y), L*S, angs, random.Random(x + 7))
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
