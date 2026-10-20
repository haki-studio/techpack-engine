"""Radial-floret exemption for the 8 mm chaos gate (ENGINE_PLAN M4c; PR #10 review, option (a) with a guard).

Florets are radial by the founder-approved playbook ("radial florets", DIGITIZING_PRINCIPLES rule 4): an 8 mm tile over
two 5 mm florets holds rays in every direction, so qa.direction_match calls it chaotic (R < 0.55) although every stitch
is exactly where the playbook puts it. This module lets such a tile out of the chaos count ONLY when the file proves it:

  1. share     >= min_radial_share (0.70) of the tile's VISIBLE stitch length (stitches >= 0.6 mm, the same filter as
               direction_match) belongs to ELIGIBLE radial parts, and
  2. adherence >= min_adherence_pct (85 %) of those parts' visible stitches in THIS tile lie within max_dev_deg (15) of
               the ray from their own part's centre (per tile, not the plan-wide radial_adherence figure), and
  3. eligible  = DirSpec mode "radial", a centre (meta["centre"]), and FLORET SIZE: the farthest outline point is at
               most floret_r_max_mm (4 mm) from the centre. A large radial-mode blob stays under the chaos rule.

Numbers: rules/house.yaml `chaos_radial_exemption` (DEFAULTS below when absent). The chaos threshold (5 %) is NOT
touched: the gate reads chaos AFTER exemption over the SAME tile count; the raw chaos figure stays in the row and on the
panel. Exempted tiles leave every direction bucket and go to their own "radial" bucket, so they never count as
independent OK (A24): a radial tile is judged by adherence, not by the reference.

  ex = exempt(dm, vis_local, vis_labels, plan.parts, cfg, ppm)   -> dict (see exempt)
  by_source = rebucket(by_source, ex)                             -> direction_by_source with a "radial" bucket
"""
import math

DEFAULTS = dict(min_radial_share=0.70, min_adherence_pct=85.0, floret_r_max_mm=4.0, max_dev_deg=15.0, min_len=0.6, centre_mm=0.9)


def config(rb=None):
    d = dict(DEFAULTS)
    if rb is not None: d.update((rb.data.get("chaos_radial_exemption") or {}))
    return d


def floret_radius(p):
    """the farthest outline point from the part's centre (mm); None without a centre"""
    c = (p.meta or {}).get("centre")
    if not c: return None
    g = p.geom; polys = [g] if g.geom_type == "Polygon" else list(getattr(g, "geoms", []))
    r = 0.0
    for q in polys:
        for x, y in q.exterior.coords: r = max(r, math.hypot(x - c[0], y - c[1]))
    return r


def eligible(parts, cfg):
    """{part id: centre} for radial-mode parts with a centre and floret size; plus the radial parts left out and why"""
    ok, out = {}, []
    for p in parts:
        if p.dir.mode != "radial": continue
        r = floret_radius(p)
        if r is None: out.append(dict(part=p.id, why="no centre"))
        elif r > cfg["floret_r_max_mm"]: out.append(dict(part=p.id, why=f"radius {r:.1f} mm > {cfg['floret_r_max_mm']} (not floret size)"))
        else: ok[p.id] = tuple(p.meta["centre"])
    return ok, out


def _key(x, y, ppm, T):
    return int(y * ppm // T), int(x * ppm // T)


def exempt(dm, segs, labels, parts, cfg=None, ppm=12.0, origin=(0.0, 0.0)):
    """dm: qa.direction_match result (tile centres in crop-local mm). segs: the VISIBLE stitch segments (qa.visible_segments
    of the written file), labels: their part ids, in garment mm; origin = the crop's top-left (garment mm) so a segment
    maps to the same tile grid as dm. parts: the plan's parts. Returns dict(tiles, chaos_raw, pct_chaos_raw, exempt
    (list of tile centres), n_exempt, chaos_after, pct_chaos_after, candidates_refused [{at_mm, share, adherence, why}],
    eligible_parts, radial_parts_not_eligible, conditions)."""
    cfg = dict(DEFAULTS, **(cfg or {}))
    tile = float(dm.get("tile_mm", 8.0)); T = int(round(tile * ppm)); x0, y0 = origin
    cen, not_el = eligible(parts, cfg)
    tot, rad, n_adh, w_adh = {}, {}, {}, {}
    for s, pid in zip(segs, labels):
        a, b, c, d = s[0] - x0, s[1] - y0, s[2] - x0, s[3] - y0
        L = math.hypot(c - a, d - b)
        if L < cfg["min_len"]: continue
        mx, my = (a + c) / 2, (b + d) / 2; k = _key(mx, my, ppm, T)
        tot[k] = tot.get(k, 0.0) + L
        if pid not in cen: continue
        rad[k] = rad.get(k, 0.0) + L
        cx, cy = cen[pid][0] - x0, cen[pid][1] - y0
        if math.hypot(mx - cx, my - cy) < cfg["centre_mm"]: continue
        ang = math.degrees(math.atan2(d - b, c - a)) % 180; ray = math.degrees(math.atan2(my - cy, mx - cx)) % 180
        dd = abs(ang - ray) % 180; dd = min(dd, 180 - dd)
        n_adh[k] = n_adh.get(k, 0) + 1; w_adh[k] = w_adh.get(k, 0) + (dd <= cfg["max_dev_deg"])
    ex, refused = [], []
    for r in dm["fail_chaos"]:
        cx, cy = r["at_mm"]; k = (int(cy // tile), int(cx // tile))
        share = rad.get(k, 0.0) / max(tot.get(k, 0.0), 1e-9)
        adh = 100.0 * w_adh.get(k, 0) / n_adh[k] if n_adh.get(k) else None
        why = []
        if share < cfg["min_radial_share"]: why.append(f"radial share {share:.2f} < {cfg['min_radial_share']}")
        if adh is None: why.append("no radial stitch off the centre to judge")
        elif adh < cfg["min_adherence_pct"]: why.append(f"adherence {adh:.0f} % < {cfg['min_adherence_pct']}")
        if why:
            if share > 0: refused.append(dict(at_mm=r["at_mm"], share=round(share, 2), adherence=None if adh is None else round(adh, 1), why="; ".join(why)))
        else:
            ex.append(dict(at_mm=r["at_mm"], share=round(share, 2), adherence=round(adh, 1)))
    n = dm["tiles"]; raw = len(dm["fail_chaos"]); after = raw - len(ex)
    return dict(tiles=n, chaos_raw=raw, pct_chaos_raw=round(100 * raw / max(n, 1), 1), exempt=ex, n_exempt=len(ex),
                chaos_after=after, pct_chaos_after=round(100 * after / max(n, 1), 1), candidates_refused=refused[:60],
                n_refused=len(refused), eligible_parts=len(cen), radial_parts_not_eligible=not_el[:40],
                n_radial_not_eligible=len(not_el), conditions=cfg)


def rebucket(by_source, ex):
    """move the exempted chaos tiles out of whatever bucket their top part put them in (they were counted there as chaos)
    into their own "radial" bucket: never independent OK, and the other buckets' figures no longer carry them.
    by_source: audit.direction_by_source result; the exempt tiles' original buckets are given by ex["exempt"][i]["bucket"]
    (set by tag_buckets)."""
    out = {k: dict(v) for k, v in by_source.items()}
    for t in ex["exempt"]:
        b = t.get("bucket")
        if b is None or b not in out: raise ValueError(f"exempt tile {t['at_mm']} has no source bucket: call tag_buckets first")
        o = out[b]; o["tiles"] -= 1; o["chaos"] -= 1
        o["pct_ok"] = round(100 * o["ok"] / max(1, o["tiles"]), 1); o["pct_chaos"] = round(100 * o["chaos"] / max(1, o["tiles"]), 1)
        o["radial_exempt_moved_out"] = o.get("radial_exempt_moved_out", 0) + 1
    if ex["exempt"]:
        out["radial"] = dict(tiles=len(ex["exempt"]), ok=0, dev=0, chaos=0, exempt=len(ex["exempt"]), pct_ok=0.0, pct_chaos=0.0,
                             note="chaos tiles over floret-size radial parts, judged by per-tile radial adherence (gates_radial)")
    return out


def tag_buckets(ex, top_part_at, rb=None, peers=None):
    """record, on each exempt tile, the direction_by_source bucket its top part gave it"""
    from digitize import audit
    for t in ex["exempt"]:
        p = top_part_at(t["at_mm"]); t["bucket"] = audit.bucket_of(p, rb, peers) if p is not None else "bare"
    return ex
