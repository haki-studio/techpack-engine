"""Delivery gates on the WRITTEN stitch files (DST read-back), references from INPUT PIXELS only (LESSONS A14):
  - A14 motif_match per colour family: the render's own yellow / gold / black pixels (front.png -> garment mm) vs the
    DST's stop masks of that colour (own stops, near 0.3 mm); IoU >= 0.70, w/h >= 80 %.
  - exposed stitches at halo 0.35 (sherpa pull comp 0.30 + 0.05; ENGINE_NOTES 2) and at the house 0.25 (reported).
  - max stitch <= 7.5, threads <= factory needles (PES), trims / stitches / stops from the DST, machine minutes.
Writes out/stitch/gates_fl.json and prints the table."""
import json, pickle, math
import numpy as np
from shapely.geometry import box
from shapely.ops import unary_union
from shapely import wkt as W
import readback, factory, qa, mockmap as MM, pixels as PX

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

def run():
    art = pickle.load(open("out/art/art.pkl", "rb")); pl = json.load(open("out/art/placements.json"))["files"]
    prof = factory.load(); res = {}
    for F in FILES:
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
        rows = []
        for col, gl in refs.items():
            ref = raster(gl, bounds, PPM); own = [i for i, t in enumerate(stop_thread) if t == col]
            for r in qa.motif_match(ref, masks, PPM, out_stops=own, near_mm=0.3):
                r.update(colour=col, x_mm=round(r["x_mm"] + bounds[0], 1), y_mm=round(r["y_mm"] + bounds[1], 1)); rows.append(r)
        stop_geoms = [unary_union([W.loads(parts[pid]["wkt"]) for pid in s["parts"]]) for s in plan["stops"]]
        ex35 = qa.exposed_stitches(base + ".dst", org, stop_geoms, halo=0.35, min_mm=0.5, min_ex=0.3)
        ex25 = qa.exposed_stitches(base + ".dst", org, stop_geoms, halo=0.25, min_mm=0.5, min_ex=0.3)
        mins = factory.machine_hours(rb["stitches"], prof, trims=rb["trims"], colour_changes=rb["stops"] - 1) * 60
        res[F] = dict(piece=pl[F]["piece"], desc=pl[F]["desc"], stitches=rb["stitches"], trims=rb["trims"], stops=rb["stops"],
                      max_stitch=rb["max_stitch"], size_mm=rb["size_mm"], threads=th, needles=prof["needles"], per_stop=rb["per_stop"],
                      stop_threads=stop_thread, machine_min=round(mins, 1), motifs=rows,
                      motifs_pass=sum(r["ok"] for r in rows), motifs_n=len(rows), exposed_035=ex35, exposed_025=ex25,
                      trims_per_10k=round(rb["trims"] / max(rb["stitches"], 1) * 1e4, 1),
                      ok=bool(all(r["ok"] for r in rows) and not ex35 and rb["max_stitch"] <= 7.5 and th <= prof["needles"]))
    json.dump(res, open("out/stitch/gates_fl.json", "w"), indent=1, default=float)
    return res

if __name__ == "__main__":
    res = run()
    for F, r in res.items():
        print(F, r["piece"], f"{r['stitches']} st {r['trims']} trims {r['stops']} stops max {r['max_stitch']} threads {r['threads']}",
              f"motifs {r['motifs_pass']}/{r['motifs_n']} minIoU {min(m['iou'] for m in r['motifs']):.2f}",
              f"exposed@0.35 {len(r['exposed_035'])} @0.25 {len(r['exposed_025'])} {r['machine_min']} min", "PASS" if r["ok"] else "FAIL")
