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
    if b[1] < HORIZON - 4 or (C.area > 900 and (b[0] < -240 or b[2] > 240)): BANKS.append(C)   # sky banks + the side-seam sea banks
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
def tone_islet(V, lobe):                                  # islets: cream florets, sand shading, pale rims (close-ups)
    return "cream"

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

# ---------------------------------------------------------------- banks: broad billowing envelopes (review C1)
def column_profile(E):
    """top and bottom y of envelope E per x (1 mm steps)"""
    b = E.bounds; xs = np.arange(math.floor(b[0]), math.ceil(b[2]) + 1, 1.0); top, bot = {}, {}
    for x in xs:
        seg = E.intersection(LineString([(x, -400), (x, 800)]))
        if seg.is_empty: continue
        bb = seg.bounds; top[x] = bb[1]; bot[x] = bb[3]
    return top, bot

def bank_tone(cx, cy, r, top, bot, rng):
    """tone by height inside the bank: upper ~60 % sage with slate pockets, cream at the base / front lobes"""
    x = float(round(cx)); x = min(top, key=lambda k: abs(k - x)) if x not in top else x
    t = (cy - top[x]) / max(8.0, bot[x] - top[x])
    pocket = math.sin(cx * 0.071 + 1.3) * math.sin(cy * 0.093 + 0.4)
    if t > 0.64: return "cream" if (t > 0.72 or rng.random() < 0.6) else "sand"
    if t > 0.52: return "sand" if rng.random() < 0.5 else "sage"
    if 0.22 < t and pocket > 0.5: return "slate"
    return "sage"

bank_info = []
for i, C in enumerate(BANKS):
    side = "R" if C.centroid.x < 0 else "L"
    lim = LIM_ALL[side].buffer(-1.0)
    E = C.buffer(3.0).buffer(-3.0).intersection(lim)
    big = E.buffer(-14).buffer(14)                       # rounds the shoulders, removes towers < 28 mm wide
    mid = Polygon()
    low = E.intersection(box(-400, HORIZON - 26, 400, 900)).buffer(-5).buffer(5)    # keep the base detail near the horizon
    E = unary_union([big, mid, low]).intersection(lim).buffer(0)
    if E.is_empty or E.area < 300: continue
    E = max(GM.polys(E), key=lambda p: p.area) if E.geom_type != "Polygon" else E
    top, bot = column_profile(E)
    ch = colheight(E)
    Rf = lambda x, y, ch=ch: float(np.clip(0.12*ch(x), 4.2, 9.0))            # dense florets (close-ups), not big bubbles
    rng = random.Random(100 + i)
    lobes = pack_var(E, Rf, rng, dy=0.40, dx=0.88, lim=lim)
    flat = HORIZON + 0.5 if C.bounds[3] < HORIZON + 6 else None
    tones = {}; sea_bank = C.bounds[1] > HORIZON - 4          # below-horizon bank (FR lower left): cream with sage shading
    def tone_fn(V, lobe, top=top, bot=bot, rng=rng, sea_bank=sea_bank):
        k = (round(lobe[0], 2), round(lobe[1], 2))
        if k not in tones:
            tones[k] = ("cream" if rng.random() < 0.75 else "sand") if sea_bank else bank_tone(lobe[0], lobe[1], lobe[2], top, bot, rng)
        return tones[k]
    regs, sil = GM.lobe_regions(lobes, tone_fn, flat_y=flat, grp="CL")
    for r in regs: add([r], 16, z=16*100000 + len(items), kgrp=f"bank{i}")
    bank_info.append(dict(side=side, lobes=len(lobes), area=sil.area, bounds=sil.bounds))

# ---------------------------------------------------------------- islets: every warm-cream blob on the mockup sea (A2, review C4)
r_, g_, b_ = _rgb[..., 0], _rgb[..., 1], _rgb[..., 2]
_im = ndi.binary_closing((r_ > g_ + 3) & (LUM > 115) & PANEL & ~ZIP & (YMM > HORIZON + 1), structure=disk(1.2))
_lab, _n = ndi.label(_im); ISL = []
BANK_U = unary_union([b["bounds"] and box(*b["bounds"]) for b in bank_info]).buffer(2) if bank_info else Polygon()
for k_, sl in enumerate(ndi.find_objects(_lab), 1):
    mm_ = _lab[sl] == k_; a_ = mm_.sum() / PPM**2
    ys_, xs_ = np.nonzero(mm_); w_ = (xs_.max() - xs_.min() + 1) / PPM; h_ = (ys_.max() - ys_.min() + 1) / PPM
    cx_ = BB[0] + (sl[1].start + xs_.mean()) / PPM; cy_ = BB[1] + (sl[0].start + ys_.max() + 1) / PPM   # cy = base
    if a_ < 6 or h_ < 2.0 or w_ / max(h_, 0.1) > 9 or w_ < 5.5: continue
    if abs(cx_ - SUN[0]) < 16 and cy_ < 400: continue                                  # glitter column
    if a_ > 900 and (cx_ < -240 or cx_ > 240): continue                                # side-seam sea banks (built with the banks)
    if BANK_U.contains(Point(cx_, cy_ - h_/2)): continue
    ISL.append((cx_, cy_, w_, h_))
ISL.sort(key=lambda o: (o[0] > 0, o[1]))
islet_info = []
for i, (cx, base, w, h) in enumerate(ISL):
    side = "R" if cx < 0 else "L"; lim = LIM_ALL[side].buffer(-1.0)
    w = max(w, 6.0); h = max(3.0, min(h * 1.1, 0.30 * w, 18.0))      # mockup islets are flat (mask height includes foam)
    def dome(x0, b0): return affinity.scale(Point(x0, b0).buffer(1.0, quad_segs=24), w/2, h, origin=(x0, b0)).intersection(box(x0 - w, b0 - 2*h, x0 + w, b0))
    D = dome(cx, base); moved = (0.0, 0.0)
    if not lim.contains(D):
        best = None
        for rr in np.arange(1, 30, 1.0):
            for th in np.linspace(0, 2*math.pi, 24, endpoint=False):
                if lim.contains(dome(cx + rr*math.cos(th), base + rr*math.sin(th))): best = (rr*math.cos(th), rr*math.sin(th)); break
            if best: break
        if not best: continue
        moved = best; cx, base = cx + best[0], base + best[1]; D = dome(cx, base)
    rng = random.Random(300 + i)
    if w < 10:      # tiny: 2-3 small domes
        n = 2 if w < 8 else 3; rr = max(2.4, w / (n + 0.6))
        lobes = [[cx - (n - 1)*rr*0.75/2 + j*rr*0.75, base - rr*0.55, rr*(1.15 if j == n//2 else 0.9), base] for j in range(n)]
    else:
        Rf = lambda x, y, h=h: float(np.clip(0.6*h, 2.6, 6.0))
        lobes = pack_var(D.buffer(0.4), Rf, rng, dy=0.5, dx=0.92, rmin=2.4, lim=lim)
        if not lobes: lobes = [[cx, base - h*0.5, max(2.6, h*0.6), base]]
    regs, sil = GM.lobe_regions(lobes, tone_islet, flat_y=base + 0.2, grp="ISL", unit=f"islet{i}")
    for r in regs: add([r], 17, z=17*100000 + len(items), unit=f"islet{i}", kgrp=f"islet{i}")
    islet_info.append(dict(side=side, mm=(round(cx, 1), round(base, 1)), w=round(w, 1), moved=moved, lobes=len(lobes)))

# horizon cloud skirt: tiny flat lobes strung along the horizon between the banks and the sun (review C7)
rng = random.Random(41); x = -290.0; skirt = 0
CL_NOW = unary_union([r["geom"] for r in items if 16 <= r["layer"] < 18]).buffer(1.5)
while x < 290:
    x += rng.uniform(9, 26)
    if abs(x) < 17 or abs(x - SUN[0]) < 14 or rng.random() < 0.35: continue
    n = rng.choice([2, 3, 3, 4]); rr = rng.uniform(1.9, 2.8)
    lobes = [[x + j*rr*1.3, HORIZON + 0.4 - rr*0.5, rr*rng.uniform(0.85, 1.15), HORIZON] for j in range(n)]
    side = "R" if x < 0 else "L"; lim = LIM_ALL[side].buffer(-1.0)
    U = unary_union([GM.ell(a, b, c) for a, b, c, _ in lobes])
    if not lim.contains(U) or U.intersects(CL_NOW): continue
    regs, _ = GM.lobe_regions(lobes, lambda V, l: "cream" if rng.random() < 0.6 else "sand", flat_y=HORIZON + 0.5, grp="ISL", unit=f"skirt{skirt}", scale=False)
    for r in regs: add([r], 17, z=17*100000 + len(items), unit=f"skirt{skirt}", kgrp=f"skirt{skirt}")
    skirt += 1; x += n*rr*1.3
CLOUD_U = unary_union([r["geom"] for r in items if 16 <= r["layer"] < 18]).buffer(0.6)
for r in items:
    if 16 <= r["layer"] < 18 and r.get("ko", True): r["kob"] = 0.5

# ================================================================ sun: 22 fine rays with dot ends, two rings; large teal hairline glow
BURST = []
for k, a in enumerate(np.linspace(-171, -9, 22)):
    L = (58 if k % 4 == 0 else (44 if k % 2 == 0 else 26)) * (0.85 + 0.3*abs(math.sin(k*1.7)))
    BURST.append((float(a), float(L)))
add(GM.sun(*SUN, r_core=5.0, r_ring=7.0, flat_y=HORIZON + 0.6), 15)
ring2 = Point(SUN).buffer(9.4, quad_segs=32).difference(Point(SUN).buffer(8.6, quad_segs=32)).intersection(box(-400, -400, 400, HORIZON - 0.2))
add([GM.R("gl_gold", ring2, "satin", ("radial", SUN[0], SUN[1]), "SUN-ring", kob=0.3)], 15)             # second ring
add(GM.burst(*SUN, BURST, 10.2, 0.95, 0.8), 15)
for a, L in BURST:
    if L >= 40:
        t = math.radians(a); add([GM.R("gl_gold", Point(SUN[0] + (L + 2.0)*math.cos(t), SUN[1] + (L + 2.0)*math.sin(t)).buffer(0.95, quad_segs=10), "satin", "auto", "DOT", kob=0.4)], 15)
add(GM.burst(*SUN, [(-178.5, 62), (-1.5, 62)], 10.2, 1.0, 0.8, col="gl_pale"), 15)
# glow: dense radial hairlines over the sky, fading out (alternate lines end early), crossing the zip onto FR
GL_RX, GL_RY = 150.0, 105.0
for k, a in enumerate(np.arange(-179.0, -0.9, 0.55)):
    t = math.radians(a); ux, uy = math.cos(t), math.sin(t)
    rmax = 1.0 / math.sqrt((ux/GL_RX)**2 + (uy/GL_RY)**2)                  # elliptical envelope
    frac = (0.95, 0.55, 0.78, 0.4, 0.85, 0.5)[k % 6] * (0.88 + 0.12*math.sin(k*0.7))
    r0 = 12.0 + (k % 3) * 6.0
    ln = LineString([(SUN[0] + r0*ux, SUN[1] + r0*uy), (SUN[0] + rmax*frac*ux, SUN[1] + rmax*frac*uy)])
    g_ = ln.buffer(0.22, cap_style="round").intersection(box(-400, -400, 400, HORIZON - 1.2))
    if not g_.is_empty: add([GM.R("gl_teal" if k % 4 else "gl_tealt", g_, "run", None, "GLW", kob=0.0)], 11)

# ================================================================ sea: dense dash field, faded edges, glitter column
add([GM.R("gl_pale", LineString([(-300, HORIZON + 0.6), (300, HORIZON + 0.6)]).buffer(0.45), "bean", None, "HZ", kob=0.3)], 13)
SEAISH = (TEAL | LIGHT) & (YMM > HORIZON + 0.5) & ~ndi.binary_dilation(cl_mask, structure=disk(1.5))
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
_sm = ndi.gaussian_filter(SEAISH.astype(np.float32), 4.0*PPM) > 0.05
_sm = ndi.binary_opening(ndi.binary_closing(_sm, structure=disk(5.0)), structure=disk(3.0)) & (YMM > HORIZON + 1.0)
_sp = mask_polys(_sm, min_area=200, simplify=0.8)
SEA_SIL = unary_union([Polygon(p.buffer(6.0).buffer(-6.0).exterior) if p.buffer(6.0).buffer(-6.0).geom_type == 'Polygon' else p for p in _sp])
SEA_SIL = SEA_SIL.intersection(box(-400, HORIZON + 1.0, 400, 600)).buffer(0)
# dashes are limited by the zip only; each size's own keep-outs (welts, seams) trim them in art_size (no all-size band)
SEA_LIM = {"R": box(-400, HORIZON + 0.5, -15.6, 700), "L": box(15.6, HORIZON + 0.5, 400, 700)}
SEA_IN = {s: prepared.prep(SEA_LIM[s]) for s in "RL"}
SIL_EDGE = SEA_SIL.boundary
CLOUD_P = prepared.prep(CLOUD_U)
def sea_col(lv):
    if lv < 28: return None
    return "gl_deep" if lv < 54 else ("gl_teal" if lv < 78 else ("gl_tealt" if lv < 112 else "gl_foam"))
GLITTER_X = (SUN[0] - 15, SUN[0] + 15)
rng = random.Random(7); sea_bars = 0; y = HORIZON + 1.9; rows = 0
def place_dash(x, x1, y, hgt, col, grp="SEA", layer=12):
    """dash kept if inside the sea and the keep-outs; at a keep-out it is shortened (runs right up to the welt clearance)"""
    side = "R" if x < 0 else "L"
    seg = LineString([(x, y), (x1, y)]).intersection(SEA_LIM[side].buffer(-hgt/2))
    segs = [seg] if seg.geom_type == "LineString" else [g for g in getattr(seg, "geoms", []) if g.geom_type == "LineString"]
    n = 0
    for sg in segs:
        if sg.length < 2.6: continue
        a_, b_ = sg.coords[0][0], sg.coords[-1][0]
        bar = LineString([(a_ + hgt/2, y), (b_ - hgt/2, y)]).buffer(hgt/2, cap_style="round") if b_ - a_ > hgt else Point((a_ + b_)/2, y).buffer(hgt/2)
        if CLOUD_P.intersects(bar): bar = bar.difference(CLOUD_U)
        if bar.is_empty or bar.area < 2: continue
        add([GM.R(col, bar, "tatami", 0.0, grp, kob=0.0)], layer); n += 1
    return n
while y < 470:
    t = min(1.0, (y - HORIZON) / 210.0)
    hgt = 1.5 + 0.8*t; vgap = 0.42 + 0.75*t
    x = -300 + rng.uniform(0, 5)
    while x < 300:
        L = rng.uniform(4, 28) * (1.35 - 0.5*t)
        x1 = x + L; mid = Point((x + x1)/2, y)
        if (x < 15.5 and x1 > -15.5) or (GLITTER_X[0] - 1.5 < x1 and x < GLITTER_X[1] + 1.5 and y < 400) or not SEA_SIL.contains(mid):
            x += rng.uniform(1.0, 2.5); continue
        d = SIL_EDGE.distance(mid)                                   # fade toward the sea's outer edge
        if d < 16:
            if rng.random() > 0.25 + 0.75*(d/16): x = x1 + rng.uniform(1, 4); continue
            x1 = x + L*(0.35 + 0.65*d/16)
        col = sea_col(lum_at(x, x1, y, 75))
        if col and x1 - x >= 3.0: sea_bars += place_dash(x, x1, y, hgt, col, "SEA-hl" if col == "gl_foam" else "SEA")
        x = x1 + rng.uniform(0.5, 0.9) + 1.0*t*rng.random()
    y += hgt + vgap; rows += 1
# glitter column: wide broken dashes at the horizon tapering away from the sun
y = HORIZON + 2.0
while y < 405:
    t = min(0.99, (y - HORIZON) / 200.0)
    wcol = 34*(1 - t)**1.1 + 4
    hgt = 1.5 + 0.6*t
    lv = lum_at(SUN[0] - wcol/2, SUN[0] + wcol/2, y, 70)
    if lv > 70:
        w = wcol*rng.uniform(0.75, 1.0); cx = SUN[0] + rng.uniform(-1.5, 1.5)*(1 + t)
        parts = [(cx - w/2, cx + w/2)] if rng.random() < 0.45 else [(cx - w/2, cx - rng.uniform(0.6, 3)), (cx + rng.uniform(0.6, 3), cx + w/2)]
        for a_, b_ in parts:
            if b_ - a_ >= 2.6: place_dash(a_, b_, y, hgt, "gl_pale" if (lv > 120 and t < 0.6) else "gl_foam", "GLT", 12.5)
    y += hgt + 0.55 + 0.9*t

# ================================================================ hairline dashed rays, slightly curved, to the welts
RAYS = [8.0, 20.0, 42.0, 68.0, 88.0, 125.5, 142.0, 162.0, 171.0, 176.5]
ray_info = []
for i, a_ in enumerate(RAYS):
    t = math.radians(a_); ux, uy = math.cos(t), math.sin(t)
    r0 = max((HORIZON + 3.0 - SUN[1]) / max(uy, 1e-3), 10.0)
    far = LineString([(SUN[0] + ux*r0, SUN[1] + uy*r0), (SUN[0] + ux*700, SUN[1] + uy*700)]).intersection(SEA_SIL.buffer(2.0))
    segs = [far] if far.geom_type == "LineString" else [g for g in getattr(far, "geoms", []) if g.geom_type == "LineString"]
    segs = [g for g in segs if g.length > 8]
    if not segs: continue
    pA = (SUN[0] + ux*r0, SUN[1] + uy*r0)
    pB = max([g.coords[0] for g in segs] + [g.coords[-1] for g in segs], key=lambda p: math.hypot(p[0]-SUN[0], p[1]-SUN[1]))
    Lr = math.hypot(pB[0]-pA[0], pB[1]-pA[1]); nx, ny = -uy, ux
    if nx * (1 if a_ < 90 else -1) < 0: nx, ny = -nx, -ny
    pts = [(pA[0] + (pB[0]-pA[0])*s_ + nx*0.018*Lr*4*s_*(1-s_), pA[1] + (pB[1]-pA[1])*s_ + ny*0.018*Lr*4*s_*(1-s_)) for s_ in np.linspace(0, 1, 40)]
    side_pts = [p for p in pts]
    for r in GM.hair_dashes(side_pts, 4.2, 2.4, 0.45, phase=(i*1.7) % 6.6):
        r["geom"] = r["geom"].difference(CLOUD_U)
        if r["geom"].area > 0.3: add([r], 14)
    ray_info.append(dict(angle=a_, start=pA, end=pB))

# ================================================================ stars (every mockup star; nudged inside the keep-outs, never dropped)
STARS_PX = {
 "big":   [(216.7, 223.3), (501.7, 218.3)],
 "med":   [(298, 300), (310, 277), (288, 245), (254, 198), (180, 193), (530, 172), (435, 248), (585, 248), (461, 303)],
 "small": [(213, 157), (233, 255), (336, 247), (331, 301), (319, 323), (500, 168), (563, 191), (503, 258), (535, 248), (476, 268), (413, 273)],
 "dot":   [(237, 180), (260, 165), (202, 185), (187, 224), (154, 235), (207, 256), (263, 230), (306, 227), (341, 277), (263, 280), (276, 271),
           (272, 298), (272, 313), (487, 183), (457, 222), (555, 224), (459, 278), (517, 275), (499, 291), (486, 309), (596, 273)],
}
SIZE = {"big": 16.0, "med": 10.5, "small": 4.0, "dot": 1.2}
stars = []; star_moved = 0
for kind, pts in STARS_PX.items():
    for px, py in pts:
        cx, cy = MM.P(px, py); side = "R" if cx < 0 else "L"
        inner = LIM_ALL[side].buffer(-(SIZE[kind] + 1.5))
        if not inner.is_empty and not inner.contains(Point(cx, cy)):
            from shapely.ops import nearest_points
            q = nearest_points(inner, Point(cx, cy))[0]; cx, cy = q.x, q.y; star_moved += 1
        u = f"star{len(stars)}"; stars.append((cx, cy, kind))
        if kind == "big":     regs = GM.star(cx, cy, 16.0, 11.0, 1.7, "big", u)
        elif kind == "med":   regs = GM.star(cx, cy, 10.5, 6.5, 1.5, "sparkle", u)
        elif kind == "small": regs = GM.star(cx, cy, 4.0, 3.2, 1.2, "cross", u)
        else:                 regs = GM.star(cx, cy, 2.3, 0, 0, "dot", u)
        add(regs, 18, unit=u)

# ================================================================ sew order: one stop per thread (scale dashes after the cloud bodies)
SEW = ["gl_deep", "gl_teal", "gl_tealt", "gl_foam", "gl_pale", "gl_gold", "gl_slate", "gl_sage", "gl_sagelt", "gl_sand", "gl_cream"]
assert not [r for r in items if r["col"] not in SEW], "colour outside the sew list"
for r in items:
    r["vlayer"] = r["layer"]
    r["layer"] = (40 if r.get("sub") == "scale" else 20) + SEW.index(r["col"])

META = dict(horizon=HORIZON, sun=SUN, rays=ray_info, burst=BURST, banks=bank_info, islets=islet_info, n_islets=len(islet_info), n_stars=len(stars),
            star_moved=star_moved, skirt=skirt, sea_bars=sea_bars, sea_rows=rows, mock_map=dict(cfx=MM.CFX, necky=MM.NECKY, sx=MM.SX, sy=MM.SY))
pickle.dump(dict(items=items, meta=META), open("scene.pkl", "wb"))
print("items", len(items), "banks", [(b["side"], b["lobes"]) for b in bank_info], "islets", len(islet_info),
      {s: sum(1 for i in islet_info if i["side"] == s) for s in "RL"}, "skirt", skirt, "stars", len(stars), "moved", star_moved,
      "sea dashes", sea_bars, "rows", rows, "rays", len(ray_info), "burst", len(BURST))
