"""Soot sprites on the front leg (07, founder J5 21 Oct: KEPT) — gates + compare sheet.
Per sprite, from the shipped DST (07a / 07b) vs the C5 map (out/front_stars.json["soot"], traced from the mockup):
  position  centre of the sewn black body vs the map centre            <= POS_MAX mm
  cover     traced body disc covered by thread (any colour)            >= COVER_MIN  (A15)
  eyes      white eye blobs sewn inside the body                       == 2, each within EYE_MAX mm of the art-table position
Rev B8 (founder 22 Oct: "eyes look crazy and cracked, some limbs missing"; the B7 gate passed 9/9 because it counted
blobs) — against the art table inputs/soot_art.json (hand-read from the mockup):
  limbs     black runs outside body+fur and outside the candies: count == table, each table limb traced (<= LIMB_MAX mm)
  gaze      pupil offset in each eye: both eyes agree (<= GAZE_AGREE mm) and match the table gaze (<= GAZE_MAX mm)
  eye size  eye white area / D^2 within EYE_AREA_TOL of the table ellipse
  no cracks the white satin closes up: neighbouring crossings <= ROW_GAP_MAX mm apart along the eye, and no crossing
            in the middle of the eye spans < 1 - SPLIT_MIN of the eye's width (a split line)
Writes out/gates_soot.json and out/compare_soot.png (mockup crop vs stitch preview, same scale, 3 sprites per row)."""
import json, math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
import kjcore
import kjcompare as C
import kjfront

PPM = C.PPM
POS_MAX, COVER_MIN, EYE_MAX = 0.6, 0.95, 0.6
LIMB_MIN, LIMB_MAX, LIMB_COVER = 1.2, 0.5, 0.8   # a limb = >= 1.2 mm of run; >= 80 % of the table limb within 0.5 mm of the sewn one
GAZE_AGREE, GAZE_MAX = 0.35, 0.35               # mm: the 2 pupils' offsets agree / match the table gaze
EYE_AREA_TOL = 0.15                              # +-15 % of the table eye area (needle points + half a thread)
ROW_GAP_MAX, SPLIT_MIN = 0.30, 0.25             # eye satin: crossings <= 0.30 mm apart (B8 sews 0.20; B7 0.36); no crossing < 75 % of the chord
DEBUG = None                                     # list -> art_gate appends (id, crossing positions) per eye
SOOT_HEX, WHITE_HEX = kjcore.KJ_PAL["kj_soot"][0].upper(), kjcore.KJ_PAL["kj_white"][0].upper()
FILES = {"front1": "HAKI_KJ_07a_front-leg-trail-upper", "front2": "HAKI_KJ_07b_front-leg-trail-lower"}

def stop_segments(path, origin):
    """[(stop index, (x0, y0), (x1, y1))] of every sewn stitch in design mm."""
    import pyembroidery as pe
    p = pe.read(path); out = []; ci = 0; prev = None
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK; P = (x / 10 + origin[0], y / 10 + origin[1])
        if k == pe.STITCH:
            if prev is not None: out.append((ci, prev, P))
            prev = P
        elif k == pe.COLOR_CHANGE: ci += 1; prev = None
        elif k == pe.TRIM: prev = None
        elif k == pe.JUMP: prev = P
        elif k == pe.END: break
    return out

def stop_index(rj, col, last=False):
    ix = [i for i, s in enumerate(rj["per_stop"]) if s.get("col") == col]
    return (ix[-1] if last else ix[0]) if ix else None

def art_gate(q, M, to_px, shape, A, rj, segs):
    """Rev B8 checks of one sprite against its art-table row A (inputs/soot_art.json)."""
    cx0, cy0 = to_px(q["x_from_side_mm"], q["y_from_waist_mm"]); h = int(24 * PPM)        # work in a 48 mm window round the sprite
    X0, Y0 = max(0, int(cx0) - h), max(0, int(cy0) - h); X1, Y1 = min(shape[1], int(cx0) + h), min(shape[0], int(cy0) + h)
    M = {k: m[Y0:Y1, X0:X1] for k, m in M.items()}; shape = (Y1 - Y0, X1 - X0)
    _tp = to_px; to_px = lambda x, y: (_tp(x, y)[0] - X0, _tp(x, y)[1] - Y0)
    Hh, Ww = shape; cx, cy = to_px(q["x_from_side_mm"], q["y_from_waist_mm"]); D = q["d_mm"]; R = D / 2
    yy, xx = np.mgrid[0:Hh, 0:Ww]; rr = np.hypot(xx - cx, yy - cy) / PPM
    body_stop, pup_stop = stop_index(rj, "kj_soot"), stop_index(rj, "kj_soot", last=True)
    soot0 = M.get(body_stop, np.zeros(shape, bool)); pup = M.get(pup_stop, np.zeros(shape, bool))
    other = np.any([m for k, m in M.items() if isinstance(k, str) and k != SOOT_HEX] or [np.zeros(shape, bool)], axis=0)
    other = ndi.binary_dilation(other, iterations=int(0.3 * PPM))
    # (a) limbs
    keep = (rr > R + kjfront.SOOT_FUR[1] + 0.35) & (rr < 22) & ~other
    lab, n = ndi.label(soot0 & keep, structure=np.ones((3, 3)))
    comps = [i for i in range(1, n + 1) if (lab == i).sum() >= LIMB_MIN * 0.35 * PPM ** 2]
    limbs = []; used = set(); DT = {}
    for L in A["limbs"]:
        P = [to_px(q["x_from_side_mm"] + x, q["y_from_waist_mm"] + y) for x, y in L["pts"]]
        smp = []
        for a, b in zip(P, P[1:]):
            m = max(2, int(math.dist(a, b) / (0.1 * PPM)))
            smp += [(a[0] + (b[0] - a[0]) * t / m, a[1] + (b[1] - a[1]) * t / m) for t in range(m + 1)]
        smp = [(x, y) for x, y in smp if 0 <= int(y) < Hh and 0 <= int(x) < Ww and keep[int(y), int(x)]]
        best = (0.0, None, 99.0)
        for i in comps:
            if i not in DT: DT[i] = ndi.distance_transform_edt(lab != i) / PPM
            dt = DT[i]
            dd = [dt[int(y), int(x)] for x, y in smp]
            cov = float(np.mean([d <= LIMB_MAX for d in dd])) if dd else 0.0
            if cov > best[0]: best = (cov, i, float(max(dd[-3:])) if dd else 99.0)
        ok = best[1] is not None and best[0] >= LIMB_COVER and best[2] <= LIMB_MAX and best[1] not in used
        if ok: used.add(best[1])
        limbs.append(dict(kind=L["kind"], cover=round(best[0], 2), end_mm=round(best[2], 2), ok=bool(ok)))
    limb_ok = len(comps) == len(A["limbs"]) and all(l["ok"] for l in limbs)
    # eyes: the white-stop blobs inside the body, filled
    white = M.get(WHITE_HEX, np.zeros(shape, bool)) & (rr < R)
    wl, nw = ndi.label(ndi.binary_fill_holes(white)); E = A["eyes"]; area_t = math.pi / 4 * E["w"] * E["h"]
    eyes = []
    for i in range(1, nw + 1):
        m = wl == i
        if m.sum() / PPM ** 2 < 2.0: continue
        ey, ex = np.nonzero(m); c = (ex.mean(), ey.mean())
        pm = pup & m; py_, px_ = np.nonzero(pm)
        off = (((px_.mean() - c[0]) / PPM, (py_.mean() - c[1]) / PPM) if len(px_) else (99.0, 99.0))
        eyes.append(dict(c=c, m=m, off=off, area=m.sum() / PPM ** 2))
    g = E["gaze"]
    if len(eyes) == 2:
        o1, o2 = eyes[0]["off"], eyes[1]["off"]
        agree = math.dist(o1, o2); mean = ((o1[0] + o2[0]) / 2, (o1[1] + o2[1]) / 2); gerr = math.dist(mean, g)
        area_r = max(abs(e["area"] / area_t - 1) for e in eyes)
    else: agree = gerr = area_r = 99.0
    # (d) cracks: the eye satin from the DST stitches. Crossings = white-stop stitches inside the eye >= 0.5 mm long;
    # row gap = largest step between neighbouring crossings along the eye's long axis (house solid satin: <= ROW_GAP_MAX,
    # i.e. 0.40 mm same side); split = a crossing in the middle half that spans < SPLIT_MIN of the eye's chord there.
    wst = stop_index(rj, "kj_white"); t = math.radians(E["tilt_deg"]); u = (math.cos(t), math.sin(t)); v = (-u[1], u[0])
    row_gap = split = 0.0
    for e in eyes:
        mm = ndi.binary_dilation(e["m"], iterations=int(0.3 * PPM)); c = e["c"]; vs = []; hv = 0.0
        ys_, xs_ = np.nonzero(e["m"]); proj = ((xs_ - c[0]) * v[0] + (ys_ - c[1]) * v[1]) / PPM; hv = (proj.max() - proj.min()) / 2
        for ci, a, b in segs:
            if ci != wst: continue
            A_, B_ = to_px(*a), to_px(*b)
            if not all(0 <= int(p[1]) < Hh and 0 <= int(p[0]) < Ww and mm[int(p[1]), int(p[0])] for p in (A_, B_)): continue
            L = math.dist(A_, B_) / PPM
            if L < 0.5 or abs((B_[0] - A_[0]) * u[0] + (B_[1] - A_[1]) * u[1]) / PPM < 0.8 * L: continue     # crossings only (not the underlay)
            mx, my = (A_[0] + B_[0]) / 2 - c[0], (A_[1] + B_[1]) / 2 - c[1]
            vv = (mx * v[0] + my * v[1]) / PPM; vs.append(vv)
            if abs(vv) < hv / 2:                                     # chord of the eye through this crossing, along u
                ch = [s_ for s_ in np.arange(-4, 4, 0.05) if 0 <= int(c[1] + (my + s_ * PPM * u[1])) < Hh and 0 <= int(c[0] + (mx + s_ * PPM * u[0])) < Ww
                      and e["m"][int(c[1] + my + s_ * PPM * u[1]), int(c[0] + mx + s_ * PPM * u[0])]]
                if ch: split = max(split, 1 - L / (max(ch) - min(ch) + 0.05))
        vs = sorted(x for x in vs if abs(x) < 0.8 * hv)
        if len(vs) > 2: row_gap = max(row_gap, max(b_ - a_ for a_, b_ in zip(vs, vs[1:])))
        else: row_gap = 99.0
        if DEBUG is not None: DEBUG.append((q["id"], vs))
    gap = row_gap
    ok = limb_ok and agree <= GAZE_AGREE and gerr <= GAZE_MAX and area_r <= EYE_AREA_TOL and row_gap <= ROW_GAP_MAX and split <= SPLIT_MIN
    return dict(limbs_dst=len(comps), limbs_art=len(A["limbs"]), limbs_ok=bool(limb_ok), limb_detail=limbs,
                gaze_agree_mm=round(agree, 2), gaze_err_mm=round(gerr, 2), eye_area_err_pct=round(100 * area_r, 1),
                row_gap_mm=round(row_gap, 2), split=round(split, 2), art_ok=bool(ok))

def sprite_gate(q, M, to_px, shape, A=None):
    Hh, Ww = shape
    cx, cy = to_px(q["x_from_side_mm"], q["y_from_waist_mm"]); R = q["d_mm"] / 2 * PPM
    yy, xx = np.mgrid[0:Hh, 0:Ww]; disc = (xx - cx) ** 2 + (yy - cy) ** 2 <= R ** 2
    soot = M.get(SOOT_HEX, np.zeros(shape, bool)); white = M.get(WHITE_HEX, np.zeros(shape, bool))
    anyt = ndi.binary_closing(np.any([m for k, m in M.items() if isinstance(k, str)], axis=0), iterations=3)   # 0.15 mm: DST lines drawn 0.35 wide on 0.45 tatami rows leave raster slivers (thread lies ~0.4)
    cover = float((disc & anyt).sum()) / max(disc.sum(), 1)
    near = (xx - cx) ** 2 + (yy - cy) ** 2 <= (R + 1.6 * PPM) ** 2
    sb = ndi.binary_fill_holes(ndi.binary_closing(soot & near, iterations=4))     # body incl. the holes left for eyes / candies
    ys, xs = np.nonzero(sb & disc | (sb & ~disc & False))
    # centre: the sewn body disc = the fitted circle of the fuzz-free body (soot inside R + 0.3 mm)
    inner = sb & ((xx - cx) ** 2 + (yy - cy) ** 2 <= (R + 0.3 * PPM) ** 2)
    edge = sb & ~ndi.binary_erosion(sb, iterations=2)
    ys, xs = np.nonzero(edge & ((xx - cx) ** 2 + (yy - cy) ** 2 <= (R + 2.0 * PPM) ** 2))
    if len(xs) > 10:                                                              # least-squares circle through the outer edge
        A_ = np.c_[2 * xs, 2 * ys, np.ones(len(xs))]; b_ = xs ** 2 + ys ** 2
        sol = np.linalg.lstsq(A_, b_, rcond=None)[0]; fx, fy = sol[0], sol[1]
        pos = math.hypot(fx - cx, fy - cy) / PPM
    else: pos = 99.0
    wl, n = ndi.label(white & disc); eyes = []
    for i, sl in enumerate(ndi.find_objects(wl), 1):
        m = wl[sl] == i
        if m.sum() / PPM ** 2 < 2.0: continue                                     # konpeito white specks are Ø0.9 (0.6 mm²)
        ey, ex = np.nonzero(m); eyes.append(((ex.mean() + sl[1].start), (ey.mean() + sl[0].start)))
    exp = [to_px(q["x_from_side_mm"] + e[0], q["y_from_waist_mm"] + e[1]) for e in (A["eyes"]["centres"] if A else q["eyes_mm"])]
    eye_err = max((min(math.dist(e, f) for f in eyes) / PPM if eyes else 99.0) for e in exp)
    ok = pos <= POS_MAX and cover >= COVER_MIN and len(eyes) == 2 and eye_err <= EYE_MAX
    return dict(id=q["id"], pos_mm=round(pos, 2), cover_pct=round(100 * cover, 1), eyes=len(eyes), eye_err_mm=round(eye_err, 2), ok=bool(ok))

def run(dst_dir="out/stitch", out="out/gates_soot.json", sheet_png="out/compare_soot.png", art=None):
    F = json.load(open("out/front_stars.json")); soot = {q["id"]: q for q in F["soot"]}
    ART = (art or kjfront.soot_art())["sprites"]
    rows, tiles = [], []
    G = kjfront.geometry(); mmpx = G["mmpx"]
    mock = Image.open(kjfront.SRC).convert("RGB")
    for k, stem in FILES.items():
        sec = [soot[i] for i in F["sections"][int(k[-1]) - 1] if i in soot]
        if not sec: continue
        rj = json.load(open(f"{dst_dir}/{stem}.json")); path = f"{dst_dir}/{stem}.dst"
        allpts = F["stars"] + F["soot"]; byid = {d["id"]: d for d in allpts}
        ids = F["sections"][int(k[-1]) - 1]
        xs = [byid[i]["x_from_side_mm"] for i in ids]; ys = [byid[i]["y_from_waist_mm"] for i in ids]
        x0, y0 = min(xs) - 14, min(ys) - 14; W, H = max(xs) - min(xs) + 28, max(ys) - min(ys) + 28
        to_px = lambda x, y, x0=x0, y0=y0: ((x - x0) * PPM, (y - y0) * PPM)
        shape = (int(round(H * PPM)), int(round(W * PPM)))
        M = C.dst_masks_on(path, rj["origin_mm"], shape, to_px)
        prev = C.render_on(path, rj["origin_mm"], shape, to_px, bg=(62, 61, 62))
        segs = stop_segments(path, rj["origin_mm"])
        for q in sec:
            r = sprite_gate(q, M, to_px, shape, ART[q["id"]]); r.update(art_gate(q, M, to_px, shape, ART[q["id"]], rj, segs))
            r["ok"] = bool(r["ok"] and r["art_ok"]); r["file"] = stem.split("_")[2]; rows.append(r)
            cx, cy = to_px(q["x_from_side_mm"], q["y_from_waist_mm"]); h = 13 * PPM
            st = prev.crop((int(cx - h), int(cy - h), int(cx + h), int(cy + h)))
            # mockup crop at the same mm scale: 13 mm each way around the traced centre (sprites are not moved)
            px, py = q["px"]; hp = 13 / mmpx
            mk = mock.crop((int(round(px - hp)), int(round(py - hp)), int(round(px + hp)), int(round(py + hp)))).resize(st.size, Image.LANCZOS)
            tiles.append((r, mk, st))
    json.dump(dict(dst_dir=dst_dir, rows=rows, limits=dict(pos_mm=POS_MAX, cover=COVER_MIN, eye_mm=EYE_MAX, limb_mm=LIMB_MAX, limb_cover=LIMB_COVER,
                   gaze_agree_mm=GAZE_AGREE, gaze_mm=GAZE_MAX, eye_area=EYE_AREA_TOL, row_gap_mm=ROW_GAP_MAX, split=SPLIT_MIN)), open(out, "w"), indent=1)
    sheet(tiles, sheet_png)
    for r in rows: print(r)
    return rows

def sheet(tiles, png="out/compare_soot.png"):
    T = 520; pad = 24; per = 3
    rowsN = math.ceil(len(tiles) / per); W = pad + per * (2 * T + 3 * pad); H = 190 + rowsN * (T + 90)
    im = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(im)
    d.text((pad, 20), "Compare — 07 soot sprites (founder 21 Oct: kept): garment mockup (left) vs stitch preview from the shipped DST (right)", fill=(20, 20, 20), font=C.font(40))
    d.text((pad, 74), "Same scale: 26 x 26 mm tiles around each traced centre. Mockup ~1 mm per px: limbs, eye size and gaze come from the hand-read art table (inputs/soot_art.json).", fill=(90, 90, 90), font=C.font(26))
    d.text((pad, 108), f"Gate: centre <= {POS_MAX} mm, cover >= {COVER_MIN:.0%}, 2 eyes; limbs = table; pupils agree <= {GAZE_AGREE} mm + match the gaze; eye area +-{EYE_AREA_TOL:.0%}; eye satin rows <= {ROW_GAP_MAX} mm, no split.", fill=(90, 90, 90), font=C.font(26))
    for k, (r, mk, st) in enumerate(tiles):
        rr, cc = divmod(k, per); x = pad + cc * (2 * T + 3 * pad); y = 170 + rr * (T + 90)
        im.paste(mk.resize((T, T), Image.LANCZOS), (x, y)); im.paste(st.resize((T, T), Image.LANCZOS), (x + T + pad, y))
        col = (20, 140, 60) if r["ok"] else (200, 30, 30)
        d.text((x, y + T + 8), f"{r['file']} {r['id']}  limbs {r['limbs_dst']}/{r['limbs_art']} · gaze {r['gaze_agree_mm']}/{r['gaze_err_mm']} · eye {r['eye_area_err_pct']}% · rows {r['row_gap_mm']} mm · split {r['split']}  {'PASS' if r['ok'] else 'FAIL'}", fill=col, font=C.font(28))
    im.save(png)

if __name__ == "__main__":
    import sys
    if "--b7" in sys.argv:          # red evidence: the shipped Rev B7 DSTs (tests/fixtures/konpeito_b7) against the B8 art table
        run("../../tests/fixtures/konpeito_b7", "out/gates_soot_b7.json", "out/compare_soot_b7.png")
    else:
        run()
