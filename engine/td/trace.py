"""Numeral-trace gate (design §1): a TD document fails if any numeral on it does not trace to a file.

Two halves, both must pass:
  1. RESOLVE every number in the TD input: a file+cell / measured_from_file source must name a real file whose cell holds
     that value. A photo estimate mislabelled file+cell fails here (its ref is a photo, or the cell holds another value).
  2. TRACE every numeral printed on the rendered output (the comment sheet pages, and the TD notes band of each annotated
     pack page) to a RESOLVED input number, or a number the engine computed from them (a PATTERN change = target -
     baseline). A numeral a TD typed into free text (comment / method / location / point) fails.

Cell references (ref = "<file>#<cell>", file relative to the repo root, else to the TD json's folder):
  .csv              A1 notation: "E2" = column E, row 2 (row 1 = the header line)
  .json .yaml .yml  dotted key path: "pom_chart.base.poms.B.tol", list items by index ("rows.3.value");
                    {value: x} / {proposed: x} leaves are read as x
  "@in" / "@cm" / "@mm" after the cell = the file holds that unit ("...poms.B.values.2@in"); the cell is converted to the
                    row's unit and must equal the row's value to the precision the TD wrote (57.8 cm ← 22 3/4 in).
  anything else (.xlsx, .dxf, .pdf, a photo) cannot be read -> FAIL, never a skip. measured_from_file refs point at the
  engine's measurement OUTPUT (a json/csv written by an engine script), not at the DXF/PDF itself.

NOT yet covered (scope 2026-10-22: tables + callouts = the TD sheet and the TD notes band):
  - the rest of each pack page (the engine's own tables/flats; they are built from the spec, not from TD input);
  - numerals inside raster images, and text drawn as paths;
  - inch fractions written in free text ("1/2") are split into numerals and fail unless they trace.

  rep = trace.check(td, svgs, root)          # svgs = comment sheet pages + annotated pages
  rep.ok, rep.failures, rep.summary()
"""
import json, os, re
from fractions import Fraction
from .schema import TDInputError

MM_PER = {"in": 25.4, "cm": 10.0, "mm": 1.0}
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
NUMERAL = re.compile(r"\d+(?:\.\d+)?")
TEXT = re.compile(r"<text\b[^>]*>(.*?)</text>", re.S)
NOTES = re.compile(r'<g data-td="notes">(.*?)</g>', re.S)
OVERFLOW = re.compile(r"\+ \d+ more lines — see the TD comment sheet")      # engine-counted, not a measurement
PAGE_CODE = re.compile(r"\b[A-Z]\d+(?:_\d+)?\b")


class TraceError(TDInputError):
    """the numeral-trace gate failed — the message lists every number that does not trace"""


class Report:
    def __init__(self):
        self.failures, self.resolved, self.numerals, self.pages = [], [], 0, 0

    @property
    def ok(self): return not self.failures

    def summary(self):
        head = (f"numeral trace: {len(self.resolved)} input numbers resolved to files, {self.numerals} numerals checked "
                f"on {self.pages} page(s)")
        return head + (" — PASS" if self.ok else f" — FAIL ({len(self.failures)}):\n  " + "\n  ".join(self.failures))


# ----------------------------------------------------------------------------- 1. resolve
def _a1(cell):
    m = re.fullmatch(r"([A-Z]+)(\d+)", cell.strip().upper())
    if not m: raise ValueError(f"'{cell}' is not an A1 cell (e.g. E2)")
    col = 0
    for ch in m.group(1): col = col * 26 + ord(ch) - 64
    return int(m.group(2)) - 1, col - 1


def _number(x):
    if isinstance(x, dict):
        for k in ("value", "proposed"):
            if k in x: return _number(x[k])
        raise ValueError("cell is a table, not a value")
    if isinstance(x, bool) or x is None: raise ValueError(f"cell holds {x!r}, not a number")
    if isinstance(x, (int, float)): return float(x)
    s = str(x).strip()
    try:
        return float(sum((Fraction(p) for p in s.split()), Fraction(0)))     # '22 3/4', '26.5'
    except (ValueError, ZeroDivisionError):
        raise ValueError(f"cell holds {s!r}, not a number")


def read_cell(path, cell):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        import csv
        r, c = _a1(cell)
        rows = list(csv.reader(open(path, newline="")))
        if r >= len(rows) or c >= len(rows[r]): raise ValueError(f"cell {cell} is outside the sheet ({len(rows)} rows)")
        return _number(rows[r][c])
    if ext in (".json", ".yaml", ".yml"):
        if ext == ".json": node = json.load(open(path))
        else:
            import yaml
            node = yaml.safe_load(open(path))
        for k in cell.split("."):
            if isinstance(node, list):
                if not k.isdigit() or int(k) >= len(node): raise ValueError(f"'{k}' is not an item of a {len(node)}-item list")
                node = node[int(k)]
            elif isinstance(node, dict) and k in node: node = node[k]
            else: raise ValueError(f"key '{k}' not found")
        return _number(node)
    raise ValueError(f"cannot read a {ext or 'extension-less'} file as cells (export it to CSV, or write the engine's "
                     f"measurement output as json/csv)")


def _decimals(v):
    s = f"{round(float(v), 4):g}"
    return len(s.split(".")[1]) if "." in s else 0


def resolve(n, roots):
    """None when the number holds in its file, else the reason it does not"""
    if n.is_photo: return None
    fpart, _, cell = n.ref.partition("#")
    cell, _, cunit = cell.partition("@")
    path = next((os.path.join(r, fpart) for r in roots if os.path.isfile(os.path.join(r, fpart))), None)
    if path is None: return f"file '{fpart}' not found (looked in {', '.join(roots)})"
    try:
        got = read_cell(path, cell)
    except (ValueError, OSError) as e:
        return f"{fpart}#{cell}: {e}"
    if cunit:
        if cunit not in MM_PER: return f"unit @{cunit} — use @in, @cm or @mm"
        got = got * MM_PER[cunit] / MM_PER[n.unit]
    tol = 0.5 * 10 ** -_decimals(n.value) + 1e-9 if cunit else 1e-9
    if abs(got - float(n.value)) > tol:
        return f"{fpart}#{cell} holds {got:g}{f' {n.unit} (converted from {cunit})' if cunit else ''}, the row says {n.value:g}"
    return None


# ----------------------------------------------------------------------------- 2. trace
def _key(x): return f"{round(abs(float(x)), 4):g}"


def _strip_meta(s, td):
    """remove text that is an identifier, not a measurement: refs, ids, product/round/rev, sizes, page codes"""
    s = OVERFLOW.sub(" ", s)
    lits = [r.raw.get("ref") for r in td.rows] + [n.ref for r in td.rows for n in r.nums()] + [r.id for r in td.rows] + \
           [td.product, td.round, f"Rev {td.rev}", f"Rev {td.supersedes}" if td.supersedes else None]
    for lit in sorted({str(x) for x in lits if x}, key=len, reverse=True): s = s.replace(lit, " ")
    for size in {r.size for r in td.rows if r.size}: s = re.sub(rf"(?<![\w.]){re.escape(str(size))}(?![\w.])", " ", s)
    return PAGE_CODE.sub(" ", s)


def check(td, svgs, roots=None):
    """run both halves; returns a Report (never raises on a failure — use enforce() for that)"""
    roots = roots or [ROOT] + ([os.path.dirname(os.path.abspath(td.path))] if td.path else [])
    rep = Report()
    ok = set()
    for r in td.rows:
        for n in r.nums():
            why = resolve(n, roots)
            if why: rep.failures.append(f"{n.where} ({n.source} {n.ref}): {why}")
            else:
                if not n.is_photo: rep.resolved.append(n)
                ok.add(_key(n.value))
        nums = r.nums()
        if nums and all(resolve(n, roots) is None for n in nums):
            if r.change() is not None: ok.add(_key(r.change()))
            if r.target_value() is not None: ok.add(_key(r.target_value()))
    for svg in svgs:
        scoped = NOTES.findall(svg) if "data-td=\"notes\"" in svg else [svg]
        if not scoped: continue
        rep.pages += 1
        for part in scoped:
            for raw in TEXT.findall(part):
                text = re.sub(r"<[^>]+>", "", raw)
                for m in NUMERAL.finditer(_strip_meta(text, td)):
                    rep.numerals += 1
                    if _key(m.group()) not in ok:
                        rep.failures.append(f"numeral {m.group()} in \"{text.strip()}\" does not trace to a resolved input number")
    if rep.pages == 0: rep.failures.append("nothing to check: no comment sheet page and no TD notes band were given")
    return rep


def enforce(td, svgs, roots=None):
    rep = check(td, svgs, roots)
    if not rep.ok: raise TraceError(rep.summary())
    return rep
