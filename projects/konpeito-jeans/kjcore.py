"""Konpeito black jeans — project core. Import FIRST in every script of this project.
Adds the house-spec thread palette + region codes to the shared engine dicts in place (no engine edits), installs the
satin-column builder (kjsatin, from keep-clean) and the 'no travel over already-sewn satin' make_pattern patch."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
import motifs, motifs2, tech, sheet

KJ_PAL = {   # Haki house spec Rev A (Oct 2026), 40wt polyester unless noted
    "kj_red":      ("#C8162B", "Red",          "patch edge + band, lettering, frame, accent dots"),
    "kj_cream":    ("#F2E9D8", "Cream",        "patch field"),
    "kj_white":    ("#FBF8F1", "White",        "border flowers + dots, flower centres, sparkles"),
    "kj_black":    ("#1C1A1A", "Black (60wt)", "lettering 元気でね / また会おうね, face line art"),
    "kj_pink":     ("#EF7FAC", "Pink",         "konpeito, flowers, hearts, pink star"),
    "kj_pink_hi":  ("#F8B5CF", "Pink tint",    "konpeito + star highlight"),
    "kj_yellow":   ("#F5C230", "Yellow",       "konpeito, flower, yellow star"),
    "kj_yellow_hi":("#FCE27E", "Yellow tint",  "konpeito + star highlight"),
    "kj_blue":     ("#35A6D6", "Blue",         "konpeito, flower, signature 理砂"),
    "kj_blue_hi":  ("#8ED2EE", "Blue tint",    "konpeito highlight"),
    "kj_rose":     ("#E8457A", "Rose",         "cheeks"),
}
for k, v in KJ_PAL.items():
    motifs2.PAL[k] = v; motifs2.HEX[k] = v[0]; motifs.HEX[k] = v[0]
tech.COLOUR_ORDER = list(KJ_PAL) + [c for c in tech.COLOUR_ORDER if c not in KJ_PAL]
WEIGHT = {k: ("60wt" if k in ("kj_black", "kj_blue60") else "40wt") for k in KJ_PAL}

KJ_RULES = {  # code -> (name, stitch, angle rule, density, stitch length, underlay, pull comp, notes)
 "BAND":  ("Patch band (under the border motifs)", "Tatami", "across the band", "0.42", "3.5", "edge run + 90° tatami", "0.20", "4.5 wide + under the edge"),
 "FIELD": ("Patch field",                 "Tatami",           "0°",                     "0.42", "3.5", "edge run + 90° tatami @ 2.0", "0.20", "motifs sew on top"),
 "EDGE":  ("Heat-cut edge satin",         "Satin column",     "across the edge",        "0.36 same side", "—", "edge run",            "0.15", "2.0 wide, sewn last"),
 "BFL":   ("Border flower Ø4.0",          "Satin, radial",    "radial from flower centre", "0.38", "—", "none",                "0.10", "red centre left open"),
 "BDOT":  ("Border dot Ø1.5",             "Satin dot",        "across",                 "0.38",  "—",  "none",                 "0.10", ""),
 "TXC":   ("Lettering column",            "Satin column",     "across the stroke",      "0.40 same side (60wt 0.28)", "—", "centre run if ≥ 1.4", "0.10", "font centreline fitted to the mockup, 1 width per string, round ends"),
 "LINE":  ("Face line art (60wt)",        "Satin column",     "across the line",        "0.28 same side", "—", "none",                 "0.00", "smoothed traced centrelines, 1 width"),
 "FL":    ("Flower petal",                "Satin, turning",   "across the petal axis",  "0.30", "—", "centre run on the axis", "0.15", "1 satin per petal, domed"),
 "FL-hi": ("Flower petal highlight",      "Satin, turning",   "across the petal axis",  "0.30", "—", "none",                 "0.10", "tint, lit side of each petal"),
 "KNOT":  ("Knot cluster / sparkle",      "Knot dot ×2 layers", "crossed 90°",          "0.20",  "—",  "none",                 "0.00", "Ø 0.9–1.15, touching in a cluster"),
 "DOT":   ("Accent dot / cheek",          "Satin dot",        "across",                 "0.38",  "—",  "none",                 "0.10", "Ø ≥ 1.2"),
 "KP":    ("Konpeito candy lobe",         "Satin",            "across each lobe axis",   "0.30", "—", "centre run on the axis", "0.15", "1 satin per traced lobe, domed"),
 "KPB":   ("Konpeito, back row (facing)",  "Satin",            "across each lobe axis",  "0.30", "—", "centre run on the axis", "0.15", "sewn first, behind the front row"),
 "KPB-hi": ("Konpeito tint, back row",    "Satin",            "across each lobe axis",  "0.30", "—", "none",                 "0.10", ""),
 "KP-hi": ("Konpeito lobe highlight",     "Satin, turning",   "across the lobe axis",   "0.30", "—", "none",                 "0.10", "tint, lit side of each lobe"),
 "STAR":  ("Puffy star body",             "Satin, radial",    "radial from star centre", "0.38", "—", "edge run",              "0.15", "direct on denim"),
 "STAR-hi": ("Puffy star highlight",      "Satin, radial",    "radial",                 "0.38",  "—",  "none",                 "0.10", ""),
}
tech.RULES.update(KJ_RULES)
sheet.FONT = "Noto Sans CJK JP"     # replaced below if missing
import subprocess
if "Noto Sans CJK" not in subprocess.run(["fc-list"], capture_output=True, text=True).stdout:
    sheet.FONT = "Zen Maru Gothic"
# column satin (kjsatin.column_pts) puts ONE needle point per row on alternate sides, so the same-side spacing is 2 x this
# value. Rev A used 0.30 (0.60 same side: open, comb-like satin) — fix pass: 0.20 / 0.18 (0.40 / 0.36 same side).
COL_SP = {"TXC": 0.20, "EDGE": 0.18, "LINE": 0.18, "FL": 0.30, "FL-hi": 0.30, "KP": 0.30, "KP-hi": 0.30, "KPB": 0.30, "KPB-hi": 0.30}

STYLE = "HK-JN-KONPEITO-BK"
NAME = "Konpeito Jeans — Washed Black"
REV = "Rev B5"
import datetime as _dt
DATE = (lambda d: f"{d.day} {d:%b %Y}")(_dt.date.today())     # build date (PR #34 nit: the stamp was typed and went stale)
SIZES = ["26", "28", "29", "30", "31", "32", "33", "34", "36", "38", "40"]     # founder 20 Oct (size labels); Rev A had 24-40 evens
sheet.FOOT = f"HAKI STUDIOS · {NAME} · {STYLE} · {REV} · {DATE}"
PROPOSED = "[proposed — confirm]"

def patch_dst2():
    import dst2, kjsatin as KS
    for k, v in KJ_RULES.items():
        dst2.PULL[k] = float(v[6]) if v[6] not in ("—", "") else 0.0
    dst2.SP_SAT, dst2.SP_RAD = 0.36, 0.36        # patch satins: small motifs, denser than the jacket defaults (0.42 / 0.40)
    if getattr(dst2, "_kj", False): return dst2
    _orig = dst2.build_object
    def build_object(r, earlier_tones):
        code = tech.rule_for(r["grp"])
        if r.get("ang") == "knots":                             # knot cluster: one block, touching knots
            import kjletter
            return [kjletter.knot_points(r["knots"])]
        if r.get("ang") == "col" and r.get("col_cl"):
            sp = COL_SP.get(code, 0.28); pull = dst2.pull_for(code)
            if r["col"] in ("kj_black", "kj_blue60"): sp = min(sp, 0.14)          # 60wt: 0.28 same side (finer thread needs denser rows)
            cl, w, caps, closed = r["col_cl"], r["col_w"], r["col_caps"], r["col_closed"]
            blocks = []
            if not closed and KS.poly_len(cl) > 2.5 and w >= 1.4:
                blocks.append(dst2.path_resample(KS.trim(cl, min(0.6, w / 2), min(0.6, w / 2)), 2.0))
                blocks.append(KS.column_pts(cl, w, sp, pull, caps, closed, r.get("col_prof"), reverse=True))
            else:
                blocks.append(KS.column_pts(cl, w, sp, pull, caps, closed, r.get("col_prof")))
            return [b for b in blocks if len(b) > 1]
        if r.get("ang") == "tl" and r.get("tline"):            # traced stroke piece: turning satin across its centreline
            from shapely.geometry import LineString
            p = r["geom"]; ln = LineString(r["tline"])
            ln = ln.intersection(p.buffer(0.6))
            ln = max(getattr(ln, "geoms", [ln]), key=lambda g: g.length) if not ln.is_empty else None
            pull = dst2.pull_for(code); sp = COL_SP.get(code, 0.30); blocks = []
            if ln is None or ln.geom_type != "LineString" or ln.length < 0.4:
                return [b for b in [dst2.fixed_satin(p, dst2.SR.auto_angle(p), sp=sp, pull=pull)] if len(b) > 1]
            w = dst2.width_of(p)
            if w >= 1.4 and ln.length > 2.5: blocks.append(dst2.path_resample(list(ln.coords), 2.0))
            blocks.append(turning(dst2, p, ln, sp, pull))
            return [b for b in blocks if len(b) > 1]
        return _orig(r, earlier_tones)
    dst2.build_object = build_object; dst2._kj = True
    _patch_make_pattern(dst2)
    return dst2

def turning(dst2, p, line, sp, pull):
    """dst2.turning_satin with empty-intersection guard; alternate rows on the inner side of tight curves shortened."""
    import math
    from shapely.geometry import LineString
    pp = p.buffer(pull, join_style="round") if pull else p
    L = line.length; n = max(2, int(L / sp)); pts = []; lastA = None; flip = False
    for k in range(n + 1):
        s = L * k / n; c = line.interpolate(s); th = dst2.tangent_at(line, s) + math.pi / 2; Rr = 20.0
        seg = LineString([(c.x - Rr*math.cos(th), c.y - Rr*math.sin(th)), (c.x + Rr*math.cos(th), c.y + Rr*math.sin(th))]).intersection(pp)
        segs = [g for g in getattr(seg, "geoms", [seg]) if g.geom_type == "LineString" and not g.is_empty and len(g.coords) >= 2]
        if not segs: continue
        sg = min(segs, key=lambda g: g.distance(c)); a, b = sg.coords[0], sg.coords[-1]
        if lastA is not None and math.dist(a, lastA) > math.dist(b, lastA): a, b = b, a
        lastA = a
        d = math.dist(a, b)
        seq = [a] + (dst2.sub(a, b, d / math.ceil(d / 6.0)) if d > 7.0 else [b])
        pts += seq if not flip else seq[::-1]; flip = not flip
    return pts

def _patch_make_pattern(dst2):
    """copied from keep-clean kccore (ENGINE_NOTES 11 there): travel hides under objects of the current stop only while
    they are still unsewn."""
    import inspect, numpy as np
    src = inspect.getsource(dst2.make_pattern)
    a = '        sewn_same = base_hid.copy()\n'
    b = '            if o["r"]["st"] in ("tatami", "padded"): cov.stamp(sewn_same, o["r"]["geom"])\n'
    assert src.count(a) == 1 and src.count(b) == 1, "engine make_pattern changed: update kjcore._patch_make_pattern"
    src = src.replace(a, a + '        _kc = _kc_init(objs, cov, si, sewn_same)\n')
    src = src.replace(b, '            _kc_sewn(_kc, o, sewn_same)\n')
    ns = dict(vars(dst2))
    def _kc_init(objs, cov, si, sewn_same):
        base = (cov.later > si) | cov.merged(si + 1)
        cnt = np.zeros(base.shape, np.int16); loc = {}
        from PIL import Image, ImageDraw
        for o in objs:
            g = o["r"]["geom"].buffer(0.1); bb = g.bounds
            c0 = max(0, int((bb[0] - cov.x0) * cov.ppm) - 1); r0 = max(0, int((bb[1] - cov.y0) * cov.ppm) - 1)
            c1 = min(cov.W, int((bb[2] - cov.x0) * cov.ppm) + 2); r1 = min(cov.H, int((bb[3] - cov.y0) * cov.ppm) + 2)
            if c1 <= c0 or r1 <= r0: continue
            im = Image.new("L", (c1 - c0, r1 - r0), 0); d = ImageDraw.Draw(im)
            for p in dst2.polys(g):
                T = lambda cs: [((x - cov.x0) * cov.ppm - c0, (y - cov.y0) * cov.ppm - r0) for x, y in cs]
                d.polygon(T(p.exterior.coords), fill=255)
                for q in p.interiors: d.polygon(T(q.coords), fill=0)
            m = np.array(im) > 127; cnt[r0:r1, c0:c1] += m; loc[id(o)] = (r0, r1, c0, c1, m)
        sewn_same[:] = base | (cnt > 0)
        return dict(base=base, cnt=cnt, loc=loc)
    def _kc_sewn(kc, o, sewn_same):
        L = kc["loc"].pop(id(o), None)
        if L is None: return
        r0, r1, c0, c1, m = L
        kc["cnt"][r0:r1, c0:c1] -= m
        sewn_same[r0:r1, c0:c1] = kc["base"][r0:r1, c0:c1] | (kc["cnt"][r0:r1, c0:c1] > 0)
    ns["_kc_init"] = _kc_init; ns["_kc_sewn"] = _kc_sewn
    exec(src, ns); dst2.make_pattern = ns["make_pattern"]
