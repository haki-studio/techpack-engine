"""Founder change (19 Oct 2026, evening): the stitch files are digitised FROM THE FOUNDER'S VECTOR ART
(inputs/svg/*_ART.svg, 16 Oct clean art, true size in mm), not from the AI mockups.

Layer ids name the stitch order + thread (01_edge_satin_and_band_RED, 02_field_CREAM, 03_border_motifs_WHITE, ...);
thread = layer fill. Digitising (LESSONS A16: one deliberate direction per part):
  border      house spec: band tatami across the band, cream field tatami 0 deg, heat-cut edge satin column;
              border flowers = the SVG's 5 petal ellipses (radial satin, red centre open), dots = round satin
  lettering / face / frame / hearts
              satin COLUMNS on the centrelines of the SVG outlines (kjsatin.glyph_columns), ONE width per layer
              (the art's own stroke width minus the 0.15 mm thread allowance); small rings (handakuten) = radial
              satin on the exact ring; compact blobs (eyes) = round satin dots
  flowers / konpeito
              one satin per petal / lobe along its axis (kjletter.petal_regions); tint centre shape = its own
              lobes on top; white specks / centres = round bead dots
  dots        round bead satin dots at the SVG centres and sizes
Reference masks for the gates are rendered from the SVG files by cairosvg, one layer at a time (true input, A14)."""
import math, re, copy, io
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
from shapely import affinity
import kjsatin as KS
import kjletter as KL

SVG = "inputs/svg"
NS = "{http://www.w3.org/2000/svg}"
PPM = 20
COL = {"#C8162B": "kj_red", "#F2E9D8": "kj_cream", "#FBF8F1": "kj_white", "#1C1A1A": "kj_black", "#EF7FAC": "kj_pink",
       "#F8B5CF": "kj_pink_hi", "#F5C230": "kj_yellow", "#FCE27E": "kj_yellow_hi", "#35A6D6": "kj_blue",
       "#8ED2EE": "kj_blue_hi", "#E8457A": "kj_rose"}
TINT_OF = {"kj_pink": "kj_pink_hi", "kj_yellow": "kj_yellow_hi", "kj_blue": "kj_blue_hi"}
REPORT = {}

# ------------------------------------------------------------------ SVG parsing (M L H V Q C Z, rotate / translate)
def _rot(t):
    m = re.match(r"rotate\(\s*([-\d.eE]+)(?:[ ,]+([-\d.eE]+)[ ,]+([-\d.eE]+))?\s*\)", t or "")
    if m:
        a = float(m.group(1)); cx = float(m.group(2) or 0); cy = float(m.group(3) or 0)
        return lambda g: affinity.rotate(g, a, origin=(cx, cy))
    m = re.match(r"translate\(\s*([-\d.eE]+)[ ,]*([-\d.eE]*)\s*\)", t or "")
    if m:
        dx = float(m.group(1)); dy = float(m.group(2) or 0); return lambda g: affinity.translate(g, dx, dy)
    if t: raise ValueError(f"unsupported transform {t}")
    return lambda g: g

def path_rings(d):
    toks = re.findall(r"[MLHVQCZmlhvqcz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", d)
    rings, cur, i, cmd, pos = [], [], 0, None, (0.0, 0.0)
    def num():
        nonlocal i; v = float(toks[i]); i += 1; return v
    while i < len(toks):
        t = toks[i]
        if re.match(r"[A-Za-z]", t): cmd = t; i += 1
        if cmd in "Zz":
            if len(cur) > 2: rings.append(cur)
            cur = []; continue
        rel = cmd.islower(); C = cmd.upper()
        ox, oy = pos if rel else (0.0, 0.0)
        if C == "M":
            if len(cur) > 2: rings.append(cur)
            pos = (num() + ox, num() + oy); cur = [pos]; cmd = "l" if rel else "L"
        elif C == "L": pos = (num() + ox, num() + oy); cur.append(pos)
        elif C == "H": pos = (num() + ox, pos[1]); cur.append(pos)
        elif C == "V": pos = (pos[0], num() + (pos[1] if rel else 0)); cur.append(pos)
        elif C == "Q":
            p0 = np.array(pos); p1 = np.array((num() + ox, num() + oy)); p2 = np.array((num() + ox, num() + oy))
            for s in np.linspace(0, 1, 9)[1:]: cur.append(tuple((1 - s) ** 2 * p0 + 2 * (1 - s) * s * p1 + s * s * p2))
            pos = tuple(p2)
        elif C == "C":
            p0 = np.array(pos); p1 = np.array((num() + ox, num() + oy)); p2 = np.array((num() + ox, num() + oy)); p3 = np.array((num() + ox, num() + oy))
            for s in np.linspace(0, 1, 13)[1:]: cur.append(tuple((1 - s) ** 3 * p0 + 3 * (1 - s) ** 2 * s * p1 + 3 * (1 - s) * s * s * p2 + s ** 3 * p3))
            pos = tuple(p3)
        else: raise ValueError(cmd)
    if len(cur) > 2: rings.append(cur)
    return rings

def evenodd(rings):
    g = Polygon()
    for r in sorted([Polygon(r).buffer(0) for r in rings], key=lambda p: -p.area):
        g = g.symmetric_difference(r)
    return g.buffer(0)

def polys(g):
    if g.is_empty: return []
    return [g] if g.geom_type == "Polygon" else [p for p in g.geoms if p.geom_type == "Polygon"]

def element_geom(e):
    tag = e.tag.replace(NS, ""); tf = _rot(e.attrib.get("transform"))
    if tag == "rect":
        x, y, w, h = (float(e.attrib[k]) for k in ("x", "y", "width", "height")); rx = float(e.attrib.get("rx", 0))
        g = box(x + rx, y + rx, x + w - rx, y + h - rx).buffer(rx, quad_segs=16) if rx else box(x, y, x + w, y + h)
    elif tag == "circle":
        g = Point(float(e.attrib["cx"]), float(e.attrib["cy"])).buffer(float(e.attrib["r"]), quad_segs=24)
    elif tag == "ellipse":
        cx, cy, rx, ry = (float(e.attrib[k]) for k in ("cx", "cy", "rx", "ry"))
        g = affinity.scale(Point(cx, cy).buffer(1, quad_segs=24), rx, ry, origin=(cx, cy))
    elif tag == "path":
        g = evenodd(path_rings(e.attrib["d"]))
    else:
        return None
    return tf(g).buffer(0)

def layers(path):
    """[(layer id, [dict(tag, geom, fill, attrib)])] for every top-level <g> (nested groups flattened, ids joined)."""
    root = ET.parse(path).getroot(); out = []
    def walk(g, name):
        els = []
        for ch in g:
            if ch.tag == NS + "g":
                walk(ch, ch.attrib.get("id", name))
            else:
                geo = element_geom(ch)
                if geo is not None and not geo.is_empty:
                    els.append(dict(tag=ch.tag.replace(NS, ""), geom=geo, fill=ch.attrib.get("fill", "").upper(), a=ch.attrib))
        if els: out.append((name, els))
    for g in root:
        if g.tag == NS + "g": walk(g, g.attrib.get("id"))
    return out

def layer_mask(path, keep, W, H, ppm=PPM, fill=None):
    """cairosvg render of ONLY the layers whose id starts with one of `keep` (and, if fill, only elements of that
    fill) -> bool mask at ppm px/mm. The gate reference: rendered from the founder's file, not from this parser."""
    import cairosvg
    root = ET.parse(path).getroot()
    for g in list(root):
        if g.tag == NS + "g" and not any(g.attrib.get("id", "").startswith(k) for k in keep): root.remove(g)
    if fill:
        for g in root.iter(NS + "g"):
            for ch in list(g):
                if ch.tag != NS + "g" and ch.attrib.get("fill", "").upper() != fill.upper(): g.remove(ch)
    png = cairosvg.svg2png(bytestring=ET.tostring(root), output_width=int(W * ppm), output_height=int(H * ppm))
    a = np.asarray(Image.open(io.BytesIO(png)).convert("RGBA"))
    return a[..., 3] > 127

def render_svg(path, W, H, ppm=PPM, bg="#FFFFFF"):
    import cairosvg
    png = cairosvg.svg2png(url=path, output_width=int(W * ppm), output_height=int(H * ppm), background_color=bg)
    return Image.open(io.BytesIO(png)).convert("RGB")

# ------------------------------------------------------------------ digitising helpers
def R(col, geom, st, grp, ang="auto", **kw):
    d = dict(col=col, geom=geom.buffer(0), st=st, ang=ang, grp=grp, layer=0); d.update(kw); return d

def bead(col, code, g, min_d=1.0):
    c = g.centroid; d = max(min_d, 2 * math.sqrt(g.area / math.pi) - 0.2)    # thread + pull: visible ~0.2 beyond the needle span (gate-calibrated)
    return dict(col=col, geom=Point(c.x, c.y).buffer(d / 2, quad_segs=16), st="satin", ang="knots", grp=code, layer=0,
                knots=[(c.x, c.y, d, 30.0)])

def stroke_width(P):
    """visible stroke width of an outline: median skeleton width (kjsatin.glyph_columns at 40 px/mm)."""
    ws = [s_["w"] for p in polys(P) for s_ in KS.glyph_columns(p, ppm=40.0) if KS.poly_len(s_["cl"]) > 0.8]
    return float(np.median(ws)) if ws else 2 * P.area / max(P.length, 1e-6)

def strokes(col, code, G, w, min_counter=0.6, eye=None, corner=KS.CORNER):
    """outline geometry -> satin columns of ONE needle width w on its centrelines; small rings -> radial satin on
    the exact ring; compact blobs (eyes, dots) -> round bead dots when eye is a code."""
    regs = []
    for P in polys(G):
        if P.area < 0.05: continue
        ys = np.array(P.exterior.coords); ext = ys.max(0) - ys.min(0)
        if eye and max(ext) < 2.2 and max(ext) / max(min(ext), 1e-6) < 1.5 and not P.interiors:
            regs.append(bead(col, eye, P)); continue
        if P.interiors and P.area < 8.0 and max(ext) < 4.0:        # small ring (handakuten): radial satin on it
            c = Polygon(P.interiors[0]).centroid
            regs.append(R(col, P, "satin", code, ang=("radial", c.x, c.y))); continue
        sts = KS.glyph_columns(P, ppm=40.0, corner=corner)
        for s_ in sts:
            cl = s_["cl"]; closed = s_.get("closed", False)
            L = KS.poly_len(list(cl) + ([cl[0]] if closed else []))
            if L < 0.25: continue
            if len(sts) > 1 and not closed and L < 1.1 * w: continue      # skeleton spur (heart cusps, stroke ends)
            ww = w
            if closed: ww = max(0.8 if w >= 0.8 else w, min(w, L / math.pi - (min_counter + 0.2 + KL.ALLOW)))
            regs.append(KS.column_region(col, code, cl, ww, s_["caps"], closed))
    return regs

def petals(col, code, G, tint=None, force_n=None):
    """flower / konpeito body: one turning satin per petal along its axis (centre = shape centroid)."""
    out = []
    for P in polys(G):
        if P.area < 1.0: continue
        P = Polygon(P.exterior)
        c = P.centroid
        regs, his, n = KL.petal_regions(col, None, P, (c.x, c.y), code=code, force_n=force_n)
        out += regs
    return out

# ------------------------------------------------------------------ house border from the SVG layers 01-03
def border(Ls, W, H):
    import kjart as KA
    out = []
    band_f, mot_f, edge = KA.border(W, H)[0], None, KA.border(W, H)[2]
    out_f = band_f                      # band tatami (4 trapezoids, rows across) + field (fixed mm = SVG rects 01/02)
    mot = []
    els = dict(Ls)["03_border_motifs_WHITE"]
    whites = [e for e in els if e["fill"] == "#FBF8F1"]
    reds = [e["geom"] for e in els if e["fill"] == "#C8162B"]
    pet = unary_union([e["geom"] for e in whites if e["tag"] == "ellipse"])
    for P in polys(pet):
        c = P.centroid
        hole = [r for r in reds if r.centroid.distance(c) < 0.6]
        g = P.difference(unary_union(hole)) if hole else P
        mot.append(R("kj_white", g, "satin", "BFL", ang=("radial", c.x, c.y)))
    for e in whites:
        if e["tag"] == "circle": mot.append(R("kj_white", e["geom"], "satin", "BDOT"))
    return out_f, mot, edge

# ------------------------------------------------------------------ elements
def waistband():
    path = f"{SVG}/HAKI_waistband-patch_ART.svg"; W, H = 80.0, 54.0
    Ls = layers(path); L = dict(Ls)
    out_f, mot, edge = border(Ls, W, H)
    vis = list(out_f) + list(mot); rep = {}
    G = lambda k: unary_union([e["geom"] for e in L[k]])
    def wcol(k, thread="40wt", minw=0.85):          # 40wt floor 0.85: clear of the 0.8 stitch-check minimum
        wv = stroke_width(G(k)); wn = max(minw, round(wv - KL.ALLOW, 2)); rep[k] = dict(w_art=round(wv, 2), w_needle=wn, thread=thread); return wn
    # sew order: pink (flowers + hearts), yellow, blue (flower + 理砂), white centres, rose, black, red (frame, ちひろ, dots)
    vis += petals("kj_pink", "FL", G("06_flowers_PINK"), force_n=5)
    vis += strokes("kj_pink", "TXC", G("10_hearts_PINK"), wcol("10_hearts_PINK"))
    vis += petals("kj_yellow", "FL", G("07_flower_YELLOW"), force_n=5)
    vis += petals("kj_blue", "FL", G("08_flower_BLUE"), force_n=5)
    vis += strokes("kj_blue", "TXC", G("15_signature_risa_BLUE"), wcol("15_signature_risa_BLUE"))
    vis += [bead("kj_white", "KNOT", P, 0.9) for P in polys(G("09_flower_centres_WHITE"))]
    vis += [bead("kj_rose", "DOT", P, 1.2) for P in polys(G("11_cheeks_ROSE"))]
    vis += strokes("kj_black", "LINE", G("12_face_BLACK"), wcol("12_face_BLACK", "60wt", 0.45), eye="LINE")
    vis += strokes("kj_black", "TXC", G("13_lettering_BLACK"), wcol("13_lettering_BLACK", "60wt", 0.6))
    vis += strokes("kj_red", "TXC", G("05_frame_RED"), wcol("05_frame_RED"))
    vis += strokes("kj_red", "TXC", G("14_name_chihiro_RED"), wcol("14_name_chihiro_RED"), corner=100.0)
    vis += [bead("kj_red", "DOT", P, 1.1) for P in polys(G("16_accent_dots_RED"))]
    vis.append(edge)
    REPORT["wb"] = rep
    fam = {"frame (red)": ("05_frame_RED",), "hearts (pink)": ("10_hearts_PINK",),
           "flowers (petals)": ("06_flowers_PINK", "07_flower_YELLOW", "08_flower_BLUE"), "flower centres (white)": ("09_flower_centres_WHITE",),
           "cheeks (rose)": ("11_cheeks_ROSE",), "face line art (black)": ("12_face_BLACK",), "元気でね / また会おうね (black)": ("13_lettering_BLACK",),
           "ちひろ (red)": ("14_name_chihiro_RED",), "理砂 (blue)": ("15_signature_risa_BLUE",), "accent dots (red)": ("16_accent_dots_RED",)}
    ref = {k: layer_mask(path, v, W, H) for k, v in fam.items()}
    return vis, ref, (W, H), path

def coin():
    path = f"{SVG}/HAKI_coin-pocket_konpeito_ART.svg"; W, H = 76.0, 56.0
    Ls = layers(path); L = dict(Ls)
    import kjart as KA
    out_f, _, edge, _ = KA.border(W, H, rivets=("tl", "tr"))
    _, mot, _ = border(Ls, W, H)
    vis = list(out_f) + list(mot); rep = {}
    kp = L["05_konpeito"]
    bodies = [e for e in kp if e["tag"] == "path" and COL.get(e["fill"]) in TINT_OF]
    tints = [e for e in kp if e["tag"] == "path" and COL.get(e["fill"]) in TINT_OF.values()]
    for e in sorted(bodies, key=lambda e: e["geom"].centroid.x):
        vis += petals(COL[e["fill"]], "KP", e["geom"])
    for e in sorted(tints, key=lambda e: e["geom"].centroid.x):
        vis += petals(COL[e["fill"]], "KP-hi", e["geom"])
    vis += [bead("kj_white", "KNOT", e["geom"], 0.9) for e in kp if e["tag"] == "circle"]
    Gl = unary_union([e["geom"] for e in L["04_lettering_RED"]])
    wv = stroke_width(Gl); wn = round(wv - KL.ALLOW, 2); rep["04_lettering_RED"] = dict(w_art=round(wv, 2), w_needle=wn, thread="40wt")
    vis += strokes("kj_red", "TXC", Gl, wn, corner=100.0)      # smooth rounded hand: curves stay one column
    vis += [bead("kj_red", "DOT", e["geom"], 1.1) for e in L["06_accent_dots_RED"]]
    vis.append(edge)
    REPORT["coin"] = rep
    fam = {"こんぺいとう (red)": ("04_lettering_RED",), "konpeito (lobes + tint + specks)": ("05_konpeito",), "accent dots (red)": ("06_accent_dots_RED",)}
    ref = {k: layer_mask(path, v, W, H) for k, v in fam.items()}
    return vis, ref, (W, H), path

SPILL_UNDER = 3.0       # the candies run 3 mm under the coin-pocket patch (no gap at the pocket mouth)
def spill():
    """facing konpeito: back row first, then the front row (body lobes, tint centres, white specks). File frame:
    x from the coin pocket's centre line, y = 0 on the coin pocket's top edge = art bottom - SPILL_UNDER [proposed]."""
    path = f"{SVG}/HAKI_facing_konpeito_ART.svg"; W, H = 66.0, 16.0
    Ls = layers(path)
    allg = unary_union([e["geom"] for _, els in Ls for e in els]); b = allg.bounds
    dx, dy = -W / 2 + 38.0, -(b[3] - SPILL_UNDER)          # SVG centre on the pocket centre (x 38 of the 76 patch)
    vis = []
    for name, els in Ls:
        back = name.startswith("F1")
        for e in els:
            g = affinity.translate(e["geom"], dx, dy); col = COL[e["fill"]]
            if e["tag"] == "circle": vis.append(bead("kj_white", "KNOT", g, 0.9)); continue
            code = ("KPB" if back else "KP") + ("-hi" if col in TINT_OF.values() else "")
            vis += petals(col, code, g)
    ref = {"konpeito (all)": layer_mask(path, ("F",), W, H)}
    return vis, ref, (W, H), path, (dx, dy)

def star_shapes(width=10.0):
    """STAR_Y / STAR_P from the founder's SVG, each scaled so the body is `width` mm tip to tip, centred on (0, 0)."""
    Ls = dict(layers(f"{SVG}/HAKI_back-pocket-stars_ART.svg")); out = {}
    for sid, body, hi in (("Y", "STAR_Y_1_YELLOW", "STAR_Y_2_YELLOW_HI"), ("P", "STAR_P_1_PINK", "STAR_P_2_PINK_HI")):
        gb = unary_union([e["geom"] for e in Ls[body]]); gh = unary_union([e["geom"] for e in Ls[hi]])
        bb = gb.bounds; s = width / (bb[2] - bb[0]); c = ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)
        f = lambda g: affinity.translate(affinity.scale(g, s, s, origin=c), -c[0], -c[1])
        out[sid] = (f(gb), f(gh), COL[Ls[body][0]["fill"]], COL[Ls[hi][0]["fill"]])
    return out

def star_regions(sid, cx=0.0, cy=0.0, width=10.0):
    gb, gh, cb, ch = star_shapes(width)[sid]
    gb = affinity.translate(gb, cx, cy); gh = affinity.translate(gh, cx, cy)
    return [R(cb, gb, "satin", "STAR", ang=("radial", gb.centroid.x, gb.centroid.y)),
            R(ch, gh, "satin", "STAR-hi", ang=("radial", gh.centroid.x, gh.centroid.y))]
