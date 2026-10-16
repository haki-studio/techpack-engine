"""Measure embroidery stitchability of outlined lettering at real size.
too_thin  = ink narrower than MIN_STROKE (satin column can't hold / disappears)
gap_fill  = background gaps narrower than MIN_GAP (threads spread and close it)"""
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

PXMM = 40                      # raster resolution
MIN_STROKE, MIN_GAP = 0.8, 0.5 # mm, typical shop minimums for 40wt thread

def disk(d_mm):
    r = d_mm * PXMM / 2
    n = int(np.ceil(r))
    y, x = np.ogrid[-n:n + 1, -n:n + 1]
    return x * x + y * y <= r * r

def raster(text, font_path, glyph_h_mm):
    """render so the tallest ink box of the string = glyph_h_mm"""
    probe = ImageFont.truetype(font_path, 400)
    l, t, r, b = probe.getbbox(text)
    size = int(400 * glyph_h_mm * PXMM / (b - t))
    F = ImageFont.truetype(font_path, size)
    l, t, r, b = F.getbbox(text)
    pad = 20
    im = Image.new("L", (r - l + 2 * pad, b - t + 2 * pad), 0)
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=F, fill=255)
    return np.array(im) > 127

def check(text, font_path, h):
    ink = raster(text, font_path, h)
    opened = ndi.binary_opening(ink, structure=disk(MIN_STROKE))
    thin = ink & ~opened
    closed = ndi.binary_closing(ink, structure=disk(MIN_GAP), border_value=0)
    gaps = closed & ~ink
    # stroke width: 2x distance transform along medial pixels
    dt = ndi.distance_transform_edt(ink)
    sk = (dt >= ndi.maximum_filter(dt, size=3)) & (dt > 2)
    widths = 2 * dt[sk] / PXMM
    a = ink.sum()
    return dict(thin_pct=100 * thin.sum() / a, gap_pct=100 * gaps.sum() / a,
                stroke_p10=np.percentile(widths, 10), stroke_med=np.median(widths)), ink, thin, gaps

if __name__ == "__main__":
    import sys
    YUSEI = "YuseiMagic-Regular.ttf"
    # element heights as a share of field height, measured from image 2
    elems = [("元気でね", 0.165), ("また会おうね", 0.165), ("ちひろ", 0.127), ("理砂", 0.170)]
    for W in (80, 85, 90, 95):
        H = W / 1.48
        fh = H - 13.0
        print(f"\n== patch {W} x {H:.1f} mm  (field height {fh:.1f})")
        for txt, k in elems:
            h = k * fh
            m, *_ = check(txt, YUSEI, h)
            flag = "OK " if m["thin_pct"] < 1.5 and m["gap_pct"] < 1.5 else "FAIL"
            print(f"  {flag} {txt:<6} h={h:4.1f}mm  stroke p10={m['stroke_p10']:.2f} med={m['stroke_med']:.2f}  "
                  f"too-thin={m['thin_pct']:4.1f}%  closing-gaps={m['gap_pct']:4.1f}%")
