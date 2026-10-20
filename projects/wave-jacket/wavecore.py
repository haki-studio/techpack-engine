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
 "RP":      ("Rope line (cream cord)",       "Tatami along",        "along the cord (A16)",     "0.45", "3.5", "edge run",                    "0.20", "continuous 2.4 mm cords between the stripes (fragments joined, uniform width)"),
 "WV":      ("Wave stripe (twisted cord)",   "Tatami cord / turning satin", "along the stripe ± 15° (cord twist, alternating per tone)", "0.45 / 0.42", "3.5", "edge run + 90° lattice (tatami > 60 mm²) · centre run (satin)", "0.25", "rows along the stripe, 15° twist = twisted cord (close-up, A16); turning satin only on stripes < 3 wide with no holes"),
 "FM":      ("Foam crest / curl (raised)",   "Tatami base + CHENILLE", "along the curl (sectors, A16)", "0.45", "5.0", "base: edge run · alt: 1 padding layer", "0.30", "PRIMARY: flat base + _CHENILLE loop rows 1.8 mm + chain cords; ALT (alt_padded/): padded tatami + loop runs"),
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
    dst2.ALONG.add("WV"); dst2.ALONG.add("RP")      # A16: stripes + rope cords sew rows along their length
    dst2.COL_MERGE.clear()
    dst2.TRIM_MIN = 2.0             # an exposed move > 2 mm is trimmed, never left as a float
    if not getattr(dst2, "_wave_cov_guard", False):
        dst2._orig_build_object = dst2.build_object; dst2.build_object = covered_build_object; dst2._wave_cov_guard = True
    if not getattr(dst2, "_wave_cord", False):
        dst2._orig_sections = dst2.sections; dst2.sections = cord_sections; dst2._wave_cord = True
    return dst2

# ---------------------------------------------------------------- satin coverage guard (QA 19 Oct, ENGINE_NOTES 7)
SAT_MIN_COV = 0.97
COV_LOG = {"checked": 0, "fixed_satin": 0, "tatami": 0}

def stitch_cover(blocks, geom, ppm=10, thread=0.6):
    """share of geom (eroded 0.25 mm) covered by the stitch lines of blocks, each drawn thread mm wide (> the 0.42 row spacing: a
    satin row of 40wt spreads to ~0.5-0.6 mm, so only real fan gaps count)"""
    import numpy as np
    from PIL import Image, ImageDraw
    from scipy import ndimage as ndi
    x0, y0, x1, y1 = geom.bounds; x0 -= 1; y0 -= 1
    W, H = int((x1 - x0 + 1) * ppm) + 2, int((y1 - y0 + 1) * ppm) + 2
    A = Image.new("L", (W, H)); d = ImageDraw.Draw(A)
    import dst2
    for q in dst2.polys(geom):
        d.polygon([((x - x0) * ppm, (y - y0) * ppm) for x, y in q.exterior.coords], fill=255)
        for h in q.interiors: d.polygon([((x - x0) * ppm, (y - y0) * ppm) for x, y in h.coords], fill=0)
    a = ndi.binary_erosion(np.asarray(A) > 0, iterations=max(1, int(0.25 * ppm)))
    if a.sum() == 0: return 1.0
    S = Image.new("L", (W, H)); ds = ImageDraw.Draw(S); lw = max(1, int(round(thread * ppm)))
    for b in blocks:
        ds.line([((x - x0) * ppm, (y - y0) * ppm) for x, y in b], fill=255, width=lw)
    return float((a & (np.asarray(S) > 0)).sum() / a.sum())

# ---------------------------------------------------------------- twisted-cord stripes (review item 5, Rev B)
# The close-up's stripes are twisted cords: the stitch rows of each stripe run at a slant to the stripe, not along it.
# Tatami rows of a WV stripe are laid at the local stripe direction + CORD_TWIST (alternating sign from tone to tone, so
# neighbouring cords twist opposite ways, as in the close-up). Everything else is the engine's along-the-stripe sections.
CORD_TWIST = 15.0          # LESSONS A16: rows ALONG the stripe; a 15 deg twist keeps the cord look inside the 25 deg grain tolerance
_CUR = {"r": None}
def cord_sections(p, line, step=6.0, across=False):
    import dst2
    out = dst2._orig_sections(p, line, step, across)
    r = _CUR["r"]
    if r is None or r.get("grp") != "WV" or across: return out
    sg = 1 if WV_KEYS.index(r["col"]) % 2 == 0 else -1
    return [(q, a + sg * CORD_TWIST) for q, a in out]

def covered_build_object(r, earlier_tones):
    _CUR["r"] = r
    try: return _covered_build_object(r, earlier_tones)
    finally: _CUR["r"] = None

def _covered_build_object(r, earlier_tones):
    """engine build_object, then: a satin object whose stitches cover < SAT_MIN_COV of it (turning satin fans out on the
    outside of a bend: drops, curl shades) is rebuilt as fixed-angle split satin, or tatami if that covers more"""
    import dst2, stitchrender as SR
    blocks = dst2._orig_build_object(r, earlier_tones)
    if r["st"] != "satin" or isinstance(r.get("ang"), tuple): return blocks
    COV_LOG["checked"] += 1
    c0 = stitch_cover(blocks, r["geom"])
    if c0 >= SAT_MIN_COV: return blocks
    code = tech.rule_for(r["grp"]); pull = dst2.pull_for(code); fs = []
    for p in dst2.polys(r["geom"]):
        if p.area < 0.06: continue
        if dst2.width_of(p) > 4.0: fs += dst2.edge_run(p, 0.5)
        fs.append(dst2.fixed_satin(p, SR.auto_angle(p), pull=pull))
    fs = [b for b in fs if len(b) > 1]; c1 = stitch_cover(fs, r["geom"])
    if c1 >= SAT_MIN_COV or c1 >= c0:
        if c1 >= SAT_MIN_COV:
            COV_LOG["fixed_satin"] += 1; return fs
    tb = dst2._orig_build_object(dict(r, st="tatami"), earlier_tones); c2 = stitch_cover(tb, r["geom"])
    best = max((c0, 0, blocks), (c1, 1, fs), (c2, 2, tb), key=lambda t: t[0])
    if best[1]: COV_LOG["fixed_satin" if best[1] == 1 else "tatami"] += 1
    return best[2]

STYLE = "HK-JK-WAVE-NV"
NAME = "Wave Jacket — Washed Navy"
ELEM = "01"; ELEM_SLUG = "wave"; ELEM_TITLE = "WAVE — Hokusai-style wave + raised foam curls (back, fronts, sleeves)"
PIECES = ("BK", "FR", "FL", "SR", "SL")
PIECE_NAME = {"BK": "back", "FR": "wearer's right front", "FL": "wearer's left front", "SR": "right sleeve", "SL": "left sleeve"}
PIECE_CODE = {"BK": "B01", "FR": "F02", "FL": "F01", "SR": "S01", "SL": "S02"}
SIZES = ["XS", "S", "M", "L", "XL", "XXL", "3XL"]
GRADE = {"XS": ("A", 0.92), "S": ("A", 0.92), "M": ("B", 1.0), "L": ("B", 1.0), "XL": ("B", 1.0), "XXL": ("C", 1.08), "3XL": ("C", 1.08)}
REV_EMB = "Rev B"; REV_GAR = "Rev A"; DATE = "19 Oct 2026"
# EMBROIDERY SAMPLING package (founder, 19 Oct): size-M strike-off only; other sizes are rebuilt after the sew-out and the
# garment pages (T1-T16, pattern) follow once the jacket body revision is done.
DOC_SIZES = ["M"]
GARMENT_NOTE = "Garment pages (T1-T16) + pattern to follow - jacket under revision"
