#!/usr/bin/env python3
"""Hat style catalogue (families/cap/styles.yaml + the shared cap facts in families/cap/family.yaml).

A hat tech pack is built from ONE style key: the block (crown die + brim die), panels, structure, POM chart,
construction, BOM and embroidery positions all come from the catalogue. Intake (scripts/intake.py) refuses a hat
design without a valid key, and scripts/dispatch.sh build refuses a hat project without one (check-project below).

Strict: an unknown style key, an unknown or missing field, or a value / POM with neither a source nor {proposed: ...}
is an error that names the fix (and the valid keys). Unknown = {proposed: x, note: ...}: printed amber on every page
and asked on the F1 page (engine/cap_pages.py).

  python3 engine/capstyle.py list                    every style: key, name, kind, status, products
  python3 engine/capstyle.py show <key>              one style in full (amber = proposed)
  python3 engine/capstyle.py check                   validate the catalogue (exit 1 + every problem)
  python3 engine/capstyle.py check-project <slug>    a hat project must name a valid style (STATUS.json / brief.md)
  python3 engine/capstyle.py product "<name>"        which style a product is made on
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)
import yaml
from family.spec import V, wrap, val, is_prop, TAG

ROOT = os.path.dirname(HERE)
CAP_DIR = os.path.join(ROOT, "families", "cap")

# garments that are hats: a design whose garment names one of these must pick a style (founder ask 2026-10-28)
HAT_GARMENTS = ("cap", "hat", "trucker", "bucket", "beanie", "snapback")
KINDS = ("cap", "bucket", "knit")
# garment word -> the style kinds it can be made on (others: any kind)
GARMENT_KINDS = {"beanie": ("knit",), "bucket": ("bucket",), "trucker": ("cap",), "snapback": ("cap",)}

IDENT = ("name", "kind", "status")                       # plain text allowed (identity, not a factory fact)
SOURCED = ("factory", "crown_die", "brim_die", "panels", "structure", "crown_profile", "brim", "closure", "size")
LISTS = ("construction", "bom", "products", "sources")
REQUIRED = {
    "cap": IDENT + SOURCED + ("pom", "embroidery") + LISTS,
    "bucket": IDENT + SOURCED + ("pom", "embroidery") + LISTS,
    "knit": IDENT + ("factory", "structure", "size", "knit", "pom", "embroidery") + LISTS,
}
OPTIONAL = ("factory_questions", "nda", "mesh", "notes")
KNIT_FIELDS = ("yarn", "stitch", "cuff", "gauge", "crown", "decoration")


class StyleError(ValueError):
    """the catalogue or a choice of style is wrong — the message says what to fix and lists the valid keys"""


def _is_v(x):
    """a {value, source} or {proposed, note} leaf, as written in the yaml"""
    return isinstance(x, dict) and ({"value", "proposed"} & set(x)) and set(x) <= {"value", "proposed", "source", "note"}


def _leaf_problem(x, where):
    """None if x is a sourced value or a proposal, else the error text"""
    if not _is_v(x):
        return (f"{where}: plain value {x!r} has no source — write {{value: ..., source: \"...\"}} "
                f"or {{proposed: ..., note: \"...\"}}")
    if "value" in x and "proposed" in x:
        return f"{where}: has both value and proposed — keep one"
    if "value" in x and not str(x.get("source") or "").strip():
        return f"{where}: value {x['value']!r} has no source — add source: \"...\" or make it {{proposed: ...}}"
    return None


def _cap_frame_positions(fam):
    return list((fam.get("cap_frame") or {}).keys())


def validate(raw_styles, fam):
    """every problem in the catalogue, as plain sentences (empty list = OK)"""
    errs = []
    sets = raw_styles.get("pom_sets") or {}
    styles = raw_styles.get("styles")
    if not isinstance(styles, dict) or not styles:
        return ["styles.yaml: no 'styles:' block"]
    for k in KINDS:
        if k not in sets: errs.append(f"pom_sets: missing the '{k}' POM set")
    positions = _cap_frame_positions(fam)
    for key, st in styles.items():
        w = f"styles.{key}"
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", str(key)):
            errs.append(f"{w}: style key must be lower-case words joined by '-'")
        if not isinstance(st, dict):
            errs.append(f"{w}: must be a block of fields"); continue
        kind = st.get("kind")
        if kind not in KINDS:
            errs.append(f"{w}.kind: '{kind}' — use one of {', '.join(KINDS)}"); continue
        req = REQUIRED[kind]
        for fld in req:
            if fld not in st: errs.append(f"{w}: missing required field '{fld}'")
        for fld in st:
            if fld not in req and fld not in OPTIONAL:
                errs.append(f"{w}: unknown field '{fld}' — valid fields for kind {kind}: {', '.join(req + OPTIONAL)}")
        for fld in IDENT:
            if fld in st and not isinstance(st[fld], str): errs.append(f"{w}.{fld}: must be plain text")
        for fld in SOURCED:
            if fld in st:
                p = _leaf_problem(st[fld], f"{w}.{fld}")
                if p: errs.append(p)
        if kind in ("cap", "bucket") and _is_v(st.get("panels")) and kind == "cap":
            pv = st["panels"].get("value", st["panels"].get("proposed"))
            if pv not in (5, 6): errs.append(f"{w}.panels: a cap has 5 or 6 crown panels (got {pv!r})")
        if kind == "knit":
            kn = st.get("knit") or {}
            if not isinstance(kn, dict): errs.append(f"{w}.knit: must be a block"); kn = {}
            for fld in KNIT_FIELDS:
                if fld not in kn: errs.append(f"{w}.knit: missing '{fld}'")
            for fld, v in kn.items():
                if fld not in KNIT_FIELDS: errs.append(f"{w}.knit: unknown field '{fld}' — valid: {', '.join(KNIT_FIELDS)}")
                else:
                    p = _leaf_problem(v, f"{w}.knit.{fld}")
                    if p: errs.append(p)
        # POM chart: every code of the kind's set (optional ones may be left out), each sourced or proposed
        pset = sets.get(kind) or {}
        pom = st.get("pom") or {}
        if not isinstance(pom, dict): errs.append(f"{w}.pom: must be a block of POM codes"); pom = {}
        for code, d in pset.items():
            if code not in pom and not d.get("optional"):
                errs.append(f"{w}.pom: missing POM {code} ({d['name']}) — give a value with a source or {{proposed: ...}}")
        for code, v in pom.items():
            if code not in pset:
                errs.append(f"{w}.pom.{code}: not a POM of kind {kind} — valid codes: {', '.join(pset)}"); continue
            p = _leaf_problem(v, f"{w}.pom.{code} ({pset[code]['name']})")
            if p: errs.append(p); continue
            num = v.get("value", v.get("proposed"))
            if not isinstance(num, (int, float)) or isinstance(num, bool) or num <= 0:
                errs.append(f"{w}.pom.{code}: must be a positive number in cm (got {num!r})")
        for lst in ("construction", "bom"):
            rows = st.get(lst) or []
            if not isinstance(rows, list): errs.append(f"{w}.{lst}: must be a list"); continue
            for i, r in enumerate(rows):
                lab = "area" if lst == "construction" else "item"
                if not isinstance(r, dict) or lab not in r or "spec" not in r:
                    errs.append(f"{w}.{lst}[{i}]: needs '{lab}:' and 'spec:'"); continue
                p = _leaf_problem(r["spec"], f"{w}.{lst}[{i}] ({r[lab]})")
                if p: errs.append(p)
        emb = st.get("embroidery") or {}
        if not isinstance(emb, dict): errs.append(f"{w}.embroidery: must be a block of positions"); emb = {}
        for pos, e in emb.items():
            if pos not in positions:
                errs.append(f"{w}.embroidery.{pos}: unknown position — valid: {', '.join(positions)}"); continue
            for dim in ("w_cm", "h_cm", "colours"):
                if isinstance(e, dict) and dim in e:
                    p = _leaf_problem(e[dim], f"{w}.embroidery.{pos}.{dim}")
                    if p: errs.append(p)
        if kind == "knit" and any(p not in ("front", "back", "left_side", "right_side") for p in emb):
            errs.append(f"{w}.embroidery: a knit beanie has no inside / under-brim position")
        for i, pr in enumerate(st.get("products") or []):
            if not isinstance(pr, dict) or not pr.get("name") or not pr.get("match"):
                errs.append(f"{w}.products[{i}]: needs name: and match:"); continue
            if not (pr.get("source") or pr.get("proposed")):
                errs.append(f"{w}.products[{i}] ({pr['name']}): needs source: \"...\" or proposed: \"why we think so\"")
        if not (st.get("sources") or []): errs.append(f"{w}.sources: list at least one source")
    # one product -> one style
    seen = {}
    for key, st in styles.items():
        for pr in (st.get("products") or []) if isinstance(st, dict) else []:
            m = norm(pr.get("match", "")) if isinstance(pr, dict) else ""
            if m and m in seen and seen[m] != key:
                errs.append(f"product match '{m}' is in two styles: {seen[m]} and {key}")
            seen[m] = key
    return errs


def norm(s):
    """'Pink "Hearts" Beanie' -> 'pink hearts beanie'; 'Big News! Hat' -> 'big news hat'"""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(s).lower()).split())


class POMv:
    """one POM of a style: code, name, how, unit, v (V: value + source, or proposed + note)"""
    def __init__(self, code, d, v, path):
        self.code, self.name, self.how, self.unit = code, d["name"], d.get("how", ""), d.get("unit", "cm")
        self.v = v
        self.path = path

    @property
    def cm(self): return float(val(self.v))
    @property
    def mm(self): return self.cm * 10.0
    @property
    def proposed(self): return is_prop(self.v)


class Style:
    """one catalogue entry, wrapped (V leaves). .fam = the shared cap family (wrapped)."""
    def __init__(self, key, raw, pom_set, fam_raw):
        self.key, self.raw = key, raw
        self.kind = raw["kind"]
        self.t = wrap(raw, f"styles.{key}")
        self.fam = wrap(fam_raw)
        self.pom = {c: POMv(c, pom_set[c], self.t["pom"][c], f"styles.{key}.pom.{c}") for c in pom_set if c in raw["pom"]}

    @property
    def name(self): return self.raw["name"]
    def __getitem__(self, k): return self.t[k]
    def get(self, k, d=None): return self.t.get(k, d)

    def num(self, k):
        """panels as an int for the drawing (proposed or not)"""
        return int(val(self.t[k]))

    def cut_and_sew(self): return self.kind in ("cap", "bucket")

    def structured(self):
        return "unstructured" not in str(val(self.t.get("structure"))).lower() and self.kind == "cap"

    def closure_kind(self):
        c = str(val(self.t.get("closure", ""))).lower()
        return "snap" if "snap" in c else "none" if c.strip() in ("none", "") else "strap"

    def frame(self, pos):
        """(max_w V, max_h V) cap-frame limit for a position, from the family"""
        f = self.fam["cap_frame"][pos]
        return f["max_w_cm"], f["max_h_cm"]

    def proposed(self):
        """every proposed value this pack prints (family shared facts + the style), deduplicated by yaml path"""
        out, seen = [], set()
        def walk(n):
            if isinstance(n, V):
                if n.proposed and n.path not in seen: seen.add(n.path); out.append(n)
            elif isinstance(n, dict):
                for v in n.values(): walk(v)
            elif isinstance(n, list):
                for v in n: walk(v)
        walk({k: v for k, v in self.fam.items() if k not in ("cap_frame", "block")})
        frame_pos = list(self.raw.get("embroidery") or {})
        walk({p: self.fam["cap_frame"][p] for p in frame_pos})
        if self.cut_and_sew(): walk(self.fam.get("block"))
        walk({k: v for k, v in self.t.items() if k != "products"})
        for p in self.raw.get("products") or []:
            if p.get("proposed"):
                out.append(V(f"{p['name']} is made on {self.name}", True, None, p["proposed"], f"styles.{self.key}.products.{norm(p['match'])}"))
        return out


class Catalogue:
    def __init__(self, styles_path=None, family_path=None):
        self.styles_path = styles_path or os.path.join(CAP_DIR, "styles.yaml")
        self.family_path = family_path or os.path.join(CAP_DIR, "family.yaml")
        self.raw = yaml.safe_load(open(self.styles_path)) or {}
        self.fam_raw = yaml.safe_load(open(self.family_path)) or {}
        errs = validate(self.raw, self.fam_raw)
        if errs:
            raise StyleError(f"{len(errs)} problem(s) in {os.path.relpath(self.styles_path, ROOT)}:\n  " + "\n  ".join(errs))
        self.styles = {k: Style(k, v, self.raw["pom_sets"][v["kind"]], self.fam_raw) for k, v in self.raw["styles"].items()}

    def keys(self): return list(self.styles)

    def valid_keys_text(self):
        return ", ".join(f"{k} ({s.name})" for k, s in self.styles.items())

    def get(self, key):
        if key not in self.styles:
            raise StyleError(f"unknown hat style '{key}'. Valid styles: {self.valid_keys_text()}")
        return self.styles[key]

    def pom_set(self, kind): return self.raw["pom_sets"][kind]

    def product_style(self, name):
        """(style key, product entry) for a product name, or (None, None). Longest match wins; a tie is an error."""
        n = f" {norm(name)} "
        hits = [(len(norm(p["match"])), k, p) for k, s in self.styles.items() for p in s.raw.get("products") or []
                if f" {norm(p['match'])} " in n]
        if not hits: return None, None
        hits.sort(key=lambda h: -h[0])
        if len(hits) > 1 and hits[0][0] == hits[1][0] and hits[0][1] != hits[1][1]:
            raise StyleError(f"'{name}' matches two styles: {hits[0][1]} and {hits[1][1]}")
        return hits[0][1], hits[0][2]


_CAT = None
def load(refresh=False):
    global _CAT
    if _CAT is None or refresh: _CAT = Catalogue()
    return _CAT


def style_for_product(name, cat=None):
    """the style key a product is made on (None = not a known hat). Inferred mappings carry proposed: in the yaml."""
    return (cat or load()).product_style(name)[0]


def is_hat_garment(garment):
    return any(w in HAT_GARMENTS for w in norm(garment).split())


def check_choice(garment, style, cat=None):
    """None if (garment, style) is acceptable for a submission, else the refusal text (names the valid keys).
    Non-hat garments need no style."""
    cat = cat or load()
    if not is_hat_garment(garment or ""): return None
    if not style:
        return (f"'{garment}' is a hat: pick its hat style (style: <key>). Valid styles: {cat.valid_keys_text()}")
    if style not in cat.styles:
        return f"unknown hat style '{style}'. Valid styles: {cat.valid_keys_text()}"
    kinds = next((GARMENT_KINDS[w] for w in norm(garment).split() if w in GARMENT_KINDS), None)
    st = cat.styles[style]
    if kinds and st.kind not in kinds:
        ok = ", ".join(k for k, s in cat.styles.items() if s.kind in kinds)
        return f"'{garment}' cannot be made on '{style}' ({st.name}, a {st.kind} block). Valid for it: {ok}"
    return None


def project_info(slug, root=None):
    """(garment, style) recorded for projects/<slug>: STATUS.json first, then inputs/brief.md; origin/main if the
    folder is not in this checkout (dispatch looks there too)."""
    root = root or ROOT
    P = os.path.join(root, "projects", slug)
    def read(rel):
        p = os.path.join(P, rel)
        if os.path.exists(p): return open(p, encoding="utf-8").read()
        r = subprocess.run(["git", "-C", root, "show", f"origin/main:projects/{slug}/{rel}"], capture_output=True, text=True)
        return r.stdout if r.returncode == 0 else None
    st = read("STATUS.json"); brief = read("inputs/brief.md") or ""
    s = json.loads(st) if st else {}
    garment, style = s.get("garment"), s.get("style")
    m = re.search(r"^- Garment:\s*(.+)$", brief, re.M)
    if not garment and m: garment = m.group(1).strip()
    m = re.search(r"^- Hat style:\s*([a-z0-9-]+)", brief, re.M)
    if not style and m: style = m.group(1).strip()
    return garment, style


# ----------------------------------------------------------------------------- CLI
def _vtext(v):
    if isinstance(v, V):
        s = v.text()
        if v.source and not v.proposed: s += f"   ({v.source})"
        if v.proposed and v.note: s += f"   — {v.note}"
        return s
    return str(v)


def _show(cat, key):
    st = cat.get(key)
    amber = "\033[33m" if sys.stdout.isatty() else ""; off = "\033[0m" if amber else ""
    def line(lab, v):
        s = _vtext(v); c = amber if is_prop(v) else ""
        print(f"  {lab:<14} {c}{s}{off if c else ''}")
    print(f"{key} — {st.name}  [{st.kind}]  {st.raw['status']}")
    for f in ("factory", "crown_die", "brim_die", "panels", "structure", "crown_profile", "brim", "closure", "size"):
        if f in st.t: line(f, st.t[f])
    if st.kind == "knit":
        for f, v in st.t["knit"].items(): line(f"knit.{f}", v)
    print("  POM (cm):")
    for c, p in st.pom.items(): line(f"  {c} {p.name}"[:14], p.v)
    print("  products: " + ("; ".join(p["name"] + (" [proposed]" if p.get("proposed") else "") for p in st.raw["products"]) or "none"))
    print(f"  {len(st.proposed())} values still {TAG} (F1)")


def main(argv=None):
    a = sys.argv[1:] if argv is None else argv
    cmd = a[0] if a else "list"
    try:
        if cmd == "check-project":
            if len(a) < 2: print("usage: capstyle.py check-project <slug> [--root DIR]"); return 2
            root = a[a.index("--root") + 1] if "--root" in a else None
            garment, style = project_info(a[1], root)
            cat = load()
            if garment is None:
                print(f"projects/{a[1]}: no garment recorded (STATUS.json / inputs/brief.md)"); return 0
            err = check_choice(garment, style, cat)
            if err: print(f"REFUSED projects/{a[1]}: {err}"); return 1
            print(f"projects/{a[1]}: {garment}" + (f" on style {style} ({cat.styles[style].name})" if style else " (not a hat)"))
            return 0
        cat = load()
        if cmd == "list":
            for k, s in cat.styles.items():
                prods = ", ".join(p["name"] for p in s.raw["products"]) or "—"
                print(f"{k:<14} {s.name:<38} {s.kind:<6} {s.raw['status']}\n{'':<14} products: {prods}")
            return 0
        if cmd == "show":
            if len(a) < 2: print(f"usage: capstyle.py show <key>. Valid styles: {cat.valid_keys_text()}"); return 2
            _show(cat, a[1]); return 0
        if cmd == "check":
            n = sum(len(s.proposed()) for s in cat.styles.values())
            print(f"OK: {len(cat.styles)} hat styles valid ({', '.join(cat.keys())}); {n} proposed values across them go to F1")
            return 0
        if cmd == "product":
            k, p = cat.product_style(" ".join(a[1:]))
            if not k: print(f"no style known for '{' '.join(a[1:])}'"); return 1
            print(f"{k} ({cat.styles[k].name})" + (f"  [proposed: {p['proposed']}]" if p.get("proposed") else f"  source: {p.get('source')}"))
            return 0
        print(__doc__); return 2
    except StyleError as e:
        print(f"ERROR: {e}"); return 1


if __name__ == "__main__":
    sys.exit(main())
