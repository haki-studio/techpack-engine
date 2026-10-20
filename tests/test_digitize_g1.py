"""ENGINE_PLAN G1: the labels contract, the generic primitive recognisers, the labels -> Parts compiler, and the
dst2 / compile block-join guard (LESSONS B39). Every guard here was proven red first (RECAP-2026-10-20-engine-g1.md)."""
import json, math, os
import numpy as np
import pytest
from shapely.geometry import LineString, box, Point

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ------------------------------------------------------------------ B39: a part's blocks never joined over its own rows
def _rows(x0, x1, y0, y1, sp=0.4, start_left=True):
    """horizontal tatami-like rows (boustrophedon), one stitch per row end"""
    pts = []; y = y0; k = 0 if start_left else 1
    while y <= y1 + 1e-9:
        pts += [(x0, y), (x1, y)] if k % 2 == 0 else [(x1, y), (x0, y)]
        y += sp; k += 1
    return pts


def _travel_over(pat_stats, pat, origin, footprint, planned, ex=0.4):
    """sewn segments that are NOT one of the planned block segments (travel / hops between blocks) lying on
    `footprint` for more than ex mm. A hop is labelled with the stitch it ends on, so labels cannot tell it apart: the
    planned segments (consecutive points inside one block, 0.1 mm grid) can."""
    import pyembroidery as pe
    ox, oy = origin; prev = None; bad = []
    key = lambda a, b: (round(a[0], 1), round(a[1], 1), round(b[0], 1), round(b[1], 1))
    plan = {key(a, b) for bl in planned for a, b in zip(bl, bl[1:])} | {key(b, a) for bl in planned for a, b in zip(bl, bl[1:])}
    for x, y, c in pat.stitches:
        cmd = c & pe.COMMAND_MASK
        if cmd == pe.STITCH:
            q = (x / 10.0 + ox, y / 10.0 + oy)
            if prev is not None and math.dist(prev, q) > 0.3 and key(prev, q) not in plan:
                L = LineString([prev, q]).intersection(footprint).length
                if L > ex: bad.append((prev, q, round(L, 2)))
            prev = q
        else: prev = None
    return bad


def _two_block_region(b2_start_left=True, b1_rows=(0.2, 3.8), b2=(6.5, 11.5)):
    import dst2
    g = box(0, 0, 12, 4)
    b1 = _rows(0.5, 5.5, *b1_rows)                         # 10 rows -> ends on the LEFT side at the top (0.5, 3.8)
    b2p = _rows(b2[0], b2[1], 0.2, 3.8, start_left=b2_start_left)
    r = dict(col="#336699", geom=g, st="tatami", ang=0.0, grp="t", part="P1", blocks=[b1, b2p], block_roles=["top", "top"])
    return g, b1, b2p, r


def test_block_join_never_sews_over_the_parts_own_rows():
    """B39: two TOP blocks of one part; the hop from the first block's end to the second's start runs diagonally across
    the first block's sewn rows (inside the part, so the old router sewed it as a 7 mm travel stitch on top: a zig-zag
    that reads back as satin). It must be a trim (or a travel that stays off the visible rows)."""
    import dst2
    from digitize import compile as CP
    g, b1, b2p, r = _two_block_region()
    stops = [dict(col=r["col"], regions=[r])]
    pat, st = dst2.make_pattern([r], stops, (6.0, 2.0), builder=CP.prebuilt, keep_order=True)
    foot = LineString(b1).buffer(0.2)
    assert _travel_over(st, pat, (6.0, 2.0), foot, r["blocks"]) == []


def test_block_join_guard_keeps_a_hop_over_unsewn_rows():
    """the guard only refuses hops over rows ALREADY sewn: a hop that runs over the second block's (not yet sewn) area
    stays a hidden travel (no extra trim)"""
    import dst2
    from digitize import compile as CP
    g = box(0, 0, 12, 4)
    b1 = _rows(0.5, 5.5, 0.2, 3.6)                          # 9 rows -> ends on the RIGHT at (5.5, 3.4)
    b2p = _rows(6.5, 11.5, 0.2, 3.8, start_left=False)     # starts at (11.5, 0.2): the hop crosses block 2's own area
    r = dict(col="#336699", geom=g, st="tatami", ang=0.0, grp="t", part="P1", blocks=[b1, b2p], block_roles=["top", "top"])
    pat, st = dst2.make_pattern([r], [dict(col=r["col"], regions=[r])], (6.0, 2.0), builder=CP.prebuilt, keep_order=True)
    assert st["trims"] == 0


def test_block_join_guard_is_off_without_block_roles():
    """default preservation: regions without block_roles (every caller before G1, dst2's own builder) route as before"""
    import dst2
    from digitize import compile as CP
    g, b1, b2p, r = _two_block_region()
    r.pop("block_roles")
    pat, st = dst2.make_pattern([r], [dict(col=r["col"], regions=[r])], (6.0, 2.0), builder=CP.prebuilt, keep_order=True)
    assert _travel_over(st, pat, (6.0, 2.0), LineString(b1).buffer(0.2), r["blocks"]) != []      # the old behaviour, unchanged


def test_compile_regions_carry_block_roles():
    from digitize import compile as CP
    from digitize.schema import ObjectPlan, Part, DirSpec, Block
    p = Part(id="a", kind="plane", geom=box(0, 0, 5, 5), thread="t", z=1, dir=DirSpec(0.0), technique="tatami")
    plan = ObjectPlan(name="x", parts=[p], stops=[dict(thread="t", parts=["a"])],
                      blocks={"a": [Block("a", "underlay", [(0, 0), (1, 1)]), Block("a", "top", [(0, 0), (5, 0)])]})
    regs = CP.regions(plan)
    assert regs[0]["regions"][0]["block_roles"] == ["underlay", "top"]
