"""Rev K/L/M pullover art + hoop plan, one size (default M). usage: python3 pv_art.py [SIZE]
Rev M (2026-10-27, Nick approved "Mockups 3"): badges, script and EVERY star sit where the approved mockup has them
(mock3.py maps mockup px -> garment mm by panel proportion). No density rule, no random placement: each mockup star becomes
the Rev J library unit of its kind (plus / dot) at its size rank. A star that lands in a keep-out or on a hoop split is
nudged up to NUDGE_MAX mm, else dropped and counted. Hoopings only cover the area that carries art.
- 4 back badges = the Rev J badge regions UNCHANGED (art_M.pkl from Rev J, elements 01-04: text 宇宙をきれいに,
  KEEP CLEAN OUR SPACE, 不要世界污染, 우리들 소중한 우주! - kccore.TEXT; the new mockup's lettering is AI and its Korean is
  mirror-reversed, td-chair C-02), translated (never rotated or rescaled) to the new mockup's back positions.
- hem script "SEE YOU SPACE COWBOY..." (element 07) on the kangaroo pocket, lower right as in the mockup, set from a font.
- star field (element 05) on front, back, pocket, both sleeves and both hood sides: units cloned from the Rev J back field
  (element 06, founder-reviewed Rev H/J) at the same density, placed AFTER the hoop plan so that no star sits within
  SPLIT_CLEAR of a split line, none within KEEP_EDGE of a cut edge, none under the pocket (td-chair-r1 G-03/G-05).
- hoop plan: every piece cut into cells no bigger than the 340 x 505 mm field (either way round); split lines may not
  cross a badge or the script (+ SPLIT_CLEAR). Fewest hoopings first, then the widest clearance.
Rev L's density rule and "zoned" fallback are gone (Mockups 3 replaces both)."""
import sys, json, math, pickle, random, itertools, os
import numpy as np
from shapely.geometry import Polygon, box, Point, LineString, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
import pv_block as B
import kclettering as KL, kcmotifs as KM

SIZE = next((a for a in sys.argv[1:] if a in B.CHART), "M")
TAG = "allover"
HOOP = (340.0, 505.0)        # Mandy: 340 x 505 single hooping confirmed (factory.json single_hooping_confirmed_mm.front)
KEEP_EDGE = 18.0             # cut edge -> star: 10 SA + 8 clear [proposed, td-chair G-03 opinion]
KEEP_FACE = 40.0             # hood face edge: 30 turn-back + 10 [proposed]
KEEP_POCKET = 22.0           # pocket cut edge (hand openings are topstitched) [proposed]
SPLIT_CLEAR = 10.0           # no star within 10 mm of a hoop split (td-chair-r1)
POCKET_CLEAR = 10.0          # no star under the pocket or within 10 mm of its edge
OBJ_CLEAR = 6.0              # star -> badge / script
TRIM_MAX = 30.0              # a hoop row thinner than this is trimmed off the star area (saves a hooping)
TRIM_BY = {"BK": 70.0}       # founder 27 Oct "remove BK-H2": the 59 mm top strip of the back is trimmed, not hooped
NUDGE_MAX = 10.0             # Rev M: a mockup star may move this far to clear a keep-out / split, else it is dropped
STAR_GAP = 3.0               # Rev M: min clear gap between two star units
REV_J = "art_M.pkl"
OUT = f"out/pv/{SIZE}"; os.makedirs(OUT, exist_ok=True)
M3 = json.load(open(f"{OUT}/mock3_targets.json"))            # run mock3.py first

KL.FONTS["sc"] = ("SourceSerif4-Italic[opsz,wght].ttf", 700)
SCRIPT = "SEE YOU SPACE COWBOY..."
SCRIPT_W = 200.0             # mockup: ~209 mm wide at M (front 1.49 mm/px); 200 keeps it inside the pocket keep-out


J = pickle.load(open(REV_J, "rb"))
cut = B.pieces(SIZE)

def shift(r, dx, dy):
    r = dict(r); r["geom"] = affinity.translate(r["geom"], dx, dy)
    if "col_cl" in r: r["col_cl"] = [(float(x) + dx, float(y) + dy) for x, y in r["col_cl"]]
    return r

def units(regs):
    u = {}
    for r in regs: u.setdefault(r["unit"], []).append(r)
    return u

# ---------------------------------------------------------------- allowed areas
L = B.poms(SIZE)["body_length"] - B.P["rib_hem"]
pocket_fp = B.pocket_on_front(SIZE)
allowed = {}
for P, g in cut.items():
    a = g.buffer(-(KEEP_POCKET if P == "PK" else KEEP_EDGE), join_style=2)
    if P == "HR": a = a.difference(box(-50, -50, KEEP_FACE, 500))
    if P == "HL": a = a.difference(box(-KEEP_FACE, -50, 50, 500))
    if P == "FR": a = a.difference(pocket_fp.buffer(POCKET_CLEAR))
    allowed[P] = a

# ---------------------------------------------------------------- badges (Rev J, unchanged) + script
items = {P: [] for P in cut}
objs = {P: [] for P in cut}          # (name, footprint) the split lines must avoid
badge_moves = {}
for el in ("01", "02", "03", "04"):
    src = "FR" if el in ("01", "03") else "FL"
    rs = [r for r in J[src] if r["el"] == el]
    fp = unary_union([r["geom"] for r in rs]); c = fp.envelope.centroid
    tx, ty = M3["badges_mm"][el]; dx, dy = tx - c.x, ty - c.y
    area = cut["BK"].buffer(-KEEP_EDGE, join_style=2)
    for _ in range(200):                                   # nudge inwards until the whole badge clears the edge keep-out
        if affinity.translate(fp, dx, dy).within(area): break
        cx, cy = affinity.translate(fp, dx, dy).centroid.coords[0]
        dx += -0.5 * np.sign(cx); dy += 0.5 if cy < 250 else -0.5
    items["BK"] += [shift(r, dx, dy) for r in rs]
    objs["BK"].append((el, affinity.translate(fp, dx, dy)))
    badge_moves[el] = dict(src=src, target_mm=(round(tx, 1), round(ty, 1)), placed_centre_mm=tuple(round(v, 1) for v in affinity.translate(fp, dx, dy).envelope.centroid.coords[0]),
                           size_mm=tuple(round(v, 1) for v in (fp.bounds[2] - fp.bounds[0], fp.bounds[3] - fp.bounds[1])))
for a, b in itertools.combinations(objs["BK"], 2):
    assert a[1].distance(b[1]) > 8, f"badges {a[0]} and {b[0]} too close ({a[1].distance(b[1]):.1f} mm)"

def set_sc(text, em, trk):
    """Latin line in the script font (KL.set_line only knows the 'en' space glyph); word space = advance of 'n'"""
    out, x = [], 0.0
    for ch in text:
        if ch == " ": x += KL.glyph("sc", "n", em)[1] * 0.8 + trk; continue
        g, adv = KL.glyph("sc", ch, em); out.append((ch, affinity.translate(g, x, 0))); x += adv + trk
    return out
gl = set_sc(SCRIPT, 20.0, 0.6)
b0 = KL.ink_bounds(gl); k = SCRIPT_W / (b0[2] - b0[0])
gl = set_sc(SCRIPT, 20.0 * k, 0.6 * k)
b0 = KL.ink_bounds(gl); sh = b0[3] - b0[1]
pk_area = cut["PK"].buffer(-KEEP_POCKET, join_style=2)
H = B.P["pocket_h"]; sx, sy = M3["script_mm"][0], H - KEEP_POCKET - 4 - sh / 2   # Mockups 3: lower right of the pocket, just above the rib
for _ in range(300):
    g2 = KL.place(gl, sx, sy, 0.0); fp = unary_union([g for _, g in g2])
    if fp.within(pk_area): break
    sx -= 0.5
core, _ = KM.text_columns(g2, "kc_white", "TXC", "round", "07-script")
for i, r in enumerate(core): r.update(layer=31, el="07", z=31 * 100000 + i, ko=True, kob=0.0)
items["PK"] += core; objs["PK"].append(("07", unary_union([fp] + [r["geom"] for r in core])))   # columns overhang the outline
script_meta = dict(text=SCRIPT, centre_mm=(round(sx, 1), round(sy, 1)), width_mm=round(fp.bounds[2] - fp.bounds[0], 1),
                   cap_height_mm=round((lambda b: b[3] - b[1])(KL.glyph("sc", "E", 20.0 * k)[0].bounds), 1),
                   font="Source Serif 4 Italic, weight 700 (OFL)", min_stroke_note="satin columns from the font strokes (kcsatin)")

# ---------------------------------------------------------------- star library + Rev M targets
lib = list(units([r for r in J["BK"] if r["el"] == "06"]).values())
cents = [unary_union([r["geom"] for r in u]).centroid for u in lib]
def u_size(u): b = unary_union([r["geom"] for r in u]).bounds; return max(b[2] - b[0], b[3] - b[1])
kind = ["SPK" if any(r["grp"] == "SPK" for r in u) else "DOT" for u in lib]
by_kind = {k: sorted([i for i in range(len(lib)) if kind[i] == k], key=lambda i: u_size(lib[i])) for k in ("SPK", "DOT")}
def unit_for(t): L_ = by_kind[t["kind"]]; return L_[min(len(L_) - 1, int(t["q"] * len(L_)))]
targets = {P: [t for t in M3["targets"] if t["piece"] == P] for P in cut}
def foot(i, x, y): c = cents[i]; return affinity.translate(unary_union([r["geom"] for r in lib[i]]), x - c.x, y - c.y)
# the hoop plan covers the art that is there: stars (within the keep-outs, so a nudge can still land) + badges/script
plan_area = {P: unary_union([foot(unit_for(t), t["x"], t["y"]).buffer(2.0) for t in targets[P]]).intersection(allowed[P]) if targets[P]
             else Polygon() for P in cut}
star_obs = {P: [("star", foot(unit_for(t), t["x"], t["y"])) for t in targets[P]] for P in cut}

# ---------------------------------------------------------------- hoop plan
def cells_for(P, avoid_stars=True):
    obs = objs[P] + (star_obs[P] if avoid_stars else [])
    A = plan_area[P].union(unary_union([f for _, f in objs[P]])) if objs[P] else plan_area[P]
    if A.is_empty: return [], A
    x0, y0, x1, y1 = A.bounds
    best = None
    for ow, oh in (HOOP, HOOP[::-1]):
        nx0 = math.ceil((x1 - x0) / ow - 1e-9)
        for nx in (nx0, nx0 + 1):
            if nx > 3: continue
            lo = [x1 - (nx - i) * ow for i in range(1, nx)]; hi = [x0 + i * ow for i in range(1, nx)]
            grids = [np.arange(max(l, x0 + 5), min(h, x1 - 5) + 0.01, 2.0) for l, h in zip(lo, hi)]
            for xs in itertools.product(*grids):
                if any(b - a < 5 for a, b in zip(xs, xs[1:])): continue
                xb = [x0, *xs, x1]
                if any(b - a > ow + 1e-6 for a, b in zip(xb, xb[1:])): continue
                if any(LineString([(x, y0 - 5), (x, y1 + 5)]).distance(f) < SPLIT_CLEAR for x in xs for _, f in obs): continue
                cols = []; ok = True
                for a, b in zip(xb, xb[1:]):
                    sub = A.intersection(box(a, y0 - 1, b, y1 + 1))
                    if sub.is_empty: cols.append([]); continue
                    _, c0, _, c1 = sub.bounds; ny = math.ceil((c1 - c0) / oh - 1e-9)
                    if ny == 2 and (c1 - c0) - oh <= TRIM_BY.get(P, TRIM_MAX) and all(f.bounds[3] <= c0 + oh - SPLIT_CLEAR for _, f in obs
                                                                      if f.intersects(box(a, c0, b, c1))):
                        ny, c1 = 1, c0 + oh                         # a thin last row: trim the star area instead of a hooping
                    if ny == 1: cols.append([(a, c0, b, c1)]); continue
                    if ny > 2: ok = False; break
                    cand = [y for y in np.arange(max(c1 - oh, c0 + 5), min(c0 + oh, c1 - 5) + 0.01, 2.0)
                            if all(LineString([(a, y), (b, y)]).distance(f) >= SPLIT_CLEAR for _, f in obs)]
                    if not cand: ok = False; break
                    clear = lambda y: min([LineString([(a, y), (b, y)]).distance(f) for _, f in obs] + [999])
                    y = max(cand, key=lambda y: (min(clear(y), 60), -abs(y - (c0 + c1) / 2)))
                    cols.append([(a, c0, b, y), (a, y, b, c1)])
                if not ok: continue
                cells = [c for col in cols for c in col]
                clr = min([LineString([(x, y0), (x, y1)]).distance(f) for x in xs for _, f in obs] + [999])
                key = (len(cells), -min(clr, 60), sum(abs(x - (x0 + x1) / 2) for x in xs))
                if best is None or key < best[0]: best = (key, cells, (ow, oh))
    if avoid_stars:   # a hooping costs more than a star moved <= NUDGE_MAX mm: take the plan that ignores stars if it has fewer cells
        alt, _ = cells_for(P, False)
        if not best or len(alt) < len(best[1]): return alt, A
    assert best, f"{P}: no hoop plan fits {HOOP}"
    return [dict(box=c, frame=best[2]) for c in best[1]], A

plan = {}
for P in cut:
    cells, A = cells_for(P)
    plan[P] = cells

def split_lines(P):
    out = []
    for c in plan[P]:
        x0, y0, x1, y1 = c["box"]
        out += [LineString([(x0, y0), (x1, y0)]), LineString([(x0, y1), (x1, y1)]), LineString([(x0, y0), (x0, y1)]), LineString([(x1, y0), (x1, y1)])]
    return unary_union(out)

# ---------------------------------------------------------------- star field (Rev M: the mockup's stars, one by one)
star_meta = dict(source="Mockups 3 (Nick approved 27 Oct 2026)", library_units=len(lib), kinds={k: len(v) for k, v in by_kind.items()},
                 mockup_detected=M3["detected"], mockup_stars=M3["stars"], nudge_max_mm=NUDGE_MAX)
RINGS = [(0.0, 0.0)] + [(r * math.cos(a * math.pi / 8), r * math.sin(a * math.pi / 8)) for r in np.arange(1.0, NUDGE_MAX + 0.01, 1.0) for a in range(16)]
counts = {}; star_stats = {}; dropped = []; nudges = []
for P in cut:
    A = allowed[P]
    for _, f in objs[P]: A = A.difference(f.buffer(OBJ_CLEAR))
    if plan[P]: A = A.intersection(unary_union([box(*c["box"]) for c in plan[P]])).difference(split_lines(P).buffer(SPLIT_CLEAR))
    placed = []; used = []
    for t in targets[P]:
        i = unit_for(t); ok = None
        for dx, dy in RINGS:
            fp = foot(i, t["x"] + dx, t["y"] + dy)
            if fp.buffer(0.5).within(A) and all(fp.distance(g) >= STAR_GAP for g in placed): ok = (dx, dy, fp); break
        if ok is None: dropped.append(dict(piece=P, x=t["x"], y=t["y"], px=t["px"])); continue
        dx, dy, fp = ok; placed.append(fp); used.append(i); n = len(placed)
        if dx or dy: nudges.append(round(math.hypot(dx, dy), 1))
        c = cents[i]
        rs = [shift(r, t["x"] + dx - c.x, t["y"] + dy - c.y) for r in lib[i]]
        for j, r in enumerate(rs): r.update(el="05", unit=f"05-{P}{n}", z=21 * 100000 + n * 10 + j)
        items[P] += rs
    counts[P] = len(placed)
    if used:
        sz = [u_size(lib[i]) for i in used]
        star_stats[P] = dict(stars=len(used), plus=sum(kind[i] == "SPK" for i in used), mean_mm=round(sum(sz) / len(sz), 2),
                             median_mm=round(sorted(sz)[len(sz) // 2], 2), mockup=len(targets[P]))
star_meta.update(per_panel=star_stats, dropped=dropped, nudged=len(nudges), nudge_mean_mm=round(sum(nudges) / len(nudges), 1) if nudges else 0,
                 plus_share=round(sum(v["plus"] for v in star_stats.values()) / max(1, sum(counts.values())), 3))

# every star / badge / script region must sit inside one hoop cell (fail loudly)
assign = {}
for P in cut:
    for uid, rs in units(items[P]).items():
        fp = unary_union([r["geom"] for r in rs])
        hit = [i for i, c in enumerate(plan[P]) if fp.within(box(*c["box"]).buffer(0.01))]
        assert len(hit) >= 1, f"{P} {uid}: crosses a hoop split"
        assign.setdefault(P, {}).setdefault(hit[0], []).extend(rs)

pickle.dump(dict(items=items, assign=assign, cut=cut, allowed=allowed, objs=objs, plan=plan, pocket_fp=pocket_fp),
            open(f"{OUT}/art_{TAG}.pkl", "wb"))
meta = dict(size=SIZE, variant=TAG, hoop=HOOP, keep=dict(edge=KEEP_EDGE, face=KEEP_FACE, pocket=KEEP_POCKET, split=SPLIT_CLEAR,
            under_pocket=POCKET_CLEAR, objects=OBJ_CLEAR), badges=badge_moves, script=script_meta, stars=star_meta,
            star_counts=counts, hoopings={P: len(plan[P]) for P in cut}, total_hoopings=sum(len(v) for v in plan.values()),
            cells={P: [dict(box=[round(v, 1) for v in c["box"]], frame=c["frame"], w=round(c["box"][2] - c["box"][0], 1),
                            h=round(c["box"][3] - c["box"][1], 1)) for c in plan[P]] for P in cut},
            pieces_mm={P: [round(v, 1) for v in g.bounds] for P, g in cut.items()})
json.dump(meta, open(f"{OUT}/plan_{TAG}.json", "w"), indent=1, ensure_ascii=False)
print(json.dumps(dict(hoopings=meta["hoopings"], total=meta["total_hoopings"], stars=counts, badges=badge_moves, script=script_meta), ensure_ascii=False))
