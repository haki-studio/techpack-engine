"""Koi engine trial (tag koi, 2026-10-20): the delivered Rev B FR file vs the engine's file, SAME crop, SAME gates.

  PYTHONPATH=engine python3 projects/koi-blossom-hoodie/bench/trial_compare.py      (no Anthropic API calls)

Reads only the two WRITTEN DSTs (+ their .pes thread lists) and input pixels:
  - bench gates (engine/digitize/bench.run_gates): direction on the visible layer vs the 12 ppm reference, chaos,
    density, trims per covered area, satin shape (blobs / fans), stack, colours;
  - motif_match + uncovered (LESSONS A14 / A15) against refmask.py (Rev C, written to be independent of ANY art: it
    imports nothing from the art side, which is blocked here with sys.modules[...] = None): flora = mockup + close-up
    pixels, fish = the founder's reference tetra at the MOCKUP fish poses x 0.82. Neither the Rev B art nor the engine's
    parts feed it, so the same reference grades both files;
  - exposed stitches (DST-only proxy for travel on bare fabric): stitch length >= 1 mm lying over cells that no OTHER
    stitch covers (< 0.3 mm/mm2 of other thread, > 1 mm of it bare, 1 mm cells: a 0.5 mm cell
    aliases with 0.45 mm tatami rows and flags thousands of covered stitches), counted when > 0.5 mm of it is bare.
The engine's own gates.json adds what only a plan can give (part ids: angle coherence, direction by source).
Writes bench/trial_gates.json and the side-by-side PNGs bench/trial_*.png."""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); PROJ = os.path.dirname(HERE); ROOT = os.path.dirname(os.path.dirname(PROJ))
os.chdir(PROJ); sys.path[:0] = [os.path.join(ROOT, "engine"), PROJ]
for _m in ("scene", "kb_motifs", "art_size", "floratrace", "fishtrace", "kbvis", "lilyguides"): sys.modules[_m] = None   # art side blocked
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
import pyembroidery as pe
import qa, dstlive
from digitize import bench
from digitize.extract import register

CFG = json.load(open(os.path.join(HERE, "bench.json"))); CROP = tuple(CFG["crop"])
REVB = (os.path.join(PROJ, CFG["baseline_dst"]), tuple(CFG["baseline_origin"]))
ENG_DIR = os.path.join(PROJ, "out/digitize/KOI_FR_M_crop")
ENG = (os.path.join(ENG_DIR, "KOI_FR_M_crop.dst"), tuple(json.load(open(os.path.join(ENG_DIR, "readback.json")))["origin"]))
FILES = {"revB": REVB, "engine": ENG}
NAMES = {"revB": "Rev B delivered", "engine": "Engine (parts-based)"}


def colours(dst): return [t.hex_color() for t in pe.read(os.path.splitext(dst)[0] + ".pes").threadlist]


def file_counts(dst, origin):
    """whole-file and in-crop stitch / colour counts from the DST read-back"""
    p = pe.read(dst); n = sum(1 for _, _, c in p.stitches if (c & pe.COMMAND_MASK) == pe.STITCH)
    segs = qa.dst_segments(dst, origin); inc = qa.clip_segments(segs, CROP)
    return dict(stitches_file=n, threads_file=len(set(colours(dst))), stitches_in_crop=len(inc))


def exposed(dst, origin, cell=1.0, other_min=0.3, min_len=1.0, min_bare=1.0):
    segs = qa.clip_segments(qa.dst_segments(dst, origin), CROP); x0, y0, x1, y1 = CROP
    H, W = int(math.ceil((y1 - y0) / cell)), int(math.ceil((x1 - x0) / cell)); g = np.zeros((H, W))
    def samples(s):
        L = math.hypot(s[2] - s[0], s[3] - s[1]); n = max(1, int(L / 0.25))
        t = (np.arange(n) + 0.5) / n; xs = s[0] + (s[2] - s[0]) * t; ys = s[1] + (s[3] - s[1]) * t
        iy = np.clip(((ys - y0) / cell).astype(int), 0, H - 1); ix = np.clip(((xs - x0) / cell).astype(int), 0, W - 1)
        return iy, ix, L / n
    S = [samples(s) for s in segs]
    for iy, ix, w in S: np.add.at(g, (iy, ix), w)
    g /= cell * cell; n = 0; bare_mm = 0.0
    for s, (iy, ix, w) in zip(segs, S):
        L = math.hypot(s[2] - s[0], s[3] - s[1])
        if L < min_len: continue
        own = np.zeros_like(g); np.add.at(own, (iy, ix), w); own /= cell * cell
        b = ((g[iy, ix] - own[iy, ix]) < other_min).sum() * w
        if b > min_bare: n += 1; bare_mm += b
    return dict(stitches=n, bare_mm=round(bare_mm, 1), note="DST-only proxy: >= 1 mm stitches with > 1 mm over 1 mm cells holding < 0.3 mm/mm2 of other thread")


def refmasks():
    import refmask as RM
    fl = RM.flora("FR"); fish = RM.fish_ref("FR"); bb = RM.BB["FR"]; P = RM.PPM
    c0, r0 = int(round((CROP[0] - bb[0]) * P)), int(round((CROP[1] - bb[1]) * P))
    c1, r1 = int(round((CROP[2] - bb[0]) * P)), int(round((CROP[3] - bb[1]) * P))
    cut = lambda m: m[r0:r1, c0:c1]
    fishes = [cut(m) for _, m in fish if cut(m).sum() / P ** 2 >= 20]
    return P, cut(fl), fishes


def closeup_flora(P, reg):
    """reference (b): embroidery pixels of THIS registration (TPS-bent close-up over the crop, the engine's source), by a
    plain colour test written here (not the engine's evidence / tone trace): far from the duck's median colour AND blue
    or light; opened 1 mm, holes < 2 mm2 filled. Fish windows are not removed: fish are graded on reference (a) only."""
    rgb = register.reference(reg, "F", CROP, ppm=P)["rgb"]
    lum = rgb @ np.array([0.299, 0.587, 0.114]); fab = np.median(rgb[lum < np.percentile(lum, 50)], axis=0)
    dist = np.sqrt(((rgb - fab) ** 2).sum(-1)); blue = rgb[..., 2] - rgb[..., 0]
    m = (dist > 60) & ((blue > 25) | (lum > 120))
    r = int(round(0.5 * P)); yy, xx = np.ogrid[-r:r + 1, -r:r + 1]; m = ndi.binary_opening(m, xx * xx + yy * yy <= r * r)
    lab, n = ndi.label(~m); sz = np.bincount(lab.ravel()) / P ** 2; m |= (sz < 2.0)[lab] & (lab > 0)
    return m


def dst_mask(dst, origin, shape, P):
    ms = qa.dst_stop_masks(dst, origin, shape, P, to_mm=lambda x, y: (x - CROP[0], y - CROP[1]))
    return np.any(list(ms.values()), axis=0) if ms else np.zeros(shape, bool)


def fidelity(P, flora, fishes, out):
    fish_rows = []
    for m in fishes:
        r = qa.motif_match(m, out, P, near_mm=1.5)
        if r: fish_rows.append(max(r, key=lambda q: q["area_mm2"]))
    fl_rows = qa.motif_match(flora, out, P, min_mm2=8.0, near_mm=1.5)
    allref = flora | np.any(fishes, axis=0) if fishes else flora
    unc = qa.uncovered(allref, out, P, min_mm2=25.0)
    def summ(rows): return dict(n=len(rows), ok=sum(r["ok"] for r in rows), mean_iou=round(float(np.mean([r["iou"] for r in rows])) if rows else 0.0, 2))
    over = out & ~ndi.binary_dilation(allref, iterations=int(1.0 * P))       # stitches where the reference shows bare duck
    return dict(fish=summ(fish_rows), fish_rows=fish_rows, flora=summ(fl_rows), flora_fail=[r for r in fl_rows if not r["ok"]][:30],
                uncovered=dict(n=len(unc), mm2=round(sum(u["area_mm2"] for u in unc), 1), largest=unc[:8]),
                ref_mm2=round(float(allref.sum()) / P ** 2, 1), sewn_mm2=round(float(out.sum()) / P ** 2, 1),
                sewn_off_reference_mm2=round(float(over.sum()) / P ** 2, 1))


def font(n):
    try: return ImageFont.load_default(size=n)
    except TypeError: return ImageFont.load_default()


def sheet(tiles, path, title):
    W = sum(t.width for t, _ in tiles) + 12 * (len(tiles) + 1); H = max(t.height for t, _ in tiles) + 64
    im = Image.new("RGB", (W, H), (245, 245, 242)); d = ImageDraw.Draw(im); x = 12
    d.text((12, 6), title, fill=(20, 20, 20), font=font(16))
    for t, lab in tiles:
        im.paste(t, (x, 50)); d.text((x, 30), lab, fill=(20, 20, 20), font=font(14)); x += t.width + 12
    im = im.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE); im.save(path, optimize=True); return path


def views(box, ppm, reg):
    ref = Image.fromarray(register.reference(reg, "F", box, ppm=ppm)["rgb"].astype(np.uint8))
    out = [(ref, "reference (mockup + close-up, input pixels)")]
    for k, (dst, o) in FILES.items():
        out.append((dstlive.render(dst, colours(dst), ppm=ppm, shell=CFG["shell"], bounds=box, origin=o), NAMES[k] + " - live view"))
    return out


def main():
    reg = register.load(os.path.join(PROJ, CFG["registration"]))
    res = {"crop": list(CROP), "files": {}}
    P, flora, fishes = refmasks(); flora_b = closeup_flora(P, reg)
    for k, (dst, o) in FILES.items():
        row, aux = bench.run_gates(CFG, PROJ, dst, o)
        out = dst_mask(dst, o, flora.shape, P)
        fb = qa.motif_match(flora_b, out, P, min_mm2=8.0, near_mm=1.5)
        unc_b = qa.uncovered(flora_b, out, P, min_mm2=25.0)
        res["files"][k] = dict(dst=os.path.relpath(dst, PROJ), origin=list(o), counts=file_counts(dst, o), gates=row,
                               verdict=bench.verdict(row, CFG["targets"]), exposed=exposed(dst, o), fidelity=fidelity(P, flora, fishes, out),
                               fidelity_closeup=dict(flora=dict(n=len(fb), ok=sum(r["ok"] for r in fb), mean_iou=round(float(np.mean([r["iou"] for r in fb])), 2) if fb else 0.0),
                                                     uncovered=dict(n=len(unc_b), mm2=round(sum(u["area_mm2"] for u in unc_b), 1))))
        print(k, json.dumps({kk: res["files"][k][kk] for kk in ("counts", "exposed")}), res["files"][k]["fidelity"]["fish"], res["files"][k]["fidelity"]["flora"], res["files"][k]["fidelity_closeup"], flush=True)
    eg = json.load(open(os.path.join(ENG_DIR, "gates.json")))
    res["engine_plan"] = dict(parts=eg["parts"], direction_by_source=eg["direction_by_source"], direction_by_kind=eg["direction_by_kind"],
                              angle_coherence={kk: eg["angle_coherence"].get(kk) for kk in ("ok", "parts", "fails", "kinds", "by_kind")},
                              separation=eg.get("separation"), stub_area=eg["stub_area"], verdict=eg["verdict"])
    pj = json.load(open(os.path.join(ENG_DIR, "parts.json")))
    res["engine_plan"]["splitter_stats"] = pj["meta"].get("splitter_stats")
    res["engine_plan"]["area_by_kind_mm2"] = {}
    for q in pj["parts"]: res["engine_plan"]["area_by_kind_mm2"][q["kind"]] = round(res["engine_plan"]["area_by_kind_mm2"].get(q["kind"], 0) + q["area_mm2"], 1)
    json.dump(res, open(os.path.join(HERE, "trial_gates.json"), "w"), indent=1, default=float)
    sheet(views(CROP, 4.0, reg), os.path.join(HERE, "trial_side_by_side.png"),
          f"Koi Blossom FR size M, crop x {CROP[0]}..{CROP[2]}, y {CROP[1]}..{CROP[3]} mm (garment mm), equal scale 4 px/mm")
    for name, box in (("lily", (-220, 88, -140, 185)), ("fish", (-148, 76, -82, 132)), ("leaves", (-220, 228, -150, 300))):
        sheet(views(box, 10.0, reg), os.path.join(HERE, f"trial_zoom_{name}.png"),
              f"zoom ({name}): x {box[0]}..{box[2]}, y {box[1]}..{box[3]} mm, 10 px/mm (2.5 x the side-by-side)")
    print("wrote", os.path.join(HERE, "trial_gates.json"))


if __name__ == "__main__":
    main()
