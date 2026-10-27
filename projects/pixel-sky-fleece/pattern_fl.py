"""Pattern outputs for the fleece: QA print, DXF per size + all sizes, 1:1 plot PDF (M), overview PNG.
usage: python3 pattern_fl.py [qa] [dxf] [pdf] [png]"""
import sys, os, cairosvg
import pattern as PT, pattern_out as PO, pattern_draw as PD, fleece as FL
from sheet import t, doc, SW, SH
STYLE = "HK-FL-PIXSKY"; OUTD = "out/pattern"; os.makedirs(OUTD, exist_ok=True)

def emb():
    try:
        import emb_place  # noqa: F401  (project module: embroidery placements on the pieces)
        PO.EMB_ON.clear(); PO.EMB_ON.update(emb_place.EMB_ON); PO.EMB_NAME.update(emb_place.EMB_NAME); return True
    except ImportError:
        return False

def overview(size="M", path="out/pattern/overview_M.png"):
    g, mt = FL.draft(size); o = [f'<rect width="{SW}" height="{SH}" fill="#fff"/>', t(10, 10, f"{STYLE} pattern size {size} (overview, not to scale)", 3, 700)]
    x, y, rowh, s = 10, 16, 0, 0.085
    for code in FL.ORDER:
        pc = g[code]; b = PT.cut_poly(pc).bounds; w, h = (b[2]-b[0])*s, (b[3]-b[1])*s
        if x + w > SW - 8: x = 10; y += rowh + 6; rowh = 0
        X = (lambda x0, b0: lambda q: x0 + (q - b0) * s)(x, b[0]); Y = (lambda y0, b1: lambda q: y0 + (q - b1) * s)(y, b[1])
        o += PD.piece_svg(pc, X, Y, s, label=True, size=size, lw=0.3, text_mm=1.2)
        x += w + 6; rowh = max(rowh, h)
    cairosvg.svg2png(bytestring=doc(o).encode(), write_to=path, output_width=2400)

if __name__ == "__main__":
    a = sys.argv[1:] or ["qa"]
    if "qa" in a:
        for sz in FL.SIZES:
            bad = [c for c in FL.shape_checks(sz) if not c[1]]; meas, walks, _ = FL.measure(sz); ch = FL.chart()
            dev = {k: round(meas[k]/10 - ch[k][2][FL.SIZES.index(sz)], 2) for k in ch}
            print(sz, "chart", "pass" if all(abs(dev[k]) <= ch[k][3] for k in ch) else dev, "shape", "pass" if not bad else bad,
                  "walks", "pass" if all(tl is None or abs(p - q) <= tl for _, p, q, tl in walks) else "CHECK")
    e = emb() if ("dxf" in a or "pdf" in a) else False
    if "dxf" in a:
        for sz in FL.SIZES: PO.write_dxf([sz], f"{OUTD}/{STYLE}_pattern_{sz}.dxf", blk=FL, style=STYLE, emb=e)
        PO.write_dxf(FL.SIZES, f"{OUTD}/{STYLE}_pattern_ALL-SIZES.dxf", blk=FL, style=STYLE, emb=e); print("dxf ok, emb marks", e)
    if "pdf" in a:
        PO.plot_pdf("M", f"{OUTD}/{STYLE}_pattern_M_1to1_PLOT.pdf", blk=FL, style=STYLE, emb=e); print("pdf ok")
    if "png" in a: overview(); print("png ok")
