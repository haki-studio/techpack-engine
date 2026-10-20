"""Scene per piece, size M, unclipped (with bleed past the M keep-outs so graded sizes still reach theirs).
  1. trace.tone_map(P): every mockup pixel -> thread tone / fabric (tonal trace, fidelity first)
  2. FL only — IP edits (brief: original castle + tree): the left half of the tree's ring and the fall straight under
     the castle are removed (filled from the tones around them), the castle is redrawn (cf_motifs.castle) on a stone base
  3. each tone component -> a region: tatami with the tone class's stitch angle, small/narrow parts satin
  4. overlays: cherry florets packed on the blossom ground, falling petals redrawn as petals
  Rev B (review, LESSONS A13 — structure, not only tones): continuous stitched sky inside the art (no bare-shell holes),
  clouds as lobes (lit rim / body / shaded underside, rows fanned per lobe), pine crowns as leaf clumps, rock + trunk regions
  sewn along the mockup's own stroke direction (structure tensor) with strata / bark lines, waterfalls as rope cords with a
  mist foot, buildings as objects (castle, karamon gate, pagoda, gate tower, village houses), the FR spire crag redrawn
usage: python3 scene.py [P ...]  -> scene_<P>.pkl {"items": [...], "info": {...}}  + out/art/scene_<P>.png"""
import cfcore
import os, sys, math, pickle, random, time
import numpy as np
from scipy import ndimage as ndi
from skimage import measure
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union
import trace as TRC, mockmap as MM, cf_motifs as CM, cf_motifs2 as M2

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


# ---------------------------------------------------------------- Rev B structure (review Rev A items 1-11)
# objects drawn per piece, mm on the size-M piece, measured on the registered close-up composite (gridwarp.py)
FALL_ZONE = {   # mm polygons where the close-up shows falls (the silhouette inside is traced)
 "FL": [[(0, 318), (205, 318), (205, 470), (0, 470)]],
 "BK": [[(-205, 320), (-120, 320), (-120, 485), (-205, 485)], [(-72, 400), (-32, 400), (-32, 488), (-72, 488)]],
 "SL": [[(92, 130), (158, 130), (158, 308), (92, 308)]], "FR": [], "SR": []}
# traced buildings: (motif fn, args, zone polygon) — the generated geometry only supplies structure overlays (ribs, eave
# lines, studs, windows, shachi), clipped to the traced silhouette
BUILDINGS = {
 "FL": {"castle": (M2.castle2, (108.0, 168.0), [(0, 140), (215, 140), (215, 330), (0, 330)]),
        "karamon": (M2.karamon, (103.0, 415.0, 150.0, 85.0), [(20, 400), (190, 400), (190, 505), (20, 505)])},
 "FR": {"pagoda": (M2.pagoda, (-147.0, 206.0, [(267, 284, 62, 300, 34), (301, 314, 70, 330, 36), (331, 346, 79, 364, 40)]), None)}}
GENERATED = {"SL": {"gate tower": (M2.gate_tower, (-150.0, 228.0))}}   # in the front mockup only (no close-up shows it)
CRAG = {"FR": [(-96, 50), (-84, 58), (-70, 110), (-55, 160), (-42, 230), (-32, 300), (-60, 310), (-100, 300), (-118, 240), (-114, 160), (-108, 100)]}
VILLAGE = {"BK": [(-205, 478, 135, 568)], "FR": [(-300, 405, -60, 512)], "FL": [(0, 478, 40, 512)], "SR": [], "SL": []}
CLOUD_T = ("cf_white", "cf_cream", "cf_mist")
FOL_T = ("cf_grndk", "cf_grn", "cf_grnlt")

def _poly_tone(t, g, to_px, keys, default):
    b = g.bounds; vals = []
    for x in np.linspace(b[0], b[2], 5):
        for y in np.linspace(b[1], b[3], 5):
            c, r = to_px(x, y)
            if 0 <= r < t.shape[0] and 0 <= c < t.shape[1] and t[r, c] >= 0 and TONES[t[r, c]] in keys: vals.append(TONES[t[r, c]])
    return max(set(vals), key=vals.count) if vals else default

def long_axis(g):
    mr = g.minimum_rotated_rectangle; c = list(mr.exterior.coords)
    e = max(((c[i], c[i + 1]) for i in range(4)), key=lambda e: math.hypot(e[1][0] - e[0][0], e[1][1] - e[0][1]))
    return math.degrees(math.atan2(e[1][1] - e[0][1], e[1][0] - e[0][0])) % 180

def zone_style(ztype, k, q, rng, info):
    """traced region inside a building / village zone -> its own object with the structure's stitch direction (A13/A14)"""
    A = q.area; w = 2 * A / max(q.length, 1e-6); thin = w < 2.0 and A < 70
    if k in ("cf_navy", "cf_sky", "cf_skylt"):                  # roofs: rows along the ridge (village) / down the slope (castle)
        ang = long_axis(q) if ztype == "vil" else 90.0
        out = [CM.R(k, q, "satin" if thin else "tatami", "auto" if thin else ang, "ROOF")]
        if ztype == "vil" and A > 12:
            out += M2.strata(q, ang, 1.7, ["cf_sky" if k == "cf_navy" else "cf_navy"], "ROOF-ln", w=0.33, inset=0.6, min_len=2.0)
            info["houses"] = info.get("houses", 0) + 1
        return out
    if k in ("cf_white", "cf_cream", "cf_mist"):
        return [CM.R(k, q, "satin" if thin else "tatami", "auto" if thin else 0.0, "WALL")]
    if k in ("cf_red", "cf_bark", "cf_brown"):
        return [CM.R(k, q, "satin" if thin else "tatami", "auto" if thin else (0.0 if ztype == "bld" else 90.0), "TMB")]
    if k == "cf_gold":
        return [CM.R(k, q, "satin" if thin else "tatami", "auto" if thin else 0.0, "ORN")]
    cls = CLASS[k]
    return [CM.R(k, q, "satin" if thin else "tatami", "auto" if thin else rng.uniform(0, 180), GRP[cls])]

def silhouette(t, f, ppm, zone, tones, open_mm=0.8, min_mm2=20.0, close_mm=0.0):
    """traced pixels of the given tones inside zone -> cleaned polygons (the motif silhouettes, LESSONS A14)"""
    H, W = t.shape; X_, Y_ = f(np.arange(W)[None, :].repeat(H, 0), np.arange(H)[:, None].repeat(W, 1))
    from shapely import contains_xy
    m = contains_xy(zone, X_, Y_) & np.isin(t, [TI[k] for k in tones])
    if close_mm: m = ndi.binary_closing(m, structure=TRC.disk(close_mm)) & contains_xy(zone, X_, Y_)
    m = ndi.binary_opening(m, structure=TRC.disk(open_mm))
    return [g for g in comp_polys(m, f, ppm, min_mm2)]

def revb_structure(P, res, t, f, rng, add, knock):
    ppm = res["ppm"]; H, W = t.shape; info = {}
    to_px = lambda x, y: (int((x - res["bbox"][0]) * ppm), int((y - res["bbox"][1]) * ppm))
    Wp = pickle.load(open("warps_M.pkl", "rb"))[P][1]
    field = M2.dir_field(Wp[:H, :W], ppm)
    # 1. sky: bare shell enclosed by the art becomes stitched deep-navy sky (continuous textured fill, item 6)
    art = t >= 0
    env = ndi.binary_fill_holes(ndi.binary_closing(art, structure=TRC.disk(24.0), iterations=1)) & ndi.binary_erosion(np.ones_like(art), iterations=2)
    hole = env & ~art
    t = t.copy(); t[hole] = TI["cf_navy"]; info["sky_fill_mm2"] = round(float(hole.sum()) / ppm ** 2)
    # 1a. Deep navy only in thin traced crevices / shadow lines (founder 19 Oct: thick navy patches read as bare shell).
    #     Thick navy (survives a 2.4 mm opening) outside buildings / village takes the tone of its context: rock -> slate,
    #     sky / cloud -> sky blue (the darkest 25 % of it, by close-up luminance, stays navy as darker sky passages),
    #     foliage -> pine dark.
    H_, W_ = t.shape; X_, Y_ = f(np.arange(W_)[None, :].repeat(H_, 0), np.arange(H_)[:, None].repeat(W_, 1))
    from shapely import contains_xy
    keep = np.zeros_like(art)
    for fn, args, _ in BUILDINGS.get(P, {}).values(): keep |= contains_xy(fn(*args)[1].buffer(2.0), X_, Y_)
    for z in VILLAGE.get(P, []): keep |= contains_xy(box(*z), X_, Y_)
    for g_ in GENERATED.get(P, {}).values(): keep |= contains_xy(g_[0](*g_[1])[1].buffer(2.0), X_, Y_)
    navy = (t == TI["cf_navy"]) & ~keep
    thick = ndi.binary_dilation(ndi.binary_opening(navy, structure=TRC.disk(2.4)), structure=TRC.disk(0.6)) & navy
    lab_t, nt = ndi.label(thick)
    L_ = Wp[:H_, :W_] @ np.array([0.3, 0.59, 0.11])
    CTX = {"rock": "cf_slate", "sky": "cf_sky", "cloud": "cf_sky", "fol": "cf_grndk", "trk": "cf_slate", "bl": "cf_sky", "bld": "cf_navy"}
    moved = 0
    for i, sl in enumerate(ndi.find_objects(lab_t), 1):
        ys = slice(max(0, sl[0].start - 6), sl[0].stop + 6); xs = slice(max(0, sl[1].start - 6), sl[1].stop + 6)
        m = lab_t[ys, xs] == i; ring = ndi.binary_dilation(m, iterations=6) & ~m
        nb = t[ys, xs][ring]; nb = nb[(nb >= 0) & (nb != TI["cf_navy"])]
        if not len(nb): ctx = "sky"
        else:
            cl = [CLASS[TONES[v]] for v in nb]; ctx = max(set(cl), key=cl.count)
        new = CTX.get(ctx, "cf_sky")
        if new == "cf_navy": continue
        sub = t[ys, xs]
        if new == "cf_sky":
            lv = L_[ys, xs][m]; thr = np.percentile(lv, 25)
            sub[m & (L_[ys, xs] > thr)] = TI["cf_sky"]
        else:
            sub[m] = TI[new]
        moved += int(m.sum())
    info["navy_reassigned_mm2"] = round(moved / ppm ** 2)
    # 1b. FR spire crag (item 11): cloud-white strata inside the crag are rock highlights, not clouds
    crag = Polygon(CRAG[P]) if P in CRAG else Polygon()
    if not crag.is_empty:
        X_, Y_ = f(np.arange(W)[None, :].repeat(H, 0), np.arange(H)[:, None].repeat(W, 1))
        from shapely import contains_xy
        inc = contains_xy(crag, X_, Y_)
        for a_, b_ in (("cf_white", "cf_mist"), ("cf_cream", "cf_mist"), ("cf_navy", "cf_slate")):
            t[inc & (t == TI[a_])] = TI[b_]
        t[inc & (t < 0)] = TI["cf_slate"]
    BO = unary_union([fn(*args)[1].buffer(2.0) for fn, args, _ in BUILDINGS.get(P, {}).values()] + [box(*z) for z in VILLAGE.get(P, [])]) if (BUILDINGS.get(P) or VILLAGE.get(P)) else Polygon()
    # 2. clouds -> lobes (lit rim / body / shaded underside, rows fanned per lobe; item 5)
    nl = 0
    cm = np.isin(t, [TI[k] for k in CLOUD_T])
    for C in comp_polys(cm, f, ppm, 20.0):
        C = C.difference(BO).buffer(0)
        if C.is_empty or C.area < 20: continue
        R0 = max(2.6, min(5.2, math.sqrt(C.area) / 4.5))
        lobes = M2.pack_lobes(C, R0, rng)
        def tn(l, C=C):
            body = _poly_tone(t, Point(l[0], l[1]).buffer(l[2] * 0.7), to_px, CLOUD_T, "cf_cream")
            return {"cf_white": ("cf_white", None, "cf_mist"), "cf_cream": ("cf_cream", "cf_white", "cf_mist"),
                    "cf_mist": ("cf_mist", "cf_cream", "cf_slate")}[body]
        regs, _ = M2.lobe_regions(lobes, tn, C=C, grp="CL")          # lobes inside the traced outline (A14)
        add(regs, 12); nl += len(lobes)
    info["cloud_lobes"] = nl
    # 3. foliage / pine crowns -> leaf clumps with dark clump edges (item 8)
    nf = 0
    fm = np.isin(t, [TI[k] for k in FOL_T])
    for C in comp_polys(fm, f, ppm, 25.0):
        C = C.difference(BO).buffer(0)
        if C.is_empty or C.area < 25: continue
        lobes = M2.pack_lobes(C, 3.1, rng, rjit=0.28, dy=0.7, dx=1.1, rmin=1.8)
        def tf(l):
            body = _poly_tone(t, Point(l[0], l[1]).buffer(l[2] * 0.7), to_px, FOL_T, "cf_grn")
            return {"cf_grnlt": ("cf_grnlt", None, "cf_grn"), "cf_grn": ("cf_grn", "cf_grnlt", "cf_grndk"), "cf_grndk": ("cf_grndk", "cf_grn", "cf_grndk")}[body]
        regs, _ = M2.lobe_regions(lobes, tf, C=C, grp="FOL", ex=1.1, ey=0.85)
        add(regs, 15); nf += len(lobes)
    info["foliage_clumps"] = nf
    zones = []
    # 4. waterfalls: silhouette traced from the close-up (fall tones inside the fall zone), filled with rope cords (item 7, A14)
    nf_ = 0
    for Z in FALL_ZONE.get(P, []):
        Z = Polygon(Z) if not hasattr(Z, "area") else Z
        for g in silhouette(t, f, ppm, Z, ("cf_white", "cf_cream", "cf_skylt"), open_mm=1.0, min_mm2=30.0, close_mm=2.0):
            b_ = g.bounds
            if (b_[3] - b_[1]) < 1.6 * (b_[2] - b_[0]) and g.area < 300: continue      # falls are tall streams
            add(M2.fall_in(g, rng), 16); knock = knock.union(g.buffer(0.2)); nf_ += 1
    info["falls"] = nf_
    # 5. buildings: traced silhouette (zone styling) + structure overlays clipped to it; generated only where no reference
    for name, (fn, args, Zp) in BUILDINGS.get(P, {}).items():
        _o = fn(*args); regs, O = _o[0], _o[1]
        Z = Polygon(Zp).intersection(O.buffer(2.0)) if Zp else O.buffer(2.0)
        sky = unary_union(silhouette(t, f, ppm, Z, ("cf_sky", "cf_skylt"), open_mm=0.6, min_mm2=6.0)) if True else Polygon()
        S = Z.difference(sky).buffer(0)
        zones.append(("bld", S))
        ov = [dict(r, ko=False, geom=r["geom"].intersection(S.buffer(-0.3)).buffer(0)) for r in regs
              if not (r["st"] == "tatami" and r["geom"].area > 40)]
        add([r for r in ov if not r["geom"].is_empty and r["geom"].area > 0.3], 19)
        info.setdefault("buildings_traced", []).append(name)
    for name, (fn, args) in GENERATED.get(P, {}).items():          # no reference pixels (not in any close-up): generated object
        regs, k = fn(*args); add([r for r in regs if r.get("ko", True)], 18); add([r for r in regs if not r.get("ko", True)], 19)
        knock = knock.union(k); info.setdefault("generated", []).append(name)
    # 6. village: every traced roof / wall / lintel region in the zone is its own object (item 4, A14)
    for Zb in VILLAGE.get(P, []): zones.append(("vil", box(*Zb)))
    info["houses"] = 0
    return dict(t=t, knock=knock, info=info, field=field, zones=zones)

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
        # Rev B (founder 19 Oct: follow the reference composition): castle on the falls rock as in the close-up / reference —
        # 3 tiers, gold shachi + studs, lantern band, red balustrade; karamon gate at the foot. Drawn as objects over the trace.
        pass        # castle + karamon: traced silhouette + structure overlays (revb_structure, LESSONS A14)
    if P in ("SR", "SL"):
        # the centre fold is the flat-lay silhouette edge in both views (dark shading, read as bare shell): where the art
        # runs on both sides of the fold, the fold strip takes the tones beside it (the top of the arm is not a seam)
        X, Y = f(xs_, ys_); strip = np.abs(X) < 16
        art = t >= 0
        cols_l = (X > -26) & (X < -16); cols_r = (X > 16) & (X < 26)
        rowl = (art & cols_l).sum(1) > 0.5 * cols_l.sum(1).clip(1); rowr = (art & cols_r).sum(1) > 0.5 * cols_r.sum(1).clip(1)
        rows = ndi.binary_closing(rowl & rowr, iterations=4)
        edge = (t < 0) | (t == TI["cf_navy"])          # the silhouette shading reads as shell or as deep navy
        fold = strip & edge & rows[:, None]
        t = refill(t, fold, {"cf_navy"}); info["fold_fill_px"] = int(fold.sum())
        # hairline seam between the two halves (the two views meet at x = 0): close it wherever both sides are art
        art = t >= 0; nl = (art & (X > -6) & (X < -2)).sum(1) > 0; nr = (art & (X > 2) & (X < 6)).sum(1) > 0
        hair = (np.abs(X) < 2.5) & (t < 0) & (nl & nr)[:, None]
        t = refill(t, hair, set()); info["fold_fill_px"] += int(hair.sum())
    fz = zone_mask(res, P, FALLS[P])
    rev_b = revb_structure(P, res, t, f, rng, add, knock)
    t, knock = rev_b["t"], rev_b["knock"]; info.update(rev_b["info"]); field = rev_b["field"]
    to_px = lambda x, y: (int((x - res["bbox"][0]) * ppm), int((y - res["bbox"][1]) * ppm))
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
                for ztype, Z in rev_b["zones"]:
                    if not g.intersects(Z): continue
                    part = g.intersection(Z).buffer(0); g = g.difference(Z).buffer(0)
                    for q in CM.polys(part):
                        if q.area >= 1.0: add(zone_style(ztype, k, q, rng, info), 11)
                if g.is_empty or g.area < 2.0: continue
                A = g.area; w = 2 * A / max(g.length, 1e-6)
                if kind == "fall":
                    r = CM.R(k, g, "tatami", 90.0 + rng.uniform(-4, 4), "FALL")
                elif w < 2.0 and A < 70:
                    r = CM.R(k, g, "satin", "auto", "TMB" if cls == "bld" else GRP[cls])
                else:
                    ang = {"sky": rng.uniform(-8, 8), "cloud": rng.uniform(-28, 28), "rock": 90 + rng.uniform(-16, 16),
                           "fol": rng.uniform(0, 180), "bl": rng.uniform(0, 180), "bld": "auto", "trk": rng.uniform(40, 140)}[cls]
                    if cls in ("rock", "trk") and A >= 12:          # Rev B: rows along the mockup's own strata / bark direction
                        ang, coh = M2.region_angle(field, g, to_px, default=ang)
                    r = CM.R(k, g, "tatami", ang, "VIL" if cls == "bld" else GRP[cls])
                    if cls == "rock" and A >= 40 and k in ("cf_slate", "cf_lav"):
                        add([r], 11); add(M2.strata(g, ang, 3.4, ["cf_mist", "cf_bark"], "RK-line", phase=rng.uniform(0, 3.4)), 11); continue
                    if cls == "trk" and A >= 30:
                        add([r], 11); add(M2.strata(g, ang, 3.0, ["cf_brown" if k == "cf_bark" else "cf_bark"], "TRK-line", phase=rng.uniform(0, 3.0)), 11); continue
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
                    add(M2.floret(cx, cy, d, rng.uniform(0, 72), col, unit=f"fl{nflor}"), 17)   # notched petals, rose centre + cream knot, veins (strip panel 4)
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
            lum = np.mean([{"cf_pinklt": 2, "cf_pink": 1, "cf_rose": 0}[TONES[v]] for v in t[ys2, xs2][m]])
            col = "cf_pinklt" if lum > 1.3 else "cf_pink"
            blob = Point(cx, cy).buffer(math.sqrt(sizes[i - 1] / math.pi) + 0.8)
            traced = []
            for r in items:
                if r["layer"] == 11 and r["col"] in ("cf_pinklt", "cf_pink", "cf_rose") and r["geom"].intersects(blob) and r["geom"].area < 45:
                    traced.append(r["geom"].intersection(blob)); r["geom"] = r["geom"].difference(blob)
            pg = M2.smooth(unary_union(traced).buffer(0.25), 0.3) if traced else Polygon()
            if pg.is_empty or pg.area < 1.5: continue
            pg = max(CM.polys(pg), key=lambda q: q.area)
            # the TRACED petal silhouette (LESSONS A14), satin across its long axis; deeper-rose base at the stalk end
            la = M2.long_axis(pg) if hasattr(M2, "long_axis") else ang
            add([CM.R(col, pg, "satin", la + 90, "PT", unit=f"pt{npet}")], 20)
            if pg.area > 6:
                ux, uy = math.cos(math.radians(la)), math.sin(math.radians(la)); c_ = pg.centroid
                pr = [(q[0] - c_.x) * ux + (q[1] - c_.y) * uy for q in pg.exterior.coords]; lo = min(pr)
                base = pg.intersection(Polygon([(c_.x + ux * lo - uy * 9 - ux * 2, c_.y + uy * lo + ux * 9 - uy * 2), (c_.x + ux * lo + uy * 9 - ux * 2, c_.y + uy * lo - ux * 9 - uy * 2),
                                                (c_.x + ux * (lo + 1.4) + uy * 9, c_.y + uy * (lo + 1.4) - ux * 9), (c_.x + ux * (lo + 1.4) - uy * 9, c_.y + uy * (lo + 1.4) + ux * 9)]).buffer(0))
                if not base.is_empty and base.area > 0.6: add([CM.R("cf_rose", base, "satin", la + 90, "PT", unit=f"pt{npet}", ko=False)], 20)
            npet += 1
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
