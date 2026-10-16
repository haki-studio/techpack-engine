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

# ================================================================ clouds: banks + islets
cl_mask = ndi.binary_opening(CLOUDISH, structure=disk(1.6))
cl_mask = ndi.binary_closing(cl_mask, structure=disk(2.0)) & PANEL & ~ZIP
comps = mask_polys(cl_mask, min_area=60)
BANKS, ISLETS = [], []
for C in comps:
    C = C.buffer(1.0).buffer(-1.0)
    b = C.bounds; cy = (b[1] + b[3])/2
    if b[1] < HORIZON - 4 and C.area < 250: continue          # star centres
    if C.area > 900 or b[1] < HORIZON - 4:
        BANKS.append(C)
    elif C.area > 25:
        ISLETS.append(C)
BANKS.sort(key=lambda c: c.bounds[0]); ISLETS.sort(key=lambda c: (c.bounds[1], c.bounds[0]))

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
    r, g, b = sample_bright(V)
    lum = 0.3*r + 0.59*g + 0.11*b
    warm = r >= g - 1
    if warm: return "cream" if lum > 172 else "sand"
    return "sage" if lum >= 118 else "slate"

def colheight(C):
    def f(x):
        seg = C.intersection(LineString([(x, -400), (x, 800)]))
        return seg.length if not seg.is_empty else 0.0
    return f

def pack_var(C, Rf, rng, dy=0.42, dx=0.92, inset=0.5, rmin=2.6, lim=None):
    """rows of overlapping discs, radius from Rf(x, y)."""
    b = C.bounds; lobes = []; row = 0
    y = b[3] - 0.45*Rf((b[0] + b[2])/2, b[3])
    while y > b[1] - 2:
        rs = []
        x = b[0] - 2 + (0.55 if row % 2 else 0.0)*Rf(b[0], y) + rng.uniform(-1, 1)
        while x < b[2] + 2:
            Rl = Rf(x, y); r = Rl*rng.uniform(0.72, 1.28)
            cx, cy = x + rng.uniform(-0.16, 0.16)*Rl, y + rng.uniform(-0.14, 0.14)*Rl
            inner = C.buffer(-inset*r)
            if not inner.is_empty and inner.contains(Point(cx, cy)) and (lim is None or lim.contains(Point(cx, cy).buffer(0.85*r))):
                lobes.append([cx, cy, r]); rs.append(Rl)
            x += dx*Rl
        y -= dy*(np.median(rs) if rs else Rf((b[0] + b[2])/2, y)); row += 1
    for _ in range(3):
        U = unary_union([Point(cx, cy).buffer(r) for cx, cy, r in lobes]) if lobes else Polygon()
        miss = C.difference(U.buffer(0.3)); added = 0
        for p in sorted(GM.polys(miss), key=lambda p: -p.area):
            c = p.representative_point(); Rl = Rf(c.x, c.y)
            if p.area < (0.4*Rl)**2: continue
            r = max(rmin, min(Rl, math.sqrt(p.area/math.pi)*1.3))
            if lim is not None and not lim.contains(Point(c.x, c.y).buffer(0.85*r)):
                r = max(rmin, min(r, lim.exterior.distance(Point(c.x, c.y)) / 0.85 if lim.contains(Point(c.x, c.y)) else 0))
                if r <= rmin or not lim.contains(Point(c.x, c.y).buffer(0.85*r)): continue
            lobes.append([c.x, c.y, r]); added += 1
        if not added: break
    lobes = [l for l in lobes if l[2] >= rmin]
    for l in lobes: l.append(l[1] + rng.uniform(-0.2, 0.2)*l[2])
    return lobes

bank_info = []
for i, C in enumerate(BANKS):
    side = "R" if C.centroid.x < 0 else "L"
    # stop the bank ~ 1 lobe short of the seam keep-outs: lobes end in scallops instead of a cut edge
    lim = CLIP_M[side].buffer(1.0)
    Cc = C
    ch = colheight(Cc)
    Rf = lambda x, y, ch=ch: float(np.clip(0.22*ch(x), 5.0, 14.0))
    rng = random.Random(100 + i)
    lobes = pack_var(Cc, Rf, rng, lim=lim)
    flat = HORIZON + 0.5 if C.bounds[3] < HORIZON + 6 else None
    regs, sil = GM.lobe_regions(lobes, tone_of, flat_y=flat, grp="CL")
    for r in regs: add([r], 16 + GM.SUB[r["sub"]], z=16*100000 + len(items), kgrp=f"bank{i}")
    bank_info.append(dict(side=side, lobes=len(lobes), area=sil.area, bounds=sil.bounds))

for i, C in enumerate(ISLETS):
    b = C.bounds; h = b[3] - b[1]
    rng = random.Random(300 + i)
    Rf = lambda x, y, h=h: float(np.clip(0.5*h, 3.0, 7.0))
    lobes = pack_var(C.buffer(0.6), Rf, rng, dy=0.5, dx=1.05, rmin=2.6)
    if not lobes:
        c = C.centroid; lobes = [[c.x, c.y, max(2.6, h*0.45), c.y]]
    regs, sil = GM.lobe_regions(lobes, tone_of, flat_y=b[3] + 0.4, grp="ISL", unit=f"islet{i}")
    for r in regs: add([r], 17 + GM.SUB[r["sub"]], z=17*100000 + len(items), unit=f"islet{i}", kgrp=f"islet{i}")
CLOUD_U = unary_union([r["geom"] for r in items if 16 <= r["layer"] < 18]).buffer(0.6)
for r in items:
    if 16 <= r["layer"] < 18: r["kob"] = 0.5            # sea / rays / glow stop 0.5 short of the cloud edge

# ================================================================ sun, sunburst, sky glow
BURST = [(-166.5, 25), (-157, 34), (-148.5, 42), (-121, 46), (-90, 54), (-65.5, 26), (-47.5, 50), (-21.5, 46), (-13, 32),
         (-178.5, 62), (-1.5, 62)]                       # last two = flare along the horizon
add(GM.sun(*SUN, flat_y=HORIZON + 0.6), 15)
add(GM.burst(*SUN, [(a, L) for a, L in BURST if abs(a) not in (178.5, 1.5)], 8.6, 1.7, 0.9), 15)
add(GM.burst(*SUN, [(a, L) for a, L in BURST if abs(a) in (178.5, 1.5)], 8.6, 1.5, 0.9, col="gl_pale"), 15)
GLOW_ENV = affinity.scale(Point(SUN[0], HORIZON).buffer(1.0, quad_segs=48), 96, 90, origin=(SUN[0], HORIZON)).intersection(box(-400, -400, 400, HORIZON - 1.5))
for k, r in enumerate(np.arange(15.0, 112.0, 9.5)):
    reg = GM.arc_line(SUN[0], SUN[1], r, -179, -1, 0.55, "gl_teal" if r < 70 else "gl_deep")
    reg["geom"] = reg["geom"].intersection(GLOW_ENV)
    add([reg], 11)

# ================================================================ sea: horizon line, bars, glitter path
add([GM.R("gl_foam", LineString([(-300, HORIZON + 0.6), (300, HORIZON + 0.6)]).buffer(0.45), "bean", None, "HZ", kob=0.0, ko=False)], 13)
SEAISH = (TEAL | LIGHT) & (YMM > HORIZON + 0.5) & ~ndi.binary_dilation(cl_mask, structure=disk(1.5))
DENS = ndi.uniform_filter(SEAISH.astype(np.float32), size=(int(2.5*PPM), int(7*PPM)))
def dens(x, y):
    px, py = int((x - BB[0])*PPM), int((y - BB[1])*PPM)
    return float(DENS[py, px]) if 0 <= px < W and 0 <= py < H else 0.0
def lum_at(x0, x1, y):
    py = int((y - BB[1])*PPM); a = int((x0 - BB[0])*PPM); b = max(a + 1, int((x1 - BB[0])*PPM))
    seg = LUM[max(0, py-1):py+2, max(0, a):min(W, b)]
    return float(np.percentile(seg, 70)) if seg.size else 0.0

GLITTER_X = (SUN[0] - 13, SUN[0] + 13)
SEA_SUB = {"gl_foam": 12.1, "gl_pale": 12.1, "gl_tealt": 12.2, "gl_teal": 12.3, "gl_deep": 12.4}
DENSE_Y = HORIZON + 95.0                          # solid sea down to here, then rows with fabric between them

# sea silhouette from the mockup
_sm = ndi.gaussian_filter(SEAISH.astype(np.float32), 2.0*PPM) > 0.13
_sm = ndi.binary_opening(ndi.binary_closing(_sm, structure=disk(3.0)), structure=disk(2.5)) & (YMM > HORIZON + 1.0)
_sp = mask_polys(_sm, min_area=300, simplify=0.8)
SEA_SIL = unary_union([p.buffer(3.0).buffer(-3.0) for p in _sp]).intersection(box(-400, HORIZON + 1.0, 400, 600))
SEA_SIL = SEA_SIL.difference(box(-15.5, -500, 15.5, 900)).difference(CLOUD_U).buffer(0)

# rays fanning from the sun over the sea (continuous gold bean lines)
RAYS = [8.0, 20.0, 42.0, 68.0, 88.0, 125.5, 142.0, 162.0, 171.0, 176.5]
ray_info = []; RAY_LINES = []
for i, a_ in enumerate(RAYS):
    t = math.radians(a_); ux, uy = math.cos(t), math.sin(t)
    r0 = max((HORIZON + 3.0 - SUN[1]) / max(uy, 1e-3), 10.0)
    far = LineString([(SUN[0] + ux*r0, SUN[1] + uy*r0), (SUN[0] + ux*600, SUN[1] + uy*600)]).intersection(SEA_SIL.buffer(4.0).intersection(ALLOWED_M.buffer(-0.5)))
    segs = [far] if far.geom_type == "LineString" else [g for g in getattr(far, "geoms", []) if g.geom_type == "LineString"]
    segs = [g for g in segs if g.length > 8]
    if not segs: continue
    pA = (SUN[0] + ux*r0, SUN[1] + uy*r0)
    pB = max([g.coords[0] for g in segs] + [g.coords[-1] for g in segs], key=lambda p: math.hypot(p[0]-SUN[0], p[1]-SUN[1]))
    L = LineString([pA, pB]); RAY_LINES.append(L)
    add([GM.R("gl_gold", L.buffer(0.4, cap_style="round"), "bean", None, "RAY", kob=0.0, ko=False)], 14)     # overlay: the field runs under it
    ray_info.append(dict(angle=a_, start=pA, end=pB))

# rows (perspective: closer under the horizon)
rows = []; y = HORIZON + 2.1
while y < 470:
    t = (y - HORIZON) / 200.0; hgt = 1.55 + 0.6*min(1, t); pitch = hgt + (0.0 if y < DENSE_Y else 0.62 + 1.1*min(1, t))
    rows.append((y, hgt)); y += max(pitch, hgt + 0.0001) if y >= DENSE_Y else hgt + 0.62
# dark field: solid under the horizon, rows below, tied together by bands along each ray (one connected object)
FIELD = SEA_SIL.intersection(box(-400, HORIZON + 1.0, 400, DENSE_Y)).buffer(0)
FIELD = FIELD.difference(box(-15.5, -500, 15.5, 900))
FIELD = unary_union([p for p in GM.polys(FIELD) if p.area > 25])
# cut into ~45 x 30 mm cells: each cell sews as its own object (short internal moves; long ones overflow the router)
_cells = []
_grid = [(cy_, 30.0, 45.0) for cy_ in np.arange(HORIZON + 1.0, DENSE_Y - 1, 30.0)]
_grid = [(a, min(h, DENSE_Y - a), w) for a, h, w in _grid]
for k_, (cy_, ch_, cw_) in enumerate(_grid):
    off = cw_/2 if k_ % 2 else 0.0
    for cx_ in np.arange(-400 - off, 400, cw_):
        q = FIELD.intersection(box(cx_, cy_, cx_ + cw_, cy_ + ch_))
        _cells += [g for g in GM.polys(q) if g.area > 4]
add([GM.R("gl_deep", g, "tatami", 0.0, "SEA-field", kob=0.0) for g in _cells], 12.4, z=12*100000 - 1)

# lighter dashes: holes in the field under the horizon; below it, chains of dashes on the fabric
rng = random.Random(7); sea_bars = 0
SIL_IN = prepared.prep(SEA_SIL.buffer(-0.4))
def blocked(x, x1, y):
    return (x < 15.5 and x1 > -15.5) or (GLITTER_X[0] - 2 < x1 and x < GLITTER_X[1] + 2 and y < 400) or not SIL_IN.contains(LineString([(x, y), (x1, y)]))
lower_rows = []
for y, hgt in rows:
    if y >= DENSE_Y: continue
    x = -300 + rng.uniform(0, 8)
    while x < 300:
        L = rng.uniform(7, 34); x1 = x + L
        if blocked(x, x1, y): x += rng.uniform(1.5, 4.0); continue
        lv = lum_at(x, x1, y)
        col = "gl_foam" if lv > 150 else ("gl_tealt" if lv > 106 else ("gl_teal" if lv > 74 else None))
        if col:
            bar = LineString([(x + hgt/2, y), (x1 - hgt/2, y)]).buffer(hgt/2, cap_style="round")
            add([GM.R(col, bar, "tatami", 0.0, "SEA-hl" if col == "gl_foam" else "SEA", kob=0.0)], SEA_SUB[col]); sea_bars += 1
        x = x1 + rng.uniform(1.0, 6.0)
y = DENSE_Y + 1.0
while y < 470:
    t = (y - HORIZON) / 200.0; hgt = 1.6 + 0.5*min(1, t)
    x = -300 + rng.uniform(0, 10)
    while x < 300:
        clen = rng.uniform(40, 120); xs, xe = x, x + clen
        lv = lum_at(xs, xe, y); col = "gl_tealt" if lv > 112 else ("gl_teal" if lv > 78 else "gl_deep")
        n_ok = 0
        while x < xe:
            L = rng.uniform(6, 22); x1 = min(x + L, xe)
            if x1 - x >= 3.5 and not blocked(x, x1, y):
                c = col
                bar = LineString([(x + hgt/2, y), (x1 - hgt/2, y)]).buffer(hgt/2, cap_style="round")
                add([GM.R(c, bar, "tatami", 0.0, "SEA-hl" if c == "gl_foam" else "SEA", kob=0.0)], SEA_SUB[c]); sea_bars += 1; n_ok += 1
            x = x1 + rng.uniform(1.0, 2.0)
        x += rng.uniform(8, 24)
    y += hgt + 1.0 + 1.6*min(1, t)

# glitter path under the sun (sewn before the field: its travel hides under the field)
y = HORIZON + 2.4; k = 0
while y < 392:
    t = min(0.99, (y - HORIZON) / 190.0)
    wmax = 24*(1 - t)**0.8 + 5
    lv = lum_at(SUN[0] - wmax/2, SUN[0] + wmax/2, y)
    hgt = 1.6 + 0.4*t
    if lv > 85:
        w = wmax*rng.uniform(0.55, 1.0); cx = SUN[0] + rng.uniform(-2.5, 2.5)
        parts = [(cx - w/2, cx + w/2)] if w < 12 or rng.random() < 0.5 else [(cx - w/2, cx - 0.9), (cx + 0.9, cx + w/2)]
        for a_, b_ in parts:
            if b_ - a_ < 3: continue
            add([GM.R("gl_pale" if t < 0.45 and lv > 120 else "gl_foam", LineString([(a_ + hgt/2, y), (b_ - hgt/2, y)]).buffer(hgt/2, cap_style="round"),
                      "tatami", 0.0, "GLT", kob=0.0)], 12.05, z=13*100000 + len(items))
    y += hgt + 0.7 + 0.5*t; k += 1

# ================================================================ stars
burst_mask = Image.new("L", (W, H), 0); bd = ImageDraw.Draw(burst_mask)
for a, L in BURST:
    t = math.radians(a); p1 = (SUN[0] + math.cos(t)*(L + 6), SUN[1] + math.sin(t)*(L + 6))
    bd.line([((SUN[0] - BB[0])*PPM, (SUN[1] - BB[1])*PPM), ((p1[0] - BB[0])*PPM, (p1[1] - BB[1])*PPM)], fill=255, width=int(5*PPM))
BURSTM = np.array(burst_mask) > 127
TOPHAT = LUM - ndi.grey_opening(LUM, size=(int(5*PPM), int(5*PPM)))
sky = ndi.binary_closing((TOPHAT > 38) & (LUM > 80) & PANEL & ~ZIP, structure=disk(0.6)) & (YMM < HORIZON - 3) & ~ndi.binary_dilation(cl_mask, structure=disk(3.0)) & ~BURSTM & (np.hypot(XMM - SUN[0], YMM - SUN[1]) > 12)
lab, n = ndi.label(ndi.binary_dilation(sky, structure=disk(0.6)) & ~ndi.binary_dilation(cl_mask, structure=disk(3.0)) & ~BURSTM, structure=np.ones((3, 3)))
stars = []
for i, sl in enumerate(ndi.find_objects(lab), 1):
    m = lab[sl] == i; a = m.sum()/PPM**2
    if a < 0.4 or a > 160: continue
    ys, xs = np.nonzero(m); cx = BB[0] + (sl[1].start + xs.mean() + 0.5)/PPM; cy = BB[1] + (sl[0].start + ys.mean() + 0.5)/PPM
    w = (xs.max() - xs.min() + 1)/PPM; h = (ys.max() - ys.min() + 1)/PPM
    peak = float(LUM[sl][m].max())
    if math.hypot(cx - SUN[0], cy - SUN[1]) < 78: continue           # sun glow texture, not stars
    if not ALLOWED_M.buffer(-1.0).contains(Point(cx, cy)): continue  # outside the keep-outs (shoulder corners = background)
    if peak < 110 or (max(w, h) < 2.6 and a < 0.8): continue          # noise
    stars.append((cx, cy, w, h, a))
# star field read off the mockup grid (front.png px): auto-detection loses the thin sparkle arms and the faint dots
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
        if kind == "big":    regs = GM.star(cx, cy, 13.0, 9.0, 1.9, "big", u)
        elif kind == "med":  regs = GM.star(cx, cy, 7.0, 5.0, 1.5, "sparkle", u)
        elif kind == "small": regs = GM.star(cx, cy, 3.8, 3.0, 1.2, "cross", u)
        else:                regs = GM.star(cx, cy, 1.9, 0, 0, "dot", u)
        add(regs, 18, unit=u)

META = dict(horizon=HORIZON, sun=SUN, rays=ray_info, burst=BURST, banks=bank_info, n_islets=len(ISLETS), n_stars=len(stars),
            sea_bars=sea_bars, mock_map=dict(cfx=MM.CFX, necky=MM.NECKY, sx=MM.SX, sy=MM.SY))
pickle.dump(dict(items=items, meta=META), open("scene.pkl", "wb"))
print("items", len(items), "banks", len(BANKS), [ (b["side"], b["lobes"]) for b in bank_info], "islets", len(ISLETS), "stars", len(stars), "sea bars", sea_bars, "rays", len(ray_info))

if "preview" in sys.argv:
    from render import geom_to_path
    from motifs2 import HEX
    import cairosvg
    x0, y0, x1, y1 = -320, -100, 320, 520
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {x1-x0} {y1-y0}" width="{(x1-x0)*3}" height="{(y1-y0)*3}">',
         f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#FFFFFF"/>']
    for pnl in (F.PANEL_R, F.PANEL_L): o.append(f'<path d="{geom_to_path(pnl)}" fill="{glcore.FABRIC}" stroke="#555" stroke-width="0.8"/>')
    for s in "RL": o.append(f'<path d="{geom_to_path(CLIP_M[s])}" fill="none" stroke="#FF4040" stroke-width="0.4" stroke-dasharray="2 1.5"/>')
    for r in sorted(items, key=lambda r: r["z"]):
        o.append(f'<path d="{geom_to_path(r["geom"])}" fill="{HEX[r["col"]]}" fill-rule="evenodd"/>')
    o.append('</svg>')
    cairosvg.svg2png(bytestring="".join(o).encode(), write_to="out/scene_raw.png", output_width=1600)
