#!/usr/bin/env python3
"""SVG -> DST drop-in (ENGINE_PLAN S1; contract docs/SVG2DST.md, svg2dst/1). Any SVG, no run.yaml. No Anthropic API calls.

  python3 scripts/svg2dst.py --svg IN.svg --width-mm 90 --fabric twill --hoop 300x300 --out OUT/ [--answers a.json] [--name design] --no-api

1. contract checks (services/svg2dst/contract.py: size, refused links / DOCTYPE, inputs)
2. svg_auto.normalize: the drawn art scaled to --width-mm (1 user unit = 1 finished mm), shapes numbered
3. svg_auto.derive: threads (nearest Isacord, dE), a role per shape from its geometry, 60wt, patch or flat, fabric ->
   run.yaml in OUT/ (the record of what was decided) + the questions it was unsure about (answers.json picks next run)
4. digitize.svgrun: extract -> plan -> compile (DST + PES) -> gates on the written file -> preview.png + panel.png
5. result.json (svg2dst/1). ok = every HARD gate passed. Exit 0 files written, 2 input refused, 1 engine crash.

Hard gates (the machine and the art must be safe): every shape read, fits the hoop, threads <= needles, longest stitch,
has stitches, no float over bare fabric (exposed stitches), no uncovered design area. The fidelity gates (centrelines,
motif IoU, fill coherence) and open questions are reported, soft: the founder judges the preview."""
import argparse, json, os, subprocess, sys, time, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (os.path.join(ROOT, "engine"), os.path.join(ROOT, "services", "svg2dst")):
    if p not in sys.path: sys.path.insert(0, p)

from contract import CONTRACT, InputError, check_inputs, check_svg_text, parse_hoop, check_result  # noqa: E402

FRAME_MARGIN = 16.0          # LESSONS B10: each hooping holds frame - 16 mm (crosses + clamp)
TECHNIQUES = {"tatami": "fill", "column_satin": "satin column", "turning_satin": "satin per lobe", "radial": "radial satin",
              "dot": "bead dot", "satin": "satin", "split_satin": "split satin", "run": "run", "bean": "bean"}


def engine_version():
    v = os.environ.get("RAILWAY_GIT_COMMIT_SHA") or os.environ.get("ENGINE_VERSION")
    if v: return v[:12]
    try:
        return subprocess.run(["git", "-C", ROOT, "rev-parse", "--short=12", "HEAD"], capture_output=True, text=True, timeout=5).stdout.strip() or "s1"
    except Exception:
        return "s1"


def gate(id_, label, value, limit, ok, hard):
    return {"id": id_, "label": label, "value": str(value), "limit": str(limit), "pass": bool(ok), "hard": bool(hard)}


def run(a):
    t0 = time.time()
    svg = open(a.svg, encoding="utf-8", errors="replace").read()
    check_svg_text(svg)
    answers = json.load(open(a.answers)) if a.answers else {}
    if isinstance(answers, dict) and isinstance(answers.get("answers"), dict): answers = answers["answers"]
    width, fabric, hoop, answers = check_inputs(a.width_mm, a.fabric, a.hoop, answers)
    hw, hh = parse_hoop(hoop)
    os.makedirs(a.out, exist_ok=True)
    import svgart
    from digitize.extract import svg_auto as A
    from digitize.svgrun import SvgRun
    try:
        norm, ninfo = A.normalize(a.svg, os.path.join(a.out, "art.svg"), width)
        cfg = dict(name=a.name, label=f"svg2dst {os.path.basename(a.svg)}", source="svg", fabric=fabric,
                   out_dir=os.path.abspath(a.out), project=os.path.abspath(a.out), review=dict(s1_answers=answers),
                   svg=dict(file=os.path.abspath(norm), auto=True))
        run_yaml = os.path.join(a.out, "run.yaml")
        json.dump(cfg, open(run_yaml, "w"), indent=1)             # JSON is valid YAML
        r = SvgRun(run_yaml)                                       # svg_auto.fill_config derives everything else here
    except (A.AutoError, svgart.SvgError) as e:
        raise InputError(str(e))
    auto = r.cfg["_s1"]
    json.dump({k: v for k, v in r.cfg.items() if not k.startswith("_")}, open(os.path.join(a.out, "run_derived.json"), "w"),
              indent=1, default=str)                               # the record of every derived choice
    r.extract(); plan = r.make_plan(); r.review(); r.compile(); g = r.gates()
    try: r.panel()
    except Exception as e: print(f"[warning] panel failed: {e}", file=sys.stderr)
    import dstlive
    from digitize.schema import ObjectPlan
    rbk = json.load(open(r.f("readback.json"))); plan = ObjectPlan.from_json(r.f("plan.json"))
    cols = [plan.threads[s["thread"]]["hex"] for s in plan.stops]
    b = r.bounds(plan); pad = 2.0; bb = (b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad)
    ppm = max(4.0, min(24.0, 1600.0 / max(bb[2] - bb[0], bb[3] - bb[1])))
    dstlive.render(r.base + ".dst", cols, ppm=ppm, shell="#2b2b30", bounds=bb, origin=tuple(rbk["origin"])).save(os.path.join(a.out, "preview.png"))
    f = g["file"]; rb = rbk["readback"]; size = rb["size_mm"]
    need = f["needles"]; n_thr = len({s["thread"] for s in plan.stops})
    art_iou = svgart.art_read(norm, ppm=min(20.0, float(r.cfg["gates"].get("ppm", 10.0))))
    fits = (size[0] <= hw - FRAME_MARGIN and size[1] <= hh - FRAME_MARGIN) or (size[0] <= hh - FRAME_MARGIN and size[1] <= hw - FRAME_MARGIN)
    cl = g["centreline"]; mm = g["motifs"]
    qs = [q for q in json.load(open(r.f("questions.json"))) if q.get("topic") in ("patch", "role", "threads")]
    gates = [
        gate("engine_real", "Made by the real digitising engine (S1)", "svg2dst", "svg2dst", True, True),
        gate("art_read", "Every shape in the SVG was read", f"{art_iou:.3f} of the art", ">= 0.980", art_iou >= 0.98, True),
        gate("fits_hoop", f"Fits the {hw}x{hh} hoop", f"{size[0]:.0f} x {size[1]:.0f} mm", f"<= {hw - FRAME_MARGIN:.0f} x {hh - FRAME_MARGIN:.0f} mm", fits, True),
        gate("threads_le_needles", "Thread colours fit the machine", n_thr, f"<= {need}", n_thr <= need, True),
        gate("max_stitch", "Longest stitch", f"{rb['max_stitch']} mm", "<= 7.5 mm", rb["max_stitch"] <= 7.5, True),
        gate("has_stitches", "File has stitches", rb["stitches"], "> 0", rb["stitches"] > 0, True),
        gate("exposed_none", "No thread floating over bare fabric", len(g["exposed_stitches"]), "0", not g["exposed_stitches"], True),
        gate("uncovered_none", "No part of the design left unstitched (>= 25 mm2)", len(g["uncovered"]), "0", not g["uncovered"], True),
        gate("centreline_all", "Lines and lettering follow the art (centreline)", f"{sum(x['ok'] for x in cl)}/{len(cl)} strings", "all", all(x["ok"] for x in cl), False),
        gate("motifs_all", "Shapes match the art (IoU >= 0.70)", f"{sum(x['passed'] for x in mm)}/{sum(x['motifs'] for x in mm)} shapes", "all", all(x["passed"] == x["motifs"] for x in mm), False),
        gate("fills_coherent", "Each fill keeps one stitch direction", f"{g['coherence']['fails']} failing of {g['coherence']['parts']}", "0", g["coherence"]["ok"], False),
        gate("questions_answered", "Engine questions answered", f"{len(qs)} open", "0", not qs, False),
    ]
    fr = A.fabric_rules(fabric); warnings = list(ninfo["warnings"]) + list(auto["warnings"])
    if fr.get("proposed"): warnings.append(f"fabric {fabric}: underlay / density / pull numbers are PROPOSED (rules/fabrics.yaml); confirm on a strike-off")
    hm = sum(x.get("house_min", 0) for x in mm)
    if hm: warnings.append(f"{hm} dot(s) are smaller than the house minimum and are sewn at the minimum size")
    threads = []
    names = plan.threads; dE = {row["thread"]: row for row in auto["report"]["threads"]}
    seen = []
    for s in plan.stops:
        if s["thread"] not in seen: seen.append(s["thread"])
    for i, k in enumerate(seen, 1):
        t = names[k]; row = dE.get(k, {})
        threads.append(dict(index=i, hex=t["hex"].lower(), name=t.get("name", k), brand="Isacord", code=row.get("code"),
                            delta_e=row.get("dE"), design_hex=(row.get("fill") or "").lower() or None, weight=t.get("weight", "40wt")))
    res = dict(contract=CONTRACT, engine="svg2dst", engine_version=engine_version(), ok=all(x["pass"] for x in gates if x["hard"]),
               inputs=dict(width_mm=width, fabric=fabric, hoop=hoop, answers=answers),
               size_mm=dict(w=round(size[0], 1), h=round(size[1], 1)),
               stats=dict(stitches=rb["stitches"], trims=rb["trims"], colour_changes=max(0, rb["stops"] - 1), jumps=rb["jumps"],
                          machine_minutes=f["machine_min"] if f["machine_min"] is not None else 0.0, max_stitch_mm=rb["max_stitch"]),
               threads=threads, gates=gates,
               questions=[dict(id=q["id"], text=q["text"], options=q["options"], default=q["default"]) for q in qs],
               warnings=warnings,
               files=dict(dst=os.path.basename(r.base) + ".dst", pes=os.path.basename(r.base) + ".pes", preview="preview.png"),
               engine_detail=dict(scale=ninfo["scale"], art_mm=ninfo["art_mm"], layers=auto["report"]["layers"],
                                  patch=auto["report"]["patch"], parts=len(plan.parts), stops=len(plan.stops),
                                  techniques=sorted({TECHNIQUES.get(p.technique, p.technique) for p in plan.parts}),
                                  seconds=round(time.time() - t0, 1)))
    check_result(res)
    json.dump(res, open(os.path.join(a.out, "result.json"), "w"), indent=1, default=float)
    print(f"svg2dst: {rb['stitches']} stitches, {n_thr} threads, {rb['trims']} trims, ok={res['ok']}, "
          f"{len(res['questions'])} questions ({res['engine_detail']['seconds']} s)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--svg", required=True); ap.add_argument("--width-mm", required=True, type=float)
    ap.add_argument("--fabric", required=True); ap.add_argument("--hoop", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--answers"); ap.add_argument("--name", default="design")
    ap.add_argument("--no-api", action="store_true", help="accepted for parity; this path never calls an API")
    a = ap.parse_args(argv)
    print("[info] svg2dst makes no Anthropic API calls; --no-api accepted.")
    try:
        return run(a)
    except InputError as e:
        print(f"input refused: {e}", file=sys.stderr)
        try:
            os.makedirs(a.out, exist_ok=True); json.dump(dict(contract=CONTRACT, error=str(e)), open(os.path.join(a.out, "result.json"), "w"))
        except OSError: pass
        return 2
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
