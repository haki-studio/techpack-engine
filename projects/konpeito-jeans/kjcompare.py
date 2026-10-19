"""Fidelity gates (LESSONS A14/A15) + compare sheets out/compare_<element>.png: mockup vs stitch preview from the DST,
same scale, zoomed regions, motif_match table per motif family and the uncovered-area table."""
import json, math, pickle
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
import kjcore
import pyembroidery as pe
import qa
import kjstitch as K

PPM = 20
FONT = "inputs/fonts/ZenMaruGothic-Bold.ttf"
def font(sz):
    try: return ImageFont.truetype(FONT, sz)
    except Exception: return ImageFont.load_default()

def dst_masks_on(path, origin, grid_shape, to_px):
    """per-thread coverage masks of the DST drawn on a reference grid. to_px(x_mm, y_mm) maps design mm -> grid px."""
    p = pe.read(path); cols = [t.hex_color().upper() for t in pe.read(path[:-4] + ".pes").threadlist]
    Hh, Ww = grid_shape
    ims = {}; ci = 0; prev = None
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK
        P = to_px(x / 10 + origin[0], y / 10 + origin[1])
        if k == pe.STITCH:
            if prev is not None:
                c = cols[min(ci, len(cols) - 1)]
                for key in (c, ci):
                    if key not in ims: ims[key] = Image.new("L", (Ww, Hh), 0)
                    ImageDraw.Draw(ims[key]).line([prev, P], fill=255, width=max(1, int(round(0.35 * PPM))))
            prev = P
        elif k == pe.COLOR_CHANGE: ci += 1; prev = None
        elif k == pe.TRIM: prev = None
        elif k == pe.JUMP: prev = P
        elif k == pe.END: break
    return {c: ndi.binary_closing(np.array(im) > 0, iterations=2) for c, im in ims.items()}

HEX = {k: v[0].upper() for k, v in kjcore.KJ_PAL.items()}
def U(masks, *keys):
    out = None
    for k in keys:
        m = masks.get(HEX[k])
        if m is None: continue
        out = m.copy() if out is None else (out | m)
    return out

def S_(masks, *idx):
    """union of the masks of these stop numbers (1-based, as on the G pages)"""
    out = None
    for i in idx:
        m = masks.get(i - 1)
        if m is not None: out = m.copy() if out is None else (out | m)
    return out

def gate(ref, out, ppm, near_mm=1.5, **kw):
    """qa.motif_match per traced motif, each against the stitches of the stop(s) that sew its family lying within
    near_mm of THAT motif: the motifs touch their neighbours (letters, overlapping candies), so the DST shapes merge and
    a whole-family comparison would compare a word with a letter."""
    if out is None: out = np.zeros_like(ref)
    lab, n = ndi.label(ref); rows = []
    it = max(1, int(near_mm * ppm))
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        m = lab == k
        if m.sum() / ppm ** 2 < kw.get("min_mm2", 4.0): continue
        o = out & ndi.binary_dilation(m, iterations=it)
        r = qa.motif_match(m, o, ppm, **kw)
        for q in r: q["motif"] = k
        rows += r
    return rows

def summarise(name, fam_rows):
    S = []
    for fam, rows in fam_rows.items():
        n = len(rows); ok = sum(r["ok"] for r in rows)
        S.append(dict(family=fam, motifs=n, passed=ok, min_iou=min([r["iou"] for r in rows], default=None),
                      mean_iou=round(float(np.mean([r["iou"] for r in rows])), 2) if rows else None))
    return S

def zoom_sheet(name, ref_img, prev_img, zooms, table, unc, title, notes):
    """ref_img/prev_img: PIL at the same px/mm. zooms: [(x0,y0,x1,y1) px]."""
    W = 2400; pad = 30
    s = (W - 3 * pad) / 2 / ref_img.width
    a = ref_img.resize((int(ref_img.width * s), int(ref_img.height * s)))
    b = prev_img.resize(a.size)
    zh = 360
    H = 120 + a.height + 2 * pad + (zh + 60) * math.ceil(len(zooms) / 2) + 60 + 34 * (len(table) + 6 + len(unc))
    im = Image.new("RGB", (W, int(H)), "white"); d = ImageDraw.Draw(im)
    d.text((pad, 20), title, fill=(20, 20, 20), font=font(40))
    d.text((pad, 72), "LEFT: mockup (rectified to finished mm)   RIGHT: stitch preview drawn from the shipped DST, same scale", fill=(90, 90, 90), font=font(26))
    im.paste(a, (pad, 120)); im.paste(b, (2 * pad + a.width, 120))
    y = 120 + a.height + pad
    for i, (x0, y0, x1, y1) in enumerate(zooms):
        ca = ref_img.crop((x0, y0, x1, y1)); cb = prev_img.crop((x0, y0, x1, y1))
        zs = zh / ca.height; ca = ca.resize((int(ca.width * zs), zh)); cb = cb.resize(ca.size)
        col = i % 2; xx = pad + col * (W // 2)
        if col == 0 and i: y += zh + 60
        im.paste(ca, (xx, y + 30)); im.paste(cb, (xx + ca.width + 10, y + 30))
        d.text((xx, y), f"zoom {i + 1}: x {x0 / PPM:.0f}-{x1 / PPM:.0f}, y {y0 / PPM:.0f}-{y1 / PPM:.0f} mm (mockup | DST)", fill=(60, 60, 60), font=font(24))
    y += zh + 80
    d.text((pad, y), "A14 motif_match per family (IoU >= 0.70, width + height >= 80 %)", fill=(20, 20, 20), font=font(30)); y += 42
    hdr = ["family", "motifs", "pass", "min IoU", "mean IoU"]
    for j, h_ in enumerate(hdr): d.text((pad + j * 300, y), h_, fill=(90, 90, 90), font=font(26))
    y += 34
    for r in table:
        okc = (30, 140, 60) if r["motifs"] and r["passed"] == r["motifs"] else (180, 40, 30)
        for j, k in enumerate(["family", "motifs", "passed", "min_iou", "mean_iou"]):
            d.text((pad + j * 300, y), str(r[k]), fill=okc if j == 2 else (20, 20, 20), font=font(26))
        y += 34
    y += 10
    d.text((pad, y), "A15 uncovered areas >= 25 mm2 (design says embroidered, DST bare): " + ("none" if not unc else ""), fill=(20, 20, 20), font=font(28)); y += 38
    for u in unc:
        d.text((pad + 20, y), f"x {u['x_mm']} y {u['y_mm']} mm, {u['w_mm']} x {u['h_mm']} mm, {u['area_mm2']} mm2 — {u.get('why', '')}", fill=(20, 20, 20), font=font(24)); y += 34
    for n_ in notes:
        d.text((pad, y), n_, fill=(90, 90, 90), font=font(24)); y += 32
    im = im.crop((0, 0, W, y + 20))
    im.save(f"out/compare_{name}.png")

def run():
    A = pickle.load(open("out/art.pkl", "rb")); G = {}
    # ---------------- waistband patch
    rj = json.load(open("out/stitch/HAKI_KJ_03_waistband-patch.json")); ref = A["wb"]["ref"]
    shape = ref["frame"].shape
    M = dst_masks_on("out/stitch/HAKI_KJ_03_waistband-patch.dst", rj["origin_mm"], shape, lambda x, y: (x * PPM, y * PPM))
    fam = {"frame (red)": gate(ref["frame"], S_(M, 10), PPM),
           "ちひろ (red)": gate(ndi.binary_closing(ref["chihiro"], iterations=3), S_(M, 10), PPM),
           "hearts (pink)": gate(ref["hearts"], S_(M, 4), PPM),
           "flowers (pink/yellow/blue + knots)": gate(ref["flowers"], S_(M, 4, 5, 6, 7), PPM),
           "元気でね / また会おうね (black)": gate(ndi.binary_closing(ref["text"], iterations=3), S_(M, 9), PPM),
           "face line art (black)": gate(ref["face"], S_(M, 9), PPM, min_mm2=1.0, near_mm=0.8),
           "理砂 (blue)": gate(ndi.binary_closing(ref["risa"], iterations=3), S_(M, 6), PPM),
           "accent dots (red)": gate(ref["dots"], S_(M, 10), PPM, min_mm2=0.8, near_mm=0.8),
           "cheeks (rose)": gate(ref["cheeks"], S_(M, 8), PPM, min_mm2=1.0)}
    allout = np.any([m for k_, m in M.items() if isinstance(k_, str)], axis=0)
    design = np.zeros(shape, bool); design[int(1 * PPM):int(53 * PPM), int(1 * PPM):int(79 * PPM)] = True
    unc = qa.uncovered(design, allout, PPM)
    G["wb"] = dict(families=summarise("wb", fam), rows=fam, uncovered=unc)
    rect = Image.open("out/trace/wb_rect.png").convert("RGB")
    prev = render_on(f"out/stitch/HAKI_KJ_03_waistband-patch.dst", rj["origin_mm"], shape, lambda x, y: (x * PPM, y * PPM))
    zoom_sheet("waistband-patch", rect, prev, [(160, 160, 760, 560), (430, 380, 1300, 720), (200, 560, 900, 960), (1200, 300, 1560, 1000)],
               G["wb"]["families"], unc, "Compare — 03 waistband patch (ちひろ note), 80 x 54 mm",
               ["Gate: each traced motif vs the stitches of its stop(s) within 1.5 mm of it (touching motifs would merge otherwise).",
                "Lettering: satin columns on the traced stroke outlines (a per-character Zen Maru Gothic registration was tried and covered the pixels worse).",
                "Border: house spec (fixed mm), not traced — the mockup's border was registered onto it."])
    # ---------------- coin pocket
    rj = json.load(open("out/stitch/HAKI_KJ_01_coin-pocket-patch.json")); ref = A["coin"]["ref"]; shape = ref["letters"].shape
    M = dst_masks_on("out/stitch/HAKI_KJ_01_coin-pocket-patch.dst", rj["origin_mm"], shape, lambda x, y: (x * PPM, y * PPM))
    fam = {"こんぺいとう (red)": gate(ndi.binary_closing(ref["letters"], iterations=3), S_(M, 11), PPM),
           "konpeito candies": gate(ref["candies"], S_(M, 4, 5, 6, 7, 8, 9, 10), PPM),
           "accent dots (red)": gate(ref["dots"], S_(M, 11), PPM, min_mm2=0.8, near_mm=0.8)}
    allout = np.any([m for k_, m in M.items() if isinstance(k_, str)], axis=0)
    design = np.zeros(shape, bool); design[int(1 * PPM):int(46.5 * PPM), int(1 * PPM):int(75 * PPM)] = True
    unc = qa.uncovered(design, allout, PPM)
    G["coin"] = dict(families=summarise("coin", fam), rows=fam, uncovered=unc)
    rect = Image.open("out/trace/coin_rect.png").convert("RGB")
    prev = render_on("out/stitch/HAKI_KJ_01_coin-pocket-patch.dst", rj["origin_mm"], shape, lambda x, y: (x * PPM, y * PPM))
    zoom_sheet("coin-pocket-patch", rect, prev, [(160, 160, 900, 560), (850, 160, 1400, 560), (200, 560, 900, 1000), (900, 600, 1500, 1050)],
               G["coin"]["families"], unc, "Compare — 01 coin-pocket patch (こんぺいとう), 76 x 56 mm",
               ["Below y 47.5 mm the mockup patch is tucked into the pocket mouth (garment detail, masked out — A15).",
                "Border: house spec (fixed mm; mockup edge reads cream, house red kept)."])
    # ---------------- spill: map DST back into the spill rectified frame
    rj = json.load(open("out/stitch/HAKI_KJ_02_coin-spill-facing.json")); ref = A["spill"]["ref"]; shape = ref["candies"].shape
    kk, bb, ang, y_mid = ref["edge"]
    def to_spill(x, y):
        y = y + y_mid; t = math.radians(ang); cx, cy = 38.0, y_mid
        xr = cx + (x - cx) * math.cos(t) - (y - cy) * math.sin(t); yr = cy + (x - cx) * math.sin(t) + (y - cy) * math.cos(t)
        return (xr * PPM, (yr + 22.0) * PPM)
    M = dst_masks_on("out/stitch/HAKI_KJ_02_coin-spill-facing.dst", rj["origin_mm"], shape, to_spill)
    above = (np.arange(shape[0])[:, None] / PPM - 22.0) < (kk * np.arange(shape[1])[None, :] / PPM + bb - 0.2)
    allc = np.any([m for k_, m in M.items() if isinstance(k_, str)], axis=0) & above
    fam = {"konpeito spilling out (all colours)": gate(ref["candies"], allc, PPM)}
    G["spill"] = dict(families=summarise("spill", fam), rows=fam, uncovered=qa.uncovered(ndi.binary_fill_holes(ref["candies"]), allc, PPM))
    rect = Image.open("out/trace/spill_rect.png").convert("RGB")
    prev = render_on("out/stitch/HAKI_KJ_02_coin-spill-facing.dst", rj["origin_mm"], shape, to_spill, bg=(40, 40, 44))
    zoom_sheet("coin-spill", rect, prev, [(80, 100, 760, 400), (700, 100, 1500, 400)], G["spill"]["families"], G["spill"]["uncovered"],
               "Compare — 02 konpeito spilling out of the coin pocket (facing), 71 x 14 mm",
               ["The DST runs 3 mm below the pocket line (hidden under the coin-pocket patch); the gate compares the part above it."])
    # ---------------- haki group (upscaled crop grid)
    rj = json.load(open("out/stitch/HAKI_KJ_04_back-pocket-L-haki.json")); ref = A["haki"]["ref"]; k = ref["k"]
    shape = ref["blue"].shape
    to_h = lambda x, y: (x / k + ref["ox"], y / k + ref["oy"])
    M = dst_masks_on("out/stitch/HAKI_KJ_04_back-pocket-L-haki.dst", rj["origin_mm"], shape, to_h)
    fam = {"'haki' (light blue)": gate(ndi.binary_closing(ref["blue"], iterations=4), U(M, "kj_blue_hi"), 1 / k, min_mm2=2.0, pad_mm=0.5)}
    G["haki"] = dict(families=summarise("haki", fam), rows=fam, uncovered=[])
    im = Image.open("inputs/back_pocket_haki.png").convert("RGB"); x0, y0, x1, y1 = (175, 405, 310, 460)
    rect = im.crop((x0, y0, x1, y1)).resize(((x1 - x0) * 8, (y1 - y0) * 8), Image.LANCZOS)
    prev = render_on("out/stitch/HAKI_KJ_04_back-pocket-L-haki.dst", rj["origin_mm"], shape, to_h, bg=(40, 40, 44), wmm=0.42 / k / PPM)
    zoom_sheet("back-pocket-haki", rect, prev, [(200, 40, 700, 400), (600, 40, 1080, 400)], G["haki"]["families"], [],
               "Compare — 04 back-pocket 'haki' + 2 stars (scaled x2.1 so the stars are 10 mm)",
               ["Mockup shown at the upscaled crop; the DST is drawn on it at the same scale (group scaled up per the founder).",
                "Stars: 10 mm puffy-star shape at the traced centres (generated, not traced: 14 px in the mockup)."])
    json.dump(G, open("out/gates.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    for e, g in G.items():
        for r in g["families"]: print(e, r)
        print(e, "uncovered", g["uncovered"])
    return G

def render_on(path, origin, shape, to_px, bg=(52, 52, 56), wmm=None):
    p = pe.read(path); cols = [t.hex_color() for t in pe.read(path[:-4] + ".pes").threadlist]
    Hh, Ww = shape
    im = Image.new("RGB", (Ww, Hh), bg); d = ImageDraw.Draw(im)
    w = max(2, int(round((wmm or 0.42) * PPM)))
    ci = 0; prev = None
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK; P = to_px(x / 10 + origin[0], y / 10 + origin[1])
        if k == pe.STITCH:
            if prev is not None:
                c = cols[min(ci, len(cols) - 1)]; rgb = tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
                ww = max(2, int(w * 0.72)) if c.upper() == "#1C1A1A" else w
                d.line([prev, P], fill=tuple(int(v * 0.72) for v in rgb), width=ww); d.line([prev, P], fill=c, width=max(1, ww - 2))
            prev = P
        elif k == pe.COLOR_CHANGE: ci += 1; prev = None
        elif k == pe.TRIM: prev = None
        elif k == pe.JUMP: prev = P
        elif k == pe.END: break
    return im

if __name__ == "__main__":
    run()
