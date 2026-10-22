"""Colour count vs the supplier's max + BOM special-trim flags (TD feasibility matrix, design §12: "colour count vs
factory max; special trims -> MOQ/subcontract"). Deterministic; reads factory.json and the pack data.

Supplier limits live in factory.json:
  top level            = Mandy's embroidery factory ("mandy"): embroidery max = needles when needles_confirmed
  "suppliers": {key: {name, max_colours: {<method>: {value, per, source}}}}   every other supplier / method
A limit that is not recorded is NOT RECORDED — never a pass. DTG / DTF are digital full-colour: no colour limit (N/A).

  rows = colour_check([{"name", "method", "supplier", "colours", "source"}], prof)   # colours None = count not recorded
  flags = trim_flags([{"item", "special"?, "moq"?, "lead_time_days"?, "made"?}])
  each row/flag: {"status": PASS|FAIL|NOT RECORDED|N/A|FLAG, "text": one line for a person}
"""
import re

PASS, FAIL, NOT_RECORDED, NA, FLAG = "PASS", "FAIL", "NOT RECORDED", "N/A", "FLAG"
FULL_COLOUR = {"dtg", "dtf"}
PROCESS = re.compile(r"\b(cmyk|4[- ]colou?r process|process colou?r)", re.I)
# hardware / custom trims that carry their own MOQ, lead time and are often made by a sub-supplier
SPECIAL = re.compile(r"\b(zip|zipper|zip puller|puller|buckle|cord ?lock|stopper|toggle|snap|press stud|rivet|eyelet|"
                     r"grommet|d-ring|hook|velcro|hook[- ]and[- ]loop|aglet|cord end|badge|metal plate|magnet|"
                     r"custom|embossed|debossed|engraved|branded)\b", re.I)


def max_colours(prof, supplier, method):
    """(n, per, source) or None when not recorded"""
    if supplier == "mandy" and method == "embroidery":
        if prof.get("needles_confirmed"):
            return int(prof["needles"]), "stitch file", prof.get("needles_note") or "factory.json needles (confirmed)"
        return None
    s = (prof.get("suppliers") or {}).get(supplier) or {}
    m = (s.get("max_colours") or {}).get(method)
    if not m or m.get("value") is None: return None
    return int(m["value"]), m.get("per", "design"), m.get("source", "factory.json")


def count_colours(colours):
    """colour entries -> count: each entry 1, an entry with count: n -> n, a CMYK / process entry -> 4.
    No list, or an EMPTY list, = not recorded (None) — never 0 colours, which would pass every limit."""
    if not colours: return None
    n = 0
    for c in colours:
        if isinstance(c, dict) and c.get("count") is not None: n += int(c["count"])
        elif PROCESS.search(str(c.get("name") if isinstance(c, dict) else c)): n += 4
        else: n += 1
    return n


def colour_check(designs, prof):
    rows = []
    for d in designs:
        nm, meth, sup, n = d["name"], d["method"], d.get("supplier"), d.get("colours")
        if meth in FULL_COLOUR:
            rows.append(dict(status=NA, text=f"{nm} ({meth}): digital full-colour, no colour limit")); continue
        lim = max_colours(prof, sup, meth) if sup else None
        sname = ((prof.get("suppliers") or {}).get(sup) or {}).get("name") or (prof.get("name") if sup == "mandy" else sup)
        if n is None:
            rows.append(dict(status=NOT_RECORDED, text=f"{nm} ({meth}): design colour count not recorded — count the "
                             f"colours before the sample" + (f" (max {lim[0]} per {lim[1]})" if lim else ""))); continue
        if lim is None:
            rows.append(dict(status=NOT_RECORDED, text=f"{nm} ({meth}, {n} colours): {sname or 'supplier not named'} max "
                             f"{meth} colours not recorded — ask: what is the maximum number of colours per design?"))
            continue
        mx, per, src = lim
        rows.append(dict(status=FAIL if n > mx else PASS,
                         text=f"{nm} ({meth}): {n} colours vs {sname} max {mx} per {per}"
                              + (f" — {n - mx} over: reduce the colours or change supplier" if n > mx else "")
                              + f" [{src}]"))
    return rows


def trim_flags(items):
    """special trims -> a closed question per missing fact (MOQ, lead time, in-house / subcontracted)"""
    out = []
    for it in items:
        name = str(it.get("item", ""))
        special = it.get("special")
        if special is None: special = bool(SPECIAL.search(name))
        if not special: continue
        miss = [k for k, lab in (("moq", "MOQ"), ("lead_time_days", "lead time (days)"), ("made", "made in-house or subcontracted"))
                if it.get(k) in (None, "")]
        if miss:
            labs = {"moq": "MOQ", "lead_time_days": "lead time (days)", "made": "made in-house or subcontracted"}
            out.append(dict(status=FLAG, item=name, text=f"special trim '{name}': not recorded — "
                            + "; ".join(labs[k] for k in miss) + ". Ask the factory for each as a number / yes-no."))
        else:
            out.append(dict(status=PASS, item=name, text=f"special trim '{name}': MOQ {it['moq']}, lead time "
                            f"{it['lead_time_days']} days, {it['made']}"))
    return out


def summary(rows, flags):
    c = {s: sum(r["status"] == s for r in rows) for s in (PASS, FAIL, NOT_RECORDED, NA)}
    f = sum(x["status"] == FLAG for x in flags)
    return (f"supplier gate: {len(rows)} designs checked (pass {c[PASS]}, FAIL {c[FAIL]}, not recorded {c[NOT_RECORDED]}, "
            f"n/a {c[NA]}); {len(flags)} special trims ({f} flagged)")
