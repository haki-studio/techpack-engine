"""Building splitter (ENGINE_PLAN M3a; motif playbook "Buildings: wall tatami; eave satin; roof down-slope with bean tile
lines; windows as satin bands; one angle per plane; build walls -> roofs bottom-up, studs last").

One zone WINDOW = one building (zones_BK.json: hand-authored windows, the silhouette inside is traced). Per window:
  1. roles from the tone trace (run yaml `building.roles`: palette tones that are roof / wall / member / ornament);
     pixels of other tones (foliage, blossom) are not used and go back to the zones below.
  2. roofs: the roof-role pixels opened by roof_open_mm (thin blue frames are not roofs), stacked tiers cut apart where a
     row is mostly not roof (building_fit.split_tiers), components >= min_roof_mm2. Each is fitted (building_fit.fit_roof):
     eave line along its unoccluded bottom edge, ridge, hip planes from the unoccluded top / side edges. Depth (rule 3):
     a tier under near_tier_rel x the zone's largest tier (house.yaml roof params) is FAR: one plane with rows along its
     eave and no tile lines; a NEAR tier gets planes down the slope (hips fan) and bean tile lines down the slope in its
     second roof tone. Every visible eave gets a satin band across it (roof's other tone, else the trim colour). Tiers
     sew bottom-up.
  3. walls: building pixels that are not roof, components >= min_wall_mm2, one tatami per plane. Ground colour = the mean
     of the face's brightest wall_bright_frac of pixels, nearest thread (the tone trace calls plaster "bark"); square to
     the eave of the roof above (rule 3: along it under a far roof, across it under a near one; 0 deg without a roof).
  4. on each wall, details (member / ornament / roof-tone pixels, or dark_dlum darker than the ground): compact ones ->
     window BANDS (a row of windows merged, along the courses, satin across, aspect >= band_aspect), long thin ones ->
     members satin across their width, frames (timber grids) split into rails and posts. Off the walls: gold ornaments
     -> studs (dot 1-1.5 mm, never touching), long ones members. Anything under a rule 9 minimum (a single window too
     small for a band, a member too short for a stroke) is listed in report["suggest"] (plan meta building_suggest).
  5. leftover building pixels within reach_mm of a plane join it (rule 1: no specks).
  6. FIDELITY FIRST: satin features are kept where the art has them; a stack cost on an underlap is reported (the
     sequencer cuts to <= 2 layers). seam_keep_mm (default off) would clip them clear of underlaps instead.
  7. rule 3 separation among the building's own walls / roofs (recorded turns <= 25 deg, audited); planes named in
     another part's seq_after are kept out of merge_specks (protect_referenced).
z inside the zone: walls z, roofs z+0.10 (+0.01 per tier up), eaves z+0.30, tile lines z+0.40, windows / members z+0.50,
studs z+0.60: sequence.py's z-DAG then sews walls -> roofs bottom-up -> eaves -> tile lines -> windows -> studs last.
M4g sequencing hints (optional meta, ignored by the M1 sequencer): `group` = the building, `seq_after` = the plane(s) a
tile line / eave lies on.
Every direction is a RULE on the fitted geometry (building_fit), never the reference grain (LESSONS A24); digitize.audit
re-derives it from the fitted points stored in the part. Small deliberate parts carry meta keep_small (no speck merge)
and min_fragment_mm2 (a 1.5 mm stud is not a fragment): the two sequence.py hooks M3a added."""
import math
import numpy as np
from scipy import ndimage as ndi
from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from digitize.schema import Part, DirSpec
from digitize.extract import building_fit as BF

DEFAULTS = dict(roof_open_mm=1.2, min_roof_mm2=30.0, min_roof_w_mm=6.0, min_roof_h_mm=2.0, min_wall_mm2=25.0,
                eave_w_mm=1.8, eave_tol_mm=1.0, tile_mm=3.0, tile_inset_mm=1.3, tile_min_share=0.08,
                feat_min_mm2=1.5, window_max_mm=8.0, member_aspect=2.5, window_gap_mm=3.0, window_min_len_mm=3.0,
                stud_max_mm=2.6, stud_pitch_mm=2.0, max_studs=4, reach_mm=1.5, ridge_tol_mm=1.0, ridge_tol_frac=0.25,
                min_plane_mm=4.0, min_hip_slope_deg=10.0, small_fragment_mm2=0.5, tier_gap_frac=0.25, tier_full_frac=0.5,
                min_free_eave=0.5, max_hip_frac=0.45, band_aspect=3.0, seam_keep_mm=None, wall_bright_frac=0.15,
                dark_dlum=60.0, member_min_len_mm=3.0)
SEWN = 0.25          # a column satin reads back ~0.25 mm wider than its centreline width (pull comp both sides + 0.1 grid)
Z = dict(wall=0.0, roof=0.10, eave=0.30, roof_tile_line=0.40, window=0.50, member=0.50, stud=0.60)


def _cfg(ctx):
    d = dict(DEFAULTS); d.update(ctx.cfg.get("building", {}) or {})
    if not d.get("roles"):
        raise ValueError("building splitter: run yaml `building.roles` must name the palette tones of roof / wall / member / "
                         "ornament (a role list is a design decision, never guessed)")
    return d


def _idx(ev, keys): return [ev.keys.index(k) for k in keys if k in ev.keys]


def _counts(ctx, m):
    v = ctx.thread_lab[m]; v = v[v >= 0]
    c = np.bincount(v, minlength=len(ctx.threads)) if len(v) else np.zeros(len(ctx.threads), int)
    return c


def _poly(ev, m):
    gs = ev.polys(m, min_mm2=0.3)
    if not gs: return None
    return gs[0] if len(gs) == 1 else unary_union(gs)


def _part(ctx, zone, kind, geom, thread, z, angle, note, **meta):
    meta.setdefault("splitter", "building")
    if kind in ("eave", "window", "member"): meta.setdefault("caps", ["flat", "flat"])   # square member ends
    if "building" in meta: meta.setdefault("group", f"{zone['id']}.b{meta['building']}")   # M4g hint: finish one building per stop
    return Part(id=ctx.new_id(zone["id"]), kind=kind, geom=geom, thread=thread, z=round(z, 3),
                dir=DirSpec(angle, source="rule", note=note), zone=zone["id"], meta=meta)


def split(ctx, zone, z, claim):
    ev = ctx.ev; sc = _cfg(ctx); R = sc["roles"]; parts = []; used = np.zeros_like(claim)
    if not claim.any(): return parts, used
    rb = ctx.rb; rprm = dict(rb.rule("roof").get("params", {})); rel = rprm.get("near_tier_rel")
    hip_min, hip_max = float(rprm.get("hip_min_sep", 20.0)), float(rprm.get("hip_max_sep", 45.0))
    roof_t = np.isin(ev.tone, _idx(ev, R.get("roof", [])))
    orn_t = np.isin(ev.tone, _idx(ev, R.get("ornament", [])))
    mem_t = np.isin(ev.tone, _idx(ev, R.get("member", [])))
    bld_t = np.isin(ev.tone, _idx(ev, sum((list(v) for v in R.values()), [])))
    lum = ev.rgb @ np.array([0.299, 0.587, 0.114])
    report = dict(windows_too_small=0, eaves_skipped=0, tiles_skipped=0, studs=0, leftover_px=0, suggest=[])
    # ---------------------------------------------------------------- pass 1: every roof tier of the zone (depth is relative)
    wins = []
    for wi, win in enumerate(zone.get("geoms") or [None]):
        wm = claim & (ev.mask(win) if win is not None else True)
        bld = wm & bld_t
        if bld.sum() < sc["min_wall_mm2"] * ev.ppm ** 2: continue
        rm = ndi.binary_opening(wm & roof_t, BF.disk(ev, sc["roof_open_mm"]))
        rm = ndi.binary_closing(rm, BF.disk(ev, 1.0)) & bld
        rm = BF.split_tiers(rm, sc["tier_gap_frac"], sc["tier_full_frac"])     # stacked tiers joined by a blue frame: cut apart
        free = wm if win is not None else claim                         # the window edge occludes like a blossom does
        L, n = ndi.label(rm); roofs = []
        for i in range(1, n + 1):
            comp = L == i; a = comp.sum() / ev.ppm ** 2
            if a < sc["min_roof_mm2"]: continue
            cols = np.nonzero(comp.any(0))[0]; rows = np.nonzero(comp.any(1))[0]
            if len(cols) / ev.ppm < sc["min_roof_w_mm"] or len(rows) / ev.ppm < sc["min_roof_h_mm"]: continue
            if _counts(ctx, comp).sum() == 0: continue
            roofs.append((comp, BF.fit_roof(ev, comp, sc, free=free)))
        roofs.sort(key=lambda t: -t[1]["eave_y"])                       # bottom tier first (largest eave y on the garment)
        wins.append((wi, wm, bld, roofs))
    hs = [BF.tier_height(f["eave_pts"], f["top_pts"]) for _, _, _, rr in wins for _, f in rr]
    hs = [h for h in hs if h is not None]
    h_ref = max(hs) if hs else None                                   # = building_fit.zone_tier_ref over the roof parts
    for wi, wm, bld, roofs in wins:
        lab = np.zeros(claim.shape, np.int32); owners = [None]          # pixel -> index into owners (plane / wall parts)
        pending = []                                                     # satin features: (kind, cl, w, thread, note, meta)
        roof_info = []
        for rank, (comp, fit) in enumerate(roofs):
            zr = z + Z["roof"] + 0.01 * min(rank, 9)
            eave_cl, eave_g = BF.eave_band(ev, comp, fit, sc["eave_w_mm"], sc["eave_tol_mm"]) if fit["eave_visible"] else (None, None)
            plane_threads = []
            far = BF.is_far(fit["eave_pts"], fit["top_pts"], rel, h_ref)
            if far:                                                      # rule 9 + rule 3: a far tier is ONE plane along its eave
                fit["planes"] = [dict(side=0, c0=int(fit["cols"][0]), c1=int(fit["cols"][-1]) + 1, hip_pts=None)]
            for pl in fit["planes"]:
                pm = comp.copy(); pm[:, :pl["c0"]] = False; pm[:, pl["c1"]:] = False
                if pm.sum() < 4: continue
                cnt = _counts(ctx, pm)
                if cnt.sum() == 0: continue
                th = ctx.threads[int(cnt.argmax())]
                ang = BF.roof_angle(fit["eave_pts"], pl["hip_pts"], pl["side"], hip_min, hip_max, far=far)
                side = {-1: "left hip", 0: "front", 1: "right hip"}[pl["side"]]
                how = (f"FAR tier ({fit['height_mm']:.1f} mm < {rel} x {h_ref:.1f} mm): along the eave (rule 3 depth)" if far
                       else "down the slope")
                owners.append(dict(kind="roof", thread=th, z=zr, angle=ang, note=f"{how} ({side}), eave {fit['eave_deg']:+.1f} deg",
                                   meta=dict(eave_pts=fit["eave_pts"], top_pts=fit["top_pts"], hip_pts=pl["hip_pts"], side=pl["side"],
                                             building=wi, tier=rank, far=far, tier_h_mm=fit["height_mm"],
                                             tier_h_ref_mm=round(h_ref, 3) if h_ref else None),
                                   cnt=cnt))
                lab[pm & (lab == 0)] = len(owners) - 1
                plane_threads.append((len(owners) - 1, th, cnt))
            roof_info.append(dict(fit=fit, comp=comp, rank=rank, eave_cl=eave_cl, eave_g=eave_g, planes=plane_threads, far=far))
        roof_mask = lab > 0
        # ---------------------------------------------------------------- walls + their features
        wl = bld & ~roof_mask
        Lw, nw = ndi.label(wl); feats = []
        for i in range(1, nw + 1):
            comp = Lw == i
            if comp.sum() < sc["min_wall_mm2"] * ev.ppm ** 2: continue
            # the wall's GROUND colour is read from the face's own pixels: the mean colour of its brightest wall_bright_frac
            # (plaster between the frames and windows), matched to the nearest thread (CIEDE2000). The tone trace alone
            # called the castle's plaster "bark tan" and gave the temple a red wall (its timber frame is the most
            # frequent tone there); dark outlines, red timber and gold are the wall's DETAILS, not its ground.
            ti, gl = _wall_ground(ctx, comp & ~(mem_t | orn_t | roof_t), lum, sc)
            if ti is None: continue
            th = ctx.threads[ti]
            rr, cc = np.nonzero(comp); cx, cy = BF.px_mm(ev, rr.mean(), cc.mean()); x0w, _ = BF.px_mm(ev, 0, cc.min()); x1w, _ = BF.px_mm(ev, 0, cc.max())
            above = [ri for ri in roof_info if ri["fit"]["eave_y"] <= cy + 1.0 and min(x1w, ri["fit"]["x1"]) - max(x0w, ri["fit"]["x0"]) > 0.3 * (x1w - x0w)]
            ra = max(above, key=lambda ri: ri["fit"]["eave_y"]) if above else None
            eave_pts = ra["fit"]["eave_pts"] if ra else None; top_pts = ra["fit"]["top_pts"] if ra else None
            ang = BF.course_angle(eave_pts, top_pts, rel, h_ref)
            near = ra is not None and abs(BF.axial_diff(ang, BF.eave_angle(eave_pts))) > 45
            owners.append(dict(kind="wall", thread=th, z=z + Z["wall"], angle=ang,
                               note=(f"{'across' if near else 'along'} the courses ({'under a near' if near else 'under a far'} roof, tier {ra['rank']})"
                                     if ra else "no roof above: 0 deg"),
                               meta=dict(eave_pts=eave_pts, top_pts=top_pts, building=wi, ground_lum=round(gl, 1)), cnt=None))
            wid = len(owners) - 1; lab[comp & (lab == 0)] = wid
            course = BF.eave_angle(eave_pts) % 180.0 if eave_pts else 0.0
            # details: member / ornament / roof-tone pixels and anything much darker than the ground (frames, windows)
            fm = comp & ((mem_t | orn_t | roof_t) | (lum < gl - sc["dark_dlum"])) & (ctx.thread_lab != ti) & (ctx.thread_lab >= 0)
            Lf, nf = ndi.label(fm)
            for j in range(1, nf + 1):
                f = Lf == j
                if f.sum() < sc["feat_min_mm2"] * ev.ppm ** 2: continue
                feats += _features(ctx, f, wid, course, sc, role=bool((f & (mem_t | orn_t | roof_t)).sum() * 2 >= f.sum()))
        # windows (compact) -> bands per row; members (long, thin) -> satin across
        wins_f = [f for f in feats if f["is_win"]]; mems = [f for f in feats if not f["is_win"]]
        for grp in _rows(wins_f, sc["window_gap_mm"]):
            band = _band(grp, sc)
            if band is None:                                             # rule 9: too small for a band -> SUGGEST, never silent
                report["windows_too_small"] += len(grp)
                for f in grp:
                    c = f["geom"].centroid
                    report["suggest"].append(dict(kind="window", at=[round(c.x, 1), round(c.y, 1)], size_mm=[round(f["L"], 1), round(f["S"], 1)],
                                                  thread=f["thread"], building=wi, why="single window too small for a satin band (rule 9)"))
                continue
            cl, w, th = band
            pending.append(("window", cl, w, th, f"window band of {len(grp)}, satin across", dict(n_windows=len(grp))))
        for f in mems:
            w = _member_w(f["geom"].area, f["L"], sc)
            if w is None:
                c = f["geom"].centroid
                report["suggest"].append(dict(kind="member", at=[round(c.x, 1), round(c.y, 1)], size_mm=[round(f["L"], 1), round(f["S"], 1)],
                                              thread=f["thread"], building=wi, why="member too short for a 1 mm satin stroke (rule 9)"))
                continue
            pending.append(("member", f["axis"], w, f["thread"], "member, satin across its width", {}))
        # ---------------------------------------------------------------- ornaments off the walls: studs / members
        om = wm & orn_t & ~(lab > 0)
        Lo, no = ndi.label(om)
        for j in range(1, no + 1):
            o = Lo == j; A = o.sum() / ev.ppm ** 2
            if A < 0.6: continue
            g = _poly(ev, o)
            if g is None: continue
            th = ctx.threads[int(_counts(ctx, o).argmax())] if _counts(ctx, o).sum() else None
            if th is None: continue
            ax, Ln, Sh = BF.rect_axis(g); eqd = 2 * math.sqrt(A / math.pi)
            w = _member_w(A, Ln, sc) if ax is not None else None
            if ax is not None and Ln / max(Sh, 1e-6) >= sc["member_aspect"] and 1.0 <= Sh <= 7.0 and Ln >= 2.5 and w is not None:
                pending.append(("member", ax, w, th, "ornament member, satin across", {})); continue   # its pixels join the planes
            if eqd <= sc["stud_max_mm"] or ax is None: pts = [(g.centroid.x, g.centroid.y)]
            else:
                pitch = max(sc["stud_pitch_mm"], float(rb.rule("stud").get("params", {}).get("max_d", 1.5)) + 0.5)   # studs never touch (rule 3)
                k = max(1, min(sc["max_studs"], int(math.dist(ax[0], ax[1]) // pitch))); (xa, ya), (xb, yb) = ax   # centres L / k >= pitch apart
                pts = [(xa + (xb - xa) * (i + 0.5) / k, ya + (yb - ya) * (i + 0.5) / k) for i in range(k)]
            sd = rb.rule("stud").get("params", {})
            for (x, y) in pts:
                d_art = min(eqd, sc["stud_max_mm"])
                nd = min(float(sd.get("max_d", 1.5)), max(float(sd.get("min_d", 1.0)), round(d_art - 0.2, 3)))
                parts.append(_part(ctx, zone, "stud", Point(x, y).buffer(nd / 2.0, 16), th, z + Z["stud"], float(rb.rule("stud")["dir"]),
                                   "stud (rule 9: 1-1.5 mm)", knots=[[round(x, 3), round(y, 3), nd, float(rb.rule("stud")["dir"])]],
                                   art_d=round(eqd, 3), building=wi, keep_small=True, min_fragment_mm2=sc["small_fragment_mm2"]))
                report["studs"] += 1
            used |= o
        # ---------------------------------------------------------------- leftover building pixels join the nearest plane
        left = bld & (lab == 0) & ~used
        if left.any() and (lab > 0).any():
            dist, (ii, jj) = ndi.distance_transform_edt(lab == 0, return_indices=True)
            near = left & (dist <= sc["reach_mm"] * ev.ppm)
            lab[near] = lab[ii[near], jj[near]]
            report["leftover_px"] += int((left & ~near).sum())
        # ---------------------------------------------------------------- satin features
        # FIDELITY FIRST (founder): every window band / member / trim is kept where the art has it; the stack cost on an
        # underlap (a 1-2 mm satin cuts nothing under it) is reported, and sequencing cuts the plan to <= 2 layers (M4g).
        # seam_keep_mm (default None = off) restores the old clearance: centrelines clipped clear of lower borders.
        zk = np.array([0.0] + [o["z"] for o in owners[1:]])
        for kind, cl, w, th, note, extra in pending:
            cl2 = cl
            if sc.get("seam_keep_mm") is not None:
                for _ in range(3):                                      # a shorter band is narrower (aspect >= band_aspect)
                    cl2 = _clear_cl(ev, lab, zk, cl, w / 2.0 + 0.1, w / 2.0 + sc["seam_keep_mm"])
                    if cl2 is None or math.dist(cl2[0], cl2[-1]) >= sc["band_aspect"] * (w + SEWN): break
                    w = math.dist(cl2[0], cl2[-1]) / sc["band_aspect"] - SEWN
                    if w < 1.0: cl2 = None; break
                if cl2 is None or math.dist(cl2[0], cl2[-1]) < sc["band_aspect"] * (w + SEWN):
                    report[f"{kind}s_seam_dropped"] = report.get(f"{kind}s_seam_dropped", 0) + 1; continue
            parts.append(_part(ctx, zone, kind, LineString(cl2).buffer(w / 2.0, cap_style=2), th, z + Z[kind], BF.across_angle(cl2), note,
                               cl=[list(c) for c in cl2], w=round(w, 3), building=wi, keep_small=True,
                               min_fragment_mm2=sc["small_fragment_mm2"], **extra))
        # ---------------------------------------------------------------- planes -> parts; eaves + tile lines per roof
        pid_of = {}
        for k in range(1, len(owners)):
            o = owners[k]; m = lab == k
            g = _poly(ev, m)
            if g is None: continue
            parts.append(_part(ctx, zone, o["kind"], g, o["thread"], o["z"], o["angle"], o["note"], **o["meta"]))
            pid_of[k] = parts[-1]; used |= m
        for ri in roof_info:
            fit = ri["fit"]
            for k, th, cnt in ri["planes"]:
                p = pid_of.get(k)
                if p is None: continue
                alt = [ctx.threads[t] for t in np.argsort(-cnt) if cnt[t] >= sc["tile_min_share"] * cnt.sum() and ctx.threads[t] != th
                       and ctx.threads[t] in _role_threads(ctx, R.get("roof", []))]
                if p.meta.get("far"): report["tiles_far"] = report.get("tiles_far", 0) + 1; continue   # far tiers: rows along the eave, no tile rows across them
                body = p.geom.difference(ri["eave_g"]) if ri["eave_g"] is not None else p.geom
                line = BF.tile_lines(body, p.dir.angle, sc["tile_mm"], sc["tile_inset_mm"]) if alt else None
                if not line or len(line) < 2: report["tiles_skipped"] += 1; continue
                parts.append(_part(ctx, zone, "roof_tile_line", LineString(line).buffer(0.3), alt[0], z + Z["roof_tile_line"], p.dir.angle,
                                   "tile rows down the slope (bean)", line=[list(c) for c in line], seq_after=[p.id], eave_pts=p.meta["eave_pts"],
                                   top_pts=p.meta["top_pts"], hip_pts=p.meta["hip_pts"], side=p.meta["side"], plane=p.id, building=wi,
                                   keep_small=True, min_fragment_mm2=sc["small_fragment_mm2"]))
            if ri["eave_cl"] is None: report["eaves_skipped"] += 1; continue   # eave hidden (occluded / out of the window)
            em = ev.mask(ri["eave_g"]) & ri["comp"]; cnt = _counts(ctx, em)
            front = [th for k, th, _ in ri["planes"] if owners[k]["meta"]["side"] == 0]
            order = [ctx.threads[t] for t in np.argsort(-cnt) if cnt[t] > 0 and ctx.threads[t] not in front]
            if not order:                                                # the eave edge shows no second tone: the trim colour
                order = [t for t in _role_threads(ctx, R.get("ornament", [])) if t not in front]
            if not order: report["eaves_skipped"] += 1; continue
            cl = ri["eave_cl"]
            parts.append(_part(ctx, zone, "eave", ri["eave_g"], order[0], z + Z["eave"], BF.across_angle(cl), "eave, satin across",
                               cl=[list(c) for c in cl], w=sc["eave_w_mm"], eave_pts=fit["eave_pts"], building=wi, tier=ri["rank"],
                               seq_after=[pid_of[k].id for k, _, _ in ri["planes"] if k in pid_of],
                               keep_small=True, min_fragment_mm2=sc["small_fragment_mm2"]))
    protect_referenced(parts)
    # rule 3 among the building's own planes (walls, roofs): recorded turns, audited
    from digitize import direction as DR
    sep = tuple(ctx.rb.principles["neighbour_sep_deg"])
    DR.separate(parts, sep=sep, kinds={"wall", "roof"})
    ctx.building_report = report
    print(f"    building {zone['id']}: " + ", ".join(f"{k} {sum(1 for p in parts if p.kind == k)}" for k in Z) +
          f"; h_ref {h_ref}; " + str({k: (len(v) if isinstance(v, list) else v) for k, v in report.items()}))
    return parts, used


def protect_referenced(parts):
    """a part another part names in seq_after (a roof plane under its tile lines / eave) must survive merge_specks, or
    the hint names a part that no longer exists (M4g raises HintError on an unknown id): it gets meta keep_small"""
    ref = {i for p in parts for i in (p.meta.get("seq_after") or [])}
    for p in parts:
        if p.id in ref: p.meta["keep_small"] = True; p.meta["seq_referenced"] = True
    return ref


def _wall_ground(ctx, comp, lum, sc):
    """(thread index, ground luminance) of a wall face: the mean colour of its brightest wall_bright_frac of pixels,
    nearest thread by CIEDE2000 among the run's threads"""
    from digitize.extract import evidence as EV
    ev = ctx.ev; L = lum[comp]
    if not len(L): return None, None
    cut = np.quantile(L, 1.0 - sc["wall_bright_frac"]); sel = comp & (lum >= cut)
    rgb = ev.rgb[sel].mean(0); gl = float(lum[sel].mean())
    labs = EV.to_lab(np.array([[EV.hex_rgb(ev.hex[ev.keys.index(t)]) for t in ctx.threads]], float))[0]
    me = EV.to_lab(rgb[None, None, :])[0, 0]
    d = EV.delta_e(np.broadcast_to(me, labs.shape), labs)
    return int(np.argmin(d)), gl


def _features(ctx, f, wid, course, sc, role=True):
    """one detail component inside a wall -> [feature]: compact = window; long and thin = member; a frame (a red timber
    grid, a blue lattice) is split into its rails (opened along the courses) and posts (opened across them), each a
    member when it is a stroke. Members come from the member / ornament / roof roles only (role=True): a dark component
    that is not compact is the render's outline shading, not timber, and stays wall."""
    ev = ctx.ev; out = []
    def mk(mask):
        g = _poly(ev, mask)
        if g is None: return None
        ax, Ln, Sh = BF.rect_axis(g)
        if ax is None: return None
        return dict(mask=mask, geom=g, axis=ax, L=Ln, S=Sh, wall=wid, course=course,
                    thread=ctx.threads[int(_counts(ctx, mask).argmax())] if _counts(ctx, mask).sum() else None)
    d = mk(f)
    if d is None or d["thread"] is None: return out
    asp = d["L"] / max(d["S"], 1e-6)
    if d["L"] <= sc["window_max_mm"] and asp < sc["member_aspect"]:
        d["is_win"] = True; return [d]
    if not role: return out
    if asp >= sc["member_aspect"] and 0.8 <= d["S"] <= 7.0:
        d["is_win"] = False; return [d]
    n = max(3, int(round(sc["member_min_len_mm"] * ev.ppm)))           # a frame: rails along the courses, posts across
    a = math.radians(course)
    for ang in (a, a + math.pi / 2):
        se = np.zeros((2 * n + 1, 2 * n + 1), bool)
        for t in np.linspace(-n, n, 4 * n + 1):
            se[int(round(n + t * math.sin(ang))), int(round(n + t * math.cos(ang)))] = True
        op = ndi.binary_opening(f, se)
        Lp, k = ndi.label(op)
        for i in range(1, k + 1):
            m = Lp == i
            if m.sum() < sc["feat_min_mm2"] * ev.ppm ** 2: continue
            q = mk(m)
            if q is None or q["thread"] is None: continue
            if q["L"] / max(q["S"], 1e-6) >= sc["member_aspect"] and 0.8 <= q["S"] <= 7.0:
                q["is_win"] = False; out.append(q)
    return out


def _role_threads(ctx, keys):
    """threads the role's palette tones map to"""
    ev = ctx.ev; idx = _idx(ev, keys); out = set()
    for i in idx:
        m = ev.tone == i
        if m.any():
            v = ctx.thread_lab[m]; v = v[v >= 0]
            if len(v): out.add(ctx.threads[int(np.bincount(v).argmax())])
    return out


def _clear_cl(ev, lab, zk, cl, need_any, need_low):
    """the longest stretch of the centreline cl (sampled every 0.25 mm) that lies in ONE plane k, >= need_any mm from
    every other region and >= need_low mm from regions LOWER than k (label 0 = other zones, taken as lower) ->
    [(x, y), (x, y)] or None"""
    (x0, y0), (x1, y1) = cl[0], cl[-1]; L = math.dist(cl[0], cl[-1])
    n = max(2, int(L / 0.25) + 1); t = np.linspace(0, 1, n)
    xs, ys = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
    j = np.clip(((xs - ev.bounds[0]) * ev.ppm).astype(int), 0, lab.shape[1] - 1); i = np.clip(((ys - ev.bounds[1]) * ev.ppm).astype(int), 0, lab.shape[0] - 1)
    ks = lab[i, j]; vals, cnt = np.unique(ks[ks > 0], return_counts=True)
    if not len(vals): return None
    k = int(vals[cnt.argmax()]); pad = int(math.ceil((need_low + 1.0) * ev.ppm))
    r0, r1 = max(0, i.min() - pad), min(lab.shape[0], i.max() + pad + 1); c0, c1 = max(0, j.min() - pad), min(lab.shape[1], j.max() + pad + 1)
    sub = lab[r0:r1, c0:c1]
    Dany = ndi.distance_transform_edt(sub == k) / ev.ppm
    Dlow = ndi.distance_transform_edt(~((sub != k) & (zk[sub] < zk[k]))) / ev.ppm
    ok = (ks == k) & (Dany[i - r0, j - c0] >= need_any) & (Dlow[i - r0, j - c0] >= need_low)
    best = None; s = None
    for q, f in enumerate(list(ok) + [False]):
        if f and s is None: s = q
        if not f and s is not None:
            if best is None or q - 1 - s > best[1] - best[0]: best = (s, q - 1)
            s = None
    if best is None or best[1] == best[0]: return None
    a, b = best
    return [(round(float(xs[a]), 3), round(float(ys[a]), 3)), (round(float(xs[b]), 3), round(float(ys[b]), 3))]


def _member_w(area, L, sc):
    """satin width of a member: its mean width, at most 7 mm (rule 4) and at most L / band_aspect (a stroke, never a blob,
    LESSONS A16); None when that leaves less than the 1 mm satin minimum (rule 9)"""
    w = min(7.0, area / max(L, 1e-6), L / sc["band_aspect"] - SEWN)
    return round(w, 3) if w >= 1.0 else None


def _rows(wins, gap):
    """windows on one course: centre within half a window height, x gap <= gap"""
    items = sorted(wins, key=lambda f: (f["geom"].centroid.y, f["geom"].centroid.x)); rows = []
    for f in items:
        cy = f["geom"].centroid.y; b = f["geom"].bounds; placed = False
        for r in rows:
            if r["wall"] != f["wall"]: continue
            h = max(r["h"], b[3] - b[1])
            if abs(r["cy"] - cy) <= 0.5 * h and (b[0] - r["x1"] <= gap and r["x0"] - b[2] <= gap):
                r["m"].append(f); r["x0"] = min(r["x0"], b[0]); r["x1"] = max(r["x1"], b[2]); placed = True; break
        if not placed: rows.append(dict(m=[f], cy=cy, x0=b[0], x1=b[2], h=b[3] - b[1], wall=f["wall"]))
    return [r["m"] for r in rows]


def _band(grp, sc):
    """a row of windows -> (cl, w, thread): a band along the wall's courses through the windows, as long as the row,
    w = the median window height, at most length / 2.5 (rule 9 / LESSONS A16: a satin is a stroke), at least 1 mm.
    None when the row is too short for a band (it stays wall)."""
    a = math.radians(grp[0]["course"])                                # windows run along the courses (the eave line)
    ux, uy = math.cos(a), math.sin(a); vx, vy = -uy, ux
    U, V, H = [], [], []
    for f in grp:
        cs = np.asarray(f["geom"].exterior.coords if f["geom"].geom_type == "Polygon" else
                        [c for q in f["geom"].geoms for c in q.exterior.coords])
        u = cs @ np.array([ux, uy]); v = cs @ np.array([vx, vy])
        U += [u.min(), u.max()]; V.append((v.min() + v.max()) / 2); H.append(v.max() - v.min())
    u0, u1 = min(U), max(U); L = u1 - u0
    if L < sc["window_min_len_mm"]: return None
    w = min(7.0, float(np.median(H)), L / sc["band_aspect"] - SEWN)
    if w < 1.0: return None
    v0 = float(np.median(V))
    cl = [(ux * u0 + vx * v0, uy * u0 + vy * v0), (ux * u1 + vx * v0, uy * u1 + vy * v0)]
    area = {}
    for f in grp: area[f["thread"]] = area.get(f["thread"], 0.0) + f["geom"].area
    th = max(area, key=lambda t: (area[t], t))
    return [(round(x, 3), round(y, 3)) for x, y in cl], w, th
