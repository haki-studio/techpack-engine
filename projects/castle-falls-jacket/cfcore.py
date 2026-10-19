"""Castle Falls jacket — project core. Import this FIRST in every script of this project.

Adds this jacket's thread palette + region codes to the engine's shared dicts in place (motifs2.PAL/HEX,
tech.RULES/COLOUR_ORDER/LAYER_NAMES), like grand-line-jacket/glcore.py (engine/ is not edited; ENGINE_NOTES.md).

Global palette = 18 threads (one thread board for the jacket); every stitch file uses <= 12 of them
(factory.json: max 12 distinct colours per file, basting included). PIECE_MERGE says which tones each piece
sews in a neighbouring thread to stay at 12 (closest ΔE2000, smallest areas)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
import motifs, motifs2, tech, sheet

# ---------------------------------------------------------------- thread palette (PROPOSED, read from the mockup)
CF_PAL = {   # key: (hex, name, use)
    "cf_white": ("#EEEAE0", "Cloud white",     "cloud lit tops, waterfall highlights, castle walls"),
    "cf_cream": ("#D4CABA", "Cloud cream",     "cloud bodies, foam, plaster"),
    "cf_mist":  ("#9EA3A6", "Mist grey",       "cloud undersides, mist, light rock"),
    "cf_skylt": ("#79A4D0", "Sky light",       "sky near the horizon, waterfall blue streaks"),
    "cf_sky":   ("#3F6FA9", "Sky blue",        "sky, roof highlights, water"),
    "cf_navy":  ("#22355C", "Deep navy",       "roofs, deep sky, windows, outlines"),
    "cf_slate": ("#566577", "Rock slate",      "cliff faces, distant ridges"),
    "cf_lav":   ("#9690B6", "Far lavender",    "distant mountains, haze"),
    "cf_grndk": ("#2F402D", "Pine dark",       "foliage shadow, moss shadow"),
    "cf_grn":   ("#5A7240", "Leaf green",      "foliage body, moss"),
    "cf_grnlt": ("#9DA65F", "Moss light",      "foliage tops, moss highlights"),
    "cf_pinklt":("#F2C3CE", "Blossom pale",    "blossom florets, petals"),
    "cf_pink":  ("#DE8EA6", "Blossom pink",    "blossom florets, petals"),
    "cf_rose":  ("#B4506F", "Blossom deep",    "blossom shade, floret centres"),
    "cf_red":   ("#B23F2E", "Vermilion",       "bridge, pagoda, gate, timber"),
    "cf_gold":  ("#D3A63F", "Gold",            "castle trims, roof ornaments, lanterns"),
    "cf_bark":  ("#958262", "Bark tan",        "pine trunk, cherry trunks"),
    "cf_brown": ("#4E3F31", "Bark dark",       "bark crevices, trunk shade"),
}
CF_KEYS = list(CF_PAL)
FABRIC = "#2E3847"          # washed navy duck (mockup sample)
for k, v in CF_PAL.items():
    motifs2.PAL[k] = v; motifs2.HEX[k] = v[0]; motifs.HEX[k] = v[0]

# stop order: far -> near, light details before the fill that hides their travel (LESSONS B2/B14)
CF_ORDER = ["cf_lav", "cf_skylt", "cf_sky", "cf_navy", "cf_slate", "cf_mist", "cf_cream", "cf_white",
            "cf_brown", "cf_bark", "cf_grndk", "cf_grn", "cf_grnlt", "cf_red", "cf_gold",
            "cf_rose", "cf_pink", "cf_pinklt"]
tech.COLOUR_ORDER = CF_ORDER + [c for c in tech.COLOUR_ORDER if c not in CF_ORDER]

# ---------------------------------------------------------------- region codes
# code -> (name, stitch, angle rule, density, stitch length, underlay, pull comp, notes)
CF_RULES = {
 "SKY":      ("Sky field",                 "Tatami",             "≈ 0° (horizontal, ±8°)",   "0.42", "3.5", "edge run + 90° lattice",  "0.20", "2–3 blues, ragged top"),
 "MT":       ("Distant mountain",          "Tatami",             "along the slope",          "0.42", "3.5", "edge run",                "0.20", "lavender / slate"),
 "RK":       ("Rock / cliff face",         "Tatami",             "≈ 90° (strata), ±16°",     "0.42", "3.5", "edge run + 90° lattice",  "0.20", "traced slate tones"),
 "RK-line":  ("Rock crevice",              "Bean (triple run)",  "follows line",             "—",    "2.0", "none",                    "—",    "0.8 line on top"),
 "FALL":     ("Waterfall stream",          "Tatami, vertical",   "90° (with the fall)",      "0.40", "4.5", "edge run",                "0.15", "white / light-blue streaks"),
 "FALL-foam":("Waterfall foam",            "Satin, turning",     "across lobe",              "0.42", "—",   "centre run",              "0.20", "small lobes at the foot"),
 "WTR":      ("River / pool",              "Tatami",             "0°",                       "0.42", "3.5", "edge run",                "0.15", "horizontal dashes"),
 "CL":       ("Cloud tone area",           "Tatami",             "per area, ±28°",           "0.42", "3.5", "edge run",                "0.20", "traced: white / cream / mist"),
 "CL-rim":   ("Cloud lobe rim (lit)",      "Tatami, per lobe",   "per lobe",                 "0.42", "3.5", "edge run",                "0.20", "top of each dome"),
 "CL-shade": ("Cloud lobe shade",          "Tatami, per lobe",   "per lobe",                 "0.42", "3.5", "edge run",                "0.20", "base of each dome"),
 "FOL":      ("Foliage tone area",         "Tatami (satin < 2 wide)", "per area, 0–180°",    "0.42", "3.5", "edge run",                "0.20", "traced: 3 greens"),
 "FOL-rim":  ("Foliage clump light top",   "Satin / tatami",     "per clump",                "0.42", "≤7",  "none",                    "0.15", ""),
 "FOL-shade":("Foliage clump shade",       "Satin / tatami",     "per clump",                "0.42", "≤7",  "none",                    "0.15", ""),
 "FOL-base": ("Foliage ground (dark)",     "Tatami",             "≈ 90°",                    "0.45", "3.5", "edge run",                "0.20", "under the clumps, no fabric gaps"),
 "BLB":      ("Blossom ground",            "Tatami",             "per area, 0–180°",         "0.45", "3.5", "edge run",                "0.20", "traced 3 pinks, florets on top"),
 "BL":       ("Blossom floret",            "Satin, radial",      "radial from floret centre","0.40", "—",   "none",                    "0.15", "5 notched petals Ø 3.6–6.4"),
 "BL-c":     ("Floret centre",             "Satin dot",          "across dot",               "0.40", "—",   "none",                    "0.10", "Ø 1.2"),
 "PT":       ("Falling petal",             "Satin",              "across petal",             "0.40", "—",   "none",                    "0.15", "3.2–5.6 long"),
 "TRK":      ("Trunk / bark tone area",    "Tatami",             "40–140° per area",         "0.42", "3.5", "edge run + 90° lattice",  "0.25", "traced tan + dark"),
 "TRK-line": ("Bark line",                 "Bean (triple run)",  "follows line",             "—",    "2.0", "none",                    "—",    "0.8 line on top"),
 "TWG":      ("Cherry branch",             "Satin, turning",     "across branch",            "0.40", "—",   "centre run",              "0.20", "≥ 1.6 wide"),
 "ROOF":     ("Roof",                      "Satin / tatami",     "down the roof slope",      "0.40", "≤7",  "edge run",                "0.20", "navy + sky ridge lines"),
 "ROOF-ln":  ("Roof ridge / tile line",    "Satin",              "across line",              "0.40", "—",   "none",                    "0.15", "≥ 0.9 wide"),
 "WALL":     ("Wall / plaster",            "Tatami",             "0°",                       "0.42", "3.5", "edge run",                "0.20", ""),
 "WIN":      ("Window / opening",          "Satin",              "auto",                     "0.40", "—",   "none",                    "0.15", "≥ 1.0"),
 "TMB":      ("Timber / rail / post",      "Satin",              "across member",            "0.40", "—",   "centre run",              "0.20", "≥ 1.0 wide"),
 "ORN":      ("Gold ornament / trim",      "Satin",              "across",                   "0.40", "—",   "none",                    "0.15", "≥ 0.9 wide"),
 "DOT":      ("Lantern / stud dot",        "Satin dot",          "across dot",               "0.40", "—",   "none",                    "0.10", "Ø 1.2–2.0"),
 "VIL":      ("Buildings (traced)",        "Tatami / satin",     "auto (across short axis)", "0.42", "3.5", "edge run",                "0.20", "red / gold tones traced"),
 "STONE":    ("Castle stone base",         "Tatami",             "0°, block courses",        "0.42", "3.5", "edge run",                "0.20", "course lines on top"),
 "STONE-ln": ("Stone course line",         "Bean (triple run)",  "follows line",             "—",    "2.0", "none",                    "—",    ""),
 "TRACE":    ("Traced tone (other)",       "Tatami",             "auto",                     "0.42", "3.5", "edge run",                "0.20", "tonal trace"),
}
tech.RULES.update(CF_RULES)
tech.LAYER_NAMES.update({11: "Far mountains + sky", 12: "Clouds", 13: "Rock + cliffs", 14: "Waterfalls + water", 15: "Foliage",
                         16: "Trunks + branches", 17: "Blossom trees", 18: "Buildings", 19: "Bridge", 20: "Petals", 21: "Castle"})

sheet.FONT = "Liberation Sans"      # Noto Sans CJK JP is not installed on this box (ENGINE_NOTES)

# per piece: tone -> thread it is sewn in (keeps every file <= 12 distinct colours; closest ΔE, smallest areas)
PIECE_MERGE = {}        # filled by merge_plan() from the built art (see build_size.py)

def patch_dst2():
    """call after `import dst2`: pull-comp for this project's codes; no global colour merge (per piece instead)"""
    import dst2
    for k, v in CF_RULES.items():
        dst2.PULL[k] = float(v[6]) if v[6] not in ("—", "") else 0.0
    dst2.COL_MERGE.clear()
    return dst2

STYLE = "HK-JK-CSFL-NV"
NAME = "Castle Falls Jacket — Washed Navy"
SHORT = "CSFL"
REV_EMB = "Rev B"; REV_GAR = "Rev B"; DATE = "19 Oct 2026"
SIZES = ["XS", "S", "M", "L", "XL", "XXL", "3XL"]
GRADE = {"XS": ("A", 0.92), "S": ("A", 0.92), "M": ("B", 1.0), "L": ("B", 1.0), "XL": ("B", 1.0), "XXL": ("C", 1.08), "3XL": ("C", 1.08)}
# elements + pieces
ELEMS = {"01": ("back-scene", "BACK SCENE — waterfall mountains, cherry trees, village, clouds", ["BK"]),
         "02": ("front-scene", "FRONT SCENE — castle, falls, pine, pagoda, bridge, clouds (split at the zip)", ["FR", "FL"]),
         "03": ("sleeve-scene", "SLEEVE SCENES — mountains, cherry blossom, clouds", ["SR", "SL"])}
PIECES = ["BK", "FR", "FL", "SR", "SL"]
PIECE_ELEM = {"BK": "01", "FR": "02", "FL": "02", "SR": "03", "SL": "03"}
PIECE_NAME = {"BK": "back", "FR": "wearer's right front", "FL": "wearer's left front", "SR": "wearer's right sleeve", "SL": "wearer's left sleeve"}
PIECE_CODE = {"BK": "B01", "FR": "F02", "FL": "F01", "SR": "S01", "SL": "S02"}

def sewn_threads():
    """distinct thread colours actually sewn in ANY written file (all sizes, read back via make_current -> dst_all.json)"""
    import json as _j, os as _o
    if not _o.path.exists("dst_all.json"): return list(CF_KEYS)
    s = set()
    for d in _j.load(open("dst_all.json")).values():
        for v in d.values(): s |= set(c for c in v["full"]["colours"] if c)
    return [k for k in CF_KEYS if k in s]
def board_text():
    n = len(sewn_threads()); return f"{n}-thread board ({len(CF_KEYS)} traced tones)"
