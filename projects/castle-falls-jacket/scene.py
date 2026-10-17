"""Scene per piece, size M, unclipped (with bleed past the M keep-outs so graded sizes still reach theirs).
  1. trace.tone_map(P): every mockup pixel -> thread tone / fabric (tonal trace, fidelity first)
  2. FL only — IP edits (brief: original castle + tree): the left half of the tree's ring and the fall straight under
     the castle are removed (filled from the tones around them), the castle is redrawn (cf_motifs.castle) on a stone base
  3. each tone component -> a region: tatami with the tone class's stitch angle, small/narrow parts satin
  4. overlays: cherry florets packed on the blossom ground, falling petals redrawn as petals
usage: python3 scene.py [P ...]  -> scene_<P>.pkl {"items": [...], "info": {...}}  + out/art/scene_<P>.png"""
import cfcore
import os, sys, math, pickle, random, time
import numpy as np
from scipy import ndimage as ndi
from skimage import measure
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
import trace as TRC, mockmap as MM, cf_motifs as CM

TI, TONES = TRC.TI, TRC.TONES
CLASS = {"cf_white": "cloud", "cf_cream": "cloud", "cf_mist": "cloud", "cf_skylt": "sky", "cf_sky": "sky", "cf_navy": "sky",
         "cf_slate": "rock", "cf_lav": "rock", "cf_grndk": "fol", "cf_grn": "fol", "cf_grnlt": "fol",
         "cf_pinklt": "bl", "cf_pink": "bl", "cf_rose": "bl", "cf_red": "bld", "cf_gold": "bld", "cf_bark": "trk", "cf_brown": "trk"}
GRP = {"cloud": "CL", "sky": "SKY", "rock": "RK", "fol": "FOL", "bl": "BLB", "bld": "TMB", "trk": "TRK"}
# waterfall zones, flat.png px boxes (x0, y0, x1, y1): light tones inside sew as vertical streaks
FALLS = {"BK": [(768 + 205, 350, 768 + 262, 508), (768 + 293, 428, 768 + 332, 518)],
         "FL": [(416, 440, 568, 596)], "FR": [], "SR": [], "SL": []}
FALL_TONES = {"cf_white", "cf_cream", "cf_mist", "cf_skylt", "cf_sky"}

def px_to_mm_grid(res):
    x0, y0 = res["bbox"][0], res["bbox"][1]; ppm = res["ppm"]
    return lambda c, r: (x0 + (c + 0.5) / ppm, y0 + (r + 0.5) / ppm)

def mm_to_px(P, x, y):
    if P == "BK": return MM.body_px("B", x, y)
    if P in ("FR", "FL"): return MM.body_px("F", x, y)
    v, px, py = MM.sleeve_px(P, x, y); return px, py

def zone_mask(res, P, boxes):
    t = res["t"]; H, W = t.shape; m = np.zeros((H, W), bool)
    if not boxes: return m
    ys, xs = np.mgrid[0:H:3, 0:W:3]; f = px_to_mm_grid(res)
    X, Y = f(xs, ys)
    PX, PY = mm_to_px(P, X, Y) if P in ("BK", "FR", "FL") else (None, None)
    sub = np.zeros(xs.shape, bool)
    for b in boxes: sub |= (PX >= b[0]) & (PX <= b[2]) & (PY >= b[1]) & (PY <= b[3])
    m = np.kron(sub, np.ones((3, 3), bool))[:H, :W]
    return m

def refill(t, where, exclude):
    """pixels in `where` take the nearest tone outside `where` that is not in `exclude` (nearest-tone fill)"""
    src = ~where & ~np.isin(t, list(exclude)) & (t >= 0)
    _, (iy, ix) = ndi.distance_transform_edt(~src, return_indices=True)
    return np.where(where, t[iy, ix], t)

def comp_polys(mask, f, ppm, min_area=2.0):
    """connected components of a binary mask -> shapely polygons (even-odd nesting of the contours)"""
    lab, n = ndi.label(mask); out = []
    for i, s in enumerate(ndi.find_objects(lab), 1):
        m = np.pad(lab[s] == i, 1)
        if m.sum() < min_area * ppm * ppm: continue
        g = Polygon()
        for c in measure.find_contours(m.astype(np.float32), 0.5):
            if len(c) < 4: continue
            pts = [f(s[1].start + x - 1, s[0].start + y - 1) for y, x in c]
            p = Polygon(pts).buffer(0)
            if not p.is_empty: g = g.symmetric_difference(p)
        g = g.simplify(0.18).buffer(0)
        if not g.is_empty and g.area >= min_area: out.append(g)
    return out

def build(P):
    t0 = time.time(); rng = random.Random(7 + cfcore.PIECES.index(P))
    res = TRC.tone_map(P); t = res["t"].astype(int).copy(); ppm = res["ppm"]; f = px_to_mm_grid(res)
    H, W = t.shape; items = []; info = dict(P=P)
    ys_, xs_ = np.mgrid[0:H, 0:W]
    def add(regs, layer, z0=0):
        for r in regs:
            if r["geom"] is None or r["geom"].is_empty: continue
            r = dict(r); r["layer"] = layer; r["z"] = layer * 1_000_000 + len(items) + z0
            r.setdefault("ko", True); r.setdefault("unit", None); items.append(r)
    knock = Polygon()
    if P == "FL":
        X, Y = f(xs_, ys_); PX, PY = MM.body_px("F", X, Y)
        trunk = np.isin(t, [TI["cf_bark"], TI["cf_brown"]])
        ring_left = trunk & (PX < 474) & (PY > 212) & (PY < 350)          # left half of the tree ring -> sky / cloud / canopy
        t = refill(t, ring_left, {"cf_bark", "cf_brown"})
        fc_t = FALL_TONES | {"cf_navy", "cf_slate"}
        fall_c = (PX > 492) & (PX < 526) & (PY > 444) & (PY < 530) & np.isin(t, [TI[k] for k in fc_t])
        t = refill(t, fall_c, fc_t)                                  # no fall straight under the castle
        info["ip_edit_px"] = int(ring_left.sum() + fall_c.sum())
        regs, knock, base_bot = CM.castle(108.0, 171.0)
        # the mockup castle (gold horns, roofs, red balcony) is erased everywhere outside the new castle: sky/cloud behind it
        from shapely.prepared import prep
        mock_castle = (PX > 420) & (PX < 578) & (PY > 270) & (PY < 456)
        bld = {"cf_navy", "cf_white", "cf_red", "cf_gold", "cf_bark", "cf_brown", "cf_slate", "cf_rose", "cf_pink", "cf_pinklt", "cf_mist"}
        kn = np.zeros_like(mock_castle)
        kb = knock.bounds; sub = (X > kb[0]) & (X < kb[2]) & (Y > kb[1]) & (Y < kb[3])
        pk = prep(knock); idx = np.nonzero(sub)
        kn[idx] = [pk.contains(Point(a, b_)) for a, b_ in zip(X[idx][::1], Y[idx][::1])]
        t = refill(t, mock_castle & ~kn & (np.isin(t, [TI[k] for k in bld | {"cf_grn", "cf_grndk", "cf_grnlt"}]) | (t < 0)), bld | {"cf_grn", "cf_grndk", "cf_grnlt"})
        horns = (PX > 452) & (PX < 548) & (PY > 272) & (PY < 304) & ~kn & (t >= 0) & ~np.isin(t, [TI["cf_sky"], TI["cf_skylt"], TI["cf_cream"]])
        t = refill(t, horns, bld | {"cf_grn", "cf_grnlt", "cf_grndk"})
        add(regs, 21)
    fz = zone_mask(res, P, FALLS[P])
    # ---- traced regions
    for k in TONES:
        mask = t == TI[k]
        if not mask.any(): continue
        cls = CLASS[k]
        for kind, m in (("fall", mask & fz), ("main", mask & ~fz)) if k in FALL_TONES else (("main", mask),):
            if not m.any(): continue
            for g in comp_polys(m, f, ppm):
                if not knock.is_empty:
                    g = g.difference(knock).buffer(0)
                    if g.is_empty or g.area < 2.0: continue
                A = g.area; w = 2 * A / max(g.length, 1e-6)
                if kind == "fall":
                    r = CM.R(k, g, "tatami", 90.0 + rng.uniform(-4, 4), "FALL")
                elif w < 2.0 and A < 70:
                    r = CM.R(k, g, "satin", "auto", "TMB" if cls == "bld" else GRP[cls])
                else:
                    ang = {"sky": rng.uniform(-8, 8), "cloud": rng.uniform(-28, 28), "rock": 90 + rng.uniform(-16, 16),
                           "fol": rng.uniform(0, 180), "bl": rng.uniform(0, 180), "bld": "auto", "trk": rng.uniform(40, 140)}[cls]
                    r = CM.R(k, g, "tatami", ang, "VIL" if cls == "bld" else GRP[cls])
                add([r], 11)
    # ---- blossom florets on the blossom ground (overlay), counted from the ground area (~1 floret per 22 mm2)
    blm = np.isin(t, [TI["cf_pinklt"], TI["cf_pink"], TI["cf_rose"]])
    lab_, n = ndi.label(blm); sizes = ndi.sum(blm, lab_, np.arange(1, n + 1)) / ppm ** 2 if n else []
    big = np.isin(lab_, np.nonzero(np.array(sizes) >= 40)[0] + 1) if n else blm & False
    ground = unary_union(comp_polys(big, f, ppm, 30)) if big.any() else Polygon()
    if not knock.is_empty: ground = ground.difference(knock)
    nflor = 0; placed = []
    if not ground.is_empty:
        inner = ground.buffer(-1.2); b = inner.bounds; step = 4.6
        y = b[1]; row = 0
        from shapely.prepared import prep
        pin = prep(inner)
        while y < b[3]:
            x = b[0] + (step / 2 if row % 2 else 0)
            while x < b[2]:
                cx, cy = x + rng.uniform(-1.0, 1.0), y + rng.uniform(-1.0, 1.0)
                if pin.contains(Point(cx, cy)):
                    c, r_ = int((cx - res["bbox"][0]) * ppm), int((cy - res["bbox"][1]) * ppm)
                    tone = TONES[t[min(H - 1, r_), min(W - 1, c)]] if t[min(H - 1, r_), min(W - 1, c)] >= 0 else "cf_pink"
                    col = {"cf_rose": "cf_pink", "cf_pink": "cf_pinklt", "cf_pinklt": "cf_pinklt"}.get(tone, "cf_pink")
                    if tone == "cf_pinklt" and rng.random() < 0.35: col = "cf_white"
                    d = rng.uniform(3.6, 5.6)
                    add(CM.floret(cx, cy, d, rng.uniform(0, 72), col, "cf_rose" if col != "cf_white" else "cf_pink", unit=f"fl{nflor}"), 17)
                    nflor += 1
                x += step
            y += step * 0.866; row += 1
    info["florets"] = nflor
    # ---- falling petals: small pink islands on fabric / sky are redrawn as petals (replacing the traced blob)
    npet = 0
    if n:
        for i, s in enumerate(ndi.find_objects(lab_), 1):
            if sizes[i - 1] >= 40 or sizes[i - 1] < 2.0: continue
            ys2 = slice(max(0, s[0].start - 4), s[0].stop + 4); xs2 = slice(max(0, s[1].start - 4), s[1].stop + 4)
            m = lab_[ys2, xs2] == i; ring = ndi.binary_dilation(m, iterations=3) & ~m
            around = t[ys2, xs2][ring]
            if not ((around == -1) | np.isin(around, [TI["cf_sky"], TI["cf_navy"], TI["cf_skylt"], TI["cf_slate"]])).mean() > 0.6: continue
            rr, cc = np.nonzero(m); cy_, cx_ = rr.mean() + ys2.start, cc.mean() + xs2.start
            cx, cy = f(cx_, cy_)
            cov = np.cov(np.stack([cc, rr])) if len(rr) > 2 else np.eye(2)
            ev, evec = np.linalg.eigh(cov); ang = math.degrees(math.atan2(evec[1, 1], evec[0, 1]))
            L = max(3.2, min(5.6, 2.1 * math.sqrt(sizes[i - 1])))
            lum = np.mean([{"cf_pinklt": 2, "cf_pink": 1, "cf_rose": 0}[TONES[v]] for v in t[ys2, xs2][m]])
            col = "cf_pinklt" if lum > 1.3 else "cf_pink"
            blob = Point(cx, cy).buffer(math.sqrt(sizes[i - 1] / math.pi) + 0.8)
            for r in items:
                if r["layer"] == 11 and r["col"] in ("cf_pinklt", "cf_pink", "cf_rose") and r["geom"].intersects(blob) and r["geom"].area < 45:
                    r["geom"] = r["geom"].difference(blob)
            add(CM.petal(cx, cy, L, ang, col, unit=f"pt{npet}"), 20); npet += 1
    info["petals"] = npet
    items = [r for r in items if not r["geom"].is_empty and r["geom"].area > 0.3]
    info.update(objects=len(items), secs=round(time.time() - t0))
    pickle.dump({"items": items, "info": info, "bbox": res["bbox"]}, open(f"scene_{P}.pkl", "wb"))
    print(P, info, flush=True)
    return items

def preview(P, ppm=2.0):
    import stitchrender as SR
    D = pickle.load(open(f"scene_{P}.pkl", "rb")); b = D["bbox"]
    vis = visible(D["items"])
    SR.render(vis, b, ppm, base=cfcore.FABRIC).save(f"out/art/scene_{P}.png")

def visible(items, clip=None):
    """z-ordered knockout: higher z covers lower unless ko=False (overlays sit on top without cutting)"""
    import shapely
    its = sorted([r for r in items if clip is None or r["geom"].intersects(clip)], key=lambda r: -r["z"])
    ko = [r for r in its if r.get("ko", True)]
    tree = shapely.STRtree([r["geom"] for r in ko]); zs = np.array([r["z"] for r in ko])
    out = []
    for r in its:
        g = r["geom"] if clip is None else r["geom"].intersection(clip)
        if g.is_empty: continue
        hits = [int(j) for j in tree.query(g, predicate="intersects") if zs[int(j)] > r["z"]]
        if hits:
            g = g.difference(unary_union([ko[j]["geom"] for j in hits]))
        g = g.buffer(0)
        if not g.is_empty and g.area > 0.2: out.append(dict(r, geom=g))
    out.reverse(); return out

if __name__ == "__main__":
    os.makedirs("out/art", exist_ok=True)
    for P in sys.argv[1:] or cfcore.PIECES:
        build(P); preview(P)
