"""Mockup (inputs/flat.png, 1536 x 1024: front view x 0-768, back view x 768-1536) <-> pattern-piece mm (size M).

Body pieces: affine per view, landmarks read from the gridded mockup (scratch grids, 16 Oct):
  front: CF zip x 413 px, CF neck seam y 150, body edges at the hem seam x 180 / 648 (= 2 x 299.5 mm), hem-rib seam y 598
         (= 510 mm)  ->  x mm = (px - 413) * 1.28,  y mm = (py - 150) * 1.14
  back:  CB x 357 (+768), CB neck seam y 75, body edges x 119 / 595, hem-rib seam y 597 (= 585 mm)
         ->  x mm = (px - 357) * 1.26 (+ = wearer's right = viewer's right), y mm = (py - 75) * 1.12
  The render is narrower than the boxy block, so x and y scale differently; motif SIZES come from the library (fixed mm).
Sleeves: the flat lay shows the FRONT half of each sleeve on the front view and the BACK half on the back view.
  A sleeve point (x, y) maps by length fraction v (cap top -> cuff seam) and lateral fraction u (sleeve centre line = 0,
  underarm seam = 1) onto the region between that view's outer silhouette (= sleeve centre fold) and its inner edge
  (armhole seam down to the underarm, then the sleeve/body boundary down to the cuff). The render's sleeves are ~1.7x
  narrower than the pattern, so sleeve art is stretched across; motif sizes stay library mm."""
import numpy as np
from PIL import Image
from shapely.geometry import LineString, Point
import keepout as KO

_IM = {}
def flat(up=1):
    if up not in _IM:
        im = Image.open("inputs/flat.png").convert("RGB")
        im = Image.fromarray(no_background(np.array(im)))
        if up > 1: im = im.resize((im.width * up, im.height * up), Image.LANCZOS)
        _IM[up] = with_closeups(np.array(im).astype(np.float32), up)
    return _IM[up]

BG_AS = (45, 55, 68)          # background (studio white around the garment) is read as bare navy shell, never as cloud
def no_background(a):
    """flood-fill the light, low-saturation studio background from the image border (and below the detail strip line)"""
    from scipy import ndimage as ndi
    f = a.astype(np.float32); lum = f @ [0.3, 0.59, 0.11]; sat = (f.max(2) - f.min(2)) / np.maximum(f.max(2), 1)
    cand = (lum > 185) & (sat < 0.10)
    lab, n = ndi.label(cand)
    edge = set(np.unique(np.r_[lab[0], lab[:, 0], lab[:, -1], lab[690, :], lab[:, 768]])) - {0}
    bg = np.isin(lab, list(edge))
    bg = ndi.binary_dilation(bg, iterations=2) & (lum > 150)
    out = a.copy(); out[bg] = BG_AS; return out

# Detail close-ups (inputs/closeup_mockup_strip.png = the 4 panels under the mockup; LESSONS A12). The panels are AI
# re-renders, not exact crops (template matching scores ~0.45 at wrong places), so they are registered by hand on matched
# features; only panels whose composition matches a mockup area are traced (the rest are motif references, see specs):
#   falls panel (strip x 786-1146): fall top (240, 150) -> mockup back (991, 370) px, fall foot (245, 320) -> (1000, 505),
#   summit (205, 45) -> (968, 277): similarity scale 0.82 (the panel has ~1.2x the mockup's pixel density, much sharper).
CLOSEUPS = {"falls": dict(box=(786, 0, 1146, 334), s=0.82, a_panel=(240.0, 150.0), a_flat=(991.0, 370.0), ell=(972.0, 400.0, 88.0, 128.0), feather=0.35)}
def with_closeups(a, up):
    from scipy import ndimage as ndi
    S = Image.open("inputs/closeup_mockup_strip.png").convert("RGB")
    for k, c in CLOSEUPS.items():
        pan = S.crop(c["box"]); s = c["s"] * up
        W, H = int(round(pan.width * s)), int(round(pan.height * s))
        p = np.asarray(pan.resize((W, H), Image.LANCZOS)).astype(np.float32)
        x0 = int(round((c["a_flat"][0] - c["s"] * c["a_panel"][0]) * up)); y0 = int(round((c["a_flat"][1] - c["s"] * c["a_panel"][1]) * up))
        # only the matched motif (the mountain + fall): elliptical mask in mockup px, soft edge (last 35 % of the radius)
        ex, ey, rx, ry = c["ell"]; yy, xx = np.mgrid[0:H, 0:W]
        d = np.sqrt((((x0 + xx) / up - ex) / rx) ** 2 + (((y0 + yy) / up - ey) / ry) ** 2)
        m = np.clip((1 - d) / c["feather"], 0, 1).astype(np.float32)[..., None]
        # colour match: the re-render is darker / more contrasty than the mockup -> per-channel mean + std matched to the
        # mockup under the same mask, so the tracer reads it with the same tone clusters (rock stays rock, not bare shell)
        ys0, xs0 = slice(max(0, y0), min(a.shape[0], y0 + H)), slice(max(0, x0), min(a.shape[1], x0 + W))
        mm = m[ys0.start - y0:ys0.stop - y0, xs0.start - x0:xs0.stop - x0, 0] > 0.5
        ref = a[ys0, xs0][mm]; src = p[ys0.start - y0:ys0.stop - y0, xs0.start - x0:xs0.stop - x0][mm]
        p = (p - src.mean(0)) / np.maximum(src.std(0), 1) * ref.std(0) + ref.mean(0)
        p = p.clip(0, 255)
        ys, xs = slice(max(0, y0), min(a.shape[0], y0 + H)), slice(max(0, x0), min(a.shape[1], x0 + W))
        py, px = slice(ys.start - y0, ys.stop - y0), slice(xs.start - x0, xs.stop - x0)
        a[ys, xs] = a[ys, xs] * (1 - m[py, px]) + p[py, px] * m[py, px]
    return a

# ---------------------------------------------------------------- body affine maps (mm -> px in flat.png)
BODY = {"F": dict(ox=413.0, oy=150.0, sx=1.28, sy=1.14), "B": dict(ox=357.0 + 768, oy=75.0, sx=1.26, sy=1.12)}
def body_px(view, x, y):
    m = BODY[view]; return x / m["sx"] + m["ox"], y / m["sy"] + m["oy"]
def body_mm(view, px, py):
    m = BODY[view]; return (px - m["ox"]) * m["sx"], (py - m["oy"]) * m["sy"]

# ---------------------------------------------------------------- sleeve landmark polylines (flat.png px)
# outer = sleeve centre fold (shoulder point -> cuff seam outer corner); inner = shoulder point -> armhole seam -> underarm
# (index UA) -> sleeve/body boundary -> cuff seam inner corner.
SL = {
 # front view, image-left sleeve = wearer's RIGHT sleeve S01, front half (S01 x > 0)
 ("SR", "front"): dict(outer=[(165, 178), (125, 215), (100, 260), (85, 310), (73, 360), (63, 420), (53, 480), (44, 540), (36, 600), (33, 615)],
                       inner=[(165, 178), (190, 192), (203, 220), (204, 255), (198, 330), (190, 420), (182, 500), (176, 560), (175, 612)], ua=3),
 # front view, image-right sleeve = wearer's LEFT sleeve S02, front half (S02 x < 0)
 ("SL", "front"): dict(outer=[(660, 178), (700, 215), (725, 262), (742, 312), (752, 362), (760, 422), (768, 482), (776, 542), (783, 600), (786, 615)],
                       inner=[(660, 178), (636, 192), (623, 220), (622, 255), (628, 330), (636, 420), (644, 500), (650, 560), (651, 612)], ua=3),
 # back view, image-left sleeve = wearer's LEFT sleeve S02, back half (S02 x > 0)
 ("SL", "back"):  dict(outer=[(883, 165), (848, 225), (818, 290), (796, 360), (781, 430), (773, 500), (770, 560), (771, 612)],
                       inner=[(883, 165), (908, 205), (918, 240), (911, 320), (903, 420), (895, 520), (903, 612)], ua=2),
 # back view, image-right sleeve = wearer's RIGHT sleeve S01, back half (S01 x < 0)
 ("SR", "back"):  dict(outer=[(1368, 170), (1408, 210), (1438, 260), (1468, 330), (1488, 400), (1501, 470), (1506, 540), (1505, 612)],
                       inner=[(1368, 170), (1358, 210), (1353, 250), (1358, 330), (1361, 420), (1363, 520), (1360, 612)], ua=2),
}

def _pull(outer, inner, d=7.0):
    out = []
    for i, (x, y) in enumerate(outer):
        j = min(range(len(inner)), key=lambda k: abs(inner[k][1] - y))
        dx = inner[j][0] - x; out.append((x + (d if dx > 0 else -d) * (i > 0), y))
    return out
for _k, _d in SL.items(): _d["outer"] = _pull(_d["outer"], _d["inner"])

def _param(pts):
    L = LineString(pts); return L, L.length

_SLC = {}
def _sleeve_model(P, size="M"):
    key = (P, size)
    if key in _SLC: return _SLC[key]
    g, mt = KO.pieces(size); h, Lu = mt["cap_h"], mt["Lu"]
    pc = g["S01" if P == "SR" else "S02"]; poly = pc.sew_poly()
    v_ua = h / (h + Lu)
    views = {}
    for view in ("front", "back"):
        d = SL[(P, view)]; o, oL = _param(d["outer"])
        inn = d["inner"]; a, aL = _param(inn[:d["ua"] + 1]); b, bL = _param(inn[d["ua"]:])
        views[view] = (o, oL, a, aL, b, bL)
    _SLC[key] = (poly, h, Lu, v_ua, views); return _SLC[key]

def _halfwidth(poly, y):
    seg = poly.intersection(LineString([(-600, y), (600, y)]))
    if seg.is_empty: return None
    b = seg.bounds; return b[0], b[2]

def sleeve_px(P, x, y, size="M"):
    """pattern point on sleeve P -> (view, px, py) in flat.png. Front half -> front view, back half -> back view."""
    poly, h, Lu, v_ua, views = _sleeve_model(P, size)
    front_half = (x > 0) if P == "SR" else (x < 0)
    view = "front" if front_half else "back"
    o, oL, a, aL, b, bL = views[view]
    v = min(1.0, max(0.0, (y + h) / (h + Lu)))
    hw = _halfwidth(poly, y)
    xmax = (hw[1] if x >= 0 else -hw[0]) if hw else 1.0
    u = min(1.0, abs(x) / max(xmax, 1e-3))
    po = o.interpolate(v * oL)
    pi = a.interpolate(v / v_ua * aL) if v <= v_ua else b.interpolate((v - v_ua) / (1 - v_ua) * bL)
    return view, po.x + (pi.x - po.x) * u, po.y + (pi.y - po.y) * u

# ---------------------------------------------------------------- warp: mockup resampled into piece mm space
def piece_px(P, X, Y):
    """arrays of pattern mm -> arrays of flat.png px (vectorised for body pieces; per point for sleeves)"""
    if P == "BK": return X / BODY["B"]["sx"] + BODY["B"]["ox"], Y / BODY["B"]["sy"] + BODY["B"]["oy"]
    if P in ("FR", "FL"): return X / BODY["F"]["sx"] + BODY["F"]["ox"], Y / BODY["F"]["sy"] + BODY["F"]["oy"]
    PX = np.zeros_like(X); PY = np.zeros_like(Y)
    for idx in np.ndindex(X.shape):
        _, PX[idx], PY[idx] = sleeve_px(P, float(X[idx]), float(Y[idx]))
    return PX, PY

def warp(P, bbox, ppm, up=4):
    """RGB float array of the mockup covering bbox (x0, y0, x1, y1) of piece P at ppm px/mm (source upscaled x up, Lanczos)."""
    from scipy.ndimage import map_coordinates
    x0, y0, x1, y1 = bbox; W, H = int(round((x1-x0)*ppm)), int(round((y1-y0)*ppm))
    xs = x0 + (np.arange(W) + 0.5) / ppm; ys = y0 + (np.arange(H) + 0.5) / ppm
    if P in ("SR", "SL"):          # sleeves: exact map on a coarse grid, bilinear in between (fast)
        step = 2.0
        gx = np.arange(x0, x1 + step, step); gy = np.arange(y0, y1 + step, step)
        GX, GY = np.meshgrid(gx, gy); PX, PY = piece_px(P, GX, GY)
        from scipy.interpolate import RegularGridInterpolator as RGI
        fx = RGI((gy, gx), PX); fy = RGI((gy, gx), PY)
        YY, XX = np.meshgrid(ys, xs, indexing="ij"); pts = np.stack([YY.ravel(), XX.ravel()], -1)
        px = fx(pts).reshape(H, W); py = fy(pts).reshape(H, W)
    else:
        XX, YY = np.meshgrid(xs, ys); px, py = piece_px(P, XX, YY)
    a = flat(up); out = np.zeros((H, W, 3), np.float32)
    for c in range(3): out[..., c] = map_coordinates(a[..., c], [py * up - 0.5 * (up - 1) / up * 0, px * up], order=1, mode="nearest")
    return out
