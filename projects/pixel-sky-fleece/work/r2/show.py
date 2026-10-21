import pickle, sys, numpy as np
from PIL import Image, ImageDraw
import mockmap as MM
a = Image.open("inputs/front.png").convert("RGB"); out = pickle.load(open(sys.argv[1], "rb"))
R = 30; Z = 6; T = 2 * R * Z
W = Image.new("RGB", (2 * T * 3, T * ((len(out) + 2) // 3)), "white")
for k, (cx, cy, g, pix) in enumerate(out):
    cx, cy = int(cx), int(cy)
    W.paste(a.crop((cx - R, cy - R, cx + R, cy + R)).resize((T, T), Image.NEAREST), ((k % 3) * 2 * T, (k // 3) * T))
    im = Image.new("RGB", (T, T), (128, 170, 240)); d = ImageDraw.Draw(im)
    ox, oy = MM.P(cx - R, cy - R); s = Z / MM.S
    for q in (g.geoms if g.geom_type == "MultiPolygon" else [g]):
        d.polygon([((x - ox) * s, (y - oy) * s) for x, y in q.exterior.coords], fill=(245, 220, 60), outline=(0, 0, 0))
    W.paste(im, ((k % 3) * 2 * T + T, (k // 3) * T))
W.save(sys.argv[2])
