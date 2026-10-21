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
    # Rev B (review item 3): lighter rim / facet threads for the domed puff look, haze under big sparkles (item 9)
    "kc_mint_lt": ("#B4F5E6", "Mint tint",    "lighter rim of the mint puff text, bars and dots"),
    "kc_blue_lt": ("#73C4FF", "Blue tint",    "lighter rim of the blue bars and CN blue dots"),
    "kc_red_lt":  ("#FF8C84", "Red tint",     "lighter rim / facets of the red hearts, bars and star"),
    "kc_lemon_lt": ("#FFF4B8", "Lemon tint",  "lighter rim of the lemon puff letters (CLEAN) and lemon bars"),
}
KC_KEYS = list(KC_PAL)
FABRIC = "#191C24"          # washed black duck (mockup median #13161D, lifted for the render)
for k, v in KC_PAL.items():
    motifs2.PAL[k] = v; motifs2.HEX[k] = v[0]; motifs.HEX[k] = v[0]

# Rev H: the dropped threads stay REGISTERED (hex + name) so old fixtures / test stops still resolve, but they are not on
# this jacket's thread list (KC_KEYS) and no region uses them (scene builds no glow / haze: kccore.GLOW False)
LEGACY_PAL = {"kc_glow": ("#1E5B4F", "Glow green", "Rev A-G only: glow halo (dropped 21 Oct)"),
              "kc_haze": ("#3A4357", "Star haze", "Rev B-G only: haze under the sparkles (dropped 21 Oct)")}
for k, v in LEGACY_PAL.items():
    motifs2.PAL[k] = v; motifs2.HEX[k] = v[0]; motifs.HEX[k] = v[0]
# specbase builds its thread table (TH) at import from the palette: if it was imported before this module (another test
# first), add this project's keys, so a written PES can name every thread (ENGINE_NOTES 29)
_sb = sys.modules.get("specbase")
if _sb is not None and hasattr(_sb, "TH"):
    _miss = [k for k in list(KC_PAL) + list(LEGACY_PAL) if k not in _sb.TH]
    if _miss: _sb.TH.update(tech.thread_table(_miss))

# stop order inside a layer
# Rev H (founder 21 Oct): the glow halo + star haze are dropped -> Glow green + Star haze threads removed (10 threads)
KC_ORDER = ["kc_white", "kc_blue", "kc_blue_lt", "kc_red", "kc_red_lt", "kc_gold", "kc_lemon", "kc_lemon_lt", "kc_mint", "kc_mint_lt"]
tech.COLOUR_ORDER = list(LEGACY_PAL) + KC_ORDER + [c for c in tech.COLOUR_ORDER if c not in KC_ORDER and c not in LEGACY_PAL]

# ---------------------------------------------------------------- region codes
# code -> (name, stitch, angle rule, density, stitch length, underlay, pull comp, notes)
KC_RULES = {
 "GLOW":   ("Neon glow halo (sheer)",     "Run, serpentine",    "along the text line",      "1.6 rows", "2.6", "none",              "—",    "sewn first, under the art"),
 "STAR":   ("Star speckle (4-point)",     "Satin",              "across arm",               "0.40",  "—",    "none",                  "0.15", "arms ≥ 0.9 wide, blunt tips"),
 "DOT":    ("Star dot",                   "Satin dot",          "across dot",               "0.40",  "—",    "none",                  "0.00", "Ø traced, min 1.45"),
 "TXF":    ("Text stroke, flat satin",    "Satin, turning",     "across the stroke",        "0.40",  "—",    "centre run if ≥ 1.6",   "0.20", "font strokes, 1 satin each"),
 "PF-TX":  ("Text stroke, 3D puff",       "Satin over 3 mm foam","across the stroke",       "0.30",  "—",    "none (foam)",           "0.35", "puff, strokes 2.5–7 wide"),
 "PF-BAR": ("Spark bar, 3D puff",         "Satin over 3 mm foam","across the bar",          "0.20 zz",  "—",    "none (foam)",           "0.35", "rounded capsule ends"),
 "PF-HRT": ("Heart, 3D puff",             "Satin over 3 mm foam","across the heart (45°)",  "0.30",  "—",    "none (foam)",           "0.35", ""),
 "PF-STR": ("Big star, 3D puff",          "Satin over 3 mm foam","across each arm",         "0.30",  "—",    "none (foam)",           "0.35", "5-point, arms ≥ 2.5"),
 "BAR":    ("Spark bar, satin",           "Satin, turning",     "across the bar",           "0.40",  "—",    "centre run",            "0.20", ""),
 "STR5":   ("5-point star, satin",        "Satin",              "across each arm",          "0.40",  "—",    "centre run",            "0.20", ""),
 "STR5-o": ("Star outline (open)",        "Satin, turning",     "across the outline",       "0.40",  "—",    "none",                  "0.15", "1.4 wide"),
 "DOTB":   ("Ring dot (domed)",           "Satin, radial",      "radial from dot centre",   "0.38",  "—",    "edge run",              "0.15", "Ø 12.4"),
 "OVAL":   ("Oval ring",                  "Satin column, closed", "across the ring",        "0.28 zz",  "—",    "edge + centre run",     "0.20", "4.0 wide"),
 "OVAL-hl":("Oval ring highlight",        "Satin column, closed", "across the ring",        "0.28 zz",  "—",    "none",                  "0.10", "1.1 wide, on top"),
 "FACE":   ("Star face (eyes/centre)",    "Satin dot",          "across dot",               "0.40",  "—",    "none",                  "0.10", "Ø 1.2"),
 # Rev B codes (review Rev A): columns = one satin per stroke along its centreline (kcsatin)
 "GLOW":   ("Neon glow, stipple run",     "Run, random short stitches", "random",          "0.30+0.16/mm", "1.8", "none",     "—",    "fades 0–4.5 mm from the art"),
 "GLOW-D": ("Neon halo, dense band",      "Tatami, sheer",      "along the badge line",     "0.60",  "2.5",  "none",                  "—",    "0–1.9 mm round the art"),
 "GLOW-S": ("Neon halo, soft band",       "Tatami, open",       "along the badge line +8°", "1.30",  "2.5",  "none",                  "—",    "1.9–3.8 mm, ragged edge"),
 "HAZE":   ("Sparkle haze, stipple run",  "Run, random short stitch", "random",          "0.55+0.35/mm", "1.5", "none",            "—",    "ring 0–r round sparkles ≥ 5 mm"),
 "SPK":    ("Sparkle (concave 4-point)",  "Satin, 2 tapered columns", "across each arm",    "0.24 zz",  "—",    "none",                  "0.00", "tips stop 0.3 short"),
 "TXC":    ("Text stroke column, flat",   "Satin column",       "across the stroke",        "0.25 zz",  "—",    "centre run",            "0.15", "1 column per stroke"),
 "PF-TXC": ("Text stroke column, puff",   "Satin column over foam", "across the stroke",    "0.20 zz",  "—",    "none (foam)",           "0.30", "core under the rim"),
 "PF-RIM": ("Puff rim (lighter thread)",  "Satin column over foam", "across the rim",       "0.20 zz",  "—",    "none (foam)",           "0.15", "0.85 wide, on the edge"),
 "PF-DOT": ("Domed dot core, puff",       "Satin column (disc)", "parallel, 35°",           "0.20 zz",  "—",    "none (foam)",           "0.25", "staggered splits"),
 "PF-OVAL":("Oval ring, 3D puff",        "Satin column over foam, closed", "across the ring", "0.20 zz", "—",   "none (foam)",           "0.30", "5.0 wide, founder 20 Oct"),
 "PF-OVHL":("Oval highlight, puff",        "Satin column over foam, closed", "across the ring", "0.20 zz", "—",   "none (foam)",           "0.10", "1.1 wide, on top of the ring"),
 "ORN":    ("Ornament (KR mark, accents)", "Satin column",      "across the stroke",        "0.25 zz",  "—",    "none",                  "0.10", "1.0–1.2 wide"),
}
tech.RULES.update(KC_RULES)
tech.LAYER_NAMES.update({20: "Glow halo", 21: "Star speckles", 22: "Spark bars + stars", 23: "Hearts", 24: "Ring dots",
                         25: "Oval ring", 26: "Text (flat)", 27: "Text (puff)", 28: "Faces / highlights"})

sheet.FONT = "Liberation Sans"
# Rev H (founder 21 Oct): "drop it entirely" - no stipple glow round the badges, no haze under the sparkles
GLOW = False

# column satin is a true zig-zag (each stitch crosses once): same-edge needle points are 2 x sp apart, so these are about
# half the row spacing of the engine satin (which hits both edges every row) for the same coverage
COL_SP = {"PF-TXC": 0.20, "PF-RIM": 0.20, "PF-BAR": 0.20, "PF-DOT": 0.20, "TXC": 0.25, "ORN": 0.25, "SPK": 0.24, "OVAL": 0.28, "OVAL-hl": 0.28, "PF-OVAL": 0.20, "PF-OVHL": 0.20}
OPEN_TAT = {"GLOW-D": (0.60, 2.5), "GLOW-S": (1.30, 2.5), "HAZE": (1.10, 2.2)}
HALF_THREAD = 0.21      # 40wt polyester lies ~0.42 wide: needle points sit this far inside the art outline
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
            if r.get("ang") == "col" and r.get("col_cl"):          # Rev B satin column (kcsatin)
                import kcsatin as KS
                puff = PUFF and code.startswith("PF-")
                sp = COL_SP.get(code, 0.20 if puff else 0.30)          # zig-zag spacing: one edge is hit every 2 x sp
                pull = dst2.pull_for(code)
                cl = r["col_cl"]; w = r["col_w"]; caps = r["col_caps"]; closed = r["col_closed"]; prof = r.get("col_prof")
                if code == "SPK" and not closed and KS.poly_len(cl) > 1.6:      # tips stop half a thread short (A14: stitched span = traced span)
                    cl = KS.trim(cl, 0.3, 0.3)
                # needle points half a thread (0.21) inside the outline: as sewn, the thread covers to the art edge (A14)
                if not r.get("rim") and code != "SPK":
                    ins = max(0.0, min(HALF_THREAD, (w - 0.8) / 2))
                    if ins > 0:
                        w = w - 2 * ins
                        if not closed and KS.poly_len(cl) > 4 * ins + 0.5: cl = KS.trim(cl, ins if caps[0] == "round" else 0.0, ins if caps[1] == "round" else 0.0)
                blocks = []
                if code in ("TXC", "OVAL") and not closed and KS.poly_len(cl) > 2.5 and w >= 1.4:      # centre-run underlay, then satin back
                    ul = KS.trim(cl, min(0.6, w / 2), min(0.6, w / 2))
                    blocks.append(dst2.path_resample(ul, 2.0))
                    blocks.append(KS.column_pts(cl, w, sp, pull, caps, closed, prof, reverse=True))
                else:
                    blocks.append(KS.column_pts(cl, w, sp, pull, caps, closed, prof))
                return [b for b in blocks if len(b) > 1]
            if r.get("run_pts"):                                       # stipple glow / haze: the precomputed run
                return [list(r["run_pts"])]
            if code in OPEN_TAT and r["st"] == "tatami":            # sheer halo / haze: open tatami, no underlay, no edge run
                sp, L = OPEN_TAT[code]; blocks = []
                for p in dst2.polys(r["geom"]):
                    if p.area < 0.3: continue
                    blocks += dst2.join_rows(dst2.tatami_rows(p, r["ang"], sp, L))
                return [b for b in blocks if len(b) > 1]
            if code == "TXF" and r["st"] == "satin":          # flat text: centre-run underlay + stroke satin
                pull = dst2.pull_for(code); blocks = []
                for p in dst2.polys(r["geom"]):
                    if p.area < 0.06: continue
                    ln = dst2.centreline(p) if (p.area > 1.0 and 2*p.area/max(p.length, 1e-6) >= 1.6) else None
                    if ln is not None: blocks.append(dst2.path_resample(list(ln.coords), 2.0))
                    blocks.append(stroke_satin(p, 0.40, pull))
                return [b for b in blocks if len(b) > 1]
            if r["st"] == "satin" and not isinstance(r.get("ang"), tuple) and r.get("ang") != "col":
                gi = r["geom"].buffer(-HALF_THREAD).buffer(0)
                if not gi.is_empty and gi.area > 0.4 * r["geom"].area: r = dict(r, geom=gi)
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
        _patch_make_pattern(dst2)
    return dst2

def _patch_make_pattern(dst2):
    """Travel may hide under objects of the current stop only while they are UNSEWN (review Rev A item 1: the engine's
    own-stop mask also counted satins already sewn, so travel ran on top of finished letters — the straight lines across
    宇 / 要 in the Rev A DST). Exec'd copy of dst2.make_pattern with a per-object count raster (ENGINE_NOTES 11)."""
    import inspect, numpy as np
    src = inspect.getsource(dst2.make_pattern)
    a = '        sewn_same = base_hid.copy()\n'
    b = '            if o["r"]["st"] in ("tatami", "padded"): cov.stamp(sewn_same, o["r"]["geom"])\n'
    assert src.count(a) == 1 and src.count(b) == 1, "engine make_pattern changed: update kccore._patch_make_pattern"
    src = src.replace(a, a + '        _kc = _kc_init(objs, cov, si, sewn_same)\n')
    src = src.replace(b, '            _kc_sewn(_kc, o, sewn_same)\n')
    # Rev C, house rule 6 under puff (LESSONS B34): flat stops (sewn BEFORE the foam is laid) may not hide their travel
    # under the later puff stops: inside the puff footprint minus CUT_KEEP_MM the 'later cover' is removed for them, so
    # no flat needle point lands inside the foam (gate: kcstitch.foam_gates base_under_puff)
    c_ = '    for si, s in enumerate(stops):\n        k = s["col"]\n'
    assert src.count(c_) == 1, "engine make_pattern changed: update kccore._patch_make_pattern (foam mask)"
    src = src.replace(c_, '    _fm = _kc_foam_init(cov, stops)\n' + c_ + '        _kc_foam_stop(cov, _fm, s)\n')
    ns = dict(vars(dst2))
    def _kc_foam_init(cov, stops):
        from shapely.ops import unary_union
        pg = [r["geom"] for s in stops if s.get("puff") for r in s["regions"]]
        if not pg: return None
        # mask from 0.5 mm inside the puff edge: the router's raster (0.2 mm px) and its 0.8 mm endpoint forgiveness let
        # travel reach ~0.4 mm past its mask, and the gate counts points deeper than CUT_KEEP_MM + 0.25
        core = unary_union(pg).buffer(-0.5)
        if core.is_empty: return None
        m = cov._draw(core, 0.0)
        lf, rf = cov.later.copy(), cov.raw.copy(); lf[m] = -1; rf[m] = -1
        return dict(full=(cov.later, cov.raw), flat=(lf, rf))
    def _kc_foam_stop(cov, fm, s):
        if fm is None or os.environ.get("KC_FOAM_MASK", "1") == "0": return          # KC_FOAM_MASK=0: diagnosis only
        cov.later, cov.raw = fm["full"] if (s.get("puff") or s.get("top")) else fm["flat"]
    ns["_kc_foam_init"] = _kc_foam_init; ns["_kc_foam_stop"] = _kc_foam_stop
    def _kc_init(objs, cov, si, sewn_same):
        base = (cov.later > si) | cov.merged(si + 1)
        cnt = np.zeros(base.shape, np.int16); loc = {}
        for o in objs:
            # Rev C: a sheer stipple run (glow / haze) hides nothing: travel laid across its footprint shows as a straight
            # line through the halo (Rev C first build: a 29.7 mm line across the JP glow once the foam mask stopped
            # travel hiding under the puff letters). Travel hops along a run's own piece still use its own halo.
            if o["r"].get("run_pts") and os.environ.get("KC_SHEER_HIDES", "0") != "1": continue
            g = o["r"]["geom"].buffer(0.1); bb = g.bounds
            c0 = max(0, int((bb[0] - cov.x0) * cov.ppm) - 1); r0 = max(0, int((bb[1] - cov.y0) * cov.ppm) - 1)
            c1 = min(cov.W, int((bb[2] - cov.x0) * cov.ppm) + 2); r1 = min(cov.H, int((bb[3] - cov.y0) * cov.ppm) + 2)
            if c1 <= c0 or r1 <= r0: continue
            from PIL import Image, ImageDraw
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

STYLE = "HK-HJ-KCOS-BK"
NAME = "Keep Clean Our Space Hooded Jacket — Washed Black"
SHORT = "KCOS"
SIZES = ["XS", "S", "M", "L", "XL", "XXL", "3XL"]
# badges keep one size per grade; positions follow each size's panel (art_size.py)
GRADE = {"XS": ("A", 0.92), "S": ("A", 0.92), "M": ("B", 1.0), "L": ("B", 1.0), "XL": ("B", 1.0), "XXL": ("C", 1.06), "3XL": ("C", 1.06)}
# Rev H (founder 21 Oct): the BACK carries stars only, same star style as the fronts; the hood stays plain
PIECES = ("FR", "FL", "SR", "SL", "BK")
PIECE_NAME = {"FR": "wearer's right front", "FL": "wearer's left front", "SR": "right sleeve", "SL": "left sleeve", "BK": "back"}
PIECE_CODE = {"FR": "F02", "FL": "F01", "SR": "S01", "SL": "S02", "BK": "B01"}
ELEMENTS = {   # id -> (slug, title, piece)
    "01": ("jp-badge", "宇宙をきれいに badge (JP)", "FR"),
    "02": ("en-badge", "KEEP CLEAN OUR SPACE badge (EN)", "FL"),
    "03": ("cn-badge", "不要世界污染 badge (CN)", "FR"),
    "04": ("kr-oval", "우리들 소중한 우주! oval (KR)", "FL"),
    "05": ("star-field", "Star speckle field", "FR FL SR SL"),
    "06": ("back-stars", "Back star field", "BK"),
}
# Text from the founder's source frame (inputs/reference.png, 19 Oct 2026). Rev D (founder answers, 20 Oct 2026): CN uses
# the Simplified Chinese 污 (不要世界污染, not the source's 汚); KR 우리들 소중한 우주! approved.
TEXT = {"01": "宇宙をきれいに", "02": ("KEEP", "CLEAN", "OUR SPACE"), "03": "不要世界污染", "04": "우리들 소중한 우주!"}
REV_EMB = "Rev H"; REV_GAR = "Rev H"; DATE = "21 Oct 2026"
# Rev D (founder 20 Oct): 3D puff on every sign part that is not a background star. A stroke / part narrower than
# PUFF_MIN_MM stays FLAT (too thin for the foam to dome and be cut cleanly); a glyph puffs only if >= PUFF_GLYPH_SHARE of
# its stroke length is wide enough (no isolated puff bits). House rules/house.yaml puff min_w is 3.0: strokes 2.5-3.0 are
# puffed as PROPOSED and listed for the strike-off (F2). The decision table is written to scene META["puff"].
PUFF_MIN_MM = 2.5
PUFF_HOUSE_MIN_MM = 3.0
PUFF_GLYPH_SHARE = 0.5
CUT_KEEP_MM = 1.0      # house rule 6 (docs/DIGITIZING_PRINCIPLES.md, engine/digitize/rules/house.yaml cut_keep_mm): flat work under puff keeps 1 mm under the edge
