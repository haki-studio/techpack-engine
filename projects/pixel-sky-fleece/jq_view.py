"""Jacquard cell maps drawn back into the mockup's view (front.png px), for the compare sheets: fronts (exact, front
coords) + the visible front halves of the sleeves (mockmap.sleeve_to_img), on top of a neutral grey garment."""
import numpy as np
from PIL import Image, ImageDraw
import mockmap as MM, jacquard as JQ, fleece as FL

def render(opt="A", size="M", bird=None):
    a = MM.img().astype(np.uint8); H, W, _ = a.shape
    im = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(im)
    ph = JQ.front_phase(); fm = JQ.fill_front(JQ.trace_front_M(ph)); ff = JQ.grid_fn(fm)
    bc, _ = JQ.bird_cells()
    g, mt = FL.draft(size)
    for code in ("F01", "F02"):
        P = JQ.raster_panel(code, size, ff, bird=(bc if (code == "F02" and opt == "A") else None), bird_anchor=lambda s: 0.0)
        for r in range(P["grid"].shape[0]):
            j = P["j1"] - 1 - r; y0 = P["hem"] - (j + 1) * JQ.CELL
            for c in range(P["grid"].shape[1]):
                v = P["grid"][r, c]
                if v == JQ.OUTSIDE: continue
                x0 = (P["i0"] + c) * JQ.CELL
                if (code == "F01") != (x0 >= 0): continue
                if y0 > P["hem"] - 0.1 or y0 < -5: continue
                if not JQ.visible(x0 + JQ.CELL / 2, y0 + JQ.CELL / 2): continue
                px0, py0 = MM.Pinv(x0, y0); px1, py1 = MM.Pinv(x0 + JQ.CELL, y0 + JQ.CELL)
                d.rectangle([px0, py0, px1 - 0.01, py1 - 0.01], fill=JQ.COL[v])
    for code, side in (("S01", "R"), ("S02", "L")):
        fs = JQ.grid_fn(JQ.sleeve_trace(side))
        P = JQ.raster_panel(code, size, fs)
        sg = 1 if side == "R" else -1
        for r in range(P["grid"].shape[0]):
            j = P["j1"] - 1 - r; y0 = P["hem"] - (j + 1) * JQ.CELL
            for c in range(P["grid"].shape[1]):
                v = P["grid"][r, c]
                if v == JQ.OUTSIDE: continue
                x0 = (P["i0"] + c) * JQ.CELL
                if np.sign(x0 + JQ.CELL / 2) != sg: continue
                xs = np.array([x0, x0 + JQ.CELL, x0 + JQ.CELL, x0]); ys = np.array([y0, y0, y0 + JQ.CELL, y0 + JQ.CELL])
                px, py, _ = MM.sleeve_to_img(side, xs, ys, mt)
                if not (np.all(np.isfinite(px))): continue
                d.polygon(list(zip(px, py)), fill=JQ.COL[v])
    # garment details on top (zip, pockets) so the view reads like the mockup
    d.rectangle([MM.CFX - 8, MM.NECKY, MM.CFX + 8, MM.HEMY], fill=(30, 30, 30))
    import pixels as PX
    for (x0, y0), (x1, y1) in PX.POCKETS_PX: d.line([(x0, y0), (x1, y1)], fill=(25, 38, 63), width=7)
    return im

if __name__ == "__main__":
    im = render("A"); im.save("out/jacquard/view_front_A.png")
    a = Image.fromarray(MM.img().astype(np.uint8))
    sbs = Image.new("RGB", (3000, 1500), "white"); sbs.paste(a, (0, 0)); sbs.paste(im, (1500, 0)); sbs.save("out/jacquard/view_sbs.png")
