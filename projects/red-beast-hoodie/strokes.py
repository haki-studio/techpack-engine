"""Rev B stitch-structure primitives (review Rev A items 2, 3, 4, 6, 12; LESSONS A13: trace the STITCH STRUCTURE).

  flow_field(L, mask)        stroke direction per pixel: structure tensor of the source texture (close-up / mockup) +
                             of the class mask (strand edges), so the hair flow is followed even where the source is soft
  stroke_tiles(mask, theta)  evenly spaced streamlines along the flow (Jobard-Lefer), cut to random lengths (long-and-short),
                             every mask pixel goes to its nearest streamline -> one stroke object per tile (1.5-3 mm wide)
  cords(mask, ...)           cream outlines rebuilt from their skeleton at a controlled width (2.5-3 mm cord, tapered tips;
                             lightning: 2.5 mm root -> 1.0 mm tip by geodesic distance from the tip)
  streaks(mask, ...)         slash streaks re-drawn as tapered pointed columns: per bundle the dominant direction (PCA), peaks
                             of the across-profile = one streak each, runs along it = its extent
All rasters are PPM px/mm, origin (x0, y0) mm, y down."""
import math
import numpy as np
from scipy import ndimage as ndi
from scipy.signal import find_peaks
from skimage import measure
from skimage.morphology import skeletonize
from shapely.geometry import Polygon, LineString

def disk_px(r):
    r = max(1, int(round(r))); y, x = np.ogrid[-r:r+1, -r:r+1]; return x*x + y*y <= r*r

def mask_geom(m, x0, y0, ppm, simp=0.08):
    cs = measure.find_contours(np.pad(m, 1).astype(np.float32), 0.5)
    g = Polygon()
    for c in sorted(cs, key=len, reverse=True):
        if len(c) < 4: continue
        p = Polygon([(x0 + (x - 0.5)/ppm, y0 + (y - 0.5)/ppm) for y, x in c]).buffer(0)
        if p.area < 0.02: continue
        g = g.symmetric_difference(p)
    return g.buffer(0).simplify(simp).buffer(0)

def smooth_geom(g, r=0.2, simp=0.1):
    return g.buffer(r, join_style="round").buffer(-r, join_style="round").simplify(simp).buffer(0)

# ------------------------------------------------------------------ direction field
def _tensor(I, s_grad, s_int):
    gy, gx = np.gradient(ndi.gaussian_filter(I.astype(np.float32), s_grad))
    return ndi.gaussian_filter(gx*gx, s_int), ndi.gaussian_filter(gy*gy, s_int), ndi.gaussian_filter(gx*gy, s_int)

def flow_field(L, masks, ppm, sigma_mm=2.0, w_mask=0.6):
    """theta (radians, stroke direction) from the source luminance texture + the class masks' edges.
    Each tensor is normalised by its own mean energy so neither dominates by contrast alone."""
    jt = _tensor(L, 0.15*ppm, sigma_mm*ppm)
    e = np.mean(jt[0] + jt[1]) + 1e-6
    J = [a/e for a in jt]
    for m in masks:
        jm = _tensor(m.astype(np.float32)*255, 0.5*ppm, sigma_mm*1.5*ppm)
        em = np.mean(jm[0] + jm[1]) + 1e-6
        J = [a + w_mask*b/em for a, b in zip(J, jm)]
    jxx, jyy, jxy = J
    th = 0.5*np.arctan2(2*jxy, jxx - jyy) + math.pi/2          # strokes run across the dominant gradient
    return th.astype(np.float32)

# ------------------------------------------------------------------ evenly spaced streamlines -> stroke tiles
def stroke_tiles(mask, theta, ppm, dsep=2.2, Lmin=5.0, Lmax=12.0, seed=1, max_turn=40.0, min_len=1.2):
    """returns (tile label image, list of (line pts px, angle deg)) — tile i+1 belongs to line i"""
    H, W = mask.shape; rng = np.random.default_rng(seed)
    rs, rt = dsep*ppm, 0.5*dsep*ppm
    seedblock = np.zeros_like(mask); traceblock = np.zeros_like(mask)
    ds, dt_ = disk_px(rs), disk_px(rt)
    def stamp(B, D, x, y):
        r = D.shape[0]//2; xi, yi = int(round(x)), int(round(y))
        y0, y1, x0, x1 = max(0, yi-r), min(H, yi+r+1), max(0, xi-r), min(W, xi+r+1)
        if y0 >= y1 or x0 >= x1: return
        B[y0:y1, x0:x1] |= D[y0-(yi-r):y1-(yi-r), x0-(xi-r):x1-(xi-r)]
    cosT = math.cos(math.radians(max_turn))
    def walk(x, y, d, nmax):
        pts = []; px, py = d
        for _ in range(nmax):
            xi, yi = int(round(x)), int(round(y))
            if not (0 <= xi < W and 0 <= yi < H): break
            t = theta[yi, xi]; dx, dy = math.cos(t), math.sin(t)
            if dx*px + dy*py < 0: dx, dy = -dx, -dy
            if dx*px + dy*py < cosT and pts: break
            x2, y2 = x + dx, y + dy; xi, yi = int(round(x2)), int(round(y2))
            if not (0 <= xi < W and 0 <= yi < H) or not mask[yi, xi] or traceblock[yi, xi]: break
            pts.append((x2, y2)); x, y, px, py = x2, y2, dx, dy
        return pts
    ys, xs = np.nonzero(mask)
    step = max(1, int(0.5*ppm))
    sel = (ys % step == 0) & (xs % step == 0)
    cand = np.stack([xs[sel], ys[sel]], 1); rng.shuffle(cand)
    # interior first (distance from the mask edge): strokes start in the body, not on the rim
    dist = ndi.distance_transform_edt(mask)
    cand = cand[np.argsort(-dist[cand[:, 1], cand[:, 0]] + rng.uniform(0, 2*ppm, len(cand)), kind="stable")]
    lines = []
    for x, y in cand:
        if seedblock[y, x] or traceblock[y, x]: continue
        Lp = rng.uniform(Lmin, Lmax)*ppm; f = rng.uniform(0.3, 0.7)
        t = theta[y, x]; d = (math.cos(t), math.sin(t))
        fw = walk(float(x), float(y), d, int(Lp*f)); bw = walk(float(x), float(y), (-d[0], -d[1]), int(Lp*(1-f)))
        pts = bw[::-1] + [(float(x), float(y))] + fw
        if len(pts) < max(2, min_len*ppm):
            pts = [(float(x), float(y))]
        for (px, py) in pts[::2]: stamp(seedblock, ds, px, py); stamp(traceblock, dt_, px, py)
        stamp(seedblock, ds, *pts[-1]); stamp(traceblock, dt_, *pts[-1])
        a = math.degrees(math.atan2(pts[-1][1]-pts[0][1], pts[-1][0]-pts[0][0])) if len(pts) > 2 else math.degrees(theta[y, x])
        lines.append((pts, a))
    C = np.zeros(mask.shape, np.int32)
    for i, (pts, a) in enumerate(lines, 1):
        for px, py in pts:
            xi, yi = int(round(px)), int(round(py))
            if 0 <= xi < W and 0 <= yi < H and mask[yi, xi]: C[yi, xi] = i
    if not lines: return C, lines
    _, (iy, ix) = ndi.distance_transform_edt(C == 0, return_indices=True)
    T = C[iy, ix]; T[~mask] = 0
    return T, lines

def tiles_to_polys(T, lines, x0, y0, ppm, min_area=0.4):
    out = []
    for i, sl in enumerate(ndi.find_objects(T), 1):
        if sl is None: continue
        pad = 2
        ys = slice(max(sl[0].start - pad, 0), min(sl[0].stop + pad, T.shape[0]))
        xs = slice(max(sl[1].start - pad, 0), min(sl[1].stop + pad, T.shape[1]))
        m = T[ys, xs] == i
        g = mask_geom(m, x0 + xs.start/ppm, y0 + ys.start/ppm, ppm)
        if g.is_empty: continue
        g = smooth_geom(g, 0.15, 0.08)
        for p in getattr(g, "geoms", [g]):
            if p.geom_type == "Polygon" and p.area >= min_area: out.append((p, lines[i-1][1]))
    return out

# ------------------------------------------------------------------ cords (cream outlines / lightning)
def geodesic_tip_distance(sk, ppm):
    """distance (mm) along the skeleton from each skeleton pixel to its nearest end point"""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    ys, xs = np.nonzero(sk); n = len(ys)
    if n == 0: return np.zeros(sk.shape, np.float32)
    idx = -np.ones(sk.shape, np.int64); idx[ys, xs] = np.arange(n)
    rows, cols, w = [], [], []
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        y2, x2 = ys + dy, xs + dx
        ok = (y2 >= 0) & (y2 < sk.shape[0]) & (x2 >= 0) & (x2 < sk.shape[1])
        j = np.full(n, -1); j[ok] = idx[y2[ok], x2[ok]]
        k = j >= 0; rows += list(np.nonzero(k)[0]); cols += list(j[k]); w += [math.hypot(dy, dx)]*int(k.sum())
    G = coo_matrix((w, (rows, cols)), shape=(n, n)).tocsr(); G = G + G.T
    deg = np.asarray((G > 0).sum(1)).ravel()
    ends = np.nonzero(deg == 1)[0]
    D = np.full(sk.shape, 1e3, np.float32)
    if len(ends) == 0: return D
    d = dijkstra(G, indices=ends, min_only=True)
    D[ys, xs] = np.where(np.isfinite(d), d/ppm, 1e3)
    return D

def _ends(sk):
    nb = ndi.convolve(sk.astype(np.uint8), np.ones((3, 3), np.uint8), mode="constant") - 1
    return sk & (nb == 1)

def prune(sk, k):
    """remove skeleton spurs shorter than k px (ribbon-edge noise); real branch tips are regrown along the original"""
    cur = sk.copy()
    for _ in range(k):
        e = _ends(cur)
        if not e.any(): break
        cur &= ~e
    removed = sk & ~cur
    grow = _ends(cur)
    for _ in range(k):
        g2 = ndi.binary_dilation(grow, structure=np.ones((3, 3), bool)) & removed & ~grow
        if not g2.any(): break
        grow |= g2; removed &= ~g2
        grow_front = g2
        grow = grow_front | (grow & False)
        cur |= g2
    lb, n = ndi.label(sk, structure=np.ones((3, 3)))          # short isolated pieces (dots, short ticks) stay whole
    if n:
        hit = ndi.maximum(cur, lb, index=np.arange(1, n + 1))
        cur |= np.isin(lb, 1 + np.nonzero(~hit.astype(bool))[0])
    return cur

def cords(mask, ppm, mode, wmin=1.2, wmax=3.0, root=2.5, tip=1.0, ramp=10.0, wfloor=2.0):
    """mask -> cord mask redrawn from its skeleton. mode 'outline': w = clip(traced, wmin, wmax), tapered to wmin over
    the last 6 mm; mode 'lightning': w = tip + (root - tip) * min(1, d_tip / ramp)."""
    m = ndi.binary_closing(mask, structure=disk_px(0.4*ppm)) | mask
    sk = prune(skeletonize(m), int(round((3.0 if mode == "outline" else 1.5)*ppm)))
    dt = ndi.distance_transform_edt(m)
    D = geodesic_tip_distance(sk, ppm)
    # Rev B2 (LESSONS A14): the cord width IS the traced width (2 x distance to the traced edge) - no width cap; only the
    # last few mm before a tip narrow toward the tip width the trace itself shows (blur rounds traced tips)
    wt = 2*dt/ppm
    if mode == "lightning":
        w = np.maximum(wt, tip)
        w = np.minimum(w, tip + (w - tip)*np.minimum(1.0, D/4.0))
    else:
        w = np.maximum(wt, wmin)
        w = np.minimum(w, wmin + (w - wmin)*np.minimum(1.0, D/3.0))
    out = np.zeros_like(mask)
    rq = np.round(w*ppm/2*2)/2          # radius in half px
    for r in np.unique(rq[sk]):
        sel = sk & (rq == r)
        out |= ndi.binary_dilation(sel, structure=disk_px(max(1.0, r)))
    return out, sk, w

# ------------------------------------------------------------------ slash streaks
def streak_poly(a, b, w, shape=(0.25, 0.55), tipw=0.25):
    """tapered pointed column a -> b, max width w: rises over the first shape[0], falls over the last shape[1]"""
    a, b = np.asarray(a, float), np.asarray(b, float); v = b - a; L = np.linalg.norm(v)
    if L < 1e-6: return Polygon()
    u = v/L; n = np.array([-u[1], u[0]]); k = max(8, int(L/0.5))
    ts = np.linspace(0, 1, k + 1)
    f = np.minimum(1, np.minimum(ts/shape[0], (1 - ts)/shape[1]))**0.8
    hw = np.maximum(tipw/2, w/2*f)
    c = a[None] + ts[:, None]*v[None]
    left = c + hw[:, None]*n[None]; right = c - hw[:, None]*n[None]
    return Polygon(np.r_[left, right[::-1]]).buffer(0)

def streaks(mask, crim, ppm, x0, y0, close_mm=3.0, min_len=7.0, sep=1.7, gap=5.0, wcap=2.5, wmin=1.2):
    """returns [(polygon, colour key, (a, b) mm, width)]"""
    out = []
    bl, n = ndi.label(ndi.binary_closing(mask, structure=disk_px(close_mm*ppm/2)) & ndi.binary_dilation(mask, structure=disk_px(close_mm*ppm/2)))
    for i, sl in enumerate(ndi.find_objects(bl), 1):
        if sl is None: continue
        m = (bl[sl] == i) & mask[sl]
        if m.sum() < 3*ppm*ppm: continue
        yy, xx = np.nonzero(m)
        X = np.stack([x0 + (xx + sl[1].start + 0.5)/ppm, y0 + (yy + sl[0].start + 0.5)/ppm], 1)
        isc = crim[sl][yy, xx]
        mu = X.mean(0); C = np.cov((X - mu).T); ev, evec = np.linalg.eigh(C); u = evec[:, 1]; nrm = np.array([-u[1], u[0]])
        s = (X - mu) @ u; t = (X - mu) @ nrm
        bw = 0.25; tb = np.arange(t.min() - 1, t.max() + 1 + bw, bw)
        hist, _ = np.histogram(t, tb); hs = ndi.gaussian_filter1d(hist.astype(float), 0.35/bw)
        pk, _ = find_peaks(hs, distance=max(1, int(sep/bw)), height=min_len*ppm*bw*ppm*0.5)
        tc = (tb[:-1] + tb[1:])/2
        peaks = sorted(tc[pk])
        for j, t0 in enumerate(peaks):
            lo = (peaks[j-1] + t0)/2 if j > 0 else t0 - 1.6
            hi = (peaks[j+1] + t0)/2 if j + 1 < len(peaks) else t0 + 1.6
            spc = min(t0 - lo, hi - t0)*2
            sel = (t >= lo) & (t < hi)
            if sel.sum() < 4: continue
            ss = s[sel]; order = np.argsort(ss); ss = ss[order]; tt = t[sel][order]; cc = isc[sel][order]
            cuts = np.nonzero(np.diff(ss) > gap)[0]
            for seg in np.split(np.arange(len(ss)), cuts + 1):
                if len(seg) < 4: continue
                sa, sb = ss[seg[0]], ss[seg[-1]]; Ls = sb - sa
                if Ls < min_len: continue
                # slight slope inside the band (streaks of one bundle are near-parallel, not identical)
                A_ = np.vstack([ss[seg], np.ones(len(seg))]).T; k_, c_ = np.linalg.lstsq(A_, tt[seg], rcond=None)[0]
                k_ = float(np.clip(k_, -0.08, 0.08))
                ta, tb_ = k_*sa + c_, k_*sb + c_
                width = (len(seg)/ppm**2)/Ls
                w = float(np.clip(width*1.1, wmin, min(wcap, 0.8*spc if spc > 0 else wcap)))
                a = mu + sa*u + ta*nrm; b = mu + sb*u + tb_*nrm
                col = "rb_crimson" if cc[seg].mean() > 0.5 else "rb_red"
                out.append((streak_poly(a, b, w), col, (tuple(a), tuple(b)), w))
    return out


def streak_tiles(mask, crim, ppm, x0, y0, close_mm=3.0, dsep=1.8, gap=0.2):
    """Rev B2 (A14): slash streaks keep their TRACED silhouette; inside each bundle (dominant direction by PCA) the traced
    area is cut into parallel strips dsep apart along the bundle direction (one satin column per strip = one streak),
    separated by a gap mm hairline. Returns [(polygon, colour key)]."""
    out = []
    bl, n = ndi.label(ndi.binary_closing(mask, structure=disk_px(close_mm*ppm/2)) & ndi.binary_dilation(mask, structure=disk_px(close_mm*ppm/2)))
    for i, sl in enumerate(ndi.find_objects(bl), 1):
        if sl is None: continue
        m = (bl[sl] == i) & mask[sl]
        if m.sum() < 1.0*ppm*ppm: continue
        yy, xx = np.nonzero(m)
        P = np.stack([xx, yy], 1).astype(float); P -= P.mean(0)
        ev, evec = np.linalg.eigh(np.cov(P.T)); u = evec[:, 1]
        theta = np.full(m.shape, math.atan2(u[1], u[0]), np.float32)
        Tl, lines = stroke_tiles(m, theta, ppm, dsep=dsep, Lmin=1e4, Lmax=1e4, seed=i, max_turn=89.0, min_len=0.5)
        cm = crim[sl]
        for p, a in tiles_to_polys(Tl, lines, x0 + sl[1].start/ppm, y0 + sl[0].start/ppm, ppm, min_area=0.6):
            q = p.buffer(-gap/2)
            if q.is_empty: continue
            for qq in getattr(q, "geoms", [q]):
                if qq.geom_type != "Polygon" or qq.area < 0.5: continue
                c = qq.representative_point(); cx_, cy_ = int((c.x - x0)*ppm) - sl[1].start, int((c.y - y0)*ppm) - sl[0].start
                cr = bool(cm[min(max(cy_, 0), cm.shape[0]-1), min(max(cx_, 0), cm.shape[1]-1)])
                out.append((qq, "rb_crimson" if cr else "rb_red"))
    return out
