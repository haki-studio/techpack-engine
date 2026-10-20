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
from digitize.schema import ObjectPlan, Layer, DIR_SOURCES
from digitize.rulebook import Rulebook
from digitize.extract import register, evidence, zones as ZN
from digitize.extract.splitters import Ctx, sky, fall, stub, stratum, cloud
from digitize import direction as DR

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
        tp = TH.plan(dict(zip(ev.keys, w.tolist())), T["palette"], needles=config.needles(cfg), protected=T["protected"], names=T.get("names"),
                     importance=T.get("importance"))
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
            if k == "stratum": return stratum.split(ctx, z, zz, m)
            if k == "cloud": return cloud.split(ctx, z, zz, m)
            raise ValueError(f"zone {z['id']}: unknown splitter {k!r}")
        parts, log = ZN.claim_and_split(zs, ev, z_of, split)
        n_traced = len(parts); sk = cfg.get("specks", {}) or {}
        parts, merged = SQ.merge_specks(parts, sk.get("min_mm2", cfg["stub"]["min_part_mm2"]), protected=T["protected"],
                                        min_protected_mm2=cfg["stub"]["min_protected_mm2"])
        sep = self.rb.principles["neighbour_sep_deg"]
        moves = DR.separate(parts, sep=tuple(sep), kinds=set(self.cfg.get("separate_kinds", ["stratum_band", "cloud_shade", "cloud_wisp"])))
        layers = sorted({(p.kind if p.kind != "zone_stub" else p.zone, p.z) for p in parts}, key=lambda t: t[1])
        plan = ObjectPlan(name=self.name, parts=parts, layers=[Layer(n, z) for n, z in layers],
                          threads=tp["threads"], meta=dict(crop=list(self.crop), view=self.view, extract_log=log, thread_merges=tp["merges"],
                                                           tone_map=tp["map"], evidence_tone_mm2={k: round(float(v), 1) for k, v in zip(ev.keys, w)},
                                                           source_ppm_median=self.ref()["source_ppm_median"],
                                                           separation_moves=[list(m) for m in moves], traced_parts=n_traced,
                                                           specks_merged=[list(m) for m in merged]))
        plan.to_json(self.f("parts.json"), with_blocks=False)
        self.plan = plan
        print(f"extract: {len(parts)} parts from {len(zs['zones'])} zones ({n_traced} traced, {len(merged)} specks merged, "
              f"{len(moves)} turned for neighbour separation), {len(tp['threads'])} threads ({time.time() - t0:.1f} s)")
        for l in log: print("   ", l)
        return plan

    # ------------------------------------------------------------ plan
    def make_plan(self):
        t0 = time.time(); plan = ObjectPlan.from_json(self.f("parts.json")); P = self.rb.principles; issues = []
        for p in plan.parts:
            p.technique = self.rb.technique_for(p.kind); p.stitch = self.rb.stitch_spec(p.kind, p.technique)
            k = self.rb.rule(p.kind)
            if p.dir.mode in ("field", "contour") and p.technique not in k.get("follows", ("guided_fill", "contour_fill")):
                p.meta["dir_was"] = dict(angle=p.dir.angle, mode=p.dir.mode, source=p.dir.source)   # toggled off: the kind's alt_dir
                p.dir = self.rb.direction(p.kind, technique=p.technique); p.meta.pop("sep_deg", None); p.meta.pop("band_offset_deg", None)
        sq = self.cfg["sequence"]; n0 = len(plan.parts)
        SQ.underlap(plan.parts, sq["keep_mm"]); SQ.cut_under(plan.parts, sq["keep_mm"])
        plan.parts, dropped = SQ.absorb_fragments(plan.parts, sq["min_fragment_mm2"])
        refreshed = DR.refresh_field_basis(plan.parts)                  # bases on the geometry actually sewn (audited)
        sep = self.rb.principles["neighbour_sep_deg"]
        moves = DR.separate(plan.parts, sep=tuple(sep), kinds=set(self.cfg.get("separate_kinds", ["stratum_band", "cloud_shade", "cloud_wisp"])))
        for p in plan.parts: issues += techniques.get(p.technique).check(p, P)
        plan.stops = SQ.order(plan.parts)
        used = {p.thread for p in plan.parts}
        plan.threads = {k: v for k, v in plan.threads.items() if k in used}
        need = config.needles(self.cfg)
        if len(plan.threads) > need: raise SystemExit(f"plan uses {len(plan.threads)} threads > {need} needles")
        CP.plan_blocks(plan)
        plan.meta.update(dropped_fragments=dropped, issues=issues, parts_before_sequence=n0, field_basis_refreshed=refreshed,
                         separation_moves_plan=[list(m) for m in moves])
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
        from digitize import bench, audit
        from shapely.geometry import Point
        plan = ObjectPlan.from_json(self.f("plan.json")); z = np.load(self.f("stitch_parts.npz"))
        mem = [tuple(map(float, s)) for s in z["segs"]]; mem_parts = [s or None for s in z["parts"].tolist()]
        # judge the WRITTEN file (M1 review): the plan's part ids are carried onto the DST's own segments, in sew order
        dst = self.base + ".dst"
        segs, sp, match = CP.labelled_dst(dst, self.origin, mem, mem_parts)
        ppm = float(self.cfg_b["ppm"])
        vis, idx = qa.visible_segments(segs, self.crop, ppm=ppm, return_index=True)
        kinds = tuple(sorted({p.kind for p in plan.parts}))
        # angle_coherence (one deliberate angle per part) applies to FIXED-angle fill parts. Guided / contour parts vary
        # on purpose: they are judged per stitch against their own planned field (audit.sewn_angles field_adherence);
        # line parts (run / bean) have no fill direction.
        fixed = [p for p in plan.parts if p.dir.mode == "fixed" and techniques.get(p.technique).stype not in ("run", "bean")]
        regs = [dict(geom=p.geom, stype=p.technique, angle=p.dir.angle, grp=p.kind, part=p.id) for p in fixed]
        bad = qa.angle_coherence(regs, groups=kinds, segs=vis, seg_parts=[sp[i] for i in idx])
        kc = {}
        for b in bad: kc[b["kind"]] = kc.get(b["kind"], 0) + 1
        bk = {}
        for b in bad: bk[f"{b['kind']} / {b['grp']}"] = bk.get(f"{b['kind']} / {b['grp']}", 0) + 1
        coh = dict(source="plan part ids carried onto the written DST (compile.labelled_dst)", parts=len(fixed), ok=not bad,
                   fails=len(bad), kinds=kc, by_kind=bk, failing=[dict(b) for b in bad[:40]])
        project = self.cfg["project"]
        row, aux = bench.run_gates(self.cfg_b, project, dst, self.origin, coherence=coh)
        row["readback_match"] = match
        # split-satin cords read from the DST (satin_runs is blind to them): rows, pieces, stagger, column width
        cords = {}
        by_part = {}
        for sg, pid in zip(segs, sp):
            if pid is not None: by_part.setdefault(pid, []).append(sg)
        for p in plan.parts:
            if p.technique != "split_satin": continue
            r = qa.split_satin_rows(by_part.get(p.id, []), max_piece=7.1)
            cords[p.id] = r
        cflags = [dict(part=k, **f) for k, r in cords.items() for f in r["flags"]]
        row["cords"] = dict(n=len(cords), flags=len(cflags), failing=cflags[:20],
                            max_piece=max([r["max_piece"] for r in cords.values()] or [0.0]),
                            aligned_max=max([r["aligned"] for r in cords.values()] or [0.0]),
                            column_w=sorted(r["column_w"] for r in cords.values()))
        row["satin"]["cord_flags"] = len(cflags)
        # direction per part kind and per direction SOURCE: each 8 mm tile belongs to the top-most part under its centre
        from shapely.strtree import STRtree
        x0, y0 = self.crop[:2]; geoms = [p.geom for p in plan.parts]; tree = STRtree(geoms)
        def part_at(c):
            pt = Point(c[0] + x0, c[1] + y0); hit = [plan.parts[i] for i in tree.query(pt, predicate="intersects")]
            return max(hit, key=lambda p: p.z) if hit else None
        def kind_at(c):
            p = part_at(c); return p.kind if p is not None else "bare"
        per = {}
        dm = aux["dm"]
        for c in dm["ok_tiles"]: per.setdefault(kind_at(c), [0, 0, 0])[0] += 1
        for r in dm["fail_dev"]: per.setdefault(kind_at(r["at_mm"]), [0, 0, 0])[1] += 1
        for r in dm["fail_chaos"]: per.setdefault(kind_at(r["at_mm"]), [0, 0, 0])[2] += 1
        row["direction_by_kind"] = {k: dict(tiles=sum(v), ok=v[0], dev=v[1], chaos=v[2], pct_ok=round(100 * v[0] / max(1, sum(v)), 1),
                                            pct_chaos=round(100 * v[2] / max(1, sum(v)), 1)) for k, v in sorted(per.items())}
        row["direction_by_source"] = audit.direction_by_source(dm, part_at)
        aa = audit.angle_audit(plan, self.rb); sw = audit.sewn_angles(plan, segs, sp, self.crop, ppm=ppm)
        areas = np.array([p.area for p in plan.parts])
        ev_mm2 = plan.meta.get("evidence_tone_mm2", {})
        row["parts"] = dict(n=len(plan.parts), pct_under_20mm2=round(100 * float((areas < 20).mean()), 1) if len(areas) else 0.0,
                            by_kind={k: sum(1 for p in plan.parts if p.kind == k) for k in kinds},
                            undeclared_angles=sum(1 for p in plan.parts if p.dir.source not in DIR_SOURCES),
                            random_angles=aa["random_angles"], unexplained_angles=aa["unexplained"], sewn_off_angle=sw["sewn_off_angle"],
                            sewn_off=sw["off"], field_adherence=sw["field_adherence"],
                            dir_sources={s: sum(1 for p in plan.parts if p.dir.source == s) for s in {p.dir.source for p in plan.parts}})
        tot = sum(p.area for p in plan.parts) or 1.0
        by_zone = {}
        for p in plan.parts:
            if p.kind == "zone_stub": by_zone[p.zone] = by_zone.get(p.zone, 0.0) + p.area
        row["stub_area"] = dict(mm2=round(sum(by_zone.values()), 1), pct_of_parts=round(100 * sum(by_zone.values()) / tot, 1),
                                by_zone={k: round(v, 1) for k, v in sorted(by_zone.items())},
                                note="zone stubs left for M3 (buildings, trunks, crowns, florets)")
        # density flags by what meets there: the number of distinct ZONES whose parts touch the flagged box, and its kinds
        from shapely.geometry import box as _box
        jz, jk = {}, {}
        for fl in aux["dens"]["flags"]:
            (cx, cy), w2, h2 = fl["at_mm"], fl["w_mm"] / 2, fl["h_mm"] / 2
            hit = [plan.parts[i] for i in tree.query(_box(cx - w2, cy - h2, cx + w2, cy + h2), predicate="intersects")]
            nz = len({p.zone for p in hit}); jz[str(min(nz, 4)) + ("+" if nz >= 4 else "")] = jz.get(str(min(nz, 4)) + ("+" if nz >= 4 else ""), 0) + 1
            for k in {p.kind for p in hit}: jk[k] = jk.get(k, 0) + 1
        row["density"]["flags_by_zones_meeting"] = dict(sorted(jz.items())); row["density"]["flags_touching_kind"] = dict(sorted(jk.items()))
        row["separation"] = DR.separation_report(plan.parts, sep=float(self.rb.principles["neighbour_sep_deg"][0]))
        row["accents"] = {k: dict(evidence_mm2=ev_mm2.get(k, 0.0), parts=sum(1 for p in plan.parts if p.thread == k),
                                  sewn_in_crop=k in plan.threads and plan.threads[k]["hex"].lower() in [h.lower() for h in row["colours"]["hex"]])
                          for k in self.cfg["threads"]["protected"]}
        rbk = json.load(open(self.f("readback.json")))
        row["file"] = dict(stitches=rbk["readback"]["stitches"], trims=rbk["readback"]["trims"], stops=rbk["readback"]["stops"],
                           colours=len(plan.threads), max_stitch=rbk["readback"]["max_stitch"])
        row["date"] = datetime.date.today().isoformat(); row["label"] = self.cfg.get("label", self.name); row["bench"] = self.cfg_b["name"]
        row["dst"] = os.path.relpath(dst, bench.main_checkout()) if self.base.startswith(bench.main_checkout()) else dst
        row["dst_sha256"] = hashlib.sha256(open(dst, "rb").read()).hexdigest()[:16]; row["origin"] = list(self.origin)
        fa = sw["field_adherence"]
        if fa["parts"]:                                     # guided / contour parts: >= 85 % of their visible stitches within 15 deg
            coh["field_adherence"] = fa; coh["ok"] = coh["ok"] and fa["pct_within"] >= 85.0
        row["verdict"] = bench.verdict(row, self.cfg_b["targets"])
        json.dump(row, open(self.f("gates.json"), "w"), indent=1, default=float)
        self._row, self._aux = row, aux
        d = row["direction"]
        print(f"gates: direction {d['pct_ok']} % OK / {d['pct_chaos']} % chaotic; by kind " +
              ", ".join(f"{k} {v['pct_ok']}% of {v['tiles']}" for k, v in row["direction_by_kind"].items()) +
              "; by source " + ", ".join(f"{k} {v['pct_ok']}% of {v['tiles']}" for k, v in row["direction_by_source"].items()) +
              f"; random angles {aa['random_angles']}, sewn off angle {sw['sewn_off_angle']}; cords {len(cords)} ({len(cflags)} flags)"
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
