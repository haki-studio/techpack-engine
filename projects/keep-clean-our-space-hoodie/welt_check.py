"""Welt keep-out measured on the STITCHES (not the art): nearest sewn stitch of every front file (full + split sections, every
size) to that size's drafted welt box (hoodie block + this mockup's welt override). -> welt_check.json {size: {file: mm}}.
usage: python3 welt_check.py"""
import kccore
import json, glob, os
import numpy as np
from shapely import distance as sdist, points as spoints
import front as F, dstview as DV

out = {}
for sz in kccore.SIZES:
    out[sz] = {}
    for P, side in (("FR", "R"), ("FL", "L")):
        welt = F.keep_geoms(sz, side)["welt"]
        bases = [f"out/stitch/{sz}/HAKI_{kccore.SHORT}_{P}_{sz}"] + sorted(p[:-4] for p in glob.glob(f"out/stitch/{sz}/splits/HAKI_{kccore.SHORT}_{P}_{sz}_*.dst"))
        for b in bases:
            pts = np.array([q for _, run in DV.strokes(b) for q in run])
            out[sz][os.path.basename(b)] = round(float(sdist(welt, spoints(pts[:, 0], pts[:, 1])).min()), 2)
json.dump(out, open("welt_check.json", "w"), indent=1)
w = min(v for d in out.values() for v in d.values())
print("nearest stitch to a welt box, all sizes + files:", w, "mm (keep-out", F.KEEP_WELT, ")")
