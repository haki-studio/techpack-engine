import time, pickle
import emb_art as EA, star_fit as SF, mockmap as MM
comps = EA.components(); out = []
for c in comps:
    w = (c["xs"].max() - c["xs"].min() + 1) * MM.S
    pass
    t = time.time(); g, err, k, tiers, tab = SF.fit_tiers(c["xs"], c["ys"])
    pix = EA.ref_pixels(c); iou = g.intersection(pix).area / g.union(pix).area
    print(round(c["cx"]), round(c["cy"]), c["colour"], f"w {w:.1f}", "k", k, tiers, f"err {err:.4f}", tab, f"IoU {iou:.3f}", f"{time.time()-t:.0f}s")
    out.append((c["cx"], c["cy"], g, pix))
pickle.dump(out, open("work/r2/tiers.pkl", "wb"))
