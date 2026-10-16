"""Haki — konpeito coin pocket: production art generator.
All geometry in millimetres (SVG user unit = 1 mm)."""
import math
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen

# ---------------------------------------------------------------- spec
W, H = 76.0, 56.0          # coin pocket finished size
EDGE = 2.0                 # satin edge (heat-cut), red
BAND = 4.5                 # tatami band carrying motifs, red
BORDER = EDGE + BAND       # 6.5 total — SHARED with waistband patch
CORNER_R = 2.5
FLOWER_D = 4.0
DOT_D = 1.5
PITCH_TARGET = 5.8         # flower -> dot spacing (both patches land 5.63–5.96)
RIVET_CAP = 8.0

C = {
    "red":        "#C8162B",
    "cream":      "#F2E9D8",
    "white":      "#FBF8F1",
    "pink":       "#EF7FAC", "pink_hi":   "#F8B5CF",
    "yellow":     "#F5C230", "yellow_hi": "#FCE27E",
    "blue":       "#35A6D6", "blue_hi":   "#8ED2EE",
}

def f(x):
    return f"{x:.3f}".rstrip("0").rstrip(".")

# ---------------------------------------------------------------- motifs
def border_flower(cx, cy, d=FLOWER_D, color=C["white"]):
    """5-petal blossom. Petals are separate shapes so red shows between them
    (reads as the gap between satin petals) and a tiny red centre."""
    out = []
    pl, pw = d * 0.46, d * 0.34      # petal length / width
    rr = d * 0.27                    # petal centre radius from flower centre
    for k in range(5):
        a = -90 + k * 72
        px = cx + rr * math.cos(math.radians(a))
        py = cy + rr * math.sin(math.radians(a))
        out.append(f'<ellipse cx="{f(px)}" cy="{f(py)}" rx="{f(pw/2)}" ry="{f(pl/2)}" '
                   f'transform="rotate({a+90:.1f} {f(px)} {f(py)})" fill="{color}"/>')
    out.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(d*0.09)}" fill="{C["red"]}"/>')
    return "\n".join(out)

def dot(cx, cy, d=DOT_D, color=C["white"]):
    return f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(d/2)}" fill="{color}"/>'

def konpeito_path(cx, cy, R, rot=0.0, n=6, steps=240):
    """Rounded 6-lobed candy star: broad round lobes, notched valleys."""
    pts = []
    for i in range(steps):
        t = 2 * math.pi * i / steps
        r = R * (0.70 + 0.30 * ((1 + math.cos(n * t)) / 2) ** 0.5)
        a = t + math.radians(rot)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts) + " Z"

def konpeito(cx, cy, d, base, hi, rot=0.0, sparkles=True):
    R = d / 2
    g = [f'<path d="{konpeito_path(cx, cy, R, rot - 90)}" fill="{C[base]}"/>',
         # lighter inner facet, nudged up-left = highlight colour stop
         f'<path d="{konpeito_path(cx - R*0.06, cy - R*0.08, R*0.52, rot - 90)}" fill="{C[hi]}"/>']
    if sparkles:
        s = max(1.1, d * 0.085)      # never below 1.1 mm — stitchable
        for ang, rad in ((-40, 0.55), (150, 0.50), (70, 0.60)):
            x = cx + R * rad * math.cos(math.radians(ang + rot))
            y = cy + R * rad * math.sin(math.radians(ang + rot))
            g.append(dot(x, y, s, C["white"]))
    return "\n".join(g)

# ---------------------------------------------------------------- border
def side_positions(a, b, pitch=PITCH_TARGET):
    L = b - a
    n = max(2, round(L / pitch))
    if n % 2:  # flower at both ends => even number of intervals
        n = n + 1 if abs(L / (n + 1) - pitch) < abs(L / (n - 1) - pitch) else n - 1
    return [a + L * i / n for i in range(n + 1)], L / n

def border_svg(w, h, rivet_corners=("tl", "tr")):
    c = EDGE + BAND / 2           # motif centreline inset
    xs, px = side_positions(c, w - c)
    ys, py = side_positions(c, h - c)
    motifs = []
    def place(x, y, i, corner=None):
        if corner in rivet_corners:
            return                # rivet keep-out: plain red
        motifs.append(border_flower(x, y) if i % 2 == 0 else dot(x, y))
    for i, x in enumerate(xs):
        place(x, c, i, "tl" if i == 0 else "tr" if i == len(xs) - 1 else None)
        place(x, h - c, i, "bl" if i == 0 else "br" if i == len(xs) - 1 else None)
    for i, y in enumerate(ys[1:-1], start=1):
        place(c, y, i)
        place(w - c, y, i)
    return "\n".join(motifs), (px, py)

# ---------------------------------------------------------------- lettering
FONT = TTFont("/home/claude/work/zen.ttf")
GS = FONT.getGlyphSet()
CMAP = FONT.getBestCmap()
UPM = FONT["head"].unitsPerEm

def glyph_bounds(ch):
    bp = BoundsPen(GS); GS[CMAP[ord(ch)]].draw(bp); return bp.bounds

def lettering(text, cx, cy, cap_h, gap, jitter):
    """Outlined, slightly hand-set kana (per-glyph tilt + baseline wobble)."""
    bounds = [glyph_bounds(ch) for ch in text]
    gh = max(b[3] - b[1] for b in bounds)
    s = cap_h / gh
    widths = [(b[2] - b[0]) * s for b in bounds]
    total = sum(widths) + gap * (len(text) - 1)
    x = cx - total / 2
    paths = []
    for ch, b, wdt, (rot, dy) in zip(text, bounds, widths, jitter):
        gcx = x + wdt / 2
        gcy = cy + dy
        # font y-up -> svg y-down; centre each glyph on (gcx,gcy) then tilt
        mx = (b[0] + b[2]) / 2; my = (b[1] + b[3]) / 2
        pen = SVGPathPen(GS)
        tp = TransformPen(pen, (s, 0, 0, -s, gcx - mx * s, gcy + my * s))
        GS[CMAP[ord(ch)]].draw(tp)
        paths.append(f'<path d="{pen.getCommands()}" fill="{C["red"]}" '
                     f'transform="rotate({rot} {f(gcx)} {f(gcy)})"/>')
        x += wdt + gap
    return "\n".join(paths), total, s

# ---------------------------------------------------------------- coin pocket
def coin_pocket(guides=False):
    inner_w, inner_h = W - 2 * BORDER, H - 2 * BORDER
    motifs, pitch = border_svg(W, H)
    text, text_w, _ = lettering(
        "こんぺいとう", W / 2, BORDER + 11.2, cap_h=10.5, gap=0.3,
        jitter=[(-4, -0.3), (3, 0.35), (-2, -0.15), (3.5, 0.3), (-3, -0.25), (2.5, 0.2)])
    ky = BORDER + 28.6
    trio = "\n".join([
        konpeito(W / 2 - 19.0, ky + 0.6, 13.0, "pink", "pink_hi", rot=4),
        konpeito(W / 2,        ky - 0.4, 13.0, "yellow", "yellow_hi", rot=-6),
        konpeito(W / 2 + 19.0, ky + 0.8, 13.0, "blue", "blue_hi", rot=8),
    ])
    accents = "\n".join(dot(x, y, 2.0, C["red"]) for x, y in [
        (BORDER + 3.4, ky + 3.2), (BORDER + 5.4, ky + 6.2),
        (W - BORDER - 5.2, ky + 4.6), (W - BORDER - 3.2, ky + 7.4), (BORDER + 4.4, ky - 5.0)])
    g = f"""
<g id="01_edge_satin_and_band_RED">
  <rect x="0" y="0" width="{f(W)}" height="{f(H)}" rx="{CORNER_R}" fill="{C['red']}"/>
</g>
<g id="02_field_CREAM">
  <rect x="{BORDER}" y="{BORDER}" width="{f(inner_w)}" height="{f(inner_h)}" fill="{C['cream']}"/>
</g>
<g id="03_border_motifs_WHITE">
{motifs}
</g>
<g id="04_lettering_RED">
{text}
</g>
<g id="05_konpeito">
{trio}
</g>
<g id="06_accent_dots_RED">
{accents}
</g>"""
    if guides:
        g += guide_layer()
    return g, pitch, text_w

def guide_layer():
    hw = 0.12
    c = EDGE + BAND / 2
    return f"""
<g id="99_GUIDES_do_not_stitch" fill="none" stroke="#00A3FF" stroke-width="{hw}">
  <rect x="{EDGE}" y="{EDGE}" width="{f(W-2*EDGE)}" height="{f(H-2*EDGE)}" rx="0.6" stroke-dasharray="0.8 0.5"/>
  <circle cx="{f(c)}" cy="{f(c)}" r="{RIVET_CAP/2}" stroke="#FF6A00" stroke-dasharray="0.6 0.4"/>
  <circle cx="{f(W-c)}" cy="{f(c)}" r="{RIVET_CAP/2}" stroke="#FF6A00" stroke-dasharray="0.6 0.4"/>
  <path d="M{f(c-1)} {f(c)} h2 M{f(c)} {f(c-1)} v2 M{f(W-c-1)} {f(c)} h2 M{f(W-c)} {f(c-1)} v2" stroke="#FF6A00"/>
</g>"""

def svg_doc(w, h, body, extra_attrs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{f(w)}mm" height="{f(h)}mm" '
            f'viewBox="0 0 {f(w)} {f(h)}" {extra_attrs}>\n{body}\n</svg>\n')

# ---------------------------------------------------------------- facing konpeito
FW, FH = 66.0, 16.0
POCKET_LINE = 9.5   # where the coin pocket's top edge lands on this piece

def facing():
    back = [(13, 6.6, 7.5, "pink", "pink_hi", 10), (33.5, 6.2, 7.5, "pink", "pink_hi", -12),
            (45, 7.0, 7.0, "pink", "pink_hi", 18)]
    front = [(6.5, 7.6, 10.5, "yellow", "yellow_hi", 5), (17.5, 6.4, 10.5, "blue", "blue_hi", -8),
             (28.5, 7.8, 10.5, "yellow", "yellow_hi", 12), (39.5, 6.6, 10.5, "blue", "blue_hi", -4),
             (50.0, 7.4, 10.5, "yellow", "yellow_hi", 9), (60.0, 8.0, 10.0, "pink", "pink_hi", -10)]
    body = ['<g id="F1_back_row_stitch_first">']
    body += [konpeito(x, y, d, b, h, r, sparkles=False) for x, y, d, b, h, r in back]
    body += ['</g>', '<g id="F2_front_row">']
    body += [konpeito(x, y, d, b, h, r) for x, y, d, b, h, r in front]
    body += ['</g>']
    return "\n".join(body)

def facing_guides():
    return (f'<g id="99_GUIDES_do_not_stitch"><line x1="-3" y1="{POCKET_LINE}" x2="{FW+3}" y2="{POCKET_LINE}" '
            f'stroke="#00A3FF" stroke-width="0.15" stroke-dasharray="1 0.6"/></g>')

if __name__ == "__main__":
    art, pitch, tw = coin_pocket()
    open("out/HAKI_coin-pocket_konpeito_ART.svg", "w").write(svg_doc(W, H, art))
    art_g, _, _ = coin_pocket(guides=True)
    open("out/HAKI_coin-pocket_konpeito_ART+guides.svg", "w").write(svg_doc(W, H, art_g))
    open("out/HAKI_facing_konpeito_ART.svg", "w").write(
        svg_doc(FW, FH, facing(), 'overflow="visible"'))
    print("border pitch x/y mm:", [round(p, 2) for p in pitch], "text width mm:", round(tw, 2))
