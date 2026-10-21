"""Konpeito size labels (founder review 20 Oct, item 14): waist-size NUMBERS, optic white in Neue Metana ExtraBold on jet
black, LOOP label (folded strip, open loop) so the hang-tag string ties through it. The main label is sewn down on all
four sides; the hang tag never hangs from it.

Flat artwork (1 SVG unit = 1 mm): strip W x L, folded at the middle; both ends go into the waistband seam (inside CB,
left of the main label). The number is woven on both halves (the back half turned 180 deg, so both faces read upright when
the loop hangs). Text is converted to outlines (no font needed at the label maker).
Writes out/labels/HAKI_KJ_size-label_<size>.svg + .pdf (1:1, dimensions) and returns the strip geometry for the pages."""
import os
import cairosvg
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

FONT_PATHS = ["/mnt/c/Users/devin/AppData/Local/Microsoft/Windows/Fonts/NeueMetana-ExtraBold.otf", "out/fonts/NeueMetana-ExtraBold.otf"]
SIZE_RUN = ["26", "28", "29", "30", "31", "32", "33", "34", "36", "38", "40"]     # founder 20 Oct
W, L = 15.0, 60.0          # flat strip mm  [proposed — confirm]: loop 25 mm long + 5 mm seam allowance each end
SA = 5.0                   # seam allowance at each end (sewn into the waistband seam)
CAP = 5.0                  # number height mm (max; narrowed so the number keeps 2 mm each side)
MAXW = W - 4.0
BLACK, WHITE = "#0A0A0A", "#FFFFFF"
_font = None

def font():
    global _font
    if _font is None:
        p = next(p for p in FONT_PATHS if os.path.exists(p))
        _font = TTFont(p)
    return _font

def text_path(s, cx, cy, h, rot180=False):
    """outline path of string s, its digit height = h mm, centred on (cx, cy) mm (y down)."""
    F = font(); gs = F.getGlyphSet(); cmap = F.getBestCmap()
    names = [cmap[ord(c)] for c in s]
    adv = [F["hmtx"][n][0] for n in names]
    bp = BoundsPen(gs); x = 0
    for n, a in zip(names, adv):
        tp = TransformPen(bp, (1, 0, 0, 1, x, 0)); gs[n].draw(tp); x += a
    x0, y0, x1, y1 = bp.bounds
    k = min(h / (y1 - y0), MAXW / (x1 - x0))
    # font units (y up) -> mm (y down), centred
    if not rot180:
        T = (k, 0, 0, -k, cx - (x0 + x1) / 2 * k, cy + (y0 + y1) / 2 * k)
    else:
        T = (-k, 0, 0, k, cx + (x0 + x1) / 2 * k, cy - (y0 + y1) / 2 * k)
    sp = SVGPathPen(gs); x = 0
    for n, a in zip(names, adv):
        tp = TransformPen(sp, (T[0], T[1], T[2], T[3], T[4] + T[0] * x, T[5] + T[1] * x)); gs[n].draw(tp); x += a
    return sp.getCommands(), (x1 - x0) * k

def strip(size, ox=0.0, oy=0.0, guides=True):
    """SVG elements of one flat size label at (ox, oy) mm."""
    o = [f'<rect x="{ox}" y="{oy}" width="{W}" height="{L}" fill="{BLACK}"/>']
    half = (L - 2 * SA) / 2
    d1, tw = text_path(size, ox + W / 2, oy + SA + half / 2, CAP)
    d2, _ = text_path(size, ox + W / 2, oy + L - SA - half / 2, CAP, rot180=True)
    o += [f'<path d="{d1}" fill="{WHITE}"/>', f'<path d="{d2}" fill="{WHITE}"/>']
    if guides:
        g = "#E0004D"
        for yy in (oy + SA, oy + L - SA):
            o.append(f'<line x1="{ox - 1.5}" y1="{yy}" x2="{ox + W + 1.5}" y2="{yy}" stroke="{g}" stroke-width="0.2" stroke-dasharray="1 0.6"/>')
        o.append(f'<line x1="{ox - 1.5}" y1="{oy + L / 2}" x2="{ox + W + 1.5}" y2="{oy + L / 2}" stroke="#1F5FA8" stroke-width="0.2" stroke-dasharray="0.4 0.4"/>')
    return o, tw

def label_svg(size):
    pw, ph = 100.0, 80.0; ox, oy = 14.0, 10.0
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{pw}mm" height="{ph}mm" viewBox="0 0 {pw} {ph}">',
         f'<rect width="{pw}" height="{ph}" fill="#FFFFFF"/>']
    s, tw = strip(size, ox, oy)
    o += s
    fs = 'font-family="DejaVu Sans, Arial" fill="#333333"'
    o.append(f'<text x="{ox}" y="{oy - 4}" font-size="2.6" font-weight="700" {fs}>SIZE {size} — loop label, flat (1:1)</text>')
    # dimensions
    o.append(f'<line x1="{ox}" y1="{oy + L + 3}" x2="{ox + W}" y2="{oy + L + 3}" stroke="#333" stroke-width="0.2"/>')
    o.append(f'<text x="{ox + W / 2}" y="{oy + L + 6.5}" font-size="2.4" text-anchor="middle" {fs}>{W:g} mm</text>')
    o.append(f'<line x1="{ox - 4}" y1="{oy}" x2="{ox - 4}" y2="{oy + L}" stroke="#333" stroke-width="0.2"/>')
    o.append(f'<text x="{ox - 5.5}" y="{oy + L / 2}" font-size="2.4" text-anchor="middle" transform="rotate(-90 {ox - 5.5} {oy + L / 2})" {fs}>{L:g} mm flat</text>')
    tx = ox + W + 4
    for i, ln in enumerate([f"red dashed = seam line ({SA:g} mm each end,", "  both ends sewn into the waistband seam)",
                            "blue dotted = fold (bottom of the loop)", f"loop when folded: {W:g} × {(L - 2 * SA) / 2:g} mm, open",
                            f"number: Neue Metana ExtraBold,", f"  {CAP:g} mm max height, optic white on jet black,", "  outlined; back half turned 180°",
                            "damask woven (as HI); dimensions", "  [proposed — confirm]",
                            "hang-tag string ties through the loop"]):
        o.append(f'<text x="{tx}" y="{oy + 3 + i * 3.6}" font-size="2.2" {fs}>{ln}</text>')
    o.append("</svg>")
    return "\n".join(o)

def build(out="out/labels"):
    os.makedirs(out, exist_ok=True)
    files = []
    for s in SIZE_RUN:
        sv = label_svg(s)
        p = f"{out}/HAKI_KJ_size-label_{s}"
        open(p + ".svg", "w").write(sv)
        cairosvg.svg2pdf(bytestring=sv.encode(), write_to=p + ".pdf")
        files += [p + ".svg", p + ".pdf"]
    cairosvg.svg2png(bytestring=label_svg("32").encode(), write_to=f"{out}/prev_size-label_32.png", output_width=700)
    return files

if __name__ == "__main__":
    print(build())
