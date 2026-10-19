"""Per-size art for the two front pieces (LESSONS A5 applied to a scene split by the zip).
Each size: the size-M scene is graded (A 92 % / B 100 % / C 108 %) about the CF neck point (0, 0) - both halves use the
same origin, so the horizon and every ray meet the same CF match marks - then clipped to THAT size's pattern keep-outs.
Small whole motifs (stars, cloud islets) that would be cut by a keep-out are dropped whole instead of being cut.
usage: python3 art_size.py XS S M ...   -> front_<size>.pkl + out/art/<size>_flat.png"""
import glcore
import pickle, sys, os, math, json, time
import numpy as np
import shapely
from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union
from shapely import affinity
import front as F, dst2
glcore.patch_dst2()

SC = pickle.load(open("scene.pkl", "rb")); ITEMS = SC["items"]; META = SC["meta"]

def scaled(items, s):
    if s == 1.0: return [dict(r) for r in items]
    out = []
    for r in items:
        r2 = dict(r, geom=affinity.scale(r["geom"], s, s, origin=(0, 0)).buffer(0))
        if isinstance(r["ang"], tuple): r2["ang"] = (r["ang"][0], r["ang"][1]*s, r["ang"][2]*s)
        out.append(r2)
    return out

def visible(items, clip):
    """z-ordered knockout inside clip. Higher z covers lower; kob = gap cut around the covering region."""
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
        if hits:   # inside one knock group (one cloud bank) regions knock out exactly; the kob gap is for other layers
            kg = r.get("kgrp")
            g = g.difference(unary_union([geoms[j] if (kg and its[j].get("kgrp") == kg) else cover[j] for j in hits]))
        g = g.buffer(0)
        if not g.is_empty and g.area > 0.05: out.append(dict(r, geom=g))
    out.reverse()
    return out

def build(size):
    t0 = time.time(); grade, s = glcore.GRADE[size]
    its = scaled(ITEMS, s); res = {"info": dict(size=size, grade=grade, scale=s)}
    for side in "RL":
        P = "FR" if side == "R" else "FL"
        clip = F.clip_for(size, side).buffer(-0.4)        # 0.4 inside the keep-out: cleaning + simplification never cross it
        half = [r for r in its if (r["geom"].centroid.x < 0) == (side == "R") or r["geom"].intersects(clip)]
        # whole small motifs: keep or drop as a unit
        units = {}
        for r in half:
            if r.get("unit"): units.setdefault(r["unit"], []).append(r)
        drop = set()
        for u, rs in units.items():
            ug = unary_union([r["geom"] for r in rs])
            if not ug.intersects(clip): drop.add(u); continue
            if not clip.buffer(0.3).contains(ug) and not u.startswith(("islet", "star")): drop.add(u)   # traced islets + stars are clipped, never dropped or moved (A14)
        kept = [r for r in half if r.get("unit") not in drop]
        vis = visible(kept, clip)
        raw_area = unary_union([r["geom"] for r in kept if r["geom"].intersects(clip)]).area
        vis = dst2.clean_vis(vis)
        vis = [dict(r, geom=r["geom"].intersection(clip).buffer(0)) for r in vis]
        vis = [r for r in vis if not r["geom"].is_empty and r["geom"].area > 0.3]
        res[P] = vis
        u = unary_union([r["geom"] for r in vis])
        res["info"][P] = dict(objects=len(vis), area=u.area, bbox=u.bounds, dropped_units=sorted(drop),
                              n_dropped=len([d for d in drop if any(r["geom"].intersects(clip.buffer(20)) for r in units[d])]))
    # CF match marks: where the horizon + each ray meet the zip keep-out line on both sides
    marks = []
    hz = META["horizon"]*s; sun = (META["sun"][0]*s, META["sun"][1]*s)
    marks.append(dict(name="horizon", y=hz + 0.6*s))
    for ry in META["rays"]:
        a = math.radians(ry["angle"]); ux, uy = math.cos(a), math.sin(a)
        for xx in (-F.KEEP_CF, F.KEEP_CF):
            if abs(ux) < 1e-6: continue
            t = (xx - sun[0]) / ux
            if t > 0: marks.append(dict(name=f"ray {ry['angle']:.0f}°", x=xx, y=sun[1] + uy*t))
    res["info"]["marks"] = marks
    pickle.dump(res, open(f"front_{size}.pkl", "wb"))
    print(size, grade, s, {P: (res["info"][P]["objects"], round(res["info"][P]["area"]), [round(v) for v in res["info"][P]["bbox"]], len(res["info"][P]["dropped_units"]))
                           for P in ("FR", "FL")}, f"{time.time()-t0:.0f}s", flush=True)
    return res

def flat_png(size, res, path, ppm=2.4):
    from render import geom_to_path
    from motifs2 import HEX
    import cairosvg
    g, mt = F.pieces(size)
    x0, y0, x1, y1 = -370, -110, 370, 600
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {x1-x0} {y1-y0}" width="{int((x1-x0)*ppm)}" height="{int((y1-y0)*ppm)}">',
         f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#FFFFFF"/>']
    for code in ("F01", "F02"):
        o.append(f'<path d="{geom_to_path(g[code].sew_poly())}" fill="{glcore.FABRIC}" stroke="#555" stroke-width="0.8"/>')
    for side in "RL":
        o.append(f'<path d="{geom_to_path(F.clip_for(size, side))}" fill="none" stroke="#FF4040" stroke-width="0.4" stroke-dasharray="2 1.5"/>')
    for P in ("FR", "FL"):
        for r in res[P]: o.append(f'<path d="{geom_to_path(r["geom"])}" fill="{HEX[r["col"]]}" fill-rule="evenodd"/>')
    for m in res["info"]["marks"]:
        if m["name"] == "horizon": o.append(f'<path d="M-24 {m["y"]:.1f} H-15 M15 {m["y"]:.1f} H24" stroke="#00C0FF" stroke-width="0.8"/>')
    o.append(f'<text x="{x0+6}" y="{y0+16}" font-size="12" font-family="Liberation Sans" fill="#333">size {size} · grade {res["info"]["grade"]} ({res["info"]["scale"]*100:.0f} %)</text>')
    o.append('</svg>')
    cairosvg.svg2png(bytestring="".join(o).encode(), write_to=path)

if __name__ == "__main__":
    os.makedirs("out/art", exist_ok=True)
    for sz in sys.argv[1:] or glcore.SIZES:
        r = build(sz); flat_png(sz, r, f"out/art/{sz}_flat.png")
