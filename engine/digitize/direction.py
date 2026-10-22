"""Direction (ENGINE_PLAN M2; DIGITIZING_PRINCIPLES rules 2 and 3): where every organic part's stitches point.

  F = direction.Field.from_evidence(ev, sigma_mm=2.5)    # structure tensor of the REFERENCE grain (input pixels only)
  F.at(x, y) -> (deg, coherence)                         # thread direction at a garment-mm point (axial, 0 == 180)
  F.mean(mask) -> (deg, coherence)                       # coherence-weighted mean over a part
  F.grid(geom, step=1.0) -> dict                         # the field over a part, stored in part.meta["field"] so a
                                                         # technique plugin (guided_fill) plans from the part alone
  direction.grid_angle(grid, x, y) -> deg                # read a stored grid back (bilinear on the doubled angle)
  direction.phase(geom, grid, ppm=4.0, offset_deg=0.0)   # phase field: phi whose level sets run ALONG the field,
                                                         # |grad phi| ~ 1 mm/mm, so rows at phi = k * spacing are evenly
                                                         # spaced guided-fill rows (least-squares Poisson solve)
  direction.separate(parts, sep=(15, 25))                # same-colour touching neighbours differ by >= 15 deg (rule 3)
  direction.depth_angle(t, far=0, near=90)               # far = near-horizontal, near = near-vertical (rule 3)

The field is EVIDENCE: the structure tensor reads the visible thread grain of the close-up (threads run across the
luminance gradient). It is smoothed at sigma_mm and, where the grain is weak (coherence < min_coh), blended toward a
wider tensor (fill_sigma_mm) so a part never gets a noise direction. It is never "auto" on a blob: a field-following
part carries DirSpec(mode="field", source="field") with the field's mean and any separation offset recorded in its meta
(digitize.audit re-derives both). Gate circularity: a part whose direction comes from this field is graded against the
same reference by direction_match, so its tiles are reported apart as SELF-DERIVED (gates: direction_by_source)."""
import math
import numpy as np
from scipy import ndimage as ndi


def _axial_mean(c2, s2, w=None):
    w = np.ones_like(c2) if w is None else w
    C, S = float((w * c2).sum()), float((w * s2).sum()); W = float(w.sum())
    if W <= 0: return None, 0.0
    return (math.degrees(0.5 * math.atan2(S, C))) % 180.0, math.hypot(C, S) / W


class Field:
    """Doubled-angle thread-direction field on a regular grid (garment mm, y down). c2/s2 = cos/sin of 2 x thread angle
    (unit length after fill-in), coh = structure-tensor coherence at sigma_mm (0 = no grain, 1 = one clear direction)."""

    def __init__(self, Jxx, Jyy, Jxy, bounds, ppm, sigma_mm=4.0, fill_sigma_mm=10.0, min_coh=0.25):
        self.bounds = tuple(bounds); self.ppm = float(ppm); self.sigma_mm = sigma_mm; self.min_coh = min_coh
        s, S = sigma_mm * ppm, fill_sigma_mm * ppm
        def tens(sig):
            xx, yy, xy = (ndi.gaussian_filter(np.asarray(a, float), sig) for a in (Jxx, Jyy, Jxy))
            tr = np.maximum(xx + yy, 1e-9); vx, vy = (xx - yy) / tr, 2 * xy / tr     # angle of v = 2 x gradient angle
            return -vx, -vy                                                            # thread = gradient + 90 deg
        cx, cy = tens(s); Lx, Ly = tens(S)
        coh = np.hypot(cx, cy); lc = np.maximum(np.hypot(Lx, Ly), 1e-9)
        w = np.clip(coh / max(min_coh, 1e-9), 0, 1)
        vx = w * cx / np.maximum(coh, 1e-9) + (1 - w) * Lx / lc
        vy = w * cy / np.maximum(coh, 1e-9) + (1 - w) * Ly / lc
        n = np.maximum(np.hypot(vx, vy), 1e-9)
        self.c2, self.s2, self.coh = vx / n, vy / n, coh
        self.raw = (cx, cy)                                                            # coherence-weighted, unfilled
        self.H, self.W = self.c2.shape

    @classmethod
    def from_evidence(cls, ev, **kw):
        return cls(ev.Jxx, ev.Jyy, ev.Jxy, ev.bounds, ev.ppm, **kw)

    @classmethod
    def from_grey(cls, grey, bounds, ppm, **kw):
        g = np.asarray(grey, float)
        if g.ndim == 3: g = g[..., :3] @ np.array([0.299, 0.587, 0.114])
        gy, gx = np.gradient(ndi.gaussian_filter(g, 0.6))
        return cls(gx * gx, gy * gy, gx * gy, bounds, ppm, **kw)

    def _px(self, x, y):
        return ((np.asarray(x, float) - self.bounds[0]) * self.ppm - 0.5, (np.asarray(y, float) - self.bounds[1]) * self.ppm - 0.5)

    def at(self, x, y):
        px, py = self._px(x, y); c = np.array([py, px]).reshape(2, -1)
        c2 = ndi.map_coordinates(self.c2, c, order=1, mode="nearest"); s2 = ndi.map_coordinates(self.s2, c, order=1, mode="nearest")
        coh = ndi.map_coordinates(self.coh, c, order=1, mode="nearest")
        a = (np.degrees(0.5 * np.arctan2(s2, c2)) % 180.0)
        return (float(a[0]), float(coh[0])) if np.ndim(x) == 0 else (a, coh)

    def mean(self, mask):
        """coherence-weighted axial mean of the RAW (unfilled) tensor over a mask on this field's grid -> (deg, R)"""
        if not mask.any(): raise ValueError("Field.mean: empty mask (a part with no pixels has no direction)")
        cx, cy = self.raw
        a, _ = _axial_mean(cx[mask], cy[mask])
        if a is None or (abs(cx[mask].sum()) + abs(cy[mask].sum())) < 1e-9:
            a, _ = _axial_mean(self.c2[mask], self.s2[mask])
        return a, float(np.hypot(cx[mask].mean(), cy[mask].mean()))

    def grid(self, geom, step=1.0, pad=1.5):
        """the (filled) field sampled every `step` mm over geom's bounds + pad: compact enough for part.meta"""
        x0, y0, x1, y1 = geom.bounds; x0 -= pad; y0 -= pad; x1 += pad; y1 += pad
        nx, ny = int(math.ceil((x1 - x0) / step)) + 1, int(math.ceil((y1 - y0) / step)) + 1
        X, Y = np.meshgrid(x0 + np.arange(nx) * step, y0 + np.arange(ny) * step)
        px, py = self._px(X, Y); c = np.array([py.ravel(), px.ravel()])
        c2 = ndi.map_coordinates(self.c2, c, order=1, mode="nearest").reshape(ny, nx)
        s2 = ndi.map_coordinates(self.s2, c, order=1, mode="nearest").reshape(ny, nx)
        ang = (np.degrees(0.5 * np.arctan2(s2, c2)) % 180.0)
        return dict(x0=round(x0, 3), y0=round(y0, 3), step=step, nx=nx, ny=ny, deg=np.round(ang, 1).ravel().tolist())


# ---------------------------------------------------------------- stored grids (part.meta["field"])
def grid_arrays(grid):
    a = np.radians(np.asarray(grid["deg"], float).reshape(grid["ny"], grid["nx"]))
    return np.cos(2 * a), np.sin(2 * a)


def grid_angle(grid, x, y, offset_deg=0.0, _cache=None):
    """thread direction (deg) of a stored field grid at garment-mm points x, y (+ offset), bilinear on the doubled angle"""
    c2, s2 = _cache if _cache is not None else grid_arrays(grid)
    px = (np.asarray(x, float) - grid["x0"]) / grid["step"]; py = (np.asarray(y, float) - grid["y0"]) / grid["step"]
    c = np.array([np.ravel(py), np.ravel(px)])
    C = ndi.map_coordinates(c2, c, order=1, mode="nearest"); S = ndi.map_coordinates(s2, c, order=1, mode="nearest")
    a = (np.degrees(0.5 * np.arctan2(S, C)) + offset_deg) % 180.0
    return float(a[0]) if np.ndim(x) == 0 else a.reshape(np.shape(x))


def grid_mean(grid, geom=None):
    c2, s2 = grid_arrays(grid)
    if geom is not None:
        from shapely import contains_xy
        X, Y = np.meshgrid(grid["x0"] + np.arange(grid["nx"]) * grid["step"], grid["y0"] + np.arange(grid["ny"]) * grid["step"])
        m = contains_xy(geom, X, Y)
        if m.any(): c2, s2 = c2[m], s2[m]
    return _axial_mean(np.ravel(c2), np.ravel(s2))[0]


# ---------------------------------------------------------------- phase field (guided rows, strata bands)
def raster(geom, bounds, ppm):
    from PIL import Image, ImageDraw
    x0, y0, x1, y1 = bounds; W, H = int(math.ceil((x1 - x0) * ppm)), int(math.ceil((y1 - y0) * ppm))
    im = Image.new("L", (max(W, 1), max(H, 1)), 0); d = ImageDraw.Draw(im)
    gs = [geom] if geom.geom_type == "Polygon" else [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon"]
    T = lambda cs: [((x - x0) * ppm, (y - y0) * ppm) for x, y in cs]
    for p in gs:
        d.polygon(T(p.exterior.coords), fill=255)
        for r in p.interiors: d.polygon(T(r.coords), fill=0)
    return np.asarray(im) > 127


def solve_phase(nx_, ny_, mask, h):
    """least-squares phi on mask pixels with grad phi ~ (nx_, ny_) (per pixel, mm units; h = mm per px): every pair of
    4-neighbours inside the mask gives one equation phi_j - phi_i = h * mean normal component. One gauge equation pins
    the mean. Returns phi (NaN outside the mask)."""
    from scipy import sparse
    from scipy.sparse.linalg import spsolve
    idx = -np.ones(mask.shape, np.int64); n = int(mask.sum()); idx[mask] = np.arange(n)
    rows, cols, vals, rhs = [], [], [], []; e = 0
    for dy, dx, comp in ((0, 1, nx_), (1, 0, ny_)):
        a = mask[:mask.shape[0] - dy, :mask.shape[1] - dx] & mask[dy:, dx:]
        ii = idx[:mask.shape[0] - dy, :mask.shape[1] - dx][a]; jj = idx[dy:, dx:][a]
        b = 0.5 * (comp[:mask.shape[0] - dy, :mask.shape[1] - dx][a] + comp[dy:, dx:][a]) * h
        k = np.arange(e, e + len(ii)); e += len(ii)
        rows += [k, k]; cols += [jj, ii]; vals += [np.ones(len(ii)), -np.ones(len(ii))]; rhs.append(b)
    if e == 0:
        out = np.full(mask.shape, np.nan); out[mask] = 0.0; return out
    A = sparse.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(e, n))
    b = np.concatenate(rhs)
    M = (A.T @ A + sparse.identity(n) * 1e-6).tocsc()
    phi = spsolve(M, A.T @ b)
    out = np.full(mask.shape, np.nan); out[mask] = phi - phi.mean()
    return out


def phase(geom, grid, ppm=4.0, offset_deg=0.0, pad_mm=1.0):
    """phase field over geom: rows = level sets phi = const run ALONG the (offset) field. Normals are oriented to the
    part's mean normal (a part's field turns < 90 deg from its mean; a tighter turn would need a split part).
    Returns dict(phi (H, W), bounds, ppm, mask)."""
    x0, y0, x1, y1 = geom.bounds; b = (x0 - pad_mm, y0 - pad_mm, x1 + pad_mm, y1 + pad_mm)
    mask = raster(geom.buffer(pad_mm), b, ppm)
    H, W = mask.shape
    X = b[0] + (np.arange(W) + 0.5) / ppm; Y = b[1] + (np.arange(H) + 0.5) / ppm
    XX, YY = np.meshgrid(X, Y)
    cache = grid_arrays(grid)
    th = np.radians(grid_angle(grid, XX, YY, offset_deg, _cache=cache))
    nx_, ny_ = -np.sin(th), np.cos(th)
    m0 = grid_mean(grid, geom); m0 = math.radians((m0 if m0 is not None else 0.0) + offset_deg)
    flip = (nx_ * -math.sin(m0) + ny_ * math.cos(m0)) < 0
    nx_[flip] *= -1; ny_[flip] *= -1
    phi = solve_phase(nx_, ny_, mask, 1.0 / ppm)
    return dict(phi=phi, bounds=b, ppm=ppm, mask=mask)


# ---------------------------------------------------------------- neighbour separation, depth
def axial_diff(a, b):
    d = abs((a - b) % 180.0); return min(d, 180.0 - d)


ANGLE_EPS = 1e-6      # DirSpec keeps 0.01 deg: 140.01 - 125.01 = 14.999999999999986, so "< sep" compares with this slack (G3)


NO_SINGLE_ANGLE = ("contour", "radial")     # rows follow an outline / rays from a centre: a different texture (rule 3); M3b adds radial


def separate(parts, sep=(15.0, 25.0), touch=0.3, kinds=None, field_of=None):
    """DIGITIZING_PRINCIPLES rule 3: same-colour neighbours (same thread, touching within `touch` mm) differ by >= sep[0]
    degrees or use a different texture. Parts in contour mode ARE a different texture (rows follow the outline) and are
    skipped. Greedy, biggest part first: a smaller part closer than sep[0] to an already-fixed neighbour turns to
    sep_mid = (sep[0] + sep[1]) / 2 (or sep[0]) from it, on the side nearer its own evidence angle, and never more than
    sep[1] degrees off that evidence (the direction gate's tolerance); when no such angle exists the clash is left and
    recorded (meta["sep_unresolved"]). The turn is recorded in part.meta["sep_deg"] (digitize.audit checks it).
    kinds: only parts of these kinds are turned (others still count as fixed neighbours). Returns [(id, from, to, nb)]."""
    from shapely.strtree import STRtree
    from digitize.schema import DirSpec
    if not parts: return []
    tree = STRtree([p.geom for p in parts]); order = sorted(range(len(parts)), key=lambda i: -parts[i].area)
    fixed = set(); moves = []; mid = (sep[0] + sep[1]) / 2.0
    for i in order:
        p = parts[i]
        if p.dir.mode in NO_SINGLE_ANGLE or (kinds is not None and p.kind not in kinds):
            fixed.add(i); continue
        nbs = [int(j) for j in tree.query(p.geom.buffer(touch), predicate="intersects")
               if int(j) != i and int(j) in fixed and parts[j].thread == p.thread and parts[j].dir.mode not in NO_SINGLE_ANGLE]
        clash = [j for j in nbs if axial_diff(parts[j].dir.angle, p.dir.angle) < sep[0] - ANGLE_EPS]
        if clash:
            base = p.dir.angle - p.meta.get("sep_deg", 0.0)                   # the part's own (evidence) angle
            cands = sorted({(parts[j].dir.angle + s * mid) % 180.0 for j in clash for s in (-1, 1)} |
                           {(parts[j].dir.angle + s * sep[0]) % 180.0 for j in clash for s in (-1, 1)},
                           key=lambda a: axial_diff(a, base))
            cands = [a for a in cands if axial_diff(a, base) <= sep[1]]           # never turn a part > sep[1] off its evidence
            ok = [a for a in cands if all(axial_diff(a, parts[j].dir.angle) >= sep[0] - ANGLE_EPS for j in nbs)]
            if not ok:
                p.meta["sep_unresolved"] = parts[clash[0]].id; fixed.add(i); continue
            new = ok[0]; old = p.dir.angle
            turn = ((new - old + 90.0) % 180.0) - 90.0
            p.meta["sep_deg"] = round(p.meta.get("sep_deg", 0.0) + turn, 2)
            p.dir = DirSpec(new, mode=p.dir.mode, source=p.dir.source,
                            note=(p.dir.note + "; " if p.dir.note else "") + f"turned {turn:+.1f} deg from same-colour neighbour {parts[clash[0]].id} (rule 3)")
            moves.append((p.id, old, p.dir.angle, parts[clash[0]].id))
        fixed.add(i)
    return moves


def separation_report(parts, sep=15.0, touch=0.3):
    """pairs of touching same-thread parts whose declared angles differ by < sep (contour-mode parts excluded)"""
    from shapely.strtree import STRtree
    if not parts: return dict(pairs=0, close=0, examples=[])
    tree = STRtree([p.geom for p in parts]); n = close = 0; ex = []
    for i, p in enumerate(parts):
        for j in tree.query(p.geom.buffer(touch), predicate="intersects"):
            j = int(j)
            if j <= i or parts[j].thread != p.thread or p.dir.mode in NO_SINGLE_ANGLE or parts[j].dir.mode in NO_SINGLE_ANGLE: continue
            n += 1
            if axial_diff(p.dir.angle, parts[j].dir.angle) < sep - ANGLE_EPS:
                close += 1
                if len(ex) < 10: ex.append((p.id, parts[j].id, round(axial_diff(p.dir.angle, parts[j].dir.angle), 1)))
    return dict(pairs=n, close=close, examples=ex)


def refresh_field_basis(parts):
    """after the plan's geometry is final (underlap, cut-under, specks): every field-derived part's basis is re-measured
    from its stored field grid over the geometry actually sewn (field -> meta field_mean, field-mean -> meta field_angle),
    and its angle re-set to basis + recorded band offset + separation turn. digitize.audit recomputes the same number,
    so a basis written by hand into meta no longer passes (PR #6 review). Returns the number of parts refreshed."""
    from digitize.schema import DirSpec
    n = 0
    for p in parts:
        key = {"field": "field_mean", "field-mean": "field_angle"}.get(p.dir.source)
        if key is None or not p.meta.get("field"): continue
        b = grid_mean(p.meta["field"], p.geom)
        if b is None: continue
        p.meta[key] = round(b, 2)
        p.dir = DirSpec(b + p.meta.get("band_offset_deg", 0.0) + p.meta.get("sep_deg", 0.0), mode=p.dir.mode, source=p.dir.source, note=p.dir.note)
        n += 1
    return n


def depth_angle(t, far=0.0, near=90.0):
    """rule 3: depth goes from near-horizontal (far, t = 0) to near-vertical (near, t = 1)"""
    t = min(1.0, max(0.0, float(t)))
    return far + (near - far) * t
