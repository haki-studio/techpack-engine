"""Jacquard cell-map gate (PR #28 round 3): no floating yarn change. Every shipped panel map (all sizes, both bird
options) must have 0 sky / cream islands (4-connected) of <= ISLAND_MAX cells, except islands enclosed by the knitted
bird (option A: its crest gaps are drawing, not noise). A mill knits a 1-2 cell island as a floating single-cell
colour change.
Red-then-green (prove-the-guard): the gate is also run on a copy of the shipped M front with one planted 1-cell speck
in the sky and one 2-cell speck in the cream; it must count both. Writes out/jacquard/gates_jq.json; exit 1 on fail."""
import glob, json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

SKY, CREAM, BLACK, OUTSIDE = 0, 1, 2, 9
ISLAND_MAX = 2
OUT = "out/jacquard"

def islands(g, n_max=ISLAND_MAX):
    """[(colour, size, row, col)] of SKY / CREAM islands <= n_max cells that do not touch the bird (BLACK)"""
    res = []
    for v in (SKY, CREAM):
        lb, n = ndi.label(g == v)
        if not n: continue
        sz = ndi.sum(np.ones_like(lb), lb, range(1, n + 1))
        for r in np.nonzero(sz <= n_max)[0] + 1:
            m = lb == r
            if (g[ndi.binary_dilation(m) & ~m] == BLACK).any(): continue      # inside the bird drawing (option A)
            ys, xs = np.nonzero(m); res.append((v, int(sz[r - 1]), int(ys[0]), int(xs[0])))
    return res

def main():
    files = sorted(glob.glob(f"{OUT}/HK-FL-PIXSKY_JQ_*.png"))
    per = {}
    for p in files:
        g = np.array(Image.open(p)); per[os.path.basename(p)[16:-4]] = len(islands(g))
    bad = {k: v for k, v in per.items() if v}
    # red: plant specks on the shipped M front
    g = np.array(Image.open(f"{OUT}/HK-FL-PIXSKY_JQ_front_L_M.png")).copy()
    ys, xs = np.nonzero(ndi.binary_erosion(g == SKY, iterations=4)); g[ys[len(ys) // 2], xs[len(xs) // 2]] = CREAM
    ys, xs = np.nonzero(ndi.binary_erosion(g == CREAM, iterations=4)); y, x = ys[len(ys) // 2], xs[len(xs) // 2]
    g[y, x] = g[y, x + 1] = SKY
    red = len(islands(g))
    ok = bool(files) and not bad and red == 2
    out = dict(rule=f"0 sky/cream islands <= {ISLAND_MAX} cells (4-connected) per panel map, bird-enclosed excepted",
               maps=len(files), maps_failing=len(bad), failing=bad, islands_total=sum(per.values()),
               selftest=dict(planted=2, caught=red, ok=red == 2), ok=ok)
    st = json.load(open(f"{OUT}/jacquard_stats.json"))
    out["despeckled_M"] = {k: v.get("despeckled") for k, v in st["panels"].items() if v["size"] == "M"}
    json.dump(out, open(f"{OUT}/gates_jq.json", "w"), indent=1); print(json.dumps(out))
    return 0 if ok else 1

if __name__ == "__main__": sys.exit(main())
