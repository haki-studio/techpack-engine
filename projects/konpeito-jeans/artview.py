"""quick flat render of region art next to the rectified mockup (for the trace loop)."""
import sys, pickle
from PIL import Image, ImageDraw
import kjcore, motifs2
def draw(vis, bbox, ppm=20, bg=(40, 40, 44), outline=False):
    x0, y0, x1, y1 = bbox
    im = Image.new("RGB", (int((x1-x0)*ppm), int((y1-y0)*ppm)), bg); d = ImageDraw.Draw(im)
    T = lambda cs: [((x-x0)*ppm, (y-y0)*ppm) for x, y in cs]
    for r in vis:
        col = motifs2.HEX[r["col"]]
        m = Image.new("L", im.size, 0); dm = ImageDraw.Draw(m)
        for p in getattr(r["geom"], "geoms", [r["geom"]]):
            if p.geom_type != "Polygon" or p.is_empty: continue
            dm.polygon(T(p.exterior.coords), fill=255)
            for q in p.interiors: dm.polygon(T(q.coords), fill=0)
        im.paste(Image.new("RGB", im.size, col), (0, 0), m)
        if outline:
            for p in getattr(r["geom"], "geoms", [r["geom"]]):
                if p.geom_type == "Polygon" and not p.is_empty: d.line(T(p.exterior.coords), fill=(0, 0, 0), width=1)
    return im
if __name__ == "__main__":
    A = pickle.load(open("out/art.pkl", "rb"))
    for k, bb, ref in (("coin", (0, 0, 76, 56), "coin"), ("wb", (0, 0, 80, 54), "wb"), ("spill", (0, -16, 76, 6), None)):
        a = draw(A[k]["vis"], bb, outline=True)
        if ref:
            m = Image.open(f"out/trace/{ref}_rect.png").convert("RGB")
            c = Image.new("RGB", (a.width*2 + 10, a.height), "white"); c.paste(m, (0, 0)); c.paste(a, (a.width + 10, 0))
        else: c = a
        c.save(f"out/trace/art_{k}.png")
