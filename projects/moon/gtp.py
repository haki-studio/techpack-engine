"""Garment tech pack pages — Drum Island jacket, MOON colourway (washed navy, full moon + power lines + clouds)."""
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
import moonpal, moonpattern
import drum, techflat as TF
import specbase as SB
from specbase import img_tag
import labelsheet as LS

REV = "Rev C"; DATE = "19 Oct 2026"; STYLE = "HK-JK-DRUM-MOON"; NAME = "Drum Island Jacket — Moon"
FOOT = f"HAKI STUDIOS · {NAME} · {STYLE} · GARMENT TECH PACK · {REV} · {DATE}"
SHELL_MAT = "12 oz (407 g/m²) 100% cotton duck canvas, 150 cm"          # shell composition as on the BOM; picks the Haki care label (LESSONS D7)
PROP = "#8A5A00"        # colour for 'proposed — confirm' text

def header(title, sub, page):
    SB.FOOT = FOOT
    return SB.header(title, sub, page)

def prop(x, y, s, size=1.85):
    return t(x, y, s + "  [proposed — confirm]", size, 600, PROP)

def flat_group(svgbody, b, ox, oy, s, k=None):
    return f'<g transform="translate({f(ox - b[0]*s)} {f(oy - b[1]*s)}) scale({f(s)})">{svgbody}</g>'

# ---------------------------------------------------------------- embroidery grading
import emb_place as EPL
_PL = EPL.place("M")[0]
EMB = {k: {"box": _PL[k][1].bounds} for k in ("back", "box", "02R", "02L", "03L", "03R", "04R", "04L")}   # size-M art boxes, pattern coords
GRADE = {k: (v[0], v[1]) for k, v in EPL.GRADE.items()}

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
    for a, b in [("Shell", "12 oz cotton duck, washed navy"), ("Collar", "cotton corduroy, navy-black"), ("Zip", "YKK #5 metal, brass, separating"),
                 ("Hem / cuffs", "rib knit, navy-black"), ("Embroidery", "4 elements (+ 01b), 7 pieces, ≤ 12 threads per file"), ("Fit", "Drum Island block (boxy, cropped)"), ("Pattern", "XS–3XL first pattern, DXF + 1:1 plot")]:
        o.append(t(ix, y, a, 1.95, 400, MUTED)); o.append(t(ix + 22, y, b, 1.95, 600)); y += 3.8
    o.append(t(SW - 14, SH - 8, FOOT, 1.8, 400, MUTED, "end"))
    return o

def p_flats(F):
    o = header("TECHNICAL FLATS — front + back (size M)", "Line drawing to scale (0.13:1). Dashed grey = topstitching. Red dashed boxes = embroidery placement (04 sleeves: see T13 + element 04); LF = licensed-figure placeholder.", "T2")
    b = TF.bounds_front(F); s = 0.122
    TF.K = 1.0 / (s * 6); TF.LBL = 2.6 / s
    fb = [(*EMB[e]["box"], e) for e in ("02R", "02L", "03L", "03R")]
    fb = [(x0, y0 + F.fnd, x1, y1 + F.fnd, lab) for x0, y0, x1, y1, lab in fb]
    bb = [(EMB["back"]["box"][0], EMB["back"]["box"][1] + F.bnd, EMB["back"]["box"][2], EMB["back"]["box"][3] + F.bnd, "01"),
          (EMB["box"]["box"][0], EMB["box"]["box"][1] + F.bnd, EMB["box"]["box"][2], EMB["box"]["box"][3] + F.bnd, "LF")]
    o.append(flat_group(TF.draw_front(F, fb), b, 12, 32, s))
    o.append(flat_group(TF.draw_back(F, bb), b, 12 + (b[2]-b[0])*s + 8, 32, s))
    o.append(t(12 + (b[2]-b[0])*s/2, 32 + (b[3]-b[1])*s + 5, "FRONT", 2.3, 700, INK, "middle"))
    o.append(t(12 + (b[2]-b[0])*s*1.5 + 8, 32 + (b[3]-b[1])*s + 5, "BACK", 2.3, 700, INK, "middle"))
    X = lambda x: 12 + (x - b[0]) * s; Y = lambda y: 32 + (y - b[1]) * s
    BX = lambda x: X(x) + (b[2]-b[0])*s + 8
    cl = [(X(-90), Y(40), 1, X(-330), 36), (X(0), Y(330), 2, X(70), 124), (X(-175), Y(F.fnd + 365), 3, X(-430), Y(F.fnd + 330)),
          (X(-150), Y(F.hem_seam + 25), 4, X(-150), 124), (X(-470), Y(620), 5, X(-500), 124), (X(-200), Y(60), 6, X(-480), Y(60)),
          (BX(0), Y(150), 7, BX(150), Y(150)), (BX(275), Y(180), 8, BX(450), Y(120))]
    for x, y, n, tx, ty in cl: o.append(callout(x, y, n, tx, ty))
    lx = 12; ly = 136
    notes = [("1", "Collar: navy-black cotton corduroy, point collar, 6 mm edge topstitch; under collar same corduroy; collar band interlined."),
             ("2", "CF: YKK #5 metal separating zip, antique brass, auto-lock slider; tape enclosed, 10 mm topstitch each side."),
             ("3", "Hand-warmer welt pockets ×2: welt 1.4 × 13 cm, diagonal; bartack both ends; cotton twill pocket bag."),
             ("4", "Hem: rib knit, navy-black, finished height 5.5 cm; joined with 4-thread overlock, topstitched 5 mm on body."),
             ("5", "Cuffs: rib knit, navy-black, finished height 7.5 cm, folded double; seam inside."),
             ("6", "Shoulder: 5-thread safety stitch, pressed to back, 6 mm single-needle topstitch on back."),
             ("7", "Back: one-piece panel. Embroidery 01 flat on the cut panel; LF = licensed-figure placeholder box (factory insert)."),
             ("8", "Side seams: 01 + 03 wires wrap back↔front; side seams NOT topstitched; match the wire notches (T13).")]
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
    body = (f'<path d="{TF.poly_path(stand)}" fill="#161A26" stroke="{TF.INK}" stroke-width="{f(0.5*TF.K)}"/>'
            f'<path d="{TF.poly_path(col)}" fill="{TF.CORD}" stroke="{TF.INK}" stroke-width="{f(0.7*TF.K)}"/>{TF.cord_lines(col, 90, 2.2)}'
            f'{TF.topstitch(col, 6, "3 2", 0.5, "#C9A882")}')
    o.append(f'<g transform="translate({f(18 - cb[0]*s)} {f(36 - cb[1]*s)}) scale({f(s)})">{body}</g>')
    ys = 36 + (cb[3]-cb[1])*s + 6
    for i, l in enumerate(["Collar height at CB (M): 10.0 ± 0.3", "Collar point (neck point → tip): 8.5 ± 0.3", "Neck opening seam-to-seam: 20.0 ± 0.5",
                           "Upper + under collar: 14-wale cotton corduroy, navy-black", "Collar band: woven fusible interlining", "Edge topstitch 6 mm, tonal Tex 60"]):
        o.append(t(14, ys + i*3.5, l, 1.8) if i < 3 else prop(14, ys + i*3.5, l, 1.8))
    # B cuff + hem rib
    bx = 112
    o.append(t(bx, 32, "B · CUFF + HEM RIB", 2.5, 700))
    o.append(f'<rect x="{bx}" y="37" width="40" height="15" fill="{TF.CUFF}" stroke="{INK}" stroke-width="0.3"/>')
    for k in range(40): o.append(f'<line x1="{f(bx + k + 0.5)}" y1="37" x2="{f(bx + k + 0.5)}" y2="52" stroke="#3E4558" stroke-width="0.12"/>')
    o.append(t(bx + 44, 42, "Cuff: 7.5 finished, folded double", 1.8)); o.append(prop(bx + 44, 45.5, "1×1 rib navy-black, 95/5", 1.75))
    o.append(f'<rect x="{bx}" y="57" width="40" height="11" fill="{TF.RIBC}" stroke="{INK}" stroke-width="0.3"/>')
    for k in range(40): o.append(f'<line x1="{f(bx + k + 0.5)}" y1="57" x2="{f(bx + k + 0.5)}" y2="68" stroke="#3E4558" stroke-width="0.12"/>')
    o.append(t(bx + 44, 61, "Hem: 5.5 finished, folded double", 1.8)); o.append(prop(bx + 44, 64.5, "1×1 rib navy-black", 1.75))
    o.append(t(bx, 74, "Cuff opening (relaxed, ½): XS 14 → 3XL 17", 1.8)); o.append(t(bx, 77.5, "Bottom sweep (relaxed, ½): XS 52 → 3XL 70", 1.8))
    o.append(prop(bx, 81, "Rib cut length = 85% of attached edge (cuff), 90% (hem)", 1.75))
    # D zip (right column)
    zx = 214
    o.append(t(zx, 32, "D · ZIP", 2.5, 700))
    zl = {sz: round((drum.POM_CM["A"][2][i] - drum.POM_CM["K"][2][i] - 0.5)) for i, sz in enumerate(drum.SIZES)}
    zrows = [("Type", "YKK #5 metal, separating, one-way"), ("Teeth / slider", "antique brass, auto-lock"),
             ("Tape", "navy to match shell"), ("Length XS–M", "  ".join(f"{k} {v}" for k, v in list(zl.items())[:3]) + " cm"),
             ("Length L–3XL", "  ".join(f"{k} {v}" for k, v in list(zl.items())[3:]) + " cm"),
             ("Top", "zip garage, 2.5 fold of shell"), ("Setting", "tape enclosed shell/facing, 10 mm topstitch")]
    for i, (a, b_) in enumerate(zrows):
        o.append(t(zx, 37 + i*3.6, a, 1.75, 600)); o.append(prop(zx + 20, 37 + i*3.6, b_, 1.7) if i == 5 else t(zx + 20, 37 + i*3.6, b_, 1.75))
    o.append(t(zx, 37 + 7*3.6, "Length = CF length (A − K) − 0.5, rounded.", 1.7, 400, MUTED))
    # C welt pocket
    wy = 106
    o.append(t(14, wy, "C · WELT POCKET (×2)", 2.5, 700))
    o.append(f'<rect x="16" y="{wy+5}" width="70" height="8" fill="#2E3854" stroke="{INK}" stroke-width="0.35"/>'
             f'<rect x="17" y="{wy+6}" width="68" height="6" fill="none" stroke="{MUTED}" stroke-width="0.2" stroke-dasharray="1 0.6"/>'
             f'<rect x="15" y="{wy+4}" width="2" height="10" fill="{INK}"/><rect x="85" y="{wy+4}" width="2" height="10" fill="{INK}"/>')
    o.append(t(16, wy + 18, "shown 0.5:1, drawn horizontal — sewn at 38° (see T2)", 1.7, 400, MUTED))
    for i, l in enumerate(["Welt 1.4 wide × 13.0 long", "Bartack both ends, 10 mm, tonal", "Edge topstitch 2 mm around welt"]):
        o.append(t(94, wy + 5 + i*3.5, l, 1.8))
    o.append(prop(94, wy + 5 + 3*3.5, "Pocket bag: cotton twill 8 oz, depth 18, French seams", 1.75))
    o.append(t(94, wy + 5 + 4*3.5, "Embroidery 02/03 (wires + pole) stay 6 mm clear of the welt box", 1.8, 600, ORANGE))
    # E inside
    iy = 146
    o.append(t(14, iy, "E · INSIDE", 2.5, 700))
    ins = [("Lining", "body: 100% cotton flannel; sleeves: polyester taffeta for easy on/off", True),
           ("Facing", "shell canvas facing at CF, 6 cm wide; zip set between shell + facing", True),
           ("Hanger loop", "6 cm self-fabric loop at CB neck, under the main label", True),
           ("Embroidery backing", "cutaway trimmed to 5 mm; lining covers the back of 01-04 (sleeve lining covers 04)", False),
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
    o.append(t(gx, ty, "B · EMBROIDERY GRADING", 2.4, 700))
    o.append(t(gx, ty + 4.5, "3 art sizes: A 92 % (XS–S), B 100 % (M–XL), C 108 % (XXL–3XL). Motifs scale; wires re-run per size.", 1.75, 400, MUTED))
    o.append(t(gx, ty + 7.8, "Digitizer re-densities at scale (don't scale stitches); stitch angles + thread order unchanged.", 1.75, 400, MUTED))
    hd = ["Size", "Art", "Scale", "01 back", "02R", "02L", "03L", "04R", "04L"]
    hx = [gx, gx + 9, gx + 16, gx + 26, gx + 47, gx + 67, gx + 87, gx + 107, gx + 129]
    for x, h in zip(hx, hd): o.append(t(x, ty + 13, h, 1.75, 700, MUTED))
    for i, sz in enumerate(drum.SIZES):
        g, sc = GRADE[sz]; y = ty + 17.5 + i*4.4
        pl = EPL.place(sz)[0]
        if i % 2 == 0: o.append(f'<rect x="{gx-1}" y="{f(y-3.1)}" width="{SW - gx - 11}" height="4.4" fill="#F5F2EC"/>')
        o.append(t(hx[0], y, sz, 1.9, 700)); o.append(t(hx[1], y, g, 1.9, 700, RED)); o.append(t(hx[2], y, f"{sc*100:.0f}%", 1.85))
        for j, e in enumerate(("back", "02R", "02L", "03L", "04R", "04L")):
            bx = pl[e][1].bounds; o.append(t(hx[3 + j], y, f"{bx[2]-bx[0]:.0f}×{bx[3]-bx[1]:.0f}", 1.65))
    y = ty + 17.5 + 7*4.4 + 2
    o.append(t(gx, y, "Art boxes in mm, measured on each size's placed art. 01 + 03 widths follow the body (wires run to 3 mm from", 1.75, 400, MUTED))
    o.append(t(gx, y + 3.3, "the side seams on every size); every size is checked on its own pattern for all keep-outs (T13).", 1.75, 400, MUTED))
    o.append(t(gx, y + 8, "C · PLACEMENT REFERENCE PER SIZE", 2.4, 700))
    pl = ["01 back + 03L/03R lower fronts: ONE FILE PER SIZE. Moon, clouds, pole graded A/B/C about CB/CF and 10 above the hem",
          "   seam; the wires are re-run on that size's pattern to the agreed heights at the side seams, so back + front always meet.",
          "02R/02L: inner edge keeps its M distance from CF; top = M distance below the neck seam × scale (nudged where a seam needs it).",
          "04R/04L: centre x × sleeve-width ratio, y from the cap top × sleeve-length ratio; ≥ 15 from cap + underarm, 10 from the cuff.",
          "Exact per-size positions are drawn on the pattern (DXF layer 8: art outline, box, centre = needle start) and listed on T13."]
    for i, l in enumerate(pl): o.append(t(gx, y + 12.5 + i*3.6, l, 1.7))
    return o

def p_bom():
    o = header("BILL OF MATERIALS", "Per jacket, size M. Fabric consumption = pattern piece area ÷ (150 cm width × 80 % marker efficiency) — replace with the factory's marker. Threads: G3.", "T6")
    import gtp_pattern as GP
    C = GP.consumption("M")
    hd = ["#", "Component", "Material / spec", "Colour", "Placement", "Supplier", "Qty (M)"]
    cx = [12, 18, 48, 124, 168, 222, 258]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.8, 700, MUTED))
    rows = [
        ("Shell", SHELL_MAT, "washed navy — match strike-off ≈ #25304D", "body, sleeves, welts, facing", "TBC", f"{C['Shell']:.2f} m", False),
        ("Collar", "14-wale cotton corduroy, 8 oz", "navy-black ≈ #1E2230", "upper + under collar", "TBC", f"{C['Collar']:.2f} m", True),
        ("Hem rib", "1×1 rib, 95/5 cotton/elastane, 400 g/m²", "navy-black", "hem band", "TBC", f"{C['Hem rib']/1000:.2f} m (1 × {C['Hem rib']/10:.0f} cm cut)", True),
        ("Cuff rib", "1×1 rib, 95/5 cotton/elastane, 400 g/m²", "navy-black", "cuffs ×2", "TBC", f"{C['Cuff rib']/1000:.2f} m", True),
        ("Body lining", "100% cotton flannel, 180 g/m²", "navy check or solid", "body", "TBC", f"{C['Body lining']:.2f} m", True),
        ("Sleeve lining", "polyester taffeta 210T", "navy", "sleeves", "TBC", f"{C['Sleeve lining']:.2f} m", True),
        ("Pocket bag", "8 oz cotton twill", "navy", "welt pockets ×2", "TBC", f"{C['Pocket bag']:.2f} m", True),
        ("Interlining", "woven fusible, 60 g/m²", "white", "top collar, facings, welts", "TBC", f"{C['Interlining']:.2f} m", True),
        ("Zip", "YKK #5 metal separating, auto-lock, one-way", "antique brass teeth, navy tape", "CF", "YKK", "1 × 56 cm (M)", False),
        ("Thread — seams", "Coats Epic 120 (Tex 27) corespun poly/cotton", "tonal to shell", "all seams + overlock", "Coats", "~ 450 m", True),
        ("Thread — topstitch", "Coats Gral 40 (Tex 60) poly", "tonal to shell", "topstitch, bartacks", "Coats", "~ 120 m", True),
        ("Embroidery thread", "Madeira Polyneon 40 (14 tones, max 12 per file, see G3)", "per embroidery spec", "01–04", "Madeira", "per spec", False),
        ("Embroidery backing", "2.5 oz cutaway", "black / navy (dark ground)", "behind each element", "TBC", "8 pieces", False),
        ("Main label", LS.main_bom(), "white / black", "CB neck facing", "Haki file", "1", False),
        ("Size label", "woven, 2 × 1.5 cm", "black / cream", "under main label", "TBC", "1", True),
        ("Care / content label", LS.care_bom(SHELL_MAT), "white / black", "wearer's left inside side seam", "Haki file", "1", True),
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
    o.append(t(12, y, "Amber rows = proposed by Haki tech design, not yet specified — confirm material, weight and supplier. Shell (12 oz duck) and zip (YKK brass) are confirmed.", 1.75, 600, PROP))
    o.append(t(12, y + 3.5, "Shell fabric: pre-shrunk / garment-wash tested before embroidery (dense embroidery shrinks panels 1.5–2.5%).", 1.75, 400, MUTED))
    return o

def p_construction():
    o = header("CONSTRUCTION — seams, stitches, assembly order", "SPI = stitches per inch. Seam allowance (SA) in cm. 'Topstitch' = tonal Tex 60 unless noted.", "T7")
    hd = ["Seam / operation", "Stitch type", "SPI", "SA", "Finish / topstitch"]
    cx = [12, 62, 104, 114, 124]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.8, 700, MUTED))
    rows = [("Shoulder", "5-thread safety stitch (ISO 516)", "11", "1.0", "pressed to back; 6 mm single-needle topstitch on back"),
            ("Armhole — front", "5-thread safety stitch", "11", "1.0", "pressed to body; 6 mm topstitch on body"),
            ("Armhole — back", "5-thread safety stitch", "11", "1.0", "pressed to body; 6 mm topstitch on body"),
            ("Side seam + underarm (wrap)", "5-thread safety stitch, one pass", "11", "1.0", "pressed to back, NO topstitch; match wire notches"),
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
             "Embroider 01 back, 02R/02L, 03L/03R, 04R/04L flat.",
             "Trim backing to 5 mm; press from the wrong side.",
             "Make welt pockets on both fronts; bartack.",
             "Join shoulders; topstitch.",
             "Set sleeves; topstitch armholes on the body.",
             "Close side + underarm seams: wire notches matched.",
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
    o = header("LABELS, TRIM PLACEMENT + PACKAGING", "Main + care label = the Haki standard labels (founder 22 Oct 2026), artwork right at 1 : 1, files in the zip labels/. Positions measured on the finished garment.", "T8")
    rows = [("Main label", "CB neck facing, 1.0 below the collar seam, centred; flat, sewn down on all 4 sides"),
            ("Size label", "folded, centred under the main label, caught in the bottom seam of the main label"),
            ("Hanger loop", "6 cm self-fabric loop at CB neck, above the main label"),
            ("Care / content", "wearer's left inside side seam, 10 cm above the hem-rib seam, caught in the lining seam"),
            ("Hangtag", "through the main-label hanger loop with cotton string + barb; never through the embroidery")]
    for i, (a, b) in enumerate(rows):
        o.append(t(14, 34 + i*4.2, a, 1.9, 600)); o.append(t(46, 34 + i*4.2, b, 1.9))
    o.append(t(14, 60, "CARE / CONTENT LABEL", 2.4, 700))
    care = [("Haki standard care label (artwork right): fibre in 9 languages, care text + symbols are printed on it — do not write your own.", False),
            ("Rib (95/5 cotton/elastane), linings and embroidery thread are not on the standard label: Haki confirms if they must be listed", True),
            ("Size: on the size label.", False)]
    for i, (c, pp) in enumerate(care): o.append(prop(14, 65 + i*3.7, c, 1.8) if pp else t(14, 65 + i*3.7, c, 1.85))
    o += LS.panel(200, 30, 85, SHELL_MAT, "Position: CB neck facing, 1.0 below the collar seam, centred.",
                  "Position: wearer's left inside side seam, 10 cm above the hem-rib seam, caught in the lining seam.")[0]
    o.append(t(14, 86, "PACKAGING", 2.4, 700))
    pk = ["Fold: zip closed, sleeves folded back across the body, folded once at the waist — embroidery (01) inside, facing the tissue.",
          "Acid-free tissue sheet between the back embroidery and the fold to stop thread abrasion.",
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
    o = header("COLOURWAY + ARTWORK — moon", "Garment colours and the embroidery in place (stitch preview, size M). Embroidery detail: following section.", "T9")
    fr = Image.open("cover_front.png"); bk = Image.open("cover_back.png")
    tag, h = img_tag(fr, 14, 30, 100); o.append(tag); tag, h2 = img_tag(bk, 120, 30, 100); o.append(tag)
    cx = 228; o.append(t(cx, 33, "GARMENT COLOURS", 2.3, 700))
    cols = [("#25304D", "Shell — washed navy duck"), ("#1E2230", "Collar — navy-black corduroy"), ("#262B3A", "Cuff rib — navy-black"),
            ("#262B3A", "Hem rib — navy-black"), ("#A07C3C", "Zip — antique brass")]
    for i, (h_, n) in enumerate(cols):
        o.append(f'<rect x="{cx}" y="{f(37 + i*5.5)}" width="6" height="4" rx="0.5" fill="{h_}" stroke="#BBB" stroke-width="0.2"/>')
        o.append(t(cx + 8, 40 + i*5.5, n, 1.85))
    o.append(t(cx, 72, "Lab-dip / strike-off approval", 1.9, 700))
    o.append(t(cx, 75.5, "required for shell, collar and both ribs.", 1.85))
    o.append(t(cx, 82, "Embroidery: 14 threads,", 1.9, 700)); o.append(t(cx, 85.5, "Madeira Polyneon (G3).", 1.85))
    return o

QUESTIONS = ["1. Shell colour: target ≈ #25304D washed navy from the mockup — send a Pantone / lab-dip reference; dye/wash method to confirm.",
          "2. Collar corduroy (proposed 14-wale, 8 oz) and rib (95/5 cotton/elastane) in navy-black — confirm weight + colour.",
          "3. Rib heights (hem 5.5, cuff 7.5) and shoulder drop 4.5 are not on the fit chart (same as plum + pine) — confirm.",
          "4. Pattern (T11–T13) is the Drum Island FIRST pattern drafted from the chart: sample + fit M before cutting the size set.",
          "5. Lining: flannel body + taffeta sleeves proposed (navy). Quilted or unlined alternative?",
          "6. Zip garage + auto-lock slider; zip lengths per size (T3) assume CF length − 0.5 cm.",
          "7. Side seams carry the wire wraps: no topstitch on the side seams (T7) — confirm with the sewing room.",
          "8. Seam types + SPI (T7) are a standard proposal — factory to confirm capability.",
          "9. Labels + packaging artwork, country of origin, care-symbol set, carton marks.",
          "10. Garment wash after embroidery? If yes: wash test on the sew-out first (cream moon + white cloud caps grey first).",
          "11. Licensed figure on the pole: licence confirmed by client 2026-10-16. Factory digitizer adds it inside the placeholder box",
          "     from the licensor-approved art; confirm the box size/position against that art (G4).",
          "12. Factory: 360 × 360 frames assumed (factory.json, unconfirmed); max 12 thread colours per file (manufacturer, confirmed): back = 6 hoopings (G5)."]
def p_questions():
    o = header("OPEN QUESTIONS — garment", "Everything marked [proposed — confirm] in this pack, in one place. Embroidery questions are on G4.", "T10")
    for i, q in enumerate(QUESTIONS): o.append(t(14, 34 + i*4.6, q, 2.0))
    return o

PAGES = ["T1 Cover + contents", "T2 Technical flats", "T3 Construction details", "T4 Measurements + size chart",
         "T5 Grading + embroidery grading", "T6 Bill of materials", "T7 Seams, stitches, assembly", "T8 Labels, packaging, QC",
         "T9 Colourway + artwork", "T10 Open questions — garment", "T11 Pattern — pieces + cut list", "T12 Pattern — grade nests + measurement check",
         "T13 Pattern — embroidery placement per size", "T14 Inside view", "T15 Operations + time estimate", "T16 Revision log + sample tracker"]

def build(emb_pdf, emb_pages, out_pdf):
    LS.export("out/labels", SHELL_MAT)                 # Haki standard label files for the zip labels/
    F = TF.Flat("M")
    index = [(n, i + 1) for i, n in enumerate(PAGES)] + [("EMBROIDERY SECTION (G1–G5 + elements 01–04)", len(PAGES) + 1)] + emb_pages
    import gtp_pattern as GP
    pages = [p_cover(index), p_flats(F), p_details(F), p_pom(F), p_grade(), p_bom(), p_construction(), p_labels(), p_colourway(), p_questions(),
             GP.p_pattern_pieces(), GP.p_pattern_grade(), GP.p_pattern_emb(), GP.p_inside(), GP.p_operations(), GP.p_revisions()]
    w = PdfWriter()
    for i, pg in enumerate(pages, 1):
        svg = doc(pg); cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"out/_T{i}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"out/prev_T{i}.png", output_width=2400)
        w.append(PdfReader(f"out/_T{i}.pdf"))
    if emb_pdf: w.append(PdfReader(emb_pdf))
    w.write(out_pdf)
    return len(pages)
