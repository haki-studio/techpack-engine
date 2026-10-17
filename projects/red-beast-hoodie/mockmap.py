"""Mockup <-> garment mm.

Sources (inputs/flat.png is one 1448 x 1086 image): front.png = its left half (whole jacket, ~1.15 mm/px),
closeup_mockup_head.png = its right half (angled detail render of the head, ~2.6x more pixels on the head).

FRONT  front.png -> front garment mm, ISOTROPIC (the art must not stretch): CF zip x = 366 px, CF neck seam y = 306 px,
       S = 1.15 mm/px (puts the beast's nose 22 mm inside the block side seam, as in the render; the render body is
       narrower and longer than the Drum Island block, so one scale cannot match both — PROPOSED).
CLOSE  closeup -> front.png: projective fit of SIFT matches on red/cream feature images (register(); inliers + residual
       saved in inputs/closeup_reg.json). Used inside the head only; the mockup stays the reference for placement.
SLEEVE front.png sleeve patch -> sleeve pattern coords (S01/S02): the visible half of a hanging sleeve is its FRONT half;
       outer silhouette = sleeve top line (x = 0), inner edge = front underarm seam (x = +-W(y)); along the sleeve by
       normalised arc length (shoulder point -> cuff seam); across with a cylinder unwrap (u -> 0.5 + asin(2u-1)/pi)."""
import json, math, os
import numpy as np
from PIL import Image

CFX, NECKY, S = 366.0, 306.0, 1.15
def P(px, py): return ((px - CFX) * S, (py - NECKY) * S)
def Pinv(x, y): return (np.asarray(x) / S + CFX, np.asarray(y) / S + NECKY)

_IM = {}
def img(name):
    if name not in _IM: _IM[name] = np.array(Image.open(f"inputs/{name}.png").convert("RGB")).astype(np.float32)
    return _IM[name]

def sample(name, px, py, order=3):
    """RGB of image `name` at float pixel coords (arrays), bicubic"""
    from scipy.ndimage import map_coordinates
    a = img(name); out = np.zeros(px.shape + (3,), np.float32)
    for c in range(3): out[..., c] = map_coordinates(a[..., c], [py, px], order=order, mode="nearest")
    return out.clip(0, 255)

# ---------------------------------------------------------------- close-up registration
CROP, CK = (360, 300, 640, 700), 2.6         # front.png crop + upscale the homography was fitted in
def register():
    from skimage.feature import SIFT, match_descriptors
    from skimage.measure import ransac
    from skimage.transform import ProjectiveTransform
    im = Image.open("inputs/front.png").convert("RGB").crop(CROP)
    Ac = np.array(im.resize((int((CROP[2]-CROP[0])*CK), int((CROP[3]-CROP[1])*CK)), Image.LANCZOS)).astype(float) / 255
    B = img("closeup_mockup_head") / 255
    def feat(a):
        r, g, b = a[..., 0], a[..., 1], a[..., 2]
        red = np.clip((r - g)*2, 0, 1); cream = np.clip((a.mean(2) - 0.45)*2, 0, 1) * (1 - np.clip((r - b)*3, 0, 1))
        return 0.5*red + cream
    d1 = SIFT(); d1.detect_and_extract(feat(Ac)); d2 = SIFT(); d2.detect_and_extract(feat(B))
    m = match_descriptors(d2.descriptors, d1.descriptors, max_ratio=0.8, cross_check=True)
    src = d2.keypoints[m[:, 0]][:, ::-1]; dst = d1.keypoints[m[:, 1]][:, ::-1]
    model, inl = ransac((src, dst), ProjectiveTransform, min_samples=4, residual_threshold=6, max_trials=5000, rng=1)
    res = np.linalg.norm(model(src[inl]) - dst[inl], axis=1) / CK * S          # residual in garment mm
    np.save("inputs/closeup_H.npy", model.params)
    info = dict(matches=int(len(m)), inliers=int(inl.sum()), resid_mm_median=float(np.median(res)), resid_mm_p90=float(np.percentile(res, 90)))
    json.dump(info, open("inputs/closeup_reg.json", "w"), indent=1)
    return info

_H = None
def close_px(fx, fy):
    """front.png px -> close-up px"""
    global _H
    if _H is None: _H = np.linalg.inv(np.load("inputs/closeup_H.npy"))
    ax, ay = (np.asarray(fx) - CROP[0]) * CK, (np.asarray(fy) - CROP[1]) * CK
    w = _H[2, 0]*ax + _H[2, 1]*ay + _H[2, 2]
    return (_H[0, 0]*ax + _H[0, 1]*ay + _H[0, 2]) / w, (_H[1, 0]*ax + _H[1, 1]*ay + _H[1, 2]) / w

# ---------------------------------------------------------------- sleeves (front.png px)
# outer = silhouette against the white background (measured per row), shoulder point -> cuff seam;
# inner = front underarm seam (sleeve/body boundary, read off the render), underarm -> cuff seam. Cuff seam y = 895.
SLV = {
 "R": dict(outer=[(83, 388), (68, 420), (45, 480), (24, 560), (10, 650), (6, 750), (8, 820), (12, 880), (13, 895)],
           inner=[(147, 470), (136, 540), (129, 620), (129, 700), (137, 770), (148, 830), (140, 860), (130, 880), (125, 895)],
           seam=[(83, 388), (115, 396), (150, 412), (147, 470)]),
 "L": dict(outer=[(638, 390), (653, 420), (676, 480), (697, 560), (712, 650), (716, 750), (716, 820), (711, 880), (710, 895)],
           inner=[(603, 480), (606, 560), (604, 640), (596, 710), (582, 780), (568, 830), (580, 860), (590, 880), (596, 895)],
           seam=[(638, 390), (622, 410), (600, 450), (603, 480)]),
}
def _arc(pts):
    pts = np.asarray(pts, float); d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]; return pts, d / d[-1]
def _at(pts, t):
    p, s = _arc(pts); t = np.clip(t, 0, 1)
    return np.stack([np.interp(t, s, p[:, 0]), np.interp(t, s, p[:, 1])], -1)

def sleeve_poly(side):
    from shapely.geometry import Polygon
    d = SLV[side]; ring = d["seam"][:-1] + d["inner"] + d["outer"][::-1]
    return Polygon(ring).buffer(0)

def unwrap(u): return 0.5 + np.arcsin(np.clip(2*u - 1, -1, 1)) / math.pi
def wrap(v): return (np.sin(math.pi*(np.clip(v, 0, 1) - 0.5)) + 1) / 2

def sleeve_to_img(side, x, y, mt):
    """sleeve pattern mm (S01 for 'R', S02 for 'L') -> front.png px. x, y arrays."""
    h, Lu, W, Ww = mt["cap_h"], mt["Lu"], mt["W"], mt["Ww"]
    sg = 1.0 if side == "R" else -1.0
    ax = np.abs(np.asarray(x, float)) * (np.sign(x) == sg); y = np.asarray(y, float)
    u = np.full_like(y, 0.5)
    for _ in range(12):
        t = (y + h*(1 - u)) / (h + Lu - u*h)
        yy = np.clip(t*Lu, 0, Lu); Wy = W + (Ww - W)*yy/Lu
        u = wrap(np.clip(ax / Wy, 0, 1))
    t = (y + h*(1 - u)) / (h + Lu - u*h)
    d = SLV[side]; O = _at(d["outer"], t); I = _at(d["inner"], t)
    p = (1 - u)[..., None]*O + u[..., None]*I
    valid = (t >= 0) & (t <= 1) & (np.sign(x) == sg) & (ax / np.maximum(W + (Ww - W)*np.clip(t*Lu, 0, Lu)/Lu, 1) <= 1)
    return p[..., 0], p[..., 1], valid

def img_to_sleeve(side, px, py, mt, n=400):
    """front.png px -> sleeve pattern mm (via a dense forward grid + nearest lookup)"""
    from scipy.spatial import cKDTree
    h, Lu, W, Ww = mt["cap_h"], mt["Lu"], mt["W"], mt["Ww"]; sg = 1.0 if side == "R" else -1.0
    T, U = np.meshgrid(np.linspace(0, 1, n), np.linspace(0, 1, n // 2))
    d = SLV[side]; O = _at(d["outer"], T); I = _at(d["inner"], T)
    pimg = (1 - U)[..., None]*O + U[..., None]*I
    y = -h*(1 - U) + T*(h + Lu - U*h); yy = np.clip(T*Lu, 0, Lu); Wy = W + (Ww - W)*yy/Lu
    x = sg * Wy * unwrap(U)
    tree = cKDTree(pimg.reshape(-1, 2)); _, k = tree.query(np.stack([np.ravel(px), np.ravel(py)], -1))
    return x.ravel()[k].reshape(np.shape(px)), y.ravel()[k].reshape(np.shape(px))

if __name__ == "__main__":
    print(register())
