"""Haki — waistband (back) patch: production art. Units = mm.
Shares border spec + thread palette with the coin pocket (build.py)."""
import math
import numpy as np
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
import build as B
from build import f, C

W, H = 80.0, 54.0
BORDER = B.BORDER
FX0, FY0, FX1, FY1 = BORDER, BORDER, W - BORDER, H - BORDER

PAL = dict(C)
PAL.update({"black": "#1C1A1A", "rose": "#E8457A"})

# ------------------------------------------------------------ geometry → svg
def geom_to_path(g):
    polys = [g] if isinstance(g, Polygon) else list(getattr(g, "geoms", []))
    d = []
    for p in polys:
        if p.is_empty:
            continue
        for ring in [p.exterior, *p.interiors]:
            cs = list(ring.coords)
            d.append("M" + " L".join(f"{f(x)} {f(y)}" for x, y in cs[:-1]) + " Z")
    return " ".join(d)

def stroke(pts, w):
    return LineString(pts).buffer(w / 2, cap_style="round", join_style="round", quad_segs=16)

def bez(p0, p1, p2, p3, n=48):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = map(np.array, (p0, p1, p2, p3))
    return ((1-t)**3*p0 + 3*(1-t)**2*t*p1 + 3*(1-t)*t**2*p2 + t**3*p3).tolist()

def catmull(points, n=24, t0=None, t1=None):
    P = [np.array(p, float) for p in points]
    out = []
    for i in range(len(P) - 1):
        a = P[i - 1] if i > 0 else P[0] - (t0 if t0 is not None else P[1] - P[0])
        d = P[i + 2] if i + 2 < len(P) else P[-1] + (t1 if t1 is not None else P[-1] - P[-2])
        b, c = P[i], P[i + 1]
        m1, m2 = (c - a) / 2, (d - b) / 2
        seg = bez(b, b + m1 / 3, c - m2 / 3, c, n)
        out += seg if i == 0 else seg[1:]
    return out

# ------------------------------------------------------------ font outlines
class FlatPen(BasePen):
    def __init__(self, gs):
        super().__init__(gs); self.contours = []; self.cur = []
    def _moveTo(self, p): self.cur = [p]
    def _lineTo(self, p): self.cur.append(p)
    def _curveToOne(self, p1, p2, p3):
        self.cur += bez(self.cur[-1], p1, p2, p3, 12)[1:]
    def _qCurveToOne(self, p1, p2):
        p0 = np.array(self.cur[-1]); p1 = np.array(p1); p2 = np.array(p2)
        for t in np.linspace(0, 1, 10)[1:]:
            self.cur.append(tuple((1-t)**2*p0 + 2*(1-t)*t*p1 + t**2*p2))
    def _closePath(self):
        if len(self.cur) > 2: self.contours.append(self.cur)
        self.cur = []
    _endPath = _closePath

FONTS = {}
def glyph_geom(font_path, ch):
    if font_path not in FONTS:
        tt = TTFont(font_path); FONTS[font_path] = (tt.getGlyphSet(), tt.getBestCmap())
    gs, cmap = FONTS[font_path]
    pen = FlatPen(gs); gs[cmap[ord(ch)]].draw(pen)
    pos, neg = [], []
    for c in pen.contours:
        p = Polygon(c).buffer(0)
        a = sum((x1*y2 - x2*y1) for (x1, y1), (x2, y2) in zip(c, c[1:] + c[:1]))
        (pos if a < 0 else neg).append(p)   # TrueType: outer contours clockwise
    g = unary_union(pos)
    if neg: g = g.difference(unary_union(neg))
    return affinity.scale(g, 1, -1, origin=(0, 0))   # y-down

def set_line(text, font_path, cx, cy, height, gap, jitter, grow, max_w=None, join=0.26):
    """Glyphs scaled so tallest ink = height, emboldened by grow/side, then placed so the
    true outline distance between neighbours = gap (optical kerning, thread-safe)."""
    gl0 = [glyph_geom(font_path, ch) for ch in text]
    hmax = max(g.bounds[3] - g.bounds[1] for g in gl0)
    s = height / hmax
    gl = []
    for g, (rot, dy) in zip(gl0, jitter):
        g = affinity.scale(g, s, s, origin=(0, 0))
        b = g.bounds
        g = affinity.translate(g, -b[0], -(b[1] + b[3]) / 2 + dy)
        g = affinity.rotate(g, rot, origin="centroid")
        if grow: g = g.buffer(grow, join_style="round", quad_segs=12)
        gl.append(g)
    placed = [gl[0]]
    for g in gl[1:]:
        prev = placed[-1]
        lo, hi = prev.bounds[0] - g.bounds[2], prev.bounds[2] - g.bounds[0] + gap + 2
        for _ in range(40):                       # bisection on x offset
            mid = (lo + hi) / 2
            if affinity.translate(g, mid, 0).distance(prev) < gap: lo = mid
            else: hi = mid
        placed.append(affinity.translate(g, hi, 0))
    u = unary_union(placed)
    if join: u = u.buffer(join, join_style="round").buffer(-join, join_style="round")  # join hairline gaps
    u = respace(u)
    u = open_up(u)
    b = u.bounds
    if max_w and (b[2] - b[0]) > max_w:
        return set_line(text, font_path, cx, cy, height * max_w / (b[2] - b[0]) * 0.995, gap, jitter, grow, max_w, join)
    return affinity.translate(u, cx - (b[0] + b[2]) / 2, cy - (b[1] + b[3]) / 2), height

def respace(g, target=0.45, iters=12):
    """Nudge small separate parts (dakuten, dots, short bars) away from neighbours closer
    than target, moving the smaller part along the nearest-point vector."""
    from shapely.ops import nearest_points
    parts = [g] if isinstance(g, Polygon) else list(g.geoms)
    for _ in range(iters):
        moved = False
        for i in range(len(parts)):
            for j in range(len(parts)):
                if i >= j: continue
                d = parts[i].distance(parts[j])
                if 0 < d < target:
                    small, big = (i, j) if parts[i].area < parts[j].area else (j, i)
                    a, b = nearest_points(parts[big], parts[small])
                    v = np.array([b.x - a.x, b.y - a.y]); v = v / (np.linalg.norm(v) or 1)
                    step = (target - d) + 0.01
                    parts[small] = affinity.translate(parts[small], v[0] * step, v[1] * step)
                    moved = True
        if not moved: break
    # boxed-in parts that could not move far enough: slim them (keeps >= ~0.7 mm stroke)
    slim = [0.0] * len(parts)
    for i in range(len(parts)):
        for j in range(len(parts)):
            if i == j: continue
            d = parts[i].distance(parts[j])
            if 0 < d < target and parts[i].area <= parts[j].area:
                slim[i] = max(slim[i], min(0.08, (target - d) / 2 + 0.01))
    parts = [p.buffer(-min(s, max(0.0, (inscribed_d(p) - 0.64) / 2)), join_style="round") if s else p
             for p, s in zip(parts, slim)]
    return unary_union(parts)

def inscribed_d(poly):
    """approx max inscribed circle diameter of a polygon (binary search on negative buffer)"""
    lo, hi = 0.0, 3.0
    for _ in range(18):
        m = (lo + hi) / 2
        if poly.buffer(-m / 2).is_empty: hi = m
        else: lo = m
    return lo

def open_up(g, slot_gap=0, min_counter=0.6, shave=0.06):
    """Widen only the gaps thread would close: enclosed counters below min_counter and
    open slots narrower than slot_gap. Adjacent strokes lose <= shave per side."""
    polys = [g] if isinstance(g, Polygon) else list(g.geoms)
    cut, fill = [], []
    for p in polys:
        for ring in p.interiors:
            h = Polygon(ring)
            if h.area < 0.12:          # junction pocket, not a counter: fill it
                fill.append(h.buffer(0.01)); continue
            d = inscribed_d(h)
            if d < min_counter:
                cut.append(h.buffer(min(shave * 1.3, (min_counter - d) / 2 + 0.02), join_style="round"))
    if slot_gap:
        r = slot_gap / 2
        closed = g.buffer(r, join_style="round").buffer(-r, join_style="round")
        slots = closed.difference(g)
        for sp in getattr(slots, "geoms", [slots]):
            if sp.area > 0.04 and not sp.is_empty:
                cut.append(sp.buffer(shave, join_style="round"))
    if fill: g = unary_union([g] + fill)
    g = g.difference(unary_union(cut)) if cut else g
    # smooth away nicks < 0.1 mm (close, then open) — far below any slot or counter size
    return g.buffer(0.05, join_style="round").buffer(-0.1, join_style="round").buffer(0.05, join_style="round")

# ------------------------------------------------------------ 理砂 hand-lettered
def risa(x0, y0, h, w_stroke=0.95):
    """Uniform-stroke marker lettering, counters spaced so they stay open at size.
    Drawn on a 10-unit em per character, y down."""
    u = h / 10.0
    P = lambda x, y, ox=0: (x0 + (x + ox) * u, y0 + y * u)
    S = lambda pts, ox=0: stroke([P(x, y, ox) for x, y in pts], w_stroke)
    ri = [  # 理 : 王 + 里
        S([(0.3, 1.5), (2.75, 1.5)]), S([(0.5, 4.9), (2.65, 4.9)]),
        S([(1.55, 1.5), (1.55, 7.9)]), S([(0.2, 8.9), (3.1, 7.6)]),
        S([(4.85, 0.6), (9.6, 0.6), (9.6, 5.2), (4.85, 5.2), (4.85, 0.6)]),
        S([(4.85, 2.9), (9.6, 2.9)]), S([(7.22, 0.6), (7.22, 9.45)]),
        S([(5.3, 7.25), (9.2, 7.25)]), S([(4.3, 9.45), (10.0, 9.45)]),
    ]
    ox = 11.9
    sa = [  # 砂 : 石 + 少
        S([(0.2, 1.3), (4.0, 1.3)], ox),
        stroke([P(x, y, ox) for x, y in bez((2.05, 1.3), (1.8, 4.2), (1.2, 6.9), (0.2, 8.9), 30)], w_stroke),
        S([(1.75, 4.5), (3.9, 4.5), (3.9, 8.6), (1.75, 8.6), (1.75, 4.5)], ox),
        stroke([P(x, y, ox) for x, y in bez((8.0, 0.4), (8.0, 2.0), (8.0, 3.4), (7.97, 4.8), 20)], w_stroke),
        S([(6.0, 2.2), (5.8, 3.9)], ox), S([(10.0, 2.0), (10.5, 3.6)], ox),
        stroke([P(x, y, ox) for x, y in bez((10.2, 5.7), (9.4, 7.5), (8.1, 8.9), (6.3, 9.75), 30)], w_stroke),
    ]
    return unary_union(ri + sa), (ox + 10.6) * u

# ------------------------------------------------------------ motifs
def heart_outline(cx, cy, wdt, w_stroke=1.15, rot=0):
    s = wdt / 2.0
    t = np.linspace(0, 2 * math.pi, 220)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2*t) - 2 * np.cos(3*t) - np.cos(4*t)
    x, y = x / 17 * s, -y / 17 * s
    ring = LineString(list(zip(cx + x, cy + y + s * 0.12)) + [(cx + x[0], cy + y[0] + s * 0.12)])
    g = ring.buffer(w_stroke / 2, join_style="round", quad_segs=12)
    return affinity.rotate(g, rot, origin=(cx, cy))

def blossom(cx, cy, d, rot=0):
    """5-petal plum blossom + white knot centre (1 centre + 5 ring dots)."""
    pr = d * 0.245
    petals = unary_union([Point(cx + d*0.255*math.cos(math.radians(rot - 90 + k*72)),
                                cy + d*0.255*math.sin(math.radians(rot - 90 + k*72))).buffer(pr, quad_segs=24)
                          for k in range(5)] + [Point(cx, cy).buffer(d * 0.26)])
    centre = [Point(cx, cy).buffer(0.7, quad_segs=16)]
    centre += [Point(cx + 1.7*math.cos(math.radians(rot - 54 + k*72)),
                     cy + 1.7*math.sin(math.radians(rot - 54 + k*72))).buffer(0.5, quad_segs=16) for k in range(5)]
    return petals, unary_union(centre)

def dotg(x, y, d):
    return Point(x, y).buffer(d / 2, quad_segs=16)

# ------------------------------------------------------------ face (from image 2, crop px → mm)
def face():
    o, k = (11.5, 26.3), 0.0275
    M = lambda pts: [(o[0] + k*x, o[1] + k*y) for x, y in pts]
    lw = 0.7   # triple-run (bean) stitch line art
    lines = [
        bez(*M([(45, 490), (110, 300), (210, 120), (330, 68)]), 40),          # hair outer L
        bez(*M([(425, 50), (560, 70), (700, 200), (770, 340)]), 40),          # hair outer R
        bez(*M([(95, 520), (125, 430), (160, 345), (200, 270)]), 30),         # strands L
        bez(*M([(172, 528), (185, 480), (198, 435), (215, 392)]), 30),
        bez(*M([(684, 282), (700, 318), (715, 350), (735, 395)]), 30),        # strands R
        bez(*M([(612, 232), (640, 310), (668, 390), (700, 470)]), 30),
        M([(300, 168), (312, 250)]), M([(362, 148), (357, 252)]), M([(420, 140), (418, 250)]),
        M([(478, 142), (490, 238)]), M([(532, 150), (552, 235)]),                # bangs
        bez(*M([(262, 348), (280, 305), (330, 303), (348, 340)]), 20),         # lids
        bez(*M([(462, 330), (485, 290), (555, 292), (578, 332)]), 20),
        M([(388, 375), (398, 418)]),                                           # nose
        bez(*M([(305, 488), (350, 528), (440, 528), (495, 465)]), 30),         # smile
        bez(*M([(228, 500), (305, 612), (515, 622), (615, 425)]), 40),         # face edge
    ]
    g = unary_union([stroke(l, lw) for l in lines] +
                    [dotg(*M([(305, 382)])[0], 1.15), dotg(*M([(520, 366)])[0], 1.15)])
    cheeks = unary_union([dotg(*M([(258, 458)])[0], 2.4), dotg(*M([(565, 428)])[0], 2.4)])
    return g, cheeks

# ------------------------------------------------------------ frame with corner loops
def frame(w_stroke=1.0):
    Ktl, Ktr, Kbr, Kbl = (12.0, 11.7), (68.4, 11.1), (69.4, 42.6), (11.7, 42.8)
    top = [Ktl, (17, 10.0), (25, 9.5), (33, 10.2), (41, 9.4), (49, 9.9), (57, 9.2), (63.5, 9.7), Ktr]
    right = [Ktr, (71.0, 16), (72.0, 22), (71.0, 28), (71.9, 34), (71.2, 39.5), Kbr]
    bottom = [Kbr, (64, 44.6), (56, 43.9), (48, 44.6), (40, 43.7), (32, 44.5), (24, 43.8), (16.5, 44.4), Kbl]
    left = [Kbl, (8.6, 38), (9.4, 32), (8.3, 26), (9.3, 20), (8.8, 15.5), Ktl]
    edges = [catmull(e, 20) for e in (top, right, bottom, left)]
    def unit(v):
        v = np.array(v, float); return v / np.linalg.norm(v)
    geoms = []
    corners = [Ktr, Kbr, Kbl, Ktl]
    for i, e in enumerate(edges):
        geoms.append(stroke(e, w_stroke))
        nxt = edges[(i + 1) % 4]
        K = np.array(corners[i])
        d_in = unit(np.array(e[-1]) - np.array(e[-3]))
        d_out = unit(np.array(nxt[2]) - np.array(nxt[0]))
        o = unit(d_in - d_out)                    # outward diagonal
        A = K + o * 3.3                           # loop apex
        tA = unit(d_in + d_out) * -1              # travel direction at apex
        a, b = 2.6, 1.9
        loop = bez(K, K + a * d_in, A - b * tA, A, 40) + bez(A, A + b * tA, K - a * d_out, K, 40)[1:]
        geoms.append(stroke(loop, w_stroke))
    return unary_union(geoms)

# ------------------------------------------------------------ compose
def compose():
    L = {}
    L["frame"] = frame()
    L["chihiro"], _ = set_line("ちひろ", "ZenMaruGothic-Bold.ttf", 23.4, 14.3, 5.4, 0.65,
                               [(-6, 0.2), (4, -0.3), (-3, 0.3)], grow=0.07, join=0.15)
    L["line1"], h1 = set_line("元気でね", "ZenMaruGothic-Bold.ttf", 36.4, 22.15, 6.7, 0.65,
                              [(-3, 0), (2, 0.25), (-2, -0.1), (3, 0.2)], grow=0.0, max_w=31.5, join=0.1)
    L["line2"], h2 = set_line("また会おうね", "ZenMaruGothic-Bold.ttf", 51.8, 29.95, 6.7, 0.65,
                              [(-2, -0.1), (3, 0.2), (-2, 0), (2, 0.25), (-3, -0.1), (2, 0.15)],
                              grow=0.0, max_w=36.4, join=0.1)
    ri, rw = risa(0, 0, 7.9)
    b = ri.bounds
    L["risa"] = affinity.rotate(affinity.translate(ri, 60.4 - (b[0] + b[2]) / 2, 38.45 - (b[1] + b[3]) / 2),
                                -4, origin="centroid")
    L["hearts"] = unary_union([heart_outline(42.0, 13.95, 6.6, rot=-4),
                               heart_outline(50.7, 13.75, 6.6, rot=3),
                               heart_outline(59.2, 13.95, 6.6, rot=-2)])
    fl = [blossom(15.0, 25.4, 7.8, 8), blossom(57.4, 22.2, 7.0, -6),
          blossom(65.4, 20.3, 7.0, 12), blossom(38.6, 38.6, 7.8, 4)]
    L["pink_flowers"] = unary_union([fl[0][0], fl[3][0]])
    L["yellow_flower"], L["blue_flower"] = fl[1][0], fl[2][0]
    L["flower_centres"] = unary_union([c for _, c in fl])
    L["face"], L["cheeks"] = face()
    L["dots"] = unary_union([dotg(*p, 1.5) for p in
                             [(19.8, 21.3), (11.7, 30.0), (13.5, 31.4),
                              (62.0, 24.4), (32.2, 41.3), (34.2, 42.1)]])
    return L

ORDER = [  # (layer id, layers, colour)
    ("05_frame_RED", ["frame"], "red"),
    ("06_flowers_PINK", ["pink_flowers"], "pink"),
    ("07_flower_YELLOW", ["yellow_flower"], "yellow"),
    ("08_flower_BLUE", ["blue_flower"], "blue"),
    ("09_flower_centres_WHITE", ["flower_centres"], "white"),
    ("10_hearts_PINK", ["hearts"], "pink"),
    ("11_cheeks_ROSE", ["cheeks"], "rose"),
    ("12_face_BLACK", ["face"], "black"),
    ("13_lettering_BLACK", ["line1", "line2"], "black"),
    ("14_name_chihiro_RED", ["chihiro"], "red"),
    ("15_signature_risa_BLUE", ["risa"], "blue"),
    ("16_accent_dots_RED", ["dots"], "red"),
]

def art_svg(L, guides=False):
    motifs, pitch = B.border_svg(W, H, rivet_corners=())
    body = [f'<g id="01_edge_satin_and_band_RED"><rect x="0" y="0" width="{f(W)}" height="{f(H)}" '
            f'rx="{B.CORNER_R}" fill="{PAL["red"]}"/></g>',
            f'<g id="02_field_CREAM"><rect x="{BORDER}" y="{BORDER}" width="{f(W-2*BORDER)}" '
            f'height="{f(H-2*BORDER)}" fill="{PAL["cream"]}"/></g>',
            f'<g id="03_border_motifs_WHITE">{motifs}</g>']
    for lid, keys, col in ORDER:
        g = unary_union([L[k] for k in keys])
        body.append(f'<g id="{lid}"><path d="{geom_to_path(g)}" fill="{PAL[col]}" fill-rule="evenodd"/></g>')
    if guides:
        body.append(f'<g id="99_GUIDES_do_not_stitch" fill="none" stroke="#00A3FF" stroke-width="0.12">'
                    f'<rect x="{B.EDGE}" y="{B.EDGE}" width="{f(W-2*B.EDGE)}" height="{f(H-2*B.EDGE)}" rx="0.6" '
                    f'stroke-dasharray="0.8 0.5"/></g>')
    return B.svg_doc(W, H, "\n".join(body)), pitch

# ------------------------------------------------------------ QA: spacing between neighbours
def collisions(L, min_gap=0.7):
    keys = list(L); out = []
    field = Polygon([(FX0, FY0), (FX1, FY0), (FX1, FY1), (FX0, FY1)])
    for k in keys:
        inset = field.exterior.distance(L[k]) if field.contains(L[k].representative_point()) else 0
        d_edge = min(L[k].distance(field.exterior), 99)
        if d_edge < min_gap or not field.contains(L[k]):
            out.append((k, "FIELD EDGE", round(d_edge, 2)))
    for i, a in enumerate(keys):
        for b2 in keys[i+1:]:
            if {a, b2} == {"face", "cheeks"} or {a, b2} <= {"pink_flowers", "yellow_flower", "blue_flower", "flower_centres"}:
                continue
            d = L[a].distance(L[b2])
            if d < min_gap:
                out.append((a, b2, round(d, 2)))
    return out

if __name__ == "__main__":
    L = compose()
    svg, pitch = art_svg(L)
    open("out/HAKI_waistband-patch_ART.svg", "w").write(svg)
    open("out/HAKI_waistband-patch_ART+guides.svg", "w").write(art_svg(L, True)[0])
    print("pitch", [round(p, 2) for p in pitch])
    for c in collisions(L): print("CLOSE:", c)
