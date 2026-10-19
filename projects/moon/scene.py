"""Moon jacket scene composition — Rev B (fidelity first). The moon tones, every cloud (lobes, bands, highlights,
indigo scallop lines, tails) and both poles with their hardware are TRACED from the mockup (tracedart.py, x4 Lanczos
read of a low-res render) and placed on the size-M pattern; wires are drawn parametric so they meet the side seams.
Garment coords: back x from CB (+ = wearer's right), y down from CB neck seam; fronts x from CF (+ = wearer's left),
y from CF neck seam; sleeves in S01/S02 pattern coords.

Elements
  01  back scene     — moon, clouds, pole, wires, LICENSED-FIGURE PLACEHOLDER BOX (knocked out) — per size
  01b moon-in-box    — our moon fill inside the box, sewn before the factory's licensed figure [proposed] — per size
  02  chest clouds   — 02R wearer's right front, 02L wearer's left front — graded A/B/C
  03  lower front    — 03L pole + wires + cloud (wearer's left), 03R wires (wearer's right) — per size
  04  sleeve clouds  — 04R right sleeve (S01), 04L left sleeve (S02) — graded A/B/C
Wires wrap back <-> front across the SIDE SEAMS (end 3 mm short on both pieces, same height above the hem seam)
and cross the CF zip (end 15 mm each side, same curve); where a wire passes a welt pocket it stops 6 mm short of
the welt box on both sides (it reads as passing behind the pocket) — so 01 and 03 are rebuilt per size."""
import math, random
import shapely
import numpy as np
from shapely.geometry import Point, Polygon, LineString, box
from shapely.ops import unary_union, substring
from shapely import affinity
from shapely.validation import make_valid
import moonpal
import moonpattern, pattern as PT
import moonmotifs as MM
import front as FR
import tracedart as TA

GRADE = {"XS": ("A", 0.92), "S": ("A", 0.92), "M": ("B", 1.0), "L": ("B", 1.0), "XL": ("B", 1.0), "XXL": ("C", 1.08), "3XL": ("C", 1.08)}
SCALE = {"A": 0.92, "B": 1.0, "C": 1.08}
KEEP = dict(seam=15.0, side=15.0, cf=15.0, hem=10.0, welt=6.0, collar=6.0, neck=6.0, cuff=10.0, wrap=FR.WRAP)
L_MOON, L_MDET, L_WIRE, L_CLOUD, L_POLE, L_HW = 11, 12, 15, 14, 15, 15     # wires + pole + hardware share one layer -> one stop per grey

# ---------------------------------------------------------------- placeholder box (licensed figure), M, back coords
# mockup figure (back.png) x 318..375 px, y 362..430 px (head to feet, incl. the stick) -> 62 x 73 mm at 1.08 mm/px,
# + 3 mm margin; bottom = pole top. PROPOSED — confirm against the licensor art.
BOX_M = (-34.0, 268.0, 34.0, 347.0)
MOON_R = TA.MOON_R_PX * TA.K

# ---------------------------------------------------------------- wire network (heights above the hem seam, mm, M) read off the mockup
# back left side seam (wearer's left)  <-> front wearer's-left side seam (03L, short wires from the pole)
H_LEFT = [153.0, 94.0, 60.0, 50.0, 20.0]          # Rev C final: read off the back close-up wires extrapolated to the seam (M)
# back right side seam (wearer's right) <-> front wearer's-right side seam (03R, wires from the 03L pole across the zip)
H_RIGHT = [130.0, 83.0]

def edge(g, pc, name): return LineString(next(e.pts for e in g[pc].edges if e.name == name))

def size_tf(size):
    g, mt = PT.draft(size); gM, mM = PT.draft("M"); sc = SCALE[GRADE[size][0]]
    kx = mt["block"].chest2 / mM["block"].chest2
    return g, mt, mM, sc, kx

def tf_regs(regs, sc, anchor_from, anchor_to, dx=0.0):
    out = []
    for r in regs:
        g = affinity.scale(r["geom"], sc, sc, origin=anchor_from)
        g = affinity.translate(g, anchor_to[0] - anchor_from[0] + dx, anchor_to[1] - anchor_from[1])
        ang = r["ang"]
        if isinstance(ang, tuple):        # radial centre moves with the art
            px = anchor_to[0] + (ang[1] - anchor_from[0]) * sc + dx; py = anchor_to[1] + (ang[2] - anchor_from[1]) * sc
            ang = (ang[0], px, py)
        d_ = dict(r, geom=g if r["st"] in ("bean", "run") else g.buffer(0), ang=ang)
        if r.get("rows") is not None:          # moon flow rows (moon3) move with their region
            d_["rows"] = affinity.translate(affinity.scale(r["rows"], sc, sc, origin=anchor_from), anchor_to[0] - anchor_from[0] + dx, anchor_to[1] - anchor_from[1])
        out.append(d_)
    return out

WIRE_W = 1.6
def cord(p0, p1, sag):
    """wire as a twisted rope (close-up): the 1.6 mm cord cut into 2.2 mm twists, each a satin at 55° to the wire,
    a charcoal shade run along its lower edge, and a wrap at the insulator end (LESSONS A13)"""
    pts = MM.wire_pts(p0, p1, sag, n=max(20, int(math.dist(p0, p1) / 2)))
    ln = LineString(pts); L = ln.length; out = []
    k = 0; s = 0.0
    while s < L - 0.3:
        e = min(L, s + 2.2)
        seg = substring(ln, s, e)
        if seg.length > 0.2:
            a, b = seg.coords[0], seg.coords[-1]; tang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
            out.append(dict(col="p2", geom=seg.buffer(WIRE_W / 2 + 0.05, cap_style="flat"), st="satin", ang=tang + 55, grp="WR"))
        s = e; k += 1
    shade = ln.parallel_offset(WIRE_W * 0.32, "right")
    if not shade.is_empty: out.append(dict(col="p4", geom=shade.buffer(0.25, cap_style="flat"), st="run", ang=None, grp="WR"))
    out.append(dict(col="p1", geom=Point(p0).buffer(1.6, 16), st="satin", ang="auto", grp="PL-hl"))
    return out

class Items(list):
    def add(self, regs, layer, el=None):
        for r in regs:
            if r["geom"] is not None and not r["geom"].is_empty:
                r = dict(r); r["z"] = len(self); r["layer"] = layer; r["el"] = el; self.append(r)

def fit(regs, clip, max_shift=60.0, tol=0.015):
    """smallest move that brings a traced motif inside the keep-out clip (tails may hang out tol of the area)"""
    U = unary_union([r["geom"] for r in regs if r["st"] not in ("bean", "run")])
    if U.is_empty: return regs, (0.0, 0.0)
    A = U.area
    def out_frac(dx, dy): return affinity.translate(U, dx, dy).difference(clip).area / A
    if out_frac(0, 0) <= tol: return regs, (0.0, 0.0)
    best = None
    for r in np.arange(1.0, max_shift + 0.1, 1.0):
        for th in np.linspace(0, 2 * math.pi, 36, endpoint=False):
            dx, dy = r * math.cos(th), r * math.sin(th)
            if out_frac(dx, dy) <= tol: best = (dx, dy); break
        if best: break
    if best is None: return regs, (0.0, 0.0)
    return [dict(r, geom=affinity.translate(r["geom"], *best), **({"rows": affinity.translate(r["rows"], *best)} if r.get("rows") is not None else {})) for r in regs], best

_T = None
def traced():
    global _T
    if _T is None:
        import closeart; _T = closeart.load()          # close-ups = tracing reference; mockup = placement (closeart docstring)
    return _T

# ================================================================ 01 back
def back_art(size="M"):
    g, mt, mM, sc, kx = size_tf(size); T_ = traced()
    A0 = (0.0, mM["hem_b"] - 10); A1 = (0.0, mt["hem_b"] - 10)
    P = lambda x, y: (A1[0] + (x - A0[0]) * sc, A1[1] + (y - A0[1]) * sc)
    it = Items()
    cb, cw = back_clips("M")
    mv = tf_regs(T_["moon"], sc, A0, A1)
    it.add([r for r in mv if r.get("under")], L_MOON, "01")          # ground tiles first
    it.add([r for r in mv if not r.get("under")], L_MDET, "01")      # then maria, stars, raised cells on top
    # wires (behind the clouds and the hardware), to the agreed heights at this size's side seams + 3 drop wires
    tips = {k: P(*v) for k, v in T_["back_tips"].items()}
    xs = mt["block"].chest2
    seamL = lambda h: (-xs, mt["hem_b"] - h * sc); seamR = lambda h: (xs, mt["hem_b"] - h * sc)
    # Rev C final: the back close-up's wire layout (closeart.BACK_TIPS_CU): 5 wires to the wearer's-left side seam, 2 out of
    # the wire wrap to the wearer's-right seam, the pins + transformer into the wrap, the lower insulator into the low right
    # wire, the second wire crossing the pole from the right pin down to the lower left wire, two short crossarm -> spool
    # wires and one drop from the small can to the hem (10 above the hem seam)
    W = [("coilL1", seamL(H_LEFT[0]), 0.03), ("coilL2", seamL(H_LEFT[1]), 0.03), ("poleLo", seamL(H_LEFT[2]), 0.02),
         ("coilL3", seamL(H_LEFT[3]), 0.02), ("canB", seamL(H_LEFT[4]), 0.02),
         ("wrap", seamR(H_RIGHT[0]), 0.03), ("wrap", seamR(H_RIGHT[1]), 0.02),
         ("pinB", tips["wrap"], 0.04), ("pinA", tips["wrap"], 0.05), ("drumR", tips["wrap"], 0.02),
         ("crossA", tips["crossEnd"], 0.02), ("armL1", tips["spoolT1"], 0.03), ("armL2", tips["spoolT2"], 0.03),
         ("canL", (tips["hemL"][0], mt["hem_b"] - 10), 0.02)]
    wires, ends = [], []
    for a, b, sg in W:
        p0 = tips[a]; span = abs(b[0] - p0[0])
        if abs(abs(b[0]) - xs) < 0.01: ends.append(("R" if b[0] > 0 else "L", round(mt["hem_b"] - b[1], 1), b, p0, sg * span))
        wires += cord(p0, b, sg * span)
    # lower insulator -> the low right wire (joins it where the close-up does, x of close-up px 1225)
    p0, b = tips["wrap"], seamR(H_RIGHT[1]); jx = P(*T_["back_junc"])[0]
    t = (jx - p0[0]) / (b[0] - p0[0]); jy = p0[1] + (b[1] - p0[1]) * t + 4 * 0.02 * abs(b[0] - p0[0]) * t * (1 - t)
    wires += cord(tips["insBlk"], (jx, jy), 0.02)
    wires.append(dict(col="p1", geom=Point(tips["wrap"]).buffer(2.6, 16), st="satin", ang="auto", grp="PL-hl"))     # wire wrap knot
    wires.append(dict(col="p4", geom=Point(tips["wrap"]).buffer(2.6, 16).exterior.buffer(0.3), st="run", ang=None, grp="PL-line"))
    it.add(wires, L_WIRE, "01")
    clouds = []
    for c in T_["back_clouds"]:
        regs, mv = fit(c["vis"], cb)
        clouds.append(mv); it.add(tf_regs(regs, sc, A0, A1), L_CLOUD, "01")
    it.add(tf_regs(T_["back_pole"], sc, A0, A1), L_POLE, "01")
    b0 = P(BOX_M[0], BOX_M[1]); b1 = P(BOX_M[2], BOX_M[3]); BOX = box(b0[0], b0[1], b1[0], b1[1])
    mc = P(0, 244)
    info = dict(size=size, grade=GRADE[size][0], scale=sc, box=BOX.bounds, moon=dict(c=mc, r=MOON_R * sc),
                pole=dict(x=0.0), wire_ends=[e[:3] for e in ends], wire_geo=ends, cloud_moves=clouds)
    return it, BOX, info

def moon_in_box(size="M"):
    """01b: our moon fill inside the placeholder box (same traced tones + concentric rows), to sew before the figure"""
    it, BOX, info = back_art(size)
    vis = [dict(r, geom=r["geom"].intersection(BOX)) for r in it if r["el"] == "01" and r["layer"] in (L_MOON, L_MDET)]
    return [v for v in vis if not v["geom"].is_empty and v["geom"].area > 0.3], BOX

def back_clips(size):
    g, mt = PT.draft(size); pc = g["B01"]; P_ = pc.sew_poly()
    def minus(names, k):
        return unary_union([edge(g, "B01", n).buffer(k) for n in names])
    base = P_.difference(minus(["armhole L", "armhole R", "shoulder L", "shoulder R"], KEEP["seam"])).difference(minus(["neck"], KEEP["neck"]))
    base = base.difference(minus(["hem"], KEEP["hem"]))
    art = base.difference(minus(["side L", "side R"], KEEP["side"]))
    wire = base.difference(minus(["side L", "side R"], KEEP["wrap"]))
    return make_valid(art).buffer(0), make_valid(wire).buffer(0)

# ================================================================ 03 lower front (per size)
def front_art(size="M"):
    g, mt, mM, sc, kx = size_tf(size); T_ = traced()
    A0 = (0.0, mM["hem_f"] - 10); A1 = (0.0, mt["hem_f"] - 10)
    PX = TA.FRONT_POLE["cx"]; dxp = PX * kx - PX * sc          # the pole group follows the chest grade (stays by the side seam)
    P = lambda x, y: (A1[0] + (x - A0[0]) * sc, A1[1] + (y - A0[1]) * sc)
    Pp = lambda x, y: (P(x, y)[0] + dxp, P(x, y)[1])
    it = Items(); fc = front_clips("M")
    tips = {k: Pp(*v) for k, v in T_["front_tips"].items()}
    xs = mt["block"].chest2
    seamL = lambda h: (xs, mt["hem_f"] - h * sc); seamR = lambda h: (-xs, mt["hem_f"] - h * sc)
    # Rev C final: seam heights follow the BACK close-up (5 wires at the wearer's-left seam, 2 at the wearer's-right one).
    # The front close-up shows 3 / 4 there (the two close-ups disagree, PROPOSED); its two extra left-going wires become
    # drops to the hem, so every wire that crosses a side seam lines up with its back half.
    W = [("pin", seamL(H_LEFT[0]), 0.03), ("canR", seamL(H_LEFT[1]), 0.03), ("pole", seamL(H_LEFT[2]), 0.02), ("poleL", seamL(H_LEFT[3]), 0.02),
         ("bracket", seamL(H_LEFT[4]), 0.02),
         ("armL", seamR(H_RIGHT[0]), 0.07), ("strL", seamR(H_RIGHT[1]), 0.06),
         ("strL2", (P(TA.FX(150), 0)[0], mt["hem_f"] - 10), 0.03), ("canL", (P(TA.FX(330), 0)[0], mt["hem_f"] - 10), 0.02),
         ("poleL", (P(TA.FX(500), 0)[0], mt["hem_f"] - 10), 0.02), ("bracket", (min(P(TA.FX(640), 0)[0] + dxp, xs - 20), mt["hem_f"] - 10), 0.02)]
    wires, ends = [], []
    for a, b, sg in W:
        p0 = tips[a]; span = abs(b[0] - p0[0])
        if abs(abs(b[0]) - xs) < 0.01: ends.append(("L" if b[0] > 0 else "R", round(mt["hem_f"] - b[1], 1), b, p0, (sg or 0.04) * span))
        wires += cord(p0, b, (sg or 0.04) * span)
    it.add(wires, L_WIRE, "03")
    for c in T_["lower"]:
        clip = fc["F01"][0] if c["side"] == "L" else fc["F02"][0]
        regs, mv = fit(c["vis"], unary_union([fc["F01"][0], fc["F02"][0], box(-15.5, -100, 15.5, 900)]))     # wisps may cross the zip (split there)
        it.add(tf_regs(regs, sc, A0, A1), L_CLOUD, "03")
    it.add(tf_regs(T_["front_pole"], sc, A0, A1, dx=dxp), L_POLE, "03")
    return it, dict(size=size, grade=GRADE[size][0], scale=sc, pole_x=PX * kx, wire_ends=[e[:3] for e in ends], wire_geo=ends)

def chest_art():
    """02 chest clouds at M (graded files are scaled about each piece's centre)"""
    T_ = traced(); fc = front_clips("M"); it = Items(); moves = []
    for c in T_["chest"]:
        clip = fc["F01"][0] if c["side"] == "L" else fc["F02"][0]
        regs, mv = fit(c["vis"], clip, max_shift=90.0, tol=0.003); moves.append(mv)
        it.add(regs, L_CLOUD, "02")
    return it

def front_clips(size):
    g, mt = PT.draft(size); out = {}
    for pc, side in (("F01", 1), ("F02", -1)):
        P_ = g[pc].sew_poly()
        sub = lambda names, k: unary_union([edge(g, pc, n).buffer(k) for n in names])
        weltg = Polygon(g[pc].internal[0][1])
        collar = FR.COLLAR_L if side > 0 else FR.COLLAR_R
        base = P_.difference(sub(["armhole", "shoulder"], KEEP["seam"])).difference(sub(["CF / zip"], KEEP["cf"]))
        base = base.difference(sub(["hem"], KEEP["hem"])).difference(weltg.buffer(KEEP["welt"] + 0.25)).difference(collar.buffer(KEEP["collar"]))
        base = base.difference(sub(["neck"], KEEP["neck"]))
        out[pc] = (make_valid(base.difference(sub(["side"], KEEP["side"] + 0.3))).buffer(0), make_valid(base.difference(sub(["side"], KEEP["wrap"]))).buffer(0))
    return out

# ================================================================ 04 sleeve clouds (M, sleeve pattern coords; S01 right: front x > 0)
def sleeve_art(k):
    T_ = traced(); clip = sleeve_clip("M", k); it = Items()
    for s_ in T_["sleeves"]:
        if s_["sleeve"] != k: continue
        regs, mv = fit(s_["vis"], clip)
        it.add(regs, L_CLOUD, "04")
    return it

def sleeve_clip(size, k):
    g, mt = PT.draft(size); pc = "S01" if k == "04R" else "S02"; P_ = g[pc].sew_poly()
    sub = lambda names, kk: unary_union([edge(g, pc, n).buffer(kk) for n in names])
    c = P_.difference(sub(["cap", "underarm front", "underarm back"], KEEP["seam"])).difference(sub(["cuff"], KEEP["cuff"]))
    return make_valid(c).buffer(0)

# ================================================================ knockout + clip
def build(items, clip, wire_clip=None, knock=None):
    """clip every item to its keep-out region, then knock out what later items cover (painter's order).
    Local knockout via an STRtree (only later items that touch this one), not one growing union (that was O(n²))."""
    from shapely.strtree import STRtree
    G = []
    for r in items:
        cl = wire_clip if (wire_clip is not None and r["grp"] == "WR") else clip
        try: g = r["geom"].intersection(cl)
        except Exception: g = make_valid(r["geom"]).buffer(0).intersection(cl)
        if knock is not None and not g.is_empty: g = g.difference(knock)
        G.append(g)
    idx = [i for i, g in enumerate(G) if not g.is_empty]
    tree = STRtree([G[i] for i in idx]); vis = []
    for n, i in enumerate(idx):
        mn = items[i]["grp"].startswith("MN")
        # moon objects sit ON each other (raised cells / stars on a continuous ground, LESSONS A13): only non-moon art
        # (clouds, pole, wires) knocks the moon out; everything else keeps painter's-order knockout
        later = [G[idx[j]] for j in tree.query(G[i]) if idx[j] > i and not (mn and items[idx[j]]["grp"].startswith("MN"))]
        g = G[i]
        if later:
            try: g = g.difference(unary_union(later))
            except Exception: g = make_valid(g).buffer(0).difference(make_valid(unary_union(later)).buffer(0))
        if not g.is_empty and g.area > 0.02: vis.append(dict(items[i], geom=g))
    return valid(absorb_slivers(vis))

def valid(vis):
    out = []
    for v in vis:
        g = v["geom"]
        if not g.is_valid: g = make_valid(g)
        if g.geom_type == "GeometryCollection": g = unary_union([p for p in MM._polys(g)])
        if v["st"] not in ("bean", "run"):
            # open by 0.06 mm: removes pinch points that turn invalid when the hatcher rotates the polygon
            try: g = shapely.set_precision(g.buffer(-0.06, join_style=2).buffer(0.06, join_style=2), 0.005).buffer(0)
            except Exception: g = make_valid(g).buffer(-0.06, join_style=2).buffer(0.06, join_style=2).buffer(0)
        if not g.is_empty and g.area > 0.02: out.append(dict(v, geom=g))
    return out

def absorb_slivers(vis):
    """(from plum + pine back2.py) knockout slivers narrower than the stitch minimum go to the neighbour they touch most."""
    from shapely.strtree import STRtree
    geoms = [v["geom"] for v in vis]; tree = STRtree(geoms); give = {}
    for i, v in enumerate(vis):
        line = v["st"] in ("bean", "run"); h = 0.3 if line else 0.4
        if line or v["grp"] == "WR": continue          # line work keeps its own pieces (a wire sliver must never grow a fill past a keep-out)
        clean = v["geom"].buffer(-h).buffer(h).intersection(v["geom"]); sl = v["geom"].difference(clean)
        if sl.is_empty or sl.area < 0.01: continue
        keep = clean
        for piece in ([sl] if sl.geom_type == "Polygon" else [p for p in getattr(sl, "geoms", []) if p.geom_type == "Polygon"]):
            if piece.area < 0.004: continue
            best, bl = None, 0.0
            for j in tree.query(piece.buffer(0.05)):
                j = int(j)
                if j == i: continue
                if (vis[j]["st"] in ("bean", "run") or vis[j]["grp"] == "WR") and not line: continue
                L = piece.buffer(0.05).intersection(geoms[j]).area * (1.5 if j > i else 1.0)
                if L > bl: best, bl = j, L
            if best is None: keep = keep.union(piece)
            else: give.setdefault(best, []).append(piece)
        vis[i] = dict(v, geom=keep)
    for j, pcs in give.items():
        vis[j] = dict(vis[j], geom=unary_union([vis[j]["geom"]] + pcs))
    return [v for v in vis if not v["geom"].is_empty and v["geom"].area > 0.02]

# ================================================================ match marks
def seam_check(vis, ends, xs):
    """every wire that meets a side seam must be visible up to 3 mm (±0.6) from the seam line on this piece.
    Returns [(side, h above hem, distance of the visible end from the seam or None)]"""
    U = unary_union([r["geom"] for r in vis if r["grp"] == "WR"]); out = []
    for side, h, (x, y) in ends:
        sg = 1 if x > 0 else -1
        win = U.intersection(box(min(sg * (xs - 12), sg * xs), y - 4, max(sg * (xs - 12), sg * xs), y + 4))
        d = None if win.is_empty else round(xs - (win.bounds[2] if sg > 0 else -win.bounds[0]), 2)
        out.append((side, h, d))
    return out

def zip_marks(vis, side):
    """wire / wisp ends at the zip keep-out line (x = ±15): y of each end"""
    out = []
    for r in vis:
        if r["grp"] not in ("WR", "CL-wisp"): continue
        for p in MM._polys(r["geom"]):
            b = p.bounds; xe = b[0] if side > 0 else b[2]
            if abs(abs(xe) - KEEP["cf"]) < 1.0:
                sl = p.intersection(box(xe - 1.0, -1e4, xe + 1.0, 1e4))
                if not sl.is_empty: out.append((r["grp"], round(sl.centroid.y, 1)))
    return sorted(set(out), key=lambda t: t[1])

def art_for_size(size):
    """everything per size: back + 03L + 03R vis, moon-in-box, marks."""
    itb, BOX, info = back_art(size)
    cb, cw = back_clips(size)
    vb = build(itb, cb, cw, knock=BOX)
    mib = [dict(r, geom=r["geom"].intersection(BOX)) for r in build([r for r in itb if r["layer"] in (L_MOON, L_MDET)], cb)]
    mib = [r for r in mib if not r["geom"].is_empty and r["geom"].area > 0.3]
    itf, finfo = front_art(size)
    fc = front_clips(size)
    vL = build(itf, *fc["F01"]); vR = build(itf, *fc["F02"])
    g, mt = PT.draft(size); xs = mt["block"].chest2
    info.update(front=finfo,
                marks=dict(back=seam_check(vb, info["wire_ends"], xs),
                           front_L=seam_check(vL, [e for e in finfo["wire_ends"] if e[0] == "L"], xs),
                           front_R=seam_check(vR, [e for e in finfo["wire_ends"] if e[0] == "R"], xs),
                           zip_L=zip_marks(vL, 1), zip_R=zip_marks(vR, -1),
                           angles=wire_angles(info["wire_geo"], finfo["wire_geo"], xs)))
    return dict(back=vb, moonbox=mib, F03L=vL, F03R=vR, info=info)

def wire_angles(back_geo, front_geo, xs):
    """slope of each wire at the side seam on the back and on the front (degrees below horizontal, wearer's view)"""
    def slope(p0, p1, sag):
        # quadratic sag curve y = lerp + 4 sag t(1-t); derivative at the seam end t = 1
        dx = p1[0] - p0[0]; dy = (p1[1] - p0[1]) - 4 * sag
        return math.degrees(math.atan2(dy, abs(dx)))
    out = []
    for s_, h, b, p0, sag in back_geo:
        f = next((e for e in front_geo if e[0] == s_ and abs(e[1] - h) < 0.6), None)
        if f is None: continue
        out.append((s_, h, round(slope(p0, b, sag), 1), round(slope(f[3], f[2], f[4]), 1)))
    return out

def graded_art():
    """02 + 04 at M (clipped to the M pattern); per-size placement in emb_place."""
    # graded art is clipped 2.5 mm (02) / 1.0 mm (04) INSIDE the M keep-outs: grade A (92 %) on XS and pull comp on the
    # satin edges must still clear 15 mm on every size (Rev C: XS 02R 13.1 / M 04L 14.8 failed with the plain M clip)
    fc = front_clips("M"); it = chest_art()
    out = {"02R": build(it, fc["F02"][0].buffer(-2.5)), "02L": build(it, fc["F01"][0].buffer(-2.5))}
    for k in ("04R", "04L"): out[k] = build(sleeve_art(k), sleeve_clip("M", k).buffer(-1.0))
    return out
