"""Delivery gates on the WRITTEN stitch files (DST read-back), references from INPUT PIXELS only (LESSONS A14):
  - A14 motif_match per colour family: the render's own yellow / gold / black pixels (front.png -> garment mm) vs the
    DST's stop masks of that colour (own stops, near 0.3 mm); IoU >= 0.70, w/h >= 80 %.
  - exposed stitches at halo 0.35 (sherpa pull comp 0.30 + 0.05; ENGINE_NOTES 2) and at the house 0.25 (reported).
  - max stitch <= 7.5, threads <= factory needles (PES), trims / stitches / stops from the DST, machine minutes.
  - colour per motif (PR #28 review): every motif region of the RENDER (yellow/gold/black pixels, own components)
    gets its expected thread from the render's core pixels (g/r < 0.93 = gold; black = bird) and the stitched thread =
    the stop covering most of it in the DST. Mismatch = FAIL (the A14 shape rows alone passed a gold sparkle sewn yellow).
  - A15 qa.uncovered: render motif coverage vs DST coverage, every gap >= 25 mm2 listed (none allowed unexplained).
  - A16 qa.angle_coherence on every plan part (all kinds treated as constructed: pixel art), measured on the VISIBLE
    DST stitches attributed to each part (stitch_parts.npz) -> undeclared-angle / satin-on-blob / angle-spread /
    no-visible-stitches rows; [] = pass.
  - A16/A17 qa.direction_match on the visible layer at 12 ppm: the CHAOS half is judged (R < 0.55 tiles, <= 5 %);
    the reference-grain half is NOT judgeable here (no close-up; the 0.6 mm/px render shows pile curls, not thread
    grain), so every tile is reported "not judged vs reference" - never as pass.
Writes out/stitch/gates_fl.json and prints the table."""
import json, pickle, math
import numpy as np
from shapely.geometry import box
from shapely.ops import unary_union
from shapely import wkt as W
import readback, factory, qa, mockmap as MM, pixels as PX
from scipy import ndimage as ndi

GOLD_GR, CORE_B, CORE_R = 0.93, 110, 195          # same render colour rule as emb_art (core pixels only)

def render_motifs(bounds, ppm, fid):
    """render motif regions inside `bounds` (garment mm, FRONT coords): [(mask on the bounds grid, expected colour)].
    Built from the render's class labels only (yellow/gold, black in the bird box), never from the art."""
    lab = PX.labels(); a = MM.img(); out = []
    x0, y0, x1, y1 = bounds; Wd, Hd = int((x1 - x0) * ppm) + 1, int((y1 - y0) * ppm) + 1
    for fam in ("spark", "black"):
        m = np.isin(lab, [PX.YELLOW, PX.GOLD]) if fam == "spark" else (lab == PX.BLACK)
        m = ndi.binary_closing(m, iterations=1)
        L, n = ndi.label(m)
        for k in range(1, n + 1):
            ys, xs = np.nonzero(L == k)
            if len(ys) < (50 if fam == "spark" else 400): continue
            if fam == "spark" and xs.mean() < 400 and ys.mean() > 1000: continue
            gx, gy = MM.P(xs + 0.5, ys + 0.5)
            if not (x0 < gx.mean() < x1 and y0 < gy.mean() < y1): continue
            if fam == "black": col = "black"
            else:
                p = a[ys, xs]; core = (p[:, 2] < CORE_B) & (p[:, 0] > CORE_R)
                if core.sum() < 8: core = p[:, 2] <= np.percentile(p[:, 2], 30)
                gr = p[core, 1] / np.maximum(p[core, 0], 1); col = "gold" if np.median(gr) < GOLD_GR else "yellow"
                # two touching sparkles of different colours: one region per colour (nearest core pixel)
                if min((gr < GOLD_GR).sum(), (gr >= GOLD_GR).sum()) >= max(15, 0.15 * core.sum()):
                    from scipy.spatial import cKDTree
                    ci = np.nonzero(core)[0]; _, nn = cKDTree(np.c_[xs[ci], ys[ci]]).query(np.c_[xs, ys])
                    isg = (gr < GOLD_GR)[nn]
                    for cc, sel in (("gold", isg), ("yellow", ~isg)):
                        sub = np.zeros(lab.shape, bool); sub[ys[sel], xs[sel]] = True
                        yy, xx = np.nonzero(ndi.binary_opening(sub, iterations=1))
                        if len(yy) >= 25: out.append((_px_mask(xx, yy, bounds, ppm, (Hd, Wd)), cc))
                    continue
            out.append((_px_mask(xs, ys, bounds, ppm, (Hd, Wd)), col))
    return out

def _px_mask(xs, ys, bounds, ppm, shape):
    M = np.zeros(shape, bool); h = MM.S / 2
    gx, gy = MM.P(xs + 0.5, ys + 0.5)
    for x, y in zip(gx, gy):
        i0, j0 = int((x - h - bounds[0]) * ppm), int((y - h - bounds[1]) * ppm); k = int(np.ceil(MM.S * ppm)) + 1
        M[max(j0, 0):j0 + k, max(i0, 0):i0 + k] = True
    return M

FILES = ["E1", "E2", "E3", "E1B"]
PPM = 10.0

def bird_ref():
    lab = PX.labels(); ys, xs = np.nonzero(lab == PX.BLACK)
    gx, gy = MM.P(xs + 0.5, ys + 0.5)
    return unary_union([box(x - MM.S / 2, y - MM.S / 2, x + MM.S / 2, y + MM.S / 2) for x, y in zip(gx, gy)]).buffer(0)

def raster(geoms, bounds, ppm):
    from PIL import Image, ImageDraw
    x0, y0, x1, y1 = bounds; Wd, Hd = int((x1 - x0) * ppm) + 1, int((y1 - y0) * ppm) + 1
    im = Image.new("L", (Wd, Hd), 0); d = ImageDraw.Draw(im)
    for g in geoms:
        for q in (g.geoms if hasattr(g, "geoms") else [g]):
            d.polygon([((x - x0) * ppm, (y - y0) * ppm) for x, y in q.exterior.coords], fill=255)
            for h in q.interiors: d.polygon([((x - x0) * ppm, (y - y0) * ppm) for x, y in h.coords], fill=0)
    return np.array(im) > 0

def run(files=FILES, mutate=None, write=True):
    """mutate (gates_selftest.py, red-then-green): 'swap_threads' (yellow<->gold on the stops), 'drop_stop' (erase the
    last stop's stitches from the masks), 'auto_angle' (first part's angle undeclared)"""
    art = pickle.load(open("out/art/art.pkl", "rb")); pl = json.load(open("out/art/placements.json"))["files"]
    prof = factory.load(); res = {}
    for F in files:
        base = f"out/stitch/{F}/HK-FL-PIXSKY_{F}"; rbj = json.load(open(f"out/stitch/{F}/readback.json"))
        plan = json.load(open(f"out/stitch/{F}/plan.json")); parts = {p["id"]: p for p in plan["parts"]}
        so = pl[F]["svg_origin"]; org = rbj["origin"]
        to_g = lambda x, y: (x + so[0], y + so[1])                         # plan (svg) mm -> garment mm
        rb = readback.dst(base + ".dst"); th = factory.check_threads(base + ".pes", prof)
        # references from the render pixels, per colour
        refs = {}
        for col, geom, ref in art[F]:
            if col == "black": ref = bird_ref()
            refs.setdefault(col, []).append(ref)
        U = unary_union([g for v in refs.values() for g in v] + [geom for _, geom, _ in art[F]])
        b = U.bounds; bounds = (b[0] - 5, b[1] - 5, b[2] + 5, b[3] + 5)
        shape = raster([], bounds, PPM).shape
        masks = qa.dst_stop_masks(base + ".dst", org, shape, PPM, to_mm=lambda x, y: (to_g(x, y)[0] - bounds[0], to_g(x, y)[1] - bounds[1]))
        stop_thread = [s["thread"] for s in plan["stops"]]
        if mutate == "swap_threads": stop_thread = [{"yellow": "gold", "gold": "yellow"}.get(t, t) for t in stop_thread]
        if mutate == "drop_stop": masks[max(masks)] = np.zeros_like(masks[max(masks)])
        rows = []
        for col, gl in refs.items():
            ref = raster(gl, bounds, PPM); own = [i for i, t in enumerate(stop_thread) if t == col]
            for r in qa.motif_match(ref, masks, PPM, out_stops=own, near_mm=0.3):
                r.update(colour=col, x_mm=round(r["x_mm"] + bounds[0], 1), y_mm=round(r["y_mm"] + bounds[1], 1)); rows.append(r)
        stop_geoms = [unary_union([W.loads(parts[pid]["wkt"]) for pid in s["parts"]]) for s in plan["stops"]]
        ex35 = qa.exposed_stitches(base + ".dst", org, stop_geoms, halo=0.35, min_mm=0.5, min_ex=0.3)
        ex25 = qa.exposed_stitches(base + ".dst", org, stop_geoms, halo=0.25, min_mm=0.5, min_ex=0.3)
        # ---- colour per motif + A15 uncovered (render motif regions vs DST). E3 is on the sleeve pattern (motifs moved
        # one by one), so A15 there uses the moved render pixels (art refs) and colour is matched motif by motif
        colour_rows, unc = [], []
        if F != "E3":
            regs = render_motifs(bounds, PPM, F)
            for M, exp in regs:
                cover = {stop_thread[i]: int((masks[i] & M).sum()) for i in masks if i < len(stop_thread)}
                tot = {}
                for i in masks:
                    if i < len(stop_thread): tot[stop_thread[i]] = tot.get(stop_thread[i], 0) + int((masks[i] & M).sum())
                got = max(tot, key=tot.get) if tot and max(tot.values()) > 0 else None
                ys_, xs_ = np.nonzero(M)
                colour_rows.append(dict(x_mm=round(xs_.mean() / PPM + bounds[0], 1), y_mm=round(ys_.mean() / PPM + bounds[1], 1),
                                        expected=exp, stitched=got, ok=bool(got == exp)))
            ref_all = np.any([M for M, _ in regs], axis=0) if regs else np.zeros(shape, bool)
            out_all = np.any([masks[i] for i in masks], axis=0)
            unc = [dict(r, x_mm=round(r["x_mm"] + bounds[0], 1), y_mm=round(r["y_mm"] + bounds[1], 1)) for r in qa.uncovered(ref_all, out_all, PPM)]
        else:
            # sleeve: each motif's expected colour from ITS render region (front px, by the placements report), the
            # stitched colour from the stops covering its traced pixels moved onto the sleeve (art ref)
            sp_rep = [r for r in json.load(open("out/art/placements.json"))["sparkles"] if r["file"] == F]
            for (col_art, geom, ref), rep in zip(art[F], sp_rep):
                cx, cy = MM.P(rep["render_px"][0], rep["render_px"][1]); rb_ = (cx - 12, cy - 12, cx + 12, cy + 12)
                regs = render_motifs(rb_, 4.0, F)
                hit = [(M.sum(), c) for M, c in regs]
                exp = max(hit)[1] if hit else None
                Mref = raster([ref], bounds, PPM); tot = {}
                for i in masks:
                    if i < len(stop_thread): tot[stop_thread[i]] = tot.get(stop_thread[i], 0) + int((masks[i] & Mref).sum())
                got = max(tot, key=tot.get) if tot and max(tot.values()) > 0 else None
                c_ = ref.centroid
                colour_rows.append(dict(x_mm=round(c_.x, 1), y_mm=round(c_.y, 1), expected=exp, stitched=got, ok=bool(got == exp)))
            ref_all = raster([r for _, _, r in art[F]], bounds, PPM); out_all = np.any([masks[i] for i in masks], axis=0)
            unc = [dict(r, x_mm=round(r["x_mm"] + bounds[0], 1), y_mm=round(r["y_mm"] + bounds[1], 1)) for r in qa.uncovered(ref_all, out_all, PPM)]
        # ---- A16 angle coherence on the plan parts, visible stitches attributed per part
        z = np.load(f"out/stitch/{F}/stitch_parts.npz", allow_pickle=True)
        segs_p = [tuple(v) for v in z["segs"]]; sp = list(z["parts"])
        pb = unary_union([W.loads(p["wkt"]) for p in plan["parts"]]).bounds; cb = (pb[0] - 2, pb[1] - 2, pb[2] + 2, pb[3] + 2)
        vis, ix = qa.visible_segments(segs_p, cb, ppm=12.0, return_index=True)
        regions = [dict(geom=W.loads(p["wkt"]), stype=p["technique"], angle=p["dir"]["angle"], grp=p["kind"], part=p["id"]) for p in plan["parts"]]
        if mutate == "auto_angle": regions[0]["angle"] = "auto"
        ac = qa.angle_coherence(regions, groups=tuple({p["kind"] for p in plan["parts"]}), segs=vis, seg_parts=[sp[i] for i in ix])
        # ---- A16/A17 direction: chaos half on the visible layer (flat reference = no grain to compare against)
        dsegs = [(a - cb[0], b - cb[1], c - cb[0], d - cb[1]) for a, b, c, d in qa.dst_segments(base + ".dst", (org[0], org[1]))]
        flat = np.full((int((cb[3] - cb[1]) * 12) + 1, int((cb[2] - cb[0]) * 12) + 1), 128.0)
        dm = qa.direction_match(flat, 12.0, dsegs)
        direction = dict(tiles=dm["tiles"], chaos_tiles=len(dm["fail_chaos"]), pct_chaos=dm["pct_chaos"], fail_chaos=dm["fail_chaos"],
                         vs_reference="not judged: no close-up; the 0.6 mm/px render shows pile curls, not thread grain",
                         declared="tatami 0 deg per motif (pixel rows), declared in the run yaml", ok=bool(dm["pct_chaos"] <= 5.0))
        mins = factory.machine_hours(rb["stitches"], prof, trims=rb["trims"], colour_changes=rb["stops"] - 1) * 60
        res[F] = dict(piece=pl[F]["piece"], desc=pl[F]["desc"], stitches=rb["stitches"], trims=rb["trims"], stops=rb["stops"],
                      max_stitch=rb["max_stitch"], size_mm=rb["size_mm"], threads=th, needles=prof["needles"], per_stop=rb["per_stop"],
                      stop_threads=stop_thread, machine_min=round(mins, 1), motifs=rows,
                      motifs_pass=sum(r["ok"] for r in rows), motifs_n=len(rows), exposed_035=ex35, exposed_025=ex25,
                      colour=colour_rows, colour_ok=all(r["ok"] for r in colour_rows), uncovered=unc,
                      coherence=ac, coherence_parts=len(regions), direction=direction,
                      trims_per_10k=round(rb["trims"] / max(rb["stitches"], 1) * 1e4, 1),
                      ok=bool(all(r["ok"] for r in rows) and not ex35 and rb["max_stitch"] <= 7.5 and th <= prof["needles"]
                              and all(r["ok"] for r in colour_rows) and not unc and not ac and direction["ok"]))
    if write: json.dump(res, open("out/stitch/gates_fl.json", "w"), indent=1, default=float)
    return res

if __name__ == "__main__":
    res = run()
    for F, r in res.items():
        print(F, r["piece"], f"{r['stitches']} st {r['trims']} trims {r['stops']} stops max {r['max_stitch']} threads {r['threads']}",
              f"motifs {r['motifs_pass']}/{r['motifs_n']} minIoU {min(m['iou'] for m in r['motifs']):.2f}",
              f"exposed@0.35 {len(r['exposed_035'])} @0.25 {len(r['exposed_025'])} {r['machine_min']} min",
              f"colour {sum(c['ok'] for c in r['colour'])}/{len(r['colour'])} A15 gaps {len(r['uncovered'])} coherence fails {len(r['coherence'])}/{r['coherence_parts']} parts",
              f"chaos {r['direction']['chaos_tiles']}/{r['direction']['tiles']} tiles", "PASS" if r["ok"] else "FAIL")
        for c in r["colour"]:
            if not c["ok"]: print("   colour FAIL", c)
        for u in r["uncovered"]: print("   A15 gap", u)
        for a in r["coherence"]: print("   coherence", a)
        for m in r["motifs"]:
            if not m["ok"]: print("   A14 FAIL", m)
