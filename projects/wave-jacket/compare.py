"""Fidelity sheets: out/compare_<piece>.png = the render mapped into that piece's pattern mm (same map the art uses) |
stitch-by-stitch render of the SHIPPED full DST of that size at the same scale, + 4 zoomed pairs (render zooms Lanczos x4 from the source, which adds
no detail). Plus out/compare_<size>.png with all five pieces.  usage: ./py.sh compare.py [size]"""
import wavecore as WC
import pickle, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from shapely.geometry import box
from shapely.ops import unary_union
import stitchrender as SR, mockmap as MM, pieces as PC, wrap as WR

size = sys.argv[1] if len(sys.argv) > 1 else "M"
D = pickle.load(open(f"art_{size}.pkl", "rb"))
VIEWS = {"BK": [("back", None)], "FR": [("front", None)], "FL": [("front", None)],
         "SR": [("back", "R"), ("front", "R")], "SL": [("back", "L"), ("front", "L")]}

def mock(P, bb, ppm):
    W, H = int((bb[2]-bb[0])*ppm), int((bb[3]-bb[1])*ppm)
    if P in ("BK", "FR", "FL"):
        im = MM.warp_body(VIEWS[P][0][0], size, bb, ppm)
    else:
        out = np.full((H, W, 3), 255, np.uint8)
        XX, YY = np.meshgrid(bb[0] + (np.arange(W) + 0.5) / ppm, bb[1] + (np.arange(H) + 0.5) / ppm)
        from scipy.ndimage import map_coordinates
        from shapely import contains_xy
        for view, side in VIEWS[P]:
            sm = WR.sleeve_map(view, side, size)                      # the seam-length harmonic map the art uses (Rev B)
            q = sm.inv(np.c_[XX.ravel(), YY.ravel()]); px, py = q[:, 0].reshape(XX.shape), q[:, 1].reshape(XX.shape)
            fin = np.isfinite(px); px = np.where(fin, px, 0); py = np.where(fin, py, 0)
            m = fin & ((XX * sm.sgn) >= 0) & contains_xy(sm.quad_px, px, py)
            a = np.asarray(MM.image(view)).astype(np.float32)
            for c in range(3): out[..., c] = np.where(m, map_coordinates(a[..., c], [py, px], order=1).clip(0, 255), out[..., c])
        im = Image.fromarray(out)
    # outside the panel: white
    pan = PC.panel(size, P); msk = Image.new("L", im.size, 0); d = ImageDraw.Draw(msk)
    d.polygon([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in pan.exterior.coords], fill=255)
    wh = Image.new("RGB", im.size, (255, 255, 255)); wh.paste(im, (0, 0), msk)
    return wh

import json, pyembroidery as pe, motifs2
LIVE = True
_PATS = {}
def dst_pat(P):
    """the shipped full DST of this size + its origin (result json) + colour per DST stop (read-back record)"""
    if P not in _PATS:
        r = json.load(open(f"out/01_wave/{size}/result_{P}.json"))["full"]
        _PATS[P] = (pe.read(r["file"] + ".dst"), [motifs2.HEX[s["col"]] for s in r["per_stop"]], r["origin"])
    return _PATS[P]
def dst_render(P, bb, ppm):
    """every sewn stitch of the DST drawn as a 0.4 mm line in its stop colour (travel included, jumps/trims not drawn)"""
    p, cols, (ox, oy) = dst_pat(P); x0, y0, x1, y1 = bb
    im = Image.new("RGB", (int((x1-x0)*ppm), int((y1-y0)*ppm)), tuple(int(WC.FABRIC[i:i+2], 16) for i in (1, 3, 5)))
    d = ImageDraw.Draw(im); lw = max(1, int(round(0.4*ppm))); ci = 0; prev = None
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK; q = ((x/10 + ox - x0)*ppm, (y/10 + oy - y0)*ppm)
        if k == pe.STITCH:
            if prev is not None: d.line([prev, q], fill=cols[min(ci, len(cols)-1)], width=lw)
            prev = q
        elif k == pe.COLOR_CHANGE: ci += 1; prev = None
        elif k in (pe.TRIM, pe.JUMP): prev = None
    import live
    rec = json.load(open(f"out/01_wave/{size}/result_{P}.json"))["full"].get("chenille")
    if rec: live.draw_chenille(im, rec, bb, ppm, live=False)          # primary foam = the chenille file, same origin
    return im
def stitch(P, bb, ppm):
    import live
    st = live.live_piece(P, bb, ppm) if LIVE else dst_render(P, bb, ppm)          # live view (LESSONS A16), every stitch
    pan = PC.panel(size, P); msk = Image.new("L", st.size, 0); d = ImageDraw.Draw(msk)
    d.polygon([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in pan.exterior.coords], fill=255)
    wh = Image.new("RGB", st.size, (255, 255, 255)); wh.paste(st, (0, 0), msk)
    d2 = ImageDraw.Draw(wh)
    d2.line([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in PC.clip_for(size, P).exterior.coords], fill=(255, 80, 80), width=1)
    return wh

def zooms(P, n=4, w=70.0, h=60.0):
    vis = D[P]; foam = unary_union([r["geom"] for r in vis if r["grp"] in ("FM", "FM-sh", "FM-gr")])
    band = unary_union([r["geom"] for r in vis if r["grp"] in ("WV", "RP")]); drop = unary_union([r["geom"] for r in vis if r["grp"] == "DR"])
    b = unary_union([r["geom"] for r in vis]).bounds; cands = []
    for x in np.arange(b[0], b[2] - w * 0.6, w / 3):
        for y in np.arange(b[1], b[3] - h * 0.6, h / 3):
            bx = box(x, y, x + w, y + h)
            fa, ba, da = foam.intersection(bx).area, band.intersection(bx).area, drop.intersection(bx).area
            cands.append((fa * 1.0 + ba * 0.6 + da * 3 + 2 * min(fa, ba), bx))
    cands.sort(key=lambda t: -t[0]); out = []
    for sc, bx in cands:
        if all(not bx.buffer(-5).intersects(o) for o in out): out.append(bx)
        if len(out) == n: break
    return [o.bounds for o in out]

def sheet(P, ppm=1.6):
    b0 = PC.panel(size, P).bounds; bb = (b0[0] - 5, b0[1] - 5, b0[2] + 5, b0[3] + 5)
    mk, st = mock(P, bb, ppm), stitch(P, bb, ppm)
    W, H = st.size; zw = 360; Z = zooms(P)
    out = Image.new("RGB", (W*2 + 40 + zw*2 + 30, max(H + 40 + 175, 4*(zw*6//7 + 34) + 30)), (255, 255, 255))
    out.paste(mk, (10, 30)); out.paste(st, (W + 30, 30)); d = ImageDraw.Draw(out)
    d.text((10, 10), f"RENDER {P} {PC.NAME[P]} (mockup mapped to size-{size} pattern mm)", fill=(0, 0, 0))
    d.text((W + 30, 10), f"SHIPPED DST {P} size {size}, LIVE VIEW (dstlive: every stitch, thread width + sheen; red = keep-out line)", fill=(0, 0, 0))
    direction_overlay(out, P, bb, ppm, W + 30, 30)
    x0 = W*2 + 50; y = 30
    for zb in Z:
        zp = zw / (zb[2] - zb[0])
        a = mock(P, zb, zp / 4.0).resize((zw, int((zb[3]-zb[1])*zp)), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
        s_ = stitch(P, zb, zp)                                    # live view at the zoom scale
        out.paste(a, (x0, y)); out.paste(s_, (x0 + zw + 10, y))
        d.text((x0, y - 13), f"x {zb[0]:.0f}..{zb[2]:.0f}, y {zb[1]:.0f}..{zb[3]:.0f} mm  (render x4 | shipped DST)", fill=(0, 0, 0))
        for (X, Y) in ((10, 30), (W + 30, 30)):
            d.rectangle([X + (zb[0]-bb[0])*ppm, Y + (zb[1]-bb[1])*ppm, X + (zb[2]-bb[0])*ppm, Y + (zb[3]-bb[1])*ppm], outline=(255, 60, 60), width=2)
        y += a.height + 34
    gate_table(out, P, 10, H + 50)
    out.save(f"out/compare_{P}.png"); return out.size

def direction_overlay(im, P, bb, ppm, X, Y):
    """A16 heat-map: tiles where the DST stitch direction deviates > 25 deg from the reference grain (orange) or is chaotic
    (red), from gates_M.json (qa.direction_match on the shipped DST)"""
    import json as _j, os as _o
    if not _o.path.exists(f"gates_{size}.json"): return
    g = _j.load(open(f"gates_{size}.json"))["pieces"][P].get("direction")
    if not g: return
    d = ImageDraw.Draw(im); T = g["tile_mm"]
    for kind, col in (("fail_dev", (255, 150, 0)), ("fail_chaos", (255, 0, 0))):
        for t_ in g[kind]:
            cx, cy = t_["at_mm"]; x0 = X + (cx - T / 2 - bb[0]) * ppm; y0 = Y + (cy - T / 2 - bb[1]) * ppm
            d.rectangle([x0, y0, x0 + T * ppm, y0 + T * ppm], outline=col, width=2)

def gate_table(im, P, x, y):
    """LESSONS A14 / A15 gate tables (gates.py on the shipped DST) + the render-vs-DST motif counts (review item 9)"""
    import json as _j, os as _o
    d = ImageDraw.Draw(im)
    if not _o.path.exists(f"gates_{size}.json"):
        d.text((x, y), "gates_M.json missing - run gates.py", fill=(200, 0, 0)); return
    G = _j.load(open(f"gates_{size}.json")); g = G["pieces"][P]; mode = G.get("mode")
    d.text((x, y), f"FIDELITY GATES (LESSONS A14 qa.motif_match / A15 qa.uncovered) on the shipped DST, {P} size {size} ({mode})", fill=(0, 0, 0)); y += 16
    hd = ["family", "render motifs", "DST motifs", "pass", "FAIL", "moved > 3 mm (max)", "IoU median", "width/height ratio min"]
    xs = [x, x + 80, x + 180, x + 270, x + 320, x + 380, x + 520, x + 610]
    for xx, h in zip(xs, hd): d.text((xx, y), h, fill=(90, 90, 90))
    y += 14
    for fam in ("curls", "drops", "stripes"):
        f_ = g[fam]; rows = f_["rows"]; mv = [r_.get("moved_mm", 0) or 0 for r_ in rows]; mvn = [v for v in mv if v > 3]
        fail = f_["n"] - f_["passed"]
        wr = min([min(r_["w_ratio"], r_["h_ratio"]) for r_ in rows], default=0)
        vals = [fam, f"{f_['n']}", f"{f_.get('dst_count', '-')}", f"{f_['passed']}", f"{fail}", f"{len(mvn)} ({max(mvn) if mvn else 0:.0f} mm)",
                f"{np.median([r_['iou'] for r_ in rows]):.2f}" if rows else "-", f"{wr:.2f}" if rows else "-"]
        for xx, v in zip(xs, vals): d.text((xx, y), v, fill=(200, 0, 0) if (v == vals[4] and fail) else (0, 0, 0))
        y += 14
    dr = g.get("direction")
    if dr: d.text((x, y), f"STITCH DIRECTION (A16, qa.direction_match, 8 mm tiles): {dr['pct_ok']} % OK of {dr['tiles']} tiles - {len(dr['fail_dev'])} off the reference grain > 25 deg (orange boxes), {len(dr['fail_chaos'])} chaotic (red boxes); deliver at >= 85 %",
                  fill=(0, 120, 50) if dr["pct_ok"] >= 85 else (200, 0, 0)); y += 14
    if dr and dr.get("by_family"):
        d.text((x + 10, y), "   by family (visible stitches): " + " · ".join(f"{k} {v['pct_ok']} % of {v['tiles']} ({v['tile_mm']:.0f} mm tiles)" for k, v in dr["by_family"].items()), fill=(60, 60, 60)); y += 14
    un = g["uncovered"]; ue = [u for u in un if u["why"] == "UNEXPLAINED"]
    d.text((x, y), f"uncovered >= 25 mm2: {len(un)} areas ({sum(u['area_mm2'] for u in un):.0f} mm2) - keep-out edge {sum(1 for u in un if u['why']=='keep-out edge')}, moved by the wrap {sum(1 for u in un if u['why']=='moved by the wrap')}, UNEXPLAINED {len(ue)}",
           fill=(200, 0, 0) if ue else (0, 120, 50)); y += 14
    for u in un[:6]:
        d.text((x + 10, y), f"({u['x_mm']:.0f}, {u['y_mm']:.0f}) {u['w_mm']:.0f} x {u['h_mm']:.0f} mm, {u['area_mm2']:.0f} mm2 - {u['why']}", fill=(90, 90, 90)); y += 13

if __name__ == "__main__":
    for P in PC.PIECES: print(P, sheet(P))
