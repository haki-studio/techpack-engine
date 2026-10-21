"""Engineered jacquard sherpa: cell maps per pattern panel and size (clouds blue / cream, optional black bird).

Grid: one cell = CELL mm square (finished, PROPOSED — the mill converts to its knit gauge). Clouds and bird are traced
per cell (Rev A traced the clouds in 2 x 2 blocks; the irregular render grid then lost the checker detail).
The AI render's pixel grid is not regular, so the art is REDRAWN on our grid: one global phase per panel family,
chosen to reproduce the mockup best (cell purity), then anchored on the CF line (fronts), CB (back), sleeve centre line
(sleeves) and the hem / cuff edge (all). Cells hidden in the mockup (zip, pockets, sleeves over the body sides, the back,
the sleeve back halves) are GENERATED (reflection of the nearest traced columns / the front) and flagged per cell.

Cell codes: 0 sky blue, 1 cream, 2 black (bird, option A only), 9 outside the knit area.
Per-cell source flags: 0 traced, 1 filled across a garment detail (zip, pocket), 2 generated (not in the mockup)."""
import json, os, math
import numpy as np
from shapely.geometry import Point, Polygon, box
from shapely import affinity
from shapely.prepared import prep
import pattern as PT, fleece as FL, mockmap as MM, pixels as PX

CELL = 2.5
CLOUD = CELL                       # trace grid. Rev A traced the clouds in 2 x 2 cell blocks (5 mm): the render's checker
                                   # squares are ~5.5 mm on an IRREGULAR grid, so one global 5 mm phase lost the checker
                                   # edges and filled the cream cut-outs (PR #28 review). Re-traced per 2.5 mm cell.
MARGIN = 12.0                      # knit area = cut line + margin (mm) so the pattern runs into the seam allowance
SKY, CREAM, BLACK, OUTSIDE = 0, 1, 2, 9
TRACED, FILLED, GENERATED = 0, 1, 2
OUT = "out/jacquard"; os.makedirs(OUT, exist_ok=True)
COL = {SKY: (128, 174, 247), CREAM: (241, 234, 226), BLACK: (36, 32, 30), OUTSIDE: (210, 210, 210)}

# ---------------------------------------------------------------- tracing at M (front coords, mm)
_LAB = None
def lab():
    global _LAB
    if _LAB is None: _LAB = PX.labels()
    return _LAB

def cell_sample(x0, y0, x1, y1):
    """class fractions in a garment-mm box on the front (mockup px)"""
    px0, py0 = MM.Pinv(x0, y0); px1, py1 = MM.Pinv(x1, y1)
    return PX.frac(px0, py0, px1, py1, lab())

_SPK = None
def spark_near(x0, y0, x1, y1):
    """any sparkle / bird pixel (+3 px rim: its anti-aliased edge reads cream) in a garment-mm box -> True.
    The sparkles are embroidered ON the sky, so the knit under them is sky (Rev A left cream specks at their rims)."""
    global _SPK
    if _SPK is None:
        from scipy import ndimage as ndi
        _SPK = ndi.binary_dilation(np.isin(lab(), [PX.YELLOW, PX.GOLD, PX.BLACK]), iterations=3)
    px0, py0 = MM.Pinv(x0, y0); px1, py1 = MM.Pinv(x1, y1)
    return bool(_SPK[int(py0):int(np.ceil(py1)), int(px0):int(np.ceil(px1))].any())

VIS = None
def visible(x, y):
    global VIS
    if VIS is None: VIS = prep(MM.visible_body().buffer(-3))
    return VIS.contains(Point(*MM.Pinv(x, y)))

def front_phase(c=CLOUD):
    """global (ox, oy) shift (mm) of the cloud grid that reproduces the mockup best (band region, both fronts)"""
    best = None
    for ox in np.arange(0, c, c / 8):
        for oy in np.arange(0, c, c / 8):
            tot = n = 0
            for y in np.arange(300 + oy, 470, c):
                for x in np.arange(-280 + ox, 280, c):
                    f, v = cell_sample(x, y, x + c, y + c)
                    if v < 0.8: continue
                    tot += max(f[0], f[1]); n += 1
            s = tot / max(n, 1)
            if best is None or s > best[0]: best = (s, float(ox), float(oy))
    return best

# ---------------------------------------------------------------- checker fringe (PR #28 round 2)
CHK_S_PX = (8, 9, 10, 11, 12)  # candidate checker squares in render px (4.8-7.2 mm; measured ~6-7 mm)
CHK_T = 0.5            # normalised checker-filter response above this = checker
CHK_ERODE = 6          # px: the filter window spills ~half a square past the checker; erode, then grow back 3
CHK_WIN = 2            # local phase window: +- 2 lattice squares
CHK_Q = (3,)           # lattice square in cells = 7.5 mm: the render measures ~6-7 mm, and 33 of 38 areas chose 3 over 2 by
                       # agreement (round 2); one size for the whole garment, as in the mockup

_CHK = None
def checker_px():
    """render-px mask of the checker fringes. Each pixel's blueness (b - r, sky +1 / cream -1) is filtered with a
    windowed 2-D checker kernel (square s px, 4 quadrature phases, s in CHK_S_PX); the response is high only where
    the two colours alternate along BOTH axes (a plain cloud edge or solid area scores ~0). Labels / connected squares
    do not work here: the render's anti-aliasing joins checker squares at their corners."""
    global _CHK
    if _CHK is not None: return _CHK
    from scipy import ndimage as ndi
    from scipy.signal import fftconvolve
    a = MM.img().astype(float); L = lab()
    B = np.clip(((a[..., 2] - a[..., 0]) - 60) / 60.0, -1, 1); B[L > 1] = 0
    best = np.zeros(B.shape)
    for sq in CHK_S_PX:
        n = 3 * sq; x = np.arange(-n, n + 1); win = np.exp(-(x / (1.2 * sq)) ** 2); R2 = 0
        for fx in (np.cos, np.sin):
            for fy in (np.cos, np.sin):
                K = np.outer(win * fy(np.pi * x / sq), win * fx(np.pi * x / sq)); K -= K.mean(); K /= np.abs(K).sum()
                R2 = R2 + fftconvolve(B, K, mode="same") ** 2
        best = np.maximum(best, 2 * np.sqrt(R2))
    m = ndi.binary_erosion(best > CHK_T, iterations=CHK_ERODE)
    _CHK = ndi.binary_dilation(m, iterations=CHK_ERODE - 3)
    return _CHK

def regularise_checker(cmap, centre_px):
    """cells whose centre falls in a render checker region -> a REGULAR 2-colour lattice (square q cells, phase and
    colour order fitted per region to the traced cells; q from CHK_Q by agreement). The 2.5 mm per-cell trace of a
    ~6.5 mm checker on an irregular render grid gave scattered single cells (PR #28 round 2).
    cmap {(i, j): (code, flag)} is changed in place; returns the set of regularised cells."""
    from scipy import ndimage as ndi
    C = checker_px(); H, W = C.shape; inr = {}
    for k, v in cmap.items():
        if v is None or v[0] not in (SKY, CREAM): continue
        p = centre_px(*k)
        if p is None: continue
        px, py = int(round(p[0])), int(round(p[1]))
        if 0 <= px < W and 0 <= py < H and C[py, px]: inr[k] = v
    if not inr: return set()
    I0 = min(i for i, _ in inr); J0 = min(j for _, j in inr); I1 = max(i for i, _ in inr); J1 = max(j for _, j in inr)
    G = np.zeros((J1 - J0 + 1, I1 - I0 + 1), bool)
    for (i, j) in inr: G[j - J0, i - I0] = True
    rl, rn = ndi.label(G, structure=np.ones((3, 3)))
    done = set()
    for r in range(1, rn + 1):
        cells = [(i, j) for (i, j) in inr if rl[j - J0, i - I0] == r]
        if len(cells) < 6: continue
        best = None
        for q in CHK_Q:
            for oi in range(q):
                for oj in range(q):
                    for par in (0, 1):
                        lat = lambda i, j: SKY if ((((i + oi) // q) + ((j + oj) // q) + par) % 2 == 0) else CREAM
                        agree = sum(lat(i, j) == inr[(i, j)][0] for i, j in cells)
                        if best is None or agree > best[0]: best = (agree, q, oi, oj, par)
        _, q = best[0], best[1]
        # the render's grid drifts (irregular AI pixels): one phase per big region fits ~55 %. Each cell takes the lattice
        # phase that best fits the traced cells within +- CHK_WIN squares; phases are then smoothed (majority in the
        # same window) so a phase change happens along a lattice line, not cell by cell.
        cs = set(cells); val = {k: inr[k][0] for k in cells}; R_ = CHK_WIN * q
        phases = [(oi, oj, par) for oi in range(q) for oj in range(q) for par in (0, 1)]
        latv = lambda i, j, ph: SKY if ((((i + ph[0]) // q) + ((j + ph[1]) // q) + ph[2]) % 2 == 0) else CREAM
        loc = {}
        for (i, j) in cells:
            nb = [(a, b) for a in range(i - R_, i + R_ + 1) for b in range(j - R_, j + R_ + 1) if (a, b) in cs]
            loc[(i, j)] = max(phases, key=lambda ph: sum(latv(a, b, ph) == val[(a, b)] for a, b in nb))
        ph_of = {}
        for (i, j) in cells:
            nb = [loc[(a, b)] for a in range(i - R_, i + R_ + 1) for b in range(j - R_, j + R_ + 1) if (a, b) in cs]
            ph_of[(i, j)] = max(set(nb), key=nb.count)
        agree = 0
        for (i, j) in cells:
            v = latv(i, j, ph_of[(i, j)]); agree += v == val[(i, j)]
            cmap[(i, j)] = (v, cmap[(i, j)][1]); done.add((i, j))
        CHK_STATS.append(dict(cells=len(cells), q=q, agree=round(agree / len(cells), 3), phases=len(set(ph_of.values()))))
    return done
CHK_STATS = []

def trace_front_M(phase):
    """dict (i, j) -> (code, flag) on the cloud grid. i: column from CF (x = i*CLOUD .. +CLOUD), j: row up from the hem
    edge (y = hem - (j+1)*CLOUD .. hem - j*CLOUD); traced where visible, else None"""
    _, ox, oy = phase; g, mt = FL.draft("M"); hem = mt["hem_f"]; out = {}
    ch = mt["block"].chest2
    for j in range(0, int((hem + 30) / CLOUD) + 1):
        for i in range(-int((ch + 40) / CLOUD) - 1, int((ch + 40) / CLOUD) + 1):
            x0 = i * CLOUD; y1 = hem - j * CLOUD; y0 = y1 - CLOUD
            sx = x0 + ox - round(ox / CLOUD) * CLOUD; sy = y0 + oy - round(oy / CLOUD) * CLOUD   # phase residue shift
            cx, cy = sx + CLOUD / 2, sy + CLOUD / 2
            if not visible(cx, cy): out[(i, j)] = None; continue
            f, v = cell_sample(sx, sy, sx + CLOUD, sy + CLOUD)
            if v < 0.5: out[(i, j)] = ("detail", None); continue
            if spark_near(sx, sy, sx + CLOUD, sy + CLOUD): out[(i, j)] = (SKY, TRACED); continue   # sparkle rim -> sky
            # sparkles (embroidered on top) and the bird sit on sky: any sparkle / bird pixel in the cell -> sky
            out[(i, j)] = (SKY if (f[2] + f[3] + f[4] > 0.12 or f[0] >= f[1]) else CREAM, TRACED)
    def centre(i, j):
        x0 = i * CLOUD; y0 = hem - (j + 1) * CLOUD
        return MM.Pinv(x0 + ox - round(ox / CLOUD) * CLOUD + CLOUD / 2, y0 + oy - round(oy / CLOUD) * CLOUD + CLOUD / 2)
    regularise_checker(out, centre)
    return out

def fill_front(tr):
    """resolve detail cells (zip, pockets) by mirroring the traced cells across the detail's edge in each row
    (FILLED; 3 x 3 majority only for what is left), then hidden cells (sides under the sleeves) by reflecting the traced columns about the outermost traced
    column of their row (GENERATED). Returns {(i, j): (code, flag)}"""
    out = {k: v for k, v in tr.items() if v is not None and v[0] != "detail"}
    todo = {k for k, v in tr.items() if v is not None and v[0] == "detail"}
    # detail cells (zip, pockets): MIRROR the traced cells across the nearer edge of the detail run in that row, so the
    # cloud texture continues under the zip / pocket (Rev A grew a 3 x 3 majority inward, which smeared the rows into
    # horizontal stripes across the zip and the pockets)
    byrow = {}
    for (i, j) in todo: byrow.setdefault(j, []).append(i)
    for j, cols in byrow.items():
        cols = sorted(cols); runs = []; a = cols[0]; p = a
        for c in cols[1:] + [None]:
            if c is not None and c == p + 1: p = c; continue
            runs.append((a, p)); a = p = c
        for a, b in runs:
            for i in range(a, b + 1):
                srcs = [a - 1 - (i - a), b + 1 + (b - i)]
                if i - a > b - i: srcs = srcs[::-1]
                for q in srcs:
                    if (q, j) in out: out[(i, j)] = (out[(q, j)][0], FILLED); break
        todo -= {(i, j) for i in cols if (i, j) in out}
    while todo:
        done = {}
        for (i, j) in todo:
            nb = [out[(i + a, j + b)][0] for a in (-1, 0, 1) for b in (-1, 0, 1) if (a or b) and (i + a, j + b) in out]
            if len(nb) >= 3: done[(i, j)] = (max(set(nb), key=nb.count), FILLED)
        if not done:                                                    # isolated: nearest resolved in the row
            for (i, j) in todo:
                ks = [q for (q, jj) in out if jj == j]
                done[(i, j)] = (out[(min(ks, key=lambda q: abs(q - i)), j)][0] if ks else SKY, FILLED)
        out.update(done); todo -= set(done)
    rows = {}
    for (i, j), v in out.items(): rows.setdefault(j, {})[i] = v
    for (i, j), v in tr.items():
        if (i, j) in out: continue
        known = rows.get(j, {}); ks = sorted(known)
        if not ks: out[(i, j)] = (SKY if j * CLOUD > 330 else CREAM, GENERATED); continue
        if ks[0] < i < ks[-1]:
            k = min(ks, key=lambda q: abs(q - i)); out[(i, j)] = (known[k][0], GENERATED); continue
        edge = ks[-1] if i > ks[-1] else ks[0]
        src = min(max(2 * edge - i, ks[0]), ks[-1])
        k = min(ks, key=lambda q: abs(q - src)); out[(i, j)] = (known[k][0], GENERATED)
    return out

# ---------------------------------------------------------------- bird (option A) at CELL resolution, anchored to the neck
def bird_cells():
    """the bird traced on its own CELL grid (best phase), as {(ci, cy_from_neck): 1} in front coords; returns cells and
    the shift applied to snap it onto the jacquard grid (anchored at CF)"""
    best = None
    for ox in np.arange(0, CELL, CELL / 6):
        for oy in np.arange(0, CELL, CELL / 6):
            cells = {}; tot = n = 0
            for y in np.arange(140 + oy, 285, CELL):
                for x in np.arange(-200 + ox, -20, CELL):
                    f, v = cell_sample(x, y, x + CELL, y + CELL)
                    if v < 0.5: continue
                    p = f[2] + 0.5 * (f[3] + f[4]) * 0
                    tot += max(f[2], 1 - f[2]); n += 1
                    if f[2] >= 0.5: cells[(x, y)] = 1
            s = tot / max(n, 1)
            if best is None or s > best[0]: best = (s, ox, oy, cells)
    s, ox, oy, cells = best
    snap = {(int(round(x / CELL)), int(round(y / CELL))) for (x, y) in cells}     # column from CF, row from neck
    return snap, dict(purity=round(s, 4), ox=float(ox), oy=float(oy), shift_mm=(round(-ox + CELL * round(ox / CELL), 2), round(-oy + CELL * round(oy / CELL), 2)), n=len(snap))

# ---------------------------------------------------------------- panels per size
def knit_area(pc):
    return PT.cut_poly(pc).buffer(MARGIN, join_style="mitre")

def raster_panel(code, size, cloud_of, bird=None, bird_anchor=None):
    """cell map of one panel. cloud_of(x, y_from_hem) -> (code, flag) gives the cloud design at a cell centre
    (x in panel coords); returns dict(grid, flags, origin, cell, area)"""
    g, mt = FL.draft(size); pc = g[code]; A = knit_area(pc); Ap = prep(A)
    x0, y0, x1, y1 = A.bounds
    hem = sew_hem_y(pc)
    # anchor: columns on x = 0 (CF / CB / sleeve centre), rows on the hem / cuff edge
    i0, i1 = math.floor(x0 / CELL), math.ceil(x1 / CELL); j0, j1 = math.floor((hem - y1) / CELL), math.ceil((hem - y0) / CELL)
    W, H = i1 - i0, j1 - j0
    grid = np.full((H, W), OUTSIDE, np.uint8); flags = np.zeros((H, W), np.uint8)
    for r in range(H):
        j = j1 - 1 - r                                    # row index from the hem (0 = first row above the hem edge)
        yc = hem - (j + 0.5) * CELL
        for cidx in range(W):
            i = i0 + cidx; xc = (i + 0.5) * CELL
            if not Ap.contains(Point(xc, yc)): continue
            v, fl = cloud_of(xc, hem - yc)
            grid[r, cidx] = v; flags[r, cidx] = fl
    if bird is not None:
        for (ci, cy) in bird:                             # bird cells: column from CF, row from the CF neck seam
            xc = (ci + 0.5) * CELL; yc = bird_anchor(size) + (cy + 0.5) * CELL
            r = int(math.floor((hem - yc) / CELL)); r = j1 - 1 - r; cidx = int(math.floor(xc / CELL)) - i0
            if 0 <= r < H and 0 <= cidx < W and grid[r, cidx] != OUTSIDE: grid[r, cidx] = BLACK; flags[r, cidx] = TRACED
    return dict(grid=grid, flags=flags, i0=i0, j1=j1, hem=hem, cell=CELL, area=A, piece=pc)

def sew_hem_y(pc):
    """y of the hem / cuff edge of a panel (max y of the sew line)"""
    return max(y for _, y in pc.sew())


# ---------------------------------------------------------------- cloud design functions per panel family
def grid_fn(cmap):
    """{(i, j): (code, flag)} on the CLOUD grid -> f(x, yh) with reflection beyond the traced range (GENERATED)"""
    I = sorted({i for i, _ in cmap}); J = sorted({j for _, j in cmap}); imin, imax, jmin, jmax = I[0], I[-1], J[0], J[-1]
    def refl(k, lo, hi):
        n = hi - lo
        if n <= 0: return lo, k != lo
        p = (k - lo) % (2 * n); r = lo + (p if p <= n else 2 * n - p); return r, not (lo <= k <= hi)
    def f(x, yh):
        i, j = math.floor(x / CLOUD), math.floor(yh / CLOUD)
        ii, g1 = refl(i, imin, imax); jj, g2 = refl(j, jmin, jmax)
        if j > jmax: return SKY, GENERATED                            # above the traced rows: sky
        v = cmap.get((ii, jj))
        if v is None: return SKY, GENERATED
        return v[0], (GENERATED if (g1 or g2) else v[1])
    return f

SLV_EDGE_PX = 22         # px (~13 mm): the sleeve outline overlaps the body side by 15-20 px at the inner edge (work/r2/sl.png)

def sleeve_trace(side, size="M"):
    """{(i, j): (code, flag)} on the CLOUD grid of the sleeve (i from the sleeve centre line, j up from the cuff edge),
    sampled through mockmap.sleeve_to_img; back half = front half mirrored (GENERATED)"""
    g, mt = FL.draft(size); code = "S01" if side == "R" else "S02"; pc = g[code]; A = knit_area(pc)
    Lu = mt["Lu"]; L = lab(); x0, y0, x1, y1 = A.bounds; out = {}
    sg = 1 if side == "R" else -1
    k = np.linspace(0.12, 0.88, 4)
    # sample only inside the sleeve outline shrunk by SLV_EDGE_PX: at the outline the samples catch the body's side and
    # the fold shadow, which read sky in the cream (round 2: a column of orphan cells at the right sleeve's seam edge)
    from PIL import Image, ImageDraw
    from scipy import ndimage as ndi
    im = Image.new("L", (L.shape[1], L.shape[0]), 0)
    ImageDraw.Draw(im).polygon([tuple(p) for p in MM.sleeve_poly(side).exterior.coords], fill=1)
    inner = ndi.binary_erosion(np.array(im, bool), iterations=SLV_EDGE_PX)
    for j in range(0, int((Lu - y0) / CLOUD) + 2):
        for i in range(math.floor(x0 / CLOUD) - 1, math.ceil(x1 / CLOUD) + 1):
            xs = (i + k) * CLOUD; ys = Lu - (j + 1 - k) * CLOUD
            X, Y = np.meshgrid(xs, ys); px, py, front = MM.sleeve_to_img(side, X, Y, mt)
            h = mt["cap_h"]; t_ok = (Y >= -h) & (Y <= Lu)
            pxi = np.clip(np.round(px).astype(int), 0, L.shape[1] - 1); pyi = np.clip(np.round(py).astype(int), 0, L.shape[0] - 1)
            t_ok = t_ok & inner[pyi, pxi]                  # off the silhouette edge (body side / fold shading reads sky)
            cl = L[pyi, pxi][t_ok]
            cl = cl[cl < 5]
            if cl.size < 6: out[(i, j)] = None; continue
            sky = np.isin(cl, [0, 2, 3, 4]).sum(); cr = (cl == 1).sum()
            fl = TRACED if np.sign((i + 0.5)) == sg else GENERATED
            out[(i, j)] = (SKY if sky >= cr else CREAM, fl)
    def centre(i, j):
        px, py, _ = MM.sleeve_to_img(side, np.array([(i + 0.5) * CLOUD]), np.array([Lu - (j + 0.5) * CLOUD]), mt)
        return (float(px[0]), float(py[0])) if np.isfinite(px[0]) and np.sign(i + 0.5) == sg else None
    # the outermost traced cell of every row samples the silhouette's anti-aliased rim: drop it (it gave a 1-cell column of
    # orphan cells at the seam edge, round 2) and let the mirror fill below replace it
    byrow = {}
    for (i, j), v in out.items():
        if v is not None: byrow.setdefault(j, []).append(i)
    for j, ks in byrow.items():
        if len(ks) > 6:
            for i in (min(ks), max(ks)): out[(i, j)] = None
    regularise_checker(out, centre)
    # unresolved cells: mirrored from the traced run of the row, else by height
    rows = {}
    for (i, j), v in out.items(): rows.setdefault(j, {})[i] = v
    res = {}
    for (i, j), v in out.items():
        if v is not None: res[(i, j)] = v; continue
        known = {q: w for q, w in rows[j].items() if w is not None}
        if known:                                     # MIRROR across the traced run's edge (nearest-in-row smeared the
            ks = sorted(known)                        # edge cell into horizontal stripes, round 2)
            if i < ks[0]: src = 2 * ks[0] - i
            elif i > ks[-1]: src = 2 * ks[-1] - i
            else:                                     # a gap (e.g. both sides of the sleeve fold): mirror from the nearer side
                a_ = max(q for q in ks if q < i); b_ = min(q for q in ks if q > i)
                src = 2 * a_ - i if i - a_ <= b_ - i else 2 * b_ - i
            q = min(ks, key=lambda q: abs(q - src)); res[(i, j)] = (known[q][0], GENERATED)
        else: res[(i, j)] = (CREAM if j * CLOUD < 120 else SKY, GENERATED)
    return res

def panel_png(P, path, scale=1):
    pal = np.zeros((256, 3), np.uint8)
    for k, c in COL.items(): pal[k] = c
    from PIL import Image
    im = Image.fromarray(P["grid"], "P"); im.putpalette(pal.ravel().tolist()); im.save(path)
    if path.endswith(".png"): im.save(path[:-4] + ".bmp")
    return im

def preview(P, path, ppm=2.0, flags=True):
    """panel at ppm px/mm: cells, cut line, sew line; generated cells hatched lighter"""
    from PIL import Image, ImageDraw
    pc = P["piece"]; A = P["area"]; x0, y0, x1, y1 = A.bounds; W, H = int((x1 - x0) * ppm) + 2, int((y1 - y0) * ppm) + 2
    im = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(im)
    gH, gW = P["grid"].shape
    for r in range(gH):
        j = P["j1"] - 1 - r; yb = P["hem"] - (j + 1) * CELL
        for c in range(gW):
            v = P["grid"][r, c]
            if v == OUTSIDE: continue
            xb = (P["i0"] + c) * CELL; col = COL[v]
            if flags and P["flags"][r, c] == GENERATED: col = tuple(int(0.75 * a + 0.25 * 255) for a in col)
            d.rectangle([(xb - x0) * ppm, (yb - y0) * ppm, (xb + CELL - x0) * ppm - 1, (yb + CELL - y0) * ppm - 1], fill=col)
    T = lambda pts: [((x - x0) * ppm, (y - y0) * ppm) for x, y in pts]
    d.line(T(list(PT.cut_poly(pc).exterior.coords)), fill=(0, 0, 0), width=2)
    d.line(T(pc.sew() + [pc.sew()[0]]), fill=(90, 90, 90), width=1)
    for nm, pts in pc.internal: d.line(T(pts), fill=(200, 0, 0), width=2)
    im.save(path); return im

PANELS = [("F01", "front_L"), ("F02", "front_R"), ("B01", "back"), ("S01", "sleeve_R"), ("S02", "sleeve_L")]

def build(sizes=None, verbose=True):
    sizes = sizes or FL.SIZES
    ph = front_phase(); tr = trace_front_M(ph); fm = fill_front(tr); ffront = grid_fn(fm)
    bird, binfo = bird_cells()
    sR, sL = sleeve_trace("R"), sleeve_trace("L"); fR, fL = grid_fn(sR), grid_fn(sL)
    from collections import Counter
    n_ = sum(c["cells"] for c in CHK_STATS)
    chk = dict(regions=len(CHK_STATS), cells=n_, q=Counter(c["q"] for c in CHK_STATS for _ in range(c["cells"])).most_common(1)[0][0] if CHK_STATS else None,
               q_by_region=[c["q"] for c in CHK_STATS], agree=round(sum(c["agree"] * c["cells"] for c in CHK_STATS) / max(n_, 1), 3),
               note="checker areas from the render's 2-D checker filter, redrawn as a regular lattice (phase fitted locally); agree = share of those cells keeping their traced colour")
    stats = dict(checker=chk, cell_mm=CELL, cloud_mm=CLOUD, phase=dict(purity=round(ph[0], 4), ox=ph[1], oy=ph[2]), bird=binfo, panels={})
    json.dump({"front_M": {f"{i},{j}": v for (i, j), v in fm.items()}, "sleeve_R": {f"{i},{j}": v for (i, j), v in sR.items()},
               "sleeve_L": {f"{i},{j}": v for (i, j), v in sL.items()}, "bird": sorted(bird)}, open(f"{OUT}/design_cloudgrid.json", "w"))
    for size in sizes:
        g, mt = FL.draft(size)
        for code, nm in PANELS:
            if code in ("F01", "F02"):
                fn = lambda x, yh: ffront(x, yh)
            elif code == "B01":
                fn = lambda x, yh: (lambda v: (v[0], GENERATED))(ffront(-x, yh))
            else:
                fs = fR if code == "S01" else fL
                fn = fs
            for opt in (("A", "B") if code == "F02" else ("A",)):
                P = raster_panel(code, size, fn, bird=(bird if (code == "F02" and opt == "A") else None), bird_anchor=lambda s: 0.0)
                tag = f"{nm}_{size}" + ("" if code != "F02" else ("_birdA" if opt == "A" else "_birdB"))
                panel_png(P, f"{OUT}/HK-FL-PIXSKY_JQ_{tag}.png")
                if size == "M": preview(P, f"{OUT}/prev_{tag}.png")
                gr, fl = P["grid"], P["flags"]; ins = gr != OUTSIDE
                stats["panels"][tag] = dict(piece=code, size=size, cols=int(gr.shape[1]), rows=int(gr.shape[0]),
                    width_mm=round(gr.shape[1] * CELL, 1), height_mm=round(gr.shape[0] * CELL, 1),
                    cells=int(ins.sum()), sky=int((gr == SKY).sum()), cream=int((gr == CREAM).sum()), black=int((gr == BLACK).sum()),
                    traced=int(((fl == TRACED) & ins).sum()), filled=int(((fl == FILLED) & ins).sum()), generated=int(((fl == GENERATED) & ins).sum()))
        if verbose: print(size, "done")
    json.dump(stats, open(f"{OUT}/jacquard_stats.json", "w"), indent=1)
    return stats

if __name__ == "__main__":
    import sys
    st = build(sys.argv[1:] or None)
    print(json.dumps({k: v for k, v in st.items() if k != "panels"}, indent=1))
    for k, v in st["panels"].items():
        if v["size"] == "M": print(k, v)

def design():
    """cached design functions: (front fn, sleeve R fn, sleeve L fn, bird cells) from out/jacquard/design_cloudgrid.json"""
    p = f"{OUT}/design_cloudgrid.json"
    if not os.path.exists(p):
        build(["M"], verbose=False)
    d = json.load(open(p))
    conv = lambda m: {tuple(int(v) for v in k.split(",")): tuple(val) for k, val in m.items()}
    return grid_fn(conv(d["front_M"])), grid_fn(conv(d["sleeve_R"])), grid_fn(conv(d["sleeve_L"])), {tuple(c) for c in d["bird"]}

def panel(code, size, opt="A"):
    ff, fR, fL, bird = design()
    if code in ("F01", "F02"): fn = ff
    elif code == "B01": fn = lambda x, yh: (ff(-x, yh)[0], GENERATED)
    else: fn = fR if code == "S01" else fL
    return raster_panel(code, size, fn, bird=(bird if (code == "F02" and opt == "A") else None), bird_anchor=lambda s: 0.0)
