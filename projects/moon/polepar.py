"""Rev C (final) pole (LESSONS A13, review item 5): the close-up's hardware as clean stitch objects at the positions read
off the close-ups (2x grid crops, px), mapped to mm by f (back: the moon registration, one uniform scale for the whole
back close-up; front: closeart.front_pole_f).
 pole body   — tatami ALONG the pole (wood fibre) in pole grey, charcoal satin outline both edges, broken light-grey bark
               highlights left of centre, dark-grey shade strip right, bark grain = short charcoal runs + crack dashes
 ring clamps — curved charcoal satin bands (cylinder perspective: the band sags 1.2 mm at the centre) that overhang the
               pole, a light run along the top edge
 crossarm    — satin along the arm, light top edge, charcoal underside run, clamp bands + bolts, two braces
 pin insulators — shaped bells: 3 skirts widening downward (light / grey alternating), stem + cap knob
 coil insulators — spool cylinder (lid ellipses, highlight) + the wire wrapped round it as overlapping loops (satin rings
               with a charcoal shade run); the cone insulator tapers in ribs to a knob
 drum transformer — clean vertical slats (satin columns, light/grey alternating, dark-grey gaps), curved charcoal rings,
               lid + dark bottom ellipse
 small can   — cylinder: grey body, light strip, shade side, lid ellipse, curved rings, hook"""
import math
import numpy as np
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union, transform
from shapely import affinity
from motifs2 import R

def M(g, f): return transform(lambda x, y, z=None: f(np.asarray(x), np.asarray(y)), g).buffer(0)
def ML(g, f): return transform(lambda x, y, z=None: f(np.asarray(x), np.asarray(y)), g)

def arc_band(x0, x1, y, h, sag):
    """band between two parallel arcs from x0 to x1 (px), centre sagging by sag (cylinder ring seen from slightly above)"""
    xs = np.linspace(x0, x1, 17); t = (xs - x0) / (x1 - x0); dy = sag * 4 * t * (1 - t)
    top = [(x, y - h / 2 + d) for x, d in zip(xs, dy)]; bot = [(x, y + h / 2 + d) for x, d in zip(xs[::-1], dy[::-1])]
    return Polygon(top + bot)
def arc_line(x0, x1, y, sag):
    xs = np.linspace(x0, x1, 17); t = (xs - x0) / (x1 - x0); return LineString([(x, y + sag * 4 * u * (1 - u)) for x, u in zip(xs, t)])

def body(f, x0, x1, ytop, ybot, bands, out, flare=1.04, seed=4):
    w0 = x1 - x0; cx = (x0 + x1) / 2; wb = w0 * flare
    X = lambda fr, y: cx + (fr - 0.5) * (w0 + (wb - w0) * (y - ytop) / max(1, ybot - ytop))
    poly = Polygon([(X(0, ytop), ytop), (X(1, ytop), ytop), (X(1, ybot), ybot), (X(0, ybot), ybot)])
    out.append(R("p2", M(poly, f), "tatami", 90, "PL"))                                   # fibre along the pole
    out.append(R("p3", M(Polygon([(X(.74, ytop), ytop), (X(.94, ytop), ytop), (X(.94, ybot), ybot), (X(.74, ybot), ybot)]), f), "tatami", 90, "PL-shade"))
    rng = np.random.RandomState(seed)
    y = ytop + 4                                                                              # broken bark highlights
    while y < ybot - 6:
        L = rng.uniform(10, 26); fr0 = rng.uniform(0.16, 0.26); fr1 = fr0 + rng.uniform(0.12, 0.22)
        q = Polygon([(X(fr0, y), y), (X(fr1, y + 2), y + 2), (X(fr1 + 0.03, y + L), y + L), (X(fr0 + 0.02, y + L - 2), y + L - 2)])
        out.append(R("p1", M(q, f), "satin", 0, "PL-hl"))
        y += L + rng.uniform(4, 12)
    for side in (0, 1):                                                                       # charcoal outline
        ln = LineString([(X(side, ytop), ytop), (X(side, ybot), ybot)])
        out.append(R("p4", M(ln.buffer(1.6, cap_style="flat"), f), "satin", "auto", "PL-band"))
    y = ytop + 6                                                                              # grain + cracks
    while y < ybot - 8:
        for k in range(3):
            fr = rng.uniform(0.3, 0.85); L = rng.uniform(5, 16)
            ln = LineString([(X(fr, y), y), (X(fr + rng.uniform(-0.04, 0.04), y + L), y + L)])
            out.append(R("p4", ML(ln, f).buffer(0.3), "run", None, "PL-line"))
        if rng.rand() < 0.6:
            fr = rng.uniform(0.35, 0.7); yy = y + rng.uniform(0, 8)
            ln = LineString([(X(fr, yy), yy), (X(fr + 0.12, yy + 1.5), yy + 1.5), (X(fr + 0.2, yy + 0.5), yy + 0.5)])
            out.append(R("p4", ML(ln, f).buffer(0.3), "run", None, "PL-line"))
        y += rng.uniform(12, 20)
    for yb in bands:                                                                          # ring clamps
        xa, xb = X(0, yb) - 3, X(1, yb) + 3
        out.append(R("p4", M(arc_band(xa, xb, yb, 9, 3.5), f), "satin", 90, "PL-band"))
        out.append(R("p1", ML(arc_line(xa + 2, xb - 2, yb - 3.2, 3.5), f).buffer(0.3), "run", None, "PL-line"))
    return out

def cap(f, cx, ytop, w, out):
    for dy, ww, col in ((0, 0.62, "p2"), (12, 0.86, "p3"), (24, 1.04, "p2"), (40, 1.10, "p4")):
        out.append(R(col, M(affinity.scale(Point(cx, ytop + dy + 6).buffer(1, 24), w * ww / 2, 6.5), f), "satin", "auto", "PL-band" if col == "p4" else "PL"))
    return out

def crossarm(f, p0, p1, w, bolts, out):
    arm = LineString([p0, p1]).buffer(w / 2, cap_style="flat")
    out.append(R("p2", M(arm, f), "satin", "auto", "PL"))
    out.append(R("p1", M(LineString([p0, p1]).parallel_offset(w * 0.28, "left").buffer(w * 0.14, cap_style="flat").intersection(arm), f), "satin", "auto", "PL-hl"))
    out.append(R("p4", ML(LineString([p0, p1]).parallel_offset(w * 0.42, "right"), f).buffer(0.3), "run", None, "PL-line"))
    v = np.array(p1, float) - p0; u = v / np.linalg.norm(v); n = np.array([-u[1], u[0]])
    for bx, by in bolts:                                                                     # clamp band + bolt head
        c = np.array([bx, by]); q = Polygon([tuple(c - u * 4 - n * w * 0.62), tuple(c + u * 4 - n * w * 0.62), tuple(c + u * 4 + n * w * 0.62), tuple(c - u * 4 + n * w * 0.62)])
        out.append(R("p4", M(q, f), "satin", "auto", "PL-band"))
        out.append(R("p1", M(Point(bx, by).buffer(2.4, 12), f), "satin", "auto", "PL-hl"))
    return out

def pin(f, x, ybase, h, w, out):
    out.append(R("p4", M(box(x - w * 0.12, ybase - h * 0.25, x + w * 0.12, ybase + 3), f), "satin", 90, "PL-band"))
    for k in range(3):                                                                        # bell skirts, widening down
        yb = ybase - h * (0.22 + 0.25 * k); ww = w * (1.0 - 0.16 * k); hh = h * 0.17
        q = Polygon([(x - ww * 0.30, yb - hh), (x + ww * 0.30, yb - hh), (x + ww / 2, yb), (x - ww / 2, yb)])
        q = q.union(affinity.scale(Point(x, yb).buffer(1, 20), ww / 2, hh * 0.25))
        out.append(R("p2" if k % 2 == 0 else "p3", M(q, f), "satin", 90, "PL" if k % 2 == 0 else "PL-shade"))
        out.append(R("p1", ML(LineString([(x - ww * 0.28, yb - hh + 1.2), (x + ww * 0.1, yb - hh + 1.2)]), f).buffer(0.3), "run", None, "PL-line"))
        out.append(R("p4", ML(LineString([(x - ww / 2, yb), (x + ww / 2, yb)]), f).buffer(0.3), "run", None, "PL-line"))
    out.append(R("p2", M(Point(x, ybase - h * 0.94).buffer(w * 0.16, 16), f), "satin", "auto", "PL"))
    return out

def spool(f, x0, x1, yc, d, out):
    """horizontal spool cylinder x0..x1 (px) centred on yc, diameter d"""
    out.append(R("p2", M(box(x0, yc - d / 2, x1, yc + d / 2), f), "satin", 90, "PL"))
    out.append(R("p1", M(box(x0 + 2, yc - d * 0.34, x1 - 2, yc - d * 0.14), f), "satin", 0, "PL-hl"))
    for xe in (x0, x1):
        out.append(R("p4", M(affinity.scale(Point(xe, yc).buffer(1, 24), 3.2, d / 2), f), "satin", "auto", "PL-band"))
    return out

def coil(f, p0, p1, n, d, out, taper=0.0):
    """wire wrapped round a rod p0 -> p1 (close-up): a dark-grey rod, then n slanted wraps across it, each a satin band
    (light / grey alternating) bulging slightly forward, with a charcoal shade run along its trailing edge"""
    v = np.array(p1, float) - p0; L = np.linalg.norm(v); u = v / L; nrm = np.array([-u[1], u[0]])
    out.append(R("p3", M(LineString([p0, p1]).buffer(d * 0.30, cap_style="flat"), f), "satin", "auto", "PL-shade"))
    step = L / n
    for k in range(n):
        dk = d * (1 - taper * k / max(1, n - 1)); c = np.array(p0) + u * step * (k + 0.5)
        a = c - u * step * 0.38 - nrm * dk / 2; b = c + u * step * 0.38 + nrm * dk / 2          # slanted wrap
        mid = (a + b) / 2 + u * step * 0.12
        ln = LineString([tuple(a), tuple(mid), tuple(b)])
        w = max(2.2 / 0.436, step * 0.55)
        out.append(R("p1" if k % 2 == 0 else "p2", M(ln.buffer(w / 2, cap_style="round"), f), "satin", "auto", "PL-hl" if k % 2 == 0 else "PL"))
        out.append(R("p4", ML(ln.parallel_offset(w * 0.45, "right"), f).buffer(0.3), "run", None, "PL-line"))
    return out

def drum(f, x0, x1, y0, y1, rings, out, slat=8.5):
    out.append(R("p3", M(box(x0, y0, x1, y1), f), "tatami", 90, "PL-shade"))
    for i, xs in enumerate(np.arange(x0 + 2, x1 - 3, slat)):                                   # clean vertical slats
        sag = 3.0 * 4 * ((xs + slat * 0.3 - x0) / (x1 - x0)) * (1 - (xs + slat * 0.3 - x0) / (x1 - x0))
        q = box(xs, y0 + 5 + sag, xs + slat * 0.62, y1 - 5 + sag)
        out.append(R("p2", M(q, f), "satin", 0, "PL"))                    # slats grey on the dark-grey drum (close-up)
        if xs < x0 + (x1 - x0) * 0.45:                                       # light side: a highlight run on each slat
            out.append(R("p1", ML(LineString([(xs + slat * 0.18, y0 + 9 + sag), (xs + slat * 0.18, y1 - 9 + sag)]), f).buffer(0.3), "run", None, "PL-line"))
    for yr in [y0 + 3] + list(rings):
        out.append(R("p4", M(arc_band(x0 - 3, x1 + 3, yr, 7, 3.0), f), "satin", 90, "PL-band"))
    out.append(R("p4", M(affinity.scale(Point((x0 + x1) / 2, y1).buffer(1, 32), (x1 - x0) / 2 + 2, 7), f), "satin", "auto", "PL-band"))
    return out

def can(f, x0, x1, y0, y1, out):
    cx = (x0 + x1) / 2
    out.append(R("p2", M(box(x0, y0 + 6, x1, y1), f), "tatami", 90, "PL"))
    out.append(R("p3", M(box(x0 + (x1 - x0) * .72, y0 + 6, x1, y1), f), "satin", 0, "PL-shade"))
    out.append(R("p1", M(box(x0 + (x1 - x0) * .14, y0 + 12, x0 + (x1 - x0) * .30, y1 - 8), f), "satin", 0, "PL-hl"))
    out.append(R("p1", M(affinity.scale(Point(cx, y0 + 6).buffer(1, 32), (x1 - x0) / 2 + 2, 6), f), "satin", "auto", "PL-hl"))
    for yr in (y0 + 18, y1 - 12):
        out.append(R("p4", M(arc_band(x0 - 2, x1 + 2, yr, 6, 2.5), f), "satin", 90, "PL-band"))
    out.append(R("p4", M(affinity.scale(Point(cx, y1).buffer(1, 24), (x1 - x0) / 2, 4), f), "satin", "auto", "PL-band"))
    out.append(R("p4", M(LineString([(cx, y0), (cx, y0 - 8)]).buffer(1.8), f), "satin", "auto", "PL-band"))     # hook
    return out

def cone(f, p0, p1, n, d0, d1, out):
    """cone insulator from p0 (base, at the pole block) to p1 (tip): n ribs tapering d0 -> d1"""
    v = np.array(p1, float) - p0; L = np.linalg.norm(v); u = v / L; ang = math.degrees(math.atan2(u[1], u[0]))
    for k in range(n):
        c = np.array(p0) + u * L * (k + 0.5) / n; dk = d0 + (d1 - d0) * k / max(1, n - 1)
        e = affinity.rotate(affinity.scale(Point(*c).buffer(1, 24), L / n * 0.55, dk / 2), ang, origin=tuple(c))
        out.append(R("p1" if k % 2 == 0 else "p2", M(e, f), "satin", "auto", "PL-hl" if k % 2 == 0 else "PL"))
    out.append(R("p2", M(Point(*p1).buffer(d1 * 0.5, 16), f), "satin", "auto", "PL"))
    return out

def bracket(f, p0, p1, out, w=4.0):
    out.append(R("p4", M(LineString([p0, p1]).buffer(w / 2, cap_style="flat"), f), "satin", "auto", "PL-band"))
    return out

def back(f, ybot=1086):
    o = []
    body(f, 697, 757, 492, ybot, [530, 602, 680, 725, 818, 945], o)
    cap(f, 727, 486, 62, o)
    crossarm(f, (583, 660), (697, 632), 15, [(630, 648)], o)                         # left of the pole
    crossarm(f, (757, 618), (940, 586), 15, [(785, 613), (828, 606), (898, 594)], o)  # right of the pole
    bracket(f, (628, 672), (697, 645), o)          # (790,612)->(762,672) is a WIRE in the close-up (light cord): scene.back_art
    pin(f, 828, 598, 66, 26, o); pin(f, 900, 588, 70, 26, o)
    drum(f, 760, 858, 672, 858, [700, 745, 790, 837], o)
    can(f, 625, 690, 760, 885, o); bracket(f, (660, 752), (697, 752), o, 5)
    spool(f, 500, 542, 775, 44, o)
    # Rev C (task 3, measured on the close-up, out/_wip/measure.py + 4x zooms): the main coil is 5 big loops next to the
    # spool, then ~9 small wraps along the rod to the pole (was 9 equal loops); left coil 5 small wraps (was 4)
    coil(f, (542, 768), (592, 760), 5, 30, o)
    coil(f, (592, 760), (690, 744), 9, 14, o)
    coil(f, (457, 775), (500, 772), 5, 15, o)
    o.append(R("p2", M(box(765, 912, 800, 958), f), "tatami", 90, "PL"))             # cone insulator block on the pole
    o.append(R("p4", M(box(795, 912, 801, 958), f), "satin", 90, "PL-band"))
    cone(f, (802, 935), (866, 952), 9, 30, 12, o)                                     # 9 ribs (measured pitch 7.4 px)
    return o

def front(f):
    o = []
    body(f, 1212, 1262, 560, 1020, [610, 695, 741, 820, 920], o)                     # bands measured (was 608/700/795/860)
    cap(f, 1237, 512, 46, o)
    crossarm(f, (1105, 668), (1212, 640), 13, [(1140, 660)], o)
    crossarm(f, (1262, 627), (1355, 600), 13, [(1300, 616)], o)
    bracket(f, (1160, 660), (1212, 720), o)
    pin(f, 1316, 606, 62, 22, o)
    drum(f, 1268, 1345, 690, 860, [726, 763, 800], o, slat=6.6)                      # slat pitch + rings measured (was 7.5; 720/765/810)
    can(f, 1150, 1206, 780, 900, o); bracket(f, (1178, 772), (1212, 772), o, 5)
    spool(f, 990, 1040, 787, 36, o)
    coil(f, (1040, 782), (1088, 777), 4, 26, o)                                      # 4 big loops, then ~9 small wraps (4x zoom)
    coil(f, (1088, 777), (1202, 767), 9, 12, o)
    coil(f, (950, 788), (990, 787), 6, 12, o)                                         # 6 small wraps (was 3)
    o.append(R("p2", M(box(1262, 890, 1292, 930), f), "tatami", 90, "PL"))
    cone(f, (1294, 912), (1350, 928), 7, 26, 10, o)                                   # 7 ribs to x 1350, then the wire (was 8 to 1370)
    return o
