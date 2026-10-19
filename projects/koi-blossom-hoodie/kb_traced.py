# NOTE (19 Oct 2026): koi() is no longer used — the founder replaced the koi by tetras (kb_fish.py). Kept for the record.
"""Rev B motifs built from the close-up traces (trace/templates.pkl, cu_trace.py) — LESSONS A12/A13.
Each function maps one traced template (close-up px) onto a mockup position (mm): centre, size, heading, optional mirror,
and returns region dicts (col, geom, st, ang, grp, sub) like kb_motifs.
  lily(...)       traced petals: outline + tone regions (dark base -> ice/cream tip, cream edges where traced), stitched
                  as long-and-short satin RADIAL from the flower centre = along each petal's axis; deep-blue throat,
                  cream anther knots, mid-blue stamen lines.  `shift` moves every tone darker (+) / lighter (-) for the
                  flowers the close-up does not show (dark flower, sleeve flower).
  koi(...)        traced silhouette: white body sewn along the spine (tatami, one direction), traced pearl shading,
                  cream scale-row double runs, 2 crisp angular red patches (same direction as the body), traced fins
                  (radial, with grey rays), traced forked tail (radial long-and-short from the root, white base step,
                  grey rays), eye.
  petal(...)      a traced free-petal silhouette, two tones split lengthwise."""
import math, pickle
import numpy as np
from shapely.geometry import Point, Polygon, LineString, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity

TPL = pickle.load(open("trace/templates.pkl", "rb"))
ORDER = ["kb_navy", "kb_cobalt", "kb_royal", "kb_blue", "kb_sky", "kb_ice", "kb_white"]

def polys(g): return [p for p in (g.geoms if hasattr(g, "geoms") else [g]) if p.geom_type == "Polygon" and not p.is_empty]

def _xf(g, c, s, rot, mirror, x, y):
    g = affinity.translate(g, -c[0], -c[1])
    if mirror: g = affinity.scale(g, -1, 1, origin=(0, 0))
    g = affinity.scale(g, s, s, origin=(0, 0)); g = affinity.rotate(g, rot, origin=(0, 0))
    g = affinity.translate(g, x, y)
    return g if g.geom_type == 'Point' else g.buffer(0)

def _pt(p, c, s, rot, mirror, x, y):
    q = _xf(Point(p), c, s, rot, mirror, x, y); return (q.x, q.y)

def line_poly(pts, w): return LineString(pts).buffer(w / 2, cap_style="round", join_style="round")

def tip_dist(name):
    f = TPL["flowers"][name]; c = np.array(f["c"], float)
    return float(np.median([np.hypot(*(np.array(p["tip"], float) - c)) for p in f["petals"]]))

def lily(name, x, y, R, rot=0.0, mirror=False, shift=0, unit=None, rng=None):
    """R = median petal length (mm) wanted; rot deg (y down)"""
    f = TPL["flowers"][name]; c = f["c"]; s = R / tip_dist(name)
    X = lambda g: _xf(g, c, s, rot, mirror, x, y)
    regs = []
    for p in f["petals"]:
        z = p["z"]; cols = sorted({t[0] for t in p["tones"]}, key=ORDER.index)
        for col, g in p["tones"]:
            k = min(max(ORDER.index(col) - shift, 0), len(ORDER) - 1); colx = ORDER[k]
            grp = "FL-base" if col == cols[0] and len(cols) > 1 else ("FL-tip" if col == cols[-1] and len(cols) > 1 else "FL-petal")
            if colx == "kb_white": grp = "FL-hl"
            regs.append(dict(col=colx, geom=X(g), st="satin", ang=("radial", x, y), grp=grp, sub=10 + 3 * z))
    throat = X(f["throat"])
    regs.append(dict(col="kb_navy", geom=throat, st="satin", ang=("radial", x, y), grp="FL-eye", sub=70))
    knots = [X(k) for k in f["knots"]]
    # stamen lines: mid-blue double runs from the throat to the 3 farthest knots (sewn over the throat, under the knots)
    far = sorted(knots, key=lambda k: -k.centroid.distance(Point(x, y)))[:3]
    lines = [line_poly([(x, y), (k.centroid.x, k.centroid.y)], 0.5) for k in far]
    if lines:
        regs.append(dict(col="kb_blue" if shift <= 0 else "kb_sky", geom=unary_union(lines).intersection(throat.buffer(1.2)).buffer(0),
                         st="run", ang=None, grp="FL-line", sub=71, ko=False))
    for k in knots:
        if k.area < 1.2: k = k.buffer(0.45)
        regs.append(dict(col="kb_white", geom=k, st="satin", ang="auto", grp="FL-stamen", sub=72))
    for r in regs: r["unit"] = unit
    sil = unary_union([X(p["visible"]) for p in f["petals"]] + [throat]).buffer(0.3)
    return regs, sil

KOI_NAMES = sorted(TPL["koi"])

LAT = 0.85      # koi slimmed across the spine to the mockup's proportions (the close-up koi are ~15 % stockier)

def koi(k, x, y, L, ang, mirror=False, unit=None):
    """koi template k (0-3) centred at (x, y), head toward `ang` (deg), length L (head tip -> tail tip, mm)"""
    t = TPL["koi"][KOI_NAMES[k % len(KOI_NAMES)]]
    hd, tl = np.array(t["head"], float), np.array(t["tail"], float); mid = (hd + tl) / 2
    a0 = math.degrees(math.atan2(*(hd - tl)[::-1]))          # template heading
    s = L / t["L"]
    # local frame: rotate the template so its head points along +x, mirror across the spine if asked, then place
    def X(g):
        g = affinity.translate(g, -mid[0], -mid[1]); g = affinity.rotate(g, -a0, origin=(0, 0))
        if mirror: g = affinity.scale(g, 1, -1, origin=(0, 0))
        g = affinity.scale(g, s, s * LAT, origin=(0, 0)); g = affinity.rotate(g, ang, origin=(0, 0))
        g = affinity.translate(g, x, y)
        return g if g.geom_type == 'Point' else g.buffer(0)
    P = lambda p: (lambda q: (q.x, q.y))(X(Point(p)))
    u = np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))])
    head = np.array([x, y]) + u * L / 2
    at = lambda f: tuple(head - u * L * f)                    # point on the spine at fraction f from the head tip
    body = X(t["body"]); tail = X(t["tail_g"]).difference(body.buffer(0.2)).buffer(0)
    regs = []
    root = at(0.64)
    tail_base = tail.intersection(Point(root).buffer(0.14 * L))
    regs.append(dict(col="kb_cream", geom=tail.difference(tail_base), st="satin", ang=("radial",) + root, grp="KO-tail", sub=1))
    regs.append(dict(col="kb_white", geom=tail_base, st="satin", ang=("radial",) + root, grp="KO-tail", sub=1))
    # tail rays: grey runs from the root to the traced tail edge (long-and-short look)
    rays = []
    if not tail.is_empty:
        ring = max(polys(tail), key=lambda q: q.area).exterior
        far = [ring.interpolate(f, normalized=True) for f in np.linspace(0, 1, 40, endpoint=False)]
        far = sorted(far, key=lambda q: -q.distance(Point(root)))[:12]
        picked = []
        for q in far:
            if all(q.distance(o) > 0.06 * L for o in picked): picked.append(q)
        for q in picked[:6]:
            e = (root[0] + (q.x - root[0]) * 0.85, root[1] + (q.y - root[1]) * 0.85)
            rays.append(line_poly([at(0.70), e], 0.65))
    fins = []
    for f0 in t["fins"]:          # traced fin outline, scaled 1.35 about its root to the mockup's fin size (fan fins read larger there)
        fx = X(f0); rt = min(fx.exterior.coords, key=lambda p: body.distance(Point(p)))
        fins.append(affinity.scale(fx, 1.35, 1.35, origin=rt).buffer(0))
    for fn in fins:
        if fn.area < 1.5: continue
        b = fn.exterior.interpolate(fn.exterior.project(body.centroid)) if False else None
        base = min(fn.exterior.coords, key=lambda p: body.distance(Point(p)))
        regs.append(dict(col="kb_cream", geom=fn, st="satin", ang=("radial",) + tuple(base), grp="KO-fin", sub=1))
        tipp = max(fn.exterior.coords, key=lambda p: math.hypot(p[0] - base[0], p[1] - base[1]))
        fl = math.hypot(tipp[0] - base[0], tipp[1] - base[1])
        if fl > 5:
            for off in (-0.25, 0.25):
                th = math.atan2(tipp[1] - base[1], tipp[0] - base[0]) + off
                rays.append(line_poly([base, (base[0] + 0.8 * fl * math.cos(th), base[1] + 0.8 * fl * math.sin(th))], 0.65))
    fins_u = unary_union(fins + [tail]) if fins or not tail.is_empty else Polygon()
    if rays:
        rg = unary_union(rays).intersection(fins_u.buffer(-0.35)).difference(body.buffer(0.3)).buffer(0)
        if not rg.is_empty: regs.append(dict(col="kb_grey", geom=rg, st="run", ang=None, grp="KO-ray", sub=2, ko=False))
    # body: white, sewn along the spine (one direction); traced pearl shading
    regs.append(dict(col="kb_white", geom=body, st="tatami", ang=ang, grp="KO", sub=3))
    grey = X(t["grey"]).buffer(-0.5).buffer(0.8).intersection(body.buffer(-0.3)).buffer(0)      # clean shading shapes, no speckle
    grey = unary_union([q for q in polys(grey) if q.area > 4.0]) if not grey.is_empty else grey
    if not grey.is_empty: regs.append(dict(col="kb_cream", geom=grey, st="tatami", ang=ang, grp="KO-shade", sub=4))
    def crisp(r):        # one clean angular object per patch: no hooks / necks (opening 1.6 mm), straight-ish edges
        q = r.buffer(-1.6, join_style=2).buffer(1.6, join_style=2).simplify(0.45).buffer(0)
        ps = polys(q); return max(ps, key=lambda p: p.area) if ps else r
    reds = [crisp(X(r).intersection(body.buffer(-0.5)).buffer(0)) for r in t["reds"]]
    red_u = unary_union(reds)
    # scale rows: cream chevron double runs across the back between the head and the peduncle (on white, not on red)
    W = 2 * max(body.distance(Point(at(0.35))), 1.0) + 0.21 * L
    nv = np.array([-u[1], u[0]]); rows = []
    for f in np.arange(0.26, 0.62, 0.055):
        c0 = np.array(at(f)); pts = []
        for lat in np.linspace(-0.6, 0.6, 9):
            pts.append(tuple(c0 + nv * lat * W / 2 + u * (abs(lat) * 0.06 * L)))
        rows.append(line_poly(pts, 0.5))
    sc = unary_union(rows).intersection(body.buffer(-0.9)).difference(red_u.buffer(0.5)).difference(grey.buffer(0.3)).buffer(0)
    if not sc.is_empty: regs.append(dict(col="kb_cream", geom=sc, st="run", ang=None, grp="KO-scale", sub=4.5, ko=False))
    for rr in reds:
        if not rr.is_empty: regs.append(dict(col="kb_red", geom=rr, st="tatami", ang=ang, grp="KO-red", sub=5))
    if t["eye"] is not None:
        ex, ey = P(t["eye"])
        regs.append(dict(col="kb_ink", geom=Point(ex, ey).buffer(0.80), st="satin", ang="auto", grp="KO-eye", sub=6))
    for r in regs: r["unit"] = unit
    sil = unary_union([r["geom"] for r in regs]).buffer(0.3)
    return regs, sil

def petal(k, x, y, L, ang, rng, tone=("kb_sky", "kb_ice"), unit=None):
    """traced free petal k, centred at (x, y), long axis along ang, length L; lit + shade halves split lengthwise (ragged)"""
    pt = TPL["petals"][k % len(TPL["petals"])]; p = pt["poly"]
    mrr = p.minimum_rotated_rectangle; cs = np.array(mrr.exterior.coords)
    e = [cs[i + 1] - cs[i] for i in range(2)]; ax = e[0] if np.hypot(*e[0]) >= np.hypot(*e[1]) else e[1]
    a0 = math.degrees(math.atan2(ax[1], ax[0])); c = p.centroid
    g = affinity.rotate(affinity.translate(p, -c.x, -c.y), -a0, origin=(0, 0))
    b = g.bounds; s = L / max(b[2] - b[0], 1e-6)
    g = affinity.scale(g, s, s, origin=(0, 0))
    if rng.random() < 0.5: g = affinity.scale(g, 1, -1, origin=(0, 0))
    b = g.bounds; cv = rng.uniform(-0.12, 0.12) * (b[3] - b[1]); zig = [(xx, cv * math.sin(math.pi * (xx - b[0]) / max(b[2] - b[0], 1e-6))) for xx in np.linspace(b[0], b[2], 12)]
    half = Polygon([(b[0] - 1, 0)] + zig + [(b[2] + 1, 0), (b[2] + 1, 50), (b[0] - 1, 50)]).buffer(0)
    lit, shd = g.difference(half), g.intersection(half)
    if rng.random() < 0.5: lit, shd = shd, lit
    T = lambda q: affinity.translate(affinity.rotate(q, ang, origin=(0, 0)), x, y).buffer(0)
    regs = [dict(col=tone[0], geom=T(shd), st="satin", ang="auto", grp="PT", sub=0, unit=unit),
            dict(col=tone[1], geom=T(lit), st="satin", ang="auto", grp="PT-tone", sub=0, unit=unit)]
    return [r for r in regs if not r["geom"].is_empty], T(g)
