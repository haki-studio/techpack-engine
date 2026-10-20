"""M6 swatch: puff, chenille and chain on synthetic shapes, through the real plugins, compile and the written file.

  PYTHONPATH=engine python3 -m digitize.swatch_m6 engine/digitize/swatches/m6.yaml [--out DIR] [--no-api]

Lock-stitch file (Brother): a flat tatami base, three puff columns (straight on the base, curved, a closed ring) in
their own foam stop, and a chain line (toggles: chain off -> faux_chain). Chenille head: a moss + chain-outline part
and a true chain line, as a PLAN (json + preview); the machine file raises FactoryFormatNeeded (F1).
Every gate is judged on generated data: puff + faux chain on the WRITTEN DST (compile.labelled_dst), chenille / chain
on the plan paths. Outputs: <out>/m6_lock.dst/.pes, m6_chenille_plan.json, gates_m6.json, swatch_*.png. No API calls."""
import argparse, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
if ENGINE not in sys.path: sys.path.insert(0, ENGINE)

from shapely.geometry import LineString, Point, box
from digitize import config, compile as CP, sequence as SQ, techniques
from digitize.schema import ObjectPlan, Part, DirSpec
from digitize.rulebook import Rulebook
from digitize.techniques import specialty as SP
from digitize.techniques import column as C
from digitize.techniques.chenille import detail as chenille_detail

THREADS = {"navy": dict(hex="#22355C", name="navy"), "cream": dict(hex="#EFE6D2", name="cream"),
           "red": dict(hex="#B23F2E", name="red"), "moss": dict(hex="#5E8C4A", name="moss green"),
           "gold": dict(hex="#D9A441", name="gold")}
ORIGIN = (60.0, 40.0)


def column_geom(cl, w, closed=False):
    ls = LineString(list(cl) + ([cl[0]] if closed else []))
    return ls.buffer(w / 2, cap_style="flat" if not closed else "round")


def lock_parts(rb):
    ps = [Part(id="base", kind="pool", geom=box(5, 5, 55, 32), thread="navy", z=0, dir=rb.direction("pool"))]
    straight = [(12.0, 18.0), (48.0, 18.0)]
    arc = [(10 + 40 * i / 40, 48 - 9 * math.sin(math.pi * i / 40)) for i in range(41)]
    ring = [(85 + 9 * math.cos(2 * math.pi * i / 72), 20 + 9 * math.sin(2 * math.pi * i / 72)) for i in range(72)]
    for pid, cl, w, closed in (("puff.straight", straight, 5.0, False), ("puff.arc", arc, 6.0, False), ("puff.ring", ring, 4.0, True)):
        ps.append(Part(id=pid, kind="puff_column", geom=column_geom(cl, w, closed), thread="cream", z=2,
                       dir=DirSpec(90.0, source="rule", note="across the column (geometry)"),
                       meta=dict(cl=[list(c) for c in cl], w=w, closed=closed, foam=dict(thickness_mm=3.0, colour="cream (match thread)"))))
    wave = [(62 + 0.5 * i, 46 + 3 * math.sin(i / 6.0)) for i in range(101)]
    ps.append(Part(id="chain.line", kind="chain_line", geom=LineString(wave).buffer(0.3), thread="red", z=1.5,
                   dir=DirSpec(0.0, mode="contour", source="outline"), meta=dict(line=[list(c) for c in wave])))
    return ps


def head_parts():
    blob = Point(30, 66).buffer(11).union(Point(44, 62).buffer(8)).union(box(18, 66, 46, 76))
    blob = blob.difference(Point(31, 67).buffer(3.0))                     # a hole: the chain outlines it too
    wave = [(62 + 0.5 * i, 70 + 3 * math.sin(i / 6.0)) for i in range(101)]
    return [Part(id="chenille.blob", kind="chenille_fill", geom=blob, thread="moss", z=0, dir=DirSpec(0.0, source="rule")),
            Part(id="chain.true", kind="chain_line", geom=LineString(wave).buffer(0.3), thread="gold", z=1,
                 dir=DirSpec(0.0, mode="contour", source="outline"), meta=dict(line=[list(c) for c in wave]))]


def plan_parts(parts, rb, technique=None):
    for p in parts:
        p.technique = technique or rb.technique_for(p.kind); p.stitch = rb.stitch_spec(p.kind, p.technique)
    return parts


def build(cfg, out):
    os.makedirs(out, exist_ok=True)
    rb = Rulebook(toggles=cfg["techniques"], overrides=cfg.get("rule_overrides") or {})
    res = dict(toggles={k: cfg["techniques"].get(k) for k in ("puff", "chenille", "chain", "faux_chain")})
    # ---------------------------------------------------------------- lock-stitch file
    parts = plan_parts(lock_parts(rb), rb)
    res["chain_line_technique"] = next(p.technique for p in parts if p.kind == "chain_line")
    plan = ObjectPlan(name="m6_swatch", parts=parts, threads={k: dict(v) for k, v in THREADS.items() if k in {p.thread for p in parts}})
    if cfg.get("swatch", {}).get("isolate_foam", True): SP.isolate_foam(plan)
    if cfg.get("swatch", {}).get("knockout", True):                                # house rule 6 under the puff
        res["knockout"] = SP.knockout_under_puff(plan.parts, rb.principles.get("cut_keep_mm", 1.0))
    plan.stops = SQ.order(plan.parts)
    res["issues"] = [i for p in plan.parts for i in techniques.get(p.technique).check(p, rb.principles)]
    CP.plan_blocks(plan)
    gates = dict(plan=SP.plan_gates(plan))
    base = os.path.join(out, "m6_lock")
    lock = [p for p in plan.parts if SP.machine_of(p) == "lockstitch"]
    head = [p for p in plan.parts if SP.machine_of(p) != "lockstitch"]          # chain toggled on: chain.line goes to the head
    lp = ObjectPlan(name=plan.name, parts=lock, threads=plan.threads, blocks={p.id: plan.blocks[p.id] for p in lock},
                    stops=[dict(thread=s["thread"], parts=[q for q in s["parts"] if q in {p.id for p in lock}]) for s in plan.stops])
    lp.stops = [s for s in lp.stops if s["parts"]]
    w = CP.write(lp, base, ORIGIN)
    D, lab, rep = CP.labelled_dst(base + ".dst", ORIGIN, w["segs"], w["seg_parts"])
    res["file"] = dict(dst=base + ".dst", stitches=w["readback"]["stitches"], trims=w["readback"]["trims"], stops=w["readback"]["stops"],
                       max_stitch=w["readback"]["max_stitch"], labelled=rep)
    by = {}
    for s, l in zip(D, lab):
        if l is not None: by.setdefault(l, []).append(s)
    # the same gate on the DST: file needle points that are PLANNED stitches (0.1 mm grid) vs points dst2 added as travel
    fpts = {pid: [q for s in S for q in (s[:2], s[2:])] for pid, S in by.items()}
    grid = {pid: {(round(x, 1), round(y, 1)) for b in plan.blocks.get(pid, []) for x, y in b.pts} for pid in fpts}
    on = lambda pid, q: any((round(q[0] + dx, 1), round(q[1] + dy, 1)) in grid[pid] for dx in (-0.05, 0, 0.05) for dy in (-0.05, 0, 0.05))
    planned = {pid: [q for q in P if on(pid, q)] for pid, P in fpts.items()}
    travel = {pid: [q for q in P if not on(pid, q)] for pid, P in fpts.items()}
    gates["file"] = {"base_under_puff": SP.plan_gates(plan, pts_by_part=planned)["base_under_puff"]}
    res["travel_under_puff"] = SP.base_under_puff(plan, pts_by_part=travel)          # info: hidden travel, sewn before the foam
    for p in lock:
        if p.technique == "puff": gates[p.id] = SP.puff_gates(p, by.get(p.id, []))
        elif p.technique == "faux_chain": gates[p.id] = SP.faux_chain_gates(p, by.get(p.id, []))
    # ---------------------------------------------------------------- chenille head (plan only)
    hp = plan_parts(head_parts(), rb)
    hp[1].technique = "chain"; hp[1].stitch = rb.stitch_spec("chain_line", "chain")        # the true-chain preview, whatever the toggle
    items = []
    for p in hp + head:
        d = chenille_detail(p) if p.technique == "chenille" else techniques.get("chain").detail(p)
        gates[p.id] = SP.chenille_gates(p, d) if p.technique == "chenille" else SP.chain_gates(p, d)
        items.append((p, d))
    SP.write_chenille_plan(items, os.path.join(out, "m6_chenille_plan.json"))
    try:
        SP.export_chenille(items, os.path.join(out, "m6_chenille"))
        res["chenille_export"] = "written"
    except SP.FactoryFormatNeeded as e:
        res["chenille_export"] = f"FactoryFormatNeeded: {e}"
    res["gates"] = gates
    res["verdict"] = {f"{pid}.{k}": v["ok"] for pid, G in gates.items() for k, v in G.items()}
    # ---------------------------------------------------------------- previews
    col = lambda p: THREADS[p.thread.split("+")[0]]["hex"]
    lay = [("stitch", by.get(p.id, []), col(p)) for p in lock if p.technique not in ("puff",)]
    pre = []
    for p in lock:
        if p.technique == "puff": pre.append(("foam", p.geom, "#CFC4A8"))
    res["png"] = dict(
        puff=SP.swatch_png(lay[:1] + pre + [("stitch", by.get(p.id, []), col(p)) for p in lock if p.technique == "puff"],
                           (0, 0, 100, 52), os.path.join(out, "swatch_puff.png"), ppm=16, title="puff (written DST): base tatami, foam, 3 puff columns"),
        knockout=SP.swatch_png(pre + lay[:1], (0, 0, 60, 36), os.path.join(out, "swatch_puff_knockout.png"), ppm=16,
                               title="base only, over the puff footprint (light): knocked out, 1 mm kept under the puff edge"),
        puff_zoom=SP.swatch_png(lay[:1] + pre + [("stitch", by.get(p.id, []), col(p)) for p in lock if p.technique == "puff"],
                                (8, 12, 22, 24), os.path.join(out, "swatch_puff_end.png"), ppm=60, title="puff end: perforation + cap"),
        chain=SP.swatch_png([("stitch", by.get(p.id, []), col(p)) for p in lock if p.kind == "chain_line"]
                            + [("chain", d["chain"], col(p)) for p, d in items if p.technique == "chain"],
                            (58, 40, 116, 76), os.path.join(out, "swatch_chain.png"), ppm=20,
                            title=f"top: {res['chain_line_technique']} (written DST)   bottom: true chain plan (chenille head)"),
        chain_zoom=SP.swatch_png([("stitch", by.get(p.id, []), col(p)) for p in lock if p.kind == "chain_line"],
                                 (62, 42, 76, 50), os.path.join(out, "swatch_chain_zoom.png"), ppm=70, title="faux chain links"),
        chenille=SP.swatch_png([("moss", d["moss"], col(p), d["spec"]["loop_height_mm"]) for p, d in items if p.technique == "chenille"]
                               + [("chain", d["chain"], "#3F6B32") for p, d in items if p.technique == "chenille"],
                               (14, 50, 58, 80), os.path.join(out, "swatch_chenille.png"), ppm=20, title="chenille plan: moss spiral + chain outline"))
    json.dump(res, open(os.path.join(out, "gates_m6.json"), "w"), indent=1, default=str)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("yaml"); ap.add_argument("--out", default=None)
    ap.add_argument("--no-api", action="store_true", help="accepted: nothing here calls the Anthropic API")
    a = ap.parse_args(argv); cfg = config.load(a.yaml)
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.yaml)), "out", "m6")
    r = build(cfg, out)
    bad = [k for k, v in r["verdict"].items() if not v]
    print(f"m6 swatch: chain_line -> {r['chain_line_technique']}; file {r['file']['stitches']} stitches, {r['file']['stops']} stops; "
          f"gates {len(r['verdict']) - len(bad)}/{len(r['verdict'])}" + (f"; FAIL {bad}" if bad else "") + f"\n  chenille export: {r['chenille_export'][:90]}...")
    return r


if __name__ == "__main__":
    main()
