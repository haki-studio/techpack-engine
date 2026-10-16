"""Collect stitch-file results -> dst_all.json (every grade) + dst_current.json (grade B = size M set), trims counted from
the DST read-back (LESSONS B8). Also checks the gates: max stitch ≤ 7.5, ≤ 15 threads, splits fit the frame."""
import json, os, collections
import pyembroidery as pe

def dst_count(base):
    p = pe.read(base + ".dst"); c = collections.Counter(s[2] & pe.COMMAND_MASK for s in p.stitches)
    return c[pe.TRIM], c[pe.STITCH]

allr = {"grades": {}, "splits": {}}; gates = []
for G in ("A", "B", "C"):
    p = f"dst_results_{G}.json"
    if os.path.exists(p):
        r = json.load(open(p))
        for k, v in r.items():
            v["trims_dst"], v["stitches_dst"] = dst_count(v["file"])
            gates.append((f"{G} {k}", v["max_stitch"] <= 7.5, v["threads"] <= 15))
        allr["grades"][G] = r
    p = f"dst_splits_{G}.json"
    if os.path.exists(p):
        s = json.load(open(p))
        for nm, v in s["sections"].items():
            v["trims_dst"], v["stitches_dst"] = dst_count(v["file"])
            gates.append((f"{G} {nm}", v["max_stitch"] <= 7.5 and v["fits"], True))
        allr["splits"][G] = s
json.dump(allr, open("dst_all.json", "w"), default=float, indent=1)
B = allr["grades"].get("B", {})
json.dump({k: B.get(k) for k in ("back", "02R", "02L")}, open("dst_current.json", "w"), default=float, indent=1)
if "B" in allr["splits"]: json.dump(allr["splits"]["B"], open("dst_current_splits.json", "w"), default=float, indent=1)
for G, r in allr["grades"].items():
    print(G, {k: (v["stitches"], v["trims_dst"], v["stops"], v["threads"], v["max_stitch"]) for k, v in r.items()})
for G, s in allr["splits"].items():
    print(G, "splits", {nm: (v["stitches"], v["trims_dst"], v["fits"]) for nm, v in s["sections"].items()})
bad = [g for g in gates if not (g[1] and g[2])]
print("GATES", "all pass" if not bad else bad, len(gates))
