"""Fidelity gates (LESSONS A14/A15) + compare sheets out/compare_<element>.png: mockup vs stitch preview from the DST,
same scale, zoomed regions, motif_match table per motif family and the uncovered-area table."""
import json, math, pickle
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
import kjcore
import pyembroidery as pe
import qa
import kjstitch as K

PPM = 20
FONT = "inputs/fonts/ZenMaruGothic-Bold.ttf"
def font(sz):
    try: return ImageFont.truetype(FONT, sz)
    except Exception: return ImageFont.load_default()

def dst_masks_on(path, origin, grid_shape, to_px):
    """per-thread coverage masks of the DST drawn on a reference grid. to_px(x_mm, y_mm) maps design mm -> grid px."""
    p = pe.read(path); cols = [t.hex_color().upper() for t in pe.read(path[:-4] + ".pes").threadlist]
    Hh, Ww = grid_shape
    ims = {}; ci = 0; prev = None
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK
        P = to_px(x / 10 + origin[0], y / 10 + origin[1])
        if k == pe.STITCH:
            if prev is not None:
                c = cols[min(ci, len(cols) - 1)]
                for key in (c, ci):
                    if key not in ims: ims[key] = Image.new("L", (Ww, Hh), 0)
                    ImageDraw.Draw(ims[key]).line([prev, P], fill=255, width=max(1, int(round(0.35 * PPM))))
            prev = P
        elif k == pe.COLOR_CHANGE: ci += 1; prev = None
        elif k == pe.TRIM: prev = None
        elif k == pe.JUMP: prev = P
        elif k == pe.END: break
    return {c: ndi.binary_closing(np.array(im) > 0, iterations=2) for c, im in ims.items()}

HEX = {k: v[0].upper() for k, v in kjcore.KJ_PAL.items()}
def U(masks, *keys):
    out = None
    for k in keys:
        m = masks.get(HEX[k])
        if m is None: continue
        out = m.copy() if out is None else (out | m)
    return out

def S_(masks, *idx):
    """union of the masks of these stop numbers (1-based, as on the G pages)"""
    out = None
    for i in idx:
        m = masks.get(i - 1)
        if m is not None: out = m.copy() if out is None else (out | m)
    return out

def gate(ref, out, ppm, near_mm=1.5, **kw):
    """qa.motif_match per traced motif, each against the stitches of the stop(s) that sew its family lying within
    near_mm of THAT motif: the motifs touch their neighbours (letters, overlapping candies), so the DST shapes merge and
    a whole-family comparison would compare a word with a letter."""
    if out is None: out = np.zeros_like(ref)
    lab, n = ndi.label(ref); rows = []
    it = max(1, int(near_mm * ppm))
    for k, sl in enumerate(ndi.find_objects(lab), 1):
        m = lab == k
        if m.sum() / ppm ** 2 < kw.get("min_mm2", 4.0): continue
        o = out & ndi.binary_dilation(m, iterations=it)
        r = qa.motif_match(m, o, ppm, **kw)
        for q in r: q["motif"] = k
        rows += r
    return rows

import kjletter as KL

TINT = {"kj_pink": "kj_pink_hi", "kj_yellow": "kj_yellow_hi", "kj_blue": "kj_blue_hi"}
KP_CODES = ["KP", "KP-hi", "KPB", "KPB-hi", "STAR", "STAR-hi", "KNOT"]
def outline_p90(r, o, ppm=PPM):
    """p90 distance (mm) from the reference outline to the DST outline and back. IoU alone passes a 5-point star
    against a konpeito (0.85, red test 20 Oct); the outline does not (star 1.3-1.5 mm vs konpeito 0.4 mm)."""
    edge = lambda m: m & ~ndi.binary_erosion(m)
    o = ndi.binary_fill_holes(ndi.binary_opening(o, iterations=2))
    if not o.any(): return 99.0, 99.0
    dt_o = ndi.distance_transform_edt(~edge(o)) / ppm; dt_r = ndi.distance_transform_edt(~edge(r)) / ppm
    return round(float(np.percentile(dt_o[edge(r)], 90)), 2), round(float(np.percentile(dt_r[edge(o)], 90)), 2)
OUTLINE_MAX = 0.7

def candy_gate(cands, M, rj, ppm=PPM, near_mm=0.3, iou_min=0.70, ratio_min=0.80):
    """A14 per konpeito (reviewer PR #29 item 6 / LESSONS A21): one row per candy, never per merged blob.
    cands: [(label, full mask, body thread)] on the DST grid. Each candy is digitised as its FULL SVG shape (back-row
    candies are sewn whole, the front row lands on top), so the reference is the candy's own full cairosvg mask and the
    DST side is only that candy's own stops (back row: KPB codes; front: KP / STAR + its white specks) within near_mm of
    it. visible_mm2 reports how much of it stays visible after the candies sewn later."""
    rows = []; it = max(1, int(round(near_mm * ppm)))
    for i, (label, m, col) in enumerate(cands):
        later = [c[1] for c in cands[i + 1:]]
        vis = m & ~np.any(later, axis=0) if later else m
        back = "back row" in label
        codes = ["KPB", "KPB-hi"] if back else ["KP", "KP-hi", "STAR", "STAR-hi"]
        st = stops_of(rj, col, codes) + stops_of(rj, TINT[col], codes) + ([] if back else stops_of(rj, "kj_white", ["KNOT"]))
        o = S_(M, *sorted(set(st)))
        o = (o if o is not None else np.zeros_like(m)) & ndi.binary_dilation(m, iterations=it)
        iou = (m & o).sum() / max((m | o).sum(), 1)
        def ext(q, ax):
            idx = np.nonzero(q.any(axis=ax))[0]; return (idx[-1] - idx[0] + 1) / ppm if len(idx) else 0.0
        wr, hr = ext(o, 0) / max(ext(m, 0), 1e-9), ext(o, 1) / max(ext(m, 1), 1e-9)
        p_r, p_o = outline_p90(m, o, ppm)
        ok = bool(iou >= iou_min and min(wr, 1 / max(wr, 1e-9)) >= ratio_min and min(hr, 1 / max(hr, 1e-9)) >= ratio_min
                  and max(p_r, p_o) <= OUTLINE_MAX)
        ys, xs = np.nonzero(m)
        rows.append(dict(family=label, motifs=1, passed=int(ok), min_iou=round(float(iou), 2), mean_iou=round(float(iou), 2),
                         x_mm=round(float(xs.mean()) / ppm, 1), y_mm=round(float(ys.mean()) / ppm, 1),
                         visible_mm2=round(float(vis.sum()) / ppm ** 2, 1), w_ratio=round(float(wr), 2), h_ratio=round(float(hr), 2), outline_p90=max(p_r, p_o), ok=ok))
    return rows
def stops_of(rj, col, codes):
    """1-based stop numbers that sew colour col with any of codes (from the read-back json)."""
    return [i + 1 for i, st in enumerate(rj["per_stop"]) if st.get("col") == col and set(st.get("codes", [])) & set(codes)]

def exposed_for(name, path, rj):
    """exposed stitch floats in the shipped DST (kjletter.exposed_stitches) for one element."""
    A = pickle.load(open("out/art.pkl", "rb"))
    vis = [r for r in A[name]["vis"] if not r["geom"].is_empty]
    stops = K.stops_for(vis, K.FILES[name][1])
    from shapely.ops import unary_union as UU
    return KL.exposed_stitches(path, rj["origin_mm"], [UU([r["geom"] for r in s["regions"]]) for s in stops])

def live_and_dir(path, rj, rect):
    import dstlive
    cols = [t.hex_color() for t in pe.read(path[:-4] + ".pes").threadlist]
    live = dstlive.render(path, colours=cols, ppm=30, shell="#1f1f22")
    try:
        dm = qa.direction_match(np.asarray(rect.convert("L"), float), PPM, qa.dst_segments(path, tuple(rj["origin_mm"])))
        dm = dict(pct_ok=round(float(dm["pct_ok"]), 1), fail_dev=dm["fail_dev"], fail_chaos=dm["fail_chaos"], tiles=dm["tiles"])
    except Exception as e:
        print("direction_match skipped:", e); dm = None
    return live, dm

def cl_rows(path, rj, items):
    """items: [(label, ref_mask, colour, codes, thread, pull)] -> centreline gate rows (kjletter.cl_gate)."""
    seq = KL.read_seq(path); ox, oy = rj["origin_mm"]; out = []
    for label, ref, col, codes, thread, pull in items:
        st = {i - 1 for i in stops_of(rj, col, codes)}
        om = KL.dst_mask(seq, None, ref.shape, lambda x, y: ((x + ox) * PPM, (y + oy) * PPM), st, KL.THREAD_D[thread])
        out.append(KL.cl_gate(label, ref, om, pull=pull))
    return out

def summarise(name, fam_rows):
    S = []
    for fam, rows in fam_rows.items():
        n = len(rows); ok = sum(r["ok"] or r.get("house_min", False) for r in rows); hm = sum(r.get("house_min", False) for r in rows)
        if hm: fam = f"{fam} — {hm} at house-min dot Ø1.1 (art Ø1.0)"
        S.append(dict(family=fam, motifs=n, passed=ok, min_iou=min([r["iou"] for r in rows], default=None),
                      mean_iou=round(float(np.mean([r["iou"] for r in rows])), 2) if rows else None))
    return S

def zoom_sheet(name, ref_img, prev_img, zooms, table, unc, title, notes, cl=None, exposed=None, prev_hi=None, hs=2, live=None, dirm=None):
    """ref_img/prev_img: PIL at the same px/mm. zooms: [(x0,y0,x1,y1) px]."""
    W = 2400; pad = 30
    s = (W - 3 * pad) / 2 / ref_img.width
    a = ref_img.resize((int(ref_img.width * s), int(ref_img.height * s)))
    b = prev_img.resize(a.size)
    zh = 360
    lv = live.resize((W - 2 * pad, int(live.height * (W - 2 * pad) / live.width)), Image.LANCZOS) if live is not None else None
    H = 120 + a.height + 2 * pad + (int(zh * 1.25) + 90) * len(zooms) + 60 + ((lv.height + 80) if lv is not None else 0) + 40 + 34 * (len(table) + 6 + len(unc)) + 34 * (len(cl or []) + 4) + 32 * len(notes) + 60
    im = Image.new("RGB", (W, int(H)), "white"); d = ImageDraw.Draw(im)
    d.text((pad, 20), title, fill=(20, 20, 20), font=font(40))
    d.text((pad, 72), "LEFT: art reference (same scale)   RIGHT: stitch preview drawn from the shipped DST, same scale", fill=(90, 90, 90), font=font(26))
    im.paste(a, (pad, 120)); im.paste(b, (2 * pad + a.width, 120))
    y = 120 + a.height + pad
    if lv is not None:
        d.text((pad, y), "LIVE VIEW of the shipped DST (engine/dstlive: real thread width, sheen by stitch angle, like Hatch) — read the stitch direction here", fill=(20, 20, 20), font=font(28))
        im.paste(lv, (pad, y + 40)); y += lv.height + 80
    col = 0; rowh = 0
    for i, (x0, y0, x1, y1) in enumerate(zooms):
        ca = ref_img.crop((x0, y0, x1, y1))
        cb = prev_hi.crop((x0 * hs, y0 * hs, x1 * hs, y1 * hs)) if prev_hi is not None else prev_img.crop((x0, y0, x1, y1))
        wide = ca.width / ca.height > 1.3                     # wide zooms (lettering lines) get a whole row
        if wide or col == 1 and rowh and False: pass
        if wide and col == 1: y += rowh + 60; col = 0; rowh = 0
        avail = (W - 3 * pad) / 2 if wide else (W // 2 - 40) / 2
        zs = min((zh * 1.25 if wide else zh) / ca.height, avail / ca.width)
        ca = ca.resize((int(ca.width * zs), int(ca.height * zs)), Image.LANCZOS); cb = cb.resize(ca.size, Image.LANCZOS)
        xx = pad + col * (W // 2)
        im.paste(ca, (xx, y + 30)); im.paste(cb, (xx + ca.width + (pad if wide else 10), y + 30))
        rowh = max(rowh, ca.height + 30)
        d.text((xx, y), f"zoom {i + 1}: x {x0 / PPM:.0f}-{x1 / PPM:.0f}, y {y0 / PPM:.0f}-{y1 / PPM:.0f} mm (reference | DST)", fill=(60, 60, 60), font=font(24))
        if wide or col == 1: y += rowh + 60; col = 0; rowh = 0
        else: col = 1
    y += rowh + 40
    if cl:
        d.text((pad, y), "Lettering + line art: centreline gate (reference skeleton vs DST skeleton; mean distance <= 0.5 mm, visible width within +-20 %)", fill=(20, 20, 20), font=font(30)); y += 42
        hdr2 = [("string / line", 0), ("mean dist mm", 520), ("p90 mm", 760), ("width ref", 960), ("width DST", 1200), ("ratio", 1420), ("result", 1580)]
        for h_, xo in hdr2: d.text((pad + xo, y), h_, fill=(90, 90, 90), font=font(26))
        y += 34
        for r in cl:
            okc = (30, 140, 60) if r["ok"] else (180, 40, 30)
            vals = [r["family"], r["mean_d"], r["p90_d"], r["w_ref"], r["w_dst"], r["ratio"], "PASS" if r["ok"] else "FAIL"]
            for (h_, xo), v in zip(hdr2, vals): d.text((pad + xo, y), str(v), fill=okc if h_ == "result" else (20, 20, 20), font=font(26))
            y += 34
        y += 16
    d.text((pad, y), "A14 motif_match per family (IoU >= 0.70, width + height >= 80 %)", fill=(20, 20, 20), font=font(30)); y += 42
    hdr = ["family", "motifs", "pass", "min IoU", "mean IoU"]
    for j, h_ in enumerate(hdr): d.text((pad + j * 300, y), h_, fill=(90, 90, 90), font=font(26))
    y += 34
    for r in table:
        okc = (30, 140, 60) if r["motifs"] and r["passed"] == r["motifs"] else (180, 40, 30)
        for j, k in enumerate(["family", "motifs", "passed", "min_iou", "mean_iou"]):
            d.text((pad + j * 300, y), str(r[k]), fill=okc if j == 2 else (20, 20, 20), font=font(26))
        y += 34
    y += 10
    d.text((pad, y), "A15 uncovered areas >= 25 mm2 (design says embroidered, DST bare): " + ("none" if not unc else ""), fill=(20, 20, 20), font=font(28)); y += 38
    for u in unc:
        d.text((pad + 20, y), f"x {u['x_mm']} y {u['y_mm']} mm, {u['w_mm']} x {u['h_mm']} mm, {u['area_mm2']} mm2 — {u.get('why', '')}", fill=(20, 20, 20), font=font(24)); y += 34
    if dirm is not None:
        d.text((pad, y), f"A16 direction_match (8 mm tiles vs the mockup's thread grain): {dirm['pct_ok']} % tiles OK"
               f" ({len(dirm['fail_dev'])} off-direction, {len(dirm['fail_chaos'])} chaotic) — reported; mockup grain at ~17 px/mm is a weak reference",
               fill=(30, 140, 60) if dirm['pct_ok'] >= 85 else (180, 40, 30), font=font(26)); y += 38
    if exposed is not None:
        d.text((pad, y), f"Exposed stitches (DST read-back: > 1 mm of a stitch off its own art and not under a later stop): {len(exposed) if exposed else 'none'}"
               + ("" if not exposed else "  — " + ", ".join(f"stop {s} at x {x} y {yy} ({l} mm)" for s, x, yy, l in exposed[:6])),
               fill=(30, 140, 60) if not exposed else (180, 40, 30), font=font(26)); y += 38
    for n_ in notes:
        d.text((pad, y), n_, fill=(90, 90, 90), font=font(24)); y += 32
    im = im.crop((0, 0, W, y + 20))
    im.save(f"out/compare_{name}.png")

FAM = {   # family -> (colour(s), codes, kind, thread, pull)
    "wb": {"frame (red)": (["kj_red"], ["TXC"], "cl", "40wt", 0.10), "hearts (pink)": (["kj_pink"], ["TXC"], "cl", "40wt", 0.10),
           "flowers (petals)": (["kj_pink", "kj_yellow", "kj_blue"], ["FL"], "iou", None, 0), "flower centres (white)": (["kj_white"], ["KNOT"], "iou", None, 0),
           "cheeks (rose)": (["kj_rose"], ["DOT"], "iou", None, 0), "face line art (black)": (["kj_black"], ["LINE"], "cl", "60wt", 0.0),
           "元気でね / また会おうね (black)": (["kj_black"], ["TXC"], "cl", "60wt", 0.10), "ちひろ (red)": (["kj_red"], ["TXC"], "cl", "40wt", 0.10),
           "理砂 (blue)": (["kj_blue"], ["TXC"], "cl", "40wt", 0.10), "accent dots (red)": (["kj_red"], ["DOT"], "iou", None, 0)},
    "coin": {"こんぺいとう (red)": (["kj_red"], ["TXC"], "cl", "40wt", 0.10),
             "accent dots (red)": (["kj_red"], ["DOT"], "iou", None, 0)},
    "spill": {},
}
STEM = {"wb": "HAKI_KJ_03_waistband-patch", "coin": "HAKI_KJ_01_coin-pocket-patch", "spill": "HAKI_KJ_02_coin-spill-facing"}

def svg_gates(name, A):
    """reference = the founder's SVG rendered per layer by cairosvg (kjsvg.layer_mask); DST masks per stop."""
    rj = json.load(open(f"out/stitch/{STEM[name]}.json")); path = f"out/stitch/{STEM[name]}.dst"
    ref = A[name]["ref"]; shape = next(iter(ref.values())).shape
    dx, dy = A[name].get("offset", (0.0, 0.0))
    to_px = lambda x, y: ((x - dx) * PPM, (y - dy) * PPM)
    M = dst_masks_on(path, rj["origin_mm"], shape, to_px)
    seq = KL.read_seq(path); ox, oy = rj["origin_mm"]
    iou, cl = {}, []
    for fam, (cols, codes, kind, thread, pull) in FAM[name].items():
        st = sorted({s for c_ in cols for s in stops_of(rj, c_, codes)})
        if kind == "iou":
            rows = gate(ref[fam], S_(M, *st), PPM, min_mm2=0.5, near_mm=0.15 if "KNOT" in codes else 0.3)   # beads 0.3 mm apart
            for r in rows:      # art dot below the house minimum satin dot (Ø1.1): sewn at the minimum, so larger
                d_art = 2 * math.sqrt(r["area_mm2"] / math.pi)
                r["house_min"] = bool(not r["ok"] and d_art < 1.15 and r["iou"] >= 0.6 and min(r["w_ratio"], r["h_ratio"]) >= 0.8)
            iou[fam] = rows
        else:
            om = KL.dst_mask(seq, None, shape, lambda x, y: ((x + ox - dx) * PPM, (y + oy - dy) * PPM), {s - 1 for s in st}, KL.THREAD_D[thread])
            cl.append(KL.cl_gate(f"{fam} {thread}", ref[fam], om, pull=pull))
    fams = summarise(name, iou)
    kp = {"coin": ("05_konpeito",), "spill": ("F",)}.get(name)
    krows = []
    if kp:
        import kjsvg
        W_, H_ = A[name]["wh"]
        krows = candy_gate([(l, m, c) for l, m, c, _ in kjsvg.candy_masks(A[name]["src"], W_, H_, kp)], M, rj)
        fams += krows
    allout = np.any([m for k_, m in M.items() if isinstance(k_, str)], axis=0)
    design = np.any(list(ref.values()), axis=0)
    unc = qa.uncovered(ndi.binary_fill_holes(design), allout, PPM)
    return dict(families=fams, rows=iou, konpeito=krows, uncovered=unc, centreline=cl,
                exposed=exposed_for(name, path, rj)), rj, path, shape, to_px

def run():
    A = pickle.load(open("out/art.pkl", "rb")); G = {}
    import kjsvg
    specs = {
        "wb": ("waistband-patch", "Compare — 03 waistband patch (ちひろ note), 80 x 54 mm: founder's vector art vs DST",
               [(160, 160, 660, 420), (360, 300, 1300, 560), (560, 470, 1540, 760), (1060, 640, 1500, 960), (180, 500, 820, 960), (900, 260, 1300, 560)]),
        "coin": ("coin-pocket-patch", "Compare — 01 coin-pocket patch (こんぺいとう), 76 x 56 mm: founder's vector art vs DST",
                 [(160, 180, 760, 520), (700, 180, 1300, 520), (200, 520, 900, 960), (860, 560, 1460, 1000)]),
        "spill": ("coin-spill", "Compare — 02 konpeito on the facing (spilling out of the coin pocket): founder's vector art vs DST",
                  [(60, 0, 700, 320), (640, 0, 1300, 320)]),
    }
    for name, (sheet, title, zooms) in specs.items():
        g, rj, path, shape, to_px = svg_gates(name, A); G[name] = g
        W_, H_ = A[name]["wh"]
        art = kjsvg.render_svg(A[name]["src"], W_, H_, PPM, bg="#F2E9D8" if name != "spill" else "#2A2A2E")
        bg = (52, 52, 56) if name != "spill" else (40, 40, 44)
        prev = render_on(path, rj["origin_mm"], shape, to_px, bg=bg)
        hi = render_on(path, rj["origin_mm"], shape, to_px, bg=bg, sc=2)
        import dstlive
        cols = [t.hex_color() for t in pe.read(path[:-4] + ".pes").threadlist]
        live = dstlive.render(path, colours=cols, ppm=30, shell="#1f1f22"); live.save(f"out/live_{sheet}.png")
        notes = ["Reference: the founder's vector art (inputs/svg), rendered per layer by cairosvg — a true input (LESSONS A14); the AI mockups are no longer the art source.",
                 "Lettering, face lines, frame, hearts: satin columns on the centrelines of the SVG outlines, ONE width per layer (art width - 0.15 mm); small rings radial.",
                 "Flowers / konpeito: one satin per petal / lobe along its axis; tint centres on top; white specks, centres, cheeks and dots = round bead satin dots."]
        if name == "spill": notes.append(f"Placement: SVG centred on the coin pocket, art bottom {kjsvg.SPILL_UNDER} mm under the pocket's top edge (hidden by the patch) [proposed — confirm].")
        zoom_sheet(sheet, art, prev, zooms, g["families"], g["uncovered"], title, notes, cl=g["centreline"], exposed=g["exposed"], prev_hi=hi, live=live)
    # ---------------- haki group (upscaled crop grid)
    rj = json.load(open("out/stitch/HAKI_KJ_04_back-pocket-L-haki.json")); ref = A["haki"]["ref"]; k = ref["k"]
    shape = ref["blue"].shape
    to_h = lambda x, y: (x / k + ref["ox"], y / k + ref["oy"])
    M = dst_masks_on("out/stitch/HAKI_KJ_04_back-pocket-L-haki.dst", rj["origin_mm"], shape, to_h)
    fam = {"'haki' (light blue)": gate(ndi.binary_closing(ref["blue"], iterations=4), U(M, "kj_blue_hi"), 1 / k, min_mm2=2.0, pad_mm=0.5)}
    G["haki"] = dict(families=summarise("haki", fam), rows=fam, uncovered=[])
    im = Image.open("inputs/back_pocket_haki.png").convert("RGB"); x0, y0, x1, y1 = (175, 405, 310, 460)
    rect = im.crop((x0, y0, x1, y1)).resize(((x1 - x0) * 8, (y1 - y0) * 8), Image.LANCZOS)
    prev = render_on("out/stitch/HAKI_KJ_04_back-pocket-L-haki.dst", rj["origin_mm"], shape, to_h, bg=(40, 40, 44), wmm=0.42 / k / PPM)
    zoom_sheet("back-pocket-haki", rect, prev, [(200, 40, 700, 400), (600, 40, 1080, 400)], G["haki"]["families"], [],
               "Compare — 04 back-pocket 'haki' + 2 stars (scaled x2.1 so the stars are 10 mm)",
               ["Mockup shown at the upscaled crop; the DST is drawn on it at the same scale (group scaled up per the founder).",
                "Stars: the founder's vector star (inputs/svg/HAKI_back-pocket-stars_ART.svg), 10 mm, at the traced centres. 'haki' is not in the SVGs: traced from inputs/back_pocket_haki.png."],
               live=__import__("dstlive").render("out/stitch/HAKI_KJ_04_back-pocket-L-haki.dst", colours=[t.hex_color() for t in pe.read("out/stitch/HAKI_KJ_04_back-pocket-L-haki.pes").threadlist], ppm=30, shell="#1f1f22"))
    kg, tiles = konpeito_gates(A); konpeito_sheet(tiles)
    for k_, v in kg.items():
        if k_ == "haki": G["haki"]["families"] += v["families"]; G["haki"]["konpeito"] = v["konpeito"]
        else: G[k_] = v
    json.dump(G, open("out/gates.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    for e, g in G.items():
        for r in g["families"]: print(e, r)
        print(e, "uncovered", g["uncovered"])
    return G

KSTEM = {"haki": "HAKI_KJ_04_back-pocket-L-haki", "starP": "HAKI_KJ_05_back-pocket-R-star-pink", "starY": "HAKI_KJ_06_back-pocket-L-lower-star-yellow",
         "front1": "HAKI_KJ_07a_front-leg-stars-upper_PROPOSED", "front2": "HAKI_KJ_07b_front-leg-stars-lower_PROPOSED"}
KNO = {"haki": "04", "starP": "05", "starY": "06", "front1": "07a", "front2": "07b"}
def konpeito_gates(A):
    """founder change 20 Oct: every konpeito on 04-07 = the 02 facing konpeito. Reference per candy = the founder's own
    02 candy paths (inputs/svg/HAKI_facing_konpeito_ART.svg), placed + recoloured, rendered by cairosvg; DST per candy
    from the shipped file. Returns {key: gate dict}, and tiles for the compare sheet."""
    import kjsvg
    from shapely.ops import unary_union
    out, tiles = {}, []
    for key, stem in KSTEM.items():
        rj = json.load(open(f"out/stitch/{stem}.json")); path = f"out/stitch/{stem}.dst"
        if key.startswith("front"):
            import kjfront
            F = json.load(open("out/front_stars.json")); byid = {d["id"]: d for d in F["stars"]}
            sec = [byid[i] for i in F["sections"][int(key[-1]) - 1]]
            pl = [dict(id=d["id"], col=kjfront.COLS[d["col"]][0], cx=d["x_from_side_mm"], cy=d["y_from_waist_mm"]) for d in sec]
        else:
            vis = A[key]["vis"]; pl = []
            for col in ("kj_yellow", "kj_pink", "kj_blue"):
                g = unary_union([r["geom"] for r in vis if r["col"] == col and r["grp"] == "STAR"])
                if g.is_empty: continue
                for P in kjsvg.polys(g.buffer(0.3)):
                    b = P.bounds; pl.append(dict(id=f"K{len(pl) + 1}", col=col, cx=(b[0] + b[2]) / 2, cy=(b[1] + b[3]) / 2))
            pl.sort(key=lambda p: p["cx"])
            for k_, p in enumerate(pl, 1): p["id"] = f"K{k_}"
        xs = [p["cx"] for p in pl]; ys = [p["cy"] for p in pl]
        x0, y0 = min(xs) - 8, min(ys) - 8; W, H = max(xs) - min(xs) + 16, max(ys) - min(ys) + 16
        svg = kjsvg.konpeito_ref_svg(pl, W, H, x0, y0)
        to_px = lambda x, y, x0=x0, y0=y0: ((x - x0) * PPM, (y - y0) * PPM)
        shape = (int(round(H * PPM)), int(round(W * PPM)))
        M = dst_masks_on(path, rj["origin_mm"], shape, to_px)
        cands = [(f"{KNO[key]} {p['id']} {p['col'][3:]}", kjsvg.svg_string_mask(svg, W, H, keep_id=p["id"]), p["col"]) for p in pl]
        rows = candy_gate(cands, M, rj)
        ref_img = kjsvg.svg_string_render(svg, W, H, PPM * 2, bg="#2A2A2E")
        prev = render_on(path, rj["origin_mm"], shape, to_px, bg=(42, 42, 46), sc=2)
        for p, r in zip(pl, rows):
            cx, cy = (p["cx"] - x0) * PPM * 2, (p["cy"] - y0) * PPM * 2; h = 7 * PPM * 2
            box_ = (int(cx - h), int(cy - h), int(cx + h), int(cy + h))
            tiles.append((r, ref_img.crop(box_), prev.crop(box_)))
        out[key] = dict(families=rows, konpeito=rows, uncovered=[], placements=pl)
    return out, tiles

def konpeito_sheet(tiles):
    """compare_konpeito.png: the 02 source candy, then every konpeito of 04-07: founder's 02 paths placed (left) vs DST (right)."""
    import kjsvg
    T = 300; pad = 24; per = 4; W = pad + per * (2 * T + 3 * pad)
    rowsN = math.ceil(len(tiles) / per)
    H = 230 + T + 120 + rowsN * (T + 80) + 60
    im = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(im)
    d.text((pad, 20), "Compare — every konpeito on 04 / 05 / 06 / 07a / 07b vs the 02 facing konpeito (founder change 20 Oct)", fill=(20, 20, 20), font=font(40))
    d.text((pad, 72), "LEFT of each pair: the founder's 02 candy paths (inputs/svg/HAKI_facing_konpeito_ART.svg) placed + recoloured at 10 mm, rendered by cairosvg.", fill=(90, 90, 90), font=font(26))
    d.text((pad, 106), "RIGHT: stitch preview drawn from the shipped DST, same scale (14 x 14 mm tiles). Same digitising as 02: one satin per lobe, tint lobes on top, 3 white bead specks.", fill=(90, 90, 90), font=font(26))
    src = Image.open("out/svg_spill.png") if __import__("os").path.exists("out/svg_spill.png") else None
    sp = Image.open("out/stitch/HAKI_KJ_02_coin-spill-facing_preview.png")
    y = 160
    d.text((pad, y), "Source: 02 on the facing (DST preview) — every konpeito below uses its front-row candy shape", fill=(20, 20, 20), font=font(28)); y += 40
    s_ = T / sp.height; im.paste(sp.resize((int(sp.width * s_), T)), (pad, y)); y += T + 60
    for k, (r, a, b) in enumerate(tiles):
        cx = pad + (k % per) * (2 * T + 3 * pad); cy = y + (k // per) * (T + 80)
        im.paste(a.resize((T, T)), (cx, cy + 34)); im.paste(b.resize((T, T)), (cx + T + 8, cy + 34))
        okc = (30, 140, 60) if r["ok"] else (180, 40, 30)
        d.text((cx, cy), f"{r['family']}  IoU {r['min_iou']}  outline p90 {r['outline_p90']} mm  {'PASS' if r['ok'] else 'FAIL'}", fill=okc, font=font(24))
    im.save("out/compare_konpeito.png")

def render_on(path, origin, shape, to_px, bg=(52, 52, 56), wmm=None, sc=1):
    p = pe.read(path); cols = [t.hex_color() for t in pe.read(path[:-4] + ".pes").threadlist]
    Hh, Ww = shape[0] * sc, shape[1] * sc
    im = Image.new("RGB", (Ww, Hh), bg); d = ImageDraw.Draw(im)
    w = max(2, int(round((wmm or 0.42) * PPM * sc)))
    _tp = to_px; to_px = (lambda x, y: tuple(v * sc for v in _tp(x, y))) if sc != 1 else to_px
    ci = 0; prev = None
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK; P = to_px(x / 10 + origin[0], y / 10 + origin[1])
        if k == pe.STITCH:
            if prev is not None:
                c = cols[min(ci, len(cols) - 1)]; rgb = tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
                ww = max(2, int(w * 0.72)) if c.upper() in ("#1C1A1A", "#34A5D6") else w
                d.line([prev, P], fill=c, width=ww); r_ = ww / 2
                for q in (prev, P): d.ellipse([q[0] - r_, q[1] - r_, q[0] + r_, q[1] + r_], fill=c)
                d.line([prev, P], fill=tuple(int(v * 0.80) for v in rgb), width=max(1, int(sc)))
            prev = P
        elif k == pe.COLOR_CHANGE: ci += 1; prev = None
        elif k == pe.TRIM: prev = None
        elif k == pe.JUMP: prev = P
        elif k == pe.END: break
    return im

if __name__ == "__main__":
    run()
