"""Detect the white star speckles on the mockup -> out/ref/specks.json [{x, y, w, h, A}] (mockup px).
Local contrast (pixel vs its 11 px median) > 80, lum > 130, low saturation, compact (<= 10 px, aspect <= 3).
Excluded: zip, welt edges, silhouette edge, side seams (garment construction lines that glint in the render).
Badge zones are excluded later in scene.py."""
import numpy as np, json, os
from PIL import Image
from scipy import ndimage as ndi
from shapely.geometry import Point, LineString
im = np.array(Image.open("inputs/flat.png").convert("RGB")).astype(float)
mx, mn, lum = im.max(2), im.min(2), im.mean(2)
sil = ndi.binary_fill_holes(ndi.binary_opening(mn < 235, iterations=2))
edge = sil & ~ndi.binary_erosion(sil, iterations=7)
med = ndi.median_filter(lum, size=11)
w = (lum - med > 80) & (lum > 130) & (mx - mn < 70) & sil & ~edge
lab, n = ndi.label(w, structure=np.ones((3, 3)))
LINES = [LineString([(300, 765), (232, 910)]).buffer(24), LineString([(790, 740), (858, 885)]).buffer(24),
         LineString([(555, 300), (555, 1100)]).buffer(14), LineString([(226, 560), (226, 1090)]).buffer(6), LineString([(887, 560), (887, 1090)]).buffer(6),
         LineString([(150, 1040), (960, 1040)]).buffer(5)]
out = []
for i, sl in enumerate(ndi.find_objects(lab), 1):
    h = sl[0].stop - sl[0].start; wd = sl[1].stop - sl[1].start; A = int((lab[sl] == i).sum())
    if A > 60 or max(h, wd) > 10: continue
    if max(h, wd) / max(1, min(h, wd)) > 3 and A > 4: continue
    x = (sl[1].start + sl[1].stop) / 2; y = (sl[0].start + sl[0].stop) / 2
    if any(L.contains(Point(x, y)) for L in LINES): continue
    out.append(dict(x=float(x), y=float(y), w=int(wd), h=int(h), A=A))
os.makedirs("out/ref", exist_ok=True); json.dump(out, open("out/ref/specks.json", "w"))
print(len(out), "specks")
