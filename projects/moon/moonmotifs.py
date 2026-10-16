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
    regs.append(R("cperi", sil, "tatami", 0, "CL"))
    regs.append(R("cindigo", sil.intersection(box(x0 - 400, yb - base_h * 0.75, x1 + 400, yb)), "tatami", 0, "CL-shade"))
    prev = Polygon(); lines = []
    for li, ((cx, cy, r), disc) in enumerate(zip(lobes, discs)):
        top = disc.difference(Point(cx + r * 0.10, cy + r * 0.36).buffer(r * 0.99, 40))
        hl = disc.difference(Point(cx + r * 0.14, cy + r * 0.20).buffer(r * 0.975, 40)).buffer(-0.3).buffer(0.3)
        # each lobe repaints its own body over the lobes behind it, so the scallop edge reads
        regs.append(R("cperi", disc.difference(top).difference(box(x0 - 400, yb - base_h * 0.75, x1 + 400, yb)), "tatami", 0, "CL"))
        regs.append(R("clav", top, "tatami", 0, "CL-top"))
        if li < nback and r > 3.5 and not hl.is_empty and hl.area > 2.5: regs.append(R("cwhite", hl, "satin", "auto", "CL-hl"))
        arc = LineString([(cx + r * math.cos(t), cy + r * math.sin(t)) for t in np.linspace(math.pi * 1.0, math.pi * 2.0, 28)])
        if not prev.is_empty and r >= 4.5:
            inner = arc.intersection(prev.buffer(-0.9))
            if not inner.is_empty and inner.length > 3: lines.append(inner)
        prev = prev.union(disc)
    for ln in lines:
        for s_ in ([ln] if ln.geom_type == "LineString" else [g for g in getattr(ln, "geoms", []) if g.geom_type == "LineString"]):
            if s_.length > 3: regs.append(R("cindigo", s_.buffer(0.35, cap_style="round"), "bean", None, "CL-line"))
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
            if not g.is_empty: regs.append(R("clav", g, "satin", "auto", "CL-wisp"))
    return regs, sil

def wisp(x0, x1, y, w, rng=None):
    pts = [(x0 + (x1 - x0) * t, y + math.sin(t * math.pi) * -1.2) for t in np.linspace(0, 1, 14)]
    g, _ = sweep(taper(pts, w / 2, 0.55))
    return [R("clav", g, "satin", "auto", "CL-wisp")]

# ================================================================ moon
MARIA = [(-0.42, -0.30, 0.17), (-0.58, 0.05, 0.12), (-0.30, 0.28, 0.15), (0.05, -0.58, 0.11), (0.40, -0.25, 0.14),
         (0.52, 0.18, 0.12), (0.12, 0.02, 0.09), (0.28, 0.55, 0.10), (-0.12, -0.18, 0.08), (-0.05, 0.62, 0.08)]
def moon(cx, cy, Rm, rng):
    disc = Point(cx, cy).buffer(Rm, 180)
    regs = [R("mcream", disc, "tatami", 0, "MN")]
    hl = disc.intersection(Point(cx - 0.30 * Rm, cy - 0.30 * Rm).buffer(0.62 * Rm, 90))
    rim = disc.difference(Point(cx - 0.07 * Rm, cy - 0.07 * Rm).buffer(0.955 * Rm, 180))
    regs.append(R("mivory", hl, "tatami", 0, "MN-hl"))
    regs.append(R("mgold", rim.buffer(-0.2).buffer(0.2), "tatami", 0, "MN-rim"))
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
        det.append(R("mgold", blob.difference(core), "tatami", 30, "MN-mare"))
        if not core.is_empty: det.append(R("mtaupe", core, "tatami", 30, "MN-mare"))
    # craters: ring (run) + floor crescent (satin)
    for k in range(26):
        a = rng.uniform(0, 2 * math.pi); d = Rm * math.sqrt(rng.uniform(0.02, 0.78))
        x, y = cx + d * math.cos(a), cy + d * math.sin(a); rr = rng.uniform(2.6, 6.5)
        ring = Point(x, y).buffer(rr + 0.3).difference(Point(x, y).buffer(rr - 0.3))
        det.append(R("mtaupe", ring, "run", None, "MN-ring"))
        fl = Point(x, y).buffer(rr - 0.3).difference(Point(x - rr * 0.35, y - rr * 0.35).buffer(rr * 0.95))
        if fl.area > 2 and not fl.buffer(-0.6).is_empty: det.append(R("mgold", fl, "satin", "auto", "MN-crater"))
    # rays from one bright crater (lower right), as the mockup's star-shaped craters
    tx, ty = cx + 0.32 * Rm, cy + 0.36 * Rm
    for k in range(9):
        a = 2 * math.pi * k / 9 + 0.2; L = Rm * rng.uniform(0.12, 0.24)
        ray = LineString([(tx + 6 * math.cos(a), ty + 6 * math.sin(a)), (tx + (6 + L) * math.cos(a), ty + (6 + L) * math.sin(a))])
        det.append(R("mtaupe", ray.buffer(0.3).intersection(disc.buffer(-3)), "run", None, "MN-ring"))
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
    regs = [R("pgrey", body, "tatami", 90, "PL")]
    regs.append(R("pchar", strip(0.80, 1.0), "tatami", 90, "PL-shade"))
    regs.append(R("plight", strip(0.10, 0.30), "satin", "auto", "PL-hl"))
    # bands (rings) near the top and at the base
    for yy in (y0 + 6, y0 + 9.5, y1 - 22):
        regs.append(R("pchar", box(cx - w, yy - 0.9, cx + w, yy + 0.9).intersection(body), "satin", 90, "PL-band"))
    # step bolts alternating sides
    for k, yy in enumerate(np.arange(y0 + 34, y1 - 30, 21.0)):
        side = 1 if k % 2 else -1
        bx = cx + side * (w * 0.5 + 1.6)
        regs.append(R("pchar", box(bx - 2.2, yy - 0.9, bx + 2.2, yy + 0.9), "satin", 0, "PL-band"))
    # wood grain / texture lines
    for f in (0.42, 0.62):
        ln = LineString([(cx + s * wt * (f - 0.5), y0 + 14), (cx + s * w * (f - 0.5), y1 - 26)])
        regs.append(R("pchar", ln.buffer(0.35).intersection(body.buffer(-0.8)), "bean", None, "PL-line"))
    return regs, body

def crossarm(p0, p1, w=4.6):
    g = LineString([p0, p1]).buffer(w / 2, cap_style="flat")
    hl = LineString([p0, p1]).parallel_offset(w * 0.28, "left").buffer(w * 0.16, cap_style="flat").intersection(g)
    return [R("pgrey", g, "satin", "auto", "PL-arm"), R("plight", hl, "satin", "auto", "PL-hl")], g

def insulator(x, ybase, h=7.0, w=4.2):
    """pin insulator standing on a crossarm (base at ybase, growing up); returns regions + tip point"""
    regs = []
    for k in range(3):
        yy = ybase - h * (k + 0.5) / 3; ww = w * (1.0 - 0.18 * k)
        regs.append(R("plight", Point(x, yy).buffer(1).buffer(0).union(box(x - ww / 2, yy - h / 7, x + ww / 2, yy + h / 7)), "satin", 0, "PL-ins"))
    regs.append(R("pchar", box(x - 0.8, ybase - h * 0.15, x + 0.8, ybase + 0.4), "satin", 90, "PL-band"))
    return regs, (x, ybase - h)

def string_insulator(p0, p1, n=6, d=4.2):
    """suspension insulator string from p0 to p1: n discs"""
    regs = []
    v = np.array(p1) - np.array(p0); L = np.linalg.norm(v); u = v / L; nrm = np.array([-u[1], u[0]])
    rod = LineString([p0, p1]).buffer(0.55, cap_style="flat")
    regs.append(R("pchar", rod, "satin", "auto", "PL-band"))
    for k in range(n):
        c = np.array(p0) + u * L * (k + 0.5) / n
        e = Point(c).buffer(1.0)
        e = affinity.scale(e, L / n * 0.42, d / 2, origin=tuple(c))
        e = affinity.rotate(e, math.degrees(math.atan2(u[1], u[0])), origin=tuple(c))
        regs.append(R("plight", e, "satin", "auto", "PL-ins"))
    return regs

def can(x0, y0, w, h):
    """transformer can: body + lid + ribs + shade"""
    body = box(x0, y0 + 3, x0 + w, y0 + h).union(Point(x0 + w / 2, y0 + 3).buffer(w / 2, 24).intersection(box(x0, y0 + 1.4, x0 + w, y0 + 3)))
    regs = [R("pgrey", body, "tatami", 90, "PL-can")]
    regs.append(R("pchar", box(x0 + w * 0.78, y0 + 3, x0 + w, y0 + h).intersection(body), "tatami", 90, "PL-shade"))
    regs.append(R("plight", box(x0 - 0.8, y0 + 1.2, x0 + w + 0.8, y0 + 3.6), "satin", 0, "PL-hl"))
    regs.append(R("pchar", box(x0 - 0.5, y0 + h - 2.2, x0 + w + 0.5, y0 + h), "satin", 0, "PL-band"))
    for f in np.linspace(0.18, 0.62, 3):
        xx = x0 + w * f
        regs.append(R("pchar", LineString([(xx, y0 + 6), (xx, y0 + h - 4)]).buffer(0.35), "bean", None, "PL-line"))
    return regs, body

def bracket(p0, p1):
    return [R("pchar", LineString([p0, p1]).buffer(0.9, cap_style="round"), "satin", "auto", "PL-band")]

# ================================================================ wire
def wire_pts(p0, p1, sag, n=60):
    out = []
    for t in np.linspace(0, 1, n):
        out.append((p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t + 4 * sag * t * (1 - t)))
    return out

def wire(p0, p1, sag, w=0.8):
    pts = wire_pts(p0, p1, sag)
    return R("pgrey", LineString(pts).buffer(w / 2, cap_style="flat"), "bean", None, "WR"), LineString(pts)
