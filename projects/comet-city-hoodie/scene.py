"""01 front scene (Rev B) — comet over a night city, composed on the size-M fronts (garment mm, unclipped).
References (LESSONS A12):
  * inputs/closeup_mockup_comet.png = the founder's own detail view, registered onto the fronts (closeup.py: projective fit +
    thin-plate refinement on 7 sky features). The COMET (and the cloud it passes behind) is TRACED from it: palette clustering
    (CIEDE2000 to the thread colours), per-colour regions, tatami along the streak.
  * inputs/front.png (mockup) = placement of everything + the cloud layout (the close-up re-composes the clouds), traced in
    5 tones with shading (pale tops, dark undersides) and lobed bank ends.
  * city / figure / lamp / bike / railing / bush / stars: drawn in the close-up's style at the mockup positions + counts.
Output: scene.pkl = {"items": [...], "meta": {...}}. Per-size clipping in art_size.py.  usage: python3 scene.py"""
import cccore
import math, random, pickle
import numpy as np
from scipy import ndimage as ndi
from skimage import measure
from skimage.color import rgb2lab, deltaE_ciede2000
from shapely.geometry import Point, Polygon, LineString, box, MultiPolygon
from shapely.ops import unary_union, nearest_points
from shapely import affinity, prepared
import shapely
from PIL import Image, ImageDraw
import mockmap as MM, front as F, cc_motifs as CM, closeup as CU
from motifs2 import HEX

P = MM.P; S = MM.S
BB, PPM = (-320.0, -40.0, 320.0, 525.0), 4.0
CLIP_M = {s: F.clip_for("M", s) for s in "RL"}
LIM_ALL = {}
for _s in "RL":                       # tightest keep-outs over all sizes, in M coordinates
    _g = CLIP_M[_s]
    for _sz in cccore.SIZES:
        _k = cccore.GRADE[_sz][1]; _g = _g.intersection(affinity.scale(F.clip_for(_sz, _s), 1/_k, 1/_k, origin=(0, 0)))
    LIM_ALL[_s] = _g.buffer(0)
LIM_U = unary_union(list(LIM_ALL.values()))

# ---------------------------------------------------------------- mockup in mm space
_rgb = np.array(MM.warp(BB, PPM)).astype(np.float32)
LUM = _rgb @ np.array([0.3, 0.59, 0.11], np.float32)
_mx, _mn = _rgb.max(2), _rgb.min(2); SAT = (_mx - _mn) / np.maximum(_mx, 1)
H, W = LUM.shape
YY, XX = np.mgrid[0:H, 0:W]; XMM = BB[0] + (XX + 0.5)/PPM; YMM = BB[1] + (YY + 0.5)/PPM
def disk(mm): r = max(1, int(round(mm*PPM))); y, x = np.ogrid[-r:r+1, -r:r+1]; return x*x + y*y <= r*r
def rast(geoms, bb=BB, ppm=PPM, shape=None):
    w_, h_ = (shape[1], shape[0]) if shape else (W, H)
    im = Image.new("L", (w_, h_), 0); d = ImageDraw.Draw(im)
    for g in geoms:
        for p in CM.polys(g):
            d.polygon([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in p.exterior.coords], fill=255)
            for h in p.interiors: d.polygon([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in h.coords], fill=0)
    return np.array(im) > 127
PANEL = rast([F.PANEL_R, F.PANEL_L]) & (np.abs(XMM) > 13)

def mask_polys(mask, bb=BB, ppm=PPM, min_area=1.5, simplify=0.25, min_hole=2.0):
    """mask -> polygons (holes kept when > min_hole mm²)"""
    out = []
    lab, n = ndi.label(mask)
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        m = np.pad(lab[sl] == i, 1)
        if m.sum() / ppm**2 < min_area: continue
        rings = []
        for c in measure.find_contours(m.astype(float), 0.5):
            if len(c) < 5: continue
            pts = [(bb[0] + (sl[1].start + x - 1 + 0.5)/ppm, bb[1] + (sl[0].start + y - 1 + 0.5)/ppm) for y, x in c]
            p = Polygon(pts).buffer(0)
            if p.area > 0.05: rings.append(p)
        if not rings: continue
        rings.sort(key=lambda p: -p.area); g = rings[0]
        for r_ in rings[1:]:
            if g.contains(r_.representative_point()) and r_.area >= min_hole: g = g.difference(r_)
        g = g.buffer(0).simplify(simplify)
        if g.area >= min_area: out.append(g)
    return out

items = []
def add(regs, sew, z=None, **kw):
    for r in regs:
        g = r["geom"]
        if g is None or g.is_empty: continue
        r = dict(r); r.update(kw); r["sew"] = sew; r["z"] = (z if z is not None else 0) * 100000 + len(items); r["el"] = "01"
        r.setdefault("ko", True); r.setdefault("kob", 0.0); r.setdefault("unit", None)
        items.append(r)
Z = dict(comet=3, meteor=4, cloud=5, star=6, glow=7, far=8, farwin=9, near=10, nearwin=11, rail=14, bush=15, lamp=16, bike=17, figure=18)

METEORS_PX = [((207, 421), (246, 381), 1.6), ((297, 486), (342, 419), 1.5), ((392, 394), (431, 341), 1.4), ((500, 330), (530, 301), 1.2),
              ((530, 394), (578, 352), 1.4), ((495, 490), (548, 434), 1.5), ((451, 599), (495, 542), 1.5),
              ((415, 430), (500, 355), 1.2)]   # seeds (mockup px); the streaks are traced below
# A14: each meteor is TRACED - the hand-picked mockup px are seeds only; the streak's own pixels (bright, blue > red) within 5 mm of
# the seed line give its axis (PCA), its two ends (2nd / 98th percentile along the axis) and its width (perpendicular spread)
_streak_px = (_rgb[..., 2] > _rgb[..., 0] + 35) & (LUM > 62)
_pts_all = np.c_[XMM[_streak_px], YMM[_streak_px]]
from scipy.spatial import cKDTree as _KD
_kd_s = _KD(_pts_all)
MET_TRACED = []; MET_SIL = []
for i, (h, t, w) in enumerate(METEORS_PX):
    a_, b_ = np.array(P(*h)), np.array(P(*t)); seg = LineString([a_, b_])
    cand = _pts_all[_kd_s.query_ball_point((a_ + b_)/2, np.linalg.norm(b_ - a_)/2 + 6)]
    if len(cand): cand = cand[np.array([seg.distance(Point(*q)) < 5.0 for q in cand])]
    if len(cand) >= 30:
        c0 = cand.mean(0); u_, s_, vt = np.linalg.svd(cand - c0, full_matrices=False); d_ = vt[0]
        if np.dot(d_, b_ - a_) < 0: d_ = -d_
        pr = (cand - c0) @ d_; pp = (cand - c0) @ np.array([-d_[1], d_[0]])
        hh, tt = c0 + d_*np.percentile(pr, 2), c0 + d_*np.percentile(pr, 98)
        wd = float(np.clip(3.0 * np.std(pp), 1.6, 4.6))
    else:
        hh, tt, wd = a_, b_, w + 1.2
    # silhouette: the streak's own pixels near the fitted axis (window raster), smoothed - stitched as the meteor's outline
    _x0, _y0 = min(hh[0], tt[0]) - 6, min(hh[1], tt[1]) - 6; _x1, _y1 = max(hh[0], tt[0]) + 6, max(hh[1], tt[1]) + 6
    _c0, _c1 = int((_x0 - BB[0])*PPM), int((_x1 - BB[0])*PPM); _r0, _r1 = int((_y0 - BB[1])*PPM), int((_y1 - BB[1])*PPM)
    _w = _streak_px[_r0:_r1, _c0:_c1].copy()
    _ax = LineString([hh, tt]).buffer(wd/2 + 1.2)
    _w &= rast([_ax], (_x0, _y0, _x0 + (_c1 - _c0)/PPM, _y0 + (_r1 - _r0)/PPM), PPM, _w.shape)
    _w = ndi.binary_opening(ndi.binary_closing(_w, structure=np.ones((3, 3))), structure=np.ones((2, 2)))
    _sil = unary_union(mask_polys(_w, (_x0, _y0), PPM, min_area=2.0, simplify=0.2, min_hole=99.0)) if _w.any() else Polygon()
    MET_SIL.append(_sil)
    MET_TRACED.append((tuple(np.round(hh, 1)), tuple(np.round(tt, 1)), round(wd, 2), int(len(cand))))

# ================================================================ comet: traced from the registered close-up
SPINE_MM = [(-80, 320), (-50, 273), (-17, 231), (23, 199), (43, 181), (87, 150), (133, 117), (175, 82), (205, 55), (232, 30), (252, 12)]
SPINE = CM.smooth_pts(SPINE_MM, 220)
def spread_v(t): return np.interp(t, [0.0, 0.12, 0.3, 0.5, 0.7, 0.85, 1.0], [1.4, 3.6, 8.0, 14.0, 18.5, 20.5, 21.0])
def spread(t): return float(spread_v(t))
ZONE = CM.ribbon(SPINE, np.array([2*(spread(t)*1.35 + 7.0) for t in np.linspace(0, 1, len(SPINE))]))
ZONE = ZONE.union(Point(SPINE[0]).buffer(9)).union(Point(SPINE[-1]).buffer(16)).buffer(3).buffer(-3)
CB, CPPM = tuple(np.array(ZONE.bounds) + [-2, -2, 2, 2]), 5.0
_cu, _cm = CU.cu_warp(CB, CPPM)
_ch, _cw = _cu.shape[:2]
_cl = rgb2lab(_cu / 255.0)
COMET_COLS = ["cc_royal", "cc_azure", "cc_violet", "cc_lilac", "cc_rose", "cc_white"]
CLOUD_COLS = ["cc_ice", "cc_cloud", "cc_dusk"]
_ALL = COMET_COLS + CLOUD_COLS + ["fabric"]
def _lab_of(h): return rgb2lab(np.array([[[int(h[i:i+2], 16)/255 for i in (1, 3, 5)]]]))[0, 0]
_ref = [_lab_of(HEX[c]) for c in COMET_COLS + CLOUD_COLS] + [_lab_of("#121A2C")]
_d = np.stack([deltaE_ciede2000(_cl, np.broadcast_to(r_, _cl.shape)) for r_ in _ref], -1)
_lab = np.argmin(_d, -1)
_zm = rast([ZONE], CB, CPPM, (_ch, _cw)) & _cm
# comet pixels = saturated or bright (not fabric, not grey cloud); each gets the nearest COMET thread
_chroma = np.hypot(_cl[..., 1], _cl[..., 2])
_cand = _zm & ((_chroma > 22) | ((_cl[..., 0] > 62) & (_chroma > 8))) & ~np.isin(_lab, [len(COMET_COLS) + i for i in range(3)])
_mk = np.array(MM.warp(CB, CPPM)).astype(np.float32)[:_ch, :_cw]
_ml = rgb2lab(_mk / 255.0); _mch = np.hypot(_ml[..., 1], _ml[..., 2])
_zall = rast([ZONE], CB, CPPM, (_ch, _cw))
_mcand = _zall & ((_mch > 26) | ((_ml[..., 0] > 66) & (_mch > 10)))
_mcand = ndi.binary_opening(_mcand, structure=np.ones((2, 2)))
_mcand &= ~rast([LineString([h_, t_]).buffer(w_/2 + 1.0) for h_, t_, w_, n_ in MET_TRACED], CB, CPPM, (_ch, _cw))   # meteors are their own motifs
_md = np.stack([deltaE_ciede2000(_ml, np.broadcast_to(r_, _ml.shape)) for r_ in _ref[:len(COMET_COLS)]], -1)
_use_m = _mcand & ~_cand                                           # mockup fills where the close-up has no comet pixel
_cand = _cand | _mcand
_d = _d.copy(); _d[..., :len(COMET_COLS)] = np.where(_use_m[..., None], _md, _d[..., :len(COMET_COLS)])
_zm = _zall
_cand = ndi.binary_closing(_cand, structure=np.ones((3, 3))) & _zm
_cand = ndi.binary_fill_holes(_cand) & ~(ndi.binary_fill_holes(_cand) & ~_cand & (ndi.uniform_filter(_cand.astype(np.float32), 9) < 0.35))
# colour: band model across the bundle, read from the close-up (upper-left edge -> lower-right edge):
#   azure streaks | royal | lilac | white core line | pink | violet | royal | azure, boundaries wavy along the comet (streaks);
# the close-up's own bright core pixels (white / pink / lilac / violet) override where it is registered
_YY, _XX = np.mgrid[0:_ch, 0:_cw]; _px = CB[0] + (_XX + 0.5)/CPPM; _py = CB[1] + (_YY + 0.5)/CPPM
from scipy.spatial import cKDTree
_sp = np.array(SPINE); _kd = cKDTree(_sp)
_dd, _ii = _kd.query(np.c_[_px.ravel(), _py.ravel()])
_tg = np.gradient(_sp, axis=0); _tg /= np.linalg.norm(_tg, axis=1)[:, None]; _nr = np.c_[-_tg[:, 1], _tg[:, 0]]
_rel = np.c_[_px.ravel(), _py.ravel()] - _sp[_ii]
_sd = (_rel * _nr[_ii]).sum(1); _tt = _ii / (len(_sp) - 1.0)
_half = spread_v(_tt)*1.35 + 7.0
_o = (_sd / _half).reshape(_ch, _cw); _t = _tt.reshape(_ch, _cw)
_seg = np.r_[0.0, np.cumsum(np.linalg.norm(np.diff(_sp, axis=0), axis=1))]
_s = (_seg[_ii] + (_rel * _tg[_ii]).sum(1)).reshape(_ch, _cw)      # continuous arc length along the comet (no 2 mm steps)
_o2 = _o + 0.06*np.sin(_s/6.0 + 13*_o) + 0.015*np.sin(_s/2.5 + 29*_o)
BANDS = [(-0.62, "cc_azure"), (-0.24, "cc_royal"), (-0.08, "cc_lilac"), (0.0, "cc_white"), (0.10, "cc_rose"), (0.30, "cc_violet"), (0.58, "cc_royal"), (9, "cc_azure")]
_band = np.full((_ch, _cw), COMET_COLS.index("cc_azure"))
for lim_, col_ in reversed(BANDS):
    _band = np.where(_o2 < lim_, COMET_COLS.index(col_), _band)
_band = np.where((_t > 0.86) & np.isin(_band, [COMET_COLS.index("cc_white"), COMET_COLS.index("cc_rose")]), COMET_COLS.index("cc_lilac"), _band)
_band = np.where((_t < 0.06) & (_band != COMET_COLS.index("cc_white")), COMET_COLS.index("cc_azure"), _band)
_cu_core = _cm & _zm & ~_use_m & np.isin(np.argmin(_d[..., :len(COMET_COLS)], -1), [COMET_COLS.index(c) for c in ("cc_white", "cc_rose", "cc_lilac", "cc_violet")]) & (np.abs(_o) < 0.45)
_cu_core = ndi.binary_opening(_cu_core, structure=np.ones((2, 2)))
_clab = np.where(_cand, np.where(_cu_core, np.argmin(_d[..., :len(COMET_COLS)], -1), _band), -1)
COM_ANG = math.degrees(math.atan2(SPINE[-1][1] - SPINE[0][1], SPINE[-1][0] - SPINE[0][0]))
n_comet = 0
# the cloud the comet passes behind (close-up), 3 tones, stacked
_cloudm = np.isin(_lab, [len(COMET_COLS) + i for i in range(3)]) & _zm
_cloudm = ndi.binary_closing(ndi.binary_opening(_cloudm, structure=np.ones((3, 3))), structure=np.ones((3, 3)))
_cl_lab, _cl_n = ndi.label(_cloudm); _cl_s = ndi.sum(_cloudm, _cl_lab, range(1, _cl_n + 1)) / CPPM**2
_cl_y = np.array([c[0] for c in ndi.center_of_mass(_cloudm, _cl_lab, range(1, _cl_n + 1))]) / CPPM + CB[1] if _cl_n else np.array([])
# only the cloud bank the comet really passes behind (y > 170 at M): faded comet pixels higher up read as cloud tones = ghost tails
_cloudm = np.isin(_cl_lab, 1 + np.nonzero((_cl_s >= 25.0) & (_cl_y > 170.0))[0])
_mcl = _zall & (_ml[..., 0] > 45) & (_ml[..., 0] < np.where((_py > 185) & (_py < 245), 95, 78)) & (_mch < 18) & (_py > 170.0)    # the MOCKUP's cloud in front of the comet (A14)
_mcl = ndi.binary_opening(ndi.binary_closing(_mcl, structure=np.ones((3, 3))), structure=np.ones((3, 3)))
_cloudm = _cloudm | _mcl
_mcc0 = ndi.binary_closing(_mcand, structure=np.ones((3, 3))) & _zall
_cloudm |= _zall & (_py > 185.0) & (_py < 245.0) & (_px > 0) & ~_mcc0 & (_ml[..., 0] > 40)   # crossing: everything the mockup shows that is not comet is cloud
_cloudm &= ~ndi.binary_dilation(_mcand, iterations=2)                 # the mockup shows the comet here: cloud stays off it
_cl_tone = {c: _cloudm & (_lab == len(COMET_COLS) + i) for i, c in enumerate(CLOUD_COLS)}
for zz, (col, m) in enumerate((("cc_dusk", _cloudm), ("cc_cloud", _cl_tone["cc_cloud"] | _cl_tone["cc_ice"]), ("cc_ice", _cl_tone["cc_ice"]))):
    m = ndi.binary_opening(m & _cloudm, structure=np.ones((2, 2)))
    _mlum = _mk @ np.array([0.3, 0.59, 0.11], np.float32)
    m &= ndi.gaussian_filter((_mlum > 62).astype(np.float32), 1.5*CPPM) > 0.5
    for g in mask_polys(m, CB, CPPM, min_area=2.0 if zz else 40.0, simplify=0.2, min_hole=3.0):
        add([CM.R(col, g, "tatami", 0.0, "COM-cl", kob=0.0, kgrp="clouds", cref=g.centroid.y)], "cloud", Z["cloud"] + 0.1*zz)
# ---- strands on top of the traced body: tapering satin streaks inside the traced extent (per-t extent of the traced mask)
_OMM = _o * (spread_v(_t)*1.35 + 7.0)
_tb = np.linspace(0, 1, 41); _ext = []
for i_ in range(40):
    sel = _mcand & (_t >= _tb[i_]) & (_t < _tb[i_ + 1])         # A12/A14: the body extent follows the MOCKUP's comet pixels (placement ref)
    if sel.sum() < 20: _ext.append(None); continue
    ov = _OMM[sel]
    _ext.append((np.percentile(ov, 4), np.percentile(ov, 96)))
_ok = [i_ for i_, e in enumerate(_ext) if e]
_tm = np.array([(_tb[i_] + _tb[i_ + 1])/2 for i_ in _ok]); _lo = np.array([_ext[i_][0] for i_ in _ok]); _hi = np.array([_ext[i_][1] for i_ in _ok])
_lo = ndi.gaussian_filter1d(_lo, 3.0, mode='nearest'); _hi = ndi.gaussian_filter1d(_hi, 3.0, mode='nearest')
def ext(t): return float(np.interp(t, _tm, _lo)), float(np.interp(t, _tm, _hi))
# ---- body (Rev B review 1): the WHOLE traced extent is filled (broad body), tatami along the streak, 9 colour bands across
#      the bundle (upper-left edge -> lower-right edge), wavy band edges along the comet; feathered (jagged) edges toward the tail
_omm = _OMM
_LO = np.interp(_t, _tm, _lo); _HI = np.interp(_t, _tm, _hi)
_f = (_omm - _LO) / np.maximum(_HI - _LO, 0.5)
_fe = (0.03 + 0.22*_t**1.5) * np.clip(0.5 + 0.3*np.sin(_s/2.3 + 7.0*_t) + 0.25*np.sin(_s/5.3 + 1.0) + 0.15*np.sin(_s/0.97 + 2.0), 0, 1)      # feather depth (fraction)
_bodym = _zall & (_f > _fe) & (_f < 1 - _fe) & (_t > 0.015) & (_t < 0.985)
_mcc = ndi.binary_closing(_mcand, structure=np.ones((3, 3))) & _zall
_cross = (_py > 185.0) & (_py < 245.0) & (_px > 0)                  # FL cloud crossing: only where the mockup shows the comet between lobes
_bodym = np.where(_cross, _mcc, _bodym | _mcc)
_bodym = ndi.binary_opening(_bodym, structure=np.ones((2, 2)))   # + every mockup comet pixel (A14)
# white core line position across the bundle traced from the close-up (median f of its white/pink pixels per t), smoothed
_corem = _cu_core & _zall & (_f > 0) & (_f < 1)
_fc_t, _fc_v = [], []
for i_ in range(40):
    sel = _corem & (_t >= _tb[i_]) & (_t < _tb[i_ + 1])
    if sel.sum() >= 15: _fc_t.append((_tb[i_] + _tb[i_ + 1])/2); _fc_v.append(float(np.median(_f[sel])))
FC = (np.array(_fc_t), ndi.gaussian_filter1d(np.clip(_fc_v, 0.35, 0.85), 2.0, mode="nearest")) if len(_fc_t) >= 4 else (np.array([0, 1]), np.array([0.715, 0.715]))
def fcore(t): return float(np.interp(t, FC[0], FC[1]))
_fcm = np.interp(_t, FC[0], FC[1])
_f2 = _f - _fcm + 0.715 + 0.05*np.sin(_s/6.0 + 13*_f) + 0.02*np.sin(_s/2.5 + 29*_f)
FBANDS = [(0.18, "cc_azure"), (0.50, "cc_royal"), (0.61, "cc_violet"), (0.68, "cc_lilac"), (0.735, "cc_white"),
          (0.755, "cc_rose"), (0.80, "cc_lilac"), (0.88, "cc_violet"), (9, "cc_royal")]
_band = np.full((_ch, _cw), COMET_COLS.index("cc_royal"))
for lim_, col_ in reversed(FBANDS):
    _band = np.where(_f2 < lim_, COMET_COLS.index(col_), _band)
_band = np.where((_t > 0.86) & np.isin(_band, [COMET_COLS.index("cc_white"), COMET_COLS.index("cc_rose")]), COMET_COLS.index("cc_lilac"), _band)
_band = np.where((_t < 0.08) & ~np.isin(_band, [COMET_COLS.index("cc_white"), COMET_COLS.index("cc_rose")]), COMET_COLS.index("cc_azure"), _band)
# head (below the cloud, FR): azure / royal body, the violet only as a thin lower edge (mockup + close-up)
_hd = (_t < 0.22) & (_f2 < 0.80)
_band = np.where(_hd & (_band == COMET_COLS.index("cc_violet")), COMET_COLS.index("cc_royal"), _band)
_band = np.where(_hd & (_band == COMET_COLS.index("cc_lilac")), COMET_COLS.index("cc_azure"), _band)
_clab = np.where(_bodym, np.where(_cu_core & _bodym, np.argmin(_d[..., :len(COMET_COLS)], -1), _band), -1)
n_comet = 0
for k, col in enumerate(COMET_COLS):
    m = ndi.binary_opening(_clab == k, structure=np.ones((2, 2)))
    for g in mask_polys(m, CB, CPPM, min_area=1.0 if col in ("cc_white", "cc_rose") else 1.4, simplify=0.15, min_hole=1.5):
        core = col in ("cc_white", "cc_rose", "cc_lilac")
        add([CM.R(col, g, "tatami", COM_ANG, "COM-core" if core else "COM", kob=0.0, kgrp="comet")], "comet", Z["comet"] + 0.01*k); n_comet += 1
_N = np.c_[-_tg[:, 1], _tg[:, 0]]
def pos(t, omm):
    i = np.clip(t * (len(_sp) - 1), 0, len(_sp) - 1.001); j = int(i); f_ = i - j
    p = _sp[j]*(1 - f_) + _sp[j + 1]*f_; n_ = _N[j]*(1 - f_) + _N[j + 1]*f_
    return p + n_ * omm
def band_col(of):
    for lim_, col_ in BANDS:
        if of < lim_: return col_
    return "cc_azure"
def fband_col(f2):
    for lim_, col_ in FBANDS:
        if f2 < lim_: return col_
    return "cc_royal"
STRAND_ON = {"cc_azure": ["cc_royal", "cc_azure", "cc_white"], "cc_royal": ["cc_azure", "cc_azure", "cc_violet"], "cc_violet": ["cc_lilac", "cc_royal", "cc_azure"],
             "cc_lilac": ["cc_violet", "cc_violet", "cc_white"], "cc_rose": ["cc_lilac", "cc_white"], "cc_white": ["cc_lilac", "cc_azure"]}
srng = random.Random(41); n_str = 0
def streak(tc, f, L, wmax, col, grp="COM", curl=0.0, drift=0.0):
    ts = np.linspace(max(0.0, tc - L/2), min(1.0, tc + L/2), 36)
    if len(ts) < 3 or ts[-1] - ts[0] < 0.03: return 0
    u = (ts - ts[0]) / (ts[-1] - ts[0])
    pts = []
    for t, uu in zip(ts, u):
        lo, hi = ext(t); om = lo + (hi - lo) * np.clip(f + drift*(uu - 0.5) + curl*uu*uu, -0.15, 1.15)
        pts.append(pos(t, om))
    pts = np.array(pts)
    w = 0.85 + (wmax - 0.85) * np.sin(np.pi * np.clip(u*0.85 + 0.12, 0, 1)) ** 0.7       # widest nearer the head, pointed tips
    g = CM.ribbon(pts, w)
    if g.is_empty or g.area < 1.0: return 0
    add([CM.R(col, g, "satin", "auto", grp, kob=0.0, kgrp="comet")], "comet", Z["comet"] + 0.5 + 0.001*len(items)); return 1
for i_ in range(44):                                   # main streaks
    f = srng.uniform(-0.02, 1.02); edge = min(f, 1 - f)
    L = srng.uniform(0.25, 0.55) if edge < 0.2 else srng.uniform(0.4, 0.85)
    tc = srng.uniform(L/2 - 0.05, 1.02 - L/2)
    of = (f - 0.5) * 2 * 0.9
    col = fband_col(f - fcore(tc) + 0.715 + srng.uniform(-0.06, 0.06))
    col = srng.choice(STRAND_ON[col])                     # a neighbour tone of the body under it: the strand reads as texture
    if tc < 0.25 and col in ("cc_violet", "cc_lilac"): col = srng.choice(["cc_azure", "cc_royal"])   # head below the cloud: blue (mockup)
    n_str += streak(tc, f, L, srng.uniform(1.0, 2.4) * (0.75 if edge < 0.15 else 1.0), col, drift=srng.uniform(-0.12, 0.12))
for i_ in range(16):                                   # side strands curling off the edges toward the tail
    side = srng.choice([0, 1]); f = 0.02 if side == 0 else 0.98
    L = srng.uniform(0.12, 0.25); tc = srng.uniform(0.35, 0.95)
    n_str += streak(tc, f, L, srng.uniform(0.9, 1.4), "cc_azure" if srng.random() < 0.6 else "cc_violet", curl=(-0.35 if side == 0 else 0.35))
# core: white line + pink + lilac strands (own stops)
for df, L, tc, w, col in ((-0.09, 0.66, 0.46, 1.8, "cc_lilac"), (0.05, 0.6, 0.42, 1.1, "cc_rose"), (0.0, 0.88, 0.44, 1.3, "cc_white")):
    n_str += streak(tc, fcore(tc) + df, L, w, col, grp="COM-core")
# FL cloud crossing: strands too stay where the mockup shows the comet between the cloud lobes (A14 gate, motif at the zip)
_XB = box(0.0, 185.0, 400.0, 245.0); _MCC = unary_union(mask_polys(_mcc & (_py > 180) & (_py < 250), CB, CPPM, min_area=1.0, simplify=0.15)).buffer(0.4)
_cut = _XB.difference(_MCC)
for r in items:
    if r["sew"] == "comet" and r["geom"].intersects(_cut): r["geom"] = r["geom"].difference(_cut).buffer(0)
COMET_U = unary_union([r["geom"] for r in items if r["sew"] == "comet"]).buffer(0)

# ================================================================ meteors (outside the comet zone), falling star
_mrng = random.Random(8); n_met = 0
for i, (hh, tt, wd, _n) in enumerate(MET_TRACED):
    seg = LineString([hh, tt])
    _regs = CM.meteor(tuple(hh), tuple(tt), w_head=wd, w_tail=max(1.2, wd*0.9), unit=None)
    if not MET_SIL[i].is_empty: _regs[0] = dict(_regs[0], geom=_regs[0]["geom"].intersection(MET_SIL[i].buffer(0.6)).union(MET_SIL[i].buffer(0.25)).buffer(0))   # traced silhouette (A14)
    add(_regs, "meteor", Z["meteor"] + (1.0 if ZONE.buffer(-3).intersects(seg) else 0), kob=(2.0 if ZONE.intersects(seg) else 0.4), kgrp=f"met{i}"); n_met += 1   # kgrp: head dot + core knock the streak exactly (no ring)   # clipped at keep-outs, not dropped
RS = P(403.5, 597.5)
trail = CM.smooth_pts([P(404.7, 530.0), P(404.3, 560.0), P(403.9, 589.0)], 30)
_tw = np.linspace(1.6, 2.5, len(trail)); _n3 = len(trail)//3      # mockup trail ~2.5 mm at the star
add([CM.R("cc_violet", CM.ribbon(trail[:2*_n3 + 1], _tw[:2*_n3 + 1]), "satin", "auto", "MET", kob=0.3)], "meteor", Z["meteor"], unit="redstar")
add([CM.R("cc_lilac", CM.ribbon(trail[2*_n3:], _tw[2*_n3:]), "satin", "auto", "MET", kob=0.3)], "meteor", Z["meteor"], unit="redstar")
add([CM.R("cc_white", CM.ribbon(trail[2*_n3 + 3:], np.full(len(trail) - 2*_n3 - 3, 0.7)), "satin", "auto", "MET", kob=0.0)], "meteor", Z["meteor"] + 0.2, unit="redstar")
add(CM.falling_star(*RS, r=9.5), "meteor", Z["meteor"] + 0.5, unit="redstar")
for (sx, sy, kk) in ((411, 582, 0.8), (395, 588, 0.7), (413, 606, 0.65)):
    add(CM.star(*P(sx, sy), "cross", "cc_white", "redstar", k=kk), "meteor", Z["meteor"], unit="redstar")
for (sx, sy) in ((398, 604), (409, 592)):
    add([CM.R("cc_red", Point(P(sx, sy)).buffer(0.75, quad_segs=8), "satin", "auto", "DOT", kob=0.3)], "meteor", Z["meteor"], unit="redstar")

# ================================================================ stars (every mockup star; varied size, glow)
STARS_PX = [
 (196.7, 309.5, "cross", "cc_white"), (227.5, 313.7, "dot", "cc_white"), (208.7, 327.5, "big", "cc_lilac"), (187, 329.5, "dot", "cc_lilac"),
 (272.5, 329.5, "sparkle", "cc_azure"), (297.5, 323.7, "dot", "cc_white"), (243.7, 357, "cross", "cc_white"), (192, 363.7, "sparkle", "cc_lilac"),
 (176.5, 367.5, "dot", "cc_white"), (181.5, 368.0, "dot", "cc_white"), (246, 380, "sparkle", "cc_azure"), (270, 375, "dot", "cc_white"),
 (297.5, 374.5, "sparkle", "cc_azure"), (243, 420.5, "cross", "cc_white"), (291, 439.5, "dot", "cc_white"), (326, 479, "sparkle", "cc_white"),
 (226, 491, "cross", "cc_white"), (186, 497, "dot", "cc_white"), (206, 504.5, "sparkle", "cc_white"), (257.5, 540.5, "dot", "cc_white"),
 (287, 549.5, "cross", "cc_white"), (314.5, 549, "dot", "cc_white"), (206, 574, "dot", "cc_white"), (180, 580, "sparkle", "cc_white"),
 (132.5, 582.5, "dot", "cc_white"), (340, 590.5, "cross", "cc_white"), (308, 580, "dot", "cc_white"), (327, 605, "dot", "cc_white"),
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
_srng = random.Random(17); stars = []; star_moved = 0
for i, (px, py, kind, col) in enumerate(STARS_PX):
    cx, cy = P(px, py); side = "R" if cx < 0 else "L"
    if ZONE.buffer(-2).contains(Point(cx, cy)) and kind == "dot": continue          # the traced comet already has its sparkle
    k = _srng.uniform(0.75, 1.3) if kind != "dot" else _srng.uniform(0.8, 1.25)
    rr = {"big": 13.0, "sparkle": 8.8, "cross": 4.6, "dot": 1.3}[kind] * k
    inner = LIM_ALL[side].buffer(-(rr + 0.8))
    if not inner.contains(Point(cx, cy)):
        q = nearest_points(inner, Point(cx, cy))[0]; cx, cy = q.x, q.y; star_moved += 1
    glow = None
    if kind in ("sparkle", "cross") and _srng.random() < 0.55:
        glow = "cc_lilac" if col != "cc_lilac" and _srng.random() < 0.5 else "cc_azure"
        if glow == col: glow = "cc_lilac"
    u = f"star{i}"; stars.append((cx, cy, kind, col, round(k, 2), glow))
    add(CM.star_b(cx, cy, kind, col, u, k=k, glow=glow), "star", Z["star"], unit=u)

# ================================================================ clouds: mockup layout, 5 shaded tones, lobed ends
STREAK_U = unary_union([ZONE] + [r["geom"].buffer(4.0) for r in items if r["grp"] in ("MET",)] +
                       [r["geom"].buffer(1.5) for r in items if r["grp"] in ("RSTAR", "DOT", "STAR-c")] +
                       [Point(RS).buffer(10.0)] + [Point(P(x_, y_)).buffer(_STAR_R[k_]) for x_, y_, k_, c_ in STARS_PX])
streakm = rast([STREAK_U])
Ls = ndi.gaussian_filter(LUM, 0.5*PPM)
_inner = rast([F.PANEL_R.buffer(-13), F.PANEL_L.buffer(-13), box(-400, 330, 400, 600).intersection(unary_union([F.PANEL_R, F.PANEL_L]))])
_inner &= ~rast([F.WELT_R.buffer(9), F.WELT_L.buffer(9)]) & (np.abs(XMM) > 16)
cl = (Ls > 60) & (ndi.gaussian_filter(SAT, 0.5*PPM) < 0.72) & PANEL & _inner & (YMM > 88) & (YMM < 408) & ~streakm   # saturated blue = streaks, not cloud
cl = ndi.binary_opening(cl, structure=disk(0.9))
cl = ndi.gaussian_filter(cl.astype(np.float32), 1.1*PPM) > np.where(YMM > 290, 0.25, 0.5)   # soft lobes; the speckled low band above the city (A15 gate) needs a lower density cut
lab, n = ndi.label(cl)
sizes = ndi.sum(cl, lab, range(1, n + 1)) / PPM**2
_cy = np.array([c[0] for c in ndi.center_of_mass(cl, lab, range(1, n + 1))]) / PPM + BB[1] if n else np.array([])
cl = np.isin(lab, 1 + np.nonzero(sizes >= 8.0)[0])                               # A14: every cloud, however small
_holes = ndi.binary_fill_holes(cl) & ~cl
_hl, _hn = ndi.label(_holes); _hs = ndi.sum(_holes, _hl, range(1, _hn + 1)) / PPM**2
cl |= np.isin(_hl, 1 + np.nonzero(_hs < 12.0)[0])                               # no pinholes
# lobed ends: within 6 mm of the (all-size) keep-out line, keep only whole round lobes
_inner_lim = LIM_U.buffer(-8.5)
_lob = []
for _p in CM.polys(_inner_lim):
    for _ring in [_p.exterior] + list(_p.interiors):
        L_ = _ring.length; nlob = max(3, int(L_ / 11.5))
        _lob += [_ring.interpolate(L_ * i / nlob).buffer(6.0, quad_segs=12) for i in range(nlob)]
ALLOW = unary_union([_inner_lim] + _lob).intersection(LIM_U.buffer(-0.8)).buffer(0)
cl &= rast([ALLOW])
cl = ndi.binary_opening(cl, structure=disk(0.8))
lab, n = ndi.label(cl); sizes = ndi.sum(cl, lab, range(1, n + 1)) / PPM**2
cl = np.isin(lab, 1 + np.nonzero(sizes >= 8.0)[0])
# shading: pale tops, dark undersides (vertical derivative of the soft cloud mask) + the mockup's own tone
soft = ndi.gaussian_filter(cl.astype(np.float32), 2.0*PPM)
g = np.zeros_like(soft); sh = int(2.5*PPM)
g[sh:-sh] = soft[:-2*sh] - soft[2*sh:]                                          # >0 near the bottom edge, <0 near the top edge
T = ndi.gaussian_filter(LUM, 0.8*PPM) - 55.0 * g
# tone thresholds = midpoints between the thread luminances (night 41, dusk 90, cloud 133, ice 179, white 240) so the stitched
# tone matches the mockup tone (Rev A/B used 100/128/165: half the cloud area came out ice/white - review 2)
THR = {"cc_night": 66.0, "cc_cloud": 112.0, "cc_ice": 154.0, "cc_white": 205.0}
def tone(m):
    m = ndi.gaussian_filter(m.astype(np.float32), 1.0*PPM) > 0.5                     # rounded tone edges, no posterised steps
    m = ndi.binary_opening(m & cl, structure=disk(0.7))
    lb, nn_ = ndi.label(m); ss = ndi.sum(m, lb, range(1, nn_ + 1)) / PPM**2
    m = np.isin(lb, 1 + np.nonzero(ss >= 5.0)[0])
    hh = ndi.binary_fill_holes(m) & ~m; hl, hn = ndi.label(hh); hs = ndi.sum(hh, hl, range(1, hn + 1)) / PPM**2
    return m | np.isin(hl, 1 + np.nonzero(hs < 4.0)[0])
TONES = [("cc_dusk", cl, 0.0), ("cc_night", tone(T < THR["cc_night"]), 0.1), ("cc_cloud", tone(T >= THR["cc_cloud"]), 0.2),
         ("cc_ice", tone(T >= THR["cc_ice"]), 0.3), ("cc_white", tone(T >= THR["cc_white"]), 0.4)]
n_cloud = 0
for col, m, zz in TONES:
    for gg in mask_polys(m, min_area=3.0 if col != "cc_dusk" else 8.0, simplify=0.2, min_hole=6.0):
        add([CM.R(col, gg, "tatami", 0.0 if col in ("cc_dusk", "cc_night") else 8.0, "CL", kob=0.0, kgrp="clouds")], "cloud", Z["cloud"] + zz); n_cloud += 1
_sil = [r["geom"] for r in items if r["grp"] in ("CL", "COM-cl") and r["col"] == "cc_dusk"]
_tree = shapely.STRtree(_sil)
for r in items:
    if r["grp"] != "CL": continue
    q = r["geom"].representative_point(); hit = [int(j) for j in _tree.query(q) if _sil[int(j)].buffer(0.05).contains(q)]
    r["cref"] = _sil[hit[0]].centroid.y if hit else r["geom"].centroid.y
CLOUD_U = unary_union([r["geom"] for r in items if r["grp"] in ("CL", "COM-cl")]).buffer(0)

# ================================================================ city: dozens of towers, window grids, neon, glow
FAR_PX = [(122, 140, 664), (140, 166, 650), (192, 201, 671), (204, 230, 660), (240, 259, 662.5), (259, 281, 649), (282, 295, 671),
          (299, 320, 665), (320, 341, 656), (349, 362, 660),
          (374, 398, 682), (430, 446, 690), (450, 471, 670), (480, 501, 680), (501, 518, 677.5), (516, 541, 681), (541, 556, 685), (591, 611, 661)]
NEAR_PX = [(122, 152, 677), (152, 202, 694), (202, 240, 690), (240, 260, 685), (260, 300, 692), (300, 325, 686), (325, 362, 690),
           (374, 391, 692), (391, 448, 699), (448, 481, 697), (481, 516, 692), (516, 541, 690), (541, 581, 705), (581, 611, 692)]
def rail_y(px): return 720.0 + (px - 130.0) * 7.0 / 470.0
def ymm(px, py): return P(px, py)[1]
_fx = [P((a + b)/2, t)[0] for a, b, t in FAR_PX]; _fy = [P((a + b)/2, t)[1] for a, b, t in FAR_PX]
_nx = [P((a + b)/2, t)[0] for a, b, t in NEAR_PX]; _ny = [P((a + b)/2, t)[1] for a, b, t in NEAR_PX]
_o = np.argsort(_fx); _fx = np.array(_fx)[_o]; _fy = np.array(_fy)[_o]; _o = np.argsort(_nx); _nx = np.array(_nx)[_o]; _ny = np.array(_ny)[_o]
def far_top(x): return float(np.interp(x, _fx, _fy))
def near_top(x): return float(np.interp(x, _nx, _ny))
def rail_mm(x): px = MM.Pinv(x, 0)[0]; return ymm(px, rail_y(px))
def kerb_mm(x): px = MM.Pinv(x, 0)[0]; return ymm(px, rail_y(px) + 40.0)
crng = random.Random(23)
towers = []                                         # (layer, box, colour)
for layer, wmin, wmax, top_fn, bot_fn in (("far", 6.0, 15.0, far_top, rail_mm), ("near", 9.0, 22.0, near_top, kerb_mm)):
    x = -300.0
    while x < 300:
        w = crng.uniform(wmin, wmax); xc = x + w/2
        if abs(xc) < 8: x += w; continue
        top = top_fn(xc) + crng.uniform(-12, 7) - (crng.uniform(10, 26) if crng.random() < 0.18 else 0)
        bot = bot_fn(xc) - (4 if layer == "far" else 0)
        rr_ = crng.random()
        # review 3: far row = lighter dusk / cloud silhouettes against the haze, near row = dark navy / dusk towers
        if layer == "far": col = "cc_dusk" if rr_ < 0.74 else ("cc_cloud" if rr_ < 0.86 else "cc_night")
        else: col = "cc_night" if rr_ < 0.58 else "cc_dusk"
        towers.append((layer, box(x, top, x + w, bot), col))
        x += w + (crng.uniform(0, 2.5) if layer == "far" else crng.uniform(0.0, 1.2))
# horizon glow (review 3): pale haze band behind the whole skyline + violet / rose glow concentrated toward the zip (mockup)
xs = np.linspace(-300, 300, 200)
haze = Polygon([(x, far_top(x) - 14 + 3.0*math.sin(x/11.0)) for x in xs] + [(x, near_top(x) + 3) for x in xs[::-1]]).buffer(0)
add([CM.R("cc_cloud", haze, "tatami", 0.0, "GLOW", kob=0.0)], "glow", Z["glow"] - 0.2)
def _glow_band(h0, amp, per, ph, xr):
    xx = np.linspace(-xr, xr, 120); env = np.clip(1.15 - np.abs(xx)/xr, 0, 1) ** 0.6
    return Polygon([(x, near_top(x) + 3 - (h0*e + 1.0) + amp*e*math.sin(x/per + ph)) for x, e in zip(xx, env)] + [(x, near_top(x) + 3) for x in xx[::-1]]).buffer(0)
vio = unary_union([_glow_band(26, 4, 9.0, 0, 250)])
ros = unary_union([_glow_band(15, 3, 6.5, 1, 170)])
add([CM.R("cc_violet", vio.difference(ros).buffer(-0.5).buffer(0.5), "tatami", 0.0, "GLOW", kob=0.0)], "glow", Z["glow"])
add([CM.R("cc_rose", ros, "tatami", 0.0, "GLOW", kob=0.0)], "glow", Z["glow"] + 0.1)
n_win = n_sign = n_ant = n_edge = 0
for layer, tb, col in towers:
    zt = Z[layer]; b = tb.bounds; w = b[2] - b[0]
    add([CM.R(col, tb, "tatami", 90.0, "BLD" if layer == "near" else "BLD-far", kob=0.3)], "building", zt)
    # lit edge: a thin pale line down the side facing the comet glow + along the roof (separates the towers, mockup)
    if layer == "near" or crng.random() < 0.5:
        ec = "cc_cloud" if col == "cc_night" else "cc_ice"
        sx_ = b[0] if (b[0] + b[2]) / 2 > 0 else b[2] - 1.0
        edge = box(sx_, b[1], sx_ + 1.0, b[3]).union(box(b[0], b[1], b[2], b[1] + 1.0))
        add([CM.R(ec, edge, "satin", "auto", "BLD-edge", kob=0.0)], "window", zt + 0.4); n_edge += 1
    # windows: a lit GRID per tower (whole floors / column pairs lit, the rest dark), mostly gold (mockup), some cool towers
    if layer == "near": ww, wh, px_, py_, p_floor, p_win = 1.6, 2.0, 3.2, 3.8, 0.62, 0.72
    else:               ww, wh, px_, py_, p_floor, p_win = 1.4, 1.6, 2.8, 3.3, 0.40, 0.55
    style = crng.random()
    pal = ["cc_gold"] if style < 0.78 else ((["cc_azure"]*3 + ["cc_white"]) if style < 0.92 else (["cc_rose"] + ["cc_gold"]*2))
    if layer == "far" and col == "cc_cloud": pal = ["cc_white", "cc_gold"]
    stripes = layer == "near" and w > 14 and crng.random() < 0.05                        # office tower: white light bands
    ncol = int((w - 1.6) // px_)
    if ncol >= 1:
        x0 = b[0] + (w - (ncol*px_ - (px_ - ww)))/2
        y = b[1] + 2.4; cols_on = [crng.random() < p_win for _ in range(ncol)]
        while y + wh < b[3] - 1.0:
            if stripes:
                add([CM.R("cc_ice", box(x0, y + 0.4, x0 + (ncol - 1)*px_ + ww, y + 1.6), "satin", 90.0, "WIN", kob=0.0)], "window", zt + 0.5); n_win += 1
            elif crng.random() < p_floor:
                for c in range(ncol):
                    if cols_on[c] and crng.random() < 0.88:
                        gw = box(x0 + c*px_, y, x0 + c*px_ + ww, y + wh)
                        add([CM.R(crng.choice(pal), gw, "satin", 0.0, "WIN", kob=0.0)], "window", zt + 0.5); n_win += 1
            y += py_
    # neon signs + antennas
    if layer == "near" and crng.random() < 0.28 and b[3] - b[1] > 18:
        sc = crng.choice(["cc_rose", "cc_rose", "cc_azure"])
        if crng.random() < 0.6:
            sx = b[0] + 0.9 if crng.random() < 0.5 else b[2] - 2.4
            add([CM.R(sc, box(sx, b[1] + 3, sx + 1.5, b[1] + 3 + crng.uniform(7, 13)), "satin", "auto", "SIGN", kob=0.0)], "window", zt + 0.6)
        else:
            add([CM.R(sc, box(b[0] + 1.2, b[1] + 1.2, min(b[2] - 1.2, b[0] + 1.2 + crng.uniform(5, 10)), b[1] + 2.8), "satin", "auto", "SIGN", kob=0.0)], "window", zt + 0.6)
        n_sign += 1
    if (b[1] < (far_top if layer == "far" else near_top)((b[0]+b[2])/2) - 6) and crng.random() < 0.6:
        ax = (b[0] + b[2])/2 + crng.uniform(-w/4, w/4); ah = crng.uniform(6, 14)
        add([CM.R(col, box(ax - 0.5, b[1] - ah, ax + 0.5, b[1] + 0.5), "satin", "auto", "ANT", kob=0.3)], "building", zt + 0.05)
        if crng.random() < 0.5: add([CM.R("cc_red", Point(ax, b[1] - ah - 0.6).buffer(0.75, quad_segs=8), "satin", "auto", "ANT", kob=0.3)], "window", zt + 0.6)
        n_ant += 1

# ================================================================ railing (dark rails, light edges), kerb
def rail_poly(dy, w, x0=110, x1=625):
    xs_ = np.linspace(x0, x1, 60); pts = [P(x, rail_y(x) + dy) for x in xs_]
    return LineString(pts).buffer(w/2, cap_style="flat")
add([CM.R("cc_night", rail_poly(0.0, 2.8), "satin", "auto", "RAIL", kob=0.0)], "rail", Z["rail"])
add([CM.R("cc_ice", rail_poly(-1.75, 1.0), "satin", "auto", "RAIL-hl", kob=0.0)], "rail", Z["rail"] + 0.1)
add([CM.R("cc_night", rail_poly(38.5, 1.8), "satin", "auto", "RAIL", kob=0.0)], "rail", Z["rail"])
add([CM.R("cc_cloud", rail_poly(37.1, 0.95), "satin", "auto", "RAIL-hl", kob=0.0)], "rail", Z["rail"] + 0.1)
add([CM.R("cc_ice", rail_poly(47.5, 1.1), "satin", "auto", "RAIL-hl", kob=0.0)], "rail", Z["rail"])
# walkway (A15 gate: the mockup's pale pavement band below the kerb was left bare in Rev B): dusk tatami from the kerb down to the
# hem keep-out (art_size slides it with the city band), a pale ice line along its far edge
_wk = Polygon([P(x, rail_y(x) + 40.5) for x in np.linspace(110, 625, 60)] + [(P(x, 0)[0], 540.0) for x in np.linspace(625, 110, 60)]).buffer(0)
add([CM.R("cc_dusk", _wk, "tatami", 0.0, "GND", kob=0.0)], "rail", Z["rail"] - 0.5)
x = 132.0; nb = 0
while x < 612:
    a = P(x, rail_y(x) + 1.6); b = P(x, rail_y(x) + 37.0)
    add([CM.R("cc_night", LineString([a, b]).buffer(0.9, cap_style="flat"), "satin", "auto", "RAIL-b", kob=0.0)], "rail", Z["rail"])
    add([CM.R("cc_ice", LineString([(a[0] - 1.25, a[1]), (b[0] - 1.25, b[1])]).buffer(0.4, cap_style="flat"), "satin", "auto", "RAIL-hl", kob=0.0)], "rail", Z["rail"] + 0.1)
    x += 10.6; nb += 1

# ================================================================ lamp post, bush, bicycle, figure (solid, in front)
def fit_left(make, x0, lim):
    """smallest sideways move (either way) that puts the whole motif inside every size's keep-outs"""
    for dx in [v for a in np.arange(0, 40, 0.5) for v in ((a, -a) if a else (0.0,))]:
        regs = make(x0 - dx)
        if lim.contains(unary_union([r["geom"] for r in regs])): return regs, float(dx)
    raise RuntimeError("motif does not fit the keep-outs")
_limL = LIM_ALL["L"].buffer(-0.6)
lp = P(586, 0)[0]
LAMP_TOP = ymm(586, 594)
def _lamp_head(x):     # only the head must stay whole; the post may pass behind the welt (as in the mockup) and is clipped there
    return [dict(r, geom=r["geom"].intersection(box(x - 20, LAMP_TOP - 5, x + 20, LAMP_TOP + 42))) for r in CM.lamp_b(x, LAMP_TOP, kerb_mm(x) - 2)]
_, lamp_dx = fit_left(_lamp_head, lp, _limL)
for r in CM.lamp_b(lp - lamp_dx, LAMP_TOP, kerb_mm(lp - lamp_dx) - 2):
    hd = r["geom"].intersection(box(-400, LAMP_TOP - 5, 400, LAMP_TOP + 42)); post = r["geom"].difference(box(-400, LAMP_TOP - 5, 400, LAMP_TOP + 42))
    add([dict(r, geom=hd)], "figure", Z["lamp"], unit="lamp")
    add([dict(r, geom=post, unit=None)], "figure", Z["lamp"])
_bush, bush_dx = fit_left(lambda x: CM.bush_b(x, kerb_mm(x) - 1.0, 56.0, 26.0, random.Random(11)), P(560, 0)[0], _limL)
add(_bush, "bush", Z["bush"], unit="bush")
BIKE_REAR = (P(186, 0)[0], 470.0)
add(CM.bicycle_b(*BIKE_REAR, r=26.0, wb=96.0), "bike", Z["bike"], unit="bike")
FIG_FEET = (P(414.7, 0)[0], 499.0)
add(CM.figure_b(*FIG_FEET, H=120.0, wk=1.2), "figure", Z["figure"], unit="figure")

# ================================================================ sew order (one stop per thread): details first, dark tones last
COLSEQ = ["cc_gold", "cc_rose", "cc_red", "cc_violet", "cc_azure", "cc_royal", "cc_lilac", "cc_white", "cc_ice", "cc_cloud", "cc_dusk", "cc_night"]
assert not [r for r in items if r["col"] not in COLSEQ], "colour outside the front palette"
for r in items: r["layer"] = 20 + COLSEQ.index(r["col"])

META = dict(n_comet_strands=n_str, spine=SPINE.tolist(), n_stars=len(stars), star_moved=star_moved, n_meteors=n_met, n_comet_regions=n_comet, n_cloud_regions=n_cloud,
            n_towers=len(towers), n_lit_edges=n_edge, n_far=sum(1 for t in towers if t[0] == "far"), n_near=sum(1 for t in towers if t[0] == "near"),
            n_windows=n_win, n_signs=n_sign, n_antennas=n_ant, n_balusters=nb, closeup_residuals=CU.residuals(), meteors_traced=MET_TRACED,
            lamp_dx=lamp_dx, bush_dx=bush_dx, mock_map=dict(cfx=MM.CFX, necky=MM.NECKY, sx=MM.SX, sy=MM.SY), bike_rear=BIKE_REAR, figure_feet=FIG_FEET)
pickle.dump(dict(items=items, meta=META), open("scene.pkl", "wb"))
pickle.dump(dict(zone=ZONE, streak=STREAK_U, lim=LIM_ALL, glows=unary_union([r["geom"] for r in items if r["grp"] in ("MET", "STAR", "STAR-c", "DOT", "RSTAR")])), open("scene_ref.pkl", "wb"))       # reference exclusions for fidelity.py (A14/A15 gates)
from collections import Counter
print("items", len(items), dict(Counter(r["sew"] for r in items)), {k: v for k, v in META.items() if k.startswith("n_")})
