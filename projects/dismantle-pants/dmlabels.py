"""Dismantle Pants size labels — copied from projects/konpeito-jeans/kjlabels.py (same HI centrefold size label, founder 20 Oct for Konpeito): the HI size label exactly (HI tech pack p. 10, "Size Label" column):
damask woven, CENTREFOLD, 30 x 10 mm flat = 5 mm seam allowance | 10 mm | fold | 10 mm face with the size | 5 mm seam
allowance; folding lines dashed, jet-black ground with a dark-red outline as drawn by HI. Our change: the size text is the
waist number (26 ... 40) in Neue Metana ExtraBold, optic white. Folded, both ends go into the waist seam inside CB and the
label stays a small loop: the hang-tag string ties through it.
Writes out/labels/HAKI_DM_size-label_<size>.svg + .pdf (1:1 with dimensions); text outlined (no font needed)."""
import os
import cairosvg
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.boundsPen import BoundsPen

FONT_PATHS = ["/mnt/c/Users/devin/AppData/Local/Microsoft/Windows/Fonts/NeueMetana-ExtraBold.otf", "out/fonts/NeueMetana-ExtraBold.otf"]
SIZE_RUN = ["26", "28", "30", "32", "34", "36", "38", "40"]     # HI published size chart (PLM pipeline.size_charts 9a469aee-…) [proposed — confirm run]
W, H = 30.0, 10.0          # flat label mm (HI size label: 0.5 + 2 cm between the folding lines + 0.5, 1 cm tall)
SA = 5.0                   # seam allowance each end (HI: 0.5 cm)
FOLD = 15.0                # centrefold
FACE = (15.0, 25.0)        # the face that shows when folded: size text centred on it (as HI "XS")
CAP = 3.0                  # number height mm [proposed — confirm] (HI "XS" ~2.5-3 mm)
MAXW = 8.0
EDGE = "#7A1F2B"           # HI drawing's dark-red outline + folding lines (drawing convention, not woven)
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

def label(size, ox=0.0, oy=0.0, s=1.0, guides=True):
    """SVG elements of one flat size label (HI layout) at (ox, oy) mm, drawn at scale s."""
    o = [f'<g transform="translate({ox} {oy}) scale({s})">',
         f'<rect x="0" y="0" width="{W}" height="{H}" fill="{BLACK}"' + (f' stroke="{EDGE}" stroke-width="0.35"' if guides else '') + '/>']
    d, tw = text_path(size, (FACE[0] + FACE[1]) / 2, H / 2, CAP)
    o.append(f'<path d="{d}" fill="{WHITE}"/>')
    if guides:
        for xx in (SA, W - SA):
            o.append(f'<line x1="{xx}" y1="0" x2="{xx}" y2="{H}" stroke="{EDGE}" stroke-width="0.25" stroke-dasharray="0.9 0.6"/>')
        o.append(f'<line x1="{FOLD}" y1="0" x2="{FOLD}" y2="{H}" stroke="#6E6E6E" stroke-width="0.2"/>')
    o.append("</g>")
    return o, tw

def label_svg(size):
    pw, ph = 100.0, 45.0; ox, oy = 14.0, 14.0
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{pw}mm" height="{ph}mm" viewBox="0 0 {pw} {ph}">',
         f'<rect width="{pw}" height="{ph}" fill="#FFFFFF"/>']
    l_, tw = label(size, ox, oy); o += l_
    fs = 'font-family="DejaVu Sans, Arial" fill="#333333"'
    o.append(f'<text x="{ox}" y="6" font-size="2.6" font-weight="700" {fs}>SIZE {size} — size label, flat (1:1), damask woven, centrefold</text>')
    dm = 'stroke="#7A1F2B" stroke-width="0.2"'
    o.append(f'<line x1="{ox}" y1="{oy - 3}" x2="{ox + SA}" y2="{oy - 3}" {dm}/><line x1="{ox + SA}" y1="{oy - 3}" x2="{ox + W - SA}" y2="{oy - 3}" {dm}/>')
    for xx in (ox, ox + SA, ox + W - SA): o.append(f'<line x1="{xx}" y1="{oy - 4.2}" x2="{xx}" y2="{oy - 1.8}" {dm}/>')
    o.append(f'<text x="{ox + SA / 2}" y="{oy - 4.2}" font-size="2" text-anchor="middle" {fs}>0.5 cm</text>')
    o.append(f'<text x="{ox + W / 2}" y="{oy - 4.2}" font-size="2" text-anchor="middle" {fs}>2 cm</text>')
    o.append(f'<line x1="{ox - 3}" y1="{oy}" x2="{ox - 3}" y2="{oy + H}" {dm}/>')
    o.append(f'<text x="{ox - 4.5}" y="{oy + H / 2 + 0.7}" font-size="2" text-anchor="end" {fs}>1 cm</text>')
    o.append(f'<text x="{ox + FOLD}" y="{oy + H + 4}" font-size="2" text-anchor="middle" {fs}>folding lines</text>')
    tx = ox + W + 6
    for i, ln in enumerate(["as the HI size label: 30 x 10 mm flat,", "5 mm seam allowance each end (dashed),",
                            "centrefold (grey line); folded, the face", "15-25 mm shows the size",
                            f"number: Neue Metana ExtraBold, {CAP:g} mm,", "optic white on jet black, outlined",
                            "[proposed — confirm number height]", "ends sewn into the waist seam inside CB:",
                            "the hang-tag string ties through the loop"]):
        o.append(f'<text x="{tx}" y="{oy - 2 + i * 3.4}" font-size="2.1" {fs}>{ln}</text>')
    o.append("</svg>")
    return "\n".join(o)

def build(out="out/labels"):
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):                  # the Rev B 15 x 60 strips are withdrawn (founder 20 Oct)
        if f.startswith(("HAKI_DM_size-label_", "prev_size-label")): os.remove(os.path.join(out, f))
    files = []
    for s in SIZE_RUN:
        sv = label_svg(s)
        p = f"{out}/HAKI_DM_size-label_{s}"
        open(p + ".svg", "w").write(sv)
        cairosvg.svg2pdf(bytestring=sv.encode(), write_to=p + ".pdf")
        files += [p + ".svg", p + ".pdf"]
    cairosvg.svg2png(bytestring=label_svg("32").encode(), write_to=f"{out}/prev_size-label_32.png", output_width=700)
    return files

if __name__ == "__main__":
    print(build())
