"""Per-size 01 back + sleeve-wrap art. The unclipped scene (back2.items, which continues past the right
armhole onto a flat sleeve extension) is scaled to the size's art grade, placed on that size's back pattern,
then clipped to that size's keep-outs. The overflow past the armhole becomes that size's sleeve piece, so the
wrap always meets the seam exactly (graded single files can't do this — the armhole doesn't grade with the art).
usage: python3 back_size.py SIZE  ->  back_<SIZE>.pkl {"back": vis, "sleeve": vis in seam coords, "info": {...}}"""
import sys, pickle, math, json
import numpy as np
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
from shapely import affinity
import back2 as B, pattern as PT, emb_place as EP, dst2

def art_for_size(size):
    g, mt = PT.draft(size); gM, mM = PT.draft("M")
    G = EP.grade_of(size, "back"); sc = EP.SCALE[G]
    OL = EP.outlines(); ref = OL["back"].bounds                  # clipped M art box
    c0 = ((ref[0] + ref[2]) / 2, (ref[1] + ref[3]) / 2)
    dx = c0[0] * sc - c0[0]
    bottom = c0[1] + (ref[3] - c0[1]) * sc
    dy = (mt["hem_b"] - (mM["hem_b"] - ref[3])) - bottom
    # anchor x on the right armhole so the branches still reach the sleeve on every size: the point where the
    # M limbs cross the armhole (mid of the M match marks) lands on this size's armhole at the same height.
    # Limited so the left limbs keep the 15 mm side keep-out (shift left of that would clip them).
    side_L = LineString(next(e.pts for e in g["B01"].edges if e.name == "side L"))
    armS = LineString(next(e.pts for e in g["B01"].edges if e.name == "armhole R"))
    marksM = json.load(open("wrap_marks.json")); sm = (marksM[0][0] + marksM[-1][1]) / 2
    P = B.ARM_R_LINE.interpolate(sm)
    nx, ny = c0[0] + (P.x - c0[0]) * sc + dx, c0[1] + (P.y - c0[1]) * sc + dy
    hit = armS.intersection(LineString([(0, ny), (800, ny)]))
    if not hit.is_empty:
        hx = hit.x if hit.geom_type == "Point" else max(q.x for q in hit.geoms)
        dx_anchor = dx + (hx - nx)
    else:
        dx_anchor = dx
    def side_ok(d):
        return affinity.translate(affinity.scale(OL["back"], sc, sc, origin=c0), d, dy).distance(side_L) >= 15.0
    lo_, hi_ = min(dx, dx_anchor), max(dx, dx_anchor)
    if side_ok(dx_anchor): dx = dx_anchor
    else:                       # largest move toward the anchor that still clears the side seam
        best = dx
        for d in np.linspace(dx, dx_anchor, 41):
            if side_ok(d): best = d
        dx = best
    if not side_ok(dx):
        for d in np.arange(dx, dx + 60, 0.5):
            if side_ok(d): dx = d; break
    T = lambda geom: affinity.translate(affinity.scale(geom, sc, sc, origin=c0), dx, dy)
    items = []
    for r in B.items:
        r2 = dict(r, geom=T(r["geom"]).buffer(0))
        if isinstance(r["ang"], tuple):
            a = r["ang"]; px, py = c0[0] + (a[1] - c0[0]) * sc + dx, c0[1] + (a[2] - c0[1]) * sc + dy
            r2["ang"] = (a[0], px, py)
        items.append(r2)
    # size clip regions (back view coords)
    panel = g["B01"].sew_poly(); hem = mt["hem_b"]
    arm = next(e.pts for e in g["B01"].edges if e.name == "armhole R")[::-1]       # shoulder seam -> underarm
    ARM = LineString(arm); sp, ua = arm[0], arm[-1]
    sleeve_R = Polygon(arm + [(ua[0] + 120, ua[1]), (sp[0] + 160, sp[1] - 40), (sp[0], sp[1] - 40)]).buffer(0)
    inner = panel.buffer(-B.KEEP_SIDE, join_style="mitre")
    inner = inner.union(affinity.translate(inner, 0, B.KEEP_SIDE - B.KEEP_HEM).intersection(box(-500, 0, 500, hem - B.KEEP_HEM)))
    gap_b = ARM.buffer(B.WRAP_BACK)
    kx = mt["block"].chest2 / mM["block"].chest2
    zone_y = ua[1] + (334 - mM["ua_b"][1])
    arm_zone = panel.intersection(box(150 * kx, 0, 500, zone_y)).difference(gap_b)
    back_clip = inner.union(arm_zone).intersection(panel).difference(gap_b).intersection(box(-500, -100, 500, hem - B.KEEP_HEM))
    sleeve_clip = sleeve_R.difference(ARM.buffer(B.WRAP_SLEEVE))
    def build(clip):
        vis = []; above = Polygon()
        from shapely.validation import make_valid
        clip = make_valid(clip).buffer(0)
        for r in reversed(items):
            try:
                gg = r["geom"].intersection(clip)
                v = gg.difference(above); above = above.union(gg)
            except Exception:
                gg = make_valid(r["geom"]).buffer(0.001).buffer(-0.001).intersection(clip)
                v = gg.difference(above.buffer(0)); above = above.buffer(0).union(gg)
            vis.append(dict(r, geom=v))
        vis.reverse()
        vis = [v for v in vis if not v["geom"].is_empty and v["geom"].area > 0.02]
        return B.absorb_slivers(vis)
    vb = build(back_clip); vs = build(sleeve_clip)
    # sleeve art -> seam coords (s from the shoulder seam along the armhole, d into the sleeve)
    def to_seam(geom):
        def f(x, y, z=None):
            xs, ys = np.atleast_1d(x), np.atleast_1d(y); ox, oy = [], []
            for a, b_ in zip(xs, ys):
                p = Point(a, b_); s = ARM.project(p); q = ARM.interpolate(s); ox.append(s); oy.append(p.distance(q))
            return np.array(ox), np.array(oy)
        from shapely.ops import transform
        return transform(f, geom).buffer(0)
    vs_seam = [dict(r, geom=to_seam(r["geom"])) for r in vs]
    vs_seam = [r for r in vs_seam if not r["geom"].is_empty and r["geom"].area > 0.02]
    # limb crossings (match marks) on this size
    bark = unary_union([r["geom"] for r in items if r["layer"] == 5]).intersection(ARM)
    segs = [bark] if bark.geom_type == "LineString" else [q for q in getattr(bark, "geoms", []) if q.geom_type == "LineString"]
    marks = sorted((min(ARM.project(Point(q.coords[0])), ARM.project(Point(q.coords[-1]))),
                    max(ARM.project(Point(q.coords[0])), ARM.project(Point(q.coords[-1])))) for q in segs if q.length > 1.5)
    info = dict(size=size, grade=G, scale=sc, dx=dx, dy=dy, marks=marks, armhole_len=ARM.length)
    return vb, vs_seam, info

if __name__ == "__main__":
    for size in sys.argv[1:]:
        vb, vs, info = art_for_size(size)
        vb = dst2.clean_vis(vb); vs = dst2.clean_vis(vs)
        pickle.dump({"back": vb, "sleeve": vs, "info": info}, open(f"back_{size}.pkl", "wb"))
        print(size, len(vb), len(vs), {k: (round(v, 1) if isinstance(v, float) else v) for k, v in info.items() if k != "marks"}, "marks", len(info["marks"]), flush=True)
