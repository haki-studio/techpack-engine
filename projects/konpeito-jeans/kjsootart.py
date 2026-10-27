"""Rev B8: drafts inputs/soot_art.json (the soot-sprite art table) from the HAND reading of 20x crops of the mockup.
The reading (which candy each sprite holds, which limbs show) is typed below in READ; this script only turns it into
polylines (arm from the body to under the candy edge, legs) and sizes/places the eyes. Re-run after editing READ:
    python3 kjsootart.py inputs/soot_art.json
then look at the compare sheet (kjsoot.py) — the table, not this script, is what the stitch builder reads."""
import json, math, os, sys
from shapely.geometry import Point, LineString
from shapely.ops import unary_union
sys.path.insert(0, '.'); import kjsvg
F = json.load(open('out/front_stars.json')); ST = {s['id']: s for s in F['stars']}
R = 14.24 / 2; FUR = 1.1
# hand reading of the mockup crops (20x, contrast-stretched): which candies each sprite holds, which limbs show
READ = {
 "K01": dict(holds=["S01", "S02"], seen="arm up-left to the pink (dark 1-px line at -5..-4, -11..-8 px); right arm to the blue and 2 legs faint", legs=True),
 "K02": dict(holds=["S04", "S03"], seen="yellow + blue held against the body; dark px above the yellow on the left = arm; legs not resolvable", legs=True),
 "K03": dict(holds=["S05"], seen="pink held against the lower-left body; arm not resolvable; legs faint below right", legs=True),
 "K04": dict(holds=["S07", "S06"], seen="pink + yellow held against the lower-right body; arms not resolvable", legs=True),
 "K05": dict(holds=["S08", "S09"], seen="both arms raised to the pink (up-left) and blue (up-right), legs = vertical dark line below (clearest sprite)", legs=True),
 "K06": dict(holds=["S10"], seen="both arms raised empty (1-px lines up-left / up-right above the body, -7..-5, -13..-8 px); stands on the yellow: legs down both sides of it (-7..-6, 8..13 px)", legs=False, under=True, cheer=True),
 "K07": dict(holds=["S11"], seen="on the side seam, yellow held below-left; arms/legs not resolvable", legs=True),
 "K08": dict(holds=["S12", "S13"], seen="arm out left to the pink; blue held against the lower-right body", legs=True),
 "K09": dict(holds=["S14"], seen="long arm up-right to the yellow (clear 1-px trail 9..10, -7..-3 px); 2 legs faint below-left", legs=True),
}
def cand_geom(s): return unary_union([r["geom"] for r in kjsvg.konpeito_regions("kj_pink", s['x_from_side_mm'], s['y_from_waist_mm'], 10.0) if r["grp"] == "STAR"])
EW, EH, SEP, PUP, GZ = 0.30, 0.38, 0.365, 0.50, 0.65     # eye white w/h, centre spacing (x D), pupil (x eye w), gaze (mm)
GAZE = {"K01": (0, -1), "K02": (0.3, 1), "K03": (-0.7, 0.7), "K04": (0.7, 0.7), "K05": (0, -1), "K06": (0, 1),
        "K07": (-0.6, 0.8), "K08": (-1, -0.2), "K09": (0.7, -0.7)}    # both pupils look the same way: at the candy held / up when arms are raised
def eyes_for(q, c, cands):
    from shapely import affinity
    D = 2 * R; w, h, sep = EW * D, EH * D, SEP * D
    (a1, b1), (a2, b2) = q["eyes_mm"]; mx, my = (a1 + a2) / 2, (b1 + b2) / 2
    ang = math.atan2(b2 - b1, a2 - a1); ang = max(-math.radians(20), min(math.radians(20), ang))
    def pair(mx, my):
        cs = [(mx - sep / 2 * math.cos(ang), my - sep / 2 * math.sin(ang)), (mx + sep / 2 * math.cos(ang), my + sep / 2 * math.sin(ang))]
        return cs, [affinity.rotate(affinity.scale(Point(c[0] + x, c[1] + y).buffer(1, quad_segs=24), w / 2, h / 2), ang, use_radians=True) for x, y in cs]
    inner = Point(c).buffer(R - 0.9)
    best = None
    for k in range(0, 41):                       # pull the pair toward the centre until both whites sit in the body, clear of candies
        f = 1 - k / 40; cs, el = pair(mx * f, my * f)
        bad = sum(e.difference(inner).area for e in el) + sum(e.intersection(cands).area for e in el)
        if best is None or bad < best[0] - 1e-6: best = (bad, cs, f)
        if bad < 0.05: break
    gx, gy = GAZE[q["id"]]; n = math.hypot(gx, gy); g = [round(GZ * gx / n, 2), round(GZ * gy / n, 2)]
    return dict(centres=[[round(x, 2), round(y, 2)] for x, y in best[1]], w=round(w, 2), h=round(h, 2), tilt_deg=round(math.degrees(ang), 1),
                pupil=round(PUP * w, 2), gaze=g, clash_mm2=round(best[0], 2), pulled_in=round(1 - best[2], 2))
def rel(p, c): return [round(p[0] - c[0], 2), round(p[1] - c[1], 2)]
# Rev B9 (founder 23 Oct: "a lot of the arms are upside down"): B8 rooted the arm on the UPPER side of the candy direction,
# so it left the top of the body and arched over and down to the candy. The mockup (founder's red line on K09): the arm
# leaves the SIDE facing the candy (shoulder, about eye height), runs out, then reaches UP to the candy's underside ("J").
SHOULDER_DEG, SHOULDER_MIN_DEG, RISE_MIN, ELBOW_R = 10.0, -30.0, 2.5, 0.8     # root elevation (deg above horizontal), lowest root, min climb (mm), elbow round-off (mm)
def holding_arm(c, k, cand):
    """[root, elbow-in, elbow-out, hand] in leg mm (y down): root on the body edge at the shoulder on the candy's side,
    level run out to under the candy, then straight up; the hand ends 0.8 mm inside the candy's lower edge (the candy is
    sewn later, on top, so the end tucks under it). The root drops below the shoulder (to SHOULDER_MIN_DEG) only when the
    candy is so low the arm would climb < RISE_MIN."""
    sx = 1 if k[0] >= c[0] else -1
    hx = k[0] - sx * 0.5                                                      # just body-side of the candy's centre line
    col = LineString([(hx, k[1] - 20), (hx, k[1] + 20)]).intersection(cand)
    bot = max(y for _, y in (col.coords if col.geom_type == "LineString" else [p for g in col.geoms for p in g.coords]))
    hand = (hx, bot - 0.8)
    el = math.radians(SHOULDER_DEG)
    if (c[1] - (R - 0.4) * math.sin(el)) - bot < RISE_MIN:                   # too little climb from the root to the candy edge
        y_root = min(bot + RISE_MIN - c[1], (R - 0.4) * math.sin(-math.radians(SHOULDER_MIN_DEG)))
        el = -math.asin(y_root / (R - 0.4))
    a = (c[0] + sx * (R - 0.4) * math.cos(el), c[1] - (R - 0.4) * math.sin(el))
    return [a, (hx - sx * ELBOW_R, a[1]), (hx, a[1] - ELBOW_R), hand]
out = {}
for q in F['soot']:
    c = (q['x_from_side_mm'], q['y_from_waist_mm']); rd = READ[q['id']]
    body = Point(c).buffer(R + FUR); cands = unary_union([cand_geom(ST[s]) for s in rd["holds"]] + [cand_geom(s) for s in ST.values() if math.dist(c, (s['x_from_side_mm'], s['y_from_waist_mm'])) < 22])
    limbs = []
    for sid in rd["holds"]:
        s = ST[sid]; k = (s['x_from_side_mm'], s['y_from_waist_mm']); th = math.atan2(k[1] - c[1], k[0] - c[0]); d = math.dist(c, k)
        if rd.get("under"):        # candy below: legs down the sides of it (+ raised empty arms when cheer)
            if rd.get("cheer"):
                for sg in (-1, 1):
                    t = math.radians(-90 + sg * 38)
                    a = (c[0] + (R - 0.4) * math.cos(t), c[1] + (R - 0.4) * math.sin(t)); b = (c[0] + (R + 2.6) * math.cos(t), c[1] + (R + 2.6) * math.sin(t))
                    e = (b[0] + sg * 0.5, b[1] - 1.8)
                    limbs.append(dict(kind="arm", to=None, pts=[a, b, e]))
            for sg in (-1, 1):
                a = (c[0] + (R - 0.4) * math.cos(th + sg * 0.95), c[1] + (R - 0.4) * math.sin(th + sg * 0.95))
                e = (k[0] + 6.0 * math.cos(th + sg * 1.3), k[1] + 6.0 * math.sin(th + sg * 1.3))      # ends beside the candy, clear of it
                m = ((a[0] + e[0]) / 2 + sg * 0.6 * math.cos(th + math.pi / 2), (a[1] + e[1]) / 2 + sg * 0.6 * math.sin(th + math.pi / 2))
                limbs.append(dict(kind="leg", to=sid, pts=[a, m, e]))
            continue
        limbs.append(dict(kind="arm", to=sid, pts=holding_arm(c, k, cand_geom(s))))
    if rd["legs"]:
        for sg in (-1, 1):
            t = math.radians(90 + sg * 22)
            a = (c[0] + (R - 0.5) * math.cos(t), c[1] + (R - 0.5) * math.sin(t)); b = (c[0] + (R + 3.4) * math.cos(t), c[1] + (R + 3.4) * math.sin(t))
            f = (b[0] + sg * 0.9, b[1] + 0.2)
            limbs.append(dict(kind="leg", pts=[a, b, f]))
    keep = []
    for L in limbs:
        vis = LineString(L["pts"]).difference(body).difference(cands)
        L["visible_mm"] = round(vis.length, 1)
        if vis.length >= 1.5: keep.append(L)
        else: print(q['id'], L["kind"], L.get("to"), "hidden", L["visible_mm"])
    out[q['id']] = dict(holds=rd["holds"], read=rd["seen"], limbs=[dict(kind=L["kind"], **({"to": L["to"]} if L.get("to") else {}), pts=[rel(p, c) for p in L["pts"]], visible_mm=L["visible_mm"]) for L in keep])
    out[q['id']]["eyes"] = eyes_for(q, c, cands)
old = json.load(open(sys.argv[1])) if os.path.exists(sys.argv[1]) else {}
for k, v in out.items():
    v["certainty"] = old.get("sprites", {}).get(k, {}).get("certainty", "")
    for L in v["limbs"]: L["pts"] = [[round(x, 2), round(y, 2)] for x, y in L["pts"]]
json.dump(dict(_doc=old.get("_doc", []), eye_rule=dict(w_D=EW, h_D=EH, sep_D=SEP, pupil_of_w=PUP, gaze_mm=GZ, tilt_max_deg=20), sprites=out),
          open(sys.argv[1], 'w'), indent=1)
for k, v in out.items(): print(k, [(L['kind'], L.get('to'), L['visible_mm']) for L in v['limbs']])
