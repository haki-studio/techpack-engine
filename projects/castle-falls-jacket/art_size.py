"""Per-size art for all five pieces (LESSONS A5 applied to every piece).
Each size: the size-M scene of each piece is graded (A 92 % / B 100 % / C 108 %) about a fixed anchor and shifted with that
size's pattern, then knocked out (z order) and clipped to THAT size's keep-outs (keepout.clip). Small whole motifs
(florets, petals, castle parts) that a keep-out would cut are dropped whole instead of being cut.
Anchors: body pieces scale about (CB/CF, hem-rib seam) — the art keeps its distance above the hem and stays centred on
CB / meets at CF; sleeves about the cuff-seam centre.
usage: python3 art_size.py XS S M ...   -> art_<size>.pkl {P: vis, "info": {...}} + out/art/<size>_<P>.png"""
import cfcore
import pickle, sys, os, time
from shapely import affinity
from shapely.ops import unary_union
import keepout as KO, scene as SC
import dst2
cfcore.patch_dst2()

def anchor(P, size):
    g, mt = KO.pieces(size)
    if P == "BK": return 0.0, mt["hem_b"]
    if P in ("FR", "FL"): return 0.0, mt["hem_f"]
    return 0.0, mt["Lu"]

def graded(items, P, size):
    s = cfcore.GRADE[size][1]; (ax, ay), (bx, by) = anchor(P, "M"), anchor(P, size)
    def T(g): return affinity.translate(affinity.scale(g, s, s, origin=(ax, ay)), bx - ax, by - ay)
    out = []
    for r in items:
        r2 = dict(r, geom=T(r["geom"]).buffer(0))
        if isinstance(r["ang"], tuple):
            px = ax + (r["ang"][1] - ax) * s + bx - ax; py = ay + (r["ang"][2] - ay) * s + by - ay
            r2["ang"] = (r["ang"][0], px, py)
        out.append(r2)
    return out

def build(size, pieces=None):
    res = {"info": dict(size=size, grade=cfcore.GRADE[size][0], scale=cfcore.GRADE[size][1])}
    old = pickle.load(open(f"art_{size}.pkl", "rb")) if pieces and os.path.exists(f"art_{size}.pkl") else {}
    for P in cfcore.PIECES:
        if pieces and P not in pieces:
            if P in old: res[P] = old[P]; res["info"][P] = old["info"].get(P)
            continue
        t0 = time.time()
        items = graded(pickle.load(open(f"scene_{P}.pkl", "rb"))["items"], P, size)
        clip = KO.clip(size, P).buffer(-0.4)            # 0.4 inside the keep-out: cleaning never crosses it
        units = {}
        for r in items:
            if r.get("unit"): units.setdefault(r["unit"], []).append(r)
        cb = clip.buffer(0.2); drop = set()
        for u, rs in units.items():
            ug = unary_union([r["geom"] for r in rs])
            if not cb.contains(ug): drop.add(u)
        kept = [r for r in items if r.get("unit") not in drop]
        vis = SC.visible(kept, clip)
        vis = dst2.clean_vis(vis)
        vis = [dict(r, geom=r["geom"].intersection(clip).buffer(0)) for r in vis]
        vis = [r for r in vis if not r["geom"].is_empty and r["geom"].area > 0.5]
        res[P] = vis
        u = dst2.bounds_of([r["geom"] for r in vis])
        res["info"][P] = dict(objects=len(vis), bbox=u, dropped_units=len(drop), secs=round(time.time() - t0))
        print(size, P, res["info"][P], flush=True)
    pickle.dump(res, open(f"art_{size}.pkl", "wb"))
    return res

def flat_png(size, res, ppm=1.6):
    import stitchrender as SR
    os.makedirs("out/art", exist_ok=True)
    for P in cfcore.PIECES:
        if P not in res: continue
        b = KO.panel(size, P).bounds; b = (b[0] - 5, b[1] - 5, b[2] + 5, b[3] + 5)
        im = SR.render(res[P], b, ppm, base=cfcore.FABRIC)
        from PIL import ImageDraw
        d = ImageDraw.Draw(im); T = lambda cs: [((x - b[0]) * ppm, (y - b[1]) * ppm) for x, y in cs]
        d.line(T(KO.panel(size, P).exterior.coords), fill=(200, 200, 200), width=2)
        d.line(T(KO.clip(size, P).exterior.coords), fill=(255, 80, 80), width=1)
        im.save(f"out/art/{size}_{P}.png")

if __name__ == "__main__":
    args = sys.argv[1:]; pcs = [a for a in args if a in cfcore.PIECES] or None
    for sz in [a for a in args if a in cfcore.SIZES] or cfcore.SIZES:
        flat_png(sz, build(sz, pcs))
