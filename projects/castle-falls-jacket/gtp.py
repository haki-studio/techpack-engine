"""Garment tech pack pages — Castle Falls jacket (Drum Island block), washed navy, embroidery on back, fronts and sleeves."""
import cfcore
import json, math, os, pickle
import numpy as np
import cairosvg
from PIL import Image
from shapely.ops import unary_union
from shapely.geometry import box
from pypdf import PdfWriter, PdfReader
import sheet as SHT
from sheet import t, swatch, doc, INK, MUTED, RED, ORANGE, GUIDE, GREEN, SW, SH
from render import f
import drum, techflat as TF
import specbase as SB
from specbase import img_tag

REV = cfcore.REV_GAR; DATE = cfcore.DATE; STYLE = cfcore.STYLE; NAME = cfcore.NAME
FOOT = f"HAKI STUDIOS · {NAME} · {STYLE} · GARMENT TECH PACK · {REV} · {DATE}"
PROP = "#8A5A00"        # colour for 'proposed — confirm' text

def header(title, sub, page):
    SB.FOOT = FOOT
    return SB.header(title, sub, page)

def prop(x, y, s, size=1.85):
    return t(x, y, s + "  [proposed — confirm]", size, 600, PROP)

def flat_group(svgbody, b, ox, oy, s, k=None):
    return f'<g transform="translate({f(ox - b[0]*s)} {f(oy - b[1]*s)}) scale({f(s)})">{svgbody}</g>'

# ---------------------------------------------------------------- embroidery grading
import pickle as _pk
from shapely.ops import unary_union as _uu
_AB = {}
def art_box(size, P):
    if size not in _AB: _AB[size] = _pk.load(open(f"art_{size}.pkl", "rb"))
    import dst2 as _d; return _d.bounds_of([r["geom"] for r in _AB[size][P]])
EMB = {P: {"box": art_box("M", P), "ref": "front"} for P in cfcore.PIECES}
GRADE = cfcore.GRADE

def callout(x, y, n, tx, ty):
    return (f'<line x1="{f(x)}" y1="{f(y)}" x2="{f(tx)}" y2="{f(ty)}" stroke="{INK}" stroke-width="0.18"/>'
            f'<circle cx="{f(x)}" cy="{f(y)}" r="0.6" fill="{INK}"/><circle cx="{f(tx)}" cy="{f(ty)}" r="2.3" fill="#FFFFFF" stroke="{INK}" stroke-width="0.25"/>'
            + t(tx, ty + 0.8, str(n), 2.0, 700, INK, "middle"))

# ---------------------------------------------------------------- pages
def p_cover(index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>']
    o.append(t(14, 22, "HAKI STUDIOS", 3.0, 700, MUTED))
    o.append(t(14, 34, NAME, 7.2, 700))
    o.append(t(14, 41.5, f"Style {STYLE} · {REV} · {DATE} · sizes XS–3XL · base size M · all dimensions cm unless marked mm", 2.6, 400, MUTED))
    o.append(f'<line x1="14" y1="45" x2="{SW-14}" y2="45" stroke="{INK}" stroke-width="0.4"/>')
    fr = Image.open("cover_front.png"); bk = Image.open("cover_back.png")
    tag, h = img_tag(fr, 14, 52, 88); o.append(tag); o.append(t(14, 52 + h + 4, "FRONT", 2.2, 700))
    tag, h2 = img_tag(bk, 108, 52, 88); o.append(tag); o.append(t(108, 52 + h2 + 4, "BACK", 2.2, 700))
    ix = 206; o.append(t(ix, 56, "CONTENTS", 2.8, 700)); y = 62
    for name, pg in index:
        o.append(t(ix, y, name, 1.95)); o.append(t(SW - 14, y, str(pg), 1.95, 600, MUTED, "end")); y += 3.9
    y += 3; o.append(t(ix, y, "KEY SPECS", 2.4, 700)); y += 4.6
    for a, b in [("Shell", "12 oz cotton duck, washed navy"), ("Collar", "cotton corduroy, washed navy"), ("Zip", "YKK #5 metal, brass, separating"),
                 ("Hem / cuffs", "rib knit, navy"), ("Embroidery", "3 elements on 5 pieces, 18-thread board (≤ 12 per file)"), ("Fit", "Drum Island block (boxy, cropped)"), ("Pattern", "XS–3XL, Drum Island pattern, DXF + 1:1 plot")]:
        o.append(t(ix, y, a, 1.95, 400, MUTED)); o.append(t(ix + 22, y, b, 1.95, 600)); y += 3.8
    o.append(t(SW - 14, SH - 8, FOOT, 1.8, 400, MUTED, "end"))
    return o

def p_flats(F):
    o = header("TECHNICAL FLATS — front + back (size M)", "Line drawing to scale (0.13:1). Dashed grey = topstitching. Red dashed boxes = embroidery placement (see embroidery section).", "T2")
    b = TF.bounds_front(F); s = 0.122
    TF.K = 1.0 / (s * 6); TF.LBL = 2.6 / s
    fb = [(*EMB[e]["box"], "02") for e in ("FR", "FL")]
    fb = [(x0, y0 + F.fnd, x1, y1 + F.fnd, lab) for x0, y0, x1, y1, lab in fb]
    bx_ = EMB["BK"]["box"]; bb = [(bx_[0], bx_[1] + F.bnd, bx_[2], bx_[3] + F.bnd, "01")]
    o.append(flat_group(TF.draw_front(F, fb), b, 12, 32, s))
    o.append(flat_group(TF.draw_back(F, bb), b, 12 + (b[2]-b[0])*s + 8, 32, s))
    o.append(t(12 + (b[2]-b[0])*s/2, 32 + (b[3]-b[1])*s + 5, "FRONT", 2.3, 700, INK, "middle"))
    o.append(t(12 + (b[2]-b[0])*s*1.5 + 8, 32 + (b[3]-b[1])*s + 5, "BACK", 2.3, 700, INK, "middle"))
    X = lambda x: 12 + (x - b[0]) * s; Y = lambda y: 32 + (y - b[1]) * s
    BX = lambda x: X(x) + (b[2]-b[0])*s + 8
    cl = [(X(-90), Y(40), 1, X(-330), 36), (X(0), Y(330), 2, X(70), 124), (X(-230), Y(F.fnd + 384), 3, X(-430), Y(F.fnd + 330)),
          (X(-150), Y(F.hem_seam + 25), 4, X(-150), 124), (X(-470), Y(620), 5, X(-500), 124), (X(-200), Y(60), 6, X(-480), Y(60)),
          (BX(0), Y(150), 7, BX(150), Y(150))]
    for x, y, n, tx, ty in cl: o.append(callout(x, y, n, tx, ty))
    lx = 12; ly = 136
    notes = [("1", "Collar: washed-navy cotton corduroy, point collar, 6 mm edge topstitch; under collar same corduroy; collar band interlined."),
             ("2", "CF: YKK #5 metal separating zip, antique brass, auto-lock slider; tape enclosed, 10 mm topstitch each side."),
             ("3", "Hand-warmer welt pockets ×2: welt 1.4 × 13 cm, diagonal; bartack both ends; cotton twill pocket bag."),
             ("4", "Hem: rib knit, navy, finished height 5.5 cm; joined with 4-thread overlock, topstitched 5 mm on body."),
             ("5", "Cuffs: rib knit, navy, finished height 7.5 cm, folded double; seam inside."),
             ("6", "Shoulder: 5-thread safety stitch, pressed to back, 6 mm single-needle topstitch on back."),
             ("7", "Armholes = wrap seams: 5-thread safety stitch, pressed to the body, NO topstitch (embroidery runs to 3 mm each side). One-piece back, no yoke."),
             ("8", "Embroidery 01 back, 02 fronts (FR + FL, before welts + zip), 03 both sleeves (front + back halves): flat on the cut pieces before any seam (G pages).")]
    for i, (n, s_) in enumerate(notes):
        o.append(f'<circle cx="{f(lx + 2.3)}" cy="{f(ly + i*4.0 - 0.7)}" r="1.9" fill="#FFF" stroke="{INK}" stroke-width="0.25"/>' + t(lx + 2.3, ly + i*4.0, n, 1.7, 700, INK, "middle"))
        o.append(t(lx + 6, ly + i*4.0, s_, 1.9))
    return o

def p_details(F):
    o = header("DETAILS — collar, cuff, hem rib, welt pocket, zip, inside", "Construction details at larger scale. Values marked [proposed] are not on the fit chart — confirm with the pattern maker.", "T3")
    # A collar (front view of collar + stand), fitted into an 88 x 52 box
    col = F.collar_front(); neck = drum.curve((0, F.fnd), F.hps, 26, 14)
    stand = TF.Polygon(neck + drum.curve(F.hps, (-F.hps[0], 0), 22, 16)[1:] + [(-x, y) for x, y in neck][::-1][1:]).buffer(0)
    U = col.union(stand); cb = U.bounds; s = min(88 / (cb[2]-cb[0]), 52 / (cb[3]-cb[1])); TF.K = 1.0 / (s * 3)
    o.append(t(14, 32, "A · COLLAR", 2.5, 700))
    body = (f'<path d="{TF.poly_path(stand)}" fill="#141414" stroke="{TF.INK}" stroke-width="{f(0.5*TF.K)}"/>'
            f'<path d="{TF.poly_path(col)}" fill="{TF.CORD}" stroke="{TF.INK}" stroke-width="{f(0.7*TF.K)}"/>{TF.cord_lines(col, 90, 2.2)}'
            f'{TF.topstitch(col, 6, "3 2", 0.5, "#6A6A6A")}')
    o.append(f'<g transform="translate({f(18 - cb[0]*s)} {f(36 - cb[1]*s)}) scale({f(s)})">{body}</g>')
    ys = 36 + (cb[3]-cb[1])*s + 6
    for i, l in enumerate(["Collar height at CB (M): 10.0 ± 0.3", "Collar point (neck point → tip): 8.5 ± 0.3", "Neck opening seam-to-seam: 20.0 ± 0.5",
                           "Upper + under collar: 14-wale cotton corduroy, washed navy", "Collar band: woven fusible interlining", "Edge topstitch 6 mm, tonal Tex 60"]):
        o.append(t(14, ys + i*3.5, l, 1.8) if i < 3 else prop(14, ys + i*3.5, l, 1.8))
    # B cuff + hem rib
    bx = 112
    o.append(t(bx, 32, "B · CUFF + HEM RIB", 2.5, 700))
    o.append(f'<rect x="{bx}" y="37" width="40" height="15" fill="{TF.CUFF}" stroke="{INK}" stroke-width="0.3"/>')
    for k in range(40): o.append(f'<line x1="{f(bx + k + 0.5)}" y1="37" x2="{f(bx + k + 0.5)}" y2="52" stroke="#4A4A4A" stroke-width="0.12"/>')
    o.append(t(bx + 44, 42, "Cuff: 7.5 finished, folded double", 1.8)); o.append(prop(bx + 44, 45.5, "1×1 rib, navy, 95/5 cotton/elastane", 1.75))
    o.append(f'<rect x="{bx}" y="57" width="40" height="11" fill="{TF.RIBC}" stroke="{INK}" stroke-width="0.3"/>')
    for k in range(40): o.append(f'<line x1="{f(bx + k + 0.5)}" y1="57" x2="{f(bx + k + 0.5)}" y2="68" stroke="#4A4A4A" stroke-width="0.12"/>')
    o.append(t(bx + 44, 61, "Hem: 5.5 finished, folded double", 1.8)); o.append(prop(bx + 44, 64.5, "1×1 rib, navy (as cuffs)", 1.75))
    o.append(t(bx, 74, "Cuff opening (relaxed, ½): XS 14 → 3XL 17", 1.8)); o.append(t(bx, 77.5, "Bottom sweep (relaxed, ½): XS 52 → 3XL 70", 1.8))
    o.append(prop(bx, 81, "Rib cut length = 85% of attached edge (cuff), 90% (hem)", 1.75))
    # D zip (right column)
    zx = 214
    o.append(t(zx, 32, "D · ZIP", 2.5, 700))
    zl = {sz: round((drum.POM_CM["A"][2][i] - drum.POM_CM["K"][2][i] - 0.5)) for i, sz in enumerate(drum.SIZES)}
    zrows = [("Type", "YKK #5 metal, separating, one-way"), ("Teeth / slider", "antique brass, auto-lock"),
             ("Tape", "navy"), ("Length XS–M", "  ".join(f"{k} {v}" for k, v in list(zl.items())[:3]) + " cm"),
             ("Length L–3XL", "  ".join(f"{k} {v}" for k, v in list(zl.items())[3:]) + " cm"),
             ("Top", "zip garage, 2.5 fold of shell"), ("Setting", "tape enclosed shell/facing, 10 mm topstitch")]
    for i, (a, b_) in enumerate(zrows):
        o.append(t(zx, 37 + i*3.6, a, 1.75, 600)); o.append(prop(zx + 20, 37 + i*3.6, b_, 1.7) if i == 5 else t(zx + 20, 37 + i*3.6, b_, 1.75))
    o.append(t(zx, 37 + 7*3.6, "Length = CF length (A − K) − 0.5, rounded.", 1.7, 400, MUTED))
    # C welt pocket
    wy = 106
    o.append(t(14, wy, "C · WELT POCKET (×2)", 2.5, 700))
    o.append(f'<rect x="16" y="{wy+5}" width="70" height="8" fill="#2E3550" stroke="{INK}" stroke-width="0.35"/>'
             f'<rect x="17" y="{wy+6}" width="68" height="6" fill="none" stroke="{MUTED}" stroke-width="0.2" stroke-dasharray="1 0.6"/>'
             f'<rect x="15" y="{wy+4}" width="2" height="10" fill="{INK}"/><rect x="85" y="{wy+4}" width="2" height="10" fill="{INK}"/>')
    o.append(t(16, wy + 18, "shown 0.5:1, drawn horizontal — sewn at 56° (see T2)", 1.7, 400, MUTED))
    o.append(prop(16, wy + 21.5, "Position from the mockup: centre 23.0 from CF, 38.4 below the CF neck (M)", 1.65))
    for i, l in enumerate(["Welt 1.4 wide × 13.0 long", "Bartack both ends, 10 mm, tonal", "Edge topstitch 2 mm around welt"]):
        o.append(t(94, wy + 5 + i*3.5, l, 1.8))
    o.append(prop(94, wy + 5 + 3*3.5, "Pocket bag: cotton twill 8 oz, depth 18, French seams", 1.75))
    o.append(t(94, wy + 5 + 4*3.5, "Embroidery 01 stays 6 mm clear of the welt box", 1.8, 600, ORANGE))
    # E inside
    iy = 146
    o.append(t(14, iy, "E · INSIDE", 2.5, 700))
    ins = [("Lining", "body: 100% cotton flannel; sleeves: polyester taffeta for easy on/off", True),
           ("Facing", "shell canvas facing at CF, 6 cm wide; zip set between shell + facing", True),
           ("Hanger loop", "6 cm self-fabric loop at CB neck, under the main label", True),
           ("Embroidery backing", "cutaway trimmed to 5 mm on all five pieces; body + sleeve linings cover it", False),
           ("Labels", "main + size at CB neck facing; care/content wearer's left inside side seam, 10 above hem (T8)", False)]
    for i, (a, b_, pp) in enumerate(ins):
        o.append(t(14, iy + 6 + i*3.7, a, 1.85, 600)); o.append(prop(44, iy + 6 + i*3.7, b_, 1.8) if pp else t(44, iy + 6 + i*3.7, b_, 1.85))
    return o

def p_pom(F):
    o = header("MEASUREMENTS — points of measure + size chart (cm)", "Garment measured flat, buttoned/zipped, relaxed. Chart from the Drum Island fit block (pattern maker notes 23 Sep). Tolerance applies to all sizes.", "T4")
    b = TF.bounds_front(F); s = 0.095; TF.K = 1.0 / (s * 6)
    ox, oy = 14, 34
    o.append(flat_group(TF.draw_front(F), b, ox, oy, s))
    X = lambda x: ox + (x - b[0]) * s; Y = lambda y: oy + (y - b[1]) * s
    def mline(x1, y1, x2, y2, lab, dx=0, dy=-1.2):
        return (f'<line x1="{f(X(x1))}" y1="{f(Y(y1))}" x2="{f(X(x2))}" y2="{f(Y(y2))}" stroke="{RED}" stroke-width="0.3"/>'
                f'<circle cx="{f(X(x1))}" cy="{f(Y(y1))}" r="0.55" fill="{RED}"/><circle cx="{f(X(x2))}" cy="{f(Y(y2))}" r="0.55" fill="{RED}"/>'
                + t((X(x1) + X(x2))/2 + dx, (Y(y1) + Y(y2))/2 + dy, lab, 2.1, 700, RED, "middle"))
    o.append(mline(F.hps[0] + 2, 0, F.hps[0] + 2, F.hem_edge, "A", 3, 0))
    o.append(mline(-F.ua[0], F.ua[1] + 4, F.ua[0], F.ua[1] + 4, "B"))
    o.append(mline(-F.sp[0], F.sp[1], F.sp[0], F.sp[1], "C", 14, -1.2))
    o.append(mline(-F.sweep2 + 4, F.hem_edge - 2, F.sweep2 - 4, F.hem_edge - 2, "D", 0, 3.2))
    o.append(mline(F.sp[0], F.sp[1], F.ua[0], F.ua[1], "E", 3, 0))
    sp = np.array(F.sp); cu = np.array(F.cuff_out)
    o.append(mline(-sp[0], sp[1], -cu[0], cu[1], "G", -3, 0))
    ci = np.array(F.cuff_in); o.append(mline(-cu[0], cu[1] - 2, -ci[0], ci[1] - 2, "H", -3, 3))
    ua = np.array(F.ua); cin = np.array(F.cuff_seam_in); bic0 = ua + (cin - ua) / np.linalg.norm(cin - ua) * 25
    out0 = np.array(F.sp); u = np.array(F.sdir)
    foot = out0 + u * np.dot(bic0 - out0, u)
    o.append(mline(bic0[0], bic0[1], foot[0], foot[1], "F", 3, 0))
    o.append(mline(-F.hps[0], -3, F.hps[0], -3, "J", 0, -1.2))
    o.append(mline(-4, 0, -4, F.fnd, "K", -4, 2))
    # chart
    tx = 132; ty = 34
    cols = ["POM", "Description", "How to measure", "Tol ±"] + drum.SIZES
    cx = [tx, tx + 6, tx + 30, tx + 70, tx + 81, tx + 90, tx + 99, tx + 108, tx + 117, tx + 126, tx + 135]
    for x, h in zip(cx, cols): o.append(t(x, ty, h, 1.8, 700, MUTED if h != "M" else INK))
    rh = 5.0
    for i, (k, (name, how, vals, tol)) in enumerate(drum.POM_CM.items()):
        y = ty + 5 + i*rh
        if i % 2 == 0: o.append(f'<rect x="{tx-1}" y="{f(y-3.3)}" width="{SW - tx - 11}" height="{rh}" fill="#F5F2EC"/>')
        o.append(f'<rect x="{f(cx[6]-1)}" y="{f(y-3.3)}" width="9" height="{rh}" fill="#FFF3D6"/>')
        o.append(t(cx[0], y, k, 1.9, 700, RED)); o.append(t(cx[1], y, name, 1.85, 600)); o.append(t(cx[2], y, how, 1.6, 400, MUTED))
        o.append(t(cx[3], y, f"{tol:g}", 1.8))
        for j, v in enumerate(vals): o.append(t(cx[4 + j], y, f"{v:g}", 1.85, 700 if j == 2 else 400))
    y = ty + 5 + len(drum.POM_CM)*rh + 3
    o.append(t(tx, y, "Shaded M = base size, sample size. J, K, L, M, N, P are fixed across sizes (per fit chart).", 1.75, 400, MUTED))
    o.append(prop(tx, y + 3.6, "Rib heights (hem 5.5, cuff 7.5) and shoulder drop (4.5) are not on the chart", 1.75))
    o.append(t(tx, y + 7.2, "Body length A includes the hem rib. Chest B measured 2.5 below armhole.", 1.75, 400, MUTED))
    return o

def p_grade():
    o = header("GRADING — increments + embroidery grading", "Body grades from the fit chart. Embroidery is graded in three art sizes so every element keeps its seam clearances on every size.", "T5")
    tx = 14; ty = 32
    o.append(t(tx, ty, "A · GRADE INCREMENTS (cm, size to size)", 2.4, 700))
    cols = ["POM", "Description"] + [f"{a}→{b}" for a, b in zip(drum.SIZES, drum.SIZES[1:])]
    cx = [tx, tx + 7] + [tx + 34 + 13*i for i in range(6)]
    for x, h in zip(cx, cols): o.append(t(x, ty + 5, h, 1.75, 700, MUTED))
    for i, (k, (name, how, vals, tol)) in enumerate([kv for kv in drum.POM_CM.items() if len(set(kv[1][2])) > 1]):
        y = ty + 9.5 + i*4.2
        if i % 2 == 0: o.append(f'<rect x="{tx-1}" y="{f(y-3)}" width="113" height="4.2" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, k, 1.85, 700, RED)); o.append(t(cx[1], y, name, 1.8))
        for j in range(6): o.append(t(cx[2 + j], y, f"{vals[j+1] - vals[j]:+.1f}", 1.8))
    o.append(t(tx, ty + 9.5 + 8*4.2 + 2, "Increments are uneven by design (fit chart) — grade nests from the chart, not a fixed rule.", 1.75, 400, MUTED))
    gx = 136
    o.append(t(gx, ty, "B · EMBROIDERY GRADING (01 back, 02 fronts, 03 sleeves)", 2.4, 700))
    o.append(t(gx, ty + 4.5, "3 art grades; body pieces scaled about CB / CF on the hem-rib seam, sleeves about the cuff-seam centre.", 1.65, 400, MUTED))
    o.append(t(gx, ty + 7.8, "One stitch file per size per piece: art re-clipped to that size's own keep-outs (pattern T13).", 1.65, 400, MUTED))
    hd = ["Size", "Art", "Scale"] + [f"{P} box" for P in cfcore.PIECES]
    hx = [gx, gx + 9, gx + 16] + [gx + 28 + 28*j for j in range(5)]
    for x, h in zip(hx, hd): o.append(t(x, ty + 13, h, 1.65, 700, MUTED))
    for i, sz in enumerate(drum.SIZES):
        g, sc = GRADE[sz]; y = ty + 17.5 + i*4.4
        if i % 2 == 0: o.append(f'<rect x="{gx-1}" y="{f(y-3.1)}" width="{SW - gx - 11}" height="4.4" fill="#F5F2EC"/>')
        o.append(t(hx[0], y, sz, 1.85, 700)); o.append(t(hx[1], y, g, 1.85, 700, RED)); o.append(t(hx[2], y, f"{sc*100:.0f}%", 1.8))
        for j, P in enumerate(cfcore.PIECES):
            b = art_box(sz, P); o.append(t(hx[3 + j], y, f"{b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}", 1.65))
    y = ty + 17.5 + 7*4.4 + 2
    o.append(t(gx, y, "Art boxes in mm, measured from each size's own art (after keep-out clipping).", 1.65, 400, MUTED))
    o.append(t(gx, y + 3.3, "The art is composed ~25 mm past the M side seams, so bigger sizes keep art up to their keep-outs.", 1.65, 400, MUTED))
    o.append(t(gx, y + 8, "C · PLACEMENT REFERENCE PER SIZE", 2.4, 700))
    pl = ["Per-size stitch files are in each size's pattern coordinates: origin = centre of the design (DXF layer 8 cross,",
          "   layer 13 point; split files' needle starts too — G6). Zip edge 15 mm from CF; armholes 3 mm (wrap).",
          "Hoop each cut piece flat; mark CB / CF / sleeve centre line, split lines and welt box (drills) before hooping.",
          "Keep-outs on every size: CF 15 · side, shoulder, underarm 15 · hem 10 · cuff 10 · welt 6 · collar 6 · armhole 3 (T13)."]
    for i, l in enumerate(pl): o.append(t(gx, y + 12.5 + i*3.6, l, 1.6))
    return o

def thread_qty():
    """top thread per jacket from the size-M DSTs: sewn length x 1.4 (take-up), in metres + 5,000 m cones"""
    import pyembroidery as pe, math
    cur = json.load(open("dst_current.json")); L = 0.0
    for P in cfcore.PIECES:
        p = pe.read(cur[P]["file"] + ".dst"); prev = None
        for x, y, c in p.stitches:
            k = c & pe.COMMAND_MASK
            if k == pe.STITCH:
                if prev: L += math.hypot(x - prev[0], y - prev[1]) / 10000.0
                prev = (x, y)
            else: prev = None
    m = L * 1.4
    return f"≈ {m:,.0f} m top + {m*0.45:,.0f} m bobbin (≈ {5000/m:.0f} jackets / 5,000 m cone avg)"

def p_bom():
    o = header("BILL OF MATERIALS", "Per jacket, size M. Fabric consumption = pattern piece area ÷ (150 cm width × 80 % marker efficiency) — replace with the factory's marker. Threads: G3.", "T6")
    import gtp_pattern as GP
    C = GP.consumption("M")
    hd = ["#", "Component", "Material / spec", "Colour", "Placement", "Supplier", "Qty (M)"]
    cx = [12, 18, 48, 124, 168, 222, 258]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.8, 700, MUTED))
    rows = [
        ("Shell", "12 oz (407 g/m²) 100% cotton duck canvas, 150 cm, washed", "washed navy ≈ #252B3B", "body, sleeves, welts, facing", "TBC", f"{C['Shell']:.2f} m", False),
        ("Collar", "14-wale cotton corduroy, 8 oz", "washed navy", "upper + under collar", "TBC", f"{C['Collar']:.2f} m", True),
        ("Hem rib", "1×1 rib, 95/5 cotton/elastane, 400 g/m²", "navy", "hem band", "TBC", f"{C['Hem rib']/1000:.2f} m (1 × {C['Hem rib']/10:.0f} cm cut)", True),
        ("Cuff rib", "1×1 rib, 95/5 cotton/elastane, 400 g/m²", "navy", "cuffs ×2", "TBC", f"{C['Cuff rib']/1000:.2f} m", True),
        ("Body lining", "100% cotton flannel, 180 g/m²", "navy / red plaid (mockup)", "body", "TBC", f"{C['Body lining']:.2f} m", True),
        ("Sleeve lining", "polyester taffeta 210T", "navy", "sleeves", "TBC", f"{C['Sleeve lining']:.2f} m", True),
        ("Pocket bag", "8 oz cotton twill", "navy", "welt pockets ×2", "TBC", f"{C['Pocket bag']:.2f} m", True),
        ("Interlining", "woven fusible, 60 g/m²", "charcoal", "top collar, facings, welts", "TBC", f"{C['Interlining']:.2f} m", True),
        ("Zip", "YKK #5 metal separating, auto-lock, one-way", "antique brass teeth, navy tape", "CF", "YKK", "1 × 56 cm (M)", False),
        ("Thread — seams", "Coats Epic 120 (Tex 27) corespun poly/cotton", "tonal navy", "all seams + overlock", "Coats", "~ 450 m", True),
        ("Thread — topstitch", "Coats Gral 40 (Tex 60) poly", "tonal navy", "topstitch, bartacks", "Coats", "~ 120 m", True),
        ("Embroidery thread", "Madeira Polyneon 40 (18-colour board, see G3)", "per embroidery spec", "01 back, 02 fronts, 03 sleeves", "Madeira", thread_qty(), False),
        ("Embroidery backing", "2.5 oz cutaway", "black / charcoal", "behind BK, FR, FL, SR, SL", "TBC", "5 pieces (+ per hooping)", False),
        ("Main label", "woven damask, HAKI logo, 7 × 2 cm, folded", "black / cream", "CB neck facing", "TBC", "1", True),
        ("Size label", "woven, 2 × 1.5 cm", "black / cream", "under main label", "TBC", "1", True),
        ("Care / content label", "printed satin, multi-page", "white", "wearer's left inside side seam", "TBC", "1", True),
        ("Hangtag + string", "350 gsm board, cotton string, brass-tone barb", "cream / black", "through main label loop", "TBC", "1", True),
        ("Polybag", "LDPE 40 µm, self-seal, suffocation warning", "clear", "packing", "TBC", "1", True),
    ]
    for i, (comp, mat, colr, plc, sup, qty, pp) in enumerate(rows):
        y = 35.5 + i*4.55
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3.1)}" width="{SW-22}" height="4.55" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, f"{i+1:02d}", 1.75, 700)); o.append(t(cx[1], y, comp, 1.85, 600))
        o.append(t(cx[2], y, mat, 1.75, 600 if pp else 400, PROP if pp else INK))
        o.append(t(cx[3], y, colr, 1.7)); o.append(t(cx[4], y, plc, 1.7)); o.append(t(cx[5], y, sup, 1.7, 400, MUTED)); o.append(t(cx[6], y, qty, 1.75, 600))
    y = 35.5 + len(rows)*4.55 + 2
    o.append(t(12, y, "Amber rows = proposed by Haki tech design, not yet specified — confirm material, weight and supplier. Shell, collar, rib, zip and plaid lining read from the mockup; fibres, weights and suppliers proposed.", 1.75, 600, PROP))
    o.append(t(12, y + 3.5, "Shell fabric: pre-shrunk / garment-wash tested before embroidery (dense embroidery shrinks panels 1.5–2.5%).", 1.75, 400, MUTED))
    return o

def p_construction():
    o = header("CONSTRUCTION — seams, stitches, assembly order", "SPI = stitches per inch. Seam allowance (SA) in cm. 'Topstitch' = tonal Tex 60 unless noted.", "T7")
    hd = ["Seam / operation", "Stitch type", "SPI", "SA", "Finish / topstitch"]
    cx = [12, 62, 104, 114, 124]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.8, 700, MUTED))
    rows = [("Shoulder", "5-thread safety stitch (ISO 516)", "11", "1.0", "pressed to back; 6 mm single-needle topstitch on back"),
            ("Armhole (wrap seam)", "5-thread safety stitch", "11", "1.0", "pressed to body, NO topstitch: embroidery to 3 mm each side [proposed]"),
            ("Sleeve cap (wrap seam)", "ease 12 mm spread evenly", "—", "—", "match art at the seam; no pressing on the embroidery face"),
            ("Side seam + underarm", "5-thread safety stitch, one pass", "11", "1.0", "pressed to back, no topstitch"),
            ("CF zip", "lockstitch (ISO 301)", "10", "1.0", "tape enclosed shell + facing; 10 mm topstitch"),
            ("Collar edge", "lockstitch, turned + pressed", "12", "0.6", "6 mm edge topstitch"),
            ("Collar to neck", "lockstitch, collar sandwiched by facing", "11", "1.0", "stitch-in-ditch at back neck"),
            ("Welt pockets", "lockstitch, welt + facing", "11", "—", "2 mm edge topstitch; 10 mm bartack ×2 each end"),
            ("Pocket bag", "French seam", "12", "0.5", "—"),
            ("Hem rib", "4-thread overlock, stretched to body", "11", "0.8", "5 mm topstitch on body"),
            ("Cuff rib", "4-thread overlock, stretched to sleeve", "11", "0.8", "seam inside, no topstitch"),
            ("Lining seams", "4-thread overlock", "12", "1.0", "lining bagged to facing + rib seams"),
            ("Bartacks", "bartack 28 stitches", "—", "—", "welt ends, hanger loop"),
            ("Embroidery", "multi-head embroidery", "—", "—", "flat on cut panels, BEFORE any seam (see embroidery section)")]
    for i, r in enumerate(rows):
        y = 35.5 + i*4.4
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3)}" width="185" height="4.4" fill="#F5F2EC"/>')
        for j, v in enumerate(r): o.append(t(cx[j], y, v, 1.8, 600 if j == 0 else 400, ORANGE if "wrap" in r[0] and j == 4 else INK))
    o.append(prop(12, 35.5 + len(rows)*4.4 + 2, "Seam types + SPI are a standard workwear proposal — confirm against the factory's capability", 1.8))
    ax = 204
    o.append(t(ax, 31, "ASSEMBLY ORDER", 2.4, 700))
    steps = ["Cut shell; mark welts, embroidery placement, notches.",
             "Embroider 01 back, 02 fronts, 03 sleeves flat.",
             "Trim backing to 5 mm; press from the wrong side.",
             "Make welt pockets on both fronts; bartack.",
             "Join shoulders; topstitch.",
             "Set sleeves (no armhole topstitch).",
             "Close side + underarm seams.",
             "Make collar; attach with facing; topstitch.",
             "Set CF zip between shell + facing; zip garage.",
             "Attach cuff ribs; attach hem rib; topstitch.",
             "Bag lining; hanger loop; labels.",
             "Final press (no iron on embroidery face).",
             "QC: measure to T4, embroidery to placement ±2.",
             "Hangtag, fold, polybag (T8)."]
    for i, s_ in enumerate(steps): o.append(t(ax, 36 + i*3.9, f"{i+1:02d}  {s_}", 1.8))
    return o

def p_labels():
    o = header("LABELS, TRIM PLACEMENT + PACKAGING", "Label artwork supplied separately by Haki. Positions measured on the finished garment.", "T8")
    rows = [("Main label", "CB neck facing, 1.0 below the collar seam, centred; sewn on 2 short ends"),
            ("Size label", "folded, centred under the main label, caught in the bottom seam of the main label"),
            ("Hanger loop", "6 cm self-fabric loop at CB neck, above the main label"),
            ("Care / content", "wearer's left inside side seam, 10 cm above the hem-rib seam, caught in the lining seam"),
            ("Hangtag", "through the main-label hanger loop with cotton string + barb; never through the embroidery")]
    for i, (a, b) in enumerate(rows):
        o.append(t(14, 34 + i*4.2, a, 1.9, 600)); o.append(t(46, 34 + i*4.2, b, 1.9))
    o.append(t(14, 60, "CARE / CONTENT LABEL TEXT", 2.4, 700))
    care = ["Shell: 100% cotton · Collar: 100% cotton · Rib: 95% cotton 5% elastane · Lining: 100% cotton / sleeve lining 100% polyester",
            f"Embroidery: 100% polyester · Made in [country] · Style {STYLE} · Size [ ]",
            "Machine wash cold, inside out, gentle · Do not bleach · Tumble dry low · Cool iron on reverse, never on embroidery · Do not dry clean",
            "Care symbols (ISO 3758): wash 30 °C gentle · no bleach · tumble low · iron 1 dot · no dry clean"]
    for i, c in enumerate(care): o.append(prop(14, 65 + i*3.7, c, 1.8) if i < 2 else t(14, 65 + i*3.7, c, 1.85))
    o.append(t(14, 86, "PACKAGING", 2.4, 700))
    pk = ["Fold: zip closed, sleeves folded back across the body, folded once at the waist — front embroidery facing the tissue.",
          "Acid-free tissue sheet over the front embroidery and in the fold to stop thread abrasion.",
          "Polybag: LDPE 40 µm self-seal, printed suffocation warning; size sticker + barcode bottom right.",
          "Carton: 5-ply export carton, max 12 units, size-ratio packing per PO; carton mark per Haki shipping guide."]
    for i, p_ in enumerate(pk): o.append(t(14, 91 + i*3.8, p_, 1.85))
    o.append(prop(14, 91 + 4*3.8, "Fold dimensions ≈ 35 × 45 cm; tissue + hangtag spec", 1.8))
    o.append(t(14, 115, "QC CHECKPOINTS", 2.4, 700))
    qc = ["Measurements to T4 tolerance on 2 pcs/size/colour per lot.", "Embroidery: placement ±2 mm, rotation ±3°, no loose jumps, backing trimmed, no puckering > 1 mm.",
          "Zip runs smoothly full length, auto-lock holds; welt corners clean, bartacks secure.", "No needle holes or stitch marks on the corduroy collar; rib recovery after 10 stretches."]
    for i, q in enumerate(qc): o.append(t(14, 120 + i*3.8, q, 1.85))
    return o

def p_colourway():
    o = header("COLOURWAY + ARTWORK — washed navy, castle falls panorama", "Garment colours and the embroidery in place (stitch preview, size M). Embroidery detail: following section.", "T9")
    fr = Image.open("cover_front.png"); bk = Image.open("cover_back.png")
    tag, h = img_tag(fr, 14, 30, 100); o.append(tag); tag, h2 = img_tag(bk, 120, 30, 100); o.append(tag)
    cx = 228; o.append(t(cx, 33, "GARMENT COLOURS", 2.3, 700))
    cols = [(cfcore.FABRIC, "Shell — washed navy duck"), ("#232B3A", "Collar — washed-navy corduroy"), ("#252D3B", "Hem + cuff rib — navy"),
            ("#A07C3C", "Zip — antique brass, navy tape")]
    for i, (h_, n) in enumerate(cols):
        o.append(f'<rect x="{cx}" y="{f(37 + i*5.5)}" width="6" height="4" rx="0.5" fill="{h_}" stroke="#BBB" stroke-width="0.2"/>')
        o.append(t(cx + 8, 40 + i*5.5, n, 1.85))
    o.append(t(cx, 66, "Lab-dip / strike-off approval", 1.9, 700))
    o.append(t(cx, 69.5, "required for shell, collar and both ribs.", 1.85))
    o.append(t(cx, 76, "Embroidery: 18-thread board,", 1.9, 700)); o.append(t(cx, 79.5, "Madeira Polyneon (G3).", 1.85))
    o.append(prop(cx, 86, "Shell piece-dyed + washed BEFORE", 1.75)); o.append(t(cx, 89.5, "embroidery (garment dye would", 1.75, 600, PROP)); o.append(t(cx, 93, "shift thread shades) — T10 Q1", 1.75, 600, PROP))
    return o

def p_questions():
    o = header("OPEN QUESTIONS — garment", "Everything marked [proposed — confirm] in this pack, in one place. Embroidery questions are on G4.", "T10")
    qs = ["1. IP: the mockup's castle-on-the-falls inside a giant arching tree reads as One Piece's Wano. Built an original castle + opened tree ring (02). Approve, or confirm a licence.",
          "2. Collar vs hood: the mockup shows a navy corduroy point collar (built); the intake note mentioned a hood. Confirm the collar (or send the hood files).",
          "3. Shell: 12 oz duck washed navy — piece-dyed + washed before embroidery (assumed) or garment-dyed after? Lab-dip / Pantone reference.",
          "4. Collar: 14-wale corduroy 8 oz, washed navy; rib 95/5 cotton/elastane navy, hem 5.5 / cuff 7.5 (not on the fit chart).",
          "5. Lining: navy / red plaid cotton flannel body (as seen at the neck in the mockup) + navy taffeta sleeves proposed.",
          "6. Armholes as wrap seams: art runs to 3 mm each side, armhole sewn without topstitch (T7). OK for durability?",
          "7. Welt pockets: Drum Island welt 1.4 × 13 cm at the mockup position (23.0 from CF, 38.4 below the neck, 56°). Confirm.",
          "8. Pattern (T11–T13) is the Drum Island first pattern: shoulder slope 4.5, cap ease 1.2, facings, rib heights proposed — sample + fit M first.",
          "9. Seam types + SPI (T7) are a standard proposal — factory to confirm capability (5-thread safety stitch, bartack).",
          "10. Embroidery grading: A 92% (XS–S) · B 100% (M–XL) · C 108% (XXL–3XL), one file per size per piece. OK?",
          "11. Frame: on 360 × 360 the jacket needs 16 hoopings (back 4, fronts 2 + 2, sleeves 4 + 4). Which frames does the factory have (F1)?",
          "12. Labels + packaging artwork, country of origin, care-symbol set, carton marks; zip garage + auto-lock slider.",
          "13. Embroidered sleeves are stiff + heavy: confirm the taffeta sleeve lining and a hand-feel check on the strike-off."]
    for i, q in enumerate(qs): o.append(t(14, 34 + i*4.6, q, 2.0))
    return o

PAGES = ["T1 Cover + contents", "T2 Technical flats", "T3 Construction details", "T4 Measurements + size chart",
         "T5 Grading + embroidery grading", "T6 Bill of materials", "T7 Seams, stitches, assembly", "T8 Labels, packaging, QC",
         "T9 Colourway + artwork", "T10 Open questions — garment", "T11 Pattern — pieces + cut list", "T12 Pattern — grade nests + measurement check",
         "T13 Pattern — embroidery placement per size", "T14 Inside view", "T15 Operations + time estimate", "T16 Revision log + sample tracker"]

def build(emb_pdf, emb_pages, out_pdf):
    F = TF.Flat("M")
    index = [(n, i + 1) for i, n in enumerate(PAGES)] + [("EMBROIDERY SECTION (G1–G6, 01–03, F1)", len(PAGES) + 1)] + emb_pages
    import gtp_pattern as GP
    pages = [p_cover(index), p_flats(F), p_details(F), p_pom(F), p_grade(), p_bom(), p_construction(), p_labels(), p_colourway(), p_questions(),
             GP.p_pattern_pieces(), GP.p_pattern_grade(), GP.p_pattern_emb(), GP.p_inside(), GP.p_operations(), GP.p_revisions()]
    w = PdfWriter()
    for i, pg in enumerate(pages, 1):
        svg = doc(pg); cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"T{i}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"prev_T{i}.png", output_width=2400)
        w.append(PdfReader(f"T{i}.pdf"))
    if emb_pdf: w.append(PdfReader(emb_pdf))
    w.write(out_pdf)
    return len(pages)
