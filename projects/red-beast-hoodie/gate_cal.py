"""Calibrate the DST -> 'visible thread' mask model of qa_gates.py on shapes of KNOWN size (ENGINE_NOTES 12 check):
synthetic objects built by the same stitch engine + project rules as the real files (streak SK, hair stroke HS along
the stroke, black stroke BS, cord OL, tooth OL-tooth), written to DST, read back, rasterised with the gate's model.
A model is right when every shape measures at its designed size (IoU vs the designed polygon, width ratio ~1).
usage: python3 gate_cal.py  -> out/gate_cal.json (+ table)"""
import rbcore
import json, os, itertools
import numpy as np
import pyembroidery as pe
from shapely.geometry import LineString, Polygon, box
from shapely import affinity
import shapely
from scipy import ndimage as ndi
import qa_gates as Q
dst2 = rbcore.patch_dst2()
import tech

def obj(col, geom, grp, ang="auto", fixed=False):
    return dict(col=col, geom=geom, st="satin", ang=ang, grp=grp, ko=True, kob=0.0, unit=None, layer=20, fixed=fixed, z=0, el="01")

def shapes():
    out = []
    for i, w in enumerate((1.2, 1.8, 2.5, 3.0, 3.5)):
        L = LineString([(0, 0), (40, 0)]).buffer(w/2, cap_style="flat")
        out.append(("streak SK %.1f" % w, w, obj("rb_red", affinity.rotate(L, 30, origin=(0, 0)), "SK")))
        out.append(("hair HS %.1f" % w, w, obj("rb_red", affinity.rotate(LineString([(0, 0), (10, 0)]).buffer(w/2, cap_style="flat"), 30, origin=(0, 0)), "HS", ang=30.0, fixed=True)))
        c = LineString([(0, 0), (15, 6), (30, 4), (45, 12)]).buffer(w/2, cap_style="round")
        out.append(("cord OL %.1f" % w, w, obj("rb_cream", c, "OL")))
        out.append(("black BS %.1f" % w, w, obj("rb_black", affinity.rotate(LineString([(0, 0), (10, 0)]).buffer(w/2, cap_style="flat"), -20, origin=(0, 0)), "BS", ang=160.0, fixed=True)))
    out.append(("tooth", 4.0, obj("rb_cream", Polygon([(0, 0), (5, 0), (3.5, 9), (1.5, 9)]), "OL-tooth", ang=90.0, fixed=True)))
    return out

def build(o, tmp):
    vis = [o]; stops = tech.stops(vis); stops = dst2.merge_stops(stops)
    b = o["geom"].bounds; c = ((b[0]+b[2])/2, (b[1]+b[3])/2)
    pat, st = dst2.make_pattern(vis, stops, c); dst2.write(pat, tmp)
    p = pe.read(tmp + ".dst"); segs = []; prev = None; ci = 0
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK
        if k == pe.STITCH:
            q = (x/10 + c[0], y/10 + c[1])
            if prev is not None: segs.append((prev, q, ci))
            prev = q
        elif k == pe.COLOR_CHANGE: ci += 1; prev = None
        elif k in (pe.TRIM, pe.JUMP): prev = None
        elif k == pe.END: break
    return dict(segs=segs, cols=[o["col"]]*(ci + 1))

def measure(o, st, thread, close_px, pull):
    g = o["geom"]; b = g.buffer(4).bounds; PP = Q.PPM
    shape = (int((b[3]-b[1])*PP), int((b[2]-b[0])*PP))
    Q.THREAD, Q.PULL = thread, pull
    vis, keys = Q.visible(None, b, shape, sts=[st])
    m = np.isin(vis, [keys.index(o["col"]) + 1])
    if close_px: m = ndi.binary_closing(m, structure=np.ones((2*close_px + 1,)*2, bool)) | m
    e = int(round(pull*PP*Q.SS))
    if e > 0: m = ndi.binary_erosion(m, iterations=e)
    m = m.reshape(m.shape[0]//Q.SS, Q.SS, m.shape[1]//Q.SS, Q.SS).mean(axis=(1, 3)) >= 0.5
    X, Y = Q.grid(b, shape); ref = shapely.contains_xy(g, X, Y)
    iou = (ref & m).sum()/max((ref | m).sum(), 1)
    rows = Q.motif_rows(ref, m, PP, min_mm2=0.5)
    r = rows[0] if rows else {}
    return round(float(iou), 3), r.get("width_ratio", r.get("w_ratio")), r.get("ok")

if __name__ == "__main__":
    os.makedirs("out/gate_cal", exist_ok=True)
    S = shapes(); built = [(n, w, o, build(o, f"out/gate_cal/s{i}")) for i, (n, w, o) in enumerate(S)]
    res = {}
    for thread, close_px, pull in itertools.product((0.40, 0.45), (1, 2, 3), (0.0, 0.125, 0.25)):
        rows = [(n,) + measure(o, st, thread, close_px, pull) for n, w, o, st in built]
        key = f"thread {thread} close {close_px}px pull {pull}"
        wr = [r[2] for r in rows if r[2]]
        res[key] = dict(rows=rows, mean_iou=round(float(np.mean([r[1] for r in rows])), 3),
                        width_err=round(float(np.mean([abs(np.log(v)) for v in wr])), 3), all_ok=all(r[3] for r in rows))
        print(key, "IoU", res[key]["mean_iou"], "width |log err|", res[key]["width_err"], "all ok", res[key]["all_ok"], flush=True)
    json.dump(res, open("out/gate_cal.json", "w"), indent=1)
