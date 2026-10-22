"""Orphan fragments: a tiny stitch block sewn in a DIFFERENT pass from a bigger block of the SAME thread that it touches
(e.g. a flat sliver sewn after the foam next to its puffed letter). Usage: orphans.py file.pes ..."""
import sys, pyembroidery as pe
from shapely.geometry import LineString, MultiPoint
def blocks(fn):
    p = pe.read(fn); cols = [t.hex_color() for t in p.threadlist]; ci = 0; out = []; cur = []
    def flush():
        nonlocal cur
        if len(cur) > 1: out.append((ci, cols[min(ci, len(cols)-1)], cur))
        cur = []
    for x, y, c in p.stitches:
        k = c & pe.COMMAND_MASK
        if k == pe.STITCH: cur.append((x/10, y/10))
        elif k == pe.COLOR_CHANGE: flush(); ci += 1
        elif k in (pe.TRIM, pe.JUMP): flush()
    flush(); return out
for fn in sys.argv[1:]:
    B = blocks(fn); G = [(s, c, MultiPoint(pts).convex_hull, len(pts)) for s, c, pts in B]
    hits = []
    for i, (s, c, g, n) in enumerate(G):
        if n > 60 or max(g.bounds[2]-g.bounds[0], g.bounds[3]-g.bounds[1]) > 8: continue
        for j, (s2, c2, g2, n2) in enumerate(G):
            if j != i and s2 != s and c2.lower() == c.lower() and n2 > 3*n and g.distance(g2) < 0.3:
                hits.append((s+1, c, n, round(g.centroid.x,1), round(g.centroid.y,1))); break
    print(f"{len(hits):4d}  {fn}")
