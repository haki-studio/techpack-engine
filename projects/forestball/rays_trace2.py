"""Rev C final (founder, 19 Oct: "the rays are not at the mockup's angles"; LESSONS A12/A14): the light rays are TRACED from the
MOCKUP stripe by stripe — no shared angle, no typed start points, no width clamp.
The mockup's rays are bands of light thread stripes on the shell. On a lightness-excess map (lightness over a 30 mm
low-percentile baseline, low saturation) every stripe is a bright ridge:
  1. stripe pixels = excess > EX_MIN on BARE shell (the traced art silhouette + 1.5 mm is masked: rays only show between
     motifs) inside the art area, garment details masked (LESSONS A15): CB seam |x| < 5 mm, background beyond the shoulders.
  2. each connected stripe = one ray object: its own silhouette (polygon of its pixels, 0.4 mm smoothing), its own axis
     (PCA), its brightness (mean excess). Kept when elongated (length / width >= 4), >= 12 mm long and running down-left
     (axis 20-80° below horizontal) — leaf-edge halos and fabric texture fail these.
  3. the stripes' axes fan: the least-squares point nearest to all axes = the light source (vanishing point), reported.
-> rays_trace2.json: vp, stripes [{pts (mm), axis_deg, length, width, excess}]; out/art/ray_mask_ref.npy (reference mask for
   qa.motif_match, 3 px/mm on BBOX)."""
import json, math, sys, pickle
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import color, measure
import shapely
from shapely.geometry import Polygon
from shapely.ops import unary_union
import fbcore, back as B
import trace_fb as T

PPM = 3.0
BBOX = (-300, -20, 300, 600)
EX_MIN = 6.0

def grid():
    x0, y0, x1, y1 = BBOX; W, H = int((x1 - x0) * PPM), int((y1 - y0) * PPM)
    return np.meshgrid(x0 + (np.arange(W) + 0.5) / PPM, y0 + (np.arange(H) + 0.5) / PPM)

def excess():
    XX, YY = grid(); mpx, mpy = T.back_px(XX, YY)
    img, valid = T.sample("inputs/back.png", None, mpx, mpy)
    L = color.rgb2lab(np.clip(img, 0, 1))[..., 0]
    mx, mn = img.max(2), img.min(2); sat = (mx - mn) / np.maximum(mx, 1e-3)
    vis = pickle.load(open("back_vis.pkl", "rb"))["back"]
    art = unary_union([r["geom"] for r in vis if r["grp"] not in ("LR", "PH")]).buffer(1.5)
    bare = (~shapely.contains_xy(art, XX, YY) & shapely.contains_xy(B.CLIP, XX, YY) & valid
            & (np.abs(XX) > 5) & (L < 75))                                     # A15: CB seam + background masked
    bare_cb = bare | ((np.abs(XX) <= 5) & shapely.contains_xy(B.CLIP, XX, YY) & ~shapely.contains_xy(art, XX, YY))
    base = ndi.percentile_filter(L, 30, size=int(30 * PPM))
    ex = ndi.gaussian_filter(np.clip((L - base) * (sat < 0.30), 0, 30), 0.35 * PPM)
    return XX, YY, ex, bare, bare_cb

def stripes(XX, YY, ex, bare):
    m = bare & (ex > EX_MIN) & (YY < 480)
    m = ndi.binary_opening(m, iterations=1)
    # A15: the CB seam strip (|x| < 5) was masked out; the stripes continue across it — a gap pixel is a stripe when the
    # stripe pixels 0.5 mm outside the strip on BOTH sides line up along the rays' median slope (44°)
    t = math.tan(math.radians(44.0)); x0, y0 = BBOX[0], BBOX[1]
    gapc = np.nonzero(np.abs(XX[0]) <= 5.0)[0]; cl = int((-5.5 - x0) * PPM); cr = int((5.5 - x0) * PPM)
    for c in gapc:
        x = XX[0, c]; dl = int(round((x + 5.5) * t * PPM)); dr = int(round((5.5 - x) * t * PPM))
        rows = np.arange(m.shape[0]); rl = rows + dl; rr = rows - dr
        ok = (rl >= 0) & (rl < m.shape[0]) & (rr >= 0) & (rr < m.shape[0])
        col = np.zeros(m.shape[0], bool); col[ok] = m[rl[ok], cl] & m[rr[ok], cr]
        m[:, c] |= col & (YY[:, c] < 480)
    lab, n = ndi.label(m); out = []; keep = np.zeros_like(m)
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        comp = lab[sl] == k; a = comp.sum() / PPM**2
        if a < 8: continue
        ys, xs = np.nonzero(comp); X = XX[sl][comp]; Y = YY[sl][comp]
        c = np.cov(np.stack([X, Y])); ev, evec = np.linalg.eigh(c); d = evec[:, 1]
        L_ = 4 * math.sqrt(max(ev[1], 1e-9)); W_ = a / max(L_, 1e-9)
        ang = math.degrees(math.atan2(d[1], d[0])) % 180          # axis direction, y down
        slope = 180 - ang if ang > 90 else ang                     # degrees below horizontal for a down-left ray
        if not (ang > 90 and 20 <= slope <= 80): continue          # rays run from top-right to bottom-left
        if L_ < 12 or L_ / max(W_, 1e-9) < 4: continue
        if X.mean() < -100 and Y.mean() < 150: continue           # lighter shell along the left shoulder/neck: no ray there
        x0, y0 = BBOX[0], BBOX[1]
        polys = []
        for cc in measure.find_contours(np.pad(comp, 1).astype(np.float32), 0.5):
            if len(cc) < 8: continue
            p = Polygon([(x0 + (sl[1].start + xx - 1 + 0.5) / PPM, y0 + (sl[0].start + yy - 1 + 0.5) / PPM) for yy, xx in cc]).buffer(0)
            if p.area > 2: polys.append(p)
        if not polys: continue
        g = unary_union(polys).buffer(0.4).buffer(-0.4).simplify(0.2)
        g = max((list(g.geoms) if hasattr(g, "geoms") else [g]), key=lambda q: q.area)
        keep[sl] |= comp
        out.append(dict(pts=[[round(x, 2), round(y, 2)] for x, y in g.exterior.coords], axis_deg=round(slope, 1), dir=[float(d[0]), float(d[1])],
                        cx=round(float(X.mean()), 1), cy=round(float(Y.mean()), 1), length=round(L_, 1), width=round(W_, 2),
                        excess=round(float(ex[sl][comp].mean()), 1), area=round(a, 1)))
    return out, keep

def vanishing_point(st):
    """least-squares point nearest to all stripe axes (weighted by length)"""
    A = np.zeros((2, 2)); b = np.zeros(2)
    for s in [s_ for s_ in st if s_["length"] >= 40]:
        d = np.array(s["dir"]); n = np.array([-d[1], d[0]]); p = np.array([s["cx"], s["cy"]]); w = s["length"]
        A += w * np.outer(n, n); b += w * np.outer(n, n) @ p
    return np.linalg.solve(A, b)

if __name__ == "__main__":
    XX, YY, ex, bare, bare_cb = excess()
    st, keep = stripes(XX, YY, ex, bare)
    vp = vanishing_point(st)
    for s in st:                                   # angle of the line from the VP through the stripe centre vs its own axis
        a = math.degrees(math.atan2(s["cy"] - vp[1], s["cx"] - vp[0])); s["vp_dev_deg"] = round(abs(((180 - a) % 180) - s["axis_deg"]), 1)
    json.dump(dict(vp=[round(float(v), 1) for v in vp], source="inputs/back.png (mockup), stripes traced", ex_min=EX_MIN, stripes=st),
              open("rays_trace2.json", "w"), indent=1)
    np.save("out/art/ray_mask_ref.npy", keep); np.save("out/art/ray_bare.npy", bare_cb)
    angs = sorted(s["axis_deg"] for s in st)
    print("VP", vp.round(1), "stripes", len(st), "axis deg min/median/max", angs[0], angs[len(angs)//2], angs[-1],
          "total length", round(sum(s["length"] for s in st)), "mm")
    Image.fromarray((keep * 255).astype(np.uint8)).save("out/dbg/ray_stripes.png")
