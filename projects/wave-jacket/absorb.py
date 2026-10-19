"""Fold near-empty hoop sections into a neighbour (F1 review: M SL had a 128-stitch and a 3,389-stitch hooping).
A section holding < FRAC of the piece's art area moves into the other section that can take it: same colour + code + stitch
type pieces that touch are re-joined (no double-sewn overlap), and the merged section incl. its registration crosses must fit
frame - 2 x margin. Proposed for the engine as split_clip(absorb=...)."""
from shapely.geometry import Point
from shapely.ops import unary_union

FRAC = 0.04

def _fits(regs, pts, frame, margin):
    g = [r["geom"] for r in regs] + [Point(p).buffer(6.0) for p in pts]
    b = unary_union(g).bounds
    return b[2] - b[0] <= frame[0] - 2 * margin and b[3] - b[1] <= frame[1] - 2 * margin

def _merge(dst, src):
    out = [dict(r) for r in dst]
    for r in src:
        for o in out:
            if (o["col"], o["grp"], o["st"]) == (r["col"], r["grp"], r["st"]) and o["geom"].intersects(r["geom"]):
                o["geom"] = unary_union([o["geom"], r["geom"]]).buffer(0); break
        else: out.append(dict(r))
    return out

def absorb_tiny(secs, marks, keys, frame, margin=9.5, frac=FRAC):
    """returns (keys kept, log). secs / marks are edited in place."""
    log = []; total = sum(r["geom"].area for k in keys for r in secs[k])
    while True:
        live = [k for k in keys if secs[k]]
        small = sorted((sum(r["geom"].area for r in secs[k]), k) for k in live)
        done = True
        for a, k in small:
            if a >= frac * total or len(live) < 2: break
            for j in sorted((j for j in live if j != k), key=lambda j: -sum(r["geom"].area for r in secs[j])):
                cand = _merge(secs[j], secs[k])
                if _fits(cand, marks.get(j, []), frame, margin):
                    log.append(f"{k} ({a:.0f} mm2) -> {j}"); secs[j] = cand; secs[k] = []; marks.pop(k, None); done = False; break
            if not done: break
        if done: return [k for k in keys if secs[k]], log
