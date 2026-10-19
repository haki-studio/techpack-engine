"""Forestball project core — import FIRST in every script (before specbase / dst2 / tech readers).
Swaps the engine's plum + pine thread palette for the Forestball palette (in place, so every module that did
`from motifs2 import HEX, PAL` sees it), adds the forest region codes to the digitizing rules, and relabels the
Drum Island pattern materials (black corduroy collar, black rib). Nothing in engine/ is edited."""
import motifs2, tech

STYLE = "HK-JK-DRUM-FB"; NAME = "Forestball Jacket"; SLUG = "forestball"
REV_EMB = "Rev C"; REV_GAR = "Rev C"; DATE = "19 Oct 2026"
FABRIC = "#3A463C"                     # washed forest green (mockup median #38433A..#3D483F)

# ---------------------------------------------------------------- thread palette (13 threads + basting, 40wt polyester) — PROPOSED, read from the mockup
PAL = {
    "navy":    ("#18222E", "Navy black",     "bark crevices, outlines, twigs, rock shadow"),
    "royal":   ("#1E4F8A", "Chain blue",     "braided chain bark + moss ropes (close-up b: royal/teal blue)"),
    "brown":   ("#4E3B2A", "Twig brown",     "twigs (chain stitch), leaf veins"),
    "bark":    ("#2D4862", "Bark blue",      "bark body + chain underside, rock body, stream"),
    "mossdk":  ("#183A33", "Moss dark teal", "moss shade + teal strands of the chain bark / rope roots (close-up a), grass shade"),
    "moss":    ("#55672C", "Moss",           "raised moss on limbs + rocks + strands"),
    "mosslt":  ("#8E9C44", "Moss light",     "moss tops + mottling, leaf shade half, grass light"),
    "leaf":    ("#C6C872", "Leaf yellow-green","leaf light half, moss highlights"),
    "grass":   ("#4F7B3B", "Grass green",    "grass blades, moss mottling (4th moss green)"),
    "sage":    ("#A1A88F", "Sage",           "light rays (sheer run)"),
    "cream":   ("#DAD5B3", "Cream",          "light rays core, water glints, moss-strand twist"),
    "waterlt": ("#7491B0", "Stream light",   "ripples, rock rims, bark ridges, placeholder outline + registration crosses"),
}
motifs2.PAL.clear(); motifs2.PAL.update(PAL)
motifs2.HEX.clear(); motifs2.HEX.update({k: v[0] for k, v in PAL.items()})
motifs2.FABRIC = FABRIC
tech.COLOUR_ORDER[:] = ["waterlt", "sage", "cream", "bark", "navy", "royal", "brown", "mossdk", "moss", "grass", "mosslt", "leaf"]
# Rev B thread merges: only pairs that are the same colour in the mockup (and matched the same catalogue thread).
# Moss vs grass green stay separate (visibly different greens; fidelity first, founder 16 Oct).
MERGE = {"leafdk": "mosslt", "water": "bark",
         # factory limit 12 colours per file incl. basting/registration (16 Oct): the two light blues are one thread,
         # and the placeholder outline + registration crosses sew in Stream light (a colour every file already uses)
         "barklt": "waterlt", "basting": "waterlt"}
def col(c): return MERGE.get(c, c)
tech.LAYER_NAMES.clear()
tech.LAYER_NAMES.update({0: "Placeholder outline", 1: "Light rays (sewn first, under the art)", 2: "Stream + rocks", 4.5: "Leaves", 5: "Bark + twigs", 6: "Moss",
                         7: "Leaves", 8: "Grass", 10: "Hanging moss", 11: "Light rays (on top)"})
STITCH_LAYER = {99: 99}                # truthy map: bark line work sews after the moss (tech.stops 6.5 rule)

# ---------------------------------------------------------------- forest region codes (name, stitch, angle, density, length, underlay, pull, notes)
tech.RULES.update({
 "LR":        ("Light ray (sheer)",          "Run, serpentine", "along the ray",          "2.6 rows", "2.6", "none",                       "—",    "≈ 15 % cover; sewn LAST, over the art"),
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
 "CH":        ("Chain link (braided bark)",  "Satin",   "along the link (±36°)",                "0.42",   "—",    "none",                       "0.15", "chain-stitch look: rows of links"),
 "LF-vein":   ("Leaf centre vein",           "Run (single)", "along the midrib",           "—",      "1.8",  "none",                       "—",    "on top of the leaf"),
 "BUD":       ("Twig-tip bud",               "Satin",   "along bud",                      "0.42",   "—",    "none",                       "0.10", "navy, at spray tips"),
 "TW-node":   ("Twig node",                  "Satin dot", "across",                       "0.42",   "—",    "none",                       "0.10", "cream nodes on the brown twig"),
 "LF":        ("Leaf, light half",           "Satin",   "midrib + 45° (feather)",         "0.42",   "—",    "centre run",                 "0.20", ""),
 "LF-dark":   ("Leaf, shade half",           "Satin",   "midrib − 45° (feather)",         "0.42",   "—",    "centre run",                 "0.20", ""),
 "PH":        ("LICENSED FIGURE placeholder",  "Run (single)", "box outline",              "—",      "3.0",  "none",                       "—",    "Stream-light thread; nothing inside"),
 "LP":        ("Lily pad",                   "Satin, turning", "radial from pad centre",  "0.40",   "—",    "edge run + centre run",      "0.20", "split satin if > 7"),
 "LP-vein":   ("Lily pad veins",             "Run (single)", "radial lines",              "—",      "2.0",  "none",                       "—",    ""),
 "BU":        ("Water-lily bud petal",       "Satin",   "along petal",                    "0.40",   "—",    "centre run",                 "0.20", "original motif"),
 "BU-tip":    ("Bud petal tip light",        "Satin",   "along petal",                    "0.40",   "—",    "none",                       "0.15", "blend 1 row"),
 "RI":        ("Ripple rings",               "Run (single)", "follows line",              "—",      "2.4",  "none",                       "—",    ""),
 "HM":        ("Hanging moss rope body",     "Tatami",  "along the rope (map)",           "0.45",   "3.5",  "edge run + tatami 90° @ 2.0","0.25", "hangs from the limb"),
 "HM-light":  ("Rope strands + chain edge",  "Bean (triple run)", "follows the rope",        "—",      "2.0",  "none",                       "—",    "twisted strands + yellow-green chain edge"),
})

import dst2   # engine reads pull comp from tech.RULES at call time (dst2.pull_for)
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

def stitch_stops(vis):
    """colour stops exactly as the stitch files sew them (build_dst.py): leaves before the twigs, then tech.stops +
    dst2.merge_stops. Specs use this so their stop tables match the DST."""
    for r in vis:                        # in place: production_svg keys regions by identity
        if r["grp"] in ("LF", "LF-dark"): r["layer"] = 4.5
    return dst2.merge_stops(tech.stops(vis, STITCH_LAYER))

# reused Drum Island codes: print the production densities the engine actually sews (dst2 v3 knobs, LESSONS B4)
for _k in ("TR", "LM", "-shade", "-ridge", "TW", "TR-knot"):
    _v = list(tech.RULES[_k])
    _v[3] = {"Tatami": "0.45", "Satin": "0.42"}.get(_v[1], _v[3])
    tech.RULES[_k] = tuple(_v)

# ---------------------------------------------------------------- Rev C thread matching (review item 8)
# 1) The Ink/Stitch Polyneon palette has names that contradict their RGB (1940 "Fluo Orange" = yellow-green, 1766 "Violet
#    Blue" = olive, 1812 "Vapor Blue" = grey, 1863 "Cocoa Mulch" = cream): entries whose name names a hue far from their
#    RGB hue are dropped (untrusted), so no pick rests on them. 2) Every palette thread gets its OWN catalogue code per
#    brand (Moss and Grass green both took Isacord 5944): conflicts go to the next-best match.
import colorsys
_FAM = {"red": (340, 18), "orange": (12, 48), "gold": (35, 60), "yellow": (42, 72), "lime": (60, 110), "green": (65, 170),
        "teal": (150, 205), "aqua": (160, 210), "turquoise": (150, 205), "blue": (180, 255), "navy": (190, 255),
        "violet": (245, 300), "purple": (250, 305), "lilac": (245, 300), "lavender": (230, 290), "pink": (295, 350), "rose": (310, 360)}
def _trusted(name, rgb):
    r, g, b = [c / 255 for c in rgb]; h, l, s = colorsys.rgb_to_hls(r, g, b); n = name.lower(); hd = h * 360
    if any(w in n for w in ("brown", "cocoa", "chocolate", "coffee", "mocha")) and l > 0.55: return False
    words = [w for w in _FAM if w in n]
    if not words: return True
    if s < 0.18 or l < 0.10: return l <= 0.25                     # a named hue on a grey swatch: untrusted
    def inside(rng):
        a0, a1 = rng
        return (a0 - 10 <= hd <= a1 + 10) if a0 < a1 else (hd >= a0 - 10 or hd <= a1 + 10)
    return any(inside(_FAM[w]) for w in words)
for _br in ("polyneon", "isacord"):
    tech.TH[_br] = [t for t in tech.TH[_br] if _trusted(t[1], t[2])]
def _unique_table(keys):
    out = {k: {} for k in keys}
    for br in ("isacord", "polyneon"):
        cand = {}
        for k in keys:
            rgb = tuple(int(HEX[k][i:i+2], 16) for i in (1, 3, 5)); L = tech._lab(rgb)
            cand[k] = sorted((tech.de2000(L, tech._lab(tuple(t[2]))), t[0], t[1], "#%02X%02X%02X" % tuple(t[2])) for t in tech.TH[br])
        used = set()
        for k in sorted(keys, key=lambda k_: cand[k_][0][0]):
            d, code, name, hx = next(c for c in cand[k] if c[1] not in used); used.add(code)
            out[k][br] = (code, name, hx, d)
    return out
HEX = {k: v[0] for k, v in PAL.items()}
SB.TH.clear(); SB.TH.update(_unique_table(list(PAL)))

# ---------------------------------------------------------------- Rev C traced region codes (trace_fb.py)
tech.RULES.update({
 "TB":  ("Traced bark / chain strands",       "Tatami",  "close-up strand direction (8 mm cells)", "0.45", "3.5", "edge run + tatami 90° @ 2.0", "0.25", "navy crevices traced"),
 "TBS": ("Traced bark strand (narrow)",       "Satin",   "across the strand",          "0.42", "—",   "centre run if > 2",           "0.20", "< 3.2 mm wide"),
 "TM":  ("Traced moss / grass",               "Tatami",  "close-up strand direction",  "0.45", "3.5", "edge run + tatami 90° @ 2.0", "0.25", "4 greens, traced tones"),
 "TMS": ("Traced moss / grass (narrow)",      "Satin",   "across the shape",           "0.42", "—",   "centre run if > 2",           "0.20", "grass blades, chain loops"),
 "TT":  ("Traced twig",                       "Tatami",  "along the twig",             "0.45", "3.5", "edge run",                    "0.20", ""),
 "TTS": ("Traced twig (narrow)",              "Satin",   "across the twig",            "0.42", "—",   "centre run if > 2",           "0.15", "brown chain twigs"),
 "TL":  ("Traced leaf",                       "Tatami",  "along the leaf",             "0.45", "3.5", "edge run",                    "0.20", "sews before the twigs"),
 "TLS": ("Traced leaf (narrow)",              "Satin",   "across the leaf",            "0.42", "—",   "centre run",                  "0.20", "two-tone halves traced"),
 "TH":  ("Traced highlight",                  "Tatami",  "close-up direction",         "0.45", "3.5", "edge run",                    "0.20", "cream / light-blue specks"),
 "THS": ("Traced highlight (narrow)",         "Satin",   "across",                     "0.42", "—",   "none",                        "0.10", "cream specks, rapids"),
 "WAS": ("Stream detail (narrow)",            "Satin",   "across",                     "0.42", "—",   "none",                        "0.15", "rapids, ledges, glints"),
 "LR":  ("Light ray (sheer)",                 "Run, serpentine", "along the ray",      "1.8 core / 2.8 edge rows", "2.6", "none",  "—",    "≈ 25-30 % cover; cream core, sage edges; sewn FIRST, under the art"),
 "RI":  ("Ripple rings (pool)",               "Run (single)", "follows the ring",      "—",    "2.4", "none",                        "—",    "round the licensed placeholder"),
})
for _k in ("TB", "TBS", "TM", "TMS", "TT", "TTS", "TL", "TLS", "TH", "THS", "WAS"):
    pass
tech.COLOUR_ORDER[:] = [c for c in tech.COLOUR_ORDER if c in PAL]
