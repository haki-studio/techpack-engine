"""Digitizing spec: region rules, stitch estimates, colour stops, thread matching."""
import math, json
import numpy as np
from shapely.ops import unary_union
from motifs2 import PAL, HEX

# code -> (name, stitch, angle rule, density, stitch length, underlay, pull comp, notes)
RULES = {
 "MI":          ("Mist bands",                 "Bean (triple run)", "follows line",            "—",        "2.2",  "none",                          "—",    "0.7 line"),
 "PB":          ("Pine branch body",           "Tatami",  "along branch",                  "0.40",  "3.5",  "edge run + 2.0 zigzag",         "0.25", ""),
 "TR":          ("Trunk body",                 "Tatami",  "along limb (map)",              "0.40",  "3.5",  "edge run + tatami 90° @ 2.0",   "0.25", "short-stitch on turns"),
 "LM":          ("Limb body",                  "Tatami",  "along limb (map)",              "0.40",  "3.5",  "edge run + tatami 90° @ 2.0",   "0.25", ""),
 "-shade":      ("Shade band / underside",     "Tatami",  "same as body",                  "0.40",  "3.0",  "edge run",                      "0.25", "blend 1 row into body"),
 "-ridge":      ("Bark ridge highlight",       "Satin",   "across ridge",                  "0.38",  "—",    "centre run",                    "0.20", "min width 1.2"),
 "-crevice":    ("Bark crevices",              "Bean (triple run)", "follows line",        "—",     "2.2",  "none",                          "—",    "sewn on top of fill"),
 "-outline":    ("Outline",                    "Bean (triple run)", "follows line",        "—",     "2.0",  "none",                          "—",    "0.7 line, last in its stop"),
 "TR-knot":     ("Bark knot",                  "Satin",   "across ring",                   "0.38",  "—",    "centre run",                    "0.15", ""),
 "TW":          ("Twig",                       "Satin",   "across twig",                   "0.38",  "—",    "centre run",                    "0.15", "≥ 1.8 wide"),
 "SN":          ("Snow on bark (raised)",      "Padded tatami", "across limb, upward (map)","0.38",  "5.0",  "2 padding layers: tatami 0.8 @ 90° + 0.8 @ 45°", "0.30", "random split, no visible rows"),
 "SN-shade":    ("Snow underside shading",     "Satin / split satin", "same as snow",      "0.38",  "≤7.0", "edge run",                      "0.25", ""),
 "SN-shadow":   ("Snow cast shadow on bark",   "Satin",   "across band",                   "0.40",  "—",    "centre run",                    "0.15", "tapered ends OK"),
 "SN-lump":     ("Snow lump contours",         "Run (single)", "follows line",             "—",     "2.0",  "none",                          "—",    "sewn on top of snow"),
 "PB-SN":       ("Snow on pine branch",        "Padded tatami", "across branch",           "0.38",  "5.0",  "1 padding layer",               "0.30", ""),
 "BL-petal":    ("Blossom petal",              "Satin, turning", "radial from flower centre","0.36", "—",    "centre run + edge run",         "0.20", "short-stitch toward centre"),
 "BL-rim":      ("Petal rim (light)",          "Satin, turning", "radial",                 "0.36",  "—",    "edge run",                      "0.20", "blend 1 row into petal"),
 "BL-base":     ("Petal base ring",            "Satin",   "radial",                        "0.36",  "—",    "centre run",                    "0.15", ""),
 "BL-eye":      ("Flower eye",                 "Satin",   "fixed",                         "0.36",  "—",    "none",                          "0.10", ""),
 "BL-stamen":   ("Stamen filaments",           "Bean (triple run)", "radial lines",        "—",     "1.8",  "none",                          "—",    ""),
 "BL-anther":   ("Anther dots",                "Satin dot", "across dot",                  "0.36",  "—",    "none",                          "0.10", "Ø ≥ 1.2"),
 "BL-outline":  ("Petal outline + splits",     "Bean (triple run)", "follows line",        "—",     "2.0",  "none",                          "—",    ""),
 "BD":          ("Bud",                        "Satin",   "across bud, perp. to stem",            "0.36",  "—",    "centre run",                    "0.20", "Ø 6.2–7.6"),
 "BD-calyx":    ("Bud calyx",                  "Satin",   "across",                        "0.36",  "—",    "none",                          "0.15", ""),
 "BD-hl":       ("Bud highlight",              "Satin dot", "across",                      "0.36",  "—",    "none",                          "0.10", "Ø ≥ 1.24"),
 "LF-light":    ("Leaf, light half",           "Satin",   "midrib + 50° (feather)",        "0.40",  "—",    "centre run",                    "0.20", "split satin if > 7"),
 "LF-shade":    ("Leaf, shade half",           "Satin",   "midrib − 50° (feather)",        "0.40",  "—",    "centre run",                    "0.20", ""),
 "LF-vein":     ("Leaf midrib",                "Bean (triple run)", "follows line",        "—",     "2.0",  "none",                          "—",    ""),
 "LF-snow":     ("Snow on leaf",               "Satin",   "vertical",                      "0.38",  "—",    "centre run",                    "0.20", ""),
 "BB-light":    ("Bamboo blade, light half",   "Satin",   "blade + 55°",                   "0.40",  "—",    "centre run",                    "0.20", "split satin if > 7"),
 "BB-shade":    ("Bamboo blade, shade half",   "Satin",   "blade − 55°",                   "0.40",  "—",    "centre run",                    "0.20", ""),
 "BB-snow":     ("Snow on bamboo",             "Satin",   "vertical",                      "0.38",  "—",    "centre run",                    "0.20", ""),
 "PR-fan":      ("Red pine fan",               "Tatami, turning", "radial from hub",       "0.40",  "3.5",  "edge run + tatami @ 2.0",       "0.25", ""),
 "PR-needle":   ("Red pine needles",           "Bean (triple run)", "radial lines",        "—",     "2.2",  "none",                          "—",    ""),
 "PW-fan":      ("White pine fan",             "Tatami, turning", "radial from hub",       "0.40",  "3.5",  "edge run + tatami @ 2.0",       "0.25", ""),
 "PW-inner":    ("White pine gold inner",      "Tatami, turning", "radial from hub",       "0.40",  "3.0",  "edge run",                      "0.20", "gradient-blend 2 rows into fan"),
 "PW-needle":   ("White pine needles",         "Bean (triple run)", "radial lines",        "—",     "2.2",  "none",                          "—",    ""),
 "P-hub":       ("Pine hub",                   "Satin",   "radial",                        "0.36",  "—",    "none",                          "0.15", ""),
 "P-snow":      ("Snow on pine fan",           "Padded satin / tatami", "vertical",       "0.38",  "5.0",  "1 padding layer",               "0.30", ""),
 "P-snow-shade":("Pine snow shading",          "Satin",   "vertical",                      "0.38",  "—",    "edge run",                      "0.20", ""),
}

def rule_for(grp):
    if grp.startswith("PB-SN"): grp = grp[3:] if grp != "PB-SN" else "PB-SN"
    if grp in RULES: return grp
    for suf in ("-outline", "-crevice", "-shade", "-ridge"):
        if grp.endswith(suf): return suf
    base = grp.split("-")[0]
    return base if base in RULES else grp

def stitches(r):
    g = r["geom"]; A = g.area; P = g.length; st = r["st"]
    if A <= 0: return 0
    if st == "bean": return (A/0.7)/2.2*3
    if st == "run":  return (A/0.7)/2.0
    if st == "tatami": return A/(0.40*3.5) + A/(2.0*3.5) + P/2.5
    if st == "padded": return A/(0.38*5.0) + 2*A/(0.8*4.0) + P/2.5
    w = max(0.8, 2*A/max(P, 1e-6))
    rows = (A/w)/0.37
    split = math.ceil(w/7.0)                 # split satin for wide columns
    return rows*split + (A/w)/2.5           # + centre-run underlay

# ---------------------------------------------------------------- CIEDE2000 thread matching
def _lab(rgb):
    def lin(c):
        c = c/255; return c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4
    r, g, b = map(lin, rgb)
    X = (0.4124*r + 0.3576*g + 0.1805*b)/0.95047; Y = 0.2126*r + 0.7152*g + 0.0722*b; Z = (0.0193*r + 0.1192*g + 0.9505*b)/1.08883
    f = lambda t: t**(1/3) if t > 0.008856 else 7.787*t + 16/116
    return (116*f(Y) - 16, 500*(f(X) - f(Y)), 200*(f(Y) - f(Z)))

def de2000(l1, l2):
    L1, a1, b1 = l1; L2, a2, b2 = l2
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2); Cb = (C1 + C2)/2
    G = 0.5*(1 - math.sqrt(Cb**7/(Cb**7 + 25**7)))
    a1p, a2p = (1+G)*a1, (1+G)*a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360; h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dLp = L2 - L1; dCp = C2p - C1p
    dh = h2p - h1p
    if C1p*C2p == 0: dh = 0
    elif dh > 180: dh -= 360
    elif dh < -180: dh += 360
    dHp = 2*math.sqrt(C1p*C2p)*math.sin(math.radians(dh/2))
    Lbp = (L1 + L2)/2; Cbp = (C1p + C2p)/2
    hbp = (h1p + h2p)/2 if abs(h1p - h2p) <= 180 else (h1p + h2p + 360)/2
    if C1p*C2p == 0: hbp = h1p + h2p
    T = 1 - 0.17*math.cos(math.radians(hbp-30)) + 0.24*math.cos(math.radians(2*hbp)) + 0.32*math.cos(math.radians(3*hbp+6)) - 0.20*math.cos(math.radians(4*hbp-63))
    dth = 30*math.exp(-((hbp-275)/25)**2); Rc = 2*math.sqrt(Cbp**7/(Cbp**7 + 25**7))
    Sl = 1 + 0.015*(Lbp-50)**2/math.sqrt(20 + (Lbp-50)**2); Sc = 1 + 0.045*Cbp; Sh = 1 + 0.015*Cbp*T
    Rt = -math.sin(math.radians(2*dth))*Rc
    return math.sqrt((dLp/Sl)**2 + (dCp/Sc)**2 + (dHp/Sh)**2 + Rt*(dCp/Sc)*(dHp/Sh))

import os as _os
TH = json.load(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "pal", "threads.json")))
def match(hexcol, brand):
    rgb = tuple(int(hexcol[i:i+2], 16) for i in (1, 3, 5)); L = _lab(rgb)
    best = min(TH[brand], key=lambda t: de2000(L, _lab(tuple(t[2]))))
    return best[0], best[1], "#%02X%02X%02X" % tuple(best[2]), de2000(L, _lab(tuple(best[2])))

def thread_table(keys):
    out = {}
    for k in keys:
        out[k] = dict(isacord=match(HEX[k], "isacord"), polyneon=match(HEX[k], "polyneon"))
    return out

# ---------------------------------------------------------------- colour stops
LAYER_NAMES = {1: "Mist", 2: "Pine branches", 3: "Red pine", 4: "White pine", 5: "Plum trunk + limbs + twigs",
               6: "Snow on plum", 7: "Leaves", 8: "Blossoms", 9: "Buds", 10: "Bamboo"}
COLOUR_ORDER = ["grey", "bark", "barkdk", "barklt", "vermilion", "cream", "gold", "orange", "snow",
                "slate", "slatelt", "plum", "petal", "plumdk", "indigo", "lavender"]
# within a layer: fills before the lines that sit on them
ST_ORDER = {"tatami": 0, "padded": 1, "satin": 2, "run": 3, "bean": 4}

STITCH_LAYER = {9: 4.6, 8: 4.7}     # stitch files: buds + blossoms sewn before the bark so their travel hides under it

def stops(vis, layer_map=None):
    """Group visible regions into colour stops: layer order, then colour within layer;
    merge consecutive same-colour stops."""
    by = {}
    for r in vis:
        lay = r["layer"]
        if layer_map and lay == 5 and r["st"] in ("bean", "run"): lay = 6.5    # bark lines after snow: snow travel hides under them
        key = ((layer_map or {}).get(lay, lay), r["col"])
        by.setdefault(key, []).append(r)
    seq = []
    for layer in sorted({k[0] for k in by}):
        cols = [c for c in COLOUR_ORDER if (layer, c) in by]
        # outlines / bean lines of barkdk always last in the layer
        fills = [c for c in cols if not all(r["st"] in ("bean", "run") for r in by[(layer, c)])]
        lines = [c for c in cols if c not in fills]
        for c in fills + lines:
            rs = by[(layer, c)]
            seq.append(dict(col=c, layers=[int(layer) if float(layer).is_integer() else {4.6: 9, 4.7: 8, 6.5: 5}.get(layer, layer)], regions=rs, st=sum(stitches(r) for r in rs),
                            area=sum(r["geom"].area for r in rs),
                            groups=sorted({rule_for(r["grp"]) for r in rs})))
    merged = []
    for s in seq:
        if merged and merged[-1]["col"] == s["col"]:
            m = merged[-1]; m["layers"] += s["layers"]; m["regions"] += s["regions"]
            m["st"] += s["st"]; m["area"] += s["area"]; m["groups"] = sorted(set(m["groups"]) | set(s["groups"]))
        else:
            merged.append(s)
    return merged
