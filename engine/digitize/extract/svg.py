"""Founder SVG -> Parts (ENGINE_PLAN M5; konpeito ENGINE_NOTES 8, 11, 12, 13). No tone trace: the vector art IS the design.

  parts, info = extract.svg.extract(cfg, rb)

Every layer of the founder's file (svgart.layers, file order = stitch order, one thread per fill) becomes parts by its
ROLE: given in run.yaml `svg.layers` (id prefix -> spec) or, for unlisted layers, by shape (circles / compact blobs ->
bead dots, everything else -> petals). Each part gets a kind from the rulebook (house.yaml, M5 patch kinds), a thread
(svgart.thread_of: exact fill, else the nearest palette colour within threads.max_dE) and a DECLARED direction from the
geometry rule of its role, never "auto" (DIGITIZING_PRINCIPLES rule 2):

  role            parts                                                  kind (house.yaml)    direction
  patch_border    band = outline - (inner layer - 0.3), 4 trapezoids;    patch_band            across the band (90 top/bottom, 0 sides)
                  heat-cut edge = closed column on the outline - edge/2  patch_edge (sewn last) across the edge
  field           the layer's shape + grow mm                            patch_field           spec `dir` (required)
  border_motifs   ellipse clusters -> florets (minus other-fill holes);  floret / dot          radial / bead rows
                  circles -> bead dots
  column          satin COLUMNS on the centrelines of the outlines        lettering | line_art  across the stroke
                  (column.glyph_columns), ONE needle width per layer =
                  art stroke width - 0.15 mm (>= min_w); loops keep a
                  counter >= 0.7 mm sewn; small rings -> radial; compact
                  blobs (eyes) -> bead dots when `dots: true`
  petals          one turning satin per petal / lobe (polar-profile       petal / petal_tint    across the petal axis
                  valleys), axis centre -> tip
  dot             each shape -> a bead dot, needle = art - 0.2 (>= min_d) dot (house-min reported) bead rows (30 deg)
  star            each shape -> radial satin from its centroid           star                  radial
  fill            tatami                                                 fill                  spec `dir` (required)

z = paint order (layer order, then element order): a later SVG shape lies on top, so it sews later (sequence.dag).
Parts with meta last=True (the heat-cut edge) sew after everything (svgrun). Placement: `svg.place` maps SVG mm to the
file frame (translate / centre / scale) and gates map back with info["frame"]."""
import math
import numpy as np
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
from shapely import affinity
from scipy import ndimage as ndi
import svgart
from digitize.schema import Part, DirSpec
from digitize.techniques import column as C

ALLOW = 0.15        # visible stroke width - needle span (konpeito, calibrated on the DST read-back, 40 + 60wt)


class SvgPartsError(ValueError):
    pass


# ------------------------------------------------------------------ frame (SVG mm -> file mm)
class Frame:
    """garment = s * (svg - c0) + t"""
    def __init__(self, s=1.0, c0=(0.0, 0.0), t=(0.0, 0.0)):
        self.s = float(s); self.c0 = tuple(map(float, c0)); self.t = tuple(map(float, t))

    def geom(self, g):
        if self.s != 1.0: g = affinity.scale(g, self.s, self.s, origin=(self.c0[0], self.c0[1]))
        dx, dy = self.t[0] - self.c0[0], self.t[1] - self.c0[1]
        return affinity.translate(g, dx, dy).buffer(0) if (dx or dy) else g

    def pt(self, q):
        return (self.s * (q[0] - self.c0[0]) + self.t[0], self.s * (q[1] - self.c0[1]) + self.t[1])

    def to_svg(self, x, y):
        return ((x - self.t[0]) / self.s + self.c0[0], (y - self.t[1]) / self.s + self.c0[1])

    def as_dict(self): return dict(s=self.s, c0=list(self.c0), t=list(self.t))


def frame_of(place, Ls):
    """svg.place: {translate: [dx, dy]} | {svg_centre_x: X, art_bottom_y: Y, width: W_svg} | {width_mm: w, centre: [x, y]}"""
    if not place: return Frame()
    allg = unary_union([L.geom for L in Ls]); b = allg.bounds
    if "width_mm" in place:                       # scale the art so it is width_mm wide, centred on `centre`
        s = float(place["width_mm"]) / (b[2] - b[0]); c0 = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        return Frame(s, c0, tuple(place.get("centre", (0.0, 0.0))))
    dx, dy = place.get("translate", (0.0, 0.0))
    if "svg_centre_x" in place: dx = float(place["svg_centre_x"]) - float(place["svg_width"]) / 2
    if "art_bottom_y" in place: dy = float(place["art_bottom_y"]) - b[3]
    return Frame(1.0, (0.0, 0.0), (dx, dy))


# ------------------------------------------------------------------ helpers (promoted from konpeito kjsvg / kjletter)
def polys(g): return svgart.polys(g)


def stroke_width(G, ppm=40.0, weighted=False):
    """visible stroke width of outline art: median skeleton width of its strokes (column.glyph_columns at 40 px/mm).
    weighted (S1, one source shape): the LENGTH-weighted median, so a glyph's short pieces (the 3 ticks of a ぺ, 0.9 mm)
    do not out-vote its main stroke (12 mm at 1.65 mm); the pooled per-layer median hid this on the hand runs."""
    ss = [(s["w"], C.poly_len(s["cl"])) for p in polys(G) for s in C.glyph_columns(p, ppm=ppm) if C.poly_len(s["cl"]) > 0.8]
    if not ss: return 2 * G.area / max(G.length, 1e-6)
    if not weighted: return float(np.median([w for w, _ in ss]))
    ss.sort(); c = np.cumsum([l for _, l in ss])
    return float(ss[int(np.searchsorted(c, c[-1] / 2))][0])


def _taper(P, cl, min_w, n=24, dev=0.25, share=0.25, belly=2.0):
    """S1 tapered stroke (crescent, brush stroke): local visible width along the centreline (2 x distance to the outline);
    >= `share` of the samples off the median by > `dev` -> (needle width at the belly, ("table", width multipliers)),
    else None (one width is right: a round-ended stroke's skeleton stops at the cap centres, so its samples stay flat).
    A taper narrows at BOTH ends with its belly in the middle half; a glyph stroke that runs into a junction widens at an
    end instead and keeps one width (konpeito wb: 70 glyph strokes profiled, 2 exposed stitches; lettering fixture: 71).
    Only a belly >= `belly` mm is profiled: below it the 0.85 mm minimum satin leaves nothing to follow."""
    from shapely.geometry import LineString
    line = LineString(cl)
    if line.length < 1e-6: return None
    lw = np.array([2 * P.exterior.distance(line.interpolate(f, normalized=True)) for f in np.linspace(0, 1, n)])
    mid = float(np.median(lw))
    if mid <= 0 or lw.max() < belly or np.mean(np.abs(lw / mid - 1) > dev) < share: return None
    if line.length < 3 * lw.max(): return None                     # a dot / square (an i dot) is no taper
    if np.mean(lw >= 0.9 * lw.max()) >= 0.5: return None          # flat-ended bar (an i stem): full width most of its length
    k = int(np.argmax(lw)); e = max(1, n // 8)
    if not (n // 4 <= k <= 3 * n // 4) or max(lw[:e].max(), lw[-e:].max()) > (1 - dev) * mid: return None
    wmax = max(min_w, float(lw.max()) - ALLOW)
    return round(wmax, 2), ("table", [round(max(min_w, float(v) - ALLOW) / wmax, 3) for v in lw])


def polar_profile(geo, c, n=360):
    out = []
    for i in range(n):
        t = math.radians(360 * i / n)
        ray = LineString([c, (c[0] + 40 * math.cos(t), c[1] + 40 * math.sin(t))]).intersection(geo)
        r = 0.0
        for g in getattr(ray, "geoms", [ray]):
            if g.is_empty: continue
            for q in g.coords: r = max(r, math.dist(c, q))
        out.append(r)
    return np.array(out)


def split_petals(geo, c, nmin=5, nmax=7, force_n=None):
    """a flower / candy silhouette -> petals at the valleys of its polar profile: (n, [(petal, tip, mid_angle)])"""
    r = polar_profile(geo, c)
    rs = ndi.gaussian_filter1d(r, 4, mode="wrap")
    F = np.fft.rfft(rs - rs.mean())
    n = force_n or int(np.argmax(np.abs(F[nmin:nmax + 1])) + nmin)
    best = None
    for ph in range(0, 360 // n):
        val = sum(rs[(ph + int(round(360 * k / n))) % 360] for k in range(n))
        if best is None or val < best[0]: best = (val, ph)
    ph = best[1]; vals = []
    for k in range(n):
        a0 = ph + 360 * k / n; cand = [int(round(a0 + dd)) % 360 for dd in range(-12, 13)]
        vals.append(min(cand, key=lambda a: rs[a]))
    vals = sorted(vals); out = []
    for k in range(n):
        a0, a1 = vals[k], vals[(k + 1) % n]
        if a1 <= a0: a1 += 360
        wedge = Polygon([c] + [(c[0] + 40 * math.cos(math.radians(a)), c[1] + 40 * math.sin(math.radians(a))) for a in np.linspace(a0, a1, 24)])
        p = geo.intersection(wedge).buffer(0)
        if p.is_empty: continue
        if p.geom_type != "Polygon": p = max(p.geoms, key=lambda q: q.area)
        am = int(np.argmax([rs[int(a) % 360] for a in np.arange(a0, a1)])) + a0
        tip = (c[0] + rs[int(am) % 360] * math.cos(math.radians(am)), c[1] + rs[int(am) % 360] * math.sin(math.radians(am)))
        out.append((p, tip, (a0 + a1) / 2))
    return n, out


def _deg(v): return math.degrees(math.atan2(v[1], v[0]))


# ------------------------------------------------------------------ the extractor
class _B:
    def __init__(self, cfg, rb, frame):
        self.cfg, self.rb, self.frame = cfg, rb, frame
        S = cfg["svg"]; T = cfg["threads"]
        self.palette = T.get("palette") or {}; self.weights = T.get("weight", {}); self.max_dE = float(T.get("max_dE", 3.0))
        self.tints = set(T.get("tints", [])); self.parts = []; self.n = {}; self.report = {}; self.thread_dE = {}
        self.fill_map = T.get("fill_map") or {}; self.src = None; self.fam = None   # S1: fill -> thread decided by svg_auto
        self.dot_floor = 0.0
        if cfg.get("fabric"):                                                # S1: pile swallows small dots (rules/fabrics.yaml)
            from digitize.extract.svg_auto import fabric_rules
            self.dot_floor = float(fabric_rules(cfg["fabric"]).get("dot_min_d", 0.0))

    def thread(self, fill):
        if fill in self.fill_map:                                            # S1: the derived thread, dE to it reported
            k = self.fill_map[fill]; _, dE = svgart.thread_of(fill, {k: self.palette[k]})
            self.thread_dE[fill] = (k, dE); return k
        k, dE = svgart.thread_of(fill, self.palette)
        if dE > self.max_dE:
            raise SvgPartsError(f"SVG fill {fill} has no thread within dE {self.max_dE} (nearest {k}, dE {dE}): add it to "
                                f"threads.palette in the run yaml")
        self.thread_dE[fill] = (k, dE); return k

    def add(self, layer, kind, geom, thread, z, dirspec, **meta):
        g = self.frame.geom(geom) if geom is not None else None
        pre = layer.split("_")[0] if layer[:2].isdigit() else layer[:6]
        self.n[pre] = self.n.get(pre, 0) + 1
        m = dict(layer=layer, thread_wt=self.weights.get(thread, "40wt"))
        if self.src: m["s1_el"] = list(self.src); m["s1_fam"] = self.fam   # S1: the SVG shapes this part comes from (gates)
        m.update(meta)
        for key in ("cl", "axis"):                 # point lists follow the frame too
            if key in m and m[key] is not None: m[key] = [self.pt(q) for q in m[key]]
        if "centre" in m and m["centre"] is not None: m["centre"] = list(self.pt(m["centre"]))
        if "knots" in m: m["knots"] = [(*self.pt(k[:2]), k[2] * self.frame.s, k[3]) for k in m["knots"]]
        if "w" in m: m["w"] = float(m["w"]) * self.frame.s
        p = Part(id=f"{pre}.{self.n[pre]:03d}", kind=kind, geom=g, thread=thread, z=float(z), dir=dirspec, zone=layer, meta=m)
        self.parts.append(p); return p

    def pt(self, q): return self.frame.pt(q)

    # -------------------------------------------------------------- roles
    def dot(self, layer, g, thread, z, kind="dot", min_d=1.1, ang=30.0):
        from digitize.techniques.dot import needle_d
        min_d = max(min_d, self.dot_floor)
        c = g.centroid; art = 2 * math.sqrt(g.area / math.pi); d, hm = needle_d(art, min_d)
        return self.add(layer, kind, Point(c.x, c.y).buffer(d / 2, quad_segs=16), thread, z,
                        DirSpec(ang, source="rule", note="bead dot: satin rows at one angle"),
                        knots=[(c.x, c.y, d, ang)], art_d=round(art, 3), house_min=bool(hm), min_d=min_d)

    def column(self, layer, G, thread, z, spec, kind):
        wv = stroke_width(G, weighted=bool(spec.get("per_shape"))); wt = self.weights.get(thread, "40wt")
        min_w = float(spec.get("min_w", 0.85 if wt == "40wt" else 0.45))
        w = max(min_w, round(wv - ALLOW, 2)); self.report[layer] = dict(w_art=round(wv, 2), w_needle=w, thread=wt)
        corner = float(spec.get("corner", C.CORNER)); min_counter = float(spec.get("min_counter", 0.6))
        dots = spec.get("dots", False); k = 0
        per_shape = bool(spec.get("per_shape"))      # S1 (G = one source shape): a tapered stroke sews on its width profile
        for P in polys(G):
            if P.area < 0.05: continue
            ys = np.array(P.exterior.coords); ext = ys.max(0) - ys.min(0)
            if dots and max(ext) < 2.2 and max(ext) / max(min(ext), 1e-6) < 1.5 and not P.interiors:
                self.dot(layer, P, thread, z + 0.001 * k, kind="dot", min_d=float(spec.get("dot_min_d", 1.0))); k += 1; continue
            if P.interiors and P.area < 8.0 and max(ext) < 4.0:          # small ring (handakuten): radial on the exact ring
                c = Polygon(P.interiors[0]).centroid
                self.add(layer, "ring", P, thread, z + 0.001 * k, DirSpec(0.0, source="rule", note="radial from the ring centre"),
                         centre=(c.x, c.y)); k += 1; continue
            sts = C.glyph_columns(P, ppm=40.0, corner=corner)
            for s in sts:
                cl = s["cl"]; closed = s.get("closed", False)
                L = C.poly_len(list(cl) + ([cl[0]] if closed else []))
                if L < 0.25: continue
                if len(sts) > 1 and not closed and L < 1.1 * w: continue        # skeleton spur (cusps, stroke ends)
                ww = w
                if closed: ww = max(0.8 if w >= 0.8 else w, min(w, L / math.pi - (min_counter + 0.2 + ALLOW)))
                # a width profile only on a shape that IS one open stroke: a glyph's strokes meet at junctions (wider
                # samples, not a taper) and profiling them sewed the lettering fixture's A thinner (ratio 0.84 -> 0.60)
                caps = tuple(s["caps"]); prof = _taper(P, cl, min_w) if per_shape and not closed and len(sts) == 1 else None
                if prof: ww, prof = prof; caps = ("flat", "flat")
                g = C.column_geom(cl, ww, caps, closed, prof)
                t = np.array(cl[min(1, len(cl) - 1)]) - np.array(cl[0])
                ex = dict(prof=prof) if prof else {}
                self.add(layer, kind, g, thread, z + 0.001 * k, DirSpec(_deg(t) + 90.0, source="rule", note="across the stroke (column)"),
                         cl=[tuple(q) for q in cl], w=ww, caps=caps, closed=bool(closed), **ex); k += 1

    def petals(self, layer, geo, thread, z, spec, kind=None):
        kind = kind or ("petal_tint" if thread in self.tints else "petal"); j = 0
        for P0 in polys(geo):                       # one shape may hold several flowers / candies
            if P0.area < 1.0: continue
            P = Polygon(P0.exterior); c = P.centroid; c = (c.x, c.y)
            n, ps = split_petals(P, c, force_n=spec.get("n"))
            for p, tip, amid in ps:
                ax = [c, (c[0] + (tip[0] - c[0]) * 1.1, c[1] + (tip[1] - c[1]) * 1.1)]
                g = p.buffer(0.05).intersection(P.buffer(0.05))
                self.add(layer, kind, g, thread, z + 0.0001 * j, DirSpec(_deg((tip[0] - c[0], tip[1] - c[1])) + 90.0, source="rule",
                         note="across the petal axis (centre -> tip)"), axis=ax, petals=n); j += 1

    def patch_border(self, layer, L, inner, z, spec):
        outer = L.geom; field = inner.geom if inner is not None else outer.buffer(-6.5)
        thread = self.thread(L.fills()[0]); x0, y0, x1, y1 = outer.bounds; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        band = outer.buffer(-float(spec.get("band_inset", 0.6))).difference(field.buffer(-float(spec.get("under_field", 0.3))))
        for tri, ang, side in (([(x0, y0), (x1, y0), (cx, cy)], 90, "top"), ([(x0, y1), (x1, y1), (cx, cy)], 90, "bottom"),
                               ([(x0, y0), (x0, y1), (cx, cy)], 0, "left"), ([(x1, y0), (x1, y1), (cx, cy)], 0, "right")):
            g = band.intersection(Polygon(tri)).buffer(0)
            if g.area > 1: self.add(layer, "patch_band", g, thread, z, DirSpec(ang, source="rule", note=f"across the band ({side})"))
        ew = float(spec.get("edge_w", 2.0))
        ring = outer.buffer(-ew / 2, join_style="round")
        cl = list(ring.exterior.coords)[:-1]
        cl = list(LineString(cl + [cl[0]]).simplify(0.02).coords)[:-1]
        self.add(layer, "patch_edge", C.column_geom(cl, ew, ("flat", "flat"), True), thread, 10 ** 6,
                 DirSpec(0.0, source="rule", note="across the heat-cut edge (column)"), cl=cl, w=ew, caps=("flat", "flat"), closed=True, last=True)

    def border_motifs(self, layer, L, z, spec):
        fills = L.fills(); main = spec.get("fill") or max(fills, key=lambda f: sum(e.geom.area for e in L.elements if e.fill == f))
        thread = self.thread(main)
        holes = [e.geom for e in L.elements if e.fill != main]
        pet = unary_union([e.geom for e in L.elements if e.fill == main and e.tag == "ellipse"])
        k = 0
        for P in sorted(polys(pet), key=lambda p: (round(p.centroid.y, 1), p.centroid.x)):
            c = P.centroid; hole = [h for h in holes if h.centroid.distance(c) < 0.6]
            g = P.difference(unary_union(hole)) if hole else P
            self.add(layer, "floret", g, thread, z + 0.0001 * k, DirSpec(0.0, source="rule", note="radial from the flower centre"),
                     centre=(c.x, c.y)); k += 1
        for e in L.elements:
            if e.fill == main and e.tag == "circle":
                self.dot(layer, e.geom, thread, z + 0.0001 * k, kind="dot", min_d=float(spec.get("dot_min_d", 1.1))); k += 1


def _spec_for(layer_id, specs):
    best = None
    for pre, s in (specs or {}).items():
        if layer_id.startswith(pre) and (best is None or len(pre) > len(best[0])): best = (pre, s)
    return dict(best[1]) if best else None


def _compact(e):
    g = e.geom
    if e.tag == "circle": return True
    if g.geom_type != "Polygon" or g.interiors: return False
    ys = np.array(g.exterior.coords); ext = ys.max(0) - ys.min(0)
    return max(ext) < 2.5 and max(ext) / max(min(ext), 1e-6) < 1.5


def _shapes(B, L, z0, spec):
    """S1 role `shapes` (svg_auto): one decision per shape, keyed '<element>.<polygon>'. Strokes (and the round pieces of an
    element that holds a stroke: eyes, i-dots) are pooled per element + colour into satin columns, each shape at its own width (a tapered one on its width profile);
    every other shape is a dot / knot, petals, a star or a fill at its declared long-axis angle."""
    sh = spec["shapes"]; strokes = {}
    for i, e in enumerate(L.elements):
        tag = e.attrib.get("data-s1")
        for j, P in enumerate(polys(e.geom)):
            d = sh.get(f"{i}.{j}")
            if d is None: raise SvgPartsError(f"layer {L.id}: shape {i}.{j} has no decision (the run config is stale: derive it again)")
            a = d["as"]; z = z0 + i + 0.01 * j
            if a == "skip": continue
            th = B.thread(e.fill); B.src = [tag] if tag else None; B.fam = "shape"
            if a in ("stroke", "stroke_dot"):
                st = strokes.setdefault((e.fill, i), dict(z=z, P=[], src=set(), dots=False)); st["P"].append(P)
                if tag: st["src"].add(tag)
                st["dots"] |= a == "stroke_dot"; st["z"] = min(st["z"], z)
            elif a in ("dot", "knot"): B.dot(L.id, P, th, z, kind=a, min_d=0.9 if a == "knot" else 1.1)
            elif a == "petals": B.petals(L.id, P, th, z, dict(n=d.get("n")), kind=d.get("kind"))
            elif a == "star":
                c = P.centroid
                B.add(L.id, d.get("kind", "star"), P, th, z, DirSpec(0.0, source="rule", note="radial from the star centre"), centre=(c.x, c.y))
            elif a == "fill":
                B.add(L.id, d.get("kind", "graphic_fill"), P, th, z, DirSpec(float(d["dir"]), source="rule",
                      note="long axis of the shape (minimum rotated rectangle), declared by svg_auto"))
            else: raise SvgPartsError(f"layer {L.id}: shape {i}.{j}: unknown decision {a!r}")
    for (f, _), st in strokes.items():        # per source element: crossing same-colour strokes keep their own widths
        B.src = sorted(st["src"]) or None; B.fam = "line"
        B.column(L.id, unary_union(st["P"]), B.thread(f), st["z"], dict(spec.get("column", {}), dots=st["dots"], per_shape=True), "lettering")
    B.src = None


def extract(cfg, rb=None):
    """-> (parts, info). info: layers (id, order, role, n parts), frame, size, width report, thread dE per fill.
    S1: a run.yaml with no thread palette (or svg.auto: true) gets its palette and layer roles from svg_auto.fill_config."""
    from digitize import config
    from digitize.extract import svg_auto
    svg_auto.fill_config(cfg)
    S = cfg["svg"]; path = config.path(cfg, S["file"])
    Ls = svgart.layers(path); W, H, scale = svgart.size_mm(path)
    if abs(scale - 1.0) > 1e-6: raise SvgPartsError(f"{path}: user units are {scale} mm, not 1 mm (export the art true-size in mm)")
    sel = S.get("select")
    if sel: Ls = [L for L in Ls if any(L.id.startswith(p) for p in sel)]
    place = dict(S.get("place") or {})
    if "svg_centre_x" in place: place.setdefault("svg_width", W)
    fr = frame_of(place, Ls); B = _B(cfg, rb, fr); specs = S.get("layers", {}); info_layers = []
    byid = {L.id: L for L in Ls}
    consumed = set()
    for L in Ls:
        if L.id in consumed: continue
        spec = _spec_for(L.id, specs) or {"role": "auto"}; role = spec.get("role", "auto"); z0 = 1000.0 * (L.order + 1); n0 = len(B.parts)
        if role == "skip": info_layers.append(dict(id=L.id, order=L.order, role=role, parts=0)); continue
        if role == "patch_border":
            inner = next((M for M in Ls if spec.get("inner") and M.id.startswith(spec["inner"])), None)
            B.patch_border(L.id, L, inner, z0, spec)
        elif role == "field":
            if "dir" not in spec: raise SvgPartsError(f"layer {L.id}: role field needs a declared `dir` (never auto)")
            th = B.thread(L.fills()[0])
            B.add(L.id, spec.get("kind", "patch_field"), L.geom.buffer(float(spec.get("grow", 0.0))), th, z0,
                  DirSpec(float(spec["dir"]), source="rule", note="declared in the run yaml"))
        elif role == "fill":
            if "dir" not in spec: raise SvgPartsError(f"layer {L.id}: role fill needs a declared `dir` (never auto)")
            for i, e in enumerate(L.elements):
                B.add(L.id, spec.get("kind", "fill"), e.geom, B.thread(e.fill), z0 + i, DirSpec(float(spec["dir"]), source="rule", note="declared in the run yaml"))
        elif role == "border_motifs":
            B.border_motifs(L.id, L, z0, spec)
        elif role == "column":
            for f in L.fills():
                G = unary_union([e.geom for e in L.elements if e.fill == f])
                B.column(L.id, G, B.thread(f), z0, spec, spec.get("kind", "lettering"))
        elif role == "dot":
            for i, e in enumerate(L.elements):
                for j, P in enumerate(polys(e.geom)):
                    B.dot(L.id, P, B.thread(e.fill), z0 + i + 0.01 * j, kind=spec.get("kind", "dot"), min_d=float(spec.get("min_d", 1.1)))
        elif role == "star":
            for i, e in enumerate(L.elements):
                th = B.thread(e.fill); c = e.geom.centroid
                B.add(L.id, spec.get("kind", "star"), e.geom, th, z0 + i, DirSpec(0.0, source="rule", note="radial from the star centre"),
                      centre=(c.x, c.y))
        elif role == "shapes":
            _shapes(B, L, z0, spec)
        elif role in ("petals", "auto"):
            for i, e in enumerate(L.elements):
                th = B.thread(e.fill)
                if _compact(e):
                    B.dot(L.id, e.geom, th, z0 + i, kind=spec.get("dot_kind", "knot"), min_d=float(spec.get("dot_min_d", 0.9)))
                else:
                    B.petals(L.id, e.geom, th, z0 + i, spec)
        else:
            raise SvgPartsError(f"layer {L.id}: unknown role {role!r}")
        info_layers.append(dict(id=L.id, order=L.order, role=role, parts=len(B.parts) - n0))
    return B.parts, dict(svg=path, size_mm=[W, H], frame=fr.as_dict(), layers=info_layers, widths=B.report,
                         thread_dE={f: list(v) for f, v in B.thread_dE.items()})
