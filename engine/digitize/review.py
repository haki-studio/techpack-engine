"""Review step (ENGINE_PLAN M1): what a person (later: the PLM question step) looks at before anything is sewn.

  review.part_map(plan, bounds, path, ppm=4)    part_map.png: every part filled by KIND, outlined, labelled with its id
                                                 (big enough parts) and a direction tick at its declared angle
  review.questions(plan, issues, ...)           questions.json: [dict(id, text, part_ids, options, default)]
The default answer is what the engine did, so an unanswered run is reproducible; answers.json (M4) overrides it."""
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


def questions(plan, issues, extract_log=None, gates=None):
    """structured questions for the person who approves the run. Every question names the parts it is about and has
    a default (= what this run did)."""
    Q = []; n = [0]
    def q(text, part_ids, options, default, **kw):
        n[0] += 1; Q.append(dict(id=f"q{n[0]:03d}", text=text, part_ids=list(part_ids), options=options, default=default, **kw))
    stubs = {}
    for p in plan.parts:
        if p.kind == "zone_stub": stubs.setdefault(p.zone, []).append(p.id)
    for z, ids in sorted(stubs.items()):
        q(f"Zone '{z}' is a STUB ({len(ids)} parts, tatami at the reference grain's mean angle per part). Its real splitter "
          f"comes in M2/M3. Accept the stub for this proof, or leave the zone out?", ids,
          ["accept stub", "leave out", "re-draw zone"], "accept stub", topic="zone_stub")
    low = [p.id for p in plan.parts if p.kind == "zone_stub" and (p.meta.get("coherence") or 0) < 0.15]
    if low:
        q(f"{len(low)} stub parts have almost no grain in the reference (coherence < 0.15): their angle is a weak "
          f"measurement. Keep the measured angle, or set one angle for all of them?", low,
          ["keep measured angle", "0 deg", "45 deg", "90 deg", "135 deg"], "keep measured angle", topic="direction")
    by = {}
    for it in issues: by.setdefault((it["technique"], it["text"].split(" (")[0].split(":")[0]), []).append(it["part"])
    for (tech, text), ids in sorted(by.items()):
        q(f"{len(ids)} {tech} parts: {text} (DIGITIZING_PRINCIPLES rule 4). Keep {tech}, or change the stitch?", ids,
          ["keep", "satin", "run", "bean", "drop"], "keep", topic="type-follows-shape")
    for t, v in sorted(plan.threads.items()):
        if v.get("protected"):
            ids = [p.id for p in plan.parts if p.thread == t]
            q(f"Protected accent {v['name']} ({v['hex']}) is used by {len(ids)} parts and never merged. Confirm the thread "
              f"against the factory card?", ids, ["confirm", "pick another card colour"], "confirm", topic="threads")
    merged = [(t, v["absorbed"]) for t, v in plan.threads.items() if v.get("absorbed")]
    if merged:
        q("Tones merged to fit the needle limit: " + "; ".join(f"{', '.join(a)} -> {t}" for t, a in merged) + ". Accept?",
          [], ["accept", "change"], "accept", topic="threads")
    return Q
