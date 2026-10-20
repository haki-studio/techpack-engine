"""Technique plugins (ENGINE_PLAN M1). Each plugin turns ONE part into blocks of needle points, at the part's declared
direction, with the numbers of its StitchSpec. A run switches plugins on and off in run.yaml (`techniques:`); the
rulebook picks the first enabled one per kind.

Contract (tests/test_digitize_m1.py::test_registry_contract plans a synthetic part with every plugin):
  name       registry key (the rulebook's technique name)
  stype      what dst2's router calls the object: "tatami" / "satin" (fills that hide travel) or "run" / "bean"
  check(part, principles) -> [issue dict]   type-follows-shape problems (rule 4), for the review questions
  plan(part)              -> [Block]        underlay first, then the top layer; every stitch <= 7 mm
  estimate(part)          -> stitches
  sequencing              -> dict: hints for sequence.py (e.g. {"after_fill": True} for line work, {"open_layer": True}
                             for blends / shading: nothing is cut under them)

  from digitize import techniques
  techniques.get("tatami").plan(part)
"""
import math

REGISTRY = {}


def register(cls):
    inst = cls()
    if not inst.name: raise ValueError(f"{cls.__name__}: technique without a name")
    REGISTRY[inst.name] = inst
    return cls


def get(name):
    _load_all()
    if name not in REGISTRY: raise KeyError(f"no technique plugin {name!r} (have {sorted(REGISTRY)})")
    return REGISTRY[name]


def names():
    _load_all(); return sorted(REGISTRY)


def _load_all():
    from digitize.techniques import tatami, satin, split_satin, run, bean, guided_fill, contour_fill, blend  # noqa: F401  (registers)


# ---------------------------------------------------------------- shared shape helpers
def polys(g):
    if g.is_empty: return []
    if g.geom_type == "Polygon": return [g]
    return [p for p in getattr(g, "geoms", []) if p.geom_type == "Polygon"]


def fits_width(g, w):
    """True when a disc of diameter w fits somewhere inside g (the part is at least w wide somewhere)"""
    return not g.buffer(-w / 2.0).is_empty


def width_of(g):
    return 2.0 * g.area / max(g.length, 1e-9)


def aspect_of(g):
    r = g.minimum_rotated_rectangle
    if r.geom_type != "Polygon": return 1.0
    c = list(r.exterior.coords); e = sorted(math.dist(c[i], c[i + 1]) for i in range(4))
    return e[-1] / max(e[0], 1e-6)


class Technique:
    name = ""
    stype = "tatami"
    sequencing = {}

    def check(self, part, principles):
        return []

    def plan(self, part):
        raise NotImplementedError

    def estimate(self, part):
        return sum(len(b.pts) for b in self.plan(part))

    def issue(self, part, text, **kw):
        return dict(part=part.id, technique=self.name, kind=part.kind, text=text, **kw)


# ---------------------------------------------------------------- ENGINE_PLAN M5 (SVG parity on Konpeito): patch plugins
# column_satin (lettering / line art / heat-cut edge, density as same_side), dot (bead dots), radial (florets, stars,
# rings), turning_satin (petals / candy lobes along a declared axis). Registered on top of the M1 set by an appended
# hook, so the M1/M2 import line in _load_all above stays untouched (fold it in once both milestones are merged).
_load_m1 = _load_all


def _load_all():
    _load_m1()
    from digitize.techniques import column_satin, dot, radial, turning  # noqa: F401  (registers)
