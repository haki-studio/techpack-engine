"""quick per-piece gate run (fix round 4 experiments): ./py.sh gate_one.py SL [--nodir]"""
import sys, json
P = sys.argv[1]
import gates as G
r = G.gate_piece(P)
for fam in ("curls", "drops", "stripes"):
    f = r[fam]; bad = [(x["x_mm"], x["y_mm"], x["area_mm2"], x["iou"], x["w_ratio"], x["h_ratio"], x.get("why")) for x in f["rows"] if not x["ok"]]
    print(P, fam, f["passed"], "/", f["n"], bad)
d = r.get("direction")
if d:
    print(P, "direction", d["pct_ok"], d["tiles"], "dev", len(d["fail_dev"]), "chaos", len(d["fail_chaos"]))
    for k, v in d["by_family"].items(): print("   ", k, v["tiles"], v["pct_ok"], "dev", v["fail_dev"], "chaos", v["fail_chaos"])
json.dump(r, open(f"/tmp/gate_one_{P}.json", "w"), default=float)
