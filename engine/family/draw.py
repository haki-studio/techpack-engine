"""Small SVG helpers for family pages (house style = engine/sheet.py: A4 landscape, mm)."""
import math
from render import f
from sheet import t, esc, INK, MUTED, RED, GREEN, FONT
from .spec import V, TAG, is_prop, val

PROP = "#8A5A00"          # amber — every proposed value (LESSONS C6)
ALT = "#F5F2EC"
GUIDE = "#0A84D6"


def vt(x, y, v, size=1.8, w=400, fill=INK, anchor="start", tag=True):
    """text for a value: amber + '[proposed — confirm]' when proposed"""
    if is_prop(v): return t(x, y, v.text(tag), size, max(w, 600), PROP, anchor)
    return t(x, y, val(v), size, w, fill, anchor)


def wrap(s, width_mm, size):
    """greedy word wrap by an average glyph width (DejaVu / Noto ~0.56 em)"""
    n = max(8, int(width_mm / (size * 0.56)))
    out, line = [], ""
    for w in str(s).split():
        if line and len(line) + 1 + len(w) > n: out.append(line); line = w
        else: line = (line + " " + w).strip()
    if line: out.append(line)
    return out or [""]


def para(o, x, y, s, width_mm, size=1.7, lh=None, w=400, fill=INK):
    """wrapped paragraph; returns the y below it"""
    lh = lh or size * 1.45
    for i, l in enumerate(wrap(s, width_mm, size)):
        o.append(t(x, y + i * lh, l, size, w, fill))
    return y + lh * len(wrap(s, width_mm, size))


def vpara(o, x, y, v, width_mm, size=1.7, lh=None, w=400, prefix=""):
    s = prefix + (v.text() if isinstance(v, V) else str(v))
    return para(o, x, y, s, width_mm, size, lh, 600 if is_prop(v) else w, PROP if is_prop(v) else INK)


def path_d(pts, close=True):
    return "M" + " L".join(f"{f(x)},{f(y)}" for x, y in pts) + (" Z" if close else "")


def poly_d(g):
    """shapely (multi)polygon -> path d"""
    polys = getattr(g, "geoms", [g])
    d = []
    for p in polys:
        if p.is_empty or not hasattr(p, "exterior"): continue
        d.append(path_d(list(p.exterior.coords)[:-1]))
        for r in p.interiors: d.append(path_d(list(r.coords)[:-1]))
    return " ".join(d)


def dim(p1, p2, off, label, size=1.8, col=INK, sw=0.16, tick=1.0):
    """aligned dimension p1->p2 (page mm), offset `off` mm to the left of the direction, label centred, rotated"""
    (x1, y1), (x2, y2) = p1, p2
    dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    a1 = (x1 + nx * off, y1 + ny * off); a2 = (x2 + nx * off, y2 + ny * off)
    ang = math.degrees(math.atan2(dy, dx))
    if ang > 90: ang -= 180
    if ang < -90: ang += 180
    mx, my = (a1[0] + a2[0]) / 2 + nx * 1.6 * (1 if off >= 0 else -1), (a1[1] + a2[1]) / 2 + ny * 1.6 * (1 if off >= 0 else -1)
    o = [f'<g stroke="{col}" stroke-width="{sw}">',
         f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(a1[0])}" y2="{f(a1[1])}" stroke-dasharray="0.6 0.5" stroke-width="0.1"/>',
         f'<line x1="{f(x2)}" y1="{f(y2)}" x2="{f(a2[0])}" y2="{f(a2[1])}" stroke-dasharray="0.6 0.5" stroke-width="0.1"/>',
         f'<line x1="{f(a1[0])}" y1="{f(a1[1])}" x2="{f(a2[0])}" y2="{f(a2[1])}"/>']
    for ax, ay in (a1, a2):
        o.append(f'<line x1="{f(ax - nx * tick)}" y1="{f(ay - ny * tick)}" x2="{f(ax + nx * tick)}" y2="{f(ay + ny * tick)}"/>')
    o.append("</g>")
    o.append(f'<text x="{f(mx)}" y="{f(my + size * 0.35)}" font-family="{FONT}" font-size="{size}" font-weight="700" fill="{col}" '
             f'text-anchor="middle" transform="rotate({f(ang)} {f(mx)} {f(my)})">{esc(label)}</text>')
    return "".join(o)


def badge(x, y, n, r=2.0, size=1.8):
    return (f'<circle cx="{f(x)}" cy="{f(y)}" r="{r}" fill="#FFFFFF" stroke="{INK}" stroke-width="0.25"/>'
            + t(x, y + size * 0.35, str(n), size, 700, INK, "middle"))


def ok_text(x, y, ok, size=1.6, yes="pass", no="FAIL"):
    return t(x, y, yes if ok else no, size, 700, GREEN if ok else RED)
