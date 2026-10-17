"""Keep-out cut check (review item 3): length of cloud / sea-field outline that lies ON a keep-out line (a straight clip
instead of whole lobes), per size and piece. Target: ~0 for clouds."""
import glcore, pickle, sys
from shapely.ops import unary_union
import front as F
for sz in sys.argv[1:] or glcore.SIZES:
    D = pickle.load(open(f"front_{sz}.pkl", "rb")); row = {}
    for P, s in (("FR", "R"), ("FL", "L")):
        edge = F.clip_for(sz, s).buffer(-0.4).boundary.buffer(0.35)
        for nm, pref in (("clouds", ("CL", "ISL")), ("field", ("SEA-field",))):
            u = unary_union([r["geom"] for r in D[P] if r["grp"].startswith(pref)])
            row[f"{P} {nm}"] = round(u.boundary.intersection(edge).length, 1) if not u.is_empty else 0.0
    print(sz, "mm of outline on a keep-out line:", row)
