"""Collect the v3 stitch-file results into dst_current.json (size M set: back + sleeve per size, fronts grade B)
and dst_all.json (every size / grade), with trims counted from the DST read-back (LESSONS B8)."""
import json, os, collections
import pyembroidery as pe

def dst_trims(base):
    p = pe.read(base + ".dst"); return collections.Counter(s[2] & pe.COMMAND_MASK for s in p.stitches)[pe.TRIM]

SIZES = ["XS", "S", "M", "L", "XL", "XXL", "3XL"]
allr = {"sizes": {}, "grades": {}}
for sz in SIZES:
    p = f"out/01_back-scene/v3_by-size/{sz}/result.json"
    if not os.path.exists(p): continue
    r = json.load(open(p))
    for k in ("back", "sleeve"):
        if k in r: r[k]["trims_dst"] = dst_trims(r[k]["file"])
    if "splits" in r:
        for nm, s in r["splits"]["sections"].items(): s["trims_dst"] = dst_trims(s["file"])
    allr["sizes"][sz] = r
for G in ("A", "B", "C"):
    p = f"dst3_results_{G}.json"
    if not os.path.exists(p): continue
    r = json.load(open(p)); out = {}
    for k in ("02R", "02L", "03", "04"):
        if k in r: out[k] = dict(r[k], trims_dst=dst_trims(r[k]["file"]))
    allr["grades"][G] = out
json.dump(allr, open("dst_all.json", "w"), default=float, indent=1)
M = allr["sizes"].get("M", {}); B = allr["grades"].get("B", {})
cur = {"back": M.get("back"), "sleeve": M.get("sleeve"), **{k: B.get(k) for k in ("02R", "02L", "03", "04")}}
json.dump(cur, open("dst_current.json", "w"), default=float, indent=1)
if M.get("splits"): json.dump(M["splits"], open("dst_current_splits.json", "w"), default=float, indent=1)
print({k: (v["stitches"], v["trims_dst"]) for k, v in cur.items() if v})
print({sz: (r["back"]["stitches"], r["back"]["trims_dst"], r["sleeve"]["stitches"]) for sz, r in allr["sizes"].items() if "back" in r})
