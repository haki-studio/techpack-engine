"""CHENILLE foam file (factory 19 Oct: chenille available -> PRIMARY foam, matching the mockup's looped foam).
The foam crests (region code FM) are sewn on the chenille head after the lockstitch file of the same hooping, from the SAME
origin (no re-hooping, no extra registration):
  stop 1  Foam white  moss / loop fill: inward contour spirals 2.0 mm apart, 2.5 mm path stitches, one path per curl where
                      possible (the chenille head makes the loops; loop height + moss vs chain set at the machine)
  stop 2  Foam shade  chain-stitch curl cords: the one continuous spiral cord of every curl (A16: along the curl)
Paths only - the stitch TYPE is set on the chenille head (loop / moss for stop 1, chain for stop 2): factory to confirm
the format their chenille machine reads (DST path accepted by most; else the FM outlines in the ART.svg).
write(foam_regions, cord_regions, origin, base) -> readback dict"""
import math
import numpy as np
import pyembroidery as pe
from shapely.geometry import LineString, Point
import waveart as WA, readback
from motifs2 import HEX

SPACING = 1.8; STEP = 2.5; TRIM_GAP = 2.0; INSET = 0.6

def moss_paths(p):
    """inward contour spirals 1.8 mm apart (loop rows); a foam part too thin for a ring gets one row on its centre line"""
    out = []; got = 0.0
    for q in WA.polys(p.buffer(-INSET)):
        if q.area < 1.0: continue
        for ln in WA.ring_chain(q, SPACING): out.append(list(ln.simplify(0.2).coords)); got += q.area
    if got < 0.5 * p.area and p.area > 1.0:
        import dst2
        ln = dst2.centreline(p)
        if ln is not None and ln.length > 1.5: out.append(list(ln.coords))
    return out

def cord_path(p):
    import dst2
    ln = dst2.centreline(p) if p.area > 1.0 else None
    if ln is None: return [list(p.exterior.coords)]
    return [list(ln.coords)]

def resample(pts, L=STEP):
    ls = LineString(pts)
    if ls.length < 0.5: return pts[:1]
    n = max(1, int(math.ceil(ls.length / L)))
    return [ls.interpolate(i * ls.length / n).coords[0] for i in range(n + 1)]

def write(foam, cords, origin, base, cols=("w1", "w3")):
    ox, oy = origin; pat = pe.EmbPattern(); first = True
    groups = [(cols[0], [pt for r in foam for p in WA.polys(r["geom"]) for pt in moss_paths(p)]),
              (cols[1], [pt for r in cords for p in WA.polys(r["geom"]) for pt in cord_path(p)])]
    groups = [(c, ps) for c, ps in groups if ps]
    pos = None
    for gi, (col, paths) in enumerate(groups):
        th = pe.EmbThread(); th.set_hex_color(HEX[col]); th.description = col; pat.add_thread(th)
        if gi > 0: pat.add_command(pe.COLOR_CHANGE)
        # nearest-neighbour path order
        left = [resample(pth) for pth in paths if len(pth) > 1]
        while left:
            if pos is None: k = 0
            else:
                d = [min(math.dist(pos, q[0]), math.dist(pos, q[-1])) for q in left]; k = int(np.argmin(d))
                if math.dist(pos, left[k][-1]) < math.dist(pos, left[k][0]): left[k] = left[k][::-1]
            q = left.pop(k)
            if pos is not None and math.dist(pos, q[0]) > TRIM_GAP:
                pat.add_command(pe.TRIM)
                pat.add_stitch_absolute(pe.JUMP, (q[0][0] - ox) * 10, (q[0][1] - oy) * 10)
            for x, y in q: pat.add_stitch_absolute(pe.STITCH, (x - ox) * 10, (y - oy) * 10)
            pos = q[-1]
    pat.add_command(pe.END)
    import dst2
    dst2.write(pat, base)
    rb = readback.dst(base + ".dst"); rb["file"] = base; rb["origin"] = list(origin)
    for ps, (c, _) in zip(rb["per_stop"], groups): ps["col"] = c; ps["codes"] = ["FM chenille (loop/moss)" if c == cols[0] else "FM-curl chain"]
    rb["colours"] = [c for c, _ in groups]
    return rb
