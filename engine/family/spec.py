"""Family + variant spec loader (ROADMAP step 1: project config instead of code).

A FAMILY (families/<family>/family.yaml) holds everything that is the same for every product of that type: the POM
chart, blank fabric, construction, trims + labels, packing. A VARIANT (families/<family>/variants/<slug>.yaml) holds only
what changes per product: body colour, decorations (art file, placement, size, method), label/trim overrides.

Value convention in the yaml (readable by a non-developer):
    hem_stitch: "twin-needle coverstitch"                      -> confirmed value
    fabric: {value: "100 % cotton 250 gsm", source: "quote"}  -> confirmed, with its source
    knit: {proposed: "single jersey", note: "not recorded"}    -> PROPOSED: printed amber "[proposed — confirm]"
                                                                  and listed on the F1 open-questions page
Every value becomes a V; spec.proposed() lists every proposed one (with its yaml path) for F1.
"""
import copy, os
from fractions import Fraction
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TAG = "[proposed — confirm]"
MM_PER = {"in": 25.4, "cm": 10.0, "mm": 1.0}


class SpecError(ValueError):
    """a variant or family file is wrong — the message says which line to fix"""


class V:
    """one value from the yaml: .v (the value), .proposed (bool), .source, .note, .path (yaml path)"""
    __slots__ = ("v", "proposed", "source", "note", "path")

    def __init__(self, v, proposed=False, source=None, note=None, path=""):
        self.v, self.proposed, self.source, self.note, self.path = v, proposed, source, note, path

    def __str__(self): return str(self.v)
    def __repr__(self): return f"V({self.v!r}{', proposed' if self.proposed else ''})"

    def text(self, tag=True):
        """display text; proposed values carry the amber tag"""
        s = str(self.v)
        return f"{s}  {TAG}" if (self.proposed and tag) else s


def wrap(node, path=""):
    """yaml tree -> same tree with V leaves. {proposed: x} / {value: x} dicts collapse to one V."""
    if isinstance(node, dict):
        keys = set(node)
        if "proposed" in keys and keys <= {"proposed", "note", "source"}:
            return V(node["proposed"], True, node.get("source"), node.get("note"), path)
        if "value" in keys and keys <= {"value", "note", "source"}:
            return V(node["value"], False, node.get("source"), node.get("note"), path)
        return {k: wrap(v, f"{path}.{k}" if path else str(k)) for k, v in node.items()}
    if isinstance(node, list):
        return [wrap(v, f"{path}[{i}]") for i, v in enumerate(node)]
    return V(node, False, None, None, path)


def val(x, default=None):
    """plain python value of a V (or of a raw value)"""
    if x is None: return default
    return x.v if isinstance(x, V) else x


def is_prop(x): return isinstance(x, V) and x.proposed


def deep_merge(base, over):
    """variant overrides family: dicts merge key by key; anything else replaces"""
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict) and not ({"proposed", "value"} & set(v)):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


# ----------------------------------------------------------------------------- measurements
def parse_num(s):
    """'25 1/2' / '7/8' / 2.2 / '21.75' -> Fraction (exact; never rounded before display)"""
    if isinstance(s, V): s = s.v
    if isinstance(s, (int, float)): return Fraction(s).limit_denominator(64)
    s = str(s).strip()
    if not s: raise SpecError("empty measurement")
    tot = Fraction(0)
    for part in s.split():
        tot += Fraction(part)
    return tot


def fmt_in(x):
    """Fraction inches -> '21 3/4' (nearest 1/8 — the chart's own resolution)"""
    q = Fraction(round(Fraction(x) * 8), 8)
    w, r = divmod(q.numerator, q.denominator)
    if r == 0: return f"{w}"
    fr = Fraction(r, q.denominator)
    return f"{w} {fr.numerator}/{fr.denominator}" if w else f"{fr.numerator}/{fr.denominator}"


class POM:
    """one point of measure. values are in the chart's own unit (exact); .mm(size) converts (LESSONS C2: .half is explicit,
    a half (flat) measure is NEVER doubled or halved silently — .mm() returns the measure as written on the chart)."""

    def __init__(self, code, d, unit, sizes, path):
        self.code = code
        self.name = val(d.get("name"))
        self.how = val(d.get("how"), "")
        if "half" not in d:
            raise SpecError(f"{path}.{code}: every POM must say half: true/false (LESSONS C2 — half measures explicit)")
        self.half = d["half"]                       # V(bool), may be proposed (e.g. "half, inferred from magnitude")
        self.unit = val(d.get("unit"), unit)
        if self.unit not in MM_PER: raise SpecError(f"{path}.{code}: unit '{self.unit}' — use in, cm or mm")
        vals = d.get("values")
        if isinstance(vals, V) or not isinstance(vals, (list, dict)):        # one value for every size
            vals = [vals] * len(sizes)
        if isinstance(vals, dict):
            vals = [vals[s] for s in sizes]
        if len(vals) != len(sizes):
            raise SpecError(f"{path}.{code}: {len(vals)} values for {len(sizes)} sizes {sizes}")
        self.cells = {s: V(parse_num(v), is_prop(v), None, getattr(v, "note", None), f"{path}.{code}.{s}")
                      for s, v in zip(sizes, vals)}
        self.tol = d.get("tol")                      # V (number) in tol_unit
        self.tol_unit = val(d.get("tol_unit"), "cm")
        self.path = f"{path}.{code}"

    def raw(self, size): return self.cells[size].v
    def mm(self, size): return float(self.cells[size].v) * MM_PER[self.unit]
    def cm(self, size): return self.mm(size) / 10.0
    def tol_mm(self): return None if self.tol is None else float(parse_num(self.tol)) * MM_PER[self.tol_unit]

    def show(self, size):
        """chart-unit text for a cell, e.g. '21 3/4' or '2.2'"""
        x = self.raw(size)
        return fmt_in(x) if self.unit == "in" else f"{float(x):g}"


class Chart:
    """the POM chart: ONE entry in family.yaml (pom_chart). Swap that entry and every page changes.

    pom_chart: {status, base: {source, unit, sizes, base_size, poms}, deltas: {at_size, source, changes}}
      base   = the factory's graded chart as received (confirmed numbers)
      deltas = recorded changes on top of it (e.g. the March 2026 new tee shape, recorded at size L only):
               {to: "27"}            the recorded value at at_size; every other size moves by the same amount
                                     (= the base chart's own grade steps) and is PROPOSED (derived)
               {by: -1.5, unit: cm}  a fixed change on every size; all PROPOSED
               {to: "4", new: {name, how, half, grade_like: E}}  a POM the base chart does not have;
                                     other sizes graded like E, PROPOSED
    base + deltas = the block. When the factory sends the full graded chart it replaces `base` and `deltas` goes."""

    def __init__(self, d, path="pom_chart"):
        self.d = d
        self.status = d.get("status")                # V; proposed => banner on every page that uses the chart
        base = d["base"] if "base" in d else d
        bpath = f"{path}.base" if "base" in d else path
        self.unit = val(base.get("unit"), "in")
        self.sizes = [val(s) for s in base["sizes"]]
        self.all_sizes = self.sizes
        self.base = val(base.get("base_size"), self.sizes[len(self.sizes) // 2])
        self.source = val(base.get("source"), "")
        self.poms = {k: POM(k, v, self.unit, self.sizes, f"{bpath}.poms") for k, v in base["poms"].items()}
        self.base_values = {k: {s: p.raw(s) for s in self.sizes} for k, p in self.poms.items()}
        self.deltas = []                             # [(code, text, V)] for the delta box on the POM page
        self.delta_source = ""
        if d.get("deltas"): self._apply_deltas(d["deltas"], f"{path}.deltas")

    @staticmethod
    def _sgn(x):
        return ("+" if x >= 0 else "-") + fmt_in(abs(x))

    def _apply_deltas(self, dl, path):
        at = val(dl.get("at_size")); self.delta_source = val(dl.get("source"), "")
        if at not in self.sizes: raise SpecError(f"{path}.at_size: '{at}' is not a chart size {self.sizes}")
        for code, ch in (dl.get("changes") or {}).items():
            cp = f"{path}.changes.{code}"; note = val(ch.get("note"))
            src = val(ch.get("source"), "")
            if "new" in ch:
                nd = {k: v for k, v in ch["new"].items()}; like = val(nd.pop("grade_like", None))
                if like not in self.poms: raise SpecError(f"{cp}: grade_like '{like}' is not a POM code")
                to = parse_num(ch["to"]); ref = self.poms[like]
                vals = {s: to + (ref.raw(s) - ref.raw(at)) for s in self.sizes}
                p = POM(code, dict(nd, values=[str(vals[s]) for s in self.sizes]), self.unit, self.sizes, f"{path}.changes")
                for s in self.sizes:
                    p.cells[s] = V(vals[s], s != at, None, f"graded like {like} from the recorded {at} value", f"{cp}.{s}")
                self.poms[code] = p
                self.deltas.append((code, f"{p.name} (new POM): {fmt_in(to)} at {at}; other sizes graded like {like}", src))
                continue
            if code not in self.poms: raise SpecError(f"{cp}: '{code}' is not a POM code in the base chart")
            p = self.poms[code]
            if "to" in ch:
                to = parse_num(ch["to"]); delta = to - p.raw(at); rec_prop = is_prop(ch["to"])
                for s in self.sizes:
                    p.cells[s] = V(p.raw(s) + delta, rec_prop or s != at, None,
                                   note or f"base chart {fmt_in(self.base_values[code][s])} {self._sgn(delta)} (recorded change at {at})",
                                   f"{cp}.{s}")
                self.deltas.append((code, f"{p.name}: {fmt_in(self.base_values[code][at])} → {fmt_in(to)} at {at}"
                                    f"  ({self._sgn(delta)} in, applied to every size)", src))
            elif "by" in ch:
                u = val(ch.get("unit"), p.unit)
                by = parse_num(ch["by"]) * Fraction(str(MM_PER[u])) / Fraction(str(MM_PER[p.unit]))
                # exact (no 1/8 rounding here): the cm column uses the exact value, inches are rounded for display only
                for s in self.sizes:
                    p.cells[s] = V(p.raw(s) + by, True, None, note, f"{cp}.{s}")
                self.deltas.append((code, f"{p.name}: {float(parse_num(ch['by'])):+g} {u} on every size"
                                    f"  ({self._sgn(by)} in on the chart)", src))
            else:
                raise SpecError(f"{cp}: a change needs 'to:' (recorded value at {at}) or 'by:' (fixed change)")

    def __getitem__(self, code): return self.poms[code]

    def mm(self, code, size): return self.poms[code].mm(size)

    def cell_proposed(self, code, size): return self.poms[code].cells[size].proposed

    def derived_cells(self):
        """one V per POM whose cells are derived (proposed) — for the F1 list"""
        out = []
        for k, p in self.poms.items():
            ps = [s for s in self.sizes if p.cells[s].proposed]
            if ps:
                out.append(V(f"{k} {p.name}: {', '.join(ps)} = " + ", ".join(p.show(s) for s in ps) + f" {p.unit}",
                             True, None, p.cells[ps[0]].note, f"pom_chart.cells.{k}"))
        return out

    def grade(self, code):
        """grade steps between consecutive sizes (chart unit): one value if uniform, else None"""
        p = self.poms[code]; ss = self.sizes
        st = {p.raw(b) - p.raw(a) for a, b in zip(ss, ss[1:])}
        return next(iter(st)) if len(st) == 1 else None


# ----------------------------------------------------------------------------- family + variant
class Spec:
    """family.yaml merged with a variant .yaml. .chart, .fam (wrapped family tree), .var (wrapped variant tree), .tree"""

    def __init__(self, family_dir, variant_path, methods=None, fam_override=None):
        self.family_dir = family_dir
        self.variant_path = variant_path
        fam_raw = yaml.safe_load(open(os.path.join(family_dir, "family.yaml")))
        if fam_override: fam_raw = deep_merge(fam_raw, fam_override)
        var_raw = yaml.safe_load(open(variant_path)) if isinstance(variant_path, str) else dict(variant_path)
        self.raw_family, self.raw_variant = fam_raw, var_raw
        for k in ("slug", "name", "body", "decorations"):
            if k not in var_raw: raise SpecError(f"variant {variant_path}: missing '{k}:'")
        merged = deep_merge(fam_raw, var_raw.get("overrides") or {})
        self.tree = wrap(merged)
        self.var = wrap(var_raw)
        self.chart = Chart(self.tree["pom_chart"])
        self.sizes = self.chart.sizes
        self.base = self.chart.base
        from . import methods as MT
        self.methods = methods or MT.load()
        self.decorations = [MT.Decoration(d, i, self) for i, d in enumerate(self.var["decorations"])]
        self.var_dir = os.path.dirname(os.path.abspath(variant_path)) if isinstance(variant_path, str) else family_dir

    def flat(self, size):
        """the family's block geometry for one size (cached); the family key picks the block (tee -> TeeFlat)"""
        cache = self.__dict__.setdefault("_flats", {})
        if size not in cache:
            fam = val(self.tree.get("family"))
            if fam == "tee":
                from .tee_block import TeeFlat
                cache[size] = TeeFlat(self, size)
            else:
                raise SpecError(f"family '{fam}' has no block yet (engine/family: add one, see docs/FAMILIES.md)")
        return cache[size]

    # convenience
    @property
    def slug(self): return val(self.var["slug"])
    @property
    def name(self): return val(self.var["name"])
    def get(self, dotted, default=None):
        node = self.tree
        for k in dotted.split("."):
            if not isinstance(node, dict) or k not in node: return default
            node = node[k]
        return node

    def proposed(self):
        """every proposed value in the family (as overridden) + the variant + the chart, deduplicated by path"""
        out, seen = [], set()
        def walk(n):
            if isinstance(n, V):
                if n.proposed and n.path not in seen: seen.add(n.path); out.append(n)
            elif isinstance(n, dict):
                for v in n.values(): walk(v)
            elif isinstance(n, list):
                for v in n: walk(v)
        walk(self.tree); walk({k: v for k, v in self.var.items() if k != "overrides"})
        for v in self.chart.derived_cells(): walk(v)        # chart cells derived from the recorded deltas
        for d in self.decorations:
            for v in d.method_fields_proposed(): walk(v)
        return out


def resolve(path, base_dir):
    """file path from a yaml: relative to the yaml's folder, else to the repo root"""
    if not path: return None
    for b in (base_dir, ROOT):
        p = os.path.join(b, path)
        if os.path.exists(p): return p
    return None
