"""Compose the four badges + the star field on the size-M pieces (garment mm, unclipped).
Badge layout (anchor positions, angles, motif counts) is read from the mockup (inputs/flat.png) through mockmap: each
badge is placed at its mapped anchor (P) and drawn at the uniform motif scale S about it. Text is SET FROM FONTS with
the brief's exact characters (kclettering), never traced from the AI glyphs. Star speckles: detected on the mockup
(white specks), positions mapped, sizes from the speck extents. Sleeves: the visible (front) half is mapped from the
mockup sleeve; the back half gets a seeded field at the same density + size mix.  [PROPOSED: back half of sleeves]
Output: scene.pkl = {"items": {"FR": [...], "FL": [...], "SR": [...], "SL": [...]}, "meta": {...}}.
usage: python3 scene.py [preview]"""
import kccore
import math, random, pickle, sys, json
import numpy as np
from scipy import ndimage as ndi
from PIL import Image
from shapely.geometry import Point, Polygon, LineString, box, MultiPoint
from shapely.ops import unary_union
from shapely import affinity
import mockmap as MM, front as F, kcmotifs as KM, kclettering as KL, kcsatin as KS, kctrace as TR

S = MM.S
items = {"FR": [], "FL": [], "SR": [], "SL": []}
META = {"badges": {}, "counts": {}, "traced": {}}
FAMC = {"kc_mint": "mint", "kc_blue": "blue", "kc_red": "red", "kc_lemon": "yellow", "kc_gold": "yellow", "kc_white": "white"}
def tr_log(el, kind, found):
    d = META["traced"].setdefault(el, {}); k = d.setdefault(kind, [0, 0]); k[0] += 1; k[1] += bool(found)

def ref_fn_for(anchor_px, anchor_mm, fam):
    """mockup family mask on a garment-mm grid, uniform motif scale S about a badge anchor (as the badge was placed)"""
    from scipy.ndimage import map_coordinates
    def f(bb, ppm):
        x0, y0, x1, y1 = bb; W, H = int((x1 - x0) * ppm), int((y1 - y0) * ppm)
        XX, YY = np.meshgrid(x0 + (np.arange(W) + 0.5) / ppm, y0 + (np.arange(H) + 0.5) / ppm)
        px = anchor_px[0] + (XX - anchor_mm[0]) / S; py = anchor_px[1] + (YY - anchor_mm[1]) / S
        a = MM.mock(); ch = [map_coordinates(a[..., k], [py, px], order=3, mode="nearest") for k in range(3)]
        return ndi.binary_closing(ndi.binary_opening(TR.FAM[fam](*ch), iterations=1), iterations=3)
    return f
SP_STARTS = [(0.0, 1.0), (45.0, 1.0), (0.0, 0.8), (0.0, 1.25), (45.0, 0.8), (45.0, 1.25)]
def fit(regs, fn, el, kind, aspect=False, starts=None, ret_iou=False):
    """trace a motif: fit its geometry to its reference silhouette (shift / rotation / scale, IoU) and apply to every region"""
    regs = [r for r in regs if r is not None]
    body = unary_union([r["geom"] for r in regs if not r.get("glow")])
    if body.is_empty: return regs
    _, info = TR.register_glyph(body, fn, aspect=aspect, starts=starts, drop_frag=kind in ("sparkle", "dot"))
    META["traced"].setdefault(el, {}).setdefault("fits", []).append(dict(kind=kind, iou_before=info["iou_before"], iou_after=info["iou_after"], scale=info["scale"], aspect=info["aspect"]))
    return (TR.apply(regs, info), info["iou_after"]) if ret_iou else TR.apply(regs, info)
def best_star(make, ks, fn, el, kind):
    """trace a star's SHAPE too: try inner-radius ratios ks, fit each (affine + aspect), keep the best IoU"""
    best = None
    for k in ks:
        regs = [r for r in make(k) if not r["geom"].is_empty]
        body = unary_union([r["geom"] for r in regs if not r.get("glow")])
        _, info = TR.register_glyph(body, fn, aspect=True)
        if best is None or info["iou_after"] > best[0]: best = (info["iou_after"], k, regs, info)
    META["traced"].setdefault(el, {}).setdefault("fits", []).append(dict(kind=kind, k=best[1], iou_after=best[3]["iou_after"], iou_before=best[3]["iou_before"], scale=best[3]["scale"], aspect=best[3]["aspect"]))
    return TR.apply(best[2], best[3])
def trace_ring(fn, cx, cy, a, b, ang, w0, n=96):
    """KR oval ring traced from the mockup: per direction from the centre, the inner + outer edge of the ring silhouette ->
    centreline + width table (the render's ring is thicker on its near side)"""
    bb = (cx - a - 8, cy - a - 8, cx + a + 8, cy + a + 8); ppm = 6.0; m = fn(bb, ppm)
    pts, ws = [], []
    for t in np.linspace(0, 2 * math.pi, n, endpoint=False):
        ex = (a * math.cos(t) * math.cos(math.radians(ang)) - b * math.sin(t) * math.sin(math.radians(ang)))
        ey = (a * math.cos(t) * math.sin(math.radians(ang)) + b * math.sin(t) * math.cos(math.radians(ang)))
        L = math.hypot(ex, ey); ux, uy = ex / L, ey / L
        rr = np.arange(max(0.0, L - 7.0), L + 7.0, 1.0 / ppm)
        xs = ((cx + ux * rr - bb[0]) * ppm).astype(int); ys = ((cy + uy * rr - bb[1]) * ppm).astype(int)
        ok = (xs >= 0) & (ys >= 0) & (xs < m.shape[1]) & (ys < m.shape[0])
        on = np.zeros(len(rr), bool); on[ok] = m[ys[ok], xs[ok]]
        if on.sum() < 4: pts.append((cx + ex * (1 - w0 / 2 / L), cy + ey * (1 - w0 / 2 / L))); ws.append(w0); continue
        idx = np.nonzero(on)[0]; r_in, r_out = rr[idx[0]], rr[idx[-1]]
        pts.append((cx + ux * (r_in + r_out) / 2, cy + uy * (r_in + r_out) / 2)); ws.append(max(2.0, r_out - r_in))
    # width = 2 x distance to the ring edge at each centreline point (radial rays cross the long sides obliquely)
    dtm = ndi.distance_transform_edt(m) / ppm
    for i, (x, y) in enumerate(pts):
        xi, yi = int((x - bb[0]) * ppm), int((y - bb[1]) * ppm)
        if 0 <= yi < m.shape[0] and 0 <= xi < m.shape[1] and m[yi, xi]: ws[i] = max(2.0, 2 * dtm[max(0, yi-1):yi+2, max(0, xi-1):xi+2].max())
    ws = np.array(ws); ws = np.convolve(np.r_[ws[-3:], ws, ws[:3]], np.ones(7) / 7, "valid")
    W = float(ws.max()); prof = ("table", list(ws / W) + [ws[0] / W])
    return pts, W, prof, float(ws.min()), float(ws.max())
def fit_pair(pair, fn, el, kind, aspect=False):
    core, rim = pair[0], pair[1]; n = len(core); allr = fit(core + rim, fn, el, kind, aspect); return allr[:n], allr[n:]
def ref_fn_field(fam):
    """front field reference: positions through mockmap (as the field stars were mapped), SHAPES at the uniform motif scale
    S about the window centre (the non-uniform front map squashes round stars by 0.70 / 0.90)"""
    from scipy.ndimage import map_coordinates
    def f(bb, ppm):
        x0, y0, x1, y1 = bb; W, H = int((x1 - x0) * ppm), int((y1 - y0) * ppm)
        XX, YY = np.meshgrid(x0 + (np.arange(W) + 0.5) / ppm, y0 + (np.arange(H) + 0.5) / ppm)
        mx, my = (x0 + x1) / 2, (y0 + y1) / 2; cpx, cpy = MM.Pinv(mx, my)
        px, py = cpx + (XX - mx) / S, cpy + (YY - my) / S; a = MM.mock(); ch = [map_coordinates(a[..., k], [py, px], order=3, mode="nearest") for k in range(3)]
        return ndi.binary_closing(TR.FAM[fam](*ch), iterations=3)
    return f
def register(glyphs, fn, el):
    out = []
    for ch, g in glyphs:
        g2, info = TR.register_glyph(g, fn, size_rule=False); out.append((ch, g2))          # font glyphs: IoU only
        META["traced"].setdefault(el, {}).setdefault("glyph fits", []).append(dict(ch=ch, **info))
    return out
def star_from(c, rot0, k=0.48):
    """5-point star size (tip-to-tip, = 2R) + rotation from a traced component (bounding box of a star = 1.90R x 1.81R)"""
    size = max(c["ext_w"] / 0.95, c["ext_h"] / 0.905) * S
    rot = c["tip_ang"] + 90.0
    while rot - rot0 > 36: rot -= 72
    while rot0 - rot > 36: rot += 72
    return size, rot
def add(piece, regs, layer, el, unit=None, **kw):
    for r in regs:
        g = r["geom"]
        if g is None or g.is_empty: continue
        r = dict(r); r.update(kw); r["layer"] = layer; r["el"] = el
        r["z"] = layer*100000 + len(items[piece]); r.setdefault("ko", True); r.setdefault("kob", 0.0)
        r["unit"] = unit if unit is not None else r.get("unit")
        items[piece].append(r)

def anchor(px, py):
    """local uniform map about a mockup anchor point: mockup px -> garment mm"""
    ax, ay = MM.P(px, py)
    return lambda qx, qy: (ax + (qx - px)*S, ay + (qy - py)*S)

def text_regs(glyphs, col, code, unit, cap, rim=False, layer=31):
    """Rev B: one satin column per font stroke (kcsatin); puff text gets a lighter rim column round every stroke edge.
    Rev D: puff text strokes narrower than kccore.PUFF_MIN_MM stay flat (KM.text_columns logs every decision)."""
    core, rims = KM.text_columns(glyphs, col, code, cap, unit, rim=rim, puff_min=kccore.PUFF_MIN_MM if code.startswith("PF-") else None)
    return core, rims

def ref_glyphs(el, piece, glyphs, threads):
    """Rev C glyph gate (glyph_gate.py): the FONT's own glyph outlines as placed here (never the stroke columns), with the
    threads that stitch them; the gate compares each one with the stitched text read back from the DST."""
    META.setdefault("glyphs", {}).setdefault(el, []).extend(dict(ch=ch, piece=piece, wkt=g.wkt, threads=threads) for ch, g in glyphs)

def put(piece, pair, layer, el, unit, rim_layer=32):
    core, rim = pair[0], pair[1]
    add(piece, core, layer, el, unit=unit); add(piece, rim, rim_layer, el, unit=unit)

# ================================================================ 01 JP badge  (FR, wearer's right chest)
J0 = (398.75, 491.25); J = anchor(*J0)
JC = J(*J0)
# Rev B (review item 4): the mockup's text runs on a CURVED baseline. Glyph centres measured on the mockup (mint pixels,
# components per glyph, mockup px): each glyph is centred there and turned to the local tangent of a quadratic fitted
# through the centres.
JP_C = [(329.6, 534.7), (351.7, 520.7), (372.4, 502.6), (393.9, 486.8), (417.3, 474.7), (441.6, 460.5), (463.3, 447.5)]
_cx = np.array([c[0] for c in JP_C]); _cy = np.array([c[1] for c in JP_C]); JP_FIT = np.polyfit(_cx, _cy, 2)
def jp_tangent(px): return math.degrees(math.atan(2 * JP_FIT[0] * px + JP_FIT[1]))
em_jp = 25.0                   # traced: glyph fits at em 22 all scaled to 1.11-1.19
jp = []
for ch, (px, py) in zip(kccore.TEXT["01"], JP_C):
    g, _ = KL.glyph("jp", ch, em_jp); b = g.bounds
    py_fit = float(np.polyval(JP_FIT, px)); cx_, cy_ = J(px, (py + py_fit) / 2)
    g = affinity.translate(g, cx_ - (b[0] + b[2]) / 2, cy_ - (b[1] + b[3]) / 2)
    jp.append((ch, affinity.rotate(g, jp_tangent(px), origin=(cx_, cy_)).buffer(0)))
JANG = jp_tangent(float(np.mean(_cx)))
META["badges"]["01"] = dict(anchor_px=J0, centre=JC, angle=JANG, angle_start=jp_tangent(_cx[0]), angle_end=jp_tangent(_cx[-1]),
                            em=em_jp, text=kccore.TEXT["01"], baseline="quadratic through the 7 measured glyph centres")
jp = register(jp, ref_fn_for(J0, JC, "mint"), "01")          # each glyph fitted to the mockup glyph silhouette (A14)
jcore, jrim = text_regs(jp, "kc_mint", "PF-TXC", "01-text", "round", rim=True); ref_glyphs("01", "FR", jp, ["kc_mint", "kc_mint_lt"])
jshape = unary_union([r["geom"] for r in jcore + jrim])
add("FR", KM.stipple_band(jshape, "01-glow", outer=4.5, seed=11), 20, "01", unit="01-glow")
# Rev C (review of PR #20): the mockup has a small mint dot right of い (A14 row 'moved', 5.8 mm2, 93 mm from CF) that no
# Rev B/C motif stitched. Traced from the mockup's own mint component (TR.comps), flat satin dot (code DOT, mint).
_dp = (J0[0] + (-93.0 - JC[0]) / S, J0[1] + (111.2 - JC[1]) / S)
_dc = [c for c in TR.comps("mint", (int(_dp[0]) - 10, int(_dp[1]) - 10, int(_dp[0]) + 10, int(_dp[1]) + 10)) if c["area"] > 1]
if _dc:
    _c = min(_dc, key=lambda c: math.hypot(c["cx"] - _dp[0], c["cy"] - _dp[1]))
    _x, _y = J(_c["cx"], _c["cy"]); _d = max(1.45, 2 * math.sqrt(_c["area"] * S * S / math.pi))
    _a = math.radians(35.0); _r = _d / 2
    _code = "PF-DOT" if _d >= kccore.PUFF_MIN_MM else "DOT"     # Rev D: sign part -> puff if wide enough
    KM.PUFF_LOG.append(dict(unit="01-dot2", ch="dot", strokes=1, puff=int(_code != "DOT"), flat=int(_code == "DOT"), share=1.0, w_min=round(_d, 2), w_med=round(_d, 2), w_max=round(_d, 2),
                            flat_w_max=round(_d, 2) if _code == "DOT" else None, below_house=int(_code != "DOT" and _d < kccore.PUFF_HOUSE_MIN_MM)))
    add("FR", [KS.column_region("kc_mint", _code, [(_x - math.cos(_a) * _r, _y - math.sin(_a) * _r), (_x + math.cos(_a) * _r, _y + math.sin(_a) * _r)], _d)],
        22, "01", unit="01-dot2")
    META["traced"].setdefault("01", {})["small mint dot"] = dict(x=round(_x, 1), y=round(_y, 1), d=round(_d, 2))
BARS_JP = [  # mockup px centre, length px, angle deg (y down), colour  (17 bars, counted on the mockup)
    ((298.5, 537.2), 26.0, -8, "kc_mint"), ((347.6, 474.3), 23.0, 52, "kc_mint"), ((454.8, 495.9), 25.6, 52, "kc_mint"),
    ((465.6, 410.5), 25.7, 110, "kc_blue"), ((401.0, 439.6), 16.3, 73, "kc_blue"), ((314.0, 512.7), 11.9, 42, "kc_blue"),
    ((403.0, 520.9), 15.8, 54, "kc_blue"), ((345.9, 569.4), 21.2, 83, "kc_blue"), ((336.9, 591.9), 12.6, 100, "kc_blue"),
    ((474.4, 424.3), 8.8, 133, "kc_red"), ((492.7, 450.2), 17.6, -7, "kc_red"), ((439.0, 500.5), 16.9, 69, "kc_red"),
    ((390.8, 539.7), 32.0, 60, "kc_red"),
    ((493.3, 472.8), 29.2, 16, "kc_lemon"), ((329.5, 566.3), 17.4, 106, "kc_lemon"), ((339.4, 489.4), 16.0, 45, "kc_lemon"),
    ((373.8, 451.3), 28.5, 52, "kc_lemon"),
]
for i, ((px, py), L, a, col) in enumerate(BARS_JP):
    c = TR.snap(FAMC[col], px, py); tr_log("01", "spark bars", c)
    w = 3.4 if L > 10 else 3.0
    if c: px, py, L, a, w = c["cx"], c["cy"], c["L"], TR.axis_near(c["ang"], a), c["W"] * S       # traced (A14)
    w = min(4.4, max(2.2, w)); cx, cy = J(px, py)
    put("FR", fit_pair(KM.bar_rc(cx, cy, max(L*S, w + 1), w, a, col, f"01-bar{i}"), ref_fn_for(J0, JC, FAMC[col]), "01", "bar", aspect=True), 30, "01", f"01-bar{i}")
c = TR.snap("mint", 523.2, 480.0); tr_log("01", "dot", c)
put("FR", fit_pair(KM.disc_rc(*J(*((c["cx"], c["cy"]) if c else (523.2, 480.0))), 2 * math.sqrt(c["area"] / math.pi) * S if c else 9.4, "kc_mint", "01-dot"), ref_fn_for(J0, JC, "mint"), "01", "dot"), 30, "01", "01-dot")
for k, (pos, sz, rot) in enumerate((((395.6, 421.0), 12.0, 0), ((333.3, 459.5), 10.4, -8))):
    c = TR.snap("red", *pos); tr_log("01", "hearts", c)
    if c: pos, sz = (c["cx"], c["cy"]), c["ext_w"] * S / 0.98
    hc, hr, _ = KM.heart_rc(*J(*pos), sz, "kc_red", f"01-heart{k}", rot=rot); hc, hr = fit_pair((hc, hr), ref_fn_for(J0, JC, "red"), "01", "heart")
    add("FR", hc, 30, "01", unit=f"01-heart{k}"); add("FR", hr, 32, "01", unit=f"01-heart{k}")
# left star with face (two knocked-out eyes), faceted
c = TR.snap("yellow", 303.8, 501.3); tr_log("01", "stars", c)
sz0, rot0 = star_from(c, -12) if c else (14.0, -12)
sx0, sy0 = J(*((c["cx"], c["cy"]) if c else (303.8, 501.3))); fs, _ = KM.star_facets(sx0, sy0, sz0, "kc_gold", "01-star0", rot=rot0)
FACE_K = [0.44, 0.50, 0.56, 0.62]
eyes = unary_union([Point(sx0 - sz0/2*0.2, sy0 - sz0/2*0.02).buffer(0.9), Point(sx0 + sz0/2*0.2, sy0 - sz0/2*0.02).buffer(0.9)])
# traced (A14): the eyes are the dark holes inside the mockup's star silhouette
_fb = (sx0 - sz0 * 0.6, sy0 - sz0 * 0.6, sx0 + sz0 * 0.6, sy0 + sz0 * 0.6); _m = ref_fn_for(J0, JC, "yellow")(_fb, 8.0)
_lab, _ = ndi.label(_m); _k = _lab[_m.shape[0] // 2 - 4:_m.shape[0] // 2 + 4, _m.shape[1] // 2 - 4:_m.shape[1] // 2 + 4].max()
if _k:
    _hl, _nh = ndi.label(ndi.binary_fill_holes(_lab == _k) & ~(_lab == _k)); _ey = []
    for _j in range(1, _nh + 1):
        _ys, _xs = np.nonzero(_hl == _j); _a = len(_ys) / 64.0
        if 0.3 < _a < 8: _ey.append(Point(_fb[0] + (_xs.mean() + 0.5) / 8, _fb[1] + (_ys.mean() + 0.5) / 8).buffer(max(0.75, math.sqrt(_a / math.pi))))
    if _ey: eyes = unary_union(_ey); META["traced"].setdefault("01", {})["face star eyes"] = len(_ey)
fs = [dict(r, geom=r["geom"].difference(eyes).buffer(0)) for r in fs]
add("FR", best_star(lambda k: [dict(r, geom=r["geom"].difference(eyes).buffer(0)) for r in KM.star_facets(sx0, sy0, sz0, "kc_gold", "01-star0", rot=rot0, k=k)[0]],
                    FACE_K, ref_fn_for(J0, JC, "yellow"), "01", "star (face)"), 30, "01", unit="01-star0")
# top star (review item 5): slender 5-point star, dark centre pit with a white dot
c = TR.snap("yellow", 460.0, 391.3); tr_log("01", "stars", c)
sz1, rot1 = star_from(c, 6) if c else (14.4, 6)
sx1, sy1 = J(*((c["cx"], c["cy"]) if c else (460.0, 391.3)))
# Rev E (review PR #31 item 1): the mockup's centre is a small dark pit (fabric, r 0.6) inside a WHITE ring (satin column
# r 0.6..1.9), and the upper facet of the upper-left arm carries the white glint. Star facets end at the ring (pit = 1.9 mm).
_TOP_PIT_R, _TOP_RING_W = 0.6, 1.3
def _top_star(kp):
    regs = KM.star_facets(sx1, sy1, sz1, "kc_gold", "01-star1", rot=rot1, k=kp, pit=(_TOP_PIT_R + _TOP_RING_W) / (sz1 / 2), round_=0.12)[0]
    out = []
    for r in regs:
        c = r["geom"].centroid; a = math.degrees(math.atan2(c.y - sy1, c.x - sx1))
        # glint: the upper (light) facet of the upper-left arm (centroid ~ -150 deg, y down)
        out.append(dict(r, col="kc_white", grp="FACE") if (-158 <= a <= -125 and r["col"] != "kc_gold") else r)
    rc = _TOP_PIT_R + _TOP_RING_W / 2
    ring = [(sx1 + rc * math.cos(math.radians(t)), sy1 + rc * math.sin(math.radians(t))) for t in range(0, 360, 15)]
    return out + [KS.column_region("kc_white", "FACE", ring, _TOP_RING_W, ("flat", "flat"), True, unit="01-star1")]
fs = best_star(_top_star, (0.20, 0.23, 0.26, 0.30, 0.34, 0.38), ref_fn_for(J0, JC, "yellow"), "01", "star (top)")
add("FR", [r for r in fs if r["grp"] != "FACE"], 30, "01", unit="01-star1"); add("FR", [r for r in fs if r["grp"] == "FACE"], 33, "01", unit="01-star1")
# small top-right star: a 4-point sparkle in star gold (mockup)
c = TR.snap("yellow", 482.5, 415.0); tr_log("01", "stars", c)
_s2 = fit(KM.sparkle_cols(*J(*((c["cx"], c["cy"]) if c else (482.5, 415.0))), max(c["ext_w"], c["ext_h"]) * S if c else 6.0, "kc_gold", "01-star2", code="SPK"), ref_fn_for(J0, JC, "yellow"), "01", "sparkle")
# Rev D: the small 4-point sparkle of the JP badge is a sign part, but its arms TAPER to points: the widest point (centre)
# is the column width, the arms are narrower over most of their length -> flat (logged with the measured width)
_w2 = max([r.get("col_w") or 0 for r in _s2] or [0])
KM.PUFF_LOG.append(dict(unit="01-star2", ch="sparkle", strokes=len(_s2), puff=0, flat=len(_s2), share=0.0, w_min=None, w_med=None, w_max=round(_w2, 2), flat_w_max=round(_w2, 2), below_house=0,
                        note="tapered 4-point arms: %.2f mm at the centre, to a point at the tips" % _w2))
add("FR", _s2, 22, "01", unit="01-star2")
# bottom red star (review item 5): SOLID red, faceted, with a small dark star pit (fabric) in the middle
c = TR.snap("red", 406.3, 563.8); tr_log("01", "stars", c)
sz3, rot3 = star_from(c, 10) if c else (15.0, 10)
_p3 = J(*((c["cx"], c["cy"]) if c else (406.3, 563.8)))
# Rev E (review PR #31 item 1): mockup red star = ONE saturated red (no light facets) with a dark star-shaped pit
# measured ~0.43 of the star radius; pit star sharper (k 0.42) so its points read at that size
add("FR", best_star(lambda k: KM.star_facets(*_p3, sz3, "kc_red", "01-star3", rot=rot3, k=k, light="kc_red", pit=0.45, pit_shape="star", pit_k=0.42)[0], [0.40, 0.46, 0.52, 0.58],
                    ref_fn_for(J0, JC, "red"), "01", "star (red)"), 30, "01", unit="01-star3")
put("FR", (jcore, jrim), 31, "01", "01-text")

# ================================================================ 02 EN badge  (FL, wearer's left chest)
E0 = (791.0, 516.0); E = anchor(*E0); EC = E(*E0); EANG = 50.0
# Rev B (review item 10): heavier + slightly larger letters (Nunito 1000, em 23) with the mockup's line length (138 mm,
# OUR SPACE measured) and line pitch 28 mm (measured: k-means of the mint pixels across the line direction).
em_en = 23.0; LEN_L2 = 138.0
_l2 = KL.set_line("en", "OUR SPACE", em_en, tracking=0.0); _b = KL.ink_bounds(_l2)
trk = (LEN_L2 - (_b[2] - _b[0])) / (len("OUR SPACE") - 1)
l1 = KL.set_line("en", "KEEP CLEAN", em_en, tracking=trk); l2 = KL.set_line("en", "OUR SPACE", em_en, tracking=trk)
lh = 28.0
u = np.array([math.cos(math.radians(EANG)), math.sin(math.radians(EANG))]); n = np.array([-u[1], u[0]])
c1 = np.array(EC) + np.array([5.0, -2.5]) - n*lh/2; c2 = c1 + n*lh
L1 = KL.place(l1, *c1, EANG); L2 = KL.place(l2, *c2, EANG)
# text position traced (A14): area-weighted centroid of the mockup's mint letters (KEEP + OUR SPACE) vs ours
_cm = [c for c in TR.comps("mint", (690, 400, 890, 640)) if c["area"] > 4]
_rx = sum(c["cx"] * c["area"] for c in _cm) / sum(c["area"] for c in _cm); _ry = sum(c["cy"] * c["area"] for c in _cm) / sum(c["area"] for c in _cm)
_ours = unary_union([g for _, g in L1[:4] + L2]).centroid
_ox, _oy = E0[0] + (_ours.x - EC[0]) / S, E0[1] + (_ours.y - EC[1]) / S
EN_SHIFT = ((_rx - _ox) * S, (_ry - _oy) * S)
c1 = c1 + np.array(EN_SHIFT); c2 = c2 + np.array(EN_SHIFT)
L1 = KL.place(l1, *c1, EANG); L2 = KL.place(l2, *c2, EANG)
keep = register([(ch, g) for ch, g in L1[:4]], ref_fn_for(E0, EC, "mint"), "02"); clean = register([(ch, g) for ch, g in L1[4:]], ref_fn_for(E0, EC, "yellow"), "02")
L2 = register(L2, ref_fn_for(E0, EC, "mint"), "02")
META["badges"]["02"] = dict(anchor_px=E0, centre=EC, angle=EANG, em=em_en, pitch=lh, tracking=round(trk, 2), line2_len=LEN_L2, text="KEEP CLEAN / OUR SPACE",
                            text_shift=tuple(round(v, 1) for v in EN_SHIFT))
ecore, erim = text_regs(keep + L2, "kc_mint", "PF-TXC", "02-text", "round", rim=True)
ccore, crim = text_regs(clean, "kc_lemon", "PF-TXC", "02-text", "round", rim=True)
ref_glyphs("02", "FL", keep + L2, ["kc_mint", "kc_mint_lt"]); ref_glyphs("02", "FL", clean, ["kc_lemon", "kc_lemon_lt"])
eshape = unary_union([r["geom"] for r in ecore + erim + ccore + crim])
add("FL", KM.stipple_band(eshape, "02-glow", outer=4.5, seed=12), 20, "02", unit="02-glow")
STARS_EN = [(325, 105), (425, 130), (495, 215), (570, 300), (645, 400), (720, 495), (770, 600), (800, 840), (750, 935), (645, 985),
            (540, 910), (460, 815), (385, 720), (305, 625), (225, 530), (140, 430), (115, 310), (195, 190)]      # 18 stars (crop_en2: /4 + (670,380))
for i, (cx_, cy_) in enumerate(STARS_EN):
    px, py = 670 + cx_/4, 380 + cy_/4
    c = TR.snap("yellow", px, py); tr_log("02", "border stars", c)
    szE, rotE = star_from(c, (i*7) % 15 - 7) if c else (11.6, (i*7) % 15 - 7)
    if c: px, py = c["cx"], c["cy"]
    _pe = E(px, py)
    add("FL", best_star(lambda k, _pe=_pe, szE=szE, rotE=rotE, i=i: KM.star_facets(*_pe, szE, "kc_gold", f"02-star{i}", rot=rotE, k=k)[0], [0.42, 0.48, 0.54],
                        ref_fn_for(E0, EC, "yellow"), "02", "border star"), 30, "02", unit=f"02-star{i}")
put("FL", (ecore + ccore, erim + crim), 31, "02", "02-text")

# ================================================================ 03 CN badge  (FR, wearer's right lower front)
DOTS_CN = [  # (px, py, colour) 22 dots detected on the mockup, alternating blue / mint around the ring
    (385.4, 661.8, "b"), (338.9, 678.5, "b"), (413.4, 702.5, "b"), (330.3, 726.4, "b"), (428.0, 758.0, "b"), (339.6, 781.6, "b"),
    (441.6, 811.6, "b"), (355.7, 839.7, "b"), (451.8, 866.9, "b"), (375.2, 899.6, "b"),
    (356.4, 660.6, "m"), (403.8, 678.5, "m"), (329.9, 700.5, "m"), (422.6, 730.5, "m"), (334.5, 753.2, "m"), (435.8, 784.4, "m"),
    (348.1, 812.1, "m"), (448.2, 839.5, "m"), (363.0, 869.7, "m"), (447.5, 893.8, "m"), (425.9, 914.0, "m"), (398.7, 917.1, "m")]
C0 = (390.0, 789.0); CN_SHIFT = (14.0, 0.0)        # moved 14 mm toward CF: clears the welt box by >= 6 on every size
_C = anchor(*C0); C = lambda px, py: (_C(px, py)[0] + CN_SHIFT[0], _C(px, py)[1] + CN_SHIFT[1])
CC = C(*C0)
dpts = [C(px, py) for px, py, _ in DOTS_CN]
META["badges"]["03"] = dict(anchor_px=C0, centre=CC, shift=CN_SHIFT, text=kccore.TEXT["03"], dots=len(dpts))
dcores, drims = [], []
for i, ((px, py, k), (x, y)) in enumerate(zip(DOTS_CN, dpts)):
    c = TR.snap("blue" if k == "b" else "mint", px, py); tr_log("03", "ring dots", c)
    dd = 12.4
    if c: x, y = C(c["cx"], c["cy"]); dd = 2 * math.sqrt(c["area"] / math.pi) * S
    c_, r_ = fit_pair(KM.disc_rc(x, y, dd, "kc_blue" if k == "b" else "kc_mint", f"03-dot{i}", rim_w=1.3, ang=35 + (i * 23) % 50), ref_fn_for(C0, CC, "blue" if k == "b" else "mint"), "03", "ring dot")
    dcores += c_; drims += r_
# glow (review item 2): soft halo round every dot (mockup: green haze round the dots), one connected band
dshape = unary_union([r["geom"] for r in dcores + drims])
add("FR", KM.stipple_band(dshape, "03-glow", outer=3.6, seed=13), 20, "03", unit="03-glow")
add("FR", dcores, 30, "03", unit="03-dots"); add("FR", drims, 32, "03", unit="03-dots")
# text column: 6 glyphs between the mockup's first + last glyph centres (the AI drew 7 garbled glyphs)
t0 = C(370.0, 690.0); t1 = C(407.5, 867.5)
col_ang = math.degrees(math.atan2(t1[1] - t0[1], t1[0] - t0[0])) - 90
em_cn = 27.0
colm = KL.set_column("cn", kccore.TEXT["03"], em_cn, gap=(math.dist(t0, t1) - 5*em_cn) / 5)
mid = ((t0[0] + t1[0])/2, (t0[1] + t1[1])/2)
cn = KL.place(colm, *mid, col_ang)
META["badges"]["03"].update(em=em_cn, angle=col_ang)
# Rev D (founder 20 Oct): CN text 3D puff (Noto Sans SC 800: the mockup's strokes are as heavy; at 600 only 11 % of the
# stroke length reached the house 3.0 mm puff minimum, at 800 81 %); no lighter rim (the mockup's CN letters show none).
# Flat strokes of a puff glyph sew after the foam is torn (layer 31 = top), like JP / EN.
put("FR", text_regs(cn, "kc_red", "PF-TXC", "03-text", "flat"), 31, "03", "03-text"); ref_glyphs("03", "FR", cn, ["kc_red"])

# ================================================================ 04 KR oval  (FL, wearer's left lower front)
K0 = (723.3, 891.8); K = anchor(*K0); KC = K(*K0); KANG = 6.9
a_c, b_c, wr = 117.7*S, 30.7*S, 4.0
_rp, _rw, _rprof, _wmin, _wmax = trace_ring(ref_fn_for(K0, KC, "yellow"), *KC, a_c + wr/2, b_c + wr/2, KANG, wr)
# Rev D (founder 20 Oct): the KR oval ring is 3D puff (traced width checked against PUFF_MIN_MM below), its lemon
# highlight sews on top of the puff ring in the same foam block
_oval = [KS.column_region("kc_gold", "PF-OVAL", _rp, _rw, ("flat", "flat"), True, prof=_rprof, unit="04-oval")]
# lemon highlight: a 1.1 column just inside the ring centreline (mockup: lighter inner line)
_hl = [(KC[0] + (x - KC[0]) * (1 - 0.9 / max(1e-6, math.hypot(x - KC[0], y - KC[1]))), KC[1] + (y - KC[1]) * (1 - 0.9 / max(1e-6, math.hypot(x - KC[0], y - KC[1])))) for x, y in _rp]
_oval.append(KS.column_region("kc_lemon", "PF-OVHL", _hl, 1.1, ("flat", "flat"), True, unit="04-oval", ko=False))
META["traced"].setdefault("04", {})["oval ring width"] = (round(_wmin, 2), round(_wmax, 2))
if _wmin < kccore.PUFF_MIN_MM:
    _oval[0]["grp"] = "OVAL"; _oval[1]["grp"] = "OVAL-hl"
KM.PUFF_LOG.append(dict(unit="04-oval", ch="ring", strokes=1, puff=int(_wmin >= kccore.PUFF_MIN_MM), flat=int(_wmin < kccore.PUFF_MIN_MM), share=1.0,
                        w_min=round(_wmin, 2), w_med=round((_wmin + _wmax) / 2, 2), w_max=round(_wmax, 2), flat_w_max=None, below_house=int(_wmin < kccore.PUFF_HOUSE_MIN_MM)))
_oval = fit(_oval, ref_fn_for(K0, KC, "yellow"), "04", "oval ring", aspect=True)
add("FL", _oval, 25, "04", unit="04-oval")
add("FL", [], 27, "04")
# the reference's longer line (9 glyphs + spaces + "!") must sit inside the ring with >= 3 mm clearance: em steps down
_ovg = unary_union([r["geom"] for r in _oval]); em_kr = 19.0; trk_kr = 1.2
while True:
    kr = KL.place(KL.set_line("kr", kccore.TEXT["04"], em_kr, tracking=trk_kr), *KC, KANG)
    if unary_union([g for _, g in kr]).distance(_ovg) >= 3.0 or em_kr <= 12: break
    em_kr -= 0.5
META["badges"]["04"] = dict(anchor_px=K0, centre=KC, angle=KANG, em=em_kr, tracking=trk_kr, text=kccore.TEXT["04"], axes=(a_c + wr/2, b_c + wr/2, wr))
put("FL", text_regs(kr, "kc_white", "PF-TXC", "04-text", "flat"), 26, "04", "04-text"); ref_glyphs("04", "FL", kr, ["kc_white"])
# Review item 7 resolved by the source frame (inputs/reference.png): the render's "i-arrow mark" is the "!" of 우주! drawn
# rotated 180°, and its accent marks are parts of rotated Hangul — they are now part of the text, no separate ornaments.
META["badges"]["04"]["ornaments"] = []

# ================================================================ 05 star field
SP = json.load(open("out/ref/specks.json"))
BADGE_PX = {   # mockup zones that belong to a badge (not field stars)
    "01": Polygon([(285, 375), (540, 375), (540, 600), (285, 610)]).buffer(0),
    "02": Polygon([(690, 395), (800, 395), (885, 600), (875, 640), (795, 640), (690, 470)]).buffer(0),
    "03": None, "04": Polygon([(600, 852), (845, 852), (845, 930), (600, 930)])}
cn_ring_px = MultiPoint([(px, py) for px, py, _ in DOTS_CN]).convex_hull.buffer(-6)
zip_px = box(540, 300, 570, 1100)
SPAN = lambda ext: min(8.5, max(4.0, (ext + 1.5) * S))      # Rev B (item 9): a 1 px/mm render under-reads the thin arms
def speck_motif(s, x, y, col="kc_white", unit=None, uniform=False, fn=None):
    """ext >= 5 px: concave 4-point sparkle (two tapered columns) + soft haze under it; smaller: satin dot.
    Size traced (A14): the speck's half-max extents on the x4 upsample (kctrace), in mm at the mapping used for it."""
    ext = max(s["w"], s["h"])
    c = TR.snap("white", s["x"], s["y"], r=4.0, box_r=10) if "x" in s else None
    tr_log("05", "sparkles" if ext >= 5 else "dots", c)
    if ext >= 5:
        if c: sp = max(3.2, math.sqrt((c["ext_w"] * (S if uniform else MM.SX)) * (c["ext_h"] * (S if uniform else MM.SY))))
        else: sp = SPAN(ext)
        rot = ((x * 13 + y * 7) % 9) - 4
        st = KM.sparkle_cols(x, y, sp, col, unit, rot=rot)
        if fn is not None:
            st, i_st = fit(st, fn, "05", "sparkle", aspect=True, starts=SP_STARTS, ret_iou=True)
            if i_st < 0.78:          # the primitive does not reach the gate with margin: stitch the traced silhouette (A14)
                cxy = unary_union([r["geom"] for r in st]).centroid; tp = TR.trace_polygon(fn, cxy.x, cxy.y)
                if tp is not None and tp.area >= 1.6 and tp.distance(cxy) < 1.5:
                    tr_log("05", "traced silhouettes", True); st = [KM.R(col, tp, "satin", "auto", "DOT", unit=unit, kob=0.6)]
        x, y = unary_union([r["geom"] for r in st]).centroid.coords[0]
        return KM.haze(x, y, 0.55 * sp, unit, star=unary_union([r["geom"] for r in st])) + st
    d = {2: 1.45, 3: 1.7, 4: 2.0}.get(ext, 1.45)
    if c: d = max(1.45, 2 * math.sqrt(c["area"] / math.pi) * (S if uniform else math.sqrt(MM.SX * MM.SY)))
    dr = KM.dot(x, y, d, col, unit)
    if fn is None: return dr
    dr, i_dot = fit(dr, fn, "05", "dot", aspect=True, starts=[(0.0, 1.0), (0.0, 0.8), (0.0, 1.25)], ret_iou=True)
    if ext >= 3 and c:
        # traced shape choice: a 3-4 px speck can be a tiny 4-point star (plus) — fit both, keep the better match
        sp = max(3.0, max(c["ext_w"], c["ext_h"]) * (S if uniform else math.sqrt(MM.SX * MM.SY)))
        st, i_sp = fit(KM.sparkle_cols(x, y, sp, col, unit), fn, "05", "sparkle (small)", aspect=True, starts=SP_STARTS, ret_iou=True)
        if i_sp > i_dot + 0.03: dr, i_dot = st, i_sp
    if i_dot < 0.75:
        # neither primitive matches this tiny star: stitch its traced silhouette (A14), satin across its long axis
        cxy = unary_union([r["geom"] for r in dr]).centroid
        tp = TR.trace_polygon(fn, cxy.x, cxy.y)
        if tp is not None and tp.area >= 1.6 and tp.distance(cxy) < 1.5:
            tr_log("05", "traced silhouettes", True)
            return [KM.R(col, tp, "satin", "auto", "DOT", unit=unit, kob=0.6)]
    return dr
nfield = {"FR": 0, "FL": 0, "SR": 0, "SL": 0}; ncn = 0
# sleeve quads in the mockup (px): top fold at the shoulder, cuff outer, underarm, cuff inner
SLQ = {"SR": dict(A=(203, 428), B=(50, 1240), C=(226, 565), D=(246, 1236)),
       "SL": dict(A=(912, 428), B=(1072, 1240), C=(889, 565), D=(870, 1236))}
g_m, _ = F.pieces("M")
SLV = {P: g_m[kccore.PIECE_CODE[P]] for P in ("SR", "SL")}
def sleeve_front_x(P, y):
    """x of the FRONT underarm seam of sleeve P at pattern y (S01 right sleeve: front half x > 0; S02 mirrored)"""
    sp = SLV[P].sew_poly(); b = sp.bounds
    ln = LineString([(0, y), (b[2] + 5 if P == "SR" else b[0] - 5, y)]).intersection(sp)
    xs = [c[0] for g in getattr(ln, "geoms", [ln]) if not g.is_empty for c in g.coords]
    return (max(xs) if P == "SR" else min(xs)) if xs else 0.0
SL_TOP = {P: SLV[P].sew_poly().bounds[1] for P in SLV}; SL_BOT = {P: SLV[P].sew_poly().bounds[3] for P in SLV}
_SIL = ndi.binary_fill_holes(ndi.binary_opening(MM.mock().min(2) < 235, iterations=2))
SL_Y0, SL_Y1 = 425.0, 1180.0                      # shoulder point .. cuff SEAM (mockup px; Rev B: the cuff is its own piece)
_INNER = {"SR": ([425, 565, 1100, 1140, 1200, 1268], [203, 226, 240, 245, 221, 190]),
          "SL": ([425, 565, 1100, 1140, 1200, 1268], [912, 887, 875, 873, 898, 930])}
def sleeve_uv(P, px, py):
    """u = shoulder -> cuff, v = 0 at the outer fold (sleeve centre line) .. 1 at the underarm seam, read per mockup row:
    outer = the jacket silhouette, inner = the drop-shoulder seam / side seam."""
    y = int(min(max(py, SL_Y0), SL_Y1 - 1)); xs = np.nonzero(_SIL[y])[0]
    xo = xs.min() if P == "SR" else xs.max()
    xi = np.interp(py, *_INNER[P])
    return (py - SL_Y0) / (SL_Y1 - SL_Y0), min(1.0, max(0.0, (px - xo) / (xi - xo)))
def on_sleeve(P, px, py):
    if py < SL_Y0 or py > SL_Y1: return False
    xi = np.interp(py, *_INNER[P])
    return px < xi - 2 if P == "SR" else px > xi + 2
sleeve_mapped = {"SR": [], "SL": []}
EXCL = dict(zip=0, big_glint=0, in_badge=0, hood=0)
for i, s in enumerate(SP):
    px, py = s["x"], s["y"]; pt = Point(px, py)
    if zip_px.contains(pt): EXCL["zip"] += 1; continue
    if max(s["w"], s["h"]) > 9: EXCL["big_glint"] += 1; continue
    if any(z is not None and z.contains(pt) for z in BADGE_PX.values()): EXCL["in_badge"] += 1; continue
    if cn_ring_px.contains(pt):           # sparkles inside the CN dot ring are part of badge 03
        x, y = C(px, py); add("FR", speck_motif(s, x, y, unit=f"03-sp{ncn}", uniform=True, fn=ref_fn_for(C0, CC, "white")), 21, "03", unit=f"03-sp{ncn}"); ncn += 1; continue
    side = None
    for P in ("SR", "SL"):
        if on_sleeve(P, px, py): side = P
    if side:
        u_, v_ = sleeve_uv(side, px, py)
        y = SL_TOP[side] + u_*(SL_BOT[side] - SL_TOP[side]); x = v_*sleeve_front_x(side, y)
        sleeve_mapped[side].append((x, y, s)); continue
    if py < 300: EXCL["hood"] += 1; continue          # hood / above the neck seam (hood plain, PROPOSED)
    x, y = MM.P(px, py)
    P = "FR" if x < 0 else "FL"
    META.setdefault("field_specks", []).append(dict(P=P, px=px, py=py, x=x, y=y, unit=f"05-{P}{nfield[P]}"))
    add(P, speck_motif(s, x, y, unit=f"05-{P}{nfield[P]}", fn=ref_fn_field("white")), 21, "05", unit=f"05-{P}{nfield[P]}"); nfield[P] += 1
# sleeves: mapped front half + seeded back half at the same density and size mix
for P in ("SR", "SL"):
    sp = SLV[P].sew_poly()
    front_half = sp.intersection(box(0, -500, 600, 600) if P == "SR" else box(-600, -500, 0, 600))
    back_half = sp.difference(front_half)
    for (x, y, s) in sleeve_mapped[P]:
        add(P, speck_motif(s, x, y, unit=f"05-{P}{nfield[P]}"), 21, "05", unit=f"05-{P}{nfield[P]}"); nfield[P] += 1
    nf = len(sleeve_mapped[P]); dens = nf / max(front_half.area, 1)
    rng = random.Random(55 if P == "SR" else 66); nb = int(round(dens * back_half.area)); pts = []
    exts = [max(s["w"], s["h"]) for _, _, s in sleeve_mapped[P]] or [3]
    bb = back_half.bounds; tries = 0
    while len(pts) < nb and tries < 20000:
        tries += 1; q = (rng.uniform(bb[0], bb[2]), rng.uniform(bb[1], bb[3]))
        if not back_half.contains(Point(q)) or any(math.dist(q, p) < 9 for p in pts): continue
        pts.append(q)
    for q in pts:
        e = rng.choice(exts); s = dict(w=e, h=e)
        add(P, speck_motif(s, *q, unit=f"05-{P}{nfield[P]}"), 21, "05", unit=f"05-{P}{nfield[P]}"); nfield[P] += 1
    META["counts"][P + "_front_mapped"] = nf; META["counts"][P + "_back_seeded"] = len(pts)
META["counts"].update({k + "_field": v for k, v in nfield.items()}, cn_sparkles=ncn, specks_detected=len(SP), **{"excluded_" + k: v for k, v in EXCL.items()})
META["counts"]["glints"] = json.load(open("out/ref/specks_glints.json"))
spans = [SPAN(max(s["w"], s["h"])) for s in SP if 5 <= max(s["w"], s["h"]) <= 9]
META["counts"]["sparkle_spans"] = dict(n=len(spans), lt5=sum(1 for v in spans if v < 5), s5_8=sum(1 for v in spans if 5 <= v <= 8), gt8=sum(1 for v in spans if v > 8))
META["S"] = S; META["SX"] = MM.SX; META["SY"] = MM.SY
META["puff"] = KM.PUFF_LOG
pickle.dump(dict(items=items, meta=META), open("scene.pkl", "wb"))
print({P: len(v) for P, v in items.items()}, META["counts"])
