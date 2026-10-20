"""Seam-true wave by a SMOOTH displacement field (Rev B, coordinator 19 Oct: no paste-and-cut band, no piecewise stretch).

Why: seamfill's continuation band + min-mismatch cut and the row-by-row stretch moved the mismatch from the seam into the
panel, where it read as a cut line (FL: a near-vertical line 0-60 mm in from the side, a horizontal step in the stripes).
Here every piece side is moved by ONE smooth field (thin-plate spline, scipy RBFInterpolator), so stripe centre lines and
tone boundaries stay continuous everywhere - at the seam and inside the panel. Domains: each body piece, and each HALF of a
sleeve (back-view half / front-view half: they meet at the centre line, which is treated like a seam).

  pass 1 - reach the seam: on every silhouette seam (side, shoulder, sleeve underarm) and the sleeve centre line the art
           stops g(s) short (the trace drops the render's edge shading). Control points at the innermost art, displaced
           along the seam normal to the keep-out line (g smoothed along the seam, capped 35 mm, faded to 0 within 40 mm of a
           fixed edge); zero displacement R = 100 mm inside and on every fixed edge (armhole / cap: continuous with the
           sleeve by the seam-length map; CF zip, hem, neck, cuff).
  pass 2 - align the tones: on each such seam the side with less stripe art is the FOLLOWER. Its tone runs 1.5 mm inside
           the keep-out are matched to the leader's runs (dynamic programming on the run sequences: same tone, nearest
           position, run edges to run edges); each matched edge is a control point displaced ALONG the seam onto its partner
           (<= 40 mm); zero at R = 100 mm, on fixed edges and on the seams where this domain leads.
  pass 3 - a stripe of the leader that meets bare fabric on the follower (no partner within 8 mm and nothing ahead)
           continues and TAPERS to a point (seamfill.continue_runs, taper mode only: it ends in fabric, never against art).
Rigid motifs (curls, drops) move with the field at their centre (they stay round) and are then moved whole out of a
keep-out (wrap.push_units). The field is checked for folds (Jacobian determinant > 0.25 on a 4 mm grid) and scaled
down if it would fold."""
import numpy as np
from scipy.interpolate import RBFInterpolator
from shapely.geometry import box, Point, LineString
from shapely.ops import unary_union
from shapely import affinity
import wrap as WR

R_DECAY = 100.0; G_CAP = 35.0; FIX_FADE = 40.0; ALONG_MAX = 40.0; STEP = 8.0

# ---------------------------------------------------------------- domains
def domain_of(size, side):
    """(P, sign) - sign = half of a sleeve (sign of x), 0 for body pieces"""
    if side.P in ("SR", "SL"):
        c = side.region.representative_point(); return (side.P, 1 if c.x > 0 else -1)
    return (side.P, 0)

def domain_region(size, key):
    import pieces as PC
    P, sg = key; pan = PC.panel(size, P)
    if sg == 0: return pan
    return pan.intersection(box(0, -1e4, 1e4, 1e4) if sg > 0 else box(-1e4, -1e4, 0, 1e4))

def fixed_edges(size, key):
    """sew lines that must not move: every edge of the domain that is not a warped seam"""
    import pieces as PC
    P, sg = key; r = PC.refs(size, P); names = {"BK": ["neck", "armhole L", "armhole R", "hem"], "FR": ["CF / zip", "neck", "armhole", "hem"],
                                               "FL": ["CF / zip", "neck", "armhole", "hem"], "SR": ["cap", "cuff"], "SL": ["cap", "cuff"]}[P]
    reg = domain_region(size, key).buffer(0.5)
    out = []
    for nm in names:
        g = r[nm].intersection(reg)
        for l in getattr(g, "geoms", [g]):
            if l.geom_type == "LineString" and l.length > 2: out.append(l)
    return out

def warped_sides(size):
    out = []
    for sm in WR.seams(size):
        if sm["kind"] not in ("silhouette", "internal"): continue
        A, B = WR.SeamSide(size, sm, "A"), WR.SeamSide(size, sm, "B")
        out.append((sm, A, B))
    return out

def split_items(art, size):
    """{domain: [items]}: sleeve items split by half (rigid units whole, by their centre)"""
    D = {}; cen = {}
    for P, its in art.items():
        if P not in ("SR", "SL"): D[(P, 0)] = list(its); continue
        for r in its:
            if r.get("unit"): cen.setdefault((P, r["unit"]), []).append(r["geom"])
        cen_ = {k: unary_union(v).centroid.x for k, v in cen.items() if k[0] == P}
        for sg in (1, -1): D[(P, sg)] = []
        hb = {1: box(0, -1e4, 1e4, 1e4), -1: box(-1e4, -1e4, 0, 1e4)}
        for r in its:
            if r.get("unit"):
                D[(P, 1 if cen_[(P, r["unit"])] > 0 else -1)].append(r); continue
            for sg in (1, -1):
                g = r["geom"].intersection(hb[sg])
                if not g.is_empty and g.area > 0.2: D[(P, sg)].append(dict(r, geom=g.buffer(0)))
    return D

def join_items(D):
    art = {}
    for (P, sg), its in D.items(): art.setdefault(P, []).extend(its)
    return art

# ---------------------------------------------------------------- field
class Field:
    def __init__(self, pts, disp, key):
        self.key = key; self.ok = len(pts) > 3 and np.abs(disp).max() > 0.05 if len(pts) else False
        if self.ok: self.f = RBFInterpolator(np.asarray(pts, float), np.asarray(disp, float), kernel="thin_plate_spline", smoothing=1e-3)
        self.scale = 1.0
    def __call__(self, X, Y):
        X = np.asarray(X, float); Y = np.asarray(Y, float)
        if not self.ok: return X, Y
        P = np.c_[X.ravel(), Y.ravel()]; U = self.f(P) * self.scale
        return (X.ravel() + U[:, 0]).reshape(X.shape), (Y.ravel() + U[:, 1]).reshape(Y.shape)
    def check_folds(self, region, h=4.0, det_min=0.25):
        if not self.ok: return 1.0
        b = region.bounds; xs = np.arange(b[0], b[2], h); ys = np.arange(b[1], b[3], h)
        XX, YY = np.meshgrid(xs, ys)
        import shapely
        ins = shapely.contains_xy(region, XX, YY)
        for _ in range(6):
            X1, Y1 = self(XX, YY)
            jx = np.gradient(X1, h); jy = np.gradient(Y1, h)
            det = (jx[1] * jy[0] - jx[0] * jy[1])[ins]
            if det.size == 0 or det.min() > det_min: return float(det.min()) if det.size else 1.0
            self.scale *= 0.8
        return float(det.min())

def apply(items, field):
    if not field.ok: return items
    cen = {}
    for r in items:
        if r.get("unit"): cen.setdefault(r["unit"], []).append(r["geom"])
    mv = {}
    for u, gs in cen.items():
        c = unary_union(gs).centroid; X, Y = field(np.array([c.x]), np.array([c.y])); mv[u] = (float(X[0] - c.x), float(Y[0] - c.y))
    out = []
    for r in items:
        if r.get("unit"):
            m0 = r.get("mv", (0.0, 0.0)); d_ = mv[r["unit"]]
            out.append(dict(r, geom=affinity.translate(r["geom"], *d_), mv=(m0[0] + d_[0], m0[1] + d_[1]))); continue
        g = WR.map_pts(r["geom"], lambda x, y: field(x, y), densify=1.0)
        if g is not None and not g.is_empty: out.append(dict(r, geom=g))
    return out

def zero_anchors(size, key, warped_here, R=R_DECAY):
    """zero-displacement points: on fixed edges every 15 mm, and R mm inside every warped seam of this domain"""
    pts = []
    for l in fixed_edges(size, key):
        for s in np.arange(0, l.length + 1e-6, 15.0): pts.append(l.interpolate(s).coords[0])
    reg = domain_region(size, key)
    for side in warped_here:
        for u in np.linspace(0, 1, max(3, int(side.L / 20))):
            p = side.point(float(u), R)
            if reg.contains(Point(p)): pts.append(p)
    # the far interior: a coarse grid of zeros beyond R from every warped seam
    b = reg.bounds; lines = unary_union([s.line for s in warped_here]) if warped_here else None
    for x in np.arange(b[0], b[2], 40.0):
        for y in np.arange(b[1], b[3], 40.0):
            q = Point(x, y)
            if reg.contains(q) and (lines is None or lines.distance(q) > R + 10): pts.append((x, y))
    return pts

def fade_fixed(size, key, p):
    """1 at >= FIX_FADE from every fixed edge, 0 on it (no shear against the armhole / hem / CF / cuff)"""
    fx = fixed_edges(size, key)
    if not fx: return 1.0
    d = min(l.distance(Point(p)) for l in fx); return float(np.clip(d / FIX_FADE, 0, 1))

# ---------------------------------------------------------------- pass 1: reach the seam
def innermost(items, side, s_mm, gap, depth=60.0, w=STEP):
    """distance from the seam to the nearest art in a w-mm strip at s_mm (None if no art within depth)"""
    u0, u1 = max(0, (s_mm - w / 2) / side.L), min(1, (s_mm + w / 2) / side.L)
    a, b = side.point(u0, 0), side.point(u1, 0); n0, n1 = side.normal_in(u0), side.normal_in(u1)
    from shapely.geometry import Polygon
    strip = Polygon([a, b, (b[0] + n1[0] * depth, b[1] + n1[1] * depth), (a[0] + n0[0] * depth, a[1] + n0[1] * depth)]).buffer(0)
    best = None
    for r in items:
        if r["grp"] in ("FM-loop", "FM-curl"): continue
        g = r["geom"]
        if not g.intersects(strip): continue
        q = g.intersection(strip)
        if q.is_empty or q.area < 1.0: continue
        dd = side.line.distance(q)
        best = dd if best is None else min(best, dd)
    return best

def pass1(D, size, gap_body, gap_int):
    log = {}; ctrl = {k: ([], []) for k in D}; warped = {k: [] for k in D}
    for sm, A, B in warped_sides(size):
        gap = gap_int if sm["kind"] == "internal" else gap_body
        for side in (A, B):
            key = domain_of(size, side); warped[key].append(side)
            its = D[key]; ss = np.arange(STEP / 2, side.L, STEP)
            g = np.array([innermost(its, side, s, gap) for s in ss], dtype=object)
            have = np.array([v is not None for v in g]); gv = np.array([v if v is not None else np.nan for v in g], float)
            if not have.any(): continue
            # smooth along the seam over rows with art; rows > 24 mm from art get no control point (the field interpolates)
            from scipy.ndimage import gaussian_filter1d
            idx = np.arange(len(ss)); fill = np.interp(idx, idx[have], np.minimum(gv[have], G_CAP))
            sm_g = gaussian_filter1d(fill, 1.5)
            near = np.array([np.min(np.abs(idx[have] - i)) for i in idx]) * STEP <= 24.0
            n_ = 0
            for i, s in enumerate(ss):
                if not near[i]: continue
                gg = float(sm_g[i]); u = s / side.L
                p = side.point(u, gg); nrm = side.normal_in(u)
                amt = max(0.0, gg - gap) * fade_fixed(size, key, p)
                ctrl[key][0].append(p); ctrl[key][1].append((-nrm[0] * amt, -nrm[1] * amt)); n_ += 1
            log[f"{sm['name']}:{side.which}"] = dict(g_median=round(float(np.median(gv[have])), 1), g_max=round(float(np.nanmax(gv)), 1), ctrl=n_)
    fields = {}
    for key in D:
        z = zero_anchors(size, key, warped[key])
        pts = ctrl[key][0] + z; disp = ctrl[key][1] + [(0.0, 0.0)] * len(z)
        F = Field(pts, np.array(disp), key); dm = F.check_folds(domain_region(size, key))
        D[key] = apply(D[key], F); fields[key] = dict(ctrl=len(ctrl[key][0]), scale=round(F.scale, 2), det_min=round(dm, 2)); FIELDS.setdefault(key, []).append(F)
    return log, fields, warped

# ---------------------------------------------------------------- pass 2: align tones along the seam
def runs_of(lab, min_len=2):
    out = []; i = 0; n = len(lab)
    while i < n:
        k = lab[i]
        if k is None: i += 1; continue
        j = i
        while j + 1 < n and lab[j + 1] == k: j += 1
        if j - i + 1 >= min_len: out.append((i, j, k))
        i = j + 1
    return out

TONE_IX = {k: i for i, k in enumerate(["b0", "b1", "b2", "b3", "b4", "b5"])}
def run_cost(a, b):
    if a[2] == b[2]: c = 0.0
    elif a[2] in TONE_IX and b[2] in TONE_IX: c = 0.25 + 0.12 * abs(TONE_IX[a[2]] - TONE_IX[b[2]])
    else: c = 1.2
    return c + abs(0.5 * (a[0] + a[1]) - 0.5 * (b[0] + b[1])) / 30.0

def match_runs(ra, rb, skip=0.9):
    """monotone DP matching of two run sequences (skips allowed). Returns [(i, j)]"""
    n, m = len(ra), len(rb); INF = 1e18
    C = np.full((n + 1, m + 1), INF); C[0, :] = np.arange(m + 1) * skip; C[:, 0] = np.arange(n + 1) * skip
    bk = np.zeros((n + 1, m + 1), int)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            c = run_cost(ra[i - 1], rb[j - 1])
            opts = (C[i - 1, j - 1] + c, C[i - 1, j] + skip, C[i, j - 1] + skip)
            k = int(np.argmin(opts)); C[i, j] = opts[k]; bk[i, j] = k
    i, j = n, m; pairs = []
    while i > 0 and j > 0:
        k = bk[i, j]
        if k == 0:
            if run_cost(ra[i - 1], rb[j - 1]) < 1.0 and abs(0.5 * (ra[i - 1][0] + ra[i - 1][1]) - 0.5 * (rb[j - 1][0] + rb[j - 1][1])) <= ALONG_MAX: pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif k == 1: i -= 1
        else: j -= 1
    return pairs[::-1]

def smooth_shift(lL, lF, win=60, lag_max=int(ALONG_MAX), sigma=10.0, grad_max=0.45):
    """along-seam displacement of the follower (mm on the leader's scale: F sample j -> L at j + shift[j]): for every 4 mm a
    window of +/- win/2 mm is slid over the leader within +/- lag_max and scored (same tone +1, neighbouring blue +0.5, art vs
    bare -0.4, bare vs bare 0); the best lag per window (only where the window has stripes on both sides) is smoothed
    (sigma mm) and slope-limited (|d shift / ds| <= grad_max - a stripe is never squeezed or stretched more than 45 %)"""
    from scipy.ndimage import gaussian_filter1d
    n = len(lF); code = {None: -1}
    toneix = {k: i for i, k in enumerate(["b0", "b1", "b2", "b3", "b4", "b5"])}
    def val(x): return -1 if x is None else (toneix.get(x, 10))
    a = np.array([val(x) for x in lL]); b = np.array([val(x) for x in lF])
    if n < 16 or (a >= 0).sum() < 6 or (b >= 0).sum() < 6: return np.zeros(n)
    def score(x, y):
        s_ = np.where((x >= 0) & (y >= 0), np.where(x == y, 1.0, np.where((np.abs(x - y) == 1) & (x < 10) & (y < 10), 0.5, -0.2)), 0.0)
        return s_ + np.where((x >= 0) ^ (y >= 0), -0.4, 0.0)
    cs, ls, ws = [], [], []
    h = win // 2
    for c in range(0, n, 4):
        j0, j1 = max(0, c - h), min(n, c + h); seg = b[j0:j1]
        if (seg >= 0).sum() < 4: continue
        best, bl = -1e9, 0
        for lag in range(-lag_max, lag_max + 1):
            i0_, i1_ = j0 + lag, j1 + lag
            if i0_ < 0 or i1_ > n: continue
            sc = score(a[i0_:i1_], seg).sum() - 0.01 * abs(lag)
            if sc > best: best, bl = sc, lag
        if best > 2.0: cs.append(c); ls.append(bl); ws.append(best)
    if not cs: return np.zeros(n)
    out = np.interp(np.arange(n), cs, ls)
    cov = np.zeros(n)
    for c in cs: cov[max(0, c - h):c + h] = 1
    out = gaussian_filter1d(out * cov, sigma) / np.maximum(gaussian_filter1d(cov, sigma), 1e-6) * np.clip(gaussian_filter1d(cov, sigma) / 0.5, 0, 1)
    for _ in range(300):
        d = np.diff(out)
        if not (np.abs(d) > grad_max).any(): break
        out = np.r_[out[0], out[0] + np.cumsum(np.clip(d, -grad_max, grad_max))]
    return np.clip(out, -ALONG_MAX, ALONG_MAX)

def run_shift(lL, lF, coarse, grad_max=0.8, sigma=3.0):
    """refine the coarse lag: after it, the follower's runs are matched to the leader's (match_runs: same / near tone,
    order kept) and each matched run's two edges are pinned onto the partner's edges; piecewise linear between pins (a
    monotone map of the seam, so no fold), fading to the coarse lag 30 mm beyond the last pin, slope-limited"""
    from scipy.ndimage import gaussian_filter1d
    n = len(lF); idx = np.arange(n)
    # follower labels as seen after the coarse lag
    lF_c = [None] * n
    for j in range(n):
        k = int(round(j + coarse[j]))
        if 0 <= k < n and lF[j] is not None: lF_c[k] = lF[j]
    rL, rF = runs_of(lL), runs_of(lF_c)
    if not rL or not rF: return coarse
    pins = []
    for i, j in match_runs(rL, rF):
        for eL, eF in ((rL[i][0], rF[j][0]), (rL[i][1], rF[j][1])): pins.append((eF, eL - eF))
    if not pins: return coarse
    pins.sort(); xs = np.array([p_[0] for p_ in pins], float); ds = np.array([p_[1] for p_ in pins], float)
    keep = [0]
    for q in range(1, len(xs)):                                            # monotone: target positions must increase
        if xs[q] + ds[q] > xs[keep[-1]] + ds[keep[-1]] + 0.5 and xs[q] > xs[keep[-1]]: keep.append(q)
    xs, ds = xs[keep], ds[keep]
    extra = np.interp(idx, xs, ds)
    fade = np.clip(1 - np.maximum(xs[0] - idx, idx - xs[-1]).clip(0) / 30.0, 0, 1)
    extra = gaussian_filter1d(extra * fade, sigma)
    # extra is defined on the coarse-shifted axis: bring it back to the follower's own axis
    tgt = idx + coarse
    out = coarse + np.interp(tgt, idx, extra)
    for _ in range(300):
        d = np.diff(out)
        if not (np.abs(d) > grad_max).any(): break
        out = np.r_[out[0], out[0] + np.cumsum(np.clip(d, -grad_max, grad_max))]
    return np.clip(out, -ALONG_MAX - 10, ALONG_MAX + 10)

def band(items): return [r for r in items if r["grp"] in WR.BAND_GRPS]

def pass2(D, size, gap_body, gap_int, warped):
    log = {}; ctrl = {k: ([], []) for k in D}; lead_sides = {k: [] for k in D}
    for sm, A, B in warped_sides(size):
        gap = gap_int if sm["kind"] == "internal" else gap_body; d0 = gap + 1.5
        kA, kB = domain_of(size, A), domain_of(size, B)
        la = WR.labels(band(D[kA]), A, d0, 1.0); lb = WR.labels(band(D[kB]), B, d0, B.L / A.L)
        n = min(len(la), len(lb)); la, lb = la[:n], lb[:n]
        lead_A = sum(x is not None for x in la) >= sum(x is not None for x in lb)
        L_, F_, lL, lF, kF = (A, B, la, lb, kB) if lead_A else (B, A, lb, la, kA)
        lead_sides[domain_of(size, L_)].append(L_)
        rL, rF = runs_of(lL), runs_of(lF)
        before = WR.art_match(lL, lF)
        sh = run_shift(lL, lF, smooth_shift(lL, lF))                          # mm on A's scale, F sample j -> L at j + sh[j]
        for j in range(0, n, 6):
            uF = min(j / n, 1.0); ds = float(sh[j]) * F_.L / n
            p = F_.point(uF, d0); t0 = np.array(F_.point(min(uF + 0.002, 1), 0)) - np.array(F_.point(max(uF - 0.002, 0), 0)); t0 /= max(np.hypot(*t0), 1e-9)
            amt = ds * fade_fixed(size, kF, p)
            ctrl[kF][0].append(p); ctrl[kF][1].append((t0[0] * amt, t0[1] * amt))
        pairs = [j for j in range(n) if abs(sh[j]) > 0.5]
        log[sm["name"]] = dict(leader=L_.P + ("" if L_.P != F_.P else (" A" if lead_A else " B")), runs=[len(rL), len(rF)], shifted_mm=len(pairs),
                               shift_max=round(float(np.abs(sh).max()) * F_.L / n, 1) if n else 0.0, tone_match_before=round(before, 2))
    fields = {}
    for key in D:
        if not ctrl[key][0]: continue
        z = zero_anchors(size, key, warped[key])
        for side in lead_sides[key]:                                         # this domain leads there: keep its seam still
            for u in np.linspace(0, 1, max(3, int(side.L / 15))): z.append(side.point(float(u), 4.9))
        pts = ctrl[key][0] + z; disp = ctrl[key][1] + [(0.0, 0.0)] * len(z)
        F = Field(pts, np.array(disp), key); dm = F.check_folds(domain_region(size, key))
        D[key] = apply(D[key], F); fields[key] = dict(ctrl=len(ctrl[key][0]), scale=round(F.scale, 2), det_min=round(dm, 2)); FIELDS.setdefault(key, []).append(F)
    for sm, A, B in warped_sides(size):                                      # tone agreement after the warp
        gap = gap_int if sm["kind"] == "internal" else gap_body; d0 = gap + 1.5
        la = WR.labels(band(D[domain_of(size, A)]), A, d0, 1.0); lb = WR.labels(band(D[domain_of(size, B)]), B, d0, B.L / A.L)
        log[sm["name"]]["tone_match_after"] = round(WR.art_match(la[:len(lb)], lb[:len(la)]), 2)
    return log, fields

# ---------------------------------------------------------------- pass 3: tapers into bare fabric only
def pass3(art, size, gap_body, gap_int):
    import seamfill as SF
    log = {}
    for sm in WR.seams(size):
        if sm["kind"] == "zip": continue
        gap = gap_int if sm["kind"] == "internal" else gap_body
        log[sm["name"]] = SF.fill_seam(art, size, sm, gap, modes=("taper",))
    return log

FIELDS = {}
def warp_grid(size, h=3.0):
    """the composed displacement (pass 1 then pass 2) of every domain sampled on an h-mm grid - gates.py maps the mockup
    reference through it, so the A14 / A15 checks compare like with like"""
    out = {}
    for key, Fs in FIELDS.items():
        reg = domain_region(size, key); b = reg.bounds
        xs = np.arange(b[0] - 6, b[2] + 6, h); ys = np.arange(b[1] - 6, b[3] + 6, h); XX, YY = np.meshgrid(xs, ys)
        X, Y = XX.copy(), YY.copy()
        for F in Fs: X, Y = F(X, Y)
        out[f"{key[0]}|{key[1]}"] = dict(x0=float(xs[0]), y0=float(ys[0]), h=h, ux=(X - XX).astype(np.float32), uy=(Y - YY).astype(np.float32))
    return out

def run(art, size, gap_body=WR.GAP + 0.4, gap_int=0.5):
    """edits art {P: items} in place; returns the log"""
    FIELDS.clear()
    D = split_items(art, size)
    l1, f1, warped = pass1(D, size, gap_body + 0.6, gap_int)
    l2, f2 = pass2(D, size, gap_body, gap_int, warped)
    new = join_items(D)
    for P in art: art[P] = new.get(P, [])
    pushed = {}
    for sm, A, B in warped_sides(size):
        if sm["kind"] == "internal": continue
        pushed[sm["name"]] = [WR.push_units(art[s.P], s, gap_body + 0.6) for s in (A, B)]
    l3 = pass3(art, size, gap_body, gap_int)
    grid = warp_grid(size)
    return dict(grid=grid, reach=l1, reach_fields={f"{k[0]}{'' if not k[1] else ('+' if k[1] > 0 else '-')}": v for k, v in f1.items()},
                align=l2, align_fields={f"{k[0]}{'' if not k[1] else ('+' if k[1] > 0 else '-')}": v for k, v in f2.items()},
                pushed=pushed, tapers=l3)
