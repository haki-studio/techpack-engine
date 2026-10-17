"""Collect per-size results -> dst_all.json + dst_current.json (size M). Every count is re-read from the written DST
(readback.dst) so a stale json can never reach a page (LESSONS B20, D3)."""
import rbcore
import json, os
import readback

def fresh(r):
    rb = readback.dst(r["file"] + ".dst")
    for ps, old in zip(rb["per_stop"], r.get("per_stop", [])):
        for k in ("col", "codes", "types", "objects"):
            if k in old: ps[k] = old[k]
    r.update(rb); r["colours"] = [ps.get("col") for ps in rb["per_stop"]]
    return r

allr = {}
for sz in rbcore.SIZES:
    for P in rbcore.PIECES:
        p = f"{rbcore.outdir(P, sz)}/result_{P}.json"
        if not os.path.exists(p): continue
        r = json.load(open(p)); fresh(r["full"])
        for s in r.get("splits", {}).get("sections", {}).values(): fresh(s)
        json.dump(r, open(p, "w"), default=float, indent=1)
        allr.setdefault(sz, {})[P] = r
json.dump(allr, open("dst_all.json", "w"), default=float, indent=1)
cur = {P: dict(allr["M"][P]["full"], splits=allr["M"][P].get("splits")) for P in rbcore.PIECES if P in allr.get("M", {})}
json.dump(cur, open("dst_current.json", "w"), default=float, indent=1)
for sz, d in allr.items():
    print(sz, {P: (v["full"]["stitches"], v["full"]["trims"], v["full"]["stops"], v["full"]["max_stitch"], v["full"]["threads"],
                   [(k, s["stitches"], s["trims"], s["fits"]) for k, s in v.get("splits", {}).get("sections", {}).items()]) for P, v in d.items()})
