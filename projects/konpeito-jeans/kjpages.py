"""Konpeito jeans — every tech-pack page (A4 landscape SVG -> PDF), merged pack, per-element folders, zip.
All stitch numbers come from the DST read-back json (kjstitch -> readback.dst); measurements from the HI size chart."""
import os, json, pickle, glob, io, base64, shutil, zipfile, math, datetime
import numpy as np
import cairosvg
from PIL import Image
from pypdf import PdfWriter, PdfReader
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union
from shapely import affinity
import kjcore
from kjcore import KJ_PAL, NAME, STYLE, REV, DATE, SIZES, PROPOSED
import sheet
from sheet import t, dim_h, dim_v, INK, MUTED, RED, ORANGE, GREEN, GUIDE, SW, SH
from render import f, geom_to_path
import tech, factory, readback
import kjflat as FL
import kjart as KA

AMBER = "#B26A00"; AMBER_BG = "#FFF3DC"
FAC = "#1F5FA8"; FAC_BG = "#E8F0FA"     # factory-to-supply items (founder 19 Oct: Mandy fills them from her HI spec)
FACTORY_POM = ["Factory to use the measurements from your Hidden Inventory pants spec/pattern (same block, cargo pockets removed).",
               "Values not held by Haki; please fill in and return for approval with the fit sample."]
def facbox(x, y, w, h, lines, size=2.0, title="FACTORY TO SUPPLY"):
    o = [f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="1.2" fill="{FAC_BG}" stroke="{FAC}" stroke-width="0.5"/>']
    o.append(t(x + 3, y + 5, title, size, 700, FAC))
    for i, ln in enumerate(lines): o.append(t(x + 3, y + 5 + (i + 1) * size * 1.5, ln, size, 400, FAC))
    return "\n".join(o)
OUT = "out/pack"; os.makedirs(OUT, exist_ok=True)
A = pickle.load(open("out/art.pkl", "rb"))
GATES = json.load(open("out/gates.json"))
FRONT = json.load(open("out/front_stars.json"))
PROF = factory.load()

# ---------------------------------------------------------------- element register
EL = [  # key, no, title, piece, process, json stem
    ("coin", "01", "Coin-pocket patch — こんぺいとう", "front-right coin pocket (wearer's right)", "embroidered patch, heat-cut edge, sewn on + 2 rivets", "HAKI_KJ_01_coin-pocket-patch"),
    ("spill", "02", "Konpeito spilling out of the coin pocket", "front-right pocket facing, above the coin pocket", "direct embroidery on the cut facing", "HAKI_KJ_02_coin-spill-facing"),
    ("wb", "03", "Waistband patch — ちひろ note", "back waistband, wearer's right", "embroidered patch, heat-cut edge, sewn on", "HAKI_KJ_03_waistband-patch"),
    ("haki", "04", "Back pocket L — 'haki' + 2 konpeito stars", "wearer's LEFT back pocket", "direct embroidery on the cut pocket", "HAKI_KJ_04_back-pocket-L-haki"),
    ("starP", "05", "Back pocket R — pink konpeito star", "wearer's RIGHT back pocket", "direct embroidery on the cut pocket", "HAKI_KJ_05_back-pocket-R-star-pink"),
    ("starY", "06", "Back pocket L — lower yellow star", "wearer's LEFT back pocket, lower outer corner", "direct embroidery on the cut pocket", "HAKI_KJ_06_back-pocket-L-lower-star-yellow"),
    ("front1", "07a", "Front-leg konpeito stars, upper [PROPOSED]", "wearer's RIGHT front leg panel", "direct embroidery on the cut front panel", "HAKI_KJ_07a_front-leg-stars-upper_PROPOSED"),
    ("front2", "07b", "Front-leg konpeito stars, lower [PROPOSED]", "wearer's RIGHT front leg panel", "direct embroidery on the cut front panel", "HAKI_KJ_07b_front-leg-stars-lower_PROPOSED"),
]
RB = {k: json.load(open(f"out/stitch/{stem}.json")) for k, *_, stem in EL}

# ---------------------------------------------------------------- helpers
def page(o): return f'<svg xmlns="http://www.w3.org/2000/svg" width="{SW}mm" height="{SH}mm" viewBox="0 0 {SW} {SH}">' + "\n".join(o) + "</svg>"
def hdr(title, sub, pg): return sheet.header(title, sub, pg)
def missing(x, y, w, h, text, size=2.4):
    o = [f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="1.2" fill="{AMBER_BG}" stroke="{AMBER}" stroke-width="0.5" stroke-dasharray="1.6 0.8"/>']
    lines = text if isinstance(text, list) else [text]
    for i, ln in enumerate(lines):
        o.append(t(x + 3, y + 5 + i * (size * 1.5), ln, size, 700 if i == 0 else 400, AMBER))
    return "\n".join(o)
def prop(x, y, s, size=2.0): return t(x, y, s + "  " + PROPOSED, size, 600, AMBER)
def img(path_or_im, x, y, w=None, h=None, q=88):
    im = path_or_im if isinstance(path_or_im, Image.Image) else Image.open(path_or_im)
    im = im.convert("RGB")
    if w is None: w = h * im.width / im.height
    if h is None: h = w * im.height / im.width
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=q)
    return f'<image x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" href="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"/>', h
def table(x, y, cols, rows, size=2.0, lh=4.0, head=True, colours=None):
    """cols: [(title, width)]; rows: list of lists of str"""
    o = []; xx = x
    if head:
        for c, w in cols: o.append(t(xx, y, c, size, 700, MUTED)); xx += w
        o.append(f'<line x1="{f(x)}" y1="{f(y + 1.2)}" x2="{f(x + sum(w for _, w in cols))}" y2="{f(y + 1.2)}" stroke="#BBBBBB" stroke-width="0.2"/>')
        y += lh
    for ri, r in enumerate(rows):
        xx = x
        for ci, (c, w) in enumerate(cols):
            v = r[ci] if ci < len(r) else ""
            col = INK
            if colours and (ri, ci) in colours: col = colours[(ri, ci)]
            if isinstance(v, str) and ("MISSING" in v): col = AMBER
            if isinstance(v, str) and "proposed" in v.lower(): col = AMBER
            o.append(t(xx, y, v, size, 400, col)); xx += w
        y += lh
    return "\n".join(o), y
def vis_svg(vis, dx=0, dy=0, s=1.0, rot=0.0, origin=(0, 0)):
    o = []
    for r in vis:
        g = r["geom"]
        if rot: g = affinity.rotate(g, rot, origin=origin)
        g = affinity.translate(affinity.scale(g, s, s, origin=(0, 0)), dx, dy)
        o.append(f'<path d="{geom_to_path(g)}" fill="{KJ_PAL[r["col"]][0]}" fill-rule="evenodd"/>')
    return "\n".join(o)
def swatch(x, y, hexc, w=5, h=3): return f'<rect x="{f(x)}" y="{f(y - h + 0.6)}" width="{w}" height="{h}" rx="0.4" fill="{hexc}" stroke="#BDBDBD" stroke-width="0.15"/>'
def hrs(rb): return rb["machine_min"]

PAGES = []          # (id, title, svg, missing_note)
def add(pid, title, o, miss=""): PAGES.append((pid, title, page(o), miss))

# ---------------------------------------------------------------- flats with embroidery placed
SIL = FL.silhouettes()
MMPX = FL.MM
def emb_front():
    """embroidery on the front flat (mm, flat coords: x from the front view's left image edge 760 px)."""
    ox = 760
    o = []
    cx, cy = (FL.COIN_TL_PX[0] - ox) * MMPX, FL.COIN_TL_PX[1] * MMPX
    o.append(vis_svg(A["spill"]["vis"], cx, cy))
    o.append(vis_svg(A["coin"]["vis"], cx, cy))
    # front-leg stars (PROPOSED): leg edge at that height + x from side
    sil = affinity.scale(SIL["front"], MMPX, MMPX, origin=(0, 0))
    for d in FRONT["stars"]:
        y = d["y_from_waist_mm"] + FL.MM * FRONT["derivation"]["origin_px"][1]
        row = sil.intersection(box(0, y - 0.3, 3000, y + 0.3))
        ex = row.bounds[0] if not row.is_empty else 790 * MMPX
        x = ex + d["x_from_side_mm"]
        g, hi = KA.puffy_star(x - ox * MMPX, y, KA.STAR_D)
        base, tint = {"pink": ("kj_pink", "kj_pink_hi"), "blue": ("kj_blue", "kj_blue_hi"), "yellow": ("kj_yellow", "kj_yellow_hi")}[d["col"]]
        o.append(f'<path d="{geom_to_path(g)}" fill="{KJ_PAL[base][0]}"/><path d="{geom_to_path(hi)}" fill="{KJ_PAL[tint][0]}"/>')
    return "\n".join(o)

BACK_POCKETS = {"L": (160, 340, 183), "R": (423, 603, 183)}      # px: x0, x1, top
HAKI_POS = (18.0, 27.0)       # yellow-star centre: mm in from the pocket's OUTER edge, mm below the pocket top edge
STARP_POS = (17.0, 25.0)      # right pocket star centre: in from OUTER edge, below top
STARY_POS = (17.0, 20.0)      # lower yellow star: in from outer edge, ABOVE the lower corner (16 Oct spec)
def emb_back():
    o = [vis_svg(A["wb"]["vis"], FL.WB_TL_PX[0] * MMPX, FL.WB_TL_PX[1] * MMPX)]
    x0, x1, top = BACK_POCKETS["L"]           # wearer's left pocket: outer edge = image left
    o.append(vis_svg(A["haki"]["vis"], x0 * MMPX + HAKI_POS[0], top * MMPX + HAKI_POS[1]))
    o.append(vis_svg(A["starY"]["vis"], (x0 + 8) * MMPX + STARY_POS[0], 352 * MMPX - STARY_POS[1]))
    x0, x1, top = BACK_POCKETS["R"]           # wearer's right pocket: outer edge = image right
    o.append(vis_svg(A["starP"]["vis"], x1 * MMPX - STARP_POS[0], top * MMPX + STARP_POS[1]))
    return "\n".join(o)

FRONT_SVG, FB = FL.front_svg(SIL["front"]); BACK_SVG, BB = FL.back_svg(SIL["back"])
def flat_group(which, x, y, s, emb=True):
    body = (FRONT_SVG + (emb_front() if emb else "")) if which == "front" else (BACK_SVG + (emb_back() if emb else ""))
    return f'<g transform="translate({f(x)} {f(y)}) scale({f(s)})">{body}</g>'

# ---------------------------------------------------------------- T1 cover
def T1(index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>', t(14, 22, "HAKI STUDIOS", 3.0, 700, MUTED),
         t(14, 34, NAME, 7.0, 700),
         t(14, 41.5, f"{STYLE} · {REV} · {DATE} · 5-pocket jean, same fit + construction as the Hidden Inventory pants (no cargo pockets) · waist sizes {' '.join(SIZES)}", 2.5, 400, MUTED),
         f'<line x1="14" y1="45" x2="{SW-14}" y2="45" stroke="{INK}" stroke-width="0.4"/>']
    s = 0.118
    o.append(flat_group("back", 14 - BB[0] * s + 2, 52, s)); o.append(flat_group("front", 92 - FB[0] * s, 52, s))
    o.append(t(16, 52 + 1240 * MMPX * s + 5, "BACK", 2.2, 700)); o.append(t(96, 52 + 1240 * MMPX * s + 5, "FRONT", 2.2, 700))
    ix = 176; o.append(t(ix, 54, "CONTENTS", 2.8, 700)); y = 60
    for pid, title, miss in index:
        o.append(t(ix, y, f"{pid}", 1.95, 700)); o.append(t(ix + 9, y, title[:58], 1.95, 400))
        if miss: o.append(t(SW - 14, y, "MISSING: " + "; ".join(m_.split(" / ")[0] for m_ in miss.split("; "))[:60], 1.7, 700, AMBER, "end"))
        y += 3.55
    y += 3
    o.append(t(ix, y, "Legend", 2.2, 700)); y += 4
    o.append(t(ix, y, "[proposed — confirm]  = for the FACTORY to confirm or correct", 1.9, 600, AMBER)); y += 3.6
    o.append(t(ix, y, "[MISSING]  = Haki still owes it (artwork / file / info to follow from Haki)", 1.9, 600, AMBER)); y += 3.6
    o.append(t(ix, y, "FACTORY TO SUPPLY (blue) = the factory fills it from its HI spec / pattern", 1.9, 500, FAC)); y += 3.6
    o.append(t(ix, y, "All dimensions mm unless marked in; stitch numbers read back from the DST files.", 1.9, 400, MUTED))
    o.append(t(SW - 14, SH - 6, sheet.FOOT, 1.9, 400, MUTED, "end"))
    return o

# ---------------------------------------------------------------- T2 flats
def star_flat_mm(sid):
    """flat (front view) mm position of a front-leg star, same maths as emb_front()."""
    d = next(q for q in FRONT["stars"] if q["id"] == sid)
    sil = affinity.scale(SIL["front"], MMPX, MMPX, origin=(0, 0))
    y = d["y_from_waist_mm"] + MMPX * FRONT["derivation"]["origin_px"][1]
    row = sil.intersection(box(0, y - 0.3, 3000, y + 0.3))
    return row.bounds[0] + d["x_from_side_mm"] - 760 * MMPX, y

def T2():
    global S07
    S07 = star_flat_mm("S06")
    o = hdr("T2 · FLATS — front + back (drawn to the mockup)", "Silhouette traced from the client flat lay; construction lines placed from it; embroidery drawn at true size on the flat (scale bar). Washed black denim, DTM black topstitch, matte black hardware.", "T2")
    s = 0.128
    o.append(flat_group("front", 16 - FB[0] * s, 32, s)); o.append(flat_group("back", 110 - BB[0] * s, 32, s))
    o.append(t(20, 32 + 1240 * MMPX * s + 4, "FRONT", 2.6, 700)); o.append(t(114, 32 + 1240 * MMPX * s + 4, "BACK", 2.6, 700))
    # callouts
    calls_f = [((FL.COIN_TL_PX[0] - 760) * MMPX + 38, FL.COIN_TL_PX[1] * MMPX + 28, "01"), ((FL.COIN_TL_PX[0] - 760) * MMPX + 38, FL.COIN_TL_PX[1] * MMPX - 8, "02"),
               (S07[0], S07[1], "07"), ((1112 - 760) * MMPX, 72 * MMPX, "B1"), ((1092 - 760) * MMPX, 150 * MMPX, "Z1")]
    calls_b = [(FL.WB_TL_PX[0] * MMPX + 40, FL.WB_TL_PX[1] * MMPX + 27, "03"), (160 * MMPX + 50, 183 * MMPX + 27, "04"),
               (603 * MMPX - 17, 183 * MMPX + 25, "05"), (168 * MMPX + 17, 352 * MMPX - 20, "06"), (380 * MMPX, 60, "L1")]
    for (x, y, lab), (gx, gy) in [(c, (16 - FB[0] * s, 32)) for c in calls_f] + [(c, (110 - BB[0] * s, 32)) for c in calls_b]:
        X, Y = gx + x * s, gy + y * s
        o.append(f'<line x1="{f(X)}" y1="{f(Y)}" x2="{f(X + 9)}" y2="{f(Y - 6)}" stroke="{GUIDE}" stroke-width="0.25"/>')
        o.append(f'<circle cx="{f(X + 11)}" cy="{f(Y - 7)}" r="2.6" fill="#FFFFFF" stroke="{GUIDE}" stroke-width="0.3"/>')
        o.append(t(X + 11, Y - 6.2, lab, 2.0, 700, GUIDE, "middle"))
    lx = 212; y = 36
    o.append(t(lx, y, "Callouts", 2.6, 700)); y += 5
    for lab, s_ in [("01", "coin-pocket patch こんぺいとう"), ("02", "konpeito spill on the facing"), ("03", "waistband patch (ちひろ note)"),
                    ("04", "back pocket L: 'haki' + 2 stars"), ("05", "back pocket R: pink star"), ("06", "back pocket L lower yellow star"),
                    ("07", "front-leg stars: artwork to follow [MISSING]"), ("B1", "28 L flat tack shank button"), ("Z1", "YKK #4.5 zip fly, 6 in"), ("L1", "main label inside CB (T7)")]:
        o.append(t(lx, y, lab, 2.0, 700, GUIDE)); o.append(t(lx + 7, y, s_, 1.9, 400, AMBER if ("MISSING" in s_ or "proposed" in s_) else INK)); y += 3.8
    y += 3
    for s_ in ["5-pocket jean, same fit + construction as the", "Hidden Inventory (HI) pants, without the cargo", "pockets:",
               "• 2 front scoop pockets + coin pocket (= patch 01)", "• NO back yoke (as HI): back panel runs up to", "  the waistband",
               "• 2 back patch pockets, HI pointed shape,", "  bartacked top corners",
               "• regular waistband, 2 pieces joined at CB", "• 5 belt loops, zip fly, 15 L rivets (T5)",
               "• front + back legs: ONE panel each, waist", "  to hem (no knee seam)"]:
        o.append(t(lx, y, s_, 1.9, 400, INK)); y += 3.4
    y += 2; o.append(t(lx, y, "Matte black metal, DTM black thread (19 Oct)", 1.8, 600, INK)); y += 3.4
    o.append(missing(lx, y + 2, 70, 10, ["07 front-leg: artwork to follow [MISSING]", "PROPOSED star positions on G7"], 1.8))
    # scale bar
    o.append(f'<line x1="24" y1="{SH-14}" x2="{24 + 100 * s}" y2="{SH-14}" stroke="{INK}" stroke-width="0.5"/>')
    o.append(t(24, SH - 15.5, "100 mm at flat scale", 1.8, 400, MUTED))
    return o

# ---------------------------------------------------------------- T3 POM
HI = {  # Hidden Inventory published chart, inches (PLM pipeline.size_charts 9a469aee-…, updated 2026-08-12)
    "26": (27.1, 37, 10.6, 27, 19.7), "28": (29.1, 39, 11, 28, 20.1), "30": (31.1, 41, 11.4, 29, 20.5), "32": (33.1, 43, 11.8, 30, 20.9),
    "34": (35, 44.9, 12.2, 30, 21.3), "36": (37, 46.9, 12.6, 31, 21.7), "38": (39, 48.8, 13, 31, 22), "40": (41, 50.8, 13.4, 31, 22.4)}
# Rev B size run (founder 20 Oct) adds 29 / 31 / 33: not on the HI chart -> half-way between the neighbouring sizes, PROPOSED
HI_MID = {m: tuple(round((HI[a][i] + HI[b][i]) / 2, 2) for i in range(5)) for m, a, b in (("29", "28", "30"), ("31", "30", "32"), ("33", "32", "34"))}
POM = [("A", "Relaxed waist", "circumference at the top edge of the waistband", 0, "±0.5"),
       ("B", "Hip", "circumference 9 in down from the top of the waistband", 1, "±0.5"),
       ("C", "Front rise", "bottom of the waistband to the crotch seam", 2, "±0.25"),
       ("D", "Inseam", "crotch seam to hem", 3, "±0.5"),
       ("E", "Leg opening", "circumference of the hem", 4, "±0.25"),
       ("F", "Back rise", "bottom of the waistband to the crotch seam, back", None, "—"),
       ("G", "Thigh", "circumference 1 in below the crotch", None, "—"),
       ("H", "Knee", "circumference at knee height", None, "—"),
       ("I", "Outseam", "top of the waistband to the hem, side", None, "—")]
def T3():
    o = hdr("T3 · POM / SIZE CHART — finished garment, inches (cm)", "Source: Hidden Inventory pants size chart (PLM pipeline.size_charts 9a469aee-d93c-4ec1-9aca-8614b5980b52, published on Shopify, updated 2026-08-12) — the published customer measurements of the shipped HI pants.", "T3")
    x0, y = 12, 36
    SC = 16.4
    cols = [("", 7), ("POM", 26), ("How to measure", 48)] + [(s, SC) for s in SIZES] + [("Tol. in", 13)]
    xx = x0
    for c, w in cols: o.append(t(xx, y, c, 2.1, 700, MUTED)); xx += w
    y += 2; o.append(f'<line x1="{x0}" y1="{y}" x2="{SW-12}" y2="{y}" stroke="{INK}" stroke-width="0.3"/>'); y += 5
    for code, name, how, idx, tol in POM:
        xx = x0
        o.append(t(xx, y, code, 2.2, 700)); xx += 7
        o.append(t(xx, y, name, 2.2, 700)); xx += 26
        for k_, ln in enumerate(wrap(how, 30)[:2]): o.append(t(xx, y - 0.6 + k_ * 2.6, ln, 1.6, 400, MUTED))
        xx += 48
        for s in SIZES:
            if idx is None:
                o.append(f'<rect x="{f(xx - 0.5)}" y="{f(y - 3.4)}" width="{SC - 1.2}" height="6.6" fill="{FAC_BG}" stroke="{FAC}" stroke-width="0.25"/>')
                o.append(t(xx + SC / 2 - 1, y - 0.6, "factory", 1.5, 700, FAC, "middle")); o.append(t(xx + SC / 2 - 1, y + 2.0, "HI spec", 1.5, 700, FAC, "middle"))
            else:
                mid = s in HI_MID
                v = (HI_MID if mid else HI)[s][idx]
                o.append(t(xx + SC / 2 - 1, y - 0.4, f"{v:g}", 2.2, 600, AMBER if mid else INK, "middle"))
                o.append(t(xx + SC / 2 - 1, y + 2.6, f"({v * 2.54:.1f})", 1.5, 400, AMBER if mid else MUTED, "middle"))
            xx += SC
        o.append(t(xx + 1, y, tol if idx is not None else "—", 1.9, 400, AMBER if idx is not None else MUTED))
        y += 9
        o.append(f'<line x1="{x0}" y1="{f(y - 5.5)}" x2="{SW-12}" y2="{f(y - 5.5)}" stroke="#DDDDDD" stroke-width="0.2"/>')
    y += 1
    o.append(t(12, y + 1, "Amber sizes 29 / 31 / 33: not on the HI chart; half-way between the neighbouring sizes  " + PROPOSED, 1.8, 600, AMBER)); y += 4
    o.append(facbox(12, y, 140, 19, ["Blue cells (back rise, thigh, knee, outseam for every size; any other gap in the HI chart):"] + FACTORY_POM
                                      + ["The HI factory tech pack (CAMOPANTS1) has no measurement chart: HI was fitted to a reference garment."], 1.75, "FACTORY TO SUPPLY — measurements"))
    # grading
    gx = 160; o.append(t(gx, y + 4, "Grading (from the chart, per size step = 2 in waist)", 2.3, 700)); gy = y + 9
    for code, name, how, idx, tol in POM[:5]:
        steps = sorted({round(HI[b][idx] - HI[a][idx], 2) for a, b in zip(list(HI)[:-1], list(HI)[1:])})
        o.append(t(gx, gy, f"{code} {name}: +{' / +'.join(f'{s:g}' for s in steps)} in per 2 in waist step", 1.9)); gy += 3.6
    o.append(t(12, SH - 14, "Tolerances: house standard for denim  " + PROPOSED + ".  Fabric as HI (RHT 3x1 denim 12 oz, 100 % cotton); washed black (T6). Shrinkage after the wash", 1.8, 500, AMBER))
    o.append(t(12, SH - 10.5, f"is built into the pattern by the factory as for HI (wash test on the bulk denim before cutting).  Size labels: waist {' '.join(SIZES)} (T7b).", 1.8, 500, INK))
    return o

# ---------------------------------------------------------------- T4 pattern
def T4():
    o = hdr("T4 · PATTERN — use the factory's Hidden Inventory pants pattern", "No pants block in our engine: we do not draft a pattern. The factory already has the Hidden Inventory (Haki cargo pant) pattern: same fit, same construction, cargo pockets left off.", "T4")
    y = 38
    for s_, b in [("Base pattern", "The factory's Hidden Inventory pants pattern, all sizes as graded for HI (T3). Same fit: waist, hip, rise, thigh, knee, leg opening, lengths."),
                  ("Leave off", "Cargo pockets (bags, box pleats, flaps, snaps), the HI flag labels, the hammer loop (not on the Konpeito mockup)  " + PROPOSED),
                  ("Front + back legs", "ONE panel each from the waist to the hem: NO knee seam (the HI panel seams are joined into one piece; plain leg as the mockup)."),
                  ("Back", "NO back yoke (as HI): the back panel runs straight up to the waistband; the two back panels are joined by the centre-back (seat) seam."),
                  ("Waistband", "Regular waistband, 2 pieces joined at centre back (CB), shank button at the centre front (CF)."),
                  ("Pockets (5-pocket)", "2 front scoop pockets (pocket bag + facing) with the coin pocket on the wearer's right facing (= patch 01, as HI: scoop + coin pocket + rivets);"),
                  ("", "2 back patch pockets, HI pointed shape, centred on each back leg (as HI)."),
                  ("Fly, loops", "Zip fly (fly + fly shield, YKK #4.5 6 in) as HI; 5 belt loops as HI (2 front 1 cm from the pocket, 2 back, 1 at CB)."),
                  ("Shrinkage", "Wash the bulk denim (T6 wash), measure shrinkage, add it to the pattern before the first sample (as HI).")]:
        o.append(t(14, y, s_, 2.3, 700)); o.append(t(56, y, b, 2.05, 400, AMBER if "proposed" in b.lower() else INK)); y += 5.9
    y += 3
    o.append(t(14, y, "Pattern pieces per garment — check against the HI pattern  " + PROPOSED, 2.5, 700, INK)); y += 6
    rows = [["Front leg L / R", "2", "shell", "one piece waist to hem (no knee seam); R carries 07 (front-leg stars)"],
            ["Back leg L / R", "2", "shell", "one piece waist to hem (no knee seam, no yoke)"],
            ["Waistband", "2", "shell + interlining as HI", "2 pieces joined at CB; patch 03 on the wearer's right back"],
            ["Fly / fly shield", "2", "shell", "YKK #4.5 zip 6 in + 28 L shank button"],
            ["Front pocket facing L / R", "2", "shell", "R carries 02 (konpeito spill) + coin pocket 01"],
            ["Front pocket bag", "2", "pocketing (T5)", ""],
            ["Coin pocket", "1", "= embroidered patch 01", "76 × 56, sewn on, rivets at the 2 top corners"],
            ["Back patch pocket L / R", "2", "shell", "L carries 04 (+06), R carries 05"],
            ["Belt loop", "5", "shell", "2 front, 2 back, 1 CB (as HI)"]]
    tb, y = table(14, y, [("Piece", 50), ("Qty", 12), ("Material", 44), ("Embroidery / note", 120)], rows, 2.1, 4.6)
    o.append(tb)
    o.append(facbox(14, y + 4, 200, 19, FACTORY_POM + ["Please also send the HI pattern (DXF/PDF) so we can convert the embroidery placements to cut-piece coordinates."], 2.0,
                    "FACTORY TO SUPPLY — pattern + measurements (back rise, thigh, knee, outseam)"))
    return o

# ---------------------------------------------------------------- T5 BOM
WASH_TARGET = ("Washed black, matched to the MOCKUP (T2 flats source image): a faded charcoal black, not jet black — mean ~#2B2A2A on the "
               "front, deepest shade ~#202020 in the creases and waistband, highs ~#444343-#555353 (read from the mockup pixels). Lighter: "
               "front upper thighs below the pockets, front knees and the hem; back seat below the pockets and the back of the knees; seams, "
               "pocket edges and hems slightly worn lighter. Darker: waistband, fly area, creases at the hip and behind the knee.")
def T5():
    o = hdr("T5 · BILL OF MATERIALS", "Per garment. Fabric, threads, hardware + label types = the Hidden Inventory pants BOM (factory tech pack CAMOPANTS1 p. 8–9). Amber [proposed — confirm] = factory to confirm or correct; [MISSING] = Haki still owes it.", "T5")
    sz = " ".join(SIZES)
    rows = [
        ["Shell", "RHT 3x1 denim, 12 oz, 100 % cotton (as HI); wash: enzyme + stone wash to the mockup's washed black (T6)", "washed black (T6)", "—", "legs, waistband, pockets, loops"],
        ["Pocket bag", "40's twill, 160 GSM, 100 % cotton (as HI)", "DTM black", "—", "front pocket bags"],
        ["Interlining", "Waistband interlining as the HI production waistband (the HI BOM lists none)  [proposed — confirm]", "black", "—", "waistband"],
        ["Thread — topstitch", "All-purpose polyester Tex 135 / TKT 20 (as HI)", "DTM black", "—", "all visible topstitch"],
        ["Thread — overlock", "All-purpose polyester Tex 60 / TKT 50 (as HI)", "DTM black", "—", "overlock, construction seams"],
        ["Thread — buttonhole", "All-purpose polyester Tex 60 / TKT 50 (as HI)", "DTM black", "—", "waistband buttonhole"],
        ["Thread — patch attach", "Polyester Tex 60 / TKT 50, 1 mm edge stitch  [proposed — confirm]", "red #C8162B", "—", "patches 01 + 03"],
        ["Embroidery threads", "40wt polyester (black 60wt), 11 colours, thread chart on G1; method per element (patch vs straight onto the panel) on G1", "see G1", "—", "embroidery 01–07"],
        ["Shank button", "Flat tack button with shank, 28 Line, brass / zinc alloy (as HI)", "matte black", "1", "waistband CF closure (B1)"],
        ["Zip", "YKK #4.5 metal, close-end, automatic lock slider, 6 in (as HI)", "matte black + DTM tape", "1", "CF fly (Z1)"],
        ["Rivets", "Inverted nipple rivet 15 L (9.5 mm), metal (as HI)", "matte black", "4", "2 front scoop corners + 2 coin-pocket top corners"],
        ["Bartacks", "Back-pocket top corners (as HI, no rivets), belt loops, fly bottom", "DTM black", "—", ""],
        ["Main label", "Damask woven, flat, 5 × 2.5 cm, sewn down on all 4 sides. Current HI artwork = reference; new artwork: to follow [MISSING]", "jet black / optic white", "1", "inside CB, centred on the waistband"],
        ["Size label", f"Damask woven LOOP label (folded, open loop), waist number in Neue Metana; sizes {sz} (artwork T7b, zip labels/)", "jet black / optic white", "1", "inside CB, left of the main label"],
        ["Care label", "Printed polyester satin ribbon, 3 × 6 cm. Current HI artwork = reference; new artwork: to follow [MISSING]", "optic white / jet black", "1", "wearer's right, waist seam, 5 cm in from side seam"],
        ["Hangtag + string", "Hangtag artwork: to follow [MISSING]; label string through the size-label loop; retail sticker on the hangtag (as HI)", "", "1", "hung from the SIZE label"],
        ["Barcode", "Barcode per size: HK code from PLM: to follow [MISSING] (Code 128, printed on the polybag sticker)", "print black", "1", "polybag sticker"],
        ["Packing", "Packing design: to follow from Haki [MISSING]. Until then as HI: transparent polybag 43 × 31 cm + polybag sticker bottom left", "", "1", ""]]
    tb, y = table(12, 35, [("Item", 33), ("Description", 150), ("Colour", 36), ("Pcs", 8), ("Where", 50)], rows, 1.8, 6.3)
    o.append(tb)
    o.append(t(12, y + 1.5, "Note: all items to be OEKO-TEX certified (as HI).", 2.2, 700))
    return o

# ---------------------------------------------------------------- T6 construction + wash
def T6():
    o = hdr("T6 · CONSTRUCTION, STITCHING + WASH", "Sew it the way the factory sews the Hidden Inventory pants (same fit, same construction, same threads + hardware, T5), without the cargo pockets. Plain words; amber = factory to confirm or correct.", "T6")
    rows = [["Threads", "Black thread that matches the denim (DTM) everywhere: topstitch Tex 135 / TKT 20; overlock + buttonhole Tex 60 / TKT 50 (as HI)."],
            ["Legs", "Front and back legs are ONE piece each from waist to hem. No knee seam."],
            ["Back", "NO back yoke (as HI). The two back panels are joined by the centre-back (seat) seam: 2 rows of topstitch, as HI."],
            ["Side + inside leg", "Outseam and inseam sewn and finished as on the HI pants (same seam type + topstitch)."],
            ["Waistband", "Regular waistband, 2 pieces joined at centre back; 2 rows of topstitch; buttonhole + 28 L shank button at the front; interlining as HI."],
            ["Front pockets", "Scoop pockets as HI: turned edge with topstitch; 15 L rivet at each pocket's top corner."],
            ["Coin pocket = patch 01", "Embroidered patch sewn onto the right pocket facing (1 mm red edge stitch on the sides + bottom; top edge left open = pocket"],
            ["", "opening); 15 L rivets through its 2 top corners. Sewn on after the wash."],
            ["Back pockets", "2 back patch pockets (HI pointed shape, centred on each back leg)."],
            ["", "Top edge hemmed with topstitch; sides + point sewn on with 2 rows of topstitch; bartack at both top corners (as HI, no rivets)."],
            ["Fly", "Zip fly, YKK #4.5 close-end 6 in, automatic lock slider; J-shaped topstitch on the front, bartack at the bottom (as HI)."],
            ["Belt loops", "5 loops (2 front 1 cm from the pocket, 2 back, 1 at CB), bartacked top + bottom (as HI)."],
            ["Hem", "Turned twice and topstitched, as the HI pants."],
            ["Labels", "Main label inside CB sewn down on all 4 sides; size LOOP label on its left; care label in the waist seam, wearer's right (T7)."],
            ["Not on Konpeito", "Cargo pockets, snap buttons, HI flag labels, hammer loop  " + PROPOSED]]
    tb, y = table(12, 36, [("Operation", 34), ("How (plain words)", 150)], rows, 1.85, 5.0)
    o.append(tb)
    wx = 200; wy = 36
    o.append(t(wx, wy, "Wash — washed black, match the MOCKUP", 2.6, 700)); wy += 5
    for ln in wrap(WASH_TARGET, 50):
        o.append(t(wx, wy, ln, 1.85, 400, INK)); wy += 3.4
    wy += 1.5
    for s_ in ["Process: enzyme wash + stone wash on the RHT 3x1", "12 oz black denim, then soften + tumble dry.",
               "The factory matches the mockup look and sends a", "washed panel / first sample for Haki's approval.",
               "", "Embroidery + wash",
               "• Embroidery sewn onto the panel (02, 04–07) goes", "  through the wash: polyester thread (colour-fast); wash-", "  test the strike-off (stones can grey yellow + pink).",
               "• Patches 01 + 03: sewn on AFTER the wash", "  (confirmed 19 Oct), coin-pocket rivets too.",
               "• Shrinkage: measure on washed bulk denim, add to", "  the pattern; embroidery positions are finished-size."]:
        o.append(t(wx, wy, s_, 1.9, 700 if s_ == "Embroidery + wash" else 400, INK)); wy += 3.8
    im = Image.open(FL.SRC).convert("RGB")
    tag, hh = img(im.crop((0, 0, 760, im.height)), wx, wy + 2, h=min(62, SH - wy - 18)); o.append(tag)
    o.append(t(wx, wy + 2 + hh + 3.5, "Wash target = the mockup (back view shown; front view on G7 / C5).", 1.8, 600, MUTED))
    return o

# ---------------------------------------------------------------- T7 labels / trims
def label_detail(X, Y, s=0.4, size="32"):
    """inside back waistband at CB (drawn 1:1 in local mm, placed at scale s): main label sewn down on all 4 sides, size
    LOOP label on its left with the hang-tag string through the loop, hang tag below (schematic)."""
    import kjlabels as KL
    ts = lambda v: v / s                  # text size v mm on the page
    o = []
    wb_h = 40.0; x = 0; y = 0
    o.append(f'<rect x="0" y="0" width="110" height="{wb_h}" fill="{FL.DENIM_LT}" stroke="{INK}" stroke-width="0.6"/>')
    o.append(f'<line x1="55" y1="-3" x2="55" y2="{wb_h + 6}" stroke="{INK}" stroke-width="0.5" stroke-dasharray="2 1.2"/>')
    o.append(t(55, -4.5, "CB", ts(1.9), 700, INK, "middle"))
    o.append(t(113, wb_h / 2, "inside back waistband", ts(1.7), 500, MUTED)); o.append(t(113, wb_h / 2 + ts(1.7) * 1.4, "(seen from inside)", ts(1.7), 500, MUTED))
    o.append(t(113, wb_h + 2, "waist seam", ts(1.7), 500, MUTED))
    o.append(f'<line x1="0" y1="{wb_h}" x2="110" y2="{wb_h}" stroke="{INK}" stroke-width="0.9"/>')
    mx, my = 30, 7.5
    o.append(f'<rect x="{mx}" y="{my}" width="50" height="25" fill="#0A0A0A"/>')
    o.append(f'<rect x="{mx + 1.2}" y="{my + 1.2}" width="47.6" height="22.6" fill="none" stroke="#B0B0B0" stroke-width="0.5" stroke-dasharray="1.4 1"/>')
    o.append(t(mx + 25, my + 11, "main label", ts(1.7), 700, "#FFFFFF", "middle")); o.append(t(mx + 25, my + 11 + ts(1.7) * 1.3, "(reference art)", ts(1.5), 500, "#FFFFFF", "middle"))
    lw = KL.W; loop = (KL.L - 2 * KL.SA) / 2
    lx = mx - 6 - lw; ly = wb_h
    o.append(f'<rect x="{lx}" y="{ly - KL.SA}" width="{lw}" height="{loop + KL.SA}" rx="2" fill="#0A0A0A" stroke="#555" stroke-width="0.4"/>')
    d, _ = KL.text_path(size, lx + lw / 2, ly + loop / 2, KL.CAP)
    o.append(f'<path d="{d}" fill="#FFFFFF"/>')
    sx, sy = lx + lw / 2, ly + loop - 3
    o.append(f'<path d="M{sx - 5} {sy} Q {sx} {sy + 4} {sx + 5} {sy} M{sx} {sy + 2} L {sx - 4} {sy + 22}" fill="none" stroke="{AMBER}" stroke-width="0.8"/>')
    tx, ty = sx - 16, sy + 22
    o.append(f'<path d="M{tx + 5} {ty} L{tx + 24} {ty} L{tx + 24} {ty + 34} L{tx} {ty + 34} L{tx} {ty + 5} Z" fill="#FFF3DC" stroke="{AMBER}" stroke-width="0.6" stroke-dasharray="2 1.2"/>')
    o.append(f'<circle cx="{tx + 12}" cy="{ty + 4}" r="1.4" fill="none" stroke="{AMBER}" stroke-width="0.5"/>')
    o.append(t(tx + 12, ty + 14, "hang tag", ts(1.6), 700, AMBER, "middle")); o.append(t(tx + 12, ty + 14 + ts(1.6) * 1.3, "to follow", ts(1.5), 500, AMBER, "middle"))
    o.append(t(tx + 12, ty + 14 + ts(1.6) * 2.6, "[MISSING]", ts(1.5), 700, AMBER, "middle"))
    o.append(t(lx + lw + 4, ly + loop - 4, "size LOOP label: both ends sewn into the waist seam,", ts(1.6), 600, INK))
    o.append(t(lx + lw + 4, ly + loop - 4 + ts(1.6) * 1.35, "loop open — the hang-tag string ties through it", ts(1.6), 600, INK))
    o.append(t(60, -4.5, "main label: sewn down on all 4 sides", ts(1.6), 600, INK, "start"))
    return f'<g transform="translate({f(X)} {f(Y)}) scale({f(s)})">' + "\n".join(o) + "</g>"

def T7():
    o = hdr("T7 · LABELS + TRIMS PLACEMENT", "Inside / outside positions of every label and metal trim. Label types + positions as Hidden Inventory (factory tech pack p. 9, 10, 13); size label = LOOP label (founder 20 Oct); artwork on T7b.", "T7")
    s = 0.085
    o.append(flat_group("back", 14 - BB[0] * s, 32, s, emb=True))
    o.append(flat_group("front", 84 - FB[0] * s, 32, s, emb=True))
    bx = 14 - BB[0] * s; fx = 84 - FB[0] * s
    # main label 50 x 25 centred on CB + size loop on its left (inside, dashed)
    o.append(f'<rect x="{f(bx + (380 * MMPX - 25) * s)}" y="{f(32 + 52 * s)}" width="{f(50 * s)}" height="{f(25 * s)}" fill="none" stroke="{GUIDE}" stroke-width="0.35" stroke-dasharray="1 0.6"/>')
    o.append(f'<rect x="{f(bx + (380 * MMPX - 25 - 21) * s)}" y="{f(32 + 85 * s)}" width="{f(15 * s)}" height="{f(25 * s)}" fill="none" stroke="{GUIDE}" stroke-width="0.35" stroke-dasharray="0.6 0.4"/>')
    o.append(t(bx + 380 * MMPX * s, 32 + 52 * s - 2, "main + size loop label (inside, CB)", 1.7, 600, GUIDE, "middle"))
    # care label 30 x 60 hanging from the waist seam, 50 mm in from the wearer's right side seam (front flat: image left)
    cx0 = fx + ((886 - 760) * MMPX + 50 - 15) * s
    o.append(f'<rect x="{f(cx0)}" y="{f(32 + 95 * MMPX * s)}" width="{f(30 * s)}" height="{f(60 * s)}" fill="none" stroke="{GUIDE}" stroke-width="0.35" stroke-dasharray="1 0.6"/>')
    ly = 32 + 95 * MMPX * s + 4
    o.append(f'<line x1="{f(fx + 13)}" y1="{f(ly + 9)}" x2="{f(cx0)}" y2="{f(ly)}" stroke="{GUIDE}" stroke-width="0.25"/>')
    o.append(t(fx + 12.5, ly + 9.6, "care label (inside)", 1.7, 600, GUIDE, "end"))
    o.append(t(14, 140, "LABEL DETAIL — inside back waistband at CB (0.4 : 1)", 2.1, 700))
    o.append(label_detail(40, 148, 0.4))
    rows = [["Main label", "damask woven, flat", "inside back waistband, centred on CB, 5 × 2.5 cm; SEWN DOWN ON ALL 4 SIDES (jet black). Nothing hangs from it.", "current HI art = reference; new artwork: to follow [MISSING]"],
            ["Size label", "damask woven LOOP", f"inside CB, left of the main label: strip folded into an open loop, both ends in the waist seam; waist numbers {' '.join(SIZES)}", "artwork T7b + zip labels/ (Neue Metana, white on black)"],
            ["Care label", "printed satin", "wearer's right side, in the waist seam, 5 cm in from the side seam; 3 × 6 cm", "current HI art = reference; new artwork: to follow [MISSING]"],
            ["Hang tag", "", "hangs from the SIZE loop label (string through the loop), never from the main label", "hang tag artwork: to follow [MISSING]"],
            ["Shank button", "28 Line flat tack", "CF waistband, centred on the WB height", "matte black"],
            ["Zip fly", "YKK #4.5, 6 in", "CF fly, close-end, automatic lock slider", "matte black, DTM tape"],
            ["Rivets", "15 L (9.5 mm)", "front scoop corners (2); coin pocket top corners (2, through patch 01, centre 4.25 / 4.25 from the patch edges)", "matte black; back pockets: bartacks, no rivets"],
            ["Patch 03", "embroidered", "back WB, wearer's right: outer edge 25 mm from the side belt loop; top edge 3 mm below WB top; runs over the waist seam onto the back panel", "position confirmed (founder 20 Oct)"],
            ["Patch 01", "embroidered", "coin pocket position of the HI front-right facing (T8); Ø9.5 rivet caps cover only edge, band + plain cream field corner", ""]]
    yy = 36
    for r in rows:
        o.append(t(196, yy, r[0], 2.0, 700)); o.append(t(222, yy, r[1], 1.85, 400, MUTED))
        for k, ln in enumerate(wrap(r[2], 56)[:3]): o.append(t(196, yy + 3.4 + k * 3.0, ln, 1.75, 400, INK))
        nl = min(3, len(wrap(r[2], 56)))
        if r[3]: o.append(t(196, yy + 3.4 + nl * 3.0, r[3], 1.75, 600, AMBER if ("proposed" in r[3] or "MISSING" in r[3]) else GREEN)); nl += 1
        yy += 4.5 + nl * 3.0 + 1.6
    o.append(t(196, yy + 1, "No HI flag labels and no cargo pockets on Konpeito (different product).", 1.75, 600, MUTED))
    return o

def T7b():
    import kjlabels as KL
    o = hdr("T7b · LABEL ARTWORK — size labels (new) + main / care label reference", "Size labels: recreated by Haki (files in the zip, labels/). Main + care label: the current Hidden Inventory artwork is shown as REFERENCE only — new artwork to follow from Haki.", "T7b")
    # A: size labels at 1:1
    o.append(t(12, 32, f"A · SIZE LOOP LABELS — 1 : 1, flat strip {KL.W:g} × {KL.L:g} mm, fold at the middle (files: labels/HAKI_KJ_size-label_<size>.svg / .pdf)", 2.2, 700))
    x = 14; y = 38
    for sz in KL.SIZE_RUN:
        st, _ = KL.strip(sz, x, y, guides=True); o += st
        o.append(t(x + KL.W / 2, y + KL.L + 4, sz, 2.0, 700, INK, "middle"))
        x += KL.W + 4
    lx = x + 2
    for i, (ln, col) in enumerate([("Waist-size numbers, Neue Metana ExtraBold, optic white on jet black;", INK),
                                   ("text outlined in the files (no font needed).", INK),
                                   ("Damask woven (as HI); LOOP label: folded at the blue", INK),
                                   ("line, both ends (red seam lines, 5 mm) sewn into the", INK),
                                   ("waist seam inside CB, left of the main label; the loop", INK),
                                   ("stays open so the hang-tag string ties through it.", INK),
                                   ("Number on both halves (back half turned 180°), so both", INK),
                                   ("faces read upright when the loop hangs.", INK),
                                   ("Strip size + number height  " + PROPOSED, AMBER),
                                   (f"Sizes: {' '.join(KL.SIZE_RUN)} (founder 20 Oct)", INK)]):
        o.append(t(lx, 40 + i * 3.5, ln, 1.8, 400 if col == INK else 600, col))
    # B: HI reference art
    yb = 112
    im = Image.open("inputs/reference/HI_p10-10.png"); im = im.crop((int(im.width * 0.03), int(im.height * 0.205), int(im.width * 0.97), int(im.height * 0.965)))
    tag, h1 = img(im, 12, yb + 2, h=SH - yb - 22); o.append(t(12, yb, "B · MAIN + CARE LABEL — current HI artwork, REFERENCE ONLY (HI p. 10)", 2.2, 700)); o.append(tag)
    w1 = h1 * im.width / im.height
    o.append(missing(12 + w1 + 6, yb + 2, 120, 16, ["Main label + care label: new artwork to follow [MISSING]", "Haki sends new artwork; until then this HI art is a reference for", "type, size, colours and layout only. HI size label (XS–3XL) NOT used."], 1.9))
    yy = yb + 24; cx = 12 + w1 + 6
    for a, b in [("Main label", "damask woven, flat, 5 × 2.5 cm; jet black ground, optic white logo;"),
                 ("", "inside CB, centred on the waistband, SEWN DOWN ON ALL 4 SIDES (jet black)."),
                 ("Care label", "printed polyester satin ribbon, 3 × 6 cm, 0.5 cm stitching allowance at the top;"),
                 ("", "optic white ground, jet black text; wearer's right, waist seam, 5 cm in from the side seam."),
                 ("Care text (HI)", "SHELL: 100% COTTON · POCKETS: 100% COTTON · MADE IN [factory: country] ·"),
                 ("", "MACHINE WASH COLD INSIDE OUT AND SEPARATE · DO NOT BLEACH · TUMBLE DRY LOW"),
                 ("", "HEAT INSIDE OUT OR LINE DRY · IRON MEDIUM HEAT INSIDE OUT · DRY CLEAN · THIS"),
                 ("", "GARMENT MAY FADE AND STAIN OTHER LIGHT SURFACES AND GARMENTS (until new art)"),
                 ("Hang tag", "hangs from the SIZE loop label; artwork to follow [MISSING]"),
                 ("Certification", "all items to be OEKO-TEX certified (as HI).")]:
        o.append(t(cx, yy, a, 1.9, 700)); o.append(t(cx + 25, yy, b, 1.75, 600 if "MISSING" in b else 400, AMBER if "MISSING" in b else INK)); yy += 3.9
    return o

# ---------------------------------------------------------------- T8 embroidery placement overview
def T8():
    o = hdr("T8 · EMBROIDERY PLACEMENT — every element, mm from garment reference points", "Finished-garment positions; embroider flat on the cut pieces and convert to cut-piece coordinates with your pattern (seam / hem allowances). Tolerance ±2 mm, ±5°.", "T8")
    rows = [["01 coin patch", "front-R coin pocket", "76 × 56", "patch top edge = coin-pocket opening; centre on the HI coin-pocket position; rivets through the top corners", ""],
            ["02 spill", "front-R facing", "71 × 14", "pocket-line (y 0 in the file) = the coin pocket's top edge; candies run 3 mm under the patch", "facing >= 3 mm clear of the WB seam " + PROPOSED],
            ["03 WB patch", "back WB, wearer's R", "80 × 54", "top edge 3 mm below WB top, outer edge 25 mm from the side belt loop; runs over the waist seam onto the back panel (sew on after assembly + wash)", "CONFIRMED (founder 20 Oct)"],
            ["04 haki group", "back pocket L", f"{RB['haki']['size_mm'][0]:.0f} × {RB['haki']['size_mm'][1]:.0f}", f"yellow-star centre {HAKI_POS[0]:.0f} mm in from the OUTER edge, {HAKI_POS[1]:.0f} mm below the pocket top edge; baseline level", "clears hem topstitch (13) + outer topstitch (11)"],
            ["05 pink star", "back pocket R", "10 × 10", f"centre {STARP_POS[0]:.0f} mm in from the OUTER edge, {STARP_POS[1]:.0f} mm below the top edge (mockup 8 mm in: moved 9 mm inward, topstitch)", ""],
            ["06 yellow star", "back pocket L", "10 × 10", f"centre {STARY_POS[0]:.0f} mm in from the outer edge, {STARY_POS[1]:.0f} mm above the lower outer corner", "kept: founder confirmed 19 Oct"],
            ["07 front stars", "front-R leg panel", "14 × Ø10", "per-star table on G7 (x from side seam, y from WB top); check vs mockup on C5", "artwork to follow [MISSING]; stars PROPOSED"]]
    tb, y = table(12, 36, [("Element", 28), ("Piece", 34), ("Size mm", 18), ("Position (finished)", 148), ("Note", 50)], rows, 1.85, 6.2)
    o.append(tb)
    # pocket detail drawings, 0.6 scale
    def pocket(ox, oy, s, side):
        x0, x1, top = BACK_POCKETS[side]
        Wp = (x1 - x0) * MMPX; Hs = (352 - 183) * MMPX; Hp = (372 - 183) * MMPX
        pts = [(0, 0), (Wp, 0), (Wp - 8 * MMPX, Hs), (Wp / 2, Hp), (8 * MMPX, Hs)]
        P = Polygon(pts)
        g = [f'<path d="{geom_to_path(affinity.translate(affinity.scale(P, s, s, origin=(0, 0)), ox, oy))}" fill="{FL.DENIM_LT}" stroke="{INK}" stroke-width="0.3"/>']
        ko = P.difference(P.buffer(-11, join_style="mitre")).union(box(0, 0, Wp, 13))
        g.append(f'<path d="{geom_to_path(affinity.translate(affinity.scale(ko.intersection(P), s, s, origin=(0, 0)), ox, oy))}" fill="#FF8A30" fill-opacity="0.45"/>')
        if side == "L":
            g.append(vis_svg(A["haki"]["vis"], ox + HAKI_POS[0] * s, oy + HAKI_POS[1] * s, s))
            g.append(vis_svg(A["starY"]["vis"], ox + (8 * MMPX + STARY_POS[0]) * s, oy + (Hs - STARY_POS[1]) * s, s))
            g.append(dim_h(ox, ox + HAKI_POS[0] * s, oy + HAKI_POS[1] * s - 9, f"{HAKI_POS[0]:.0f}", 1.8))
            g.append(dim_v(oy, oy + HAKI_POS[1] * s, ox + HAKI_POS[0] * s - 4, f"{HAKI_POS[1]:.0f}", 1.8))
            g.append(t(ox, oy + Hp * s + 5, "wearer's LEFT back pocket (outer edge = left)", 1.9, 700))
        else:
            g.append(vis_svg(A["starP"]["vis"], ox + (Wp - STARP_POS[0]) * s, oy + STARP_POS[1] * s, s))
            g.append(dim_h(ox + (Wp - STARP_POS[0]) * s, ox + Wp * s, oy + STARP_POS[1] * s + 6, f"{STARP_POS[0]:.0f}", 1.8))
            g.append(dim_v(oy, oy + STARP_POS[1] * s, ox + (Wp - STARP_POS[0]) * s - 6, f"{STARP_POS[1]:.0f}", 1.8))
            g.append(t(ox, oy + Hp * s + 5, "wearer's RIGHT back pocket (outer edge = right)", 1.9, 700))
        return "\n".join(g)
    o.append(pocket(20, y + 8, 0.40, "L")); o.append(pocket(105, y + 8, 0.40, "R"))
    o.append(t(16, SH - 12, "Orange = topstitch + 3 mm keep-out (pocket hem 13 mm, sides 11 mm): no embroidery. Pocket outline from the flat (schematic) — use the HI pocket pattern.", 1.8, 500, ORANGE))
    # waistband patch detail
    wx, wy = 205, y + 8
    o.append(t(wx, wy - 2, "03 on the back waistband (0.6 : 1)", 1.9, 700))
    s = 0.6
    o.append(f'<rect x="{wx}" y="{wy}" width="{f(84 * s)}" height="{f(40 * s)}" fill="{FL.DENIM_LT}" stroke="{INK}" stroke-width="0.3"/>')
    o.append(t(wx + 86 * s, wy + 20 * s, "WB 40 (HI pattern)", 1.6, 500, MUTED))
    o.append(vis_svg(A["wb"]["vis"], wx + 2, wy + 3 * s, s))
    o.append(dim_v(wy, wy + 3 * s, wx - 2, "3", 1.6))
    return o

# ---------------------------------------------------------------- G1 embroidery summary + thread chart
def G1():
    o = hdr("G1 · EMBROIDERY SUMMARY — files, read-back numbers, threads", f"01–03 + stars digitised from the founder's vector art (inputs/svg); 04 'haki' traced from its mockup. Every number read back from the written DST (readback.dst). Machine time at {PROF['spm']} spm + 6 s per trim + 4 s per colour change (factory.json). <= {factory.max_threads()} threads per file.", "G1")
    rows = []; tot = dict(st=0, tr=0, mi=0)
    for k, no, title, piece, proc, stem in EL:
        r = RB[k]
        rows.append([no, title[:44], f"{stem}.dst/.pes", f"{r['size_mm'][0]:.1f} × {r['size_mm'][1]:.1f}", f"{r['stitches']:,}", str(r["trims"]), str(r["stops"]),
                     str(r["threads"]), f"{r['max_stitch']}", f"{r['machine_min']}"])
        if not k.startswith("front"): tot["st"] += r["stitches"]; tot["tr"] += r["trims"]; tot["mi"] += r["machine_min"]
    tb, y = table(12, 34, [("#", 9), ("Element", 70), ("File", 72), ("Size mm", 22), ("Stitches", 18), ("Trims", 12), ("Stops", 12), ("Thr.", 10), ("Max st.", 14), ("Min", 12)], rows, 1.85, 4.6)
    o.append(tb)
    o.append(t(12, y + 1, f"Per garment, confirmed elements 01–06: {tot['st']:,} stitches · {tot['tr']} trims · {tot['mi']:.1f} machine-min. 07a/07b (PROPOSED) not included.", 2.0, 700))
    y += 6
    o.append(t(12, y, "Method:", 2.0, 700))
    o.append(t(28, y, "PATCHES (01 coin pocket, 03 waistband): embroidered on twill, heat-cut edge, then sewn onto the jean AFTER the wash with a 1 mm red edge stitch; backing cut-away  " + PROPOSED, 1.85, 400, AMBER))
    o.append(t(28, y + 3.6, "SEWN STRAIGHT ONTO THE PANEL (02 facing, 04–06 back pockets, 07 front leg): embroidered on the flat cut piece before the jean is assembled, then washed with the jean; tearaway backing  " + PROPOSED, 1.85, 400, AMBER))
    y += 10
    o.append(t(12, y, "Thread chart (house palette, 40wt polyester; black 60wt) — closest catalogue match by ΔE2000", 2.4, 700)); y += 5
    used = {}
    for k, no, *_ , stem in EL:
        for ps in RB[k]["per_stop"]:
            if ps.get("col"): used.setdefault(ps["col"], set()).add(no)
    trs = []
    for key, (hexc, name, use) in KJ_PAL.items():
        pn = tech.match(hexc, "polyneon"); iso = tech.match(hexc, "isacord")
        trs.append((key, hexc, name, use, pn, iso))
    xx = 12
    for i, (key, hexc, name, use, pn, iso) in enumerate(trs):
        yy = y + i * 4.6
        o.append(swatch(xx, yy, hexc)); o.append(t(xx + 7, yy, name, 1.9, 700)); o.append(t(xx + 34, yy, hexc, 1.8, 400, MUTED))
        o.append(t(xx + 50, yy, kjcore.WEIGHT[key], 1.8))
        o.append(t(xx + 62, yy, f"Polyneon {pn[0]} (ΔE {pn[3]:.1f})", 1.8, 400, RED if pn[3] > 3 else INK))
        o.append(t(xx + 104, yy, f"Isacord {iso[0]} (ΔE {iso[3]:.1f})", 1.8, 400, RED if iso[3] > 3 else INK))
        o.append(t(xx + 146, yy, "files " + ", ".join(sorted(used.get(key, []))), 1.8, 400, MUTED))
        o.append(t(xx + 196, yy, use, 1.7, 400, MUTED))
    return o

# ---------------------------------------------------------------- element spec pages
def stop_table(rb, x, y):
    rows = []
    for ps in rb["per_stop"]:
        col = ps.get("col")
        rows.append([str(ps["stop"]), KJ_PAL[col][1] if col else "—", ", ".join(ps.get("codes", [])), f"{ps['stitches']:,}", str(ps["trims"])])
    tb, y2 = table(x, y, [("Stop", 9), ("Thread", 24), ("Objects", 26), ("Stitches", 15), ("Trims", 10)], rows, 1.75, 3.4)
    sw = []
    for i, ps in enumerate(rb["per_stop"]):
        if ps.get("col"): sw.append(swatch(x + 6.2, y + 3.4 * (i + 1) - 0.1, KJ_PAL[ps["col"]][0], 2.4, 2.2))
    return tb + "\n".join(sw), y2

def stitch_check(vis):
    """house thresholds per thread layer: min stroke / gap / counter (skill reference)."""
    import numpy as np
    from scipy import ndimage as ndi
    from qa import rast, disk
    out = []
    by = {}
    for r in vis: by.setdefault(r["col"], []).append(r["geom"])
    for col, gs in by.items():
        g = unary_union(gs)
        if g.area < 0.5: continue
        thin60 = col in ("kj_black", "kj_blue60")
        ms, mg, mc = (0.6, 0.35, 0.45) if thin60 else (0.8, 0.5, 0.6)
        px = 30; ink = rast(g, px)
        thin = ink & ~ndi.binary_opening(ink, structure=disk(ms, px))
        bg = ~ink; lab, n = ndi.label(bg)
        border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
        bdt = ndi.distance_transform_edt(bg)
        small = 0
        for sl_i, sl in enumerate(ndi.find_objects(lab), 1):
            if sl_i in border or sl is None: continue
            if 2 * bdt[sl][lab[sl] == sl_i].max() / px < mc: small += 1
        thin_pct = 100 * thin.sum() / max(ink.sum(), 1)
        out.append([KJ_PAL[col][1], f"{ms}/{mg}/{mc}", f"{thin_pct:.1f} %", str(small), "PASS" if thin_pct < 3 and small == 0 else "CHECK"])
    return out

def element_page(pid, key, no, title, piece, proc, stem, ref_png=None, ref_crop=None, extra=None, miss="", ref_label="B · MOCKUP REFERENCE (placement + colour; art from inputs/svg)"):
    rb = RB[key]
    pair = " · house patch spec (6.5 border, 5.8 pitch), pairs with patch " + ("03" if no == "01" else "01") if "patch" in proc else " · konpeito stars 10 mm, same as every star on the jean"
    o = hdr(f"{pid} · {no} {title}", f"{proc} · {piece} · {REV} · {DATE} · finished size, mm · DST/PES {stem}{pair}", pid)
    # A: stitch preview from the DST at a stated scale
    prev = Image.open(f"out/stitch/{stem}_preview.png")
    wmm, hmm = rb["size_mm"]; sc = min(120 / wmm, 92 / hmm, 4.0)
    tag, h = img(prev, 12, 32, w=(wmm + 4) * sc); o.append(t(12, 30, f"A · STITCH PREVIEW from the DST (scale {sc:.2f} : 1)", 2.3, 700)); o.append(tag)
    o.append(dim_h(12 + 2 * sc, 12 + (wmm + 2) * sc, 32 + h + 4, f"{wmm:.1f}", 2.0))
    o.append(dim_v(32 + 2 * sc, 32 + (hmm + 2) * sc, 12 + (wmm + 4) * sc + 4, f"{hmm:.1f}", 2.0, side=1))
    y = 32 + h + 10
    # B: mockup reference
    if ref_png:
        im = Image.open(ref_png).convert("RGB")
        if ref_crop: im = im.crop(ref_crop)
        hh_ = min(SH - y - 18, 46, 130 * im.height / im.width)          # never wider than the left column
        tag, hh = img(im, 12, y + 2, h=hh_); o.append(t(12, y, ref_label, 2.1, 700)); o.append(tag)
        y += hh + 4
    # C: numbers
    cx = 150
    o.append(t(cx, 30, "C · FILE (read back from the DST)", 2.3, 700))
    for i, (a, b) in enumerate([("Stitches", f"{rb['stitches']:,}"), ("Trims", str(rb["trims"])), ("Colour stops", str(rb["stops"])),
                                 ("Threads", f"{rb['threads']} (limit {factory.max_threads()})"), ("Max stitch", f"{rb['max_stitch']} mm (<= 7.5)"),
                                 ("Design size", f"{wmm:.1f} × {hmm:.1f} mm"), ("Machine time", f"{rb['machine_min']} min / piece"),
                                 ("Trims / 10k st.", f"{rb['trims'] / max(rb['stitches'], 1) * 1e4:.0f}")]):
        o.append(t(cx, 35 + i * 3.8, a, 1.9, 400, MUTED)); o.append(t(cx + 26, 35 + i * 3.8, b, 1.9, 700))
    st, y2 = stop_table(rb, cx + 62, 35 - 3.4); o.append(st)
    yy = max(35 + 8 * 3.8, y2) + 3
    o.append(t(cx, yy, "D · STITCH CHECK per thread (min stroke / gap / counter, mm)", 2.1, 700)); yy += 4
    tb, yy = table(cx, yy, [("Thread", 30), ("Thresholds", 22), ("Thin area", 16), ("Small counters", 22), ("", 12)], stitch_check(A[key]["vis"] if key in A else []), 1.75, 3.4)
    o.append(tb)
    g = GATES.get(key)
    if g:
        yy += 2; o.append(t(cx, yy, "E · FIDELITY (LESSONS A14) — motif_match per family; compare sheet in the pack", 2.1, 700)); yy += 4
        rows = [[r["family"][:34], str(r["motifs"]), str(r["passed"]), str(r["min_iou"]), str(r["mean_iou"])] for r in g["families"]]
        col = {(i, 2): (GREEN if r["passed"] == r["motifs"] else RED) for i, r in enumerate(g["families"])}
        tb, yy = table(cx, yy, [("Family", 50), ("Motifs", 11), ("Pass", 10), ("min IoU", 13), ("mean", 11)], rows, 1.7, 3.3, colours=col)
        o.append(tb)
        if g.get("centreline"):
            yy += 1.5; o.append(t(cx, yy, "Lettering + line art — centreline gate (mean dist <= 0.5 mm, width +-20 % vs the art)", 1.9, 700)); yy += 3.6
            rows = [[r["family"][:30], str(r["mean_d"]), str(r["w_ref"]), str(r["w_dst"]), str(r["ratio"]), "PASS" if r["ok"] else "FAIL"] for r in g["centreline"]]
            col = {(i, 5): (GREEN if r["ok"] else RED) for i, r in enumerate(g["centreline"])}
            tb, yy = table(cx, yy, [("String / line", 40), ("dist mm", 13), ("w art", 15), ("w DST", 13), ("ratio", 10), ("", 11)], rows, 1.7, 3.3, colours=col)
            o.append(tb)
    gen = A.get("generated", {}).get(key) or (A.get("generated", {}).get("star" + key[-1]) if key.startswith("star") else None)
    yy += 2
    o.append(t(cx, yy, "F · NOTES", 2.1, 700)); yy += 3.8
    notes = (extra or []) + [("Generated, not traced: " + (g_.replace("[proposed — confirm]", "(confirmed 19 Oct)") if key == "spill" else g_)) for g_ in (gen or [])]
    for n_ in notes:
        for k_, ln in enumerate(wrap(n_, 92)):
            o.append(t(cx, yy, ln, 1.7, 400, AMBER if ("PROPOSED" in ln or "MISSING" in ln or "proposed" in ln) else INK)); yy += 3.0
    if miss:
        o.append(missing(cx, min(yy + 2, SH - 26), 135, 13, miss, 1.9))
    return o

def wrap(s, n):
    words = s.split(); lines = [""]
    for w in words:
        if len(lines[-1]) + len(w) + 1 > n: lines.append("")
        lines[-1] += ("" if not lines[-1] else " ") + w
    return lines

def G7():
    o = hdr("G7 · 07 FRONT-LEG KONPEITO STARS — artwork to follow, PROPOSED star map", "Wearer's right front leg panel. The front-leg artwork is to follow from Haki; this page holds the placement area and the PROPOSED positions of the candy stars, read from the garment mockup (check on C5).", "G7")
    o.append(missing(12, 30, 273, 11, ["07 front-leg: artwork to follow [MISSING]",
                                       "The stars below are PROPOSED positions and PROPOSED stitch files (07a / 07b); they are replaced when Haki sends the front-leg artwork."], 2.0))
    s = 0.125
    o.append(f'<g transform="translate({f(14 - FB[0] * s)} 46) scale({s})">{FRONT_SVG}{emb_front()}</g>')
    sil = affinity.scale(SIL["front"], MMPX, MMPX, origin=(0, 0))
    area = Polygon([(790 * MMPX, 190 * MMPX), (990 * MMPX, 190 * MMPX), (960 * MMPX, 900 * MMPX), (790 * MMPX, 900 * MMPX)]).intersection(sil)
    area = affinity.translate(area, -760 * MMPX, 0)
    o.append(f'<path d="{geom_to_path(affinity.translate(affinity.scale(area, s, s, origin=(0, 0)), 14 - FB[0] * s, 46))}" fill="#FFB000" fill-opacity="0.14" stroke="{AMBER}" stroke-width="0.4" stroke-dasharray="1.2 0.7"/>')
    for d in FRONT["stars"]:
        X, Y = star_flat_mm(d["id"]); X = 14 - FB[0] * s + X * s; Y = 46 + Y * s
        o.append(t(X + 2.0, Y + 0.7, d["id"], 1.3, 700, "#FFFFFF"))
    o.append(t(120, SH - 16, "Amber area on the flat = star area: below the front pocket opening to ~830 mm below the WB top, within ~120 mm of the side seam.", 1.8, 500, AMBER))
    rows = [[d["id"], d["col"], f"{d['x_from_side_mm']:.0f}", f"{d['y_from_waist_mm']:.0f}",
             ("—" if d["below_opening_mm"] is None else f"{d['below_opening_mm']:.0f}"),
             (f"moved {d['moved_in_mm']:.0f} mm in (side-seam keep-out)" if d["moved_in_mm"] else ""),
             "07a" if d["id"] in FRONT["sections"][0] else "07b"] for d in FRONT["stars"]]
    o.append(t(120, 48, "PROPOSED star map — 10 mm konpeito stars (same as every star on the jean), size 32", 2.2, 700, AMBER))
    tb, y = table(120, 53, [("Star", 11), ("Colour", 14), ("x from side seam", 25), ("y from WB top", 22), ("gap below pocket opening", 36), ("Note", 46), ("File", 10)], rows, 1.8, 3.8)
    o.append(tb)
    y += 3
    der = FRONT["derivation"]
    for ln in ["x = mm in from the side seam at the star's height; y = mm down from the top of the waistband at the side seam (origin O, C5).",
               "Gap = from the star's top edge down to the front pocket opening above it ('—' = the star is not under the opening).",
               f"Every star sits on the front leg panel BELOW the pocket opening: {len(der['stars_inside_opening'])} of {len(FRONT['stars'])} inside the opening (check on C5).",
               "Stars over the area where the front pocket bag hangs behind the panel are embroidered on the flat front panel BEFORE the",
               "pocket bag is attached, so the bag is never stitched shut.",
               "Positions are size 32; grade with the leg (keep the gap to the pocket opening and the distance to the side seam).",
               f"Files 07a ({RB['front1']['stitches']:,} st, {RB['front1']['trims']} trims, {RB['front1']['size_mm'][0]:.0f} × {RB['front1']['size_mm'][1]:.0f} mm) and 07b ({RB['front2']['stitches']:,} st, {RB['front2']['trims']} trims,",
               f"{RB['front2']['size_mm'][0]:.0f} × {RB['front2']['size_mm'][1]:.0f} mm) = PROPOSED stars only, one hooping each on the {factory.largest_frame()[0]:.0f} × {factory.largest_frame()[1]:.0f} mm frame."]:
        o.append(t(120, y, ln, 1.75, 400, AMBER if ("PROPOSED" in ln) else INK)); y += 3.3
    return o

def C5():
    """07 star map: overlay check against the garment mockup (founder review item 15). The maths, read from out/front_stars.json."""
    der = FRONT["derivation"]
    o = hdr("C5 · CHECK — 07 star map vs the garment mockup (overlay)", "Haki placement check (not a sewing instruction): the corrected star map drawn back onto the mockup and onto the flat, with the maths. Sewing positions are on G7.", "C5")
    im = Image.open("out/check_07_mockup.png")
    tag, h = img(im.crop((0, 0, im.width, int(im.height * 0.42))), 12, 32, h=118); o.append(tag)
    o.append(t(12, 30.5, "A · MOCKUP with the map (front view, wearer's right leg; 3x)", 2.0, 700))
    w = 118 * im.width / int(im.height * 0.42)
    tag2, h2 = img(im.crop((0, int(im.height * 0.42), im.width, im.height)), 12 + w + 4, 32, h=118); o.append(tag2)
    o.append(t(12 + w + 4, 30.5, "lower leg", 2.0, 700))
    # B: flat with the same stars + the opening
    s = 0.1
    bx = 12 + w + 4 + 118 * im.width / (im.height - int(im.height * 0.42)) + 8
    o.append(t(bx, 30.5, "B · FLAT (T2) with the same map", 2.0, 700))
    o.append(f'<g transform="translate({f(bx - FB[0] * s)} 34) scale({s})">{FRONT_SVG}{emb_front()}</g>')
    op = [((x - 760) * MMPX, y * MMPX) for x, y in FL.OPENING_PX]
    o.append('<path d="M' + " L".join(f"{f(bx - FB[0] * s + x * s)} {f(34 + y * s)}" for x, y in op) + '" fill="none" stroke="#FF8C00" stroke-width="0.6"/>')
    # C: maths
    x0 = 12; y = 160
    o.append(t(x0, y, "C · MATHS (out/front_stars.json, kjfront.py)", 2.2, 700)); y += 5
    oxm = der["pocket_opening_mm"]
    ra = {d["id"]: d for d in json.load(open("inputs/front_stars_RevA.json"))["stars"]}       # Rev A map, kept for this comparison
    dy = [ra[d["id"]]["y_from_waist_mm"] - d["y_from_waist_mm"] for d in FRONT["stars"]]
    mv = (min(dy), max(dy), max(abs(ra[d["id"]]["x_from_side_mm"] - d["x_from_side_mm"]) for d in FRONT["stars"]))
    lines = [f"1. Scale from the waistband: the front waistband on the mockup is {der['wb_width_px']} px wide (traced silhouette, at the WB mid-height row {der['wb_mid_row_px']:.0f}).",
             f"   The flat front shows half the waist: size 32 relaxed waist 33.1 in / 2 = {der['half_waist_mm']} mm  ->  {der['half_waist_mm']} / {der['wb_width_px']} = {der['mm_per_px']} mm per px.",
             f"2. Origin O = top of the waistband at the side seam (mockup px {der['origin_px'][0]:.0f}, {der['origin_px'][1]:.0f}); y straight down, x in from the side seam at each star's height.",
             f"3. Pocket opening traced from the mockup (5x zoom, 10 px grid): from the side seam at y {oxm[0][1]:.0f} mm, lowest point y {max(p[1] for p in oxm):.0f} mm, up to the rivet at x {oxm[-1][0]:.0f} / y {oxm[-1][1]:.0f} mm.",
             f"4. Result: {len(der['stars_inside_opening'])} of {len(FRONT['stars'])} stars inside the opening; the top stars S01 / S02 sit {FRONT['stars'][0]['below_opening_mm']:.0f} / {FRONT['stars'][1]['below_opening_mm']:.0f} mm below it, on the front leg panel, as on the mockup.",
             "5. Rev A cause: the flat's scoop line was drawn ~50 mm too low (reaching the side seam ~185 mm below the WB top instead of ~125 mm), so the stars looked",
             f"   as if they were inside the pocket. Rev B redraws the scoop from the traced opening. With the new scale + origin the stars moved up {mv[0]:.0f}-{mv[1]:.0f} mm (sideways <= {mv[2]:.1f} mm); 07a / 07b rebuilt."]
    for ln in lines: o.append(t(x0, y, ln, 1.8, 400, INK)); y += 3.5
    return o

def compare_page(pid, name, title):
    o = hdr(f"{pid} · COMPARE — {title}", "Founder's vector art (left; 04 haki: mockup) vs stitch preview drawn from the shipped DST (right), same scale; live view; zooms; centreline + A14 motif_match + A15 tables.", pid)
    im = Image.open(f"out/compare_{name}.png")
    gap = 4
    def fit(n): return min((273 - gap * (n - 1)) / n / im.width, 172 / math.ceil(im.height / n))
    n = max(range(1, 5), key=fit)                       # tall sheet: n side-by-side columns, largest scale wins
    ch = math.ceil(im.height / n); sc = fit(n)
    for k in range(n):
        part = im.crop((0, k * ch, im.width, min(im.height, (k + 1) * ch)))
        tag, h = img(part, 12 + k * (im.width * sc + gap), 30, w=im.width * sc, q=88); o.append(tag)
    return o

F1_Y = 176        # below section 5 (chenille) of the engine page (checked on the render)
def F1():
    strike = [dict(file=f"{RB[k]['file']}.dst", piece=title, stitches=RB[k]["stitches"], trims=RB[k]["trims"]) for k, no, title, *_ in EL]
    threads = []
    for key, (hexc, name, use) in KJ_PAL.items():
        pn = tech.match(hexc, "polyneon"); threads.append(dict(name=name, code=f"Polyneon {pn[0]}", de=pn[3]))
    pieces = [dict(piece=f"{no} {title[:30]}", w=RB[k]["size_mm"][0], h=RB[k]["size_mm"][1],
                   hoopings=1 if max(RB[k]["size_mm"]) <= min(factory.largest_frame()) - 16 else 2) for k, no, title, *_ in EL]
    svgs = factory.requests_page(NAME + " (sizes are waist sizes; strike-off = size 32 positions, files are the same for all sizes)", strike, threads, pieces, "F1")
    y = F1_Y
    extra = [t(12, y, "6  Measurements + pattern (garment factory) — founder 19 Oct", 3.2, 700)]
    for i, ln in enumerate(["Back rise, thigh, knee, outseam (every size) and any other gap in the HI chart (blue cells on T3); sizes 29 / 31 / 33 are new (T3):"] + FACTORY_POM
                           + [f"Size labels: waist numbers {' '.join(SIZES)}, loop labels, artwork in the zip (labels/, T7b)."]):
        extra.append(t(16, y + 5 + i * 3.6, ln, 2.2, 400, FAC if i in (1, 2) else INK))
    return svgs[0].replace("</svg>", "\n".join(extra) + "</svg>")

# ---------------------------------------------------------------- build
def build():
    PAGES.clear()
    import kjsvg
    for k_, nm in (("coin", "coin"), ("spill", "spill"), ("wb", "wb")):
        W_, H_ = A[k_]["wh"]; kjsvg.render_svg(A[k_]["src"], W_, H_, 20, bg="#2A2A2E" if k_ == "spill" else "#FFFFFF").save(f"out/svg_{nm}.png")
    idx_plan = [("T1", "Cover / style summary + contents", ""), ("T2", "Flats — front + back", ""),
                ("T3", "POM / size chart (HI, inches + cm; factory fills gaps)", ""),
                ("T4", "Pattern — factory HI pattern, minus cargo", ""), ("T5", "Bill of materials (fabric + trims as HI)", ""),
                ("T6", "Construction, stitching + wash", ""), ("T7", "Labels + trims placement", ""), ("T7b", "Label artwork — size labels + reference", ""),
                ("T8", "Embroidery placement overview", ""), ("G1", "Embroidery summary + thread chart", ""),
                ("G2", "01 Coin-pocket patch こんぺいとう", ""), ("G3", "02 Konpeito spill (facing)", ""), ("G4", "03 Waistband patch ちひろ note", ""),
                ("G5", "04 Back pocket L 'haki' + stars", ""), ("G6", "05 R star + 06 L lower star", ""),
                ("G7", "07 Front-leg stars — PROPOSED map", ""),
                ("C1", "Compare — coin-pocket patch", ""), ("C2", "Compare — konpeito spill", ""), ("C3", "Compare — waistband patch", ""),
                ("C4", "Compare — back-pocket haki", ""), ("C5", "Check — 07 star map vs mockup", ""), ("F1", "Factory requests", "")]
    add("T2", "Flats", T2(), "front-leg art"); add("T3", "POM", T3()); add("T4", "Pattern", T4()); add("T5", "BOM", T5(), "x")
    add("T6", "Construction", T6(), "x"); add("T7", "Labels", T7(), "x"); add("T7b", "Label artwork", T7b()); add("T8", "Placement", T8())
    add("G1", "Embroidery summary", G1())
    SV = "digitised from the founder's vector art (inputs/svg, 16 Oct clean art, true size)"
    tf = A["textfit"]
    add("G2", "Coin", element_page("G2", "coin", "01", "Coin-pocket patch — こんぺいとう", "front-right coin pocket", "embroidered patch, heat-cut edge", RB["coin"]["file"],
                                   "out/svg_coin.png", None,
                                   [f"Art: {SV}: HAKI_coin-pocket_konpeito_ART.svg, layers 01–06 in stitch order; thread = layer fill.",
                                    f"こんぺいとう: satin COLUMNS on the centrelines of the SVG outlines, one width: art {tf['coin']['04_lettering_RED']['w_art']} mm -> {tf['coin']['04_lettering_RED']['w_needle']} mm needle span; round ends, centre-run underlay; ぺ ring = radial satin.",
                                    "Border: house spec — 2.0 red heat-cut satin edge + 4.5 band, Ø4.0 white flowers / Ø1.5 dots at 5.8 pitch (the SVG's layer 03); rivet corners TL + TR plain.",
                                    "Rivets: HI 15 L matte black (Ø9.5 cap) centred 4.25 / 4.25 from the edges: the cap covers edge + band + 3.5 mm² of plain cream field per corner, no motif; overhangs the patch edge 0.5 mm.",
                                    "Konpeito: one satin per SVG lobe along its axis; the tint centre star = its own lobes on top; white specks + red accent dots = round bead satin dots at the SVG centres.",
                                    "Edge red, as in the SVG (shared with patch 03): confirmed by the founder 19 Oct (the mockup edge reads cream).",
                                    "Backing: patch twill + cut-away; sew on AFTER the garment wash (confirmed 19 Oct) with a 1 mm red edge stitch; top edge open (pocket opening).", "Sew-out on the production twill before bulk."],
                                   ref_label="B · FOUNDER'S VECTOR ART (digitised from it)"))
    add("G3", "Spill", element_page("G3", "spill", "02", "Konpeito spilling out of the coin pocket", "front-right pocket facing", "direct embroidery", RB["spill"]["file"],
                                    "out/svg_spill.png", None,
                                    [f"Art: {SV}: HAKI_facing_konpeito_ART.svg — F1 back row (sewn first), then F2 front row (lobes, tint centres, white specks).",
                                     "File y = 0 is the coin pocket's top edge; the art's lower 3 mm runs under the patch so no gap shows at the pocket mouth; SVG centred on the pocket (placement confirmed 19 Oct).",
                                     "Embroider the cut facing BEFORE the coin-pocket patch is attached; tearaway backing.",
                                     "Facing must reach >= 14 mm above the coin pocket and stay 3 mm clear of the WB seam [proposed — confirm]."],
                                    ref_label="B · FOUNDER'S VECTOR ART (digitised from it)"))
    add("G4", "WB patch", element_page("G4", "wb", "03", "Waistband patch — ちひろ note", "back waistband, wearer's right", "embroidered patch, heat-cut edge", RB["wb"]["file"],
                                       "out/svg_wb.png", None,
                                       [f"Art: {SV}: HAKI_waistband-patch_ART.svg, layers 01–16 in stitch order; thread = layer fill.",
                                        "Lettering ちひろ / 元気でね / また会おうね / 理砂, frame, hearts, face: satin COLUMNS on the centrelines of the SVG outlines, ONE width per layer (art width - 0.15 mm):",
                                        "  " + "; ".join(f"{k_.split('_', 1)[1].rsplit('_', 1)[0]} {v['w_art']} -> {v['w_needle']} ({v['thread']})" for k_, v in tf['wb'].items()) + ".",
                                        "Flowers: one satin per petal along its axis; white centres, cheeks, eyes and accent dots = round bead satin dots at the SVG centres and sizes.",
                                        "Flower-centre dots are Ø1.0 in the art: 0.9 mm needle span (visible ~1.1, the house-minimum satin dot). Check 気, 会, 理, 砂 counters on the sew-out.",
                                        "Sew on after the waistband is attached and AFTER the garment wash (confirmed 19 Oct); the patch runs over the waist seam onto the back panel (no yoke); 1 mm red edge stitch. Position CONFIRMED (founder 20 Oct)."],
                                       ref_label="B · FOUNDER'S VECTOR ART (digitised from it)"))
    add("G5", "Haki", element_page("G5", "haki", "04", "Back pocket L — 'haki' + 2 konpeito stars", "wearer's LEFT back pocket", "direct embroidery", RB["haki"]["file"],
                                   "inputs/back_pocket_haki.png", (150, 380, 340, 480),
                                   [f"Founder: scale up so the konpeito match. Mockup stars 14 px vs right-pocket star 30 px -> group scaled x2.14; stars now 10 mm.",
                                    f"Final sizes: group {RB['haki']['size_mm'][0]:.1f} × {RB['haki']['size_mm'][1]:.1f} mm; 'haki' ~{RB['haki']['size_mm'][0] - 2 * 10 - 8:.0f} mm wide, 2 mm light-blue satin strokes; stars 10 mm.",
                                    f"Placement: yellow-star centre {HAKI_POS[0]:.0f} mm in from the outer edge, {HAKI_POS[1]:.0f} mm below the pocket top edge (moved down from the mockup to clear the hem topstitch).",
                                    "Lettering light blue = Blue tint #8ED2EE (closest house thread to the mockup's light blue) [proposed — confirm].",
                                    "Stars: the founder's vector stars (inputs/svg), 10 mm. 'haki' is not in the SVGs: traced from inputs/back_pocket_haki.png (as before).",
                                    "Embroider the cut pocket before hemming / attaching; tearaway."]))
    add("G6", "Stars", element_page("G6", "starP", "05", "Back pocket R — pink konpeito star (+ 06 L lower yellow star)", "wearer's RIGHT back pocket", "direct embroidery", RB["starP"]["file"],
                                    "inputs/back_pocket_haki.png", (1040, 370, 1180, 520),
                                    [f"05: centre {STARP_POS[0]:.0f} mm in from the outer edge, {STARP_POS[1]:.0f} mm below the top edge (mockup ~8 mm in: moved inward to clear the outer topstitch).",
                                     f"06 (file {RB['starY']['file']}, {RB['starY']['stitches']} st, {RB['starY']['trims']} trim): yellow star at the left pocket's lower outer corner, {STARY_POS[0]:.0f} mm in from the outer edge, {STARY_POS[1]:.0f} mm above the lower corner — KEPT, confirmed by the founder 19 Oct.",
                                     "Stars: the founder's vector star (inputs/svg/HAKI_back-pocket-stars_ART.svg: STAR_P / STAR_Y + highlight layers), 10 mm tip to tip; body + tint highlight, radial satin, edge-run underlay."]))
    add("G7", "Front leg", G7(), "x")
    add("C1", "Compare coin", compare_page("C1", "coin-pocket-patch", "01 coin-pocket patch"))
    add("C2", "Compare spill", compare_page("C2", "coin-spill", "02 konpeito spill"))
    add("C3", "Compare wb", compare_page("C3", "waistband-patch", "03 waistband patch"))
    add("C4", "Compare haki", compare_page("C4", "back-pocket-haki", "04 back-pocket haki group"))
    add("C5", "Check 07", C5())
    PAGES.append(("F1", "Factory requests", F1(), ""))
    # cover flags come from each page's actual content: a page is flagged when it carries a "[MISSING — …]" box
    import re
    # cover flags: what Haki still owes, per page; every flagged page must carry a [MISSING] mark and no other page may
    FLAGS = {"T2": "front-leg artwork", "T5": "label + hang tag art; packing design; barcodes", "T7": "main, care + hang tag art",
             "T7b": "main + care label art", "T8": "front-leg artwork", "G7": "front-leg artwork"}
    has = {pid for pid, _, svg, _ in PAGES if "[MISSING]" in svg}
    assert has == set(FLAGS), f"[MISSING] marks on {sorted(has)} vs cover flags {sorted(FLAGS)}"
    state = {pid: [FLAGS[pid]] for pid in FLAGS}
    index = [(pid, title, "; ".join(state.get(pid, []))) for pid, title, _ in idx_plan]
    print("cover flags:", {p_: m for p_, _, m in index if m})
    PAGES.insert(0, ("T1", "Cover", page(T1(index)), ""))
    pdfs = []
    for pid, title, svg, miss in PAGES:
        p = f"{OUT}/{pid}.pdf"; cairosvg.svg2pdf(bytestring=svg.encode(), write_to=p); pdfs.append(p)
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{OUT}/prev_{pid}.png", output_width=2000)
    w = PdfWriter()
    for p in pdfs:
        for pg in PdfReader(p).pages: w.add_page(pg)
    final = f"out/HAKI_konpeito-jeans_TECHPACK_{REV.replace(' ', '')}.pdf"
    w.write(final)
    print("pages", len(pdfs), final, os.path.getsize(final) // 1024, "kB")
    return final


# ---------------------------------------------------------------- deliverable folder + zip
def art_svg(vis, stops_plan, W, H, ox=0, oy=0):
    groups = []
    for i, (col, codes) in enumerate(stops_plan, 1):
        rs = [r for r in vis if r["col"] == col and r["grp"] in codes]
        if not rs: continue
        d = " ".join(geom_to_path(r["geom"]) for r in rs)
        groups.append(f'<g id="{i:02d}_{"-".join(sorted(codes))}_{KJ_PAL[col][1].upper().replace(" ", "_").replace("(", "").replace(")", "")}"><path d="{d}" fill="{KJ_PAL[col][0]}" fill-rule="evenodd"/></g>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{f(W)}mm" height="{f(H)}mm" viewBox="{f(ox)} {f(oy)} {f(W)} {f(H)}">' + "\n".join(groups) + "</svg>")

def preview_1to1(png, wmm, hmm, out_pdf, title):
    im = Image.open(png); pad = 2.0
    tag, _ = img(im, 20, 30, w=wmm + 2 * pad)
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>', t(20, 18, title + " — stitch preview at 1 : 1 (print at 100 %)", 3.2, 700),
         t(20, 24, f"Drawn from the DST read-back. Design {wmm:.1f} × {hmm:.1f} mm. 50 mm check bar below.", 2.2, 400, MUTED), tag,
         f'<line x1="20" y1="{f(36 + hmm + 2 * pad)}" x2="70" y2="{f(36 + hmm + 2 * pad)}" stroke="{INK}" stroke-width="0.4"/>',
         t(20, 34 + hmm + 2 * pad, "50 mm", 2.0)]
    if hmm + 2 * pad > SH - 40:     # tall files: A4 portrait would not hold them either; scale note
        o.append(t(20, SH - 8, "File taller than the page: printed scale reduced — check with the 50 mm bar.", 2.0, 600, AMBER))
    cairosvg.svg2pdf(bytestring=page(o).encode(), write_to=out_pdf)

def package(final):
    import kjstitch as K
    pkg = "out/pkg"; shutil.rmtree(pkg, ignore_errors=True); os.makedirs(pkg)
    for k, no, title, piece, proc, stem in EL:
        d = f"{pkg}/elements/{no}_{stem.split('_', 3)[-1]}"; os.makedirs(d, exist_ok=True)
        for ext in (".dst", ".pes"): shutil.copy(f"out/stitch/{stem}{ext}", d)
        shutil.copy(f"out/stitch/{stem}_preview.png", f"{d}/{stem}_PREVIEW.png")
        rb = RB[k]
        preview_1to1(f"out/stitch/{stem}_preview.png", rb["size_mm"][0], rb["size_mm"][1], f"{d}/{stem}_PREVIEW_1to1.pdf", f"{no} {title}")
        # thread chart (per stop, read back)
        lines = [f"{no} {title}", f"file {stem}.dst / .pes — {rb['stitches']:,} stitches, {rb['trims']} trims, {rb['stops']} stops, {rb['threads']} threads, max stitch {rb['max_stitch']} mm, {rb['size_mm'][0]} x {rb['size_mm'][1]} mm, {rb['machine_min']} min",
                 "", "stop  thread         hex      weight  Polyneon       Isacord        stitches  trims"]
        for ps in rb["per_stop"]:
            c = ps.get("col"); hexc = KJ_PAL[c][0]; pn = tech.match(hexc, "polyneon"); iso = tech.match(hexc, "isacord")
            lines.append(f"{ps['stop']:>4}  {KJ_PAL[c][1]:<14} {hexc}  {kjcore.WEIGHT[c]:<6}  {pn[0]:<6} dE{pn[3]:.1f}  {iso[0]:<6} dE{iso[3]:.1f}  {ps['stitches']:>8,}  {ps['trims']:>5}")
        open(f"{d}/THREAD_CHART.txt", "w").write("\n".join(lines) + "\n")
        if k in A and "vis" in A[k]:
            vis = A[k]["vis"]; b = unary_union([r["geom"] for r in vis]).bounds
            sv = art_svg(vis, K.FILES[k][1], b[2] - b[0] + 2, b[3] - b[1] + 2, b[0] - 1, b[1] - 1)
            open(f"{d}/ART.svg", "w").write(sv)
            cairosvg.svg2png(bytestring=sv.encode(), write_to=f"{d}/ART.png", output_width=int((b[2] - b[0] + 2) * 20))
        if "PROPOSED" in stem:
            open(f"{d}/PROPOSED_README.txt", "w").write("PROPOSED placeholder: candy stars at the mockup positions (G7, check C5). Front-leg artwork: to follow [MISSING];\n"
                                                         "replace this file when it arrives. Positions: G7 star table (x from side seam, y from waistband top, size 32).\n")
    for pid, title, svg, miss in PAGES:
        if pid.startswith("G"): shutil.copy(f"{OUT}/{pid}.pdf", f"{pkg}/elements/SPEC_{pid}.pdf")
    import kjlabels
    os.makedirs(f"{pkg}/labels", exist_ok=True)
    for fn in kjlabels.build():
        shutil.copy(fn, f"{pkg}/labels/")
    shutil.copy(final, pkg)
    readme = f"""HAKI — {NAME} ({STYLE}) — {REV}, {DATE}

Tech pack: {os.path.basename(final)} (T pages = garment, G = embroidery, C = compare sheets, F1 = factory requests).
Pattern: use the factory's Hidden Inventory pants pattern, remove cargo pockets, 5-pocket jean construction (T4).
Sizes: waist """ + " ".join(SIZES) + """ (measurements: T3, from the HI chart; 29 / 31 / 33 half-way PROPOSED; back rise / thigh / knee / outseam from the factory's HI spec).
labels/                  size LOOP labels, one SVG + one PDF per size, 1:1 with dimensions (T7b)

elements/<no>_<name>/  per embroidery element:
  *.dst *.pes            production stitch files (<= 12 threads each; numbers on G1 read back from these DSTs)
  *_PREVIEW.png          stitch preview drawn from the DST
  *_PREVIEW_1to1.pdf     the preview at 1 : 1 (print at 100 %, 50 mm check bar)
  THREAD_CHART.txt       per-stop thread, house hex, Madeira Polyneon / Isacord match (dE2000), stitches, trims
  ART.svg / ART.png      region art, one group per colour stop, 1 SVG unit = 1 mm
elements/SPEC_G*.pdf     the element spec pages

Files:
""" + "\n".join(f"  {no:<4} {stem}  {RB[k]['stitches']:,} st  {RB[k]['trims']} trims  {RB[k]['threads']} threads  {title}" for k, no, title, *_, stem in EL) + """

Fabric, threads, hardware (YKK #4.5 zip fly, 28 L shank button, 15 L rivets) and label types as the Hidden Inventory
pants (T5-T7b); same fit + construction as HI: no back yoke, regular 2-piece waistband joined at CB, 2 back patch pockets
(HI pointed shape), one-piece legs (no knee seam). Wash: washed black matched to the mockup (T6).
Measurements not on the HI chart (back rise, thigh, knee, outseam): factory to fill in from its HI spec/pattern and return
with the fit sample (T3, T4, F1).
Legend: [proposed - confirm] = for the FACTORY to confirm or correct; [MISSING] = Haki still owes it.
PROPOSED: 07a/07b front-leg stars (positions from the mockup, G7 / C5).
MISSING (to follow from Haki): front-leg artwork, main + care label artwork, hang tag artwork, packing design,
barcode per size (HK code from PLM, Code 128 on the polybag sticker).
Sew-out (strike-off) of every file on the washed production denim / patch twill before bulk.
"""
    open(f"{pkg}/README.txt", "w").write(readme)
    z = final.replace(".pdf", ".zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(pkg):
            for fn in files:
                p = os.path.join(root, fn); zf.write(p, os.path.relpath(p, pkg))
    print("zip", z, os.path.getsize(z) // 1024, "kB")
    return z

if __name__ == "__main__":
    import subprocess
    raw = build()
    small = raw.replace(".pdf", "_s.pdf")
    subprocess.run(["python3", "shrink.py", raw, small, "2400", "82"], check=True)
    os.replace(small, raw); print("shrunk", os.path.getsize(raw) // 1024, "kB")
    package(raw)
