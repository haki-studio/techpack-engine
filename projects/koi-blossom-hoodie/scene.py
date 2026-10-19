"""Blossom tetra scene (slug koi-blossom-hoodie) — composed on the size-M pieces (garment / pattern mm, unclipped).
Every motif position, size and direction is read from the mockup (inputs/front.png, px) — counted, not traced
(LESSONS A2/A10): 18 fish, 7 flowers, ~85 leaves, 37 floating petals.  Rev B: motif STRUCTURE is traced from the close-up
(inputs/closeup_mockup_koi.png -> cu_trace.py -> trace/templates.pkl, A12/A13): lilies (petal outlines + tone regions,
throat, anthers) and free-petal shapes, each mapped onto its mockup
position (cu_register.py: the close-up drifted ~13 mm, so positions come from the mockup).  Output: scene.pkl = {"items": {piece: [...]}, "meta": {...}}.
usage: python3 scene.py"""
import kbcore
import math, random, pickle, json
import numpy as np
from shapely.geometry import Point
from shapely.ops import unary_union
import mockmap as MM, front as F, kb_motifs as KM, kb_traced as KT, kb_fish as KF, kbvis, json

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
        if kind == "fish": lay = 24.0 + sub / 10.0          # tail + fins -> body facets -> lines -> pectoral -> ring -> eye
        if kind == "flower": lay = 22.2 if r["grp"] in ("FL-cup", "FL-eye", "FL-stamen") else 22.0
        if r["grp"] in ("KO-ray", "LF-vein"): r["ko"] = False
        else: r.setdefault("ko", ko)
        r["layer"] = lay; r["unit"] = unit; r["cluster"] = cluster; r["el"] = kbcore.ELEM_OF[P]
        r.setdefault("kob", 0.0)
        ITEMS[P].append(r)

def ang_of(P, a, b):
    A, B = np.array(to_mm(P, *a)), np.array(to_mm(P, *b))
    d = B - A; return math.degrees(math.atan2(d[1], d[0])), float(np.hypot(*d)), A

# ================================================================ fish (head px, tail px, -, -) — FOUNDER CHANGE 19 Oct 2026: tetras, not koi
# Positions + headings = the mockup's fish (former koi); proportions from inputs/reference_fish.png (slimmer + shorter):
# length = 0.82 x the mockup fish length (min 40 mm), belly kept on the lower side (kb_fish.fish mirrors leftward swimmers).
KOI = [((255, 371), (201, 344), 0, 2), ((286, 424), (245, 395), 2, -2), ((343, 483), (297, 450), 1, 2), ((283, 499), (215, 465), 0, 3),
       ((322, 565), (277, 515), 3, -2), ((335, 703), (286, 663), 1, 2),                                      # FR
       ((582, 486), (541, 476), 2, 1), ((546, 505), (500, 501), 0, -1), ((509, 533), (461, 528), 1, 1), ((472, 563), (412, 535), 0, 2),
       ((591, 567), (547, 550), 2, -1), ((462, 648), (414, 601), 3, 2), ((535, 709), (474, 676), 1, -2),     # FL
       ((51, 540), (89, 489), 3, 2), ((105, 671), (57, 626), 0, -2), ((79, 811), (50, 753), 2, 2),            # SR
       ((707, 756), (680, 669), 3, -3), ((651, 813), (615, 861), 1, 2)]                                       # SL
rng = random.Random(11)
fish_info = []; KOI_MM = {}
for i, (hd, tl, pat, bend) in enumerate(KOI):
    P = piece_of(*hd)
    a, L, A = ang_of(P, tl, hd)
    Lpx = math.hypot(hd[0] - tl[0], hd[1] - tl[1]); Lmm = max(40.0, Lpx * S * 0.98 * 0.82)
    c = np.array(to_mm(P, (hd[0] + tl[0]) / 2, (hd[1] + tl[1]) / 2))
    u = f"fish{i}"
    regs, sil = KF.fish(c[0], c[1], Lmm, a, unit=u)
    KOI_MM.setdefault(P, []).append((list(to_mm(P, *hd)), list(to_mm(P, *tl))))
    add(P, regs, 5000 + i*10, 24, u, "fish"); fish_info.append(dict(piece=P, unit=u, L=round(Lmm, 1), c=c.tolist(), ang=a))

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
            ((338, 762), (350, 772), "cobalt", 0.04),
            # Rev B: dark-blue leaves beside the FR hem flower (mockup)
            ((306, 758), (284, 774), "navy", 0.05), ((340, 742), (354, 722), "cobalt", -0.05), ((312, 736), (298, 716), "navy", 0.05),
            ((344, 768), (362, 782), "royal", -0.04)]),
 "FL_bot": dict(
    flowers=[((482, 735), 40, "light", -85, 6), ((560, 744), 27, "dark", -70, 6)],
    stems=[([(470, 758), (510, 767), (556, 765)], 1.8, 1.1, "kb_navy"),
           ([(568, 742), (594, 726), (601, 695), (601, 660), (594, 628)], 2.0, 1.0, "kb_cobalt")],
    leaves=[((448, 738), (397, 728), "sky", -0.06), ((446, 722), (413, 705), "blue", 0.06), ((456, 706), (424, 690), "blue", -0.05),
            ((462, 722), (458, 690), "royal", 0.06), ((452, 760), (410, 762), "royal", 0.05), ((466, 768), (440, 776), "cobalt", -0.04),
            ((500, 768), (540, 760), "ice", -0.06), ((594, 650), (588, 615), "royal", 0.05), ((594, 668), (566, 656), "blue", -0.05),
            ((597, 664), (614, 640), "blue", 0.05), ((591, 700), (568, 684), "ice", 0.05), ((597, 702), (614, 722), "royal", -0.05),
            ((590, 628), (578, 606), "cobalt", 0.04), ((599, 708), (612, 690), "sky", -0.04),
            ((578, 764), (602, 748), "royal", 0.05), ((548, 770), (520, 780), "ice", -0.05), ((596, 726), (612, 738), "cobalt", 0.04),
            # Rev B (review item 7, mockup counts): more leaves round the lily, the dark flower and up the right-hand vine
            ((520, 752), (545, 738), "cobalt", 0.05), ((515, 772), (538, 786), "navy", -0.05), ((470, 705), (462, 680), "royal", 0.05),
            ((440, 748), (418, 754), "cobalt", -0.05), ((585, 735), (600, 715), "navy", 0.05), ((560, 765), (585, 778), "cobalt", -0.04),
            ((600, 690), (618, 676), "navy", 0.05), ((592, 645), (575, 628), "blue", -0.05)]),
 "SR_cuff": dict(
    flowers=[((45, 868), 25, "mid", -80, 6)],
    stems=[([(45, 870), (48, 842), (55, 815)], 1.5, 1.0, "kb_cobalt")],
    leaves=[((40, 846), (25, 822), "blue", 0.06), ((51, 840), (57, 818), "ice", -0.05), ((66, 852), (91, 829), "blue", 0.06),
            ((68, 866), (113, 866), "blue", -0.05), ((62, 885), (92, 893), "blue", 0.05), ((28, 862), (12, 862), "cobalt", 0.04)]),
}
rng = random.Random(23)
cl_info = {}
# which traced lily each mockup flower uses: (template, tone shift (+ = darker), mirror, rotation deg)
LILY = {("FR_vine", 0): ("cu_lily0", 0, False, 0.0),    # = close-up flower 1 (big pale lily)
        ("FR_vine", 1): ("cu_lily1", 0, False, 0.0),    # = close-up flower 2 (mid lily)
        ("FR_bot", 0): ("cu_lily1", 0, True, 15.0),
        ("FL_bot", 0): ("cu_lily0", 0, True, 0.0),      # big light lily at the FL hem
        ("FL_bot", 1): ("cu_lily1", 1, False, -20.0),   # dark flower
        ("SR_cuff", 0): ("cu_lily1", 0, True, 10.0)}
lily_info = []
for cname, cl in CLUSTERS.items():
    P = piece_of(*cl["flowers"][0][0])
    n_l = 0
    for k, (pts, w0, w1, col) in enumerate(cl["stems"]):
        mm = [to_mm(P, *p) for p in pts]; u = f"{cname}_stem{k}"
        regs, _ = KM.stem(mm, w0, w1, col, unit=u); add(P, regs, 1000 + k, 20, u, "stem", cname)
    for k, (b, t, tone, bend) in enumerate(cl["leaves"]):
        a, L, A = ang_of(P, b, t); u = f"{cname}_leaf{k}"
        regs, _ = KM.leaf(A[0], A[1], L, a, rng, tone, bend=bend, unit=u, lit=(cname == "FR_vine" and tone in ("ice", "sky", "blue", "royal"))); add(P, regs, 2000 + k*5, 21, u, "leaf", cname); n_l += 1
    for k, (c, Rpx, tones, rot, n) in enumerate(cl["flowers"]):
        cm = to_mm(P, *c); u = f"{cname}_flower{k}"
        tpl, shift, mir, rot2 = LILY[(cname, k)]
        regs, _ = KT.lily(tpl, cm[0], cm[1], 0.9 * Rpx * S, rot=rot2, mirror=mir, shift=shift, unit=u); add(P, regs, 3000 + k*100, 22, u, "flower", cname)
        lily_info.append(dict(unit=u, piece=P, c=[float(cm[0]), float(cm[1])], template=tpl, shift=shift, mirror=mir, rot=rot2, R=round(0.9 * Rpx * S, 1), close_up=(cname, k) in (("FR_vine", 0), ("FR_vine", 1))))
    # stems run BEHIND the lilies: no stem line through the gaps between petals
    fl_sil = unary_union([r["geom"] for r in ITEMS[P] if r.get("cluster") == cname and r["unit"].split("_")[-1].startswith("flower")]).buffer(1.5)
    for r in ITEMS[P]:
        if r.get("cluster") == cname and r["grp"] == "ST": r["geom"] = r["geom"].difference(fl_sil).buffer(0)
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
PTONE = {"white": ("kb_cream", "kb_white"), "ice": ("kb_sky", "kb_ice"), "sky": ("kb_blue", "kb_sky"), "blue": ("kb_royal", "kb_blue"), "royal": ("kb_cobalt", "kb_royal")}
rng = random.Random(5)
pet_info = []
for k, (px, py, Lpx, apx, tone) in enumerate(PETALS):
    P = piece_of(px, py)
    a_ = math.radians(apx); d = 0.5 * Lpx
    a, L, A = ang_of(P, (px - math.cos(a_)*d, py - math.sin(a_)*d), (px + math.cos(a_)*d, py + math.sin(a_)*d))
    L = max(L, 9.0) if tone != "white" else max(L, 8.0)
    u = f"petal{k}"
    regs, _ = KT.petal(k, A[0], A[1], L * 1.05, a, rng, PTONE[tone], unit=u)
    add(P, regs, 4000 + k, 23, u, "petal"); pet_info.append(dict(piece=P, unit=u, L=round(L, 1)))


# ================================================================ A14/A15 (19 Oct 2026): every flora silhouette traced from the mockup
# The mockup's flora pixels (mockref.flora_mask: garment details, background, mockup koi masked out FIRST) give one
# silhouette per motif / cluster. Floating petals = the traced silhouettes themselves (two tones split on their axis,
# tones from the mockup's luminance); clusters = the leaf / stem / lily objects CLIPPED to the traced cluster silhouette,
# and whatever of the silhouette they leave bare FILLED with the mockup's own tone regions ("traced fill").
# The two FR lilies traced from the close-up (A12/A13) are kept as traced there (their reference is the close-up).
import mockref as MR
from shapely.geometry import Point as _Pt, Polygon
PROTECT = {"FR_vine_flower0", "FR_vine_flower1"}
TRACE = {}
def _pet_tones(Lm):
    if Lm > 195: return ("kb_cream", "kb_white")
    if Lm > 165: return ("kb_sky", "kb_ice")
    if Lm > 125: return ("kb_blue", "kb_sky")
    return ("kb_cobalt", "kb_royal")
pet_info = []
for P in kbcore.PIECES:
    emb, tone, bb = MR.flora_mask(P, KOI_MM.get(P, []), mt=MT_M); Lm = MR.lum(P)
    sils = MR.polys_of(emb, bb, min_mm2=4.0)
    flora = [r for r in ITEMS[P] if r["unit"].split("_")[-1].startswith(("leaf", "stem", "flower"))]
    prot = unary_union([r["geom"] for r in flora if r["unit"] in PROTECT]) if any(r["unit"] in PROTECT for r in flora) else None
    cl_geoms = [r["geom"] for r in flora]
    flora_u = unary_union(cl_geoms) if cl_geoms else None
    petals, clusters = [], []
    for sgeo in sils:
        if prot is not None and sgeo.buffer(-0.5).intersection(prot).area > 0.5 * sgeo.area: continue      # the close-up lily itself
        near = flora_u is not None and sgeo.intersection(flora_u).area > 0.25 * sgeo.area
        if prot is not None and sgeo.area < 150 and sgeo.distance(prot) < 1.0: continue   # inside the close-up lily's zone: the close-up governs
        (clusters if (sgeo.area >= 150 or near) else petals).append(sgeo)
    # floating petals: drop the generated ones, add the traced silhouettes
    ITEMS[P] = [r for r in ITEMS[P] if not r["unit"].startswith("petal")]
    for k, sgeo in enumerate(petals):
        H_, W_ = Lm.shape
        m = MR.raster([sgeo], bb); lm = float(Lm[m].mean()) if m.any() else 150.0
        mrr = sgeo.minimum_rotated_rectangle; cs = np.array(mrr.exterior.coords); e = [cs[i + 1] - cs[i] for i in range(2)]
        ax = e[0] if np.hypot(*e[0]) >= np.hypot(*e[1]) else e[1]; ax = ax / np.hypot(*ax); c = sgeo.centroid
        cut = Polygon([(c.x - ax[0] * 200, c.y - ax[1] * 200), (c.x + ax[0] * 200, c.y + ax[1] * 200),
                       (c.x + ax[0] * 200 - ax[1] * 200, c.y + ax[1] * 200 + ax[0] * 200), (c.x - ax[0] * 200 - ax[1] * 200, c.y - ax[1] * 200 + ax[0] * 200)])
        dk, lt = _pet_tones(lm); u = f"petal_{P}{k}"
        sg = sgeo.buffer(-0.2 if sgeo.area >= 8 else -0.32)    # stitched = traced: the engine adds ~0.2 mm pull compensation per side (tiny dots grow more)
        if sgeo.area < 15:                      # small petals: one tone (two halves would be under the 0.7 mm min width)
            regs = [dict(col=lt, geom=sg, st="satin", ang="auto", grp="PT", sub=0)]
        else:
            regs = [dict(col=dk, geom=sg.intersection(cut).buffer(0), st="satin", ang="auto", grp="PT", sub=0),
                    dict(col=lt, geom=sg.difference(cut).buffer(0), st="satin", ang="auto", grp="PT-tone", sub=0)]
        add(P, [r for r in regs if not r["geom"].is_empty], 4000 + k, 23, u, "petal")
        pet_info.append(dict(piece=P, unit=u, L=round(float(max(np.hypot(*e[0]), np.hypot(*e[1]))), 1), traced=True))
    # clusters: clip the drawn objects to the traced silhouette, fill what they leave bare with the mockup's tones
    C = unary_union(clusters) if clusters else Polygon()
    Cb = C.buffer(-0.2)                       # inside the traced silhouette by the 0.2 mm pull compensation (stitched = traced)
    kept = []
    for r in ITEMS[P]:
        if r in flora and r["unit"] not in PROTECT and r["grp"] != "ST":
            g_ = r["geom"].intersection(Cb).buffer(0)
            g_ = unary_union([q for q in (g_.geoms if hasattr(g_, 'geoms') else [g_]) if q.geom_type == 'Polygon' and q.area >= 3.0]) if not g_.is_empty else g_
            if g_.is_empty or g_.area < 3.0: continue          # a sliver of a drawn object: the traced fill covers it instead
            r["geom"] = g_
        kept.append(r)
    ITEMS[P] = kept
    drawn = unary_union([r["geom"] for r in ITEMS[P] if r["unit"].split("_")[-1].startswith(("leaf", "stem", "flower"))] + ([prot] if prot is not None else []))
    fill = C.buffer(-0.2).difference(drawn.buffer(0.05)).buffer(-0.35).buffer(0.35)
    nf = 0
    for q in (fill.geoms if hasattr(fill, "geoms") else [fill]):
        if q.geom_type != "Polygon" or q.area < 3.0: continue
        m = MR.raster([q], bb); tv = tone[m & (tone >= 0)]
        k_t = int(np.bincount(tv, minlength=4).argmax()) if tv.size else 1          # ONE tone per fill object (majority of the mockup pixels)
        best = None
        for cname, ci in cl_info.items():
            if ci["piece"] != P: continue
            cg = unary_union([r["geom"] for r in ITEMS[P] if r.get("cluster") == cname])
            dd = cg.distance(q) if not cg.is_empty else 1e9
            if best is None or dd < best[0]: best = (dd, cname)
        cn = best[1] if best and best[0] < 25 else None
        u = f"fill_{P}{nf}"           # traced in place: fitted on its own (never moved with a drawn cluster)
        add(P, [dict(col=MR.TONE_KEYS[k_t], geom=q, st="satin", ang="auto", grp="LF-fill", sub=0)], 1500 + nf * 0.01, 19, u, "fill", None)
        nf += 1
    TRACE[P] = dict(silhouettes=len(sils), petals=len(petals), clusters=len(clusters), fill_objects=nf, fill_mm2=round(fill.area, 1),
                    cluster_mm2=round(C.area, 1))
print("A14 trace", TRACE)

META = dict(trace=TRACE, koi_mm=KOI_MM, fish=fish_info, clusters=cl_info, petals=pet_info, lilies=lily_info,
            counts={P: dict(fish=sum(1 for k in fish_info if k["piece"] == P), petals=sum(1 for p in pet_info if p["piece"] == P),
                            flowers=sum(c["flowers"] for c in cl_info.values() if c["piece"] == P),
                            leaves=sum(c["leaves"] for c in cl_info.values() if c["piece"] == P)) for P in kbcore.PIECES},
            mock_map=dict(cfx=MM.CFX, necky=MM.NECKY, sx=MM.SX, sy=MM.SY, s=MM.S), units=UNITS)
pickle.dump(dict(items=ITEMS, meta=META), open("scene.pkl", "wb"))
print({P: len(v) for P, v in ITEMS.items()}, META["counts"])
