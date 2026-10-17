"""Per-size art (01 back + 03L/03R lower fronts, wires re-run to that size's side seams) and the graded art
(02R/02L chest clouds, 04R/04L sleeve clouds at M), cleaned for stitching (dst2.clean_vis, LESSONS A6).
usage: ./py.sh art_size.py SIZE... | graded   ->  art_<SIZE>.pkl / art_graded.pkl"""
import sys, pickle, time
import moonpal, scene, dst2
for a in sys.argv[1:]:
    t = time.time()
    if a == "graded":
        g = scene.graded_art(); n0 = {k: len(v) for k, v in g.items()}
        g = {k: dst2.merge_colours(dst2.clean_vis(v), moonpal.FILE_MERGE) for k, v in g.items()}
        pickle.dump(g, open("art_graded.pkl", "wb")); print("graded", n0, {k: len(v) for k, v in g.items()}, f"{time.time()-t:.0f}s", flush=True)
    else:
        d = scene.art_for_size(a)
        n0 = {k: len(d[k]) for k in ("back", "F03L", "F03R")}
        for k in ("back", "F03L", "F03R"): d[k] = dst2.clean_vis(d[k])
        bad = [m for k in ("back", "front_L", "front_R") for m in d["info"]["marks"][k] if m[2] is None or abs(m[2] - 3.0) > 0.6]
        pickle.dump(d, open(f"art_{a}.pkl", "wb"))
        print(a, "fragments", n0, "->", {k: len(d[k]) for k in ("back", "F03L", "F03R")}, "wire ends off:", bad, f"{time.time()-t:.0f}s", flush=True)
