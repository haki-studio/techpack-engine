"""LESSONS check for review item 12: no stitch on the welt line. For every size + front piece, read every stitch point of the
written full DST (and the split files) back into garment mm and measure the distance to that size's welt box. -> welt_check.json"""
import cccore, json
import numpy as np
import pyembroidery as pe
from shapely.geometry import MultiPoint
from shapely import distance as sdist, points
import front as F

def pts_of(base, origin):
    d = pe.read(base + ".dst"); ox, oy = origin
    a = np.array([(x/10.0 + ox, y/10.0 + oy) for x, y, c in d.stitches if (c & pe.COMMAND_MASK) == pe.STITCH])
    return a

out = {}
for sz in cccore.SIZES:
    for P, s in (("FR", "R"), ("FL", "L")):
        r = json.load(open(f"{cccore.edir(P)}/{sz}/result_{P}.json"))
        welt = F.keep_geoms(sz, s)["welt"]
        files = [("full", r["full"])] + list(r.get("splits", {}).get("sections", {}).items())
        res = {}
        for nm, fl in files:
            a = pts_of(fl["file"], fl["origin"])
            dmin = float(np.min(sdist(points(a), welt))) if len(a) else None
            res[nm] = round(dmin, 2)
        out.setdefault(sz, {})[P] = res
json.dump(out, open("welt_check.json", "w"), indent=1)
worst = min(v for sz in out for P in out[sz] for v in out[sz][P].values())
print({sz: {P: out[sz][P]["full"] for P in out[sz]} for sz in out}, "worst", worst, "PASS" if worst >= F.KEEP_WELT - 0.6 else "CHECK")
