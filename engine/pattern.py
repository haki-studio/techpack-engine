"""Drum Island jacket — first production pattern, drafted from the POM chart (drum.py) for XS–3XL.
Internal coords: mm, y DOWN. Body pieces are drafted in garment coords (back: x from CB, y from CB neck seam;
fronts: x from CF, + = wearer's left; y from CF neck seam) so embroidery placements drop straight onto them.
Values not on the fit chart are PROPOSED (see PROPOSED + the pattern QA page)."""
import math, json
import numpy as np
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
from shapely import affinity
import drum

SIZES = drum.SIZES
# ---------------------------------------------------------------- pattern constants (proposed unless on the chart)
SA_STD, SA_HEM, SA_EDGE = 10.0, 8.0, 6.0        # T7: body 1.0, rib joins 0.8, collar edge 0.6
FWD = 10.0                                      # P: shoulder seam 1 cm forward of the true shoulder (chart)
CAP_EASE = 12.0                                 # sleeve cap ease over armhole (canvas: low ease)
CUFF_RATIO = 1.25                               # shell sleeve opening / cuff rib relaxed length
COLLAR_RISE = 14.0                              # neck-edge rise at the collar front end (roll)
FACING_W, FACING_SH = 60.0, 40.0                # front facing width at CF, length along shoulder
BFACING_D = 65.0                                # back neck facing depth at CB
WELT_L, WELT_W = 130.0, 14.0                    # welt 1.4 × 13 cm (mockup welt; the embroidery is drawn around it)
BAG_W, BAG_D = 180.0, 200.0                     # pocket bag (T10 Q7: 18 cm proposed)
PLEAT = 20.0                                    # back lining CB pleat
CUFF_RIB, HEM_RIB = 75.0, 55.0                  # finished rib heights (PROPOSED)
PROPOSED = {"Shoulder slope (HPS→shoulder point)": "4.5 cm", "Shoulder seam forward": "1.0 cm (chart P)",
            "Sleeve cap ease": f"{CAP_EASE/10:.1f} cm", "Shell sleeve opening": f"{CUFF_RATIO:.2f} × cuff rib",
            "Hem rib / cuff rib finished": "5.5 / 7.5 cm", "Collar neck rise at front": f"{COLLAR_RISE/10:.1f} cm",
            "Front facing": "6 cm at CF, 4 cm on shoulder", "Back neck facing depth": "6.5 cm", "Welt": "1.6 × 14 cm",
            "Pocket bag": "18 × 20 cm", "Back lining CB pleat": "2 cm"}

# ---------------------------------------------------------------- HOODED variant (collar -> 3-panel hood, rib -> self-fabric bands)
VARIANTS = ("default", "hooded")
# Hood dims at size M + grade per size step. ALL PROPOSED. Override per project: draft(size, "hooded", hood={...}) or HOOD.update(...)
HOOD = dict(height=340.0,        # side panel flat: hood neck point at CF -> crown
            width=255.0,         # side panel flat: face edge -> back of the head, widest
            face_opening=760.0,  # CF -> CF along the face edge (side + centre-panel end + side)
            grade_height=6.0, grade_width=4.0, grade_face=10.0,   # per size step from M
            centre_w=100.0,      # centre panel width (constant, straight grain)
            neck_rise=40.0,      # side panel: CB end of the neck seam sits this much above the CF end
            neck_bow=10.0,       # neck edge bows out (convex) - mate of the scooped body neck
            face_lean=25.0, face_bow=6.0,   # face edge: top set back / bowed forward
            cf_set=0.0,          # hood neck starts this far back from the CF sew line (0 = hood fronts meet at the zip)
            facing_w=30.0,       # finished hood facing (shell) at the face opening
            toc=3.0,             # sherpa turn-of-cloth per centre seam (full at the crown, 0 at the neck)
            sa_lining=12.0)      # sherpa seam allowance
BAND = dict(hem=55.0, cuff=60.0)  # hooded: finished self-fabric hem band / cuff heights (folded double), PROPOSED
_GRADE = {"height": "grade_height", "width": "grade_width", "face_opening": "grade_face"}

def hood_dims(size, hood=None):
    """HOOD (+ overrides) graded to `size`"""
    d = dict(HOOD); d.update(hood or {})
    k = SIZES.index(size) - SIZES.index("M")
    for key, gk in _GRADE.items(): d[key] = d[key] + k * d[gk]
    return d

def proposed(variant="default", hood=None):
    """the PROPOSED table for a variant (pages print every entry amber "[proposed — confirm]")"""
    if variant == "default": return PROPOSED
    d = hood_dims("M", hood)
    out = {k: v for k, v in PROPOSED.items() if k not in ("Collar neck rise at front", "Hem rib / cuff rib finished", "Shell sleeve opening")}
    out.update({
        "Hood height (CF neck point to crown, flat)": f"{d['height']/10:.1f} cm (M), ±{d['grade_height']/10:.1f} cm per size",
        "Hood width (face edge to back, flat)": f"{d['width']/10:.1f} cm (M), ±{d['grade_width']/10:.1f} cm per size",
        "Hood face opening (CF to CF along the edge)": f"{d['face_opening']/10:.1f} cm (M), ±{d['grade_face']/10:.1f} cm per size",
        "Hood centre panel width": f"{d['centre_w']/10:.1f} cm",
        "Hood neck rise / neck bow": f"{d['neck_rise']/10:.1f} / {d['neck_bow']/10:.1f} cm",
        "Hood face edge lean / bow": f"{d['face_lean']/10:.1f} / {d['face_bow']/10:.1f} cm",
        "Hood start at CF": f"{d['cf_set']/10:.1f} cm back from the CF sew line (hood fronts meet at the zip)",
        "Hood facing (shell)": f"{d['facing_w']/10:.1f} cm finished",
        "Sherpa lining turn-of-cloth": f"{d['toc']/10:.1f} cm per centre seam at the crown, 0 at the neck",
        "Sherpa seam allowance": f"{d['sa_lining']/10:.1f} cm",
        "Hem band / cuff finished (self-fabric, folded)": f"{BAND['hem']/10:.1f} / {BAND['cuff']/10:.1f} cm",
        "Shell sleeve opening": "= cuff length (woven cuff, no ease); half opening = chart H",
        "Side seam taper at hem": "side seams taper in to 1/2 sweep D at the hem (woven band, no ease)"})
    return out

# ---------------------------------------------------------------- geometry helpers
def alen(pts): return sum(math.hypot(b[0]-a[0], b[1]-a[1]) for a, b in zip(pts, pts[1:]))
def at(pts, s):
    """point + unit tangent at arc length s along polyline"""
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        d = math.hypot(b[0]-a[0], b[1]-a[1])
        if acc + d >= s or b is pts[-1]:
            t = 0 if d == 0 else min(1, max(0, (s - acc) / d))
            return (a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t), ((b[0]-a[0])/(d or 1), (b[1]-a[1])/(d or 1))
        acc += d
def resample(pts, step=2.0):
    L = alen(pts); n = max(2, int(L / step) + 1)
    return [at(pts, L * i / (n - 1))[0] for i in range(n)]
def mirror(pts): return [(-x, y) for x, y in pts]
def rev(pts): return list(pts)[::-1]
def cut_curve_from(pts, s0):
    """part of polyline from arc length s0 to the end"""
    L = alen(pts); out = [at(pts, s0)[0]]; acc = 0.0
    for a, b in zip(pts, pts[1:]):
        acc += math.hypot(b[0]-a[0], b[1]-a[1])
        if acc > s0 + 1e-6: out.append(b)
    return out
def line_x(p, q, other):
    """intersection of infinite line p-q with polyline `other`: first hit, as (point, arc length on other)"""
    (x1, y1), (x2, y2) = p, q; dx, dy = x2-x1, y2-y1; L = math.hypot(dx, dy); dx, dy = dx/L, dy/L
    big = LineString([(x1 - dx*2000, y1 - dy*2000), (x1 + dx*2000, y1 + dy*2000)])
    hit = big.intersection(LineString(other))
    pts = [hit] if hit.geom_type == "Point" else list(getattr(hit, "geoms", []))
    best = min(pts, key=lambda g: LineString(other).project(g))
    return (best.x, best.y), LineString(other).project(best)

class Edge:
    def __init__(self, name, pts, sa, notches=(), kind="seam"):
        self.name, self.pts, self.sa, self.kind = name, [tuple(p) for p in pts], sa, kind
        self.notches = list(notches)     # arc lengths from edge start (on the sew line)
    @property
    def length(self): return alen(self.pts)

class Piece:
    def __init__(self, code, name, qty, material, edges, grain, category="SHELL", drills=(), internal=(), fuse=False, note=""):
        self.code, self.name, self.qty, self.material, self.category = code, name, qty, material, category
        self.edges = edges; self.grain = grain; self.drills = list(drills); self.internal = list(internal)
        self.fuse = fuse; self.note = note
    def sew(self):
        pts = []
        for e in self.edges: pts += e.pts if not pts else e.pts[1:]
        return pts
    def sew_poly(self): return Polygon(self.sew()).buffer(0)
    def cut(self):
        """cut line: each edge offset by its own SA, corners joined at the intersection of the offsets."""
        sp = self.sew_poly(); offs = []
        for e in self.edges:
            ls = LineString(e.pts)
            if e.sa <= 0: offs.append(list(e.pts)); continue
            cands = []
            for d in (e.sa, -e.sa):
                o = ls.offset_curve(d, quad_segs=8, join_style="round")
                if o.is_empty: continue
                if o.geom_type != "LineString": o = max(o.geoms, key=lambda g: g.length)
                c = list(o.coords)
                if math.hypot(c[0][0]-e.pts[0][0], c[0][1]-e.pts[0][1]) > math.hypot(c[-1][0]-e.pts[0][0], c[-1][1]-e.pts[0][1]): c = c[::-1]
                cands.append(c)
            def outside(c):
                l_ = LineString(c); return sum(0 if sp.contains(l_.interpolate(f, normalized=True)) else 1 for f in (0.2, 0.35, 0.5, 0.65, 0.8))
            out = max(cands, key=outside)
            offs.append(out)
        n = len(offs); res = [None]*n
        for i in range(n):
            a, b = offs[i], offs[(i + 1) % n]
            la, lb = LineString(a), LineString(b)
            hit = la.intersection(lb)
            if not hit.is_empty:
                ps = [hit] if hit.geom_type == "Point" else [g for g in getattr(hit, "geoms", []) if g.geom_type == "Point"]
                if ps:
                    p = min(ps, key=lambda g: g.distance(Point(a[-1])))
                    sa_, sb_ = la.project(p), lb.project(p)
                    offs[i] = [q for q in a if la.project(Point(q)) <= sa_] + [(p.x, p.y)]
                    offs[(i + 1) % n] = [(p.x, p.y)] + [q for q in b if lb.project(Point(q)) >= sb_]
                    continue
            # no crossing: extend the end segments to meet
            (x1, y1), (x2, y2) = a[-2], a[-1]; (x3, y3), (x4, y4) = b[0], b[1]
            d = (x2-x1)*(y4-y3) - (y2-y1)*(x4-x3)
            if abs(d) > 1e-6:
                t = ((x3-x1)*(y4-y3) - (y3-y1)*(x4-x3)) / d
                px, py = x1 + (x2-x1)*t, y1 + (y2-y1)*t
                if math.hypot(px - x2, py - y2) < 40:
                    offs[i] = a + [(px, py)]; offs[(i + 1) % n] = [(px, py)] + b; continue
        pts = []
        for o in offs: pts += o
        P = Polygon(pts).buffer(0)
        if P.geom_type != "Polygon": P = max(P.geoms, key=lambda g: g.area)
        return P
    def notch_marks(self, depth=5.0):
        """slit notches: (point on cut line, point inward) for every notch, perpendicular to the sew line."""
        cut = self.cut(); sp = self.sew_poly(); out = []
        for e in self.edges:
            for s in e.notches:
                p, tg = at(e.pts, s); n = (-tg[1], tg[0])
                if sp.contains(Point(p[0] + n[0]*2, p[1] + n[1]*2)): n = (-n[0], -n[1])     # outward
                far = LineString([p, (p[0] + n[0]*(e.sa + 30), p[1] + n[1]*(e.sa + 30))]).intersection(cut.exterior)
                q = far if far.geom_type == "Point" else (min(far.geoms, key=lambda g: g.distance(Point(p))) if not far.is_empty else Point(p[0] + n[0]*e.sa, p[1] + n[1]*e.sa))
                out.append(((q.x, q.y), (q.x - n[0]*depth, q.y - n[1]*depth)))
        return out

# ---------------------------------------------------------------- drafting
def collar_edges(Ln, M, N, extra=0.0):
    """full collar, CB at x=0. Neck edge rises toward the front ends (roll). extra = turn-of-cloth for the top collar."""
    lo, hi = Ln * 0.8, Ln
    for _ in range(50):
        xe = (lo + hi) / 2
        xs = np.linspace(0, xe, 60); pts = [(x, -COLLAR_RISE * (x / xe) ** 2) for x in xs]
        if alen(pts) > Ln: hi = xe
        else: lo = xe
    neckR = pts; E = neckR[-1]
    ang = math.radians(28)
    T = (E[0] + (N + extra) * math.sin(ang), E[1] - (N + extra) * math.cos(ang))
    Mo = M + extra
    outerR = [(x, -Mo + (T[1] + Mo) * (x / T[0]) ** 2.2) for x in np.linspace(0, T[0], 40)]   # CB outer -> tip
    neck_full = mirror(rev(neckR)) + neckR[1:]                     # front L end -> CB -> front R end
    return neck_full, [E, T], rev(outerR) + mirror(outerR)[1:], [mirror([T])[0], mirror([E])[0]], neckR

def _welt_ref():
    """the welt reference (front.WELT_L): the project's front.py if it defines one, else Drum Island's (the block's own
    welt) - so a new project on this block (e.g. the hooded ones) can draft before it has any art code."""
    try:
        import front as FR
        if hasattr(FR, "WELT_L"): return FR
    except ImportError:
        pass
    from types import SimpleNamespace          # same construction as projects/drum-island-plum-pine/front.py (mockup px -> mm)
    P = lambda px, py: ((px - 448) * 0.80, (py - 190) * 0.736)
    return SimpleNamespace(WELT_L=LineString([P(600, 630), P(720, 750)]).buffer(16 * 0.77 / 2, cap_style="flat", join_style="mitre"))

def draft(size, variant="default", hood=None):
    """pieces {code: Piece}, meta. variant "hooded": collar -> 3-panel hood with sherpa lining + facing,
    rib hem/cuffs -> self-fabric bands (woven: band = seam it joins, 1:1). hood = overrides for HOOD."""
    if variant not in VARIANTS: raise ValueError(f"variant {variant!r} not in {VARIANTS}")
    hooded = variant == "hooded"
    b = drum.Block(size); g = {}
    n2, sh2, ch2, drop = b.neck2, b.sh2, b.chest2, b.drop
    hx = ch2                                     # half hem width at the side seam (= chest: straight side seam)
    cuff_h, cuff_ratio = CUFF_RIB, CUFF_RATIO
    if hooded:
        hx = drum.m("D", size) / 2               # woven band can't pull the hem in: side seam tapers to 1/2 sweep D
        cuff_h, cuff_ratio = BAND["cuff"], 1.0   # woven cuff = shell opening; half opening = chart H
    # ------------------------------------------------ BACK (one piece, cut 1 — embroidered, not cut on fold)
    hps_b = (n2, -b.bnd - FWD); sp_b = (sh2, b.b_sp[1] - FWD)
    neck_bR = drum.curve((0, 0), hps_b, -6, 30)
    arm_bR = [sp_b] + drum.curve(b.b_sp, b.b_ua, -18, 50)          # 10 mm forward extension, then the block armhole
    hem_b = b.b_hem if not hooded else b.b_hem_edge - BAND["hem"]
    ua_b = arm_bR[-1]
    back_neck = mirror(rev(neck_bR)) + neck_bR[1:]
    arm_len_b = alen(arm_bR)
    back = Piece("B01", "BACK", "1", "Shell — 12 oz duck", [
        Edge("neck", rev(back_neck), SA_STD, [alen(back_neck)/2]),                       # from HPS R via CB to HPS L
        Edge("shoulder L", [mirror([hps_b])[0], mirror([sp_b])[0]], SA_STD),
        Edge("armhole L", mirror(arm_bR), SA_STD, [arm_len_b - 100, arm_len_b - 106]),
        Edge("side L", [mirror([ua_b])[0], (-hx, hem_b)], SA_STD),
        Edge("hem", [(-hx, hem_b), (hx, hem_b)], SA_HEM, [hx]),
        Edge("side R", [(hx, hem_b), ua_b], SA_STD),
        Edge("armhole R", rev(arm_bR), SA_STD, [100, 106]),
        Edge("shoulder R", [sp_b, hps_b], SA_STD)],
        grain=((0, 60), (0, hem_b - 60)), note="CB marked by notches; embroidery 01 sewn on the cut piece")
    # ------------------------------------------------ FRONT (drafted for the wearer's LEFT, x > 0; right = mirror)
    hps_f = (n2, -b.fnd + FWD)
    neck_f = drum.curve((0, 0), hps_f, -28, 30)          # scooped (concave) front neck
    arm_f_old = drum.curve(b.f_sp, b.f_ua, -22, 60)
    sp_f, s0 = line_x(hps_f, (hps_f[0] + (sh2 - n2), hps_f[1] + drop), arm_f_old)
    arm_f = [sp_f] + cut_curve_from(arm_f_old, s0)[1:]
    ua_f = arm_f[-1]; hem_f = b.f_hem if not hooded else b.f_hem_edge - BAND["hem"]; arm_len_f = alen(arm_f)
    def front(side):
        X = (lambda pts: list(pts)) if side > 0 else mirror
        return [Edge("CF / zip", X([(0, hem_f), (0, 0)]), SA_STD),
                Edge("neck", X(neck_f), SA_STD),
                Edge("shoulder", X([hps_f, sp_f]), SA_STD),
                Edge("armhole", X(arm_f), SA_STD, [arm_len_f - 80]),
                Edge("side", X([ua_f, (hx, hem_f)]), SA_STD),
                Edge("hem", X([(hx, hem_f), (0, hem_f)]), SA_HEM)]
    # welt pocket per size: keeps its distance above the hem seam, x graded with the chest
    wl_m = drum.Block("M"); kx = ch2 / wl_m.chest2
    FR = _welt_ref()
    wc = FR.WELT_L.centroid; c = np.array(FR.WELT_L.exterior.coords)
    u = c[1] - c[2]; u = u / np.linalg.norm(u)
    if u[1] < 0: u = -u
    wcx, wcy = wc.x * kx, hem_f - (wl_m.f_hem - wc.y)
    def welt_box(side):
        uu = np.array([u[0]*side, u[1]]); vv = np.array([-uu[1], uu[0]]); cc = np.array([wcx*side, wcy])
        corners = [cc + uu*sx*WELT_L/2 + vv*sy*WELT_W/2 for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        drills = [tuple(cc + uu*sx*(WELT_L/2 - 3) + vv*sy*(WELT_W/2 - 3)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        return [tuple(p) for p in corners], drills
    for side, code, nm in ((1, "F01", "FRONT LEFT"), (-1, "F02", "FRONT RIGHT")):
        wb, dr = welt_box(side)
        g[code] = Piece(code, nm + " (wearer's)", "1", "Shell — 12 oz duck", front(side), grain=((side*150, 60), (side*150, hem_f - 60)),
                        drills=dr, internal=[("WELT POCKET", wb + [wb[0]])], note="welt pocket marked; embroidery 02/03/04 placement")
    g["B01"] = back
    # ------------------------------------------------ SLEEVE (right sleeve: back of cap on the left, x < 0)
    AH = arm_len_b + arm_len_f; target = AH + CAP_EASE
    Lc = m_G = drum.m("G", size) - cuff_h                        # cap top -> cuff seam along the sleeve centre
    Hh = drum.m("H", size); Ww = Hh * cuff_ratio                   # half-width of the sleeve at the cuff seam (= 1/2 shell opening)
    F = drum.m("F", size)                                           # half bicep, 25 mm below underarm
    def cap(W, h, pb=0.92, pf=1.08, n=80):
        us = np.linspace(0, 1, n)
        back_ = [(-W*u, -h*((1 + math.cos(math.pi*u))/2) ** pb) for u in us]     # top -> back underarm
        front_ = [(W*u, -h*((1 + math.cos(math.pi*u))/2) ** pf) for u in us]     # top -> front underarm
        return back_, front_
    W = F
    for _ in range(30):
        lo, hi = 20.0, 260.0
        for _ in range(60):
            h = (lo + hi) / 2; bk, fr = cap(W, h)
            if alen(bk) + alen(fr) > target: hi = h
            else: lo = h
        Lu = Lc - h
        W_new = (F - Ww * 25 / Lu) / (1 - 25 / Lu)
        if abs(W_new - W) < 0.01: W = W_new; break
        W = W_new
    bk, fr = cap(W, h); Lu = Lc - h
    capb_len, capf_len = alen(bk), alen(fr)
    capT = capb_len + capf_len; k = capT / AH                    # ease spread evenly along the cap
    s_top = arm_len_b * k                                           # shoulder-seam notch (from the back underarm)
    sl_edges = [Edge("cap", rev(bk) + fr[1:], SA_STD, [k*100, k*106, s_top, capT - k*80]),   # back underarm -> top -> front underarm
                Edge("underarm front", [(W, 0), (Ww, Lu)], SA_STD),
                Edge("cuff", [(Ww, Lu), (-Ww, Lu)], SA_HEM),
                Edge("underarm back", [(-Ww, Lu), (-W, 0)], SA_STD)]
    g["S01"] = Piece("S01", "SLEEVE RIGHT", "1", "Shell — 12 oz duck", sl_edges, grain=((0, -h + 40), (0, Lu - 40)), note="01 wrap embroidery on the back cap")
    g["S02"] = Piece("S02", "SLEEVE LEFT", "1", "Shell — 12 oz duck",
                     [Edge(e.name, mirror(e.pts), e.sa, e.notches) for e in sl_edges], grain=((0, -h + 40), (0, Lu - 40)))
    # ------------------------------------------------ COLLAR (top + under), neck edge = back neck + front neck
    Ln = alen(neck_bR) + alen(neck_f)
    Mc, Nc = drum.m("M", size), drum.m("N", size)
    for code, nm, extra, qty in (("C01", "TOP COLLAR", 2.0, "1"), ("C02", "UNDER COLLAR", 0.0, "1")) if not hooded else ():
        neck_full, frontR, outer, frontL, neckR = collar_edges(Ln, Mc, Nc, extra)
        nb = alen(neck_bR)
        nk = alen(neck_full) / 2
        g[code] = Piece(code, nm, qty, "Corduroy — 14 wale, dark brown",
                        [Edge("neck", neck_full, SA_STD, [nk - nb, nk, nk + nb]), Edge("front R", frontR, SA_EDGE),
                         Edge("outer", outer, SA_EDGE, [alen(outer)/2]), Edge("front L", frontL, SA_EDGE)],
                        grain=((0, -Mc + 15), (0, -12)), fuse=(code == "C01"), note="fuse top collar")
    # ------------------------------------------------ FRONT FACING (shell), BACK NECK FACING
    q0, _ = at([hps_f, sp_f], FACING_SH)
    inner = [q0] + drum.curve(q0, (FACING_W, 170), -12, 20)[1:] + [(FACING_W, hem_f)]
    fneck_end = neck_f
    face_edges = [Edge("CF / zip", [(0, hem_f), (0, 0)], SA_STD), Edge("neck", fneck_end, SA_STD),
                  Edge("shoulder", [hps_f, q0], SA_STD), Edge("lining join", inner, SA_STD), Edge("hem", [(FACING_W, hem_f), (0, hem_f)], SA_HEM)]
    g["K01"] = Piece("K01", "FRONT FACING", "1 pair", "Shell — 12 oz duck", face_edges, grain=((30, 60), (30, hem_f - 60)), fuse=True, note="zip set between shell + facing")
    qb, _ = at([hps_b, sp_b], FACING_SH)
    xs = np.linspace(qb[0], -qb[0], 50)
    binner = [(x, BFACING_D + (qb[1] - BFACING_D) * (abs(x) / qb[0]) ** 2) for x in xs]
    g["K02"] = Piece("K02", "BACK NECK FACING", "1", "Shell — 12 oz duck",
                     [Edge("neck", rev(back_neck), SA_STD, [alen(back_neck)/2]), Edge("shoulder L", [mirror([hps_b])[0], mirror([qb])[0]], SA_STD),
                      Edge("lining join", rev(binner), SA_STD), Edge("shoulder R", [qb, hps_b], SA_STD)],
                     grain=((0, 8), (0, BFACING_D - 8)), fuse=True, note="main + size label 1 cm below collar seam")
    # ------------------------------------------------ LINING: front, back (CB pleat), sleeve
    lin_f = [Edge("facing join", rev(inner), SA_STD), Edge("shoulder", [q0, sp_f], SA_STD), Edge("armhole", arm_f, SA_STD, [arm_len_f - 80]),
             Edge("side", [ua_f, (hx, hem_f)], SA_STD), Edge("hem", [(hx, hem_f), (FACING_W, hem_f)], SA_STD)]
    g["L01"] = Piece("L01", "FRONT LINING", "1 pair", "Lining — cotton flannel", lin_f, grain=((170, 120), (170, hem_f - 60)), category="LINING")
    bR = [(x + PLEAT/2, y) for x, y in binner if x >= 0]; bL = [(x - PLEAT/2, y) for x, y in binner if x <= 0]
    shift = lambda pts, d: [(x + d, y) for x, y in pts]
    lin_b = [Edge("facing join", rev(bL) + rev(bR), SA_STD), Edge("shoulder R", shift([qb, sp_b], PLEAT/2), SA_STD),
             Edge("armhole R", shift(arm_bR, PLEAT/2), SA_STD, [arm_len_b - 100, arm_len_b - 106]),
             Edge("side R", shift([ua_b, (hx, hem_b)], PLEAT/2), SA_STD),
             Edge("hem", [(hx + PLEAT/2, hem_b), (-hx - PLEAT/2, hem_b)], SA_STD, [hx + PLEAT/2]),
             Edge("side L", shift([(-hx, hem_b), mirror([ua_b])[0]], -PLEAT/2), SA_STD),
             Edge("armhole L", shift(rev(mirror(arm_bR)), -PLEAT/2), SA_STD, [100, 106]),
             Edge("shoulder L", shift([mirror([sp_b])[0], mirror([qb])[0]], -PLEAT/2), SA_STD)]
    # reorder so edges chain: start after 'facing join' which runs L->R
    lin_b = [lin_b[0], lin_b[1], lin_b[2], lin_b[3], lin_b[4], lin_b[5], lin_b[6], lin_b[7]]
    g["L02"] = Piece("L02", "BACK LINING", "1", "Lining — cotton flannel", lin_b, grain=((0, 120), (0, hem_b - 60)), category="LINING",
                     internal=[("CB PLEAT fold", [(-PLEAT/2, BFACING_D), (-PLEAT/2, hem_b)]), ("CB PLEAT fold", [(PLEAT/2, BFACING_D), (PLEAT/2, hem_b)]),
                               ("CB", [(0, BFACING_D), (0, hem_b)])],
                     note="2 cm CB pleat: stitch 5 cm down from the neck, release below")
    g["L03"] = Piece("L03", "SLEEVE LINING", "1 pair", "Lining — polyester taffeta 210T",
                     [Edge(e.name, e.pts, SA_STD, e.notches) for e in sl_edges], grain=((0, -h + 40), (0, Lu - 40)), category="LINING")
    # ------------------------------------------------ small parts
    def rect(code, name, qty, mat, w, h_, sas, grain_v=True, cat="SHELL", fold=None, fuse=False, note=""):
        e = [Edge("top", [(0, 0), (w, 0)], sas[0]), Edge("right", [(w, 0), (w, h_)], sas[1]),
             Edge("bottom", [(w, h_), (0, h_)], sas[2]), Edge("left", [(0, h_), (0, 0)], sas[3])]
        gr = ((w/2, 10), (w/2, h_ - 10)) if grain_v else ((10, h_/2), (w - 10, h_/2))
        internal = [("FOLD", fold)] if fold else []
        return Piece(code, name, qty, mat, e, gr, category=cat, internal=internal, fuse=fuse, note=note)
    D = drum.m("D", size)
    if hooded:      # self-fabric bands, woven: each band = the seam it joins (no negative ease), folded double
        hem_len = 2 * alen([(hx, hem_f), (0, hem_f)]) + 2 * hx
        g["R01"] = rect("R01", "HEM BAND", "1", "Shell — 12 oz duck", hem_len, 2*BAND["hem"], (SA_HEM, SA_STD, SA_HEM, SA_STD), grain_v=False, cat="BAND",
                        fold=[(0, BAND["hem"]), (hem_len, BAND["hem"])], note="self-fabric, folded double; = body hem 1:1 (woven); ends into the zip")
        g["R02"] = rect("R02", "CUFF", "2", "Shell — 12 oz duck", Ww*2, 2*BAND["cuff"], (SA_HEM, SA_HEM, SA_HEM, SA_HEM), grain_v=False, cat="BAND",
                        fold=[(0, BAND["cuff"]), (Ww*2, BAND["cuff"])], note="self-fabric, folded double; = sleeve opening 1:1 (woven); closed into a loop")
    else:
      g["R01"] = rect("R01", "HEM RIB", "1", "Rib knit 1×1 — tan", 2*D, 2*HEM_RIB, (SA_HEM, SA_STD, SA_HEM, SA_STD), grain_v=True, cat="RIB",
                    fold=[(0, HEM_RIB), (2*D, HEM_RIB)], note="folded double; wales run across the height; ends into the zip")
      g["R02"] = rect("R02", "CUFF RIB", "2", "Rib knit 1×1 — dark brown", Hh*2, 2*CUFF_RIB, (SA_HEM, SA_HEM, SA_HEM, SA_HEM), cat="RIB",
                    fold=[(0, CUFF_RIB), (Hh*2, CUFF_RIB)], note="folded double; closed into a loop")
    g["P01"] = rect("P01", "WELT", "2", "Shell — 12 oz duck", WELT_L, 2*WELT_W, (SA_STD,)*4, grain_v=False, fold=[(0, WELT_W), (WELT_L, WELT_W)], fuse=True)
    bag = [(0, 0), (BAG_W, 0)] + [(BAG_W - 40 + 40*math.cos(a), BAG_D - 40 + 40*math.sin(a)) for a in np.linspace(0, math.pi/2, 10)] + \
          [(40 + 40*math.cos(a), BAG_D - 40 + 40*math.sin(a)) for a in np.linspace(math.pi/2, math.pi, 10)]
    g["P02"] = Piece("P02", "POCKET BAG", "4 (2 pairs)", "Pocket — 8 oz cotton twill",
                     [Edge("mouth", bag[:2], SA_STD), Edge("side R", [bag[1], bag[2]], 5.0), Edge("bottom", bag[2:-1], 5.0),
                      Edge("side L", [bag[-1], bag[0]], 5.0)], grain=((BAG_W/2, 20), (BAG_W/2, BAG_D - 20)), category="POCKETING")
    g["P03"] = rect("P03", "ZIP GARAGE", "2", "Shell — 12 oz duck", 50, 60, (SA_STD,)*4, fold=[(0, 30), (50, 30)], note="proposed — confirm (T10 Q6)")
    g["P04"] = rect("P04", "HANGER LOOP", "1", "Shell — 12 oz duck", 25, 140, (0, 0, 0, 0), note="folded in 4, edge-stitched")
    for code in ("C01", "K01", "K02", "P01") if not hooded else ("K01", "K02", "P01"):       # fusing = cut line inset 3 mm
        pc = g[code]
        g["I" + code] = Piece("I" + code, "FUSING — " + pc.name, pc.qty, "Woven fusible 60 g/m²", pc.edges, pc.grain, category="FUSING")
        g["I" + code].inset = 3.0
    meta = dict(AH=AH, cap=capT, cap_top=s_top, cap_b=capb_len, cap_f=capf_len, cap_h=h, W=W, Ww=Ww, Lu=Lu, Ln=Ln, arm_b=arm_len_b, arm_f=arm_len_f,
                hps_b=hps_b, sp_b=sp_b, ua_b=ua_b, hps_f=hps_f, sp_f=sp_f, ua_f=ua_f, hem_b=hem_b, hem_f=hem_f,
                welt_c=(wcx, wcy), welt_u=tuple(u), neck_b=alen(neck_bR), neck_f=alen(neck_f), block=b)
    if hooded:
        meta.update(variant=variant, hem_band=BAND["hem"], cuff_band=cuff_h, hx=hx, **draft_hood(g, size, alen(neck_bR), alen(neck_f), hood))
    return g, meta

def draft_hood(g, size, neck_b, neck_f, hood=None):
    """adds the hood pieces H01-H05 to g; returns hood meta. neck_b / neck_f = body back-neck half / front neck (sew line)."""
    import hood as HD
    d = hood_dims(size, hood); cw, sal = d["centre_w"], d["sa_lining"]
    neck_len = neck_f + neck_b - cw / 2 - d["cf_set"]          # side panel neck seam: CF (less cf_set) -> centre panel
    hps = neck_f - d["cf_set"]                                  # shoulder-seam notch on the hood neck (arc from the CF end)
    if neck_len <= hps + 10: raise ValueError("hood centre panel wider than the back neck")
    neck, back, face = HD.side_panel(neck_len, d, drum.curve, alen)
    Lb, Lf = alen(back), alen(face)
    i_cr = min(range(len(back)), key=lambda i: back[i][1]); crown_s = alen(back[:i_cr + 1])   # NB -> crown
    side = [Edge("neck", neck, SA_STD, [hps]), Edge("centre seam", back, SA_STD, [crown_s, Lb - 60]), Edge("face", face, SA_EDGE, [Lf / 2])]
    gx = neck[-1][0] * 0.5
    gr = ((gx, -40), (gx, -d["height"] + 60))
    g["H01"] = Piece("H01", "HOOD SIDE", "1 pair", "Shell — 12 oz duck", side, grain=gr, note="mirror for the pair; neck notch = shoulder seam")
    def centre(code, name, L, mat, sa, cat, crown):
        e = [Edge("face end", [(-cw/2, 0), (cw/2, 0)], sa if cat == "LINING" else SA_EDGE, [cw/2]),
             Edge("side R", [(cw/2, 0), (cw/2, L)], sa, [L - crown, 60] if crown else []),
             Edge("neck end", [(cw/2, L), (-cw/2, L)], sa, [cw/2]),
             Edge("side L", [(-cw/2, L), (-cw/2, 0)], sa, [crown, L - 60] if crown else [])]
        return Piece(code, name, "1", mat, e, grain=((0, 30), (0, L - 30)), category=cat, note="notches: CB neck, top centre, crown")
    g["H02"] = centre("H02", "HOOD CENTRE PANEL", Lb, "Shell — 12 oz duck", SA_STD, "SHELL", crown_s)
    # sherpa lining = same panels less the facing band at the face, with turn-of-cloth on the centre seam;
    # facing (shell) = that band, traced off the hood so both its edges match by construction
    ln, lb, lf, (fn, fj, fs, ff) = HD.lining_panel(neck, back, face, d)
    LbL, LfL, Ls = alen(lb), alen(lf), alen(fs); cut_front = alen(fn)
    g["H03"] = Piece("H03", "HOOD FACING SIDE", "1 pair", "Shell — 12 oz duck",
                     [Edge("neck", fn, SA_STD), Edge("lining join", fj, sal), Edge("centre seam", fs, SA_STD), Edge("face", ff, SA_EDGE, [Lf / 2])],
                     grain=((ff[len(ff)//2][0] + d["facing_w"] / 2, ff[len(ff)//2][1] - 60), (ff[len(ff)//2][0] + d["facing_w"] / 2, ff[len(ff)//2][1] + 60)),
                     note="mirror for the pair; turned to the inside at the face opening")
    g["H04"] = Piece("H04", "HOOD FACING CENTRE", "1", "Shell — 12 oz duck",
                     [Edge("face end", [(-cw/2, 0), (cw/2, 0)], SA_EDGE, [cw/2]), Edge("side R", [(cw/2, 0), (cw/2, Ls)], SA_STD),
                      Edge("lining join", [(cw/2, Ls), (-cw/2, Ls)], sal, [cw/2]), Edge("side L", [(-cw/2, Ls), (-cw/2, 0)], SA_STD)],
                     grain=((-cw/2 + 15, Ls/2), (cw/2 - 15, Ls/2)), note="joins the two facing sides; notch = top centre")
    g["H05"] = Piece("H05", "HOOD SIDE LINING", "1 pair", "Sherpa — cream (pile 4–6 mm)",
                     [Edge("neck", ln, sal, [hps - cut_front] if hps > cut_front + 5 else []),
                      Edge("centre seam", lb, sal), Edge("facing join", lf, sal)], grain=gr, category="LINING", note="mirror for the pair; pile runs down (crown -> neck)")
    g["H06"] = centre("H06", "HOOD CENTRE LINING", LbL, "Sherpa — cream (pile 4–6 mm)", sal, "LINING", None)
    return dict(hood=d, hood_neck=2 * neck_len + cw, hood_face=2 * Lf + cw, hood_side_neck=neck_len, hood_back=Lb, hood_face_side=Lf, hood_crown_s=crown_s,
                hood_lining_neck=2 * alen(ln) + cw, hood_lining_face=2 * LfL + cw, hood_lining_back=LbL, hood_facing_neck=2 * cut_front,
                hood_facing_seam=Ls, hood_pts=dict(neck=neck, back=back, face=face))

def cut_poly(pc):
    P = pc.cut()
    if getattr(pc, "inset", 0): P = pc.cut().buffer(-pc.inset - 0.0, join_style="mitre")
    return P

ORDER = ["B01", "F01", "F02", "S01", "S02", "C01", "C02", "K01", "K02", "P01", "P02", "P03", "P04", "R01", "R02",
         "L01", "L02", "L03", "IC01", "IK01", "IK02", "IP01"]
ORDER_HOODED = ["B01", "F01", "F02", "S01", "S02", "H01", "H02", "H03", "H04", "K01", "K02", "P01", "P02", "P03", "P04", "R01", "R02",
                "L01", "L02", "L03", "H05", "H06", "IK01", "IK02", "IP01"]
def order(variant="default"): return ORDER_HOODED if variant == "hooded" else ORDER
PROPOSED_HOODED = proposed("hooded")       # with the default HOOD; after overriding, call proposed("hooded", hood)

if __name__ == "__main__":
    g, m = draft("M")
    for k in ORDER:
        pc = g[k]; c = cut_poly(pc); b_ = c.bounds
        print(k, pc.name, pc.qty, f"{(b_[2]-b_[0]):.0f}×{(b_[3]-b_[1]):.0f}", "valid", c.is_valid, "edges", [f"{e.name}:{e.length:.0f}" for e in pc.edges][:6])
    print({k: (round(v, 1) if isinstance(v, float) else v) for k, v in m.items() if k != "block"})
