"""Mockup (inputs/front.png, 720x870) <-> garment mm (size M).
Landmarks: CF zip x = 375 px, CF neck seam y = 170 px, side seams x = 375 -/+ 248 px (= 1/2 chest 299.5 mm),
hem-rib seam y = 672 px (= 510 mm). The render is narrower than the boxy block, so x and y scale differently;
motif SIZES use the mean scale S (motifs stay round)."""
import numpy as np
from PIL import Image

CFX, NECKY = 375.0, 170.0
SX, SY = 299.5 / 248.0, 510.0 / 502.0
S = (SX + SY) / 2

def P(px, py): return ((px - CFX) * SX, (py - NECKY) * SY)
def Pinv(x, y): return (x / SX + CFX, y / SY + NECKY)

_IM = None
def mock():
    global _IM
    if _IM is None: _IM = np.array(Image.open("inputs/front.png").convert("RGB")).astype(np.float32)
    return _IM

def sample(x, y):
    """mockup RGB at garment mm (bilinear)."""
    im = mock(); px, py = Pinv(x, y)
    x0, y0 = int(np.floor(px)), int(np.floor(py)); fx, fy = px - x0, py - y0
    x0 = min(max(x0, 0), im.shape[1] - 2); y0 = min(max(y0, 0), im.shape[0] - 2)
    a = im[y0, x0]*(1-fx)*(1-fy) + im[y0, x0+1]*fx*(1-fy) + im[y0+1, x0]*(1-fx)*fy + im[y0+1, x0+1]*fx*fy
    return a

def warp(bbox, ppm):
    """mockup resampled into garment mm space: image covering bbox (x0,y0,x1,y1) at ppm px/mm."""
    x0, y0, x1, y1 = bbox; W, H = int((x1-x0)*ppm), int((y1-y0)*ppm)
    xs = x0 + (np.arange(W) + 0.5) / ppm; ys = y0 + (np.arange(H) + 0.5) / ppm
    XX, YY = np.meshgrid(xs, ys); px, py = Pinv(XX, YY)
    im = Image.open("inputs/front.png").convert("RGB")
    from scipy.ndimage import map_coordinates
    a = np.array(im).astype(np.float32); out = np.zeros((H, W, 3), np.float32)
    for c in range(3): out[..., c] = map_coordinates(a[..., c], [py, px], order=1, mode="nearest")
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))
