"""Mockup (inputs/front.png, 755 x 1087) <-> garment mm (size M).
Fronts — landmarks: CF zip x = 368 px, CF neck seam y = 305 px, body side edges at the hem band x = 368 -/+ 242.5 px
(= the block's 1/2 chest 299.5 mm), hem-band seam y = 801 px (= 510 mm below the CF neck). The render is narrower than
the boxy block, so x and y scale differently; motif SIZES use the mean scale S (motifs stay round).
Sleeves — the hanging sleeves show their front half. Along the sleeve: shoulder point (cap top) -> cuff seam on the
mockup = cap top -> cuff seam on the pattern. Across: the visible width (outer silhouette = sleeve centre line,
inner edge = underarm seam) is a half cylinder, so pattern x = W(y) * (asin(2u - 1)/pi + 1/2), u = 0..1 across."""
import math
import numpy as np
from PIL import Image

CFX, NECKY = 368.0, 305.0
SX, SY = 299.5 / 242.5, 510.0 / (801.0 - 305.0)
S = (SX + SY) / 2

def P(px, py): return ((px - CFX) * SX, (py - NECKY) * SY)
def Pinv(x, y): return (np.asarray(x) / SX + CFX, np.asarray(y) / SY + NECKY)

_IM = None
def mock():
    global _IM
    if _IM is None: _IM = np.array(Image.open("inputs/front.png").convert("RGB")).astype(np.float32)
    return _IM

def _remap(px, py, W, H):
    from scipy.ndimage import map_coordinates
    a = mock(); out = np.zeros((H, W, 3), np.float32)
    for c in range(3): out[..., c] = map_coordinates(a[..., c], [py, px], order=1, mode="nearest")
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))

def warp(bbox, ppm):
    """mockup resampled into front garment mm space: image covering bbox (x0,y0,x1,y1) at ppm px/mm."""
    x0, y0, x1, y1 = bbox; W, H = int((x1-x0)*ppm), int((y1-y0)*ppm)
    xs = x0 + (np.arange(W) + 0.5) / ppm; ys = y0 + (np.arange(H) + 0.5) / ppm
    XX, YY = np.meshgrid(xs, ys); px, py = Pinv(XX, YY)
    return _remap(px, py, W, H)

# ---------------------------------------------------------------- sleeves
# silhouette tables (mockup px): y -> (outer edge x, inner edge x); shoulder point + cuff seam y
SLV = {
 "R": dict(top=395.0, cuff=920.0, edges=[(395, 95, 150), (450, 62, 150), (500, 40, 140), (550, 29, 132), (600, 21, 124),
                                         (650, 14, 124), (700, 9, 126), (750, 7, 130), (800, 6, 140), (850, 7, 150), (900, 11, 140), (920, 13, 138)]),
 "L": dict(top=400.0, cuff=915.0, edges=[(400, 640, 590), (450, 670, 600), (500, 690, 601), (550, 703, 600), (600, 715, 602),
                                         (650, 724, 605), (700, 733, 603), (750, 734, 600), (800, 734, 596), (850, 733, 590), (900, 730, 598), (915, 729, 600)]),
}

def _edges(side, py):
    e = SLV[side]["edges"]; ys = [a for a, _, _ in e]
    return float(np.interp(py, ys, [b for _, b, _ in e])), float(np.interp(py, ys, [c for _, _, c in e]))

_SG = {}
def sleeve_dims(size="M"):
    """(cap top y, cuff seam y, half-width function W(y)) of S01 from the pattern"""
    if size not in _SG:
        import front as F
        g, mt = F.pieces(size); pc = g["S01"]
        poly = pc.sew_poly(); b = poly.bounds
        from shapely.geometry import LineString
        def W(y):
            seg = poly.intersection(LineString([(0, y), (b[2] + 5, y)]))
            return max(seg.bounds[2], 1.0) if not seg.is_empty else 1.0
        ys = np.linspace(b[1] + 0.5, b[3] - 0.5, 200); ws = [W(y) for y in ys]
        _SG[size] = (b[1], b[3], ys, np.array(ws))
    return _SG[size]

def SP(side, px, py, size="M"):
    """mockup px -> sleeve pattern mm (S01 coords for 'R', S02 (mirrored) for 'L')"""
    top, cuff, ys, ws = sleeve_dims(size); s = SLV[side]
    t = (py - s["top"]) / (s["cuff"] - s["top"]); y = top + t * (cuff - top)
    xo, xi = _edges(side, py); u = float(np.clip((px - xo) / (xi - xo), 0, 1))
    x = float(np.interp(y, ys, ws)) * (math.asin(2*u - 1) / math.pi + 0.5)
    return (x if side == "R" else -x), y

def SPinv(side, x, y, size="M"):
    top, cuff, ys, ws = sleeve_dims(size); s = SLV[side]
    x = np.asarray(x, float) * (1 if side == "R" else -1); y = np.asarray(y, float)
    t = (y - top) / (cuff - top); py = s["top"] + t * (s["cuff"] - s["top"])
    Wy = np.interp(y, ys, ws); sfr = np.clip(x / Wy, -0.5, 1.0)
    u = (np.sin((sfr - 0.5) * math.pi) + 1) / 2
    e = s["edges"]; eys = [a for a, _, _ in e]
    xo = np.interp(py, eys, [b for _, b, _ in e]); xi = np.interp(py, eys, [c for _, _, c in e])
    px = xo + u * (xi - xo)
    return px, py

def swarp(side, bbox, ppm):
    """mockup resampled into sleeve pattern mm (pixels outside the visible half come out as the mockup edge colour)"""
    x0, y0, x1, y1 = bbox; W, H = int((x1-x0)*ppm), int((y1-y0)*ppm)
    xs = x0 + (np.arange(W) + 0.5) / ppm; ys = y0 + (np.arange(H) + 0.5) / ppm
    XX, YY = np.meshgrid(xs, ys); px, py = SPinv(side, XX, YY)
    return _remap(px, py, W, H)

def sscale(side, py):
    """local mm per mockup px across the sleeve centre line (for motif sizes)"""
    top, cuff, ys, ws = sleeve_dims(); xo, xi = _edges(side, py)
    y = top + (py - SLV[side]["top"]) / (SLV[side]["cuff"] - SLV[side]["top"]) * (cuff - top)
    return (2 * float(np.interp(y, ys, ws)) / math.pi) / abs(xi - xo)
