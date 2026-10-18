"""Rev C pole (LESSONS A13): the close-up's hardware drawn as clean stitch objects at the positions read off the
close-ups (grid crops, px), mapped to mm by the pole's registration f (closeart):
 pole body   — horizontal grain satin rows (pole grey) with a light strip + a shade strip, wood-grain runs, charcoal ring
               clamps (bands) at the close-up's band heights, ornamental cap stack at the top
 crossarm    — satin along the arm, light top edge, bolts + brace
 insulators  — pin insulators as 3 stacked discs on a stem; coiled string insulators as overlapping ellipses
 transformer — ribbed drum: vertical slats (alternating grey / dark grey satin columns) + charcoal rings + lid ellipse;
               small can: cylinder with lid, side shade and 2 rings"""
import math
import numpy as np
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union, transform
from shapely import affinity
from motifs2 import R

def M(g, f): return transform(lambda x, y, z=None: f(np.asarray(x), np.asarray(y)), g).buffer(0)

def body(f, x0, x1, ytop, ybot, bands, out, flare=1.05):
    w0 = x1 - x0; cx = (x0 + x1) / 2
    poly = Polygon([(x0, ytop), (x1, ytop), (cx + w0 / 2 * flare, ybot), (cx - w0 / 2 * flare, ybot)])
    out.append(R("p2", M(poly, f), "satin", 0, "PL"))                                 # horizontal grain rows
    out.append(R("p1", M(Polygon([(x0 + w0 * .12, ytop), (x0 + w0 * .30, ytop), (cx - w0 * .2 * flare, ybot), (cx - w0 * .38 * flare, ybot)]), f), "satin", 0, "PL-hl"))
    out.append(R("p3", M(Polygon([(x0 + w0 * .76, ytop), (x1, ytop), (cx + w0 / 2 * flare, ybot), (cx + w0 * .26 * flare, ybot)]), f), "satin", 0, "PL-shade"))
    rng = np.random.RandomState(4)
    for yy in np.arange(ytop + 8, ybot - 6, 11.0):                                     # grain: short horizontal runs
        for k in range(2):
            xa = x0 + w0 * rng.uniform(0.15, 0.6); L = w0 * rng.uniform(0.15, 0.35)
            ln = LineString([(xa, yy + rng.uniform(-3, 3)), (xa + L, yy + rng.uniform(-3, 3))])
            out.append(R("p4", M(ln, f).buffer(0.3), "run", None, "PL-line"))
    for yb in bands:                                                                   # ring clamps
        out.append(R("p4", M(box(x0 - 3, yb - 4, x1 + 3, yb + 4), f), "satin", 90, "PL-band"))
        out.append(R("p1", M(box(x0 - 1, yb - 4, x1 + 1, yb - 2), f), "satin", 90, "PL-hl"))
    return out

def cap(f, cx, ytop, w, out):
    for k, (dy, ww, col) in enumerate(((0, 0.55, "p2"), (14, 0.8, "p3"), (26, 1.0, "p2"), (44, 1.05, "p4"))):
        out.append(R(col, M(Point(cx, ytop + dy).buffer(1, 24), f).buffer(0) if False else M(affinity.scale(Point(cx, ytop + dy + 6).buffer(1, 24), w * ww / 2, 7), f), "satin", "auto", "PL-band" if col == "p4" else "PL"))
    return out

def crossarm(f, p0, p1, w, bolts, out):
    arm = LineString([p0, p1]).buffer(w / 2, cap_style="flat")
    out.append(R("p2", M(arm, f), "satin", "auto", "PL"))
    out.append(R("p1", M(LineString([p0, p1]).parallel_offset(w * 0.3, "left").buffer(w * 0.14, cap_style="flat").intersection(arm), f), "satin", "auto", "PL-hl"))
    for bx, by in bolts:
        out.append(R("p4", M(Point(bx, by).buffer(w * 0.42, 16), f), "satin", "auto", "PL-band"))
    return out

def pin(f, x, ybase, h, w, out):
    out.append(R("p4", M(box(x - w * 0.12, ybase - h * 0.3, x + w * 0.12, ybase + 2), f), "satin", 90, "PL-band"))
    for k in range(3):
        yc = ybase - h * (0.25 + 0.27 * k); ww = w * (1.0 - 0.18 * k)
        e = affinity.scale(Point(x, yc).buffer(1, 24), ww / 2, h * 0.11)
        out.append(R("p1" if k % 2 == 0 else "p2", M(e, f), "satin", "auto", "PL-hl" if k % 2 == 0 else "PL"))
    out.append(R("p2", M(Point(x, ybase - h * 0.98).buffer(w * 0.18, 16), f), "satin", "auto", "PL"))
    return out

def coil(f, p0, p1, n, d, out):
    v = np.array(p1, float) - p0; L = np.linalg.norm(v); u = v / L; ang = math.degrees(math.atan2(u[1], u[0]))
    out.append(R("p4", M(LineString([p0, p1]).buffer(d * 0.12, cap_style="flat"), f), "satin", "auto", "PL-band"))
    for k in range(n):
        c = np.array(p0) + u * L * (k + 0.5) / n
        e = affinity.rotate(affinity.scale(Point(*c).buffer(1, 24), L / n * 0.55, d / 2), ang, origin=tuple(c))
        out.append(R("p1" if k % 2 == 0 else "p2", M(e, f), "satin", "auto", "PL-hl" if k % 2 == 0 else "PL"))
    return out

def drum(f, x0, x1, y0, y1, rings, out, slat=8.0):
    out.append(R("p3", M(box(x0, y0, x1, y1), f), "satin", 90, "PL-shade"))
    for xs in np.arange(x0 + 2, x1 - 2, slat):                                          # clean vertical slats
        out.append(R("p2" if int((xs - x0) / slat) % 2 == 0 else "p1", M(box(xs, y0 + 4, xs + slat * 0.55, y1 - 4), f), "satin", 0, "PL"))
    for yr in [y0] + list(rings) + [y1]:
        out.append(R("p4", M(box(x0 - 3, yr - 3.5, x1 + 3, yr + 3.5), f), "satin", 90, "PL-band"))
    out.append(R("p4", M(affinity.scale(Point((x0 + x1) / 2, y1).buffer(1, 32), (x1 - x0) / 2, 7), f), "satin", "auto", "PL-band"))
    return out

def can(f, x0, x1, y0, y1, out):
    out.append(R("p2", M(box(x0, y0 + 6, x1, y1), f), "satin", 0, "PL"))
    out.append(R("p3", M(box(x0 + (x1 - x0) * .72, y0 + 6, x1, y1), f), "satin", 0, "PL-shade"))
    out.append(R("p1", M(box(x0 + (x1 - x0) * .12, y0 + 10, x0 + (x1 - x0) * .26, y1 - 6), f), "satin", 0, "PL-hl"))
    out.append(R("p1", M(affinity.scale(Point((x0 + x1) / 2, y0 + 6).buffer(1, 32), (x1 - x0) / 2 + 2, 6), f), "satin", "auto", "PL-hl"))
    for yr in (y0 + 20, y1 - 14):
        out.append(R("p4", M(box(x0 - 2, yr - 3, x1 + 2, yr + 3), f), "satin", 90, "PL-band"))
    return out

def bracket(f, p0, p1, out, w=4.0):
    out.append(R("p4", M(LineString([p0, p1]).buffer(w / 2, cap_style="flat"), f), "satin", "auto", "PL-band"))
    return out

def back(f, ybot=1086):
    o = []
    body(f, 697, 753, 492, ybot, [528, 599, 673, 748, 815, 957], o)
    cap(f, 725, 486, 60, o)
    crossarm(f, (578, 645), (945, 588), 13, [(612, 640), (840, 604), (905, 594)], o)
    bracket(f, (650, 640), (700, 700), o); bracket(f, (800, 610), (752, 690), o)
    pin(f, 828, 590, 70, 26, o); pin(f, 898, 580, 74, 26, o)
    drum(f, 760, 860, 672, 860, [699, 744, 789, 840], o)
    can(f, 625, 690, 752, 885, o); bracket(f, (690, 780), (697, 780), o, 6)
    coil(f, (690, 742), (530, 762), 9, 22, o); coil(f, (530, 762), (440, 778), 6, 26, o)
    coil(f, (753, 935), (875, 958), 8, 24, o)
    return o

def front(f):
    o = []
    body(f, 1212, 1262, 560, 1020, [608, 700, 795, 860], o)
    cap(f, 1237, 512, 44, o)
    crossarm(f, (1105, 668), (1355, 600), 12, [(1140, 660), (1300, 616)], o)
    bracket(f, (1160, 660), (1212, 720), o)
    pin(f, 1316, 600, 62, 22, o)
    drum(f, 1268, 1345, 690, 860, [720, 765, 810], o, slat=7.0)
    can(f, 1150, 1206, 780, 900, o)            # can + string insulator 20 px (7 mm) lower than the close-up: clear of the welt
    coil(f, (1212, 772), (1100, 780), 8, 20, o); coil(f, (1100, 780), (960, 785), 7, 24, o)
    coil(f, (1262, 905), (1370, 935), 7, 22, o)
    return o
