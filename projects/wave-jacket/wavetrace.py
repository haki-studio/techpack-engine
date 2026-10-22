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
    if view == "front" and os.path.exists("cu_reg.json"):
        lab = closeup_labels(lab, up, b)
    if os.path.exists("cu_regs.json"):
        lab = closeups_labels(view, lab, up, b)
    lab = mask_details(view, lab, up, b)
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

# garment details of the RENDER that read as art (LESSONS A15): the welt-pocket lips are light lines on the front and were
# traced as stripes / rope lines, then mapped onto the body where the pattern's welt sits ~5 cm away (fix round 2). Corridors
# in render px (centre line + half width) read off inputs/front.png; masked to fabric before tracing (the mockup shows no art
# under a welt - its opening hides it).
DETAILS_PX = {"front": [((448, 485), (522, 572), 16.0), ((215, 488), (132, 575), 16.0)]}

def mask_details(view, lab, up, b):
    from shapely.geometry import LineString
    from shapely import contains_xy
    Hh, Ww = lab.shape
    yy, xx = np.mgrid[0:Hh, 0:Ww]; X = xx / up + b[0] + 0.5 / up; Y = yy / up + b[1] + 0.5 / up
    for a, c, hw in DETAILS_PX.get(view, []):
        poly = LineString([a, c]).buffer(hw, cap_style="flat")
        m = contains_xy(poly, X, Y) & np.isin(lab, ids(CREAM + GREY + BLUES))
        lab = np.where(m, NAMES.index("f2"), lab)
    return lab

def closeup_labels(lab, up, b, inset=3.0):
    """LESSONS A12: inside the footprint of the founder's detail close-up (inputs/closeup_mockup_foam.png, registered
    onto the render by register_cu.py), classes come from the close-up pixels (~4 close-up px per render px), not from
    the render. The render still decides placement (the registration maps the close-up onto it)."""
    import json
    from shapely.geometry import Polygon
    from shapely import contains_xy
    R_ = json.load(open("cu_reg.json")); H = np.array(R_["H"])
    cu = np.asarray(Image.open("inputs/closeup_mockup_foam.png").convert("RGB")).astype(float)
    h, w = cu.shape[:2]
    corners = np.array([[0, 0, 1], [w, 0, 1], [w, h, 1], [0, h, 1]], float) @ H.T; corners = corners[:, :2] / corners[:, 2:]
    foot = Polygon(corners).buffer(-inset)
    Hh, Ww = lab.shape
    yy, xx = np.mgrid[0:Hh, 0:Ww]; X = xx / up + b[0] + 0.5 / up; Y = yy / up + b[1] + 0.5 / up
    ins = contains_xy(foot, X, Y) & (lab >= 0)
    if not ins.any(): return lab
    Hi = np.linalg.inv(H); P = np.stack([X[ins], Y[ins], np.ones(ins.sum())]); q = Hi @ P; u, v = q[0] / q[2], q[1] / q[2]
    rgb = np.stack([ndi.map_coordinates(ndi.gaussian_filter(cu[..., k], 1.2), [v, u], order=1) for k in range(3)], -1)
    L = TR.lab_img(rgb[None])[0]; Pt = TR.lab_img(np.array([t[1] for t in TONES], float)[None])[0]
    d = ((L[:, None, :] - Pt[None]) ** 2).sum(-1); cl = d.argmin(1)
    new = lab.copy(); new[ins] = cl
    oh = np.stack([ndi.uniform_filter((new == i).astype(np.float32), 5) for i in range(len(TONES))], -1)
    sm = oh.argmax(-1); new = np.where(ins, sm, lab)
    return new

CU_ARTEFACT = (29, 43, 67)       # the sleeve composite's separator / masking colour (founder: blotches are not design)
CU_STATS = {}

def closeup_pixels(c):
    """(rgb float array of the close-up crop, valid mask) - artefact pixels (exact separator colour, +2 px) are invalid"""
    a = np.asarray(Image.open(c["file"]).convert("RGB"))
    if c.get("crop"): x0, y0, x1, y1 = c["crop"]; a = a[y0:y1, x0:x1]
    bad = (a == np.array(CU_ARTEFACT, np.uint8)).all(-1)
    bad = ndi.binary_dilation(bad, iterations=2)
    return a.astype(np.float32), ~bad

def closeups_labels(view, lab, up, b, inset=2.0):
    """Founder close-ups (20 Oct, register_closeups.py -> cu_regs.json): inside each footprint the classes come from the
    close-up pixels (6-14 close-up px per render px), outside from the render. The close-ups are pixel-aligned
    super-resolutions of the same render, so placement and motif counts stay the mockup's (founder rule); artefact pixels
    keep the render's class."""
    import json
    from shapely.geometry import Polygon
    from shapely import contains_xy
    Pt = TR.lab_img(np.array([t[1] for t in TONES], float)[None])[0]
    Hh, Ww = lab.shape
    yy, xx = np.mgrid[0:Hh, 0:Ww]; X = xx / up + b[0] + 0.5 / up; Y = yy / up + b[1] + 0.5 / up
    new = lab.copy(); done = np.zeros(lab.shape, bool)
    for c in json.load(open("cu_regs.json")):
        if c["view"] != view or not c["ok"]: continue
        foot = Polygon(c["footprint_render_px"]).buffer(-inset)
        ins = contains_xy(foot, X, Y) & (lab >= 0) & ~done
        if not ins.any(): continue
        cu, valid = closeup_pixels(c); H = np.array(c["H"])
        Hi = np.linalg.inv(H); P = np.stack([X[ins], Y[ins], np.ones(ins.sum())]); q = Hi @ P; u, v = q[0] / q[2], q[1] / q[2]
        k = c["cu_px_per_render_px"] / up               # close-up px per label px: blur to that footprint
        ok = ndi.map_coordinates(valid.astype(np.float32), [v, u], order=0) > 0.5
        rgb = np.stack([ndi.map_coordinates(ndi.gaussian_filter(cu[..., j], 0.4 * k), [v, u], order=1) for j in range(3)], -1)
        L = TR.lab_img(rgb[None])[0]
        cl = np.empty(len(L), np.int32)
        for s0 in range(0, len(L), 200000):
            d = ((L[s0:s0 + 200000, None, :] - Pt[None]) ** 2).sum(-1); cl[s0:s0 + 200000] = d.argmin(1)
        iy, ix = np.nonzero(ins); iy, ix = iy[ok], ix[ok]
        before = lab[iy, ix]; new[iy, ix] = cl[ok]; done[iy, ix] = True
        art = ids(CREAM + GREY + BLUES)
        CU_STATS[c["name"]] = dict(px=int(ok.sum()), same_class=round(float((before == cl[ok]).mean()), 3),
                                   art_render=int(np.isin(before, art).sum()), art_closeup=int(np.isin(cl[ok], art).sum()))
    oh = np.stack([ndi.uniform_filter((new == i).astype(np.float32), 3) for i in range(len(TONES))], -1)
    sm = oh.argmax(-1)
    # founder rule (20 Oct): the MOCKUP governs what / where; close-ups only inform detail inside each motif. The close-ups
    # resolve the washed duck's crease highlights as pale-blue / cream lines on bare fabric (traced as stray stripes and rope
    # lines below the FL crest, along the sleeve edges): a close-up art pixel only counts within 2 render px of art the
    # render itself shows; elsewhere the render's (fabric) class stays.
    art_ids = ids(CREAM + GREY + BLUES)
    near = ndi.binary_dilation(np.isin(lab, art_ids), iterations=2 * up)
    sm = np.where(np.isin(sm, art_ids) & ~near, lab, sm)
    out = np.where(done, sm, lab)
    # crease highlights: inside a footprint, an art component that is thin + elongated (skeleton length / mean width > 6),
    # small (< 60 render px2) and 3 render px clear of any other art is a wash crease of the duck, not a stripe / rope line
    # (drops are compact, spray tails touch their drop). Set back to fabric.
    art = np.isin(out, art_ids); cl, n = ndi.label(art, structure=np.ones((3, 3)))
    if n:
        big = np.zeros(n + 1, bool); area = ndi.sum(art, cl, range(1, n + 1)) / (up * up)
        for k, sl in enumerate(ndi.find_objects(cl), 1):
            if area[k - 1] >= 60 or not done[sl].any(): continue
            m = cl[sl] == k
            L = morphology.skeletonize(m).sum() / up; w = area[k - 1] / max(L, 1e-6)
            if L / max(w, 1e-6) <= 6: continue
            ring = ndi.binary_dilation(np.pad(m, 3 * up), iterations=3 * up)
            y0, x0 = sl[0].start - 3 * up, sl[1].start - 3 * up
            Y0, X0 = max(0, y0), max(0, x0); Y1, X1 = min(out.shape[0], sl[0].stop + 3 * up), min(out.shape[1], sl[1].stop + 3 * up)
            ringc = ring[Y0 - y0:Y0 - y0 + (Y1 - Y0), X0 - x0:X0 - x0 + (X1 - X0)]
            others = art[Y0:Y1, X0:X1] & (cl[Y0:Y1, X0:X1] != k)
            if (ringc & others).any(): continue
            out[sl][m] = NAMES.index("f2"); CU_STATS.setdefault("creases_dropped", 0); CU_STATS["creases_dropped"] += 1
    return out

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

def dots_hr(view, tr, margin=2.0):
    """PR #27 review 1 (A14 drops): a spray drop is 4-25 mm2, i.e. 8-50 render px, so its silhouette from the x4 label map
    (~2.8 px/mm) is off by about one gate pixel. Inside a founder close-up footprint each drop is re-traced from the close-up's
    OWN pixels (4-10 px/mm): nearest render tone per close-up px, the cream + grey component(s) overlapping the drop, holes
    filled, back to render px through the registration. Placement and count stay the mockup's (the component must overlap
    the mockup drop); shade / grey / blue parts are re-cut on the new outline. Drops outside every footprint keep the x4 trace."""
    import json
    from shapely.geometry import Polygon as _P, box as _box
    from shapely import affinity as _aff
    if not os.path.exists("cu_regs.json"): return tr, 0
    regs = [c for c in json.load(open("cu_regs.json")) if c["view"] == view and c["ok"]]
    Pt = TR.lab_img(np.array([t[1] for t in TONES], float)[None])[0]
    cg_ids = ids(CREAM + GREY); n_ok = 0; cache = {}
    for c in tr["foam"]:
        if c["kind"] != "dot" or c["filled"].is_empty: continue
        F = c["filled"]; bx = F.bounds
        reg = next((r for r in regs if _P(r["footprint_render_px"]).buffer(-margin - 1).contains(_box(*bx))), None)
        if reg is None: continue
        if reg["name"] not in cache: cache[reg["name"]] = closeup_pixels(reg)
        cu, valid = cache[reg["name"]]; H = np.array(reg["H"]); Hi = np.linalg.inv(H)
        q = np.array([[bx[0] - margin, bx[1] - margin, 1], [bx[2] + margin, bx[3] + margin, 1]]) @ Hi.T; q = q[:, :2] / q[:, 2:]
        x0, y0 = np.floor(q.min(0)).astype(int); x1, y1 = np.ceil(q.max(0)).astype(int)
        x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(cu.shape[1], x1), min(cu.shape[0], y1)
        if x1 - x0 < 4 or y1 - y0 < 4: continue
        a = ndi.gaussian_filter(cu[y0:y1, x0:x1], (0.6, 0.6, 0)); ok = valid[y0:y1, x0:x1]
        L = TR.lab_img(a); cl = ((L[:, :, None, :] - Pt[None, None]) ** 2).sum(-1).argmin(-1)
        art = np.isin(cl, cg_ids) & ok
        art = ndi.binary_opening(art, iterations=1)
        # the mockup drop, in close-up px: the component(s) that overlap it are the drop
        Fc = _aff.affine_transform(F, [Hi[0, 0], Hi[0, 1], Hi[1, 0], Hi[1, 1], Hi[0, 2] - x0, Hi[1, 2] - y0])
        from PIL import Image as _I, ImageDraw as _D
        im = _I.new("1", (x1 - x0, y1 - y0), 0); dd = _D.Draw(im)
        for p in TR_polys(Fc.buffer(0)): dd.polygon(list(p.exterior.coords), fill=1)
        fm = np.array(im, bool)
        lab_, n_ = ndi.label(art)
        keep = [k for k in range(1, n_ + 1) if ((lab_ == k) & fm).any()]
        if not keep: continue
        m = ndi.binary_fill_holes(np.isin(lab_, keep))
        g = TR.polys_of(m, 1, (x0, y0), min_px=4, simplify=0.6)
        if g.is_empty: continue
        g = _aff.affine_transform(g, [H[0, 0], H[0, 1], H[1, 0], H[1, 1], H[0, 2], H[1, 2]]).buffer(0)
        if g.is_empty or g.area < 0.3 * F.area or g.area > 3.0 * F.area: continue      # registration / class sanity
        def part(name):
            mm_ = m & (cl == NAMES.index(name))
            if not mm_.any(): return _P()
            pg = TR.polys_of(mm_, 1, (x0, y0), min_px=4, simplify=0.6)
            return _aff.affine_transform(pg, [H[0, 0], H[0, 1], H[1, 0], H[1, 1], H[0, 2], H[1, 2]]).buffer(0).intersection(g) if not pg.is_empty else _P()
        c["filled"] = g; c["mass"] = g; c["shade"] = part("w3"); c["grey"] = part("g1"); c["inner"] = {}
        c["blue"] = {n: b_.difference(g) for n, b_ in c.get("blue", {}).items() if not b_.difference(g).is_empty}
        c["hr"] = reg["name"]; n_ok += 1
    return tr, n_ok

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
        tr, lab = trace_view(view); tr = drop_blues(tr); tr, nhr = dots_hr(view, tr); print(view, "drops re-traced from close-ups", nhr, flush=True)
        pickle.dump(tr, open(f"trace_{view}.pkl", "wb"))
        preview(view, lab, tr["up"], tr["box"], f"out/trace/{view}_classes.png")
        nd = sum(1 for c in tr["foam"] if c["kind"] == "dot"); nc = len(tr["foam"]) - nd
        print(view, "crests", nc, "drops", nd, "band area px", round(tr["band_all"].area), "lines px", round(tr["lines"].area), flush=True)
