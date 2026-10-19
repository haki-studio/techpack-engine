"""Boxy zip hoodie block — derived from the APPROVED Drum Island jacket (Haki, 16 Oct 2026: "same body as the jacket").

Body, sleeve, welts, facings and body lining are the jacket pattern (pattern.draft). Explicit deltas only:
  - hood (3 panels: side pair + centre panel), sherpa-lined, replaces the collar (C01/C02/IC01 removed)
  - self-fabric hem band + cuff bands with elastic replace the rib hem + cuffs (R01/R02 redrafted)
  - two-way separating zip (BOM)
Every number not on the jacket chart is PROPOSED (HOOD_CM, BAND, PROPOSED) and printed amber in documents.
Coords as pattern.py (mm, y down). Hood pieces: x from the face edge toward the back, y up = negative, neck at y≈0.
"""
import math
import numpy as np
from shapely.geometry import Polygon
import drum, pattern as PT
from pattern import Edge, Piece, alen, at, mirror, rev

BLOCK = "zip-hoodie"; NAME = "Boxy zip hoodie (Drum Island body)"
SIZES = drum.SIZES
INHERITED = ["A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "P"]       # jacket chart codes kept as-is
HOOD_CM = {   # PROPOSED — sherpa pile (~8 mm) allowance included (+1.5 cm on height and width vs an unlined hood)
    "Q": ("Hood height", "HPS neck seam to top of hood, flat", [35.0, 35.5, 36.0, 36.5, 37.0, 37.5, 38.0], 1.0),
    "R": ("Hood width", "face edge to back fold, widest, flat", [25.0, 25.5, 26.0, 26.5, 27.0, 27.5, 28.0], 1.0),
    "S": ("Hem band height", "finished, self fabric + elastic", [5.5] * 7, 0.3),
    "T": ("Cuff band height", "finished, self fabric + elastic", [5.0] * 7, 0.3),
}
CW = 100.0                 # hood centre panel width (proposed)
NECK_RISE = 45.0           # hood neck edge rises from CF to the back (side view)
FLAT = 60.0                # hem band: no elastic for 6 cm each side of the zip (zip sits flat)
EL_HEM_W, EL_CUFF_W = 40.0, 35.0
PROPOSED = {"Hood": "3 panels, centre panel 10 cm; sherpa-lined; no drawcord; face edge bagged + 6 mm topstitch",
            "Hood height / width (M)": "36 / 26 cm incl. 1.5 cm sherpa allowance", "Hem band": "5.5 cm self fabric, 4 cm elastic, flat 6 cm each side of zip",
            "Cuff band": "5 cm self fabric, 3.5 cm elastic loop", "Zip": "2-way separating, YKK #5 metal, antique brass",
            "Body lining": "cotton flannel plaid (as jacket); sleeves taffeta", "Hood lining": "sherpa 280 g/m² polyester, cream"}

def hcm(code, size): return HOOD_CM[code][2][SIZES.index(size)] * 10.0

# ---------------------------------------------------------------- hood
def _side_panel(Ls, hs, ws, lean=8.0):
    """side panel outline pieces. Ls = neck edge length; hs, ws = side height / width before the centre panel."""
    lo, hi = 0.5 * Ls, Ls
    for _ in range(60):                                          # neck edge: front (0,0) -> back, rising, sagging 12 mm
        xb = (lo + hi) / 2; neck = drum.curve((0, 0), (xb, -NECK_RISE), -12, 40)
        if alen(neck) > Ls: hi = xb
        else: lo = xb
    Bn = neck[-1]; Ft = (-lean, -hs)
    r = 0.55 * ws                                                # rounded crown (superellipse quarter, exp 2.4)
    cx, cy = ws - r, -hs + r
    q = [(cx + r * abs(math.cos(t)) ** (2 / 2.4), cy - r * abs(math.sin(t)) ** (2 / 2.4)) for t in np.linspace(0, math.pi / 2, 30)]
    back = [Bn] + [(ws, y) for y in np.linspace(Bn[1] - 40, cy, 6)] + q[1:] + [Ft]   # neck back point -> up -> crown -> face top
    back = [p for i, p in enumerate(back) if i == 0 or math.hypot(p[0] - back[i-1][0], p[1] - back[i-1][1]) > 0.5]
    face = [Ft, (-lean * 0.4, -hs * 0.5), (0, 0)]
    return neck, back, face

def hood(size, Ln_half, neck_f_len):
    """solve side panel height/width so the FLAT hood measures the chart Q/R (incl. half the centre panel)."""
    Ls = Ln_half - CW / 2
    Q, R = hcm("Q", size), hcm("R", size); hs, ws = Q - CW / 2 + 20, R - CW / 2
    for _ in range(40):
        neck, back, face = _side_panel(Ls, hs, ws)
        hps, _ = at(neck, neck_f_len)
        allp = neck + back + face
        mh = hps[1] - min(y for _, y in allp) + CW / 2
        mw = max(x for x, _ in allp) - min(x for x, _ in allp) + CW / 2
        if abs(mh - Q) < 0.05 and abs(mw - R) < 0.05: break
        hs += Q - mh; ws += R - mw
    return dict(neck=neck, back=back, face=face, hps=hps, Q=mh, R=mw, Ls=Ls, seam=alen(back), face_len=alen(face))

# ---------------------------------------------------------------- draft
def draft(size, welt=None):
    """welt: per-design welt override, see pattern.draft. For pattern_out pass blk=hoodie.Variant(welt=...)."""
    T = hcm("T", size)
    g, mt = PT.draft(size, cuff_h=T, welt=welt)
    for k in ("C01", "C02", "IC01"): g.pop(k, None)
    for pc in g.values():                                        # jacket-only notes
        if pc.note.startswith("01 wrap") or "embroidery" in pc.note: pc.note = ""
    g["K02"].note = "main + size label 1 cm below the hood seam"
    Ln_half = mt["neck_b"] + mt["neck_f"]
    H = hood(size, Ln_half, mt["neck_f"])
    side = [Edge("neck", H["neck"], PT.SA_STD, [mt["neck_f"]]),           # notch = shoulder seam (HPS)
            Edge("centre seam", H["back"], PT.SA_STD, [H["seam"] / 2]),
            Edge("face edge", H["face"], PT.SA_EDGE)]
    grain = ((H["hps"][0], -40), (H["hps"][0], -H["Q"] + CW / 2 + 60))
    for code, nm, mat, cat in (("H01", "HOOD SIDE", "Shell — 12 oz duck", "SHELL"), ("H03", "HOOD SIDE LINING", "Sherpa — 280 g/m² polyester, cream", "LINING")):
        g[code] = Piece(code, nm, "1 pair", mat, side, grain, category=cat,
                        note="pair = mirror; notch at HPS meets the shoulder seam" if code == "H01" else "bagged to the shell at the face edge")
    L = H["seam"]
    ctr = [Edge("neck end", [(CW / 2, 0), (-CW / 2, 0)], PT.SA_STD, [CW / 2]),
           Edge("side L", [(-CW / 2, 0), (-CW / 2, -L)], PT.SA_STD, [L / 2]),
           Edge("face end", [(-CW / 2, -L), (CW / 2, -L)], PT.SA_EDGE),
           Edge("side R", [(CW / 2, -L), (CW / 2, 0)], PT.SA_STD, [L / 2])]
    for code, nm, mat, cat in (("H02", "HOOD CENTRE PANEL", "Shell — 12 oz duck", "SHELL"), ("H04", "HOOD CENTRE LINING", "Sherpa — 280 g/m² polyester, cream", "LINING")):
        g[code] = Piece(code, nm, "1", mat, ctr, ((0, -30), (0, -L + 30)), category=cat, note="neck-end notch = CB")
    # self-fabric bands (fold line at the finished height; elastic inside)
    S = hcm("S", size); body_hem = 2 * g["F01"].edges[-1].length + g["B01"].edges[4].length
    sleeve_open = g["S01"].edges[2].length
    def band(code, name, qty, L_, h_, note):
        e = [Edge("top", [(0, 0), (L_, 0)], PT.SA_HEM), Edge("right", [(L_, 0), (L_, 2 * h_)], PT.SA_STD),
             Edge("bottom", [(L_, 2 * h_), (0, 2 * h_)], PT.SA_HEM), Edge("left", [(0, 2 * h_), (0, 0)], PT.SA_STD)]
        return Piece(code, name, qty, "Shell — 12 oz duck", e, ((40, h_ / 2), (L_ - 40, h_ / 2)), category="SHELL",
                     internal=[("FOLD", [(0, h_), (L_, h_)])], note=note)
    el_hem = 2 * drum.m("D", size) - 2 * FLAT                   # relaxed sweep = chart D (unchanged from the jacket)
    el_cuff = 2 * drum.m("H", size)                              # relaxed opening = chart H
    g["R01"] = band("R01", "HEM BAND", "1", body_hem, S,
                    f"self fabric, folded; {EL_HEM_W:.0f} mm elastic {el_hem:.0f} mm relaxed, flat {FLAT/10:.0f} cm each side of the zip; ends into the zip")
    g["R02"] = band("R02", "CUFF BAND", "2", sleeve_open, T, f"self fabric, folded, closed into a loop; {EL_CUFF_W:.0f} mm elastic loop {el_cuff:.0f} mm + 15 overlap")
    for code in ("K01", "K02", "P01"):                           # fusing kept (jacket); collar fusing removed above
        pass
    mt.update(hood=H, hem_band=body_hem, el_hem=el_hem, el_cuff=el_cuff, sleeve_open=sleeve_open, cuff_h=T, hem_h=S, Ln_half=Ln_half)
    return g, mt

ORDER = ["B01", "F01", "F02", "S01", "S02", "H01", "H02", "K01", "K02", "P01", "P02", "P03", "P04", "R01", "R02",
         "L01", "L02", "L03", "H03", "H04", "IK01", "IK02", "IP01"]

def chart():
    """the hoodie size chart: inherited jacket POMs + hood/band POMs. {code: (name, how, values cm, tol, source)}"""
    out = {k: drum.POM_CM[k] + ("jacket (approved)",) for k in INHERITED}
    out["D"] = (drum.POM_CM["D"][0], "1/2, hem edge, relaxed (elastic sets it)") + drum.POM_CM["D"][2:] + ("jacket (approved)",)
    out["H"] = (drum.POM_CM["H"][0], "1/2, cuff edge, relaxed (elastic sets it)") + drum.POM_CM["H"][2:] + ("jacket (approved)",)
    for k, v in HOOD_CM.items(): out[k] = v + ("PROPOSED",)
    return out

# ---------------------------------------------------------------- QA
def measure(size):
    g, mt = draft(size); b = mt["block"]; S_ = g["S01"]
    from shapely.geometry import LineString
    def sleeve_width(yy):
        u = LineString(S_.sew()).intersection(LineString([(-1000, yy), (1000, yy)]))
        xs = [p.x for p in (u.geoms if hasattr(u, "geoms") else [u])]; return max(xs) - min(xs)
    H = mt["hood"]
    m = {"A": mt["hem_b"] - (mt["hps_b"][1] + PT.FWD) + mt["hem_h"], "B": 2 * mt["ua_f"][0], "C": 2 * mt["sp_b"][0],
         "D": (2 * FLAT + mt["el_hem"]) / 2, "E": math.hypot(b.chest2 - b.sh2, mt["ua_b"][1] - b.b_sp[1]),
         "F": sleeve_width(25.0) / 2, "G": mt["cap_h"] + mt["Lu"] + mt["cuff_h"], "H": mt["el_cuff"] / 2,
         "J": 2 * mt["hps_f"][0], "K": -(mt["hps_f"][1] - PT.FWD), "L": -(mt["hps_b"][1] + PT.FWD), "P": PT.FWD,
         "Q": H["Q"], "R": H["R"], "S": g["R01"].internal[0][1][0][1], "T": g["R02"].internal[0][1][0][1]}
    E = lambda code, nm: next(e.length for e in g[code].edges if e.name == nm)
    walks = [("Shoulder: back vs front", E("B01", "shoulder R"), E("F01", "shoulder"), 1.5),
             ("Side seam: back vs front", E("B01", "side R"), E("F01", "side"), 1.5),
             ("Sleeve cap vs armhole (ease)", S_.edges[0].length, mt["AH"], None),
             ("Hood neck (side + ½ centre) vs body half neckline", E("H01", "neck") + CW / 2, mt["Ln_half"], 1.0),
             ("Hood side centre seam vs centre panel side", E("H01", "centre seam"), E("H02", "side L"), 1.0),
             ("Hood lining vs shell (side neck)", E("H03", "neck"), E("H01", "neck"), 0.5),
             ("Hem band vs body hem", g["R01"].edges[0].length, mt["hem_band"], 1.0),
             ("Cuff band vs sleeve opening", g["R02"].edges[0].length, mt["sleeve_open"], 1.0),
             ("Facing CF vs front CF", g["K01"].edges[0].length, g["F01"].edges[0].length, 1.0),
             ("Lining side vs shell side (front)", E("L01", "side"), E("F01", "side"), 1.0)]
    return m, walks, mt

def shape_checks(size):
    from shapely.geometry import Point
    g, mt = draft(size); out = []
    for code in ORDER:
        pc = g[code]
        if getattr(pc, "inset", 0): continue
        c = PT.cut_poly(pc); sp = pc.sew_poly()
        ok = c.is_valid and sp.is_valid and c.buffer(0.5).contains(sp) and (c.area > sp.area or all(e.sa == 0 for e in pc.edges))
        out.append((f"{code} cut line encloses sew line", ok, f"+{(c.area - sp.area)/100:.0f} cm²"))
    r = mt["el_cuff"] / mt["sleeve_open"]
    out.append(("cuff elastic / sleeve opening 0.75–0.85", 0.75 <= r <= 0.85, f"{r:.2f}"))
    rh = (mt["el_hem"] + 2 * FLAT) / mt["hem_band"]
    out.append(("hem elastic + flat / body hem 0.85–1.0", 0.85 <= rh <= 1.0, f"{rh:.2f}"))
    H = mt["hood"]; hs = Polygon(H["neck"] + H["back"][1:] + H["face"][1:]).buffer(0)
    out.append(("hood side panel is one simple shape", hs.geom_type == "Polygon" and hs.is_valid, f"{hs.area/100:.0f} cm²"))
    return out


class Variant:
    """hoodie with per-design options (e.g. the welt): pattern_out.write_dxf(..., blk=hoodie.Variant(welt=dict(...)))."""
    def __init__(self, **kw): self.kw = kw
    def draft(self, size): return draft(size, **self.kw)
