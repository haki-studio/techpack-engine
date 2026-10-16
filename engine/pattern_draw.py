"""SVG drawing of pattern pieces (shared by the overview PNG, the tech-pack pages and the 1:1 PDF)."""
import math
from render import f
import pattern as PT

INK = "#1A1A1A"; RED = "#D0312D"; BLUE = "#0A84FF"; GREY = "#8A8A8A"; EMB = "#C2185B"

def path_d(pts, close=True):
    return "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts) + (" Z" if close else "")

def piece_svg(pc, X, Y, s, label=True, size="M", emb=(), lw=1.0, fill="#FFFFFF", text_mm=None, emb_fill=True):
    """X, Y map piece coords -> sheet coords; s = sheet units per mm (for stroke/text sizing)."""
    o = []
    cut = PT.cut_poly(pc)
    T = lambda pts: [(X(x), Y(y)) for x, y in pts]
    o.append(f'<path d="{path_d(T(cut.exterior.coords))}" fill="{fill}" stroke="{INK}" stroke-width="{f(0.35*lw)}"/>')
    if not getattr(pc, "inset", 0):
        o.append(f'<path d="{path_d(T(pc.sew()))}" fill="none" stroke="{GREY}" stroke-width="{f(0.18*lw)}" stroke-dasharray="{f(1.2*lw)} {f(0.8*lw)}"/>')
        for a, b in pc.notch_marks():
            o.append(f'<line x1="{f(X(a[0]))}" y1="{f(Y(a[1]))}" x2="{f(X(b[0]))}" y2="{f(Y(b[1]))}" stroke="{INK}" stroke-width="{f(0.35*lw)}"/>')
        for nm, pts in pc.internal:
            col = RED if "FOLD" in nm or "PLEAT" in nm else BLUE
            o.append(f'<path d="{path_d(T(pts), close=False)}" fill="none" stroke="{col}" stroke-width="{f(0.22*lw)}" stroke-dasharray="{f(2*lw)} {f(1*lw)}"/>')
        for x, y in pc.drills:
            r = 1.2 * lw
            o.append(f'<circle cx="{f(X(x))}" cy="{f(Y(y))}" r="{f(r)}" fill="none" stroke="{INK}" stroke-width="{f(0.2*lw)}"/>'
                     f'<path d="M{f(X(x)-r)} {f(Y(y))} H{f(X(x)+r)} M{f(X(x))} {f(Y(y)-r)} V{f(Y(y)+r)}" stroke="{INK}" stroke-width="{f(0.15*lw)}"/>')
    for nm, pts, kind in emb:
        if kind == "outline":
            fl = f'fill="{EMB}" fill-opacity="0.18"' if emb_fill else 'fill="none"'
            o.append(f'<path d="{path_d(T(pts))}" {fl} stroke="{EMB}" stroke-width="{f(0.2*lw)}"/>')
        elif kind == "box":
            o.append(f'<path d="{path_d(T(pts))}" fill="none" stroke="{EMB}" stroke-width="{f(0.25*lw)}" stroke-dasharray="{f(1.5*lw)} {f(0.8*lw)}"/>')
        elif kind == "cross":
            (x, y), = pts; r = 3.0 * lw
            o.append(f'<path d="M{f(X(x)-r)} {f(Y(y))} H{f(X(x)+r)} M{f(X(x))} {f(Y(y)-r)} V{f(Y(y)+r)}" stroke="{EMB}" stroke-width="{f(0.3*lw)}"/>')
        elif kind == "line":
            o.append(f'<path d="{path_d(T(pts), close=False)}" fill="none" stroke="{EMB}" stroke-width="{f(0.25*lw)}" stroke-dasharray="{f(0.8*lw)} {f(0.8*lw)}"/>')
    # grain line with arrows
    (gx0, gy0), (gx1, gy1) = pc.grain
    ax0, ay0, ax1, ay1 = X(gx0), Y(gy0), X(gx1), Y(gy1)
    L = math.hypot(ax1 - ax0, ay1 - ay0) or 1; ux, uy = (ax1 - ax0)/L, (ay1 - ay0)/L; ah = 2.2 * lw
    o.append(f'<line x1="{f(ax0)}" y1="{f(ay0)}" x2="{f(ax1)}" y2="{f(ay1)}" stroke="{INK}" stroke-width="{f(0.25*lw)}"/>')
    for (px, py), sg in (((ax0, ay0), 1), ((ax1, ay1), -1)):
        o.append(f'<path d="M{f(px)} {f(py)} L{f(px + sg*(ux*ah) - uy*ah*0.45)} {f(py + sg*(uy*ah) + ux*ah*0.45)} '
                 f'M{f(px)} {f(py)} L{f(px + sg*(ux*ah) + uy*ah*0.45)} {f(py + sg*(uy*ah) - ux*ah*0.45)}" stroke="{INK}" stroke-width="{f(0.25*lw)}" fill="none"/>')
    if label:
        c = cut.representative_point() if pc.code not in ("B01", "L02") else None
        cx, cy = (X(c.x), Y(c.y)) if c else (X(0), Y(pc.grain[0][1] + 140))
        tm = text_mm or 3.0
        lines = [(pc.code + "  " + pc.name, 700), (f"size {size} · cut {pc.qty}", 400), (pc.material, 400)]
        if pc.fuse: lines.append(("+ fuse", 600))
        for i, (tx, w) in enumerate(lines):
            o.append(f'<text x="{f(cx)}" y="{f(cy + i*tm*1.25)}" font-family="Source Sans 3, Helvetica" font-size="{f(tm)}" font-weight="{w}" text-anchor="middle" fill="{INK}">{tx.replace("&", "+")}</text>')
    return o
