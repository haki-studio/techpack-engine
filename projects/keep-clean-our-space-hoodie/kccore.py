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

TEXT_CODES = ("TXF", "PF-TX")
def stroke_satin(p, sp, pull):
    """satin for one text stroke: rows perpendicular to the smoothed centreline, a row that would cross the previous one
    (tight inner curve / junction blob) is skipped, so the satin never fans; short blobs get a fixed satin across their
    long axis. Rows > 7 mm are split (split satin)."""
    import dst2, math
    import numpy as np
    from shapely.geometry import LineString
    w = 2 * p.area / max(p.length, 1e-6)
    line = dst2.centreline(p) if p.area > 1.0 else None
    if line is not None:
        line = line.simplify(max(0.25, 0.35 * w))
    if line is None or line.length < 1.6 * max(w, 1.0):
        mrr = p.minimum_rotated_rectangle; cs = list(mrr.exterior.coords)
        e0 = (cs[1][0]-cs[0][0], cs[1][1]-cs[0][1]); e1 = (cs[2][0]-cs[1][0], cs[2][1]-cs[1][1])
        e = e0 if math.hypot(*e0) >= math.hypot(*e1) else e1
        return dst2.fixed_satin(p, math.degrees(math.atan2(e[1], e[0])) + 90, sp=sp, pull=pull)
    pp = p.buffer(pull, join_style="round") if pull else p
    L = line.length; n = max(2, int(L / sp)); out = []; prev = None; flip = False; rows = []
    for k in range(n + 1):
        s = L * k / n; c = line.interpolate(s)
        a_ = line.interpolate(max(0, s - max(0.8, w*0.6))); b_ = line.interpolate(min(L, s + max(0.8, w*0.6)))
        th = math.atan2(b_.y - a_.y, b_.x - a_.x) + math.pi/2; R = 30.0
        seg = LineString([(c.x - R*math.cos(th), c.y - R*math.sin(th)), (c.x + R*math.cos(th), c.y + R*math.sin(th))]).intersection(pp)
        segs = [g for g in getattr(seg, "geoms", [seg]) if g.geom_type == "LineString" and not g.is_empty]
        if not segs: continue
        sg = min(segs, key=lambda g: g.distance(c))
        A, B = sg.coords[0], sg.coords[-1]
        if prev is not None:
            if math.hypot(A[0]-prev[0][0], A[1]-prev[0][1]) > math.hypot(B[0]-prev[0][0], B[1]-prev[0][1]): A, B = B, A
            if LineString([A, B]).crosses(LineString(prev)): continue
            ma, mb = math.dist(A, prev[0]), math.dist(B, prev[1])
            if min(ma, mb) < 0.12 and max(ma, mb) > 4 * sp: continue        # pivoting round an inner corner = a fan
        prev = (A, B); rows.append((A, B))
        d = math.hypot(B[0]-A[0], B[1]-A[1])
        row = [A] + (dst2.sub(A, B, d / math.ceil(d / 6.0)) if d > 7.0 else [B])
        out += row if not flip else row[::-1]; flip = not flip
    # coverage check: rows (as 2 x spacing bands) must cover the stroke; else a fixed satin at the most "across" angle
    from shapely.ops import unary_union
    cov = unary_union([LineString(r_).buffer(max(sp, 0.35), cap_style="flat") for r_ in rows]).intersection(p).area / max(p.area, 1e-9) if rows else 0
    # fan check: the satin may turn at most ~60 deg while travelling one stroke width along the centreline (a tighter
    # turn pivots the rows round the inner edge)
    ds = []
    for (a1, b1), (a2, b2) in zip(rows, rows[1:]):
        t1 = math.atan2(b1[1]-a1[1], b1[0]-a1[0]); t2 = math.atan2(b2[1]-a2[1], b2[0]-a2[0])
        ds.append(math.degrees(abs((t2 - t1 + math.pi/2) % math.pi - math.pi/2)))
    k = max(2, int(math.ceil(w / sp)))
    fan = max([sum(ds[i:i+k]) for i in range(max(1, len(ds) - k + 1))] or [0])
    lens = sorted(math.dist(a_, b_) for a_, b_ in rows) or [0]
    med = lens[len(lens)//2]; longf = sum(1 for v in lens if v > 1.6 * med) / max(1, len(lens))
    if cov < 0.95 or fan > 75 or (ds and max(ds) > 20) or longf > 0.12:
        best = None
        for a in range(0, 180, 15):
            segs = [g for g in dst2.SR.hatch(pp, a, 1.0) if g.length > 0]
            if not segs: continue
            m = max(g.length for g in segs) + 0.3 * sum(g.length for g in segs) / len(segs)
            if best is None or m < best[0]: best = (m, a)
        if best: return dst2.fixed_satin(p, best[1], sp=sp, pull=pull)
    return out

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
            if code == "TXF" and r["st"] == "satin":          # flat text: centre-run underlay + stroke satin
                pull = dst2.pull_for(code); blocks = []
                for p in dst2.polys(r["geom"]):
                    if p.area < 0.06: continue
                    ln = dst2.centreline(p) if (p.area > 1.0 and 2*p.area/max(p.length, 1e-6) >= 1.6) else None
                    if ln is not None: blocks.append(dst2.path_resample(list(ln.coords), 2.0))
                    blocks.append(stroke_satin(p, 0.40, pull))
                return [b for b in blocks if len(b) > 1]
            if not (PUFF and code.startswith("PF-") and r["st"] == "satin"):
                return _orig(r, earlier_tones)
            pull = dst2.pull_for(code); blocks = []
            for p in dst2.polys(r["geom"]):
                if p.area < 0.06: continue
                if isinstance(r["ang"], tuple):
                    blocks.append(dst2.radial_satin(p, r["ang"][1], r["ang"][2], sp=PUFF_SP, pull=pull)); continue
                if code in TEXT_CODES: blocks.append(stroke_satin(p, PUFF_SP, pull)); continue
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
