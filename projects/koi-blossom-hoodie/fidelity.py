"""LESSONS A14/A15 gates on the shipped size-M DSTs: qa.motif_match per motif family + qa.uncovered, every piece.
Families: floating petals + lily/leaf clusters (reference = the mockup's embroidery pixels, garment details masked out
first: welt boxes, zip, seams, hem band, everything outside the art keep-outs, and the mockup koi, which the founder
replaced by tetras); fish (reference = the COMPOSED target: reference_fish.png proportions at the mockup positions,
i.e. the art's fish regions). Out masks are drawn from the DST read-back, split by what each colour stop sews
(result json per_stop codes: FI-* = fish, everything else = flora).
Output: out/fidelity_M.json + out/fidelity_<piece>.png (masks) — tables printed on the compare sheets.
usage: python3 fidelity.py"""
import kbcore, json, pickle, math, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from shapely.geometry import LineString, Point
from shapely.ops import unary_union
import pyembroidery as pe
import qa, mockmap as MM, front as F, mockref as MR

SIZE = "M"; PPM = MR.PPM
g, mt = F.pieces(SIZE)
BB = {"FR": (-300, -60, 0, 520), "FL": (0, -60, 300, 520), "SR": (-10, -110, 260, 470), "SL": (-260, -110, 10, 470)}
META = pickle.load(open("scene.pkl", "rb"))["meta"]; ART = pickle.load(open(f"art_{SIZE}.pkl", "rb"))

def grid(bb): return int((bb[3] - bb[1]) * PPM), int((bb[2] - bb[0]) * PPM)

def raster(geoms, bb):
    H, W = grid(bb); im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    T = lambda cs: [((x - bb[0]) * PPM, (y - bb[1]) * PPM) for x, y in cs]
    for gg in geoms:
        for p in (gg.geoms if hasattr(gg, "geoms") else [gg]):
            if p.geom_type != "Polygon" or p.is_empty: continue
            d.polygon(T(p.exterior.coords), fill=255)
            for h in p.interiors: d.polygon(T(h.coords), fill=0)
    return np.array(im) > 127

def dst_masks(P, bb):
    r = json.load(open(f"{kbcore.outdir(P)}/{SIZE}/result_{P}.json"))["full"]; ox, oy = r["origin"]
    fish_stop = [all(c.startswith("FI") for c in ps.get("codes", [])) for ps in r["per_stop"]]
    stem_stop = [set(ps.get("codes", [])) <= {"ST"} for ps in r["per_stop"]]          # stems: generated, not traced (1 px/mm mockup)
    H, W = grid(bb); ims = {k: Image.new("L", (W, H), 0) for k in ("fish", "flora", "stems")}; dr = {k: ImageDraw.Draw(v) for k, v in ims.items()}
    w = 1; ci = 0; prev = None                 # 1 px (0.33 mm) lines: stitched extent, no extra growth
    for x, y, c in pe.read(r["file"] + ".dst").stitches:
        k = c & pe.COMMAND_MASK; p = ((ox + x / 10 - bb[0]) * PPM, (oy + y / 10 - bb[1]) * PPM)
        if k == pe.STITCH:
            j = min(ci, len(fish_stop) - 1)
            if prev is not None: dr["fish" if fish_stop[j] else ("stems" if stem_stop[j] else "flora")].line([prev, p], fill=255, width=w)
            prev = p
        elif k == pe.COLOR_CHANGE: ci += 1; prev = None
        elif k in (pe.TRIM, pe.JUMP): prev = None
        elif k == pe.END: break
    st = qa.disk(0.6, PPM)
    return {k: ndi.binary_fill_holes(ndi.binary_closing(np.array(v) > 0, structure=st)) for k, v in ims.items()}, r["file"]

def koi_footprints(P):
    """the mockup's koi (now tetras) — excluded from the flora reference"""
    out = []
    for k in META["fish"]:
        if k["piece"] != P: continue
        Lk = k["L"] / 0.82; a = math.radians(k["ang"]); u = np.array([math.cos(a), math.sin(a)]); c = np.array(k["c"])
        out.append(LineString([tuple(c - u * Lk * 0.55), tuple(c + u * Lk * 0.55)]).buffer(0.17 * Lk))
    return out

def _old_flora_reference(P, bb, design_area):
    mk = np.array(MM.warp_piece(P, bb, PPM, mt)).astype(float)
    inside = design_area
    fab = np.median(mk[inside], axis=0)
    dist = np.sqrt(((mk - fab) ** 2).sum(-1)); red = (mk[..., 0] > mk[..., 2] + 40)
    emb = (dist > 48) & ~red & inside
    emb &= ~raster(koi_footprints(P), bb)
    emb = ndi.binary_fill_holes(ndi.binary_opening(emb, structure=qa.disk(1.0, PPM)))
    return emb, fab

PROTECT = ("FR_vine_flower0", "FR_vine_flower1")

def run(P):
    bb = BB[P]
    ref_flora, tone, _ = MR.flora_mask(P, META["koi_mm"].get(P, []), mt=mt)
    # composed reference: the two FR lilies traced from the CLOSE-UP replace their (1 px/mm) mockup pixels
    lil = [r["geom"] for r in ART[P] if r["unit"] in PROTECT]
    lily_ref = raster(lil, bb) if lil else np.zeros_like(ref_flora)
    if lil: ref_flora = ref_flora | lily_ref          # the close-up lily silhouettes are part of the reference
    out, dfile = dst_masks(P, bb)
    # stems are generated, not traced (A14 list): their footprint is taken out of the flora comparison (merge_stops can put a
    # stem in the same colour stop as traced fill, so stop codes alone cannot separate them)
    stem_zone = raster([r["geom"].buffer(0.45) for r in ART[P] if r["grp"] == "ST"], bb)
    out["stems"] = out["stems"] | (out["flora"] & stem_zone); out["flora"] = out["flora"] & ~stem_zone
    ref_flora = ref_flora & ~stem_zone                 # ... and out of the reference (same footprint on both sides)
    lab, n = ndi.label(ref_flora); areas = ndi.sum(ref_flora, lab, range(1, n + 1)) / PPM**2
    small = areas < 150
    lily_zone = raster([unary_union(lil).buffer(1.0)], bb) if lil else np.zeros_like(ref_flora)
    near_lily = np.array([bool((lily_zone & (lab == i + 1)).any()) for i in range(n)]) if n else np.zeros(0, bool)
    pet = np.isin(lab, 1 + np.nonzero(small & ~near_lily)[0]); clus = np.isin(lab, 1 + np.nonzero(~small)[0])
    zone_n = int((small & near_lily).sum())          # small mockup bits inside the close-up lily zone (the close-up governs there)
    rows = dict(petals=qa.motif_match(pet, out["flora"], PPM), clusters=qa.motif_match(clus, out["flora"], PPM), fish=[])
    # fish: one motif per fish (composed target = the art's fish regions, reference_fish proportions at the mockup positions)
    for k in META["fish"]:
        if k["piece"] != P: continue
        tg = [r["geom"] for r in ART[P] if r["unit"] == k["unit"]]
        if not tg: continue
        t_m = raster(tg, bb); foot = raster([unary_union(tg).buffer(2.0)], bb)
        rr = qa.motif_match(t_m, out["fish"] & foot, PPM)
        if rr:
            best = max(rr, key=lambda x: x["area_mm2"]); best["motif"] = k["unit"]; rows["fish"].append(best)
    fish_t = raster([r["geom"] for r in ART[P] if r["grp"].startswith("FI")], bb)
    zone_bits = np.isin(lab, 1 + np.nonzero(small & near_lily)[0])
    gaps = qa.uncovered((ref_flora & ~zone_bits) | fish_t, out["flora"] | out["fish"] | out["stems"], PPM)
    for fam in rows.values():
        for r in fam: r["x_mm"] = round(r["x_mm"] + bb[0], 1); r["y_mm"] = round(r["y_mm"] + bb[1], 1)
    for r in gaps: r["x_mm"] = round(r["x_mm"] + bb[0], 1); r["y_mm"] = round(r["y_mm"] + bb[1], 1)
    vis = np.zeros(ref_flora.shape + (3,), np.uint8); vis[ref_flora | fish_t] = (90, 90, 200); vis[(out["flora"] | out["fish"])] += np.array([0, 120, 0], np.uint8)
    Image.fromarray(vis).save(f"out/fidelity_{P}.png")
    return dict(dst=dfile + ".dst", rows=rows, gaps=gaps, lily_zone_bits=zone_n)

if __name__ == "__main__":
    res = {P: run(P) for P in kbcore.PIECES}
    json.dump(res, open(f"out/fidelity_{SIZE}.json", "w"), indent=1, default=float)
    for P, r in res.items():
        print(P, {fam: (sum(x["ok"] for x in rs), len(rs)) for fam, rs in r["rows"].items()}, "gaps>=25:", [(g_["x_mm"], g_["y_mm"], g_["area_mm2"]) for g_ in r["gaps"]][:6])
        for fam, rs in r["rows"].items():
            for x in rs:
                if not x["ok"]: print("   FAIL", fam, x)
