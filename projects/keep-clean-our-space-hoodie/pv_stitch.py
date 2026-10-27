"""Rev K pullover: one production stitch file per hooping (the cells of pv_art's hoop plan), same stitch engine and stop
rules as kcstitch.py (flat stops, PAUSE for 3 mm foam, puff stops, details on top). Nothing crosses a split, so no
section is clipped and no registration crosses are needed; each file's origin is its art centre, given in garment mm.
usage: python3 pv_stitch.py [SIZE] [allover|zoned] [PIECE ...]  -> out/pv/<SIZE>/stitch_<tag>/  + result_<tag>.json
Every number written comes from the DST read back (readback.dst, LESSONS B8/B20)."""
import kccore
import sys, os, json, pickle, time
from shapely.ops import unary_union
import tech, readback, factory
import pv_block as B
dst2 = kccore.patch_dst2()

SIZE = next((a for a in sys.argv[1:] if a in B.CHART), "M")
TAG = "zoned" if "zoned" in sys.argv else "allover"
OUT = f"out/pv/{SIZE}"; SD = f"{OUT}/stitch_{TAG}"; os.makedirs(SD, exist_ok=True)
A = pickle.load(open(f"{OUT}/art_{TAG}.pkl", "rb"))
which = [a for a in sys.argv[1:] if a in A["cut"]] or list(A["cut"])
EXACT = dict(halo=0.25, max_ex=0.5)

def is_puff(r): return tech.rule_for(r["grp"]).startswith("PF-") and kccore.PUFF
def is_top(r): return r["layer"] >= 30 and not is_puff(r) and r["el"] != "07"
def stops_for(vis):
    blocks = [[r for r in vis if not is_puff(r) and not is_top(r)], [r for r in vis if is_puff(r)], [r for r in vis if is_top(r)]]
    out = []
    for bi, rs in enumerate(blocks):
        if not rs: continue
        st = dst2.merge_stops(tech.stops(rs))
        for s in st: s["puff"] = bi == 1; s["top"] = bi == 2
        out += st
    return out

rp = f"{OUT}/result_{TAG}_{'-'.join(which)}.json"
res = json.load(open(rp)) if os.path.exists(rp) else {}
for P in which:
    for i, rs in sorted(A["assign"].get(P, {}).items()):
        name = f"HAKI_KCOS-PO_{P}-H{i+1}_{SIZE}"; t = time.time()
        vis = dst2.merge_colours(rs)
        ub = dst2.bounds_of([r["geom"] for r in vis]); c = ((ub[0] + ub[2]) / 2, (ub[1] + ub[3]) / 2)
        stops = stops_for(vis); pat, st = dst2.make_pattern(vis, stops, c, exact_travel=EXACT)
        base = f"{SD}/{name}"; dst2.write(pat, base); dst2.render(base, base + "_preview.png", bg=(25, 28, 36), s=0.5)
        rb = readback.dst(base + ".dst"); rb["threads"] = factory.check_threads(base + ".pes")
        puff = [k + 1 for k, s in enumerate(stops) if s.get("puff")]
        cell = A["plan"][P][i]["box"]
        rb.update(piece=P, hooping=i + 1, cell_mm=[round(v, 1) for v in cell], origin_mm=[round(v, 1) for v in c], art_box=[round(v, 1) for v in ub],
                  elements=sorted({r["el"] for r in rs}), stars=len({r["unit"] for r in rs if r["el"] == "05"}),
                  foam_pause_before_stop=puff[0] if puff else None, secs=round(time.time() - t), file=base)
        rb["machine_min"] = round(60 * factory.machine_hours(rb["stitches"], trims=rb["trims"], colour_changes=max(0, rb["stops"] - 1)), 1)
        res[f"{P}-H{i+1}"] = rb
        json.dump(res, open(rp, "w"), default=float, indent=1)
        print(name, {k: rb[k] for k in ("stitches", "trims", "stops", "size_mm", "max_stitch", "machine_min")}, f"{rb['secs']}s", flush=True)
print("DONE", SIZE, TAG, which, flush=True)
