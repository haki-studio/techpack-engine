"""The digitizing plan as data (ENGINE_PLAN M1): what is sewn, as PARTS, each with one deliberate direction.

  Part        one semantic object (a sky band, a fall cord, a pool, a zone stub): geometry (garment mm, y down), kind,
              thread, z (sew depth: lower sews first), DirSpec, and, once planned, the technique + StitchSpec.
  Layer       a named z level (sky 0, ground 1, falls 3, ...): the z-DAG's coarse order.
  DirSpec     the stitch direction of a part. NEVER "auto" (LESSONS A16, DIGITIZING_PRINCIPLES rule 2): a direction is a
              design decision with a source ("rule", "field-mean", "splitter"), so a missing one raises here, at
              construction, not as a silent by-product of a traced blob.
  StitchSpec  technique + its numbers (spacing, stitch length, underlay, pull compensation, params).
  Block       one run of needle points (mm) for one part: underlay or top. compile.py hands blocks to dst2 unchanged.
  ObjectPlan  parts + layers + threads + stops (sew order) + blocks: plan.json, with WKT geometry.

Everything round-trips through JSON (to_json / from_json) so a plan can be reviewed, answered (the future PLM question
step) and re-compiled without re-running extraction."""
import json, math
from dataclasses import dataclass, field, asdict
from typing import Optional
from shapely import wkt as _wkt
from shapely.geometry.base import BaseGeometry

DIR_MODES = ("fixed", "field", "contour", "radial")   # fixed angle (M1); "field": rows follow part.meta["field"] (guided fill, M2),
                                            # "radial" (M3b): rays from part.meta["centre"] (face-on florets, rule 4);
                                            # angle = the field's mean + offset; "contour": rows follow the outline (M2)
DIR_SOURCES = ("rule", "field-mean", "splitter", "answer", "field", "depth", "outline", "label")   # digitize.audit re-derives each
# --- G1 --- "label": the labeller's deliberate angle (parts.labels.json intent "angle"), audited from meta label_angle


class PlanError(ValueError):
    pass


@dataclass
class DirSpec:
    """angle in degrees, garment frame (0 = along +x, 90 = along +y / down the garment), axial (0 == 180)."""
    angle: float
    mode: str = "fixed"
    source: str = "rule"
    note: str = ""

    def __post_init__(self):
        if isinstance(self.angle, str) or self.angle is None or isinstance(self.mode, str) and self.mode.lower() == "auto":
            raise PlanError(f"DirSpec: direction {self.angle!r} / mode {self.mode!r} is not a declared angle. A direction "
                            f"is a design decision (DIGITIZING_PRINCIPLES rule 2): give a number with its source.")
        if self.mode not in DIR_MODES: raise PlanError(f"DirSpec: mode {self.mode!r} not in {DIR_MODES}")
        if self.source not in DIR_SOURCES: raise PlanError(f"DirSpec: source {self.source!r} not in {DIR_SOURCES}")
        a = float(self.angle)
        if not math.isfinite(a): raise PlanError(f"DirSpec: angle {a} is not finite")
        self.angle = round(a % 180.0, 2)


@dataclass
class StitchSpec:
    technique: str
    spacing: float = 0.45               # row spacing mm (tatami / satin density)
    stitch_len: float = 3.5             # mm (tatami stitch, run stitch, split satin max piece)
    underlay: list = field(default_factory=list)   # e.g. ["edge_run", "lattice_90"], ["centre_run"]
    pull_comp: float = 0.2
    params: dict = field(default_factory=dict)


@dataclass
class Layer:
    name: str
    z: float
    note: str = ""


@dataclass
class Part:
    id: str
    kind: str
    geom: BaseGeometry
    thread: str
    z: float
    dir: DirSpec
    zone: str = ""
    technique: Optional[str] = None
    stitch: Optional[StitchSpec] = None
    rgb: Optional[tuple] = None          # mean evidence colour (0-255), for thread planning
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.dir, DirSpec):
            raise PlanError(f"part {self.id}: dir must be a DirSpec, got {self.dir!r} (never 'auto')")

    @property
    def area(self): return float(self.geom.area)


@dataclass
class Block:
    part: str
    role: str                            # "underlay" | "top"
    pts: list                            # [(x, y)] mm, needle-down in order


@dataclass
class ObjectPlan:
    name: str
    parts: list
    layers: list = field(default_factory=list)
    threads: dict = field(default_factory=dict)      # id -> dict(hex, name, protected)
    stops: list = field(default_factory=list)        # [dict(thread, parts=[ids in sew order])]
    blocks: dict = field(default_factory=dict)       # part id -> [Block]
    meta: dict = field(default_factory=dict)

    def part(self, pid):
        for p in self.parts:
            if p.id == pid: return p
        raise KeyError(pid)

    # ---------------------------------------------------------------- JSON (WKT geometry)
    def to_dict(self, with_blocks=True):
        def pd(p):
            d = dict(id=p.id, kind=p.kind, zone=p.zone, thread=p.thread, z=p.z, dir=asdict(p.dir), technique=p.technique,
                     stitch=asdict(p.stitch) if p.stitch else None, rgb=list(p.rgb) if p.rgb is not None else None,
                     area_mm2=round(p.area, 2), meta=p.meta, wkt=_wkt.dumps(p.geom, rounding_precision=3))
            return d
        out = dict(name=self.name, layers=[asdict(l) for l in self.layers], threads=self.threads, stops=self.stops,
                   meta=self.meta, parts=[pd(p) for p in self.parts])
        if with_blocks:
            out["blocks"] = {pid: [dict(role=b.role, pts=[[round(x, 3), round(y, 3)] for x, y in b.pts]) for b in bl]
                             for pid, bl in self.blocks.items()}
        return out

    def to_json(self, path, with_blocks=True):
        json.dump(self.to_dict(with_blocks), open(path, "w"), indent=None, separators=(",", ":"), default=float)
        return path

    @classmethod
    def from_dict(cls, d):
        parts = []
        for q in d["parts"]:
            st = StitchSpec(**q["stitch"]) if q.get("stitch") else None
            g = _wkt.loads(q["wkt"])
            if not g.is_valid: g = g.buffer(0)
            parts.append(Part(id=q["id"], kind=q["kind"], geom=g, thread=q["thread"], z=q["z"],
                              dir=DirSpec(**q["dir"]), zone=q.get("zone", ""), technique=q.get("technique"), stitch=st,
                              rgb=tuple(q["rgb"]) if q.get("rgb") is not None else None, meta=q.get("meta", {})))
        blocks = {pid: [Block(part=pid, role=b["role"], pts=[tuple(p) for p in b["pts"]]) for b in bl]
                  for pid, bl in d.get("blocks", {}).items()}
        return cls(name=d["name"], parts=parts, layers=[Layer(**l) for l in d.get("layers", [])], threads=d.get("threads", {}),
                   stops=d.get("stops", []), blocks=blocks, meta=d.get("meta", {}))

    @classmethod
    def from_json(cls, path): return cls.from_dict(json.load(open(path)))
