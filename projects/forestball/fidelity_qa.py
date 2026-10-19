"""LESSONS A14 / A15 fidelity gates on the SHIPPED grade-B DSTs (size M), per motif family:
  qa.motif_match(ref, dst, ppm): every traced motif's silhouette vs what the DST sews (IoU >= 0.70, width + height >= 80 %).
  qa.uncovered(ref, dst, ppm):   areas the reference says are embroidered but the DST leaves bare (>= 25 mm² after a 1 mm opening).
References (same garment-mm grids as the trace): out/art/design_lbl_<piece>.npy (per-pixel thread of the traced source, inside
the keep-outs; garment details are outside the art mask: zip, welts, seams are keep-outs, the CB seam strip is masked for the
rays) and out/art/ray_mask_ref.npy (the mockup's ray stripes, rays_trace2.py).
-> fidelity_qa.json + a table image per piece for the compare sheets (out/dbg/fqa_<piece>.png)."""
import json, sys
import numpy as np
import pyembroidery as pe
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
import shapely
import fbcore, qa, back as B, front as F
import trace_fb as T
from motifs2 import HEX

CUR = json.load(open("dst_current.json"))
FAM = {"leaves": ["leaf"], "moss + grass": ["moss", "mosslt", "grass"], "bark / chain / stream dark": ["navy", "bark", "royal", "mossdk", "brown"],
       "highlights + water light": ["cream", "waterlt"]}

def ray_stops(key):
    """0-based colour-stop indices of the light rays: the sage / cream stops sewn first, right after the placeholder outline"""
    f = CUR[key]["file"]; tl = [t.hex_color().upper() for t in pe.read(f + ".pes").threadlist]; out = set()
    rc = {HEX["sage"].upper(), HEX["cream"].upper()}
    for i, c in enumerate(tl):
        if i == 0: continue
        if c in rc: out.add(i)
        else: break
    return out

def dst_mask(key, bbox, ppm, cols=None, close_mm=0.0, open_mm=0.9, only_stops=None, skip_stops=None):
    x0, y0, x1, y1 = bbox; W, H = int((x1 - x0) * ppm), int((y1 - y0) * ppm)   # same as trace_fb.grid
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im); f = CUR[key]["file"]; cx, cy = CUR[key]["centre"]
    tl = [t.hex_color().upper() for t in pe.read(f + ".pes").threadlist]; p = pe.read(f + ".dst"); ci = 0; prev = None
    want = None if cols is None else {HEX[c].upper() for c in cols}
    lw = max(1, int(round(0.42 * ppm)))
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK
        if k == pe.COLOR_CHANGE: ci += 1; prev = None; continue
        if k != pe.STITCH: prev = None; continue
        P_ = ((x / 10 + cx - x0) * ppm, (y / 10 + cy - y0) * ppm)
        use = (want is None or tl[min(ci, len(tl) - 1)] in want) and (only_stops is None or ci in only_stops) and (skip_stops is None or ci not in skip_stops)
        if prev and use: d.line([prev, P_], fill=255, width=lw)
        prev = P_
    m = np.array(im) > 0
    if close_mm > 0: m = ndi.binary_closing(m, structure=qa.disk(close_mm, ppm))
    # the sewn COVERAGE, not the travel: single running lines (travel / centre runs hidden under later fills, 0.4 mm) are
    # opened away, so a spray's leaves are not chained into one "motif" by the run that travels between them
    if open_mm > 0: m = ndi.binary_opening(m, structure=qa.disk(open_mm, ppm))
    return m

def motif_match_cells(ref, out, ppm, min_mm2=4.0, iou_min=0.70, ratio_min=0.80):
    """qa.motif_match, with every stitched pixel assigned to its NEAREST reference motif (its Voronoi cell) before the
    comparison. Plain qa.motif_match unions every out component touching a motif, so on dense traced art (sprays,
    grass, chain links) a correct leaf "fails" because the DST joins it to its neighbour (Forestball: 706 back leaves, 44 pass).
    Cells keep the gate's teeth: a stand-in larger than its reference overshoots inside its own cell and lowers IoU; a missing
    or flattened motif fails on IoU / height. Same thresholds as the engine gate."""
    lab, n = ndi.label(ref)
    if n == 0: return []
    idx = ndi.distance_transform_edt(lab == 0, return_distances=False, return_indices=True)
    near = lab[idx[0], idx[1]]; own = np.where(out, near, 0)
    rows = []
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        r = lab == k if False else None
        pad = int(4 * ppm); y0, y1 = max(0, sl[0].start - pad), min(ref.shape[0], sl[0].stop + pad)
        x0, x1 = max(0, sl[1].start - pad), min(ref.shape[1], sl[1].stop + pad)
        r = lab[y0:y1, x0:x1] == k; area = r.sum() / ppm**2
        if area < min_mm2: continue
        o = own[y0:y1, x0:x1] == k
        iou = (r & o).sum() / max((r | o).sum(), 1)
        def ext(m, ax):
            ii = np.nonzero(m.any(axis=ax))[0]; return (ii[-1] - ii[0] + 1) / ppm if len(ii) else 0.0
        wr, hr = ext(o, 0) / max(ext(r, 0), 1e-9), ext(o, 1) / max(ext(r, 1), 1e-9)
        ok = iou >= iou_min and min(wr, 1 / max(wr, 1e-9)) >= ratio_min and min(hr, 1 / max(hr, 1e-9)) >= ratio_min
        rows.append(dict(motif=k, x_mm=round((x0 + x1) / 2 / ppm, 1), y_mm=round((y0 + y1) / 2 / ppm, 1), area_mm2=round(float(area), 1),
                         iou=round(float(iou), 2), w_ratio=round(float(wr), 2), h_ratio=round(float(hr), 2), ok=bool(ok)))
    return rows

def summarise(rows):
    n = len(rows); ok = sum(r["ok"] for r in rows); ko = sum((not r["ok"]) and r.get("why") == "keep-out" for r in rows)
    fails = [r for r in rows if not r["ok"] and r.get("why") != "keep-out"]
    return dict(motifs=n, passed=ok, keepout=ko, failed=len(fails), failed_large=sum(r["area_mm2"] >= 25 for r in fails),
                worst=sorted(fails, key=lambda r: -r["area_mm2"])[:8])

def piece_qa(key, lbl_path, bbox, clip, extra_ref=None):
    lbl = np.load(lbl_path); ppm = 4.0; nT = len(T.TONES)
    XX, YY = T.grid(bbox) if True else None
    res = {"families": {}, "uncovered": []}
    RS = ray_stops(key) if key == "back" else set()
    kz = clip.boundary.buffer(1.5)
    for fam, cols in FAM.items():
        ref = np.isin(lbl, [T.TONES.index(c) for c in cols])
        if key == "back": ref &= ~shapely.contains_xy(B.PH_BOX.buffer(1.5), XX, YY)
        out = dst_mask(key, bbox, ppm, cols=[fbcore.col(c) for c in cols], close_mm=0.6, skip_stops=RS)
        out = ndi.binary_erosion(out, iterations=1)          # stitched coverage = outline + pull comp (~0.25 mm)
        rows = motif_match_cells(ref, out, ppm, min_mm2=4.0)
        for r in rows:                                       # motifs the keep-out cut: left out whole on purpose (A8, review 6)
            if not r["ok"] and kz.intersects(shapely.geometry.Point(r["x_mm"] + bbox[0], r["y_mm"] + bbox[1]).buffer(max(3.0, (r["area_mm2"] ** 0.5)))):
                r["why"] = "keep-out"
        eng = qa.motif_match(ref, out, ppm, min_mm2=4.0)
        res["families"][fam] = dict(summarise(rows), engine_passed=sum(r["ok"] for r in eng), engine_motifs=len(eng))
    design = lbl < nT
    if key == "back": design &= ~shapely.contains_xy(B.PH_BOX.buffer(1.5), XX, YY)
    allout = dst_mask(key, bbox, ppm, close_mm=0.8, skip_stops=RS)
    gaps = qa.uncovered(design, allout, ppm, min_mm2=25.0)
    edge = clip.boundary
    for g in gaps:
        dist = edge.distance(shapely.geometry.Point(g["x_mm"] + bbox[0], g["y_mm"] + bbox[1]))
        g["x_mm"] = round(g["x_mm"] + bbox[0], 1); g["y_mm"] = round(g["y_mm"] + bbox[1], 1)
        g["why"] = "keep-out edge: leaf/twig left out whole or art rounded 4 mm inside the keep-out" if dist <= 12 else "UNEXPLAINED"
    res["uncovered"] = gaps
    if extra_ref is not None:
        rref, rbare, rbbox, rppm = extra_ref
        out = dst_mask(key, rbbox, rppm, cols=["sage", "cream"], close_mm=1.8, open_mm=0.0, only_stops=RS) & rbare
        rows = motif_match_cells(rref, out, rppm, min_mm2=8.0)
        res["families"]["light rays (mockup stripes)"] = summarise(rows); res["ray_rows"] = rows
        # per-ray angle: the mockup stripe's traced axis vs the axis of what the DST sews inside it (PCA of the stitched pixels)
        R = json.load(open("rays_trace2.json")); XXr, YYr = np.meshgrid(rbbox[0] + (np.arange(out.shape[1]) + 0.5) / rppm, rbbox[1] + (np.arange(out.shape[0]) + 0.5) / rppm)
        ang = []
        for i, st in enumerate(R["stripes"]):
            P = shapely.geometry.Polygon(st["pts"]).buffer(1.0)
            b = P.bounds; c0, r0 = int((b[0] - rbbox[0]) * rppm), int((b[1] - rbbox[1]) * rppm); c1, r1 = int((b[2] - rbbox[0]) * rppm) + 1, int((b[3] - rbbox[1]) * rppm) + 1
            sub = out[r0:r1, c0:c1] & shapely.contains_xy(P, XXr[r0:r1, c0:c1], YYr[r0:r1, c0:c1])
            if sub.sum() < 20: ang.append(dict(stripe=i, mockup_deg=st["axis_deg"], dst_deg=None, length=st["length"])); continue
            X = XXr[r0:r1, c0:c1][sub]; Y = YYr[r0:r1, c0:c1][sub]; ev, evec = np.linalg.eigh(np.cov(np.stack([X, Y]))); d_ = evec[:, 1]
            a = np.degrees(np.arctan2(d_[1], d_[0])) % 180; sl = 180 - a if a > 90 else a
            ang.append(dict(stripe=i, mockup_deg=st["axis_deg"], dst_deg=round(float(sl), 1), length=st["length"]))
        res["ray_angles"] = ang
    return res

def table_png(name, res, path):
    lines = [f"FIDELITY GATES {name} (grade B DST vs traced reference; LESSONS A14 motif_match / A15 uncovered)"]
    for fam, s in res["families"].items():
        lines.append(f"  {fam:30s} motifs {s['motifs']:4d}  pass {s['passed']:4d}  keep-out (left out whole) {s.get('keepout', 0):3d}  "
                     f"fail {s['failed']:3d} (>= 25 mm²: {s.get('failed_large', 0)})" +
                     (f"   [engine qa.motif_match, neighbours merged: {s['engine_passed']}/{s['engine_motifs']}]" if "engine_motifs" in s else ""))
    un = [g for g in res["uncovered"] if g["why"] == "UNEXPLAINED"]
    lines.append(f"  uncovered >= 25 mm²: {len(res['uncovered'])} gaps, {len(un)} unexplained" +
                 ("" if not res["uncovered"] else "   largest " + ", ".join(f"{g['area_mm2']:.0f} mm² @({g['x_mm']:.0f},{g['y_mm']:.0f}) {g['why'][:9]}" for g in res["uncovered"][:3])))
    try: fnt = ImageFont.truetype("DejaVuSansMono.ttf", 20)
    except Exception: fnt = None
    im = Image.new("RGB", (2300, 30 * len(lines) + 20), (255, 255, 255)); d = ImageDraw.Draw(im)
    for i, l in enumerate(lines): d.text((10, 10 + 30 * i), l, fill=(20, 20, 20) if i else (120, 0, 0), font=fnt)
    im.save(path)

if __name__ == "__main__":
    out = {}
    rr = np.load("out/art/ray_mask_ref.npy"); rb = np.load("out/art/ray_bare.npy")
    out["back"] = piece_qa("back", "out/art/design_lbl_back.npy", (-300, -20, 300, 600), B.CLIP, extra_ref=(rr, rb, (-300, -20, 300, 600), 3.0))
    for p, side in (("02R", "R"), ("02L", "L")):
        bb = json.load(open(f"out/art/design_bbox_{p}.json"))
        out[p] = piece_qa(p, f"out/art/design_lbl_{p}.npy", tuple(bb), F.clip_for(side))
    json.dump(out, open("fidelity_qa.json", "w"), indent=1, default=float)
    for k, v in out.items():
        table_png(k, v, f"out/dbg/fqa_{k}.png")
        print(k, {f: (s["passed"], s["motifs"]) for f, s in v["families"].items()}, "uncovered", len(v["uncovered"]),
              "unexplained", sum(g["why"] == "UNEXPLAINED" for g in v["uncovered"]))
