"""Factory copy of a tech pack: FACTORY SUMMARY (what the factory needs to make it right the first time) + the full
pack kept as the INTERNAL copy. Generalised from Pixel Sky Rev G (rfq_text_gate, LESSONS E14) — see LESSONS E15.

A project opts in by tagging every page it builds:

    pages = [Page("T1", "cover", "Cover", FACTORY, svg), ..., Page("C1", "compare", "Compare — coin", INTERNAL, svg)]
    probs = summary_gate(pages)                       # [] = every page kind a factory needs is there, in order
    fac = factory_pages(pages)                        # the factory pages in KINDS order
    svg = scrub_svg(svg, BASE_SCRUB + project_rules)  # rewrite / drop internal wording on a factory page
    g = leak_gate(pdf_texts(factory_pdf), pdf_texts(internal_pdf), extra_patterns=[...], current_rev="Rev B8")
    assert g["ok"], g                                 # red-then-green built in: the internal copy MUST have hits

The gate reads the TEXT LAYER of the rendered PDF. Text drawn inside an embedded image (a compare PNG with a gate
table, a screenshot) is invisible to it: pages built from such images are INTERNAL by kind (compare / check / qa),
and summary_gate refuses them in the factory copy.
"""
import html
import re
from dataclasses import dataclass

FACTORY, INTERNAL = "factory", "internal"


@dataclass(frozen=True)
class Kind:
    key: str
    need: str          # what the factory gets from this page
    required: str      # "always" | "decorated" (only when the garment carries embroidery / print) | "optional"


# Order = order in the factory summary. A page kind that is not here is internal-only.
KINDS = [
    Kind("cover", "style, colourway, size range, order quantity, contents", "always"),
    Kind("flats", "front + back flats with callouts", "always"),
    Kind("measurements", "measurement chart per size + how to measure", "always"),
    Kind("pattern", "pattern / cut list (or which existing pattern to use)", "optional"),
    Kind("bom", "fabric, trims, hardware, thread colours", "always"),
    Kind("construction", "seams, stitching, assembly order, wash", "always"),
    Kind("labels_packing", "labels, trims placement, packing", "always"),
    Kind("artwork_placement", "where every embroidery / print element sits on the garment", "decorated"),
    Kind("artwork_summary", "stitch / print files + thread chart", "decorated"),
    Kind("artwork_element", "each element at a stated scale with size, stops and threads", "decorated"),
    Kind("factory_questions", "strike-off requests + open questions for the factory", "always"),
]
KIND_ORDER = {k.key: i for i, k in enumerate(KINDS)}
# Kinds that may only ever be internal: QA tables, compare sheets (often images of gate tables), decisions / Rev logs.
INTERNAL_KINDS = {"compare", "check", "qa", "decisions", "internal"}


@dataclass
class Page:
    id: str
    kind: str
    title: str
    audience: str      # FACTORY | INTERNAL
    svg: str = ""


def summary_gate(pages, decorated=True):
    """Problems with the factory page set ([] = pass): a required kind missing, an internal-only kind or an unknown
    kind tagged factory, a bad audience tag, factory pages out of KINDS order."""
    probs = []
    for p in pages:
        if p.audience not in (FACTORY, INTERNAL):
            probs.append(f"{p.id}: audience {p.audience!r} (factory | internal)")
        if p.kind not in KIND_ORDER and p.kind not in INTERNAL_KINDS:
            probs.append(f"{p.id}: unknown kind {p.kind!r}")
        if p.audience == FACTORY and p.kind in INTERNAL_KINDS:
            probs.append(f"{p.id}: kind {p.kind!r} is internal-only but tagged factory")
    fac = [p for p in pages if p.audience == FACTORY]
    have = {p.kind for p in fac}
    for k in KINDS:
        if (k.required == "always" or (k.required == "decorated" and decorated)) and k.key not in have:
            probs.append(f"missing factory page kind {k.key!r} ({k.need})")
    idx = [KIND_ORDER.get(p.kind, -1) for p in fac]
    if idx != sorted(idx):
        probs.append("factory pages out of order: " + " ".join(f"{p.id}:{p.kind}" for p in fac))
    return probs


def factory_pages(pages):
    """the factory pages, in KINDS order (stable within a kind)"""
    fac = [p for p in pages if p.audience == FACTORY]
    return sorted(fac, key=lambda p: KIND_ORDER.get(p.kind, 99))


# ---------------------------------------------------------------- leak patterns
_MON = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
# Internal wording that must never reach a factory: who decided, when, how we checked it, where our files live.
BASE_PATTERNS = [
    r"[Ff]ounder", r"\bCEO\b", r"Claude", r"\bagent\b", r"\bsession\b", r"\bPR ?#\d", r"\breviewer\b",
    r"LESSONS", r"\b[A-Z]\d{1,2} rule\b", r"\bA1\d\b", r"ENGINE_NOTES", r"\b[Ee]ngine\b",
    r"\bgates?\b", r"\bIoU\b", r"motif_match", r"centreline gate", r"read[- ]back", r"\bQA\b", r"PASS\b", r"FAIL\b",
    r"\.py\b", r"\.json\b", r"\.pkl\b", r"\binputs/", r"\bout/", r"\bprojects/",
    r"licen[cs]e risk", r"licensed character", r"\bPLM\b", r"\bpipeline\.", r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-",
    r"Generated, not traced", r"\bas before\b",
    r"\b[a-z]+_[a-z]+ [\d.]+ ?(?:->|-›|→)", r"\b\d+(?:\.\d+)?(?: mm)? ?(?:->|-›|→) ?\d",   # "name_chihiro 0.9 -> 0.85": layer ids, before -> after
    r"\b\d{1,2} " + _MON + r"\b(?! \d{4})",     # a decision date ("founder 19 Oct"); a full build date "22 Oct 2026" is fine
]


def rev_pattern(current_rev):
    """any revision name other than the current one ("Rev A", "Rev B6" when current is "Rev B8") = Rev history"""
    cur = re.escape(current_rev.split()[-1])
    return rf"\bRev (?!{cur}\b)[A-Z]\d*\b|\bfrom Rev\b|\bwas \d+\)"


def _norm(tx):
    return re.sub(r"\s+", " ", tx)


def pdf_texts(pdf):
    """text layer of each page of a rendered PDF (whitespace collapsed)"""
    from pypdf import PdfReader
    return [_norm(pg.extract_text() or "") for pg in PdfReader(pdf).pages]


def file_text(path):
    """everything a recipient can read in a file we ship: the text of .txt/.svg/.md; for .pdf/.ai the text layer PLUS the
    document info, the XMP author/title/tool fields and the PostScript '%%' header lines (Illustrator writes
    '%%For: (<user name>)' there)"""
    if not path.lower().endswith((".pdf", ".ai")):
        return open(path, encoding="utf-8", errors="replace").read()
    from pypdf import PdfReader
    r = PdfReader(path)
    meta = " ".join(f"{k} {v}" for k, v in (r.metadata or {}).items())
    raw = open(path, "rb").read().decode("latin-1")
    # XMP: the fields a person can read (author, title, tool) — not the instance uuids or the base64 thumbnail
    xmp = " ".join(re.sub(r"<[^>]+>", " ", v) for _, v in
                   re.findall(r"<((?:dc|pdf|photoshop):\w+|xmp:CreatorTool)\b[^>]*>(.*?)</\1>", raw, re.S))
    dsc = " ".join(re.findall(r"^%%\w+:.*$", raw, re.M))
    return _norm(" ".join(pdf_texts(path)) + " " + meta + " " + xmp + " " + dsc)


def strip_creator(path, who=b"Haki"):
    """overwrite the user name Illustrator / Acrobat leave in a shipped .ai / .pdf ('%%For: (Jane Doe)', /Author (...),
    XMP dc:creator) in place, padded with spaces to the same byte length so the PDF xref offsets stay valid.
    Returns how many fields changed."""
    raw = open(path, "rb").read()

    def same(m):
        n = len(m.group(2))
        return m.group(1) + (who[:n] + b" " * max(0, n - len(who))) + m.group(3)
    n = 0
    for pat in (rb"(%%For: \()([^)]*)(\))", rb"(/Author ?\()([^)]*)(\))", rb"(<dc:creator>\s*<rdf:Seq>\s*<rdf:li>)([^<]*)(</rdf:li>)"):
        raw, k = re.subn(pat, same, raw)
        n += k
    if n:
        open(path, "wb").write(raw)
    return n


def scan(texts, patterns):
    """[(page_no, pattern, snippet)] for every pattern hit; texts = one string per page (or one string)"""
    if isinstance(texts, str):
        texts = [texts]
    hits = []
    for i, tx in enumerate(texts, 1):
        tx = _norm(tx)
        for pat in patterns:
            for m in re.finditer(pat, tx):
                hits.append((i, pat, tx[max(0, m.start() - 40): m.end() + 40]))
    return hits


def leak_gate(factory_text, internal_text, extra_patterns=(), current_rev=None, patterns=None, min_chars=40, image_only=()):
    """Red-then-green text gate. The same pattern list must find hits in the INTERNAL copy (else the gate is blind —
    a typo'd pattern or an empty text layer) and none in the FACTORY copy.
    The factory side can be blind too: a page whose text layer is empty (outlined text, a page that is one image) passes
    any pattern list. Every factory page / file needs >= min_chars of text unless it is listed in image_only (1-based
    page numbers, or names when factory_text is a {name: text} dict) — list a page there only after a human read it.
    factory_text / internal_text: a string, a list of page strings (pdf_texts()) or a {name: text} dict.
    Returns dict(ok, blind, empty, factory_hits, internal_hits, factory=[...], internal_sample=[...], patterns=[...])."""
    pats = list(BASE_PATTERNS if patterns is None else patterns) + list(extra_patterns)
    if current_rev:
        pats.append(rev_pattern(current_rev))
    if isinstance(factory_text, str):
        factory_text = [factory_text]
    named = dict(factory_text) if isinstance(factory_text, dict) else {i: tx for i, tx in enumerate(factory_text, 1)}
    if isinstance(internal_text, dict):
        internal_text = list(internal_text.values())
    empty = [k for k, tx in named.items() if len(_norm(tx or "").strip()) < min_chars and k not in set(image_only)]
    if not named:
        empty = ["<no factory text at all>"]
    fh = [(k, pat, snip) for k, tx in named.items() for _, pat, snip in scan(tx or "", pats)]
    ih = scan(internal_text, pats)
    blind = not ih
    return dict(ok=not fh and not blind and not empty, blind=blind, empty=empty, factory_hits=len(fh), internal_hits=len(ih),
                factory=[list(h) for h in fh][:80], internal_sample=[list(h) for h in ih][:10], patterns=pats)


# ---------------------------------------------------------------- scrub a factory page
# (regex, replacement); replacement None = drop the whole <text> element. Applied in order to each <text>'s content.
BASE_SCRUB = [
    (r"\bfounder spec(?: \d{1,2} " + _MON + r")?", "Haki spec"),
    (r"(?i)\bconfirmed by the founder(?: \d{1,2} " + _MON + r")?", "confirmed"),
    (r"[,;]?\s*\bfounder(?: change)? \d{1,2} " + _MON + r"\b", ""),             # "shape = the 02 konpeito, founder 20 Oct"
    (r"\b(confirmed|CONFIRMED) \d{1,2} " + _MON + r"\b", r"\1"),                # "placement confirmed 19 Oct"
    (r"\s*\((?:confirmed )?(?:by the )?founder(?:'s)?[^()]*\)", ""),          # "(founder 20 Oct)", "(confirmed by the founder 21 Oct)"
    (r"\bfounder confirmed(?: \d{1,2} " + _MON + r")?", "confirmed"),
    (r"\s*\((?:confirmed )?\d{1,2} " + _MON + r"\)", ""),                      # "(19 Oct)", "(confirmed 19 Oct)"
    (r"\bread[- ]back numbers\b", "file numbers"),
    (r"\bread back from\b", "counted from"),
    (r"\(read back from the DST\)", "(from the DST)"),
    (r"\s*\(factory\.json\)", ""),
    (r"^Generated, not traced: .*", None),
    (r"^\(?(?:placement |move )?(?:confirmed|CONFIRMED)\)?\.?$", None),     # a status word alone: decision history, or the
]                                                                              # tail of a wrapped line whose head was dropped


def _tidy(s):
    s = re.sub(r"\(\s*[;:,]?\s*\)", "", s)                  # "labels ()" left by a removed "(founder 22 Oct)"
    s = re.sub(r"\(\s*[;:,]\s*", "(", s)                       # "(; care label ..." / "(: soot sprites ..."
    s = re.sub(r"\s+([,;])", r"\1", re.sub(r"  +", " ", s))
    s = re.sub(r"\s+\.(\s|$)", r".\1", s)
    s = re.sub(r"\s*[—–]\s*$", "", s)                           # "... (garment factory) — founder 19 Oct" -> no dangling dash
    return s.strip()


def scrub_text(s, rules):
    """apply the rewrite rules in order, tidying the leftovers after each one; a drop rule (replacement None) is
    tested on the raw text AND on the result, so "move CONFIRMED (founder 21 Oct)" -> "move CONFIRMED" still meets an
    anchored drop rule. None = drop the line."""
    drops = [pat for pat, rep in rules if rep is None]
    if any(re.search(p, s) for p in drops):
        return None
    for pat, rep in rules:
        if rep is not None:
            s = _tidy(re.sub(pat, rep, s))
    if any(re.search(p, s) for p in drops):
        return None
    return s if s and s not in ".,;:" else None


def scrub_svg(svg, rules):
    """rewrite the text of every <text> element with rules; a rule with replacement None drops the element.
    Only <text> content changes: geometry, images and layout stay as built."""
    def one(m):
        inner = m.group(2)
        if "<" in inner:                       # tspans etc.: leave to the gate
            return m.group(0)
        out = scrub_text(html.unescape(inner), rules)
        return "" if out is None else m.group(1) + html.escape(out, quote=False) + m.group(3)
    return re.sub(r"(<text\b[^>]*>)(.*?)(</text>)", one, svg, flags=re.S)
