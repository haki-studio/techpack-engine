"""Rev-log <-> POM chart / callout agreement gate (was a TD pack-checklist item; design §4 "rev log; pattern/chart/
callouts agree"). Deterministic: reads the structured rev log and the chart the pages are drawn from.

A rev-log entry: {rev, date, change, pom_changes: [{pom, size, to} | {pom, by, unit}]}
  to   the value (chart unit, e.g. "27" or "22 3/4") the POM has at `size` after this revision
  by   a change applied to every size (unit: in | cm | mm)

Checks (each failure names the entry and the POM):
  R1  the log is not empty; every entry has rev, date, change; no rev twice; the pack's current rev = the newest entry
      (newest last)
  R2  the newest entry that states a POM value agrees with the chart the pages print: `to` = the chart cell at that size;
      `by` = chart - base chart at every size
  R3  every change on the chart (the T3 "changes" callout box = chart deltas) is named in the rev log — no silent change
  R4  (when a measured pattern is given: {pom: {size: mm}}) every POM the log changed measures on the pattern within
      the POM's tolerance (1 mm when none is set)

  rep = revgate.check(log, chart, current_rev, measured=None, scope="variant")
  rep.ok, rep.failures, rep.summary()
"""
from fractions import Fraction

MM_PER = {"in": 25.4, "cm": 10.0, "mm": 1.0}


class Report:
    def __init__(self, scope):
        self.scope, self.failures, self.entries, self.values = scope, [], 0, 0

    @property
    def ok(self): return not self.failures

    def summary(self):
        head = f"rev-log gate ({self.scope}): {self.entries} entries, {self.values} stated POM values checked against the chart"
        return head + (" — PASS" if self.ok else f" — FAIL ({len(self.failures)}):\n  " + "\n  ".join(self.failures))


def norm_rev(r): return "".join(str(r).split()).lower()


def _num(x):
    if isinstance(x, (int, float)): return Fraction(x).limit_denominator(64)
    return sum((Fraction(p) for p in str(x).split()), Fraction(0))


def check(log, chart, current_rev, measured=None, scope="pack", require_deltas=True, also_named=()):
    rep = Report(scope); F = rep.failures
    log = list(log or [])
    rep.entries = len(log)
    # R1
    if not log: F.append("R1 the rev log is empty")
    seen = set()
    for i, e in enumerate(log):
        for k in ("rev", "date", "change"):
            if not e.get(k): F.append(f"R1 entry {i + 1} ({e.get('rev', '?')}): missing '{k}'")
        r = norm_rev(e.get("rev", ""))
        if r in seen: F.append(f"R1 rev '{e.get('rev')}' is logged twice")
        seen.add(r)
    if log and current_rev is not None and norm_rev(log[-1].get("rev", "")) != norm_rev(current_rev):
        F.append(f"R1 the pack says {current_rev} but the newest rev-log entry is {log[-1].get('rev')} (newest last)")
    # R2: newest statement per (pom, size|by) wins
    latest = {}
    for e in log:
        for c in e.get("pom_changes") or []:
            pom = c.get("pom")
            if "by" in c and pom in chart.poms:
                # `by` changes add up across revisions: the chart shows their SUM (Rev A -1.5 cm + Rev B -0.5 cm = -2 cm)
                p = chart.poms[pom]; u = c.get("unit", p.unit)
                if u not in MM_PER: F.append(f"R2 {e.get('rev')}: {pom} unit '{u}'"); continue
                prev = latest.get((pom, "*by"), (None, {"_cum": Fraction(0), "_txt": []}))[1]
                d = _num(c["by"]) * Fraction(str(MM_PER[u])) / Fraction(str(MM_PER[p.unit]))
                c = {"by": True, "_cum": prev["_cum"] + d, "_txt": prev["_txt"] + [f"{c['by']} {u} ({e.get('rev')})"]}
            latest[(pom, c.get("size") if "to" in c else "*by")] = (e.get("rev"), c)
    named = set(also_named)
    for (pom, _), (rev, c) in latest.items():
        named.add(pom)
        if pom not in chart.poms:
            F.append(f"R2 {rev}: POM '{pom}' is not on the chart"); continue
        p = chart.poms[pom]
        if "to" in c:
            sz = c.get("size")
            if sz not in chart.sizes: F.append(f"R2 {rev}: {pom} 'to' needs a chart size (got {sz!r})"); continue
            rep.values += 1
            if _num(c["to"]) != Fraction(p.raw(sz)).limit_denominator(64):
                F.append(f"R2 {rev}: log says {pom} {p.name} = {c['to']} {p.unit} at {sz}; the chart prints {p.show(sz)}")
        elif "by" in c:
            by = c["_cum"]; txt = " + ".join(c["_txt"])
            for sz in chart.sizes:
                rep.values += 1
                got = Fraction(p.raw(sz)) - Fraction(chart.base_values.get(pom, {}).get(sz, p.raw(sz)))
                if abs(got - by) > Fraction(1, 10000):
                    u = c["_txt"][-1].split()[1]
                    F.append(f"R2 {rev}: log says {pom} {p.name} {txt} on every size; the chart moved it "
                             f"{float(got) * MM_PER[p.unit] / MM_PER[u]:+g} {u} at {sz}"); break
        else:
            F.append(f"R2 {rev}: {pom} change needs 'to' (with size) or 'by'")
    # R3
    if require_deltas:
        for code, txt, _ in getattr(chart, "deltas", []):
            if code not in named:
                F.append(f"R3 the chart callout '{code}: {txt}' is not in the rev log (log it with pom_changes)")
    # R4
    if measured:
        for pom in sorted({k[0] for k in latest} & set(chart.poms)):
            p = chart.poms[pom]; tol = p.tol_mm() if hasattr(p, "tol_mm") and p.tol is not None else 1.0
            for sz, mm in (measured.get(pom) or {}).items():
                if abs(mm - p.mm(sz)) > tol + 1e-9:
                    F.append(f"R4 {pom} {p.name} {sz}: pattern measures {mm:.1f} mm, chart {p.mm(sz):.1f} mm (tol ±{tol:g} mm)")
    return rep
