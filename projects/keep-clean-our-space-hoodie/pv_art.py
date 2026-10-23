"""Rev K pullover art + hoop plan, one size (default M). usage: python3 pv_art.py [SIZE] [zoned]
- 4 back badges = the Rev J badge regions UNCHANGED (art_M.pkl from Rev J, elements 01-04: text 宇宙をきれいに,
  KEEP CLEAN OUR SPACE, 不要世界污染, 우리들 소중한 우주! - kccore.TEXT; the new mockup's lettering is AI and its Korean is
  mirror-reversed, td-chair C-02), translated (never rotated or rescaled) to the new mockup's back positions.
- hem script "SEE YOU SPACE COWBOY..." (element 07) on the kangaroo pocket, lower right as in the mockup, set from a font.
- star field (element 05) on front, back, pocket, both sleeves and both hood sides: units cloned from the Rev J back field
  (element 06, founder-reviewed Rev H/J) at the same density, placed AFTER the hoop plan so that no star sits within
  SPLIT_CLEAR of a split line, none within KEEP_EDGE of a cut edge, none under the pocket (td-chair-r1 G-03/G-05).
- hoop plan: every piece cut into cells no bigger than the 340 x 505 mm field (either way round); split lines may not
  cross a badge or the script (+ SPLIT_CLEAR). Fewest hoopings first, then the widest clearance.
"zoned" = the fallback (founder card): stars at half density, only hood, shoulders / upper back, upper sleeves, top front."""
import sys, json, math, pickle, random, itertools, os
import numpy as np
from shapely.geometry import Polygon, box, Point, LineString, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
import pv_block as B
import kclettering as KL, kcmotifs as KM

SIZE = next((a for a in sys.argv[1:] if a in B.CHART), "M")
ZONED = "zoned" in sys.argv
TAG = "zoned" if ZONED else "allover"
HOOP = (340.0, 505.0)        # Mandy: 340 x 505 single hooping confirmed (factory.json single_hooping_confirmed_mm.front)
KEEP_EDGE = 18.0             # cut edge -> star: 10 SA + 8 clear [proposed, td-chair G-03 opinion]
KEEP_FACE = 40.0             # hood face edge: 30 turn-back + 10 [proposed]
KEEP_POCKET = 22.0           # pocket cut edge (hand openings are topstitched) [proposed]
SPLIT_CLEAR = 10.0           # no star within 10 mm of a hoop split (td-chair-r1)
POCKET_CLEAR = 10.0          # no star under the pocket or within 10 mm of its edge
OBJ_CLEAR = 6.0              # star -> badge / script
REV_J = "art_M.pkl"
OUT = f"out/pv/{SIZE}"; os.makedirs(OUT, exist_ok=True)

KL.FONTS["sc"] = ("SourceSerif4-Italic[opsz,wght].ttf", 700)
SCRIPT = "SEE YOU SPACE COWBOY..."
SCRIPT_W = 200.0             # mockup: ~209 mm wide at M (front 1.49 mm/px); 200 keeps it inside the pocket keep-out

# mockup back view (px, 1307 x 684 render): CB x 985, neck y 150, x 1.63 mm/px (chest 635 / 390 px), y 1.35 mm/px
BADGE_PX = {"01": (871, 238), "02": (1092, 258), "03": (859, 410), "04": (1055, 472)}
def back_mm(px, py): return ((px - 985) * 1.63, (py - 150) * 1.35)

rnd = random.Random(20261023 + (7 if ZONED else 0))
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
if ZONED:   # fallback: hood, shoulders / upper back, upper sleeves, light top front
    allowed["BK"] = allowed["BK"].intersection(box(-999, -999, 999, 230))
    allowed["FR"] = allowed["FR"].intersection(box(-999, -999, 999, 170))
    for P in ("SR", "SL"): allowed[P] = allowed[P].intersection(box(-999, -999, 999, 260))
    allowed["PK"] = Polygon()

# ---------------------------------------------------------------- badges (Rev J, unchanged) + script
items = {P: [] for P in cut}
objs = {P: [] for P in cut}          # (name, footprint) the split lines must avoid
badge_moves = {}
for el in ("01", "02", "03", "04"):
    src = "FR" if el in ("01", "03") else "FL"
    rs = [r for r in J[src] if r["el"] == el]
    fp = unary_union([r["geom"] for r in rs]); c = fp.envelope.centroid
    tx, ty = back_mm(*BADGE_PX[el]); dx, dy = tx - c.x, ty - c.y
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
H = B.P["pocket_h"]; sx, sy = 70.0, H - KEEP_POCKET - 4 - sh / 2      # mockup: lower right of the pocket, just above the rib
for _ in range(300):
    g2 = KL.place(gl, sx, sy, 0.0); fp = unary_union([g for _, g in g2])
    if fp.within(pk_area): break
    sx -= 0.5
core, _ = KM.text_columns(g2, "kc_white", "TXC", "round", "07-script")
for i, r in enumerate(core): r.update(layer=31, el="07", z=31 * 100000 + i, ko=True, kob=0.0)
items["PK"] += core; objs["PK"].append(("07", fp))
script_meta = dict(text=SCRIPT, centre_mm=(round(sx, 1), round(sy, 1)), width_mm=round(fp.bounds[2] - fp.bounds[0], 1),
                   cap_height_mm=round((lambda b: b[3] - b[1])(KL.glyph("sc", "E", 20.0 * k)[0].bounds), 1),
                   font="Source Serif 4 Italic, weight 700 (OFL)", min_stroke_note="satin columns from the font strokes (kcsatin)")

# ---------------------------------------------------------------- hoop plan
def cells_for(P):
    A = allowed[P].union(unary_union([f for _, f in objs[P]])) if objs[P] else allowed[P]
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
                if any(LineString([(x, y0 - 5), (x, y1 + 5)]).distance(f) < SPLIT_CLEAR for x in xs for _, f in objs[P]): continue
                cols = []; ok = True
                for a, b in zip(xb, xb[1:]):
                    sub = A.intersection(box(a, y0 - 1, b, y1 + 1))
                    if sub.is_empty: cols.append([]); continue
                    _, c0, _, c1 = sub.bounds; ny = math.ceil((c1 - c0) / oh - 1e-9)
                    if ny == 1: cols.append([(a, c0, b, c1)]); continue
                    if ny > 2: ok = False; break
                    cand = [y for y in np.arange(max(c1 - oh, c0 + 5), min(c0 + oh, c1 - 5) + 0.01, 2.0)
                            if all(LineString([(a, y), (b, y)]).distance(f) >= SPLIT_CLEAR for _, f in objs[P])]
                    if not cand: ok = False; break
                    clear = lambda y: min([LineString([(a, y), (b, y)]).distance(f) for _, f in objs[P]] + [999])
                    y = max(cand, key=lambda y: (min(clear(y), 60), -abs(y - (c0 + c1) / 2)))
                    cols.append([(a, c0, b, y), (a, y, b, c1)])
                if not ok: continue
                cells = [c for col in cols for c in col]
                clr = min([LineString([(x, y0), (x, y1)]).distance(f) for x in xs for _, f in objs[P]] + [999])
                key = (len(cells), -min(clr, 60), sum(abs(x - (x0 + x1) / 2) for x in xs))
                if best is None or key < best[0]: best = (key, cells, (ow, oh))
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

# ---------------------------------------------------------------- star field
lib = list(units([r for r in J["BK"] if r["el"] == "06"]).values())
cents = [unary_union([r["geom"] for r in u]).centroid for u in lib]
hull = unary_union([Point(c.x, c.y) for c in cents]).convex_hull
DENS = len(lib) / hull.area * (0.5 if ZONED else 1.0)          # stars per mm^2
star_meta = dict(library_units=len(lib), revj_back_hull_mm2=round(hull.area), density_per_m2=round(DENS * 1e6),
                 kinds={k: sum(1 for u in lib if any(r["grp"] == k for r in u)) for k in ("DOT", "SPK")})
counts = {}
for P in cut:
    A = allowed[P]
    for _, f in objs[P]: A = A.difference(f.buffer(OBJ_CLEAR))
    if plan[P]: A = A.difference(split_lines(P).buffer(SPLIT_CLEAR))
    if A.is_empty: counts[P] = 0; continue
    target = int(round(DENS * A.area)); dmin = 0.55 / math.sqrt(DENS)
    x0, y0, x1, y1 = A.bounds; pts = []; tries = 0
    while len(pts) < target and tries < 60000:
        tries += 1
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        if any((x - a) ** 2 + (y - b) ** 2 < dmin ** 2 for a, b in pts): continue
        i = rnd.randrange(len(lib)); u = lib[i]; c = cents[i]
        rs = [shift(r, x - c.x, y - c.y) for r in u]
        if not unary_union([r["geom"] for r in rs]).buffer(0.5).within(A): continue
        pts.append((x, y)); n = len(pts)
        for j, r in enumerate(rs): r.update(el="05", unit=f"05-{P}{n}", z=21 * 100000 + n * 10 + j)
        items[P] += rs
    counts[P] = len(pts)

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
