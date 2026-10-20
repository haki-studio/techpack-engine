"""Registration: a 12 ppm reference image for any garment-mm crop, from the mockup + the registered close-ups
(ENGINE_PLAN M0; LESSONS A12). Promoted from projects/castle-falls-jacket/mockmap.py (no_background, tps_map,
with_closeups_tps, body affine). The registration is DATA (a JSON file per project), not project constants:

  {"flat": "inputs/flat.png",
   "background": {lum_min, sat_max, seed_rows, seed_cols, dilate, dilate_lum_min, as_rgb},
   "views": {"B": {ox, oy, sx, sy}, ...},             # garment mm <-> flat px: x mm = (px - ox) * sx, y mm = (py - oy) * sy
   "tps": {smoothing, border_pad, border_nx, border_ny},
   "closeups": [{name, view, file, region: [x0, y0, x1, y1] flat px, feather: flat px, pts: [[[cu x, cu y], [flat x, flat y]], ...]}]}

Unlike mockmap.warp (flat.png composited at 4x, then sampled), each output pixel is mapped garment mm -> flat px ->
close-up px and sampled from the close-up itself, so a 12 ppm crop carries the close-up's own detail (~4 px/mm) instead
of an upscaled mockup (~0.8 px/mm). Feather masks follow mockmap exactly (trim feather/2 at the region border, Gaussian
sigma feather/2.5, then (m - 0.25) * 1.6), computed on a 2x flat-px grid.

  cfg = register.load("projects/castle-falls-jacket/bench/registration.json")
  r = register.reference(cfg, "B", (-180, 370, 20, 570), ppm=12)  # r["rgb"], r["grey"], r["weights"]["back_left"]
  register.crop_inside(cfg, "B", bounds, "back_left")             # min feather weight over the crop (> 0.6 = inside)

Input pixels only (LESSONS A14): nothing here reads art, scene data or templates.
"""
import json, os
import numpy as np
from PIL import Image

_CACHE = {}


def load(path):
    """registration JSON -> dict; relative file paths resolve against the project folder (the JSON's parent's parent
    when the JSON sits in <project>/bench/, else its own folder), or cfg["root"] when given."""
    cfg = json.load(open(path))
    here = os.path.dirname(os.path.abspath(path))
    root = cfg.get("root") or (os.path.dirname(here) if os.path.basename(here) == "bench" else here)
    cfg["root"] = os.path.abspath(os.path.join(here, root)) if not os.path.isabs(root) else root
    return cfg


def _path(cfg, p): return p if os.path.isabs(p) else os.path.join(cfg["root"], p)


def _img(path):
    if path not in _CACHE: _CACHE[path] = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    return _CACHE[path]


def no_background(a, bg):
    """flood-fill the light, low-saturation studio background from the seed rows / columns (mockmap.no_background)"""
    from scipy import ndimage as ndi
    f = a.astype(np.float32); lum = f @ np.array([0.3, 0.59, 0.11]); sat = (f.max(2) - f.min(2)) / np.maximum(f.max(2), 1)
    lab, _ = ndi.label((lum > bg["lum_min"]) & (sat < bg["sat_max"]))
    seeds = [lab[r, :] for r in bg.get("seed_rows", [0])] + [lab[:, c] for c in bg.get("seed_cols", [0, -1])]
    edge = set(np.unique(np.concatenate(seeds))) - {0}
    m = np.isin(lab, list(edge))
    m = ndi.binary_dilation(m, iterations=bg.get("dilate", 2)) & (lum > bg.get("dilate_lum_min", 150))
    out = a.copy(); out[m] = bg.get("as_rgb", (45, 55, 68)); return out


def flat(cfg):
    key = ("flat", _path(cfg, cfg["flat"]))
    if key not in _CACHE:
        a = _img(_path(cfg, cfg["flat"]))
        _CACHE[key] = no_background(a, cfg["background"]) if cfg.get("background") else a
    return _CACHE[key]


def mm_to_px(cfg, view, x, y):
    v = cfg["views"][view]; return np.asarray(x) / v["sx"] + v["ox"], np.asarray(y) / v["sy"] + v["oy"]


def px_to_mm(cfg, view, px, py):
    v = cfg["views"][view]; return (np.asarray(px) - v["ox"]) * v["sx"], (np.asarray(py) - v["oy"]) * v["sy"]


def tps_map(cu, cfg):
    """flat px -> close-up px (thin-plate spline, smoothed; mockmap.tps_map). The spline is anchored by the
    least-squares affine on a ring of points outside the close-up, so it never swirls where nothing was matched."""
    from scipy.interpolate import RBFInterpolator
    t = cfg.get("tps", {}); pad = t.get("border_pad", 200)
    src = np.array([p[0] for p in cu["pts"]], float); dst = np.array([p[1] for p in cu["pts"]], float)
    A = np.c_[src, np.ones(len(src))]; M, *_ = np.linalg.lstsq(A, dst, rcond=None)
    H, W = _img(_path(cfg, cu["file"])).shape[:2]
    bd = np.array([(x, y) for x in np.linspace(-pad, W + pad, t.get("border_nx", 7)) for y in np.linspace(-pad, H + pad, t.get("border_ny", 6))
                   if x < 0 or x > W or y < 0 or y > H])
    src = np.r_[src, bd]; dst = np.r_[dst, np.c_[bd, np.ones(len(bd))] @ M]
    return RBFInterpolator(dst, src, kernel="thin_plate_spline", smoothing=t.get("smoothing", 40.0))


def _cu_fields(cu, cfg, up=2):
    """on a flat-px grid over the close-up's region (up x finer): close-up coords (sx, sy) and the feather weight"""
    key = ("cu", cu["name"], _path(cfg, cu["file"]), up)
    if key in _CACHE: return _CACHE[key]
    from scipy.ndimage import gaussian_filter
    f = tps_map(cu, cfg); x0, y0, x1, y1 = cu["region"]
    gx = x0 + np.arange((x1 - x0) * up) / up; gy = y0 + np.arange((y1 - y0) * up) / up
    GX, GY = np.meshgrid(gx, gy); q = np.empty(GX.shape + (2,))
    flatq = np.stack([GX.ravel(), GY.ravel()], -1); out = np.empty_like(flatq)
    for i in range(0, len(flatq), 200000): out[i:i + 200000] = f(flatq[i:i + 200000])
    q = out.reshape(GX.shape + (2,))
    S = _img(_path(cfg, cu["file"])); H, W = S.shape[:2]
    inside = (q[..., 0] >= 2) & (q[..., 1] >= 2) & (q[..., 0] < W - 2) & (q[..., 1] < H - 2)
    fr = int(cu["feather"] * up); h = fr // 2
    if h: inside[:h] = inside[-h:] = False; inside[:, :h] = inside[:, -h:] = False
    m = gaussian_filter(inside.astype(np.float32), cu["feather"] * up / 2.5)
    m = np.clip((m - 0.25) * 1.6, 0, 1)
    _CACHE[key] = (q, m); return _CACHE[key]


def _grid(bounds, ppm):
    x0, y0, x1, y1 = bounds; W, H = int(round((x1 - x0) * ppm)), int(round((y1 - y0) * ppm))
    return np.meshgrid(x0 + (np.arange(W) + 0.5) / ppm, y0 + (np.arange(H) + 0.5) / ppm)


def weight(cfg, view, bounds, name, ppm=2.0):
    """feather weight of close-up `name` over a garment-mm crop (0 = mockup only, 1 = close-up only)"""
    from scipy.ndimage import map_coordinates
    cu = next(c for c in cfg["closeups"] if c["name"] == name); up = 2
    XX, YY = _grid(bounds, ppm); px, py = mm_to_px(cfg, view, XX, YY)
    _, m = _cu_fields(cu, cfg, up)
    x0, y0 = cu["region"][:2]
    return map_coordinates(m, [(py - y0) * up, (px - x0) * up], order=1, mode="constant", cval=0.0)


def crop_inside(cfg, view, bounds, name, ppm=2.0):
    return float(weight(cfg, view, bounds, name, ppm).min())


def fit_crop(cfg, view, bounds, name, thresh=0.6, step_mm=5.0, max_shift_mm=100.0):
    """the crop as given if the close-up covers it everywhere (weight > thresh), else the smallest shift (same size, on a
    step_mm grid) that does. Returns (bounds, shift_mm, min_weight)."""
    w0 = crop_inside(cfg, view, bounds, name)
    if w0 > thresh: return tuple(bounds), (0.0, 0.0), w0
    best = None; n = int(max_shift_mm / step_mm)
    for dx in range(-n, n + 1):
        for dy in range(-n, n + 1):
            d = (dx * dx + dy * dy) ** 0.5 * step_mm
            if best is not None and d >= best[0]: continue
            b = (bounds[0] + dx * step_mm, bounds[1] + dy * step_mm, bounds[2] + dx * step_mm, bounds[3] + dy * step_mm)
            w = crop_inside(cfg, view, b, name, ppm=1.0)
            if w > thresh: best = (d, b, (dx * step_mm, dy * step_mm))
    if best is None: raise ValueError(f"no shift within {max_shift_mm} mm puts {bounds} inside close-up {name!r}")
    return best[1], best[2], crop_inside(cfg, view, best[1], name)


def reference(cfg, view, bounds, ppm=12.0):
    """the reference image of a garment-mm crop at ppm: the mockup (background removed) composited with every
    registered close-up of that view, each sampled from its own pixels. Returns dict(rgb (H, W, 3) float 0-255,
    grey (H, W), weights {name: (H, W)}, closeup_weight (H, W), source_ppm (H, W), source_ppm_median, bounds, ppm, view).

    ppm is the SAMPLING GRID, not a detail guarantee: a 12 ppm crop of the mockup alone still only carries the mockup's
    ~0.8 px/mm of real detail. What the pixels actually hold is reported per pixel:
      closeup_weight = the strongest close-up feather weight at that pixel (0 = mockup only, 1 = close-up only);
      source_ppm     = the effective SOURCE resolution there (px of the image the colour came from, per garment mm),
                       blended by weight: mockup 1 / sqrt(sx * sy), close-up from the local scale of the TPS map.
    Gates that read thread grain mask tiles where closeup_weight < 0.6 (qa.direction_match weight=...)."""
    from scipy.ndimage import map_coordinates
    XX, YY = _grid(bounds, ppm); px, py = mm_to_px(cfg, view, XX, YY)
    a = flat(cfg)
    rgb = np.stack([map_coordinates(a[..., c], [py, px], order=1, mode="nearest") for c in range(3)], -1)
    weights = {}; up = 2
    v = cfg["views"][view]; mock_ppm = 1.0 / np.sqrt(abs(v["sx"] * v["sy"]))
    cw = np.zeros(XX.shape, np.float32); sppm = np.full(XX.shape, mock_ppm, np.float32)
    for cu in cfg["closeups"]:
        if cu.get("view") != view: continue
        if cu.get("mode") == "inform": continue                     # --- KOI --- informing close-ups: extract/inform.py, below
        x0, y0, x1, y1 = cu["region"]
        if px.max() < x0 or px.min() > x1 or py.max() < y0 or py.min() > y1: continue
        q, m = _cu_fields(cu, cfg, up)
        ix, iy = (px - x0) * up, (py - y0) * up
        w = map_coordinates(m, [iy, ix], order=1, mode="constant", cval=0.0)
        if not (w > 0).any(): continue
        sx = map_coordinates(q[..., 0], [iy, ix], order=1, mode="nearest"); sy = map_coordinates(q[..., 1], [iy, ix], order=1, mode="nearest")
        S = _img(_path(cfg, cu["file"]))
        p = np.stack([map_coordinates(S[..., c], [sy, sx], order=1, mode="nearest") for c in range(3)], -1)
        rgb = rgb * (1 - w[..., None]) + p * w[..., None]; weights[cu["name"]] = w
        dxs, dys = np.gradient(sx), np.gradient(sy)                 # close-up px per output px (rows, cols)
        cu_ppm = np.sqrt(np.abs(dxs[1] * dys[0] - dxs[0] * dys[1])) * ppm
        sppm = sppm * (1 - w) + cu_ppm * w; cw = np.maximum(cw, w)
    if any(cu.get("mode") == "inform" and cu.get("view") == view for cu in cfg["closeups"]):   # --- KOI --- the mockup governs
        from digitize.extract import inform
        rgb, cw, sppm, weights = inform.composite(cfg, view, XX, YY, px, py, rgb, cw, sppm, weights, mock_ppm)
    rgb = rgb.clip(0, 255)
    return dict(rgb=rgb, grey=rgb @ np.array([0.299, 0.587, 0.114]), weights=weights, closeup_weight=cw, source_ppm=sppm,
                source_ppm_median=round(float(np.median(sppm)), 2), bounds=tuple(bounds), ppm=ppm, view=view)
