"""Digitize a crop / piece end to end (ENGINE_PLAN M1). No Anthropic API calls anywhere in this pipeline; --no-api is
accepted (and is the default) so the command reads the same once the review step (M4) can ask Claude questions.

  python3 -m digitize.run projects/castle-falls-jacket/bench/run_bk_crop.yaml --stages all --no-api

Stages (comma list, or "all"):
  extract   12 ppm reference -> evidence (tone trace + grain) -> threads v0 -> zones -> splitters -> parts.json
  review    part_map.png + questions.json
  plan      rulebook (technique, numbers, direction) -> sequence v0 (underlap, cut-under, fragments, z-DAG stops)
            -> technique plugins -> plan.json
  compile   dst2 (builder=planned blocks, keep_order, threads) -> <name>.dst/.pes, readback.json
  gates     every bench gate + angle_coherence on the plan's part ids + per-kind direction -> gates.json
  panel     reference | part map | live view | direction heat-map | density -> panel.png
  bench     append the gate row to <project>/bench/SCOREBOARD.json + BENCH.md (with a copy of the panel)
Outputs: <project>/<out_dir>/ (git-ignored)."""
import argparse, datetime, hashlib, json, os, shutil, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
if ENGINE not in sys.path: sys.path.insert(0, ENGINE)

import numpy as np
from digitize import config, threads as TH, sequence as SQ, compile as CP, review as RV, techniques
from digitize.schema import ObjectPlan, Layer
from digitize.rulebook import Rulebook
from digitize.extract import register, evidence, zones as ZN
from digitize.extract.splitters import Ctx, sky, fall, stub

STAGES = ["extract", "review", "plan", "compile", "gates", "panel", "bench"]
SPLIT_KIND = {"sky": "sky_band", "fall": "fall_cord", "pool": "pool"}


class Run:
    def __init__(self, yaml_path, overrides=None):
        self.cfg = config.load(yaml_path, overrides)
        self.cfg_b = json.load(open(config.path(self.cfg, self.cfg["bench"])))
        self.out = config.path(self.cfg, self.cfg["out_dir"]); os.makedirs(self.out, exist_ok=True)
        self.crop = tuple(self.cfg_b["crop"]); self.view = self.cfg_b["view"]
        self.rb = Rulebook(self.cfg.get("rules"), toggles=self.cfg["techniques"], overrides=self.cfg.get("rule_overrides"))
        self.name = self.cfg["name"]; self.base = os.path.join(self.out, self.name)
        self.origin = ((self.crop[0] + self.crop[2]) / 2.0, (self.crop[1] + self.crop[3]) / 2.0)
        self._ref = None

    def f(self, name): return os.path.join(self.out, name)

    def ref(self):
        if self._ref is None:
            reg = register.load(config.path(self.cfg, self.cfg_b["registration"]))
            self._ref = register.reference(reg, self.view, self.crop, ppm=float(self.cfg_b["ppm"]))
        return self._ref

    # ------------------------------------------------------------ extract
    def extract(self):
        t0 = time.time(); cfg = self.cfg; T = cfg["threads"]
        ev = evidence.build(self.ref(), T["palette"], **cfg["evidence"])
        ev.tone_png(self.f("evidence_tones.png"))
        w = np.bincount(ev.tone.ravel(), minlength=len(ev.keys)) / ev.ppm ** 2
        tp = TH.plan(dict(zip(ev.keys, w.tolist())), T["palette"], needles=config.needles(cfg), protected=T["protected"], names=T.get("names"))
        ctx = Ctx(ev, self.rb, cfg, tp["map"], T["protected"])
        zs = ZN.load(config.path(cfg, cfg["zones"]))
        def z_of(z):
            if "z" in z: return float(z["z"])
            return self.rb.z(SPLIT_KIND[z["splitter"]])
        def split(z, zz, m):
            k = z["splitter"]
            if k == "sky": return sky.split(ctx, z, zz, m)
            if k == "fall": return fall.split(ctx, z, zz, m)
            if k == "pool": return stub.split_pool(ctx, z, zz, m)
            if k == "stub": return stub.split(ctx, z, zz, m)
            raise ValueError(f"zone {z['id']}: unknown splitter {k!r}")
        parts, log = ZN.claim_and_split(zs, ev, z_of, split)
        layers = sorted({(p.kind if p.kind != "zone_stub" else p.zone, p.z) for p in parts}, key=lambda t: t[1])
        plan = ObjectPlan(name=self.name, parts=parts, layers=[Layer(n, z) for n, z in layers],
                          threads=tp["threads"], meta=dict(crop=list(self.crop), view=self.view, extract_log=log, thread_merges=tp["merges"],
                                                           tone_map=tp["map"], evidence_tone_mm2={k: round(float(v), 1) for k, v in zip(ev.keys, w)},
                                                           source_ppm_median=self.ref()["source_ppm_median"]))
        plan.to_json(self.f("parts.json"), with_blocks=False)
        self.plan = plan
        print(f"extract: {len(parts)} parts from {len(zs['zones'])} zones, {len(tp['threads'])} threads ({time.time() - t0:.1f} s)")
        for l in log: print("   ", l)
        return plan

    # ------------------------------------------------------------ plan
    def make_plan(self):
        t0 = time.time(); plan = ObjectPlan.from_json(self.f("parts.json")); P = self.rb.principles; issues = []
        for p in plan.parts:
            p.technique = self.rb.technique_for(p.kind); p.stitch = self.rb.stitch_spec(p.kind, p.technique)
        sq = self.cfg["sequence"]; n0 = len(plan.parts)
        SQ.underlap(plan.parts, sq["keep_mm"]); SQ.cut_under(plan.parts, sq["keep_mm"])
        plan.parts, dropped = SQ.absorb_fragments(plan.parts, sq["min_fragment_mm2"])
        for p in plan.parts: issues += techniques.get(p.technique).check(p, P)
        plan.stops = SQ.order(plan.parts)
        used = {p.thread for p in plan.parts}
        plan.threads = {k: v for k, v in plan.threads.items() if k in used}
        need = config.needles(self.cfg)
        if len(plan.threads) > need: raise SystemExit(f"plan uses {len(plan.threads)} threads > {need} needles")
        CP.plan_blocks(plan)
        plan.meta.update(dropped_fragments=dropped, issues=issues, parts_before_sequence=n0)
        plan.to_json(self.f("plan.json")); self.plan = plan
        print(f"plan: {len(plan.parts)} parts ({len(dropped)} fragments dropped), {len(plan.stops)} stops, {len(plan.threads)} threads, "
              f"{len(issues)} check issues ({time.time() - t0:.1f} s)")
        return plan

    # ------------------------------------------------------------ review
    def review(self):
        plan = ObjectPlan.from_json(self.f("plan.json") if os.path.exists(self.f("plan.json")) else self.f("parts.json"))
        RV.part_map(plan, self.crop, self.f("part_map.png"))
        qs = RV.questions(plan, plan.meta.get("issues", []))
        json.dump(qs, open(self.f("questions.json"), "w"), indent=1)
        parts_json = dict(name=plan.name, n=len(plan.parts), parts=[dict(id=p.id, kind=p.kind, zone=p.zone, thread=p.thread, z=p.z,
                          technique=p.technique, angle=p.dir.angle, dir_source=p.dir.source, area_mm2=round(p.area, 1)) for p in plan.parts])
        json.dump(parts_json, open(self.f("parts_summary.json"), "w"), indent=1)
        print(f"review: part_map.png, {len(qs)} questions")

    # ------------------------------------------------------------ compile
    def compile(self):
        t0 = time.time(); plan = ObjectPlan.from_json(self.f("plan.json"))
        res = CP.write(plan, self.base, self.origin)
        if len(res["seg_parts"]) != len(res["segs"]): raise RuntimeError("compile: labels out of step with stitches")
        json.dump(dict(base=os.path.basename(self.base), origin=res["origin"], build=res["build"], readback=res["readback"], stops=res["stops"]),
                  open(self.f("readback.json"), "w"), indent=1)
        np.savez_compressed(self.f("stitch_parts.npz"), segs=np.asarray(res["segs"], np.float32), parts=np.asarray([p or "" for p in res["seg_parts"]]))
        rb = res["readback"]
        print(f"compile: {rb['stitches']} stitches, {rb['trims']} trims, {rb['stops']} stops, max stitch {rb['max_stitch']} mm ({time.time() - t0:.1f} s)")
        return res

    # ------------------------------------------------------------ gates
    def gates(self):
        import qa
        from digitize import bench
        from shapely.geometry import Point
        plan = ObjectPlan.from_json(self.f("plan.json")); z = np.load(self.f("stitch_parts.npz"))
        segs = [tuple(map(float, s)) for s in z["segs"]]; sp = [s or None for s in z["parts"].tolist()]
        ppm = float(self.cfg_b["ppm"])
        vis, idx = qa.visible_segments(segs, self.crop, ppm=ppm, return_index=True)
        kinds = tuple(sorted({p.kind for p in plan.parts}))
        regs = [dict(geom=p.geom, stype=p.technique, angle=p.dir.angle, grp=p.kind, part=p.id) for p in plan.parts]
        bad = qa.angle_coherence(regs, groups=kinds, segs=vis, seg_parts=[sp[i] for i in idx])
        kc = {}
        for b in bad: kc[b["kind"]] = kc.get(b["kind"], 0) + 1
        bk = {}
        for b in bad: bk[f"{b['kind']} / {b['grp']}"] = bk.get(f"{b['kind']} / {b['grp']}", 0) + 1
        coh = dict(source="plan part ids (compile labels)", parts=len(plan.parts), ok=not bad, fails=len(bad), kinds=kc, by_kind=bk,
                   failing=[dict(b) for b in bad[:40]])
        project = self.cfg["project"]
        row, aux = bench.run_gates(self.cfg_b, project, self.base + ".dst", self.origin, coherence=coh)
        # direction per part kind: each 8 mm tile belongs to the top-most part under its centre
        from shapely.strtree import STRtree
        x0, y0 = self.crop[:2]; geoms = [p.geom for p in plan.parts]; tree = STRtree(geoms)
        def kind_at(c):
            pt = Point(c[0] + x0, c[1] + y0); hit = [plan.parts[i] for i in tree.query(pt, predicate="intersects")]
            return max(hit, key=lambda p: p.z).kind if hit else "bare"
        per = {}
        dm = aux["dm"]
        for c in dm["ok_tiles"]: per.setdefault(kind_at(c), [0, 0, 0])[0] += 1
        for r in dm["fail_dev"]: per.setdefault(kind_at(r["at_mm"]), [0, 0, 0])[1] += 1
        for r in dm["fail_chaos"]: per.setdefault(kind_at(r["at_mm"]), [0, 0, 0])[2] += 1
        row["direction_by_kind"] = {k: dict(tiles=sum(v), ok=v[0], dev=v[1], chaos=v[2], pct_ok=round(100 * v[0] / max(1, sum(v)), 1)) for k, v in sorted(per.items())}
        areas = np.array([p.area for p in plan.parts])
        ev_mm2 = plan.meta.get("evidence_tone_mm2", {})
        prot = [k for k, v in plan.threads.items() if v.get("protected")]
        row["parts"] = dict(n=len(plan.parts), pct_under_20mm2=round(100 * float((areas < 20).mean()), 1) if len(areas) else 0.0,
                            by_kind={k: sum(1 for p in plan.parts if p.kind == k) for k in kinds},
                            undeclared_angles=sum(1 for p in plan.parts if p.dir.source not in ("rule", "field-mean", "splitter", "answer")),
                            random_angles=0, dir_sources={s: sum(1 for p in plan.parts if p.dir.source == s) for s in {p.dir.source for p in plan.parts}})
        row["accents"] = {k: dict(evidence_mm2=ev_mm2.get(k, 0.0), parts=sum(1 for p in plan.parts if p.thread == k),
                                  sewn_in_crop=k in plan.threads and plan.threads[k]["hex"].lower() in [h.lower() for h in row["colours"]["hex"]])
                          for k in self.cfg["threads"]["protected"]}
        rbk = json.load(open(self.f("readback.json")))
        row["file"] = dict(stitches=rbk["readback"]["stitches"], trims=rbk["readback"]["trims"], stops=rbk["readback"]["stops"],
                           colours=len(plan.threads), max_stitch=rbk["readback"]["max_stitch"])
        row["date"] = datetime.date.today().isoformat(); row["label"] = self.cfg.get("label", self.name); row["bench"] = self.cfg_b["name"]
        row["dst"] = os.path.relpath(self.base + ".dst", bench.main_checkout()) if self.base.startswith(bench.main_checkout()) else self.base + ".dst"
        row["dst_sha256"] = hashlib.sha256(open(self.base + ".dst", "rb").read()).hexdigest()[:16]; row["origin"] = list(self.origin)
        row["verdict"] = bench.verdict(row, self.cfg_b["targets"])
        json.dump(row, open(self.f("gates.json"), "w"), indent=1, default=float)
        self._row, self._aux = row, aux
        d = row["direction"]
        print(f"gates: direction {d['pct_ok']} % OK / {d['pct_chaos']} % chaotic; by kind " +
              ", ".join(f"{k} {v['pct_ok']}% of {v['tiles']}" for k, v in row["direction_by_kind"].items()) +
              f"; coherence {'pass' if coh['ok'] else coh['kinds']}; {sum(row['verdict'].values())}/{len(row['verdict'])} gates")
        return row, aux

    def _gated(self):
        if not hasattr(self, "_row"): self.gates()
        return self._row, self._aux

    # ------------------------------------------------------------ panel / bench
    def panel(self):
        from PIL import Image
        from digitize import bench
        row, aux = self._gated()
        P = float(self.cfg_b["panel_ppm"]); W = int(round((self.crop[2] - self.crop[0]) * P)); H = int(round((self.crop[3] - self.crop[1]) * P))
        pm = Image.open(self.f("part_map.png")).convert("RGB").resize((W, H), Image.LANCZOS)
        bench.panel(row, aux, self.cfg_b, self.base + ".dst", self.origin, self.f("panel.png"), extra=[(pm, "part_map")])
        print(f"panel: {self.f('panel.png')}")

    def bench(self):
        from PIL import Image
        from digitize import bench
        row, aux = self._gated()
        P = float(self.cfg_b["panel_ppm"]); W = int(round((self.crop[2] - self.crop[0]) * P)); H = int(round((self.crop[3] - self.crop[1]) * P))
        pm = Image.open(self.f("part_map.png")).convert("RGB").resize((W, H), Image.LANCZOS)
        bench.append(row, self.cfg["project"], aux, self.cfg_b, self.base + ".dst", self.origin, extra=[(pm, "part_map")])
        print(f"bench: appended '{row['label']}' to {self.cfg['project']}/bench/SCOREBOARD.json + BENCH.md (panel {row['panel']})")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_yaml")
    ap.add_argument("--stages", default="all")
    ap.add_argument("--no-api", action="store_true", help="no Anthropic API calls (the only mode in M1; accepted for the M4 question step)")
    a = ap.parse_args(argv)
    if config.load(a.run_yaml).get("source") == "svg":          # M5: founder vector art as the part source
        from digitize import svgrun; return svgrun.main(argv)
    print("[info] digitize.run makes no Anthropic API calls (M1); --no-api accepted.")
    st = STAGES if a.stages == "all" else [s.strip() for s in a.stages.split(",")]
    for s in st:
        if s not in STAGES: raise SystemExit(f"unknown stage {s!r} (have {STAGES})")
    r = Run(a.run_yaml); t0 = time.time()
    order = ["extract", "plan", "review", "compile", "gates", "panel", "bench"]
    for s in order:
        if s not in st: continue
        {"extract": r.extract, "plan": r.make_plan, "review": r.review, "compile": r.compile, "gates": r.gates,
         "panel": r.panel, "bench": r.bench}[s]()
    print(f"done in {time.time() - t0:.0f} s -> {r.out}")


if __name__ == "__main__":
    main()
