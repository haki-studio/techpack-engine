"""dev helper: the cached composite warp (warps_M.pkl) of a piece with a 10 mm grid. usage: gridwarp.py P x0 y0 x1 y1 scale out.png"""
import cfcore, sys, pickle
import numpy as np
from PIL import Image, ImageDraw
P = sys.argv[1]; bb = [float(v) for v in sys.argv[2:6]]; sc = float(sys.argv[6]); out = sys.argv[7]
W = pickle.load(open("warps_M.pkl", "rb")); b, a = W[P]; ppm = 3.0
c0, r0 = int((bb[0] - b[0]) * ppm), int((bb[1] - b[1]) * ppm); c1, r1 = int((bb[2] - b[0]) * ppm), int((bb[3] - b[1]) * ppm)
im = Image.fromarray(a[max(0, r0):r1, max(0, c0):c1].clip(0, 255).astype(np.uint8)); im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
d = ImageDraw.Draw(im); k = ppm * sc
for x in np.arange(np.ceil(bb[0] / 10) * 10, bb[2], 10):
    X = (x - bb[0]) * k; d.line([(X, 0), (X, im.height)], fill=(255, 0, 0) if x % 50 == 0 else (255, 255, 0), width=1)
    if x % 20 == 0: d.text((X + 2, 2), f"{x:.0f}", fill=(255, 255, 0))
for y in np.arange(np.ceil(bb[1] / 10) * 10, bb[3], 10):
    Y = (y - bb[1]) * k; d.line([(0, Y), (im.width, Y)], fill=(255, 0, 0) if y % 50 == 0 else (255, 255, 0), width=1)
    if y % 20 == 0: d.text((2, Y + 2), f"{y:.0f}", fill=(255, 255, 0))
im.save(out); print(im.size)
