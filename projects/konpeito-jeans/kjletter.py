"""Rev A fix pass (19 Oct 2026): lettering + line art digitised the way a hand digitiser sets them.

Rev A built satin on the traced (noisy, AI-render) outlines: ragged, comb-like columns, illegible small lettering.
Now:
  * reference masks per string are HALF-MAX masks of the rectified mockup pixels (edge = halfway between thread and
    cream), so the measured stroke width is the visible width of the mockup thread (LESSONS A14: input pixels only);
  * lettering: each glyph of a rounded gothic (Zen Maru Gothic) is fitted to the mockup glyph's SKELETON (position,
    x/y scale, rotation, slant: chamfer distance between the font centreline and the mockup centreline), then its
    centreline becomes satin COLUMNS (kjsatin: one column per stroke, split at corners, round free ends) with ONE
    width per string, measured from the mockup;
  * line art: smoothed centrelines of the traced strokes -> constant-width satin columns; dots are round satin dots
    (or traced-profile columns for drops) at the traced centres and sizes;
  * flowers / candies: one satin per petal along the petal axis, a tint highlight per petal, a clean knot cluster.
Gate (ENGINE_NOTES 4): skeleton-to-skeleton mean distance <= 0.5 mm and width within +-20 % of the mockup."""
import math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from scipy.optimize import minimize
from skimage.morphology import skeletonize
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
from shapely import affinity
import kjsatin as KS
import classify as CL

PPM = 20
THREAD_D = {"40wt": 0.40, "60wt": 0.28}     # thread diameter: stitch lines are drawn this wide in the gate's DST mask
ALLOW = 0.15    # visible width - needle span, calibrated on the DST read-back (Rev A fix pass: coin, wb, 40 + 60wt)
FONTS = {"medium": "inputs/fonts/ZenMaruGothic-Medium.ttf", "bold": "inputs/fonts/ZenMaruGothic-Bold.ttf",
         "black": "inputs/fonts/ZenMaruGothic-Black.ttf"}

# ------------------------------------------------------------------ reference masks from the mockup pixels
def hsv_img(name, sigma=0.8):
    img = np.asarray(Image.open(f"out/trace/{name}_rect.png").convert("RGB")).astype(float)
    img = ndi.gaussian_filter(img, (sigma, sigma, 0))
    return CL.hsv(img)

def halfmax(name, kind, zone):
    """visible-thread mask inside zone: black = value below half (cream ~0.85, black ~0.1), colours = saturation above
    half (cream ~0.12, thread ~0.8), hue-gated per family."""
    h, s, v = hsv_img(name)
    if kind == "black": m = (v < 0.45) & ~(((h > 330) | (h < 15)) & (s > 0.6) & (v > 0.25))
    elif kind == "red": m = (s > 0.45) & ((h > 330) | (h < 15))
    elif kind == "rose": m = (s > 0.40) & ((h > 320) | (h < 15))
    elif kind == "blue": m = (s > 0.40) & (h > 170) & (h < 225)
    else: raise ValueError(kind)
    m &= zone
    return ndi.binary_opening(m, iterations=1)

def prune(sk, n):
    """remove skeleton spurs shorter than n px (endpoint erosion, then regrow from the surviving endpoints)."""
    k = np.ones((3, 3)); cur = sk.copy()
    for _ in range(n):
        nb = ndi.convolve(cur.astype(int), k, mode="constant") - cur
        cur = cur & ~(nb <= 1)
    nb = ndi.convolve(cur.astype(int), k, mode="constant") - cur
    grow = cur & (nb == 1)
    for _ in range(n):
        grow = ndi.binary_dilation(grow, structure=np.ones((3, 3))) & sk
    return cur | grow

def skel(mask, ppm=PPM, spur_mm=0.6):
    m = ndi.gaussian_filter(mask.astype(float), 1.0) > 0.5
    sk = skeletonize(m)
    return prune(sk, max(1, int(spur_mm * ppm))), m

def width_on(mask, sk, ppm=PPM):
    dt = ndi.distance_transform_edt(mask)
    v = 2 * dt[sk] / ppm
    return float(np.median(v)) if v.size else 0.0

def skel_pts(sk, ppm=PPM):
    ys, xs = np.nonzero(sk); return np.c_[(xs + 0.5) / ppm, (ys + 0.5) / ppm]

# ------------------------------------------------------------------ glyph centrelines from the font
_GL = {}
def glyph_strokes(ch, weight="bold", size=8.0):
    """font glyph at `size` mm ink height -> kjsatin strokes, coordinates normalised by size (ink box centred on 0)."""
    key = (ch, weight)
    if key in _GL: return _GL[key]
    import kjtext
    kjtext.FONTS.update(FONTS)
    g, adv = kjtext.glyph(ch, weight)
    P = affinity.scale(g, size, size, origin=(0, 0))
    sts = []
    for p in (P.geoms if P.geom_type == "MultiPolygon" else [P]):
        cut = KS.glyph_columns(p, ppm=40.0)
        loops = [s_ for s_ in KS.glyph_columns(p, ppm=40.0, corner=999.0) if s_.get("closed")]
        for lp in loops:                       # a loop (handakuten, small eyes) stays ONE closed column
            ring = LineString(list(lp["cl"]) + [lp["cl"][0]])
            cut = [s_ for s_ in cut if np.median([ring.distance(Point(q)) for q in KS._resample(s_["cl"], 0.1)[0]]) > 0.3 * lp["w"]]
            cut.append(lp)
        sts += cut
    out = []
    for s_ in sts:
        out.append(dict(cl=[(x / size, y / size) for x, y in s_["cl"]], caps=s_["caps"], closed=s_.get("closed", False),
                        wf=s_["w"] / size))
    _GL[key] = (out, g, adv)
    return _GL[key]

def sample(sts, step):
    pts = []
    for s_ in sts:
        cl = list(s_["cl"]) + ([s_["cl"][0]] if s_["closed"] else [])
        if len(cl) < 2: continue
        ls = LineString(cl); n = max(2, int(ls.length / step))
        pts += [ls.interpolate(ls.length * i / n).coords[0] for i in range(n + 1)]
    return np.array(pts)

def T(p, P):
    """normalised glyph coords -> mm: scale (sx, sy), slant, rotate, translate."""
    cx, cy, sx, sy, rot, sh = p
    x = P[:, 0] * sx + sh * P[:, 1] * sy; y = P[:, 1] * sy
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    return np.c_[cx + c * x - s * y, cy + s * x + c * y]

_EM = {}
def em_box(ch, weight="bold"):
    """ink box of the glyph in em units, y down: (w, h, cx, cy) with (0, 0) = left end of the baseline."""
    key = (ch, weight)
    if key not in _EM:
        import kjtext
        from fontTools.ttLib import TTFont
        tt = TTFont(FONTS[weight]); gs = tt.getGlyphSet(); cmap = tt.getBestCmap(); em = tt["head"].unitsPerEm
        pen = kjtext.FlatPen(gs); gs[cmap[ord(ch)]].draw(pen)
        P = np.array([p for c in pen.contours for p in c], float)
        x0, y0 = P.min(0); x1, y1 = P.max(0)
        _EM[key] = ((x1 - x0) / em, (y1 - y0) / em, (x0 + x1) / 2 / em, -(y0 + y1) / 2 / em)
    return _EM[key]

def segment(text, ref_mask, weight="bold", ppm=PPM, min_mm2=0.5):
    """mockup glyph components -> one group per character: components sorted along the string's baseline and split
    into len(text) CONTIGUOUS groups whose lengths best match the font's ink widths at one common scale (exhaustive
    over the partitions). Specks under min_mm2 join the nearest group. Returns (groups of component masks, u, v)."""
    from itertools import combinations
    ys, xs = np.nonzero(ref_mask); X = np.c_[xs / ppm, ys / ppm]
    b_, a_ = np.polyfit(X[:, 0], X[:, 1], 1)
    ang = math.atan(b_); u = np.array([math.cos(ang), math.sin(ang)]); v = np.array([-u[1], u[0]])
    lab, n = ndi.label(ref_mask, structure=np.ones((3, 3)))
    comps = []
    for k in range(1, n + 1):
        m = lab == k; a = m.sum() / ppm ** 2
        yy, xx = np.nonzero(m); P = np.c_[xx / ppm, yy / ppm] @ u
        comps.append(dict(m=m, a=a, a0=P.min(), a1=P.max(), c=P.mean()))
    big = sorted([c for c in comps if c["a"] >= min_mm2], key=lambda c: c["c"])
    small = [c for c in comps if c["a"] < min_mm2]
    wem = np.array([em_box(ch, weight)[0] for ch in text]); N = len(text)
    best = None
    for cuts in combinations(range(1, len(big)), N - 1):
        idx = [0, *cuts, len(big)]
        ext = np.array([max(c["a1"] for c in big[i:j]) - min(c["a0"] for c in big[i:j]) for i, j in zip(idx, idx[1:])])
        E = float(ext @ wem / (wem @ wem))
        cost = float((((ext - E * wem) / (E * wem)) ** 2).sum())
        # characters do not overlap their neighbours along the baseline; strokes of one character do (or nearly touch)
        st_ = [min(c["a0"] for c in big[i:j]) for i, j in zip(idx, idx[1:])]
        en_ = [max(c["a1"] for c in big[i:j]) for i, j in zip(idx, idx[1:])]
        cost += 4.0 * sum(max(0.0, en_[k] - st_[k + 1]) for k in range(N - 1)) / E
        for i, j in zip(idx, idx[1:]):
            g = sorted(big[i:j], key=lambda c: c["a0"]); reach = g[0]["a1"]
            for c in g[1:]:
                cost += 1.0 * max(0.0, c["a0"] - reach) / E; reach = max(reach, c["a1"])
        if best is None or cost < best[0]: best = (cost, idx)
    idx = best[1]
    groups = [big[i:j] for i, j in zip(idx, idx[1:])]
    for c in small:
        k = min(range(N), key=lambda k: min(abs(c["c"] - g["c"]) for g in groups[k]))
        groups[k].append(c)
    return [np.any([c["m"] for c in g], axis=0) for g in groups], u, v

def fit_string(text, ref_mask, weight="bold", ppm=PPM):
    """fit each glyph's centreline to the mockup skeleton of ITS OWN mockup components (segment()): start from the
    group's box (x/y scale from the font's ink box, baseline tilt), then refine position, x/y scale, rotation and slant
    on the chamfer distance between the font centreline and the mockup skeleton, held within +-20 % / +-0.2 h of the
    box. Returns [dict(ch, p, sts, cost)] (cost = symmetric mean chamfer distance, mm)."""
    groups, u, v = segment(text, ref_mask, weight, ppm)
    ang = math.degrees(math.atan2(u[1], u[0]))
    fits = []
    for ch, gm in zip(text, groups):
        sts, g, adv = glyph_strokes(ch, weight)
        sk, _ = skel(gm, ppm); Rk = skel_pts(sk, ppm)
        yy, xx = np.nonzero(gm); X = np.c_[(xx + 0.5) / ppm, (yy + 0.5) / ppm]
        pa, pv = X @ u, X @ v
        a0, a1, v0, v1 = pa.min(), pa.max(), pv.min(), pv.max()
        c = u * (a0 + a1) / 2 + v * (v0 + v1) / 2
        h = v1 - v0; w = a1 - a0
        p0 = np.array([c[0], c[1], w / adv, h, ang, 0.0])
        if len(Rk) < 5:
            fits.append(dict(ch=ch, p=p0, sts=sts, cost=0.0)); continue
        tk = cKDTree(Rk); base = sample(sts, 0.03)
        def cost(q):
            gp = T(q, base)
            d1, _ = tk.query(gp); d2, _ = cKDTree(gp).query(Rk)
            c_ = np.minimum(d1, 1.0).mean() + np.minimum(d2, 1.0).mean()
            c_ += 2.0 * max(0, abs(math.log(q[2] / p0[2])) - 0.2) + 2.0 * max(0, abs(math.log(q[3] / p0[3])) - 0.2)
            c_ += 2.0 * max(0, math.hypot(q[0] - p0[0], q[1] - p0[1]) / h - 0.2)
            c_ += 0.05 * max(0, abs(q[4] - p0[4]) - 12) + 2.0 * max(0, abs(q[5]) - 0.3)
            return c_
        best = None
        for sh in (0.0, -0.12, 0.12):
            q0 = p0.copy(); q0[5] = sh
            r = minimize(cost, q0, method="Nelder-Mead", options=dict(xatol=0.005, fatol=1e-4, maxiter=2500))
            if best is None or r.fun < best.fun: best = r
        gp = T(best.x, base); d1, _ = tk.query(gp); d2, _ = cKDTree(gp).query(Rk)
        fits.append(dict(ch=ch, p=best.x, sts=sts, cost=float(d1.mean() + d2.mean())))
    return fits

def string_columns(col, code, fits, w, min_counter=0.7, min_w_loop=0.8):
    """fitted glyph centrelines -> satin column regions, one width w for the whole string."""
    regs = []
    for f in fits:
        for s_ in f["sts"]:
            cl = [tuple(q) for q in T(f["p"], np.array(s_["cl"]))]
            L = KS.poly_len(cl + ([cl[0]] if s_["closed"] else []))
            if L < 0.2: continue
            ww = w
            if s_["closed"]:                    # loops (handakuten, ね/お/ろ eyes): keep the counter >= min_counter open
                ww = max(min_w_loop, min(w, L / math.pi - (min_counter + 0.2 + ALLOW)))   # counter as SEWN (pull + thread)
            if s_["closed"] and L < 10.0:       # small loop: radial satin across the ring (a column's inner ends collapse)
                g = KS.column_geom(cl, ww, ("flat", "flat"), True); c = g.centroid
                regs.append(dict(col=col, geom=g, st="satin", ang=("radial", c.x, c.y), grp=code, layer=0, glyph=f["ch"])); continue
            regs.append(KS.column_region(col, code, cl, ww, s_["caps"], s_["closed"], glyph=f["ch"]))
    return regs

# ------------------------------------------------------------------ line art
def smooth_cl(pts, win_mm=1.2, closed=False):
    rs, L = KS._resample(pts, 0.1, closed)
    if L < 0.3: return list(pts)
    k = max(1, int(win_mm / 0.1 / 2))
    for _ in range(2): rs = KS._smooth(rs, k, closed)
    return list(LineString(rs).simplify(0.02).coords)

def line_art(col, code, ref_mask, w, dot_min=1.0, ppm=PPM, holes=False, dots=True, win_mm=1.2):
    """traced line drawing -> constant-width satin columns on smoothed centrelines; compact blobs (eyes) -> dots."""
    regs = []; dots = []
    lab, n = ndi.label(ref_mask, structure=np.ones((3, 3)))
    for k in range(1, n + 1):
        m = lab == k
        a = m.sum() / ppm ** 2
        if a < 0.12: continue
        sk, mm = skel(m, ppm, spur_mm=0.4); L = sk.sum() / ppm
        ys, xs = np.nonzero(m)
        cov = np.cov(np.c_[xs, ys].T) if len(xs) > 3 else np.eye(2)
        ev = np.sort(np.linalg.eigvalsh(cov))[::-1]
        el = math.sqrt(ev[0] / max(ev[1], 1e-9))
        if dots and el < 1.6 and L < 2.0:            # eye / dot
            cx, cy = xs.mean() / ppm, ys.mean() / ppm
            d = 2 * math.sqrt(a / math.pi)
            dots.append((cx, cy, d)); continue
        from kjart import mask_geom
        P = mask_geom(m, sigma=1.2, simp=0.03)
        for p in ([P] if P.geom_type == "Polygon" else list(P.geoms)):
            if p.area < 0.1: continue
            if holes:                            # lettering: keep real counters (> 0.05 mm2), drop pin holes
                p = Polygon(p.exterior, [r for r in p.interiors if Polygon(r).area > 0.05])
            else:
                p = Polygon(p.exterior)          # line art has no counters: pin holes in the trace made skeleton loops
            sts = KS.glyph_columns(p, ppm=40.0)
            for s_ in sts:
                cl = smooth_cl(s_["cl"], win_mm=win_mm, closed=s_.get("closed", False))
                if KS.poly_len(cl) < 0.4: continue
                regs.append(KS.column_region(col, code, cl, w, s_["caps"], s_.get("closed", False)))
    return regs, dots

def dot_shapes(ref_mask, ppm=PPM, thread=0.20, min_d=1.1, el_max=1.25):
    """traced dots -> (kind, data): round = (cx, cy, needle d); drop = column along the major axis with the traced
    width profile."""
    out = []
    lab, n = ndi.label(ref_mask, structure=np.ones((3, 3)))
    for k in range(1, n + 1):
        m = lab == k; a = m.sum() / ppm ** 2
        if a < 0.3: continue
        ys, xs = np.nonzero(m); X = np.c_[(xs + 0.5) / ppm, (ys + 0.5) / ppm]
        c = X.mean(0); cov = np.cov((X - c).T); ev, evec = np.linalg.eigh(cov)
        el = math.sqrt(ev[1] / max(ev[0], 1e-9))
        d = 2 * math.sqrt(a / math.pi)
        if el < el_max:
            out.append(("round", (float(c[0]), float(c[1]), max(min_d, d - thread)))); continue
        u = evec[:, 1]; t = (X - c) @ u; vperp = (X - c) @ evec[:, 0]
        t0, t1 = t.min() + 0.5 / ppm, t.max() - 0.5 / ppm
        bins = np.linspace(t0, t1, 9); wid = []
        for i in range(len(bins) - 1):
            sel = (t >= bins[i]) & (t < bins[i + 1])
            wid.append(vperp[sel].max() - vperp[sel].min() + 1 / ppm if sel.any() else 0.0)
        wid = np.array(wid); wmax = max(wid.max(), 1e-6)
        out.append(("drop", dict(c=c.tolist(), u=u.tolist(), t0=float(t0), t1=float(t1), w=float(wmax - 0.3), prof=(wid / wmax).tolist())))
    return out

def dot_regions(col, code, shapes):
    regs = []
    for kind, d in shapes:
        if kind == "round":                  # bead dot: underlay cross + dense satin (kjletter.knot_points)
            cx, cy, dd = d
            regs.append(dict(col=col, geom=Point(cx, cy).buffer(dd / 2, quad_segs=16), st="satin", ang="knots", grp=code, layer=0,
                             knots=[(cx, cy, dd, 30.0)]))
        else:
            c, u = np.array(d["c"]), np.array(d["u"]); w = max(0.9, d["w"])
            r = w / 2
            a = c + u * (d["t0"] + 0.05); b = c + u * (d["t1"] - 0.05)     # round caps shrink inside the ends
            prof = ("table", [max(0.45, v) for v in d["prof"]])
            regs.append(KS.column_region(col, code, [tuple(a), tuple(b)], w, ("round", "round"), False, prof))
    return regs

# ------------------------------------------------------------------ knot clusters (flower centres)
def knot_cluster(col, cx, cy, d=1.0, ring=6, rot=0.0, code="KNOT", gap=0.15):
    """1 + ring bead knots (ring radius d + gap): sewn as ONE object; each bead = a tiny cross underlay + a dense satin
    dot turned to the ring tangent, so the beads read separately; the 0.15 mm moves between beads are not visible."""
    rr = d + gap
    pts = [(cx, cy, 0.0)] + [(cx + rr * math.cos(math.radians(rot + 360 * j / ring)), cy + rr * math.sin(math.radians(rot + 360 * j / ring)),
                              rot + 360 * j / ring + 90) for j in range(ring)]
    g = unary_union([Point(x, y).buffer(d / 2, quad_segs=12) for x, y, _ in pts])
    return dict(col=col, geom=g.buffer(0), st="satin", ang="knots", grp=code, layer=0, knots=[(x, y, d, a) for x, y, a in pts])

def knot_points(knots, sp=0.18):
    seq = []
    for kn in knots:
        x, y, d = kn[:3]; a = kn[3] if len(kn) > 3 else 0.0
        r = d / 2; t = math.radians(a); ux, uy = math.cos(t), math.sin(t); vx, vy = -uy, ux
        q = 0.3 * r                                            # underlay: small cross, lifts the bead
        seq += [(x - ux * q, y - uy * q), (x + ux * q, y + uy * q), (x, y), (x - vx * q, y - vy * q), (x + vx * q, y + vy * q)]
        n = max(4, int(d / sp))
        for k in range(n + 1):
            o = -r + d * k / n; hw = math.sqrt(max(0.0, r * r - o * o)) * 0.95
            if hw < 0.1: continue
            A = (x + vx * o - ux * hw, y + vy * o - uy * hw); B = (x + vx * o + ux * hw, y + vy * o + uy * hw)
            seq += [A, B] if k % 2 == 0 else [B, A]
    return seq

# ------------------------------------------------------------------ petals (flowers + candies)
def polar_profile(geo, c, n=360):
    out = []
    for i in range(n):
        t = math.radians(360 * i / n)
        ray = LineString([c, (c[0] + 40 * math.cos(t), c[1] + 40 * math.sin(t))]).intersection(geo)
        r = 0.0
        for g in getattr(ray, "geoms", [ray]):
            if g.is_empty: continue
            for q in g.coords: r = max(r, math.dist(c, q))
        out.append(r)
    return np.array(out)

def petals(geo, c, nmin=5, nmax=7, force_n=None):
    """split a flower silhouette into petals at the valleys of its polar profile. Returns n, phase, [(petal, tip)]."""
    r = polar_profile(geo, c)
    rs = ndi.gaussian_filter1d(r, 4, mode="wrap")
    F = np.fft.rfft(rs - rs.mean())
    n = force_n or int(np.argmax(np.abs(F[nmin:nmax + 1])) + nmin)
    # valleys: local minima of the smoothed profile, the n deepest roughly 360/n apart
    best = None
    for ph in range(0, 360 // n):
        val = sum(rs[(ph + int(round(360 * k / n))) % 360] for k in range(n))
        if best is None or val < best[0]: best = (val, ph)
    ph = best[1]
    vals = []
    for k in range(n):       # refine each valley within +-12 deg
        a0 = ph + 360 * k / n; cand = [int(round(a0 + dd)) % 360 for dd in range(-12, 13)]
        vals.append(min(cand, key=lambda a: rs[a]))
    vals = sorted(vals)
    out = []
    for k in range(n):
        a0, a1 = vals[k], vals[(k + 1) % n]
        if a1 <= a0: a1 += 360
        pts = [c] + [(c[0] + 40 * math.cos(math.radians(a)), c[1] + 40 * math.sin(math.radians(a))) for a in np.linspace(a0, a1, 24)]
        wedge = Polygon(pts)
        p = geo.intersection(wedge).buffer(0)
        if p.is_empty: continue
        if p.geom_type != "Polygon": p = max(p.geoms, key=lambda q: q.area)
        am = int(np.argmax([rs[int(a) % 360] for a in np.arange(a0, a1)])) + a0
        tip = (c[0] + rs[int(am) % 360] * math.cos(math.radians(am)), c[1] + rs[int(am) % 360] * math.sin(math.radians(am)))
        out.append((p, tip, (a0 + a1) / 2))
    return n, out

def petal_regions(col, tint, geo, c, code="FL", code_hi="FL-hi", force_n=None, hi_scale=0.55, light=(-0.6, -0.8)):
    """one turning satin per petal across its axis (centre -> tip) + a tint highlight on the lit side of each petal."""
    n, ps = petals(geo, c, force_n=force_n)
    regs, his = [], []
    lx, ly = light; ln_ = math.hypot(lx, ly); lx, ly = lx / ln_, ly / ln_
    for p, tip, amid in ps:
        axis = [c, tip]
        regs.append(dict(col=col, geom=p.buffer(0.05).intersection(geo.buffer(0.05)), st="satin", ang="tl", grp=code, layer=0,
                         tline=[c, (c[0] + (tip[0] - c[0]) * 1.1, c[1] + (tip[1] - c[1]) * 1.1)]))
        if tint:
            L = math.dist(c, tip)
            ux, uy = (tip[0] - c[0]) / L, (tip[1] - c[1]) / L
            lit = 0.5 + 0.5 * (ux * lx + uy * ly)          # 0 = petal facing away from the light, 1 = facing it
            f = 0.55 + 0.15 * lit
            o = (c[0] + ux * L * f + lx * 0.25, c[1] + uy * L * f + ly * 0.25)
            h = affinity.scale(p, hi_scale, hi_scale, origin=o).intersection(p.buffer(-0.5))
            h = h.buffer(-0.15).buffer(0.15)
            if not h.is_empty and h.area > 0.8:
                if h.geom_type != "Polygon": h = max(h.geoms, key=lambda q: q.area)
                his.append(dict(col=tint, geom=h, st="satin", ang="tl", grp=code_hi, layer=0,
                                tline=[(o[0] - ux * L, o[1] - uy * L), (o[0] + ux * L, o[1] + uy * L)]))
    return regs, his, n

# ------------------------------------------------------------------ centreline gate
def dst_mask(seq, cols, shape, to_px, stops, thread_d):
    """mask of the stitches of the given stop indexes (0-based), each stitch drawn at its thread's visible diameter."""
    Hh, Ww = shape
    im = Image.new("L", (Ww, Hh), 0); d = ImageDraw.Draw(im)
    for ci, a, b in seq:
        if ci in stops:
            d.line([to_px(*a), to_px(*b)], fill=255, width=max(1, int(round(thread_d * PPM))))
    m = ndi.binary_closing(np.array(im) > 0, iterations=2)
    lab, n = ndi.label(~m)                                   # needle-gap pin holes (< 0.3 mm2) are not counters
    if n:
        sz = ndi.sum(np.ones_like(lab), lab, range(1, n + 1)) / PPM ** 2
        small = np.r_[False, sz < 0.3]; m |= small[lab]
    return m

def read_seq(path):
    import pyembroidery as pe
    p = pe.read(path); seq = []; ci = 0; prev = None
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK; P = (x / 10, y / 10)
        if k == pe.STITCH:
            if prev is not None: seq.append((ci, prev, P))
            prev = P
        elif k == pe.COLOR_CHANGE: ci += 1; prev = None
        elif k == pe.TRIM: prev = None
        elif k == pe.JUMP: prev = P
        elif k == pe.END: break
    return seq

def cl_gate(name, ref_mask, out_mask, pull=0.0, near_mm=1.0, ppm=PPM, d_max=0.5, w_tol=0.20):
    """skeleton-to-skeleton mean distance (symmetric mean of both directions) + visible width ratio.
    ref_mask: mockup pixels only. out_mask: the DST's stitches of this family's stop(s), limited to near_mm of ref."""
    near = ndi.binary_dilation(ref_mask, iterations=max(1, int(near_mm * ppm)))
    o = out_mask & near
    sr, mr = skel(ref_mask, ppm); so, mo = skel(o, ppm)
    R = skel_pts(sr, ppm); O = skel_pts(so, ppm)
    if len(O) == 0 or len(R) == 0:
        return dict(family=name, mean_d=None, p90_d=None, w_ref=None, w_dst=None, ratio=None, ok=False)
    d1, _ = cKDTree(O).query(R); d2, _ = cKDTree(R).query(O)
    md = float((d1.mean() + d2.mean()) / 2); p90 = float(np.percentile(np.r_[d1, d2], 90))
    wr = width_on(mr, sr, ppm); wo = width_on(mo, so, ppm) - 2 * pull
    ratio = wo / wr if wr else 0.0
    return dict(family=name, mean_d=round(md, 2), p90_d=round(p90, 2), w_ref=round(wr, 2), w_dst=round(wo, 2),
                ratio=round(ratio, 2), ok=bool(md <= d_max and abs(ratio - 1) <= w_tol))

# ------------------------------------------------------------------ exposed stitches (travel floats) from the DST
def exposed_stitches(path, origin, stop_geoms, halo=0.35, min_mm=1.0):
    """every sewn stitch of stop i must lie on stop i's own art (+halo) or under art sewn by a later stop.
    Returns [(stop 1-based, x, y, exposed length mm)] for stitches with > min_mm outside that cover."""
    from shapely.prepared import prep
    seq = read_seq(path); ox, oy = origin
    cover = []
    for i in range(len(stop_geoms)):
        g = unary_union([stop_geoms[i].buffer(halo)] + [s_ for s_ in stop_geoms[i + 1:]])
        cover.append(g)
    out = []
    for ci, a, b in seq:
        if ci >= len(cover): continue
        A = (a[0] + ox, a[1] + oy); B = (b[0] + ox, b[1] + oy)
        if math.dist(A, B) < min_mm: continue
        ex = LineString([A, B]).difference(cover[ci]).length
        if ex > min_mm: out.append((ci + 1, round((A[0] + B[0]) / 2, 1), round((A[1] + B[1]) / 2, 1), round(ex, 2)))
    return out
