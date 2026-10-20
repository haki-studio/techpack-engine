"""Splitters (ENGINE_PLAN M1): a zone's claimed pixels -> PARTS with a kind, a thread and a declared direction.

  sky.split   luminance bands at 0 deg + two-colour blends between them; sewn first, cut under (playbook: sky)
  fall.split  traced silhouette -> 4-10 cords along the medial axis, alternating tones, split satin at 90 deg
  stub.split  zone_stub: one part per connected tone component >= 20 mm2 of the zone (smaller ones absorbed into the
              neighbour they share most border with), tatami at the FIELD-MEAN angle of the reference grain over the
              part. No blobs, no random angles. pools use the same partition at the rulebook's fixed 0 deg.

Every splitter has the signature split(ctx, zone, z, claim_mask) -> (parts, used_mask); ctx carries the evidence, the
tone -> thread map, the rulebook and the run config."""
import numpy as np
from scipy import ndimage as ndi


class Ctx:
    def __init__(self, ev, rb, cfg, tone_thread, protected):
        self.ev, self.rb, self.cfg = ev, rb, cfg
        self.protected = set(protected)
        keys = ev.keys
        self.threads = sorted({t for t in tone_thread.values() if t})
        ti = {t: i for i, t in enumerate(self.threads)}
        lut = np.array([ti[tone_thread[k]] if tone_thread.get(k) else -1 for k in keys], int)
        self.thread_lab = lut[ev.tone]                     # (H, W) index into self.threads
        self.n = 0

    def new_id(self, prefix):
        self.n += 1; return f"{prefix}.{self.n:03d}"

    def disk(self, mm):
        r = max(1, int(round(mm * self.ev.ppm / 2))); y, x = np.ogrid[-r:r + 1, -r:r + 1]; return x * x + y * y <= r * r

    def mm2(self, mask): return float(mask.sum()) / self.ev.ppm ** 2


def dominant(ctx, mask):
    """thread with the most pixels in mask (None when empty)"""
    v = ctx.thread_lab[mask]; v = v[v >= 0]
    if not len(v): return None
    return ctx.threads[int(np.bincount(v).argmax())]


def partition(ctx, claim, min_mm2, min_protected_mm2, min_keep_mm2=1.0):
    """connected components of (claim AND thread) -> final component masks. Components under min_mm2 (protected threads:
    min_protected_mm2) are absorbed into the neighbouring component sharing the longest border, smallest first; a small
    component with no neighbour in the claim is kept when >= min_keep_mm2, else dropped. Returns [(thread, mask)]."""
    lab = np.where(claim, ctx.thread_lab, -1); comp = np.zeros(lab.shape, np.int32); thr = [None]; k = 0
    for t in range(len(ctx.threads)):
        l, n = ndi.label(lab == t)
        if n:
            comp[l > 0] = l[l > 0] + k; thr += [ctx.threads[t]] * n; k += n
    if k == 0: return []
    sizes = np.bincount(comp.ravel(), minlength=k + 1).astype(float) / ctx.ev.ppm ** 2
    parent = np.arange(k + 1)
    def root(i):
        while parent[i] != i: parent[i] = parent[parent[i]]; i = parent[i]
        return i
    lim = lambda i: min_protected_mm2 if thr[i] in ctx.protected else min_mm2
    small = sorted([i for i in range(1, k + 1) if sizes[i] < lim(i)], key=lambda i: sizes[i])
    sl = ndi.find_objects(comp); st = np.ones((3, 3), bool)
    for i in small:
        if sizes[root(i)] >= lim(root(i)) and root(i) != i: continue
        s = sl[i - 1]
        if s is None: continue
        s2 = tuple(slice(max(0, a.start - 1), a.stop + 1) for a in s)
        sub = comp[s2]; rs = np.vectorize(root)(sub) if sub.size else sub
        me = rs == root(i)
        ring = ndi.binary_dilation(me, st) & ~me & (sub > 0)
        if not ring.any():
            if sizes[root(i)] < min_keep_mm2: parent[root(i)] = 0
            continue
        nb = np.bincount(rs[ring].ravel(), minlength=k + 1); nb[0] = 0; nb[root(i)] = 0
        if nb.max() == 0: continue
        j = int(nb.argmax()); ri = root(i)
        parent[ri] = j; sizes[j] += sizes[ri]
    roots = np.array([root(i) for i in range(k + 1)]); final = roots[comp]
    out = []
    for r in np.unique(final):
        if r == 0: continue
        out.append((thr[r], final == r))
    return out
