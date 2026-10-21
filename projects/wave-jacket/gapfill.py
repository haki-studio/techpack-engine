"""A15 gap fill (PR #27 review, blocker 2): every area >= 25 mm2 that the MOCKUP shows embroidered but the art leaves bare
is filled from the mockup's own pixels there - the same tone classes the gate reads (gates.ref_classes: the render's
tone labels through the art's piece map + seam warp, garment details and keep-outs masked out). Only a gap inside 6 mm of
the spec'd art limit (keep-out edge, < 400 mm2) stays bare.

Per gap (component of ref_any & ~art, opened 1 mm, as qa.uncovered sees it): the gap is grown 1 mm into the art around
it (so the fill overlaps its neighbours and leaves no slit), the tone labels inside are cleaned with a 3x3 majority
(render speckle < 1 mm), and each tone becomes art:
  blues b0-b5  -> stripe (WV, its own thread), MERGED into the touching stripe region of the same thread when there is
                  one (one continuous cord, no new cut line), else a new stripe region (tatami along the band)
  cream w1/w2  -> foam (FM, padded if >= 2.4 mm wide, else satin);  w3 -> foam shade (FM-sh);  g1 -> hollow (FM-gr)
Fills sit UNDER the existing art of their layer (they only cover bare fabric). Nothing is generated: every filled pixel is
a mockup pixel of that tone. Earlier gate versions explained these gaps as 'moved by the wrap'; the review asked for
each to be filled or explained, so they are filled.
usage: ./py.sh gapfill.py [M]   (rewrites art_<size>.pkl after tonematch.py, keeps art_<size>_pregap.pkl; gapfill_<size>.json)"""
import sys
size = next((a for a in sys.argv[1:] if not a.startswith("-")), "M")
sys.argv = [sys.argv[0], "--art"]                      # gates in ART mode: compare against the art, not a DST
import json, os, pickle, shutil
# repeatable: a second run starts again from the pre-gap art (tonematch output), never fills on top of its own fills
if os.path.exists(f"art_{size}_pregap.pkl") and pickle.load(open(f"art_{size}.pkl", "rb"))["info"].get("gapfill"):
    shutil.copy(f"art_{size}_pregap.pkl", f"art_{size}.pkl")
import numpy as np
from scipy import ndimage as ndi
from shapely.ops import unary_union
from shapely import STRtree
import gates as G, qa, wavetrace as WT, waveart as WA, wavecore as WC, trace as TR
from motifs2 import R

assert G.SIZE == size
PPM = G.PPM

def art_cover(P, bb, shape):
    from PIL import Image, ImageDraw
    im = Image.new("L", shape[::-1], 0); d = ImageDraw.Draw(im)
    for r in G.D[P]:
        if r["grp"] in ("FM-loop",): continue
        for q in WA.polys(r["geom"]):
            d.polygon([((x - bb[0]) * PPM, (y - bb[1]) * PPM) for x, y in q.exterior.coords], fill=255)
            for h in q.interiors: d.polygon([((x - bb[0]) * PPM, (y - bb[1]) * PPM) for x, y in h.coords], fill=0)
    return np.asarray(im) > 0

def tone_of(name):
    if name in WT.BLUES: return name, "WV", WC.L_BAND, WA.Z["band"] - 0.01
    if name in ("w1", "w2"): return "w1", "FM", WC.L_FOAM, WA.Z["foam"] - 0.01
    if name == "w3": return "w3", "FM-sh", WC.L_FDET, WA.Z["fdet"] - 0.01
    if name == "g1": return "g1", "FM-gr", WC.L_FDET, WA.Z["fdet"] - 0.01
    return None

def fill_piece(P):
    cls, bb = G.ref_classes(P)
    allart = [WT.NAMES.index(n) for n in WT.CREAM + WT.GREY + WT.BLUES]
    ref_any = ndi.binary_opening(np.isin(cls, allart), iterations=1)
    cov = art_cover(P, bb, cls.shape)
    out_any = ndi.binary_dilation(cov, iterations=int(1.0 * PPM))
    gaps = qa.uncovered(ref_any, out_any, PPM)
    gap_m = ndi.binary_opening(ref_any & ~out_any, structure=qa.disk(1.0, PPM))
    lab, _ = ndi.label(gap_m)
    rows = G.explain_gaps(P, [dict(g) for g in gaps], bb)
    # majority-cleaned tone labels (3x3 = 0.75 mm at 4 ppm)
    lab_cls = cls.copy()
    from scipy.ndimage import generic_filter
    def maj(v):
        v = v[v >= 0].astype(int)
        return np.bincount(v).argmax() if len(v) else -1
    added, filled = [], []
    for g in rows:
        if g["why"] == "keep-out edge": continue
        cx, cy = int((g["x_mm"] - bb[0]) * PPM), int((g["y_mm"] - bb[1]) * PPM)
        win = lab[max(0, cy - int(g["h_mm"] * PPM)):cy + int(g["h_mm"] * PPM) + 1, max(0, cx - int(g["w_mm"] * PPM)):cx + int(g["w_mm"] * PPM) + 1]
        ids = np.unique(win[win > 0])
        if not len(ids): continue
        # the component(s) of this gap row: the biggest label in its box
        k = max(ids, key=lambda i: (win == i).sum())
        m = lab == k
        grow = ndi.binary_dilation(m, iterations=int(1.0 * PPM)) & ref_any         # 1 mm into the neighbours: no slit
        ys, xs = np.nonzero(grow); y0, y1, x0, x1 = ys.min() - 2, ys.max() + 3, xs.min() - 2, xs.max() + 3
        y0, x0 = max(0, y0), max(0, x0)
        sub = np.where(grow[y0:y1, x0:x1], cls[y0:y1, x0:x1], -1)
        sub = generic_filter(sub, maj, size=3, mode="constant", cval=-1)
        sub = np.where(grow[y0:y1, x0:x1], sub, -1)
        n_add = 0
        for t in np.unique(sub[sub >= 0]):
            spec = tone_of(WT.NAMES[int(t)])
            if spec is None: continue
            col, grp, layer, z = spec
            geom = TR.polys_of(sub == t, PPM, (bb[0] + x0 / PPM, bb[1] + y0 / PPM), min_px=1, simplify=0.1)
            for p in WA.polys(geom):
                if p.area < 1.5 or p.buffer(-0.35).is_empty: continue
                st = "tatami" if grp == "WV" else ("padded" if grp == "FM" and WA.width(p) >= 2.4 else "satin")
                rec = dict(R(col, p, st, "auto", grp), z=z, unit=None, layer=layer, gen="gap fill (mockup pixels)")
                added.append(rec); n_add += 1
        filled.append(dict(x_mm=g["x_mm"], y_mm=g["y_mm"], area_mm2=g["area_mm2"], was=g["why"], regions=n_add))
    # fills join the art around them (one continuous cord per stripe, as tonematch.band_clean does for the trace):
    #  - a fill touching a region of the SAME thread + group is merged into it;
    #  - a small fill (< SMALL_MM2) touching a region of the same group in another thread takes that region's thread and
    #    merges (render shading inside one stripe / crest, not design);
    #  - otherwise it stays its own region.
    SMALL_MM2 = 150.0
    same = lambda a, r: r["grp"] == a["grp"] and not r.get("unit")
    pool = [r for r in G.D[P] if r["grp"] in ("WV", "FM", "FM-sh", "FM-gr") and not r.get("unit")]
    keep = []
    for a in sorted(added, key=lambda r: -r["geom"].area):
        tree = STRtree([r["geom"] for r in pool]) if pool else None
        hit = [pool[int(j)] for j in tree.query(a["geom"].buffer(0.3))] if tree is not None else []
        hit = [r for r in hit if same(a, r) and r["geom"].buffer(0.3).intersects(a["geom"])]
        best = None
        sh = lambda r: r["geom"].buffer(0.4).intersection(a["geom"].boundary).length
        h1 = [r for r in hit if r["col"] == a["col"]]
        if h1: best = max(h1, key=sh)
        elif hit and a["geom"].area < SMALL_MM2: best = max(hit, key=sh)
        if best is not None and sh(best) > 0.5:
            best["geom"] = unary_union([best["geom"], a["geom"]]).buffer(0); best["gapfill"] = True; continue
        keep.append(a); pool.append(a)
    # foam fills get the house foam structure (A16, review item 4): each connected cream / grey cluster is one curl unit
    # (rows along the curl around its eye, waveart.curl_direction) with the loop spiral on its padded foam
    n_merged = len(added) - len(keep)
    foam = [a for a in keep if a["grp"] in ("FM", "FM-sh", "FM-gr")]
    if foam:
        U = unary_union([a["geom"].buffer(0.2) for a in foam]); cl = WA.polys(U)
        for a in foam:
            c = a["geom"].representative_point()
            a["unit"] = f"gapfill:{P}:{next((i for i, q in enumerate(cl) if q.contains(c)), 0)}"
        rest = [a for a in keep if a not in foam]
        foam = WA.curl_direction(foam)
        loops = []
        for a in foam:
            if a["grp"] == "FM" and a["st"] == "padded":
                for lp in WA.loops_for(a["geom"]):
                    for q in WA.polys(lp.intersection(a["geom"].buffer(-0.3))):
                        if q.area > 0.5: loops.append(dict(R("w3", q, "run", None, "FM-loop"), z=WA.Z["foam"] + 0.5, unit=a["unit"], gen=a["gen"]))
        keep = rest + foam + loops
        for a in keep: a["layer"] = WA.layer_of(a)
    G.D[P] += keep
    return dict(piece=P, gaps=len(rows), filled=len(filled), regions_added=len(added), merged_into_stripes=n_merged, regions_kept=len(keep),
                kept_bare=[(g["x_mm"], g["y_mm"], g["area_mm2"]) for g in rows if g["why"] == "keep-out edge"], detail=filled)

if __name__ == "__main__":
    src, bak = f"art_{size}.pkl", f"art_{size}_pregap.pkl"
    shutil.copy(src, bak)
    log = [fill_piece(P) for P in WC.PIECES]
    for l in log: print(l["piece"], {k: l[k] for k in ("gaps", "filled", "regions_added", "merged_into_stripes")}, flush=True)
    G.D["info"]["gapfill"] = [{k: l[k] for k in ("piece", "gaps", "filled", "regions_added", "merged_into_stripes")} for l in log]
    pickle.dump(G.D, open(src, "wb"))
    json.dump(log, open(f"gapfill_{size}.json", "w"), indent=1, default=float)
