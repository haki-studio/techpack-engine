"""Fidelity sheets from the FINAL stitch files (review Rev A item 1): nothing here is drawn from the art regions.
out/compare_<el>_<slug>.png = mockup crop (Lanczos x4 from inputs/flat.png, mapped at the badge's motif scale S about its
anchor, the badge's per-size move applied) | the written DST read back (dstview: every sewn stitch as a thread, PES colours)
at the same scale, + 4 zoomed pairs on named features. out/compare_front_<size>.png (both fronts) and
out/compare_05_sleeves.png (mockup sleeves | SR + SL DST). usage: python3 compare.py [size]"""
import kccore, pickle, sys, json, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from shapely.ops import unary_union
import mockmap as MM, front as F, dstview as DV

size = sys.argv[1] if len(sys.argv) > 1 else "M"
D = pickle.load(open(f"art_{size}.pkl", "rb")); META = pickle.load(open("scene.pkl", "rb"))["meta"]
_FD = os.path.expanduser("~/.local/share/fonts")
FONT = ImageFont.truetype(os.path.join(_FD, "LiberationSans-Bold.ttf"), 22); FS = ImageFont.truetype(os.path.join(_FD, "LiberationSans-Regular.ttf"), 17)
def base(P): return f"out/stitch/{size}/HAKI_{kccore.SHORT}_{P}_{size}"
FAB = tuple(int(kccore.FABRIC[i:i+2], 16) for i in (1, 3, 5))

def mock_local(el, bb, ppm):
    """mockup around badge el at the uniform motif scale S about its anchor (+ the badge's per-size move)"""
    from scipy.ndimage import map_coordinates
    b = META["badges"][el]; ax_px = b["anchor_px"]; cx, cy = b["centre"]
    P = kccore.ELEMENTS[el][2]; mv = D["info"][P]["moves"].get(el, (0, 0)); mv = mv if isinstance(mv, tuple) else (0, 0)
    x0, y0, x1, y1 = bb; W, H = int((x1-x0)*ppm), int((y1-y0)*ppm)
    xs = x0 + (np.arange(W) + 0.5)/ppm; ys = y0 + (np.arange(H) + 0.5)/ppm; XX, YY = np.meshgrid(xs, ys)
    px = ax_px[0] + (XX - (cx + mv[0])) / MM.S; py = ax_px[1] + (YY - (cy + mv[1])) / MM.S
    a = MM.mock(); out = np.zeros((H, W, 3), np.float32)
    for c in range(3): out[..., c] = map_coordinates(a[..., c], [py, px], order=3, mode="nearest")
    return Image.fromarray(out.clip(0, 255).astype("uint8")).filter(ImageFilter.UnsharpMask(2, 60, 2))

def zone(P, unit=None, ch=None, el=None, h=20.0, pick=None):
    rs = [r for r in D[P] if (unit is None or (r.get("unit") or "").startswith(unit)) and (ch is None or r.get("ch") == ch)
          and (el is None or r["el"] == el) and not r.get("glow")]
    if pick: rs = pick(rs)
    c = unary_union([r["geom"] for r in rs]).centroid
    return (c.x - h, c.y - h, c.x + h, c.y + h)

def top(rs):     # the topmost unit of a set (ring dot / star)
    u = min({r["unit"] for r in rs}, key=lambda u: min(r["geom"].bounds[1] for r in rs if r["unit"] == u))
    return [r for r in rs if r["unit"] == u]

ZOOMS = {
 "01": [("宇宙 + face star (puff text, rims, halo)", dict(unit="01-text", ch="宙", h=19)), ("き れ (curved baseline, bars)", dict(unit="01-text", ch="き", h=19)),
        ("top star: dark pit + white centre, bars", dict(unit="01-star1", h=15)), ("bottom red star: solid, star pit", dict(unit="01-star3", h=13))],
 "02": [("KEEP (puff, rim)", dict(unit="02-text", ch="K", h=17)), ("CLEAN (lemon, white rim)", dict(unit="02-text", ch="L", h=17)),
        ("SPACE + halo", dict(unit="02-text", ch="S", h=17)), ("faceted border stars", dict(unit="02-star5", h=12))],
 "03": [("要 (flat column satin)", dict(unit="03-text", ch="要", h=17)), ("球 地", dict(unit="03-text", ch="地", h=17)),
        ("domed ring dots + halo", dict(unit="03-dots", h=14, pick=top)), ("inner sparkles", dict(unit="03-sp", h=14))],
 "04": [("i-arrow mark + 우", dict(unit="04-orn", h=14, pick=lambda rs: [r for r in rs if r["grp"] != "DOT"])), ("깨끗", dict(unit="04-text", ch="끗", h=16)),
        ("accent tick + dot", dict(unit="04-orn", h=14, pick=lambda rs: [r for r in rs if r["grp"] == "DOT"])), ("oval ring + highlight", dict(unit="04-oval", h=14, pick=lambda rs: rs))],
}

def label(im, s, f=FS):
    out = Image.new("RGB", (im.width, im.height + 26), (255, 255, 255)); out.paste(im, (0, 26))
    ImageDraw.Draw(out).text((4, 3), s, fill=(0, 0, 0), font=f); return out

def sheet(el):
    P = kccore.ELEMENTS[el][2]
    u = unary_union([r["geom"] for r in D[P] if r["el"] == el and not r.get("glow")]).bounds
    bb = (u[0] - 8, u[1] - 8, u[2] + 8, u[3] + 8); ppm = 4.0
    mk = mock_local(el, bb, ppm); st = DV.image([base(P)], bb, ppm)
    W, H = st.size
    zs = []
    for name, kw in ZOOMS[el]:
        if el == "04" and name.startswith("oval"):
            b_ = META["badges"]["04"]; z = (u[2] - 30, (u[1] + u[3]) / 2 - 15, u[2] + 2, (u[1] + u[3]) / 2 + 17)
        else:
            unit = kw.pop("unit"); z = zone(P, unit, **kw); kw["unit"] = unit
        zs.append((name, z))
    zw = 330
    rows = []
    for name, z in zs:
        zp = zw / (z[2] - z[0])
        a = mock_local(el, z, zp); s_ = DV.image([base(P)], z, zp)
        pair = Image.new("RGB", (zw * 2 + 8, a.height), (255, 255, 255)); pair.paste(a, (0, 0)); pair.paste(s_, (zw + 8, 0))
        rows.append(label(pair, f"{name} — x {z[0]:.0f}..{z[2]:.0f}, y {z[1]:.0f}..{z[3]:.0f} mm (mockup | DST)"))
    zcol_h = sum(r.height + 8 for r in rows)
    out = Image.new("RGB", (W * 2 + 40 + zw * 2 + 30, max(H + 70, zcol_h + 50)), (255, 255, 255))
    out.paste(mk, (10, 60)); out.paste(st, (W + 30, 60)); d = ImageDraw.Draw(out)
    d.text((10, 6), f"{el} {kccore.ELEMENTS[el][1]} — Rev B, size {size}", fill=(0, 0, 0), font=FONT)
    d.text((10, 34), f"MOCKUP (flat.png, motif scale {MM.S:.3f} mm/px; low-res render, no close-up)", fill=(0, 0, 0), font=FS)
    d.text((W + 30, 34), f"WRITTEN DST read back ({os.path.basename(base(P))}.dst, {ppm:.0f} px/mm, same scale)", fill=(0, 0, 0), font=FS)
    for _, z in zs:
        for X in (10, W + 30):
            d.rectangle([X + (z[0]-bb[0])*ppm, 60 + (z[1]-bb[1])*ppm, X + (z[2]-bb[0])*ppm, 60 + (z[3]-bb[1])*ppm], outline=(255, 60, 60), width=2)
    y = 50; x0 = W * 2 + 50
    for r in rows: out.paste(r, (x0, y)); y += r.height + 8
    p = f"out/compare_{el}_{kccore.ELEMENTS[el][0]}.png"; out.save(p); return p

def fronts():
    bb = (-310, -100, 310, 520); ppm = 1.6
    st = DV.image([base("FR"), base("FL")], bb, ppm)
    d_ = ImageDraw.Draw(st)
    for s_ in "RL":
        w_ = F.keep_geoms(size, s_)["welt"]; d_.polygon([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in w_.exterior.coords], outline=(120, 130, 150))
        pn = F.keep_geoms(size, s_)["panel"]; d_.line([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in pn.exterior.coords], fill=(120, 120, 120), width=1)
    d_.rectangle([(-6 - bb[0])*ppm, (0 - bb[1])*ppm, (6 - bb[0])*ppm, (510 - bb[1])*ppm], fill=(160, 125, 60))
    mk = MM.warp(bb, ppm)
    W, H = st.size; out = Image.new("RGB", (W*2 + 20, H + 40), (255, 255, 255)); out.paste(mk, (0, 40)); out.paste(st, (W + 20, 40))
    d = ImageDraw.Draw(out); d.text((10, 8), "MOCKUP fronts (mapped to size-M mm: x 0.902, y 0.703 mm/px)", fill=(0, 0, 0), font=FS)
    d.text((W + 30, 8), f"WRITTEN DST FR + FL size {size} read back (badges at motif scale; Drum Island panel, welts outlined)", fill=(0, 0, 0), font=FS)
    out.save(f"out/compare_front_{size}.png"); st.save(f"out/render_front_{size}.png")

def sleeves():
    import sleeve as SV
    ims = []
    for P in ("SR", "SL"):
        b = SV.piece(size, P).sew_poly().bounds; bb = (b[0] - 5, b[1] - 5, b[2] + 5, b[3] + 5)
        st = DV.image([base(P)], bb, 1.2); d_ = ImageDraw.Draw(st)
        d_.line([((x - bb[0])*1.2, (y - bb[1])*1.2) for x, y in SV.piece(size, P).sew_poly().exterior.coords], fill=(150, 150, 150), width=2)
        ims.append(st)
    q = MM.mock(); crop = Image.fromarray(q.astype("uint8")).crop((30, 400, 1100, 1260)).resize((int(1070*0.7), int(860*0.7)))
    W = sum(i.width for i in ims) + crop.width + 60; H = max(max(i.height for i in ims), crop.height) + 40
    out = Image.new("RGB", (W, H), (255, 255, 255)); x = 10
    out.paste(crop, (x, 40)); x += crop.width + 20
    for i in ims: out.paste(i, (x, 40)); x += i.width + 20
    d = ImageDraw.Draw(out); d.text((10, 8), f"MOCKUP (sleeves seen from the front)  |  WRITTEN DST right sleeve S01, left sleeve S02, size {size} (whole piece; front half toward the body side)", fill=(0, 0, 0), font=FS)
    out.save("out/compare_05_sleeves.png")
    # sparkle close-up: mockup sparkle vs a DST sparkle (same scale)
    rs = sorted([r for r in D["FL"] if r["el"] == "05" and r["grp"] == "SPK"], key=lambda r: -r["geom"].area)
    if rs:
        c = rs[0]["geom"].centroid; z = (c.x - 9, c.y - 9, c.x + 9, c.y + 9)
        s_ = DV.image([base("FL")], z, 24); s_.save("out/ref/sparkle_dst.png")

if __name__ == "__main__":
    for el in ("01", "02", "03", "04"): print(sheet(el))
    fronts(); sleeves(); print("fronts + sleeves")
