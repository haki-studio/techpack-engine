"""Rev K pullover pack (factory-facing): K1 factory summary = questions for Mandy, K2 overview, K3 hoop plan + files,
K4 back badges + hem script, K5 star field rules, K6 block / size chart; then the Rev J badge stitch-detail pages
(E01-E04, R1) as reference with a banner. Every stitch number is read from result_<tag>_*.json (DST read-back).
No prices, no machine minutes and no cost thoughts go in here (request-a-supplier-quote: the factory names prices first).
usage: python3 pv_pack.py [SIZE] -> out/pv/<SIZE>/HAKI_KCOS-PULLOVER_RevK_<SIZE>.pdf + _files.zip"""
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
MOCK = "inputs/mockup-2026-10-23-hoodie-front-back.png"
SB.FOOT = "HAKI STUDIOS · Keep Clean Our Space pullover hoodie (washed black) · Rev K · 23 Oct 2026 · size M"
plan = json.load(open(f"{OUT}/plan_allover.json"))
R = {}
for fp in glob.glob(f"{OUT}/result_allover_*.json"): R.update(json.load(open(fp)))
ORDER = ("FR", "BK", "PK", "SR", "SL", "HR", "HL")
def files(P): return sorted([(k, v) for k, v in R.items() if v["piece"] == P], key=lambda kv: kv[1]["hooping"])
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
               "Washed-black kangaroo-pocket pullover hoodie on your EE / Come Over hoodie block. Embroidery on the cut pieces before sewing: all-over white stars + 4 colour badges on the back + hem script on the pocket.", "K1")
    y = 33
    o.append(t(12, y, "HOOPINGS PER PIECE (our plan, size M, field up to 340 x 505 mm each)", 2.8, 700)); y += 5
    cols = (12, 52, 70, 150, 178, 200)
    for x, h in zip(cols, ("Piece", "Hoopings", "Field size of each hooping (mm, w x h)", "Stitches", "Trims", "Files")): o.append(t(x, y, h, 2.3, 700, MUTED))
    y += 4
    for P in ORDER:
        fs = files(P); cells = plan["cells"][P]
        o.append(t(cols[0], y, B.NAMES[P], 2.4)); o.append(t(cols[1], y, str(len(cells)), 2.4, 700))
        o.append(t(cols[2], y, ", ".join(f"{c['w']:.0f} x {c['h']:.0f}" for c in cells), 2.3))
        o.append(t(cols[3], y, f"{sum(v['stitches'] for _, v in fs):,}", 2.3)); o.append(t(cols[4], y, str(sum(v['trims'] for _, v in fs)), 2.3))
        o.append(t(cols[5], y, ", ".join(k for k, _ in fs), 2.1, 400, MUTED)); y += 4.2
    o.append(t(cols[0], y, "Total", 2.4, 700)); o.append(t(cols[1], y, str(plan["total_hoopings"]), 2.4, 700))
    o.append(t(cols[3], y, f"{TOT['stitches']:,}", 2.4, 700)); o.append(t(cols[4], y, str(TOT["trims"]), 2.4, 700)); y += 8
    o.append(t(12, y, "QUESTIONS", 2.8, 700)); y += 5
    sr = R.get("SR-H1", {})
    Q = [("1. Hoopings + frame.", f"Our plan is {plan['total_hoopings']} hoopings per hoodie (table above). Can you do it in fewer? You confirmed a 340 x 505 mm field in one hooping, but your frames are 300 x 300 and 400 x 450: which frame sews 340 x 505?"),
         ("2. Wash.", "Is the washed black dyed or washed AFTER sewing? If yes: shrinkage % in length and width, and does the wash change the thread colours or flatten the 3D puff?"),
         ("3. How you price embroidery.", f"Per 1,000 stitches, per trim, per hooping, or per piece? Please quote one sleeve file as the example: SR-H1 ({sr.get('stitches', 0):,} stitches, {sr.get('trims', 0)} trims, 1 colour). Then please quote the whole hoodie, embroidered, at 100, 200 and 300 pcs."),
         ("4. Oversized blocks.", "Will you embroider oversized rough-cut blocks and recut them to the pattern after (yes / no)? If no, what allowance do you add for pull-in?"),
         ("5. Strike-off through the wash.", "Before bulk, will you sew one back panel (files BK-H1 + BK-H3: badges in 3D puff + stars) and put it through the real wash, then send photos (daylight, ruler in shot, before and after wash)? Yes / no, and how many days?"),
         ("6. Your pattern.", "Please send the EE / Come Over hoodie pattern (DXF) or the cut panel sizes. Our outlines come from the published size chart (page K6); we re-place every star and badge on your real pieces before bulk, all sizes.")]
    for h, q in Q:
        o.append(t(12, y, h, 2.6, 700)); y = wrap(o, 52, y, q, 2.45, width=140); y += 1.5
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
    for line in ("Art centre = file origin, in mm. Front / back: x from CF / CB (+ = wearer's left on the front, wearer's right on the",
                 "back view), y down from the HPS line. Sleeves: x from the sleeve centre line, y from the cap top. Hood: x from the face",
                 "edge, y from the crown. Pocket: x from its centre, y from its top edge.",
                 "'puff' = the file has a machine PAUSE to lay 3 mm foam before the puff stops (same procedure as Rev J).",
                 "Every number is read back from the written DST. Max stitch < 7.5 mm. Max 12 colours per file (your limit)."):
        o.append(t(x0, y, line, 1.95, 400, MUTED)); y += 3
    return o

def k4():
    TX = kccore.TEXT
    o = header("K4 · BACK BADGES + HEM SCRIPT", "The 4 badges are the Rev J badges unchanged (same stitch files, colours, 3D puff), moved from the jacket fronts to the back. Stitch detail: reference pages E01-E04, R1.", "K4")
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
    for line in ("Text is set from the Rev J files, NOT copied from the new mockup:",
                 "the mockup is an AI render; its Korean line is mirror-reversed and",
                 "its Chinese line is misspelt. Please sew the text exactly as in the files."):
        o.append(t(x0, y, line, 2.3, 600, RED)); y += 3.4
    return o

def k5():
    st = plan["stars"]; n = plan["star_counts"]
    o = header("K5 · STAR FIELD — white stars all over (body, sleeves, hood, pocket)", f"{sum(n.values())} stars at size M, same star shapes and density as the Rev J back field (~{st['density_per_m2']} per m²): small satin dots + 4-point sparkles, white.", "K5")
    y = 34
    o.append(t(12, y, "Stars per piece (size M)", 2.8, 700)); y += 5
    for P in ORDER: o.append(t(12, y, B.NAMES[P], 2.4)); o.append(t(60, y, str(n[P]), 2.4, 700)); y += 4
    y += 4; o.append(t(12, y, "Layout rules (the files already follow them)", 2.8, 700)); y += 5
    k = plan["keep"]
    for r in (f"No star within {k['split']:.0f} mm of a hoop split line (so a small hooping shift never cuts or doubles a star).",
              f"No star within {k['edge']:.0f} mm of a cut edge (10 mm seam allowance + 8 mm clear) [proposed — confirm your seam allowance].",
              f"No star under the kangaroo pocket or within {k['under_pocket']:.0f} mm of where it is sewn; the pocket carries its own stars.",
              f"Hood: no star within {k['face']:.0f} mm of the face edge (turn-back) [proposed]. Pocket: {k['pocket']:.0f} mm from its cut edge.",
              f"Stars keep {k['objects']:.0f} mm away from every badge and from the hem script.",
              "Rib (hem, cuffs) is not embroidered.",
              "Please hoop oversized rough-cut blocks and recut to the pattern after embroidery, if you can (question 4)."):
        y = wrap(o, 14, y, "• " + r, 2.4, width=150); y += 1
    im, h = embed_svg_png(f"{OUT}/stitch_allover/HAKI_KCOS-PO_SR-H1_M_preview.png", 190, 32, 90)
    o.append(im); o.append(t(190, 34 + h, "Read-back render of file SR-H1 (right sleeve, top hooping)", 2.0, 400, MUTED))
    return o

def k6():
    o = header("K6 · BLOCK — EE / Come Over hoodie size chart (published) + what we assumed", "Our panel outlines are for embroidery placement only. Please cut from YOUR EE / Come Over pattern and send it to us (question 6).", "K6")
    y = 34; xs = (12, 34, 62, 90, 124)
    for x, h in zip(xs, ("Size",) + B.CHART_COLS): o.append(t(x, y, h, 2.3, 700, MUTED))
    y += 4.5
    for sz, vals in B.CHART.items():
        o.append(t(xs[0], y, sz, 2.4, 700))
        for x, v in zip(xs[1:], vals): o.append(t(x, y, f'{v}" ({v*B.IN:.0f} mm)', 2.3))
        y += 4
    o.append(t(12, y + 1, "Inches, flat. Chest = pit to pit. Sleeve = shoulder seam to cuff end. Source: Haki hoodie size chart (EE / Come Over).", 2.0, 400, MUTED)); y += 9
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
             ("K2", img_page("K2", "K2 · OVERVIEW — target look (mockup) and our size-M layout", "Mockup = look and placement only (AI render: do not copy its lettering). Layout = what the stitch files sew.",
                             MOCK, w=200, extra=None)),
             ("K3", k3()), ("K4", k4()), ("K5", k5()), ("K6", k6())]
    from pypdf import PdfWriter, PdfReader
    wr = PdfWriter()
    for k, o in pages:
        svg = tofu.check(doc(o), k); cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"{PG}/{k}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{PG}/prev_{k}.png", output_width=2000)
        wr.append(f"{PG}/{k}.pdf")
    if os.path.exists(REVJ):
        rj = PdfReader(REVJ)
        ban = doc([f'<rect x="0" y="0" width="{SB.SW}" height="9" fill="#B3261E"/>',
                   t(8, 6.2, "REFERENCE ONLY (Rev J) — stitch detail of the badges. On the pullover they sit on the BACK: placement is page K4, files are BK-H1 / BK-H3 / BK-H4.", 2.6, 700, "#FFFFFF")])
        bp = io.BytesIO(cairosvg.svg2pdf(bytestring=ban.encode())); banner = PdfReader(bp).pages[0]
        for i in (16, 17, 18, 19, 25):         # E01-E04, R1
            p = rj.pages[i]; p.merge_page(banner); wr.add_page(p)
    pdf = f"{OUT}/HAKI_KCOS-PULLOVER_RevK_{SIZE}.pdf"; wr.write(pdf)
    z = f"{OUT}/HAKI_KCOS-PULLOVER_RevK_{SIZE}_files.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(pdf, os.path.basename(pdf))
        for fp in sorted(glob.glob(f"{OUT}/stitch_allover/*")):
            if fp.endswith((".dst", ".pes", "_preview.png")): zf.write(fp, "stitch_files/" + os.path.basename(fp))
        zf.writestr("README.txt", "Keep Clean Our Space pullover hoodie, Rev K, size M.\nOne DST + PES per hooping (name = piece-hooping), plus a preview of each.\n"
                    "Pieces: FR front, BK back, PK kangaroo pocket, SR/SL sleeves, HR/HL hood sides. Hooping plan and placement: PDF pages K3-K4.\n"
                    "Other sizes are built after your answers on page K1 (your pattern, wash, hoopings).\n")
    print(pdf, z, TOT)

if __name__ == "__main__":
    build()
