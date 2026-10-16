"""Collect every production stitch file's numbers (DST/PES read-back) -> out/results/all.json + gate check
(max stitch ≤ 7.5, ≤ 15 threads, splits fit the 360² frame, every file present)."""
import json, os, drum
out = {"sizes": {}, "grades": {}}; bad = []
for sz in drum.SIZES:
    r = json.load(open(f"out/results/size_{sz}.json")); out["sizes"][sz] = r
    for k in ("back", "03L", "03R"):
        v = r[k]
        if v["max_stitch"] > 7.5 or v["threads"] > 15 or not os.path.exists(v["file"] + ".dst"): bad.append((sz, k, v["max_stitch"], v["threads"]))
    for nm, v in r["splits"]["sections"].items():
        if not v["fits"] or v["max_stitch"] > 7.5 or v["threads"] > 15: bad.append((sz, nm, v["size"], v["fits"]))
for G in "ABC":
    r = json.load(open(f"out/results/grade_{G}.json")); out["grades"][G] = r
    for k, v in r.items():
        if v["max_stitch"] > 7.5 or v["threads"] > 15: bad.append((G, k, v["max_stitch"]))
json.dump(out, open("out/results/all.json", "w"), default=float, indent=1)
for sz, r in out["sizes"].items():
    sp = r["splits"]
    print(f"{sz:4} back {r['back']['stitches']:>7,} st {r['back']['trims_dst']:>4} tr {r['back']['stops']:>2} stops {r['back']['threads']:>2} thr | 03L {r['03L']['stitches']:>6,}/{r['03L']['trims_dst']} | 03R {r['03R']['stitches']:>5,}/{r['03R']['trims_dst']} | splits {sp['grid']} {len(sp['sections'])} box→{sp['box_section']}")
for G, r in out["grades"].items():
    print(G, {k: (v["stitches"], v["trims_dst"], v["stops"], v["threads"], v["size"]) for k, v in r.items()})
print("GATE FAILS:", bad or "none")
