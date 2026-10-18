"""Moon jacket motifs (new for this product; proposed for the engine motif library — ENGINE_NOTES.md):
cloud (scalloped Japanese cloud with highlight caps, underside shadow, scallop lines, wisps), full moon (low-density
tonal body + maria + craters), utility pole (tapered pole, bands, step bolts, crossarms, insulators, transformer cans),
wire (sagging bean line). Units mm, y down. Every motif returns region dicts (motifs2.R) and named attachment points."""
import math, random
import numpy as np
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union
from shapely import affinity
from motifs2 import R
from motifs import taper, sweep

def _polys(g):
    if g.is_empty: return []
    if g.geom_type == "Polygon": return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]

def line_poly(pts, w):
    return LineString(pts).buffer(w / 2, cap_style="round", join_style="round")

# ================================================================ cloud
def cloud(x0, x1, yb, H, rng, tiers=None, tail=(1, 0.45), wisp_l=None, flip=False):
    """Japanese scalloped cloud (mockup style) from x0..x1 on base line yb, crown height H (mm).
    Envelope: a compact crown at ~30 % of the width (70 % if flip) tapering into long flat streaks toward the tail.
    Two scallop rows: back row (big lobes, crown) and a front row of small scale-like lobes; underside shadow band,
    light top + white highlight caps on each lobe, indigo scallop lines where a lobe overlaps the ones behind it,
    satin streak wisps off the tail end. `tiers` is accepted for older calls and ignored."""
    W = x1 - x0; uc = 0.7 if flip else 0.3; side = tail[0]
    env = lambda u: H * (0.16 + 0.84 * math.exp(-((u - uc) / 0.30) ** 2))
    regs = []
    cut = box(x0 - 400, yb - 400, x1 + 400, yb)
    rows = []
    for row, (fy, fr, step) in enumerate(((0.62, 0.50, 0.55), (0.30, 0.30, 0.62))):
        lob = []; u = 0.04
        while u < 0.96:
            h = env(u); r = max(3.6, h * fr * rng.uniform(0.9, 1.1))
            cx = x0 + W * u; cy = yb - h * fy + r * 0.15
            if h > H * 0.36 or (row == 1 and h > H * 0.26): lob.append((cx, cy, r))
            u += max(0.025, (r * step * 2.0) / W) * rng.uniform(0.9, 1.15)
        rows.append(lob)
    base_h = H * 0.17
    allx = [cx - r for cx, cy, r in rows[0] + rows[1]] + [cx + r for cx, cy, r in rows[0] + rows[1]]
    bx0, bx1 = min(allx) - base_h * 0.5, max(allx) + base_h * 0.5
    base = Polygon([(bx0 - base_h, yb), (bx0 + base_h * 0.5, yb - base_h), (bx1 - base_h * 0.5, yb - base_h), (bx1 + base_h, yb)])
    nback = len(rows[0])
    lobes = sorted(rows[0], key=lambda l: -l[2]) + rows[1]
    discs = [Point(cx, cy).buffer(r, 40).intersection(cut) for cx, cy, r in lobes]
    sil = unary_union(discs + [base]).buffer(0.3).buffer(-0.3)
    regs.append(R("c3", sil, "tatami", 0, "CL"))
    regs.append(R("c5", sil.intersection(box(x0 - 400, yb - base_h * 0.75, x1 + 400, yb)), "tatami", 0, "CL-shade"))
    prev = Polygon(); lines = []
    for li, ((cx, cy, r), disc) in enumerate(zip(lobes, discs)):
        top = disc.difference(Point(cx + r * 0.10, cy + r * 0.36).buffer(r * 0.99, 40))
        hl = disc.difference(Point(cx + r * 0.14, cy + r * 0.20).buffer(r * 0.975, 40)).buffer(-0.3).buffer(0.3)
        # each lobe repaints its own body over the lobes behind it, so the scallop edge reads
        regs.append(R("c3", disc.difference(top).difference(box(x0 - 400, yb - base_h * 0.75, x1 + 400, yb)), "tatami", 0, "CL"))
        regs.append(R("c2", top, "tatami", 0, "CL-top"))
        if li < nback and r > 3.5 and not hl.is_empty and hl.area > 2.5: regs.append(R("c1", hl, "satin", "auto", "CL-hl"))
        arc = LineString([(cx + r * math.cos(t), cy + r * math.sin(t)) for t in np.linspace(math.pi * 1.0, math.pi * 2.0, 28)])
        if not prev.is_empty and r >= 4.5:
            inner = arc.intersection(prev.buffer(-0.9))
            if not inner.is_empty and inner.length > 3: lines.append(inner)
        prev = prev.union(disc)
    for ln in lines:
        for s_ in ([ln] if ln.geom_type == "LineString" else [g for g in getattr(ln, "geoms", []) if g.geom_type == "LineString"]):
            if s_.length > 3: regs.append(R("c5", s_.buffer(0.35, cap_style="round"), "bean", None, "CL-line"))
    # streak wisps off the tail end
    frac = tail[1]
    if frac > 0:
        L = wisp_l or W * frac
        for k, (dy, w0) in enumerate(((0.10, 0.032), (0.26, 0.024), (0.0, 0.02))):
            yy = yb - H * dy
            if side > 0: xa, xb = bx1 - W * 0.08 * (k + 1), bx1 + L * (1.0 - 0.3 * k)
            else:        xa, xb = bx0 + W * 0.08 * (k + 1), bx0 - L * (1.0 - 0.3 * k)
            pts = [(xa + (xb - xa) * t, yy - math.sin(t * math.pi) * 0.6) for t in np.linspace(0, 1, 14)]
            g, _ = sweep(taper(pts, max(0.75, H * w0), 0.5))
            g = g.difference(sil)
            if not g.is_empty: regs.append(R("c2", g, "satin", "auto", "CL-wisp"))
    return regs, sil

def wisp(x0, x1, y, w, rng=None):
    pts = [(x0 + (x1 - x0) * t, y + math.sin(t * math.pi) * -1.2) for t in np.linspace(0, 1, 14)]
    g, _ = sweep(taper(pts, w / 2, 0.55))
    return [R("c2", g, "satin", "auto", "CL-wisp")]

# ================================================================ moon
MARIA = [(-0.42, -0.30, 0.17), (-0.58, 0.05, 0.12), (-0.30, 0.28, 0.15), (0.05, -0.58, 0.11), (0.40, -0.25, 0.14),
         (0.52, 0.18, 0.12), (0.12, 0.02, 0.09), (0.28, 0.55, 0.10), (-0.12, -0.18, 0.08), (-0.05, 0.62, 0.08)]
def moon(cx, cy, Rm, rng):
    disc = Point(cx, cy).buffer(Rm, 180)
    regs = [R("m2", disc, "tatami", 0, "MN")]
    hl = disc.intersection(Point(cx - 0.30 * Rm, cy - 0.30 * Rm).buffer(0.62 * Rm, 90))
    rim = disc.difference(Point(cx - 0.07 * Rm, cy - 0.07 * Rm).buffer(0.955 * Rm, 180))
    regs.append(R("m1", hl, "tatami", 0, "MN-hl"))
    regs.append(R("m3", rim.buffer(-0.2).buffer(0.2), "tatami", 0, "MN-rim"))
    det = []
    for (u, v, s) in MARIA:
        mx, my, mr = cx + u * Rm, cy + v * Rm, s * Rm
        pts = []; ph = rng.uniform(0, 6)
        for k in range(28):
            t = 2 * math.pi * k / 28
            rr = mr * (1 + 0.12 * math.sin(3 * t + ph) + 0.07 * math.sin(5 * t + ph * 2))
            pts.append((mx + rr * math.cos(t), my + rr * 0.85 * math.sin(t)))
        blob = Polygon(pts).buffer(0).buffer(1.2).buffer(-1.2).intersection(disc.buffer(-4))
        # break each mare into two tones: taupe core + pale-gold halo -> soft, no hard dome
        core = blob.buffer(-mr * 0.45)
        det.append(R("m3", blob.difference(core), "tatami", 30, "MN-mare"))
        if not core.is_empty: det.append(R("m5", core, "tatami", 30, "MN-mare"))
    # craters: ring (run) + floor crescent (satin)
    for k in range(26):
        a = rng.uniform(0, 2 * math.pi); d = Rm * math.sqrt(rng.uniform(0.02, 0.78))
        x, y = cx + d * math.cos(a), cy + d * math.sin(a); rr = rng.uniform(2.6, 6.5)
        ring = Point(x, y).buffer(rr + 0.3).difference(Point(x, y).buffer(rr - 0.3))
        det.append(R("m5", ring, "run", None, "MN-ring"))
        fl = Point(x, y).buffer(rr - 0.3).difference(Point(x - rr * 0.35, y - rr * 0.35).buffer(rr * 0.95))
        if fl.area > 2 and not fl.buffer(-0.6).is_empty: det.append(R("m3", fl, "satin", "auto", "MN-crater"))
    # rays from one bright crater (lower right), as the mockup's star-shaped craters
    tx, ty = cx + 0.32 * Rm, cy + 0.36 * Rm
    for k in range(9):
        a = 2 * math.pi * k / 9 + 0.2; L = Rm * rng.uniform(0.12, 0.24)
        ray = LineString([(tx + 6 * math.cos(a), ty + 6 * math.sin(a)), (tx + (6 + L) * math.cos(a), ty + (6 + L) * math.sin(a))])
        det.append(R("m5", ray.buffer(0.3).intersection(disc.buffer(-3)), "run", None, "MN-ring"))
    return regs, det, disc

# ================================================================ utility pole
def pole(cx, y0, y1, w, rng, mirror=False):
    """tapered pole cx, from top y0 to bottom y1, width w at the bottom (top 82 %). Returns (regions, body poly)."""
    wt = w * 0.82
    body = Polygon([(cx - wt / 2, y0), (cx + wt / 2, y0), (cx + w / 2, y1), (cx - w / 2, y1)])
    top = Point(cx, y0).buffer(wt / 2, 24).intersection(box(cx - w, y0 - w, cx + w, y0))
    body = body.union(affinity.scale(top, 1, 0.35, origin=(cx, y0)))
    s = -1 if mirror else 1
    def strip(f0, f1):
        pts = [(cx + s * wt * (f0 - 0.5), y0), (cx + s * wt * (f1 - 0.5), y0), (cx + s * w * (f1 - 0.5), y1), (cx + s * w * (f0 - 0.5), y1)]
        return Polygon(pts).buffer(0).intersection(body)
    regs = [R("p2", body, "tatami", 90, "PL")]
    regs.append(R("p4", strip(0.80, 1.0), "tatami", 90, "PL-shade"))
    regs.append(R("p1", strip(0.10, 0.30), "satin", "auto", "PL-hl"))
    # bands (rings) near the top and at the base
    for yy in (y0 + 6, y0 + 9.5, y1 - 22):
        regs.append(R("p4", box(cx - w, yy - 0.9, cx + w, yy + 0.9).intersection(body), "satin", 90, "PL-band"))
    # step bolts alternating sides
    for k, yy in enumerate(np.arange(y0 + 34, y1 - 30, 21.0)):
        side = 1 if k % 2 else -1
        bx = cx + side * (w * 0.5 + 1.6)
        regs.append(R("p4", box(bx - 2.2, yy - 0.9, bx + 2.2, yy + 0.9), "satin", 0, "PL-band"))
    # wood grain / texture lines
    for f in (0.42, 0.62):
        ln = LineString([(cx + s * wt * (f - 0.5), y0 + 14), (cx + s * w * (f - 0.5), y1 - 26)])
        regs.append(R("p4", ln.buffer(0.35).intersection(body.buffer(-0.8)), "bean", None, "PL-line"))
    return regs, body

def crossarm(p0, p1, w=4.6):
    g = LineString([p0, p1]).buffer(w / 2, cap_style="flat")
    hl = LineString([p0, p1]).parallel_offset(w * 0.28, "left").buffer(w * 0.16, cap_style="flat").intersection(g)
    return [R("p2", g, "satin", "auto", "PL-arm"), R("p1", hl, "satin", "auto", "PL-hl")], g

def insulator(x, ybase, h=7.0, w=4.2):
    """pin insulator standing on a crossarm (base at ybase, growing up); returns regions + tip point"""
    regs = []
    for k in range(3):
        yy = ybase - h * (k + 0.5) / 3; ww = w * (1.0 - 0.18 * k)
        regs.append(R("p1", Point(x, yy).buffer(1).buffer(0).union(box(x - ww / 2, yy - h / 7, x + ww / 2, yy + h / 7)), "satin", 0, "PL-ins"))
    regs.append(R("p4", box(x - 0.8, ybase - h * 0.15, x + 0.8, ybase + 0.4), "satin", 90, "PL-band"))
    return regs, (x, ybase - h)

def string_insulator(p0, p1, n=6, d=4.2):
    """suspension insulator string from p0 to p1: n discs"""
    regs = []
    v = np.array(p1) - np.array(p0); L = np.linalg.norm(v); u = v / L; nrm = np.array([-u[1], u[0]])
    rod = LineString([p0, p1]).buffer(0.55, cap_style="flat")
    regs.append(R("p4", rod, "satin", "auto", "PL-band"))
    for k in range(n):
        c = np.array(p0) + u * L * (k + 0.5) / n
        e = Point(c).buffer(1.0)
        e = affinity.scale(e, L / n * 0.42, d / 2, origin=tuple(c))
        e = affinity.rotate(e, math.degrees(math.atan2(u[1], u[0])), origin=tuple(c))
        regs.append(R("p1", e, "satin", "auto", "PL-ins"))
    return regs

def can(x0, y0, w, h):
    """transformer can: body + lid + ribs + shade"""
    body = box(x0, y0 + 3, x0 + w, y0 + h).union(Point(x0 + w / 2, y0 + 3).buffer(w / 2, 24).intersection(box(x0, y0 + 1.4, x0 + w, y0 + 3)))
    regs = [R("p2", body, "tatami", 90, "PL-can")]
    regs.append(R("p4", box(x0 + w * 0.78, y0 + 3, x0 + w, y0 + h).intersection(body), "tatami", 90, "PL-shade"))
    regs.append(R("p1", box(x0 - 0.8, y0 + 1.2, x0 + w + 0.8, y0 + 3.6), "satin", 0, "PL-hl"))
    regs.append(R("p4", box(x0 - 0.5, y0 + h - 2.2, x0 + w + 0.5, y0 + h), "satin", 0, "PL-band"))
    for f in np.linspace(0.18, 0.62, 3):
        xx = x0 + w * f
        regs.append(R("p4", LineString([(xx, y0 + 6), (xx, y0 + h - 4)]).buffer(0.35), "bean", None, "PL-line"))
    return regs, body

def bracket(p0, p1):
    return [R("p4", LineString([p0, p1]).buffer(0.9, cap_style="round"), "satin", "auto", "PL-band")]

# ================================================================ wire
def wire_pts(p0, p1, sag, n=60):
    out = []
    for t in np.linspace(0, 1, n):
        out.append((p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t + 4 * sag * t * (1 - t)))
    return out

def wire(p0, p1, sag, w=0.8):
    pts = wire_pts(p0, p1, sag)
    return R("p2", LineString(pts).buffer(w / 2, cap_style="flat"), "bean", None, "WR"), LineString(pts)

# ================================================================ Rev B: seigaiha cloud texture inside a traced silhouette
def cloud_texture(sil, ppm=4.0, scale_r=3.8, rng_seed=0):
    """Fill a cloud silhouette (mm) the way the close-ups are sewn: horizontal tone bands by height inside each column
    (white-pink caps along the top contour, lavender, periwinkle, indigo underside), and rows of overlapping fish-scale
    arcs (seigaiha) sewn as indigo/lavender bean lines on top — every lobe reads as a fan of curved scallop rows."""
    from shapely import contains_xy
    from skimage import measure as _ms
    if sil.is_empty: return []
    x0, y0, x1, y1 = sil.bounds; W = int((x1 - x0) * ppm) + 3; H = int((y1 - y0) * ppm) + 3
    yy, xx = np.mgrid[0:H, 0:W]; X = x0 + (xx + 0.5) / ppm; Y = y0 + (yy + 0.5) / ppm
    m = contains_xy(sil, X, Y)
    from scipy import ndimage as ndi
    # depth below the top contour (per column) and distance to the upper boundary
    top = np.where(m.any(0), m.argmax(0), H); bot = np.where(m.any(0), H - 1 - m[::-1].argmax(0), 0)
    hgt = np.maximum(bot - top, 1)
    t = (yy - top[None, :]) / hgt[None, :]
    up = ndi.distance_transform_edt(m) / ppm
    # boundary pixels whose outward normal points up = the lit tops of the lobes
    gy = ndi.sobel(m.astype(float), 0)
    lit = ndi.binary_dilation(gy > 0.5, iterations=int(2.2 * ppm)) & m & (up < 2.6)
    lab = np.full(m.shape, -1)
    lab[m] = 3                                   # periwinkle
    lab[m & (t < 0.45)] = 2                      # lavender band
    lab[m & (t > 0.72)] = 5                      # indigo underside
    lab[lit & (t < 0.6)] = 1                     # white-pink caps on lit lobe tops
    lab = ndi.median_filter(lab, size=5)
    names = {1: "c1", 2: "c2", 3: "c3", 5: "c5"}; codes = {1: "CL-hl", 2: "CL-top", 3: "CL", 5: "CL-shade"}
    regs = []
    for v, n in names.items():
        mm_ = (lab == v) & m
        if not mm_.any(): continue
        g = Polygon()
        for cnt in _ms.find_contours(np.pad(mm_, 1).astype(float), 0.5):
            if len(cnt) < 4: continue
            p = Polygon([(x0 + (c - 1 + 0.5) / ppm, y0 + (r - 1 + 0.5) / ppm) for r, c in cnt]).buffer(0)
            g = g.symmetric_difference(p)
        g = g.buffer(0.2).buffer(-0.2).intersection(sil)
        for p in _polys(g):
            if p.area < 0.8: continue
            w = 2 * p.area / max(p.length, 1e-6)
            regs.append(R(n, p, "satin" if w < 2.6 else "tatami", "auto" if w < 2.6 else 0, codes[v]))
    # seigaiha scale rows: arcs (upper half circles) on a staggered grid, clipped to the silhouette minus the caps
    rs = scale_r; dx = 2 * rs * 0.92; dy = rs * 0.95
    inner = sil.buffer(-0.8)
    caps = unary_union([r["geom"] for r in regs if r["col"] == "c1"]) if regs else Polygon()
    lines = []
    k = 0
    for yc in np.arange(y0 + rs, y1 + rs, dy):
        off = (k % 2) * dx / 2; k += 1
        for xc in np.arange(x0 - dx + off, x1 + dx, dx):
            arc = LineString([(xc + rs * math.cos(a), yc - rs * math.sin(a)) for a in np.linspace(0.12 * math.pi, 0.88 * math.pi, 9)])
            seg = arc.intersection(inner).difference(caps.buffer(0.3))
            for s in ([seg] if seg.geom_type == "LineString" else [g for g in getattr(seg, "geoms", []) if g.geom_type == "LineString"]):
                if s.length > 2.0: lines.append(s)
    if lines:
        L = unary_union([s.buffer(0.35, cap_style="round") for s in lines])
        regs.append(R("c5", L, "bean", None, "CL-line"))
    return regs

# ================================================================ Rev C: contour-following cloud (LESSONS A13)
def cloud_contour(sil, row=2.6, scale=4.2, ppm=4.0):
    """Cloud from a traced silhouette, built like the close-ups are sewn:
    tone bands top -> bottom (white-pink cap along every upward-facing edge, lavender, periwinkle, indigo underside);
    scallop rows = inward offsets of the silhouette every `row` mm, each offset's upward-facing parts cut into arcs of
    ~`scale` mm that bulge outward (fish scales that follow the cloud's own contour, not a global grid)."""
    from shapely.geometry import MultiPolygon
    from shapely import contains_xy
    from scipy import ndimage as ndi
    from skimage import measure as _ms
    if sil.is_empty: return []
    x0, y0, x1, y1 = sil.bounds; W = int((x1 - x0) * ppm) + 3; H = int((y1 - y0) * ppm) + 3
    yy, xx = np.mgrid[0:H, 0:W]; X = x0 + (xx + 0.5) / ppm; Y = y0 + (yy + 0.5) / ppm
    m = contains_xy(sil, X, Y)
    top = np.where(m.any(0), m.argmax(0), H); bot = np.where(m.any(0), H - 1 - m[::-1].argmax(0), 0)
    t = (yy - top[None, :]) / np.maximum(bot - top, 1)[None, :]
    dist = ndi.distance_transform_edt(m) / ppm
    gy = ndi.gaussian_filter(m.astype(float), 2.0); up = np.gradient(gy, axis=0) > 0.02      # boundary facing up
    up = ndi.binary_dilation(up, iterations=int(2.0 * ppm))
    lab = np.zeros(m.shape, int)
    lab[m] = 3
    lab[m & (t < 0.42)] = 2
    lab[m & (t > 0.74)] = 5
    lab[m & up & (dist < 2.2) & (t < 0.75)] = 1
    lab = ndi.median_filter(lab, size=5)
    names = {1: ("c1", "CL-hl"), 2: ("c2", "CL-top"), 3: ("c3", "CL"), 5: ("c5", "CL-shade")}
    regs = []
    for v, (n, code) in names.items():
        mm_ = (lab == v) & m
        if not mm_.any(): continue
        g = Polygon()
        for cnt in _ms.find_contours(np.pad(mm_, 1).astype(float), 0.5):
            if len(cnt) < 4: continue
            g = g.symmetric_difference(Polygon([(x0 + (c - 0.5) / ppm, y0 + (r - 0.5) / ppm) for r, c in cnt]).buffer(0))
        g = g.buffer(0.35).intersection(sil)          # tones overlap 0.35 mm: no fabric between them
        for p in _polys(g):
            if p.area < 0.8: continue
            w = 2 * p.area / max(p.length, 1e-6)
            regs.append(R(n, p, "satin" if w < 2.6 else "tatami", "auto" if w < 2.6 else 0, code))
    # contour scallop rows
    arcs = []
    k = 1
    while True:
        inner = sil.buffer(-row * k + 0.6, join_style=1)
        if inner.is_empty or inner.area < 4: break
        for p in _polys(inner):
            from shapely.geometry.polygon import orient as _orient
            ring = LineString(_orient(p, 1.0).exterior.coords)
            L = ring.length; n = max(3, int(L / scale))
            pts = [ring.interpolate(L * i / n) for i in range(n + 1)]
            for a_, b_ in zip(pts, pts[1:]):
                mx, my = (a_.x + b_.x) / 2, (a_.y + b_.y) / 2
                dx, dy = b_.x - a_.x, b_.y - a_.y; dl = math.hypot(dx, dy) or 1
                nx, ny = dy / dl, -dx / dl                     # outward normal (exterior is CCW after buffer)
                if not sil.contains(Point(mx + nx * 0.6, my + ny * 0.6)) and sil.contains(Point(mx - nx * 0.6, my - ny * 0.6)): pass
                if ny > -0.25: nx, ny = 0.0, -1.0              # down/side-facing rows: scales still bulge up (close-up)
                h = dl * 0.32
                arc = [(a_.x + dx * s_ + nx * h * math.sin(math.pi * s_), a_.y + dy * s_ + ny * h * math.sin(math.pi * s_)) for s_ in np.linspace(0, 1, 7)]
                arcs.append(LineString(arc))
        k += 1
    # lobes: peaks of the top contour -> one dome per peak; its rim inside the cloud = an indigo shading arc between lobes
    lobes = []
    xs = np.arange(x0, x1, 0.5); tops = []
    for x in xs:
        seg = sil.intersection(LineString([(x, y0 - 1), (x, y1 + 1)])); tops.append(seg.bounds[1] if not seg.is_empty else np.nan)
    tops = np.array(tops)
    for i in range(3, len(xs) - 3):
        if np.isnan(tops[i]): continue
        w = tops[max(0, i - 12):i + 13]
        if tops[i] <= np.nanmin(w) + 1e-6:
            lobes.append((xs[i], tops[i]))
    lob_lines = []
    for lx, ly in lobes:
        seg = sil.intersection(LineString([(lx, ly - 1), (lx, y1 + 1)])); h = seg.bounds[3] - ly if not seg.is_empty else 0
        rr = max(3.0, min(14.0, h * 0.45)); cx_, cy_ = lx, ly + rr
        arc = LineString([(cx_ + rr * math.cos(a), cy_ + rr * math.sin(a)) for a in np.linspace(1.08 * math.pi, 1.92 * math.pi, 16)])   # dome rim (upper arc)
        lob_lines.append(arc)
    if arcs or lob_lines:
        inner = sil.buffer(-0.8)
        tone_of = lambda pt: {1: "c1", 2: "c1", 3: "c2", 5: "c3"}.get(int(lab[min(H - 1, max(0, int((pt.y - y0) * ppm))), min(W - 1, max(0, int((pt.x - x0) * ppm)))]), "c2")
        crest = {}
        for a in arcs:
            crest.setdefault(tone_of(a.interpolate(0.5, normalized=True)), []).append(a.buffer(0.45, cap_style="round"))
        for n, gs in crest.items():
            g = unary_union(gs).intersection(inner)
            for p in _polys(g):
                if p.area > 0.5: regs.append(R(n, p, "satin", "auto", "CL-top"))
        shade = unary_union([affinity.translate(a, 0, 1.0).buffer(0.3, cap_style="round") for a in arcs] +
                            [l.buffer(0.35, cap_style="round") for l in lob_lines]).intersection(inner)
        if not shade.is_empty: regs.append(R("c5", shade, "bean", None, "CL-line"))
    return regs

def smooth_sil(g, r=2.5, keep_frac=0.02):
    """domed cumulus silhouette: close + open by r, drop tiny detached bits, keep tails attached"""
    g = g.buffer(r).buffer(-2 * r).buffer(r).simplify(0.25)
    ps = _polys(g)
    if not ps: return Polygon()
    big = max(p.area for p in ps)
    return unary_union([Polygon(p.exterior) for p in ps if p.area >= keep_frac * big]).buffer(0)

def profile_sil(g, step=0.5, s_top=1.2, s_bot=3.5, min_h=0.9):
    """domed cumulus from a traced (jagged, holey) mask: per column top + bottom edge, top smoothed lightly (keeps the
    lobes), bottom smoothed strongly (flat base), tails kept where the column is at least min_h tall."""
    from scipy import ndimage as ndi
    out = []
    for p in _polys(g.buffer(0)):
        x0, y0, x1, y1 = p.bounds
        xs = np.arange(x0, x1 + step, step); top = []; bot = []
        for x in xs:
            seg = p.intersection(LineString([(x, y0 - 1), (x, y1 + 1)]))
            if seg.is_empty: top.append(np.nan); bot.append(np.nan); continue
            b = seg.bounds; top.append(b[1]); bot.append(b[3])
        top = np.array(top); bot = np.array(bot); ok = ~np.isnan(top)
        if ok.sum() < 6: continue
        top = np.interp(xs, xs[ok], top[ok]); bot = np.interp(xs, xs[ok], bot[ok])
        top = ndi.gaussian_filter1d(top, s_top / step); bot = ndi.gaussian_filter1d(bot, s_bot / step)
        keep = (bot - top) >= min_h
        if keep.sum() < 4: continue
        i0, i1 = np.argmax(keep), len(keep) - np.argmax(keep[::-1]) - 1
        xs_, t_, b_ = xs[i0:i1 + 1], top[i0:i1 + 1], np.maximum(bot[i0:i1 + 1], top[i0:i1 + 1] + min_h)
        poly = Polygon(list(zip(xs_, t_)) + list(zip(xs_[::-1], b_[::-1]))).buffer(0)
        if not poly.is_empty: out.append(poly)
    return unary_union(out).buffer(0.3).buffer(-0.3) if out else Polygon()
