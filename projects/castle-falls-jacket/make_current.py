"""Collect per-size results -> dst_all.json + dst_current.json (size M). Every count is re-read from the written DST
(readback.dst) so a stale json can never reach a page. Fields: stitches, trims (DST trims), jumps, stops, per_stop,
max_stitch, size_mm, threads."""
import cfcore
import json, os
import readback

def fresh(r):
    rb = readback.dst(r["file"] + ".dst")
    for ps, old in zip(rb["per_stop"], r.get("per_stop", [])):
        for k in ("col", "codes", "types", "objects"):
            if k in old: ps[k] = old[k]
    r.update(rb); r["colours"] = [ps.get("col") for ps in rb["per_stop"]]
    return r

def path(sz, P):
    e = cfcore.PIECE_ELEM[P]; return f"out/{e}_{cfcore.ELEMS[e][0]}/{sz}/result_{P}.json"

if __name__ == "__main__":
    allr = {}
    for sz in cfcore.SIZES:
        for P in cfcore.PIECES:
            p = path(sz, P)
            if not os.path.exists(p): continue
            r = json.load(open(p))
            if "full" not in r: continue
            fresh(r["full"])
            for s in r.get("splits", {}).get("sections", {}).values(): fresh(s)
            json.dump(r, open(p, "w"), default=float, indent=1)
            allr.setdefault(sz, {})[P] = r
    json.dump(allr, open("dst_all.json", "w"), default=float, indent=1)
    cur = {P: dict(allr["M"][P]["full"], splits=allr["M"][P].get("splits")) for P in cfcore.PIECES if P in allr.get("M", {})}
    json.dump(cur, open("dst_current.json", "w"), default=float, indent=1)
    for sz, d in allr.items():
        print(sz, {P: (v["full"]["stitches"], v["full"]["trims"], v["full"]["stops"], v["full"]["max_stitch"], v["full"]["threads"],
                       [(k, s["stitches"], s["trims"], s["fits"]) for k, s in v.get("splits", {}).get("sections", {}).items()]) for P, v in d.items()})
