"""S1 SVG drop-in (ENGINE_PLAN S1): the run config for `digitize.svgrun`, derived from a bare SVG by GEOMETRY ONLY.
No Anthropic API calls. Layer ids and names are never read (tests rename every layer and get the same parts).

  norm, info = svg_auto.normalize(src_svg, out_svg, width_mm)   # art scaled to its finished width: 1 user unit = 1 mm
  auto = svg_auto.derive(norm_svg, fabric="twill", answers={})   # dict(cfg, questions, report, warnings)
  svg_auto.fill_config(cfg)                                      # in place, for a run.yaml with no palette / layers

What M5 needed a person to write in run.yaml, derived here:
  threads    every fill -> the nearest Isacord thread (engine/pal/threads.json, CIEDE2000), dE reported per fill; two fills
             never share a thread unless they are within MERGE_DE of each other (then the merge is reported)
  weight     a thread that only sews strokes <= FINE_T mm thick -> 60wt (a question, default 60wt)
  roles      a patch (a rectangle holding all the art + an inset rectangle of another colour) -> patch_border + field;
             ellipse clusters (>= 4 touching ellipses) -> border_motifs (florets); every other shape is classified alone:
               dot     round (circularity >= DOT_CIRC) and <= DOT_MAX_D across -> bead dot (knot below KNOT_D)
               stroke  length / thickness (area / T^2, T = largest inscribed circle) >= STROKE_E and T <= 7 mm
                       (rule 4) -> satin column across the stroke (strokes pooled per colour, like the M5 column role)
               star    5 regular points (polar profile) and hull / area >= STAR_HULL -> radial from the centre
               petals  3-8 lobes with valleys -> one turning satin per lobe; a lobe shape sitting on another colour = tint
               fill    everything else -> tatami at the shape's LONG AXIS (minimum rotated rectangle), declared, never auto
  scale      normalize(): the art (drawn bounds) is scaled to width_mm before anything is measured, so every threshold
             above is in finished mm
  fabric     rules/fabrics.yaml deltas, applied by svgrun.make_plan (twill / denim = the house numbers)
Low confidence = a shape within BORDER of a threshold, or a patch guess: a review QUESTION with a stable id (topic + layer
+ hash), default = what this run does; answers.json picks the other option next run, and an answered question is not
asked again."""
import hashlib, io, json, math, os, re
import xml.etree.ElementTree as ET
import numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union, polylabel
from shapely.strtree import STRtree
from scipy import ndimage as ndi
import svgart

DOT_CIRC, DOT_MAX_D, KNOT_D = 0.85, 3.0, 1.3
STROKE_E, STROKE_MAX_T = 1.6, 7.0
STAR_HULL, STAR_N, STAR_ASK = 1.12, 5, 0.03     # 5 regular points, hull/area >= 1.12; ask within +-0.03
TINT_BODY = 8.0               # a lobe on a shape at most 8x its area is that shape's tint (a patch field is not a body)
FILL_MIN_T = 4.0              # rule 4: fill only where >= ~5 mm wide; below 4 mm a stroke is never asked about as a fill
LOBE_HULL, LOBE_VD = 1.03, 0.9
FINE_T = 1.0
BORDER = 0.15                 # within 15 % of a threshold -> ask
MERGE_DE = 3.0                # two design colours closer than this share one thread
FAR_DE = 6.0                  # nearest Isacord further than this -> warning (the thread card decides)
PATCH_RECT = 0.97             # area / minimum rotated rectangle: the patch outline must be a rectangle (band trapezoids)
PATCH_BAND = (2.0, 15.0)      # band width range between the outline and the field, mm
TAG = "data-s1"               # normalize() numbers every shape element; parts and gates use it to find their source shapes
SVG_NS = "http://www.w3.org/2000/svg"
SHAPES = ("path", "rect", "circle", "ellipse", "polygon", "polyline", "line")
HERE = os.path.dirname(os.path.abspath(__file__))


class AutoError(ValueError):
    """the SVG cannot be digitised as given; the message says what to change in the file"""


# ------------------------------------------------------------------ normalize: finished size, numbered shapes
def _vb(root):
    v = [float(x) for x in re.findall(svgart._NUM, root.attrib.get("viewBox", ""))]
    if len(v) == 4 and v[2] > 0 and v[3] > 0: return v
    w, h = (svgart._num_attr(root.attrib.get(k), None) for k in ("width", "height"))
    if not w or not h: raise AutoError("the SVG has no viewBox and no width/height: re-export it with a size")
    return [0.0, 0.0, w, h]


def _gradients(root):
    """{id: mean stop colour hex} for linear / radial gradients (a gradient cannot be one thread: flattened + warned)"""
    out = {}
    for tag in ("linearGradient", "radialGradient"):
        for g in root.iter(f"{{{SVG_NS}}}{tag}"):
            cols = []
            for st in g.iter(f"{{{SVG_NS}}}stop"):
                c = svgart._norm_fill(svgart._attr(st, "stop-color", "#000000"))
                if re.fullmatch(r"#[0-9A-F]{6}", c): cols.append([int(c[i:i + 2], 16) for i in (1, 3, 5)])
            if cols: out[g.attrib.get("id", "")] = "#%02X%02X%02X" % tuple(int(round(v)) for v in np.mean(cols, axis=0))
    return out


def _painted_bounds(path, vb):
    """bounds (user units) of what cairosvg paints: catches art the parser does not read (text, images)"""
    import cairosvg
    from PIL import Image
    px = 1200; png = cairosvg.svg2png(url=path, output_width=px, output_height=int(round(px * vb[3] / vb[2])), unsafe=False)
    a = np.asarray(Image.open(io.BytesIO(png)).convert("RGBA"))[..., 3] > 0
    if not a.any(): return None
    ys, xs = np.where(a); k = vb[2] / px
    return (vb[0] + xs.min() * k, vb[1] + ys.min() * k, vb[0] + (xs.max() + 1) * k, vb[1] + (ys.max() + 1) * k)


def normalize(src, dst, width_mm, margin_mm=1.0):
    """src SVG -> dst SVG whose user unit is a FINISHED mm: the drawn art is width_mm wide, the canvas is cropped to the art
    + margin, every shape element carries data-s1="<n>", gradients are flattened to their mean stop colour. The shapes are
    the founder's, only scaled: the gate reference stays cairosvg's render of this file (LESSONS A14).
    -> (dst, info dict(scale, art_mm [w, h], warnings))"""
    ET.register_namespace("", SVG_NS); ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
    tree = ET.parse(src); root = tree.getroot(); warnings = []
    if root.tag != f"{{{SVG_NS}}}svg": raise AutoError("the root element is not an SVG <svg> (missing the SVG namespace?)")
    vb = _vb(root)
    grads = _gradients(root); n = 0
    for e in root.iter():
        tag = e.tag.replace(f"{{{SVG_NS}}}", "")
        if tag in ("text", "image", "foreignObject"):
            warnings.append(f"the SVG has a <{tag}> element: it is not digitised (convert text to outlines, trace images); "
                            f"the 'every shape read' gate fails while it is there")
        if tag in SHAPES: n += 1; e.set(TAG, str(n))
        for k in ("fill", "stroke"):
            for where in ("attr", "style"):
                v = e.attrib.get(k) if where == "attr" else svgart._style(e).get(k)
                m = re.fullmatch(r"\s*url\(\s*#([^)\s]+)\s*\)\s*", v or "")
                if not m: continue
                hexc = grads.get(m.group(1))
                if hexc is None: continue
                if where == "attr": e.set(k, hexc)
                else: e.set("style", re.sub(rf"{k}\s*:\s*url\([^)]*\)", f"{k}:{hexc}", e.attrib["style"]))
                warnings.append(f"a gradient fill was flattened to its mean colour {hexc} (one thread per shape)")
        op = min(svgart._num_attr(svgart._attr(e, a, "1"), 1.0) for a in ("opacity", "fill-opacity"))
        if op < 0.999 and tag in SHAPES: warnings.append(f"shape {n} is {op:.0%} opaque: sewn as a solid colour")
    tmp = dst + ".tmp.svg"; tree.write(tmp, xml_declaration=False, encoding="unicode")
    Ls = svgart.layers(tmp)
    if not Ls: os.remove(tmp); raise AutoError("the SVG has no filled shapes the engine can read (paths, rects, circles ...)")
    b = unary_union([L.geom for L in Ls]).bounds
    pb = _painted_bounds(tmp, vb)                    # unread art (text, images) outside the shapes widens the canvas
    if pb and max(b[0] - pb[0], b[1] - pb[1], pb[2] - b[2], pb[3] - b[3]) > 0.01 * max(vb[2], vb[3]):
        b = (min(b[0], pb[0]), min(b[1], pb[1]), max(b[2], pb[2]), max(b[3], pb[3]))
    os.remove(tmp)
    if b[2] - b[0] <= 0: raise AutoError("the art has no width")
    s = float(width_mm) / (b[2] - b[0]); m = margin_mm / s
    x0, y0, w, h = b[0] - m, b[1] - m, (b[2] - b[0]) + 2 * m, (b[3] - b[1]) + 2 * m
    W, H = w * s, h * s
    wrap = ET.Element(f"{{{SVG_NS}}}g", {"transform": f"scale({s:.10g}) translate({-x0:.10g} {-y0:.10g})"})
    for ch in list(root): root.remove(ch); wrap.append(ch)
    root.append(wrap)
    for k in ("width", "height", "viewBox", "preserveAspectRatio", "x", "y"): root.attrib.pop(k, None)
    root.set("width", f"{W:.4f}mm"); root.set("height", f"{H:.4f}mm"); root.set("viewBox", f"0 0 {W:.4f} {H:.4f}")
    tree.write(dst, xml_declaration=False, encoding="unicode")
    return dst, dict(scale=round(s, 6), art_mm=[round((b[2] - b[0]) * s, 2), round((b[3] - b[1]) * s, 2)],
                     canvas_mm=[round(W, 2), round(H, 2)], shapes=n, warnings=sorted(set(warnings)))


# ------------------------------------------------------------------ shape features
def _deg(a): return float(a % 180.0)


def long_axis(P):
    """angle (deg, 0..180) of the long side of P's minimum rotated rectangle; a square takes the side nearest 0 deg"""
    r = P.minimum_rotated_rectangle
    cs = list(r.exterior.coords) if r.geom_type == "Polygon" else list(P.exterior.coords)
    sides = [(math.dist(cs[i], cs[i + 1]), math.degrees(math.atan2(cs[i + 1][1] - cs[i][1], cs[i + 1][0] - cs[i][0])) % 180.0)
             for i in range(min(4, len(cs) - 1))]
    L = max(s[0] for s in sides)
    cand = [a for l, a in sides if l >= L * 0.98]
    a = min(cand, key=lambda a: min(a, 180 - a))
    return round(_deg(round(a, 1)), 1)


def features(P):
    A = P.area; per = P.exterior.length or 1e-9
    c = polylabel(P, tolerance=0.01); T = 2 * P.boundary.distance(c) if not P.is_empty else 0.0
    f = dict(area=A, circ=4 * math.pi * A / per ** 2, hull=P.convex_hull.area / max(A, 1e-9), T=T,
             E=A / max(T * T, 1e-9), d_eq=2 * math.sqrt(A / math.pi), holes=len(P.interiors))
    b = P.bounds; f["ext"] = max(b[2] - b[0], b[3] - b[1])
    f["pk"], f["vd"], f["gap_sd"] = 0, 1.0, 99.0
    if A >= 1.0 and not P.interiors:
        from digitize.extract.svg import polar_profile
        cc = P.centroid; r = polar_profile(P, (cc.x, cc.y)); rs = ndi.gaussian_filter1d(r, 4, mode="wrap")
        pk = [i for i in range(360) if rs[i] >= rs[i - 1] and rs[i] > rs[(i + 1) % 360] and rs[i] > 0.6 * rs.max()]
        f["pk"] = len(pk); f["vd"] = float(rs.min() / max(rs.max(), 1e-9))
        if len(pk) >= 2:
            g = np.diff(sorted(pk) + [sorted(pk)[0] + 360]); f["gap_sd"] = float(np.std(g))
    return f


def classify(f):
    """-> (class, borderline topic or None). class in dot, knot, stroke, star, petals, fill"""
    near = lambda v, t: abs(v - t) <= BORDER * t
    if f["circ"] >= DOT_CIRC and f["d_eq"] <= DOT_MAX_D and f["hull"] <= 1.05 and not f["holes"]:
        return ("knot" if f["d_eq"] < KNOT_D else "dot"), None
    if f["E"] >= STROKE_E and f["T"] <= STROKE_MAX_T:
        bl = "stroke-fill" if (near(f["E"], STROKE_E) and f["T"] >= FILL_MIN_T) or near(f["T"], STROKE_MAX_T) else None
        return "stroke", bl
    if f["T"] < 0.8:                                            # too thin for a fill: a column (rule 4), the house minimum reports
        return "stroke", None
    lobed = f["hull"] >= LOBE_HULL and 3 <= f["pk"] <= 8 and f["vd"] <= LOBE_VD
    if lobed:
        star = f["pk"] == STAR_N and f["hull"] >= STAR_HULL and f["gap_sd"] < 6.0
        bl = "star-petals" if abs(f["hull"] - STAR_HULL) <= STAR_ASK and f["pk"] == STAR_N else None
        return ("star" if star else "petals"), bl
    bl = "stroke-fill" if near(f["E"], STROKE_E) and f["T"] <= STROKE_MAX_T else None
    return "fill", bl


# ------------------------------------------------------------------ threads
def _isacord():
    th = json.load(open(os.path.join(os.path.dirname(os.path.dirname(HERE)), "pal", "threads.json")))
    return [(code, name, "#%02X%02X%02X" % tuple(rgb)) for code, name, rgb in th["isacord"]]


def match_threads(fills):
    """design fills -> {fill: dict(code, name, hex, dE, merged_into)}. Each fill takes its nearest Isacord (CIEDE2000) that
    no other fill has taken; a fill within MERGE_DE of an earlier fill shares that fill's thread (reported)."""
    from digitize.extract.evidence import to_lab, hex_rgb, delta_e
    book = _isacord(); seen = set(); uniq = []
    for c, n, h in book:                                         # the book lists some RGB twice (0015 / 0017): keep the first
        if h in seen: continue
        seen.add(h); uniq.append((c, n, h))
    lab_b = to_lab(np.array([[hex_rgb(h) for _, _, h in uniq]], float))[0]
    out = {}; taken = set(); placed = []
    for f in fills:
        q = to_lab(np.array([[hex_rgb(f)]], float))[0]
        for g, lab_g in placed:
            d = float(delta_e(q, lab_g)[0])
            if d < MERGE_DE:
                out[f] = dict(out[g], merged_into=g, dE_to=round(d, 1)); break
        else:
            d = delta_e(np.repeat(q, len(uniq), axis=0), lab_b)
            for j in np.argsort(d):
                if uniq[j][0] not in taken:
                    c, n, h = uniq[j]; taken.add(c)
                    out[f] = dict(code=c, name=n, hex=h, dE=round(float(d[j]), 1), merged_into=None,
                                  nearest_taken=bool(j != int(np.argmin(d))))
                    break
            placed.append((f, q))
    return out


# ------------------------------------------------------------------ questions
def _qid(topic, layer, extra=""):
    s = re.sub(r"[^A-Za-z0-9]+", "-", layer).strip("-")[:28] or "root"
    h = hashlib.sha1(f"{layer}|{extra}".encode()).hexdigest()[:6]
    return f"{topic}:{s}:{h}"[:80]


class _Q:
    def __init__(self, answers):
        self.answers = dict(answers or {}); self.asked = []; self.used = set()

    def ask(self, qid, topic, text, options, default, effect, part_hint=None):
        """the answer if one was given (the question is then not asked again), else the default and the question"""
        if qid in self.answers:
            a = self.answers[qid]; self.used.add(qid)
            if a not in options: raise AutoError(f"answer {a!r} to {qid} is not one of {options}")
            return a
        self.asked.append(dict(id=qid, topic=topic, text=text[:900], options=list(options), default=default, effect=effect,
                               part_ids=[], about=part_hint or {}))
        return default


# ------------------------------------------------------------------ derive
def _is_rect(P): return P.area / max(P.minimum_rotated_rectangle.area, 1e-9) >= PATCH_RECT and not P.interiors


def _patch(Ls):
    """(outline layer, field layer) when the art is a patch: the first layer is ONE rectangle holding every later shape, and
    a later layer is one rectangle of another colour inset by a band of PATCH_BAND mm on every side"""
    if len(Ls) < 2: return None
    L0 = Ls[0]; P0 = L0.geom
    if len(L0.elements) != 1 or P0.geom_type != "Polygon" or not _is_rect(P0) or len(L0.fills()) != 1: return None
    rest = unary_union([L.geom for L in Ls[1:]])
    if not P0.buffer(0.05).contains(rest): return None
    for L in Ls[1:]:
        G = L.geom
        if len(L.elements) != 1 or G.geom_type != "Polygon" or not _is_rect(G) or L.fills() == L0.fills(): continue
        if not P0.contains(G): continue
        d_min = P0.exterior.distance(G.exterior); d_max = G.exterior.hausdorff_distance(P0.exterior)
        if PATCH_BAND[0] <= d_min and d_max <= PATCH_BAND[1] and G.area >= 0.4 * P0.area: return L0, L
    return None


def _floret_layer(L):
    """True when the layer's shapes are mostly ellipse clusters (>= 4 touching ellipses of one colour = a floret)"""
    els = [e for e in L.elements if e.tag == "ellipse"]
    if len(els) < 4: return False
    by = {}
    for e in els: by.setdefault(e.fill, []).append(e.geom)
    main = max(by, key=lambda f: len(by[f]))
    groups = svgart.polys(unary_union([g.buffer(0.01) for g in by[main]]))
    tree = STRtree(by[main]); n4 = 0
    for G in groups:
        k = sum(1 for i in tree.query(G) if by[main][i].intersects(G))
        if k >= 4: n4 += 1
    main_area = sum(e.geom.area for e in L.elements if e.fill == main)
    return n4 >= 1 and sum(g.area for g in by[main]) >= 0.6 * main_area


def derive(norm_svg, fabric="twill", answers=None):
    """-> dict(cfg=<run.yaml fragment for svgrun>, questions=[...], report=dict(...), warnings=[...])"""
    Ls = svgart.layers(norm_svg); W, H, scale = svgart.size_mm(norm_svg)
    if abs(scale - 1.0) > 1e-6: raise AutoError(f"{norm_svg}: user units are {scale} mm; run normalize() first")
    Q = _Q(answers); warnings = []; specs = {}; report = dict(layers=[], shapes={})
    pat = _patch(Ls)
    if pat:
        L0, LF = pat
        a = Q.ask(_qid("patch", L0.id), "patch",
                  f"The art looks like a PATCH: a {L0.geom.bounds[2] - L0.geom.bounds[0]:.0f} x {L0.geom.bounds[3] - L0.geom.bounds[1]:.0f} mm "
                  f"rectangle with an inset field of another colour. Sew it as a patch (band across the border + a 2 mm heat-cut "
                  f"satin edge sewn last), or as flat art on the garment (both rectangles plain fills)?",
                  ["patch", "flat art"], "patch", "flat art: the outline and the field become fills at their long axis")
        if a == "patch":
            specs[L0.id] = dict(role="patch_border", inner=LF.id, edge_w=2.0)
            specs[LF.id] = dict(role="field", dir=long_axis(LF.geom), grow=0.3)
    # every shape, in paint order, for the 'sits on another colour' test (tints) and per-thread facts
    allp = []
    for L in Ls:
        for i, e in enumerate(L.elements):
            for j, P in enumerate(svgart.polys(e.geom)): allp.append(dict(L=L, i=i, j=j, e=e, P=P))
    geoms = [r["P"] for r in allp]; tree = STRtree(geoms) if geoms else None
    def on_other(k):
        P = allp[k]["P"]
        for m in tree.query(P):
            if m >= k or allp[m]["e"].fill == allp[k]["e"].fill: continue
            if geoms[m].area <= TINT_BODY * P.area and geoms[m].intersection(P).area >= 0.9 * P.area: return True
        return False
    use = {}                                                     # fill -> [(class, T)]
    for r in allp:
        if r["L"].id in specs: use.setdefault(r["e"].fill, []).append(("fill", 99.0))
    for L in Ls:
        if L.id in specs: continue
        if _floret_layer(L):
            specs[L.id] = dict(role="border_motifs", dot_min_d=1.1)
            for e in L.elements: use.setdefault(e.fill, []).append(("floret", 99.0))
            continue
        shapes = {}; border = {}; n_cls = {}
        for k, r in enumerate(allp):
            if r["L"] is not L: continue
            f = features(r["P"]); cls, bl = classify(f)
            if cls in ("petals", "star") and on_other(k): kind = "petal_tint" if cls == "petals" else "star_tint"
            else: kind = {"petals": "petal", "star": "star"}.get(cls)
            d = {"as": cls}
            if kind: d["kind"] = kind
            if cls == "petals" and not (5 <= f["pk"] <= 7): d["n"] = int(f["pk"])
            if cls == "fill": d["dir"] = long_axis(r["P"])
            shapes[f"{r['i']}.{r['j']}"] = d
            if bl: border.setdefault(bl, []).append((f"{r['i']}.{r['j']}", f))
            n_cls[cls] = n_cls.get(cls, 0) + 1
            use.setdefault(r["e"].fill, []).append((cls, f["T"]))
        # an element holding a stroke sews its round pieces (eyes, i-dots) inside the column (M5 column dots=True)
        for i in range(len(L.elements)):
            ks = [k for k in shapes if k.split(".")[0] == str(i)]
            if any(shapes[k]["as"] == "stroke" for k in ks):
                for k in ks:
                    if shapes[k]["as"] in ("dot", "knot"): shapes[k] = {"as": "stroke_dot"}
        for topic, items in sorted(border.items()):
            keys = [k for k, _ in items]; cur = shapes[keys[0]]["as"]
            Ts = [f["T"] for _, f in items]; Es = [f["E"] for _, f in items]
            if topic == "stroke-fill":
                opts = ["column satin", "fill"]; dflt = "column satin" if cur == "stroke" else "fill"
                text = (f"{len(keys)} shape(s) in layer '{L.id}' are near the satin/fill limit (thickness {min(Ts):.1f}-{max(Ts):.1f} mm, "
                        f"length/thickness {min(Es):.1f}-{max(Es):.1f}; rule 4: satin 1-7 mm on stroke-like shapes). Column satin or fill?")
            else:
                opts = ["radial (star)", "satin per point (petals)"]; dflt = "radial (star)" if cur == "star" else "satin per point (petals)"
                text = (f"{len(keys)} five-point shape(s) in layer '{L.id}' could be stars (radial from the centre) or rounded "
                        f"lobes (one satin per point). Which?")
            a = Q.ask(_qid("role", L.id, topic + ",".join(keys)), "role", text, opts, dflt,
                      "the shapes use the other stitch type in the next run", dict(layer=L.id, shapes=keys))
            for k in keys:
                if a == "fill": shapes[k] = {"as": "fill", "dir": long_axis(_poly(Ls, L, k))}
                elif a == "column satin": shapes[k] = {"as": "stroke"}
                elif a.startswith("radial"): shapes[k] = {"as": "star", "kind": "star_tint" if "tint" in shapes[k].get("kind", "") else "star"}
                elif a.startswith("satin per point"): shapes[k] = {"as": "petals", "kind": "petal_tint" if "tint" in shapes[k].get("kind", "") else "petal"}
        specs[L.id] = dict(role="shapes", shapes=shapes)
        report["layers"].append(dict(id=L.id, classes=n_cls))
    # threads
    fills = []
    for L in Ls:
        for e in L.elements:
            if e.fill and e.fill not in fills: fills.append(e.fill)
    bad = [f for f in fills if not re.fullmatch(r"#[0-9A-F]{6}", f)]
    if bad: raise AutoError(f"fill colour(s) {bad[:3]} are not plain colours the engine can match to a thread")
    tm = match_threads(fills)
    palette, names, weight, fill_map, rows = {}, {}, {}, {}, []
    for f in fills:
        t = tm[f]; key = f"isa_{t['code']}"
        palette[key] = t["hex"]; names[key] = f"Isacord {t['code']} {t['name']}"; fill_map[f] = key
        rows.append(dict(fill=f, thread=key, code=t["code"], name=t["name"], hex=t["hex"], dE=t["dE"], merged_into=t["merged_into"]))
        if t["merged_into"]: warnings.append(f"design colours {f} and {t['merged_into']} are only dE {t['dE_to']} apart: one thread (Isacord {t['code']})")
        elif t["dE"] > FAR_DE: warnings.append(f"{f}: the nearest Isacord is {t['code']} {t['name']} at dE {t['dE']} (visibly different; check the thread card)")
        if t.get("nearest_taken"): warnings.append(f"{f}: its nearest Isacord was taken by another colour, so it uses {t['code']} {t['name']} (dE {t['dE']})")
    by_key = {}
    for f in fills: by_key.setdefault(fill_map[f], []).extend(use.get(f, []))
    for key, us in by_key.items():
        if not any(c == "stroke" for c, _ in us) or any(c not in ("stroke", "stroke_dot", "dot", "knot") for c, _ in us): continue
        from digitize.extract.svg import stroke_width
        G = unary_union([r["P"] for r in allp if fill_map[r["e"].fill] == key])
        Tm = stroke_width(G)
        if Tm > FINE_T: continue
        a = Q.ask(_qid("thread.weight", key), "threads",
                  f"{names[key]} only sews fine lines (visible width {Tm:.2f} mm). Use 60wt thread (finer, sharper lines; the "
                  f"house uses it for face lines and small lettering) or the standard 40wt?",
                  ["60wt", "40wt"], "60wt", "40wt: the columns use the 40wt density and minimum width")
        if a == "60wt": weight[key] = "60wt"
    n_threads = len(set(fill_map.values()))
    if n_threads > 12:
        warnings.append(f"the art needs {n_threads} threads, more than the 12 needles: the file fails the thread gate until "
                        f"colours are merged (answer the merge questions)")
        keys = sorted(set(fill_map.values())); from digitize.extract.evidence import to_lab, hex_rgb, delta_e
        lab = {k: to_lab(np.array([[hex_rgb(palette[k])]], float))[0] for k in keys}
        pairs = sorted(((float(delta_e(lab[a], lab[b])[0]), a, b) for ai, a in enumerate(keys) for b in keys[ai + 1:]))
        merged = set()
        for d, a, b in pairs[: (n_threads - 12) + 2]:
            if a in merged or b in merged: continue
            ans = Q.ask(_qid("thread.merge", f"{a}+{b}"), "threads",
                        f"Too many colours for 12 needles. Merge {names[b]} into {names[a]} (dE {d:.1f})?",
                        ["keep separate", "merge"], "keep separate", "merge: both colours sew in the first thread")
            if ans == "merge":
                for f in fills:
                    if fill_map[f] == b: fill_map[f] = a
                merged.add(b)
        palette = {k: v for k, v in palette.items() if k in set(fill_map.values())}
    ppm = float(min(20.0, max(8.0, 3000.0 / max(W, H))))
    cfg = dict(source="svg", fabric=fabric,
               techniques=dict(tatami=True, satin=True, split_satin=True, run=True, bean=True, column_satin=True, dot=True,
                               radial=True, turning_satin=True),
               svg=dict(file=norm_svg, layers=specs, auto=True),
               threads=dict(needles="factory", max_dE=100.0, palette=palette, names=names, weight=weight, fill_map=fill_map,
                            tints=[], allow_over=True),
               sequence=dict(cut_under=False, touch=-0.05),
               compile=dict(exact_travel=dict(halo=0.25, max_ex=0.3, unsewn_only=True)),
               gates=dict(ppm=ppm, centreline=dict(d_max=0.5, w_tol=0.20, near_mm=1.0),
                          motif=dict(min_mm2=0.5, near_mm=0.3, near_mm_knot=0.15), thread_d={"40wt": 0.40, "60wt": 0.28}))
    unknown = sorted(set(Q.answers) - Q.used)
    if unknown: warnings.append(f"ignored answers to questions this run did not ask: {', '.join(unknown)}")
    report.update(size_mm=[W, H], threads=rows, patch=bool(pat and specs.get(pat[0].id, {}).get("role") == "patch_border"),
                  answered=sorted(Q.used))
    return dict(cfg=cfg, questions=Q.asked, report=report, warnings=warnings)


def _poly(Ls, L, key):
    i, j = map(int, key.split("."))
    return svgart.polys(L.elements[i].geom)[j]


def fill_config(cfg):
    """an SVG run.yaml with no thread palette (or svg.auto: true): derive the palette and the layer roles IN PLACE (the
    caller's cfg is the run's cfg, so later stages see them). Layers the yaml lists keep their hand roles."""
    from digitize import config
    S = cfg["svg"]; T = cfg.setdefault("threads", {})
    if T.get("palette") and not S.get("auto"): return cfg
    if S.get("_derived"): return cfg
    path = config.path(cfg, S["file"])
    auto = derive(path, fabric=cfg.get("fabric", "twill"), answers=(cfg.get("review") or {}).get("s1_answers"))
    hand = dict(S.get("layers") or {})
    S["layers"] = dict(auto["cfg"]["svg"]["layers"], **hand); S["_derived"] = True
    for k, v in auto["cfg"]["threads"].items():
        if k not in T or not T[k] or k in ("palette", "fill_map", "names", "weight", "max_dE", "allow_over"): T[k] = v
    for k in ("sequence", "compile", "gates", "techniques"):
        if not cfg.get(k): cfg[k] = auto["cfg"][k]
        else: cfg[k] = config.merge(auto["cfg"][k], cfg[k])
    cfg["_s1"] = dict(questions=auto["questions"], report=auto["report"], warnings=auto["warnings"])
    return cfg


def fabric_rules(name):
    """rules/fabrics.yaml entry for a fabric (svg2dst --fabric); unknown fabric -> AutoError naming the known ones"""
    from digitize import config
    F = config._read(os.path.join(os.path.dirname(HERE), "rules", "fabrics.yaml"))
    if name not in F: raise AutoError(f"fabric {name!r} has no rules (known: {', '.join(F)})")
    return dict(F[name])
