"""Thread planner (ENGINE_PLAN M1 v0, M4g planner): candidate tones -> at most `needles` threads (factory.json: 12).

  tp = threads.plan({"cf_navy": 755.6, "cf_red": 59.3, ...}, palette, needles=12, protected=["cf_red", "cf_gold"])
  tp["map"]["cf_lav"]  -> "cf_mist"      (merged into)
  tp["threads"]        -> {key: dict(hex, name, protected, weight_mm2, absorbed=[...])}
  tp["merges"]         -> [dict(src, dst, dE, cost, mix)] in the order they were made

Greedy, importance-weighted: while there are too many threads, merge the pair with the lowest
cost = CIEDE2000(a, b) x min(weight_a, weight_b): merging a rare tone into a close one is cheap, merging two big
different ones is expensive. The SMALLER weight is absorbed and the bigger keeps its own colour (a thread is a real
colour off a card, never an average). PROTECTED tones (run.yaml threads.protected: the founder's red and gold accents)
never merge, neither into another thread nor absorbing one: an accent that disappears at build time was the Rev B
colours failure (BENCH baseline: no red, no gold). Tones with zero weight are dropped first. Weight = covered area in
mm2 x IMPORTANCE (run.yaml threads.importance, default 1): a tone a motif depends on (the water blues of the falls,
M1 review: area weighting merged both blues away, small in area but the whole read of the water) gets a multiplier so
it is expensive to absorb, without the hard guarantee of `protected`.

M4g (DIGITIZING_PRINCIPLES rule 8: gradients from density, not threads; each thread serves several motifs):
  KEEP         keep=[tones]: never absorbed (it may absorb others, unlike a protected accent). The lever of a trade-off.
  SALIENCY     saliency={tone: x}: visual importance (threads.salience(): local contrast of the tone to what touches
               it x the number of motifs (zones) it serves), applied like importance. Off unless asked (run.yaml
               threads.saliency: true): the founder's call, offered as an alternative (below), not taken for him.
  MIX          every merge also records the best OPTICAL MIX of two kept threads for the absorbed tone (an open layer
               of b over a, ratio 1/4, 1/2, 3/4, mixed in linear RGB): `mix` = dict(a, b, ratio, dE). Reported (review
               question), not sewn: a mix is a second layer (rule 6 counts it), so it is the founder's call per motif.
  ALTERNATIVES alternatives(): for each visible merge (dE >= alt_min_dE) the plan that KEEPS that tone instead, and
               what it then merges; plus the saliency-weighted plan. plan_from_config() applies run.yaml
               threads.choice (an alternative's id; "default" = the plain plan) and records the trade-off for the
               review step (review.questions asks it; answers.json picks it in the next run)."""
import numpy as np


class ThreadError(ValueError):
    pass


def _lab(hexes):
    from digitize.extract.evidence import to_lab, hex_rgb
    return to_lab(np.array([[hex_rgb(h) for h in hexes]], float))[0]


def plan(weights, palette, needles=12, protected=(), names=None, importance=None, keep=(), saliency=None, mix=True):
    protected = [p for p in protected]; keep = [k for k in keep if k not in protected]
    imp = {k: float((importance or {}).get(k, 1.0)) * float((saliency or {}).get(k, 1.0)) for k in palette}
    for k, v in (importance or {}).items():
        if k not in palette: raise ThreadError(f"importance for {k!r}, which is not in the palette")
        if not v > 0: raise ThreadError(f"importance of {k!r} must be > 0, got {v!r}")
    for k, v in (saliency or {}).items():
        if k not in palette: raise ThreadError(f"saliency for {k!r}, which is not in the palette")
        if not v > 0: raise ThreadError(f"saliency of {k!r} must be > 0, got {v!r}")
    for p in protected:
        if p not in palette: raise ThreadError(f"protected tone {p!r} is not in the palette")
    for p in keep:
        if p not in palette: raise ThreadError(f"kept tone {p!r} is not in the palette")
    if len(protected) > needles: raise ThreadError(f"{len(protected)} protected tones > {needles} needles")
    if len(protected) + len(keep) > needles: raise ThreadError(f"{len(protected)} protected + {len(keep)} kept tones > {needles} needles")
    from digitize.extract.evidence import delta_e
    live = {k: float(weights.get(k, 0.0)) for k in palette if float(weights.get(k, 0.0)) > 0 or k in protected}
    mp = {k: k for k in palette}; merges = []; absorbed = {k: [] for k in palette}
    keys = list(live); lab = dict(zip(keys, _lab([palette[k] for k in keys]))) if keys else {}
    for k in palette:
        if k not in live: mp[k] = None                          # unused tone: no thread
    while len(live) > needles:
        best = None; ks = [k for k in live if k not in protected]
        if len(ks) < 2 and len(live) > needles:
            raise ThreadError(f"cannot get to {needles} threads: only protected tones left to merge")
        for i, a in enumerate(ks):
            for b in ks[i + 1:]:
                if a in keep and b in keep: continue
                dE = float(delta_e(lab[a][None], lab[b][None])[0]); cost = dE * min(live[a] * imp[a], live[b] * imp[b])
                if best is None or cost < best[0]: best = (cost, a, b, dE)
        if best is None: raise ThreadError(f"cannot get to {needles} threads: only protected / kept tones left to merge")
        cost, a, b, dE = best
        if a in keep: src, dst = b, a
        elif b in keep: src, dst = a, b
        else: src, dst = (a, b) if live[a] * imp[a] < live[b] * imp[b] else (b, a)
        live[dst] += live.pop(src); absorbed[dst] += [src] + absorbed.pop(src, [])
        for k, v in mp.items():
            if v == src: mp[k] = dst
        merges.append(dict(src=src, dst=dst, dE=round(dE, 1), cost=round(cost, 1)))
    if mix and merges:                       # accents stay accents: protected tones are not offered as mixing threads
        kept = [k for k in live if k not in protected]
        for m in merges: m["mix"] = optical_mix(palette[m["src"]], {k: palette[k] for k in kept})
    threads = {k: dict(hex=palette[k], name=(names or {}).get(k, k), protected=k in protected, weight_mm2=round(live[k], 1),
                       absorbed=absorbed.get(k, []), **({"importance": imp[k]} if imp[k] != 1.0 else {}),
                       **({"kept": True} if k in keep else {})) for k in live}
    return dict(map=mp, threads=threads, merges=merges, needles=needles)


# ------------------------------------------------------------------ optical mixing (rule 8)
def _lin(hex_):
    from digitize.extract.evidence import hex_rgb
    c = np.array(hex_rgb(hex_), float) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _to_lab_lin(lin):
    from digitize.extract.evidence import to_lab
    s = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.clip(lin, 0, 1), 1 / 2.4) - 0.055)
    return to_lab(np.array([[s * 255.0]], float))[0][0]


def optical_mix(src_hex, kept, ratios=(0.25, 0.5, 0.75)):
    """the closest two-thread optical mix to src among the kept threads: an open layer of b over a fill of a, b
    covering `ratio` of the area (mixed in linear RGB, which is what the eye averages at reading distance).
    Returns dict(a, b, ratio, dE) or None (fewer than two kept threads)."""
    from digitize.extract.evidence import delta_e
    ks = list(kept)
    if len(ks) < 2: return None
    L = {k: _lin(h) for k, h in kept.items()}; target = _lab([src_hex])[0]; best = None
    for i, a in enumerate(ks):
        for b in ks[i + 1:]:
            for r in ratios:
                lab = _to_lab_lin((1 - r) * L[a] + r * L[b]); d = float(delta_e(lab[None], target[None])[0])
                if best is None or d < best[3]: best = (a, b, r, d)
    a, b, r, d = best
    return dict(a=a, b=b, ratio=r, dE=round(d, 1))


# ------------------------------------------------------------------ visual importance
def salience(tone, keys, palette, ppm, zone_masks=None, contrast_ref=20.0, min_zone_mm2=20.0, motif_step=0.25):
    """visual importance per tone, from the evidence (tone index image): x = clip(C / contrast_ref, 0.5, 2) x
    (1 + motif_step x (motifs - 1)), C = the boundary-length-weighted mean CIEDE2000 between the tone and the tones
    its pixels touch (a small tone that stands out of its surroundings reads; one that blends into its neighbour does
    not), motifs = zones (zone_masks: {zone: bool mask}) where the tone covers >= min_zone_mm2 (rule 8: a thread that
    serves several motifs is worth a needle). Returns {tone: dict(x, contrast, motifs)}."""
    from digitize.extract.evidence import delta_e
    labs = _lab([palette[k] for k in keys]); n = len(keys)
    D = np.array([[float(delta_e(labs[i][None], labs[j][None])[0]) for j in range(n)] for i in range(n)])
    t = np.asarray(tone, int); acc = np.zeros(n); cnt = np.zeros(n)
    for a, b in ((t[:, :-1], t[:, 1:]), (t[:-1, :], t[1:, :])):
        diff = a != b; aa, bb = a[diff], b[diff]
        np.add.at(acc, aa, D[aa, bb]); np.add.at(cnt, aa, 1); np.add.at(acc, bb, D[aa, bb]); np.add.at(cnt, bb, 1)
    out = {}
    for i, k in enumerate(keys):
        C = acc[i] / cnt[i] if cnt[i] else 0.0
        motifs = sum(1 for m in (zone_masks or {}).values() if (t[m] == i).sum() / ppm ** 2 >= min_zone_mm2) if zone_masks else 1
        x = float(np.clip(C / contrast_ref, 0.5, 2.0)) * (1 + motif_step * (max(1, motifs) - 1))
        out[k] = dict(x=round(x, 3), contrast=round(float(C), 1), motifs=int(motifs))
    return out


# ------------------------------------------------------------------ alternatives / the trade-off
def _desc(tp, names):
    nm = lambda k: (names or {}).get(k, k)
    return [f"{nm(m['src'])} -> {nm(m['dst'])} (dE {m['dE']})" for m in tp["merges"]]


def alternatives(weights, palette, needles=12, protected=(), names=None, importance=None, sal=None, alt_min_dE=8.0, max_alts=4, max_dE=18.0):
    """the trade-off as options (the founder decides, LESSONS: thread choices are design decisions). Options:
      default            the plain plan (area x importance)
      keep_<tone>        for each VISIBLE merge of the default (dE >= alt_min_dE, most expensive first, at most max_alts):
                         the plan that keeps that tone, and what it merges instead
      saliency           area x importance x salience() (if sal given)
    Each: dict(id, label, keep, saliency, merges=[text], lost=[merges not in the default], worst_dE, cost, recommended):
    recommended = False when the option's worst merge is over max_dE (18: a different colour, not a shade; PR #8 review),
    shown to the founder as NOT RECOMMENDED but still offered."""
    base = plan(weights, palette, needles, protected, names, importance)
    def opt(id_, label, keep=(), saliency=None):
        tp = plan(weights, palette, needles, protected, names, importance, keep=keep, saliency=saliency)
        bm = {(m["src"], m["dst"]) for m in base["merges"]}
        lost = [m for m in tp["merges"] if (m["src"], m["dst"]) not in bm]
        worst = max([m["dE"] for m in tp["merges"]] or [0.0])
        return dict(id=id_, label=label, keep=list(keep), saliency=bool(saliency), merges=_desc(tp, names), recommended=worst <= max_dE,
                    lost=[f"{(names or {}).get(m['src'], m['src'])} -> {(names or {}).get(m['dst'], m['dst'])} (dE {m['dE']})" for m in lost],
                    worst_dE=max([m["dE"] for m in tp["merges"]] or [0.0]), cost=round(sum(m["cost"] for m in tp["merges"]), 1),
                    threads=sorted(tp["threads"]))
    out = [opt("default", "as planned (area x importance)")]
    vis = sorted([m for m in base["merges"] if m["dE"] >= alt_min_dE], key=lambda m: -m["cost"])[:max_alts]
    nm = lambda k: (names or {}).get(k, k)
    for m in vis:            # keep BOTH tones of a visible merge: what has to merge instead is the real trade-off
        try: out.append(opt(f"keep_{m['src']}", f"keep {nm(m['src'])} as its own thread (beside {nm(m['dst'])})", keep=[m["src"], m["dst"]]))
        except ThreadError: pass
    if sal:
        try: out.append(opt("saliency", "weighted by visual importance (contrast x motifs served)", saliency={k: v["x"] for k, v in sal.items()}))
        except ThreadError: pass
    return out


def plan_from_config(weights, T, needles, sal=None):
    """run.yaml `threads:` -> the plan + its trade-off record. T: protected, importance, names, palette, and (M4g)
    keep: [tones], saliency: true/false, choice: <alternative id> ("default"). Returns tp with tp["tradeoff"] =
    dict(choice, options, salience)."""
    pal = T["palette"]; names = T.get("names"); prot = T.get("protected", []); imp = T.get("importance")
    opts = alternatives(weights, pal, needles, prot, names, imp, sal=sal)
    choice = T.get("choice", "default") or "default"
    by = {o["id"]: o for o in opts}
    if choice not in by: raise ThreadError(f"threads.choice {choice!r} is not one of the planner's options {sorted(by)}")
    o = by[choice]
    keep = list(dict.fromkeys(list(T.get("keep", [])) + o["keep"]))
    use_sal = (o["saliency"] or bool(T.get("saliency"))) and sal
    tp = plan(weights, pal, needles, prot, names, imp, keep=keep, saliency={k: v["x"] for k, v in sal.items()} if use_sal else None)
    tp["tradeoff"] = dict(choice=choice, keep=keep, saliency=bool(use_sal), options=opts, salience=sal)
    return tp


def needles_used(threads):
    """physical threads = needles: a puff stop's key '<colour>+foam' (M6 isolate_foam, threads[k]["foam_of"]) is the
    SAME thread as its flat colour, reused on the same needle; it never counts twice against the needle limit"""
    from digitize.techniques.specialty import FOAM
    def base(k, v):
        if isinstance(v, dict) and v.get("foam_of"): return v["foam_of"]
        return k[:-len(FOAM)] if k.endswith(FOAM) else k
    return len({base(k, v) for k, v in threads.items()})
