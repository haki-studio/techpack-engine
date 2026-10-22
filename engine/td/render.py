"""Render TD rows (td.schema) into (a) "TD: ..." annotations on pack pages and (b) the factory comment sheet (design §5).

Every number printed here is a field of an input row (or target - baseline, computed here) — never typed.

  td = schema.load("projects/<slug>/td/<event>.json")
  svg = annotate(svg, td.page_rows("T3"))             # one pack page, notes in a band at the foot
  pages = comment_sheet(td)                            # [svg] A4 pages: HOLD first, then PATTERN, ...
  text = "\\n".join(l for _, l in sheet_lines(td))       # the same sheet as plain lines (chat / email draft)
"""
import re
import sheet as SHT
from sheet import t, doc, SW, SH, INK, MUTED, RED, ORANGE, GUIDE
from render import f
from family.draw import wrap
from .schema import PHOTO, TDInputError

SEV_ORDER = {"high": 0, "medium": 1, "low": 2}
STANDING_PATTERN = ("Change the pattern at {points} only. Do NOT grade or scale the whole piece. "
                    "Send the new pattern PDF + a measured sheet BEFORE cutting.")
STANDING_SA = "Tell us the seam allowance and shrinkage % you used."


def num(x, unit=None):
    """a number as printed: shortest exact form (26.5, 0.3), never rounded to look neat"""
    s = f"{round(float(x), 4):g}"
    return f"{s} {unit}" if unit else s


def signed(x, unit):
    v = round(float(x), 4)
    return ("+" if v > 0 else "") + num(v, unit)


def val_text(n, approx_mark=True):
    """one Num as text; a photo estimate always carries its warning"""
    if n.is_photo: return f"≈ {num(n.value, n.unit)} ({PHOTO}; photo {n.ref})"
    return num(n.value, n.unit)


def where(r): return f"{r.point}" + (f" {r.size}" if r.size else "")


def by_sev(rows): return sorted(rows, key=lambda r: SEV_ORDER[r.severity])


# ----------------------------------------------------------------------------- annotations
def note_text(r):
    """'TD (fit · high): ...' — the line a pack page carries for one row"""
    head = f"TD ({r.lens} · {r.severity}): "
    if r.kind == "delta":
        b, tg, ch = r.baseline, r.target_value(), r.change()
        unit = r.nums()[0].unit
        s = f"PATTERN {where(r)}: " + (f"{num(b.value)} → " if b else "") + \
            (f"{num(tg, unit)} " if tg is not None else "") + f"(change {signed(ch, unit)}) at {r.location}"
    elif r.kind == "tolerance":
        s = f"tolerance {where(r)} ± {val_text(r.num)}"
    elif r.kind == "pom":
        s = f"{where(r)} {'' if r.num.is_photo else '= '}{val_text(r.num)}" + ("  — HOLD (do not change)" if r.hold else "")
    else:
        s = r.comment + (f" ({val_text(r.num)})" if r.num else "")
    if r.comment and r.kind != "comment": s += f" — {r.comment}"
    src = [n for n in r.nums() if not n.is_photo]
    if src: s += "  [" + "; ".join(f"{n.source}: {n.ref}" for n in src) + "]"
    elif r.kind == "comment" and r.raw.get("ref"): s += f"  [see {r.raw['ref']}]"
    return head + s


BAND_SIZE, BAND_LH, BAND_MAX = 1.6, 2.5, 10
_ROOT = re.compile(r'^(<svg\b[^>]*viewBox="0 0 (\d+(?:\.\d+)?) (\d+(?:\.\d+)?)"[^>]*>)(.*)(</svg>)\s*$', re.S)


def annotate(svg, rows):
    """put the rows' notes in a band at the foot of one A4 page. The page content is scaled uniformly (aspect kept, so
    true-proportion drawings stay true) to make room; nothing on the page is covered. No rows -> the page unchanged."""
    if not rows: return svg
    m = _ROOT.match(svg.strip())
    if not m or (float(m.group(2)), float(m.group(3))) != (SW, SH):
        raise TDInputError("annotate: not an engine A4 page (svg with viewBox 0 0 297 210)")
    lines = []
    for r in by_sev(rows):
        for i, l in enumerate(wrap(note_text(r), SW - 30, BAND_SIZE)):
            lines.append((l if i == 0 else "   " + l, RED if r.severity == "high" else INK))
    extra = 0
    if len(lines) > BAND_MAX: extra = len(lines) - (BAND_MAX - 1); lines = lines[:BAND_MAX - 1]
    band = 5.5 + BAND_LH * (len(lines) + (1 if extra else 0))
    k = (SH - band) / SH; ox = (SW - SW * k) / 2
    y0 = SH - band
    o = [f'<g transform="translate({f(ox)} 0) scale({k:.5f})">{m.group(4)}</g>',
         f'<rect x="8" y="{f(y0 + 0.4)}" width="{SW - 16}" height="{f(band - 1.4)}" fill="#EEF6FD" stroke="{GUIDE}" stroke-width="0.25"/>',
         t(11, y0 + 3.4, "TD NOTES — recommendations from the technical designers; every number is from the file named", 1.6, 700, GUIDE)]
    y = y0 + 3.4 + BAND_LH
    for l, col in lines: o.append(t(11, y, l, BAND_SIZE, 500, col)); y += BAND_LH
    if extra: o.append(t(11, y, f"+ {extra} more lines — see the TD comment sheet", BAND_SIZE, 700, MUTED))
    return m.group(1) + "\n".join(o) + m.group(5)


# ----------------------------------------------------------------------------- the comment sheet (design §5)
def sheet_lines(td):
    """[(kind, text)] the whole comment sheet, in order: HOLD list first (lead brief 2026-10-22), then PATTERN changes,
    tolerances, measurements to check, CONSTRUCTION / WORKMANSHIP, standing lines. Raises on a sheet a factory must
    never receive: a PATTERN change with no HOLD list."""
    pat, hold = by_sev(td.pattern_rows()), td.hold_rows()
    if pat and not hold:
        raise TDInputError("comment sheet: PATTERN changes with no HOLD list — list every other point with its current "
                           "value (hold: true), or the factory will regrade the whole piece")
    L = [("title", f"TD comment sheet — {td.product} — {td.round}"),
         ("sub", f"Rev {td.rev}" + (f" — supersedes Rev {td.supersedes}" if td.supersedes else " — first issue"))]
    L.append(("h", "HOLD — do not change these points"))
    if hold:
        for r in hold: L.append(("row", f"{where(r)}: keep at {val_text(r.num)}"))
    else:
        L.append(("muted", "no points held this round"))
    L.append(("h", "PATTERN changes — the factory edits the pattern"))
    if pat:
        L.append(("muted", "point · last measured sample → target · change · method · location of the change"))
        for r in pat:
            unit = r.nums()[0].unit; tg = r.target_value()
            base = val_text(r.baseline) if r.baseline else "NO MEASURED SHEET ON FILE — send it before this change"
            L.append(("warn" if not r.baseline else "row",
                      f"{where(r)} · {base} → {num(tg, unit) if tg is not None else 'target not stated'} · "
                      f"change {signed(r.change(), unit)} · {r.method or 'measure as on the POM chart'} · {r.location}"))
            if r.knock_on: L.append(("check", "   CHECK after this change: " + ", ".join(r.knock_on)))
        pts = ", ".join(dict.fromkeys(where(r) for r in pat))
        L.append(("standing", STANDING_PATTERN.format(points=pts)))
    else:
        L.append(("muted", "no pattern changes this round"))
    tol = td.tolerance_rows()
    if tol:
        L.append(("h", "TOLERANCES"))
        for r in by_sev(tol): L.append(("row", f"{where(r)}: ± {val_text(r.num)}"))
    oth = td.other_pom_rows()
    if oth:
        L.append(("h", "MEASUREMENTS TO CHECK (no change asked)"))
        for r in by_sev(oth): L.append(("row", f"{where(r)}: {val_text(r.num)}" + (f" — {r.comment}" if r.comment else "")))
    com = td.comment_rows()
    L.append(("h", "CONSTRUCTION / WORKMANSHIP — re-sew only"))
    if com:
        for r in by_sev(com):
            ref = r.raw.get("ref") if not r.num else (r.num.ref if r.num.is_photo else r.raw.get("ref"))
            L.append(("row", f"{r.point}: {r.comment}" + (f" ({val_text(r.num)})" if r.num else "") + (f" — see {ref}" if ref else "")))
    else:
        L.append(("muted", "no construction comments this round"))
    L.append(("standing", STANDING_SA))
    return L


_STYLE = {"h": (2.4, 700, INK, 2.0), "row": (1.85, 500, INK, 0), "warn": (1.85, 700, RED, 0), "check": (1.7, 600, ORANGE, 0),
          "standing": (1.85, 700, INK, 0.8), "muted": (1.7, 400, MUTED, 0)}
LH = 3.2


def comment_sheet(td, page="C1"):
    """the comment sheet as A4 pages (svg strings); continues onto C1_2, C1_3 ... with the header repeated"""
    L = sheet_lines(td)
    title, sub = L[0][1], L[1][1]
    SHT.FOOT = f"HAKI STUDIOS · {td.product} · TD comment sheet · Rev {td.rev}"
    pages, o, y, n = [], None, 0, 0
    def new():
        nonlocal o, y, n
        if o is not None: pages.append(doc(o))
        n += 1
        o = SHT.header(title + ("" if n == 1 else " (cont.)"), sub, page if n == 1 else f"{page}_{n}")
        y = 33
    new()
    for kind, text in L[2:]:
        size, w, col, gap = _STYLE[kind]
        parts = wrap(text, SW - 30, size)
        need = gap + LH * len(parts)
        if y + need > SH - 12: new()
        y += gap
        for i, p in enumerate(parts):
            o.append(t(12 if kind == "h" else 15, y, p if i == 0 else "   " + p, size, w, col)); y += LH
    pages.append(doc(o))
    return pages
