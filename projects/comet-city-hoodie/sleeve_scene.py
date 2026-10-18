"""02 sleeves (Rev B) — night garden, clouds and stars on the front-facing half of both sleeves (size-M sleeve pattern coords).
The mockup shows only the front half of each hanging sleeve; mockmap.SP maps it onto the flat sleeve (half-cylinder).
  * undergrowth: the mockup's own foliage area (smoothed, extended to the outer silhouette) as a soft dark fill;
  * foliage on top, placed by area over the undergrowth: palms, ferns, broad serrated leaves, sprigs in 4 blues (no repeated stamp);
  * clouds: the mockup's cloud areas in 4 shaded tones (pale tops, dark undersides), no speckle;
  * stars + meteor at the mockup positions; fireflies = the clear light dots in the foliage.
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
ANCHORS = {   # mockup px of the palm rosettes (x, y, radius px) - the largest plants; the rest of the foliage fills by area
 "R": [(25, 722, 15), (47, 775, 25), (95, 812, 15), (60, 805, 18), (48, 840, 18), (105, 870, 18), (55, 880, 18), (85, 745, 12)],
 "L": [(672, 522, 20), (690, 545, 16), (680, 557, 18), (688, 594, 19), (660, 610, 16), (672, 630, 22), (700, 650, 18), (690, 672, 26),
       (680, 712, 21), (712, 730, 16), (650, 762, 30), (710, 775, 24), (651, 820, 22), (692, 830, 22), (632, 875, 32), (712, 870, 16)],
}

def mask_polys(mask, bb, min_area=1.5, simplify=0.22, min_hole=4.0):
    out = []
    lab, n = ndi.label(mask)
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        m = np.pad(lab[sl] == i, 1)
        if m.sum() / PPM**2 < min_area: continue
        rings = []
        for c in measure.find_contours(m.astype(float), 0.5):
            if len(c) < 5: continue
            p = Polygon([(bb[0] + (sl[1].start + x - 1 + 0.5)/PPM, bb[1] + (sl[0].start + y - 1 + 0.5)/PPM) for y, x in c]).buffer(0)
            if p.area > 0.05: rings.append(p)
        if not rings: continue
        rings.sort(key=lambda p: -p.area); g = rings[0]
        for r_ in rings[1:]:
            if g.contains(r_.representative_point()) and r_.area >= min_hole: g = g.difference(r_)
        g = g.buffer(0).simplify(simplify)
        if g.area >= min_area: out.append(g)
    return out

ITEMS = {}; META = {}
for side in "RL":
    Pc = "SR" if side == "R" else "SL"; sgn = 1 if side == "R" else -1
    pc = g0["S01" if side == "R" else "S02"].sew_poly(); b = pc.bounds; bb = b
    clip = F.sleeve_clip("M", side).buffer(-0.6)
    SPp = lambda px, py: MM.SP(side, px, py)
    items = []
    def add(regs, z, **kw):
        for r in regs:
            if r["geom"].is_empty: continue
            r = dict(r); r.update(kw); r["z"] = z*100000 + len(items); r["el"] = "02"
            r.setdefault("ko", True); r.setdefault("kob", 0.0); r.setdefault("unit", None); items.append(r)
    rgb = np.array(MM.swarp(side, bb, PPM)).astype(np.float32)
    H, W = rgb.shape[:2]
    XMM = bb[0] + (np.arange(W) + 0.5)/PPM; YMM = bb[1] + (np.arange(H) + 0.5)/PPM
    _, _, _ys, _ws = MM.sleeve_dims()
    Wy = np.interp(YMM, _ys, _ws)[:, None]
    readable = ((XMM * sgn)[None, :] > 28.0) & ((XMM * sgn)[None, :] < 0.80 * Wy)
    im = Image.new("L", (W, H), 0); ImageDraw.Draw(im).polygon([((x - bb[0])*PPM, (y - bb[1])*PPM) for x, y in clip.exterior.coords], fill=255)
    CLIPm = np.array(im) > 127
    inside = CLIPm & readable
    L = ndi.gaussian_filter(rgb @ np.array([0.3, 0.59, 0.11], np.float32), 0.4*PPM)
    r_, g_, b_ = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    sat = (rgb.max(2) - rgb.min(2)) / np.maximum(rgb.max(2), 1)
    leafy = (b_ > r_ + 40) & (sat > 0.5) & inside
    # ---------------- undergrowth: smoothed foliage area, carried out to the outer silhouette (x = 0) where the mockup can't be read
    ug = ndi.gaussian_filter(leafy.astype(np.float32), 2.5*PPM) > 0.22
    ug = ndi.binary_closing(ug, structure=np.ones((int(6*PPM), int(6*PPM))))
    ext_ = np.zeros_like(ug)
    for yi in range(H):                      # rows with foliage at the readable limit: extend toward the centre line
        row = ug[yi]
        xs_ = np.nonzero(row)[0]
        if not len(xs_): continue
        edge_x = xs_.min() if sgn > 0 else xs_.max()
        if abs(XMM[edge_x] * sgn - 28.0) < 6.0:
            if sgn > 0: ext_[yi, :edge_x] = True
            else: ext_[yi, edge_x:] = True
    ug = (ug | (ext_ & ndi.binary_dilation(ug, iterations=int(30*PPM)))) & CLIPm
    ug = ndi.gaussian_filter(ug.astype(np.float32), 1.5*PPM) > 0.5
    lb, nn = ndi.label(ug); ss = ndi.sum(ug, lb, range(1, nn + 1)) / PPM**2
    ug = np.isin(lb, 1 + np.nonzero(ss >= 80.0)[0])
    UG = unary_union(mask_polys(ug, bb, min_area=80.0, simplify=0.4, min_hole=40.0)).buffer(0)
    # ---------------- clouds (4 shaded tones)
    _ex = Image.new("L", (W, H), 0); _exd = ImageDraw.Draw(_ex)
    for (px, py, kind, col) in STARS[side]:
        cx_, cy_ = SPp(px, py); rr_ = {"big": 9, "sparkle": 7, "cross": 4.5, "dot": 2.5}[kind]
        _exd.ellipse([((cx_ - rr_) - bb[0])*PPM, ((cy_ - rr_) - bb[1])*PPM, ((cx_ + rr_) - bb[0])*PPM, ((cy_ + rr_) - bb[1])*PPM], fill=255)
    for (h, t, w) in METEORS[side]:
        a_, b_2 = SPp(*h), SPp(*t)
        _exd.line([((a_[0] - bb[0])*PPM, (a_[1] - bb[1])*PPM), ((b_2[0] - bb[0])*PPM, (b_2[1] - bb[1])*PPM)], fill=255, width=int(9*PPM))
    EXCL = np.array(_ex) > 127
    cl = (L > 62) & (L < 215) & (sat < 0.6) & inside & ~ndi.binary_dilation(leafy, iterations=2) & ~EXCL
    cl = ndi.binary_opening(cl, structure=np.ones((4, 4)))
    cl = ndi.gaussian_filter(cl.astype(np.float32), 1.0*PPM) > 0.5
    lb, nn = ndi.label(cl); ss = ndi.sum(cl, lb, range(1, nn + 1))/PPM**2
    cl = np.isin(lb, 1 + np.nonzero(ss >= 60.0)[0])
    hh = ndi.binary_fill_holes(cl) & ~cl; hl, hn = ndi.label(hh); hs = ndi.sum(hh, hl, range(1, hn + 1))/PPM**2
    cl |= np.isin(hl, 1 + np.nonzero(hs < 10.0)[0])
    soft = ndi.gaussian_filter(cl.astype(np.float32), 1.8*PPM); gsh = np.zeros_like(soft); sh = int(2.2*PPM)
    gsh[sh:-sh] = soft[:-2*sh] - soft[2*sh:]
    T = ndi.gaussian_filter(L, 0.7*PPM) - 70.0*gsh
    def tone(m):
        m = ndi.gaussian_filter(m.astype(np.float32), 0.6*PPM) > 0.5
        m = ndi.binary_opening(m & cl, structure=np.ones((2, 2)))
        lb_, nn_ = ndi.label(m); ss_ = ndi.sum(m, lb_, range(1, nn_ + 1))/PPM**2
        return np.isin(lb_, 1 + np.nonzero(ss_ >= 3.0)[0])
    ncl = 0
    for col, m, zz in (("cc_dusk", cl, 0.0), ("cc_cloud", tone(T >= 100), 0.1), ("cc_ice", tone(T >= 128), 0.2), ("cc_white", tone(T >= 165), 0.3)):
        for g in mask_polys(m, bb, min_area=3.0 if col != "cc_dusk" else 60.0):
            add([CM.R(col, g, "tatami", 0.0 if col == "cc_dusk" else 8.0, "CL", kob=0.0, kgrp="clouds")], 3 + zz); ncl += 1
    CLOUD_G = unary_union([r["geom"] for r in items if r["grp"] == "CL"]).buffer(1.5) if items else Polygon()
    _sx = [Point(*SPp(px, py)).buffer({"big": 11, "sparkle": 8, "cross": 5, "dot": 3}[kind]) for (px, py, kind, col) in STARS[side]]
    _sx += [LineString([SPp(*h), SPp(*t)]).buffer(4.5) for (h, t, w) in METEORS[side]]
    CLOUD_G = unary_union([CLOUD_G] + _sx)
    # ---------------- foliage: anchors = palms, then fill by area with mixed motifs
    rng = random.Random(21 if side == "R" else 22)
    placed = []
    def put(regs, z, unit):
        add(regs, z, unit=unit); placed.append(unary_union([r["geom"] for r in regs]))
    nmot = 0
    for i, (px, py, rr) in enumerate(ANCHORS[side]):
        cx, cy = SPp(px, py); k = MM.sscale(side, py)
        R0 = rr*k*1.2; rot = 270 + rng.uniform(-12, 12)
        put(CM.palm(cx, cy, R0, rng.randint(6, 9), rot, "cc_leaf", "cc_leaflt", f"pal{i}", rng), 6 + 0.01*i, f"pal{i}"); nmot += 1
    UGs = UG.buffer(-1).difference(CLOUD_G)
    kinds = ["fern", "broad", "palm", "sprig"]
    tries = 0
    target = int(UGs.area / 150)
    while nmot < target + len(ANCHORS[side]) and tries < 4000:
        tries += 1
        bx = UGs.bounds
        p = Point(rng.uniform(bx[0], bx[2]), rng.uniform(bx[1], bx[3]))
        if not UGs.contains(p): continue
        if placed and min(g.distance(p) for g in placed[-60:]) < 2.0 and rng.random() < 0.7: continue
        kind = rng.choices(kinds, weights=[0.32, 0.26, 0.22, 0.20])[0]; u = f"m{nmot}"
        ang = -90 + rng.uniform(-70, 70)
        if kind == "fern":
            regs = CM.fern((p.x, p.y), ang, rng.uniform(12, 22), rng.choice(["cc_leaflt", "cc_leaf"]), rng.choice(["cc_azure", "cc_leaflt"]), u, rng, droop=rng.uniform(0.1, 0.45))
        elif kind == "broad":
            regs = CM.broad_leaf((p.x, p.y), ang, rng.uniform(10, 17), rng.choice(["cc_royal", "cc_leaf"]), rng.choice(["cc_azure", "cc_leaflt"]), u, curl=rng.uniform(-0.25, 0.25))
        elif kind == "palm":
            regs = CM.palm(p.x, p.y, rng.uniform(9, 15), rng.randint(5, 7), 270 + rng.uniform(-20, 20), rng.choice(["cc_leaf", "cc_royal"]), "cc_leaflt", u, rng)
        else:
            regs = CM.sprig((p.x, p.y), ang, rng.uniform(7, 11), rng.choice(["cc_azure", "cc_leaflt"]), u, rng)
        ug_ = unary_union([r["geom"] for r in regs])
        if not clip.contains(ug_) or ug_.intersects(CLOUD_G): continue
        put(regs, 5 + rng.random()*2, u); nmot += 1
    # soft undergrowth: hugs the foliage (grown + rounded), never a slab
    UGF = unary_union(placed).buffer(3.2).buffer(-2.0).intersection(clip).difference(CLOUD_G).buffer(0)
    UGF = unary_union([p for p in CM.polys(UGF) if p.area > 40])
    add([CM.R("cc_night", g, "tatami", 60.0, "UG", kob=0.0, kgrp="ug") for g in CM.polys(UGF)], 2)
    # fireflies: clear light dots in the foliage area
    dots = (L > 120) & (b_ > r_ + 30) & inside
    dl, dn = ndi.label(dots); fly = 0
    for k_, sl in enumerate(ndi.find_objects(dl), 1):
        m_ = dl[sl] == k_; a_ = m_.sum()/PPM**2
        if not (0.8 < a_ < 6.0): continue
        ys_, xs_ = np.nonzero(m_); cx = bb[0] + (sl[1].start + xs_.mean() + 0.5)/PPM; cy = bb[1] + (sl[0].start + ys_.mean() + 0.5)/PPM
        if not UG.buffer(4).contains(Point(cx, cy)): continue
        add([CM.R("cc_ice", Point(cx, cy).buffer(0.75, quad_segs=8), "satin", "auto", "FLY", unit=f"fly{fly}", kob=0.4)], 8, unit=f"fly{fly}"); fly += 1
    # ---------------- stars + meteor
    srng = random.Random(5 if side == "R" else 6)
    for i, (px, py, kind, col) in enumerate(STARS[side]):
        cx, cy = SPp(px, py); u = f"star{i}"
        glow = ("cc_lilac" if col != "cc_lilac" else "cc_azure") if kind in ("sparkle", "cross") else None
        add(CM.star_b(cx, cy, kind, col, u, k=srng.uniform(0.85, 1.25), glow=glow), 9, unit=u)
    for i, (h, t, w) in enumerate(METEORS[side]):
        add(CM.meteor(SPp(*h), SPp(*t), w_head=w + 0.3, unit=f"met{i}"), 5, unit=f"met{i}")
    COLSEQ = ["cc_lilac", "cc_white", "cc_azure", "cc_leaflt", "cc_royal", "cc_leaf", "cc_ice", "cc_cloud", "cc_dusk", "cc_night"]
    for r in items: r["layer"] = 20 + COLSEQ.index(r["col"])
    ITEMS[Pc] = items
    META[Pc] = dict(rosettes=len(ANCHORS[side]), plants=nmot, stars=len(STARS[side]), meteors=len(METEORS[side]), fireflies=fly,
                    cloud_regions=ncl, undergrowth_mm2=round(UGF.area))
pickle.dump(dict(items=ITEMS, meta=META), open("sleeve_scene.pkl", "wb"))
print({k: len(v) for k, v in ITEMS.items()}, META)
