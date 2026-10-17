"""Compose the four badges + the star field on the size-M pieces (garment mm, unclipped).
Badge layout (anchor positions, angles, motif counts) is read from the mockup (inputs/flat.png) through mockmap: each
badge is placed at its mapped anchor (P) and drawn at the uniform motif scale S about it. Text is SET FROM FONTS with
the brief's exact characters (kclettering), never traced from the AI glyphs. Star speckles: detected on the mockup
(white specks), positions mapped, sizes from the speck extents. Sleeves: the visible (front) half is mapped from the
mockup sleeve; the back half gets a seeded field at the same density + size mix.  [PROPOSED: back half of sleeves]
Output: scene.pkl = {"items": {"FR": [...], "FL": [...], "SR": [...], "SL": [...]}, "meta": {...}}.
usage: python3 scene.py [preview]"""
import kccore
import math, random, pickle, sys, json
import numpy as np
from scipy import ndimage as ndi
from PIL import Image
from shapely.geometry import Point, Polygon, LineString, box, MultiPoint
from shapely.ops import unary_union
from shapely import affinity
import mockmap as MM, front as F, kcmotifs as KM, kclettering as KL

S = MM.S
items = {"FR": [], "FL": [], "SR": [], "SL": []}
META = {"badges": {}, "counts": {}}
def add(piece, regs, layer, el, unit=None, **kw):
    for r in regs:
        g = r["geom"]
        if g is None or g.is_empty: continue
        r = dict(r); r.update(kw); r["layer"] = layer; r["el"] = el
        r["z"] = layer*100000 + len(items[piece]); r.setdefault("ko", True); r.setdefault("kob", 0.0)
        r["unit"] = unit if unit is not None else r.get("unit")
        items[piece].append(r)

def anchor(px, py):
    """local uniform map about a mockup anchor point: mockup px -> garment mm"""
    ax, ay = MM.P(px, py)
    return lambda qx, qy: (ax + (qx - px)*S, ay + (qy - py)*S)

def text_regs(glyphs, col, code, unit):
    regs = []
    for ch, g in glyphs:
        for s in KL.strokes(g):
            regs.append(KM.R(col, s, "satin", "auto", code, unit=unit, kob=0.5, ch=ch))
    return regs

# ================================================================ 01 JP badge  (FR, wearer's right chest)
J0 = (398.75, 491.25); J = anchor(*J0)
JC = J(*J0); JANG = -30.1
jp = KL.place(KL.set_line("jp", kccore.TEXT["01"], 22.0), *JC, JANG)
META["badges"]["01"] = dict(anchor_px=J0, centre=JC, angle=JANG, em=22.0, text=kccore.TEXT["01"])
band = unary_union([g for _, g in jp]).buffer(9.0).buffer(-3.5)          # halo hugs the letters (mockup: ~5 mm glow)
add("FR", KM.glow(band, JANG, rng=random.Random(11)), 20, "01", unit="01-glow", nok=True)
BARS_JP = [  # mockup px centre, length px, angle deg (y down), colour  (21 bars, counted on the mockup)
    ((298.5, 537.2), 26.0, -8, "kc_mint"), ((347.6, 474.3), 23.0, 52, "kc_mint"), ((454.8, 495.9), 25.6, 52, "kc_mint"),
    ((465.6, 410.5), 25.7, 110, "kc_blue"), ((401.0, 439.6), 16.3, 73, "kc_blue"), ((314.0, 512.7), 11.9, 42, "kc_blue"),
    ((403.0, 520.9), 15.8, 54, "kc_blue"), ((345.9, 569.4), 21.2, 83, "kc_blue"), ((336.9, 591.9), 12.6, 100, "kc_blue"),
    ((474.4, 424.3), 8.8, 133, "kc_red"), ((492.7, 450.2), 17.6, -7, "kc_red"), ((439.0, 500.5), 16.9, 69, "kc_red"),
    ((390.8, 539.7), 32.0, 60, "kc_red"),
    ((493.3, 472.8), 29.2, 16, "kc_lemon"), ((329.5, 566.3), 17.4, 106, "kc_lemon"), ((339.4, 489.4), 16.0, 45, "kc_lemon"),
    ((373.8, 451.3), 28.5, 52, "kc_lemon"),
]
for i, ((px, py), L, a, col) in enumerate(BARS_JP):
    cx, cy = J(px, py); w = 3.4 if L > 10 else 3.0
    if (px, py) == (336.9, 591.9): w = 2.6
    add("FR", KM.capsule_c(cx, cy, max(L*S, w + 1), w, a, col, "PF-BAR"), 30, "01", unit=f"01-bar{i}")
add("FR", KM.ring_dot(*J(523.2, 480.0), 9.4, "kc_mint", "PF-BAR"), 30, "01", unit="01-dot")
add("FR", KM.heart(*J(395.6, 421.0), 12.0, "kc_red"), 30, "01", unit="01-heart0")
add("FR", KM.heart(*J(333.3, 459.5), 10.4, "kc_red", rot=-8), 30, "01", unit="01-heart1")
add("FR", KM.star5(*J(303.8, 501.3), 14.0, "kc_gold", "PF-STR", rot=-12, face="eyes"), 30, "01", unit="01-star0")
add("FR", KM.star5(*J(460.0, 391.3), 14.4, "kc_gold", "PF-STR", rot=6, face="centre", face_col="kc_white"), 30, "01", unit="01-star1")
add("FR", KM.star5(*J(482.5, 415.0), 6.4, "kc_gold", "STR5", rot=0), 22, "01", unit="01-star2")
add("FR", KM.star5_outline(*J(406.3, 563.8), 15.0, 1.5, "kc_red", rot=10), 22, "01", unit="01-star3")
add("FR", text_regs(jp, "kc_mint", "PF-TX", "01-text"), 31, "01", unit="01-text")

# ================================================================ 02 EN badge  (FL, wearer's left chest)
E0 = (791.0, 516.0); E = anchor(*E0); EC = E(*E0); EANG = 50.0
em_en = 22.0
l1 = KL.set_line("en", "KEEP CLEAN", em_en, tracking=0.6); l2 = KL.set_line("en", "OUR SPACE", em_en, tracking=0.6)
lh = 27.0                              # line pitch, measured on the mockup (line centres 28 mm apart)
b1 = KL.ink_bounds(l1); b2 = KL.ink_bounds(l2)
u = np.array([math.cos(math.radians(EANG)), math.sin(math.radians(EANG))]); n = np.array([-u[1], u[0]])
c1 = np.array(EC) + np.array([5.0, -2.5]) - n*lh/2; c2 = c1 + n*lh
L1 = KL.place(l1, *c1, EANG); L2 = KL.place(l2, *c2, EANG)
keep = [(ch, g) for ch, g in L1[:4]]; clean = [(ch, g) for ch, g in L1[4:]]
META["badges"]["02"] = dict(anchor_px=E0, centre=EC, angle=EANG, em=em_en, text="KEEP CLEAN / OUR SPACE")
eb = unary_union([g for _, g in L1 + L2]).buffer(9.0).buffer(-3.5)
add("FL", KM.glow(eb, EANG, rng=random.Random(12)), 20, "02", unit="02-glow", nok=True)
STARS_EN = [(325, 105), (425, 130), (495, 215), (570, 300), (645, 400), (720, 495), (770, 600), (800, 840), (750, 935), (645, 985),
            (540, 910), (460, 815), (385, 720), (305, 625), (225, 530), (140, 430), (115, 310), (195, 190)]      # 18 stars (crop_en2: /4 + (670,380))
for i, (cx_, cy_) in enumerate(STARS_EN):
    px, py = 670 + cx_/4, 380 + cy_/4
    add("FL", KM.star5(*E(px, py), 11.6, "kc_gold", "PF-STR", rot=(i*7) % 15 - 7), 30, "02", unit=f"02-star{i}")
add("FL", text_regs(keep, "kc_mint", "PF-TX", "02-text") + text_regs(L2, "kc_mint", "PF-TX", "02-text"), 31, "02", unit="02-text")
add("FL", text_regs(clean, "kc_lemon", "PF-TX", "02-text"), 31, "02", unit="02-text")

# ================================================================ 03 CN badge  (FR, wearer's right lower front)
DOTS_CN = [  # (px, py, colour) 22 dots detected on the mockup, alternating blue / mint around the ring
    (385.4, 661.8, "b"), (338.9, 678.5, "b"), (413.4, 702.5, "b"), (330.3, 726.4, "b"), (428.0, 758.0, "b"), (339.6, 781.6, "b"),
    (441.6, 811.6, "b"), (355.7, 839.7, "b"), (451.8, 866.9, "b"), (375.2, 899.6, "b"),
    (356.4, 660.6, "m"), (403.8, 678.5, "m"), (329.9, 700.5, "m"), (422.6, 730.5, "m"), (334.5, 753.2, "m"), (435.8, 784.4, "m"),
    (348.1, 812.1, "m"), (448.2, 839.5, "m"), (363.0, 869.7, "m"), (447.5, 893.8, "m"), (425.9, 914.0, "m"), (398.7, 917.1, "m")]
C0 = (390.0, 789.0); CN_SHIFT = (14.0, 0.0)        # moved 14 mm toward CF: clears the welt box by >= 6 on every size
_C = anchor(*C0); C = lambda px, py: (_C(px, py)[0] + CN_SHIFT[0], _C(px, py)[1] + CN_SHIFT[1])
CC = C(*C0)
dpts = [C(px, py) for px, py, _ in DOTS_CN]
# ring path through the dot centres (ordered by angle about the ring centre)
ring_c = np.mean(np.array(dpts), axis=0)
order = sorted(range(len(dpts)), key=lambda i: math.atan2(dpts[i][1] - ring_c[1], dpts[i][0] - ring_c[0]))
ring_path = LineString([dpts[i] for i in order] + [dpts[order[0]]])
META["badges"]["03"] = dict(anchor_px=C0, centre=CC, shift=CN_SHIFT, text=kccore.TEXT["03"], dots=len(dpts))
# glow: one zig-zag sheer run along the dot ring (halo around every dot, no trims)
def zigzag(path, hw, step):
    pts = []; Lp = path.length; k = 0
    for s in np.arange(0, Lp, step):
        a = path.interpolate(max(0, s - 0.5)); b = path.interpolate(min(Lp, s + 0.5)); c = path.interpolate(s)
        t = np.array([b.x - a.x, b.y - a.y]); t /= max(np.linalg.norm(t), 1e-9); nn = np.array([-t[1], t[0]])
        sgn = 1 if k % 2 == 0 else -1; pts.append((c.x + nn[0]*hw*sgn, c.y + nn[1]*hw*sgn)); k += 1
    return LineString(pts)
add("FR", [KM.R("kc_glow", zigzag(ring_path, 9.4, 1.3).buffer(0.3, cap_style="round", join_style="round"), "run", None, "GLOW", ko=False)],
    20, "03", unit="03-glow", nok=True)
for i, ((px, py, k), (x, y)) in enumerate(zip(DOTS_CN, dpts)):
    add("FR", KM.ring_dot(x, y, 12.4, "kc_blue" if k == "b" else "kc_mint", "DOTB"), 24, "03", unit=f"03-dot{i}")
# text column: 6 glyphs between the mockup's first + last glyph centres (the AI drew 7 garbled glyphs)
t0 = C(370.0, 690.0); t1 = C(407.5, 867.5)
col_ang = math.degrees(math.atan2(t1[1] - t0[1], t1[0] - t0[0])) - 90
em_cn = 27.0
colm = KL.set_column("cn", kccore.TEXT["03"], em_cn, gap=(math.dist(t0, t1) - 5*em_cn) / 5)
cb = KL.ink_bounds(colm); mid = ((t0[0] + t1[0])/2, (t0[1] + t1[1])/2)
cn = KL.place(colm, *mid, col_ang)
META["badges"]["03"].update(em=em_cn, angle=col_ang)
add("FR", text_regs(cn, "kc_red", "TXF", "03-text"), 26, "03", unit="03-text")

# ================================================================ 04 KR oval  (FL, wearer's left lower front)
K0 = (723.3, 891.8); K = anchor(*K0); KC = K(*K0); KANG = 6.9
a_c, b_c, wr = 117.7*S, 30.7*S, 4.0
add("FL", KM.oval_ring(*KC, a_c + wr/2, b_c + wr/2, wr, "kc_gold", ang=KANG, hl=True, hl_w=1.1, hl_col="kc_lemon"), 25, "04", unit="04-oval")
em_kr = 19.0
kr = KL.place(KL.set_line("kr", kccore.TEXT["04"], em_kr, tracking=3.6), *KC, KANG)
META["badges"]["04"] = dict(anchor_px=K0, centre=KC, angle=KANG, em=em_kr, text=kccore.TEXT["04"], axes=(a_c + wr/2, b_c + wr/2, wr))
add("FL", text_regs(kr, "kc_white", "TXF", "04-text"), 26, "04", unit="04-text")

# ================================================================ 05 star field
SP = json.load(open("out/ref/specks.json"))
BADGE_PX = {   # mockup zones that belong to a badge (not field stars)
    "01": Polygon([(285, 375), (540, 375), (540, 600), (285, 610)]).buffer(0),
    "02": Polygon([(690, 395), (800, 395), (885, 600), (875, 640), (795, 640), (690, 470)]).buffer(0),
    "03": None, "04": Polygon([(600, 852), (845, 852), (845, 930), (600, 930)])}
cn_ring_px = MultiPoint([(px, py) for px, py, _ in DOTS_CN]).convex_hull.buffer(-6)
zip_px = box(540, 300, 570, 1100)
def speck_motif(s, x, y, col="kc_white", unit=None):
    ext = max(s["w"], s["h"])
    if ext >= 5: return KM.sparkle(x, y, min(8.0, max(3.6, ext*S*0.95)), col, unit, grp="STAR")
    return KM.dot(x, y, {2: 1.45, 3: 1.7, 4: 2.0}.get(ext, 1.45), col, unit)
nfield = {"FR": 0, "FL": 0, "SR": 0, "SL": 0}; ncn = 0
# sleeve quads in the mockup (px): top fold at the shoulder, cuff outer, underarm, cuff inner
SLQ = {"SR": dict(A=(203, 428), B=(50, 1240), C=(226, 565), D=(246, 1236)),
       "SL": dict(A=(912, 428), B=(1072, 1240), C=(889, 565), D=(870, 1236))}
g_m, _ = F.pieces("M")
SLV = {P: g_m[kccore.PIECE_CODE[P]] for P in ("SR", "SL")}
def sleeve_front_x(P, y):
    """x of the FRONT underarm seam of sleeve P at pattern y (S01 right sleeve: front half x > 0; S02 mirrored)"""
    sp = SLV[P].sew_poly(); b = sp.bounds
    ln = LineString([(0, y), (b[2] + 5 if P == "SR" else b[0] - 5, y)]).intersection(sp)
    xs = [c[0] for g in getattr(ln, "geoms", [ln]) if not g.is_empty for c in g.coords]
    return (max(xs) if P == "SR" else min(xs)) if xs else 0.0
SL_TOP = {P: SLV[P].sew_poly().bounds[1] for P in SLV}; SL_BOT = {P: SLV[P].sew_poly().bounds[3] for P in SLV}
_SIL = ndi.binary_fill_holes(ndi.binary_opening(MM.mock().min(2) < 235, iterations=2))
SL_Y0, SL_Y1 = 425.0, 1268.0                      # shoulder point .. cuff edge (mockup px)
_INNER = {"SR": ([425, 565, 1100, 1140, 1200, 1268], [203, 226, 240, 245, 221, 190]),
          "SL": ([425, 565, 1100, 1140, 1200, 1268], [912, 887, 875, 873, 898, 930])}
def sleeve_uv(P, px, py):
    """u = shoulder -> cuff, v = 0 at the outer fold (sleeve centre line) .. 1 at the underarm seam, read per mockup row:
    outer = the jacket silhouette, inner = the drop-shoulder seam / side seam."""
    y = int(min(max(py, SL_Y0), SL_Y1 - 1)); xs = np.nonzero(_SIL[y])[0]
    xo = xs.min() if P == "SR" else xs.max()
    xi = np.interp(py, *_INNER[P])
    return (py - SL_Y0) / (SL_Y1 - SL_Y0), min(1.0, max(0.0, (px - xo) / (xi - xo)))
def on_sleeve(P, px, py):
    if py < SL_Y0 or py > SL_Y1: return False
    xi = np.interp(py, *_INNER[P])
    return px < xi - 2 if P == "SR" else px > xi + 2
sleeve_mapped = {"SR": [], "SL": []}
for i, s in enumerate(SP):
    px, py = s["x"], s["y"]; pt = Point(px, py)
    if zip_px.contains(pt) or max(s["w"], s["h"]) > 9: continue
    if any(z is not None and z.contains(pt) for z in BADGE_PX.values()): continue
    if cn_ring_px.contains(pt):           # sparkles inside the CN dot ring are part of badge 03
        x, y = C(px, py); add("FR", speck_motif(s, x, y, unit=f"03-sp{ncn}"), 21, "03", unit=f"03-sp{ncn}"); ncn += 1; continue
    side = None
    for P in ("SR", "SL"):
        if on_sleeve(P, px, py): side = P
    if side:
        u_, v_ = sleeve_uv(side, px, py)
        y = SL_TOP[side] + u_*(SL_BOT[side] - SL_TOP[side]); x = v_*sleeve_front_x(side, y)
        sleeve_mapped[side].append((x, y, s)); continue
    if py < 300: continue                   # hood / above the neck seam
    x, y = MM.P(px, py)
    P = "FR" if x < 0 else "FL"
    add(P, speck_motif(s, x, y, unit=f"05-{P}{nfield[P]}"), 21, "05", unit=f"05-{P}{nfield[P]}"); nfield[P] += 1
# sleeves: mapped front half + seeded back half at the same density and size mix
for P in ("SR", "SL"):
    sp = SLV[P].sew_poly()
    front_half = sp.intersection(box(0, -500, 600, 600) if P == "SR" else box(-600, -500, 0, 600))
    back_half = sp.difference(front_half)
    for (x, y, s) in sleeve_mapped[P]:
        add(P, speck_motif(s, x, y, unit=f"05-{P}{nfield[P]}"), 21, "05", unit=f"05-{P}{nfield[P]}"); nfield[P] += 1
    nf = len(sleeve_mapped[P]); dens = nf / max(front_half.area, 1)
    rng = random.Random(55 if P == "SR" else 66); nb = int(round(dens * back_half.area)); pts = []
    exts = [max(s["w"], s["h"]) for _, _, s in sleeve_mapped[P]] or [3]
    bb = back_half.bounds; tries = 0
    while len(pts) < nb and tries < 20000:
        tries += 1; q = (rng.uniform(bb[0], bb[2]), rng.uniform(bb[1], bb[3]))
        if not back_half.contains(Point(q)) or any(math.dist(q, p) < 9 for p in pts): continue
        pts.append(q)
    for q in pts:
        e = rng.choice(exts); s = dict(w=e, h=e)
        add(P, speck_motif(s, *q, unit=f"05-{P}{nfield[P]}"), 21, "05", unit=f"05-{P}{nfield[P]}"); nfield[P] += 1
    META["counts"][P + "_front_mapped"] = nf; META["counts"][P + "_back_seeded"] = len(pts)
META["counts"].update({k + "_field": v for k, v in nfield.items()}, cn_sparkles=ncn)
META["S"] = S; META["SX"] = MM.SX; META["SY"] = MM.SY
pickle.dump(dict(items=items, meta=META), open("scene.pkl", "wb"))
print({P: len(v) for P, v in items.items()}, META["counts"])
