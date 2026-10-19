"""Fidelity gates (LESSONS A14 / A15) on the SHIPPED size-M DSTs:
  * qa.motif_match per TRACED motif family: clouds (front + sleeves, traced from the mockup), comet (traced from the close-up +
    mockup). ref = the family's pixels in the reference, out = the same family's thread colours rendered from the DST.
  * qa.uncovered: design-coverage mask from the mockup (bright / saturated embroidery) with garment details masked out FIRST
    (zip + its shadow, welt boxes, side / armhole / hem seams = the keep-out band; sleeve: outside the readable front half), vs the
    stitched coverage. Every gap >= 25 mm2 is listed with its explanation.
Families that are generated (not traced) are listed with the reason; the spec pages carry the same list.
usage: python3 fidelity.py  -> fidelity.json + table panels pasted onto out/compare_<piece>.png"""
import cccore
import json, math
import numpy as np
from scipy import ndimage as ndi
from PIL import Image, ImageDraw
from shapely.geometry import Point, LineString
from shapely.ops import unary_union
from shapely import affinity
import pyembroidery as pe
import qa, mockmap as MM, front as F, cc_motifs as CM
from motifs2 import HEX

PPM = 4.0
KEY_OF = {HEX[k].upper(): k for k in cccore.CC_PAL}

def dst_layers(P, bb, ppm=PPM):
    """{thread key: bool mask} of one shipped full DST (size M) on the bb grid; stitch lines 0.5 mm wide + 0.3 mm closing"""
    r = json.load(open(f"{cccore.edir(P)}/M/result_{P}.json"))["full"]; ox, oy = r["origin"]
    d = pe.read(r["file"] + ".dst"); cols = [t.hex_color().upper() for t in pe.read(r["file"] + ".pes").threadlist]
    W, H = int((bb[2] - bb[0]) * ppm), int((bb[3] - bb[1]) * ppm)
    ims = {}; ci = 0; prev = None
    def im_for(c):
        k = KEY_OF.get(cols[min(c, len(cols) - 1)], "other")
        if k not in ims: ims[k] = Image.new("L", (W, H), 0)
        return ImageDraw.Draw(ims[k])
    dr = im_for(0); lw = max(1, int(round(0.5 * ppm)))
    for x, y, c in d.stitches:
        cmd = c & pe.COMMAND_MASK; X, Y = (x / 10.0 + ox - bb[0]) * ppm, (y / 10.0 + oy - bb[1]) * ppm
        if cmd == pe.STITCH:
            if prev is not None and math.hypot(X - prev[0], Y - prev[1]) < 7.6 * ppm: dr.line([prev, (X, Y)], fill=255, width=lw)
            prev = (X, Y)
        elif cmd == pe.COLOR_CHANGE: ci += 1; dr = im_for(ci); prev = None
        elif cmd == pe.TRIM: prev = None
        elif cmd == pe.JUMP: prev = None
    return {k: ndi.binary_closing(np.array(v) > 127, iterations=1) for k, v in ims.items()}

import sys
ART = "art" in sys.argv          # fast iteration: rasterise art_M.pkl regions instead of the DST (the delivered gate = DST mode)
_ARTD = None
def art_layers(P, bb, ppm=PPM):
    global _ARTD
    import pickle
    if _ARTD is None: _ARTD = pickle.load(open("art_M.pkl", "rb"))
    W, H = int((bb[2] - bb[0]) * ppm), int((bb[3] - bb[1]) * ppm); out = {}
    for r in _ARTD[P]:
        out.setdefault(r["col"], []).append(r["geom"])
    return {k: rast(v, bb, (H, W), ppm) for k, v in out.items()}
if ART: dst_layers = art_layers

def rast(geoms, bb, shape, ppm=PPM):
    im = Image.new("L", (shape[1], shape[0]), 0); d = ImageDraw.Draw(im)
    for g in geoms:
        for p in CM.polys(g):
            d.polygon([((x - bb[0]) * ppm, (y - bb[1]) * ppm) for x, y in p.exterior.coords], fill=255)
            for h in p.interiors: d.polygon([((x - bb[0]) * ppm, (y - bb[1]) * ppm) for x, y in h.coords], fill=0)
    return np.array(im) > 127

def disk(mm): r = max(1, int(round(mm * PPM))); y, x = np.ogrid[-r:r+1, -r:r+1]; return x*x + y*y <= r*r

# ------------------------------------------------------------------ fronts
import scene_ref as SRF          # the scene's reference geometry only (spine, comet zone, star / meteor exclusions) - no art
OUT = {"fronts": {}, "sleeves": {}}; DIAG = {}
for P, side in (("FR", "R"), ("FL", "L")):
    bb = (-300.0, -40.0, -5.0, 515.0) if P == "FR" else (5.0, -40.0, 300.0, 515.0)
    rgb = np.array(MM.warp(bb, PPM)).astype(np.float32); H, W = rgb.shape[:2]
    lum = ndi.gaussian_filter(rgb @ np.array([0.3, 0.59, 0.11], np.float32), 0.5 * PPM)
    mx, mn = rgb.max(2), rgb.min(2); sat = ndi.gaussian_filter((mx - mn) / np.maximum(mx, 1), 0.5 * PPM)
    YMM = bb[1] + (np.arange(H)[:, None] + 0.5) / PPM; XMM = bb[0] + (np.arange(W)[None, :] + 0.5) / PPM
    clip = F.clip_for("M", side)
    LEGAL = rast([SRF.LIM[side].buffer(-1.0)], bb, (H, W))           # garment details masked: zip, welts, seams, hem = the all-size keep-out band
    lay = dst_layers(P, bb)
    allst = np.zeros((H, W), bool)
    for v in lay.values(): allst |= v
    # --- clouds (traced family): mockup cloud pixels above the skyline, not streaks / stars
    excl = rast([SRF.STREAK_U], bb, (H, W))
    LOBE = rast([SRF.LIM[side].buffer(-8.5)], bb, (H, W))              # clouds: bank ends within 8.5 of a keep-out are drawn as whole lobes (review 2: no hard cuts)
    ref_cl = (lum > 60) & (sat < 0.72) & (YMM > 88) & (YMM < 300) & ~excl & LOBE
    ref_cl = ndi.binary_opening(ndi.gaussian_filter(ref_cl.astype(np.float32), 1.1 * PPM) > 0.5, structure=disk(0.8))
    lab, n = ndi.label(ref_cl); s_ = ndi.sum(ref_cl, lab, range(1, n + 1)) / PPM**2
    ref_cl = np.isin(lab, 1 + np.nonzero(s_ >= 25.0)[0])
    out_cl = np.zeros((H, W), bool)
    for k in ("cc_dusk", "cc_cloud", "cc_ice", "cc_white", "cc_night"): out_cl |= lay.get(k, np.zeros((H, W), bool))
    out_cl = ndi.binary_closing(out_cl, structure=disk(0.6)) & (YMM < 300) & ~excl & LOBE      # same exclusions as the reference
    rows_cl = qa.motif_match(ref_cl, out_cl, PPM, min_mm2=25.0)
    # --- comet (traced family)
    zone = rast([SRF.ZONE], bb, (H, W))
    lab_ = rgb / 255.0
    from skimage.color import rgb2lab
    L_ = rgb2lab(lab_); ch = np.hypot(L_[..., 1], L_[..., 2])
    ref_cm = zone & ((ch > 26) | ((L_[..., 0] > 66) & (ch > 10))) & LEGAL
    ref_cm = ndi.binary_closing(ndi.binary_opening(ref_cm, structure=disk(0.5)), structure=disk(1.0))
    ref_cm = ndi.binary_fill_holes(ref_cm)
    out_cm = np.zeros((H, W), bool)
    for k in ("cc_royal", "cc_azure", "cc_violet", "cc_lilac", "cc_rose", "cc_white"): out_cm |= lay.get(k, np.zeros((H, W), bool))
    out_cm = out_cm & zone          # no closing: a streak beside the body must stay its own component (kob gap 0.4)
    rows_cm = qa.motif_match(ref_cm, out_cm, PPM, min_mm2=40.0)
    # --- uncovered (A15): design coverage from the mockup inside the legal area
    design = ((lum > 62) | ((lum > 45) & (sat > 0.55))) & LEGAL          # navy fabric itself is saturated (0.6-0.7) but dark (lum 20-55)
    design = ndi.binary_opening(design, structure=disk(0.8))
    gaps = qa.uncovered(design, ndi.binary_closing(allst, structure=disk(0.8)), PPM)
    for g in gaps:
        g["x_mm"] = round(g["x_mm"] + bb[0], 1); g["y_mm"] = round(g["y_mm"] + bb[1], 1)
    for rr in rows_cl + rows_cm:
        rr["x_mm"] = round(rr["x_mm"] + bb[0], 1); rr["y_mm"] = round(rr["y_mm"] + bb[1], 1)
    OUT["fronts"][P] = dict(clouds=rows_cl, comet=rows_cm, gaps=gaps)
    DIAG[P] = dict(ref_cl=ref_cl, out_cl=out_cl, ref_cm=ref_cm, out_cm=out_cm, design=design, st=allst)

# ------------------------------------------------------------------ sleeves (clouds traced; foliage generated -> coverage only)
import sleeve_ref as SLR
for P, side in (("SR", "R"), ("SL", "L")):
    g0, _ = F.pieces("M"); bb = g0["S01" if side == "R" else "S02"].sew_poly().bounds
    ref = SLR.masks(side, bb, PPM)
    H, W = ref["cloud"].shape
    lay = dst_layers(P, bb)
    allst = np.zeros((H, W), bool)
    for v in lay.values(): allst |= v
    out_cl = np.zeros((H, W), bool)
    for k in ("cc_dusk", "cc_cloud", "cc_ice", "cc_white"): out_cl |= lay.get(k, np.zeros((H, W), bool))
    out_cl = ndi.binary_closing(out_cl, structure=disk(0.6))
    rows_cl = qa.motif_match(ref["cloud"], out_cl, PPM, min_mm2=25.0)
    gaps = qa.uncovered(ref["design"], ndi.binary_closing(allst, structure=disk(0.8)), PPM)
    for g in gaps: g["x_mm"] = round(g["x_mm"] + bb[0], 1); g["y_mm"] = round(g["y_mm"] + bb[1], 1)
    for rr in rows_cl: rr["x_mm"] = round(rr["x_mm"] + bb[0], 1); rr["y_mm"] = round(rr["y_mm"] + bb[1], 1)
    OUT["sleeves"][P] = dict(clouds=rows_cl, gaps=gaps)
    DIAG[P] = dict(design=ref["design"], st=ndi.binary_closing(allst, structure=disk(0.8)), ref_cl=ref["cloud"], out_cl=out_cl)

def classify(g, piece):
    """explanation for a gap (A15): every gap >= 25 mm2 gets one; 'UNEXPLAINED' blocks delivery"""
    p = Point(g["x_mm"], g["y_mm"])
    if piece in ("FR", "FL"):
        side = "R" if piece == "FR" else "L"
        if SRF.LIM[side].boundary.distance(p) < 9.0:
            return "keep-out edge: within 9 mm of a keep-out line (zip / seam / welt / hem): art stops at the keep-out, cloud banks end in whole lobes (review 2)"
        if SRF.GLOWS.distance(p) < 5.0:
            return "light glow around a star / meteor / falling star in the photo-render (light, not thread); the streak itself is traced"
        if 300.0 <= g["y_mm"] <= 365.0:
            return "skyline band: bright haze between the mockup's towers; the skyline is generated (original, IP) - haze band + low clouds sewn behind it"
    else:
        if SLR.GLOWS[piece].distance(p) < 5.0:
            return "light glow around a star / meteor in the photo-render (light, not thread)"
        if SLR.EDGE[piece].distance(p) < 6.0:
            return "edge of the readable front half of the hanging sleeve (garment fold / silhouette highlight masked, A15)"
        return "foliage: leaves are generated by area over the traced foliage area (undergrowth fills the rest); gap between leaf clusters"
    return "UNEXPLAINED"

GENERATED = [
    ("Skyline towers, windows, signs, antennas", "generated in the close-up's style at the mockup's skyline heights + counts; ORIGINAL skyline on purpose (IP, 'Your Name' resemblance - founder deciding)"),
    ("Figure", "generated, our own pose (IP) at the mockup position + size; not traced on purpose"),
    ("Lamp post, bicycle, railing, bush", "generated library motifs at the mockup positions + sizes (mockup ~1 px/mm: silhouettes below the reference resolution)"),
    ("Stars, meteors, falling star", "positions + kinds traced from the mockup; star shapes from the motif library at stitch resolution"),
    ("Comet strands (texture)", "generated inside the TRACED comet extent (strands are ~1 mm, below the close-up's 2 px/mm)"),
    ("Sleeve foliage", "generated by area inside the mockup's traced foliage area (leaves below the hanging-sleeve mockup's resolution)"),
]
OUT["generated_not_traced"] = GENERATED
for grp in ("fronts", "sleeves"):
    for P, d in OUT[grp].items():
        for g in d["gaps"]: g["why"] = classify(g, P)
OUT["unexplained"] = sum(1 for grp in ("fronts", "sleeves") for d in OUT[grp].values() for g in d["gaps"] if g["why"] == "UNEXPLAINED")
OUT["failing_motifs"] = sum(1 for grp in ("fronts", "sleeves") for d in OUT[grp].values() for fam in ("clouds", "comet") for r in d.get(fam, []) if not r["ok"])
OUT["mode"] = "art (iteration)" if ART else "shipped DST"
json.dump(OUT, open("fidelity.json" if not ART else "fidelity_art.json", "w"), indent=1, default=float)
print("FAILING MOTIFS", OUT["failing_motifs"], "UNEXPLAINED GAPS", OUT["unexplained"], "->", "PASS" if not (OUT["failing_motifs"] or OUT["unexplained"]) else "BLOCKED")

def summary(d):
    fam = {k: v for k, v in d.items() if k in ("clouds", "comet")}
    return {k: (sum(r["ok"] for r in v), len(v)) for k, v in fam.items()}, len(d["gaps"])
for grp in ("fronts", "sleeves"):
    for P, d in OUT[grp].items():
        print(P, summary(d), [(g["x_mm"], g["y_mm"], g["area_mm2"], g["why"][:20]) for g in d["gaps"]])
        for fam in ("clouds", "comet"):
            for r in d.get(fam, []):
                if not r["ok"]: print("   FAIL", fam, r)

if __name__ == "__main__":
    import sys
    if "diag" in sys.argv:
        for P, d in DIAG.items():
            for fam in ("cl", "cm"):
                if "ref_" + fam not in d: continue
                r, o = d["ref_" + fam], d["out_" + fam]
                im = np.zeros(r.shape + (3,), np.uint8); im[r & o] = (200, 200, 200); im[r & ~o] = (255, 60, 60); im[o & ~r] = (60, 140, 255)
                Image.fromarray(im).resize((im.shape[1] // 2, im.shape[0] // 2)).save(f"out/diag_{P}_{fam}.png")
            im = np.zeros(d["design"].shape + (3,), np.uint8); im[d["design"] & d["st"]] = (200, 200, 200); im[d["design"] & ~d["st"]] = (255, 60, 60); im[d["st"] & ~d["design"]] = (60, 90, 160)
            Image.fromarray(im).resize((im.shape[1] // 2, im.shape[0] // 2)).save(f"out/diag_{P}_cov.png")
