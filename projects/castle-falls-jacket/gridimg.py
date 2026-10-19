"""dev helper: image crop with a labelled px grid. usage: gridimg.py img x0 y0 x1 y1 step scale out.png"""
import sys
from PIL import Image, ImageDraw
f, x0, y0, x1, y1, st, sc, out = sys.argv[1], *map(int, sys.argv[2:7]), float(sys.argv[7]), sys.argv[8]
im = Image.open(f).convert("RGB").crop((x0, y0, x1, y1)); im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
d = ImageDraw.Draw(im)
for x in range((x0 // st + 1) * st, x1, st):
    X = (x - x0) * sc; d.line([(X, 0), (X, im.height)], fill=(255, 255, 0), width=1); d.text((X + 2, 2), str(x), fill=(255, 255, 0))
for y in range((y0 // st + 1) * st, y1, st):
    Y = (y - y0) * sc; d.line([(0, Y), (im.width, Y)], fill=(255, 255, 0), width=1); d.text((2, Y + 2), str(y), fill=(255, 255, 0))
im.save(out)
