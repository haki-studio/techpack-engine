"""Per-size art for the four stitch pieces (FR, FL fronts; SR, SL sleeves).
Badges: each badge keeps its shape; its anchor moves with the size's panel (x * chest ratio, y * front-length ratio) and
it is drawn at the grade scale (A 92 % / B 100 % / C 106 %) about that anchor. If a badge would cross a keep-out on a
size, the smallest move (<= 20 mm) that clears every keep-out is applied and recorded (LESSONS C5 nudge solver).
Star speckles: positions follow the panel (front: chest/length ratio; sleeve: width/length ratio), the star size is
constant; a star that would cross a keep-out or touch a badge is dropped whole.
usage: python3 art_size.py XS S M ...   -> art_<size>.pkl + out/art/<size>_flat.png"""
import kccore
import pickle, sys, os, math, json, time
import numpy as np
import shapely
from shapely.geometry import Point, LineString, box, Polygon
from shapely.ops import unary_union
from shapely import affinity
import front as F, sleeve as SV, drum, dst2
import kcsatin as KS
kccore.patch_dst2()

SC = pickle.load(open("scene.pkl", "rb")); ITEMS = SC["items"]; META = SC["meta"]
BM = drum.Block("M")

def visible(items, clip):
    """z-ordered knockout inside clip. Higher z covers lower (cut kob mm around it); regions of the same unit knock out
    exactly (strokes of one glyph tile, they must not get gaps); nok regions (sheer glow, sewn first) are never cut."""
    its = [r for r in items if r["geom"].intersects(clip)]
    its.sort(key=lambda r: -r["z"])
    geoms = [r["geom"] for r in its]
    cover = [r["geom"].buffer(r["kob"]) if r.get("kob") else r["geom"] for r in its]
    tree = shapely.STRtree(cover)
    out = []
    for i, r in enumerate(its):
        g = r["geom"].intersection(clip)
        if g.is_empty: continue
        if not r.get("nok"):
            hits = [int(j) for j in tree.query(g) if int(j) < i and its[int(j)].get("ko", True)]
            if hits:
                u = r.get("unit")
                g = g.difference(unary_union([geoms[j] if (u and its[j].get("unit") == u) else cover[j] for j in hits]))
        g = g.buffer(0)
        if not g.is_empty and g.area > 0.05: out.append(dict(r, geom=g))
    out.reverse()
    return out

def badge_of(r):
    u = r.get("unit") or ""; el = r["el"]
    return el if el in ("01", "02", "03", "04") else None

def place_front(size, P):
    grade, s = kccore.GRADE[size]; b = drum.Block(size)
    kx, ky = b.chest2 / BM.chest2, b.f_hem / BM.f_hem
    side = "R" if P == "FR" else "L"
    clip = F.clip_for(size, side).buffer(-0.4)
    its = ITEMS[P]; out = []; moves = {}
    for el in sorted({r["el"] for r in its if badge_of(r)}):
        rs = [r for r in its if r["el"] == el and not (r.get("unit") or "").startswith("05")]
        ax, ay = META["badges"][el]["centre"]
        tx, ty = ax*kx, ay*ky
        def tf(g, dx=0.0, dy=0.0):
            return affinity.translate(affinity.scale(g, s, s, origin=(ax, ay)), tx - ax + dx, ty - ay + dy).buffer(0)
        U = unary_union([r["geom"] for r in rs if not r.get("glow")])
        best = None
        for rad in np.arange(0, 20.5, 0.5):
            for k in range(max(1, int(rad*2))):
                a = 2*math.pi*k/max(1, int(rad*2)); dx, dy = rad*math.cos(a), rad*math.sin(a)
                if clip.contains(tf(U, dx, dy)): best = (dx, dy); break
            if best: break
        if best is None: best = (0.0, 0.0); moves[el] = "NO FIT"
        else: moves[el] = (round(best[0], 1), round(best[1], 1))
        for r in rs:             # geometry + column centrelines / widths + radial centres follow the badge
            out.append(KS.move(r, s, (ax, ay), (tx - ax + best[0], ty - ay + best[1])))
    badges = unary_union([r["geom"] for r in out if not r.get("glow")]).buffer(2.0)
    stars = [r for r in its if (r.get("unit") or "").startswith("05")]
    kept, dropped, nudged, reloc = place_stars(stars, clip, badges, lambda c: (c.x*kx, c.y*ky), out, far=45.0)
    return out, clip, dict(moves=moves, stars=kept, stars_dropped=dropped, stars_nudged=nudged, stars_relocated=reloc, scale=s, grade=grade)

def place_stars(stars, clip, avoid, mapf, out, max_move=8.0, gap=2.5, far=None):
    """move each star (all regions of one unit together) to its mapped position. A star that lands in a keep-out (or on a
    badge) goes to a free spot inside the clip, chosen on a 1 mm grid by distance from its mapped position minus spacing
    from its neighbours (nearest-point projection lined stars up along the keep-out edges). Tiers: <= max_move
    ('nudged'), <= far, then <= 2 x far ('relocated', fronts: review item 8 — nudge, don't drop)."""
    from shapely import contains_xy
    groups = {}
    for r in stars: groups.setdefault(r.get("unit"), []).append(r)
    placed = []; pc = []; kept = dropped = nudged = relocated = 0
    rng = np.random.default_rng(5)
    for u, rs in groups.items():
        body = unary_union([r["geom"] for r in rs if not r.get("glow")] or [r["geom"] for r in rs])
        c = body.centroid; nx_, ny_ = mapf(c)
        g = affinity.translate(body, nx_ - c.x, ny_ - c.y)
        gb = g.bounds; rad = max(gb[2] - gb[0], gb[3] - gb[1]) / 2 + 0.4       # bounding radius (sparkles are concave)
        ok = lambda q: clip.contains(q) and (avoid is None or not q.intersects(avoid)) and all(q.distance(p) >= gap for p in placed)
        if not ok(g):
            moved = None; tiers = [max_move] + ([far, 2 * far] if far else [])
            free0 = clip.buffer(-rad)
            if avoid is not None: free0 = free0.difference(avoid.buffer(rad))
            gc = np.array([g.centroid.x, g.centroid.y])
            for ti, lim in enumerate(tiers):
                free = free0.intersection(g.centroid.buffer(lim))
                if free.is_empty: continue
                b_ = free.bounds
                X, Y = np.meshgrid(np.arange(b_[0], b_[2] + 1e-6, 1.0), np.arange(b_[1], b_[3] + 1e-6, 1.0))
                m = contains_xy(free, X, Y); xs, ys = X[m], Y[m]
                if not len(xs): continue
                dist = np.hypot(xs - gc[0], ys - gc[1])
                if pc:
                    P_ = np.array([q[:2] for q in pc]); R_ = np.array([q[2] for q in pc])
                    near = np.hypot(xs[:, None] - P_[None, :, 0], ys[:, None] - P_[None, :, 1]) - R_[None, :] - rad
                    md = near.min(axis=1)
                else: md = np.full(len(xs), 10.0)
                sel = md >= gap
                if not sel.any(): continue
                score = dist - 1.2 * np.minimum(md, 8.0) + rng.uniform(0, 0.8, len(xs))
                score[~sel] = 1e9
                for k in np.argsort(score)[:6]:
                    if score[k] >= 1e9: break
                    cand = affinity.translate(g, xs[k] - gc[0], ys[k] - gc[1])
                    if ok(cand): moved = cand; break
                if moved is not None:
                    if ti == 0: nudged += 1
                    else: relocated += 1
                    break
            if moved is None: dropped += 1; continue
            g = moved
        dx, dy = g.centroid.x - c.x, g.centroid.y - c.y
        for r in rs: out.append(KS.move(r, 1.0, (0, 0), (dx, dy)))
        placed.append(g); pc.append((g.centroid.x, g.centroid.y, rad)); kept += 1
    return kept, dropped, nudged, relocated

def place_sleeve(size, P):
    clip = SV.clip_for(size, P).buffer(-0.4)
    kx, ky, top_m, top_s = SV.ratio(size, P)
    out = []
    kept, dropped, nudged, reloc = place_stars(ITEMS[P], clip, None, lambda c: (c.x*kx, top_s + (c.y - top_m)*ky), out, far=14.0)
    return out, clip, dict(stars=kept, stars_dropped=dropped, stars_nudged=nudged, stars_relocated=reloc)

def clip_runs(vis, clip):
    """stipple runs (glow, haze) carry their own stitch points: cut them at the clip (keep-outs), one region per inside
    piece, geometry = the piece's own footprint (one polygon, so make_pattern emits it once)."""
    from shapely import contains_xy
    out = []
    for r in vis:
        if not r.get("run_pts"): out.append(r); continue
        P = np.array(r["run_pts"]); ins = contains_xy(clip, P[:, 0], P[:, 1]); runs = []; cur = []
        for q, k in zip(r["run_pts"], ins):
            if k: cur.append(q)
            elif cur: runs.append(cur); cur = []
        if cur: runs.append(cur)
        for run in runs:
            if len(run) < 3: continue
            g = LineString(run).buffer(0.35)
            if g.geom_type != "Polygon": g = max(getattr(g, "geoms", [g]), key=lambda q: q.area)
            out.append(dict(r, geom=g, run_pts=run))
    return out

def build(size):
    t0 = time.time(); res = {"info": dict(size=size, grade=kccore.GRADE[size][0], scale=kccore.GRADE[size][1])}
    for P in kccore.PIECES:
        its, clip, info = (place_front if P in ("FR", "FL") else place_sleeve)(size, P)
        vis = visible(its, clip)
        vis = dst2.clean_vis([v for v in vis if not v.get("nok")]) + [v for v in vis if v.get("nok")]
        vis = clip_runs(vis, clip)
        vis = [dict(r, geom=r["geom"].intersection(clip).buffer(0)) for r in vis]
        vis = [r for r in vis if not r["geom"].is_empty and r["geom"].area > 0.3]
        vis.sort(key=lambda r: r["z"])
        res[P] = vis
        u = unary_union([r["geom"] for r in vis])
        res["info"][P] = dict(info, objects=len(vis), area=u.area, bbox=u.bounds)
    pickle.dump(res, open(f"art_{size}.pkl", "wb"))
    print(size, {P: {k: v for k, v in res["info"][P].items() if k in ("moves", "stars", "stars_dropped", "stars_nudged", "stars_relocated", "objects")} for P in kccore.PIECES},
          f"{time.time()-t0:.0f}s", flush=True)
    return res

def flat_png(size, res, path, ppm=2.0):
    from render import geom_to_path
    from motifs2 import HEX
    import cairosvg
    g, mt = F.pieces(size)
    sl = {P: SV.piece(size, P) for P in ("SR", "SL")}
    # fronts in place; sleeves drawn beside them (their own pattern coords, offset)
    OFF = {"SR": (-640, 120), "SL": (640, 120)}
    x0, y0, x1, y1 = -930, -130, 930, 620
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {x1-x0} {y1-y0}" width="{int((x1-x0)*ppm)}" height="{int((y1-y0)*ppm)}">',
         f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#FFFFFF"/>']
    for code in ("F01", "F02"):
        o.append(f'<path d="{geom_to_path(g[code].sew_poly())}" fill="{kccore.FABRIC}" stroke="#555" stroke-width="0.8"/>')
    for side in "RL":
        o.append(f'<path d="{geom_to_path(F.clip_for(size, side))}" fill="none" stroke="#FF4040" stroke-width="0.4" stroke-dasharray="2 1.5"/>')
        o.append(f'<path d="{geom_to_path(F.keep_geoms(size, side)["welt"])}" fill="#2a2f3a" stroke="#888" stroke-width="0.5"/>')
    for P in ("SR", "SL"):
        dx, dy = OFF[P]
        o.append(f'<g transform="translate({dx} {dy})"><path d="{geom_to_path(sl[P].sew_poly())}" fill="{kccore.FABRIC}" stroke="#555" stroke-width="0.8"/>'
                 f'<path d="{geom_to_path(SV.clip_for(size, P))}" fill="none" stroke="#FF4040" stroke-width="0.4" stroke-dasharray="2 1.5"/></g>')
    for P in kccore.PIECES:
        dx, dy = OFF.get(P, (0, 0))
        o.append(f'<g transform="translate({dx} {dy})">')
        for r in res[P]: o.append(f'<path d="{geom_to_path(r["geom"])}" fill="{HEX[r["col"]]}" fill-rule="evenodd"/>')
        o.append('</g>')
    o.append(f'<text x="{x0+8}" y="{y0+20}" font-size="16" font-family="Liberation Sans" fill="#333">size {size} · grade {res["info"]["grade"]} ({res["info"]["scale"]*100:.0f} %) · sleeves shown beside the fronts (pattern coords; front half toward the body)</text>')
    o.append('</svg>')
    cairosvg.svg2png(bytestring="".join(o).encode(), write_to=path)

if __name__ == "__main__":
    os.makedirs("out/art", exist_ok=True)
    for sz in sys.argv[1:] or kccore.SIZES:
        r = build(sz); flat_png(sz, r, f"out/art/{sz}_flat.png")
