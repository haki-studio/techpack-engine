"""Fidelity sheets: out/compare_<element>.png = mockup crop (Lanczos x4 from the source, mapped at the badge's motif
scale S about its anchor) | stitch render of the size-M art at the same scale, + zoomed pairs; out/compare_front_M.png
(both fronts, mockup mapped to size-M mm) and out/compare_sleeves.png.  usage: python3 compare.py [size]"""
import kccore, pickle, sys, json
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from shapely.geometry import box
import stitchrender as SR, mockmap as MM, front as F

size = sys.argv[1] if len(sys.argv) > 1 else "M"
D = pickle.load(open(f"art_{size}.pkl", "rb")); META = pickle.load(open("scene.pkl", "rb"))["meta"]
try: FONT = ImageFont.truetype("/home/devinubuntu/.local/share/fonts/LiberationSans-Bold.ttf", 22); FS = ImageFont.truetype("/home/devinubuntu/.local/share/fonts/LiberationSans-Regular.ttf", 17)
except Exception: FONT = FS = None

def badge_vis(el, field=False):
    P = kccore.ELEMENTS[el][2]
    return [r for r in D[P] if r["el"] == el or (field and r["el"] == "05")]

def mock_local(el, bb, ppm):
    """mockup around badge el, uniform scale S about its anchor; the badge's per-size move is applied too"""
    b = META["badges"][el]; ax_px = b["anchor_px"]; cx, cy = b["centre"]
    P = kccore.ELEMENTS[el][2]; mv = D["info"][P]["moves"].get(el, (0, 0)); mv = mv if isinstance(mv, tuple) else (0, 0)
    sh = b.get("shift", (0, 0))
    # garment mm -> mockup px: px = ax + (x - (cx + mv)) / S
    x0, y0, x1, y1 = bb; W, H = int((x1-x0)*ppm), int((y1-y0)*ppm)
    import numpy as np
    from scipy.ndimage import map_coordinates
    xs = x0 + (np.arange(W) + 0.5)/ppm; ys = y0 + (np.arange(H) + 0.5)/ppm; XX, YY = np.meshgrid(xs, ys)
    px = ax_px[0] + (XX - (cx + mv[0])) / MM.S; py = ax_px[1] + (YY - (cy + mv[1])) / MM.S
    a = MM.mock(); out = np.zeros((H, W, 3), np.float32)
    for c in range(3): out[..., c] = map_coordinates(a[..., c], [py, px], order=3, mode="nearest")
    return Image.fromarray(out.clip(0, 255).astype("uint8")).filter(ImageFilter.UnsharpMask(2, 60, 2))

ZOOM = {"01": "text + spark bars", "02": "letters + star border", "03": "dots, sparkles, glyphs", "04": "oval ring + hangul"}
def sheet(el):
    vis = badge_vis(el)
    from shapely.ops import unary_union
    u = unary_union([r["geom"] for r in vis]).bounds
    bb = (u[0] - 8, u[1] - 8, u[2] + 8, u[3] + 8); ppm = 4.0
    allv = badge_vis(el, True)
    mk = mock_local(el, bb, ppm); st = SR.render(allv, bb, ppm, base=kccore.FABRIC)
    W, H = st.size
    # 3 zooms across the badge diagonal
    zs = []
    import numpy as np
    cs = sorted([(r["geom"].centroid.x, r["geom"].centroid.y) for r in vis if not r.get("nok")])
    n_ = len(cs); h = 22
    for lo, hi in ((0, 0.25), (0.4, 0.6), (0.75, 1.0)):
        sel = cs[int(lo*n_):max(int(lo*n_) + 1, int(hi*n_))]; zx, zy = np.mean(sel, axis=0)
        zs.append((zx - h, zy - h, zx + h, zy + h))
    zw = 360; zp = zw / 44
    out = Image.new("RGB", (W*2 + 60 + zw*2 + 20, max(H + 60, 3*(zw + 50) + 40)), (255, 255, 255))
    out.paste(mk, (10, 50)); out.paste(st, (W + 30, 50)); d = ImageDraw.Draw(out)
    d.text((10, 8), f"{el} {kccore.ELEMENTS[el][0]} — MOCKUP (flat.png, motif scale {MM.S:.3f} mm/px about the badge anchor)", fill=(0, 0, 0), font=FONT)
    d.text((W + 30, 28), f"STITCH RENDER size {size} (same scale, {ppm:.0f} px/mm)", fill=(0, 0, 0), font=FS)
    x0 = W*2 + 50; y = 50
    for zb in zs:
        a = mock_local(el, zb, zp); s_ = SR.render(allv, zb, zp, base=kccore.FABRIC)
        out.paste(a, (x0, y)); out.paste(s_, (x0 + zw + 10, y))
        d.text((x0, y - 20), f"zoom x {zb[0]:.0f}..{zb[2]:.0f}, y {zb[1]:.0f}..{zb[3]:.0f} mm (mockup | render)", fill=(0, 0, 0), font=FS)
        for (X, Y) in ((10, 50), (W + 30, 50)):
            d.rectangle([X + (zb[0]-bb[0])*ppm, Y + (zb[1]-bb[1])*ppm, X + (zb[2]-bb[0])*ppm, Y + (zb[3]-bb[1])*ppm], outline=(255, 60, 60), width=2)
        y += zw + 50
    p = f"out/compare_{el}_{kccore.ELEMENTS[el][0]}.png"; out.save(p); return p

def fronts():
    bb = (-310, -100, 310, 520); ppm = 1.6
    st = SR.render(D["FR"] + D["FL"], bb, ppm, base=kccore.FABRIC); mk = MM.warp(bb, ppm)
    d_ = ImageDraw.Draw(st)
    for s_ in "RL":
        w_ = F.keep_geoms(size, s_)["welt"]; d_.polygon([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in w_.exterior.coords], fill=(40, 44, 55), outline=(120, 130, 150))
        pn = F.keep_geoms(size, s_)["panel"]; d_.line([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in pn.exterior.coords], fill=(120, 120, 120), width=1)
    d_.rectangle([(-6 - bb[0])*ppm, (0 - bb[1])*ppm, (6 - bb[0])*ppm, (510 - bb[1])*ppm], fill=(160, 125, 60))
    W, H = st.size; out = Image.new("RGB", (W*2 + 20, H + 40), (255, 255, 255)); out.paste(mk, (0, 40)); out.paste(st, (W + 20, 40))
    d = ImageDraw.Draw(out); d.text((10, 8), "MOCKUP fronts (mapped to size-M mm: x 0.902, y 0.703 mm/px)", fill=(0, 0, 0), font=FS)
    d.text((W + 30, 8), f"STITCH RENDER size {size} fronts (badges at motif scale; Drum Island panel)", fill=(0, 0, 0), font=FS)
    out.save(f"out/compare_front_{size}.png"); st.save(f"out/render_front_{size}.png")

def sleeves():
    import sleeve as SV
    ims = []
    for P in ("SR", "SL"):
        b = SV.piece(size, P).sew_poly().bounds; bb = (b[0] - 5, b[1] - 5, b[2] + 5, b[3] + 5)
        st = SR.render(D[P], bb, 1.2, base=kccore.FABRIC); d_ = ImageDraw.Draw(st)
        d_.line([((x - bb[0])*1.2, (y - bb[1])*1.2) for x, y in SV.piece(size, P).sew_poly().exterior.coords], fill=(150, 150, 150), width=2)
        ims.append(st)
    q = MM.mock(); crop = Image.fromarray(q.astype("uint8")).crop((30, 400, 1100, 1260)).resize((int(1070*0.7), int(860*0.7)))
    W = sum(i.width for i in ims) + crop.width + 60; H = max(max(i.height for i in ims), crop.height) + 40
    out = Image.new("RGB", (W, H), (255, 255, 255)); x = 10
    out.paste(crop, (x, 40)); x += crop.width + 20
    for i in ims: out.paste(i, (x, 40)); x += i.width + 20
    d = ImageDraw.Draw(out); d.text((10, 8), "MOCKUP (sleeves seen from the front)  |  STITCH RENDER right sleeve S01, left sleeve S02 (whole piece; front half toward the body side)", fill=(0, 0, 0), font=FS)
    out.save("out/compare_05_sleeves.png")

if __name__ == "__main__":
    for el in ("01", "02", "03", "04"): print(sheet(el))
    fronts(); sleeves(); print("fronts + sleeves")
