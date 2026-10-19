"""Collect per-size results -> dst_all.json + dst_current.json (size M). Every count is the readback.dst() of the written
file (done in build_size.py, re-read here so a stale json can never reach a page). Field names say what they count."""
import wavecore as WC
import json, os
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
for sz in WC.DOC_SIZES:          # sampling package: size M only (other sizes follow after the strike-off)
    for P in WC.PIECES:
        p = f"out/01_wave/{sz}/result_{P}.json"
        if not os.path.exists(p): continue
        r = json.load(open(p)); fresh(r["full"])
        for s in r.get("splits", {}).get("sections", {}).values(): fresh(s)
        r["hoopings"] = len(r.get("splits", {}).get("sections", {})) or 1
        json.dump(r, open(p, "w"), default=float, indent=1)
        allr.setdefault(sz, {})[P] = r
json.dump(allr, open("dst_all.json", "w"), default=float, indent=1)
cur = {P: dict(allr["M"][P]["full"], splits=allr["M"][P].get("splits"), hoopings=allr["M"][P]["hoopings"]) for P in WC.PIECES if P in allr.get("M", {})}
json.dump(cur, open("dst_current.json", "w"), default=float, indent=1)
for sz, d in allr.items():
    print(sz, {P: (v["full"]["stitches"], v["full"]["trims"], v["full"]["stops"], v["full"]["max_stitch"], v["hoopings"]) for P, v in d.items()})
