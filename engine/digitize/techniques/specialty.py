"""Gates, machine routing, export and previews for the M6 specialty plugins (puff, chenille, chain / faux_chain).

  machine_of(part)                 "lockstitch" | "chenille" (technique sequencing["machine"])
  isolate_foam(plan)               puff parts get their own thread key (<thread>+foam): sequence.order then gives them
                                   their own stop = the machine stop where the operator lays the foam
  knockout_under_puff(parts)       house rule 6 for puff: lower lock-stitch parts lose what the puff covers, keeping
                                   cut_keep_mm under its edge (no flat stitches inside the foam)
  plan_gates(plan)                 no tatami / fill on a puff part; every puff stop holds only puff parts; flat parts
                                   that touch a puff part sew in an EARLIER stop (foam goes on top of the flat work);
                                   puff thread + stop key end in "+foam"; 0 lower stitches inside puff minus keep band
  guard_puff(plan)                 compile.write raises PuffNotIsolated when any plan gate fails
  puff_gates(part, segs)           on the WRITTEN file's segments of the part (compile.labelled_dst): width in range,
                                   satin only (no penetrations inside the foam body), row spacing <= max, ends closed
                                   (perforated + capped), rows <= the DST limit, foam spec in range
  faux_chain_gates(part, segs)     reads as linked loops (both sides of the line in every link), on the line, short
                                   stitches, no gaps
  chenille_gates(part, detail)     constant stitch length, moss covers the part without pile-up, chain outline closed
                                   on the edge, head settings declared
  chain_gates(part, detail)        constant stitch length, on the line
  export_chenille(items, base)     raises FactoryFormatNeeded: the factory has not said which chenille head / file
                                   format (F1). write_chenille_plan() writes the neutral plan json (mm paths + settings).
  swatch_png(layers, bounds, png)  preview: lock-stitch segments, foam, moss loops, chain links

Every gate returns {name: dict(ok=bool, value=..., limit=...)}; a gate is judged on generated data, never typed."""
import json, math
import numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

PUFF_KINDS = ("puff_column",)
CHENILLE_QUESTION = ("Chenille: which machine sews it (e.g. Tajima TMCE / Barudan BEMR / other), which file format does "
                     "it read, how are loop (moss) and chain modes and needle / loop height set (in the file or at the "
                     "machine), and which chenille yarn + colours do you stock? We send chenille as a path plan until "
                     "you confirm - we will not guess the format.")


class FactoryFormatNeeded(RuntimeError):
    """the factory has not confirmed the chenille machine + file format (F1 open question)"""


class OtherMachine(ValueError):
    """a part planned for a non-lock-stitch head (chenille / chain mode) reached a lock-stitch file"""


def _tech(p):
    from digitize import techniques
    return techniques.get(p.technique) if p.technique else None


def machine_of(p):
    t = _tech(p)
    return (t.sequencing.get("machine") if t is not None else None) or "lockstitch"


def is_puff(p):
    return p.kind in PUFF_KINDS or bool(p.meta.get("puff"))


def g(ok, value=None, limit=None, **kw):
    return dict(ok=bool(ok), value=value, limit=limit, **kw)


# ---------------------------------------------------------------- plan-level
FOAM = "+foam"            # FOAM-ISOLATION CONTRACT: a puff part's thread / stop key ends in "+foam". The stop with that key
                          # is the machine stop where the operator lays the foam, so it must NEVER be merged with a flat
                          # stop of the same colour (sequence batching / any merge by hex colour must keep the key apart).
                          # compile.write refuses a plan that breaks it (guard_puff).


class PuffNotIsolated(ValueError):
    """a puff plan reached a lock-stitch file without its foam stop, or with flat stitches inside the foam"""


def isolate_foam(plan):
    for p in plan.parts:
        if p.technique == "puff" and not p.thread.endswith(FOAM):
            base = p.thread; k = base + FOAM
            if k not in plan.threads:
                th = dict(plan.threads.get(base, {})); th["name"] = f"{th.get('name', base)} (puff stop: lay foam)"
                th["foam_of"] = base; plan.threads[k] = th
            p.thread = k
    return plan


def house_keep():
    from digitize.rulebook import Rulebook
    return float(Rulebook().principles.get("cut_keep_mm", 1.0))


def _under(q, p):
    return (q.technique != "puff" and machine_of(q) == "lockstitch" and q.z < p.z and q.geom.intersects(p.geom))


def knockout_under_puff(parts, keep=None):
    """house rule 6 (cut what is covered) for puff: every lower lock-stitch part loses what the puff covers, keeping a
    `keep` mm underlap band under the puff edge (cut_keep_mm, house.yaml). sequence.cut_under does the same for a whole
    run; this is the puff-only step for callers that plan without it. Returns [(part, puff, mm2 removed)]."""
    from digitize.sequence import clean
    keep = house_keep() if keep is None else keep; out = []
    for p in [p for p in parts if p.technique == "puff"]:
        core = p.geom.buffer(-keep)
        if core.is_empty: continue
        for q in parts:
            if not q.technique or not _under(q, p): continue
            a0 = q.geom.area; q.geom = clean(q.geom.difference(core)); out.append((q.id, p.id, round(a0 - q.geom.area, 2)))
    return out


def base_under_puff(plan, keep=None, pts_by_part=None, tol=0.25):
    """needle points of LOWER lock-stitch parts inside a puff footprint minus the keep band (target 0). pts_by_part:
    {part id: [(x, y)]} from the written file; default = the planned blocks"""
    from shapely.prepared import prep
    keep = house_keep() if keep is None else keep; hits = {}
    for p in [p for p in plan.parts if p.technique == "puff"]:
        core = p.geom.buffer(-(keep + tol))
        if core.is_empty: continue
        C = prep(core)
        for q in plan.parts:
            if not _under(q, p): continue
            pts = pts_by_part.get(q.id, []) if pts_by_part is not None else [pt for b in plan.blocks.get(q.id, []) for pt in b.pts]
            n = sum(1 for pt in pts if C.contains(Point(pt)))
            if n: hits[f"{q.id}>{p.id}"] = n
    return hits


def plan_gates(plan, keep=None, pts_by_part=None):
    out = {}
    bad = [p.id for p in plan.parts if is_puff(p) and p.technique != "puff"]
    out["puff_no_fill"] = g(not bad, value=bad, limit="every puff part sewn by the puff plugin (satin columns, never tatami)")
    stop_of = {pid: i for i, s in enumerate(plan.stops) for pid in s["parts"]}
    mixed = [i for i, s in enumerate(plan.stops)
             if any(plan.part(q).technique == "puff" for q in s["parts"]) and not all(plan.part(q).technique == "puff" for q in s["parts"])]
    late = []
    for p in plan.parts:
        if p.technique != "puff" or p.id not in stop_of: continue
        for q in plan.parts:
            if q.technique == "puff" or q.id not in stop_of or machine_of(q) != "lockstitch": continue
            if q.geom.distance(p.geom) <= 0.5 and stop_of[q.id] >= stop_of[p.id]: late.append((q.id, p.id))
    out["foam_stop"] = g(not mixed and not late, value=dict(mixed_stops=mixed, flat_after_puff=late),
                         limit="puff parts alone in their stop; touching flat parts sewn earlier")
    unkeyed = [p.id for p in plan.parts if p.technique == "puff" and not p.thread.endswith(FOAM)]
    unkeyed += [f"stop {i}" for i, s in enumerate(plan.stops)
                if any(plan.part(q).technique == "puff" for q in s["parts"]) and not str(s["thread"]).endswith(FOAM)]
    out["foam_isolated"] = g(not unkeyed, value=unkeyed, limit=f"puff thread + stop key end in {FOAM!r} (isolate_foam)")
    hits = base_under_puff(plan, keep, pts_by_part)
    out["base_under_puff"] = g(not hits, value=hits,
                               limit=f"0 lower stitches inside the puff minus the {house_keep() if keep is None else keep} mm keep band")
    return out


def guard_puff(plan, keep=None):
    """compile.write: a plan with puff parts must pass every plan gate, else nothing is written"""
    if not any(p.technique == "puff" or is_puff(p) for p in plan.parts): return None   # a puff KIND sewn as tatami too
    G = plan_gates(plan, keep); bad = {k: v["value"] for k, v in G.items() if not v["ok"]}
    if bad:
        raise PuffNotIsolated(f"puff plan refused: {bad}. Call specialty.isolate_foam(plan) before sequence.order (the "
                              f"'{FOAM}' stop is where the foam is laid), knock out flat parts under the puff "
                              f"(sequence.cut_under / specialty.knockout_under_puff) and never fill a puff part.")
    return G


# ---------------------------------------------------------------- geometry helpers
def _frame(ls, pt, d=0.15):
    s = ls.project(Point(pt)); L = ls.length
    a = ls.interpolate(max(0.0, s - d)).coords[0]; b = ls.interpolate(min(L, s + d)).coords[0]
    t = np.subtract(b, a); t = t / max(np.linalg.norm(t), 1e-9)
    c = ls.interpolate(s).coords[0]; v = np.subtract(pt, c)
    return s, float(t[0] * v[1] - t[1] * v[0])          # arc position, signed offset (left +)


def points_of(segs):
    pts = []
    for x0, y0, x1, y1 in segs:
        if not pts or math.dist(pts[-1], (x0, y0)) > 1e-6: pts.append((x0, y0))
        pts.append((x1, y1))
    return pts


# ---------------------------------------------------------------- puff
def puff_gates(part, segs):
    from digitize.techniques.puff import columns_of, foam_of, end_frame, ROW_MAX
    P = part.stitch.params; out = {}
    lo, hi = P.get("min_w", 3.0), P.get("max_w", 7.0); cols = columns_of(part)
    ws = [round(q["w"], 2) for q in cols]
    out["width_in_range"] = g(cols and all(lo <= w <= hi for w in ws), value=ws, limit=[lo, hi])
    f = foam_of(part); fl, fh = P.get("foam_min_mm", 2.0), P.get("foam_max_mm", 4.0)
    out["foam_spec"] = g(fl <= float(f["thickness_mm"]) <= fh and bool(f.get("colour")), value=f, limit=[fl, fh],
                         machine=dict(needle=P.get("needle", "[proposed - confirm]"), spm=P.get("spm", "[proposed - confirm]"),
                                      pull_comp=part.stitch.pull_comp, note="PROPOSED for the strike-off, not measured"))
    if not segs or not cols:
        out["sewn"] = g(False, value=len(segs)); return out
    lss = [LineString(q["cl"]) for q in cols]
    def col_of(pt): return int(np.argmin([ls.distance(Point(pt)) for ls in lss]))
    tol = P.get("edge_tol", 0.45) + part.stitch.pull_comp; ez = P.get("end_zone", 2.0)
    interior = body = 0; cross = 0; body_len = 0.0; ends = []; longest = 0.0
    seg_col = [col_of(((a + c) / 2, (b + d) / 2)) for a, b, c, d in segs]
    for ci, (q, ls) in enumerate(zip(cols, lss)):
        S = [s for s, k in zip(segs, seg_col) if k == ci]; w = q["w"]; L = ls.length
        lo_s, hi_s = (0.0, L) if q["closed"] else (ez, L - ez)
        body_len += max(0.0, hi_s - lo_s)
        for pt in points_of(S):
            s, off = _frame(ls, pt)
            if not (lo_s <= s <= hi_s): continue
            body += 1
            if abs(abs(off) - w / 2) > tol: interior += 1
        for x0, y0, x1, y1 in S:
            longest = max(longest, math.dist((x0, y0), (x1, y1)))
            s0, o0 = _frame(ls, (x0, y0)); s1, o1 = _frame(ls, (x1, y1))
            if lo_s <= (s0 + s1) / 2 <= hi_s and o0 * o1 < 0 and min(abs(o0), abs(o1)) >= w / 2 - tol: cross += 1
        if not q["closed"]:
            for at_start in (True, False):
                E, t, n = end_frame(q["cl"], at_start); h = w / 2
                pts = [np.subtract(p, E) for p in points_of(S)]
                perf = sorted(float(v @ n) for v in pts if abs(v @ t) <= 0.35 and abs(v @ n) <= h + 0.6)
                gaps = np.diff(perf) if len(perf) > 1 else [99.0]
                perf_ok = len(perf) > 1 and perf[0] <= -0.9 * h and perf[-1] >= 0.9 * h and max(gaps) <= 0.8
                capn = []
                for x0, y0, x1, y1 in S:
                    a = np.subtract((x0, y0), E); b = np.subtract((x1, y1), E); d = b - a; Ld = np.linalg.norm(d)
                    if Ld < 0.8 or abs(d @ t) / Ld < 0.94: continue
                    if max(a @ t, b @ t) >= 0.3 and min(a @ t, b @ t) <= -0.3 and abs((a + b) @ n / 2) <= h + 0.4:
                        capn.append(float((a + b) @ n / 2))
                capn.sort(); cg = np.diff(capn) if len(capn) > 1 else [99.0]
                cap_ok = len(capn) >= w / 0.4 and capn and capn[0] <= -0.9 * h and capn[-1] >= 0.9 * h and max(cg) <= 0.6
                ends.append(dict(col=ci, start=at_start, perforated=bool(perf_ok), capped=bool(cap_ok), perf_pts=len(perf), cap_stitches=len(capn)))
    frac = interior / max(body, 1)
    out["satin_only"] = g(frac <= P.get("max_interior_frac", 0.03), value=round(frac, 4), limit=P.get("max_interior_frac", 0.03),
                          note="share of the body's needle points INSIDE the foam (tatami / zigzag underlay / split rows put them there)")
    spc = body_len / max(cross, 1)
    out["density"] = g(cross > 0 and spc <= P.get("max_spacing", 0.30), value=round(spc, 3), limit=P.get("max_spacing", 0.30),
                       note="row spacing = body length / crossing rows read from the file")
    out["ends_closed"] = g(all(e["perforated"] and e["capped"] for e in ends), value=ends, limit="every open end perforated + capped")
    out["row_len"] = g(longest <= ROW_MAX + 1e-6, value=round(longest, 2), limit=ROW_MAX, note="LESSONS B7: no sewn stitch > 7.5 mm")
    return out


# ---------------------------------------------------------------- faux chain (lock-stitch, from the file)
def faux_chain_gates(part, segs):
    from digitize.techniques.run import lines
    P = part.stitch.params; h = P.get("half_w", 0.45); link = P.get("link", 2.5); step = link * (1 - P.get("overlap", 0.3))
    out = {}; ls = [LineString(l) for l in lines(part)]
    pts = points_of(segs)
    if not pts: return dict(sewn=g(False, value=0))
    on = max(min(l.distance(Point(p)) for l in ls) for p in pts)
    out["on_line"] = g(on <= h + 0.2, value=round(on, 3), limit=h + 0.2)
    longest = max(math.dist(s[:2], s[2:]) for s in segs)
    out["short_stitches"] = g(longest <= P.get("max_stitch", 3.0), value=round(longest, 2), limit=P.get("max_stitch", 3.0))
    win_ok = win = 0; gaps = []
    for l in ls:
        fr = [_frame(l, p) for p in pts if l.distance(Point(p)) <= h + 0.25]
        ss = sorted(s for s, _ in fr); gaps.append(max(np.diff([0.0] + ss + [l.length])) if ss else l.length)
        for k in range(int(l.length // step)):
            a, b = k * step, k * step + step
            offs = [o for s, o in fr if a <= s < b]
            win += 1; win_ok += any(o >= 0.6 * h for o in offs) and any(o <= -0.6 * h for o in offs)
    out["reads_as_chain"] = g(win and win_ok / win >= 0.9, value=round(win_ok / max(win, 1), 3), limit=0.9,
                              note="share of link windows with a loop on both sides of the line (a run / bean has none)")
    out["no_gaps"] = g(max(gaps) <= link + 1e-6, value=round(float(max(gaps)), 2), limit=link)
    return out


# ---------------------------------------------------------------- chenille / chain (plan: no machine file yet)
def const_len(paths, L, tol=0.10, closed=False):
    worst = 0.0
    for p in paths:
        d = [math.dist(a, b) for a, b in zip(p, p[1:])]
        if not closed and len(d) > 1: d = d[:-1]               # an open path's last stitch may be shorter
        if d: worst = max(worst, max(abs(x - L) / L for x in d))
    return worst <= tol, round(worst, 4)


def _sample(paths, step=0.4):
    S, idx = [], []
    for k, p in enumerate(paths):
        ls = LineString(p); n = max(2, int(ls.length / step))
        for i in range(n + 1):
            S.append(ls.interpolate(ls.length * i / n).coords[0]); idx.append((k, ls.length * i / n))
    return np.array(S), idx


def chenille_gates(part, d):
    from scipy.spatial import cKDTree
    from digitize.techniques import polys
    s = d["spec"]; out = {}
    ok_m, wm = const_len(d["moss"], s["moss_len"]); ok_c, wc = const_len(d["chain"], s["chain_len"], tol=0.15, closed=True)
    out["const_stitch_len"] = g(ok_m and ok_c, value=dict(moss=wm, chain=wc), limit="moss +-10 %, chain +-15 % (closed loops share the remainder)")
    region = part.geom
    if d["moss"] and not region.is_empty:
        S, idx = _sample(d["moss"]); tree = cKDTree(S)
        yarn = unary_union([LineString(p).buffer(s["spacing"] * 0.6) for p in d["moss"] + d["chain"]])   # a loop ~1.2 x spacing wide
        cov = region.intersection(yarn).area / region.area
        pile = 0
        for i, j in tree.query_pairs(0.55 * s["spacing"]):
            (ki, si), (kj, sj) = idx[i], idx[j]
            if ki != kj or abs(si - sj) > 2.5 * s["spacing"]: pile += 1
        pf = pile / max(len(S), 1)
        out["moss_coverage"] = g(cov >= 0.90, value=round(cov, 3), limit=0.90)
        out["moss_no_pileup"] = g(pf <= 0.05, value=round(pf, 4), limit=0.05, note="moss paths closer than 0.55 x spacing (yarn pile-up)")
    else:
        out["moss_coverage"] = g(False, value=0.0, limit=0.90)
    if s["outline"]:
        rings = [r for q in polys(part.geom.buffer(-s["outline_inset"])) for r in [q.exterior] + list(q.interiors) if r.length >= 3]
        okr = []
        for r in rings:
            c = [p for p in d["chain"] if max(r.distance(Point(x)) for x in p) <= 0.3]
            okr.append(bool(c) and math.dist(c[0][0], c[0][-1]) < 0.05 and sum(LineString(x).length for x in c) >= 0.95 * r.length)
        out["chain_outline"] = g(rings and all(okr), value=okr, limit="every edge ring has a closed chain on it")
    out["head_settings"] = g(isinstance(s["loop_height_mm"], (int, float)) and bool(s["yarn"]),
                             value=dict(loop_height_mm=s["loop_height_mm"], yarn=s["yarn"]), limit="declared")
    return out


def chain_gates(part, d):
    from digitize.techniques.run import lines
    ok, worst = const_len(d["chain"], d["spec"]["chain_len"], tol=0.15)
    ls = [LineString(l) for l in lines(part)]
    off = max((min(l.distance(Point(p)) for l in ls) for c in d["chain"] for p in c), default=99.0)
    return dict(const_stitch_len=g(ok, value=worst, limit=0.15), on_line=g(off <= 0.3, value=round(off, 3), limit=0.3))


def write_chenille_plan(items, path):
    """items: [(part, detail)] -> json (mm paths + head settings), the neutral plan the factory digitiser can read"""
    J = [dict(part=p.id, kind=p.kind, technique=p.technique, thread=p.thread, spec=d["spec"],
              moss=[[[round(x, 3), round(y, 3)] for x, y in q] for q in d["moss"]],
              chain=[[[round(x, 3), round(y, 3)] for x, y in q] for q in d["chain"]]) for p, d in items]
    json.dump(dict(units="mm, garment frame, y down", question=CHENILLE_QUESTION, parts=J), open(path, "w"), indent=None)
    return path


def export_chenille(items, base, prof=None):
    """the chenille machine file. Not guessed: raises until factory.json carries chenille_format (F1 open question)."""
    import factory
    prof = prof or factory.load(); fmt = prof.get("chenille_format")
    ids = [p.id for p, _ in items]
    if not fmt:
        raise FactoryFormatNeeded(f"factory format needed (F1): {len(ids)} chenille / chain-mode part(s) {ids[:6]} have a plan but no "
                                  f"machine file. {CHENILLE_QUESTION} Set factory.json chenille_format once answered; the plan "
                                  f"json (write_chenille_plan) can go to the factory's chenille digitiser meanwhile.")
    raise FactoryFormatNeeded(f"factory format needed (F1): chenille_format {fmt!r} is on file but no writer is built for it yet")


# ---------------------------------------------------------------- previews
def _hex(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _shade(c, k):
    return tuple(int(min(255, max(0, v + (255 - v) * k if k > 0 else v * (1 + k)))) for v in c)


def swatch_png(layers, bounds, png, ppm=16.0, bg="#D7C29C", title=None):
    """layers in draw order: ("foam", geom, hex) | ("stitch", segs, hex) | ("moss", paths, hex, loop_h) |
    ("chain", paths, hex). Thread drawn 0.4 mm wide with a darker edge; moss = overlapping loops; chain = links."""
    from PIL import Image, ImageDraw
    x0, y0, x1, y1 = bounds; W, H = int((x1 - x0) * ppm), int((y1 - y0) * ppm) + (24 if title else 0)
    im = Image.new("RGB", (W, H), _hex(bg)); d = ImageDraw.Draw(im); oy = 24 if title else 0
    T = lambda p: ((p[0] - x0) * ppm, (p[1] - y0) * ppm + oy)
    for L in layers:
        kind, data, col = L[0], L[1], _hex(L[2])
        if kind == "foam":
            from digitize.techniques import polys
            for q in polys(data):
                d.polygon([T(c) for c in q.exterior.coords], fill=col)
                for r in q.interiors: d.polygon([T(c) for c in r.coords], fill=_hex(bg))
        elif kind == "stitch":
            tw = max(1, int(0.40 * ppm))
            for s in data: d.line([T(s[:2]), T(s[2:])], fill=_shade(col, -0.35), width=tw + 2)
            for s in data: d.line([T(s[:2]), T(s[2:])], fill=col, width=tw)
            for s in data:
                m0 = ((3 * s[0] + s[2]) / 4, (3 * s[1] + s[3]) / 4); m1 = ((s[0] + 3 * s[2]) / 4, (s[1] + 3 * s[3]) / 4)
                d.line([T(m0), T(m1)], fill=_shade(col, 0.35), width=max(1, tw // 3))
        elif kind == "moss":
            r = max(2, int((0.25 * L[3] + 0.4) * ppm / 2))
            for p in data:
                for a, b in zip(p, p[1:]):
                    for f in (0.0, 0.5):
                        c = T((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
                        d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=col, outline=_shade(col, -0.4))
                        d.ellipse([c[0] - r * 0.45, c[1] - r * 0.6, c[0] + r * 0.15, c[1] - r * 0.1], fill=_shade(col, 0.3))
        elif kind == "chain":
            hw = 0.55 * ppm
            for p in data:
                for a, b in zip(p, p[1:]):
                    A, B = np.array(T(a)), np.array(T(b)); v = B - A; n = np.linalg.norm(v)
                    if n < 1e-6: continue
                    u = v / n; nn = np.array([-u[1], u[0]])
                    oval = [tuple(A + u * (n * (0.5 - 0.6 * math.cos(t))) + nn * hw * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 18)]
                    d.polygon(oval, outline=_shade(col, -0.45), fill=col)
                    d.line([tuple(A + u * n * 0.3), tuple(A + u * n * 0.75)], fill=_shade(col, -0.25), width=max(1, int(0.12 * ppm)))
    if title: d.text((6, 5), title, fill=(30, 30, 30))
    im.save(png); return png
