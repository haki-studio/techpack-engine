"""Keep Clean Our Space hooded jacket — project core. Import this FIRST in every script of this project.

Adds this jacket's thread palette, region codes, stop order and the puff-satin variant to the shared engine dicts in
place (motifs2.PAL/HEX, tech.RULES/COLOUR_ORDER/LAYER_NAMES), without editing engine/ (ENGINE_NOTES.md)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
import motifs, motifs2, tech, sheet

# ---------------------------------------------------------------- thread palette (7 threads, PROPOSED from the mockup)
KC_PAL = {   # key: (hex, name, use)
    "kc_mint":  ("#6FE3CC", "Neon mint",     "JP + EN text, mint spark bars, CN mint dots"),
    "kc_lemon": ("#F2E27E", "Lemon",         "CLEAN, lemon spark bars, oval inner highlight"),
    "kc_gold":  ("#F1C73C", "Star gold",     "EN star border, JP stars, KR oval ring"),
    "kc_red":   ("#EC3135", "Signal red",    "CN text, JP hearts + red bars + red star"),
    "kc_blue":  ("#1F8DE3", "Electric blue", "JP blue bars, CN blue dots"),
    "kc_white": ("#F1F0EA", "Star white",    "star speckles, KR text, CN ring sparkles"),
    "kc_glow":  ("#1E5B4F", "Glow green",    "sheer neon halo behind the JP text + CN dots"),
}
KC_KEYS = list(KC_PAL)
FABRIC = "#191C24"          # washed black duck (mockup median #13161D, lifted for the render)
for k, v in KC_PAL.items():
    motifs2.PAL[k] = v; motifs2.HEX[k] = v[0]; motifs.HEX[k] = v[0]

# stop order inside a layer
KC_ORDER = ["kc_glow", "kc_white", "kc_blue", "kc_red", "kc_gold", "kc_lemon", "kc_mint"]
tech.COLOUR_ORDER = KC_ORDER + [c for c in tech.COLOUR_ORDER if c not in KC_ORDER]

# ---------------------------------------------------------------- region codes
# code -> (name, stitch, angle rule, density, stitch length, underlay, pull comp, notes)
KC_RULES = {
 "GLOW":   ("Neon glow halo (sheer)",     "Run, serpentine",    "along the text line",      "1.6 rows", "2.6", "none",              "—",    "≈ 20 % cover, sewn first; knocks nothing out"),
 "STAR":   ("Star speckle (4-point)",     "Satin",              "across arm",               "0.40",  "—",    "none",                  "0.15", "arms ≥ 0.9 wide, blunt tips"),
 "DOT":    ("Star dot",                   "Satin dot",          "across dot",               "0.40",  "—",    "none",                  "0.10", "Ø 1.3–2.0"),
 "TXF":    ("Text stroke, flat satin",    "Satin, turning",     "across the stroke",        "0.40",  "—",    "centre run if ≥ 2",     "0.20", "set from the font, split per stroke"),
 "PF-TX":  ("Text stroke, 3D puff",       "Satin over 3 mm foam","across the stroke",       "0.30",  "—",    "none (foam)",           "0.35", "puff: 2.5–7 wide; sew-out to confirm"),
 "PF-BAR": ("Spark bar, 3D puff",         "Satin over 3 mm foam","across the bar",          "0.30",  "—",    "none (foam)",           "0.35", "rounded capsule ends"),
 "PF-HRT": ("Heart, 3D puff",             "Satin over 3 mm foam","across the heart (45°)",  "0.30",  "—",    "none (foam)",           "0.35", ""),
 "PF-STR": ("Big star, 3D puff",          "Satin over 3 mm foam","across each arm",         "0.30",  "—",    "none (foam)",           "0.35", "5-point, arms ≥ 2.5"),
 "BAR":    ("Spark bar, satin",           "Satin, turning",     "across the bar",           "0.40",  "—",    "centre run",            "0.20", ""),
 "STR5":   ("5-point star, satin",        "Satin",              "across each arm",          "0.40",  "—",    "centre run",            "0.20", ""),
 "STR5-o": ("Star outline (open)",        "Satin, turning",     "across the outline",       "0.40",  "—",    "none",                  "0.15", "1.4 wide"),
 "DOTB":   ("Ring dot (domed)",           "Satin, radial",      "radial from dot centre",   "0.38",  "—",    "edge run + 1 padding",  "0.15", "Ø 8.5, raised"),
 "OVAL":   ("Oval ring",                  "Satin, turning",     "across the ring",          "0.40",  "—",    "edge + centre run",     "0.20", "4.2 wide"),
 "OVAL-hl":("Oval ring highlight",        "Satin, turning",     "across the ring",          "0.40",  "—",    "none",                  "0.10", "1.1 wide, on top"),
 "FACE":   ("Star face (eyes/centre)",    "Satin dot",          "across dot",               "0.40",  "—",    "none",                  "0.10", "Ø 1.2"),
}
tech.RULES.update(KC_RULES)
tech.LAYER_NAMES.update({20: "Glow halo", 21: "Star speckles", 22: "Spark bars + stars", 23: "Hearts", 24: "Ring dots",
                         25: "Oval ring", 26: "Text (flat)", 27: "Text (puff)", 28: "Faces / highlights"})

sheet.FONT = "Liberation Sans"

PUFF_SP = 0.30          # puff satin row spacing (dense, cuts the foam at the column ends)
PUFF = True             # region codes starting PF- are built as puff satin (no underlay, dense, +pull)

def patch_dst2():
    """call after `import dst2`: pull comp for this project's codes, no colour merge, puff satin builder."""
    import dst2
    for k, v in KC_RULES.items():
        dst2.PULL[k] = float(v[6]) if v[6] not in ("—", "") else 0.0
    dst2.COL_MERGE.clear()
    if not getattr(dst2, "_kc_puff", False):
        _orig = dst2.build_object
        def build_object(r, earlier_tones):
            code = tech.rule_for(r["grp"])
            if not (PUFF and code.startswith("PF-") and r["st"] == "satin"):
                return _orig(r, earlier_tones)
            pull = dst2.pull_for(code); blocks = []
            for p in dst2.polys(r["geom"]):
                if p.area < 0.06: continue
                line = dst2.centreline(p) if dst2.is_elongated(p) else None
                if line is not None: blocks.append(dst2.turning_satin(p, line, sp=PUFF_SP, pull=pull))
                else:
                    a = dst2.SR.auto_angle(p) if r["ang"] in ("auto", None) else r["ang"]
                    blocks.append(dst2.fixed_satin(p, a, sp=PUFF_SP, pull=pull))
            return [b for b in blocks if len(b) > 1]
        dst2.build_object = build_object; dst2._kc_puff = True
    return dst2

STYLE = "HK-HJ-KCOS-BK"
NAME = "Keep Clean Our Space Hooded Jacket — Washed Black"
SHORT = "KCOS"
SIZES = ["XS", "S", "M", "L", "XL", "XXL", "3XL"]
# badges keep one size per grade; positions follow each size's panel (art_size.py)
GRADE = {"XS": ("A", 0.92), "S": ("A", 0.92), "M": ("B", 1.0), "L": ("B", 1.0), "XL": ("B", 1.0), "XXL": ("C", 1.06), "3XL": ("C", 1.06)}
PIECES = ("FR", "FL", "SR", "SL")
PIECE_NAME = {"FR": "wearer's right front", "FL": "wearer's left front", "SR": "right sleeve", "SL": "left sleeve"}
PIECE_CODE = {"FR": "F02", "FL": "F01", "SR": "S01", "SL": "S02"}
ELEMENTS = {   # id -> (slug, title, piece)
    "01": ("jp-badge", "宇宙をきれいに badge (JP)", "FR"),
    "02": ("en-badge", "KEEP CLEAN OUR SPACE badge (EN)", "FL"),
    "03": ("cn-badge", "不要污染地球 badge (CN)", "FR"),
    "04": ("kr-oval", "우주를 깨끗하게 oval (KR)", "FL"),
    "05": ("star-field", "Star speckle field", "FR FL SR SL"),
}
TEXT = {"01": "宇宙をきれいに", "02": ("KEEP", "CLEAN", "OUR SPACE"), "03": "不要污染地球", "04": "우주를 깨끗하게"}
REV_EMB = "Rev A"; REV_GAR = "Rev A"; DATE = "16 Oct 2026"
