"""Koi blossom hoodie — project core. Import this FIRST in every script of this project.

The engine's palette, region rules and colour-stop order are hard-wired for the plum + pine jacket (motifs2.PAL,
tech.RULES, tech.COLOUR_ORDER). This module adds this jacket's 12-thread palette + region codes to those shared
dicts in place (as Grand Line's glcore does) without editing engine/."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
import motifs, motifs2, tech, sheet

# ---------------------------------------------------------------- thread palette (12 threads, PROPOSED from the mockup)
KB_PAL = {   # key: (hex, name, use)
    "kb_white":  ("#F1ECE2", "Koi white",     "koi bodies, petal tips + highlights, flower stamens"),
    "kb_cream":  ("#CFC8BC", "Pearl grey",    "koi body shading, fins, tails, cream petals"),
    "kb_grey":   ("#8F8A84", "Fin grey",      "fin + tail rays, koi edge shading"),
    "kb_red":    ("#D1272D", "Koi red",       "koi red patches (kohaku)"),
    "kb_ink":    ("#15181F", "Eye black",     "koi eyes"),
    "kb_ice":    ("#C7D6EA", "Ice blue",      "lightest petal + leaf tone"),
    "kb_sky":    ("#97B2D8", "Sky blue",      "light petal + leaf tone, floating petals"),
    "kb_blue":   ("#6F93C8", "Cornflower",    "mid petal + leaf tone"),
    "kb_royal":  ("#4A73B0", "Royal blue",    "petal bases, leaf shade halves"),
    "kb_cobalt": ("#30569A", "Cobalt",        "dark flowers, leaf shade, stems"),
    "kb_navy":   ("#23396F", "Deep navy",     "flower centres, darkest leaves, vine stems"),
    "kb_slate":  ("#5E6E8C", "Slate",         "petal + leaf shadow tone"),
}
KB_KEYS = list(KB_PAL)
FABRIC = "#1F2A40"          # washed navy duck (mockup sample)
for k, v in KB_PAL.items():
    motifs2.PAL[k] = v; motifs2.HEX[k] = v[0]; motifs.HEX[k] = v[0]

# stop order inside a layer (back -> front within the layer)
KB_ORDER = ["kb_navy", "kb_cobalt", "kb_royal", "kb_slate", "kb_blue", "kb_sky", "kb_ice",
            "kb_grey", "kb_cream", "kb_white", "kb_red", "kb_ink"]
tech.COLOUR_ORDER = KB_ORDER + [c for c in tech.COLOUR_ORDER if c not in KB_ORDER]

# ---------------------------------------------------------------- region codes
# code -> (name, stitch, angle rule, density, stitch length, underlay, pull comp, notes)
KB_RULES = {
 "KO":        ("Koi body",                 "Satin, turning",     "across the body",          "0.40", "—",   "edge run + centre run",   "0.20", "split satin > 7"),
 "KO-shade":  ("Koi body shading",         "Satin, turning",     "across the body",          "0.40", "—",   "centre run",              "0.20", "long-short edge into body"),
 "KO-red":    ("Koi red patch",            "Satin, turning",     "across the body",          "0.40", "—",   "centre run",              "0.20", "sewn on top of the body"),
 "KO-head":   ("Koi head",                 "Satin",              "across head",              "0.40", "—",   "centre run",              "0.15", ""),
 "KO-eye":    ("Koi eye",                  "Satin dot",          "across dot",               "0.38", "—",   "none",                    "0.10", "Ø ≥ 1.2"),
 "KO-fin":    ("Koi fin",                  "Satin, radial",      "radial from fin base",     "0.42", "—",   "none",                    "0.15", ""),
 "KO-tail":   ("Koi tail",                 "Satin, radial",      "radial from tail root",    "0.42", "—",   "centre run",              "0.15", "forked"),
 "KO-ray":    ("Fin + tail rays",          "Run (double)",       "follows line",             "—",    "2.0", "none",                    "—",    "sewn on top of the fin"),
 "FL-petal":  ("Flower petal (body tone)", "Satin, radial",      "radial from flower centre","0.40", "—",   "edge run + centre run",   "0.20", "long-short tone steps"),
 "FL-tip":    ("Flower petal tip / edge",  "Satin, radial",      "radial from flower centre","0.40", "—",   "centre run",              "0.20", "zig-zag tone boundary"),
 "FL-base":   ("Flower petal base",        "Satin, radial",      "radial from flower centre","0.40", "—",   "centre run",              "0.20", ""),
 "FL-hl":     ("Petal highlight stroke",   "Satin",              "along petal",              "0.40", "—",   "none",                    "0.15", "on top"),
 "FL-cup":    ("Flower inner cup",         "Satin, radial",      "radial from flower centre","0.38", "—",   "none",                    "0.15", "cream inner petals"),
 "FL-eye":    ("Flower centre",            "Satin, radial",      "radial",                   "0.38", "—",   "none",                    "0.15", ""),
 "FL-stamen": ("Stamens",                  "Satin dot",          "across dot",               "0.38", "—",   "none",                    "0.10", "Ø ≥ 1.2"),
 "LF":        ("Leaf, light half",         "Satin, turning",     "midrib ± 45°",             "0.40", "—",   "centre run",              "0.20", "split satin if > 7"),
 "LF-dk":     ("Leaf, shade half",         "Satin, turning",     "midrib ± 45°",             "0.40", "—",   "centre run",              "0.20", ""),
 "LF-tip":    ("Leaf tip / edge tone",     "Satin, turning",     "midrib ± 45°",             "0.40", "—",   "none",                    "0.20", "long-short step"),
 "LF-vein":   ("Leaf midrib",              "Run (double)",       "follows line",             "—",    "2.0", "none",                    "—",    "on top"),
 "ST":        ("Stem / vine",              "Satin, turning",     "across stem",              "0.40", "—",   "centre run",              "0.15", "≥ 1.2 wide"),
 "PT":        ("Floating petal",           "Satin, turning",     "across petal",             "0.40", "—",   "centre run",              "0.20", ""),
 "PT-tone":   ("Floating petal tone",      "Satin, turning",     "across petal",             "0.40", "—",   "none",                    "0.20", "2nd tone"),
}
tech.RULES.update(KB_RULES)
tech.LAYER_NAMES.update({20: "Stems", 21: "Leaves", 22: "Flowers", 23: "Floating petals", 24: "Koi"})

sheet.FONT = "Liberation Sans"

def patch_dst2():
    """call after `import dst2`: pull-comp for this project's codes; no colour merges (12 threads)"""
    import dst2
    for k, v in KB_RULES.items():
        dst2.PULL[k] = float(v[6]) if v[6] not in ("—", "") else 0.0
    dst2.COL_MERGE.clear()
    return dst2

STYLE = "HK-HD-KOIB-NV"
NAME = "Koi Blossom Hooded Jacket — Washed Navy"
SHORT = "KOIB"
ELEMS = {"01": ("front-koi", "FRONT — koi school + blue flowers (split at the zip)", ("FR", "FL")),
         "02": ("sleeve-koi", "SLEEVES — koi, flowers + petals", ("SR", "SL"))}
PIECES = ("FR", "FL", "SR", "SL")
ELEM_OF = {"FR": "01", "FL": "01", "SR": "02", "SL": "02"}
PIECE_NAME = {"FR": "wearer's right front", "FL": "wearer's left front", "SR": "wearer's right sleeve", "SL": "wearer's left sleeve"}
PIECE_CODE = {"FR": "F02", "FL": "F01", "SR": "S01", "SL": "S02"}
SIZES = ["XS", "S", "M", "L", "XL", "XXL", "3XL"]
GRADE = {"XS": ("A", 0.92), "S": ("A", 0.92), "M": ("B", 1.0), "L": ("B", 1.0), "XL": ("B", 1.0), "XXL": ("C", 1.08), "3XL": ("C", 1.08)}
REV_EMB = "Rev A"; REV_GAR = "Rev A"; DATE = "16 Oct 2026"
def outdir(P): e = ELEM_OF[P]; return f"out/{e}_{ELEMS[e][0]}"
