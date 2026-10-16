"""Collect per-size stitch-file results -> dst_all.json (every size, piece, split) + dst_current.json (size M),
trims counted from the DST read-back (LESSONS B8). Also scene_meta.json for the page builders."""
import glcore
import json, os, pickle, collections
import pyembroidery as pe

def dst_counts(base):
    p = pe.read(base + ".dst"); c = collections.Counter(s[2] & pe.COMMAND_MASK for s in p.stitches)
    return dict(trims_dst=c[pe.TRIM], stitches_dst=c[pe.STITCH], colour_changes_dst=c[pe.COLOR_CHANGE])

allr = {}
for sz in glcore.SIZES:
    for P in glcore.PIECES:
        p = f"out/01_front-scene/{sz}/result_{P}.json"
        if not os.path.exists(p): continue
        r = json.load(open(p))
        if "full" in r: r["full"].update(dst_counts(r["full"]["file"]))
        if "splits" in r:
            for nm, s in r["splits"]["sections"].items(): s.update(dst_counts(s["file"]))
        allr.setdefault(sz, {})[P] = r
json.dump(allr, open("dst_all.json", "w"), default=float, indent=1)
cur = {P: dict(allr["M"][P]["full"], splits=allr["M"][P].get("splits")) for P in glcore.PIECES if P in allr.get("M", {})}
json.dump(cur, open("dst_current.json", "w"), default=float, indent=1)
meta = pickle.load(open("scene.pkl", "rb"))["meta"]
json.dump(meta, open("scene_meta.json", "w"), default=float, indent=1)
for sz, d in allr.items():
    print(sz, {P: (v["full"]["stitches"], v["full"]["trims_dst"], v["full"]["max_stitch"], len(v["full"]["colours"]),
                   [(k, s["stitches"], s["trims_dst"], s["fits"]) for k, s in v.get("splits", {}).get("sections", {}).items()]) for P, v in d.items()})
