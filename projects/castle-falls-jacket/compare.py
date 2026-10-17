"""Fidelity sheets out/compare_<element>.png: the mockup mapped onto the size-M pattern piece (mockmap.warp, Lanczos x4 —
reads shapes, adds no detail) beside the stitch render of the size-M art at the SAME scale, + 4 zoomed pairs per element.
usage: python3 compare.py [01 02 03]"""
import cfcore
import pickle, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import stitchrender as SR, mockmap as MM, keepout as KO

ZOOMS = {   # element -> [(piece, (x0, y0, x1, y1) mm, caption)]
 "01": [("BK", (-215, 260, -135, 340), "left falls + cliff"), ("BK", (-60, 120, 20, 200), "cloud bank + petals"),
        ("BK", (-230, 440, -150, 520), "cherry tree florets"), ("BK", (-60, 470, 20, 550), "village roofs")],
 "02": [("FL", (30, 160, 190, 340), "castle (original design)"), ("FR", (-150, 300, -70, 380), "pagoda"),
        ("FL", (120, 390, 200, 470), "bridge + blossom"), ("FR", (-150, 60, -70, 140), "clouds + petals")],
 "03": [("SR", (0, 120, 100, 220), "SR front: cliff foliage"), ("SR", (20, 300, 120, 400), "SR front: cherry florets"),
        ("SL", (40, 150, 140, 250), "SL back: clouds"), ("SL", (-170, 150, -70, 250), "SL front: gate tower")],
}
PIECES = {"01": ["BK"], "02": ["FR", "FL"], "03": ["SR", "SL"]}

def pair(P, bb, ppm, vis, size="M"):
    st = SR.render(vis, bb, ppm, base=cfcore.FABRIC)
    up = max(1, min(4, int(round(ppm))))
    mk = Image.fromarray(MM.warp(P, bb, ppm, up=4).clip(0, 255).astype(np.uint8)).resize(st.size, Image.LANCZOS)
    m = Image.new("L", st.size, 0); d = ImageDraw.Draw(m)
    T = lambda cs: [((x - bb[0]) * ppm, (y - bb[1]) * ppm) for x, y in cs]
    d.polygon(T(KO.panel(size, P).exterior.coords), fill=255)
    white = Image.new("RGB", st.size, (255, 255, 255))
    mk = Image.composite(mk, white, m); st = Image.composite(st, white, m)
    dc = ImageDraw.Draw(st); dc.line(T(KO.clip(size, P).exterior.coords), fill=(255, 90, 90), width=1)
    return mk, st

def sheet(e, size="M"):
    art = pickle.load(open(f"art_{size}.pkl", "rb")); pcs = PIECES[e]; ppm = 1.4
    tiles = []
    for P in pcs:
        b = KO.panel(size, P).bounds; b = (b[0] - 4, b[1] - 4, b[2] + 4, b[3] + 4)
        tiles.append((P, b) + pair(P, b, ppm, art[P]))
    W = sum(t[2].width for t in tiles) * 2 + 40 * len(tiles); H = max(t[2].height for t in tiles)
    zw = 330; zrows = len(ZOOMS[e])
    out = Image.new("RGB", (W + zw * 2 + 40, max(H + 50, zrows * (zw + 40) + 40)), (255, 255, 255)); d = ImageDraw.Draw(out)
    x = 10
    for P, b, mk, st in tiles:
        out.paste(mk, (x, 30)); d.text((x, 10), f"MOCKUP {P} (flat.png mapped onto the size-{size} pattern)", fill=(0, 0, 0))
        out.paste(st, (x + mk.width + 10, 30)); d.text((x + mk.width + 10, 10), f"STITCH RENDER {P} size {size}, same scale (red = keep-out line)", fill=(0, 0, 0))
        for (zp, zb, cap) in ZOOMS[e]:
            if zp != P: continue
            for X0 in (x, x + mk.width + 10):
                d.rectangle([X0 + (zb[0] - b[0]) * ppm, 30 + (zb[1] - b[1]) * ppm, X0 + (zb[2] - b[0]) * ppm, 30 + (zb[3] - b[1]) * ppm], outline=(255, 40, 40), width=2)
        x += mk.width * 2 + 40
    x0 = W + 20; y = 30
    for (zp, zb, cap) in ZOOMS[e]:
        zp_ = zw / (zb[2] - zb[0]); a, s_ = pair(zp, zb, zp_, art[zp])
        out.paste(a, (x0, y)); out.paste(s_, (x0 + zw + 10, y))
        d.text((x0, y - 14), f"{zp} {cap}: x {zb[0]}..{zb[2]}, y {zb[1]}..{zb[3]} mm (mockup x4 | render)", fill=(0, 0, 0))
        y += a.height + 40
    out.save(f"out/compare_{cfcore.ELEMS[e][0]}.png")
    return out.size

if __name__ == "__main__":
    for e in sys.argv[1:] or ["01", "02", "03"]: print(e, sheet(e))
