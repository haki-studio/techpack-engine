"""dev helper: mockup crop of a piece in mm coords with a 10 mm grid (labels every 20 mm). usage: gridview.py P x0 y0 x1 y1 ppm out.png [dst]"""
import cfcore, sys
import numpy as np
from PIL import Image, ImageDraw
import mockmap as MM
P = sys.argv[1]; bb = tuple(float(v) for v in sys.argv[2:6]); ppm = float(sys.argv[6]); out = sys.argv[7]
im = Image.fromarray(MM.warp(P, bb, ppm, up=4).clip(0, 255).astype(np.uint8))
if len(sys.argv) > 8:
    import compare as C
    st = C.dst_image(P, bb, ppm); W = im.width; c = Image.new("RGB", (W * 2 + 10, im.height), "white"); c.paste(im, (0, 0)); c.paste(st, (W + 10, 0)); im = c
d = ImageDraw.Draw(im)
for off in ([0] if len(sys.argv) <= 8 else [0, int((bb[2]-bb[0])*ppm) + 10]):
    for x in np.arange(np.ceil(bb[0] / 10) * 10, bb[2], 10):
        X = off + (x - bb[0]) * ppm; d.line([(X, 0), (X, im.height)], fill=(255, 255, 0) if x % 50 else (255, 0, 0), width=1)
        if x % 20 == 0: d.text((X + 2, 2), f"{x:.0f}", fill=(255, 255, 0))
    for y in np.arange(np.ceil(bb[1] / 10) * 10, bb[3], 10):
        Y = (y - bb[1]) * ppm; d.line([(off, Y), (off + (bb[2]-bb[0])*ppm, Y)], fill=(255, 255, 0) if y % 50 else (255, 0, 0), width=1)
        if y % 20 == 0: d.text((off + 2, Y + 2), f"{y:.0f}", fill=(255, 255, 0))
im.save(out); print(im.size)
