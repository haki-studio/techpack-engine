import sys, time, numpy as np
import emb_art as EA, star_fit as SF, mockmap as MM
comps = EA.components()
for c in comps:
    w = (c["xs"].max() - c["xs"].min() + 1) * MM.S
    if w < SF.SMALL_MM: continue
    t = time.time(); g, err, cell, kind, tab = SF.fit_unit(c["xs"], c["ys"])
    best = min(tab, key=lambda r: r[1])
    print(round(c["cx"]), round(c["cy"]), c["colour"], f"w {w:.1f}", "unit", cell, kind, f"err {err:.4f}", "best", best, f"{time.time()-t:.0f}s")
    print("   ", " ".join(f"{a}:{b:.3f}" for a, b in tab))
