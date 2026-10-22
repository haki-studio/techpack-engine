"""Rev C seam-band REDRAW (founder decision 21 Oct 2026, 'Do A').

Why: continuity_M_art.json showed the traced ART itself fails the wrap seams (CF zip meet 63 / tone 37, side L 58/57,
side R 70/64, underarm R 73/52, sleeve centre R 70/32, armhole front R 65/71): the front and back mockup views were drawn
independently, so the two sides of a seam show different waves and no stitch setting can join them. The founder: stop
tuning stitches; REDRAW the art in a band near every wrap seam so the waves carry across, same colour family both sides;
keep everything outside the band as traced; show each seam before / after. Shoulders are NOT wrap seams (W4: the front
wave ends at the shoulder seam, the back keeps its own art), so they are not redrawn here.

How (one seam at a time, both sides unrolled along the seam with the pattern's seam walk: s = the same fraction of each
side's own length = the same point when sewn, the cap / armhole ease spread evenly; d = mm from the sew line):
  1. stripe slope per side near the seam (structure tensor of the tone image 3-25 mm in, coherence-weighted, smoothed
     along the seam; no clear stripe -> 0);
  2. two candidate pictures of the JOINED band (t = -d on side A, +d on side B):  P_A = A's own art, continued across
     the seam into B by a GLIDE reflection (B(s, d) <- A(s + 2 m_A d, d): a straight stripe of slope m_A runs on straight,
     at its own angle, into B);  P_B the same from B into A;
  3. ONE cut path t = c(s) through the joined band (dynamic programming over s, image-quilting style): left of the cut
     P_A, right of it P_B. The cut may not lie within DMIN of the seam (so at the seam both sides always show the SAME
     picture), it may jump across the seam (the leader switches side) at the cost of the mismatch it cuts through, it
     prefers to run where the two pictures agree (same thread, else same colour family), avoids slicing a curl or drop,
     and prefers to stay close to the seam (change as little of the traced mockup as possible); it never goes deeper
     than the band W;
  4. the side that loses the zone between the seam and the cut gets the other side's art there, glide-mapped (stripes,
     rope, foam masses: every vertex; curls / drops (rigid units): moved whole by their centre, never sheared) with all
     its attributes (thread, stitch type, layer); its own art in the zone is removed (units by their centre); a z-order
     knockout keeps the piece a clean partition.
Every redrawn item carries gen='seam redraw <seam>' (listed on G7 / G9); D['redraw'] keeps each zone (wkb) + the map so
grainfield's close-up grain can be carried along (--grain, after grainfield.py: the sewn rows in a redrawn zone follow
the grain of the art that was continued there).
usage: ./py.sh seamredraw.py [M]          (after tonematch.py --no-recolour, before seamedge.py; keeps art_<size>_preredraw.pkl)
       ./py.sh seamredraw.py [M] --grain  (after grainfield.py: remaps grain_<size>_<P>.npz inside the zones)"""
import sys, os, json, pickle, shutil, math
import numpy as np
import shapely
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
from shapely import affinity
from shapely.validation import make_valid
from scipy import ndimage as ndi
import wavecore as WC, wrap as WR, pieces as PC

size = next((a for a in sys.argv[1:] if not a.startswith("-")), "M")
PPM = 2.0                    # px per mm of the unrolled grid
BAND = 42.0                  # the redraw never reaches deeper than keep-out + BAND mm into a piece
DMIN = 8.0                   # at least keep-out + DMIN mm of the seam band shows the SAME picture on both sides
PIVOT = 2.0                  # mm beyond the keep-out where both sides show the same point (the stitch edge band)
M_MAX = 1.2                  # |slope| cap (stripes within ~50 deg of the seam normal continue at their angle)
LAMBDA = 0.002               # per px row: prefer a cut close to the seam (keep the traced mockup)
DEL = 0.03                   # per px of art deleted (replaced by bare fabric) between the seam and the cut
EDGE = 0.35                  # cost factor of a mismatch on an outline pixel
CORNER = 10.0                # per column: a picture that the other side cannot continue at the stitch edge
SWITCH = 4.0                 # extra cost when the cut jumps across the seam (leader switches side)
# founder W4 (21 Oct 2026): the shoulders are not wrap seams - the front wave ends at the shoulder seam
# order: a seam redrawn first locks its matched band; the short right armholes go before side R so the underarm corner
# (where the sleeve's underarm keep-out leaves no room) is settled on the armhole first
WRAP_SEAMS = ["CF zip", "armhole front R", "armhole back R", "side L", "side R", "armhole front L", "armhole back L",
              "underarm L", "underarm R", "sleeve centre L", "sleeve centre R"]
OVERLAY = ("FM-loop",)       # thread drawn ON the foam (not part of the partition)
FAM = {"w1": "foam", "w2": "foam", "w3": "foam", "g1": "foam", "b0": "light", "b1": "light", "b2": "light",
       "b3": "dark", "b4": "dark", "b5": "dark"}
KEYS = ["w1", "w3", "g1", "b0", "b1", "b2", "b3", "b4", "b5"]


def band_of(sm): return 20.0 if sm["kind"] == "internal" else BAND
def dmin_of(sm): return 4.0 if sm["kind"] == "internal" else DMIN     # the sleeve centre is no seam: a short mirror only


def d0_of(sm): return {"internal": 0.0, "zip": 15.0}.get(sm["kind"], WR.GAP)


def polys(g):
    if g is None or g.is_empty: return []
    if g.geom_type == "Polygon": return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon" and not p.is_empty]


def clean(g):
    """valid (Multi)Polygon: make_valid, keep the polygon parts, dissolve (a mapped ring may self-touch or fold)"""
    if g is None or g.is_empty: return Polygon()
    if not g.is_valid: g = make_valid(g)
    ps = polys(g) if g.geom_type != "GeometryCollection" else [p for x in g.geoms for p in polys(x)]
    if not ps: return Polygon()
    u = unary_union(ps)
    return u if u.is_valid else u.buffer(0)


class Side:
    """unrolled seam side: n columns over the fraction u in [0, 1], rows = depth (mm) from the sew line"""
    def __init__(self, sm, which, n, depth):
        self.sd = WR.SeamSide(size, sm, which); self.P = self.sd.P; self.n = n
        self.u = np.linspace(0, 1, n)
        self.base = np.array([self.sd.line.interpolate(float(u), normalized=True).coords[0] for u in self.u])
        nr = np.array([self.sd.normal_in(float(u)) for u in self.u])
        k = 5; pad = np.r_[nr[:1].repeat(k, 0), nr, nr[-1:].repeat(k, 0)]
        nr = np.array([pad[i:i + 2 * k + 1].mean(0) for i in range(n)]); self.nrm = nr / np.hypot(*nr.T)[:, None]
        self.rows = int(round(depth * PPM)); self.d = (np.arange(self.rows) + 0.5) / PPM
        self.region = self.sd.region; self.L = self.sd.L

    def xy(self, f, d):
        """piece coords of (fraction f, depth d) - vectorised"""
        f = np.clip(np.asarray(f, float), 0, 1); d = np.asarray(d, float); c = f * (self.n - 1); cols = np.arange(self.n)
        bx = np.interp(c, cols, self.base[:, 0]); by = np.interp(c, cols, self.base[:, 1])
        nx = np.interp(c, cols, self.nrm[:, 0]); ny = np.interp(c, cols, self.nrm[:, 1])
        return bx + nx * d, by + ny * d

    def fd(self, X, Y):
        """(fraction, depth) of piece points: nearest column (dense) then local projection"""
        P = np.c_[np.ravel(X), np.ravel(Y)]
        if not hasattr(self, "_tree"):
            from scipy.spatial import cKDTree
            self._fine = 8; m = (self.n - 1) * self._fine + 1; uu = np.linspace(0, 1, m); c = uu * (self.n - 1); cols = np.arange(self.n)
            self._fb = np.c_[np.interp(c, cols, self.base[:, 0]), np.interp(c, cols, self.base[:, 1])]
            self._fn = np.c_[np.interp(c, cols, self.nrm[:, 0]), np.interp(c, cols, self.nrm[:, 1])]
            self._fu = uu; self._tree = cKDTree(self._fb)
        # search the base point whose normal line passes through P: minimise the along-seam residual among k nearest
        dist, idx = self._tree.query(P, k=24)
        best_f = np.zeros(len(P)); best_d = np.zeros(len(P)); best_r = np.full(len(P), np.inf)
        for j in range(idx.shape[1]):
            i = idx[:, j]; v = P - self._fb[i]; nn = self._fn[i]
            dd = (v * nn).sum(1); res = np.abs(v[:, 0] * nn[:, 1] - v[:, 1] * nn[:, 0])
            better = res < best_r
            best_r[better] = res[better]; best_f[better] = self._fu[i][better]; best_d[better] = dd[better]
        return best_f.reshape(np.shape(X)), best_d.reshape(np.shape(X))

    def band_poly(self, d_from, d_to, f0=0.0, f1=1.0):
        u = np.linspace(f0, f1, max(2, int((f1 - f0) * (self.n - 1)) + 1))
        x0, y0 = self.xy(u, np.full(len(u), d_from)); x1, y1 = self.xy(u[::-1], np.full(len(u), d_to))
        return clean(Polygon(np.c_[np.r_[x0, x1], np.r_[y0, y1]]))


def sample(items, X, Y):
    """index of the top item (layer, then z) at every grid point, -1 = fabric; overlays (loop texture) ignored"""
    its = [i for i, r in enumerate(items) if r["grp"] not in OVERLAY]
    if not its: return np.full(X.shape, -1)
    tree = shapely.STRtree([items[i]["geom"] for i in its])
    pts = shapely.points(X.ravel(), Y.ravel())
    pi, ti = tree.query(pts, predicate="intersects")
    out = np.full(X.size, -1); best = np.full(X.size, -np.inf)
    key = np.array([items[i].get("layer", 0) * 100 + items[i]["z"] for i in its], float)
    for p, t in zip(pi, ti):
        k = key[t]
        if k > best[p]: best[p] = k; out[p] = its[t]
    return out.reshape(X.shape)


def slopes(lab_col, d0):
    """column shift per row going AWAY from the seam, of the stripes 3-25 mm inside the keep-out (structure tensor)"""
    img = np.where(lab_col >= 0, lab_col + 1, 0).astype(float)
    T = ndi.gaussian_filter(img, 1.5); gy, gx = np.gradient(T)              # gy: depth (rows), gx: along (cols)
    r0, r1 = int((d0 + 3) * PPM), int((d0 + 25) * PPM)
    sig = 10 * PPM
    Jxx = ndi.gaussian_filter1d((gx * gx)[r0:r1].sum(0), sig); Jyy = ndi.gaussian_filter1d((gy * gy)[r0:r1].sum(0), sig)
    Jxy = ndi.gaussian_filter1d((gx * gy)[r0:r1].sum(0), sig)
    tr = Jxx + Jyy; coh = np.sqrt((Jxx - Jyy) ** 2 + 4 * Jxy ** 2) / np.maximum(tr, 1e-9)
    ang = 0.5 * np.arctan2(2 * Jxy, Jxx - Jyy)                              # gradient direction (cols, rows)
    m = -np.tan(ang)                                                        # stripe: perpendicular to the gradient
    m = np.where(np.abs(np.cos(ang)) < 0.2, 0.0, m)                         # gradient along the seam: stripes run across it
    w = np.clip((coh - 0.2) / 0.4, 0, 1) * (tr > 1e-3)
    m = np.clip(m, -M_MAX, M_MAX) * w
    return ndi.gaussian_filter1d(m, 6 * PPM)


def code_of(items, idx):
    col = np.full(idx.shape, -1); unit = np.zeros(idx.shape, bool)
    ok = idx >= 0
    keys = np.array([KEYS.index(r["col"]) if r["col"] in KEYS else 0 for r in items] + [0])
    uf = np.array([bool(r.get("unit")) for r in items] + [False])
    col[ok] = keys[idx[ok]]; unit[ok] = uf[idx[ok]]
    return col, unit


FAMC = np.array([{"foam": 0, "light": 1, "dark": 2}[FAM[k]] for k in KEYS])


def mismatch(ca, cb, ua, ub):
    """0 same thread, 0.25 same family, 1 different (or art vs fabric); +0.5 where a mismatch slices a curl / drop"""
    same = ca == cb
    fam = (ca >= 0) & (cb >= 0) & (FAMC[np.clip(ca, 0, 8)] == FAMC[np.clip(cb, 0, 8)])
    c = np.where(same, 0.0, np.where(fam, 0.25, 1.0))
    return c + 0.5 * (c > 0) * (ua | ub)


def glide_cols(m, rows, n, dp):
    """source column for every (row, dest column): j + 2 m(j) (d - dp)  (dp = pivot depth: the stripe meets itself at
    the stitch edge on both sides and keeps its own angle beyond)"""
    j = np.arange(n)[None, :]; r = (np.arange(rows)[:, None] + 0.5) - dp * PPM
    return np.clip(np.round(j + 2 * m[None, :] * r), 0, n - 1).astype(int), (j + 2 * m[None, :] * r < 0) | (j + 2 * m[None, :] * r > n - 1)


def cut_path(cost, mis, R, dmin_r):
    """DP: one cut row per column through the joined band (rows 0..2R-1; row R-1 / R are the two sides of the seam).
    node cost = cost (forbidden within dmin of the seam); a jump between columns pays the mismatch it cuts through"""
    NR, n = cost.shape
    cum = np.r_[np.zeros((1, n)), np.cumsum(mis, 0)]
    side = np.where(np.arange(NR) < R, -1, 1)
    E = cost[:, 0].copy(); back = np.zeros((NR, n), np.int32)
    rr = np.arange(NR)
    for j in range(1, n):
        c = cum[:-1, j]
        vert = np.abs(c[:, None] - c[None, :])                         # [r, r'] mismatch crossed at column j
        sw = (side[:, None] != side[None, :]) * SWITCH
        T = E[None, :] + vert + sw
        k = T.argmin(1); E = T[rr, k] + cost[:, j]; back[:, j] = k
    r = int(E.argmin()); cut = np.zeros(n, int)
    for j in range(n - 1, -1, -1): cut[j] = r; r = back[r, j]
    return cut


GRP = np.array(["foam", "foam", "foam", "light", "light", "light", "dark", "dark", "dark"], object)


def seam_score(D, sm):
    """the continuity.py measure on the art, right at this seam: 1 mm columns, majority group 1-3 mm in from each
    side's art limit; meet = the other side carries art within +/-2 mm, tone = the same group within +/-4 mm"""
    d0 = d0_of(sm); n = int(round(max(WR.SeamSide(size, sm, "A").L, WR.SeamSide(size, sm, "B").L))) + 1
    labs = []
    for w in ("A", "B"):
        S = Side(sm, w, n, d0 + 3.5); dd = np.arange(d0 + 1.0, d0 + 3.01, 0.5)
        X = S.base[None, :, 0] + dd[:, None] * S.nrm[None, :, 0]; Y = S.base[None, :, 1] + dd[:, None] * S.nrm[None, :, 1]
        inside = shapely.contains_xy(S.region.buffer(0.3), X, Y)
        c, _ = code_of(D[S.P], np.where(inside, sample(D[S.P], X, Y), -1))
        g = np.where(c >= 0, GRP[np.clip(c, 0, 8)], None); col = []
        for j in range(n):
            v = [x for x in g[:, j] if x is not None]
            col.append(max(set(v), key=v.count) if len(v) * 2 > g.shape[0] else None)
        labs.append(col)
    a, b = labs
    pairs = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x is not None or y is not None]
    if not pairs: return None
    def near(l, i, v, w): seg = l[max(0, i - w):i + w + 1]; return any(x is not None for x in seg) if v == "any" else v in seg
    meet = np.mean([(x is None or near(b, i, "any", 2)) and (y is None or near(a, i, "any", 2)) for i, x, y in pairs])
    tone = np.mean([(x is None or near(b, i, x, 4)) and (y is None or near(a, i, y, 4)) for i, x, y in pairs])
    return dict(art_mm=len(pairs), meet=round(100 * float(meet)), tone=round(100 * float(tone)))


LOCK = {}


LOBE_R, NOTCH = 2.6, 2.4


def foam_lobes(tcut, t_mm, PA, PB, d0):
    """where the continued foam meets BARE fabric at the cut (runs >= 6 mm), the cut is scalloped like the mockup's own
    crest ends (lobes of radius LOBE_R every 2 LOBE_R, crowns at the cut, notches NOTCH mm closer to the seam) instead
    of a straight edge parallel to the seam (seamedge.py does the same on one-sided seam runs)"""
    n = len(tcut); out = tcut.copy(); runs = 0
    rows = np.array([np.argmin(np.abs(t_mm - t)) for t in tcut])
    j = np.arange(n)
    src = np.where(tcut > 0, PA[rows, j], PB[rows, j]); dst = np.where(tcut > 0, PB[np.minimum(rows + 1, len(t_mm) - 1), j], PA[np.maximum(rows - 1, 0), j])
    hit = (src >= 0) & (src <= 2) & (dst < 0)
    k = 0; per = 2 * LOBE_R * PPM
    while k < n:
        if not hit[k]: k += 1; continue
        k1 = k
        while k1 + 1 < n and hit[k1 + 1]: k1 += 1
        if (k1 - k + 1) / PPM >= 6.0:
            x = (np.arange(k, k1 + 1) - k) % per / per * 2 - 1                  # -1 .. 1 across one lobe
            rec = NOTCH * (1 - np.sqrt(np.clip(1 - x ** 2, 0, 1)))
            mag = np.maximum(np.abs(tcut[k:k1 + 1]) - rec, d0)
            out[k:k1 + 1] = np.sign(tcut[k:k1 + 1]) * mag; runs += 1
        k = k1 + 1
    return out, runs


def redraw_seam(D, sm, log):
    d0 = d0_of(sm); depth = d0 + band_of(sm)
    sA0 = WR.SeamSide(size, sm, "A"); n = int(round(max(sA0.L, WR.SeamSide(size, sm, "B").L) * PPM)) + 1
    A, B = Side(sm, "A", n, depth), Side(sm, "B", n, depth)
    R = A.rows
    grids = {}
    for S in (A, B):
        X = S.base[None, :, 0] + S.d[:, None] * S.nrm[None, :, 0]; Y = S.base[None, :, 1] + S.d[:, None] * S.nrm[None, :, 1]
        inside = shapely.contains_xy(PC.clip_for(size, S.P).buffer(0.3).intersection(S.region.buffer(0.3)), X, Y)   # where art may be
        idx = sample(D[S.P], X, Y); idx = np.where(inside, idx, -1)
        grids[S] = (idx, inside)
    (iA, inA), (iB, inB) = grids[A], grids[B]
    cA, uA = code_of(D[A.P], iA); cB, uB = code_of(D[B.P], iB)
    if (cA[int(d0 * PPM):] < 0).all() and (cB[int(d0 * PPM):] < 0).all():
        log.append(dict(seam=sm["name"], skipped="no art")); return
    mA, mB = slopes(cA, d0), slopes(cB, d0)
    dp = d0 + PIVOT; A.dp = B.dp = dp
    gA, offA = glide_cols(mA, R, n, dp); gB, offB = glide_cols(mB, R, n, dp)
    rows_ = np.arange(R)[:, None]
    A_on_B = np.where(offA | ~inB, -1, cA[rows_, gA]); uA_on_B = np.where(offA | ~inB, False, uA[rows_, gA])
    B_on_A = np.where(offB | ~inA, -1, cB[rows_, gB]); uB_on_A = np.where(offB | ~inA, False, uB[rows_, gB])
    # joined band: rows 0..R-1 = side A from deep (row 0 = depth R-1) to the seam; rows R..2R-1 = side B seam -> deep
    PA = np.r_[cA[::-1], A_on_B]; PAu = np.r_[uA[::-1], uA_on_B]
    PB = np.r_[B_on_A[::-1], cB]; PBu = np.r_[uB_on_A[::-1], uB]
    mis = mismatch(PA, PB, PAu, PBu)
    # a cut that runs along an outline of either picture reads as one motif ending and the next beginning, not as a
    # straight cut line: mismatch on an outline pixel costs EDGE x
    edge = np.zeros(PA.shape, bool)
    for Q in (PA, PB):
        edge[1:] |= Q[1:] != Q[:-1]; edge[:-1] |= Q[1:] != Q[:-1]
    mis = np.where(edge, mis * EDGE, mis)
    NR = 2 * R; t_mm = np.r_[-(np.arange(R)[::-1] + 0.5), np.arange(R) + 0.5] / PPM
    cost = mis + LAMBDA * np.abs(t_mm)[:, None] * PPM
    # the founder: motifs that hit a seam CONTINUE on the other panel - deleting art is dearer than continuing it
    delA = ((PB < 0) & (PA >= 0))[:R][::-1]                              # A side, seam -> deep: A's art replaced by fabric
    delB = ((PA < 0) & (PB >= 0))[R:]                                    # B side, seam -> deep
    cost[:R] += DEL * np.cumsum(delA, 0)[::-1]; cost[R:] += DEL * np.cumsum(delB, 0)
    dmin = d0 + dmin_of(sm)
    # where one side has art at the stitch edge but the other side cannot hold art there (its keep-out corner), continuing
    # that side's picture leaves a one-sided run at the seam: that choice costs CORNER per column (the other choice -
    # taking the bare picture - pays the deletion cost instead)
    rp = int(round((d0 + PIVOT) * PPM))
    badA = (cA[rp] >= 0) & ~inB[rp]; badB = (cB[rp] >= 0) & ~inA[rp]
    cost[R:, :] += CORNER * badA[None, :]; cost[:R, :] += CORNER * badB[None, :]
    cost[np.abs(t_mm) < dmin] += 1e3
    cut = cut_path(cost, mis, R, dmin)
    tcut = t_mm[cut]                                                    # > 0: B gets A's art from the seam to the cut
    tcut = ndi.median_filter(tcut, size=5, mode="nearest")
    tcut, nlobe = foam_lobes(tcut, t_mm, PA, PB, dmin)
    # zones (piece coords) and the glide maps
    info = dict(seam=sm["name"], A=A.P, B=B.P, d0=d0, band_mm=band_of(sm), dmin_mm=dmin_of(sm), cut_mm=[round(float(np.min(tcut)), 1), round(float(np.median(tcut)), 1), round(float(np.max(tcut)), 1)],
                mismatch_on_cut=round(float(np.mean(mis[cut, np.arange(n)])), 3), foam_lobe_runs=nlobe, zones={})
    snapshot = {A.P: list(D[A.P]), B.P: list(D[B.P])}
    for dst, src, sgn, msrc in ((B, A, 1, mA), (A, B, -1, mB)):
        dd = np.where(sgn * tcut > 0, np.abs(tcut), 0.0)
        if not (dd > 0).any(): continue
        zones = []
        on = dd > 0; j = 0
        while j < n:
            if not on[j]: j += 1; continue
            j1 = j
            while j1 + 1 < n and on[j1 + 1]: j1 += 1
            u = A.u[j:j1 + 1]; x0, y0 = dst.xy(u, np.full(len(u), -1.0)); x1, y1 = dst.xy(u[::-1], dd[j:j1 + 1][::-1])
            if j1 > j: zones.append(clean(Polygon(np.c_[np.r_[x0, x1], np.r_[y0, y1]])))
            j = j1 + 1
        zone = clean(unary_union(zones)).intersection(dst.region.buffer(0.01)) if zones else Polygon()
        if not zone.is_empty and LOCK.get(dst.P) is not None: zone = clean(zone.difference(LOCK[dst.P]))
        if zone.is_empty or zone.area < 2: continue
        n_in = apply_zone(D, snapshot, src, dst, zone, msrc, sm["name"])
        info["zones"][dst.P + ("" if dst.P != src.P else ("/A" if dst is A else "/B"))] = dict(area_mm2=round(zone.area), items_in=n_in,
                                                                                                  depth_max_mm=round(float(dd.max()), 1))
        D.setdefault("redraw", []).append(dict(seam=sm["name"], P=dst.P, src=src.P, zone=shapely.to_wkb(zone),
                                               m=msrc.tolist(), n=n, which_dst="B" if dst is B else "A"))
    for S in (A, B):                                     # this seam's matched band is not redrawn again by a later seam
        lk = S.band_poly(-1.0, d0 + dmin_of(sm) + 2.0).intersection(S.region.buffer(0.01))
        LOCK[S.P] = lk if LOCK.get(S.P) is None else clean(unary_union([LOCK[S.P], lk]))
    if os.environ.get("RD_DEBUG"):
        print("  DEBUG tcut tail", tcut[-24:].round(1).tolist(), "badA", badA[-24:].astype(int).tolist(), "inB", inB[rp][-24:].astype(int).tolist(), "cA", cA[rp][-24:].tolist())
        r2 = int((d0 + 2.0) * PPM)
        for S, rowsel in ((A, R - 1 - r2), (B, R + r2)):
            X = S.base[None, :, 0] + S.d[:, None] * S.nrm[None, :, 0]; Y = S.base[None, :, 1] + S.d[:, None] * S.nrm[None, :, 1]
            inside = shapely.contains_xy(S.region.buffer(0.3), X, Y)
            c2, _ = code_of(D[S.P], np.where(inside, sample(D[S.P], X, Y), -1))
            pred = np.where(rowsel < cut, PB[rowsel], PA[rowsel]) if False else np.where(t_mm[rowsel] < tcut, PA[rowsel], PB[rowsel])
            act = c2[r2]; bad = np.nonzero(pred != act)[0]
            print("  DEBUG", S.P, "pred!=actual at", len(bad), "of", n, "cols; mm:", (bad[::4] / PPM).round(0).tolist()[:40], "pred", pred[bad[::4]][:20].tolist(), "act", act[bad[::4]][:20].tolist())
    log.append(info)


def map_fn(src, dst, m, shift=None):
    """glide map src piece coords -> dst piece coords (shift: fixed fraction offset = rigid unit move)"""
    n = src.n
    def f(x, y, z=None):
        X = np.asarray(x, float); Y = np.asarray(y, float)
        fr, d = src.fd(X, Y)
        if shift is None:
            mm = np.interp(fr * (n - 1), np.arange(n), m); df = 2 * mm * (d - src.dp) * PPM / (n - 1)
        else: df = shift
        nx, ny = dst.xy(fr - df, d)
        return nx, ny
    return f


def mapped(g, fn, seg=0.6):
    if g.is_empty: return g
    g = shapely.segmentize(g, seg)
    return clean(shapely.ops.transform(fn, g))


import shapely.ops


def apply_zone(D, snap, src, dst, zone, m, name):
    """dst loses its art in the zone and gets src's art there (glide-mapped); returns items added"""
    n = src.n
    src_band = src.band_poly(-1.0, src.rows / PPM + 6.0)
    src_its = [r for r in snap[src.P] if r["geom"].intersects(src_band) and r["geom"].intersects(src.region)]
    fn = map_fn(src, dst, m)
    clip = PC.clip_for(size, dst.P).intersection(dst.region.buffer(0.01)) if dst.region is not None else PC.clip_for(size, dst.P)
    zone_b = zone.buffer(0.05)
    added = []
    # rigid units: by centre
    units = {}
    for r in src_its:
        if r.get("unit"): units.setdefault(r["unit"], []).append(r)
    rigid_done = set()
    for u, rs in units.items():
        c = unary_union([r["geom"] for r in rs]).centroid
        fr, d = src.fd(np.array([c.x]), np.array([c.y]))
        if d[0] < -0.5 or d[0] > src.rows / PPM: continue
        # a rigid motif moves with the glide AT ITS NEAREST POINT TO THE SEAM (where it meets the other side), whole
        U = unary_union([r["geom"] for r in rs]); xy = np.asarray(U.convex_hull.exterior.coords) if U.convex_hull.geom_type == "Polygon" else np.array([[c.x, c.y]])
        fv, dv = src.fd(xy[:, 0], xy[:, 1]); k = int(np.argmin(dv)); fr, d = fv[k:k + 1], np.maximum(dv[k:k + 1], src.dp)
        mm = np.interp(fr * (n - 1), np.arange(n), m); df = float(2 * mm[0] * (d[0] - src.dp) * PPM / (n - 1))
        fu = map_fn(src, dst, m, shift=df)
        gs = [(r, mapped(r["geom"], fu)) for r in rs]
        whole = unary_union([g for _, g in gs])
        if whole.is_empty or whole.intersection(zone).area < 0.7 * whole.area: continue      # sliced below like the stripes
        rigid_done.add(u)
        for r, g in gs:
            g = g.intersection(clip)
            if g.is_empty or g.area < 0.2: continue
            added.append(dict(r, geom=g, unit=f"rd:{name}:{u}", z=r["z"] + 0.001, gen=f"seam redraw {name}", mv=(0.0, 0.0),
                              ang=_ang(r, fu)))
    # everything else: vertex by vertex, clipped to the zone
    for r in src_its:
        if r.get("unit") in rigid_done: continue
        g = r["geom"].intersection(src_band)
        if g.is_empty: continue
        g = mapped(g, fn).intersection(zone_b).intersection(clip)
        if g.is_empty or g.area < 0.2: continue
        extra = dict(unit=f"rd:{name}:{r['unit']}", mv=(0.0, 0.0)) if r.get("unit") else {}
        added.append(dict(r, geom=g, z=r["z"] + 0.001, gen=f"seam redraw {name}", ang=_ang(r, fn), **extra))
    # dst: units with their centre in the zone go; other art is cut out of the zone
    keep = []
    dst_units = {}
    for r in D[dst.P]:
        if r.get("unit") and r["geom"].intersects(zone_b): dst_units.setdefault(r["unit"], []).append(r)
    gone = {u for u, rs in dst_units.items() if zone.contains(unary_union([r["geom"] for r in rs]).centroid)
            and unary_union([r["geom"] for r in rs]).intersection(zone).area >= 0.7 * unary_union([r["geom"] for r in rs]).area}
    for r in D[dst.P]:
        if r.get("unit") in gone: continue
        if r["geom"].intersects(zone_b):
            g = clean(r["geom"].difference(zone_b))
            if g.is_empty or g.area < 0.2: continue
            r = dict(r, geom=g)
        keep.append(r)
    # z-order knockout of the new art against the kept art around the zone (the piece stays a partition)
    foot = unary_union([r["geom"] for r in added if r["grp"] not in OVERLAY]) if added else Polygon()
    out = []
    for r in keep:
        if foot.is_empty or not r["geom"].intersects(foot): out.append(r); continue
        above = unary_union([a["geom"] for a in added if a["grp"] not in OVERLAY and a["z"] >= r["z"] and a["geom"].intersects(r["geom"])]) \
            if r["grp"] not in OVERLAY else foot
        g = clean(r["geom"].difference(above)) if not above.is_empty else r["geom"]
        if not g.is_empty and g.area >= 0.2: out.append(dict(r, geom=g))
    fin = []
    for a in added:                                                       # new art under kept higher art
        if a["grp"] in OVERLAY: fin.append(a); continue
        above = [r["geom"] for r in out if r["grp"] not in OVERLAY and r["z"] > a["z"] and r["geom"].intersects(a["geom"])]
        g = clean(a["geom"].difference(unary_union(above))) if above else a["geom"]
        if not g.is_empty and g.area >= 0.2: fin.append(dict(a, geom=g))
    # overlays (loop texture) only on the foam they belong to
    D[dst.P] = out + fin
    return len(fin)


def _ang(r, fn):
    a = r.get("ang")
    if not isinstance(a, (int, float)) or r["geom"].is_empty: return a
    c = r["geom"].representative_point(); t = math.radians(a)
    p0 = fn(np.array([c.x]), np.array([c.y])); p1 = fn(np.array([c.x + 1.5 * math.cos(t)]), np.array([c.y + 1.5 * math.sin(t)]))
    return (math.degrees(math.atan2(float(p1[1][0] - p0[1][0]), float(p1[0][0] - p0[0][0])))) % 180.0


def run():
    src, bak = f"art_{size}.pkl", f"art_{size}_preredraw.pkl"
    D = pickle.load(open(src, "rb"))
    if D["info"].get("seamredraw"):
        D = pickle.load(open(bak, "rb"))
    else: shutil.copy(src, bak)
    D["redraw"] = []
    seams = {sm["name"]: sm for sm in WR.seams(size)}
    log = []
    for name in WRAP_SEAMS:
        before = seam_score(D, seams[name])
        redraw_seam(D, seams[name], log); log[-1]["art_before"] = before; log[-1]["art_after"] = seam_score(D, seams[name])
        print(name, before, "->", log[-1]["art_after"], flush=True)
    log.append(dict(final={name: seam_score(D, seams[name]) for name in WRAP_SEAMS}))
    print("final", log[-1]["final"], flush=True)
    for P in WC.PIECES:
        import waveart as WA
        for r in D[P]: r["layer"] = WA.layer_of(r)
    D["marks"] = WR.match_marks({P: D[P] for P in WC.PIECES}, size)
    D["info"]["seamredraw"] = dict(band_mm=BAND, dmin_mm=DMIN, seams=WRAP_SEAMS, log=log)
    pickle.dump(D, open(src, "wb"))
    json.dump(log, open(f"seamredraw_{size}.json", "w"), indent=1)


def grain():
    """remap grain_<size>_<P>.npz inside every redrawn zone: the dest cell takes the grain of the source point it was
    continued from (angle carried through the glide map)"""
    D = pickle.load(open(f"art_{size}.pkl", "rb")); seams = {sm["name"]: sm for sm in WR.seams(size)}
    Z = {P: dict(np.load(f"grain_{size}_{P}.npz")) for P in WC.PIECES}
    src0 = {P: {k: v.copy() for k, v in Z[P].items()} for P in WC.PIECES}
    tot = {}
    for z in D.get("redraw", []):
        sm = seams[z["seam"]]; d0 = d0_of(sm); n = z["n"]
        A, B = Side(sm, "A", n, d0 + band_of(sm)), Side(sm, "B", n, d0 + band_of(sm))
        dst, src = (B, A) if z["which_dst"] == "B" else (A, B)
        A.dp = B.dp = d0 + PIVOT
        m = np.array(z["m"]); zone = shapely.from_wkb(z["zone"])
        G = Z[dst.P]; S = src0[src.P]
        x0, y0 = float(G["x0"]), float(G["y0"]); H, W = G["ang"].shape
        b = zone.bounds; j0, j1 = max(0, int(b[0] - x0)), min(W, int(b[2] - x0) + 1); i0, i1 = max(0, int(b[1] - y0)), min(H, int(b[3] - y0) + 1)
        jj, ii = np.meshgrid(np.arange(j0, j1), np.arange(i0, i1)); X = x0 + jj + 0.5; Y = y0 + ii + 0.5
        ins = shapely.contains_xy(zone, X, Y)
        if not ins.any(): continue
        X, Y, ii, jj = X[ins], Y[ins], ii[ins], jj[ins]
        fr, d = dst.fd(X, Y)
        mm = np.interp(fr * (n - 1), np.arange(n), m); df = 2 * mm * (d - src.dp) * PPM / (n - 1)
        sx, sy = src.xy(fr + df, d)                                       # dst (f, d) <- src (f + 2 m d, d)
        si = np.clip((sy - float(S["y0"])).astype(int), 0, S["ang"].shape[0] - 1); sj = np.clip((sx - float(S["x0"])).astype(int), 0, S["ang"].shape[1] - 1)
        fn = map_fn(src, dst, m)
        for key, ck in (("ang", "coh"), ("ang4", "coh4")):
            a = np.radians(S[key][si, sj]); px, py = fn(sx, sy); qx, qy = fn(sx + 1.5 * np.cos(a), sy + 1.5 * np.sin(a))
            G[key][ii, jj] = (np.degrees(np.arctan2(qy - py, qx - px)) % 180.0).astype(np.float32)
            G[ck][ii, jj] = S[ck][si, sj]
        G["w"][ii, jj] = S["w"][si, sj]
        tot[dst.P] = tot.get(dst.P, 0) + int(ins.sum())
    for P in WC.PIECES: np.savez_compressed(f"grain_{size}_{P}.npz", **Z[P])
    print("grain cells remapped", tot)


if __name__ == "__main__":
    if "--grain" in sys.argv: grain()
    else: run()
