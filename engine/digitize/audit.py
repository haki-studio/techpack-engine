"""Audits for the gates stage (ENGINE_PLAN M2; M1 review follow-ups 1 and 3). Everything here reads the plan and the
WRITTEN file (compile.labelled_dst), never the in-memory stitches.

  angle_audit(plan, rb)                  every part's declared angle re-derived from its source -> random_angles
  sewn_angles(plan, segs, labels)        each fixed-angle part's VISIBLE stitches vs its declared angle (the file
                                         agrees with the plan) -> sewn_off_angle
  direction_by_source(dm, plan, crop)    direction_match tiles split by where the top part's direction came from:
                                         INDEPENDENT (a house rule, an answer, a depth rule: not read from the reference
                                         the gate grades against) vs SELF-DERIVED (field-mean / field: measured from
                                         the SAME reference pixels, so an OK there is consistency, not evidence) vs
                                         OUTLINE (contour fills: rows follow the traced outline)

random_angles was hard-coded 0 in M1. A declared angle is "random" (unexplained) when it cannot be re-derived:
  rule        the rulebook's number for the kind
  field-mean  direction.grid_mean(part.meta["field"], part.geom), RECOMPUTED (the recorded meta["field_angle"] must agree)
  field       the same for guided parts (meta["field_mean"] must agree): a basis typed into meta does not pass
  depth       direction.depth_angle(part.meta["depth"])
  answer      part.meta["answer_angle"] (the person's answer, M4)
  outline     part.meta["outline_angle"] (contour fill: the lobe's long axis, for the part map only)
plus the recorded adjustments, each within the house limit: meta["sep_deg"] (rule 3 neighbour separation, |x| <= 25)
and meta["band_offset_deg"] (stratum bands alternate +-, |x| <= 12.5). Anything else, e.g. an angle from
rng.uniform, is counted, listed, and fails the angle check."""
import math
import numpy as np

INDEPENDENT = ("rule", "answer", "depth")
SELF_DERIVED = ("field-mean", "field")
OUTLINE = ("outline",)
SEP_MAX, BAND_MAX = 25.0, 12.5


def axial_diff(a, b):
    d = abs((a - b) % 180.0); return min(d, 180.0 - d)


def _depth(t):
    from digitize.direction import depth_angle
    return depth_angle(t)


def field_basis(p, tol=0.5):
    """(basis, why): for field / field-mean parts the basis is RECOMPUTED from the stored field grid over the part's
    geometry (direction.grid_mean), never read from meta alone; a recorded basis that disagrees by more than tol is
    reported (0.5 deg: plan.json stores geometry to 1 micron, which moves a grid point on the outline in or out)"""
    from digitize.direction import grid_mean
    key = {"field": "field_mean", "field-mean": "field_angle"}[p.dir.source]
    if not p.meta.get("field"): return None, f"{p.dir.source} part without a stored field grid: its basis cannot be recomputed"
    b = grid_mean(p.meta["field"], p.geom)
    if b is None: return None, "the stored field grid does not cover the part"
    rec = p.meta.get(key)
    if rec is None or axial_diff(b, float(rec)) > tol:
        return None, f"recorded {key} {rec} != {round(b, 2)} recomputed from the stored field grid"
    return b, None


def basis(p, rb):
    s, m = p.dir.source, p.meta
    if s in ("field", "field-mean"): return field_basis(p)[0]
    if s == "rule":
        d = rb.rule(p.kind).get("dir")
        return float(d) if isinstance(d, (int, float)) else None
    return {"field-mean": m.get("field_angle"), "field": m.get("field_mean"), "answer": m.get("answer_angle"),
            "outline": m.get("outline_angle"), "depth": _depth(m["depth"]) if "depth" in m else None}.get(s)


def angle_audit(plan, rb, tol=0.05):
    bad = []
    for p in plan.parts:
        b = basis(p, rb); sep = float(p.meta.get("sep_deg", 0.0)); band = float(p.meta.get("band_offset_deg", 0.0))
        why = None
        if b is None: why = (field_basis(p)[1] if p.dir.source in ("field", "field-mean") else None) or f"no basis for source {p.dir.source!r}"
        elif abs(sep) > SEP_MAX + tol: why = f"separation turn {sep} > {SEP_MAX}"
        elif abs(band) > BAND_MAX + tol: why = f"band offset {band} > {BAND_MAX}"
        elif axial_diff(float(b) + sep + band, p.dir.angle) > (0.5 if p.dir.source in SELF_DERIVED else tol):
            why = f"declared {p.dir.angle} != {p.dir.source} basis {round(float(b), 2)} + sep {sep} + band {band}"
        if why: bad.append(dict(part=p.id, kind=p.kind, source=p.dir.source, angle=p.dir.angle, why=why))
    return dict(random_angles=len(bad), unexplained=bad[:40])


def sewn_angles(plan, segs, labels, crop, ppm=12.0, max_dev=15.0, min_segs=12, min_len=0.6):
    """per fixed-angle part: the length-weighted axial mean of its VISIBLE stitches in the written file vs its declared
    angle. Field / contour parts are judged per stitch against their own planned direction (field_adherence)."""
    import qa
    from digitize import direction as DR
    vis, idx = qa.visible_segments(segs, crop, ppm=ppm, return_index=True)
    by = {}
    for s, i in zip(vis, idx):
        pid = labels[i]
        if pid is None: continue
        L = math.hypot(s[2] - s[0], s[3] - s[1])
        if L >= min_len: by.setdefault(pid, []).append(s)
    off, field = [], dict(parts=0, stitches=0, within=0)
    for p in plan.parts:
        S = by.get(p.id, [])
        if len(S) < min_segs: continue
        A = np.array([math.atan2(s[3] - s[1], s[2] - s[0]) for s in S]); W = np.array([math.hypot(s[2] - s[0], s[3] - s[1]) for s in S])
        if p.dir.mode == "fixed":
            a = math.degrees(0.5 * math.atan2((W * np.sin(2 * A)).sum(), (W * np.cos(2 * A)).sum())) % 180
            d = axial_diff(a, p.dir.angle)
            if d > max_dev: off.append(dict(part=p.id, kind=p.kind, declared=p.dir.angle, sewn=round(a, 1), dev=round(d, 1), n=len(S)))
        elif p.dir.mode == "field" and p.meta.get("field"):
            g = p.meta["field"]; mx = np.array([(s[0] + s[2]) / 2 for s in S]); my = np.array([(s[1] + s[3]) / 2 for s in S])
            want = DR.grid_angle(g, mx, my, offset_deg=p.dir.angle - p.meta.get("field_mean", p.dir.angle))
            got = np.degrees(A) % 180; dd = np.abs((got - want) % 180); dd = np.minimum(dd, 180 - dd)
            field["parts"] += 1; field["stitches"] += len(S); field["within"] += int((dd <= max_dev).sum())
    field["pct_within"] = round(100.0 * field["within"] / max(1, field["stitches"]), 1)
    return dict(sewn_off_angle=len(off), off=off[:40], field_adherence=field)


def bucket(source):
    if source in INDEPENDENT: return "independent"
    if source in SELF_DERIVED: return "self-derived"
    if source in OUTLINE: return "outline"
    return "other"


def direction_by_source(dm, top_part_at):
    """dm: qa.direction_match result; top_part_at(centre) -> Part or None (the top-most part under the tile centre)"""
    per = {}
    def add(c, k):
        p = top_part_at(c); b = bucket(p.dir.source) if p is not None else "bare"
        per.setdefault(b, [0, 0, 0])[k] += 1
    for c in dm["ok_tiles"]: add(c, 0)
    for r in dm["fail_dev"]: add(r["at_mm"], 1)
    for r in dm["fail_chaos"]: add(r["at_mm"], 2)
    return {k: dict(tiles=sum(v), ok=v[0], dev=v[1], chaos=v[2], pct_ok=round(100 * v[0] / max(1, sum(v)), 1),
                    pct_chaos=round(100 * v[2] / max(1, sum(v)), 1)) for k, v in sorted(per.items())}
