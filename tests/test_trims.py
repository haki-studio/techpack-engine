"""Golden trim tests for the hidden-travel router (LESSONS B21-B24). Each design below is a pattern seen on the first
/techpack batch, cut down to a fixture that sews in a second; the bound is what the engine achieves today, the comment
says what the old engine did. Trims are read back from the DST (LESSONS B8)."""
import os, tempfile, collections
import pyembroidery as pe
from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union
import dst2, tech


def _sew(vis):
    stops = dst2.merge_stops(tech.stops(vis))
    b = dst2.bounds_of([r["geom"] for r in vis])
    pat, st = dst2.make_pattern(vis, stops, ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2))
    base = os.path.join(tempfile.mkdtemp(), "t"); dst2.write(pat, base)
    trims = collections.Counter(s[2] & pe.COMMAND_MASK for s in pe.read(base + ".dst").stitches)[pe.TRIM]
    return trims, st, stops, dst2.verify(base)


def R(col, geom, st, grp, layer):
    return dict(col=col, geom=geom, st=st, ang=0 if st == "tatami" else "auto", grp=grp, layer=layer, z=layer)


def striped_patch():
    """100 x 76 patch: 40 small gold details (sewn first) inside a field of 5 mm strips in two tones that sew AFTER them
    (slate strips, then a plum comb whose teeth sit between the slate strips). Every move between two details
    crosses a seam between the two later tones (Moon clouds, Grand Line sea)."""
    dots = [Point(8 + 12 * i, 8 + 12.5 * j).buffer(1.6) for i in range(8) for j in range(5)]
    D = unary_union(dots)
    slate = [box(10 * k + 5, 0, 10 * k + 10, 70).difference(D) for k in range(10)]
    plum = unary_union([box(10 * k, 0, 10 * k + 5, 70) for k in range(10)] + [box(0, 70, 100, 76)]).difference(D)
    return ([R("gold", d, "satin", "LF-shade", 2) for d in dots] + [R("slate", s, "tatami", "TR", 3) for s in slate]
            + [R("plum", plum, "tatami", "TR", 4)])


def test_travel_crosses_seams_between_later_fills():
    """B21: the later-stop mask is merged before it is inset. Old engine: each stop inset 0.25 mm on its own, a ~0.5 mm
    unhidden strip on every slate/plum seam, so detail-to-detail moves became trims (13 on this patch)."""
    trims, st, stops, v = _sew(striped_patch())
    assert trims <= 6, (trims, st.get("why"))
    assert v["max_stitch"] <= 7.5
    ex = dst2.exposed_travel(stops, [r for r in st["runs"] if r[0] == 0])     # the detail stop's travel
    assert not ex or max(ex) <= 1.0, max(ex)            # stays hidden (0.6 mm rule + raster slack)


def far_details():
    """4 details at the corners of a 200 mm square inside one big field that sews after them (Forestball water,
    Moon back): every move is ~200 mm, too long for the fine router's window."""
    dots = [Point(x, y).buffer(2.0) for x in (20, 220) for y in (20, 220)]
    field = box(0, 0, 240, 240).difference(unary_union(dots))
    return [R("gold", d, "satin", "LF-shade", 2) for d in dots] + [R("slate", field, "tatami", "TR", 3)]


def test_long_moves_inside_big_fills_are_routed():
    """B22: windows > ROUTE_MAX_PX are routed on a coarse grid and re-checked on the fine one. Old engine: every move
    whose window was over 900k px became a trim (4 here)."""
    trims, st, stops, v = _sew(far_details())
    assert trims <= 1, (trims, st.get("why"))
    ex = dst2.exposed_travel(stops, [r for r in st["runs"] if r[0] == 0])
    assert not ex or max(ex) <= 1.0, max(ex)


def holed_field():
    """120 x 60 field with 24 round holes (rocks / stones knocked out of water, sewn earlier)."""
    holes = unary_union([Point(10 + 20 * i + (5 if j % 2 else 0), 10 + 13 * j).buffer(3.5) for i in range(6) for j in range(4)])
    return box(0, 0, 120, 60).difference(holes)


def test_tatami_rows_sew_cell_by_cell_around_holes():
    """B23: rows are chained cell by cell. Old engine: rows were sewn in hatch order across every hole, so each row
    segment became its own block (one travel move per segment: 470 blocks here)."""
    p = holed_field()
    blocks = dst2.join_rows(dst2.tatami_rows(p, 0, dst2.SP_TAT))
    assert len(blocks) <= 120, len(blocks)
    # same rows, same stitches: only the order changed
    segs = sum(len(b) for b in dst2.tatami_rows(p, 0, dst2.SP_TAT))
    old = dst2.TATAMI_CHAIN; dst2.TATAMI_CHAIN = False
    try: segs_old = sum(len(b) for b in dst2.tatami_rows(p, 0, dst2.SP_TAT))
    finally: dst2.TATAMI_CHAIN = old
    assert abs(segs - segs_old) <= 0.02 * segs_old, (segs, segs_old)


def test_exposed_travel_reports_bare_fabric():
    """the QA helper itself: a run across bare fabric is reported, a run under a later fill is not."""
    stops = [dict(col="gold", regions=[R("gold", Point(0, 0).buffer(1), "satin", "LF-shade", 2)]),
             dict(col="slate", regions=[R("slate", box(-2, 10, 40, 20), "tatami", "TR", 3)])]
    assert dst2.exposed_travel(stops, [(0, [(0, 15), (30, 15)])]) == []
    ex = dst2.exposed_travel(stops, [(0, [(0, 0), (0, 30)])])
    assert ex and 8 < max(ex) < 10, ex      # 1.3 -> 9.7 and 20.3 -> 29.2 are bare


def thin_arcs():
    """two 3.2 mm wide tatami arcs sewn LAST on top of an earlier field (Moon wires, Forestball twigs): nothing later
    to hide under, so moves between an arc's blocks may only run inside the arc itself."""
    import math
    arcs = [LineString([(30 + 50 * k + 20 * math.cos(t / 20 * math.pi), 60 - 40 * math.sin(t / 20 * math.pi)) for t in range(21)]).buffer(1.6)
            for k in range(2)]
    field = box(0, 0, 130, 100).difference(unary_union(arcs))
    return [R("slate", field, "tatami", "TR", 2)] + [R("plum", a, "tatami", "TR", 3) for a in arcs]


def test_travel_inside_thin_objects_stays_inside():
    """B24: the router's `own` halo is OWN_HALO (0.25 mm, ~ pull comp). Old engine: 0.6 mm, so travel cut corners just
    outside thin objects, on top of the earlier fill beside them (2.5 mm exposed here)."""
    trims, st, stops, v = _sew(thin_arcs())
    ex = dst2.exposed_travel(stops, [r for r in st["runs"] if r[0] == 1])
    assert not ex or max(ex) <= 1.5, max(ex)
    assert trims <= 4, trims
