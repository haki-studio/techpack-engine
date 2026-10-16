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
        for _ in range(max(3, int(len(band)*1.5))):
            k = rng.randint(i, j); rk = max(S[k][2], min_r)
            lr = max(min_r, min(10.0, rk*size*rng.uniform(0.16, 0.34)))
            c = np.array(S[k][:2]) + N[k]*(rk*rng.uniform(0.15, 0.75))
            geoms.append(Point(*c).buffer(lr, quad_segs=12))
        i = j
    if not geoms: return [], Polygon()
    g = unary_union(geoms).buffer(0.6).buffer(-0.6)
    lumps = [x for x in geoms if x.geom_type == "Polygon" and x.area < 350]
    nm = np.mean([N[k] for k in range(i0, max(i0+1, i1))], axis=0)
    return moss_finish(g, lumps, nm, rng, grp, sparkle), g

def moss_finish(g, lumps, nm, rng, grp="MS", sparkle=0.25, shadow=True):
    """moss geometry -> regions: padded body, dark underside, lit top band, lump contours, a few cream sparkles,
    navy cast shadow below it."""
    nm = np.array(nm, float); nm = nm / (np.linalg.norm(nm) or 1)
    ang = math.degrees(math.atan2(nm[1], nm[0]))
    shade = g.difference(affinity.translate(g, nm[0]*2.4, nm[1]*2.4)).buffer(-0.4).buffer(0.4)
    top = g.difference(affinity.translate(g, -nm[0]*1.6, -nm[1]*1.6)).difference(shade.buffer(0.3)).buffer(-0.45).buffer(0.45)
    shadow_g = affinity.translate(g, -nm[0]*2.0 + 0.3, -nm[1]*2.0).difference(g) if shadow else Polygon()
    arcs, dots = [], []
    for lp in lumps:
        c = lp.centroid; rr = math.sqrt(lp.area/math.pi)
        if rr < 2.4: continue
        a0 = math.atan2(nm[1], nm[0])
        pts = [(c.x + rr*0.8*math.cos(a0 + t), c.y + rr*0.8*math.sin(a0 + t)) for t in np.linspace(-1.0, 1.0, 12)]
        arcs.append(LineString(pts).buffer(0.35, cap_style="round"))
        if rng.random() < sparkle:
            dots.append(Point(c.x + nm[0]*rr*0.35, c.y + nm[1]*rr*0.35).buffer(0.75))
    body = g.difference(shade).difference(top)
    seams = unary_union(arcs).intersection(body.buffer(-0.9)) if arcs else Polygon()
    dots = unary_union(dots).intersection(body.buffer(-0.8)) if dots else Polygon()
    regs = [R("navy", shadow_g, "satin", "auto", grp + "-shadow"),
            R("moss", body.difference(seams.buffer(0.05)).difference(dots), "padded", ang, grp),
            R("mossdk", shade, "satin", ang, grp + "-shade"),
            R("mosslt", top, "satin", ang, grp + "-top"),
            R("cream", dots, "satin", "auto", grp + "-top"),
            R("mossdk", seams, "run", None, grp + "-lump")]
    # mottling as the mockup: every other lump contour in navy (blue bark showing through the moss)
    if arcs and len(arcs) > 3:
        nv = unary_union(arcs[::2]).intersection(body.buffer(-0.9)).difference(dots.buffer(0.3))
        regs[-1] = R("mossdk", unary_union(arcs[1::2]).intersection(body.buffer(-0.9)), "run", None, grp + "-lump")
        regs.append(R("navy", nv, "run", None, grp + "-lump"))
    return [r for r in regs if not r["geom"].is_empty]

def mossy_limb(pts_r, rng, grp="TR", moss=(0.0, 1.0), cover=0.7, size=1.3, gap_p=0.08, texture=True):
    regs, poly, S = M.limb_regions(pts_r, rng, grp=grp, texture=texture)
    regs = recol(regs, BARKMAP)
    mr, mg = ([], Polygon())
    if moss and max(s[2] for s in S) >= 2.4:
        mr, mg = moss_regions(S, moss[0], moss[1], rng, size=size, cover=cover, gap_p=gap_p)
    return regs, mr, poly, S, mg

def twig(pts, r0=1.2, r1=0.9):
    """thin dark twig (satin, turning) along pts"""
    poly, S = sweep(taper(pts, r0, r1))
    return [R("navy", poly, "satin", "auto", "TW")], poly, S

# ---------------------------------------------------------------- leaves
def leaf_regs(x, y, L, W, a):
    p = M.leaf_shape(L, W, serr=False)
    upper = p.intersection(Polygon([(-1, 0), (L+1, 0), (L+1, -W), (-1, -W)])); lower = p.difference(upper)
    T = lambda g: affinity.translate(affinity.rotate(g, a, origin=(0, 0)), x, y)
    P, U, Lw = T(p), T(upper), T(lower)
    light, dark = (U, Lw) if math.sin(math.radians(a)) >= -0.2 else (Lw, U)
    return [R("leaf", light, "satin", a + 45, "LF"), R("leafdk", dark, "satin", a - 45, "LF-dark")], P

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
    return regs, unary_union(allg)

# ---------------------------------------------------------------- sheer light ray (serpentine double run)
def light_ray(p0, d, length, w0, w1, rng, sp=1.9, col="sage", core_col="cream", core=0.34, grp="LR"):
    """band from p0 along unit d, widening w0 -> w1. Rows run along the ray, `sp` apart, joined end to end into one
    serpentine path per tone (one object, no trims inside the ray). Row ends are ragged so the ray fades in/out.
    The central `core` fraction sews in the core colour."""
    d = np.array(d, float); d /= np.linalg.norm(d); nrm = np.array([-d[1], d[0]])
    wmax = max(w0, w1); nrows = int(wmax / sp)
    paths = {col: [], core_col: []}
    for k in range(nrows):
        f = (k + 0.5) / nrows - 0.5                     # -0.5..0.5 across
        c = core_col if abs(f) < core/2 else col
        s0 = rng.uniform(0.0, 0.12)*length; s1 = length*(1 - rng.uniform(0.0, 0.18)*(1 + abs(f)))
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
    pts = []
    for i in range(k):
        t = 2*math.pi*i/k; rr = 1 + rng.uniform(-rough, rough)
        x = cx + w/2*math.cos(t)*rr; y = cy + h/2*math.sin(t)*rr
        if flat_bottom and math.sin(t) > 0.3: y = cy + h/2*(0.75 + 0.25*math.sin(t))
        pts.append((x, y))
    sm = catmull(pts + pts[:3], 8)[8:-8*1]
    return Polygon(sm).buffer(0).buffer(1.5).buffer(-1.5)

def mossy_rock(poly, rng, cover=0.48, grp="RK"):
    """rock body (blue tatami) + navy shadow below + raised moss cap over the top `cover` of its height, with bumps
    along the top contour (as the mockup mounds)."""
    x0, y0, x1, y1 = poly.bounds; h = y1 - y0
    shade = poly.difference(affinity.translate(poly, 2.0, -h*0.22)).buffer(-0.5).buffer(0.5)
    cap = poly.difference(affinity.translate(poly, rng.uniform(-3, 3), h*cover))
    ring = LineString(list(cap.exterior.coords)) if cap.geom_type == "Polygon" else LineString(list(max(cap.geoms, key=lambda q: q.area).exterior.coords))
    lumps = []; s = 0.0
    while s < ring.length:
        p = ring.interpolate(s)
        if p.y < y0 + h*cover*0.9:
            rr = rng.uniform(4.0, 9.0); lumps.append(Point(p.x, p.y + rr*rng.uniform(0.3, 1.1)).buffer(rr, quad_segs=10))
        s += rng.uniform(5, 9)
    g = unary_union([cap] + lumps).intersection(poly.buffer(2.5)).buffer(0.5).buffer(-0.5)
    regs = [R("bark", poly.difference(shade).difference(g), "tatami", 20.0, grp),
            R("navy", shade.difference(g), "tatami", 20.0, grp + "-shade")]
    regs += moss_finish(g, lumps, (0, -1), rng, "RM", sparkle=0.3, shadow=False)
    rim = poly.exterior.buffer(0.6).intersection(poly).difference(g.buffer(0.3)).intersection(box(x0, y0, x1, y0 + h*0.8))
    if not rim.is_empty: regs.append(R("barklt", rim, "satin", "auto", grp + "-rim"))
    return [r for r in regs if not r["geom"].is_empty], unary_union([poly, g])

# ---------------------------------------------------------------- grass
GRASS_COLS = ["grass", "mosslt", "grass", "leafdk", "mossdk", "grass", "leaf"]
def grass_tuft(x, y, h, n, rng, spread=34, lean=0.0, cols=None, r0=1.15, r1=0.55):
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
def hanging_moss(anchors, rng, length=(160, 300), wmin=1.4, wmax=2.6, sway=10.0):
    """strands hanging from anchor points (on the limb), waving, tapering, overlapping; each strand gets a chain-stitch
    look: satin body + a light run highlight down its centre and small knots along it. Returns regions + union."""
    regs = []; allg = []
    for i, (ax, ay) in enumerate(anchors):
        L = rng.uniform(*length); ph = rng.uniform(0, 6.28); amp = rng.uniform(0.5, 1.0)*sway; fr = rng.uniform(2.5, 4.5)
        pts = [(ax + amp*math.sin(ph + t*fr)*min(1, t*2.5) + rng.uniform(-0.8, 0.8), ay + L*t) for t in np.linspace(0, 1, 14)]
        r0 = rng.uniform(wmin, wmax); poly, S = sweep(taper(pts, r0, max(0.7, r0*0.5)), n=6)
        regs.append(R(HM_COLS[i % len(HM_COLS)], poly, "satin", "auto", "HM")); allg.append(poly)
        ln = LineString([s_[:2] for s_ in S]).simplify(0.2)
        if r0 > 2.4:
            hl = ln.buffer(0.35, cap_style="round").intersection(poly.buffer(-1.0))
            col = "cream" if HM_COLS[i % len(HM_COLS)] in ("bark", "mossdk") else ("mosslt" if HM_COLS[i % len(HM_COLS)] != "mosslt" else "leaf")
            regs.append(R(col, hl, "run", None, "HM-light"))
    return regs, unary_union(allg)

# ---------------------------------------------------------------- licensed-figure placeholder (nothing stitched inside)
def placeholder(cx, cy, w, h, label="LICENSED FIGURE — placeholder"):
    """returns (void polygon that knocks everything out, outline region in removable basting thread)"""
    b = box(cx - w/2, cy - h/2, cx + w/2, cy + h/2)
    outline = b.exterior.buffer(0.35)
    return b, R("basting", outline, "run", None, "PH")

# ---------------------------------------------------------------- LESSONS A1 check: nothing floats after clipping
TREE = ("TR", "LM", "TW", "LF", "MS", "HM")
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
        if vis[i]["grp"].split("-")[0] in ("TR", "LM") and vis[i]["st"] in ("tatami", "satin", "padded"): bark[k] += p.area
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
