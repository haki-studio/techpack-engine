"""Fidelity sheets out/compare_<element>.png from the FINAL size-M stitch files (LESSONS A11/A12, review rule: compare sheets
come from the DSTs, not the art). Left = the mockup mapped onto the size-M pattern piece (mockmap.warp, Lanczos x4 — reads
shapes, adds no detail; the registered falls close-up is composited in, A12); right = the DST read back and drawn stitch by
stitch in its PES thread colours (0.42 mm thread width) on the shell colour, placed by the file origin, SAME scale.
Then 4 zoomed pairs per element; the back adds a 3-up row: raw close-up panel | mockup composite | DST.
usage: python3 compare.py [01 02 03]"""
import cfcore
import json, sys
import numpy as np
import pyembroidery as pe
from PIL import Image, ImageDraw, ImageFont
import mockmap as MM, keepout as KO, make_current as MC, scene as SCN

ZOOMS = {   # element -> [(piece, (x0, y0, x1, y1) mm, caption)]
 "01": [("BK", (-215, 260, -135, 340), "left falls + cliff"), ("BK", (-60, 120, 20, 200), "cloud bank + petals"),
        ("BK", (-230, 440, -150, 520), "cherry tree florets"), ("BK", (-60, 470, 20, 550), "village roofs")],
 "02": [("FL", (30, 160, 190, 340), "castle (reference composition)"), ("FR", (-200, 210, -100, 310), "pagoda"),
        ("FL", (120, 390, 200, 470), "bridge + blossom"), ("FR", (-150, 60, -70, 140), "clouds + petals")],
 "03": [("SR", (0, 120, 100, 220), "SR front: cliff foliage"), ("SR", (-170, 250, -70, 350), "SR back: cherry florets"),
        ("SL", (40, 150, 140, 250), "SL back: clouds"), ("SL", (-195, 235, -105, 325), "SL front: gate tower")],
}
PIECES = {"01": ["BK"], "02": ["FR", "FL"], "03": ["SR", "SL"]}
FALLS_BOX = ("BK", (-240, 250, -100, 520), "falls mountain: CLOSE-UP panel (registered, A12) | mockup composite | final DST")
FAB = tuple(int(cfcore.FABRIC[i:i + 2], 16) for i in (1, 3, 5))
try: FNT = ImageFont.truetype("DejaVuSans-Bold.ttf", 15)
except Exception: FNT = None

_SEG = {}
def segments(P, size="M"):
    """sewn segments of the final DST of piece P in pattern mm: (N, 4) array + colour per segment"""
    if (P, size) not in _SEG:
        r = json.load(open(MC.path(size, P)))["full"]; ox, oy = r["origin"]
        cols = [t.hex_color() for t in pe.read(r["file"] + ".pes").threadlist]
        seg, ci_ = [], []; ci = 0; prev = None
        for x, y, c in pe.read(r["file"] + ".dst").stitches:
            k = c & pe.COMMAND_MASK
            if k == pe.COLOR_CHANGE: ci += 1; prev = None; continue
            if k != pe.STITCH: prev = None; continue
            q = (x / 10 + ox, y / 10 + oy)
            if prev is not None: seg.append(prev + q); ci_.append(min(ci, len(cols) - 1))
            prev = q
        _SEG[(P, size)] = (np.array(seg), np.array(ci_), cols, r["file"])
    return _SEG[(P, size)]

def dst_image(P, bb, ppm, size="M"):
    x0, y0, x1, y1 = bb; W, H = int(round((x1 - x0) * ppm)), int(round((y1 - y0) * ppm))
    im = Image.new("RGB", (W, H), FAB); d = ImageDraw.Draw(im); lw = max(1, int(round(0.42 * ppm)))
    S, C, cols, _ = segments(P, size)
    inb = ((np.maximum(S[:, 0], S[:, 2]) >= x0) & (np.minimum(S[:, 0], S[:, 2]) <= x1) &
           (np.maximum(S[:, 1], S[:, 3]) >= y0) & (np.minimum(S[:, 1], S[:, 3]) <= y1))
    for s, c in zip(S[inb], C[inb]):
        d.line([((s[0] - x0) * ppm, (s[1] - y0) * ppm), ((s[2] - x0) * ppm, (s[3] - y0) * ppm)], fill=cols[c], width=lw)
    return im

def pair(P, bb, ppm, size="M"):
    st = dst_image(P, bb, ppm, size)
    mk = Image.fromarray(MM.warp(P, bb, ppm, up=4).clip(0, 255).astype(np.uint8)).resize(st.size, Image.LANCZOS)
    m = Image.new("L", st.size, 0); d = ImageDraw.Draw(m)
    T = lambda cs: [((x - bb[0]) * ppm, (y - bb[1]) * ppm) for x, y in cs]
    d.polygon(T(KO.panel(size, P).exterior.coords), fill=255)
    white = Image.new("RGB", st.size, (255, 255, 255))
    mk = Image.composite(mk, white, m); st = Image.composite(st, white, m)
    dc = ImageDraw.Draw(st); dc.line(T(KO.clip(size, P).exterior.coords), fill=(255, 90, 90), width=1)
    return mk, st

def closeup_image(bb, ppm):
    """the raw falls panel of inputs/closeup_mockup_strip.png resampled into back mm (inverse of the A12 registration)"""
    from scipy.ndimage import map_coordinates
    c = MM.CLOSEUPS["falls"]; S = np.asarray(Image.open("inputs/closeup_mockup_strip.png").convert("RGB")).astype(np.float32)
    x0, y0, x1, y1 = bb; W, H = int(round((x1 - x0) * ppm)), int(round((y1 - y0) * ppm))
    XX, YY = np.meshgrid(x0 + (np.arange(W) + .5) / ppm, y0 + (np.arange(H) + .5) / ppm)
    fx, fy = MM.piece_px("BK", XX, YY)
    px = c["box"][0] + c["a_panel"][0] + (fx - c["a_flat"][0]) / c["s"]; py = c["box"][1] + c["a_panel"][1] + (fy - c["a_flat"][1]) / c["s"]
    out = np.stack([map_coordinates(S[..., k], [py, px], order=1, cval=255) for k in range(3)], -1)
    out[(px < c["box"][0]) | (px > c["box"][2]) | (py < c["box"][1]) | (py > c["box"][3])] = 255
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))

def txt(d, xy, s): d.text(xy, s, fill=(0, 0, 0), font=FNT)

def sheet(e, size="M"):
    pcs = PIECES[e]; ppm = 1.4; tiles = []
    for P in pcs:
        b = KO.panel(size, P).bounds; b = (b[0] - 4, b[1] - 4, b[2] + 4, b[3] + 4)
        tiles.append((P, b) + pair(P, b, ppm, size))
    W = sum(t[2].width for t in tiles) * 2 + 40 * len(tiles); H = max(t[2].height for t in tiles)
    zw = 330; zs = ZOOMS[e]
    extra = 0
    if e == "01":
        fb = FALLS_BOX[1]; fz = zw / (fb[2] - fb[0]) * 1.0; extra = int((fb[3] - fb[1]) * fz) + 60
    out = Image.new("RGB", (W + zw * 2 + 40, max(H + 60 + extra, len(zs) * (zw + 40) + 40)), (255, 255, 255)); d = ImageDraw.Draw(out)
    x = 10
    for P, b, mk, st in tiles:
        out.paste(mk, (x, 34)); txt(d, (x, 10), f"MOCKUP {P} (mapped onto the size-{size} pattern)")
        out.paste(st, (x + mk.width + 10, 34)); txt(d, (x + mk.width + 10, 10), f"FINAL DST {P} size {size}, stitch by stitch, same scale")
        for (zp, zb, cap) in zs:
            if zp != P: continue
            for X0 in (x, x + mk.width + 10):
                d.rectangle([X0 + (zb[0] - b[0]) * ppm, 34 + (zb[1] - b[1]) * ppm, X0 + (zb[2] - b[0]) * ppm, 34 + (zb[3] - b[1]) * ppm], outline=(255, 40, 40), width=2)
        x += mk.width * 2 + 40
    x0 = W + 20; y = 34
    for (zp, zb, cap) in zs:
        zp_ = zw / (zb[2] - zb[0]); a, s_ = pair(zp, zb, zp_, size)
        out.paste(a, (x0, y)); out.paste(s_, (x0 + zw + 10, y))
        txt(d, (x0, y - 18), f"{zp} {cap}: x {zb[0]}..{zb[2]}, y {zb[1]}..{zb[3]} mm  (mockup | DST)")
        y += a.height + 40
    if e == "01":
        P, fb, cap = FALLS_BOX; yy = H + 80
        cu = closeup_image(fb, fz); mk, st = pair(P, fb, fz, size)
        txt(d, (10, yy - 20), f"{P} {cap}: x {fb[0]}..{fb[2]}, y {fb[1]}..{fb[3]} mm")
        for i, im in enumerate((cu, mk, st)): out.paste(im, (10 + i * (im.width + 10), yy))
    # fidelity gate tables (LESSONS A14/A15) from fidelity.py, read off the same final DSTs
    import os
    if os.path.exists("out/fidelity_M.json"):
        FD = json.load(open("out/fidelity_M.json")); lines = ["FIDELITY GATES (size M, final DSTs): qa.motif_match per family (IoU >= 0.70, w/h >= 80 %) + qa.uncovered (gaps >= 25 mm2)"]
        for P in pcs:
            if P not in FD: continue
            for fm, v in FD[P]["families"].items():
                lines.append(f"  {P} {fm:14s} motifs {v['motifs']:4d}   pass {v['passed']:4d}   min IoU {v['iou_min']}   {'PASS' if v['passed'] == v['motifs'] else 'FAIL'}")
            lines.append(f"  {P} uncovered gaps >= 25 mm2: {len(FD[P]['gaps'])}   {'PASS' if not FD[P]['gaps'] else 'FAIL'}")
        gen = [f"{P}: " + ", ".join(SCN.GENERATED.get(P, {}).keys()) for P in pcs if SCN.GENERATED.get(P)]
        lines.append("  Generated, not traced: " + ("; ".join(gen) if gen else "none") + "  (structure overlays — tile ribs, studs, windows, cords, lobes, florets — sit inside traced silhouettes)")
        ext = Image.new("RGB", (out.width, out.height + 22 * len(lines) + 20), (255, 255, 255)); ext.paste(out, (0, 0)); d2 = ImageDraw.Draw(ext)
        for i, l in enumerate(lines): txt(d2, (10, out.height + 8 + i * 22), l)
        out = ext
    out.save(f"out/compare_{cfcore.ELEMS[e][0]}.png")
    return out.size, [segments(P, size)[3] for P in pcs]

if __name__ == "__main__":
    for e in sys.argv[1:] or ["01", "02", "03"]: print(e, *sheet(e))
