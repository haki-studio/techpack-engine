"""Mockup (inputs/front.png, 770 x 1088 px) <-> garment mm (size M).
Fronts: CF zip x = 368 px, CF neck seam y = 308 px, hem-band seam y = 783 px (= 510 mm on the Drum Island block, M).
SY = 510 / 475. The render is a blouson (hem band gathered), so the body's x scale is set so the outermost mockup art
(vine leaves at x 122 px, lower-left flower leaves at 605 px) lands inside the 15 mm side-seam keep-out: SX = 1.12.
Motif sizes use the mean scale S. Sleeves: see SLEEVE_MAP (mockup sleeve axis -> sleeve-piece coords)."""
import numpy as np
from PIL import Image

CFX, NECKY = 368.0, 308.0
SY = 510.0 / (783.0 - 308.0)
SX = 1.12
S = (SX + SY) / 2

def P(px, py): return ((px - CFX) * SX, (py - NECKY) * SY)
def Pinv(x, y): return (np.asarray(x) / SX + CFX, np.asarray(y) / SY + NECKY)

# Sleeves, front view. Each sleeve: mockup polyline of the sleeve's outer silhouette (= sleeve centreline x = 0 on the
# pattern, the shoulder-seam line) and of the inner visible edge (= front underarm seam), from the armhole seam to the
# cuff seam. A mockup point is mapped by (t along the sleeve, u across from outer to inner edge) -> pattern
# (x = u * half-width(t) on the front half, y = cap-top .. cuff seam).  Read from inputs/front.png.
SLEEVE_PX = {
    # wearer's right sleeve (viewer's left): outer silhouette and inner edge, top (armhole) -> bottom (cuff seam)
    "SR": dict(outer=[(88, 392), (50, 500), (25, 600), (10, 700), (4, 800), (2, 900)],
               inner=[(110, 420), (128, 500), (140, 600), (150, 700), (160, 800), (165, 905)]),
    # wearer's left sleeve (viewer's right)
    "SL": dict(outer=[(645, 392), (690, 500), (711, 600), (726, 700), (731, 800), (733, 895)],
               inner=[(612, 420), (596, 520), (596, 620), (600, 720), (606, 800), (612, 890)]),
}

_IM = None
def mock():
    global _IM
    if _IM is None: _IM = np.array(Image.open("inputs/front.png").convert("RGB")).astype(np.float32)
    return _IM

def warp(bbox, ppm):
    """mockup resampled into front garment mm space: image covering bbox (x0,y0,x1,y1) at ppm px/mm."""
    x0, y0, x1, y1 = bbox; W, H = int((x1-x0)*ppm), int((y1-y0)*ppm)
    xs = x0 + (np.arange(W) + 0.5) / ppm; ys = y0 + (np.arange(H) + 0.5) / ppm
    XX, YY = np.meshgrid(xs, ys); px, py = Pinv(XX, YY)
    from scipy.ndimage import map_coordinates
    a = mock(); out = np.zeros((H, W, 3), np.float32)
    for c in range(3): out[..., c] = map_coordinates(a[..., c], [py, px], order=1, mode="nearest")
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))

# ---------------------------------------------------------------- sleeve map (front view -> sleeve pattern coords)
def _poly_at(pl, t):
    pl = np.asarray(pl, float); seg = np.hypot(*np.diff(pl, axis=0).T); cum = np.r_[0, np.cumsum(seg)]
    s = t * cum[-1]; i = min(np.searchsorted(cum, s, side="right") - 1, len(seg) - 1)
    f = (s - cum[i]) / max(seg[i], 1e-9); return pl[i] + (pl[i+1] - pl[i]) * f

_SG = {}
def _grid(P, mt):
    """forward map (t, u) -> mockup px, sampled densely, for inverting."""
    key = (P, round(mt["cap_h"], 2), round(mt["Lu"], 2))
    if key not in _SG:
        sp = SLEEVE_PX[P]; T = np.linspace(0, 1, 121); U = np.linspace(0, 1, 61)
        pts, tu = [], []
        for t in T:
            o, i = _poly_at(sp["outer"], t), _poly_at(sp["inner"], t)
            for u in U:
                p = (1 - np.cos(np.pi * u)) / 2            # cylinder projection: arc fraction u -> projected fraction p
                pts.append(o + (i - o) * p); tu.append((t, u))
        _SG[key] = (np.array(pts), np.array(tu))
    return _SG[key]

def sleeve_P(P, px, py, mt):
    """mockup px on sleeve P ('SR' / 'SL') -> that sleeve's pattern coords (size of `mt`, normally M).
    t = 0 at the armhole, 1 at the cuff seam; u = 0 at the outer fold (sleeve centreline x = 0), 1 at the front underarm seam.
    y: outer fold runs cap top (-cap_h) -> cuff (Lu), underarm seam runs 0 -> Lu.  x = u * half-width at that y."""
    from scipy.interpolate import griddata
    pts, tu = _grid(P, mt)
    t, u = griddata(pts, tu, [(px, py)], method="linear")[0]
    if np.isnan(t): t, u = griddata(pts, tu, [(px, py)], method="nearest")[0]
    y_out = -mt["cap_h"] + t * (mt["Lu"] + mt["cap_h"]); y_in = t * mt["Lu"]
    y = y_out + (y_in - y_out) * u
    hw = mt["W"] + (mt["Ww"] - mt["W"]) * max(0.0, y) / mt["Lu"]
    x = u * hw
    return (x if P == "SR" else -x, y)

def sleeve_scale(P, px, py, mt):
    """local mm per mockup px at that point (mean of both axes) — motif sizes on the sleeve"""
    a = np.array(sleeve_P(P, px - 2, py, mt)); b = np.array(sleeve_P(P, px + 2, py, mt))
    c = np.array(sleeve_P(P, px, py - 2, mt)); d = np.array(sleeve_P(P, px, py + 2, mt))
    return (np.linalg.norm(b - a) + np.linalg.norm(d - c)) / 8

def sleeve_Pinv(P, x, y, mt):
    """sleeve pattern coords -> mockup px (vectorised); points on the back half map to NaN"""
    x = np.asarray(x, float); y = np.asarray(y, float)
    xs = x if P == "SR" else -x
    hw = mt["W"] + (mt["Ww"] - mt["W"]) * np.clip(y, 0, None) / mt["Lu"]
    u = xs / hw
    t = (y + (1 - u) * mt["cap_h"]) / ((1 - u) * (mt["Lu"] + mt["cap_h"]) + u * mt["Lu"])
    sp = SLEEVE_PX[P]; o = np.array(sp["outer"], float); inn = np.array(sp["inner"], float)
    def at(pl, tt):
        seg = np.hypot(*np.diff(pl, axis=0).T); cum = np.r_[0, np.cumsum(seg)] / seg.sum()
        return np.interp(tt, cum, pl[:, 0]), np.interp(tt, cum, pl[:, 1])
    ox, oy = at(o, np.clip(t, 0, 1)); ix, iy = at(inn, np.clip(t, 0, 1))
    p = (1 - np.cos(np.pi * np.clip(u, 0, 1))) / 2
    px, py = ox + (ix - ox) * p, oy + (iy - oy) * p
    bad = (u < 0) | (u > 1) | (t < 0) | (t > 1)
    return np.where(bad, np.nan, px), np.where(bad, np.nan, py)

def warp_piece(P, bbox, ppm, mt=None):
    """mockup resampled into a piece's mm space (fronts: garment coords; sleeves: pattern coords)"""
    x0, y0, x1, y1 = bbox; W, H = int((x1-x0)*ppm), int((y1-y0)*ppm)
    xs = x0 + (np.arange(W) + 0.5) / ppm; ys = y0 + (np.arange(H) + 0.5) / ppm
    XX, YY = np.meshgrid(xs, ys)
    if P in ("FR", "FL"): px, py = Pinv(XX, YY)
    else: px, py = sleeve_Pinv(P, XX, YY, mt)
    from scipy.ndimage import map_coordinates
    a = mock(); out = np.full((H, W, 3), 245, np.float32); ok = ~np.isnan(px)
    for c in range(3): out[..., c][ok] = map_coordinates(a[..., c], [py[ok], px[ok]], order=1, mode="nearest")
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))
