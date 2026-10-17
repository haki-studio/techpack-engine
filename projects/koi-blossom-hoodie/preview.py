"""Quick look: mockup (mapped to each piece's mm) | scene render, keep-out clip outline in red.  usage: python3 preview.py [size]"""
import kbcore, pickle, sys
from PIL import Image, ImageDraw
import stitchrender as SR, mockmap as MM, front as F, kbvis
size = sys.argv[1] if len(sys.argv) > 1 else "M"
src = sys.argv[2] if len(sys.argv) > 2 else "scene"
g, mt = F.pieces(size)
if src == "scene": D = pickle.load(open("scene.pkl", "rb"))["items"]; D = {P: kbvis.visible(v) for P, v in D.items()}
else: D = pickle.load(open(f"art_{size}.pkl", "rb"))
BB = {"FR": (-300, -60, 0, 520), "FL": (0, -60, 300, 520), "SR": (-20, -110, 270, 470), "SL": (-270, -110, 20, 470)}
ppm = 2.0; tiles = []
for P in kbcore.PIECES:
    bb = BB[P]; mk = MM.warp_piece(P, bb, ppm, mt); st = SR.render(D[P], bb, ppm, base=kbcore.FABRIC)
    for im in (mk, st):
        d = ImageDraw.Draw(im); c = F.clip_for(size, P)
        for poly in (c.geoms if c.geom_type == "MultiPolygon" else [c]):
            d.line([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in poly.exterior.coords], fill=(255, 60, 60), width=1)
        pc = g[F.CODE[P]].sew_poly()
        d.line([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in pc.exterior.coords], fill=(200, 200, 200), width=1)
    tiles.append((mk, st))
W = sum(a.width*2 + 20 for a, _ in tiles); H = max(a.height for a, _ in tiles)
out = Image.new("RGB", (W, H), (255, 255, 255)); x = 0
for a, b in tiles: out.paste(a, (x, 0)); out.paste(b, (x + a.width, 0)); x += a.width*2 + 20
out.save(f"out/preview_{src}_{size}.png"); print(out.size)
