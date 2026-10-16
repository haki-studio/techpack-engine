"""Shared motif library — plum / pine / bamboo jacket. All units mm, y down."""
import math, random
import numpy as np
from shapely.geometry import Point, Polygon, LineString, MultiPolygon, GeometryCollection
from shapely.ops import unary_union
from shapely import affinity

# ---------------------------------------------------------------- thread palette (14 colours)
PAL = {
    "snow":      ("#F8F5EE", "Snow white",       "snow, white pine fans, sparkle"),
    "shadow":    ("#A3ABB2", "Snow shadow grey", "snow shadow, mist lines"),
    "bark":      ("#7A5640", "Bark brown",       "trunk & branch fill"),
    "barkdk":    ("#3A271C", "Bark dark",        "bark texture, outlines, pine needles (white pine)"),
    "plum":      ("#C9343B", "Plum red",         "petals, buds"),
    "petal":     ("#EE9C94", "Petal pink",       "petal edges, bud highlight"),
    "plumdk":    ("#86202A", "Plum dark",        "petal outlines, bud calyx"),
    "gold":      ("#E3AE45", "Gold",             "stamens, white-pine inner zone, red-pine needles"),
    "orange":    ("#DD7426", "Orange",           "pine hubs"),
    "leaf":      ("#3E5962", "Slate",            "plum leaves"),
    "leaflt":    ("#86A3AA", "Slate light",      "leaf veins"),
    "indigo":    ("#4C4F8C", "Indigo",           "bamboo blades"),
    "lavender":  ("#9A9BCB", "Lavender",         "bamboo highlight"),
    "vermilion": ("#C4482B", "Vermilion",        "red pine fans"),
}
HEX = {k: v[0] for k, v in PAL.items()}
FABRIC = "#D9C4A0"

OUTLINE = 0.7      # triple-run line art width (mm)
U = lambda g: unary_union(g) if isinstance(g, (list, tuple)) else g

# ---------------------------------------------------------------- geometry helpers
def bez(p0, p1, p2, p3, n=24):
    t = np.linspace(0, 1, n)[:, None]
    p0, p1, p2, p3 = map(np.array, (p0, p1, p2, p3))
    return ((1-t)**3*p0 + 3*(1-t)**2*t*p1 + 3*(1-t)*t**2*p2 + t**3*p3).tolist()

def catmull(points, n=10):
    P = [np.array(p, float) for p in points]
    if len(P) == 2:
        return [list(P[0] + (P[1]-P[0])*t) for t in np.linspace(0, 1, n)]
    out = []
    for i in range(len(P) - 1):
        a = P[i-1] if i > 0 else 2*P[0] - P[1]
        d = P[i+2] if i + 2 < len(P) else 2*P[-1] - P[-2]
        b, c = P[i], P[i+1]
        seg = bez(b, b + (c-a)/6, c - (d-b)/6, c, n)
        out += seg if i == 0 else seg[1:]
    return out

def sweep(pts, n=8):
    """pts: [(x,y,r)] -> smooth tapered tube polygon; returns (polygon, samples[(x,y,r)])."""
    S = catmull(pts, n)
    geoms = []
    for (x1, y1, r1), (x2, y2, r2) in zip(S, S[1:]):
        c1 = Point(x1, y1).buffer(max(r1, 0.05), quad_segs=10)
        c2 = Point(x2, y2).buffer(max(r2, 0.05), quad_segs=10)
        geoms.append(c1.union(c2).convex_hull)
    return unary_union(geoms), S

def taper(xy, r0, r1, power=1.0):
    n = len(xy)
    return [(x, y, r0 + (r1 - r0) * (i / (n-1))**power) for i, (x, y) in enumerate(xy)]

def line(pts, w=OUTLINE, smooth=True, n=8):
    P = catmull(pts, n) if smooth and len(pts) > 2 else pts
    return LineString([p[:2] for p in P]).buffer(w/2, cap_style="round", join_style="round", quad_segs=8)

def normals(S):
    out = []
    for i in range(len(S)):
        a = np.array(S[max(i-1, 0)][:2]); b = np.array(S[min(i+1, len(S)-1)][:2])
        t = b - a; t = t / (np.linalg.norm(t) or 1)
        nrm = np.array([t[1], -t[0]])
        if nrm[1] > 0: nrm = -nrm          # point "up" (snow side)
        out.append(nrm)
    return out

# ---------------------------------------------------------------- bark, branch, snow
def snow_ridge(S, t0=0.0, t1=1.0, rng=None, size=0.62, step=0.9, lift=0.55, min_r=1.0, gap_p=0.28):
    """Heavy, clumpy snow on the upper side of a sweep between fractions t0..t1.
    Snow comes in clumps (band hugging the top edge + cauliflower lumps) with bare-bark gaps between."""
    rng = rng or random.Random(1)
    N = normals(S); n = len(S)
    i0, i1 = int(t0*(n-1)), int(t1*(n-1))
    seg = [np.hypot(S[k+1][0]-S[k][0], S[k+1][1]-S[k][1]) for k in range(n-1)]
    def advance(i, dist):
        d = 0.0
        while i < i1 and d < dist:
            d += seg[i]; i += 1
        return i
    geoms = []
    i = i0
    while i < i1:
        r = max(S[i][2], min_r)
        if rng.random() < gap_p and i > i0:
            i = advance(i, r*rng.uniform(0.6, 1.4)); continue
        j = advance(i, r*rng.uniform(1.3, 2.8))
        if j - i < 1: break
        top = [np.array(S[k][:2]) + N[k]*S[k][2]*0.62 for k in range(i, j+1)]
        if len(top) >= 2:
            geoms.append(LineString(top).buffer(max(min_r*0.8, r*0.36*size), cap_style="round"))
        nl = max(3, int(len(top) * 1.3))
        for _ in range(nl):
            k = rng.randint(i, j); rk = max(S[k][2], min_r)
            c = np.array(S[k][:2]) + N[k]*rk*rng.uniform(0.55, 0.95)*lift/0.75
            geoms.append(Point(*c).buffer(max(min_r, min(9.0, rk*size*rng.uniform(0.2, 0.42))), quad_segs=10))
        i = j
    if not geoms: return Polygon()
    g = unary_union(geoms)
    return g.buffer(0.6).buffer(-0.6)

def bark_lines(S, poly, rng=None, w=OUTLINE):
    """Longitudinal bark texture strokes inside a tube."""
    rng = rng or random.Random(2)
    N = normals(S); n = len(S); out = []
    inner = poly.buffer(-0.9)
    for off in (-0.55, -0.15, 0.3):
        i = rng.randint(0, 3)
        while i < n - 4:
            L = rng.randint(4, 9)
            pts = []
            for k in range(i, min(i + L, n)):
                x, y, r = S[k]
                if r < 3.0: break
                o = off + rng.uniform(-0.08, 0.08)
                pts.append((x + N[k][0]*r*o, y + N[k][1]*r*o))
            if len(pts) >= 3:
                out.append(line(pts, w))
            i += L + rng.randint(2, 5)
    g = unary_union(out) if out else Polygon()
    return g.intersection(inner)

def knot(cx, cy, rx, ry, rot=0, w=OUTLINE):
    e = affinity.rotate(affinity.scale(Point(cx, cy).buffer(1, quad_segs=16), rx, ry), rot)
    return e.exterior.buffer(w/2)

# ---------------------------------------------------------------- plum blossom & bud
def blossom(cx, cy, d, rot=0.0):
    """returns dict layer->geometry for a 5-petal plum blossom of diameter d."""
    pr, pd = d * 0.235, d * 0.255
    petals, hi, outl = [], [], []
    for k in range(5):
        a = math.radians(rot - 90 + 72*k)
        px, py = cx + pd*math.cos(a), cy + pd*math.sin(a)
        p = Point(px, py).buffer(pr, quad_segs=16)
        # slight notch at the petal tip
        petals.append(p)
        # light rim toward the tip
        h = p.difference(Point(cx + pd*0.6*math.cos(a), cy + pd*0.6*math.sin(a)).buffer(pr*1.02))
        hi.append(h)
    body = unary_union(petals)
    # petal split lines (center to between petals) + outer outline
    for k in range(5):
        a = math.radians(rot - 90 + 72*k + 36)
        outl.append(LineString([(cx + d*0.13*math.cos(a), cy + d*0.13*math.sin(a)),
                                (cx + d*0.40*math.cos(a), cy + d*0.40*math.sin(a))]).buffer(OUTLINE/2, cap_style="round"))
    outl.append(body.exterior.buffer(OUTLINE/2))
    centre = Point(cx, cy).buffer(d*0.12, quad_segs=16)
    nst = 12 if d >= 22 else 8
    st = [Point(cx + d*0.2*math.cos(math.radians(rot + 360/nst*k)), cy + d*0.2*math.sin(math.radians(rot + 360/nst*k))).buffer(max(0.6, d*0.032))
          for k in range(nst)]
    stem = [LineString([(cx + d*0.12*math.cos(math.radians(rot + 30*k)), cy + d*0.12*math.sin(math.radians(rot + 30*k))),
                        (cx + d*0.19*math.cos(math.radians(rot + 30*k)), cy + d*0.19*math.sin(math.radians(rot + 30*k)))]).buffer(0.35)
            for k in range(12)] if d >= 26 else []
    return {"plum": body, "petal": unary_union(hi), "plumdk": unary_union(outl),
            "gold": unary_union([centre] + st), "goldline": unary_union(stem) if stem else Polygon(), "orange": Point(cx, cy).buffer(d*0.05, quad_segs=12) if d >= 26 else Polygon()}

def bud(cx, cy, d, ang=0.0):
    """round bud with dark calyx toward the stem (ang = direction to stem, degrees)."""
    b = Point(cx, cy).buffer(d/2, quad_segs=16)
    a = math.radians(ang)
    cal = Point(cx + d*0.42*math.cos(a), cy + d*0.42*math.sin(a)).buffer(d*0.28, quad_segs=12).intersection(b.buffer(0.3))
    hl = Point(cx - d*0.17*math.cos(a) - d*0.08, cy - d*0.17*math.sin(a) - d*0.1).buffer(max(0.6, d*0.12))
    return {"plum": b, "plumdk": cal, "petal": hl}

# ---------------------------------------------------------------- leaves (plum leaf clusters)
def leaf(x0, y0, L, W, ang, serr=True):
    t = np.linspace(0, 1, 40)
    half = W/2 * np.sin(np.pi * t**0.85)
    if serr:
        half = half * (1 + 0.16*np.abs(np.sin(t*np.pi*6)))
    top = np.c_[t*L, half]; bot = np.c_[t*L, -half][::-1]
    poly = Polygon(np.r_[top, bot]).buffer(0)
    poly = affinity.rotate(poly, ang, origin=(0, 0)); poly = affinity.translate(poly, x0, y0)
    a = math.radians(ang)
    vein = LineString([(x0 + 0.12*L*math.cos(a), y0 + 0.12*L*math.sin(a)),
                       (x0 + 0.85*L*math.cos(a), y0 + 0.85*L*math.sin(a))]).buffer(0.45, cap_style="round")
    return poly, vein

def leaf_cluster(x, y, L, angles, snow=True, rng=None):
    rng = rng or random.Random(5)
    body, veins, sn = [], [], []
    for a in angles:
        Lk = L * rng.uniform(0.8, 1.05)
        p, v = leaf(x, y, Lk, Lk*0.42, a)
        body.append(p); veins.append(v)
        if snow:
            cap = p.difference(affinity.translate(p, 0, Lk*0.42*0.26))
            sn.append(cap.buffer(-0.45).buffer(0.45))
    B = unary_union(body)
    Sn = unary_union(sn) if sn else Polygon()
    return {"leaf": B.difference(Sn), "leaflt": unary_union(veins).intersection(B.difference(Sn).buffer(-0.5)), "snow": Sn,
            "outline": B.boundary.buffer(OUTLINE/2)}

# ---------------------------------------------------------------- pine canopy (fans)
def pine_fan(hx, hy, R, kind="red", lobes=5, spread=168, rot=0.0):
    """Fan: sector body with scalloped outer edge; hub at (hx,hy) at the bottom.
    kind 'red' = vermilion fan, gold needles; 'white' = white fan, gold inner zone, dark needles."""
    a0, a1 = math.radians(-90 - spread/2), math.radians(-90 + spread/2)
    angs = np.linspace(a0 + math.radians(8), a1 - math.radians(8), lobes)
    lob = [Point(hx + R*0.74*math.cos(a), hy + R*0.74*math.sin(a)).buffer(R*0.29, quad_segs=16) for a in angs]
    arc = [(hx + R*0.80*math.cos(a), hy + R*0.80*math.sin(a)) for a in np.linspace(a0, a1, 40)]
    sector = Polygon([(hx, hy + R*0.04)] + arc)
    fan = unary_union(lob + [sector]).buffer(0.8).buffer(-0.8)
    clip = Polygon([(hx, hy + R*0.06)] + [(hx + 1.4*R*math.cos(a), hy + 1.4*R*math.sin(a)) for a in np.linspace(a0, a1, 40)])
    fan = fan.intersection(clip.buffer(R*0.08))
    fan = affinity.rotate(fan, rot, origin=(hx, hy))
    snow = fan.difference(affinity.translate(fan.buffer(-R*0.12), 0, R*0.07))
    upper = affinity.rotate(Polygon([(hx-2*R, hy-R*0.40), (hx+2*R, hy-R*0.40), (hx+2*R, hy-2*R), (hx-2*R, hy-2*R)]), rot, origin=(hx, hy))
    snow = snow.intersection(upper).buffer(-0.3).buffer(0.3)
    needles = []
    n_need = 13
    for k in range(n_need):
        a = math.radians(-90 - spread/2 + 10 + (spread - 20)*k/(n_need-1) + rot)
        r0, r1 = R*0.16, R*(0.62 + 0.06*((k % 2)))
        needles.append(LineString([(hx + r0*math.cos(a), hy + r0*math.sin(a)), (hx + r1*math.cos(a), hy + r1*math.sin(a))]))
    needles = unary_union([l.buffer(OUTLINE/2, cap_style="round") for l in needles]).intersection(fan.buffer(-0.8))
    hub = Point(hx, hy).buffer(R*0.16, quad_segs=16).intersection(fan.buffer(0.01))
    out = {"needle": needles.difference(snow.buffer(0.7)), "hub": hub, "snow": snow,
           "outline": fan.exterior.buffer(OUTLINE/2)}
    if kind == "red":
        out["body"] = ("vermilion", fan.difference(snow)); out["needle_col"] = "gold"
    else:
        inner = Point(hx, hy).buffer(R*0.46, quad_segs=24).intersection(fan).difference(snow)
        out["body"] = ("snow", fan.difference(snow).difference(inner)); out["inner"] = inner; out["needle_col"] = "barkdk"
    return out

def canopy(fans, kind):
    """fans: list of (hx,hy,R,rot) drawn back-to-front; later fans occlude earlier ones."""
    layers = {}
    occl = Polygon()
    built = [pine_fan(hx, hy, R, kind, rot=rot) for hx, hy, R, rot in fans]
    # front fan is the LAST: occlude backwards
    acc = []
    for f in reversed(built):
        mask = occl
        g = {}
        g["snow"] = f["snow"].difference(mask)
        body_col, body = f["body"]
        g[body_col + "_body"] = body.difference(mask)
        if "inner" in f: g["gold_inner"] = f["inner"].difference(mask)
        g["needle"] = f["needle"].difference(mask.buffer(0.7))
        g["hub"] = f["hub"].difference(mask)
        g["outline"] = f["outline"].difference(mask.buffer(0.2))
        acc.append(g)
        fan_shape = unary_union([f["snow"], body] + ([f["inner"]] if "inner" in f else []))
        occl = occl.union(fan_shape.buffer(0.6))
    for g in acc:
        for k, v in g.items():
            layers[k] = layers.get(k, Polygon()).union(v)
    return layers, occl

# ---------------------------------------------------------------- bamboo
def bamboo_blade(x0, y0, L, W, ang, snow_frac=0.33):
    """Blade: quick swell from the stem, long parallel body, short rounded taper (stitchable tip)."""
    t = np.linspace(0, 1, 60)
    up = np.clip(t / 0.18, 0, 1); up = up*up*(3 - 2*up)
    down = np.where(t > 0.72, 1 - ((t - 0.72) / 0.28)**2, 1.0)
    half = np.maximum(W/2 * (0.25 + 0.75*up) * np.clip(down, 0, 1), 0)
    top = np.c_[t*L, half]; bot = np.c_[t*L, -half][::-1]
    p = Polygon(np.r_[top, bot]).buffer(0).buffer(0.6).buffer(-0.6)
    p = affinity.rotate(p, ang, origin=(0, 0)); p = affinity.translate(p, x0, y0)
    a = math.radians(ang)
    d = np.array([math.cos(a), math.sin(a)])
    snow = p.difference(affinity.translate(p, 0, max(W*0.38, 2.4))).buffer(-0.5).buffer(0.5)
    hl = LineString([(x0 + 0.22*L*d[0], y0 + 0.22*L*d[1]), (x0 + 0.68*L*d[0], y0 + 0.68*L*d[1])]).buffer(0.62, cap_style="round")
    return p, snow, hl

def bamboo_cluster(x, y, L, angles, rng=None):
    rng = rng or random.Random(9)
    B, S, H = [], [], []
    for a in angles:
        Lk = L * rng.uniform(0.82, 1.05)
        p, s, h = bamboo_blade(x, y, Lk, Lk*0.24, a)
        B.append(p); S.append(s); H.append(h)
    Bu = unary_union(B); Su = unary_union(S)
    Su = Su.buffer(-0.45).buffer(0.45)
    return {"indigo": Bu.difference(Su), "lavender": unary_union(H).intersection(Bu.difference(Su).buffer(-1.0)).buffer(-0.1).buffer(0.1),
            "snow": Su.buffer(-0.45).buffer(0.45), "outline": Bu.boundary.buffer(OUTLINE/2)}

# ---------------------------------------------------------------- mist (kasumi)
def mist(x, y, L, rows=3, gap=3.0, rng=None):
    """Stacked rounded bars, outline only (triple run)."""
    rng = rng or random.Random(11)
    bars = []
    for i in range(rows):
        Li = L * rng.uniform(0.55, 1.0)
        xi = x + rng.uniform(-0.15, 0.25) * L
        yi = y + i * gap
        bars.append(LineString([(xi, yi), (xi + Li, yi)]).buffer(gap*0.42, cap_style="round"))
    u = unary_union(bars)
    rings = [u.exterior] if u.geom_type == "Polygon" else [g.exterior for g in u.geoms]
    inner = []
    for i in range(rows):   # inner long strokes for the streaked look
        Li = L * rng.uniform(0.3, 0.7); xi = x + rng.uniform(0, 0.3)*L
        inner.append(LineString([(xi, y + i*gap), (xi + Li, y + i*gap)]))
    g = unary_union([r.buffer(OUTLINE/2) for r in rings] + [l.buffer(OUTLINE/2, cap_style="round") for l in inner])
    return g.intersection(u.buffer(OUTLINE/2 + 0.01))
