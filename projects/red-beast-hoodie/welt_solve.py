"""Welt placement (PROPOSED): the render draws the wearer's-left welt under the beast's lower jaw. Search the smallest
move of the mockup welt (same angle, length, both sides mirrored) whose 6 mm keep-out cuts the least art on size M,
staying >= 30 mm above the hem seam and >= 20 mm inside the side seam. Writes welt.json (read by front.py)."""
import rbcore
import pickle, json, math
import numpy as np
from shapely.ops import unary_union
from shapely import prepared
import front as F

SC = pickle.load(open("scene.pkl", "rb"))
art = unary_union([r["geom"] for r in SC["F"]]).buffer(0)
head = unary_union([r["geom"] for r in SC["F"] if r["grp"] in ("OL", "OL-fill", "BK", "BK-fill", "HR-fill")]).buffer(0)
def cost(c, ang):
    w = F._welt(+1, c, ang).buffer(F.KEEP_WELT); wr = F._welt(-1, c, ang).buffer(F.KEEP_WELT)
    return (w.intersection(head).area + wr.intersection(head).area,
            w.intersection(art).area + wr.intersection(art).area)
c0, a0 = F.WELT_MOCK_C, 61.6
base = cost(c0, a0)
best = None
for dy in np.arange(-10, 60.1, 2.5):
    for dx in np.arange(-30, 50.1, 2.5):
        c = (c0[0] + dx, c0[1] + dy); w = F._welt(+1, c, a0)
        b = w.bounds
        if b[3] > F.HEM - 30 or b[2] > F.BLK.chest2 - 20: continue
        h, a = cost(c, a0)
        key = (round(h, 0) > 5, h + 0.5*a + 2.0*math.hypot(dx, dy))
        if best is None or key < best[0]: best = (key, c, h, a, (dx, dy))
print("mockup welt: head cut", round(base[0]), "mm2, all art cut", round(base[1]), "mm2")
print("chosen: centre", [round(v, 1) for v in best[1]], "move", best[4], "head cut", round(best[2]), "all art cut", round(best[3]))
json.dump({"c": [round(best[1][0], 1), round(best[1][1], 1)], "ang": a0, "mock_c": list(c0), "move_mm": list(best[4]),
           "head_cut_mm2": round(best[2], 1), "art_cut_mm2": round(best[3], 1), "mock_head_cut_mm2": round(base[0], 1),
           "mock_art_cut_mm2": round(base[1], 1)}, open("welt.json", "w"), indent=1)
