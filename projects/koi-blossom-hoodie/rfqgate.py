"""Koi blossom factory-copy settings on top of fc_shim (= engine/factory_copy.py, Konpeito): the Koi-only leak patterns
and scrub rules, and check() over rendered PDFs. Kept free of build imports so tests can load it."""
import fc_shim as FC

REV = "Rev F"                        # = kbcore.REV (not imported here: kbcore pulls in the engine)
# names / sources that are internal for THIS product (another product, people, our build steps)
EXTRA = [r"Drum Island", r"Mandy", r"\bSteph\b", r"\bNick\b", r"\bDevin\b", r"\b[Kk]oi\b(?!-)", r"AI close-up", r"AI mockup",
         r"factory\.json", r"\btrace/", r"REVIEW_OPEN", r"\bfidelity\b", r"\bTD\b", r"\bchair\b",
         r"\.(png|jpe?g|py|json|pkl)\b"]       # any of our file names ("ref.png"): the shim's base list only has .py / .json / .pkl after a word
# (regex, replacement | None = drop the text element): run BEFORE fc_shim.BASE_SCRUB on block / engine pages we don't own
SCRUB = [(r"\(founder 22 Oct 2026\)", "(Haki Studios, 22 Oct 2026)"), (r"founder decision 19 Oct 2026, ", ""),
         (r"FOUNDER DECISION 19 Oct", "confirmed"),
         # a new factory has no "approved jacket block" of ours: say our block, as supplied in the DXF (td-chair C-08)
         (r"(?:the )?approved Drum Island jacket chart", "our block's chart (DXF)"), (r"(?:the )?approved Drum Island chart", "our block's chart (DXF)"),
         (r"exactly as the Drum Island jacket", "as our block (DXF, pattern T4)"),
         (r"the approved Drum Island jacket", "our block (DXF)"), (r"Drum Island jacket", "our block (DXF)"), (r"Drum Island", "our block"),
         (r"\(factory\.json(, PROPOSED)?\)", "(proposed — confirm)"), (r"factory\.json(, PROPOSED)?", "proposed — confirm"),
         (r"factory\.machine_hours ?", ""), (r" ?\(LESSONS [A-Z]\d+(/[A-Z]?\d+)*\)", ""), (r"LESSONS [A-Z]\d+", ""),
         (r" ?\(fidelity\.py\)", ""), (r", split in the DST by fidelity\.py", ""), (r"\(counted on the mockup, A2\)", "(counted on the mockup)"),
         (r" ?\(reference_fish\.png[^)]*\)?", ""), (r"from reference_fish\.png", "from the fish reference"),
         (r"\(size M, DST read-back\)", "(size M, from the DST)"), (r"\(DST read-back\)", "(from the DST)"),
         # engine/factory.requests_page (F1) words the hooping count as "art W x H mm → N hoopings today", which reads as a
         # before -> after note to FC's history pattern; engine fix requested in ENGINE_NOTES.md (Rev D), narrow rule until then
         # C-07: F1 sizes are the stitch-file box (E0 / E01 print the art box, up to 1 mm smaller): say which
         (r"(?:art )?(\d+ x \d+ mm) ?→ ?(\d+) hoopings today", r"stitch-file box \1: \2 hoopings on the proposed frame")]
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

# ---------------------------------------------------------------- one embroidery method everywhere (td-chair C-01, Rev F)
# E0 says: embroider an OVERSIZED BLOCK of shell, then re-cut. A factory page that still tells them to embroider / hoop /
# mark the CUT panel (or cut sleeve / cut front) contradicts it. Sentence-level: an embroidery verb + "cut <panel|sleeve|front>".
# E0's own contrast sentences ("not the cut panel", "a cut panel has nothing to clamp") are the method, not a contradiction.
import re as _re
METHOD = "oversized block"
CUT_RX = _re.compile(r"\bcut\s+(?:[\w+/]+\s+){0,3}?(?:panels?|sleeves?|fronts?)\b", _re.I)
VERB_RX = _re.compile(r"\b(?:embroider\w*|hoop\w*|chalk\w*|mark\w*|direct embroidery)\b", _re.I)
CONTRAST = ("not the cut panel", "nothing to clamp")

def method_hits(texts):
    """sentences in factory text that put the embroidery on a CUT panel while the method (E0) is the oversized block;
    [] when no text names the oversized-block method (then there is nothing to contradict)"""
    flat = [" ".join(t_.split()) for t_ in texts]
    if not any(METHOD in t_.lower() for t_ in flat): return []
    hits = []
    for t_ in flat:
        for sent in _re.split(r"(?<=[.;])\s+|•", t_):
            if CUT_RX.search(sent) and VERB_RX.search(sent) and not any(c in sent.lower() for c in CONTRAST):
                hits.append(sent.strip()[:160])
    return hits

def method_gate(factory_pdfs):
    """{pdf: [contradicting sentences]} over the SHIPPED factory PDFs (all pages of all PDFs read together: the method
    is stated on E0 in the summary and on the element pages in the techpack)"""
    texts = {p: FC.pdf_texts(p) for p in factory_pdfs}
    allt = [x for v in texts.values() for x in v]
    if not any(METHOD in " ".join(x.split()).lower() for x in allt): return {p: [] for p in factory_pdfs}
    return {p: method_hits([METHOD] + v) for p, v in texts.items()}

def meta_names(pdf):
    """/Author + /Creator of a shipped PDF (must hold no person's name after FC.strip_creator)"""
    from pypdf import PdfReader
    m = PdfReader(pdf).metadata or {}
    return {k: str(m.get(k, "")) for k in ("/Author", "/Creator")}
