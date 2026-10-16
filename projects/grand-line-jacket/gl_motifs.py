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
TONES = {   # lobe class -> (body, rim, shade)
    "cream": ("gl_cream", "gl_pale", "gl_sand"),
    "sand":  ("gl_sand", "gl_cream", "gl_sage"),
    "sage":  ("gl_sage", "gl_sagelt", "gl_slate"),
    "slate": ("gl_slate", "gl_sagelt", "gl_shadow"),
}
EDGE = "gl_shadow"          # dark edge band along every lobe that sits in front of another
SUB = {"rim": 0.1, "shade": 0.2, "body": 0.3, "edge": 0.4}     # sew order inside a cloud layer (travel hides under later parts)

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

def lobe_regions(lobes, tone_of, flat_y=None, grp="CL", unit=None, base_bottom=True, edge_w=1.15):
    """visible part of each lobe -> rim (lit top edge), body, shade band and a dark edge band where the lobe in front
    overlaps it. Lobes touch (no fabric gaps); the edge bands of neighbouring lobes join into one connected network.
    Each region carries 'sub' (rim/body/shade/edge) for the sew order."""
    discs = []
    EX, EY = 1.16, 0.9                                   # lobes a little wider than tall (cumulus domes)
    def ell(cx, cy, r): return affinity.scale(Point(cx, cy).buffer(1.0, quad_segs=24), r*EX, r*EY, origin=(cx, cy))
    for cx, cy, r, z in lobes:
        d = ell(cx, cy, r)
        if flat_y is not None: d = d.intersection(box(cx - 2*r, cy - 2*r, cx + 2*r, flat_y))
        discs.append((z, cx, cy, r, d))
    discs.sort(key=lambda t: -t[0])                     # front first
    regs = []; front = Polygon()
    for z, cx, cy, r, d in discs:
        V = (d.difference(front) if not front.is_empty else d).buffer(0)
        if V.area < 3.0:
            front = front.union(d); continue
        tone = tone_of(V, (cx, cy, r))
        bcol, rcol, scol = TONES[tone]
        wr = min(3.0, max(1.3, 0.24*r)); ws = min(3.2, max(1.3, 0.26*r))
        edge = V.intersection(front.buffer(edge_w)) if not front.is_empty else Polygon()
        if base_bottom and r >= 3.5:
            bot = V.intersection(box(cx - 2*r, cy + 0.9*r*EY - edge_w, cx + 2*r, cy + 2*r))
            edge = edge.union(bot)
        edge = smooth(edge.intersection(V), 0.3)
        # the edge band is an overlay (sewn last, on top): body + shade run underneath it so neighbouring bodies touch
        shade = V.intersection(front.buffer(edge_w + ws)) if not front.is_empty else Polygon()
        if base_bottom:
            shade = shade.union(V.intersection(box(cx - 2*r, cy + max(0.45*r, 0.9*r*EY - edge_w - ws), cx + 2*r, cy + 2*r)))
        shade = smooth(shade, 0.4) if r >= 4.0 else Polygon()
        rim = V.intersection(ell(cx, cy, r).difference(ell(cx, cy + 0.35*wr, r - wr))).intersection(box(cx - 2*r, cy - 2*r, cx + 2*r, cy + 0.2*r))
        rim = smooth(rim.difference(edge.buffer(0.2)).difference(shade.buffer(0.2)), 0.45) if r >= 5.0 else Polygon()
        body = V.difference(rim).difference(shade).buffer(0)
        # slivers narrower than the 0.8 satin minimum go to the shade (or rim) band they touch
        bc = body.buffer(-0.42).buffer(0.42).intersection(body)
        sl = body.difference(bc)
        if not sl.is_empty and sl.area > 0.01:
            body = bc
            if not shade.is_empty: shade = shade.union(sl.intersection(shade.buffer(0.6).union(sl))).buffer(0)
            elif not rim.is_empty: rim = rim.union(sl).buffer(0)
            else: body = body.union(sl)
        for col, g, gg, sb in ((rcol, rim, grp + "-rim", "rim"), (bcol, body, grp, "body"), (scol, shade, grp + "-shade", "shade"), (EDGE, edge, grp + "-edge", "edge")):
            if not g.is_empty: regs.append(R(col, g, "satin", "auto", gg, unit=unit, sub=sb, ko=(sb != "edge")))
        front = front.union(d)
    return regs, front

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
        return [R("gl_pale", Point(cx, cy).buffer(max(0.75, Lv/2), quad_segs=10), "satin", "auto", "DOT", unit=unit, kob=0.5)]
    cd = max(0.8, w0*0.75)
    if kind in ("cross", "sparkle"):            # one thread: arms overlap at the centre and chain without a trim
        col = "gl_pale" if kind == "cross" else "gl_gold"
        return [R(col, taper_arm(cx, cy, a + rot, L, w0, 0.9, 0.0).union(Point(cx, cy).buffer(w0*0.62)), "satin", "auto", "STAR", unit=unit, kob=0.5)
                for L, a in ((Lv, -90), (Lh, 0), (Lv, 90), (Lh, 180))]
    arms = []
    for k, (L, a) in enumerate(((Lv, -90), (Lh, 0), (Lv, 90), (Lh, 180))):
        arms.append(taper_arm(cx, cy, a + rot, L, w0, 0.9, cd*0.6))
    if kind == "big":
        for a in (45, 135, 225, 315):
            arms.append(taper_arm(cx, cy, a + rot, Lh*0.42, w0*0.8, 0.9, cd*0.6))
    centre = Point(cx, cy).buffer(cd + 0.2, quad_segs=12)
    for g in arms:
        regs.append(R("gl_gold", g.difference(centre), "satin", "auto", "STAR", unit=unit, kob=0.5))
    regs.append(R("gl_pale", centre, "satin", "auto", "STAR-c", unit=unit, kob=0.5))
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
