import glcore, pickle
import pyembroidery as pe, tech
dst2 = glcore.patch_dst2()
from shapely.ops import unary_union
D = pickle.load(open("front_M.pkl", "rb")); vis = dst2.merge_colours(D["FR"])
st = tech.stops(vis); st = dst2.merge_stops(st)
ub = unary_union([r["geom"] for r in vis]).bounds; c = ((ub[0]+ub[2])/2, (ub[1]+ub[3])/2)
pat, s = dst2.make_pattern(vis, st, c)
counts = [0]; seq = []
for x, y, cmd in pat.stitches:
    k = cmd & pe.COMMAND_MASK
    if k == pe.COLOR_CHANGE: counts.append(0)
    elif k == pe.STITCH: counts[-1] += 1
print(len(st), len(counts), [(i+1, s_["col"], n) for i, (s_, n) in enumerate(zip(st, counts))])
print([t.hex_color() for t in pat.threadlist][:6], len(pat.threadlist))
