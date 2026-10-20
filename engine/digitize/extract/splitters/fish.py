"""Fish splitter (engine trial on Koi Blossom, tag KOI, 2026-10-20). The founder replaced the mockup's koi with TETRAS
(inputs/reference_fish.png, 19 Oct 2026) at the mockup fish poses, 0.82 x the mockup fish length ("82 % is fine"). So a
fish has two input-pixel sources: its POSE from the reference crop (the registered close-up / mockup fish), its SHAPE
from the founder's tetra. Nothing is typed (LESSONS A14): no polygon, no head point, no size constant except the
founder's length factor (run.yaml fish.length_factor).

  1. template (once per run): the founder reference image, background = the median of its border; fish = pixels far
     from it (bg_dist); the largest fish not touching the image border is the template. Its pixels are classified to the
     run palette (CIEDE2000, like the evidence). Pose: principal axis; head = the end nearer the eye (the darkest compact
     blob inside the fish), else the blunter end (the peduncle is the thinnest cross-section 10-35 % from the tail);
     snout / tail tip = the extreme points along the axis. Dorsal side = the side of the axis holding the dorsal
     stripe pixels (dorsal_tones: the tetra's neon line), else the side of the image's top.
  2. pose on the garment: the zone's claimed fish pixels (light + red tones, filled), the largest blob >= min_fish_mm2;
     axis, head (eye / blunt end) and length from those pixels the same way.
  3. placement: a similarity transform puts the template's snout -> tail on the pose's head -> tail at length_factor x
     the pose length, centred on the pose's middle, mirrored if needed so the dorsal side faces up the garment (-y).
  4. parts (template pixels -> garment mm): BODY = the fish opened by fin_open_frac x its body height (fins removed);
     FINS = fish - body, components >= min_fin_mm2; STRIPES = the stripe tones inside the body (red, cyan); EYE = the
     eye blob. Body tones are partitioned by thread (pieces < min_piece_mm2 absorbed; the template's
     anti-aliased dark rim, edge_tones, belongs to the main body tone).
       fish_body   tatami ALONG the fish axis (construct rule "axis": the body's head -> tail chord through each piece)
       fish_stripe satin column ACROSS the stripe along its traced centreline (rule "column"); a stripe that is not a
                   stroke (>= 1 mm wide, length >= 1.5 x width) is sewn as a body piece instead
       fish_fin    tatami fanning from the fin's root on the body to its tip (rule "fan", outline bucket)
       fish_eye    a bead (dot technique) at the eye, sewn last
     z: fins under the body, stripes and eye on top.
meta: splitter "fish", fish (zone id), pose (head, tail, length_mm), template, construct; M4g hint group = the fish."""
import math, os
import numpy as np
from scipy import ndimage as ndi
from PIL import Image
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union, nearest_points
from shapely import affinity
import dst2
from digitize.schema import Part, DirSpec
from digitize.extract.splitters.construct import basis as cbasis, line_angle

DEFAULTS = dict(reference="inputs/reference_fish.png", length_factor=0.82, bg_dist=55.0, min_fish_mm2=40.0, fish_tones=None,
                light_tones=["kb_white", "kb_lav", "kb_ice", "kb_sky"], stripe_tones=["kb_red", "kb_cyan", "kb_corn", "kb_royal"],
                eye_tones=["kb_black"], dorsal_tones=["kb_cyan"], edge_tones=["kb_navy", "kb_cobalt"], fin_open_frac=0.28, min_fin_mm2=1.5, min_piece_mm2=8.0, eye_min_d=1.3,
                body_threads=["kb_white", "kb_lav", "kb_ice"], fin_thread="kb_white", wide_stripe_mm=2.0, min_stripe_mm2=3.0,
                fin_z=-0.2, stripe_z=0.2, eye_z=0.4)

_TEMPLATE = {}


def _cfg(ctx):
    d = dict(DEFAULTS); d.update(ctx.cfg.get("fish", {}) or {}); return d


# ------------------------------------------------------------------ pose of a fish mask (template or garment)
def pose(mask, eye=None, scale=1.0, origin=(0.0, 0.0)):
    """principal axis of a fish mask -> dict(head, tail, axis (unit, head -> tail), normal, length, centre) in the
    mask's units (px * scale + origin). Head = the end nearer the eye centroid when given, else the blunter end."""
    ys, xs = np.nonzero(mask)
    P = np.c_[xs + 0.5, ys + 0.5] * scale + np.asarray(origin, float)
    c = P.mean(0); U, S, Vt = np.linalg.svd(P - c, full_matrices=False); a = Vt[0]
    t = (P - c) @ a; lo, hi = t.min(), t.max()
    if eye is not None:
        te = (np.asarray(eye, float) - c) @ a
        head_is_lo = abs(te - lo) < abs(te - hi)
    else:                                                       # the peduncle: thinnest cross-section 10-35 % in from the tail
        n = (P - c) @ np.array([-a[1], a[0]]); L = hi - lo; nb = 40
        b = np.clip(((t - lo) / max(L, 1e-9) * nb).astype(int), 0, nb - 1)
        wid = np.array([np.ptp(n[b == k]) if (b == k).any() else 0.0 for k in range(nb)])
        lo_band = wid[int(0.10 * nb):int(0.35 * nb)].min(initial=1e9); hi_band = wid[int(0.65 * nb):int(0.90 * nb)].min(initial=1e9)
        head_is_lo = hi_band < lo_band                         # the narrower band is the tail's peduncle
    if not head_is_lo: a = -a; t = -t; lo, hi = -hi, -lo
    head = c + a * lo; tail = c + a * hi
    return dict(head=head, tail=tail, axis=a, normal=np.array([-a[1], a[0]]), length=float(hi - lo), centre=(head + tail) / 2)


def tail_mask(mask, po, lo=0.60, hi=0.92, nb=40):
    """the tail fin of a fish mask: every pixel behind the PEDUNCLE, the thinnest cross-section between lo and hi of the
    length from the head (pose po in the mask's px). The opening that strips the other fins keeps a broad tail joined to
    the body through a wide peduncle, so it would be sewn as body along the axis (Koi trial re-run: tails lost)."""
    ys, xs = np.nonzero(mask); Pp = np.c_[xs + 0.5, ys + 0.5]
    t = (Pp - po["head"]) @ po["axis"]; n = (Pp - po["centre"]) @ po["normal"]; L = max(po["length"], 1e-9)
    b = np.clip((t / L * nb).astype(int), 0, nb - 1)
    wid = np.array([np.ptp(n[b == k]) if (b == k).any() else np.inf for k in range(nb)])
    k0, k1 = int(lo * nb), int(hi * nb); k = k0 + int(np.argmin(wid[k0:k1]))
    out = np.zeros_like(mask); sel = t > (k + 0.5) / nb * L; out[ys[sel], xs[sel]] = True
    return out


def _nearest_tone(rgb, keys, hexes):
    from digitize.extract.evidence import to_lab, delta_e, hex_rgb
    lab = to_lab(rgb.reshape(-1, 3)[None])[0]; lp = to_lab(np.array([[hex_rgb(h) for h in hexes]]))[0]
    d = np.stack([delta_e(lab, np.broadcast_to(lp[i], lab.shape)) for i in range(len(keys))], -1)
    return d.argmin(-1).reshape(rgb.shape[:2])


def template(path, palette, sc):
    """the founder's reference fish -> dict(mask, tone (palette key index), keys, pose, dorsal (+1 / -1 along the
    pose normal), body_h) in template px"""
    key = (path, tuple(sorted(palette.items())), sc["bg_dist"])
    if key in _TEMPLATE: return _TEMPLATE[key]
    a = np.asarray(Image.open(path).convert("RGB")).astype(float)
    border = np.r_[a[0], a[-1], a[:, 0], a[:, -1]]; bg = np.median(border, 0)
    fishy = np.linalg.norm(a - bg, axis=2) > sc["bg_dist"]
    fishy = ndi.binary_opening(fishy, np.ones((3, 3), bool))
    lab, n = ndi.label(fishy); H, W = fishy.shape; best = None
    for i, s in enumerate(ndi.find_objects(lab), 1):
        if s is None or s[0].start == 0 or s[1].start == 0 or s[0].stop >= H or s[1].stop >= W: continue
        area = int((lab[s] == i).sum())
        if best is None or area > best[0]: best = (area, i, s)
    if best is None: raise ValueError(f"{path}: no whole fish (every fish blob touches the image border)")
    _, i, s = best; pad = 4
    s = (slice(max(0, s[0].start - pad), min(H, s[0].stop + pad)), slice(max(0, s[1].start - pad), min(W, s[1].stop + pad)))
    m = ndi.binary_fill_holes(lab[s] == i); rgb = a[s]
    keys = list(palette); tone = _nearest_tone(rgb, keys, [palette[k] for k in keys])
    eye_i = [keys.index(k) for k in sc["eye_tones"] if k in keys]
    em = m & np.isin(tone, eye_i) & (rgb @ np.array([0.299, 0.587, 0.114]) < 70)
    el, en = ndi.label(em); eye = None
    if en:
        sz = np.bincount(el.ravel()); sz[0] = 0; ys, xs = np.nonzero(el == sz.argmax()); eye = (xs.mean() + 0.5, ys.mean() + 0.5)
    po = pose(m, eye)
    dist = ndi.distance_transform_edt(m); body_h = 2.0 * dist.max()
    st_i = [keys.index(k) for k in sc["dorsal_tones"] if k in keys]
    sy, sx = np.nonzero(m & np.isin(tone, st_i))
    if len(sx): side = float(np.sign(((np.c_[sx + 0.5, sy + 0.5] - po["centre"]) @ po["normal"]).mean()) or 1.0)
    else: side = float(np.sign(-po["normal"][1]) or 1.0)       # no stripe: the image's top is the dorsal side
    out = dict(mask=m, tone=tone, keys=keys, pose=po, dorsal=side, body_h=body_h, eye=eye, path=path, rgb=rgb)
    _TEMPLATE[key] = out
    return out


def placement(T, P, factor):
    """template px -> garment mm: (fn(x, y) -> (X, Y) on arrays, scale mm/px, mirrored)"""
    s = factor * P["length"] / T["pose"]["length"]
    ta, tn = T["pose"]["axis"], T["pose"]["normal"]; pa = P["axis"]; pn = np.array([-pa[1], pa[0]])
    # dorsal must face up the garment (-y): choose the normal sign so the template's dorsal side maps to pn . y < 0
    dn = pn if pn[1] < 0 else -pn
    sign = 1.0 if T["dorsal"] > 0 else -1.0                    # template dorsal = +normal (sign 1) or -normal
    tc = T["pose"]["centre"]; pc = P["centre"]
    def fn(x, y):
        d = np.stack([np.asarray(x, float) - tc[0], np.asarray(y, float) - tc[1]], -1)
        u = d @ ta; v = (d @ tn) * sign                        # v > 0 = dorsal
        out = pc + s * (u[..., None] * pa + v[..., None] * dn)
        return out[..., 0], out[..., 1]
    cr = lambda a, b: a[0] * b[1] - a[1] * b[0]
    mirrored = bool(np.sign(cr(ta, tn) * sign) != np.sign(cr(pa, dn)))
    return fn, s, mirrored


def _polys(mask, fn, simplify_px=0.6):
    """template mask -> garment polygons (contours mapped through fn)"""
    from skimage import measure
    out = []
    lab, n = ndi.label(mask)
    for i, s in enumerate(ndi.find_objects(lab), 1):
        if s is None: continue
        m = np.pad(lab[s] == i, 1); g = Polygon()
        for c in measure.find_contours(m.astype(np.float32), 0.5):
            if len(c) < 4: continue
            xs = c[:, 1] + s[1].start - 1 + 0.5; ys = c[:, 0] + s[0].start - 1 + 0.5
            X, Y = fn(xs, ys); p = Polygon(np.c_[X, Y]).buffer(0)
            if not p.is_empty: g = g.symmetric_difference(p)
        g = g.buffer(0)
        if not g.is_empty: out.append(g)
    return out


def _one(gs):
    gs = [g for g in gs if not g.is_empty]
    if not gs: return None
    return gs[0] if len(gs) == 1 else unary_union(gs).buffer(0)


def _thread(ctx, key):
    t = ctx.tone_thread.get(key) if hasattr(ctx, "tone_thread") else key
    if t is None: raise ValueError(f"fish template tone {key!r} has no thread in this run (no pixels of it in the crop's evidence): "
                                   f"protect it in run.yaml threads.protected (the founder's fish colours are accents)")
    return t


def axis_chord(g, ang):
    """construct rule "axis" for a body piece: the chord through its representative point at the fish-axis angle, as
    long as the piece is along that angle; None when it does not rebuild (not on the part / not a stroke)"""
    rp = g.representative_point(); ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    r = affinity.rotate(g, -ang, origin=rp); b = r.bounds; L = max(b[2] - b[0], 0.1)
    c = ((rp.x - ux * L / 2, rp.y - uy * L / 2), (rp.x + ux * L / 2, rp.y + uy * L / 2))
    probe = Part(id="_", kind="fish_body", geom=g, thread="", z=0, dir=DirSpec(0.0, source="splitter"),
                 meta=dict(construct=dict(rule="axis", line=[list(c[0]), list(c[1])])))
    return c if cbasis(probe)[0] is not None else None


def split(ctx, zone, z, claim):
    ev = ctx.ev; sc = _cfg(ctx); ppm = ev.ppm; parts = []; used = np.zeros_like(claim)
    if not claim.any(): return parts, used
    keys = ev.keys
    light = np.isin(ev.tone, [keys.index(k) for k in sc["light_tones"] + sc["stripe_tones"][:1] if k in keys])
    sil = ndi.binary_fill_holes(ndi.binary_closing(claim & light, ctx.disk(1.0))) & (claim | ndi.binary_closing(claim & light, ctx.disk(1.0)))
    sil = ndi.binary_fill_holes(sil)
    lab, n = ndi.label(sil)
    stats = dict(fish=0, head_from=None, length_mm=None, scale_mm_per_px=None, mirrored=None, parts={})
    if n == 0: ctx.stats = getattr(ctx, "stats", {}); ctx.stats[zone["id"]] = stats; return parts, used
    sizes = np.bincount(lab.ravel()); sizes[0] = 0; F = lab == int(sizes.argmax())
    if sizes.max() / ppm ** 2 < sc["min_fish_mm2"]: ctx.stats = getattr(ctx, "stats", {}); ctx.stats[zone["id"]] = stats; return parts, used
    used |= F | (claim & ndi.binary_dilation(F, ctx.disk(1.5)))
    eyem = F & np.isin(ev.tone, [keys.index(k) for k in sc["eye_tones"] if k in keys]) & ~ndi.binary_dilation(~F, ctx.disk(0.6))
    el, en = ndi.label(eyem); eye = None
    if en:
        sz = np.bincount(el.ravel()); sz[0] = 0; ys, xs = np.nonzero(el == sz.argmax())
        if sz.max() / ppm ** 2 <= 6.0: eye = ev.to_mm(xs.mean() + 0.5, ys.mean() + 0.5)
    P = pose(F, eye, scale=1.0 / ppm, origin=ev.bounds[:2])
    path = sc["reference"] if os.path.isabs(sc["reference"]) else os.path.join(ctx.cfg["project"], sc["reference"])
    pal = {k: v for k, v in ctx.cfg["threads"]["palette"].items() if k not in (ctx.cfg["threads"].get("bare") or [])}
    T = template(path, pal, sc)
    fn, s, mir = placement(T, P, float(sc["length_factor"]))
    stats.update(fish=1, head_from="eye" if eye is not None else "peduncle", length_mm=round(P["length"], 1),
                 tetra_mm=round(float(sc["length_factor"]) * P["length"], 1), scale_mm_per_px=round(s, 4), mirrored=mir)
    m = T["mask"]; tone = T["tone"]; tk = T["keys"]
    r_open = max(1, int(round(sc["fin_open_frac"] * T["body_h"] / 2)))
    yy, xx = np.ogrid[-r_open:r_open + 1, -r_open:r_open + 1]
    body = ndi.binary_opening(m, xx * xx + yy * yy <= r_open * r_open)
    bl, bn = ndi.label(body)
    if bn: bs = np.bincount(bl.ravel()); bs[0] = 0; body = bl == int(bs.argmax())
    tail = tail_mask(m, T["pose"])                         # the tail fin is a FIN (behind the peduncle), never body
    body = body & ~tail
    fins = m & ~ndi.binary_dilation(body, np.ones((3, 3), bool))
    ti = lambda names: np.isin(tone, [tk.index(k) for k in names if k in tk])
    eyeT = body & ti(sc["eye_tones"]) & (T["rgb"] @ np.array([0.299, 0.587, 0.114]) < 70)
    if eyeT.any():
        lab_e, ne = ndi.label(eyeT); se = np.bincount(lab_e.ravel()); se[0] = 0; eyeT = lab_e == int(se.argmax())
    ang = line_angle(tuple(P["head"]), tuple(P["tail"])); gid = f"{zone['id']}.fish"
    _bc = np.bincount(tone[body], minlength=len(tk)); _bc[[tk.index(e) for e in sc["edge_tones"] if e in tk]] = 0
    main_tone = tk[int(_bc.argmax())]
    pose_meta = dict(head=[round(float(v), 2) for v in P["head"]], tail=[round(float(v), 2) for v in P["tail"]],
                     length_mm=round(P["length"], 2), tetra_mm=stats["tetra_mm"], template=os.path.basename(path), mirrored=mir)
    bodyg = _one(_polys(body, fn))
    def add(kind, g, thread, zz, d, meta):
        parts.append(Part(id=ctx.new_id(zone["id"]), kind=kind, geom=g, thread=thread, z=zz, dir=d, zone=zone["id"], rgb=None,
                          meta=dict(splitter="fish", fish=zone["id"], pose=pose_meta, group=gid, tone_group=gid, **meta)))
        stats["parts"][kind] = stats["parts"].get(kind, 0) + 1
    # stripes (inside the body): red first, then the blue / cyan line. A stripe at least wide_stripe_mm wide is a BAND of
    # the body (tatami along the fish axis, like the body: a light, flat colour band, not a heavy satin slab, and the
    # same direction as the body so the tile reads one grain); a thinner line is a light satin column across it.
    taken = eyeT.copy(); bands = []
    for sk in sc["stripe_tones"][:2]:
        if sk not in tk: continue
        sm = body & ti([sk]) & ~taken
        sm = ndi.binary_opening(sm, np.ones((2, 2), bool))
        for g in _polys(sm, fn):
            if g.area < sc["min_stripe_mm2"]: continue
            gp = g if g.geom_type == "Polygon" else max(g.geoms, key=lambda q: q.area)
            line = dst2.centreline(gp)
            if line is None or line.length < 1.0: bands.append((sk, g)); continue
            line = LineString(line.simplify(0.4).coords); w = gp.area / line.length
            if w >= sc["wide_stripe_mm"] or w < 1.0 or line.length < 1.5 * w: bands.append((sk, g)); continue
            cl = [list(map(float, q)) for q in line.coords]; con = dict(rule="column", cl=cl)
            probe = Part(id="_", kind="fish_stripe", geom=gp, thread="", z=0, dir=DirSpec(0.0, mode="contour", source="splitter"), meta=dict(construct=con))
            a2, why = cbasis(probe)
            if a2 is None: bands.append((sk, g)); continue
            add("fish_stripe", gp, _thread(ctx, sk), z + sc["stripe_z"], DirSpec(a2, mode="contour", source="splitter",
                note="light satin across the line, along its centreline"), dict(cl=cl, w=round(w, 2), construct=con))
        taken |= body & ti([sk])
    # body: SILVER / LAVENDER bands. Every body pixel of the founder's tetra is read against the light body threads only
    # (body_threads: silver white, lavender grey, ice blue; nearest in Lab), majority-filtered, so the reference's shading
    # (light back, lavender flank and belly) becomes 2-3 bands instead of nearest-thread blues of an anti-aliased image.
    rest = body & ~taken
    if bodyg is not None and rest.any():
        bt = [k for k in sc["body_threads"] if k in pal]
        bi = _nearest_tone(T["rgb"], bt, [pal[k] for k in bt])
        r_m = 2; cnt = np.stack([ndi.uniform_filter((bi == i).astype(np.float32), 2 * r_m + 1) for i in range(len(bt))], -1); bi = cnt.argmax(-1)
        bc = np.bincount(bi[rest], minlength=len(bt)); main = bt[int(bc.argmax())]
        pieces = [(bt[i], g) for i in range(len(bt)) if bc[i] for g in _polys(rest & (bi == i), fn)]
        pieces += bands
        keep = []; mg = None
        for k, g in pieces:
            if k == main or g.area < sc["min_piece_mm2"]:
                mg = g if mg is None else mg.union(g.buffer(0.05)).buffer(0); continue
            c = axis_chord(g, ang)
            if c is None: mg = g if mg is None else mg.union(g).buffer(0); continue     # not along the axis: main piece
            keep.append((k, g, c))
        if mg is not None:
            c = axis_chord(mg, ang) or (axis_chord(bodyg, ang) if mg.distance(bodyg.representative_point()) < 1.0 else None)
            if c is not None: keep.append((main, mg, c))
            else: stats["no_construct"] = stats.get("no_construct", 0) + 1
        for k, g, c in keep:
            con = dict(rule="axis", line=[list(map(float, c[0])), list(map(float, c[1]))])
            zz = z + (sc["stripe_z"] if k in sc["stripe_tones"][:2] else (0.0 if k == main else 0.05))
            add("fish_body", g, _thread(ctx, k), zz, DirSpec(line_angle(*con["line"]), source="splitter",
                note="along the fish axis"), dict(construct=con, tone=k))
    # fins and tail: satin ALONG THE RAYS, fanning from the fin's root on the body (radial technique, centre = the root;
    # house.yaml fish_fin, rule 4 exception asked for by the founder 20 Oct 2026), in the lightest body thread so they read crisp
    if bodyg is not None:
        fl, fnum = ndi.label(fins)
        fin_k = sc["fin_thread"] if sc["fin_thread"] in pal else main_tone
        for j in range(1, fnum + 1):
            fmask = fl == j
            g = _one(_polys(fmask, fn))
            if g is None or g.area < sc["min_fin_mm2"]: continue
            gp = g if g.geom_type == "Polygon" else max(g.geoms, key=lambda q: q.area)
            root = nearest_points(bodyg, gp.centroid)[0]; cen = [float(root.x), float(root.y)]
            con = dict(rule="radial")
            probe = Part(id="_", kind="fish_fin", geom=g, thread="", z=0, dir=DirSpec(0.0, mode="radial", source="splitter"),
                         meta=dict(construct=con, centre=cen))
            a3, why = cbasis(probe)
            if a3 is None: stats["fin_no_construct"] = stats.get("fin_no_construct", 0) + 1; continue
            add("fish_fin", g, _thread(ctx, fin_k), z + sc["fin_z"], DirSpec(0.0, mode="radial", source="splitter", note="satin along the fin rays, from the root"),
                dict(construct=con, centre=cen, tone=fin_k, keep_small=True, min_fragment_mm2=1.0))       # small fins are deliberate detail
    # eye: one bead
    if eyeT.any():
        ys, xs = np.nonzero(eyeT); X, Y = fn(xs + 0.5, ys + 0.5); cx, cy = float(X.mean()), float(Y.mean())
        art_d = 2.0 * math.sqrt(eyeT.sum() * s * s / math.pi)
        from digitize.techniques.dot import needle_d
        d, hm = needle_d(art_d, sc["eye_min_d"])
        ek = sc["eye_tones"][0] if sc["eye_tones"][0] in pal else tk[int(np.bincount(tone[eyeT], minlength=len(tk)).argmax())]
        add("fish_eye", Point(cx, cy).buffer(max(d, art_d) / 2, 16), _thread(ctx, ek), z + sc["eye_z"], DirSpec(0.0, source="rule"),
            dict(knots=[[cx, cy, d, 0.0]], art_d=round(art_d, 2), house_min=hm, keep_small=True, min_fragment_mm2=0.5))   # a 1-2 mm bead: never a speck
    ctx.stats = getattr(ctx, "stats", {}); ctx.stats[zone["id"]] = stats
    return parts, used
