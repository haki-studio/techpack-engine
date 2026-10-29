"""Rev K/L/M pullover pack (factory-facing): K1 factory summary = questions for Mandy, K2 overview, K3 hoop plan + files,
K4 back badges + hem script, K5 star field rules, K6 block / size chart; then the Rev J badge stitch-detail pages
(E01-E04, R1) as reference with a banner. Every stitch number is read from result_<tag>_*.json (DST read-back).
No prices, no machine minutes and no cost thoughts go in here (request-a-supplier-quote: the factory names prices first).
usage: python3 pv_pack.py [SIZE] -> out/pv/<SIZE>/HAKI_KCOS-PULLOVER_RevM_<SIZE>.pdf + _files.zip"""
import sys, os, glob, json, zipfile, io
import cairosvg
import kccore
import sheet as SB
from sheet import t, header, doc, embed_svg_png, INK, MUTED, RED, ORANGE, GUIDE
import pv_block as B
import kcdoc as KD, tofu

SIZE = next((a for a in sys.argv[1:] if a in B.CHART), "M")
OUT = f"out/pv/{SIZE}"; PG = f"{OUT}/pages"; os.makedirs(PG, exist_ok=True)
REVJ = os.environ.get("KCOS_REVJ_PDF", "/mnt/c/Users/devin/Desktop/TECH PACKS/2 Keep Clean Our Space hoodie/Keep Clean Our Space hoodie - Rev J - full tech pack - USABLE WITH CAVEAT.pdf")
MOCK = "inputs/mockups-3-2026-10-27.png"   # Rev M: "Mockups 3", Nick approved 27 Oct
SB.FOOT = "HAKI STUDIOS · Keep Clean Our Space pullover hoodie (washed black) · Rev M · 28 Oct 2026 · size M"
plan = json.load(open(f"{OUT}/plan_allover.json"))
R = {}
for fp in glob.glob(f"{OUT}/result_allover_*.json"): R.update(json.load(open(fp)))
ORDER = ("FR", "BK", "PK", "SR", "SL", "HR", "HL")
def over():
    """hoopings whose frame (centred on the cell) is bigger than the cut piece in either direction (TD M1)"""
    out = []
    for P in ORDER:
        x0, y0, x1, y1 = plan["pieces_mm"][P]
        for i, c in enumerate(plan["cells"][P]):
            fw, fh = c["frame"]; cx, cy = (c["box"][0] + c["box"][2]) / 2, (c["box"][1] + c["box"][3]) / 2
            if cx - fw / 2 < x0 or cx + fw / 2 > x1 or cy - fh / 2 < y0 or cy + fh / 2 > y1: out.append(B.hoop_name(P, i, len(plan["cells"][P])))
    return out
def files(P): return sorted([(k, v) for k, v in R.items() if v["piece"] == P], key=lambda kv: kv[1]["hooping"])
OVER = over()
TOT = dict(files=len(R), stitches=sum(v["stitches"] for v in R.values()), trims=sum(v["trims"] for v in R.values()))
AMB = "#B26A00"
def threads(v): th = v.get("threads"); return th.get("n", th.get("count", "?")) if isinstance(th, dict) else th
def wrap(o, x, y, text, size=2.5, w=400, fill=INK, width=125, lh=None):
    lh = lh or size * 1.45; line = ""
    for word in text.split(" "):
        if len(line) + len(word) + 1 > width: o.append(t(x, y, line, size, w, fill)); y += lh; line = word
        else: line = (line + " " + word).strip()
    if line: o.append(t(x, y, line, size, w, fill)); y += lh
    return y

def k1():
    o = header("K1 · FACTORY SUMMARY — please answer these before sampling",
               "Rev M: washed-black kangaroo-pocket pullover hoodie, Come Over block, Hidden Inventory fabric + wash. Embroidered on cut pieces before sewing.", "K1")
    y = 33
    o.append(t(12, y, "HOOPINGS PER PIECE (our plan, size M, field up to 340 x 505 mm each, frame can be turned 90 degrees)", 2.8, 700)); y += 5
    cols = (12, 52, 70, 150, 178, 200)
    for x, h in zip(cols, ("Piece", "Hoopings", "Field size of each hooping (mm, w x h)", "Stitches", "Trims", "Files")): o.append(t(x, y, h, 2.3, 700, MUTED))
    y += 4
    for P in ORDER:
        fs = files(P); cells = plan["cells"][P]
        o.append(t(cols[0], y, B.NAMES[P], 2.4)); o.append(t(cols[1], y, str(len(cells)), 2.4, 700))
        o.append(t(cols[2], y, ", ".join(f"{v['cell_mm'][2]-v['cell_mm'][0]:.0f} x {v['cell_mm'][3]-v['cell_mm'][1]:.0f}" for _, v in fs), 2.3))
        o.append(t(cols[3], y, f"{sum(v['stitches'] for _, v in fs):,}", 2.3)); o.append(t(cols[4], y, str(sum(v['trims'] for _, v in fs)), 2.3))
        o.append(t(cols[5], y, ", ".join(k for k, _ in fs), 2.1, 400, MUTED)); y += 4.2
    o.append(t(cols[0], y, "Total", 2.4, 700)); o.append(t(cols[1], y, str(plan["total_hoopings"]), 2.4, 700))
    o.append(t(cols[3], y, f"{TOT['stitches']:,}", 2.4, 700)); o.append(t(cols[4], y, str(TOT["trims"]), 2.4, 700)); y += 8
    # founder 27 Oct: "use the same fabric as hidden inventory + the same wash". Lines copied verbatim from the Hidden
    # Inventory Hoodie tech pack (14/09/2025) BOM; that pack has no wash line, so the wash is named, not specified (Q2).
    o.append(t(12, y, "FABRIC + WASH (same as our Hidden Inventory Hoodie, which you made for us; wording from its BOM)", 2.8, 700)); y += 4.6
    for h, q in (("Self", "French Terry/Fleece. 350 GSM. 100% Cotton. Finishing: Brushed on reverse side. Colour: washed black."),
                 ("Rib (cuffs + body hem)", "Rib Knit 1x1. 380 GSM. 2 Way strechable. 95% Cotton 5% Elastane. Colour: washed black."),
                 ("Wash", "The same wash as our Hidden Inventory Hoodie (question 2)."),
                 ("Block", "Your Come Over hoodie pattern and measurements (page K6), not Hidden Inventory.")):
        o.append(t(12, y, h, 2.4, 700)); o.append(t(52, y, q, 2.4)); y += 3.8
    y += 2
    o.append(t(12, y, "QUESTIONS", 2.8, 700)); y += 5
    sr = R.get("SR-H1", {})
    Q = [("1. Hoopings + frame.", f"How many hoopings do you need for each piece (front, back, pocket, sleeve, hood)? Our plan is {plan['total_hoopings']} per hoodie (table above). On a 340 x 505 field the pocket and left sleeve hoopings need the frame turned 90 degrees. On a 400 x 450 frame every hooping fits without turning EXCEPT the two back hoopings (up to 486 mm tall): there the back needs more hoopings: we will re-plan it for your frame and send the new count. You confirmed a 340 x 505 mm field in one hooping, but your frames are 300 x 300 and 400 x 450: which frame sews 340 x 505? Please answer this before digitizing or sewing: if no frame takes 340 x 505, we re-plan the hoopings for your frame."),
         ("2. Wash.", "Please use the same fabric and the same wash as our Hidden Inventory Hoodie. What is that wash called, and is it done AFTER sewing? Shrinkage % in length and width? Does it change the thread colours or flatten the 3D puff? Our files assume 40wt polyester thread (page R1): is that what you use?"),
         ("3. How you price embroidery.", f"Per 1,000 stitches, per trim, per hooping, or per piece? Please quote one sleeve file as the example: SR-H1 ({sr.get('stitches', 0):,} stitches, {sr.get('trims', 0)} trims, 1 colour). Then please quote (a) the embroidery only (b) the whole hoodie with embroidery, and (c) the same without the two hood hoopings (HR-H1, HL-H1), at 100, 200 and 300 pcs."),
         ("4. Blocks or floating.", "Please choose one. Most hoopings are bigger than the cut piece they sit on (" + ", ".join(OVER) + "), so a cut piece cannot be clamped in the frame. Which do you do: (a) embroider oversized rough-cut blocks and recut them to the pattern after, or (b) float the cut piece on hooped tear-away backing? If (a), what allowance do you add for pull-in?"),
         ("5. Strike-off through the wash.", "Before bulk, will you sew one back panel (files BK-L + BK-R: all 4 badges in 3D puff + stars) and put it through the real wash (do the dense 3D puff areas pucker after the wash?), then send photos (daylight, ruler in shot, before and after wash)? Please also sew file SR-H1 (right sleeve) on a scrap of the same fabric and wash it with the panel: it carries our smallest stars and dots. Yes / no, and how many days?"),
         ("6. Your pattern.", "Please send the Come Over hoodie pattern (DXF) or the cut panel sizes. Our outlines come from the published size chart (page K6); we re-place every star and badge on your real pieces before bulk, all sizes. Also: how wide is the finish on the kangaroo pocket openings (the script ends near the right opening)? Is the hood lined, and how many panels is it?")]
    for h, q in Q:
        o.append(t(12, y, h, 2.6, 700)); y = wrap(o, 52, y, q, 2.45, width=172); y += 1.5
        o.append(f'<line x1="52" y1="{y}" x2="{SB.SW-12}" y2="{y}" stroke="#CFCFCF" stroke-width="0.2"/>'); o.append(t(52, y - 0.6, "Answer:", 1.9, 400, MUTED)); y += 4
    return o

def img_page(code, title, sub, path, w=273, x=12, y=30, extra=None):
    o = header(title, sub, code); im, h = embed_svg_png(path, x, y, w)
    if h > 168: im, h = embed_svg_png(path, x, y, w * 168 / h)
    o.append(im)
    if extra: o += extra
    return o

def k3():
    o = header("K3 · HOOP PLAN + STITCH FILES (size M)", "Blue boxes = one hooping each. Nothing crosses a box edge: stars keep 10 mm off every split line, so hooping-to-hooping alignment does not show.", "K3")
    im, h = embed_svg_png(f"{OUT}/layout_allover.png", 12, 29, 128); o.append(im)
    x0 = 146; y = 31
    hd = ("File", "Field w x h", "Art centre (x, y)", "Stitches", "Trims", "Colours", "Stops", "Max st.")
    xs = (x0, x0 + 34, x0 + 52, x0 + 76, x0 + 91, x0 + 102, x0 + 114, x0 + 124)
    for x, s in zip(xs, hd): o.append(t(x, y, s, 2.0, 700, MUTED))
    y += 3.6
    for P in ORDER:
        for k, v in files(P):
            c = v["cell_mm"]
            row = (f"HAKI_KCOS-PO_{k}_M", f"{c[2]-c[0]:.0f} x {c[3]-c[1]:.0f}", f"{v['origin_mm'][0]:.0f}, {v['origin_mm'][1]:.0f}", f"{v['stitches']:,}",
                   str(v["trims"]), str(threads(v)), str(v["stops"]), f"{v['max_stitch']:.1f}")
            for x, s in zip(xs, row): o.append(t(x, y, s, 2.0))
            if v.get("foam_pause_before_stop"): o.append(t(x0 + 133, y, "puff", 1.9, 700, ORANGE))
            y += 3.4
    y += 2
    for line in ("Art centre = file origin, in mm. Front / back: x from CF / CB, + = to the right as the piece lies face up (as drawn),",
                 "y down from the HPS line. Sleeves: x from the sleeve centre line (front half = -x on SR, +x on SL, as drawn), y from the cap top. Hood: x from the face",
                 "edge, y from the crown. Pocket: x from its centre, y from its top edge.",
                 "'puff' = the file has a machine PAUSE to lay 3 mm foam before the puff stops (same procedure as Rev J).",
                 "Every number is read back from the written DST. Max stitch < 7.5 mm. Max 12 colours per file (your limit)."):
        o.append(t(x0, y, line, 1.95, 400, MUTED)); y += 3
    return o

def k4():
    TX = kccore.TEXT
    o = header("K4 · BACK BADGES + HEM SCRIPT", "The 4 badges are the Rev J badges unchanged (same stitch files, colours, 3D puff), placed where the approved mockup has them. Stitch detail: reference pages E01-E04, R1.", "K4")
    import pv_view as V
    o2, (bx, by, bw, bh) = V.piece_svg("BK", pad=10, label=True)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{bx} {by} {bw} {bh}">' + "".join(o2) + "</svg>"
    cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{PG}/k4_back.png", output_width=1600)
    im, h = embed_svg_png(f"{PG}/k4_back.png", 12, 29, 150); o.append(im)
    x0 = 168; y = 33
    names = {"01": "JP burst", "02": "EN star oval", "03": "CN dotted capsule", "04": "KR oval"}
    for el in ("01", "02", "03", "04"):
        b = plan["badges"][el]; txt = TX[el] if isinstance(TX[el], str) else " ".join(TX[el])
        o.append(t(x0, y, f"{el} · {names[el]}", 2.6, 700)); y += 3.8
        o.append(KD.auto(x0, y, f"Text: {txt}", 2.4)); y += 3.4
        o.append(t(x0, y, f"Size {b['size_mm'][0]:.0f} x {b['size_mm'][1]:.0f} mm · centre x {b['placed_centre_mm'][0]:+.0f}, y {b['placed_centre_mm'][1]:.0f} mm (from CB, HPS line)", 2.2, 400, MUTED)); y += 5.5
    s = plan["script"]
    o.append(t(x0, y, "07 · Hem script on the pocket (front, lower right)", 2.6, 700)); y += 3.8
    o.append(t(x0, y, f"Text: {s['text']}", 2.4)); y += 3.4
    o.append(t(x0, y, f"White satin, {s['font']}, {s['width_mm']:.0f} mm wide, cap height {s['cap_height_mm']:.1f} mm", 2.2, 400, MUTED)); y += 3.2
    o.append(t(x0, y, f"Centre x {s['centre_mm'][0]:+.0f}, y {s['centre_mm'][1]:.0f} mm (from pocket centre / top edge); file PK-H1", 2.2, 400, MUTED)); y += 6
    for line in ("Text is set from the Rev J files, NOT copied from the mockup:",
                 "the mockup is a render; its Korean and Chinese lines are not",
                 "the approved spelling. Please sew the text exactly as in the files."):
        o.append(t(x0, y, line, 2.3, 600, RED)); y += 3.4
    return o

def k5():
    st = plan["stars"]; n = plan["star_counts"]
    o = header("K5 · STAR FIELD — white stars placed as in the approved mockup", f"{sum(n.values())} stars at size M (Rev J star shapes), each one placed where the approved mockup (page K2) shows it. About {st['plus_share']*100:.0f}% are 4-point sparkles, the rest dots.", "K5")
    y = 34
    o.append(t(12, y, "Stars per piece (size M)", 2.8, 700)); y += 5
    pp = st.get("per_panel", {})
    for x, h in ((60, "Stars"), (78, "Sparkles"), (98, "Average size")): o.append(t(x, y - 0.5, h, 2.0, 700, MUTED))
    y += 3.5
    for P in ORDER:
        o.append(t(12, y, B.NAMES[P], 2.4)); o.append(t(60, y, str(n[P]), 2.4, 700))
        if P in pp: o.append(t(78, y, str(pp[P]["plus"]), 2.4)); o.append(t(98, y, f"{pp[P]['mean_mm']:.1f} mm", 2.4))
        y += 4
    y += 4; o.append(t(12, y, "Layout rules (the files already follow them)", 2.8, 700)); y += 5
    k = plan["keep"]
    for r in ("Star positions follow the mockup by proportion of each piece (the mockup is not to scale). A star that fell on a seam allowance, a hoop split or a badge was moved up to 10 mm, or left out.",
              f"No star within {k['split']:.0f} mm of a hoop split line (so a small hooping shift never cuts or doubles a star).",
              f"No star within {k['edge']:.0f} mm of a cut edge (10 mm seam allowance + 8 mm clear) [proposed — confirm your seam allowance].",
              f"No star under the kangaroo pocket or within {k['under_pocket']:.0f} mm of where it is sewn; the pocket carries its own stars.",
              f"Hood: no star within {k['face']:.0f} mm of the face edge (turn-back) [proposed]. Hood star positions are approximate until we have your hood pattern [proposed]. Pocket: {k['pocket']:.0f} mm from its cut edge.",
              "Sleeves are NOT a mirror pair: each sleeve's front half and back half carry different stars. Front half = the side towards the front notch.",
              f"Stars keep {k['objects']:.0f} mm away from every badge and from the hem script.",
              "Hoopings cover only the area that carries embroidery; the rest of each piece is plain.",
              "Back files: BK-L = the half with the Japanese burst + Chinese capsule badges; BK-R = the half with KEEP CLEAN OUR SPACE + the Korean oval.",
              "Rib (hem, cuffs) is not embroidered.",
              "Most hoopings are bigger than the cut piece: blocks or floating, please choose in question 4."):
        y = wrap(o, 14, y, "• " + r, 2.4, width=150); y += 1
    im, h = embed_svg_png(f"{OUT}/stitch_allover/HAKI_KCOS-PO_SR-H1_M_preview.png", 190, 32, 90)
    o.append(im); o.append(t(190, 34 + h, "Read-back render of file SR-H1 (right sleeve)", 2.0, 400, MUTED))
    return o

def k6():
    o = header("K6 · BLOCK — Come Over hoodie size chart (published) + what we assumed", "Our panel outlines are for embroidery placement only. Please cut from YOUR Come Over pattern and send it to us (question 6).", "K6")
    y = 34; xs = (12, 34, 62, 90, 124)
    for x, h in zip(xs, ("Size",) + B.CHART_COLS): o.append(t(x, y, h, 2.3, 700, MUTED))
    y += 4.5
    for sz, vals in B.CHART.items():
        o.append(t(xs[0], y, sz, 2.4, 700))
        for x, v in zip(xs[1:], vals): o.append(t(x, y, f'{v}" ({v*B.IN:.0f} mm)', 2.3))
        y += 4
    o.append(t(12, y + 1, "Inches, flat. Chest = pit to pit. Sleeve = shoulder seam to cuff end. Source: Haki hoodie size chart (Come Over).", 2.0, 400, MUTED)); y += 9
    o.append(t(12, y, "Assumed for placement [proposed — confirm, or send your pattern]", 2.8, 700, AMB)); y += 5
    for kk, lab in B.PROPOSED.items():
        o.append(t(14, y, lab, 2.3, 400, AMB)); o.append(t(80, y, f"{B.P[kk]:.0f} mm", 2.3, 600, AMB)); y += 3.6
    o.append(t(14, y + 1, f"Seam allowance {B.SA:.0f} mm", 2.3, 400, AMB))
    import pv_view as V
    for i, P in enumerate(("FR", "SR")):
        o2, (bx, by, bw, bh) = V.piece_svg(P, pad=8, label=False, cells=False)
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{bx} {by} {bw} {bh}">' + "".join(o2) + "</svg>"
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{PG}/k6_{P}.png", output_width=900)
        im, h = embed_svg_png(f"{PG}/k6_{P}.png", 150 + i * 72, 34, 66); o.append(im)
        o.append(t(150 + i * 72, 36 + h, f"{B.NAMES[P]} (size M, cut line)", 2.0, 400, MUTED))
    return o

def build():
    pages = [("K1", k1()),
             ("K2", img_page("K2", "K2 · OVERVIEW — target look (mockup) and our size-M layout", "Mockup (approved) = look and placement (do not copy its lettering). Layout = what the stitch files sew.",
                             MOCK, w=200, extra=None)),
             ("K3", k3()), ("K4", k4()), ("K5", k5()), ("K6", k6())]
    from pypdf import PdfWriter, PdfReader
    wr = PdfWriter()
    for k, o in pages:
        svg = tofu.check(doc(o), k); cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"{PG}/{k}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{PG}/prev_{k}.png", output_width=2000)
        wr.append(f"{PG}/{k}.pdf")
    if not os.path.exists(REVJ) and not os.environ.get("KCOS_DRAFT"):   # never ship a pack without the badge stitch detail
        sys.exit(f"Rev J reference pack not readable: {REVJ} (set KCOS_DRAFT=1 for a preview without pages E01-E04, R1)")
    if os.path.exists(REVJ):
        rj = PdfReader(REVJ)
        ban = doc([f'<rect x="0" y="0" width="{SB.SW}" height="9" fill="#B3261E"/>',
                   t(8, 6.2, "REFERENCE ONLY (Rev J) — stitch detail of the badges. On the pullover they sit on the BACK: placement is page K4, files are BK-L / BK-R.", 2.6, 700, "#FFFFFF")])
        bp = io.BytesIO(cairosvg.svg2pdf(bytestring=ban.encode())); banner = PdfReader(bp).pages[0]
        for i in (16, 17, 18, 19, 25):         # E01-E04, R1
            p = rj.pages[i]; p.merge_page(banner); wr.add_page(p)
    pdf = f"{OUT}/HAKI_KCOS-PULLOVER_RevM_{SIZE}.pdf"; wr.write(pdf)
    z = f"{OUT}/HAKI_KCOS-PULLOVER_RevM_{SIZE}_files.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(pdf, os.path.basename(pdf))
        for fp in sorted(glob.glob(f"{OUT}/stitch_allover/*")):
            if fp.endswith((".dst", ".pes", "_preview.png")): zf.write(fp, "stitch_files/" + os.path.basename(fp))
        zf.writestr("README.txt", "Keep Clean Our Space pullover hoodie, Rev M, size M.\nOne DST + PES per hooping (name = piece-hooping), plus a preview of each.\n"
                    "Pieces: FR front, BK back, PK kangaroo pocket, SR/SL sleeves, HR/HL hood sides. Hooping plan and placement: PDF pages K3-K4.\n"
                    "Other sizes are built after your answers on page K1 (your pattern, wash, hoopings).\n")
    print(pdf, z, TOT)

if __name__ == "__main__":
    build()
