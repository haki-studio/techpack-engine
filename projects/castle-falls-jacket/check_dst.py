"""Keep-out check on the STITCH FILES (not the art): every sewn stitch of every full file, read back from the DST and placed
on that size's pattern piece by the file origin, must clear every keep-out line by its minimum (- 0.5 mm for pull comp).
Found 16 Oct: FR art outline passed while FR files from an earlier art build had ~11k stitches inside the welt keep-out.
usage: python3 check_dst.py [sizes...]  -> prints offenders per size/piece; exit 1 if any."""
import cfcore
import json, sys
import pyembroidery as pe
from shapely.geometry import MultiPoint
from shapely.prepared import prep
import keepout as KO, make_current as MC

def offenders(size, P, tol=0.5):
    r = json.load(open(MC.path(size, P)))["full"]; ox, oy = r["origin"]
    import numpy as np, shapely
    a = np.array([(x / 10 + ox, y / 10 + oy) for x, y, c in pe.read(r["file"] + ".dst").stitches if (c & pe.COMMAND_MASK) == pe.STITCH])
    pts = a
    out = {}
    for nm, (geo, d) in KO.lines(size, P).items():
        z = geo.buffer(max(0.0, d - tol)); shapely.prepare(z)
        n = int(shapely.contains_xy(z, a[:, 0], a[:, 1]).sum())
        if n: out[nm] = n
    return out, len(pts)

if __name__ == "__main__":
    bad = False
    for sz in [a for a in sys.argv[1:] if a in cfcore.SIZES] or cfcore.SIZES:
        row = {}
        for P in cfcore.PIECES:
            o, n = offenders(sz, P); row[P] = o or "ok"; bad |= bool(o)
        print(sz, row, flush=True)
    print("DST KEEP-OUTS FAIL" if bad else "DST KEEP-OUTS PASS (every stitch of every file)")
    sys.exit(1 if bad else 0)
