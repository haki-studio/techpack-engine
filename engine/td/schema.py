"""TD input JSON: one file per review event, written by td-generalist / td-chair, read by the engine.

  {"product": "pixel-sky-fleece", "round": "fit sample round 2", "rev": "C", "supersedes": "B",
   "rows": [ {row}, ... ]}

Every row:
  id        unique finding id (the chair merges by id)
  kind      pom | delta | tolerance | comment
  point     the point of measure / area ("front rise", "side seam")
  lens      fit | make | spec | chair          (which checklist the finding came from)
  severity  high | medium | low
  hold      true = HOLD (do not change); only pom rows can be held
  page      optional pack page code ("T3") -> a "TD: ..." annotation on that page
  size      optional size ("M")
  comment   optional words (no numbers: every number is a field with a source)

A NUMBER is never bare: it carries where it came from.
  value, unit (cm | mm), source, ref       on the row itself (pom / tolerance / comment value; delta = the change)
  baseline: {value, unit, source, ref}     delta only: last measured sample (round N, post-wash) or the POM chart
  target:   {value, unit, source, ref}     delta only: the value the pattern should give
  source    file+cell          ref = "<file>#<cell>" (a cell / key path in a generated or received file)
            measured_from_file ref = "<file>#<what was measured>" (a pattern DXF, a 1:1 PDF ...)
            photo_estimate     ref = the photo id; renders "approx., from photo, not a measurement" and is REFUSED in
                               any PATTERN-change (delta) row, on any of its numbers (design §1)
A delta row is a PATTERN change; the engine computes the change (target - baseline) — a TD never types it twice.
Old agent rows ({"kind", "point", "value", "unit", "source", "ref"}) still need id, lens and severity added.
"""
import json

KINDS = ("pom", "delta", "tolerance", "comment")
SOURCES = ("file+cell", "measured_from_file", "photo_estimate")
LENSES = ("fit", "make", "spec", "chair")
SEVERITIES = ("high", "medium", "low")
UNITS = ("cm", "mm")
PHOTO = "approx., from photo, not a measurement"


class TDInputError(ValueError):
    """a TD input file is wrong — the message names the row and the field to fix"""


class Num:
    """one number with its provenance"""
    __slots__ = ("value", "unit", "source", "ref", "where")

    def __init__(self, value, unit, source, ref, where):
        self.value, self.unit, self.source, self.ref, self.where = value, unit, source, ref, where

    @property
    def is_photo(self): return self.source == "photo_estimate"

    def __repr__(self): return f"Num({self.value!r} {self.unit}, {self.source}:{self.ref})"


class Row:
    __slots__ = ("id", "kind", "point", "lens", "severity", "hold", "page", "size", "comment", "num", "baseline",
                 "target", "method", "location", "knock_on", "raw")

    @property
    def is_pattern_change(self): return self.kind == "delta"

    def nums(self):
        """every number this row carries (the trace gate resolves each one)"""
        return [n for n in (self.num, self.baseline, self.target) if n is not None]

    def change(self):
        """PATTERN change in the row's unit: target - baseline when both are on file, else the stated change"""
        if self.baseline is not None and self.target is not None:
            return round(self.target.value - self.baseline.value, 4)
        return None if self.num is None else self.num.value

    def target_value(self):
        if self.target is not None: return self.target.value
        if self.baseline is not None and self.num is not None: return round(self.baseline.value + self.num.value, 4)
        return None


class TDInput:
    __slots__ = ("product", "round", "rev", "supersedes", "rows", "path")

    def pattern_rows(self): return [r for r in self.rows if r.kind == "delta"]
    def hold_rows(self): return [r for r in self.rows if r.hold]
    def tolerance_rows(self): return [r for r in self.rows if r.kind == "tolerance"]
    def comment_rows(self): return [r for r in self.rows if r.kind == "comment"]
    def other_pom_rows(self): return [r for r in self.rows if r.kind == "pom" and not r.hold]
    def page_rows(self, page): return [r for r in self.rows if r.page == page]


def _need(d, key, where, allowed=None):
    if key not in d or d[key] in (None, ""):
        raise TDInputError(f"{where}: missing '{key}'" + (f" (one of {', '.join(allowed)})" if allowed else ""))
    v = d[key]
    if allowed and v not in allowed:
        raise TDInputError(f"{where}: {key} '{v}' is not one of {', '.join(allowed)}")
    return v


def _num(d, where, unit=None, source=None, ref=None):
    """a number object {value, unit, source, ref}; unit/source/ref fall back to the row's"""
    v = d.get("value")
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise TDInputError(f"{where}: value must be a number (got {v!r}) — a number, not text, so the engine can trace it")
    u = d.get("unit") or unit
    if u not in UNITS: raise TDInputError(f"{where}: unit {u!r} is not one of {', '.join(UNITS)}")
    s = d.get("source") or source
    if s not in SOURCES: raise TDInputError(f"{where}: source {s!r} is not one of {', '.join(SOURCES)}")
    r = d.get("ref") or ref
    if not r: raise TDInputError(f"{where}: missing 'ref' (file#cell, file#what was measured, or the photo id)")
    if s in ("file+cell", "measured_from_file") and "#" not in str(r):
        raise TDInputError(f"{where}: a {s} ref is '<file>#<cell>' (got {r!r})")
    return Num(v, u, s, str(r), where)


def _row(d, i):
    where = f"rows[{i}]" + (f" ({d.get('id')})" if isinstance(d, dict) and d.get("id") else "")
    if not isinstance(d, dict): raise TDInputError(f"{where}: a row is an object")
    r = Row()
    r.raw = d
    r.id = str(_need(d, "id", where))
    r.kind = _need(d, "kind", where, KINDS)
    r.point = str(_need(d, "point", where))
    r.lens = _need(d, "lens", where, LENSES)
    r.severity = _need(d, "severity", where, SEVERITIES)
    r.hold = d.get("hold", False)
    if not isinstance(r.hold, bool): raise TDInputError(f"{where}: hold is true or false")
    r.page, r.size, r.comment = d.get("page"), d.get("size"), d.get("comment")
    r.method, r.location, r.knock_on = d.get("method"), d.get("location"), list(d.get("knock_on") or [])
    unit, source, ref = d.get("unit"), d.get("source"), d.get("ref")
    r.num = _num(d, where, unit, source, ref) if "value" in d else None
    r.baseline = _num(d["baseline"], f"{where}.baseline", unit, source, ref) if d.get("baseline") else None
    r.target = _num(d["target"], f"{where}.target", unit, source, ref) if d.get("target") else None

    if r.kind != "delta" and (r.baseline or r.target):
        raise TDInputError(f"{where}: baseline / target belong on a delta (PATTERN change) row, not a {r.kind} row")
    if r.kind in ("pom", "tolerance") and r.num is None:
        raise TDInputError(f"{where}: a {r.kind} row needs a value")
    if r.hold and r.kind != "pom":
        raise TDInputError(f"{where}: only a pom row can be held (a {r.kind} row with hold: true contradicts itself)")
    if r.kind == "delta":
        if r.num is None and not (r.baseline and r.target):
            raise TDInputError(f"{where}: a PATTERN change needs value (the change) or baseline + target")
        if r.num is not None and r.baseline and r.target:
            raise TDInputError(f"{where}: give the change OR baseline + target, not both (the engine computes the change)")
        for n in r.nums():
            if n.is_photo:
                raise TDInputError(f"{n.where}: photo_estimate refused in a PATTERN-change row ({PHOTO}); "
                                   f"measure it from the file or the measured sheet, or make it a comment")
        units = {n.unit for n in r.nums()}
        if len(units) > 1: raise TDInputError(f"{where}: mixed units {sorted(units)} in one PATTERN change")
        if not r.location: raise TDInputError(f"{where}: a PATTERN change needs 'location' (where on the piece to change it)")
    if r.kind == "comment":
        if not r.comment: raise TDInputError(f"{where}: a comment row needs 'comment'")
        if not ref and r.num is None:
            raise TDInputError(f"{where}: a construction / workmanship comment needs a photo or page reference ('ref')")
    return r


def parse(data, path=None):
    """dict -> TDInput (raises TDInputError naming the first bad field)"""
    if not isinstance(data, dict): raise TDInputError("TD input is an object with product, round, rev, rows")
    td = TDInput()
    td.path = path
    for k in ("product", "round", "rev"):
        setattr(td, k, str(_need(data, k, "TD input")))
    td.supersedes = data.get("supersedes")
    rows = data.get("rows")
    if not isinstance(rows, list): raise TDInputError("TD input: 'rows' must be a list")
    td.rows = [_row(d, i) for i, d in enumerate(rows)]
    seen = set()
    for r in td.rows:
        if r.id in seen: raise TDInputError(f"rows: id '{r.id}' used twice (the chair merges by id)")
        seen.add(r.id)
    held = {(r.point, r.size) for r in td.hold_rows()}
    for r in td.pattern_rows():
        if (r.point, r.size) in held:
            raise TDInputError(f"rows ({r.id}): '{r.point}' is both a PATTERN change and on the HOLD list")
    return td


def load(path):
    with open(path) as fh:
        return parse(json.load(fh), path)
