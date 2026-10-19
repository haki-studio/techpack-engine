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
    """Rev C: stitch-structure moon (moon2.py): direction-field ground, ~470 raised oval cells, traced star craters."""
    import moon3
    vis, disc, n = moon3.build(CB)
    return vis, disc

# ================================================================ clouds
def cloud_comps(img, box_px, sinks, up=2):
    tr = TR.trace(img, box_px, tones(CLOUD + sinks), keep=CLOUD, up=up, sigma=1.6, majority=9, min_px=10)
    lab, up = tr["_lab"]; names = [t[0] for t in tones(CLOUD + sinks)]
    a_ = np.asarray(img.crop(box_px).convert("L")).astype(float)
    bg = ndi.grey_dilation(ndi.grey_erosion(a_, size=61), size=61)
    con = np.kron((a_ - bg) > 25, np.ones((up, up), bool))[:lab.shape[0], :lab.shape[1]]
    cm = np.isin(lab, [names.index(n) for n in CLOUD[:4]]) & con
    # tails: thin bright-blue strokes that the tone majority filter drops -> add them from the raw colour
    raw = np.asarray(img.crop(box_px).convert("RGB")).astype(float)
    tail = (raw[..., 2] > raw[..., 0] + 12) & (raw.mean(2) > 95) & ((a_ - bg) > 30)
    tail = np.kron(ndi.binary_opening(tail, iterations=1), np.ones((up, up), bool))[:lab.shape[0], :lab.shape[1]]
    cm = ndi.binary_fill_holes(ndi.binary_closing(cm | tail, iterations=up))
    U = TR.polys_of(cm, up, box_px, 20).buffer(1).buffer(-1)
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

def place(c, centre_mm, s, flipx=False, img=None, want_sil=False):
    """close-up cloud -> mm (Rev C final, cloud3): the close-up component under c['px'] rebuilt as stitch structure
    (silhouette, scallop rows, tones, tails) and placed at centre_mm with scale s mm/px."""
    import cloud3
    from PIL import ImageDraw
    img = img or c.get("img")
    cx, cy = c["px"].centroid.x, c["px"].centroid.y
    x0, y0, x1, y1 = (int(v) for v in c["px"].buffer(8).bounds); x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(img.width, x1), min(img.height, y1)
    a = np.asarray(img.crop((x0, y0, x1, y1)).convert("RGB")).astype(float)
    im = Image.new("L", (x1 - x0, y1 - y0), 0); d = ImageDraw.Draw(im)
    for p in polys(c["px"]):
        d.polygon([(x - x0, y - y0) for x, y in p.exterior.coords], fill=255)
        for h in p.interiors: d.polygon([(x - x0, y - y0) for x, y in h.coords], fill=0)
    lab_, n_, _ = cloud3.masks(img, (x0, y0, x1, y1))
    comp = (np.array(im) > 127) & (lab_ > 0)
    comp = ndi.binary_fill_holes(ndi.binary_closing(comp, iterations=2))
    # drop thin VERTICAL strokes stuck to a cloud (light sleeve topstitching / garment edges in the close-ups); tails are horizontal
    core = ndi.binary_dilation(morphology.binary_opening(comp, morphology.disk(3)), iterations=3)
    lab2, n2 = ndi.label(comp & ~core)
    for k in range(1, n2 + 1):
        ys_, xs_ = np.nonzero(lab2 == k)
        if ys_.max() - ys_.min() > 1.6 * (xs_.max() - xs_.min() + 1) and ys_.max() - ys_.min() > 12: comp[lab2 == k] = False
    if comp.sum() < 300: return ([], None) if want_sil else []
    sx = -s if flipx else s
    f = lambda x, y: (centre_mm[0] + (np.asarray(x) - cx) * sx, centre_mm[1] + (np.asarray(y) - cy) * s)
    cut = [f(xe, 0)[0] for xe, hit in ((0, x0 <= 2 and comp[:, :4].any()), (img.width - 1, x1 >= img.width - 2 and comp[:, -4:].any())) if hit]
    regs, sil = cloud3.cloud(a, comp, (x0, y0), f, abs(s), cut_x=[float(c) for c in cut])
    return (regs, sil) if want_sil else regs

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
# wire anchor points read off the back close-up (px, 2x grid crops out/_wip/cu_low.png, cu_right.png); scene.back_art
# runs the wires between them / to the side seams exactly as the close-up does (review item 6)
BACK_TIPS_CU = {"coilL1": (455, 772), "coilL2": (462, 762), "coilL3": (470, 768), "poleLo": (690, 955), "canB": (660, 885),
                "pinB": (900, 598), "pinA": (858, 606), "wrap": (1057, 712), "drumR": (857, 737), "insBlk": (812, 925),
                "crossA": (842, 608), "crossEnd": (645, 962), "armL1": (600, 662), "spoolT1": (522, 750), "armL2": (628, 674),
                "spoolT2": (545, 752), "canL": (625, 852), "hemL": (500, 1086)}
def back_pole():
    # Rev C final: ONE uniform registration for the whole back close-up (the moon: K = 0.436 mm/px); it puts the crossarm
    # and the lower insulator within 11 / 5 mm of the mockup (the Rev B pole-only fit squashed the hardware to 69 % height)
    import moon3, polepar
    f = lambda x, y: moon3.to_mm(x, y)
    hem = PT.draft("M")[1]["hem_b"]; ybot = float(moon3.to_px(0, hem - 10)[1])     # pole runs to 10 above the hem seam
    vis = polepar.back(f, ybot)                  # Rev C: clean stitch objects at the close-up positions (A13)
    vis = traced_silhouette(vis, CB, (380, 470, 1448, int(ybot) + 1), f, fig_px=(600, 850, 500))
    tips = {k: tuple(float(v) for v in f(*p)) for k, p in BACK_TIPS_CU.items()}
    return vis, tips

def pole_masks(img, box_px, fig_px=None):
    """close-up pole + hardware pixels (grey / charcoal, low saturation) and the thin wire pixels, in close-up px"""
    a = np.asarray(img.convert("RGB")).astype(float)
    sat = a.max(2) - a.min(2); lum = a.mean(2); blue = a[..., 2] - a[..., 0]
    g = ((sat < 62) & (lum > 52) & (blue < 22)) | ((lum <= 52) & (lum > 18) & (blue < 12))      # greys + the brownish pin glaze
    win = np.zeros_like(g); x0, y0, x1, y1 = box_px; win[y0:y1, x0:x1] = True; g &= win
    if fig_px is not None: fx0, fx1, fy1 = fig_px; g[:fy1, fx0:fx1] = False
    import cloud3
    labc, nc, _ = cloud3.masks(img, (0, 0, img.width, img.height))
    cl = np.zeros_like(g)
    for k, sl in enumerate(ndi.find_objects(labc), 1):                 # real clouds only (wide); light pole strips are narrow
        if sl is not None and sl[1].stop - sl[1].start >= 90 and sl[0].stop - sl[0].start < 2.2 * (sl[1].stop - sl[1].start): cl[sl] |= labc[sl] == k
    g &= ~ndi.binary_dilation(cl, iterations=6)                        # cloud undersides are grey too: never pole
    g = ndi.binary_closing(g, iterations=1)
    pole = morphology.remove_small_objects(morphology.binary_opening(g, morphology.disk(5)), 400)
    pole = ndi.binary_fill_holes(ndi.binary_closing(pole, iterations=2))
    wires = morphology.remove_small_objects(g & ~ndi.binary_dilation(pole, iterations=3), 40)
    return pole, wires

def traced_silhouette(vis, img, box_px, f, fig_px=None):
    """LESSONS A14: the pole + hardware SILHOUETTE comes from the close-up pixels: the drawn parts are clipped to the traced
    outline's areas: every traced area no drawn part covers is filled in
    pole dark grey, so the stitched outline is the close-up's; the drawn parts give the inside structure."""
    pole, _ = pole_masks(img, box_px, fig_px)
    sil = map_geom(TR.polys_of(pole, 1, (0, 0, img.width, img.height), 60, simplify=0.3), f).buffer(0.4).buffer(-0.4)
    out = list(vis)                       # drawn parts are measured off the same close-up: kept whole (thin braces/stems)
    drawn = unary_union([r["geom"] for r in out if r["st"] not in ("bean", "run")])
    for p in polys(sil.difference(drawn.buffer(0.3)).buffer(-0.4).buffer(0.75).intersection(sil)):
        if p.area > 3.0 and p.intersects(drawn.buffer(0.8)) and p.difference(drawn.buffer(6.0)).area < 0.25 * p.area: out.insert(0, R("p3", p, "tatami" if width(p) > 2.6 else "satin", "auto" if width(p) <= 2.6 else 90, "PL-shade"))
    return out

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
        return X, Y
    return f
FRONT_TIPS_CU = {"armL": (1107, 662), "armR": (1353, 603), "pin": (1316, 550), "strL": (962, 785), "strL2": (966, 792),
                 "canL": (1176, 905), "canR": (1345, 700), "pole": (1265, 830), "poleL": (1210, 900), "bracket": (1350, 935)}
def front_pole():
    f = front_pole_f()
    import polepar; vis = polepar.front(f)
    vis = traced_silhouette(vis, CF, (930, 480, 1448, 1040), f)
    tips = {k: tuple(float(v) for v in f(*p)) for k, p in FRONT_TIPS_CU.items()}
    return vis, tips

# ================================================================ sleeves (4 views)
VIEWS = [("04R", -1, (0, 335)), ("04R", +1, (340, 715)), ("04L", -1, (725, 1100)), ("04L", +1, (1105, 1448))]
CAP_Y, CUFF_Y = 60.0, 950.0
def sleeves():
    mt = PT.draft("M")[1]; L = mt["cap_h"] + mt["Lu"]
    import cloud3
    lab_, n_, _ = cloud3.masks(CS, (0, 100, 1448, 900))           # Rev C final: cloud3 mask (keeps the pale caps)
    comps = [dict(px=TR.polys_of(lab_ == i, 1, (0, 100, 1448, 900), 30), regs=[], lines=[]) for i in range(1, n_ + 1) if (lab_ == i).sum() > 500]
    out = []
    for c in comps:
        for vi, (sl, half, (vx0, vx1)) in enumerate(VIEWS):
            q = c["px"].intersection(box(vx0 + 14, 0, vx1 - 14, 1086))      # 14 px in: never the light sleeve-edge seam lines
            if q.is_empty or q.area < 600: continue
            sub = dict(px=q, regs=[(n, g.intersection(q)) for n, g in c["regs"] if not g.intersection(q).is_empty],
                       lines=[l.intersection(q.buffer(1)) for l in c["lines"] if l.intersects(q)])
            cx, cy = q.centroid.x, q.centroid.y
            y = -mt["cap_h"] + (cy - CAP_Y) / (CUFF_Y - CAP_Y) * L
            Wy = mt["W"] + (mt["Ww"] - mt["W"]) * min(1, max(0, y / mt["Lu"]))
            fr = (cx - vx0) / (vx1 - vx0)                     # 0..1 across the view
            x = (fr - 1.0) * Wy if half < 0 else fr * Wy      # R: back half [-W, 0] | front half [0, W]; L (S02) the same in its own coords
            v_, sil_ = place(sub, (x * 0.94, y), 0.65, img=CS, want_sil=True)
            if v_: out.append(dict(sleeve=sl, view=vi, vis=v_, sil=sil_, px=(cx, cy)))
    return out

def build_all():
    mock = TA.load()                                  # mockup trace = placement + scale reference
    d = dict(mock=mock)
    d["moon"], d["disc"] = moon()
    # back clouds (Rev C final): every close-up cloud, traced as stitch structure (cloud3) and placed by the SAME
    # registration as the moon + pole (the close-up matches the mockup layout); scene.fit() keeps them off the seams
    import cloud3, moon3
    d["back_clouds"] = [dict(vis=c["vis"], sil=c["sil"], src=i) for i, c in enumerate(cloud3.clouds_in(CB, (0, 120, 1448, 760), lambda x, y: moon3.to_mm(x, y), moon3.K))]
    d["back_pole"], d["back_tips"] = back_pole()
    import moon3; d["back_junc"] = tuple(float(v) for v in moon3.to_mm(1225, 804))
    # front clouds: close-up -> mockup (chest + lower)
    import cloud3
    lab_, n_, _ = cloud3.masks(CF, (0, 0, 1448, 740))            # Rev C final: cloud3 mask (keeps the pale caps)
    cuf = [dict(px=TR.polys_of(lab_ == i, 1, (0, 0, 1448, 740), 30)) for i in range(1, n_ + 1) if (lab_ == i).sum() > 500]
    def _is_cloud(p):          # not the welt-pocket edge / zip tape: thin diagonal strokes fill < 15 % of their box
        b = p.bounds; return (b[2] - b[0] > 60) and p.area / max(1, (b[2] - b[0]) * (b[3] - b[1])) > 0.15
    cuf = [c for c in cuf if not c["px"].is_empty and _is_cloud(c["px"])]
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
    # Rev C final: every front cloud placed by the ONE fitted close-up -> garment mapping (not each by its own mockup
    # partner): neighbouring clouds keep the close-up's overlap (no 'mid-right hole' between the two right chest clouds)
    s1 = float(math.sqrt(abs(ax_[0] * ay_[0]))) if len(pairs) >= 2 else sm
    for c, ctr, s, i in M_:
        ctr = regf2(c["px"].centroid.x, c["px"].centroid.y)
        kind = "chest" if ctr[1] < 300 else "lower"; side = "L" if ctr[0] > 0 else "R"
        v_, sil_ = place(c, ctr, s1, img=CF, want_sil=True)
        d[kind].append(dict(vis=v_, sil=sil_, side=side, src=i))
    d["front_pole"], d["front_tips"] = front_pole()
    d["sleeves"] = sleeves()
    return TA.sanitize(d)

def load():
    p = "close_M.pkl"
    srcs = ["inputs/closeups/closeup_back.png", "inputs/closeups/closeup_front.png", "inputs/closeups/closeup_sleeves.png", "closeart.py", "trace.py", "moon3.py", "cloud3.py", "polepar.py"]
    if os.path.exists(p) and all(os.path.getmtime(p) > os.path.getmtime(s) for s in srcs if os.path.exists(s)):
        return pickle.load(open(p, "rb"))
    d = build_all(); pickle.dump(d, open(p, "wb")); return d

if __name__ == "__main__":
    import time; t = time.time(); d = build_all(); pickle.dump(d, open("close_M.pkl", "wb"))
    print("moon", len(d["moon"]), "back clouds", len(d["back_clouds"]), [c["src"] for c in d["back_clouds"]], "back pole", len(d["back_pole"]),
          "chest", [(c["side"], c["src"]) for c in d["chest"]], "lower", len(d["lower"]), "front pole", len(d["front_pole"]),
          "sleeves", [(s["sleeve"], s["view"]) for s in d["sleeves"]], f"{time.time()-t:.0f}s")
