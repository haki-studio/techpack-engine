"""Rev B structure motifs for the Castle Falls jacket (review Rev A -> A13: trace the STITCH STRUCTURE, not only tones).
Units mm, y down. Region dicts like cf_motifs.R (col, geom, st, ang, grp) + ko / kob / unit.
  pack_lobes + lobe_regions  cumulus clouds + pine clumps as overlapping domes (adapted from grand-line gl_motifs), rows fanned
                             from each lobe base (turning tatami), lit rim / body / shaded underside per lobe
  dir_field + region_angle   local stroke direction of the mockup (structure tensor) -> stitch angle per traced region
  strata                     parallel strata / bark lines inside a region along its traced direction
  fall                       waterfall as twisted rope cords (slanted satin segments) over a blue ground, wide base, mist foot
  castle2, pagoda, gate_tower, crag, house  buildings + spire drawn as objects (redrawn from the low-res mockup)"""
import math, random
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import Point, Polygon, LineString, MultiLineString, box
from shapely.ops import unary_union
from shapely import affinity
from cf_motifs import R, polys

def smooth(g, d=0.35):
    return g.buffer(d, join_style="round").buffer(-2 * d, join_style="round").buffer(d, join_style="round")

# ---------------------------------------------------------------- lobes (clouds, pine clumps)
EX, EY = 1.16, 0.9
def ell(cx, cy, r, ex=EX, ey=EY): return affinity.scale(Point(cx, cy).buffer(1.0, quad_segs=20), r * ex, r * ey, origin=(cx, cy))

def pack_lobes(C, R0, rng, rjit=0.22, dy=0.62, dx=1.18, inset=0.45, rmin=2.2):
    """overlapping discs whose union follows outline C; lower discs sit in front (z = their base y)"""
    b = C.bounds; lobes = []
    y = b[3] - 0.45 * R0; row = 0
    while y > b[1] - 0.2 * R0:
        x = b[0] + (0.6 * R0 if row % 2 else 0.0) + rng.uniform(-0.2, 0.2) * R0
        while x < b[2] + 0.3 * R0:
            r = R0 * rng.uniform(1 - rjit, 1 + rjit)
            cx, cy = x + rng.uniform(-0.18, 0.18) * R0, y + rng.uniform(-0.15, 0.15) * R0
            inner = C.buffer(-inset * r)
            if not inner.is_empty and inner.contains(Point(cx, cy)): lobes.append([cx, cy, r])
            x += dx * R0
        y -= dy * R0; row += 1
    for _ in range(3):
        U = unary_union([Point(cx, cy).buffer(r) for cx, cy, r in lobes]) if lobes else Polygon()
        miss = C.difference(U.buffer(0.3)); added = 0
        for p in sorted(polys(miss), key=lambda p: -p.area):
            if p.area < (0.45 * R0) ** 2: continue
            c = p.representative_point(); r = max(rmin, min(R0, math.sqrt(p.area / math.pi) * 1.25))
            lobes.append([c.x, c.y - 0.15 * r, r]); added += 1
        if not added: break
    lobes = [l for l in lobes if l[2] >= rmin]
    for l in lobes: l.append(l[1] + rng.uniform(-0.25, 0.25) * R0)
    return lobes

def lobe_regions(lobes, tones, C=None, grp="CL", unit=None, gap=0.0, ex=EX, ey=EY):
    """each lobe's visible dome -> lit rim (top), body, shaded underside where the front lobe overlaps + its base.
    tones(lobe) -> (body, rim or None, shade). Rows fan from the lobe base (turning tatami follows the dome)."""
    discs = []
    for cx, cy, r, z in lobes:
        d = ell(cx, cy, r, ex, ey)
        if C is not None: d = d.intersection(C)
        discs.append((z, cx, cy, r, d))
    discs.sort(key=lambda t: -t[0])
    regs = []; front = Polygon()
    for z, cx, cy, r, d in discs:
        V = (d.difference(front.buffer(gap) if gap else front) if not front.is_empty else d).buffer(0)
        V = smooth(V, 0.3)
        if V.area < 2.0:
            front = front.union(d); continue
        bcol, rcol, scol = tones((cx, cy, r))
        wr = min(2.6, max(1.1, 0.3 * r)); ws = min(1.8, max(0.9, 0.2 * r))
        shade = V.intersection(front.buffer(gap + ws)) if not front.is_empty else Polygon()
        shade = shade.union(V.intersection(box(cx - 2 * r, cy + max(0.4 * r, 0.9 * r * ey - ws), cx + 2 * r, cy + 2 * r)))
        shade = smooth(shade.intersection(V), 0.4) if r >= 3.0 else Polygon()
        rim = Polygon()
        if rcol and r >= 3.6:
            rim = V.intersection(ell(cx, cy, r, ex, ey).difference(ell(cx, cy + 0.35 * wr, r - wr, ex, ey))).intersection(box(cx - 2 * r, cy - 2 * r, cx + 2 * r, cy + 0.15 * r))
            rim = smooth(rim.difference(shade.buffer(0.2)), 0.45)
        body = V.difference(rim).difference(shade).buffer(0)
        bc = body.buffer(-0.42).buffer(0.42).intersection(body); sl = body.difference(bc)
        if not sl.is_empty and sl.area > 0.01 and not shade.is_empty: body = bc; shade = shade.union(sl).buffer(0)
        fa = ("radial", cx, cy + 0.75 * r)
        for col, g, gg in ((rcol, rim, grp + "-rim"), (bcol, body, grp), (scol, shade, grp + "-shade")):
            if col and not g.is_empty and g.area > 0.6: regs.append(R(col, g, "tatami", fa, gg, unit=unit))
        front = front.union(d)
    return regs, front

# ---------------------------------------------------------------- direction field (structure tensor of the mockup)
def dir_field(rgb, ppm, sigma_mm=2.5):
    """angle (deg, image coords y down) of the local stroke direction = direction of least luminance change"""
    L = rgb[..., 0] * 0.3 + rgb[..., 1] * 0.59 + rgb[..., 2] * 0.11
    L = ndi.gaussian_filter(L, 0.6 * ppm / 3)
    gx = ndi.sobel(L, 1); gy = ndi.sobel(L, 0)
    s = sigma_mm * ppm
    jxx = ndi.gaussian_filter(gx * gx, s); jyy = ndi.gaussian_filter(gy * gy, s); jxy = ndi.gaussian_filter(gx * gy, s)
    th = 0.5 * np.degrees(np.arctan2(2 * jxy, jxx - jyy)) + 90.0          # along the strokes
    coh = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / np.maximum(jxx + jyy, 1e-6)
    return th, coh

def region_angle(field, geom, to_px, default=90.0, min_coh=0.12):
    th, coh = field; H, W = th.shape
    b = geom.bounds; pts = []
    from shapely.prepared import prep
    pg = prep(geom); step = max(0.8, math.sqrt(geom.area) / 12)
    for x in np.arange(b[0], b[2], step):
        for y in np.arange(b[1], b[3], step):
            if pg.contains(Point(x, y)):
                c, r = to_px(x, y)
                if 0 <= r < H and 0 <= c < W: pts.append((th[r, c], coh[r, c]))
    if not pts: return default, 0.0
    a = np.radians(2 * np.array([p[0] for p in pts])); w = np.array([p[1] for p in pts])
    C, S = (w * np.cos(a)).sum(), (w * np.sin(a)).sum()
    c_ = math.hypot(C, S) / max(w.sum(), 1e-6)
    if c_ < min_coh: return default, c_
    return (0.5 * math.degrees(math.atan2(S, C))) % 180, c_

def strata(geom, ang, spacing, cols, grp, w=0.45, inset=0.9, min_len=3.0, phase=0.0, unit=None):
    """parallel lines at `ang` through the region (bean lines on top, ko=False), colours cycling through cols"""
    g = geom.buffer(-inset)
    if g.is_empty: return []
    c = geom.centroid; D = math.hypot(geom.bounds[2] - geom.bounds[0], geom.bounds[3] - geom.bounds[1])
    a = math.radians(ang); ux, uy = math.cos(a), math.sin(a); nx, ny = -uy, ux
    out = []; k = 0
    for off in np.arange(-D / 2 + phase, D / 2, spacing):
        p0 = (c.x + nx * off - ux * D, c.y + ny * off - uy * D); p1 = (c.x + nx * off + ux * D, c.y + ny * off + uy * D)
        seg = LineString([p0, p1]).intersection(g)
        for s in getattr(seg, "geoms", [seg]):
            if s.geom_type != "LineString" or s.length < min_len: continue
            out.append(R(cols[k % len(cols)], s.buffer(w, cap_style="round"), "bean", None, grp, ko=False, unit=unit))
        k += 1
    return out

# ---------------------------------------------------------------- waterfall: twisted rope cords
def fall(top, bot, w_top, w_bot, rng, cols=("cf_white", "cf_white", "cf_skylt", "cf_white", "cf_cream"), ground="cf_sky",
         cord=3.2, gap=0.9, seg=4.6, twist=58.0, wobble=1.2, mist_cols=("cf_white", "cf_cream", "cf_mist"), foot_w=None, unit=None):
    """top/bot = (x, y) of the fall's centre line; returns regions + outline. Cords are slanted satin segments (rope twist),
    alternating white / light blue; the blue ground shows in the gaps; a wide flared base and mist lobes at the foot."""
    (x0, y0), (x1, y1) = top, bot; H = y1 - y0
    def half(t): return (w_top + (w_bot - w_top) * (t ** 1.6)) / 2
    def cxat(t): return x0 + (x1 - x0) * t + wobble * math.sin(t * math.pi * 1.3)
    ts = np.linspace(0, 1, 40)
    left = [(cxat(t) - half(t), y0 + H * t) for t in ts]; right = [(cxat(t) + half(t), y0 + H * t) for t in ts][::-1]
    outline = Polygon(left + right).buffer(0)
    regs = [R(ground, outline, "tatami", 90.0, "FALL", unit=unit)]
    n = max(2, int(round(w_bot / (cord + gap))))
    for i in range(n):
        u = (i + 0.5) / n - 0.5                     # lateral position -1/2 .. 1/2
        ph = rng.uniform(0, 2 * math.pi); amp = rng.uniform(0.3, 0.7)
        cl = []; cr = []
        for t in np.linspace(0, 1, 36):
            hw = half(t); xc = cxat(t) + 2 * u * hw * 0.96 + amp * math.sin(ph + t * 9.0)
            wd = min(cord, 2 * hw / n - gap) / 2 * (0.85 + 0.15 * math.sin(ph * 2 + t * 13.0))
            cl.append((xc - wd, y0 + H * t)); cr.append((xc + wd, y0 + H * t))
        strip = Polygon(cl + cr[::-1]).buffer(0).intersection(outline.buffer(-0.2))
        if strip.is_empty or strip.area < 2: continue
        col = cols[i % len(cols)]
        regs.append(R(col, strip, "satin", "auto", "FALL-cord", unit=unit))
        if col == "cf_white" and H > 30:             # light-blue twist streak down the middle of some white cords
            core = LineString([((a[0] + b[0]) / 2, a[1]) for a, b in zip(cl[3:-6], cr[3:-6])]).buffer(0.55)
            if rng.random() < 0.5: regs.append(R("cf_skylt", core.intersection(strip.buffer(-0.6)), "run", None, "FALL-ln", unit=unit, ko=False))
    # mist at the foot: small lobes across the base
    fw = foot_w or w_bot * 1.5
    lobes = []
    for j in range(max(3, int(fw / 6))):
        lx = x1 - fw / 2 + (j + 0.5) * fw / max(3, int(fw / 6)); lobes.append([lx + rng.uniform(-1, 1), y1 + rng.uniform(-2.5, 0.5), rng.uniform(3.2, 4.6), y1 + rng.uniform(0, 2)])
    mr, mo = lobe_regions(lobes, lambda l: (mist_cols[0], None, mist_cols[2]), grp="FALL-foam", unit=unit)
    regs += mr
    return regs, outline.union(mo)

# ---------------------------------------------------------------- roofs + buildings
def roof_poly(cx, top, bot, w_top, w_eave, lift=3.0, n=24):
    left = [(cx - w_top / 2 - (w_eave - w_top) / 2 * (t ** 1.7), top + (bot - top) * t - lift * t ** 6) for t in np.linspace(0, 1, n)]
    right = [(2 * cx - x, y) for x, y in left][::-1]
    return Polygon(left + [(cx - w_eave / 2 + 2.5, bot + 1.0), (cx + w_eave / 2 - 2.5, bot + 1.0)] + right).buffer(0)

def roof(cx, top, bot, w_top, w_eave, lift=3.0, rib=2.6, eave_col="cf_gold", rib_col="cf_sky", stud_col="cf_white", studs=True, unit=None, grp="ROOF"):
    """hip roof: navy fill sewn DOWN the slope (tile direction), tile ribs from the ridge fanning to the eave, curved eave satin
    with upturned tips, studs along the eave, ridge cap line"""
    rp = roof_poly(cx, top, bot, w_top, w_eave, lift)
    regs = [R("cf_navy", rp, "tatami", 90.0, grp, unit=unit)]
    inner = rp.buffer(-0.7)
    n = max(3, int((w_eave - 4) / rib))
    for k in range(n + 1):
        f = k / n
        xt = cx - w_top / 2 + w_top * f; xb = cx - w_eave / 2 + 3 + (w_eave - 6) * f
        ln = LineString([(xt, top + 1.0), (xb, bot - 2.8 - (lift * 0.8 if abs(f - 0.5) > 0.42 else 0))]).intersection(inner)
        if ln.length > 2.5: regs.append(R(rib_col, ln.buffer(0.4, cap_style="flat"), "run", None, grp + "-ln", ko=False, unit=unit))
    tips = [(cx - w_eave / 2, bot - lift - 0.6), (cx - w_eave / 2 + 5, bot - 0.7), (cx + w_eave / 2 - 5, bot - 0.7), (cx + w_eave / 2, bot - lift - 0.6)]
    eave = LineString(tips).buffer(0.85, cap_style="round")
    regs.append(R(eave_col, eave, "satin", "auto", "ORN", unit=unit))
    regs.append(R(eave_col, LineString([(cx - w_top / 2, top + 0.3), (cx + w_top / 2, top + 0.3)]).buffer(0.75), "satin", "auto", "ORN", unit=unit, ko=False))
    if studs:
        m = int((w_eave - 12) / 5.5)
        for k in range(m + 1):
            x = cx - (w_eave - 12) / 2 + k * (w_eave - 12) / max(1, m)
            regs.append(R(stud_col, Point(x, bot - 2.4).buffer(0.62), "satin", "auto", "DOT", unit=unit, ko=False))
        for s in (-1, 1): regs.append(R(eave_col, Point(cx + s * (w_eave / 2 - 0.4), bot - lift - 1.0).buffer(1.1), "satin", "auto", "DOT", unit=unit))
    return regs, rp

def wall_band(cx, y, h, w, win_w=2.6, win_gap=3.6, wall_col="cf_white", win_col="cf_navy", lintel_col="cf_gold", unit=None):
    """lit plaster wall with a window band: navy windows with a gold lintel line above + slate sill"""
    regs = [R(wall_col, box(cx - w / 2, y, cx + w / 2, y + h), "tatami", 0.0, "WALL", unit=unit)]
    if h >= 7:
        regs.append(R(lintel_col, box(cx - w / 2 + 1, y + 1.4, cx + w / 2 - 1, y + 2.3), "satin", 90.0, "ORN", unit=unit, ko=False))
        n = int((w - 4) / (win_w + win_gap))
        x0 = cx - (n * (win_w + win_gap) - win_gap) / 2
        for k in range(n):
            x = x0 + k * (win_w + win_gap)
            regs.append(R(win_col, box(x, y + 3.4, x + win_w, y + min(h - 1.8, 3.4 + 4.2)), "satin", 90.0, "WIN", unit=unit, ko=False))
    regs.append(R("cf_slate", box(cx - w / 2, y + h - 1.4, cx + w / 2, y + h), "satin", 90.0, "TMB", unit=unit, ko=False))
    return regs, box(cx - w / 2, y, cx + w / 2, y + h)

def shachi(x, y, s, col="cf_gold", unit=None):
    """gold fish ornament on a ridge end: curled body + flared tail (s = +1 faces right)"""
    body = LineString([(x, y), (x + s * 1.6, y - 3.5), (x + s * 0.6, y - 6.5), (x - s * 1.4, y - 8.6)]).buffer(1.35, cap_style="round")
    tail = Polygon([(x - s * 1.4, y - 8.6), (x - s * 4.2, y - 11.2), (x - s * 0.2, y - 10.6), (x + s * 0.8, y - 12.6)]).buffer(0.5)
    return [R(col, unary_union([body, tail]).buffer(0), "satin", "auto", "ORN", unit=unit)]

def castle2(cx, y0, unit=None, T=None, bal=(176.0, 24.0)):
    """3-tier castle as in the founder's front close-up / reference.png (Rev B): per tier a hip roof with tile ribs, curved gold
    eave + white studs, lit white wall with a window band; karahafu on the top roof, two chidori gables on the middle + lower
    roofs, gold shachi; the lowest wall is the lantern band; red balustrade with posts below. Returns regions, outline, bottom y."""
    regs = []; outline = []
    T = T or [(32.0, 22.0, 55.0, 132.0, 80.0), (23.0, 17.0, 92.0, 164.0, 106.0), (28.0, 8.0, 116.0, 190.0, 150.0)]   # roof h, wall h, ridge w, eave w, wall w
    y = y0
    for s in (-1, 1): regs += shachi(cx + s * (T[0][2] / 2 - 4), y + 0.5, s, unit=unit)
    for i, (rh, wh, rw, ew, ww) in enumerate(T):
        rr, rp = roof(cx, y, y + rh, rw, ew, lift=3.6, unit=unit); regs += rr; outline.append(rp)
        if i == 0:
            arc = [(cx + 13 * math.cos(a), y + rh * 0.92 - 10 * math.sin(a) ** 0.8) for a in np.linspace(0, math.pi, 24)]
            regs.append(R("cf_white", Polygon(arc).buffer(-1.0), "satin", 90.0, "WALL", unit=unit, ko=False))
            regs.append(R("cf_gold", LineString(arc).buffer(0.75), "satin", "auto", "ORN", unit=unit, ko=False))
            for s in (-1, 1): regs.append(R("cf_navy", Point(cx + s * 4.5, y + rh * 0.92 - 3.2).buffer(1.5), "satin", "auto", "WIN", unit=unit, ko=False))
        if i >= 1:
            gw = 26.0 if i == 1 else 30.0
            for gx in ((cx - 0.0,) if i == 1 else (cx - 36, cx + 36)):
                tri = Polygon([(gx - gw / 2, y + rh * 0.88), (gx, y + rh * 0.22), (gx + gw / 2, y + rh * 0.88)])
                regs.append(R("cf_white", tri.buffer(-1.0), "satin", 90.0, "WALL", unit=unit, ko=False))
                regs.append(R("cf_gold", LineString([(gx - gw / 2, y + rh * 0.88), (gx, y + rh * 0.22), (gx + gw / 2, y + rh * 0.88)]).buffer(0.7), "satin", "auto", "ORN", unit=unit, ko=False))
                regs.append(R("cf_gold", Point(gx, y + rh * 0.55).buffer(1.1), "satin", "auto", "DOT", unit=unit, ko=False))
        y += rh
        if wh >= 12:
            wr, wp = wall_band(cx, y - 0.6, wh + 0.6, ww, unit=unit); regs += wr; outline.append(wp)
        else:                                     # lantern band: white plaster with round red lanterns
            band = box(cx - ww / 2, y - 0.6, cx + ww / 2, y + wh)
            regs.append(R("cf_white", band, "tatami", 0.0, "WALL", unit=unit)); outline.append(band)
            n = int(ww / 14)
            for k in range(n):
                x = cx - ww / 2 + (k + 0.5) * ww / n
                regs.append(R("cf_red", Point(x, y + wh / 2).buffer(min(2.6, wh / 2 - 0.4)), "satin", "auto", "DOT", unit=unit, ko=False))
        y += wh
    bw, bh = bal; bt = y - 0.4
    bal_ = box(cx - bw / 2, bt, cx + bw / 2, bt + bh)
    regs.append(R("cf_red", bal_, "tatami", 0.0, "TMB", unit=unit)); outline.append(bal_)
    regs.append(R("cf_gold", box(cx - bw / 2, bt + 0.6, cx + bw / 2, bt + 1.6), "satin", 90.0, "ORN", unit=unit, ko=False))
    np_ = 16; pw = bw / np_
    for k in range(np_):
        x = cx - bw / 2 + k * pw
        regs.append(R("cf_white", box(x + 1.8, bt + 4.5, x + pw - 1.8, bt + 9.5), "satin", 90.0, "WIN", unit=unit, ko=False))
        regs.append(R("cf_navy", box(x + 2.2, bt + 13.0, x + pw - 2.2, bt + bh - 3.5), "satin", 90.0, "WIN", unit=unit, ko=False))
    for k in range(np_ + 1):
        regs.append(R("cf_gold", Point(cx - bw / 2 + k * pw, bt + 1.6).buffer(1.0), "satin", "auto", "DOT", unit=unit, ko=False))
    regs.append(R("cf_brown", box(cx - bw / 2, bt + bh - 1.4, cx + bw / 2, bt + bh), "satin", 90.0, "TMB", unit=unit, ko=False))
    return regs, unary_union(outline).buffer(0.5), bt + bh

def karamon(cx, y0, w=64.0, h=46.0, unit=None):
    """gold/brown gate at the foot of the castle rock: cusped (karahafu) roof in bark + gold edge, brown posts, dark opening,
    gold studs. y0 = roof top."""
    regs = []
    rh = h * 0.42
    top = [(cx + (w / 2) * math.cos(a), y0 + rh - rh * (math.sin(a) ** 0.6) - 0.0) for a in np.linspace(0, math.pi, 32)]
    curl = [(cx - w / 2 - 3, y0 + rh + 1.5), (cx + w / 2 + 3, y0 + rh + 1.5)]
    rf = Polygon([curl[1]] + top + [curl[0]]).buffer(0)
    regs.append(R("cf_bark", rf, "tatami", ("radial", cx, y0 + rh + 8), "ROOF", unit=unit))
    regs.append(R("cf_gold", LineString(top).buffer(0.9), "satin", "auto", "ORN", unit=unit, ko=False))
    regs.append(R("cf_gold", LineString(curl).buffer(1.0), "satin", "auto", "ORN", unit=unit))
    for k in range(7): regs.append(R("cf_gold", Point(cx - w / 2 + 6 + k * (w - 12) / 6, y0 + rh - 1.6).buffer(0.7), "satin", "auto", "DOT", unit=unit, ko=False))
    yb = y0 + rh + 2.5; hb = h - rh - 2.5
    body = box(cx - w / 2 + 4, yb, cx + w / 2 - 4, yb + hb)
    regs.append(R("cf_brown", body, "tatami", 90.0, "TMB", unit=unit))
    regs.append(R("cf_navy", box(cx - w / 2 + 10, yb + 4, cx + w / 2 - 10, yb + hb), "tatami", 90.0, "WIN", unit=unit))
    regs.append(R("cf_gold", box(cx - w / 2 + 4, yb + 1.0, cx + w / 2 - 4, yb + 2.4), "satin", 90.0, "ORN", unit=unit, ko=False))
    for s in (-1, 1):
        for j in range(3): regs.append(R("cf_gold", Point(cx + s * (w / 2 - 7), yb + 7 + j * 6).buffer(0.8), "satin", "auto", "DOT", unit=unit, ko=False))
    return regs, unary_union([rf, body]).buffer(0.4)

def pagoda(cx, spire_top, tiers, ring_col="cf_gold", unit=None):
    """3-tier pagoda: gold finial spire with rings (sorin), per tier an upturned navy tile roof with gold tips, red balcony band
    and red body with a window. tiers = [(roof_top, roof_bot, eave_w, body_bot, body_w), ...] top first."""
    regs = []; outline = []
    sb = tiers[0][0] + 1.0
    mast = LineString([(cx, spire_top + 2), (cx, sb)]).buffer(0.9, cap_style="flat")
    regs.append(R("cf_brown", mast, "satin", "auto", "TMB", unit=unit))
    n = int((sb - spire_top - 12) / 6.2)
    for k in range(n):
        y = spire_top + 9 + k * 6.2
        regs.append(R(ring_col, affinity.scale(Point(cx, y).buffer(1.0, quad_segs=12), 3.3, 2.5, origin=(cx, y)), "satin", 0.0, "ORN", unit=unit))
    regs.append(R(ring_col, Point(cx, spire_top + 1.8).buffer(1.6), "satin", "auto", "ORN", unit=unit))     # hoju (top jewel)
    regs.append(R(ring_col, box(cx - 3.4, sb - 4.0, cx + 3.4, sb + 0.2), "satin", 90.0, "ORN", unit=unit))  # roban (base)
    outline.append(mast.buffer(1.4))
    for i, (rt, rb, ew, bb, bw) in enumerate(tiers):
        rr, rp = roof(cx, rt, rb, max(6.0, ew * 0.16), ew, lift=4.2, rib=2.4, studs=False, unit=unit); regs += rr; outline.append(rp)
        body = box(cx - bw / 2, rb - 0.5, cx + bw / 2, bb)
        regs.append(R("cf_red", body, "tatami", 90.0, "TMB", unit=unit)); outline.append(body)
        regs.append(R("cf_gold", box(cx - bw / 2 - 2, rb + 0.4, cx + bw / 2 + 2, rb + 1.6), "satin", 90.0, "ORN", unit=unit))   # balcony rail
        hh = bb - rb
        if i < 2: regs.append(R("cf_white", Point(cx, rb + hh * 0.55).buffer(min(2.2, hh * 0.22)), "satin", "auto", "WIN", unit=unit, ko=False))
        else:
            for s in (-1, 0, 1): regs.append(R("cf_navy", box(cx + s * bw * 0.28 - 1.6, rb + 4, cx + s * bw * 0.28 + 1.6, bb - 2), "satin", 90.0, "WIN", unit=unit, ko=False))
    return regs, unary_union(outline).buffer(0.4)

def gate_tower(cx, top, unit=None, gold="cf_gold"):
    """two-storey red gate tower: navy hipped tile roofs with eaves + gold shachi, red upper storey with window openings,
    red posts with dark openings below (SL front, beside the left welt)"""
    regs = []; outline = []
    r1, p1 = roof(cx, top, top + 26, 30, 86, lift=4.5, rib=2.6, eave_col=gold, studs=False, unit=unit); regs += r1; outline.append(p1)
    for s in (-1, 1): regs += shachi(cx + s * 13, top + 0.5, s, col=gold, unit=unit)
    y = top + 26
    up = box(cx - 24, y - 0.5, cx + 24, y + 14)
    regs.append(R("cf_red", up, "tatami", 90.0, "TMB", unit=unit)); outline.append(up)
    for k in range(4): regs.append(R("cf_navy", box(cx - 20 + k * 11, y + 3, cx - 20 + k * 11 + 5.5, y + 11), "satin", 90.0, "WIN", unit=unit, ko=False))
    y += 14
    r2, p2 = roof(cx, y - 1, y + 13, 50, 92, lift=4.0, rib=2.6, eave_col=gold, studs=False, unit=unit); regs += r2; outline.append(p2)
    y += 13
    lo = box(cx - 26, y - 0.5, cx + 26, y + 30)
    regs.append(R("cf_navy", lo, "tatami", 90.0, "WIN", unit=unit)); outline.append(lo)
    for k in range(4):
        x = cx - 26 + k * (52 - 5) / 3
        regs.append(R("cf_red", box(x, y - 0.5, x + 5, y + 30), "satin", 90.0, "TMB", unit=unit))
    regs.append(R("cf_red", box(cx - 27, y + 1, cx + 27, y + 4.5), "satin", 90.0, "TMB", unit=unit))
    regs.append(R("cf_white", box(cx - 8, y + 9, cx + 8, y + 12), "satin", 90.0, "WIN", unit=unit, ko=False))
    return regs, unary_union(outline).buffer(0.4)

def crag(pts_l, pts_r, cap_to, rng, body="cf_slate", lit="cf_mist", dark="cf_navy", cap=("cf_grn", "cf_grndk"), line_cols=("cf_mist", "cf_brown"), unit=None):
    """tall slim crag: left/right outline point lists (top -> bottom), lit left face, strata lines, green cap down to y=cap_to"""
    poly = Polygon(pts_l + pts_r[::-1]).buffer(0)
    regs = [R(body, poly, "tatami", 96.0, "RK", unit=unit)]
    face = poly.intersection(affinity.translate(poly, 3.2, 0)).symmetric_difference(poly).intersection(poly).buffer(-0.2).buffer(0.2)
    regs.append(R(lit, face, "tatami", 96.0, "RK", unit=unit))
    for y in np.arange(pts_l[0][1] + 8, pts_l[-1][1], 5.5):
        ln = LineString([(poly.bounds[0] - 2, y + rng.uniform(-1, 1)), (poly.bounds[2] + 2, y + 3 + rng.uniform(-1, 1))]).intersection(poly.buffer(-1.0))
        for s in getattr(ln, "geoms", [ln]):
            if s.geom_type == "LineString" and s.length > 2.5: regs.append(R(line_cols[int(y) % 2], s.buffer(0.45), "bean", None, "RK-line", ko=False, unit=unit))
    cz = poly.intersection(box(poly.bounds[0] - 5, poly.bounds[1] - 5, poly.bounds[2] + 5, cap_to))
    if not cz.is_empty:
        lobes = [[x, y, rng.uniform(2.4, 3.4)] for x in np.arange(cz.bounds[0], cz.bounds[2], 3.6) for y in np.arange(cz.bounds[1] + 2, cap_to + 2, 3.4)]
        lobes = [l + [l[1]] for l in lobes if cz.buffer(1.5).contains(Point(l[0], l[1]))]
        cr, _ = lobe_regions(lobes, lambda l: (cap[0], None, cap[1]), grp="FOL", unit=unit); regs += cr
    return regs, poly

def house(cx, base, w, rng, wall=("cf_red", "cf_bark"), unit=None):
    """village house: navy hip roof (own object, rows along the ridge) with a sky ridge line, white lintel, red/tan wall with
    dark windows. base = wall bottom y."""
    wh = max(3.0, w * 0.26); rh = max(3.6, w * 0.34)
    wl = box(cx - w * 0.42, base - wh, cx + w * 0.42, base)
    rt = base - wh - rh
    rf = Polygon([(cx - w / 2, base - wh + 0.6), (cx - w * 0.28, rt), (cx + w * 0.28, rt), (cx + w / 2, base - wh + 0.6)]).buffer(0)
    wc = wall[0] if rng.random() < 0.55 else wall[1]
    regs = [R(wc, wl, "satin" if wh < 6.5 else "tatami", 90.0 if wh < 6.5 else 0.0, "TMB", unit=unit),
            R("cf_navy", rf, "tatami", 0.0, "ROOF", unit=unit),
            R("cf_white", box(cx - w * 0.42, base - wh, cx + w * 0.42, base - wh + 0.9), "satin", 90.0, "ORN", unit=unit, ko=False),
            R("cf_sky", LineString([(cx - w * 0.26, rt + 0.6), (cx + w * 0.26, rt + 0.6)]).buffer(0.5), "satin", 90.0, "ROOF-ln", unit=unit, ko=False)]
    if w >= 10:
        for s in (-1, 1): regs.append(R("cf_navy", box(cx + s * w * 0.2 - 1.0, base - wh + 1.6, cx + s * w * 0.2 + 1.0, base - 0.6), "satin", 90.0, "WIN", unit=unit, ko=False))
    return regs, unary_union([wl, rf]).buffer(0.3)

# ---------------------------------------------------------------- cherry floret (strip panel 4 + sleeve / back close-ups)
def floret(cx, cy, d, rot, col, unit=None):
    """5 notched petals, each its own satin sewn ACROSS the petal (radial from the centre), a deep-rose centre ring and a
    cream knot (stamens); thin rose veins from the centre on the larger florets. Overlays (ko=False) on the blossom ground."""
    r = d / 2; out = []
    ring = Point(cx, cy).buffer(max(0.75, d * 0.17), quad_segs=8)
    for k in range(5):
        a = math.radians(rot + k * 72); ux, uy = math.cos(a), math.sin(a)
        c = (cx + ux * r * 0.55, cy + uy * r * 0.55)
        e = affinity.rotate(affinity.scale(Point(c).buffer(1.0, quad_segs=10), r * 0.50, r * 0.38), math.degrees(a), origin=c)
        e = e.difference(Point(cx + ux * r * 1.06, cy + uy * r * 1.06).buffer(r * 0.17)).difference(ring.buffer(0.1))
        if e.area > 0.3: out.append(R(col, e.buffer(0), "satin", ("radial", cx, cy), "BL", unit=unit, ko=False))
    out.append(R("cf_rose", ring.difference(Point(cx, cy).buffer(max(0.5, d * 0.09))), "satin", ("radial", cx, cy), "BL-c", unit=unit, ko=False))
    out.append(R("cf_cream", Point(cx, cy).buffer(max(0.55, d * 0.1), quad_segs=6), "satin", "auto", "BL-c", unit=unit, ko=False))
    return out
