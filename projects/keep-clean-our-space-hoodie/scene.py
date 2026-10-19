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
import mockmap as MM, front as F, kcmotifs as KM, kclettering as KL, kcsatin as KS

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

def text_regs(glyphs, col, code, unit, cap, rim=False, layer=31):
    """Rev B: one satin column per font stroke (kcsatin); puff text gets a lighter rim column round every stroke edge."""
    core, rims = KM.text_columns(glyphs, col, code, cap, unit, rim=rim)
    return core, rims

def put(piece, pair, layer, el, unit, rim_layer=32):
    core, rim = pair[0], pair[1]
    add(piece, core, layer, el, unit=unit); add(piece, rim, rim_layer, el, unit=unit)

# ================================================================ 01 JP badge  (FR, wearer's right chest)
J0 = (398.75, 491.25); J = anchor(*J0)
JC = J(*J0)
# Rev B (review item 4): the mockup's text runs on a CURVED baseline. Glyph centres measured on the mockup (mint pixels,
# components per glyph, mockup px): each glyph is centred there and turned to the local tangent of a quadratic fitted
# through the centres.
JP_C = [(329.6, 534.7), (351.7, 520.7), (372.4, 502.6), (393.9, 486.8), (417.3, 474.7), (441.6, 460.5), (463.3, 447.5)]
_cx = np.array([c[0] for c in JP_C]); _cy = np.array([c[1] for c in JP_C]); JP_FIT = np.polyfit(_cx, _cy, 2)
def jp_tangent(px): return math.degrees(math.atan(2 * JP_FIT[0] * px + JP_FIT[1]))
em_jp = 22.0
jp = []
for ch, (px, py) in zip(kccore.TEXT["01"], JP_C):
    g, _ = KL.glyph("jp", ch, em_jp); b = g.bounds
    py_fit = float(np.polyval(JP_FIT, px)); cx_, cy_ = J(px, (py + py_fit) / 2)
    g = affinity.translate(g, cx_ - (b[0] + b[2]) / 2, cy_ - (b[1] + b[3]) / 2)
    jp.append((ch, affinity.rotate(g, jp_tangent(px), origin=(cx_, cy_)).buffer(0)))
JANG = jp_tangent(float(np.mean(_cx)))
META["badges"]["01"] = dict(anchor_px=J0, centre=JC, angle=JANG, angle_start=jp_tangent(_cx[0]), angle_end=jp_tangent(_cx[-1]),
                            em=em_jp, text=kccore.TEXT["01"], baseline="quadratic through the 7 measured glyph centres")
jcore, jrim = text_regs(jp, "kc_mint", "PF-TXC", "01-text", "round", rim=True)
jshape = unary_union([r["geom"] for r in jcore + jrim])
add("FR", KM.stipple_band(jshape, "01-glow", outer=4.5, seed=11), 20, "01", unit="01-glow")
BARS_JP = [  # mockup px centre, length px, angle deg (y down), colour  (17 bars, counted on the mockup)
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
    put("FR", KM.bar_rc(cx, cy, max(L*S, w + 1), w, a, col, f"01-bar{i}"), 30, "01", f"01-bar{i}")
put("FR", KM.disc_rc(*J(523.2, 480.0), 9.4, "kc_mint", "01-dot"), 30, "01", "01-dot")
for k, (pos, sz, rot) in enumerate((((395.6, 421.0), 12.0, 0), ((333.3, 459.5), 10.4, -8))):
    hc, hr, _ = KM.heart_rc(*J(*pos), sz, "kc_red", f"01-heart{k}", rot=rot)
    add("FR", hc, 30, "01", unit=f"01-heart{k}"); add("FR", hr, 32, "01", unit=f"01-heart{k}")
# left star with face (two knocked-out eyes), faceted
sx0, sy0 = J(303.8, 501.3); fs, _ = KM.star_facets(sx0, sy0, 14.0, "kc_gold", "01-star0", rot=-12)
eyes = unary_union([Point(sx0 - 7.0*0.2, sy0 - 7.0*0.02).buffer(1.0), Point(sx0 + 7.0*0.2, sy0 - 7.0*0.02).buffer(1.0)])
fs = [dict(r, geom=r["geom"].difference(eyes).buffer(0)) for r in fs]
add("FR", [r for r in fs if not r["geom"].is_empty], 30, "01", unit="01-star0")
# top star (review item 5): slender 5-point star, dark centre pit with a white dot
sx1, sy1 = J(460.0, 391.3)
fs, _ = KM.star_facets(sx1, sy1, 14.4, "kc_gold", "01-star1", rot=6, k=0.30, pit=0.24, round_=0.12)
add("FR", fs, 30, "01", unit="01-star1")
add("FR", KM.dot(sx1, sy1, 1.4, "kc_white", "01-star1", grp="FACE"), 33, "01", unit="01-star1")
# small top-right star: a 4-point sparkle in star gold (mockup)
add("FR", KM.sparkle_cols(*J(482.5, 415.0), 6.0, "kc_gold", "01-star2", code="SPK"), 22, "01", unit="01-star2")
# bottom red star (review item 5): SOLID red, faceted, with a small dark star pit (fabric) in the middle
fs, _ = KM.star_facets(*J(406.3, 563.8), 15.0, "kc_red", "01-star3", rot=10, pit=0.30, pit_shape="star")
add("FR", fs, 30, "01", unit="01-star3")
put("FR", (jcore, jrim), 31, "01", "01-text")

# ================================================================ 02 EN badge  (FL, wearer's left chest)
E0 = (791.0, 516.0); E = anchor(*E0); EC = E(*E0); EANG = 50.0
# Rev B (review item 10): heavier + slightly larger letters (Nunito 1000, em 23) with the mockup's line length (138 mm,
# OUR SPACE measured) and line pitch 28 mm (measured: k-means of the mint pixels across the line direction).
em_en = 23.0; LEN_L2 = 138.0
_l2 = KL.set_line("en", "OUR SPACE", em_en, tracking=0.0); _b = KL.ink_bounds(_l2)
trk = (LEN_L2 - (_b[2] - _b[0])) / (len("OUR SPACE") - 1)
l1 = KL.set_line("en", "KEEP CLEAN", em_en, tracking=trk); l2 = KL.set_line("en", "OUR SPACE", em_en, tracking=trk)
lh = 28.0
u = np.array([math.cos(math.radians(EANG)), math.sin(math.radians(EANG))]); n = np.array([-u[1], u[0]])
c1 = np.array(EC) + np.array([5.0, -2.5]) - n*lh/2; c2 = c1 + n*lh
L1 = KL.place(l1, *c1, EANG); L2 = KL.place(l2, *c2, EANG)
keep = [(ch, g) for ch, g in L1[:4]]; clean = [(ch, g) for ch, g in L1[4:]]
META["badges"]["02"] = dict(anchor_px=E0, centre=EC, angle=EANG, em=em_en, pitch=lh, tracking=round(trk, 2), line2_len=LEN_L2, text="KEEP CLEAN / OUR SPACE")
ecore, erim = text_regs(keep + L2, "kc_mint", "PF-TXC", "02-text", "round", rim=True)
ccore, crim = text_regs(clean, "kc_lemon", "PF-TXC", "02-text", "round", rim=True)
eshape = unary_union([r["geom"] for r in ecore + erim + ccore + crim])
add("FL", KM.stipple_band(eshape, "02-glow", outer=4.5, seed=12), 20, "02", unit="02-glow")
STARS_EN = [(325, 105), (425, 130), (495, 215), (570, 300), (645, 400), (720, 495), (770, 600), (800, 840), (750, 935), (645, 985),
            (540, 910), (460, 815), (385, 720), (305, 625), (225, 530), (140, 430), (115, 310), (195, 190)]      # 18 stars (crop_en2: /4 + (670,380))
for i, (cx_, cy_) in enumerate(STARS_EN):
    px, py = 670 + cx_/4, 380 + cy_/4
    fs, _ = KM.star_facets(*E(px, py), 11.6, "kc_gold", f"02-star{i}", rot=(i*7) % 15 - 7)
    add("FL", fs, 30, "02", unit=f"02-star{i}")
put("FL", (ecore + ccore, erim + crim), 31, "02", "02-text")

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
META["badges"]["03"] = dict(anchor_px=C0, centre=CC, shift=CN_SHIFT, text=kccore.TEXT["03"], dots=len(dpts))
dcores, drims = [], []
for i, ((px, py, k), (x, y)) in enumerate(zip(DOTS_CN, dpts)):
    c_, r_ = KM.disc_rc(x, y, 12.4, "kc_blue" if k == "b" else "kc_mint", f"03-dot{i}", rim_w=1.3, ang=35 + (i * 23) % 50)
    dcores += c_; drims += r_
# glow (review item 2): soft halo round every dot (mockup: green haze round the dots), one connected band
dshape = unary_union([r["geom"] for r in dcores + drims])
add("FR", KM.stipple_band(dshape, "03-glow", outer=3.6, seed=13), 20, "03", unit="03-glow")
add("FR", dcores, 30, "03", unit="03-dots"); add("FR", drims, 32, "03", unit="03-dots")
# text column: 6 glyphs between the mockup's first + last glyph centres (the AI drew 7 garbled glyphs)
t0 = C(370.0, 690.0); t1 = C(407.5, 867.5)
col_ang = math.degrees(math.atan2(t1[1] - t0[1], t1[0] - t0[0])) - 90
em_cn = 27.0
colm = KL.set_column("cn", kccore.TEXT["03"], em_cn, gap=(math.dist(t0, t1) - 5*em_cn) / 5)
mid = ((t0[0] + t1[0])/2, (t0[1] + t1[1])/2)
cn = KL.place(colm, *mid, col_ang)
META["badges"]["03"].update(em=em_cn, angle=col_ang)
put("FR", text_regs(cn, "kc_red", "TXC", "03-text", "flat"), 26, "03", "03-text")

# ================================================================ 04 KR oval  (FL, wearer's left lower front)
K0 = (723.3, 891.8); K = anchor(*K0); KC = K(*K0); KANG = 6.9
a_c, b_c, wr = 117.7*S, 30.7*S, 4.0
add("FL", KM.oval_cols(*KC, a_c + wr/2, b_c + wr/2, wr, "kc_gold", ang=KANG, hl_col="kc_lemon", unit="04-oval"), 25, "04", unit="04-oval")
add("FL", [], 27, "04")
em_kr = 19.0; trk_kr = 2.4
kr = KL.place(KL.set_line("kr", kccore.TEXT["04"], em_kr, tracking=trk_kr), *KC, KANG)
META["badges"]["04"] = dict(anchor_px=K0, centre=KC, angle=KANG, em=em_kr, tracking=trk_kr, text=kccore.TEXT["04"], axes=(a_c + wr/2, b_c + wr/2, wr))
put("FL", text_regs(kr, "kc_white", "TXC", "04-text", "flat"), 26, "04", "04-text")
# ornaments (review item 7): the mockup's non-text marks are kept — the 'i'-arrow mark at the left end (vertical stem,
# diamond head, arrow foot) and two accent marks (a tick above the line, a dot below), white. The mark sits 3.5 mm left
# of the upright text, centred on the line (the mockup's mark is where its mirrored text began).
def korn(px, py): return K(px, py)
ux, uy = math.cos(math.radians(KANG)), math.sin(math.radians(KANG)); vx, vy = -uy, ux        # u along the line, v down
tu = unary_union([g for _, g in kr]); proj = [((x - KC[0]) * ux + (y - KC[1]) * uy) for x, y in tu.exterior.coords] if tu.geom_type == "Polygon" else \
     [((x - KC[0]) * ux + (y - KC[1]) * uy) for g in tu.geoms for x, y in g.exterior.coords]
s_left = min(proj) - 3.5 - 1.7
ax_, ay_ = KC[0] + ux * s_left, KC[1] + uy * s_left
stem = [(ax_ - vx*3.4, ay_ - vy*3.4), (ax_ + vx*3.2, ay_ + vy*3.2)]
orn = [KS.column_region("kc_white", "ORN", stem, 1.15, ("flat", "flat"), unit="04-orn")]
dh = (ax_ - vx*5.0, ay_ - vy*5.0)
orn += KM.sparkle_cols(*dh, 3.2, "kc_white", "04-orn", rot=KANG, code="SPK")
foot = (ax_ + vx*5.0, ay_ + vy*5.0)
for sgn in (-1, 1):
    orn.append(KS.column_region("kc_white", "ORN", [(foot[0] + ux*1.7*sgn - vx*1.9, foot[1] + uy*1.7*sgn - vy*1.9), foot], 1.0, ("flat", "round"), unit="04-orn"))
tk = korn(732.0, 879.0); orn.append(KS.column_region("kc_white", "ORN", [(tk[0] - ux*1.1 - vx*1.0, tk[1] - uy*1.1 - vy*1.0), (tk[0] + ux*1.1 + vx*1.0, tk[1] + uy*1.1 + vy*1.0)], 1.0, ("round", "round"), unit="04-orn"))
orn += KM.dot(*korn(731.0, 914.0), 1.5, "kc_white", "04-orn", grp="DOT")
add("FL", orn, 26, "04", unit="04-orn")
META["badges"]["04"]["ornaments"] = ["i-arrow mark (stem 1.15 + diamond sparkle 3.4 + arrow foot)", "accent tick 1.0 × 3", "accent dot Ø 1.5"]

# ================================================================ 05 star field
SP = json.load(open("out/ref/specks.json"))
BADGE_PX = {   # mockup zones that belong to a badge (not field stars)
    "01": Polygon([(285, 375), (540, 375), (540, 600), (285, 610)]).buffer(0),
    "02": Polygon([(690, 395), (800, 395), (885, 600), (875, 640), (795, 640), (690, 470)]).buffer(0),
    "03": None, "04": Polygon([(600, 852), (845, 852), (845, 930), (600, 930)])}
cn_ring_px = MultiPoint([(px, py) for px, py, _ in DOTS_CN]).convex_hull.buffer(-6)
zip_px = box(540, 300, 570, 1100)
SPAN = lambda ext: min(8.5, max(4.0, (ext + 1.5) * S))      # Rev B (item 9): a 1 px/mm render under-reads the thin arms
def speck_motif(s, x, y, col="kc_white", unit=None):
    """ext >= 5 px: concave 4-point sparkle (two tapered columns) + soft haze under it; smaller: satin dot"""
    ext = max(s["w"], s["h"])
    if ext >= 5:
        sp = SPAN(ext); rot = ((x * 13 + y * 7) % 9) - 4
        st = KM.sparkle_cols(x, y, sp, col, unit, rot=rot)
        return KM.haze(x, y, 0.55 * sp, unit, star=unary_union([r["geom"] for r in st])) + st
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
EXCL = dict(zip=0, big_glint=0, in_badge=0, hood=0)
for i, s in enumerate(SP):
    px, py = s["x"], s["y"]; pt = Point(px, py)
    if zip_px.contains(pt): EXCL["zip"] += 1; continue
    if max(s["w"], s["h"]) > 9: EXCL["big_glint"] += 1; continue
    if any(z is not None and z.contains(pt) for z in BADGE_PX.values()): EXCL["in_badge"] += 1; continue
    if cn_ring_px.contains(pt):           # sparkles inside the CN dot ring are part of badge 03
        x, y = C(px, py); add("FR", speck_motif(s, x, y, unit=f"03-sp{ncn}"), 21, "03", unit=f"03-sp{ncn}"); ncn += 1; continue
    side = None
    for P in ("SR", "SL"):
        if on_sleeve(P, px, py): side = P
    if side:
        u_, v_ = sleeve_uv(side, px, py)
        y = SL_TOP[side] + u_*(SL_BOT[side] - SL_TOP[side]); x = v_*sleeve_front_x(side, y)
        sleeve_mapped[side].append((x, y, s)); continue
    if py < 300: EXCL["hood"] += 1; continue          # hood / above the neck seam (hood plain, PROPOSED)
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
META["counts"].update({k + "_field": v for k, v in nfield.items()}, cn_sparkles=ncn, specks_detected=len(SP), **{"excluded_" + k: v for k, v in EXCL.items()})
spans = [SPAN(max(s["w"], s["h"])) for s in SP if 5 <= max(s["w"], s["h"]) <= 9]
META["counts"]["sparkle_spans"] = dict(n=len(spans), lt5=sum(1 for v in spans if v < 5), s5_8=sum(1 for v in spans if 5 <= v <= 8), gt8=sum(1 for v in spans if v > 8))
META["S"] = S; META["SX"] = MM.SX; META["SY"] = MM.SY
pickle.dump(dict(items=items, meta=META), open("scene.pkl", "wb"))
print({P: len(v) for P, v in items.items()}, META["counts"])
