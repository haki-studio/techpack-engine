"""Pro reference profiler: how a professional digitiser builds embroidery, measured as per-area RATES, and the same
numbers on our own files (docs/PRO_REFERENCE.md). No Anthropic API calls.

Reference set = ONLY the 10 licensed stock designs in PRO_ALLOW (one professional digitiser, Wilcom/Hatch). The folder
they live in also holds the founder's own amateur files: those are never read. The designs are licensed: they are
read from PRO_REF_DIR and never copied into git; renders go to the git-ignored out/ dir. Only derived numbers are
committed (engine/digitize/rules/pro_reference.json).

  python3 engine/proprofile.py all            # profile pro + ours, renders + overlays, write the JSON + the table
  python3 engine/proprofile.py file X.dst     # one file, metrics to stdout

Method (all from the stitch file, nothing from art):
  1. read stitches (PES for geometry + thread colours when a PES sits next to the DST; trims/jumps from the DST via
     readback, LESSONS B8), split into colour blocks and runs (a run = stitches between trims/jumps);
  2. split each run into ROWS at every turn > 60 deg; link consecutive rows that run antiparallel (within 30 deg),
     overlap along their axis and sit 0.08-3 mm apart sideways (short connector rows < 0.6 mm are skipped). A chain of
     >= 3 linked rows is a HATCH object: SATIN if it has ~1 stitch per row (the thread spans the whole width), else
     FILL (tatami: several stitches per row). Everything else is RUN material (single line, bean, travel, ties);
  3. a run or an OPEN hatch (row spacing >= 0.9 mm) whose stitches lie >= 80 % under a dense object sewn LATER in the
     same colour block is UNDERLAY (edge / centre runs, zig-zag and lattice underlay, and hidden travel under the top);
  4. coverage is rasterised on CELL_MM cells: every segment marks the cells it passes through, each object's cells are
     closed by one cell (so rows <= ~1 mm apart read as solid). Covered area = union of all objects. Layer depth = how
     many objects cover a cell.

Identity used to explain a stitch rate (exact, by construction):
    st/cm2 (covered) = 100 * D * rho / L
    D   = mean layer depth  = sum of object areas / covered area                     (layering)
    rho = thread mm per mm2 of object area (~1 / row spacing for a fill)              (density)
    L   = mean stitch length mm = thread length / stitches                            (detail: short stitches)
"""
import glob
import hashlib
import json
import math
import os
import subprocess
import sys

import numpy as np
import pyembroidery as pe
from scipy import ndimage as ndi

ENGINE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(ENGINE)
if ENGINE not in sys.path: sys.path.insert(0, ENGINE)
import readback  # noqa: E402

PRO_REF_DIR = os.environ.get("PRO_REF_DIR", "/mnt/c/Users/devin/My Embroidery/My Machine Files/")
# hard allowlist: the 10 professionally digitised John Deer stock designs. Law.DST and the Chopper Jacket folder in
# the same directory are the founder's own amateur files and must never be used as reference.
PRO_ALLOW = ("A-0661", "A-0698", "C-3078", "D-4015", "D-4058", "D-4063", "E-4816", "E-5045", "E-5056", "F-5643")
STATS_JSON = os.path.join(ENGINE, "digitize", "rules", "pro_reference.json")
OUT_DIR = os.environ.get("PRO_REF_OUT", os.path.join(ROOT, "out", "pro_reference"))   # git-ignored (**/out/)

# our files to compare: (key, project-relative path, label). Missing ones are skipped and reported. git-ignored build
# outputs are looked up here first, then in the main checkout (like digitize.bench.find).
OURS = [
    ("castle_crop", "projects/castle-falls-jacket/out/digitize/BK_M_crop/BK_M_crop.dst",
     "Castle back crop, digitize engine on main (200 x 200 mm)"),
    ("castle_revB_back", "projects/castle-falls-jacket/out/01_back-scene/M/HAKI_CSFL_01_back-scene_BK_M.dst",
     "Castle Rev B full back, shipped (dst2)"),
    ("kcos_FR", "projects/keep-clean-our-space-hoodie/out/stitch/M/HAKI_KCOS_FR_M.dst",
     "Keep Clean Our Space FR M, shipped"),
    ("wave_FR", "projects/wave-jacket/out/01_wave/M/HAKI_WAVE_01_wave_FR_M.dst", "Wave jacket FR M (flat thread)"),
    ("konpeito_coin", "projects/konpeito-jeans/out/stitch/HAKI_KJ_01_coin-pocket-patch.dst",
     "Konpeito coin-pocket patch (founder SVG)"),
]

# classifier knobs (why: docstring above; checked on the overlays in out/pro_reference/*_classes.png)
CELL_MM = 0.5            # coverage raster
TURN_DEG = 60.0          # a row ends where the needle turns more than this
ANTI_DEG = 30.0          # linked rows are antiparallel within this
GAP_MIN, GAP_MAX = 0.08, 3.0   # sideways step between linked rows (mm): 0 = bean / double run, > 3 = another object
CONNECTOR_MM = 0.6       # rows shorter than this are turn connectors (tatami turns, satin edge steps), skipped
RETRACE_MM = 0.05        # loop area / row length below this = a retrace (bean, double run), never a hatch link
MIN_ROWS = 3             # a hatch object has at least this many linked rows
SATIN_SPR = 1.35         # stitches per row at or below this = satin (one needle penetration per side)
OPEN_SPACING = 0.9       # hatch with row spacing >= this is open (underlay / light shading)
UNDER_FRAC = 0.8         # share of an object's stitches under a later dense same-block object to call it underlay
CLASSES = ("satin", "fill", "run", "underlay")


# ------------------------------------------------------------------ reading
def pro_files(folder=None):
    """the 10 allow-listed pro designs: [(code, dst path, pes path or None)]. Anything else in the folder is ignored."""
    folder = folder or PRO_REF_DIR
    out = []
    for code in PRO_ALLOW:
        d = sorted(glob.glob(os.path.join(glob.escape(folder), code + "*_M.DST")))
        if not d: continue
        pes = d[0][:-4] + ".PES"
        out.append((code, d[0], pes if os.path.exists(pes) else None))
    return out


def pes_source(pes):
    """the design file a PES was exported from, as written in its header (Wilcom writes '<name>.EMB': an object
    design whose stitches are regenerated at its own size, not a scaled stitch file). None if not stated."""
    try:
        head = open(pes, "rb").read(400)
    except OSError:
        return None
    import re
    m = re.search(rb"([ -~]{3,80}\.(?:EMB|emb|PXF|pxf|ART|art|JAN|jan))", head)
    return m.group(1).decode("ascii", "replace").strip() if m else None


def main_checkout():
    try:
        g = subprocess.run(["git", "-C", ROOT, "rev-parse", "--git-common-dir"], capture_output=True, text=True,
                           check=True).stdout.strip()
        return os.path.dirname(os.path.abspath(os.path.join(ROOT, g)))
    except Exception:
        return ROOT


def find_ours(rel):
    for base in (ROOT, main_checkout()):
        p = os.path.join(base, rel)
        if os.path.exists(p): return p
    return None


def load(path, pes=None):
    """stitches of a file as colour blocks of runs. Returns dict(blocks=[[run, ...], ...], colours=[hex per block]);
    a run is an (N, 2) float array in mm (y down) of consecutive needle points joined by STITCH moves."""
    geo = pe.read(pes or path)
    cols = [t.hex_color() for t in geo.threadlist] if pes else []
    blocks, cur, run, prev = [[]], None, [], None

    def flush():
        nonlocal run
        if len(run) >= 2: blocks[-1].append(np.asarray(run, float) / 10.0)
        run = []
    for x, y, cmd in geo.stitches:
        k = cmd & pe.COMMAND_MASK
        if k == pe.STITCH:
            if not run and prev is not None: run.append(prev)    # the move into the first stitch is not sewn
            run.append((x, y)); prev = (x, y)
        elif k in (pe.JUMP, pe.TRIM):
            flush(); prev = None if k == pe.TRIM else (x, y)
            if k == pe.JUMP: prev = None
        elif k == pe.COLOR_CHANGE:
            flush(); blocks.append([]); prev = None
        elif k == pe.END:
            break
    flush()
    while len(blocks) > 1 and not blocks[-1]: blocks.pop()
    return dict(blocks=blocks, colours=cols[:len(blocks)])


# ------------------------------------------------------------------ segmentation + classification
def _rows(P):
    """split a run into rows at turns > TURN_DEG. Returns list of (i0, i1): row = points P[i0..i1] (i1 inclusive)."""
    V = np.diff(P, axis=0); n = len(V)
    if n == 0: return []
    L = np.hypot(V[:, 0], V[:, 1])
    rows, i0 = [], 0
    last = None                                     # last non-zero stitch direction
    for i in range(n):
        if L[i] < 1e-6: continue
        if last is not None:
            c = float(np.dot(V[last], V[i]) / (L[last] * L[i]))
            if math.degrees(math.acos(max(-1.0, min(1.0, c)))) > TURN_DEG:
                rows.append((i0, i)); i0 = i
        last = i
    rows.append((i0, n))
    return rows


def _link(P, a, b):
    """are rows a and b (index pairs) adjacent hatch rows? returns the sideways gap (mm) or None"""
    pa0, pa1, pb0, pb1 = P[a[0]], P[a[1]], P[b[0]], P[b[1]]
    ua = pa1 - pa0; ub = pb1 - pb0; la = np.hypot(*ua); lb = np.hypot(*ub)
    if la < CONNECTOR_MM or lb < CONNECTOR_MM: return None
    ua = ua / la; ub = ub / lb
    if float(np.dot(ua, ub)) > -math.cos(math.radians(ANTI_DEG)): return None
    # a retrace (bean / triple run, double run) walks back over the previous row's own needle points, so the loop
    # row a -> row b encloses no area; satin, fill and radial rows enclose about (row length x row step). Without
    # this, a bean along a curve links into a "fill" at ~0.1-0.2 mm "spacing".
    loop = np.vstack([P[a[0]:a[1] + 1], P[b[0] + 1:b[1] + 1]])
    x, y = loop[:, 0], loop[:, 1]
    area = 0.5 * abs(float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))))
    if area / max(la, lb) < RETRACE_MM: return None
    mb = (pb0 + pb1) / 2
    d = mb - pa0
    gap = abs(float(ua[0] * d[1] - ua[1] * d[0]))
    if not (GAP_MIN <= gap <= GAP_MAX): return None
    sa = sorted((0.0, la)); sb = sorted((float(np.dot(pb0 - pa0, ua)), float(np.dot(pb1 - pa0, ua))))
    ov = min(sa[1], sb[1]) - max(sa[0], sb[0])
    if ov < 0.3 * min(la, lb): return None
    return gap


def segment_run(P):
    """objects of one run: list of dict(kind 'hatch'|'run', i0, i1 (point indices, inclusive), rows, gaps, row_len,
    row_spr, axis_deg)."""
    R = _rows(P)
    if not R: return []
    rl = [float(np.hypot(*(P[r[1]] - P[r[0]]))) for r in R]
    ud = [(P[r[1]] - P[r[0]]) / max(l, 1e-9) for r, l in zip(R, rl)]
    # chains of linked rows. Between two linked rows the needle may make up to 2 CONNECTOR moves: a short turn stitch
    # (< CONNECTOR_MM: tatami turns, the edge step of a stepped satin) or a side-step across the row direction no
    # longer than GAP_MAX (an open lattice / underlay steps 2 mm sideways between its rows)
    chains, cur, gaps_cur, skipped = [], [], [], 0
    for k in range(len(R)):
        if cur:
            g = _link(P, R[cur[-1]], R[k])
            if g is not None:
                cur.append(k); gaps_cur.append(g); skipped = 0; continue
            conn = rl[k] < CONNECTOR_MM or (rl[k] <= GAP_MAX and abs(float(np.dot(ud[k], ud[cur[-1]]))) < 0.5)
            if conn and skipped < 2:
                skipped += 1; continue
            chains.append((cur, gaps_cur))
        cur, gaps_cur, skipped = ([k], [], 0) if rl[k] >= CONNECTOR_MM else ([], [], 0)
    if cur: chains.append((cur, gaps_cur))
    objs = []
    for rows_k, gaps in chains:
        if len(rows_k) >= MIN_ROWS:
            i0, i1 = R[rows_k[0]][0], R[rows_k[-1]][1]
            spr = [R[k][1] - R[k][0] for k in rows_k]
            # axis: doubled-angle mean of row directions
            ang = [math.atan2(*(P[R[k][1]] - P[R[k][0]])[::-1]) for k in rows_k]
            ax = 0.5 * math.atan2(np.mean(np.sin(2 * np.array(ang))), np.mean(np.cos(2 * np.array(ang))))
            objs.append(dict(kind="hatch", i0=i0, i1=i1, rows=len(rows_k), gaps=gaps,
                             row_len=[rl[k] for k in rows_k], row_spr=spr, axis_deg=math.degrees(ax) % 180.0))
    # everything not inside a hatch object is run material; consecutive leftovers form one run object
    objs.sort(key=lambda o: o["i0"])
    out, pos = [], 0
    for o in objs:
        if o["i0"] > pos: out.append(dict(kind="run", i0=pos, i1=o["i0"]))
        out.append(o); pos = o["i1"]
    if pos < len(P) - 1: out.append(dict(kind="run", i0=pos, i1=len(P) - 1))
    return out


def _seg_len(P):
    V = np.diff(P, axis=0); return np.hypot(V[:, 0], V[:, 1])


def describe(P, o):
    """class + parameters of one segmented object (before the underlay pass)"""
    Q = P[o["i0"]:o["i1"] + 1]; L = _seg_len(Q); L = L[L > 1e-6]
    d = dict(stitches=int(len(L)), thread_mm=float(L.sum()), pts=Q)
    if o["kind"] == "hatch":
        spr = float(np.median(o["row_spr"]))
        gap = float(np.median(o["gaps"]))
        if spr <= SATIN_SPR:
            d.update(cls="satin", width=float(np.median(o["row_len"])), spacing=gap, same_side=2 * gap if
                     _zigzag(Q) else gap, angle=o["axis_deg"])
        else:
            inrow = L[L >= CONNECTOR_MM]
            d.update(cls="fill", spacing=gap, stitch_len=float(np.median(inrow)) if len(inrow) else 0.0,
                     angle=o["axis_deg"], row_len=float(np.median(o["row_len"])))
        g = np.asarray(o["gaps"]); ok = np.abs(g - gap) <= 0.5 * gap + 0.05
        d["conf"] = float(ok.mean())
        d["open"] = gap >= OPEN_SPACING
    else:
        d.update(cls="run", stitch_len=float(np.median(L)) if len(L) else 0.0)
        # confidence of a run: share of its stitches that do not turn sharply (a scribble is a weak run)
        V = np.diff(Q, axis=0); V = V[np.hypot(V[:, 0], V[:, 1]) > 1e-6]
        if len(V) > 1:
            c = np.einsum("ij,ij->i", V[:-1], V[1:]) / (np.hypot(*V[:-1].T) * np.hypot(*V[1:].T))
            d["conf"] = float(np.mean((c > 0.5) | (c < -0.95)))     # straight-ish, or a clean bean reversal
        else:
            d["conf"] = 1.0
        d["open"] = True
    return d


def _zigzag(Q):
    """True when consecutive needle points alternate sides with no edge step (a true zig-zag satin); False when each
    row is joined to the next by a short stitch along the edge (dst2's fixed / turning satin). Same-side spacing is
    2 x the row step for a zig-zag (LESSONS B26), 1 x for a stepped satin."""
    L = _seg_len(Q); L = L[L > 1e-6]
    return float(np.mean(L < CONNECTOR_MM)) < 0.25 if len(L) else True


# ------------------------------------------------------------------ raster
class Grid:
    def __init__(self, pts, cell=CELL_MM, pad=2.0):
        P = np.vstack(pts) if pts else np.zeros((1, 2))
        self.x0, self.y0 = P.min(0) - pad
        self.cell = cell
        self.W = int(math.ceil((P[:, 0].max() + pad - self.x0) / cell)) + 1
        self.H = int(math.ceil((P[:, 1].max() + pad - self.y0) / cell)) + 1

    def cells(self, Q, step=0.1):
        """flat indices of the cells a polyline passes through (segment midpoint sampling, every ~step mm)"""
        if len(Q) < 2: return np.zeros(0, np.int64)
        A, B = Q[:-1], Q[1:]
        L = np.hypot(*(B - A).T); k = np.maximum(1, np.ceil(L / step)).astype(int)
        idx = np.repeat(np.arange(len(A)), k); j = np.arange(len(idx)) - np.repeat(np.cumsum(k) - k, k)
        t = ((j + 0.5) / k[idx])[:, None]
        S = A[idx] + t * (B[idx] - A[idx])
        ix = ((S[:, 0] - self.x0) / self.cell).astype(int); iy = ((S[:, 1] - self.y0) / self.cell).astype(int)
        return np.unique(iy * self.W + ix)

    def mask(self, Q, close=True):
        """closed coverage of one object as flat cell indices"""
        c = self.cells(Q)
        if not len(c) or not close: return c
        iy, ix = np.divmod(c, self.W)
        y0, x0 = iy.min() - 2, ix.min() - 2
        m = np.zeros((iy.max() - y0 + 3, ix.max() - x0 + 3), bool); m[iy - y0, ix - x0] = True
        m = ndi.binary_closing(m, structure=np.ones((3, 3), bool)) | m
        yy, xx = np.nonzero(m)
        return (yy + y0) * self.W + (xx + x0)

    def area(self, cells): return len(cells) * self.cell ** 2


# ------------------------------------------------------------------ profile one file
def analyse(design):
    """segment + classify every object of a loaded design. Returns (objects, grid); each object dict has block, run,
    order, cls, params, cells (closed coverage), and stitches/thread_mm."""
    allp = [r for b in design["blocks"] for r in b]
    G = Grid(allp)
    objs = []
    for bi, blk in enumerate(design["blocks"]):
        for ri, P in enumerate(blk):
            for o in segment_run(P):
                d = describe(P, o)
                if d["stitches"] == 0: continue
                d.update(block=bi, run=ri, order=len(objs), cells=G.mask(d["pts"]))
                objs.append(d)
    _underlay(objs, G)
    return objs, G


def _underlay(objs, G):
    """low-density objects (runs, open hatch) lying >= UNDER_FRAC under a dense object sewn later in the same block"""
    by_block = {}
    for o in objs: by_block.setdefault(o["block"], []).append(o)
    near = np.zeros(G.W * G.H, bool)
    for blk in by_block.values():
        near[:] = False                            # walking backwards: near = dense objects sewn after o, + 1 cell
        for o in reversed(blk):
            if o["open"] and o["stitches"]:
                raw = G.cells(o["pts"])
                if len(raw) and near[raw].mean() >= UNDER_FRAC:
                    o["base_cls"] = o["cls"]; o["cls"] = "underlay"
            if not o["open"]:
                near[_dilate(o["cells"], G)] = True


def _dilate(cells, G):
    iy, ix = np.divmod(cells, G.W)
    out = [cells]
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx or dy:
                jy, jx = iy + dy, ix + dx; ok = (jy >= 0) & (jy < G.H) & (jx >= 0) & (jx < G.W)
                out.append(jy[ok] * G.W + jx[ok])
    return np.unique(np.concatenate(out))


def _q(v):
    v = [x for x in v if x is not None and not (isinstance(x, float) and math.isnan(x))]
    if not v: return None
    a = np.asarray(v, float)
    return dict(n=len(a), median=round(float(np.median(a)), 3), p10=round(float(np.percentile(a, 10)), 3),
                p90=round(float(np.percentile(a, 90)), 3), min=round(float(a.min()), 3), max=round(float(a.max()), 3))


def _wq(v, w):
    """weighted median / p10 / p90 (weights = stitches): what most of the THREAD does, not most of the objects"""
    if not len(v): return None
    v = np.asarray(v, float); w = np.asarray(w, float); o = np.argsort(v); v, w = v[o], w[o]
    c = np.cumsum(w) / w.sum()
    pick = lambda q: round(float(v[min(np.searchsorted(c, q), len(v) - 1)]), 3)
    return dict(n=int(len(v)), median=pick(0.5), p10=pick(0.1), p90=pick(0.9))


def profile(path, pes=None, name=None):
    """all metrics of one stitch file (dict, JSON-ready) + (objects, grid, design) for renders"""
    design = load(path, pes)
    rb = readback.dst(path) if path.lower().endswith(".dst") else None   # trims / jumps from the DST (LESSONS B8)
    return profile_design(design, rb, name or os.path.basename(path))


def profile_design(design, rb=None, name="design"):
    """metrics of a loaded (or synthetic) design: dict(blocks=[[run (N, 2) mm, ...], ...], colours=[...])"""
    objs, G = analyse(design)
    S = sum(o["stitches"] for o in objs); T = sum(o["thread_mm"] for o in objs)
    depth_all = np.zeros(G.W * G.H, np.int32); depth_top = np.zeros(G.W * G.H, np.int32)
    for o in objs:
        depth_all[o["cells"]] += 1
        if o["cls"] in ("satin", "fill") and not o["open"]: depth_top[o["cells"]] += 1
    cov = depth_all > 0; A = cov.sum() * G.cell ** 2                         # covered mm2
    P = np.vstack([r for b in design["blocks"] for r in b])
    bw, bh = P.max(0) - P.min(0); Abox = float(bw * bh)
    hist = {str(k): round(float(((depth_all == k) & cov).sum() / max(cov.sum(), 1)), 4) for k in (1, 2, 3)}
    hist["4+"] = round(float(((depth_all >= 4) & cov).sum() / max(cov.sum(), 1)), 4)
    topcov = depth_top > 0
    hist_top = {str(k): round(float((depth_top == k).sum() / max(topcov.sum(), 1)), 4) for k in (1, 2)}
    hist_top["3+"] = round(float((depth_top >= 3).sum() / max(topcov.sum(), 1)), 4)
    sumA = sum(len(o["cells"]) for o in objs) * G.cell ** 2
    D = sumA / A if A else 0.0; rho = T / sumA if sumA else 0.0; Lm = T / S if S else 0.0
    by = {c: [o for o in objs if o["cls"] == c] for c in CLASSES}
    share = {c: round(sum(o["stitches"] for o in by[c]) / max(S, 1), 4) for c in CLASSES}
    cls_rate = {}
    for c in CLASSES:
        cells = np.unique(np.concatenate([o["cells"] for o in by[c]])) if by[c] else np.zeros(0)
        a = len(cells) * G.cell ** 2
        cls_rate[c] = dict(stitches=sum(o["stitches"] for o in by[c]), area_cm2=round(a / 100, 2),
                           st_per_cm2=round(100 * sum(o["stitches"] for o in by[c]) / a, 1) if a else None)
    sat = [o for o in by["satin"]]; fil = [o for o in by["fill"] if not o["open"]]
    run = by["run"]
    allL = np.concatenate([_seg_len(o["pts"]) for o in objs]) if objs else np.zeros(0)
    allL = allL[allL > 1e-6]
    conf = sum(o["conf"] * o["stitches"] for o in objs) / max(S, 1)
    m = dict(
        name=name, stitches=int(S), stitches_file=rb["stitches"] if rb else None,
        size_mm=[round(float(bw), 1), round(float(bh), 1)],
        covered_cm2=round(A / 100, 2), bbox_cm2=round(Abox / 100, 2), cover_of_bbox=round(A / Abox, 3) if Abox else None,
        st_per_cm2_covered=round(100 * S / A, 1) if A else None, st_per_cm2_bbox=round(100 * S / Abox, 1) if Abox else None,
        thread_m=round(T / 1000, 1), thread_mm_per_mm2=round(T / A, 3) if A else None,
        decomposition=dict(D_mean_depth=round(D, 3), rho_thread_per_layer_mm2=round(rho, 3), L_mean_stitch_mm=round(Lm, 3),
                           check=round(100 * D * rho / Lm, 1) if Lm else None),
        # where the layers and the stitches come from: D split by class (sums to D), mean stitch length per class
        depth_by_class={c: round(sum(len(o["cells"]) for o in by[c]) * G.cell ** 2 / A, 3) if A else None for c in CLASSES},
        stitch_len_by_class={c: round(sum(o["thread_mm"] for o in by[c]) / max(sum(o["stitches"] for o in by[c]), 1), 2)
                             for c in CLASSES},
        open_fill_share=round(sum(o["stitches"] for o in by["fill"] if o["open"]) / max(S, 1), 4),
        depth_all=hist, depth_top=hist_top, mean_depth_top=round(float(depth_top[topcov].mean()), 3) if topcov.any() else 0,
        class_share=share, class_rate=cls_rate, classifier_conf=round(conf, 3),
        fill_spacing=_wq([o["spacing"] for o in fil], [o["stitches"] for o in fil]),
        fill_stitch_len=_wq([o["stitch_len"] for o in fil], [o["stitches"] for o in fil]),
        fill_angle_count=len({int(round(o["angle"] / 15.0)) % 12 for o in fil}),
        satin_width=_wq([o["width"] for o in sat], [o["stitches"] for o in sat]),
        satin_spacing=_wq([o["spacing"] for o in sat], [o["stitches"] for o in sat]),
        satin_same_side=_wq([o["same_side"] for o in sat], [o["stitches"] for o in sat]),
        run_stitch_len=_wq([o["stitch_len"] for o in run], [o["stitches"] for o in run]),
        stitch_len=_q(list(allL)) if len(allL) else None,
        max_stitch=round(float(allL.max()), 2) if len(allL) else 0.0,
        underlay_share=share["underlay"],
        smallest=dict(satin_width_p5=round(float(np.percentile([o["width"] for o in sat], 5)), 2) if sat else None,
                      satin_width_min=round(min(o["width"] for o in sat), 2) if sat else None,
                      fill_area_min_mm2=round(min(len(o["cells"]) for o in fil) * G.cell ** 2, 1) if fil else None,
                      fill_area_p10_mm2=round(float(np.percentile([len(o["cells"]) * G.cell ** 2 for o in fil], 10)), 1) if fil else None,
                      element_min_mm2=_smallest_element(objs, G)),
        overlap=_overlaps(objs, G),
        trims=rb["trims"] if rb else None, jumps=rb["jumps"] if rb else None,
        colour_blocks=len(design["blocks"]), colours_distinct=len(set(design["colours"])) if design["colours"] else None,
        trims_per_100cm2=round(100 * 100 * rb["trims"] / A, 1) if (rb and A) else None,
        stitches_per_block=_q([sum(o["stitches"] for o in objs if o["block"] == b) for b in range(len(design["blocks"]))]),
        objects=len(objs), objects_per_cm2=round(100 * len([o for o in objs if o["cls"] != "underlay"]) / A, 2) if A else None,
        sequencing=_sequencing(objs, G, design),
    )
    return m, objs, G, design


def _smallest_element(objs, G):
    """smallest connected patch of top coverage (dense satin/fill, any block) >= 0.5 mm2: the finest separate detail"""
    best = None
    for o in objs:
        if o["cls"] not in ("satin", "fill") or o["open"]: continue
        a = len(o["cells"]) * G.cell ** 2
        if a >= 0.5 and (best is None or a < best): best = a
    return round(best, 2) if best is not None else None


def _overlaps(objs, G):
    """how far a later dense object sits ON an earlier fill (raster band width 2 * area / perimeter of each overlap
    patch >= 1 mm2): satin over fill (an outline over its fill: the underlap a pro leaves under the edge), fill over a
    fill of another colour block. Resolution = CELL_MM, so values below ~0.5 mm read as 0.5-1 mm."""
    res = {"satin_on_fill": [], "fill_on_fill": []}
    last_fill_block = np.full(G.W * G.H, -1, np.int32)        # block of the latest fill sewn on each cell
    for o in sorted(objs, key=lambda o: o["order"]):
        if o["cls"] not in ("satin", "fill") or o["open"]: continue
        lb = last_fill_block[o["cells"]]
        if o["cls"] == "satin": hit = o["cells"][lb >= 0]
        else: hit = o["cells"][(lb >= 0) & (lb != o["block"])]
        if len(hit) >= 4: res["satin_on_fill" if o["cls"] == "satin" else "fill_on_fill"] += _band_widths(hit, G)
        if o["cls"] == "fill": last_fill_block[o["cells"]] = o["block"]
    return {k: _q(v) for k, v in res.items()}


def _band_widths(cells, G, min_mm2=1.0):
    iy, ix = np.divmod(cells, G.W)
    y0, x0 = iy.min() - 1, ix.min() - 1
    m = np.zeros((iy.max() - y0 + 2, ix.max() - x0 + 2), bool); m[iy - y0, ix - x0] = True
    lab, n = ndi.label(m)
    out = []
    for k in range(1, n + 1):
        r = lab == k; a = r.sum() * G.cell ** 2
        if a < min_mm2: continue
        er = r & ~ndi.binary_erosion(r)
        per = er.sum() * G.cell
        out.append(min(2 * a / max(per, 1e-6), 20.0))
    return out


def _sequencing(objs, G, design):
    """order of the colour blocks: is the biggest area first (background first)? are later blocks smaller (fine detail
    last)? does sewing move outwards from the centre within a block (centre-out, Spearman rho > 0)?"""
    from scipy.stats import spearmanr
    nb = len(design["blocks"])
    area = []
    for b in range(nb):
        cs = [o["cells"] for o in objs if o["block"] == b and o["cls"] != "underlay"]
        area.append(len(np.unique(np.concatenate(cs))) * G.cell ** 2 if cs else 0.0)
    order = list(range(nb))
    rho_area = spearmanr(order, area).statistic if nb > 2 else None
    allc = np.concatenate([o["cells"] for o in objs]); cy, cx = np.divmod(allc, G.W); c0 = (cx.mean(), cy.mean())
    rhos = []
    for b in range(nb):
        oo = [o for o in objs if o["block"] == b and o["cls"] in ("satin", "fill")]
        if len(oo) < 5: continue
        dist = []
        for o in oo:
            yy, xx = np.divmod(o["cells"], G.W); dist.append(math.hypot(xx.mean() - c0[0], yy.mean() - c0[1]))
        r = spearmanr(range(len(oo)), dist).statistic
        if not math.isnan(r): rhos.append(r)
    last = [o for o in objs if o["block"] == nb - 1]
    ls = sum(o["stitches"] for o in last) or 1
    return dict(biggest_block_index=int(np.argmax(area)), blocks=nb,
                area_vs_order_rho=round(float(rho_area), 2) if rho_area is not None and not math.isnan(rho_area) else None,
                centre_out_rho_median=round(float(np.median(rhos)), 2) if rhos else None,
                last_block_satin_run_share=round(sum(o["stitches"] for o in last if o["cls"] in ("satin", "run")) / ls, 2),
                last_block_area_share=round(area[-1] / max(sum(area), 1e-9), 3))


# ------------------------------------------------------------------ renders
CLS_COL = {"satin": (220, 40, 40), "fill": (40, 90, 220), "run": (20, 160, 60), "underlay": (240, 190, 0)}


def render(design, objs, G, png, ppm=8, overlay=False, max_px=4000):
    """stitch preview (thread colours, 0.4 mm lines) or the class overlay (satin red, fill blue, run green, underlay
    amber; open fills drawn thin)"""
    from PIL import Image, ImageDraw
    ppm = min(ppm, max_px / max(G.W * G.cell, G.H * G.cell))
    W, H = int(G.W * G.cell * ppm), int(G.H * G.cell * ppm)
    im = Image.new("RGB", (W, H), (245, 242, 235) if overlay else (215, 194, 156)); d = ImageDraw.Draw(im)
    cols = design["colours"]
    lw = max(1, int(round(0.4 * ppm)))
    seq = objs if not overlay else ([o for o in objs if o["cls"] in ("satin", "fill")] + [o for o in objs if o["cls"] == "underlay"]
                                     + [o for o in objs if o["cls"] == "run"])          # lines on top so they can be seen
    for o in seq:
        if overlay: c = CLS_COL[o["cls"]]
        else:
            h = cols[o["block"]] if o["block"] < len(cols) else "#404040"
            c = tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
        pts = [((x - G.x0) * ppm, (y - G.y0) * ppm) for x, y in o["pts"]]
        d.line(pts, fill=c, width=1 if (overlay and o["open"] and o["cls"] != "run") else lw)
    os.makedirs(os.path.dirname(png), exist_ok=True); im.save(png)
    return png


def render_depth(objs, G, png, top=True, ppm=8):
    """layer-depth map: dense top layers only (top=True) or every object. 1 light grey, 2 blue, 3 orange, 4+ red"""
    from PIL import Image
    dep = np.zeros(G.W * G.H, np.int32)
    for o in objs:
        if not top or (o["cls"] in ("satin", "fill") and not o["open"]): dep[o["cells"]] += 1
    pal = np.array([(250, 250, 250), (200, 200, 200), (70, 120, 220), (245, 150, 30), (210, 30, 30)], np.uint8)
    im = Image.fromarray(pal[np.minimum(dep, 4)].reshape(G.H, G.W, 3))
    s = max(1, int(round(ppm * G.cell)))
    im = im.resize((G.W * s, G.H * s), Image.NEAREST)
    os.makedirs(os.path.dirname(png), exist_ok=True); im.save(png)
    return png


# ------------------------------------------------------------------ summary over the pro set + comparison
KEYS = [  # (label, getter, unit, how to read)
    ("stitches / cm2 covered", lambda m: m["st_per_cm2_covered"], "st/cm2"),
    ("stitches / cm2 of bounding box", lambda m: m["st_per_cm2_bbox"], "st/cm2"),
    ("covered / bounding box", lambda m: m["cover_of_bbox"], ""),
    ("thread mm per mm2 covered", lambda m: m["thread_mm_per_mm2"], "mm/mm2"),
    ("D mean layer depth (all objects)", lambda m: m["decomposition"]["D_mean_depth"], "layers"),
    ("rho thread per layer area", lambda m: m["decomposition"]["rho_thread_per_layer_mm2"], "mm/mm2"),
    ("L mean stitch length", lambda m: m["decomposition"]["L_mean_stitch_mm"], "mm"),
    ("area 1 layer deep (all objects)", lambda m: m["depth_all"]["1"], "share"),
    ("area 3+ layers deep (all objects)", lambda m: m["depth_all"]["3"] + m["depth_all"]["4+"], "share"),
    ("mean depth of dense top layers", lambda m: m["mean_depth_top"], "layers"),
    ("dense top 2+ deep", lambda m: m["depth_top"]["2"] + m["depth_top"]["3+"], "share"),
    ("satin share of stitches", lambda m: m["class_share"]["satin"], "share"),
    ("fill share of stitches", lambda m: m["class_share"]["fill"], "share"),
    ("run share of stitches", lambda m: m["class_share"]["run"], "share"),
    ("underlay share of stitches", lambda m: m["class_share"]["underlay"], "share"),
    ("fill row spacing (median)", lambda m: (m["fill_spacing"] or {}).get("median"), "mm"),
    ("fill stitch length (median)", lambda m: (m["fill_stitch_len"] or {}).get("median"), "mm"),
    ("satin width (median)", lambda m: (m["satin_width"] or {}).get("median"), "mm"),
    ("satin row step (median)", lambda m: (m["satin_spacing"] or {}).get("median"), "mm"),
    ("satin same-side spacing (median)", lambda m: (m["satin_same_side"] or {}).get("median"), "mm"),
    ("run stitch length (median)", lambda m: (m["run_stitch_len"] or {}).get("median"), "mm"),
    ("max stitch", lambda m: m["max_stitch"], "mm"),
    ("satin width p5 (smallest columns)", lambda m: m["smallest"]["satin_width_p5"], "mm"),
    ("smallest dense object", lambda m: m["smallest"]["element_min_mm2"], "mm2"),
    ("trims / 100 cm2 covered", lambda m: m["trims_per_100cm2"], ""),
    ("objects / cm2 covered", lambda m: m["objects_per_cm2"], ""),
    ("stitches per colour block (median)", lambda m: (m["stitches_per_block"] or {}).get("median"), "st"),
    ("classifier confidence", lambda m: m["classifier_conf"], ""),
]


def summarise(rows):
    """pro range per metric over the files: median, p10, p90, min, max (each file counts once)"""
    out = {}
    for label, f, unit in KEYS:
        v = [f(m) for m in rows]
        out[label] = dict(unit=unit, **(_q(v) or {}))
    return out


def compare(pro_summary, ours):
    """[(label, unit, pro p10, median, p90, {key: (value, flag)})] flag: 'low' / 'high' outside the pro p10-p90"""
    table = []
    for label, f, unit in KEYS:
        s = pro_summary[label]
        vals = {}
        for k, m in ours.items():
            v = f(m); flag = ""
            if v is not None and s.get("p10") is not None:
                if v < s["p10"]: flag = "low"
                elif v > s["p90"]: flag = "high"
            vals[k] = (v, flag)
        table.append((label, unit, s.get("p10"), s.get("median"), s.get("p90"), vals))
    return table


def table_md(table, keys):
    f = lambda v: "-" if v is None else (f"{v:.3g}" if isinstance(v, float) else str(v))
    head = "| metric | pro p10 | pro median | pro p90 | " + " | ".join(keys) + " |"
    lines = [head, "|" + "---|" * (4 + len(keys))]
    for label, unit, a, b, c, vals in table:
        cells = []
        for k in keys:
            v, flag = vals[k]
            cells.append(f(v) + (" **HIGH**" if flag == "high" else " **low**" if flag == "low" else ""))
        lines.append(f"| {label}{' (' + unit + ')' if unit else ''} | {f(a)} | {f(b)} | {f(c)} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _strip(m):
    return json.loads(json.dumps(m, default=lambda o: float(o) if isinstance(o, np.floating) else int(o)))


def run_all(render_png=True):
    pro = {}
    for code, dst, pes in pro_files():
        m, objs, G, design = profile(dst, pes, name=code)
        m["sha256_16"] = hashlib.sha256(open(dst, "rb").read()).hexdigest()[:16]
        src = pes_source(pes) if pes else None
        m["source_design"] = ("Wilcom EMB, size " + src.rsplit("_", 1)[-1][:-4]) if src and src.upper().endswith(".EMB") and "_" in src else src
        pro[code] = _strip(m)
        if render_png:
            render(design, objs, G, os.path.join(OUT_DIR, f"{code}_preview.png"))
            render(design, objs, G, os.path.join(OUT_DIR, f"{code}_classes.png"), overlay=True)
            render_depth(objs, G, os.path.join(OUT_DIR, f"{code}_depth_top.png"))
        print(f"{code}: {m['stitches']} st, {m['covered_cm2']} cm2, {m['st_per_cm2_covered']} st/cm2, conf {m['classifier_conf']}",
              flush=True)
    if len(pro) != len(PRO_ALLOW):
        print(f"WARNING: {len(pro)} of {len(PRO_ALLOW)} pro files found in {PRO_REF_DIR}")
    ours, missing = {}, []
    for key, rel, label in OURS:
        p = find_ours(rel)
        if not p: missing.append(rel); continue
        pes = p[:-4] + ".pes"
        m, objs, G, design = profile(p, pes if os.path.exists(pes) else None, name=key)
        m["label"] = label; m["path"] = rel; m["sha256_16"] = hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
        ours[key] = _strip(m)
        if render_png:
            render(design, objs, G, os.path.join(OUT_DIR, f"ours_{key}_classes.png"), overlay=True, ppm=4)
            render(design, objs, G, os.path.join(OUT_DIR, f"ours_{key}_preview.png"), ppm=4)
            render_depth(objs, G, os.path.join(OUT_DIR, f"ours_{key}_depth_top.png"), ppm=4)
        print(f"ours {key}: {m['stitches']} st, {m['covered_cm2']} cm2, {m['st_per_cm2_covered']} st/cm2", flush=True)
    summ = summarise(list(pro.values()))
    doc = dict(_doc="Pro reference profile (engine/proprofile.py, docs/PRO_REFERENCE.md). Derived numbers only: the 10 "
                    "licensed designs are read from PRO_REF_DIR, never committed. PROVISIONAL: 10 designs, one digitiser; "
                    "re-run when the reference set reaches ~50 files.",
               method=dict(cell_mm=CELL_MM, turn_deg=TURN_DEG, anti_deg=ANTI_DEG, gap=[GAP_MIN, GAP_MAX],
                           connector_mm=CONNECTOR_MM, min_rows=MIN_ROWS, satin_spr=SATIN_SPR, open_spacing=OPEN_SPACING,
                           under_frac=UNDER_FRAC),
               pro_files=sorted(pro), summary=summ, pro=pro, ours=ours, ours_missing=missing)
    os.makedirs(os.path.dirname(STATS_JSON), exist_ok=True)
    with open(STATS_JSON, "w") as fh: json.dump(doc, fh, indent=1)
    t = compare(summ, ours)
    md = table_md(t, list(ours))
    os.makedirs(OUT_DIR, exist_ok=True)
    open(os.path.join(OUT_DIR, "table.md"), "w").write(md + "\n")
    print(md)
    return doc


if __name__ == "__main__":
    a = sys.argv[1:] or ["all"]
    if a[0] == "all": run_all(render_png="--no-render" not in a)
    elif a[0] == "file":
        p = a[1]; pes = p[:-4] + ".PES" if os.path.exists(p[:-4] + ".PES") else (p[:-4] + ".pes" if os.path.exists(p[:-4] + ".pes") else None)
        m, objs, G, design = profile(p, pes)
        print(json.dumps(_strip(m), indent=1))
        if "--render" in a:
            stem = os.path.join(OUT_DIR, os.path.splitext(os.path.basename(p))[0])
            print(render(design, objs, G, stem + "_preview.png"), render(design, objs, G, stem + "_classes.png", overlay=True))
