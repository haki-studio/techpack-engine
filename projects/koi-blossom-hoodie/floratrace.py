"""Flora traced from the input pixels, motif by motif (Rev C, review items 2-4; LESSONS A12-A15).

Source image per piece = refmask.source(P): the mockup mapped onto the size-M piece (mm grid, 5 px/mm), with the two
close-up lilies pasted in their registration discs on FR (the close-up governs there). Garment details (keep-outs,
welts, background, sleeve inner edge) and the mockup fish (colour: light blobs holding red) are masked out first.
This tracer has its OWN flora classifier (thresholds differ from the gate's refmask.flora on purpose: the gate is not
fed by this mask).

  lilies   every lily (2 close-up + 4 mockup: FR hem, FL hem big, FL dark flower, SR cuff) = its own petal fan: one guide
           per petal (centre -> tip, width; read on 8-10x gridded zooms of THAT flower) clipped to the traced silhouette,
           stacked back -> front; tone regions = the pixels' nearest thread (Lab), cleaned (islands < 2.5 mm2 merged),
           <= 3 tones per petal; stitched as TATAMI ROWS ALONG THE PETAL AXIS (long rows, not a radial fan).
           Throat = the dark pixels round the centre; anthers = the cream pixels round the centre (>= 1.8 mm knots).
  leaves   the rest of every cluster silhouette, split leaf by leaf: watershed on the distance transform (one marker per
           leaf body, >= 3.5 mm apart) + the luminance edges between leaves, segments merged back where the shared edge
           is wide and the colour the same (one leaf cut in two). Each leaf: traced outline, axis + length from its
           pixels (PCA), <= 2 traced tones (nearest thread).
  stems    the thin parts of the silhouette (narrower than 2.6 mm), traced outline, nearest thread.
  petals   the small free components (< 150 mm2, no cluster): traced outline, <= 2 traced tones.
trace(P) -> dict(regs=[region dicts], lilies=[...], info=...)."""
import math
import numpy as np
from scipy import ndimage as ndi
from scipy.interpolate import griddata
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
from skimage import measure
from skimage.segmentation import watershed
from skimage.feature import peak_local_max
import refmask as R, mockmap as MM, front as F

PPM = R.PPM
FLORA_THREADS = ["kb_navy", "kb_cobalt", "kb_royal", "kb_blue", "kb_sky", "kb_ice", "kb_white"]      # blue family only: the mockup flora reads blue (Rev B review item 3); slate stays a fish thread
DARK_ORDER = {k: i for i, k in enumerate(["kb_navy", "kb_cobalt", "kb_royal", "kb_slate", "kb_blue", "kb_sky", "kb_ice", "kb_white"])}

# ---------------------------------------------------------------- lily guides (source px): centre, [(tip, width px)] back -> front
# close-up lilies: close-up px (cu_trace FLOWERS, read on 2x gridded zooms of the close-up)
CU_GUIDES = {
 "lily0": dict(c=(95, 415), petals=[((118, 232), 46), ((-12, 330), 58), ((-25, 470), 62), ((282, 413), 58), ((182, 537), 72), ((176, 298), 74)]),
 "lily1": dict(c=(250, 680), petals=[((105, 598), 42), ((228, 558), 56), ((108, 712), 52), ((222, 803), 48), ((378, 790), 58), ((357, 640), 58)]),
}
# mockup lilies: mockup px, read on 8-10x gridded zooms of front.png (Rev C) — each flower's own fan
MK_GUIDES = {
 "FR_hem":  dict(piece="FR", c=(346, 757), petals=[((358, 733), 8), ((356, 779), 8), ((312, 749), 9), ((330, 789), 14), ((347, 714), 15)]),
 "FL_big":  dict(piece="FL", c=(483, 754), petals=[((523, 724), 18), ((518, 782), 20), ((470, 798), 20), ((437, 743), 20), ((483, 705), 22)]),
 "FL_dark": dict(piece="FL", c=(567, 746), petals=[((598, 738), 9), ((560, 782), 10), ((583, 770), 13), ((538, 728), 13), ((573, 719), 12)]),
 "SR_cuff": dict(piece="SR", c=(46, 883), petals=[((17, 858), 12), ((60, 912), 16), ((16, 898), 18), ((82, 869), 18), ((46, 846), 16)]),
}

def _lab(rgb):
    c = np.asarray(rgb, float) / 255.0
    c = np.where(c > 0.04045, ((c + 0.055) / 1.055) ** 2.4, c / 12.92)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.9505, 1.0, 1.089])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)

def hexrgb(h): h = h.lstrip("#"); return [int(h[i:i + 2], 16) for i in (0, 2, 4)]
def polys(g): return [p for p in (g.geoms if hasattr(g, "geoms") else [g]) if p.geom_type == "Polygon" and not p.is_empty]

def to_mm(P, xs, ys):
    """source px -> piece mm (vectorised): fronts linear, sleeves through the mockmap cylinder grid"""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    if P in ("FR", "FL"):
        return (xs - MM.CFX) * MM.SX, (ys - MM.NECKY) * MM.SY
    mt = F.pieces("M")[1]; pts, tu = MM._grid(P, mt)
    t_u = griddata(pts, tu, np.c_[xs, ys], method="linear")
    bad = np.isnan(t_u[:, 0])
    if bad.any(): t_u[bad] = griddata(pts, tu, np.c_[xs, ys][bad], method="nearest")
    t, u = t_u[:, 0], t_u[:, 1]
    y = (-mt["cap_h"] + t * (mt["Lu"] + mt["cap_h"])) * (1 - u) + t * mt["Lu"] * u
    hw = mt["W"] + (mt["Ww"] - mt["W"]) * np.clip(y, 0, None) / mt["Lu"]
    x = u * hw
    return (x if P == "SR" else -x), y

def cu_to_mock(name, xs, ys):
    A = R._A(); c_cu = np.array(R.CU_LILY[name][0], float); c_mk = np.array(R.MK_LILY[name], float)
    d = np.stack([np.asarray(xs, float) - c_cu[0], np.asarray(ys, float) - c_cu[1]], -1) @ A.T
    return d[..., 0] + c_mk[0], d[..., 1] + c_mk[1]

def lanceolate(c, tip, w, n=30, wmax_at=0.42):
    c = np.array(c, float); t = np.array(tip, float); d = t - c; L = np.hypot(*d); u = d / L; nv = np.array([-u[1], u[0]])
    s = np.linspace(0, 1, n)
    hw = w / 2 * np.where(s < wmax_at, np.clip(np.sin(np.pi / 2 * s / wmax_at), 0, 1) ** 0.7,
                          np.clip(np.cos(np.pi / 2 * np.clip(s - wmax_at, 0, None) / (1 - wmax_at)), 0, 1) ** 0.9)
    hw[0] = w * 0.12
    return np.array([c + u * L * si + nv * h for si, h in zip(s, hw)] + [c + u * L * si - nv * h for si, h in zip(s, hw)][::-1])

# ---------------------------------------------------------------- raster helpers
def grid_xy(P):
    return R.grid(P)

def poly_of_mask(m, P, smooth=0.35, simp=0.08, off=(0, 0)):
    """bool mask on the piece grid (or a window of it starting at row/col `off`) -> list of polygons (mm), holes kept"""
    bb = R.BB[P]; bb = (bb[0] + off[1] / PPM, bb[1] + off[0] / PPM); lab, n = ndi.label(m); out = []
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        mm = np.pad(lab[sl] == k, 2)
        if mm.sum() < 3: continue
        rings = measure.find_contours(mm.astype(float), 0.5)
        y0, x0 = sl[0].start - 2, sl[1].start - 2
        ps = [Polygon([(bb[0] + (x0 + c[1]) / PPM, bb[1] + (y0 + c[0]) / PPM) for c in r]).buffer(0) for r in rings if len(r) > 3]
        ps = sorted([p for p in ps if not p.is_empty], key=lambda p: -p.area)
        if not ps: continue
        g = ps[0]
        for h in ps[1:]:
            if g.contains(h.representative_point()): g = g.difference(h)
        sm = min(smooth, 0.08 * g.area ** 0.5)
        g = (g.buffer(sm, join_style=1).buffer(-sm, join_style=1) if sm > 0.05 else g).simplify(simp).buffer(0)
        out += polys(g)
    return out

_C = {}
def base(P):
    """(rgb, flora mask E, thread class map cls, zone) for piece P"""
    if P in _C: return _C[P]
    rgb, zone, _ = R.source(P); area = R.art_area(P)
    fab = np.median(rgb[area & ~zone], axis=0)
    dist = np.sqrt(((rgb - fab) ** 2).sum(-1)); L = rgb.mean(-1); blue = rgb[..., 2] - rgb[..., 0]
    E = area & (dist > 22) & ((blue > fab[2] - fab[0] + 14) | (L > fab.mean() + 50))
    E &= ~R.fish_px(P)[0] & ~R.fish_px(P, composed=True)[0]
    E = ndi.binary_opening(E, structure=R.disk(1.2))
    E = ndi.binary_closing(E, structure=R.disk(0.8)) & area
    lab, n = ndi.label(E)                       # isolated thin lines (welt edges, zip shine): not flora
    if n:
        wmax = ndi.maximum(ndi.distance_transform_edt(E), lab, range(1, n + 1)) * 2 / PPM
        E &= ~np.isin(lab, 1 + np.nonzero(wmax < 1.8)[0])
        lab, n = ndi.label(E)
        if n:                                   # long isolated lines (welt topstitching): length / width > 8 and width < 2.4 mm
            wmax = ndi.maximum(ndi.distance_transform_edt(E), lab, range(1, n + 1)) * 2 / PPM
            sz = ndi.sum(E, lab, range(1, n + 1)) / PPM ** 2
            E &= ~np.isin(lab, 1 + np.nonzero((wmax < 2.4) & (sz / np.maximum(wmax, 0.1) ** 2 > 8))[0])
    holes = ndi.binary_fill_holes(E) & ~E; hl, hn = ndi.label(holes)
    if hn: E |= np.isin(hl, 1 + np.nonzero(ndi.sum(holes, hl, range(1, hn + 1)) / PPM ** 2 < 4.0)[0])
    # nearest flora thread per pixel (Lab); blurred rim (outer 0.6 mm mixes in the fabric) takes the interior tone
    T = np.array([hexrgb(__import__("kbcore").KB_PAL[k][0]) for k in FLORA_THREADS], float)
    sm = ndi.gaussian_filter(rgb, (0.25 * PPM, 0.25 * PPM, 0))
    d = ((_lab(sm)[..., None, :] - _lab(T)[None, None]) ** 2).sum(-1); cls = d.argmin(-1)
    rim = E & ~ndi.binary_erosion(E, structure=R.disk(2.0))
    core = E & ~rim
    if core.any():
        idx = ndi.distance_transform_edt(~core, return_distances=False, return_indices=True)
        cls = np.where(rim, cls[idx[0], idx[1]], cls)
    oh = np.stack([ndi.uniform_filter((cls == k).astype(float), int(1.0 * PPM) | 1) for k in range(len(FLORA_THREADS))], -1)
    cls = np.where(E, oh.argmax(-1), -1)
    LUM[P] = ndi.gaussian_filter(rgb.mean(-1), 0.3 * PPM)
    _C[P] = (rgb, E, cls, zone)
    return _C[P]

LUM = {}
def clean_tones(cls, m, keep_max=2, min_mm2=2.5, min_share=0.12, lum=None, sigma_mm=1.2):
    """<= keep_max tones inside mask m (the dominant nearest-thread classes of its pixels). With `lum` (the source
    luminance window) the tones are laid out as smooth BANDS: the luminance is smoothed inside the motif (normalised
    gaussian, sigma 1.2 mm) and cut at the midpoints between the kept tones' own mean luminance -> long-and-short tone
    steps instead of pixel speckle. Islands < min_mm2 go to their neighbours."""
    v = cls[m]; v = v[v >= 0]
    if v.size == 0: return None, []
    cnt = np.bincount(v, minlength=len(FLORA_THREADS))
    keep = [k for k in np.argsort(cnt)[::-1][:keep_max] if cnt[k] >= min_share * v.size] or [int(cnt.argmax())]
    keep = sorted(keep, key=lambda k: DARK_ORDER[FLORA_THREADS[k]])
    if lum is not None and len(keep) > 1:
        s = sigma_mm * PPM; num = ndi.gaussian_filter(np.where(m, lum, 0.0), s); den = ndi.gaussian_filter(m.astype(float), s)
        Ls = num / np.maximum(den, 1e-6)
        means = [float(lum[m & (cls == k)].mean()) if (m & (cls == k)).any() else 0.0 for k in keep]
        order = np.argsort(means); keep = [keep[i] for i in order]; means = [means[i] for i in order]
        cuts = [(means[i] + means[i + 1]) / 2 for i in range(len(keep) - 1)]
        c2 = np.where(m, np.array(keep)[np.digitize(Ls, cuts)], -1)
    else:
        remap = np.array([min(keep, key=lambda kk: abs(kk - k)) for k in range(len(FLORA_THREADS))])
        c2 = np.where(m, remap[np.clip(cls, 0, None)], -1)
    min_px = min_mm2 * PPM ** 2
    for _ in range(3):
        bad = np.zeros_like(m)
        for k in keep:
            mk = (c2 == k); lb, n = ndi.label(mk)
            if n == 0: continue
            sz = ndi.sum(mk, lb, range(1, n + 1)); bad |= np.isin(lb, 1 + np.nonzero(sz < min_px)[0])
        if not bad.any() or bad.sum() == m.sum(): break
        src = m & ~bad; idx = ndi.distance_transform_edt(~src, return_distances=False, return_indices=True)
        c2 = np.where(m, c2[idx[0], idx[1]], -1)
    return c2, keep

def win(m, pad=6):
    ys, xs = np.nonzero(m)
    if not len(ys): return None
    return (slice(max(0, ys.min() - pad), ys.max() + pad + 1), slice(max(0, xs.min() - pad), xs.max() + pad + 1))

def sub_raster(P, geoms):
    return R.raster(geoms, P)

# ---------------------------------------------------------------- lilies
def lily_specs(P):
    out = []
    if P == "FR":
        for nm, g in CU_GUIDES.items():
            cx, cy = cu_to_mock(nm, [g["c"][0]], [g["c"][1]])
            pet = []
            for tip, w in g["petals"]:
                ring = lanceolate(g["c"], tip, w); mx, my = cu_to_mock(nm, ring[:, 0], ring[:, 1])
                pet.append((np.c_[mx, my], cu_to_mock(nm, [tip[0]], [tip[1]])))
            out.append(dict(name=f"cu_{nm}", src="close-up", c=(float(cx[0]), float(cy[0])), petals=pet))
    for nm, g in MK_GUIDES.items():
        if g["piece"] != P: continue
        out.append(dict(name=nm, src="mockup", c=g["c"], petals=[(lanceolate(g["c"], tip, w), ([tip[0]], [tip[1]])) for tip, w in g["petals"]]))
    return out

def trace_lilies(P, E, cls):
    res = []; taken = np.zeros_like(E)
    for spec in lily_specs(P):
        cx, cy = to_mm(P, [spec["c"][0]], [spec["c"][1]]); c = (float(cx[0]), float(cy[0]))
        Ed = ndi.binary_dilation(E, structure=R.disk(0.6))
        pr = []
        for ring, tip in spec["petals"]:
            x, y = to_mm(P, ring[:, 0], ring[:, 1]); g = Polygon(np.c_[x, y]).buffer(0)
            tx, ty = to_mm(P, tip[0], tip[1])
            pr.append((sub_raster(P, [g]) & Ed, (float(tx[0]), float(ty[0]))))
        petals = []
        for i, (m, tip) in enumerate(pr):
            vis = m.copy()
            for m2, _ in pr[i + 1:]: vis &= ~m2
            if vis.sum() < 3 * PPM ** 2: continue
            w_ = win(vis); c2, keep = clean_tones(cls[w_], vis[w_], keep_max=3, min_mm2=4.0, min_share=0.08, lum=LUM[P][w_])
            ang = math.degrees(math.atan2(tip[1] - c[1], tip[0] - c[0]))
            tones = []
            for k in keep:
                for q in poly_of_mask(c2 == k, P, off=(w_[0].start, w_[1].start)):
                    if q.area >= 1.0: tones.append((FLORA_THREADS[k], q))
            petals.append(dict(tones=tones, ang=ang, tip=tip, keep=[FLORA_THREADS[k] for k in keep]))
        Rr = float(np.median([math.hypot(p["tip"][0] - c[0], p["tip"][1] - c[1]) for p in petals])) if petals else 10.0
        XX, YY = grid_xy(P); rr = np.hypot(XX - c[0], YY - c[1])
        uni = np.zeros_like(E)
        for m, _ in pr: uni |= m
        dark = uni & (cls >= 0) & (cls <= 1) & (rr < 0.24 * Rr)
        throat = poly_of_mask(ndi.binary_closing(dark, structure=R.disk(0.8)), P)
        throat = max(throat, key=lambda q: q.area) if throat else Point(c).buffer(0.1 * Rr)
        throat = throat.union(Point(c).buffer(max(1.2, 0.09 * Rr))).buffer(0)
        light = uni & (cls >= 5) & (rr < 0.42 * Rr) & (rr > 0.05 * Rr) & (LUM[P] > 172)
        knots = sorted([q for q in poly_of_mask(light, P) if q.area >= 0.5], key=lambda q: -q.area)[:6]
        knots = [q.buffer(0.35).buffer(0) if q.minimum_rotated_rectangle.length / 4 < 0.9 else q for q in knots]
        knots = [q if q.area >= 2.5 else q.union(Point(q.centroid.x, q.centroid.y).buffer(0.9)).buffer(0) for q in knots]
        res.append(dict(name=spec["name"], src=spec["src"], c=c, R=Rr, petals=petals, throat=throat, knots=knots))
        taken |= uni
    return res, taken

# ---------------------------------------------------------------- leaves + stems
def segment(P, rest, rgb):
    """rest: flora pixels of the clusters minus lilies -> (leaf label map, stem mask)"""
    op = ndi.binary_opening(rest, structure=R.disk(2.6))
    thin = rest & ~op
    # thin bits touching one leaf body and small = that leaf's tip; elongated / large thin parts = stems
    tl, tn = ndi.label(thin); stems = np.zeros_like(rest)
    L = rgb.mean(-1); grad = ndi.gaussian_gradient_magnitude(L, 0.6 * PPM)
    dt = ndi.distance_transform_edt(op) / PPM
    comp, _ = ndi.label(op)
    pk = peak_local_max(dt, min_distance=int(3.5 * PPM), threshold_abs=1.2, labels=comp)
    mk = np.zeros(rest.shape, int); mk[tuple(pk.T)] = np.arange(1, len(pk) + 1)
    # every op component gets at least one marker
    have = set(np.unique(comp[mk > 0]))
    for k, sl in enumerate(ndi.find_objects(comp), 1):
        if k in have or sl is None: continue
        sub = (comp[sl] == k) * dt[sl]; j = np.unravel_index(np.argmax(sub), sub.shape)
        mk[sl[0].start + j[0], sl[1].start + j[1]] = mk.max() + 1
    lab = watershed(-dt + 0.05 * grad, mk, mask=op)
    # merge two leaves cut from one: wide shared edge + same colour
    lab = merge_segments(lab, rgb)
    # thin parts: tips merge into the touching leaf, the rest are stems
    for k, sl in enumerate(ndi.find_objects(tl), 1):
        if sl is None: continue
        sl = (slice(max(0, sl[0].start - 3), sl[0].stop + 3), slice(max(0, sl[1].start - 3), sl[1].stop + 3))
        m = tl[sl] == k; area = m.sum() / PPM ** 2; lw = lab[sl]
        nb = np.unique(lw[ndi.binary_dilation(m, iterations=2) & (lw > 0)])
        ys, xs = np.nonzero(m); ext = max(np.ptp(xs), np.ptp(ys)) / PPM
        if len(nb) == 1 and (area < 8.0 or ext < 6.0): lw[m] = nb[0]
        elif area >= 1.5: stems[sl] |= m
    return lab, stems

def merge_segments(lab, rgb):
    """merge two segments of one leaf: shared edge >= 0.75 x the narrower one's width and colour difference dE < 9"""
    from skimage.segmentation import find_boundaries
    labf = _lab(ndi.gaussian_filter(rgb, (1, 1, 0)))
    for _ in range(3):
        n = int(lab.max())
        if n < 2: break
        idx = np.arange(1, n + 1)
        means = np.stack([ndi.mean(labf[..., c], lab, idx) for c in range(3)], -1)
        inner = (lab > 0) & ~find_boundaries(lab, mode="inner")
        wid = ndi.maximum(ndi.distance_transform_edt(inner), lab, idx) * 2 / PPM + 0.4
        a = lab[:, :-1]; b = lab[:, 1:]; c = lab[:-1, :]; d = lab[1:, :]
        h = (a != b) & (a > 0) & (b > 0); v = (c != d) & (c > 0) & (d > 0)
        pairs = np.r_[np.c_[a[h], b[h]], np.c_[c[v], d[v]]]
        if not len(pairs): break
        pairs = np.sort(pairs, 1); up, cnt = np.unique(pairs, axis=0, return_counts=True)
        parent = np.arange(n + 1)
        def root(k):
            while parent[k] != k: k = parent[k]
            return k
        changed = False
        for (i, j), nc in sorted(zip(map(tuple, up), cnt), key=lambda t: -t[1]):
            ri, rj = root(i), root(j)
            if ri == rj: continue
            edge = nc / PPM; w = min(wid[i - 1], wid[j - 1])
            dE = float(np.sqrt(((means[i - 1] - means[j - 1]) ** 2).sum()))
            if edge >= 0.75 * w and dE < 9.0 and ri == i and rj == j:      # each segment merges once per pass
                parent[j] = i; changed = True
        lab = np.array([root(k) for k in range(n + 1)])[lab]
        if not changed: break
    u = np.unique(lab[lab > 0]); m = np.zeros(lab.max() + 1, int); m[u] = np.arange(1, len(u) + 1)
    return m[lab]

def trace(P):
    rgb, E, cls, zone = base(P)
    clip = F.clip_for("M", P).buffer(-0.45)
    lilies, taken = trace_lilies(P, E, cls)
    lab, n = ndi.label(E); areas = ndi.sum(E, lab, range(1, n + 1)) / PPM ** 2
    lily_comp = set(np.unique(lab[taken & (lab > 0)]))
    is_cl = np.array([(areas[i] >= 150) or ((i + 1) in lily_comp) for i in range(n)])
    clusters = np.isin(lab, 1 + np.nonzero(is_cl)[0]); petals_m = E & ~clusters
    regs = []; info = dict(lilies=[], leaves=0, stems=0, petals=0, clusters={})
    cname = {}
    for k in 1 + np.nonzero(is_cl)[0]:
        cname[int(k)] = f"{P}_cl{len(cname)}"
    def cl_at(geom):
        p = geom.representative_point(); x, y = p.x, p.y; bb = R.BB[P]
        i, j = int((y - bb[1]) * PPM), int((x - bb[0]) * PPM)
        i = min(max(i, 0), lab.shape[0] - 1); j = min(max(j, 0), lab.shape[1] - 1)
        k = int(lab[i, j])
        if k in cname: return cname[k]
        ys, xs = np.nonzero(clusters); d = np.hypot(ys - i, xs - j); q = int(np.argmin(d)); return cname.get(int(lab[ys[q], xs[q]]))
    def C(g): return g.intersection(clip).buffer(0)
    # lilies
    for li, L_ in enumerate(lilies):
        cl = cl_at(Point(L_["c"]).buffer(1.0)); u = f"{cl}_flower{li}"
        for pi, p in enumerate(L_["petals"]):
            ks = sorted({t[0] for t in p["tones"]}, key=DARK_ORDER.get)
            for col, g in p["tones"]:
                g = C(g.buffer(-0.2 if g.area >= 8 else -0.1))
                if g.is_empty or g.area < 0.8: continue
                grp = "FL-hl" if col == "kb_white" else ("FL-base" if (col == ks[0] and len(ks) > 1) else ("FL-tip" if (col == ks[-1] and len(ks) > 1) else "FL-petal"))
                regs.append(dict(col=col, geom=g, st="tatami", ang=p["ang"], grp=grp, sub=10 + 3 * pi, unit=u, cluster=cl, kind="flower"))
        th = C(L_["throat"])
        regs.append(dict(col="kb_navy", geom=th, st="satin", ang=("radial",) + tuple(L_["c"]), grp="FL-eye", sub=70, unit=u, cluster=cl, kind="flower"))
        lines = [LineString([L_["c"], (q.centroid.x, q.centroid.y)]).buffer(0.32) for q in L_["knots"]]
        if lines:
            regs.append(dict(col="kb_sky", geom=C(unary_union(lines).intersection(th.buffer(0.6))), st="run", ang=None, grp="FL-line", sub=71, ko=False, unit=u, cluster=cl, kind="flower"))
        for q in L_["knots"]:
            regs.append(dict(col="kb_white", geom=C(q), st="satin", ang="auto", grp="FL-stamen", sub=72, unit=u, cluster=cl, kind="flower"))
        info["lilies"].append(dict(name=L_["name"], src=L_["src"], piece=P, unit=u, c=list(L_["c"]), R=round(L_["R"], 1), petals=len(L_["petals"]),
                                   tones=[p["keep"] for p in L_["petals"]], knots=len(L_["knots"])))
    # leaves + stems
    rest = clusters & ~ndi.binary_dilation(taken, structure=R.disk(0.4))
    llab, stems = segment(P, rest, rgb)
    nl = 0; XX, YY = grid_xy(P)
    for k, w_ in enumerate(ndi.find_objects(llab), 1):
        if w_ is None: continue
        w_ = (slice(max(0, w_[0].start - 6), w_[0].stop + 6), slice(max(0, w_[1].start - 6), w_[1].stop + 6))
        m = llab[w_] == k
        if m.sum() < 3 * PPM ** 2: continue
        c2, keep = clean_tones(cls[w_], m, keep_max=2, min_mm2=3.0, min_share=0.15, lum=LUM[P][w_])
        if c2 is None: continue
        x, y = XX[w_][m], YY[w_][m]
        cc = np.cov(np.stack([x - x.mean(), y - y.mean()])); w, v = np.linalg.eigh(cc); ax = v[:, 1]
        s = (x - x.mean()) * ax[0] + (y - y.mean()) * ax[1]; Lk = float(np.ptp(s))
        geoms = []
        for kk in keep:
            for q in poly_of_mask(c2 == kk, P, off=(w_[0].start, w_[1].start)):
                if q.area >= 1.0: geoms.append((FLORA_THREADS[kk], q))
        if not geoms: continue
        cl = cl_at(unary_union([g for _, g in geoms])); u = f"{cl}_leaf{nl}"; nl += 1
        dk = min(keep, key=lambda kk: kk)
        for col, g in geoms:
            g = C(g.buffer(-0.2 if g.area >= 8 else -0.1))
            if g.is_empty or g.area < 0.8: continue
            regs.append(dict(col=col, geom=g, st="satin", ang="auto", grp="LF-dk" if (FLORA_THREADS.index(col) == dk and len(keep) > 1) else "LF",
                             sub=0, unit=u, cluster=cl, kind="leaf", axis=float(math.degrees(math.atan2(ax[1], ax[0]))), L=round(Lk, 1)))
    info["leaves"] = nl
    sl_, sn = ndi.label(stems); ns = 0
    for k, w_ in enumerate(ndi.find_objects(sl_), 1):
        if w_ is None: continue
        w_ = (slice(max(0, w_[0].start - 4), w_[0].stop + 4), slice(max(0, w_[1].start - 4), w_[1].stop + 4))
        m = sl_[w_] == k; c2, keep = clean_tones(cls[w_], m, keep_max=1)
        if c2 is None: continue
        for q in poly_of_mask(m, P, smooth=0.2, off=(w_[0].start, w_[1].start)):
            q = C(q.buffer(-0.1))
            if q.is_empty or q.area < 1.5: continue
            cl = cl_at(q); u = f"{cl}_stem{ns}"; ns += 1
            regs.append(dict(col=FLORA_THREADS[keep[0]], geom=q, st="satin", ang="auto", grp="ST", sub=0, unit=u, cluster=cl, kind="stem"))
    info["stems"] = ns
    # floating petals
    pl, pn = ndi.label(petals_m); npt = 0
    for k, w_ in enumerate(ndi.find_objects(pl), 1):
        if w_ is None: continue
        w_ = (slice(max(0, w_[0].start - 4), w_[0].stop + 4), slice(max(0, w_[1].start - 4), w_[1].stop + 4))
        m = pl[w_] == k
        if m.sum() < 4.0 * PPM ** 2: continue
        c2, keep = clean_tones(cls[w_], m, keep_max=2 if m.sum() >= 15 * PPM ** 2 else 1, min_mm2=2.5, min_share=0.2, lum=LUM[P][w_], sigma_mm=0.8)
        u = f"petal_{P}{npt}"; npt += 1
        for kk in keep:
            for q in poly_of_mask(c2 == kk, P, off=(w_[0].start, w_[1].start)):
                q = C(q.buffer(-0.2 if q.area >= 8 else -0.3))
                if q.is_empty or q.area < 1.0: continue
                regs.append(dict(col=FLORA_THREADS[kk], geom=q, st="satin", ang="auto", grp="PT" if kk == min(keep) else "PT-tone",
                                 sub=0, unit=u, cluster=None, kind="petal"))
    info["petals"] = npt
    info["clusters"] = {v: int(k) for k, v in cname.items()}
    return dict(regs=regs, lilies=lilies, info=info)

if __name__ == "__main__":
    import sys, kbcore, pickle
    from PIL import Image, ImageDraw
    out = {}
    for P in (sys.argv[1:] or kbcore.PIECES):
        t = trace(P); out[P] = t
        print(P, {k: v for k, v in t["info"].items() if k != "clusters"}, "regions", len(t["regs"]))
    pickle.dump(out, open("trace/flora.pkl", "wb"))
    # overlay per piece: source | traced regions (thread colours, outlines per unit)
    import os; os.makedirs("out/trace", exist_ok=True)
    for P, t in out.items():
        bb = R.BB[P]; rgb = base(P)[0]; H, W = rgb.shape[:2]
        im = Image.new("RGB", (W, H), kbcore.FABRIC); d = ImageDraw.Draw(im)
        T = lambda cs: [((x - bb[0]) * PPM, (y - bb[1]) * PPM) for x, y in cs]
        for r in sorted(t["regs"], key=lambda r: ({"stem": 0, "leaf": 1, "flower": 2, "petal": 3}[r["kind"]], r["sub"])):
            for p in polys(r["geom"]):
                d.polygon(T(p.exterior.coords), fill=kbcore.KB_PAL[r["col"]][0], outline=(15, 18, 30))
                for h in p.interiors: d.polygon(T(h.coords), fill=kbcore.FABRIC)
        sh = Image.new("RGB", (2 * W + 10, H), "white"); sh.paste(Image.fromarray(rgb.astype(np.uint8)), (0, 0)); sh.paste(im, (W + 10, 0))
        sh.save(f"out/trace/flora_{P}.png")
