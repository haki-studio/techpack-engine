import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from shapely.geometry import Polygon
import wb
PX = 40
def rast(g):
    minx, miny, maxx, maxy = g.bounds
    w, h = int((maxx-minx)*PX)+40, int((maxy-miny)*PX)+40
    im = Image.new("L", (w, h), 0); d = ImageDraw.Draw(im)
    polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
    for p in polys:
        T = lambda cs: [((x-minx)*PX+20, (y-miny)*PX+20) for x, y in cs]
        d.polygon(T(p.exterior.coords), fill=255)
        for r in p.interiors: d.polygon(T(r.coords), fill=0)
    return np.array(im) > 127
def disk(mm):
    r = mm*PX/2; n = int(np.ceil(r)); y, x = np.ogrid[-n:n+1, -n:n+1]; return x*x+y*y <= r*r
def qa(name, g, min_stroke=0.8, min_gap=0.5, min_counter=0.6):
    ink = rast(g)
    thin = ink & ~ndi.binary_opening(ink, structure=disk(min_stroke))
    bg = ~ink; lab, n = ndi.label(bg)
    border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    bdt = ndi.distance_transform_edt(bg)
    holes = sorted(round(2*bdt[lab == i].max()/PX, 2) for i in range(1, n+1) if i not in border)
    nb = ndi.label(ink)[1]; na = ndi.label(ndi.binary_closing(ink, structure=disk(min_gap)) | ink)[1]
    thin_pct = 100*thin.sum()/ink.sum()
    small = [h for h in holes if h < min_counter]
    ok = thin_pct < 1.0 and not small and nb == na
    print(f"{'PASS' if ok else 'CHECK'}  {name:<16} thin<{min_stroke}: {thin_pct:4.1f}%  counters {len(holes)} (smallest {holes[:3]})  "
          f"shapes {nb}->{na} under {min_gap}mm")
    return ink, thin
if __name__ == "__main__":
  L = wb.compose()
  for k in ["line1", "line2", "chihiro", "risa", "face", "hearts", "frame", "pink_flowers", "flower_centres", "dots"]:
    ms = 0.6 if k == "face" else 0.8
    qa(k, L[k], min_stroke=ms)
