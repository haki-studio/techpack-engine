"""Fix round 4 (PR #27 review of b448e33, item 2, LESSONS A13 + A16): the loop texture ON the padded foam follows the
close-up's visible grain.

Before: FM-loop = scalloped contour rings (2.1 mm apart) round every foam region. In 4 mm tiles a scallop points every
which way, so the foam's visible top layer read CHAOTIC on the direction gate (BK 1,078 of 2,913 foam tiles) and, in the
live view, flat grey-white hatching with no cord or loop definition (review).
Now: where a founder close-up covers the crest and shows a clear grain (grainfield.py ang4 / coh4, the 4 mm field read
from input pixels), the texture is a set of CORD lines along that grain: streamlines of the field, seeded 2.1 mm apart
(the old ring spacing) and kept >= 1.6 mm apart, inside the foam inset 0.9 mm, clear of the C-curl lines; each sewn as
the same w3 run as the rings (a 0.44 mm double run). Where there is no clear grain the scalloped rings stay.
Angle source: the close-up grain (self-derived for the A16 foam row - reported as such on G8).
Idempotent: re-running restores the stashed rings first (D['_foamcord'][P]).
usage: ./py.sh foamcord.py [M]   (after grainfield.py, before build_size.py)"""
import wavecore as WC
import sys, pickle, json, math
import numpy as np
import shapely
from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from shapely.prepared import prep

SIZE = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "M"
SEED, MIN_GAP, STEP, MIN_LEN = 2.1, 1.6, 0.5, 4.0
W_MIN, COH_MIN = 0.6, 0.25

def polys(g):
    return [p for p in getattr(g, "geoms", [g]) if p.geom_type == "Polygon" and not p.is_empty]

class Field:
    def __init__(self, P):
        z = np.load(f"grain_{SIZE}_{P}.npz")
        self.a = np.radians(z["ang4"]); self.c = z["coh4"]; self.w = z["w"]
        self.x0, self.y0, self.s = float(z["x0"]), float(z["y0"]), float(z["step"])
    def at(self, x, y):
        i, j = int((y - self.y0) / self.s), int((x - self.x0) / self.s)
        if not (0 <= i < self.a.shape[0] and 0 <= j < self.a.shape[1]): return None
        if self.w[i, j] < W_MIN or self.c[i, j] < COH_MIN: return None
        return self.a[i, j]

def streamline(F, inside, occ, x, y):
    """trace both ways from (x, y) along the axial field; stops outside, where the grain is unclear, or near another cord"""
    out = []
    for sgn in (1, -1):
        pts = []; px, py = x, y; prev = None
        for _ in range(400):
            a = F.at(px, py)
            if a is None: break
            v = np.array([math.cos(a), math.sin(a)])
            if prev is None: v = v * sgn
            elif v @ prev < 0: v = -v
            nx, ny = px + STEP * v[0], py + STEP * v[1]
            if not inside.contains(Point(nx, ny)) or occ.near(nx, ny): break
            pts.append((nx, ny)); prev = v; px, py = nx, ny
        out.append(pts)
    return out[1][::-1] + [(x, y)] + out[0]

class Occ:
    def __init__(self): self.g = {}
    def key(self, x, y): return (int(x // MIN_GAP), int(y // MIN_GAP))
    def near(self, x, y):
        kx, ky = self.key(x, y)
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for (qx, qy) in self.g.get((kx + i, ky + j), ()):
                    if (qx - x) ** 2 + (qy - y) ** 2 < MIN_GAP ** 2: return True
        return False
    def add(self, pts):
        for x, y in pts[::2]: self.g.setdefault(self.key(x, y), []).append((x, y))

def run():
    D = pickle.load(open(f"art_{SIZE}.pkl", "rb")); stash = D.setdefault("_foamcord", {}); log = {}
    for P in WC.PIECES:
        rs = [r for r in D[P] if r.get("gen") != "grain cord"] + stash.get(P, [])        # restore the rings first
        F = Field(P)
        foam = [r for r in rs if r["grp"] == "FM" and r["st"] == "padded"]
        curls = unary_union([r["geom"] for r in rs if r["grp"] == "FM-curl"]).buffer(0.3)
        keep, removed, new = [], [], []
        by_unit = {}
        for r in foam: by_unit.setdefault(r.get("unit"), []).append(r["geom"])
        grain_zone = {}
        for u, gs in by_unit.items():
            inner = unary_union(gs).buffer(0).buffer(-0.9).difference(curls)
            if inner.is_empty: continue
            ok = []
            for p in polys(inner):
                b = p.bounds; xs = np.arange(b[0] + 0.5, b[2], 1.0); ys = np.arange(b[1] + 0.5, b[3], 1.0)
                pts = [(x, y) for y in ys for x in xs]
                if not pts: continue
                inn = shapely.contains_xy(p, np.array([q[0] for q in pts]), np.array([q[1] for q in pts]))
                cl = [F.at(x, y) is not None for (x, y), i_ in zip(pts, inn) if i_]
                if cl and np.mean(cl) >= 0.5: ok.append(p)              # the close-up shows a clear grain on most of it
            if not ok: continue
            zone = unary_union(ok); grain_zone[u] = zone; pz = prep(zone); occ = Occ()
            b = zone.bounds
            seeds = [(x, y) for y in np.arange(b[1] + SEED / 2, b[3], SEED) for x in np.arange(b[0] + SEED / 2, b[2], SEED)]
            for x, y in seeds:
                if not pz.contains(Point(x, y)) or F.at(x, y) is None or occ.near(x, y): continue
                ln = streamline(F, pz, occ, x, y)
                if len(ln) < 2: continue
                L = LineString(ln)
                if L.length < MIN_LEN: continue
                occ.add(ln)
                q = L.simplify(0.1).buffer(0.22, cap_style="round", join_style="round")
                for pq in polys(q.intersection(zone)):
                    if pq.area > 0.5:
                        new.append(dict(col="w3", geom=pq, st="run", ang=None, grp="FM-loop", z=3.5, unit=u, layer=WC.L_LOOP, gen="grain cord"))
        for r in rs:
            if r["grp"] == "FM-loop" and r.get("gen") != "grain cord" and r.get("unit") in grain_zone and r["geom"].representative_point().within(grain_zone[r["unit"]].buffer(0.5)):
                removed.append(r)
            else: keep.append(r)
        stash[P] = removed; D[P] = keep + new
        log[P] = dict(rings_replaced=len(removed), rings_kept=sum(1 for r in keep if r["grp"] == "FM-loop"), cords=len(new),
                      cord_length_m=round(sum(r["geom"].length / 2 for r in new) / 1000, 2),
                      grain_foam_mm2=round(sum(z.area for z in grain_zone.values())), foam_mm2=round(unary_union([r["geom"] for r in foam]).area))
        print(P, log[P], flush=True)
    pickle.dump(D, open(f"art_{SIZE}.pkl", "wb")); json.dump(log, open(f"foamcord_{SIZE}.json", "w"), indent=1)

if __name__ == "__main__":
    run()
