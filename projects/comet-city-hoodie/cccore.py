"""Comet City hoodie — project core. Import this FIRST in every script of this project.

The engine's palette, region rules and colour-stop order are hard-wired for the plum + pine jacket (motifs2.PAL,
tech.RULES, tech.COLOUR_ORDER). This module adds this jacket's thread palette + region codes to those shared dicts
in place (every module that did `from motifs2 import HEX` sees them) without editing engine/ (see ENGINE_NOTES.md)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
import motifs, motifs2, tech, sheet

# ---------------------------------------------------------------- thread palette (PROPOSED, sampled from the mockup)
# 14 colours over the garment; every stitch file uses <= 12 (factory.json): the fronts use 12 (no leaf greens), the sleeves
# use white/ice/cloud/dusk/azure/leaf/leaflt/lilac.
CC_PAL = {   # key: (hex, name, use)
    "cc_white":  ("#F2F0F8", "Star white",    "star sparkles + centres, comet core line, red-star core, white windows"),
    "cc_ice":    ("#A7B4CF", "Cloud ice",     "cloud tops, bicycle, figure rim light, railing top rail, pale stars"),
    "cc_cloud":  ("#6D88B3", "Cloud blue",    "cloud middles, far haze, railing balusters"),
    "cc_dusk":   ("#405E8C", "Dusk blue",     "cloud undersides, far buildings, ground line"),
    "cc_night":  ("#1C2A4E", "Night navy",    "near buildings, figure, lamp post, railing posts"),
    "cc_azure":  ("#5AA8F2", "Azure",         "comet outer streaks, meteors, blue stars, cyan windows, leaf tips"),
    "cc_royal":  ("#2F5BCF", "Royal blue",    "comet body, bushes, sleeve leaves (shade)"),
    "cc_violet": ("#7E5FD6", "Violet",        "comet violet band, falling-star trail"),
    "cc_lilac":  ("#C2A6F0", "Lilac",         "comet lavender core, lilac stars"),
    "cc_gold":   ("#F0BE4E", "Window gold",   "lit windows, lamp light"),
    "cc_rose":   ("#E87FB2", "Neon rose",     "pink windows, city glow"),
    "cc_red":    ("#DC2F2C", "Star red",      "red falling star"),
    "cc_leaf":   ("#2B5C9E", "Leaf blue",     "sleeve leaves (body)"),
    "cc_leaflt": ("#4C83CF", "Leaf light",    "sleeve leaves (light half), firefly dots"),
}
CC_KEYS = list(CC_PAL)
FABRIC = "#141D30"          # washed navy duck (mockup sample)
for k, v in CC_PAL.items():
    motifs2.PAL[k] = v; motifs2.HEX[k] = v[0]; motifs.HEX[k] = v[0]
motifs2.FABRIC = FABRIC

CC_ORDER = ["cc_night", "cc_dusk", "cc_cloud", "cc_ice", "cc_gold", "cc_rose", "cc_royal", "cc_leaf", "cc_leaflt", "cc_azure",
            "cc_violet", "cc_lilac", "cc_red", "cc_white"]
tech.COLOUR_ORDER = CC_ORDER + [c for c in tech.COLOUR_ORDER if c not in CC_ORDER]

# ---------------------------------------------------------------- region codes
# code -> (name, stitch, angle rule, density, stitch length, underlay, pull comp, notes)
CC_RULES = {
 "CL":       ("Cloud tone patch",         "Tatami, short",      "15° rows (stepped)",     "0.45", "2.6", "edge run",                "0.20", "3 tones; light on top (mockup)"),
 "CL-hl":    ("Cloud top highlight",      "Satin",              "across band",            "0.42", "—",   "centre run",              "0.15", "ice tone along the lobe tops"),
 "HAZE":     ("Horizon haze dashes",      "Run (double)",       "0° (horizontal)",        "—",    "2.4", "none",                    "—",    "sparse, between clouds and city"),
 "COM":      ("Comet tone area (traced)", "Tatami, short",      "along the streak (-41°)", "0.42", "2.4", "edge run",                "0.15", "traced from the close-up; feathered tips"),
 "COM-core": ("Comet core (white / pink)","Tatami, short",      "along the streak (-41°)", "0.42", "2.4", "edge run",                "0.10", "own stops, sewn last in the comet"),
 "COM-cl":   ("Cloud over the comet",     "Tatami, short",      "0°",                     "0.45", "2.6", "edge run",                "0.20", "traced from the close-up"),
 "MET":      ("Meteor streak",            "Satin, turning",     "across streak",          "0.40", "—",   "none",                    "0.10", "tapered to 0.9"),
 "STAR":     ("Star arm",                 "Satin",              "across arm",             "0.40", "—",   "centre run",              "0.15", "≥ 0.9 wide, blunt tip"),
 "STAR-c":   ("Star centre",              "Satin dot",          "across dot",             "0.40", "—",   "none",                    "0.10", "Ø ≥ 1.4"),
 "DOT":      ("Star dot",                 "Satin dot",          "across dot",             "0.40", "—",   "none",                    "0.10", "Ø 1.2–2.2"),
 "RSTAR":    ("Falling star (red)",       "Satin",              "radial",                 "0.40", "—",   "centre run",              "0.15", "8 rays + white core"),
 "BLD":      ("Building (near)",          "Tatami, vertical",   "90°",                    "0.45", "3.5", "edge run + 90° lattice",  "0.20", "windows knocked out"),
 "BLD-far":  ("Building (far)",           "Tatami, vertical",   "90°",                    "0.45", "3.5", "edge run",                "0.20", "behind the near row"),
 "BLD-edge": ("Building lit edge",        "Satin",              "across",                 "0.40", "—",   "none",                    "0.15", "1.0 wide"),
 "WIN":      ("Lit window",               "Satin",              "across (short side)",    "0.40", "—",   "none",                    "0.10", "1.4 × 1.8 min"),
 "GLOW":     ("Horizon glow (violet / rose)","Tatami, horizontal","0°",                    "0.50", "3.0", "none",                    "0.15", "bands behind the far towers"),
 "RAIL":     ("Railing rail (dark)",      "Satin",              "across rail",            "0.40", "—",   "none",                    "0.15", "top rail 2.6, mid rail 1.6, night"),
 "RAIL-b":   ("Railing bar (dark)",       "Satin",              "across",                 "0.40", "—",   "none",                    "0.15", "1.3 wide, night"),
 "RAIL-hl":  ("Railing light edge",       "Satin",              "across",                 "0.40", "—",   "none",                    "0.10", "0.6–0.8 ice / cloud edge"),
 "GND":      ("Walkway / kerb",           "Tatami, horizontal", "0°",                     "0.45", "3.5", "edge run",                "0.20", ""),
 "BIKE":     ("Bicycle (dark solid)",     "Satin",              "across tube / radial",   "0.40", "—",   "none",                    "0.15", "night tyres 2.8 + tubes 1.7; ice glints"),
 "FIG":      ("Figure body",              "Tatami",             "along body",             "0.45", "3.0", "edge run",                "0.20", "seen from behind"),
 "FIG-rim":  ("Figure rim light",         "Satin",              "across rim",             "0.40", "—",   "none",                    "0.15", "1.0 wide, ice"),
 "FIG-line": ("Figure fold lines",        "Run (double)",       "follows line",           "—",    "2.0", "none",                    "—",    "jacket seam, arm folds"),
 "LAMP":     ("Lamp post",                "Satin",              "across pole",            "0.40", "—",   "centre run",              "0.15", ""),
 "LAMP-l":   ("Lamp light",               "Satin",              "across",                 "0.40", "—",   "none",                    "0.10", ""),
 "BUSH":     ("Bush mound",               "Tatami",             "75°",                    "0.45", "3.0", "edge run",                "0.20", "night, soft dome outline"),
 "BUSH-hl":  ("Bush leaf highlights",     "Satin",              "along leaf",             "0.42", "—",   "none",                    "0.10", "royal / azure / dusk dabs"),
 "SIGN":     ("Neon sign",                "Satin",              "across",                 "0.40", "—",   "none",                    "0.10", "rose / azure, 1.5 wide"),
 "ANT":      ("Antenna / aviation light", "Satin",              "across",                 "0.40", "—",   "none",                    "0.10", "0.9 wide; red dot"),
 "UG":       ("Undergrowth (sleeves)",    "Tatami",             "60°",                    "0.45", "3.0", "edge run",                "0.20", "soft fill under the leaves"),
 "LF":       ("Leaf / frond",             "Satin, turning",     "feather from midrib",    "0.42", "≤7",  "centre run",              "0.20", "serrated edge"),
 "LF-hl":    ("Leaf light half",          "Satin, turning",     "feather from midrib",    "0.42", "≤7",  "centre run",              "0.20", ""),
 "LF-stem":  ("Leaf stem",                "Bean (triple run)",  "follows line",           "—",    "2.0", "none",                    "—",    "0.8 line"),
 "FLY":      ("Firefly dots",             "Satin dot",          "across dot",             "0.40", "—",   "none",                    "0.10", "Ø 1.3"),
}
tech.RULES.update(CC_RULES)
tech.LAYER_NAMES.update({20 + i: f"{CC_PAL[c][1]}" for i, c in enumerate(CC_ORDER)})

# sheet font: Noto Sans CJK JP is not installed on this box -> Liberation Sans (Arial metrics)
sheet.FONT = "Liberation Sans"

def patch_dst2():
    """call after `import dst2`: pull-comp for this project's codes; no colour merging (12 threads per file)"""
    import dst2
    for k, v in CC_RULES.items():
        dst2.PULL[k] = float(v[6]) if v[6] not in ("—", "") else 0.0
    dst2.COL_MERGE.clear()
    return dst2

STYLE = "HK-HD-COMET-NV"
NAME = "Comet City Hooded Jacket — Washed Navy"
SHORT = "COMET"
PIECES = ("FR", "FL", "SR", "SL")
FRONTS = ("FR", "FL"); SLEEVES = ("SR", "SL")
PIECE_NAME = {"FR": "wearer's right front", "FL": "wearer's left front", "SR": "wearer's right sleeve", "SL": "wearer's left sleeve"}
PIECE_CODE = {"FR": "F02", "FL": "F01", "SR": "S01", "SL": "S02"}        # pattern piece codes (pattern.py)
ELEM_OF = {"FR": "01", "FL": "01", "SR": "02", "SL": "02"}
ELEMS = {"01": ("front-scene", "FRONT SCENE — comet over a night city (split at the zip)", FRONTS),
         "02": ("sleeve-garden", "SLEEVES — night garden, clouds and stars", SLEEVES)}
def edir(P): return f"out/{ELEM_OF[P]}_{ELEMS[ELEM_OF[P]][0]}"
def fname(P, size): return f"HAKI_{SHORT}_{ELEM_OF[P]}_{ELEMS[ELEM_OF[P]][0]}_{P}_{size}"
SIZES = ["XS", "S", "M", "L", "XL", "XXL", "3XL"]
GRADE = {"XS": ("A", 0.92), "S": ("A", 0.92), "M": ("B", 1.0), "L": ("B", 1.0), "XL": ("B", 1.0), "XXL": ("C", 1.08), "3XL": ("C", 1.08)}
REV_EMB = "Rev A"; REV_GAR = "Rev A"; DATE = "16 Oct 2026"
