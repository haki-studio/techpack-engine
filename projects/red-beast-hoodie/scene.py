"""Rev B scene: traced label rasters (trace_M.npz) -> stitch OBJECTS that follow the close-up's stitch structure
(LESSONS A12/A13, review Rev A items 2, 3, 4, 6, 7, 8, 12). Rev A (scene_revA.py) filled tone regions with 14 mm tatami cells.

Per piece space (F = both fronts, SR, SL), size M, garment / sleeve mm:
  1. labels: 3x3 majority, small fabric holes inside the art -> black ground, then one-hot smoothing (no stair steps)
  2. slash streaks (zones on the fronts, everything red on the sleeves) -> tapered pointed columns, one per streak
     (strokes.streaks: per bundle PCA direction + across-profile peaks); their pixels leave the red mass
  3. cream: teeth (inside the mouth) = one object each, satin ALONG the tooth (vertical stitches) + white edge run;
     outlines = cords redrawn from the skeleton at 2.5-3.0 mm (thin detail lines keep their width, >= 1.2), tips tapered;
     lightning (wearer's right front) = 2.5 mm root -> 1.0 mm tip by distance along the branch; every fork kept
  4. crimson under-edge: 1 mm band below every cord (raised-cord shadow), crimson along the lower edge of red strands
  5. red / crimson / black: evenly spaced streamlines of the flow field (structure tensor of the close-up texture + strand
     edges), random lengths (long-and-short), every pixel to its nearest streamline -> one stroke object per tile,
     sewn as satin ALONG the stroke (fixed angle = the stroke's own direction)
  6. specks: islands < 8 mm2 with no stroke neighbour within 1.5 mm are dropped (A8)
usage: python3 scene.py   -> scene.pkl + out/trace/scene_<space>.png"""
import rbcore
import pickle, math, time, json, os
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
import shapely
import strokes as SK
from trace import MOUTH

T = np.load("trace_M.npz"); PPM = float(T["ppm"])
LAYER = {"rb_red": 20, "rb_crimson": 21, "rb_black": 22, "rb_cream": 23, "rb_white": 24}

# slash-streak zones on the fronts (front mm, read off out/trace/trace_F.png with a 20 mm grid)
ZONES_F = {
    "FR_low": Polygon([(-185, 300), (-100, 300), (-60, 318), (-5, 318), (-5, 390), (-185, 390)]),
    "FL_low": Polygon([(2, 330), (120, 330), (150, 400), (200, 415), (245, 415), (245, 485), (2, 485)]),
    "FL_shoulder": Polygon([(45, -45), (305, -45), (305, 178), (250, 178), (200, 95), (130, 40), (45, 35)]),
}
LIGHTNING_X = 0.0          # cream on the wearer's right front (x < 0) = lightning branches (taper rule, item 12)
TEETH = Polygon(MOUTH).buffer(-2.0)          # inside the jaw lines: the jaw outlines stay cords, teeth are their own objects

def disk(mm): return SK.disk_px(mm*PPM/2)

def grid_xy(bb, shape):
    x0, y0 = bb[0], bb[1]
    xs = x0 + (np.arange(shape[1]) + 0.5)/PPM; ys = y0 + (np.arange(shape[0]) + 0.5)/PPM
    return np.meshgrid(xs, ys)

def majority(lab, valid):
    cnt = np.stack([ndi.uniform_filter((lab == k).astype(np.float32), 3) for k in range(5)], 0)
    out = np.argmax(cnt, 0).astype(np.uint8); out[~valid] = 9
    return out

def smooth_classes(lab, valid, sigma_mm=0.3):
    cnt = np.stack([ndi.gaussian_filter((lab == k).astype(np.float32), sigma_mm*PPM) for k in range(5)], 0)
    out = np.argmax(cnt, 0).astype(np.uint8); out[~valid] = 9
    return out

def fill_ground(lab):
    """fabric specks enclosed by the art (black-thread highlights in the close-up read as fabric) -> black ground"""
    art = (lab >= 1) & (lab <= 4)
    holes = ndi.binary_fill_holes(art) & ~art & (lab == 0)
    hl, n = ndi.label(holes)
    if n:
        sz = ndi.sum(np.ones_like(hl), hl, index=np.arange(1, n + 1))/PPM**2
        small = np.isin(hl, 1 + np.nonzero(sz < 25)[0])
        lab = lab.copy(); lab[small] = 3
    return lab

def split_teeth(m):
    """one label per tooth: watershed on the distance map, markers = local maxima >= 4 mm apart"""
    from skimage.segmentation import watershed
    from skimage.feature import peak_local_max
    dt = ndi.distance_transform_edt(m)
    lb0, _ = ndi.label(m)
    pk = peak_local_max(dt, min_distance=int(4.0*PPM), labels=lb0, exclude_border=False)
    mk = np.zeros(m.shape, np.int32)
    for i, (y, x) in enumerate(pk, 1): mk[y, x] = i
    lab = watershed(-dt, mk, mask=m)
    return lab, int(lab.max())

def R(col, geom, st, ang, grp, **kw):
    d = dict(col=col, geom=geom, st=st, ang=ang, grp=grp, ko=True, kob=0.0, unit=None, layer=LAYER[col]); d.update(kw); return d

def to_regs(mask, x0, y0, col, grp, st="satin"):
    """thin mask -> one turning satin per skeleton branch (cords, bands)"""
    from scene_revA import branches
    regs = []
    tl, nt = ndi.label(mask, structure=np.ones((3, 3)))
    for i, sl in enumerate(ndi.find_objects(tl), 1):
        if sl is None: continue
        pad = 3
        ys = slice(max(sl[0].start - pad, 0), min(sl[0].stop + pad, mask.shape[0]))
        xs = slice(max(sl[1].start - pad, 0), min(sl[1].stop + pad, mask.shape[1]))
        sub = tl[ys, xs] == i
        if sub.sum() < 0.5*PPM**2: continue
        bl, nb = branches(sub)
        ox, oy = x0 + xs.start/PPM, y0 + ys.start/PPM
        for j in range(1, nb + 1):
            bm = bl == j
            if bm.sum() < 0.4*PPM**2: continue
            g = SK.smooth_geom(SK.mask_geom(bm, ox, oy, PPM), 0.12, 0.06)
            for p in getattr(g, "geoms", [g]):
                if p.geom_type == "Polygon" and p.area >= 0.4: regs.append(R(col, p, st, "auto", grp))
    return regs

def stroke_regs(mask, theta, x0, y0, col, grp, dsep, Lmin, Lmax, seed):
    Tl, lines = SK.stroke_tiles(mask, theta, PPM, dsep=dsep, Lmin=Lmin, Lmax=Lmax, seed=seed)
    regs = []
    for p, a in SK.tiles_to_polys(Tl, lines, x0, y0, PPM):
        w = 2*p.area/max(p.length, 1e-6)
        if w >= 1.1:   # stroke: satin ALONG the stroke (long-and-short), angle = this stroke's direction
            regs.append(R(col, p, "satin", round(float(a) % 180.0, 1), grp, fixed=True))
        else:          # hairline tip: plain turning satin
            regs.append(R(col, p, "satin", "auto", grp))
    return regs, len(lines)

def grow_min(m, w_mm=1.0):
    """every strand at least w_mm wide: add a w_mm disc along its own skeleton"""
    from skimage.morphology import skeletonize
    return m | (ndi.binary_dilation(skeletonize(m), structure=disk(w_mm)) & ~np.zeros_like(m))

def vectorize(sp, lab, Lsrc, bb, closeup=None):
    x0, y0 = bb[0], bb[1]; X, Y = grid_xy(bb, lab.shape)
    valid = lab != 9
    lab = majority(lab, valid)
    if sp == "F": lab = fill_ground(lab)
    lab = smooth_classes(lab, valid)
    lab0 = lab.copy()
    st = {}
    regs = []
    cream = lab == 4; red = lab == 1; crim = lab == 2; blk = lab == 3
    # ---------------- 2. slash streaks
    if sp == "F":
        zone = np.zeros(lab.shape, bool)
        for z in ZONES_F.values(): zone |= shapely.contains_xy(z, X, Y)
        head = ndi.binary_fill_holes(ndi.binary_closing(cream | blk, structure=disk(6.0)))
        head = ndi.binary_dilation(head, structure=disk(2.0))
        sm = (red | crim) & zone & ~head & ~ndi.binary_dilation(cream | blk, structure=disk(2.0))
        blk = blk & ~(zone & ~head)                 # no black ground under streaks on bare fabric
    else:
        sm = red | crim
    sm = ndi.binary_opening(sm, structure=np.ones((2, 2)))
    sts = SK.streaks(sm, crim, PPM, x0, y0)
    keep_out = SK.mask_geom(cream, x0, y0, PPM).buffer(0.3) if cream.any() else Polygon()
    ns = 0
    for p, col, ab, w in sts:
        g = p.difference(keep_out) if not keep_out.is_empty else p
        for q in getattr(g, "geoms", [g]):
            if q.geom_type == "Polygon" and q.area > 0.8: regs.append(R(col, q, "satin", "auto", "SK")); ns += 1
    st["streaks"] = ns; st["streak_list"] = [(round(ab[0][0], 1), round(ab[0][1], 1), round(ab[1][0], 1), round(ab[1][1], 1), round(w, 2), col) for p, col, ab, w in sts]
    red &= ~sm; crim &= ~sm
    # sleeves: no hair mass - every red pixel is a streak
    if sp != "F":
        red[:] = False; crim[:] = False; blk[:] = False
        if sp == "SL": cream[:] = False                  # review item 8: stray cream stop on SL (render highlights)
    # ---------------- 3. cream: teeth, cords, lightning
    teeth = cream & shapely.contains_xy(TEETH, X, Y) if sp == "F" else np.zeros_like(cream)
    teeth = ndi.binary_opening(teeth, structure=disk(0.8))
    rest = cream & ~teeth
    light = rest & (X < LIGHTNING_X) if sp == "F" else rest
    outl = rest & ~light
    cord = np.zeros_like(cream)
    if outl.any():
        c1, _, _ = SK.cords(outl, PPM, "outline", wmin=1.2, wmax=3.0); cord |= c1 & valid
    if light.any():
        c2, _, _ = SK.cords(light, PPM, "lightning", root=2.5, tip=1.0, ramp=6.0); cord |= c2 & valid
    cord &= ~teeth
    # teeth: one object per tooth, satin along the tooth (vertical stitches), white edge run
    tl, nt = split_teeth(teeth); ntooth = 0
    for i, sl in enumerate(ndi.find_objects(tl), 1):
        if sl is None: continue
        g = SK.smooth_geom(SK.mask_geom(tl[sl] == i, x0 + sl[1].start/PPM, y0 + sl[0].start/PPM, PPM), 0.45, 0.08)
        for p in getattr(g, "geoms", [g]):
            if p.geom_type != "Polygon" or p.area < 1.5: continue
            from stitchrender import auto_angle
            a = (auto_angle(p) - 90) % 180          # long axis of the tooth
            regs.append(R("rb_cream", p, "satin", round(a, 1), "OL-tooth", fixed=True)); ntooth += 1
            e = p.buffer(-0.75)
            if p.area > 5 and not e.is_empty and e.geom_type == "Polygon" and e.area > 0.5:
                regs.append(R("rb_white", e.exterior.buffer(0.3), "bean", "auto", "OL-hl"))   # path 0.45 inside the tooth edge
    st["teeth"] = ntooth
    regs += to_regs(cord, x0, y0, "rb_cream", "OL")
    # ---------------- 4. crimson under-edges
    sh = np.zeros_like(cream)
    if sp != "SL":
        cord_o = cord & ~light if sp == "F" else np.zeros_like(cord)    # outlines only: lightning has no under-edge in the mockup
        thick = ndi.binary_erosion(cord_o, structure=disk(1.9))          # cord parts >= ~1.9 mm wide cast the shadow
        src = ndi.binary_dilation(thick, structure=disk(1.9)) & cord_o
        dy, dx = int(round(0.9*PPM)), int(round(0.25*PPM))
        shifted = np.zeros_like(src); shifted[dy:, dx:] = src[:-dy, :-dx]
        sh = shifted & ~cord & ~teeth & valid & ~blk & ~sm
        sh = ndi.binary_opening(sh, structure=np.ones((2, 2)))
    redfull = red & ~cord & ~teeth & ~sh
    if sp == "F":
        thick_r = ndi.binary_opening(redfull, structure=disk(4.0))      # only broad strands get a shaded lower edge
        below = np.zeros_like(redfull); d2 = int(round(0.9*PPM)); below[:-d2] = redfull[d2:]
        lower = redfull & ~below & ndi.binary_dilation(thick_r, structure=disk(1.0))
        crim = (crim | lower) & ~cord & ~teeth
        red = redfull & ~lower
    regs += to_regs(sh & ~crim, x0, y0, "rb_crimson", "OL-shadow")
    st["shadow_mm2"] = round(float(sh.sum())/PPM**2)
    # ---------------- 5. stroke tiling (red, crimson, black) along the flow field
    if sp == "F":
        theta = SK.flow_field(Lsrc, [red | crim, cord], PPM, sigma_mm=2.0)
        blk = blk & ~cord & ~teeth
        crim = crim & ~blk
        red = red & ~blk
        done = {}
        def others(col):
            o = np.zeros_like(cord)
            for c_, mm in done.items(): o |= mm
            return o
        for k, (m, col, grp, dsep, L0, L1) in enumerate(((red, "rb_red", "HS", 2.2, 5.0, 12.0),
                                                          (crim, "rb_crimson", "CS", 1.8, 4.0, 9.0),
                                                          (blk, "rb_black", "BS", 2.6, 5.0, 11.0))):
            m = ndi.binary_opening(m, structure=np.ones((2, 2))) | (m & ndi.binary_erosion(m))
            lb, n = ndi.label(m)
            if n:
                sz = ndi.sum(np.ones_like(lb), lb, index=np.arange(1, n + 1))/PPM**2
                m = np.isin(lb, 1 + np.nonzero(sz >= 0.6)[0])
            hl, nh = ndi.label(ndi.binary_fill_holes(m) & ~m & (lab0 == 0))     # pin-holes inside a tone (trace noise)
            if nh:
                hs = ndi.sum(np.ones_like(hl), hl, index=np.arange(1, nh + 1))/PPM**2
                m |= np.isin(hl, 1 + np.nonzero(hs < 3.0)[0])
            if col != "rb_black": m = grow_min(m, 1.0)
            m &= ~cord & ~teeth & ~sh & ~others(col)
            done[col] = m
            rr, nl = stroke_regs(m, theta, x0, y0, col, grp, dsep, L0, L1, seed=k + 1)
            regs += rr; st[col] = dict(strokes=len(rr), lines=nl, area=round(float(m.sum())/PPM**2))
    return regs, st

def drop_specks(regs, amax=8.0, gap=1.5):
    """A8 + review item 7: islands < 8 mm2 with no other object within 1.5 mm are render noise, not thread"""
    tree = shapely.STRtree([r["geom"] for r in regs]); out = []; nd = 0
    for i, r in enumerate(regs):
        if r["geom"].area < amax and r["st"] != "bean":
            hits = [j for j in tree.query(r["geom"].buffer(gap)) if j != i and regs[j]["st"] != "bean"]
            if not hits: nd += 1; continue
        out.append(r)
    return out, nd

def preview(regs, bb, path, ppm=2.0):
    import stitchrender as SR
    SR.render(regs, bb, ppm, base=rbcore.FABRIC).save(path)

if __name__ == "__main__":
    import sys
    t0 = time.time(); out = {"meta": {}}
    for sp in [a for a in sys.argv[1:] if a in ("F", "SR", "SL")] or ("F", "SR", "SL"):
        lab = T[sp]; L = T["L" + sp]
        bb = tuple(T["bbF"]) if sp == "F" else tuple(T["bbS"])
        regs, st = vectorize(sp, lab, L, bb)
        regs, nd = drop_specks(regs); st["specks_dropped"] = nd
        for i, r in enumerate(regs): r["z"] = r["layer"]*100000 + i; r["el"] = "01" if sp == "F" else "02"
        out[sp] = regs; out["meta"][sp] = st
        print(sp, len(regs), {k: v for k, v in st.items() if k != "streak_list"}, f"{time.time()-t0:.0f}s", flush=True)
        if "png" in sys.argv: preview(regs, bb, f"out/trace/scene_{sp}.png")
    if os.path.exists("scene.pkl") and len(out) < 4:
        old = pickle.load(open("scene.pkl", "rb"))
        for k in ("F", "SR", "SL"):
            if k not in out and k in old: out[k] = old[k]; out["meta"][k] = old["meta"].get(k)
    out["meta"]["closeup_reg"] = json.load(open("inputs/closeup_reg.json"))
    out["meta"]["rev"] = "B"
    pickle.dump(out, open("scene.pkl", "wb"))
