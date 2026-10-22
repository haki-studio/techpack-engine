"""Founder vector art (SVG) as the part source (ENGINE_PLAN M5; konpeito ENGINE_NOTES 12).

With true-size vector art (one layer per thread, layers in stitch order) there is nothing to trace: the geometry IS the
design. Promoted from projects/konpeito-jeans/kjsvg.py, generalised:

  els   = svgart.layers(path)                 # [Layer(id, order, elements=[El(tag, geom, fill, attrib)])], file order
  W, H  = svgart.size_mm(path)                # from width/height in mm, else the viewBox
  key, dE = svgart.thread_of("#C8162B", palette)     # layer -> thread by fill (exact hex, else nearest CIEDE2000)
  m     = svgart.layer_mask(path, ["13_lettering"], W, H, ppm=20)  # cairosvg render of ONLY those layers: gate reference
  ious  = svgart.parse_iou(path, ppm=20)      # {layer id: IoU(parsed geometry, cairosvg mask)}: the parser test

Parser: <path> (M L H V Q T C S A Z, absolute + relative; arcs added in S1), <rect> (rx), <circle>, <ellipse>, <polygon>, <polyline>
(filled), transforms (matrix, translate, scale, rotate with/without centre, skewX/Y, lists of them) on elements AND
groups, fill from the attribute, a <style> class rule (S1) or style (inherited from the group), fill-rule evenodd / nonzero.
Curves and arcs are flattened to <= 0.02 mm.

Coordinates: SVG user units = mm when the file is true-size (width="80mm" + viewBox 0 0 80 54); size_mm() reports the
scale so a caller can refuse a file that is not. y is DOWN, like the engine.

The gate reference is cairosvg's rendering of the founder's file, never this parser's output (LESSONS A14: a gate built
from our own geometry is circular). parse_iou() is what proves the parser reads the file the way a renderer does."""
import io, math, re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
import numpy as np
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
from shapely import affinity

NS = "{http://www.w3.org/2000/svg}"
FLAT_MM = 0.02            # max chord error when flattening curves


class SvgError(ValueError):
    pass


@dataclass
class El:
    tag: str
    geom: object
    fill: str
    attrib: dict = field(default_factory=dict)


@dataclass
class Layer:
    id: str
    order: int
    elements: list

    @property
    def geom(self):
        return unary_union([e.geom for e in self.elements]).buffer(0)

    def fills(self):
        out = []
        for e in self.elements:
            if e.fill and e.fill not in out: out.append(e.fill)
        return out


# ------------------------------------------------------------------ transforms (3x3 affine matrices)
def _m(a, b, c, d, e, f):
    return np.array([[a, c, e], [b, d, f], [0.0, 0.0, 1.0]])

I3 = np.eye(3)
_NUM = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"


def parse_transform(t):
    """SVG transform list -> 3x3 matrix (applied right to left, as SVG does)."""
    M = I3.copy()
    if not t: return M
    for name, args in re.findall(r"(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)", t):
        v = [float(x) for x in re.findall(_NUM, args)]
        if name == "matrix":
            if len(v) != 6: raise SvgError(f"matrix() needs 6 numbers: {t!r}")
            T = _m(*v)
        elif name == "translate": T = _m(1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0.0)
        elif name == "scale": T = _m(v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "rotate":
            a = math.radians(v[0]); c, s = math.cos(a), math.sin(a); R = _m(c, s, -s, c, 0, 0)
            if len(v) == 3: T = _m(1, 0, 0, 1, v[1], v[2]) @ R @ _m(1, 0, 0, 1, -v[1], -v[2])
            else: T = R
        elif name == "skewX": T = _m(1, 0, math.tan(math.radians(v[0])), 1, 0, 0)
        else: T = _m(1, math.tan(math.radians(v[0])), 0, 1, 0, 0)
        M = M @ T
    left = re.sub(r"(matrix|translate|scale|rotate|skewX|skewY)\s*\([^)]*\)", "", t).strip(" ,")
    if left: raise SvgError(f"unsupported transform {t!r}")
    return M


def apply(g, M):
    if np.allclose(M, I3): return g
    return affinity.affine_transform(g, [M[0, 0], M[0, 1], M[1, 0], M[1, 1], M[0, 2], M[1, 2]])


# ------------------------------------------------------------------ path data -> rings
def _nseg(pts, tol=FLAT_MM):
    """segments needed to flatten a Bezier with control polygon pts to <= tol"""
    L = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
    return int(min(64, max(2, math.ceil(math.sqrt(L / max(tol, 1e-6)) * 0.6))))


def path_rings(d, tol=FLAT_MM):
    """path data -> [ring [(x, y)]] (open subpaths are closed: a filled path is filled as if closed)."""
    return [r for r, _ in path_subpaths(d, tol) if len(r) > 2]


def path_subpaths(d, tol=FLAT_MM):
    """path data -> [(points, closed)] for every subpath with >= 2 points (S1: a STROKE needs to know which are open)."""
    toks = re.findall(r"[MLHVQTCSAZmlhvqtcsaz]|" + _NUM, d)
    rings, cur, i, cmd = [], [], 0, None
    pos = (0.0, 0.0); start = (0.0, 0.0); last_c = None; last_q = None; prev_cmd = None
    def num():
        nonlocal i
        if i >= len(toks) or re.match(r"[A-Za-z]", toks[i]): raise SvgError(f"path data ends early near token {i}: {d[:60]!r}")
        v = float(toks[i]); i += 1; return v
    def flag():                                        # arc flags may be packed: "a1 1 0 011 1" = flags 0, 1 then x 1
        nonlocal i
        if i >= len(toks) or toks[i][:1] not in "01": raise SvgError(f"bad arc flag near token {i}: {d[:60]!r}")
        t = toks[i]
        if len(t) > 1: toks[i] = t[1:]
        else: i += 1
        return t[0] == "1"
    while i < len(toks):
        t = toks[i]
        if re.match(r"[A-Za-z]", t): cmd = t; i += 1
        elif cmd is None: raise SvgError(f"path data starts with a number: {d[:40]!r}")
        if cmd in "Zz":
            if len(cur) >= 2: rings.append((cur, True))
            cur = []; pos = start; prev_cmd = "Z"; last_c = last_q = None; continue
        rel = cmd.islower(); C = cmd.upper(); ox, oy = pos if rel else (0.0, 0.0)
        if C == "A":                                   # S1: elliptical arcs (SVG 1.1 F.6.5, endpoint -> centre form)
            rx, ry, phi = abs(num()), abs(num()), num(); fa, fs = flag(), flag()
            p1 = (num() + ox, num() + oy)
            cur += arc_points(pos, p1, rx, ry, phi, fa, fs, tol)
            pos = p1; last_c = last_q = None; prev_cmd = C; continue
        if C == "M":
            if len(cur) >= 2: rings.append((cur, False))
            pos = (num() + ox, num() + oy); start = pos; cur = [pos]; cmd = "l" if rel else "L"; last_c = last_q = None
        elif C == "L": pos = (num() + ox, num() + oy); cur.append(pos); last_c = last_q = None
        elif C == "H": pos = (num() + ox, pos[1]); cur.append(pos); last_c = last_q = None
        elif C == "V": pos = (pos[0], num() + (pos[1] if rel else 0.0)); cur.append(pos); last_c = last_q = None
        elif C in "QT":
            p0 = np.array(pos)
            if C == "Q": p1 = np.array((num() + ox, num() + oy))
            else: p1 = 2 * p0 - np.array(last_q) if last_q is not None and prev_cmd in "QT" else p0
            p2 = np.array((num() + ox, num() + oy))
            n = _nseg([p0, p1, p2], tol)
            for s in np.linspace(0, 1, n + 1)[1:]: cur.append(tuple((1 - s) ** 2 * p0 + 2 * (1 - s) * s * p1 + s * s * p2))
            pos = tuple(p2); last_q = tuple(p1); last_c = None
        elif C in "CS":
            p0 = np.array(pos)
            if C == "C": p1 = np.array((num() + ox, num() + oy))
            else: p1 = 2 * p0 - np.array(last_c) if last_c is not None and prev_cmd in "CS" else p0
            p2 = np.array((num() + ox, num() + oy)); p3 = np.array((num() + ox, num() + oy))
            n = _nseg([p0, p1, p2, p3], tol)
            for s in np.linspace(0, 1, n + 1)[1:]:
                cur.append(tuple((1 - s) ** 3 * p0 + 3 * (1 - s) ** 2 * s * p1 + 3 * (1 - s) * s * s * p2 + s ** 3 * p3))
            pos = tuple(p3); last_c = tuple(p2); last_q = None
        else: raise SvgError(f"unsupported path command {cmd!r}")
        prev_cmd = C
    if len(cur) >= 2: rings.append((cur, False))
    return rings


def arc_points(p0, p1, rx, ry, phi_deg, large, sweep, tol=FLAT_MM):
    """points after p0 along an SVG elliptical arc to p1 (p1 included). Radii too small are scaled up, zero radii = a line,
    as the SVG spec says (F.6.6)."""
    if p0 == p1: return []
    if rx == 0 or ry == 0: return [p1]
    phi = math.radians(phi_deg % 360); c, s_ = math.cos(phi), math.sin(phi)
    dx, dy = (p0[0] - p1[0]) / 2, (p0[1] - p1[1]) / 2
    x1, y1 = c * dx + s_ * dy, -s_ * dx + c * dy
    lam = (x1 / rx) ** 2 + (y1 / ry) ** 2
    if lam > 1: rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num_ = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1; den = rx * rx * y1 * y1 + ry * ry * x1 * x1
    k = math.sqrt(max(0.0, num_ / den)) if den else 0.0
    if large == sweep: k = -k
    cx1, cy1 = k * rx * y1 / ry, -k * ry * x1 / rx
    cx, cy = c * cx1 - s_ * cy1 + (p0[0] + p1[0]) / 2, s_ * cx1 + c * cy1 + (p0[1] + p1[1]) / 2
    ang = lambda ux, uy, vx, vy: math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
    t1 = ang(1, 0, (x1 - cx1) / rx, (y1 - cy1) / ry)
    dt = ang((x1 - cx1) / rx, (y1 - cy1) / ry, (-x1 - cx1) / rx, (-y1 - cy1) / ry)
    if not sweep and dt > 0: dt -= 2 * math.pi
    elif sweep and dt < 0: dt += 2 * math.pi
    r = max(rx, ry); n = int(min(256, max(2, math.ceil(abs(dt) / max(2 * math.acos(max(-1.0, 1 - tol / r)), 1e-3)))))
    out = []
    for t in np.linspace(t1, t1 + dt, n + 1)[1:]:
        ex, ey = rx * math.cos(t), ry * math.sin(t)
        out.append((c * ex - s_ * ey + cx, s_ * ex + c * ey + cy))
    out[-1] = tuple(p1)
    return out


def evenodd(rings):
    g = Polygon()
    for r in sorted([Polygon(r).buffer(0) for r in rings], key=lambda p: -p.area):
        g = g.symmetric_difference(r)
    return g.buffer(0)


def nonzero(rings):
    """nonzero winding: a ring wound against its enclosing ring is a hole; same-wound rings add."""
    def signed(r):
        a = np.array(r); return 0.5 * float(np.sum(a[:, 0] * np.roll(a[:, 1], -1) - np.roll(a[:, 0], -1) * a[:, 1]))
    rs = sorted([(Polygon(r).buffer(0), signed(r)) for r in rings if len(r) > 2], key=lambda t: -t[0].area)
    g = Polygon(); placed = []
    for p, s in rs:
        if p.is_empty: continue
        par = [ps for pp, ps in placed if pp.contains(p.representative_point())]
        if par and (par[-1] > 0) != (s > 0): g = g.difference(p)
        else: g = g.union(p)
        placed.append((p, s))
    return g.buffer(0)


def polys(g):
    if g.is_empty: return []
    return [g] if g.geom_type == "Polygon" else [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]


# ------------------------------------------------------------------ elements + layers
def _style(e):
    st = {}
    for kv in (e.attrib.get("style") or "").split(";"):
        if ":" in kv: k, v = kv.split(":", 1); st[k.strip()] = v.strip()
    return st


def _attr(e, k, inh=None):
    st = _style(e)
    return st.get(k, e.attrib.get(k, inh))


def _norm_fill(f):
    if f is None: return ""
    f = f.strip()
    if f.lower() in ("none", "transparent", ""): return ""
    if re.fullmatch(r"#[0-9a-fA-F]{3}", f): f = "#" + "".join(c * 2 for c in f[1:])
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", f) and not f.lower().startswith("url("):    # S1: rgb(), CSS colour names
        try:
            from PIL import ImageColor
            f = "#%02X%02X%02X" % ImageColor.getrgb(f)[:3]
        except ValueError: pass
    return f.upper()


def element_geom(e, M=I3, fill_rule="nonzero"):
    tag = e.tag.replace(NS, ""); A = e.attrib; fr = _attr(e, "fill-rule", fill_rule)
    f = lambda k, d=0.0: float(A.get(k, d))
    if tag == "rect":
        x, y, w, h = f("x"), f("y"), f("width"), f("height"); rx = f("rx", A.get("ry", 0)); rx = min(rx, w / 2, h / 2)
        g = box(x + rx, y + rx, x + w - rx, y + h - rx).buffer(rx, quad_segs=16) if rx > 0 else box(x, y, x + w, y + h)
    elif tag == "circle":
        g = Point(f("cx"), f("cy")).buffer(f("r"), quad_segs=24)
    elif tag == "ellipse":
        cx, cy = f("cx"), f("cy")
        g = affinity.scale(Point(cx, cy).buffer(1, quad_segs=24), f("rx"), f("ry"), origin=(cx, cy))
    elif tag == "path":
        rings = path_rings(A.get("d", ""))
        if not rings: return None
        g = evenodd(rings) if fr == "evenodd" else nonzero(rings)
    elif tag in ("polygon", "polyline"):
        v = [float(x) for x in re.findall(_NUM, A.get("points", ""))]
        if len(v) < 6: return None
        g = Polygon(list(zip(v[0::2], v[1::2]))).buffer(0)
    else:
        return None
    return apply(g, M @ parse_transform(A.get("transform"))).buffer(0)


def _num_attr(v, default):
    m = re.match(r"\s*(" + _NUM + ")", str(v)) if v is not None else None
    return float(m.group(1)) if m else default


def element_lines(e):
    """the element's outline as [(points, closed)] in its own coordinates (what a stroke follows)"""
    tag = e.tag.replace(NS, ""); A = e.attrib; f = lambda k, d=0.0: float(A.get(k, d))
    if tag == "path": return path_subpaths(A.get("d", ""))
    if tag == "line": return [([(f("x1"), f("y1")), (f("x2"), f("y2"))], False)]
    if tag in ("polygon", "polyline"):
        v = [float(x) for x in re.findall(_NUM, A.get("points", ""))]
        return [(list(zip(v[0::2], v[1::2])), tag == "polygon")] if len(v) >= 4 else []
    if tag in ("rect", "circle", "ellipse"):
        g = element_geom(e, I3)
        return [(list(q.exterior.coords)[:-1], True) for q in polys(g)] if g is not None else []
    return []


def stroke_geom(e, M=I3, width=1.0, cap="butt", join="miter", miter=4.0):
    """S1: a stroked outline -> the filled area the stroke paints (shapely buffer of the outline, then the transform,
    so a scaled group scales the stroke the way a renderer does)"""
    from shapely.geometry import LineString, LinearRing
    capm = {"butt": "flat", "round": "round", "square": "square"}.get(cap, "flat")
    joinm = {"miter": "mitre", "round": "round", "bevel": "bevel", "miter-clip": "mitre", "arcs": "round"}.get(join, "mitre")
    parts = []
    for pts, closed in element_lines(e):
        pts = [tuple(map(float, q)) for q in pts]
        if closed and len(pts) >= 3: ln = LinearRing(pts)
        elif len(pts) >= 2 and pts[0] != pts[-1]: ln = LineString(pts)
        else: continue
        parts.append(ln.buffer(width / 2, cap_style=capm, join_style=joinm, mitre_limit=max(1.0, miter)))
    if not parts: return None
    return apply(unary_union(parts), M @ parse_transform(e.attrib.get("transform"))).buffer(0)


def _apply_css(root):
    """S1: <style> class rules (.a, .b {fill: #..}) folded into each element's style attribute (inline style still wins).
    Drawing tools (Illustrator) export fills this way; without it every shape read as the default black."""
    css = {}
    for st in root.iter(NS + "style"):
        txt = re.sub(r"/\*.*?\*/", "", st.text or "", flags=re.S)
        for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", txt):
            for one in sel.split(","):
                one = one.strip()
                if re.fullmatch(r"\.[A-Za-z0-9_-]+", one): css.setdefault(one[1:], []).append(body.strip())
    if not css: return
    for e in root.iter():
        cls = e.attrib.get("class")
        if not cls: continue
        decl = ";".join(b for c in cls.split() for b in css.get(c, []))
        if decl: e.set("style", decl + ";" + e.attrib.get("style", ""))


def layers(path):
    """[Layer] for every <g> that directly holds shapes, in FILE order (= stitch order for founder files). A nested
    group becomes its own layer under its own id (STAR_Y > STAR_Y_1_YELLOW, STAR_Y_2_YELLOW_HI); shapes outside any
    group go to a layer named '_root'. Group transforms and fills are inherited."""
    root = ET.parse(path).getroot(); out = []; _apply_css(root)
    def walk(g, name, M, fill, fr, sk):
        els = []
        for ch in g:
            tag = ch.tag.replace(NS, "")
            if tag in ("defs", "title", "desc", "metadata", "style", "clipPath", "mask", "symbol"): continue
            if tag == "g":
                ssk = {k: _attr(ch, k, sk.get(k)) for k in STROKE_KEYS}
                walk(ch, ch.attrib.get("id", name), M @ parse_transform(ch.attrib.get("transform")),
                     _attr(ch, "fill", fill), _attr(ch, "fill-rule", fr), ssk)
                continue
            if tag == "use": raise SvgError(f"{path}: <use> is not supported (expand symbols in the drawing tool)")
            if tag == "line": geo = None
            else: geo = element_geom(ch, M, _attr(ch, "fill-rule", fr))
            f = _norm_fill(_attr(ch, "fill", fill if fill is not None else "#000000"))
            if geo is not None and not geo.is_empty and f:           # fill="none" paints nothing (S1: no longer kept)
                els.append(El(tag=tag, geom=geo, fill=f, attrib=dict(ch.attrib)))
            st = {k: _attr(ch, k, sk.get(k)) for k in STROKE_KEYS}; sc = _norm_fill(st["stroke"])
            sw = _num_attr(st["stroke-width"], 1.0)
            if sc and sw > 0:                                        # S1: a stroke paints on top of the fill
                sg = stroke_geom(ch, M, sw, st["stroke-linecap"] or "butt", st["stroke-linejoin"] or "miter",
                                 _num_attr(st["stroke-miterlimit"], 4.0))
                if sg is not None and not sg.is_empty:
                    els.append(El(tag="stroke", geom=sg, fill=sc, attrib=dict(ch.attrib, _stroke_width=str(sw))))
        if els: out.append(Layer(id=name, order=len(out), elements=els))
    walk(root, "_root", parse_transform(root.attrib.get("transform")), None, "nonzero",
         {k: _attr(root, k, None) for k in STROKE_KEYS})
    return out


STROKE_KEYS = ("stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-miterlimit")


def size_mm(path):
    """(W, H) of the art in mm and the user-unit scale (mm per unit). Raises unless width/height are in mm (or the
    file has only a viewBox, then 1 unit = 1 mm is ASSUMED and reported)."""
    root = ET.parse(path).getroot(); vb = [float(v) for v in re.findall(_NUM, root.attrib.get("viewBox", ""))]
    def mm(s):
        if s is None: return None
        m = re.fullmatch(r"\s*(" + _NUM + r")\s*(mm|cm|in|px|pt)?\s*", s)
        if not m: return None
        v = float(m.group(1)); u = m.group(2) or "px"
        return v * {"mm": 1.0, "cm": 10.0, "in": 25.4, "px": 25.4 / 96, "pt": 25.4 / 72}[u]
    W, H = mm(root.attrib.get("width")), mm(root.attrib.get("height"))
    if W is None or H is None:
        if len(vb) != 4: raise SvgError(f"{path}: no width/height and no viewBox")
        return vb[2], vb[3], 1.0
    scale = W / vb[2] if len(vb) == 4 and vb[2] else 1.0
    return W, H, scale


# ------------------------------------------------------------------ colours -> threads
def thread_of(fill, palette):
    """(thread key, dE) for an SVG fill: an exact hex match first (dE 0), else the nearest palette colour by CIEDE2000.
    palette: {key: "#RRGGBB"}. The caller decides how large a dE it accepts (extract/svg raises above its limit)."""
    f = _norm_fill(fill)
    for k, h in palette.items():
        if _norm_fill(h) == f: return k, 0.0
    from digitize.extract.evidence import to_lab, hex_rgb, delta_e
    keys = list(palette)
    lab = to_lab(np.array([[hex_rgb(palette[k]) for k in keys]], float))[0]
    q = to_lab(np.array([[hex_rgb(f)]], float))[0]
    d = delta_e(np.repeat(q, len(keys), axis=0), lab)
    j = int(np.argmin(d)); return keys[j], round(float(d[j]), 1)


# ------------------------------------------------------------------ rendering (cairosvg): the gate reference
def _keep_tree(path, keep, fill=None, els=None, exact=False):
    """the SVG with only the shapes inside a group whose id starts with one of `keep` (at any depth); S1: and, if `els`, only
    the shapes whose data-s1 number is in it (one family of a mixed layer)"""
    tree = ET.parse(path); root = tree.getroot()
    def prune(g, kept):
        any_kept = False
        for ch in list(g):
            tag = ch.tag.replace(NS, "")
            if tag == "g":
                gid = ch.attrib.get("id", "")
                k = kept or any((gid == p) if exact else gid.startswith(p) for p in keep)
                if prune(ch, k): any_kept = True
                else: g.remove(ch)
            elif tag in ("defs", "style"): continue
            else:
                ok = kept and (fill is None or _norm_fill(_attr(ch, "fill", "")) == _norm_fill(fill)) \
                    and (els is None or ch.attrib.get("data-s1") in els)
                if ok: any_kept = True
                else: g.remove(ch)
        return any_kept
    prune(root, "_root" in keep)
    return root


def layer_mask(path, keep, W, H, ppm=20.0, fill=None, els=None, exact=False):
    """cairosvg render of ONLY the layers whose id starts with one of `keep` (and, if fill, only shapes of that fill)
    -> bool mask (H*ppm, W*ppm). The gate reference: rendered from the founder's file, not from this parser."""
    import cairosvg
    from PIL import Image
    root = _keep_tree(path, list(keep), fill, els, exact)
    png = cairosvg.svg2png(bytestring=ET.tostring(root), output_width=int(round(W * ppm)), output_height=int(round(H * ppm)), unsafe=False)
    a = np.asarray(Image.open(io.BytesIO(png)).convert("RGBA"))
    return a[..., 3] > 127


def render(path, W, H, ppm=20.0, bg="#FFFFFF"):
    import cairosvg
    from PIL import Image
    png = cairosvg.svg2png(url=path, output_width=int(round(W * ppm)), output_height=int(round(H * ppm)), background_color=bg, unsafe=False)
    return Image.open(io.BytesIO(png)).convert("RGB")


def to_svg(g, W, H, fill="#000000"):
    """shapely geometry -> an SVG document (one evenodd path per polygon), W x H mm"""
    ds = []
    for p in polys(g):
        for ring in [p.exterior] + list(p.interiors):
            cs = list(ring.coords)
            ds.append("M" + " L".join(f"{x:.4f} {y:.4f}" for x, y in cs) + " Z")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}">'
            f'<path fill="{fill}" fill-rule="evenodd" d="{" ".join(ds)}"/></svg>')


def raster(g, W, H, ppm=20.0):
    """bool mask of shapely geometry on the same grid as layer_mask, drawn by the SAME renderer (cairosvg), so a
    comparison measures geometry differences, not two rasterisers' edge rules (1 px of a 14 px line = 7 % IoU)."""
    import cairosvg
    from PIL import Image
    png = cairosvg.svg2png(bytestring=to_svg(g, W, H).encode(), output_width=int(round(W * ppm)), output_height=int(round(H * ppm)), unsafe=False)
    return np.asarray(Image.open(io.BytesIO(png)).convert("RGBA"))[..., 3] > 127


def parse_iou(path, ppm=20.0, layer_ids=None):
    """{layer id: IoU(parsed geometry raster, cairosvg mask of that layer)}. A layer whose later shapes cover earlier
    ones is fine: both sides are the union of the layer's shapes."""
    W, H, _ = size_mm(path); out = {}
    for L in layers(path):
        if layer_ids and L.id not in layer_ids: continue
        ref = layer_mask(path, [L.id], W, H, ppm)
        # an id that prefixes another layer's id would render both: compare against the union of those layers
        same = [M for M in layers(path) if M.id.startswith(L.id)]
        got = raster(unary_union([M.geom for M in same]), W, H, ppm)
        out[L.id] = round(float((ref & got).sum() / max((ref | got).sum(), 1)), 4)
    return out


def art_read(path, ppm=10.0):
    """S1: did the parser read EVERYTHING the renderer paints? IoU of the whole file's cairosvg alpha vs the union of the
    parsed layers, drawn by the same renderer. Text, images, gradients and anything else the parser skips lower it;
    svg2dst makes it a hard gate (a shape we did not read would silently not be sewn)."""
    import cairosvg
    from PIL import Image
    W, H, _ = size_mm(path)
    png = cairosvg.svg2png(url=path, output_width=int(round(W * ppm)), output_height=int(round(H * ppm)), unsafe=False)
    ref = np.asarray(Image.open(io.BytesIO(png)).convert("RGBA"))[..., 3] > 127
    Ls = layers(path)
    got = raster(unary_union([L.geom for L in Ls]), W, H, ppm) if Ls else np.zeros_like(ref)
    return round(float((ref & got).sum() / max((ref | got).sum(), 1)), 4)
