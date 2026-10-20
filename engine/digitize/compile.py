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


class ReadbackMismatch(RuntimeError):
    pass


def labelled_dst(dst, origin, segs, labels, tol=0.16, skip_mm=0.2):
    """The WRITTEN file's stitch segments (qa.dst_segments) with the plan's part id on each, matched in sew order
    against the in-memory segments `segs` / `labels` (pattern_segments). Gates must judge the file the factory gets,
    not the plan (M1 review): every planned segment longer than skip_mm must appear in the DST, in order, within tol mm
    (the 0.1 mm grid); segments the writer adds (tie-on / tie-off) are labelled None and counted. A planned segment
    missing from the file raises ReadbackMismatch. Returns (dst_segs, dst_labels, report)."""
    import qa
    D = qa.dst_segments(dst, origin); out = [None] * len(D); j = 0; n = len(segs); extra = 0; skipped = 0
    def same(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2]), abs(a[3] - b[3])) <= tol
    for i, d in enumerate(D):
        while j < n and not same(d, segs[j]) and math.dist(segs[j][:2], segs[j][2:]) < skip_mm:
            j += 1; skipped += 1                           # a sub-grid planned stitch rounded onto its neighbour
        if j < n and same(d, segs[j]):
            out[i] = labels[j]; j += 1
        else:
            extra += 1
    while j < n and math.dist(segs[j][:2], segs[j][2:]) < skip_mm: j += 1; skipped += 1
    if j < n:
        raise ReadbackMismatch(f"{dst}: planned segment {j} of {n} {tuple(round(v, 2) for v in segs[j])} (part {labels[j]}) is not in "
                               f"the written file in sew order: the gates would judge a plan the file does not contain")
    lab = [l for l in out if l is not None]
    return D, out, dict(file_segs=len(D), planned_segs=n, matched=n - skipped, writer_added=extra, skipped_subgrid=skipped,
                        labelled=len(lab))


def write(plan, base, origin, **mp_kw):
    """mp_kw: extra dst2.make_pattern options (M5: exact_travel=dict(...) for patches); none = the M1 behaviour"""
    # --- M6 --- a chenille-head part (chenille moss, true chain) never goes into a lock-stitch file
    from digitize.techniques.specialty import machine_of, OtherMachine
    other = [p.id for p in plan.parts if p.technique and machine_of(p) != "lockstitch"]
    if other: raise OtherMachine(f"{base}: parts {other[:6]} are planned for the chenille head, not this lock-stitch file: "
                                 f"split them out (specialty.export_chenille) or switch the run to faux_chain")
    from digitize.techniques.specialty import guard_puff
    guard_puff(plan)                                       # puff: own "+foam" stop, nothing flat inside the foam, never fill
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
