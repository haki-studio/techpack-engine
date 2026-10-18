"""Rev B art from the CLOSE-UPS (inputs/closeups/*.png, 1448 x 1086, made by Devin in the same image tool) — the
primary tracing reference. Placement + scale follow the MOCKUP (tracedart.py mockup trace = position reference):
  back moon:   close-up disc (centre 724.5, 295.5 px, r 275) -> mockup moon (0, 244) mm, r 120 mm.
  back clouds: each close-up cloud placed at its matching mockup cloud's centroid, scaled to the mockup cloud's width.
  poles:       close-up hardware, x scaled to the mockup pole width, y registered pole top -> lower insulator on the
               mockup positions; the close-up stops above the hem, so the pole body is extended down to 10 above it.
  front:       each close-up cloud / wisp placed + scaled on its matching mockup cloud; pole fitted as the mockup pole.
  sleeves:     4 views (R back half | R front half | L front half | L back half — read from the cap seams); clouds keep the
               close-up count and position (fraction along the sleeve and across the view), 0.65 mm/px.
The licensed figure in the close-up is NOT traced: its pixels become moon (under the box) / are excluded from the pole."""
import math, pickle, os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import morphology
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union
from shapely import affinity
import moonpal
import trace as TR
import tracedart as TA
import moonpattern, pattern as PT
from motifs2 import R

CB = Image.open("inputs/closeups/closeup_back.png").convert("RGB")
CF = Image.open("inputs/closeups/closeup_front.png").convert("RGB")
CS = Image.open("inputs/closeups/closeup_sleeves.png").convert("RGB")
# segmentation colours (close-up screen colours, k-means) -> thread keys
SEGC = {"m1": (237, 213, 180), "m2": (231, 201, 157), "m3": (210, 179, 139), "m4": (181, 157, 125), "m5": (148, 128, 106),
        "m5b": (120, 104, 88),
        "c1": (175, 165, 198), "c2": (140, 134, 174), "c3": (114, 110, 153), "c4": (84, 90, 140), "c5": (64, 71, 116),
        "p1": (203, 190, 190), "p2": (139, 124, 126), "p3": (100, 86, 89), "p4": (50, 42, 46),
        "navy": (24, 33, 58), "navy2": (32, 44, 76), "navy3": (18, 25, 45), "fig": (22, 28, 50)}
MOON = ["m1", "m2", "m3", "m4", "m5"]; CLOUD = ["c1", "c2", "c3", "c4", "c5"]; POLE = ["p1", "p2", "p3", "p4"]
NAVY = ["navy", "navy2", "navy3", "fig"]
CODE = TA.CODE
def tones(names): return [(n.replace("m5b", "m5b"), SEGC[n]) for n in names]
polys = TA.polys; width = TA.width; map_geom = TA.map_geom

# ================================================================ moon
CU_MOON = (724.5, 295.5, 275.0)
def moon():
    cx, cy, r = CU_MOON
    box_px = (int(cx - r - 4), max(0, int(cy - r - 4)), int(cx + r + 4), int(cy + r + 4))
    def mask(rc, up, b):
        rr, cc = rc; X = cc / up + b[0]; Y = rr / up + b[1]; return np.hypot(X - cx, Y - cy) < r
    T = tones(MOON + ["m5b"] + CLOUD + POLE + NAVY)
    tr = TR.trace(CB, box_px, T, keep=MOON + ["m5b"], mask=mask, up=2, sigma=4.0, majority=21, min_px=40)
    lab, up = tr["_lab"]; names = [t[0] for t in T]
    # figure, pole top and cloud overlaps are not moon: re-assign them to moon cream (they sit under the box / clouds)
    sink = np.isin(lab, [names.index(n) for n in CLOUD + POLE + NAVY]) & (lab >= 0)
    sink = ndi.binary_dilation(sink, structure=morphology.disk(3 * up)) & (lab >= 0)
    lab2 = np.where(sink, names.index("m2"), lab)        # under the figure / clouds: moon cream (box area, covered anyway)
    lab2 = np.where(lab2 == names.index("m5b"), names.index("m5"), lab2)        # darkest = crater dark tone (+ its thin rays as lines)
    k = TA.MOON_R_PX * TA.K / r
    f = lambda x, y: ((np.asarray(x) - cx) * k, 244 + (np.asarray(y) - cy) * k)
    disc = Point(0, 244).buffer(TA.MOON_R_PX * TA.K, 360)
    G = {n: map_geom(TR.polys_of(lab2 == names.index(n), up, box_px, 24), f).buffer(0).buffer(0.6).buffer(-0.6).intersection(disc) for n in MOON}
    rim = disc.difference(disc.buffer(-2.5))
    vis = []
    for n in ("m2", "m1", "m3"):           # body tones: concentric directional rows (15° sectors), as the close-up's thread texture
        g = G[n].union(rim) if n == "m3" else G[n].difference(rim)
        for kk in range(24):
            a0, a1 = math.radians(kk * 15), math.radians((kk + 1) * 15)
            sec = Polygon([(0, 244)] + [(400 * math.cos(a), 244 + 400 * math.sin(a)) for a in np.linspace(a0, a1, 6)])
            q = g.intersection(sec)
            if not q.is_empty and q.area > 0.5: vis.append(R(n, q, "tatami", math.degrees((a0 + a1) / 2) + 90, CODE[n]))
    for n in ("m4", "m5"):                 # craters + maria: each patch its own stitch direction (along its long axis)
        for p in polys(G[n].difference(rim)):
            if p.area < 0.8: continue
            vis.append(R(n, p, "satin" if width(p) < 2.6 else "tatami", "auto", CODE[n]))
    # small oval craters (the close-up's crater "bubbles"): local dark blobs at 2-8 px scale -> satin oval in crater
    # light + a lighter rim run (highlight) on the upper-left side, each at its own angle
    from skimage import measure as _ms
    Lm = np.asarray(CB.convert("L")).astype(float)
    dog = ndi.gaussian_filter(Lm, 7) - ndi.gaussian_filter(Lm, 2)
    yy_, xx_ = np.mgrid[0:Lm.shape[0], 0:Lm.shape[1]]
    inside = np.hypot(xx_ - cx, yy_ - cy) < r - 10
    figz = (np.abs(xx_ - 725) < 85) & (yy_ > 300)                     # figure: never traced
    bl = ndi.binary_opening((dog > 8) & inside & ~figz, iterations=2)
    nb = 0
    for rp in _ms.regionprops(_ms.label(bl)):
        if not (40 <= rp.area <= 450) or rp.major_axis_length > 1.8 * max(rp.minor_axis_length, 1) or rp.solidity < 0.85: continue
        yc, xc = rp.centroid; X0, Y0 = f(xc, yc); X0, Y0 = float(X0), float(Y0)
        a_ = max(1.4, rp.major_axis_length / 2 * k); b_ = max(1.0, rp.minor_axis_length / 2 * k)
        ell = affinity.rotate(affinity.scale(Point(X0, Y0).buffer(1, 24), a_, b_), -math.degrees(rp.orientation) + 90, origin=(X0, Y0))
        vis.append(R("m4", ell, "satin", "auto", "MN-crater"))
        rim_ = ell.buffer(0.5).exterior.intersection(box(X0 - 20, Y0 - 20, X0 + 20, Y0 + 0.3 * b_))
        if not rim_.is_empty and rim_.length > 2: vis.append(R("m1", rim_.buffer(0.3, cap_style="round"), "run", None, "MN-ray"))
        nb += 1
    # star-burst craters (3 in the close-up): rays drawn as run lines from each crater centre (the close-up's dark dashes
    # between stitches are thread texture, not art — not traced)
    rng = np.random.RandomState(5)
    for (sx, sy, R0) in ((650, 118, 34), (650, 224, 38), (848, 235, 42)):
        X0, Y0 = f(sx, sy); X0, Y0 = float(X0), float(Y0)
        for kk in range(9):
            a = 2 * math.pi * kk / 9 + rng.uniform(-0.2, 0.2); L1 = R0 * k * rng.uniform(0.7, 1.1)
            ln = LineString([(X0 + 2.0 * math.cos(a), Y0 + 2.0 * math.sin(a)), (X0 + L1 * math.cos(a), Y0 + L1 * math.sin(a))]).intersection(disc.buffer(-2))
            if not ln.is_empty and ln.length > 2.5: vis.append(R("m5", ln.buffer(0.32, cap_style="round"), "run", None, "MN-ray"))
        vis.append(R("m4", Point(X0, Y0).buffer(1.8), "satin", "auto", "MN-crater"))
    return vis, disc

# ================================================================ clouds
def cloud_comps(img, box_px, sinks, up=2):
    tr = TR.trace(img, box_px, tones(CLOUD + sinks), keep=CLOUD, up=up, sigma=1.6, majority=9, min_px=10)
    lab, up = tr["_lab"]; names = [t[0] for t in tones(CLOUD + sinks)]
    a_ = np.asarray(img.crop(box_px).convert("L")).astype(float)
    bg = ndi.grey_dilation(ndi.grey_erosion(a_, size=61), size=61)
    con = np.kron((a_ - bg) > 25, np.ones((up, up), bool))[:lab.shape[0], :lab.shape[1]]
    cm = np.isin(lab, [names.index(n) for n in CLOUD[:4]]) & con
    cm = ndi.binary_fill_holes(ndi.binary_closing(cm, iterations=3 * up))
    U = TR.polys_of(cm, up, box_px, 20).buffer(2).buffer(-2)
    # no fabric holes inside a cloud: dark gaps take the nearest cloud tone
    lab = TR.fill_inside(lab, [names.index(n) for n in CLOUD], cm)
    G = {n: TR.polys_of(lab == names.index(n), up, box_px, 6) for n in CLOUD}
    lines = TR.dark_lines(img, box_px, size=7, thr=14, min_len_px=8,
                          mask=lambda xx, yy: cm[np.clip((yy - box_px[1]) * up, 0, cm.shape[0] - 1), np.clip((xx - box_px[0]) * up, 0, cm.shape[1] - 1)])
    out = []
    for p in [q for q in polys(U) if q.area > 600]:
        regs = [(n, g) for n in CLOUD for g in polys(G[n].intersection(p)) if g.area > 4]
        ls = [l.intersection(p.buffer(-1.5)) for l in lines if l.intersects(p)]
        out.append(dict(px=p, regs=regs, lines=[l for l in ls if not l.is_empty and l.length > 6]))
    return out

def place(c, centre_mm, s, flipx=False):
    """close-up cloud -> mm: the traced SILHOUETTE (lobes + tails) placed at centre_mm, scale s; inside it the sewn look
    of the close-up is rebuilt as tone bands + seigaiha scale rows (moonmotifs.cloud_texture)."""
    import moonmotifs as MM
    cx, cy = c["px"].centroid.x, c["px"].centroid.y
    sx = -s if flipx else s
    f = lambda x, y: (centre_mm[0] + (np.asarray(x) - cx) * sx, centre_mm[1] + (np.asarray(y) - cy) * s)
    sil = map_geom(c["px"], f).buffer(0)
    sil = unary_union([Polygon(p.exterior) for p in polys(sil)]).buffer(1.6).buffer(-2.0).buffer(0.4).simplify(0.3)
    return MM.cloud_texture(sil)

def mm_bbox(vis): return unary_union([r["geom"] for r in vis]).bounds

def match(cu_comps, reg, mock):
    """cu_comps: close-up components; reg(px) -> mockup-mm guess; mock: [(centre_mm, width_mm)]. Returns placements."""
    out, used = [], set()
    for c in sorted(cu_comps, key=lambda c: -c["px"].area):
        g = reg(c["px"].centroid.x, c["px"].centroid.y)
        cand = sorted(((math.hypot(m[0][0] - g[0], m[0][1] - g[1]), i) for i, m in enumerate(mock) if i not in used))
        if cand and cand[0][0] < 70:
            d, i = cand[0]; used.add(i); ctr, w = mock[i]
            out.append((c, ctr, w / (c["px"].bounds[2] - c["px"].bounds[0]), i))
        else:
            out.append((c, g, None, None))
    return out

# ================================================================ poles (hardware from the close-up, figure excluded)
def hardware(img, box_px, f, pole_x, open_r=5, up=2, exclude=None):
    x0, y0, x1, y1 = box_px
    a = np.asarray(img.crop(box_px).convert("RGB")).astype(float)
    sat = a.max(2) - a.min(2); lum = a.mean(2); blue = a[..., 2] - a[..., 0]
    m = ((sat < 42) & (lum > 52) & (blue < 25)) | ((lum <= 52) & (lum > 18) & (blue < 12))
    m = ndi.binary_closing(m, iterations=2); m = morphology.remove_small_holes(m, 300)     # only small holes: big ones are fabric between wires
    core = morphology.binary_opening(m, morphology.disk(open_r))        # drops the free wires (they are drawn parametric)
    keep = m & ndi.binary_dilation(core, iterations=open_r + 1)
    lab, n = ndi.label(keep); sizes = np.bincount(lab.ravel()); ok = np.zeros(n + 1, bool); ok[1:] = sizes[1:] > 120
    keep = ok[lab]
    # only the pole structure: the connected group (allowing 8 px gaps) that holds the most pixels; drops stray cloud bits
    lab2, n2 = ndi.label(ndi.binary_dilation(keep, iterations=8))
    if n2 > 1:
        big = np.argmax(np.bincount(lab2[keep])[1:]) + 1; keep &= lab2 == big
    if exclude is not None:
        yy, xx = np.mgrid[y0:y1, x0:x1]; keep &= ~exclude(xx, yy)
    def mask(rc, up_, b):
        rr, cc = rc; return keep[np.clip((rr // up_).astype(int), 0, keep.shape[0] - 1), np.clip((cc // up_).astype(int), 0, keep.shape[1] - 1)]
    T = tones(POLE + NAVY)
    tr = TR.trace(img, box_px, T, keep=POLE, line_tone="p4", line_w_px=2.4, mask=mask, up=up, sigma=0.4, majority=3, min_px=4)
    lab2, up = tr["_lab"]; names = [t[0] for t in T]
    lab2 = np.where(np.isin(lab2, [names.index(x) for x in NAVY]), names.index("p3"), lab2)    # dark shadows inside hardware = pole dark grey (charcoal stays for the traced outlines)
    vis = []
    for nn in POLE:
        g = map_geom(TR.polys_of(lab2 == names.index(nn), up, box_px, 4), f).buffer(0)
        for p in polys(g):
            if p.area < 0.5: continue
            st, ang = ("satin", "auto") if width(p) < 2.6 else ("tatami", "auto")
            vis.append(R(nn, p, st, ang, CODE[nn]))
    for ln in tr["LINES"]:
        m_ = map_geom(ln, f)
        for s in ([m_] if m_.geom_type == "LineString" else [g for g in getattr(m_, "geoms", []) if g.geom_type == "LineString"]):
            if s.length > 2.5: vis.append(R("p4", s.buffer(0.35, cap_style="round"), "bean", None, "PL-line"))
    return vis

# back close-up pole: x centre 725 px, top 488 px (under the figure's feet), lower insulator 935 px
BPX, BTOP, BLOW = 725.0, 492.0, 958.0
def back_pole_f():
    mt = TA.bpole_f(346.5, 430)[1]; ml = TA.bpole_f(346.5, 603)[1]          # mockup pole top / lower insulator (mm)
    ky = (float(ml) - float(mt)) / (BLOW - BTOP); kx = (25.0 * TA.K) / 58.0     # pole width: mockup 25 px*1.08 / close-up 58 px
    return (lambda x, y: ((np.asarray(x) - BPX) * kx, float(mt) + (np.asarray(y) - BTOP) * ky)), kx, ky, float(mt)
BACK_TIPS_CU = {"armL": (590, 652), "armR": (938, 585), "pinA": (828, 540), "pinB": (898, 532), "strL": (452, 772), "strL2": (456, 780),
                "canL": (655, 888), "insR": (868, 958), "canR": (858, 700), "pole": (726, 950)}
def back_pole():
    f, kx, ky, top = back_pole_f()
    fig = lambda xx, yy: (yy < BTOP + 4) & (np.abs(xx - BPX) < 130)       # the figure sits above the pole top: never traced
    vis = hardware(CB, (420, int(BTOP) - 20, 1040, 1086), f, BPX, exclude=fig)
    # the close-up ends above the hem: extend the pole body to 10 above the hem seam (mockup: pole runs into the rib)
    yb = float(f(0, 1086)[1]); hem = PT.draft("M")[1]["hem_b"]
    w0 = 58 * kx / 2
    ext = Polygon([(-w0, yb - 1), (w0, yb - 1), (w0 * 1.03, hem - 10), (-w0 * 1.03, hem - 10)])
    vis.append(R("p2", ext, "tatami", "auto", "PL"))
    vis.append(R("p3", Polygon([(w0 * 0.45, yb - 1), (w0, yb - 1), (w0 * 1.03, hem - 10), (w0 * 0.47, hem - 10)]), "tatami", "auto", "PL-shade"))
    for xg in (-0.45, 0.1):
        vis.append(R("p4", LineString([(w0 * xg, yb), (w0 * xg * 1.02, hem - 12)]).buffer(0.35), "bean", None, "PL-line"))
    vis += pole_details(f, BPX, 29.0, [528, 599, 673, 748, 815, 957], (760, 860, 673, 860), [699, 744, 789, 840], 492, 1086)
    tips = {k: tuple(float(v) for v in f(*p)) for k, p in BACK_TIPS_CU.items()}
    return vis, tips

def pole_details(f, px, half_w, bands, can_box, can_rings, y0, y1):
    """close-up details the colour trace can't hold at stitch size: charcoal bands round the pole, the ribbed
    transformer's rings + vertical ribs, and wood-grain dashes down the pole (all read off the close-up)."""
    out = []
    P = lambda x, y: tuple(float(v) for v in f(x, y))
    for yb in bands:
        a_, b_ = P(px - half_w, yb), P(px + half_w, yb)
        out.append(R("p4", LineString([a_, b_]).buffer(1.1, cap_style="flat"), "satin", "auto", "PL-band"))
    x0, x1, cy0, cy1 = can_box
    for yr in can_rings:
        out.append(R("p4", LineString([P(x0, yr), P(x1, yr)]).buffer(0.8, cap_style="flat"), "satin", "auto", "PL-band"))
    for xr in np.arange(x0 + 5, x1 - 3, 6.0):
        out.append(R("p4", LineString([P(xr, cy0 + 6), P(xr, cy1 - 6)]).buffer(0.35), "bean", None, "PL-line"))
    rng = np.random.RandomState(9)
    for xg in (-0.55, -0.15, 0.3):
        y = y0 + 20
        while y < y1 - 20:
            L = rng.uniform(14, 34)
            out.append(R("p4", LineString([P(px + xg * half_w, y), P(px + xg * half_w + rng.uniform(-1, 1), y + L)]).buffer(0.35), "bean", None, "PL-line"))
            y += L + rng.uniform(8, 20)
    return out

# front close-up pole: x centre 1235 px, top 515, bottom (rib) 1040; welt-side hardware (string + left can) nudged down 7 mm
FPX_CU, FTOP_CU, FBOT_CU = 1237.0, 510.0, 1020.0
def front_pole_f():
    P = TA.FRONT_POLE; ky = (P["y1"] - P["y0"]) / (FBOT_CU - FTOP_CU); kx = ky * 0.95
    def f(x, y):
        x = np.asarray(x, float); y = np.asarray(y, float)
        X = P["cx"] + (x - FPX_CU) * kx; Y = P["y0"] + (y - FTOP_CU) * ky
        return X, Y + np.where((x < 1185) & (y > 700), 7.0, 0.0)
    return f
FRONT_TIPS_CU = {"armL": (1107, 662), "armR": (1353, 603), "pin": (1316, 550), "strL": (952, 762), "strL2": (956, 770),
                 "canL": (1176, 885), "canR": (1345, 700), "pole": (1265, 830), "poleL": (1210, 900), "bracket": (1350, 935)}
def front_pole():
    f = front_pole_f()
    vis = hardware(CF, (930, 495, 1448, 1020), f, FPX_CU)
    vis += pole_details(f, FPX_CU, 27.0, [608, 700, 795, 860], (1270, 1345, 690, 860), [720, 765, 810], 515, 1020)
    tips = {k: tuple(float(v) for v in f(*p)) for k, p in FRONT_TIPS_CU.items()}
    return vis, tips

# ================================================================ sleeves (4 views)
VIEWS = [("04R", -1, (0, 335)), ("04R", +1, (340, 715)), ("04L", -1, (725, 1100)), ("04L", +1, (1105, 1448))]
CAP_Y, CUFF_Y = 60.0, 950.0
def sleeves():
    mt = PT.draft("M")[1]; L = mt["cap_h"] + mt["Lu"]
    comps = cloud_comps(CS, (0, 100, 1448, 900), NAVY + POLE)
    out = []
    for c in comps:
        for vi, (sl, half, (vx0, vx1)) in enumerate(VIEWS):
            q = c["px"].intersection(box(vx0, 0, vx1, 1086))
            if q.is_empty or q.area < 600: continue
            sub = dict(px=q, regs=[(n, g.intersection(q)) for n, g in c["regs"] if not g.intersection(q).is_empty],
                       lines=[l.intersection(q.buffer(1)) for l in c["lines"] if l.intersects(q)])
            cx, cy = q.centroid.x, q.centroid.y
            y = -mt["cap_h"] + (cy - CAP_Y) / (CUFF_Y - CAP_Y) * L
            Wy = mt["W"] + (mt["Ww"] - mt["W"]) * min(1, max(0, y / mt["Lu"]))
            fr = (cx - vx0) / (vx1 - vx0)                     # 0..1 across the view
            x = (fr - 1.0) * Wy if half < 0 else fr * Wy      # R: back half [-W, 0] | front half [0, W]; L (S02) the same in its own coords
            out.append(dict(sleeve=sl, view=vi, vis=place(sub, (x * 0.94, y), 0.65), px=(cx, cy)))
    return out

def build_all():
    mock = TA.load()                                  # mockup trace = placement + scale reference
    d = dict(mock=mock)
    d["moon"], d["disc"] = moon()
    # back clouds: close-up clouds onto the mockup clouds
    cu = cloud_comps(CB, (0, 120, 1448, 760), MOON + ["m5b"] + POLE + NAVY)
    cx, cy, r = CU_MOON; s0 = TA.MOON_R_PX * TA.K / r
    reg = lambda x, y: (float((x - cx) * s0), float(244 + (y - cy) * s0))
    mk = [((lambda b: ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2))(mm_bbox(c["vis"])), mm_bbox(c["vis"])[2] - mm_bbox(c["vis"])[0]) for c in mock["back_clouds"]]
    d["back_clouds"] = []
    for c, ctr, s, i in match(cu, reg, mk):
        if s is None: continue                                     # close-up cloud with no mockup partner (mockup wins)
        d["back_clouds"].append(dict(vis=place(c, ctr, s), src=i))
    d["back_pole"], d["back_tips"] = back_pole()
    # front clouds: close-up -> mockup (chest + lower)
    cuf = cloud_comps(CF, (0, 0, 1448, 740), POLE + NAVY)
    mockf = [("chest", c) for c in mock["chest"]] + [("lower", c) for c in mock["lower"]]
    mkf = [((lambda b: ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2))(mm_bbox(c["vis"])), mm_bbox(c["vis"])[2] - mm_bbox(c["vis"])[0]) for _, c in mockf]
    zx = 727.0; sf = 246.0 / (FPX_CU - zx)
    regf = lambda x, y: (float((x - zx) * sf), float(88 + (y - 30) * 0.41))
    d["chest"], d["lower"] = [], []
    M_ = match(cuf, regf, mkf)
    pairs = [(c["px"].centroid.x, c["px"].centroid.y, ctr[0], ctr[1], s) for c, ctr, s, i in M_ if s is not None]
    if len(pairs) >= 2:      # refit the close-up -> garment mapping on the matched clouds (per axis, least squares)
        P_ = np.array(pairs); ax_ = np.polyfit(P_[:, 0], P_[:, 2], 1); ay_ = np.polyfit(P_[:, 1], P_[:, 3], 1); sm = float(np.median(P_[:, 4]))
        regf2 = lambda x, y: (float(np.polyval(ax_, x)), float(np.polyval(ay_, y)))
    else:
        regf2, sm = regf, 0.4
    for c, ctr, s, i in M_:
        if s is None:               # close-up cloud / wisp with no mockup partner: keep it (close-up count), mapped by the fit
            ctr = regf2(c["px"].centroid.x, c["px"].centroid.y); s = sm
            kind = "chest" if ctr[1] < 300 else "lower"; side = "L" if ctr[0] > 0 else "R"
        else:
            kind, mc = mockf[i]; side = mc["side"]
        d[kind].append(dict(vis=place(c, ctr, s), side=side, src=i))
    d["front_pole"], d["front_tips"] = front_pole()
    d["sleeves"] = sleeves()
    return TA.sanitize(d)

def load():
    p = "close_M.pkl"
    srcs = ["inputs/closeups/closeup_back.png", "inputs/closeups/closeup_front.png", "inputs/closeups/closeup_sleeves.png", "closeart.py", "trace.py"]
    if os.path.exists(p) and all(os.path.getmtime(p) > os.path.getmtime(s) for s in srcs if os.path.exists(s)):
        return pickle.load(open(p, "rb"))
    d = build_all(); pickle.dump(d, open(p, "wb")); return d

if __name__ == "__main__":
    import time; t = time.time(); d = build_all(); pickle.dump(d, open("close_M.pkl", "wb"))
    print("moon", len(d["moon"]), "back clouds", len(d["back_clouds"]), [c["src"] for c in d["back_clouds"]], "back pole", len(d["back_pole"]),
          "chest", [(c["side"], c["src"]) for c in d["chest"]], "lower", len(d["lower"]), "front pole", len(d["front_pole"]),
          "sleeves", [(s["sleeve"], s["view"]) for s in d["sleeves"]], f"{time.time()-t:.0f}s")
