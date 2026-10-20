"""Decoration methods (methods.yaml) + one Decoration per entry in a variant's `decorations:` list."""
import os
import yaml
from .spec import V, SpecError, val, is_prop, resolve

HERE = os.path.dirname(os.path.abspath(__file__))
VIEWS = ("front", "back")


def load(path=None):
    return yaml.safe_load(open(path or os.path.join(HERE, "methods.yaml")))


class Decoration:
    """placement in cm on the flat: view front/back; centre_from_cf_cm (+ = wearer's LEFT on a front, wearer's RIGHT on
    a back view = viewer's right, as the engine's garment coords); top_below_hps_cm = top edge of the art below the HPS
    line; width_cm / height_cm = one value or a per-size {S: .., M: ..} map."""

    def __init__(self, d, i, spec):
        p = f"decorations[{i}]"
        self.i, self.d, self.spec = i, d, spec
        self.name = val(d.get("name"), f"Decoration {i + 1}")
        self.code = f"D{i + 1}"
        if "method" not in d: raise SpecError(f"{p} ({self.name}): missing 'method:' — one of {', '.join(spec.methods)}")
        self.method_v = d["method"] if isinstance(d["method"], V) else V(d["method"], path=f"{p}.method")
        m = str(val(self.method_v))
        if m not in spec.methods:
            raise SpecError(f"{p} ({self.name}): unknown method '{m}'. Known methods: {', '.join(spec.methods)} "
                            f"(add a new one to engine/family/methods.yaml)")
        self.method = m
        self.mdef = spec.methods[m]
        self.view = val(d.get("view"), "front")
        if self.view not in VIEWS: raise SpecError(f"{p} ({self.name}): view '{self.view}' — use front or back")
        for k in ("width_cm", "height_cm"):
            if k not in d: raise SpecError(f"{p} ({self.name}): missing '{k}:'")
        tops = [k for k in ("top_below_hps_cm", "top_below_neck_cm") if k in d]
        if len(tops) != 1:
            raise SpecError(f"{p} ({self.name}): give exactly one of top_below_hps_cm (from the HPS line) or "
                            f"top_below_neck_cm (from the CF / CB neck seam, under the rib)")
        self.top_ref = "hps" if tops[0] == "top_below_hps_cm" else "neck"
        self.cx = d.get("centre_from_cf_cm", V(0.0, path=f"{p}.centre_from_cf_cm"))
        self.top, self.w, self.h = d[tops[0]], d["width_cm"], d["height_cm"]
        self.art = d.get("artwork") or {}
        self.colours = d.get("colours") or []
        self.notes = d.get("notes") or []
        self.spec_over = d.get("spec") or {}
        unknown = set(self.spec_over) - set(self.mdef["fields"])
        if unknown:
            raise SpecError(f"{p} ({self.name}): spec field(s) {sorted(unknown)} not defined for method '{m}' "
                            f"(fields: {', '.join(self.mdef['fields'])})")
        self._fields = None

    @property
    def stub(self): return bool(self.mdef.get("stub"))
    @property
    def label(self): return self.mdef["label"]

    def per_size(self, x, size):
        if isinstance(x, dict):
            if size not in x: raise SpecError(f"{self.code} {self.name}: no value for size {size} in {list(x)}")
            x = x[size]
        return x

    def box_mm(self, size):
        """(x0, y0, x1, y1) of the art box in flat coords (mm; x from CF/CB, y down from the HPS line)"""
        w = float(val(self.per_size(self.w, size))) * 10; h = float(val(self.per_size(self.h, size))) * 10
        cx = float(val(self.per_size(self.cx, size))) * 10; top = float(val(self.per_size(self.top, size))) * 10
        if self.top_ref == "neck": top += self.neck_seam_mm(size)
        return (cx - w / 2, top, cx + w / 2, top + h)

    def neck_seam_mm(self, size):
        """HPS line -> neck seam (under the rib) at CF / CB: neck drop + band height, from the chart"""
        return self.spec.flat(size).neck_seam(self.view == "back")

    def placement_proposed(self):
        return any(is_prop(self.per_size(x, s)) for x in (self.cx, self.top, self.w, self.h) for s in self.spec.sizes
                   if not (isinstance(x, dict) and s not in x))

    def fields(self):
        """[(label, V)] — the method's spec block; defaults are proposed, variant `spec:` entries override"""
        if self._fields is None:
            from . import factory_profile
            out = []
            for k, fd in self.mdef["fields"].items():
                if k in self.spec_over:
                    v = self.spec_over[k]
                    if not isinstance(v, V): v = V(v)
                else:
                    txt = str(fd["default"]).replace("{needles}", str(factory_profile().get("needles", "?")))
                    v = V(txt, True, None, "method default (engine/family/methods.yaml)", f"decorations[{self.i}].spec.{k}")
                out.append((fd["label"], v))
            self._fields = out
        return self._fields

    def method_fields_proposed(self):
        return [v for _, v in self.fields() if v.proposed]

    def art_path(self):
        return resolve(val(self.art.get("file")), self.spec.var_dir) if self.art else None
