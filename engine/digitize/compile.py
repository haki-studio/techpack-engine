"""Compile (ENGINE_PLAN M1): ObjectPlan -> DST + PES through dst2's router / writer / read-back, unchanged.

  blocks = compile.plan_blocks(plan)                         # every part through its technique plugin
  res = compile.write(plan, base, origin)                    # base.dst / base.pes, readback dict, labelled segments

dst2.make_pattern gets builder=<the planned blocks>, keep_order=True (the plan's sew order is the order) and
threads=<the plan's thread table>: it emits exactly the planned blocks and only adds hidden travel / trims between them.
Each STITCH is labelled with its part id (stats["labels"]), so gates can attribute stitches to parts (angle_coherence
seg_parts) instead of guessing from geometry."""
import json, math
import dst2, readback
from digitize import techniques


def plan_blocks(plan):
    for p in plan.parts:
        plan.blocks[p.id] = techniques.get(p.technique).plan(p)
    return plan.blocks


def regions(plan):
    """dst2 stops: [dict(col, regions=[dict(col, geom, st, ang, grp, part, blocks)])] in the plan's sew order"""
    stops = []
    for s in plan.stops:
        regs = []
        for pid in s["parts"]:
            p = plan.part(pid); bl = plan.blocks.get(pid) or []
            if not bl: continue
            regs.append(dict(col=s["thread"], geom=p.geom, st=techniques.get(p.technique).stype, ang=p.dir.angle, grp=p.kind,
                             part=p.id, blocks=[list(b.pts) for b in bl]))
        if regs: stops.append(dict(col=s["thread"], regions=regs))
    return stops


def prebuilt(r, earlier):
    return r["blocks"]


def thread_table(plan):
    return {k: dict(hex=v["hex"], description=f"{v.get('name', k)} [proposed thread - confirm against the factory card]",
                    catalog=k, brand="factory card (to confirm)") for k, v in plan.threads.items()}


def pattern_segments(pat, labels, origin):
    """(segments in garment mm, part id per segment) from the pattern in memory, before the writer adds ties: a segment
    joins two consecutive STITCH points and takes the label of the stitch it ends on"""
    import pyembroidery as pe
    segs, lab = [], []; prev = None; k = 0; ox, oy = origin
    for x, y, c in pat.stitches:
        cmd = c & pe.COMMAND_MASK
        if cmd == pe.STITCH:
            q = (x / 10.0 + ox, y / 10.0 + oy)
            if prev is not None and prev != q: segs.append((prev[0], prev[1], q[0], q[1])); lab.append(labels[k])
            prev = q; k += 1
        else: prev = None
    return segs, lab


def write(plan, base, origin, **mp_kw):
    """mp_kw: extra dst2.make_pattern options (M5: exact_travel=dict(...) for patches); none = the M1 behaviour"""
    stops = regions(plan)
    vis = [r for s in stops for r in s["regions"]]
    pat, stats = dst2.make_pattern(vis, stops, origin, builder=prebuilt, keep_order=True, threads=thread_table(plan), **mp_kw)
    segs, lab = pattern_segments(pat, stats["labels"], origin)
    dst2.write(pat, base)
    rb = readback.dst(base + ".dst")
    return dict(base=base, origin=list(origin), build=dict(stitches=stats["stitches"], travel=stats["travel"], trims=stats["trims"],
                                                          jumps=stats["jumps"], why=stats.get("why", {})),
                readback=rb, segs=segs, seg_parts=lab, stops=len(stops),
                runs=stats["runs"], regions=stops, exact_trims=stats.get("exact_trims"))
