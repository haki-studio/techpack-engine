"""Tonal trace of the wave art from the low-res render (inputs/back.png, front.png), in RENDER PX.
Every pixel inside the jacket silhouette is classed to the nearest render tone (CIE Lab, x4 Lanczos upscale - it adds no
detail, it only smooths the class boundaries, pipeline §0b); then
  bands : the six blues (pale -> ultramarine), each one geometry; band pixels hidden under foam / lines are filled from
          the nearest band tone within 5 px, so a band ends UNDER its crest, never in a gap
  lines : thin cream strokes (the rope lines between the bands, spray tails) = cream thinner than ~3.4 px
  foam  : thick cream/grey masses = crests and curls; each connected mass is one component with its own interior
          (grey curl hollows, the shade cream, blue claws inside the curl) so it can be moved as one rigid motif
  dots  : small foam components (spray drops), with their blue lower halves
usage: ./py.sh wavetrace.py  ->  trace_<view>.pkl  + out/trace/<view>_classes.png"""
import os, pickle, sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
import trace as TR, mockmap as MM

# render tones (sampled by k-means inside the silhouette) -> class name
TONES = [
    ("w1", (240, 237, 234)), ("w2", (222, 217, 214)), ("w3", (194, 189, 186)), ("g1", (160, 159, 160)),
    ("b0", (177, 199, 216)), ("b1", (128, 174, 208)), ("b2", (82, 141, 190)), ("b3", (31, 101, 168)),
    ("b4", (5, 66, 153)), ("b5", (3, 40, 112)),
    ("f0", (16, 19, 28)), ("f1", (29, 35, 52)), ("f2", (39, 47, 67)), ("f3", (53, 62, 83)), ("f4", (78, 89, 110)),
    ("f5", (116, 126, 143)), ("zip", (109, 87, 60)),
]
NAMES = [t[0] for t in TONES]
CREAM = ["w1", "w2", "w3"]; GREY = ["g1"]; BLUES = ["b0", "b1", "b2", "b3", "b4", "b5"]
FABRIC = ["f0", "f1", "f2", "f3", "f4", "f5", "zip"]
BOX = {"back": (0, 230, 620, 740), "front": (0, 190, 640, 720)}
UP = 4
DOT_MAX = 70.0          # foam components smaller than this (render px²) are spray drops
CORE_W = 6.0            # cream wider than this (render px, ~8.5 mm) is a crest core
ROPE_L = 16.0           # thinner cream at least this long (render px) lying on a band is a rope line

def ids(names): return [NAMES.index(n) for n in names]

def classify(view):
    img = MM.image(view); b = BOX[view]
    sil = MM.silhouette(view)
    def mask(rc, up, bb):
        r, c = rc; X = np.clip((c / up + bb[0]).astype(int), 0, sil.shape[1] - 1); Y = np.clip((r / up + bb[1]).astype(int), 0, sil.shape[0] - 1)
        return sil[Y, X]
    lab, up = TR.label_map(img, b, TONES, up=UP, sigma=0.45, majority=5, mask=mask)
    # grey + washed fabric look alike: grey only counts inside / next to foam (within 2 px of cream)
    cream = np.isin(lab, ids(CREAM))
    near_c = ndi.binary_dilation(cream, iterations=2 * up)
    grey = np.isin(lab, ids(GREY))
    lab = np.where(grey & ~near_c, NAMES.index("f5"), lab)
    # the palest blue + f5 confusion: pale blue only next to other blues or cream
    art = np.isin(lab, ids(CREAM + GREY + BLUES))
    art = morphology.remove_small_objects(art, int(1.2 * up * up))
    lab = np.where(np.isin(lab, ids(CREAM + GREY + BLUES)) & ~art, NAMES.index("f2"), lab)
    return lab, up, b

def trace_view(view):
    lab, up, b = classify(view)
    out = dict(view=view, box=b, up=up)
    cg = np.isin(lab, ids(CREAM + GREY))
    # crest cores = cream wider than CORE_W; cream thinner than that is a rope line if it is long, else it stays with
    # the crest it touches (curl tails), or is a spray drop when it touches nothing
    core = morphology.binary_opening(cg, morphology.disk(int(round(CORE_W * up / 2))))
    foam = cg & ndi.binary_dilation(core, iterations=up)
    rest = cg & ~foam
    rl, nr = ndi.label(rest, structure=np.ones((3, 3)))
    near_band = ndi.binary_dilation(np.isin(lab, ids(BLUES)), iterations=2 * up)
    touch = ndi.binary_dilation(foam, iterations=2)
    thin = np.zeros_like(cg)
    for i, sl in enumerate(ndi.find_objects(rl), 1):
        m = rl[sl] == i
        a = m.sum() / (up * up)
        if a < 1.0: continue
        L = morphology.skeletonize(m).sum() / up               # centre-line length, render px
        w = a / max(L, 1e-6)
        on_band = (m & near_band[sl]).sum() / m.sum()
        if L >= ROPE_L and on_band > 0.5: thin[sl] |= m          # rope line along a band
        elif (m & touch[sl]).any(): foam[sl] |= m                # curl tail / lobe edge
        elif on_band > 0.5 and L >= 6: thin[sl] |= m             # short rope dash on a band
        else: foam[sl] |= m                                      # spray drop / fleck
    # ---- bands: blue labels; pixels under foam / lines take the nearest band tone (within 5 px)
    blue = np.isin(lab, ids(BLUES))
    # the render's stitch texture leaves dark (fabric-class) slits between band strokes: close them into the band
    art = blue | foam | thin
    closed = morphology.binary_closing(art, morphology.disk(int(1.3 * up)))
    closed = morphology.remove_small_holes(closed, int(8 * up * up))
    slit = closed & ~art
    dist, (iy, ix) = ndi.distance_transform_edt(~blue, return_indices=True)
    lab = np.where(slit & (dist < 3 * up), lab[iy, ix], lab)
    blue = np.isin(lab, ids(BLUES))
    dist, (iy, ix) = ndi.distance_transform_edt(~blue, return_indices=True)
    under = (foam | thin) & (dist < 5 * up)
    blab = np.where(blue, lab, -1); blab = np.where(under, lab[iy, ix], blab)
    # smooth the stripe tones (the render's thread sheen speckles them): majority vote over ~2 render px, band area kept
    ins = blab >= 0
    oh = np.stack([ndi.uniform_filter((blab == NAMES.index(n)).astype(np.float32), 2 * up + 1) for n in BLUES], -1)
    blab = np.where(ins, np.array(ids(BLUES))[oh.argmax(-1)], -1)
    # the render's edge highlights (sleeve folds, collar, hem) read as thin pale lines: nothing thin within 5 px of the
    # silhouette edge is art
    sil = MM.silhouette(view)[b[1]:b[3], b[0]:b[2]]
    edge = ~ndi.binary_erosion(sil, iterations=5)
    edge = np.kron(edge, np.ones((up, up), bool))[:thin.shape[0], :thin.shape[1]]
    tl, nt = ndi.label(thin, structure=np.ones((3, 3)))
    edge9 = ~ndi.binary_erosion(sil, iterations=10)
    edge9 = np.kron(edge9, np.ones((up, up), bool))[:thin.shape[0], :thin.shape[1]]
    for i, sl in enumerate(ndi.find_objects(tl), 1):
        m = tl[sl] == i
        if (m & edge9[sl]).sum() > 0.5 * m.sum(): thin[sl] &= ~m
    bl_, nb = ndi.label(blab >= 0)
    for i, sl in enumerate(ndi.find_objects(bl_), 1):
        m = bl_[sl] == i
        if m.sum() < 400 * up * up and (m & edge[sl]).sum() > 0.3 * m.sum(): blab[sl] = np.where(m, -1, blab[sl])
    out["lines"] = TR.polys_of(thin, up, b, min_px=2, simplify=0.10)
    bands = {}
    for n in BLUES:
        bands[n] = TR.polys_of(blab == NAMES.index(n), up, b, min_px=3, simplify=0.12)
    out["bands"] = bands
    out["band_all"] = TR.polys_of(blab >= 0, up, b, min_px=3, simplify=0.12)

    # ---- foam components
    edgeF = np.kron(~ndi.binary_erosion(MM.silhouette(view)[b[1]:b[3], b[0]:b[2]], iterations=10), np.ones((up, up), bool))[:foam.shape[0], :foam.shape[1]]
    fl, nf = ndi.label(foam)
    comps = []
    objs = ndi.find_objects(fl)
    for i, sl in enumerate(objs, 1):
        m = fl[sl] == i
        area_px = m.sum() / (up * up)
        if area_px < 1.5: continue
        filled = ndi.binary_fill_holes(m)
        inner = filled & ~m
        sub = lab[sl]
        y0, x0 = sl[0].start, sl[1].start
        bb = (b[0] + x0 / up, b[1] + y0 / up, b[0] + sl[1].stop / up, b[1] + sl[0].stop / up)
        def P(mask): return TR.polys_of(mask, up, (bb[0], bb[1]), min_px=1, simplify=0.10)
        c = dict(mass=P(m), filled=P(filled), area=area_px,
                 shade=P(m & (sub == NAMES.index("w3"))), grey=P(m & (sub == NAMES.index("g1"))),
                 inner={n: P(inner & (sub == NAMES.index(n))) for n in BLUES + GREY + CREAM})
        c["inner"] = {k: v for k, v in c["inner"].items() if not v.is_empty and v.area > 0.3}
        c["kind"] = "dot" if area_px < DOT_MAX else "crest"
        if c["mass"].is_empty: continue
        sk_ = morphology.skeletonize(m).sum() / up
        if (m & edgeF[sl]).sum() > 0.4 * m.sum() and sk_ > 15 and area_px / max(sk_, 1) < 3.5: continue   # long thin fold highlight
        # dots: their blue lower half = band-blue pixels touching the drop (within 1.5 px), not part of a band
        comps.append(c)
    out["foam"] = comps
    return out, lab

def drop_blues(tr):
    """blue pixels of a spray drop (the light-blue underside) belong to the drop, not to a band: give small isolated
    blue islands next to a drop to that drop"""
    band_big = [p for p in TR_polys(tr["band_all"]) if p.area > 40]
    big = unary_union(band_big) if band_big else Polygon()
    for c in tr["foam"]:
        if c["kind"] != "dot": continue
        halo = c["filled"].buffer(2.0)
        c["blue"] = {}
        for n, g in tr["bands"].items():
            q = g.intersection(halo).difference(big)
            if not q.is_empty and q.area > 0.4: c["blue"][n] = q
    for n in list(tr["bands"]):
        tr["bands"][n] = tr["bands"][n].intersection(big.buffer(0.01)) if not big.is_empty else tr["bands"][n]
    return tr

def TR_polys(g):
    if g.is_empty: return []
    return [g] if g.geom_type == "Polygon" else [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]

PALE = {"w1": (240, 237, 234), "w2": (222, 217, 214), "w3": (194, 189, 186), "g1": (160, 159, 160), "b0": (177, 199, 216),
        "b1": (128, 174, 208), "b2": (82, 141, 190), "b3": (31, 101, 168), "b4": (5, 66, 153), "b5": (3, 40, 112)}

def preview(view, lab, up, b, path):
    cols = np.array([t[1] for t in TONES], np.uint8)
    im = cols[np.clip(lab, 0, None)]; im[lab < 0] = 255
    Image.fromarray(im).resize(((b[2] - b[0]) * 2, (b[3] - b[1]) * 2), Image.NEAREST).save(path)

if __name__ == "__main__":
    os.makedirs("out/trace", exist_ok=True)
    for view in (sys.argv[1:] or ["back", "front"]):
        tr, lab = trace_view(view); tr = drop_blues(tr)
        pickle.dump(tr, open(f"trace_{view}.pkl", "wb"))
        preview(view, lab, tr["up"], tr["box"], f"out/trace/{view}_classes.png")
        nd = sum(1 for c in tr["foam"] if c["kind"] == "dot"); nc = len(tr["foam"]) - nd
        print(view, "crests", nc, "drops", nd, "band area px", round(tr["band_all"].area), "lines px", round(tr["lines"].area), flush=True)
