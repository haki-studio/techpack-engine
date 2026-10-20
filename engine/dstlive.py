"""'Live view' render of a written DST (like Hatch's 3D view): every stitch drawn as a thread of real width with a
sheen that depends on its angle to the light, on the shell colour. Shows stitch DIRECTION the way a person reads a
sew-out, so chaotic angles and fans are visible at a glance (LESSONS A16). Reads only the DST + its thread colours.

  img = dstlive.render(dst_path, colours=["#3f6fa9", ...], ppm=8, shell="#232b3d")
"""
import math
import numpy as np
import pyembroidery as pe
from PIL import Image, ImageDraw, ImageFilter

def _rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def _shade(c, k):
    return tuple(int(max(0, min(255, v + (255 - v) * k if k >= 0 else v * (1 + k)))) for v in c)

def _off(p, q, W, H, m):
    """both ends beyond the same side of the canvas (+ margin m): the stitch cannot touch it"""
    return (p[0] < -m and q[0] < -m) or (p[1] < -m and q[1] < -m) or (p[0] > W + m and q[0] > W + m) or (p[1] > H + m and q[1] > H + m)

def render(dst, colours=None, ppm=8.0, shell="#232b3d", thread_mm=0.42, light_deg=135.0, pad_mm=3.0, bounds=None, origin=(0.0, 0.0)):
    """colours: one hex per colour stop (thread chart order); default greys. Returns a PIL RGB image.
    bounds=(x0, y0, x1, y1) mm (with origin added to the DST coords, e.g. garment mm) renders only that crop, image
    pixel (0, 0) = (x0, y0); default: the whole file plus pad_mm."""
    p = pe.read(dst)
    pts = [(x / 10.0 + origin[0], y / 10.0 + origin[1], c & pe.COMMAND_MASK) for x, y, c in p.stitches]
    if bounds is not None:
        x0, y0 = bounds[0], bounds[1]
        W, H = int(round((bounds[2] - x0) * ppm)), int(round((bounds[3] - y0) * ppm))
    else:
        xs = [a for a, _, k in pts if k == pe.STITCH]; ys = [b for _, b, k in pts if k == pe.STITCH]
        x0, y0 = min(xs) - pad_mm, min(ys) - pad_mm
        W, H = int((max(xs) - x0 + pad_mm) * ppm) + 1, int((max(ys) - y0 + pad_mm) * ppm) + 1
    S = 2                                                     # supersample
    im = Image.new("RGB", (W * S, H * S), _rgb(shell)); d = ImageDraw.Draw(im)
    tw = max(1, int(round(thread_mm * ppm * S)))
    stop, prev = 0, None
    cols = [_rgb(c) for c in (colours or [])] or [(200, 200, 200)]
    L = math.radians(light_deg)
    for x, y, k in pts:
        if k == pe.COLOR_CHANGE: stop += 1; prev = None; continue
        if k != pe.STITCH: prev = None; continue
        q = ((x - x0) * ppm * S, (y - y0) * ppm * S)
        if prev is not None and prev != q and not (bounds is not None and _off(prev, q, W * S, H * S, 10 * ppm * S)):
            a = math.atan2(q[1] - prev[1], q[0] - prev[0])
            sheen = 0.32 * abs(math.cos(a - L)) - 0.16            # threads catch light by direction
            d.line([prev, q], fill=_shade(cols[stop % len(cols)], sheen), width=tw)
        prev = q
    im = im.filter(ImageFilter.GaussianBlur(0.35 * S)).resize((W, H), Image.LANCZOS)
    return im
