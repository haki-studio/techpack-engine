"""Collect per-size results -> dst_all.json + dst_current.json (size M). Every count is the readback.dst() of the written
file (done in build_size.py, re-read here so a stale json can never reach a page). Field names say what they count:
stitches, trims (DST trims), jumps, stops, per_stop, max_stitch, size_mm."""
import glcore
import json, os, pickle
import readback

def fresh(r):
    rb = readback.dst(r["file"] + ".dst")
    for ps, old in zip(rb["per_stop"], r.get("per_stop", [])):
        for k in ("col", "codes", "types", "objects"):
            if k in old: ps[k] = old[k]
    r.update(rb); r["colours"] = [ps.get("col") for ps in rb["per_stop"]]
    for k in ("trims_cmd", "trims_dst", "size"): r.pop(k, None)
    return r

allr = {}
for sz in glcore.SIZES:
    for P in glcore.PIECES:
        p = f"out/01_front-scene/{sz}/result_{P}.json"
        if not os.path.exists(p): continue
        r = json.load(open(p)); fresh(r["full"])
        for s in r.get("splits", {}).get("sections", {}).values(): fresh(s)
        json.dump(r, open(p, "w"), default=float, indent=1)
        allr.setdefault(sz, {})[P] = r
json.dump(allr, open("dst_all.json", "w"), default=float, indent=1)
cur = {P: dict(allr["M"][P]["full"], splits=allr["M"][P].get("splits")) for P in glcore.PIECES if P in allr.get("M", {})}
json.dump(cur, open("dst_current.json", "w"), default=float, indent=1)
json.dump(pickle.load(open("scene.pkl", "rb"))["meta"], open("scene_meta.json", "w"), default=float, indent=1)
for sz, d in allr.items():
    print(sz, {P: (v["full"]["stitches"], v["full"]["trims"], v["full"]["stops"], v["full"]["max_stitch"],
                   [(k, s["stitches"], s["trims"], s["fits"]) for k, s in v.get("splits", {}).get("sections", {}).items()]) for P, v in d.items()})
