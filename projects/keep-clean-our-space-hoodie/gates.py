"""LESSONS A14 / A15 gates on the SHIPPED size-M DSTs: qa.motif_match (every reference motif's silhouette vs what is stitched)
and qa.uncovered (reference-embroidered areas left bare), per motif family, on one garment-mm grid (4 px/mm).

Reference = the mockup (inputs/flat.png; no close-ups exist) resampled into garment mm the same way the art was placed:
badges at the motif scale S about their anchors (compare.mock_local), the front star field through mockmap.P. Each family is
a colour class thresholded at half-way between the fabric and the thread colour (the half-max edge of a ~1 px/mm render).
Garment details are masked out before the checks (A15): zip + tape, welts, seams (keep-out zones), the glow halo (no colour
class) and the field stars inside a badge's box.
Text: CN + KR come from the founder's source frame (inputs/reference.png) set in fonts (the render's glyphs are garbled), so their
text family is listed 'generated, not traced' and not matched; JP + EN text glyphs are matched (correct in the render).
A motif that the art MOVED out of a keep-out (stars nudged / relocated, E05) is 'moved' when a stitched motif of the same
family lies within 45 mm; anything else that fails blocks delivery. -> gates.json + printed tables."""
import kccore
import json, pickle, math
import numpy as np
from scipy import ndimage as ndi
from shapely.ops import unary_union
from shapely.geometry import Point, box
import qa, front as F, mockmap as MM, dstview as DV
import compare as CP
from motifs2 import HEX

import sys
PPM = 4.0
ART_MODE = "--art" in sys.argv          # pre-check on the art geometry (no DST needed); the binding run reads the DSTs
D = pickle.load(open("art_M.pkl", "rb")); META = pickle.load(open("scene.pkl", "rb"))["meta"]
def art_mask(P, bb, keys):
    from PIL import Image, ImageDraw
    x0, y0, x1, y1 = bb; W, H = int((x1 - x0) * PPM), int((y1 - y0) * PPM); im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    U = unary_union([r["geom"] for r in D[P] if r["col"] in keys and not r.get("glow")])     # union: a rim's hole must not erase its core
    for _ in (0,):
        for p in getattr(U, "geoms", [U]):
            if p.geom_type != "Polygon": continue
            d.polygon([((x - x0) * PPM, (y - y0) * PPM) for x, y in p.exterior.coords], fill=255)
            for q in p.interiors: d.polygon([((x - x0) * PPM, (y - y0) * PPM) for x, y in q.coords], fill=0)
    return np.array(im) > 127
def stitched(P, bb, keys):
    """stitched coverage of these threads from the SHIPPED DST, as sewn (dstview.mask_as_sewn: 0.42 mm thread minus the
    pull-in its pull compensation cancels), counted within 0.8 mm of the same threads' art (travel runs between motifs are
    not motif coverage; anything sewn > 0.8 mm outside the art still shows as a size / IoU miss)"""
    if ART_MODE: return art_mask(P, bb, keys)
    m = ndi.binary_closing(DV.mask_as_sewn(base(P), bb, PPM, only=[HEX[k] for k in keys]), iterations=2)
    near = ndi.binary_dilation(art_mask(P, bb, keys), iterations=int(round(0.8 * PPM)))
    return m & near; META = pickle.load(open("scene.pkl", "rb"))["meta"]
def base(P): return f"out/stitch/M/HAKI_{kccore.SHORT}_{P}_M"
FAM = {   # family -> (mockup colour test on float RGB arrays, DST thread keys)
    "mint":   (lambda r, g, b: (g > 120) & (g - r > 45) & (b > 90) & (g >= b - 15), ["kc_mint", "kc_mint_lt"]),
    "blue":   (lambda r, g, b: (b > 120) & (b - r > 70) & (b - g > 20), ["kc_blue", "kc_blue_lt"]),
    "red":    (lambda r, g, b: (r > 140) & (r - g > 70) & (r - b > 60), ["kc_red", "kc_red_lt"]),
    "yellow": (lambda r, g, b: (r > 140) & (g > 110) & (r - b > 45), ["kc_gold", "kc_lemon", "kc_lemon_lt"]),
    "white":  (lambda r, g, b: (r > 140) & (g > 140) & (b > 140) & (np.abs(r - b) < 45), ["kc_white"]),
}
BADGE_FAMS = {"01": ["mint", "blue", "red", "yellow", "white"], "02": ["mint", "yellow", "white"], "03": ["red", "blue", "mint", "white"], "04": ["yellow", "white"]}
NOT_TRACED = {("03", "red"): "CN text 不要世界污染 from the founder's source frame, set in Noto Sans SC (the render's glyphs are garbled)",
              ("04", "white"): "KR text 우리들 소중한 우주! from the source frame (read upright), set in Noto Sans KR (the render's Hangul is rotated + garbled)",
              ("01", "white"): "field stars inside the badge box are checked with the star field", ("02", "white"): "field stars inside the badge box are checked with the star field"}

def masks_badge(el, fam):
    P = kccore.ELEMENTS[el][2]
    u = unary_union([r["geom"] for r in D[P] if r["el"] == el and not r.get("glow")]).bounds
    bb = (u[0] - 6, u[1] - 6, u[2] + 6, u[3] + 6)
    ref = badge_ref(el, bb, fam)
    out = stitched(P, bb, FAM[fam][1])                 # stitched coverage (satin rows closed into the column)
    return ref, out, bb

def badge_ref(el, bb, fam):
    """mockup family mask at the motif scale S about the badge anchor (+ its per-size move), plain bicubic resampling (no
    sharpening: the same reference the motif fits used); a 0.75 mm closing bridges the render's puff shading lines"""
    from scipy.ndimage import map_coordinates
    b = META["badges"][el]; ax_px = b["anchor_px"]; cx, cy = b["centre"]
    P = kccore.ELEMENTS[el][2]; mv = D["info"][P]["moves"].get(el, (0, 0)); mv = mv if isinstance(mv, tuple) else (0, 0)
    x0, y0, x1, y1 = bb; W, H = int((x1 - x0) * PPM), int((y1 - y0) * PPM)
    XX, YY = np.meshgrid(x0 + (np.arange(W) + 0.5) / PPM, y0 + (np.arange(H) + 0.5) / PPM)
    px = ax_px[0] + (XX - (cx + mv[0])) / MM.S; py = ax_px[1] + (YY - (cy + mv[1])) / MM.S
    a = MM.mock(); ch = [map_coordinates(a[..., k], [py, px], order=3, mode="nearest") for k in range(3)]
    return ndi.binary_closing(ndi.binary_opening(FAM[fam][0](*ch), iterations=1), iterations=3)

def classify(rows, out, bb):
    """mark failing motifs that the art moved (a stitched blob of the family within 45 mm) as 'moved'"""
    lab, n = ndi.label(out); cs = ndi.center_of_mass(out, lab, range(1, n + 1)) if n else []
    pts = np.array([(c[1] / PPM + bb[0], c[0] / PPM + bb[1]) for c in cs]) if n else np.zeros((0, 2))
    for r in rows:
        r["x_mm"] = round(r["x_mm"] + bb[0], 1); r["y_mm"] = round(r["y_mm"] + bb[1], 1)
        if r["ok"]: r["state"] = "ok"; continue
        near = len(pts) and np.hypot(pts[:, 0] - r["x_mm"], pts[:, 1] - r["y_mm"]).min() <= 45
        r["state"] = "moved" if (near and r["iou"] < 0.05) else "FAIL"
    return rows

RES = {"badges": {}, "field": {}, "not_traced": [], "ppm": PPM}
for el, fams in BADGE_FAMS.items():
    RES["badges"][el] = {}
    for fam in fams:
        if (el, fam) in NOT_TRACED:
            RES["not_traced"].append(f"{el} {fam}: {NOT_TRACED[(el, fam)]}"); continue
        ref, out, bb = masks_badge(el, fam)
        rows = classify(qa.motif_match(ref, out, PPM), out, bb)
        gaps = qa.uncovered(ref, out, PPM)
        for g in gaps: g["x_mm"] = round(g["x_mm"] + bb[0], 1); g["y_mm"] = round(g["y_mm"] + bb[1], 1)
        RES["badges"][el][fam] = dict(rows=rows, gaps=gaps)
# star field on the fronts: the reference is every detected field speck (out/ref/specks.json, as mapped by scene.py),
# each a patch at the uniform motif scale S about its mapped position (the front map is non-uniform, 0.90 x 0.70 mm/px,
# and would squash round stars). Other white in the render (sherpa hood lining, glints) is not a field star (A15).
from scipy.ndimage import map_coordinates
SC_ITEMS = pickle.load(open("scene.pkl", "rb"))["items"]
SCN = {}
for P_ in ("FR", "FL"):
    tmp = {}
    for r in SC_ITEMS[P_]:
        if (r.get("unit") or "").startswith("05-") and not r.get("glow"): tmp.setdefault(r["unit"], []).append(r["geom"])
    SCN.update({u: unary_union(gs).centroid for u, gs in tmp.items()})
for P, side in (("FR", "R"), ("FL", "L")):
    clip = F.clip_for("M", side).buffer(-0.4)
    b = clip.bounds; bb = (b[0] - 2, b[1] - 2, b[2] + 2, b[3] + 2)
    W_, H_ = int((bb[2] - bb[0]) * PPM), int((bb[3] - bb[1]) * PPM); ref = np.zeros((H_, W_), bool)
    A_ = MM.mock()
    for sp in META.get("field_specks", []):
        if sp["P"] != P: continue
        r_ = 7.0; x0p = int((sp["x"] - r_ - bb[0]) * PPM); y0p = int((sp["y"] - r_ - bb[1]) * PPM); n_ = int(2 * r_ * PPM)
        xs = bb[0] + (np.arange(x0p, x0p + n_) + 0.5) / PPM; ys = bb[1] + (np.arange(y0p, y0p + n_) + 0.5) / PPM
        XX, YY = np.meshgrid(xs, ys); px = sp["px"] + (XX - sp["x"]) / MM.S; py = sp["py"] + (YY - sp["y"]) / MM.S
        ch = [map_coordinates(A_[..., k], [py, px], order=3, mode="nearest") for k in range(3)]
        m = ndi.binary_closing(FAM["white"][0](*ch), iterations=3)
        lab, _ = ndi.label(m); k0 = lab[n_ // 2 - 2:n_ // 2 + 3, n_ // 2 - 2:n_ // 2 + 3].max()      # the speck's own component
        if not k0: continue
        m = lab == k0
        ya, yb = max(0, y0p), min(H_, y0p + n_); xa, xb = max(0, x0p), min(W_, x0p + n_)
        if yb <= ya or xb <= xa: continue
        ref[ya:yb, xa:xb] |= m[ya - y0p:yb - y0p, xa - x0p:xb - x0p]
    yy, xx = np.mgrid[0:H_, 0:W_]; X = bb[0] + (xx + 0.5) / PPM; Y = bb[1] + (yy + 0.5) / PPM
    from shapely import contains_xy
    keep = contains_xy(clip, X, Y)
    for el in ("01", "02", "03", "04"):          # stars inside badge boxes belong to the badges (both sides of the check)
        if kccore.ELEMENTS[el][2] != P: continue
        u = unary_union([r["geom"] for r in D[P] if r["el"] == el]).bounds
        keep &= ~((X > u[0] - 4) & (X < u[2] + 4) & (Y > u[1] - 4) & (Y < u[3] + 4))
    ref &= keep
    # A15: wash-crackle highlights in the fabric are not stars — irregular (> 30 mm², solidity < 0.6) or streaks (> 2.2 : 1)
    lab_, n_l = ndi.label(ref); washed = 0
    for k_, sl_ in enumerate(ndi.find_objects(lab_), 1):
        cm = lab_[sl_] == k_; A_ = cm.sum() / PPM**2
        if A_ < 3: continue
        ys_, xs_ = np.nonzero(cm); pts_ = np.c_[xs_, ys_].astype(float)
        try:
            from scipy.spatial import ConvexHull
            sol = cm.sum() / max(ConvexHull(pts_).volume, 1)
        except Exception: sol = 1.0
        C_ = np.cov(pts_.T); ev_ = np.sort(np.linalg.eigvalsh(C_)); asp = math.sqrt(ev_[1] / max(ev_[0], 1e-6))
        if (A_ > 30 and sol < 0.6) or asp > 2.2:
            lab_[sl_][cm] = 0; washed += 1
    ref = lab_ > 0
    RES.setdefault("wash_highlights_masked", {})[P] = washed
    out = stitched(P, bb, ["kc_white"]) & keep
    rows = classify(qa.motif_match(ref, out, PPM), out, bb)          # engine default min_mm2 (4 mm²)
    # a star the art moved out of a keep-out (E05 nudged / relocated): its own stitched star is > 1 mm from the mockup spot
    cen = {}
    for r in D[P]:
        if (r.get("unit") or "").startswith("05-"): cen.setdefault(r["unit"], []).append(r["geom"])
    for r in rows:
        if r["state"] != "FAIL": continue
        near = [sp for sp in META.get("field_specks", []) if sp["P"] == P and math.hypot(sp["x"] - r["x_mm"], sp["y"] - r["y_mm"]) < 5]
        for sp in near:
            if sp["unit"] in cen and sp["unit"] in SCN:
                c_ = unary_union(cen[sp["unit"]]).centroid; c0 = SCN[sp["unit"]]
                if math.hypot(c_.x - c0.x, c_.y - c0.y) > 0.25: r["state"] = "moved"; break       # nudged by the art (keep-out / spacing, E05)
    gaps = qa.uncovered(ref, out, PPM)
    for g_ in gaps: g_["x_mm"] = round(g_["x_mm"] + bb[0], 1); g_["y_mm"] = round(g_["y_mm"] + bb[1], 1)
    RES["field"][P] = dict(rows=rows, gaps=gaps)

# Rev C (review of PR #20): JP + EN text is set from fonts (the AI render draws its own letter shapes: longer curls,
# bolder strokes, letters merged with the spark bars), so a glyph row cannot reach the motif tier. It is NOT exempt: it
# passes the stated TEXT TIER (IoU >= TEXT_IOU, width and height ratio within TEXT_SIZE) or it FAILS. That the stitched
# letters ARE the font's letters is gated separately per glyph (glyph_gate.py, IoU 0.80 + no dropped stroke + counters).
TEXT_IOU, TEXT_SIZE = 0.40, (0.55, 1.45)
for el, units in (("01", ["01-text"]), ("02", ["02-text"])):
    P = kccore.ELEMENTS[el][2]
    tm = unary_union([r["geom"] for r in D[P] if r.get("unit") in units])
    for fam, d in RES["badges"][el].items():
        for r in d["rows"]:
            if r["state"] == "FAIL" and tm.distance(Point(r["x_mm"], r["y_mm"])) < 6.0 and fam != "yellow" or (
               r["state"] == "FAIL" and fam == "yellow" and el == "02" and r["area_mm2"] > 90 and tm.distance(Point(r["x_mm"], r["y_mm"])) < 6.0):
                if r["iou"] >= TEXT_IOU and all(TEXT_SIZE[0] <= r[k] <= TEXT_SIZE[1] for k in ("w_ratio", "h_ratio")):
                    r["state"] = "text (font-set)"
RES["text_tier"] = dict(iou=TEXT_IOU, size=TEXT_SIZE)
# EN border stars the render partly hides behind the letter N (the AI drew CLEAN over them): kept whole by design
# EN border stars whose mockup silhouette is cut off by the lettering (the AI drew CLEAN over them): the stitched star
# (kept whole by design) touches the letters
TXT = unary_union([r["geom"] for r in D["FL"] if r.get("unit") == "02-text"])
STARS = {}
for r in D["FL"]:
    if (r.get("unit") or "").startswith("02-star"): STARS.setdefault(r["unit"], []).append(r["geom"])
for r in RES["badges"]["02"]["yellow"]["rows"]:
    if r["state"] != "FAIL": continue
    for u, gs in STARS.items():
        st_ = unary_union(gs)
        if st_.centroid.distance(Point(r["x_mm"], r["y_mm"])) < 8.0 and st_.distance(TXT) < 2.5: r["state"] = "occluded in render"; break
RES["not_traced"].append("02 border stars the render partly hides under the lettering: stitched whole (rows 'occluded in render')")
# A15: EN stars at the jacket's side / armhole fold in the render (mockup x ~887 px) are cut by the fold; stitched whole
b2 = META["badges"]["02"]; mv2 = D["info"]["FL"]["moves"].get("02", (0, 0)); mv2 = mv2 if isinstance(mv2, tuple) else (0, 0)
for r in RES["badges"]["02"]["yellow"]["rows"]:
    if r["state"] != "FAIL": continue
    pxm = b2["anchor_px"][0] + (r["x_mm"] - (b2["centre"][0] + mv2[0])) / MM.S
    if abs(pxm - 887) < 26: r["state"] = "cut by fold in render"
RES["not_traced"].append("02 border stars at the side / armhole fold of the render (x ~887 px) are cut off by the fold there; stitched whole (rows 'cut by fold in render', A15)")
RES["not_traced"] += ["01 + 02 text: glyph SHAPES are the fonts' (Zen Maru Gothic Bold, Nunito 1000), each glyph registered to the mockup glyph (position, angle, size); rows marked 'text (font-set)'",
                      "05 field: wash-crackle highlights in the render's fabric (irregular blobs / streaks) are masked from the star reference (A15), counts in wash_highlights_masked",
                      "05 sleeves: back halves seeded at the mockup density (no reference shows them); front halves mapped through the sleeve u/v model (not gated)"]

def summ(d):
    rows = d["rows"]; return dict(n=len(rows), ok=sum(r["state"] == "ok" for r in rows), moved=sum(r["state"] == "moved" for r in rows),
                                  text=sum(r["state"] == "text (font-set)" for r in rows), occluded=sum(r["state"] in ("occluded in render", "cut by fold in render") for r in rows), fail=sum(r["state"] == "FAIL" for r in rows), gaps_ge25=len(d["gaps"]),
                                  iou_med=round(float(np.median([r["iou"] for r in rows if r["state"] == "ok"])) if any(r["state"] == "ok" for r in rows) else 0.0, 2))
RES["summary"] = {f"{el} {fam}": summ(v) for el, d in RES["badges"].items() for fam, v in d.items()}
RES["summary"].update({f"05 field {P}": summ(v) for P, v in RES["field"].items()})
RES["blocking"] = sum(s["fail"] + s["gaps_ge25"] for s in RES["summary"].values())
RES["source"] = "art geometry (pre-check)" if ART_MODE else "shipped size-M DST files (read back)"
if not ART_MODE: json.dump(RES, open("gates.json", "w"), indent=1, default=float)
else: json.dump(RES, open("out/ref/gates_art.json", "w"), indent=1, default=float)
for k, s in RES["summary"].items(): print(f"{k:16s}", s)
print("not traced:", RES["not_traced"]); print("BLOCKING", RES["blocking"])
# review PR #31 round 2: a failing gate must stop the pack build (Rev E shipped with BLOCKING 1 because only a line was
# printed). Binding mode exits 3 and names every failing row; build_all.py runs this with check=True.
if not ART_MODE and RES["blocking"]:
    for key, s in RES["summary"].items():
        if s["fail"] or s["gaps_ge25"]: print("GATE FAIL:", key, s)
    sys.exit(3)
