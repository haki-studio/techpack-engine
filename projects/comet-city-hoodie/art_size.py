"""Per-size art for the four embroidered pieces (LESSONS A5 applied to a scene split by the zip + two sleeves).
Fronts: the size-M scene is graded (A 92 % / B 100 % / C 108 %) about the CF neck point (0, 0) - both halves use the same
origin, so the comet, railing and kerb meet the same CF match marks - then clipped to THAT size's pattern keep-outs.
Sleeves: the size-M sleeve art is graded about the cuff-seam centre and clipped to that size's sleeve keep-outs.
Small whole motifs (stars, meteors, rosettes) that would be cut by a keep-out are dropped whole instead of being cut.
usage: python3 art_size.py XS S M ...   -> art_<size>.pkl + out/art/<size>_flat.png"""
import cccore
import pickle, sys, os, math, json, time
import numpy as np
import shapely
from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union
from shapely import affinity
import front as F, dst2
cccore.patch_dst2()

SC = pickle.load(open("scene.pkl", "rb")); ITEMS = SC["items"]; META = SC["meta"]
SL = pickle.load(open("sleeve_scene.pkl", "rb")) if os.path.exists("sleeve_scene.pkl") else None
HEM_M = LineString(F.keep_geoms("M", "L")["hem"]).bounds[1]     # 510 on the Drum Island block
Y0, Y1 = 200.0, 340.0                                            # hem-anchoring ramp (size-M mm): sky above Y0 stays, city below Y1 moves fully

def scaled(items, s, origin=(0, 0)):
    if s == 1.0: return [dict(r) for r in items]
    out = []
    for r in items:
        r2 = dict(r, geom=affinity.scale(r["geom"], s, s, origin=origin).buffer(0))
        if isinstance(r["ang"], tuple):
            r2["ang"] = (r["ang"][0], origin[0] + (r["ang"][1] - origin[0])*s, origin[1] + (r["ang"][2] - origin[1])*s)
        out.append(r2)
    return out

def visible(items, clip):
    """z-ordered knockout inside clip. Higher z covers lower (unless the covering region is an overlay, ko=False);
    kob = gap cut around the covering region. Inside one knock group (kgrp) regions knock out exactly."""
    its = [r for r in items if r["geom"].intersects(clip)]
    its.sort(key=lambda r: -r["z"])
    geoms = [r["geom"] for r in its]
    cover = [r["geom"].buffer(r["kob"]) if r.get("kob") else r["geom"] for r in its]
    tree = shapely.STRtree(cover)
    out = []
    for i, r in enumerate(its):
        g = r["geom"].intersection(clip)
        if g.is_empty: continue
        hits = [int(j) for j in tree.query(g) if int(j) < i and its[int(j)].get("ko", True)]
        if hits:
            kg = r.get("kgrp")
            g = g.difference(unary_union([geoms[j] if (kg and its[j].get("kgrp") == kg) else cover[j] for j in hits]))
        g = g.buffer(0)
        if not g.is_empty and g.area > 0.05: out.append(dict(r, geom=g))
    out.reverse()
    return out

def piece_art(its, clip, side_test):
    half = [r for r in its if side_test(r) or r["geom"].intersects(clip)]
    units = {}
    for r in half:
        if r.get("unit"): units.setdefault(r["unit"], []).append(r)
    drop = set()
    for u, rs in units.items():
        ug = unary_union([r["geom"] for r in rs])
        if not ug.intersects(clip): drop.add(u); continue
        if not clip.buffer(0.3).contains(ug): drop.add(u)
    kept = [r for r in half if r.get("unit") not in drop]
    vis = visible(kept, clip)
    vis = dst2.clean_vis(vis)
    vis = [dict(r, geom=r["geom"].intersection(clip).buffer(0)) for r in vis]
    vis = [r for r in vis if not r["geom"].is_empty and r["geom"].area > 0.3]
    near = [d for d in drop if any(r["geom"].intersects(clip.buffer(20)) for r in units[d])]
    return vis, sorted(drop), near

def build(size):
    t0 = time.time(); grade, s = cccore.GRADE[size]
    res = {"info": dict(size=size, grade=grade, scale=s)}
    its = scaled(ITEMS, s)
    # hem anchoring: the city band (railing, bicycle, figure, buildings) stands on THIS size's hem-band seam; the shift ramps
    # in through the lower clouds (whole clouds / whole motifs move together); the comet + upper sky stay on the CF-neck grade
    hem = LineString(F.keep_geoms(size, "L")["hem"]).bounds[1]
    dy = hem - HEM_M * s
    def ramp(y): return float(np.clip((y - Y0*s) / ((Y1 - Y0)*s), 0, 1))
    refs = {}
    for r in its:
        if r.get("unit"): refs.setdefault(r["unit"], []).append(r["geom"].centroid.y)
    for r in its:
        if r.get("sew") in ("comet",): continue
        yr = r.get("cref", None)
        yr = yr*s if yr is not None else (np.mean(refs[r["unit"]]) if r.get("unit") else r["geom"].centroid.y)
        k = ramp(yr) * dy
        if abs(k) > 0.01:
            r["geom"] = affinity.translate(r["geom"], 0, k)
            if isinstance(r["ang"], tuple): r["ang"] = (r["ang"][0], r["ang"][1], r["ang"][2] + k)
    res["info"]["hem_shift"] = round(dy, 1)
    for side in "RL":
        P = "FR" if side == "R" else "FL"
        clip = F.clip_for(size, side).buffer(-0.4)        # 0.4 inside the keep-out: cleaning + simplification never cross it
        vis, drop, near = piece_art(its, clip, lambda r: (r["geom"].centroid.x < 0) == (side == "R"))
        res[P] = vis
        u = unary_union([r["geom"] for r in vis])
        res["info"][P] = dict(objects=len(vis), area=u.area, bbox=u.bounds, dropped_units=drop, n_dropped=len(near))
    if SL is not None:
        for side in "RL":
            P = "SR" if side == "R" else "SL"
            g, mt = F.pieces(size); pc = g["S01" if side == "R" else "S02"].sew_poly(); b = pc.bounds
            g0, _ = F.pieces("M"); b0 = g0["S01"].sew_poly().bounds
            org = (0.0, b0[3])                                   # cuff-seam centre (M)
            sits = scaled(SL["items"][P], s, origin=org)
            sits = [dict(r, geom=affinity.translate(r["geom"], 0, b[3] - b0[3])) for r in sits]
            for r in sits:
                if isinstance(r["ang"], tuple): r["ang"] = (r["ang"][0], r["ang"][1], r["ang"][2] + b[3] - b0[3])
            clip = F.sleeve_clip(size, side).buffer(-0.4)
            vis, drop, near = piece_art(sits, clip, lambda r: True)
            res[P] = vis
            u = unary_union([r["geom"] for r in vis])
            res["info"][P] = dict(objects=len(vis), area=u.area, bbox=u.bounds, dropped_units=drop, n_dropped=len(near))
    # CF match marks: where the top rail, the kerb line and the comet spine meet the zip keep-out line on both sides
    import mockmap as MM
    marks = []
    for nm, dpx in (("top rail", 0.0), ("kerb", 47.5)):          # mockup px below the top rail
        for xx in (-F.KEEP_CF, F.KEEP_CF):
            px = MM.Pinv(xx / s, 0)[0]; y = MM.P(px, 720.0 + (px - 130.0)*7/470 + dpx)[1]
            marks.append(dict(name=nm, x=xx, y=y*s + dy))            # city band: graded + slid to this size's hem
    sp = np.array(META.get("spine", []))
    if len(sp):
        for xx in (-F.KEEP_CF, F.KEEP_CF):
            i = int(np.argmin(np.abs(sp[:, 0] - xx / s))); marks.append(dict(name="comet core", x=xx, y=float(sp[i, 1])*s))
    res["info"]["marks"] = marks
    pickle.dump(res, open(f"art_{size}.pkl.tmp", "wb")); os.replace(f"art_{size}.pkl.tmp", f"art_{size}.pkl")   # atomic: builds may be reading
    print(size, grade, s, {P: (res["info"][P]["objects"], round(res["info"][P]["area"]), [round(v) for v in res["info"][P]["bbox"]], res["info"][P]["n_dropped"])
                           for P in cccore.PIECES if P in res["info"]}, f"{time.time()-t0:.0f}s", flush=True)
    return res

def flat_png(size, res, path, ppm=2.4):
    from render import geom_to_path
    from motifs2 import HEX
    import cairosvg
    g, mt = F.pieces(size)
    x0, y0, x1, y1 = -340, -110, 340, 540
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {x1-x0} {y1-y0}" width="{int((x1-x0)*ppm)}" height="{int((y1-y0)*ppm)}">',
         f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#FFFFFF"/>']
    for code in ("F01", "F02"):
        o.append(f'<path d="{geom_to_path(g[code].sew_poly())}" fill="{cccore.FABRIC}" stroke="#555" stroke-width="0.8"/>')
    for side in "RL":
        o.append(f'<path d="{geom_to_path(F.clip_for(size, side))}" fill="none" stroke="#FF4040" stroke-width="0.4" stroke-dasharray="2 1.5"/>')
    for P in ("FR", "FL"):
        for r in res[P]: o.append(f'<path d="{geom_to_path(r["geom"])}" fill="{HEX[r["col"]]}" fill-rule="evenodd"/>')
    o.append(f'<text x="{x0+6}" y="{y0+16}" font-size="12" font-family="Liberation Sans" fill="#333">size {size} · grade {res["info"]["grade"]} ({res["info"]["scale"]*100:.0f} %)</text>')
    o.append('</svg>')
    cairosvg.svg2png(bytestring="".join(o).encode(), write_to=path)

if __name__ == "__main__":
    os.makedirs("out/art", exist_ok=True)
    for sz in sys.argv[1:] or cccore.SIZES:
        r = build(sz); flat_png(sz, r, f"out/art/{sz}_flat.png")
