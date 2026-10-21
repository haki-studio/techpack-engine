"""Pixel-art motif fit for SMALL motifs on a low-res render (PR #28 review: a 6 mm 4-arm sparkle came out as a square,
two touching sparkles as one blob).

At 0.6 mm/px a 2 mm sparkle arm is ~3 render px and the render is anti-aliased, so a hard 0.5-coverage trace of the
blurred blob fills the corners (plus -> square). Instead every candidate staircase is scored against the SOFT motif map
of the render (how much each render pixel is motif colour, 0..1), with a soft IoU on a fine grid:
  - candidates: the plain staircase (cells >= 50 % covered) and the D4-symmetric staircase (the cell coverage averaged
    over the 8 mirror/rotations of the square, thresholds 0.35..0.65), for every candidate cell size and grid phase.
  - pixel-art sparkles are drawn 4-fold symmetric; the D4 candidate wins only when the render supports it.
Generic: no template, no motif-specific shape; inputs are the render pixels only (A14)."""
import math
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import box
from shapely.ops import unary_union
import mockmap as MM

FINE = 0.125                                          # mm per fine-grid px

def soft_map(xs, ys, pad_px=4):
    """soft motif map on the render around the component: min(not-sky, not-black) by channel (sky b=247, motif b<=60;
    black r=40, motif r>=220) -> 0..1; restricted to the component +- pad (so neighbours do not count)"""
    a = MM.img(); x0, x1 = xs.min() - pad_px, xs.max() + pad_px + 1; y0, y1 = ys.min() - pad_px, ys.max() + pad_px + 1
    sub = a[y0:y1, x0:x1]
    s = np.minimum(np.clip((247 - sub[..., 2]) / 190.0, 0, 1), np.clip((sub[..., 0] - 40) / 180.0, 0, 1))
    m = np.zeros(s.shape, bool); m[ys - y0, xs - x0] = True
    s = s * ndi.binary_dilation(m, iterations=2)
    return s, (x0, y0)

def _fine(s, org):
    """render-px soft map -> fine grid (bilinear) + its mm origin"""
    k = MM.S / FINE
    F = ndi.zoom(s, k, order=1, grid_mode=True, mode="nearest")
    ox, oy = MM.P(org[0], org[1])
    return np.clip(F, 0, 1), (float(ox), float(oy))

def d4(M):
    Ms = [M, M[::-1], M[:, ::-1], M[::-1, ::-1]]
    return np.mean(Ms + [m.T for m in Ms], axis=0)

def fit(xs, ys, cells=(2.5, 2.0, 1.67, 1.25), nofs=6, thresholds=(0.35, 0.45, 0.55, 0.65), prefer_coarse=0.02, kinds=("plain", "d4")):
    """-> (geometry front mm, soft IoU, cell mm, kind 'plain'|'d4', hard-mask pixel polygon for the A14 reference)"""
    s, org = soft_map(xs, ys); F, (fx, fy) = _fine(s, org); H, W = F.shape
    tot = F.sum(); best = None
    cx = fx + (F * np.arange(W)[None]).sum() / tot * FINE; cy = fy + (F * np.arange(H)[:, None]).sum() / tot * FINE
    span = max(W, H) * FINE
    for c in cells:
        n = int(round(c / FINE))
        for even in (False, True):
            K = int(math.ceil(span / c / 2)) + 1; N = 2 * K + (0 if even else 1)
            for dx in np.arange(-c / 2, c / 2, c / nofs):
                for dy in np.arange(-c / 2, c / 2, c / nofs):
                    ox, oy = cx + dx - N * c / 2, cy + dy - N * c / 2
                    i0, j0 = int(round((ox - fx) / FINE)), int(round((oy - fy) / FINE))
                    # cell coverage: pad F so every cell is inside
                    P = np.zeros((N * n, N * n))
                    a0, b0 = max(0, -j0), max(0, -i0); a1, b1 = min(N * n, H - j0), min(N * n, W - i0)
                    if a1 <= a0 or b1 <= b0: continue
                    P[a0:a1, b0:b1] = F[j0 + a0:j0 + a1, i0 + b0:i0 + b1]
                    M = P.reshape(N, n, N, n).mean(axis=(1, 3))
                    cands = [("plain", M >= 0.5)] + [("d4", d4(M) >= t) for t in thresholds]
                    out_mass = tot - P.sum()                       # soft mass outside the candidate grid
                    for kind, S in cands:
                        if kind not in kinds or not S.any(): continue
                        O = np.kron(S, np.ones((n, n)))
                        inter = np.minimum(O, P).sum(); uni = np.maximum(O, P).sum() + out_mass
                        iou = inter / uni
                        score = iou + prefer_coarse * (c / cells[0]) + (0.01 if kind == "d4" else 0.0)
                        if best is None or score > best[0]:
                            best = (score, iou, c, kind, [(ox + b * c, oy + a * c) for a, b in zip(*np.nonzero(S))])
    _, iou, c, kind, tl = best
    g = unary_union([box(x, y, x + c, y + c) for x, y in tl]).buffer(0)
    return g, float(iou), c, kind


# ---------------------------------------------------------------- family exemplar for motifs too small to resolve
MAX_FILL = 0.70          # family drawings fill 0.53-0.66 of their box (plus 0.56); a near-solid resample (0.75+) is no sparkle
SMALL_MM = 16.0          # motifs under this (< ~27 render px) are blurred past their own pixel steps on a 0.6 mm/px render

def to_matrix(g, cell):
    """staircase geometry on a cell grid -> bool matrix (rows = y)"""
    from shapely.geometry import Point
    x0, y0, x1, y1 = g.bounds; nx, ny = int(round((x1 - x0) / cell)), int(round((y1 - y0) / cell))
    return np.array([[g.contains(Point(x0 + (i + 0.5) * cell, y0 + (j + 0.5) * cell)) for i in range(nx)] for j in range(ny)])

def exemplar(g, cell):
    """the best-resolved family member's cell matrix, made square + D4-symmetric (the family's drawing rule)"""
    M = to_matrix(g, cell).astype(float); n = max(M.shape); P = np.zeros((n, n))
    a, b = (n - M.shape[0]) // 2, (n - M.shape[1]) // 2; P[a:a + M.shape[0], b:b + M.shape[1]] = M
    return d4(P) >= 0.5

def scaled(E, N):
    """exemplar matrix resampled to N x N cells (nearest, centre sampling): 13 -> 3 gives the plus, -> 5 the small star"""
    n = E.shape[0]; idx = [min(n - 1, int((k + 0.5) * n / N)) for k in range(N)]
    return E[np.ix_(idx, idx)]

def fit_exemplar(xs, ys, E, cell_range=(1.25, 3.0), nofs=6):
    """small motif = the family exemplar scaled to N cells, N and phase by soft IoU vs the render -> (geom, iou, cell, N)"""
    s, org = soft_map(xs, ys); F, (fx, fy) = _fine(s, org); H, W = F.shape; tot = F.sum()
    cx = fx + (F * np.arange(W)[None]).sum() / tot * FINE; cy = fy + (F * np.arange(H)[:, None]).sum() / tot * FINE
    best = None
    for N in range(3, 12):
        S = scaled(E, N)
        if not S.any(): continue
        for c in np.arange(cell_range[0], cell_range[1] + 1e-6, 0.125):
            n = int(round(c / FINE)); c = n * FINE
            for dx in np.arange(-c / 2, c / 2, c / nofs):
                for dy in np.arange(-c / 2, c / 2, c / nofs):
                    ox, oy = cx + dx - N * c / 2, cy + dy - N * c / 2
                    i0, j0 = int(round((ox - fx) / FINE)), int(round((oy - fy) / FINE))
                    P = np.zeros((N * n, N * n))
                    a0, b0 = max(0, -j0), max(0, -i0); a1, b1 = min(N * n, H - j0), min(N * n, W - i0)
                    if a1 <= a0 or b1 <= b0: continue
                    P[a0:a1, b0:b1] = F[j0 + a0:j0 + a1, i0 + b0:i0 + b1]
                    O = np.kron(S, np.ones((n, n)))
                    iou = np.minimum(O, P).sum() / (np.maximum(O, P).sum() + tot - P.sum())
                    if best is None or iou > best[0]: best = (iou, c, N, [(ox + b * c, oy + a * c) for a, b in zip(*np.nonzero(S))])
    iou, c, N, tl = best
    return unary_union([box(x, y, x + c, y + c) for x, y in tl]).buffer(0), float(iou), float(c), N


def fit_forward(xs, ys, E, sigma_px=0.8, cell_range=(1.25, 3.0), Ns=range(3, 12), nofs=4):
    """FORWARD-MODEL fit (blurred render): each candidate (family exemplar scaled to N cells, cell size, phase) is
    blurred with the render's anti-alias PSF (gaussian sigma_px render px) and compared with the soft motif map by
    squared error. A plain IoU on blurred data rewards blobs (the blur fills a plus's corners); comparing blurred with
    blurred does not. -> (geom, rmse, cell, N)"""
    s, org = soft_map(xs, ys, pad_px=6); F, (fx, fy) = _fine(s, org); H, W = F.shape; tot = F.sum()
    cx = fx + (F * np.arange(W)[None]).sum() / tot * FINE; cy = fy + (F * np.arange(H)[:, None]).sum() / tot * FINE
    sig = sigma_px * MM.S / FINE; best = None
    Es = E if isinstance(E, (list, tuple)) else [E]
    cand = []
    for X in Es:
        for N in Ns:
            S = scaled(X, N)
            if S.mean() > MAX_FILL: continue                     # a resampled exemplar that became a solid square
            if S.any() and not any(S.shape == q.shape and (S == q).all() for _, q in cand): cand.append((N, S))
    for N, S in cand:
        for c in np.arange(cell_range[0], cell_range[1] + 1e-6, 0.125):
            n = int(round(c / FINE)); c = n * FINE
            if N * c > 1.6 * max(W, H) * FINE: continue
            for dx in np.arange(-c / 2, c / 2, c / nofs):
                for dy in np.arange(-c / 2, c / 2, c / nofs):
                    ox, oy = cx + dx - N * c / 2, cy + dy - N * c / 2
                    i0, j0 = int(round((ox - fx) / FINE)), int(round((oy - fy) / FINE))
                    O = np.zeros((H, W)); Ok = np.kron(S, np.ones((n, n)))
                    a0, b0 = max(0, -j0), max(0, -i0); a1, b1 = min(N * n, H - j0), min(N * n, W - i0)
                    if a1 <= a0 or b1 <= b0: continue
                    O[j0 + a0:j0 + a1, i0 + b0:i0 + b1] = Ok[a0:a1, b0:b1]
                    err = float(np.sqrt(((ndi.gaussian_filter(O, sig) - F) ** 2).mean()))
                    if best is None or err < best[0]: best = (err, c, N, [(ox + b * c, oy + a * c) for a, b in zip(*np.nonzero(S))])
    err, c, N, tl = best
    return unary_union([box(x, y, x + c, y + c) for x, y in tl]).buffer(0), err, float(c), N


# ---------------------------------------------------------------- big motifs: the sprite's OWN pixel unit (fix round 2)
def fit_grid(xs, ys, cells=None, sigma_px=0.8, nofs=4, thresholds=(0.35, 0.5, 0.65)):
    """FORWARD-MODEL staircase on the motif's own pixel unit. A pixel-art sprite is drawn on a coarse unit (the large
    sparkles: ~6 mm units, a 3x3-unit plus or a 5x5-unit stepped plus); tracing it on a fine 2.5 mm cell turns each
    square arm step into a 1-cell stair (PR #28 round 2: 'stepped diamonds where the mockup has blunt plus-shapes').
    For every candidate cell (2.5 .. 9 mm), grid phase and staircase (plain >= 0.5 coverage, D4-symmetric at several
    thresholds) the staircase is blurred with the render PSF and compared with the soft motif map (rmse).
    -> list of (rmse, cell, kind, top-left cells) best per cell, sorted by cell"""
    s, org = soft_map(xs, ys, pad_px=6); F, (fx, fy) = _fine(s, org); H, W = F.shape; tot = F.sum()
    cx = fx + (F * np.arange(W)[None]).sum() / tot * FINE; cy = fy + (F * np.arange(H)[:, None]).sum() / tot * FINE
    sig = sigma_px * MM.S / FINE; span = max(W, H) * FINE
    cells = cells if cells is not None else np.arange(2.5, 9.01, 0.25)
    per = {}
    for c in cells:
        n = int(round(c / FINE)); c = n * FINE
        for even in (False, True):
            K = int(math.ceil(span / c / 2)) + 1; N = 2 * K + (0 if even else 1)
            for dx in np.arange(-c / 2, c / 2, c / nofs):
                for dy in np.arange(-c / 2, c / 2, c / nofs):
                    ox, oy = cx + dx - N * c / 2, cy + dy - N * c / 2
                    i0, j0 = int(round((ox - fx) / FINE)), int(round((oy - fy) / FINE))
                    P = np.zeros((N * n, N * n))
                    a0, b0 = max(0, -j0), max(0, -i0); a1, b1 = min(N * n, H - j0), min(N * n, W - i0)
                    if a1 <= a0 or b1 <= b0: continue
                    P[a0:a1, b0:b1] = F[j0 + a0:j0 + a1, i0 + b0:i0 + b1]
                    M = P.reshape(N, n, N, n).mean(axis=(1, 3))
                    seen = []
                    for kind, S in [("plain", M >= 0.5)] + [("d4", d4(M) >= t) for t in thresholds]:
                        if not S.any() or any((S == q).all() for q in seen): continue
                        seen.append(S)
                        Ok = np.kron(S, np.ones((n, n))); O = np.zeros((H, W))
                        O[j0 + a0:j0 + a1, i0 + b0:i0 + b1] = Ok[a0:a1, b0:b1]
                        err = float(np.sqrt(((ndi.gaussian_filter(O, sig) - F) ** 2).mean()))
                        if c not in per or err < per[c][0]:
                            per[c] = (err, c, kind, [(ox + b * c, oy + a * c) for a, b in zip(*np.nonzero(S))])
    return [per[c] for c in sorted(per)]

UNIT_TOL = 0.012     # the COARSEST cell whose blur-model rmse is within this of the best cell is the sprite's unit

def fit_unit(xs, ys, **kw):
    """-> (geom, rmse, cell, kind, per-cell table) on the sprite's own unit (coarsest cell within UNIT_TOL of the best)"""
    rows = fit_grid(xs, ys, **kw); e0 = min(r[0] for r in rows)
    err, c, kind, tl = [r for r in rows if r[0] <= e0 + UNIT_TOL][-1]
    g = unary_union([box(x, y, x + c, y + c) for x, y in tl]).buffer(0)
    return g, err, c, kind, [(round(r[1], 3), round(r[0], 4)) for r in rows]


# ---------------------------------------------------------------- big motifs: tiered 4-arm sprite (fix round 2)
def cross_mask(H, W, fx, fy, cx, cy, tiers):
    """fine-grid bool mask of a union of D4 crosses: tier (w, L) = rect half-size w x L  U  L x w, centred (cx, cy) mm"""
    X = fx + (np.arange(W) + 0.5) * FINE - cx; Y = fy + (np.arange(H) + 0.5) * FINE - cy
    ax, ay = np.abs(X)[None, :], np.abs(Y)[:, None]; O = np.zeros((H, W), bool)
    for w, L in tiers: O |= ((ax <= w) & (ay <= L)) | ((ax <= L) & (ay <= w))
    return O

def tiers_geom(cx, cy, tiers):
    return unary_union([g for w, L in tiers for g in (box(cx - w, cy - L, cx + w, cy + L), box(cx - L, cy - w, cx + L, cy + w))]).buffer(0)

ARM_MAX = 0.5       # outer tier half-width <= half its length: the family's 4 arms (a 3-unit plus is 0.33)
ARM_OUT = 0.25      # ... and stick out past every inner tier by >= 25 % of their length (no square with nubs)
FREE_GAIN = 0.90    # free (per-edge) fit replaces the 4-fold one only when it cuts the blur-model rmse by >= 10 %
SNAP_MM = 1.25      # (capped at 15 % of the radius on small sparkles) edges closer than this are one pixel edge of the sprite (no sub-pixel slivers or 0.25 mm jogs)

def snap_edges(r, tol=SNAP_MM):
    """rect edge list [x0,x1,y0,y1]*n -> x edges and y edges each clustered (gap < tol) to their cluster mean"""
    r = list(r)
    for axis in (0, 1):
        idx = [i for i in range(len(r)) if (i % 4 < 2) == (axis == 0)]
        idx.sort(key=lambda i: r[i]); groups = [[idx[0]]]
        for i in idx[1:]:
            (groups[-1].append(i) if r[i] - r[groups[-1][-1]] < tol else groups.append([i]))
        for g in groups:
            m = round(float(np.mean([r[i] for i in g])) / 0.25) * 0.25
            for i in g: r[i] = m
    return r

def fit_tiers(xs, ys, kmax=3, sigma_px=0.8, step=0.25, tol=0.004, free_edges=True):
    """A big pixel sparkle = a stack of k concentric D4 crosses (arm, shoulder, centre block: blunt square arms and
    square steps, whatever the render's own pixel unit is). Each tier's half-width w and half-length L is fitted to the
    render by the blur forward model (rmse of the blurred mask vs the soft motif map), coordinate descent at `step` mm
    from several starts; the centre is the soft centroid (4-fold symmetric shape). The fewest tiers within `tol` rmse of
    the best is used (no extra steps the render does not show). Generic: no template; k, w, L all come from the pixels.
    -> (geom, rmse, k, tiers, table {k: rmse})"""
    s, org = soft_map(xs, ys, pad_px=6); F, (fx, fy) = _fine(s, org); H, W = F.shape; tot = F.sum()
    cx = fx + (F * (np.arange(W)[None] + 0.5)).sum() / tot * FINE; cy = fy + (F * (np.arange(H)[:, None] + 0.5)).sum() / tot * FINE
    sig = sigma_px * MM.S / FINE
    X = fx + (np.arange(W) + 0.5) * FINE - cx; Y = fy + (np.arange(H) + 0.5) * FINE - cy
    Rx = float(np.abs(X)[(F >= 0.5).any(axis=0)].max()); Ry = float(np.abs(Y)[(F >= 0.5).any(axis=1)].max()); R = (Rx + Ry) / 2
    cache = {}
    def err(t):
        t = tuple(sorted((round(w / step) * step, round(L / step) * step) for w, L in t))
        if t in cache: return cache[t]
        if any(w <= 0.5 or L < w or L > R + 3 for w, L in t): cache[t] = 9.0; return 9.0
        wa, La = max(t, key=lambda p: p[1])
        if wa > ARM_MAX * La: cache[t] = 9.0; return 9.0          # the outer tier is the ARMS: a sparkle, not a block
        if any(L > (1 - ARM_OUT) * La for w, L in t if (w, L) != (wa, La)): cache[t] = 9.0; return 9.0  # arms stick out
        O = cross_mask(H, W, fx, fy, cx, cy, t).astype(float)
        e = float(np.sqrt(((ndi.gaussian_filter(O, sig) - F) ** 2).mean())); cache[t] = e; return e
    def descend(t):
        t = [list(p) for p in t]; e = err(t); moved = True
        while moved:
            moved = False
            for i in range(len(t)):
                for j in (0, 1):
                    for d in (-step, step, -2 * step, 2 * step):
                        u = [p[:] for p in t]; u[i][j] += d; eu = err(u)
                        if eu < e - 1e-6: t, e, moved = u, eu, True
        return e, [tuple(p) for p in t]
    table = {}; best = {}
    for k in range(1, kmax + 1):
        for f in np.linspace(0.15, 0.45, 4):                  # starts: arm half-width as a fraction of the radius
            if k == 1: t0 = [(f * R, R)]
            elif k == 2: t0 = [(f * R, R), (min(R * 0.9, 3 * f * R), max(3 * f * R, R * 0.6))]
            else: t0 = [(f * R, R), (2 * f * R, R * 0.8), (min(R * 0.9, 3 * f * R), max(3 * f * R, R * 0.6))]
            e, t = descend(t0)
            if k not in best or e < best[k][0]: best[k] = (e, t)
        table[k] = round(best[k][0], 4)
    # free edges: each tier's horizontal and vertical bar gets its own 4 edges (the render is not exactly 4-fold
    # symmetric: sleeve drape, one arm a pixel longer), refined from the symmetric fit by the same descent
    X0 = fx + (np.arange(W) + 0.5) * FINE; Y0 = fy + (np.arange(H) + 0.5) * FINE
    cache2 = {}
    def err2(r):
        key = tuple(round(v / step) for v in r)
        if key in cache2: return cache2[key]
        O = np.zeros((H, W), bool)
        for a in range(0, len(r), 4):
            x0, x1, y0, y1 = r[a:a + 4]
            if x1 - x0 < 1.0 or y1 - y0 < 1.0: cache2[key] = 9.0; return 9.0
            O |= ((X0 >= x0) & (X0 <= x1))[None, :] & ((Y0 >= y0) & (Y0 <= y1))[:, None]
        e = float(np.sqrt(((ndi.gaussian_filter(O.astype(float), sig) - F) ** 2).mean())); cache2[key] = e; return e
    free = {}
    for k, (e, t) in best.items():
        r = []
        for w, L in t: r += [cx - L, cx + L, cy - w, cy + w, cx - w, cx + w, cy - L, cy + L]
        e = err2(r); moved = True
        while moved:
            moved = False
            for i in range(len(r)):
                for d in (-step, step, -2 * step, 2 * step):
                    u = r[:]; u[i] += d; eu = err2(u)
                    if eu < e - 1e-6: r, e, moved = u, eu, True
        free[k] = (e, [round(v / step) * step for v in r]); table[k] = round(e, 4)
    e0 = min(v[0] for v in free.values()); k = min(k for k in free if free[k][0] <= e0 + tol)
    e, r = free[k]; snap = min(SNAP_MM, 0.15 * R)
    ed4, t = best[k]
    if not free_edges or e > FREE_GAIN * ed4:                 # free edges do not explain the render clearly better: keep the 4-fold drawing
        t = sorted((round(w / step) * step, round(L / step) * step) for w, L in t)
        r = []
        for w, L in t: r += [cx - L, cx + L, cy - w, cy + w, cx - w, cx + w, cy - L, cy + L]
        e = ed4; table["kind"] = "D4"
    else: table["kind"] = "free edges"
    r = snap_edges(r, snap)
    g = unary_union([box(r[a], r[a + 2], r[a + 1], r[a + 3]) for a in range(0, len(r), 4)]).buffer(0)
    return g, e, k, r, table
