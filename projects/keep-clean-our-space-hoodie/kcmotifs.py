"""Motifs for the Keep Clean Our Space jacket (neon badges + star field). Regions: dict(col, geom, st, ang, grp, ...).
sparkle (4-point star) and taper_arm follow grand-line-jacket/gl_motifs.star (library candidate, ENGINE_NOTES)."""
import math, random
import numpy as np
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union
from shapely import affinity

def R(col, geom, st, ang, grp, **kw):
    d = dict(col=col, geom=geom, st=st, ang=ang, grp=grp); d.update(kw); return d

def polys(g):
    if g is None or g.is_empty: return []
    if g.geom_type == "Polygon": return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]

def taper_arm(cx, cy, ang, L, w0, w1=0.9, r0=0.0):
    a = math.radians(ang); ux, uy = math.cos(a), math.sin(a); nx, ny = -uy, ux
    p0 = (cx + ux*r0, cy + uy*r0); p1 = (cx + ux*L, cy + uy*L)
    return Polygon([(p0[0] + nx*w0/2, p0[1] + ny*w0/2), (p1[0] + nx*w1/2, p1[1] + ny*w1/2),
                    (p1[0] - nx*w1/2, p1[1] - ny*w1/2), (p0[0] - nx*w0/2, p0[1] - ny*w0/2)]).buffer(0.12).buffer(0)

# ---------------------------------------------------------------- star field
def sparkle(cx, cy, span, col="kc_white", unit=None, rot=0.0, grp="STAR"):
    """4-point concave sparkle (mockup: diamond star with pinched sides), one object in one thread: fixed 45° satin so
    all four arms sew in one pass. Tips are flat 0.8 wide (min satin), inner radius 0.32 of the arm length."""
    L = span / 2; ri = max(0.75, L * 0.32); tw = 0.4
    pts = []
    for k in range(4):
        a = math.radians(rot - 90 + 90*k); ux, uy = math.cos(a), math.sin(a); nx, ny = -uy, ux
        pts += [(cx + ux*L - nx*tw, cy + uy*L - ny*tw), (cx + ux*L + nx*tw, cy + uy*L + ny*tw)]
        b = a + math.radians(45); pts.append((cx + math.cos(b)*ri, cy + math.sin(b)*ri))
    g = Polygon(pts).buffer(0.15, join_style="round").buffer(-0.1).buffer(0)
    return [R(col, g, "satin", 45.0 + rot, grp, unit=unit, kob=0.6)]

def dot(cx, cy, d, col="kc_white", unit=None, grp="DOT"):
    return [R(col, Point(cx, cy).buffer(max(0.65, d/2), quad_segs=10), "satin", "auto", grp, unit=unit, kob=0.6)]

# ---------------------------------------------------------------- badge parts
def capsule(p0, p1, w, col, grp="PF-BAR", unit=None):
    g = LineString([p0, p1]).buffer(w/2, quad_segs=10, cap_style="round")
    return [R(col, g, "satin", "auto", grp, unit=unit, kob=0.5)]

def capsule_c(cx, cy, L, w, ang, col, grp="PF-BAR", unit=None):
    a = math.radians(ang); dx, dy = math.cos(a)*(L - w)/2, math.sin(a)*(L - w)/2
    return capsule((cx - dx, cy - dy), (cx + dx, cy + dy), w, col, grp, unit)

def star5_geom(cx, cy, R_, rot=0.0, k=0.48, round_=0.5):
    pts = []
    for i in range(10):
        r = R_ if i % 2 == 0 else R_ * k
        a = math.radians(-90 + rot + 36*i)
        pts.append((cx + r*math.cos(a), cy + r*math.sin(a)))
    g = Polygon(pts).buffer(0)
    return g.buffer(-round_, join_style="round").buffer(round_, join_style="round") if round_ else g

def star5(cx, cy, size, col, grp="PF-STR", unit=None, rot=0.0, face=None, face_col=None):
    """5-point star (size = tip-to-tip height). Satin per arm: the star is cut into 5 kites (one per arm, angle across the arm),
    so each arm sews as its own satin and the tips stay sharp-ish. face: 'eyes' (two knocked-out eyes) | 'centre' (dot)."""
    R_ = size / 2
    g = star5_geom(cx, cy, R_, rot)
    regs = []
    holes = Polygon()
    if face == "eyes":
        e = R_ * 0.13
        holes = unary_union([Point(cx - R_*0.18, cy - R_*0.02).buffer(e), Point(cx + R_*0.18, cy - R_*0.02).buffer(e)])
    for i in range(5):
        a0 = math.radians(-90 + rot + 72*i - 36); a1 = math.radians(-90 + rot + 72*i + 36)
        wedge = Polygon([(cx, cy), (cx + 3*R_*math.cos(a0), cy + 3*R_*math.sin(a0)),
                         (cx + 3*R_*math.cos((a0 + a1)/2), cy + 3*R_*math.sin((a0 + a1)/2)), (cx + 3*R_*math.cos(a1), cy + 3*R_*math.sin(a1))])
        arm = g.intersection(wedge).difference(holes).buffer(0)
        arm_ang = -90 + rot + 72*i
        for p in polys(arm):
            regs.append(R(col, p, "satin", arm_ang + 90, grp, unit=unit, kob=0.5))
    if face == "centre" and face_col:
        regs.append(R(face_col, Point(cx, cy).buffer(R_ * 0.2, quad_segs=10), "satin", "auto", "FACE", unit=unit, kob=0.4))
    return regs

def star5_outline(cx, cy, size, w, col, grp="STR5-o", unit=None, rot=0.0, eyes=True):
    R_ = size / 2
    g = star5_geom(cx, cy, R_, rot, round_=0.3)
    ring = g.difference(g.buffer(-w)).buffer(0)
    import kclettering as KL          # a closed ring is cut into strokes (one turning satin per side)
    regs = [R(col, q, "satin", "auto", grp, unit=unit, kob=0.5) for p in polys(ring) for q in KL.split_corners(KL._cut_ring(p)[0]) + [x for r_ in KL._cut_ring(p)[1:] for x in KL.split_corners(r_)]]
    if eyes:
        e = max(0.65, R_ * 0.10)
        for dx in (-0.2, 0.2):
            regs.append(R(col, Point(cx + dx*R_, cy - 0.02*R_).buffer(e, quad_segs=8), "satin", "auto", "FACE", unit=unit, kob=0.4))
    return regs

def heart(cx, cy, size, col, grp="PF-HRT", unit=None, rot=0.0):
    """heart, size = width. Two lobes + point; split into left/right halves so each half sews as one satin."""
    s = size / 2
    lobe = s * 0.52
    g = unary_union([Point(cx - s*0.46, cy - s*0.18).buffer(lobe, quad_segs=16), Point(cx + s*0.46, cy - s*0.18).buffer(lobe, quad_segs=16),
                     Polygon([(cx - s*0.95, cy - s*0.05), (cx + s*0.95, cy - s*0.05), (cx, cy + s*0.95)])]).buffer(0.2).buffer(-0.2)
    g = affinity.rotate(g, rot, origin=(cx, cy))
    halves = []
    for sgn in (-1, 1):
        hb = affinity.rotate(box(cx if sgn > 0 else cx - 3*s, cy - 3*s, cx + 3*s if sgn > 0 else cx, cy + 3*s), rot, origin=(cx, cy))
        hp = g.intersection(hb).buffer(0)
        for p in polys(hp): halves.append(R(col, p, "satin", rot + (45 if sgn < 0 else -45), grp, unit=unit, kob=0.5))
    return halves

def ring_dot(cx, cy, d, col, grp="DOTB", unit=None):
    return [R(col, Point(cx, cy).buffer(d/2, quad_segs=24), "satin", ("radial", cx, cy), grp, unit=unit, kob=0.6)]

def oval_ring(cx, cy, a, b, w, col, ang=0.0, grp="OVAL", hl=None, hl_w=1.1, hl_col=None):
    """elliptic ring (outer semi-axes a, b, width w); cut into 4 quarter arcs so each sews as one turning satin.
    hl: highlight band on the inner half of the ring in hl_col, sewn on top (overlay)."""
    E = lambda A, B: affinity.scale(Point(0, 0).buffer(1.0, quad_segs=64), A, B, origin=(0, 0))
    ring = E(a, b).difference(E(a - w, b - w))
    regs = []
    for q in range(4):
        th0 = math.radians(q*90 + 45); th1 = math.radians(q*90 + 135)
        wedge = Polygon([(0, 0)] + [(4*a*math.cos(t), 4*b*math.sin(t)) for t in np.linspace(th0, th1, 12)])
        part = ring.intersection(wedge).buffer(0)
        for p in polys(part):
            p = affinity.translate(affinity.rotate(p, ang, origin=(0, 0)), cx, cy)
            regs.append(R(col, p, "satin", "auto", grp, kob=0.5))
    if hl:
        mid = E(a - w*0.38 + hl_w/2, b - w*0.38 + hl_w/2).difference(E(a - w*0.38 - hl_w/2, b - w*0.38 - hl_w/2))
        for q in range(4):
            th0 = math.radians(q*90 + 45); th1 = math.radians(q*90 + 135)
            wedge = Polygon([(0, 0)] + [(4*a*math.cos(t), 4*b*math.sin(t)) for t in np.linspace(th0, th1, 12)])
            for p in polys(mid.intersection(wedge).buffer(0)):
                p = affinity.translate(affinity.rotate(p, ang, origin=(0, 0)), cx, cy)
                regs.append(R(hl_col, p, "satin", "auto", "OVAL-hl", kob=0.0, ko=False))
    return regs

# ---------------------------------------------------------------- neon glow (sheer serpentine run)
def glow(shape, ang, col="kc_glow", sp=1.6, rng=None, ragged=0.35, grp="GLOW"):
    """sheer halo: rows along `ang` across `shape`, row ends ragged (soft edge), joined end to end into ONE serpentine
    path (one object, no trims inside). Sewn first; it knocks nothing out (overlay under the badge)."""
    rng = rng or random.Random(7)
    c = shape.centroid
    g = affinity.rotate(shape, -ang, origin=c)
    x0, y0, x1, y1 = g.bounds
    seq = []
    k = 0
    for y in np.arange(y0 + sp/2, y1, sp):
        ln = LineString([(x0 - 5, y), (x1 + 5, y)]).intersection(g)
        segs = [s for s in getattr(ln, "geoms", [ln]) if s.geom_type == "LineString" and s.length > 2]
        for s in segs:
            a, b = s.coords[0], s.coords[-1]; L = b[0] - a[0]
            cut0 = rng.uniform(0, ragged) * min(L, 14); cut1 = rng.uniform(0, ragged) * min(L, 14)
            a = (a[0] + cut0, y); b = (b[0] - cut1, y)
            if b[0] - a[0] < 2: continue
            pts = [a, b] if k % 2 == 0 else [b, a]
            seq += pts; k += 1
    if len(seq) < 2: return []
    line = affinity.rotate(LineString(seq), ang, origin=c)
    return [R(col, line.buffer(0.3, cap_style="round", join_style="round"), "run", None, grp, ko=False, kob=0.0)]
