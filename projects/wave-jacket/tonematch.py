"""Seam TONE handover (REVIEW_OPEN 2 + 3, Rev B fix round 20 Oct 2026): a stripe must keep its thread across every seam it
crosses (armholes, side seams, shoulders, CF zip, sleeve underarm) and across the sleeve centre line (the sleeve is ONE piece:
its two halves come from two render views and must read as one continuous trace).

seamwarp.py already brings the stripes to the seam and lines their EDGES up; the two render views still disagree on the
TONE of the same stripe (continuity.py 'tone' 22-91 % per seam). Here, per seam, the LEADER side keeps its tones (body over
sleeve; on the CF zip, the underarm and the sleeve centre: the side with more stripe on the seam) and every FOLLOWER stripe
region that meets the leader's stripes on the seam takes the leader's thread (majority of its seam samples, >= 60 %).
Whole regions only (no tone step inside a stripe = no new cut line). A region is locked once it has led or followed, so the
first (more important) seam decides. Big follower regions mostly far from the seam (> 6,000 mm2 and < 40 % of the area
within 60 mm of it) are kept and reported, not recoloured (mockup fidelity of the panel wins over the seam there).
usage: ./py.sh tonematch.py [M]   (rewrites art_<size>.pkl, keeps art_<size>_pretone.pkl; prints + writes tonematch_<size>.json)"""
import wavecore as WC
import sys, json, pickle, shutil, os
import numpy as np
from shapely import STRtree
from shapely.geometry import Point
import wrap as WR

size = next((a for a in sys.argv[1:] if not a.startswith("-")), "M")
BLUES = ("b0", "b1", "b2", "b3", "b4", "b5")
ORDER = ["CF zip", "side L", "side R", "shoulder L", "shoulder R", "armhole back L", "armhole front L", "armhole back R",
         "armhole front R", "underarm L", "underarm R", "sleeve centre L", "sleeve centre R"]
DEPTHS = (1.0, 2.0, 3.0, 4.0)
BIG_MM2, NEAR_MM, NEAR_SHARE = 6000.0, 60.0, 0.40


SMALL_MM2, WV_SHARE = 150.0, 0.5


def band_clean(items, log_):
    """REVIEW_OPEN 5 (continuous twisted-cord bands): the tone trace cut every stripe into patches - 81 % of the WV regions
    are < 150 mm2 (render shading, not design). A small WV patch whose outline is >= 50 % shared with other WV regions
    joins the neighbour it shares the most outline with (smallest first, repeated), so each stripe is one continuous band
    whose rows follow it (cord_sections are computed along the merged band). Small patches mostly on bare fabric / foam
    (stripe tips, spray) keep their own shape."""
    wv = [r for r in items if r["grp"] == "WV"]; rest = [r for r in items if r["grp"] != "WV"]
    merged = 0
    while True:
        wv.sort(key=lambda r: r["geom"].area); tree = STRtree([r["geom"] for r in wv]); done = set(); moved = 0
        for i, r in enumerate(wv):
            if r["geom"].area >= SMALL_MM2: break
            if i in done: continue
            g = r["geom"]; per = g.length
            if per <= 0: continue
            best, bl, tot = None, 0.0, 0.0
            for j in tree.query(g.buffer(0.3)):
                if j == i or j in done: continue
                sh = g.boundary.intersection(wv[j]["geom"].buffer(0.3)).length; tot += sh
                if sh > bl: best, bl = j, sh
            if best is None or tot < WV_SHARE * per: continue
            t_ = wv[best]; t_["geom"] = t_["geom"].union(g.buffer(0.05)).buffer(0)
            done.add(i); moved += 1
        if not moved: break
        wv = [r for k, r in enumerate(wv) if k not in done]; merged += moved
    log_.append(merged)
    return rest + wv


FILL_GRPS = ("WV", "FM", "FM-sh", "FM-gr", "FM-in", "DR", "DR-b", "RP")
HOLE_MM2 = 150.0


def fill_holes(items):
    """REVIEW_OPEN 4 (foam continuous, hollows = thin ridges): when the grey hollow blobs became thin ridges and the trace's
    fragments were cleaned, small pockets inside the art were left with NOTHING in them - bare navy specks inside the curls
    and between stripe and crest (FL M: 2,821 pockets, 1,241 mm2). Every pocket < HOLE_MM2 that is enclosed by the art is
    given to the fill region it shares the most outline with (foam pockets become foam, stripe pockets stripe)."""
    from shapely.ops import unary_union
    from shapely.geometry import Polygon
    fills = [r for r in items if r["grp"] in FILL_GRPS]
    U = unary_union([r["geom"] for r in fills])
    holes = [Polygon(h) for g in getattr(U, "geoms", [U]) for h in g.interiors]
    holes = [h for h in holes if h.area < HOLE_MM2]
    tree = STRtree([r["geom"] for r in fills]); add = {}
    for h in holes:
        best, bl = None, 0.0
        for j in tree.query(h.buffer(0.3)):
            sh = h.boundary.intersection(fills[j]["geom"].buffer(0.3)).length
            if sh > bl: best, bl = j, sh
        if best is not None: add.setdefault(best, []).append(h.buffer(0.1))
    for j, hs in add.items():
        fills[j]["geom"] = unary_union([fills[j]["geom"]] + hs).buffer(0)
    return len(holes), round(sum(h.area for h in holes))


def d0_of(sm): return {"internal": 0.0, "zip": 15.0}.get(sm["kind"], WR.GAP)


class Tones:
    """top stripe region at a point of one piece side"""
    def __init__(self, items, side):
        self.items = [r for r in items if r["grp"] == "WV" and r["col"] in BLUES and r["geom"].intersects(side.region)]
        self.tree = STRtree([r["geom"] for r in self.items]); self.side = side

    def at(self, s, d):
        x, y = self.side.point(s, d); p = Point(x, y)
        if not self.side.region.buffer(0.01).contains(p): return None
        hit = [self.items[i] for i in self.tree.query(p) if self.items[i]["geom"].contains(p)]
        return max(hit, key=lambda r: r.get("layer", 0)) if hit else None

    def samples(self, n, d0):
        out = []
        for k in range(n):
            s = (k + 0.5) / n; got = None
            for d in DEPTHS:
                got = self.at(s, d0 + d)
                if got is not None: break
            out.append(got)
        return out


def run(size):
    src = f"art_{size}.pkl"; bak = f"art_{size}_pretone.pkl"
    if not os.path.exists(bak): shutil.copy(src, bak)
    D = pickle.load(open(bak, "rb"))                        # always start from the pre-tone art: the pass is repeatable
    locked = set(); log = []
    for P in WC.PIECES:
        n0 = sum(1 for r in D[P] if r["grp"] == "WV"); lg = []
        D[P] = band_clean(D[P], lg)
        nh, ah = fill_holes(D[P]); lg.append((nh, ah))
        print(f"{P}: stripe patches merged into their band {lg[0]} ({n0} -> {sum(1 for r in D[P] if r['grp'] == 'WV')} WV regions); bare pockets filled {lg[1][0]} ({lg[1][1]} mm2)", flush=True)
        log.append(dict(piece=P, band_clean_merged=lg[0], wv_before=n0, wv_after=sum(1 for r in D[P] if r["grp"] == "WV"), pockets_filled=lg[1][0], pockets_mm2=lg[1][1]))
    seams = {sm["name"]: sm for sm in WR.seams(size)}
    # Rev C (founder 21 Oct 'Do A'): the wrap seams are REDRAWN in a band (seamredraw.py); whole-region recolouring would
    # change stripes far from the seam, so with --no-recolour only the structure passes above run
    for name in ([] if "--no-recolour" in sys.argv else ORDER):
        sm = seams.get(name)
        if sm is None: continue
        A, B = WR.SeamSide(size, sm, "A"), WR.SeamSide(size, sm, "B"); d0 = d0_of(sm)
        n = int(round(max(A.L, B.L)))
        TA, TB = Tones(D[A.P], A), Tones(D[B.P], B)
        sa, sb = TA.samples(n, d0), TB.samples(n, d0)
        agree0 = _agree(sa, sb)                              # before any recolour (regions are mutated below)
        if name.startswith(("armhole", "side", "shoulder")): lead = "A"       # body leads (A = BK on sides/shoulders, body on armholes)
        else: lead = "A" if sum(x is not None for x in sa) >= sum(x is not None for x in sb) else "B"
        L, F = (sa, sb) if lead == "A" else (sb, sa)
        Fside = B if lead == "A" else A
        votes = {}
        for k, fr in enumerate(F):
            if fr is None: continue
            near = [L[j]["col"] for j in range(max(0, k - 3), min(n, k + 4)) if L[j] is not None]
            if not near: continue
            col = max(set(near), key=near.count)
            votes.setdefault(id(fr), [fr, []])[1].append(col)
        changed = kept = same = 0; rows = []
        for fr, cols in votes.values():
            best = max(set(cols), key=cols.count); share = cols.count(best) / len(cols)
            if id(fr) in locked or share < 0.6: continue
            if best == fr["col"]: same += 1; locked.add(id(fr)); continue
            a = fr["geom"].area
            near_a = fr["geom"].intersection(Fside.line.buffer(NEAR_MM)).area
            if a > BIG_MM2 and near_a / a < NEAR_SHARE:
                kept += 1; rows.append(dict(kept=True, area=round(a), near_share=round(near_a / a, 2), col=fr["col"], to=best)); continue
            rows.append(dict(area=round(a), col=fr["col"], to=best, samples=len(cols), share=round(share, 2)))
            fr["col"] = best; fr["tone_from"] = name; changed += 1; locked.add(id(fr))
        for r in L:
            if r is not None: locked.add(id(r))
        sa2, sb2 = TA.samples(n, d0), TB.samples(n, d0)
        agree1 = _agree(sa2, sb2)
        log.append(dict(seam=name, leader=(A.P if lead == "A" else B.P), follower=Fside.P, recoloured=changed, kept_big=kept,
                        already_same=same, tone_agree_before=agree0, tone_agree_after=agree1, rows=rows))
        print(f"{name:<16} lead {log[-1]['leader']} -> {Fside.P}: recoloured {changed}, kept (big) {kept}, same {same};"
              f" stripe tone agrees {agree0} -> {agree1} %", flush=True)
    pickle.dump(D, open(src, "wb"))
    json.dump(log, open(f"tonematch_{size}.json", "w"), indent=1)
    return log


def _agree(sa, sb):
    """share (%) of seam samples with a stripe on both sides (+/- 3 mm) whose thread is the same"""
    n = len(sa); tot = ok = 0
    for k in range(n):
        if sa[k] is None: continue
        near = [sb[j]["col"] for j in range(max(0, k - 3), min(n, k + 4)) if sb[j] is not None]
        if not near: continue
        tot += 1; ok += sa[k]["col"] in near
    return round(100.0 * ok / tot) if tot else None


if __name__ == "__main__":
    run(size)
