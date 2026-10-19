"""Rev C: TRACE the embroidery from the registered close-ups (LESSONS A12), not generate it.
  BACK : close-up a (it shows the back scene), registered on back.png by a SIFT projective fit (closereg.py);
         outside its coverage, and for the placeholder pool, the back.png crop read at x4.
  02R  : close-up b, placed on front.png by an affine fit on 4 matched features (limb top at the shoulder, limb bend,
         limb at the zip, hanging-moss tip) — b has drifted, so the mockup decides placement; within 40 mm of CF the
         mockup x4 is used so the limb meets 02L at the zip.
  02L  : no close-up — traced from the front.png crop read at x4 (no new geometry invented).
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
FABRICS = ["#38433A", "#2E3830", "#424E43", "#26302A"]          # washed shell: mid, shade, highlight, crease
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
    L = color.rgb2lab(np.clip(img, 0, 1)); P = lab([HEX[k] for k in TONES] + FABRICS)
    best = np.full(L.shape[:2], np.inf); lbl = np.zeros(L.shape[:2], int)
    for i, p in enumerate(P):
        d = ((L - p) ** 2).sum(-1); w = d < best; best[w] = d[w]; lbl[w] = i
    nT = len(TONES); fab = lbl >= nT
    sage = lbl == TONES.index("sage")
    lbl[sage] = nT                                                    # sage streaks = the rays: re-sewn as overlay
    cream = lbl == TONES.index("cream")
    near_art = ndi.binary_dilation(~(fab | sage | cream), iterations=int(1.5*PPM))
    lbl[cream & ~near_art] = nT                                       # cream far from art = ray core on fabric
    lbl[lbl >= nT] = nT
    # dark crevices: fabric-classed pixels enclosed by art (holes < 60 mm² after a 1.5 mm closing) are navy, not fabric
    artpx = lbl < nT
    closed = ndi.binary_closing(artpx, structure=np.ones((int(1.5*PPM)*2+1,)*2, bool))
    holes = ndi.binary_fill_holes(closed) & ~closed
    hl, hn = ndi.label(holes)
    if hn:
        hs = ndi.sum(holes, hl, range(1, hn+1)) / PPM**2
        holes = np.isin(hl, 1 + np.where(hs < 60)[0])
    dark = (closed | holes) & ~artpx & (L[..., 0] < 32)
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

def trace_back():
    t = time.time(); bbox = (-300, -20, 300, 600)
    H = np.load("inputs/closeup_BACK_H.npy")
    pool = B.PH_BOX.buffer(24)
    use_close = lambda X, Y: ~shapely.contains_xy(pool, X, Y)
    img, art = compose(back_px, [("inputs/closeups/closeup_front_right_a.png", H, use_close), ("inputs/back.png", None, None)], bbox, B.CLIP)
    art &= ~shapely.contains_xy(B.PH_BOX.buffer(1.0), *grid(bbox))
    lbl = classify(img, art)
    regs, sil = regions_from(lbl, img, bbox, B.CLIP, stream=B.STREAM.buffer(4))
    Image.fromarray((img*255).astype(np.uint8)).save("out/art/trace_src_back.png")
    print("back traced", len(regs), f"{time.time()-t:.0f}s", flush=True)
    return regs

def trace_front():
    t = time.time(); out = {}
    H, res = affine_from_pairs(FIT_02R); print("02R affine fit residual (mockup px)", np.round(res, 1).tolist())
    for piece, side in (("02R", "R"), ("02L", "L")):
        clip = F.clip_for(side); bb = clip.bounds; bbox = (bb[0]-6, bb[1]-6, bb[2]+6, bb[3]+6)
        if piece == "02R":
            rope = Polygon([((x - F.CFX) * F.SX, (y - F.NECKY) * F.SY) for x, y in ROPE_PX])
            far = lambda X, Y: (X < -40.0) & ~shapely.contains_xy(rope, X, Y)
            srcs = [("inputs/closeups/closeup_front_right_b.png", H, far), ("inputs/front.png", None, None)]
        else:
            srcs = [("inputs/front.png", None, None)]
        mfn = front_px
        if piece == "02L":     # zip continuity (review: centres within 3 mm at x = ±15): the mockup limb drops 6.6 mm across the
            # zip gap; a smooth vertical shear over the first 50 mm of 02L lifts it level with 02R (no effect beyond x = 65)
            ZIP_LIFT = 6.6
            mfn = lambda X, Y: front_px(X, Y + ZIP_LIFT * np.clip(1 - (X - 15.0) / 50.0, 0, 1))
        img, art = compose(mfn, srcs, bbox, clip)
        lbl = classify(img, art)
        regs, sil = regions_from(lbl, img, bbox, clip)
        Image.fromarray((img*255).astype(np.uint8)).save(f"out/art/trace_src_{piece}.png")
        out[piece] = regs; print(piece, "traced", len(regs), f"{time.time()-t:.0f}s", flush=True)
    return out, res

if __name__ == "__main__":
    what = sys.argv[1:] or ["back", "front"]
    if "back" in what: pickle.dump(trace_back(), open("trace_back.pkl", "wb"))
    if "front" in what:
        fr, res = trace_front(); pickle.dump(fr, open("trace_front.pkl", "wb"))
        json.dump(dict(fit_02R_resid_px=[round(float(r), 1) for r in res]), open("trace_info.json", "w"))
