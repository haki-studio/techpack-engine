"""Auto-generate a DRAFT stitch file (DST + PES) for the back scene from the region art.
Per region: tatami / padded / satin / radial / bean / run, at the spec angles and densities."""
import math, pickle, sys
import numpy as np
import pyembroidery as pe
from shapely.geometry import LineString, MultiLineString, Polygon, Point
from shapely import affinity
from shapely.ops import unary_union
import tech, stitchrender as SR
from motifs2 import HEX, PAL
import specbase as SB

U = 10.0                 # pyembroidery units per mm (0.1 mm)
TRIM_JUMP = 6.0          # mm  (shorter moves stay as jumps; Hatch can auto-trim them)

def rows(p, ang, sp):
    return SR.hatch(p, ang, sp)

def serp(segs):
    """order hatch rows boustrophedon"""
    out = []
    for i, s in enumerate(segs):
        cs = list(s.coords)
        if len(cs) < 2: continue
        a, b = cs[0], cs[-1]
        out.append((a, b) if i % 2 == 0 else (b, a))
    return out

def subdivide(a, b, L):
    d = math.hypot(b[0]-a[0], b[1]-a[1]); n = max(1, int(math.ceil(d / L)))
    return [(a[0] + (b[0]-a[0])*k/n, a[1] + (b[1]-a[1])*k/n) for k in range(1, n+1)]

def tatami(p, ang, sp=0.40, L=3.5, under=True):
    pts = []
    if under and p.area > 6:
        inner = p.buffer(-0.6)
        for q in SR.polys(inner):
            for a, b in serp(rows(q, ang + 90, 2.0)):
                pts += [a] + subdivide(a, b, 3.0)
    off = 0
    for i, (a, b) in enumerate(serp(rows(p, ang, sp))):
        d = math.hypot(b[0]-a[0], b[1]-a[1]); ux, uy = (b[0]-a[0])/max(d, 1e-9), (b[1]-a[1])/max(d, 1e-9)
        t = (i % 3) * L / 3; seq = [a]
        while t + 0.3 < d:
            t += L if t > 0 else (L - (i % 3) * L / 3 or L)
            seq.append((a[0] + ux*min(t, d), a[1] + uy*min(t, d)))
        if seq[-1] != b: seq.append(b)
        pts += seq
    return pts

def satin(p, ang, sp=0.38):
    pts = []
    if p.area > 4:   # centre-run underlay along the long axis
        c = p.buffer(-0.5)
        for q in SR.polys(c):
            for a, b in serp(rows(q, ang + 90, 1.6))[:1]:
                pts += [a] + subdivide(a, b, 2.5)
    for a, b in serp(rows(p, ang, sp)):
        d = math.hypot(b[0]-a[0], b[1]-a[1])
        if d > 7.0:   # split satin
            n = int(math.ceil(d / 7.0)); pts += [a] + subdivide(a, b, d / n)
        else:
            pts += [a, b]
    return pts

def radial_fill(p, cx, cy, sp=0.40):
    pts = []
    for i, s in enumerate(SR.radial(p, cx, cy, sp)):
        cs = list(s.coords)
        if len(cs) < 2: continue
        a, b = (cs[0], cs[-1]) if i % 2 == 0 else (cs[-1], cs[0])
        d = math.hypot(b[0]-a[0], b[1]-a[1])
        pts += [a] + (subdivide(a, b, 3.5) if d > 7 else [b])
    return pts

def line_run(p, L=2.0, triple=True):
    """centre path of a thin line polygon ≈ its exterior; triple = bean (forward, back, forward)."""
    ring = p.exterior
    n = max(3, int(ring.length / L))
    path = [ring.interpolate(i * ring.length / n).coords[0] for i in range(n + 1)]
    return path        # going round a 0.7-wide line = 2 passes along it (bean look); run = same at 2.6 spacing

def split_long(pts, max_link=2.6, max_sat=7.2, sat=False):
    """break a point list into sew-able blocks wherever a link is longer than allowed
    (satin: alternate links are the satin stitches themselves, allowed up to max_sat)."""
    blocks, cur = [], [pts[0]]
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        d = math.hypot(b[0]-a[0], b[1]-a[1])
        lim = max_sat if sat else 4.2
        if d > lim and not (sat and d <= max_sat):
            if len(cur) > 1: blocks.append(cur)
            cur = [b]; continue
        if d < 0.3 and len(cur) > 1: continue
        cur.append(b)
    if len(cur) > 1: blocks.append(cur)
    return blocks

def region_stitches(r):
    out = []
    st = r["st"]; ang = r["ang"]
    for p in SR.polys(r["geom"]):
        if p.area < 0.08: continue
        if st in ("bean", "run"):
            out.append(line_run(p, 2.0 if st == "bean" else 2.6, st == "bean")); continue
        if isinstance(ang, tuple):
            out.append(radial_fill(p, ang[1], ang[2])); continue
        a = SR.auto_angle(p) if ang in ("auto", None) else ang
        if st == "padded":
            pad = tatami(p.buffer(-0.5), a + 90, 0.8, 4.0, under=False) + tatami(p.buffer(-0.5), a + 45, 0.8, 4.0, under=False) if p.area > 8 else []
            out.append(pad + tatami(p, a, 0.38, 5.0, under=False))
        elif st == "tatami":
            out.append(tatami(p, a))
        else:
            out.append(satin(p, a))
    res = []
    sat = st == "satin" or (isinstance(ang, tuple) and st == "satin")
    for b in out:
        if len(b) > 1: res += split_long(b, sat=sat)
    return res

def nn_order(blocks):
    if not blocks: return []
    rest = list(blocks); out = [rest.pop(0)]
    while rest:
        e = out[-1][-1]
        j = min(range(len(rest)), key=lambda k: (rest[k][0][0]-e[0])**2 + (rest[k][0][1]-e[1])**2)
        out.append(rest.pop(j))
    return out

def build(vis, stops, origin, out_base):
    pat = pe.EmbPattern()
    ox, oy = origin
    total = 0
    for si, s in enumerate(stops):
        k = s["col"]; iso, pn = SB.TH[k]["isacord"], SB.TH[k]["polyneon"]
        th = pe.EmbThread(); th.set_hex_color(HEX[k]); th.description = f"{PAL[k][1]} (Polyneon {pn[0]} / Isacord {iso[0]})"
        th.brand = "Madeira Polyneon"; th.catalog_number = pn[0]
        pat.add_thread(th)
        if si > 0: pat.add_command(pe.COLOR_CHANGE)
        # fills before lines inside the stop
        regs = sorted(s["regions"], key=lambda r: {"tatami": 0, "padded": 1, "satin": 2, "run": 3, "bean": 4}[r["st"]])
        blocks = []
        for r in regs: blocks += region_stitches(r)
        blocks = nn_order(blocks)
        last = None
        for b in blocks:
            x0, y0 = b[0]
            if last is not None and math.hypot(x0 - last[0], y0 - last[1]) > TRIM_JUMP:
                pat.add_command(pe.TRIM)
            pat.add_stitch_absolute(pe.JUMP, (x0 - ox) * U, (y0 - oy) * U)
            for (x, y) in b:
                pat.add_stitch_absolute(pe.STITCH, (x - ox) * U, (y - oy) * U); total += 1
            last = b[-1]
        pat.add_command(pe.TRIM)
    pat.add_command(pe.END)
    settings = {"long_stitch_contingency": pe.CONTINGENCY_LONG_STITCH_SEW_TO, "max_stitch": 121, "max_jump": 121, "tie_on": True, "tie_off": True}
    pe.write_dst(pat, out_base + ".dst", settings)
    pe.write_pes(pat, out_base + ".pes", {**settings, "pes version": 6})
    return total, pat

if __name__ == "__main__":
    d = pickle.load(open("back2_vis.pkl", "rb"))
    vb = d["back"]
    stops = tech.stops(vb)
    ub = unary_union([r["geom"] for r in vb]).bounds
    cx, cy = (ub[0] + ub[2]) / 2, (ub[1] + ub[3]) / 2      # design centred on the art box centre
    n, pat = build(vb, stops, (cx, cy), "out/01_back-scene/HAKI_jacket_01_back-scene_DRAFT")
    ext = pat.extents()
    print("stitches", n, "stops", len(stops), "extents mm", [round(v/10, 1) for v in ext], "centre", round(cx, 1), round(cy, 1))
