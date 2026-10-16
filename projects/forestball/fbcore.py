"""Forestball project core — import FIRST in every script (before specbase / dst2 / tech readers).
Swaps the engine's plum + pine thread palette for the Forestball palette (in place, so every module that did
`from motifs2 import HEX, PAL` sees it), adds the forest region codes to the digitizing rules, and relabels the
Drum Island pattern materials (black corduroy collar, black rib). Nothing in engine/ is edited."""
import motifs2, tech

STYLE = "HK-JK-DRUM-FB"; NAME = "Forestball Jacket"; SLUG = "forestball"
REV_EMB = "Rev A"; REV_GAR = "Rev A"; DATE = "16 Oct 2026"
FABRIC = "#3A463C"                     # washed forest green (mockup median #38433A..#3D483F)

# ---------------------------------------------------------------- thread palette (13 threads + basting, 40wt polyester) — PROPOSED, read from the mockup
PAL = {
    "navy":    ("#18222E", "Navy black",     "bark crevices, outlines, twigs, rock shadow"),
    "bark":    ("#2D4862", "Bark blue",      "bark body, rock body"),
    "barklt":  ("#557696", "Bark blue light","bark ridges, rock rims, water mid"),
    "mossdk":  ("#3B4B26", "Moss dark",      "moss underside, lump contours, grass shade"),
    "moss":    ("#55672C", "Moss",           "raised moss on limbs + rocks"),
    "mosslt":  ("#8E9C44", "Moss light",     "moss tops, grass light, leaf shade on fronts"),
    "leaf":    ("#C6C872", "Leaf yellow-green","leaf light half"),
    "leafdk":  ("#8E9A42", "Leaf olive",     "leaf shade half"),
    "sage":    ("#A1A88F", "Sage",           "light rays (sheer run)"),
    "cream":   ("#DAD5B3", "Cream",          "light rays core, highlights, water sparkle"),
    "water":   ("#294A63", "Stream blue",    "stream body"),
    "waterlt": ("#7491B0", "Stream light",   "ripples, ripple rings"),
    "grass":   ("#4F7B3B", "Grass green",    "grass blades, lily pad"),
    "basting": ("#00A3FF", "Placement basting", "licensed-figure placeholder outline (water-soluble, removed)"),
}
motifs2.PAL.clear(); motifs2.PAL.update(PAL)
motifs2.HEX.clear(); motifs2.HEX.update({k: v[0] for k, v in PAL.items()})
motifs2.FABRIC = FABRIC
tech.COLOUR_ORDER[:] = ["basting", "sage", "cream", "water", "waterlt", "bark", "navy", "barklt", "mossdk", "moss", "mosslt",
                        "grass", "leafdk", "leaf"]
tech.LAYER_NAMES.clear()
tech.LAYER_NAMES.update({1: "Light rays", 2: "Stream", 3: "Grass behind", 4: "Rocks", 5: "Bark + twigs", 6: "Moss",
                         7: "Leaves", 8: "Grass front", 0: "Placeholder outline", 10: "Hanging moss"})
STITCH_LAYER = {99: 99}                # truthy map: bark line work sews after the moss (tech.stops 6.5 rule)

# ---------------------------------------------------------------- forest region codes (name, stitch, angle, density, length, underlay, pull, notes)
tech.RULES.update({
 "LR":        ("Light ray (sheer)",          "Run, serpentine", "along the ray",          "1.9 rows", "2.6", "none",                       "—",    "≈ 15 % cover; sews first"),
 "MS":        ("Moss on bark (raised)",      "Padded tatami", "across limb (map)",        "0.45",   "5.0",  "1 padding layer @ 90°",      "0.30", "random split, no rows"),
 "MS-shade":  ("Moss underside",             "Satin / split satin", "same as moss",       "0.42",   "≤7.0", "edge run",                   "0.25", ""),
 "MS-top":    ("Moss top light",             "Satin",   "across band",                    "0.42",   "—",    "centre run",                 "0.20", "blend 1 row into moss"),
 "MS-shadow": ("Moss cast shadow on bark",   "Satin",   "across band",                    "0.42",   "—",    "centre run",                 "0.15", ""),
 "MS-lump":   ("Moss lump contours",         "Run (single)", "follows line",              "—",      "2.0",  "none",                       "—",    "sewn on top of moss"),
 "RM":        ("Moss on rocks (raised)",     "Padded tatami", "vertical (90°)",           "0.45",   "5.0",  "1 padding layer @ 0°",       "0.30", "random split, no rows"),
 "RM-shade":  ("Rock moss underside",        "Satin / split satin", "vertical",           "0.42",   "≤7.0", "edge run",                   "0.25", ""),
 "RM-top":    ("Rock moss top light",        "Satin",   "vertical",                       "0.42",   "—",    "centre run",                 "0.20", "blend 1 row into moss"),
 "RM-lump":   ("Rock moss lump contours",    "Run (single)", "follows line",              "—",      "2.0",  "none",                       "—",    "sewn on top of moss"),
 "RK":        ("Rock body",                  "Tatami",  "fixed 20°",                      "0.45",   "3.5",  "edge run + tatami 90° @ 2.0","0.25", ""),
 "RK-shade":  ("Rock shadow",                "Tatami",  "fixed 20°",                      "0.45",   "3.0",  "edge run",                   "0.25", "blend into body"),
 "RK-rim":    ("Rock rim light",             "Satin",   "across rim",                     "0.42",   "—",    "centre run",                 "0.20", ""),
 "WA":        ("Stream body",                "Tatami",  "horizontal (0°)",                "0.45",   "3.5",  "edge run + tatami 90° @ 2.0","0.25", "long rows read as water"),
 "WA-deep":   ("Stream deep",                "Tatami",  "horizontal (0°)",                "0.45",   "3.5",  "edge run",                   "0.25", ""),
 "WA-ripple": ("Ripple bars",                "Satin",   "across bar",                     "0.42",   "—",    "none",                       "0.15", "≥ 0.9 wide"),
 "WA-glint":  ("Water glints",               "Satin dot", "across",                       "0.42",   "—",    "none",                       "0.10", "≥ 1.2 long"),
 "GR":        ("Grass blade",                "Satin, turning", "across blade",            "0.42",   "—",    "centre run if > 2",          "0.20", "blunt tips ≥ 0.9"),
 "GR-light":  ("Grass blade, light side",    "Satin, turning", "across blade",            "0.42",   "—",    "none",                       "0.15", ""),
 "LF":        ("Leaf, light half",           "Satin",   "midrib + 45° (feather)",         "0.42",   "—",    "centre run",                 "0.20", ""),
 "LF-dark":   ("Leaf, shade half",           "Satin",   "midrib − 45° (feather)",         "0.42",   "—",    "centre run",                 "0.20", ""),
 "PH":        ("LICENSED FIGURE placeholder",  "Run, basting", "box outline",              "—",      "3.0",  "none",                       "—",    "remove; nothing inside"),
 "LP":        ("Lily pad",                   "Satin, turning", "radial from pad centre",  "0.40",   "—",    "edge run + centre run",      "0.20", "split satin if > 7"),
 "LP-vein":   ("Lily pad veins",             "Run (single)", "radial lines",              "—",      "2.0",  "none",                       "—",    ""),
 "BU":        ("Water-lily bud petal",       "Satin",   "along petal",                    "0.40",   "—",    "centre run",                 "0.20", "original motif"),
 "BU-tip":    ("Bud petal tip light",        "Satin",   "along petal",                    "0.40",   "—",    "none",                       "0.15", "blend 1 row"),
 "RI":        ("Ripple rings",               "Run (single)", "follows line",              "—",      "2.4",  "none",                       "—",    ""),
 "HM":        ("Hanging moss strand",        "Satin, turning", "across strand",           "0.42",   "—",    "centre run if > 2",          "0.20", "hangs from the limb"),
 "HM-light":  ("Hanging moss highlight",     "Run (single)", "down the strand",           "—",      "2.0",  "none",                       "—",    "sewn on top of the strand"),
})

import dst2   # after the rules (dst2.PULL reads them at import)
dst2.PULL.update({k: (float(v[6]) if v[6] not in ("—", "") else 0.0) for k, v in tech.RULES.items()})
dst2.ALONG = set(dst2.ALONG) | {"GR", "GR-light", "HM"}
dst2.ACROSS = set(dst2.ACROSS) | {"MS", "MS-shade", "MS-shadow", "MS-top"}
dst2.BLEND = dict(dst2.BLEND, **{"MS": 2.0, "MS-top": 1.2, "RM": 2.0, "RM-top": 1.2, "RK-shade": 2.0, "BU-tip": 1.0})
dst2.COL_MERGE = {}                    # 14 threads: no merge needed (≤ 15 per file)

import specbase as SB                  # thread table for the new palette
SB.TH.clear(); SB.TH.update(tech.thread_table(list(PAL)))

# ---------------------------------------------------------------- Drum Island pattern, Forestball materials
import pattern as PT
_draft = PT.draft
MAT = {"Shell — 12 oz duck": "Shell — 12 oz duck, washed forest green", "Corduroy — 14 wale, dark brown": "Corduroy — 14 wale, black",
       "Rib knit 1×1 — tan": "Rib knit 1×1 — black", "Rib knit 1×1 — dark brown": "Rib knit 1×1 — black"}
def draft(size):
    g, mt = _draft(size)
    for pc in g.values():
        pc.material = MAT.get(pc.material, pc.material)
        if pc.code == "S01": pc.note = "plain sleeve (no embroidery)"
        if pc.code in ("F01", "F02"): pc.note = "welt pocket marked; embroidery 02 placement"
        if pc.code == "B01": pc.note = "CB marked by notches; embroidery 01 sewn on the cut piece"
    return g, mt
PT.draft = draft
