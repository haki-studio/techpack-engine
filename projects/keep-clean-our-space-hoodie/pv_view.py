"""Rev K layout views from the art pickle: each piece with its cut line, keep-outs, hoop cells (numbered) and the art.
usage: python3 pv_view.py [SIZE] [allover|zoned] -> out/pv/<SIZE>/layout_<tag>.png + layout_<tag>_<piece>.svg (pack pages)"""
import sys, pickle, json
import cairosvg
import kccore   # registers the KCOS thread colours in motifs2.HEX
from render import geom_to_path, f
from motifs2 import HEX
import pv_block as B

SIZE = next((a for a in sys.argv[1:] if a in B.CHART), "M")
TAG = "zoned" if "zoned" in sys.argv else "allover"
OUT = f"out/pv/{SIZE}"
A = pickle.load(open(f"{OUT}/art_{TAG}.pkl", "rb"))
ORDER = ("HR", "BK", "HL", "SR", "FR", "SL", "PK")
CELL = "#2F9BFF"

def piece_svg(P, pad=30, label=True, cells=True):
    g = A["cut"][P]; x0, y0, x1, y1 = g.bounds
    x0 -= pad; y0 -= pad; x1 += pad; y1 += pad
    o = [f'<rect x="{f(x0)}" y="{f(y0)}" width="{f(x1-x0)}" height="{f(y1-y0)}" fill="#ffffff"/>',
         f'<path d="{geom_to_path(g)}" fill="#1d1f24" stroke="#888" stroke-width="1"/>']
    if P == "FR": o.append(f'<path d="{geom_to_path(A["pocket_fp"])}" fill="none" stroke="#9a9a9a" stroke-width="1.2" stroke-dasharray="6 4"/>')
    o.append(f'<path d="{geom_to_path(A["allowed"][P])}" fill="none" stroke="#55606e" stroke-width="0.6" stroke-dasharray="3 3"/>') if not A["allowed"][P].is_empty else None
    for r in sorted(A["items"][P], key=lambda r: r["z"]):
        o.append(f'<path d="{geom_to_path(r["geom"])}" fill="{HEX.get(r["col"], "#ffffff")}"/>')
    if cells:
        for i, c in enumerate(A["plan"][P]):
            a, b, cc, d = c["box"]
            o.append(f'<rect x="{f(a)}" y="{f(b)}" width="{f(cc-a)}" height="{f(d-b)}" fill="none" stroke="{CELL}" stroke-width="2.2"/>')
            if label: o.append(f'<text x="{f(a+6)}" y="{f(b+22)}" font-family="Noto Sans" font-size="20" font-weight="700" fill="{CELL}">{B.hoop_name(P, i, len(A["plan"][P]))}</text>')
    return o, (x0, y0, x1 - x0, y1 - y0)

def page_png():
    W = 0; rows = [("HR", "BK", "HL"), ("SR", "FR", "SL"), ("PK",)]; parts = []; y = 0
    for row in rows:
        x = 0; h = 0
        for P in row:
            o, (bx, by, bw, bh) = piece_svg(P)
            parts.append(f'<g transform="translate({f(x-bx)} {f(y-by)})">' + "".join(o) + "</g>")
            x += bw + 20; h = max(h, bh)
        W = max(W, x); y += h + 20
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {f(W)} {f(y)}" width="{f(W)}" height="{f(y)}"><rect width="100%" height="100%" fill="#fff"/>' + "".join(parts) + "</svg>"
    cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{OUT}/layout_{TAG}.png", output_width=2400)

if __name__ == "__main__":
    page_png(); print(f"{OUT}/layout_{TAG}.png")
