"""Region width QA per region code (fill/satin min 0.8, line min 0.6): share of area thin for > 2.5 mm (qa.check_geom).
-> qa_width.json {piece: {code: {long_pct, tip_pct}}}"""
import pickle, json, time
import fbcore
from shapely.ops import unary_union
import qa, tech
D = pickle.load(open("back_vis.pkl", "rb")); F = pickle.load(open("front_vis.pkl", "rb"))
out = {}; t0 = time.time()
for piece, vis in (("back", D["back"]), ("02R", F["02R"]), ("02L", F["02L"])):
    groups = {}
    for r in vis:
        if r["grp"] == "PH": continue
        groups.setdefault(tech.rule_for(r["grp"]), []).append(r)
    res = {}
    for code, rs in groups.items():
        line = rs[0]["st"] in ("bean", "run")
        u = unary_union([r["geom"] for r in rs]); parts = [u] if u.geom_type == "Polygon" else list(u.geoms)
        A = L = T = 0.0
        for p in parts:
            if p.area < 0.05: continue
            q = qa.check_geom(p, 0.6 if line else 0.8, 0.35 if line else 0.5, 0.45 if line else 0.6)
            if not q: continue
            A += q["area"]; L += q["long_area"]; T += q["thin_area"]
        res[code] = dict(long_pct=100*L/max(A, 1e-9), tip_pct=100*(T-L)/max(A, 1e-9))
    out[piece] = res
    worst = max(res, key=lambda k: res[k]["long_pct"])
    print(piece, "worst", worst, round(res[worst]["long_pct"], 2), {k: round(v["long_pct"], 1) for k, v in res.items() if v["long_pct"] >= 1}, flush=True)
json.dump(out, open("qa_width.json", "w"), indent=1)
print("done", round(time.time() - t0))
