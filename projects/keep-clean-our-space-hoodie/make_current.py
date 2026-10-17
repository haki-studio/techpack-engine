"""Collect per-size results -> dst_all.json + dst_current.json (size M). Every count is re-read from the written DST
(readback.dst) so a stale json can never reach a page (LESSONS B20). Field names say what they count."""
import kccore
import json, os, pickle
import readback

def fresh(r):
    rb = readback.dst(r["file"] + ".dst")
    for ps, old in zip(rb["per_stop"], r.get("per_stop", [])):
        for k in ("col", "codes", "types", "objects", "elements", "puff", "top"):
            if k in old: ps[k] = old[k]
    r.update(rb); r["colours"] = [ps.get("col") for ps in rb["per_stop"]]
    return r

allr = {}
for sz in kccore.SIZES:
    for P in kccore.PIECES:
        p = f"out/stitch/{sz}/result_{P}.json"
        if not os.path.exists(p): continue
        r = json.load(open(p))
        if "full" not in r: continue
        fresh(r["full"])
        for s in r.get("splits", {}).get("sections", {}).values(): fresh(s)
        json.dump(r, open(p, "w"), default=float, indent=1)
        allr.setdefault(sz, {})[P] = r
json.dump(allr, open("dst_all.json", "w"), default=float, indent=1)
cur = {P: dict(allr["M"][P]["full"], splits=allr["M"][P].get("splits")) for P in kccore.PIECES if P in allr.get("M", {})}
json.dump(cur, open("dst_current.json", "w"), default=float, indent=1)
meta = pickle.load(open("scene.pkl", "rb"))["meta"]
json.dump(meta, open("scene_meta.json", "w"), default=float, indent=1)
for sz, d in allr.items():
    print(sz, {P: (v["full"]["stitches"], v["full"]["trims"], v["full"]["stops"], v["full"]["max_stitch"], v["full"]["threads"],
                   [(k, s["stitches"], s["trims"], s["fits"]) for k, s in v.get("splits", {}).get("sections", {}).items()]) for P, v in d.items()})
