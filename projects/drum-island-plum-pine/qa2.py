import pickle, json, time
from shapely.ops import unary_union
import qa, tech
d = pickle.load(open('back2_vis.pkl', 'rb'))
out = {}
t0 = time.time()
groups = {}
for r in d['back'] + d['sleeve']:
    groups.setdefault(tech.rule_for(r['grp']), []).append(r)
for code, rs in groups.items():
    line = rs[0]['st'] in ('bean', 'run')
    u = unary_union([r['geom'] for r in rs])
    parts = [u] if u.geom_type == 'Polygon' else list(u.geoms)
    A = L = T = 0.0
    for p in parts:
        if p.area < 0.05: continue
        res = qa.check_geom(p, 0.6 if line else 0.8, 0.35 if line else 0.5, 0.45 if line else 0.6)
        if not res: continue
        A += res['area']; L += res['long_area']; T += res['thin_area']
    out[code] = dict(long_pct=100*L/max(A, 1e-9), tip_pct=100*(T-L)/max(A, 1e-9))
    print(f"{code:<14} thin-runs {out[code]['long_pct']:5.1f}%  tips {out[code]['tip_pct']:5.1f}%", flush=True)
json.dump(out, open('qa2.json', 'w'))
print('done', time.time() - t0)
