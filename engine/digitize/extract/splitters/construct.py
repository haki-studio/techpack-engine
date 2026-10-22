"""Constructed directions (ENGINE_PLAN M3b; the ONE basis for every constructed angle since the M3a / M3b merge, PR #10
review): angles BUILT from a part's geometry by a playbook rule, never read from the reference grain. digitize.audit
RECOMPUTES every one through basis() here, so a typed-in angle without a matching construction is counted as random
(LESSONS A23 / A24), and bucket_of() here decides which constructed angles may count as independent evidence.

Two ways a part names its rule:
  M3b  DirSpec(source="splitter") + part.meta["construct"] = {rule, ...}: the rules below.
  M3a  DirSpec(source="rule") on a kind whose house.yaml dir is "construct": the kind's `construct:` names the rule
       (course / down_slope / across, M3A_RULES), re-derived from the fitted points the part stores by
       extract/building_fit.rule_basis (the depth rule reads the zone's other roofs: `peers`).

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

RULES = ("axis", "fan", "between_petals", "radial", "column", "fan_smooth", "long_axis")   # --- M4c --- fan_smooth (crown.py); G1 long_axis
M3A_RULES = ("course", "down_slope", "across")   # building fitter (extract/building_fit.py), registered behind basis()
OUTLINE_RULES = ("fan", "fan_smooth", "long_axis")          # angles read off the traced outline's shape: not independent of the reference (A24)
DEPTH_RULES = ("course", "down_slope")   # M3a rule 3 depth: a FAR tier's angle (rows along the eave) was chosen where the
                                         # render's grain agreed (BENCH_m3a.md "partly grain-informed"): reported as outline


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


def rule_of(p, rb=None):
    """the construction rule a part's angle comes from (M3b meta construct, else the M3a kind's construct), or None"""
    c = (p.meta or {}).get("construct")
    if p.dir.source == "splitter": return c.get("rule") if c else None
    if p.dir.source == "rule" and rb is not None:
        k = rb.rule(p.kind)
        if k.get("dir") == "construct": return k.get("construct")
    return None


def is_constructed(p, rb=None):
    return p.dir.source == "splitter" or rule_of(p, rb) in M3A_RULES


def basis(p, rb=None, peers=None):
    """(angle, why): the constructed angle RE-BUILT (M3b: from meta["construct"]; M3a: building_fit.rule_basis from the
    fitted points, peers = the plan's parts for the depth rule); why is the reason it cannot be (None when it can)."""
    if (p.meta or {}).get("construct"): return _m3b_basis(p, peers)      # M3b (and the splitters' own probes)
    if p.dir.source == "rule":
        r = rule_of(p, rb)
        if r not in M3A_RULES: return None, f"source rule without a construct rule (kind {p.kind!r})"
        from digitize.extract.building_fit import rule_basis
        a = rule_basis(p, rb, peers)
        return (a, None) if a is not None else (None, f"M3a rule {r!r}: the part does not store the fitted points it needs")
    return _m3b_basis(p)


def bucket_of(p, rb=None, peers=None):
    """"independent" / "outline" for a constructed part (None when it is not constructed): fans read off the outline
    (OUTLINE_RULES) and M3a's FAR tiers (DEPTH_RULES with the depth rule on and the tier far) are "outline"."""
    r = rule_of(p, rb)
    if r is None: return None
    if r in OUTLINE_RULES: return "outline"
    if r in DEPTH_RULES and rb is not None and _far(p, rb, peers): return "outline"
    return "independent"


def _far(p, rb, peers):
    from digitize.extract import building_fit as BF
    k = rb.rule(p.kind); prm = rb.rule(k.get("params_from", p.kind)).get("params", {}); rel = prm.get("near_tier_rel")
    if rel is None or peers is None or not p.meta.get("eave_pts") or not p.meta.get("top_pts"): return False
    try: return bool(BF.is_far(p.meta["eave_pts"], p.meta["top_pts"], rel, BF.zone_tier_ref(peers, p.zone)))
    except (KeyError, TypeError, IndexError): return False


def _m3b_basis(p, peers=None):
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
    if r == "fan_smooth":                                             # --- M4c --- crown clumps, a smooth fan
        return _fan_smooth(p, c, peers)
    if r == "long_axis":                                              # --- G1 --- lobes (primitives/lobe.py)
        return _long_axis(p, c)
    return None, f"unknown construction rule {r!r} (have {RULES})"


SMOOTH_NB_MM = 25.0      # a neighbour's axis middle lies within this of the part (the clumps touch; a clump is <= ~20 mm)
LIT_AXIS_MM = 12.0       # a lit piece lies inside its clump: the clump's axis middle within this of the piece


def _fan_smooth(p, c, peers=None):
    """M4c rule "fan_smooth" (crown clumps): construct = {rule, axes: [{from, to, w}, ...], at (lit pieces)}. The first axis
    is the clump's own fan (its long axis from the attachment end, as rule "fan"), the others the touching clumps' fans;
    angle = their weighted AXIAL mean (crown.smooth_angle). Checks: a dark clump's own axis passes the "fan" checks (`to`
    on the clump within 2 mm, `from` within 6 mm: the clump touches its support; the clump = the dark part plus the lit
    pieces in `peers` that name it in lit_of, since the axis middle may lie in a knocked-out lit piece); a lit piece holds its `at` point (1.5 mm)
    and its clump's axis middle is within LIT_AXIS_MM; every neighbour's axis middle within SMOOTH_NB_MM; weights > 0.
    Built from traced outlines: reported as "outline" (OUTLINE_RULES), never independent (A24)."""
    from shapely.geometry import Point
    ax = c.get("axes") or []
    if not ax: return None, "fan_smooth without axes"
    for a in ax:
        if not (a.get("w", 0) > 0): return None, "fan_smooth axis with weight <= 0"
        if math.dist(a["from"], a["to"]) < 0.5: return None, "fan_smooth axis origin and middle coincide"
    own = ax[0]
    if p.kind == "crown_clump_lit":
        if not c.get("at") or p.geom.distance(Point(c["at"])) > 1.5: return None, "fan_smooth lit piece does not hold its `at` point"
        if p.geom.distance(Point(own["to"])) > LIT_AXIS_MM: return None, f"fan_smooth: the clump's axis is more than {LIT_AXIS_MM} mm from its lit piece"
    else:
        clump = p.geom                    # the clump = this dark part + its own lit pieces (peers naming it in lit_of):
        if peers:                         # the axis middle may sit in a lit piece knocked out of the dark
            from shapely.ops import unary_union
            clump = unary_union([p.geom] + [q.geom for q in peers if q is not p and (q.meta or {}).get("lit_of") == p.id])
        if clump.distance(Point(own["to"])) > 2.0: return None, "fan target is not on the clump"
        if clump.distance(Point(own["from"])) > 6.0: return None, "fan origin is more than 6 mm from the clump (clump does not touch its support)"
    for a in ax[1:]:
        if p.geom.distance(Point(a["to"])) > SMOOTH_NB_MM: return None, f"fan_smooth neighbour axis more than {SMOOTH_NB_MM} mm away (not a neighbour)"
    C = S = 0.0
    for a in ax:
        t = math.atan2(a["to"][1] - a["from"][1], a["to"][0] - a["from"][0]); C += a["w"] * math.cos(2 * t); S += a["w"] * math.sin(2 * t)
    return math.degrees(0.5 * math.atan2(S, C)) % 180.0, None


def _long_axis(p, c):
    """G1 rule "long_axis" (primitives lobe, cord stubs): rows along the long mid-line of the minimum rotated rectangle of
    construct["of"], the TRACED outline recorded at extraction (the lobe itself, or the lobe a lit / shade layer belongs
    to), else of the part. Sequencing reshapes a part afterwards (speck merges, underlap, cut-under), so the outline is
    recorded like M3b's fan points; the part must still overlap it by >= 50 % of the smaller area. Read off a traced outline: "outline" bucket (OUTLINE_RULES), never independent (A24)."""
    from shapely.geometry import Polygon
    from digitize.techniques.turning import long_axis
    g = p.geom
    if c.get("of"):
        g = Polygon(c["of"]).buffer(0)
        if g.is_empty: return None, "long_axis `of` outline is empty"
        if p.geom.intersection(g).area < 0.5 * min(p.geom.area, g.area): return None, "long_axis: the part does not overlap its recorded `of` outline"
    gp = g if g.geom_type == "Polygon" else max(getattr(g, "geoms", [g]), key=lambda q: q.area)
    if gp.is_empty or gp.area <= 0: return None, "long_axis on an empty part"
    a, b = long_axis(gp)
    if math.dist(a, b) < 1e-6: return None, "long_axis of a degenerate part"
    return line_angle(a, b), None
