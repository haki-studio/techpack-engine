"""Konpeito jeans — FACTORY SUMMARY + factory reference zip + INTERNAL copy from one build (engine/factory_copy.py,
LESSONS E15). Run after kjstitch / kjsoot / kjcompare (it calls kjpages.build twice: factory pages, then the full pack).

  out/Konpeito jeans - <REV> - FACTORY SUMMARY.pdf     what the factory needs to make it right the first time
  out/Konpeito jeans - <REV> - FACTORY REFERENCE.zip   stitch files, 1:1 previews, thread charts, art, labels, README
  out/Konpeito jeans - <REV> - INTERNAL.pdf            the full pack: compare sheets, QA tables, decisions log
  out/factory/leak_gate.json                           red-then-green text gate on the rendered PDFs + README
"""
import os, json, shutil, subprocess, zipfile
import cairosvg
from pypdf import PdfWriter, PdfReader
import factory_copy as FC
from factory_copy import Page, FACTORY, INTERNAL
import kjpages as P
from kjcore import REV, SIZES
import sheet
from sheet import t, INK, MUTED

FOUT = "out/factory"
TITLE = "Konpeito jeans"
SUMMARY = f"out/{TITLE} - {REV} - FACTORY SUMMARY.pdf"
REFZIP = f"out/{TITLE} - {REV} - FACTORY REFERENCE.zip"
INTERNAL_PDF = f"out/{TITLE} - {REV} - INTERNAL.pdf"

# every page kjpages builds, tagged (kind, audience). A new page in kjpages without a row here fails the build.
TAGS = {"T1": ("cover", FACTORY), "T2": ("flats", FACTORY), "T3": ("measurements", FACTORY), "T4": ("pattern", FACTORY),
        "T5": ("bom", FACTORY), "T6": ("construction", FACTORY), "T7": ("labels_packing", FACTORY), "T7b": ("labels_packing", FACTORY),
        "T8": ("artwork_placement", FACTORY), "G1": ("artwork_summary", FACTORY),
        **{g: ("artwork_element", FACTORY) for g in ("G2", "G3", "G4", "G5", "G7")},
        "G6": ("internal", INTERNAL), "G6b": ("internal", INTERNAL),        # folded into the factory G5 (back_pockets)
        **{c: ("compare", INTERNAL) for c in ("C1", "C2", "C3", "C4", "C5", "C6", "C7")},
        "F1": ("factory_questions", FACTORY), "Q1": ("decisions", INTERNAL)}

TITLES = {"T1": "Cover + contents", "T2": "Flats — front + back", "T3": "Measurements per size (factory fills the blue cells)",
          "T4": "Pattern — your HI pants pattern, minus cargo", "T5": "Bill of materials — fabric, trims, hardware", "T6": "Construction, stitching + wash",
          "T7": "Labels + trims placement", "T7b": "Label artwork — main, care + size labels", "T8": "Embroidery placement on the jean",
          "G1": "Embroidery files + thread chart", "G2": "01 Coin-pocket patch こんぺいとう", "G3": "02 Konpeito spill (facing)",
          "G4": "03 Waistband patch ちひろ note", "G5": "04 / 05 / 06 Back pockets — 'haki' + konpeito", "G7": "07 Front-leg trail — konpeito + soot sprites", "F1": "Strike-off, threads + our requests"}

from kjfactory_words import EXTRA, KJ_SCRUB      # data-free, so tests/test_konpeito_factory_words.py runs in a fresh checkout


def tagged(pages):
    miss = [pid for pid, *_ in pages if pid not in TAGS]
    assert not miss, f"kjfactory.TAGS has no row for {miss}: tag every new page factory / internal"
    return [Page(pid, TAGS[pid][0], TITLES.get(pid, title), TAGS[pid][1], svg) for pid, title, svg, _ in pages]


def cover(fac):
    """T1 for the factory: contents = the factory pages only, plus the order block"""
    index = [(p.id, p.title, "") for p in fac]
    flags = {"T5": "hang tag art; packing design; barcodes", "T7": "hang tag art"}
    index = [(pid, ttl, flags.get(pid, "")) for pid, ttl, _ in index]
    o = P.T1(index)
    y = 60 + len(index) * 3.55 + 3 + 4 + 4 * 3.6 + 8
    o.append(t(176, y, "ORDER", 2.8, 700)); y += 5
    for ln in ["Colourway: washed black (one colourway).", "Sizes (waist): " + " ".join(SIZES) + ".",
               "Quantity per size: on the purchase order.", "Strike-off + fit sample before bulk (F1)."]:
        o.append(t(176, y, ln, 1.95, 400, INK)); y += 3.6
    assert y <= sheet.SH - 12, ("factory cover runs into the footer", y)
    return P.page(o)


def back_pockets():
    """factory G5: the three back-pocket files (04 'haki' group, 05 pink + 06 yellow konpeito) on one page — the internal
    pack gives each its own page with QA panels; the factory needs preview, size, stops and placement."""
    from sheet import dim_h, dim_v
    o = P.hdr("G5 · 04 / 05 / 06 BACK POCKETS — 'haki' + konpeito", "direct embroidery on the cut back pockets, before hemming / attaching; tearaway backing · "
              f"{REV} · {P.DATE} · finished size, mm · every konpeito = the 02 shape, 10 mm (one satin per lobe, tint lobes on top, 3 white Ø0.9 dots)", "G5")
    w_haki = P.RB["haki"]["size_mm"][0] - 2 * 10 - 8
    cols = [("haki", "04", "Back pocket L — 'haki' + 2 konpeito", 1.0,
             [f"Wearer's LEFT back pocket. Yellow-konpeito centre {P.HAKI_POS[0]:.0f} mm in from the pocket's outer edge, {P.HAKI_POS[1]:.0f} mm below the pocket top edge (T8).",
              f"'haki' ~{w_haki:.0f} mm wide, 2 mm light-blue satin strokes; lettering thread = Blue tint #8ED2EE  [proposed — confirm].",
              "Konpeito 10 mm, yellow + blue, the 02 shape."]),
            ("starP", "05", "Back pocket R — pink konpeito", 4.0,
             [f"Wearer's RIGHT back pocket. Centre {P.STARP_POS[0]:.0f} mm in from the outer edge, {P.STARP_POS[1]:.0f} mm below the top edge: clears the outer topstitch (T8).",
              "Pink konpeito 10 mm, the 02 shape (not a 5-point star)."]),
            ("starY", "06", "Back pocket L — lower yellow konpeito", 4.0,
             [f"Wearer's LEFT back pocket, lower outer corner. Centre {P.STARY_POS[0]:.0f} mm in from the outer edge, {P.STARY_POS[1]:.0f} mm above the lower corner (T8).",
              "Yellow konpeito 10 mm, the 02 shape. Hoop on the file centre = the placement point."])]
    stem = {k: s_ for k, *_, s_ in P.EL}
    for i, (k, no, title, sc, notes) in enumerate(cols):
        x = 12 + i * 92; rb = P.RB[k]; wmm, hmm = rb["size_mm"]
        o.append(t(x, 32, f"{no} · {title}", 2.4, 700))
        o.append(t(x, 36.5, f"{stem[k]}.dst / .pes", 1.7, 400, MUTED))
        o.append(t(x, 42, f"A · STITCH PREVIEW from the DST, {'1 : 1' if sc == 1 else f'{sc:.0f} : 1'}", 1.9, 700))
        tag, h = P.img(f"out/stitch/{stem[k]}_preview.png", x, 44, w=(wmm + 4) * sc); o.append(tag)
        o.append(dim_h(x + 2 * sc, x + (wmm + 2) * sc, 44 + h + 4, f"{wmm:.1f}", 1.9))
        o.append(dim_v(44 + 2 * sc, 44 + (hmm + 2) * sc, x + (wmm + 4) * sc + 4, f"{hmm:.1f}", 1.9, side=1))
        y = 44 + max(h, 48) + 10
        o.append(t(x, y, "B · FILE", 1.9, 700)); y += 4
        for a, b in [("Stitches", f"{rb['stitches']:,}"), ("Trims", str(rb["trims"])), ("Colour stops / threads", f"{rb['stops']} / {rb['threads']}"),
                     ("Design size", f"{wmm:.1f} × {hmm:.1f} mm"), ("Machine time", f"{rb['machine_min']} min / piece")]:
            o.append(t(x, y, a, 1.8, 400, MUTED)); o.append(t(x + 34, y, b, 1.8, 700)); y += 3.6
        y += 1
        st, y = P.stop_table(rb, x, y); o.append(st)
        y += 5; o.append(t(x, y, "C · PLACEMENT + NOTES", 1.9, 700)); y += 4
        for n_ in notes:
            for ln in P.wrap(n_, 62):
                o.append(t(x, y, ln, 1.75, 400, P.AMBER if "proposed" in ln else INK)); y += 3.1
            y += 0.8
        assert y <= sheet.SH - 12, ("back_pockets column runs into the footer", no, y)
    return P.page(o)


def render(pages, out, tag):
    os.makedirs(FOUT, exist_ok=True)
    for fn in os.listdir(FOUT):
        if fn.startswith((f"{tag}_", f"prev_{tag}_")): os.remove(f"{FOUT}/{fn}")      # no stale pages from an earlier page set
    w = PdfWriter()
    for p in pages:
        pdf = f"{FOUT}/{tag}_{p.id}.pdf"
        cairosvg.svg2pdf(bytestring=p.svg.encode(), write_to=pdf)
        cairosvg.svg2png(bytestring=p.svg.encode(), write_to=f"{FOUT}/prev_{tag}_{p.id}.png", output_width=2000)
        w.append(PdfReader(pdf))
    w.write(out)
    return out


def shrink(pdf):
    small = pdf.replace(".pdf", "_s.pdf")
    subprocess.run(["python3", "shrink.py", pdf, small, "2400", "82"], check=True)
    os.replace(small, pdf)


README = """HAKI STUDIOS — {name} ({style}) — {rev}, {date}

{summary}
  The tech pack for this jean: flats, measurements, materials, construction + wash, labels,
  embroidery placement, every embroidery element and our requests (F1).

elements/<no>_<name>/  per embroidery element:
  *.dst *.pes            production stitch files (12 threads or fewer each; numbers on G1 come from these files)
  *_PREVIEW.png          stitch preview drawn from the DST
  *_PREVIEW_1to1.pdf     the preview at 1 : 1 (print at 100 %, 50 mm check bar)
  THREAD_CHART.txt       per stop: thread, hex, Madeira Polyneon / Isacord match, stitches, trims
  ART.svg / ART.png      region art, one group per colour stop, 1 SVG unit = 1 mm
elements/SPEC_G*.pdf     the element pages from the summary (G2-G7)
labels/                  size labels (one SVG + one PDF per size, 1:1), main label 65 x 20 mm, care label 30 x 65 mm
                         (care -white.pdf = the one to make). The care label prints MADE IN CHINA: change it if made elsewhere.

Files:
{files}

Sizes (waist): {sizes}. Measurements: T3; back rise, thigh, knee and outseam from your Hidden Inventory spec (blue cells).
Pattern: your Hidden Inventory pants pattern, cargo pockets removed, 5-pocket jean construction (T4).
Legend: [proposed - confirm] = please confirm or correct; [MISSING] = Haki still owes it (hang tag art, packing
design, barcode per size: to follow).
Strike-off of every stitch file on the washed production denim / patch twill before bulk (F1).
"""


def reference_zip(fac_pdfs):
    """factory reference zip from kjpages.package's tree: internal pack + README swapped for the factory ones"""
    src, pkg = "out/pkg", f"{FOUT}/pkg"
    shutil.rmtree(pkg, ignore_errors=True); shutil.copytree(src, pkg)
    for fn in os.listdir(pkg):
        if fn.endswith(".pdf") or fn == "README.txt": os.remove(f"{pkg}/{fn}")
    for fn in os.listdir(f"{pkg}/elements"):
        if fn.startswith("SPEC_"): os.remove(f"{pkg}/elements/{fn}")
    for pid, pdf in fac_pdfs.items():
        if pid.startswith("G") and pid != "G1": shutil.copy(pdf, f"{pkg}/elements/SPEC_{pid}.pdf")
    shutil.copy(SUMMARY, pkg)
    files = "\n".join(f"  {no:<4} {stem}  {P.RB[k]['stitches']:,} st  {P.RB[k]['trims']} trims  {P.RB[k]['threads']} threads  {title}"
                      for k, no, title, *_, stem in P.EL)
    rd = README.format(name=P.NAME, style=P.STYLE, rev=REV, date=P.DATE, summary=os.path.basename(SUMMARY), files=files, sizes=" ".join(SIZES))
    open(f"{pkg}/README.txt", "w").write(rd)
    texts = {}
    for r, _, fs in os.walk(pkg):
        for f_ in fs:
            p = os.path.join(r, f_)
            if f_.endswith((".pdf", ".ai")): FC.strip_creator(p)       # Illustrator's "%%For: (<user name>)"
            if f_.endswith((".txt", ".svg", ".pdf", ".ai")): texts[os.path.relpath(p, pkg)] = FC.file_text(p)
    if os.path.exists(REFZIP): os.remove(REFZIP)
    with zipfile.ZipFile(REFZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, fs in os.walk(pkg):
            for fn in fs:
                p = os.path.join(root, fn); zf.write(p, os.path.relpath(p, pkg))
    return texts


def build():
    # 1 · factory pages: element pages without the QA panels, every page scrubbed
    P.FACTORY = True
    P.build()
    pages = tagged(P.PAGES)
    probs = FC.summary_gate(pages)
    assert not probs, probs
    fac = FC.factory_pages(pages)
    rules = FC.BASE_SCRUB + KJ_SCRUB
    for p in fac:
        if p.id == "G5": p.svg = back_pockets()
        p.svg = FC.scrub_svg(cover(fac) if p.kind == "cover" else p.svg, rules)
    render(fac, SUMMARY, "fac")
    fac_pdfs = {p.id: f"{FOUT}/fac_{p.id}.pdf" for p in fac}
    # 2 · internal: the full pack, as built today (QA panels, compare sheets, decisions)
    P.FACTORY = False
    final = P.build()
    shutil.copy(final, INTERNAL_PDF)
    P.package(final)
    shrink(SUMMARY); shrink(INTERNAL_PDF)          # the gate reads the files we ship, so it runs after the shrink
    # 3 · leak gate on the rendered text (red-then-green: the internal copy must have hits; every factory page has text)
    internal = FC.pdf_texts(INTERNAL_PDF)
    g = FC.leak_gate(FC.pdf_texts(SUMMARY), internal, EXTRA, current_rev=REV)
    for h in g["factory"]: print("LEAK:", h)
    assert not g["blind"], "leak gate found nothing in the INTERNAL copy — the gate is blind"
    assert not g["empty"], f"factory summary pages with no text layer (the gate cannot read them): {g['empty']}"
    assert g["ok"], f"leak gate: {g['factory_hits']} internal strings in the factory summary"
    # 4 · reference zip (stitch files, previews, labels): every shipped file's text + metadata through the same gate
    texts = reference_zip(fac_pdfs)
    gz = FC.leak_gate(texts, internal, EXTRA, current_rev=REV)
    for h in gz["factory"]: print("ZIP LEAK:", h)
    assert not gz["empty"], f"reference zip files with no readable text: {gz['empty']}"
    assert gz["ok"], f"leak gate: {gz['factory_hits']} internal strings in the reference zip"
    json.dump(dict(summary=os.path.basename(SUMMARY), pages=[[p.id, p.kind, p.title] for p in fac],
                   internal_pages=[[p.id, p.kind] for p in pages if p.audience == INTERNAL],
                   summary_gate=probs, leak_gate={k: v for k, v in g.items() if k != "patterns"},
                   zip_leak_gate={k: v for k, v in gz.items() if k not in ("patterns", "internal_sample")}, zip_files=sorted(texts),
                   patterns=g["patterns"]),
              open(f"{FOUT}/leak_gate.json", "w"), indent=1, ensure_ascii=False)
    print(f"FACTORY SUMMARY {len(fac)} pages: {SUMMARY} ({os.path.getsize(SUMMARY) // 1024} kB)")
    print(f"leak gate ok: 0 in the factory copy, {g['internal_hits']} in the internal copy; zip text 0 hits")
    print(f"zip gate read {len(texts)} files (text + metadata)")
    print("reference zip", REFZIP, os.path.getsize(REFZIP) // 1024, "kB; internal", INTERNAL_PDF)


if __name__ == "__main__":
    build()
