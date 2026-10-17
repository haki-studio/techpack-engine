"""Forest motifs (Forestball): mossy limbs + rocks, leaf sprays, sheer light rays, stream, grass, hanging moss,
licensed-figure placeholder. Region dicts as motifs2 (col, geom, st, ang, grp). Units mm, y down.
Reuses the library: motifs2.limb_regions (bark tube, recoloured), motifs2.leaf_shape, motifs.sweep/taper/normals;
moss clumps follow motifs2.snow_regions (same clump logic, moss colours + a lit top band).
Candidates for the motif library (ENGINE_NOTES.md)."""
import math, random
import numpy as np
from shapely.geometry import Point, Polygon, LineString, MultiLineString, box
from shapely.ops import unary_union
from shapely import affinity
from motifs import sweep, taper, normals, catmull, OUTLINE
import motifs2 as M
R = M.R
BARKMAP = {"bark": "bark", "barkdk": "navy", "barklt": "barklt"}

def polys(g):
    if g is None or g.is_empty: return []
    if g.geom_type == "Polygon": return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]

def recol(regs, m):
    return [dict(r, col=m.get(r["col"], r["col"])) for r in regs]

# ---------------------------------------------------------------- moss (raised clumps riding the upper side of a sample line)
def moss_regions(S, t0, t1, rng, size=1.3, min_r=2.0, gap_p=0.10, cover=0.66, grp="MS", sparkle=0.25):
    """S = [(x, y, r)] samples (limb centreline or a rock's top contour). Clumps sit on the 'up' side.
    cover = how far down the limb the moss band reaches (fraction of r below the top edge)."""
    N = normals(S); n = len(S)
    i0, i1 = int(t0*(n-1)), int(t1*(n-1))
    seg = [math.hypot(S[k+1][0]-S[k][0], S[k+1][1]-S[k][1]) for k in range(n-1)]
    def adv(i, dist):
        d = 0.0
        while i < i1 and d < dist: d += seg[i]; i += 1
        return i
    geoms = []; i = i0
    while i < i1:
        r = max(S[i][2], min_r)
        if rng.random() < gap_p and i > i0:
            i = adv(i, r*rng.uniform(0.4, 0.9)); continue
        j = adv(i, r*rng.uniform(1.2, 2.6))
        if j - i < 1: break
        band = [np.array(S[k][:2]) + N[k]*S[k][2]*(1 - cover) for k in range(i, j+1)]
        if len(band) >= 2:
            geoms.append(LineString(band).buffer(max(min_r*0.9, r*cover*0.55), cap_style="round"))
        for _ in range(max(5, int(len(band)*3.2))):          # Rev B: many small clumps (mockup texture)
            k = rng.randint(i, j); rk = max(S[k][2], min_r)
            lr = max(min_r*0.85, min(7.0, rk*size*rng.uniform(0.10, 0.24)))
            c = np.array(S[k][:2]) + N[k]*(rk*rng.uniform(0.15, 0.75))
            geoms.append(Point(*c).buffer(lr, quad_segs=12))
        i = j
    if not geoms: return [], Polygon()
    g = unary_union(geoms).buffer(0.6).buffer(-0.6)
    lumps = [x for x in geoms if x.geom_type == "Polygon" and x.area < 350]
    nm = np.mean([N[k] for k in range(i0, max(i0+1, i1))], axis=0)
    return moss_finish(g, lumps, nm, rng, grp, sparkle), g

def moss_finish(g, lumps, nm, rng, grp="MS", sparkle=0.0, shadow=True):
    """moss geometry -> regions: padded body in two tones (moss + dark-moss lumps, mottled as the mockup), dark underside,
    lit top band + lit crescents on the lumps, lump contours on every lump, navy cast shadow below. No cream specks (Rev B)."""
    nm = np.array(nm, float); nm = nm / (np.linalg.norm(nm) or 1)
    ang = math.degrees(math.atan2(nm[1], nm[0]))
    shade = g.difference(affinity.translate(g, nm[0]*2.4, nm[1]*2.4)).buffer(-0.4).buffer(0.4)
    top = g.difference(affinity.translate(g, -nm[0]*1.6, -nm[1]*1.6)).difference(shade.buffer(0.3)).buffer(-0.45).buffer(0.45)
    shadow_g = affinity.translate(g, -nm[0]*2.0 + 0.3, -nm[1]*2.0).difference(g) if shadow else Polygon()
    arcs, dark, lit, grn, hil = [], [], [], [], []
    a0 = math.atan2(nm[1], nm[0])
    for i, lp in enumerate(lumps):
        c = lp.centroid; rr = math.sqrt(lp.area/math.pi)
        if rr < 1.8: continue
        pts = [(c.x + rr*0.8*math.cos(a0 + t), c.y + rr*0.8*math.sin(a0 + t)) for t in np.linspace(-1.1, 1.1, 12)]
        arcs.append(LineString(pts).buffer(0.35, cap_style="round"))
        if rr > 3.0 and rng.random() < 0.5:          # second contour on the lower side of the bigger lumps
            pts = [(c.x - rr*0.55*math.cos(a0 + t), c.y - rr*0.55*math.sin(a0 + t)) for t in np.linspace(-0.8, 0.8, 9)]
            arcs.append(LineString(pts).buffer(0.35, cap_style="round"))
        u = rng.random()
        if u < 0.28: dark.append(lp.buffer(-0.6))
        elif u < 0.52: grn.append(lp.buffer(-0.6))
        elif rr > 2.2:
            cres = lp.difference(affinity.translate(lp, -nm[0]*rr*0.45, -nm[1]*rr*0.45)).buffer(-0.45).buffer(0.45)
            (hil if rng.random() < 0.25 else lit).append(cres)
    body = g.difference(shade).difference(top)
    seams = unary_union(arcs).intersection(body.buffer(-0.9)) if arcs else Polygon()
    dk = unary_union(dark).intersection(body.buffer(-0.5)).difference(seams.buffer(0.2)).buffer(-0.4).buffer(0.4) if dark else Polygon()
    gr = unary_union(grn).intersection(body.buffer(-0.5)).difference(seams.buffer(0.2)).difference(dk).buffer(-0.4).buffer(0.4) if grn else Polygon()
    lt = unary_union(lit).intersection(body.buffer(-0.5)).difference(seams.buffer(0.2)).difference(dk).difference(gr).buffer(-0.4).buffer(0.4) if lit else Polygon()
    hl = unary_union(hil).intersection(body.buffer(-0.5)).difference(seams.buffer(0.2)).difference(dk).difference(gr).buffer(-0.4).buffer(0.4) if hil else Polygon()
    regs = [R("navy", shadow_g, "satin", "auto", grp + "-shadow"),
            R("moss", body.difference(seams.buffer(0.05)).difference(dk).difference(lt).difference(gr).difference(hl), "padded", ang, grp),
            R("mossdk", dk, "padded", ang + 20, grp),
            R("grass", gr, "padded", ang - 20, grp),
            R("leaf", hl, "satin", ang, grp + "-top"),
            R("mossdk", shade, "satin", ang, grp + "-shade"),
            R("mosslt", unary_union([top, lt]), "satin", ang, grp + "-top")]
    if arcs and len(arcs) > 3:   # mottled contours: alternate navy (blue bark showing through) and dark moss
        regs.append(R("mossdk", unary_union(arcs[1::2]).intersection(body.buffer(-0.9)).difference(dk), "run", None, grp + "-lump"))
        regs.append(R("navy", unary_union(arcs[::2]).intersection(body.buffer(-0.9)), "run", None, grp + "-lump"))
    elif arcs: regs.append(R("mossdk", seams, "run", None, grp + "-lump"))
    return [r for r in regs if not r["geom"].is_empty]

def mossy_limb(pts_r, rng, grp="TR", moss=(0.0, 1.0), cover=0.7, size=1.3, gap_p=0.08, texture=True):
    """mossy limb: bark tube (motifs2.limb_regions) whose underside is twisted blue chain bark (bark-blue band with
    navy diagonal chain strokes, Rev B) under a raised two-tone moss cover."""
    regs, poly, S = M.limb_regions(pts_r, rng, grp=grp, texture=texture)
    regs = recol(regs, BARKMAP)
    out = []
    N = normals(S)
    for r in regs:
        if r["grp"].endswith("-shade"):
            band = r["geom"]; out.append(dict(r, col="bark"))
            ch = []; acc = 0.0
            for k in range(1, len(S) - 1):
                acc += math.hypot(S[k][0]-S[k-1][0], S[k][1]-S[k-1][1]); x, y, rad = S[k]
                if acc < 3.2 or rad < 3.0: continue
                acc = 0.0
                tx, ty = S[k+1][0]-S[k-1][0], S[k+1][1]-S[k-1][1]; L = math.hypot(tx, ty) or 1; tx, ty = tx/L, ty/L
                lo = (x - N[k][0]*rad*0.98, y - N[k][1]*rad*0.98); hi = (x - N[k][0]*rad*0.35, y - N[k][1]*rad*0.35)
                d = rad*0.35          # diagonal stroke across the band = one chain link
                ch.append(LineString([(lo[0] - tx*d, lo[1] - ty*d), ((lo[0]+hi[0])/2 + tx*d*0.2, (lo[1]+hi[1])/2 + ty*d*0.2),
                                      (hi[0] + tx*d, hi[1] + ty*d)]).buffer(0.35, cap_style="round"))
            if ch: out.append(R("navy", unary_union(ch).intersection(band.buffer(-0.5)), "bean", None, grp + "-crevice"))
        else: out.append(r)
    mr, mg = ([], Polygon())
    if moss and max(s[2] for s in S) >= 2.4:
        mr, mg = moss_regions(S, moss[0], moss[1], rng, size=size, cover=cover, gap_p=gap_p)
    return out, mr, poly, S, mg

def twig(pts, r0=1.2, r1=0.9, nodes=True):
    """twig in brown (chain look from close-up b) with small cream nodes every ~6 mm"""
    poly, S = sweep(taper(pts, r0, r1))
    regs = [R("brown", poly, "satin", "auto", "TW")]
    if nodes:
        ln = LineString([s_[:2] for s_ in S]); nd = []; t = 3.0
        while t < ln.length - 2:
            q = ln.interpolate(t); nd.append(Point(q.x, q.y).buffer(0.65)); t += 6.0
        if nd: regs.append(R("cream", unary_union(nd).intersection(poly.buffer(0.2)), "satin", "auto", "TW-node"))
    return regs, poly, S

# ---------------------------------------------------------------- leaves
def leaf_regs(x, y, L, W, a):
    p = M.leaf_shape(L, W, serr=False)
    upper = p.intersection(Polygon([(-1, 0), (L+1, 0), (L+1, -W), (-1, -W)])); lower = p.difference(upper)
    T = lambda g: affinity.translate(affinity.rotate(g, a, origin=(0, 0)), x, y)
    P, U, Lw = T(p), T(upper), T(lower)
    light, dark = (U, Lw) if math.sin(math.radians(a)) >= -0.2 else (Lw, U)
    vein = T(LineString([(0.12*L, 0), (0.82*L, 0)]).buffer(0.32, cap_style="round")).intersection(P.buffer(-0.5))
    dk = "grass" if (int(abs(x*7 + y*13)) % 4 == 0) else "mosslt"        # ~1 in 4 leaves has the dark-green half (close-up b)
    return [R("leaf", light.difference(vein), "satin", a + 45, "LF"), R(dk, dark.difference(vein), "satin", a - 45, "LF-dark"),
            R("brown", vein, "run", None, "LF-vein")], P

def leaf_spray(base, ang, length, rng, leaf=10.0, pairs=None, bend=12.0, r0=1.15):
    """pinnate spray: a curved twig from `base` at `ang` (deg), alternate leaves along the outer 70 %, terminal leaf.
    Leaves point forward (35–55° off the twig). Returns (regions, union of leaves + twig)."""
    a = math.radians(ang); bd = math.radians(rng.uniform(-bend, bend))
    pts = [base]
    for k in range(1, 5):
        aa = a + bd*k/4
        pts.append((pts[-1][0] + math.cos(aa)*length/4, pts[-1][1] + math.sin(aa)*length/4))
    regs, tp, S = twig(pts, r0, 0.9)
    line = LineString([s[:2] for s in S]); Ltot = line.length
    n = pairs or max(2, int(Ltot*0.7 / (leaf*0.62)))
    allg = [tp]; side = 1
    for i in range(n):
        s = Ltot*(0.3 + 0.7*i/max(1, n)) ; p0 = line.interpolate(s); p1 = line.interpolate(min(Ltot, s + 0.8))
        ta = math.degrees(math.atan2(p1.y - p0.y, p1.x - p0.x))
        la = ta + side*rng.uniform(38, 55)
        Lk = leaf*rng.uniform(0.85, 1.08)
        lr, P = leaf_regs(p0.x, p0.y, Lk, Lk*0.52, la)
        regs += lr; allg.append(P); side = -side
    e = line.interpolate(Ltot); e0 = line.interpolate(Ltot - 1.0)
    ta = math.degrees(math.atan2(e.y - e0.y, e.x - e0.x))
    lr, P = leaf_regs(e.x - math.cos(math.radians(ta))*0.8, e.y - math.sin(math.radians(ta))*0.8, leaf*1.05, leaf*0.55, ta)
    regs += lr; allg.append(P)
    # tiny navy bud on a short side shoot near the tip (close-up b)
    q = line.interpolate(Ltot*0.8); bd = affinity.rotate(affinity.scale(Point(q.x, q.y).buffer(1.0), 1.5, 0.9), ta - 50, origin=(q.x, q.y))
    bd = affinity.translate(bd, math.cos(math.radians(ta - 50))*2.2, math.sin(math.radians(ta - 50))*2.2)
    regs.append(R("navy", bd, "satin", ta - 50, "BUD")); allg.append(bd)
    return regs, unary_union(allg)

# ---------------------------------------------------------------- sheer light ray (serpentine double run)
def light_ray(p0, d, length, w0, w1, rng, sp=2.6, col="sage", core_col="cream", core=0.34, grp="LR"):
    """band from p0 along unit d, widening w0 -> w1. Rows run along the ray, `sp` apart, joined end to end into one
    serpentine path per tone (one object, no trims inside the ray). Row ends are ragged so the ray fades in/out.
    The central `core` fraction sews in the core colour."""
    d = np.array(d, float); d /= np.linalg.norm(d); nrm = np.array([-d[1], d[0]])
    wmax = max(w0, w1); nrows = int(wmax / sp)
    paths = {col: [], core_col: []}
    for k in range(nrows):
        f = (k + 0.5) / nrows - 0.5                     # -0.5..0.5 across
        c = core_col if abs(f) < core/2 else col
        s0 = rng.uniform(0.0, 0.10)*length; s1 = length*(1 - rng.uniform(0.0, 0.45)*(0.6 + abs(f)))   # ragged, fading ends (soft ray)
        if s1 - s0 < 20: continue
        pts = []
        for s in np.linspace(s0, s1, 12):
            w = w0 + (w1 - w0)*s/length
            off = f*w
            q = np.array(p0) + d*s + nrm*off
            pts.append(tuple(q))
        paths[c].append(pts)
    regs = []
    for c, rows in paths.items():
        if not rows: continue
        seq = []
        for i, rpts in enumerate(rows):
            seq += rpts if i % 2 == 0 else rpts[::-1]
        g = LineString(seq).buffer(0.32, cap_style="round", join_style="round")
        regs.append(R(c, g, "run", None, grp))
    band = Polygon([tuple(np.array(p0) + nrm*w0/2), tuple(np.array(p0) - nrm*w0/2),
                    tuple(np.array(p0) + d*length - nrm*w1/2), tuple(np.array(p0) + d*length + nrm*w1/2)])
    return regs, band

# ---------------------------------------------------------------- stream
def stream(poly, rng, deep=None, nrip=60, nglint=26):
    """water body (horizontal tatami), deep band, ripple bars + glints sewn on top."""
    regs = []
    dp = deep.intersection(poly) if deep is not None else Polygon()
    regs.append(R("water", poly.difference(dp), "tatami", 0.0, "WA"))
    if not dp.is_empty: regs.append(R("navy", dp, "tatami", 0.0, "WA-deep"))
    x0, y0, x1, y1 = poly.bounds; rips = []; gl = []
    inner = poly.buffer(-1.5)
    for _ in range(nrip * 6):
        if len(rips) >= nrip: break
        x = rng.uniform(x0, x1); y = rng.uniform(y0, y1); L = rng.uniform(6, 26); w = rng.uniform(1.0, 1.5)
        b = LineString([(x - L/2, y), (x + L/2, y + rng.uniform(-0.6, 0.6))]).buffer(w/2, cap_style="round")
        if not inner.contains(b) or any(b.distance(o) < 1.6 for o in rips): continue
        rips.append(b)
    for _ in range(nglint * 8):
        if len(gl) >= nglint: break
        x = rng.uniform(x0, x1); y = rng.uniform(y0, y1); L = rng.uniform(1.6, 3.2)
        b = LineString([(x - L/2, y), (x + L/2, y)]).buffer(0.65, cap_style="round")
        if not inner.contains(b) or any(b.distance(o) < 1.2 for o in rips + gl): continue
        gl.append(b)
    if rips: regs.append(R("waterlt", unary_union(rips), "satin", 0.0 + 90, "WA-ripple"))
    if gl: regs.append(R("cream", unary_union(gl), "satin", 90.0, "WA-glint"))
    return regs

# ---------------------------------------------------------------- mossy rock
def blob(cx, cy, w, h, rng, k=9, rough=0.12, flat_bottom=True):
    """rounded dome (mossy mound): half-ellipse top, softly flattened base"""
    pts = []
    for i in range(k):
        t = 2*math.pi*i/k; rr = 1 + rng.uniform(-rough, rough)
        x = cx + w/2*math.cos(t)*rr; y = cy + h/2*math.sin(t)*rr*(0.55 if math.sin(t) > 0 else 1.0)
        pts.append((x, y))
    sm = catmull(pts + pts[:3], 8)[8:-8*1]
    return Polygon(sm).buffer(0).buffer(2.0).buffer(-2.0)

def mossy_rock(poly, rng, cover=0.75, grp="RK"):
    """mossy mound: moss over the top `cover` of its height with bumps all along the top contour, blue rock showing
    below, a thin navy shadow only at the base (no hard under-shadow: mounds sit IN the bank, Rev B)."""
    x0, y0, x1, y1 = poly.bounds; h = y1 - y0
    shade = poly.difference(affinity.translate(poly, 0, -min(3.0, h*0.08))).buffer(-0.5).buffer(0.5)
    cap = poly.difference(affinity.translate(poly, rng.uniform(-3, 3), h*cover))
    ring = LineString(list(cap.exterior.coords)) if cap.geom_type == "Polygon" else LineString(list(max(cap.geoms, key=lambda q: q.area).exterior.coords))
    lumps = []; s = 0.0
    while s < ring.length:
        p = ring.interpolate(s)
        if p.y < y0 + h*cover*0.95:
            rr = rng.uniform(4.0, 9.5); lumps.append(Point(p.x, p.y + rr*rng.uniform(0.3, 1.1)).buffer(rr, quad_segs=10))
        s += rng.uniform(4.5, 8)
    inner = cap.buffer(-4)       # lumps inside the cap too, so the contours cover the whole mound
    if not inner.is_empty:
        bx0, by0, bx1, by1 = inner.bounds
        for _ in range(int(inner.area / 60)):
            q = Point(rng.uniform(bx0, bx1), rng.uniform(by0, by1))
            if inner.contains(q): lumps.append(q.buffer(rng.uniform(3.5, 7.0), quad_segs=10))
    g = unary_union([cap] + lumps).intersection(poly.buffer(2.5)).buffer(0.5).buffer(-0.5)
    regs = [R("bark", poly.difference(shade).difference(g), "tatami", 20.0, grp), R("navy", shade.difference(g), "tatami", 20.0, grp + "-shade")]
    regs += moss_finish(g, lumps, (0, -1), rng, "RM", shadow=False)
    return [r for r in regs if not r["geom"].is_empty], unary_union([poly, g])

# ---------------------------------------------------------------- grass
GRASS_COLS = ["grass", "mosslt", "grass", "leafdk", "mossdk", "grass", "leaf"]
def grass_tuft(x, y, h, n, rng, spread=34, lean=0.0, cols=None, r0=1.25, r1=0.55):
    """blades rising from (x, y): curved tapered satin columns, blunt tips (≥ 1.1 wide)."""
    regs = []; allg = []; cols = cols or GRASS_COLS
    for i in range(n):
        a = math.radians(-90 + lean + spread*((i + 0.5)/n - 0.5)*2 + rng.uniform(-6, 6))
        hk = h*rng.uniform(0.55, 1.0); curl = rng.uniform(-0.5, 0.5)
        pts = []
        for k in range(6):
            t = k/5; aa = a + curl*t*t
            pts.append((x + rng.uniform(-1.5, 1.5)*(k == 0) + math.cos(aa)*hk*t, y + math.sin(aa)*hk*t))
        poly, S = sweep(taper(pts, r0, r1), n=6)
        regs.append(R(cols[(i + rng.randint(0, 3)) % len(cols)], poly, "satin", "auto", "GR")); allg.append(poly)
    return regs, unary_union(allg)

# ---------------------------------------------------------------- hanging moss (front shoulder)
HM_COLS = ["moss", "mosslt", "bark", "mossdk", "leafdk", "barklt", "moss"]
HM_GREEN = ["moss", "mosslt", "mossdk", "moss", "mosslt"]; HM_BLUE = ["bark", "barklt", "bark"]
def hanging_moss(anchors, rng, length=(120, 260), wmin=2.0, wmax=6.0, sway=14.0, blue_every=3):
    """hanging moss as twisted ropes (Rev B): strands 4–12 mm wide (r 2–6), tapered at both ends, waving with different
    phase/frequency so they overlap and cross; each strand gets a rope twist (diagonal cord-run strokes every ~3 mm, no
    centre line). Green strands first, blue strands layered on top (later z), as the mockup."""
    green, blue = [], []
    for i, (ax, ay) in enumerate(anchors):
        L = rng.uniform(*length); ph = rng.uniform(0, 6.28); amp = rng.uniform(0.5, 1.2)*sway; fr = rng.uniform(2.0, 5.0)
        drift = rng.uniform(-18, 18)
        pts = [(ax + amp*math.sin(ph + t*fr)*min(1, t*2.2) + drift*t, ay + L*t) for t in np.linspace(0, 1, 16)]
        r0 = rng.uniform(wmin, wmax)
        rad = [(x, y, r0*(0.55 + 0.45*min(1, t/0.12))*(1 - 0.78*max(0, (t - 0.55)/0.45))) for (x, y), t in zip(pts, np.linspace(0, 1, 16))]
        poly, S = sweep([(x, y, max(0.6, r)) for x, y, r in rad], n=6)
        isblue = (i % blue_every == 1)
        col = (HM_BLUE[i % len(HM_BLUE)] if isblue else HM_GREEN[i % len(HM_GREEN)])
        tw = []; acc = 0.0                   # rope twist strokes
        for k in range(1, len(S) - 1):
            acc += math.hypot(S[k][0]-S[k-1][0], S[k][1]-S[k-1][1]); x, y, r = S[k]
            if acc < 3.0 or r < 1.6: continue
            acc = 0.0
            tx, ty = S[k+1][0]-S[k-1][0], S[k+1][1]-S[k-1][1]; Ln = math.hypot(tx, ty) or 1; tx, ty = tx/Ln, ty/Ln
            nx, ny = -ty, tx
            a_ = (x - nx*r*0.8 - tx*r*0.5, y - ny*r*0.8 - ty*r*0.5); b_ = (x + nx*r*0.8 + tx*r*0.5, y + ny*r*0.8 + ty*r*0.5)
            tw.append(LineString([a_, b_]).buffer(0.32, cap_style="round"))
        twc = "cream" if col in ("bark", "mossdk") else ("mossdk" if col == "mosslt" else "mosslt")
        reg = [R(col, poly, "satin", "auto", "HM")]
        if not isblue and r0 > 2.5:          # moss clumps along the green strands (chain links, two tones)
            cl = []; acc = 0.0; side = 1
            for k in range(1, len(S) - 1):
                acc += math.hypot(S[k][0]-S[k-1][0], S[k][1]-S[k-1][1]); x, y, r = S[k]
                if acc < r*1.1 or r < 2.0: continue
                acc = 0.0; tx, ty = S[k+1][0]-S[k-1][0], S[k+1][1]-S[k-1][1]; Ln = math.hypot(tx, ty) or 1
                cl.append(Point(x - ty/Ln*r*0.35*side, y + tx/Ln*r*0.35*side).buffer(r*0.5)); side = -side
            if cl:
                lump = unary_union(cl).intersection(poly.buffer(-0.5))
                reg.append(R("mosslt" if col != "mosslt" else "leaf", lump, "satin", "auto", "HM"))
        if tw: reg.append(R(twc, unary_union(tw).intersection(poly.buffer(-0.7)), "run", None, "HM-light"))
        (blue if isblue else green).append((reg, poly))
    regs = [r for rg, _ in green for r in rg] + [r for rg, _ in blue for r in rg]
    return regs, unary_union([p for _, p in green + blue])

# ---------------------------------------------------------------- licensed-figure placeholder (nothing stitched inside)
def placeholder(cx, cy, w, h, label="LICENSED FIGURE — placeholder"):
    """returns (void polygon that knocks everything out, outline region in removable basting thread)"""
    b = box(cx - w/2, cy - h/2, cx + w/2, cy + h/2)
    outline = b.exterior.buffer(0.35)
    return b, R("basting", outline, "run", None, "PH")

# ---------------------------------------------------------------- LESSONS A1 check: nothing floats after clipping
TREE = ("TR", "LM", "TW", "LF", "MS", "HM", "CH", "BUD")
def drop_floating(vis, min_bark=150.0, join=0.9):
    """After the keep-out clip, a spray whose twig was cut off would float. Tree pieces (bark, twigs, leaves, moss)
    are grouped into connected clusters (touching within `join` mm); a cluster survives only if it holds at least
    `min_bark` mm² of limb bark (TR/LM) — i.e. it is still attached to a limb. Rock moss (RM) is not a tree part. Returns (vis, n_dropped_pieces)."""
    import shapely
    tree_ix = [i for i, r in enumerate(vis) if r["grp"].split("-")[0] in TREE]
    pieces = [(i, p) for i in tree_ix for p in polys(vis[i]["geom"])]
    if not pieces: return vis, 0
    cl = polys(unary_union([p.buffer(join) for _, p in pieces]))
    tr = shapely.STRtree(cl)
    bark = [0.0] * len(cl); owner = []
    for i, p in pieces:
        k = next(int(j) for j in tr.query(p.representative_point()) if cl[int(j)].contains(p.representative_point()))
        owner.append(k)
        if vis[i]["grp"].split("-")[0] in ("TR", "LM", "CH") and vis[i]["st"] in ("tatami", "satin", "padded"): bark[k] += p.area
    keep = {}; dropped = 0
    for (i, p), k in zip(pieces, owner):
        if bark[k] >= min_bark: keep.setdefault(i, []).append(p)
        else: dropped += 1
    out = []
    for i, r in enumerate(vis):
        if i in tree_ix:
            if i in keep: out.append(dict(r, geom=unary_union(keep[i])))
        else: out.append(r)
    return out, dropped


def ridge_cleanup(vis, h=0.45):
    """Bark ridge highlights half-hidden under moss leave thin satin strips (< 0.8 mm). Open each ridge region by h and
    hand the strips to the bark body region they touch most (the strip then sews as bark, no gap)."""
    import shapely
    body_ix = [i for i, r in enumerate(vis) if r["grp"] in ("TR", "LM") and r["st"] == "tatami"]
    tree = shapely.STRtree([vis[i]["geom"] for i in body_ix]); give = {}
    for i, r in enumerate(vis):
        if not r["grp"].endswith("-ridge"): continue
        g = r["geom"]; op = g.buffer(-h).buffer(h).intersection(g); rest = g.difference(op)
        vis[i] = dict(r, geom=op)
        for piece in polys(rest):
            hits = [body_ix[int(j)] for j in tree.query(piece.buffer(0.05))]
            if not hits: continue
            j = max(hits, key=lambda j: piece.buffer(0.05).intersection(vis[j]["geom"]).area)
            give.setdefault(j, []).append(piece)
    for j, pcs in give.items(): vis[j] = dict(vis[j], geom=unary_union([vis[j]["geom"]] + pcs).buffer(0))
    return [r for r in vis if not r["geom"].is_empty and r["geom"].area > 0.05]


# ---------------------------------------------------------------- hanging moss as chain-link ropes (Rev B, mockup texture)
CHAIN_TONES = [("bark", "barklt"), ("moss", "mosslt"), ("navy", "bark"), ("mossdk", "moss"), ("barklt", "bark"), ("moss", "leaf"), ("bark", "navy")]
def hanging_chains(anchors, rng, length=(220, 300), wmin=2.6, wmax=5.2, sway=6.0, drift=10.0):
    """dense mass of hanging moss ropes: each strand is a chain of overlapping oval links (satin, across the link),
    alternating two tones (blue/teal or greens), tapering to the tip; strands overlap and cross (different phases,
    drift), blue strands drawn over green ones. Returns (regions, union)."""
    strands = []
    for i, (ax, ay) in enumerate(anchors):
        L = rng.uniform(*length); ph = rng.uniform(0, 6.28); amp = rng.uniform(0.4, 1.0)*sway; fr = rng.uniform(1.5, 3.5)
        dr = rng.uniform(-drift, drift); r0 = rng.uniform(wmin, wmax)
        line = LineString([(ax + amp*math.sin(ph + t*fr*math.pi)*min(1, t*3) + dr*t, ay + L*t) for t in np.linspace(0, 1, 40)])
        strands.append((i, line, r0, CHAIN_TONES[i % len(CHAIN_TONES)]))
    strands.sort(key=lambda s_: 0 if s_[3][0] in ("moss", "mossdk") else 1)       # greens under, blues on top
    regs, allg = [], []
    for i, line, r0, (c1, c2) in strands:
        s_ = 0.0; k = 0; Ltot = line.length
        while s_ < Ltot:
            t = s_ / Ltot; r = r0*(0.6 + 0.4*min(1, t/0.08))*(1 - 0.75*max(0, (t - 0.6)/0.4))
            if r < 0.9: break
            p0 = line.interpolate(max(0, s_ - 0.5)); p1 = line.interpolate(min(Ltot, s_ + 0.5)); c = line.interpolate(s_)
            ang = math.degrees(math.atan2(p1.y - p0.y, p1.x - p0.x))
            link = affinity.rotate(affinity.scale(Point(c.x, c.y).buffer(1.0, quad_segs=10), r*1.15, r*0.95), ang + (18 if k % 2 else -18), origin=(c.x, c.y))
            regs.append(R(c1 if k % 2 == 0 else c2, link, "satin", ang + 90, "HM")); allg.append(link)
            s_ += r*1.35; k += 1
    return regs, unary_union(allg)


# ---------------------------------------------------------------- hanging moss ropes (Rev B, traced from the 4x mockup crop)
def hanging_ropes(ropes, rng):
    """ropes: [(pts [(x, y, r)], body colour)] — thick drooping moss ropes as the mockup: dark blue/navy chain body
    (tatami along the rope), 3 twisted strand lines inside (wavy bean runs in teal + light moss), a yellow-green chain
    edge (bean) with small loops along it. Later ropes lie over earlier ones."""
    regs, allg = [], []
    for ri, (pts, body_col) in enumerate(ropes):
        poly, S = sweep(pts, n=8); N = normals(S)
        regs.append(R(body_col, poly, "tatami", "auto", "HM")); allg.append(poly)
        mr, mg = moss_regions(S, 0.0, 0.85, rng, size=1.1, min_r=1.7, gap_p=0.25, cover=0.42, grp="MS")   # lumpy moss on the rope
        regs += [dict(r, geom=r["geom"].intersection(poly.buffer(1.5))) for r in mr if r["grp"] != "MS-shadow"]
        line_cols = ["barklt", "mosslt", "bark" if body_col == "navy" else "navy"]
        for j, off in enumerate((-0.45, 0.0, 0.45)):
            ph = rng.uniform(0, 6.28); wl = []
            for k, (x, y, r) in enumerate(S):
                o = off + 0.18*math.sin(ph + k*0.55)
                wl.append((x + N[k][0]*r*o, y + N[k][1]*r*o))
            g = LineString(wl).buffer(0.38, cap_style="round").intersection(poly.buffer(-0.9))
            regs.append(R(line_cols[j], g, "bean", None, "HM-light"))
        # yellow-green chain edge: edge line + small loops every ~5 mm
        edge = poly.exterior.buffer(0.38).intersection(poly.buffer(0.1))
        loops = []; ring = poly.exterior; Lr = ring.length; t = rng.uniform(0, 4)
        while t < Lr:
            q = ring.interpolate(t); loops.append(Point(q.x, q.y).buffer(1.6).exterior.buffer(0.35)); t += rng.uniform(4.5, 6.5)
        ch = unary_union([edge] + loops).intersection(poly.buffer(-0.05))
        regs.append(R("mosslt" if ri % 2 == 0 else "leaf", ch, "bean", None, "HM-light"))
    return regs, unary_union(allg)


# ---------------------------------------------------------------- braided chain-stitch limb (Rev B, close-up b vocabulary)
CHAIN_UP = ["mosslt", "leaf", "moss", "mosslt", "cream", "grass"]
CHAIN_MID = ["royal", "moss", "navy", "grass", "royal", "mossdk"]
CHAIN_LOW = ["royal", "navy", "bark", "royal", "navy"]
def chain_limb(pts_r, rng, grp="TR", link=3.2, up=None, mid=None, low=None, cream=0.10):
    """limb (or moss rope) filled with rows of chain links: lanes run along the limb with a slow diagonal drift (braid),
    each link a small satin oval angled ±28°; colours by lane — top lanes yellow-greens with cream specks, middle royal
    blue / greens / navy, underside royal blue + navy. A navy base fill sits under the links."""
    poly, S = sweep(pts_r); N = normals(S)
    regs = [R("navy", poly, "tatami", "auto", grp)]
    up = up or CHAIN_UP; mid = mid or CHAIN_MID; low = low or CHAIN_LOW
    line = LineString([s_[:2] for s_ in S]); L = line.length
    rs = [s_[2] for s_ in S]; cum = [0.0]
    for a, b in zip(S, S[1:]): cum.append(cum[-1] + math.hypot(b[0]-a[0], b[1]-a[1]))
    # braid: n strands spiral along the limb (offset drifts across the width and wraps), each strand keeps its own thread
    n = max(3, int(round(2*max(rs) / (link*0.75))))
    strand_col = []
    for j in range(n):
        pal = [up, mid, low, mid][j % 4]; strand_col.append(pal[j % len(pal)])
    period = rng.uniform(70, 95)                    # mm per half twist
    s = 0.0; step = link*0.55; k = 0
    while s < L:
        i = min(range(len(cum)), key=lambda j: abs(cum[j] - s)); x, y, r = S[i]
        if r < 1.3: s += step; continue
        p0 = line.interpolate(max(0, s - 0.6)); p1 = line.interpolate(min(L, s + 0.6))
        ang = math.degrees(math.atan2(p1.y - p0.y, p1.x - p0.x))
        for j in range(n):
            u = ((j / n + s / period) % 1.0)
            o = -0.9 + 1.8*u
            cx, cy = x + N[i][0]*r*o, y + N[i][1]*r*o
            rx = link*0.62*rng.uniform(0.9, 1.1); ry = min(link*0.34, r*2.0/n*0.62)*rng.uniform(0.9, 1.1)
            if ry < 0.6: continue
            tilt = 38 + rng.uniform(-6, 6)          # links lean along the twist
            lk = affinity.rotate(affinity.scale(Point(cx, cy).buffer(1.0, quad_segs=8), rx, ry), ang + tilt, origin=(cx, cy))
            col = strand_col[j]
            if o > 0.35 and rng.random() < cream: col = "cream"          # cream highlight specks on the top
            elif rng.random() < 0.08: col = [up, mid, low][rng.randrange(3)][0]
            regs.append(R(col, lk.intersection(poly), "satin", ang + tilt, "CH"))
        s += step; k += 1
    return regs, poly, S

def loop_chain(pts, rng, col, ring=1.2, gap=2.1):
    """free hanging moss strand drawn as a chain of open loops (bean outline rings) along a wavy line"""
    ln = LineString(pts); out = []; t = 0.0
    while t < ln.length:
        q = ln.interpolate(t); out.append(Point(q.x, q.y).buffer(ring).exterior.buffer(0.33)); t += gap
    return R(col, unary_union(out), "bean", None, "HM-light")
