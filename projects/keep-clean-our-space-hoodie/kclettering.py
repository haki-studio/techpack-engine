"""Lettering from real fonts -> stitchable satin strokes (no tracing of the mockup's AI glyphs).

 1. glyph(font, char, height_mm, wght)  : the font outline as shapely polygons in mm (y down, origin = em-box top-left)
 2. set_line(...) / set_column(...)     : lay a string out horizontally (advance widths + tracking) or vertically (CJK)
 3. strokes(poly)                       : split one glyph into satin strokes: skeleton -> branches (junctions removed,
                                          spurs pruned, straight-through branches re-joined) -> every glyph pixel goes to
                                          its nearest branch -> one polygon per stroke, cut out of the exact outline.
                                          Closed rings (O, ㅇ, counters) are cut in two so a turning satin covers them.
Fonts (OFL, inputs/fonts): Zen Maru Gothic Black (JP), Nunito ExtraBold (EN), Noto Sans SC Bold (CN), Noto Sans KR (KR)."""
import os, math
import numpy as np
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, box
from shapely.ops import unary_union, split as shp_split
from shapely import affinity
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
from skimage import measure
from PIL import Image, ImageDraw

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inputs", "fonts")
FONTS = {"jp": ("ZenMaruGothic-Bold.ttf", None), "en": ("Nunito[wght].ttf", 1000), "cn": ("NotoSansSC[wght].ttf", 600),
         "kr": ("NotoSansKR[wght].ttf", 450)}
_F = {}

def font(key):
    if key in _F: return _F[key]
    fn, w = FONTS[key]
    path = os.path.join(FONT_DIR, fn)
    if w is not None:
        cache = os.path.join(FONT_DIR, f"_inst_{key}_{w}.ttf")
        if not os.path.exists(cache):
            from fontTools.varLib import instancer
            f = TTFont(path); f = instancer.instantiateVariableFont(f, {"wght": w}); f.save(cache)
        path = cache
    f = TTFont(path); _F[key] = f
    return f

class _Flat(BasePen):
    def __init__(self, gs, step=24):
        super().__init__(gs); self.contours = []; self.cur = []; self.step = step
    def _moveTo(self, p): self.cur = [p]
    def _lineTo(self, p): self.cur.append(p)
    def _curveToOne(self, p1, p2, p3):
        p0 = self.cur[-1]
        for t in np.linspace(0, 1, self.step)[1:]:
            mt = 1 - t
            self.cur.append((mt**3*p0[0] + 3*mt*mt*t*p1[0] + 3*mt*t*t*p2[0] + t**3*p3[0],
                             mt**3*p0[1] + 3*mt*mt*t*p1[1] + 3*mt*t*t*p2[1] + t**3*p3[1]))
    def _qCurveToOne(self, p1, p2):
        p0 = self.cur[-1]
        for t in np.linspace(0, 1, self.step)[1:]:
            mt = 1 - t
            self.cur.append((mt*mt*p0[0] + 2*mt*t*p1[0] + t*t*p2[0], mt*mt*p0[1] + 2*mt*t*p1[1] + t*t*p2[1]))
    def _closePath(self):
        if len(self.cur) > 2: self.contours.append(self.cur)
        self.cur = []
    _endPath = _closePath

def _signed(c):
    a = 0.0
    for (x0, y0), (x1, y1) in zip(c, c[1:] + c[:1]): a += x0*y1 - x1*y0
    return a / 2

def glyph(key, ch, height_mm):
    """outline of `ch` scaled so the em = height_mm; returns (geom, advance_mm). Coordinates: x right, y DOWN,
    origin at the top-left of the em box (ascender line = 0 for CJK fonts, baseline = em*asc/(asc+desc))."""
    f = font(key); gs = f.getGlyphSet(); cmap = f.getBestCmap()
    gn = cmap[ord(ch)]; upm = f["head"].unitsPerEm
    hh = f["hhea"]; asc = hh.ascent; desc = -hh.descent
    k = height_mm / upm
    pen = _Flat(gs); gs[gn].draw(pen)
    return nonzero([[(x*k, (asc - y)*k) for x, y in c] for c in pen.contours]), gs[gn].width * k

def nonzero(contours):
    """the font rasteriser's NONZERO fill rule on overlapping contours. Rev C (review of PR #20): the old 'union of
    outer contours minus union of holes' was wrong wherever a variable-font instance keeps OVERLAPPING contours: the
    holes of 界's 田 box were subtracted from the cross strokes that lie inside them, so the centre vertical was never
    stitched. Now: node every contour edge, polygonize into faces, keep each face whose winding number (sum of +-1 over
    the contours that contain it, by orientation) is not 0."""
    from shapely.ops import polygonize
    from shapely.geometry import LineString
    from shapely.prepared import prep
    rings = []
    for c in contours:
        if len(c) < 3: continue
        pg = Polygon(c)
        if abs(pg.area) < 1e-9: continue
        rings.append((c, 1 if _signed(c) > 0 else -1, prep(Polygon(c).buffer(0))))
    if not rings: return Polygon()
    edges = unary_union([LineString(c + c[:1]) for c, _, _ in rings])
    keep = []
    for f_ in polygonize(edges):
        if f_.area < 1e-6: continue
        p = f_.representative_point()
        w = sum(s for _, s, P in rings if P.contains(p))
        if w != 0: keep.append(f_)
    return unary_union(keep).buffer(0) if keep else Polygon()

def set_line(key, text, height_mm, tracking=0.0, kern_pairs=None):
    """horizontal line; returns list of (char, geom) with x from 0, y down (em top = 0)."""
    out = []; x = 0.0
    for ch in text:
        if ch == " ":
            _, adv = glyph(key, "n" if key == "en" else "가" if key == "kr" else "　", height_mm) if key != "kr" else (None, height_mm*0.30)
            if key == "kr": adv = height_mm * 0.28
            x += adv + tracking; continue
        g, adv = glyph(key, ch, height_mm)
        out.append((ch, affinity.translate(g, x, 0)))
        x += adv + tracking + (kern_pairs or {}).get(ch, 0.0)
    return out

def set_column(key, text, height_mm, gap=0.0):
    """vertical CJK column, each glyph centred on x = 0, stacked down from y = 0 (em pitch + gap)."""
    out = []; y = 0.0
    for ch in text:
        g, adv = glyph(key, ch, height_mm)
        b = g.bounds
        g = affinity.translate(g, -(b[0] + b[2]) / 2, y - 0.0)
        out.append((ch, g)); y += height_mm + gap
    return out

def ink_bounds(glyphs):
    return unary_union([g for _, g in glyphs]).bounds

def place(glyphs, cx, cy, ang, anchor=None):
    """centre the set on (cx, cy) and rotate by ang degrees (y down: positive = clockwise on screen)."""
    b = ink_bounds(glyphs); ax, ay = anchor or ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    out = []
    for ch, g in glyphs:
        g2 = affinity.rotate(affinity.translate(g, cx - ax, cy - ay), ang, origin=(cx, cy))
        out.append((ch, g2.buffer(0)))
    return out

# ------------------------------------------------------------------ glyph -> satin strokes
def _polys(g):
    if g is None or g.is_empty: return []
    if g.geom_type == "Polygon": return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]

def _cut_ring(p):
    """a closed ring (polygon with a hole) cannot be covered by one turning satin: cut it in two across its long axis."""
    if not p.interiors: return [p]
    mrr = p.minimum_rotated_rectangle; cs = list(mrr.exterior.coords)
    e0 = math.dist(cs[0], cs[1]); e1 = math.dist(cs[1], cs[2])
    # cut line along the SHORT axis direction through the centroid -> two C halves
    (a, b) = (cs[1], cs[2]) if e0 >= e1 else (cs[0], cs[1])
    c = p.centroid; d = np.array(b) - np.array(a); d = d / max(np.linalg.norm(d), 1e-9); R = 200
    ln = LineString([(c.x - d[0]*R, c.y - d[1]*R), (c.x + d[0]*R, c.y + d[1]*R)])
    try:
        parts = [q for q in shp_split(p, ln).geoms if q.area > 0.05]
    except Exception:
        parts = [p]
    out = []
    for q in parts: out += _cut_ring(q) if q.interiors else [q]
    return out

def strokes(geom, ppm=24.0, join_angle=150.0, spur_k=1.25, min_area=0.15, corner=50.0):
    """split a glyph outline into satin strokes. Returns a list of polygons that tile the glyph exactly.
    Strokes that turn a sharp corner (L, 冖, ㄱ) are cut on the mitre so a turning satin never fans round a corner."""
    out = []
    for P in _polys(geom):
        qs = []
        for q in _strokes_one(P, ppm, join_angle, spur_k, min_area):
            qs += split_corners(q, corner)
        out += [r for q in merge_small(qs, P) for r in split_corners(q, corner)]
    return out

def merge_small(pieces, P, k=1.3):
    """junction crumbs (area < k * stroke width^2) join the neighbour they share the longest edge with (if the union is
    one polygon); every crumb is tried once."""
    wg = 2 * P.area / max(P.length, 1e-6) * 1.15
    ps = [p for p in pieces if not p.is_empty]
    crumbs = sorted([i for i, q in enumerate(ps) if q.area < k * wg * wg], key=lambda i: ps[i].area)
    dead = set()
    for i in crumbs:
        if i in dead: continue
        q = ps[i]; best = None
        for j, r in enumerate(ps):
            if j == i or j in dead: continue
            if q.distance(r) > 0.05: continue
            L = q.buffer(0.05).intersection(r.buffer(0.05)).area
            if L > 0 and (best is None or L > best[0]): best = (L, j)
        if best is None: continue
        j = best[1]; m = unary_union([ps[j], q.buffer(0.02)]).intersection(P).buffer(0)
        if m.geom_type != "Polygon": continue
        ps[j] = m; dead.add(i)
    return [q for i, q in enumerate(ps) if i not in dead]

def split_corners(p, corner=50.0, depth=0):
    import dst2
    if depth > 4 or p.area < 3 or not dst2.is_elongated(p): return [p]
    line = dst2.centreline(p)
    if line is None: return [p]
    w = max(0.8, 2 * p.area / max(p.length, 1e-6) * 1.3)
    ln = line.simplify(max(0.3, 0.45 * w)); cs = list(ln.coords)
    best = None
    for i in range(1, len(cs) - 1):
        a = np.array(cs[i]) - np.array(cs[i-1]); b = np.array(cs[i+1]) - np.array(cs[i])
        la, lb = np.linalg.norm(a), np.linalg.norm(b)
        if la < 0.6*w or lb < 0.6*w: continue
        a /= la; b /= lb; ang = math.degrees(math.acos(max(-1, min(1, float(np.dot(a, b))))))
        if ang > corner and (best is None or ang > best[0]): best = (ang, i, a, b)
    if best is None: return [p]
    _, i, a, b = best; c = np.array(cs[i]); d = a - b; d /= max(np.linalg.norm(d), 1e-9); R = 3 * w + 5
    cut = LineString([tuple(c - d*R), tuple(c + d*R)])
    try:
        parts = [q for q in shp_split(p, cut).geoms if q.area > 0.05]
    except Exception:
        return [p]
    if len(parts) < 2: return [p]
    if len(parts) > 2:      # the mitre also clipped a far part of the polygon: keep the two pieces at the corner, give the rest back
        parts.sort(key=lambda q: q.distance(Point(*c)))
        main = parts[:2]; rest = parts[2:]
        for r in rest:
            k = min((0, 1), key=lambda j: main[j].distance(r)); main[k] = main[k].union(r).buffer(0)
        parts = [q for m in main for q in _polys(m)]
    out = []
    for q in parts: out += split_corners(q, corner, depth + 1)
    return out

def _strokes_one(P, ppm, join_angle, spur_k, min_area):
    x0, y0, x1, y1 = P.bounds; m = 4
    W, H = int((x1 - x0)*ppm) + 2*m, int((y1 - y0)*ppm) + 2*m
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    T = lambda cs: [((x - x0)*ppm + m, (y - y0)*ppm + m) for x, y in cs]
    d.polygon(T(P.exterior.coords), fill=255)
    for r in P.interiors: d.polygon(T(r.coords), fill=0)
    mask = np.array(im) > 127
    if mask.sum() < 20: return [P]
    sk = skeletonize(mask)
    K = np.ones((3, 3), int)
    nbc = ndi.convolve(sk.astype(int), K, mode="constant") - 1
    nbc[~sk] = 0
    dt = ndi.distance_transform_edt(mask)
    junc = sk & (nbc >= 3)
    jl, nj = ndi.label(ndi.binary_dilation(junc, iterations=1) & sk, structure=np.ones((3, 3)))
    # break the skeleton at junction zones (radius ~ local half width so branch directions are clean)
    jz = np.zeros_like(sk)
    for j in range(1, nj + 1):
        ys, xs = np.nonzero(jl == j); cy, cx = ys.mean(), xs.mean(); r = max(2.0, dt[ys, xs].max() * 1.0)
        yy, xx = np.ogrid[:H, :W]; jz |= ((yy - cy)**2 + (xx - cx)**2 <= r*r)
    br = sk & ~jz
    bl, nb = ndi.label(br, structure=np.ones((3, 3)))
    if nb == 0: return [P]
    ends = sk & (nbc == 1)
    # prune spurs: short branches with a free end
    keep = np.ones(nb + 1, bool); keep[0] = False
    info = {}
    for i in range(1, nb + 1):
        ys, xs = np.nonzero(bl == i); L = len(ys); wpx = 2*np.median(dt[ys, xs])
        free = ends[ys, xs].any()
        touches = set()
        info[i] = (ys, xs, L, wpx, free)
        if free and L < spur_k * wpx and nb > 1: keep[i] = False
    # join straight-through branches across each junction (union-find)
    parent = list(range(nb + 1))
    def fd(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for j in range(1, nj + 1):
        ys, xs = np.nonzero(jl == j); cy, cx = ys.mean(), xs.mean(); r = max(2.0, dt[ys, xs].max() * 1.0)
        ring = ((np.ogrid[:H, :W][0] - cy)**2 + (np.ogrid[:H, :W][1] - cx)**2 <= (r + 2.5)**2)
        near = [i for i in np.unique(bl[ring & br]) if i and keep[i]]
        dirs = {}
        for i in near:
            by_, bx_ = info[i][0], info[i][1]
            dd = np.hypot(by_ - cy, bx_ - cx); sel = dd < r + 3 * max(2.0, info[i][3])
            if sel.sum() < 2: sel = dd <= np.sort(dd)[min(len(dd) - 1, 6)]
            v = np.array([bx_[sel].mean() - cx, by_[sel].mean() - cy]); n = np.linalg.norm(v)
            if n > 1e-6: dirs[i] = v / n
        pairs = []
        ids = list(dirs)
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                ang = math.degrees(math.acos(max(-1, min(1, float(np.dot(dirs[ids[a]], dirs[ids[b]]))))))
                if ang >= join_angle: pairs.append((ang, ids[a], ids[b]))
        used = set()
        for ang, a, b in sorted(pairs, reverse=True):
            if a in used or b in used: continue
            used |= {a, b}; parent[fd(a)] = fd(b)
    lab = np.zeros_like(bl)
    for i in range(1, nb + 1):
        if keep[i]: lab[bl == i] = fd(i)
    if lab.max() == 0: return [P]
    # every glyph pixel -> nearest kept branch pixel
    _, (iy, ix) = ndi.distance_transform_edt(lab == 0, return_indices=True)
    own = lab[iy, ix]; own[~mask] = 0
    out = []
    for v in np.unique(own):
        if v == 0: continue
        mv = np.pad(own == v, 1)
        cs = measure.find_contours(mv.astype(float), 0.5)
        ps = []
        for c in cs:
            if len(c) < 4: continue
            pts = [((x - 1 - m) / ppm + x0, (y - 1 - m) / ppm + y0) for y, x in c]
            pg = Polygon(pts).buffer(0)
            if not pg.is_empty: ps.append(pg)
        if not ps: continue
        ps.sort(key=lambda q: -q.area)
        g = ps[0]
        for q in ps[1:]:
            g = g.difference(q) if g.contains(q.representative_point()) else g.union(q)
        out.append(g.buffer(0))
    # exact tiling of the true outline: assign by the raster pieces, then give leftovers to the nearest piece
    pieces = []
    rest = P
    for g in sorted(out, key=lambda q: -q.area):
        q = g.intersection(rest).buffer(0)
        if q.is_empty: continue
        pieces.append(q); rest = rest.difference(q).buffer(0)
    for r in _polys(rest):
        if r.area < 1e-4 or not pieces: continue
        k = min(range(len(pieces)), key=lambda i: pieces[i].distance(r)); pieces[k] = pieces[k].union(r).buffer(0)
    res = []
    for q in pieces:
        for p in _polys(q):
            if p.area < min_area and res:
                k = min(range(len(res)), key=lambda i: res[i].distance(p)); res[k] = res[k].union(p).buffer(0); continue
            res += _cut_ring(p)
    return [p for q in res for p in _polys(q)]
