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
        k_ = int(n*0.35); core = LineString(pts[:k_]).buffer(0.42, cap_style="round") if k_ >= 2 else None
        if core is not None and w_head >= 1.5:
            regs.append(R("cc_white", core, "satin", "auto", "MET", unit=unit, kob=0.0))
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


# ================================================================ Rev B motifs (review 17 Oct: solid silhouettes, glows)
def star_b(cx, cy, kind, col, unit, k=1.0, glow=None, rot=0.0):
    """star with size factor k and an optional soft glow (short diagonal rays in `glow`, lilac / azure)"""
    regs = star(cx, cy, kind, col, unit, k=k, rot=rot)
    if glow and kind in ("sparkle", "big", "cross"):
        Lv, Lh, w0, Ld = STAR_SIZE[kind]
        L = max(1.8, 0.42 * Lh * k) if kind != "big" else 0.0
        if L:
            cd = 1.0
            for a in (45, 135, 225, 315):
                g = taper_arm(cx, cy, a + rot, L + cd, 1.0, 0.8, cd)
                regs.append(R(glow, g, "satin", "auto", "STAR", unit=unit, kob=0.4))
    return regs

def falling_star(cx, cy, r=6.0, unit="redstar"):
    """bright red-white starburst: 8 red rays, 8 short white rays between them, white core with halo ring"""
    regs = []
    core = Point(cx, cy).buffer(2.0, quad_segs=14)
    for k, a in enumerate(range(0, 360, 45)):
        L = r if k % 2 == 0 else r * 0.66
        regs.append(R("cc_red", taper_arm(cx, cy, a - 90, L, 1.6 if k % 2 == 0 else 1.2, 0.8, 1.6).difference(core.buffer(0.3)), "satin", "auto", "RSTAR", unit=unit, kob=0.4))
    for a in range(0, 360, 45):
        regs.append(R("cc_white", taper_arm(cx, cy, a - 67.5, r * 0.45, 1.0, 0.8, 1.6).difference(core.buffer(0.3)), "satin", "auto", "RSTAR", unit=unit, kob=0.4))
    regs.append(R("cc_white", core, "satin", ("radial", cx, cy), "STAR-c", unit=unit, kob=0.4))
    for a in range(0, 360, 30):                                     # halo: 12 white sparks just outside the rays
        t_ = math.radians(a + 15); d_ = r * 1.18
        regs.append(R("cc_white", Point(cx + d_*math.cos(t_), cy + d_*math.sin(t_)).buffer(0.55, quad_segs=6), "satin", "auto", "DOT", unit=unit, kob=0.3))
    return regs

def bicycle_b(rx, ry, r=26.0, wb=96.0, unit="bike"):
    """side view, facing +x; rear hub (rx, ry). Dark solid: night tyres + frame, dusk spokes, ice glints on the frame + rims."""
    P = lambda x, y: (rx + x, ry + y)
    out = []
    def tube(pts, w, col="cc_night", grp="BIKE"):
        out.append(R(col, LineString([P(*p) for p in pts]).buffer(w/2, cap_style="round", join_style="round"), "satin", "auto", grp, unit=unit, kob=0.5))
    s = r / 22.0
    for hx in (0.0, wb):
        c = Point(P(hx, 0))
        out.append(R("cc_night", c.buffer(r).difference(c.buffer(r - 2.8)), "satin", ("radial", *P(hx, 0)), "BIKE", unit=unit, kob=0.5))
        out.append(R("cc_dusk", c.buffer(r - 2.8).difference(c.buffer(r - 3.8)), "satin", ("radial", *P(hx, 0)), "BIKE", unit=unit, kob=0.0))
        arc = [(hx + (r - 0.6)*math.cos(math.radians(a)), (r - 0.6)*math.sin(math.radians(a))) for a in np.linspace(185, 335, 22)]
        out.append(R("cc_ice", LineString([P(*p) for p in arc]).buffer(0.45, cap_style="round"), "satin", "auto", "BIKE", unit=unit, kob=0.0))
        for k in range(12):
            a = math.radians(k * 30 + 7)
            out.append(R("cc_dusk", LineString([P(hx + 2.0*math.cos(a), 2.0*math.sin(a)), P(hx + (r - 3.8)*math.cos(a), (r - 3.8)*math.sin(a))]).buffer(0.3, cap_style="flat"),
                         "run", None, "BIKE", unit=unit, kob=0.0))
        out.append(R("cc_ice", c.buffer(1.6), "satin", "auto", "BIKE", unit=unit, kob=0.2))
    C = (41.0*s, 2.0); Sd = (23.0*s, -33.0*s); Ht = (72.0*s, -33.0*s); Hb = (75.0*s, -20.0*s); Fh = (wb, 0.0)
    for a, b in ((C, (0, 0)), ((0, 0), Sd), (C, Sd), (Sd, Ht), (C, Hb), (Ht, Hb), (Hb, Fh)):
        tube([a, b], 1.7)
    tube([Ht, (71.0*s, -41.0*s), (80.0*s, -43.0*s), (84.0*s, -41.0*s)], 1.6)
    out.append(R("cc_night", LineString([P(14.0*s, -37.0*s), P(28.0*s, -37.5*s)]).buffer(1.5, cap_style="round"), "satin", "auto", "BIKE", unit=unit, kob=0.5))
    tube([(23.0*s, -33.0*s), (22.0*s, -37.0*s)], 1.6)
    out.append(R("cc_night", Point(P(*C)).buffer(3.0), "satin", "auto", "BIKE", unit=unit, kob=0.5))
    # glints: thin ice lines along the top of the top tube + seat stay, and the saddle top
    for a, b in ((Sd, Ht), ((0, 0), Sd), (C, Sd), (C, Hb), (Hb, Fh), (C, (0, 0))):
        ax, ay = a; bx, by = b; nx, ny = -(by - ay), (bx - ax); L = math.hypot(nx, ny); nx, ny = nx / L * -0.55, ny / L * -0.55
        out.append(R("cc_ice", LineString([P(ax + (bx-ax)*0.1 + nx, ay + (by-ay)*0.1 + ny), P(ax + (bx-ax)*0.85 + nx, ay + (by-ay)*0.85 + ny)]).buffer(0.4, cap_style="round"), "satin", "auto", "BIKE", unit=unit, kob=0.0))
    out.append(R("cc_ice", LineString([P(15.0*s, -38.3*s), P(26.0*s, -38.8*s)]).buffer(0.4, cap_style="round"), "satin", "auto", "BIKE", unit=unit, kob=0.0))
    return out

def figure_b(fx, fy, H=118.0, unit="figure", wk=1.22):
    """solid figure seen from behind (our pose: arms down, hands loose at the sides, head tilted up), spiky hair,
    hood lying on the shoulders, raglan jacket. Night fill, azure rim light, dusk raglan seams. Nothing shows through."""
    k = H / 118.0
    P = lambda x, y: (fx + x*k*wk, fy - y*k)
    def poly(pts): return Polygon([P(*p) for p in pts]).buffer(0)
    hc = (0.5, 103.0); hr = 11.5
    head = Point(P(*hc)).buffer(hr*k, quad_segs=24)
    spikes = []
    for i, a in enumerate(np.linspace(15, 165, 11)):
        L = hr * (1.16 + 0.08 * ((i * 7) % 3)); t = math.radians(a)
        tip = (hc[0] + L*math.cos(t), hc[1] + L*math.sin(t))
        b1 = (hc[0] + (hr - 1)*math.cos(t - 0.16), hc[1] + (hr - 1)*math.sin(t - 0.16))
        b2 = (hc[0] + (hr - 1)*math.cos(t + 0.16), hc[1] + (hr - 1)*math.sin(t + 0.16))
        spikes.append(poly([b1, tip, b2]))
    hair = unary_union([head] + spikes).buffer(0.25*k).buffer(-0.25*k)
    neck = poly([(-4, 95), (5, 95), (4.5, 88), (-3.5, 88)])
    hood = poly([(-13, 91), (-6, 95), (6, 95), (14, 91), (12, 84), (0, 81), (-11, 84)])
    torso = poly([(-15, 87), (-20, 82), (-21.5, 68), (-20.5, 44), (-19, 37), (20, 37), (21.5, 44), (22.5, 68), (21, 82), (16, 87), (6, 89), (-5, 89)])
    armL = poly([(-20, 82), (-25, 74), (-26.5, 58), (-25.5, 44), (-24.5, 40), (-20.5, 40), (-21, 50), (-21.5, 62), (-20, 72)])
    armR = poly([(21, 82), (26, 74), (27.5, 58), (26.5, 44), (25.5, 40), (21.5, 40), (22, 50), (22.5, 62), (21, 72)])
    handL = Point(P(-23.0, 37.5)).buffer(2.6*k, quad_segs=12); handR = Point(P(23.5, 37.5)).buffer(2.6*k, quad_segs=12)
    legs = poly([(-17, 38), (17, 38), (16, 0), (2.5, 0), (1.5, 26), (-0.5, 26), (-1.5, 0), (-15.5, 0)])
    body = unary_union([hair, neck, hood, torso, armL, armR, handL, handR, legs]).buffer(0.3).buffer(-0.3)
    rimz = body.difference(body.buffer(-1.0))
    rim = rimz.intersection(box(fx - 80, fy - 200, fx + 80, fy - 44*k))          # rim light on hair, shoulders, arms (not hands / legs)
    sleeves = unary_union([armL, armR, poly([(-20, 82), (-15, 87), (-8, 89), (-13, 80), (-18, 66)]), poly([(21, 82), (16, 87), (9, 89), (14, 80), (19, 66)])]).intersection(body).difference(rim).buffer(0)
    out = [R("cc_night", body.difference(rim).difference(sleeves).buffer(0), "tatami", 90.0, "FIG", unit=unit, kob=0.7),
           R("cc_dusk", sleeves, "tatami", 80.0, "FIG", unit=unit, kob=0.0),
           R("cc_azure", rim.buffer(0), "satin", "auto", "FIG-rim", unit=unit, kob=0.0)]
    for pts in (((-13, 88), (-17, 70), (-19, 50)), ((14, 88), (18, 70), (20, 50))):                 # raglan seams
        out.append(R("cc_dusk", LineString([P(*p) for p in pts]).buffer(0.35*k, cap_style="round"), "run", None, "FIG-line", unit=unit, kob=0.0))
    out.append(R("cc_dusk", LineString([P(-12, 87), P(-5, 83), P(0, 82), P(6, 83), P(13, 87)]).buffer(0.35*k), "run", None, "FIG-line", unit=unit, kob=0.0))
    return out

def lamp_b(x, y_top, y_bot, unit="lamp"):
    """slim post + lantern head: night, gold glass, ice rim light down the left edge + head outline"""
    head_w, head_h = 10.5, 30.0
    lant = box(x - head_w/2, y_top + 4, x + head_w/2, y_top + 4 + head_h)
    capg = Polygon([(x - head_w/2 - 1.5, y_top + 4.5), (x + head_w/2 + 1.5, y_top + 4.5), (x, y_top)])
    neck = box(x - 2.2, y_top + 4 + head_h, x + 2.2, y_top + 8 + head_h)
    pole = box(x - 1.8, y_top + 8 + head_h, x + 1.8, y_bot)
    base = box(x - 3.2, y_bot - 6, x + 3.2, y_bot)
    body = unary_union([lant, capg, neck, pole, base]).buffer(0)
    glass = box(x - head_w/2 + 2.0, y_top + 8, x + head_w/2 - 2.0, y_top + head_h)
    ring = body.difference(body.buffer(-0.9))
    rim = ring.intersection(box(x - 20, y_top - 5, x - 0.2, y_bot + 1)).union(ring.intersection(box(x - 20, y_top - 5, x + 20, y_top + 8 + head_h))).difference(glass.buffer(0.6))
    return [R("cc_night", body.difference(glass.buffer(0.35)).difference(rim).buffer(0), "satin", "auto", "LAMP", unit=unit, kob=0.8),
            R("cc_dusk", glass, "satin", 90.0, "LAMP-l", unit=unit, kob=0.0),
            R("cc_ice", rim.buffer(0), "satin", "auto", "LAMP", unit=unit, kob=0.0)]

def bush_b(cx, base_y, w, h, rng, unit="bush"):
    """soft dark bush: night mound of overlapping domes + leaf-shaped highlight dabs (royal / azure / dusk) on the upper part"""
    domes = []
    n = max(4, int(w / 9))
    for i in range(n):
        x = cx - w/2 + w * (i + 0.5) / n + rng.uniform(-2, 2)
        r = rng.uniform(0.45, 0.65) * h * (1.0 - 0.5 * abs((i + 0.5)/n - 0.5))
        domes.append(Point(x, base_y - r * 0.8).buffer(r, quad_segs=16))
    mound = unary_union(domes).intersection(box(cx - w, base_y - 2*h, cx + w, base_y)).buffer(0)
    out = [R("cc_night", mound, "tatami", 75.0, "BUSH", unit=unit, kob=0.6)]
    b = mound.bounds; dabs = {"cc_royal": [], "cc_azure": [], "cc_dusk": []}
    for _ in range(int(mound.area / 4)):
        x, y = rng.uniform(b[0], b[2]), rng.uniform(b[1], b[3])
        if not mound.buffer(-1.6).contains(Point(x, y)): continue
        tfrac = (y - b[1]) / max(1, b[3] - b[1])
        if rng.random() < tfrac * 0.55: continue                      # highlights on the upper part
        L = rng.uniform(2.8, 4.6); a = rng.uniform(-150, -30)
        leaf = affinity.rotate(affinity.scale(Point(x, y).buffer(1.0, quad_segs=8), L/2, 0.75), a, origin=(x, y))
        q = rng.random(); c = "cc_dusk" if q < 0.5 else ("cc_royal" if q < 0.92 else "cc_azure")
        dabs[c].append(leaf)
    for c, ls in dabs.items():
        g = unary_union(ls).intersection(mound.buffer(-0.4)).buffer(0)
        if not g.is_empty: out.append(R(c, g, "satin", "auto", "BUSH-hl", unit=unit, kob=0.0))
    return out

def fern(base, ang, L, col, col_hl, unit, rng, droop=0.25):
    """single arching fern frond: thin rib, many short narrow leaflets alternating light / dark"""
    return pinna(base, ang, L, L*0.22, col, col_hl, unit, droop, rng, grp="LF")

def broad_leaf(base, ang, L, col, col_hl, unit, curl=0.15):
    """broad tropical leaf (monstera / banana-like): wide serrated blade, light half"""
    return frond(base, ang, L, L*0.55, col, col_hl, grp="LF", unit=unit, curl=curl, n_teeth=max(3, int(L/4.5)))

def sprig(base, ang, L, col, unit, rng):
    """small sprig: 3-5 tiny leaves on a short stem"""
    out = []
    a = math.radians(ang); ux, uy = math.cos(a), math.sin(a)
    stem = LineString([base, (base[0] + ux*L, base[1] + uy*L)])
    out.append(R(col, stem.buffer(0.5, cap_style="round"), "satin", "auto", "LF", unit=unit, kob=0.3))
    for k in range(rng.randint(3, 5)):
        t = 0.35 + 0.65*k/4; p = (base[0] + ux*L*t, base[1] + uy*L*t); s = 1 if k % 2 else -1
        la = ang + s*rng.uniform(35, 60)
        out += frond(p, la, L*0.38, L*0.2, col, None, unit=unit, curl=0.0, n_teeth=2)
    return out
