"""Review step (ENGINE_PLAN M1, question step M4g): what a person (later: the PLM question step) looks at before anything is sewn.

  review.part_map(plan, bounds, path, ppm=4)    part_map.png: every part filled by KIND, outlined, labelled with its id
                                                 (big enough parts) and a direction tick at its declared angle
  review.questions(plan, issues, ...)           questions.json: [dict(id, text, part_ids, options, default)]
The default answer is what the engine did, so an unanswered run is reproducible; answers.json (M4g, below) overrides it."""
import json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

KIND_COL = {"sky_band": (120, 170, 230), "sky_blend": (170, 205, 245), "fall_cord": (235, 240, 250), "pool": (150, 225, 235),
            "zone_stub": (150, 150, 150)}


def _font(n):
    try: return ImageFont.load_default(size=n)
    except TypeError: return ImageFont.load_default()


def _col(p, threads):
    if p.kind == "zone_stub":                             # stubs: their thread colour, washed 45 % toward grey
        h = threads.get(p.thread, {}).get("hex", "#969696").lstrip("#"); c = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
        return tuple(int(v * 0.55 + 150 * 0.45) for v in c)
    if p.kind in ("stratum_band", "stratum_crack", "cloud_shade", "cloud_wisp"):   # M2 organic parts: their own thread colour
        h = threads.get(p.thread, {}).get("hex", "#969696").lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    if p.kind == "cloud_lobe": return (250, 250, 245) if p.meta.get("lobe", 0) % 2 == 0 else (225, 228, 240)
    if p.kind == "fall_cord": return (235, 240, 250) if p.meta.get("cord", 0) % 2 == 0 else (190, 210, 240)
    return KIND_COL.get(p.kind, (200, 200, 200))


def part_map(plan, bounds, path, ppm=4.0, label_mm2=60.0):
    x0, y0, x1, y1 = bounds; W, H = int(round((x1 - x0) * ppm)), int(round((y1 - y0) * ppm))
    im = Image.new("RGB", (W, H), (40, 44, 52)); d = ImageDraw.Draw(im); f = _font(11)
    T = lambda cs: [((x - x0) * ppm, (y - y0) * ppm) for x, y in cs]
    from digitize.techniques import polys
    for p in sorted(plan.parts, key=lambda p: p.z):
        c = _col(p, plan.threads)
        for q in polys(p.geom):                           # holes cut on a mask, so they never paint over other parts
            m = Image.new("L", (W, H), 0); dm = ImageDraw.Draw(m); dm.polygon(T(q.exterior.coords), fill=255)
            for r in q.interiors: dm.polygon(T(r.coords), fill=0)
            im.paste(c, mask=m); d.line(T(q.exterior.coords), fill=(30, 30, 30), width=1)
    for p in plan.parts:                                   # direction ticks + ids on the larger parts
        if p.area < label_mm2: continue
        pt = p.geom.representative_point(); cx, cy = (pt.x - x0) * ppm, (pt.y - y0) * ppm
        a = math.radians(p.dir.angle); L = 5 * ppm
        d.line([(cx - L * math.cos(a), cy - L * math.sin(a)), (cx + L * math.cos(a), cy + L * math.sin(a))], fill=(200, 30, 30), width=2)
        d.text((cx + 3, cy + 2), p.id.split(".")[-1], fill=(0, 0, 0), font=f)
    im.save(path); return path




# ================================================================== M4g: the question step (ENGINE_PLAN M4)
# questions.json -> a person (later: the PLM question flow) answers -> answers.json -> the NEXT run reads it:
#   answers override defaults; a question left unanswered keeps its default and is REPORTED; an answer to a question
#   this run does not ask is reported (the design changed); an answer that is not one of the question's options raises.
# Question ids are STABLE across runs (topic + what it is about, never a running number), so an answers file written
# against one run applies to the next. Each question carries `effect`: what its answer changes.
#
#   qs = review.questions(plan, issues)                         -> [dict(id, topic, text, part_ids, options, default, effect)]
#   cfg, rep = review.apply_answers(cfg, answers, qs)           -> cfg overrides + dict(answered, defaulted, unknown, pending)
#   review.apply_extract(cfg, parts) / review.apply_plan(cfg, plan)   the overrides, at the stage they belong to
ANGLE_OPTS = ["keep measured angle", "0 deg", "45 deg", "90 deg", "135 deg"]
LOW_CONFIDENCE = 0.5          # Part.meta["confidence"] below this asks (M3a / M3b splitters may set it, 0..1)


class AnswerError(ValueError):
    pass


def _slug(s):
    import re
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:48]


def questions(plan, issues, extract_log=None, gates=None, rb=None):
    """structured questions for the person who approves the run. Every question names the parts it is about, has a
    default (= what this run did) and a stable id. Topics: zone_stub (unresolved kinds: zones whose splitter is not
    built), direction (stub parts with almost no reference grain), confidence (parts a splitter was unsure of,
    meta["confidence"] < 0.5), type-follows-shape / house-min (technique check issues, rule 4 / rule 9),
    threads (protected accents, the needle trade-off with its alternatives and optical mixes), sequence (budget)."""
    Q = []
    def q(id_, topic, text, part_ids, options, default, effect, **kw):
        Q.append(dict(id=id_, topic=topic, text=text, part_ids=list(part_ids), options=list(options), default=default, effect=effect, **kw))
    stubs = {}
    for p in plan.parts:
        if p.kind == "zone_stub": stubs.setdefault(p.zone, []).append(p.id)
    for z, ids in sorted(stubs.items()):
        q(f"zone_stub:{z}", "zone_stub",
          f"Zone '{z}' is a STUB ({len(ids)} parts, tatami at the reference grain's mean angle per part): its kind is not "
          f"resolved yet (M3: buildings, trunks, crowns, florets). Accept the stub for this proof, or leave the zone out?", ids,
          ["accept stub", "leave out", "re-draw zone"], "accept stub",
          "leave out: the zone's parts are not sewn in the next run; re-draw zone: pending (a person edits the zones file)")
    low = {}
    for p in plan.parts:
        if p.kind == "zone_stub" and (p.meta.get("coherence") or 0) < 0.15: low.setdefault(p.zone, []).append(p.id)
    for z, ids in sorted(low.items()):
        q(f"direction:low_grain:{z}", "direction",
          f"{len(ids)} stub parts in zone '{z}' have almost no grain in the reference (coherence < 0.15): their angle is a "
          f"weak measurement. Keep the measured angle, or set one angle for all of them?", ids, ANGLE_OPTS, ANGLE_OPTS[0],
          "an angle: those parts are sewn at it (DirSpec source 'answer', audited from meta answer_angle)")
    conf = {}
    for p in plan.parts:
        c = p.meta.get("confidence")
        if c is not None and float(c) < LOW_CONFIDENCE: conf.setdefault((p.zone, p.kind), []).append(p.id)
    for (z, k), ids in sorted(conf.items()):
        q(f"confidence:{z}:{k}", "confidence",
          f"{len(ids)} {k} parts in zone '{z}' were found with low confidence (< {LOW_CONFIDENCE}). Keep them as found, or drop them?",
          ids, ["keep", "drop"], "keep", "drop: those parts are not sewn in the next run")
    by = {}
    for it in issues: by.setdefault((it["technique"], it["text"].split(" (")[0].split(":")[0], it.get("severity", "check")), []).append(it["part"])
    for (tech, text, sev), ids in sorted(by.items()):
        topic = "house-min" if sev == "report" else "type-follows-shape"
        q(f"{topic}:{tech}:{_slug(text)}", topic,
          f"{len(ids)} {tech} parts: {text} ({'rule 9, house minimum' if sev == 'report' else 'DIGITIZING_PRINCIPLES rule 4'}). "
          f"Keep {tech}, or change the stitch?", ids,
          ["keep"] + [t for t in ("satin", "tatami", "run", "bean") if t != tech and (rb is None or rb.enabled(t))] + ["drop"], "keep",
          "another technique: those parts use it in the next run (it must be enabled in run.yaml); drop: not sewn")
    for t, v in sorted(plan.threads.items()):
        if v.get("protected"):
            ids = [p.id for p in plan.parts if p.thread == t]
            q(f"threads.accent:{t}", "threads",
              f"Protected accent {v['name']} ({v['hex']}) is used by {len(ids)} parts and never merged. Confirm the thread "
              f"against the factory card?", ids, ["confirm", "pick another card colour"], "confirm",
              "pick another card colour: pending (a person edits the palette)")
    tr = plan.meta.get("thread_tradeoff")
    if tr and tr.get("options"):
        opts = tr["options"]; cur = tr.get("choice", "default"); names = {k: v.get("name", k) for k, v in plan.threads.items()}
        mixes = [m for m in plan.meta.get("thread_merges", []) if m.get("mix")]
        mixtxt = "; ".join(f"{m['src']} as {m['dst']} dE {m['dE']}, or an optical mix {int(100 * (1 - m['mix']['ratio']))}% "
                           f"{m['mix']['a']} + {int(100 * m['mix']['ratio'])}% {m['mix']['b']} dE {m['mix']['dE']}"
                           for m in mixes if m["mix"]["dE"] < m["dE"] - 2)
        lines = [f"[{o['id']}] {o['label']}{'' if o.get('recommended', True) else ' (NOT RECOMMENDED: worst dE ' + str(o['worst_dE']) + ')'}: merges {', '.join(o['merges']) or 'none'} (worst dE {o['worst_dE']})" for o in opts]
        q("threads.tradeoff", "threads",
          f"The needle limit ({len(plan.threads)} threads) forces merges. Which trade-off? " + " | ".join(lines) +
          (f". Optical mixes that read closer than the merge (an open layer, rule 8; not sewn unless chosen per motif): {mixtxt}" if mixtxt else ""),
          [], [o["id"] for o in opts], cur, "the option's plan is used in the next run (run.yaml threads.choice)",
          alternatives=opts)
    bud = (plan.meta.get("sequence") or {}).get("budget")
    if bud and not bud.get("ok", True):
        q("sequence.budget", "sequence", f"The plan has {bud['planned']} stitches, over the budget {bud['max']} (rule 6). "
          f"Accept, or reduce?", [], ["accept", "reduce"], "accept", "reduce: pending (a person picks what to simplify)")
    return Q


def load_answers(path):
    """answers.json: {"answers": {question id: option}} (or the bare mapping)"""
    d = json.load(open(path))
    return dict(d.get("answers", d))


def apply_answers(cfg, answers, qs):
    """answers (from load_answers) against the questions they answer (the previous run's questions.json) -> (cfg with
    the overrides, report). Overrides: threads.choice; review.drop_zones; review.angles {part: deg};
    review.technique {part: technique | "drop"}. Report: answered [(id, answer)], defaulted [(id, default)] (missing
    answers: the default is kept), unknown [ids] (answered, but no such question), pending [(id, answer)] (needs a
    person outside the engine, e.g. re-draw a zone)."""
    from digitize import config
    cfg = config.merge(cfg, {}); rv = cfg.setdefault("review", {})
    rv.setdefault("drop_zones", []); rv.setdefault("angles", {}); rv.setdefault("technique", {})
    byid = {x["id"]: x for x in qs}; rep = dict(answered=[], defaulted=[], unknown=sorted(set(answers) - set(byid)), pending=[])
    for qid, x in byid.items():
        if qid not in answers:
            rep["defaulted"].append((qid, x["default"])); continue
        a = answers[qid]
        if a not in x["options"]:
            raise AnswerError(f"answer {a!r} to {qid} is not one of its options {x['options']}")
        rep["answered"].append((qid, a))
        if a == x["default"]: continue
        t = x["topic"]
        if qid == "threads.tradeoff": cfg.setdefault("threads", {})["choice"] = a
        elif t == "zone_stub":
            if a == "leave out": rv["drop_zones"].append(qid.split(":", 1)[1])
            else: rep["pending"].append((qid, a))
        elif t == "direction":
            for pid in x["part_ids"]: rv["angles"][pid] = float(a.split()[0])
        elif t == "confidence":
            for pid in x["part_ids"]: rv["technique"][pid] = "drop"
        elif t in ("type-follows-shape", "house-min"):
            for pid in x["part_ids"]: rv["technique"][pid] = a
        else: rep["pending"].append((qid, a))
    return cfg, rep


def apply_extract(cfg, parts):
    """extract-stage overrides: parts of zones answered 'leave out' are not sewn. Returns (parts, dropped ids)."""
    dz = set((cfg.get("review") or {}).get("drop_zones", []))
    keep = [p for p in parts if p.zone not in dz]
    stale = sorted(dz - {p.zone for p in parts})
    if stale: (cfg.setdefault("_answers_report", {})).setdefault("stale", []).extend(f"zone:{z}" for z in stale)
    return keep, [p.id for p in parts if p.zone in dz]


def apply_plan(cfg, plan, rb):
    """plan-stage overrides, after the rulebook chose technique + direction: an answered angle (fixed rows, source
    'answer', meta answer_angle for the audit), an answered technique (must be enabled in the run: a toggle is a promise),
    'drop'. Part ids answered about that this run no longer has are STALE: returned and added to the answers report
    (cfg["_answers_report"]["stale"]), never silently skipped. Returns dict(angles, technique, dropped, stale)."""
    from digitize.schema import DirSpec
    rv = cfg.get("review") or {}; A = rv.get("angles", {}); Tq = rv.get("technique", {}); out = dict(angles=[], technique=[], dropped=[])
    keep = []
    for p in plan.parts:
        t = Tq.get(p.id)
        if t == "drop": out["dropped"].append(p.id); continue
        if t:
            if not rb.enabled(t): raise AnswerError(f"answer: part {p.id} -> technique {t!r}, which this run disables")
            p.technique = t; p.stitch = rb.stitch_spec(p.kind, t); out["technique"].append(p.id)
        if p.id in A:
            p.meta["answer_angle"] = float(A[p.id]); p.dir = DirSpec(float(A[p.id]), source="answer", note="review answer")
            for k in ("sep_deg", "band_offset_deg"): p.meta.pop(k, None)
            out["angles"].append(p.id)
        keep.append(p)
    plan.parts = keep
    have = {p.id for p in plan.parts} | set(out["dropped"])
    out["stale"] = sorted((set(A) | set(Tq)) - have)          # answered about parts this run does not have (ids changed)
    if out["stale"]: (cfg.setdefault("_answers_report", {})).setdefault("stale", []).extend(out["stale"])
    return out
