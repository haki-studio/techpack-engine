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

size = next((a for a in sys.argv[1:] if not a.startswith("-")), "M") if __name__ == "__main__" else "M"
D = pickle.load(open(f"art_{size}.pkl", "rb")); META = pickle.load(open("scene.pkl", "rb"))["meta"]
_FD = os.path.expanduser("~/.local/share/fonts")
FONT = ImageFont.truetype("inputs/fonts/_inst_cn_720.ttf", 22); FS = ImageFont.truetype("inputs/fonts/_inst_cn_640.ttf", 17)
FS_KR = ImageFont.truetype("inputs/fonts/_inst_kr_560.ttf", 17)
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

REF_BOX = {"01": ((330, 160, 940, 520), 0), "02": ((1150, 200, 1600, 720), 0), "03": ((250, 680, 560, 1270), 0), "04": ((800, 1040, 1360, 1190), 180)}
def ref_panel(el, H):
    """the founder's source frame (inputs/reference.png) around this badge, KR turned upright, scaled to height H"""
    if not os.path.exists("inputs/reference.png"): return None
    b, rot = REF_BOX[el]; im = Image.open("inputs/reference.png").convert("RGB").crop(b)
    if rot: im = im.rotate(rot)
    return im.resize((int(im.width * H / im.height), H), Image.LANCZOS)

def gate_lines(el=None, field=None):
    """A14 / A15 gate rows from gates.json (shipped DST) for this element"""
    if not os.path.exists("gates.json"): return ["A14/A15 gates: gates.json missing — run gates.py"]
    G = json.load(open("gates.json")); out = [f"A14 / A15 GATES ({G.get('source', '')}; IoU >= 0.70, size within 0.8-1.25, bare gap < 25 mm²)",
                                               "  text tier (JP / EN letters): IoU >= 0.40, size 0.55-1.45; each stitched letter also gated vs its font glyph"]
    keys = [k for k in G["summary"] if (el and k.startswith(el + " ")) or (field and k.startswith("05 field"))]
    for k in keys:
        v = G["summary"][k]; st = "PASS" if v["fail"] == 0 and v["gaps_ge25"] == 0 else "FAIL"
        out.append(f"  {k:12s} {st}: {v['n']} motifs — {v['ok']} match (median IoU {v['iou_med']}), {v['moved']} moved by the art (keep-out), "
                   f"{v.get('text', 0)} text-tier, {v.get('occluded', 0)} hidden in the render, {v['fail']} FAIL; bare gaps >= 25 mm²: {v['gaps_ge25']}")
    for n in G.get("not_traced", []):
        if (el and n.startswith(el)) or (field and n.startswith("05")) or (el in ("01", "02") and n.startswith("01 + 02")): out.append("  generated, not traced: " + n)
    return out

ZOOMS = {
 "01": [("宇宙 + face star (puff text, rims, halo)", dict(unit="01-text", ch="宙", h=19)), ("き れ (curved baseline, bars)", dict(unit="01-text", ch="き", h=19)),
        ("top star: dark pit + white centre, bars", dict(unit="01-star1", h=15)), ("bottom red star: solid, star pit", dict(unit="01-star3", h=13))],
 "02": [("KEEP (puff, rim)", dict(unit="02-text", ch="K", h=17)), ("CLEAN (lemon, lemon-tint rim)", dict(unit="02-text", ch="L", h=17)),
        ("SPACE + halo", dict(unit="02-text", ch="S", h=17)), ("faceted border stars", dict(unit="02-star5", h=12))],
 "03": [("要 (flat column satin)", dict(unit="03-text", ch="要", h=17)), ("世 界", dict(unit="03-text", ch="界", h=17)),
        ("domed ring dots + halo", dict(unit="03-dots", h=14, pick=lambda rs: [min(rs, key=lambda r: r["geom"].bounds[1])])), ("inner sparkles", dict(unit="03-sp9", h=10))],
 "04": [("우리들 (light satin columns)", dict(unit="04-text", ch="들", h=16)), ("소중한", dict(unit="04-text", ch="중", h=16)),
        ("우주! (the '!' the render showed rotated)", dict(unit="04-text", ch="!", h=14)), ("oval ring + highlight", dict(unit="04-oval", h=14, pick=lambda rs: rs))],
}

def label(im, s, f=FS):
    out = Image.new("RGB", (im.width, im.height + 26), (255, 255, 255)); out.paste(im, (0, 26))
    if any("\uac00" <= ch <= "\ud7af" for ch in s): f = FS_KR
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
    rp = ref_panel(el, H); RW = rp.width + 20 if rp is not None else 0
    gl = gate_lines(el=el); gh = 26 * len(gl) + 20
    out = Image.new("RGB", (W * 2 + 40 + RW + zw * 2 + 30, max(H + 70 + gh, zcol_h + 50)), (255, 255, 255))
    out.paste(mk, (10, 60)); out.paste(st, (W + 30, 60)); d = ImageDraw.Draw(out)
    if rp is not None:
        out.paste(rp, (2 * W + 50, 60)); d.text((2 * W + 50, 34), "SOURCE FRAME (founder; text + lettering)" + (" — turned upright" if el == "04" else ""), fill=(0, 0, 0), font=FS)
    for i, l in enumerate(gl): d.text((10, H + 80 + i * 26), l, fill=(0, 0, 0) if i else (20, 20, 120), font=FS_KR if any("\uac00" <= c <= "\ud7af" for c in l) else FS)
    d.text((10, 6), f"{el} {kccore.ELEMENTS[el][1]} — {kccore.REV_EMB}, size {size}", fill=(0, 0, 0), font=ImageFont.truetype("inputs/fonts/_inst_kr_560.ttf", 22) if el == "04" else FONT)
    narrow = W < 700
    d.text((10, 34), "MOCKUP (flat.png, low-res)" if narrow else f"MOCKUP (flat.png, motif scale {MM.S:.3f} mm/px; low-res render, no close-up)", fill=(0, 0, 0), font=FS)
    d.text((W + 30, 34), f"DST read back ({os.path.basename(base(P))}.dst)" if narrow else f"WRITTEN DST read back ({os.path.basename(base(P))}.dst, {ppm:.0f} px/mm, same scale)", fill=(0, 0, 0), font=FS)
    for _, z in zs:
        for X in (10, W + 30):
            d.rectangle([X + (z[0]-bb[0])*ppm, 60 + (z[1]-bb[1])*ppm, X + (z[2]-bb[0])*ppm, 60 + (z[3]-bb[1])*ppm], outline=(255, 60, 60), width=2)
    y = 50; x0 = W * 2 + 50 + RW
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
    W, H = st.size; gl = gate_lines(field=True); out = Image.new("RGB", (W*2 + 20, H + 60 + 26 * len(gl)), (255, 255, 255)); out.paste(mk, (0, 40)); out.paste(st, (W + 20, 40))
    dd = ImageDraw.Draw(out)
    for i, l in enumerate(gl): dd.text((10, H + 50 + i * 26), l, fill=(0, 0, 0), font=FS)
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
