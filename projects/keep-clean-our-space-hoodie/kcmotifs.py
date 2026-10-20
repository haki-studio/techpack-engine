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

# ================================================================ Rev B motifs (review Rev A items 2, 3, 5, 7, 9)
# Every satin is a column (kcsatin): one turning satin per stroke, no fans, no skipped rows.
import kcsatin as KS
RIM_COL = {"kc_mint": "kc_mint_lt", "kc_blue": "kc_blue_lt", "kc_red": "kc_red_lt", "kc_lemon": "kc_lemon_lt", "kc_gold": "kc_lemon"}
RIM_W = 0.85          # puff rim column (lighter thread) — 40wt satin minimum is 0.8
RIM_OVL = 0.3         # the core runs this far under the rim

def _core_w(w, rw=RIM_W): return max(0.9, w - 2 * (rw - RIM_OVL))

def gap_fillers(P, sts, min_mm2=2.0):
    """Rev C (glyph gate): parts of the font glyph that no stroke column covers get their own short column across the
    piece's long axis (the KR '!' dot had no skeleton at all; an A apex cut at the corner left its outer point bare).
    One filler per uncovered piece >= min_mm2; width = the piece's narrow side, round caps."""
    covered = KS.strokes_geom(sts).buffer(0.1) if sts else None
    left = P.difference(covered) if covered is not None else P
    out = []
    for q in polys(left.buffer(-0.05).buffer(0.05)):
        if q.area < min_mm2: continue
        r = q.minimum_rotated_rectangle; cs = list(r.exterior.coords)
        e0 = np.subtract(cs[1], cs[0]); e1 = np.subtract(cs[2], cs[1])
        L, W, ax = (np.linalg.norm(e0), np.linalg.norm(e1), e0) if np.linalg.norm(e0) >= np.linalg.norm(e1) else (np.linalg.norm(e1), np.linalg.norm(e0), e1)
        from shapely.ops import polylabel
        pc = polylabel(q, 0.03); rr = q.exterior.distance(pc)          # widest inscribed disc: the filler stays inside
        if rr < 0.3: continue                                             # a sliver under the neighbours' pull comp
        w = max(0.9, 2 * rr)                            # the inscribed width (pull comp is added by the satin builder)
        u = ax / max(np.linalg.norm(ax), 1e-9)
        c = np.array(pc.coords[0])
        # a round piece (a dot) is one disc column across its diameter (round caps shrink inside the ends, as disc_rc);
        # a long sliver gets a short column centred on its widest point (spills less at the sliver tips)
        h = L / 2 - 0.1 if L <= 3.2 * rr else max(0.1, (L - w) / 2)
        out.append(dict(cl=[tuple(c - u * h), tuple(c + u * h)], w=w, caps=("round", "round"), closed=False, filler=True))
    return out

def text_columns(glyphs, col, code, cap, unit, rim=False, rim_code="PF-RIM", **kw):
    """font glyphs -> stroke columns (core) [+ lighter rim columns round the stroke outline, puff dome look]."""
    core, rims = [], []
    for ch, g in glyphs:
        for P in polys(g):
            sts = KS.glyph_columns(P, cap); sts = sts + gap_fillers(P, sts)
            if not sts: continue
            for s in sts:
                w = _core_w(s["w"]) if rim else s["w"]
                core.append(KS.column_region(col, code, s["cl"], w, s["caps"], s.get("closed", False), unit=unit, ch=ch, **kw))
            if rim:
                shape = KS.strokes_geom(sts)
                for p in polys(shape):
                    for s in KS.ring_columns(p, RIM_W):
                        rims.append(KS.column_region(RIM_COL[col], rim_code, s["cl"], RIM_W, s["caps"], s.get("closed", False), unit=unit, ch=ch, rim=True, **kw))
    return core, rims

def bar_rc(cx, cy, L, w, ang, col, unit, code="PF-BAR"):
    """spark bar: core column along the bar + lighter rim column round the capsule (domed)."""
    a = math.radians(ang); dx, dy = math.cos(a) * L / 2, math.sin(a) * L / 2
    cl = [(cx - dx, cy - dy), (cx + dx, cy + dy)]
    cap = KS.column_geom(cl, w)
    core = [KS.column_region(col, code, cl, _core_w(w), unit=unit)]
    rim = [KS.column_region(RIM_COL[col], "PF-RIM", s["cl"], RIM_W, s["caps"], s.get("closed", False), unit=unit, rim=True)
           for p in polys(cap) for s in KS.ring_columns(p, RIM_W)]
    return core, rim

def disc_rc(cx, cy, d, col, unit, code="PF-DOT", rim_w=1.1, ang=35.0):
    """domed dot: core = one round-capped column across the disc (a disc, rows parallel, staggered splits — no radial
    starburst, no centre line) + lighter rim ring column."""
    rc = d / 2 - rim_w + RIM_OVL; a = math.radians(ang)
    cl = [(cx - math.cos(a) * rc, cy - math.sin(a) * rc), (cx + math.cos(a) * rc, cy + math.sin(a) * rc)]
    core = [KS.column_region(col, code, cl, 2 * rc, unit=unit)]
    rr = d / 2 - rim_w / 2
    ring = [(cx + rr * math.cos(t), cy + rr * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 72, endpoint=False)]
    rim = [KS.column_region(RIM_COL[col], "PF-RIM", ring, rim_w, ("flat", "flat"), True, unit=unit, rim=True)]
    return core, rim

def heart_rc(cx, cy, size, col, unit, rot=0.0, code="PF-HRT"):
    s = size / 2; lobe = s * 0.52
    g = unary_union([Point(cx - s*0.46, cy - s*0.18).buffer(lobe, quad_segs=16), Point(cx + s*0.46, cy - s*0.18).buffer(lobe, quad_segs=16),
                     Polygon([(cx - s*0.95, cy - s*0.05), (cx + s*0.95, cy - s*0.05), (cx, cy + s*0.95)])]).buffer(0.2).buffer(-0.2)
    g = affinity.rotate(g, rot, origin=(cx, cy))
    inner = g.buffer(-(RIM_W - RIM_OVL)); core = []
    for sgn in (-1, 1):
        hb = affinity.rotate(box(cx if sgn > 0 else cx - 3*s, cy - 3*s, cx + 3*s if sgn > 0 else cx, cy + 3*s), rot, origin=(cx, cy))
        for p in polys(inner.intersection(hb).buffer(0)):
            core.append(R(col, p, "satin", rot + (45 if sgn < 0 else -45), code, unit=unit, kob=0.0, nok=True))
    rim = [KS.column_region(RIM_COL[col], "PF-RIM", s_["cl"], RIM_W, s_["caps"], s_.get("closed", False), unit=unit, rim=True)
           for s_ in KS.ring_columns(g, RIM_W, corner=40.0)]
    return core, rim, g

def star_facets(cx, cy, size, col, unit, rot=0.0, k=0.48, code="PF-STR", light=None, pit=0.0, pit_shape="circle", round_=0.35):
    """faceted 5-point star: every arm = two facets (centre-tip-valley triangles), each its own satin direction; the
    facet that faces up (light from above) sews in the lighter thread. pit: knocked-out centre (fabric shows):
    radius as a share of R, a circle or a small star."""
    R_ = size / 2; light = light or RIM_COL.get(col, col)
    g = star5_geom(cx, cy, R_, rot, k=k, round_=round_)
    hole = Polygon()
    if pit:
        hole = Point(cx, cy).buffer(R_ * pit, quad_segs=12) if pit_shape == "circle" else star5_geom(cx, cy, R_ * pit, rot, k=0.5, round_=0.0)
    out = []
    for i in range(5):
        ta = math.radians(-90 + rot + 72 * i)
        tip = (cx + 3 * R_ * math.cos(ta), cy + 3 * R_ * math.sin(ta))
        for side in (-1, 1):
            va = ta + side * math.radians(36)
            val = (cx + 3 * R_ * math.cos(va), cy + 3 * R_ * math.sin(va))
            tri = Polygon([(cx, cy), tip, val])
            f = g.intersection(tri).difference(hole).buffer(0)
            # facet normal: the facet's centroid direction rotated toward its valley; "up" facets catch the light
            c = f.centroid if not f.is_empty else Point(cx, cy)
            up = (c.y - cy) < -0.15 * R_ or (abs(c.y - cy) <= 0.15 * R_ and side < 0)
            # rows run from the arm axis to the facet edge, slanted toward the valley
            ang = math.degrees(ta) + 90 + side * 18
            for p in polys(f):
                if p.area < 0.15: continue
                out.append(R(light if up else col, p, "satin", ang, code, unit=unit, kob=0.0, nok=True, facet=True))
    return out, g

def sparkle_cols(cx, cy, span, col="kc_white", unit=None, rot=0.0, code="SPK"):
    """concave 4-point sparkle: two crossing tapered columns (arms pinch to 0.25 at the tips, concave sides)."""
    w0 = max(1.1, 0.52 * span); L = span / 2 * 0.9  # traced: fat 4-point star; arms end at 90 % (needle tips sit outside the half-max edge)
    prof = ("taper", 1.3, 0.10)
    if span < 5.0: w0, prof = max(1.1, 0.62 * span), ("taper", 1.0, 0.12)      # small ones read as diamonds
    out = []
    for k in (0, 1):
        a = math.radians(rot + 90 * k)
        cl = [(cx - math.cos(a) * L, cy - math.sin(a) * L), (cx + math.cos(a) * L, cy + math.sin(a) * L)]
        out.append(KS.column_region(col, code, cl, w0, ("flat", "flat"), False, prof=prof, unit=unit))
    return out

def haze(cx, cy, r, unit, col="kc_haze", code="HAZE", star=None):
    """soft glow round a big sparkle: a stipple run on a disc, fading out (review item 9)"""
    core = star if star is not None else Point(cx, cy).buffer(0.6)
    return stipple_band(core, unit, outer=r, col=col, code=code, seed=int(abs(cx * 7 + cy * 13)) % 9973, s0=0.55, k=0.35, hole_inset=0.0, step=1.5)

def halo(shape, ang, unit, inner=1.9, outer=3.8, col="kc_glow", rng=None, hole_inset=0.45):
    """soft neon halo following the silhouette: dense band 0..inner mm round the shape, sparse band inner..outer with a
    ragged outer edge. Both are knocked out where the art sits (the art overlaps them by hole_inset)."""
    rng = rng or random.Random(7)
    s0 = shape.buffer(0.6).buffer(-0.6)
    dense = s0.buffer(inner, join_style="round").buffer(0)
    out_g = s0.buffer(outer + 1.2, join_style="round").buffer(-1.2, join_style="round")       # bridges letter gaps
    # ragged outer edge
    rag = []
    for p in polys(out_g):
        ring = LineString(p.exterior.coords); L = ring.length; n = max(12, int(L / 1.1)); pts = []
        for i in range(n):
            q = ring.interpolate(L * i / n); q2 = ring.interpolate(L * i / n + 0.3)
            t = np.array([q2.x - q.x, q2.y - q.y]); tn = np.linalg.norm(t)
            nn = np.array([t[1], -t[0]]) / tn if tn > 1e-9 else np.array([0.0, 0.0])
            d = rng.uniform(0.0, 1.5)
            pts.append((q.x - nn[0] * d, q.y - nn[1] * d))
        pp = Polygon(pts).buffer(0)
        hole = [Polygon(h.coords) for h in p.interiors]
        if hole: pp = pp.difference(unary_union(hole))
        rag.append(pp)
    out_g = unary_union(rag).buffer(0.25).buffer(-0.25).union(dense).buffer(0)
    art = shape.buffer(-hole_inset)
    d_ = dense.difference(art).buffer(0); s_ = out_g.difference(dense.buffer(-0.2)).difference(art).buffer(0)
    regs = []
    for p in polys(d_):
        if p.area > 0.4: regs.append(R(col, p, "tatami", ang, "GLOW-D", unit=unit, kob=0.0, nok=True, glow=True))
    for p in polys(s_):
        if p.area > 0.4: regs.append(R(col, p, "tatami", ang + 8, "GLOW-S", unit=unit, kob=0.0, nok=True, glow=True))
    return regs

def oval_cols(cx, cy, a, b, w, col, ang=0.0, hl_col=None, hl_w=1.1, unit=None):
    """elliptic ring as ONE closed satin column (no quarter seams) + an inner highlight column on top."""
    def ell(A, B):
        return [(cx + A * math.cos(t) * math.cos(math.radians(ang)) - B * math.sin(t) * math.sin(math.radians(ang)),
                 cy + A * math.cos(t) * math.sin(math.radians(ang)) + B * math.sin(t) * math.cos(math.radians(ang)))
                for t in np.linspace(0, 2 * math.pi, 220, endpoint=False)]
    regs = [KS.column_region(col, "OVAL", ell(a - w / 2, b - w / 2), w, ("flat", "flat"), True, unit=unit)]
    if hl_col:
        m = w * 0.38
        regs.append(KS.column_region(hl_col, "OVAL-hl", ell(a - w + m, b - w + m), hl_w, ("flat", "flat"), True, unit=unit, ko=False))
    return regs

# ---------------------------------------------------------------- Rev B soft glow: stipple run (review item 2)
def stipple_band(shape, unit, inner=0.0, outer=3.6, col="kc_glow", code="GLOW", seed=7, s0=0.30, k=0.16, hole_inset=0.45,
                 step=1.8, glow=True, max_hop=3.0):
    """soft glow: a random short-stitch run inside the band round `shape` (0..outer mm from its silhouette, following
    it — no bridging), point spacing s0 + k * distance, so it is dense at the art and fades out. One run per connected
    band (greedy nearest-neighbour path, hops > step re-stitched). Returns regions with r['run_pts']."""
    from shapely import contains_xy, distance as sdist, points as spoints
    rng = np.random.default_rng(seed)
    band = shape.buffer(outer, join_style="round").difference(shape.buffer(-hole_inset)).buffer(0)
    if inner: band = band.difference(shape.buffer(inner)).buffer(0)
    regs = []
    for part in polys(band):
        if part.area < 2: continue
        b = part.bounds; g = 0.25
        X, Y = np.meshgrid(np.arange(b[0], b[2], g), np.arange(b[1], b[3], g))
        X = X + rng.uniform(-g/2, g/2, X.shape); Y = Y + rng.uniform(-g/2, g/2, Y.shape)
        m = contains_xy(part, X, Y); xs, ys = X[m], Y[m]
        if not len(xs): continue
        d = sdist(shape.boundary, spoints(xs, ys)); d = np.where(contains_xy(shape, xs, ys), 0.0, d)
        sp = s0 + k * d                          # local spacing
        keep = rng.uniform(0, 1, len(xs)) < (g * g) / (sp * sp)
        P = np.c_[xs[keep], ys[keep]]
        if len(P) < 3: continue
        # greedy nearest-neighbour walk (KD-tree)
        from scipy.spatial import cKDTree
        tree = cKDTree(P); used = np.zeros(len(P), bool); i = int(np.argmin(P[:, 0])); path = [tuple(P[i])]; used[i] = True; paths = []
        for _ in range(len(P) - 1):
            kq = 8
            while True:
                dd, ii = tree.query(P[i], k=min(kq, len(P)))
                ii = np.atleast_1d(ii); cand = [j for j in ii if not used[j]]
                if cand or kq >= len(P): break
                kq *= 4
            if not cand:
                rest = np.nonzero(~used)[0]
                if not len(rest): break
                j = rest[np.argmin(np.hypot(P[rest, 0] - P[i, 0], P[rest, 1] - P[i, 1]))]
            else: j = cand[0]
            a = path[-1]; bpt = tuple(P[j]); L = math.dist(a, bpt)
            if L > max_hop:                      # Rev C: a long hop was sewn as a straight line across the halo (up to
                paths.append(path); path = [bpt]  # 57 mm on Rev B FR M): start a new run instead (the router hides / trims)
                used[j] = True; i = j; continue
            if L > step:
                n = int(math.ceil(L / step)); path += [(a[0] + (bpt[0] - a[0]) * t / n, a[1] + (bpt[1] - a[1]) * t / n) for t in range(1, n)]
            path.append(bpt); used[j] = True; i = j
        paths.append(path)
        for pth in paths:
            if len(pth) < 3: continue
            gg = LineString(pth).buffer(0.35)
            if gg.geom_type != "Polygon": gg = max(getattr(gg, "geoms", [gg]), key=lambda q: q.area)
            regs.append(dict(col=col, geom=gg, st="run", ang=None, grp=code, unit=unit, kob=0.0, nok=True, ko=False, glow=True, run_pts=pth))
    return regs
