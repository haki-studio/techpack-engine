"""parts.labels.json: the LABELS CONTRACT between the vision step and the engine (ENGINE_PLAN G1, RE-PLAN 2026-10-20).

The vision step (today: the Claude Code session looking at the mockup sheet, digitize.labels.sheet; later the PLM call, with
--no-api mocks) writes WHAT is on the garment, as motifs made of generic PARTS. It never writes stitches, and it never
draws geometry: a part's outline is traced from the input pixels inside its hint (LESSONS A14), exactly like a zone.

  {"schema": "techpack.labels/1",
   "source": {"view": "B", "crop": [x0, y0, x1, y1], "by": "session <sid> | api <model> | person", "date": "YYYY-MM-DD",
              "image": "what was looked at (the bench reference, the mockup)"},
   "review_below": 0.6,                       # optional: parts with confidence < this become review questions
   "motifs": [
     {"id": "fall_left", "what": "the big left waterfall", "confidence": 0.9,
      "parts": [
        {"id": "water",                       # unique inside the motif; the part id is "<motif>.<part>"
         "primitive": "cord",                 # one of PRIMITIVES (below)
         "hint": {"polygons": [[[x, y], ...]], "seeds": [[x, y]], "except": ["<motif>.<part>"]},
                                              # garment mm. polygons = WINDOWS (required unless "rest"); seeds = optional
                                              # points the part's pixels must connect to (components without a seed are
                                              # given back); except = other parts' windows cut out of this one
                                              # "each": true (G3) = every window is its OWN piece, listed back
                                              # to front (one window per petal / panel): pieces claim front first,
                                              # sew back first, each takes its own direction; one question / answer
         "tones": ["cf_white", "cf_cream"] | "all",   # palette tones that belong to the part (evidence classes)
         "z": 3.0,                            # sew depth: lower sews first; claims run from the highest z down
         "direction": {"intent": "along"},    # see INTENTS: never "auto" (DIGITIZING_PRINCIPLES rule 2)
         "colour": "auto" | "<palette key>",  # auto = from the pixels (dominant / per-piece); a key forces one thread
         "confidence": 0.85,                  # 0..1: how sure the labeller is of THIS part (primitive + extent)
         "question": "optional: what the labeller is unsure about",
         "alternatives": ["lobe"],            # optional: other primitives the review question offers
         "params": {...},                     # optional, primitive-specific numbers (see digitize/primitives/*)
         "rest": false,                       # true: takes every pixel nobody else claimed (one per file)
         "reference": {...}}                  # optional (G3): this part is graded as its own unit (below)
      ],
      "reference": {"image": "refs/x.png", "box": [x0, y0, x1, y1]}}]}
                                              # optional (G3): the picture motif_match grades this motif against
                                              # instead of the mockup crop (default = the mockup). image: a path
                                              # relative to the labels file (opaque / non-background pixels = the
                                              # motif); box: where it sits, garment mm. Grading only: it never
                                              # changes what is extracted (digitize.labels.refgrade).

PRIMITIVES and the direction intents each accepts (first = default when "direction" is omitted):
  stroke  1-7 mm strokes (lettering, stems, fins, rails)    across            satin column across the stroke
  cord    falls, trunks, vines, bodies lengthwise          along             split satin along the medial axis
  band    sky, strata, far roofs, stripes                   along | angle | grain   tatami / guided fill along the band
  lobe    clouds, leaves, petals, crowns, bodies            outline | grain | angle  one part per lobe
  plane   walls, roofs, flat graphic areas                  angle             tatami at one deliberate angle
  radial  florets, fins, tails, rays                         radial            radial satin from each centre
  dot     eyes, studs, stars, beads                          none              bead
  line    outlines, cracks, tile lines                       along             run / bean along the traced line

Intents: along (the part's own axis: a constructed angle, independent of the grain), across (across the stroke,
constructed), angle (the labeller's deliberate angle, "angle": deg, audited from meta label_angle), grain (guided fill
along the reference grain: SELF-DERIVED, A24), outline (the lobe's own long axis: "outline" bucket), radial (from each
centre), none (beads)."""
import json, math

SCHEMA = "techpack.labels/1"
PRIMITIVES = {
    "stroke": ("across",),
    "cord": ("along",),
    "band": ("along", "angle", "grain"),
    "lobe": ("outline", "grain", "angle"),
    "plane": ("angle",),
    "radial": ("radial",),
    "dot": ("none",),
    "line": ("along",),
}
INTENTS = ("along", "across", "angle", "grain", "outline", "radial", "none")
PART_KEYS = {"id", "primitive", "hint", "tones", "z", "direction", "colour", "confidence", "question", "alternatives", "params",
             "rest", "what", "reference"}
REFERENCE_KEYS = {"image", "box"}
REVIEW_BELOW = 0.6


class LabelsError(ValueError):
    pass


def load(path, palette=None):
    d = json.load(open(path))
    validate(d, palette)
    return d


def iter_parts(d):
    for m in d.get("motifs", []):
        for p in m.get("parts", []):
            yield m, p


def part_id(m, p):
    return f"{m['id']}.{p['id']}"


def intent_of(p):
    d = p.get("direction") or {}
    return d.get("intent") or PRIMITIVES[p["primitive"]][0]


def _reference_errs(where, r):
    """problems with a motif / part `reference` (G3)"""
    if not isinstance(r, dict): return [f"{where}: reference must be an object {{image, box}}"]
    errs = []
    extra = set(r) - REFERENCE_KEYS
    if extra: errs.append(f"{where}: reference has unknown keys {sorted(extra)} (have {sorted(REFERENCE_KEYS)})")
    if not isinstance(r.get("image"), str) or not r.get("image"): errs.append(f"{where}: reference.image (a picture path) required")
    b = r.get("box")
    if not (isinstance(b, (list, tuple)) and len(b) == 4 and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                                                                 and math.isfinite(v) for v in b) and b[2] > b[0] and b[3] > b[1]):
        errs.append(f"{where}: reference.box must be [x0, y0, x1, y1] garment mm with x1 > x0, y1 > y0, got {b!r}")
    return errs


def validate(d, palette=None):
    """raise LabelsError naming every problem (all at once, so one look at the file fixes them all)"""
    errs = []
    if d.get("schema") != SCHEMA: errs.append(f"schema must be {SCHEMA!r}, got {d.get('schema')!r}")
    if not isinstance(d.get("motifs"), list) or not d["motifs"]: errs.append("motifs: a non-empty list is required")
    seen, rest = set(), []
    ids = {part_id(m, p) for m, p in iter_parts(d) if isinstance(m, dict) and isinstance(p, dict) and "id" in m and "id" in p}
    for m in d.get("motifs", []) or []:
        if not m.get("id"): errs.append("a motif without an id"); continue
        c = m.get("confidence", 1.0)
        if not isinstance(c, (int, float)) or not 0 <= c <= 1: errs.append(f"motif {m['id']}: confidence {c!r} not in 0..1")
        if not m.get("parts"): errs.append(f"motif {m['id']}: no parts")
        if "reference" in m: errs += _reference_errs(f"motif {m['id']}", m["reference"])
        for p in m.get("parts", []) or []:
            pid = part_id(m, p) if p.get("id") else f"{m['id']}.<no id>"
            if not p.get("id"): errs.append(f"{pid}: part without an id"); continue
            if pid in seen: errs.append(f"{pid}: duplicate part id")
            seen.add(pid)
            extra = set(p) - PART_KEYS
            if extra: errs.append(f"{pid}: unknown keys {sorted(extra)} (have {sorted(PART_KEYS)})")
            prim = p.get("primitive")
            if prim not in PRIMITIVES: errs.append(f"{pid}: primitive {prim!r} not in {sorted(PRIMITIVES)}"); continue
            dr = p.get("direction") or {}
            it = dr.get("intent", PRIMITIVES[prim][0])
            if it == "auto" or it not in INTENTS:
                errs.append(f"{pid}: direction intent {it!r} is not a declared intent {INTENTS} (never 'auto', rule 2)")
            elif it not in PRIMITIVES[prim]:
                errs.append(f"{pid}: a {prim} takes direction {PRIMITIVES[prim]}, not {it!r}")
            if it == "angle":
                a = dr.get("angle")
                if not isinstance(a, (int, float)) or isinstance(a, bool) or not math.isfinite(a):
                    errs.append(f"{pid}: intent 'angle' needs a number 'angle' (deg), got {a!r}")
            z = p.get("z")
            if not isinstance(z, (int, float)) or isinstance(z, bool): errs.append(f"{pid}: z must be a number, got {z!r}")
            c = p.get("confidence")
            if not isinstance(c, (int, float)) or isinstance(c, bool) or not 0 <= c <= 1:
                errs.append(f"{pid}: confidence must be a number in 0..1, got {c!r}")
            h = p.get("hint") or {}
            if p.get("rest"): rest.append(pid)
            else:
                pols = h.get("polygons") or []
                if not pols: errs.append(f"{pid}: hint.polygons (garment mm windows) required unless rest: true")
                for w in pols:
                    if not isinstance(w, list) or len(w) < 3 or not all(isinstance(q, (list, tuple)) and len(q) == 2 for q in w):
                        errs.append(f"{pid}: a hint polygon needs >= 3 [x, y] points")
            if "each" in h:
                if not isinstance(h["each"], bool): errs.append(f"{pid}: hint.each must be true or false, got {h['each']!r}")
                elif h["each"] and len(h.get("polygons") or []) < 2: errs.append(f"{pid}: hint.each needs >= 2 windows (one per piece)")
            if "reference" in p: errs += _reference_errs(pid, p["reference"])
            for o in h.get("except", []) or []:
                if o not in ids: errs.append(f"{pid}: hint.except names unknown part {o!r}")
            for s in h.get("seeds", []) or []:
                if not isinstance(s, (list, tuple)) or len(s) != 2: errs.append(f"{pid}: a seed is [x, y]")
            t = p.get("tones", "all")
            if t != "all":
                if not isinstance(t, list) or not t: errs.append(f"{pid}: tones must be 'all' or a non-empty list")
                elif palette is not None:
                    bad = [k for k in t if k not in palette]
                    if bad: errs.append(f"{pid}: tones {bad} are not in the run palette")
            col = p.get("colour", "auto")
            if col != "auto" and palette is not None and col not in palette:
                errs.append(f"{pid}: colour {col!r} is not 'auto' or a palette key")
            for a in p.get("alternatives", []) or []:
                if a not in PRIMITIVES: errs.append(f"{pid}: alternative {a!r} is not a primitive")
    if len(rest) > 1: errs.append(f"more than one rest part: {rest}")
    if errs: raise LabelsError("parts.labels.json:\n  " + "\n  ".join(errs))
    return d
