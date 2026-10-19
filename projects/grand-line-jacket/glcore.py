"""Grand Line jacket — project core. Import this FIRST in every script of this project.

The engine's palette, region rules and colour-stop order are hard-wired for the plum + pine jacket (motifs2.PAL,
tech.RULES, tech.COLOUR_ORDER). This module adds this jacket's thread palette + region codes to those shared dicts
in place (every module that did `from motifs2 import HEX` sees them) without editing engine/ (see ENGINE_NOTES.md)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
import motifs, motifs2, tech, sheet

# ---------------------------------------------------------------- thread palette (12 threads, PROPOSED from the mockup)
GL_PAL = {   # key: (hex, name, use)
    "gl_cream":  ("#EDE2CB", "Cloud cream",   "cloud lobes (lower bank), islets, star centres"),
    "gl_sand":   ("#C9BB9C", "Cloud sand",    "cream-lobe shadows, islet bases"),
    "gl_sagelt": ("#B9BFA0", "Sage light",    "upper-lobe rims"),
    "gl_sage":   ("#87917A", "Sage",          "upper cloud lobes"),
    "gl_slate":  ("#627779", "Slate grey-teal",    "middle cloud lobes"),
    "gl_shadow": ("#4B575E", "Cloud shadow",  "lobe bases, deep cloud gaps"),
    "gl_deep":   ("#1F4A50", "Sea deep",      "sea bars (dark), sky-glow arcs"),
    "gl_teal":   ("#2E6B6C", "Sea teal",      "sea bars (main)"),
    "gl_tealt":  ("#4E9590", "Sea light",     "sea bars (light), near the horizon"),
    "gl_foam":   ("#A9C9B8", "Sea foam",      "highlight bars, horizon line"),
    "gl_gold":   ("#E3C890", "Star gold-cream",     "ray lines, star arms, sunburst"),
    "gl_pale":   ("#F7EDD2", "Sun pale",      "sun core, glitter path, star sparkle"),
}
GL_KEYS = list(GL_PAL)      # Rev D: 12 threads (cloud shadow is back as the lobe shadow band traced from the close-ups)
FABRIC = "#252B3B"          # washed navy duck (mockup sample)
for k, v in GL_PAL.items():
    motifs2.PAL[k] = v; motifs2.HEX[k] = v[0]; motifs.HEX[k] = v[0]

# stop order inside a layer (back -> front within the layer)
GL_ORDER = ["gl_deep", "gl_teal", "gl_tealt", "gl_foam", "gl_shadow", "gl_slate", "gl_sage", "gl_sagelt",
            "gl_sand", "gl_cream", "gl_gold", "gl_pale"]
tech.COLOUR_ORDER = GL_ORDER + [c for c in tech.COLOUR_ORDER if c not in GL_ORDER]

# ---------------------------------------------------------------- region codes
# code -> (name, stitch, angle rule, density, stitch length, underlay, pull comp, notes)
GL_RULES = {
 "GLW":      ("Sky-glow radial lines",    "Run (double)",       "radial from the sun",    "—",    "2.6", "none",                    "—",    "sewn over the glow fill"),
 "GLW-fill": ("Sky-glow fill",            "Tatami, radial",     "radial from the sun",    "0.45", "3.5", "edge run",                "0.20", "dark teal halo behind the sun"),
 "SEA":      ("Sea bar",                  "Tatami, horizontal", "0° (along bar)",         "0.45", "3.5", "edge run",                "0.15", "bars 1.6–2.2 high, gaps ≥ 0.6"),
 "SEA-hl":   ("Sea highlight bar",        "Tatami, horizontal", "0° (along bar)",         "0.45", "3.5", "edge run",                "0.15", "foam / pale"),
 "HZ":       ("Horizon line",             "Bean (triple run)",  "follows line",           "—",    "2.2", "none",                    "—",    "0.8 line"),
 "GLT":      ("Sun glitter bar",          "Tatami, horizontal", "0° (along bar)",         "0.45", "3.5", "edge run",                "0.15", "column under the sun"),
 "RAY":      ("Dashed hairline sun ray",  "Run (double)",       "follows the ray",        "—",    "2.0", "none",                    "—",    "dash 4.2 / gap 2.4, slight curve"),
 "SUN":      ("Sun core",                 "Satin, radial",      "radial from sun centre", "0.40", "—",   "centre run",              "0.15", "Ø 9"),
 "SUN-ring": ("Sun ring",                 "Satin, radial",      "radial from sun centre", "0.40", "—",   "edge run",                "0.15", ""),
 "BURST":    ("Sunburst ray",             "Satin, tapered",     "across ray",             "0.42", "—",   "centre run",              "0.15", "≥ 0.9 wide, blunt tip"),
 "CL":       ("Cloud lobe body",          "Satin, turning",     "across lobe",            "0.42", "≤7",  "edge run + centre run",   "0.20", "split satin > 7"),
 "CL-rim":   ("Cloud lobe rim (light)",   "Satin, turning",     "across rim",             "0.42", "—",   "centre run",              "0.20", "sewn first in the bank"),
 "CL-shade": ("Cloud lobe shade band",    "Satin, turning",     "across band",            "0.42", "—",   "centre run",              "0.20", ""),
 "CL-edge":  ("Cloud lobe edge (dark)",   "Satin, turning",     "across band",            "0.42", "—",   "none",                    "0.15", "1.15 wide, joins into one network"),
 "ISL-rim":  ("Islet lobe rim (light)",   "Satin",              "across rim",             "0.42", "—",   "none",                    "0.15", ""),
 "ISL-shade":("Islet shade band",         "Satin",              "across band",            "0.42", "—",   "none",                    "0.15", ""),
 "ISL-edge": ("Islet edge (dark)",        "Satin",              "across band",            "0.42", "—",   "none",                    "0.15", ""),
 "GLT-line": ("Glitter centre line",      "Run (double)",       "vertical",               "—",    "2.0", "none",                    "—",    "hairline over the glitter"),
 "SEA-field":("Sea ground (dark teal)",   "Tatami, horizontal", "0°",                     "0.45", "3.5", "edge run + 90° lattice",  "0.20", "between the dashes, upper sea"),
 "CL-scale": ("Cloud scale dashes",       "Run (double)",       "follows the lobe dome",  "—",    "2.0", "none",                    "—",    "2.6 dash / 1.7 gap, on top"),
 "ISL-scale":("Islet scale dashes",       "Run (double)",       "follows the lobe dome",  "—",    "2.0", "none",                    "—",    "on top"),
 "ISL":      ("Islet cloud lobe",         "Satin, radial",      "radial from lobe base",  "0.42", "—",   "centre run",              "0.20", ""),
 "STAR":     ("Star / sparkle arm",       "Satin",              "across arm",             "0.40", "—",   "centre run",              "0.15", "≥ 0.9 wide, blunt tip"),
 "STAR-c":   ("Star centre",              "Satin dot",          "across dot",             "0.40", "—",   "none",                    "0.10", "Ø ≥ 1.4"),
 "DOT":      ("Star dot",                 "Satin dot",          "across dot",             "0.40", "—",   "none",                    "0.10", "Ø 1.4–2.2"),
}
tech.RULES.update(GL_RULES)
tech.LAYER_NAMES.update({11: "Sky glow", 12: "Sea", 13: "Horizon + glitter", 14: "Rays", 15: "Sun + sunburst",
                         16: "Cloud banks", 17: "Cloud islets", 18: "Stars"})
tech.LAYER_NAMES.update({12.05: "Sun glitter", 12.1: "Sea foam dashes", 12.2: "Sea light dashes", 12.3: "Sea teal dashes", 12.4: "Sea field",
                         16.1: "Cloud rims", 16.2: "Cloud bodies", 16.3: "Cloud shade", 16.4: "Cloud edges",
                         17.1: "Islet rims", 17.2: "Islet bodies", 17.3: "Islet shade", 17.4: "Islet edges"})

# sheet font: Noto Sans CJK JP is not installed on this box -> Liberation Sans (Arial metrics)
sheet.FONT = "Liberation Sans"

def patch_dst2():
    """call after `import dst2`: pull-comp + blends for this project's codes"""
    import dst2
    for k, v in GL_RULES.items():
        dst2.PULL[k] = float(v[6]) if v[6] not in ("—", "") else 0.0
    dst2.COL_MERGE.clear()          # 12 threads: nothing to merge
    dst2.TRIM_MIN = 2.0             # review C2: an exposed move > 2 mm is trimmed, never left as a float
    return dst2

STYLE = "HK-JK-GRLN-NV"
NAME = "Grand Line Jacket — Washed Navy"
ELEM = "01"; ELEM_SLUG = "front-scene"; ELEM_TITLE = "FRONT SCENE — sunrise over a sea of clouds"
PIECES = ("FR", "FL")       # FR = wearer's right front (x < 0), FL = wearer's left front (x > 0)
PIECE_NAME = {"FR": "wearer's right front", "FL": "wearer's left front"}
PIECE_CODE = {"FR": "F02", "FL": "F01"}        # pattern piece codes (pattern.py)
SIZES = ["XS", "S", "M", "L", "XL", "XXL", "3XL"]
GRADE = {"XS": ("A", 0.92), "S": ("A", 0.92), "M": ("B", 1.0), "L": ("B", 1.0), "XL": ("B", 1.0), "XXL": ("C", 1.08), "3XL": ("C", 1.08)}
REV_EMB = "Rev E"; REV_GAR = "Rev E"; DATE = "18 Oct 2026"
