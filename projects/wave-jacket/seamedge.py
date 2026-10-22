"""Fix round 3 (PR #27 review 2 item 4, the founder's seamless wrap): ONE-SIDED seam runs. Where the art reaches a seam on
one piece and the partner piece is bare there in the mockup (shoulder L: the front wave runs over the shoulder, the back
render is bare at the shoulder; CF zip / side seams where a crest sits on one side only), the foam used to stop on the
seam keep-out as a STRAIGHT cut line along the seam (G9). Nothing may be invented on the bare partner (the mockup is the
source), so the crest ENDS in foam lobes instead: along each one-sided run >= 6 mm the foam edge is scalloped - lobes of
radius LOBE_R every 2 x LOBE_R, reaching the keep-out at their crowns and receding NOTCH mm between them - the way the
mockup's own crests end in curls. Stripes are not touched (wrap.continue_across tapers them). Generated geometry: every
edited item gets gen='seam lobes' and is listed on G9.
usage: ./py.sh seamedge.py [M]   (after tonematch.py; edits art_<size>.pkl in place, keeps art_<size>_preedge.pkl; seamedge_<size>.json)"""
import sys, json, os, pickle, shutil
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import wavecore as WC
import wrap as WR

size = next((a for a in sys.argv[1:] if not a.startswith("-")), "M")
if os.path.exists(f"art_{size}_preedge.pkl") and pickle.load(open(f"art_{size}.pkl", "rb"))["info"].get("seamedge"):
    shutil.copy(f"art_{size}_preedge.pkl", f"art_{size}.pkl")
D = pickle.load(open(f"art_{size}.pkl", "rb")); shutil.copy(f"art_{size}.pkl", f"art_{size}_preedge.pkl")
LOBE_R, NOTCH, MIN_RUN = 2.6, 2.4, 6.0
FOAM = ("FM", "FM-sh", "FM-gr", "FM-in", "FM-loop", "FM-curl")
D0 = WR.GAP + 1.0

def runs(la, lb):
    """one-sided runs (mm along the seam) where side a has foam at D0 and side b has no art within +/-2 mm"""
    out, k0 = [], None
    n = min(len(la), len(lb))
    for k in range(n + 1):
        one = k < n and la[k] in ("w1", "w3", "g1") and all(lb[j] is None for j in range(max(0, k - 2), min(n, k + 3)))
        if one and k0 is None: k0 = k
        if not one and k0 is not None:
            if k - k0 >= MIN_RUN: out.append((k0, k - 1))
            k0 = None
    return out

def cutter(side, s0, s1):
    """the area to remove: from beyond the seam to a scalloped line GAP+0.6 (crowns) .. GAP+0.6+NOTCH (notches) inside"""
    per = 2 * LOBE_R; L = side.L; pts_in, pts_out = [], []
    for s in np.arange(s0 - 1.0, s1 + 1.0 + 1e-6, 0.5):
        ph = ((s - s0) % per) / per                                   # 0..1 inside one lobe
        d = WR.GAP + 0.6 + NOTCH * (1 - np.sqrt(max(0.0, 1 - (2 * ph - 1) ** 2)))   # semicircle crown, notch at the joins
        f = min(max(s / L, 0.0), 1.0)
        pts_in.append(side.point(f, d)); pts_out.append(side.point(f, -3.0))
    return Polygon(pts_in + pts_out[::-1]).buffer(0)

log = {}
for sm in WR.seams(size):
    if sm["kind"] == "internal": continue
    A, B = WR.SeamSide(size, sm, "A"), WR.SeamSide(size, sm, "B")
    for a, b in ((A, B), (B, A)):
        ia = [r for r in D[a.P] if r["geom"].intersects(a.region)]; ib = [r for r in D[b.P] if r["geom"].intersects(b.region)]
        la = WR.labels(ia, a, D0); lb_ = WR.labels(ib, b, D0)
        lb = [lb_[min(len(lb_) - 1, int(round(k * b.L / a.L)))] if lb_ else None for k in range(len(la))]   # same seam fraction
        rr = runs(la, lb)
        if not rr: continue
        cut = unary_union([cutter(a, s0, s1) for s0, s1 in rr]).intersection(a.region.buffer(5.0))
        n = 0
        for i, r in enumerate(D[a.P]):
            if r["grp"] not in FOAM or not r["geom"].intersects(cut): continue
            g = r["geom"].difference(cut).buffer(0)
            D[a.P][i] = dict(r, geom=g, gen="seam lobes"); n += 1
        D[a.P] = [r for r in D[a.P] if not r["geom"].is_empty and r["geom"].area > 0.3]
        log[f"{sm['name']} {a.which} ({a.P})"] = dict(runs=[[int(s0), int(s1)] for s0, s1 in rr], mm=int(sum(s1 - s0 + 1 for s0, s1 in rr)), items=n)
D["info"]["seamedge"] = log
pickle.dump(D, open(f"art_{size}.pkl", "wb")); json.dump(log, open(f"seamedge_{size}.json", "w"), indent=1)
for k, v in log.items(): print(k, v)
