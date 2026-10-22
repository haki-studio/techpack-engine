"""Front-leg konpeito stars (07) — PROPOSED placement map + PROPOSED stitch files (the front-leg artwork is to follow).

Rev B (founder review 20 Oct, item 15): the map is re-derived from the garment mockup (1792127150159_image.png) with the
math written into out/front_stars.json["derivation"] and drawn on out/check_07_mockup.png (the pack's C5 page):
  scale   = half relaxed waist of size 32 (33.1 in / 2 = 420.4 mm) / the front waistband width on the mockup, measured on
            the traced silhouette at the waistband's mid-height (px)            -> mm per px
  origin  = top of the waistband at the side seam (wearer's right, image left); y straight down, x in from the side seam
            (the silhouette edge at the star's own height)
  pocket  = the front scoop-pocket opening, traced from the mockup at 5x zoom on a 10 px grid (POCKET_OPENING_PX)
  check   = every star centre must lie BELOW the opening (outside the pocket mouth); the gap is reported per star.
Stars are 10 mm (same size as every konpeito star on the jean)."""
import json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from shapely.geometry import box, LineString, Point, Polygon
import kjcore
import classify as CL
import kjart as KA
import kjflat as FL

SRC = "inputs/1792127150159_image.png"
HALF_WAIST_MM = 33.1 * 25.4 / 2          # size 32 relaxed waist (HI chart, T3) / 2 = 420.4 mm (the flat shows the front half)
SIDE_KO = 12.0                           # keep-out: finished side seam + topstitch + 3 mm
STAR_D = KA.STAR_D
COLS = {"pink": ("kj_pink", "kj_pink_hi"), "blue": ("kj_blue", "kj_blue_hi"), "yellow": ("kj_yellow", "kj_yellow_hi")}
# front scoop-pocket opening (wearer's right), mockup px, from the side seam to the rivet under the waistband:
# read on the mockup at 5x zoom with a 10 px grid (out/check_07_pocket_grid.png). The coin-pocket patch sits INSIDE it.
POCKET_OPENING_PX = FL.OPENING_PX

def geometry():
    sil = FL.silhouettes()["front"]
    wb_top = min(y for x, y in sil.exterior.coords)
    wb_bot = 88.0                                              # waistband lower seam at the side (mockup px, grid read)
    ymid = (wb_top + wb_bot) / 2
    row = sil.intersection(box(0, ymid - 0.3, 3000, ymid + 0.3)).bounds
    wb_w = row[2] - row[0]
    mmpx = HALF_WAIST_MM / wb_w
    top = sil.intersection(box(0, wb_top + 3.7, 3000, wb_top + 4.3)).bounds   # side seam x at the WB top
    origin = (top[0], wb_top)
    return dict(sil=sil, wb_top=wb_top, wb_mid=ymid, wb_w_px=wb_w, mmpx=mmpx, origin=origin)

def side_x(sil, y):
    r = sil.intersection(box(0, y - 0.3, 3000, y + 0.3))
    return r.bounds[0]

def opening_y(x):
    xs = [p[0] for p in POCKET_OPENING_PX]; ys = [p[1] for p in POCKET_OPENING_PX]
    if x < xs[0] or x > xs[-1]: return None
    return float(np.interp(x, xs, ys))

MERGE_RATIO = 1.3

def check_merges(blobs, ratio=MERGE_RATIO):
    """guard (PR #34 review): a detected star wider/taller than ratio x the median star is probably two motifs read as
    one blob. Raises, so a merge cannot reach the map silently."""
    sz = [max(sl[0].stop - sl[0].start, sl[1].stop - sl[1].start) for _, sl, _ in blobs]
    med = float(np.median(sz))
    big = [(c, (sl[1].start, sl[0].start), z) for (c, sl, _), z in zip(blobs, sz) if z > ratio * med]
    if big:
        raise ValueError(f"possible merged stars (size > {ratio} x median {med:.0f} px): {big}")
    return med

EDGE_PX = 3          # band either side of the traced side-seam edge searched for clipped candies (PR #34 round 2)
EDGE_SAT = 0.12      # a clipped sliver is 1-3 px wide and anti-aliased into the background: lower saturation floor
EDGE_MIN_PX = 3      # >= 3 px: the faint blue sliver at the side seam is 5 px; single-pixel colour noise on the edge is dropped

def edge_slivers(G, h, s, v, blobs):
    """PR #34 round 2: candies that run off the side seam on the mockup show as 1-3 px slivers on the cut edge, below
    the main trace's 6 px / saturation floor. Search a +-EDGE_PX band along the traced side seam with a lower
    saturation floor; slivers already covered by a main blob are skipped."""
    H, W = s.shape
    band = np.zeros((H, W), bool)
    for y in range(int(G["wb_top"]) + 5, H):
        try: ex = side_x(G["sil"], y + 0.5)
        except Exception: continue
        if not np.isfinite(ex): continue
        e = int(round(ex)); band[y, max(e - EDGE_PX, 0):e + EDGE_PX + 1] = True
    band[60:186, 893:992] = False
    sv = (s > EDGE_SAT) & (v > 0.3) & band
    masks = {"pink": sv & ((h > 300) | (h < 15)), "blue": sv & (h > 160) & (h < 230), "yellow": sv & (h > 35) & (h < 65)}
    out = []
    for col, m in masks.items():
        lab, n = ndi.label(m, structure=np.ones((3, 3)))
        for i, sl in enumerate(ndi.find_objects(lab), 1):
            mm = lab[sl] == i
            if mm.sum() < EDGE_MIN_PX: continue
            cy, cx = (sl[0].start + sl[0].stop) / 2, (sl[1].start + sl[1].stop) / 2
            if any(b[1][0].start - 2 <= cy <= b[1][0].stop + 2 and b[1][1].start - 2 <= cx <= b[1][1].stop + 2 for b in blobs):
                continue
            out.append((col, sl, mm, True))
    return out

def trace(G):
    a = np.asarray(Image.open(SRC).convert("RGB")).astype(float)
    h, s, v = CL.hsv(a)
    sv = (s > 0.45) & (v > 0.5)
    # PR #34 review: label EACH colour on its own — a pink and a yellow star that touch (S06, 4th soot sprite) were
    # one blob when all hues were labelled together.
    masks = {"pink": sv & ((h > 300) | (h < 15)), "blue": sv & (h > 180) & (h < 215), "yellow": sv & (h > 35) & (h < 65)}
    blobs = []
    for col, m in masks.items():
        m[:, :770] = False; m[:, 1000:] = False
        m[60:186, 893:992] = False                     # the coin-pocket patch + its konpeito (elements 01/02)
        lab, n = ndi.label(ndi.binary_dilation(m, iterations=1))
        for i, sl in enumerate(ndi.find_objects(lab), 1):
            mm = lab[sl] == i
            if mm.sum() < 6: continue
            blobs.append((col, sl, mm))
    check_merges(blobs)
    blobs = [(c, sl, mm, False) for c, sl, mm in blobs] + edge_slivers(G, h, s, v, blobs)
    mmpx = G["mmpx"]; oy = G["wb_top"]
    stars = []
    for col, sl, mm, sliver in blobs:
        ys, xs = np.nonzero(mm); cy, cx = ys.mean() + sl[0].start, xs.mean() + sl[1].start
        ex = side_x(G["sil"], cy)
        x_side = (cx - ex) * mmpx; y_wb = (cy - oy) * mmpx
        x_mock = x_side
        moved = None
        if x_side - STAR_D / 2 < SIDE_KO:
            moved = round(SIDE_KO + STAR_D / 2 - x_side, 1); x_side = SIDE_KO + STAR_D / 2
        oyp = opening_y(cx)
        gap = None if oyp is None else round((cy - oyp) * mmpx - STAR_D / 2, 1)    # star top edge below the opening, mm
        clipped = bool(sliver or sl[1].start <= ex + EDGE_PX)        # the candy runs off the garment edge on the mockup
        stars.append(dict(col=col, px=(round(cx, 1), round(cy, 1)), size_px=int(sl[1].stop - sl[1].start), side_px=round(ex, 1),
                          clipped=clipped, sliver_px=(int(mm.sum()) if sliver else None),
                          x_mockup_mm=round(x_mock, 1), x_from_side_mm=round(x_side, 1), y_from_waist_mm=round(y_wb, 1),
                          moved_in_mm=moved, below_opening_mm=gap,
                          inside_opening=bool(oyp is not None and cy < oyp)))
    stars.sort(key=lambda d: d["y_from_waist_mm"])
    for k, d in enumerate(stars, 1): d["id"] = f"S{k:02d}"
    return stars

# ---------------------------------------------------------------- founder answers 21 Oct (J4, J5)
EXCLUDE_CLIPPED = True   # J4: the 3 konpeito clipped by the side seam are DROPPED ("I don't think that's supposed to be there").
                         # The edge pass still DETECTS them (trace flags them clipped); this product excludes them from the map.

def product_map(stars, exclude_clipped=None):
    """the sewn konpeito map: trace result minus the clipped side-seam candies (J4), renumbered S01.. in y order.
    Returns (kept, excluded); every entry keeps its trace id in 'trace_id'."""
    ex = EXCLUDE_CLIPPED if exclude_clipped is None else exclude_clipped
    keep = [dict(d, trace_id=d["id"]) for d in stars if not (ex and d["clipped"])]
    drop = [dict(d, trace_id=d["id"]) for d in stars if ex and d["clipped"]]
    for k, d in enumerate(keep, 1): d["id"] = f"S{k:02d}"
    for k, d in enumerate(drop, 1): d["id"] = f"X{k}"
    return keep, drop

# J5 (founder 21 Oct): the soot-sprite characters on the front leg are KEPT (licence risk accepted by the founder,
# LESSONS A7 overridden for this product). Traced from the mockup: every sprite has a pair of white eyes on a black body.
SOOT_EYE_G = 130          # eye white: grey > 130, saturation < 0.25, next to the black body (grey < 35)
SOOT_BODY_G = 35          # body: grey < 35 within 12 px of the eye pair (holes filled)
SOOT_FUR = (0.2, 1.1)     # fuzz hairs reach 0.2-1.1 mm beyond the body edge (the light ring round each body on the mockup)
SOOT_EYE = (0.24, 0.31)   # eye white = 0.24 D wide x 0.31 D tall (mockup ~3.5 x 4.5 px on a 15 px body, compare_soot.png)
SOOT_EYE_OFF = 0.22      # eye-pair midpoint held within 0.22 D of the body centre
SOOT_EYE_SEP = (0.31, 0.38)   # eye centre spacing 0.31-0.38 D (min: the 0.24 D eyes keep a 1 mm gap) (traced: 4.1-5.5 mm on a 14.2 mm body)
SOOT_PUPIL_D = 1.2        # pupil: round satin dot, the house-minimum dot that reads
SOOT_LEG = 2.8            # 2 legs, 2.8 mm beyond the body, 28 deg either side of straight down (mockup: thin dark legs)

def trace_soot(G):
    """soot sprites on the mockup: eye pairs -> body centre (centroid of the black body), one uniform body diameter
    (median of the traced bodies), eye + pupil positions per sprite. Positions in the 07 frame (x from the side seam,
    y from the WB top), with the same side-seam keep-out as the konpeito."""
    a = np.asarray(Image.open(SRC).convert("RGB")).astype(float)
    g = a.mean(2); s = (a.max(2) - a.min(2)) / np.maximum(a.max(2), 1)
    w = (g > SOOT_EYE_G) & (s < 0.25) & ndi.binary_dilation(g < SOOT_BODY_G, iterations=2)
    w[:, :780] = False; w[:, 1010:] = False; w[:int(G["wb_top"]) + 100, :] = False
    w[60:186, 893:992] = False
    lab, _ = ndi.label(ndi.binary_dilation(w, iterations=2))
    H, W = g.shape; YY, XX = np.mgrid[0:H, 0:W]
    out = []
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        eye = (lab == i) & w
        if eye.sum() < 3: continue
        ys, xs = np.nonzero(eye); ex, ey = xs.mean(), ys.mean()
        oyp = opening_y(ex)
        if oyp is not None and ey < oyp: continue
        near = (XX - ex) ** 2 + (YY - ey) ** 2 < 12 ** 2
        body = ndi.binary_fill_holes(((g < SOOT_BODY_G) | eye) & near)
        bl, _ = ndi.label(body); k = bl[int(round(ey)), int(round(ex))] or np.bincount(bl[body]).argmax()
        by, bx = np.nonzero(bl == k)
        # the two eyes: split the white pixels along their longest spread
        P = np.c_[xs, ys].astype(float); c = P.mean(0); u, sv, vt = np.linalg.svd(P - c); ax = vt[0] * (1 if vt[0][0] >= 0 else -1)
        t_ = (P - c) @ ax; eyes = [P[t_ < 0].mean(0) if (t_ < 0).any() else c, P[t_ >= 0].mean(0)]
        pup = []
        for e in eyes:                                     # pupil: darkness-weighted centroid in a 5 x 5 window on the eye
            x0, y0 = int(round(e[0])) - 2, int(round(e[1])) - 2
            win = 255 - g[y0:y0 + 5, x0:x0 + 5]; wy, wx = np.mgrid[0:5, 0:5]
            pc = np.array([(wx * win).sum(), (wy * win).sum()]) / max(win.sum(), 1) + [x0, y0]
            pup.append(pc - e)
        out.append(dict(px=(round(float(bx.mean()), 1), round(float(by.mean()), 1)), d_px=round(2 * math.sqrt(len(bx) / math.pi), 1),
                        eyes_px=[[round(float(v), 2) for v in e] for e in eyes], pupil_off_px=[[round(float(v), 2) for v in p] for p in pup]))
    D_px = float(np.median([q["d_px"] for q in out])); mmpx = G["mmpx"]; oy = G["wb_top"]; D = D_px * mmpx
    R_out = D / 2 + SOOT_FUR[1]
    for q in out:
        cx, cy = q["px"]; e_ = side_x(G["sil"], cy)
        x_side = (cx - e_) * mmpx; moved = None
        if x_side - R_out < SIDE_KO: moved = round(SIDE_KO + R_out - x_side, 1); x_side = SIDE_KO + R_out
        ew = SOOT_EYE[0] * D; lim = 0.28 * ew
        # eyes: measured midpoint + axis; the body centroid is pulled by the candies on top of the body and by denim
        # shading, so the eye midpoint is held within SOOT_EYE_OFF x D of the body centre and the eye spacing within
        # SOOT_EYE_SEP x D (the eyes stay inside the body, as on every mockup sprite)
        (e1x, e1y), (e2x, e2y) = q["eyes_px"]
        mx, my = ((e1x + e2x) / 2 - cx) * mmpx, ((e1y + e2y) / 2 - cy) * mmpx
        r_ = math.hypot(mx, my); k_ = min(1.0, SOOT_EYE_OFF * D / r_) if r_ > 0 else 1.0; mx, my = mx * k_, my * k_
        sep = math.hypot(e2x - e1x, e2y - e1y) * mmpx; ang = math.atan2(e2y - e1y, e2x - e1x)
        sep = min(max(sep, SOOT_EYE_SEP[0] * D), SOOT_EYE_SEP[1] * D)
        eyes = [[mx - sep / 2 * math.cos(ang), my - sep / 2 * math.sin(ang)], [mx + sep / 2 * math.cos(ang), my + sep / 2 * math.sin(ang)]]
        q.update(d_mm=round(D, 2), x_from_side_mm=round(x_side, 1), y_from_waist_mm=round((cy - oy) * mmpx, 1), moved_in_mm=moved,
                 eye_mid_traced_mm=[round(((e1x + e2x) / 2 - cx) * mmpx, 2), round(((e1y + e2y) / 2 - cy) * mmpx, 2)],
                 eyes_mm=[[round(v, 2) for v in e] for e in eyes],
                 pupils_mm=[[round(float(np.clip(dx * mmpx, -lim, lim)), 2), round(float(np.clip(dy * mmpx, -lim, lim)), 2)] for dx, dy in q["pupil_off_px"]])
    out.sort(key=lambda q: q["y_from_waist_mm"])
    for k, q in enumerate(out, 1): q["id"] = f"K{k:02d}"
    return out

SOOT_ART_PATH = "inputs/soot_art.json"   # Rev B8: per-sprite art table, hand-read from the mockup (kjsootart.py)
SOOT_EYE_SP = 0.20        # eye white satin row spacing (0.40 same side): solid white, no split (eyes < 7 mm wide)
_ART = {}

def soot_art(path=SOOT_ART_PATH):
    if path not in _ART: _ART[path] = json.load(open(path))
    return _ART[path]

def _triple(pts, step=1.5):
    """triple run along a polyline (out, back, out), ~step mm stitches."""
    from shapely.geometry import LineString
    ln = LineString(pts); n = max(2, int(math.ceil(ln.length / step)))
    f = [tuple(ln.interpolate(ln.length * k / n).coords[0]) for k in range(n + 1)]
    return f + f[-2::-1] + f[1:]

def _eye_satin(c, w, h, tilt, sp=SOOT_EYE_SP):
    """one satin oval: centre-run underlay along the long axis, then a zigzag across the width, needle points on
    alternate sides every sp mm (2 x sp on the same side); no split (w < 7 mm), no short connector stitches."""
    t = math.radians(tilt); ux, uy = math.cos(t), math.sin(t); vx, vy = -uy, ux        # u = across (width), v = long axis
    a, b = w / 2, h / 2
    P = lambda s, r: (c[0] + ux * s + vx * r, c[1] + uy * s + vy * r)
    und = [P(0, -b + 0.6), P(0, b - 0.6)]
    n = max(4, int(h / sp)); zz = []
    for k in range(n + 1):
        r = -b + h * k / n; hw = a * math.sqrt(max(0.0, 1 - (r / b) ** 2))
        if hw < 0.3: continue
        zz.append(P(-hw if len(zz) % 2 == 0 else hw, r))
    return [und, zz]

def soot_regions(q, x=None, y=None, seed=None, art=None):
    """one soot sprite in leg mm: black tatami body, radial fuzz of random length (prebuilt block), then from the Rev B8
    art table (inputs/soot_art.json, by K id): its limbs (arms to the candies it holds, legs) as triple runs, 2 white satin
    eyes at the table size/tilt and 2 black satin-dot pupils offset by ONE shared gaze vector."""
    from shapely.geometry import Point, LineString
    from shapely import affinity
    import kjsvg
    cx = q["x_from_side_mm"] if x is None else x; cy = q["y_from_waist_mm"] if y is None else y
    D = q["d_mm"]; R = D / 2
    A = (art or soot_art())["sprites"][q["id"]]
    rng = np.random.default_rng(seed if seed is not None else int(q["id"][1:]) * 7919)
    regs = [dict(col="kj_soot", geom=Point(cx, cy).buffer(R - 0.15, quad_segs=24), st="tatami", ang=45.0, grp="SOOT", layer=0)]
    n = int(round(2 * math.pi * (R + 0.6) / 0.42)); pts = []
    for k in range(n):
        th = 2 * math.pi * k / n
        r_ = R - 1.0 if k % 2 == 0 else R + SOOT_FUR[0] + rng.random() * (SOOT_FUR[1] - SOOT_FUR[0])
        pts.append((cx + r_ * math.cos(th), cy + r_ * math.sin(th)))
    pts.append(pts[0])
    ring = Point(cx, cy).buffer(R + SOOT_FUR[1], quad_segs=24).difference(Point(cx, cy).buffer(R - 1.0, quad_segs=24))
    regs.append(dict(col="kj_soot", geom=ring, st="satin", ang="pre", grp="FUR", layer=0, pre=[pts]))
    for L in A["limbs"]:
        P = [(cx + px_, cy + py_) for px_, py_ in L["pts"]]
        regs.append(dict(col="kj_soot", geom=LineString(P).buffer(0.25), st="bean", ang="pre", grp="LEG", layer=0, pre=[_triple(P)], limb=L["kind"]))
    E = A["eyes"]; gx, gy = E["gaze"]
    for ex, ey in E["centres"]:
        c = (cx + ex, cy + ey)
        e = affinity.rotate(affinity.scale(Point(c).buffer(1.0, quad_segs=24), E["w"] / 2, E["h"] / 2), E["tilt_deg"], origin=c)
        regs.append(dict(col="kj_white", geom=e, st="satin", ang="pre", grp="EYE", layer=0, pre=_eye_satin(c, E["w"], E["h"], E["tilt_deg"])))
        regs.append(kjsvg.bead("kj_soot", "PUPIL", Point(c[0] + gx, c[1] + gy).buffer(E["pupil"] / 2 + 0.1, quad_segs=16), E["pupil"]))
    return regs

def sections(stars, frame=None):
    """group items (konpeito + soot sprites) into hoopings that fit the factory frame (largest frame - 16 mm margin)."""
    import factory
    fw, fh = factory.largest_frame()
    big = max([STAR_D] + [d.get("d_mm", 0) + 2 * SOOT_FUR[1] for d in stars])
    lim = min(fw, fh) - 16.0 - big
    secs = []
    for d in sorted(stars, key=lambda q: q["y_from_waist_mm"]):
        if secs and d["y_from_waist_mm"] - secs[-1][0]["y_from_waist_mm"] <= lim:
            xs = [q["x_from_side_mm"] for q in secs[-1]] + [d["x_from_side_mm"]]
            if max(xs) - min(xs) <= lim: secs[-1].append(d); continue
        secs.append([d])
    return secs

def section_vis(sec):
    """regions for one hooping, in leg mm (x from side seam, y from waistband top): konpeito (S..) + soot sprites (K..)."""
    import kjsvg          # founder change 20 Oct: the 02 facing konpeito, same digitising, 10 mm
    from shapely.ops import unary_union
    cands = [d for d in sec if not d["id"].startswith("K")]; soots = [d for d in sec if d["id"].startswith("K")]
    per = [(d, kjsvg.konpeito_regions(COLS[d["col"]][0], d["x_from_side_mm"], d["y_from_waist_mm"], STAR_D)) for d in cands]
    # overlapping konpeito (S06 yellow under S07 pink, PR #34 review): the candy sewn later (stop order yellow -> pink ->
    # blue, kjstitch._FRONT_PLAN) lies on top, as on the mockup; the white bead specks are sewn last, so a speck of the
    # candy underneath that falls under a later candy's body is dropped (it would show on top of the front candy).
    RANK = {"yellow": 0, "pink": 1, "blue": 2}
    vis = []
    for d, rs in per:
        tops = [unary_union([r["geom"] for r in rs2 if r["grp"] != "KNOT"]) for e, rs2 in per
                if e is not d and RANK[e["col"]] > RANK[d["col"]]
                and math.dist((e["x_from_side_mm"], e["y_from_waist_mm"]), (d["x_from_side_mm"], d["y_from_waist_mm"])) < STAR_D]
        if tops:
            top = unary_union(tops).buffer(0.3)
            rs = [r for r in rs if not (r["grp"] == "KNOT" and r["geom"].intersects(top))]
        vis += rs
    # soot sprites (J5): sewn FIRST (black), the konpeito they hold lie on top (as on the mockup); the body tatami is
    # cut away under the candies (0.5 mm overlap kept) so the candy satin does not sit on a full tatami layer.
    cand_body = unary_union([r["geom"] for _, rs in per for r in rs if r["grp"] in ("STAR",)]) if per else None
    sv = []
    for q in soots:
        for r in soot_regions(q):
            if r["grp"] == "SOOT" and cand_body is not None and not cand_body.is_empty:
                r = dict(r, geom=r["geom"].difference(cand_body.buffer(-0.5)))
            sv.append(r)
    return sv + vis

def overlay(G, stars, out="out/check_07_mockup.png", s=3, soot=(), dropped=()):
    """the corrected map drawn back onto the mockup: WB scale line, origin, pocket opening, star centres + ids."""
    im = Image.open(SRC).convert("RGB")
    x0, y0, x1, y1 = 790, 20, 1080, 920
    c = im.crop((x0, y0, x1, y1)).resize(((x1 - x0) * s, (y1 - y0) * s), Image.LANCZOS)
    d = ImageDraw.Draw(c)
    try: fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    except Exception: fnt = ImageFont.load_default()
    P = lambda x, y: ((x - x0) * s, (y - y0) * s)
    # waistband scale line (clipped to the crop) + origin
    d.line([P(G["origin"][0], G["wb_mid"]), P(x1, G["wb_mid"])], fill=(0, 200, 255), width=3)
    d.text(P(G["origin"][0] + 40, G["wb_mid"] - 14), f"WB width {G['wb_w_px']:.1f} px = 420.4 mm", fill=(0, 200, 255), font=fnt)
    ox, oy = P(*G["origin"]); d.ellipse([ox - 9, oy - 9, ox + 9, oy + 9], outline=(0, 255, 0), width=4)
    d.text((ox + 12, oy + 2), "O (0,0)", fill=(0, 255, 0), font=fnt)
    d.line([P(*p) for p in POCKET_OPENING_PX], fill=(255, 140, 0), width=5)
    d.text(P(1026, 160), "pocket\nopening", fill=(255, 140, 0), font=fnt)
    # labels in a column right of the stars, pushed apart + leader lines (PR #34 review item 3: S01/S02 overlapped)
    r = STAR_D / G["mmpx"] / 2 * s
    pts = [P(*st["px"]) for st in stars]
    xl = max(x for x, _ in pts) + r + 40
    order = sorted(range(len(pts)), key=lambda i: pts[i][1]); ly = [0.0] * len(pts); last = -1e9
    for i in order: ly[i] = max(pts[i][1], last + 28); last = ly[i]
    for st, (cx, cy), yl in zip(stars, pts, ly):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255), width=3)
        d.line([(cx + r, cy), (xl - 4, yl)], fill=(255, 255, 255), width=2)
        d.text((xl, yl - 12), st["id"], fill=(255, 255, 255), font=fnt, stroke_width=2, stroke_fill=(0, 0, 0))
    # soot sprites (J5, kept): traced body circle (uniform D) + eye centres, labels left of the leg
    for q in soot:
        cx, cy = P(*q["px"]); rr = q["d_mm"] / G["mmpx"] / 2 * s
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(120, 255, 120), width=3)
        for ex_, ey_ in q["eyes_px"]:
            ex2, ey2 = P(ex_, ey_); d.ellipse([ex2 - 3, ey2 - 3, ex2 + 3, ey2 + 3], outline=(120, 255, 120), width=2)
        d.text((cx - rr - 52, cy - 12), q["id"], fill=(120, 255, 120), font=fnt, stroke_width=2, stroke_fill=(0, 0, 0))
    # konpeito clipped by the side seam: detected, NOT sewn (J4)
    for q in dropped:
        cx, cy = P(*q["px"])
        d.line([(cx - 10, cy - 10), (cx + 10, cy + 10)], fill=(255, 60, 60), width=4); d.line([(cx - 10, cy + 10), (cx + 10, cy - 10)], fill=(255, 60, 60), width=4)
        d.text((cx + 14, cy - 12), q["id"], fill=(255, 60, 60), font=fnt, stroke_width=2, stroke_fill=(0, 0, 0))
    c.save(out)
    # grid used to read the pocket opening (kept as evidence)
    x0g, y0g, x1g, y1g = 840, 30, 1060, 240; sg = 5
    g = im.crop((x0g, y0g, x1g, y1g)).resize(((x1g - x0g) * sg, (y1g - y0g) * sg), Image.NEAREST); dg = ImageDraw.Draw(g)
    for x in range(x0g, x1g, 10): dg.line([((x - x0g) * sg, 0), ((x - x0g) * sg, g.height)], fill=(0, 255, 0) if x % 50 == 0 else (0, 90, 0))
    for y in range(y0g, y1g, 10): dg.line([(0, (y - y0g) * sg), (g.width, (y - y0g) * sg)], fill=(0, 255, 0) if y % 50 == 0 else (0, 90, 0))
    dg.line([((x - x0g) * sg, (y - y0g) * sg) for x, y in POCKET_OPENING_PX], fill=(255, 140, 0), width=3)
    g.save("out/check_07_pocket_grid.png")

if __name__ == "__main__":
    G = geometry(); det = trace(G); st, dropped = product_map(det); soot = trace_soot(G); secs = sections(st + soot)
    der = dict(half_waist_mm=round(HALF_WAIST_MM, 1), wb_width_px=round(G["wb_w_px"], 1), wb_mid_row_px=G["wb_mid"],
               mm_per_px=round(G["mmpx"], 4), origin_px=[round(v, 1) for v in G["origin"]],
               pocket_opening_px=POCKET_OPENING_PX,
               pocket_opening_mm=[[round((x - G["origin"][0]) * G["mmpx"], 1), round((y - G["wb_top"]) * G["mmpx"], 1)] for x, y in POCKET_OPENING_PX],
               stars_inside_opening=[d["id"] for d in st if d["inside_opening"]],
               detected=len(det), detected_clipped=sum(1 for d in det if d["clipped"]), exclude_clipped=EXCLUDE_CLIPPED,
               soot_d_px_traced=[q["d_px"] for q in soot])
    json.dump(dict(stars=st, excluded_clipped=dropped, soot=soot, sections=[[d["id"] for d in s] for s in secs], mm_per_px=G["mmpx"], derivation=der),
              open("out/front_stars.json", "w"), indent=1)
    overlay(G, st, soot=soot, dropped=dropped)
    print(json.dumps(der, indent=1))
    for d in st: print(d)
    for q in soot: print(q)
    print("excluded:", [(d["trace_id"], d["col"]) for d in dropped])
    print([[d["id"] for d in s] for s in secs])
