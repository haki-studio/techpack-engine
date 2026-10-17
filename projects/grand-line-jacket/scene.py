"""01 front scene — sunrise over a sea of clouds, composed on the size-M front (garment mm, unclipped).
Positions, outlines and tones are read from the mockup (inputs/front.png) through mockmap; motifs are drawn with
gl_motifs. Output: scene.pkl = {"items": [...], "meta": {...}}. Per-size clipping happens in art_size.py.
usage: python3 scene.py [preview]"""
import glcore
import math, random, pickle, sys
import numpy as np
from scipy import ndimage as ndi
from skimage import measure
from shapely.geometry import Point, Polygon, LineString, box, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity, prepared
import mockmap as MM, front as F, gl_motifs as GM

BB, PPM = (-330.0, -110.0, 330.0, 540.0), 2.0
HORIZON = 199.0                  # sea top edge (mockup y 363 px)
SUN = (45.0, 195.0)              # sun centre, wearer's left of the zip (mockup 413, 362 px)
CLIP_M = {s: F.clip_for("M", s) for s in "RL"}
# the tightest keep-outs over all sizes, in M coordinates (each size's clip scaled back by its grade): whole lobes on every size
LIM_ALL = {}
for _s in "RL":
    _g = CLIP_M[_s]
    for _sz in glcore.SIZES:
        _k = glcore.GRADE[_sz][1]; _g = _g.intersection(affinity.scale(F.clip_for(_sz, _s), 1/_k, 1/_k, origin=(0, 0)))
    LIM_ALL[_s] = _g.buffer(0)
ALLOWED_M = unary_union(list(CLIP_M.values()))

# ---------------------------------------------------------------- mockup masks in mm space
_rgb = np.array(MM.warp(BB, PPM)).astype(np.float32)
LUM = _rgb @ np.array([0.3, 0.59, 0.11], np.float32)
_mx, _mn = _rgb.max(2), _rgb.min(2); SAT = (_mx - _mn) / np.maximum(_mx, 1)
H, W = LUM.shape
YY, XX = np.mgrid[0:H, 0:W]; XMM = BB[0] + (XX + 0.5)/PPM; YMM = BB[1] + (YY + 0.5)/PPM
def disk(mm): r = int(round(mm*PPM)); y, x = np.ogrid[-r:r+1, -r:r+1]; return x*x + y*y <= r*r
PANEL = np.zeros((H, W), bool)
from PIL import Image, ImageDraw
_im = Image.new("L", (W, H), 0); _d = ImageDraw.Draw(_im)
for pnl in (F.PANEL_R, F.PANEL_L): _d.polygon([((x - BB[0])*PPM, (y - BB[1])*PPM) for x, y in pnl.exterior.coords], fill=255)
PANEL = np.array(_im) > 127
ZIP = np.abs(XMM) < 11
LIGHT = (LUM > 118) & PANEL & ~ZIP
SUNZONE = (((XMM - SUN[0])/48)**2 + ((YMM - SUN[1])/66)**2 < 1) & (YMM < HORIZON + 3) | ((np.abs(XMM - SUN[0]) < 17) & (YMM >= HORIZON - 3) & (YMM < 400))
CLOUDISH = (LUM > 72) & (SAT < 0.30) & PANEL & ~ZIP & ~SUNZONE & (YMM > 30)
_r, _g, _b = _rgb[..., 0], _rgb[..., 1], _rgb[..., 2]
TEAL = (((_g - _r) > 10) | ((_g - _b) > -6)) & (LUM > 38) & ~CLOUDISH & PANEL & ~ZIP

def mask_polys(mask, min_area=0.0, simplify=0.4):
    out = []
    lab, n = ndi.label(mask)
    for i in range(1, n + 1):
        m = lab == i
        if m.sum() / PPM**2 < min_area: continue
        m = ndi.binary_fill_holes(m)
        cs = measure.find_contours(np.pad(m, 1).astype(float), 0.5)
        ps = []
        for c in cs:
            if len(c) < 8: continue
            pts = [(BB[0] + (x - 1 + 0.5)/PPM, BB[1] + (y - 1 + 0.5)/PPM) for y, x in c]
            p = Polygon(pts).buffer(0)
            if p.area > 1: ps.append(p)
        if ps:
            g = max(ps, key=lambda p: p.area)
            out.append(g.simplify(simplify))
    return out

def sample_mean(geom, step=1.0):
    b = geom.bounds; vals = []
    for x in np.arange(b[0] + step/2, b[2], step):
        for y in np.arange(b[1] + step/2, b[3], step):
            if geom.contains(Point(x, y)):
                px, py = int((x - BB[0])*PPM), int((y - BB[1])*PPM)
                if 0 <= px < W and 0 <= py < H: vals.append(_rgb[py, px])
    if not vals:
        c = geom.representative_point(); px, py = int((c.x - BB[0])*PPM), int((c.y - BB[1])*PPM); vals = [_rgb[py, px]]
    return np.mean(vals, axis=0)

items = []
def add(regs, layer, z=None, **kw):
    for r in regs:
        g = r["geom"]
        if g is None or g.is_empty: continue
        r = dict(r); r.update(kw); r["layer"] = layer; r["z"] = layer*100000 + len(items) if z is None else z; r["el"] = "01"
        r.setdefault("ko", True); r.setdefault("kob", 0.0); r.setdefault("unit", None)
        items.append(r)

# ================================================================ clouds: banks (from the mockup mask) + islets (counted, A2)
cl_mask = ndi.binary_opening(CLOUDISH, structure=disk(1.6))
cl_mask = ndi.binary_closing(cl_mask, structure=disk(2.0)) & PANEL & ~ZIP
comps = mask_polys(cl_mask, min_area=60)
BANKS = []
for C in comps:
    C = C.buffer(1.0).buffer(-1.0); b = C.bounds
    if b[1] < HORIZON - 4 and C.area < 250: continue          # star centres
    if C.area > 900 or b[1] < HORIZON - 4: BANKS.append(C)
BANKS.sort(key=lambda c: c.bounds[0])

def sample_bright(geom, step=0.8):
    b = geom.bounds; vals = []
    for x in np.arange(b[0] + step/2, b[2], step):
        for y in np.arange(b[1] + step/2, b[3], step):
            if geom.contains(Point(x, y)):
                px, py = int((x - BB[0])*PPM), int((y - BB[1])*PPM)
                if 0 <= px < W and 0 <= py < H: vals.append(_rgb[py, px])
    if not vals: return sample_mean(geom)
    v = np.array(vals); l = v @ np.array([0.3, 0.59, 0.11]); k = l >= np.median(l)
    return v[k].mean(axis=0)

def tone_of(V, lobe):
    """tone from the mockup pixels under the lobe that are thread, not the dark gaps between lobes (lum > 85)"""
    bnd = V.bounds; vals = []
    for x in np.arange(bnd[0] + 0.4, bnd[2], 0.8):
        for y in np.arange(bnd[1] + 0.4, bnd[3], 0.8):
            if V.contains(Point(x, y)):
                px, py = int((x - BB[0])*PPM), int((y - BB[1])*PPM)
                if 0 <= px < W and 0 <= py < H: vals.append(_rgb[py, px])
    v = np.array(vals) if vals else np.array([sample_mean(V)])
    l = v @ np.array([0.3, 0.59, 0.11]); k = l > 85
    if k.sum() < 3: return "slate"
    r, g, b = v[k].mean(axis=0); lum = l[k].mean()
    if r > g + 2: return "cream" if lum > 165 else "sand"
    if lum > 185: return "cream"
    return "sage" if (g - b) > -2 else "slate"
def tone_islet(V, lobe):                                  # islets are cream with sand undersides (the sea shows through the samples)
    rb, gb, bb_ = sample_bright(V); lb = 0.3*rb + 0.59*gb + 0.11*bb_
    return "cream" if lb > 150 else "sand"

def colheight(C):
    def f(x):
        seg = C.intersection(LineString([(x, -400), (x, 800)]))
        return seg.length if not seg.is_empty else 0.0
    return f

def fits(lim, cx, cy, r): return lim is None or lim.contains(GM.ell(cx, cy, r))

def pack_var(C, Rf, rng, dy=0.42, dx=0.92, inset=0.5, rmin=2.6, lim=None):
    """rows of overlapping domes, radius from Rf(x, y); with `lim`, every dome lies wholly inside it (whole lobes at the keep-out)."""
    b = C.bounds; lobes = []; row = 0
    lim_g = lim; lim = prepared.prep(lim_g) if lim_g is not None else None
    y = b[3] - 0.45*Rf((b[0] + b[2])/2, b[3])
    while y > b[1] - 2:
        rs = []
        x = b[0] - 2 + (0.55 if row % 2 else 0.0)*Rf(b[0], y) + rng.uniform(-1, 1)
        while x < b[2] + 2:
            Rl = Rf(x, y); r = Rl*rng.uniform(0.72, 1.28)
            cx, cy = x + rng.uniform(-0.16, 0.16)*Rl, y + rng.uniform(-0.14, 0.14)*Rl
            inner = C.buffer(-inset*r)
            if not inner.is_empty and inner.contains(Point(cx, cy)):
                rr = r
                while rr > rmin and not fits(lim, cx, cy, rr): rr *= 0.85
                if fits(lim, cx, cy, rr) and rr >= rmin: lobes.append([cx, cy, rr]); rs.append(Rl)
            x += dx*Rl
        y -= dy*(np.median(rs) if rs else Rf((b[0] + b[2])/2, y)); row += 1
    for _ in range(4):                       # fill what the rows missed, with domes that still fit
        U = unary_union([GM.ell(cx, cy, r) for cx, cy, r in lobes]) if lobes else Polygon()
        miss = C.difference(U.buffer(0.3))
        if lim_g is not None: miss = miss.intersection(lim_g)
        added = 0
        for p in sorted(GM.polys(miss), key=lambda p: -p.area):
            c = p.representative_point(); Rl = Rf(c.x, c.y)
            if p.area < (0.4*Rl)**2: continue
            r = max(rmin, min(Rl, math.sqrt(p.area/math.pi)*1.3))
            while r > rmin and not fits(lim, c.x, c.y, r): r *= 0.85
            if r < rmin or not fits(lim, c.x, c.y, r): continue
            lobes.append([c.x, c.y, r]); added += 1
        if not added: break
    for l in lobes: l.append(l[1] + rng.uniform(-0.2, 0.2)*l[2])
    return lobes

bank_info = []
for i, C in enumerate(BANKS):
    side = "R" if C.centroid.x < 0 else "L"
    lim = LIM_ALL[side].buffer(-1.0)        # whole lobes, 1.2 inside the M keep-out (grades shift it a little)
    ch = colheight(C)
    Rf = lambda x, y, ch=ch: float(np.clip(0.17*ch(x), 5.0, 12.0))          # florets: the mockup lobes are ~6-17 mm
    rng = random.Random(100 + i)
    lobes = pack_var(C, Rf, rng, lim=lim)
    flat = HORIZON + 0.5 if C.bounds[3] < HORIZON + 6 else None
    regs, sil = GM.lobe_regions(lobes, tone_of, flat_y=flat, grp="CL")
    for r in regs: add([r], 16, z=16*100000 + len(items), kgrp=f"bank{i}")
    bank_info.append(dict(side=side, lobes=len(lobes), area=sil.area, bounds=sil.bounds))

# islets on the sea: counted on the mockup (front.png px centre, width px) - 11 across both halves
ISLETS_PX = [(303, 403, 47), (300, 433, 40), (287, 488, 15), (308, 522, 43), (280, 590, 74),
             (460, 432, 21), (501, 432, 18), (460, 483, 27), (453, 513, 14), (423, 530, 20), (484, 560, 78)]
islet_info = []
for i, (px, py, wp) in enumerate(ISLETS_PX):
    cx, cy = MM.P(px, py); w = wp*MM.SX; h = max(3.5, 0.21*w)
    side = "R" if cx < 0 else "L"; lim = LIM_ALL[side].buffer(-1.0)
    dome = lambda x0, y0: affinity.scale(Point(x0, y0).buffer(1.0, quad_segs=24), w/2, h, origin=(x0, y0)).intersection(box(x0 - w, y0 - 2*h, x0 + w, y0 + 0.25*h))
    D = dome(cx, cy); moved = (0.0, 0.0)
    if not lim.contains(D):                       # nudge (never drop) so the whole islet clears the welt / seams
        best = None
        for rr in np.arange(1, 40, 1.0):
            for th in np.linspace(0, 2*math.pi, 24, endpoint=False):
                if lim.contains(dome(cx + rr*math.cos(th), cy + rr*math.sin(th))): best = (rr*math.cos(th), rr*math.sin(th)); break
            if best: break
        if best: moved = best; cx, cy = cx + best[0], cy + best[1]; D = dome(cx, cy)
    rng = random.Random(300 + i)
    Rf = lambda x, y, h=h: float(np.clip(0.62*h, 2.6, 6.0))
    lobes = pack_var(D.buffer(0.4), Rf, rng, dy=0.5, dx=0.95, rmin=2.4, lim=lim)
    if not lobes: lobes = [[cx, cy, max(2.6, h*0.6), cy]]
    regs, sil = GM.lobe_regions(lobes, tone_islet, flat_y=D.bounds[3] + 0.3, grp="ISL", unit=f"islet{i}")
    for r in regs: add([r], 17, z=17*100000 + len(items), unit=f"islet{i}", kgrp=f"islet{i}")
    islet_info.append(dict(px=(px, py), mm=(round(cx, 1), round(cy, 1)), w=round(w, 1), moved=moved, lobes=len(lobes)))
CLOUD_U = unary_union([r["geom"] for r in items if 16 <= r["layer"] < 18]).buffer(0.6)
for r in items:
    if 16 <= r["layer"] < 18 and r.get("ko", True): r["kob"] = 0.5      # sea / rays / glow stop 0.5 short of the cloud edge

# ================================================================ sun, fine sunburst, radial glow
BURST = [(-166.5, 25), (-157, 34), (-148.5, 42), (-121, 46), (-90, 54), (-65.5, 26), (-47.5, 50), (-21.5, 46), (-13, 32)]
add(GM.sun(*SUN, flat_y=HORIZON + 0.6), 15)
add(GM.burst(*SUN, BURST, 8.4, 1.05, 0.82), 15)                                     # hairline satin rays
add(GM.burst(*SUN, [(-178.5, 62), (-1.5, 62)], 8.4, 1.1, 0.82, col="gl_pale"), 15)   # flare along the horizon
GLOW_ENV = affinity.scale(Point(SUN[0], HORIZON).buffer(1.0, quad_segs=48), 96, 90, origin=(SUN[0], HORIZON)).intersection(box(-400, -400, 400, HORIZON - 1.5))
GLOW_ENV2 = affinity.scale(Point(SUN[0], HORIZON).buffer(1.0, quad_segs=64), 105, 95, origin=(SUN[0], HORIZON)).intersection(box(-400, -400, 400, HORIZON - 1.2))
for k, a in enumerate(np.arange(-178.5, -1.0, 1.5)):   # dense radial hairline glow behind the sun (close-ups)
    t = math.radians(a); r0 = 9.0 + (k % 3) * 7.0
    L1 = 34 + 16*abs(math.sin(t*2.3 + 0.7)); L2 = L1 + 12 + 16*abs(math.sin(t*3.7))
    for (ra, rb, col, lay) in ((r0, L1, "gl_teal", 11), (L1 - 6, L2, "gl_deep", 10.8)):
        ln = LineString([(SUN[0] + ra*math.cos(t), SUN[1] + ra*math.sin(t)), (SUN[0] + rb*math.cos(t), SUN[1] + rb*math.sin(t))])
        g_ = ln.buffer(0.22, cap_style="round").intersection(GLOW_ENV2)
        if not g_.is_empty: add([GM.R(col, g_, "run", None, "GLW", kob=0.0)], lay)
# dot ends on the longer burst rays (close-ups)
for a, L in BURST:
    if L >= 40:
        t = math.radians(a); add([GM.R("gl_gold", Point(SUN[0] + (L + 2.2)*math.cos(t), SUN[1] + (L + 2.2)*math.sin(t)).buffer(0.9, quad_segs=10), "satin", "auto", "DOT", kob=0.4)], 15)

# ================================================================ sea: horizon line, dash field, glitter path
add([GM.R("gl_pale", LineString([(-300, HORIZON + 0.6), (300, HORIZON + 0.6)]).buffer(0.45), "bean", None, "HZ", kob=0.3)], 13)
SEAISH = (TEAL | LIGHT) & (YMM > HORIZON + 0.5) & ~ndi.binary_dilation(cl_mask, structure=disk(1.5))
# the mockup's own welts (drawn 18-40 mm from where the pattern puts them): their dark pixels are not "no sea"
MOCK_WELTS = unary_union([LineString([MM.P(128, 566), MM.P(250, 453)]).buffer(17), LineString([MM.P(622, 566), MM.P(500, 453)]).buffer(17)])
_wm = Image.new("L", (W, H), 0); _wd = ImageDraw.Draw(_wm)
for p in GM.polys(MOCK_WELTS): _wd.polygon([((x - BB[0])*PPM, (y - BB[1])*PPM) for x, y in p.exterior.coords], fill=255)
WELTM = np.array(_wm) > 127
LUM = np.where(WELTM, np.maximum(LUM, 66.0), LUM)
SEAISH = SEAISH | (WELTM & (YMM > HORIZON + 30))
def lum_at(x0, x1, y, q=60):
    py = int((y - BB[1])*PPM); a = int((x0 - BB[0])*PPM); b = max(a + 1, int((x1 - BB[0])*PPM))
    seg = LUM[max(0, py-1):py+2, max(0, a):min(W, b)]
    return float(np.percentile(seg, q)) if seg.size else 0.0
GLITTER_X = (SUN[0] - 13, SUN[0] + 13)
_sm = ndi.gaussian_filter(SEAISH.astype(np.float32), 3.0*PPM) > 0.05
_sm = ndi.binary_opening(ndi.binary_closing(_sm, structure=disk(3.0)), structure=disk(2.0)) & (YMM > HORIZON + 1.0)
_sp = mask_polys(_sm, min_area=200, simplify=0.8)
SEA_SIL = unary_union([Polygon(p.buffer(3.0).buffer(-3.0).exterior) if p.buffer(3.0).buffer(-3.0).geom_type == 'Polygon' else p for p in _sp]).intersection(box(-400, HORIZON + 1.0, 400, 600)).difference(CLOUD_U).buffer(0)
SIL_IN = prepared.prep(SEA_SIL.buffer(-0.3))
def sea_col(lv):
    if lv < 30: return None                        # navy shows (gap in the mockup)
    return "gl_deep" if lv < 56 else ("gl_teal" if lv < 80 else ("gl_tealt" if lv < 115 else "gl_foam"))
rng = random.Random(7); sea_bars = 0; y = HORIZON + 1.9; rows = 0
while y < 470:
    t = min(1.0, (y - HORIZON) / 210.0)
    hgt = 1.45 + 0.75*t; vgap = 0.6 + 0.9*t          # perspective: rows open up toward the viewer
    x = -300 + rng.uniform(0, 5)
    while x < 300:
        L = rng.uniform(4, 26) * (1.3 - 0.5*t)
        x1 = x + L
        if (x < 15.5 and x1 > -15.5) or (GLITTER_X[0] - 2 < x1 and x < GLITTER_X[1] + 2 and y < 400) or not SIL_IN.contains(LineString([(x, y), (x1, y)])):
            x += rng.uniform(1.2, 3.0); continue
        col = sea_col(lum_at(x, x1, y, 75))
        if col and x1 - x >= 3.0:
            bar = LineString([(x + hgt/2, y), (x1 - hgt/2, y)]).buffer(hgt/2, cap_style="round")
            add([GM.R(col, bar, "tatami", 0.0, "SEA-hl" if col == "gl_foam" else "SEA", kob=0.0)], 12)
            sea_bars += 1
        x = x1 + rng.uniform(0.6, 1.1) + 1.2*t*rng.random()
    y += hgt + vgap; rows += 1

y = HORIZON + 2.2                                      # glitter path under the sun
while y < 400:
    t = min(0.99, (y - HORIZON) / 190.0)
    wmax = 24*(1 - t)**0.8 + 5
    lv = lum_at(SUN[0] - wmax/2, SUN[0] + wmax/2, y, 70)
    hgt = 1.5 + 0.5*t
    if lv > 80:
        w = wmax*rng.uniform(0.55, 1.0); cx = SUN[0] + rng.uniform(-2.5, 2.5)
        parts = [(cx - w/2, cx + w/2)] if w < 12 or rng.random() < 0.5 else [(cx - w/2, cx - 0.9), (cx + 0.9, cx + w/2)]
        for a_, b_ in parts:
            if b_ - a_ < 3: continue
            add([GM.R("gl_pale" if lv > 125 else "gl_foam", LineString([(a_ + hgt/2, y), (b_ - hgt/2, y)]).buffer(hgt/2, cap_style="round"),
                      "tatami", 0.0, "GLT", kob=0.0)], 12.5)
    y += hgt + 0.6 + 0.8*t

# ================================================================ dashed gold rays across the sea (as in the mockup)
RAYS = [8.0, 20.0, 42.0, 68.0, 88.0, 125.5, 142.0, 162.0, 171.0, 176.5]
ray_info = []
for i, a_ in enumerate(RAYS):
    t = math.radians(a_); ux, uy = math.cos(t), math.sin(t)
    r0 = max((HORIZON + 3.0 - SUN[1]) / max(uy, 1e-3), 10.0)
    far = LineString([(SUN[0] + ux*r0, SUN[1] + uy*r0), (SUN[0] + ux*600, SUN[1] + uy*600)]).intersection(SEA_SIL.buffer(4.0).intersection(ALLOWED_M.buffer(-0.5)))
    segs = [far] if far.geom_type == "LineString" else [g for g in getattr(far, "geoms", []) if g.geom_type == "LineString"]
    segs = [g for g in segs if g.length > 8]
    if not segs: continue
    pA = (SUN[0] + ux*r0, SUN[1] + uy*r0)
    pB = max([g.coords[0] for g in segs] + [g.coords[-1] for g in segs], key=lambda p: math.hypot(p[0]-SUN[0], p[1]-SUN[1]))
    regs = [r for r in GM.dashed(pA, pB, 4.6, 2.6, 0.85, 0.45, phase=(i*1.7) % 7.2) if r["st"] == "bean"]   # dashes only, fabric gaps
    for r in regs: r["kob"] = 0.35
    add(regs, 14)
    ray_info.append(dict(angle=a_, start=pA, end=pB))

# ================================================================ stars (every mockup star, position + type)
STARS_PX = {
 "big":   [(216.7, 223.3), (501.7, 218.3)],
 "med":   [(298, 300), (310, 277), (288, 245), (254, 198), (180, 193), (530, 172), (435, 248), (585, 248), (461, 303)],
 "small": [(213, 157), (233, 255), (336, 247), (331, 301), (319, 323), (500, 168), (563, 191), (503, 258), (535, 248), (476, 268), (413, 273)],
 "dot":   [(237, 180), (260, 165), (202, 185), (187, 224), (154, 235), (207, 256), (263, 230), (306, 227), (341, 277), (263, 280), (276, 271),
           (272, 298), (272, 313), (487, 183), (457, 222), (555, 224), (459, 278), (517, 275), (499, 291), (486, 309), (596, 273)],
}
stars = []
for kind, pts in STARS_PX.items():
    for px, py in pts:
        cx, cy = MM.P(px, py); u = f"star{len(stars)}"; stars.append((cx, cy, kind))
        if kind == "big":     regs = GM.star(cx, cy, 15.0, 10.5, 1.35, "big", u)       # long thin arms + short diagonals
        elif kind == "med":   regs = GM.star(cx, cy, 10.0, 6.0, 1.1, "sparkle", u)     # long-armed sparkle
        elif kind == "small": regs = GM.star(cx, cy, 3.8, 3.0, 1.15, "cross", u)
        else:                 regs = GM.star(cx, cy, 1.9, 0, 0, "dot", u)
        add(regs, 18, unit=u)

# ================================================================ sew order: one stop per thread (scale dashes after the cloud bodies)
SEW = ["gl_deep", "gl_teal", "gl_tealt", "gl_foam", "gl_pale", "gl_gold", "gl_shadow", "gl_slate", "gl_sage", "gl_sagelt", "gl_sand", "gl_cream"]
for r in items:
    r["vlayer"] = r["layer"]
    r["layer"] = (40 if r.get("sub") == "scale" else 20) + SEW.index(r["col"])

META = dict(horizon=HORIZON, sun=SUN, rays=ray_info, burst=BURST, banks=bank_info, islets=islet_info, n_islets=len(ISLETS_PX), n_stars=len(stars),
            sea_bars=sea_bars, sea_rows=rows, mock_map=dict(cfx=MM.CFX, necky=MM.NECKY, sx=MM.SX, sy=MM.SY))
pickle.dump(dict(items=items, meta=META), open("scene.pkl", "wb"))
print("items", len(items), "banks", [(b["side"], b["lobes"]) for b in bank_info], "islets", len(islet_info), [i["moved"] for i in islet_info if any(i["moved"])],
      "stars", len(stars), "sea dashes", sea_bars, "rows", rows, "rays", len(ray_info))
