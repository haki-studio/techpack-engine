"""3-panel hood (2 side panels + centre panel) for the hooded variant of the Drum Island block.

Side panel drafting frame (mm, y DOWN): N0 = hood neck point at CF = (0, 0); x runs toward the back of the head.
Edges, chained:  neck  N0 -> NB  (to the centre-panel seam at CB)
                 back  NB -> TF  (centre-panel seam: up the back of the head, over the crown, to the top front)
                 face  TF -> N0  (face opening)
The neck and face edges meet the centre-panel seam at 90 deg, so the neck line and the face line run on smoothly across
the centre panel's ends (checked in pattern_out.shape_checks).

Every dimension here is PROPOSED (not on the fit chart). They live in pattern.HOOD and can be overridden per project:
    pattern.draft("M", variant="hooded", hood={"height": 350, "face_opening": 780})
or for the whole project:  pattern.HOOD.update(height=350)."""
import math
import numpy as np
from shapely.geometry import LineString, Point, Polygon

def bezier(p0, c0, c1, p1, n=40):
    t = np.linspace(0, 1, n)[:, None]
    p0, c0, c1, p1 = (np.array(v, float) for v in (p0, c0, c1, p1))
    return [tuple(v) for v in ((1-t)**3*p0 + 3*(1-t)**2*t*c0 + 3*(1-t)*t**2*c1 + t**3*p1)]

def hermite(p0, t0, p1, t1, n=40, a=0.42):
    """cubic from p0 to p1 leaving along unit t0, arriving along unit t1; handles = a × chord"""
    L = math.hypot(p1[0]-p0[0], p1[1]-p0[1])
    return bezier(p0, (p0[0] + t0[0]*L*a, p0[1] + t0[1]*L*a), (p1[0] - t1[0]*L*a, p1[1] - t1[1]*L*a), p1, n)

def unit(v):
    L = math.hypot(*v) or 1.0; return (v[0]/L, v[1]/L)

def side_panel(neck_len, d, curve, alen):
    """neck_len = side-panel neck seam length; d = graded hood dims. Returns (neck, back, face) polylines."""
    H, W, Lf = d["height"], d["width"], (d["face_opening"] - d["centre_w"]) / 2
    r = d["neck_rise"]
    # neck edge: N0 -> NB, bowing OUT of the panel (down) by neck_bow -> convex, the mate of the scooped body neck
    lo, hi = 50.0, 600.0
    for _ in range(60):
        wn = (lo + hi) / 2
        neck = [tuple(p) for p in curve((0, 0), (wn, -r), -d["neck_bow"], 40)]
        if alen(neck) > neck_len: hi = wn
        else: lo = wn
    NB = neck[-1]
    # face edge: TF -> N0, leaning back by face_lean at the top, bowing forward (out) by face_bow; height solved for length
    lo, hi = 50.0, 2 * Lf
    for _ in range(60):
        hf = (lo + hi) / 2
        face = [tuple(p) for p in curve((d["face_lean"], -hf), (0, 0), -d["face_bow"], 40)]
        if alen(face) > Lf: hi = hf
        else: lo = hf
    TF = face[0]
    if hf > H - 4:
        raise ValueError(f"hood: face opening {d['face_opening']:.0f} needs a face edge {hf:.0f} high, more than the hood height {H:.0f}")
    min_x = min(p[0] for p in face)
    bk = (W + min_x, -(r + 0.38 * (H - r)))                       # widest point at the back of the head
    if bk[0] < NB[0] + 10:
        raise ValueError(f"hood: width {W:.0f} too small for the neck seam (needs > {NB[0] - min_x + 10:.0f})")
    cr = (TF[0] + 0.42 * (bk[0] - TF[0]), -H)                     # crown
    dn = unit((neck[-1][0] - neck[-2][0], neck[-1][1] - neck[-2][1]))
    t_nb = (dn[1], -dn[0])                                          # 90 deg to the neck, pointing up
    df = unit((face[1][0] - face[0][0], face[1][1] - face[0][1]))
    t_tf = (-df[1], df[0])                                          # 90 deg to the face edge, travelling forward
    back = hermite(NB, t_nb, bk, (0, -1)) + hermite(bk, (0, -1), cr, (-1, 0))[1:] + hermite(cr, (-1, 0), TF, t_tf)[1:]
    return neck, back, face

def _inside_offset(pts, dist, poly):
    """offset a polyline into poly by dist (scalar or per-point list) along its normals"""
    out = []
    n = len(pts)
    ds = dist if isinstance(dist, (list, tuple, np.ndarray)) else [dist] * n
    for i, p in enumerate(pts):
        a, b = pts[max(0, i-1)], pts[min(n-1, i+1)]
        tx, ty = unit((b[0]-a[0], b[1]-a[1])); nx, ny = -ty, tx
        if not poly.contains(Point(p[0] + nx*2, p[1] + ny*2)): nx, ny = -nx, -ny
        out.append((p[0] + nx*ds[i], p[1] + ny*ds[i]))
    return out

def _extend(pts, e=80.0):
    a = unit((pts[0][0]-pts[1][0], pts[0][1]-pts[1][1])); b = unit((pts[-1][0]-pts[-2][0], pts[-1][1]-pts[-2][1]))
    return [(pts[0][0] + a[0]*e, pts[0][1] + a[1]*e)] + list(pts) + [(pts[-1][0] + b[0]*e, pts[-1][1] + b[1]*e)]

def _sub(pts, s0, s1):
    """part of polyline between arc lengths s0 < s1"""
    ls = LineString(pts); out = [ls.interpolate(s0).coords[0]]
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        acc += math.hypot(b[0]-a[0], b[1]-a[1])
        if s0 + 1e-6 < acc < s1 - 1e-6: out.append(b)
    out.append(ls.interpolate(s1).coords[0])
    return out

def _hit(a, b):
    h = LineString(a).intersection(LineString(b))
    if h.is_empty: raise ValueError("hood lining: offset lines do not meet")
    ps = [h] if h.geom_type == "Point" else [g for g in getattr(h, "geoms", []) if g.geom_type == "Point"]
    return ps[0]

def lining_panel(neck, back, face, d):
    """sherpa lining side panel: face edge moved back by the facing width (facing join), centre seam moved in by the
    turn-of-cloth (full at the crown, ramping to 0 at the neck so the lining neck still matches the body neck)."""
    poly = Polygon(neck + back[1:] + face[1:]).buffer(0)
    face_in = _extend(_inside_offset(face, d["facing_w"], poly))
    sb = np.cumsum([0] + [math.hypot(q[0]-p[0], q[1]-p[1]) for p, q in zip(back, back[1:])]); Lb = sb[-1]
    ramp = [d["toc"] * min(1.0, s / (0.3 * Lb)) ** 2 * (3 - 2 * min(1.0, s / (0.3 * Lb))) for s in sb]   # smoothstep
    back_in = _inside_offset(back, ramp, poly)
    back_in = back_in + [(back_in[-1][0] + (back_in[-1][0]-back_in[-2][0]) * 40, back_in[-1][1] + (back_in[-1][1]-back_in[-2][1]) * 40)]
    A = _hit(face_in, neck); B = _hit(face_in, back_in)
    ln, lb, lf = LineString(neck), LineString(back_in), LineString(face_in)
    neck_l = _sub(neck, ln.project(A), ln.length)
    back_l = _sub(back_in, 0.0, lb.project(B))
    sa_, sb_ = sorted((lf.project(B), lf.project(A)))
    face_l = _sub(face_in, sa_, sb_)
    if math.hypot(face_l[0][0]-B.x, face_l[0][1]-B.y) > 1e-6: face_l = face_l[::-1]
    back_l[0] = neck_l[-1]; face_l[0] = back_l[-1]; face_l[-1] = neck_l[0]      # exact shared corners (no sliver at closure)
    # facing side = the band the lining gave up: N0 -> A on the neck, A -> B along the facing join, B -> TF, face TF -> N0
    f_neck = _sub(neck, 0.0, ln.project(A)); f_neck[0] = neck[0]; f_neck[-1] = neck_l[0]
    f_seam = [back_l[-1], back[-1]]
    facing = (f_neck, face_l[::-1], f_seam, list(face))
    return neck_l, back_l, face_l, facing
