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

def components():
    """sparkles from the render: [(id, colour, px mask bbox, garment geometry polygon in FRONT coords, centroid px)]"""
    lab = PX.labels(); m = np.isin(lab, [PX.YELLOW, PX.GOLD])
    m = ndi.binary_closing(m, iterations=1)
    L, n = ndi.label(m); out = []
    for k in range(1, n + 1):
        ys, xs = np.nonzero(L == k)
        if len(ys) < 50: continue
        if xs.mean() < 400 and ys.mean() > 1000: continue                 # sleeve fold shading near the body side, not art
        col = "yellow" if (lab[ys, xs] == PX.YELLOW).mean() >= 0.5 else "gold"
        out.append(dict(k=k, colour=col, xs=xs, ys=ys, cx=float(xs.mean()), cy=float(ys.mean())))
    return out

def stair(xs, ys, cell, search=6):
    """pixel mask (render px) -> staircase polygon on its own fitted grid (front mm). Best phase = max IoU vs the
    render mask (the reference is the render's own pixels)"""
    gx, gy = MM.P(xs + 0.5, ys + 0.5)                                     # pixel centres in mm
    pix = unary_union([box(x - MM.S / 2, y - MM.S / 2, x + MM.S / 2, y + MM.S / 2) for x, y in zip(gx, gy)]).buffer(0)
    best = None
    x0, y0, x1, y1 = pix.bounds
    for ox in np.arange(0, cell, cell / search):
        for oy in np.arange(0, cell, cell / search):
            cells = []
            for i in range(int(math.floor((x0 - ox) / cell)), int(math.ceil((x1 - ox) / cell)) + 1):
                for j in range(int(math.floor((y0 - oy) / cell)), int(math.ceil((y1 - oy) / cell)) + 1):
                    b = box(ox + i * cell, oy + j * cell, ox + (i + 1) * cell, oy + (j + 1) * cell)
                    if b.intersection(pix).area >= 0.5 * b.area: cells.append(b)
            if not cells: continue
            g = unary_union(cells).buffer(0)
            iou = g.intersection(pix).area / g.union(pix).area
            if best is None or iou > best[0]: best = (iou, g, ox, oy)
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

def build():
    comps = components(); g, mt = FL.draft("M")
    files = {"E1": dict(piece="F02", desc="Sparkles, wearer's right front (beside the bird)", parts=[]),
             "E2": dict(piece="F01", desc="Sparkles, wearer's left front", parts=[]),
             "E3": dict(piece="S02", desc="Sparkles, wearer's left sleeve", parts=[])}
    report = []
    for c in comps:
        geom, iou, pix = stair(c["xs"], c["ys"], SPARK_CELL)
        fid = "E1" if c["cx"] < MM.CFX else ("E2" if c["cx"] < 1124 else "E3")
        if fid == "E3":                                                        # move the motif onto the sleeve pattern
            gc = geom.centroid; sx, sy = sleeve_xy(c["cx"], c["cy"], mt, "L")
            geom = affinity.translate(geom, sx - gc.x, sy - gc.y); pix = affinity.translate(pix, sx - gc.x, sy - gc.y)
        files[fid]["parts"].append(dict(colour=c["colour"], geom=geom, ref=pix))
        b = geom.bounds
        report.append(dict(file=fid, colour=c["colour"], render_px=[round(c["cx"]), round(c["cy"])], w_mm=round(b[2] - b[0], 1),
                           h_mm=round(b[3] - b[1], 1), stair_iou_vs_render=round(iou, 3)))
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
