"""Digitize founder vector art end to end (ENGINE_PLAN M5: SVG parity on Konpeito). No Anthropic API calls.

  python3 -m digitize.run projects/konpeito-jeans/bench/run_wb_svg.yaml --no-api      (run.py hands `source: svg` here)
  python3 -m digitize.svgrun <run.yaml> --stages extract,plan,compile --no-api

Stages (comma list, or "all"):
  extract  founder SVG -> parts.json (extract/svg.py: kind by layer role / shape, thread by fill, declared directions)
  plan     rulebook (technique + numbers per kind) -> sequence (paint order = z; touching parts keep it, others batch by
           colour; meta last=True parts sew in a final stop) -> technique plugins -> plan.json
  review   part_map.png + questions.json (type-follows-shape issues, house-minimum dots)
  compile  dst2.make_pattern (prebuilt blocks, keep_order, exact_travel from run.yaml) -> <name>.dst/.pes + readback.json
  gates    on the FILE vs cairosvg masks of the founder's layers: centreline gate per column layer, motif IoU per other
           layer (own stops, near-restricted), A15 uncovered, exposed stitches on the exact geometry, threads <= needles,
           max stitch, angle coherence of the fills, direction per object layer -> gates.json
  panel    founder art | part map | live view | density -> panel.png
Outputs: <project>/<out_dir>/ (git-ignored)."""
import argparse, json, math, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
if ENGINE not in sys.path: sys.path.insert(0, ENGINE)

import numpy as np
from shapely.ops import unary_union
from digitize import config, sequence as SQ, compile as CP, techniques, threads as TH
from digitize.schema import ObjectPlan, Layer
from digitize.rulebook import Rulebook

STAGES = ["extract", "plan", "review", "compile", "gates", "panel"]
SPEC_KEYS = ("techniques", "dir", "z", "note", "spacing", "stitch_len", "underlay", "pull_comp")
COLUMN_KINDS = ("lettering", "line_art")
SKIP_IOU = ("patch_band", "patch_field", "patch_edge", "fill")


def kind_params(rb, kind):
    """kind-level numbers that are not StitchSpec fields (same_side, min_d, ...) -> spec.params"""
    return {k: v for k, v in rb.rule(kind).items() if k not in SPEC_KEYS}


class SvgRun:
    def __init__(self, yaml_path, overrides=None):
        self.cfg = config.load(yaml_path, overrides)
        if self.cfg.get("source") != "svg": raise SystemExit(f"{yaml_path}: not an SVG run (source: svg)")
        from digitize.extract import svg_auto
        svg_auto.fill_config(self.cfg)                       # S1: no palette in the yaml -> derived from the SVG itself
        self.out = config.path(self.cfg, self.cfg["out_dir"]); os.makedirs(self.out, exist_ok=True)
        self.rb = Rulebook(self.cfg.get("rules"), toggles=self.cfg["techniques"], overrides=self.cfg.get("rule_overrides"))
        self.name = self.cfg["name"]; self.base = os.path.join(self.out, self.name)

    def f(self, name): return os.path.join(self.out, name)

    # ------------------------------------------------------------ extract
    def extract(self):
        from digitize.extract import svg as XS
        t0 = time.time(); parts, info = XS.extract(self.cfg, self.rb)
        T = self.cfg["threads"]; used = []
        for p in parts:
            if p.thread not in used: used.append(p.thread)
        threads = {k: dict(hex=T["palette"][k], name=T.get("names", {}).get(k, k), protected=k in T.get("protected", []),
                           weight=T.get("weight", {}).get(k, "40wt")) for k in used}
        kinds = sorted({p.kind for p in parts})
        plan = ObjectPlan(name=self.name, parts=parts, layers=[Layer(L["id"], float(L["order"])) for L in info["layers"]],
                          threads=threads, meta=dict(source="svg", svg=info, kinds=kinds))
        plan.to_json(self.f("parts.json"), with_blocks=False)
        print(f"extract: {len(parts)} parts from {len(info['layers'])} SVG layers, {len(threads)} threads, kinds {kinds} ({time.time() - t0:.1f} s)")
        for L in info["layers"]: print(f"    {L['id']:<34} {L['role']:<14} {L['parts']} parts")
        for k, v in info["widths"].items(): print(f"    width {k}: art {v['w_art']} -> needle {v['w_needle']} ({v['thread']})")
        return plan

    # ------------------------------------------------------------ plan
    def make_plan(self):
        t0 = time.time(); plan = ObjectPlan.from_json(self.f("parts.json")); P = self.rb.principles; issues = []
        fab = None
        if self.cfg.get("fabric"):
            from digitize.extract.svg_auto import fabric_rules
            fab = fabric_rules(self.cfg["fabric"])
        for p in plan.parts:
            p.technique = self.rb.technique_for(p.kind); p.stitch = self.rb.stitch_spec(p.kind, p.technique)
            p.stitch.params.update(kind_params(self.rb, p.kind))
            if p.technique == "dot" and p.meta.get("min_d"): p.stitch.params["min_d"] = p.meta["min_d"]
            if fab: apply_fabric(p, fab)
        sq = self.cfg["sequence"]
        if sq.get("cut_under", False): SQ.cut_under(plan.parts, sq["keep_mm"])
        for p in plan.parts: issues += techniques.get(p.technique).check(p, P)
        body = [p for p in plan.parts if not p.meta.get("last")]; last = [p for p in plan.parts if p.meta.get("last")]
        plan.stops = order_complete(body, touch=float(sq.get("touch", 0.5))) if body else []
        for p in sorted(last, key=lambda p: p.z):
            if plan.stops and plan.stops[-1]["thread"] == p.thread and plan.stops[-1].get("last"): plan.stops[-1]["parts"].append(p.id)
            else: plan.stops.append(dict(thread=p.thread, parts=[p.id], last=True))
        need = config.needles(self.cfg)
        if TH.needles_used(plan.threads) > need:                                                # M4g: <colour>+foam = the same needle
            if not self.cfg["threads"].get("allow_over"):
                raise SystemExit(f"plan uses {TH.needles_used(plan.threads)} threads > {need} needles")
            plan.meta["threads_over"] = TH.needles_used(plan.threads)      # S1 (svg2dst): written, and the thread gate fails
        CP.plan_blocks(plan)
        plan.meta.update(issues=issues)
        plan.to_json(self.f("plan.json")); self.plan = plan
        print(f"plan: {len(plan.parts)} parts, {len(plan.stops)} stops, {len(plan.threads)} threads, {len(issues)} check issues "
              f"({sum(1 for i in issues if i.get('severity') == 'report')} reported) ({time.time() - t0:.1f} s)")
        return plan

    # ------------------------------------------------------------ review
    def review(self):
        plan = ObjectPlan.from_json(self.f("plan.json"))
        W, H = plan.meta["svg"]["size_mm"]; b = self.bounds(plan)
        part_map(plan, b, self.f("part_map.png"))
        qs = [dict(q) for q in (self.cfg.get("_s1") or {}).get("questions", [])]          # S1: the derived-config questions first
        for k, i in enumerate(plan.meta.get("issues", []), 1):
            qs.append(dict(id=f"q{k:03d}", text=i["text"], part_ids=[i["part"]], options=["accept", "change"], default="accept",
                           topic=i.get("technique"), severity=i.get("severity", "check")))
        json.dump(qs, open(self.f("questions.json"), "w"), indent=1)
        print(f"review: part_map.png, {len(qs)} questions")

    def bounds(self, plan):
        from dst2 import bounds_of
        return bounds_of([p.geom for p in plan.parts])

    # ------------------------------------------------------------ compile
    def compile(self):
        import factory
        t0 = time.time(); plan = ObjectPlan.from_json(self.f("plan.json"))
        b = self.bounds(plan); origin = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        res = CP.write(plan, self.base, origin, **dict(dict(join_guard=False), **self.cfg.get("compile", {})))   # B39 guard opt-in here (G1)
        if len(res["seg_parts"]) != len(res["segs"]): raise RuntimeError("compile: labels out of step with stitches")
        import dst2
        rb = res["readback"]; ex = sorted(dst2.exposed_travel(res["regions"], res["runs"]))
        prof = factory.load()
        mins = factory.machine_hours(rb["stitches"], prof, trims=rb["trims"], colour_changes=rb["stops"] - 1) * 60
        json.dump(dict(base=os.path.basename(self.base), origin=res["origin"], build=res["build"], readback=rb, stops=res["stops"],
                       exact_trims=res["exact_trims"], exposed_travel_gt1mm=sum(1 for v in ex if v > 1.0),
                       max_exposed_travel=round(ex[-1], 2) if ex else 0.0, machine_min=round(mins, 1),
                       threads=factory.check_threads(self.base + ".pes")),
                  open(self.f("readback.json"), "w"), indent=1)
        np.savez_compressed(self.f("stitch_parts.npz"), segs=np.asarray(res["segs"], np.float32), parts=np.asarray([p or "" for p in res["seg_parts"]]))
        print(f"compile: {rb['stitches']} stitches, {rb['trims']} trims, {rb['stops']} stops, max stitch {rb['max_stitch']} mm, "
              f"{res['exact_trims']} exact-geometry trims ({time.time() - t0:.1f} s)")
        return res

    # ------------------------------------------------------------ gates
    def gates(self):
        g = gate_file(self.cfg, ObjectPlan.from_json(self.f("plan.json")), self.base + ".dst", json.load(open(self.f("readback.json"))),
                      seg_npz=self.f("stitch_parts.npz"))
        json.dump(g, open(self.f("gates.json"), "w"), indent=1, default=float)
        cl = g["centreline"]; mm = g["motifs"]
        print(f"gates: centreline {sum(r['ok'] for r in cl)}/{len(cl)} strings pass; motifs "
              f"{sum(r['passed'] for r in mm)}/{sum(r['motifs'] for r in mm)} pass (+house-min); uncovered {len(g['uncovered'])}; "
              f"exposed stitches {len(g['exposed_stitches'])}; threads {g['file']['threads']} <= {g['file']['needles']}; "
              f"fills coherent {g['coherence']['ok']}")
        self._g = g
        return g

    # ------------------------------------------------------------ panel
    def panel(self):
        import svgart, dstlive, qa
        from PIL import Image
        from digitize import panel as PN
        plan = ObjectPlan.from_json(self.f("plan.json")); rbk = json.load(open(self.f("readback.json")))
        g = self._g if hasattr(self, "_g") else json.load(open(self.f("gates.json")))
        P = 12.0; b = self.bounds(plan); pad = 1.5; bb = (b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad)
        W, H = int(round((bb[2] - bb[0]) * P)), int(round((bb[3] - bb[1]) * P))
        sv = plan.meta["svg"]; fr = sv["frame"]
        art = svgart.render(sv["svg"], sv["size_mm"][0], sv["size_mm"][1], ppm=P * fr["s"], bg=self.cfg.get("panel_bg", "#2A2A2E"))
        canvas = Image.new("RGB", (W, H), (42, 42, 46))
        ox = int(round((fr["t"][0] - fr["c0"][0] * fr["s"] - bb[0]) * P)); oy = int(round((fr["t"][1] - fr["c0"][1] * fr["s"] - bb[1]) * P))
        canvas.paste(art, (ox, oy))
        part_map(plan, bb, self.f("part_map_panel.png"), ppm=P)
        pm = Image.open(self.f("part_map_panel.png")).convert("RGB")
        cols = [t["hex"] for t in (plan.threads[s["thread"]] for s in plan.stops)]
        live = dstlive.render(self.base + ".dst", cols, ppm=P * 2, shell="#1f1f22", bounds=bb, origin=tuple(rbk["origin"])).resize((W, H), Image.LANCZOS)
        segs = [(a[0], a[1], c[0], c[1]) for _, a, c in qa.dst_stitches(self.base + ".dst", tuple(rbk["origin"]))]
        dm = qa.density_map(segs, bb)
        den = Image.fromarray(PN.ramp(dm["grid"])).resize((W, H), Image.NEAREST)
        f = g["file"]
        cl = g["centreline"]; mm = g["motifs"]
        tiles = [(canvas, f"founder art (cairosvg) - {os.path.basename(sv['svg'])}"),
                 (pm, f"part map: {len(plan.parts)} parts, thread colour, red tick = declared angle (radial / dots: centre)"),
                 (live, f"live view - {f['stitches']:,} st, {f['trims']} trims, {f['stops']} stops, {f['threads']} threads"),
                 (den, f"density mm/mm2: mean {dm['mean']}, p95 {dm['p95']}, {len(dm['flags'])} areas > 7 (navy 1, green 5, red 9+)")]
        legend = (f"{self.cfg.get('label', self.name)}  |  centreline {sum(r['ok'] for r in cl)}/{len(cl)} strings  |  motifs "
                  f"{sum(r['passed'] for r in mm)}/{sum(r['motifs'] for r in mm)}  |  exposed stitches {len(g['exposed_stitches'])}  |  "
                  f"uncovered {len(g['uncovered'])}  |  M5 engine (digitize.svgrun)")
        PN.compose(tiles, legend, self.f("panel.png"), quantize=False)
        live_big = dstlive.render(self.base + ".dst", cols, ppm=30, shell="#1f1f22", bounds=bb, origin=tuple(rbk["origin"]))
        live_big.save(self.f("live.png"))
        print(f"panel: {self.f('panel.png')} + live.png")


def apply_fabric(p, fab):
    """rules/fabrics.yaml deltas on one part's StitchSpec (S1, svg2dst --fabric). twill / denim carry none."""
    t = p.technique; sp = p.stitch
    if t in ("tatami", "satin", "split_satin", "column_satin", "turning_satin", "radial") and fab.get("pull_add"):
        sp.pull_comp = round(sp.pull_comp + float(fab["pull_add"]), 3)
    if t == "tatami" and fab.get("spacing_mul"): sp.spacing = round(sp.spacing * float(fab["spacing_mul"]), 3)
    if t == "tatami" and fab.get("lattice_all"):
        sp.params["lattice_min_mm2"] = 0.0
        if "lattice_90" not in sp.underlay: sp.underlay = list(sp.underlay) + ["lattice_90"]
    if t == "column_satin" and fab.get("centre_run_min_w"):
        sp.params["centre_run_min_w"] = min(float(sp.params.get("centre_run_min_w", 1.4)), float(fab["centre_run_min_w"]))
        if sp.underlay == [] and p.kind not in ("patch_edge",): sp.underlay = ["centre_run"]


# ------------------------------------------------------------------ sequence for patches
def order_complete(parts, touch=0.5):
    """sequence.order's z-DAG (a part sews after every lower-z part it touches / overlaps), with one change in how the
    next thread is chosen when the current one has no free part: prefer a thread whose REMAINING parts are all free
    now or waits only on its own thread (sewing it empties it: no second stop of that colour later), then the deepest free z, then the most free area.
    On the coin patch the M1 rule ("deepest free layer first") sewed the white specks once per candy (3 white stops);
    this sews them once, after all candies (14 -> 12 stops)."""
    from collections import defaultdict
    pred = SQ.dag(parts, touch); n = len(parts); done = [False] * n; left = {i: set(pred[i]) for i in range(n)}
    stops = []; cur = None; pos = None
    while not all(done):
        free = [i for i in range(n) if not done[i] and not left[i]]
        if not free: raise RuntimeError("sequence: cycle in the z-DAG")
        same = [i for i in free if parts[i].thread == cur]
        if not same:
            fr = defaultdict(list)
            for i in free: fr[parts[i].thread].append(i)
            waits = defaultdict(bool)                  # a remaining part of t waits on a part of ANOTHER thread
            for i in range(n):
                if not done[i] and any(parts[j].thread != parts[i].thread for j in left[i]): waits[parts[i].thread] = True
            key = lambda t: (not waits[t], -min(parts[i].z for i in fr[t]), sum(parts[i].area for i in fr[t]), t)
            cur = max(fr, key=key); stops.append(dict(thread=cur, parts=[])); continue
        c = lambda i: parts[i].geom.representative_point().coords[0]
        i = min(same, key=lambda i: (math.dist(pos, c(i)) if pos else 0.0, parts[i].z, parts[i].id))
        done[i] = True; stops[-1]["parts"].append(parts[i].id); pos = c(i)
        for j in range(n): left[j].discard(i)
    return [s for s in stops if s["parts"]]


# ------------------------------------------------------------------ part map
def part_map(plan, bounds, path, ppm=8.0):
    from PIL import Image, ImageDraw
    from digitize.techniques import polys
    x0, y0, x1, y1 = bounds; W, H = int(round((x1 - x0) * ppm)), int(round((y1 - y0) * ppm))
    im = Image.new("RGB", (W, H), (40, 44, 52)); d = ImageDraw.Draw(im)
    T = lambda cs: [((x - x0) * ppm, (y - y0) * ppm) for x, y in cs]
    for p in sorted(plan.parts, key=lambda p: p.z):
        h = plan.threads.get(p.thread, {}).get("hex", "#969696").lstrip("#"); c = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
        c = tuple(int(v * 0.75 + 128 * 0.25) for v in c)
        for q in polys(p.geom):
            m = Image.new("L", (W, H), 0); dm = ImageDraw.Draw(m); dm.polygon(T(q.exterior.coords), fill=255)
            for r in q.interiors: dm.polygon(T(r.coords), fill=0)
            im.paste(c, mask=m); d.line(T(q.exterior.coords), fill=(25, 25, 25), width=1)
    for p in plan.parts:
        if p.area < 1.5 or p.technique in ("radial", "dot"): continue
        pt = p.geom.representative_point(); cx, cy = (pt.x - x0) * ppm, (pt.y - y0) * ppm
        a = math.radians(p.dir.angle); L = min(3.0, 0.5 * math.sqrt(p.area)) * ppm
        d.line([(cx - L * math.cos(a), cy - L * math.sin(a)), (cx + L * math.cos(a), cy + L * math.sin(a))], fill=(220, 30, 30), width=1)
    im.save(path); return path


# ------------------------------------------------------------------ gates on the file
def gate_file(cfg, plan, dst, rbk, seg_npz=None):
    """every M5 gate on the written DST vs the founder's layers (cairosvg). Families = SVG layers; a family's DST
    stitches = the stops that sew its parts (plan.stops order = file order)."""
    import svgart, qa, factory
    from scipy import ndimage as ndi
    G = cfg.get("gates", {}); ppm = float(G.get("ppm", 20)); sv = plan.meta["svg"]; W, H = sv["size_mm"]
    fr = sv["frame"]; s, c0, t = fr["s"], fr["c0"], fr["t"]
    to_svg = lambda x, y: ((x - t[0]) / s + c0[0], (y - t[1]) / s + c0[1])
    origin = tuple(rbk["origin"]); shape = (int(round(H * ppm)), int(round(W * ppm)))
    TD = G.get("thread_d", {"40wt": 0.40, "60wt": 0.28})
    stop_of = {pid: i for i, st in enumerate(plan.stops) for pid in st["parts"]}
    wt = {i: plan.threads[st["thread"]].get("weight", "40wt") for i, st in enumerate(plan.stops)}
    masks = qa.dst_stop_masks(dst, origin, shape, ppm, thread_d={i: TD[w] / s for i, w in wt.items()}, to_mm=to_svg)
    by_layer = {}; fam_els = {}
    for p in plan.parts:                    # S1: a mixed layer is gated per family (lines | shapes) on its own source shapes
        lid = p.meta.get("layer", p.zone); key = (lid, p.meta["s1_fam"]) if p.meta.get("s1_fam") else lid
        by_layer.setdefault(key, []).append(p)
        if p.meta.get("s1_el"): fam_els.setdefault(key, set()).update(p.meta["s1_el"])
    fams_of = {}
    for key in by_layer: fams_of.setdefault(key[0] if isinstance(key, tuple) else key, []).append(key)
    CLc = G.get("centreline", {}); MOc = G.get("motif", {})
    cl_rows, motif_rows, rows_all = [], [], {}
    refs = {}
    for key, ps in by_layer.items():
        lid = key[0] if isinstance(key, tuple) else key
        els = fam_els.get(key) if isinstance(key, tuple) and len(fams_of[lid]) > 1 else None
        ref = svgart.layer_mask(sv["svg"], [lid], W, H, ppm, els=els, exact=bool(cfg["svg"].get("auto"))); refs[key] = ref
        if isinstance(key, tuple) and len(fams_of[lid]) > 1: lid = f"{lid} [{key[1]}s]"
        kinds = {p.kind for p in ps}; stops = sorted({stop_of[p.id] for p in ps if p.id in stop_of})
        if kinds & set(COLUMN_KINDS):
            wts = {p.meta.get("thread_wt", "40wt") for p in ps}; w_ = sorted(wts)[0]
            m = np.any([masks[i] for i in stops if i in masks], axis=0) if stops else np.zeros(shape, bool)
            pull = max(p.stitch.pull_comp for p in ps if p.kind in COLUMN_KINDS)
            r = qa.centreline_match(ref, m, ppm, name=f"{lid} {w_}", pull=pull / s, near_mm=CLc.get("near_mm", 1.0),
                                    d_max=CLc.get("d_max", 0.5), w_tol=CLc.get("w_tol", 0.20))
            r.update(layer=lid, stops=[i + 1 for i in stops]); cl_rows.append(r); continue
        if kinds <= set(SKIP_IOU): continue
        near = MOc.get("near_mm_knot", 0.15) if "knot" in kinds else MOc.get("near_mm", 0.3)
        rows = qa.motif_match(ref, masks, ppm, min_mm2=MOc.get("min_mm2", 0.5), near_mm=near, out_stops=stops)
        for r in rows:
            d_art = 2 * math.sqrt(r["area_mm2"] / math.pi)
            r["house_min"] = bool(not r["ok"] and d_art < 1.15 and r["iou"] >= 0.6 and min(r["w_ratio"], r["h_ratio"]) >= 0.8)
        rows_all[lid] = rows
        motif_rows.append(dict(family=lid, kinds=sorted(kinds), motifs=len(rows), passed=sum(r["ok"] or r["house_min"] for r in rows),
                               house_min=sum(r["house_min"] for r in rows), min_iou=min([r["iou"] for r in rows], default=None),
                               mean_iou=round(float(np.mean([r["iou"] for r in rows])), 2) if rows else None, stops=[i + 1 for i in stops]))
    allout = np.any(list(masks.values()), axis=0) if masks else np.zeros(shape, bool)
    design = np.any(list(refs.values()), axis=0)
    if cfg["svg"].get("auto"):              # S1: art may enclose bare fabric (a ring logo): fill only pinholes (<= 4 mm2)
        holes = ndi.binary_fill_holes(design) & ~design; lab, n = ndi.label(holes)
        if n:
            sz = ndi.sum(holes, lab, range(1, n + 1)) / ppm ** 2
            design = design | np.isin(lab, [i + 1 for i, a in enumerate(sz) if a <= 4.0])
    else: design = ndi.binary_fill_holes(design)
    unc = qa.uncovered(design, allout, ppm)
    stop_geoms = [unary_union([plan.part(pid).geom for pid in st["parts"]]) for st in plan.stops]
    EX = dict(halo=0.25, min_mm=0.5, min_ex=0.3, **G.get("exposed", {}))
    exs = qa.exposed_stitches(dst, origin, stop_geoms, **EX)
    rb = rbk["readback"]; need = factory.max_threads()
    file = dict(stitches=rb["stitches"], trims=rb["trims"], jumps=rb["jumps"], stops=rb["stops"], threads=rbk.get("threads"),
                needles=need, max_stitch=rb["max_stitch"], size_mm=rb["size_mm"], machine_min=rbk.get("machine_min"),
                exact_trims=rbk.get("exact_trims"), exposed_travel_gt1mm=rbk.get("exposed_travel_gt1mm"))
    # fills: the visible stitches of each tatami part keep ONE direction (angle_coherence on the plan's part ids)
    coh = dict(ok=True, fails=0, parts=0)
    if seg_npz and os.path.exists(seg_npz):
        z = np.load(seg_npz); segs = [tuple(map(float, q)) for q in z["segs"]]; sp = [q or None for q in z["parts"].tolist()]
        from dst2 import bounds_of
        bb = bounds_of([p.geom for p in plan.parts])
        vis, idx = qa.visible_segments(segs, bb, ppm=12.0, return_index=True)
        vis = [(a - bb[0], b - bb[1], c - bb[0], d - bb[1]) for a, b, c, d in vis]
        fills = [p for p in plan.parts if p.technique == "tatami"]
        from shapely import affinity
        regs = [dict(geom=affinity.translate(p.geom, -bb[0], -bb[1]), stype="tatami", angle=p.dir.angle, grp=p.kind, part=p.id) for p in fills]
        bad = qa.angle_coherence(regs, groups=tuple(sorted({p.kind for p in fills})), segs=vis, seg_parts=[sp[i] for i in idx]) if fills else []
        coh = dict(ok=not bad, fails=len(bad), parts=len(fills), failing=bad[:10])
    gates = dict(centreline_all=all(r["ok"] for r in cl_rows), motifs_all=all(r["passed"] == r["motifs"] for r in motif_rows),
                 uncovered_none=not unc, exposed_none=not exs, threads_ok=(file["threads"] or 0) <= need,
                 max_stitch_ok=rb["max_stitch"] <= 7.5, fills_coherent=coh["ok"])
    return dict(file=file, centreline=cl_rows, motifs=motif_rows, motif_rows=rows_all, uncovered=unc, exposed_stitches=exs,
                coherence=coh, gates=gates, all_pass=all(gates.values()))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_yaml")
    ap.add_argument("--stages", default="all")
    ap.add_argument("--no-api", action="store_true", help="no Anthropic API calls (the only mode; accepted for the M4 question step)")
    a = ap.parse_args(argv)
    print("[info] digitize.svgrun makes no Anthropic API calls; --no-api accepted.")
    st = STAGES if a.stages == "all" else [s.strip() for s in a.stages.split(",")]
    for s in st:
        if s not in STAGES: raise SystemExit(f"unknown stage {s!r} (have {STAGES})")
    r = SvgRun(a.run_yaml); t0 = time.time()
    for s in STAGES:
        if s in st: {"extract": r.extract, "plan": r.make_plan, "review": r.review, "compile": r.compile, "gates": r.gates, "panel": r.panel}[s]()
    print(f"done in {time.time() - t0:.0f} s -> {r.out}")


if __name__ == "__main__":
    main()
