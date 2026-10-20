"""Thread planner v0 (ENGINE_PLAN M1): candidate tones -> at most `needles` threads (factory.json: 12 per file).

  tp = threads.plan({"cf_navy": 755.6, "cf_red": 59.3, ...}, palette, needles=12, protected=["cf_red", "cf_gold"])
  tp["map"]["cf_lav"]  -> "cf_mist"      (merged into)
  tp["threads"]        -> {key: dict(hex, name, protected, weight_mm2, absorbed=[...])}
  tp["merges"]         -> [dict(src, dst, dE, cost)] in the order they were made

Greedy, importance-weighted: while there are too many threads, merge the pair with the lowest
cost = CIEDE2000(a, b) x min(weight_a, weight_b): merging a rare tone into a close one is cheap, merging two big
different ones is expensive. The SMALLER weight is absorbed and the bigger keeps its own colour (a thread is a real
colour off a card, never an average). PROTECTED tones (run.yaml threads.protected: the founder's red and gold accents)
never merge, neither into another thread nor absorbing one: an accent that disappears at build time was the Rev B
colours failure (BENCH baseline: no red, no gold). Tones with zero weight are dropped first. Weight = covered area in
mm2 (M4 adds importance: motif saliency, accents, optical mixing)."""
import numpy as np


class ThreadError(ValueError):
    pass


def _lab(hexes):
    from digitize.extract.evidence import to_lab, hex_rgb
    return to_lab(np.array([[hex_rgb(h) for h in hexes]], float))[0]


def plan(weights, palette, needles=12, protected=(), names=None):
    protected = [p for p in protected]
    for p in protected:
        if p not in palette: raise ThreadError(f"protected tone {p!r} is not in the palette")
    if len(protected) > needles: raise ThreadError(f"{len(protected)} protected tones > {needles} needles")
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
                dE = float(delta_e(lab[a][None], lab[b][None])[0]); cost = dE * min(live[a], live[b])
                if best is None or cost < best[0]: best = (cost, a, b, dE)
        cost, a, b, dE = best
        src, dst = (a, b) if live[a] < live[b] else (b, a)
        live[dst] += live.pop(src); absorbed[dst] += [src] + absorbed.pop(src, [])
        for k, v in mp.items():
            if v == src: mp[k] = dst
        merges.append(dict(src=src, dst=dst, dE=round(dE, 1), cost=round(cost, 1)))
    threads = {k: dict(hex=palette[k], name=(names or {}).get(k, k), protected=k in protected, weight_mm2=round(live[k], 1),
                       absorbed=absorbed.get(k, [])) for k in live}
    return dict(map=mp, threads=threads, merges=merges, needles=needles)
