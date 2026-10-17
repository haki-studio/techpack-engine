"""Per-size art for the four embroidered pieces (LESSONS A5 applied per piece).
Fronts: the size-M scene graded (A 92 % / B 100 % / C 108 %) about the CF neck point (0, 0) - both halves use the same
origin so the head reads continuous across the zip - then clipped to THAT size's pattern keep-outs (C8).
Sleeves: graded about the cap top (0, -cap_h), moved onto that size's cap top, clipped to that size's sleeve keep-outs.
usage: python3 art_size.py XS S M ...   -> art_<size>.pkl + out/art/<size>_<piece>.png"""
import rbcore
import pickle, sys, os, time
import numpy as np
from shapely.ops import unary_union
from shapely import affinity
import front as F, dst2
rbcore.patch_dst2()

SC = pickle.load(open("scene.pkl", "rb"))

def graded(regs, s, origin, shift=(0, 0)):
    out = []
    for r in regs:
        g = affinity.scale(r["geom"], s, s, origin=origin) if s != 1.0 else r["geom"]
        if shift != (0, 0): g = affinity.translate(g, *shift)
        out.append(dict(r, geom=g.buffer(0)))
    return out

def clip_regs(regs, clip):
    out = []
    from shapely import prepared
    pc = prepared.prep(clip)
    for r in regs:
        if not pc.intersects(r["geom"]): continue
        g = r["geom"] if pc.contains(r["geom"]) else r["geom"].intersection(clip).buffer(0)
        if not g.is_empty and g.area > 0.3: out.append(dict(r, geom=g))
    return out

def build(size):
    t0 = time.time(); grade, s = rbcore.GRADE[size]; res = {"info": dict(size=size, grade=grade, scale=s)}
    g, mt = F.pieces(size); gM, mM = F.pieces("M")
    for P in rbcore.PIECES:
        if P[0] == "F":
            src = [r for r in SC["F"] if (r["geom"].centroid.x < 0) == (P == "FR")]
            regs = graded(src, s, (0, 0))
        else:
            src = SC["S" + P[1]]
            regs = graded(src, s, (0, -mM["cap_h"]), (0, -mt["cap_h"] + mM["cap_h"]))
        clip = F.piece_clip(size, P).buffer(-0.4)        # 0.4 inside the keep-out: cleaning never crosses it
        vis = clip_regs(regs, clip)
        vis = dst2.clean_vis(vis)
        vis = [dict(r, geom=r["geom"].intersection(clip).buffer(0)) for r in vis]
        vis = [r for r in vis if not r["geom"].is_empty and r["geom"].area > 0.3]
        res[P] = vis
        u = unary_union([r["geom"] for r in vis])
        res["info"][P] = dict(objects=len(vis), area=round(u.area), bbox=[round(v, 1) for v in u.bounds],
                              by_col={c: round(sum(r["geom"].area for r in vis if r["col"] == c)) for c in rbcore.SEW})
    pickle.dump(res, open(f"art_{size}.pkl", "wb"))
    print(size, grade, s, {P: (res["info"][P]["objects"], res["info"][P]["area"], res["info"][P]["bbox"]) for P in rbcore.PIECES},
          f"{time.time()-t0:.0f}s", flush=True)
    return res

def piece_png(size, res, P, path, ppm=3.0):
    import stitchrender as SR
    g, mt = F.pieces(size); pc = g[rbcore.PIECE_CODE[P]].sew_poly(); b = pc.bounds
    bb = (b[0] - 10, b[1] - 10, b[2] + 10, b[3] + 10)
    im = SR.render(res[P], bb, ppm, base=rbcore.FABRIC, clip=None)
    im.save(path)

if __name__ == "__main__":
    os.makedirs("out/art", exist_ok=True)
    for sz in sys.argv[1:] or rbcore.SIZES:
        r = build(sz)
        if sz == "M" or "png" in sys.argv:
            for P in rbcore.PIECES: piece_png(sz, r, P, f"out/art/{sz}_{P}.png")
