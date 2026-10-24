"""Garment pages T1-T9 for the Keep Clean Our Space hooded jacket on block `zip-hoodie` (engine/hoodie.py; founder decision
19 Oct 2026), copied from projects/comet-city-hoodie/gtp.py and adapted. Every measurement is read from the pattern; every
embroidery number from the stitch files / emb_place; every stitch picture is the written DST read back (dstview).
build(emb_pdf, emb_index, out_pdf) merges T + G pages."""
import kccore
import os, math, json, io
import numpy as np
import cairosvg
from PIL import Image, ImageFilter
from pypdf import PdfWriter, PdfReader
from shapely import affinity
import sheet as SHT
from sheet import t, doc, INK, MUTED, RED, GREEN, SW, SH, dim_h, dim_v
from render import f
import drum, pattern as PT, pattern_draw as PD
import front as F_                    # front.WELT = this design's welt (engine per-design override)
import hoodie as HD, hflat as HF
import emb_place as EP, factory as FA, dstview as DV
import pattern_kc as PC
import kcdoc as KD

STYLE = kccore.STYLE; REV = kccore.REV_GAR; DATE = kccore.DATE; NAME = kccore.NAME
FOOT = f"HAKI STUDIOS · {NAME} · {STYLE} · GARMENT · {REV} · {DATE}"
PROP = "#8A5A00"; ALT = "#F5F2EC"
SIZES = HD.SIZES
HF.SHELL = "#2B2F38"; HF.SHELL_D = "#22252D"; HF.SHERPA = "#F2ECDF"          # washed black duck, cream sherpa
def prop(x, y, s, size=1.85): return t(x, y, s + "  [proposed — confirm]", size, 600, PROP)
def H(title, sub, page): SHT.FOOT = FOOT; return SHT.header(title, sub, page)
def flat_g(body, b, ox, oy, s): return f'<g transform="translate({f(ox - b[0]*s)} {f(oy - b[1]*s)}) scale({f(s)})">{body}</g>'
def qty_of(pc):
    q = pc.qty.split(); return int(q[0]) * (2 if q[1:2] == ["pair"] else 1)

G = {sz: HD.draft(sz, welt=F_.WELT) for sz in SIZES}
MEAS = {sz: HD.measure(sz) for sz in SIZES}
CH = HD.chart()
CHECK = {sz: all(abs(MEAS[sz][0][k] / 10 - CH[k][2][SIZES.index(sz)]) <= CH[k][3] for k in CH) for sz in SIZES}
WALKS_OK = {sz: all(tol is None or abs(a - b) <= tol for _, a, b, tol in MEAS[sz][1]) for sz in SIZES}
SHAPE_OK = {sz: all(c[1] for c in HD.shape_checks(sz)) for sz in SIZES}
gM, mM = G["M"]
CUR = json.load(open("dst_current.json"))
import pickle
ART = pickle.load(open("art_M.pkl", "rb"))

def area_m2(codes, g): return sum(PT.cut_poly(g[c]).area * qty_of(g[c]) for c in codes) / 1e6

# ---------------------------------------------------------------- flats with the stitch render in place
def _sleeve_affine(Fl, P):
    """S01/S02 pattern coords -> flat sleeve (front view). Centre line -> outer sleeve edge, underarm front -> inner edge."""
    g, _ = F_.pieces("M"); pc = g["S01"].sew_poly(); b = pc.bounds; ycap, ycuff = b[1], b[3]
    s = 1 if P == "SL" else -1                         # flat +x = wearer's left
    sp = np.array([s*Fl.sp[0], Fl.sp[1]]); co = np.array([s*Fl.cs_out[0], Fl.cs_out[1]]); ci = np.array([s*Fl.cs_in[0], Fl.cs_in[1]])
    Wc = float(np.interp(ycuff - 1, *zip(*[(y, pc.intersection(__import__("shapely").geometry.LineString([(0, y), (400, y)])).bounds[2]) for y in np.linspace(0, ycuff - 1, 20)])))
    xs = -1 if P == "SL" else 1                        # front half: SL x < 0, SR x > 0
    src = np.array([[0, ycap], [0, ycuff], [xs*Wc, ycuff]], float); dst = np.array([sp, co, ci])
    A = np.linalg.solve(np.c_[src, np.ones(3)], dst)   # 3x2
    return [A[0, 0], A[1, 0], A[0, 1], A[1, 1], A[2, 0], A[2, 1]]

def flat_png(back=False, ppm=3.0, art=True):
    Fl = HF.Flat("M"); b = HF.bounds(Fl, back); pad = 10
    body = HF.draw_back(Fl) if back else HF.draw_front(Fl)
    W, Hh = b[2] - b[0] + 2*pad, b[3] - b[1] + 2*pad
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{b[0]-pad} {b[1]-pad} {W} {Hh}" width="{int(W*ppm)}" height="{int(Hh*ppm)}">'
           f'<rect x="{b[0]-pad}" y="{b[1]-pad}" width="{W}" height="{Hh}" fill="#fff"/>{body}</svg>')
    im = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode()))).convert("RGBA")
    if art and not back:
        # the written DST files read back (dstview, transparent): fronts shifted to flat coords, sleeves warped onto the
        # flat sleeve with the pattern -> flat affine
        bbx = (b[0]-pad, b[1]-pad, b[2]+pad, b[3]+pad); emb = Image.new("RGBA", im.size, (0, 0, 0, 0))
        for P in ("FR", "FL"):
            base = f"out/stitch/M/HAKI_{kccore.SHORT}_{P}_M"; o_ = DV.origin_of(base)
            emb = Image.alpha_composite(emb, DV.image([base], bbx, ppm, origins=[(o_[0], o_[1] + Fl.fnd)], bg=None).resize(im.size))
        for P in ("SR", "SL"):
            M = _sleeve_affine(Fl, P); base = f"out/stitch/M/HAKI_{kccore.SHORT}_{P}_M"
            g_, _ = F_.pieces("M"); sb = g_[kccore.PIECE_CODE[P]].sew_poly().bounds; sbb = (sb[0]-5, sb[1]-5, sb[2]+5, sb[3]+5); sp_ = ppm * 1.4
            src = DV.image([base], sbb, sp_, bg=None)
            # the flat is a FRONT view: only the sleeve's front half (S01 x > 0, S02 x < 0) is visible
            sa = np.array(src); xs_ = sbb[0] + (np.arange(sa.shape[1]) + 0.5) / sp_
            back = (xs_ < 0) if P == "SR" else (xs_ > 0); sa[:, back, 3] = 0; src = Image.fromarray(sa)
            A = np.array([[M[0], M[1], M[4]], [M[2], M[3], M[5]], [0, 0, 1]]); Ai = np.linalg.inv(A)
            # output px (u, v) -> flat (x, y) -> sleeve (xs, ys) -> source px
            T1 = np.array([[1/ppm, 0, bbx[0]], [0, 1/ppm, bbx[1]], [0, 0, 1]]); T2 = np.array([[sp_, 0, -sbb[0]*sp_], [0, sp_, -sbb[1]*sp_], [0, 0, 1]])
            K = T2 @ Ai @ T1
            emb = Image.alpha_composite(emb, src.transform(im.size, Image.AFFINE, tuple(K[:2].ravel()), resample=Image.BILINEAR))
        a = emb.split()[3]
        sh = Image.new("RGBA", emb.size, (0, 0, 0, 0)); sh.putalpha(a.point(lambda v: int(v*0.45))); sh = sh.filter(ImageFilter.GaussianBlur(1.0))
        base = Image.new("RGBA", emb.size, (0, 0, 0, 0)); base.paste(sh, (1, 2))
        im = Image.alpha_composite(im, Image.alpha_composite(base, emb))
        # redraw the zip on top
        zsvg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{b[0]-pad} {b[1]-pad} {W} {Hh}" width="{int(W*ppm)}" height="{int(Hh*ppm)}">'
                f'{HF.zip_tape(Fl, Fl.fnd - 2, Fl.hem_edge)}</svg>')
        im = Image.alpha_composite(im, Image.open(io.BytesIO(cairosvg.svg2png(bytestring=zsvg.encode()))).convert("RGBA"))
    return im.convert("RGB"), (b[0]-pad, b[1]-pad, b[2]+pad, b[3]+pad)

from specbase import img_tag

# ---------------------------------------------------------------- pages
def p_cover(index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>', t(14, 22, "HAKI STUDIOS", 3.0, 700, MUTED), t(14, 34, NAME, 7.0, 700),
         t(14, 41.5, f"Style {STYLE} · {REV} · {DATE} · sizes XS–3XL · base size M · block zip-hoodie (Drum Island body + hood) · cm unless marked mm", 2.4, 400, MUTED),
         f'<line x1="14" y1="45" x2="{SW-14}" y2="45" stroke="{INK}" stroke-width="0.4"/>']
    fr, _ = flat_png(False); bk, _ = flat_png(True, art=False)
    tag, h = img_tag(fr, 14, 50, 100); o.append(tag); o.append(t(14, 50 + h + 4, "FRONT — badges 01–04 + 05 star field (DST read back, size M)", 2.0, 700))
    tag, h2 = img_tag(bk, 118, 50, 80); o.append(tag); o.append(t(118, 50 + h2 + 4, "BACK + HOOD — plain (sleeve backs carry stars: E05, not drawn here)", 2.0, 700)); o.append(prop(118, 50 + h2 + 7.5, "no embroidery on back + hood", 1.7))
    ix = 206; o.append(t(ix, 56, "CONTENTS", 2.8, 700)); y = 62
    for name, pg in index: o.append(t(ix, y, name, 1.85)); o.append(t(SW - 14, y, str(pg), 1.85, 600, MUTED, "end")); y += 3.7
    y += 3; o.append(t(ix, y, "KEY SPECS", 2.4, 700)); y += 4.6
    for a, b_, p in [("Body + sleeve", "Drum Island jacket — approved fit, unchanged", False), ("Hood", "3 panels, sherpa-lined (cream), no drawcord", True),
                     ("Hem / cuffs", f"self fabric + elastic ({HD.hcm('S','M')/10:.1f} / {HD.hcm('T','M')/10:.1f} cm)", True), ("Zip", "2-way separating, YKK #5 metal, brass", True),
                     ("Shell", "12 oz cotton duck, washed black", True), ("Lining", "plaid flannel body · taffeta sleeves · sherpa hood", True),
                     ("Embroidery", f"5 elements, 4 pieces, {len({c for p in CUR for c in CUR[p]['colours']})} threads, 3D puff badges (G pages)", False),
                     ("Pattern", "XS–3XL, DXF (AAMA) + 1:1 plot", False)]:
        o.append(t(ix, y, a, 1.9, 400, MUTED)); o.append(t(ix + 23, y, b_, 1.8, 600, PROP if p else INK)); y += 3.7
    y += 3
    for l in ["Block: zip-hoodie (engine/hoodie.py = Drum Island body + 3-panel hood + elastic hem + cuff bands),",
              "founder decision 19 Oct 2026. Welts at this mockup's position via the block's welt override [proposed — confirm]."]:
        o.append(t(ix, y, l, 1.55, 700, PROP)); y += 3.1
    o.append(t(SW - 14, SH - 8, FOOT, 1.8, 400, MUTED, "end"))
    return o

NOTES = [("1", "Hood: 3 panels — side pair + 10 cm centre panel. Washed black duck outside, cream sherpa inside, bagged at the face edge; 6 mm topstitch. No drawcord. Plain (no embroidery).", True),
         ("2", "Hood neck: shell hood to body neckline, sherpa hood to the front facings + back neck facing. Embroidery keeps 10 mm clear of the neck seam.", True),
         ("3", "Zip: 2-way separating, YKK #5 metal, antique brass, two pullers (mockup). Embroidery keeps 15 mm each side of CF.", True),
         ("4", f"Welt pockets at the mockup's steep slash position ({F_.WELT['cx']/10:.1f} cm from CF, {F_.WELT['cy']/10:.1f} cm below the neck, {F_.WELT['angle']:.0f}°, size M), Drum Island welt 1.4 × 13; embroidery keeps {F_.KEEP_WELT:.0f} mm clear (DST-checked, T7).", True),
         ("5", f"Hem band: self fabric, {HD.hcm('S','M')/10:.1f} cm finished, folded; {HD.EL_HEM_W/10:.0f} cm elastic, flat {HD.FLAT/10:.0f} cm each side of the zip. Not embroidered.", True),
         ("6", f"Cuff band: self fabric, {HD.hcm('T','M')/10:.1f} cm finished, folded, closed into a loop. Not embroidered (stars stop 10 mm above the cuff seam).", True),
         ("7", "Embroidery: 01 JP + 03 CN badges (FR), 02 EN + 04 KR badges (FL), 05 star field (FR, FL, both full sleeves): direct embroidery on the cut panels before any seam; 3D puff on 01 / 02 / 03 dots (G pages).", False),
         ("8", "Lining: cotton flannel body (plaid, as mockup), polyester taffeta sleeves; hood fully lined in sherpa. Labels on the back neck facing.", True)]

def p_flats():
    o = H("FLATS + CONSTRUCTION", "Size M · zip-hoodie block (Drum Island body + 3-panel sherpa hood + self-fabric bands); numbered notes = hoodie + design specifics.", "T2")
    fr, bb = flat_png(False); bk, bb2 = flat_png(True, art=False)
    tag, h = img_tag(fr, 12, 30, 98); o.append(tag); tag, h2 = img_tag(bk, 114, 30, 86); o.append(tag)
    Fl = HF.Flat("M"); s1 = 98 / (bb[2] - bb[0]); s2 = 86 / (bb2[2] - bb2[0])
    def cxy(i, x, y):
        b_, s_, ox = (bb, s1, 12) if i == 0 else (bb2, s2, 114); return ox + (x - b_[0]) * s_, 30 + (y - b_[1]) * s_
    calls = [(1, (0, -(HD.hcm("Q", "M") - 120)), "1"), (0, (Fl.b.neck2 * 0.6, Fl.fnd * 0.55), "2"), (0, (0, Fl.hem_seam - 60), "3"),
             (0, (F_.WELT["cx"] + 20, F_.WELT["cy"] + Fl.fnd), "4"), (0, (-200, Fl.hem_seam + 25), "5"), (0, (Fl.cuff_out[0] - 30, Fl.cuff_out[1] - 20), "6"), (0, (-150, 140), "7"), (1, (0, 280), "8")]
    for i, (x, y), n in calls:
        X, Y = cxy(i, x, y)
        o.append(f'<circle cx="{f(X)}" cy="{f(Y)}" r="2.4" fill="#FFFFFF" stroke="{INK}" stroke-width="0.3"/>' + t(X, Y + 0.85, n, 2.1, 700, INK, "middle"))
    y = 34; tx = 206
    for n, s_, p in NOTES:
        o.append(f'<circle cx="{tx}" cy="{f(y - 0.8)}" r="2.0" fill="#FFFFFF" stroke="{INK}" stroke-width="0.25"/>' + t(tx, y, n, 1.8, 700, INK, "middle"))
        words = s_.split(); line, lines = "", []
        for w in words:
            if len(line) + len(w) > 52: lines.append(line); line = w
            else: line = (line + " " + w).strip()
        lines.append(line)
        for j, l in enumerate(lines): o.append(t(tx + 4, y + j * 3.0, l, 1.6, 400, PROP if p else INK))
        y += 3.0 * len(lines) + 2.2
    o.append(t(tx, y + 2, "Amber = proposed by Haki tech design — confirm.", 1.6, 600, PROP))
    return o

def p_pom():
    o = H("SIZE CHART + MEASUREMENT CHECK", "Chart in cm. Body + sleeve rows are the approved Drum Island chart, unchanged. Hood + band rows are the zip-hoodie block (proposed). ½ = half measurement, flat.", "T3")
    Fl = HF.Flat("M"); b = HF.bounds(Fl); s = 62 / (b[2] - b[0]); ox, oy = 12, 34
    o.append(flat_g(HF.draw_front(Fl), b, ox, oy, s))
    X = lambda x: ox + (x - b[0]) * s; Y = lambda y: oy + (y - b[1]) * s
    o.append(dim_v(Y(0), Y(Fl.hem_edge), X(Fl.ua[0] + 22), "A", 1.8, side=1))
    o.append(dim_h(X(-Fl.ua[0]), X(Fl.ua[0]), Y(Fl.ua[1] + 6), "B", 1.8))
    o.append(dim_h(X(-Fl.sp[0]), X(Fl.sp[0]), Y(Fl.sp[1] - 4), "C", 1.8))
    o.append(dim_v(Y(-(HD.hcm("Q", "M") - 70)), Y(0), X(-Fl.b.neck2 - 90), "Q", 1.8))
    o.append(dim_v(Y(Fl.hem_seam), Y(Fl.hem_edge), X(-Fl.sweep2 - 14), "S", 1.6))
    tb = 12; ty = oy + (b[3] - b[1]) * s + 8
    for j, l in enumerate(["D ½ hem, relaxed (elastic) · E armhole, straight · F ½ bicep", "G sleeve length incl. cuff band · H ½ cuff, relaxed (elastic)",
                           "J neck width · K / L front / back neck drop · P shoulder fwd", "R hood width · T cuff band height"]):
        o.append(t(tb, ty + j * 3, l, 1.45, 400, MUTED))
    hd = ["", "Point of measure", "How measured"] + SIZES + ["Tol", "Source"]; cx = [80, 85, 128, 168, 177, 186, 195, 204, 213, 223, 233, 243]
    for x_, h_ in zip(cx, hd): o.append(t(x_, 31, h_, 1.6, 700, MUTED))
    order = ["A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "P", "Q", "R", "S", "T"]
    for i, k in enumerate(order):
        nm, how, vals, tol, src = CH[k]; y = 35.5 + i * 4.1; pr = src == "PROPOSED"
        if i % 2 == 0: o.append(f'<rect x="79" y="{f(y - 2.9)}" width="{SW - 90}" height="4.1" fill="{ALT}"/>')
        col = PROP if pr else INK
        o.append(t(cx[0], y, k, 1.7, 700, col)); o.append(t(cx[1], y, nm[:34], 1.55, 600, col)); o.append(t(cx[2], y, how[:52], 1.3, 400, MUTED))
        for j, v in enumerate(vals): o.append(t(cx[3 + j], y, f"{v:g}", 1.55, 600 if SIZES[j] == "M" else 400, col))
        o.append(t(cx[10], y, f"±{tol:g}", 1.45, 400, MUTED)); o.append(t(cx[11], y, "proposed" if pr else "jacket", 1.45, 600, col))
    y = 35.5 + len(order) * 4.1 + 4
    o.append(t(80, y, "PATTERN CHECK — every size measured off the drafted pattern pieces vs this chart", 1.9, 700)); y += 4.2
    for j, sz in enumerate(SIZES):
        ok = CHECK[sz] and WALKS_OK[sz] and SHAPE_OK[sz]
        o.append(t(cx[3 + j], y, "pass" if ok else "FAIL", 1.6, 700, GREEN if ok else RED))
    o.append(t(80, y, "chart · seam walks · shape checks", 1.5, 400, MUTED))
    y += 6
    for l in ["Hood height (Q) and width (R) include 1.5 cm for the sherpa pile (~8 mm).",
              "D and H are relaxed: the elastic sets them. Extended = the body hem / sleeve opening of the jacket.",
              "The pattern is drafted, not fitted: sew + fit a blank (or this design) in M before cutting the size set (LESSONS C7)."]:
        o.append(t(80, y, l, 1.55, 400, MUTED)); y += 3.2
    return o

def _draw(o, g, codes, x0, y0, wmax, s, lw=0.3, tm=1.2, gap=4, emb=None):
    x, y, rowh = x0, y0, 0.0
    for code in codes:
        pc = g[code]; b = PT.cut_poly(pc).bounds; w, h = (b[2] - b[0]) * s, (b[3] - b[1]) * s
        if x + w > x0 + wmax: x = x0; y += rowh + gap; rowh = 0
        X = (lambda xx0, b0: (lambda q: xx0 + (q - b0) * s))(x, b[0]); Y = (lambda yy0, b1: (lambda q: yy0 + (q - b1) * s))(y, b[1])
        o += PD.piece_svg(pc, X, Y, s, label=True, size="M", lw=lw, text_mm=tm, emb=(emb or {}).get(code, ()))
        x += w + gap; rowh = max(rowh, h)
    return y + rowh

def p_pieces():
    o = H("PATTERN — pieces + cut list (size M)", "Seam allowance included; dashed = sew line; slits = notches; crossed circles = drill holes; outlined areas = embroidery placement (DXF layer 8).", "T4")
    em = PC.emb_marks("M")
    y1 = _draw(o, gM, ["B01", "F01", "F02", "S01", "S02"], 12, 30, 190, 0.075, 0.32, 1.2, emb=em)
    y2 = _draw(o, gM, ["H01", "H02", "H03", "H04", "K01", "K02", "L01", "L02", "L03"], 12, y1 + 5, 190, 0.05, 0.26, 0.85, 8)
    _draw(o, gM, ["R01", "R02", "P01", "P02", "P03", "P04"], 12, y2 + 5, 190, 0.05, 0.26, 1.0, 4)
    tx = 206; o.append(t(tx, 31, "CUT LIST — per hoodie", 2.3, 700))
    hd = ["Code", "Piece", "Cut", "Material", "Emb."]; cx = [tx, tx + 9, tx + 37, tx + 48, tx + 76]
    for x_, h_ in zip(cx, hd): o.append(t(x_, 35.5, h_, 1.55, 700, MUTED))
    rows = [c for c in HD.ORDER if not c.startswith("I")]
    embc = {v: k for k, v in kccore.PIECE_CODE.items()}
    for i, code in enumerate(rows):
        pc = gM[code]; y = 39.5 + i * 3.4; new = code.startswith("H") or code in ("R01", "R02")
        if i % 2 == 0: o.append(f'<rect x="{tx - 1}" y="{f(y - 2.4)}" width="{SW - tx - 11}" height="3.4" fill="{ALT}"/>')
        col = PROP if new else INK
        o.append(t(cx[0], y, code, 1.45, 700, col)); o.append(t(cx[1], y, pc.name.replace(" (wearer's)", "")[:21], 1.42, 400, col))
        o.append(t(cx[2], y, pc.qty.replace(" (2 pairs)", ""), 1.42)); o.append(t(cx[3], y, pc.material.split(" — ")[0][:16], 1.4))
        if code in embc: o.append(t(cx[4], y, embc[code], 1.42, 700, "#0A84D6"))
    y = 39.5 + len(rows) * 3.4 + 2
    for l in ["Amber = zip-hoodie block parts (hood, bands); rest = jacket pattern.", "Blue = embroidered piece (cut first, embroider flat, then sew).",
              "SA 1.0 cm; band joins + hems 0.8; hood face edge 0.6.", "Hood lining (H03/H04) cut in sherpa.",
              "Files: DXF per size + all sizes (AAMA layers), 1:1 plot PDF size M."]:
        o.append(t(tx, y, l, 1.45, 400, MUTED)); y += 3.2
    return o

def p_hood():
    o = H("HOOD + BANDS — detail and per-size table", "Hood side + centre panel at 1:4 (size M) with seam lengths; elastic and band lengths per size. All values read from the pattern.", "T5")
    s = 0.25; Hd = mM["hood"]
    for code, ox, oy in (("H01", 18, 40), ("H02", 112, 40)):
        pc = gM[code]; b = PT.cut_poly(pc).bounds
        X = (lambda b0: (lambda q: ox + (q - b0) * s))(b[0]); Y = (lambda b1: (lambda q: oy + (q - b1) * s))(b[1])
        o += PD.piece_svg(pc, X, Y, s, label=True, size="M", lw=0.4, text_mm=1.6)
        if code == "H01":
            for e in pc.edges:
                p, _ = PT.at(e.pts, e.length / 2)
                o.append(t(X(p[0]) + (3 if e.name != "face edge" else -3), Y(p[1]) + (4 if e.name == "neck" else 0), f"{e.name} {e.length/10:.1f}", 1.5, 600, "#0A84D6", "start" if e.name != "face edge" else "end"))
        else:
            o.append(t(ox, oy + (b[3] - b[1]) * s + 5, f"{HD.CW/10:.0f} × {Hd['seam']/10:.1f} cm", 1.6, 600, "#0A84D6"))
    hd = ["Size", "Q hood ht", "R hood wd", "Side neck", "Centre seam", "Face edge", "Hem band cut", "Hem elastic", "Cuff band cut", "Cuff elastic", "Zip"]
    cx = [150, 160, 172, 184, 196, 209, 221, 236, 250, 264, 278]
    o.append(t(150, 33, "PER SIZE (cm) — cut lengths are sew-line lengths; elastic = relaxed cut length", 1.8, 700))
    for x_, h_ in zip(cx, hd): o.append(t(x_, 38, h_, 1.35, 700, MUTED))
    for i, sz in enumerate(SIZES):
        g, mt = G[sz]; y = 42.5 + i * 4.0; Hs = mt["hood"]
        if i % 2 == 0: o.append(f'<rect x="149" y="{f(y - 2.8)}" width="{SW - 160}" height="4" fill="{ALT}"/>')
        zip_l = g["F01"].edges[0].length + mt["hem_h"] - 5
        vals = [sz, Hs["Q"], Hs["R"], Hs["Ls"], Hs["seam"], Hs["face_len"], mt["hem_band"], mt["el_hem"], mt["sleeve_open"], mt["el_cuff"] + 15, zip_l]
        for j, v in enumerate(vals): o.append(t(cx[j], y, v if isinstance(v, str) else f"{v/10:.1f}", 1.5, 700 if j == 0 or sz == "M" else 400))
    y = 42.5 + 7 * 4.0 + 4
    o.append(t(150, y, "SEAM WALKS — size M", 1.8, 700)); y += 4
    for nm, a, b_, tol in MEAS["M"][1]:
        ok = tol is None or abs(a - b_) <= tol
        o.append(t(150, y, nm, 1.45)); o.append(t(250, y, f"{a/10:.1f} / {b_/10:.1f}", 1.45, 600)); o.append(t(275, y, "ease" if tol is None else ("ok" if ok else "CHECK"), 1.45, 700, GREEN if ok else RED)); y += 3.2
    y = 150
    o.append(t(14, y, "BANDS", 2.0, 700)); y += 4
    for l in [f"Hem band R01: cut {mM['hem_band']/10:.1f} × {2*mM['hem_h']/10:.0f} cm + SA, folded at {mM['hem_h']/10:.1f} cm. Elastic {HD.EL_HEM_W/10:.0f} cm wide, {mM['el_hem']/10:.1f} cm relaxed,",
              f"   stitched in the fold; first + last {HD.FLAT/10:.0f} cm (at the zip) without elastic so the zip lies flat. Relaxed ½ hem = chart D.",
              f"Cuff band R02 (×2): cut {mM['sleeve_open']/10:.1f} × {2*mM['cuff_h']/10:.0f} cm + SA, closed into a loop, folded. Elastic loop {HD.EL_CUFF_W/10:.1f} cm wide,",
              f"   {mM['el_cuff']/10:.1f} cm + 1.5 cm overlap. Relaxed ½ cuff = chart H; gather ratio {mM['el_cuff']/mM['sleeve_open']:.2f}.",
              "Hood: shell + sherpa sewn separately, bagged at the face edge, turned, 6 mm topstitch through all layers (sherpa side down)."]:
        o.append(t(14, y, l, 1.55, 400, PROP if l.startswith(("Hem", "Cuff", "Hood")) else INK)); y += 3.3
    return o

def p_bom():
    o = H("BILL OF MATERIALS", "Per hoodie, size M. Fabric = pattern piece area ÷ (150 cm usable width × 80 % marker efficiency) — replace with the factory's marker.", "T6")
    shell = [c for c in HD.ORDER if gM[c].material.startswith("Shell")]; sher = ["H03", "H04"]
    flan = [c for c in HD.ORDER if "flannel" in gM[c].material]; taf = [c for c in HD.ORDER if "taffeta" in gM[c].material]
    pock = [c for c in HD.ORDER if gM[c].category == "POCKETING"]; fus = [c for c in HD.ORDER if c.startswith("I")]
    m = lambda codes: area_m2(codes, gM) / (1.5 * 0.8)
    zip_l = gM["F01"].edges[0].length + mM["hem_h"] - 5
    cols = sorted({c for p in CUR for c in CUR[p]["colours"]})
    hoops = sum(len(CUR[p]["splits"]["sections"]) or 1 for p in CUR)
    BACKING = sum((s_["size_mm"][0] + 60) * (s_["size_mm"][1] + 60) for p in CUR for s_ in CUR[p]["splits"]["sections"].values()) / 1e6   # m² = m at 100 cm width
    rows = [("Shell", "12 oz cotton duck canvas, washed black (pre-washed before embroidery)", f"{m(shell):.2f} m", True),
            ("Hood lining", "Sherpa 280 g/m² polyester, cream", f"{m(sher):.2f} m", True),
            ("Body lining", "Cotton flannel, plaid (green / red / navy, as mockup)", f"{m(flan):.2f} m", True), ("Sleeve lining", "Polyester taffeta 210T, black", f"{m(taf):.2f} m", True),
            ("Pocketing", "8 oz cotton twill", f"{m(pock):.2f} m", True), ("Fusing", "Woven fusible 60 g/m² (facings, welts)", f"{m(fus):.2f} m", False),
            ("Zip", f"YKK #5 metal, brass, 2-way separating, {zip_l/10:.0f} cm (M)", "1", True),
            ("Elastic — hem", f"{HD.EL_HEM_W/10:.0f} cm woven elastic, {mM['el_hem']/10:.1f} cm (M)", "1", True),
            ("Elastic — cuff", f"{HD.EL_CUFF_W/10:.1f} cm woven elastic, {(mM['el_cuff']+15)/10:.1f} cm (M)", "2", True),
            ("Embroidery thread", f"40wt polyester, {len(cols)} colours over the jacket, ≤ 12 per file (G3) — FR + FL + SR + SL", f"{sum(CUR[p]['stitches'] for p in CUR):,} stitches (M)", True),
            ("3D puff foam", "3 mm embroidery foam, black: FR one sheet (01 + 03 dot ring), FL one sheet (02)", "2 sheets", True),
            ("Embroidery backing", f"2.5 oz cutaway, black, 100 cm wide — {hoops} hoopings per jacket (G6), each split file + 30 per side", f"{BACKING:.2f} m", True),
            ("Thread — seams", "Coats Epic 120 (Tex 27), black — estimate from the block, factory to confirm", "~ 450 m", True), ("Thread — topstitch", "Coats Gral 40 (Tex 60), tonal charcoal — estimate from the block", "~ 140 m", True),
            ("Labels", "Main + size on back neck facing; care label left side seam lining", "1 set", False)]
    hd = ["Item", "Description", "Qty / consumption"]; cx = [12, 52, 200]
    for x_, h_ in zip(cx, hd): o.append(t(x_, 33, h_, 1.8, 700, MUTED))
    for i, (a, b_, q, p) in enumerate(rows):
        y = 38 + i * 4.4
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y - 3.0)}" width="{SW - 22}" height="4.4" fill="{ALT}"/>')
        o.append(t(cx[0], y, a, 1.75, 700)); o.append(t(cx[1], y, b_ + ("  [proposed — confirm]" if p else ""), 1.7, 400, PROP if p else INK)); o.append(t(cx[2], y, q, 1.75, 600))
    y = 38 + len(rows) * 4.4 + 5
    o.append(t(12, y, "ZIP LENGTH PER SIZE (cm, hem-band edge to CF neck − 0.5)", 1.9, 700)); y += 4.4
    for j, sz in enumerate(SIZES):
        g, mt = G[sz]; o.append(t(12 + j * 22, y, f"{sz}  {(g['F01'].edges[0].length + mt['hem_h'] - 5)/10:.0f}", 1.8, 600))
    return o

def p_placement():
    o = H("EMBROIDERY PLACEMENT ON THE PATTERN — every size, every keep-out", "Measured on each size's drafted pattern pieces (sew lines) from the per-size art (emb_place.py). mm. Min = keep-out.", "T7")
    pieces = kccore.PIECES
    o.append(t(12, 31, "CLEARANCE TO EACH KEEP-OUT (mm) — fronts: CF zip, armhole, shoulder, side, hem band, hood neck, welt; sleeves: cap, underarm front/back, cuff band", 1.8, 700))
    y = 37; allok = True
    for P in pieces:
        mn = EP.mins(P); keys = list(mn)
        o.append(t(12, y, f"{P} — {kccore.PIECE_NAME[P]} ({kccore.PIECE_CODE[P]})", 1.8, 700)); y += 3.6
        cx = [12] + [32 + 24*i for i in range(len(keys))]
        o.append(t(cx[0], y, "Size", 1.5, 700, MUTED))
        for i, k in enumerate(keys): o.append(t(cx[i + 1], y, f"{k} (min {mn[k]:.0f})", 1.45, 700, MUTED))
        y += 3.4
        for j, sz in enumerate(SIZES):
            c = EP.clearances(sz)[P]
            if j % 2 == 0: o.append(f'<rect x="11" y="{f(y - 2.4)}" width="{SW - 22}" height="3.2" fill="{ALT}"/>')
            o.append(t(cx[0], y, sz, 1.45, 700))
            for i, k in enumerate(keys):
                ok = c[k] >= mn[k] - 0.3; allok &= ok
                o.append(t(cx[i + 1], y, f"{c[k]:.1f}", 1.45, 600 if not ok else 400, GREEN if ok else RED))
            y += 3.2
        y += 2.2
    o.append(t(12, y + 1, f"Result: {'ALL KEEP-OUTS PASS on every size' if allok else 'KEEP-OUT FAILURE — see red'}.", 2.0, 700, GREEN if allok else RED))
    try:
        wc = json.load(open("welt_check.json")); worst = min(v for sz in wc for v in wc[sz].values())
        okw = worst >= F_.KEEP_WELT - 0.6
        o.append(t(150, y + 1, f"Welt line: nearest STITCH to the welt box, read from every DST (full + splits), all sizes: {worst:.1f} mm — {'no stitch on the welt' if okw else 'CHECK'}.", 1.7, 700, GREEN if okw else RED))
    except FileNotFoundError:
        pass
    o.append(t(12, y + 5, "Badges graded A 92 % (XS–S) / B 100 % (M–XL) / C 106 % (XXL–3XL), anchors follow each size's panel; stars keep their size, positions follow the panel (E05).", 1.6, 400, MUTED))
    o.append(t(12, y + 8.4, "The art outline, art box, split line and every needle start are on DXF layer 8 / 13 of each size's pattern file.", 1.6, 400, MUTED))
    return o

def p_fit():
    o = H("SAMPLE CHECKS + OPEN QUESTIONS", "The body is the approved jacket; the zip-hoodie block (hood, bands) has no fitted sample yet — check it on this design's first sample.", "T8")
    checks = ["Hood on the head (zip closed): crown clears the head by 2–3 cm with the sherpa; face opening doesn't pull at forehead or chin.",
              "Hood down: lies flat on the back, centre panel straight, no drag lines from the neck seam toward the shoulders.",
              "Neck seam: hood sits on the neckline without rippling; the star field stays ≥ 10 mm below the hood seam.",
              "Hem band: gathers even, none in the 6 cm next to the zip; stars + KR oval stay ≥ 10 mm above the band seam.",
              "Cuff band: gathers even; sleeve stars end ≥ 10 mm above the cuff seam.",
              "Welts at the slash position (58°): pocket bags clear the CN badge 03 + KR oval 04; no stitch within 6 mm of a welt (T7).",
              "Embroidery: puff letters + dots domed and clean at the edges (no foam showing), no puckering round the dense badges; glow halo soft.",
              "Same as the jacket (should already pass): chest, shoulder, armhole, sleeve pitch, body length."]
    o.append(t(12, 34, "CHECK ON THE SAMPLE", 2.4, 700)); y = 40
    for c in checks:
        o.append(f'<rect x="12" y="{f(y - 2.2)}" width="2.6" height="2.6" fill="none" stroke="{INK}" stroke-width="0.25"/>'); o.append(t(16.5, y, c, 1.7)); y += 4.2
    y += 4; o.append(t(12, y, "OPEN QUESTIONS — confirm before the sample", 2.4, 700)); y += 6
    qs = ["1. Text from the founder's source frame: 宇宙をきれいに · KEEP CLEAN OUR SPACE · 不要世界汚染 (汚 as drawn; Simplified 污?) · 우리들 소중한 우주! (source reads 소중함 — confirm).",
          "2. Back + hood plain; star field on both fronts + all round both sleeves. Confirm, or add back / hood stars.",
          "3. Hood size 36 × 26 cm (M) incl. sherpa allowance, no drawcord; hem / cuff bands 5.5 / 5 cm with elastic (zip-hoodie block, proposed).",
          "4. Zip: 2-way separating YKK #5 metal, antique brass (mockup shows two pullers).",
          "5. Shell: 12 oz washed black duck, pre-washed before embroidery; lining: plaid flannel (body), taffeta (sleeves), cream sherpa (hood).",
          f"6. Welts at the mockup's slash position ({F_.WELT['cx']/10:.1f} cm from CF, {F_.WELT['cy']/10:.1f} cm below the neck, {F_.WELT['angle']:.0f}°) via the block's welt override.",
          "7. Sample size M first (the blank fit of the hoodie block is still pending); then the size set.",
          "Closed 19 Oct: hood block = zip-hoodie block (engine/hoodie.py, elastic hem + cuff bands) — founder decision; welt override in the engine."]
    for q in qs: o.append(KD.auto(12, y, q, 1.7, PROP)); y += 4.2          # CJK runs as font outlines
    return o

def p_revisions():
    o = H("REVISION LOG + SAMPLE TRACKER", "Every change, newest last.", "T9")
    revs = [("Rev A", "16 Oct 2026", "Embroidery only: four neon text badges (JP, EN, CN, KR) + star field on the Drum Island body pieces; text set from fonts; "
                            "pattern waiting for the hood block."),
            ("Rev B", DATE, "Independent review fixes: stroke-column satin text, stipple glow halo, domed puff rims in tint threads + faceted stars, curved JP baseline, "
                            "solid red star, CN + KR text from the founder's source frame, motifs traced + A14/A15 gates, every mockup star placed (seam glints removed), heavier EN; compare sheets drawn from the DST files. "
                            "Garment: zip-hoodie block (founder decision 19 Oct) with this mockup's slash welts (engine welt override); pattern XS–3XL, DXF + 1:1 plot, T pages.")]
    y = 36
    for rv, dt, ch in revs:
        o.append(t(12, y, rv, 1.8, 700)); o.append(t(36, y, dt, 1.7))
        words = ch.split(); line, lines = "", []
        for w in words:
            if len(line) + len(w) > 150: lines.append(line); line = w
            else: line = (line + " " + w).strip()
        lines.append(line)
        for j, l in enumerate(lines): o.append(t(60, y + j * 3.2, l, 1.7))
        y += 3.2 * len(lines) + 4
    y += 4; o.append(t(12, y, "SAMPLE TRACKER", 2.4, 700)); y += 5
    for i, sname in enumerate(["Embroidery strike-off, size M (F1)", "First sample, size M (hoodie block fit + embroidery)", "Size set", "Approved for bulk"]):
        yy = y + i * 9
        o.append(f'<rect x="11" y="{f(yy - 4)}" width="{SW - 22}" height="9" fill="{ALT if i % 2 == 0 else "#FFFFFF"}" stroke="#DDD" stroke-width="0.2"/>')
        o.append(t(13, yy + 1, sname, 1.8, 600))
    return o

PAGES = ["T1 Cover", "T2 Flats + construction", "T3 Size chart + measurement check", "T4 Pattern pieces + cut list", "T5 Hood + bands detail",
         "T6 Bill of materials", "T7 Embroidery placement + keep-outs, all sizes", "T8 Sample checks + open questions", "T9 Revision log + sample tracker"]

def build(emb_pdf, emb_pages, out_pdf):
    for sz in SIZES: assert CHECK[sz] and WALKS_OK[sz] and SHAPE_OK[sz], f"pattern QA failed for {sz}"
    index = [(n, i + 1) for i, n in enumerate(PAGES)] + [("EMBROIDERY SECTION (G1–G6, specs, F1)", len(PAGES) + 1)] + emb_pages
    pages = [p_cover(index), p_flats(), p_pom(), p_pieces(), p_hood(), p_bom(), p_placement(), p_fit(), p_revisions()]
    w = PdfWriter(); os.makedirs("out/pages", exist_ok=True)
    for i, pg in enumerate(pages, 1):
        svg = doc(pg); pdf = f"out/pages/T{i}.pdf"
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=pdf)
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"out/pages/prev_T{i}.png", output_width=2400)
        w.append(PdfReader(pdf))
    w.append(PdfReader(emb_pdf))
    w.write(out_pdf)
    return len(pages)
