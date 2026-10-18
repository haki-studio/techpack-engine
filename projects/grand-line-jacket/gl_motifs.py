"""New motifs for the Grand Line front scene (candidates for the engine motif library — see ENGINE_NOTES.md).
Units mm, y down. Every function returns Region dicts (col, geom, st, ang, grp) like motifs2, plus optional keys:
  ko      False = overlay line sewn on top of its parent, does not knock out what is under it
  kob     knockout buffer: regions below are cut back this far (dark fabric line between lobes)
  unit    id of the motif it belongs to (per-size clipping drops whole small motifs instead of cutting them)"""
import math, random
import numpy as np
from shapely.geometry import Point, Polygon, LineString, MultiPolygon, box
from shapely.ops import unary_union
from shapely import affinity

def R(col, geom, st, ang, grp, **kw):
    d = dict(col=col, geom=geom, st=st, ang=ang, grp=grp); d.update(kw); return d

def polys(g):
    if g is None or g.is_empty: return []
    if g.geom_type == "Polygon": return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]

def smooth(g, d=0.35):
    return g.buffer(d, join_style="round").buffer(-2*d, join_style="round").buffer(d, join_style="round")

# ---------------------------------------------------------------- cloud lobes ("scale packing")
TONES = {   # lobe class -> (body, rim, shade, scale-dash colour). No dark outline / shadow thread (review C2).
    "cream": ("gl_cream", "gl_pale", "gl_sand", "gl_sand"),
    "sand":  ("gl_sand", "gl_cream", "gl_sage", "gl_sage"),
    "sage":  ("gl_sage", "gl_sagelt", "gl_slate", "gl_slate"),   # sage florets with pale highlight rims (close-ups)
    "slate": ("gl_slate", "gl_sagelt", "gl_sage", "gl_sage"),
}
EX, EY = 1.16, 0.9                                   # lobes a little wider than tall (cumulus domes)
def ell(cx, cy, r): return affinity.scale(Point(cx, cy).buffer(1.0, quad_segs=24), r*EX, r*EY, origin=(cx, cy))

def pack_lobes(C, R0, rng, rjit=0.22, dy=0.62, dx=1.18, inset=0.5, rmin=2.6):
    """cumulus as overlapping discs whose union follows the outline C. Lower discs sit in front (higher z)."""
    b = C.bounds; lobes = []
    y = b[3] - 0.45*R0; row = 0
    while y > b[1] - 0.2*R0:
        x = b[0] + (0.6*R0 if row % 2 else 0.0) + rng.uniform(-0.2, 0.2)*R0
        while x < b[2] + 0.3*R0:
            r = R0 * rng.uniform(1 - rjit, 1 + rjit)
            cx, cy = x + rng.uniform(-0.18, 0.18)*R0, y + rng.uniform(-0.15, 0.15)*R0
            inner = C.buffer(-inset*r)
            if not inner.is_empty and inner.contains(Point(cx, cy)):
                lobes.append([cx, cy, r])
            x += dx*R0
        y -= dy*R0; row += 1
    # fill what the rows missed (from behind)
    for _ in range(3):
        U = unary_union([Point(cx, cy).buffer(r) for cx, cy, r in lobes]) if lobes else Polygon()
        miss = C.difference(U.buffer(0.3))
        added = 0
        for p in sorted(polys(miss), key=lambda p: -p.area):
            if p.area < (0.45*R0)**2: continue
            c = p.representative_point(); r = max(rmin, min(R0, math.sqrt(p.area/math.pi)*1.25))
            lobes.append([c.x, c.y - 0.15*r, r]); added += 1
        if not added: break
    lobes = [l for l in lobes if l[2] >= rmin]
    for l in lobes: l.append(l[1] + rng.uniform(-0.25, 0.25)*R0)       # z: lower = in front
    return lobes

def lobe_regions(lobes, tone_of, flat_y=None, grp="CL", unit=None, base_bottom=True, gap=0.0, scale=False, fan=False):
    """Mockup-style cumulus: each lobe's visible dome (the lobes in front cut it back by a `gap` of bare fabric, the dark
    line between lobes in the mockup) -> lit rim along the top, body, darker shade band where the front lobe overlaps it,
    and rows of short dark scale dashes following the dome (the mockup's stitch texture), sewn on top (overlay)."""
    discs = []
    for cx, cy, r, z in lobes:
        d = ell(cx, cy, r)
        if flat_y is not None: d = d.intersection(box(cx - 2*r, cy - 2*r, cx + 2*r, flat_y))
        discs.append((z, cx, cy, r, d))
    discs.sort(key=lambda t: -t[0])                     # front first
    regs = []; front = Polygon()
    for z, cx, cy, r, d in discs:
        V = (d.difference(front.buffer(gap) if gap else front) if not front.is_empty else d).buffer(0)
        V = smooth(V, 0.3)
        if V.area < 2.5:
            front = front.union(d); continue
        tone = tone_of(V, (cx, cy, r))
        bcol, rcol, scol, dcol = TONES[tone]
        wr = min(3.0, max(1.2, 0.3*r)); ws = min(1.8, max(0.9, 0.17*r))
        shade = V.intersection(front.buffer(gap + ws)) if not front.is_empty else Polygon()   # darker base where the front lobe sits
        if base_bottom:
            shade = shade.union(V.intersection(box(cx - 2*r, cy + max(0.45*r, 0.9*r*EY - ws), cx + 2*r, cy + 2*r)))
        shade = smooth(shade.intersection(V), 0.4) if r >= 3.5 else Polygon()
        rim = V.intersection(ell(cx, cy, r).difference(ell(cx, cy + 0.35*wr, r - wr))).intersection(box(cx - 2*r, cy - 2*r, cx + 2*r, cy + 0.2*r))
        rim = smooth(rim.difference(shade.buffer(0.2)), 0.45) if r >= 4.5 else Polygon()
        body = V.difference(rim).difference(shade).buffer(0)
        bc = body.buffer(-0.42).buffer(0.42).intersection(body); sl = body.difference(bc)
        if not sl.is_empty and sl.area > 0.01 and not shade.is_empty:
            body = bc; shade = shade.union(sl).buffer(0)
        jit = ((cx * 7.31 + cy * 3.17) % 40.0) - 20.0
        fa = ("radial", cx, cy + 0.75*r)                       # Rev D: short tatami fanned from the lobe base (follows the dome)
        for col, g, gg, sb, an in ((rcol, rim, grp + "-rim", "rim", fa if fan else jit * 0.5), (bcol, body, grp, "body", fa if fan else jit),
                                   (scol, shade, grp + "-shade", "shade", fa if fan else -jit * 0.6)):
            if not g.is_empty: regs.append(R(col, g, "tatami", an, gg, unit=unit, sub=sb))
        if scale and r >= 5.0 and not body.is_empty:          # scale rows: dashed arcs inside the body
            inner = body.buffer(-0.7)
            for k, fr in enumerate((0.78, 0.55) if r >= 7 else (0.68,)):
                rr = r*fr; n = max(6, int(math.pi*rr*1.2/1.0)); off = 0.5 if k % 2 else 0.0
                L, gp = 2.6, 1.7; s_ = off*(L + gp); arc = []
                pts = [(cx + rr*EX*math.cos(math.radians(a)), cy - rr*EY*math.sin(math.radians(a)) + 0.25*r) for a in np.linspace(12, 168, n)]
                line = LineString(pts); tot = line.length
                while s_ < tot - 0.8:
                    seg = substring_(line, s_, min(tot, s_ + L))
                    g = seg.buffer(0.33, cap_style="round").intersection(inner)
                    if not g.is_empty and g.area > 0.9: regs.append(R(dcol, g, "run", None, grp + "-scale", unit=unit, sub="scale", ko=False))
                    s_ += L + gp
        front = front.union(d)
    return regs, front

def substring_(line, a, b):
    from shapely.ops import substring
    return substring(line, a, b)

# ---------------------------------------------------------------- stars
def taper_arm(cx, cy, ang, L, w0, w1=0.9, r0=0.0):
    a = math.radians(ang); ux, uy = math.cos(a), math.sin(a); nx, ny = -uy, ux
    p0 = (cx + ux*r0, cy + uy*r0); p1 = (cx + ux*L, cy + uy*L)
    pts = [(p0[0] + nx*w0/2, p0[1] + ny*w0/2), (p1[0] + nx*w1/2, p1[1] + ny*w1/2),
           (p1[0] - nx*w1/2, p1[1] - ny*w1/2), (p0[0] - nx*w0/2, p0[1] - ny*w0/2)]
    return Polygon(pts).union(Point(*p1).buffer(w1/2, quad_segs=6))

def star(cx, cy, Lv, Lh, w0, kind, unit, rot=0.0):
    """4-point sparkle. kind: 'dot' | 'cross' | 'sparkle' | 'big'"""
    regs = []
    if kind == "dot":
        return [R("gl_gold", Point(cx, cy).buffer(max(0.75, Lv/2), quad_segs=10), "satin", "auto", "DOT", unit=unit, kob=0.5)]
    cd = max(0.8, w0*0.75)
    if kind == "cross":                         # small cross: one thread, arms overlap at the centre
        col = "gl_gold"
        return [R(col, taper_arm(cx, cy, a + rot, L, w0, 0.8, 0.0).union(Point(cx, cy).buffer(w0*0.62)), "satin", "auto", "STAR", unit=unit, kob=0.5)
                for L, a in ((Lv, -90), (Lh, 0), (Lv, 90), (Lh, 180))]
    arms = []
    for k, (L, a) in enumerate(((Lv, -90), (Lh, 0), (Lv, 90), (Lh, 180))):
        arms.append(taper_arm(cx, cy, a + rot, L, w0, 0.8, cd*0.6))          # tapered to a 0.8 tip
    if kind == "big":
        for a in (45, 135, 225, 315):
            arms.append(taper_arm(cx, cy, a + rot, Lh*0.62, w0*0.9, 0.8, cd*0.6))
    centre = Point(cx, cy).buffer(cd + 0.2, quad_segs=12)
    for g in arms:
        regs.append(R("gl_gold", g.difference(centre), "satin", "auto", "STAR", unit=unit, kob=0.5))
    regs.append(R("gl_pale", centre, "satin", "auto", "STAR-c", unit=unit, kob=0.5))   # same thread: arms + centre chain
    return regs

# ---------------------------------------------------------------- sun + rays
def dashed(p0, p1, dash=4.5, gap=2.5, wd=0.8, wl=0.45, col="gl_gold", grp="RAY", unit=None, phase=0.0):
    """dashed ray: bean dashes joined by a single-run link (no trims, reads as a dashed line)."""
    L = math.hypot(p1[0]-p0[0], p1[1]-p0[1]); ux, uy = (p1[0]-p0[0])/L, (p1[1]-p0[1])/L
    regs = []; s = -phase
    P = lambda t: (p0[0] + ux*t, p0[1] + uy*t)
    while s < L:
        a, b = max(0.0, s), min(L, s + dash)
        if b - a > 1.2:
            regs.append(R(col, LineString([P(a), P(b)]).buffer(wd/2, cap_style="round"), "bean", None, grp, unit=unit, kob=0.4))
        a2, b2 = min(L, s + dash), min(L, s + dash + gap)
        if b2 - a2 > 0.3 and b2 < L - 0.5:
            regs.append(R(col, LineString([P(a2 - 0.1), P(b2 + 0.1)]).buffer(wl/2, cap_style="flat"), "run", None, grp, unit=unit, kob=0.3))
        s += dash + gap
    return regs

def sun(cx, cy, r_core=5.2, r_ring=7.6, flat_y=None):
    core = Point(cx, cy).buffer(r_core, quad_segs=20)
    ring = Point(cx, cy).buffer(r_ring, quad_segs=24).difference(core)
    if flat_y is not None:
        core = core.intersection(box(cx - 20, cy - 20, cx + 20, flat_y)); ring = ring.intersection(box(cx - 20, cy - 20, cx + 20, flat_y))
    return [R("gl_gold", ring, "satin", ("radial", cx, cy), "SUN-ring", kob=0.4),
            R("gl_pale", core, "satin", ("radial", cx, cy), "SUN", kob=0.4)]

def burst(cx, cy, rays, r0, w0=1.7, w1=0.9, col="gl_gold"):
    out = []
    for ang, L in rays:
        out.append(R(col, taper_arm(cx, cy, ang, L, w0, w1, r0), "satin", "auto", "BURST", kob=0.5))
    return out

def arc_line(cx, cy, r, a0, a1, w=0.5, col="gl_deep", grp="GLW"):
    n = max(8, int(abs(a1 - a0) * r / 3))
    pts = [(cx + r*math.cos(math.radians(a)), cy + r*math.sin(math.radians(a))) for a in np.linspace(a0, a1, n)]
    return R(col, LineString(pts).buffer(w/2, cap_style="round"), "run", None, grp, kob=0.0)


def hair_dashes(pts, dash=4.2, gap=2.4, w=0.45, col="gl_gold", grp="RAY", phase=0.0, kob=0.3):
    """dashed hairline along a polyline (double-run line art, dash / gap by arc length)"""
    from shapely.ops import substring
    ln = LineString(pts); L = ln.length; s = -phase; out = []
    while s < L:
        a, b = max(0.0, s), min(L, s + dash)
        if b - a > 1.0: out.append(R(col, substring(ln, a, b).buffer(w/2, cap_style="round"), "run", None, grp, kob=kob))
        s += dash + gap
    return out
