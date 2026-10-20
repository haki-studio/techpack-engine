"""Informing close-ups (founder ruling 2026-10-20, Koi engine trial): the GARMENT MOCKUP governs, a close-up only INFORMS.
"The close-up is just an AI image, it's not showing the garment ... closeups can help, but the closeup should inform."

So a close-up never moves, adds or removes a motif, and never changes its silhouette or colour. It may only add
INTERIOR detail (petal structure, shading pattern, thread grain) inside a motif the mockup already has, where the
mockup has it:

  1. motif by motif: each informed motif is a window on the mockup (flat px) plus a SIMILARITY map
     flat px -> close-up px (cx = a*px - b*py + tx, cy = b*px + a*py + ty), fitted to THAT motif alone
     (fit_similarity: rotation x scale grid around the global fit, best translation by cross-correlation of the two
     motif masks). Never one global warp: the AI close-up drifts 13 mm (up to 30 mm) from the mockup (Koi
     trace/closeup_reg.json), differently per motif.
  2. the mockup decides WHERE: only pixels inside the mockup's own motif silhouette (the largest one in the window) (far from the fabric colour AND
     blue or light, closed close_mm, holes filled) inside the window can take close-up detail. A close-up motif with
     no mockup motif under it is never sampled; a mockup motif with no close-up detail under it stays mockup.
  3. inside the silhouette a pixel takes the close-up only where the close-up shows embroidery there (not its
     fabric), and its colour is TRANSFERRED to the mockup motif's colour (per-motif mean in Lab), so the
     mockup's colours stay; the close-up gives the pattern of light and dark, not the hue.
Outputs (register.reference): rgb, closeup_weight = 1 where close-up detail was used (direction gates may read grain
there), source_ppm there = the close-up's resolution, weights[<close-up name>] = that mask.

registration.json close-up entry:
  {"name", "view", "file", "mode": "inform", "motif_test": {dist, blue, lum, close_mm},
   "motifs": [{"name", "window": [x0, y0, x1, y1] flat px, "sim": [a, b, tx, ty], "fit": {iou, rot, scale},
               "exclude": [[x0, y0, x1, y1] flat px, ...] (optional: parts of the window that are another motif)}]}
Input pixels only (LESSONS A14): nothing here reads art, scene data or templates."""
import math
import numpy as np
from scipy import ndimage as ndi
from scipy.ndimage import map_coordinates

TEST = dict(dist=45.0, blue=18.0, lum=110.0, close_mm=1.0)
_FAB = {}


def fabric_of(rgb):
    """the fabric colour of an image or crop: the median of its darker half (the shell dominates bare areas)"""
    a = np.asarray(rgb, float).reshape(-1, 3); l = a @ np.array([0.299, 0.587, 0.114])
    return np.median(a[l <= np.median(l)], axis=0)


def motif_like(rgb, fab, dist=45.0, blue=18.0, lum=110.0, **_):
    """embroidery pixels: far from the fabric colour AND blue or light (the Koi motifs are blues, whites and red)"""
    a = np.asarray(rgb, float); d = np.sqrt(((a - fab) ** 2).sum(-1))
    l = a @ np.array([0.299, 0.587, 0.114]); b = a[..., 2] - a[..., 0]; red = (a[..., 0] - a[..., 2]) > 60
    return (d > dist) & ((b > blue) | (l > lum) | red)


def silhouette(rgb, fab, ppm, test):
    m = motif_like(rgb, fab, **test)
    r = max(1, int(round(test.get("close_mm", 1.0) * ppm / 2))); yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
    m = ndi.binary_closing(m, xx * xx + yy * yy <= r * r)
    return ndi.binary_fill_holes(m)


def sim_apply(sim, px, py):
    a, b, tx, ty = sim
    return a * px - b * py + tx, b * px + a * py + ty


def _lab(rgb):
    from skimage.color import rgb2lab
    return rgb2lab(np.clip(np.asarray(rgb, float) / 255.0, 0, 1)[None])[0]


def _rgb(lab):
    from skimage.color import lab2rgb
    return lab2rgb(np.asarray(lab, float)[None])[0] * 255.0


def transfer(src, ref):
    """src colours moved to ref's MEAN in Lab (the mockup motif's hue and lightness) keeping src's own variation (the
    close-up's light and dark pattern). Not ref's spread: the ~1 px/mm mockup motif is nearly flat, so matching its
    spread would erase the very detail the close-up is there to give."""
    if len(src) == 0 or len(ref) == 0: return src
    ls, lr = _lab(src), _lab(ref)
    return np.clip(_rgb(ls - ls.mean(0) + lr.mean(0)), 0, 255)


def composite(cfg, view, XX, YY, px, py, rgb, cw, sppm, weights, mock_ppm):
    from digitize.extract.register import _img, _path
    mock = rgb.copy(); ppm = 1.0 / max(abs(XX[0, 1] - XX[0, 0]), 1e-9)
    for cu in cfg["closeups"]:
        if cu.get("mode") != "inform" or cu.get("view") != view: continue
        test = dict(TEST, **cu.get("motif_test", {}))
        fab_m = np.asarray(cu["fabric_mockup"], float) if cu.get("fabric_mockup") else fabric_of(mock)
        sil = silhouette(mock, fab_m, ppm, test)
        S = _img(_path(cfg, cu["file"])); key = _path(cfg, cu["file"])
        if key not in _FAB: _FAB[key] = fabric_of(S)
        fab_c = np.asarray(cu["fabric_closeup"], float) if cu.get("fabric_closeup") else _FAB[key]
        used = np.zeros(px.shape, bool)
        for m in cu.get("motifs", []):
            x0, y0, x1, y1 = m["window"]
            sel = sil & (px >= x0) & (px < x1) & (py >= y0) & (py < y1) & ~used
            for ex in m.get("exclude", []):                # hand-drawn "not this motif" boxes (a fish tail touching a petal)
                sel &= ~((px >= ex[0]) & (px < ex[2]) & (py >= ex[1]) & (py < ex[3]))
            if not sel.any(): continue
            lab, n = ndi.label(sel)                        # the motif = the LARGEST mockup silhouette in its window: a fish
            if n > 1:                                      # tail or a petal that reaches into the window is not this motif
                sz = np.bincount(lab.ravel()); sz[0] = 0; sel = lab == int(sz.argmax())
            cx, cy = sim_apply(m["sim"], px[sel], py[sel])
            inside = (cx >= 0) & (cy >= 0) & (cx < S.shape[1] - 1) & (cy < S.shape[0] - 1)
            p = np.stack([map_coordinates(S[..., c], [cy, cx], order=1, mode="nearest") for c in range(3)], -1)
            ok = inside & motif_like(p, fab_c, **test)
            if not ok.any(): continue
            idx = np.flatnonzero(sel)[ok]
            flat = rgb.reshape(-1, 3); flat[idx] = transfer(p[ok], mock.reshape(-1, 3)[np.flatnonzero(sel)])
            used.flat[idx] = True
            s = math.hypot(m["sim"][0], m["sim"][1])            # close-up px per mockup px
            sppm.flat[idx] = mock_ppm * s
        cw = np.maximum(cw, used.astype(np.float32)); weights[cu["name"]] = used.astype(np.float32)
    return rgb, cw, sppm, weights


# ------------------------------------------------------------------ per-motif fit (a tool: its result is stored as data)
def init_from_affine(X, tie=None):
    """a similarity flat px -> close-up px from a global affine close-up px -> flat px (X: [[a, b], [c, d], [tx, ty]],
    as trace/closeup_reg.json stores it), optionally pinned at a tie point [[cu x, cu y], [flat x, flat y]]"""
    X = np.asarray(X, float); A = X[:2].T; t = X[2]; Ai = np.linalg.inv(A)
    a = (Ai[0, 0] + Ai[1, 1]) / 2; b = (Ai[1, 0] - Ai[0, 1]) / 2
    if tie is not None:
        (cux, cuy), (fx, fy) = tie
    else:
        fx, fy = 0.0, 0.0; cux, cuy = Ai @ (np.array([fx, fy]) - t)
    return [a, b, cux - (a * fx - b * fy), cuy - (b * fx + a * fy)]


def fit_similarity(flat_rgb, cu_rgb, window, init, test=None, up=2, rot_deg=24.0, rot_step=2.0, scale_rel=0.15, scale_step=0.03, max_shift=20):
    """the similarity flat px -> close-up px that best overlays the close-up's motif on the MOCKUP's motif inside
    `window` (flat px): rotation x scale grid around `init`, translation by cross-correlating the two motif masks
    (within max_shift flat px). Returns dict(sim, iou, rot, scale, shift_px, iou_init)."""
    from scipy.signal import fftconvolve
    test = dict(TEST, **(test or {}))
    x0, y0, x1, y1 = window
    gx = x0 + (np.arange(int((x1 - x0) * up)) + 0.5) / up; gy = y0 + (np.arange(int((y1 - y0) * up)) + 0.5) / up
    GX, GY = np.meshgrid(gx, gy)
    fr = np.stack([map_coordinates(np.asarray(flat_rgb, float)[..., c], [GY, GX], order=1, mode="nearest") for c in range(3)], -1)
    M = ndi.binary_fill_holes(motif_like(fr, fabric_of(flat_rgb), **test)).astype(float)
    C = motif_like(cu_rgb, fabric_of(cu_rgb), **test).astype(np.float32)
    a0, b0 = init[0], init[1]; s0 = math.hypot(a0, b0); r0 = math.atan2(b0, a0)
    cx0, cy0 = (x0 + x1) / 2, (y0 + y1) / 2; ccx, ccy = sim_apply(init, cx0, cy0)
    def warp(s, r):
        a, b = s * math.cos(r), s * math.sin(r)
        sim = [a, b, ccx - (a * cx0 - b * cy0), ccy - (b * cx0 + a * cy0)]
        X, Y = sim_apply(sim, GX, GY)
        return sim, map_coordinates(C, [Y, X], order=0, mode="constant", cval=0.0)
    def score(W):
        cc = fftconvolve(M, W[::-1, ::-1], mode="full"); H, Wd = M.shape
        oy, ox = H - 1, Wd - 1; ms = max_shift * up
        sub = cc[oy - ms:oy + ms + 1, ox - ms:ox + ms + 1]; k = np.unravel_index(sub.argmax(), sub.shape)
        dy, dx = k[0] - ms, k[1] - ms
        Ws = np.roll(np.roll(W, dy, 0), dx, 1)
        inter = (M * Ws).sum(); uni = ((M + Ws) > 0).sum()
        return inter / max(uni, 1), dy, dx
    sim_i, W_i = warp(s0, r0); iou_i = ((M * W_i).sum() / max(((M + W_i) > 0).sum(), 1))
    best = None
    for ds in np.arange(-scale_rel, scale_rel + 1e-9, scale_step):
        for dr in np.arange(-rot_deg, rot_deg + 1e-9, rot_step):
            s, r = s0 * (1 + ds), r0 + math.radians(dr)
            sim, W = warp(s, r); iou, dy, dx = score(W)
            if best is None or iou > best[0]: best = (iou, sim, dy, dx, s, r)
    iou, sim, dy, dx, s, r = best
    a, b, tx, ty = sim; dxf, dyf = dx / up, dy / up         # output shifted by (dx, dy): it samples sim(p - d)
    sim = [a, b, tx - (a * dxf - b * dyf), ty - (b * dxf + a * dyf)]
    return dict(sim=[float(v) for v in sim], iou=round(float(iou), 3), iou_init=round(float(iou_i), 3),
                rot=round(math.degrees(r - r0), 1), scale=round(s / s0, 3), shift_px=[round(dxf, 1), round(dyf, 1)])
