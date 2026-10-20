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

def render(dst, colours=None, ppm=8.0, shell="#232b3d", thread_mm=0.42, light_deg=135.0, pad_mm=3.0):
    """colours: one hex per colour stop (thread chart order); default greys. Returns a PIL RGB image."""
    p = pe.read(dst)
    pts = [(x / 10.0, y / 10.0, c & pe.COMMAND_MASK) for x, y, c in p.stitches]
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
        if prev is not None and prev != q:
            a = math.atan2(q[1] - prev[1], q[0] - prev[0])
            sheen = 0.32 * abs(math.cos(a - L)) - 0.16            # threads catch light by direction
            d.line([prev, q], fill=_shade(cols[stop % len(cols)], sheen), width=tw)
        prev = q
    im = im.filter(ImageFilter.GaussianBlur(0.35 * S)).resize((W, H), Image.LANCZOS)
    return im
