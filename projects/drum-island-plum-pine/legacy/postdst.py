"""Count trims as a machine reads them back from each DST (same method as the v1 baseline)."""
import json, glob, collections, pyembroidery as pe
def dst_trims(f):
    p = pe.read(f); return collections.Counter(s[2] & pe.COMMAND_MASK for s in p.stitches)[pe.TRIM]
N = {"back": "01_back-scene/HAKI_jacket_01_back-scene_BACK_v2", "sleeve": "01_back-scene/HAKI_jacket_01_back-scene_SLEEVE_v2",
     "02R": "02_chest-branch/HAKI_jacket_02_chest-branch_02R_v2", "02L": "02_chest-branch/HAKI_jacket_02_chest-branch_02L_v2",
     "03": "03_chest-pine/HAKI_jacket_03_chest-pine_v2", "04": "04_lower-bamboo/HAKI_jacket_04_lower-bamboo_v2"}
r = json.load(open("dst2_results.json"))
for k, b in N.items(): r[k]["trims_dst"] = dst_trims(f"out/{b}.dst")
json.dump(r, open("dst2_results.json", "w"), default=float, indent=1)
s = json.load(open("dst2_splits.json"))
for nm in s["sections"]: s["sections"][nm]["trims_dst"] = dst_trims(f"out/01_back-scene/splits/HAKI_jacket_01_back-scene_{nm}.dst")
json.dump(s, open("dst2_splits.json", "w"), default=float, indent=1)
print({k: (r[k]["stitches"], r[k]["trims_dst"]) for k in N}, {k: (v["stitches"], v["trims_dst"]) for k, v in s["sections"].items()})
