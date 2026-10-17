"""02 sleeves — night garden, clouds and stars on the front-facing half of both sleeves (size-M sleeve pattern coords).
The mockup shows only the front half of each hanging sleeve; mockmap.SP maps it onto the flat sleeve (half-cylinder).
Clouds = the mockup's own tone areas (3 tones); stars, the meteor and the plant rosettes are vector motifs placed at the
mockup positions (rosette count from the 4x zooms); firefly dots = every small light-blue dot on the mockup sleeves.
Output: sleeve_scene.pkl = {"items": {"SR": [...], "SL": [...]}, "meta": {...}}.  usage: python3 sleeve_scene.py"""
import cccore
import math, random, pickle
import numpy as np
from scipy import ndimage as ndi
from skimage import measure
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union
from PIL import Image, ImageDraw
import mockmap as MM, front as F, cc_motifs as CM

PPM = 4.0
g0, _ = F.pieces("M")
STARS = {   # mockup px (x, y, kind, colour)
 "R": [(63, 491, "cross", "cc_lilac"), (94, 517, "sparkle", "cc_azure"), (64.5, 544, "big", "cc_white"), (108, 559, "sparkle", "cc_white"),
       (72.5, 586, "dot", "cc_white"), (32.5, 619, "dot", "cc_white")],
 "L": [(654.5, 442.5, "sparkle", "cc_azure"), (674.5, 477.5, "dot", "cc_white"), (627.5, 495, "cross", "cc_azure"), (619, 555.5, "dot", "cc_white"),
       (640, 564, "dot", "cc_white"), (629, 584, "big", "cc_white"), (652, 585.5, "dot", "cc_white")],
}
METEORS = {"R": [((44, 624), (82.5, 584), 1.6)], "L": []}
ROSETTES = {   # mockup px (x, y, radius px, fronds, rotation)
 "R": [(25, 722, 15, 6, 270), (47, 775, 25, 8, 265), (95, 812, 15, 6, 275), (60, 805, 18, 7, 255), (48, 840, 18, 7, 270),
       (105, 870, 18, 7, 268), (55, 880, 18, 7, 262), (85, 745, 12, 5, 280)],
 "L": [(672, 522, 20, 7, 268), (690, 545, 16, 6, 275), (680, 557, 18, 7, 262), (688, 594, 19, 7, 270), (660, 610, 16, 6, 258),
       (672, 630, 22, 7, 268), (700, 650, 18, 6, 280), (690, 672, 26, 8, 266), (680, 712, 21, 7, 272), (712, 730, 16, 6, 285),
       (650, 762, 30, 8, 262), (710, 775, 24, 8, 276), (651, 820, 22, 7, 266), (692, 830, 22, 7, 272), (632, 875, 32, 9, 266),
       (712, 870, 16, 6, 280)],
}

def mask_polys(mask, bb, min_area=1.5, simplify=0.22):
    out = []
    lab, n = ndi.label(mask)
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        m = np.pad(lab[sl] == i, 1)
        if m.sum() / PPM**2 < min_area: continue
        for c in measure.find_contours(m.astype(float), 0.5):
            if len(c) < 6: continue
            pts = [(bb[0] + (sl[1].start + x - 1 + 0.5)/PPM, bb[1] + (sl[0].start + y - 1 + 0.5)/PPM) for y, x in c]
            p = Polygon(pts).buffer(0).simplify(simplify)
            if p.area >= min_area: out.append(p)
    # nested contours (holes) come out as separate rings: even-odd combine
    out.sort(key=lambda p: -p.area); res = []
    for p in out:
        inside = [q for q in res if q.buffer(0.01).contains(p)]
        if inside:
            q = inside[0]; res.remove(q); res.append(q.difference(p).buffer(0))
        else: res.append(p)
    return res

ITEMS = {}; META = {}
for side in "RL":
    Pc = "SR" if side == "R" else "SL"; sgn = 1 if side == "R" else -1
    pc = g0["S01" if side == "R" else "S02"].sew_poly(); b = pc.bounds
    bb = (b[0], b[1], b[2], b[3])
    SPp = lambda px, py: MM.SP(side, px, py)
    items = []
    def add(regs, z, **kw):
        for r in regs:
            if r["geom"].is_empty: continue
            r = dict(r); r.update(kw); r["z"] = z*100000 + len(items); r["el"] = "02"
            r.setdefault("ko", True); r.setdefault("kob", 0.0); r.setdefault("unit", None); items.append(r)
    rgb = np.array(MM.swarp(side, bb, PPM)).astype(np.float32)
    H, W = rgb.shape[:2]
    XMM = bb[0] + (np.arange(W) + 0.5)/PPM
    YMM_ = bb[1] + (np.arange(H) + 0.5)/PPM
    _, _, _ys, _ws = MM.sleeve_dims()
    Wy = np.interp(YMM_, _ys, _ws)[:, None]
    front_half = ((XMM * sgn)[None, :] > 28.0) & ((XMM * sgn)[None, :] < 0.80 * Wy)   # front half, minus the silhouette edges (background / body)
    im = Image.new("L", (W, H), 0); ImageDraw.Draw(im).polygon([((x - bb[0])*PPM, (y - bb[1])*PPM) for x, y in pc.exterior.coords], fill=255)
    inside = (np.array(im) > 127) & front_half
    # do not read the body / background next to the sleeve
    YMM = bb[1] + (np.arange(H) + 0.5)/PPM
    L = ndi.gaussian_filter(rgb @ np.array([0.3, 0.59, 0.11], np.float32), 0.35*PPM)
    r_, g_, b_ = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    sat = (rgb.max(2) - rgb.min(2)) / np.maximum(rgb.max(2), 1)
    # ---------------- leaves are vector rosettes; firefly dots = small light-blue dots
    leafy = (b_ > r_ + 50) & (sat > 0.6) & inside
    dots = (L > 115) & (b_ > r_ + 30) & inside
    dl, dn = ndi.label(dots); fly = 0
    # ---------------- rosettes
    rng = random.Random(21 if side == "R" else 22)
    for i, (px, py, rr, n, rot) in enumerate(ROSETTES[side]):
        cx, cy = SPp(px, py); k = MM.sscale(side, py)
        rot2 = rot if side == "R" else 540 - rot           # mirror the lean on the left sleeve (front half at x < 0)
        add(CM.palm(cx, cy, rr*k*1.35, n, rot2, "cc_leaf", "cc_leaflt", f"ros{i}", rng), 6 + 0.01*i, unit=f"ros{i}")
    LEAF_U = unary_union([r["geom"] for r in items]).buffer(0) if items else Polygon()
    for k_, sl in enumerate(ndi.find_objects(dl), 1):
        m_ = dl[sl] == k_; a_ = m_.sum()/PPM**2
        if not (0.25 < a_ < 6.0): continue
        ys_, xs_ = np.nonzero(m_); cx = bb[0] + (sl[1].start + xs_.mean() + 0.5)/PPM; cy = bb[1] + (sl[0].start + ys_.mean() + 0.5)/PPM
        if LEAF_U.buffer(-0.5).contains(Point(cx, cy)): continue
        if not LEAF_U.buffer(14).contains(Point(cx, cy)): continue      # fireflies live in the garden; sky dots are stars
        add([CM.R("cc_leaflt", Point(cx, cy).buffer(0.7, quad_segs=8), "satin", "auto", "FLY", unit=f"fly{fly}", kob=0.3)], 7, unit=f"fly{fly}"); fly += 1
    # ---------------- clouds (3 tones)
    cl = (L > 62) & (L < 215) & (sat < 0.6) & inside & ~ndi.binary_dilation(leafy, iterations=2)
    cl = ndi.binary_opening(cl, structure=np.ones((3, 3)))
    lab, n = ndi.label(cl); sizes = ndi.sum(cl, lab, range(1, n + 1))/PPM**2
    cl = np.isin(lab, 1 + np.nonzero(sizes >= 30.0)[0])
    cl = ndi.binary_closing(cl, structure=np.ones((3, 3))) & inside
    t_cl = ndi.binary_opening(cl & (L >= 96), structure=np.ones((3, 3))); t_ice = ndi.binary_opening(cl & (L >= 132), structure=np.ones((3, 3)))
    ncl = 0
    for col, m, zz in (("cc_dusk", cl, 0.0), ("cc_cloud", t_cl | t_ice, 0.1), ("cc_ice", t_ice, 0.2)):
        for g in mask_polys(m, bb):
            add([CM.R(col, g, "tatami", 0.0 if col != "cc_cloud" else 8.0, "CL", kob=0.0, kgrp="clouds")], 3 + zz); ncl += 1
    # ---------------- stars + meteor
    for i, (px, py, kind, col) in enumerate(STARS[side]):
        cx, cy = SPp(px, py); u = f"star{i}"
        add(CM.star(cx, cy, kind, col, u), 8, unit=u)
    for i, (h, t, w) in enumerate(METEORS[side]):
        add(CM.meteor(SPp(*h), SPp(*t), w_head=w + 0.3, unit=f"met{i}"), 5, unit=f"met{i}")
    COLSEQ = ["cc_lilac", "cc_white", "cc_azure", "cc_leaflt", "cc_leaf", "cc_ice", "cc_cloud", "cc_dusk"]
    for r in items: r["layer"] = 20 + COLSEQ.index(r["col"])
    ITEMS[Pc] = items
    META[Pc] = dict(rosettes=len(ROSETTES[side]), stars=len(STARS[side]), meteors=len(METEORS[side]), fireflies=fly, cloud_regions=ncl)
pickle.dump(dict(items=ITEMS, meta=META), open("sleeve_scene.pkl", "wb"))
print({k: len(v) for k, v in ITEMS.items()}, META)
