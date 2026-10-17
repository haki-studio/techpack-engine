import warnings
warnings.filterwarnings('ignore', category=RuntimeWarning)
"""Koi blossom motif library (units mm, y down). Every motif returns a list of region dicts
(col, geom, st, ang, grp, sub) in local z order (first = sewn/stacked lowest) plus its silhouette.
Detail level follows the close-up (inputs/closeup_mockup_koi.png): long-and-short tone steps are built as 2-4 tone
bands with zig-zag boundaries; koi are top views with pectoral + pelvic fin pairs, forked tail with rays, red kohaku
patches, eyes.  Candidates for engine/motifs3.py (ENGINE_NOTES)."""
import math, random
import numpy as np
from shapely.geometry import Point, Polygon, LineString, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
from motifs import sweep, taper, catmull

def R(col, geom, st, ang, grp, sub=0):
    return dict(col=col, geom=geom.buffer(0), st=st, ang=ang, grp=grp, sub=sub)

def T(g, x, y, ang):
    return affinity.translate(affinity.rotate(g, ang, origin=(0, 0)), x, y)

def line_poly(pts, w):
    return LineString(pts).buffer(w / 2, cap_style="round", join_style="round")

def jag_cut(t_of, n, amp, lo=-50.0, hi=50.0, period=1.6, phase=0.0, rng=None):
    """polygon of the half plane x < t(lat) in local coords, boundary zig-zag (long-and-short look).
    t_of(lat) = base boundary x at lateral y; amp = zig-zag depth; period = tooth width (mm)."""
    ys = np.arange(lo, hi + period/2, period/2)
    pts = []
    for i, y in enumerate(ys):
        a = amp * (1 if i % 2 == 0 else -1) * (0.6 + 0.4*((rng.random() if rng else 0.5)))
        pts.append((t_of(y) + a + phase, y))
    return Polygon([(-500, lo)] + pts + [(-500, hi)]).buffer(0)

# ================================================================ koi (top view)
RED_PATTERNS = [     # (s0, s1, lateral offset as a fraction of W): long patches along the back, as in the close-up
    [(0.13, 0.33, -0.08), (0.38, 0.62, -0.06)],                    # shoulder patch + long back patch
    [(0.16, 0.46, -0.06), (0.51, 0.64, 0.02)],                     # long shoulder patch + tail-root patch
    [(0.12, 0.30, -0.04), (0.36, 0.62, -0.08)],                    # head-to-shoulder + long back patch
    [(0.15, 0.58, -0.06)],                                         # one long patch
]

def koi_profile(L, W):
    """half-width h(s), s = 0 head tip .. 0.70 peduncle"""
    def h(s):
        if s < 0.0 or s > 0.70: return 0.0
        if s < 0.26: return W/2 * math.sin(math.pi/2 * (s/0.26))**0.75
        return W/2 - (W/2 - 0.045*L) * ((s - 0.26)/0.44)**1.15
    return h

def koi(cx, cy, L, ang, rng, pattern=0, bend=0.0, unit=None):
    """koi centred at (cx, cy), head pointing along `ang` (deg, y down), body length L (head tip to tail tip).
    bend: lateral curvature (mm at the tail tip, + = toward local +y)."""
    W = 0.20 * L; h = koi_profile(L, W)
    X = lambda s: L/2 - s*L                       # local x: head tip at +L/2
    def spine(s): return bend * (s**2)            # lateral offset of the spine
    ss = np.linspace(0, 0.70, 60)
    top = [(X(s), spine(s) - h(s)) for s in ss]; bot = [(X(s), spine(s) + h(s)) for s in ss]
    body = Polygon(top + bot[::-1]).buffer(0.01).buffer(0)
    head_c = (X(0.10), spine(0.10))
    regs = []
    # tail: forked fan from the peduncle, two lobes
    s0 = 0.66; px0 = X(s0); oy = spine(s0)
    tip = 0.13*L; lob = []
    for sg in (-1, 1):
        root = [(px0 + 0.5, oy - 0.04*L*sg*0), (px0, oy + 0.045*L*sg)]
        outer = [(X(0.80), oy + sg*0.10*L + spine(0.8) - oy), (X(0.93), oy + sg*0.15*L + spine(0.93) - oy), (X(1.0), oy + sg*tip + spine(1.0) - oy)]
        notch = [(X(0.93), spine(0.93) + sg*0.055*L), (X(0.86), spine(0.86) + sg*0.012*L)]
        lob.append(Polygon([(px0 + 1.0, oy)] + root[1:] + outer + notch).buffer(0.25).buffer(-0.25))
    tail = unary_union(lob).buffer(0)
    tail_base = tail.intersection(Point(px0, oy).buffer(0.13*L))
    regs.append(R("kb_cream", tail.difference(tail_base), "satin", ("radial", px0 + 2, oy), "KO-tail", 1))
    regs.append(R("kb_white", tail_base, "satin", ("radial", px0 + 2, oy), "KO-tail", 1))
    rays = []
    for sg in (-1, 1):
        for k, f in enumerate((0.25, 0.55, 0.85)):
            e = (X(0.80 + 0.18*f), spine(0.80 + 0.18*f) + sg*(0.03*L + f*0.11*L))
            rays.append(line_poly([(X(0.71), spine(0.71) + sg*0.012*L), e], 0.65))
    ray_u = unary_union(rays).intersection(tail.buffer(-0.35))
    regs.append(R("kb_grey", ray_u, "run", None, "KO-ray", 2))
    # fins: pectoral pair at s 0.24, pelvic pair at s 0.47 (fan shapes swept back), cream with grey rays
    fin_rays = []
    for s_f, fl, fw, back in ((0.24, 0.13*L, 0.065*L, 55), (0.47, 0.085*L, 0.045*L, 60)):
        for sg in (-1, 1):
            bx, by = X(s_f), spine(s_f) + sg*h(s_f)*0.85
            a = math.radians(180 - back) if sg > 0 else math.radians(180 + back)
            ux, uy = math.cos(a), math.sin(a)                 # swept back toward the tail
            nx, ny = -uy, ux
            tipp = (bx + ux*fl, by + uy*fl)
            fan = Polygon([(bx - ux*1.2 + nx*fw*0.25, by - uy*1.2 + ny*fw*0.25), (bx + ux*fl*0.55 + nx*fw*0.55, by + uy*fl*0.55 + ny*fw*0.55),
                           tipp, (bx + ux*fl*0.8 - nx*fw*0.5, by + uy*fl*0.8 - ny*fw*0.5), (bx - ux*1.2 - nx*fw*0.3, by - uy*1.2 - ny*fw*0.3)])
            fan = fan.buffer(0.6).buffer(-0.6)
            regs.append(R("kb_cream", fan, "satin", ("radial", bx, by), "KO-fin", 1))
            if fl > 6:
                for f in (-0.3, 0.15):
                    fin_rays.append(line_poly([(bx, by), (bx + ux*fl*0.85 + nx*fw*f, by + uy*fl*0.85 + ny*fw*f)], 0.65))
    if fin_rays:
        fins_u = unary_union([r["geom"] for r in regs if r["grp"] == "KO-fin"])
        regs.append(R("kb_grey", unary_union(fin_rays).intersection(fins_u.buffer(-0.3)).difference(body.buffer(0.3)), "run", None, "KO-ray", 2))
    # body: white, shaded flank (cream, zig-zag), grey edge toward the tail on the shaded side
    regs.append(R("kb_white", body, "satin", "auto", "KO", 3))
    shade = body.intersection(Polygon([(X(s), spine(s) + h(s)*(0.58 + (0.12 if i % 2 else -0.06))) for i, s in enumerate(ss)] + [(X(s), spine(s) + 50) for s in ss[::-1]]).buffer(0))
    tailshade = body.intersection(Polygon([(X(0.60) - 300, -60), (X(0.60), -60)] + [(X(0.60) + (0.8 if i % 2 else -0.8), yy) for i, yy in enumerate(np.linspace(-60, 60, 160))] + [(X(0.60) - 300, 60)]).buffer(0))
    regs.append(R("kb_cream", unary_union([shade, tailshade]).buffer(0), "satin", "auto", "KO-shade", 4))
    # red patches (kohaku)
    pat = RED_PATTERNS[pattern % len(RED_PATTERNS)]; reds = []
    for a0, a1, off in pat:
        sc = (a0 + a1)/2; hl = (a1 - a0)*L/2*1.08; hw = h(sc)*0.66
        pts = []
        for k in range(28):
            th = 2*math.pi*k/28; rr = 1 + 0.07*math.sin(3*th + rng.uniform(0, 6)) + rng.uniform(-0.03, 0.03)
            pts.append((X(sc) + hl*math.cos(th)*rr, spine(sc) + off*W + hw*math.sin(th)*rr))
        reds.append(Polygon(pts).buffer(0))
    red = unary_union(reds).intersection(body.buffer(-0.7))
    regs.append(R("kb_red", red, "satin", "auto", "KO-red", 5))
    # head: lighter snout + eyes
    eyes = unary_union([Point(X(0.085), spine(0.085) + sg*h(0.085)*0.60).buffer(0.80) for sg in (-1, 1)])
    regs.append(R("kb_ink", eyes, "satin", "auto", "KO-eye", 6))
    sil = unary_union([r["geom"] for r in regs]).buffer(0.3)
    out = []
    for r in regs:
        g = T(r["geom"], cx, cy, ang)
        a_ = r["ang"]
        if isinstance(a_, tuple):
            p = T(Point(a_[1], a_[2]), cx, cy, ang); a_ = ("radial", p.x, p.y)
        elif isinstance(a_, (int, float)): a_ = a_ + ang
        out.append(dict(r, geom=g, ang=a_, unit=unit))
    return out, T(sil, cx, cy, ang)

# ================================================================ lily / clematis flower
FTONES = {  # base, lit half, shade half, lit tip, shade tip, highlight streak
    "pale":  ("kb_royal", "kb_ice", "kb_sky", "kb_white", "kb_white", "kb_white"),
    "light": ("kb_royal", "kb_sky", "kb_blue", "kb_ice", "kb_sky", "kb_white"),
    "mid":   ("kb_cobalt", "kb_sky", "kb_royal", "kb_ice", "kb_blue", "kb_ice"),
    "dark":  ("kb_navy", "kb_blue", "kb_cobalt", "kb_sky", "kb_royal", "kb_sky"),
}
TONES = {   # base, mid, tip, rim highlight
    "light": ("kb_royal", "kb_sky", "kb_ice", "kb_white"),
    "mid":   ("kb_cobalt", "kb_blue", "kb_sky", "kb_ice"),
    "dark":  ("kb_navy", "kb_cobalt", "kb_royal", "kb_sky"),
    "pale":  ("kb_royal", "kb_ice", "kb_white", "kb_sky"),
}

def petal_shape(Lp, Wp, r0=0.0, curl=0.0, tip_pow=0.85):
    t = np.linspace(0, 1, 40)
    half = Wp/2 * np.sin(np.pi * np.clip(t, 0, 1)**tip_pow)**0.6
    half[0] = Wp*0.12
    xs = r0 + t*Lp; cy = curl * t**2 * Lp
    return Polygon(np.r_[np.c_[xs, cy - half], np.c_[xs, cy + half][::-1]]).buffer(0)

def flower(cx, cy, Rr, rot, rng, tones="light", n=6, cup=True, unit=None, petal_w=0.62, lens=None):
    """open lily (close-up): n ovate pointed petals arranged unevenly, each split on its midrib into a lit half and a shade
    half (the close-up's two-tone petals, stitched feathered at +-40 deg to the midrib), a darker base step and a lit tip
    step (zig-zag long-and-short boundaries), a highlight streak on the lit half; centre = navy eye with radiating cream
    stamen dashes on a dark cup."""
    base_c, lit_c, shade_c, lit_tip, shade_tip, rim_c = FTONES[tones]
    regs = []; sils = []
    order = list(range(n)); rng.shuffle(order)
    gaps = [rng.uniform(0.6, 1.4) for _ in range(n)]; tot = sum(gaps); acc = 0.0; angs = []
    for gp in gaps: angs.append(rot + 360.0*acc/tot); acc += gp
    for z, k in enumerate(order):
        a = angs[k]
        Lp = Rr * (lens[k] if lens else rng.uniform(0.68, 1.08)); Wp = Rr*petal_w*rng.uniform(0.78, 1.25)
        curl = rng.uniform(-0.16, 0.16); r0 = Rr*0.05
        p = petal_shape(Lp, Wp, r0, curl)
        sd = 1 if rng.random() < 0.5 else -1
        mid = [(r0 + Lp*t, curl*(t**2)*Lp) for t in np.linspace(0, 1, 20)]
        lit = p.intersection(Polygon(mid + [(r0 + Lp + 5, sd*60), (r0 - 5, sd*60)]).buffer(0))
        shd = p.difference(lit)
        b1 = jag_cut(lambda y: r0 + Lp*0.30, 0, Lp*0.05, -Wp, Wp, period=1.7, rng=rng)
        b2 = jag_cut(lambda y: r0 + Lp*0.74, 0, Lp*0.04, -Wp, Wp, period=1.7, rng=rng)
        base = p.intersection(b1); tipz = p.difference(b2)
        streak = line_poly([(r0 + Lp*0.40, curl*0.16*Lp + sd*Wp*0.20), (r0 + Lp*0.78, curl*0.6*Lp + sd*Wp*0.12)], max(1.0, Wp*0.07)).intersection(lit.buffer(-0.5))
        fa = sd * 40.0
        parts = [(base_c, base.intersection(lit), "FL-base", a + fa), (base_c, base.intersection(shd), "FL-base", a - fa),
                 (lit_c, lit.difference(base).difference(tipz), "FL-petal", a + fa), (shade_c, shd.difference(base).difference(tipz), "FL-petal", a - fa),
                 (lit_tip, tipz.intersection(lit), "FL-tip", a + fa), (shade_tip, tipz.intersection(shd), "FL-tip", a - fa)]
        for col, g, grp, an in parts:
            g = g.difference(streak).buffer(0)
            if not g.is_empty: regs.append(dict(col=col, geom=T(g, cx, cy, a), st="satin", ang=an, grp=grp, sub=10 + 3*z))
        if not streak.is_empty and streak.area > 0.8 and Lp > 12:
            regs.append(dict(col=rim_c, geom=T(streak, cx, cy, a), st="satin", ang=a + fa, grp="FL-hl", sub=11 + 3*z))
        sils.append(T(p, cx, cy, a))
    eye = Point(cx, cy).buffer(Rr*0.10)
    regs.append(dict(col="kb_navy", geom=eye, st="satin", ang=("radial", cx, cy), grp="FL-eye", sub=70))
    if cup:
        dashes = []
        for k in range(8):
            a = math.radians(rot + 45*k + rng.uniform(-8, 8)); r1 = Rr*rng.uniform(0.22, 0.30)
            dashes.append(line_poly([(cx + Rr*0.11*math.cos(a), cy + Rr*0.11*math.sin(a)), (cx + r1*math.cos(a), cy + r1*math.sin(a))], max(1.4, Rr*0.07)))
        st_u = unary_union(dashes).difference(eye.buffer(-Rr*0.03))
        regs.append(dict(col="kb_white", geom=st_u, st="satin", ang=("radial", cx, cy), grp="FL-stamen", sub=72))
        cupz = Point(cx, cy).buffer(Rr*0.25).difference(st_u).difference(eye)
        regs.append(dict(col=base_c if tones != "dark" else "kb_royal", geom=cupz, st="satin", ang=("radial", cx, cy), grp="FL-cup", sub=69))
    for r in regs: r["unit"] = unit; r["geom"] = r["geom"].buffer(0)
    return regs, unary_union(sils + [eye]).buffer(0.3)

# ================================================================ leaves, stems, floating petals
LEAF_TONES = {"ice": ("kb_ice", "kb_sky", "kb_white"), "sky": ("kb_sky", "kb_blue", "kb_ice"), "blue": ("kb_blue", "kb_royal", "kb_sky"),
              "royal": ("kb_royal", "kb_cobalt", "kb_blue"), "cobalt": ("kb_cobalt", "kb_navy", "kb_royal"), "navy": ("kb_navy", "kb_navy", "kb_cobalt")}

def leaf_poly(L, W, bend=0.0, n=48):
    t = np.linspace(0, 1, n)
    half = W/2 * (np.sin(np.pi * t**0.9)**0.9)
    cyy = bend * L * (t - t**2) * 2
    top = np.c_[t*L, cyy - half]; bot = np.c_[t*L, cyy + half]
    return Polygon(np.r_[top, bot[::-1]]).buffer(0), LineString(np.c_[t*L, cyy][4:-4])

def leaf(x, y, L, ang, rng, tone="blue", bend=0.0, W=None, unit=None, vein=True):
    """lanceolate leaf from its base (x, y) toward `ang`: light half + shade half split on the midrib, a lit tip
    step (zig-zag), midrib run on top for leaves > 14 mm."""
    W = W or L*rng.uniform(0.28, 0.36)
    lt, dk, tp = LEAF_TONES[tone]
    p, mid = leaf_poly(L, W, bend)
    up = p.intersection(Polygon([(-1, -50)] + [(c[0], c[1]) for c in mid.coords] + [(L + 1, -50)]).buffer(0))
    if up.is_empty or up.area < 0.1:
        up = p.intersection(Polygon([(-1, -50), (L+1, -50), (L+1, 0), (-1, 0)]))
    lo = p.difference(up)
    tipcut = p.difference(jag_cut(lambda yy: L*0.72, 0, L*0.04, -W, W, 1.5, rng=rng))
    light, shade = (up, lo) if rng.random() < 0.5 else (lo, up)
    regs = [R(lt, light.difference(tipcut), "satin", "auto", "LF", 0), R(dk, shade.difference(tipcut), "satin", "auto", "LF-dk", 0),
            R(tp, tipcut.intersection(light).buffer(0), "satin", "auto", "LF-tip", 1), R(lt, tipcut.intersection(shade).buffer(0), "satin", "auto", "LF-tip", 1)]
    if vein and L > 14:
        regs.append(R(tp if tone in ("cobalt", "navy", "royal") else dk, mid.buffer(0.32).intersection(p.buffer(-0.5)).intersection(Point(0, 0).buffer(L*0.8)), "run", None, "LF-vein", 2))
    out = [dict(r, geom=T(r["geom"], x, y, ang), unit=unit) for r in regs if not r["geom"].is_empty]
    return out, T(p, x, y, ang)

def stem(pts, w0, w1, col="kb_navy", unit=None):
    """tapered curved stem through pts (catmull), width w0 -> w1 (mm)"""
    sm = catmull(pts, 8)
    rr = taper(sm, w0/2, w1/2)
    poly, _ = sweep(rr)
    poly = poly.buffer(0)
    return [dict(col=col, geom=poly, st="satin", ang="auto", grp="ST", sub=0, unit=unit)], poly

def float_petal(x, y, L, ang, rng, tone="sky", unit=None, curl=None):
    """floating petal: almond with a pointed tip and a thin tail, two tones split lengthwise (zig-zag)."""
    W = L*rng.uniform(0.36, 0.46)
    curl = rng.uniform(-0.12, 0.12) if curl is None else curl
    t = np.linspace(0, 1, 36)
    half = W/2 * np.sin(np.pi * t**1.25)**0.8
    cyy = curl * L * (t**2)
    p = Polygon(np.r_[np.c_[t*L, cyy - half], np.c_[t*L, cyy + half][::-1]]).buffer(0)
    lt, dk, tp = LEAF_TONES[tone]
    split = jag_cut(lambda yy: L*0.0, 0, 0, -W, W)          # placeholder
    sd = 1 if rng.random() < 0.5 else -1
    half_poly = Polygon([(-1, 0), (L + 1, 0), (L + 1, sd*50), (-1, sd*50)])
    zig = []
    for i, xx in enumerate(np.linspace(L*0.12, L*0.95, 12)):
        zig.append((xx, curl*L*(xx/L)**2 + (0.35 if i % 2 else -0.35)))
    hp = Polygon([(-1, 0)] + zig + [(L + 1, 0), (L + 1, sd*50), (-1, sd*50)]).buffer(0)
    a_ = p.intersection(hp); b_ = p.difference(hp)
    regs = [R(lt, b_, "satin", "auto", "PT", 0), R(tp if tone in ("ice", "sky") else dk, a_, "satin", "auto", "PT-tone", 0)]
    if L >= 12:
        tail = line_poly([(-L*0.18, curl*L*0.02), (L*0.06, 0)], 0.9)
        regs.append(R(dk if tone != "navy" else "kb_cobalt", tail, "satin", "auto", "ST", 0))
    out = [dict(r, geom=T(r["geom"], x, y, ang), unit=unit) for r in regs if not r["geom"].is_empty]
    return out, T(p, x, y, ang)
