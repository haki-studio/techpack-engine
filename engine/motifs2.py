"""Region-based motif library v2 — plum / pine / bamboo jacket. Units mm, y down.
Every motif returns a list of Region dicts:
  col   thread key            geom  shapely geometry
  st    'tatami' | 'satin' | 'bean' | 'run' | 'padded'
  ang   float degrees | ('radial', cx, cy) | 'auto' (satin across the short axis)
  grp   region-group code (for the region table)
"""
import math, random
import numpy as np
from shapely.geometry import Point, Polygon, LineString, MultiPolygon
from shapely.ops import unary_union, split
from shapely import affinity
from motifs import bez, catmull, sweep, taper, normals, line, OUTLINE

PAL = {   # key: (hex, name, use)
    "snow":     ("#F8F6F0", "Snow white",      "snow, sparkle, pine snow caps"),
    "cream":    ("#EADFC8", "Snow cream",      "snow shading, white-pine fans, anthers"),
    "grey":     ("#A4ABB2", "Shadow grey",     "snow shadow on bark, mist, white-pine outline"),
    "barklt":   ("#A47A58", "Bark light",      "bark ridges / highlights"),
    "bark":     ("#6E4C37", "Bark brown",      "trunk + limb fill, pine branches"),
    "barkdk":   ("#33231A", "Bark dark",       "crevices, underside, outlines, twigs, needles"),
    "plum":     ("#C8323A", "Plum red",        "petals, buds"),
    "petal":    ("#F0A39A", "Petal pink",      "petal rims, bud highlight"),
    "plumdk":   ("#7E1B25", "Plum deep",       "petal base ring, outlines, calyx"),
    "gold":     ("#E2A93F", "Gold",            "stamens, flower eye, white-pine inner, red-pine needles"),
    "orange":   ("#D96F24", "Orange",          "pine hubs"),
    "slate":    ("#2E4650", "Slate",           "leaf shade half"),
    "slatelt":  ("#5F7D87", "Slate light",     "leaf light half, leaf veins"),
    "indigo":   ("#474B88", "Indigo",          "bamboo shade half"),
    "lavender": ("#9C9DCF", "Lavender",        "bamboo light half"),
    "vermilion":("#C4462A", "Vermilion",       "red-pine fans"),
}
HEX = {k: v[0] for k, v in PAL.items()}
FABRIC = "#D9C4A0"

def R(col, geom, st, ang, grp):
    return dict(col=col, geom=geom, st=st, ang=ang, grp=grp)

def _polys(g):
    if g.is_empty: return []
    if g.geom_type == "Polygon": return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]

# ---------------------------------------------------------------- bark / limbs
def limb_regions(pts_r, rng, grp="TR", snow=None, texture=True, min_tex_r=3.0):
    """Tapered limb with 3 bark tones; returns (regions, poly, samples)."""
    poly, S = sweep(pts_r)
    N = normals(S)
    regs = []
    # main direction (for tatami angle along the limb)
    a = np.array(S[0][:2]); b = np.array(S[-1][:2])
    ang = math.degrees(math.atan2(b[1]-a[1], b[0]-a[0]))
    big = max(s[2] for s in S) >= 2.2
    if not big:
        regs.append(R("barkdk", poly, "satin", "auto", "TW"))
        return regs, poly, S
    # underside shadow band (lower 28% of width) and upper highlight strip (rides under the snow)
    lower, upper = [], []
    for i in range(len(S)-1):
        x, y, r = S[i]; x2, y2, r2 = S[i+1]
        if r < 2.2: continue
        p0 = np.array([x, y]) - N[i]*r*0.72; p1 = np.array([x2, y2]) - N[i+1]*r2*0.72
        lower.append(LineString([p0, p1]).buffer(r*0.34, cap_style="flat"))
        if r >= 4.0:
            q0 = np.array([x, y]) + N[i]*r*0.38; q1 = np.array([x2, y2]) + N[i+1]*r2*0.38
            upper.append(LineString([q0, q1]).buffer(max(0.75, r*0.16), cap_style="round"))
    low = unary_union(lower).intersection(poly) if lower else Polygon()
    up = unary_union(upper).intersection(poly.buffer(-0.6)).difference(low) if upper else Polygon()
    up = up.buffer(-0.4).buffer(0.4)
    body = poly.difference(low).difference(up)
    clean = body.buffer(-0.45).buffer(0.45)
    low = low.union(body.difference(clean)).intersection(poly)       # slivers of body go to the shade band
    body = clean.intersection(poly)
    regs.append(R("bark", body, "tatami", ang, grp))
    regs.append(R("barkdk", low, "tatami", ang, grp + "-shade"))
    regs.append(R("barklt", up, "satin", "auto", grp + "-ridge"))
    if texture:
        tex = []
        offs = (-0.62, -0.38, -0.12, 0.12, 0.3) if max(s_[2] for s_ in S) > 9 else (-0.45, -0.05, 0.25)
        for off in offs:
            i = rng.randint(0, 3)
            while i < len(S) - 4:
                L = rng.randint(4, 9); pts = []
                for k in range(i, min(i + L, len(S))):
                    x, y, r = S[k]
                    if r < min_tex_r: break
                    o = off + rng.uniform(-0.1, 0.1)
                    pts.append((x + N[k][0]*r*o, y + N[k][1]*r*o))
                if len(pts) >= 3: tex.append(line(pts, OUTLINE))
                i += L + rng.randint(1, 4)
        if tex:
            regs.append(R("barkdk", unary_union(tex).intersection(poly.buffer(-0.8)), "bean", None, grp + "-crevice"))
    regs.append(R("barkdk", poly.boundary.buffer(OUTLINE/2), "bean", None, grp + "-outline"))
    return regs, poly, S

def knot(cx, cy, rx, ry, rot=0):
    e = affinity.rotate(affinity.scale(Point(cx, cy).buffer(1, quad_segs=16), rx, ry), rot)
    return [R("barkdk", e.difference(e.buffer(-0.9)), "satin", "auto", "TR-knot"),
            R("barklt", e.buffer(-0.9), "satin", rot, "TR-knot")]

# ---------------------------------------------------------------- snow
def snow_regions(S, t0, t1, rng, size=1.2, min_r=2.0, gap_p=0.12, grp="SN"):
    """Clumpy snow riding the upper side of a limb + cream underside shading + grey shadow on the bark."""
    N = normals(S); n = len(S)
    i0, i1 = int(t0*(n-1)), int(t1*(n-1))
    seg = [np.hypot(S[k+1][0]-S[k][0], S[k+1][1]-S[k][1]) for k in range(n-1)]
    def adv(i, dist):
        d = 0.0
        while i < i1 and d < dist: d += seg[i]; i += 1
        return i
    geoms = []; i = i0
    while i < i1:
        r = max(S[i][2], min_r)
        if rng.random() < gap_p and i > i0:
            i = adv(i, r*rng.uniform(0.5, 1.2)); continue
        j = adv(i, r*rng.uniform(1.4, 3.0))
        if j - i < 1: break
        top = [np.array(S[k][:2]) + N[k]*S[k][2]*0.6 for k in range(i, j+1)]
        if len(top) >= 2:
            geoms.append(LineString(top).buffer(max(min_r*0.8, r*min(0.30, 0.22*size)), cap_style="round"))
        for _ in range(max(3, int(len(top)*1.6))):
            k = rng.randint(i, j); rk = max(S[k][2], min_r)
            lr = max(min_r, min(11.0, rk*size*rng.uniform(0.14, 0.36)))
            c = np.array(S[k][:2]) + N[k]*(rk*0.62 + lr*rng.uniform(0.15, 0.75))
            geoms.append(Point(*c).buffer(lr, quad_segs=12))
        i = j
    if not geoms: return [], Polygon()
    g = unary_union(geoms).buffer(0.6).buffer(-0.6)
    lumps = [x for x in geoms if x.geom_type == "Polygon" and x.area < 400]
    nm = np.mean([N[k] for k in range(i0, max(i0+1, i1))], axis=0)
    ang = math.degrees(math.atan2(nm[1], nm[0]))          # stitches run up/down across the snow
    shade = g.difference(affinity.translate(g, nm[0]*2.2, nm[1]*2.2)).buffer(-0.35).buffer(0.35)
    shadow = affinity.translate(g, -nm[0]*2.2 + 0.4, -nm[1]*2.2).difference(g)
    arcs = []
    for lp in lumps:
        c = lp.centroid; rr = math.sqrt(lp.area/math.pi)
        if rr < 2.2: continue
        a0 = math.atan2(nm[1], nm[0])       # upper contour of each lump
        pts = [(c.x + rr*0.82*math.cos(a0 + t), c.y + rr*0.82*math.sin(a0 + t)) for t in np.linspace(-0.9, 0.9, 12)]
        arcs.append(LineString(pts).buffer(0.35, cap_style="round"))
    seams = unary_union(arcs).intersection(g.buffer(-1.0)).difference(shade.buffer(0.3)) if arcs else Polygon()
    regs = [R("grey", shadow, "satin", "auto", grp + "-shadow"),
            R("snow", g.difference(shade).difference(seams), "padded", ang, grp),
            R("cream", shade, "satin", ang, grp + "-shade"),
            R("grey", seams, "run", None, grp + "-lump")]
    return regs, g

# ---------------------------------------------------------------- blossoms + buds
def blossom(cx, cy, d, rot=0.0):
    pr, pd = d*0.235, d*0.255
    regs = []
    petals = []
    for k in range(5):
        a = math.radians(rot - 90 + 72*k)
        p = Point(cx + pd*math.cos(a), cy + pd*math.sin(a)).buffer(pr, quad_segs=18)
        wedge = Polygon([(cx, cy)] + [(cx + d*math.cos(a + math.radians(t)), cy + d*math.sin(a + math.radians(t)))
                                       for t in np.linspace(-36, 36, 9)])
        petals.append(p.intersection(wedge))
    flower = unary_union([p.buffer(0.05) for p in petals]).buffer(-0.05)
    base = Point(cx, cy).buffer(d*0.17, quad_segs=18)
    eye = Point(cx, cy).buffer(d*0.095, quad_segs=16)
    rimR = d*0.36
    for p in petals:
        rim = p.difference(Point(cx, cy).buffer(rimR, quad_segs=24))
        regs.append(R("plum", p.difference(rim).difference(base), "satin", ("radial", cx, cy), "BL-petal"))
        regs.append(R("petal", rim, "satin", ("radial", cx, cy), "BL-rim"))
    regs.append(R("plumdk", base.difference(eye), "satin", ("radial", cx, cy), "BL-base"))
    regs.append(R("gold", eye, "satin", rot, "BL-eye"))
    n_st = 10 if d >= 24 else 7
    st_lines, anth = [], []
    for k in range(n_st):
        a = math.radians(rot + 360/n_st*k + 18)
        r0, r1 = d*0.10, d*(0.25 if k % 2 else 0.22)
        st_lines.append(LineString([(cx + r0*math.cos(a), cy + r0*math.sin(a)), (cx + r1*math.cos(a), cy + r1*math.sin(a))]))
        anth.append(Point(cx + (r1 + 0.35)*math.cos(a), cy + (r1 + 0.35)*math.sin(a)).buffer(max(0.6, d*0.03)))
    if d >= 18:
        regs.append(R("gold", unary_union([l.buffer(OUTLINE/2, cap_style="round") for l in st_lines]), "bean", None, "BL-stamen"))
    regs.append(R("cream", unary_union(anth), "satin", "auto", "BL-anther"))
    splits = [LineString([(cx + d*0.17*math.cos(math.radians(rot - 90 + 72*k + 36)), cy + d*0.17*math.sin(math.radians(rot - 90 + 72*k + 36))),
                          (cx + d*0.42*math.cos(math.radians(rot - 90 + 72*k + 36)), cy + d*0.42*math.sin(math.radians(rot - 90 + 72*k + 36)))]).buffer(OUTLINE/2, cap_style="round")
              for k in range(5)]
    regs.append(R("plumdk", unary_union(splits + [flower.boundary.buffer(OUTLINE/2)]), "bean", None, "BL-outline"))
    return regs, flower.buffer(OUTLINE/2)

def bud(cx, cy, d, ang_to_stem):
    b = Point(cx, cy).buffer(d/2, quad_segs=16)
    a = math.radians(ang_to_stem)
    cal = Point(cx + d*0.45*math.cos(a), cy + d*0.45*math.sin(a)).buffer(d*0.3, quad_segs=12).intersection(b.buffer(0.2))
    hl = Point(cx - d*0.18*math.cos(a) - d*0.06, cy - d*0.18*math.sin(a) - d*0.1).buffer(max(0.62, d*0.12))
    body = b.difference(cal).difference(hl)
    return [R("plum", body, "satin", ang_to_stem + 90, "BD"), R("plumdk", cal, "satin", "auto", "BD-calyx"),
            R("petal", hl, "satin", "auto", "BD-hl")], b

# ---------------------------------------------------------------- leaves
def leaf_shape(L, W, serr=True):
    t = np.linspace(0, 1, 48)
    half = W/2 * np.sin(np.pi * t**0.8)
    if serr: half = half * (1 + 0.14*np.abs(np.sin(t*np.pi*6)))
    return Polygon(np.r_[np.c_[t*L, half], np.c_[t*L, -half][::-1]]).buffer(0)

def leaf_cluster(x, y, L, angles, rng, snow=True):
    regs, allg = [], []
    for a in angles:
        Lk = L*rng.uniform(0.82, 1.05); W = Lk*0.42
        p = leaf_shape(Lk, W)
        upper = p.intersection(Polygon([(-1, 0), (Lk+1, 0), (Lk+1, -W), (-1, -W)]))
        lower = p.difference(upper)
        T = lambda g: affinity.translate(affinity.rotate(g, a, origin=(0, 0)), x, y)
        P, U, Lw = T(p), T(upper), T(lower)
        light, dark = (U, Lw) if math.sin(math.radians(a)) >= -0.2 else (Lw, U)
        sn = P.difference(affinity.translate(P, 0, W*0.30)).buffer(-0.45).buffer(0.45) if snow else Polygon()
        vein = T(LineString([(0.1*Lk, 0), (0.88*Lk, 0)]).buffer(0.4, cap_style="round")).intersection(P.buffer(-0.6))
        regs += [R("slatelt", light.difference(sn).difference(vein), "satin", a + 50, "LF-light"),
                 R("slate", dark.difference(sn).difference(vein), "satin", a - 50, "LF-shade"),
                 R("slatelt", vein, "bean", None, "LF-vein"),
                 R("snow", sn, "satin", a + 90, "LF-snow"),
                 R("barkdk", P.boundary.buffer(OUTLINE/2), "bean", None, "LF-outline")]
        allg.append(P)
    return regs, unary_union(allg)

# ---------------------------------------------------------------- bamboo
def blade_shape(L, W):
    t = np.linspace(0, 1, 70)
    up = np.clip(t/0.15, 0, 1); up = up*up*(3-2*up)
    down = np.where(t > 0.62, 1 - (t-0.62)/0.38, 1.0)
    half = W/2*(0.3 + 0.7*up)*np.clip(down, 0, 1)**0.85
    return Polygon(np.r_[np.c_[t*L, half], np.c_[t*L, -half][::-1]]).buffer(0)

def bamboo_cluster(x, y, L, angles, rng):
    regs, allg = [], []
    for a in angles:
        Lk = L*rng.uniform(0.82, 1.06); W = Lk*0.2
        p = blade_shape(Lk, W)
        upper = p.intersection(Polygon([(-1, 0), (Lk+1, 0), (Lk+1, -W), (-1, -W)]))
        lower = p.difference(upper)
        T = lambda g: affinity.translate(affinity.rotate(g, a, origin=(0, 0)), x, y)
        P, U, Lw = T(p), T(upper), T(lower)
        light, dark = (U, Lw) if math.cos(math.radians(a)) >= 0 else (Lw, U)
        sn = P.difference(affinity.translate(P, 0, max(W*0.42, 2.2))).buffer(-0.45).buffer(0.45)
        regs += [R("lavender", light.difference(sn), "satin", a + 55, "BB-light"),
                 R("indigo", dark.difference(sn), "satin", a - 55, "BB-shade"),
                 R("snow", sn, "satin", a + 90, "BB-snow"),
                 R("barkdk", P.boundary.buffer(OUTLINE/2), "bean", None, "BB-outline")]
        allg.append(P)
    return regs, unary_union(allg)

# ---------------------------------------------------------------- pine fans
def fan_shape(hx, hy, R_, spread=168, lobes=5, rot=0.0):
    a0, a1 = math.radians(-90 - spread/2), math.radians(-90 + spread/2)
    angs = np.linspace(a0 + math.radians(8), a1 - math.radians(8), lobes)
    lob = [Point(hx + R_*0.74*math.cos(a), hy + R_*0.74*math.sin(a)).buffer(R_*0.29, quad_segs=16) for a in angs]
    arc = [(hx + R_*0.80*math.cos(a), hy + R_*0.80*math.sin(a)) for a in np.linspace(a0, a1, 40)]
    fan = unary_union(lob + [Polygon([(hx, hy + R_*0.04)] + arc)]).buffer(0.8).buffer(-0.8)
    clip = Polygon([(hx, hy + R_*0.06)] + [(hx + 1.4*R_*math.cos(a), hy + 1.4*R_*math.sin(a)) for a in np.linspace(a0, a1, 40)])
    fan = fan.intersection(clip.buffer(R_*0.08))
    return affinity.rotate(fan, rot, origin=(hx, hy))

def pine_fan(hx, hy, R_, kind, rot=0.0, spread=168):
    fan = fan_shape(hx, hy, R_, spread, rot=rot)
    upper = affinity.rotate(Polygon([(hx-2*R_, hy-R_*0.42), (hx+2*R_, hy-R_*0.42), (hx+2*R_, hy-2*R_), (hx-2*R_, hy-2*R_)]), rot, origin=(hx, hy))
    snow = fan.difference(affinity.translate(fan.buffer(-R_*0.14), 0, R_*0.08)).intersection(upper).buffer(-0.4).buffer(0.4)
    snow_shade = snow.difference(affinity.translate(snow, 0, -1.8)).buffer(-0.3).buffer(0.3)
    nd = []
    for k in range(15):
        a = math.radians(-90 - spread/2 + 9 + (spread-18)*k/14 + rot)
        r0, r1 = R_*0.17, R_*(0.60 + 0.07*(k % 2))
        nd.append(LineString([(hx + r0*math.cos(a), hy + r0*math.sin(a)), (hx + r1*math.cos(a), hy + r1*math.sin(a))]).buffer(OUTLINE/2, cap_style="round"))
    needles = unary_union(nd).intersection(fan.buffer(-0.8)).difference(snow.buffer(0.6))
    hub = Point(hx, hy).buffer(R_*0.17, quad_segs=16).intersection(fan.buffer(0.01))
    rad = ("radial", hx, hy)
    regs = []
    if kind == "red":
        regs.append(R("vermilion", fan.difference(snow).difference(hub), "tatami", rad, "PR-fan"))
        regs.append(R("gold", needles, "bean", None, "PR-needle"))
        regs.append(R("barkdk", fan.exterior.buffer(OUTLINE/2), "bean", None, "PR-outline"))
    else:
        inner = Point(hx, hy).buffer(R_*0.46, quad_segs=24).intersection(fan).difference(snow).difference(hub)
        regs.append(R("cream", fan.difference(snow).difference(inner).difference(hub), "tatami", rad, "PW-fan"))
        regs.append(R("gold", inner, "tatami", rad, "PW-inner"))
        regs.append(R("barkdk", needles, "bean", None, "PW-needle"))
        regs.append(R("grey", fan.exterior.buffer(OUTLINE/2), "bean", None, "PW-outline"))
    regs.append(R("orange", hub, "satin", rad, "P-hub"))
    regs.append(R("snow", snow.difference(snow_shade), "padded", rot + 90, "P-snow"))
    regs.append(R("cream", snow_shade, "satin", rot + 90, "P-snow-shade"))
    return regs, fan

# ---------------------------------------------------------------- mist
def mist(x, y, L, rows, gap, rng):
    bars = []
    for i in range(rows):
        Li = L*rng.uniform(0.55, 1.0); xi = x + rng.uniform(-0.15, 0.25)*L
        bars.append(LineString([(xi, y + i*gap), (xi + Li, y + i*gap)]).buffer(gap*0.42, cap_style="round"))
    u = unary_union(bars)
    rings = [p.exterior for p in _polys(u)]
    inner = []
    for i in range(rows):
        Li = L*rng.uniform(0.3, 0.7); xi = x + rng.uniform(0, 0.3)*L
        inner.append(LineString([(xi, y + i*gap), (xi + Li, y + i*gap)]))
    g = unary_union([r.buffer(OUTLINE/2) for r in rings] + [l.buffer(OUTLINE/2, cap_style="round") for l in inner])
    return [R("grey", g.intersection(u.buffer(OUTLINE/2 + 0.01)), "bean", None, "MI")], u
