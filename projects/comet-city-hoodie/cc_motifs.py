"""Motifs for the Comet City hoodie (candidates for the engine motif library — see ENGINE_NOTES.md).
Units mm, y down. Every function returns Region dicts (col, geom, st, ang, grp) like motifs2, plus optional keys:
  ko      False = overlay line sewn on top of what is under it (does not knock it out)
  kob     knockout buffer: regions below are cut back this far (dark fabric ring)
  unit    id of the motif (per-size clipping keeps or drops small motifs whole)"""
import math
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

def smooth_pts(pts, n=60):
    """smooth curve through control points (centripetal-ish Catmull-Rom by scipy spline)"""
    from scipy.interpolate import splprep, splev
    p = np.array(pts, float)
    k = min(3, len(p) - 1)
    tck, u = splprep([p[:, 0], p[:, 1]], s=0, k=k)
    x, y = splev(np.linspace(0, 1, n), tck)
    return np.c_[x, y]

def ribbon(pts, w):
    """polygon of a centreline with per-point width w (array), round-ish ends"""
    p = np.asarray(pts, float); w = np.asarray(w, float)
    d = np.gradient(p, axis=0); d /= np.maximum(np.linalg.norm(d, axis=1)[:, None], 1e-9)
    n = np.c_[-d[:, 1], d[:, 0]]
    left = p + n * (w[:, None] / 2); right = p - n * (w[:, None] / 2)
    g = Polygon(np.r_[left, right[::-1]]).buffer(0)
    return g

# ---------------------------------------------------------------- stars
def taper_arm(cx, cy, ang, L, w0, w1=0.85, r0=0.0):
    a = math.radians(ang); ux, uy = math.cos(a), math.sin(a); nx, ny = -uy, ux
    p0 = (cx + ux*r0, cy + uy*r0); p1 = (cx + ux*L, cy + uy*L)
    pts = [(p0[0] + nx*w0/2, p0[1] + ny*w0/2), (p1[0] + nx*w1/2, p1[1] + ny*w1/2),
           (p1[0] - nx*w1/2, p1[1] - ny*w1/2), (p0[0] - nx*w0/2, p0[1] - ny*w0/2)]
    return Polygon(pts).union(Point(*p1).buffer(w1/2, quad_segs=6))

STAR_SIZE = {   # kind -> (vertical arm, horizontal arm, base width, diagonal arm)
    "big": (12.5, 10.0, 2.0, 5.0), "sparkle": (8.4, 6.6, 1.6, 0.0), "cross": (4.3, 3.8, 1.2, 0.0), "dot": (1.1, 0, 0, 0)}

def star(cx, cy, kind, col, unit, k=1.0, rot=0.0):
    """4-point sparkle (8-point for 'big'): arms in `col`, white centre. kind: dot | cross | sparkle | big"""
    Lv, Lh, w0, Ld = STAR_SIZE[kind]
    if kind == "dot":
        return [R(col, Point(cx, cy).buffer(max(0.75, Lv*k), quad_segs=10), "satin", "auto", "DOT", unit=unit, kob=0.5)]
    Lv, Lh, w0, Ld = Lv*k, Lh*k, max(1.0, w0*min(1.0, k)), Ld*k
    if kind == "cross":                         # small cross: one thread, arms overlap at the centre
        g = unary_union([taper_arm(cx, cy, a + rot, L, w0, 0.8) for L, a in ((Lv, -90), (Lh, 0), (Lv, 90), (Lh, 180))] +
                        [Point(cx, cy).buffer(w0*0.7)])
        return [R(col, g, "satin", "auto", "STAR", unit=unit, kob=0.5)]
    cd = max(0.9, w0*0.8)
    arms = [taper_arm(cx, cy, a + rot, L, w0, 0.8, cd*0.6) for L, a in ((Lv, -90), (Lh, 0), (Lv, 90), (Lh, 180))]
    if Ld:
        arms += [taper_arm(cx, cy, a + rot, Ld, w0*0.8, 0.8, cd*0.6) for a in (45, 135, 225, 315)]
    centre = Point(cx, cy).buffer(cd + 0.25, quad_segs=12)
    regs = [R(col, g.difference(centre), "satin", "auto", "STAR", unit=unit, kob=0.5) for g in arms]
    regs.append(R("cc_white", centre, "satin", "auto", "STAR-c", unit=unit, kob=0.5))
    return regs

def meteor(p_head, p_tail, w_head=1.5, w_tail=0.85, col="cc_azure", unit=None, head_dot=True):
    """tapered satin streak, thick at the head; optional white head dot"""
    n = 24; t = np.linspace(0, 1, n)
    pts = np.c_[p_head[0] + (p_tail[0] - p_head[0])*t, p_head[1] + (p_tail[1] - p_head[1])*t]
    w = w_head + (w_tail - w_head) * t**0.8
    regs = [R(col, ribbon(pts, w).union(Point(p_head).buffer(w_head/2, quad_segs=8)), "satin", "auto", "MET", unit=unit, kob=0.4)]
    if head_dot:
        regs.append(R("cc_white", Point(p_head).buffer(max(0.75, w_head*0.55), quad_segs=10), "satin", "auto", "DOT", unit=unit, kob=0.3))
    return regs

def red_star(cx, cy, r=5.4, unit="redstar"):
    """falling star: 8 red rays (4 long) around a white core + spark dots"""
    regs = []
    core = Point(cx, cy).buffer(1.6, quad_segs=12)
    for k, a in enumerate(range(0, 360, 45)):
        L = r if k % 2 == 0 else r*0.62
        regs.append(R("cc_red", taper_arm(cx, cy, a - 90, L, 1.5 if k % 2 == 0 else 1.15, 0.8, 1.2).difference(core), "satin", "auto", "RSTAR", unit=unit, kob=0.4))
    regs.append(R("cc_white", core, "satin", ("radial", cx, cy), "STAR-c", unit=unit, kob=0.4))
    return regs

# ---------------------------------------------------------------- comet strands
def strand(spine, o, t0, t1, wmax, col, spread, grp="COM", unit=None, wtip=0.9, bulge=0.5):
    """one comet strand: spine = (N,2) curve head->tail; o = offset in [-1, 1] across the bundle; spread(t) = half-width
    of the bundle (mm) at t; the strand runs t0..t1 with a width that swells to wmax and tapers to wtip at both ends."""
    N = len(spine); ts = np.linspace(0, 1, N)
    d = np.gradient(spine, axis=0); d /= np.linalg.norm(d, axis=1)[:, None]
    nrm = np.c_[-d[:, 1], d[:, 0]]
    m = (ts >= t0) & (ts <= t1)
    if m.sum() < 3: return []
    tt = ts[m]; base = spine[m] + nrm[m] * (o * np.array([spread(t) for t in tt]))[:, None]
    u = (tt - t0) / max(t1 - t0, 1e-6)
    w = wtip + (wmax - wtip) * np.sin(np.pi * np.clip(u, 0, 1)) ** bulge
    w[0] = w[-1] = wtip
    g = ribbon(base, w)
    return [R(col, g, "satin", "auto", grp, unit=unit, kob=0.0)] if not g.is_empty else []

# ---------------------------------------------------------------- leaves (night garden)
def frond(base, ang, L, W, col, col_hl=None, grp="LF", unit=None, curl=0.18, n_teeth=None):
    """palm/fern frond: tapered blade with serrated edges along a gently curved midrib; optional light half.
    base = attachment point, ang = direction (deg, y down), L length, W max width."""
    a = math.radians(ang); ux, uy = math.cos(a), math.sin(a); nx, ny = -uy, ux
    n = 40; s = np.linspace(0, 1, n)
    bend = curl * L * s**2
    mid = np.c_[base[0] + ux*L*s + nx*bend, base[1] + uy*L*s + ny*bend]
    teeth = n_teeth or max(4, int(L / 3.2))
    prof = W/2 * np.sin(np.pi * np.clip(s*1.05, 0, 1)) ** 0.7 * (1 - 0.15*s)
    serr = 1 - 0.32 * np.abs(np.sin(np.pi * teeth * s))          # leaflet notches
    hw = np.maximum(prof * serr, 0.0)
    d = np.gradient(mid, axis=0); d /= np.maximum(np.linalg.norm(d, axis=1)[:, None], 1e-9)
    nn = np.c_[-d[:, 1], d[:, 0]]
    left = mid + nn * hw[:, None]; right = mid - nn * hw[:, None]
    blade = Polygon(np.r_[left, right[::-1]]).buffer(0)
    if blade.is_empty or blade.area < 1.0: return []
    if col_hl is None:
        return [R(col, blade, "satin", "auto", grp, unit=unit, kob=0.35)]
    half = Polygon(np.r_[left, mid[::-1]]).buffer(0).intersection(blade)
    rest = blade.difference(half.buffer(0.01))
    out = []
    if rest.area > 0.8: out.append(R(col, rest, "satin", "auto", grp, unit=unit, kob=0.35))
    if half.area > 0.8: out.append(R(col_hl, half, "satin", "auto", grp + "-hl", unit=unit, kob=0.35))
    return out

def rosette(cx, cy, R0, n, rot, col, col_hl, unit, rng, droop=0.25, spread=300):
    """plant rosette: n fronds radiating from (cx, cy), upper ones longer, lower ones drooping"""
    regs = []
    for k in range(n):
        a = rot - spread/2 + spread * (k + 0.5) / n + rng.uniform(-8, 8)
        up = -math.sin(math.radians(a))                      # +1 = pointing up
        L = R0 * (0.75 + 0.35*max(0.0, up)) * rng.uniform(0.85, 1.12)
        W = L * rng.uniform(0.34, 0.44)
        curl = (droop if math.cos(math.radians(a)) > 0 else -droop) * (0.5 + 0.5*(1 - up))
        regs += frond((cx, cy), a, L, W, col, col_hl if (k % 2 == 0) else None, unit=unit, curl=curl)
    return regs

def pinna(base, ang, L, W, col, col_hl, unit, droop, rng, grp="LF"):
    """arching palm/fern frond: curved midrib (bends toward the ground by `droop`), narrow leaflets on both sides
    (pinnate, swept toward the tip), leaflets alternate light / dark like the mockup's two-tone fronds."""
    a = math.radians(ang); ux, uy = math.cos(a), math.sin(a)
    n = 30; s = np.linspace(0, 1, n)
    mid = np.c_[base[0] + ux*L*s, base[1] + uy*L*s + droop*L*s**2]
    rib = LineString(mid)
    out = []
    d = np.gradient(mid, axis=0); d /= np.maximum(np.linalg.norm(d, axis=1)[:, None], 1e-9)
    nl = max(4, int(L / 2.6))
    blades = {col: [], col_hl: []}
    for i in range(nl):
        t = 0.12 + 0.86 * (i + 0.5) / nl; j = int(t * (n - 1))
        p = mid[j]; tg = d[j]; nn = np.array([-tg[1], tg[0]])
        ll = W * (0.55 + 0.45*math.sin(math.pi * min(1.0, t*1.1))) * rng.uniform(0.85, 1.1)
        for sgn_, c in ((1, col_hl if i % 2 == 0 else col), (-1, col if i % 2 == 0 else col_hl)):
            dirv = nn*sgn_*0.82 + tg*0.58; dirv /= np.linalg.norm(dirv)
            tip = p + dirv*ll; w0 = max(1.0, ll*0.34)
            nb = np.array([-dirv[1], dirv[0]])
            blade = Polygon([p + nb*w0/2 - tg*0.3, tip + nb*0.35, tip - nb*0.35, p - nb*w0/2 + tg*0.3]).buffer(0.25, join_style=1)
            blades[c].append(blade)
    for c, bl in blades.items():
        g = unary_union(bl).buffer(0)
        if not g.is_empty: out.append(R(c, g, "satin", "auto", grp + ("-hl" if c == col_hl else ""), unit=unit, kob=0.3))
    out.append(R(col, rib.buffer(0.55, cap_style="round"), "satin", "auto", grp, unit=unit, kob=0.3))
    return out

def palm(cx, cy, R0, n, rot, col, col_hl, unit, rng):
    """small palm / fern plant: n arching fronds fanned over the upper half, outer ones drooping"""
    regs = []
    for k in range(n):
        f = (k + 0.5) / n - 0.5                       # -0.5 .. 0.5 across the fan
        a = rot + f * 200 + rng.uniform(-7, 7)
        L = R0 * (1.0 - 0.35*abs(f)) * rng.uniform(0.85, 1.1)
        droop = 0.15 + 0.9*abs(f)
        regs += pinna((cx, cy), a, L, L*0.30, col, col_hl, unit, droop, rng)
    return regs

# ---------------------------------------------------------------- bicycle (line art)
def bicycle(rx, ry, r=22.0, wb=84.0, unit="bike"):
    """side view, facing +x; rear hub at (rx, ry). Tyres: dusk satin rings, frame: ice bean lines, spokes: run."""
    P = lambda x, y: (rx + x, ry + y)
    out = []
    def line(pts, w, col, st="bean", grp="BIKE", ko=False):
        out.append(R(col, LineString([P(*p) for p in pts]).buffer(w/2, cap_style="round", join_style="round"), st, None, grp, unit=unit, ko=ko, kob=0.0))
    for hx in (0.0, wb):
        c = Point(P(hx, 0))
        out.append(R("cc_dusk", c.buffer(r).difference(c.buffer(r - 1.7)), "satin", ("radial", *P(hx, 0)), "BIKE", unit=unit, ko=False, kob=0.0))
        out.append(R("cc_ice", c.buffer(r - 2.1).difference(c.buffer(r - 2.9)), "bean", None, "BIKE", unit=unit, ko=False, kob=0.0))
        for k in range(12):
            a = math.radians(k * 30 + 7)
            line([(hx + 1.6*math.cos(a), 1.6*math.sin(a)), (hx + (r - 3.0)*math.cos(a), (r - 3.0)*math.sin(a))], 0.45, "cc_cloud", "run")
        out.append(R("cc_ice", c.buffer(1.4), "satin", "auto", "BIKE", unit=unit, ko=False, kob=0.0))
    C = (36.0, 2.0); Sd = (20.0, -29.0); Ht = (63.0, -29.0); Hb = (66.0, -18.0); F = (wb, 0.0)
    for a, b in ((C, (0, 0)), ((0, 0), Sd), (C, Sd), (Sd, Ht), (C, Hb), (Ht, Hb), (Hb, F)):
        line([a, b], 0.95, "cc_ice")
    line([Ht, (62.0, -36.0), (70.0, -38.0), (74.0, -36.5)], 0.95, "cc_ice")            # stem + bar
    out.append(R("cc_ice", LineString([P(13.0, -32.0), P(25.0, -32.5)]).buffer(1.2, cap_style="round"), "satin", "auto", "BIKE", unit=unit, ko=False, kob=0.0))
    line([(20.0, -29.0), (19.0, -32.0)], 0.95, "cc_ice")
    out.append(R("cc_ice", Point(P(*C)).buffer(2.4).difference(Point(P(*C)).buffer(1.3)), "bean", None, "BIKE", unit=unit, ko=False, kob=0.0))
    line([C, (41.0, 8.0)], 0.95, "cc_ice"); line([(38.5, 8.3), (44.0, 8.0)], 1.1, "cc_ice")
    return out

# ---------------------------------------------------------------- figure seen from behind (original pose)
def figure(fx, fy, H=118.0, unit="figure", wk=1.0):
    """standing figure seen from behind, hands in the jacket pockets, head tilted up to the comet.
    (fx, fy) = point between the feet on the ground; H = height. Night fill, ice rim light, dusk fold lines."""
    k = H / 118.0
    P = lambda x, y: (fx + x*k*wk, fy - y*k)         # y up in the drawing; wk = width factor
    def poly(pts): return Polygon([P(*p) for p in pts]).buffer(0)
    # hair: rounded mass with soft tufts (not spiky)
    hc = (0.5, 103.0); hr = 10.5
    hair = Point(P(*hc)).buffer(hr*k, quad_segs=24)
    tufts = unary_union([Point(P(hc[0] + (hr - 1.2)*math.cos(math.radians(a)), hc[1] + (hr - 1.2)*math.sin(math.radians(a)))).buffer(2.6*k, quad_segs=10)
                         for a in (20, 50, 80, 110, 140, 165, 195)])
    head = unary_union([hair, tufts]).buffer(0.6*k).buffer(-0.6*k)
    neck = poly([(-3.5, 94), (4.5, 94), (4.0, 88), (-3.0, 88)])
    torso = poly([(-15, 86), (-19, 82), (-20.5, 70), (-19.5, 45), (-18.5, 38), (19.5, 38), (20.5, 45), (21.5, 70), (20, 82), (16, 86), (6, 89), (-5, 89)])
    armL = poly([(-19, 82), (-23.5, 74), (-24.0, 60), (-23.0, 50), (-20.0, 43), (-17.5, 45), (-19.5, 52), (-20.0, 62), (-19, 72)])
    armR = poly([(20, 82), (24.5, 74), (25.0, 60), (24.0, 50), (21.0, 43), (18.5, 45), (20.5, 52), (21.0, 62), (20, 72)])
    legs = poly([(-16.5, 39), (16.5, 39), (15.5, 0), (2.5, 0), (1.5, 30), (-0.5, 30), (-1.5, 0), (-15.0, 0)])
    body = unary_union([head, neck, torso, armL, armR, legs]).buffer(0)
    rim_zone = body.difference(body.buffer(-0.95))
    rim = rim_zone.difference(box(*P(-40, 2), *P(40, -10)).buffer(0))              # no rim at the feet
    # jacket night with dusk raglan shoulders/upper arms; pants + hair night; ice rim light
    yoke = Polygon([P(-30, 92), P(-6, 89), P(-14, 77), P(-28, 64), P(-40, 64)]).union(Polygon([P(30, 92), P(7, 89), P(15, 77), P(29, 64), P(41, 64)])).buffer(0)
    fill = body.difference(rim)
    out = [R("cc_night", fill.difference(yoke).buffer(0), "tatami", 90.0, "FIG", unit=unit, kob=0.6),
           R("cc_dusk", fill.intersection(yoke).buffer(0), "tatami", 70.0, "FIG", unit=unit, kob=0.6),
           R("cc_ice", rim, "satin", "auto", "FIG-rim", unit=unit, kob=0.0)]
    def fold(pts, w=0.6, col="cc_dusk"):
        out.append(R(col, LineString([P(*p) for p in pts]).buffer(w/2*k, cap_style="round"), "run", None, "FIG-line", unit=unit, ko=False, kob=0.0))
    fold([(-17.5, 47), (-18.5, 62), (-17.0, 78)]); fold([(18.5, 47), (19.5, 62), (18.0, 78)])           # arm / body separation
    fold([(-11, 85), (-7, 79), (0, 77), (8, 79), (12, 85)])                                               # hood lying flat
    fold([(0, 77), (0.5, 40)])                                                                            # centre back seam
    fold([(-18.5, 40), (19.5, 40)], 0.8)                                                                  # jacket hem band
    fold([(0.5, 30), (0.5, 4)])                                                                           # leg gap
    return out
