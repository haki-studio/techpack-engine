"""Soot sprites on the front leg (07, founder J5 21 Oct: KEPT) — gates + compare sheet.
Per sprite, from the shipped DST (07a / 07b) vs the C5 map (out/front_stars.json["soot"], traced from the mockup):
  position  centre of the sewn black body vs the map centre            <= POS_MAX mm
  cover     traced body disc covered by thread (any colour)            >= COVER_MIN  (A15)
  eyes      white eye blobs sewn inside the body                       == 2, each within EYE_MAX mm of its map position
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
SOOT_HEX, WHITE_HEX = kjcore.KJ_PAL["kj_soot"][0].upper(), kjcore.KJ_PAL["kj_white"][0].upper()
FILES = {"front1": "HAKI_KJ_07a_front-leg-trail-upper", "front2": "HAKI_KJ_07b_front-leg-trail-lower"}

def sprite_gate(q, M, to_px, shape):
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
    exp = [to_px(q["x_from_side_mm"] + e[0], q["y_from_waist_mm"] + e[1]) for e in q["eyes_mm"]]
    eye_err = max((min(math.dist(e, f) for f in eyes) / PPM if eyes else 99.0) for e in exp)
    ok = pos <= POS_MAX and cover >= COVER_MIN and len(eyes) == 2 and eye_err <= EYE_MAX
    return dict(id=q["id"], pos_mm=round(pos, 2), cover_pct=round(100 * cover, 1), eyes=len(eyes), eye_err_mm=round(eye_err, 2), ok=bool(ok))

def run():
    F = json.load(open("out/front_stars.json")); soot = {q["id"]: q for q in F["soot"]}
    rows, tiles = [], []
    G = kjfront.geometry(); mmpx = G["mmpx"]
    mock = Image.open(kjfront.SRC).convert("RGB")
    for k, stem in FILES.items():
        sec = [soot[i] for i in F["sections"][int(k[-1]) - 1] if i in soot]
        if not sec: continue
        rj = json.load(open(f"out/stitch/{stem}.json")); path = f"out/stitch/{stem}.dst"
        allpts = F["stars"] + F["soot"]; byid = {d["id"]: d for d in allpts}
        ids = F["sections"][int(k[-1]) - 1]
        xs = [byid[i]["x_from_side_mm"] for i in ids]; ys = [byid[i]["y_from_waist_mm"] for i in ids]
        x0, y0 = min(xs) - 14, min(ys) - 14; W, H = max(xs) - min(xs) + 28, max(ys) - min(ys) + 28
        to_px = lambda x, y, x0=x0, y0=y0: ((x - x0) * PPM, (y - y0) * PPM)
        shape = (int(round(H * PPM)), int(round(W * PPM)))
        M = C.dst_masks_on(path, rj["origin_mm"], shape, to_px)
        prev = C.render_on(path, rj["origin_mm"], shape, to_px, bg=(62, 61, 62))
        for q in sec:
            r = sprite_gate(q, M, to_px, shape); r["file"] = stem.split("_")[2]; rows.append(r)
            cx, cy = to_px(q["x_from_side_mm"], q["y_from_waist_mm"]); h = 13 * PPM
            st = prev.crop((int(cx - h), int(cy - h), int(cx + h), int(cy + h)))
            # mockup crop at the same mm scale: 13 mm each way around the traced centre (sprites are not moved)
            px, py = q["px"]; hp = 13 / mmpx
            mk = mock.crop((int(round(px - hp)), int(round(py - hp)), int(round(px + hp)), int(round(py + hp)))).resize(st.size, Image.LANCZOS)
            tiles.append((r, mk, st))
    json.dump(dict(rows=rows, limits=dict(pos_mm=POS_MAX, cover=COVER_MIN, eye_mm=EYE_MAX)), open("out/gates_soot.json", "w"), indent=1)
    sheet(tiles)
    for r in rows: print(r)
    return rows

def sheet(tiles):
    T = 520; pad = 24; per = 3
    rowsN = math.ceil(len(tiles) / per); W = pad + per * (2 * T + 3 * pad); H = 190 + rowsN * (T + 90)
    im = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(im)
    d.text((pad, 20), "Compare — 07 soot sprites (founder 21 Oct: kept): garment mockup (left) vs stitch preview from the shipped DST (right)", fill=(20, 20, 20), font=C.font(40))
    d.text((pad, 74), "Same scale: 26 x 26 mm tiles around each traced centre. The mockup is low-res (~1 mm per px): the sprite is redrawn from it (uniform body Ø, fuzz, eyes", fill=(90, 90, 90), font=C.font(26))
    d.text((pad, 108), f"+ pupils traced per sprite, 2 legs). Konpeito on the DST are 10 mm (house size) vs ~8.7 mm on the mockup. Gate: centre <= {POS_MAX} mm, cover >= {COVER_MIN:.0%}, 2 eyes <= {EYE_MAX} mm.", fill=(90, 90, 90), font=C.font(26))
    for k, (r, mk, st) in enumerate(tiles):
        rr, cc = divmod(k, per); x = pad + cc * (2 * T + 3 * pad); y = 170 + rr * (T + 90)
        im.paste(mk.resize((T, T), Image.LANCZOS), (x, y)); im.paste(st.resize((T, T), Image.LANCZOS), (x + T + pad, y))
        col = (20, 140, 60) if r["ok"] else (200, 30, 30)
        d.text((x, y + T + 8), f"{r['file']} {r['id']}  centre {r['pos_mm']} mm · cover {r['cover_pct']} % · eyes {r['eyes']} ({r['eye_err_mm']} mm)  {'PASS' if r['ok'] else 'FAIL'}", fill=col, font=C.font(28))
    im.save("out/compare_soot.png")

if __name__ == "__main__":
    run()
