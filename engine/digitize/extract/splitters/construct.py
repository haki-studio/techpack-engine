"""Constructed directions (ENGINE_PLAN M3b): angles BUILT from a part's geometry by a playbook rule, never read from the
reference grain. Each part stores its construction in part.meta["construct"] with DirSpec(source="splitter"), and
digitize.audit RECOMPUTES the angle from it (basis()), so a typed-in angle without a matching construction is counted as
random (LESSONS A23 / A24).

  rule "axis"          trunk strips / branches: stitches ALONG the traced axis. construct = {rule, line: [[x, y], [x, y]]}
                       (the strip's medial-axis chord). Checks: the chord's midpoint lies on the part (within 1.5 mm) and
                       the chord is at least 1.5 x the part's mean width long (a stroke, not a blob).
  rule "fan"           crown clumps: rows fan out from the clump's support along the clump. construct = {rule, from: [x, y]
                       (the clump's long-axis end nearer its attachment), to: [x, y] (the axis middle)}; angle = from -> to.
                       Checks: `to` lies on the part (within 2 mm), `from` within 6 mm of it. Built from the traced
                       OUTLINE, so audit.bucket_of puts these parts in the "outline" bucket (OUTLINE_RULES), not independent.
  rule "between_petals" knots: the bead rows sit across the floret's first petal, between two petal axes (phase + 90
                       + 18: 5 petals are 36 deg apart axially). construct = {rule, phase}.
  rule "column"        branches (DirSpec mode "contour"): a satin column ACROSS the stroke along the traced centreline;
                       the declared angle is across the centreline's mean direction (polyline_angle) + 90. Check: the centreline's middle lies on
                       the part, and it is >= 1.5 x the part's width long. The file is judged per stitch (trunk.column_adherence).
  rule "radial"        face-on florets (DirSpec mode "radial"): every stitch on a ray from the floret centre; the declared
                       angle is the conventional 0. construct = {rule}; the centre is part.meta["centre"], the ONE field
                       the radial plugin sews from, the audit rebuilds from and the file check (blossom.radial_adherence)
                       reads (PR #10 review). Check: the centre exists and lies on the floret (within 1.5 mm, the knot hole).
plus the recorded adjustments digitize.audit already allows (meta sep_deg <= 25, band_offset_deg <= 12.5).

Independence (A24): axis / radial / between_petals angles come from POSITIONS (where the trunk runs, the floret centre),
not from the luminance grain the direction gate measures: independent. Caveat (BENCH_m3b.md): on a long thin trunk the
outline and the grain are not fully separable (its own edges run along the axis too). fan angles are the clump's traced
elongation: reported as "outline", never as independent."""
import math

RULES = ("axis", "fan", "between_petals", "radial", "column")
OUTLINE_RULES = ("fan",)          # angles read off the traced outline's shape: not independent of the reference (A24)


def line_angle(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0


def polyline_angle(cl):
    """the length-weighted axial mean direction of a polyline's segments (deg): a branch's overall run, robust to the
    centreline's ends turning into the outline's corners"""
    C = S = 0.0
    for a, b in zip(cl, cl[1:]):
        L = math.dist(a, b); t = math.atan2(b[1] - a[1], b[0] - a[0])
        C += L * math.cos(2 * t); S += L * math.sin(2 * t)
    return math.degrees(0.5 * math.atan2(S, C)) % 180.0


def _width(g):
    return 2.0 * g.area / max(g.length, 1e-9)


def basis(p):
    """(angle, why) for a part whose DirSpec.source is "splitter": the angle re-built from meta["construct"]; why is the
    reason it cannot be (None when it can)."""
    from shapely.geometry import Point, LineString
    c = (p.meta or {}).get("construct")
    if not c: return None, "splitter angle without a stored construction (meta construct)"
    r = c.get("rule")
    if r == "axis":
        a, b = c["line"]; L = math.dist(a, b)
        mid = Point((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        if p.geom.distance(mid) > 1.5: return None, "axis chord does not lie on the part"
        if L < 1.5 * _width(p.geom): return None, f"axis chord {L:.1f} mm shorter than 1.5 x the part's width (not a stroke)"
        return line_angle(a, b), None
    if r == "fan":
        f, t = c["from"], c["to"]
        if math.dist(f, t) < 0.5: return None, "fan origin and clump centre coincide"
        if p.geom.distance(Point(t)) > 2.0: return None, "fan target is not on the clump"
        if p.geom.distance(Point(f)) > 6.0: return None, "fan origin is more than 6 mm from the clump (clump does not touch its support)"
        return line_angle(f, t), None
    if r == "between_petals":
        return (float(c["phase"]) + 90.0 + 18.0) % 180.0, None
    if r == "column":
        cl = c["cl"]
        if len(cl) < 2: return None, "column centreline has < 2 points"
        mid = cl[len(cl) // 2]
        if p.geom.distance(Point(mid)) > 1.5: return None, "column centreline does not lie on the part"
        if LineString(cl).length < 1.5 * _width(p.geom): return None, "column shorter than 1.5 x its width (not a stroke)"
        return (polyline_angle(cl) + 90.0) % 180.0, None
    if r == "radial":
        if p.dir.mode != "radial": return None, "radial construction on a part that is not in radial mode"
        cen = (p.meta or {}).get("centre")
        if not cen: return None, "radial part without meta centre (the field the plugin sews from and the file check reads)"
        if p.geom.distance(Point(cen)) > 1.5: return None, "radial centre is not on the floret"
        return 0.0, None
    return None, f"unknown construction rule {r!r} (have {RULES})"
