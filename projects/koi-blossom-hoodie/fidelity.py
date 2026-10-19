"""LESSONS A13/A14/A15 gates on the shipped size-M DSTs (Rev C) — every REFERENCE mask from input pixels only (refmask.py).

Reference (refmask.py, reads no art / scene / template):
  flora   refmask.flora(P): the mockup's embroidery pixels (the two close-up lilies pasted in their registration discs
          on FR), garment details + the mockup fish masked first. Split into families by size: floating petals
          (components < 150 mm2) and clusters (>= 150 mm2: lilies + leaves + stems, stems INCLUDED).
  lilies  per lily: the same flora pixels inside the lily's disc (centre + radius read on the input images:
          floratrace guides / close-up registration) — silhouette + tone + row-direction rows.
  fish    refmask.fish_ref(P): the founder's reference tetra pixels at each mockup fish pose (pose from the mockup
          pixels), 0.82 x the mockup length (founder decision).
Out masks: every sewn stitch of the DST as a 0.4 mm thread line, closed 0.5 mm (row spacing), NO hole filling.
Fish vs flora stitches: stops that sew only FI-* codes are fish; a stop that also sews flora (shared thread colour after
merge_stops) is split by the fish pose boxes (from the mockup pixels).
Gates: qa.motif_match (IoU >= 0.70, width + height >= 80 %) per motif; qa.uncovered (gaps >= 25 mm2);
A13 texture primitives: tone agreement (reference luminance quartiles vs the DST's thread luminance quartiles, same
pixels: exact + within one step), lily row direction (median angle between stitches and the petal axis = radial from
the lily centre), fish facet tone agreement.
Output: out/fidelity_M.json + out/fidelity_<piece>.png.   usage: python3 fidelity.py"""
import kbcore, json, math, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
import pyembroidery as pe
import qa, refmask as RM, front as F
import floratrace as FT_guides                      # only the lily centres (input readings), never its masks

SIZE = "M"; PPM = RM.PPM
_, mt = F.pieces(SIZE)

def hexrgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def dst_render(P):
    """(stitch segments in piece mm with stop index, stop codes, thread colours, file)"""
    r = json.load(open(f"{kbcore.outdir(P)}/{SIZE}/result_{P}.json"))["full"]; ox, oy = r["origin"]
    cols = [t.hex_color() for t in pe.read(r["file"] + ".pes").threadlist]
    codes = [ps.get("codes", []) for ps in r["per_stop"]]
    segs = []; ci = 0; prev = None
    for x, y, c in pe.read(r["file"] + ".dst").stitches:
        k = c & pe.COMMAND_MASK; p = (ox + x / 10, oy + y / 10)
        if k == pe.STITCH:
            if prev is not None: segs.append((ci, prev, p))
            prev = p
        elif k == pe.COLOR_CHANGE: ci += 1; prev = None
        elif k in (pe.TRIM, pe.JUMP): prev = None
        elif k == pe.END: break
    return segs, codes, cols, r["file"]

def pose_box(pose, f=1.15):
    from shapely.geometry import Polygon
    c = np.array(pose["c"]); a = math.radians(pose["ang"]); e = np.array([math.cos(a), math.sin(a)]); n = np.array([-e[1], e[0]])
    L = pose["L_ref"] * f / 2; W = pose["L_ref"] * 0.30
    return Polygon([tuple(c + e * L + n * W), tuple(c - e * L + n * W), tuple(c - e * L - n * W), tuple(c + e * L - n * W)])

NST = {}
def masks(P, poses):
    NST.clear()
    segs, codes, cols, f = dst_render(P); bb = RM.BB[P]
    H, W = RM.grid(P)[0].shape
    ims = {k: Image.new("L", (W, H), 0) for k in ("fish", "flora")}; dr = {k: ImageDraw.Draw(v) for k, v in ims.items()}
    lum = Image.new("L", (W, H), 0); dl = ImageDraw.Draw(lum)
    ang = np.full((H, W), np.nan, np.float32)
    boxes = [pose_box(p) for p in poses]
    from shapely.geometry import Point
    from shapely.ops import unary_union
    bu = unary_union(boxes) if boxes else None
    w = max(1, int(round(0.4 * PPM)))
    T = lambda p: ((p[0] - bb[0]) * PPM, (p[1] - bb[1]) * PPM)
    for ci, a, b in segs:
        cs = codes[min(ci, len(codes) - 1)]
        fish_only = cs and all(c.startswith("FI") for c in cs); mixed = any(c.startswith("FI") for c in cs) and not fish_only
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        fam = "fish" if (fish_only or (mixed and bu is not None and bu.contains(Point(mid)))) else "flora"
        A, B = T(a), T(b); dr[fam].line([A, B], fill=255, width=w); NST[fam] = NST.get(fam, 0) + 1
        rgb = hexrgb(cols[min(ci, len(cols) - 1)]); dl.line([A, B], fill=int(sum(rgb) / 3), width=w)
        if fam == "flora":
            i, j = int(T(mid)[1]), int(T(mid)[0])
            if 0 <= i < H and 0 <= j < W and math.hypot(b[0] - a[0], b[1] - a[1]) > 1.0: ang[i, j] = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    st = RM.disk(0.5)
    out = {k: ndi.binary_closing(np.array(v) > 0, structure=st) | (np.array(v) > 0) for k, v in ims.items()}
    return out, np.array(lum).astype(float), ang, f

def tone_agree(ref_tone, ref_m, out_lum, out_m):
    """reference luminance quartile (0-3) vs the DST thread-luminance quartile on the pixels both cover"""
    m = ref_m & out_m & (ref_tone >= 0)
    if m.sum() < 25: return None
    q = np.quantile(out_lum[m], [0.25, 0.5, 0.75]); ot = np.digitize(out_lum[m], q); rt = ref_tone[m]
    return dict(exact=round(float((ot == rt).mean()), 2), within1=round(float((np.abs(ot - rt) <= 1).mean()), 2))

def lily_discs(P):
    """lily centre + radius from the input readings (close-up registration / the guides read on the mockup zooms)"""
    out = []
    for spec in FT_guides.lily_specs(P):
        cx, cy = FT_guides.to_mm(P, [spec["c"][0]], [spec["c"][1]]); c = (float(cx[0]), float(cy[0]))
        tips = [FT_guides.to_mm(P, t[0], t[1]) for _, t in spec["petals"]]
        Rr = float(np.median([math.hypot(float(x[0]) - c[0], float(y[0]) - c[1]) for x, y in tips]))
        out.append((spec["name"], spec["src"], c, Rr))
    return out

def run(P):
    bb = RM.BB[P]
    ref = RM.flora(P); tone = RM.tone(P); fr = RM.fish_ref(P); poses = [p for p, _ in fr]
    fish_all = np.any([m for _, m in fr], axis=0) if fr else np.zeros_like(ref)
    out, olum, oang, dfile = masks(P, poses); NSTP = dict(NST)
    fish_zone = ndi.binary_dilation(fish_all, structure=RM.disk(1.5))
    ref_f = ref & ~fish_zone; out_f = out["flora"] & ~fish_zone
    lab, n = ndi.label(ref_f); areas = ndi.sum(ref_f, lab, range(1, n + 1)) / PPM ** 2
    pet = np.isin(lab, 1 + np.nonzero(areas < 150)[0]); clus = np.isin(lab, 1 + np.nonzero(areas >= 150)[0])
    rows = dict(petals=qa.motif_match(pet, out_f, PPM), clusters=qa.motif_match(clus, out_f, PPM), lilies=[], fish=[])
    XX, YY = RM.grid(P)
    for name, src, c, Rr in lily_discs(P):
        disc = np.hypot(XX - c[0], YY - c[1]) < Rr * 1.0
        rm = ref_f & disc
        if rm.sum() < 20: continue
        om = out_f & disc
        iou = float((rm & om).sum() / max((rm | om).sum(), 1))
        def ext(m, ax):
            idx = np.nonzero(m.any(axis=ax))[0]; return (idx[-1] - idx[0] + 1) / PPM if len(idx) else 0.0
        wr = ext(om, 0) / max(ext(rm, 0), 1e-9); hr = ext(om, 1) / max(ext(rm, 1), 1e-9)
        ta = tone_agree(tone, rm, olum, om)
        a = oang[disc & ~np.isnan(oang) & (np.hypot(XX - c[0], YY - c[1]) > 0.25 * Rr)]
        rad = np.degrees(np.arctan2(YY - c[1], XX - c[0]))[disc & ~np.isnan(oang) & (np.hypot(XX - c[0], YY - c[1]) > 0.25 * Rr)]
        dd = np.abs(((a - rad) + 90) % 180 - 90) if a.size else np.array([90.0])
        ok = iou >= 0.70 and min(wr, 1 / max(wr, 1e-9)) >= 0.8 and min(hr, 1 / max(hr, 1e-9)) >= 0.8
        rows["lilies"].append(dict(motif=name, ref=src, x_mm=round(c[0], 1), y_mm=round(c[1], 1), R_mm=round(Rr, 1), area_mm2=round(float(rm.sum() / PPM ** 2), 1),
                                   iou=round(iou, 2), w_ratio=round(wr, 2), h_ratio=round(hr, 2), ok=bool(ok), tone=ta,
                                   row_dir_median_deg=round(float(np.median(dd)), 1), rows_along_pct=round(float((dd < 30).mean() * 100), 1)))
    for pose, m in fr:
        zone = ndi.binary_dilation(m, structure=RM.disk(4.0))
        rr = qa.motif_match(m, out["fish"] & zone, PPM)
        if not rr: continue
        best = max(rr, key=lambda x: x["area_mm2"]); best["motif"] = f"fish at ({pose['c'][0]:.0f}, {pose['c'][1]:.0f})"
        best["L_mm"] = round(pose["L_ref"], 1); best["heading_deg"] = round(pose["ang"])
        best["tone"] = tone_agree(pose["tone"], m, olum, out["fish"])
        rows["fish"].append(best)
    for fam in ("petals", "clusters", "fish"):
        for r_ in rows[fam]:
            if fam != "fish" or "x_mm" in r_:
                r_["x_mm"] = round(r_["x_mm"] + bb[0], 1); r_["y_mm"] = round(r_["y_mm"] + bb[1], 1)
    # cluster tone agreement
    for r_ in rows["clusters"]:
        i, j = int((r_["y_mm"] - bb[1]) * PPM), int((r_["x_mm"] - bb[0]) * PPM)
        k = lab[min(max(i, 0), lab.shape[0] - 1), min(max(j, 0), lab.shape[1] - 1)]
        cm = (lab == k) if k > 0 else clus
        r_["tone"] = tone_agree(tone, cm, olum, out_f)
    gaps = qa.uncovered(ref | fish_all, out["flora"] | out["fish"], PPM)
    for g_ in gaps: g_["x_mm"] = round(g_["x_mm"] + bb[0], 1); g_["y_mm"] = round(g_["y_mm"] + bb[1], 1)
    # explain gaps: inside the close-up lily zone edge / hem keep-out etc. are listed, none hidden
    band = band_zone_mm2(P)
    vis = np.zeros(ref.shape + (3,), np.uint8); vis[ref | fish_all] = (90, 90, 200); vis[out["flora"] | out["fish"]] += np.array([0, 120, 0], np.uint8)
    Image.fromarray(vis).save(f"out/fidelity_{P}.png")
    return dict(dst=dfile + ".dst", rows=rows, gaps=gaps, band_zone_mm2=band, stitches_by_family=NSTP,
                reference="refmask.py: input pixels only (mockup front.png" + (" + close-up lily discs" if P == "FR" else "") + "; fish = reference_fish.png at the mockup poses x 0.82)")

def band_zone_mm2(P):
    """mockup embroidery pixels between the hem / cuff keep-out line and the band seam (art stops there, item 6)"""
    if P not in ("FR", "FL", "SR"): return 0.0
    k = F.keep_geoms(SIZE, P); seam = k["hem"] if P in ("FR", "FL") else k["cuff"]
    strip = k["panel"].intersection(seam.buffer(F.KEEP_HEM if P in ("FR", "FL") else F.KEEP_CUFF))
    rgb = RM.source(P)[0]; fab = np.median(rgb[RM.art_area(P)], axis=0)
    m = RM.raster([strip], P) & (np.sqrt(((rgb - fab) ** 2).sum(-1)) > 30) & ((rgb[..., 2] - rgb[..., 0]) > fab[2] - fab[0] + 22)
    m = ndi.binary_opening(m, structure=RM.disk(1.0))
    return round(float(m.sum() / PPM ** 2), 1)

if __name__ == "__main__":
    res = {P: run(P) for P in kbcore.PIECES}
    json.dump(res, open(f"out/fidelity_{SIZE}.json", "w"), indent=1, default=float)
    for P, r in res.items():
        print(P, {fam: (sum(x["ok"] for x in rs), len(rs), min([x["iou"] for x in rs] or [1])) for fam, rs in r["rows"].items()},
              "gaps>=25:", [(g_["x_mm"], g_["y_mm"], g_["area_mm2"]) for g_ in r["gaps"]][:8], "band", r["band_zone_mm2"])
        for fam, rs in r["rows"].items():
            for x in rs:
                if not x["ok"]: print("   FAIL", fam, {k: x[k] for k in ("x_mm", "y_mm", "area_mm2", "iou", "w_ratio", "h_ratio")})
        for x in r["rows"]["lilies"]: print("   lily", x["motif"], x["iou"], x["tone"], x["row_dir_median_deg"], x["rows_along_pct"])
