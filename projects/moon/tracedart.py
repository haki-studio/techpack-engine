"""Rev B (fidelity first): every moon tone, cloud lobe/band/line and pole part TRACED from the mockup (trace.py), mapped
to garment mm on the size-M pattern. Output cached in traced_M.pkl (rebuild: ./py.sh tracedart.py).

Mockup -> mm (inputs/back.png, front.png, 724 x 870 px; source is ONE low-res image, so shapes are redrawn from the
x4 Lanczos upscale, not traced at stitch resolution — said on every spec page):
  back:  moon centre px (346, 335) -> (0, 244) mm, 1.08 mm/px (moon Ø 222 px -> 240 mm). Above py 430 (pole top) the
         whole scene uses 1.08 mm/px so clouds overlap the moon exactly as drawn; below it the body is shorter in the
         render than on the pattern, so y compresses 0.86 mm/px (pole bottom lands 10 above the hem seam). x stays 1.08.
         Each cloud keeps its own shape at 1.08 mm/px around its centroid.
  front: x = (px - 378) * 1.25, y = py - 170 (CF neck) for positions; cloud shapes 1.10 mm/px around their centroid;
         the front pole group is fitted between y 325 and 500 (10 above the hem seam), x scale 0.85, centre x 246.
  sleeves: centroid mapped by distance from the shoulder point (along the sleeve) and lateral position between the
         outer fold and the underarm seam; shapes 1.20 mm/px."""
import math, pickle, os, sys
import numpy as np
from PIL import Image
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union
from shapely import affinity
import moonpal
from moonpal import SEG
import trace as TR
import moonpattern, pattern as PT
from motifs2 import R

BACK = Image.open("inputs/back.png").convert("RGB"); FRONT = Image.open("inputs/front.png").convert("RGB")
MOON_C_PX, MOON_R_PX = (346.0, 335.0), 111.0
K = 1.08
def BX(px): return (px - 346.5) * K
def BY(py): return 244 + (py - 335) * K if py <= 430 else 244 + 95 * K + (py - 430) * 0.86
def back_pt(px, py): return (BX(px), BY(py))

def tones(names): return [(n, SEG[n]) for n in names]
CLOUD = ["c1", "c2", "c3", "c4", "c5"]; MOON = ["m1", "m2", "m3", "m4", "m5"]; POLE = ["p1", "p2", "p3", "p4"]
CODE = {"m1": "MN-hl", "m2": "MN", "m3": "MN-warm", "m4": "MN-crater", "m5": "MN-mare",
        "c1": "CL-hl", "c2": "CL-top", "c3": "CL", "c4": "CL-mid", "c5": "CL-shade",
        "p1": "PL-hl", "p2": "PL", "p3": "PL-shade", "p4": "PL-band"}

def polys(g):
    if g.is_empty: return []
    if g.geom_type == "Polygon": return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]

def width(p): return 2 * p.area / max(p.length, 1e-6)

def map_geom(g, f):
    from shapely.ops import transform
    return transform(lambda x, y, z=None: f(np.asarray(x), np.asarray(y)), g)

# ---------------------------------------------------------------- moon
def moon():
    box_px = (232, 221, 462, 451)
    def mask(rc, up, b):
        r, c = rc; X = c / up + b[0]; Y = r / up + b[1]
        return np.hypot(X - MOON_C_PX[0], Y - MOON_C_PX[1]) < MOON_R_PX
    tr = TR.trace(BACK, box_px, tones(MOON + CLOUD + ["p4", "navy", "navy2"]), keep=MOON, mask=mask,
                  fill_holes_from=None, sigma=0.5, majority=5, min_px=3)
    # the figure, the pole top and clouds over the moon are not moon: those pixels become moon cream (m2) under them
    lab, up = tr["_lab"]; names = [t_[0] for t_ in tones(MOON + CLOUD + ["p4", "navy", "navy2"])]
    sink = np.isin(lab, [names.index(n) for n in CLOUD + ["p4", "navy", "navy2"]])
    from scipy import ndimage as _ndi
    sink = _ndi.binary_dilation(sink, iterations=2 * up) & (lab >= 0)
    lab2 = np.where(sink, names.index("m2"), lab)
    for n in MOON: tr[n] = TR.polys_of(lab2 == names.index(n), up, box_px, 3)
    f = lambda x, y: ((x - MOON_C_PX[0]) * K, 244 + (y - MOON_C_PX[1]) * K)
    disc = Point(0, 244).buffer(MOON_R_PX * K, 360)
    regs = {}
    for n in MOON:
        g = map_geom(tr[n], f).buffer(0).intersection(disc)
        regs[n] = g.buffer(0.25).buffer(-0.25) if not g.is_empty else g
    # faint warm rim: 2.5 mm ring of the warm tone around the edge (the mockup's soft warm edge)
    rim = disc.difference(disc.buffer(-2.5))
    out = []
    for n in ("m2", "m1", "m3", "m4", "m5"):
        g = regs[n]
        if n == "m3": g = g.union(rim)
        else: g = g.difference(rim)
        out.append((n, g))
    # fine directional texture: every tone cut into 15° sectors, rows concentric (perpendicular to the radius)
    vis = []
    for n, g in out:
        for k in range(24):
            a0 = math.radians(k * 15); a1 = math.radians((k + 1) * 15)
            sec = Polygon([(0, 244)] + [(400 * math.cos(a), 244 + 400 * math.sin(a)) for a in np.linspace(a0, a1, 6)])
            q = g.intersection(sec)
            if q.is_empty or q.area < 0.5: continue
            ang = math.degrees((a0 + a1) / 2) + 90
            vis.append(R(n, q, "tatami", ang, CODE[n]))
    return vis, disc

# ---------------------------------------------------------------- clouds (a whole image area; each connected cloud = one motif)
def cloud_components(img, box_px, extra_sinks, mask=None, split_x=None):
    tr = TR.trace(img, box_px, tones(CLOUD + extra_sinks), keep=CLOUD, line_tone="c5", line_w_px=1.4, mask=mask, sigma=0.5, majority=5, min_px=3)
    # cloud = noticeably lighter than the local fabric (lit sleeves read as cloud indigo/violet by colour alone)
    from scipy import ndimage as _ndi
    a_ = np.asarray(img.crop(box_px).convert("L")).astype(float)
    bg = _ndi.grey_dilation(_ndi.grey_erosion(a_, size=31), size=31)
    lab, up = tr["_lab"]
    con = np.kron((a_ - bg) > 22, np.ones((up, up), bool))[:lab.shape[0], :lab.shape[1]]
    names = [t_[0] for t_ in tones(CLOUD + extra_sinks)]
    cm = np.isin(lab, [names.index(n) for n in CLOUD[:4]]) & con
    U = TR.polys_of(cm, up, box_px, 3).buffer(1.2).buffer(-1.2)
    comps = [p for p in polys(U) if p.area > 60]
    if split_x is not None:
        cs = []
        for p in comps:
            for xs in split_x:
                pass
            cs.append(p)
        comps = cs
    out = []
    for p in comps:
        regs = []
        for n in CLOUD:
            g = tr[n].intersection(p.buffer(1.0 if n != "c5" else 0.6))
            for q in polys(g):
                if q.area < 1.2: continue
                regs.append((n, q))
        lines = [ln.intersection(p.buffer(1.5)) for ln in tr["LINES"] if ln.intersects(p)]
        lines = [l for l in lines if not l.is_empty and l.length > 2]
        out.append(dict(px=p, regs=regs, lines=lines))
    return out

def place_cloud(c, centre_mm, s):
    """cloud component (px) -> regions in mm: iso scale s about its centroid, centroid to centre_mm"""
    cx, cy = c["px"].centroid.x, c["px"].centroid.y
    f = lambda x, y: (centre_mm[0] + (x - cx) * s, centre_mm[1] + (y - cy) * s)
    vis = []
    for n, q in c["regs"]:
        g = map_geom(q, f).buffer(0)
        for p in polys(g):
            st, ang = ("satin", "auto") if width(p) < 3.0 else ("tatami", 0)
            vis.append(R(n, p, st, ang, CODE[n]))
    for ln in c["lines"]:
        for seg in ([ln] if ln.geom_type == "LineString" else [g for g in getattr(ln, "geoms", []) if g.geom_type == "LineString"]):
            m = map_geom(seg, f)
            if m.length > 3: vis.append(R("c5", m.buffer(0.35, cap_style="round"), "bean", None, "CL-line"))
    return vis

def back_clouds():
    def mask(rc, up, b):
        r, c = rc; X = c / up + b[0]; return (X > 100) & (X < 625)
    comps = cloud_components(BACK, (100, 290, 625, 530), MOON + POLE + ["navy", "navy2"], mask=mask)
    out = []
    for c in comps:
        cx, cy = c["px"].centroid.x, c["px"].centroid.y
        if c["px"].area < 150 or cx > 600: continue                  # x > 600: right-sleeve cloud edge inside the crop (04)
        out.append(dict(vis=place_cloud(c, back_pt(cx, cy), K), px=(cx, cy), bbox=c["px"].bounds))
    return out

# ---------------------------------------------------------------- pole groups
# hardware silhouettes read off the x4 / x5 upscales (mockup px); tones are traced INSIDE them (the render's dark pole
# shadows are too close to the navy fabric to separate by colour alone). Order = back to front. (dx, dy) = mm nudge.
def quad(p0, p1, w):
    return LineString([p0, p1]).buffer(w / 2, cap_style="flat")
BACK_PARTS = [("pole", Polygon([(336, 426), (357, 426), (360.5, 697), (332.5, 697)]), 0, 0),
              ("can", box(359, 495, 402, 576), 0, 0), ("can_strap_t", box(356, 508, 362, 514), 0, 0), ("can_strap_b", box(356, 558, 362, 564), 0, 0),
              ("small_can", box(308.5, 532, 335, 589), 0, 0),
              ("arm", quad((289, 498.5), (433, 462), 6.5), 0, 0),
              ("pinA", box(381.5, 446, 395.5, 471), 0, 0), ("pinB", box(408.5, 440, 421.5, 467), 0, 0),
              ("string_rope", box(299, 519, 337, 538), 0, 0), ("string_discs", box(254, 526, 301, 549), 0, 0), ("string_bolt", box(242, 533, 256, 542), 0, 0),
              ("ins_low", Polygon([(358, 596), (380, 596), (408, 601), (408, 609), (380, 614), (358, 614)]), 0, 0)]
FRONT_PARTS = [("pole", Polygon([(569.5, 484), (588.5, 484), (591.5, 671), (560.5, 671)]), 0, 0),
               ("canR", box(589, 555, 616, 622), 0, 0), ("canL", box(544.5, 589, 564, 634), 0, 7.0),
               ("bracket", box(587, 639, 613, 663), 0, 0),
               ("arm", quad((527, 546), (628, 521), 5.5), 0, 0),
               ("pin", box(601.5, 495, 614, 523), 0, 0),
               ("string_rope", box(521, 574, 567, 591), 0, 7.0), ("string_discs", box(479, 578, 523, 600), 0, 7.0), ("string_bolt", box(465, 582, 481, 592), 0, 7.0)]

def pole_group(img, parts, f):
    U = unary_union([p for _, p, _, _ in parts]); b = [int(v) for v in U.bounds]; bx = (b[0] - 2, b[1] - 2, b[2] + 3, b[3] + 3)
    def mask(rc, up, bb):
        r, c = rc; X = c / up + bb[0]; Y = r / up + bb[1]
        from shapely import contains_xy
        return contains_xy(U.buffer(0.3), X, Y)
    tr = TR.trace(img, bx, tones(POLE), keep=POLE, line_tone="p4", line_w_px=1.3, mask=mask, sigma=0.35, majority=3, min_px=1)
    # hardware other than the pole body: drop the navy fabric that the rectangle silhouettes include
    trn = TR.trace(img, bx, tones(POLE + ["navy", "navy2"]), keep=POLE, line_tone="p4", line_w_px=1.3, mask=mask, sigma=0.35, majority=3, min_px=1)
    vis = []
    later = [unary_union([p for _, p, _, _ in parts[i + 1:]]) if i + 1 < len(parts) else Polygon() for i in range(len(parts))]
    for i, (nm, part, dx, dy) in enumerate(parts):
        own = part.difference(later[i]) if not later[i].is_empty else part
        g_f = lambda x, y, dx=dx, dy=dy: tuple(np.asarray(v) + o for v, o in zip(f(x, y), (dx, dy)))
        src = tr if nm == "pole" else trn
        for n in POLE:
            g = map_geom(src[n].intersection(own), g_f).buffer(0)
            for p in polys(g):
                if p.area < 0.5: continue
                st, ang = ("satin", "auto") if width(p) < 3.0 else ("tatami", "auto")
                vis.append(R(n, p, st, ang, CODE[n]))
        for ln in src["LINES"]:
            m = ln.intersection(own)
            if m.is_empty: continue
            m = map_geom(m, g_f)
            for seg in ([m] if m.geom_type == "LineString" else [g for g in getattr(m, "geoms", []) if g.geom_type == "LineString"]):
                if seg.length > 2.5: vis.append(R("p4", seg.buffer(0.35, cap_style="round"), "bean", None, "PL-line"))
    return vis

BACK_TIPS_PX = {"armL": (290, 498), "armR": (432, 462), "pinA": (388.5, 447), "pinB": (415, 441), "strL": (243, 537),
                "strL2": (246, 539), "canL": (321, 588), "insR": (408, 605), "canR": (401, 503), "pole": (346, 560)}
def bpole_f(x, y): return (BX(x), np.where(np.asarray(y) <= 430, 244 + (np.asarray(y) - 335) * K, 244 + 95 * K + (np.asarray(y) - 430) * 0.86))
def back_pole():
    vis = pole_group(BACK, BACK_PARTS, bpole_f)
    tips = {k: tuple(float(v) for v in bpole_f(*v)) for k, v in BACK_TIPS_PX.items()}
    return vis, tips

FPX, FPY0, FPY1 = 577.0, 485.0, 671.0
FRONT_POLE = dict(cx=246.0, y0=325.0, y1=500.0, sx=0.85)
def front_pole_f(x, y):
    sy = (FRONT_POLE["y1"] - FRONT_POLE["y0"]) / (FPY1 - FPY0)
    return (FRONT_POLE["cx"] + (np.asarray(x) - FPX) * FRONT_POLE["sx"], FRONT_POLE["y0"] + (np.asarray(y) - FPY0) * sy)
FRONT_TIPS_PX = {"armL": (528, 546), "armR": (627, 521), "pin": (607.5, 496), "strL": (466, 587), "strL2": (468, 589),
                 "canL": (554, 634), "canR": (615, 562), "pole": (591, 600), "poleL": (562, 640), "bracket": (612, 655)}
TIP_DY = {"strL": 7.0, "strL2": 7.0, "canL": 7.0}
def front_pole():
    vis = pole_group(FRONT, FRONT_PARTS, front_pole_f)
    tips = {k: (float(front_pole_f(*v)[0]), float(front_pole_f(*v)[1]) + TIP_DY.get(k, 0.0)) for k, v in FRONT_TIPS_PX.items()}
    return vis, tips

# ---------------------------------------------------------------- front clouds (chest 02, lower 03) + sleeves (04)
def FX(px): return (px - 378) * 1.25
def FYm(py): return py - 170
def front_clouds():
    comps = cloud_components(FRONT, (0, 240, 724, 580), POLE + ["navy", "navy2"])
    chest, lower, sleeves = [], [], []
    for c in comps:
        p = c["px"]
        # split a component at the body edges (the mockup runs some clouds over the hanging sleeves)
        for part, where in ((p.intersection(box(0, 0, 138, 900)), "sR"), (p.intersection(box(138, 0, 615, 900)), "body"), (p.intersection(box(615, 0, 724, 900)), "sL")):
            for q in polys(part):
                if q.area < 60: continue
                sub = dict(px=q, regs=[(n, g.intersection(q)) for n, g in c["regs"] if not g.intersection(q).is_empty],
                           lines=[l.intersection(q.buffer(1)) for l in c["lines"] if l.intersects(q)])
                cx, cy = q.centroid.x, q.centroid.y
                if where == "body":
                    (lower if cy > 470 else chest).append(dict(c=sub, px=(cx, cy), side="L" if cx > 378 else "R"))
                else:
                    sleeves.append(dict(c=sub, px=(cx, cy), view="front", sleeve="04R" if where == "sR" else "04L"))
    return chest, lower, sleeves

def back_sleeve_clouds():
    comps = cloud_components(BACK, (0, 290, 724, 640), MOON + POLE + ["navy", "navy2"])
    out = []
    for c in comps:
        p = c["px"]
        for part, sl in ((p.intersection(box(0, 0, 100, 900)), "04L"), (p.intersection(box(622, 0, 724, 900)), "04R")):
            for q in polys(part):
                if q.area < 60: continue
                sub = dict(px=q, regs=[(n, g.intersection(q)) for n, g in c["regs"] if not g.intersection(q).is_empty],
                           lines=[l.intersection(q.buffer(1)) for l in c["lines"] if l.intersects(q)])
                out.append(dict(c=sub, px=(q.centroid.x, q.centroid.y), view="back", sleeve=sl))
    return out

def sleeve_pos(s, size="M"):
    """mockup sleeve-cloud centroid -> S01/S02 pattern coords. Flat-lay sleeves: shoulder point at py 215 (front) /
    py 225 (back); the outer fold is the sleeve centre line; the inner edge is the underarm seam."""
    g, mt = PT.draft(size); L = mt["cap_h"] + mt["Lu"]
    px, py = s["px"]
    sp_y = 215 if s["view"] == "front" else 225
    d = (py - sp_y) / (790 - sp_y) * L                      # along the sleeve, 0 = cap top
    y = -mt["cap_h"] + d
    # lateral: fraction between the outer edge (0) and the underarm/body edge (1) of the flat-lay sleeve
    if s["view"] == "front":
        if s["sleeve"] == "04R": xo, xi = 30 - (py - 215) * 0.03, 140
        else:                    xo, xi = 700 + (py - 215) * 0.03, 612
    else:
        if s["sleeve"] == "04L": xo, xi = 10, 100
        else:                    xo, xi = 715, 622
    fr = min(0.85, max(0.15, (px - xo) / (xi - xo)))
    Wy = mt["W"] + (mt["Ww"] - mt["W"]) * min(1, max(0, y / mt["Lu"]))
    half = (1 if s["view"] == "front" else -1) * (1 if s["sleeve"] == "04R" else -1)   # S01 front x > 0; S02 = mirror
    return (half * fr * Wy * 0.92, y)

def build_all():
    out = {}
    out["moon"], out["disc"] = moon()
    out["back_clouds"] = back_clouds()
    out["back_pole"], out["back_tips"] = back_pole()
    chest, lower, sl_f = front_clouds()
    out["chest"] = [dict(vis=place_cloud(c["c"], (FX(c["px"][0]), FYm(c["px"][1])), 1.10), px=c["px"], side=c["side"]) for c in chest]
    out["lower"] = [dict(vis=place_cloud(c["c"], (FX(c["px"][0]), FYm(c["px"][1])), 1.10), px=c["px"], side=c["side"]) for c in lower]
    out["front_pole"], out["front_tips"] = front_pole()
    sl = sl_f + back_sleeve_clouds()
    out["sleeves"] = [dict(vis=place_cloud(s["c"], sleeve_pos(s), 1.20), px=s["px"], view=s["view"], sleeve=s["sleeve"]) for s in sl]
    return out

def sanitize(d):
    from shapely.validation import make_valid
    def fx(vis):
        out = []
        for r in vis:
            g = r["geom"]
            if not g.is_valid: g = make_valid(g)
            g = g.buffer(0) if r["st"] not in ("bean", "run") else g
            g = unary_union(polys(g)) if g.geom_type == "GeometryCollection" else g
            if not g.is_empty and g.area > 0.05: out.append(dict(r, geom=g))
        return out
    d["moon"] = fx(d["moon"]); d["back_pole"] = fx(d["back_pole"]); d["front_pole"] = fx(d["front_pole"])
    for k in ("back_clouds", "chest", "lower", "sleeves"):
        for c in d[k]: c["vis"] = fx(c["vis"])
    return d

def load():
    p = "traced_M.pkl"
    srcs = ["inputs/back.png", "inputs/front.png", "tracedart.py"]
    if os.path.exists(p) and all(os.path.getmtime(p) > os.path.getmtime(s) for s in srcs):
        return pickle.load(open(p, "rb"))
    d = sanitize(build_all()); pickle.dump(d, open(p, "wb")); return d

if __name__ == "__main__":
    import time; t = time.time(); d = sanitize(build_all()); pickle.dump(d, open("traced_M.pkl", "wb"))
    print("moon regions", len(d["moon"]), "back clouds", len(d["back_clouds"]), "back pole", len(d["back_pole"]),
          "chest", [(c["side"], len(c["vis"])) for c in d["chest"]], "lower", len(d["lower"]), "front pole", len(d["front_pole"]),
          "sleeves", [(s["sleeve"], s["view"]) for s in d["sleeves"]], f"{time.time()-t:.0f}s")
