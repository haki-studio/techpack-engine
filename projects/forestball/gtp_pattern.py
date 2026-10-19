"""Garment tech pack Rev B additions: pattern pages (T11–T13), inside view (T14), operations (T15), revision log (T16);
plus pattern-derived BOM consumption used by T6."""
import math, json, os
import numpy as np
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union
from shapely import affinity
from sheet import t, INK, MUTED, RED, ORANGE, GREEN, SW, SH
from render import f
import fbcore
import drum, pattern as PT, pattern_draw as PD, pattern_fb as PO, emb_place as EP
import gtp as GT

SHELL = ["B01", "F01", "F02", "S01", "S02", "K01", "K01", "K02", "P01", "P01", "P03", "P03", "P04"]
def qty_of(pc):
    q = pc.qty.split()[0]
    return 2 if "pair" in pc.qty else int(q)

def consumption(size="M", width=1500.0, eff=0.80):
    g, _ = PT.draft(size); out = {}
    groups = {"Shell": ["B01", "F01", "F02", "S01", "S02", "K01", "K02", "P01", "P03", "P04"], "Collar": ["C01", "C02"],
              "Body lining": ["L01", "L02"], "Sleeve lining": ["L03"], "Pocket bag": ["P02"], "Interlining": ["IC01", "IK01", "IK02", "IP01"]}
    for k, codes in groups.items():
        area = sum(PT.cut_poly(g[c]).area * qty_of(g[c]) for c in codes)
        out[k] = area / (width * eff) / 1000.0           # metres
    out["Hem rib"] = PT.cut_poly(g["R01"]).bounds[3] - PT.cut_poly(g["R01"]).bounds[1]
    out["Cuff rib"] = 2 * (PT.cut_poly(g["R02"]).bounds[3] - PT.cut_poly(g["R02"]).bounds[1])
    return out

def _draw_pieces(o, g, codes, x0, y0, wmax, s, size, em=None, lw=0.5, tm=1.6, gap=4):
    x, y, rowh = x0, y0, 0.0
    for code in codes:
        pc = g[code]; b = PT.cut_poly(pc).bounds; w, h = (b[2]-b[0])*s, (b[3]-b[1])*s
        if x + w > x0 + wmax: x = x0; y += rowh + gap; rowh = 0
        X = (lambda xx0, b0: (lambda q: xx0 + (q - b0)*s))(x, b[0]); Y = (lambda yy0, b1: (lambda q: yy0 + (q - b1)*s))(y, b[1])
        o += PD.piece_svg(pc, X, Y, s, label=True, size=size, emb=(em or {}).get(code, ()), lw=lw, text_mm=tm)
        x += w + gap; rowh = max(rowh, h)
    return y + rowh

def p_pattern_pieces():
    o = GT.header("PATTERN — pieces + cut list (size M, sample size)", "First pattern, drafted from the Drum Island fit chart (T4). Seam allowance included; dashed = sew line; slits = notches; ⊕ = drill holes; pink = embroidery placement.", "T11")
    g, mt = PT.draft("M"); em = PO.emb_marks("M")
    y1 = _draw_pieces(o, g, ["B01", "F01", "F02", "S01"], 12, 30, 190, 0.085, "M", em, lw=0.35, tm=1.4)
    y2 = _draw_pieces(o, g, ["C01", "C02", "K01", "K02", "L01", "L02", "L03"], 12, y1 + 6, 190, 0.06, "M", None, lw=0.28, tm=1.15, gap=3)
    _draw_pieces(o, g, ["R01", "R02", "P01", "P02", "P03", "P04"], 12, y2 + 6, 190, 0.06, "M", None, lw=0.28, tm=1.1, gap=4)
    tx = 206; o.append(t(tx, 31, "CUT LIST — per jacket", 2.3, 700))
    hd = ["Code", "Piece", "Cut", "Material", "Fuse"]; cx = [tx, tx + 9, tx + 36, tx + 47, tx + 73]
    for x_, h in zip(cx, hd): o.append(t(x_, 35.5, h, 1.6, 700, MUTED))
    for i, code in enumerate([c for c in PT.ORDER if not c.startswith("I")]):
        pc = g[code]; y = 39.5 + i*3.5
        if i % 2 == 0: o.append(f'<rect x="{tx-1}" y="{f(y-2.5)}" width="{SW - tx - 11}" height="3.5" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, code, 1.5, 700)); o.append(t(cx[1], y, pc.name.replace(" (wearer's)", "")[:20], 1.5))
        o.append(t(cx[2], y, pc.qty.replace(" (2 pairs)", ""), 1.5)); o.append(t(cx[3], y, pc.material.split(" — ")[0] if "—" in pc.material else pc.material[:16], 1.45))
        o.append(t(cx[4], y, "yes" if pc.fuse else "", 1.5, 600, GREEN))
    y = 39.5 + 18*3.5 + 2
    for i, l in enumerate(["Seam allowance: 1.0 cm; rib joins + body/sleeve hems 0.8; collar edges 0.6.",
                           "Grain: body + sleeves straight grain; collar CB on grain; rib wales across the band height.",
                           "Fusing: woven 60 g/m², cut 3 mm inside the piece (IC01, IK01, IK02, IP01).",
                           "Back is cut whole (not on fold): embroidery 01 is sewn on it flat.",
                           "S02 sleeve left = mirror of S01 (sleeves plain — no embroidery).",
                           "Files: DXF (AAMA layers) per size + all sizes; 1:1 plot PDF for size M."]):
        o.append(t(tx, y + i*3.4, l, 1.5, 400, MUTED))
    o.append(GT.prop(12, SH - 14, "First pattern from the measurement chart — sew a size-M sample and fit it before cutting the size set", 1.7))
    return o

def p_pattern_grade():
    o = GT.header("PATTERN — grade nests + measurement check (XS–3XL)", "Each size drafted from its own fit-chart values (not a fixed grade rule). Measured off the pattern pieces vs the chart; seam walks below.", "T12")
    cols = ["#9C9C9C", "#7E7E7E", "#1A1A1A", "#5A5A5A", "#3A3A3A", "#2A2A2A", "#111111"]
    nests = [("B01", "Back", 0.072, (14, 32)), ("F01", "Front left", 0.072, (64, 32)), ("S01", "Sleeve", 0.072, (92, 32)), ("C02", "Under collar", 0.072, (138, 36))]
    for code, nm, s, (ox, oy) in nests:
        for i, sz in enumerate(PT.SIZES):
            g, mt = PT.draft(sz); pc = g[code]
            # align on CB/CF + hem (body), cap top (sleeve), CB neck (collar)
            sew = pc.sew()
            if code == "B01": ax, ay = 0.0, mt["hem_b"]
            elif code == "F01": ax, ay = 0.0, mt["hem_f"]
            elif code == "S01": ax, ay = 0.0, -mt["cap_h"]
            else: ax, ay = 0.0, 0.0
            X = lambda q: ox + 22*(code != "F01" and code != "C02") + (q - ax)*s + (0 if code != "C02" else 22)
            Y = lambda q: oy + (q - ay)*s + (46 if code in ("B01", "F01") else 0)
            o.append(f'<path d="{PD.path_d([(X(x), Y(y)) for x, y in sew])}" fill="none" stroke="{cols[i]}" stroke-width="{0.22 if sz != "M" else 0.4}"/>')
        o.append(t(ox, oy - 2, f"{nm} — sew lines", 1.7, 700))
    o.append(t(14, 84, "Nests shown at 0.07:1; heaviest line = M. Body aligned on CB/CF + hem seam; sleeve on cap top; collar on CB neck.", 1.55, 400, MUTED))
    # measurement table
    rows = PO.qa_table(); ty = 92
    hd = ["POM", "Description"] + PT.SIZES + ["Tol"]
    cx = [14, 21] + [70 + 15*i for i in range(7)] + [176]
    for x_, h in zip(cx, hd): o.append(t(x_, ty, h, 1.7, 700, MUTED))
    for i, (k, (name, how, vals, tol)) in enumerate(drum.POM_CM.items()):
        y = ty + 4.2 + i*3.7
        if i % 2 == 0: o.append(f'<rect x="13" y="{f(y-2.6)}" width="172" height="3.7" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, k, 1.6, 700, RED)); o.append(t(cx[1], y, name, 1.6))
        for j, sz in enumerate(PT.SIZES):
            pv = rows[sz]["meas"][k] / 10; cv = vals[j]; ok = abs(pv - cv) <= tol + 1e-6
            o.append(t(cx[2 + j], y, f"{pv:.1f}", 1.6, 700 if sz == "M" else 400, INK if ok else RED))
        o.append(t(cx[-1], y, f"±{tol:g}", 1.55, 400, MUTED))
    y = ty + 4.2 + len(drum.POM_CM)*3.7 + 1.5
    o.append(t(14, y, "cm, measured off the pattern (finished, flat). All values within tolerance of the chart; red would flag a miss.", 1.55, 400, MUTED))
    # seam walks (M + extremes)
    wx = 194; o.append(t(wx, 31, "SEAM WALKS (mm)", 2.3, 700))
    hd = ["Seam", "XS", "M", "3XL"]; cxw = [wx, wx + 46, wx + 63, wx + 80]
    for x_, h in zip(cxw, hd): o.append(t(x_, 35.5, h, 1.6, 700, MUTED))
    for i, wk in enumerate(rows["M"]["walks"]):
        y = 39.5 + i*7.2; nm = wk[0]
        if i % 2 == 0: o.append(f'<rect x="{wx-1}" y="{f(y-2.7)}" width="{SW - wx - 11}" height="7.2" fill="#F5F2EC"/>')
        o.append(t(cxw[0], y, nm, 1.5, 600))
        for j, sz in enumerate(("XS", "M", "3XL")):
            _, a, b, tol = rows[sz]["walks"][i]
            if "ratio" in nm: txt = f"{a/b:.2f}"
            elif "ease" in nm: txt = f"+{a-b:.1f}"
            else: txt = f"{a:.0f}/{b:.0f}"
            bad = tol is not None and abs(a - b) > tol
            o.append(t(cxw[1 + j], y, txt, 1.5, 700 if sz == "M" else 400, RED if bad else INK))
        note = {"Sleeve cap vs armhole (ease)": "cap ease, 12 mm all sizes", "Hem rib vs body hem (ratio)": "rib / body hem: 0.94–0.97 (chart sweep)",
                "Cuff rib vs shell sleeve opening (ratio)": "rib / sleeve: 0.80 (rib stretched 25 %)", "Top vs under collar outer": "+2 mm turn of cloth"}.get(nm, "equal within 1–2 mm")
        o.append(t(cxw[0], y + 3.1, note, 1.4, 400, MUTED))
    o.append(t(wx, 39.5 + 10*7.2 + 1, "a/b = first seam / its partner. Cap height ≈ 9.8–10.7 cm.", 1.45, 400, MUTED))
    return o

def p_pattern_emb():
    o = GT.header("PATTERN — embroidery placement per size + keep-out check", "Placement is drawn on the pattern pieces (DXF layer 8: art outline + box + centre ⊕ = DST origin / needle start). Position = art-box corner on the sew-line coordinates.", "T13")
    OL = EP.outlines()
    hd = ["Size", "Art", "01 back: box x / y (from CB, CB neck)", "02R x / y (CF, neck)", "02L x / y", "Licensed box x / y (B01)", "Keep-outs"]
    cx = [12, 22, 31, 92, 132, 172, 226]
    for x_, h in zip(cx, hd): o.append(t(x_, 31, h, 1.6, 700, MUTED))
    allok = True
    for i, sz in enumerate(PT.SIZES):
        pl, g, mt = EP.place(sz, OL); c = EP.clearances(sz, OL); c.pop("nudge")
        y = 36 + i*5.2
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3.2)}" width="{SW-22}" height="5.2" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, sz, 1.8, 700)); o.append(t(cx[1], y, EP.GRADE[sz][0], 1.8, 700, RED))
        def bx(e): b = pl[e][1].bounds; return f"{b[0]:+.0f}…{b[2]:+.0f} / {b[1]:.0f}…{b[3]:.0f}"
        for j, e in enumerate(("back", "02R", "02L")):
            o.append(t(cx[2 + j], y, bx(e), 1.5))
        pb = pl["_ph"].bounds; o.append(t(cx[5], y, f"{pb[0]:+.0f}…{pb[2]:+.0f} / {pb[1]:.0f}…{pb[3]:.0f}", 1.5, 600, RED))
        bad = [f"{e} {k} {v:.1f}" for e, d in c.items() for k, v in d.items() if k in EP.MIN.get(e, {}) and v < EP.MIN[e][k] - 0.6]
        allok &= not bad
        o.append(t(cx[6], y, "all pass" if not bad else "; ".join(bad)[:40], 1.5, 700, GREEN if not bad else RED))
    y = 36 + 7*5.2 + 2
    rules = ["Keep-outs checked on every size against that size's pattern (minimum, mm): side seams 15 · CF/zip 15 · front armhole + shoulder 15 ·",
             "hem-rib seam 10 · welt box 6 · back armholes + shoulders 15 · back collar fall 6. Measured from the actual art outline, not the box.",
             "One stitch file per art grade (A/B/C) per piece, positioned per size as above (smallest nudge that restores every keep-out).",
             "Licensed box (red) = placeholder on B01, DXF layer 8 'LICENSED FIGURE placeholder'; it grades + moves with the 01 art."]
    for i, l in enumerate(rules): o.append(t(12, y + i*3.4, l, 1.55, 400, MUTED))
    # picture: XS and 3XL back + front left with art
    em_xs = PO.emb_marks("XS"); em_3 = PO.emb_marks("3XL")
    gx, _ = PT.draft("XS"); g3, _ = PT.draft("3XL")
    s = 0.068; yy = y + 17
    for k, (gg, em, lab, ox) in enumerate(((gx, em_xs, "XS", 12), (g3, em_3, "3XL", 152))):
        xx = ox
        for code in ("B01", "F02", "F01"):
            pc = gg[code]; b = PT.cut_poly(pc).bounds
            X = (lambda x0, b0: (lambda q: x0 + (q - b0)*s))(xx, b[0]); Y = (lambda b1: (lambda q: yy + (q - b1)*s))(b[1])
            o += PD.piece_svg(pc, X, Y, s, label=False, emb=em.get(code, ()), lw=0.3)
            xx += (b[2]-b[0])*s + 3
        o.append(t(ox, yy - 2, f"{lab} (grade {EP.GRADE[lab][0]}): back, front R, front L", 1.7, 700))
    return o

# ---------------------------------------------------------------- inside view
def p_inside():
    o = GT.header("INSIDE VIEW — lining, facings, pockets, labels (size M)", "Jacket opened flat, inside facing up. Drawn from the pattern pieces. Shell facing = green duck; flannel = check; twill bags dashed.", "T14")
    g, mt = PT.draft("M"); s = 0.125; ox, oy = 182, 52
    X = lambda x: ox + x*s; Y = lambda y: oy + (y + 40)*s
    sand, flan, taff, cord = "#8C9A8D", "#B9C2B5", "#9A9A9A", "#1F1F1F"
    defs = ('<defs><pattern id="chk" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="4" fill="#B9C2B5"/>'
            '<path d="M0 0H2V2H0Z M2 2H4V4H2Z" fill="#8E9C8A" opacity="0.6"/></pattern></defs>')
    o.append(defs)
    P = lambda pts: PD.path_d([(X(x), Y(y)) for x, y in pts])
    # back (centre), fronts opened out to each side — drawn as mirrored outlines around the back
    back = g["B01"].sew(); o.append(f'<path d="{P(back)}" fill="url(#chk)" stroke="{INK}" stroke-width="0.3"/>')
    bf = g["K02"].sew(); o.append(f'<path d="{P(bf)}" fill="{sand}" stroke="{INK}" stroke-width="0.3"/>')
    o.append(f'<path d="M{f(X(-10))} {f(Y(PT.BFACING_D))} V{f(Y(PT.BFACING_D + 50))} M{f(X(10))} {f(Y(PT.BFACING_D))} V{f(Y(PT.BFACING_D + 50))}" stroke="{RED}" stroke-width="0.25" stroke-dasharray="1 0.6"/>')
    for side, code in ((1, "F01"), (-1, "F02")):
        # front laid open: mirror about the side seam so the CF ends up on the outside
        dx = side * 2 * mt["block"].chest2
        fr = [(dx - x if side > 0 else dx - x, y - (mt["hem_f"] - mt["hem_b"])) for x, y in g[code].sew()]
        o.append(f'<path d="{P(fr)}" fill="url(#chk)" stroke="{INK}" stroke-width="0.3"/>')
        fc = [(dx - side*x, y - (mt["hem_f"] - mt["hem_b"])) for x, y in g["K01"].sew()]
        o.append(f'<path d="{P(fc)}" fill="{sand}" stroke="{INK}" stroke-width="0.3"/>')
        # pocket bag behind the welt
        wc = mt["welt_c"]; u = mt["welt_u"]; dyh = mt["hem_f"] - mt["hem_b"]
        m0 = (wc[0] - u[0]*(PT.WELT_L/2 + 20), wc[1] - u[1]*(PT.WELT_L/2 + 20)); m1 = (wc[0] + u[0]*(PT.WELT_L/2 + 20), wc[1] + u[1]*(PT.WELT_L/2 + 20))
        yb = max(m0[1], m1[1]) + 110
        bag = Polygon([m0, m1, (m1[0], yb), (m0[0], yb)]).buffer(8).buffer(-8)
        bag = affinity.translate(affinity.scale(bag, -side, 1, origin=(0, 0)), dx, -dyh)
        o.append(f'<path d="{P(list(bag.exterior.coords))}" fill="none" stroke="{INK}" stroke-width="0.25" stroke-dasharray="1.2 0.8"/>')
        wl = [(dx - side*x, y - dyh) for x, y in g["F01"].internal[0][1]]
        o.append(f'<path d="{P(wl)}" fill="{sand}" stroke="{INK}" stroke-width="0.25"/>')
        # zip along CF
        cfx = dx; o.append(f'<line x1="{f(X(cfx))}" y1="{f(Y(-(mt["hem_f"] - mt["hem_b"]) ))}" x2="{f(X(cfx))}" y2="{f(Y(mt["hem_b"]))}" stroke="#9A7A30" stroke-width="0.9"/>')
    # collar along the neck (inside: under collar visible)
    o.append(f'<path d="{P([(x, y - 45) for x, y in g["C02"].sew()])}" fill="{cord}" stroke="{INK}" stroke-width="0.3" opacity="0.9"/>')
    o.append(t(X(0), Y(-150), "collar (under collar shown, laid up)", 1.5, 400, MUTED, "middle"))
    # hem rib
    hw = 2 * mt["block"].chest2
    o.append(f'<rect x="{f(X(-hw))}" y="{f(Y(mt["hem_b"]))}" width="{f(2*hw*s)}" height="{f(PT.HEM_RIB*s)}" fill="#2A2A2A" stroke="{INK}" stroke-width="0.3"/>')
    # labels
    ly = 12
    o.append(f'<rect x="{f(X(-35))}" y="{f(Y(ly))}" width="{f(70*s)}" height="{f(20*s)}" fill="#111" />' + t(X(0), Y(ly) + 2.4, "HAKI", 1.6, 700, "#F2E8D5", "middle"))
    o.append(f'<rect x="{f(X(-10))}" y="{f(Y(ly + 22))}" width="{f(20*s)}" height="{f(15*s)}" fill="#333"/>')
    cl_x = mt["block"].chest2 + 6
    o.append(f'<rect x="{f(X(cl_x))}" y="{f(Y(mt["hem_b"] - 100))}" width="{f(40*s)}" height="{f(60*s)}" fill="#FFF" stroke="{INK}" stroke-width="0.25"/>')
    o.append(f'<rect x="{f(X(-6))}" y="{f(Y(-34))}" width="{f(12*s)}" height="{f(28*s)}" fill="none" stroke="{INK}" stroke-width="0.3"/>')
    # callouts
    notes = [("1", "Back neck facing — shell canvas, fused; main + size label 1 cm below the collar seam.", X(0), Y(30)),
             ("2", "Hanger loop — self fabric 6 cm, caught in the collar seam at CB.", X(0), Y(-25)),
             ("3", "Back lining — cotton flannel, 2 cm CB pleat stitched 5 cm down from the facing.", X(0), Y(250)),
             ("4", "Front facing — shell canvas 6 cm at CF, 4 cm on the shoulder; zip tape between shell + facing.", X(2*mt["block"].chest2 - 30), Y(250)),
             ("5", "Front lining — flannel; joins facing, shoulder, armhole, side; bagged to the hem-rib seam.", X(2*mt["block"].chest2 - 170), Y(150)),
             ("6", "Pocket bags — 8 oz twill, hang from the welt, free between shell + lining, edges bound.", X(-2*mt["block"].chest2 + 150), Y(420)),
             ("7", "Care / content label — wearer's left side seam, 10 cm above the hem-rib seam.", X(cl_x + 20), Y(mt["hem_b"] - 70)),
             ("8", "Embroidery backing — cutaway trimmed to 5 mm, hidden by the lining (back + both fronts).", X(-150), Y(450)),
             ("9", "Sleeve lining — polyester taffeta 210T (lets the arm slide); joined at armhole + cuff-rib seam (sleeves not drawn).", X(-mt["block"].chest2 + 25), Y(120))]
    for i, (n, txt, px, py) in enumerate(notes):
        tx_, ty_ = 14, 36 + i*9.5
        o.append(GT.callout(px, py, n, px + 0.001, py)[:0] if False else "")
        o.append(f'<circle cx="{f(px)}" cy="{f(py)}" r="2.1" fill="#FFF" stroke="{INK}" stroke-width="0.25"/>' + t(px, py + 0.8, n, 1.8, 700, INK, "middle"))
        o.append(f'<circle cx="{f(tx_ + 2)}" cy="{f(ty_ - 0.7)}" r="2.0" fill="#FFF" stroke="{INK}" stroke-width="0.25"/>' + t(tx_ + 2, ty_, n, 1.7, 700, INK, "middle"))
        words = txt.replace("&", "+").split(); line, lines = "", []
        for w_ in words:
            if len(line) + len(w_) > 40: lines.append(line); line = w_
            else: line = (line + " " + w_).strip()
        lines.append(line)
        for j, l in enumerate(lines): o.append(t(tx_ + 6, ty_ + j*2.7, l, 1.65))
    o.append(GT.prop(14, SH - 14, "Lining fabrics, pleat, pocket-bag finish and label positions are proposals (T10)", 1.7))
    return o

# ---------------------------------------------------------------- operations / SMV
OPS = [("Cutting", "Cut shell, collar, lining, rib, pocketing, fusing; drill welt + embroidery marks", "Cutting table", 6.0),
       ("Fusing", "Fuse top collar, facings, back neck facing, welts", "Fusing press", 2.5),
       ("Embroidery", "01 back, 02R, 02L — flat on cut pieces; licensed figure by factory (machine time separate, see G4)", "Multi-head (12 colours/file)", 8.0),
       ("Embroidery finish", "Trim backing to 5 mm, remove registration crosses if visible (split files), press from wrong side", "Hand / press", 6.0),
       ("Welt pockets", "Mark, set welt + bags both fronts, bartack ×4", "Lockstitch + bartack", 9.0),
       ("Shoulders", "Join shoulders (5-thread), press to back, 6 mm topstitch", "Safety stitch + lockstitch", 2.5),
       ("Sleeves", "Set sleeves; 6 mm armhole topstitch on body", "Safety stitch + lockstitch", 6.0),
       ("Side + underarm", "Close side + underarm seams in one pass", "Safety stitch", 2.5),
       ("Collar", "Make collar (top + under), turn, press, 6 mm edge topstitch", "Lockstitch", 6.5),
       ("Collar attach", "Attach collar sandwiched by facings; stitch-in-ditch back neck", "Lockstitch", 4.5),
       ("Zip", "Set CF zip between shell + facing, zip garage, 10 mm topstitch", "Lockstitch", 7.0),
       ("Lining", "Assemble lining (overlock), back pleat, sleeves", "4-thread overlock", 7.0),
       ("Ribs", "Join cuff ribs, attach cuffs; attach hem rib, 5 mm topstitch", "Overlock + lockstitch", 6.0),
       ("Bagging", "Bag lining to facings + rib seams; close turning gap", "Lockstitch", 5.0),
       ("Labels + loop", "Main/size label, care label, hanger loop", "Lockstitch", 2.0),
       ("Finishing", "Trim threads, press, QC (T8), hangtag, fold, polybag", "Hand / press", 8.0)]

def p_operations():
    o = GT.header("OPERATIONS — sewing sequence + time estimate", "Standard minute values (SMV) are Haki estimates for quoting, not time studies. Embroidery machine run time is separate (G4).", "T15")
    hd = ["#", "Operation", "Detail", "Machine", "SMV"]; cx = [12, 18, 46, 190, 250]
    for x_, h in zip(cx, hd): o.append(t(x_, 31, h, 1.8, 700, MUTED))
    for i, (op, det, mc, smv) in enumerate(OPS):
        y = 36 + i*4.6
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3.1)}" width="{SW-22}" height="4.6" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, f"{i+1:02d}", 1.7, 700)); o.append(t(cx[1], y, op, 1.8, 600)); o.append(t(cx[2], y, det, 1.7))
        o.append(t(cx[3], y, mc, 1.7, 400, MUTED)); o.append(t(cx[4], y, f"{smv:.1f}", 1.8, 600))
    tot = sum(x[3] for x in OPS); y = 36 + len(OPS)*4.6 + 1
    o.append(t(cx[3], y, "TOTAL (sewing + finishing)", 1.8, 700)); o.append(t(cx[4], y, f"{tot:.0f} min", 1.8, 700))
    import factory
    cur = json.load(open("dst_current.json")) if os.path.exists("dst_current.json") else {}
    st = sum(v["stitches"] for k, v in cur.items() if v)
    mh = sum(factory.machine_hours(v["stitches"], None, trims=v["trims_dst"], colour_changes=v["stops"] - 1) for k, v in cur.items() if v)
    o.append(t(12, y + 6, f"Embroidery machine time, size M: {st:,} stitches → ≈ {mh:.1f} h per head (factory.machine_hours: spm + trims + colour changes; G4) + 6 hoopings; licensed figure extra.", 1.75, 600))
    o.append(GT.prop(12, y + 10, "SMVs are estimates — replace with the factory's time study at the sample stage", 1.75))
    return o

# ---------------------------------------------------------------- revision log + sample tracker
REVS = [("Garment Rev A", "16 Oct 2026", "Forestball pack on the Drum Island pattern (unchanged, XS–3XL): flats, details, size chart, grading, BOM, construction, labels, "
                                          "colourway, pattern pages, inside view, operations. Black corduroy collar + black ribs; plain sleeves."),
        ("Embroidery Rev A", "16 Oct 2026", "01 back scene (sheer light rays, mossy branch + trunk, stream, mossy rocks, grass) with the LICENSED stream figure as a "
                                             "placeholder box only; 02R/02L chest mossy branch split at the zip, hanging moss on 02R. Files per grade A/B/C, back 4 × 360² splits."),
        ("Garment + embroidery Rev B", "16 Oct 2026", "Reviewer fixes: per-size hooping plan (G6), F1 factory requests, keep-outs exact (≥ 15.0), zip continuity, 12 colours/file "
                                                       "(factory limit), DST read-back numbers; fidelity-first art in the close-up stitch vocabulary."),
        ("Garment + embroidery Rev C", "17 Oct 2026", "Art TRACED from the registered close-ups (back: close-up a; 02R: close-up b) + mockup x4 where no close-up covers "
                                                       "(LESSONS A12); light rays traced as 5 broad sheer bands (~28 % cover); ripple rings round the placeholder; thread "
                                                       "codes re-checked (untrusted catalogue names dropped, one code per thread); merged pack rebuilt from the current specs.")]
SAMPLES = ["Proto / fit sample (M)", "Embroidery strike-off (sew-out on 12 oz duck)", "Lab dips: shell, corduroy, ribs, lining", "Size set (XS, M, 3XL)", "PP sample", "TOP (top of production)"]

def p_revisions():
    o = GT.header("REVISION LOG + SAMPLE TRACKER", "Every change to this pack, newest last. The tracker is filled in by Haki + the factory at each sample round.", "T16")
    hd = ["Revision", "Date", "Changes"]; cx = [12, 44, 66]
    for x_, h in zip(cx, hd): o.append(t(x_, 31, h, 1.8, 700, MUTED))
    y = 36
    for rv, dt, ch in REVS:
        words = ch.split(); line, lines = "", []
        for w_ in words:
            if len(line) + len(w_) > 150: lines.append(line); line = w_
            else: line = (line + " " + w_).strip()
        lines.append(line)
        o.append(t(cx[0], y, rv, 1.8, 700)); o.append(t(cx[1], y, dt, 1.7))
        for j, l in enumerate(lines): o.append(t(cx[2], y + j*3.2, l, 1.7))
        y += 3.2*len(lines) + 2.6
    y += 4; o.append(t(12, y, "SAMPLE TRACKER", 2.4, 700)); y += 5
    hd = ["Stage", "Requested", "Received", "Approved / comments", "By"]; cx2 = [12, 92, 122, 152, 262]
    for x_, h in zip(cx2, hd): o.append(t(x_, y, h, 1.8, 700, MUTED))
    for i, sname in enumerate(SAMPLES):
        yy = y + 6 + i*9
        o.append(f'<rect x="11" y="{f(yy-4)}" width="{SW-22}" height="9" fill="{"#F5F2EC" if i % 2 == 0 else "#FFFFFF"}" stroke="#DDD" stroke-width="0.2"/>')
        o.append(t(cx2[0], yy, sname, 1.8, 600))
        for x_ in cx2[1:]: o.append(f'<line x1="{f(x_ - 2)}" y1="{f(yy - 4)}" x2="{f(x_ - 2)}" y2="{f(yy + 5)}" stroke="#DDD" stroke-width="0.2"/>')
    return o
