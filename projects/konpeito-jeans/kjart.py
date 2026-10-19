"""Konpeito jeans — production art as stitch regions (mm, y down), traced from the rectified mockups (LESSONS A14/A15).

Elements
  01 coin   coin-pocket patch 76 x 56 (house border, rivet corners TL/TR), field traced from 1792126222329_image.png
  02 spill  konpeito spilling out of the coin pocket: direct embroidery on the front-right pocket facing, traced
  03 wb     back waistband patch 80 x 54 (house border, no rivet corners), field traced from 1792126245750_image.png
  04 stars  back-pocket stars 10 mm (generated: the flat shows them at ~10 px)
Every function returns a list of region dicts (col, geom, st, ang, grp, + column data for satin columns) and a dict of
per-family reference masks for the fidelity gates.
"""
import math, pickle, json
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import measure
from shapely.geometry import Polygon, Point, LineString, box, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
import kjcore
import kjsatin as KS
import classify as CL

PPM = 20                    # rectified mockup px per mm
EDGE, BAND = 2.0, 4.5
BORDER = EDGE + BAND        # 6.5 house border
CORNER_R = 2.5
FLOWER_D, DOT_D, PITCH = 4.0, 1.5, 5.8
RIVET_CAP = 8.0
MIN_W = {"kj_black": 0.7}   # 60wt line minimum; 40wt satin columns 0.8
GENERATED = {}
TEXTFIT = {}                # element -> line -> [(char, dice)] registration of the font glyphs on the traced pixels              # element -> list of what is generated (not traced), printed on the spec pages

# ------------------------------------------------------------------ raster -> geometry
def mask_geom(mask, x0=0.0, y0=0.0, ppm=PPM, sigma=0.8, simp=0.05, min_area=0.15):
    m = ndi.gaussian_filter(mask.astype(float), sigma) if sigma else mask.astype(float)
    m = np.pad(m, 1)
    polys = []
    for c in measure.find_contours(m, 0.5):
        if len(c) < 4: continue
        p = Polygon([((x - 1) / ppm + x0, (y - 1) / ppm + y0) for y, x in c]).buffer(0)
        if not p.is_empty: polys.append(p)
    g = Polygon()
    for p in sorted(polys, key=lambda q: -q.area):
        g = g.symmetric_difference(p)
    g = g.buffer(0).simplify(simp)
    parts = [p for p in getattr(g, "geoms", [g]) if p.area >= min_area]
    return unary_union(parts) if parts else Polygon()

def polys(g):
    if g.is_empty: return []
    return [g] if g.geom_type == "Polygon" else [p for p in g.geoms if p.geom_type == "Polygon"]

def R(col, geom, st, grp, ang="auto", **kw):
    d = dict(col=col, geom=geom.buffer(0), st=st, ang=ang, grp=grp, layer=0); d.update(kw); return d

def columns(col, geom, code="TXC", min_w=0.8, ppm=40.0):
    """traced stroke shape -> satin pieces that tile the TRACED outline exactly: the skeleton graph (kjsatin.glyph_columns)
    gives one centreline per stroke, every pixel of the shape goes to its nearest centreline, and each piece is sewn as a
    turning satin across that centreline (rows clipped to the traced outline). Strokes under min_w are widened to min_w."""
    out = []
    for P in polys(geom):
        if P.area < 0.15: continue
        if 2 * P.area / max(P.length, 1e-6) < min_w * 0.9:
            P = P.buffer((min_w - 2 * P.area / max(P.length, 1e-6)) / 2, join_style="round")
            P = max(polys(P), key=lambda q: q.area)
        sts = KS.glyph_columns(P, ppm=ppm)
        lines = []
        for s_ in sts:
            cl = list(s_["cl"])
            if s_.get("closed"): cl = cl + [cl[0]]
            if len(cl) >= 2 and LineString(cl).length > 0.3: lines.append(LineString(cl))
        if not lines:
            out.append(R(col, P, "satin", code)); continue
        if len(lines) == 1:
            out.append(R(col, P, "satin", code, ang="tl", tline=list(lines[0].coords))); continue
        x0, y0, x1, y1 = P.bounds; m = 4
        Wp, Hp = int((x1 - x0) * ppm) + 2 * m, int((y1 - y0) * ppm) + 2 * m
        from PIL import ImageDraw
        T = lambda cs: [((x - x0) * ppm + m, (y - y0) * ppm + m) for x, y in cs]
        im = Image.new("L", (Wp, Hp), 0); d = ImageDraw.Draw(im); d.polygon(T(P.exterior.coords), fill=255)
        for q in P.interiors: d.polygon(T(q.coords), fill=0)
        pm = np.array(im) > 127
        li = Image.new("I", (Wp, Hp), 0); dl = ImageDraw.Draw(li)
        for k, ln in enumerate(lines, 1): dl.line(T(ln.coords), fill=k, width=1)
        la = np.array(li)
        _, (iy, ix) = ndi.distance_transform_edt(la == 0, return_indices=True)
        near = la[iy, ix]
        for k, ln in enumerate(lines, 1):
            piece = mask_geom(pm & (near == k), x0 - m / ppm, y0 - m / ppm, ppm=ppm, sigma=0.0, simp=0.02, min_area=0.02)
            piece = piece.buffer(0.04).intersection(P)        # pieces overlap 0.04 at the joins: no hairline gaps
            for q in polys(piece):
                if q.area < 0.03: continue
                out.append(R(col, q, "satin", code, ang="tl", tline=list(ln.coords)))
    return out

def colsat(col, geom, code="TXC", min_w=0.8, uniform=False, ppm=40.0, spur=1.3):
    """stroke shape -> satin columns (kjsatin.glyph_columns: skeleton graph, one column per stroke, overlapping at joins).
    uniform=True: every column of this motif gets the motif's median width (line art drawn with one thread width)."""
    out = []; allst = []
    for P in polys(geom):
        if P.area < 0.1: continue
        sts = KS.glyph_columns(P, ppm=ppm)
        if not sts:
            c = P.centroid; allst.append(dict(cl=[(c.x - 0.01, c.y), (c.x + 0.01, c.y)], w=max(min_w, 2 * math.sqrt(P.area / math.pi)), caps=("round", "round"))); continue
        if len(sts) > 1:
            sts = [s_ for s_ in sts if s_.get("closed") or KS.poly_len(s_["cl"]) > spur * s_["w"] or len(sts) == 1]
        allst += sts
    if uniform and allst:
        wm = float(np.median([s_["w"] for s_ in allst]))
        for s_ in allst: s_["w"] = wm
    for s_ in allst:
        out.append(KS.column_region(col, code, s_["cl"], max(min_w, s_["w"]), s_["caps"], s_.get("closed", False)))
    return out

def text_regions(col, text, mask, min_w=0.8):
    """register Zen Maru Gothic glyphs per character on the traced pixels (kjtext.fit_line), best of Bold / Black,
    then satin columns per stroke."""
    import kjtext
    ys, xs = np.nonzero(mask)
    box_ = (xs.min() / PPM, ys.min() / PPM, (xs.max() + 1) / PPM, (ys.max() + 1) / PPM)
    best = None
    for wt in ("bold", "black"):
        fit = kjtext.fit_line(text, mask, PPM, box_, wt)
        sc = float(np.mean([o["dice"] for o in fit]))
        if best is None or sc > best[0]: best = (sc, wt, fit)
    sc, wt, fit = best
    regs = []
    for o in fit:
        regs += colsat(col, o["geom"], min_w=min_w)
    return dict(regs=regs, fit=dict(weight=wt, chars=[(o["ch"], o["dice"]) for o in fit]),
                geom=unary_union([o["geom"] for o in fit]))

def dot_region(col, geom, code="DOT", min_d=1.2):
    c = geom.centroid; d = max(min_d, 2 * math.sqrt(geom.area / math.pi))
    g = geom if 2 * math.sqrt(geom.area / math.pi) >= min_d else Point(c.x, c.y).buffer(min_d / 2, quad_segs=16)
    return R(col, g, "satin", code)

def radial_region(col, geom, code, centre=None):
    c = centre or (geom.centroid.x, geom.centroid.y)
    return R(col, geom, "satin", code, ang=("radial", c[0], c[1]))

# ------------------------------------------------------------------ house border (fixed mm, shared by both patches)
def side_positions(a, b, pitch=PITCH):
    L = b - a; n = max(2, round(L / pitch))
    if n % 2: n = n + 1 if abs(L / (n + 1) - pitch) < abs(L / (n - 1) - pitch) else n - 1
    return [a + L * i / n for i in range(n + 1)], L / n

def border_flower(cx, cy, d=FLOWER_D):
    pl, pw, rr = d * 0.46, d * 0.34, d * 0.27
    petals = []
    for k in range(5):
        a = -90 + k * 72
        px, py = cx + rr * math.cos(math.radians(a)), cy + rr * math.sin(math.radians(a))
        e = affinity.scale(Point(0, 0).buffer(1, quad_segs=16), pw / 2, pl / 2)
        petals.append(affinity.translate(affinity.rotate(e, a + 90, origin=(0, 0)), px, py))
    return unary_union(petals).difference(Point(cx, cy).buffer(d * 0.11, quad_segs=12))

def rrect(x0, y0, x1, y1, r):
    return box(x0 + r, y0 + r, x1 - r, y1 - r).buffer(r, quad_segs=16)

def border(W, H, rivets=()):
    """red band tatami (4 sides, rows across the band), cream field, white motifs, red heat-cut edge column."""
    out = []; c = EDGE + BAND / 2
    outer = rrect(0, 0, W, H, CORNER_R); field = box(BORDER, BORDER, W - BORDER, H - BORDER)
    band = outer.buffer(-0.6).difference(field.buffer(-0.3))     # band runs 0.3 under the field, 1.4 under the edge
    cx, cy = W / 2, H / 2
    for tri, ang in (([(0, 0), (W, 0), (cx, cy)], 90), ([(0, H), (W, H), (cx, cy)], 90),
                     ([(0, 0), (0, H), (cx, cy)], 0), ([(W, 0), (W, H), (cx, cy)], 0)):
        g = band.intersection(Polygon(tri))
        if g.area > 1: out.append(R("kj_red", g, "tatami", "BAND", ang))
    out.append(R("kj_cream", field.buffer(0.3), "tatami", "FIELD", 0))
    xs, px = side_positions(c, W - c); ys, py = side_positions(c, H - c)
    mot = []
    def place(x, y, i, corner=None):
        if corner in rivets: return
        mot.append(R("kj_white", border_flower(x, y), "satin", "BFL", ang=("radial", x, y)) if i % 2 == 0
                   else R("kj_white", Point(x, y).buffer(DOT_D / 2, quad_segs=16), "satin", "BDOT"))
    for i, x in enumerate(xs):
        place(x, c, i, "tl" if i == 0 else "tr" if i == len(xs) - 1 else None)
        place(x, H - c, i, "bl" if i == 0 else "br" if i == len(xs) - 1 else None)
    for i, y in enumerate(ys[1:-1], start=1):
        place(c, y, i); place(W - c, y, i)
    # heat-cut edge: closed 2.0 column on the outline inset 1.0
    cl = list(rrect(1.0, 1.0, W - 1.0, H - 1.0, CORNER_R - 1.0).exterior.coords)[:-1]
    edge = KS.column_region("kj_red", "EDGE", cl, EDGE, ("flat", "flat"), True)
    return out, mot, edge, (px, py)

# ------------------------------------------------------------------ helpers on the label image
def load(name):
    lab = np.load(f"out/trace/{name}_lab.npy"); img = np.asarray(Image.open(f"out/trace/{name}_rect.png").convert("RGB"))
    return lab, img

def field_mask(shape, x0, y0, x1, y1, inset=0.45):
    m = np.zeros(shape, bool)
    m[int((y0 + inset) * PPM):int((y1 - inset) * PPM), int((x0 + inset) * PPM):int((x1 - inset) * PPM)] = True
    return m

def comps(mask, min_px=8):
    lab, n = ndi.label(mask, structure=np.ones((3, 3)))
    out = []
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        m = lab == k
        if m.sum() >= min_px: out.append(m)
    return out

def cen(m):
    ys, xs = np.nonzero(m); return xs.mean() / PPM, ys.mean() / PPM

def area(m): return m.sum() / PPM ** 2

# ------------------------------------------------------------------ 03 waistband patch
def waistband():
    W, H = 80.0, 54.0
    lab, img = load("wb")
    F = field_mask(lab.shape, BORDER, BORDER, W - BORDER, H - BORDER)
    st = np.ones((3, 3), bool)
    red = (lab == 1) & F; pink = (lab == 3) & F; black = (lab == 2) & F
    yellow = (lab == 4) & F; blue = (lab == 5) & F; white = ((lab == 6) | (lab == 0)) & F
    ref = {}; regs = {}
    # red + pink families split per component by pink fraction
    rp = ndi.binary_closing(red | pink, st, 1) & F
    frame = []; pinkm = np.zeros_like(F); redm = np.zeros_like(F)
    for m in comps(rp, 12):
        a = area(m); pf = (m & pink).sum() / max(m.sum(), 1)
        if a > 60 and pf < 0.2: frame.append(m)
        elif pf > 0.22: pinkm |= m
        else: redm |= m
    frame = frame[0] if frame else np.zeros_like(F)
    # pink motifs: hearts (top band, outline rings) and flowers (filled, white centre)
    hearts = np.zeros_like(F); pflowers = []
    for m in comps(pinkm, 20):
        x, y = cen(m)
        if y < 19.5 and x > 35: hearts |= m
        else: pflowers.append(ndi.binary_fill_holes(m))
    # red: chihiro lettering (top-left), cheeks (inside the face), dots
    chihiro = np.zeros_like(F); cheeks = []; dots = []
    for m in comps(redm, 6):
        x, y = cen(m); a = area(m)
        if y < 21 and x < 32 and a > 0.6: chihiro |= m
        elif 13 < x < 31 and 33 < y < 40 and a > 2.0: cheeks.append(m)
        else: dots.append(m)
    yfl = [ndi.binary_fill_holes(m) for m in comps(ndi.binary_closing(yellow, st, 2), 40)]
    bl = comps(ndi.binary_closing(blue, st, 1), 10)
    bflower = [ndi.binary_fill_holes(m) for m in bl if cen(m)[1] < 28 and area(m) > 10]
    risa = np.zeros_like(F)
    for m in bl:
        if cen(m)[1] >= 28: risa |= m
    # black: face (left-bottom) vs text
    face = np.zeros_like(F); text = np.zeros_like(F)
    for m in comps(black, 6):
        x, y = cen(m)
        if area(m) < 0.15: continue
        (face if (x < 30.5 and y > 24) else text).__ior__(m)
    ref.update(frame=frame, chihiro=chihiro, hearts=hearts, text=text, face=face, risa=risa,
               flowers=np.any([*pflowers, *yfl, *bflower], axis=0), dots=np.any(dots, axis=0) if dots else np.zeros_like(F),
               cheeks=np.any(cheeks, axis=0) if cheeks else np.zeros_like(F))
    g = lambda m, **k: mask_geom(m, **k)
    out_f, mot, edge, pitch = border(W, H)
    vis = list(out_f) + list(mot)
    # flowers: petals radial satin + white centre knots traced from the white pixels inside the flower
    V = img.astype(float).mean(-1)
    def flower(m, col):
        """petals = traced silhouette (radial satin from the traced centre); centre knots = brightness peaks of the
        traced white centre cluster, one Ø1.1 knot dot per peak (min pitch 1.5 mm)."""
        geo = g(m, sigma=1.2).buffer(0.15).buffer(-0.15)
        blob = np.zeros_like(m)
        for k in comps(m & white, 4):
            if math.dist(cen(k), cen(m)) < 2.6: blob |= k
        cx, cy = cen(blob) if blob.any() else cen(m)
        # knot cluster: centre knot + 5 round it (r 1.6, Ø1.1) on the traced centre, ring turned to the flower's petals
        ang0 = math.degrees(math.atan2(*(np.array(cen(m))[::-1] - np.array((cx, cy))[::-1])))
        kn = [R("kj_white", Point(cx, cy).buffer(0.55, quad_segs=12), "satin", "KNOT")]
        for j in range(5):
            t = math.radians(ang0 + 36 + j * 72)
            kn.append(R("kj_white", Point(cx + 1.6 * math.cos(t), cy + 1.6 * math.sin(t)).buffer(0.55, quad_segs=12), "satin", "KNOT"))
        petals = [radial_region(col, p, "FL", (cx, cy)) for p in polys(geo)]
        return petals, kn
    knots = []
    for m in pflowers:
        p, k = flower(m, "kj_pink"); vis += p; knots += k
    for m in yfl:
        p, k = flower(m, "kj_yellow"); vis += p; knots += k
    for m in bflower:
        p, k = flower(m, "kj_blue"); vis += p; knots += k
    vis += colsat("kj_pink", g(hearts, sigma=1.0), uniform=True)
    T = {}
    T["risa"] = text_regions("kj_blue", "理砂", risa)
    vis += knots
    vis += [dot_region("kj_rose", g(m, sigma=1.0), "DOT", 1.6) for m in cheeks]
    vis += colsat("kj_black", g(face, sigma=0.5), code="LINE", min_w=MIN_W["kj_black"], uniform=True)
    l1 = np.zeros_like(text); l2 = np.zeros_like(text)
    for m in comps(text, 2):
        if area(m) < 0.3: continue                       # shadow specks next to the flowers, not lettering
        (l1 if cen(m)[1] < 25.0 else l2).__ior__(m)
    T["line1"] = text_regions("kj_black", "元気でね", l1, min_w=MIN_W["kj_black"])
    T["line2"] = text_regions("kj_black", "また会おうね", l2, min_w=MIN_W["kj_black"])
    vis += colsat("kj_red", g(frame, sigma=1.0), uniform=True)
    T["chihiro"] = text_regions("kj_red", "ちひろ", chihiro)
    for k in ("risa", "line1", "line2", "chihiro"):
        vis += T[k]["regs"]
    TEXTFIT["wb"] = {k: T[k]["fit"] for k in T}
    vis += [dot_region("kj_red", g(m, sigma=0.8), "DOT", 1.2) for m in dots if area(m) > 0.25]
    vis.append(edge)
    GENERATED["wb"] = ["border (house spec: 2.0 edge + 4.5 band, Ø4.0 flowers / Ø1.5 dots at 5.8 pitch — fixed mm, not traced)",
                       "flower centre knots: traced centre, knot pattern (1 + 5 at r 1.6, Ø1.1) generated", "lettering: Zen Maru Gothic glyphs registered per character on the traced pixels (dice table)"]
    return vis, ref, (W, H), pitch

# ------------------------------------------------------------------ 01 coin pocket
def coin():
    W, H = 76.0, 56.0
    lab, img = load("coin")
    VIS = 47.0                                     # mockup field visible down to here (pocket mouth below: A15 mask)
    F = field_mask(lab.shape, BORDER, BORDER, W - BORDER, VIS)
    st = np.ones((3, 3), bool)
    red = (lab == 1) & F; pink = (lab == 3) & F; yellow = (lab == 4) & F; blue = (lab == 5) & F
    light = ((lab == 6) | (lab == 0))
    # candies: pink family = pink + its red shading; yellow; blue — each filled (white sparkles are holes)
    rp = ndi.binary_closing(red | pink, st, 1) & F
    letters = np.zeros_like(F); dots = []; candies = []
    for m in comps(rp, 10):
        pf = (m & pink).sum() / max(m.sum(), 1)
        if pf > 0.3 and area(m) > 20: candies.append(("kj_pink", m))
        elif cen(m)[1] < 29:
            ys_, xs_ = np.nonzero(m)
            if area(m) > 0.5 and ys_.min() > (BORDER + 0.8) * PPM: letters |= m
        else: dots.append(m)
    for col, fam in (("kj_yellow", yellow), ("kj_blue", blue)):
        for m in comps(ndi.binary_closing(fam, st, 2), 60):
            if area(m) > 20: candies.append((col, m))
    out_f, mot, edge, pitch = border(W, H, rivets=("tl", "tr"))
    vis = list(out_f) + list(mot)
    ref = dict(letters=letters, candies=np.any([ndi.binary_fill_holes(m) for _, m in candies], axis=0),
               dots=np.any(dots, axis=0) if dots else np.zeros_like(F))
    hi_regs, sp_regs = [], []
    for col, m in sorted(candies, key=lambda cm: cen(cm[1])[0]):
        body, hi, sparks = candy(col, m, light)
        vis.append(body); hi_regs += hi; sp_regs += sparks
    vis += hi_regs + sp_regs
    T = text_regions("kj_red", "こんぺいとう", letters)
    vis += T["regs"]; TEXTFIT["coin"] = {"konpeito": T["fit"]}
    vis += [dot_region("kj_red", mask_geom(m, sigma=1.0), "DOT", 1.3) for m in dots if area(m) > 0.3]
    vis.append(edge)
    GENERATED["coin"] = ["border (house spec, fixed mm; mockup edge reads cream, house spec red kept)",
                         "candy highlight = traced silhouette inset (tint), sparkle dots Ø1.1 at traced positions"]
    return vis, ref, (W, H), pitch, VIS

HI = {"kj_pink": "kj_pink_hi", "kj_yellow": "kj_yellow_hi", "kj_blue": "kj_blue_hi"}
def candy(col, m, light, x0=0.0, y0=0.0, clip=None):
    """traced candy silhouette -> body radial satin, tint highlight (silhouette inset 1.6 mm, nudged up-left),
    white sparkle knots at the traced light specks."""
    fm = ndi.binary_fill_holes(ndi.binary_closing(m, np.ones((3, 3)), 2))
    geo = mask_geom(fm, x0, y0, sigma=1.2).buffer(0.2).buffer(-0.2)
    if clip is not None: geo = geo.intersection(clip)
    if geo.is_empty: return None, [], []
    geo = max(polys(geo), key=lambda p: p.area) if len(polys(geo)) > 1 else geo
    c = geo.centroid
    body = radial_region(col, geo, "KP", (c.x, c.y))
    hi = []
    h = affinity.translate(geo.buffer(-1.7, join_style="round"), -0.35, -0.45).intersection(geo.buffer(-0.6))
    for p in polys(h):
        if p.area > 1.0: hi.append(radial_region(HI[col], p, "KP-hi", (c.x, c.y)))
    sparks = []
    inner = ndi.binary_erosion(fm, np.ones((3, 3)), 8) & light
    for k in comps(inner, 3):
        a = area(k)
        if 0.02 < a < 1.6:
            x, y = cen(k); x += x0; y += y0
            p = Point(x, y).buffer(0.55, quad_segs=12)
            if geo.buffer(-0.5).contains(p) and all(p.distance(s["geom"]) > 0.5 for s in sparks):
                sparks.append(R("kj_white", p, "satin", "KNOT"))
    return body, hi, sparks

# ------------------------------------------------------------------ 02 konpeito spill (facing, above the coin pocket)
def spill():
    lab, img = load("spill")          # canvas y from -22 mm, patch-field frame
    Y0 = -22.0
    # top of the coin pocket's rolled cream edge per column -> the line the patch covers
    cream = (lab == 0) | (lab == 6)
    rows = []
    for xi in range(int(8 * PPM), int(68 * PPM), 10):
        col = cream[int(10 * PPM):int(22 * PPM), xi]       # y -12 .. 0
        idx = np.nonzero(ndi.binary_opening(col, np.ones(9)))[0]
        if len(idx): rows.append((xi / PPM, idx[0] / PPM + 10 + Y0))
    xs, ys = np.array(rows).T
    k, b = np.polyfit(xs, ys, 1)                           # straight edge (patch top), y = k x + b
    st = np.ones((3, 3), bool)
    above = np.zeros(lab.shape, bool)
    yy = (np.arange(lab.shape[0]) / PPM + Y0)[:, None]; xx = (np.arange(lab.shape[1]) / PPM)[None, :]
    above = yy < (k * xx + b - 0.2)
    pink = ((lab == 3) | (lab == 1)) & above; yellow = (lab == 4) & above; blue = (lab == 5) & above
    light = (lab == 6) | (lab == 0)
    cands = []
    for col, fam, mn in (("kj_yellow", yellow, 40), ("kj_blue", blue, 40), ("kj_pink", pink, 25)):
        for m in comps(ndi.binary_closing(fam, st, 2), mn):
            if area(m) > 1.5: cands.append((col, m))
    # level the patch edge: rotate so the edge is horizontal at y = 0 (the coin pocket's top edge on the garment)
    ang = math.degrees(math.atan(k)); x_mid = 38.0; y_mid = k * x_mid + b
    vis = []; ref_geo = []
    order = sorted(cands, key=lambda cm: (cm[0] != "kj_pink", cen(cm[1])[0]))   # small pink ones behind: first
    for col, m in order:
        body, hi, sparks = candy(col, m, light, 0.0, Y0)
        if body is None: continue
        ref_geo.append(body["geom"])
        for r in [body] + hi + sparks:
            g = affinity.rotate(r["geom"], -ang, origin=(x_mid, y_mid))
            g = affinity.translate(g, 0, -y_mid)
            # run 3.0 mm under the coin pocket (no gap at the pocket mouth): extend the parts that reach the edge down
            if r is body and g.bounds[3] > -1.0:
                g = unary_union([g, affinity.translate(g, 0, 1.5), affinity.translate(g, 0, 3.0)]).intersection(box(-50, -60, 150, 3.0))
                g = g.intersection(unary_union([g.buffer(0)]))
            r2 = dict(r, geom=g.buffer(0))
            if isinstance(r.get("ang"), tuple):
                c = affinity.translate(affinity.rotate(Point(r["ang"][1], r["ang"][2]), -ang, origin=(x_mid, y_mid)), 0, -y_mid)
                r2["ang"] = ("radial", c.x, c.y)
            vis.append(r2)
    # order: pink bodies first (they sit behind), then the rest; highlight + sparkles after all bodies
    bodies = [r for r in vis if r["grp"] == "KP"]; rest = [r for r in vis if r["grp"] != "KP"]
    vis = bodies + rest
    GENERATED["spill"] = ["3.0 mm run-under below the pocket line (hidden by the coin-pocket patch)",
                          "tint highlight = traced silhouette inset; sparkles Ø1.1 at traced specks"]
    ref = dict(candies=np.any([ndi.binary_fill_holes(m) for _, m in cands], axis=0), edge=(k, b, ang, y_mid))
    return vis, ref

# ------------------------------------------------------------------ 04 back-pocket stars (generated, 10 mm)
def puffy_star(cx, cy, width=10.0, rot=0.0, inner=0.50, tip=0.75, valley=0.45):
    Rr = 5.6
    pts = [((Rr if i % 2 == 0 else Rr * inner) * math.cos(math.radians(-90 + 36 * i)),
            (Rr if i % 2 == 0 else Rr * inner) * math.sin(math.radians(-90 + 36 * i))) for i in range(10)]
    g = Polygon(pts).buffer(valley, join_style="round").buffer(-valley, join_style="round")
    g = g.buffer(-tip, join_style="round").buffer(tip, join_style="round")
    b = g.bounds; s = width / (b[2] - b[0])
    g = affinity.scale(g, s, s, origin=(0, 0))
    hi = affinity.translate(affinity.scale(g, 0.5, 0.5, origin=(0, 0)), -0.45, -0.55)
    g = affinity.rotate(g, rot, origin=(0, 0)); hi = affinity.rotate(hi, rot, origin=(0, 0))
    return affinity.translate(g, cx, cy), affinity.translate(hi, cx, cy)

STARS = {"Y": ("kj_yellow", "kj_yellow_hi", -6, "wearer's LEFT back pocket, lower outer corner"),
         "P": ("kj_pink", "kj_pink_hi", 8, "wearer's RIGHT back pocket, upper outer corner below the rivet")}
def star(sid):
    base, tint, rot, _ = STARS[sid]
    g, hi = puffy_star(0, 0, rot=rot)
    GENERATED["star" + sid] = ["whole star (flat lay shows it at ~10 px; 5-point puffy star redrawn, colour from the house palette)"]
    return [radial_region(base, g, "STAR", (0, 0)), radial_region(tint, hi, "STAR-hi", (hi.centroid.x, hi.centroid.y))]

# ------------------------------------------------------------------ 04 back-pocket "haki" group (inputs/back_pocket_haki.png)
HAKI_SRC = (175, 405, 310, 460)   # crop of the group in the back-pocket mockup (px)
HAKI_UP = 8                       # Lanczos upscale, only to read the stroke centrelines (adds no detail)
STAR_D = 10.0                     # every konpeito star on the jean: 10 mm tip to tip (founder: same size everywhere)
def haki_group():
    """trace the light-blue 'haki' script + the two stars; scale the group so its stars are 10 mm like the
    right-pocket star (mockup: 14 px vs 30 px -> x 2.14). Returns regions in group mm (origin = yellow star centre)."""
    im = Image.open("inputs/back_pocket_haki.png").convert("RGB")
    x0, y0, x1, y1 = HAKI_SRC
    cr = np.asarray(im.crop(HAKI_SRC).resize(((x1 - x0) * HAKI_UP, (y1 - y0) * HAKI_UP), Image.LANCZOS)).astype(float)
    h, s_, v = CL.hsv(cr)
    blue = (h > 180) & (h < 215) & (s_ > 0.25) & (v > 0.45)
    yel = (h > 30) & (h < 62) & (s_ > 0.35) & (v > 0.45)
    pnk = ((h > 300) | (h < 12)) & (s_ > 0.30) & (v > 0.5)
    star_px = []
    for m in (yel, pnk):
        cm = max(comps(m, 30), key=lambda k: k.sum())
        ys, xs = np.nonzero(cm); star_px.append(((xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2, xs.max() - xs.min() + 1))
    k = STAR_D / np.mean([w for _, _, w in star_px])            # mm per upscaled px: stars come out 10 mm
    ox, oy = star_px[0][0], star_px[0][1]
    ppm_ = 1 / k
    bm = np.zeros_like(blue)
    xr = star_px[0][0] + star_px[0][2] * 0.6          # specks next to the yellow star are not lettering
    for c in comps(blue, 40):
        if cen(c)[0] * PPM > xr: bm |= c
    geo = mask_geom(bm, -ox * k, -oy * k, ppm=ppm_, sigma=1.5, simp=0.05)
    regs = colsat("kj_blue_hi", geo, code="TXC", min_w=1.2, uniform=True)
    out = []
    for (cx, cy, w), (base, tint) in zip(star_px, (("kj_yellow", "kj_yellow_hi"), ("kj_pink", "kj_pink_hi"))):
        g, hi = puffy_star((cx - ox) * k, (cy - oy) * k, STAR_D, rot=0)
        out += [radial_region(base, g, "STAR", ((cx - ox) * k, (cy - oy) * k)), radial_region(tint, hi, "STAR-hi", (hi.centroid.x, hi.centroid.y))]
    GENERATED["haki"] = ["stars: 10 mm puffy-star shape at the traced centres (the mockup shows them at 14 px)",
                         "'haki' strokes traced (x8 upscale only to read centrelines), one width for the whole word"]
    ref = dict(blue=bm, k=k, scale=STAR_D / (np.mean([w for _, _, w in star_px]) / HAKI_UP) / (10.0 / 30.0))
    return out + regs, ref

def build_all():
    A = {}
    vis, ref, wh, pitch, VIS = coin(); A["coin"] = dict(vis=vis, ref=ref, wh=wh, pitch=pitch, vis_to=VIS)
    vis, ref = spill(); A["spill"] = dict(vis=vis, ref=ref)
    vis, ref, wh, pitch = waistband(); A["wb"] = dict(vis=vis, ref=ref, wh=wh, pitch=pitch)
    for s in STARS: A["star" + s] = dict(vis=star(s))
    vis, ref = haki_group(); A["haki"] = dict(vis=vis, ref=ref)
    A["generated"] = dict(GENERATED); A["textfit"] = dict(TEXTFIT)
    pickle.dump(A, open("out/art.pkl", "wb"))
    return A

if __name__ == "__main__":
    A = build_all()
    for k, v in A.items():
        if k in ("generated", "textfit"): continue
        cols = sorted({r["col"] for r in v["vis"]})
        print(k, len(v["vis"]), "regions", len(cols), "colours", cols)
