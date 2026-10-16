"""Shared spec-sheet helpers (A4 landscape, mm)."""
import base64, io
from PIL import Image
from render import f, geom_to_path
from motifs2 import HEX

SW, SH = 297.0, 210.0
FONT = "Noto Sans CJK JP"
INK, MUTED, RED, ORANGE, GUIDE, GREEN = "#1A1A1A", "#6B6B6B", "#B3261E", "#C25000", "#0A84D6", "#1E8E3E"

def esc(s): return str(s).replace("&", "+").replace("<", "‹").replace(">", "›")

def t(x, y, s, size=2.4, w=400, fill=INK, anchor="start"):
    return (f'<text x="{f(x)}" y="{f(y)}" font-family="{FONT}" font-size="{size}" font-weight="{w}" '
            f'fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>')

def dim_h(x1, x2, y, label, size=2.2, tick=1.3, col=INK):
    return (f'<g stroke="{col}" stroke-width="0.18"><line x1="{f(x1)}" y1="{f(y)}" x2="{f(x2)}" y2="{f(y)}"/>'
            f'<line x1="{f(x1)}" y1="{f(y-tick)}" x2="{f(x1)}" y2="{f(y+tick)}"/>'
            f'<line x1="{f(x2)}" y1="{f(y-tick)}" x2="{f(x2)}" y2="{f(y+tick)}"/></g>'
            + t((x1 + x2) / 2, y - 1.1, label, size, 600, col, "middle"))

def dim_v(y1, y2, x, label, size=2.2, tick=1.3, col=INK, side=-1):
    cy = (y1 + y2) / 2; tx = x + side * 1.4
    return (f'<g stroke="{col}" stroke-width="0.18"><line x1="{f(x)}" y1="{f(y1)}" x2="{f(x)}" y2="{f(y2)}"/>'
            f'<line x1="{f(x-tick)}" y1="{f(y1)}" x2="{f(x+tick)}" y2="{f(y1)}"/>'
            f'<line x1="{f(x-tick)}" y1="{f(y2)}" x2="{f(x+tick)}" y2="{f(y2)}"/></g>'
            f'<text x="{f(tx)}" y="{f(cy)}" font-family="{FONT}" font-size="{size}" font-weight="600" fill="{col}" '
            f'text-anchor="middle" transform="rotate(-90 {f(tx)} {f(cy)})">{esc(label)}</text>')

def header(title, sub, page=None):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>',
         t(12, 16, title, 4.8, 700), t(12, 22, sub, 2.3, 400, MUTED),
         f'<line x1="12" y1="25.5" x2="{SW-12}" y2="25.5" stroke="{INK}" stroke-width="0.3"/>']
    if page: o.append(t(SW - 12, 16, page, 2.4, 600, MUTED, "end"))
    o.append(t(SW - 12, SH - 6, "HAKI STUDIOS · plum + pine work jacket · Rev A · 16 Oct 2026", 1.9, 400, MUTED, "end"))
    return o

def swatch(x, y, col, w=5, h=3):
    return f'<rect x="{f(x)}" y="{f(y-h+0.6)}" width="{w}" height="{h}" rx="0.4" fill="{HEX[col]}" stroke="#BDBDBD" stroke-width="0.15"/>'

def embed(path, crop=None, w_mm=60, x=0, y=0, quality=88):
    im = Image.open(path).convert("RGB")
    if crop: im = im.crop(crop)
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=quality)
    h_mm = w_mm * im.height / im.width
    return (f'<image x="{f(x)}" y="{f(y)}" width="{f(w_mm)}" height="{f(h_mm)}" '
            f'href="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"/>'), h_mm

def embed_svg_png(png_path, x, y, w_mm, h_mm=None):
    im = Image.open(png_path); h = h_mm or w_mm * im.height / im.width
    buf = io.BytesIO(); im.convert("RGB").save(buf, "JPEG", quality=92)
    return (f'<image x="{f(x)}" y="{f(y)}" width="{f(w_mm)}" height="{f(h)}" '
            f'href="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"/>'), h

def doc(o):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{SW}mm" height="{SH}mm" viewBox="0 0 {SW} {SH}">'
            + "\n".join(o) + "</svg>")
