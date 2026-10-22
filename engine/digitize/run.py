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
from digitize.extract.splitters import trunk, crown, blossom, hints   # --- M3b ---
M3B_SPLITTERS = {"trunk": trunk.split, "crown": crown.split, "blossom": blossom.split}
NO_FILL_DIRECTION = ("dot",)                                          # beads: judged by size (rule 9), not by angle


def zero_bare(w, keys, bare):
    """--- mockup-governs --- run.yaml threads.bare: palette tones that are the BARE shell (fabric left unsewn between motifs). They
    stay in the evidence (so a duck pixel is not classified as the nearest thread) but get zero weight, so the thread
    planner maps them to no thread (splitters see thread_lab -1 and never sew them). Default (none) = unchanged."""
    w = np.array(w, float)
    for k in bare or []:
        if k not in keys: raise SystemExit(f"threads.bare names {k!r}, which is not in the palette")
        w[list(keys).index(k)] = 0.0
    return w


def florets_by_part_map(row, segs, labels, plan, crop):
    """M3b: qa.satin_shape reads satin runs from the DST alone and cannot tell a floret from a fan in a window (its own
    docstring: "needs the part map"). A flagged run whose stitches are mostly labelled with a RADIAL part (a face-on
    floret, rule 4) is re-filed as a floret fan; a flagged run inside a BEAD (dot technique: its tiny cross underlay and
    end rows read as a < 1 mm satin) is re-filed as a bead (rule 9 studs). The counts moved are recorded; everything
    else stays flagged."""
    import qa
    radial = {p.id for p in plan.parts if p.dir.mode == "radial"}
    beads = {p.id for p in plan.parts if p.technique in NO_FILL_DIRECTION}
    if not radial and not beads: return
    x0, y0, x1, y1 = crop; inside = lambda q: x0 <= q[0] < x1 and y0 <= q[1] < y1
    moved = {"blob": 0, "too-narrow": 0, "too-wide": 0}; bead = {"blob": 0, "too-narrow": 0, "too-wide": 0}
    for f in qa.satin_shape(segs)["flags"]:
        if not inside(f["at_mm"]): continue
        lab = [labels[i] for i in range(f["i0"], f["i1"] + 1)]
        if sum(1 for l in lab if l in radial) > 0.5 * len(lab): moved[f["kind"]] += 1
        elif sum(1 for l in lab if l in beads) > 0.5 * len(lab) and f["width_mm"] <= 1.5: bead[f["kind"]] += 1
    s = row["satin"]
    for k, key in (("blob", "blob"), ("too-narrow", "too_narrow"), ("too-wide", "too_wide")): s[key] -= moved[k] + bead[k]
    s["floret_runs_by_part_map"] = moved; s["bead_runs_by_part_map"] = bead


class Run:
    def __init__(self, yaml_path, overrides=None, answers=None):
        self.cfg = config.load(yaml_path, overrides)
        self.cfg_b = json.load(open(config.path(self.cfg, self.cfg["bench"])))
        self.out = config.path(self.cfg, self.cfg["out_dir"]); os.makedirs(self.out, exist_ok=True)
        self._answers(answers or self.cfg.get("answers"))                                        # M4g
        self.crop = tuple(self.cfg_b["crop"]); self.view = self.cfg_b["view"]
        self.rb = Rulebook(self.cfg.get("rules"), toggles=self.cfg["techniques"], overrides=self.cfg.get("rule_overrides"))
        self.name = self.cfg["name"]; self.base = os.path.join(self.out, self.name)
        self.origin = ((self.crop[0] + self.crop[2]) / 2.0, (self.crop[1] + self.crop[3]) / 2.0)
        self._ref = None

    def f(self, name): return os.path.join(self.out, name)

    # ------------------------------------------------------------ M4g: answers.json from the review step
    def _answers(self, path):
        """answers to the PREVIOUS run's questions (run.yaml `answers:` / --answers; questions from run.yaml
        `questions:`, else <out>/questions.json) -> config overrides for this run + answers_report.json"""
        if not path: return
        path = config.path(self.cfg, path); qp = config.path(self.cfg, self.cfg["questions"]) if self.cfg.get("questions") else self.f("questions.json")
        if not os.path.exists(qp): raise SystemExit(f"answers {path}: no questions file {qp} to answer against (run the review stage first)")
        self.cfg, rep = RV.apply_answers(self.cfg, RV.load_answers(path), json.load(open(qp)))
        rep["answers"] = os.path.relpath(path, self.cfg["project"]); self.cfg["_answers_report"] = rep
        json.dump(rep, open(self.f("answers_report.json"), "w"), indent=1)
        print(f"answers: {len(rep['answered'])} answered, {len(rep['defaulted'])} left at their default "
              f"({', '.join(q for q, _ in rep['defaulted'][:6])}{' ...' if len(rep['defaulted']) > 6 else ''}), "
              f"{len(rep['unknown'])} unknown {rep['unknown'][:6]}, {len(rep['pending'])} pending a person")

    # ------------------------------------------------------------ G1: labels or zones
    def _claims(self):
        """the claims the thread planner weighs motifs by: the zones file, or the labelled parts as zone-like dicts"""
        if not self.cfg.get("labels"): return ZN.load(config.path(self.cfg, self.cfg["zones"]))
        from digitize.labels import schema as LS, compile as LC
        self.labels = LS.load(config.path(self.cfg, self.cfg["labels"]), palette=self.cfg["threads"]["palette"])
        R = LC.resolve(self.labels, (self.cfg.get("review") or {}).get("labels"))
        return dict(zones=[dict(id=r["zone"], tones=r["tones"], geoms=r["geoms"], **({"rest": True} if r["rest"] else {})) for r in R])

    def ref(self):
        if self._ref is None:
            reg = register.load(config.path(self.cfg, self.cfg.get("registration") or self.cfg_b["registration"]))   # --- mockup-governs --- run.yaml
            # `registration:` = the EXTRACTION source (mockup + informing close-ups); bench.json's stays the gate reference
            self._ref = register.reference(reg, self.view, self.crop, ppm=float(self.cfg_b["ppm"]))
        return self._ref

    # ------------------------------------------------------------ extract
    def extract(self):
        t0 = time.time(); cfg = self.cfg; T = cfg["threads"]
        ev = evidence.build(self.ref(), T["palette"], **cfg["evidence"])
        ev.tone_png(self.f("evidence_tones.png"))
        w = np.bincount(ev.tone.ravel(), minlength=len(ev.keys)) / ev.ppm ** 2
        w = zero_bare(w, ev.keys, T.get("bare"))           # --- mockup-governs --- bare-shell tones: evidence only, never a thread
        # M4g: thread planner with the trade-off as options (threads.choice / answers.json), salience per tone
        zs0 = self._claims()                                # --- G1 --- zones, or the labelled parts (parts.labels.json)
        zm = {z["id"]: (np.ones((ev.H, ev.W), bool) if z.get("rest") else ev.mask(ZN.window(z))) &
                       (np.isin(ev.tone, [ev.keys.index(k) for k in z["tones"] if k in ev.keys]) if z.get("tones", "all") != "all" else True)
              for z in zs0["zones"]}                       # a motif = a zone whose OWN tones include the tone
        tp = TH.plan_from_config(dict(zip(ev.keys, w.tolist())), T, config.needles(cfg), sal=TH.salience(ev.tone, ev.keys, T["palette"], ev.ppm, zm))
        ctx = Ctx(ev, self.rb, cfg, tp["map"], T["protected"])
        label_q = None
        if cfg.get("labels"):                               # --- G1 --- labels -> generic primitives (no subject splitters)
            from digitize.labels import compile as LC
            parts, log, label_q = LC.extract(ctx, ev, self.labels, answers=(cfg.get("review") or {}).get("labels"))
            zs = zs0
        else:
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
            if k in M3B_SPLITTERS: return M3B_SPLITTERS[k](ctx, z, zz, m)          # M3b: trunk, crown, blossom
            if k == "building":                                    # M3a: building template fitter
                from digitize.extract.splitters import building; return building.split(ctx, z, zz, m)
            raise ValueError(f"zone {z['id']}: unknown splitter {k!r}")
        if not cfg.get("labels"): parts, log = ZN.claim_and_split(zs, ev, z_of, split)
        parts, left_out = RV.apply_extract(self.cfg, parts)                                    # M4g: answers
        if left_out: print(f"    answers: {len(left_out)} parts of zones answered 'leave out' are not sewn")
        n_traced = len(parts); sk = cfg.get("specks", {}) or {}
        parts, merged = SQ.merge_specks(parts, sk.get("min_mm2", cfg["stub"]["min_part_mm2"]), protected=T["protected"],
                                        min_protected_mm2=cfg["stub"]["min_protected_mm2"])
        hint_fix = hints.repoint(parts, merged)            # M3b: knockout_of targets merged away -> re-pointed (PR #10 review)
        sep = self.rb.principles["neighbour_sep_deg"]
        moves = DR.separate(parts, sep=tuple(sep), kinds=set(self.cfg.get("separate_kinds", ["stratum_band", "cloud_shade", "cloud_wisp"])))
        layers = sorted({(p.kind if p.kind != "zone_stub" else p.zone, p.z) for p in parts}, key=lambda t: t[1])
        plan = ObjectPlan(name=self.name, parts=parts, layers=[Layer(n, z) for n, z in layers],
                          threads=tp["threads"], meta=dict(crop=list(self.crop), view=self.view, extract_log=log, thread_merges=tp["merges"],
                                                           tone_map=tp["map"], evidence_tone_mm2={k: round(float(v), 1) for k, v in zip(ev.keys, w)},
                                                           source_ppm_median=self.ref()["source_ppm_median"],
                                                           separation_moves=[list(m) for m in moves], traced_parts=n_traced,
                                                           specks_merged=[list(m) for m in merged], thread_tradeoff=tp.get("tradeoff"),
                                                           review_answers=self.cfg.get("_answers_report"),
                                                           splitter_stats=getattr(ctx, "stats", {}), hint_repairs=[list(h) for h in hint_fix]))   # M3b: florets / clumps / trunks
        if cfg.get("labels"):                               # --- G1 ---
            import hashlib
            lpth = config.path(cfg, cfg["labels"])
            plan.meta.update(labels=dict(file=os.path.relpath(lpth, cfg["project"]), sha256=hashlib.sha256(open(lpth, "rb").read()).hexdigest()[:16],
                                         by=self.labels.get("source", {}).get("by"), parts=sum(1 for _ in __import__("digitize.labels.schema", fromlist=["x"]).iter_parts(self.labels))),
                             label_questions=label_q)
        if getattr(ctx, "building_report", None):                  # M3a: details under a rule 9 minimum, as SUGGESTIONS
            plan.meta["building_suggest"] = ctx.building_report.get("suggest", [])
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
        answered = RV.apply_plan(self.cfg, plan, self.rb)                                      # M4g: answers
        if self.cfg.get("_answers_report", {}).get("stale"):                                    # M4g: stale ids reported
            json.dump(self.cfg["_answers_report"], open(self.f("answers_report.json"), "w"), indent=1)
            print(f"answers: STALE (no such part / zone in this run): {self.cfg['_answers_report']['stale'][:8]}")
        sq = dict(SQ.SEQ_DEFAULTS, **self.cfg["sequence"]); n0 = len(plan.parts); m4 = sq["planner"] != "m1"   # M4g
        if m4: seqi = SQ.plan_sequence(plan, sq, P); dropped = seqi["dropped"]                             # M4g
        else:
            SQ.underlap(plan.parts, sq["keep_mm"]); SQ.cut_under(plan.parts, sq["keep_mm"])
            plan.parts, dropped = SQ.absorb_fragments(plan.parts, sq["min_fragment_mm2"])
        hint_fix = hints.repoint(plan.parts)                # M3b: a knockout_of target dropped as a fragment -> hint removed
        refreshed = DR.refresh_field_basis(plan.parts)                  # bases on the geometry actually sewn (audited)
        sep = self.rb.principles["neighbour_sep_deg"]
        moves = DR.separate(plan.parts, sep=tuple(sep), kinds=set(self.cfg.get("separate_kinds", ["stratum_band", "cloud_shade", "cloud_wisp"])))
        for p in plan.parts: issues += techniques.get(p.technique).check(p, P)
        if m4: pred = SQ.dag_v1(plan.parts, sq["touch"]); plan.stops = SQ.order_v1(plan.parts, pred=pred, lookahead=sq["stop_lookahead"])   # M4g
        else: plan.stops = SQ.order(plan.parts)
        used = {p.thread for p in plan.parts}
        plan.threads = {k: v for k, v in plan.threads.items() if k in used}
        need = config.needles(self.cfg)
        if TH.needles_used(plan.threads) > need:                                                # M4g: <colour>+foam = the same needle
            raise SystemExit(f"plan uses {TH.needles_used(plan.threads)} threads > {need} needles")
        CP.plan_blocks(plan)
        if m4:                                                                                             # M4g
            if sq["orient"]: seqi["travel"] = SQ.sequence_blocks(plan, sq["touch"], sq["group_bonus_mm"], pred=pred, inner_travel=sq["inner_travel"])
            seqi["budget"] = SQ.budget(plan, (self.cfg.get("budget") or {}).get("stitches_max"))
            seqi["report"] = SQ.report(plan, pred=pred); seqi["stack_max_plan"] = SQ.stack_count(plan.parts)
            seqi["seams"] = dict(pair=SQ.seam_report(plan.parts), any_lower=SQ.seam_report(plan.parts, any_lower=True))   # rule 6 underlap
            plan.meta["sequence"] = dict(planner="m4", stack_cut_parts=len(seqi["stack_cut"]),
                                         stack_cut_mm2=round(sum(c for _, c in seqi["stack_cut"]), 1), **{k: seqi[k] for k in
                                         ("hints", "budget", "report", "stack_max_plan", "seams") if k in seqi}, travel=seqi.get("travel"))
            print(f"sequence (M4): {plan.meta['sequence']['report']['stops']} stops, stack <= {seqi['stack_max_plan']} "
                  f"({len(seqi['stack_cut'])} parts cut), travel {seqi.get('travel')}, budget {seqi['budget']}")
        plan.meta.update(hint_repairs_plan=[list(h) for h in hint_fix], dropped_fragments=dropped, issues=issues, parts_before_sequence=n0,
                         field_basis_refreshed=refreshed, review_answers_plan=answered,
                         separation_moves_plan=[list(m) for m in moves])
        plan.to_json(self.f("plan.json")); self.plan = plan
        print(f"plan: {len(plan.parts)} parts ({len(dropped)} fragments dropped), {len(plan.stops)} stops, {len(plan.threads)} threads, "
              f"{len(issues)} check issues ({time.time() - t0:.1f} s)")
        return plan

    # ------------------------------------------------------------ review
    def review(self):
        plan = ObjectPlan.from_json(self.f("plan.json") if os.path.exists(self.f("plan.json")) else self.f("parts.json"))
        RV.part_map(plan, self.crop, self.f("part_map.png"))
        qs = RV.questions(plan, plan.meta.get("issues", []), rb=self.rb)                       # M4g: options = enabled techniques
        json.dump(qs, open(self.f("questions.json"), "w"), indent=1)
        parts_json = dict(name=plan.name, n=len(plan.parts), parts=[dict(id=p.id, kind=p.kind, zone=p.zone, thread=p.thread, z=p.z,
                          technique=p.technique, angle=p.dir.angle, dir_source=p.dir.source, area_mm2=round(p.area, 1)) for p in plan.parts])
        # --- M4c --- lit highlights grown to a visible size (crown.py): per part, traced vs drawn area and the growth used
        for d_, p in zip(parts_json["parts"], plan.parts):
            if p.meta.get("lit_growth"): d_["lit_growth"] = p.meta["lit_growth"]
        lg_ = [p.meta["lit_growth"] for p in plan.parts if p.meta.get("lit_growth")]
        if lg_:
            parts_json["lit_growth"] = dict(pieces=len(lg_), grown=sum(1 for g in lg_ if g["grow_mm"] > 0),
                                            traced_mm2=round(sum(g["traced_mm2"] for g in lg_), 1), added_mm2=round(sum(g["added_mm2"] for g in lg_), 1),
                                            max_grow_mm=max(g["grow_mm"] for g in lg_), note="added = growth to a visible size + dark slivers joined")
            print(f"review: lit highlights {parts_json['lit_growth']}")
        json.dump(parts_json, open(self.f("parts_summary.json"), "w"), indent=1)
        print(f"review: part_map.png, {len(qs)} questions")

    # ------------------------------------------------------------ compile
    def compile(self):
        t0 = time.time(); plan = ObjectPlan.from_json(self.f("plan.json"))
        res = CP.write(plan, self.base, self.origin, **(self.cfg.get("compile") or {}))   # G1: run.yaml compile: {exact_travel: {..., unsewn_only: true}}
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
        fixed = [p for p in plan.parts if p.dir.mode == "fixed" and techniques.get(p.technique).stype not in ("run", "bean")
                 and p.technique not in NO_FILL_DIRECTION]                     # M3b: a 1.2 mm bead has no fill direction
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
        florets_by_part_map(row, segs, sp, plan, self.crop)               # M3b: radial floret runs are fans, by the part map
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
        row["direction_by_source"] = audit.direction_by_source(dm, part_at, self.rb, plan.parts)   # M3b: one constructed basis
        if self.cfg.get("labels"):                          # --- G1 --- the label-angle tiles on their own line (counted independent)
            lab = [0, 0, 0]
            for k_, tiles in ((0, dm["ok_tiles"]), (1, [r["at_mm"] for r in dm["fail_dev"]]), (2, [r["at_mm"] for r in dm["fail_chaos"]])):
                for c in tiles:
                    p_ = part_at(c)
                    if p_ is not None and p_.dir.source == "label": lab[k_] += 1
            row["direction_label"] = dict(tiles=sum(lab), ok=lab[0], dev=lab[1], chaos=lab[2], pct_ok=round(100 * lab[0] / max(1, sum(lab)), 1),
                                          note="tiles whose top part's angle is the labeller's (source label); included in 'independent'")
        # --- M4c --- radial-floret exemption (gates_radial): raw chaos stays in row["direction"]; exempt tiles -> "radial"
        from digitize import gates_radial as GR
        ex = GR.tag_buckets(GR.exempt(dm, vis, [sp[i] for i in idx], plan.parts, GR.config(self.rb), ppm, origin=self.crop[:2]),
                            part_at, self.rb, plan.parts)
        row["direction_by_source_raw"] = row["direction_by_source"]; row["direction_by_source"] = GR.rebucket(row["direction_by_source"], ex)
        row["radial_exemption"] = ex; aux["radial_exempt"] = [t["at_mm"] for t in ex["exempt"]]
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
        ra = blossom.radial_adherence(plan, segs, sp, self.crop, ppm=ppm)    # M3b: radial florets, every stitch on its ray
        if ra["parts"] or ra["no_centre"] or ra["unseen"]:
            coh["radial_adherence"] = dict(ra, no_centre=ra["no_centre"][:40], unseen=ra["unseen"][:40], n_no_centre=len(ra["no_centre"]), n_unseen=len(ra["unseen"]))
            coh["ok"] = coh["ok"] and ra["ok"] and not ra["unseen"]
            for key, ids in (("no-visible-stitches / floret", ra["unseen"]), ("no-centre / floret", ra["no_centre"])):
                if ids:
                    coh["by_kind"][key] = len(ids); coh["fails"] += len(ids)
                    k0 = key.split(" / ")[0]; coh["kinds"][k0] = coh["kinds"].get(k0, 0) + len(ids)
        ca = trunk.column_adherence(plan, segs, sp, self.crop, ppm=ppm)     # M3b: branch columns, across the centreline
        if ca["parts"]:
            coh["column_adherence"] = ca; coh["ok"] = coh["ok"] and ca["pct_within"] >= 85.0
        # --- M4s --- part-based stack + travel on sewn fill, on the labelled written file (two new verdict lines)
        from digitize import gates_stack
        gates_stack.run_hook(row, plan, segs, sp, self.crop, self.cfg.get("gates_m4s"))
        if self.cfg.get("labels"):                          # --- G3 --- motif_match per labelled motif vs the reference the labels name
            row["motif_reference"] = self.motif_reference(dst)
        row["verdict"] = bench.verdict(row, self.cfg_b["targets"])
        json.dump(row, open(self.f("gates.json"), "w"), indent=1, default=float)
        self._row, self._aux = row, aux
        d = row["direction"]
        print(f"gates: direction {d['pct_ok']} % OK / {d['pct_chaos']} % chaotic; by kind " +
              ", ".join(f"{k} {v['pct_ok']}% of {v['tiles']}" for k, v in row["direction_by_kind"].items()) +
              "; by source " + ", ".join(f"{k} {v['pct_ok']}% of {v['tiles']}" for k, v in row["direction_by_source"].items()) +
              f"; random angles {aa['random_angles']}, sewn off angle {sw['sewn_off_angle']}; cords {len(cords)} ({len(cflags)} flags)"
              f"; coherence {'pass' if coh['ok'] else coh['kinds']}; {gates_stack.summary(row['verdict'])} gates"
              f"; M4s stack by parts {row['stack_parts']['over_mm2']} mm2 in regions > 2 = {row['stack_parts']['per_100cm2']} /100 cm2"
              f" (cap {row['stack_parts']['cap_per_100cm2']})"
              f", travel on sewn fill {row['travel_on_fill']['n_exposed']} stitches / {row['travel_on_fill']['exposed_mm']} mm")
        return row, aux

    def motif_reference(self, dst):
        """G3: every labelled motif (or part with its own `reference`) graded with qa.motif_match against the mockup
        (the GATE reference, bench.json's registration) or the picture its labels name (digitize.labels.refgrade).
        Reported, not a verdict line: which reference governs a motif is the labeller's (founder's) call."""
        import qa
        from digitize.labels import schema as LS, refgrade as RG
        lpth = config.path(self.cfg, self.cfg["labels"]); T = self.cfg["threads"]
        labels = LS.load(lpth, palette=T["palette"])
        reg = register.load(os.path.join(self.cfg["project"], self.cfg_b["registration"]))
        ev = evidence.build(register.reference(reg, self.view, self.crop, ppm=float(self.cfg_b["ppm"])), T["palette"], **self.cfg["evidence"])
        ms = qa.dst_stop_masks(dst, self.origin, (ev.H, ev.W), ev.ppm, to_mm=lambda x, y: (x - ev.bounds[0], y - ev.bounds[1]))
        out = np.any(list(ms.values()), axis=0) if ms else np.zeros((ev.H, ev.W), bool)
        rows = RG.grade(labels, os.path.dirname(lpth), ev, out, bare=tuple(T.get("bare") or ()))
        res = dict(source="digitize.labels.refgrade: qa.motif_match (near 1.5 mm) per labelled motif; mockup = bench registration",
                   labels=os.path.relpath(lpth, self.cfg["project"]), summary=RG.summary(rows), rows=rows)
        print("    motif reference: " + ", ".join(f"{k} {v['ok']}/{v['n']} (IoU {v['mean_iou']})" for k, v in res["summary"].items()))
        return res

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
    ap.add_argument("--answers", help="answers.json to the previous run's questions.json (M4g review step)")
    a = ap.parse_args(argv)
    if config.load(a.run_yaml).get("source") == "svg":          # M5: founder vector art as the part source
        from digitize import svgrun; return svgrun.main(argv)
    print("[info] digitize.run makes no Anthropic API calls (M1); --no-api accepted.")
    st = STAGES if a.stages == "all" else [s.strip() for s in a.stages.split(",")]
    for s in st:
        if s not in STAGES: raise SystemExit(f"unknown stage {s!r} (have {STAGES})")
    r = Run(a.run_yaml, answers=a.answers); t0 = time.time()
    order = ["extract", "plan", "review", "compile", "gates", "panel", "bench"]
    for s in order:
        if s not in st: continue
        {"extract": r.extract, "plan": r.make_plan, "review": r.review, "compile": r.compile, "gates": r.gates,
         "panel": r.panel, "bench": r.bench}[s]()
    print(f"done in {time.time() - t0:.0f} s -> {r.out}")


if __name__ == "__main__":
    main()
