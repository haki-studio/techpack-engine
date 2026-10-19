"""Stars TRACED from the mockup (LESSONS A14): centre = local brightness peak near the listed star, arm lengths = half-max of each
arm's own contrast along the 4 axes (+ diagonals for the big 8-point stars), measured on the mockup upsampled x8 (bilinear).
The mockup is ~1 px/mm, so arm WIDTH is not measurable; widths stay the stitchable minimum (tapered satin)."""
import numpy as np
from scipy import ndimage as ndi
import mockmap as MM

UP = 8.0
def measure(cx, cy, kind):
    bb = (cx - 30, cy - 30, cx + 30, cy + 30)
    a = np.array(MM.warp(bb, UP)).astype(np.float32); lum = a @ np.array([0.3, 0.59, 0.11])
    c0 = np.array([30*UP, 30*UP])
    win = lum[int(c0[1] - 2.5*UP):int(c0[1] + 2.5*UP), int(c0[0] - 2.5*UP):int(c0[0] + 2.5*UP)]
    r_, c_ = np.unravel_index(np.argmax(ndi.gaussian_filter(win, 0.4*UP)), win.shape)
    py, px = int(c0[1] - 2.5*UP) + r_, int(c0[0] - 2.5*UP) + c_
    ncx, ncy = bb[0] + (px + .5)/UP, bb[1] + (py + .5)/UP
    bg = float(np.percentile(lum, 30))
    def arm(dx, dy):
        rs = np.arange(0, 26, 0.25); xs = px + dx*rs*UP; ys = py + dy*rs*UP
        p = ndi.map_coordinates(lum, [ys, xs], order=1, mode="nearest") - bg
        def run(r0, r1):                       # half-max of the arm's own contrast measured between r0 and r1
            ref = np.median(p[(rs >= r0) & (rs <= r1)])
            if ref <= 6: return 0.0
            L = 0.0
            for r, v in zip(rs, p):
                if r < r0: continue
                if v <= 0.5*ref: break
                L = r
            return L
        return float(max(run(1.2, 2.5), run(3.0, 5.0)))     # a bright core (r < 2.5) must not hide a dimmer long arm
    up, dn, lf, rt = arm(0, -1), arm(0, 1), arm(-1, 0), arm(1, 0)
    d = [arm(s1*0.7071, s2*0.7071) for s1 in (-1, 1) for s2 in (-1, 1)] if kind == "big" else []
    pair = lambda a_, b_: min((a_ + b_)/2, 1.35*min(a_, b_)) if min(a_, b_) > 0 else max(a_, b_)    # one arm running into a neighbour does not count
    return dict(cx=ncx, cy=ncy, Lv=pair(up, dn), Lh=pair(lf, rt), Ld=float(np.median(d)) if d else 0.0, peak=float(lum[py, px] - bg), arms=(up, dn, lf, rt))

def measure_dot(cx, cy):
    """dot: half-max radius of the core (the arms test would run into neighbours); returns centre + diameter"""
    m = measure(cx, cy, "dot")
    return m["cx"], m["cy"], m

# ---------------------------------------------------------------- observation model shared with qa_fidelity (same operator both sides)
PPM_OBS = 4.0
GROW = 0.25        # mm: satin pull comp + thread width the stitched star gains over its outline (as the DST render shows)
PSF = 0.7          # mm: the mockup's own softness beyond its ~1.2 mm pixel grid
def observe(a, ppm=PPM_OBS):
    """a stitched/drawn coverage image (0..1, garment mm grid) as the mockup would show it: averaged into the mockup's pixel
    grid (MM.S mm), softened by PSF, bilinear back to the grid"""
    from PIL import Image
    k = max(1, int(round(MM.S*ppm)))
    h_, w_ = (a.shape[0]//k)*k, (a.shape[1]//k)*k
    lo = ndi.gaussian_filter(a[:h_, :w_].reshape(h_//k, k, w_//k, k).mean((1, 3)), PSF/MM.S)
    up = np.array(Image.fromarray(lo.astype(np.float32)).resize((w_, h_), Image.BILINEAR)); o = np.zeros_like(a, dtype=np.float32); o[:h_, :w_] = up
    return o
def halfmax(a, bg, ppm=PPM_OBS, win_mm=8.0):
    pk = ndi.maximum_filter(a, size=int(win_mm*ppm)); return (a - bg) > 0.5*(pk - bg)

def _raster(geoms, bb, ppm):
    from PIL import Image, ImageDraw
    x0, y0, x1, y1 = bb; W, H = int((x1-x0)*ppm), int((y1-y0)*ppm)
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    for g in geoms:
        for p in (g.geoms if hasattr(g, "geoms") else [g]):
            if p.geom_type == "Polygon": d.polygon([((x - x0)*ppm, (y - y0)*ppm) for x, y in p.exterior.coords], fill=255)
    return np.array(im).astype(np.float32) / 255

def fit(cx, cy, kind, make, p0):
    """fit the star's parameters so that the drawn star, seen through observe() + halfmax(), matches the mockup's own half-max
    blob (IoU). make(cx, cy, params) -> list of geometries. Returns (params, centre, iou)."""
    R = 22.0; bb = (cx - R, cy - R, cx + R, cy + R); ppm = PPM_OBS
    a = np.array(MM.warp(bb, ppm)).astype(np.float32); lum = a @ np.array([0.3, 0.59, 0.11])
    bg = float(np.percentile(lum, 30)); pk_ = ndi.maximum_filter(lum, size=int(8*ppm))
    ref = halfmax(lum, bg) & ((pk_ - bg) > 0.35*(lum.max() - bg))           # fabric texture is not part of the star
    lab, n = ndi.label(ref); c = int(R*ppm)
    if not n: return p0, (cx, cy), 0.0
    if lab[c, c]: k = lab[c, c]
    else:
        ys, xs = np.nonzero(lab); i = np.argmin((ys - c)**2 + (xs - c)**2); k = lab[ys[i], xs[i]]
    ref = lab == k
    def score(pc, x_, y_):
        o = halfmax(observe(_raster([g.buffer(GROW) for g in make(x_, y_, pc)], bb, ppm)), 0.0)
        ol, _ = ndi.label(o); keep = np.unique(ol[ref & (ol > 0)]); o = np.isin(ol, keep) & (ol > 0)
        return (ref & o).sum() / max((ref | o).sum(), 1)
    best = (score(p0, cx, cy), p0, (cx, cy))
    for dx in (-0.8, 0, 0.8):                                  # centre
        for dy in (-0.8, 0, 0.8):
            s = score(best[1], cx + dx, cy + dy)
            if s > best[0]: best = (s, best[1], (cx + dx, cy + dy))
    for _ in range(3):                                          # sizes: coordinate search over each parameter
        for j in range(len(p0)):
            for f in (0.6, 0.8, 0.9, 1.1, 1.25, 1.5, 2.0):
                pc = list(best[1]); pc[j] = float(np.clip(pc[j]*f, max(0.8, 0.5*p0[j]), 2.5*p0[j]))     # stay near the measured arm (width: clipped 0.9-2.2 by make)
                s = score(pc, *best[2])
                if s > best[0]: best = (s, pc, best[2])
    return best[1], best[2], float(best[0])
