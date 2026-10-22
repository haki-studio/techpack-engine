"""Koi blossom factory-copy settings on top of fc_shim (= engine/factory_copy.py, Konpeito): the Koi-only leak patterns
and scrub rules, and check() over rendered PDFs. Kept free of build imports so tests can load it."""
import fc_shim as FC

REV = "Rev D"                        # = kbcore.REV (not imported here: kbcore pulls in the engine)
# names / sources that are internal for THIS product (another product, people, our build steps)
EXTRA = [r"Drum Island", r"Mandy", r"\bSteph\b", r"\bNick\b", r"\bDevin\b", r"\b[Kk]oi\b(?!-)", r"AI close-up", r"AI mockup",
         r"factory\.json", r"\btrace/", r"REVIEW_OPEN", r"\bfidelity\b", r"\bTD\b", r"\bchair\b"]
# (regex, replacement | None = drop the text element): run BEFORE fc_shim.BASE_SCRUB on block / engine pages we don't own
SCRUB = [(r"\(founder 22 Oct 2026\)", "(Haki Studios, 22 Oct 2026)"), (r"founder decision 19 Oct 2026, ", ""),
         (r"FOUNDER DECISION 19 Oct", "confirmed"),
         (r"the approved Drum Island jacket chart", "the approved jacket chart"), (r"approved Drum Island chart", "approved jacket chart"),
         (r"exactly as the Drum Island jacket", "as the approved Haki jacket block (pattern T4)"),
         (r"the approved Drum Island jacket", "the approved Haki jacket block"), (r"Drum Island jacket", "Haki jacket block"), (r"Drum Island", "Haki jacket"),
         (r"\(factory\.json(, PROPOSED)?\)", "(proposed — confirm)"), (r"factory\.json(, PROPOSED)?", "proposed — confirm"),
         (r"factory\.machine_hours ?", ""), (r" ?\(LESSONS [A-Z]\d+(/[A-Z]?\d+)*\)", ""), (r"LESSONS [A-Z]\d+", ""),
         (r" ?\(fidelity\.py\)", ""), (r", split in the DST by fidelity\.py", ""), (r"\(counted on the mockup, A2\)", "(counted on the mockup)"),
         (r" ?\(reference_fish\.png[^)]*\)?", ""), (r"from reference_fish\.png", "from the fish reference"),
         (r"\(size M, DST read-back\)", "(size M, from the DST)"), (r"\(DST read-back\)", "(from the DST)"),
         # engine/factory.requests_page (F1) words the hooping count as "art W x H mm → N hoopings today", which reads as a
         # before -> after note to FC's history pattern; engine fix requested in ENGINE_NOTES.md (Rev D), narrow rule until then
         (r"(\d+ x \d+ mm) ?→ ?(\d+) hoopings today", r"\1: \2 hoopings on the proposed frame")]
RULES = SCRUB + FC.BASE_SCRUB

def scrub(svg): return FC.scrub_svg(svg, RULES)

IMAGE_ONLY = ()                      # factory pages exempt from min_chars (pure images, read by a human) — none in Rev D

def check(factory_pdfs, internal_pdf):
    """{pdf: leak_gate dict} for every SHIPPED factory PDF against the internal copy: each page's text layer (min_chars
    per page) + FC.file_text (text + document info + XMP + '%%' header fields). ok = 0 factory hits, no empty page,
    > 0 internal hits, for every PDF"""
    it = FC.file_text(internal_pdf)
    res = {}
    for p in factory_pdfs:
        ft = {f"p{i}": tx for i, tx in enumerate(FC.pdf_texts(p), 1)}; ft["file"] = FC.file_text(p)
        res[p] = FC.leak_gate(ft, it, extra_patterns=EXTRA, current_rev=REV, image_only=IMAGE_ONLY)
    return dict(ok=all(g["ok"] for g in res.values()), gates=res)

def meta_names(pdf):
    """/Author + /Creator of a shipped PDF (must hold no person's name after FC.strip_creator)"""
    from pypdf import PdfReader
    m = PdfReader(pdf).metadata or {}
    return {k: str(m.get(k, "")) for k in ("/Author", "/Creator")}
