"""Pixel Sky fleece — block (fit CONFIRMED by the founder 21 Oct 2026) derived from the APPROVED Drum Island jacket (LESSONS C9: explicit delta list).

Body + sleeve = pattern.draft on the Drum Island chart with PILE EASE added (sherpa ~8-10 mm pile each side):
    B chest +2.0 (half = +4 cm round)   C shoulder +1.0   D sweep = chest (bound hem, no rib)   E armhole +1.0
    F bicep +1.0 (half)                 G sleeve +2.0     J neck opening +1.0 (stand collar over pile)
Removed: corduroy collar, rib hem + cuffs, welt pockets, facings, flannel / taffeta lining (UNLINED: sherpa reverse
inside, seams taped). Added: 9 cm stand collar (outer sky-blue taslan matched to the sky sherpa, inner cream sherpa), navy bindings (hem, cuffs with
elastic, collar seam piping), CF zip facing strip, two vertical zip pockets with bags.
Pile ease + bound hem CONFIRMED 21 Oct; trims / collar / binding details stay PROPOSED (amber in documents). The drum chart is swapped only inside `chart_ctx()` (engine untouched).
Coords as pattern.py (mm, y down; fronts x from CF, + = wearer's left)."""
import math, contextlib, copy
import numpy as np
from shapely.geometry import Polygon, LineString, Point
import drum, pattern as PT
from pattern import Edge, Piece, alen, at, mirror, rev

BLOCK = "pixel-sky-fleece"; NAME = "Pixel Sky sherpa fleece jacket"
SIZES = drum.SIZES
EASE_CM = {"B": 2.0, "C": 1.0, "E": 1.0, "F": 1.0, "G": 2.0, "J": 1.0}      # pile ease, CONFIRMED 21 Oct
COLLAR_H = 90.0            # stand collar finished height (brief: about 9 cm)
BIND_W = 12.0              # finished binding width (hem, cuffs) — visible navy band
BIND_CUT = 50.0            # binding cut width (double fold over ~10 mm sherpa)
CUFF_EL_W = 10.0           # cuff elastic inside the binding channel
PIPE_W = 8.0               # navy piping visible in the collar seam
ZIPF_W = 35.0              # CF zip facing strip (taslan), finished
PKT_L, PKT_ANGLE = 165.0, 7.4     # vertical pocket zip: opening length, lean from vertical (top toward the side seam)
PKT_C = (198.0, 432.0)     # pocket opening centre, size M, wearer's-left front coords (mm) — read off the mockup (mockmap)
PBAG_W, PBAG_D = 170.0, 215.0
SHERPA = "Sherpa — jacquard, blue / cream (+ black, opt. A)"
PROPOSED = {"Pile ease": "+4 cm chest round, +2 cm sleeve length, +1 cm shoulder / armhole / bicep, +1 cm neck",
            "Stand collar": "9 cm, outer sky-blue taslan matched to the sky sherpa (lab dip), inner cream sherpa, navy piping in the neck seam",
            "Hem / cuffs": "navy binding 1.2 cm finished; cuffs gathered on 1 cm elastic in the binding",
            "CF zip": "black #5 coil, separating, blue pull; 3.5 cm taslan facing strip inside",
            "Pockets": "2 vertical zip pockets 16.5 cm, navy tape, blue pulls; tricot bags",
            "Seams": "overlocked 4-thread + taped (navy taslan tape 1.5 cm) — unlined",
            "Length": "Drum Island chart A (cropped at the hip)"}

def chart_vals():
    """fleece chart {code: (name, how, values cm, tol, source)}"""
    out = {}
    for k, (nm, how, vals, tol) in drum.POM_CM.items():
        if k in ("M", "N"): continue                             # jacket collar
        e = EASE_CM.get(k, 0.0)
        out[k] = (nm, how, [round(v + e, 2) for v in vals], tol, "jacket + pile ease (confirmed 21 Oct)" if e else "jacket (approved)")
    nm, how, vals, tol = drum.POM_CM["D"]          # straight boxy body, bound (not ribbed) hem: sweep = chest
    out["D"] = (nm, "1/2, along the bound hem edge, flat", [round(v + EASE_CM["B"], 2) for v in drum.POM_CM["B"][2]], tol, "= chest, bound hem (confirmed 21 Oct)")
    out["M"] = ("Collar height at CB", "neck seam to collar edge, stand", [COLLAR_H / 10] * 7, 0.3, "PROPOSED")
    out["Q"] = ("Binding width", "hem + cuff, finished", [BIND_W / 10] * 7, 0.1, "PROPOSED")
    out["R"] = ("Pocket zip opening", "vertical zip pocket, teeth", [PKT_L / 10] * 7, 0.3, "PROPOSED")
    return out

@contextlib.contextmanager
def chart_ctx():
    """swap the Drum chart for the fleece chart (pile ease) + zero rib heights, restore afterwards"""
    pom, prop = drum.POM_CM, dict(drum.PROPOSED)
    new = copy.deepcopy(pom)
    for k, e in EASE_CM.items():
        nm, how, vals, tol = new[k]; new[k] = (nm, how, [v + e for v in vals], tol)
    drum.POM_CM = new; drum.PROPOSED["hem_rib"] = 0.0
    try: yield
    finally: drum.POM_CM = pom; drum.PROPOSED.clear(); drum.PROPOSED.update(prop)

def m(code, size): return chart_vals()[code][2][SIZES.index(size)] * 10.0

def _rect(code, name, qty, mat, w, h, sas, cat="SHELL", fold=None, note="", grain_v=True):
    e = [Edge("top", [(0, 0), (w, 0)], sas[0]), Edge("right", [(w, 0), (w, h)], sas[1]),
         Edge("bottom", [(w, h), (0, h)], sas[2]), Edge("left", [(0, h), (0, 0)], sas[3])]
    gr = ((w / 2, 8), (w / 2, h - 8)) if grain_v else ((8, h / 2), (w - 8, h / 2))
    return Piece(code, name, qty, mat, e, gr, category=cat, internal=[("FOLD", f) for f in (fold or [])], note=note)

def pocket_line(size, side=1):
    """pocket zip opening (top, bottom) on the front; side +1 = wearer's left (F01). Graded: x with the chest,
    y keeps its distance above the hem."""
    with chart_ctx():
        bM = drum.Block("M"); b = drum.Block(size)
    kx = b.chest2 / bM.chest2; cx, cy = PKT_C[0] * kx, b.f_hem - (bM.f_hem - PKT_C[1])
    a = math.radians(PKT_ANGLE); u = np.array([math.sin(a), -math.cos(a)])          # up and out
    top = np.array([cx, cy]) + u * PKT_L / 2; bot = np.array([cx, cy]) - u * PKT_L / 2
    return [(side * top[0], top[1]), (side * bot[0], bot[1])]

def draft(size):
    with chart_ctx():
        g, mt = PT.draft(size, cuff_h=0.0)
    for k in ("C01", "C02", "IC01", "K01", "K02", "IK01", "IK02", "L01", "L02", "L03", "P01", "IP01", "P03", "R01", "R02"):
        g.pop(k, None)
    for code, side in (("F01", 1), ("F02", -1)):
        pc = g[code]; pc.material = SHERPA; t_, b_ = pocket_line(size, side)
        u = np.array(b_) - np.array(t_); u = u / np.linalg.norm(u); v = np.array([-u[1], u[0]]) * 3
        box = [tuple(np.array(t_) + v), tuple(np.array(b_) + v), tuple(np.array(b_) - v), tuple(np.array(t_) - v)]
        pc.internal = [("POCKET ZIP OPENING", box + [box[0]])]
        pc.drills = [tuple(np.array(t_) + u * 3), tuple(np.array(b_) - u * 3)]
        pc.note = "jacquard placed per panel (J pages); pocket zip opening marked; embroidery on the cut piece"
    for code in ("B01", "S01", "S02"):
        g[code].material = SHERPA
        g[code].note = "jacquard placed per panel (J pages)" + ("; sparkle embroidery E3" if code == "S02" else "")
    g["B01"].note = "jacquard placed per panel (J pages); back motif NOT SHOWN in the mockup"
    # ---- stand collar: straight-ish band, neck edge = body neckline, slight curve (front end rises 8 mm)
    Ln = 2 * (mt["neck_b"] + mt["neck_f"]); H = COLLAR_H
    xs = np.linspace(-Ln / 2, Ln / 2, 61); rise = 8.0
    neck = [(x, -rise * (abs(x) / (Ln / 2)) ** 2) for x in xs]
    # neck edge arc length must equal Ln: rescale x
    k = Ln / alen(neck); neck = [(x * k, y) for x, y in neck]
    top = [(x, y - H) for x, y in neck][::-1]
    xL, xR = neck[0][0], neck[-1][0]
    nb = mt["neck_b"]; nl = alen(neck) / 2
    def collar(code, nm, mat, cat, note):
        return Piece(code, nm, "1", mat, [Edge("neck", neck, PT.SA_STD, [nl - nb, nl, nl + nb]),
                                          Edge("front R", [neck[-1], top[0]], PT.SA_STD),
                                          Edge("top fold", top, PT.SA_EDGE, [alen(top) / 2]),
                                          Edge("front L", [top[-1], neck[0]], PT.SA_STD)],
                     grain=((0, -15), (0, -H + 15)), category=cat, note=note)
    g["C01"] = collar("C01", "COLLAR OUTER", "Taslan — nylon, sky blue (lab dip to the sky sherpa)", "SHELL", "outer face; notches = CB + shoulder seams")
    g["C02"] = collar("C02", "COLLAR INNER", "Sherpa — cream, plain", "SHELL", "inside face; seamed to C01 at the top edge")
    # ---- CF zip facing strip (taslan) covers the zip tape + sherpa seam inside
    cf = g["F01"].edges[0].length
    g["Z01"] = _rect("Z01", "ZIP FACING STRIP", "2", "Taslan — nylon, navy", ZIPF_W, cf + H, (PT.SA_STD, PT.SA_EDGE, PT.SA_HEM, PT.SA_EDGE),
                     note="from hem to collar top; edge-stitched over the zip tape")
    # ---- bindings (navy, cut on the cross / stretch-woven)
    hem_len = 2 * g["F01"].edges[-1].length + g["B01"].edges[4].length
    sleeve_open = g["S01"].edges[2].length
    g["BD1"] = _rect("BD1", "HEM BINDING", "1", "Binding — navy taslan, cross-cut", hem_len, BIND_CUT, (0, PT.SA_STD, 0, PT.SA_STD),
                     cat="TRIM", fold=[[(0, BIND_CUT / 2), (hem_len, BIND_CUT / 2)]], note=f"{BIND_W/10:.1f} cm finished, encloses the hem edge; ends turned in at the zip")
    g["BD2"] = _rect("BD2", "CUFF BINDING", "2", "Binding — navy taslan, cross-cut", sleeve_open, BIND_CUT + 10, (0, PT.SA_STD, 0, PT.SA_STD),
                     cat="TRIM", fold=[[(0, (BIND_CUT + 10) / 2), (sleeve_open, (BIND_CUT + 10) / 2)]], note=f"loop; {CUFF_EL_W/10:.0f} cm elastic inside the channel")
    g["BD3"] = _rect("BD3", "COLLAR SEAM PIPING", "1", "Binding — navy taslan, cross-cut", Ln, 30.0, (0, PT.SA_EDGE, 0, PT.SA_EDGE),
                     cat="TRIM", fold=[[(0, 15.0), (Ln, 15.0)]], note=f"folded, {PIPE_W/10:.1f} cm visible in the collar / body seam")
    g["P02"] = Piece("P02", "POCKET BAG", "4 (2 pairs)", "Pocketing — tricot fleece 160 g, cream",
                     [Edge("opening", [(0, 0), (0, PBAG_D)], PT.SA_STD), Edge("bottom", [(0, PBAG_D), (PBAG_W, PBAG_D - 25)], PT.SA_STD),
                      Edge("side", [(PBAG_W, PBAG_D - 25), (PBAG_W, 30)], PT.SA_STD), Edge("top", [(PBAG_W, 30), (0, 0)], PT.SA_STD)],
                     ((PBAG_W / 2, 20), (PBAG_W / 2, PBAG_D - 40)), category="POCKETING", note="zip-side bag sewn to the zip tape; caught in the side seam? no — free-hanging, bar-tacked to the CF facing")
    g["P04"].material = "Taslan — nylon, navy"; g["P04"].note = "folded in 4, edge-stitched; in the collar seam at CB"
    el_cuff = 2 * m("H", size)
    mt.update(Ln=Ln, hem_len=hem_len, sleeve_open=sleeve_open, el_cuff=el_cuff, collar_h=H, pocket=pocket_line(size, 1))
    return g, mt

ORDER = ["B01", "F01", "F02", "S01", "S02", "C01", "C02", "Z01", "P02", "P04", "BD1", "BD2", "BD3"]

# ---------------------------------------------------------------- QA (pattern vs fleece chart + seam walks)
def measure(size):
    g, mt = draft(size); b = mt["block"]; S_ = g["S01"]
    def sleeve_width(yy):
        u = LineString(S_.sew()).intersection(LineString([(-1000, yy), (1000, yy)]))
        xs = [p.x for p in (u.geoms if hasattr(u, "geoms") else [u])]; return max(xs) - min(xs)
    E = lambda code, nm: next(e.length for e in g[code].edges if e.name == nm)
    meas = {"A": mt["hem_b"] - (mt["hps_b"][1] + PT.FWD), "B": 2 * mt["ua_f"][0], "C": 2 * mt["sp_b"][0],
            "D": g["F01"].edges[-1].length * 2 / 2 + g["B01"].edges[4].length / 2 - g["B01"].edges[4].length / 2,
            "E": math.hypot(b.chest2 - b.sh2, mt["ua_b"][1] - b.b_sp[1]), "F": sleeve_width(25.0) / 2,
            "G": mt["cap_h"] + mt["Lu"], "H": mt["el_cuff"] / 2, "J": 2 * mt["hps_f"][0], "K": -(mt["hps_f"][1] - PT.FWD),
            "L": -(mt["hps_b"][1] + PT.FWD), "P": PT.FWD, "M": COLLAR_H, "Q": BIND_W,
            "R": math.dist(*mt["pocket"])}
    meas["D"] = g["B01"].edges[4].length                          # 1/2 sweep = back hem width, flat
    walks = [("Shoulder: back vs front", E("B01", "shoulder R"), E("F01", "shoulder"), 1.5),
             ("Side seam: back vs front", E("B01", "side R"), E("F01", "side"), 1.5),
             ("Sleeve cap vs armhole (ease)", S_.edges[0].length, mt["AH"], None),
             ("Underarm: front vs back", S_.edges[1].length, S_.edges[3].length, 1.0),
             ("Collar neck vs body neckline", E("C01", "neck"), mt["Ln"], 1.5),
             ("Collar outer vs inner (top)", E("C01", "top fold"), E("C02", "top fold"), 0.5),
             ("Hem binding vs body hem", g["BD1"].edges[0].length, mt["hem_len"], 1.0),
             ("Cuff binding vs sleeve opening", g["BD2"].edges[0].length, mt["sleeve_open"], 1.0),
             ("Zip facing vs CF + collar", g["Z01"].edges[1].length, g["F01"].edges[0].length + COLLAR_H, 1.0)]
    return meas, walks, mt

def shape_checks(size):
    g, mt = draft(size); out = []
    pc = g["F01"]; e = next(x for x in pc.edges if x.name == "neck"); a, b = e.pts[0], e.pts[-1]
    out.append(("F01 neck scooped (chord outside piece)", not pc.sew_poly().buffer(-0.01).contains(Point((a[0]+b[0])/2, (a[1]+b[1])/2)), ""))
    for code in ORDER:
        pc = g[code]; c = PT.cut_poly(pc); sp = pc.sew_poly()
        ok = c.is_valid and sp.is_valid and c.buffer(0.5).contains(sp) and (c.area > sp.area or all(e.sa == 0 for e in pc.edges))
        out.append((f"{code} cut line encloses sew line", ok, f"+{(c.area - sp.area)/100:.0f} cm²"))
    r = mt["el_cuff"] / mt["sleeve_open"]
    out.append(("cuff elastic / sleeve opening 0.70–0.85", 0.70 <= r <= 0.85, f"{r:.2f}"))
    for side, code in ((1, "F01"), (-1, "F02")):
        t_, b_ = pocket_line(size, side); sp = g[code].sew_poly()
        d = min(sp.exterior.distance(Point(t_)), sp.exterior.distance(Point(b_)))
        out.append((f"{code} pocket opening ≥ 40 mm inside the seams", d >= 40, f"{d:.0f} mm"))
    return out

def chart(): return chart_vals()

if __name__ == "__main__":
    for sz in SIZES:
        meas, walks, mt = measure(sz); ch = chart_vals()
        dev = {k: round(meas[k] / 10 - ch[k][2][SIZES.index(sz)], 2) for k in ch}
        bad = [c for c in shape_checks(sz) if not c[1]]
        print(sz, "dev>tol", {k: v for k, v in dev.items() if abs(v) > ch[k][3]}, "shape", "ok" if not bad else bad)
        for nm, a, b, tol in walks:
            if tol is not None and abs(a - b) > tol: print("   WALK", nm, round(a, 1), round(b, 1))
        if sz == "M":
            print("  dev", dev); print("  walks", [(n, round(a), round(b)) for n, a, b, _ in walks])
