"""POM table rules from the first live TD run (Godspeed track pants, 2026-10-22; LESSONS T1, T3).

  rise_check(rows)        rows = [(label, incl_waistband)] for ONE table -> [problems]
      every rise POM (front / back / any "rise") must say incl_waistband: true|false, and one table must not mix the
      two methods. A rise measured "with waistband" next to an unlabelled one is how a 3-4 cm rise "error" is read.
  required_missing(codes_and_names, family)  -> [missing POM keys]
      family `pom_required: [...]`, plus the waist rule: `waist: elastic` needs waist_relaxed AND waist_stretched.
"""
import re

# rise = the CF / CB seam from waist to crotch, whatever the chart calls it
RISE = re.compile(r"\brise\b|\bcrotch\s+(depth|length)\b|\bC[FB]\s+(seam\s+)?length\b|\b(front|back)\s+crotch\b", re.I)
WAIST_REQUIRED = {"elastic": ["waist_relaxed", "waist_stretched"]}


def is_rise(label): return bool(RISE.search(str(label or "")))


def rise_check(rows, table="POM table"):
    out = []
    rises = [(lab, v) for lab, v in rows if is_rise(lab)]
    for lab, v in rises:
        if not isinstance(v, bool):
            out.append(f"{table}: rise POM '{lab}' must say incl_waistband: true or false (got {v!r})")
    methods = {v for _, v in rises if isinstance(v, bool)}
    if len(methods) > 1:
        w = [lab for lab, v in rises if v is True]; wo = [lab for lab, v in rises if v is False]
        out.append(f"{table}: mixed rise methods — with waistband: {', '.join(w)}; without: {', '.join(wo)}. "
                   f"Measure every rise in one table the same way")
    return out


def _key(s): return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")


def required_missing(keys, family):
    """keys = POM codes + names present; family = dict with optional pom_required / waist"""
    have = {_key(k) for k in keys}
    need = list(family.get("pom_required") or []) + WAIST_REQUIRED.get(str(family.get("waist") or "").lower(), [])
    return [n for n in dict.fromkeys(need) if _key(n) not in have]
