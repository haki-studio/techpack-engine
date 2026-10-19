"""Wave jacket — project core. Import this FIRST in every script of this project (before dst2 / specbase).

The engine's palette, region rules and colour-stop order are hard-wired for the plum + pine jacket (motifs2.PAL,
tech.RULES, tech.COLOUR_ORDER). This module adds this jacket's thread palette + region codes to those shared dicts in
place (every module that did `from motifs2 import HEX` sees them) without editing engine/ (ROADMAP: project palette)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
import motifs, motifs2, tech, sheet

# ---------------------------------------------------------------- thread palette (9 threads, read off the render by k-means — PROPOSED)
WV_PAL = {   # key: (hex, name, use)
    "w1": ("#F0EDEA", "Foam white",   "foam crests + curls (raised), rope lines, spray drops"),
    "w3": ("#C2BDBA", "Foam shade",   "curl undersides, curl lines + loop texture on the foam"),
    "g1": ("#A09FA0", "Curl grey",    "curl hollows / shadow inside the crests"),
    "b0": ("#B1C7D8", "Pale blue",    "palest wave stripes, drop undersides"),
    "b1": ("#80AED0", "Sky blue",     "light wave stripes"),
    "b2": ("#528DBE", "Mid blue",     "mid wave stripes"),
    "b3": ("#1F65A8", "Cobalt",       "wave stripes"),
    "b4": ("#054299", "Royal blue",   "wave stripes (main)"),
    "b5": ("#032870", "Ultramarine",  "deepest wave stripes"),
}
WV_KEYS = list(WV_PAL)
FABRIC = "#272F43"          # washed navy duck (render sample) — PROPOSED, lab dip
for k, v in WV_PAL.items():
    motifs2.PAL[k] = v; motifs2.HEX[k] = v[0]; motifs.HEX[k] = v[0]
# stop order inside a layer (first sewn first)
WV_ORDER = ["b0", "b1", "b2", "b3", "b4", "b5", "g1", "w3", "w1"]
tech.COLOUR_ORDER = WV_ORDER + [c for c in tech.COLOUR_ORDER if c not in WV_ORDER]

# ---------------------------------------------------------------- region codes
# code -> (name, stitch, angle rule, density, stitch length, underlay, pull comp, notes)
WV_RULES = {
 "RP":      ("Rope line (cream)",            "Satin, turning",      "across the line",          "0.42", "—",   "centre run",                  "0.20", "rope lines between the wave stripes"),
 "WV":      ("Wave stripe",                  "Satin, turning / tatami along", "along the stripe (map)", "0.42 / 0.45", "3.5", "centre run (satin) · edge run + 90° lattice (tatami > 60 mm²)", "0.25", "tatami along the stripe; turning satin only on stripes < 3 wide with no holes (DST coverage ≥ 99 %)"),
 "FM":      ("Foam crest / curl (raised)",   "Padded tatami",       "auto (long axis)",         "0.45", "5.0", "1 padding layer @ 90° + edge run", "0.30", "raised; chenille look from FM-loop on top [proposed — ask chenille]"),
 "FM-sh":   ("Foam shade",                   "Satin / tatami",      "auto",                     "0.42", "3.5", "centre run",                  "0.20", "sewn before the foam (B2)"),
 "FM-gr":   ("Curl hollow (grey)",           "Satin / tatami",      "auto",                     "0.42", "3.5", "centre run",                  "0.20", "sewn before the foam (B2)"),
 "FM-in":   ("Blue inside the curl",         "Satin / tatami",      "auto",                     "0.42", "3.5", "centre run",                  "0.20", "sewn before the foam (B2)"),
 "FM-loop": ("Foam loop texture",            "Run (single)",        "scalloped contour spiral", "—",    "2.6", "none",                        "—",    "sewn ON the padded foam in Foam shade: bouclé / chenille look"),
 "FM-curl": ("Curl separation + C-curl",     "Bean (triple run)",   "follows line",             "—",    "2.0", "none",                        "—",    "0.7 line in Foam shade, on top of the foam"),
 "DR":      ("Spray drop (white)",           "Satin",               "across the drop",          "0.40", "—",   "none / centre run > 2",       "0.15", "Ø ≥ 1.2"),
 "DR-b":    ("Drop underside (blue)",        "Satin",               "across",                   "0.40", "—",   "none",                        "0.15", ""),
}
tech.RULES.update(WV_RULES)
L_ROPE, L_BAND, L_FDET, L_FOAM, L_LOOP, L_DROPB, L_DROP = 10, 11, 12, 13, 14, 15, 16
tech.LAYER_NAMES.update({L_ROPE: "Rope lines", L_BAND: "Wave stripes", L_FDET: "Foam details (shade, hollows, inner blue)",
                         L_FOAM: "Foam crests (raised)", L_LOOP: "Foam loop texture", L_DROPB: "Drop undersides", L_DROP: "Spray drops"})

sheet.FONT = "Liberation Sans"     # Noto Sans CJK is not installed on this box

def patch_dst2():
    """call after `import dst2`: pull comp + angle sets for this project's codes; nothing to merge (9 threads)"""
    import dst2
    for k, v in WV_RULES.items():
        dst2.PULL[k] = float(v[6]) if v[6] not in ("—", "") else 0.0
    dst2.ALONG.add("WV")
    dst2.COL_MERGE.clear()
    dst2.TRIM_MIN = 2.0             # an exposed move > 2 mm is trimmed, never left as a float
    return dst2

STYLE = "HK-JK-WAVE-NV"
NAME = "Wave Jacket — Washed Navy"
ELEM = "01"; ELEM_SLUG = "wave"; ELEM_TITLE = "WAVE — Hokusai-style wave + raised foam curls (back, fronts, sleeves)"
PIECES = ("BK", "FR", "FL", "SR", "SL")
PIECE_NAME = {"BK": "back", "FR": "wearer's right front", "FL": "wearer's left front", "SR": "right sleeve", "SL": "left sleeve"}
PIECE_CODE = {"BK": "B01", "FR": "F02", "FL": "F01", "SR": "S01", "SL": "S02"}
SIZES = ["XS", "S", "M", "L", "XL", "XXL", "3XL"]
GRADE = {"XS": ("A", 0.92), "S": ("A", 0.92), "M": ("B", 1.0), "L": ("B", 1.0), "XL": ("B", 1.0), "XXL": ("C", 1.08), "3XL": ("C", 1.08)}
REV_EMB = "Rev A"; REV_GAR = "Rev A"; DATE = "19 Oct 2026"
