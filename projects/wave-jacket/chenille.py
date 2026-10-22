"""CHENILLE foam PLAN (Rev B fix round, 20 Oct 2026; LESSONS B32 + B33).
The factory said "chenille yes" (19 Oct) but not on which machine or in which file format (factory.json chenille_format =
null). So chenille is NOT a machine file: per piece we ship a path PLAN in the piece's pattern mm (json) + a preview PNG
that the factory's chenille digitiser can read, and the PRIMARY files sew the foam lockstitch (padded tatami along the curl
+ spiral curl cord + loop spiral). Once the factory names the format, the plan becomes the _CHENILLE file.
  moss / loop rows (Foam white): engine chenille.spiral_paths - inward offset rings 1.8 mm apart INCLUDING the rings round
                                 holes, chained into open spirals; needle points at a CONSTANT chord of 2.5 mm
                                 (engine chenille.resample_const, B32: uneven stitch length = uneven loop height)
  chain curl cords (Foam shade): the one continuous spiral cord of every curl, constant 2.0 mm chord
plan(foam_regions, cord_regions, origin, base) -> stats dict (+ base.json, base_preview.png)"""
import json, math
import numpy as np
from PIL import Image, ImageDraw
from digitize.techniques import chenille as CH
from digitize.techniques import specialty as SP
import waveart as WA
from motifs2 import HEX

SPACING = 1.8; MOSS_LEN = 2.5; CHAIN_LEN = 2.0; INSET = 0.6; LOOP_H = 4.0


def moss(p):
    out = []
    for q in WA.polys(p.buffer(-INSET)):
        if q.area < 1.0: continue
        for pth in CH.spiral_paths(q, SPACING):
            out.append(CH.resample_const(pth, MOSS_LEN))
    if not out and p.area > 1.0:
        import dst2
        ln = dst2.centreline(p)
        if ln is not None and ln.length > 1.5: out.append(CH.resample_const(list(ln.coords), MOSS_LEN))
    return out


def cord(p):
    import dst2
    ln = dst2.centreline(p) if p.area > 1.0 else None
    pts = list(ln.coords) if ln is not None else list(p.exterior.coords)
    return [CH.resample_const(pts, CHAIN_LEN)] if len(pts) > 1 else []


def const_len_dev(paths, L):
    """worst relative deviation of a stitch (chord) from L, last stitch of each path excluded (it ends on the end point)"""
    w = 0.0
    for p in paths:
        for a, b in zip(p[:-2], p[1:-1]): w = max(w, abs(math.dist(a, b) - L) / L)
    return round(w, 3)


def plan(foam, cords, origin, base, cols=("w1", "w3")):
    M = [pt for r in foam for p in WA.polys(r["geom"]) for pt in moss(p)]
    C = [pt for r in cords for p in WA.polys(r["geom"]) for pt in cord(p)]
    J = dict(units="mm, piece pattern coords (y down); same origin as the lockstitch file of the piece",
             origin=[round(float(v), 2) for v in origin], question=SP.CHENILLE_QUESTION,
             spec=dict(moss_spacing_mm=SPACING, moss_stitch_mm=MOSS_LEN, chain_stitch_mm=CHAIN_LEN, loop_height_mm=LOOP_H,
                       moss_thread=cols[0], chain_thread=cols[1], status="proposed - confirm with the chenille operator"),
             moss=[[[round(x, 2), round(y, 2)] for x, y in p] for p in M],
             chain=[[[round(x, 2), round(y, 2)] for x, y in p] for p in C])
    json.dump(J, open(base + ".json", "w"))
    # preview: foam outline (cream) + moss paths + chain cords, 3 px/mm on navy
    allp = [q for p in M + C for q in p]
    if allp:
        xs, ys = [p[0] for p in allp], [p[1] for p in allp]; bb = (min(xs) - 5, min(ys) - 5, max(xs) + 5, max(ys) + 5); k = 3.0
        im = Image.new("RGB", (int((bb[2] - bb[0]) * k), int((bb[3] - bb[1]) * k)), (39, 47, 67)); d = ImageDraw.Draw(im)
        T = lambda p: ((p[0] - bb[0]) * k, (p[1] - bb[1]) * k)
        for p in M: d.line([T(q) for q in p], fill=HEX[cols[0]], width=4)
        for p in C: d.line([T(q) for q in p], fill=HEX[cols[1]], width=3)
        im.save(base + "_preview.png")
    L = sum(math.dist(a, b) for p in M + C for a, b in zip(p, p[1:]))
    return dict(file=base, paths=len(M) + len(C), moss_paths=len(M), chain_paths=len(C),
                needle_points=sum(len(p) for p in M + C), length_m=round(L / 1000, 1),
                const_len_dev=dict(moss=const_len_dev(M, MOSS_LEN), chain=const_len_dev(C, CHAIN_LEN)),
                status="PLAN - no machine file until the factory names the chenille format (F1)")
