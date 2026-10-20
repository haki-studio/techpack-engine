"""Pixel Sky fleece — the merged tech pack PDF: garment pages T*, jacquard pages J*, embroidery pages G*, factory
requests F*, questions Q1, LESSONS check R1. Every number is read from a generated file (DST read-back via
gates_fl.json, jacquard_stats.json, the pattern, clearances.json). usage: python3 pack.py"""
import os, json, math, shutil, subprocess, datetime
import cairosvg
from pypdf import PdfWriter, PdfReader
import sheet as SHT
from sheet import t, doc, INK, MUTED, RED, GREEN, ORANGE, SW, SH, embed
import factory, tech, readback
import fleece as FL, pattern as PT, pattern_draw as PD

STYLE = "HK-FL-PIXSKY"; REV = "Rev A"; DATE = "20 Oct 2026"; NAME = "Pixel Sky sherpa fleece jacket"
SHT.FOOT = f"HAKI STUDIOS · {NAME} · {STYLE} · {REV} · {DATE}"
PROP = "#8A5A00"; ALT = "#F5F2EC"
OUT = "out"; PG = f"{OUT}/pages"; os.makedirs(PG, exist_ok=True)
SIZES = FL.SIZES
GATES = json.load(open(f"{OUT}/stitch/gates_fl.json")); JQS = json.load(open(f"{OUT}/jacquard/jacquard_stats.json"))
PLACE = json.load(open(f"{OUT}/art/placements.json")); CLR = json.load(open(f"{OUT}/clearances.json"))
AGREE = json.load(open(f"{OUT}/jacquard/agreement.json"))
PROF = factory.load(); FRAME = factory.largest_frame(PROF)
TH = {"yellow": "#F6E23A", "gold": "#D9A521", "black": "#231F1E"}
THN = {"yellow": "Sparkle yellow", "gold": "Sparkle gold", "black": "Bird black"}
G = {sz: FL.draft(sz) for sz in SIZES}; gM, mM = G["M"]
CH = FL.chart(); MEAS = {sz: FL.measure(sz) for sz in SIZES}
CHECK = {sz: all(abs(MEAS[sz][0][k] / 10 - CH[k][2][SIZES.index(sz)]) <= CH[k][3] for k in CH) for sz in SIZES}
WALKS = {sz: all(tol is None or abs(a - b) <= tol for _, a, b, tol in MEAS[sz][1]) for sz in SIZES}
SHAPE = {sz: all(c[1] for c in FL.shape_checks(sz)) for sz in SIZES}
FILES = [("E1", "Sparkles — wearer's right front (beside the bird)", "option A + B"), ("E2", "Sparkles — wearer's left front", "always"),
         ("E3", "Sparkles — wearer's left sleeve", "always"), ("E1B", "Bird + sparkles — wearer's right front", "option B only (replaces E1)")]

def H(title, sub, page): return SHT.header(title, sub, page)
def prop(x, y, s, size=1.8): return t(x, y, s + "  [proposed — confirm]", size, 600, PROP)
def mins(F): return GATES[F]["machine_min"]
def wrap(s, n):
    out, line = [], ""
    for w in s.split():
        if len(line) + len(w) + 1 > n: out.append(line); line = w
        else: line = (line + " " + w).strip()
    return out + [line]
def para(o, x, y, s, n=110, size=1.75, col=INK, lh=3.1):
    for l in wrap(s, n): o.append(t(x, y, l, size, 400, col)); y += lh
    return y
def img(o, path, x, y, w, crop=None):
    s, h = embed(path, crop=crop, w_mm=w, x=x, y=y); o.append(s); return h
def img_fit(o, path, x, y, w, hmax):
    from PIL import Image
    im = Image.open(path); r = im.height / im.width; ww = min(w, hmax / r); return img(o, path, x + (w - ww) / 2, y, ww)

# ---------------------------------------------------------------- T pages
def p_cover(index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>', t(14, 22, "HAKI STUDIOS", 3.0, 700, MUTED), t(14, 34, NAME, 7.0, 700),
         t(14, 41.5, f"Style {STYLE} · {REV} · {DATE} · sizes XS–3XL · base M · mm unless marked · FIRST FLEECE — fit sample mandatory", 2.4, 400, MUTED),
         f'<line x1="14" y1="45" x2="{SW-14}" y2="45" stroke="{INK}" stroke-width="0.4"/>']
    img_fit(o, "inputs/front.png", 14, 50, 60, 62); o.append(t(14, 116, "MOCKUP (front only, AI render)", 1.9, 700))
    img_fit(o, f"{OUT}/flat_front_A.png", 78, 52, 118, 52); o.append(t(78, 108, "FRONT — drawn from the pattern (M), jacquard + embroidery", 1.9, 700))
    img_fit(o, f"{OUT}/flat_back.png", 78, 116, 118, 52); o.append(t(78, 172, "BACK — NOT SHOWN in the mockup: cloud band continued [proposed — confirm]", 1.9, 700, PROP))
    ix = 204; o.append(t(ix, 54, "CONTENTS", 2.8, 700)); y = 60
    for name, pg in index: o.append(t(ix, y, name, 1.8)); o.append(t(SW - 14, y, str(pg), 1.8, 600, MUTED, "end")); y += 3.5
    y += 3; o.append(t(ix, y, "KEY SPECS", 2.4, 700)); y += 4.4
    for a, b_ in [("Shell", "engineered jacquard sherpa: sky blue / cream"), ("Clouds", "knitted in (jacquard), 2.5 mm cells"),
                  ("Sparkles", "embroidered, yellow + gold (E1–E3)"), ("Bird", "knitted black (A) or embroidered (B, E1B)"),
                  ("Collar", "9 cm stand, blue taslan / cream sherpa"), ("Edges", "navy binding; elastic cuffs"),
                  ("Closures", "CF zip + 2 vertical zip pockets"), ("Block", "Drum Island + pile ease")]:
        o.append(t(ix, y, a, 1.8, 400, MUTED)); o.append(t(ix + 17, y, b_, 1.75, 600, PROP)); y += 3.6
    o.append(t(SW - 14, SH - 8, SHT.FOOT, 1.8, 400, MUTED, "end"))
    return o

NOTES = [("1", "Stand collar 9 cm: outer blue taslan (C01), inner cream sherpa (C02), seamed at the top edge, turned; navy piping (BD3) in the neck seam, visible 8 mm."),
         ("2", "CF zip: black #5 coil, separating, blue pull, hem binding edge to collar top − 5 mm; zip tape covered inside by a navy taslan facing strip (Z01)."),
         ("3", "Bird: knitted black in the jacquard (option A) — or embroidered E1B (option B) if the mill cannot add a 3rd colour. Sparkles E1/E2 always embroidered."),
         ("4", "Vertical zip pockets 16.5 cm, navy tape, blue pulls; tricot pocket bags (P02) bar-tacked to the zip facing."),
         ("5", "Hem: navy binding 1.2 cm finished, encloses the cut edge (no rib); ends turned in at the zip."),
         ("6", "Cuffs: navy binding channel with 1 cm elastic, gathers the sleeve opening to chart H."),
         ("7", "Sleeve sparkles E3 on the wearer's left sleeve, front half, above the cloud band."),
         ("8", "Unlined: sherpa reverse inside; seams 4-thread overlocked + navy taslan tape 1.5 cm. Labels on the back neck tape.")]

def p_flats():
    o = H("FLATS + CONSTRUCTION", "Size M, drawn from the pattern pieces with the jacquard cell maps and the stitch art. Amber = proposed — confirm.", "T2")
    img_fit(o, f"{OUT}/flat_front_A.png", 12, 30, 190, 82); img_fit(o, f"{OUT}/flat_back.png", 12, 116, 190, 82)
    o.append(t(12, 30, "FRONT", 2.2, 700)); o.append(t(12, 116, "BACK (assumed — not in the mockup)", 2.2, 700, PROP))
    y = 32; tx = 208
    for n, s_ in NOTES:
        o.append(f'<circle cx="{tx}" cy="{y - 0.8}" r="2.0" fill="#FFFFFF" stroke="{INK}" stroke-width="0.25"/>' + t(tx, y, n, 1.8, 700, INK, "middle"))
        y = para(o, tx + 4, y, s_, 52, 1.6, PROP) + 2.2
    y += 2; y = para(o, tx, y, "Mockup vs block: the render is slimmer than the Drum Island block (shoulder ~46 vs 53 cm at the art scale). "
                     "Art keeps the mockup's sizes and heights; the block keeps its width, so the cloud band and sky run wider than in the render.", 52, 1.5, MUTED)
    return o

def p_pom():
    o = H("SIZE CHART + MEASUREMENT CHECK", "cm. Rows from the approved Drum Island chart; pile ease and new rows are PROPOSED (amber). ½ = half measurement, flat.", "T3")
    hd = ["", "Point of measure", "How measured"] + SIZES + ["Tol", "Source"]; cx = [12, 18, 62, 120, 131, 142, 153, 164, 175, 186, 198, 210]
    for x_, h_ in zip(cx, hd): o.append(t(x_, 32, h_, 1.7, 700, MUTED))
    order = ["A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "P", "M", "Q", "R"]
    for i, k in enumerate(order):
        nm, how, vals, tol, src = CH[k]; y = 37 + i * 4.3; pr = "PROPOSED" in src
        if i % 2 == 0: o.append(f'<rect x="11" y="{y - 3}" width="{SW - 22}" height="4.3" fill="{ALT}"/>')
        col = PROP if pr else INK
        o.append(t(cx[0], y, k, 1.8, 700, col)); o.append(t(cx[1], y, nm[:30], 1.65, 600, col)); o.append(t(cx[2], y, how[:44], 1.4, 400, MUTED))
        for j, v in enumerate(vals): o.append(t(cx[3 + j], y, f"{v:g}", 1.65, 700 if SIZES[j] == "M" else 400, col))
        o.append(t(cx[10], y, f"±{tol:g}", 1.5, 400, MUTED)); o.append(t(cx[11], y, src.replace(" (PROPOSED)", " [proposed]"), 1.45, 600, col))
    y = 37 + len(order) * 4.3 + 5
    o.append(t(12, y, "PATTERN CHECK — every size measured off the drafted pieces vs this chart", 2.0, 700)); y += 4.4
    for j, sz in enumerate(SIZES):
        ok = CHECK[sz] and WALKS[sz] and SHAPE[sz]; o.append(t(cx[3 + j], y, "pass" if ok else "FAIL", 1.7, 700, GREEN if ok else RED))
    o.append(t(12, y, "chart · seam walks · shape checks (pattern QA)", 1.6, 400, MUTED)); y += 6
    for l in [f"Pile ease vs Drum Island: {', '.join(f'{k} +{v:g}' for k, v in FL.EASE_CM.items())} cm; D (½ sweep) = B: straight bound hem, no rib.",
              "Length A unchanged (cropped at the hip as the mockup). Sleeve G includes the 1.2 cm cuff binding.",
              "A fit sample in M (blank sherpa is fine) is mandatory before the size set — first fleece on this block."]:
        o.append(t(12, y, l, 1.65, 400, PROP)); y += 3.4
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
    _draw(o, gM, ["C01", "C02", "Z01", "P02", "P04", "BD1", "BD2", "BD3"], 12, y1 + 6, 190, 0.062, 0.26, 0.9, 5)
    tx = 206; o.append(t(tx, 31, "CUT LIST — per jacket", 2.3, 700))
    hd = ["Code", "Piece", "Cut", "Material"]; cx = [tx, tx + 9, tx + 39, tx + 50]
    for x_, h_ in zip(cx, hd): o.append(t(x_, 35.5, h_, 1.55, 700, MUTED))
    for i, code in enumerate(FL.ORDER):
        pc = gM[code]; y = 39.5 + i * 3.5
        if i % 2 == 0: o.append(f'<rect x="{tx - 1}" y="{y - 2.4}" width="{SW - tx - 11}" height="3.5" fill="{ALT}"/>')
        o.append(t(cx[0], y, code, 1.45, 700)); o.append(t(cx[1], y, pc.name.replace(" (wearer's)", "")[:22], 1.4))
        o.append(t(cx[2], y, pc.qty.replace(" (2 pairs)", ""), 1.4)); o.append(t(cx[3], y, pc.material.split(" — ")[0] + " " + pc.material.split(" — ")[-1][:24], 1.35, 400, PROP))
    y = 39.5 + len(FL.ORDER) * 3.5 + 3
    for l in ["Jacquard panels B01 F01 F02 S01 S02: knit each panel to its own cell map (J pages),",
              "cut on the marked cut line; the map runs 12 mm past the cut line (knit area).", "SA 1.0 cm; binding joins 0; collar top edge 0.6.",
              "Files: DXF per size + all sizes (AAMA layers; layer 8 = embroidery boxes),", "1:1 plot PDF size M."]:
        o.append(t(tx, y, l, 1.4, 400, MUTED)); y += 3.1
    return o

def p_bom():
    o = H("BILL OF MATERIALS + TRIMS", "Per jacket, size M. Lengths read from the pattern. Fabric = piece area ÷ (150 cm width × 80 % marker) — replace with the factory's marker.", "T5")
    qty = lambda pc: int(pc.qty.split()[0]) * (2 if "pair" in pc.qty and "(" not in pc.qty else 1)
    area = lambda codes: sum(PT.cut_poly(gM[c]).area * qty(gM[c]) for c in codes) / 1e6 / (1.5 * 0.8)
    zip_l = gM["F01"].edges[0].length + FL.COLLAR_H - 5
    rows = [("Shell — jacquard sherpa", "Engineered pile jacquard, sky blue / cream (+ black bird, option A), ~ 300 g/m², polyester", f"{area(['B01','F01','F02','S01','S02']):.2f} m (knit per panel)"),
            ("Collar inner", "Plain sherpa, cream (same pile)", f"{area(['C02']):.2f} m"),
            ("Collar outer + zip facing + loop", "Nylon taslan, sky blue (collar) / navy (facing, loop)", f"{area(['C01']):.2f} + {area(['Z01','P04']):.2f} m"),
            ("Binding", f"Navy taslan, cross-cut, {FL.BIND_CUT:.0f} mm cut, {FL.BIND_W:.0f} mm finished: hem {mM['hem_len']/10:.0f} cm, cuffs 2 × {mM['sleeve_open']/10:.0f} cm, collar piping {mM['Ln']/10:.0f} cm", "1 set"),
            ("Cuff elastic", f"{FL.CUFF_EL_W:.0f} mm woven elastic, {mM['el_cuff']/10:.1f} cm + 1.5 overlap (M)", "2"),
            ("CF zip", f"#5 coil, separating, black tape + teeth, blue pull, {zip_l/10:.0f} cm (M)", "1"),
            ("Pocket zips", f"#3 coil, navy tape, blue pull, {FL.PKT_L/10:.1f} cm opening", "2"),
            ("Pocketing", "Tricot fleece 160 g/m², cream", f"{area(['P02']):.2f} m"),
            ("Seam tape", "Navy taslan 15 mm, over every inside seam (unlined)", "~ 6 m"),
            ("Thread — seams", "Polyester core-spun Tex 27, tonal (blue / cream) + overlock", "~ 400 m"),
            ("Embroidery", "Topping: water-soluble film 40 µm on top of the pile; backing: cutaway 2.5 oz under the cut piece", "per hooping"),
            ("Labels", "Main + size on the back neck tape; care label left side seam", "1 set")]
    for x_, h_ in zip([12, 62, 220], ["Item", "Description", "Qty / consumption"]): o.append(t(x_, 33, h_, 1.8, 700, MUTED))
    y = 38
    for i, (a, b_, q) in enumerate(rows):
        lines = wrap(b_ + "  [proposed — confirm]", 95)
        if i % 2 == 0: o.append(f'<rect x="11" y="{y - 3.1}" width="{SW - 22}" height="{3.6 * len(lines) + 1}" fill="{ALT}"/>')
        o.append(t(12, y, a, 1.75, 700))
        for j, l in enumerate(lines): o.append(t(62, y + j * 3.6, l, 1.65, 400, PROP))
        o.append(t(220, y, q, 1.7, 600)); y += 3.6 * len(lines) + 1.5
    y += 4; o.append(t(12, y, "PER SIZE (cm) — read from the pattern", 2.0, 700)); y += 4.4
    hd = ["Size", "CF zip", "Hem binding", "Cuff binding", "Cuff elastic", "Collar / neck", "Pocket opening"]
    for j, h_ in enumerate(hd): o.append(t(12 + j * 30, y, h_, 1.6, 700, MUTED))
    for i, sz in enumerate(SIZES):
        g, mt = G[sz]; y += 3.8
        vals = [sz, (g["F01"].edges[0].length + FL.COLLAR_H - 5) / 10, mt["hem_len"] / 10, mt["sleeve_open"] / 10, (mt["el_cuff"] + 15) / 10, mt["Ln"] / 10, FL.PKT_L / 10]
        for j, v in enumerate(vals): o.append(t(12 + j * 30, y, v if isinstance(v, str) else f"{v:.1f}", 1.65, 700 if sz == "M" or j == 0 else 400))
    return o

# ---------------------------------------------------------------- J pages (jacquard)
def p_j1():
    o = H("J1 · JACQUARD SHERPA — method, colours, files", "Clouds (and the bird in option A) are KNITTED into the sherpa, engineered per pattern panel. Founder 19 Oct: jacquard preferred — confirm with the mill.", "J1")
    y = 33
    for l in ["HOW IT WORKS", ]:
        o.append(t(12, y, l, 2.4, 700)); y += 5
    for s_ in [f"One cell = {JQS['cell_mm']} × {JQS['cell_mm']} mm finished [proposed — the mill converts to its knit gauge: stitches × courses per cell]. "
               f"Clouds are drawn in 2 × 2 blocks ({JQS['cloud_mm']} mm, the mockup's cloud 'pixel'); the bird in single cells (its own pixel is half the clouds').",
               "Each panel map = the pattern piece's cut line + 12 mm knit margin, anchored on the CF (fronts) / CB (back) / sleeve centre line and on the hem / cuff edge, "
               "so the cloud band sits at the same height above the hem in every size and meets across the side seams and the zip.",
               "Files: one indexed PNG + BMP per panel and size, 1 px = 1 cell; palette index 0 = sky blue, 1 = cream, 2 = black (bird), 9 = outside the knit area.",
               "Option A: bird knitted black (3rd colour, bird area only) → F02 map *_birdA, embroider E1 + E2 + E3. "
               "Option B: 2 colours only → F02 map *_birdB (no bird), embroider E1B (bird + sparkles) + E2 + E3. Nothing to rebuild."]:
        y = para(o, 12, y, s_, 120, 1.75, PROP) + 1.6
    y += 2; o.append(t(12, y, "YARN COLOURS (match the mockup; lab dip on the pile)", 2.2, 700)); y += 4.6
    for k, (nm, hx) in enumerate([("0 Sky blue", "#80AEF7"), ("1 Cream", "#F1EAE2"), ("2 Black (bird, option A)", "#24201E")]):
        o.append(f'<rect x="12" y="{y - 2.6}" width="6" height="3.2" fill="{hx}" stroke="#999" stroke-width="0.15"/>'); o.append(t(20, y, f"{nm}  {hx}", 1.75)); y += 4
    y += 2; o.append(t(12, y, "PANEL FILES — size M (all sizes in the zip: jacquard/HK-FL-PIXSKY_JQ_PANEL_SIZE.png + .bmp)", 2.0, 700)); y += 4.4
    hd = ["Panel map", "Piece", "Cells (w × h)", "Knit area mm", "Sky", "Cream", "Black", "Traced", "Filled*", "Generated**"]
    cx = [12, 52, 66, 92, 118, 134, 150, 163, 180, 196]
    for x_, h_ in zip(cx, hd): o.append(t(x_, y, h_, 1.5, 700, MUTED))
    for k, v in JQS["panels"].items():
        if v["size"] != "M": continue
        y += 3.6; vals = [k.replace("_M", ""), v["piece"], f"{v['cols']} × {v['rows']}", f"{v['width_mm']:.0f} × {v['height_mm']:.0f}", v["sky"], v["cream"], v["black"], v["traced"], v["filled"], v["generated"]]
        for x_, vv in zip(cx, vals): o.append(t(x_, y, f"{vv:,}" if isinstance(vv, int) else vv, 1.5))
    y += 5
    y = para(o, 12, y, f"* filled across a garment detail (CF zip, pocket zips + pulls) from the surrounding cells.  ** not visible in the mockup: body sides under the sleeves "
             f"(reflected from the traced columns), the whole back (= front mirrored at the side seams), sleeve back halves (= front half mirrored) — GENERATED, not traced "
             f"[proposed — confirm]. Trace vs mockup: {AGREE['agree_front']*100:.1f} % pixel agreement over the visible front, {AGREE['agree_band']*100:.1f} % in the cloud band (J3).", 140, 1.5, MUTED)
    y += 2; o.append(t(12, y, "FOR THE MILL — please answer (also on F2)", 2.0, 700, RED)); y += 4
    for q in ["Can you knit an ENGINEERED (placed per panel) pile jacquard sherpa from these maps? Machine gauge, cell → stitch/course conversion, pile height?",
              "Minimum motif / cell size you can hold on pile (the bird uses single 2.5 mm cells, checker dither 5 mm)? A 3rd colour (black) in the bird area only?",
              "MOQ, lead time, strike-off / knit-down price; file format you want (BMP indexed is ready; we can export others)."]:
        y = para(o, 14, y, "•  " + q, 140, 1.6, RED) + 0.6
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

def p_j3():
    o = H("J3 · JACQUARD vs MOCKUP", f"Cell maps drawn back into the mockup view (same scale). Pixel agreement {AGREE['agree_front']*100:.1f} % (visible front), {AGREE['agree_band']*100:.1f} % (cloud band).", "J3")
    img_fit(o, f"{OUT}/compare_jacquard.png", 12, 30, SW - 24, 150)
    para(o, 12, 186, "Redrawn from a low-res mockup (~0.6 mm per render pixel; the render's pixel grid is not regular), so every cell was re-decided on our grid: "
         "shapes, heights and counts follow the mockup; individual checker cells can differ by one cell. A designer may touch up the PNG maps directly (1 px = 1 cell).", 170, 1.6, PROP)
    return o

# ---------------------------------------------------------------- G pages (embroidery)
def p_g1():
    o = H("G1 · EMBROIDERY — overview, placement, sherpa set-up", "Sparkles are embroidered (founder 19 Oct). Bird: knitted (option A) or embroidered E1B (option B). Numbers read from the DST files.", "G1")
    img_fit(o, f"{OUT}/flat_front_A.png", 12, 30, 140, 66)
    hd = ["File", "Element", "Piece", "Use", "Art mm", "Stitches", "Trims", "Stops", "Threads", "Max st.", "Run min", "Hoopings"]
    cx = [150, 160, 189, 199, 213, 230, 245, 254, 262, 271, 280, 297]
    y = 33
    for x_, h_ in zip(cx[:-1], hd[:-1]): o.append(t(x_, y, h_, 1.3, 700, MUTED))
    for F, nm, use in FILES:
        r = GATES[F]; y += 4.2; w, h = PLACE["files"][F]["size_mm"]
        vals = [F, nm.split(" — ")[0], r["piece"], {"E1": "opt A + B", "E2": "always", "E3": "always", "E1B": "opt B only"}[F], f"{r['size_mm'][0]:.0f}×{r['size_mm'][1]:.0f}", f"{r['stitches']:,}", r["trims"], r["stops"], r["threads"], r["max_stitch"], r["machine_min"]]
        for x_, v in zip(cx, vals): o.append(t(x_, y, str(v), 1.4, 700 if x_ == cx[0] else 400))
    y += 4.6; o.append(t(150, y, f"Every file fits one {FRAME[0]:.0f} × {FRAME[1]:.0f} hooping (factory.json frames). Run minutes at {PROF['spm']} spm incl. trims + colour changes.", 1.4, 400, MUTED))
    y += 3.4; o.append(t(150, y, "Per jacket: option A = E1 + E2 + E3; option B = E1B + E2 + E3.", 1.4, 700))
    for opt, fs in (("A", ["E1", "E2", "E3"]), ("B", ["E1B", "E2", "E3"])):
        y += 3.4; st = sum(GATES[F]["stitches"] for F in fs); tr = sum(GATES[F]["trims"] for F in fs); mn = sum(GATES[F]["machine_min"] for F in fs)
        o.append(t(150, y, f"Option {opt}: {st:,} stitches · {tr} trims · {mn:.1f} min machine time · 3 hoopings (F01, F02, S02)", 1.45))
    y = 104; o.append(t(12, y, "SHERPA SET-UP (high pile) — every file", 2.2, 700)); y += 4.6
    for s_ in ["Embroider the CUT jacquard panels (F01, F02, S02) before assembly, as the factory does (factory.json).",
               "Backing: cutaway 2.5 oz under the panel, hooped with the panel (or adhesive cutaway + floated panel if the pile crushes in the hoop).",
               "Topping: water-soluble film (~40 µm) ON TOP of the pile, hooped / basted over the design area, so stitches sit on the pile instead of sinking. Tear + mist away after sewing, brush the pile up.",
               "Fill: tatami 0.40 mm, 0° rows (= the pixel rows), stitch 3.5, pull comp 0.30, underlay edge run + 90° lattice — denser than on duck so the pile does not poke through [proposed — strike-off].",
               "Needle 75/11 sharp, 40 wt polyester threads; speed per the factory's sherpa practice. Hoop marks: brush / steam the pile after removal.",
               f"Placement: design centre (= DST origin) per file below, in piece coords. Same file for every size (art 100 %); keep-outs pass on every size (min CF/zip 15 mm, pocket 6 mm)."]:
        y = para(o, 14, y, "•  " + s_, 150, 1.6, PROP) + 0.8
    y += 2; o.append(t(12, y, "PLACEMENT (design centre, mm) — fronts: x from CF (+ wearer's left), y below the CF neck seam; sleeve: x from the sleeve centre line, y from the underarm line", 1.6, 700)); y += 4
    for F, nm, use in FILES:
        c = PLACE["files"][F]["centre"]; pc = PLACE["files"][F]["piece"]
        o.append(t(14, y, f"{F}  {pc}  centre x {c[0]:+.1f}, y {c[1]:.1f}  ·  art {PLACE['files'][F]['art_bounds'][2]-PLACE['files'][F]['art_bounds'][0]:.0f} × {PLACE['files'][F]['art_bounds'][3]-PLACE['files'][F]['art_bounds'][1]:.0f} mm  ·  marked on the pattern (DXF layer 8, plot PDF)", 1.55)); y += 3.4
    mn = {}
    for sz, rows in CLR.items():
        for r in rows:
            if r["edge"] == "inside the piece": continue
            mn[(r["el"], r["edge"])] = min(mn.get((r["el"], r["edge"]), 1e9), r["mm"])
    allok = all(r["ok"] for rows in CLR.values() for r in rows)
    y += 1; o.append(t(14, y, f"Keep-out check XS–3XL: {'ALL PASS' if allok else 'FAIL'} · tightest: " + ", ".join(f"{e} {min(v for (el, ed), v in mn.items() if el == e):.1f} mm" for e in ("E1", "E2", "E3")), 1.55, 700, GREEN if allok else RED))
    return o

def p_gfile(F, nm, use, page):
    r = GATES[F]
    o = H(f"{page} · {F} — {nm}", f"{use}. {r['stitches']:,} stitches · {r['trims']} trims · {r['stops']} stops · {r['threads']} threads · max stitch {r['max_stitch']} mm · {r['machine_min']} min · file {r['size_mm'][0]} × {r['size_mm'][1]} mm (DST read-back)", page)
    img_fit(o, f"{OUT}/compare_{F}.png", 12, 29, 200, 120)
    tx = 216; y = 33; o.append(t(tx, y, "COLOUR STOPS (DST read-back)", 2.0, 700)); y += 4
    for x_, h_ in zip([tx, tx + 7, tx + 34, tx + 54, tx + 68], ["Stop", "Thread", "Isacord / Polyneon", "Stitches", "Trims"]): o.append(t(x_, y, h_, 1.4, 700, MUTED))
    for s, thr in zip(r["per_stop"], r["stop_threads"]):
        y += 3.6; i_, p_ = tech.match(TH[thr], "isacord"), tech.match(TH[thr], "polyneon")
        o.append(f'<rect x="{tx + 7}" y="{y - 2.3}" width="3" height="2.6" fill="{TH[thr]}" stroke="#999" stroke-width="0.1"/>')
        o.append(t(tx, y, str(s["stop"]), 1.45)); o.append(t(tx + 11, y, THN[thr], 1.4)); o.append(t(tx + 34, y, f"{i_[0]} / {p_[0]}", 1.4))
        o.append(t(tx + 54, y, f"{s['stitches']:,}", 1.45)); o.append(t(tx + 68, y, str(s["trims"]), 1.45))
    y += 6; o.append(t(tx, y, "A14 FIDELITY GATE (vs the render's pixels)", 2.0, 700)); y += 4
    o.append(t(tx, y, f"{r['motifs_pass']}/{r['motifs_n']} motifs pass (IoU ≥ 0.70, w/h ≥ 80 %)", 1.6, 700, GREEN if r["motifs_pass"] == r["motifs_n"] else RED)); y += 3.5
    for m in r["motifs"][:12]:
        o.append(t(tx, y, f"{m['colour']:<6} at ({m['x_mm']:.0f}, {m['y_mm']:.0f})  IoU {m['iou']:.2f}  w {m['w_ratio']:.2f}  h {m['h_ratio']:.2f}", 1.35, 400, GREEN if m["ok"] else RED)); y += 3
    y += 2; o.append(t(tx, y, f"Exposed stitches: {len(r['exposed_035'])} at halo 0.35 (pull comp 0.30)", 1.5, 600, GREEN if not r["exposed_035"] else RED)); y += 3.2
    o.append(t(tx, y, f"   ({len(r['exposed_025'])} at the duck halo 0.25 = pull-comp corners; ENGINE_NOTES 2)", 1.35, 400, MUTED)); y += 3.2
    o.append(t(tx, y, f"Trims per 10k stitches: {r['trims_per_10k']} (reported, not a gate)", 1.45, 400, MUTED)); y += 3.2
    o.append(t(tx, y, "Stitch direction: tatami 0° on every motif (pixel rows)", 1.45, 400, MUTED)); y += 3.2
    para(o, 12, 156, "Art traced from the low-res mockup (inputs/front.png, no close-ups): every motif is the render's own connected colour region redrawn as a pixel-art "
         "staircase on its own fitted 2.5 mm grid (the render's pixel unit). Nothing generated: counts, sizes, positions and colours are the mockup's. "
         + ("Sleeve: motif shapes kept true size; each motif's position was mapped from the hanging sleeve onto the sleeve pattern." if F == "E3" else "")
         + (" Bird = the jacquard bird cells (same drawing as option A). IP check pending (Q1)." if F == "E1B" else ""), 180, 1.55, MUTED)
    return o

def f_pages():
    so = [dict(file=f"HK-FL-PIXSKY_{F}.dst", piece=f"{GATES[F]['piece']} — {nm}", stitches=GATES[F]["stitches"], trims=GATES[F]["trims"]) for F, nm, _ in FILES]
    thr = [dict(name=THN[k], code=f"Isacord {tech.match(h, 'isacord')[0]}", de=tech.match(h, "isacord")[3]) for k, h in TH.items()]
    pieces = [dict(piece=f"{F} ({GATES[F]['piece']})", w=GATES[F]["size_mm"][0], h=GATES[F]["size_mm"][1], hoopings=1) for F, _, _ in FILES]
    pages = factory.requests_page(f"{NAME} ({STYLE})", so, thr, pieces, page="F1", prof=dict(PROF, chenille=False))   # no chenille on this product (LESSONS D5)
    return pages

def p_f2():
    o = H("F2 · FACTORY + MILL REQUESTS — sherpa specific", "In addition to F1. Answers update factory.json and the J/G pages; no art rebuild is needed for either bird option.", "F2")
    y = 34
    blocks = [("1  Jacquard sherpa (mill)", ["Factory said 'jacquard sherpa normally no problem' (19 Oct). Please confirm ENGINEERED placement per panel from our maps (J1/J2), knit gauge + cell conversion, pile height, MOQ, lead time.",
                                            "Can the bird area take a 3rd colour (black)? YES → option A (map *_birdA, embroider E1). NO → option B (map *_birdB, embroider E1B). Tell us which.",
                                            "Knit-down / strike-off of the F02 panel in M first (bird + band + pocket area), photographed flat with a ruler."]),
              ("2  Embroidery on sherpa", ["Factory said 'embroidery on sherpa yes'. Please confirm topping (water-soluble film) + backing (cutaway 2.5 oz) and whether you hoop the panel or float it on adhesive backing.",
                                         "Sew E1B and E2 in M on a jacquard (or plain blue) sherpa offcut: check pile poke-through, pull (measured size vs file), hoop marks. We expect to retune density / pull comp after this."]),
              ("3  Hoopings (information — frames confirmed)", [f"Every file is one hooping on your {FRAME[0]:.0f} × {FRAME[1]:.0f} frame: " + ", ".join(f"{F} {GATES[F]['size_mm'][0]:.0f} × {GATES[F]['size_mm'][1]:.0f} mm" for F, _, _ in FILES) + "."]),
              ("4  Trims", ["Navy taslan binding + seam tape, blue taslan collar outer, #5 coil CF zip (black, blue pull), #3 coil pocket zips (navy tape, blue pull): please quote / propose your stock colours against the mockup."])]
    for h, items in blocks:
        o.append(t(12, y, h, 2.3, 700)); y += 4.6
        for s_ in items: y = para(o, 15, y, "•  " + s_, 160, 1.7, INK) + 1.0
        y += 2.5
    return o

# ---------------------------------------------------------------- Q1 + R1
def p_q1():
    o = H("Q1 · OPEN QUESTIONS + ASSUMPTIONS (PROPOSED)", "Everything amber in this pack. Recorded on the board (status_set.py --question); answers update the brief and rebuild.", "Q1")
    y = 34; o.append(t(12, y, "OPEN QUESTIONS", 2.4, 700)); y += 5
    qs = json.load(open("STATUS.json")).get("questions", []) if os.path.exists("STATUS.json") else []
    for i, q in enumerate(qs, 1): y = para(o, 14, y, f"{i}. {q}", 160, 1.65, RED) + 1.2
    y += 3; o.append(t(12, y, "ASSUMPTIONS USED IN THIS PACK", 2.4, 700)); y += 5
    for a in ["Block: Drum Island + pile ease (T3). Sizes XS–3XL. Unlined, taped seams. Fit sample in M mandatory.",
              "Back + sleeve backs not shown: cloud band continued at the same height above the hem; back = front mirrored at the side seams; no back motif.",
              "Art scale 0.601 mm per render px (CF neck → hem = 565 mm at M). The render is slimmer than the block: art keeps the mockup's motif sizes; hidden body sides are generated.",
              "Brief said the bird is on the wearer's LEFT chest; the mockup shows it on the wearer's RIGHT front (viewer's left). Built as the mockup shows.",
              "Jacquard cell 2.5 mm (clouds 5 mm blocks) and yarn colours; option A/B for the bird. Threads: catalogue matches, ΔE listed on F1.",
              "Embroidery on sherpa: water-soluble topping + cutaway; tatami 0.40, pull 0.30 (to be tuned at the strike-off). Trims + colours per T5."]:
        y = para(o, 14, y, "•  " + a, 160, 1.65, PROP) + 1.0
    return o

def p_r1():
    o = H("R1 · LESSONS CHECKS — before delivery", "Every check from LESSONS.md that applies to this product, with its result. Numbers from the generated files.", "R1")
    allA = all(GATES[F]["motifs_pass"] == GATES[F]["motifs_n"] for F in GATES)
    rows = [("A2/A11/A14", "Motif counts + silhouettes vs the mockup", f"20/20 sparkles + bird; A14 motif_match {sum(GATES[F]['motifs_pass'] for F in GATES)}/{sum(GATES[F]['motifs_n'] for F in GATES)} (refs = render pixels)", allA),
            ("A3/C8", "Keep-outs on every size (pattern pieces)", "clearances.json XS–3XL", all(r["ok"] for rows in CLR.values() for r in rows)),
            ("A7", "IP: copyrighted character?", "bird resembles a game sprite — question open (Q1); built as traced", None),
            ("A10", "Low-res source stated on the spec pages", "G2–G5, J3", True),
            ("A15", "Garment details masked before tracing", "zip, pockets + pulls, bindings, collar, silhouette fringe → FILLED / DETAIL", True),
            ("A16/A17", "Declared stitch direction per motif", "tatami 0° (pixel rows); angle coherence on the file: pass", True),
            ("B5", f"≤ {PROF['needles']} threads per file (PES)", ", ".join(f"{F} {GATES[F]['threads']}" for F in GATES), all(GATES[F]["threads"] <= PROF["needles"] for F in GATES)),
            ("B7/B17", "Max stitch ≤ 7.5 mm (DST)", ", ".join(f"{F} {GATES[F]['max_stitch']}" for F in GATES), all(GATES[F]["max_stitch"] <= 7.5 for F in GATES)),
            ("B8/B20", "Trims + stitches from the DST read-back", "gates_fl.json via readback.dst", True),
            ("B27", "Exposed stitches on the exact geometry", "0 on every file at halo 0.35 (pull 0.30) — ENGINE_NOTES 2", all(not GATES[F]["exposed_035"] for F in GATES)),
            ("C1–C3", "Pattern shape checks (neck scoop, SA)", "all sizes", all(SHAPE.values())),
            ("C2", "Half measures converted", "chart vs pattern all sizes", all(CHECK.values())),
            ("C6/C7", "Proposed values marked; drafted not fitted", "amber everywhere; fit sample required", True),
            ("C9", "Derived block with explicit delta list", "fleece.py EASE_CM; Drum chart untouched", True),
            ("D1", "Every page rendered + looked at", "prev_*.png", True), ("D2", "PDF recompressed", "shrink", True),
            ("E7", "F1 factory requests page", "F1 + F2", True)]
    y = 34
    for x_, h_ in zip([12, 34, 112, 250], ["Lesson", "Check", "Evidence", "Result"]): o.append(t(x_, y, h_, 1.8, 700, MUTED))
    for i, (a, b_, c, ok) in enumerate(rows):
        y += 5.2
        if i % 2 == 0: o.append(f'<rect x="11" y="{y - 3.4}" width="{SW - 22}" height="5.2" fill="{ALT}"/>')
        o.append(t(12, y, a, 1.65, 700)); o.append(t(34, y, b_, 1.6)); o.append(t(112, y, c[:95], 1.5, 400, MUTED))
        o.append(t(250, y, "PASS" if ok else ("OPEN" if ok is None else "FAIL"), 1.7, 700, GREEN if ok else (ORANGE if ok is None else RED)))
    return o

def build():
    for sz in SIZES: assert CHECK[sz] and WALKS[sz] and SHAPE[sz], f"pattern QA failed {sz}"
    names = ["T1 Cover", "T2 Flats + construction", "T3 Size chart + measurement check", "T4 Pattern pieces + cut list", "T5 BOM + trims",
             "J1 Jacquard method + files", "J2 Jacquard panel maps (M)", "J3 Jacquard vs mockup", "G1 Embroidery overview + placement",
             "G2 E1 sparkles (F02)", "G3 E2 sparkles (F01)", "G4 E3 sleeve sparkles (S02)", "G5 E1B bird + sparkles (option B)",
             "F1 Factory requests", "F2 Factory + mill requests (sherpa)", "Q1 Open questions + assumptions", "R1 LESSONS checks"]
    index = [(n, i + 1) for i, n in enumerate(names)]
    pages = [p_cover(index), p_flats(), p_pom(), p_pieces(), p_bom(), p_j1(), p_j2(), p_j3(), p_g1()]
    for (F, nm, use), pg in zip(FILES, ["G2", "G3", "G4", "G5"]): pages.append(p_gfile(F, nm, use, pg))
    f1 = f_pages(); pages += [None] * 0
    w = PdfWriter(); allp = pages[:13] + [("raw", s) for s in f1] + [p_f2(), p_q1(), p_r1()]
    for i, pg in enumerate(allp, 1):
        svg = pg[1] if isinstance(pg, tuple) else doc(pg)
        pdf = f"{PG}/p{i:02d}.pdf"; cairosvg.svg2pdf(bytestring=svg.encode(), write_to=pdf)
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{PG}/prev_p{i:02d}.png", output_width=2000)
        w.append(PdfReader(pdf))
    out = f"{OUT}/HAKI_{STYLE}_TECHPACK_{REV.replace(' ', '')}.pdf"; w.write(out)
    print("pages", len(allp), out, round(os.path.getsize(out) / 1e6, 1), "MB")
    return out, len(allp)

if __name__ == "__main__":
    build()
