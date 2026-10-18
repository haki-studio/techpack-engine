"""Close-up registration (LESSONS A12): inputs/closeup_mockup_comet.png is the right half of the founder's mockup image, a
detail view (~2x) of the comet, clouds, city, figure and lamp. It is re-composed, not an exact zoom (no zip; the city and figure
are much larger), so only its SKY part (comet, clouds, stars, falling star) is registered onto the fronts:
  base = projective fit on all matched features, refined by a thin-plate spline through the sky features, so the matched
  features land exactly on their mockup positions (placement stays the mockup's) and the close-up detail fills in between.
The close-up's city part is a style reference only (tones, window grids, neon, figure + lamp silhouette).
API: cu_warp(bbox, ppm) -> RGB image in front garment mm (NaN-free; outside the registered area = None mask), cu_mask(bbox, ppm)."""
import numpy as np
from PIL import Image
from scipy.interpolate import RBFInterpolator
from scipy.ndimage import map_coordinates
from skimage.transform import ProjectiveTransform
import mockmap as MM

CU = "inputs/closeup_mockup_comet.png"
# matched features: close-up px -> mockup (front.png) px
PAIRS = {
    "comet tail tip": ((605, 72), (573, 321)),
    "comet head tip": ((55, 660), (302, 621)),
    "comet enters cloud": ((330, 280), (390, 492)),
    "comet leaves cloud": ((240, 365), (356, 527)),
    "falling star": ((257, 562), (403.5, 597.5)),
    "lilac star": ((611, 292), (565, 405)),
    "big white star": ((596, 510), (565, 459)),
    "figure head": ((270, 937), (414.7, 682.5)),
    "lamp head": ((612, 787), (585, 598)),
}
SKY = [k for k in PAIRS if k not in ("figure head", "lamp head")]
SKY_Y_MAX = 700.0           # close-up rows below this are city (style reference only)

_im = None
def img():
    global _im
    if _im is None: _im = np.array(Image.open(CU).convert("RGB")).astype(np.float32)
    return _im

def _fit():
    src = np.array([PAIRS[k][0] for k in PAIRS], float); dst = np.array([PAIRS[k][1] for k in PAIRS], float)
    H = ProjectiveTransform(); H.estimate(dst, src)                  # mockup px -> close-up px
    m = np.array([PAIRS[k][1] for k in SKY], float); c = np.array([PAIRS[k][0] for k in SKY], float)
    resid = c - H(m)                                                  # TPS on the residual: exact at the sky features
    rbf = RBFInterpolator(m, resid, kernel="thin_plate_spline", smoothing=0.0)
    return H, rbf
H, RBF = _fit()

def mock_to_cu(px, py):
    p = np.c_[np.ravel(px), np.ravel(py)]
    q = H(p) + RBF(p)
    return q[:, 0].reshape(np.shape(px)), q[:, 1].reshape(np.shape(px))

def residuals():
    out = {}
    for k, (c, m) in PAIRS.items():
        q = np.array(mock_to_cu(np.array([m[0]]), np.array([m[1]]))).ravel()
        out[k] = float(np.hypot(*(q - np.array(c))))
    return out

def cu_warp(bbox, ppm):
    """close-up resampled into front garment mm; mask = registered sky part of the close-up"""
    x0, y0, x1, y1 = bbox; W, Hh = int((x1 - x0) * ppm), int((y1 - y0) * ppm)
    xs = x0 + (np.arange(W) + 0.5) / ppm; ys = y0 + (np.arange(Hh) + 0.5) / ppm
    XX, YY = np.meshgrid(xs, ys); px, py = MM.Pinv(XX, YY)
    cx, cy = mock_to_cu(px, py)
    a = img(); out = np.zeros((Hh, W, 3), np.float32)
    for k in range(3): out[..., k] = map_coordinates(a[..., k], [cy, cx], order=3, mode="nearest")
    mask = (cx >= 2) & (cx < a.shape[1] - 2) & (cy >= 2) & (cy < SKY_Y_MAX)
    # reject where the warp folds or stretches (local scale vs the projective base differs by > 35 %)
    gx = np.gradient(cx, axis=1); gy = np.gradient(cy, axis=0); gxy = np.gradient(cx, axis=0); gyx = np.gradient(cy, axis=1)
    J = gx * gy - gxy * gyx; med = np.median(J[mask]) if mask.any() else 1.0
    mask &= (J > 0.65 * med) & (J < 1.5 * med)
    return out.clip(0, 255), mask

if __name__ == "__main__":
    print({k: round(v, 1) for k, v in residuals().items()})
