"""Dismantle Pants — INTERNAL tech pack, Rev A (sampling draft for the internal team, NOT a factory send).

Model: projects/konpeito-jeans/kjpages.py (same Hidden Inventory silhouette + construction). No embroidery (no G pages, no DST).
Pages: T1 cover, T2 flats + mockup placeholders, P1 print spec, T3 POM, T4 pattern + check matching, T5 BOM,
T6 construction, T7 labels placement, T7b label artwork, Q1 open questions.
Run: source scripts/env.sh projects/dismantle-pants && python3 dmprint.py && python3 dmpages.py
"""
import os, io, sys, json, base64, shutil, zipfile, subprocess
import cairosvg
from PIL import Image
from pypdf import PdfWriter, PdfReader
from shapely import affinity
import sheet
from sheet import t, dim_h, dim_v, INK, MUTED, GUIDE, GREEN, SW, SH
from render import f
import labels as LB

NAME = "Dismantle Pants — Black / Tan check"
STYLE = "HK-PT-DISMANTLE-BK"                      # proposed internal style code
REV = "Rev A"
DATE = "27 Oct 2026"
PLM_ID = "e05f184d-20f9-4aa9-be67-126d0d097344"
PROPOSED = "[proposed — confirm]"
ESTIMATE = "[estimate — confirm]"
sheet.FOOT = f"HAKI STUDIOS · {NAME} · {STYLE} · {REV} · {DATE} · INTERNAL — sampling draft"

import dmprint
PR = dmprint.measure()                            # out/print.json (read by dmflat for the check scale)
import dmflat as FL
import dmlabels as KL

SIZES = KL.SIZE_RUN                               # HI published evens 26-40
CARE_FIBRE = None                                 # shell fabric not chosen (Q1) -> care label cannot be picked (LESSONS D7)
CARE = LB.care_label(CARE_FIBRE or "")
assert CARE is None

AMBER = "#B26A00"; AMBER_BG = "#FFF3DC"
FAC = "#1F5FA8"; FAC_BG = "#E8F0FA"
OUT = "out/pack"; os.makedirs(OUT, exist_ok=True)
MMPX = FL.MM
SQ = PR["square_cm_proposed"]
LINE_HEX = FL.LINE; GROUND_HEX = FL.GROUND


# ---------------------------------------------------------------- helpers (as kjpages)
def page(o): return f'<svg xmlns="http://www.w3.org/2000/svg" width="{SW}mm" height="{SH}mm" viewBox="0 0 {SW} {SH}">' + "\n".join(o) + "</svg>"
def hdr(title, sub, pg): return sheet.header(title, sub, pg)
def wrap(s, n):
    words = s.split(); lines = [""]
    for w in words:
        if len(lines[-1]) + len(w) + 1 > n: lines.append("")
        lines[-1] += ("" if not lines[-1] else " ") + w
    return lines
def amberish(s): return isinstance(s, str) and any(k in s for k in ("MISSING", "proposed", "estimate", "PROPOSED", "OPEN"))
def missing(x, y, w, h, text, size=2.2):
    o = [f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="1.2" fill="{AMBER_BG}" stroke="{AMBER}" stroke-width="0.5" stroke-dasharray="1.6 0.8"/>']
    for i, ln in enumerate(text if isinstance(text, list) else [text]):
        o.append(t(x + 3, y + 5 + i * (size * 1.5), ln, size, 700 if i == 0 else 400, AMBER))
    return "\n".join(o)
def facbox(x, y, w, h, lines, size=2.0, title="FACTORY TO SUPPLY"):
    o = [f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="1.2" fill="{FAC_BG}" stroke="{FAC}" stroke-width="0.5"/>']
    o.append(t(x + 3, y + 5, title, size, 700, FAC))
    for i, ln in enumerate(lines): o.append(t(x + 3, y + 5 + (i + 1) * size * 1.5, ln, size, 400, FAC))
    return "\n".join(o)
def b64(im, q=88):
    buf = io.BytesIO(); im.convert("RGB").save(buf, "JPEG", quality=q)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
def img(path_or_im, x, y, w=None, h=None, q=88):
    im = path_or_im if isinstance(path_or_im, Image.Image) else Image.open(path_or_im)
    if w is None: w = h * im.width / im.height
    if h is None: h = w * im.height / im.width
    return f'<image x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" href="{b64(im, q)}"/>', h
def table(x, y, cols, rows, size=2.0, lh=4.0, head=True, wrapcol=None):
    """cols: [(title, width_mm, wrap_chars or None)]; long cells wrap; returns (svg, y_end)."""
    o = []; xx = x
    if head:
        for c, w, *_ in cols: o.append(t(xx, y, c, size, 700, MUTED)); xx += w
        o.append(f'<line x1="{f(x)}" y1="{f(y + 1.2)}" x2="{f(x + sum(c[1] for c in cols))}" y2="{f(y + 1.2)}" stroke="#BBBBBB" stroke-width="0.2"/>')
        y += lh
    for r in rows:
        xx = x; nl = 1
        for ci, c in enumerate(cols):
            v = r[ci] if ci < len(r) else ""
            n = c[2] if len(c) > 2 else None
            lines = wrap(v, n) if (n and v) else [v]
            for k, ln in enumerate(lines):
                col = AMBER if amberish(v) else INK
                o.append(t(xx, y + k * size * 1.35, ln, size, 700 if ci == 0 else 400, col))
            nl = max(nl, len(lines)); xx += c[1]
        y += lh + (nl - 1) * size * 1.35
        o.append(f'<line x1="{f(x)}" y1="{f(y - lh + 1.3)}" x2="{f(x + sum(c[1] for c in cols))}" y2="{f(y - lh + 1.3)}" stroke="#EEEEEE" stroke-width="0.15"/>')
    return "\n".join(o), y

MAIN_PNG = LB.render(LB.MAIN, dpi=300)
SIL = FL.silhouettes()
FRONT_SVG, FB = FL.front_svg(SIL["front"])
BACK_SVG, BB = FL.back_svg(SIL["back"], label_href=b64(MAIN_PNG))
def flat_group(which, x, y, s):
    body = FRONT_SVG if which == "front" else BACK_SVG
    return f'<g transform="translate({f(x)} {f(y)}) scale({f(s)})">{body}</g>'
FLAT_H = 1240 * MMPX

PAGES = []
def add(pid, title, o): PAGES.append((pid, title, page(o)))


def callout(o, X, Y, lab, dx=11, dy=-7):
    ex, ey = X + dx * 9 / 11, Y + dy * 6 / 7
    o.append(f'<line x1="{f(X)}" y1="{f(Y)}" x2="{f(ex)}" y2="{f(ey)}" stroke="{GUIDE}" stroke-width="0.25"/>')
    o.append(f'<circle cx="{f(X + dx)}" cy="{f(Y + dy)}" r="2.6" fill="#FFFFFF" stroke="{GUIDE}" stroke-width="0.3"/>')
    o.append(t(X + dx, Y + dy + 0.8, lab, 1.9, 700, GUIDE, "middle"))


# ---------------------------------------------------------------- T1 cover
def T1(index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>', t(14, 22, "HAKI STUDIOS", 3.0, 700, MUTED),
         t(14, 34, NAME, 7.0, 700),
         t(14, 41.5, f"Style {STYLE} {PROPOSED} · {REV} · {DATE} · trouser on the Hidden Inventory pants fit + waistband, black / tan windowpane check · sizes {' '.join(SIZES)}", 2.3, 400, MUTED),
         f'<line x1="14" y1="45" x2="{SW-14}" y2="45" stroke="{INK}" stroke-width="0.4"/>']
    o.append(f'<rect x="14" y="49" width="74" height="9" rx="1" fill="{AMBER}"/>')
    o.append(t(51, 55, "INTERNAL — sampling draft", 3.0, 700, "#FFFFFF", "middle"))
    o.append(t(92, 52.5, "For the Haki team to review. NOT a factory send yet: open questions (Q1) first.", 2.0, 600, AMBER))
    o.append(t(92, 56, f"PLM product id {PLM_ID}", 1.9, 400, MUTED))
    s = 0.105
    o.append(flat_group("front", 16 - FB[0] * s, 64, s)); o.append(flat_group("back", 90 - BB[0] * s, 64, s))
    o.append(t(18, 64 + FLAT_H * s + 5, "FRONT", 2.2, 700)); o.append(t(92, 64 + FLAT_H * s + 5, "BACK", 2.2, 700))
    o.append(t(18, 64 + FLAT_H * s + 9, "Flats drawn on the HI silhouette; check drawn at its estimated scale (P1).", 1.7, 400, MUTED))
    ix = 176; o.append(t(ix, 66, "CONTENTS", 2.8, 700)); y = 72
    for pid, title, miss in index:
        o.append(t(ix, y, pid, 1.95, 700)); o.append(t(ix + 9, y, title, 1.95, 400))
        if miss: o.append(t(ix + 9, y + 2.9, "MISSING: " + miss, 1.6, 700, AMBER)); y += 2.9
        y += 4.1
    y += 3
    o.append(t(ix, y, "Summary", 2.2, 700)); y += 4
    for ln in ["Founder (27 Oct): we like the PRINT only. Hidden Inventory fit +",
               "HI waistband construction; back label on the waistband; two back",
               "pockets, HI shape. Everything else here is proposed (amber).",
               "No embroidery on this product."]:
        o.append(t(ix, y, ln, 1.8, 400, INK)); y += 3.2
    y += 2
    o.append(t(ix, y, "Legend", 2.2, 700)); y += 4
    o.append(t(ix, y, "[proposed — confirm] = assumed by us; Haki team to confirm", 1.85, 600, AMBER)); y += 3.5
    o.append(t(ix, y, "[estimate — confirm] = measured from a photo, not a swatch", 1.85, 600, AMBER)); y += 3.5
    o.append(t(ix, y, "[MISSING] = Haki still owes it (decision / file / info)", 1.85, 600, AMBER)); y += 3.5
    o.append(t(ix, y, "FACTORY TO SUPPLY (blue) = from the factory's HI spec / pattern", 1.85, 500, FAC)); y += 3.5
    o.append(t(ix, y, "Dimensions mm unless marked in.", 1.85, 400, MUTED))
    o.append(t(SW - 14, SH - 6, sheet.FOOT, 1.9, 400, MUTED, "end"))
    return o


# ---------------------------------------------------------------- T2 flats
def T2():
    o = hdr("T2 · FLATS — front + back", "Hidden Inventory (HI) pants silhouette and construction lines (as the Konpeito flats), cargo pockets, knee seams, hammer loop and flag labels left off. Check drawn at its estimated scale; black DTM topstitch drawn as grey dashes.", "T2")
    s = 0.104; y0 = 32
    fx = 14 - FB[0] * s; bx = 88 - BB[0] * s
    o.append(flat_group("front", fx, y0, s)); o.append(flat_group("back", bx, y0, s))
    o.append(t(18, y0 + FLAT_H * s + 4, "FRONT", 2.4, 700)); o.append(t(92, y0 + FLAT_H * s + 4, "BACK", 2.4, 700))
    P = lambda gx, x, y: (gx + x * s, y0 + y * s)
    ox = 760
    cs = [(P(fx, (1112 - ox) * MMPX, 72 * MMPX), "B1", (11, -7)), (P(fx, (1092 - ox) * MMPX, 160 * MMPX), "Z1", (11, 5)),
          (P(fx, (960 - ox) * MMPX, 184 * MMPX), "F1", (-10, 8)), (P(fx, (FL.COIN_TL_PX[0] - ox) * MMPX + 30, FL.COIN_TL_PX[1] * MMPX + 30), "C1", (-12, -6)),
          (P(fx, (1190 - ox) * MMPX, 70 * MMPX), "W1", (11, -7)),
          (P(bx, FL.CB_PX * MMPX, (FL.WB_TOP_PX + FL.WB_BOT_PX) / 2 * MMPX), "L1", (2, -11)), (P(bx, 250 * MMPX, 280 * MMPX), "K1", (-12, 4)),
          (P(bx, 323 * MMPX, 60 * MMPX), "W2", (-11, -7)), (P(bx, FL.CB_PX * MMPX, 300 * MMPX), "S1", (10, 8))]
    for (X, Y), lab, (dx, dy) in cs: callout(o, X, Y, lab, dx, dy)
    # mockup placeholders
    px = 159; pw = 51; ph = 64
    for i, side in enumerate(("FRONT", "BACK")):
        yy = 32 + i * (ph + 5)
        o.append(f'<rect x="{px}" y="{yy}" width="{pw}" height="{ph}" rx="1.5" fill="#F4F4F4" stroke="{AMBER}" stroke-width="0.5" stroke-dasharray="2 1.2"/>')
        o.append(t(px + pw / 2, yy + ph / 2 - 3, f"Mockup {side.lower()} — to come", 2.4, 700, AMBER, "middle"))
        o.append(t(px + pw / 2, yy + ph / 2 + 1, "(founder ChatGPT render)", 2.0, 400, AMBER, "middle"))
        o.append(t(px + pw / 2, yy + ph / 2 + 5, "[MISSING]", 2.0, 700, AMBER, "middle"))
    lx = 214; y = 34
    o.append(t(lx, y, "Callouts", 2.6, 700)); y += 5
    for lab, s_ in [("B1", "28 L flat tack shank button, CF (as HI)"), ("Z1", "zip fly, YKK #4.5 metal, 6 in, J topstitch (as HI)"),
                    ("F1", "HI scoop front pockets + 15 L rivets  " + PROPOSED), ("C1", "HI coin pocket, wearer's right  " + PROPOSED),
                    ("W1", "regular waistband, 2 pcs joined at CB (as HI)"), ("W2", "belt loops: 2 front, 2 side-back, 2 either"),
                    ("", "side of the back label (HI CB loop moved)  " + PROPOSED),
                    ("L1", "back label OUTSIDE at CB, sewn all 4 sides  " + PROPOSED), ("K1", "2 HI pointed back patch pockets, centred on"),
                    ("", "each leg, horizontal bartacks top corners"), ("S1", "CB seat seam, NO back yoke (as HI)")]:
        o.append(t(lx, y, lab, 1.9, 700, GUIDE))
        o.append(t(lx + 6, y, s_.replace("  " + PROPOSED, ""), 1.75, 400, AMBER if PROPOSED in s_ else INK)); y += 3.6
    y += 2
    for s_ in ["Fit + waistband = Hidden Inventory (founder).", "One panel per leg, waist to hem (no knee",
               "seam, as Konpeito). No cargo pockets, no", "hammer loop, no HI flag labels.",
               "Check: whole garment incl. waistband, loops", "and pockets; matched at seams (T4).",
               "Topstitch: black DTM (tone-on-tone)."]:
        o.append(t(lx, y, s_, 1.75, 400, INK)); y += 3.2
    y += 2
    for ln in ("L / R = the WEARER's. Front view: image left =", "wearer's right (coin pocket). Back view seen", "from behind: image right = wearer's right."):
        o.append(t(lx, y, ln, 1.65, 700, INK)); y += 2.9
    o.append(f'<line x1="18" y1="{SH-13}" x2="{18 + 100 * s}" y2="{SH-13}" stroke="{INK}" stroke-width="0.5"/>')
    o.append(t(18, SH - 14.5, "100 mm at flat scale", 1.8, 400, MUTED))
    return o


# ---------------------------------------------------------------- P1 print spec
def repeat_tile(x, y, scale, n=3):
    """n x n repeats of the proposed check at `scale` page-mm per garment-mm."""
    r = SQ * 10
    pid = f"rp{int(scale * 100)}"
    o = [f'<g transform="translate({f(x)} {f(y)}) scale({f(scale)})">' + FL.check_defs(pid)
         + f'<rect x="0" y="0" width="{f(n * r)}" height="{f(n * r)}" fill="url(#{pid})" stroke="#999" stroke-width="{f(0.2 / scale)}"/></g>']
    return "\n".join(o), n * r * scale

def P1():
    o = hdr("P1 · PRINT SPEC — black / tan windowpane check", "Read from the founder's two reference photos (print ONLY; their elastic waist and shape are ignored). Every number here comes from a photo, not a swatch: amber, confirm on a physical swatch / strike-off.", "P1")
    y0 = 32
    # A: refs
    o.append(t(12, y0, "A · REFERENCES (founder, 27 Oct)", 2.2, 700))
    for i, n in enumerate(("front", "back")):
        tag, h = img(dmprint.REF[n], 12 + i * 33, y0 + 3, w=31); o.append(tag)
        o.append(t(12 + i * 33 + 15.5, y0 + 3 + h + 3, n, 1.8, 600, MUTED, "middle"))
    o.append(t(12, y0 + 50, "Zoom (leg, 120 × 120 px of the photo):", 1.8, 600, INK))
    for i, n in enumerate(("front", "back")):
        tag, h = img(f"out/zoom_{n}.png", 12 + i * 33, y0 + 52, w=31); o.append(tag)
    o.append(t(12, y0 + 87, "The line reads broken / beaded (a 'dashed'", 1.7, 400, INK))
    o.append(t(12, y0 + 90, "look) at photo resolution: typical of a", 1.7, 400, INK))
    o.append(t(12, y0 + 93, "yarn-dyed woven with a twist / marl yarn.", 1.7, 400, INK))
    # B: drawn repeat
    bx = 82
    o.append(t(bx, y0, f"B · PROPOSED REPEAT — {SQ * 10:g} mm square  {ESTIMATE}", 2.2, 700, AMBER))
    tag, w = repeat_tile(bx, y0 + 5, 1.0, 3); o.append(tag)
    o.append(dim_h(bx, bx + SQ * 10, y0 + 5 + w + 3, f"{SQ * 10:g} mm", 1.8))
    o.append(t(bx, y0 + 5 + w + 8, "1 : 1 (3 × 3 repeats; print at 100 %)", 1.7, 400, MUTED))
    tag, w2 = repeat_tile(bx + 44, y0 + 5, 2.0, 1); o.append(tag)
    o.append(t(bx + 44, y0 + 5 + w2 + 3.5, f"2 : 1, one repeat; line ≈ {FL.LINE_W:g} mm", 1.7, 400, MUTED))
    # swatches
    sy = y0 + 56
    o.append(t(bx, sy, "Colours (sampled from the photos — lighting shifts them)", 2.0, 700)); sy += 4
    for lab, hx, src, tcx in (("Ground", GROUND_HEX, f"front {PR['ground_hex']['front']} / back {PR['ground_hex']['back']}", "≈ 19-0303 TCX Jet Black"),
                              ("Line", LINE_HEX, f"front {PR['line_hex']['front']} / back {PR['line_hex']['back']}", "≈ 17-1009 TCX Dune (alt. 16-1010 TCX Incense)")):
        o.append(f'<rect x="{bx}" y="{sy - 3}" width="10" height="7" fill="{hx}" stroke="#999" stroke-width="0.2"/>')
        o.append(t(bx + 12, sy, f"{lab}: {hx}  (photo: {src})", 1.8, 600, INK))
        o.append(t(bx + 12, sy + 3, f"nearest TCX {tcx} — approximate, confirm on a TCX book", 1.7, 600, AMBER)); sy += 10
    o.append(t(bx, sy, "Photo colour of a thin bright line on black reads darker + greyer than the", 1.6, 400, MUTED)); sy += 2.8
    o.append(t(bx, sy, "yarn: expect the real tan to be a touch lighter / warmer. Match to swatch.", 1.6, 400, MUTED))
    # C: spec table
    cx = 176
    o.append(t(cx, y0, "C · PRINT SPEC", 2.2, 700))
    rows = [["Motif", "windowpane grid check: single thin line both ways, equal squares"],
            ["Ground", f"black, {GROUND_HEX} (photo)  {ESTIMATE}"],
            ["Line", f"tan / beige, {LINE_HEX} (photo)  {ESTIMATE}"],
            ["Repeat", f"{SQ * 10:g} mm square, same warp + weft  {ESTIMATE}"],
            ["Line width", f"≈ {FL.LINE_W:g} mm (≈ 1/10 of the repeat in the photo)  {ESTIMATE}"],
            ["Line style", "broken / beaded ('dashed look'); segment length cannot be read from the photos [MISSING swatch]"],
            ["Grain", "straight grain: lines parallel / square to the warp; no bias, no skew"],
            ["Scale", "identical front + back, every size (the repeat is not graded)"],
            ["Placement", "allover; centre a line on CF, CB and on the pocket centres (T4)"],
            ["Method", "OPEN — woven yarn-dyed vs printed (Q1)"]]
    tb, yy = table(cx, y0 + 5, [("", 20, None), ("", 89, 54)], rows, 1.75, 4.0, head=False); o.append(tb)
    # D: working
    dy = 132
    o.append(t(12, dy, "D · HOW THE REPEAT WAS ESTIMATED (working)", 2.2, 700)); dy += 4.5
    pf, pb = PR["pitch_px"]["front"], PR["pitch_px"]["back"]
    for ln in [f"1. Square pitch in the photos (FFT of the brightness profile over flat leg areas, 3 areas per photo): front {', '.join(f'{v:g}' for v in pf)} px; back {', '.join(f'{v:g}' for v in pb)} px  →  mean {PR['pitch_px_mean']:g} px (range {PR['pitch_px_range'][0]:g}–{PR['pitch_px_range'][1]:g}; drape skews single areas).",
               f"2. Garment width at the hip line (flat, row {dmprint.HIP_Y} px): front {PR['hip_px']['front']} px, back {PR['hip_px']['back']} px  →  {PR['squares_across_half_hip']:g} squares across the half hip.",
               "3. The reference garment's real size is unknown and its waist is elastic (no usable waistband width), so the scale is taken from assumed half-hip widths:"]:
        for k, l2 in enumerate(wrap(ln, 175)): o.append(t(14, dy, l2, 1.7, 400, INK)); dy += 2.9
        dy += 0.6
    rows = [[s_["anchor"], f"{s_['half_hip_cm']:g} cm", f"{s_['px_per_cm']:g} px/cm", f"{s_['square_cm'] * 10:.1f} mm", f"{s_['implied_length_cm']:g} cm"] for s_ in PR["scenarios"]]
    tb, dy = table(18, dy + 1, [("Assumed reference size", 70, None), ("half hip", 22, None), ("scale", 22, None), ("square", 20, None), ("implied outseam", 30, None)], rows, 1.7, 3.6); o.append(tb)
    for ln in [f"4. Range {PR['square_cm_range'][0] * 10:.1f}–{PR['square_cm_range'][1] * 10:.1f} mm; the implied outseam favours the low end (a ~100 cm full-length wide leg). Proposed: {SQ * 10:g} mm = 1/2 in, a standard mill check repeat inside the range.  {ESTIMATE}",
               "   Note: the ChatGPT mockup prompt says 'roughly 1.5–2 cm squares' — the photos measure smaller (≈ 45 squares across the half hip). Pick on a swatch (Q5)."]:
        o.append(t(14, dy + 1.5, ln, 1.7, 600, AMBER)); dy += 3.0
    return o


# ---------------------------------------------------------------- T3 POM
HI = {  # Hidden Inventory published chart, inches (PLM pipeline.size_charts 9a469aee-d93c-4ec1-9aca-8614b5980b52, read 27 Oct 2026)
    "26": (27.1, 37, 10.6, 27, 19.7), "28": (29.1, 39, 11, 28, 20.1), "30": (31.1, 41, 11.4, 29, 20.5), "32": (33.1, 43, 11.8, 30, 20.9),
    "34": (35, 44.9, 12.2, 30, 21.3), "36": (37, 46.9, 12.6, 31, 21.7), "38": (39, 48.8, 13, 31, 22), "40": (41, 50.8, 13.4, 31, 22.4)}
assert list(HI) == SIZES
POM = [("A", "Relaxed waist", "circumference at the top edge of the waistband", 0, "±0.5"),
       ("B", "Hip", "circumference 9 in down from the top of the waistband", 1, "±0.5"),
       ("C", "Front rise", "bottom of the waistband to the crotch seam", 2, "±0.25"),
       ("D", "Inseam", "crotch seam to hem", 3, "±0.5"),
       ("E", "Leg opening", "circumference of the hem", 4, "±0.25"),
       ("F", "Back rise", "bottom of the waistband to the crotch seam, back", None, "—"),
       ("G", "Thigh", "circumference 1 in below the crotch", None, "—"),
       ("H", "Knee", "circumference at knee height", None, "—"),
       ("I", "Outseam", "top of the waistband to the hem, side", None, "—"),
       ("J", "Waistband height", "finished, at CB (carries the 2 cm back label)", None, "—")]
def T3():
    o = hdr("T3 · POM / SIZE CHART — finished garment, inches (cm)", "Source: Hidden Inventory pants size chart (PLM pipeline.size_charts 9a469aee-d93c-4ec1-9aca-8614b5980b52, published on Shopify) — the same chart Konpeito T3 uses. Founder: 'the hidden inventory fit'.", "T3")
    x0, y = 12, 36; SC = 19.5
    cols = [("", 7), ("POM", 26), ("How to measure", 52)] + [(s, SC) for s in SIZES] + [("Tol. in", 13)]
    xx = x0
    for c, w in cols: o.append(t(xx, y, c, 2.1, 700, MUTED)); xx += w
    y += 2; o.append(f'<line x1="{x0}" y1="{y}" x2="{SW-12}" y2="{y}" stroke="{INK}" stroke-width="0.3"/>'); y += 5
    for code, name, how, idx, tol in POM:
        xx = x0
        o.append(t(xx, y, code, 2.2, 700)); xx += 7
        o.append(t(xx, y, name, 2.1, 700)); xx += 26
        for k_, ln in enumerate(wrap(how, 34)[:2]): o.append(t(xx, y - 0.6 + k_ * 2.6, ln, 1.6, 400, MUTED))
        xx += 52
        for s in SIZES:
            if idx is None:
                o.append(f'<rect x="{f(xx - 0.5)}" y="{f(y - 3.4)}" width="{SC - 1.5}" height="6.6" fill="{FAC_BG}" stroke="{FAC}" stroke-width="0.25"/>')
                o.append(t(xx + SC / 2 - 1.2, y - 0.6, "factory", 1.5, 700, FAC, "middle")); o.append(t(xx + SC / 2 - 1.2, y + 2.0, "HI spec", 1.5, 700, FAC, "middle"))
            else:
                v = HI[s][idx]
                o.append(t(xx + SC / 2 - 1, y - 0.4, f"{v:g}", 2.2, 600, INK, "middle"))
                o.append(t(xx + SC / 2 - 1, y + 2.6, f"({v * 2.54:.1f})", 1.5, 400, MUTED, "middle"))
            xx += SC
        o.append(t(xx + 1, y, tol if idx is not None else "—", 1.9, 400, AMBER if idx is not None else MUTED))
        y += 8.6
        o.append(f'<line x1="{x0}" y1="{f(y - 5.3)}" x2="{SW-12}" y2="{f(y - 5.3)}" stroke="#DDDDDD" stroke-width="0.2"/>')
    y += 1
    o.append(t(12, y, f"Size run {' '.join(SIZES)} = the HI published sizes (as Konpeito Rev A). Konpeito later added 29 / 31 / 33 — not added here  {PROPOSED}", 1.8, 600, AMBER)); y += 3.8
    o.append(t(12, y, f"Sample size: 32  {PROPOSED}.   Tolerances: as Konpeito (house standard)  {PROPOSED}.", 1.8, 600, AMBER)); y += 3
    o.append(facbox(12, y, 150, 17, ["Blue cells (back rise, thigh, knee, outseam, waistband height): from the factory's HI pants spec/pattern —",
                                      "same block, cargo pockets removed. Fill in and return with the fit sample.",
                                      "The HI factory tech pack (CAMOPANTS1) has no measurement chart: HI was fitted to a reference garment."], 1.75, "FACTORY TO SUPPLY — measurements"))
    gx = 168; o.append(t(gx, y + 4, "Grading (from the chart, per 2 in waist step)", 2.2, 700)); gy = y + 8.5
    for code, name, how, idx, tol in POM[:5]:
        steps = sorted({round(HI[b][idx] - HI[a][idx], 2) for a, b in zip(SIZES[:-1], SIZES[1:])})
        o.append(t(gx, gy, f"{code} {name}: +{' / +'.join(f'{s:g}' for s in steps)} in", 1.85)); gy += 3.4
    o.append(t(12, SH - 11, "Fabric is NOT the HI denim yet (Q1): if the shell changes (lighter twill / yarn-dyed check), the factory must shrink-test the bulk fabric and re-apply shrinkage to the HI pattern before cutting.", 1.75, 600, AMBER))
    return o


# ---------------------------------------------------------------- T4 pattern + check matching
def T4():
    o = hdr("T4 · PATTERN — factory's Hidden Inventory pants pattern + check matching", "We do not draft a pattern: the factory already holds the HI pants pattern. Same fit, same waistband; cargo pockets and knee seams left off (as Konpeito). Check matching rules are new for this product.", "T4")
    y = 36
    for s_, b in [("Base pattern", "The factory's Hidden Inventory pants pattern, all sizes as graded for HI (T3). Same fit: waist, hip, rise, thigh, knee, leg opening, lengths."),
                  ("Leave off", "Cargo pockets (bags, box pleats, flaps, snaps), HI flag labels, hammer loop, knee / panel seams: ONE panel per leg, waist to hem (as Konpeito)."),
                  ("Waistband", "As HI (founder): regular waistband, 2 pieces joined at CB, interlined as HI, buttonhole + 28 L shank button at CF."),
                  ("Back", "NO back yoke (as HI); 2 HI pointed back patch pockets centred on each leg (founder: 'same shape as hidden inventory')."),
                  ("Front", "HI scoop pockets + coin pocket + zip fly  [proposed — confirm] (the references show an elastic waist; Q2)."),
                  ("Belt loops", "HI positions, except the CB loop: replaced by 2 loops either side of the outside back label  [proposed — confirm] (Q3)."),
                  ("Shrinkage", "Shrink-test the bulk check fabric with the chosen finish (T6), add it to the pattern before the first sample.")]:
        o.append(t(14, y, s_, 2.15, 700)); o.append(t(46, y, b, 1.95, 400, AMBER if amberish(b) else INK)); y += 5.3
    y += 2
    o.append(t(14, y, f"CHECK MATCHING (repeat {SQ * 10:g} mm, P1)  {PROPOSED}", 2.5, 700, AMBER)); y += 5
    rows = [["CF", "Centre a vertical line on CF of each front; the check lines up across the fly when closed (left over right)."],
            ["CB seat seam", "Match the horizontal lines across the CB seam at the hip line; chevron below the seat curve is acceptable."],
            ["Side seams", "Match the horizontal lines front-to-back at the hip line (9 in below the WB top), where the seam is straight grain; let them run off below."],
            ["Inseam", "Match horizontal lines at the crotch point where possible."],
            ["Waistband", "Cut on straight grain, a horizontal line centred on the WB height; vertical lines match the body at CF and CB."],
            ["Back pockets", "Cut matched: pocket lines continue the back-leg lines (pocket 'disappears'). Alternative: cut on 45° bias as a deliberate contrast."],
            ["Coin pocket", "Matched to the facing, same as the back pockets."],
            ["Belt loops", "Cut on straight grain with a line centred along the loop."],
            ["Cutting", "Single-ply or pinned-ply cutting with the check aligned ply to ply; allow +5–10 % fabric for matching (factory to quote)."]]
    tb, y = table(14, y, [("Where", 30, None), ("Rule", 240, 150)], rows, 1.85, 4.3, head=False); o.append(tb)
    y += 2
    o.append(t(14, y, "Pattern pieces per garment — check against the HI pattern  " + PROPOSED, 2.3, 700, AMBER)); y += 5
    rows = [["Front leg L / R", "2", "shell", "one piece waist to hem; CF line centred"], ["Back leg L / R", "2", "shell", "one piece, no yoke"],
            ["Waistband", "2", "shell + interlining as HI", "joined at CB; back label on the outside at CB"], ["Fly / fly shield", "2", "shell", "YKK #4.5 zip 6 in"],
            ["Front facing L / R + coin pocket", "3", "shell", "coin pocket on the wearer's right facing"], ["Front pocket bag", "2", "pocketing (T5)", ""],
            ["Back patch pocket L / R", "2", "shell", "HI pointed shape, matched"], ["Belt loop", "6", "shell", "2 front, 2 side-back, 2 by the label  [proposed — confirm]"]]
    tb, y = table(14, y, [("Piece", 52, None), ("Qty", 10, None), ("Material", 44, None), ("Note", 130, None)], rows, 1.8, 3.7); o.append(tb)
    return o


# ---------------------------------------------------------------- T5 BOM
def T5():
    o = hdr("T5 · BILL OF MATERIALS", "Per garment. Threads, hardware and label types = the Hidden Inventory pants BOM (factory tech pack CAMOPANTS1 p. 8–9), metal in matte black as Konpeito. The shell fabric is OPEN (Q1): both options shown.", "T5")
    sz = " ".join(SIZES)
    rows = [
        ["Shell — option A", f"YARN-DYED woven windowpane check, black ground / tan line, {SQ * 10:g} mm repeat (P1); 100 % cotton twill, 10–12 oz bottom weight  [proposed — confirm]", "black / tan (P1)", "—", "whole garment"],
        ["Shell — option B", "PRINTED check on black: HI 12 oz RHT 3x1 denim (100 % cotton) or a 9–10 oz cotton twill; discharge / pigment print, tan lines (P1)  [proposed — confirm]", "black / tan (P1)", "—", "whole garment"],
        ["Pocket bag", "40's twill, 160 GSM, 100 % cotton (as HI)", "DTM black", "—", "front pocket bags"],
        ["Interlining", "Waistband interlining as the HI production waistband (HI BOM lists none)  [proposed — confirm]", "black", "—", "waistband"],
        ["Thread — topstitch", "All-purpose polyester Tex 135 / TKT 20 (as HI)", "DTM black", "—", "all visible topstitch"],
        ["Thread — overlock", "All-purpose polyester Tex 60 / TKT 50 (as HI)", "DTM black", "—", "overlock, construction"],
        ["Thread — buttonhole", "All-purpose polyester Tex 60 / TKT 50 (as HI)", "DTM black", "—", "waistband buttonhole"],
        ["Thread — back label", "Polyester Tex 60 / TKT 50, edge stitch all 4 sides  [proposed — confirm]", "white (DTM label)", "—", "outside back label"],
        ["Shank button", "Flat tack button with shank, 28 Line, brass / zinc alloy (as HI)", "matte black", "1", "waistband CF (B1)"],
        ["Zip", "YKK #4.5 metal, close-end, automatic lock slider, 6 in (as HI)", "matte black + DTM tape", "1", "CF fly (Z1)"],
        ["Rivets", "Inverted nipple rivet 15 L (9.5 mm) (as HI: 5 = scoop + coin pocket corners)  [proposed — confirm]", "matte black", "4", "2 scoop + 2 coin-pocket corners"],
        ["Bartacks", "Back-pocket top corners (horizontal, as HI), belt loops, fly bottom", "DTM black", "—", ""],
        ["Back label", "HAKI STANDARD main label 6.5 × 2 cm, white, black logo (T7b, labels/); OUTSIDE at CB of the waistband  [proposed — confirm]", "white / black", "1", "outside back WB, CB"],
        ["Size label", f"Damask woven CENTREFOLD 30 × 10 mm (as HI / Konpeito), waist number; sizes {sz}", "jet black / optic white", "1", "inside CB"],
        ["Care label", "HAKI STANDARD care label BY FIBRE — fibre not chosen yet [MISSING]: 100 % cotton → the 100-cotton label; any blend → ask Haki", "white / black", "1", "waist seam, wearer's right, 5 cm from side"],
        ["Hangtag + string", "Hangtag artwork to follow [MISSING]; string through the size-label loop (as HI)", "", "1", "on the size label"],
        ["Barcode / packing", "Barcode per size (HK code from PLM) + packing design to follow [MISSING]; until then as HI: polybag 43 × 31 cm + sticker", "", "1", "polybag"]]
    tb, y = table(12, 35, [("Item", 30, None), ("Description", 150, 98), ("Colour", 34, None), ("Pcs", 8, None), ("Where", 52, 34)], rows, 1.7, 4.6)
    o.append(tb)
    o.append(t(12, y + 1.5, "Note: all items to be OEKO-TEX certified (as HI).  No embroidery on this product.", 2.0, 700))
    return o


# ---------------------------------------------------------------- T6 construction
def T6():
    o = hdr("T6 · CONSTRUCTION, STITCHING + FINISH", "Sew it the way the factory sews the Hidden Inventory pants (same fit, waistband, threads + hardware), without the cargo pockets and knee seams. Plain words; amber = proposed.", "T6")
    rows = [["Threads", "Black DTM everywhere (tone-on-tone on the check): topstitch Tex 135 / TKT 20; overlock + buttonhole Tex 60 / TKT 50 (as HI)."],
            ["Cutting", f"Check matched per T4 (CF, CB, side seams at hip, waistband, pockets). Repeat {SQ * 10:g} mm (P1)."],
            ["Legs", "Front and back legs ONE piece each from waist to hem. No knee seam."],
            ["Back", "NO back yoke (as HI). Back panels joined by the CB (seat) seam: 2 rows of topstitch, as HI."],
            ["Side + inside leg", "Outseam and inseam sewn and finished as on the HI pants (same seam type + topstitch)."],
            ["Waistband", "As HI: regular waistband, 2 pieces joined at CB, 2 rows of topstitch, interlined; buttonhole + 28 L shank button at CF."],
            ["Back label", "Haki standard main label on the OUTSIDE of the waistband, centred on CB and on the WB height; edge-stitched on all 4 sides; sew it on BEFORE the waistband is closed so the stitches are caught inside  [proposed — confirm]."],
            ["Front pockets", "HI scoop pockets: turned edge with topstitch; 15 L rivet at each pocket's top corner  [proposed — confirm]."],
            ["Coin pocket", "HI coin pocket on the wearer's right facing, check matched; 15 L rivets at its 2 top corners  [proposed — confirm]."],
            ["Back pockets", "2 HI pointed back patch pockets, centred on each back leg, check matched; top edge hemmed + topstitched; 2 rows of topstitch; horizontal bartacks at both top corners (as HI, no rivets)."],
            ["Fly", "Zip fly, YKK #4.5 close-end 6 in, automatic lock slider; J topstitch on the front, bartack at the bottom (as HI)."],
            ["Belt loops", "6 loops bartacked top + bottom: 2 front 1 cm from the pocket (as HI), 2 side-back (as HI), 2 either side of the back label, ≈ 15 mm clear of its ends  [proposed — confirm]."],
            ["Hem", "Turned twice and topstitched, as HI."],
            ["Inside labels", "Size label (centrefold) inside CB in the waist seam; care label in the waist seam, wearer's right, 5 cm in from the side seam (T7)."],
            ["Not on Dismantle", "Cargo pockets, snap buttons, HI flag labels, hammer loop, knee seams, embroidery."]]
    tb, y = table(12, 36, [("Operation", 30, None), ("How (plain words)", 160, 100)], rows, 1.8, 4.6); o.append(tb)
    wx = 208; wy = 36
    o.append(t(wx, wy, "Wash / finish", 2.6, 700)); wy += 5
    for s_ in ["HI is RHT 3x1 denim with an ENZYME + STONE", "wash. That wash does NOT carry over here:",
               "", "• Option A (yarn-dyed cotton twill check):", "  garment rinse + softener + tumble dry only;", "  no stones, no enzyme (they would grey the",
               "  black ground and fuzz the tan lines).", "", "• Option B (printed on denim / twill):", "  rinse wash only to set + soften the print;",
               "  stone / enzyme wash only if a worn look is", "  wanted — sample a panel first.", "",
               "[proposed — confirm] (depends on Q1)", "", "Colour fastness: black ground must not stain", "the tan lines in the wash (crocking + wash", "test on the first yardage)."]:
        o.append(t(wx, wy, s_, 1.85, 700 if s_.startswith("[") else 400, AMBER if (s_.startswith("[") or s_.startswith("•") or s_.startswith("  ")) else INK)); wy += 3.6
    return o


# ---------------------------------------------------------------- T7 labels placement
def back_wb_detail(X, Y, s=0.6):
    """outside back waistband at CB, local mm drawn at scale s: back label 65 x 20 sewn all 4 sides, 2 loops either side."""
    ts = lambda v: v / s
    o = [FL.check_defs("chkd")]
    W = 180; wb = 40.0
    o.append(f'<rect x="0" y="0" width="{W}" height="{wb}" fill="url(#chkd)" stroke="{INK}" stroke-width="0.6"/>')
    o.append(f'<rect x="0" y="{wb}" width="{W}" height="22" fill="url(#chkd)" stroke="{INK}" stroke-width="0.4" opacity="0.85"/>')
    o.append(f'<line x1="{W/2}" y1="-4" x2="{W/2}" y2="{wb + 22}" stroke="{GUIDE}" stroke-width="0.5" stroke-dasharray="2 1.2"/>')
    o.append(t(W / 2, -5.5, "CB", ts(1.9), 700, GUIDE, "middle"))
    mw, mh = LB.MAIN_MM; mx, my = W / 2 - mw / 2, (wb - mh) / 2
    tag, _ = img(MAIN_PNG, mx, my, w=mw, h=mh); o.append(tag)
    o.append(f'<rect x="{f(mx)}" y="{f(my)}" width="{f(mw)}" height="{f(mh)}" fill="none" stroke="{INK}" stroke-width="0.4"/>')
    o.append(f'<rect x="{f(mx + 1.2)}" y="{f(my + 1.2)}" width="{f(mw - 2.4)}" height="{f(mh - 2.4)}" fill="none" stroke="#C0392B" stroke-width="0.4" stroke-dasharray="1.4 1"/>')
    for lx in (mx - 15 - 14, mx + mw + 15):       # loops 14 wide, 15 mm clear of the label ends (proposed)
        o.append(f'<rect x="{f(lx)}" y="-3" width="14" height="{wb + 8}" fill="url(#chkd)" stroke="{INK}" stroke-width="0.5"/>')
        for yy in (0, wb + 2): o.append(f'<line x1="{f(lx + 2)}" y1="{f(yy)}" x2="{f(lx + 12)}" y2="{f(yy)}" stroke="#DDD" stroke-width="1.6"/>')
    o.append(dim_h(mx, mx + mw, wb + 27, "65 mm", ts(1.6)))
    o.append(dim_v(my, my + mh, mx + mw + 4, "20", ts(1.5), side=1))
    o.append(dim_h(mx + mw, mx + mw + 15, -6, "15", ts(1.5), col=AMBER))
    o.append(t(0, wb + 30, "waist seam", ts(1.6), 500, MUTED))
    return f'<g transform="translate({f(X)} {f(Y)}) scale({f(s)})">' + "\n".join(o) + "</g>"

def T7():
    o = hdr("T7 · LABELS + TRIMS PLACEMENT", "Founder: 'add a back label on the waist band'. Proposed: the Haki standard main label on the OUTSIDE at CB. Size + care labels inside as Konpeito / HI (factory tech pack p. 9–10). Artwork T7b.", "T7")
    s = 0.085
    bx = 14 - BB[0] * s; fx = 84 - FB[0] * s
    o.append(flat_group("back", bx, 32, s)); o.append(flat_group("front", fx, 32, s))
    o.append(t(18, 32 + FLAT_H * s + 4, "BACK", 2.1, 700)); o.append(t(88, 32 + FLAT_H * s + 4, "FRONT", 2.1, 700))
    lx, ly, lw, lh = FL.back_label_rect()
    callout(o, bx + (lx + lw / 2) * s, 32 + ly * s, "L1", 0, -8)
    # care label (inside) on the front flat, wearer's right = image left
    cw, ch = LB.CARE_MM
    cx0 = fx + ((886 - 760) * MMPX + 50 - cw / 2) * s
    o.append(f'<rect x="{f(cx0)}" y="{f(32 + 95 * MMPX * s)}" width="{f(cw * s)}" height="{f(ch * s)}" fill="none" stroke="#FFFFFF" stroke-width="0.4" stroke-dasharray="1 0.6"/>')
    callout(o, cx0, 32 + (95 * MMPX + 30) * s, "L3", -9, 6)
    o.append(t(14, 145, "DETAIL — outside back waistband at CB (0.6 : 1)  " + PROPOSED, 2.1, 700, AMBER))
    o.append(back_wb_detail(22, 156, 0.6))
    rows = [["L1 Back label", "Haki standard main label, woven, flat", "OUTSIDE back waistband, centred on CB and on the WB height, 6.5 × 2 cm, white; edge-stitched on ALL 4 SIDES (red dashed = stitch line, 1.2 mm in). Nothing hangs from it.", "outside vs inside + label type: [proposed — confirm] (Q3)"],
            ["L2 Size label", "damask woven, centrefold (as HI)", f"inside CB in the waist seam (moves to CB: no main label inside); 30 × 10 mm folded; waist numbers {' '.join(SIZES)}; the hang-tag string ties through its loop", "artwork T7b + labels/"],
            ["L3 Care label", "printed satin", "wearer's right, in the waist seam, 5 cm in from the side seam (as HI); 3 × 6.5 cm; top 0.5 cm into the seam", "artwork: by fibre — fibre not chosen [MISSING]"],
            ["Hang tag", "", "hangs from the SIZE label, never from the back label", "artwork to follow [MISSING]"],
            ["Belt loops", "6", "2 front (as HI), 2 side-back (as HI), 2 flanking the back label ≈ 15 mm clear of its ends (replace the HI CB loop)", "[proposed — confirm] (Q3)"],
            ["Hardware", "matte black", "28 L shank button CF; YKK #4.5 6 in zip; 15 L rivets at the scoop + coin-pocket corners; back pockets bartacked, no rivets", ""]]
    yy = 36
    for r in rows:
        o.append(t(160, yy, r[0], 2.0, 700)); o.append(t(186, yy, r[1], 1.75, 400, MUTED))
        lines = wrap(r[2], 74)
        for k, ln in enumerate(lines): o.append(t(160, yy + 3.4 + k * 2.9, ln, 1.75, 400, INK))
        nl = len(lines)
        if r[3]: o.append(t(160, yy + 3.4 + nl * 2.9, r[3], 1.75, 600, AMBER if amberish(r[3]) else GREEN)); nl += 1
        yy += 4.5 + nl * 2.9 + 1.4
    o.append(t(160, yy + 1, "Alternative to L1 if the team prefers: main label inside CB as on every other", 1.7, 600, MUTED))
    o.append(t(160, yy + 4, "Haki product, plus a separate outside back patch (leather / jacron / woven) — Q3.", 1.7, 600, MUTED))
    return o


# ---------------------------------------------------------------- T7b label artwork
def T7b():
    o = hdr("T7b · LABEL ARTWORK — back label, size label, care label", "Back label = the Haki standard main label (engine/labels.py, founder 22 Oct: one main label for every product). Size label = HI centrefold with our waist sizes. Care label = by fibre: fabric not chosen, so it cannot be picked yet.", "T7b")
    yb = 34; wc = 88; h1 = 98; dm = 'stroke="#7A1F2B" stroke-width="0.2"'
    for i in range(3): o.append(f'<rect x="{f(12 + i * (wc + 4))}" y="{yb}" width="{wc}" height="{h1}" fill="#FFFFFF" stroke="#222" stroke-width="0.3"/>')
    # 1 main / back label
    cx = 12 + wc / 2; mw, mh = LB.MAIN_MM
    o.append(t(cx, yb + 7, "Back label (= Haki main label)", 2.7, 400, INK, "middle"))
    o.append(t(cx, yb + 10.5, "HAKI STANDARD — every product", 1.8, 700, GREEN, "middle"))
    lx, ly = cx - mw / 2, yb + 24
    tag, _ = img(MAIN_PNG, lx, ly, w=mw, h=mh); o.append(tag)
    o.append(f'<rect x="{f(lx)}" y="{f(ly)}" width="{f(mw)}" height="{f(mh)}" fill="none" stroke="#555" stroke-width="0.25"/>')
    o.append(f'<line x1="{f(lx)}" y1="{f(ly - 2.2)}" x2="{f(lx + mw)}" y2="{f(ly - 2.2)}" {dm}/>'); o.append(t(cx, ly - 3.2, "6.5 cm", 1.6, 400, INK, "middle"))
    o.append(f'<line x1="{f(lx - 2)}" y1="{f(ly)}" x2="{f(lx - 2)}" y2="{f(ly + mh)}" {dm}/>'); o.append(t(lx - 3, ly + mh / 2 + 0.6, "2 cm", 1.6, 400, INK, "end"))
    o.append(t(cx, ly + mh + 4, "drawn 1 : 1 — file labels/main-label-6.5x2cm-white.pdf", 1.6, 400, MUTED, "middle"))
    for i, ln in enumerate(["White ground, black HAKI STUDIOS logo + mark.", "Flat; edge-stitched on all 4 sides.",
                            "Placed OUTSIDE at CB of the back waistband", "[proposed — confirm] (Q3)", "Weave (damask, as HI) [proposed — confirm]"]):
        o.append(t(cx, ly + mh + 11 + i * 3.4, ln, 1.7, 600 if "proposed" in ln else 400, AMBER if "proposed" in ln else INK, "middle"))
    o.append(t(cx, yb + h1 - 4, "Type: Woven label. Flat", 2.0, 400, INK, "middle"))
    # 2 size label
    xs = 12 + wc + 4; cxm = xs + wc / 2
    o.append(t(cxm, yb + 7, "Size Label", 2.7, 400, INK, "middle"))
    o.append(t(cxm, yb + 10.5, "HI centrefold — Haki waist sizes", 1.8, 700, GREEN, "middle"))
    s1 = 1.6; lx = cxm - KL.W * s1 / 2; ly = yb + 18
    st, _ = KL.label("32", lx, ly, s1); o += st
    o.append(t(cxm, ly + KL.H * s1 + 4, "1.6 : 1 (size 32). Flat 30 × 10 mm, 5 mm seam", 1.6, 400, MUTED, "middle"))
    o.append(t(cxm, ly + KL.H * s1 + 7, "allowance each end (dashed), fold at 15 mm", 1.6, 400, MUTED, "middle"))
    gy = yb + 52
    for i, sz in enumerate(SIZES):
        r_, c_ = divmod(i, 2)
        st, _ = KL.label(sz, xs + 10 + c_ * 38, gy + r_ * 9.5, 1.0); o += st
    o.append(t(cxm, yb + h1 - 4, "Type: Damask woven label. Centerfold", 2.0, 400, INK, "middle"))
    # 3 care label
    xc = 12 + 2 * (wc + 4); cxc = xc + wc / 2
    o.append(t(cxc, yb + 7, "Care Label", 2.7, 400, INK, "middle"))
    o.append(t(cxc, yb + 10.5, "HAKI STANDARD — by fibre", 1.8, 700, GREEN, "middle"))
    o.append(missing(xc + 5, yb + 16, wc - 10, 52, ["[MISSING] fibre not chosen (Q1)",
                                                      "The care label is picked from the shell",
                                                      "composition (engine/labels.py):",
                                                      "• 100 % cotton (option A twill, or HI",
                                                      "  denim) → haki-studios-care-label-",
                                                      "  100-cotton-white.pdf",
                                                      "• 90 % cotton / 10 % polyester → the",
                                                      "  90-cotton-10-polyester label",
                                                      "• anything else → no standard label:",
                                                      "  ask Haki. Never pick the nearest."], 1.75))
    o.append(t(cxc, yb + 74, "3 × 6.5 cm, printed satin, front + back;", 1.7, 400, INK, "middle"))
    o.append(t(cxc, yb + 77.4, "wearer's right in the waist seam, 5 cm", 1.7, 400, INK, "middle"))
    o.append(t(cxc, yb + 80.8, "in from the side seam (as HI).", 1.7, 400, INK, "middle"))
    o.append(t(cxc, yb + h1 - 4, "Type: Printed satin ribbon", 2.0, 400, INK, "middle"))
    yr = yb + h1 + 8
    o.append(t(12, yr, "B · SIZE LABELS 1 : 1 (flat, before folding) — files labels/HAKI_DM_size-label_<size>.svg / .pdf, text outlined (Neue Metana ExtraBold, optic white on jet black)", 2.0, 700))
    for i, sz in enumerate(SIZES):
        st, _ = KL.label(sz, 12 + i * (KL.W + 4), yr + 4); o += st
    yy = yr + 22
    for a, b in [("Not reused", "No HI or other product's label art: back label = Haki standard file; size labels generated for this style (HAKI_DM_*)."),
                 ("Number height", f"{KL.CAP:g} mm  [proposed — confirm] (as Konpeito)."),
                 ("Certification", "all items to be OEKO-TEX certified (as HI).")]:
        o.append(t(12, yy, a, 1.9, 700)); o.append(t(38, yy, b, 1.8, 600 if amberish(b) else 400, AMBER if amberish(b) else INK)); yy += 3.8
    return o


# ---------------------------------------------------------------- Q1 open questions
QUESTIONS = [
    ("Q1", "Fabric: woven yarn-dyed check or a printed check? Which base + weight?",
     "A: yarn-dyed cotton twill check, 10–12 oz (shown first on T5)", "A yarn-dyed woven (gives the beaded line of the refs, lines stay straight, no print cracking) vs B printed on HI 12 oz denim or 9–10 oz twill (cheaper MOQ, line may sit off-grain). Decides the care label, wash, shrinkage + cost.", "Founder / Nick"),
    ("Q2", "Front: HI scoop pockets + coin pocket + zip fly + button?",
     "Yes, as HI (the refs have an elastic waist we ignore)", "Founder named the HI waistband; the refs' front is elastic-only with side-seam pockets. Alternative: HI waistband but slant side pockets, no coin pocket.", "Founder"),
    ("Q3", "Back label: what, and where?",
     "Haki standard main label 6.5 × 2 cm white, OUTSIDE at CB, sewn all 4 sides; HI CB loop replaced by 2 loops flanking it", "Alternatives: inside CB (as every Haki product) + a separate outside patch (leather / jacron / woven, own art = new artwork owed); black-ground label to sit quieter on the check.", "Founder"),
    ("Q4", "Colourway", "Black ground + tan line only (as the refs)", "Any second colourway for the sample round?", "Founder"),
    ("Q5", "Check repeat size", f"{SQ * 10:g} mm (1/2 in) square — estimated from the photos (P1)", "Photos measure 12–14 mm; the ChatGPT prompt said 15–20 mm. Bigger = bolder from a distance. Pick on a swatch / strike-off.", "Founder (swatch)"),
    ("Q6", "Sizes + sample size", f"HI published run {' '.join(SIZES)}; sample in 32", "Konpeito later added 29 / 31 / 33 — add them here too?", "Founder"),
    ("Q7", "Factory", "The factory that holds the HI pants pattern (as Konpeito)", "If a new factory: it needs the HI pattern / a reference garment, and T3 blue cells become our job.", "Product lead"),
    ("Q8", "Style code", f"{STYLE}", "Confirm against the PLM / Shopify SKU scheme.", "Ops"),
    ("Q9", "Back pockets: matched or bias?", "Matched to the back leg (pocket 'disappears')", "Bias-cut pockets are a common plaid detail and avoid a near-miss match.", "Founder"),
    ("Q10", "Wash / finish", "Rinse + soften only, no stone / enzyme", "HI's stone wash would grey the black and fuzz the lines; only if a worn look is wanted.", "Founder"),
    ("Q11", "Owed by Haki", "—", "Mockups front / back (ChatGPT render), hang tag art, barcode per size, packing design, care label (after Q1).", "Founder / design"),
]
def Q1():
    o = hdr("Q1 · OPEN QUESTIONS — for the internal review", "Everything the founder did not state. The pack is built on the 'assumed' column (amber in the pages); change any of these and the listed pages change.", "Q1")
    tb, y = table(12, 36, [("#", 10, None), ("Question", 62, 38), ("Assumed in this pack", 70, 44), ("Options / why it matters", 112, 72), ("Decides", 20, None)],
                  [[a, b, c + "  [proposed — confirm]" if c != "—" else c, d, e] for a, b, c, d, e in QUESTIONS], 1.75, 4.4)
    o.append(tb)
    return o


# ---------------------------------------------------------------- build
def build():
    PAGES.clear()
    import dmlabels
    labels = dmlabels.build()
    idx_plan = [("T1", "Cover / summary + contents", ""), ("T2", "Flats — front + back (+ mockup placeholders)", "mockups"),
                ("P1", "Print spec — black / tan windowpane check", ""), ("T3", "POM / size chart (HI, factory fills gaps)", ""),
                ("T4", "Pattern — factory HI pattern + check matching", ""), ("T5", "Bill of materials (fabric open)", "care label; hang tag; barcode; packing"),
                ("T6", "Construction, stitching + finish", ""), ("T7", "Labels + trims placement", "care label; hang tag"),
                ("T7b", "Label artwork — back, size, care label", "care label"), ("Q1", "Open questions", "")]
    add("T2", "Flats", T2()); add("P1", "Print", P1()); add("T3", "POM", T3()); add("T4", "Pattern", T4()); add("T5", "BOM", T5())
    add("T6", "Construction", T6()); add("T7", "Labels", T7()); add("T7b", "Label art", T7b()); add("Q1", "Questions", Q1())
    # cover flags must match the pages that carry a [MISSING] mark (as Konpeito)
    has = {pid for pid, _, svg in PAGES if "[MISSING" in svg}
    flagged = {pid for pid, _, m in idx_plan if m}
    assert has - {"P1", "Q1"} == flagged, f"[MISSING] on {sorted(has)} vs cover flags {sorted(flagged)}"
    PAGES.insert(0, ("T1", "Cover", page(T1(idx_plan))))
    pdfs = []
    for pid, title, svg in PAGES:
        p = f"{OUT}/{pid}.pdf"; cairosvg.svg2pdf(bytestring=svg.encode(), write_to=p); pdfs.append(p)
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{OUT}/prev_{pid}.png", output_width=2400)
    w = PdfWriter()
    for p in pdfs:
        for pg in PdfReader(p).pages: w.add_page(pg)
    w.add_metadata({"/Title": f"{NAME} — {REV} — INTERNAL", "/Author": "Haki Studios"})
    raw = f"out/raw_{REV.replace(' ', '')}.pdf"; w.write(raw)
    final = f"out/Dismantle Pants - {REV} - INTERNAL.pdf"
    subprocess.run([sys.executable, "../konpeito-jeans/shrink.py", raw, final, "2400", "85"], check=True)
    print("pages", len(pdfs), final, os.path.getsize(final) // 1024, "kB")
    return final, labels


def package(final, labels):
    pkg = "out/pkg"; shutil.rmtree(pkg, ignore_errors=True); os.makedirs(f"{pkg}/labels")
    for fn in labels + LB.files_for(CARE_FIBRE or ""):
        shutil.copy(fn, f"{pkg}/labels/")
    shutil.copy(final, pkg)
    readme = f"""HAKI — {NAME} ({STYLE}, proposed) — {REV}, {DATE} — INTERNAL sampling draft (not a factory send)

PDF: {os.path.basename(final)}
labels/
  main-label-6.5x2cm-white.pdf   Haki standard main label 65 x 20 mm, 1:1 = the BACK LABEL (outside at CB, proposed; T7, T7b)
  HAKI_DM_size-label_<size>.svg/.pdf   HI-style centrefold size labels 30 x 10 mm flat, 1:1, sizes {' '.join(SIZES)}
  (no care label: the shell fibre is not chosen yet [MISSING], LESSONS D7)
No embroidery, no stitch files. Pattern = the factory's Hidden Inventory pants pattern (T4).
"""
    open(f"{pkg}/README.txt", "w").write(readme)
    z = final.replace(".pdf", ".zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(pkg):
            for fn in files: zf.write(os.path.join(root, fn), os.path.relpath(os.path.join(root, fn), pkg))
    return z


if __name__ == "__main__":
    final, labels = build()
    z = package(final, labels)
    print("zip", z)
