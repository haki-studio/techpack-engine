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
 "KO":        ("Koi body",                 "Tatami",             "along the spine (koi axis)", "0.45", "3.5", "edge run + 90° lattice > 60 mm²", "0.20", "traced silhouette (close-up)"),
 "KO-shade":  ("Koi body shading",         "Tatami",             "along the spine",          "0.45", "3.5", "edge run",                "0.20", "traced pearl shading"),
 "KO-scale":  ("Koi scale rows",           "Run (double)",       "chevron rows across back", "—",    "2.6", "none",                    "—",    "on top of the white body"),
 "KO-red":    ("Koi red patch",            "Tatami",             "along the spine (same as body)", "0.45", "3.5", "edge run",        "0.20", "2 crisp traced patches, on top"),
 "KO-head":   ("Koi head",                 "Satin",              "across head",              "0.40", "—",   "centre run",              "0.15", ""),
 "KO-eye":    ("Koi eye",                  "Satin dot",          "across dot",               "0.38", "—",   "none",                    "0.10", "Ø 1.6"),
 "KO-fin":    ("Koi fin",                  "Satin, radial",      "fan from the fin base",    "0.40", "—",   "none",                    "0.15", "traced fin outline"),
 "KO-tail":   ("Koi tail",                 "Satin, radial",      "fan from the tail root",   "0.40", "—",   "centre run",              "0.15", "forked, traced; white base step"),
 "KO-ray":    ("Fin + tail rays",          "Run (double)",       "follows line",             "—",    "2.6", "none",                    "—",    "sewn on top of fin / tail"),
 "FL-petal":  ("Lily petal, mid tone",     "Satin, radial (long-short)", "along the petal axis (from the flower centre)", "0.40", "—", "edge run > 4 mm", "0.20", "tone regions traced from the close-up"),
 "FL-tip":    ("Lily petal, tip tone",     "Satin, radial (long-short)", "along the petal axis",   "0.40", "—",   "none",                    "0.20", "lightest tone of the petal"),
 "FL-base":   ("Lily petal, base tone",    "Satin, radial (long-short)", "along the petal axis",   "0.40", "—",   "edge run > 4 mm",         "0.20", "darkest tone of the petal"),
 "FL-hl":     ("Lily cream edge / highlight", "Satin, radial (long-short)", "along the petal axis", "0.40", "—",  "none",                    "0.15", "traced cream edges"),
 "FL-eye":    ("Lily throat",              "Satin, radial",      "radial",                   "0.38", "—",   "none",                    "0.15", "deep-blue, traced"),
 "FL-line":   ("Stamen lines",             "Run (double)",       "throat -> anther",         "—",    "2.0", "none",                    "—",    "over the throat"),
 "FL-stamen": ("Anther knots",             "Satin",              "across knot",              "0.38", "—",   "none",                    "0.10", "4-6 uneven, traced"),
 "LF":        ("Leaf, light half",         "Satin, turning",     "midrib ± 45°",             "0.40", "—",   "centre run",              "0.20", "split satin if > 7"),
 "LF-dk":     ("Leaf, shade half",         "Satin, turning",     "midrib ± 45°",             "0.40", "—",   "centre run",              "0.20", ""),
 "LF-tip":    ("Leaf tip / edge tone",     "Satin, turning",     "midrib ± 45°",             "0.40", "—",   "none",                    "0.20", "long-short step"),
 "LF-lit":    ("Leaf lit edge",            "Satin, turning",     "across the stroke",        "0.40", "—",   "none",                    "0.15", "pale-ice highlight on one edge"),
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
REV_EMB = "Rev B"; REV_GAR = "Rev A"; DATE = "19 Oct 2026"
def outdir(P): e = ELEM_OF[P]; return f"out/{e}_{ELEMS[e][0]}"
