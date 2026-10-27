"""Mockup <-> garment mm for the Pixel Sky fleece (inputs/front.png, 1500 x 1500 AI render, front only).

FRONT  front.png px -> front garment mm, ISOTROPIC: CF zip x = CFX, CF neck seam y = NECKY, S mm/px from the body length
       (CF neck seam -> hem edge = chart A - K on the fleece block). The render is slimmer than the Drum Island block
       (shoulder 46 vs 53 cm at this scale) — one scale cannot match both; the art keeps the mockup's motif sizes and
       heights, the block keeps its width (PROPOSED). Body sides hidden under the hanging sleeves are not visible.
SLEEVE front.png sleeve patch -> sleeve pattern coords (S01 wearer's right = viewer's LEFT, S02 = viewer's right): the
       visible half of a hanging sleeve is its FRONT half; outer silhouette = sleeve top line (x = 0), inner edge = front
       underarm / armhole fold (x = +-W(y)); along the sleeve by normalised arc length (shoulder point -> cuff seam);
       across with a cylinder unwrap (u -> 0.5 + asin(2u-1)/pi). Same method as red-beast-hoodie/mockmap.py."""
import math
import numpy as np
from PIL import Image

CFX, NECKY = 738.0, 368.0
HEMY = 1308.0                                  # hem edge (bottom of the navy binding)
S = 0.601                                      # mm/px: (HEMY - NECKY) px = A - K = 565 mm at M (fleece block)
def P(px, py): return ((np.asarray(px) - CFX) * S, (np.asarray(py) - NECKY) * S)
def Pinv(x, y): return (np.asarray(x) / S + CFX, np.asarray(y) / S + NECKY)

_IM = {}
def img(name="front"):
    if name not in _IM: _IM[name] = np.array(Image.open(f"inputs/{name}.png").convert("RGB")).astype(np.float32)
    return _IM[name]

def sample(px, py, order=1, name="front"):
    from scipy.ndimage import map_coordinates
    a = img(name); out = np.zeros(np.shape(px) + (3,), np.float32)
    for c in range(3): out[..., c] = map_coordinates(a[..., c], [py, px], order=order, mode="nearest")
    return out.clip(0, 255)

# ---------------------------------------------------------------- sleeves (front.png px), read off the render
# outer = silhouette against the white background (measured per row); inner = the armhole / sleeve fold line next to the
# body (dark seam line, x ~ 367 -> 345). Shoulder point = top of the armhole seam. Cuff seam = top of the navy binding.
SLV = {
 "R": dict(outer=[(355, 335), (311, 370), (258, 470), (211, 570), (166, 670), (130, 770), (95, 870), (66, 970), (40, 1070),
                  (19, 1170), (10, 1260), (22, 1325)],
           inner=[(355, 335), (367, 400), (362, 520), (352, 640), (346, 760), (346, 900), (344, 1040), (340, 1180), (334, 1290), (326, 1352)]),
 "L": dict(outer=[(1124, 320), (1156, 370), (1213, 470), (1267, 570), (1312, 670), (1354, 770), (1390, 870), (1426, 970), (1455, 1070),
                  (1478, 1170), (1487, 1260), (1474, 1325)],
           inner=[(1124, 320), (1112, 400), (1116, 520), (1126, 640), (1131, 760), (1131, 900), (1133, 1040), (1137, 1180), (1143, 1290), (1150, 1352)]),
}
def _arc(pts):
    pts = np.asarray(pts, float); d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]; return pts, d / d[-1]
def _at(pts, t):
    p, s = _arc(pts); t = np.clip(t, 0, 1)
    return np.stack([np.interp(t, s, p[:, 0]), np.interp(t, s, p[:, 1])], -1)

def sleeve_poly(side):
    from shapely.geometry import Polygon
    d = SLV[side]; return Polygon(d["inner"] + d["outer"][::-1]).buffer(0)

def unwrap(u): return 0.5 + np.arcsin(np.clip(2 * u - 1, -1, 1)) / math.pi
def wrap(v): return (np.sin(math.pi * (np.clip(v, 0, 1) - 0.5)) + 1) / 2

def sleeve_to_img(side, x, y, mt):
    """sleeve pattern mm (S01 for 'R', S02 for 'L'; front half = +x on S01, -x on S02) -> front.png px + visible mask.
    Back half points are folded onto the front half (|x|): the hidden back half repeats the front (PROPOSED)."""
    h, Lu, W, Ww = mt["cap_h"], mt["Lu"], mt["W"], mt["Ww"]
    ax = np.abs(np.asarray(x, float)); y = np.asarray(y, float)
    u = np.full_like(y, 0.5)
    for _ in range(12):
        t = (y + h * (1 - u)) / (h + Lu - u * h)
        yy = np.clip(t * Lu, 0, Lu); Wy = W + (Ww - W) * yy / Lu
        u = wrap(np.clip(ax / Wy, 0, 1))
    t = (y + h * (1 - u)) / (h + Lu - u * h)
    d = SLV[side]; O = _at(d["outer"], t); I = _at(d["inner"], t)
    p = (1 - u)[..., None] * O + u[..., None] * I
    front = np.sign(np.asarray(x, float)) == (1.0 if side == "R" else -1.0)
    return p[..., 0], p[..., 1], front

def visible_body():
    """front body region visible in the render (between the sleeves, below the collar), front.png px polygon"""
    from shapely.geometry import Polygon
    R, L = SLV["R"]["inner"], SLV["L"]["inner"]
    return Polygon(R + [(380, 1308), (1100, 1308)] + L[::-1] + [(900, 300), (580, 300)]).buffer(0)
