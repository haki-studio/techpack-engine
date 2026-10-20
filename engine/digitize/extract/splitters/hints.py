"""Sequencing hints that name other parts (ENGINE_PLAN M3b; the M4g hint contract): `knockout_of` = the fill a detail is
knocked out of. A splitter sets it at extraction, but the named fill can disappear before sequencing: merge_specks folds
a small part into its neighbour, absorb_fragments drops one with nothing left. M4g's sequencer raises on a hint that
names no part (PR #10 review: `knockout_of 'foliage.172' names no part`), so after every step that removes parts the
hints are repaired here:

  changes = hints.repoint(parts, merged=[(speck id, into id), ...])
    a target that was MERGED is re-pointed along the merge chain to the part that now holds its pixels;
    a target that is simply GONE (dropped) is removed from the hint;
    returns [(part id, key, old target, new target or None)] for the plan's meta (logged, never silent).

  hints.dangling(parts) -> [(part id, key, target)]   every hint that names no part (a test / gate helper)"""

KEYS = ("knockout_of",)


def _ids(v):
    if v is None: return []
    return list(v) if isinstance(v, (list, tuple)) else [v]


def repoint(parts, merged=()):
    alive = {p.id for p in parts}
    into = {a: b for a, b in merged}
    def follow(t):
        seen = set()
        while t not in alive and t in into and t not in seen:
            seen.add(t); t = into[t]
        return t if t in alive else None
    changes = []
    for p in parts:
        for key in KEYS:
            if key not in p.meta: continue
            old = _ids(p.meta[key]); new = []
            for t in old:
                n = t if t in alive else follow(t)
                if n != t: changes.append((p.id, key, t, n))
                if n is not None and n != p.id and n not in new: new.append(n)
            if not new: p.meta.pop(key)
            else: p.meta[key] = new[0] if not isinstance(p.meta[key], (list, tuple)) and len(new) == 1 else new
    return changes


def dangling(parts):
    alive = {p.id for p in parts}
    return [(p.id, key, t) for p in parts for key in KEYS for t in _ids(p.meta.get(key)) if t not in alive]
