"""Gate reference masks for LESSONS A14/A15 — built from INPUT PIXELS ONLY (Rev C, review item 1).

Nothing here reads the art, the scene, art_<size>.pkl, scene.pkl, the traced templates or any typed motif position.
Inputs used: inputs/front.png (mockup), inputs/closeup_mockup_koi.png (close-up), inputs/reference_fish.png (fish
reference), the pattern (keep-outs / welts = garment details, A15) and the close-up registration features
(trace/closeup_reg.json: lily centres + koi head/tail points read off both images = input pixels); the close-up is
mapped by the global affine + a continuous correction (inverse-distance blend of the two lily-centre residuals).

  source(P)       the reference image on piece P's mm grid (PPM px/mm): the mockup mapped to the piece; on FR the two
                  close-up lilies are pasted in their registration discs (the close-up governs there, A12).
  fish_px(P)      the mockup's fish (former koi) found by colour: every light blob that contains red pixels.
  flora(P)        embroidery pixels that are not fish: colour far from the fabric AND blue or light, inside the art area
                  (pattern keep-outs, welts + 4 mm, white background, sleeve inner edge masked FIRST, A15). Opening 1.0 mm
                  only (stems ~2 mm stay in), closing 0.6 mm, holes < 2 mm2 filled — nothing taken from the art.
  fish_ref(P)     one mask per mockup fish: the founder's reference tetra (reference_fish.png pixels, segmented by colour)
                  laid onto the mockup fish's pose measured from the mockup pixels (centroid, principal axis, head = the
                  end nearer the red), at 0.82 x the mockup fish length (founder decision 19 Oct: "82 % is fine").
  tone(P)         the flora pixels quantised into 4 luminance classes (texture/tone primitive check, A13).
This module is deliberately independent of the art tracers (leaftrace.py, lilytrace.py, fishtrace.py): own classifier,
own thresholds, no shared mask code."""
import json, math
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.ndimage import map_coordinates
import mockmap as MM, front as F

PPM = 5.0
BB = {"FR": (-300, -60, 0, 520), "FL": (0, -60, 300, 520), "SR": (-10, -110, 260, 470), "SL": (-260, -110, 10, 470)}
FISH_SCALE = 0.82                       # founder decision 19 Oct 2026
REG = json.load(open("trace/closeup_reg.json"))
# close-up lily discs: centre feature (close-up px), radius read on the close-up (px) — registration inputs, not art
CU_LILY = {"lily0": ((95, 415), 185.0), "lily1": ((250, 680), 125.0)}
MK_LILY = {"lily0": (195, 438), "lily1": (222, 500)}
# founder fish reference: snout + tail-lobe tip of the template fish, read on reference_fish.png (lower middle fish)
RF_SNOUT, RF_TAILTIP = (740.0, 930.0), (967.0, 809.0)

def disk(mm, ppm=PPM):
    r = mm * ppm / 2; n = int(np.ceil(r)); y, x = np.ogrid[-n:n + 1, -n:n + 1]; return x * x + y * y <= r * r

def grid(P, ppm=PPM):
    bb = BB[P]; W, H = int((bb[2] - bb[0]) * ppm), int((bb[3] - bb[1]) * ppm)
    xs = bb[0] + (np.arange(W) + 0.5) / ppm; ys = bb[1] + (np.arange(H) + 0.5) / ppm
    return np.meshgrid(xs, ys)

def raster(geoms, P, ppm=PPM):
    from PIL import ImageDraw
    bb = BB[P]; H, W = int((bb[3] - bb[1]) * ppm), int((bb[2] - bb[0]) * ppm)
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    T = lambda cs: [((x - bb[0]) * ppm, (y - bb[1]) * ppm) for x, y in cs]
    for g in geoms:
        for p in (g.geoms if hasattr(g, "geoms") else [g]):
            if p.geom_type != "Polygon" or p.is_empty: continue
            d.polygon(T(p.exterior.coords), fill=255)
            for h in p.interiors: d.polygon(T(h.coords), fill=0)
    return np.array(im) > 127

def _A():
    X = np.array(REG["affine"]["X"]); return X[:2].T          # close-up px -> mockup px (linear part)

def _resid():
    """residual of each lily centre after the global affine (mockup px): the close-up drifted differently per lily"""
    X = np.array(REG["affine"]["X"]); out = []
    for nm, (c_cu, _) in CU_LILY.items():
        p = np.array([c_cu[0], c_cu[1], 1.0]) @ X; out.append((p, np.array(MK_LILY[nm], float) - p))
    return out

def cu_field(mx, my):
    """continuous correction field (mockup px) at mockup points: inverse-distance blend of the lily residuals, so each
    lily centre lands exactly on its mockup centre and the two lily discs meet without a seam"""
    mx, my = np.asarray(mx, float), np.asarray(my, float); res = _resid()
    w = [1.0 / (np.hypot(mx - p[0], my - p[1]) ** 2 + 1.0) for p, _ in res]; ws = sum(w)
    return sum(wi * r[0] for wi, (_, r) in zip(w, res)) / ws, sum(wi * r[1] for wi, (_, r) in zip(w, res)) / ws

def cu_to_mock(xs, ys):
    X = np.array(REG["affine"]["X"]); xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    mx = xs * X[0, 0] + ys * X[1, 0] + X[2, 0]; my = xs * X[0, 1] + ys * X[1, 1] + X[2, 1]
    for _ in range(3):                         # the field is evaluated at the corrected point (fixed point)
        fx, fy = cu_field(mx, my)
    fx, fy = cu_field(mx + fx, my + fy)
    return mx + fx, my + fy

def mock_to_cu(mx, my):
    X = np.array(REG["affine"]["X"]); fx, fy = cu_field(mx, my)
    q = np.stack([np.asarray(mx, float) - fx - X[2, 0], np.asarray(my, float) - fy - X[2, 1]], -1) @ np.linalg.inv(_A()).T
    return q[..., 0], q[..., 1]

_C = {}
def source(P, ppm=PPM):
    """(rgb float HxWx3, close-up zone bool, zone id int) on the piece grid"""
    key = ("src", P, ppm)
    if key in _C: return _C[key]
    mt = F.pieces("M")[1]
    rgb = np.array(MM.warp_piece(P, BB[P], ppm, mt)).astype(np.float32)
    zone = np.zeros(rgb.shape[:2], int)
    if P == "FR":
        cu = np.array(Image.open("inputs/closeup_mockup_koi.png").convert("RGB")).astype(np.float32)
        XX, YY = grid(P, ppm); px, py = MM.Pinv(XX, YY); cx, cy = mock_to_cu(px, py)
        # close-up brightness is matched to the mockup on the fabric (median of each image's dark pixels)
        mk_fab = np.median(rgb.reshape(-1, 3)[rgb.reshape(-1, 3).mean(1) < 90], axis=0)
        cu_fab = np.median(cu.reshape(-1, 3)[cu.reshape(-1, 3).mean(1) < 90], axis=0)
        for zi, (nm, (c_cu, R)) in enumerate(CU_LILY.items(), 1):
            inz = (np.hypot(cx - c_cu[0], cy - c_cu[1]) < R) & (cx >= 0) & (cy >= 0) & (cx < cu.shape[1] - 1) & (cy < cu.shape[0] - 1) & (zone == 0)
            for c in range(3):
                v = map_coordinates(cu[..., c], [cy[inz], cx[inz]], order=1)
                rgb[..., c][inz] = mk_fab[c] + (v - cu_fab[c])
            zone[inz] = zi
    _C[key] = (rgb.clip(0, 255), zone > 0, zone)
    return _C[key]

def art_area(P, ppm=PPM):
    """garment details masked first (A15): pattern keep-outs, welts + 4 mm, white background, sleeve inner edge"""
    key = ("area", P, ppm)
    if key in _C: return _C[key]
    mt = F.pieces("M")[1]; rgb = source(P, ppm)[0]
    area = raster([F.clip_for("M", P)], P, ppm)
    if P in ("FR", "FL"): area &= ~raster([F.keep_geoms("M", P)["welt"].buffer(4)], P, ppm)
    bg = (rgb.min(-1) > 196) & ((rgb[..., 2] - rgb[..., 0]) < 22)
    lb, _ = ndi.label(bg); edge = np.unique(np.r_[lb[0], lb[-1], lb[:, 0], lb[:, -1]]); bg = np.isin(lb, edge[edge > 0])
    area &= ~ndi.binary_dilation(bg, iterations=int(2 * ppm))
    if P in ("SR", "SL"):          # front view: the body shows behind the inner part of the sleeve
        XX, YY = grid(P, ppm); hw = mt["W"] + (mt["Ww"] - mt["W"]) * np.clip(YY, 0, None) / mt["Lu"]
        area &= (np.abs(XX) / hw) < 0.72
    _C[key] = area
    return area

def fish_px(P, ppm=PPM, composed=False):
    """fish by colour: light low-saturation blobs (cream body, grey fins) that contain red pixels, + 0.8 mm.
    composed=False: the mockup alone (fish POSES come from the mockup); True: the composed source (close-up koi in
    the lily discs too — used only to keep fish pixels out of the flora reference)"""
    key = ("fish", P, ppm, composed)
    if key in _C: return _C[key]
    rgb = source(P, ppm)[0] if composed else np.array(MM.warp_piece(P, BB[P], ppm, F.pieces("M")[1])).astype(np.float32)
    R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    red = (R > 150) & (R - G > 70) & (R - B > 60)
    cream = (rgb.mean(-1) > 125) & (np.abs(R - B) < 45) & (B - R < 25)
    body = ndi.binary_closing(red | cream, structure=disk(0.8, ppm))
    lab, n = ndi.label(body)
    has = np.unique(lab[ndi.binary_erosion(red, iterations=1) & (lab > 0)])
    m = np.isin(lab, has[has > 0])
    _C[key] = ndi.binary_dilation(m, structure=disk(1.6, ppm)), red, lab, has
    return _C[key]

def flora(P, ppm=PPM):
    """embroidered flora pixels (bool) — not fish, inside the art area"""
    key = ("flora", P, ppm)
    if key in _C: return _C[key]
    rgb, zone, _ = source(P, ppm); area = art_area(P, ppm)
    fab = np.median(rgb[area & ~zone], axis=0)
    dist = np.sqrt(((rgb - fab) ** 2).sum(-1)); L = rgb.mean(-1); blue = rgb[..., 2] - rgb[..., 0]
    emb = area & (dist > 20) & ((blue > fab[2] - fab[0] + 15) | (L > fab.mean() + 55)) & ~fish_px(P, ppm)[0] & ~fish_px(P, ppm, True)[0]
    emb = ndi.binary_opening(emb, structure=disk(1.0, ppm))
    emb = ndi.binary_closing(emb, structure=disk(0.6, ppm)) & area
    # isolated thin lines (topstitching, welt edges, zip-tape shine — A15 garment details): components whose widest
    # point is under 1.6 mm. Stems are not isolated (they join their cluster), floating petals are >= 2.5 mm wide.
    lab, n = ndi.label(emb)
    if n:
        wmax = ndi.maximum(ndi.distance_transform_edt(emb), lab, range(1, n + 1)) * 2 / ppm
        emb &= ~np.isin(lab, 1 + np.nonzero(wmax < 1.6)[0])
    lab, n = ndi.label(emb)
    if n:   # long isolated lines (welt topstitching): length/width > 8 and narrower than 2.4 mm
        wmax = ndi.maximum(ndi.distance_transform_edt(emb), lab, range(1, n + 1)) * 2 / ppm
        sz = ndi.sum(emb, lab, range(1, n + 1)) / ppm ** 2
        emb &= ~np.isin(lab, 1 + np.nonzero((wmax < 2.4) & (sz / np.maximum(wmax, 0.1) ** 2 > 8))[0])
    emb = zip_band(P, emb, ppm)
    holes = ndi.binary_fill_holes(emb) & ~emb; hl, hn = ndi.label(holes)
    if hn:
        hs = ndi.sum(holes, hl, range(1, hn + 1)) / ppm ** 2
        emb |= np.isin(hl, 1 + np.nonzero(hs < 2.0)[0])
    _C[key] = emb
    return emb

def zip_band(P, m, ppm=PPM):
    """garment-edge shine (A15 garment details), not petals: fronts — specks < 15 mm2 within 24 mm of CF (zip tape /
    placket) or within 10 mm of a welt box (welt lip shine); sleeves — specks < 15 mm2 within 6 mm of the outer fold (the front view's silhouette edge)"""
    lim = 24.0 if P in ("FR", "FL") else 6.0
    XX, _ = grid(P, ppm); lab, n = ndi.label(m)
    if not n: return m
    sz = ndi.sum(m, lab, range(1, n + 1)) / ppm ** 2
    cx = ndi.mean(np.abs(XX), lab, range(1, n + 1))
    drop = (sz < 15) & (cx < lim)
    if P in ("FR", "FL"):                      # welt lip / topstitch shine: specks < 15 mm2 within 10 mm of the welt box
        near = raster([F.keep_geoms("M", P)["welt"].buffer(10)], P, ppm)
        drop |= (sz < 15) & (ndi.maximum(near.astype(int), lab, range(1, n + 1)) > 0)
    return m & ~np.isin(lab, 1 + np.nonzero(drop)[0])

def tone(P, ppm=PPM):
    """4 luminance classes over the flora pixels (0 darkest .. 3 lightest), -1 elsewhere; quartiles per source zone"""
    rgb, zone, _ = source(P, ppm); emb = flora(P, ppm); L = ndi.gaussian_filter(rgb.mean(-1), 0.4 * ppm)
    out = np.full(emb.shape, -1, int)
    for z in (False, True):
        m = emb & (zone == z)
        if m.sum() < 50: continue
        q = np.quantile(L[m], [0.25, 0.5, 0.75]); out[m] = np.digitize(L[m], q)
    return out

# ---------------------------------------------------------------- fish: poses from the mockup pixels, silhouette from reference_fish.png
def fish_poses(P, ppm=PPM):
    """one dict per mockup fish blob: centre (mm), heading deg (toward the head), length (mm, tip to tip), red centroid"""
    m, red, lab, has = fish_px(P, ppm); bb = BB[P]; out = []
    XX, YY = grid(P, ppm)
    for k in has[has > 0]:
        b = lab == k
        if b.sum() / ppm ** 2 < 25: continue
        x, y = XX[b], YY[b]; c = np.array([x.mean(), y.mean()])
        C = np.cov(np.stack([x - c[0], y - c[1]])); w, v = np.linalg.eigh(C); ax = v[:, 1]
        s = (x - c[0]) * ax[0] + (y - c[1]) * ax[1]
        rb = b & red; rc = np.array([XX[rb].mean(), YY[rb].mean()])
        # head end: the tail end has the narrow peduncle (width minimum at 65-85 % of the length from the head);
        # width profile along the axis from the pixels, the end farther from that minimum is the head
        t = (s - s.min()) / max(s.max() - s.min(), 1e-6); lat = -(x - c[0]) * ax[1] + (y - c[1]) * ax[0]
        nb = 20; wid = np.array([np.ptp(lat[(t >= i / nb) & (t < (i + 1) / nb)]) if ((t >= i / nb) & (t < (i + 1) / nb)).sum() > 2 else 0 for i in range(nb)])
        lo = wid[2:7].min(); hi = wid[13:18].min()                  # peduncle near t ~ 0.1-0.35 (head at +) or 0.65-0.9 (head at -)
        if hi < lo: ax = -ax; s = -s
        L = float(s.max() - s.min()); mid = c + ax * (s.max() + s.min()) / 2
        out.append(dict(c=mid.tolist(), ang=float(math.degrees(math.atan2(ax[1], ax[0]))), L=L, red=rc.tolist(), area=float(b.sum() / ppm ** 2)))
    return out

_RF = {}
def ref_fish_mask():
    """the template fish from reference_fish.png: bool mask (template px) + its frame (snout, tail tip)"""
    if not _RF:
        im = np.array(Image.open("inputs/reference_fish.png").convert("RGB")).astype(np.float32)
        L = im.mean(-1); fab = np.median(im.reshape(-1, 3), axis=0)
        m = np.sqrt(((im - fab) ** 2).sum(-1)) > 60
        m = ndi.binary_fill_holes(ndi.binary_closing(ndi.binary_opening(m, iterations=1), iterations=2))
        lab, _ = ndi.label(m); mid = np.array(RF_SNOUT) * 0.5 + np.array(RF_TAILTIP) * 0.5
        k = lab[int(mid[1]), int(mid[0])]
        if k == 0:
            ys, xs = np.nonzero(lab); j = np.argmin(np.hypot(xs - mid[0], ys - mid[1])); k = lab[ys[j], xs[j]]
        _RF.update(mask=lab == k, im=im)
    return _RF

def fish_ref(P, ppm=PPM):
    """list of (pose, bool mask on the piece grid): the reference tetra at each mockup fish pose, 0.82 x length"""
    rf = ref_fish_mask(); XX, YY = grid(P, ppm); out = []
    sn, tt = np.array(RF_SNOUT), np.array(RF_TAILTIP); Lr = np.hypot(*(sn - tt)); er = (sn - tt) / Lr
    nr = np.array([-er[1], er[0]])
    # belly side of the template: the template lies belly-down on the image (its lower side = +y)
    if nr[1] < 0: nr = -nr
    midr = (sn + tt) / 2
    for pose in fish_poses(P, ppm):
        L = pose["L"] * FISH_SCALE; a = math.radians(pose["ang"]); e = np.array([math.cos(a), math.sin(a)])
        nrm = np.array([-e[1], e[0]])
        if nrm[1] < 0: nrm = -nrm                                   # belly toward the garment's lower side
        c = np.array(pose["c"]); dx, dy = XX - c[0], YY - c[1]
        u = (dx * e[0] + dy * e[1]) / L; v = (dx * nrm[0] + dy * nrm[1]) / L
        cx = midr[0] + u * Lr * er[0] + v * Lr * nr[0]; cy = midr[1] + u * Lr * er[1] + v * Lr * nr[1]
        ok = (cx >= 0) & (cy >= 0) & (cx < rf["mask"].shape[1] - 1) & (cy < rf["mask"].shape[0] - 1)
        mm = np.zeros(XX.shape, bool)
        mm[ok] = map_coordinates(rf["mask"].astype(np.float32), [cy[ok], cx[ok]], order=1) > 0.5
        lum = np.full(XX.shape, -1.0, np.float32); Lim = rf["im"].mean(-1)
        lum[mm] = map_coordinates(Lim, [cy[mm], cx[mm]], order=1)
        q = np.quantile(lum[mm], [0.25, 0.5, 0.75]) if mm.any() else [0, 0, 0]
        tone = np.where(mm, np.digitize(lum, q), -1)
        out.append((dict(pose, L_ref=L, tone=tone), mm))
    return out

if __name__ == "__main__":
    import kbcore
    S = "out/refmask"; import os; os.makedirs(S, exist_ok=True)
    for P in kbcore.PIECES:
        rgb, zone, _ = source(P); fl = flora(P); fr = fish_ref(P)
        vis = (rgb * 0.6).astype(np.uint8); vis[fl] = (vis[fl] * 0.3 + np.array([255, 200, 0]) * 0.7).astype(np.uint8)
        for _, m in fr: vis[m] = (0, 255, 255)
        vis[fish_px(P)[0] & ~np.any([m for _, m in fr] or [np.zeros_like(fl)], axis=0)] //= 2
        Image.fromarray(vis).save(f"{S}/{P}.png")
        print(P, "flora mm2", round(fl.sum() / PPM ** 2), "fish", [(round(p["c"][0]), round(p["c"][1]), round(p["ang"]), round(p["L"])) for p, _ in fr])
