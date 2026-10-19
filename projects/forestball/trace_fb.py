"""Rev C: TRACE the embroidery from the registered close-ups (LESSONS A12), not generate it.
  BACK : close-up a (it shows the back scene), registered on back.png by a SIFT projective fit (closereg.py);
         outside its coverage, and for the placeholder pool, the back.png crop read at x4.
  02R  : close-up c, registered on front.png by SIFT + RANSAC (54 inliers, ~1 px); it also covers the zip half of 02L.
  02L  : the front.png crop read at x4 (close-up c's 02L part disagrees with the mockup), twigs as cords.
Per pixel (4 px/mm, size-M garment mm): nearest thread of the 12-thread palette in CIELAB, or FABRIC (+ sage ray streaks
-> fabric: the rays are re-sewn as a sheer overlay). Majority filter, islands < 1.5 mm² absorbed, polygons per tone.
Stitch per piece: width < 3.2 mm -> satin across the piece; else tatami along the close-up's own strand direction
(structure tensor, per 8 mm cell). Keep-outs: the art silhouette is cut 4 mm inside the keep-out and re-grown 4 mm
(round ends, no square cut), then clipped to the keep-out."""
import sys, json, math, pickle, time
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi
from skimage import measure, color
from shapely.geometry import Polygon, box, Point
from shapely.ops import unary_union
from shapely import affinity
import shapely
import fbcore
from motifs2 import HEX
import back as B, front as F

PPM = 4.0
LAST_FINE = None
GAMMA, W_L, NAVY_L = 0.6, 0.4, 10.0                             # Rev C re-tone (see classify); set per source below
TONE_BACK = (0.7, 0.5, 14.0)       # close-up a: brighter photo (fabric median #2D3A30) — picked on a render-compare of 3 settings
TONE_FRONT = (0.6, 0.4, 10.0)
HOLE_CLOSE, HOLE_MAX = 2.5, 120.0  # Rev C final (A15 gate): the dark gaps between the bank's rope strands read as bare shell;
                                   # enclosed gaps (after a 2.5 mm closing, < 120 mm², ringed by limb / moss tones) are navy crevices
C_ZIP = 55.0                          # mm from CF: inside this, 02R is traced from the mockup x4 (zip continuity)
ZIP_SHEAR_R, ZIP_SHEAR_L = 0.0, 0.0   # mm: 02R (close-up c) unsheared; 02L (mockup x4) lifted next to the zip — the mockup limb
                                      # drops across the zip gap (measured on the zip band check, emb_place.zip_check)      # close-up c: darker photo (fabric median #263429)
FABRICS_BASE = ["#38433A", "#2E3830", "#424E43", "#26302A"]     # washed shell: mid, shade, highlight, crease
FABRICS_C = ["#1D271F", "#222D24"]                               # Rev C: close-up c fabric + its shade (sampled: median #263429,
                                                                 # shade #1D271F) — without them c's dark fabric read as navy art.
                                                                 # NOT used on the back: close-up a's limb crevices are that dark
FABRICS = list(FABRICS_BASE)
NOLIFT = None                                                    # per-pixel mask: no tone lift (back stream: mid blues stay mid blue)
TONES = [k for k in fbcore.PAL]                                  # 12 threads

def lab(hexs): return color.rgb2lab(np.array([[[int(h[i:i+2], 16)/255 for i in (1, 3, 5)] for h in hexs]]))[0]

# ---------------------------------------------------------------- mm -> mockup px
def back_px(x, y):
    u = x / B.SX + 350.0                                         # warped px; invert warp_x
    px = np.where(u < 110, 110 - (110 - u) / 0.55, np.where(u > 600, 600 + (u - 600) / 0.55, u))
    return px, y / B.SY + 70.0
def front_px(x, y): return x / F.SX + F.CFX, y / F.SY + F.NECKY

def affine_from_pairs(pairs):
    """similarity fit (scale + rotation + shift): the limb pairs are nearly collinear, so a full affine is degenerate across it"""
    from skimage.transform import SimilarityTransform
    src = np.array([p[0] for p in pairs], float); dst = np.array([p[1] for p in pairs], float)
    T = SimilarityTransform(); T.estimate(src, dst)
    return T.params, np.linalg.norm(T(src) - dst, axis=1)
FIT_02R = [((100, 410), (200, 175)), ((286, 494), (235, 215)), ((478, 677), (265, 245)), ((670, 735), (300, 275)), ((870, 880), (338, 305))]
ROPE_PX = [(118, 140), (222, 140), (232, 260), (215, 420), (120, 430)]    # mockup px: hanging-moss rope zone (traced from the mockup x4)

def sample(imgpath, H_cm, mpx, mpy, scale=1.0):
    """colour of image at mockup px (mpx, mpy). H_cm: close-up px -> mockup px (None: the image IS the mockup)."""
    im = Image.open(imgpath).convert("RGB")
    if H_cm is None:
        im = im.resize((im.width*4, im.height*4), Image.LANCZOS)
        cx, cy = mpx*4 - 0.5, mpy*4 - 0.5
    else:
        Hi = np.linalg.inv(H_cm); w = Hi[2, 0]*mpx + Hi[2, 1]*mpy + Hi[2, 2]
        cx = (Hi[0, 0]*mpx + Hi[0, 1]*mpy + Hi[0, 2]) / w; cy = (Hi[1, 0]*mpx + Hi[1, 1]*mpy + Hi[1, 2]) / w
    A = np.asarray(im).astype(np.float32) / 255
    out = np.stack([ndi.map_coordinates(A[..., k], [cy, cx], order=1, mode="nearest") for k in range(3)], -1)
    valid = (cx >= 1) & (cy >= 1) & (cx < A.shape[1] - 2) & (cy < A.shape[0] - 2)
    return out, valid

def grid(bbox):
    x0, y0, x1, y1 = bbox; W, Hh = int((x1-x0)*PPM), int((y1-y0)*PPM)
    XX, YY = np.meshgrid(x0 + (np.arange(W)+0.5)/PPM, y0 + (np.arange(Hh)+0.5)/PPM)
    return XX, YY

def classify(img, art_mask):
    """Rev C final, two passes.
    1) ART vs FABRIC: plain nearest colour (unlifted Lab) over the 12 threads + the fabric colours of this source — the dark
       crevices between chain links stay art (a lifted pass turned them into fabric holes).
    2) TONE of every art pixel: the close-ups are darker than the threads (photographed, shaded stitches), so close-up pixels
       are lifted (gamma GAMMA; mockup x4 + NOLIFT stream pixels are not) and matched with lightness weighted W_L (hue +
       chroma decide): mid blues / teal / greens no longer collapse to navy. Really dark pixels (L < NAVY_L) stay navy
       crevices; sage stays reserved for the ray overlay."""
    L = color.rgb2lab(np.clip(img, 0, 1)); P = lab([HEX[k] for k in TONES] + FABRICS)
    best = np.full(L.shape[:2], np.inf); lbl = np.zeros(L.shape[:2], int)
    for i, p in enumerate(P):
        d = ((L - p) ** 2).sum(-1); w = d < best; best[w] = d[w]; lbl[w] = i
    nT = len(TONES); fab = lbl >= nT
    gam = np.full(L.shape[:2], 1.0, np.float32)
    if LAST_FINE is not None and LAST_FINE.shape == L.shape[:2]: gam[LAST_FINE] = GAMMA
    if NOLIFT is not None and NOLIFT.shape == L.shape[:2]: gam[NOLIFT] = 1.0
    Lg = color.rgb2lab(np.clip(img, 0, 1) ** gam[..., None])
    best2 = np.full(L.shape[:2], np.inf); lb2 = np.zeros(L.shape[:2], int)
    for i, p in enumerate(lab([HEX[k] for k in TONES])):
        if TONES[i] == "sage": continue
        d = W_L * (Lg[..., 0] - p[0]) ** 2 + (Lg[..., 1] - p[1]) ** 2 + (Lg[..., 2] - p[2]) ** 2
        w = d < best2; best2[w] = d[w]; lb2[w] = i
    lb2[L[..., 0] < NAVY_L] = TONES.index("navy")
    re = ~fab & (lbl != TONES.index("sage")) & (lbl != TONES.index("cream"))   # sage/cream keep pass-1 labels for the ray rules
    lbl[re] = lb2[re]
    sage = lbl == TONES.index("sage")
    lbl[sage] = nT                                                    # sage streaks = the rays: re-sewn as overlay
    cream = lbl == TONES.index("cream")
    near_art = ndi.binary_dilation(~(fab | sage | cream), iterations=int(1.5*PPM))
    lbl[cream & ~near_art] = nT                                       # cream far from art = ray core on fabric
    lbl[lbl >= nT] = nT
    # dark crevices: fabric-classed pixels enclosed by art (holes < 60 mm² after a 1.5 mm closing) are navy, not fabric
    artpx = lbl < nT
    closed = ndi.binary_closing(artpx, structure=np.ones((int(HOLE_CLOSE*PPM)*2+1,)*2, bool))
    holes = ndi.binary_fill_holes(closed) & ~closed
    hl, hn = ndi.label(holes)
    if hn:
        hs = ndi.sum(holes, hl, range(1, hn+1)) / PPM**2
        # only gaps ringed by LIMB tones are crevices; fabric between leaves stays fabric (Rev C final: the gaps inside leaf
        # clusters had become navy squares)
        limbset = [TONES.index(k) for k in ("navy", "bark", "royal", "mossdk", "moss", "brown", "mosslt", "grass", "cream", "waterlt")]
        ring = ndi.grey_dilation(hl, size=(5, 5)) * (~holes)
        rl = ring[ring > 0]; rv = np.isin(lbl[ring > 0], limbset); lv = lbl[ring > 0] == TONES.index("leaf")
        tot = np.bincount(rl, minlength=hn + 1)[1:]; lim = np.bincount(rl, weights=rv, minlength=hn + 1)[1:]
        lf = np.bincount(rl, weights=lv, minlength=hn + 1)[1:]
        keep = (hs < HOLE_MAX) & (lim >= 0.6 * np.maximum(tot, 1)) & (lf < 0.3 * np.maximum(tot, 1))
        holes = np.isin(hl, 1 + np.where(keep)[0])
    # Rev C final: only ENCLOSED gaps become navy crevices; the closing fringe round leaves / twigs (fabric within 1.5 mm
    # of art) stays fabric — it read as a dark halo round every spray.
    dark = holes & ~artpx & (L[..., 0] < 32)
    lbl[dark] = TONES.index("navy")
    lbl[~art_mask] = nT
    artpx = lbl < nT; cl, cn = ndi.label(ndi.binary_dilation(artpx, iterations=2))
    if cn:
        darkset = [TONES.index(k) for k in ("navy", "bark", "royal")]
        tot = ndi.sum(artpx, cl, range(1, cn + 1)); lit = ndi.sum(artpx & ~np.isin(lbl, darkset), cl, range(1, cn + 1))
        bad = 1 + np.where((lit < 0.12 * np.maximum(tot, 1)) | (tot / PPM**2 < 4))[0]
        lbl[np.isin(cl, bad) & artpx] = nT
        # dark pixels far (> 9 mm) from any lit art are garment shading (seams, panel edges, welt shadows), not embroidery
        litpx = (lbl < nT) & ~np.isin(lbl, darkset)
        far = ndi.distance_transform_edt(~litpx) > 9 * PPM
        lbl[far & np.isin(lbl, darkset)] = nT
    # majority filter (~1.25 mm) then absorb islands < 1.5 mm²
    oh = np.stack([ndi.uniform_filter((lbl == k).astype(np.float32), 5) for k in range(nT + 1)], -1)
    lbl = oh.argmax(-1)
    for k in range(nT):
        m = lbl == k; lab_, n = ndi.label(m)
        if not n: continue
        sz = ndi.sum(m, lab_, range(1, n+1)) / PPM**2
        small = np.isin(lab_, 1 + np.where(sz < 1.5)[0])
        if small.any():
            other = np.where(small, -1, lbl)
            idx = ndi.distance_transform_edt(other < 0, return_distances=False, return_indices=True)
            lbl = np.where(small, other[idx[0], idx[1]], lbl)
    return lbl

def polys_of(mask, bbox):
    x0, y0 = bbox[0], bbox[1]; acc = Polygon()
    for c in measure.find_contours(np.pad(mask, 1).astype(np.float32), 0.5):
        if len(c) < 6: continue
        p = Polygon([(x0 + (xx - 1 + 0.5)/PPM, y0 + (yy - 1 + 0.5)/PPM) for yy, xx in c]).buffer(0)
        if p.area > 0.3: acc = acc.symmetric_difference(p)
    return shapely.make_valid(acc).buffer(0).simplify(0.12)

FAMILY = {"navy": "TB", "bark": "TB", "royal": "TB", "waterlt": "TH", "cream": "TH", "brown": "TT",
          "mossdk": "TM", "moss": "TM", "grass": "TM", "mosslt": "TM", "leaf": "TL", "sage": "TH"}
LAYER = {"TB": 5, "TM": 6, "TT": 5.5, "TL": 7, "TH": 8, "WA": 2}

def regions_from(lbl, img, bbox, clip, stream=None):
    lum = img @ np.array([0.3, 0.59, 0.11], np.float32)
    g = ndi.gaussian_filter(lum, 0.5); gx = ndi.sobel(g, 1); gy = ndi.sobel(g, 0); s = 1.2*PPM
    Jxx = ndi.gaussian_filter(gx*gx, s); Jyy = ndi.gaussian_filter(gy*gy, s); Jxy = ndi.gaussian_filter(gx*gy, s)
    x0, y0 = bbox[0], bbox[1]; Hh, W = lbl.shape
    # review item 6 ("no vertical keep-out cut"): a leaf the keep-out would cut is left out WHOLE — every leaf-tone
    # component (leaf + leaf shade, < 250 mm²) that reaches past the clip line is removed before the polygons are made
    XXg, YYg = grid(bbox); inside = shapely.contains_xy(clip.buffer(-0.3), XXg, YYg)
    lm = np.isin(lbl, [TONES.index("leaf"), TONES.index("mosslt")])
    cl_, cn_ = ndi.label(lm, structure=np.ones((3, 3), bool))
    if cn_:
        sz = ndi.sum(lm, cl_, range(1, cn_ + 1)) / PPM**2; out_ = ndi.sum(lm & ~inside, cl_, range(1, cn_ + 1))
        drop = 1 + np.where((sz < 250) & (out_ > 0))[0]
        lbl = np.where(np.isin(cl_, drop), len(TONES), lbl)
        print("   leaves at the keep-out removed whole:", len(drop), flush=True)
    art = polys_of(lbl < len(TONES), bbox)
    sil = art.intersection(clip.buffer(-4.0)).buffer(4.0, quad_segs=8).intersection(clip)      # round ends at keep-outs
    cut = clip.boundary.buffer(0.8)            # where the keep-out cut the art: drop part-leaves / part-twigs there
    regs = []
    # ---- LESSONS A13: stitch STRUCTURE from the close-up — every chain link / rope strand / moss lump / bark grain is its own
    # object: watershed of the close-up luminance (markers = local maxima >= 1.5 mm apart) inside the bark/moss/highlight
    # tones; each (segment, thread) piece -> satin ALONG its own major axis (a link sews as a loop); tone regions are the ground.
    fine = LAST_FINE if LAST_FINE is not None and LAST_FINE.shape == lbl.shape else np.zeros(lbl.shape, bool)
    STRUCT = [TONES.index(t_) for t_ in TONES if FAMILY[t_] in ("TB", "TM", "TH")]
    smask = np.isin(lbl, STRUCT)          # close-up areas and the mockup x4 (rope, 02L): its links read at ~1 px/mm
    if stream is not None:
        XXg, YYg = grid(bbox); smask &= ~shapely.contains_xy(stream, XXg, YYg)
    if smask.any():
        from skimage.segmentation import watershed
        from skimage.feature import peak_local_max
        from skimage.measure import regionprops
        gl = ndi.gaussian_filter(lum, 0.6 * PPM)
        pk = peak_local_max(gl, min_distance=int(1.5 * PPM), labels=smask.astype(int), exclude_border=False)
        mk = np.zeros(lbl.shape, np.int32); mk[pk[:, 0], pk[:, 1]] = np.arange(1, len(pk) + 1)
        seg = watershed(-gl, mk, mask=smask)
        obj = np.where(smask, seg.astype(np.int64) * 16 + lbl, 0)
        for rp in regionprops(obj.astype(np.int64)):
            if rp.area < 1.2 * PPM**2: continue
            r0, c0, r1, c1 = rp.bbox; sub = rp.image
            tone = TONES[int(rp.label % 16)]; fam = FAMILY[tone]
            for cc in measure.find_contours(np.pad(sub, 1).astype(np.float32), 0.5):
                if len(cc) < 6: continue
                q = Polygon([(x0 + (c0 + xx - 1 + 0.5)/PPM, y0 + (r0 + yy - 1 + 0.5)/PPM) for yy, xx in cc]).buffer(0).simplify(0.1)
                q = q.intersection(sil)
                for qq in SRpolys(q):
                    if qq.area < 1.0: continue
                    ang = -math.degrees(rp.orientation) + 90.0          # major axis, garment coords (y down)
                    big = rp.minor_axis_length / PPM > 7.0
                    regs.append(dict(col=tone, geom=qq, st="tatami" if big else "satin", ang=float(ang),
                                     grp=fam if big else fam + "-s", layer=LAYER[fam]))
        lbl = np.where(smask, len(TONES), lbl)             # structure objects replace those pixels in the ground pass
    for k, tone in enumerate(TONES):
        m = lbl == k
        if not m.any(): continue
        P_ = polys_of(m, bbox).intersection(sil)
        for p in SRpolys(P_):
            if p.area < 1.2: continue
            fam = FAMILY[tone]
            if fam in ("TL", "TT") and p.intersects(cut) and p.area < 400: continue
            if stream is not None and fam in ("TB", "TH") and stream.contains(p.representative_point()): fam = "WA"
            w = 2 * p.area / max(p.length, 1e-6)
            if w < 3.2:
                regs.append(dict(col=tone, geom=p, st="satin", ang="auto", grp=fam + "-s", layer=LAYER[fam])); continue
            b = p.bounds
            for gy0 in np.arange(b[1], b[3], 8.0):
                for gx0 in np.arange(b[0], b[2], 8.0):
                    q = p.intersection(box(gx0, gy0, gx0 + 8.0, gy0 + 8.0))
                    for qq in SRpolys(q):
                        if qq.area < 0.6: continue
                        c0, r0 = max(0, int((qq.bounds[0]-x0)*PPM)), max(0, int((qq.bounds[1]-y0)*PPM))
                        c1, r1 = min(W, int((qq.bounds[2]-x0)*PPM)+1), min(Hh, int((qq.bounds[3]-y0)*PPM)+1)
                        jxx, jyy, jxy = Jxx[r0:r1, c0:c1].mean(), Jyy[r0:r1, c0:c1].mean(), Jxy[r0:r1, c0:c1].mean()
                        ang = math.degrees(0.5*math.atan2(2*jxy, jxx - jyy)) + 90.0
                        regs.append(dict(col=tone, geom=qq, st="tatami", ang=float(ang), grp=fam, layer=LAYER[fam]))
    return regs, sil

def SRpolys(g):
    if g.is_empty: return []
    if g.geom_type == "Polygon": return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]

def compose(mpx_fn, sources, bbox, clip, art_hint=None):
    """sources: [(imgpath, H or None, weight-mask fn(XX,YY)->bool)] first valid wins"""
    XX, YY = grid(bbox); mpx, mpy = mpx_fn(XX, YY)
    img = np.zeros(XX.shape + (3,), np.float32); have = np.zeros(XX.shape, bool); srcmap = np.full(XX.shape, -1, np.int8)
    for si, (path, H, use) in enumerate(sources):
        im, valid = sample(path, H, mpx, mpy)
        take = valid & ~have & (use(XX, YY) if use else True)
        img[take] = im[take]; have |= take; srcmap[take] = si if H is not None else -1
    global LAST_FINE; LAST_FINE = srcmap >= 0
    inside = shapely.contains_xy(clip.buffer(6.0), XX, YY)
    return img, have & inside

CLOSEUP_BOX = (95.9, 425.9, 158.1, 449.1)                      # close-up a's drawn box, garment mm (closereg H)
# ---------------------------------------------------------------- twigs as continuous cords (LESSONS A13: cords are objects)
# The x4 mockup (and close-up c at the panel edge) reads thin twigs as dashes: per-pixel tones gave broken twig pieces.
# 1) bridge: endpoints of dark thin fragments are joined (<= 7 mm) where the line between them follows a dark ridge (sato)
# 2) 02L outside close-up c: the twig centrelines traced by hand on the mockup x6 grid (out/dbg/grid_02L_*.png), mockup px.
TWIGS_02L_PX = [
    [(490, 243), (500, 235), (512, 224), (525, 213), (540, 207), (560, 204), (580, 203), (598, 206)],
    [(480, 265), (500, 262), (520, 260), (540, 262), (560, 268), (580, 272), (600, 277)],
    [(520, 262), (523, 275), (528, 290), (537, 300), (550, 305), (563, 312), (575, 320)],
    [(588, 274), (593, 284), (598, 295)],
    [(500, 247), (512, 254), (522, 260)],
    [(500, 378), (520, 384), (540, 387), (557, 391), (572, 395), (590, 397), (603, 398)],
    [(512, 390), (530, 399), (545, 405), (560, 410), (578, 416), (592, 421)],
    [(392, 285), (410, 276), (430, 264), (450, 253), (470, 245), (490, 240)],
    [(412, 326), (425, 310), (440, 293), (455, 277), (470, 262), (485, 248), (497, 238)],
    [(445, 270), (465, 267), (480, 265)]]
# 02L main limb outline traced by hand on the x6 mockup grid (mockup px): inside it the x4 read is a broken chain of dark
# blobs (its links); no twig cord is painted over it
LIMB_02L_PX = [(380, 320), (400, 324), (420, 332), (440, 341), (460, 349), (480, 360), (500, 371), (515, 379), (527, 385),
               (527, 396), (510, 393), (490, 388), (470, 383), (450, 375), (430, 365), (410, 355), (395, 350), (380, 349)]
def twig_cords(img, lbl, extra_lines=(), bbox=None, protect=None):
    from skimage.filters import sato
    from skimage.morphology import skeletonize, disk
    from skimage.draw import line as dline
    from scipy.spatial import cKDTree
    nT = len(TONES); lum = img @ np.array([0.3, 0.59, 0.11], np.float32)
    R = sato(lum, sigmas=[1.5, 2.5, 3.5], black_ridges=True)
    L = color.rgb2lab(np.clip(img, 0, 1))[..., 0]; Lbg = ndi.gaussian_filter(L, 3 * PPM)
    artm = lbl < nT; leafm = np.isin(lbl, [TONES.index("leaf"), TONES.index("mosslt")])
    thick = ndi.binary_dilation(ndi.binary_opening(artm, structure=disk(int(2.5 * PPM))), iterations=4)
    dk = np.isin(lbl, [TONES.index(k) for k in ("navy", "brown", "bark", "royal")]) & ~thick
    frag = skeletonize(ndi.binary_dilation(dk, iterations=1))
    lab_, n = ndi.label(frag, structure=np.ones((3, 3)))
    nb = ndi.convolve(frag.astype(int), np.ones((3, 3), int), mode="constant") - frag
    ep = np.argwhere(frag & (nb <= 1)); epl = lab_[ep[:, 0], ep[:, 1]]; con = np.zeros_like(frag)
    if len(ep) > 1:
        for i, j in cKDTree(ep).query_pairs(7 * PPM):
            if epl[i] == epl[j]: continue
            rr, cc = dline(*ep[i], *ep[j])
            if leafm[rr, cc].mean() > 0.2: continue
            if R[rr, cc].mean() > 0.02 and (L[rr, cc] < Lbg[rr, cc] - 1.5).mean() > 0.6: con[rr, cc] = True
    sk = frag | con
    # only where the source is the mockup x4: close-up c reads its own twigs (and its limb) whole — there the cords had
    # painted the thinner 02L limb brown
    mock = ~LAST_FINE if (LAST_FINE is not None and LAST_FINE.shape == lbl.shape) else np.ones(lbl.shape, bool)
    mock = ndi.binary_erosion(mock, iterations=8)
    sk &= mock
    l2, n2 = ndi.label(sk, structure=np.ones((3, 3))); sz = ndi.sum(sk, l2, range(1, n2 + 1))
    sk = np.isin(l2, 1 + np.where(sz >= int(4 * PPM))[0])
    cord = ndi.binary_dilation(sk, structure=disk(2))                    # ~1.25 mm cord (>= 0.8 satin minimum)
    nodes = np.zeros_like(cord)
    if extra_lines:
        XXg, YYg = grid(bbox)
        for ln, w in extra_lines:
            cord |= shapely.contains_xy(ln.buffer(w / 2, cap_style="round"), XXg, YYg)
            for d_ in np.arange(3.0, ln.length - 2.0, 6.5):              # cream/tan nodes along the twig, as on the mockup
                q = ln.interpolate(d_); nodes |= shapely.contains_xy(Point(q.x, q.y).buffer(0.7), XXg, YYg)
    keep = np.isin(lbl, [TONES.index(k) for k in ("leaf", "mosslt", "cream")]) | thick
    if protect is not None: keep |= protect
    cord |= dk & ndi.binary_dilation(cord, iterations=3) & mock   # the dashes the cord replaces join it (no thin dark slivers left)
    out = lbl.copy(); out[cord & ~keep] = TONES.index("brown"); out[nodes & ~np.isin(lbl, [TONES.index("leaf")])] = TONES.index("cream")
    print("   twig cords: bridged", int(con.sum() / PPM), "mm, cord", int(cord.sum() / PPM**2), "mm²", flush=True)
    return out

def trace_back():
    global GAMMA, W_L, NAVY_L, FABRICS
    GAMMA, W_L, NAVY_L = TONE_BACK; FABRICS = list(FABRICS_BASE)
    t = time.time(); bbox = (-300, -20, 300, 600)
    H = np.load("inputs/closeup_BACK_H.npy")
    # Rev C: the close-up is used in the pool too (it shows the pool, its ripple rings and a placeholder box at the same place,
    # 96-158 x 426-449 mm vs ours 102-156 x 408-456): the close-up's own drawn box (frame + inside) is replaced by its
    # surroundings (nearest traced tone), our box (+1 mm) stays empty.
    img, art = compose(back_px, [("inputs/closeups/closeup_front_right_a.png", H, None), ("inputs/back.png", None, None)], bbox, B.CLIP)
    XXg, YYg = grid(bbox)
    art &= ~shapely.contains_xy(B.PH_BOX.buffer(1.0), XXg, YYg)
    global NOLIFT
    NOLIFT = shapely.contains_xy(B.STREAM.buffer(2.0), XXg, YYg)        # stream + pool: mid blue body, navy reflections
    lbl = classify(img, art); NOLIFT = None
    cbox = shapely.contains_xy(box(*CLOSEUP_BOX).buffer(2.5), XXg, YYg) & ~shapely.contains_xy(B.PH_BOX.buffer(1.0), XXg, YYg)
    if cbox.any():
        src_ok = ~cbox & ~shapely.contains_xy(B.PH_BOX.buffer(1.0), XXg, YYg) & (lbl < len(TONES))
        idx = ndi.distance_transform_edt(~src_ok, return_distances=False, return_indices=True)
        lbl = np.where(cbox, lbl[idx[0], idx[1]], lbl)
    np.save("out/art/design_lbl_back.npy", np.where(shapely.contains_xy(B.CLIP, XXg, YYg), lbl, len(TONES)).astype(np.uint8))   # fidelity_qa reference
    regs, sil = regions_from(lbl, img, bbox, B.CLIP, stream=B.STREAM.buffer(4))
    Image.fromarray((img*255).astype(np.uint8)).save("out/art/trace_src_back.png")
    print("back traced", len(regs), f"{time.time()-t:.0f}s", flush=True)
    return regs

def trace_front():
    """Rev C final: close-up c registered on front.png by SIFT + RANSAC (closereg.py '02Rc': 54 inliers, median residual
    ~1 mockup px) covers mockup x 130-505, y 122-495 = all of 02R (hanging moss, limb, sprays) and the zip-side half of
    02L, continuously across the zip. Close-up b (8 inliers, drifted) is no longer used. Outside c: the mockup x4."""
    global GAMMA, W_L, NAVY_L, FABRICS
    GAMMA, W_L, NAVY_L = TONE_FRONT; FABRICS = FABRICS_BASE + FABRICS_C
    t = time.time(); out = {}
    H = np.load("inputs/closeup_02Rc_H.npy"); res = np.array(json.load(open("inputs/closeup_reg.json"))["02Rc"]["resid_px_median"], ndmin=1)
    for piece, side in (("02R", "R"), ("02L", "L")):
        clip = F.clip_for(side); bb = clip.bounds; bbox = (bb[0]-6, bb[1]-6, bb[2]+6, bb[3]+6)
        # 02L: close-up c's right third is the image tool's extrapolation and disagrees with the mockup there (its limb
        # thins and ends ~80 mm from CF; the mockup's runs thick to ~158 mm) -> rejected for 02L (techpack-pipeline §0b);
        # 02L is traced from the mockup x4 only, twigs as cords.
        # 02R: close-up c except the 40 mm next to the zip (mockup x4 there, as 02L), so the limb meets 02L as the mockup draws it
        srcs = ([("inputs/closeups/closeup_front_right_c.png", H, lambda X, Y: X < -C_ZIP)] if piece == "02R" else []) + [("inputs/front.png", None, None)]
        # zip continuity (review: limb centres within 3 mm at x = ±15): close-up c draws the limb straight on across the zip,
        # so it drops ~19 mm over the 30 mm zip gap. A smooth vertical shear over the 70 mm next to the zip on EACH piece
        # (02R down ZIP_SHEAR, 02L up ZIP_SHEAR) closes the step; no effect beyond 85 mm from CF.
        sh = -ZIP_SHEAR_R if piece == "02R" else ZIP_SHEAR_L
        mfn = lambda X, Y, sh=sh: front_px(X, Y + sh * np.clip(1 - (np.abs(X) - 15.0) / 70.0, 0, 1))
        img, art = compose(mfn, srcs, bbox, clip)
        lbl = classify(img, art)
        extra = []
        if piece == "02L":
            from shapely.geometry import LineString as _LS
            for k_, pts in enumerate(TWIGS_02L_PX):
                gp = [((x - F.CFX) * F.SX, (y - F.NECKY) * F.SY) for x, y in pts]
                gp = [(gx, gy - ZIP_SHEAR_L * max(0.0, min(1.0, 1 - (abs(gx) - 15.0) / 70.0))) for gx, gy in gp]   # same shear as the art
                extra.append((_LS(gp), 1.8 if k_ in (5, 6) else 1.3))
            XXg, YYg = grid(bbox)
            lp = [((x - F.CFX) * F.SX, (y - F.NECKY) * F.SY) for x, y in LIMB_02L_PX]
            lp = [(gx, gy - ZIP_SHEAR_L * max(0.0, min(1.0, 1 - (abs(gx) - 15.0) / 70.0))) for gx, gy in lp]
            limb = shapely.contains_xy(Polygon(lp).buffer(0), XXg, YYg) & art
            lbl = twig_cords(img, lbl, extra, bbox, protect=limb)      # 02R: close-up c reads its twigs whole; bridging there webbed the moss
        np.save(f"out/art/design_lbl_{piece}.npy", np.where(shapely.contains_xy(clip, *grid(bbox)), lbl, len(TONES)).astype(np.uint8))   # fidelity_qa reference
        json.dump([float(v) for v in bbox], open(f"out/art/design_bbox_{piece}.json", "w"))
        regs, sil = regions_from(lbl, img, bbox, clip)
        Image.fromarray((img*255).astype(np.uint8)).save(f"out/art/trace_src_{piece}.png")
        out[piece] = regs; print(piece, "traced", len(regs), f"{time.time()-t:.0f}s", flush=True)
    return out, res

if __name__ == "__main__":
    what = sys.argv[1:] or ["back", "front"]
    if "back" in what: pickle.dump(trace_back(), open("trace_back.pkl", "wb"))
    if "front" in what:
        fr, res = trace_front(); pickle.dump(fr, open("trace_front.pkl", "wb"))
        json.dump(dict(closeup_02R="c (SIFT projective)", fit_02R_resid_px_median=[round(float(r), 2) for r in res]), open("trace_info.json", "w"))
