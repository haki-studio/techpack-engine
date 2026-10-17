"""Element spec sheets (5 pages each, A4 landscape) for the moon jacket elements 01–04 + production art SVGs.
Every count is read from the generated files (out/results/*.json: DST read-back), every clearance from emb_place.
usage: ./py.sh moonspec.py 01 02 03 04"""
import os, sys, json, pickle, math
import numpy as np
import cairosvg
from PIL import Image, ImageDraw
from shapely.geometry import box
from shapely.ops import unary_union
from shapely import affinity
from pypdf import PdfWriter, PdfReader
import moonpal
import sheet as SHT
from sheet import t, swatch, doc, INK, MUTED, RED, ORANGE, GUIDE, GREEN, SW, SH
from render import geom_to_path, f
from motifs2 import HEX, PAL
import tech, stitchrender as SR, qa
import specbase as SB
from specbase import img_tag, direction_map, header
import moonpattern, pattern as PT, emb_place as EP, scene, preview as PV
import readback, factory, sheet as _SH
import pyembroidery as pe
from shapely.strtree import STRtree

REV = "Rev B"; DATE = "16 Oct 2026"
PROP = "#8A5A00"
RES_M = json.load(open("out/results/size_M.json")); RES_B = json.load(open("out/results/grade_B.json"))
CLR = json.load(open("out/results/clearances.json"))
ART_M = pickle.load(open("art_M.pkl", "rb")); GRD = pickle.load(open("art_graded.pkl", "rb"))
VIS = {"back": ART_M["back"], "03L": ART_M["F03L"], "03R": ART_M["F03R"], **GRD}
PIECE_OF = {"back": "B01", "03L": "F01", "03R": "F02", "02R": "F02", "02L": "F01", "04R": "S01", "04L": "S02"}
G_M, MT_M = PT.draft("M")

def res_of(p): return RES_M[p] if p in RES_M else RES_B[p]

def measured_density(p):
    """thread length (mm) per mm² and stitches per mm² for every fill code, read from the DST: each sewn segment is given
    to the art region under its midpoint (travel under later fills counts where it lies — that is what the fabric gets)."""
    r = res_of(p); cx, cy = r["centre"]; pt = pe.read(r["file"] + ".dst")
    regs = [q for q in VIS[p] if q["st"] in ("tatami", "satin", "padded")]
    geoms = [q["geom"] for q in regs]; tree = STRtree(geoms); L = {}; N = {}; A = {}
    for q in regs: A[tech.rule_for(q["grp"])] = A.get(tech.rule_for(q["grp"]), 0) + q["geom"].area
    prev = None
    from shapely.geometry import Point as _P
    for x, y, c in pt.stitches:
        k = c & pe.COMMAND_MASK
        X, Y = x / 10 + cx, y / 10 + cy
        if k == pe.STITCH:
            if prev is not None:
                mx, my = (X + prev[0]) / 2, (Y + prev[1]) / 2
                hit = tree.query(_P(mx, my), predicate="within")
                if len(hit):
                    code = tech.rule_for(regs[int(hit[0])]["grp"]); d = math.hypot(X - prev[0], Y - prev[1])
                    L[code] = L.get(code, 0) + d; N[code] = N.get(code, 0) + 1
            prev = (X, Y)
        else: prev = None
    return {k: (L.get(k, 0) / A[k], N.get(k, 0) / A[k], A[k]) for k in A if A[k] > 0}

def width_check(vis):
    groups = {}
    for r in vis: groups.setdefault(tech.rule_for(r["grp"]), []).append(r)
    out = {}
    for code, rs in groups.items():
        line = rs[0]["st"] in ("bean", "run")
        u = unary_union([r["geom"] for r in rs]); parts = [u] if u.geom_type == "Polygon" else list(getattr(u, "geoms", []))
        A = L = 0.0
        for p in parts:
            if p.geom_type != "Polygon" or p.area < 0.05: continue
            res = qa.check_geom(p, 0.6 if line else 0.8, 0.35 if line else 0.5, 0.45 if line else 0.6)
            if res: A += res["area"]; L += res["long_area"]
        out[code] = 100 * L / max(A, 1e-9)
    return out

def piece_view(p, ppm=2.2, highlight=True):
    pc = PIECE_OF[p]; poly = G_M[pc].sew_poly()
    extra = None
    if p == "back":
        bx = ART_M["info"]["box"]
        def extra(d, T):
            x0, y0, x1, y1 = bx
            d.line(T([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]), fill=(255, 45, 155), width=3)
            d.line(T([(x0, y0), (x1, y1)]), fill=(255, 45, 155), width=1); d.line(T([(x1, y0), (x0, y1)]), fill=(255, 45, 155), width=1)
    return PV.piece_img(VIS[p], poly, ppm, extra), poly.bounds

CHANGES = {
 "01": ["Source: art redrawn from Devin's close-up (inputs/closeups/closeup_back.png,",
        "  1448 px; moon 550 px) on top of the low-res mockup: shapes + tones traced",
        "  from the close-up, placement + size from the mockup (mockup wins).",
        "Moon: 5 close-up tones (cream, highlight, pale gold, crater light, crater",
        "  grey-green) traced patch by patch, warm 2.5 mm rim, concentric rows in",
        "  15° sectors (thread texture follows the disc), craters each at their own",
        "  angle, star-burst rays + rim strokes as run lines (in the close-up).",
        "Clouds: each cloud from the close-up (scale rows = indigo lines, 5 tones,",
        "  white-pink tops, tapering wisps), placed + sized on the mockup cloud.",
        "Pole: every part traced from the close-up (wood grain lines, bands, crossarm,",
        "  2 pin insulators, ribbed transformer + small can, coiled string, bracket);",
        "  pole body extended to 10 above the hem (close-up ends above it).",
        "Licensed figure in the close-up NOT traced: box 68 × 79 (fig + 3 mm).",
        "Wires: satin cord 1.6, 12 wires, wraps at the insulators; side-seam wrap."],
 "02": ["Source: close-up closeup_front.png (clouds 3 per panel incl. the wisp by",
        "  the zip), each cloud placed + sized on its mockup cloud (mockup wins).",
        "Every lobe + scale row traced: 5 tones, indigo scallop lines, white-pink",
        "  tops, tapering tails. Clouds that cross a seam in the mockup are moved",
        "  the smallest distance that clears the 15 mm keep-outs."],
 "03": ["Source: close-up closeup_front.png (pole + hardware traced), mockup",
        "  placement: pole outside the welt, 15 off the side seam, 10 above hem.",
        "Hardware: pole grain, bands, crossarm, pin insulator, ribbed transformer,",
        "  small can, coiled string insulator (+7 mm to clear the welt), bracket.",
        "Wires: 12 (5 across the zip to the wearer's right side seam, 4 to the left",
        "  side seam, 3 drops), satin cord 1.6 with wraps. Where a wire passes a welt",
        "  pocket it stops 6 short of the welt box both sides (behind the pocket).",
        "Every wire meets its back (01) partner at the side seam (same height)."],
 "04": ["Source: close-up closeup_sleeves.png — 4 views (R back half, R front half,",
        "  L front half, L back half, read from the cap seams): cloud count +",
        "  position per view kept (fraction along the sleeve + across the view).",
        "Every lobe + scale row traced, same 5 tones as 01/02.",
        "15 clear of the cap + underarm seams, 10 above the cuff seam (moved",
        "  the smallest distance where a close-up cloud sat on a seam)."]}
PROD = ["Embroider the cut pieces flat, BEFORE any seam.",
        "40wt polyester (Madeira Polyneon), 75/11 sharp,",
        "  2.5 oz cutaway (black/navy on the dark duck).",
        "Wash test if the jacket is garment-washed",
        "  (cream + white grey first).",
        "Files are production-intent drafts: the factory",
        "  digitizer checks density + pull on 12 oz duck,",
        "  then sews out before bulk."]

CFG = {
 "01": dict(slug="back-scene", title="BACK SCENE — moon, clouds, pole + wires, licensed-figure placeholder", pieces=["back"],
            sub="Direct embroidery on the cut back panel · ONE FILE PER SIZE (+ 360² split files: 4, 3XL 6) · mm, finished size · art 1:1 · x from CB, y down from CB neck seam",
            crops=[(-75, 185, -25, 235, "Moon body, maria, craters (low density)"), (-215, 280, -165, 330, "Cloud crown: caps, scallops, shadow"),
                   (-20, 360, 30, 410, "Pole top, crossarm, insulator"), (10, 395, 60, 445, "Transformer can + wires")],
            dm=[(-90, 180, -20, 230, "Moon: horizontal tatami, maria at 30°"), (-230, 270, -150, 320, "Cloud: horizontal tatami, turning satin caps"), (-20, 360, 60, 410, "Pole: tatami along the pole, satin hardware")],
            mock=(150, 200, 560, 720), mock_src="inputs/back.png"),
 "02": dict(slug="chest-clouds", title="CHEST CLOUDS (02R wearer's right · 02L wearer's left)", pieces=["02R", "02L"],
            sub="Direct embroidery on the cut front panels, before zip + welts · graded A/B/C · mm, finished size · x from CF (+ = wearer's left), y from CF neck seam",
            crops=[(-215, 110, -165, 160, "Cloud crown (02R)"), (190, 150, 240, 200, "Cloud + streaks (02L)")],
            dm=[(-240, 100, -160, 160, "Horizontal tatami body, turning satin caps"), (150, 140, 230, 200, "Streak wisps: turning satin")],
            mock=(40, 240, 724, 410), mock_src="inputs/front.png"),
 "03": dict(slug="lower-front", title="LOWER FRONT — pole + wires (03L), wires (03R), split at the zip", pieces=["03R", "03L"],
            sub="Direct embroidery on the cut front panels · ONE FILE PER SIZE (wires meet the side seams) · mm, finished size · x from CF (+ = wearer's left)",
            crops=[(225, 330, 275, 380, "Crossarm, insulators, can"), (195, 425, 245, 475, "String insulator + small can")],
            dm=[(215, 320, 290, 380, "Pole: tatami along the pole"), (190, 420, 260, 480, "Insulators + can: satin / tatami")],
            mock=(330, 450, 724, 690), mock_src="inputs/front.png"),
 "04": dict(slug="sleeve-clouds", title="SLEEVE CLOUDS (04R right sleeve · 04L left sleeve)", pieces=["04R", "04L"],
            sub="Direct embroidery on the cut sleeves (one-piece sleeve, front half + back half) · graded A/B/C · mm · sleeve pattern coords (y down from the bicep line)",
            crops=[(60, 120, 110, 170, "Sleeve cloud crown (04R front)"), (-150, 230, -100, 280, "Sleeve cloud (04R back)")],
            dm=[(30, 110, 130, 175, "Horizontal tatami, satin caps"), (-160, 220, -60, 290, "Back-half cloud")],
            mock=(0, 280, 160, 620), mock_src="inputs/front.png"),
}

def placement_rows(n):
    c = CLR["M"]; rows = []
    if n == "01":
        b = unary_union([r["geom"] for r in VIS["back"]]).bounds; d = c["01"]; bx = ART_M["info"]["box"]
        rows = [("Art box (back panel)", f"{b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}"), ("  x / y range", f"{b[0]:+.0f}…{b[2]:+.0f} / {b[1]:.0f}…{b[3]:.0f}"),
                ("  art → side seams (min)", f"{min(d['side_L'], d['side_R']):.1f} (≥ 15)"), ("  WIRES → side seams", f"{d['wire_side_L']:.1f} / {d['wire_side_R']:.1f} (3, wrap)"),
                ("  → armholes (min)", f"{min(d['armhole_L'], d['armhole_R']):.1f} (≥ 15)"), ("  → hem seam", f"{d['hem']:.1f} (≥ 10)"),
                ("Moon", f"Ø {2*ART_M['info']['moon']['r']:.0f}, centre (0, {ART_M['info']['moon']['c'][1]:.0f})"),
                ("PLACEHOLDER BOX (licensed)", f"{bx[2]-bx[0]:.0f} × {bx[3]-bx[1]:.0f}, x {bx[0]:+.1f}…{bx[2]:+.1f}, y {bx[1]:.0f}…{bx[3]:.0f}")]
    elif n == "02":
        for p in ("02R", "02L"):
            b = unary_union([r["geom"] for r in VIS[p]]).bounds; d = c[p]
            rows += [(f"Art box {p}", f"{b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}  (x {b[0]:+.0f}…{b[2]:+.0f}, y {b[1]:.0f}…{b[3]:.0f})"),
                     ("  → CF / armhole / side", f"{d['CF']:.0f} / {d['armhole']:.0f} / {d['side']:.0f}"), ("  → collar / welt", f"{d['collar']:.0f} / {d['welt']:.0f}")]
    elif n == "03":
        for p in ("03R", "03L"):
            b = unary_union([r["geom"] for r in VIS[p]]).bounds; d = c[p]
            rows += [(f"Art box {p}", f"{b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}  (x {b[0]:+.0f}…{b[2]:+.0f}, y {b[1]:.0f}…{b[3]:.0f})"),
                     ("  → CF / hem", f"{d['CF']:.1f} / {d['hem']:.1f}"), ("  wires → side seam / welt", f"{d['wire_side']:.1f} / {d['wire_welt']:.1f}")]
            if "side" in d: rows.append(("  pole + cloud → side / welt", f"{d['side']:.1f} / {d['welt']:.1f}"))
    else:
        for p in ("04R", "04L"):
            b = unary_union([r["geom"] for r in VIS[p]]).bounds; d = c[p]
            rows += [(f"Art box {p}", f"{b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}  (x {b[0]:+.0f}…{b[2]:+.0f}, y {b[1]:.0f}…{b[3]:.0f})"),
                     ("  → cap / underarm / cuff", f"{d['cap']:.0f} / {d['underarm']:.0f} / {d['cuff']:.0f}")]
    return rows


def page6_01(NP):
    o = header("01 · HOOP SPLITS PER SIZE + MOON-IN-BOX FILE", f"Frame from factory.json: {' / '.join(f'{w:.0f} × {h:.0f}' for w, h in factory.load()['frames_mm'])} mm [proposed — confirm]. Layout: moon + box whole in the top-middle hooping, pole + hardware whole in the bottom-middle one (every size).", f"p6 / {NP}")
    import drum
    hd = ["Size", "Grid", "Split x (mm, from CB)", "Split y", "Sections: stitches · size · fit", "Placeholder basted in", "Moon-in-box st / trims"]
    cx = [12, 22, 32, 64, 80, 214, 254]
    for x_, h in zip(cx, hd): o.append(t(x_, 31, h, 1.55, 700, MUTED))
    y = 35.5
    for i, sz in enumerate(drum.SIZES):
        R_ = json.load(open(f"out/results/size_{sz}.json")); sp = R_["splits"]
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.6)}" width="{SW-22}" height="3.7" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, sz, 1.5, 700)); o.append(t(cx[1], y, f"{sp['grid'][0]}×{sp['grid'][1]}", 1.45))
        o.append(t(cx[2], y, ", ".join(f"{v:+.0f}" for v in sp["xs"]), 1.45)); o.append(t(cx[3], y, ", ".join(f"{v:.0f}" for v in sp["ys"]), 1.45))
        o.append(t(cx[4], y, " · ".join(f"{k[:2]} {v['stitches']/1000:.0f}k {v['size'][0]:.0f}×{v['size'][1]:.0f}{'' if v['fits'] else ' !'}" for k, v in sp["sections"].items()), 1.3))
        o.append(t(cx[5], y, sp["box_section"][:28], 1.4)); mb = R_.get("moonbox")
        o.append(t(cx[6], y, f"{mb['stitches']:,} / {mb['trims_dst']}" if mb else "—", 1.45)); y += 3.7
    y += 2
    M_ = json.load(open("out/results/size_M.json"))["splits"]
    o.append(t(12, y, "Registration crosses, size M (mm, garment coords; every size in the result files + thread charts):", 1.55, 700)); y += 3.3
    cr = sorted({(round(m[0]), round(m[1])) for v in M_["sections"].values() for m in v["marks"]})
    for j in range(0, len(cr), 12):
        o.append(t(12, y, "  ".join(f"({a:+d}, {b})" for a, b in cr[j:j + 12]), 1.4)); y += 3.0
    # diagrams for every size
    yy = y + 3; xx = 12
    for sz in drum.SIZES:
        R_ = json.load(open(f"out/results/size_{sz}.json")); sp = R_["splits"]; g, mt = PT.draft(sz)
        poly = g["B01"].sew_poly(); b = poly.bounds; s_ = 36 / (b[2] - b[0])
        X = lambda x, b=b, xx=xx, s_=s_: xx + (x - b[0]) * s_; Y = lambda yv, b=b, yy=yy, s_=s_: yy + (yv - b[1]) * s_
        o.append(f'<path d="{"M" + " L".join(f"{f(X(px))} {f(Y(py))}" for px, py in poly.exterior.coords)} Z" fill="#E9ECF3" stroke="#888" stroke-width="0.15"/>')
        for nm, v in sp["sections"].items():
            bb = v["bbox"]
            o.append(f'<rect x="{f(X(bb[0]))}" y="{f(Y(bb[1]))}" width="{f((bb[2]-bb[0])*s_)}" height="{f((bb[3]-bb[1])*s_)}" fill="none" stroke="#0A84FF" stroke-width="0.18"/>')
            o.append(t(X((bb[0]+bb[2])/2), Y((bb[1]+bb[3])/2) + 0.5, nm[:2], 1.3, 700, "#0A84FF", "middle"))
            for m in v["marks"]:
                o.append(f'<path d="M{f(X(m[0])-0.7)} {f(Y(m[1]))} H{f(X(m[0])+0.7)} M{f(X(m[0]))} {f(Y(m[1])-0.7)} V{f(Y(m[1])+0.7)}" stroke="#00A3FF" stroke-width="0.2"/>')
        bx = R_["info"]["box"]
        o.append(f'<rect x="{f(X(bx[0]))}" y="{f(Y(bx[1]))}" width="{f((bx[2]-bx[0])*s_)}" height="{f((bx[3]-bx[1])*s_)}" fill="none" stroke="#FF2D9B" stroke-width="0.3"/>')
        o.append(t(xx, yy - 1.2, sz, 1.6, 700)); xx += 40
    o.append(t(12, yy + 45, "Blue = each split file's extent (art + crosses); + = basting crosses; pink = licensed-figure box. Hooping order S1 → Sn (top row left → right, then bottom row).", 1.5, 400, MUTED))
    o.append(t(12, yy + 49, "01b MOON-IN-BOX (per size): our moon fill inside the box (same tones, concentric rows), origin = box centre; sew it before the licensed figure.", 1.55, 700, PROP))
    o.append(t(12, yy + 52.5, "Ownership [proposed — confirm]: Haki supplies the moon-in-box file; the factory digitizer adds the figure on top of it from the licensor-approved art.", 1.55, 600, PROP))
    return o

def page6_03(NP):
    import drum
    o = header("03 · WIRE MARKS PER SIZE — side seams + zip", "Heights in mm above the hem seam (side seams) / y below the CF neck seam (zip ends at x = ±15). Read from each size's art + stitch file. Notches carry these labels on the DXF (layer 4).", f"p6 / {NP}")
    hd = ["Size", "Wearer's LEFT side seam (back ↔ 03L)", "Wearer's RIGHT side seam (back ↔ 03R)", "Zip ends 03L (y)", "Zip ends 03R (y)"]
    cx = [12, 24, 84, 150, 220]
    for x_, h in zip(cx, hd): o.append(t(x_, 31, h, 1.6, 700, MUTED))
    y = 36
    for i, sz in enumerate(drum.SIZES):
        mk = pickle.load(open(f"art_{sz}.pkl", "rb"))["info"]["marks"]
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.7)}" width="{SW-22}" height="3.9" fill="#F5F2EC"/>')
        L_ = ", ".join(f"W{h:.0f}" for s_, h, d in mk["back"] if s_ == "L"); R_ = ", ".join(f"W{h:.0f}" for s_, h, d in mk["back"] if s_ == "R")
        zl = ", ".join(f"{yv:.0f}" for gname, yv in mk["zip_L"] if gname == "WR"); zr = ", ".join(f"{yv:.0f}" for gname, yv in mk["zip_R"] if gname == "WR")
        o.append(t(cx[0], y, sz, 1.6, 700)); o.append(t(cx[1], y, L_, 1.5)); o.append(t(cx[2], y, R_, 1.5)); o.append(t(cx[3], y, zl, 1.5)); o.append(t(cx[4], y, zr, 1.5)); y += 3.9
    y += 4
    ang = pickle.load(open("art_M.pkl", "rb"))["info"]["marks"]["angles"]
    o.append(t(12, y, "WIRE ANGLE AT THE SIDE SEAM, size M (degrees below horizontal, + = falling toward the seam; back / front)", 2.0, 700)); y += 4.5
    for j in range(0, len(ang), 3):
        o.append(t(12, y, "    ".join(f"{s_} W{h:.0f}: back {a:+.0f}° / front {b:+.0f}°" for s_, h, a, b in ang[j:j + 3]), 1.6)); y += 3.4
    y += 3
    for l in ["Rule: the HEIGHT must match across the seam (± 2 mm, notch to notch). The angle need not match: each wire is its own sagging",
              "span (pole → seam on one panel, seam → pole on the other), as a real line bends at the body's side — the mockup reads the same.",
              "Where a wire passes a welt pocket it stops 6 mm short of the welt box on both sides (reads as passing behind the pocket).",
              "Hooping order: 03L and 03R are one hooping each; sew 02 (chest clouds) first, then 03, on the same cut front panel."]:
        o.append(t(12, y, l, 1.7)); y += 3.6
    return o

def build(n):
    cfg = CFG[n]; pieces = cfg["pieces"]; NP = 6 if n in ("01", "03") else 5
    SB.FOOT = f"HAKI STUDIOS · Drum Island jacket · moon · {n} {cfg['slug']} · {REV} · {DATE}"
    OUT = f"out/{n}_{cfg['slug']}"; os.makedirs(OUT, exist_ok=True)
    V = {p: VIS[p] for p in pieces}; ALL = [r for p in pieces for r in V[p]]
    STOPS = {p: tech.stops(V[p]) for p in pieces}
    BB = {p: unary_union([r["geom"] for r in V[p]]).bounds for p in pieces}
    WC = width_check(ALL)
    pages = []
    # ---------------- p1
    o = header(f"{n} · {cfg['title']}", cfg["sub"], f"p1 / {NP}")
    x = 12; ymax = 0
    imgs = [piece_view(p, 2.0) for p in pieces]
    widths = [(b[2] - b[0] + 24) for _, b in imgs]; s = min(150 / sum(widths), 150 / max(b[3] - b[1] + 24 for _, b in imgs))
    for (im, b), p in zip(imgs, pieces):
        w_mm = (b[2] - b[0] + 24) * s; tag, h = img_tag(im, x, 29, w_mm); o.append(tag)
        o.append(t(x, 29 + h + 3.2, f"{p} on {PIECE_OF[p]} (size M, shown {s:.2f}:1)", 1.75, 700)); x += w_mm + 3; ymax = max(ymax, h)
    rx = 172; o.append(t(rx, 33, "PLACEMENT (size M; every size: T13 + G2)", 2.2, 700)); yy = 38
    for a_, b_ in placement_rows(n):
        o.append(t(rx, yy, a_, 1.8, 400, MUTED)); o.append(t(rx + 44, yy, b_, 1.8, 600)); yy += 3.5
    yy += 2.5; o.append(t(rx, yy, "BY THE NUMBERS (read back from the DST files)", 2.2, 700)); yy += 4.4
    for p in pieces:
        r = res_of(p)
        o.append(t(rx, yy, f"{p} ({'size M' if p in RES_M else 'grade B'})", 1.8, 400, MUTED))
        o.append(t(rx + 44, yy, f"{r['stitches']:,} st · {r['trims_dst']} trims · {r['stops']} stops · {r['threads']} threads · {r['stitches']/750:.0f} min", 1.8, 600)); yy += 3.5
        if "sections" in r:
            o.append(t(rx + 44, yy, "hoopings: " + " · ".join(f"{k[:2]} {v['stitches']/1000:.0f}k ({v['size'][0]:.0f}×{v['size'][1]:.0f})" for k, v in r["sections"].items()) + ("  fit 360²" if all(v["fits"] for v in r["sections"].values()) else "  CHECK"), 1.7, 400, MUTED)); yy += 3.5
    if n == "01":
        sp = RES_M["splits"]
        o.append(t(rx, yy, "360² splits (size M)", 1.8, 400, MUTED))
        o.append(t(rx + 44, yy, " · ".join(f"{k[:2]} {v['stitches']/1000:.0f}k" for k, v in sp["sections"].items()) + ("  all fit" if all(v["fits"] for v in sp["sections"].values()) else "  CHECK"), 1.8, 600)); yy += 5
        o.append(t(rx, yy, "LICENSED FIGURE — PLACEHOLDER ONLY", 2.2, 700, RED)); yy += 4
        for l in ["Licence confirmed by client 2026-10-16. Nothing is drawn inside the box;",
                  "our fills are knocked out there. Last stop of the file = basting outline",
                  "of the box (pink, water-soluble): the factory digitizer replaces it with",
                  "the licensor-approved figure insert, matching the moon fill around it.",
                  f"Box placed in split section {sp['box_section']} for the 4-hooping route."]:
            o.append(t(rx, yy, l, 1.7)); yy += 3.2
    if n in ("01", "03"):
        yy += 2; o.append(t(rx, yy, "SIDE-SEAM WIRE MARKS (height above the hem seam, M)", 2.0, 700)); yy += 3.8
        m = ART_M["info"]["marks"]
        for side, nm in (("L", "wearer's left"), ("R", "wearer's right")):
            hs = [f"{h:.0f}" for s_, h, d in m["back"] if s_ == side]
            o.append(t(rx, yy, f"{nm} side seam: {', '.join(hs)}  (ends 3.0 from the seam, both pieces)", 1.7)); yy += 3.2
        if n == "03":
            zl = [f"{y_:.0f}" for g_, y_ in m["zip_L"]]; o.append(t(rx, yy, f"zip (x = ±15): wire/wisp ends at y {', '.join(zl)}", 1.7)); yy += 3.2
    pages.append(o)
    # ---------------- p2 direction map
    o = header(f"{n} · STITCH-DIRECTION MAP + REGION CODES", "Hatch = stitch direction of every fill/satin region. Dark solid = line work (bean / run). Labels = region code → stitch table p3.", f"p2 / {NP}")
    xcur = 12; widths = [BB[p][2] - BB[p][0] + 6 for p in pieces]
    scale = min(165 / max(BB[p][3] - BB[p][1] + 6 for p in pieces), (172 - 6 * (len(pieces) - 1)) / sum(widths))
    for p in pieces:
        b = BB[p]; bb = (b[0] - 3, b[1] - 3, b[2] + 3, b[3] + 3)
        dm = direction_map(V[p], bb, 3.2 if n == "01" else 4.5, label_min=120 if n == "01" else 40, label_mm=3.0)
        wmm = (bb[2] - bb[0]) * scale; tag, hh = img_tag(dm, xcur, 30, wmm, 88); o.append(tag)
        o.append(f'<rect x="{f(xcur)}" y="30" width="{f(wmm)}" height="{f(hh)}" fill="none" stroke="#BBB" stroke-width="0.2"/>')
        o.append(t(xcur, 30 + hh + 3.2, f"{p} (shown {scale:.2f}:1)", 1.9, 700)); xcur += wmm + 6
    zx = 192; o.append(t(zx, 32, "DETAIL CROPS", 2.4, 700)); yy = 35
    for (x0, y0, x1, y1, cap) in cfg["dm"]:
        im = direction_map(ALL, (x0, y0, x1, y1), 12, label_min=20, label_mm=1.4)
        wmm = 64; tag, hh = img_tag(im, zx, yy, wmm, 90); o.append(tag)
        o.append(f'<rect x="{zx}" y="{f(yy)}" width="{f(wmm)}" height="{f(hh)}" fill="none" stroke="#BBB" stroke-width="0.2"/>')
        o.append(t(zx, yy + hh + 3, cap, 1.75, 400, MUTED)); yy += hh + 6.5
    pages.append(o)
    # ---------------- p3 region table
    o = header(f"{n} · REGION STITCH TABLE — digitizing parameters per region code",
               "Rows = row spacing (mm). Pull comp = added width per side (mm). Width = share of the code's area below its minimum (fill/satin 0.8, line 0.6).", f"p3 / {NP}")
    stats = {}
    for r in ALL:
        k = tech.rule_for(r["grp"]); st_ = stats.setdefault(k, dict(n=0, cols=set(), st=0.0)); st_["n"] += 1; st_["cols"].add(r["col"]); st_["st"] += tech.stitches(r)
    MD = {}
    for p in pieces:
        for k_, (mm, sn, a_) in measured_density(p).items():
            o_ = MD.get(k_, (0, 0, 0)); MD[k_] = (o_[0] + mm * a_, o_[1] + sn * a_, o_[2] + a_)
    MD = {k_: (v[0] / v[2], v[1] / v[2]) for k_, v in MD.items() if v[2] > 0}
    hdr = ["Code", "Region", "Thread(s)", "Stitch", "Angle", "Rows", "Len.", "Underlay", "Pull", "Notes", "Width", "DST mm/mm² · st/mm²", "Obj."]
    cx = [12, 30, 63, 86, 117, 150, 159, 168, 206, 214, 238, 250, 279]
    for x_, hd in zip(cx, hdr): o.append(t(x_, 31, hd, 1.65, 700, MUTED))
    order = [k for k in tech.RULES if k in stats]; rh = min(4.2, 140 / max(1, len(order)))
    for i, k in enumerate(order):
        y = 34.6 + i * rh
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.9)}" width="{SW-22}" height="{f(rh)}" fill="#F5F2EC"/>')
        name, st, ang, dens, ln, ul, pull, note = tech.RULES[k]; s_ = stats[k]
        o.append(t(cx[0], y, k, 1.6, 700)); o.append(t(cx[1], y, name[:24], 1.5))
        xs = cx[2]
        for c in sorted(s_["cols"], key=lambda c: tech.COLOUR_ORDER.index(c))[:4]: o.append(swatch(xs, y, c, 3.0, 2.1)); xs += 4.0
        for j, v in enumerate((st, ang, dens, ln, ul, pull, note)):
            lim = {0: 20, 1: 24, 4: 28, 6: 18}.get(j, 30)
            o.append(t(cx[3 + j], y, v if len(v) <= lim else v[:lim].rsplit(' ', 1)[0] + '…', 1.45))
        q = WC.get(k, 0.0); qc = GREEN if q < 1.0 else (ORANGE if q < 3.5 else RED)
        o.append(t(cx[10], y, f"{q:.1f}%", 1.5, 600, qc))
        if k in MD: o.append(t(cx[11], y, f"{MD[k][0]:.1f} · {MD[k][1]:.2f}", 1.5, 600))
        o.append(t(cx[12], y, f"{s_['n']}", 1.5, 400, MUTED))
    yb = 34.6 + len(order) * rh + 3
    tot = sum(res_of(p)["stitches"] for p in pieces)
    o.append(t(12, yb, f"Stitches in the production files ({', '.join(pieces)}, M / grade B): {tot:,} (DST read-back). 40wt polyester, 75/11 sharp, 2.5 oz cutaway, no topping.", 1.7, 600))
    o.append(t(12, yb + 3.4, "DST mm/mm² = thread length the file actually sews per mm² of each code (underlay + top rows + blends + hidden travel that lies under it), read back", 1.6, 400, MUTED))
    o.append(t(12, yb + 6.6, "from the DST. One 0.45 tatami layer alone is ≈ 2.2 mm/mm². Rev B is fidelity-first (client direction): density is reported, not limited — clean up after the sew-out.", 1.6, 600, PROP))
    if any(v >= 1.0 for v in WC.values()):
        o.append(t(12, yb + 9.8, "Amber width = short tapered ends (wisp tips, cap tips, crater slivers) under 0.8 for < 2.5 mm; the digitizer drops or widens them.", 1.6, 400, ORANGE))
    pages.append(o)
    # ---------------- p4 colour stops
    o = header(f"{n} · COLOUR STOP SEQUENCE + THREADS", "Sewing order back to front: moon → craters → wires → clouds → pole → hardware. Fills before the lines on them. Same-colour stops merged where nothing sewn in between is within 1 mm.", f"p4 / {NP}")
    colx = [12, 150] if len(pieces) == 2 else [12]
    H2K = {v[0].upper(): k_ for k_, v in PAL.items()}
    for ci, p in enumerate(pieces):
        x0 = colx[ci]; mst = __import__("moonstitch").stops_for(V[p])[0]
        rb = readback.dst(res_of(p)["file"] + ".dst"); thr = pe.read(res_of(p)["file"] + ".pes").threadlist
        o.append(t(x0, 30.5, f"PIECE {p} — {rb['stops']} stops in the file · {rb['stitches']:,} st · {rb['trims']} trims (readback.dst)", 2.0, 700))
        hc = [x0, x0 + 8, x0 + 36, x0 + 50, x0 + 64, x0 + 98, x0 + 116]
        for x_, hd in zip(hc, ["Stop", "Thread", "Isacord", "Polyneon", "Sews (region codes)", "Stitches", "Trims"]): o.append(t(x_, 34.5, hd, 1.55, 700, MUTED))
        rh = min(3.4, 150 / max(1, rb["stops"] + 1))
        for i, ps in enumerate(rb["per_stop"]):
            y = 38 + i * rh; hx = thr[min(i, len(thr) - 1)].hex_color().upper(); k = H2K.get(hx)
            if i % 2 == 0: o.append(f'<rect x="{x0-1}" y="{f(y-2.4)}" width="134" height="{f(rh)}" fill="#F5F2EC"/>')
            o.append(t(hc[0], y, f"{i+1:02d}", 1.55, 700))
            if k:
                iso, pn = SB.TH[k]["isacord"], SB.TH[k]["polyneon"]
                o.append(swatch(hc[1], y, k, 3.2, 2.2)); o.append(t(hc[1] + 4.2, y, PAL[k][1][:16], 1.45))
                o.append(t(hc[2], y, f"{iso[0]}", 1.45)); o.append(t(hc[3], y, f"{pn[0]}", 1.45))
                mi = next((m for m in mst if m["col"] == k), None)
                if mi: o.append(t(hc[4], y, ", ".join(sorted({tech.rule_for(r['grp']) for r in mi['regions']}))[:26], 1.35, 400, MUTED))
            else:
                o.append(f'<rect x="{hc[1]}" y="{f(y-2.0)}" width="3.2" height="2.2" fill="{hx}"/>')
                o.append(t(hc[1] + 4.2, y, "PLACEHOLDER basting outline — licensed insert" if p == "back" and i == rb["stops"] - 1 else "basting (registration)", 1.45, 600, RED))
            o.append(t(hc[5], y, f"{ps['stitches']:,}", 1.45)); o.append(t(hc[6], y, f"{ps['trims']}", 1.45))
    if len(pieces) == 1:
        sx = 160; used = sorted({r["col"] for r in ALL}, key=lambda c: tech.COLOUR_ORDER.index(c))
        o.append(t(sx, 30.5, "THREADS USED (ΔE2000 to target)", 2.2, 700))
        for i, k in enumerate(used):
            y = 36 + i * 3.6; iso, pn = SB.TH[k]["isacord"], SB.TH[k]["polyneon"]
            o.append(swatch(sx, y, k, 3.2, 2.2)); o.append(t(sx + 5, y, f"{PAL[k][1]} {HEX[k]}", 1.6))
            ci_ = GREEN if iso[3] < 3 else (ORANGE if iso[3] < 5.5 else RED); cp = GREEN if pn[3] < 3 else (ORANGE if pn[3] < 5.5 else RED)
            o.append(t(sx + 44, y, f"Isacord {iso[0]}  ΔE {iso[3]:.1f}", 1.55, 600, ci_)); o.append(t(sx + 80, y, f"Polyneon {pn[0]}  ΔE {pn[3]:.1f}", 1.55, 600, cp))
    pages.append(o)
    # ---------------- p5 1:1 details + mockup + changes
    o = header(f"{n} · 1:1 DETAILS, WHAT CHANGED, PRODUCTION NOTES", "Print at 100 % to check scale. Art redrawn from the close-ups (low-res AI renders): shapes read off a x2 upscale, not traced at stitch resolution.", f"p5 / {NP}")
    o.append(t(14, 31, "1:1 STITCH-OUT DETAILS", 2.6, 700)); x = 14
    for (x0, y0, x1, y1, cap) in cfg["crops"]:
        im = SR.render(ALL, (x0, y0, x1, y1), 12, base=moonpal.FABRIC); tag, hh = img_tag(im, x, 35, x1 - x0); o.append(tag)
        o.append(t(x, 35 + hh + 3, cap, 1.7, 600)); x += (x1 - x0) + 4
    my = 98
    tag, hh = SHT.embed(cfg["mock_src"], cfg["mock"], 56 if n != "02" else 58, 14, my + 3); o.append(tag)
    o.append(t(14, my, "MOCKUP", 2.4, 700))
    o.append(t(76, my, "WHAT CHANGED vs MOCKUP (and why)", 2.4, 700))
    for i, c in enumerate(CHANGES[n]): o.append(t(76, my + 4.5 + i * 3.3, c, 1.8))
    o.append(t(196, my, "PRODUCTION", 2.4, 700))
    _ab = unary_union([r["geom"] for r in VIS["back"]]).bounds
    pr = PROD + ([f"Back: border frame ≥ {_ab[2]-_ab[0]+14:.0f} × {_ab[3]-_ab[1]+14:.0f} (M) single file, or", "  the 360² split files (4; 3XL 6) with basting crosses (G5)."] if n == "01" else [])
    pr += (["Sleeves: two hoopings per sleeve (split files S1 +", "  S2, front + back half) with basting crosses."] if n == "04" else [])
    pr += ["Wires: satin cord 1.6; side-seam ends 3 mm short —", "  match the W notches when closing (no topstitch)."] if n in ("01", "03") else []
    pr += {"01": ["Hooping order: S1 → S6 (top row L→R, bottom row);", "  01b moon-in-box in the S2 hooping, then the figure."],
           "02": ["Hooping order: 02 first on each cut front panel,", "  then 03 (pole + wires) on the same panel."],
           "03": ["Hooping order: after 02 on the same front panel."],
           "04": ["Hooping order per sleeve: S1 (back half) then S2."]}[n]
    for i, c in enumerate(pr): o.append(t(196, my + 4.5 + i * 3.3, c, 1.8))
    o.append(t(14, SH - 12, "[proposed — confirm] threads + densities: approve a thread board and a sew-out on the production duck before bulk.", 1.8, 600, PROP))
    pages.append(o)
    if n == "01": pages.append(page6_01(NP))
    if n == "03": pages.append(page6_03(NP))
    w = PdfWriter()
    for i, pg in enumerate(pages, 1):
        svg = doc(pg)
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"out/_e{n}_{i}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"out/prev_{n}_p{i}.png", output_width=2400)
        w.append(PdfReader(f"out/_e{n}_{i}.pdf"))
    spec = f"{OUT}/HAKI_moon_{n}_{cfg['slug']}_SPEC_{REV.replace(' ', '')}.pdf"; w.write(spec)
    # production art SVGs (size M / grade B, region attributes), + guides, + stitch preview
    for p in pieces:
        b = BB[p]; ox, oy = b[0] - 5, b[1] - 5; Wd, Hd = b[2] - b[0] + 10, b[3] - b[1] + 10
        pc = PIECE_OF[p]; panel = affinity.translate(G_M[pc].sew_poly(), -ox, -oy)
        gd = f'<path d="{geom_to_path(panel)}" fill="none" stroke="#00A3FF" stroke-width="0.4" stroke-dasharray="3 2"/>'
        if p == "back":
            bx = ART_M["info"]["box"]
            gd += (f'<rect x="{f(bx[0]-ox)}" y="{f(bx[1]-oy)}" width="{f(bx[2]-bx[0])}" height="{f(bx[3]-bx[1])}" fill="none" stroke="#FF2D9B" stroke-width="0.5"/>'
                   f'<text x="{f(bx[0]-ox+2)}" y="{f(bx[1]-oy+6)}" font-size="4" fill="#FF2D9B">LICENSED FIGURE — placeholder (factory insert)</text>')
        mst = __import__("moonstitch").stops_for(V[p])[0]
        open(f"{OUT}/HAKI_moon_{n}_{p}_ART.svg", "w").write(SB.production_svg(V[p], mst, Wd, Hd, ox, oy))
        open(f"{OUT}/HAKI_moon_{n}_{p}_ART+guides.svg", "w").write(SB.production_svg(V[p], mst, Wd, Hd, ox, oy, gd))
        SR.render(V[p], (b[0] - 6, b[1] - 6, b[2] + 6, b[3] + 6), 4 if p == "back" else 6, base=moonpal.FABRIC).save(f"{OUT}/HAKI_moon_{n}_{p}_STITCH-PREVIEW.png")
    json.dump(dict(width=WC, bbox=BB, stops={p: len(STOPS[p]) for p in pieces}), open(f"{OUT}/summary.json", "w"), default=float)
    print(n, "pages", len(pages), spec, {k: round(v, 1) for k, v in WC.items() if v >= 1.0}, flush=True)
    return spec

if __name__ == "__main__":
    for n in sys.argv[1:]: build(n)
