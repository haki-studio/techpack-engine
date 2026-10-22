"""Rev D "RFQ / sample edition" — three PDFs from one build, a thin layer over the garment.py + pack.py page builders:
  HAKI_KOIB_FACTORY-SUMMARY_RevD.pdf  what the factory needs to make it right the first time (the factory-summary page kinds
                                      of the Konpeito factory copy, same names + order: KINDS)
  HAKI_KOIB_TECHPACK_RevD.pdf         full reference for the factory: the summary pages + pattern, stitch files, hooping, specs
  HAKI_KOIB_INTERNAL_RevD.pdf         our copy: finish.py's merged T + G pack (provenance, revision logs, internal questions) + TBD
Every page is a fc_shim.Page(id, kind, title, audience, svg) — fc_shim = temporary mirror of engine/factory_copy.py (Konpeito).
Factory copies are built with kbcore.MODE = "factory" (neutral wording; scrub_svg with rfqgate.RULES on every page) and
both pass summary_gate + leak_gate (red-then-green against the internal copy).
Also: out/TBD_RevD.md + .png, the factory files zip, and bench/dst_sha_RevD.json (sha256 of every DST/PES, to prove the stitch
files did not move). When engine/factory_copy.py lands: `import factory_copy as FC` instead of fc_shim, delete fc_shim.py.
usage: python3 rfq.py   (after run_all.sh)"""
import kbcore
import os, io, json, glob, hashlib, shutil, subprocess, textwrap
import cairosvg
from pypdf import PdfWriter, PdfReader
import garment as GM                    # T pages (zip-hoodie block builders fed with this design's pattern)
import pack as PK                       # G pages, F1
import sheet as SHT, specbase as SB
from sheet import t, doc, INK, MUTED, RED, GREEN, ORANGE, SW, SH
from render import f
import rfqgate
import fc_shim as FC
from fc_shim import Page, FACTORY, INTERNAL as INT
ZB, F, HF = GM.ZB, GM.F, GM.HF
PROP, ALT = ZB.PROP, ZB.ALT
REV, DATE, STYLE, NAME = kbcore.REV, kbcore.DATE, kbcore.STYLE, GM.NAME
R_ = REV.replace(" ", "")
OUT = "out"; PG = f"{OUT}/rfq_pages"; shutil.rmtree(PG, ignore_errors=True); os.makedirs(PG)
FAC_SUM = f"{OUT}/HAKI_{kbcore.SHORT}_FACTORY-SUMMARY_{R_}.pdf"
FAC_REF = f"{OUT}/HAKI_{kbcore.SHORT}_TECHPACK_{R_}.pdf"
INTERNAL = f"{OUT}/HAKI_{kbcore.SHORT}_INTERNAL_{R_}.pdf"            # finish.py writes it; rfq.py appends the TBD page
LADDER = [100, 200, 300, 500]          # brief: THEY quote at these quantities — never our price (skill request-a-supplier-quote)
SAMPLING = "Stitch files are for SAMPLING — the fish fill is under revision; the bulk files follow after the strike-off."

def H(title, sub, page): return SHT.header(title, sub, page)
def blank(o, x, y, w): o.append(f'<line x1="{x}" y1="{y + 0.6}" x2="{x + w}" y2="{y + 0.6}" stroke="{MUTED}" stroke-width="0.15"/>')
def para(o, x, y, s, n=110, size=1.75, col=INK, lh=3.1, w=400):
    for l in textwrap.wrap(s, n): o.append(t(x, y, l, size, w, col)); y += lh
    return y
def prop(s): return s + "  [proposed — confirm]"

# ---------------------------------------------------------------- C1 cover (factory)
def p_cover(index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>', t(14, 22, "HAKI STUDIOS", 3.0, 700, MUTED),
         t(SW - 14, 22, "REQUEST FOR QUOTATION · SAMPLE", 3.0, 700, INK, "end"), t(14, 34, NAME, 7.0, 700),
         t(14, 41.5, f"Style {STYLE} · {REV} · {DATE} · sizes XS–3XL · base size M · cm unless marked mm", 2.5, 400, MUTED),
         f'<line x1="14" y1="45" x2="{SW-14}" y2="45" stroke="{INK}" stroke-width="0.4"/>']
    for i, lab in enumerate(["Prepared for:", "Quantity (pcs):", "Reply by:"]):
        x = 14 + i * 64; o.append(t(x, 51, lab, 2.0, 700)); blank(o, x + (20 if i != 1 else 22), 51, 38)
    fo, h = GM.front_flat_with_art(14, 57, 86); o += fo; o.append(t(14, 57 + h + 4.5, "FRONT (size M, embroidery from the size-M stitch files)", 1.9, 700))
    Fl = GM.Flat("M"); b = HF.bounds(Fl, True); s = 82 / (b[2] - b[0])
    o.append(ZB.flat_g(HF.draw_back(Fl), b, 106, 57, s)); o.append(t(106, 57 + (b[3] - b[1]) * s + 4.5, prop("BACK + HOOD plain, no embroidery"), 1.9, 700, PROP))
    ix = 196; y = 56; o.append(t(ix, y, "COLOURWAY — WASHED NAVY", 2.4, 700)); y += 4
    for hx, a, b_ in [(kbcore.FABRIC, "Shell", prop("washed navy duck, 12 oz")), ("#EFE6D2", "Hood lining", prop("cream sherpa")),
                      ("#7A5A48", "Body lining", prop("plaid cotton flannel")), ("#B08A4A", "CF zip", prop("2-way, antique brass metal")),
                      ("#6F93C8", "Embroidery", "12 thread colours, blues + fish accents (G3)")]:
        o.append(f'<rect x="{ix}" y="{f(y - 2.4)}" width="4.5" height="3" fill="{hx}" stroke="#999" stroke-width="0.1"/>')
        o.append(t(ix + 6, y, a, 1.75, 700)); o.append(t(ix + 24, y, b_, 1.6, 400, PROP if "proposed" in b_ else INK)); y += 3.8
    y += 3; o.append(t(ix, y, "CONTENTS", 2.4, 700)); y += 4.2
    for name, pg in index: o.append(t(ix, y, name[:62], 1.6)); o.append(t(SW - 14, y, str(pg), 1.6, 600, MUTED, "end")); y += 3.2
    tot = sum(PK.CUR[p]["stitches"] for p in kbcore.PIECES)
    y += 2.5; o.append(t(ix, y, "AT A GLANCE (size M)", 2.2, 700)); y += 4
    for a, b_ in [("Pattern", "Haki jacket block body + sleeve, 3-panel hood (T2–T5, DXF)"), ("Embroidery", f"fronts + front half of sleeves, {tot:,} stitches"),
                  ("Hoopings", f"{PK.HOOPS} per jacket on {PK.FR_S} mm (proposed frame)"), ("Files", "DST + PES per size and piece; DXF per size; label artwork")]:
        o.append(t(ix, y, a, 1.6, 400, MUTED)); o.append(t(ix + 16, y, b_, 1.55, 600)); y += 3.3
    o.append(t(14, SH - 14, SAMPLING, 1.9, 700, ORANGE))
    o.append(t(14, SH - 10.5, "Amber = proposed — please confirm or propose your alternative. Measurements in cm, embroidery in mm.", 1.7, 400, MUTED))
    o.append(t(SW - 14, SH - 8, SHT.FOOT, 1.8, 400, MUTED, "end"))
    return o

# ---------------------------------------------------------------- Q1 request for quotation (closed, neutral — they name every price)
def p_q1():
    o = H("Q1 · REQUEST FOR QUOTATION — please quote and fill in", "Please name your prices; we have not set any. Open design points: Q2. Amber = proposed — confirm.", "Q1")
    y = 33; o.append(t(12, y, "PLEASE QUOTE — SAMPLES", 2.3, 700)); y += 4.6
    for x_, h_ in zip([12, 122, 152], ["Item", "Price (state currency)", "Lead time (days)"]): o.append(t(x_, y, h_, 1.6, 700, MUTED))
    items = [("1  Fit sample, size M, no embroidery", "full jacket from the pattern (T2–T6), to check hood, bands and zip before the embroidered sample"),
             ("2  Embroidery strike-off", "the size-M files listed on F1, sewn on the washed shell with the proposed threads and backing"),
             ("3  Embroidered sample, size M", "full jacket with embroidery, from our pattern + stitch files")]
    for i, (a, b_) in enumerate(items):
        y += 5.6; ZB_zebra(o, i, y, 7.6, 11, 186)
        o.append(t(12, y, a, 1.65, 700)); para(o, 14, y + 2.6, b_, 140, 1.35, MUTED, 2.3)
        blank(o, 122, y, 26); blank(o, 152, y, 30); y += 2.4
    y += 9; o.append(t(12, y, "BULK — price per piece, FOB origin port", 2.1, 700)); o.append(t(80, y, "[proposed — confirm the Incoterm]", 1.5, 600, PROP)); y += 4.4
    o.append(t(12, y, "Quantity (pcs), sizes XS–3XL", 1.55, 700, MUTED))
    for j, q in enumerate(LADDER): o.append(t(70 + j * 29, y, f"{q}", 1.7, 700))
    y += 5; o.append(t(12, y, "Price per piece", 1.55))
    for j in range(len(LADDER)): blank(o, 70 + j * 29, y, 24)
    y += 6
    for l in ["Freight quoted separately: air and sea, to Ohio, USA — please state whether duty is included.",
              "Please send a quotation sheet (unit price per quantity, spec, freight, total). Sampling and set-up charges listed separately from bulk."]:
        y = para(o, 12, y, l, 105, 1.55, INK, 2.9)
    tx = 192; ty = 33; o.append(t(tx, ty, "PLEASE TELL US", 2.3, 700)); ty += 4.6
    for q in ["MOQ per colourway (pcs)", "MOQ per order (pcs)", "Sample lead time (days)", "Bulk lead time (days)",
              "Embroidery: in-house or subcontracted?", "Max thread colours per head", "Largest embroidery frame (mm)",
              "Shell you propose: weight + wash", "Fibre % — shell", "Fibre % — body lining (flannel)", "Fibre % — sleeve lining (taffeta)",
              "Fibre % — hood lining (sherpa)", "Fibre % — pocketing", "Payment terms"]:
        o.append(t(tx, ty, q, 1.5)); blank(o, tx + 56, ty, 37); ty += 4.25
    y = max(y, ty) + 4
    o.append(t(12, y, "WHY WE ASK THE FIBRE", 1.9, 700)); y += 3.8
    y = para(o, 12, y, "The care label (T6b) is printed from the fibre content of the shell. It is not confirmed yet, so the care label is held: "
                       "please state the fibre % of the fabrics you propose, and we send the matching care label artwork.", 170, 1.55, INK, 2.9)
    y += 2; o.append(t(12, y, "ATTACHED", 1.9, 700)); y += 3.8
    for l in ["This pack (factory summary) + the full tech pack (reference) · pattern/: DXF per size + all sizes (AAMA, mm; layer 8 = embroidery positions,",
              "layer 13 = needle starts), 1:1 plot PDF size M · elements/: stitch files DST + PES per size and piece, thread charts, art SVG (true size) · labels/: label artwork"]:
        o.append(t(12, y, l, 1.45)); y += 3.0
    return o

def ZB_zebra(o, i, y, h, x0=11, x1=None):
    if i % 2 == 0: o.append(f'<rect x="{x0}" y="{f(y - 3.6)}" width="{(x1 or SW - 11) - x0}" height="{h}" fill="{ALT}"/>')

# ---------------------------------------------------------------- Q2 open design points + packing (kept amber until confirmed)
OPEN = [("Back + hood", "plain — no embroidery on the back, the hood or the back half of the sleeves."),
        ("Art clearances", f"art stops {F.KEEP_HEM:.0f} mm above the hem-band seam and the cuff seams, and {F.KEEP_CF:.0f} mm each side of the zip (nothing crosses the zip)."),
        ("Grading", "XS–S sew the art at 92 %, M–XL at 100 % (L + XL use the size-M art, re-placed on their pieces), XXL–3XL at 108 % (G5)."),
        ("Welt pockets", f"position + angle as drawn ({F.WELT_ANG:.0f}° from horizontal), opening 1.4 × 13 cm (T2, T7)."),
        ("Thread colours", "all 12 are targets from the design artwork — please match them on your physical thread card before the strike-off (G3, F1)."),
        ("Care label", "held until the fibre content is confirmed (Q1); the main label is final (T6b)."),
        ("Construction", "welt pockets, pocket bags, facings and body lining follow the pattern pieces (T4 + DXF). Tell us if you need a separate seam spec.")]
PACK = [("Fold", "your standard fold for a zip jacket, zip closed, hood folded in."), ("Polybag", "one per piece, with a suffocation warning."),
        ("Carton", "your standard — please state pieces per carton and carton size."), ("Hangtag + barcode", "artwork and numbers follow from Haki Studios.")]
def p_q2():
    o = H("Q2 · OPEN DESIGN POINTS + PACKING", "These are our proposals. Please confirm each, or tell us what you would change and why.", "Q2")
    y = 34; o.append(t(12, y, "OPEN DESIGN POINTS", 2.3, 700)); y += 5
    for i, (a, b_) in enumerate(OPEN, 1):
        ZB_zebra(o, i - 1, y + 0.4, 6.0, 11, SW - 11)
        o.append(t(12, y, f"{i}. {a}", 1.75, 700)); y = para(o, 52, y, prop(b_), 150, 1.65, PROP, 2.9); y += 3.1
    y += 4; o.append(t(12, y, "PACKING", 2.3, 700)); y += 5
    for a, b_ in PACK: o.append(t(12, y, a, 1.75, 700)); o.append(t(52, y, prop(b_), 1.65, 600, PROP)); y += 4.2
    y += 4; o.append(t(12, y, "SAMPLE PLAN", 2.3, 700)); y += 5
    for l in ["1. Fit sample, size M, no embroidery — hood, bands and zip checked (Q1 item 1).", "2. Embroidery strike-off on the washed shell (F1) — photos + measured size back to us.",
              "3. Embroidered sample, size M, after both are approved.", SAMPLING]:
        o.append(t(12, y, l, 1.7, 700 if l == SAMPLING else 400, ORANGE if l == SAMPLING else INK)); y += 3.6
    return o

# ---------------------------------------------------------------- summary-only pages (lead TASK 2026-10-22: one page per kind)
# The sample room works from these; the per-size tables, 5-page element specs and the long question pages stay in the
# full reference (TECHPACK), and each summary page names the TECHPACK pages behind it (TP = page ranges, set by render).
TP = {}
import espec, emb_place as EP
from sheet import swatch
from specbase import img_tag
from motifs2 import PAL, HEX
def tp(*ids):
    r = [TP[i] for i in ids if i in TP]
    if not r: return "TECHPACK"
    a, b = min(a for a, _ in r), max(b for _, b in r)
    return f"TECHPACK p. {a}" if a == b else f"TECHPACK p. {a}–{b}"
def cols(pieces): return [k for k in kbcore.KB_KEYS if any(k in PK.CUR[p]["colours"] for p in pieces)]
def thread_rows(o, x, y, keys, rh=3.5, size=1.55):
    """swatch, name, hex, nearest Isacord + Polyneon with ΔE2000 (green < 3, amber 3–5.5, red > 5.5); a note when two
    targets share one catalogue colour (pick from the physical card)"""
    de = lambda v: (GREEN if v < 3 else (ORANGE if v < 5.5 else RED))
    for x_, h_ in zip([x, x + 6, x + 28, x + 44, x + 58, x + 72, x + 86], ["", "Thread", "Hex", "Isacord", "ΔE", "Polyneon", "ΔE"]): o.append(t(x_, y, h_, 1.4, 700, MUTED))
    for i, k in enumerate(keys):
        yy = y + 4 + i * rh; iso, pn = SB.TH[k]["isacord"], SB.TH[k]["polyneon"]
        o.append(swatch(x, yy, k, 4.5, 2.6)); o.append(t(x + 6, yy, PAL[k][1], size, 600)); o.append(t(x + 28, yy, HEX[k], size - 0.1, 400, MUTED))
        o.append(t(x + 44, yy, f"{iso[0]}", size)); o.append(t(x + 58, yy, f"{iso[3]:.1f}", size - 0.1, 600, de(iso[3])))
        o.append(t(x + 72, yy, f"{pn[0]}", size)); o.append(t(x + 86, yy, f"{pn[3]:.1f}", size - 0.1, 600, de(pn[3])))
    y = y + 4 + len(keys) * rh
    for br in ("isacord", "polyneon"):
        seen = {}
        for k in keys: seen.setdefault(SB.TH[k][br][0], []).append(PAL[k][1])
        for code, nm in seen.items():
            if len(nm) > 1: o.append(t(x, y, f"{' + '.join(nm)} share {'Isacord' if br == 'isacord' else 'Polyneon'} {code}: pick the nearer of two from your card.", 1.35, 600, ORANGE)); y += 2.8
    o.append(t(x, y, "ΔE = colour distance to the target: green < 3, amber 3–5.5 (check on the card), red > 5.5 (propose your nearest).", 1.3, 400, MUTED))
    return y + 2.8

def p_e0():
    o = H("EMBROIDERY SUMMARY — threads, stitch files, how to sew", f"Size M, all 4 pieces. Per-size files + hoop splits: {tp('G5', 'G6')}. Hex = on-screen target; match on your physical card.", "E0")
    o.append(t(12, 32, f"THREADS — 12 colours, 40 wt polyester (Isacord or Madeira Polyneon)  [proposed — confirm on your card]", 2.0, 700))
    y = thread_rows(o, 12, 36.5, kbcore.KB_KEYS)
    y += 4; o.append(t(12, y, "BACKING + NEEDLES", 2.0, 700)); y += 4
    for l in ["Backing 2.5 oz cutaway, navy/black, 30 mm larger than each hooping; trim to 5 mm after sewing. No topping.",
              "Needle 75/11 sharp. Bobbin 60 wt navy or black polyester. Pre-wash the shell before embroidery.",
              "Embroider the cut panels flat, before zip, welts, side + sleeve seams and the hem / cuff bands."]:
        y = para(o, 12, y, l, 100, 1.5, INK, 2.9)
    tx = 112; ty = 32; o.append(t(tx, ty, "STITCH FILES, SIZE M (counted from the DST files)", 2.0, 700)); ty += 4.5
    hd = ["Piece", "Art mm", "Stitches", "Trims", "Stops", "Hoopings", "Run time"]; cx = [tx, tx + 40, tx + 62, tx + 80, tx + 94, tx + 108, tx + 126]
    for x_, h_ in zip(cx, hd): o.append(t(x_, ty, h_, 1.45, 700, MUTED))
    for i, p in enumerate(kbcore.PIECES):
        r = PK.CUR[p]; b = PK.BB[p]; yy = ty + 4.2 + i * 4
        ZB_zebra(o, i, yy + 0.6, 4, tx - 1, SW - 11)
        o.append(t(cx[0], yy, f"{p} {kbcore.PIECE_NAME[p]}", 1.5, 600)); o.append(t(cx[1], yy, f"{b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}", 1.5))
        o.append(t(cx[2], yy, f"{r['stitches']:,}", 1.5, 600)); o.append(t(cx[3], yy, f"{r['trims']}", 1.5)); o.append(t(cx[4], yy, f"{r['stops']}", 1.5))
        o.append(t(cx[5], yy, f"{len(r['splits']['sections'])}", 1.5)); o.append(t(cx[6], yy, f"{sum(PK.mh(v) for v in r['splits']['sections'].values())*60:.0f} min", 1.5))
    yy = ty + 4.2 + 4 * 4 + 0.5
    o.append(t(cx[0], yy, "Per jacket", 1.55, 700)); o.append(t(cx[2], yy, f"{PK.TOT:,}", 1.55, 700)); o.append(t(cx[3], yy, f"{PK.TRIMS:,}", 1.55, 700))
    o.append(t(cx[5], yy, f"{PK.HOOPS}", 1.55, 700)); o.append(t(cx[6], yy, f"{PK.MH_SPLIT:.1f} h", 1.55, 700))
    yy += 4; yy = para(o, tx, yy, "Run time = proposed machine speed + 6 s per trim + 4 s per colour change, split files. Please give your own run time and price per hooping (strike-off).", 95, 1.4, MUTED, 2.6)
    yy += 4; o.append(t(tx, yy, "HOOPING", 2.0, 700)); yy += 4
    for l in [f"Files are split for a {PK.FR_S} mm frame  [proposed — confirm]: pieces taller than the frame sew in two hoopings, S1 (top) then S2 (bottom).",
              "Stop 1 of each split file opens with registration crosses in its own thread: re-hoop S2 on the crosses S1 sewed, then pick them out.",
              "A larger (jacket-back) frame removes the joins — tell us which frames you have (Q, section 2).",
              f"Each piece's needle start + split line per size: {tp('G6')} and the DXF (layer 13)."]:
        yy = para(o, tx, yy, l, 95, 1.5, PROP if "proposed" in l else INK, 2.9); yy += 0.6
    yy += 3; o.append(t(tx, yy, "SEWING ORDER (per piece)", 2.0, 700)); yy += 4
    yy = para(o, tx, yy, "stems → leaves (dark tones first) → lilies (dark → light → throat → stamen lines → anthers) → petals → fish (tail + fins → body → cyan line + red stripe → eye).", 95, 1.5, INK, 2.9)
    yy += 3; o.append(t(tx, yy, SAMPLING, 1.6, 700, ORANGE))
    return o

E_Q = {"01": [f"Art stops {F.KEEP_HEM:.0f} mm above the hem-band seam and {F.KEEP_CF:.0f} mm each side of the zip (nothing crosses the zip) — OK?",
              "Grading: XS–S at 92 %, L + XL sew the M art, XXL–3XL at 108 % (stitch counts above) — OK?",
              "Welt boxes are not embroidered: the art keeps clear of them on every size (G2).",
              "Thread colours: please match all 12 on your card; the 6 blues must read on the washed navy."],
       "02": ["Back half of each sleeve plain (no embroidery) — OK?",
              f"Art stops {F.KEEP_CUFF:.0f} mm above the cuff seam, {F.KEEP_SEAM:.0f} mm off the underarm seam, {F.KEEP_CAP:.0f} mm off the cap — OK?",
              "Grading: XS–S at 92 %, L + XL sew the M art, XXL–3XL at 108 % — OK?",
              "Embroider the sleeve flat before the underarm seam and the cuff band are sewn."]}
def p_element(el):
    pcs = list(kbcore.ELEMS[el][2]); title = kbcore.ELEMS[el][1]
    o = H(f"{el} · {title}", f"One page for the sample room. Full spec (stop list, stitch types, 1:1 details): {tp(el)}.", f"E{el}")
    im, vp, bbox = espec.view_png(el, PK.V, 2.0)
    wmax, hmax = (124, 150) if el == "01" else (96, 150)
    w = min(wmax, hmax * im.width / im.height); tag, h = img_tag(im, 12, 33, w); o.append(tag)
    o.append(t(12, 33 + h + 3.5, "Size M, " + ("both fronts; zip at CF" if el == "01" else "both sleeves, front half embroidered") + ". Hood, back" + (" and back half of the sleeves" if el == "02" else "") + ": plain.", 1.6, 700))
    tx = 12 + w + 8; y = 33
    o.append(t(tx, y, "PLACEMENT, SIZE M (art box in mm)", 2.0, 700)); y += 4.2
    pl = EP.place("M")[0]
    for p in pcs:
        b = pl[p][1].bounds
        y = para(o, tx, y, f"{p} {kbcore.PIECE_NAME[p]}: {b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}, x {b[0]:+.0f} … {b[2]:+.0f}, y {b[1]:.0f} … {b[3]:.0f}", 120, 1.55, INK, 2.9)
    y = para(o, tx, y, ("x from CF (+ = wearer's left), y down from the CF neck seam." if el == "01" else "x from the sleeve centre line, y down from the underarm line.") + " Every size: G2 + DXF layer 8.", 120, 1.4, MUTED, 2.6)
    y += 3; o.append(t(tx, y, "STITCHES + HOOPINGS PER SIZE (counted from the DST files)", 2.0, 700)); y += 4.2
    cx = [tx, tx + 11, tx + 24] + [tx + 24 + 30 * (j + 1) for j in range(len(pcs))]
    for x_, h_ in zip(cx, ["Size", "Art", *[f"{p} stitches / hoopings" for p in pcs]]): o.append(t(x_, y, h_, 1.4, 700, MUTED))
    for i, sz in enumerate(kbcore.SIZES):
        yy = y + 3.6 + i * 3.3; r = PK.ALL[sz]
        if i % 2 == 0: o.append(f'<rect x="{tx - 1}" y="{f(yy - 2.4)}" width="{SW - 11 - tx + 1}" height="3.3" fill="{ALT}"/>')
        o.append(t(cx[0], yy, sz, 1.5, 700)); o.append(t(cx[1], yy, f"{kbcore.GRADE[sz][1] * 100:.0f} %", 1.45, 600, PROP))
        for j, p in enumerate(pcs): o.append(t(cx[2 + j], yy, f"{r[p]['full']['stitches']:,} / {len(r[p]['splits']['sections'])}", 1.45))
    y += 3.6 + 7 * 3.3 + 1
    y = para(o, tx, y, f"Frame {PK.FR_S} mm [proposed — confirm]. 2 hoopings = split files S1 + S2 with registration crosses (E0).", 120, 1.45, PROP, 2.7)
    y += 3; o.append(t(tx, y, f"THREADS ({len(cols(pcs))} colours)", 2.0, 700)); y += 1
    y = thread_rows(o, tx, y + 3, cols(pcs), 3.3, 1.5)
    y += 3; o.append(t(tx, y, "OPEN QUESTIONS", 2.0, 700)); y += 4
    for q in E_Q[el]: y = para(o, tx, y, prop(q), 120, 1.5, PROP, 2.8); y += 0.5
    o.append(t(12, SH - 12, SAMPLING, 1.6, 700, ORANGE))
    return o

def p_qf():
    """ALL factory questions on one page: RFQ first, then the strike-off, open design points, packing"""
    o = H("FACTORY QUESTIONS — quote, strike-off, open points, packing", "Please name your prices; we have not set any. Amber = our proposal — confirm or tell us what you would change.", "Q")
    x1, x2, x3 = 12, 104, 198; y = 32
    o.append(t(x1, y, "1  PLEASE QUOTE", 2.1, 700)); y += 4.4
    o.append(t(x1 + 52, y, "Price", 1.35, 700, MUTED)); o.append(t(x1 + 72, y, "Lead time (days)", 1.35, 700, MUTED)); y += 3.8
    for a in ["Fit sample, M, no embroidery", "Embroidery strike-off (files: below)", "Embroidered sample, size M"]:
        o.append(t(x1, y, a, 1.5)); blank(o, x1 + 52, y, 17); blank(o, x1 + 72, y, 17); y += 4.2
    y += 2; o.append(t(x1, y, "Bulk, price per piece, FOB origin port", 1.6, 700)); o.append(t(x1, y + 3, "[proposed — confirm the Incoterm]", 1.3, 600, PROP)); y += 7
    for j, q in enumerate(LADDER): o.append(t(x1 + j * 22, y, f"{q} pcs", 1.5, 700)); blank(o, x1 + j * 22, y + 4, 17)
    y += 9
    for l in ["Freight quoted separately: air and sea, to Ohio, USA — say whether duty is included.",
              "Please send a quotation sheet: unit price per quantity, spec, freight, total. Sampling + set-up charges listed separately."]:
        y = para(o, x1, y, l, 95, 1.45, INK, 2.7); y += 0.6
    y += 3; o.append(t(x1, y, "3  STRIKE-OFF — first, before any sample", 2.1, 700)); y += 4.4
    for l in ["Sew the size-M files on the washed shell, with the proposed threads + backing: "
              + ", ".join(f"{p} {PK.CUR[p]['stitches']:,} st" for p in kbcore.PIECES) + " (E01, E02).",
              "Send back: photos straight-on in daylight + a close-up with a ruler; the sewn size vs the file (W × H mm); puckering, show-through, thread breaks; run time per hooping and your price for it.",
              "Your digitizer may adjust density + pull for this shell: tell us what you changed."]:
        y = para(o, x1, y, l, 95, 1.45, INK, 2.7); y += 0.8
    y = 32; o.append(t(x2, y, "2  PLEASE TELL US", 2.1, 700)); y += 4.6
    for q in ["MOQ per colourway (pcs)", "MOQ per order (pcs)", "Sample lead time (days)", "Bulk lead time (days)", "Embroidery: in-house or subcontracted?",
              "Max thread colours per head", "Largest embroidery frame (mm)", "Shell you propose: weight + wash", "Fibre % — shell", "Fibre % — body lining (flannel)",
              "Fibre % — sleeve lining (taffeta)", "Fibre % — hood lining (sherpa)", "Fibre % — pocketing", "Payment terms"]:
        o.append(t(x2, y, q, 1.45)); blank(o, x2 + 52, y, 36); y += 4.15
    y += 1.5; y = para(o, x2, y, "The care label (T6b) is printed from the shell fibre content, which is not confirmed yet: please state it, and we send the matching care label artwork.", 95, 1.4, MUTED, 2.6)
    y = 32; o.append(t(x3, y, "4  OPEN DESIGN POINTS — please confirm", 2.1, 700)); y += 4.6
    sref = {"(G5)": "(E01, E02)", "(T2, T7)": "(T2, G2)", "(G3, F1)": "(E0, section 3)", "(Q1)": "(section 2)"}   # summary page codes
    for i, (a, b_) in enumerate(OPEN, 1):
        for k_, v_ in sref.items(): b_ = b_.replace(k_, v_)
        o.append(t(x3, y, f"{i}. {a}", 1.5, 700)); y = para(o, x3 + 3, y + 2.8, b_, 92, 1.4, PROP, 2.6); y += 1.2
    y += 2; o.append(t(x3, y, "5  PACKING  [proposed — confirm]", 2.1, 700)); y += 4.4
    for a, b_ in PACK: y = para(o, x3, y, f"{a}: {b_}", 92, 1.45, PROP, 2.7); y += 0.5
    o.append(t(12, SH - 12, SAMPLING + "  Sample plan: fit sample → strike-off → embroidered sample, M.", 1.6, 700, ORANGE))
    return o

# ---------------------------------------------------------------- TBD (internal: md + png + a page in the internal pack)
TBD = [("Decide with the factory", [
          "MOQ, sample + bulk lead times, FOB price at 100/200/300/500, sample cost, payment terms, freight air + sea (Q1). They quote first.",
          "Shell they propose (weight, wash) + fibre % of shell, flannel, taffeta, sherpa, pocketing (Q1). The care label waits on this (labelsheet MISSING state).",
          "Embroidery in-house or subcontracted; largest frame + needles per head. A bigger frame removes the S1/S2 hoop splits (G5/G6).",
          "Physical thread card for the 12 threads, the 6 blues on washed navy first (G3).",
          "Construction detail for welts, pocket bags, facings, lining: the pack points to the jacket block (T2 note 4, T4 + DXF); no separate seam page exists. Ask if they need one.",
          "Packing: fold, polybag, carton qty + size (Q2). Trims (zip, elastic, threads): their stock equivalents (T6)."]),
       ("Decided by us", [
          "Back + hood plain (★ default, founder card koi-blossom-rfq-questions; shown amber until he answers).",
          "Art 10 mm above hem band / cuffs, 15 mm off the zip (★ default, amber).",
          "Grading XS–S 92 %, L/XL sew the M art, XXL–3XL 108 % (★ default, amber).",
          "Fibre for the care label: 'confirm fibre' and the factory is asked (★ default). Never a guessed %.",
          "'Prepared for' + quantity + reply-by on the cover: blank, the founder writes them.",
          "Product name 'Blossom Tetra Hooded Jacket' (style code HK-HD-KOIB-NV kept). Welt position + angle (mockup).",
          "Fish fill: PR #52 tetra-governed fish replaces the Rev C fish before bulk (files are for sampling).",
          "Hangtag, barcode, RN, Pantone/TCX references: we send them."]),
       ("Decide at sampling", [
          "Fit sample (no embroidery) first: hood crown + face opening with the sherpa, relaxed band + cuff sizes, zip lies flat.",
          "Strike-off on washed duck: pull/shrink, puckering, density, the S1/S2 joints; fish + lily detail at 1:1 (F1).",
          "Wash test of the embroidered panel if the jacket is washed after embroidery.",
          "Thread colours judged on the strike-off against the navy shell."])]
def p_tbd():
    o = H("TBD · every proposed / open item (internal)", f"{REV} {DATE}. Plain words, grouped by who decides. Not in the factory copies.", "TBD")
    y = 34
    for g, items in TBD:
        o.append(t(12, y, g.upper(), 2.3, 700)); y += 4.6
        for it in items: y = para(o, 16, y, "• " + it, 165, 1.6, INK, 2.9); y += 0.6
        y += 3
    return o
def tbd_md():
    L = [f"# Koi blossom hooded jacket ({STYLE}): TBD, {REV} ({DATE})", "",
         "Every proposed or open item, grouped by who decides. Internal: it is not in the factory copies.", ""]
    for g, items in TBD: L += [f"## {g}", ""] + [f"- {it}" for it in items] + [""]
    return "\n".join(L)

# ---------------------------------------------------------------- page table: Page(id, kind, title, audience, svg) + how to make it (svg = filled by render)
# REF_ONLY = full reference only (the summary points to them); SUMMARY_ONLY = the one-page condensations of those.
REF_ONLY = {"T7", "G3", "G4", "G5", "G6", "01", "02", "Q1", "Q2", "F1"}
SUMMARY_ONLY = {"E0", "E01", "E02", "QF"}
def espec_pdf(el): return glob.glob(f"{OUT}/{el}_{kbcore.ELEMS[el][0]}/*_SPEC_{R_}_FACTORY.pdf")[0]
TABLE = [(Page("C1", "cover", "Cover", FACTORY, ""), None),
         (Page("T2", "flats", "Flats + construction notes", FACTORY, ""), lambda: ZB.p_flats()),
         (Page("T3", "measurements", "Size chart + how to measure", FACTORY, ""), lambda: ZB.p_pom()),
         (Page("T4", "pattern", "Pattern pieces + cut list", FACTORY, ""), lambda: ZB.p_pieces()),
         (Page("T6", "bom", "Bill of materials", FACTORY, ""), lambda: ZB.p_bom()),
         (Page("T5", "construction", "Hood + bands construction", FACTORY, ""), lambda: ZB.p_hood()),
         (Page("T6b", "labels_packing", "Labels — Haki standard main + care label", FACTORY, ""), lambda: ZB.p_labels()),
         (Page("G2", "artwork_placement", "Embroidery placement overview + keep-outs", FACTORY, ""), lambda: PK.overview()),
         (Page("T7", "artwork_placement", "Embroidery placement on the pattern, every size", FACTORY, ""), lambda: GM.p_placement()),
         (Page("G3", "artwork_summary", "Thread colours + embroidery trims", FACTORY, ""), lambda: PK.threads()),
         (Page("G4", "artwork_summary", "Stitch summary per piece", FACTORY, ""), lambda: PK.summary()),
         (Page("G5", "artwork_summary", "Stitch files + hoop splits, every size", FACTORY, ""), lambda: PK.files_page()),
         (Page("G6", "artwork_summary", "Hooping table, every size", FACTORY, ""), lambda: PK.hooping_page()),
         (Page("E0", "artwork_summary", "Embroidery summary — threads, files, hooping", FACTORY, ""), lambda: p_e0()),
         (Page("01", "artwork_element", "Element 01 front — spec, stops, 1:1 details", FACTORY, ""), lambda: ("pdf", espec_pdf("01"))),
         (Page("02", "artwork_element", "Element 02 sleeves — spec, stops, 1:1 details", FACTORY, ""), lambda: ("pdf", espec_pdf("02"))),
         (Page("E01", "artwork_element", "01 front — placement, stitches per size, threads, questions", FACTORY, ""), lambda: p_element("01")),
         (Page("E02", "artwork_element", "02 sleeves — placement, stitches per size, threads, questions", FACTORY, ""), lambda: p_element("02")),
         (Page("QF", "factory_questions", "Factory questions — quote, strike-off, open points, packing", FACTORY, ""), lambda: p_qf()),
         (Page("Q1", "factory_questions", "Request for quotation", FACTORY, ""), lambda: p_q1()),
         (Page("Q2", "factory_questions", "Open design points + packing", FACTORY, ""), lambda: p_q2()),
         (Page("F1", "factory_questions", "Strike-off + factory requests", FACTORY, ""), lambda: ("svgs", PK.f1_pages())),
         # internal-only (finish.py's merged pack + the TBD page): listed so summary_gate sees the whole set
         (Page("T1", "internal", "Garment cover (internal contents + key specs)", INT, ""), None),
         (Page("T8", "decisions", "Garment questions + revision log", INT, ""), None),
         (Page("G1", "decisions", "Embroidery cover: provenance + revision log", INT, ""), None),
         (Page("TBD", "decisions", "Every proposed / open item", INT, ""), None)]
MAKE = {pg.id: mk for pg, mk in TABLE}

def made(pg, index):
    """[("svg", str) | ("pdf", path)] for one page, in the current kbcore.MODE (factory pages scrubbed)"""
    r = p_cover(index) if pg.id == "C1" else MAKE[pg.id]()
    if isinstance(r, tuple) and r[0] == "pdf": return [r]
    if isinstance(r, tuple) and r[0] == "svgs": return [("svg", kbcore.scrub(s)) for s in r[1]]
    return [("svg", kbcore.scrub(doc(r)))]

def render(pages, out, tag):
    """pages = fc_shim.factory_pages(...) (KINDS order); C1 is built last so its contents carry the page numbers"""
    body = {pg.id: made(pg, None) for pg in pages if pg.id != "C1"}
    index, k = [], 1
    for pg in pages:
        index.append((f"{pg.id}  {pg.title}", k))
        k += 1 if pg.id == "C1" else sum(len(PdfReader(v).pages) if typ == "pdf" else 1 for typ, v in body[pg.id])
    if tag == "techpack":
        k = 1
        for pg in pages:
            n_ = 1 if pg.id == "C1" else sum(len(PdfReader(v).pages) if typ == "pdf" else 1 for typ, v in body[pg.id])
            TP[pg.id] = (k, k + n_ - 1); k += n_
    body["C1"] = made(pages[0], index)
    w = PdfWriter(); pngs = []; n = 0
    for pg in pages:
        for typ, v in body[pg.id]:
            if typ == "svg":
                pg.svg = v; n += 1; png = f"{PG}/{tag}_p{n:02d}_{pg.id}.png"; pdf = f"{PG}/{tag}_p{n:02d}.pdf"
                cairosvg.svg2pdf(bytestring=v.encode(), write_to=pdf); cairosvg.svg2png(bytestring=v.encode(), write_to=png, output_width=2000)
                w.append(PdfReader(pdf)); pngs.append(png)
            else:
                rd = PdfReader(v); w.append(rd)
                for j in range(len(rd.pages)):
                    n += 1; png = f"{PG}/{tag}_p{n:02d}_{pg.id}"
                    subprocess.run(["pdftoppm", "-png", "-r", "170", "-f", str(j + 1), "-l", str(j + 1), "-singlefile", v, png], check=True)
                    pngs.append(png + ".png")
    tmp = out + ".tmp.pdf"; w.write(tmp)
    subprocess.run(["python3", "shrink.py", tmp, out, "3000", "82"], check=True); os.remove(tmp)
    print("pages", len(PdfReader(out).pages), out, round(os.path.getsize(out) / 1e6, 1), "MB")
    return len(PdfReader(out).pages), pngs

def sha_manifest():
    m = {os.path.relpath(p, OUT): hashlib.sha256(open(p, "rb").read()).hexdigest() for p in sorted(glob.glob(f"{OUT}/0*_*/**/*.dst", recursive=True) + glob.glob(f"{OUT}/0*_*/**/*.pes", recursive=True))}
    json.dump(m, open("bench/dst_sha_RevD.json", "w"), indent=1)
    return m
def factory_zip():
    """the files a factory gets with the PDFs: pattern, stitch files (+ thread charts, art, previews), labels, factory README"""
    Z = f"{OUT}/pkg_factory"; shutil.rmtree(Z, ignore_errors=True); os.makedirs(f"{Z}/elements")
    for el, (slug, _, _) in kbcore.ELEMS.items():
        shutil.copytree(f"{OUT}/{el}_{slug}", f"{Z}/elements/{el}_{slug}", ignore=shutil.ignore_patterns("summary.json", "result_*.json", "*.pdf", "*.json"))
    shutil.copytree(f"{OUT}/garment/pattern", f"{Z}/pattern")
    if os.path.isdir(f"{OUT}/garment/labels"): shutil.copytree(f"{OUT}/garment/labels", f"{Z}/labels")
    for p in (FAC_SUM, FAC_REF): shutil.copy(p, Z)
    open(f"{Z}/README.txt", "w").write(f"""HAKI STUDIOS - {NAME} (style {STYLE}) - {REV} - {DATE}

{os.path.basename(FAC_SUM)}   start here: what you need to make the sample right the first time, + our questions (Q1, Q2).
{os.path.basename(FAC_REF)}   full reference: every page, incl. pattern pieces, stitch files per size and the hooping table.
pattern/     DXF per size + all sizes (AAMA, mm; layer 8 = embroidery art box + design centre, layer 13 = needle start), 1:1 plot PDF size M.
elements/01_front-fish/<size>/   wearer's right + left front stitch files (DST + PES), thread charts, previews.
elements/02_sleeve-fish/<size>/  wearer's right + left sleeve (front half) stitch files. splits/ = two hoopings for a {PK.FR_S} mm frame [proposed - confirm].
labels/      Haki standard main label artwork (care label follows once the fibre content is confirmed).

{SAMPLING}
Every [proposed - confirm] in the PDFs is still open: please confirm it or propose your alternative.
""")
    zp = f"{OUT}/HAKI_{kbcore.SHORT}_{R_}_factory-files.zip"
    if os.path.exists(zp): os.remove(zp)
    subprocess.run(f"cd {Z} && zip -qr ../{os.path.basename(zp)} .", shell=True, check=True)
    return zp

def build():
    for sz in GM.SIZES: assert ZB.CHECK[sz] and ZB.WALKS_OK[sz] and ZB.SHAPE_OK[sz], f"pattern QA failed {sz}"
    assert os.path.exists(INTERNAL), "run finish.py first (it writes the internal merged pack)"
    kbcore.MODE = "factory"
    SHT.FOOT = SB.FOOT = f"HAKI STUDIOS · {NAME} · {STYLE} · {REV} · {DATE}"
    subprocess.run(["python3", "run_spec.py", "--factory"], check=True)            # factory element specs (_FACTORY.pdf)
    pages = [pg for pg, _ in TABLE]
    probs = FC.summary_gate(pages, decorated=True); assert not probs, probs
    fac = FC.factory_pages(pages); internal = [pg for pg in pages if pg.audience == INT]
    ref = [pg for pg in fac if pg.id not in SUMMARY_ONLY]; summ = [pg for pg in fac if pg.id not in REF_ONLY]
    for nm, ps in (("techpack", ref), ("summary", summ)): assert not FC.summary_gate(ps + internal), (nm, FC.summary_gate(ps + internal))
    n_ref, png_ref = render(ref, FAC_REF, "techpack")             # first: the summary pages cite its page numbers (TP)
    n_sum, png_sum = render(summ, FAC_SUM, "summary")
    kbcore.MODE = "internal"
    buf = io.BytesIO(open(INTERNAL, "rb").read()); rd = PdfReader(buf); w = PdfWriter()
    for pg_ in rd.pages:                                   # re-runs: drop the TBD page an earlier rfq.py run appended
        if "every proposed / open item (internal)" not in (pg_.extract_text() or ""): w.add_page(pg_)
    svg = doc(p_tbd()); cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"{PG}/tbd.pdf"); w.append(PdfReader(f"{PG}/tbd.pdf")); w.write(INTERNAL)
    cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{OUT}/TBD_{R_}.png", output_width=2400)
    open(f"{OUT}/TBD_{R_}.md", "w").write(tbd_md())
    stripped = {os.path.basename(p): FC.strip_creator(p) for p in (FAC_SUM, FAC_REF)}    # the files that ship, post-shrink
    meta = {os.path.basename(p): rfqgate.meta_names(p) for p in (FAC_SUM, FAC_REF)}
    print("strip_creator", stripped, "meta", meta)
    g = rfqgate.check([FAC_SUM, FAC_REF], INTERNAL); g["meta"] = meta
    json.dump(g, open(f"{OUT}/leak_gate_{R_}.json", "w"), indent=1, ensure_ascii=False)
    for p, r in g["gates"].items():
        for h in r["factory"]: print("LEAK", os.path.basename(p), h)
        if r["empty"]: print("EMPTY", os.path.basename(p), r["empty"])
        assert not r["blind"], "leak gate found nothing in the INTERNAL copy — the gate is blind (red-then-green failed)"
    assert g["ok"], "leak gate: internal strings in a factory copy"
    sha = sha_manifest(); zp = factory_zip()
    ih = next(iter(g["gates"].values()))["internal_hits"]
    print(f"leak gate ok: {ih} hits in internal, 0 in summary ({n_sum} pp) + techpack ({n_ref} pp); "
          f"internal {len(PdfReader(INTERNAL).pages)} pp; {len(sha)} stitch files hashed; {zp}")
    return dict(summary=(FAC_SUM, n_sum, png_sum), techpack=(FAC_REF, n_ref, png_ref), internal=INTERNAL, zip=zp)

if __name__ == "__main__":
    build()
