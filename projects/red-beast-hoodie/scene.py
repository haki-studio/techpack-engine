"""Traced label rasters (trace_M.npz) -> stitch regions on the size-M pieces (unclipped).

Per colour class:
  * majority-filter the labels, drop specks < 0.6 mm2;
  * thick core = opening with a 4.6 mm disc (width >= 4.6) -> tatami along the stroke flow, cut into 14 mm cells,
    each with its own angle (structure tensor of the source stitch texture, sigma 2.5 mm) = long-and-short look;
  * the rest (strands, outlines, lightning branches, teeth) -> split at every fork of its skeleton into branches
    (each pixel goes to its nearest branch) -> one satin column per branch, turning along its centreline.
Output: scene.pkl = {"F": [...], "SR": [...], "SL": [...], "meta": {...}}; regions in garment / sleeve mm.
usage: python3 scene.py"""
import rbcore
import pickle, math, time, json
import numpy as np
from scipy import ndimage as ndi
from skimage import measure
from skimage.morphology import skeletonize
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from shapely import affinity
import shapely

T = np.load("trace_M.npz"); PPM = float(T["ppm"])
CLS = {1: "rb_red", 2: "rb_crimson", 3: "rb_black", 4: "rb_cream"}
LAYER = {"rb_red": 20, "rb_crimson": 21, "rb_black": 22, "rb_cream": 23}
CODE = {("F", "rb_red"): "HR", ("F", "rb_crimson"): "HR", ("F", "rb_black"): "BK", ("F", "rb_cream"): "OL",
        ("S", "rb_red"): "SK", ("S", "rb_crimson"): "SK", ("S", "rb_black"): "BK", ("S", "rb_cream"): "OL"}
CORE_W, CELL = 4.6, 14.0

def disk(mm):
    r = max(1, int(round(mm*PPM/2))); y, x = np.ogrid[-r:r+1, -r:r+1]; return x*x + y*y <= r*r

def majority(lab, valid):
    """3x3 majority vote over the art classes (removes single-pixel class noise at the boundaries)"""
    cnt = np.stack([ndi.uniform_filter((lab == k).astype(np.float32), 3) for k in range(5)], 0)
    out = np.argmax(cnt, 0).astype(np.uint8); out[~valid] = 9
    return out

def mask_geom(m, x0, y0):
    """binary mask (crop) -> shapely geometry in mm (even-odd over all contour rings)"""
    cs = measure.find_contours(np.pad(m, 1).astype(np.float32), 0.5)
    g = Polygon()
    for c in sorted(cs, key=len, reverse=True):
        if len(c) < 4: continue
        p = Polygon([(x0 + (x - 0.5)/PPM, y0 + (y - 0.5)/PPM) for y, x in c]).buffer(0)
        if p.area < 0.02: continue
        g = g.symmetric_difference(p)
    return g.buffer(0).simplify(0.08).buffer(0)

def flow_angles(L, sigma_mm=2.5):
    gy, gx = np.gradient(ndi.gaussian_filter(L, 0.6*PPM/4))
    s = sigma_mm*PPM
    jxx, jyy, jxy = ndi.gaussian_filter(gx*gx, s), ndi.gaussian_filter(gy*gy, s), ndi.gaussian_filter(gx*gy, s)
    th = 0.5*np.arctan2(2*jxy, jxx - jyy)              # dominant gradient direction
    return np.degrees(th) + 90.0                        # strokes run across the gradient

def branches(m):
    """split a thin mask into skeleton branches; returns a label image (0 = none) over m"""
    sk = skeletonize(m)
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode="constant") - 1
    junc = sk & (nb >= 3)
    seg = sk & ~ndi.binary_dilation(junc, structure=np.ones((3, 3)))
    bl, n = ndi.label(seg, structure=np.ones((3, 3)))
    if n == 0: return bl, 0
    # drop short spurs (end branches shorter than the local width): their pixels go to the neighbour branch
    dt = ndi.distance_transform_edt(m)
    size = ndi.sum(np.ones_like(bl), bl, index=np.arange(1, n + 1))
    wid = ndi.maximum(dt, bl, index=np.arange(1, n + 1)) * 2
    ends = ndi.sum((nb == 1) & seg, bl, index=np.arange(1, n + 1))
    keep = ~((ends >= 1) & (size < np.maximum(5, 1.3*wid)) & (n > 1))
    lut = np.zeros(n + 1, np.int32); lut[1:] = np.where(keep, np.arange(1, n + 1), 0)
    bl = lut[bl]
    if bl.max() == 0: bl = ndi.label(sk, structure=np.ones((3, 3)))[0]
    # every mask pixel -> nearest branch pixel
    _, (iy, ix) = ndi.distance_transform_edt(bl == 0, return_indices=True)
    out = bl[iy, ix]; out[~m] = 0
    return out, int(out.max())

def R(col, geom, st, ang, grp, **kw):
    d = dict(col=col, geom=geom, st=st, ang=ang, grp=grp, ko=True, kob=0.0, unit=None); d.update(kw); return d

def vectorize(space, lab, Lsrc, bb, piece_kind):
    x0, y0 = bb[0], bb[1]
    valid = lab != 9
    lab = majority(lab, valid)
    ang = flow_angles(Lsrc)
    regs = []; stats = {}
    for k, col in CLS.items():
        m = lab == k
        m = ndi.binary_opening(m, structure=np.ones((2, 2))) | (ndi.binary_closing(m, structure=np.ones((2, 2))) & m)
        lb, n = ndi.label(m)
        if n:
            sz = ndi.sum(np.ones_like(lb), lb, index=np.arange(1, n + 1)) / PPM**2
            m = np.isin(lb, 1 + np.nonzero(sz >= 0.6)[0])
        if not m.any(): continue
        core = ndi.binary_opening(m, structure=disk(CORE_W)) if col != "rb_cream" or True else np.zeros_like(m)
        thin = m & ~core
        thin = ndi.binary_opening(thin, structure=np.ones((2, 2))) | (thin & ~ndi.binary_dilation(core, iterations=1))
        code = CODE[(piece_kind, col)]
        nf = ns = 0
        # thick cores: tatami cells along the flow
        cl, nc = ndi.label(core)
        for i, sl in enumerate(ndi.find_objects(cl), 1):
            if sl is None: continue
            sub = cl[sl] == i
            g = mask_geom(sub, x0 + sl[1].start/PPM, y0 + sl[0].start/PPM)
            if g.is_empty or g.area < 2: continue
            gb = g.bounds
            for cx in np.arange(gb[0], gb[2], CELL):
                for cy in np.arange(gb[1], gb[3], CELL):
                    c = g.intersection(box(cx, cy, cx + CELL, cy + CELL)).buffer(0)
                    if c.is_empty or c.area < 1.0: continue
                    pt = c.representative_point(); px_, py_ = int((pt.x - x0)*PPM), int((pt.y - y0)*PPM)
                    a = float(ang[min(max(py_, 0), ang.shape[0]-1), min(max(px_, 0), ang.shape[1]-1)])
                    regs.append(R(col, c, "tatami", round(a, 1), code + "-fill", layer=LAYER[col])); nf += 1
        # thin parts: one satin column per skeleton branch
        tl, nt = ndi.label(thin, structure=np.ones((3, 3)))
        for i, sl in enumerate(ndi.find_objects(tl), 1):
            if sl is None: continue
            pad = 3
            ys = slice(max(sl[0].start - pad, 0), min(sl[0].stop + pad, thin.shape[0]))
            xs = slice(max(sl[1].start - pad, 0), min(sl[1].stop + pad, thin.shape[1]))
            sub = tl[ys, xs] == i
            if sub.sum() < 0.6*PPM**2: continue
            bl, nb_ = branches(sub)
            ox, oy = x0 + xs.start/PPM, y0 + ys.start/PPM
            for j in range(1, nb_ + 1):
                bm = bl == j
                if bm.sum() < 0.5*PPM**2: continue
                g = mask_geom(bm, ox, oy)
                if g.is_empty: continue
                for p in (g.geoms if hasattr(g, "geoms") else [g]):
                    if p.geom_type != "Polygon" or p.area < 0.5: continue
                    regs.append(R(col, p, "satin", "auto", code, layer=LAYER[col])); ns += 1
        stats[col] = dict(fill_cells=nf, satin_branches=ns, area=round(float(m.sum())/PPM**2))
    return regs, stats

def drop_specks(regs, amax=3.0, gap=1.5):
    """isolated tiny bits on bare fabric (denim highlights read as cream / red in the source) - not thread"""
    tree = shapely.STRtree([r["geom"] for r in regs]); out = []; nd = 0
    for i, r in enumerate(regs):
        if r["geom"].area < amax:
            hits = [j for j in tree.query(r["geom"].buffer(gap)) if j != i]
            if not hits: nd += 1; continue
        out.append(r)
    return out, nd

if __name__ == "__main__":
    t0 = time.time(); out = {"meta": {}}
    for sp in ("F", "SR", "SL"):
        lab = T[sp]; L = T["L" + sp] if ("L" + sp) in T else T["LF"]
        bb = tuple(T["bbF"]) if sp == "F" else tuple(T["bbS"])
        regs, st = vectorize(sp, lab, L, bb, "F" if sp == "F" else "S")
        regs, nd = drop_specks(regs); st["specks_dropped"] = nd
        for i, r in enumerate(regs): r["z"] = r["layer"]*100000 + i; r["el"] = "01" if sp == "F" else "02"
        out[sp] = regs; out["meta"][sp] = st
        print(sp, len(regs), st, f"{time.time()-t0:.0f}s", flush=True)
    out["meta"]["closeup_reg"] = json.load(open("inputs/closeup_reg.json"))
    pickle.dump(out, open("scene.pkl", "wb"))
