"""Mockup (inputs/flat.png, 1122 x 1402) <-> garment mm (size M, Drum Island block).
Landmarks read on the mockup: CF zip x = 555 px, CF neck seam (zip top) y = 315 px, side seams x = 555 -/+ 332 px
(= 1/2 chest 299.5 mm), hem-band seam y = 1040 px (= front length 510 mm). The AI render is a longer jacket than the
boxy Drum Island block, so x and y scale differently (SX 0.90, SY 0.70 mm/px). Positions use SX/SY; motif SIZES use
S (the mean), so round things stay round."""
import numpy as np
from PIL import Image

CFX, NECKY = 555.0, 315.0
SX, SY = 299.5 / 332.0, 510.0 / 725.0
S = (SX + SY) / 2

def P(px, py): return ((px - CFX) * SX, (py - NECKY) * SY)
def Pinv(x, y): return (x / SX + CFX, y / SY + NECKY)

_IM = None
def mock():
    global _IM
    if _IM is None: _IM = np.array(Image.open("inputs/flat.png").convert("RGB")).astype(np.float32)
    return _IM

def warp(bbox, ppm, sx=None, sy=None, centre=None):
    """mockup resampled into garment mm space (bbox x0,y0,x1,y1 at ppm px/mm). With sx/sy/centre the mapping is
    uniform about `centre` (a mockup px point mapped to its P() position): used for motif-scale comparisons."""
    x0, y0, x1, y1 = bbox; W, H = int((x1-x0)*ppm), int((y1-y0)*ppm)
    xs = x0 + (np.arange(W) + 0.5) / ppm; ys = y0 + (np.arange(H) + 0.5) / ppm
    XX, YY = np.meshgrid(xs, ys)
    if centre is None: px, py = Pinv(XX, YY)
    else:
        cx, cy = P(*centre); px = centre[0] + (XX - cx) / (sx or S); py = centre[1] + (YY - cy) / (sy or S)
    a = mock(); out = np.zeros((H, W, 3), np.float32)
    from scipy.ndimage import map_coordinates
    for c in range(3): out[..., c] = map_coordinates(a[..., c], [py, px], order=1, mode="nearest")
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))
