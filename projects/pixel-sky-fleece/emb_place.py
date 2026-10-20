"""Embroidery placement per size + keep-out clearances (LESSONS A3, C8: measured on the drafted pattern pieces).
Art is 100 % in every size; positions are the mockup's, in piece coords: fronts x from CF, y from the CF neck seam
(chest motifs keep their height under the neck); sleeve sparkles keep their distance from the cuff seam and the sleeve
centre line. Used by pattern_out (DXF layer 8 marks) via EMB_ON / EMB_NAME / place()."""
import json, pickle
from shapely.geometry import Point, LineString
from shapely.ops import unary_union
from shapely import affinity
import fleece as FL, pattern as PT

EMB_ON = {"F02": ["E1"], "F01": ["E2"], "S02": ["E3"]}
EMB_NAME = {"E1": "E1 sparkles (opt A) / E1B bird + sparkles (opt B)", "E2": "E2 sparkles", "E3": "E3 sleeve sparkles", "E1B": "E1B bird + sparkles"}
MIN = {"CF / zip": 15.0, "side": 15.0, "armhole": 15.0, "shoulder": 15.0, "neck": 15.0, "hem": 10.0, "pocket opening": 6.0,
       "cap": 15.0, "underarm front": 15.0, "underarm back": 15.0, "cuff": 10.0}

def art():
    return pickle.load(open("out/art/art.pkl", "rb"))

def place(size):
    """{element: (piece, geometry in piece coords)}; E1 is drawn with the option-B bird so the box covers both"""
    A = art(); g, mt = FL.draft(size); gM, mtM = FL.draft("M"); out = {}
    for el, src in (("E1", "E1B"), ("E2", "E2"), ("E3", "E3"), ("E1B", "E1B")):
        G = unary_union([geom for _, geom, _ in A[src]])
        if el == "E3":     # keep the distance from the cuff seam (y = Lu) and the centre line
            G = affinity.translate(G, 0, mt["Lu"] - mtM["Lu"])
        out[el] = ({"E1": "F02", "E1B": "F02", "E2": "F01", "E3": "S02"}[el], G)
    return {k: (None, v[1]) for k, v in out.items()}, {k: v[0] for k, v in out.items()}

def clearances(size):
    pl, piece = place(size); g, mt = FL.draft(size); rows = []
    for el, (_, G) in pl.items():
        pc = g[piece[el]]
        for e in pc.edges:
            d = G.distance(LineString(e.pts)); key = e.name
            lim = MIN.get(key, 15.0)
            rows.append(dict(el=el, piece=pc.code, edge=key, mm=round(d, 1), min=lim, ok=d >= lim))
        for nm, pts in pc.internal:
            if "POCKET" in nm:
                d = G.distance(LineString(pts)); rows.append(dict(el=el, piece=pc.code, edge="pocket opening", mm=round(d, 1), min=MIN["pocket opening"], ok=d >= MIN["pocket opening"]))
        inside = pc.sew_poly().buffer(-1).contains(G)
        rows.append(dict(el=el, piece=pc.code, edge="inside the piece", mm=0.0, min=0.0, ok=bool(inside)))
    return rows

if __name__ == "__main__":
    allok = True; res = {}
    for sz in FL.SIZES:
        rows = clearances(sz); bad = [r for r in rows if not r["ok"]]; allok &= not bad
        res[sz] = rows
        print(sz, "PASS" if not bad else bad, {k: (min(x["mm"] for x in rows if x["el"] == k and x["edge"] != "inside the piece"),
              min((x for x in rows if x["el"] == k and x["edge"] != "inside the piece"), key=lambda x: x["mm"])["edge"]) for k in ("E1", "E2", "E3")})
    json.dump(res, open("out/clearances.json", "w"), indent=1)
    print("ALL PASS" if allok else "FAIL")
