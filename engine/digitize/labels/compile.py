"""labels -> Parts (ENGINE_PLAN G1): the engine side of the labels contract. No subject code: every labelled part goes to
the recogniser of its PRIMITIVE (digitize/primitives), which reads only the pixels the part may claim.

  parts, log, questions = labels.compile.extract(ctx, ev, labels, answers=None)

1. resolve: each labelled part -> a zone-like claim (windows = hint polygons minus `except` windows, tones, z, rest),
   with its primitive / intent / angle / colour / confidence / params. Answers from the review step (review.labels:
   {part id: primitive | "drop"}) are applied first: an answered primitive replaces the label's; "drop" removes it.
2. claim: zones.claim_and_split claims pixels from the highest z down (the rest part last), exclusive, exactly like
   hand-authored zones (LESSONS A14: geometry from input pixels only). Hint seeds keep only the claim's components that
   reach a seed (1 mm): a window that also holds an unrelated blob of the same tone gives it back.
3. recognise: primitives.get(primitive)(ctx, lp, z, claim) -> (parts, used); pixels a recogniser does not use go back to
   the parts below (a stroke gives back blobs, a dot gives back big areas).
4. questions: every part with confidence < review_below (default 0.6), and every motif below it, becomes a review
   question (topic "label", stable id "label:<part id>"), options = [its primitive] + its alternatives + ["drop"], default
   = its primitive (what this run did); the labeller's own question text is shown. An answer changes the next run's
   compile (review.apply_answers -> cfg review.labels).
The extract log gets one row per labelled part (claimed / used mm2, parts made) and the unused share of each claim."""
from shapely.geometry import Polygon
from shapely.ops import unary_union
from digitize.labels import schema as LS


def resolve(labels, answers=None):
    """labels dict -> [resolved part dicts] (answers applied: {pid: primitive | 'drop'})"""
    answers = answers or {}; out = []
    win = {LS.part_id(m, p): [Polygon(w).buffer(0) for w in (p.get("hint") or {}).get("polygons", [])] for m, p in LS.iter_parts(labels)}
    for m, p in LS.iter_parts(labels):
        pid = LS.part_id(m, p); prim = p["primitive"]; a = answers.get(pid)
        if a == "drop": continue
        if a and a != prim:
            if a not in LS.PRIMITIVES: raise LS.LabelsError(f"answer for {pid}: {a!r} is not a primitive")
            prim = a
        dr = p.get("direction") or {}
        it = dr.get("intent", LS.PRIMITIVES[prim][0])
        if it not in LS.PRIMITIVES[prim]: it = LS.PRIMITIVES[prim][0]      # an answered primitive takes its default intent
        geoms = list(win[pid])
        for o in (p.get("hint") or {}).get("except", []) or []:
            cut = unary_union(win[o]); geoms = [g.difference(cut) for g in geoms if not g.difference(cut).is_empty]
        out.append(dict(pid=pid, motif=m["id"], what=p.get("what") or m.get("what", ""), primitive=prim, intent=it,
                        angle=dr.get("angle"), z=float(p["z"]), colour=p.get("colour", "auto"),
                        confidence=float(min(p["confidence"], m.get("confidence", 1.0))), params=dict(p.get("params") or {}),
                        tones=p.get("tones", "all"), rest=bool(p.get("rest")), geoms=geoms,
                        seeds=[tuple(s) for s in (p.get("hint") or {}).get("seeds", []) or []],
                        question=p.get("question"), alternatives=list(p.get("alternatives") or []),
                        answered=a if a else None, labelled_primitive=p["primitive"]))
    return out


def _seeded(ev, mask, seeds, reach_mm=1.0):
    """keep only the components of mask that reach a seed (within reach_mm)"""
    import numpy as np
    from scipy import ndimage as ndi
    if not seeds or not mask.any(): return mask
    lab, n = ndi.label(mask); keep = set()
    r = max(1, int(round(reach_mm * ev.ppm)))
    for x, y in seeds:
        px, py = ev.to_px(x, y); px, py = int(px), int(py)
        win = lab[max(0, py - r):py + r + 1, max(0, px - r):px + r + 1]
        keep |= set(int(v) for v in np.unique(win) if v > 0)
    return np.isin(lab, sorted(keep)) if keep else np.zeros_like(mask)


def extract(ctx, ev, labels, answers=None):
    """-> (parts, log, questions). ctx: splitters.Ctx; ev: the evidence; labels: a validated labels dict"""
    from digitize.extract import zones as ZN
    from digitize import primitives
    R = resolve(labels, answers)
    zs = dict(zones=[dict(id=r["pid"], tones=r["tones"], z=r["z"], geoms=r["geoms"], rest=r["rest"],
                          close_mm=r["params"].get("claim_close_mm"), _lp=r) for r in R])
    for z in zs["zones"]:
        if not z["close_mm"]: z.pop("close_mm")
        if not z["rest"]: z.pop("rest")

    def split(z, zz, m):
        lp = z["_lp"]; m = _seeded(ev, m, lp["seeds"])
        return primitives.get(lp["primitive"])(ctx, lp, zz, m)

    parts, log = ZN.claim_and_split(zs, ev, lambda z: float(z["z"]), split)
    for row in log:
        lp = next(r for r in R if r["pid"] == row["zone"])
        row.update(primitive=lp["primitive"], intent=lp["intent"], confidence=lp["confidence"],
                   unused_pct=round(100.0 * (1 - row["used_mm2"] / row["claimed_mm2"]), 1) if row["claimed_mm2"] else 0.0)
    return parts, log, questions(labels, R)


def questions(labels, R=None):
    """review questions for low-confidence labelled parts (topic 'label', stable ids)"""
    R = R if R is not None else resolve(labels)
    below = float(labels.get("review_below", LS.REVIEW_BELOW)); out = []
    for r in R:
        if r["confidence"] >= below: continue
        opts = [r["labelled_primitive"]] + [a for a in r["alternatives"] if a != r["labelled_primitive"]] + ["drop"]
        text = (f"Labelled part '{r['pid']}' ({r['what'] or 'no description'}) was read as a {r['labelled_primitive']} with "
                f"confidence {r['confidence']:.2f} (< {below}). " + (f"Labeller: {r['question']} " if r.get("question") else "") +
                "Keep it, sew it as another primitive, or leave it out?")
        out.append(dict(id=f"label:{r['pid']}", topic="label", text=text, part_ids=[], label=r["pid"], options=opts,
                        default=r["labelled_primitive"], effect="another primitive: the part is recognised and sewn as that primitive "
                        "in the next run; drop: not sewn (its pixels go to the parts below)"))
    return out
