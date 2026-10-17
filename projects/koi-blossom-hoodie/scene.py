"""Koi blossom scene — composed on the size-M pieces (garment / pattern mm, unclipped).
Every motif position, size and direction is read from the mockup (inputs/front.png, px) — counted, not traced
(LESSONS A2/A10): 18 koi, 7 flowers, ~60 leaves, 33 floating petals. Detail comes from the close-up
(inputs/closeup_mockup_koi.png) via kb_motifs.  Output: scene.pkl = {"items": {piece: [...]}, "meta": {...}}.
usage: python3 scene.py"""
import kbcore
import math, random, pickle, json
import numpy as np
from shapely.geometry import Point
from shapely.ops import unary_union
import mockmap as MM, front as F, kb_motifs as KM, kbvis

G_M, MT_M = F.pieces("M")
S = MM.S                                   # mm per mockup px for motif sizes (fronts + sleeves)

def piece_of(px, py):
    """which piece a mockup point lies on (fronts split at the zip; sleeves by the drawn sleeve edges)"""
    for P in ("SR", "SL"):
        sp = MM.SLEEVE_PX[P]; o = np.array(sp["outer"]); i = np.array(sp["inner"])
        yo = np.interp(py, o[:, 1], o[:, 0]); yi = np.interp(py, i[:, 1], i[:, 0])
        if min(yo, yi) <= px <= max(yo, yi) and py > min(o[0, 1], i[0, 1]) + (0 if P == "SR" else 0): return P
    return "FR" if px < MM.CFX else "FL"

def to_mm(P, px, py):
    if P in ("FR", "FL"): return MM.P(px, py)
    return MM.sleeve_P(P, px, py, MT_M)

ITEMS = {P: [] for P in kbcore.PIECES}
UNITS = {}                                 # unit -> dict(kind, piece, cluster)
def add(P, regs, zbase, layer, unit, kind, cluster=None, ko=True):
    UNITS[unit] = dict(kind=kind, piece=P, cluster=cluster)
    for r in regs:
        if r["geom"].is_empty: continue
        r = dict(r, geom=kbvis.fix(r["geom"]))
        sub = r.get("sub", 0)
        r["z"] = zbase + sub + len(ITEMS[P]) * 1e-4
        lay = layer
        if kind == "koi": lay = {1: 24.1, 2: 24.2, 3: 24.3, 4: 24.4, 5: 24.5, 6: 24.6}[sub]
        if kind == "flower": lay = 22.2 if r["grp"] in ("FL-cup", "FL-eye", "FL-stamen") else 22.0
        if r["grp"] in ("KO-ray", "LF-vein"): r["ko"] = False
        else: r.setdefault("ko", ko)
        r["layer"] = lay; r["unit"] = unit; r["cluster"] = cluster; r["el"] = kbcore.ELEM_OF[P]
        r.setdefault("kob", 0.0)
        ITEMS[P].append(r)

def ang_of(P, a, b):
    A, B = np.array(to_mm(P, *a)), np.array(to_mm(P, *b))
    d = B - A; return math.degrees(math.atan2(d[1], d[0])), float(np.hypot(*d)), A

# ================================================================ koi (head px, tail px, red pattern, bend)
KOI = [((255, 371), (201, 344), 0, 2), ((286, 424), (245, 395), 2, -2), ((343, 483), (297, 450), 1, 2), ((283, 499), (215, 465), 0, 3),
       ((322, 565), (277, 515), 3, -2), ((335, 703), (286, 663), 1, 2),                                      # FR
       ((582, 486), (541, 476), 2, 1), ((546, 505), (500, 501), 0, -1), ((509, 533), (461, 528), 1, 1), ((472, 563), (412, 535), 0, 2),
       ((591, 567), (547, 550), 2, -1), ((462, 648), (414, 601), 3, 2), ((535, 709), (474, 676), 1, -2),     # FL
       ((51, 540), (89, 489), 3, 2), ((105, 671), (57, 626), 0, -2), ((79, 811), (50, 753), 2, 2),            # SR
       ((707, 756), (680, 669), 3, -3), ((651, 813), (615, 861), 1, 2)]                                       # SL
rng = random.Random(11)
koi_info = []
for i, (hd, tl, pat, bend) in enumerate(KOI):
    P = piece_of(*hd)
    a, L, A = ang_of(P, tl, hd)
    Lpx = math.hypot(hd[0] - tl[0], hd[1] - tl[1]); Lmm = max(50.0, Lpx * S * 0.98)      # tails read short in the render
    c = np.array(to_mm(P, (hd[0] + tl[0]) / 2, (hd[1] + tl[1]) / 2))
    u = f"koi{i}"
    regs, sil = KM.koi(c[0], c[1], Lmm, a, rng, pattern=pat, bend=bend, unit=u)
    add(P, regs, 5000 + i*10, 24, u, "koi"); koi_info.append(dict(piece=P, unit=u, L=round(Lmm, 1), c=c.tolist(), ang=a))

# ================================================================ flower clusters (flowers, leaves, stems), px from the mockup
# leaf = (base px, tip px, tone, bend); flower = (centre px, R px, tones, rot, n)
CLUSTERS = {
 "FR_vine": dict(
    flowers=[((195, 438), 46, "pale", -95, 5), ((222, 500), 31, "mid", -60, 5)],
    stems=[([(208, 512), (186, 545), (168, 585), (150, 625), (138, 665), (128, 708)], 2.6, 1.3, "kb_navy"),
           ([(171, 580), (194, 561), (215, 547), (238, 541)], 1.6, 1.0, "kb_cobalt"),
           ([(150, 626), (170, 616), (186, 606)], 1.4, 1.0, "kb_cobalt"),
           ([(205, 470), (185, 450), (168, 425)], 1.5, 1.0, "kb_cobalt")],
    leaves=[((176, 428), (150, 392), "cobalt", 0.08), ((178, 452), (134, 474), "royal", -0.08), ((186, 482), (160, 505), "blue", 0.06),
            ((206, 512), (178, 528), "royal", 0.05), ((232, 512), (262, 534), "cobalt", -0.06), ((214, 522), (203, 560), "navy", 0.07),
            ((163, 592), (158, 543), "ice", 0.06), ((152, 606), (125, 572), "sky", -0.05), ((165, 596), (200, 578), "ice", 0.08),
            ((194, 563), (222, 574), "ice", -0.06), ((212, 547), (228, 522), "ice", 0.05), ((150, 622), (130, 642), "royal", 0.05),
            ((168, 612), (196, 600), "cobalt", -0.06), ((160, 618), (192, 630), "cobalt", 0.06), ((140, 652), (172, 646), "ice", -0.08),
            ((139, 660), (124, 628), "sky", 0.06), ((134, 690), (150, 714), "cobalt", 0.05), ((131, 682), (117, 703), "royal", -0.05),
            ((142, 666), (162, 690), "navy", 0.06), ((182, 548), (170, 520), "blue", -0.06), ((236, 540), (252, 528), "sky", 0.04),
            # denser vine (mockup: dark leaves fill the stem from the lilies to below the welt)
            ((190, 540), (165, 525), "cobalt", 0.05), ((176, 568), (148, 556), "royal", -0.05), ((172, 584), (150, 590), "navy", 0.05),
            ((158, 612), (140, 600), "cobalt", -0.05), ((146, 640), (124, 650), "royal", 0.05), ((143, 646), (160, 662), "cobalt", -0.05),
            ((133, 676), (148, 690), "royal", 0.05), ((130, 700), (116, 720), "cobalt", -0.05), ((129, 706), (142, 728), "navy", 0.05),
            ((200, 522), (230, 508), "royal", 0.05), ((165, 470), (140, 455), "cobalt", -0.06), ((170, 405), (160, 380), "royal", 0.06),
            ((200, 470), (215, 450), "cobalt", 0.05), ((228, 528), (250, 552), "royal", -0.05), ((180, 520), (162, 545), "navy", 0.05)]),
 "FR_bot": dict(
    flowers=[((326, 745), 26, "mid", -100, 5)],
    stems=[([(300, 738), (316, 752), (330, 758)], 1.6, 1.0, "kb_navy")],
    leaves=[((318, 750), (294, 745), "ice", 0.06), ((321, 763), (298, 769), "sky", -0.06), ((330, 728), (336, 708), "royal", 0.05),
            ((338, 762), (350, 772), "cobalt", 0.04)]),
 "FL_bot": dict(
    flowers=[((482, 735), 40, "light", -85, 6), ((560, 744), 27, "dark", -70, 6)],
    stems=[([(470, 758), (510, 767), (556, 765)], 1.8, 1.1, "kb_navy"),
           ([(568, 742), (594, 726), (601, 695), (601, 660), (594, 628)], 2.0, 1.0, "kb_cobalt")],
    leaves=[((448, 738), (397, 728), "sky", -0.06), ((446, 722), (413, 705), "blue", 0.06), ((456, 706), (424, 690), "blue", -0.05),
            ((462, 722), (458, 690), "royal", 0.06), ((452, 760), (410, 762), "royal", 0.05), ((466, 768), (440, 776), "cobalt", -0.04),
            ((500, 768), (540, 760), "ice", -0.06), ((594, 650), (588, 615), "royal", 0.05), ((594, 668), (566, 656), "blue", -0.05),
            ((597, 664), (614, 640), "blue", 0.05), ((591, 700), (568, 684), "ice", 0.05), ((597, 702), (614, 722), "royal", -0.05),
            ((590, 628), (578, 606), "cobalt", 0.04), ((599, 708), (612, 690), "sky", -0.04),
            ((578, 764), (602, 748), "royal", 0.05), ((548, 770), (520, 780), "ice", -0.05), ((596, 726), (612, 738), "cobalt", 0.04)]),
 "SR_cuff": dict(
    flowers=[((45, 868), 25, "mid", -80, 6)],
    stems=[([(45, 870), (48, 842), (55, 815)], 1.5, 1.0, "kb_cobalt")],
    leaves=[((40, 846), (25, 822), "blue", 0.06), ((51, 840), (57, 818), "ice", -0.05), ((66, 852), (91, 829), "blue", 0.06),
            ((68, 866), (113, 866), "blue", -0.05), ((62, 885), (92, 893), "blue", 0.05), ((28, 862), (12, 862), "cobalt", 0.04)]),
}
rng = random.Random(23)
cl_info = {}
for cname, cl in CLUSTERS.items():
    P = piece_of(*cl["flowers"][0][0])
    n_l = 0
    for k, (pts, w0, w1, col) in enumerate(cl["stems"]):
        mm = [to_mm(P, *p) for p in pts]; u = f"{cname}_stem{k}"
        regs, _ = KM.stem(mm, w0, w1, col, unit=u); add(P, regs, 1000 + k, 20, u, "stem", cname)
    for k, (b, t, tone, bend) in enumerate(cl["leaves"]):
        a, L, A = ang_of(P, b, t); u = f"{cname}_leaf{k}"
        regs, _ = KM.leaf(A[0], A[1], L, a, rng, tone, bend=bend, unit=u); add(P, regs, 2000 + k*5, 21, u, "leaf", cname); n_l += 1
    for k, (c, Rpx, tones, rot, n) in enumerate(cl["flowers"]):
        cm = to_mm(P, *c); u = f"{cname}_flower{k}"
        regs, _ = KM.flower(cm[0], cm[1], Rpx * S, rot, rng, tones, n=n, unit=u); add(P, regs, 3000 + k*100, 22, u, "flower", cname)
    cl_info[cname] = dict(piece=P, flowers=len(cl["flowers"]), leaves=n_l, stems=len(cl["stems"]))

# ================================================================ floating petals (centre px, length px, tip angle deg in px space, tone)
PETALS = [
 (229, 310, 14, 40, "sky"), (241, 313, 18, -5, "ice"), (186, 354, 22, 30, "sky"), (214, 384, 10, -70, "white"), (225, 378, 12, -45, "white"),
 (214, 405, 18, 30, "ice"), (283, 337, 16, -60, "ice"), (320, 406, 20, 25, "ice"), (245, 431, 11, 60, "white"), (246, 446, 13, 70, "white"),
 (279, 462, 24, 70, "blue"), (302, 494, 11, 60, "royal"), (262, 512, 20, -30, "ice"), (275, 577, 24, 50, "sky"), (284, 618, 24, 95, "ice"),
 (240, 545, 18, 165, "white"), (231, 578, 10, 160, "royal"), (230, 668, 18, 30, "blue"), (285, 730, 26, 55, "white"),          # FR 19
 (402, 490, 28, 25, "ice"), (449, 522, 7, -60, "white"), (548, 494, 12, -30, "sky"), (405, 585, 18, -70, "sky"), (443, 584, 12, 40, "blue"),
 (472, 613, 12, -80, "royal"), (505, 568, 18, -15, "sky"), (532, 569, 18, 5, "sky"), (565, 640, 14, 45, "ice"),                 # FL 9
 (65, 591, 26, 180, "sky"), (63, 756, 24, -80, "sky"), (88, 768, 20, -80, "sky"), (100, 792, 22, -60, "sky"),                   # SR 4
 (658, 582, 26, 35, "sky"), (676, 622, 26, 100, "white"), (686, 625, 14, 100, "royal"), (662, 705, 18, -80, "sky"), (668, 784, 30, 125, "sky")]  # SL 5
TONE = {"white": "ice", "ice": "ice", "sky": "sky", "blue": "blue", "royal": "royal"}
rng = random.Random(5)
pet_info = []
for k, (px, py, Lpx, apx, tone) in enumerate(PETALS):
    P = piece_of(px, py)
    a_ = math.radians(apx); d = 0.5 * Lpx
    a, L, A = ang_of(P, (px - math.cos(a_)*d, py - math.sin(a_)*d), (px + math.cos(a_)*d, py + math.sin(a_)*d))
    L = max(L, 9.0) if tone != "white" else max(L, 8.0)
    u = f"petal{k}"
    regs, _ = KM.float_petal(A[0], A[1], L * 1.05, a, rng, TONE[tone], unit=u)
    if tone == "white":
        for r in regs:
            r["col"] = {"kb_ice": "kb_white", "kb_white": "kb_cream", "kb_sky": "kb_cream"}.get(r["col"], r["col"])
    add(P, regs, 4000 + k, 23, u, "petal"); pet_info.append(dict(piece=P, unit=u, L=round(L, 1)))

META = dict(koi=koi_info, clusters=cl_info, petals=pet_info,
            counts={P: dict(koi=sum(1 for k in koi_info if k["piece"] == P), petals=sum(1 for p in pet_info if p["piece"] == P),
                            flowers=sum(c["flowers"] for c in cl_info.values() if c["piece"] == P),
                            leaves=sum(c["leaves"] for c in cl_info.values() if c["piece"] == P)) for P in kbcore.PIECES},
            mock_map=dict(cfx=MM.CFX, necky=MM.NECKY, sx=MM.SX, sy=MM.SY, s=MM.S), units=UNITS)
pickle.dump(dict(items=ITEMS, meta=META), open("scene.pkl", "wb"))
print({P: len(v) for P, v in ITEMS.items()}, META["counts"])
