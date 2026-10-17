"""Red beast hoodie — project core. Import this FIRST in every script of this project.

Adds this jacket's thread palette + region codes to the engine's shared dicts in place (motifs2.PAL/HEX, tech.RULES,
tech.COLOUR_ORDER, tech.LAYER_NAMES) without editing engine/ (same pattern as grand-line-jacket/glcore.py; ROADMAP
step 1 is the engine fix)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
import motifs, motifs2, tech, sheet

# ---------------------------------------------------------------- thread palette (PROPOSED, sampled from the mockup)
RB_PAL = {   # key: (hex, name, use)
    "rb_red":     ("#C91F32", "Beast red",     "hair strokes, mane, slash streaks (main red)"),
    "rb_crimson": ("#8E1626", "Deep crimson",  "shadow strokes in the mane + streaks, inner mouth edge"),
    "rb_black":   ("#141416", "Shadow black",  "stitched black shading between the strokes, mouth + eye"),
    "rb_cream":   ("#EADFCB", "Bone cream",    "raised outlines, teeth, lightning branches"),
}
RB_KEYS = list(RB_PAL)
FABRIC = "#2B3039"          # washed black / charcoal duck (mockup sample, PROPOSED)
for k, v in RB_PAL.items():
    motifs2.PAL[k] = v; motifs2.HEX[k] = v[0]; motifs.HEX[k] = v[0]

# sew order: red hair strokes first (their travel hides under the black ground sewn after them), the black ground,
# then the cream outlines + teeth last so they sit raised on top (fidelity: "white raised outline")
SEW = ["rb_red", "rb_crimson", "rb_black", "rb_cream"]
tech.COLOUR_ORDER = SEW + [c for c in tech.COLOUR_ORDER if c not in SEW]

# ---------------------------------------------------------------- region codes
# code -> (name, stitch, angle rule, density, stitch length, underlay, pull comp, notes)
RB_RULES = {
 "HR":      ("Hair stroke (red)",          "Satin, turning",       "across the stroke",          "0.40", "≤7",  "centre run (≥ 2 wide)",      "0.20", "strands ≥ 1.0 wide (tips grown along the skeleton)"),
 "HR-fill": ("Hair mass (red)",            "Tatami, flow angle",   "along the hair flow (traced)","0.42", "3.5", "edge run + 90° lattice",     "0.20", "long-and-short look; angle per 14 mm cell"),
 "SK":      ("Slash streak",               "Satin, turning",       "across the streak",          "0.40", "≤7",  "centre run (≥ 2 wide)",      "0.20", "≥ 1.0 wide; split satin > 7"),
 "SK-fill": ("Slash streak, wide part",    "Tatami, flow angle",   "along the streak",           "0.42", "3.5", "edge run",                   "0.20", ""),
 "BK":      ("Black shading stroke",       "Satin, turning",       "across the stroke",          "0.42", "≤7",  "none",                       "0.15", "black on black: texture, not colour"),
 "BK-fill": ("Black ground",               "Tatami, flow angle",   "along the hair flow",        "0.45", "3.5", "edge run + 90° lattice",     "0.20", "fills between the red strokes (sewn after red)"),
 "OL":      ("Raised outline (cream)",     "Satin, turning",       "across the line",            "0.38", "≤7",  "centre run + edge run",      "0.20", "1.2–3.5 wide; sewn last, on top"),
 "OL-fill": ("Tooth / bone (cream)",       "Satin / tatami",       "along the tooth",            "0.40", "3.5", "edge run",                   "0.20", "teeth, eye white"),
}
tech.RULES.update(RB_RULES)
tech.LAYER_NAMES.update({20: "Red hair + streaks", 21: "Crimson shadow strokes", 22: "Black shading", 23: "Cream outlines + teeth"})

sheet.FONT = "Liberation Sans"

def patch_dst2():
    """call after `import dst2`: pull-comp for this project's codes; 4 threads -> nothing to merge"""
    import dst2
    for k, v in RB_RULES.items():
        dst2.PULL[k] = float(v[6]) if v[6] not in ("—", "") else 0.0
    dst2.COL_MERGE.clear()
    return dst2

STYLE = "HK-HD-RBST-BK"
NAME = "Red Beast Hooded Jacket — Washed Black"
SHORT = "RBST"
ELEMS = {   # element -> (slug, title, pieces)
    "01": ("beast-head", "01 BEAST HEAD — fronts (head, mane, lightning, streaks)", ("FR", "FL")),
    "02": ("sleeve-streaks", "02 SLASH STREAKS — sleeves", ("SR", "SL")),
}
PIECES = ("FR", "FL", "SR", "SL")
PIECE_ELEM = {"FR": "01", "FL": "01", "SR": "02", "SL": "02"}
PIECE_NAME = {"FR": "wearer's right front", "FL": "wearer's left front", "SR": "wearer's right sleeve", "SL": "wearer's left sleeve"}
PIECE_CODE = {"FR": "F02", "FL": "F01", "SR": "S01", "SL": "S02"}        # pattern piece codes (pattern.py)
SIZES = ["XS", "S", "M", "L", "XL", "XXL", "3XL"]
GRADE = {"XS": ("A", 0.92), "S": ("A", 0.92), "M": ("B", 1.0), "L": ("B", 1.0), "XL": ("B", 1.0), "XXL": ("C", 1.08), "3XL": ("C", 1.08)}
REV_EMB = "Rev A"; REV_GAR = "Rev A"; DATE = "16 Oct 2026"

def fname(P, size, sec=None):
    e = PIECE_ELEM[P]; slug = ELEMS[e][0]
    return f"HAKI_{SHORT}_{e}_{slug}_{P}_{size}" + (f"_{sec}" if sec else "")
def outdir(P, size):
    e = PIECE_ELEM[P]; return f"out/{e}_{ELEMS[e][0]}/{size}"
