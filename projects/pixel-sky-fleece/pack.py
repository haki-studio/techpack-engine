"""Pixel Sky fleece — the merged tech pack PDFs, two from one build (Rev G):
  HAKI_<STYLE>_RFQ_RevG.pdf       SUPPLIER copy for the RFQ: no QA tables, no internal provenance, no engine jargon
                                  (rfq_text_gate on the rendered text, red-then-green against the internal copy)
  HAKI_<STYLE>_TECHPACK_RevG.pdf  internal full pack = the same pages + full J3 / G pages, decisions log Q3, R1 checks
Garment pages T*, jacquard J*, embroidery G*, factory requests F*, quote Q1, open points Q2. Every number is read from a
generated file (DST read-back via gates_fl.json, jacquard_stats.json, the pattern, clearances.json).
usage: python3 pack.py"""
import os, re, json
import cairosvg
from pypdf import PdfWriter, PdfReader
import sheet as SHT
from sheet import t, doc, INK, MUTED, RED, GREEN, ORANGE, SW, SH, embed
import factory, tech
import fleece as FL, pattern as PT, pattern_draw as PD, jacquard as JQ

STYLE = "HK-FL-PIXSKY"; REV = "Rev G"; DATE = "22 Oct 2026"; NAME = "Pixel Sky sherpa fleece jacket"
SHT.FOOT = f"HAKI STUDIOS · {NAME} · {STYLE} · {REV} · {DATE}"
PROP = "#8A5A00"; ALT = "#F5F2EC"
OUT = "out"; PG = f"{OUT}/pages"; os.makedirs(PG, exist_ok=True)
SIZES = FL.SIZES
GATES = json.load(open(f"{OUT}/stitch/gates_fl.json")); JQS = json.load(open(f"{OUT}/jacquard/jacquard_stats.json"))
PLACE = json.load(open(f"{OUT}/art/placements.json")); CLR = json.load(open(f"{OUT}/clearances.json"))
AGREE = json.load(open(f"{OUT}/jacquard/agreement.json"))
GJQ = json.load(open(f"{OUT}/jacquard/gates_jq.json")) if os.path.exists(f"{OUT}/jacquard/gates_jq.json") else None   # island gate (round 3)
CHK = JQS["checker"]; CHKQ = CHK["q"]                                      # checker lattice (jacquard.regularise_checker)
_small = f"{OUT}/HAKI_{STYLE}_TECHPACK_{REV.replace(' ', '')}_small.pdf"       # finish.py output (run_all runs pack twice)
SMALL_OK = os.path.exists(_small) and os.path.getsize(_small) < 0.6 * os.path.getsize(_small.replace("_small", "")) if os.path.exists(_small) else False
SMALL_EV = (f"{os.path.basename(_small)} {os.path.getsize(_small) / 1e6:.1f} MB vs {os.path.getsize(_small.replace('_small', '')) / 1e6:.1f} MB" if os.path.exists(_small) else "small PDF not built yet (finish.py)")
SELFTEST = json.load(open(f"{OUT}/stitch/gates_selftest.json")) if os.path.exists(f"{OUT}/stitch/gates_selftest.json") else None
TXTGATE = f"{OUT}/rfq_text_gate.json"
PROF = factory.load()
TH = {"yellow": "#F6E23A", "gold": "#D9A521", "black": "#231F1E"}
THN = {"yellow": "Sparkle yellow", "gold": "Sparkle gold", "black": "Bird black"}
G = {sz: FL.draft(sz) for sz in SIZES}; gM, mM = G["M"]
CH = FL.chart(); MEAS = {sz: FL.measure(sz) for sz in SIZES}
CHECK = {sz: all(abs(MEAS[sz][0][k] / 10 - CH[k][2][SIZES.index(sz)]) <= CH[k][3] for k in CH) for sz in SIZES}
WALKS = {sz: all(tol is None or abs(a - b) <= tol for _, a, b, tol in MEAS[sz][1]) for sz in SIZES}
SHAPE = {sz: all(c[1] for c in FL.shape_checks(sz)) for sz in SIZES}
FILES = [("E1", "Sparkles — wearer's right front (beside the bird)", "option A + B"), ("E2", "Sparkles — wearer's left front", "always"),
         ("E3", "Sparkles — wearer's left sleeve", "always"), ("E1B", "Bird + sparkles — wearer's right front", "option B only (replaces E1)")]
BIG = max(FILES, key=lambda f_: GATES[f_[0]]["size_mm"][0] * GATES[f_[0]]["size_mm"][1])[0]
hexs = lambda c: "#%02X%02X%02X" % tuple(c)
# colour standard (TD N1): hex from the files (jacquard palette, flat render colours, thread design colours); TCX to follow
import fflat as FF
import labelsheet as LS
SHELL_RECORDED = "jacquard sherpa, fibre content: mill to state"     # no fibre % recorded -> care label MISSING (LESSONS D7, never guessed)
COLOURS = [("Sky blue — sherpa yarn 0 + collar outer taslan", hexs(JQ.COL[0])), ("Cream — sherpa yarn 1 + collar inner", hexs(JQ.COL[1])),
           ("Black — bird yarn 2 (option A)", hexs(JQ.COL[2])), ("Navy — binding, tapes, facing, pocket zip tape", hexs(FF.NAVY)),
           ("Black — CF zip tape + teeth", hexs(FF.ZIPC)), ("Blue — zip pulls", hexs(FF.PULL)),
           ("Sparkle yellow — thread", TH["yellow"]), ("Sparkle gold — thread", TH["gold"])]
TCX = "Pantone TCX to follow — until then match the hex shown and propose your nearest TCX / stock card"
DIP = "Sky sherpa yarn and sky taslan are dipped to the same TCX in parallel; final taslan approval is against the approved sherpa knit-down"
CARE = "No garment wash. Care: cold machine wash inside out, no tumble dry (or low), do not iron the pile; final care text after the mill's fibre content and the wash test"
FITS = "Fit sample in M in a stock (plain) sherpa of the same pile height and weight as the quoted jacquard quality — mandatory before the size set."
PILE = "sherpa pile ~8-10 mm"                   # fleece.py docstring: the pile assumption behind the pile ease
LADDER = [100, 200, 300, 500]                    # brief (RFQ edition): ask THEM to quote at these quantities — no target price
MODE = "internal"
def RFQ(): return MODE == "rfq"
def cf(d="21 Oct"): return f"confirmed (Haki Studios, {d})" if RFQ() else f"confirmed by the founder {d}"

def H(title, sub, page): return SHT.header(title, sub, page)
def prop(x, y, s, size=1.8): return t(x, y, s + "  [proposed — confirm]", size, 600, PROP)
def wrap(s, n):
    out, line = [], ""
    for w in s.split():
        if len(line) + len(w) + 1 > n: out.append(line); line = w
        else: line = (line + " " + w).strip()
    return out + [line]
def para(o, x, y, s, n=110, size=1.75, col=INK, lh=3.1, w=400):
    for l in wrap(s, n): o.append(t(x, y, l, size, w, col)); y += lh
    return y
def img(o, path, x, y, w, crop=None):
    s, h = embed(path, crop=crop, w_mm=w, x=x, y=y); o.append(s); return h
def img_fit(o, path, x, y, w, hmax):
    from PIL import Image
    im = Image.open(path); r = im.height / im.width; ww = min(w, hmax / r); return img(o, path, x + (w - ww) / 2, y, ww)
def blank(o, x, y, w): o.append(f'<line x1="{x}" y1="{y + 0.6}" x2="{x + w}" y2="{y + 0.6}" stroke="{MUTED}" stroke-width="0.15"/>')
def zebra(o, i, y, h, x0=11, x1=None):
    if i % 2 == 0: o.append(f'<rect x="{x0}" y="{y - 2.6}" width="{(x1 or SW - 11) - x0}" height="{h}" fill="{ALT}"/>')

# ---------------------------------------------------------------- T pages
def p_cover(index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>', t(14, 22, "HAKI STUDIOS", 3.0, 700, MUTED), t(14, 34, NAME, 7.0, 700),
         t(14, 41.5, f"Style {STYLE} · {REV} · {DATE} · sizes XS–3XL · base M · mm unless marked · first sample: fit sample in M (T3)", 2.4, 400, MUTED),
         f'<line x1="14" y1="45" x2="{SW-14}" y2="45" stroke="{INK}" stroke-width="0.4"/>']
    o.append(t(SW - 14, 22, ("REQUEST FOR QUOTATION" if RFQ() else "INTERNAL TECH PACK"), 3.0, 700, RED if not RFQ() else INK, "end"))
    o.append(t(SW - 14, 30, "Prepared for:", 2.2, 600, MUTED, "end")); blank(o, SW - 74, 36, 60)
    img_fit(o, "inputs/front.png", 14, 50, 60, 62); o.append(t(14, 116, "DESIGN MOCKUP (front only)", 1.9, 700))
    img_fit(o, f"{OUT}/flat_front_A.png", 78, 52, 118, 52); o.append(t(78, 108, "FRONT — drawn from the pattern (M), jacquard + embroidery", 1.9, 700))
    img_fit(o, f"{OUT}/flat_back.png", 78, 116, 118, 52); o.append(t(78, 172, f"BACK — cloud band continued, no back motif — {cf()}", 1.9, 700))
    ix = 204; o.append(t(ix, 54, "CONTENTS", 2.8, 700)); y = 60
    for name, pg in index: o.append(t(ix, y, name, 1.75)); o.append(t(SW - 14, y, str(pg), 1.75, 600, MUTED, "end")); y += 3.3
    y += 2.5; o.append(t(ix, y, "KEY SPECS", 2.4, 700)); y += 4.2
    for a, b_, c_ in [("Shell", f"jacquard sherpa, sky blue / cream, {PILE.replace('sherpa ', '')}", PROP), ("Clouds", "knitted in (jacquard), 2.5 mm cells", PROP),
                      ("Sparkles", "embroidered, yellow + gold (E1–E3)", INK), ("Bird", "knitted black (A) or embroidered (B, E1B)", PROP),
                      ("Collar", "9 cm stand, sky-blue taslan outer / cream sherpa inner", PROP), ("Edges", "navy binding; elastic cuffs", PROP),
                      ("Closures", "CF zip + 2 vertical zip pockets", PROP), ("Fit", "block + pile ease " + cf(), INK)]:
        o.append(t(ix, y, a, 1.75, 400, MUTED)); o.append(t(ix + 15, y, b_, 1.65, 600, c_)); y += 3.4
    o.append(t(ix, y + 1.2, "Amber = proposed — confirm; black = confirmed (Haki Studios).", 1.5, 400, MUTED))
    o.append(t(SW - 14, SH - 8, SHT.FOOT, 1.8, 400, MUTED, "end"))
    return o

def notes():
    bag = gM["P02"].note.replace(" [proposed]", "")
    return [("1", "Stand collar 9 cm: outer SKY-BLUE taslan (C01), inner cream sherpa (C02), seamed at the top edge, turned; navy piping (BD3) in the neck seam, visible 8 mm. Colour: " + DIP + "."),
            ("2", "CF zip: black #5 coil, separating, blue pull, hem binding edge to collar top − 5 mm; zip tape covered inside by a navy taslan facing strip (Z01)."),
            ("3", "Bird: knitted black in the jacquard (option A) — or embroidered E1B (option B) if the mill cannot add a 3rd colour. Sparkles E1/E2 always embroidered."),
            ("4", f"Vertical zip pockets {FL.PKT_L/10:.1f} cm, navy tape, blue pulls; bound slit with a taslan facing (factory to recommend). Tricot bags (P02): {bag}; factory to advise whether to bar-tack the bag to the CF facing or catch it in the side seam."),
            ("5", f"Hem: navy binding {FL.BIND_W/10:.1f} cm finished, encloses the cut edge (no rib); ends turned in at the zip."),
            ("6", f"Cuffs: navy binding channel with {FL.CUFF_EL_W/10:.0f} cm elastic, gathers the sleeve opening to chart H."),
            ("7", "Sleeve sparkles E3 on the wearer's left sleeve, front half, above the cloud band."),
            ("8", f"Unlined: sherpa reverse inside (reverse photo asked, F2–F3 q8); seams per T7. Neck seam covered inside by the navy taslan neck tape NT1 ({FL.NECKT_W/10:.1f} cm), carrying the main + size label and the hanger loop P04 (T6).")]

def p_flats():
    o = H("FLATS + CONSTRUCTION", "Size M, drawn from the pattern pieces with the jacquard cell maps and the stitch art. Amber = proposed — confirm.", "T2")
    img_fit(o, f"{OUT}/flat_front_A.png", 12, 30, 190, 82); img_fit(o, f"{OUT}/flat_back.png", 12, 116, 190, 82)
    o.append(t(12, 30, "FRONT", 2.2, 700)); o.append(t(12, 116, f"BACK — band continued, no motif: {cf()}", 2.2, 700))
    y = 32; tx = 208
    for n, s_ in notes():
        o.append(f'<circle cx="{tx}" cy="{y - 0.8}" r="2.0" fill="#FFFFFF" stroke="{INK}" stroke-width="0.25"/>' + t(tx, y, n, 1.8, 700, INK, "middle"))
        y = para(o, tx + 4, y, s_, 54, 1.55, PROP, 2.85) + 1.8
    if not RFQ():
        y += 1; y = para(o, tx, y, "Mockup vs block: the render is slimmer than the Drum Island block (shoulder ~46 vs 53 cm at the art scale). "
                         "Art keeps the mockup's sizes and heights; the block keeps its width, so the cloud band and sky run wider than in the render.", 54, 1.45, MUTED, 2.7)
    return o

def p_pom():
    o = H("SIZE CHART + HOW TO MEASURE", "cm, garment flat. ½ = half measurement. Amber rows = proposed — confirm. Points of measure: key on the right.", "T3")
    hd = ["", "Point of measure", "How measured"] + SIZES + ["Tol"]; cx = [12, 17, 50, 100, 109, 118, 127, 136, 145, 154, 164]
    for x_, h_ in zip(cx, hd): o.append(t(x_, 31, h_, 1.6, 700, MUTED))
    order = ["A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "P", "M", "Q", "R"]
    for i, k in enumerate(order):
        nm, how, vals, tol, src = CH[k]; y = 36 + i * 4.1; pr = "PROPOSED" in src
        zebra(o, i, y, 4.1, 11, 172); col = PROP if pr else INK
        o.append(t(cx[0], y, k, 1.75, 700, col)); o.append(t(cx[1], y, nm[:24], 1.55, 600, col)); o.append(t(cx[2], y, how[:40], 1.3, 400, MUTED))
        for j, v in enumerate(vals): o.append(t(cx[3 + j], y, f"{v:g}", 1.6, 700 if SIZES[j] == "M" else 400, col))
        o.append(t(cx[10], y, f"±{tol:g}", 1.45, 400, MUTED))
    y = 36 + len(order) * 4.1; zebra(o, len(order), y, 4.1, 11, 172)
    o.append(t(cx[0], y, "H2", 1.75, 700, PROP)); o.append(t(cx[1], y, "Sleeve opening, stretched", 1.55, 600, PROP)); o.append(t(cx[2], y, "½, cuff edge, elastic fully stretched", 1.3, 400, MUTED))
    o.append(t(cx[3], y, "TBD — factory to measure at the fit sample  [proposed]", 1.55, 600, PROP))
    yk = y + 5
    tx = 176; y = 33; o.append(t(tx, y, "HOW TO MEASURE", 2.1, 700)); y += 4
    for l, c_ in [("Garment flat, zip closed, no tension. Measure at the BASE OF THE PILE (the knitted ground), not at the pile surface.", INK),
                  ("Half measurements (½) straight across the flat garment. Sleeve G includes the cuff binding. Length A cropped at the hip as the mockup.", INK),
                  (f"Rows M, Q, R and H2 are proposed — confirm. Binding width tolerance set to ±{CH['Q'][3]:g} cm: a pile edge cannot be measured closer.", PROP),
                  (FITS, RED)]:
        y = para(o, tx, y, l, 66, 1.6, c_, 3.0, 700 if c_ == RED else 400) + 1.0
    if not RFQ():
        y += 1.5; y = para(o, tx, y, "PATTERN CHECK (internal) — every size measured off the drafted pieces vs this chart (chart · seam walks · shape)", 66, 1.6, INK, 3.0, 700)
        for j, sz in enumerate(SIZES):
            ok = CHECK[sz] and WALKS[sz] and SHAPE[sz]; o.append(t(tx + j * 15, y, f"{sz} " + ("pass" if ok else "FAIL"), 1.4, 700, GREEN if ok else RED))
        y += 3.6; y = para(o, tx, y, f"Pile ease vs Drum Island: {', '.join(f'{k} +{v:g}' for k, v in FL.EASE_CM.items())} cm; D = B (bound hem) — {cf()}.", 70, 1.4, MUTED, 2.7)
    o.append(t(12, yk, "POINTS OF MEASURE — key on the size-M front flat (letters = chart rows; not for scaling)", 1.7, 700))
    img_fit(o, f"{OUT}/measure_key.png", 12, yk + 2, 200, SH - yk - 12)
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
    o = H("PATTERN — pieces + cut list (size M)", "Seam allowance included; dashed = sew line; slits = notches; red box = pocket zip opening; ⊕ = drill holes.", "T4")
    y1 = _draw(o, gM, ["B01", "F01", "F02", "S01", "S02"], 12, 30, 190, 0.062, 0.3, 1.1)
    _draw(o, gM, ["C01", "C02", "Z01", "P02", "P04", "BD1", "BD2", "BD3", "NT1"], 12, y1 + 6, 190, 0.062, 0.26, 0.9, 5)
    tx = 206; o.append(t(tx, 31, "CUT LIST — per jacket", 2.3, 700))
    hd = ["Code", "Piece", "Cut", "Material"]; cx = [tx, tx + 9, tx + 39, tx + 50]
    for x_, h_ in zip(cx, hd): o.append(t(x_, 35.5, h_, 1.55, 700, MUTED))
    for i, code in enumerate(FL.ORDER):
        pc = gM[code]; y = 39.5 + i * 3.5; zebra(o, i, y + 0.2, 3.5, tx - 1)
        o.append(t(cx[0], y, code, 1.45, 700)); o.append(t(cx[1], y, pc.name.replace(" (wearer's)", "")[:22], 1.4))
        o.append(t(cx[2], y, pc.qty.replace(" (2 pairs)", ""), 1.4)); o.append(t(cx[3], y, (pc.material.split(" — ")[0] + " " + pc.material.split(" — ")[-1][:24]).split(" (")[0].rstrip(" ,"), 1.35, 400, PROP))
    y = 39.5 + len(FL.ORDER) * 3.5 + 3
    for l in ["Jacquard panels B01 F01 F02 S01 S02: knit each panel to its own cell map (J pages),",
              "cut on the marked cut line; the map runs 12 mm past the cut line (knit area).",
              f"SA {PT.SA_STD/10:.1f} cm; binding joins 0; collar top edge {PT.SA_EDGE/10:.1f}.",
              f"NT1 neck tape: {gM['NT1'].edges[0].length/10:.1f} cm (= neck seam, M)  [proposed — confirm].",
              "Files: DXF per size + all sizes (AAMA layers; layer 8 = embroidery boxes),", "1:1 plot PDF size M."]:
        o.append(t(tx, y, l, 1.4, 400, PROP if "proposed" in l else MUTED)); y += 3.1
    return o

def p_bom():
    o = H("BILL OF MATERIALS + TRIMS + COLOUR STANDARD", "Per jacket, size M. Lengths read from the pattern. Fabric = piece area ÷ (150 cm width × 80 % marker) — replace with your marker.", "T5")
    qty = lambda pc: int(pc.qty.split()[0]) * (2 if "pair" in pc.qty and "(" not in pc.qty else 1)
    area = lambda codes: sum(PT.cut_poly(gM[c]).area * qty(gM[c]) for c in codes) / 1e6 / (1.5 * 0.8)
    zip_l = gM["F01"].edges[0].length + FL.COLLAR_H - 5
    rows = [("Shell — jacquard sherpa", f"Engineered pile jacquard, sky blue / cream (+ black bird, option A); {PILE}, ~ 300 g/m²; fibre content: mill to state (F2–F3 q4)", f"{area(['B01','F01','F02','S01','S02']):.2f} m (knit per panel)"),
            ("Collar inner", "Plain sherpa, cream (same pile) — knitted in the same run if possible (F2–F3 q7)", f"{area(['C02']):.2f} m"),
            ("Collar outer + zip facing + loop", "Nylon taslan: collar SKY BLUE to the colour standard below; navy (facing, loop)", f"{area(['C01']):.2f} + {area(['Z01','P04']):.2f} m"),
            ("Binding", f"Navy taslan, cross-cut, {FL.BIND_CUT:.0f} mm cut, {FL.BIND_W:.0f} mm finished: hem {mM['hem_len']/10:.0f} cm, cuffs 2 × {mM['sleeve_open']/10:.0f} cm, collar piping {mM['Ln']/10:.0f} cm", "1 set"),
            ("Neck tape NT1", f"Navy taslan, {FL.NECKT_CUT:.0f} mm cut, {FL.NECKT_W:.0f} mm finished, over the neck seam inside; carries main + size label + hanger loop", f"{gM['NT1'].edges[0].length/10:.1f} cm"),
            ("Cuff elastic", f"{FL.CUFF_EL_W:.0f} mm woven elastic, {mM['el_cuff']/10:.1f} cm + 1.5 overlap (M)", "2"),
            ("CF zip", f"#5 coil, separating, black tape + teeth, blue pull, {zip_l/10:.0f} cm (M)", "1"),
            ("Pocket zips", f"#3 coil, navy tape, blue pull, {FL.PKT_L/10:.1f} cm opening", "2"),
            ("Pocketing", "Tricot fleece 160 g/m², cream; fibre content: supplier to state", f"{area(['P02']):.2f} m"),
            ("Seam tape", "Navy taslan 15 mm, over the body seams (unlined) — or flatlock, factory to recommend (T7)", "~ 6 m"),
            ("Thread — seams", "Polyester core-spun Tex 27, tonal (blue / cream) + overlock", "~ 400 m"),
            ("Embroidery", "40 wt polyester threads (G pages); topping: water-soluble film on top of the pile; backing: cutaway 2.5 oz", "per hooping"),
            ("Labels + packing", "Main + size label, care / content / COO label, hangtag, polybag — T6", "1 set")]
    for x_, h_ in zip([12, 60, 228], ["Item", "Description", "Qty / consumption"]): o.append(t(x_, 32, h_, 1.75, 700, MUTED))
    y = 36.5
    for i, (a, b_, q) in enumerate(rows):
        lines = wrap(b_ + "  [proposed — confirm]", 150)
        zebra(o, i, y - 0.4, 3.3 * len(lines) + 0.9)
        o.append(t(12, y, a, 1.65, 700))
        for j, l in enumerate(lines): o.append(t(60, y + j * 3.3, l, 1.55, 400, PROP))
        o.append(t(228, y, q, 1.6, 600)); y += 3.3 * len(lines) + 1.1
    y += 3; o.append(t(12, y, "COLOUR STANDARD", 2.0, 700)); o.append(t(48, y, TCX + "  [proposed — confirm]", 1.5, 600, PROP)); y += 4
    for i, (nm, hx) in enumerate(COLOURS):
        x = 12 + (i % 4) * 70; yy = y + (i // 4) * 4.4
        o.append(f'<rect x="{x}" y="{yy - 2.6}" width="6" height="3.2" fill="{hx}" stroke="#999" stroke-width="0.15"/>')
        o.append(t(x + 8, yy, f"{hx}  {nm}", 1.45)); o.append(t(x + 8, yy + 2.1, "TCX: ____________", 1.3, 400, MUTED))
    y += 10.5; y = para(o, 12, y, "Lab dips: " + DIP + ". Judge from daylight photos next to the TCX card, ruler in shot.  [proposed — confirm]", 170, 1.5, PROP, 2.8)
    y += 1.5; o.append(t(12, y, "PER SIZE (cm) — read from the pattern", 1.8, 700)); y += 3.6
    hd = ["Size", "CF zip", "Hem binding", "Cuff binding", "Cuff elastic", "Collar / neck", "Neck tape", "Pocket opening"]
    for j, h_ in enumerate(hd): o.append(t(12 + j * 28, y, h_, 1.5, 700, MUTED))
    for i, sz in enumerate(SIZES):
        g, mt = G[sz]; y += 3.2
        vals = [sz, (g["F01"].edges[0].length + FL.COLLAR_H - 5) / 10, mt["hem_len"] / 10, mt["sleeve_open"] / 10, (mt["el_cuff"] + 15) / 10, mt["Ln"] / 10, g["NT1"].edges[0].length / 10, FL.PKT_L / 10]
        for j, v in enumerate(vals): o.append(t(12 + j * 28, y, v if isinstance(v, str) else f"{v:.1f}", 1.5, 700 if sz == "M" or j == 0 else 400))
    return o

def p_labels():
    o = H("T6 · LABELS + PACKAGING", "Main label = Haki Studios standard label (art right, 1 : 1, file in the zip labels/). Care label: fibre not confirmed yet. RN / manufacturer ID follow from Haki Studios. Positions on the finished garment.", "T6")
    img_fit(o, f"{OUT}/labels_key.png", 12, 30, 125, 60); o.append(t(12, 30, "BACK VIEW (inside positions shown through)", 1.7, 700))
    rows = [("1  Main label", "Haki standard, 6.5 × 2 cm, white, woven, flat (art right)", f"inside back neck: centred at CB on the neck tape NT1 ({FL.NECKT_W/10:.1f} cm navy taslan), sewn down on all 4 sides; the 2 cm label is taller than the tape — centre it on the tape", False),
            ("1  Size label", "woven, size only", "folded, centred under the main label, caught in the main label's lower seam", True),
            ("1  Hanger loop", f"P04, navy taslan, {gM['P04'].note.split(':')[0]}", "CB, caught under the neck tape above the main label", True),
            ("2  Care / content / COO", "Haki standard care label " + LS.MISSING, "inside the wearer's LEFT side seam, ~10 cm above the hem binding, text reading down", True),
            ("Hangtag", "Haki hangtag, supplied or sourced (F2–F3 q23)", "through the hanger loop with string / pin; never through the jacquard face", True)]
    y = 96
    for x_, h_ in zip([12, 52, 120], ["Item", "What", "Placement"]): o.append(t(x_, y, h_, 1.65, 700, MUTED))
    for i, (a, b_, c_, pp) in enumerate(rows):
        ls_ = wrap(c_ + "  [proposed — confirm]", 92); y += 4.6; zebra(o, i, y, 3.0 * len(ls_) + 1.6, 11, 196)
        o.append(t(12, y, a, 1.6, 700)); o.append(t(52, y, b_[:70], 1.5, 400, (PROP if pp else INK) if "MISSING" not in b_ else LS.AMBER))
        for j, l in enumerate(ls_): o.append(t(120, y + j * 3.0, l, 1.5, 400, PROP))
        y += 3.0 * (len(ls_) - 1)
    y += 8; o.append(t(12, y, "CARE / CONTENT / COO LABEL — Haki standard care label " + LS.MISSING, 2.0, 700, LS.AMBER)); y += 4
    y = para(o, 14, y, "The shell fibre % is not known yet (mill to state, F2–F3 q4). Haki standard care labels exist for 100 % cotton and 90 % cotton / 10 % polyester only; once the fibre is stated, Haki confirms the care label and sends its artwork. Do not print a care label until then.", 170, 1.55, INK, 2.9) + 0.6
    for l in ["Other components: collar outer nylon taslan · collar inner [mill to state] · binding + tapes nylon taslan · pocketing [supplier to state] · embroidery thread polyester · RN / manufacturer ID [to follow] · Style HK-FL-PIXSKY",
              CARE + "."]:
        y = para(o, 14, y, l + "  [proposed — confirm]", 170, 1.55, PROP, 2.9) + 0.6
    y += 3; o.append(t(12, y, "PACKAGING", 2.0, 700)); y += 4
    for l in ["Hangtag + one clear polybag per piece, printed suffocation warning; size sticker on the bag.",
              "Fold: zip closed; fold advised by the factory so the pile is not crushed (F2–F3 q23).",
              "Carton: export carton; pieces per carton and size packing — please propose; carton marks to follow (style, colour, size breakdown, qty, carton n / N)."]:
        y = para(o, 14, y, "•  " + l + "  [proposed — confirm]", 170, 1.55, PROP, 2.9) + 0.6
    tx = 145; ty = 34; o.append(t(tx, ty, "ON THE BACK VIEW", 1.8, 700)); ty += 4
    for l in ["1 = main + size label + hanger loop, CB inside the neck,", "     on the neck tape NT1 (T7: neck seam).",
              "2 = care / content / COO label, wearer's left side seam,", "     inside, ~10 cm above the hem binding.",
              "Back view: wearer's left = viewer's left."]:
        o.append(t(tx, ty, l, 1.6)); ty += 3.2
    o += LS.panel(200, 58, 86, SHELL_RECORDED, f"Position: CB inside the neck, centred on the neck tape NT1 ({FL.NECKT_W/10:.1f} cm) — the label is taller than the tape [proposed — confirm].",
                  "Position: wearer's left side seam, inside, ~10 cm above the hem binding.")[0]
    return o

def p_seams():
    o = H("T7 · SEAMS, STITCHES + ASSEMBLY", "Per seam: stitch type, finish, stitches per inch. All proposed — confirm or recommend your method for this pile. SPI: factory to state.", "T7")
    rows = [("Shoulder, side + underarm, armhole", "4-thread overlock", "navy taslan tape 15 mm over the seam, edge-stitched both sides — or flatlock: which do you recommend on this pile? (F2–F3 q21)"),
            ("Collar top edge (C01 + C02)", "lockstitch, seamed + turned", f"top edge SA {PT.SA_EDGE/10:.1f} cm; topstitch close to the edge"),
            ("Neck seam (collar + piping BD3 + body)", "lockstitch", f"inside: neck tape NT1 {FL.NECKT_W/10:.1f} cm over the seam, edge-stitched both sides, zip to zip; main + size label + hanger loop caught at CB"),
            ("Hem binding BD1", "lockstitch with binder / folder (or coverstitch)", f"{FL.BIND_W/10:.1f} cm finished, encloses the cut edge; ends turned in at the zip"),
            ("Cuff binding BD2", "lockstitch with binder / folder", f"channel with {FL.CUFF_EL_W/10:.0f} cm elastic; elastic ends overlapped 1.5 cm"),
            ("CF zip", "lockstitch, zip edge-stitched", "facing strip Z01 over the zip tape inside, edge-stitched; zip runs hem binding edge to collar top − 5 mm"),
            ("Pocket zip slits", "lockstitch, zip edge-stitched", "bound slit with a taslan facing (factory to recommend, F2–F3 q20); bag P02 sewn round the opening"),
            ("Bar-tacks", "bar-tack", "pocket zip ends (top + bottom), CF zip bottom, hanger loop, cuff elastic join"),
            ("Pile shaving", "—", "seam, binding and zip allowances: factory to advise (F2–F3 q16, q19)")]
    for x_, h_ in zip([12, 72, 122, 262], ["Seam", "Stitch type", "Finish", "SPI"]): o.append(t(x_, 33, h_, 1.75, 700, MUTED))
    y = 38
    for i, (a, b_, c_) in enumerate(rows):
        lines = wrap(c_ + "  [proposed]", 92); zebra(o, i, y - 0.3, 3.3 * len(lines) + 1.4)
        o.append(t(12, y, a, 1.6, 700)); o.append(t(72, y, b_, 1.5, 400, PROP))
        for j, l in enumerate(lines): o.append(t(122, y + j * 3.3, l, 1.5, 400, PROP))
        o.append(t(262, y, "factory to state", 1.45, 400, MUTED)); y += 3.3 * len(lines) + 1.6
    y += 4; o.append(t(12, y, "ASSEMBLY ORDER", 2.0, 700)); y += 4
    for i, s_ in enumerate(["Knit the jacquard panels to their maps; cut on the marked cut lines.", "Embroider the cut panels F01, F02, S02 (G pages) before assembly.",
                            "Pocket slits + zips + bags on F01 / F02.", "Shoulders; collar C01 + C02 seamed at the top edge and turned; collar + piping BD3 to the neckline.",
                            "Neck tape NT1 over the neck seam inside, with the main + size label and the hanger loop P04 at CB.", "Sleeves set in; side + underarm seams in one; seams finished per the table.",
                            "CF zip + facing strips Z01; hem binding BD1; cuff bindings BD2 with elastic.", "Care label in the wearer's left side seam; bar-tacks; pile brushed up; QC (T3 tolerances); hangtag; pack (T6)."]):
        o.append(t(14, y, f"{i + 1:02d}  {s_}", 1.6, 400, PROP)); y += 3.4
    o.append(t(14, y + 1.5, "Assembly order and stitch types are proposals — please confirm or send yours.", 1.5, 600, PROP))
    return o

# ---------------------------------------------------------------- J pages (jacquard)
def p_j1():
    o = H("J1 · JACQUARD SHERPA — method, colours, files", "Clouds (and the bird in option A) are KNITTED into the sherpa, engineered per pattern panel [proposed — confirm feasibility, F2–F3 q1].", "J1")
    y = 33; o.append(t(12, y, "HOW IT WORKS", 2.4, 700)); y += 5
    for s_ in [f"One cell = {JQS['cell_mm']} × {JQS['cell_mm']} mm finished [proposed — you convert to your knit gauge: stitches × courses per cell]. "
               f"Clouds and the bird are drawn per cell; the 2-colour checker along the cloud edges is a regular lattice of {CHKQ} × {CHKQ} cells ({CHKQ * 2.5:.1f} mm squares) [proposed].",
               "Each panel map = the pattern piece's cut line + 12 mm knit margin, anchored on the CF (fronts) / CB (back) / sleeve centre line and on the hem / cuff edge, "
               "so the cloud band sits at the same height above the hem in every size and meets across the side seams and the zip.",
               "Files: one indexed PNG + BMP per panel and size, 1 px = 1 cell; palette index 0 = sky blue, 1 = cream, 2 = black (bird), 9 = outside the knit area.",
               "Option A: bird knitted black (3rd colour, bird area only) → F02 map *_birdA, embroider E1 + E2 + E3. "
               "Option B: 2 colours only → F02 map *_birdB (no bird), embroider E1B (bird + sparkles) + E2 + E3. Nothing to rebuild."]:
        y = para(o, 12, y, s_, 120, 1.75, PROP) + 1.6
    y += 2; o.append(t(12, y, "YARN COLOURS", 2.2, 700)); o.append(t(42, y, TCX + "  [proposed — confirm]", 1.5, 600, PROP)); y += 4.6
    for nm, hx in [("0 Sky blue", hexs(JQ.COL[0])), ("1 Cream", hexs(JQ.COL[1])), ("2 Black (bird, option A)", hexs(JQ.COL[2]))]:
        o.append(f'<rect x="12" y="{y - 2.6}" width="6" height="3.2" fill="{hx}" stroke="#999" stroke-width="0.15"/>'); o.append(t(20, y, f"{nm}  {hx}   TCX: ____________", 1.75)); y += 4
    y += 2; o.append(t(12, y, "PANEL FILES — size M (all sizes in the zip: jacquard/HK-FL-PIXSKY_JQ_PANEL_SIZE.png + .bmp)", 2.0, 700)); y += 4.4
    hd = ["Panel map", "Piece", "Cells (w × h)", "Knit area mm", "Sky", "Cream", "Black"] + ([] if RFQ() else ["Traced", "Filled*", "Generated**"])
    cx = [12, 52, 66, 92, 118, 134, 150, 163, 180, 196]
    for x_, h_ in zip(cx, hd): o.append(t(x_, y, h_, 1.5, 700, MUTED))
    for k, v in JQS["panels"].items():
        if v["size"] != "M": continue
        y += 3.6; vals = [k.replace("_M", ""), v["piece"], f"{v['cols']} × {v['rows']}", f"{v['width_mm']:.0f} × {v['height_mm']:.0f}", v["sky"], v["cream"], v["black"]] + ([] if RFQ() else [v["traced"], v["filled"], v["generated"]])
        for x_, vv in zip(cx, vals): o.append(t(x_, y, f"{vv:,}" if isinstance(vv, int) else vv, 1.5))
    y += 5
    if RFQ():
        y = para(o, 12, y, "The front is traced from the mockup; areas the mockup does not show (body sides under the sleeves, the back, sleeve back halves) are generated from it, "
                 f"so the cloud band runs round the back and sleeves at the same height — {cf()}. Cells under the zips are filled from the cells beside them.", 140, 1.5, MUTED)
        y += 2; o.append(t(12, y, "Your answers on knitting this design: factory questions F2–F3 (q1–q9).", 1.8, 700))
    else:
        y = para(o, 12, y, f"* filled across a garment detail (CF zip, pocket zips + pulls) from the surrounding cells.  ** not visible in the mockup: body sides under the sleeves "
                 f"(reflected from the traced columns), the whole back (= front mirrored at the side seams), sleeve back halves (= front half mirrored) — GENERATED, not traced "
                 f"(back design {cf()}: band continued, no motif). Trace vs mockup: {AGREE['agree_front']*100:.1f} % pixel agreement over the visible front, {AGREE['agree_band']*100:.1f} % in the cloud band, {AGREE['agree_sleeve']*100:.1f} % on the visible sleeves (J3).", 140, 1.5, MUTED)
        y += 2; o.append(t(12, y, "Mill questions: F2–F3 q1–q9 (TD chair B13: the Rev F 'for the mill' box is folded into F2).", 1.8, 700))
    return o

def p_j2():
    o = H("J2 · PANEL MAPS — size M", "Each panel's cell map with its cut line (black), sew line (grey) and pocket opening (red). Lighter cells = GENERATED (not visible in the mockup).", "J2")
    xs = [(12, "front_R_M_birdA", "F02 front right — option A (bird knitted)"), (66, "front_L_M", "F01 front left"),
          (120, "back_M", "B01 back (generated)"), (190, "sleeve_R_M", "S01 sleeve right"), (243, "sleeve_L_M", "S02 sleeve left")]
    for x, tag, lab in xs:
        w = 66 if "back" in tag else 52
        img_fit(o, f"{OUT}/jacquard/prev_{tag}.png", x, 34, w, 150); o.append(t(x, 32, lab, 1.6, 700))
    o.append(t(12, 194, "Option B map (F02 without the bird) is in the zip: HK-FL-PIXSKY_JQ_front_R_SIZE_birdB. Sleeves: front half (toward the body on the front view) traced, back half mirrored.", 1.6, 400, MUTED))
    return o

def p_j3_rfq():
    o = H("J3 · JACQUARD vs MOCKUP", "Cell maps drawn back into the mockup view, same scale.", "J3")
    img_fit(o, f"{OUT}/compare_jacquard_rfq.png", 12, 29, 200, 165)
    para(o, 218, 40, "A 2.5 mm cell cannot follow the mockup's finer edges, so cloud outlines step by one cell. "
         "A designer may touch up the PNG maps directly (1 px = 1 cell) — please send any change back to us before knitting.", 40, 1.7, INK, 3.2)
    return o

def p_j3():
    o = H("J3 · JACQUARD vs MOCKUP", f"Cell maps drawn back into the mockup view (same scale). Pixel agreement {AGREE['agree_front']*100:.1f} % visible front, "
          f"{AGREE['agree_band']*100:.1f} % cloud band, {AGREE['agree_sleeve']*100:.1f} % sleeves.", "J3")
    img_fit(o, f"{OUT}/compare_jacquard.png", 12, 29, 118, 168)
    tx = 136; y = 34; o.append(t(tx, y, "WHAT DIFFERS FROM THE MOCKUP, AND WHY", 2.2, 700)); y += 5
    ds, dc = AGREE["diff_sky_as_cream"] * 100, AGREE["diff_cream_as_sky"] * 100
    items = [("Traced per 2.5 mm cell (Rev B).", f"Rev A traced the clouds in 5 mm blocks on one global phase; the render's ~6–7 mm checker sits on an irregular grid, so its edges and the cream cut-outs were lost. Every cell is now decided on its own (Rev B band 94.4 %); with the regular checker lattice below the band agrees {AGREE['agree_band']*100:.1f} % pixel for pixel (Rev A 91.8 %): the lattice trades a few pixels for the mockup's regular look.", INK),
             ("Checker fringe regularised (Rev C).", f"The render's 2-colour checker along the cloud edges (~6–7 mm squares on an irregular AI grid) traced per cell as scattered single cells. "
              f"Checker areas are found by a 2-D checker filter on the render (both colours alternating along both axes), then drawn as a REGULAR lattice of {CHKQ} × {CHKQ} cell squares "
              f"({CHKQ * 2.5:.1f} mm [proposed]), phase fitted locally (± 2 squares) to the traced cells: {CHK['cells']:,} cells in {CHK['regions']} areas, {CHK['agree'] * 100:.0f} % of them keep their traced colour. "
              f"Only whole squares (Rev D): a square half inside an area is completed ({CHK['completed_cells']} cells), a smaller part is given back to its surroundings ({CHK['dropped_cells']} cells).", PROP),
             ("No floating cells (Rev D).", (f"Every map, all sizes: {GJQ['islands_total']} sky / cream islands of ≤ 2 cells ({GJQ['maps']} maps; gates_jq.py, red on {GJQ['selftest']['caught']}/{GJQ['selftest']['planted']} planted specks). " if GJQ else "")
              + f"Islands of ≤ {JQS['speck_max']} cells (rim leftovers, mirror seams) take their surroundings' colour; the bird's own gaps are kept.", INK),
             ("Cell edges (diff map, left).", f"Red = render sky / map cream ({ds:.1f} % of judged pixels), orange = render cream / map sky ({dc:.1f} %). They lie on the cloud outlines: a 2.5 mm cell cannot follow a 0.6 mm render pixel edge. No cloud, cut-out or checker group is missing; part of the difference is the checker lattice (above).", INK),
             ("FILLED (zip, pocket zips + pulls).", "Cells under the CF zip and the pocket zips are mirrored from the traced cells across the detail's edge, row by row (Rev A grew a majority inward and left horizontal stripes).", PROP),
             ("GENERATED (not in the mockup).", f"Body sides under the sleeves (reflected from the traced columns), the whole back (front mirrored at the side seams), sleeve back halves (the traced half mirrored about the sleeve centre line; the hidden strips of the front half about one fixed column each, Rev D) — lighter cells on J2. Back: band continued round back + sleeves at the same height, no back motif ({cf()}).", INK),
             ("Sparkles.", f"Cells under the embroidered sparkles are sky: the sparkles sew on top. Their anti-aliased render rim (up to {JQS['rim_foot_px']} px out) is sky too and never counts as checker (Rev D: Rev C left cream specks there).", INK),
             ("Low-res source.", "Redrawn from a low-res mockup (~0.6 mm per render pixel). No close-ups: the founder is happy with this fidelity (21 Oct), none needed. A designer may touch up the PNG maps directly (1 px = 1 cell).", INK)]
    for h, body, col in items:
        o.append(t(tx, y, h, 1.75, 700, col)); y += 3.3; y = para(o, tx + 2, y, body, 92, 1.6, col, 2.9) + 1.8
    return o

# ---------------------------------------------------------------- G pages (embroidery)
def e3_ref():
    c = PLACE["files"]["E3"]["centre"]; return c, mM["Lu"] - c[1]

def p_g1():
    o = H("G1 · EMBROIDERY — overview, placement, sherpa set-up", "Sparkles are embroidered. Bird: knitted (option A) or embroidered E1B (option B). Numbers read from the stitch files (DST).", "G1")
    img_fit(o, f"{OUT}/flat_front_A.png", 12, 30, 140, 66)
    hd = ["File", "Element", "Piece", "Use", "Art mm", "Stitches", "Trims", "Stops", "Threads", "Max st.", "Run min*"]
    cx = [150, 160, 189, 199, 213, 230, 245, 254, 262, 271, 280]
    y = 33
    for x_, h_ in zip(cx, hd): o.append(t(x_, y, h_, 1.3, 700, MUTED))
    for F, nm, use in FILES:
        r = GATES[F]; y += 4.2
        vals = [F, nm.split(" — ")[0], r["piece"], {"E1": "opt A + B", "E2": "always", "E3": "always", "E1B": "opt B only"}[F], f"{r['size_mm'][0]:.0f}×{r['size_mm'][1]:.0f}", f"{r['stitches']:,}", r["trims"], r["stops"], r["threads"], r["max_stitch"], r["machine_min"]]
        for x_, v in zip(cx, vals): o.append(t(x_, y, str(v), 1.4, 700 if x_ == cx[0] else 400))
    b = GATES[BIG]["size_mm"]
    y += 4.6; o.append(t(150, y, f"Largest file {BIG} {b[0]:.0f} × {b[1]:.0f} mm: one hooping each — please confirm on your frames (F2–F3 q11).", 1.4, 400, PROP))
    y += 3.4; o.append(t(150, y, f"* run minutes estimated at {PROF['spm']} spm incl. trims + colour changes [proposed]. Option A = E1 + E2 + E3; option B = E1B + E2 + E3.", 1.35, 400, MUTED))
    for opt, fs in (("A", ["E1", "E2", "E3"]), ("B", ["E1B", "E2", "E3"])):
        y += 3.4; st = sum(GATES[F]["stitches"] for F in fs); tr = sum(GATES[F]["trims"] for F in fs); mn = sum(GATES[F]["machine_min"] for F in fs)
        o.append(t(150, y, f"Option {opt}: {st:,} stitches · {tr} trims · {mn:.1f} min machine time · 3 hoopings (F01, F02, S02)", 1.45))
    y = 104; o.append(t(12, y, "SHERPA SET-UP (high pile) — every file", 2.2, 700)); y += 4.6
    for s_ in ["Embroider the CUT jacquard panels (F01, F02, S02) before assembly [proposed — confirm your practice].",
               "Backing: cutaway 2.5 oz under the panel, hooped with the panel (or adhesive cutaway + floated panel if the pile crushes in the hoop — F2–F3 q12).",
               "Topping: water-soluble film (~40 µm) ON TOP of the pile, hooped / basted over the design area, so stitches sit on the pile instead of sinking. Tear + mist away after sewing, brush the pile up.",
               "Fill: tatami 0.40 mm, 0° rows (= the pixel rows), stitch 3.5, pull comp 0.30, underlay edge run + 90° lattice — denser than on a flat fabric so the pile does not poke through [proposed — strike-off].",
               "Needle 75/11 sharp, 40 wt polyester threads; speed per your sherpa practice. Hoop marks: brush / steam the pile after removal."]:
        y = para(o, 14, y, "•  " + s_, 150, 1.6, PROP) + 0.8
    y += 2; o.append(t(12, y, "PLACEMENT (design centre = file origin, mm, size M). Per-size positions = DXF layer-8 marks (plot PDF); art 100 % in every size.", 1.6, 700)); y += 4
    for F, nm, use in FILES:
        c = PLACE["files"][F]["centre"]; pc = PLACE["files"][F]["piece"]
        if F == "E3":
            c3, dc = e3_ref()
            s_ = f"{F}  {pc}  centre x {c3[0]:+.1f} from the sleeve centre line, y {c3[1]:.1f} below the underarm line (M) = {dc:.1f} above the cuff seam — kept from the cuff seam in every size"
        else:
            s_ = f"{F}  {pc}  centre x {c[0]:+.1f} from CF (+ = wearer's left), y {c[1]:.1f} below the CF neck seam — kept from the neck seam in every size"
        o.append(t(14, y, s_ + f"  ·  file {GATES[F]['size_mm'][0]:.0f} × {GATES[F]['size_mm'][1]:.0f} mm", 1.5)); y += 3.4
    mn = {}
    for sz, rows in CLR.items():
        for r in rows:
            if r["edge"] == "inside the piece": continue
            mn[(r["el"], r["edge"])] = min(mn.get((r["el"], r["edge"]), 1e9), r["mm"])
    allok = all(r["ok"] for rows in CLR.values() for r in rows)
    tight = ", ".join(f"{e} {min(v for (el, ed), v in mn.items() if el == e):.1f} mm" for e in ("E1", "E2", "E3"))
    y += 1
    if RFQ(): o.append(t(14, y, f"Clearance from seams, zip and pocket opening measured on every size XS–3XL: closest {tight} (min CF/zip 15 mm, pocket 6 mm).", 1.5, 400, MUTED))
    else: o.append(t(14, y, f"Keep-out check XS–3XL: {'ALL PASS' if allok else 'FAIL'} · tightest: " + tight, 1.55, 700, GREEN if allok else RED))
    return o

def stops_table(o, F, tx, y):
    r = GATES[F]; o.append(t(tx, y, "COLOUR STOPS", 2.0, 700)); y += 4
    for x_, h_ in zip([tx, tx + 7, tx + 34, tx + 76, tx + 90], ["Stop", "Thread", "Isacord / Polyneon (or your nearest)", "Stitches", "Trims"]): o.append(t(x_, y, h_, 1.5, 700, MUTED))
    for s, thr in zip(r["per_stop"], r["stop_threads"]):
        y += 3.8; i_, p_ = tech.match(TH[thr], "isacord"), tech.match(TH[thr], "polyneon")
        o.append(f'<rect x="{tx + 7}" y="{y - 2.3}" width="3" height="2.6" fill="{TH[thr]}" stroke="#999" stroke-width="0.1"/>')
        o.append(t(tx, y, str(s["stop"]), 1.55)); o.append(t(tx + 11, y, f"{THN[thr]} {TH[thr]}", 1.5)); o.append(t(tx + 34, y, f"{i_[0]} / {p_[0]}", 1.5))
        o.append(t(tx + 76, y, f"{s['stitches']:,}", 1.55)); o.append(t(tx + 90, y, str(s["trims"]), 1.55))
    return y

def p_gfile_rfq(F, nm, use, page):
    r = GATES[F]
    o = H(f"{page} · {F} — {nm}", f"{use.capitalize()}. {r['stitches']:,} stitches · {r['trims']} trims · {r['stops']} colour stops · {r['threads']} threads · max stitch {r['max_stitch']} mm · file {r['size_mm'][0]} × {r['size_mm'][1]} mm", page)
    img_fit(o, f"{OUT}/compare_{F}_rfq.png", 12, 28, SW - 24, 110)
    y = stops_table(o, F, 12, 146)
    tx = 126; y = 146; o.append(t(tx, y, "PLACEMENT + FILES", 2.0, 700)); y += 4.4
    pc = PLACE["files"][F]["piece"]
    if F == "E3":
        c3, dc = e3_ref(); pl = f"{pc}: centre x {c3[0]:+.1f} mm from the sleeve centre line, {dc:.1f} mm above the cuff seam (M; kept in every size)"
    else:
        c = PLACE["files"][F]["centre"]; pl = f"{pc}: centre x {c[0]:+.1f} mm from CF, {c[1]:.1f} mm below the CF neck seam (M; kept in every size)"
    for l in [pl, "Per-size positions = DXF layer-8 marks (plot PDF). Art 100 % in every size.",
              f"Files: elements/HK-FL-PIXSKY_{F}.dst + .pes; art/HK-FL-PIXSKY_{F}_ART.svg (true size, one layer per thread).",
              "Fill: tatami 0° rows (= the pixel rows); sherpa set-up on G1."]:
        y = para(o, tx, y, l, 95, 1.6, INK, 3.0) + 0.6
    return o

def p_gfile(F, nm, use, page):
    r = GATES[F]
    o = H(f"{page} · {F} — {nm}", f"{use}. {r['stitches']:,} stitches · {r['trims']} trims · {r['stops']} stops · {r['threads']} threads · max stitch {r['max_stitch']} mm · {r['machine_min']} min · file {r['size_mm'][0]} × {r['size_mm'][1]} mm (DST read-back)", page)
    img_fit(o, f"{OUT}/compare_{F}.png", 12, 28, SW - 24, 104)
    tx = 12; y = stops_table(o, F, tx, 138)
    y += 6; o.append(t(tx, y, "FILE GATES (gates_fl.json)", 2.0, 700)); y += 4
    cl = r["colour"]; dr = r["direction"]
    for ok, s_ in [(r["motifs_pass"] == r["motifs_n"], f"A14 shape: {r['motifs_pass']}/{r['motifs_n']} motifs (IoU ≥ 0.70, w/h ≥ 80 %), min IoU {min(m['iou'] for m in r['motifs']):.2f}"),
                   (r["colour_ok"], f"Colour per motif: {sum(c['ok'] for c in cl)}/{len(cl)} sewn in the render's colour"),
                   (not r["uncovered"], f"A15 uncovered ≥ 25 mm²: {len(r['uncovered'])} gaps"),
                   (not r["coherence"], f"A16 angle coherence: {len(r['coherence'])} fails on {r['coherence_parts']} parts (visible stitches)"),
                   (dr["ok"], f"A16/A17 chaos: {dr['chaos_tiles']}/{dr['tiles']} tiles (≤ 5 %)"),
                   (not r["exposed_035"], f"Exposed stitches: {len(r['exposed_035'])} at halo 0.35 ({len(r['exposed_025'])} at 0.25 = pull-comp corners)")]:
        o.append(t(tx, y, ("PASS  " if ok else "FAIL  ") + s_, 1.55, 600, GREEN if ok else RED)); y += 3.4
    o.append(t(tx, y, "Direction vs reference: NOT JUDGED — no close-up; the render shows pile curls, not thread grain.", 1.5, 400, MUTED)); y += 3.2
    o.append(t(tx, y, f"Declared: tatami 0° on every motif (pixel rows). Trims per 10k stitches {r['trims_per_10k']} (reported).", 1.5, 400, MUTED))
    tx2 = 112; y = 138; o.append(t(tx2, y, "MOTIF ROWS (A14 shape + colour, vs the render's pixels)", 2.0, 700)); y += 4
    for m in r["motifs"][:12]:
        o.append(t(tx2, y, f"{m['colour']:<6} at ({m['x_mm']:.0f}, {m['y_mm']:.0f})  IoU {m['iou']:.2f}  w {m['w_ratio']:.2f}  h {m['h_ratio']:.2f}", 1.45, 400, GREEN if m["ok"] else RED)); y += 3.1
    y += 1
    for c in cl[:12]:
        o.append(t(tx2, y, f"colour at ({c['x_mm']:.0f}, {c['y_mm']:.0f}): render {c['expected']} → sewn {c['stitched']}", 1.4, 400, GREEN if c["ok"] else RED)); y += 2.9
    para(o, 206, 140, "ART: traced from the low-res mockup (inputs/front.png, 0.6 mm/px, no close-ups). Counts, sizes, positions and colours are the mockup's. "
         "Every sparkle is redrawn as its own pixel sprite: a stack of 1-3 concentric 4-arm crosses (arms, shoulder steps, centre block) whose widths and "
         "lengths are fitted to the render by a blur model (the blurred drawing must reproduce the blurred render pixels). Sparkles ≥ 16 mm may keep one "
         "arm longer when the render shows it; smaller ones are drawn as a plain 4-arm plus (the render is too blurred for their inner steps). "
         "Touching sparkles (bird wing pair) are split by colour first. "
         + ("Sleeve: shapes true size; each motif's position mapped from the hanging sleeve onto the sleeve pattern. " if F == "E3" else "")
         + ("Bird = the jacquard bird cells (same drawing as option A). Original pixel art: IP cleared by the founder 21 Oct." if F == "E1B" else ""), 46, 1.5, MUTED, 2.8)
    return o

# ---------------------------------------------------------------- F pages: strike-off + factory questions
def p_f1():
    o = H("F1 · STRIKE-OFF + THREADS — please answer before bulk", f"{NAME} ({STYLE}) · what we need from the factory", "F1")
    y = 34
    def h2(s):
        nonlocal y; o.append(t(12, y, s, 3.0, 700)); y += 5
    def line(s, col=INK, x=16, size=2.1):
        nonlocal y; o.append(t(x, y, s, size, 400, col)); y += 3.6
    h2("1  Strike-off (sew-out) — first, before any bulk")
    line("Sew these size-M files on the real shell fabric, in the bulk finish (no garment wash [proposed — confirm]), with the proposed threads + backing:")
    for F, nm, _ in FILES:
        line(f"•  HK-FL-PIXSKY_{F}.dst  —  {GATES[F]['piece']} — {nm}  ·  {GATES[F]['stitches']:,} stitches  ·  {GATES[F]['trims']} trims", x=20)
    line("Send back: (a) photos straight-on in daylight + one raking-light close-up per colour area, with a ruler in shot;")
    line("(b) design size measured after sewing vs the spec (width x height, mm) — tells us the pull / shrink;")
    line("(c) pile poke-through, puckering, hoop marks, thread breaks, any area you would digitise differently;")
    line("(d) actual run time per hooping and your price for it.")
    y += 2; h2("2  Wash test of the knit-down")
    line("Wash the knit-down per your care recommendation: shrinkage % (warp / weft), colour fastness incl. navy binding on cream (bleed), pile matting. Photos before / after.")
    line(CARE + "  [proposed — confirm]", PROP, size=1.9)
    y += 2; h2("3  Thread card / lab dip")
    line("Please send your thread colour card, or dip these colours; propose your nearest match:")
    for k, hx in TH.items():
        i_ = tech.match(hx, "isacord"); p_ = tech.match(hx, "polyneon")
        line(f"•  {THN[k]} {hx}  —  closest Isacord {i_[0]} (ΔE {i_[3]:.1f}) / Polyneon {p_[0]} (ΔE {p_[3]:.1f})", RED if i_[3] > factory.DE_ASK else INK, x=20)
    y += 2; h2("4  Frames, colours per file, quote basis")
    line("Frames, colours per file, hooping or floating on pile and how you price embroidery: factory questions F2–F3 q10–q13.")
    line("Total stitches and trims per piece are on the embroidery pages (G).", MUTED)
    return o

FQ = [("Knit sherpa (colours knitted in)", [
        "Can you knit the design into the sherpa placed per panel, so each pattern piece has its own map as in our files? If not, can you knit a continuous border repeat that we place when cutting?",
        "Our maps are one per panel and per size. Do you price set-up per map, per size or per panel? What is your MOQ in metres or pieces per map, per size and per colourway?",
        "What machine gauge do you use? After brushing, how many stitches and courses per cm are finished? Which file format do you want (we can supply indexed BMP or PNG, or export others)?",
        "Fabric: fibre content in %, pile type (curly or straight), pile height in mm, single- or double-face, weight in g/m², usable width in cm, shrinkage in % warp and weft, colourfastness rating.",
        "What is the smallest motif detail you can hold on this pile, in mm?",
        "Can you add a third colour (black) in one small area only (the bird)? Is there an extra cost or MOQ?",
        "Can you knit the plain cream collar-inner panel in the same run?",
        "Please send a daylight photo of the reverse of a similar knitted sherpa with a ruler in shot. Is the reverse acceptable as the inside face of an unlined jacket, or do you recommend a lining or bonding?",
        "What are the price and lead time in days for a knit-down of the front-right panel in size M?"]),
      ("Embroidery on the sherpa", [
        "Do you embroider in-house? If you subcontract, will the same shop do bulk?",
        "What is your maximum frame size in mm, and the maximum number of thread colours per file?",
        "Do you hoop the panel or float it on adhesive cutaway? Do you use water-soluble topping on pile?",
        "What are the strike-off price per file and the lead time in days? How do you price embroidery: per thousand stitches, per trim, per hooping or per piece?"]),
      ("Collar, bindings, zips, pockets, seams", [
        "Can you source a smooth sky-blue nylon taslan dyed to our colour standard? MOQ and lead time?",
        "Can you make a stand collar with a taslan outer and a sherpa inner and the zip running to the top? What construction do you suggest?",
        "Can you bind the hem and cuffs (with an elastic channel) and pipe the neck seam with navy taslan bias binding on this pile? Do you shave the pile in the binding allowance?",
        "Navy taslan for binding, tape and facing: in stock? MOQ?",
        "Black separating coil CF zip with a blue pull, and navy coil pocket zips with blue pulls: stock or custom? Please send stock colour cards. MOQ and lead time?",
        "Can you set the CF zip on this pile without pile catching in the coil (for example by shaving the zip allowance)? Do you recommend a zip garage at the collar top?",
        "Can you make a vertical zip pocket with a slit opening in this pile? Which slit finish do you recommend? Will you send a photo of a mock-up on a scrap before cutting?",
        "Seams: do you recommend overlock plus taslan tape, or flatlock, on this pile? What stitches per inch do you use for each seam?"]),
      ("Labels and packing", [
        "Can you make the woven main and size labels and the printed care/content/COO label? MOQ?",
        "Can you supply the hangtag and polybag? Which fold do you recommend so the pile is not crushed?"]),
      ("Samples, price, timing", [
        "Fit sample in M in a plain stock sherpa of the same pile height and weight as the quoted quality: cost and lead time in days?",
        "Jacquard prototype in M with embroidery: cost and lead time in days?",
        "Price per piece at each quantity on the cover, with sampling and set-up charges listed separately from bulk.",
        "Bulk lead time from approval, your factory closure dates for Chinese New Year, and your latest approval date for goods to land in Ohio in early April.",
        "Please also tell us the seam allowance and shrinkage % you used on the samples."])]

def p_fq(groups, start, page, cont=False):
    o = H(f"{page} · FACTORY QUESTIONS" + (" (continued)" if cont else ""), "Please answer each with YES / NO, or a value plus a unit. Write in the right-hand column or reply by email quoting the number.", page)
    y = 33; n = start
    for gname, qs in groups:
        o.append(t(12, y, gname.upper(), 2.1, 700)); y += 4.4
        for q in qs:
            lines = wrap(q, 128); h = max(len(lines) * 3.1, 6.2) + 1.6; zebra(o, n, y, h)
            o.append(t(13, y, f"{n}.", 1.7, 700))
            for j, l in enumerate(lines): o.append(t(19, y + j * 3.1, l, 1.65))
            o.append(t(214, y, "YES / NO", 1.5, 600, MUTED)); blank(o, 230, y + 3.0, 55)
            y += h + 0.6; n += 1
        y += 2
    return o

def f_pages():
    return [p_fq(FQ[:2], 1, "F2"), p_fq(FQ[2:], 1 + sum(len(q) for _, q in FQ[:2]), "F3", True)]

# ---------------------------------------------------------------- Q pages
def p_q1():
    o = H("Q1 · REQUEST FOR QUOTATION — please quote and fill in", "We ask you to name the prices. Detailed questions: F2–F3. Amber = proposed — confirm.", "Q1")
    y = 33; o.append(t(12, y, "PLEASE QUOTE", 2.4, 700)); y += 4.6
    for x_, h_ in zip([12, 120, 150], ["Item", "Price (state currency)", "Lead time (days)"]): o.append(t(x_, y, h_, 1.6, 700, MUTED))
    items = [("1  Jacquard knit-down", "front-right panel F02, size M (bird + cloud band + pocket area), photographed flat with a ruler; then the wash test (F1 §2)"),
             ("2  Fit sample, size M", FITS.replace(" — mandatory before the size set.", "")),
             ("3  Embroidery strike-off", "E1B + E2, size M, on a sherpa offcut (F1 §1)"),
             ("4  Jacquard prototype, size M", "full jacket with embroidery, from our maps + files")]
    for i, (a, b_) in enumerate(items):
        y += 5.6; zebra(o, i, y, 7.6, 11, 186)
        o.append(t(12, y, a, 1.65, 700)); para(o, 14, y + 2.6, b_, 140, 1.35, MUTED, 2.3)
        blank(o, 120, y, 26); blank(o, 150, y, 30); y += 2.4
    y += 9; o.append(t(12, y, "BULK — price per piece, FOB origin port  [proposed — confirm]", 2.0, 700)); y += 4.4
    o.append(t(12, y, "Quantity (pcs)  [proposed — confirm]", 1.55, 700, MUTED))
    for j, q in enumerate(LADDER): o.append(t(70 + j * 29, y, f"{q}", 1.7, 700, PROP))
    for lab in ("Option A — bird knitted (3 colours)", "Option B — bird embroidered (2 colours)"):
        y += 5; o.append(t(12, y, lab, 1.55))
        for j in range(len(LADDER)): blank(o, 70 + j * 29, y, 24)
    y += 5
    for l in ["Sampling and set-up charges listed separately from bulk (F2–F3 q26). Please price per layout and per size, not only per piece (F2–F3 q2).",
              "Size ratio: quote per size run across XS–3XL; ratio to follow  [proposed — confirm]."]:
        y = para(o, 12, y, l, 105, 1.55, PROP, 2.9)
    tx = 192; ty = 33; o.append(t(tx, ty, "PLEASE TELL US", 2.4, 700)); ty += 4.6
    for q in ["MOQ per colourway (pcs)", "MOQ per order (pcs)", "MOQ, placed (engineered) jacquard sherpa (m / pcs)", "MOQ with a 3rd colour (black bird)",
              "Sample lead time incl. the jacquard knit-down (days)", "Bulk lead time incl. fabric knitting (days)",
              "Chinese New Year: last working day before", "Chinese New Year: first working day after",
              "Knit gauge", "Max colours in the pile jacquard", "Minimum motif cell (mm)", "Pile height you propose (mm)", "Fabric weight you propose (g/m²)",
              "Embroidery: in-house or subcontracted?", "Payment terms"]:
        o.append(t(tx, ty, q, 1.5)); blank(o, tx + 62, ty, 31); ty += 4.25
    y = max(y, ty) + 3
    o.append(t(12, y, "TERMS + RETURN", 2.0, 700)); y += 4
    for l in ["Incoterm: FOB origin port. Payment terms: per your standard — please state. Samples to: Haki Studios, Ohio (address with the order).  [proposed — confirm]",
              "Reply by: ________________          Colour standard: T5 (" + TCX + ").  [proposed — confirm]"]:
        y = para(o, 12, y, l, 175, 1.55, PROP, 2.9)
    y += 1.5; o.append(t(12, y, "ATTACHED", 2.0, 700)); y += 3.8
    for l in ["This PDF · pattern/: DXF per size + all sizes (AAMA, mm; layer 8 = embroidery positions), 1:1 plot PDF size M",
              "jacquard/: cell map per panel + size (indexed PNG + BMP, 1 px = 1 cell) · elements/: embroidery files DST + PES · art/: embroidery art SVG (true size) · compare/: previews"]:
        o.append(t(12, y, l, 1.5)); y += 3.2
    return o

QOPEN = [("Decide with the factory", [
            "Bird: knitted black (option A) if you can add a 3rd colour in the bird area; otherwise embroidered (option B, file E1B ready) — F2–F3 q6.",
            "Knit method: placed per panel (our maps) or a continuous border repeat placed in cutting — F2–F3 q1-q2.",
            "Shell fabric: fibre content, pile, weight, width, shrinkage; is the reverse acceptable inside an unlined jacket — F2–F3 q4, q8.",
            "Seams: overlock + taslan tape or flatlock; pile shaving in seam / binding / zip allowances — F2–F3 q16, q19, q21.",
            "Pocket slit finish and bag anchoring (CF facing or side seam) — F2–F3 q20. Zip garage at the collar top: do you recommend one? — F2–F3 q19.",
            "Collar construction: taslan outer, sherpa inner, zip to the top — F2–F3 q15.",
            "Trim colours: navy binding / tape / facing, black CF zip with blue pull, navy pocket zips with blue pulls — your stock cards, F2–F3 q17-q18.",
            "Labels, hangtag, polybag, fold and carton packing (T6) — F2–F3 q22-q23."]),
         ("Haki Studios will send", [
            "Pantone TCX for each colour (T5); until then match the hex. " + DIP + ".",
            "Label artwork, RN / manufacturer ID, care text, carton marks; size ratio; reply-by date; sample address."]),
         ("Decided at sampling", [
            FITS, "Knit-down: bird detail and cloud edges judged flat with a ruler; wash test (F1 §2).",
            "Embroidery strike-off on the pile: size, pull, poke-through, hoop marks (F1 §1).", "Stretched sleeve opening (T3 H2) measured on the fit sample."])]

def p_q2():
    o = H("Q2 · OPEN POINTS", "What is still open in this pack and where it gets decided. Everything amber in the pack is proposed — confirm.", "Q2")
    y = 34
    for gname, items in QOPEN:
        o.append(t(12, y, gname.upper(), 2.3, 700)); y += 4.8
        for s_ in items: y = para(o, 14, y, "•  " + s_, 165, 1.7, PROP if gname != "Decided at sampling" else INK, 3.1) + 1.0
        y += 3
    return o

def p_q3():
    o = H("Q3 · DECISIONS LOG + HOLDS (internal)", "Founder answers (STATUS.json), assumptions still proposed, and the TD chair's section (c) holds for the first sample / size set.", "Q3")
    st = json.load(open("STATUS.json")) if os.path.exists("STATUS.json") else {}
    y = 34; o.append(t(12, y, "OPEN (internal board)", 2.2, 700)); y += 4.6
    for i, q in enumerate(st.get("questions", []), 1): y = para(o, 14, y, f"{i}. {q}", 170, 1.5, RED, 2.8) + 0.6
    y += 2; o.append(t(12, y, "ANSWERED BY THE FOUNDER (closed)", 2.2, 700)); y += 4.6
    for a in st.get("answered", []):
        y = para(o, 14, y, f"✓ {a['date']}: {a['answer']}", 170, 1.5, GREEN, 2.8) + 0.2
    y += 2; o.append(t(12, y, "HOLDS FOR THE FIRST SAMPLE / SIZE SET (TD chair section c — not in the RFQ)", 2.2, 700)); y += 4.6
    for s_ in ["PS-22 pile ease: bicep / armhole / zipped collar may feel tight; judge at the M fit sample in a sherpa of matching pile, human fit session (HOLD).",
               "PS-23 collar neck not graded: try L + 3XL zipped at the size set; Nick decides whether J grades for fleece (HOLD).",
               "PS-24 grade steps (A into 3XL, C at L) inherited from the Drum Island chart: Nick confirms (HOLD).",
               "PS-25 motif-to-band gap changes across sizes (bird/sparkles anchor to the neck, band to the hem): Nick reviews XS + 3XL maps before the size set.",
               "PS-26 render slimmer than the block: the sample will look boxier. PS-17 bird resolution and PS-18 sparkles on pile: judged on the knit-down / strike-off photos.",
               "Red flags: per-map set-up cost (fallback = border repeat + option B); CNY 2027 vs early-April Ohio landing; flammability if the fibre is not 100 % polyester."]:
        y = para(o, 14, y, "•  " + s_, 170, 1.5, PROP, 2.8) + 0.5
    return o

def p_r1():
    o = H("R1 · LESSONS CHECKS — before delivery", "Every check from LESSONS.md that applies to this product, with its result. Numbers from the generated files.", "R1")
    allA = all(GATES[F]["motifs_pass"] == GATES[F]["motifs_n"] for F in GATES)
    nE1 = GATES["E1"]["motifs_n"]; distinct = sum(GATES[F]["motifs_n"] for F in GATES) - nE1      # E1B repeats E1's sparkles
    tg = json.load(open(TXTGATE)) if os.path.exists(TXTGATE) else None
    rows = [("A2/A11/A14", "Motif counts + silhouettes vs the mockup", f"{len(PLACE['sparkles'])} sparkles + bird = {distinct} motifs; A14 " + ", ".join(f"{F} {GATES[F]['motifs_pass']}/{GATES[F]['motifs_n']}" for F in GATES) + " (E1B repeats E1's)", allA),
            ("A3/C8", "Keep-outs on every size (pattern pieces)", "clearances.json XS–3XL", all(r["ok"] for rows in CLR.values() for r in rows)),
            ("A7", "IP: copyrighted character?", "bird = original pixel art, not from a game — cleared by the founder 21 Oct", "DONE"),
            ("A10", "Low-res source stated on the art pages", "G2–G5, J3 (internal); close-ups not needed (founder 21 Oct)", "DONE"),
            ("A14+", "Colour per motif (render core hue vs sewn stop)", ", ".join(f"{F} {sum(c['ok'] for c in GATES[F]['colour'])}/{len(GATES[F]['colour'])}" for F in GATES), all(GATES[F]["colour_ok"] for F in GATES)),
            ("A15", "Details masked; qa.uncovered on every file", "gaps ≥ 25 mm²: " + ", ".join(f"{F} {len(GATES[F]['uncovered'])}" for F in GATES), all(not GATES[F]["uncovered"] for F in GATES)),
            ("A16", "qa.angle_coherence (visible stitches per part)", ", ".join(f"{F} {len(GATES[F]['coherence'])} fails/{GATES[F]['coherence_parts']}" for F in GATES), all(not GATES[F]["coherence"] for F in GATES)),
            ("A16/A17", "qa.direction_match: chaos ≤ 5 %; vs reference", ", ".join(f"{F} {GATES[F]['direction']['chaos_tiles']}/{GATES[F]['direction']['tiles']}" for F in GATES) + " chaotic; vs reference NOT RUN (no close-up)", all(GATES[F]["direction"]["ok"] for F in GATES)),
            ("guards", "New gates red on a planted defect (gates_selftest.py)", ("colour " + str(SELFTEST["colour_red"]) + " / A15 " + str(SELFTEST["a15_red"]) + " / A16 " + str(SELFTEST["a16_red"]) + " rows red; 0 on the shipped E2") if SELFTEST else "not run", bool(SELFTEST and SELFTEST["ok"])),
            ("J-isl", "Jacquard: no ≤ 2-cell island (all maps, sizes)", (f"{GJQ['islands_total']} islands in {GJQ['maps']} maps; planted {GJQ['selftest']['caught']}/{GJQ['selftest']['planted']} caught (gates_jq.py)") if GJQ else "not run", bool(GJQ and GJQ["ok"])),
            ("B5", f"≤ {PROF['needles']} threads per file (PES)", ", ".join(f"{F} {GATES[F]['threads']}" for F in GATES), all(GATES[F]["threads"] <= PROF["needles"] for F in GATES)),
            ("B7/B17", "Max stitch ≤ 7.5 mm (DST)", ", ".join(f"{F} {GATES[F]['max_stitch']}" for F in GATES), all(GATES[F]["max_stitch"] <= 7.5 for F in GATES)),
            ("B8/B20", "Trims + stitches from the DST read-back", "gates_fl.json via readback.dst (process)", "DONE"),
            ("B27", "Exposed stitches on the exact geometry", "0 on every file at halo 0.35 (pull 0.30) — ENGINE_NOTES 2", all(not GATES[F]["exposed_035"] for F in GATES)),
            ("C1–C3", "Pattern shape checks (neck scoop, SA) + seam walks", "all sizes, incl. neck tape NT1 vs neck seam", all(SHAPE.values()) and all(WALKS.values())),
            ("C2", "Half measures converted", "chart vs pattern all sizes", all(CHECK.values())),
            ("C6/C7", "Proposed values marked; drafted not fitted", "amber everywhere; fit sample required (process)", "DONE"),
            ("D1", "Every page rendered + looked at", "prev_*.png both copies (process)", "DONE"), ("D2", "PDF recompressed", SMALL_EV, SMALL_OK),
            ("RFQ", "Supplier copy: no internal / old-factory text (rfq_text_gate)", (f"{tg['rfq_hits']} hits in the RFQ copy; same gate finds {tg['internal_hits']} in the internal copy (red-then-green)") if tg else "not run", bool(tg and tg["ok"]))]
    y = 34
    for x_, h_ in zip([12, 34, 112, 250], ["Lesson", "Check", "Evidence", "Result"]): o.append(t(x_, y, h_, 1.8, 700, MUTED))
    for i, (a, b_, c, ok) in enumerate(rows):
        y += 5.0
        if i % 2 == 0: o.append(f'<rect x="11" y="{y - 3.4}" width="{SW - 22}" height="5.0" fill="{ALT}"/>')
        o.append(t(12, y, a, 1.65, 700)); o.append(t(34, y, b_, 1.55)); o.append(t(112, y, c[:100], 1.45, 400, MUTED))
        lab_, col_ = ("DONE", MUTED) if ok == "DONE" else (("PASS", GREEN) if ok else (("OPEN", ORANGE) if ok is None else ("FAIL", RED)))
        o.append(t(250, y, lab_, 1.7, 700, col_))
    y += 6; o.append(t(12, y, "PASS / FAIL = measured from the generated files. DONE = a process step (no file to measure).", 1.5, 400, MUTED))
    return o

# ---------------------------------------------------------------- supplier-copy text gate (TD chair L1)
BANNED = [r"factory\.json", r"gates?_", r"\bgates?\b", r"\bIoU\b", r"LESSONS", r"status_set", r"[Ff]actory said", r"[Ff]ounder", r"\bIP\b",
          r"\bRev [A-F]\b", r"Claude", r"\.py\b", r"\.json\b", r"inputs/", r"Drum Island", r"Mandy", r"read-back", r"phoenix", r"sprite",
          r"\bA1[0-9]\b", r"\bPS-\d", r"\bTD\b", r"chair", r"confirmed\)\s*$"]
def text_hits(pdf):
    """[(page, pattern, snippet)] for every banned string in the rendered PDF text"""
    hits = []
    for i, pg in enumerate(PdfReader(pdf).pages, 1):
        tx = pg.extract_text() or ""
        for pat in BANNED[:-1]:
            for m in re.finditer(pat, tx): hits.append((i, pat, tx[max(0, m.start() - 30): m.end() + 30].replace("\n", " ")))
    return hits

def render(pages, out):
    w = PdfWriter(); tag = os.path.basename(out).split("_")[2].lower()
    for i, pg in enumerate(pages, 1):
        svg = doc(pg); pdf = f"{PG}/{tag}_p{i:02d}.pdf"; cairosvg.svg2pdf(bytestring=svg.encode(), write_to=pdf)
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{PG}/prev_{tag}_p{i:02d}.png", output_width=2000)
        w.append(PdfReader(pdf))
    w.write(out); print("pages", len(pages), out, round(os.path.getsize(out) / 1e6, 1), "MB")

def build_mode(mode):
    global MODE
    MODE = mode
    names = ["T1 Cover", "Q1 Request for quotation", "T2 Flats + construction", "T3 Size chart + how to measure", "T4 Pattern pieces + cut list",
             "T5 BOM + trims + colour standard", "T6 Labels + packaging", "T7 Seams, stitches + assembly", "J1 Jacquard method + files", "J2 Jacquard panel maps (M)",
             "J3 Jacquard vs mockup", "G1 Embroidery overview + placement", "G2 E1 sparkles (F02)", "G3 E2 sparkles (F01)", "G4 E3 sleeve sparkles (S02)",
             "G5 E1B bird + sparkles (option B)", "F1 Strike-off + threads", "F2–F3 Factory questions", "Q2 Open points"]
    if not RFQ(): names += ["Q3 Decisions log + holds (internal)", "R1 LESSONS checks (internal)"]
    index, k = [], 1
    for n in names: index.append((n, k)); k += 2 if n.startswith("F2") else 1
    gf = p_gfile_rfq if RFQ() else p_gfile
    pages = [p_cover(index), p_q1(), p_flats(), p_pom(), p_pieces(), p_bom(), p_labels(), p_seams(), p_j1(), p_j2(), p_j3_rfq() if RFQ() else p_j3(), p_g1()]
    for (F, nm, use), pg in zip(FILES, ["G2", "G3", "G4", "G5"]): pages.append(gf(F, nm, use, pg))
    pages += [p_f1()] + f_pages() + [p_q2()]
    if not RFQ(): pages += [p_q3(), p_r1()]
    out = f"{OUT}/HAKI_{STYLE}_{'RFQ' if RFQ() else 'TECHPACK'}_{REV.replace(' ', '')}.pdf"
    render(pages, out); return out, len(pages)

def build():
    for sz in SIZES: assert CHECK[sz] and WALKS[sz] and SHAPE[sz], f"pattern QA failed {sz}"
    rfq, n_r = build_mode("rfq"); inn, n_i = build_mode("internal")
    hr, hi = text_hits(rfq), text_hits(inn)
    json.dump(dict(ok=not hr and len(hi) > 0, rfq_hits=len(hr), internal_hits=len(hi), rfq=[list(h) for h in hr][:50], internal_sample=[list(h) for h in hi][:10]),
              open(TXTGATE, "w"), indent=1, ensure_ascii=False)
    for h in hr: print("RFQ TEXT GATE:", h)
    assert hi, "rfq_text_gate found nothing in the INTERNAL copy — the gate is blind (red-then-green failed)"
    assert not hr, f"rfq_text_gate: {len(hr)} internal / old-factory strings in the supplier copy"
    _, n_i = build_mode("internal")                    # rebuild so R1 shows this run's gate result
    print("rfq_text_gate ok:", len(hi), "hits in internal, 0 in RFQ")
    return rfq, inn

if __name__ == "__main__":
    build()
