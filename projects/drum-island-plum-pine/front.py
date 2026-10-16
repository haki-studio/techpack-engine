"""Front elements 02 (chest plum branch, split at CF zip), 03 (chest pine + mist), 04 (lower bamboo + mist).
Garment coords (mm): x from CF (+ = wearer's LEFT = viewer's right on a front view), y down from CF neck seam.
Fitted to the Drum Island block (size M, drum.py). Mockup px -> mm: x = (px - 448) * SX, y = (py - 190) * SY;
motif sizes scale by S."""
import random, math, json
import numpy as np
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union, nearest_points
from shapely import affinity
from motifs import catmull, sweep, taper, normals
import motifs2 as M

S, SX, SY = 0.77, 0.80, 0.736
CFX, NECKY = 448, 190
def P(px, py): return ((px - CFX) * SX, (py - NECKY) * SY)
def PR(pts): return [(*P(x, y), r * S) for x, y, r in pts]
def PT(pts, r0, r1): return taper([P(x, y) for x, y in pts], r0 * S, r1 * S)
def MP(pts): return [P(x, y) for x, y in pts]

# ---------------------------------------------------------------- garment model (Drum Island block, size M)
import drum
from shapely.ops import linemerge
BLK = drum.Block("M")
HEM = BLK.f_hem
PANEL_R = BLK.front_panel(-1)                                # wearer's right front (x < 0)
PANEL_L = BLK.front_panel(+1)                                # wearer's left front
ARM_R = unary_union([BLK.front_shoulder_line(-1), BLK.front_arm_line(-1)])
SIDE_R = BLK.front_side_line(-1)
_neck = [(-x, y) for x, y in drum.curve((0, 0), BLK.f_hps, 28, 16)]
COLLAR_R = Polygon(_neck + [(-176, -76), (-150, -30), (-72, 66), (-14, 22)]).buffer(0)   # collar lying flat (N = 85 to point)
COLLAR_L = affinity.scale(COLLAR_R, -1, 1, origin=(0, 0))
def welt(p0, p1, w=16):
    a = np.array(P(*p0)); b = np.array(P(*p1)); return LineString([a, b]).buffer(w * S / 2, cap_style="flat", join_style="mitre")
WELT_R = welt((160, 745), (300, 625))
WELT_L = welt((600, 630), (720, 750))
KEEP_CF, KEEP_SEAM, KEEP_HEM, KEEP_WELT, KEEP_COLLAR = 15.0, 15.0, 10.0, 6.0, 6.0

def clip_for(side):
    panel = PANEL_R if side == "R" else PANEL_L
    arm = ARM_R if side == "R" else affinity.scale(ARM_R, -1, 1, origin=(0, 0))
    sidel = SIDE_R if side == "R" else affinity.scale(SIDE_R, -1, 1, origin=(0, 0))
    collar = COLLAR_R if side == "R" else COLLAR_L
    weltg = WELT_R if side == "R" else WELT_L
    g = panel.difference(arm.buffer(KEEP_SEAM)).difference(sidel.buffer(KEEP_SEAM))
    g = g.difference(box(-KEEP_CF, -50, KEEP_CF, 900)).intersection(box(-400, -50, 400, HEM - KEEP_HEM))
    g = g.difference(collar.buffer(KEEP_COLLAR)).difference(weltg.buffer(KEEP_WELT))
    return g

items = []
def add(regs, layer, el):
    for r in regs:
        if r["geom"] is not None and not r["geom"].is_empty:
            r = dict(r); r["z"] = len(items); r["layer"] = layer; r["el"] = el; items.append(r)

def gnarl(rr, amp, seed, rad_noise=0.12, sub=2):
    g = random.Random(seed); out = []
    for i in range(len(rr) - 1):
        (x0, y0, r0_), (x1, y1, r1_) = rr[i], rr[i+1]
        for k in range(sub):
            tt = k / sub; out.append((x0 + (x1-x0)*tt, y0 + (y1-y0)*tt, r0_ + (r1_-r0_)*tt))
    out.append(rr[-1]); res = [out[0]]
    for i in range(1, len(out) - 1):
        x, y, r = out[i]
        dx, dy = out[i+1][0] - out[i-1][0], out[i+1][1] - out[i-1][1]; L = math.hypot(dx, dy) or 1
        o = g.uniform(-1, 1) * amp * (0.5 + r/12)
        res.append((x - dy/L*o, y + dx/L*o, r * (1 + g.uniform(-rad_noise, rad_noise))))
    res.append(out[-1]); return res

# ================================================================ 02 chest plum branch
limbs = []
def limb(pts_r, snow=None, amp=2.6, big=False, seed=None):
    rr = gnarl(PR(pts_r), amp, seed or 300 + len(limbs), 0.16 if big else 0.08, 3 if big else 2)
    regs, poly, Sm = M.limb_regions(rr, random.Random(seed or 40 + len(limbs)), grp="TR" if big else "LM")
    add(regs, 5, "02"); limbs.append((poly, Sm, snow))

A = [(135, 320, 12), (165, 312, 15), (195, 320, 16), (225, 342, 15.5), (250, 372, 14.5), (275, 395, 13), (300, 412, 12),
     (330, 428, 10.5), (360, 442, 9), (390, 455, 8.5), (420, 463, 8), (450, 470, 7.5), (480, 476, 7), (505, 478, 6.4),
     (530, 465, 5.5), (555, 450, 4.8), (585, 432, 4), (615, 420, 3.3), (650, 422, 2.6), (684, 444, 2.0)]
limb(A, snow=(0.03, 0.8, 3.2), amp=3.6, big=True)
limb([(168, 314, 8), (176, 292, 7), (190, 272, 6), (205, 257, 5), (225, 246, 4), (250, 240, 3.2), (275, 248, 2.5), (293, 262, 2.0)], snow=(0.0, 0.7, 1.7), big=True)
limb([(242, 356, 6.5), (250, 322, 5.5), (258, 293, 4.5), (265, 272, 3.4), (270, 254, 2.2)], snow=(0.0, 0.7, 1.4))
limb([(310, 420, 6.5), (325, 450, 5.5), (338, 480, 4.8), (348, 510, 3.8), (355, 540, 3.0), (358, 566, 2.2)], snow=(0.0, 0.55, 1.3))
limb([(530, 465, 4.4), (560, 430, 3.8), (590, 400, 3.2), (610, 378, 2.6), (628, 355, 2.0)], snow=(0.0, 0.6, 1.2))
limb([(505, 480, 4.2), (510, 505, 3.4), (515, 532, 2.8), (518, 560, 2.0)])
limb([(430, 465, 3.4), (432, 440, 2.8), (435, 415, 2.4), (437, 397, 2.0)], snow=(0.0, 0.6, 1.0))
limb([(468, 470, 3.0), (480, 445, 2.5), (493, 425, 2.0)])
limb([(208, 332, 3.4), (203, 370, 2.8), (200, 400, 2.2)])
limb([(228, 348, 3.4), (224, 400, 2.8), (220, 448, 2.2)])
limb([(590, 400, 2.8), (612, 404, 2.4), (640, 398, 2.0)])
limb([(555, 450, 3.0), (575, 470, 2.5), (598, 482, 2.0)])

# spray twigs off the limbs
for li, (poly, Sm, sn) in enumerate(list(limbs)):
    g = random.Random(700 + li); acc = 0.0; side = 1; every = g.uniform(10, 15)
    for k in range(1, len(Sm) - 2):
        acc += math.hypot(Sm[k+1][0]-Sm[k][0], Sm[k+1][1]-Sm[k][1]); x, y, r = Sm[k]
        if acc < every or r > 8 or k < len(Sm)*0.15: continue
        acc = 0.0; every = g.uniform(10, 15)
        tx, ty = Sm[k+1][0]-Sm[k-1][0], Sm[k+1][1]-Sm[k-1][1]; L = math.hypot(tx, ty) or 1; tx, ty = tx/L, ty/L
        a = math.atan2(ty, tx) + side*math.radians(g.uniform(35, 65)); side = -side
        ln = g.uniform(10, 22); pts = [(x + math.cos(a)*r*0.6, y + math.sin(a)*r*0.6)]
        for j in range(3):
            aa = a + g.uniform(-0.35, 0.35); pts.append((pts[-1][0] + math.cos(aa)*ln/3, pts[-1][1] + math.sin(aa)*ln/3))
        regs, tp, tS = M.limb_regions(taper(pts, 1.25, 0.95), g, grp="TW")
        add(regs, 5, "02"); limbs.append((tp, tS, (0.0, 0.75, 1.15) if g.random() < 0.65 else None))

for li in range(2):
    poly, Sm, _ = limbs[li]; gk = random.Random(91 + li); acc = 0.0; Nk = normals(Sm)
    for k in range(2, len(Sm) - 2):
        acc += math.hypot(Sm[k+1][0]-Sm[k][0], Sm[k+1][1]-Sm[k][1]); x, y, r = Sm[k]
        if acc > gk.uniform(22, 34) and r > 6:
            acc = 0.0; off = gk.uniform(-0.55, -0.1)
            ang = math.degrees(math.atan2(Sm[k+1][1]-Sm[k-1][1], Sm[k+1][0]-Sm[k-1][0]))
            add(M.knot(x + Nk[k][0]*r*off, y + Nk[k][1]*r*off, min(4.5, r*0.32), min(2.4, r*0.16), ang), 5, "02")
BARK = unary_union([l[0] for l in limbs])

snow_u = []
for i, (poly, Sm, sn) in enumerate(limbs):
    if sn:
        t0, t1, size = sn; tw = Sm[0][2] < 2.0
        regs, g = M.snow_regions(Sm, t0, t1, random.Random(400 + i), size=size, min_r=1.4 if tw else 2.2,
                                 gap_p=0.45 if tw else 0.2, grp="SN")
        add(regs, 6, "02"); snow_u.append(g)
SNOW = unary_union(snow_u)

for (x, y, L, angs) in [(200, 402, 34, [118, 148, 178, 208]), (220, 450, 40, [62, 88, 114, 140]), (590, 482, 24, [40, 70])]:
    regs, _ = M.leaf_cluster(*P(x, y), L*S, angs, random.Random(x*3 + y)); add(regs, 7, "02")

BLOBS = json.load(open("blobs_front.json"))
placed = []
for (bx, by, bd) in sorted(BLOBS, key=lambda b: -b[2]):
    c = P(bx, by)
    if bd >= 19:     d = min(46, max(30, bd * 1.1)) * S; kind = "L"
    elif bd >= 13:   d = max(24, bd * 1.6) * S; kind = "S"
    else:            d = max(6.4, bd * 0.98 * S); kind = "B"
    disc = Point(c).buffer(d/2 + 0.7)
    if any(Point(c).distance(Point(pc)) < (d + pd)/2 + 0.8 for pc, pd, _ in placed): continue
    if disc.intersects(SNOW.buffer(0.2)) and kind == "B": continue
    placed.append((c, d, kind))
# extra buds along limbs + tips
extra = []
for li, (poly, Sm, sn) in enumerate(limbs):
    if li < 1: continue
    N = normals(Sm); acc = 0.0; side = 1; g = random.Random(li*11)
    every = g.uniform(6.5, 9.0)
    for k in range(len(Sm) - 1):
        acc += math.hypot(Sm[k+1][0]-Sm[k][0], Sm[k+1][1]-Sm[k][1]); x, y, r = Sm[k]
        if acc > every and r < 5.0 and k > len(Sm)*0.25:
            d = g.uniform(6.2, 7.6); extra.append(((x + N[k][0]*side*(r + d*0.42), y + N[k][1]*side*(r + d*0.42)), d, "B"))
            side = -side; acc = 0.0; every = g.uniform(6.5, 9.0)
    x, y, r = Sm[-1]; tdir = np.array(Sm[-1][:2]) - np.array(Sm[-3][:2]); tdir = tdir/(np.linalg.norm(tdir) or 1)
    extra.append((tuple(np.array([x, y]) + tdir*3.2), 7.0, "B"))
for c, d, k in extra:
    disc = Point(c).buffer(d/2 + 0.7)
    if disc.intersects(SNOW.buffer(0.3)): continue
    if any(Point(c).distance(Point(pc)) < (d + pd)/2 + 0.8 for pc, pd, _ in placed): continue
    placed.append((c, d, k))
placed = [(c, d, k) for c, d, k in placed if BARK.distance(Point(c)) - d/2 < (3.5 if k == "B" else 12)]
# twig stubs to blossoms not touching bark
for c, d, kind in placed:
    dist = BARK.distance(Point(c)) - d/2
    if 1.2 < dist < 12:
        a, _ = nearest_points(BARK, Point(c)); v = np.array(c) - np.array([a.x, a.y]); u = v/np.linalg.norm(v)
        end = np.array(c) - u*d*0.3
        regs, _, _ = M.limb_regions(taper([(a.x, a.y), tuple(end)], 1.1, 0.9), random.Random(int(c[0]*7)), grp="TW"); add(regs, 5, "02")
for i, (c, d, kind) in enumerate(placed):
    if kind in ("L", "S"):
        regs, _ = M.blossom(*c, d, random.Random(i).uniform(-20, 20)); add(regs, 8, "02")
    else:
        a, _ = nearest_points(BARK, Point(c)); ang = math.degrees(math.atan2(a.y - c[1], a.x - c[0]))
        regs, _ = M.bud(*c, d, ang); add(regs, 9, "02")

# ================================================================ 03 chest pine + mist (wearer's left)
for (x, y, L, rows) in [(556, 598, 125, 3), (640, 618, 90, 2)]:
    regs, _ = M.mist(*P(x, y), L*S, rows, 3.6, random.Random(x + y)); add(regs, 1, "03")
pb, pbp, pbS = M.limb_regions(gnarl(PR([(588, 594, 5.5), (628, 596, 5.8), (668, 600, 5.4), (708, 606, 4.6), (745, 616, 3.2)]), 1.6, 77), random.Random(5), grp="PB")
add(pb, 2, "03")
sr, _ = M.snow_regions(pbS, 0.05, 0.9, random.Random(9), size=1.1, min_r=1.8, gap_p=0.3, grp="PB-SN"); add(sr, 2, "03")
for hx, hy, R_, rot in [(667, 580, 50, 0), (620, 590, 42, -14), (710, 596, 40, 14)]:
    regs, _ = M.pine_fan(*P(hx, hy), R_*S, "white", rot); add(regs, 4, "03")

# ================================================================ 04 lower bamboo + mist (wearer's right)
for (x, y, L, rows) in [(128, 772, 130, 3), (210, 800, 150, 3), (150, 836, 120, 2)]:
    regs, _ = M.mist(*P(x, y), L*S, rows, 3.6, random.Random(x*7 + y)); add(regs, 1, "04")
for (x, y, L, angs) in [(238, 762, 72, [4, 32, 58, 84, 110, 138, 166, 205, 236]), (192, 815, 56, [8, 38, 68, 98, 128, 160, 190])]:
    regs, _ = M.bamboo_cluster(*P(x, y), L*S, angs, random.Random(x + 3)); add(regs, 10, "04")

# ================================================================ pieces
PIECES = {"02R": ("02", "R"), "02L": ("02", "L"), "03": ("03", "L"), "04": ("04", "R")}
def build(piece):
    el, side = PIECES[piece]
    clip = clip_for(side)
    vis = []; above = Polygon()
    for r in reversed([r for r in items if r["el"] == el]):
        g = r["geom"].intersection(clip)
        v = g.difference(above); above = above.union(g)
        rr = dict(r); rr["geom"] = v; vis.append(rr)
    vis.reverse()
    vis = [v for v in vis if not v["geom"].is_empty and v["geom"].area > 0.02]
    import back2
    return back2.absorb_slivers(vis)

def zip_marks():
    bark = limbs[0][0]
    out = []
    for xx in (-KEEP_CF, KEEP_CF):
        inter = bark.intersection(LineString([(xx, -50), (xx, 900)]))
        segs = [inter] if inter.geom_type == "LineString" else [g for g in getattr(inter, "geoms", []) if g.geom_type == "LineString"]
        for s in segs:
            ys = [c[1] for c in s.coords]
            if max(ys) - min(ys) > 1.5: out.append((xx, min(ys), max(ys)))
    return out
