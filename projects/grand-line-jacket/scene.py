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

# ---------------------------------------------------------------- banks: TRACED from the registered close-ups (closetrace.py, LESSONS A12)
TRACE = pickle.load(open("closetrace.pkl", "rb"))
bank_info = []
for P_, side in (("FR", "R"), ("FL", "L")):
    for r in TRACE[P_]["regions"]:
        add([dict(r)], 16, z=16*100000 + len(items), kgrp=f"bank{P_}")
    inf = TRACE[P_]["info"]; reg_ = TRACE[P_]["region"]
    bank_info.append(dict(side=side, traced=True, kept_mm2=inf["kept_mm2"], lost_to_keepout_mm2=inf["lost_to_keepout_mm2"],
                          edge_lobes=inf["edge_lobes"], tone_mm2=inf["tone_mm2"], fit_resid_mm=inf["fit_resid_mm"], bounds=reg_.bounds, lobes=inf["edge_lobes"]))
TRACED_U = unary_union([TRACE[p]["region"] for p in ("FR", "FL")]).buffer(2.0)

# ---------------------------------------------------------------- islets: TRACED from the mockup (A12), lobe rows inside the outline (A13)
# Every warm-cream blob on the mockup sea is found at 2 px/mm, then its silhouette is re-traced at 8 px/mm (Lanczos x4 of the mockup,
# cream threshold, largest part, holes filled, foam/glow under the base cut at the base line). The traced outline keeps its own width +
# height profile (taller tiered centre, flat-ish base); it is filled with rows of domes INSIDE the outline (pack_var), so the
# silhouette is the mockup's, not a box. An outline that hits a keep-out is first shrunk (>= 80 %), then nudged the shortest way.
r_, g_, b_ = _rgb[..., 0], _rgb[..., 1], _rgb[..., 2]
_im = ndi.binary_closing((r_ > g_ + 3) & (LUM > 115) & PANEL & ~ZIP & (YMM > HORIZON + 1), structure=disk(1.2))
_im = ndi.binary_opening(_im, structure=disk(1.0))          # Rev E2: the gold rays crossing the sea are not islets
_lab, _n = ndi.label(_im); ISL = []
BANK_U = TRACED_U
for k_, sl in enumerate(ndi.find_objects(_lab), 1):
    mm_ = _lab[sl] == k_; a_ = mm_.sum() / PPM**2
    ys_, xs_ = np.nonzero(mm_); w_ = (xs_.max() - xs_.min() + 1) / PPM; h_ = (ys_.max() - ys_.min() + 1) / PPM
    cx_ = BB[0] + (sl[1].start + xs_.mean()) / PPM; cy_ = BB[1] + (sl[0].start + ys_.max() + 1) / PPM   # cy = base
    if a_ < 6 or h_ < 2.0 or w_ / max(h_, 0.1) > 9 or w_ < 5.5: continue
    if abs(cx_ - SUN[0]) < 16 and cy_ < 400: continue                                  # glitter column
    if abs(cx_ - SUN[0]) < 30 and cy_ < HORIZON + 12: continue                         # horizon glare under the sun
    if BANK_U.contains(Point(cx_, cy_ - h_/2)): continue
    bx = (BB[0] + sl[1].start/PPM - 4, BB[1] + sl[0].start/PPM - 4, BB[0] + sl[1].stop/PPM + 4, BB[1] + sl[0].stop/PPM + 3)
    ISL.append((cx_, cy_, w_, h_, bx))
ISL.sort(key=lambda o: (o[0] > 0, o[1]))
TPPM = 8.0
def disk_px(r): y, x = np.ogrid[-r:r+1, -r:r+1]; return x*x + y*y <= r*r
def trace_islet(bx):
    """silhouette of one mockup islet at 8 px/mm: cream pixels (warm, bright), largest part, base cut where the body ends"""
    a = np.array(MM.warp(bx, TPPM / 4.0).resize((int((bx[2]-bx[0])*TPPM), int((bx[3]-bx[1])*TPPM)), Image.LANCZOS)).astype(np.float32)
    lum = a @ np.array([0.3, 0.59, 0.11]); m = (lum > 112) & (a[..., 0] > a[..., 2] + 6)
    m = ndi.binary_opening(ndi.binary_closing(m, structure=np.ones((5, 5))), structure=disk_px(int(1.1*TPPM)))   # cut off rays crossing it
    lab, n = ndi.label(m)
    if not n: return None
    m = lab == (np.bincount(lab.ravel())[1:].argmax() + 1); m = ndi.binary_fill_holes(m)
    cols = m.sum(0); prof = np.where(cols > 0)[0]
    # base: the row where the body is still >= 55 % of its widest row (foam + glow trail below it is not cloud)
    rows = m.sum(1); rmax = rows.max(); rb = max(i for i in range(len(rows)) if rows[i] >= 0.55*rmax)
    m[rb + 1:] = False
    cs = measure.find_contours(np.pad(m, 1).astype(float), 0.5)
    if not cs: return None
    c = max(cs, key=len)
    P = Polygon([(bx[0] + (x - 1 + 0.5)/TPPM, bx[1] + (y - 1 + 0.5)/TPPM) for y, x in c]).buffer(0)
    if P.geom_type != "Polygon": P = max(GM.polys(P), key=lambda q: q.area)
    return P.buffer(0.6).buffer(-0.6).simplify(0.15)
islet_info = []; ISL_REF = []
for i, (cx, base, w, h, bx) in enumerate(ISL):
    side = "R" if cx < 0 else "L"; lim = CLIP_M[side].buffer(-1.0)          # size M keep-outs; other sizes clip in art_size
    O = trace_islet(bx)
    if O is None or O.is_empty or O.area < 8: continue
    if O.intersects(TRACED_U): continue                                                 # traced from the close-up already
    ISL_REF.append(O.wkt)                                                            # mockup silhouette, for qa.motif_match (A14)
    moved = (0.0, 0.0); a0_ = O.area
    if not lim.contains(O):              # keep the mockup position (never moved): cut at the keep-out, round the cut, keep every part
        ob0 = O.bounds; rr_ = min(2.5, 0.25*min(ob0[2] - ob0[0], ob0[3] - ob0[1]))
        Oc = O.intersection(lim).buffer(0)
        if not Oc.is_empty:              # Rev E3: round the cut ONLY near the keep-out edge (an opening of the whole islet ate its thin foam tails)
            band = lim.boundary.buffer(rr_ + 1.5)
            Oc = unary_union([Oc.difference(band), Oc.buffer(-rr_).buffer(rr_).intersection(band).intersection(Oc.buffer(0.01))]).buffer(0)
            Oc = unary_union([q for q in GM.polys(Oc.intersection(lim)) if q.area >= 4.0])
        if Oc.is_empty or Oc.area < 0.25*a0_:
            islet_info.append(dict(side=side, mm=(round((ob0[0]+ob0[2])/2, 1), round(ob0[3], 1)), w=round(ob0[2]-ob0[0], 1), h=round(ob0[3]-ob0[1], 1),
                                   dropped="in the keep-out (< 25 % sewable)", traced=True))
            continue
        O = Oc
    cut_pct = round(100*(1 - O.area/a0_), 1)
    ob = O.bounds; w2, h2 = ob[2] - ob[0], ob[3] - ob[1]; base2 = ob[3]
    rng = random.Random(300 + i)
    Rf = lambda x, y, h2=h2, w2=w2: float(np.clip(0.42*min(h2, w2/2.2), 1.8, 5.5))
    lobes = pack_var(O, Rf, rng, dy=0.5, dx=0.85, inset=0.55, rmin=1.6, lim=O.buffer(0.35))
    if not lobes: lobes = [[(ob[0]+ob[2])/2, base2 - h2*0.5, max(1.2, h2*0.5), base2]]
    regs, sil = GM.lobe_regions(lobes, tone_islet, flat_y=base2 + 0.1, grp="ISL", unit=f"islet{i}", fan=True)
    base_fill = O.difference(sil).buffer(0)          # the traced outline is fully stitched: sand between / under the domes
    if not base_fill.is_empty and base_fill.area > 0.8:
        regs = [GM.R("gl_sand", base_fill, "tatami", 0.0, "ISL", unit=f"islet{i}")] + regs
    for r in regs:
        r["geom"] = r["geom"].intersection(O.buffer(-0.25)).buffer(0)       # pull comp + thread width give the 0.25 back
        if not r["geom"].is_empty and r["geom"].area > 0.2: add([r], 17, z=17*100000 + len(items), unit=f"islet{i}", kgrp=f"islet{i}")
    islet_info.append(dict(side=side, mm=(round((ob[0]+ob[2])/2, 1), round(base2, 1)), w=round(w2, 1), h=round(h2, 1), moved=[round(float(v), 1) for v in moved],
                           cut_pct=cut_pct, lobes=len(lobes), traced=True))
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
    regs, _ = GM.lobe_regions(lobes, lambda V, l: "cream", flat_y=HORIZON + 0.5, grp="ISL", unit=f"skirt{skirt}", fan=True)
    for r in regs: add([r], 17, z=17*100000 + len(items), unit=f"skirt{skirt}", kgrp=f"skirt{skirt}")
    skirt += 1; x += n*rr*1.3
CLOUD_U = unary_union([r["geom"] for r in items if 16 <= r["layer"] < 18]).buffer(0.6)
for r in items:
    if 16 <= r["layer"] < 18 and r.get("ko", True): r["kob"] = 0.5

# ================================================================ sun (Rev D, close-up): small soft half sun, thin tapered rays with dot ends; faint glow
BURST = []
for k, a in enumerate(np.linspace(-170, -10, 20)):
    L = (31 if k % 4 == 0 else (23 if k % 2 == 0 else 15)) * (0.88 + 0.24*abs(math.sin(k*1.7)))     # Rev E: shorter
    BURST.append((float(a), float(L)))
add([r for r in GM.sun(*SUN, r_core=4.2, r_ring=5.0, flat_y=HORIZON + 0.6) if r["grp"] != "SUN-ring"], 15)   # Rev E: ring dropped
for a, L in BURST:                                     # Rev E2: long rays = hairline bean in gold-cream, short rays = paler single-weight run
    t = math.radians(a); long_ = L >= 22
    add([GM.R("gl_gold" if long_ else "gl_pale", LineString([(SUN[0] + 6.2*math.cos(t), SUN[1] + 6.2*math.sin(t)), (SUN[0] + L*math.cos(t), SUN[1] + L*math.sin(t))]).buffer(0.25 if long_ else 0.2, cap_style="round"),
              "bean" if long_ else "run", None, "BURST", kob=0.3)], 15)
for a, L in BURST:
    if L >= 22:
        t = math.radians(a); add([GM.R("gl_gold", Point(SUN[0] + (L + 1.6)*math.cos(t), SUN[1] + (L + 1.6)*math.sin(t)).buffer(0.62, quad_segs=10), "satin", "auto", "DOT", kob=0.4)], 15)
for a in (-178.5, -1.5):
    t = math.radians(a); add([GM.R("gl_pale", LineString([(SUN[0] + 6.2*math.cos(t), SUN[1] + 6.2*math.sin(t)), (SUN[0] + 30*math.cos(t), SUN[1] + 30*math.sin(t))]).buffer(0.28, cap_style="round"), "bean", None, "BURST", kob=0.3)], 15)
# glow: sparse hairlines (every 2.2 deg), ragged ends, the outer part in sea deep so it fades to navy; no envelope edge
rng_g = random.Random(5)
for k, a in enumerate(np.arange(-178.0, -1.0, 3.0)):          # Rev E2: sparser glow
    t = math.radians(a); ux, uy = math.cos(t), math.sin(t)
    rmax = 1.0 / math.sqrt((ux/120.0)**2 + (uy/85.0)**2) * rng_g.uniform(0.55, 1.0)
    r0 = 9.0 + rng_g.uniform(0, 8); rm = r0 + (rmax - r0) * rng_g.uniform(0.45, 0.7)
    for (ra, rb, col) in ((r0, rm, "gl_teal"), (rm + 1.5, rmax, "gl_deep")):
        if rb - ra < 4: continue
        ln = LineString([(SUN[0] + ra*ux, SUN[1] + ra*uy), (SUN[0] + rb*ux, SUN[1] + rb*uy)])
        g_ = ln.buffer(0.22, cap_style="round").intersection(box(-400, -400, 400, HORIZON - 1.2))
        if not g_.is_empty: add([GM.R(col, g_, "run", None, "GLW", kob=0.0)], 11)

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
# Rev E2 (founder 19 Oct): the sea runs continuously from the CF keep-out to the panel edge on every row (the mockup's zip shadow
# is not navy sea): each 2 mm row of the traced sea silhouette is extended to the CF keep-out on its side
_ext = []
for _y in np.arange(HORIZON + 1.0, 600, 2.0):
    _band = SEA_SIL.intersection(box(-400, _y, 400, _y + 2.0))
    for _s, (_a, _b) in (("R", (-400, -15.6)), ("L", (15.6, 400))):
        _h = _band.intersection(box(_a, _y, _b, _y + 2.0))
        if _h.is_empty or _h.area < 2: continue
        hb = _h.bounds
        _ext.append(box(hb[0], _y, -15.6, _y + 2.0) if _s == "R" else box(15.6, _y, hb[2], _y + 2.0))
SEA_EXT = unary_union([SEA_SIL] + _ext).buffer(0.5).buffer(-0.5)
SIL_EDGE = SEA_EXT.boundary.difference(box(-19, -1000, 19, 1000))      # no fade at the zip keep-out
# Rev E2 (A14/A15): WHERE the sea is stitched is traced from the mockup: sea pixels (teal, or the bright glitter under the sun),
# closed over 3 mm (the navy between the mockup's own dashes), the zip-shadow band filled where the row is sea just outside it
_teal = (TEAL | LIGHT) & PANEL & ~ZIP & ~WELTM & (YMM > HORIZON + 1.0) & ~ndi.binary_dilation(cl_mask, structure=disk(1.0))
SEA_DES = ndi.binary_closing(_teal, structure=np.ones((int(3*PPM), int(3*PPM))))
_zb = (np.abs(XMM) > 15.6) & (np.abs(XMM) < 40) & (YMM > HORIZON + 1.0)
for _sgn in (-1, 1):
    _cols = (np.sign(XMM[0]) == _sgn) & (np.abs(XMM[0]) > 40) & (np.abs(XMM[0]) < 70)
    _rowsea = SEA_DES[:, _cols].mean(1) > 0.5
    SEA_DES |= _zb & (np.sign(XMM) == _sgn) & _rowsea[:, None]
# the mockup's welts are garment details (A15): fill their area from the sea around them (our welts sit 18 mm closer to CF and
# have their own keep-out, applied per size in art_size)
_wfill = ndi.binary_dilation(SEA_DES & ~WELTM, structure=disk(9.0), iterations=2) & WELTM & (YMM > HORIZON + 1.0)
SEA_DES |= _wfill
def des_frac(x0, x1, y):
    py = int((y - BB[1])*PPM); a = max(0, int((x0 - BB[0])*PPM)); b = min(W, max(a + 1, int((x1 - BB[0])*PPM)))
    return float(SEA_DES[py, a:b].mean()) if 0 <= py < H and b > a else 0.0
_ROW = {}
def row_ref(side, y):
    """the row's own sea brightness (70th pct of the mockup sea away from the zip), used where the mockup's zip shadow reads dark"""
    k = (side, int((y - HORIZON) // 2))
    if k not in _ROW:
        xs = [x_ for x_ in np.arange(-290, 290, 4.0) if (x_ < -90 if side == "R" else x_ > 90) and SEA_SIL.contains(Point(x_, y))]
        _ROW[k] = float(np.percentile([lum_at(x_, x_ + 4, y, 75) for x_ in xs], 70)) if len(xs) >= 3 else None
    return _ROW[k]
CLOUD_P = prepared.prep(CLOUD_U)
def sea_col(lv):
    if lv < 34: return None                         # Rev D: navy gaps as in the mockup
    return "gl_deep" if lv < 54 else ("gl_teal" if lv < 78 else ("gl_tealt" if lv < 112 else "gl_foam"))
GLITTER_X = (SUN[0] - 15, SUN[0] + 15)
def glit_half(y):                                       # Rev E2: only the glitter's bright core is kept free; the sea runs under its ragged edges
    t = min(0.99, (y - HORIZON) / 200.0); return (17*(1 - t)**1.2 + 3) * 0.18
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
    hgt0 = 1.5 + 0.8*t; vgap = (0.42 + 0.75*t) * rng.uniform(0.7, 1.4)
    x = -300 + rng.uniform(0, 5)
    while x < 300:
        L = min(40.0, rng.lognormvariate(math.log(11), 0.65)) * (1.3 - 0.5*t) * (1 - 0.35*t)      # irregular, shorter toward the hem
        hgt = hgt0 * rng.uniform(0.75, 1.25)                                            # and thicknesses
        x1 = x + L; mid = Point((x + x1)/2, y)
        if x < -15.6 < x1: x1 = -15.6; mid = Point((x + x1)/2, y)              # Rev E2: a dash reaching the zip ends at the keep-out (was dropped)
        if des_frac(x, x1, y) < 0.5:                                 # a shorter dash where the mockup's sea patch is short
            for f_ in (0.5, 0.3):
                if L*f_ >= 3.0 and des_frac(x, x + L*f_, y) >= 0.5: x1 = x + L*f_; mid = Point((x + x1)/2, y); break
        if (x < 15.5 and x1 > -15.5) or des_frac(x, x1, y) < 0.5:          # Rev E3 (founder a): the sea runs UNDER the glitter too
            x += rng.uniform(0.8, 1.6); continue                     # the mockup's sea layout (incl. its fade) decides where dashes go
        lv = lum_at(x, x1, y, 75)
        if abs(mid.x) < 40:                                              # Rev E2 (A15): zip-shadow band -> the row's own sea brightness
            rf = row_ref("R" if mid.x < 0 else "L", y)
            if rf is not None: lv = max(lv, 0.92*rf)
        lv = lv + (14 if t < 0.2 else 0) - 26*t                          # Rev E: bright near the horizon, darker toward the hem
        col = "gl_deep" if y < HORIZON + 5.0 else (sea_col(lv) or "gl_deep")    # dark band under the horizon; traced sea is never left bare
        if col and x1 - x >= 3.0: sea_bars += place_dash(x, x1, y, hgt, col, "SEA-hl" if col == "gl_foam" else "SEA")
        x = x1 + rng.uniform(0.5, 1.2) + (1.3*rng.random() if rng.random() < 0.25 else 0) + 0.6*t*rng.random()    # gaps < 3.1 mm
    y += hgt0 + vgap; rows += 1
# Rev E3 (A15): fill pass. Wherever the traced design sea (SEA_DES) is still bare after the rows (a mockup sea patch that fell
# between two rows, or a dash that ended short), add dashes along that patch's own rows, so no traced sea is left bare.
def _sea_cover():
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    for r in items:
        if r["layer"] != 12: continue
        for p in GM.polys(r["geom"]): d.polygon([((x - BB[0])*PPM, (y - BB[1])*PPM) for x, y in p.exterior.coords], fill=255)
    return ndi.binary_closing(np.array(im) > 0, structure=np.ones((int(3*PPM), int(3*PPM))))
sea_fill = 0
for _pass in range(2):
    _gap = SEA_DES & ~_sea_cover() & (np.abs(XMM) > 16.0) & (YMM > HORIZON + 1.5) & ~ndi.binary_dilation(cl_mask, structure=disk(1.5))
    _gap = ndi.binary_opening(_gap, structure=disk(0.5))
    _lab, _n = ndi.label(_gap)
    for _k, _sl in enumerate(ndi.find_objects(_lab), 1):
        _m = _lab[_sl] == _k
        if _m.sum() / PPM**2 < 6.0: continue
        _ys = np.nonzero(_m.any(1))[0]; _y0 = BB[1] + (_sl[0].start + _ys[0]) / PPM; _y1 = BB[1] + (_sl[0].start + _ys[-1] + 1) / PPM
        _nr = max(1, int(round((_y1 - _y0) / 2.6)))
        for _j in range(_nr):
            yy = _y0 + (_y1 - _y0) * (_j + 0.5) / _nr; ry = int((yy - BB[1])*PPM) - _sl[0].start
            ry = min(max(ry, 0), _m.shape[0] - 1); cols = np.nonzero(_m[ry])[0]
            if not len(cols): continue
            # runs of bare pixels on this row
            brk = np.nonzero(np.diff(cols) > 2)[0]; starts = np.r_[cols[0], cols[brk + 1]]; ends = np.r_[cols[brk], cols[-1]]
            for a_, b_ in zip(starts, ends):
                xa = BB[0] + (_sl[1].start + a_) / PPM - 0.8; xb = BB[0] + (_sl[1].start + b_ + 1) / PPM + 0.8
                if xb - xa < 3.0: xa, xb = (xa + xb)/2 - 1.6, (xa + xb)/2 + 1.6
                t = min(1.0, (yy - HORIZON) / 210.0); hgt = min(1.5 + 0.8*t, max(1.4, (_y1 - _y0) / _nr - 0.3))
                lv = lum_at(xa, xb, yy, 75)
                if abs((xa + xb)/2) < 40:
                    rf = row_ref("R" if xa < 0 else "L", yy)
                    if rf is not None: lv = max(lv, 0.92*rf)
                lv = lv + (14 if t < 0.2 else 0) - 26*t
                col = "gl_deep" if yy < HORIZON + 5.0 else (sea_col(lv) or "gl_deep")
                sea_fill += place_dash(xa, xb, yy, hgt, col, "SEA")
print("sea fill dashes", sea_fill)
# glitter column: narrow, tapering, broken bars laid ON the sea (sewn after it, layer 12.5)
y = HORIZON + 2.0
while y < 405:
    t = min(0.99, (y - HORIZON) / 200.0)
    wcol = 30*(1 - t) + 6                                               # Rev E2: mockup glitter bars ~30 wide under the sun, ~15 at y 320
    hgt = 1.3 + 0.5*t
    lv = lum_at(SUN[0] - wcol/2, SUN[0] + wcol/2, y, 70)
    if lv > 55 and rng.random() > 0.08 + 0.30*t:                       # Rev E2: bright broken bars on the sea, fading with distance
        w = wcol*rng.uniform(0.55, 1.0); cx = SUN[0] + rng.uniform(-2.0, 2.0)*(1 + t)
        hgt = hgt * rng.uniform(0.7, 1.15)
        parts = [(cx - w/2, cx + w/2)] if rng.random() < 0.35 else [(cx - w/2, cx - rng.uniform(0.8, 2.5)), (cx + rng.uniform(0.8, 2.5), cx + w/2)]
        for a_, b_ in parts:
            if b_ - a_ >= 2.6: place_dash(a_, b_, y, hgt, "gl_pale" if (lv > 100 and t < 0.6) else ("gl_foam" if t < 0.7 else "gl_tealt"), "GLT", 12.5)
    y += hgt + 0.7 + 1.1*t
# Rev E: glitter centre line removed (read as a ladder)

# ================================================================ solid hairline rays (approved 2026-10-19), slightly curved, to the welts
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
    # Devin 2026-10-19: SOLID rays approved instead of the mockup's dashes -> one continuous 0.6 mm bean line per ray, cut at clouds
    g_ = LineString(side_pts).buffer(0.3, cap_style="round").difference(CLOUD_U.buffer(0.3))
    for q in GM.polys(g_):
        if q.area > 0.6: add([GM.R("gl_gold", q, "bean", None, "RAY", kob=0.3)], 14)
    ray_info.append(dict(angle=a_, start=pA, end=pB))

# ================================================================ stars (every mockup star traced; cut by the keep-outs, never moved)
STARS_PX = {
 "big":   [(216.7, 223.3), (501.7, 218.3)],
 "med":   [(298, 300), (310, 277), (288, 245), (254, 198), (180, 193), (530, 172), (435, 248), (585, 248), (461, 303)],
 "small": [(213, 157), (233, 255), (336, 247), (331, 301), (319, 323), (500, 168), (563, 191), (503, 258), (535, 248), (476, 268), (413, 273)],
 "dot":   [(237, 180), (260, 165), (202, 185), (187, 224), (154, 235), (207, 256), (263, 230), (306, 227), (341, 277), (263, 280), (276, 271),
           (272, 298), (272, 313), (487, 183), (457, 222), (555, 224), (459, 278), (517, 275), (499, 291), (486, 309), (596, 273)],
}
SIZE = {"big": 16.0, "med": 10.5, "small": 4.0, "dot": 1.2}
stars = []; star_moved = 0; star_trace = []
import qa_fidelity as _QF                       # the gate's own sky background per side (fit and gate see the same reference blob)
GATE_BG = {"R": _QF.star_sky("FR")[3], "L": _QF.star_sky("FL")[3]}
import startrace as STR
def star_free(cx, cy, p, kind, u):
    """Rev E3 (A14): a star with its OWN arm lengths (up, right, down, left [, 4 diagonals + diagonal angle offset]) and root width
    p[-1], all fitted to the mockup's star. Same stitch build as GM.star (tapered satin arms, pale centre)."""
    w0 = float(np.clip(p[-1], 0.8, 1.6)); R_ = GM.R           # 0.8 = 40wt satin minimum stroke
    if kind == "dot":                              # Rev E3: elliptical dot (width, height fitted)
        a_, b_ = max(0.55, p[0]/2), max(0.55, p[1]/2)        # rhombus (the mockup's tiny 4-point glints) U ellipse of fraction p[2]
        g_ = Polygon([(cx - a_, cy), (cx, cy - b_), (cx + a_, cy), (cx, cy + b_)]).union(affinity.scale(Point(cx, cy).buffer(1.0, quad_segs=10), max(0.5, a_*p[2]), max(0.5, b_*p[2])))
        return [R_("gl_gold", g_.buffer(0), "satin", "auto", "DOT", unit=u, kob=0.5)]
    L4 = p[:4]; ang4 = (-90, 0, 90, 180)
    MINA = 1.6                                     # Rev E3: what clean_vis keeps (satin part >= 1.5 mm2): the fit sees only sewable arms
    if kind in ("cross", "small"):                 # small cross: one thread, each arm overlaps the centre (no sliver arms)
        cc = Point(cx, cy).buffer(w0*0.62)
        arms = [GM.taper_arm(cx, cy, a, L, w0, 0.8, 0.0) for L, a in zip(L4, ang4)]
        arms = [g for g in arms if g.difference(cc).area >= MINA]
        if not arms: return [R_("gl_gold", cc.buffer(0.3), "satin", "auto", "DOT", unit=u, kob=0.5)]
        return [R_("gl_gold", g.union(cc), "satin", "auto", "STAR", unit=u, kob=0.5) for g in arms]
    cd = max(0.8, w0*0.75); arms = [GM.taper_arm(cx, cy, a, L, w0, 0.65, cd*0.6) for L, a in zip(L4, ang4)]
    if kind in ("big", "med"):                     # Rev E3: the mockup's medium stars carry short diagonals too (fitted, 0 = none)
        off = p[8]
        # Rev E3: diagonals FIRST (lower z): the main arms knock them out at the root, so a main arm is never notched by two
        # diagonals (a notched arm broke the engine's centreline: the down arm sewed as a 1.8 mm wedge, ENGINE_NOTES 18)
        arms = [GM.taper_arm(cx, cy, a + (off if a in (45, 225) else -off), L, w0*0.8, 0.65, cd*0.6) for L, a in zip(p[4:8], (225, 315, 45, 135)) if L >= 1.6] + arms
    centre = Point(cx, cy).buffer(cd + 0.2, quad_segs=12)
    arms = [g.difference(centre) for g in arms]; arms = [g for g in arms if g.area >= MINA]
    return [R_("gl_gold", g, "satin", "auto", "STAR", unit=u, kob=0.5) for g in arms] + \
           [R_("gl_pale", centre, "satin", "auto", "STAR-c", unit=u, kob=0.5)]
MUL = (0.6, 0.8, 0.9, 1.1, 1.25, 1.5, 2.0)
for kind, pts in STARS_PX.items():
    for px, py in pts:
        cx, cy = MM.P(px, py)
        m = STR.measure(cx, cy, kind); cx, cy = m["cx"], m["cy"]          # Rev E2 (A14): centre + arm lengths traced from the mockup
        side = "R" if cx < 0 else "L"; ocx, ocy = cx, cy
        u = f"star{len(stars)}"
        geo = lambda regs: [r["geom"] for r in regs]
        if kind == "dot":
            core = sorted(m["arms"])[1:3]; dia = float(np.clip(2*np.mean(core) - 1.2, 1.5, 3.2))
            p0 = [dia, dia, 1.0]; steps = [MUL, MUL, tuple(("add", d_) for d_ in (-0.3, -0.15, 0.15))]; lo = [1.1, 1.1, 0.55]; hi = [5.5, 5.5, 1.0]
        else:
            up, dn, lf, rt = [max(a_, 2.0) for a_ in m["arms"]]
            Lv, Lh = max(m["Lv"], 2.0), max(m["Lh"], 2.0)
            arm0 = [min(up, 1.35*Lv), min(rt, 1.35*Lh), min(dn, 1.35*Lv), min(lf, 1.35*Lh)]   # each arm its own (neighbour run-ins capped)
            w0 = {"big": 1.25, "med": 1.1, "small": 1.0}[kind]
            if kind in ("big", "med"):
                Ld = max(m["Ld"], 2.0) if kind == "big" else 0.35*min(Lv, Lh)
                DADD = tuple(("add", d_) for d_ in (-3.0, -1.5, -0.7, 0.7, 1.5, 3.0))
                p0 = arm0 + [Ld]*4 + [0.0, w0]; steps = [MUL]*4 + [MUL if kind == "big" else DADD]*4 + [tuple(("add", d_) for d_ in (-12, -6, -3, 3, 6, 12)), MUL]
                lo = [1.5]*4 + [1.5 if kind == "big" else 0.0]*4 + [-20.0, 0.8]; hi = [max(2.5*v, 30.0 if kind == "big" else 14.0) for v in arm0] + [max(2.5*Ld, 12.0 if kind == "big" else 6.0)]*4 + [20.0, 1.6]
            else:
                p0 = arm0 + [w0]; steps = [MUL]*5; lo = [1.2]*4 + [0.8]; hi = [max(2.5*v, 8.0) for v in arm0] + [1.6]
        _cl = CLIP_M[side].buffer(-0.4)
        def _sewn(gs, _cl=_cl):          # what art_size + clean_vis keep of it at size M: cut at the keep-out, slivers dropped
            out_ = []
            for g_ in gs:
                if not _cl.contains(g_): g_ = g_.intersection(_cl)
                out_ += [q for q in GM.polys(g_) if q.area >= 1.5 and not q.buffer(-0.35).is_empty]
            return out_
        mk = lambda x_, y_, p, kind=kind, u=u: _sewn(geo(star_free(x_, y_, p, kind, u)))
        RW = 32.0 if kind == "big" else 22.0           # window: the big stars' arms run past 22 mm
        if kind == "big": p0 = [max(v, 12.0) for v in p0[:4]] + [max(v, 6.0) for v in p0[4:8]] + p0[8:]     # measure() undershoots when its centre is off
        pf, (fx_, fy_), iou_ = STR.fit_free(cx, cy, mk, p0, steps, lo, hi, clip=CLIP_M[side].buffer(-1.0), R=RW, bg=GATE_BG[side],
                                            centre_steps=(1.6, 0.4) if kind == "big" else (0.8, 0.4))
        # Rev E3: refine through the STITCH model (engine stitch blocks drawn as thread, the gate's own operator)
        def mkr(x_, y_, p, kind=kind, u=u, _cl=_cl):
            out_ = []
            for r_ in star_free(x_, y_, p, kind, u):
                g_ = r_["geom"] if _cl.contains(r_["geom"]) else r_["geom"].intersection(_cl)
                ps_ = [q for q in GM.polys(g_) if q.area >= 1.5 and not q.buffer(-0.35).is_empty]
                if ps_: out_.append(dict(r_, geom=unary_union(ps_)))
            return out_
        fine = tuple(("add", d_) for d_ in (-2, -1, 1, 2))
        st2 = [MUL if s_ is MUL else s_ for s_ in steps]
        pf, (fx_, fy_), iou_ = STR.fit_free(fx_, fy_, mkr, pf, st2, lo, hi, clip=CLIP_M[side].buffer(-1.0), render=STR.stitch_render, rounds=2, centre_steps=(0.4, 0.2), bg=GATE_BG[side], R=RW)
        if kind == "dot":          # Rev E3: a "dot" may be a tiny 4-point glint: fit it as a small cross too, keep the better
            mkc = lambda x_, y_, p, u=u: mkr(x_, y_, p, "small", u)
            pc_, cc_, ic_ = STR.fit_free(fx_, fy_, mkc, [max(1.2, pf[0]/2)]*2 + [max(1.2, pf[1]/2)]*2 + [0.9], [MUL]*5, [1.0]*4 + [0.8], [6.0]*4 + [1.4],
                                     clip=CLIP_M[side].buffer(-1.0), render=STR.stitch_render, rounds=2, centre_steps=(0.4, 0.2), bg=GATE_BG[side])
            if ic_ > iou_ + 0.03: kind, pf, (fx_, fy_), iou_ = "small", pc_, cc_, ic_
        cx, cy = fx_, fy_
        # Rev E3 (A14): a star at a keep-out is CUT by the keep-out per size (art_size), never shrunk, moved or dropped
        regs = star_free(cx, cy, pf, kind, u)
        if not any(r["geom"].intersects(LIM_ALL[side].buffer(-0.5)) for r in regs) and not any(r["geom"].intersects(CLIP_M[side]) for r in regs):
            star_trace.append(dict(kind=kind, mm=(round(cx, 1), round(cy, 1)), dropped="fully inside the keep-out", fit_score=round(iou_, 2), moved_mm=0.0))
            continue
        stars.append((cx, cy, kind))
        cut = not all(CLIP_M[side].buffer(-0.4).contains(r["geom"]) for r in regs)
        star_trace.append(dict(kind=kind, mm=(round(cx, 1), round(cy, 1)), arms=[round(v, 1) for v in pf[:-1]], w=round(float(pf[-1]), 2), fit_score=round(iou_, 2),
                               traced_at=(round(ocx, 1), round(ocy, 1)), moved_mm=0.0, cut_by_keepout=bool(cut),
                               Lv=round(max(pf[0], pf[2]) if kind != "dot" else pf[0], 1), Lh=round(max(pf[1], pf[3]) if kind != "dot" else pf[0], 1)))
        add(regs, 18, unit=u, kgrp=u)        # Rev E3: arms of one star knock each other out exactly (the kob gap cut small arms to slivers)

for r in items:                                                   # Rev D: stars pale cream (close-up), not gold
    if r["layer"] == 18: r["col"] = "gl_gold"                       # Rev E: warm gold-cream (#E3C890), centres included

# ================================================================ sew order: one stop per thread (scale dashes after the cloud bodies)
SEW = ["gl_deep", "gl_teal", "gl_tealt", "gl_foam", "gl_pale", "gl_gold", "gl_shadow", "gl_slate", "gl_sage", "gl_sagelt", "gl_sand", "gl_cream"]
assert not [r for r in items if r["col"] not in SEW], "colour outside the sew list"
for r in items:
    r["vlayer"] = r["layer"]
    r["layer"] = (40 if r.get("sub") == "scale" else 20) + SEW.index(r["col"])

META = dict(sea_des=dict(mask=SEA_DES, x0=BB[0], y0=BB[1], ppm=PPM), star_trace=star_trace, islet_ref=ISL_REF, horizon=HORIZON, sun=SUN, rays=ray_info, burst=BURST, banks=bank_info, islets=islet_info, n_islets=len(islet_info), n_stars=len(stars),
            star_moved=star_moved, skirt=skirt, sea_bars=sea_bars, sea_fill=sea_fill, sea_rows=rows, mock_map=dict(cfx=MM.CFX, necky=MM.NECKY, sx=MM.SX, sy=MM.SY))
pickle.dump(dict(items=items, meta=META), open("scene.pkl", "wb"))
print("items", len(items), "banks", [(b["side"], b["lobes"]) for b in bank_info], "islets", len(islet_info),
      {s: sum(1 for i in islet_info if i["side"] == s) for s in "RL"}, "skirt", skirt, "stars", len(stars), "moved", star_moved,
      "sea dashes", sea_bars, "rows", rows, "rays", len(ray_info), "burst", len(BURST))
