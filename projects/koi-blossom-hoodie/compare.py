"""Fidelity sheets (LESSONS A11): out/compare_01_front.png + out/compare_02_sleeves.png — the mockup mapped to each piece's
mm space next to the stitch render of the size-M art at the same scale, plus zoomed pairs (mockup Lanczos x4 from the
source | render). Red boxes on the overview = the zooms.  usage: python3 compare.py [size]"""
import kbcore, pickle, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import stitchrender as SR, mockmap as MM, front as F

size = sys.argv[1] if len(sys.argv) > 1 else "M"
D = pickle.load(open(f"art_{size}.pkl", "rb")); g, mt = F.pieces(size)
try: FONT = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 22)
except Exception: FONT = None
BB = {"FR": (-300, -60, 0, 520), "FL": (0, -60, 300, 520), "SR": (-10, -110, 260, 470), "SL": (-260, -110, 10, 470)}
ZOOMS = {"01": [("FR", (-235, 85, -150, 170), "FR big lily + leaves"), ("FR", (-175, 220, -90, 305), "FR vine leaves"),
                ("FR", (-150, 40, -65, 125), "FR koi pair + petals"), ("FL", (95, 360, 180, 445), "FL lily cluster at the hem band"),
                ("FL", (75, 210, 160, 295), "FL koi school"), ("FL", (170, 330, 255, 415), "FL dark flower + side vine")],
         "02": [("SR", (20, 60, 105, 145), "SR top koi"), ("SR", (25, 340, 110, 425), "SR koi + petals"),
                ("SR", (20, 380, 105, 465), "SR cuff flower cluster"), ("SL", (-110, 250, -25, 335), "SL long koi"),
                ("SL", (-150, 330, -65, 415), "SL koi near cuff"), ("SL", (-150, 110, -65, 195), "SL petals")]}

def outline(im, bb, ppm, P):
    d = ImageDraw.Draw(im); c = F.clip_for(size, P)
    for poly in (c.geoms if c.geom_type == "MultiPolygon" else [c]):
        d.line([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in poly.exterior.coords], fill=(255, 90, 90), width=1)
    if P in ("FR", "FL"):
        w_ = F.keep_geoms(size, P)["welt"]; d.polygon([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in w_.exterior.coords], fill=(30, 35, 52), outline=(150, 150, 170))

def pair(P, bb, ppm, mock_ppm=None):
    st = SR.render(D[P], bb, ppm, base=kbcore.FABRIC)
    mk = MM.warp_piece(P, bb, mock_ppm or ppm, mt)
    if mock_ppm: mk = mk.resize(st.size, Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
    return mk, st

def sheet(el):
    pcs = kbcore.ELEMS[el][2]; ppm = 1.6
    ov = []
    for P in pcs:
        mk, st = pair(P, BB[P], ppm); outline(st, BB[P], ppm, P); ov.append((P, mk, st))
    W0 = sum(m.width + s.width + 30 for _, m, s in ov); H0 = max(m.height for _, m, _ in ov)
    zw = 360; zs = ZOOMS[el]; cols = 3; rows = (len(zs) + cols - 1) // cols
    out = Image.new("RGB", (max(W0, cols*(2*zw + 30)) + 20, H0 + 60 + rows*(zw + 50) + 20), (255, 255, 255)); d = ImageDraw.Draw(out)
    d.text((10, 6), f"{el} {kbcore.ELEMS[el][1]} — MOCKUP (front.png mapped to size-{size} mm) | STITCH RENDER size {size}, same scale. Red line = keep-outs.", fill=(0, 0, 0), font=FONT)
    x = 10; pos = {}
    for P, mk, st in ov:
        out.paste(mk, (x, 40)); out.paste(st, (x + mk.width + 6, 40)); pos[P] = (x, x + mk.width + 6)
        d.text((x + 4, 44), f"{P} mockup", fill=(255, 255, 0), font=FONT); d.text((x + mk.width + 10, 44), f"{P} size {size}", fill=(255, 255, 0), font=FONT)
        x += mk.width + st.width + 30
    y0 = H0 + 60
    for k, (P, zb, cap) in enumerate(zs):
        zp = zw / (zb[2] - zb[0]); mk, st = pair(P, zb, zp, mock_ppm=zp/4)
        cx = 10 + (k % cols)*(2*zw + 30); cy = y0 + (k // cols)*(zw + 50)
        out.paste(mk, (cx, cy + 26)); out.paste(st, (cx + zw + 6, cy + 26))
        d.text((cx, cy + 2), f"{k+1}. {cap}  (mockup x4 | render)", fill=(0, 0, 0), font=FONT)
        bb = BB[P]
        for X in pos[P]:
            d.rectangle([X + (zb[0]-bb[0])*ppm, 40 + (zb[1]-bb[1])*ppm, X + (zb[2]-bb[0])*ppm, 40 + (zb[3]-bb[1])*ppm], outline=(255, 40, 40), width=2)
            d.text((X + (zb[0]-bb[0])*ppm + 3, 40 + (zb[1]-bb[1])*ppm + 2), str(k+1), fill=(255, 40, 40), font=FONT)
    out.save(f"out/compare_{el}_{kbcore.ELEMS[el][0]}.png"); return out.size

if __name__ == "__main__":
    for el in kbcore.ELEMS: print(el, sheet(el))
