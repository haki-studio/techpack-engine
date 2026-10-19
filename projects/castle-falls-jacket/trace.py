"""Tonal trace (fidelity first): mockup warped into piece mm space (mockmap.warp, source Lanczos x4 — reads shapes, adds no
detail) -> every pixel to one of 40 mockup tone clusters (k-means over all five pieces, km_centres.npy) -> thread tone
(CLUSTER_THREAD) -> bare fabric where large dark-neutral areas are (the mockup's unembroidered navy) -> dark pixels inside
the art take the darkest thread of the tone around them (shadow of the neighbour) -> majority filter -> regions.

Output per piece: tone label array (index into TONES, -1 = fabric), at PPM px/mm over the piece bbox (+ bleed)."""
import cfcore
import os, pickle
import numpy as np
from scipy import ndimage as ndi
from tonemap import lab

PPM = 3.0
TONES = cfcore.CF_KEYS                      # thread keys; label = index
TI = {k: i for i, k in enumerate(TONES)}
DARK = "DARK"
# k-means cluster -> thread (or DARK = dark neutral: fabric if in a large area, else the neighbour's shadow thread)
CLUSTER_THREAD = {
    26: DARK, 35: DARK, 29: DARK, 8: DARK, 17: DARK,            # bluish darks = the navy shell (fabric if in a large area)
    28: "SHADOW", 16: "SHADOW", 15: "SHADOW", 11: "SHADOW",      # neutral / greenish darks = shadows inside the art, never fabric
    31: "cf_navy", 24: "cf_brown", 0: "cf_red", 36: "cf_grndk", 39: "cf_navy", 20: "cf_grndk", 25: "cf_slate",
    32: "cf_brown", 38: "cf_sky", 2: "cf_red", 14: "cf_grn", 22: "cf_slate", 34: "cf_slate", 5: "cf_rose",
    18: "cf_bark", 33: "cf_sky", 6: "cf_grn", 30: "cf_slate", 4: "cf_mist", 19: "cf_rose", 21: "cf_skylt",
    10: "cf_bark", 12: "cf_grnlt", 7: "cf_mist", 27: "cf_bark", 9: "cf_pink", 23: "cf_mist", 3: "cf_cream",
    37: "cf_pinklt", 1: "cf_white", 13: "cf_white",
}
SHADOW = {"cf_skylt": "cf_navy", "cf_sky": "cf_navy", "cf_navy": "cf_navy", "cf_slate": "cf_navy", "cf_lav": "cf_slate",
          "cf_mist": "cf_slate", "cf_cream": "cf_mist", "cf_white": "cf_mist", "cf_grndk": "cf_grndk", "cf_grn": "cf_grndk",
          "cf_grnlt": "cf_grndk", "cf_pinklt": "cf_rose", "cf_pink": "cf_rose", "cf_rose": "cf_rose", "cf_red": "cf_brown",
          "cf_gold": "cf_brown", "cf_bark": "cf_brown", "cf_brown": "cf_brown"}
FABRIC_OPEN_MM = 2.6        # dark areas wider than this are bare fabric

def disk(mm, ppm=PPM):
    r = max(1, int(round(mm * ppm / 2))); y, x = np.ogrid[-r:r + 1, -r:r + 1]; return x * x + y * y <= r * r

MIN_ISLAND = 2.5

def merge_small(t, amin):
    out = t.copy(); px = amin * PPM * PPM
    for k in np.unique(t):
        lab_, n = ndi.label(t == k)
        if n == 0: continue
        sz = ndi.sum(np.ones_like(t), lab_, np.arange(1, n + 1))
        small = np.isin(lab_, np.nonzero(sz < px)[0] + 1)
        out[small] = -9
    _, (iy, ix) = ndi.distance_transform_edt(out == -9, return_indices=True)
    return np.where(out == -9, out[iy, ix], out)

def fabric_absorb(t, amax=60.0):
    """navy / slate / sky specks on bare fabric (fabric wash read as tone) become fabric: components < amax mm2 whose
    surrounding ring is mostly fabric"""
    out = t.copy()
    for k in (TI["cf_navy"], TI["cf_slate"], TI["cf_sky"], TI["cf_skylt"], TI["cf_mist"]):
        lab_, n = ndi.label(out == k)
        if n == 0: continue
        sl = ndi.find_objects(lab_)
        for i, s in enumerate(sl, 1):
            ys = slice(max(0, s[0].start - 3), s[0].stop + 3); xs = slice(max(0, s[1].start - 3), s[1].stop + 3)
            m = lab_[ys, xs] == i
            if m.sum() > amax * PPM * PPM: continue
            ring = ndi.binary_dilation(m, iterations=2) & ~m
            if ring.sum() and (out[ys, xs][ring] == -1).mean() > 0.55: out[ys, xs][m] = -1
    return out

def classify(rgb):
    C = np.load("km_centres.npy")
    L = lab(ndi.gaussian_filter(rgb, (0.8, 0.8, 0)))
    best = np.full(L.shape[:2], np.inf); cl = np.zeros(L.shape[:2], int)
    for i, c in enumerate(C):
        d = ((L - c) ** 2).sum(-1); w = d < best; best[w] = d[w]; cl[w] = i
    return cl

def tone_map(P, cache=True):
    cp = f"trace_{P}.pkl"
    if cache and os.path.exists(cp) and os.path.getmtime(cp) > max(os.path.getmtime(__file__), os.path.getmtime("warps_M.pkl")):
        return pickle.load(open(cp, "rb"))
    W = pickle.load(open("warps_M.pkl", "rb")); bbox, rgb = W[P]
    cl = classify(rgb)
    lut = np.array([-2 if CLUSTER_THREAD[i] == DARK else (-3 if CLUSTER_THREAD[i] == "SHADOW" else TI[CLUSTER_THREAD[i]]) for i in range(len(CLUSTER_THREAD))])
    t = lut[cl]
    shadow = t == -3
    dark = t == -2
    # washed fabric reads partly as navy / slate / sky speckle: those count as fabric where the area is mostly dark
    weak = dark | np.isin(t, [TI["cf_navy"], TI["cf_slate"], TI["cf_sky"]])
    frac = ndi.uniform_filter(dark.astype(np.float32), int(6 * PPM))
    cand = dark | (weak & (frac > 0.5))
    fabric = ndi.binary_opening(cand, structure=disk(FABRIC_OPEN_MM))
    dark = dark | (cand & fabric)
    fabric = ndi.binary_dilation(fabric, structure=disk(0.7)) & dark          # back to the dark area's own edge
    # dark inside the art: shadow thread of the nearest thread tone
    inner = (dark & ~fabric) | shadow
    _, (iy, ix) = ndi.distance_transform_edt((t < 0), return_indices=True)
    near = t[iy, ix]
    sh = np.array([TI[SHADOW[k]] for k in TONES])
    t = np.where(inner, sh[np.clip(near, 0, None)], t)
    t = np.where(fabric, -1, t)
    # majority filter (mode over a 1.0 mm window) — removes 1-px speckle, keeps 1.2 mm source features
    n = len(TONES) + 1
    oh = np.stack([ndi.uniform_filter((t == (k - 1)).astype(np.float32), 3) for k in range(n)], -1)
    t = oh.argmax(-1) - 1
    if P == "BK":          # the mockup's CB fold line (px 357-360) is not art: fill it from the columns beside it
        x0 = bbox[0]; c0 = int((-1.5 - x0) * PPM); c1 = int((5.5 - x0) * PPM)
        for c in range(c0, c1): t[:, c] = t[:, c0 - 1 - (c - c0)] if c < (c0 + c1) // 2 else t[:, c1 + (c1 - 1 - c)]
    # navy / slate in an area that is otherwise fabric (> 80 % fabric/navy/slate over 12 mm) is the fabric wash, not art
    nv = (t == -1) | np.isin(t, [TI["cf_navy"], TI["cf_slate"]])
    fr2 = ndi.uniform_filter(nv.astype(np.float32), int(12 * PPM))
    strong = ndi.uniform_filter((~nv & (t >= 0)).astype(np.float32), int(12 * PPM))
    t = np.where(np.isin(t, [TI["cf_navy"], TI["cf_slate"]]) & (fr2 > 0.8) & (strong < 0.06), -1, t)
    t = fabric_absorb(t)
    # bare shell enclosed by art (dark rock faces, deep shadows) is shadow thread, not a hole: only shell connected to the open
    # shell around the art, or a very large patch, stays bare (the dark close-up rock face read as shell, 16 Oct)
    lab_, n = ndi.label(t == -1)
    if n:
        edge = set(np.unique(np.r_[lab_[0], lab_[-1], lab_[:, 0], lab_[:, -1]])) - {0}
        sz = ndi.sum(np.ones_like(lab_), lab_, np.arange(1, n + 1)) / PPM ** 2
        keep = [i + 1 for i in range(n) if (i + 1) in edge or sz[i] > 4000]
        hole = (lab_ > 0) & ~np.isin(lab_, keep)
        _, (iy2, ix2) = ndi.distance_transform_edt(hole | (t < 0), return_indices=True)
        near2 = t[iy2, ix2]
        LIGHT = {"cf_white", "cf_cream", "cf_pinklt", "cf_pink", "cf_skylt", "cf_grnlt", "cf_gold"}
        sh2 = np.array([TI[SHADOW[k]] if k in LIGHT else TI[k] for k in TONES])      # mid / dark neighbours continue as themselves
        t = np.where(hole, sh2[np.clip(near2, 0, None)], t)
    # islands below MIN_ISLAND mm2 join the tone around them (nearest-tone fill): no fabric holes, fewer trims
    t = merge_small(t, MIN_ISLAND)
    res = dict(P=P, bbox=bbox, ppm=PPM, t=t.astype(np.int8))
    if cache: pickle.dump(res, open(cp, "wb"))
    return res

def tone_png(res, path):
    from PIL import Image
    from tonemap import hexrgb
    cols = np.array([hexrgb(cfcore.FABRIC)] + [hexrgb(cfcore.CF_PAL[k][0]) for k in TONES], np.uint8)
    Image.fromarray(cols[res["t"].astype(int) + 1]).save(path)

if __name__ == "__main__":
    import sys
    for P in sys.argv[1:] or cfcore.PIECES:
        r = tone_map(P, cache=False); pickle.dump(r, open(f"trace_{P}.pkl", "wb"))
        os.makedirs("out/art", exist_ok=True); tone_png(r, f"out/art/tones_{P}.png")
        u, c = np.unique(r["t"], return_counts=True)
        print(P, {("fabric" if k < 0 else TONES[k]): round(100 * v / c.sum(), 1) for k, v in zip(u, c)}, flush=True)
