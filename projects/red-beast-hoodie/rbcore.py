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
    "rb_white":   ("#F8F5EE", "Highlight white", "bright edge run on the teeth (Rev B)"),
}
RB_KEYS = list(RB_PAL)
FABRIC = "#2B3039"          # washed black / charcoal duck (mockup sample, PROPOSED)
for k, v in RB_PAL.items():
    motifs2.PAL[k] = v; motifs2.HEX[k] = v[0]; motifs.HEX[k] = v[0]

# sew order: red hair strokes first (their travel hides under the black ground sewn after them), the black ground,
# then the cream outlines + teeth last so they sit raised on top (fidelity: "white raised outline")
SEW = ["rb_red", "rb_crimson", "rb_black", "rb_cream", "rb_white"]
tech.COLOUR_ORDER = SEW + [c for c in tech.COLOUR_ORDER if c not in SEW]

# ---------------------------------------------------------------- region codes
# code -> (name, stitch, angle rule, density, stitch length, underlay, pull comp, notes)
RB_RULES = {
 "HS":       ("Hair stroke (red)",            "Satin ALONG the stroke",  "stroke direction (traced flow)", "0.42", "≤7 (split 6)", "centre run (≥ 1.8 wide)", "0.20", "long-and-short: 1.5–3 wide, 5–12 long, staggered ends"),
 "CS":       ("Crimson shade stroke",         "Satin ALONG the stroke",  "stroke direction (traced flow)", "0.42", "≤7 (split 6)", "centre run (≥ 1.8 wide)", "0.20", "lower edge of strands, dim-red stitches in the throat"),
 "BS":       ("Black ground stroke",          "Satin ALONG the stroke",  "stroke direction (traced flow)", "0.42", "≤7 (split 6)", "centre run (≥ 1.8 wide)", "0.15", "mouth + throat: directional strokes, not flat fill"),
 "SK":       ("Slash streak",                 "Satin, turning",          "across the streak",              "0.40", "≤7",  "centre run (≥ 2 wide)",      "0.20", "tapered pointed column 1.2–2.5 wide"),
 "OL":       ("Raised cord (cream)",          "Satin, turning",          "across the cord",                "0.38", "≤7",  "centre run (≥ 2 wide)",      "0.20", "2.5–3.0 wide (detail lines ≥ 1.2); lightning 2.5 root → 1.0 tip"),
 "OL-shadow":("Cord under-edge (crimson)",    "Satin, turning",          "across the band",                "0.40", "≤7",  "none",                       "0.15", "≈1 mm band under each cord"),
 "OL-tooth": ("Tooth (cream)",                "Satin ALONG the tooth",   "tooth long axis (vertical)",     "0.40", "≤7 (split 6)", "centre run (≥ 1.8 wide)", "0.20", "one object per tooth"),
 "OL-hl":    ("Tooth bright edge (white)",    "Bean (triple run)",       "follows the tooth edge",         "—",    "2.0", "none",                       "—",    "0.45 inside the tooth outline, sewn last"),
}
tech.RULES.update(RB_RULES)
tech.LAYER_NAMES.update({20: "Red hair strokes + streaks", 21: "Crimson shade strokes + cord under-edges", 22: "Black ground strokes", 23: "Cream cords + teeth", 24: "White tooth edges"})

sheet.FONT = "Liberation Sans"

def patch_dst2():
    """call after `import dst2`: pull-comp for this project's codes; 5 threads -> nothing to merge; and the Rev B
    stroke objects (r["fixed"]): satin with stitches ALONG the stroke at the stroke's own angle (the engine turns every
    elongated satin across its centreline - right for cords, wrong for long-and-short hair; ENGINE_NOTES 6)"""
    import dst2
    for k, v in RB_RULES.items():
        dst2.PULL[k] = float(v[6]) if v[6] not in ("—", "") else 0.0
    dst2.COL_MERGE.clear()
    if getattr(dst2, "_rb_patched", False): return dst2
    orig = dst2.build_object
    def build_object(r, earlier_tones):
        if not r.get("fixed") or r["st"] != "satin" or not isinstance(r["ang"], (int, float)): return orig(r, earlier_tones)
        pull = dst2.pull_for(tech.rule_for(r["grp"])); a = float(r["ang"]); blocks = []
        for p in dst2.polys(r["geom"]):
            if p.area < 0.06: continue
            if dst2.width_of(p) >= 1.8:          # centre-run underlay along the stroke
                for s_ in sheet_hatch(p.buffer(-0.5), a, 1e3):
                    cs = list(s_.coords)
                    if len(cs) >= 2: blocks.append(dst2.path_resample([cs[0], cs[-1]], 2.0))
            # satin rows ALONG the stroke, ordered cell by cell (chain_rows) so a row never jumps across a hole or a
            # concave bay of the object (fixed_satin zig-zags row to row in list order); stitches > 7 split at <= 6 mm
            pp = p.buffer(pull, join_style="round") if pull else p
            rows = []
            for a_, b_, _i in dst2.chain_rows(dst2.SR.hatch(pp, a, dst2.SP_SAT), pp, a, dst2.SP_SAT):
                d_ = ((b_[0]-a_[0])**2 + (b_[1]-a_[1])**2) ** 0.5
                rows.append([a_] + (dst2.sub(a_, b_, d_ / -(-d_ // 6.0)) if d_ > 7.0 else [b_]))
            blocks += dst2.join_rows(rows)
        return [b for b in blocks if len(b) > 1]
    def sheet_hatch(p, a, sp):
        import stitchrender as SR_
        if p.is_empty: return []
        c = p.centroid; from shapely.geometry import LineString as LS
        import math as m_
        ux, uy = m_.cos(m_.radians(a)), m_.sin(m_.radians(a)); R_ = 60
        ln = LS([(c.x - ux*R_, c.y - uy*R_), (c.x + ux*R_, c.y + uy*R_)]).intersection(p)
        return [g for g in ([ln] if ln.geom_type == "LineString" else getattr(ln, "geoms", [])) if g.geom_type == "LineString" and g.length > 1.0]
    dst2.build_object = build_object; dst2._rb_patched = True
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
REV_EMB = "Rev B"; REV_GAR = "Rev A"; DATE = "19 Oct 2026"

def fname(P, size, sec=None):
    e = PIECE_ELEM[P]; slug = ELEMS[e][0]
    return f"HAKI_{SHORT}_{e}_{slug}_{P}_{size}" + (f"_{sec}" if sec else "")
def outdir(P, size):
    e = PIECE_ELEM[P]; return f"out/{e}_{ELEMS[e][0]}/{size}"
