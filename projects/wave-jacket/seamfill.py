"""Seam-true stripe continuation (Rev B, founder 19 Oct 2026: "the wave must look seamless").

Built so the two sides of a seam AGREE BY CONSTRUCTION, whatever the two render views showed there:
  1. both sides are unrolled into (s, d) grids: s = position along the seam as a fraction of each side's own length (so
     the eased cap / armhole are compared point for point as sewn), d = distance from the sew line into that piece;
  2. on the LEADER side (more stripe art on the seam), every stripe / rope line that crosses the seam is a run of one
     tone in the row 1.5 mm inside its keep-out; its direction is fitted from how the run moves over the next 20 mm;
  3. that run is continued straight across the seam into the FOLLOWER at its own angle and tone (translational
     continuation in the unfolded plane) and ends in one of three ways:
       join  - it reaches a stripe of the same tone on the follower (within 30 mm): the two become one stripe;
       taper - the follower is bare ahead: the stripe narrows to a point over 2.5 x its width (15-40 mm);
       abut  - the follower has different art ahead: the stripe runs until that art (>= 6 mm);
  4. then the same from the follower into the leader, only where the leader is bare on the seam.
Result: at every seam position with art, both sides carry the same tone (continuity_<size>.json measures it).
Curls and drops are discrete raised motifs: they are never continued; wrap.push_units moves them whole out of a
keep-out, wrap.transfer carries the part of a curl that really crosses a seam."""
import numpy as np
from scipy.ndimage import map_coordinates
from shapely.geometry import Polygon
from shapely.ops import transform
import trace as TR
import wrap as WR

PPM = 2.0          # px per mm of the unrolled grid
QW = 60.0          # band depth looked at on each side
QDMIN = 6.0        # a continuation always runs at least this far into the follower
JOIN_MAX = 30.0    # look this far ahead for a same-tone stripe to join
Z_CONT = {"WV": 1.6, "RP": 1.7}      # above the follower's own stripes (0) + rope lines (1), below the foam (2-5)

class Unroll:
    def __init__(self, side, n):
        self.side = side; self.n = n; self.u = np.linspace(0, 1, n)
        self.base = np.array([side.line.interpolate(float(u), normalized=True).coords[0] for u in self.u])
        nr = np.array([side.normal_in(float(u)) for u in self.u])
        k = 5; pad = np.r_[nr[:1].repeat(k, 0), nr, nr[-1:].repeat(k, 0)]
        nr = np.array([pad[i:i + 2 * k + 1].mean(0) for i in range(n)]); self.nrm = nr / np.hypot(*nr.T)[:, None]
        self.d = (np.arange(int(QW * PPM)) + 0.5) / PPM
    def grid(self):
        X = self.base[None, :, 0] + self.d[:, None] * self.nrm[None, :, 0]
        Y = self.base[None, :, 1] + self.d[:, None] * self.nrm[None, :, 1]
        return X, Y
    def to_piece(self, g):
        """geometry in unrolled mm (x = col / PPM, y = depth mm) -> piece coords"""
        cols = np.arange(self.n)
        def f(x, y, z=None):
            c = np.asarray(x) * PPM - 0.5; d = np.asarray(y)
            bx = np.interp(c, cols, self.base[:, 0]); by = np.interp(c, cols, self.base[:, 1])
            nx = np.interp(c, cols, self.nrm[:, 0]); ny = np.interp(c, cols, self.nrm[:, 1])
            return bx + nx * d, by + ny * d
        return transform(f, g)

def band_labels(items, un, keys):
    its = [r for r in items if r["grp"] in WR.BAND_GRPS and r["geom"].intersects(un.side.region.buffer(1.0))]
    X, Y = un.grid()
    if not its: return np.zeros(X.shape, np.int32)
    b = [min(r["geom"].bounds[0] for r in its) - 2, min(r["geom"].bounds[1] for r in its) - 2,
         max(r["geom"].bounds[2] for r in its) + 2, max(r["geom"].bounds[3] for r in its) + 2]
    lab = WR._label_raster(its, b, 4.0, keys)
    out = map_coordinates(lab, [(Y - b[1]) * 4.0, (X - b[0]) * 4.0], order=0, mode="constant", cval=0).astype(np.int32)
    # outside this side's region (other sleeve half, beyond the panel) nothing counts
    import shapely
    ok = shapely.contains_xy(un.side.region.buffer(0.3), X, Y)
    return np.where(ok, out, 0)

def seam_row(gap): return int(round((gap + 1.5) * PPM))

def runs(sc, allowed):
    out = []; c = 0; n = len(sc)
    while c < n:
        k = sc[c]
        if k and allowed[c]:
            c1 = c
            while c1 + 1 < n and sc[c1 + 1] == k and allowed[c1 + 1]: c1 += 1
            if c1 - c + 1 >= 2: out.append((c, c1, int(k)))
            c = c1 + 1
        else: c += 1
    return out

def slope_of(LS, c0, c1, k, r0, rows=int(20 * PPM)):
    """col shift per row AWAY from the seam (b) of the run's stripe, from the centroid of tone k near it per row"""
    cs, rs = [], []; lo, hi = c0, c1
    for r in range(r0, min(LS.shape[0], r0 + rows)):
        row = LS[r]; w = max(4, (hi - lo) // 2 + 6)
        a, b_ = max(0, lo - w), min(len(row), hi + w + 1)
        idx = np.nonzero(row[a:b_] == k)[0]
        if len(idx) == 0: break
        # the connected run nearest the previous one
        segs = np.split(idx, np.nonzero(np.diff(idx) > 1)[0] + 1); prev = 0.5 * (lo + hi) - a
        sg = min(segs, key=lambda s: abs(0.5 * (s[0] + s[-1]) - prev))
        lo, hi = a + sg[0], a + sg[-1]; cs.append(0.5 * (lo + hi)); rs.append(r)
    if len(rs) < 6: return None
    b, a = np.polyfit(np.array(rs, float), np.array(cs, float), 1)
    return float(b)

def continue_runs(LS, LT, gap_s, allowed):
    """continuation label image on the follower grid + per-run log"""
    nd, n = LT.shape; C = np.zeros_like(LT); r0 = seam_row(gap_s)
    genuine = LS[r0] * (LS[r0] == LS[min(nd - 1, r0 + int(3 * PPM))])
    log = {"join": 0, "taper": 0, "abut": 0, "skipped": 0}
    for c0, c1, k in runs(genuine, allowed):
        b = slope_of(LS, c0, c1, k, r0)
        if b is None or abs(b) > 3.0: log["skipped"] += 1; continue          # runs along the seam: does not cross it
        cS0 = 0.5 * (c0 + c1) + b * r0                                      # stripe centre extrapolated to the sew line
        w0 = (c1 - c0 + 1); w_mm = (w0 / PPM) / np.sqrt(1 + b * b)
        Eq = float(np.clip(2.5 * w_mm, 15.0, 40.0)) * PPM
        cen = lambda rr: cS0 - b * rr                                         # straight on into the follower
        def at(rr):
            c = int(round(cen(rr)))
            return LT[rr, c] if 0 <= c < n and rr < nd else -1
        mode, end = None, None
        for rr in range(int(QDMIN * PPM), min(nd, int(JOIN_MAX * PPM))):
            if at(rr) == k: mode, end = "join", rr; break
        if mode is None:
            ahead = [at(rr) for rr in range(int(QDMIN * PPM), min(nd, int(Eq)))]
            if all(v <= 0 for v in ahead): mode, end = "taper", int(Eq)
            else:
                first = next(i for i, v in enumerate(ahead) if v > 0); mode, end = "abut", int(QDMIN * PPM) + first
        log[mode] += 1
        for rr in range(0, min(nd, end + 1)):
            hw = 0.5 * w0 * ((1 - rr / Eq) if mode == "taper" else 1.0)
            if hw < 0.35 * PPM: break
            a, z = int(np.floor(cen(rr) - hw + 0.5)), int(np.ceil(cen(rr) + hw - 0.5))
            if z < 0 or a >= n: continue
            C[rr, max(0, a):min(n, z + 1)] = k
    return C, log

def add_continuation(art, un, C, keys, tag):
    n = 0
    for k in np.unique(C):
        if k == 0: continue
        g = TR.polys_of(C == k, PPM, (0.0, 0.0), min_px=2, simplify=0.15)
        if g.is_empty: continue
        g = un.to_piece(g).buffer(0).intersection(un.side.region)
        col = keys[k - 1]; grp = "RP" if col == "w1" else "WV"
        for p in WR.polys_of(g):
            if p.area < 0.8: continue
            st = "satin" if (grp == "RP" or (not p.interiors and 2 * p.area / max(p.length, 1e-6) < 3.0)) else "tatami"
            art[un.side.P].append(dict(col=col, geom=p, st=st, ang="auto", grp=grp, z=Z_CONT[grp], unit=None, cont=tag, layer=0)); n += 1
    return n

def fill_seam(art, size, sm, gap):
    """continuation both ways across one seam; returns a log"""
    A, B = WR.SeamSide(size, sm, "A"), WR.SeamSide(size, sm, "B")
    keys = sorted({r["col"] for P_ in art for r in art[P_] if r["grp"] in WR.BAND_GRPS})
    n = max(8, int(round(A.L * PPM)))
    uA, uB = Unroll(A, n), Unroll(B, n)
    LA, LB = band_labels(art[A.P], uA, keys), band_labels(art[B.P], uB, keys)
    r0 = seam_row(gap)
    lead_A = (LA[r0] > 0).sum() >= (LB[r0] > 0).sum()
    S, T, LS, LT, uS, uT = (A, B, LA, LB, uA, uB) if lead_A else (B, A, LB, LA, uB, uA)
    allow = np.ones(n, bool)
    C1, log1 = continue_runs(LS, LT, gap, allow)
    C2, log2 = continue_runs(LT, LS, gap, LS[r0] == 0)              # follower -> leader only where the leader is bare
    n1 = add_continuation(art, uT, C1, keys, f"{sm['name']}:{S.P}>{T.P}")
    n2 = add_continuation(art, uS, C2, keys, f"{sm['name']}:{T.P}>{S.P}")
    return dict(leader=S.P if S.P != T.P else ("A" if lead_A else "B"), lead_runs=log1, follow_runs=log2, added=[n1, n2])
