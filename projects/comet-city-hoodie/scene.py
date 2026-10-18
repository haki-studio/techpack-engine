"""01 front scene — comet over a night city, composed on the size-M fronts (garment mm, unclipped).
Positions are read from the mockup (inputs/front.png, mapped by mockmap); clouds + horizon haze are the mockup's own
tone areas (3 tones) re-cut as fills; stars, meteors, the comet, the city, railing, bicycle, figure and lamp post are
drawn as vector motifs (cc_motifs) at the mockup positions and counts. Output: scene.pkl = {"items": [...], "meta": {...}}.
Per-size clipping happens in art_size.py.  usage: python3 scene.py"""
import cccore
import math, random, pickle
import numpy as np
from scipy import ndimage as ndi
from skimage import measure
from shapely.geometry import Point, Polygon, LineString, box, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity, prepared
from PIL import Image, ImageDraw
import mockmap as MM, front as F, cc_motifs as CM

P = MM.P; S = MM.S
BB, PPM = (-320.0, -40.0, 320.0, 525.0), 4.0
CLIP_M = {s: F.clip_for("M", s) for s in "RL"}

# ---------------------------------------------------------------- mockup in mm space
_rgb = np.array(MM.warp(BB, PPM)).astype(np.float32)
LUM = _rgb @ np.array([0.3, 0.59, 0.11], np.float32)
_mx, _mn = _rgb.max(2), _rgb.min(2); SAT = (_mx - _mn) / np.maximum(_mx, 1)
H, W = LUM.shape
YY, XX = np.mgrid[0:H, 0:W]; XMM = BB[0] + (XX + 0.5)/PPM; YMM = BB[1] + (YY + 0.5)/PPM
def disk(mm): r = max(1, int(round(mm*PPM))); y, x = np.ogrid[-r:r+1, -r:r+1]; return x*x + y*y <= r*r
def rast(geoms):
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    for g in geoms:
        for p in CM.polys(g):
            d.polygon([((x - BB[0])*PPM, (y - BB[1])*PPM) for x, y in p.exterior.coords], fill=255)
            for h in p.interiors: d.polygon([((x - BB[0])*PPM, (y - BB[1])*PPM) for x, y in h.coords], fill=0)
    return np.array(im) > 127
PANEL = rast([F.PANEL_R, F.PANEL_L]) & (np.abs(XMM) > 13)

def mask_polys(mask, min_area=1.5, simplify=0.25, holes=True):
    out = []
    cs = measure.find_contours(np.pad(mask, 1).astype(float), 0.5)
    rings = []
    for c in cs:
        if len(c) < 6: continue
        pts = [(BB[0] + (x - 1 + 0.5)/PPM, BB[1] + (y - 1 + 0.5)/PPM) for y, x in c]
        p = Polygon(pts).buffer(0)
        if p.area >= 0.3: rings.append(p)
    rings.sort(key=lambda p: -p.area)
    # even-odd nesting -> polygons with holes
    used = [False]*len(rings)
    for i, p in enumerate(rings):
        if used[i]: continue
        g = p
        for j in range(i + 1, len(rings)):
            if not used[j] and p.contains(rings[j].representative_point()) and holes:
                depth = sum(1 for q in rings[:j] if q.contains(rings[j].representative_point()))
                if depth % 2 == 1: g = g.difference(rings[j]); used[j] = True
        used[i] = True
        g = g.buffer(0).simplify(simplify)
        if g.area >= min_area: out.append(g)
    return out

items = []
def add(regs, sew, z=None, **kw):
    """sew = sew-order group name (see SEW at the bottom); z = stacking (higher covers lower)"""
    for r in regs:
        g = r["geom"]
        if g is None or g.is_empty: continue
        r = dict(r); r.update(kw); r["sew"] = sew; r["z"] = (z if z is not None else 0) * 100000 + len(items); r["el"] = "01"
        r.setdefault("ko", True); r.setdefault("kob", 0.0); r.setdefault("unit", None)
        items.append(r)
Z = dict(haze=1, glow=2, comet=3, meteor=4, cloud=5, star=8, far=10, farwin=11, near=12, nearwin=13, rail=14, bush=15, lamp=16, bike=17, figure=18)

# ================================================================ comet (one bundle of strands, crossing the zip)
SPINE_PX = [(302, 621), (330, 575), (355, 527), (373, 494), (400, 452), (440, 413), (480, 383), (520, 353), (548, 334), (575, 318)]
# axis read in mm from the mockup mapped to size M (overlay check: scratch spine.png): head lower-left on FR, tail upper-right on FL
SPINE_MM = [(-80, 320), (-50, 273), (-17, 231), (23, 199), (43, 181), (87, 150), (133, 117), (175, 82), (205, 55), (232, 30), (252, 12)]
SPINE = CM.smooth_pts(SPINE_MM, 220)
def spread(t):              # half-width of the bundle (mm) from the head (t=0) to the tail (t=1)
    return float(np.interp(t, [0.0, 0.12, 0.3, 0.5, 0.7, 0.85, 1.0], [1.4, 3.6, 8.0, 14.0, 18.5, 20.5, 21.0]))
# (offset, t0, t1, max width, colour) - from the upper-left edge (-1) to the lower-right edge (+1), mockup + close-up order
STRANDS = [
 (-1.05, 0.38, 0.97, 1.0, "cc_azure"), (-0.92, 0.22, 0.86, 1.3, "cc_royal"), (-0.80, 0.10, 1.00, 1.5, "cc_azure"),
 (-0.66, 0.30, 0.92, 1.9, "cc_royal"), (-0.52, 0.04, 0.99, 2.2, "cc_azure"), (-0.36, 0.15, 0.90, 2.0, "cc_royal"),
 (-0.22, 0.00, 1.02, 2.6, "cc_azure"), (-0.08, 0.02, 0.98, 2.6, "cc_lilac"), (0.06, 0.08, 1.04, 2.4, "cc_violet"),
 (0.20, 0.25, 0.95, 2.1, "cc_lilac"), (0.34, 0.12, 0.88, 2.3, "cc_violet"), (0.48, 0.30, 0.99, 2.0, "cc_royal"),
 (0.62, 0.20, 0.84, 1.7, "cc_azure"), (0.76, 0.42, 0.95, 1.5, "cc_royal"), (0.90, 0.33, 0.78, 1.2, "cc_violet"),
 (1.04, 0.52, 0.92, 1.0, "cc_azure"),
]
_rc = random.Random(5)
for k in range(30):
    o = _rc.uniform(-1.0, 1.0); t0 = _rc.uniform(0.18, 0.85); t1 = min(1.03, t0 + _rc.uniform(0.12, 0.4))
    ao = abs(o + 0.1)
    col = _rc.choice(["cc_lilac", "cc_violet", "cc_azure"] if ao < 0.35 else (["cc_azure", "cc_violet", "cc_royal"] if ao < 0.7 else ["cc_royal", "cc_azure"]))
    STRANDS.append((o, t0, t1, _rc.uniform(1.2, 2.3), col))
for i, (o, t0, t1, wm, col) in enumerate(STRANDS):
    wm = wm * (1.3 if i < 16 else 1.0)
    add(CM.strand(SPINE, o, t0, t1, wm, col, spread, unit=None), "comet", Z["comet"] + 0.01*i)
# white core line on the lilac strand (head to mid-tail) and a bright head
add(CM.strand(SPINE, -0.12, 0.0, 0.78, 1.1, "cc_white", spread, grp="COM-core"), "comet", Z["comet"] + 0.5)
add([CM.R("cc_white", Point(SPINE[0]).buffer(1.4, quad_segs=10), "satin", "auto", "COM-core", kob=0.0)], "comet", Z["comet"] + 0.6)
# tail wisps fanning out past the bundle end
for k, (o, dl, col) in enumerate(((-0.95, 26, "cc_lilac"), (-0.55, 18, "cc_violet"), (-0.15, 30, "cc_lilac"), (0.35, 20, "cc_violet"), (0.8, 14, "cc_royal"))):
    end = SPINE[-1]; d = SPINE[-1] - SPINE[-12]; d /= np.linalg.norm(d); n = np.array([-d[1], d[0]])
    a = SPINE[-30] + n * o * spread(0.86); b = end + n * o * spread(1.0) * 1.1 + d * dl
    pts = CM.smooth_pts([a, (a + b)/2 + n*1.5, b], 30)
    w = np.linspace(1.6, 0.85, len(pts))
    add([CM.R(col, CM.ribbon(pts, w), "satin", "auto", "COM", kob=0.0)], "comet", Z["comet"] + 0.3)
COMET_U = unary_union([r["geom"] for r in items]).buffer(0)

# ================================================================ meteors (7, head = lower-left end)
METEORS_PX = [((207, 421), (246, 381), 1.6), ((297, 486), (342, 419), 1.5), ((392, 394), (431, 341), 1.4), ((500, 330), (530, 301), 1.2),
              ((530, 394), (578, 352), 1.4), ((495, 490), (548, 434), 1.5), ((451, 599), (495, 542), 1.5)]
for i, (h, t, w) in enumerate(METEORS_PX):
    add(CM.meteor(P(*h), P(*t), w_head=w + 0.3, unit=f"met{i}"), "meteor", Z["meteor"], unit=f"met{i}")
# falling star + violet trail + red sparks
RS = P(403.5, 597.5)
trail = CM.smooth_pts([P(404.7, 532.0), P(404.2, 560.0), P(403.8, 590.0)], 30)
add([CM.R("cc_violet", CM.ribbon(trail, np.linspace(0.85, 1.5, len(trail))), "satin", "auto", "MET", kob=0.3)], "meteor", Z["meteor"], unit="redstar")
add(CM.red_star(*RS, r=5.6), "meteor", Z["meteor"] + 0.5, unit="redstar")
for (sx, sy) in ((409, 580), (397, 589), (411, 591), (396, 604)):
    add([CM.R("cc_red", Point(P(sx, sy)).buffer(0.75, quad_segs=8), "satin", "auto", "DOT", kob=0.3)], "meteor", Z["meteor"], unit="redstar")

# ================================================================ clouds + horizon haze (mockup tone areas, 3 tones)
STARS_PX = [
 # FR (wearer's right front)
 (196.7, 309.5, "cross", "cc_white"), (227.5, 313.7, "dot", "cc_white"), (208.7, 327.5, "big", "cc_lilac"), (187, 329.5, "dot", "cc_lilac"),
 (272.5, 329.5, "sparkle", "cc_azure"), (297.5, 323.7, "dot", "cc_white"), (243.7, 357, "cross", "cc_white"), (192, 363.7, "sparkle", "cc_lilac"),
 (176.5, 367.5, "dot", "cc_white"), (181.5, 368.0, "dot", "cc_white"), (246, 380, "sparkle", "cc_azure"), (270, 375, "dot", "cc_white"),
 (297.5, 374.5, "sparkle", "cc_azure"), (243, 420.5, "cross", "cc_white"), (291, 439.5, "dot", "cc_white"), (326, 479, "sparkle", "cc_white"),
 (226, 491, "cross", "cc_white"), (186, 497, "dot", "cc_white"), (206, 504.5, "sparkle", "cc_white"), (257.5, 540.5, "dot", "cc_white"),
 (287, 549.5, "cross", "cc_white"), (314.5, 549, "dot", "cc_white"), (206, 574, "dot", "cc_white"), (180, 580, "sparkle", "cc_white"),
 (132.5, 582.5, "dot", "cc_white"), (340, 590.5, "cross", "cc_white"), (308, 580, "dot", "cc_white"), (327, 605, "dot", "cc_white"),
 # FL (wearer's left front)
 (480.5, 309.5, "dot", "cc_white"), (469, 333, "big", "cc_azure"), (539, 323, "dot", "cc_white"), (525, 330, "dot", "cc_white"),
 (478.5, 347.5, "dot", "cc_white"), (434, 379, "dot", "cc_white"), (408.5, 407.5, "cross", "cc_white"), (550, 398.7, "sparkle", "cc_white"),
 (565, 405, "sparkle", "cc_lilac"), (533.5, 412, "dot", "cc_white"), (482, 461, "cross", "cc_white"), (565, 459, "big", "cc_white"),
 (573.5, 419, "dot", "cc_white"), (483.5, 422.5, "dot", "cc_white"), (465, 482, "dot", "cc_white"), (530, 484, "sparkle", "cc_white"),
 (512, 496, "dot", "cc_white"), (413, 539, "dot", "cc_white"), (393, 547.5, "dot", "cc_white"), (391, 556, "dot", "cc_white"),
 (428, 552, "cross", "cc_azure"), (496, 565, "dot", "cc_white"), (530, 574, "cross", "cc_white"), (542, 588, "dot", "cc_white"),
 (572, 584, "dot", "cc_white"), (602, 586, "cross", "cc_white"), (424, 597.5, "dot", "cc_white"), (450, 607, "dot", "cc_white"),
 (453, 541, "dot", "cc_white"), (396, 570, "dot", "cc_white"), (391, 585, "dot", "cc_white"),
]
_STAR_R = {"big": 9.0, "sparkle": 6.5, "cross": 4.0, "dot": 2.6}
STREAK_U = unary_union([COMET_U.buffer(2.0), COMET_U.buffer(9.0).intersection(box(-400, -100, 400, 190))] + [r["geom"].buffer(1.2) for r in items if r["grp"] in ("MET", "RSTAR", "DOT", "STAR-c")] +
                       [Point(P(_x, _y)).buffer(8.0) for _x, _y in ((403.5, 597.5),)] +
                       [Point(P(_x, _y)).buffer(_STAR_R[_k]) for _x, _y, _k, _c in STARS_PX])     # stars + their glow are not clouds
streakm = rast([STREAK_U])
Ls = ndi.gaussian_filter(LUM, 0.35*PPM)
# no seam topstitching / welt pockets / zip tape from the mockup: cloud tones only 20 inside the side + armhole seams,
# 12 clear of the welt boxes, 17 from CF
_inner = rast([F.PANEL_R.buffer(-20), F.PANEL_L.buffer(-20), box(-400, 330, 400, 600).intersection(unary_union([F.PANEL_R, F.PANEL_L]))])
_inner &= ~rast([F.WELT_R.buffer(12), F.WELT_L.buffer(12)]) & (np.abs(XMM) > 17)
cloudish = (Ls > 60) & PANEL & _inner & (YMM > 88) & (YMM < 408)
_front = rast([box(*P(360, 486), *P(480, 528))])         # the one cloud bank the comet passes behind (mockup, at the zip)
cloudish &= ~(streakm & ~(_front & (SAT < 0.42)))
cloudish = ndi.binary_opening(cloudish, structure=disk(0.6))
lab, n = ndi.label(cloudish)
sizes = ndi.sum(cloudish, lab, range(1, n + 1)) / PPM**2
_cy = np.array([c[0] for c in ndi.center_of_mass(cloudish, lab, range(1, n + 1))]) / PPM + BB[1] if n else np.array([])
keep = np.isin(lab, 1 + np.nonzero((sizes >= 12.0) & ((sizes >= 25.0) | (_cy > 200)))[0])      # sky above the clouds: only real cloud wisps
cloudish = ndi.binary_closing(keep, structure=disk(0.5)) & PANEL
_holes = ndi.binary_fill_holes(cloudish) & ~cloudish            # fill only small holes (< 3 mm2); bigger dark gaps stay fabric
_hl, _hn = ndi.label(_holes); _hs = ndi.sum(_holes, _hl, range(1, _hn + 1)) / PPM**2
cloudish |= np.isin(_hl, 1 + np.nonzero(_hs < 3.0)[0])
T_ICE, T_CLOUD = 132.0, 92.0
tone_ice = ndi.binary_opening(cloudish & (Ls >= T_ICE), structure=disk(0.45))
tone_cl = ndi.binary_opening(cloudish & (Ls >= T_CLOUD), structure=disk(0.45)) | tone_ice
for col, m, zz in (("cc_dusk", cloudish, 0.0), ("cc_cloud", tone_cl, 0.1), ("cc_ice", tone_ice, 0.2)):
    for g in mask_polys(m, min_area=1.5, simplify=0.22):
        cy = g.centroid.y
        sew = "haze" if cy > 340 else "cloud"
        add([CM.R(col, g, "tatami", 0.0 if col != "cc_cloud" else 8.0, "CL", kob=0.0, kgrp="clouds")], sew, Z["cloud" if sew == "cloud" else "haze"] + zz)
# each tone patch remembers the y of its cloud silhouette (per-size hem anchoring moves whole clouds, never single tones)
_sil = [r["geom"] for r in items if r["grp"] == "CL" and r["col"] == "cc_dusk"]
_tree = __import__("shapely").STRtree(_sil)
for r in items:
    if r["grp"] != "CL": continue
    q = r["geom"].representative_point(); hit = [int(j) for j in _tree.query(q) if _sil[int(j)].buffer(0.05).contains(q)]
    r["cref"] = _sil[hit[0]].centroid.y if hit else r["geom"].centroid.y
CLOUD_U = unary_union([r["geom"] for r in items if r["grp"] == "CL"]).buffer(0)

# rose city glow: the pink pixels in the haze band behind the skyline
r_, g_, b_ = _rgb[..., 0], _rgb[..., 1], _rgb[..., 2]
pink = (r_ > 130) & (r_ > g_ + 25) & (b_ > g_ - 5) & PANEL & (YMM > 345) & (YMM < 400)
pink = ndi.binary_closing(pink, structure=disk(0.6))
for g in mask_polys(pink, min_area=1.6, simplify=0.2):
    add([CM.R("cc_rose", g.buffer(0.3), "tatami", 0.0, "GLOW", kob=0.0)], "glow", Z["glow"])

# ================================================================ stars (every mockup star, from the 4x zooms)
LIM_ALL = {}
for _s in "RL":
    _g = CLIP_M[_s]
    for _sz in cccore.SIZES:
        _k = cccore.GRADE[_sz][1]; _g = _g.intersection(affinity.scale(F.clip_for(_sz, _s), 1/_k, 1/_k, origin=(0, 0)))
    LIM_ALL[_s] = _g.buffer(0)
stars = []; star_moved = 0
from shapely.ops import nearest_points
for i, (px, py, kind, col) in enumerate(STARS_PX):
    cx, cy = P(px, py); side = "R" if cx < 0 else "L"
    rr = {"big": 13.0, "sparkle": 8.8, "cross": 4.6, "dot": 1.3}[kind]
    inner = LIM_ALL[side].buffer(-(rr + 0.8))
    if not inner.contains(Point(cx, cy)):
        q = nearest_points(inner, Point(cx, cy))[0]; cx, cy = q.x, q.y; star_moved += 1
    u = f"star{i}"; stars.append((cx, cy, kind, col))
    add(CM.star(cx, cy, kind, col, u), "star", Z["star"], unit=u)

# ================================================================ city: far + near buildings, windows, glow
# buildings (mockup px): (x0, x1, top) - read from the 4x zooms; bottoms run down behind the next row
FAR_PX = [(122, 140, 664), (140, 166, 650), (192, 201, 671), (204, 230, 660), (240, 259, 662.5), (259, 281, 649), (282, 295, 671),
          (299, 320, 665), (320, 341, 656), (349, 362, 660),
          (374, 398, 682), (430, 446, 690), (450, 471, 670), (480, 501, 680), (501, 518, 677.5), (516, 541, 681), (541, 556, 685), (591, 611, 661)]
ANTENNA_PX = [(215, 654, 660), (249, 655, 662.5), (270, 637, 649), (330, 645, 656), (460, 658, 670), (490, 670, 680)]
NEAR_PX = [(122, 152, 677), (152, 202, 694), (202, 240, 690), (240, 260, 685), (260, 300, 692), (300, 325, 686), (325, 362, 690),
           (374, 391, 692), (391, 448, 699), (448, 481, 697), (481, 516, 692), (516, 541, 690), (541, 581, 705), (581, 611, 692)]
def rail_y(px): return 720.0 + (px - 130.0) * 7.0 / 470.0          # top rail, mockup px (slopes down 7 px across the fronts)
BOT_PX = lambda px: rail_y(px) + 40.0
far = []; near = []
for x0, x1, top in FAR_PX:
    a, b = P(x0, top), P(x1, rail_y((x0 + x1)/2))
    far.append(box(a[0], a[1], b[0], b[1] - 6))
for x, y0, y1 in ANTENNA_PX:
    a = P(x, y0); b = P(x, y1 + 1); far.append(box(a[0] - 0.55, a[1], a[0] + 0.55, b[1]))
for x0, x1, top in NEAR_PX:
    a, b = P(x0, top), P(x1, BOT_PX((x0 + x1)/2))
    near.append(box(a[0], a[1], b[0], b[1]))
FAR_U = unary_union(far).buffer(0); NEAR_U = unary_union(near).buffer(0)
# lit left edges on the tall far towers (mockup: pale blue rim light)
edges = []
for x0, x1, top in FAR_PX:
    a, b = P(x0, top), P(x1, top)
    if (P(x0, 700)[1] - a[1]) > 25 and (b[0] - a[0]) > 18:
        edges.append(box(a[0], a[1], a[0] + 1.1, P(x0, 690)[1]))

# windows: every lit blob on the mockup inside the building band (count + positions + colour), re-cut as satin blocks
Lw = LUM
bright = ((Lw > 118) | ((r_ > 150) & (g_ > 105) & (b_ < 125)) | ((r_ > 160) & (b_ > 120) & (g_ < 150))) & PANEL
cityband = (YMM > P(0, 645)[1]) & (YMM < P(0, 768)[1])
railband = np.zeros_like(bright)
for yy in (0.0, 40.0):           # top + bottom rail rows are not windows
    for xi in range(0, W, 4):
        px_ = MM.Pinv(XMM[0, xi], 0)[0]; yr = P(0, rail_y(px_) + yy)[1]
        y0 = int((yr - 2.2 - BB[1])*PPM); y1 = int((yr + 2.2 - BB[1])*PPM); railband[max(0, y0):y1, xi:xi + 4] = True
wm = bright & cityband & ~railband & rast([FAR_U.buffer(0.5), NEAR_U.buffer(0.5)])
wlab, wn = ndi.label(wm)
windows = []
for k_, sl in enumerate(ndi.find_objects(wlab), 1):
    m_ = wlab[sl] == k_; a_ = m_.sum() / PPM**2
    if a_ < 0.6 or a_ > 40: continue
    ys_, xs_ = np.nonzero(m_); w_ = (xs_.max() - xs_.min() + 1)/PPM; h_ = (ys_.max() - ys_.min() + 1)/PPM
    if h_ > 3.2*w_ and h_ > 6: continue                                     # balusters / poles
    cx_ = BB[0] + (sl[1].start + xs_.mean() + 0.5)/PPM; cy_ = BB[1] + (sl[0].start + ys_.mean() + 0.5)/PPM
    pix = _rgb[sl][m_]; mr, mg, mb = pix.mean(0); ml = 0.3*mr + 0.59*mg + 0.11*mb
    if mr > mb + 40 and mg > mb + 10: col = "cc_gold"
    elif mr > mg + 25 and mb > mg - 10: col = "cc_rose"
    elif ml > 190: col = "cc_white"
    else: col = "cc_azure"
    ww = float(np.clip(w_, 1.5, 4.5)); hh = float(np.clip(h_, 1.8, 3.6))
    if w_ > 6 and h_ < 3.2: ww = float(np.clip(w_, 1.5, 22.0)); hh = float(np.clip(h_, 1.5, 2.2))    # window bands on the striped tower
    windows.append((cx_, cy_, ww, hh, col))
# the figure + lamp + bike stand in front: windows there are hidden anyway
WIN = []
for cx_, cy_, ww, hh, col in windows:
    g = box(cx_ - ww/2, cy_ - hh/2, cx_ + ww/2, cy_ + hh/2)
    inside = (FAR_U.buffer(-0.6).contains(g) or NEAR_U.buffer(-0.6).contains(g))
    if not inside: continue
    if any(g.distance(o) < 0.6 for o in WIN): continue
    WIN.append(g)
    lay = "nearwin" if NEAR_U.buffer(-0.6).contains(g) else "farwin"
    add([CM.R(col, g, "satin", 0.0 if hh > ww else 90.0, "WIN", kob=0.0)], "window", Z[lay])
add([CM.R("cc_dusk", g, "tatami", 90.0, "BLD-far", kob=0.4) for g in CM.polys(FAR_U)], "building", Z["far"])
add([CM.R("cc_azure", g, "satin", "auto", "BLD-edge", kob=0.0) for g in edges], "window", Z["farwin"])
add([CM.R("cc_night", g, "tatami", 90.0, "BLD", kob=0.5) for g in CM.polys(NEAR_U)], "building", Z["near"])

# ================================================================ railing, kerb
def rail_line(dy, w, col, grp, st="satin"):
    xs = np.linspace(110, 625, 60)
    pts = [P(x, rail_y(x) + dy) for x in xs]
    return CM.R(col, LineString(pts).buffer(w/2, cap_style="flat"), st, "auto", grp, ko=False, kob=0.0)
add([rail_line(0.0, 1.8, "cc_ice", "RAIL")], "rail", Z["rail"])
add([rail_line(38.5, 1.2, "cc_cloud", "RAIL")], "rail", Z["rail"])
add([rail_line(47.5, 1.1, "cc_ice", "RAIL")], "rail", Z["rail"])              # kerb line
x = 132.0; nb = 0
while x < 612:
    a = P(x, rail_y(x) + 1.2); b = P(x, rail_y(x) + 37.8)
    add([CM.R("cc_cloud", LineString([a, b]).buffer(0.5, cap_style="flat"), "satin", "auto", "RAIL-b", ko=False, kob=0.0)], "rail", Z["rail"])
    x += 10.6; nb += 1

# ================================================================ lamp post (FL), bush (FL), bicycle (FR), figure (FL)
lp = P(586, 0)[0]
pole = box(lp - 1.7, P(0, 636)[1], lp + 1.7, P(0, 790)[1])
lant = box(P(578.5, 0)[0], P(0, 598)[1], P(591.5, 0)[0], P(0, 636)[1])
cap = Polygon([(lant.bounds[0] - 1.0, lant.bounds[1] + 0.5), (lant.bounds[2] + 1.0, lant.bounds[1] + 0.5), ((lant.bounds[0] + lant.bounds[2])/2, lant.bounds[1] - 3.0)])
lamp_body = unary_union([pole, lant, cap]).buffer(0)
glass = box(lant.bounds[0] + 2.0, lant.bounds[1] + 3.0, lant.bounds[2] - 2.0, lant.bounds[3] - 3.5)
add([CM.R("cc_night", lamp_body.difference(glass.buffer(0.3)), "satin", "auto", "LAMP", kob=0.6, unit="lamp")], "figure", Z["lamp"], unit="lamp")
add([CM.R("cc_cloud", glass, "satin", 90.0, "LAMP-l", kob=0.0, unit="lamp")], "lampglass", Z["lamp"] + 0.1, unit="lamp")
add([CM.R("cc_ice", LineString([(lp + 1.7, P(0, 640)[1]), (lp + 1.7, P(0, 788)[1])]).buffer(0.45, cap_style="flat"), "satin", "auto", "LAMP", ko=False, kob=0.0, unit="lamp")], "overlay_ice", Z["lamp"] + 0.2, unit="lamp")
rng = random.Random(11)
BUSH_PX = [(540, 760, 9, 6, 250), (586, 752, 8, 5, 285), (529, 772, 8, 5, 245), (566, 776, 8, 6, 270), (546, 770, 13, 7, 255), (562, 756, 14, 7, 262), (578, 768, 12, 7, 275), (535, 783, 10, 6, 250), (557, 781, 11, 6, 268), (575, 784, 9, 6, 280), (549, 747, 9, 5, 265)]
for i, (bx, by, R0, n, rot) in enumerate(BUSH_PX):
    add(CM.palm(*P(bx, by), R0*1.15, n, rot, "cc_royal", "cc_azure", f"bush{i}", rng), "bush", Z["bush"] + 0.01*i, unit=f"bush{i}")
BIKE_REAR = (P(188.7, 0)[0], 476.0)
add(CM.bicycle(*BIKE_REAR, r=22.0, wb=84.0), "bike", Z["bike"], unit="bike")
FIG_FEET = (P(414.7, 0)[0], 499.0)
add(CM.figure(*FIG_FEET, H=118.0, wk=1.22), "figure", Z["figure"], unit="figure")

# ================================================================ sew order (stop order): details first, the dark connected tones last
SEW = [("window", None), ("glow", None), ("meteor", None), ("star", None), ("comet", None), ("cloud", None), ("haze", None),
       ("bush", None), ("lampglass", None), ("building", None), ("figure", None), ("rail", None), ("bike", None), ("overlay_ice", None)]
ORDER = [s for s, _ in SEW]
COLSEQ = ["cc_gold", "cc_rose", "cc_red", "cc_white", "cc_lilac", "cc_violet", "cc_azure", "cc_royal", "cc_ice", "cc_cloud", "cc_dusk", "cc_night"]
assert not [r for r in items if r["col"] not in COLSEQ], "colour outside the front palette"
for r in items:
    ov = r["sew"] in ("rail", "bike", "overlay_ice") or (r["grp"] == "FIG-line")
    # one stop per thread for the main art (layer 20+), overlays (railing, bicycle, figure fold lines) sew after the fills
    r["layer"] = (40 if ov else 20) + COLSEQ.index(r["col"])

META = dict(spine=SPINE.tolist(), n_stars=len(stars), star_moved=star_moved, n_meteors=len(METEORS_PX), n_strands=len(STRANDS) + 6, n_windows=len(WIN),
            n_far=len(FAR_PX), n_near=len(NEAR_PX), n_balusters=nb, n_bush=len(BUSH_PX),
            mock_map=dict(cfx=MM.CFX, necky=MM.NECKY, sx=MM.SX, sy=MM.SY), rail_px=(rail_y(130), rail_y(600)),
            bike_rear=BIKE_REAR, figure_feet=FIG_FEET)
pickle.dump(dict(items=items, meta=META), open("scene.pkl", "wb"))
from collections import Counter
print("items", len(items), dict(Counter(r["sew"] for r in items)), "stars", len(stars), "moved", star_moved, "windows", len(WIN), "balusters", nb)
