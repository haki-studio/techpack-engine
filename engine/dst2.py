"""Stitch engine v2 — draft production stitch files from the region art.
 1. Travel routing   : moves between objects run as hidden travel stitches under fill that is sewn later
                       (or over same-colour tatami already sewn); only exposed moves become trims. Later stops form
                       one merged mask (B21); long moves route on a coarse grid (B22); exposed_travel() is the QA (B24).
 2. Turning satin    : elongated satins walk a skeleton centreline, stitches stay perpendicular to it.
                       Long fills are cut into 6 mm sections, each with its own local angle.
 3. Underlay / pull  : satin <2 none, 2-4 centre run, >4 edge run + centre run; tatami edge run (+ 90° tatami at 2.0 mm if > 30 mm²);
                       padded = 2 cross padding layers + edge run. Pull comp = RULES value (buffer per side).
                       Short stitches on the inside of tight curves (alternate stitches pulled in 40%).
 4. Density blends   : later tone of a shading pair is feathered into the earlier one (ragged half-density rows).
 5. Hoop splits      : objects assigned whole to sections that fit a frame; basting registration crosses.
"""
import math, random, pickle, json, sys, os
import numpy as np
import pyembroidery as pe
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
from shapely.geometry import LineString, MultiLineString, Polygon, Point, box
from shapely.ops import unary_union, substring
from shapely import affinity
import tech, stitchrender as SR
from motifs2 import HEX, PAL
import specbase as SB

U = 10.0          # 0.1 mm units
TRIM_MIN = 2.5    # exposed moves shorter than this become plain jumps (no trim)
MERGE_LATER = True   # hidden travel: merge this stop + all later stops into one mask before insetting (LESSONS B21)
TATAMI_CHAIN = True     # tatami rows sewn cell by cell around holes instead of row by row across them (LESSONS B23)
OWN_HALO = 0.25         # travel inside the object being sewn may run this far outside its outline (was 0.6: ran beside thin objects, LESSONS B24)
ROUTE_MAX_PX = 900000   # fine router window limit (pixels)
ROUTE_COARSE = 4        # larger windows are routed on blocks of up to 4 x 4 px and re-checked on the fine raster (0 = trim)
MERGE_ERODE = 1      # inset of that merged mask in raster pixels (1 px = 0.2 mm at 5 px/mm; per-stop masks use 0.25 mm)
RNG = random.Random(1)
# ---- density knobs (v3: production density for 12 oz duck)
SP_TAT, SP_PAD, SP_SAT, SP_RAD = 0.45, 0.45, 0.42, 0.40     # row spacing mm (v2: 0.40 / 0.38 / 0.37 / 0.36)
PAD_LAYERS = 1                                               # padding layers under padded snow (v2: 2)
LATTICE_MIN = 60.0                                           # 90° lattice underlay only under fills > this mm² (v2: 30)
TRAVEL_L = 7.0                                               # hidden travel stitch length (v2: 2.5)
PAD_MIN_W = 3.0                                              # no padding under snow narrower than this (it reads raised anyway)
FEATHER_SP = 1.0                                             # blend row spacing (v2: 0.8)

ALONG = {"TR", "LM", "PB", "-shade", "TW", "-ridge"}       # stitch angle follows the centreline tangent (fill rows along)
ACROSS = {"SN", "PB-SN", "SN-shade", "SN-shadow", "P-snow", "P-snow-shade"}
BLEND = {"-shade": 2.5, "-ridge": 1.4, "SN": 2.0, "BL-rim": 1.2, "PW-inner": 2.5, "P-snow": 1.5}
def pull_for(code, default=0.2):
    """pull compensation for a rule code, read from tech.RULES at call time (rules added by a project after import count)"""
    v = tech.RULES.get(code)
    if v is None: return default
    return float(v[6]) if v[6] not in ("—", "") else 0.0
PULL = {k: pull_for(k) for k in tech.RULES}     # kept for older project scripts; the engine reads pull_for()

# ------------------------------------------------------------------ geometry helpers
def polys(g): return SR.polys(g)

def sub(a, b, L):
    d = math.hypot(b[0]-a[0], b[1]-a[1]); n = max(1, int(math.ceil(d / L)))
    return [(a[0] + (b[0]-a[0])*k/n, a[1] + (b[1]-a[1])*k/n) for k in range(1, n+1)]

def path_resample(pts, L, tol=0.2):
    """even stitches of length <= L along a path; the path is first simplified (tol mm) so dense outline
    vertices don't turn into dozens of 0.3 mm stitches (v2 kept every vertex)."""
    if tol and len(pts) > 2:
        sp = LineString(pts).simplify(tol)
        if not sp.is_empty and len(sp.coords) >= 2: pts = list(sp.coords)
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]): out += sub(a, b, L)
    return out

def width_of(p): return 2 * p.area / max(p.length, 1e-6)

def centreline(p):
    """skeleton longest path, extended to the boundary at both ends. Returns LineString or None."""
    minx, miny, maxx, maxy = p.bounds; span = max(maxx-minx, maxy-miny)
    px = max(2.0, min(10.0, 900.0 / max(span, 1)))
    W, H = int((maxx-minx)*px) + 6, int((maxy-miny)*px) + 6
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    T = lambda cs: [((x-minx)*px + 3, (y-miny)*px + 3) for x, y in cs]
    d.polygon(T(p.exterior.coords), fill=255)
    for r in p.interiors: d.polygon(T(r.coords), fill=0)
    sk = skeletonize(np.array(im) > 127)
    ys, xs = np.nonzero(sk)
    if len(xs) < 4: return None
    idx = {(y, x): i for i, (y, x) in enumerate(zip(ys, xs))}
    nb = [[] for _ in xs]
    for i, (y, x) in enumerate(zip(ys, xs)):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                j = idx.get((y+dy, x+dx))
                if j is not None and j != i: nb[i].append(j)
    def bfs(s):
        dist = {s: 0}; prev = {s: None}; q = [s]
        for u in q:
            for v in nb[u]:
                if v not in dist: dist[v] = dist[u] + 1; prev[v] = u; q.append(v)
        far = max(dist, key=dist.get); return far, prev
    a, _ = bfs(0); b, prev = bfs(a)
    path = []; u = b
    while u is not None: path.append(u); u = prev[u]
    pts = [((xs[i]-3)/px + minx, (ys[i]-3)/px + miny) for i in path]
    if len(pts) < 3: return None
    k = max(1, len(pts)//25)
    sm = [tuple(np.mean(pts[max(0, i-k):i+k+1], axis=0)) for i in range(len(pts))]
    ln = LineString(sm).simplify(0.15)
    # extend both ends along their tangent to the boundary
    def ext(p0, p1):
        v = np.array(p0) - np.array(p1); n = np.linalg.norm(v)
        if n < 1e-6: return p0
        v = v / n; far = (p0[0] + v[0]*span, p0[1] + v[1]*span)
        x = LineString([p0, far]).intersection(p.exterior)
        if x.is_empty: return p0
        pts_ = [x] if x.geom_type == "Point" else [g for g in getattr(x, "geoms", []) if g.geom_type == "Point"]
        if not pts_: return p0
        q = min(pts_, key=lambda g: g.distance(Point(p0))); return (q.x, q.y)
    cs = list(ln.coords)
    if len(cs) < 2: return None
    cs = [ext(cs[0], cs[1])] + cs + [ext(cs[-1], cs[-2])]
    return LineString(cs)

def tangent_at(line, s):
    a = line.interpolate(max(0, s - 0.6)); b = line.interpolate(min(line.length, s + 0.6))
    return math.atan2(b.y - a.y, b.x - a.x)

def is_elongated(p):
    w = width_of(p); return p.length > 0 and (p.length / 2) / max(w, 0.1) > 3.0 and p.area > 3

# ------------------------------------------------------------------ stitch generators (each returns list of point lists)
def run_path(pts, L=2.5): return path_resample(pts, L)

def edge_run(p, inset=0.5, L=2.5):
    q = p.buffer(-inset)
    out = []
    for g in polys(q):
        cs = list(g.exterior.coords)
        if len(cs) > 3: out.append(path_resample(cs, L))
    return out

def chain_rows(segs, p, ang, sp):
    """Order hatch segments cell by cell (boustrophedon): walk up one run of overlapping segments in consecutive rows,
    stop where the run splits around a hole or another unsewn run merges in, then start the nearest new cell.
    hatch() returns segments row by row, so a fill with holes used to zig-zag across every hole on every row
    (one block + one travel move per segment). Returns [(a, b, row)] with a = start point."""
    c = p.centroid
    info = []
    for s in segs:
        cs = list(s.coords)
        if len(cs) < 2: continue
        q = affinity.rotate(LineString([cs[0], cs[-1]]), -ang, origin=c).coords
        (xa, ya), (xb, yb) = q[0], q[-1]
        info.append([min(xa, xb), max(xa, xb), (ya + yb) / 2, cs[0], cs[-1]])
    if not info: return []
    y0 = min(t[2] for t in info)
    rows = {}
    for k, t in enumerate(info):
        t.append(int(round((t[2] - y0) / sp))); rows.setdefault(t[5], []).append(k)
    ov = lambda a, b: min(info[a][1], info[b][1]) - max(info[a][0], info[b][0]) > 0.2
    used = [False] * len(info); out = []; pos = None
    def free_below(k):
        return any(not used[u] and ov(u, k) for u in rows.get(info[k][5] - 1, ()))
    while len(out) < len(info):
        starts = [k for k in range(len(info)) if not used[k] and not free_below(k)] or [k for k in range(len(info)) if not used[k]]
        if pos is None: k = min(starts, key=lambda k: (info[k][5], info[k][0]))
        else: k = min(starts, key=lambda k: min(math.dist(pos, info[k][3]), math.dist(pos, info[k][4])))
        while True:
            a, b = info[k][3], info[k][4]
            if pos is not None and math.dist(pos, b) < math.dist(pos, a): a, b = b, a
            out.append((a, b, info[k][5])); used[k] = True; pos = b
            nxt = [t for t in rows.get(info[k][5] + 1, ()) if not used[t] and ov(k, t)]
            if not nxt: break
            t = min(nxt, key=lambda t: min(math.dist(pos, info[t][3]), math.dist(pos, info[t][4])))
            if any(not used[u] and ov(u, t) for u in rows[info[k][5]]): break     # another unsewn run joins here
            k = t
    return out

def tatami_rows(p, ang, sp=0.40, L=3.5):
    pts = []
    if p.is_empty or p.area < 0.05: return pts
    segs = SR.hatch(p, ang, sp)
    if TATAMI_CHAIN:
        seq = chain_rows(segs, p, ang, sp)
    else:
        seq = []
        for i, s in enumerate(segs):
            cs = list(s.coords)
            if len(cs) < 2: continue
            seq.append(((cs[0], cs[-1]) if i % 2 == 0 else (cs[-1], cs[0])) + (i,))
    for a, b, i in seq:
        d = math.hypot(b[0]-a[0], b[1]-a[1]); ux, uy = (b[0]-a[0])/max(d, 1e-9), (b[1]-a[1])/max(d, 1e-9)
        off = (i % 3) * L / 3; run = [a]; t = off if off > 0.4 else L
        while t < d - 0.4:
            run.append((a[0] + ux*t, a[1] + uy*t)); t += L
        run.append(b); pts.append(run)
    return pts

def join_rows(rows):
    """join consecutive hatch rows into one block if the hop between them is short (stays inside the fill)."""
    blocks, cur = [], []
    for r in rows:
        if cur and math.hypot(r[0][0]-cur[-1][0], r[0][1]-cur[-1][1]) > 1.2:
            blocks.append(cur); cur = []
        cur += r
    if cur: blocks.append(cur)
    return blocks

def turning_satin(p, line, sp=None, pull=0.2, short=True):
    sp = sp or SP_SAT
    pp = p.buffer(pull, join_style="round") if pull else p
    L = line.length; n = max(2, int(L / sp)); pts = []; lastA = lastB = None; flip = False
    for k in range(n + 1):
        s = L * k / n; c = line.interpolate(s); th = tangent_at(line, s) + math.pi/2
        R = 40.0
        seg = LineString([(c.x - R*math.cos(th), c.y - R*math.sin(th)), (c.x + R*math.cos(th), c.y + R*math.sin(th))]).intersection(pp)
        segs = [seg] if seg.geom_type == "LineString" else [g for g in getattr(seg, "geoms", []) if g.geom_type == "LineString"]
        if not segs: continue
        sg = min(segs, key=lambda g: g.distance(c))
        a, b = sg.coords[0], sg.coords[-1]
        if lastA is not None and math.hypot(a[0]-lastA[0], a[1]-lastA[1]) > math.hypot(b[0]-lastA[0], b[1]-lastA[1]):
            a, b = b, a
        if short and lastA is not None:      # inner side of a curve: endpoints bunch up -> shorten alternate stitches
            for side in (0, 1):
                e, le = (a, lastA) if side == 0 else (b, lastB)
                if math.hypot(e[0]-le[0], e[1]-le[1]) < 0.18 and k % 2:
                    e2 = (e[0] + (c.x - e[0])*0.4, e[1] + (c.y - e[1])*0.4)
                    if side == 0: a = e2
                    else: b = e2
        lastA, lastB = a, b
        if math.hypot(b[0]-a[0], b[1]-a[1]) > 7.0:   # split satin
            m = int(math.ceil(math.hypot(b[0]-a[0], b[1]-a[1]) / 6.0))
            seq = [a] + sub(a, b, math.hypot(b[0]-a[0], b[1]-a[1]) / m)
        else:
            seq = [a, b]
        pts += seq if not flip else seq[::-1]
        flip = not flip
    return pts

def fixed_satin(p, ang, sp=None, pull=0.2):
    sp = sp or SP_SAT
    pp = p.buffer(pull, join_style="round") if pull else p
    if pp.is_empty: return []
    out = []
    for i, s in enumerate(SR.hatch(pp, ang, sp)):
        cs = list(s.coords)
        if len(cs) < 2: continue
        a, b = (cs[0], cs[-1]) if i % 2 == 0 else (cs[-1], cs[0])
        d = math.hypot(b[0]-a[0], b[1]-a[1])
        out += [a] + (sub(a, b, d / math.ceil(d / 6.0)) if d > 7.0 else [b])
    return out

def radial_satin(p, cx, cy, sp=None, pull=0.15, short=True):
    sp = sp or SP_RAD
    pp = p.buffer(pull) if pull else p
    out = []
    for i, s in enumerate(SR.radial(pp, cx, cy, sp)):
        cs = list(s.coords)
        if len(cs) < 2: continue
        a, b = cs[0], cs[-1]
        if math.hypot(a[0]-cx, a[1]-cy) > math.hypot(b[0]-cx, b[1]-cy): a, b = b, a     # a = inner end
        if short and i % 2:      # short stitches toward the centre
            a = (a[0] + (b[0]-a[0])*0.35, a[1] + (b[1]-a[1])*0.35)
        seg = [a, b] if i % 2 == 0 else [b, a]
        d = math.hypot(b[0]-a[0], b[1]-a[1])
        out += [seg[0]] + (sub(seg[0], seg[1], d / math.ceil(d / 6.0)) if d > 7.0 else [seg[1]])
    return out

def sections(p, line, step=6.0, across=False):
    """cut a long fill into pieces with their own local angle."""
    out = []; L = line.length; n = max(1, int(L / step))
    cuts = []
    for k in range(1, n):
        s = L * k / n; c = line.interpolate(s); th = tangent_at(line, s) + math.pi/2; R = 60
        cuts.append(LineString([(c.x - R*math.cos(th), c.y - R*math.sin(th)), (c.x + R*math.cos(th), c.y + R*math.sin(th))]))
    pieces = [p]
    if cuts:
        from shapely.ops import split
        blade = unary_union(cuts)
        try:
            pieces = [g for g in split(p, blade).geoms if g.geom_type == "Polygon" and g.area > 0.05]
        except Exception:
            pieces = [p]
    for q in pieces:
        s = line.project(q.representative_point()); th = math.degrees(tangent_at(line, s))
        out.append((q, th + 90 if across else th))
    return out

def feather(r, zone, ang, width):
    """ragged half-density rows extending r's colour into an earlier neighbouring tone."""
    if zone.is_empty: return []
    src = r["geom"]; out = []
    for i, s in enumerate(SR.hatch(zone, ang, FEATHER_SP)):
        cs = list(s.coords)
        if len(cs) < 2: continue
        a, b = cs[0], cs[-1]
        if Point(b).distance(src) < Point(a).distance(src): a, b = b, a
        f = RNG.uniform(0.15, 1.0) ** 1.6
        e = (a[0] + (b[0]-a[0])*f, a[1] + (b[1]-a[1])*f)
        if math.hypot(e[0]-a[0], e[1]-a[1]) > 0.5:
            out.append([a, e] if i % 2 == 0 else [e, a])
    return out

# ------------------------------------------------------------------ object builder
def build_object(r, earlier_tones):
    """returns list of blocks (point lists) for one region, underlay first."""
    code = tech.rule_for(r["grp"]); st = r["st"]; ang = r["ang"]; pull = pull_for(code)
    blocks = []
    for p in polys(r["geom"]):
        if p.area < 0.06: continue
        w = width_of(p)
        if st in ("bean", "run"):
            cs = list(p.exterior.coords); blocks.append(path_resample(cs, 2.0 if st == "bean" else 2.6)); continue
        if isinstance(ang, tuple):   # radial
            if st == "tatami":
                blocks += edge_run(p, 0.6)
                # turning tatami: radial rows split into stitches
                rows = []
                for i, s in enumerate(SR.radial(p.buffer(pull), ang[1], ang[2], SP_TAT)):
                    cs = list(s.coords)
                    if len(cs) < 2: continue
                    a, b = (cs[0], cs[-1]) if i % 2 == 0 else (cs[-1], cs[0])
                    rows.append([a] + sub(a, b, 3.5))
                blocks += join_rows(rows)
            else:
                if w > 2.5: blocks += edge_run(p, 0.45)
                blocks.append(radial_satin(p, ang[1], ang[2], pull=pull))
            continue
        line = centreline(p) if (is_elongated(p) and (st == "satin" or code in ALONG | ACROSS)) else None
        if st == "satin":
            if w > 4.0: blocks += edge_run(p, 0.5)
            if line is not None:
                if w >= 2.0: blocks.append(path_resample(list(line.coords), 2.0))      # centre run underlay
                blocks.append(turning_satin(p, line, pull=pull))
            else:
                a = SR.auto_angle(p) if ang in ("auto", None) else ang
                blocks.append(fixed_satin(p, a, pull=pull))
        else:   # tatami / padded
            blocks += edge_run(p, 0.6)
            if line is not None and code in ALONG | ACROSS:
                parts = sections(p, line, 6.0, across=code in ACROSS)
            else:
                a = SR.auto_angle(p) - 90 if ang in ("auto", None) else ang
                parts = [(p, a)]
            for q, a in parts:
                if st == "tatami" and q.area > LATTICE_MIN:      # light 90° tatami underlay under larger fills
                    blocks += join_rows(tatami_rows(q.buffer(-0.8), a + 90, 2.0, 4.0))
                if st == "padded" and q.area > 4 and w > PAD_MIN_W:
                    blocks += join_rows(tatami_rows(q.buffer(-0.5), a + 90, 0.8 if PAD_LAYERS > 1 else 1.0, 4.0))
                    if PAD_LAYERS > 1: blocks += join_rows(tatami_rows(q.buffer(-0.5), a + 45, 0.8, 4.0))
                blocks += join_rows(tatami_rows(q.buffer(pull * 0.5) if pull else q, a, SP_TAT if st == "tatami" else SP_PAD, 3.5 if st == "tatami" else 5.0))
    # density blend into the earlier tone
    if code in BLEND and earlier_tones is not None and not earlier_tones.is_empty:
        fw = BLEND[code]
        ring = r["geom"].buffer(fw).difference(r["geom"])
        zone = earlier_tones.clip(ring) if hasattr(earlier_tones, "clip") else ring.intersection(earlier_tones)
        a = SR.auto_angle(r["geom"]) if (ang in ("auto", None) or isinstance(ang, tuple)) else ang
        blocks += feather(r, zone, a, fw)
    return [b for b in blocks if len(b) > 1]


# ------------------------------------------------------------------ production cleanup
def clean_vis(vis, close=0.3, min_area=1.5, min_w=0.7, min_line=0.8):
    """Remove knockout slivers that cannot be sewn (or only add trims): morphological close per region,
    drop fill fragments under min_area mm2 or narrower than min_w, drop line fragments under min_line mm2."""
    out = []
    for r in vis:
        g = r["geom"]
        if r["st"] in ("bean", "run"):
            keep = [p for p in polys(g.buffer(0)) if p.area >= min_line]
        else:
            g = g.buffer(0).buffer(close, join_style=2).buffer(-close, join_style=2)
            keep = [p for p in polys(g) if p.area >= min_area and not p.buffer(-min_w / 2).is_empty]
        if keep:
            out.append(dict(r, geom=unary_union([p.buffer(0) for p in keep]).buffer(0)))
    return out

# ------------------------------------------------------------------ fast geometry helpers (LESSONS B13)
def bounds_of(geoms):
    """envelope of many geometries = bounds of their union, without computing the union (that union cost ~1 min on a back)."""
    bs = np.array([g.bounds for g in geoms if not g.is_empty])
    return (bs[:, 0].min(), bs[:, 1].min(), bs[:, 2].max(), bs[:, 3].max())

class Tones:
    """fill already sewn by earlier stops, queried locally. Replaces unary_union(all earlier fills) per stop,
    which grew with every stop and was ~60 % of a back build (265 s of 454 s on XS)."""
    def __init__(self): self.ps = []; self.tree = None
    def add(self, g): self.ps += [p for p in polys(g) if not p.is_empty]; self.tree = None
    @property
    def is_empty(self): return not self.ps
    def clip(self, zone):
        if not self.ps or zone.is_empty: return Polygon()
        if self.tree is None:
            from shapely.strtree import STRtree
            self.tree = STRtree(self.ps)
        hit = [self.ps[i] for i in self.tree.query(zone, predicate="intersects")]
        return unary_union([zone.intersection(p) for p in hit]) if hit else Polygon()

def cut_length(geoms, line, tree=None):
    """length of `line` inside the union of `geoms` (1-D interval merge along the line; no 2-D union)."""
    from shapely.strtree import STRtree
    tree = tree or STRtree(geoms); (ax, ay), (bx, by) = line.coords[0], line.coords[-1]
    L = math.hypot(bx - ax, by - ay); ux, uy = (bx - ax) / L, (by - ay) / L; iv = []
    for i in tree.query(line, predicate="intersects"):
        for seg in [geoms[i].intersection(line)]:
            for part in getattr(seg, "geoms", [seg]):
                if part.is_empty or part.length == 0: continue
                ts = [(x - ax) * ux + (y - ay) * uy for x, y in part.coords]; iv.append((min(ts), max(ts)))
    iv.sort(); tot = 0.0; cur = None
    for a, b in iv:
        if cur is None or a > cur[1]: tot += (cur[1] - cur[0]) if cur else 0.0; cur = [a, b]
        else: cur[1] = max(cur[1], b)
    return tot + ((cur[1] - cur[0]) if cur else 0.0)

# ------------------------------------------------------------------ coverage raster for hidden travel
class Cover:
    def __init__(self, bounds, ppm=5.0):
        self.x0, self.y0 = bounds[0] - 5, bounds[1] - 5; self.ppm = ppm
        self.W = int((bounds[2] - bounds[0] + 10) * ppm); self.H = int((bounds[3] - bounds[1] + 10) * ppm)
        self.later = np.full((self.H, self.W), -1, np.int16)    # last stop index whose fill covers the pixel
        self.raw = np.full((self.H, self.W), -1, np.int16)      # same, drawn without inset (for the merged mask)
    def _draw(self, g, inset=0.4):
        im = Image.new("L", (self.W, self.H), 0); d = ImageDraw.Draw(im)
        for p in polys(g.buffer(-inset) if inset else g):
            T = lambda cs: [((x - self.x0)*self.ppm, (y - self.y0)*self.ppm) for x, y in cs]
            d.polygon(T(p.exterior.coords), fill=255)
            for q in p.interiors: d.polygon(T(q.coords), fill=0)
        return np.array(im) > 127
    def add_stop(self, idx, g, inset=0.25):
        self.later[self._draw(g, inset)] = idx
        if MERGE_LATER: self.raw[self._draw(g, 0.0)] = idx
    def merged(self, stop_idx):
        """everything sewn from stop_idx on (this stop's own fills + all later stops) as ONE mask, inset once.
        Insetting each stop on its own left a ~0.5 mm unhidden strip on every seam between two different later
        fills, so travel could not cross from one to the other although pull comp covers that seam (LESSONS B21)."""
        if not MERGE_LATER: return np.zeros_like(self.raw, bool)
        return ndi.binary_erosion(self.raw >= stop_idx, structure=np.ones((3, 3), bool), iterations=MERGE_ERODE)
    def hidden(self, a, b, stop_idx, sewn_mask=None):
        n = max(2, int(math.hypot(b[0]-a[0], b[1]-a[1]) * self.ppm))
        xs = ((np.linspace(a[0], b[0], n) - self.x0) * self.ppm).astype(int)
        ys = ((np.linspace(a[1], b[1], n) - self.y0) * self.ppm).astype(int)
        ok = (xs >= 0) & (ys >= 0) & (xs < self.W) & (ys < self.H)
        if not ok.all(): return False
        hid = self.later[ys, xs] > stop_idx
        if sewn_mask is not None: hid |= sewn_mask[ys, xs]
        return bool(hid.all())
    def blank(self): return np.zeros((self.H, self.W), bool)
    def route(self, a, b, stop_idx, sewn_mask, own=None, pad=12.0):
        """least-cost path from a to b through pixels hidden (later fill / same-colour sewn / own object).
        Returns list of mm points if fully hidden, else None."""
        from skimage.graph import route_through_array
        x0 = min(a[0], b[0]) - pad; y0 = min(a[1], b[1]) - pad; x1 = max(a[0], b[0]) + pad; y1 = max(a[1], b[1]) + pad
        c0 = max(0, int((x0 - self.x0)*self.ppm)); r0 = max(0, int((y0 - self.y0)*self.ppm))
        c1 = min(self.W, int((x1 - self.x0)*self.ppm) + 1); r1 = min(self.H, int((y1 - self.y0)*self.ppm) + 1)
        if c1 - c0 < 3 or r1 - r0 < 3: return None
        f = max(1, math.ceil(math.sqrt((c1 - c0) * (r1 - r0) / ROUTE_MAX_PX)))
        if f > 1 and (not ROUTE_COARSE or f > ROUTE_COARSE): return None
        hid = (self.later[r0:r1, c0:c1] > stop_idx) | sewn_mask[r0:r1, c0:c1]
        if own is not None:
            im = Image.new("L", (c1 - c0, r1 - r0), 0); dr = ImageDraw.Draw(im)
            for p in polys(own.intersection(box(x0, y0, x1, y1))):
                T = lambda cs: [((x - self.x0)*self.ppm - c0, (y - self.y0)*self.ppm - r0) for x, y in cs]
                dr.polygon(T(p.exterior.coords), fill=255)
                for q in p.interiors: dr.polygon(T(q.coords), fill=0)
            hid = hid | (np.array(im) > 127)
        P = lambda p: (min(r1 - r0 - 1, max(0, int((p[1] - self.y0)*self.ppm) - r0)), min(c1 - c0 - 1, max(0, int((p[0] - self.x0)*self.ppm) - c0)))
        if f > 1: return self._route_coarse(a, b, hid, f, P, c0, r0)
        sa, sb = P(a), P(b)
        cost = np.where(hid, 1.0, 400.0)
        for (pr, pc_) in (sa, sb):                     # endpoints sit on the pull-compensated edge: forgive ~0.8 mm
            cost[max(0, pr-4):pr+5, max(0, pc_-4):pc_+5] = 1.0
        try:
            path, tot = route_through_array(cost, sa, sb, fully_connected=True, geometric=True)
        except Exception:
            return None
        if tot > 1.6 * len(path) + 3 * 400 + 40: return None   # crossed more than ~0.6 mm of exposed fabric
        pts = [((c + c0) / self.ppm + self.x0, (r + r0) / self.ppm + self.y0) for r, c in path]
        L = sum(math.hypot(q[0]-p[0], q[1]-p[1]) for p, q in zip(pts, pts[1:]))
        if L > 4.0 * math.hypot(b[0]-a[0], b[1]-a[1]) + 25: return None   # absurd detour -> trim instead
        out = [a] + [p for i, p in enumerate(pts[1:-1]) if i % 6 == 5] + [b]
        return LineString(out).simplify(0.4).coords[:]
    def _route_coarse(self, a, b, hid, f, P, c0, r0):
        """route() for a window too big for the fine raster (long moves inside big fills, LESSONS B22): least-cost path on
        f x f blocks (a block is hidden only if all its pixels are), then the path is re-checked on the fine raster with
        the same 0.6 mm exposed allowance."""
        from skimage.graph import route_through_array
        H, W = hid.shape[0] // f * f, hid.shape[1] // f * f
        hc = hid[:H, :W].reshape(H // f, f, W // f, f).all(axis=(1, 3))
        cost = np.where(hc, 1.0, 400.0)
        sa, sb = P(a), P(b); sa = (min(sa[0] // f, H // f - 1), min(sa[1] // f, W // f - 1)); sb = (min(sb[0] // f, H // f - 1), min(sb[1] // f, W // f - 1))
        e = max(1, 4 // f)
        for (pr, pc_) in (sa, sb): cost[max(0, pr-e):pr+e+1, max(0, pc_-e):pc_+e+1] = 1.0
        try:
            path, tot = route_through_array(cost, sa, sb, fully_connected=True, geometric=True)
        except Exception:
            return None
        if tot > 1.6 * len(path) + 3 * 400 / f + 40: return None
        pts = [a] + [((c * f + f / 2 + c0) / self.ppm + self.x0, (r * f + f / 2 + r0) / self.ppm + self.y0) for r, c in path[1:-1]] + [b]
        out = LineString(pts).simplify(0.4)
        L = out.length
        if L > 4.0 * math.hypot(b[0]-a[0], b[1]-a[1]) + 25: return None
        # fine check: exposed length along the path (first/last 0.8 mm forgiven, like the fine router's endpoint window)
        n = max(2, int(L * self.ppm * 2))
        ss = np.linspace(0, L, n); keep = (ss > 0.8) & (ss < L - 0.8)
        q = [out.interpolate(t) for t in ss[keep]]
        if q:
            cs = np.clip(((np.array([g.x for g in q]) - self.x0) * self.ppm).astype(int) - c0, 0, hid.shape[1] - 1)
            rs = np.clip(((np.array([g.y for g in q]) - self.y0) * self.ppm).astype(int) - r0, 0, hid.shape[0] - 1)
            if (~hid[rs, cs]).sum() * (L / n) > 0.6: return None
        return out.coords[:]
    def stamp(self, mask, g):
        im = self._draw(g, 0.6); mask |= im

# ------------------------------------------------------------------ pattern assembly
FILL_ST = ("tatami", "padded", "satin")

def make_pattern(vis, stops, origin, reg_marks=None, builder=None, keep_order=False, threads=None):
    """Regions -> pyembroidery pattern, with hidden travel and trims (see the module doc).
    Hooks for engine/digitize/compile.py (ENGINE_PLAN M1); the defaults reproduce the old behaviour exactly:
      builder(r, earlier_tones) -> [blocks]  replaces build_object; called once per REGION (not per polygon piece), so a
                   prebuilt plan (r["blocks"]) is emitted exactly as planned
      keep_order   sew each stop's regions in the given order (no stitch-type sort, no nearest-first reordering): the
                   plan's rank is the sew order
      threads      {col: dict(hex, description, catalog, brand)} for colours that are not motifs2.HEX keys
    stats["labels"] holds one entry per STITCH added: the region's r.get("part") (None = travel / registration)."""
    cov = Cover(bounds_of([r["geom"] for r in vis]))
    for i, s in enumerate(stops):
        g = unary_union([r["geom"] for r in s["regions"] if r["st"] in FILL_ST])
        if not g.is_empty: cov.add_stop(i, g)
        gl = unary_union([r["geom"] for r in s["regions"] if r["st"] == "bean"])
        if not gl.is_empty: cov.add_stop(i, gl, inset=0.12)      # travel may hide under triple-run lines too
    # tones sewn so far (for blends): union of fill geometry per colour sewn earlier
    tones = Tones()
    pat = pe.EmbPattern(); ox, oy = origin
    stats = dict(stitches=0, trims=0, travel=0, jumps=0, runs=[], labels=[])     # runs: (stop, travel polyline) for exposed_travel()
    stitch_labels = stats["labels"]
    def emit_thread(k, label=None):
        th = pe.EmbThread()
        if threads and k in threads:
            t = threads[k]; th.set_hex_color(t["hex"]); th.description = t.get("description", k)
            th.catalog_number = t.get("catalog", ""); th.brand = t.get("brand", ""); pat.add_thread(th); return
        th.set_hex_color(HEX[k] if k in HEX else k)
        if k in HEX:
            pn = SB.TH[k]["polyneon"]; iso = SB.TH[k]["isacord"]
            th.description = f"{PAL[k][1]} (Polyneon {pn[0]} / Isacord {iso[0]})"; th.catalog_number = pn[0]; th.brand = "Madeira Polyneon"
        else:
            th.description = label or "basting"; th.catalog_number = "WSB"
        pat.add_thread(th)
    cur = None; first_stop = True
    if reg_marks:
        emit_thread("#00A3FF", "REGISTRATION basting - water-soluble, remove"); first_stop = False
        for (mx, my) in reg_marks:
            for seg in ([(mx - 6, my), (mx + 6, my)], [(mx, my - 6), (mx, my + 6)]):
                pat.add_command(pe.TRIM) if cur else None
                pat.add_stitch_absolute(pe.JUMP, (seg[0][0]-ox)*U, (seg[0][1]-oy)*U)
                for x, y in path_resample(seg, 4.0): pat.add_stitch_absolute(pe.STITCH, (x-ox)*U, (y-oy)*U); stitch_labels.append(None)
                cur = seg[-1]
        pat.add_command(pe.TRIM)
    for si, s in enumerate(stops):
        k = s["col"]
        if not first_stop: pat.add_command(pe.COLOR_CHANGE)
        emit_thread(k); first_stop = False
        earlier = tones
        objs = []
        regs = list(s["regions"]) if keep_order else sorted(s["regions"], key=lambda r: {"tatami": 0, "padded": 1, "satin": 2, "run": 3, "bean": 4}[r["st"]])
        for r in regs:
            if builder is not None:             # prebuilt / plugin blocks: one object per region, blocks as given
                bl = [b for b in builder(r, earlier) if len(b) > 1]
                if bl: objs.append(dict(blocks=bl, r=r, own=r["geom"].buffer(OWN_HALO)))
                continue
            for p in polys(r["geom"]):          # one object per connected piece, so ordering can chain them
                rp_ = dict(r, geom=p)
                bl = build_object(rp_, earlier)
                if bl: objs.append(dict(blocks=bl, r=rp_, own=p.buffer(OWN_HALO)))
        sewn_same = cov.blank()
        # hidden-travel mask for this stop: fill sewn by later stops + this stop's own fills/satins
        # (travel under an object that is about to be sewn over is a standard underpath)
        own_mask = cov.blank()
        for o in objs:
            if o["r"]["st"] in FILL_ST: own_mask |= cov._draw(o["r"]["geom"], -0.1)
        base_hid = (cov.later > si) | own_mask | cov.merged(si)
        lab, _ = ndi.label(ndi.binary_dilation(base_hid, iterations=2), structure=np.ones((3, 3), int))
        def comp(pt, rad=3):
            c = int((pt[0] - cov.x0) * cov.ppm); r_ = int((pt[1] - cov.y0) * cov.ppm)
            win = lab[max(0, r_-rad):r_+rad+1, max(0, c-rad):c+rad+1]
            return int(win.max()) if win.size else 0
        for o in objs:
            o["c0"] = comp(o["blocks"][0][0]); o["c1"] = comp(o["blocks"][-1][-1])
        sewn_same = base_hid.copy()
        # ordering: stay inside the current hidden component (nearest first); jump (trim) only when it is exhausted
        rest = [] if keep_order else list(range(len(objs))); order = list(range(len(objs))) if keep_order else []
        pos = cur; pc = comp(cur) if cur is not None else 0
        def d0(i): st0 = objs[i]["blocks"][0][0]; return math.hypot(st0[0]-pos[0], st0[1]-pos[1])
        while rest:
            if pos is None: j = rest[0]
            else:
                same = [i for i in rest if pc and objs[i]["c0"] == pc] or [i for i in rest if d0(i) < TRIM_MIN]
                pool = same if same else rest
                if not same:      # next component: prefer the one holding most remaining objects nearby
                    j = min(pool, key=d0)
                else:
                    j = min(pool, key=d0)
            rest.remove(j); order.append(j); pos = objs[j]["blocks"][-1][-1]; pc = objs[j]["c1"] or objs[j]["c0"]
        prev_o = None
        for j in order:
            o = objs[j]
            for b in o["blocks"]:
                x0, y0 = b[0]
                if cur is not None:
                    d = math.hypot(x0 - cur[0], y0 - cur[1])
                    route = None
                    if d < 0.3: route = []
                    elif d <= 1.0: route = [(x0, y0)]
                    elif LineString([cur, (x0, y0)]).within(o["own"]) or cov.hidden(cur, (x0, y0), si, sewn_same):
                        route = path_resample([cur, (x0, y0)], TRAVEL_L)
                    else:
                        rp = cov.route(cur, (x0, y0), si, sewn_same, o["own"] if o is prev_o or o.get("started") else None,
                                       pad=max(12.0, 0.5 * d))
                        if rp: route = path_resample(rp, TRAVEL_L)
                    if route is not None:
                        if len(route) > 1: stats["runs"].append((si, [tuple(cur)] + [tuple(q) for q in route]))
                        for x, y in route[:-1] if len(route) > 1 else route:
                            pat.add_stitch_absolute(pe.STITCH, (x-ox)*U, (y-oy)*U); stats["travel"] += 1; stitch_labels.append(None)
                    elif d < TRIM_MIN:
                        pat.add_stitch_absolute(pe.JUMP, (x0-ox)*U, (y0-oy)*U); stats["jumps"] += 1
                    else:
                        pat.add_command(pe.TRIM); stats["trims"] += 1
                        stats.setdefault("by", {}); kk = tech.rule_for(o["r"]["grp"]) + ("/intra" if o.get("started") else ""); stats["by"][kk] = stats["by"].get(kk, 0) + 1
                        # why: 'island' = no hidden connection between the two points; 'route' = same hidden area, router gave up
                        wk = "route" if (comp(cur) and comp(cur) == comp((x0, y0))) else "island"
                        stats.setdefault("why", {}); stats["why"][wk] = stats["why"].get(wk, 0) + 1
                        pat.add_stitch_absolute(pe.JUMP, (x0-ox)*U, (y0-oy)*U)
                else:
                    pat.add_stitch_absolute(pe.JUMP, (x0-ox)*U, (y0-oy)*U)
                last = None
                for (x, y) in b:
                    if last is not None:
                        d = math.hypot(x-last[0], y-last[1])
                        if d < 0.25: continue
                        if d > 7.4:        # safety: never a sewn stitch > 7.5 mm after 0.1 mm grid rounding (LESSONS B17)
                            for q in sub(last, (x, y), 6.0)[:-1]:
                                pat.add_stitch_absolute(pe.STITCH, (q[0]-ox)*U, (q[1]-oy)*U); stats["stitches"] += 1; stitch_labels.append(o["r"].get("part"))
                    pat.add_stitch_absolute(pe.STITCH, (x-ox)*U, (y-oy)*U); stats["stitches"] += 1; last = (x, y); stitch_labels.append(o["r"].get("part"))
                cur = b[-1]; o["started"] = True
            if o["r"]["st"] in ("tatami", "padded"): cov.stamp(sewn_same, o["r"]["geom"])
            prev_o = o
        fills = [r["geom"] for r in s["regions"] if r["st"] in FILL_ST]
        if fills: tones.add(unary_union(fills))
    pat.add_command(pe.TRIM); pat.add_command(pe.END)
    return pat, stats

def exposed_travel(stops, runs, forgive=0.8, tol=0.3):
    """QA for hidden travel, measured on the region geometry (not the router's raster): for every travel run, the longest
    stretch that lies on bare fabric, i.e. outside every fill/bean sewn at or after the run's stop. The first and last
    `forgive` mm of a run are skipped (they sit on the pull-compensated edges of the two objects they join); a fill
    covers `tol` mm beyond its outline (pull comp, and the router's raster is drawn to the pixel).
    Returns the sorted list of exposed lengths (mm), one per run with any exposure."""
    from shapely.strtree import STRtree
    gs, ix = [], []
    for i, s in enumerate(stops):
        for r in s["regions"]:
            if r["st"] in FILL_ST or r["st"] == "bean":
                for p in polys(r["geom"]): gs.append(p); ix.append(i)
    if not gs: return []
    tree = STRtree(gs); ix = np.array(ix); out = []
    for si, pts in runs:
        ln = LineString(pts)
        if ln.length <= 2 * forgive: continue
        ln = substring(ln, forgive, ln.length - forgive)
        hits = [h for h in tree.query(ln.buffer(tol), predicate="intersects") if ix[h] >= si]
        bare = ln.difference(unary_union([gs[h].buffer(tol, 4) for h in hits])) if hits else ln
        if not bare.is_empty and bare.length > 1e-3:
            out.append(max(g.length for g in getattr(bare, "geoms", [bare])))
    return sorted(out)

def write(pat, base):
    settings = {"long_stitch_contingency": pe.CONTINGENCY_LONG_STITCH_SEW_TO, "max_stitch": 121, "max_jump": 121,
                "tie_on": pe.CONTINGENCY_TIE_ON_THREE_SMALL, "tie_off": pe.CONTINGENCY_TIE_OFF_THREE_SMALL}
    pe.write_dst(pat, base + ".dst", settings)
    pe.write_pes(pat, base + ".pes", dict(settings, **{"pes version": 6}))

def verify(base):
    p = pe.read(base + ".pes"); S = p.stitches; L = []
    import collections
    c = collections.Counter(s[2] & pe.COMMAND_MASK for s in S)
    for a, b in zip(S, S[1:]):
        if a[2] & pe.COMMAND_MASK == pe.STITCH and b[2] & pe.COMMAND_MASK == pe.STITCH: L.append(math.hypot(b[0]-a[0], b[1]-a[1]) / 10)
    ex = p.extents()
    return dict(stitches=c[pe.STITCH], trims=c[pe.TRIM], jumps=c[pe.JUMP], colour_changes=c[pe.COLOR_CHANGE],
                max_stitch=round(max(L), 2) if L else 0, size=(round((ex[2]-ex[0])/10, 1), round((ex[3]-ex[1])/10, 1)))

def render(base, out_png, bg=(215, 194, 156), s=0.5):
    p = pe.read(base + ".pes"); ex = p.extents()
    im = Image.new("RGB", (int((ex[2]-ex[0])*s) + 20, int((ex[3]-ex[1])*s) + 20), bg); d = ImageDraw.Draw(im)
    cols = [t.hex_color() for t in p.threadlist]; ci = 0; prev = None
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK; P = ((x-ex[0])*s + 10, (y-ex[1])*s + 10)
        if k == pe.STITCH:
            if prev: d.line([prev, P], fill=cols[min(ci, len(cols)-1)], width=1)
            prev = P
        elif k == pe.COLOR_CHANGE: ci += 1; prev = None
        elif k == pe.TRIM: prev = None
        else: prev = P
    im.save(out_png)

# ------------------------------------------------------------------ hoop split
def split_sections(vis, frame=(360.0, 360.0), margin=8.0):
    """2x2 (or 1x2/2x1) split. Objects (regions) go whole to the section holding their representative point;
    split lines are searched to minimise cut length through art and to keep each section inside the frame."""
    from shapely.strtree import STRtree
    GS = [p for r in vis for p in polys(r["geom"])]; GT = STRtree(GS); b = bounds_of(GS)
    fw, fh = frame[0] - 2*margin, frame[1] - 2*margin
    nx = 1 if b[2]-b[0] <= fw else 2; ny = 1 if b[3]-b[1] <= fh else 2
    best = None
    xs = np.linspace(b[0] + (b[2]-b[0])*0.35, b[0] + (b[2]-b[0])*0.65, 13) if nx == 2 else [None]
    ys = np.linspace(b[1] + (b[3]-b[1])*0.35, b[1] + (b[3]-b[1])*0.65, 13) if ny == 2 else [None]
    reps = [(r, r["geom"].representative_point()) for r in vis]
    for sx in xs:
        for sy in ys:
            secs = {}
            for r, pnt in reps:
                key = (0 if sx is None or pnt.x < sx else 1, 0 if sy is None or pnt.y < sy else 1)
                secs.setdefault(key, []).append(r)
            ok = True; bbs = {}
            for key, rs in secs.items():
                bb = bounds_of([r["geom"] for r in rs]); bbs[key] = bb
                if bb[2]-bb[0] > fw or bb[3]-bb[1] > fh: ok = False
            cut = 0.0
            if sx is not None: cut += cut_length(GS, LineString([(sx, b[1]), (sx, b[3])]), GT)
            if sy is not None: cut += cut_length(GS, LineString([(b[0], sy), (b[2], sy)]), GT)
            score = cut + (0 if ok else 1e6)
            if best is None or score < best[0]: best = (score, sx, sy, secs, bbs, ok)
    return best

def reg_marks_for(sx, sy, b):
    m = []
    if sx is not None: m += [(sx, b[1] + (b[3]-b[1])*0.2), (sx, b[1] + (b[3]-b[1])*0.8)]
    if sy is not None: m += [(b[0] + (b[2]-b[0])*0.2, sy), (b[0] + (b[2]-b[0])*0.8, sy)]
    if sx is not None and sy is not None: m.append((sx, sy))
    return m

def split_clip(vis, frame=(360.0, 360.0), margin=8.0, overlap=1.2, whole_max=70.0, ext=18.5, arm=6.0):   # ext = cross 12 mm out + 6 mm arm + 0.5; arm = cross arm on the split line
    """Production split. Small components (bbox < whole_max mm) go whole to the section that holds their
    representative point; larger fills are cut at the split line with `overlap` mm sewn into both sections
    so the join never shows fabric. The split position is searched to minimise length cut through art."""
    from shapely.strtree import STRtree
    GS = [p for r in vis for p in polys(r["geom"])]; GT = STRtree(GS); b = bounds_of(GS)
    fw, fh = frame[0] - 2*margin, frame[1] - 2*margin
    nx = 1 if b[2]-b[0] <= fw else 2; ny = 1 if b[3]-b[1] <= fh else 2
    xs = np.linspace(b[0] + (b[2]-b[0])*0.40, b[0] + (b[2]-b[0])*0.60, 21) if nx == 2 else [None]
    ys = np.linspace(b[1] + (b[3]-b[1])*0.40, b[1] + (b[3]-b[1])*0.60, 21) if ny == 2 else [None]
    best = None
    def fits_cand(sx, sy):        # each half (+ the outer registration crosses, ext mm beyond the art) must fit the frame
        ok = True
        if sx is not None: ok &= (sx - b[0] + ext + arm <= fw) and (b[2] - sx + ext + arm <= fw)
        if sy is not None: ok &= (sy - b[1] + ext + arm <= fh) and (b[3] - sy + ext + arm <= fh)
        return ok
    if any(fits_cand(sx, sy) for sx in xs for sy in ys):
        cands = [(sx, sy) for sx in xs for sy in ys if fits_cand(sx, sy)]
    else:
        cands = [(sx, sy) for sx in xs for sy in ys]
    for sx, sy in cands:
        if True:
            cut = 0.0
            if sx is not None: cut += cut_length(GS, LineString([(sx, b[1]), (sx, b[3])]), GT)
            if sy is not None: cut += cut_length(GS, LineString([(b[0], sy), (b[2], sy)]), GT)
            if best is None or cut < best[0]: best = (cut, sx, sy)
    _, sx, sy = best
    BIG = 1e4
    def rect(key, ov):
        i, j = key
        x0 = -BIG if (sx is None or i == 0) else sx - ov; x1 = BIG if (sx is None or i == 1) else sx + ov
        y0 = -BIG if (sy is None or j == 0) else sy - ov; y1 = BIG if (sy is None or j == 1) else sy + ov
        return box(x0, y0, x1, y1)
    keys = [(i, j) for j in ((0, 1) if sy is not None else (0,)) for i in ((0, 1) if sx is not None else (0,))]
    def key_of(pt): return (0 if sx is None or pt.x < sx else 1, 0 if sy is None or pt.y < sy else 1)
    secs = {k: [] for k in keys}
    # motif clusters: small pieces that touch (petals + rim + eye + outline of one blossom, a bud + calyx + highlight)
    # travel together, decided by the cluster's centre, so a motif is never split between hoopings
    import shapely
    MOTIF = ("BL", "BD")                    # blossoms + buds cluster only with themselves (never chain into snow/bark)
    def is_motif(r): return tech.rule_for(r["grp"]).startswith(MOTIF)
    small, small_m = [], []
    for r in vis:
        for p in polys(r["geom"]):
            pb = p.bounds
            if max(pb[2]-pb[0], pb[3]-pb[1]) <= whole_max: (small_m if is_motif(r) else small).append(p)
    cl_o = polys(unary_union([p.buffer(0.6) for p in small])) if small else []
    cl_m = polys(unary_union([p.buffer(0.6) for p in small_m])) if small_m else []
    trees = {False: (shapely.STRtree(cl_o), cl_o), True: (shapely.STRtree(cl_m), cl_m)}
    def cluster_key(p, motif=False):
        c = Point((p.bounds[0]+p.bounds[2])/2, (p.bounds[1]+p.bounds[3])/2)
        tree, cl = trees[motif]
        for i in tree.query(p.representative_point()):
            q = cl[int(i)]
            if q.contains(p.representative_point()):
                qb = q.bounds
                if max(qb[2]-qb[0], qb[3]-qb[1]) <= whole_max * 1.2: c = q.centroid
                break
        return key_of(c)
    for r in vis:
        parts = {k: [] for k in keys}
        for p in polys(r["geom"]):
            pb = p.bounds
            if max(pb[2]-pb[0], pb[3]-pb[1]) <= whole_max:
                parts[cluster_key(p, is_motif(r))].append(p)
            else:
                ov = overlap if r["st"] in FILL_ST else 0.0
                for k in keys:
                    q = p.intersection(rect(k, ov))
                    if not q.is_empty and q.area > 0.5: parts[k] += polys(q)
        for k in keys:
            if parts[k]: secs[k].append(dict(r, geom=unary_union(parts[k])))
    # frame pass: anything a section can't hold (whole motifs overhanging the split) moves whole to the neighbour
    # that can hold it, else is cut at the frame limit with the overlap going to the neighbour (LESSONS B12)
    def allowed(key):
        i, j = key
        x0 = b[0] - ext if (sx is None or i == 0) else b[2] + ext - fw
        x1 = b[0] - ext + fw if (sx is not None and i == 0) else b[2] + ext
        y0 = b[1] - ext if (sy is None or j == 0) else b[3] + ext - fh
        y1 = b[1] - ext + fh if (sy is not None and j == 0) else b[3] + ext
        return box(x0, y0, x1, y1)
    AL = {k: allowed(k) for k in keys}
    moved = {k: [] for k in keys}
    for k in keys:
        keep = []
        for r in secs[k]:
            stay, out = [], []
            for p in polys(r["geom"]):
                if AL[k].buffer(0.01).contains(p): stay.append(p); continue
                home = next((k2 for k2 in keys if k2 != k and AL[k2].buffer(0.01).contains(p)), None)
                if home is not None: out.append((home, p)); continue
                inside = p.intersection(AL[k])
                if not inside.is_empty: stay += polys(inside)
                rest = p.difference(AL[k].buffer(-overlap))
                for k2 in keys:
                    if k2 == k: continue
                    q = rest.intersection(AL[k2])
                    if not q.is_empty and q.area > 0.3: out += [(k2, qq) for qq in polys(q)]
            if stay: keep.append(dict(r, geom=unary_union(stay)))
            for k2, q in out: moved[k2].append(dict(r, geom=q))
        secs[k] = keep
    for k in keys:
        secs[k] += moved[k]
    bbs = {k: bounds_of([r["geom"] for r in secs[k]]) for k in keys if secs[k]}
    def span(k, bb):        # section extent as the file is measured: art + outer crosses (ext) + the cross arm on each split line
        i, j = k
        x0 = b[0] - ext if (sx is None or i == 0) else min(bb[0], sx - arm)
        x1 = b[2] + ext if (sx is None or i == 1) else max(bb[2], sx + arm)
        y0 = b[1] - ext if (sy is None or j == 0) else min(bb[1], sy - arm)
        y1 = b[3] + ext if (sy is None or j == 1) else max(bb[3], sy + arm)
        return x1 - x0, y1 - y0
    fits = {k: (lambda w, h: w <= fw and h <= fh)(*span(k, bb)) for k, bb in bbs.items()}      # LESSONS B16
    return dict(sx=sx, sy=sy, secs=secs, bbs=bbs, fits=fits, cut=best[0], bounds=b)

def split_marks(sp, clear=5.0, ext=12.0):
    """Registration crosses on each section boundary, placed where the split line crosses bare fabric
    (>= clear mm from any art) so they stay visible for the next hooping. Returns {section_key: [pts]}."""
    import shapely
    geoms = [p for k in sp["secs"] for r in sp["secs"][k] for p in polys(r["geom"])]; tree = shapely.STRtree(geoms)
    b = sp["bounds"]
    def dist(pt):
        _, d = tree.query_nearest(Point(pt), return_distance=True); return float(d[0]) if len(d) else 1e9
    sx, sy = sp["sx"], sp["sy"]; out = {k: [] for k in sp["secs"]}
    def pick(seg_pts):
        ok = [p for p in seg_pts if dist(p) >= clear]
        if not ok: ok = [seg_pts[0], seg_pts[-1]]
        return [ok[0], ok[-1]] if len(ok) > 1 else ok
    def line(a, b_, n=120): return [(a[0] + (b_[0]-a[0])*t, a[1] + (b_[1]-a[1])*t) for t in np.linspace(0, 1, n)]
    if sx is not None:
        parts = [((sx, b[1]-ext), (sx, sy if sy is not None else b[3]+ext), 0)] + ([((sx, sy), (sx, b[3]+ext), 1)] if sy is not None else [])
        for a, b_, j in parts:
            m = pick(line(a, b_))
            for i in (0, 1): out[(i, j)] += m
    if sy is not None:
        parts = [((b[0]-ext, sy), (sx if sx is not None else b[2]+ext, sy), 0)] + ([((sx, sy), (b[2]+ext, sy), 1)] if sx is not None else [])
        for a, b_, i in parts:
            m = pick(line(a, b_))
            for j in (0, 1): out[(i, j)] += m
    return out

def clean_cached(name, vis, src_file):
    """clean_vis with an on-disk cache (invalidated when the source pickle changes)."""
    cp = f"clean_{name}.pkl"
    if os.path.exists(cp) and os.path.getmtime(cp) > os.path.getmtime(src_file):
        return pickle.load(open(cp, "rb"))
    cv = clean_vis(vis); pickle.dump(cv, open(cp, "wb")); return cv

# ------------------------------------------------------------------ v3: thread + stop consolidation
COL_MERGE = {"vermilion": "plum"}      # 16 -> 15 threads (fits a 15-needle head); red pine sews in plum red

def merge_colours(vis, m=None):
    m = COL_MERGE if m is None else m
    return [dict(r, col=m.get(r["col"], r["col"])) for r in vis]

def merge_stops(stops, clear=1.0):
    """Move each region to the earliest same-colour stop it can join without crossing anything sewn in between
    (nothing from the intermediate stops within `clear` mm). Empty stops disappear."""
    import shapely
    regs = []; owner = []
    for si, s in enumerate(stops):
        for r in s["regions"]: regs.append(r); owner.append(si)
    tree = shapely.STRtree([r["geom"] for r in regs])
    owner = np.array(owner); cols = [s["col"] for s in stops]
    first_of = {}
    for ri in range(len(regs)):
        j = owner[ri]
        g = regs[ri]["geom"].buffer(clear)
        hits = tree.query(g, predicate="intersects")
        ks = [owner[h] for h in hits if h != ri and owner[h] < j and cols[owner[h]] != cols[j]]
        kmax = max(ks) if ks else -1
        cand = [i for i in range(kmax + 1, j) if cols[i] == cols[j]]
        if cand: owner[ri] = cand[0]
    out = []
    for si, s in enumerate(stops):
        rs = [regs[ri] for ri in range(len(regs)) if owner[ri] == si]
        if rs: out.append(dict(s, regions=rs))
    return out
