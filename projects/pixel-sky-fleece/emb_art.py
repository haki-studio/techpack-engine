"""Embroidery art from the mockup pixels: pixel sparkles (yellow + gold) and the pixel bird (black, option B).

Every motif is TRACED from inputs/front.png (A14): one connected component of the yellow/gold (or black) classes, redrawn
as a pixel-art staircase on its OWN fitted grid (best phase per motif): sparkles at SPARK_CELL (3 render px), the bird at
the jacquard CELL (its own pixel, so the jacquard option A and the embroidered option B are the same drawing).
Positions, sizes, counts and colours are the mockup's; nothing is generated. Output: true-size SVG per file (mm, one layer
per thread, in stitch order) for digitize.svgrun + placements.json (design centre per file in piece coords)."""
import json, math, os
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import box, Point
from shapely.ops import unary_union
from shapely import affinity
import mockmap as MM, pixels as PX, fleece as FL

SPARK_CELL = 2.5                    # mm, sparkle pixel = the bird / jacquard cell (render: big sparkle = 3-7-12 units of ~4.3 px)
OUT = "out/art"; os.makedirs(OUT, exist_ok=True)
HEX = {"yellow": "#F6E23A", "gold": "#D9A521", "black": "#231F1E"}
NAMES = {"yellow": "Sparkle yellow", "gold": "Sparkle gold", "black": "Bird black"}

GOLD_GR = 0.93                      # core-pixel g/r below this = gold (gold 0.82-0.89, yellow 0.95-1.0 on the render)
CORE_R = 195                        # ... and red > 195: rim pixels blended with the black bird darken AND lower g/r (read gold)
CORE_B = 110                        # core = pixels with blue < 110: the sparkle's own colour, no blue sky blended in

def components():
    """sparkles from the render: [dict(colour, xs, ys, cx, cy)] one per motif.
    Colour is decided on the CORE pixels only (blue < CORE_B): the anti-aliased rim blends the sky in, and sky raises
    g/r, so a small gold sparkle's rim reads yellow (PR #28 review: E2 gold sparkle stitched yellow). A component whose
    core holds BOTH colours (two touching sparkles, e.g. the yellow + gold pair on the bird's wing) is split: every
    pixel goes to the colour of its nearest core pixel, then each colour's pixels are labelled on their own."""
    from scipy.spatial import cKDTree
    lab = PX.labels(); a = MM.img(); m = np.isin(lab, [PX.YELLOW, PX.GOLD])
    m = ndi.binary_closing(m, iterations=1)
    L, n = ndi.label(m); out = []
    for k in range(1, n + 1):
        ys, xs = np.nonzero(L == k)
        if len(ys) < 50: continue
        if xs.mean() < 400 and ys.mean() > 1000: continue                 # sleeve fold shading near the body side, not art
        p = a[ys, xs]; core = (p[:, 2] < CORE_B) & (p[:, 0] > CORE_R)
        if core.sum() < 8: core = p[:, 2] <= np.percentile(p[:, 2], 30)
        gold_core = (p[:, 1] / np.maximum(p[:, 0], 1)) < GOLD_GR
        cg, cy_ = (core & gold_core).sum(), (core & ~gold_core).sum()
        if min(cg, cy_) >= 15 and min(cg, cy_) >= 0.15 * core.sum():   # two sparkles touching: split by nearest core colour
            ci = np.nonzero(core)[0]; _, nn = cKDTree(np.c_[xs[ci], ys[ci]]).query(np.c_[xs, ys])
            isg = gold_core[ci][nn]
            for col, sel in (("gold", isg), ("yellow", ~isg)):
                sub = np.zeros_like(m); sub[ys[sel], xs[sel]] = True
                sub = ndi.binary_opening(sub, iterations=1)             # cut the 1-2 px rim strands left on the other motif
                Ls, ns = ndi.label(sub)
                for kk in range(1, ns + 1):
                    yy, xx = np.nonzero(Ls == kk)
                    if len(yy) < 25: continue
                    out.append(dict(k=k, colour=col, xs=xx, ys=yy, cx=float(xx.mean()), cy=float(yy.mean()), split=True))
            continue
        col = "gold" if cg > cy_ else "yellow"
        out.append(dict(k=k, colour=col, xs=xs, ys=ys, cx=float(xs.mean()), cy=float(ys.mean()), split=False))
    return out

SPARK_CELLS = (2.5, 2.0, 1.67, 1.25)   # candidate pixel cells (mm): big sparkles use 2.5, small 4-arm ones need a finer cell
CELL_OK = 0.85                         # the coarsest cell whose staircase reaches this IoU vs the render is used (keeps the
                                       # big sparkles' crisp 2.5 mm pixels); otherwise the best-fitting finer cell

def stair_cells(xs, ys, cells=SPARK_CELLS):
    """best staircase over the candidate cells: the coarsest cell unless a finer one fits the render pixels clearly
    better (a 6 mm 4-arm sparkle on a 2.5 mm grid collapses to a square; PR #28 review)"""
    best = None
    for c in cells:
        g, iou, pix = stair(xs, ys, c)
        if iou >= CELL_OK: return (g, iou, pix, c)
        if best is None or iou > best[1]: best = (g, iou, pix, c)
    return best

SYM_TOL = 0.03      # a sparkle is drawn mirror-symmetric (both axes) when that costs <= this IoU vs the render pixels

def _sym(S):
    """cell set -> its 2-axis mirror-symmetric version: a cell is kept when >= 2 of the 4 mirror images hold it
    (pixel-art sparkles are 4-fold symmetric; the low-res render blurs one rim pixel here and there)"""
    I = [i for i, _ in S]; J = [j for _, j in S]; si, sj = min(I) + max(I), min(J) + max(J)
    cand = S | {(si - i, j) for i, j in S} | {(i, sj - j) for i, j in S} | {(si - i, sj - j) for i, j in S}
    return {(i, j) for i, j in cand if ((i, j) in S) + ((si - i, j) in S) + ((i, sj - j) in S) + ((si - i, sj - j) in S) >= 2}

def stair(xs, ys, cell, search=6, sym=True):
    """pixel mask (render px) -> staircase polygon on its own fitted grid (front mm). Best phase = max IoU vs the
    render mask (the reference is the render's own pixels). With sym, the 2-axis symmetric staircase is used when it
    fits the render within SYM_TOL of the plain one."""
    gx, gy = MM.P(xs + 0.5, ys + 0.5)                                     # pixel centres in mm
    pix = unary_union([box(x - MM.S / 2, y - MM.S / 2, x + MM.S / 2, y + MM.S / 2) for x, y in zip(gx, gy)]).buffer(0)
    best = None; best_s = None
    x0, y0, x1, y1 = pix.bounds
    geo = lambda S, ox, oy: unary_union([box(ox + i * cell, oy + j * cell, ox + (i + 1) * cell, oy + (j + 1) * cell) for i, j in S]).buffer(0)
    for ox in np.arange(0, cell, cell / search):
        for oy in np.arange(0, cell, cell / search):
            S = set()
            for i in range(int(math.floor((x0 - ox) / cell)), int(math.ceil((x1 - ox) / cell)) + 1):
                for j in range(int(math.floor((y0 - oy) / cell)), int(math.ceil((y1 - oy) / cell)) + 1):
                    b = box(ox + i * cell, oy + j * cell, ox + (i + 1) * cell, oy + (j + 1) * cell)
                    if b.intersection(pix).area >= 0.5 * b.area: S.add((i, j))
            if not S: continue
            g = geo(S, ox, oy); iou = g.intersection(pix).area / g.union(pix).area
            if best is None or iou > best[0]: best = (iou, g)
            if sym:
                gs = geo(_sym(S), ox, oy); ious = gs.intersection(pix).area / gs.union(pix).area
                if best_s is None or ious > best_s[0]: best_s = (ious, gs)
    if best_s is not None and best_s[0] >= best[0] - SYM_TOL: best = best_s
    return best[1], best[0], pix

def bird_geom():
    """bird silhouette = the jacquard bird cells (same drawing for option A and B), front mm"""
    import jacquard as JQ
    cells, info = JQ.bird_cells()
    C = JQ.CELL
    g = unary_union([box(i * C, j * C, (i + 1) * C, (j + 1) * C) for i, j in cells]).buffer(0)
    return g, info

def sleeve_xy(px, py, mt, side="L", n=500):
    """front.png px -> sleeve pattern mm (dense forward grid + nearest; mockmap.sleeve_to_img)"""
    from scipy.spatial import cKDTree
    h, Lu, W, Ww = mt["cap_h"], mt["Lu"], mt["W"], mt["Ww"]; sg = 1 if side == "R" else -1
    ys = np.linspace(-h, Lu, n); xs = np.linspace(0, max(W, Ww), n // 2) * sg
    X, Y = np.meshgrid(xs, ys); qx, qy, _ = MM.sleeve_to_img(side, X, Y, mt)
    ok = np.isfinite(qx)
    tree = cKDTree(np.stack([qx[ok], qy[ok]], -1)); _, k = tree.query([px, py])
    return float(X[ok][k]), float(Y[ok][k])

def family_exemplars(comps):
    """the well-resolved sparkles (>= star_fit.SMALL_MM): their tiered drawings (fit_tiers) on a 1 mm matrix, made
    D4-symmetric = the family's drawings for the small sparkles"""
    import star_fit as SF
    exs = []
    for c in comps:
        if (c["xs"].max() - c["xs"].min() + 1) * MM.S < SF.SMALL_MM: continue
        g = SF.fit_tiers(c["xs"], c["ys"])[0]; X = SF.exemplar(g, EX_CELL)
        if not any(x.shape == X.shape and (x == X).all() for x in exs): exs.append(X)
    return exs

EX_CELL = 1.0       # mm, matrix cell of a family exemplar (resampled to N cells for a small sparkle)

SMALL_KMAX = 1      # small sparkles (< star_fit.SMALL_MM): one cross = the plain 4-arm plus. A 2nd tier fitted on a
                    # blur this wide rounds them into stepped octagons/blobs (round 2 check)

def fit_motif(c, exs=None):
    """every sparkle = its own tiered pixel sprite (star_fit.fit_tiers: k concentric crosses with blunt square arms,
    widths/lengths by the blur forward model vs the render). PR #28 round 2: a 2.5 mm staircase drew the big sparkles
    as stepped diamonds, and the resampled family exemplar drew the small ones as round blobs. Big sparkles may use
    free edges (sleeve drape, one arm longer) when that explains the render >= 10 % better; small ones stay 4-fold."""
    import star_fit as SF
    _, _, pix = stair(c["xs"], c["ys"], 2.5, search=1, sym=False)
    big = (c["xs"].max() - c["xs"].min() + 1) * MM.S >= SF.SMALL_MM
    g, err, k, r, tab = SF.fit_tiers(c["xs"], c["ys"], kmax=3 if big else SMALL_KMAX, free_edges=big)
    iou = g.intersection(pix).area / g.union(pix).area
    return g, iou, pix, None, f"own sprite, {k} tier{'s' if k > 1 else ''} ({tab['kind']}, blur-model rmse {err:.3f})"

def ref_pixels(c, level=0.5):
    """A14 reference of a sparkle = its render pixels that are at least half motif colour (star_fit.soft_map >= level).
    The class labels also keep the anti-aliased rim; against the black bird that rim (yellow blended with black) reads
    GOLD, which inflated the wing sparkle's reference to 14 x 15 mm for a ~9.5 mm sparkle (PR #28 fix round)."""
    import star_fit as SF
    s, (x0, y0) = SF.soft_map(c["xs"], c["ys"], pad_px=0)
    own = np.zeros(s.shape, bool); own[c["ys"] - y0, c["xs"] - x0] = True
    yy, xx = np.nonzero((s >= level) & own); xx = xx + x0; yy = yy + y0
    if len(xx) < 5: xx, yy = c["xs"], c["ys"]
    gx, gy = MM.P(xx + 0.5, yy + 0.5)
    return unary_union([box(x - MM.S / 2, y - MM.S / 2, x + MM.S / 2, y + MM.S / 2) for x, y in zip(gx, gy)]).buffer(0)

def build():
    comps = components(); g, mt = FL.draft("M"); exs = None
    files = {"E1": dict(piece="F02", desc="Sparkles, wearer's right front (beside the bird)", parts=[]),
             "E2": dict(piece="F01", desc="Sparkles, wearer's left front", parts=[]),
             "E3": dict(piece="S02", desc="Sparkles, wearer's left sleeve", parts=[])}
    report = []
    for c in comps:
        geom, iou, pix, cell, how = fit_motif(c, exs)
        pix = ref_pixels(c); iou = geom.intersection(pix).area / geom.union(pix).area
        fid = "E1" if c["cx"] < MM.CFX else ("E2" if c["cx"] < 1124 else "E3")
        if fid == "E3":                                                        # move the motif onto the sleeve pattern
            gc = geom.centroid; sx, sy = sleeve_xy(c["cx"], c["cy"], mt, "L")
            geom = affinity.translate(geom, sx - gc.x, sy - gc.y); pix = affinity.translate(pix, sx - gc.x, sy - gc.y)
        files[fid]["parts"].append(dict(colour=c["colour"], geom=geom, ref=pix))
        b = geom.bounds
        report.append(dict(file=fid, colour=c["colour"], render_px=[round(c["cx"]), round(c["cy"])], w_mm=round(b[2] - b[0], 1),
                           h_mm=round(b[3] - b[1], 1), stair_iou_vs_render=round(iou, 3),
                           cell_mm=cell, drawn_as=how, split_from_touching_pair=c["split"]))
    bg, binfo = bird_geom()
    E1 = files["E1"]
    files["E1B"] = dict(piece="F02", desc="Bird + sparkles, wearer's right front (option B: bird embroidered)",
                        parts=[dict(colour="black", geom=bg, ref=None)] + E1["parts"])
    meta = {}
    for fid, F in files.items():
        U = unary_union([p["geom"] for p in F["parts"]]); x0, y0, x1, y1 = U.bounds
        W, H = x1 - x0 + 4, y1 - y0 + 4; ox, oy = x0 - 2, y0 - 2
        layers = []
        order = ["black", "gold", "yellow"]
        for k, col in enumerate([c for c in order if any(p["colour"] == c for p in F["parts"])], 1):
            paths = []
            for p in F["parts"]:
                if p["colour"] != col: continue
                for q in (p["geom"].geoms if p["geom"].geom_type == "MultiPolygon" else [p["geom"]]):
                    d = "M" + " L".join(f"{x - ox:.3f} {y - oy:.3f}" for x, y in list(q.exterior.coords)[:-1]) + " Z"
                    for hole in q.interiors:
                        d += " M" + " L".join(f"{x - ox:.3f} {y - oy:.3f}" for x, y in list(hole.coords)[:-1]) + " Z"
                    paths.append(f'<path d="{d}" fill="{HEX[col]}" fill-rule="evenodd"/>')
            layers.append(f'<g id="{k:02d}_{col}" inkscape:groupmode="layer" inkscape:label="{k:02d}_{col}">' + "".join(paths) + "</g>")
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
               f'width="{W:.3f}mm" height="{H:.3f}mm" viewBox="0 0 {W:.3f} {H:.3f}">' + "".join(layers) + "</svg>")
        open(f"{OUT}/HK-FL-PIXSKY_{fid}_ART.svg", "w").write(svg)
        meta[fid] = dict(piece=F["piece"], desc=F["desc"], svg_origin=[ox, oy], size_mm=[round(W, 2), round(H, 2)],
                         art_bounds=[round(v, 2) for v in (x0, y0, x1, y1)], centre=[round((x0 + x1) / 2, 2), round((y0 + y1) / 2, 2)],
                         motifs={c: sum(1 for p in F["parts"] if p["colour"] == c) for c in order})
    json.dump(dict(files=meta, sparkles=report, bird=binfo), open(f"{OUT}/placements.json", "w"), indent=1)
    import pickle
    pickle.dump({fid: [(p["colour"], p["geom"], p["ref"]) for p in F["parts"]] for fid, F in files.items()}, open(f"{OUT}/art.pkl", "wb"))
    return meta, report, binfo

if __name__ == "__main__":
    meta, rep, bi = build()
    for fid, m in meta.items(): print(fid, m["piece"], m["size_mm"], m["motifs"], "centre", m["centre"])
    print("sparkles", len(rep), "min stair IoU", min(r["stair_iou_vs_render"] for r in rep)); print("bird", bi)
