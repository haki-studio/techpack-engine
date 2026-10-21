import pickle, sys
import emb_art as EA, star_fit as SF, mockmap as MM
kmax = int(sys.argv[1]); out = []
for c in EA.components():
    w = (c["xs"].max() - c["xs"].min() + 1) * MM.S
    if w >= SF.SMALL_MM: continue
    g, err, k, r, tab = SF.fit_tiers(c["xs"], c["ys"], kmax=kmax, free_edges=False)
    pix = EA.ref_pixels(c); iou = g.intersection(pix).area / g.union(pix).area
    print(round(c["cx"]), round(c["cy"]), c["colour"], f"w {w:.1f} k {k} err {err:.3f} iou {iou:.3f}", tab)
    out.append((c["cx"], c["cy"], g, pix))
pickle.dump(out, open("work/r2/small.pkl", "wb"))
