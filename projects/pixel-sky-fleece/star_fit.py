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
