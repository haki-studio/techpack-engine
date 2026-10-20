"""Building template fitter (ENGINE_PLAN M3a; DIGITIZING_PRINCIPLES rule 2 "constructed parts follow rule tables",
rule 3, rule 9, motif playbook "Buildings").

The template is a stack of TIERS: a roof (sloped planes with an eave line along its bottom) over a wall plane, with
members (timber, trims), windows and studs on top. Everything is FITTED from the reference pixels of one building
window (the evidence tone trace: which thread each pixel looks like); nothing about a particular crop is coded here.
Every number that steers a fit comes from rules/house.yaml (kind params) or the run yaml (`building:`).

Directions are RULES applied to the fitted geometry, never the reference grain (so they are independent evidence for the
direction gate, LESSONS A24):
  roof plane  NEAR tier (rule 2) down the slope: the front plane runs perpendicular to its fitted eave line; a hip plane
              (left / right of the ridge) fans halfway between that and its fitted hip line, kept hip_min_sep..hip_max_sep
              off the front. FAR tier (rule 3 depth: far = near-horizontal; fitted tier height < near_tier_mm): along
              the eave line.
  wall plane  one angle per plane, square to the eave of the roof above it: along it under a far roof, across it under a
              near one (rule 3 depth); 0 deg without a roof
  eave / member / window band   satin across the member's width = its centreline's chord + 90
  roof tile lines               bean lines down the slope of their plane (the tile rows), near tiers only
digitize.audit re-derives every one of them from the fitted points stored in the part (rule_basis), so a number typed
into meta does not pass."""
import math
import numpy as np
from scipy import ndimage as ndi


# ------------------------------------------------------------------ lines
def fit_line(pts, trim_mm=1.0, iters=2):
    """total-least-squares line through pts [(x, y)] mm, refit after dropping points > trim_mm off the line.
    Returns (axial angle deg in [0, 180), centre (x, y), inlier count) or None for < 2 points."""
    P = np.asarray(pts, float).reshape(-1, 2)
    if len(P) < 2: return None
    keep = np.ones(len(P), bool)
    for _ in range(iters + 1):
        Q = P[keep]
        if len(Q) < 2: Q = P; keep[:] = True
        c = Q.mean(0); U = Q - c
        w, v = np.linalg.eigh(U.T @ U); d = v[:, -1]
        ang = math.degrees(math.atan2(d[1], d[0])) % 180.0
        nrm = np.array([-d[1], d[0]]); r = np.abs((P - c) @ nrm)
        nk = r <= trim_mm
        if nk.sum() < 2 or (nk == keep).all(): break
        keep = nk
    return round(ang, 4), (float(c[0]), float(c[1])), int(keep.sum())


def slope(axial):
    """axial angle -> signed slope angle in (-90, 90] (0 = horizontal, + = falling to the right in y-down coords)"""
    a = axial % 180.0
    return a - 180.0 if a > 90.0 else a


def axial_diff(a, b):
    d = abs((a - b) % 180.0); return min(d, 180.0 - d)


# ------------------------------------------------------------------ rule angles (pure functions of stored points)
def eave_angle(eave_pts):
    f = fit_line(eave_pts)
    return slope(f[0]) if f else 0.0


def course_angle(eave_pts, top_pts=None, near_tier_mm=None):
    """wall plane, one angle per plane, square to the eave of the roof above it; rule 3 depth decides which way: under a
    FAR roof (or with no roof above) along the courses = parallel to the eave (near-horizontal), under a NEAR roof
    across them (near-vertical). No roof above: 0 deg."""
    if not eave_pts: return 0.0
    ea = eave_angle(eave_pts) % 180.0
    if near_tier_mm is None: return round(ea, 3)                    # depth rule off: every wall along its courses
    far = is_far(eave_pts, top_pts, near_tier_mm) if top_pts else False   # roof height unknown -> near, like the roof
    return round(ea if far else (ea + 90.0) % 180.0, 3)


def tier_height(eave_pts, top_pts):
    """the roof tier's visible height (mm): 75th percentile of bottom - top over the paired profile samples (an occluded
    top only lowers a column, so the upper quartile reads the real tier)"""
    if not top_pts or len(top_pts) != len(eave_pts): return None
    h = [b[1] - t[1] for b, t in zip(eave_pts, top_pts)]
    return float(np.percentile(h, 75)) if h else None


def is_far(eave_pts, top_pts, near_tier_mm):
    """rule 3 (depth: far = near-horizontal, near = near-vertical): a roof tier shorter than near_tier_mm is FAR"""
    if near_tier_mm is None: return False
    h = tier_height(eave_pts, top_pts)
    return h is not None and h < float(near_tier_mm)


def roof_angle(eave_pts, hip_pts=None, side=0, hip_min_sep=20.0, hip_max_sep=45.0, far=False):
    """NEAR tier (rule 2, down the slope): front plane (side 0) perpendicular to the eave line; a hip plane (side -1 left,
    +1 right of the ridge) halfway between the front's fall line and its own hip line (pointing down), kept
    hip_min_sep..hip_max_sep off the front on its own side (left planes fan down-left = > front; right planes < front).
    FAR tier (rule 3 depth: far parts near-horizontal): rows along the eave line; a hip plane along its own hip line,
    kept hip_min_sep..hip_max_sep off the front (left hips rise to the left = < front, right hips > front)."""
    ea = eave_angle(eave_pts) % 180.0
    if far:
        if not side or not hip_pts: return round(ea, 3)
        f = fit_line(hip_pts); hip = f[0] % 180.0 if f else ea
        want = -1.0 if side < 0 else 1.0
        d = ((hip - ea + 90.0) % 180.0) - 90.0                 # signed axial turn front -> hip line
        mag = min(max(abs(d) if d * want > 0 else 0.0, hip_min_sep), hip_max_sep)
        return round((ea + want * mag) % 180.0, 3)
    down = (ea + 90.0) % 180.0
    if not side or not hip_pts: return round(down, 3)
    f = fit_line(hip_pts)
    hip = f[0] % 180.0 if f else down                       # (cos, sin) with sin >= 0: the line already points down
    fan = (down + hip) / 2.0
    d = fan - down; want = 1.0 if side < 0 else -1.0
    mag = min(max(abs(d) if d * want > 0 else 0.0, hip_min_sep), hip_max_sep)
    return round((down + want * mag) % 180.0, 3)


def across_angle(cl):
    """satin across a member: the centreline's chord + 90"""
    (x0, y0), (x1, y1) = cl[0], cl[-1]
    return round((math.degrees(math.atan2(y1 - y0, x1 - x0)) + 90.0) % 180.0, 3)


def rule_basis(p, rb):
    """the declared angle of a constructed part, RE-DERIVED from the fitted points stored in its meta (digitize.audit).
    Returns None when the part does not carry what its rule needs."""
    k = rb.rule(p.kind); rule = k.get("construct"); m = p.meta; prm = rb.rule(k.get("params_from", p.kind)).get("params", {})
    try:
        if rule == "down_slope":
            far = is_far(m["eave_pts"], m.get("top_pts"), prm.get("near_tier_mm"))
            return roof_angle(m["eave_pts"], m.get("hip_pts"), int(m.get("side", 0)), float(prm.get("hip_min_sep", 20.0)),
                              float(prm.get("hip_max_sep", 45.0)), far=far)
        if rule == "course": return course_angle(m.get("eave_pts"), m.get("top_pts"), prm.get("near_tier_mm"))
        if rule == "across": return across_angle(m["cl"])
    except (KeyError, TypeError, IndexError):
        return None
    return None


# ------------------------------------------------------------------ pixels
def px_mm(ev, i, j):
    """evidence pixel (row i, col j) centre -> garment mm"""
    return (ev.bounds[0] + (np.asarray(j) + 0.5) / ev.ppm, ev.bounds[1] + (np.asarray(i) + 0.5) / ev.ppm)


def disk(ev, mm):
    r = max(1, int(round(mm * ev.ppm / 2))); y, x = np.ogrid[-r:r + 1, -r:r + 1]; return x * x + y * y <= r * r


def profiles(mask):
    """per column with pixels: (cols, top row, bottom row)"""
    cols = np.nonzero(mask.any(0))[0]
    if not len(cols): return cols, cols, cols
    sub = mask[:, cols]; H = mask.shape[0]
    top = sub.argmax(0); bot = H - 1 - sub[::-1].argmax(0)
    return cols, top, bot


def subsample(pts, n=60):
    pts = list(pts)
    if len(pts) <= n: return [[round(float(x), 3), round(float(y), 3)] for x, y in pts]
    idx = np.linspace(0, len(pts) - 1, n).round().astype(int)
    return [[round(float(pts[i][0]), 3), round(float(pts[i][1]), 3)] for i in idx]


def longest_run(flags):
    """(start, stop) of the longest run of True in a 1-D bool array (None when none)"""
    best = None; s = None
    for i, f in enumerate(list(flags) + [False]):
        if f and s is None: s = i
        if not f and s is not None:
            if best is None or i - s > best[1] - best[0]: best = (s, i)
            s = None
    return best


def split_tiers(mask, gap_frac=0.25, full_frac=0.5):
    """stacked roof tiers joined through a thin blue frame or wall post read as ONE component; per component, rows where
    under gap_frac of its columns are roof, with a row >= full_frac roof both above and below, are a gap between tiers:
    they are cut out so each tier is its own roof"""
    L, n = ndi.label(mask); out = mask.copy()
    for s in ndi.find_objects(L):
        if s is None: continue
        sub = mask[s]; f = sub.mean(1)
        if len(f) < 3: continue
        above = np.maximum.accumulate(f); below = np.maximum.accumulate(f[::-1])[::-1]
        cut = (f < gap_frac) & (above >= full_frac) & (below >= full_frac)
        if cut.any():
            rows = np.arange(s[0].start, s[0].stop)[cut]
            out[rows, s[1].start:s[1].stop] = False
    return out


def fit_roof(ev, comp, prm, free=None):
    """one roof component (bool mask on the evidence grid) -> dict(eave_pts, top_pts (paired with eave_pts, None when
    the eave is not visible), eave_visible, eave_deg, eave_y, planes=[dict(side, c0, c1, hip_pts)], cols, bot, top,
    height_mm) with c0 / c1 column ranges (evidence px) of each plane.
    free: pixels this zone may claim. An edge pixel whose outside neighbour is NOT free is OCCLUDED (a blossom crown sewn
    over the roof, the window or crop edge): that edge is not the roof's own and is never fitted.
      eave   the unoccluded bottom edge (line fit). When most of the bottom is occluded the eave is not visible: the
             unoccluded top edge (ridge, parallel to the eave) gives the course line and the tier height is unknown.
      ridge  the unoccluded columns whose top edge lies within ridge_tol of the highest one.
      hips   per side: the unoccluded top edge left / right of the ridge PLUS the unoccluded outer side edge (leftmost /
             rightmost pixel per row, from the top down to the eave corner) - one sloped line; a hip plane spans the
             columns that edge covers when it is >= min_plane_mm wide, <= max_hip_frac of the roof and sloped."""
    cols, top, bot = profiles(comp); H, Wd = comp.shape
    if free is None: free = np.ones_like(comp)
    ftop = free[np.maximum(top - 1, 0), cols] & free[np.maximum(top - 2, 0), cols] & (top > 1)      # 2 px clear outside the edge
    fbot = free[np.minimum(bot + 1, H - 1), cols] & free[np.minimum(bot + 2, H - 1), cols] & (bot < H - 2)
    xs, ybot = px_mm(ev, bot + 0.5, cols)                  # bottom EDGE of the lowest pixel
    _, ytop = px_mm(ev, top - 0.5, cols)
    def pick(mask):
        idx = np.nonzero(mask)[0]
        return idx if len(idx) <= 60 else idx[np.linspace(0, len(idx) - 1, 60).round().astype(int)]
    eave_visible = fbot.mean() >= prm.get("min_free_eave", 0.5) and fbot.sum() >= 4
    if eave_visible:
        sel = pick(fbot)
        eave_pts = [[round(float(xs[i]), 3), round(float(ybot[i]), 3)] for i in sel]
        top_pts = [[round(float(xs[i]), 3), round(float(ytop[i]), 3)] for i in sel]
    else:                                                       # the ridge line stands in for the eave (parallel); height unknown
        sel = pick(ftop if ftop.sum() >= 4 else np.ones_like(ftop))
        eave_pts = [[round(float(xs[i]), 3), round(float(ytop[i]), 3)] for i in sel]; top_pts = None
    f = fit_line(eave_pts, trim_mm=prm.get("eave_trim_mm", 1.0))
    eave_deg = slope(f[0]) if f else 0.0
    h = tier_height(eave_pts, top_pts) if top_pts else float(np.percentile(ybot - ytop, 75))
    tol = max(prm.get("ridge_tol_mm", 1.0), prm.get("ridge_tol_frac", 0.25) * h)
    yt = np.where(ftop, ytop, np.inf)
    r = longest_run(ftop & (ytop <= yt.min() + tol)) if ftop.any() else None
    rs, re_ = r if r else (len(cols) // 2, len(cols) // 2)
    # outer side edges, row by row
    rows = np.nonzero(comp.any(1))[0]; sub = comp[rows]
    xl = sub.argmax(1); xr = Wd - 1 - sub[:, ::-1].argmax(1)
    fl = free[rows, np.maximum(xl - 1, 0)] & free[rows, np.maximum(xl - 2, 0)] & (xl > 1)
    fr = free[rows, np.minimum(xr + 1, Wd - 1)] & free[rows, np.minimum(xr + 2, Wd - 1)] & (xr < Wd - 2)
    planes = []; minw = prm.get("min_plane_mm", 4.0) * ev.ppm; min_hip = prm.get("min_hip_slope_deg", 10.0)
    span = cols[-1] - cols[0] + 1; c_lo, c_hi = cols[0], cols[-1] + 1
    for side in (-1, 1):
        e = xl if side < 0 else xr; fe = fl if side < 0 else fr
        corner = int(np.argmin(e)) if side < 0 else int(np.argmax(e))          # the eave corner: the outermost row
        er = np.arange(0, corner + 1)
        pe = [(float(px_mm(ev, 0, e[i])[0]), float(px_mm(ev, rows[i], 0)[1])) for i in er if fe[i]]
        tc = np.arange(0, rs) if side < 0 else np.arange(re_, len(cols))
        pt = [(float(xs[i]), float(ytop[i])) for i in tc if ftop[i]]
        pts = pe + pt
        if len(pts) < 6: continue
        fh = fit_line(pts)
        if fh is None or abs(slope(fh[0])) < min_hip: continue
        inner = max([e[i] for i in er] + ([cols[i] for i in tc] if len(tc) else [])) if side < 0 else \
            min([e[i] for i in er] + ([cols[i] for i in tc] if len(tc) else []))
        c0, c1 = (cols[0], int(inner) + 1) if side < 0 else (int(inner), cols[-1] + 1)
        if c1 - c0 < minw or c1 - c0 > prm.get("max_hip_frac", 0.45) * span: continue
        planes.append(dict(side=side, c0=int(c0), c1=int(c1), hip_pts=subsample(pts, 40)))
        if side < 0: c_lo = c1
        else: c_hi = c0
    if c_hi - c_lo < minw:                                       # no room for a front plane: hips only would be a guess
        planes = []; c_lo, c_hi = cols[0], cols[-1] + 1
    planes.append(dict(side=0, c0=int(c_lo), c1=int(c_hi), hip_pts=None))
    return dict(eave_pts=eave_pts, top_pts=top_pts, eave_visible=bool(eave_visible), eave_deg=round(eave_deg, 3),
                eave_y=float(np.median(ybot)), x0=float(xs.min()), x1=float(xs.max()), planes=planes, cols=cols, bot=bot,
                top=top, height_mm=round(float(h), 3), free_top=round(float(ftop.mean()), 3))


def eave_band(ev, comp, fit, w_mm, tol_mm):
    """the eave: a straight band w_mm wide along the fitted eave line, over the longest run of columns whose bottom edge
    lies within tol_mm of that line (the upturned tips are left to the roof / trims). Returns (cl [(x, y)] mm, mask) or
    (None, None)."""
    cols, bot = fit["cols"], fit["bot"]
    xs, yb = px_mm(ev, bot + 0.5, cols)
    f = fit_line(fit["eave_pts"])
    if f is None: return None, None
    a = math.radians(f[0]); cx, cy = f[1]
    def line_y(x): return cy + (x - cx) * math.tan(a) if abs(math.cos(a)) > 1e-6 else cy
    near = np.abs(yb - np.array([line_y(x) for x in xs])) <= tol_mm
    r = longest_run(near)
    if r is None or (xs[r[1] - 1] - xs[r[0]]) < 2.5 * w_mm: return None, None
    xa, xb = float(xs[r[0]]) - 0.5 / ev.ppm, float(xs[r[1] - 1]) + 0.5 / ev.ppm
    cl = [(xa, line_y(xa) - w_mm / 2.0), (xb, line_y(xb) - w_mm / 2.0)]
    from shapely.geometry import LineString
    g = LineString(cl).buffer(w_mm / 2.0, cap_style=2)
    return [(round(x, 3), round(y, 3)) for x, y in cl], g


def tile_lines(poly, angle, sp, inset=0.8, min_len=2.0):
    """bean tile lines down the slope: hatch lines at `angle` every sp mm across poly (inset), longest piece per line,
    joined end to end in a serpentine (short steps along the plane's edge) -> [(x, y)] or None"""
    from shapely.geometry import LineString
    from shapely import affinity
    q = poly.buffer(-inset)
    if q.is_empty: return None
    c = q.centroid; r = affinity.rotate(q, -angle, origin=c)          # lines run along +x in the rotated frame
    x0, y0, x1, y1 = r.bounds; segs = []
    n = int((y1 - y0) // sp)
    off = y0 + ((y1 - y0) - n * sp) / 2.0
    for k in range(n + 1):
        y = off + k * sp
        ln = r.intersection(LineString([(x0 - 1, y), (x1 + 1, y)]))
        parts = [g for g in getattr(ln, "geoms", [ln]) if g.geom_type == "LineString" and g.length >= min_len]
        if not parts: continue
        g = max(parts, key=lambda g: g.length); segs.append(list(g.coords))
    if not segs: return None
    from shapely.ops import substring
    from shapely.geometry import Point as _P
    rq = r if r.geom_type == "Polygon" else max(r.geoms, key=lambda g: g.area)
    ring = LineString(rq.exterior.coords); RL = ring.length
    def step(a, b):
        """connector a -> b along the plane's (inset) edge, the shorter way round (a straight cut would show)"""
        if _P(a).distance(ring) > 0.3 or _P(b).distance(ring) > 0.3: return []
        da, db = ring.project(_P(a)), ring.project(_P(b))
        lo, hi = min(da, db), max(da, db)
        if hi - lo <= RL / 2: cs = list(substring(ring, lo, hi).coords)
        else: cs = list(substring(ring, hi, RL).coords) + list(substring(ring, 0, lo).coords)[1:]
        if math.dist(cs[0], a) > math.dist(cs[-1], a): cs = cs[::-1]
        return cs[1:-1]
    path = []
    for i, s in enumerate(segs):
        s = s if i % 2 == 0 else s[::-1]
        if path: path += step(path[-1], s[0])
        path += s
    back = affinity.rotate(LineString(path), angle, origin=c)
    return [(round(x, 3), round(y, 3)) for x, y in back.coords]


def rect_axis(g):
    """minimum rotated rectangle of g -> (long-axis chord [(x, y), (x, y)] through its centre, long, short) mm"""
    r = g.minimum_rotated_rectangle
    if r.geom_type != "Polygon": return None, 0.0, 0.0
    c = list(r.exterior.coords)[:4]
    e = [(math.dist(c[i], c[(i + 1) % 4]), i) for i in range(4)]
    L, i = max(e); S = min(e)[0]
    a, b = c[i], c[(i + 1) % 4]; ux, uy = (b[0] - a[0]) / max(L, 1e-9), (b[1] - a[1]) / max(L, 1e-9)
    if ux < -1e-9 or (abs(ux) <= 1e-9 and uy < 0): ux, uy = -ux, -uy   # chord points along +x (or +y when vertical)
    m = r.centroid
    return [(m.x - ux * L / 2, m.y - uy * L / 2), (m.x + ux * L / 2, m.y + uy * L / 2)], L, S
