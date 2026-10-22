"""Boxy zip hoodie BLOCK — blank fit-sample pack: pattern QA, DXF (per size + all), 1:1 plot PDF (M), tech pack PDF.
usage: source scripts/env.sh projects/zip-hoodie-block && python3 build.py"""
import os, math, json, shutil, subprocess
import cairosvg
from pypdf import PdfWriter, PdfReader
import sheet as SHT
from sheet import t, doc, INK, MUTED, RED, GREEN, SW, SH, dim_h, dim_v
from render import f
import drum, pattern as PT, pattern_out as PO, pattern_draw as PD, hoodie as HD, hflat as HF
import labelsheet as LS

STYLE = "HK-HD-ZIP-BLK"; REV = "Rev A"; DATE = "16 Oct 2026"; NAME = "Boxy Zip Hoodie — block"
SHT.FOOT = f"HAKI STUDIOS · {NAME} · {STYLE} · FIT-SAMPLE TECH PACK · {REV} · {DATE}"
PROP = "#8A5A00"; ALT = "#F5F2EC"
SHELL_MAT = "12 oz cotton duck canvas, washed (colour per design)"   # a design sets its own (no fibre % = care label MISSING, LESSONS D7)
OUT = "out"; os.makedirs(f"{OUT}/pattern", exist_ok=True); os.makedirs(f"{OUT}/pages", exist_ok=True)
SIZES = HD.SIZES

def prop(x, y, s, size=1.85): return t(x, y, s + "  [proposed — confirm]", size, 600, PROP)
def H(title, sub, page): return SHT.header(title, sub, page)
def flat_g(body, b, ox, oy, s): return f'<g transform="translate({f(ox - b[0]*s)} {f(oy - b[1]*s)}) scale({f(s)})">{body}</g>'
def qty_of(pc):
    q = pc.qty.split(); return int(q[0]) * (2 if q[1:2] == ["pair"] else 1)     # "1 pair" = 2 pieces; "4 (2 pairs)" = 4

# ---------------------------------------------------------------- data (everything on the pages is read from the pattern)
G = {sz: HD.draft(sz) for sz in SIZES}
MEAS = {sz: HD.measure(sz) for sz in SIZES}
CH = HD.chart()
CHECK = {sz: all(abs(MEAS[sz][0][k] / 10 - CH[k][2][SIZES.index(sz)]) <= CH[k][3] for k in CH) for sz in SIZES}
WALKS_OK = {sz: all(tol is None or abs(a - b) <= tol for _, a, b, tol in MEAS[sz][1]) for sz in SIZES}
SHAPE_OK = {sz: all(c[1] for c in HD.shape_checks(sz)) for sz in SIZES}
gM, mM = G["M"]

def area_m2(codes, g):
    return sum(PT.cut_poly(g[c]).area * qty_of(g[c]) for c in codes) / 1e6

# ---------------------------------------------------------------- pages
def p_cover(index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>', t(14, 22, "HAKI STUDIOS", 3.0, 700, MUTED), t(14, 34, NAME, 7.2, 700),
         t(14, 41.5, f"Style {STYLE} · {REV} · {DATE} · sizes XS–3XL · base size M · all dimensions cm unless marked mm · BLANK fit sample (no embroidery)", 2.5, 400, MUTED),
         f'<line x1="14" y1="45" x2="{SW-14}" y2="45" stroke="{INK}" stroke-width="0.4"/>']
    F = HF.Flat("M")
    for i, (fn, back, lab) in enumerate(((HF.draw_front, False, "FRONT"), (HF.draw_back, True, "BACK"))):
        b = HF.bounds(F, back); s = 88 / (b[2] - b[0]); ox = 14 + i * 96
        o.append(flat_g(fn(F), b, ox, 52, s)); o.append(t(ox, 52 + (b[3] - b[1]) * s + 5, lab, 2.2, 700))
    ix = 206; o.append(t(ix, 56, "CONTENTS", 2.8, 700)); y = 62
    for name, pg in index: o.append(t(ix, y, name, 1.95)); o.append(t(SW - 14, y, str(pg), 1.95, 600, MUTED, "end")); y += 3.9
    y += 3; o.append(t(ix, y, "KEY SPECS", 2.4, 700)); y += 4.6
    for a, b_, p in [("Body + sleeve", "Drum Island jacket — approved fit, unchanged", False), ("Hood", "3 panels, sherpa-lined, no drawcord", True),
                     ("Hem / cuffs", "self fabric + elastic (5.5 / 5 cm)", True), ("Zip", "2-way separating, YKK #5 metal", True),
                     ("Shell", "12 oz cotton duck, washed (per design)", True), ("Lining", "flannel body · taffeta sleeves · sherpa hood", True),
                     ("Pattern", "XS–3XL, DXF (AAMA) + 1:1 plot", False)]:
        o.append(t(ix, y, a, 1.95, 400, MUTED)); o.append(t(ix + 23, y, b_, 1.9, 600, PROP if p else INK)); y += 3.8
    y += 4
    for l in ["This block is the silhouette for every Haki zip hoodie: the approved Drum Island jacket body",
              "and sleeve with a hood and elastic bands. Designs add embroidery on top; the pattern stays.",
              "Sew this blank in M (+ XS and 3XL if possible) and approve the fit before any embroidered sample."]:
        o.append(t(ix, y, l, 1.6, 400, INK)); y += 3.1
    o.append(t(SW - 14, SH - 8, SHT.FOOT, 1.8, 400, MUTED, "end"))
    return o

NOTES = [("1", "Hood: 3 panels — side pair + 10 cm centre panel. Shell outside, sherpa lining inside, bagged at the face edge; 6 mm topstitch. No drawcord.", True),
         ("2", "Hood neck: shell hood to body neckline, sherpa hood to front facings + back neck facing — neck seam fully enclosed. Notch at HPS = shoulder seam.", False),
         ("3", "Zip: 2-way separating, YKK #5 metal, antique brass, hem-band edge to CF neck; top stop 5 mm below the hood face edge.", True),
         ("4", "Welt pockets, pocket bags, shoulder / armhole / side seams, facings and body lining: exactly as the Drum Island jacket.", False),
         ("5", f"Hem band: self fabric, {HD.hcm('S','M')/10:.1f} cm finished, folded; {HD.EL_HEM_W/10:.0f} cm elastic, flat {HD.FLAT/10:.0f} cm each side of the zip; one piece CF to CF.", True),
         ("6", f"Cuff band: self fabric, {HD.hcm('T','M')/10:.1f} cm finished, folded, closed into a loop; {HD.EL_CUFF_W/10:.1f} cm elastic loop.", True),
         ("7", "Lining: cotton flannel body (plaid), polyester taffeta sleeves; hood fully lined in sherpa.", True),
         ("8", "Main + size label on the back neck facing, 1 cm below the hood seam (Haki standard main label, T6b).", False)]

def p_flats():
    o = H("FLATS + CONSTRUCTION", "Size M, front and back. Body and sleeve are the approved Drum Island jacket; numbered notes are the hoodie changes.", "T2")
    F = HF.Flat("M")
    pos = []
    for i, (fn, back) in enumerate(((HF.draw_front, False), (HF.draw_back, True))):
        b = HF.bounds(F, back); s = 92 / (b[2] - b[0]); ox = 12 + i * 100; o.append(flat_g(fn(F), b, ox, 32, s)); pos.append((b, s, ox))
    def cxy(i, x, y): b, s, ox = pos[i]; return ox + (x - b[0]) * s, 32 + (y - b[1]) * s
    calls = [(0, (0, -(HD.hcm("Q", "M") - 120)), "1"), (0, (F.b.neck2 * 0.6, F.fnd * 0.55), "2"), (0, (0, F.hem_seam - 120), "3"),
             (0, (240, 420), "4"), (0, (-200, F.hem_seam + 25), "5"), (1, (-F.cuff_out[0] + 30, F.cuff_out[1] - 20), "6"), (1, (0, 280), "7"), (1, (0, 40), "8")]
    for i, (x, y), n in calls:
        X, Y = cxy(i, x, y)
        o.append(f'<circle cx="{f(X)}" cy="{f(Y)}" r="2.4" fill="#FFFFFF" stroke="{INK}" stroke-width="0.3"/>' + t(X, Y + 0.85, n, 2.1, 700, INK, "middle"))
    y = 34; tx = 214
    for n, s_, p in NOTES:
        o.append(f'<circle cx="{tx}" cy="{f(y - 0.8)}" r="2.0" fill="#FFFFFF" stroke="{INK}" stroke-width="0.25"/>' + t(tx, y, n, 1.8, 700, INK, "middle"))
        words = s_.split(); line, lines = "", []
        for w in words:
            if len(line) + len(w) > 46: lines.append(line); line = w
            else: line = (line + " " + w).strip()
        lines.append(line)
        for j, l in enumerate(lines): o.append(t(tx + 4, y + j * 3.1, l, 1.65, 400, PROP if p else INK))
        y += 3.1 * len(lines) + 2.4
    o.append(t(tx, y + 2, "Amber = proposed by Haki tech design — confirm.", 1.6, 600, PROP))
    return o

def p_pom():
    o = H("SIZE CHART + MEASUREMENT CHECK", "Chart in cm. Body + sleeve rows are the approved Drum Island chart, unchanged. Hood + band rows are new (proposed). ½ = half measurement, flat.", "T3")
    F = HF.Flat("M"); b = HF.bounds(F); s = 62 / (b[2] - b[0]); ox, oy = 12, 34
    o.append(flat_g(HF.draw_front(F), b, ox, oy, s))
    X = lambda x: ox + (x - b[0]) * s; Y = lambda y: oy + (y - b[1]) * s
    o.append(dim_v(Y(0), Y(F.hem_edge), X(F.ua[0] + 22), "A", 1.8, side=1))
    o.append(dim_h(X(-F.ua[0]), X(F.ua[0]), Y(F.ua[1] + 6), "B", 1.8))
    o.append(dim_h(X(-F.sp[0]), X(F.sp[0]), Y(F.sp[1] - 4), "C", 1.8))
    o.append(dim_v(Y(-(HD.hcm("Q", "M") - 70)), Y(0), X(-F.b.neck2 - 90), "Q", 1.8))
    o.append(dim_v(Y(F.hem_seam), Y(F.hem_edge), X(-F.sweep2 - 14), "S", 1.6))
    tb = 12; ty = oy + (b[3] - b[1]) * s + 8
    for j, l in enumerate(["D ½ hem, relaxed (elastic) · E armhole, straight · F ½ bicep", "G sleeve length incl. cuff band · H ½ cuff, relaxed (elastic)",
                           "J neck width · K / L front / back neck drop · P shoulder fwd", "R hood width · T cuff band height"]):
        o.append(t(tb, ty + j * 3, l, 1.45, 400, MUTED))
    hd = ["", "Point of measure", "How measured"] + SIZES + ["Tol", "Source"]; cx = [80, 85, 128, 168, 177, 186, 195, 204, 213, 223, 233, 243]
    for x_, h_ in zip(cx, hd): o.append(t(x_, 31, h_, 1.6, 700, MUTED))
    order = ["A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "P", "Q", "R", "S", "T"]
    for i, k in enumerate(order):
        nm, how, vals, tol, src = CH[k]; y = 35.5 + i * 4.1; pr = src == "PROPOSED"
        if i % 2 == 0: o.append(f'<rect x="79" y="{f(y - 2.9)}" width="{SW - 90}" height="4.1" fill="{ALT}"/>')
        col = PROP if pr else INK
        o.append(t(cx[0], y, k, 1.7, 700, col)); o.append(t(cx[1], y, nm[:34], 1.55, 600, col)); o.append(t(cx[2], y, how[:52], 1.3, 400, MUTED))
        for j, v in enumerate(vals): o.append(t(cx[3 + j], y, f"{v:g}", 1.55, 600 if SIZES[j] == "M" else 400, col))
        o.append(t(cx[10], y, f"±{tol:g}", 1.45, 400, MUTED)); o.append(t(cx[11], y, "proposed" if pr else "jacket", 1.45, 600, col))
    y = 35.5 + len(order) * 4.1 + 4
    o.append(t(80, y, "PATTERN CHECK — every size measured off the drafted pattern pieces vs this chart", 1.9, 700)); y += 4.2
    for j, sz in enumerate(SIZES):
        ok = CHECK[sz] and WALKS_OK[sz] and SHAPE_OK[sz]
        o.append(t(cx[3 + j], y, "pass" if ok else "FAIL", 1.6, 700, GREEN if ok else RED))
    o.append(t(80, y, "chart · seam walks · shape checks", 1.5, 400, MUTED))
    y += 6
    for l in ["Hood height (Q) and width (R) include 1.5 cm for the sherpa pile (~8 mm) — an unlined hood would be 1.5 cm smaller.",
              "D and H are relaxed: the elastic sets them. Extended (elastic stretched) = the body hem / sleeve opening of the jacket.",
              "Grading: body + sleeve per the jacket chart; hood +0.5 cm height and width per size."]:
        o.append(t(80, y, l, 1.55, 400, MUTED)); y += 3.2
    return o

def _draw(o, g, codes, x0, y0, wmax, s, lw=0.3, tm=1.2, gap=4):
    x, y, rowh = x0, y0, 0.0
    for code in codes:
        pc = g[code]; b = PT.cut_poly(pc).bounds; w, h = (b[2] - b[0]) * s, (b[3] - b[1]) * s
        if x + w > x0 + wmax: x = x0; y += rowh + gap; rowh = 0
        X = (lambda xx0, b0: (lambda q: xx0 + (q - b0) * s))(x, b[0]); Y = (lambda yy0, b1: (lambda q: yy0 + (q - b1) * s))(y, b[1])
        o += PD.piece_svg(pc, X, Y, s, label=True, size="M", lw=lw, text_mm=tm)
        x += w + gap; rowh = max(rowh, h)
    return y + rowh

def p_pieces():
    o = H("PATTERN — pieces + cut list (size M)", "Seam allowance included; dashed = sew line; slits = notches; ⊕ = drill holes. Body, sleeve, facings, lining = the jacket pattern.", "T4")
    y1 = _draw(o, gM, ["B01", "F01", "F02", "S01"], 12, 30, 190, 0.08, 0.32, 1.3)
    y2 = _draw(o, gM, ["H01", "H02", "H03", "H04", "K01", "K02", "L01", "L02", "L03"], 12, y1 + 5, 190, 0.055, 0.26, 0.85, 9)
    _draw(o, gM, ["R01", "R02", "P01", "P02", "P03", "P04"], 12, y2 + 5, 190, 0.055, 0.26, 1.0, 4)
    tx = 206; o.append(t(tx, 31, "CUT LIST — per hoodie", 2.3, 700))
    hd = ["Code", "Piece", "Cut", "Material", "Fuse"]; cx = [tx, tx + 9, tx + 37, tx + 48, tx + 76]
    for x_, h_ in zip(cx, hd): o.append(t(x_, 35.5, h_, 1.55, 700, MUTED))
    rows = [c for c in HD.ORDER if not c.startswith("I")]
    for i, code in enumerate(rows):
        pc = gM[code]; y = 39.5 + i * 3.4; new = code.startswith("H") or code in ("R01", "R02")
        if i % 2 == 0: o.append(f'<rect x="{tx - 1}" y="{f(y - 2.4)}" width="{SW - tx - 11}" height="3.4" fill="{ALT}"/>')
        col = PROP if new else INK
        o.append(t(cx[0], y, code, 1.45, 700, col)); o.append(t(cx[1], y, pc.name.replace(" (wearer's)", "")[:21], 1.42, 400, col))
        o.append(t(cx[2], y, pc.qty.replace(" (2 pairs)", ""), 1.42)); o.append(t(cx[3], y, pc.material.split(" — ")[0][:16], 1.4))
        o.append(t(cx[4], y, "yes" if pc.fuse else "", 1.42, 600, GREEN))
    y = 39.5 + len(rows) * 3.4 + 2
    for l in ["Amber = new for the hoodie; everything else is the jacket pattern.", "Removed from the jacket: collar (C01, C02, IC01) and rib (old R01/R02).",
              "SA 1.0 cm; band joins + hems 0.8; hood face edge 0.6.", "Hood lining (H03/H04) = shell hood pieces, cut in sherpa.",
              "Files: DXF per size + all sizes (AAMA layers), 1:1 plot PDF size M."]:
        o.append(t(tx, y, l, 1.45, 400, MUTED)); y += 3.2
    return o

def p_hood():
    o = H("HOOD + BANDS — detail and per-size table", "Hood side + centre panel at 1:4 (size M) with seam lengths; elastic and band lengths per size. All values read from the pattern.", "T5")
    s = 0.25; Hd = mM["hood"]
    for code, ox, oy in (("H01", 18, 40), ("H02", 112, 40)):
        pc = gM[code]; b = PT.cut_poly(pc).bounds
        X = (lambda b0: (lambda q: ox + (q - b0) * s))(b[0]); Y = (lambda b1: (lambda q: oy + (q - b1) * s))(b[1])
        o += PD.piece_svg(pc, X, Y, s, label=True, size="M", lw=0.4, text_mm=1.6)
        if code == "H01":
            for e in pc.edges:
                p, _ = PT.at(e.pts, e.length / 2)
                o.append(t(X(p[0]) + (3 if e.name != "face edge" else -3), Y(p[1]) + (4 if e.name == "neck" else 0), f"{e.name} {e.length/10:.1f}", 1.5, 600, "#0A84D6", "start" if e.name != "face edge" else "end"))
        else:
            o.append(t(ox + HD.CW * s + 8, oy + 20, f"{HD.CW/10:.0f} × {Hd['seam']/10:.1f} cm", 1.6, 600, "#0A84D6"))
    hd = ["Size", "Q hood ht", "R hood wd", "Side neck", "Centre seam", "Face edge", "Hem band cut", "Hem elastic", "Cuff band cut", "Cuff elastic", "Zip"]
    cx = [150, 160, 172, 184, 196, 209, 221, 236, 250, 264, 278]
    o.append(t(150, 33, "PER SIZE (cm) — cut lengths are sew-line lengths; elastic = relaxed cut length", 1.8, 700))
    for x_, h_ in zip(cx, hd): o.append(t(x_, 38, h_, 1.35, 700, MUTED))
    for i, sz in enumerate(SIZES):
        g, mt = G[sz]; y = 42.5 + i * 4.0; Hs = mt["hood"]
        if i % 2 == 0: o.append(f'<rect x="149" y="{f(y - 2.8)}" width="{SW - 160}" height="4" fill="{ALT}"/>')
        zip_l = g["F01"].edges[0].length + mt["hem_h"] - 5
        vals = [sz, Hs["Q"], Hs["R"], Hs["Ls"], Hs["seam"], Hs["face_len"], mt["hem_band"], mt["el_hem"], mt["sleeve_open"], mt["el_cuff"] + 15, zip_l]
        for j, v in enumerate(vals): o.append(t(cx[j], y, v if isinstance(v, str) else f"{v/10:.1f}", 1.5, 700 if j == 0 or sz == "M" else 400))
    y = 42.5 + 7 * 4.0 + 4
    o.append(t(150, y, "SEAM WALKS — size M", 1.8, 700)); y += 4
    for nm, a, b_, tol in MEAS["M"][1]:
        ok = tol is None or abs(a - b_) <= tol
        o.append(t(150, y, nm, 1.45)); o.append(t(250, y, f"{a/10:.1f} / {b_/10:.1f}", 1.45, 600)); o.append(t(275, y, "ease" if tol is None else ("ok" if ok else "CHECK"), 1.45, 700, GREEN if ok else RED)); y += 3.2
    y = 150
    o.append(t(14, y, "BANDS", 2.0, 700)); y += 4
    for l in [f"Hem band R01: cut {mM['hem_band']/10:.1f} × {2*mM['hem_h']/10:.0f} cm + SA, folded at {mM['hem_h']/10:.1f} cm. Elastic {HD.EL_HEM_W/10:.0f} cm wide, {mM['el_hem']/10:.1f} cm relaxed,",
              f"   stitched in the fold; first + last {HD.FLAT/10:.0f} cm (at the zip) without elastic so the zip lies flat. Relaxed ½ hem = chart D.",
              f"Cuff band R02 (×2): cut {mM['sleeve_open']/10:.1f} × {2*mM['cuff_h']/10:.0f} cm + SA, closed into a loop, folded. Elastic loop {HD.EL_CUFF_W/10:.1f} cm wide,",
              f"   {mM['el_cuff']/10:.1f} cm + 1.5 cm overlap. Relaxed ½ cuff = chart H; gather ratio {mM['el_cuff']/mM['sleeve_open']:.2f}.",
              "Hood: shell + sherpa sewn separately, bagged at the face edge, turned, 6 mm topstitch through all layers (sherpa side down)."]:
        o.append(t(14, y, l, 1.55, 400, PROP if l.startswith(("Hem", "Cuff", "Hood")) else INK)); y += 3.3
    return o

def p_bom():
    o = H("BILL OF MATERIALS", "Per hoodie, size M. Fabric = pattern piece area ÷ (150 cm usable width × 80 % marker efficiency) — replace with the factory's marker.", "T6")
    shell = [c for c in HD.ORDER if gM[c].material.startswith("Shell")]; sher = ["H03", "H04"]
    flan = [c for c in HD.ORDER if "flannel" in gM[c].material]; taf = [c for c in HD.ORDER if "taffeta" in gM[c].material]
    pock = [c for c in HD.ORDER if gM[c].category == "POCKETING"]; fus = [c for c in HD.ORDER if c.startswith("I")]
    m = lambda codes: area_m2(codes, gM) / (1.5 * 0.8)
    zip_l = gM["F01"].edges[0].length + mM["hem_h"] - 5
    rows = [("Shell", SHELL_MAT, f"{m(shell):.2f} m", True),
            ("Hood lining", "Sherpa 280 g/m² polyester, cream", f"{m(sher):.2f} m", True),
            ("Body lining", "Cotton flannel, plaid", f"{m(flan):.2f} m", True), ("Sleeve lining", "Polyester taffeta 210T", f"{m(taf):.2f} m", True),
            ("Pocketing", "8 oz cotton twill", f"{m(pock):.2f} m", True), ("Fusing", "Woven fusible 60 g/m² (facings, welts)", f"{m(fus):.2f} m", False),
            ("Zip", f"YKK #5 metal, antique brass, 2-way separating, {zip_l/10:.0f} cm (M)", "1", True),
            ("Elastic — hem", f"{HD.EL_HEM_W/10:.0f} cm woven elastic, {mM['el_hem']/10:.1f} cm (M)", "1", True),
            ("Elastic — cuff", f"{HD.EL_CUFF_W/10:.1f} cm woven elastic, {(mM['el_cuff']+15)/10:.1f} cm (M)", "2", True),
            ("Thread — seams", "Coats Epic 120 (Tex 27), tonal", "~ 450 m", False), ("Thread — topstitch", "Coats Gral 40 (Tex 60), tonal", "~ 140 m", False),
            ("Main label", LS.main_bom("T6b") + "; back neck facing", "1", False),
            ("Care label", LS.care_bom(SHELL_MAT, "T6b") + "; left side seam lining", "1", False)]
    hd = ["Item", "Description", "Qty / consumption"]; cx = [12, 52, 200]
    for x_, h_ in zip(cx, hd): o.append(t(x_, 33, h_, 1.8, 700, MUTED))
    for i, (a, b_, q, p) in enumerate(rows):
        y = 38 + i * 4.6
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y - 3.1)}" width="{SW - 22}" height="4.6" fill="{ALT}"/>')
        o.append(t(cx[0], y, a, 1.8, 700)); o.append(t(cx[1], y, b_ + ("  [proposed — confirm]" if p else ""), 1.75, 400, LS.AMBER if LS.MISSING in b_ else PROP if p else INK)); o.append(t(cx[2], y, q, 1.8, 600))
    y = 38 + len(rows) * 4.6 + 6
    o.append(t(12, y, "ZIP LENGTH PER SIZE (cm, hem-band edge to CF neck − 0.5)", 1.9, 700)); y += 4.4
    for j, sz in enumerate(SIZES):
        g, mt = G[sz]; o.append(t(12 + j * 22, y, f"{sz}  {(g['F01'].edges[0].length + mt['hem_h'] - 5)/10:.0f}", 1.8, 600))
    return o

def p_labels():
    """T6b: Haki standard main label + the care label for SHELL_MAT (MISSING when it has no fibre %), placement as note 8."""
    return LS.hoodie_page(H, SHELL_MAT)

def p_fit():
    o = H("FIT SAMPLE — what to check + open questions", "The body is the approved jacket, so the fit session focuses on what is new: hood, bands, zip.", "T7")
    checks = ["Hood on the head (zip closed): crown clears the head by 2–3 cm with the sherpa; face opening doesn't pull at the forehead or chin.",
              "Hood down: lies flat on the back, centre panel straight, no drag lines from the neck seam toward the shoulders.",
              "Neck seam: hood sits on the neckline without rippling; HPS notch on the shoulder seam; zip top stop 5 mm under the face edge.",
              "Hem band: relaxed sweep = chart D; gathers even, none in the 6 cm next to the zip; band doesn't flip or roll.",
              "Cuff band: slides over the hand without strain; gathers even; sleeve length to the wrist bone + 2 cm.",
              "Sherpa bulk at the hood seam + face edge: seam pressed open / graded; topstitch even through all layers.",
              "Same as the jacket (should already pass): chest, shoulder, armhole, sleeve pitch, welt position, body length."]
    o.append(t(12, 34, "CHECK ON THE SAMPLE", 2.4, 700)); y = 40
    for i, c in enumerate(checks):
        o.append(f'<rect x="12" y="{f(y - 2.2)}" width="2.6" height="2.6" fill="none" stroke="{INK}" stroke-width="0.25"/>'); o.append(t(16.5, y, c, 1.75)); y += 4.4
    y += 4; o.append(t(12, y, "OPEN QUESTIONS — confirm before the fit sample", 2.4, 700)); y += 6
    qs = ["1. Hood size: 36 × 26 cm (M) incl. sherpa allowance — or measure a hoodie whose hood you like (height HPS→top, width face→back) and we use that.",
          "2. Drawcord: none (as the mockup). Add eyelets + cord?",
          "3. Hem gather: relaxed sweep = jacket chart D, so the hem is only lightly gathered. For a more blouson hem, shorten the hem elastic (e.g. −8 cm).",
          "4. Zip: 2-way separating, YKK #5 metal, antique brass — confirm (mockup shows two pullers).",
          "5. Sherpa: 280 g/m² cream polyester; hood only (body lined in flannel as the jacket) — confirm, or sherpa body lining too?",
          "6. Shell for the blank sample: same washed 12 oz duck as the designs, so the fit matches production.",
          "7. Sizes to sample: M (base) — XS and 3XL too if possible, to check the hood + band grading at the ends."]
    for q in qs: o.append(t(12, y, q, 1.75, 400, PROP)); y += 4.4
    return o

def p_revisions():
    o = H("REVISION LOG + SAMPLE TRACKER", "Every change to this block, newest last.", "T8")
    revs = [("Rev A", DATE, "Block created from the approved Drum Island jacket (same body + sleeve per Haki, 16 Oct 2026). Hood (3 panels, sherpa), "
                            "self-fabric elastic hem + cuff bands, 2-way zip. Pattern XS–3XL, DXF + 1:1 plot.")]
    y = 36
    for rv, dt, ch in revs:
        o.append(t(12, y, rv, 1.8, 700)); o.append(t(36, y, dt, 1.7))
        words = ch.split(); line, lines = "", []
        for w in words:
            if len(line) + len(w) > 150: lines.append(line); line = w
            else: line = (line + " " + w).strip()
        lines.append(line)
        for j, l in enumerate(lines): o.append(t(60, y + j * 3.2, l, 1.7))
        y += 3.2 * len(lines) + 4
    y += 4; o.append(t(12, y, "SAMPLE TRACKER", 2.4, 700)); y += 5
    for i, sname in enumerate(["Blank fit sample (M)", "Blank fit sample (XS, 3XL)", "Block approved — designs can sample", "First embroidered sample"]):
        yy = y + i * 9
        o.append(f'<rect x="11" y="{f(yy - 4)}" width="{SW - 22}" height="9" fill="{ALT if i % 2 == 0 else "#FFFFFF"}" stroke="#DDD" stroke-width="0.2"/>')
        o.append(t(13, yy + 1, sname, 1.8, 600))
    return o

PAGES = ["T1 Cover", "T2 Flats + construction", "T3 Size chart + measurement check", "T4 Pattern pieces + cut list", "T5 Hood + bands detail",
         "T6 Bill of materials", "T6b Labels (Haki standard)", "T7 Fit sample checks + open questions", "T8 Revision log + sample tracker"]

def build():
    for sz in SIZES:
        assert CHECK[sz] and WALKS_OK[sz] and SHAPE_OK[sz], f"pattern QA failed for {sz}"
    for sz in SIZES: PO.write_dxf([sz], f"{OUT}/pattern/{STYLE}_pattern_{sz}.dxf", blk=HD, style=STYLE, emb=False)
    PO.write_dxf(SIZES, f"{OUT}/pattern/{STYLE}_pattern_ALL-SIZES.dxf", blk=HD, style=STYLE, emb=False)
    PO.plot_pdf("M", f"{OUT}/pattern/{STYLE}_pattern_M_1to1_PLOT.pdf", blk=HD, style=STYLE, emb=False)
    index = [(n, i + 1) for i, n in enumerate(PAGES)]
    pages = [p_cover(index), p_flats(), p_pom(), p_pieces(), p_hood(), p_bom(), p_labels(), p_fit(), p_revisions()]
    w = PdfWriter()
    for i, pg in enumerate(pages, 1):
        svg = doc(pg); pdf = f"{OUT}/pages/T{i}.pdf"
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=pdf)
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{OUT}/pages/prev_T{i}.png", output_width=2400)
        w.append(PdfReader(pdf))
    pdf = f"{OUT}/HAKI_{STYLE}_FIT-SAMPLE-TECHPACK_{REV.replace(' ', '')}.pdf"; w.write(pdf)
    pkg = f"{OUT}/pkg"; shutil.rmtree(pkg, ignore_errors=True); os.makedirs(pkg)
    shutil.copytree(f"{OUT}/pattern", f"{pkg}/pattern"); shutil.copy(pdf, pkg); LS.export(f"{pkg}/labels", SHELL_MAT)
    open(f"{pkg}/README.txt", "w").write(f"""HAKI STUDIOS - {NAME} ({STYLE}) - {REV} - {DATE}
Blank fit sample: the approved Drum Island jacket body + sleeve with a 3-panel sherpa-lined hood and self-fabric elastic bands.

{os.path.basename(pdf)}   T1-T8: flats, size chart + measurement check, pattern pieces + cut list, hood + bands, BOM, fit checks, revisions
pattern/{STYLE}_pattern_<size>.dxf      AAMA-layer DXF per size (1 cut, 14 sew, 4 notches, 7 grain, 8 internal, 13 drill, 15 text), mm
pattern/{STYLE}_pattern_ALL-SIZES.dxf   every size in one file
pattern/{STYLE}_pattern_M_1to1_PLOT.pdf size M, one page per piece at 1:1 (check the 100 mm test box)
Amber items are proposed by Haki tech design - confirm. Sew + fit M before the size set.
""")
    z = f"{OUT}/HAKI_{STYLE}_{REV.replace(' ', '')}_files.zip"
    if os.path.exists(z): os.remove(z)
    subprocess.run(f"cd {pkg} && zip -qr ../{os.path.basename(z)} .", shell=True)
    print("pages", len(pages), pdf, z)

if __name__ == "__main__":
    for sz in SIZES:
        print(sz, "chart", CHECK[sz], "walks", WALKS_OK[sz], "shape", SHAPE_OK[sz])
    build()
