"""Moon jacket scene composition. All art is composed on the size-M pattern (moonpattern / engine pattern, garment
coords: back x from CB (+ = wearer's right), y down from CB neck seam; fronts x from CF (+ = wearer's left), y from
CF neck seam; sleeves in S01/S02 pattern coords). Mockup (inputs/back.png, front.png, 724x870) was measured on a
grid and converted to mm by hand (positions below are mm, M).

Elements
  01  back scene     — moon, clouds, pole, wires, LICENSED-FIGURE PLACEHOLDER BOX (knocked out) — per size
  02  chest clouds   — 02R wearer's right front, 02L wearer's left front — graded A/B/C
  03  lower front    — 03L pole + wires + cloud (wearer's left), 03R wires (wearer's right) — per size
  04  sleeve clouds  — 04R right sleeve (S01), 04L left sleeve (S02) — graded A/B/C
Wires wrap back <-> front across the SIDE SEAMS (end 3 mm short on both pieces, same height above the hem seam)
and cross the CF zip (end 15 mm each side, same curve) — so 01 and 03 are rebuilt per size from that size's pattern."""
import math, random
import numpy as np
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union
from shapely import affinity
from shapely.validation import make_valid
import moonpal
import moonpattern, pattern as PT
import moonmotifs as MM
import front as FR

GRADE = {"XS": ("A", 0.92), "S": ("A", 0.92), "M": ("B", 1.0), "L": ("B", 1.0), "XL": ("B", 1.0), "XXL": ("C", 1.08), "3XL": ("C", 1.08)}
SCALE = {"A": 0.92, "B": 1.0, "C": 1.08}
KEEP = dict(seam=15.0, side=15.0, cf=15.0, hem=10.0, welt=6.0, collar=6.0, neck=6.0, cuff=10.0, wrap=FR.WRAP)
L_MOON, L_MDET, L_WIRE, L_CLOUD, L_POLE, L_HW = 11, 12, 13, 14, 15, 16

# ---------------------------------------------------------------- placeholder box (licensed figure)  — M, back coords
# mockup figure bounds (back.png px x 316..377, y 358..437) -> 63 x 81 mm + 4 mm margin all round. PROPOSED.
POLE_TOP_B = 338.0
BOX_M = (-35.5, POLE_TOP_B - 89.0, 35.5, POLE_TOP_B)

# ---------------------------------------------------------------- wire network: heights above the hem seam (mm, M)
# back left side seam (wearer's left)  <->  front wearer's-left side seam (03L)
H_LEFT = [150.0, 138.0, 100.0, 62.0]
# back right side seam (wearer's right) <->  front wearer's-right side seam (03R, wires from the 03L pole across the zip)
H_RIGHT = [80.0, 62.0, 46.0, 30.0]

def edge(g, pc, name): return LineString(next(e.pts for e in g[pc].edges if e.name == name))

def size_tf(size):
    """M -> size transform for per-size art: motifs scale by the grade about (CB/CF, 10 above the hem seam)."""
    g, mt = PT.draft(size); gM, mM = PT.draft("M"); sc = SCALE[GRADE[size][0]]
    def back(x, y): return (x * sc, (mt["hem_b"] - 10) - ((mM["hem_b"] - 10) - y) * sc)
    kx = mt["block"].chest2 / mM["block"].chest2
    def front(x, y):      # front pole sits by the side seam: x follows the chest grade, size follows the art grade
        return (x * sc, (mt["hem_f"] - 10) - ((mM["hem_f"] - 10) - y) * sc)
    return g, mt, sc, kx, back, front

def T(regs, f, sc):
    out = []
    for r in regs:
        g = affinity.scale(r["geom"], sc, sc, origin=(0, 0))
        o = f(0, 0); g = affinity.translate(g, o[0], o[1])
        out.append(dict(r, geom=g.buffer(0) if r["st"] not in ("bean", "run") else g))
    return out

class Items(list):
    def add(self, regs, layer, el=None):
        for r in regs:
            if r["geom"] is not None and not r["geom"].is_empty:
                r = dict(r); r["z"] = len(self); r["layer"] = layer; r["el"] = el; self.append(r)

# ================================================================ 01 back
def back_art(size="M"):
    """items for the back at `size`, + info (box, pole, wire seam marks)."""
    g, mt, sc, kx, TB, _ = size_tf(size)
    P = lambda x, y: TB(x, y)
    S = lambda v: v * sc
    it = Items(); rng = random.Random(7)
    # moon
    mreg, mdet, disc = MM.moon(*P(0, 244), S(120), random.Random(5))
    it.add(mreg, L_MOON, "01"); it.add(mdet, L_MDET, "01")
    # pole hardware geometry (attachment points first: wires go behind the hardware)
    cx = 0.0
    y0, y1 = P(0, POLE_TOP_B)[1], P(0, 575)[1]
    arm0, arm1 = P(-66, 392), P(98, 367)
    def on_arm(x):
        t = (x - arm0[0]) / (arm1[0] - arm0[0]); return (x, arm0[1] + (arm1[1] - arm0[1]) * t)
    ins_x = [S(-50), S(62), S(86)]
    tips = {}
    hw = []
    a_regs, arm_g = MM.crossarm(arm0, arm1, S(4.8)); hw += a_regs
    for nm, x in zip(("i1", "i2", "i3"), ins_x):
        r_, tip = MM.insulator(x, on_arm(x)[1] - S(2.4), S(7.5), S(4.4)); hw += r_; tips[nm] = tip
    for x in (S(-36), S(36)):
        hw += MM.bracket(on_arm(x), (math.copysign(S(9), x), P(0, 412)[1]))
    sl0, sl1 = P(-12, 428), P(-66, 428)
    hw += MM.string_insulator(sl0, sl1, 6, S(4.8))
    tips["s1"] = sl1
    cr, _ = MM.can(*P(15, 397), S(40), S(70)); hw += cr
    hw += MM.bracket(P(12, 405), P(16, 405)) + MM.bracket(P(12, 455), P(16, 455))
    cl, _ = MM.can(*P(-42, 440), S(24), S(42)); hw += cl
    hw += MM.bracket(P(-18, 448), P(-12, 448))
    sr0, sr1 = P(12, 503), P(60, 503)
    hw += MM.string_insulator(sr0, sr1, 6, S(4.2)); tips["s2"] = sr1
    tips["a0"] = arm0; tips["a1"] = arm1
    # wires: to the side seams at the agreed heights (graded), + two drop wires that end above the hem rib
    xs = mt["block"].chest2
    seamL = lambda h: (-xs, mt["hem_b"] - h * sc)
    seamR = lambda h: (xs, mt["hem_b"] - h * sc)
    W = [("a0", seamL(H_LEFT[0])), ("i1", seamL(H_LEFT[1])), ("s1", seamL(H_LEFT[2])), ("s1", seamL(H_LEFT[3])),
         ("a1", seamR(H_RIGHT[0])), ("i3", seamR(H_RIGHT[1])), ("i2", seamR(H_RIGHT[2])), ("s2", seamR(H_RIGHT[3])),
         ("s1", (S(-118), mt["hem_b"] - 4)), ("s2", (S(132), mt["hem_b"] - 4))]
    wires = []; ends = []
    for a, b in W:
        p0 = tips[a]; span = abs(b[0] - p0[0])
        if abs(abs(b[0]) - xs) < 0.01: ends.append(("R" if b[0] > 0 else "L", round(mt["hem_b"] - b[1], 1), b))
        reg, ln = MM.wire(p0, b, 0.055 * span if abs(b[1] - mt["hem_b"]) > 8 else 0.02 * span, 1.0)
        wires.append(reg)
    it.add(wires, L_WIRE, "01")
    # clouds (in front of the moon + wires)
    CL = [(-268, -60, 268, 52, [(0, 0.78, 0, 1.0), (0.3, 1.0, 0.3, 0.62)], (1, 0.30), 11),
          (-226, -40, 314, 36, None, (1, 0.25), 12),
          (82, 278, 300, 44, [(0.0, 0.85, 0, 1.0), (0.25, 1.0, 0.25, 0.6)], (-1, 0.25), 13),
          (-262, -60, 414, 50, [(0, 0.8, 0, 1.0), (0.35, 1.0, 0.3, 0.6)], (1, 0.22), 14),
          (88, 280, 371, 46, None, (-1, 0.25), 15)]
    for x0, x1, yb, H, tiers, tail, seed in CL:
        (a, yy) = P(x0, yb); (b, _) = P(x1, yb)
        regs, _ = MM.cloud(a, b, yy, S(H), random.Random(seed), tiers=tiers, tail=tail)
        it.add(regs, L_CLOUD, "01")
    # pole on top
    pr, pbody = MM.pole(cx, y0, y1, S(25), rng); it.add(pr, L_POLE, "01")
    it.add(hw, L_HW, "01")
    bx = BOX_M; b0 = P(bx[0], bx[1]); b1 = P(bx[2], bx[3]); BOX = box(b0[0], b0[1], b1[0], b1[1])
    info = dict(size=size, grade=GRADE[size][0], scale=sc, box=BOX.bounds, moon=dict(c=P(0, 244), r=S(120)),
                pole=dict(x=cx, y0=y0, y1=y1), wire_ends=ends)
    return it, BOX, info

def back_clips(size):
    g, mt = PT.draft(size); pc = g["B01"]; P_ = pc.sew_poly()
    def minus(names, k):
        return unary_union([edge(g, "B01", n).buffer(k) for n in names])
    base = P_.difference(minus(["armhole L", "armhole R", "shoulder L", "shoulder R"], KEEP["seam"])).difference(minus(["neck"], KEEP["neck"]))
    base = base.difference(minus(["hem"], KEEP["hem"]))
    art = base.difference(minus(["side L", "side R"], KEEP["side"]))
    wire = base.difference(minus(["side L", "side R"], KEEP["wrap"]))
    return make_valid(art).buffer(0), make_valid(wire).buffer(0)

# ================================================================ 03 lower front (per size), 02 chest clouds (M)
def front_art(size="M"):
    g, mt, sc, kx, _, TF = size_tf(size)
    P = lambda x, y: TF(x, y)
    S = lambda v: v * sc
    it = Items(); rng = random.Random(21)
    tips = {}; hw = []
    # pole on the wearer's left front, outside the welt pocket; held 15 from the side seam via x of the M layout x kx
    PX = 250.0
    def Q(x, y):             # pole-local: M x offsets from the pole centre, which follows the chest grade
        px, py = P(PX, y); return (PX * kx + (x - PX) * sc, py)
    y0, y1 = Q(PX, 325)[1], Q(PX, 500)[1]
    a0, a1 = Q(205, 347), Q(282, 343)
    def on_arm(x):
        t = (x - a0[0]) / (a1[0] - a0[0]); return (x, a0[1] + (a1[1] - a0[1]) * t)
    r_, arm = MM.crossarm(a0, a1, S(4.4)); hw += r_
    for nm, x in (("i1", Q(214, 0)[0]), ("i2", Q(274, 0)[0])):
        r_, tip = MM.insulator(x, on_arm(x)[1] - S(2.2), S(7.0), S(4.2)); hw += r_; tips[nm] = tip
    hw += MM.bracket(on_arm(Q(226, 0)[0]), Q(241, 362))
    cr, _ = MM.can(*Q(262, 360), S(21), S(46)); hw += cr
    hw += MM.bracket(Q(260, 372), Q(263, 372)) + MM.bracket(Q(260, 398), Q(263, 398))
    s0, s1 = Q(239, 436), Q(203, 436)
    hw += MM.string_insulator(s0, s1, 5, S(4.4)); tips["s1"] = s1
    cl, _ = MM.can(*Q(216, 444), S(18), S(36)); hw += cl
    hw += MM.bracket(Q(234, 452), Q(240, 452))
    tips.update(a1=a1, can=Q(283, 395), pr=Q(261, 455), cs=Q(216, 456), pl=Q(239, 470))
    xs = mt["block"].chest2
    seamL = lambda h: (xs, mt["hem_f"] - h * sc)                # wearer's left side seam (x > 0)
    seamR = lambda h: (-xs, mt["hem_f"] - h * sc)               # wearer's right side seam, across the zip
    W = [("i2", seamL(H_LEFT[0]), 0.0), ("a1", seamL(H_LEFT[1]), 0.0), ("can", seamL(H_LEFT[2]), 0.0), ("pr", seamL(H_LEFT[3]), 0.0),
         ("s1", seamR(H_RIGHT[0]), 22.0), ("s1", seamR(H_RIGHT[1]), 24.0), ("cs", seamR(H_RIGHT[2]), 18.0), ("pl", seamR(H_RIGHT[3]), 13.0)]
    wires = []; ends = []
    for a, b, sag in W:
        ends.append(("L" if b[0] > 0 else "R", round(mt["hem_f"] - b[1], 1), b))
        reg, _ = MM.wire(tips[a], b, S(sag) if sag else 0.04 * abs(b[0] - tips[a][0]), 1.0); wires.append(reg)
    it.add(wires, L_WIRE, "03")
    # lower cloud with a long wisp tail across the zip (split at the zip like the wires)
    (ca, cy) = P(28, 392); (cb, _) = P(108, 392)
    regs, _ = MM.cloud(ca, cb, cy, S(30), random.Random(31), tail=(-1, 0.0))
    it.add(regs, L_CLOUD, "03")
    it.add(MM.wisp(P(-92, 0)[0], ca + S(10), cy - S(2.0), S(2.4)), L_CLOUD, "03")
    it.add(MM.wisp(P(-60, 0)[0], ca + S(4), cy + S(1.8), S(1.8)), L_CLOUD, "03")
    pr, _ = MM.pole(Q(PX, 0)[0], y0, y1, S(22), rng); it.add(pr, L_POLE, "03")
    it.add(hw, L_HW, "03")
    return it, dict(size=size, grade=GRADE[size][0], scale=sc, pole_x=Q(PX, 0)[0], wire_ends=ends)

def chest_art():
    """02 chest clouds at M (graded files are scaled about each piece's centre)."""
    it = Items()
    CL = [(-242, -50, 150, 58, [(0, 0.8, 0, 1.0), (0.3, 1.0, 0.28, 0.6)], (1, 0.25), 41),
          (-258, -36, 215, 55, [(0, 0.75, 0, 1.0), (0.35, 1.0, 0.3, 0.62)], (1, 0.18), 42),
          (72, 258, 185, 48, [(0.15, 1.0, 0, 1.0), (0.0, 0.7, 0.3, 0.6)], (-1, 0.28), 43),
          (150, 270, 228, 34, None, (-1, 0.35), 44)]
    for x0, x1, yb, H, tiers, tail, seed in CL:
        regs, _ = MM.cloud(x0, x1, yb, H, random.Random(seed), tiers=tiers, tail=tail, flip=x0 > 0)
        it.add(regs, L_CLOUD, "02")
    it.add(MM.wisp(22, 95, 222, 2.2), L_CLOUD, "02")
    return it

def front_clips(size):
    g, mt = PT.draft(size); out = {}
    for pc, side in (("F01", 1), ("F02", -1)):
        P_ = g[pc].sew_poly()
        sub = lambda names, k: unary_union([edge(g, pc, n).buffer(k) for n in names])
        weltg = Polygon(g[pc].internal[0][1])
        collar = FR.COLLAR_L if side > 0 else FR.COLLAR_R
        base = P_.difference(sub(["armhole", "shoulder"], KEEP["seam"])).difference(sub(["CF / zip"], KEEP["cf"]))
        base = base.difference(sub(["hem"], KEEP["hem"])).difference(weltg.buffer(KEEP["welt"])).difference(collar.buffer(KEEP["collar"]))
        base = base.difference(sub(["neck"], KEEP["neck"]))
        out[pc] = (make_valid(base.difference(sub(["side"], KEEP["side"]))).buffer(0), make_valid(base.difference(sub(["side"], KEEP["wrap"]))).buffer(0))
    return out

# ================================================================ 04 sleeve clouds (M, sleeve pattern coords; S01 right: front x > 0)
SLEEVE_CL = {
 "04R": [(45, 175, 48, 40, None, (-1, 0.22), 51), (25, 185, 175, 48, [(0, 0.8, 0, 1.0), (0.3, 1.0, 0.3, 0.6)], (-1, 0.2), 52),
         (-190, -60, 50, 40, None, (1, 0.22), 53), (-175, -25, 170, 45, [(0.2, 1.0, 0, 1.0), (0, 0.7, 0.3, 0.6)], (1, 0.2), 54),
         (-160, -15, 285, 45, None, (1, 0.25), 55)],
 "04L": [(-175, -45, 95, 42, None, (1, 0.22), 61), (-170, -35, 235, 46, [(0.2, 1.0, 0, 1.0), (0, 0.7, 0.3, 0.6)], (1, 0.2), 62),
         (50, 195, 110, 46, [(0, 0.8, 0, 1.0), (0.3, 1.0, 0.3, 0.6)], (-1, 0.22), 63), (15, 160, 280, 45, None, (-1, 0.25), 64)]}
def sleeve_art(k):
    it = Items()
    for x0, x1, yb, H, tiers, tail, seed in SLEEVE_CL[k]:
        c = (x0 + x1) / 2; x0, x1 = c + (x0 - c) * 1.15, c + (x1 - c) * 1.15; H = H * 1.2
        regs, _ = MM.cloud(x0, x1, yb, H, random.Random(seed), tiers=tiers, tail=tail, flip=x0 > 0)
        it.add(regs, L_CLOUD, "04")
    return it

def sleeve_clip(size, k):
    g, mt = PT.draft(size); pc = "S01" if k == "04R" else "S02"; P_ = g[pc].sew_poly()
    sub = lambda names, kk: unary_union([edge(g, pc, n).buffer(kk) for n in names])
    c = P_.difference(sub(["cap", "underarm front", "underarm back"], KEEP["seam"])).difference(sub(["cuff"], KEEP["cuff"]))
    return make_valid(c).buffer(0)

# ================================================================ knockout + clip
def build(items, clip, wire_clip=None, knock=None):
    vis = []; above = Polygon()
    for r in reversed(items):
        cl = wire_clip if (wire_clip is not None and r["grp"] == "WR") else clip
        try:
            gg = r["geom"].intersection(cl)
            if knock is not None: gg = gg.difference(knock)
            v = gg.difference(above); above = above.union(gg)
        except Exception:
            gg = make_valid(r["geom"]).buffer(0.001).buffer(-0.001).intersection(cl)
            if knock is not None: gg = gg.difference(knock)
            v = gg.difference(above.buffer(0)); above = above.buffer(0).union(gg)
        vis.append(dict(r, geom=v))
    vis.reverse()
    vis = [v for v in vis if not v["geom"].is_empty and v["geom"].area > 0.02]
    return absorb_slivers(vis)

def absorb_slivers(vis):
    """(from plum + pine back2.py) knockout slivers narrower than the stitch minimum go to the neighbour they touch most."""
    from shapely.strtree import STRtree
    geoms = [v["geom"] for v in vis]; tree = STRtree(geoms); give = {}
    for i, v in enumerate(vis):
        line = v["st"] in ("bean", "run"); h = 0.3 if line else 0.4
        clean = v["geom"].buffer(-h).buffer(h).intersection(v["geom"]); sl = v["geom"].difference(clean)
        if sl.is_empty or sl.area < 0.01: continue
        keep = clean
        for piece in ([sl] if sl.geom_type == "Polygon" else [p for p in getattr(sl, "geoms", []) if p.geom_type == "Polygon"]):
            if piece.area < 0.004: continue
            best, bl = None, 0.0
            for j in tree.query(piece.buffer(0.05)):
                j = int(j)
                if j == i: continue
                if vis[j]["st"] in ("bean", "run") and not line: continue
                L = piece.buffer(0.05).intersection(geoms[j]).area * (1.5 if j > i else 1.0)
                if L > bl: best, bl = j, L
            if best is None: keep = keep.union(piece)
            else: give.setdefault(best, []).append(piece)
        vis[i] = dict(v, geom=keep)
    for j, pcs in give.items():
        vis[j] = dict(vis[j], geom=unary_union([vis[j]["geom"]] + pcs))
    return [v for v in vis if not v["geom"].is_empty and v["geom"].area > 0.02]

# ================================================================ match marks
def seam_check(vis, ends, xs):
    """every wire that meets a side seam must be visible up to 3 mm (±0.6) from the seam line on this piece.
    Returns [(side, h above hem, distance of the visible end from the seam or None)]"""
    U = unary_union([r["geom"] for r in vis if r["grp"] == "WR"]); out = []
    for side, h, (x, y) in ends:
        sg = 1 if x > 0 else -1
        win = U.intersection(box(min(sg * (xs - 12), sg * xs), y - 4, max(sg * (xs - 12), sg * xs), y + 4))
        d = None if win.is_empty else round(xs - (win.bounds[2] if sg > 0 else -win.bounds[0]), 2)
        out.append((side, h, d))
    return out

def zip_marks(vis, side):
    """wire / wisp ends at the zip keep-out line (x = ±15): y of each end"""
    out = []
    for r in vis:
        if r["grp"] not in ("WR", "CL-wisp"): continue
        for p in MM._polys(r["geom"]):
            b = p.bounds; xe = b[0] if side > 0 else b[2]
            if abs(abs(xe) - KEEP["cf"]) < 1.0:
                sl = p.intersection(box(xe - 1.0, -1e4, xe + 1.0, 1e4))
                if not sl.is_empty: out.append((r["grp"], round(sl.centroid.y, 1)))
    return sorted(set(out), key=lambda t: t[1])

def art_for_size(size):
    """everything per size: back + 03L + 03R vis, marks."""
    itb, BOX, info = back_art(size)
    cb, cw = back_clips(size)
    vb = build(itb, cb, cw, knock=BOX)
    itf, finfo = front_art(size)
    fc = front_clips(size)
    vL = build(itf, *fc["F01"]); vR = build(itf, *fc["F02"])
    g, mt = PT.draft(size); xs = mt["block"].chest2
    info.update(front=finfo,
                marks=dict(back=seam_check(vb, info["wire_ends"], xs),
                           front_L=seam_check(vL, [e for e in finfo["wire_ends"] if e[0] == "L"], xs),
                           front_R=seam_check(vR, [e for e in finfo["wire_ends"] if e[0] == "R"], xs),
                           zip_L=zip_marks(vL, 1), zip_R=zip_marks(vR, -1)))
    return dict(back=vb, F03L=vL, F03R=vR, info=info)

def graded_art():
    """02 + 04 at M (clipped to the M pattern); per-size placement in emb_place."""
    fc = front_clips("M"); it = chest_art()
    out = {"02R": build(it, fc["F02"][0]), "02L": build(it, fc["F01"][0])}
    for k in ("04R", "04L"): out[k] = build(sleeve_art(k), sleeve_clip("M", k))
    return out
