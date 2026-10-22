"""Rev E construction pages (technical-design review of Rev D: M1-M3, M5, M6, S1, S3, S10, S15, N1, N2, N5, N6):
  CS  seams + stitches + wash (one row per seam; SA read from the pattern edges, the rest amber [proposed])
  CI  inside view (drawn from the pattern pieces F01/K01/L01/P02, B01/K02/L02/R01) + numbered bag-out order
  CD  welt pocket, zip / hood / neck junction, zip garage, hanger loop, zip ordering lengths
and the project-level overrides of the zip-hoodie block pages (install(ZB), called by garment.py after it feeds the block
this design's pattern): T2 notes 9-10 (zip garage + hanger loop placed), T3 extended hem / cuff rows + every callout drawn,
T4 S02 drawn + not-to-scale note, T5 centre-panel label moved off the table. The block itself is not edited.
Every number is read from the pattern (front.pieces / hoodie) or the BOM; method choices print amber."""
import kbcore
import math
import numpy as np
from shapely.geometry import Polygon, LineString, box
from shapely import affinity
import sheet as SHT
from sheet import t, INK, MUTED, GREEN, RED, SW, SH, dim_h, dim_v
from render import f
import hoodie as HD, drum
import front as F, emb_place as EP
import build as ZB                       # projects/zip-hoodie-block (garment.py put it on the path + fed it this pattern)
HF = ZB.HF
PROP, ALT = ZB.PROP, ZB.ALT
PR = "  [proposed — confirm]"

def H(title, sub, page): return SHT.header(title, sub, page)
def wrap(o, x, y, s, n, size=1.4, col=INK, lh=2.4, w=400):
    import textwrap
    ls = textwrap.wrap(s, n) or [""]
    for i, l in enumerate(ls): o.append(t(x, y + i * lh, l, size, w, col))
    return len(ls)
def edge(code, name, size="M"):
    return next(e for e in F.pieces(size)[0][code].edges if e.name == name)
def sa(code, name): return edge(code, name).sa / 10                     # cm, from the pattern
def cm(v): return f"{v / 10:.1f}"
def poly(p, X, Y, fill, stroke=INK, w=0.25, dash=None):
    d = " ".join("M" + " L".join(f"{f(X(x))} {f(Y(y))}" for x, y in list(g.exterior.coords)) + " Z" for g in ([p] if p.geom_type == "Polygon" else p.geoms))
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{w}"' + (f' stroke-dasharray="{dash}"' if dash else "") + "/>"
def line(X, Y, pts, col=INK, w=0.25, dash=None):
    return (f'<path d="M' + " L".join(f"{f(X(x))} {f(Y(y))}" for x, y in pts) + f'" fill="none" stroke="{col}" stroke-width="{w}"'
            + (f' stroke-dasharray="{dash}"' if dash else "") + "/>")
def call(x, y, n, r=1.9):
    return f'<circle cx="{f(x)}" cy="{f(y)}" r="{r}" fill="#FFFFFF" stroke="{INK}" stroke-width="0.25"/>' + t(x, y + 0.7, str(n), 1.7, 700, INK, "middle")

# ---------------------------------------------------------------- facts from the pattern (size M)
G, MT = F.pieces("M")
WELT = Polygon(G["F01"].internal[0][1])                                  # welt box on F01 (front coords: x from CF)
FAC_W = 60.0
_k = G["K01"].sew_poly().intersection(LineString([(-1, F.WELT_C[1]), (400, F.WELT_C[1])]))
FAC_W = _k.bounds[2] if not _k.is_empty else FAC_W                       # facing width at the welt height
WELT_TO_FAC = WELT.bounds[0] - FAC_W
P01 = G["P01"]; WELT_W = P01.internal[0][1][0][1]; WELT_L = P01.edges[0].length
BAG = G["P02"].sew_poly().bounds; BAG_MOUTH, BAG_DEPTH = BAG[2] - BAG[0], BAG[3] - BAG[1]; BAG_SIDE = edge("P02", "side R").length
WELT_LOW = MT["hem_f"] - WELT.bounds[3]                                  # welt box lowest corner to the front hem seam
GAR = G["P03"]; GAR_W = GAR.edges[0].length; GAR_H = GAR.internal[0][1][0][1]
LOOP = G["P04"]; LOOP_W = LOOP.edges[0].length; LOOP_L = LOOP.edges[1].length
PLEAT = [p for nm, p in G["L02"].internal if nm.startswith("CB PLEAT")]
PLEAT_W = abs(PLEAT[0][0][0] - PLEAT[1][0][0]); PLEAT_NOTE = G["L02"].note
def zip_len(sz): g, mt = F.pieces(sz); return g["F01"].edges[0].length + mt["hem_h"] - 5
ZIPS = {sz: zip_len(sz) for sz in kbcore.SIZES}
TURN = 15                                                                # cm, turning opening in a sleeve-lining seam [proposed]
FLAT = HD.FLAT / 10
FL_WELT_M = EP.clearances("M")["FL"]["welt"]                     # mm, art to the welt box, wearer's left front, size M

# ---------------------------------------------------------------- CS seams + stitches + wash (M1, M5, S3)
EPIC, GRAL = "Epic 120", "Gral 40"
SEAMS = [  # (seam, pieces, stitch, SPI, SA (code, edge) | text, topstitch, thread, edge finish / note)
    ("Shoulder", "F01/F02 + B01", "301", "10", ("B01", "shoulder L"), "6 mm single needle, on the back", f"{EPIC} + {GRAL}", "pressed to the back; enclosed by the lining"),
    ("Armhole (set-in sleeve)", "S01/S02 + body", "301", "10", ("S01", "cap"), "6 mm single needle, on the body", f"{EPIC} + {GRAL}", "pressed to the body; enclosed"),
    ("Side seam", "F01/F02 + B01", "301", "10", ("F01", "side"), "none", EPIC, "pressed open; enclosed"),
    ("Sleeve underarm", "S01, S02", "301", "10", ("S01", "underarm front"), "none", EPIC, "pressed open; enclosed"),
    ("Hood centre seams", "H01 + H02 + H01", "301", "10", ("H01", "centre seam"), "6 mm single needle, on the centre panel, both sides", f"{EPIC} + {GRAL}", "pressed to the panel; enclosed by the sherpa hood"),
    ("Shell hood to body neck", "H01/H02 + body neck", "301", "10", ("H01", "neck"), "none", EPIC, "notch at HPS = shoulder seam, CB notch; enclosed (T2 note 2)"),
    ("Sherpa hood seams", "H03 + H04 + H03", "301", "8", ("H03", "centre seam"), "none", EPIC, "shave the pile out of the SA; finger-press open"),
    ("Sherpa hood to facings", "H03/H04 + K01/K02 neck", "301", "8", ("K02", "neck"), "none", EPIC, "enclosed; hanger loop caught at CB (CD)"),
    ("Hood face edge (bag-out)", "H01/H02 + H03/H04", "301", "10", ("H01", "face edge"), "6 mm through all layers, sherpa side down", f"{EPIC} + {GRAL}", "shave the pile out of the SA first; scrap mock before the sample (QF2 c)"),
    ("CF zip", "F01/F02 + zip + K01", "301", "10", ("F01", "CF / zip"), "6 mm from the CF fold, through shell + tape + facing", f"{EPIC} + {GRAL}", "tape between shell and facing (CD); continues round the face edge"),
    ("Facing to lining", "K01/K02 + L01/L02", "301", "10", ("K01", "lining join"), "none", EPIC, "pressed to the lining"),
    ("Body lining seams", "L01 + L02", "301", "10", ("L01", "side"), "none", EPIC, "pressed open; CB pleat on L02 (CI step 5)"),
    ("Sleeve lining", "L03 + L01/L02", "301", "10", ("L03", "cap"), "none", EPIC, f"pressed; {TURN} cm left open in one underarm seam to turn (CI)"),
    ("Body hem to hem band", "F01/F02/B01 hem + R01", "301", "10", ("B01", "hem"), "6 mm single needle, on the body above the band", f"{EPIC} + {GRAL}", "outer band layer to the shell, inner layer to the lining hem (CI 10)"),
    ("Hem band elastic", f"R01 + {HD.EL_HEM_W / 10:.0f} cm elastic", "bartack", "—", "—", "none: the elastic floats in the fold (channel)", EPIC, f"elastic ends bartacked {FLAT:.0f} cm from each CF edge; no elastic in the last {FLAT:.0f} cm at the zip"),
    ("Cuff band to sleeve", "S01/S02 cuff + R02 + L03", "301", "10", ("S01", "cuff"), "6 mm single needle, on the sleeve above the band", f"{EPIC} + {GRAL}", "outer band layer to the shell, inner layer to the sleeve lining"),
    ("Cuff band loop", "R02 ends", "301", "10", ("R02", "right"), "none", EPIC, "pressed open; loop seam at the underarm seam"),
    ("Cuff elastic", f"{HD.EL_CUFF_W / 10:.1f} cm elastic loop", "304 zigzag", "—", "1.5 overlap", "none: the loop floats in the fold", EPIC, "overlap zigzagged flat; loop tacked once at the underarm seam"),
    ("Welt + pocket bag", "P01 + P02 + F01/F02", "301 + bartack", "10", ("P01", "top"), "edge-stitch 1.5 mm, welt ends only", f"{EPIC} + {GRAL}", "detail + questions: CD"),
    ("Pocket bag edges", "P02 (2 per pocket)", "301 + 504", "10", ("P02", "side R"), "none", EPIC, "3-thread overlock"),
    ("Zip garage", "P03", "301", "10", ("P03", "left"), "edge-stitch 1.5 mm", f"{EPIC} + {GRAL}", "folded; caught in the zip seam at the top (CD)"),
    ("Hanger loop", "P04", "301", "10", "0", "edge-stitch 1.5 mm", GRAL, "folded in 4; ends caught in the hood-to-facing seam at CB (CD)")]

def p_seams():
    o = H("CONSTRUCTION — seams, stitches + wash", "One row per seam. SA = read from the pattern (DXF). Amber = proposed standard practice for a lined duck work jacket — confirm, or tell us your method.", "CS")
    cx = [12, 16, 54, 85, 104, 113, 124, 176, 203]
    for x_, h_ in zip(cx, ["#", "Seam", "Pieces", "Stitch", "SPI", "SA cm", "Topstitch", "Thread (BOM, T6)", "Edge finish / note"]): o.append(t(x_, 31.5, h_, 1.4, 700, MUTED))
    y = 36
    for i, (nm, pcs, st, spi, sa_, top, thr, fin) in enumerate(SEAMS, 1):
        s_ = (f"{sa(*sa_):.1f}" if isinstance(sa_, tuple) else sa_)
        nl = max(1, -(-len(top) // 64), -(-len(fin) // 98))
        h = 2.2 + 2.3 * nl
        if i % 2: o.append(f'<rect x="11" y="{f(y - 2.6)}" width="{SW - 22}" height="{f(h)}" fill="{ALT}"/>')
        o.append(t(cx[0], y, str(i), 1.4, 700, MUTED)); o.append(t(cx[1], y, nm, 1.42, 700)); o.append(t(cx[2], y, pcs, 1.32, 400, MUTED))
        o.append(t(cx[3], y, st, 1.38, 600, PROP)); o.append(t(cx[4], y, spi, 1.38, 600, PROP)); o.append(t(cx[5], y, s_, 1.42, 700, INK))
        wrap(o, cx[6], y, top, 64, 1.32, PROP, 2.3); o.append(t(cx[7], y, thr, 1.32, 600, PROP)); wrap(o, cx[8], y, fin, 98, 1.32, PROP, 2.3)
        y += h
    y += 3
    o.append(t(12, y, "KEY", 1.9, 700)); y2 = y + 3.6
    for l in ["301 = single-needle lockstitch · 304 = zigzag · 504 = 3-thread overlock · bartack = 1 cm, 28–42 stitches  [proposed — confirm]",
              "SPI = stitches per inch (10 SPI = 2.5 mm stitch, 8 SPI = 3.2 mm). Thread from the BOM (T6): Coats Epic 120 (Tex 27) for seams,",
              "Coats Gral 40 (Tex 60) for topstitching; tonal = navy top + bobbin on the shell, cream on the sherpa  [proposed — confirm]."]:
        o.append(t(12, y2, l, 1.38, 400, INK)); y2 += 2.7
    wx = 160
    o.append(t(wx, y, "WASH + SHRINKAGE  [proposed — confirm]", 1.9, 700, PROP)); y3 = y + 3.6
    for l in ["No garment wash: the shell is pre-washed (washed navy duck) before cutting and embroidery.",
              "The pattern (DXF) is net finished size + seam allowance; it carries no shrinkage allowance.",
              "Please tell us: shell shrinkage after your pre-wash, warp ____ %  weft ____ %;",
              "flannel ____ %, sherpa ____ %; and the SA + shrinkage % you used to cut the sample."]:
        o.append(t(wx, y3, l, 1.38, 400, PROP)); y3 += 2.7
    return o

# ---------------------------------------------------------------- CI inside view + bag-out order (M2)
FLANNEL, FLAN_L, SHELL_I, FACE_I, SHERPA = "#EADCCB", "#C9A98F", "#D3D9E2", "#BCC4D0", "#F2ECDF"
def plaid(p, X, Y, step=40):
    x0, y0, x1, y1 = p.bounds; out = []
    for x in np.arange(x0 + step / 2, x1, step):
        s_ = p.intersection(LineString([(x, y0 - 1), (x, y1 + 1)]))
        if not s_.is_empty and s_.geom_type == "LineString": out.append(line(X, Y, list(s_.coords), FLAN_L, 0.25))
    for y in np.arange(y0 + step / 2, y1, step):
        s_ = p.intersection(LineString([(x0 - 1, y), (x1 + 1, y)]))
        if not s_.is_empty and s_.geom_type == "LineString": out.append(line(X, Y, list(s_.coords), FLAN_L, 0.25))
    return "".join(out)
STEPS = [
    "Embroider the cut front + sleeve panels first (E0). Fuse the facings K01 / K02 and the welts P01.",
    "Fronts: welt pockets with their bags (CD).",
    "Shell: shoulders, set the sleeves, side + underarm seams in one pass; topstitch (CS 1–4).",
    "Shell hood H01 + H02 + H01, topstitch; sew it to the body neck (notch at HPS = shoulder seam, CB notch).",
    f"Lining: L01 + L02 + L03. CB pleat on L02: fold the {PLEAT_W / 10:.0f} cm pleat on the two dashed lines, stitch 5 cm down from the neck, release below. "
    f"Leave {TURN} cm open in one sleeve-lining underarm seam (turning opening).",
    "Facings K01 + K02 to the lining. Main label + hanger loop on K02 (T6b, CD).",
    "Sherpa hood H03 + H04 + H03; sew it to the facing neck (CS 7–8).",
    "Zip between shell CF and facing CF, top stop 5 mm below the face edge; zip garage over the zip top (CD).",
    "Face edge: shell hood to sherpa hood, right sides together (CS 9).",
    f"Hem band: outer layer to the shell hem, elastic in the fold ({FLAT:.0f} cm flat at each zip side), inner layer to the lining hem. The band ends wrap the zip bottom.",
    "Cuffs: band loop + elastic loop to the sleeve; inner layer to the sleeve lining.",
    "Turn the jacket through the sleeve-lining opening; close it with an edge-stitch. Topstitch the face edge + zip 6 mm. "
    "Tack the lining to the shell at both underarms (2 cm thread chain).",
    "Press. No garment wash (CS). Measure against T3, including the extended rows D+ and H+."]

def p_inside():
    o = H("INSIDE VIEW + BAG-OUT ORDER", "Size M, seen from the lining side. Shapes from the pattern pieces; numbers = the steps on the right. Amber = proposed method — confirm or tell us yours.", "CI")
    s = 0.195
    # wearer's left front F01, inside (CF at the left edge of the drawing)
    ox, oy = 18, 38 + 85 * s
    X = lambda x: ox + x * s; Y = lambda y: oy + y * s
    f01, k01, l01 = G["F01"].sew_poly(), G["K01"].sew_poly(), G["L01"].sew_poly()
    o.append(poly(f01, X, Y, SHELL_I, INK, 0.3))
    o.append(poly(l01, X, Y, FLANNEL, INK, 0.25)); o.append(plaid(l01, X, Y))
    o.append(poly(k01, X, Y, FACE_I, INK, 0.3))
    o.append(poly(WELT, X, Y, "none", MUTED, 0.25, "0.8 0.5"))
    hem = MT["hem_f"]; band = box(0, hem, f01.bounds[2], hem + MT["hem_h"])
    o.append(poly(band, X, Y, FACE_I, INK, 0.3)); o.append(line(X, Y, [(0, hem + MT["hem_h"] / 2), (f01.bounds[2], hem + MT["hem_h"] / 2)], MUTED, 0.2, "0.6 0.5"))
    o.append(f'<rect x="{f(X(-6))}" y="{f(Y(-85))}" width="{f(6 * s)}" height="{f((hem + MT["hem_h"] + 85) * s)}" fill="#3A3A3A"/>')
    o.append(f'<rect x="{f(X(0))}" y="{f(Y(-85))}" width="{f(GAR_W * s)}" height="{f(GAR_H * s)}" fill="{FACE_I}" stroke="{INK}" stroke-width="0.25"/>')
    o.append(t(X(0), Y(hem + MT["hem_h"]) + 4, "F01 wearer's left front, inside (CF at left)", 1.45, 700))
    for (x, y), n in [((30, 150), 6), ((180, 120), 5), ((200, 470), 2), ((-3, -40), 8), ((150, hem + 28), 10)]:
        o.append(call(X(x), Y(y), n))
    o.append(t(X(0), Y(hem + MT["hem_h"]) + 7.5, "dashed = welt box; pocket bag behind the lining: CD", 1.25, 400, MUTED))
    # back B01 inside: lining L02 + pleat, facing K02, labels, hanger loop, hem band
    bx, by = 84 + 310 * s, 38 + 30 * s
    X2 = lambda x: bx + x * s; Y2 = lambda y: by + y * s
    b01, k02 = G["B01"].sew_poly(), G["K02"].sew_poly()
    l02 = G["L02"].sew_poly().intersection(b01).difference(k02)
    o.append(poly(b01, X2, Y2, SHELL_I, INK, 0.3)); o.append(poly(l02, X2, Y2, FLANNEL, INK, 0.25)); o.append(plaid(l02, X2, Y2))
    o.append(poly(k02, X2, Y2, FACE_I, INK, 0.3))
    for pl in PLEAT: o.append(line(X2, Y2, pl, INK, 0.3, "1.0 0.6"))
    py0 = PLEAT[0][0][1]
    o.append(f'<rect x="{f(X2(-PLEAT_W / 2))}" y="{f(Y2(py0))}" width="{f(PLEAT_W * s)}" height="{f(50 * s)}" fill="none" stroke="{RED}" stroke-width="0.35"/>')
    lab_y = k02.bounds[1] + 10
    o.append(f'<rect x="{f(X2(-32))}" y="{f(Y2(lab_y))}" width="{f(65 * s)}" height="{f(20 * s)}" fill="#FFFFFF" stroke="{INK}" stroke-width="0.25"/>')
    o.append(f'<path d="M{f(X2(-4))} {f(Y2(k02.bounds[1]))} v{f(36 * s)} M{f(X2(4))} {f(Y2(k02.bounds[1]))} v{f(36 * s)}" stroke="{PROP}" stroke-width="0.45" fill="none"/>')
    hb = MT["hem_b"]; band2 = box(b01.bounds[0], hb, b01.bounds[2], hb + MT["hem_h"])
    o.append(poly(band2, X2, Y2, FACE_I, INK, 0.3))
    o.append(t(X2(b01.bounds[0]), Y2(hb + MT["hem_h"]) + 4, "B01 back, inside", 1.45, 700))
    for (x, y), n in [((60, 40), 6), ((-28, py0 + 20), 5), ((150, 300), 5), ((-200, hb + 28), 10), ((0, -50), 7)]:
        o.append(call(X2(x), Y2(y), n))
    o.append(t(X2(PLEAT_W / 2) + 2, Y2(py0 + 25), f"CB pleat {PLEAT_W / 10:.0f} cm: stitched 5 cm (red), released below", 1.25, 600, INK))
    o.append(t(X2(40), Y2(lab_y) + 2.6, "main label + hanger loop (amber)", 1.2, 400, MUTED))
    ly = Y2(hb + MT["hem_h"]) + 9
    for col, lab in [(SHELL_I, "shell (duck)"), (FACE_I, "facing / band (duck, fused facings)"), (FLANNEL, "body lining (plaid flannel)")]:
        o.append(f'<rect x="{f(bx - 300 * s)}" y="{f(ly - 2.2)}" width="4" height="2.6" fill="{col}" stroke="{INK}" stroke-width="0.15"/>' + t(bx - 300 * s + 5.5, ly, lab, 1.3)); ly += 3.3
    o.append(t(bx - 300 * s, ly + 1, "Sleeve lining L03 (taffeta) and sherpa hood: not drawn — joins in steps 5, 7, 11.", 1.3, 400, MUTED))
    # numbered sequence
    tx = 213; y = 33
    o.append(t(tx, y, "BAG-OUT ORDER" + PR, 1.9, 700, PROP)); y += 4.2
    for i, s_ in enumerate(STEPS, 1):
        o.append(call(tx + 1.6, y - 0.6, i, 1.6))
        n = wrap(o, tx + 4.5, y, s_, 98, 1.32, PROP, 2.35); y += n * 2.35 + 1.5
    return o

# ---------------------------------------------------------------- CD welt, zip / hood / neck junction, zip garage, hanger loop (M3, S1, S3, S10, N2)
def p_details():
    o = H("DETAILS — welt pocket, zip + hood junction, zip garage, hanger loop", "Size M. Numbers from the pattern (DXF); amber = proposed — confirm, or tell us how you would make it.", "CD")
    # welt: front panel crop at 1:2.5
    s = 0.36; x0, y0, x1, y1 = 0, 260, 300, 520
    ox, oy = 14, 34
    X = lambda x: ox + (x - x0) * s; Y = lambda y: oy + (y - y0) * s
    win = box(x0, y0, x1, y1)
    o.append(poly(G["F01"].sew_poly().intersection(win), X, Y, SHELL_I, INK, 0.3))
    o.append(line(X, Y, [(FAC_W, y0), (FAC_W, y1)], MUTED, 0.3, "1.2 0.8"))
    o.append(t(X(FAC_W) + 1, Y(y1) - 2, f"facing edge, {FAC_W / 10:.1f} cm from CF", 1.3, 600, MUTED))
    o.append(poly(WELT, X, Y, FACE_I, INK, 0.35))
    c = np.array(WELT.exterior.coords[:4]); u = c[1] - c[0]; ul = np.linalg.norm(u); u /= ul; nrm = c[3] - c[0]
    for e0 in (c[0], c[1]):                                                       # bartacks across both welt ends
        p0 = e0 + u * (6 if e0 is c[0] else -6)
        o.append(line(X, Y, [tuple(p0), tuple(p0 + nrm)], RED, 0.9))
    o.append(line(X, Y, [(0, y0), (0, y1)], INK, 0.4))
    o.append(t(X(2), Y(y0) + 3, "CF", 1.4, 700))
    o.append(t(ox, Y(y1) + 4, "WELT POCKET, wearer's left front (right = mirror). Red = bartacks.", 1.35, 700))
    y = Y(y1) + 8.5
    for l, p in [(f"Type: single welt, one piece P01 folded lengthwise + fused; finished {WELT_W / 10:.1f} × {WELT_L / 10:.1f} cm at {F.WELT_ANG:.0f}° (pattern).", False),
                 (f"Welt box on the panel: {WELT.bounds[0] / 10:.1f} cm from CF at its nearest corner; {WELT_TO_FAC / 10:.1f} cm clear of the facing edge (pattern).", False),
                 (f"Bag: 2 × P02 per pocket (cotton twill), mouth {BAG_MOUTH / 10:.1f} cm, side {BAG_SIDE / 10:.1f} cm, {BAG_DEPTH / 10:.1f} cm deep at the centre (pattern); seams 0.5 cm, overlocked.", False),
                 (f"The welt's lowest corner is {WELT_LOW / 10:.1f} cm above the hem seam and {WELT_TO_FAC / 10:.1f} cm from the facing edge (pattern): please lay the bag on the front pattern and tell us how it hangs.", False),
                 ("Bartacks: both welt ends, 1 cm, through welt + shell + bag. Edge-stitch the welt ends only." + PR, True),
                 ("Bag to facing: where the bag reaches the facing, catch its CF edge in the facing-to-lining seam so it can't twist; otherwise it hangs free." + PR, True),
                 ("No bag stitching shows on the outside front: only the welt and its bartacks." + PR, True)]:
        n = wrap(o, ox, y, l, 165, 1.35, PROP if p else INK, 2.4); y += n * 2.4 + 0.6
    y += 1.5; o.append(t(ox, y, "PLEASE ANSWER", 1.6, 700)); y += 3.2
    for q in ["Is any pocket-bag stitching visible on the outside front?   YES / NO",
              f"Can you sew the welts with the art 6 mm from the welt box (wearer's left front: {FL_WELT_M:.1f} mm at size M)?   YES / NO — if NO, the clearance you need: ____ mm"]:
        n = wrap(o, ox, y, q, 160, 1.38, INK, 2.4, 600); y += n * 2.4 + 0.8
    # zip / hood / neck junction (schematic)
    jx, jy = 150, 34; o.append(t(jx, jy, "ZIP + HOOD + NECK JUNCTION (schematic, inside view at CF)", 1.7, 700))
    sj = 1.0; gx = jx + 30; top = jy + 8
    o.append(f'<path d="M{f(gx - 26)} {f(top)} Q{f(gx - 4)} {f(top - 2)} {f(gx)} {f(top + 10)} L{f(gx)} {f(top + 52)} L{f(gx - 26)} {f(top + 52)} Z" fill="{SHERPA}" stroke="{INK}" stroke-width="0.3"/>')
    o.append(t(gx - 24, top + 6, "sherpa hood", 1.25, 600))
    o.append(f'<rect x="{f(gx - 2.5)}" y="{f(top + 10 + 0.5 * sj)}" width="5" height="{f(42)}" fill="#3A3A3A"/>')
    o.append(f'<line x1="{f(gx)}" y1="{f(top + 10.5)}" x2="{f(gx)}" y2="{f(top + 52)}" stroke="#D2B062" stroke-width="1.6" stroke-dasharray="0.6 0.4"/>')
    o.append(f'<rect x="{f(gx + 2.5)}" y="{f(top + 18)}" width="22" height="34" fill="{FACE_I}" stroke="{INK}" stroke-width="0.3"/>')
    o.append(t(gx + 5, top + 36, "facing K01", 1.25, 600))
    o.append(f'<rect x="{f(gx - GAR_W / 10)}" y="{f(top + 11)}" width="{f(GAR_W / 5)}" height="{f(GAR_H / 5)}" fill="{FACE_I}" stroke="{PROP}" stroke-width="0.4" fill-opacity="0.85"/>')       # 2:1
    o.append(line(lambda x: x, lambda y: y, [(gx + 4, top + 10.5), (gx + 40, top + 4)], MUTED, 0.2)); o.append(t(gx + 41, top + 4, "zip top stop 5 mm below the face edge (T2 note 3)", 1.25))
    o.append(line(lambda x: x, lambda y: y, [(gx + 3, top + 14), (gx + 40, top + 11)], PROP, 0.2)); o.append(t(gx + 41, top + 11, f"zip garage P03, {GAR_W / 10:.0f} × {GAR_H / 10:.0f} cm folded, over the zip top", 1.25, 600, PROP))
    o.append(line(lambda x: x, lambda y: y, [(gx - 6, top + 6), (gx + 40, top + 18)], PROP, 0.2)); o.append(t(gx + 41, top + 18, "6 mm topstitch: round the face edge, down the zip", 1.25, 600, PROP))
    o.append(line(lambda x: x, lambda y: y, [(gx + 1, top + 40), (gx + 40, top + 25)], MUTED, 0.2)); o.append(t(gx + 41, top + 25, "tape between shell and facing; tape ends folded back 45° under the facing", 1.25, 600, PROP))
    y = top + 58
    for l, p in [("Zip: YKK #5 metal, antique brass, 2-way separating; navy tape; both sliders open downward, lock pullers" + PR, True),
                 ("Bottom: the box + pin end at the hem-band edge; the band's flat zone (no elastic) wraps the tape so the box lies flat (QF2 a)." + PR, True),
                 (f"Art keep-out: {F.KEEP_CF:.0f} mm each side of the CF line of the pattern (x = 0 = the CF sew line = the shell fold at the zip teeth). "
                  f"The 6 mm zip topstitch therefore runs {F.KEEP_CF - 6:.0f} mm clear of the art.", False),
                 (f"Zip garage P03: cut {GAR_W / 10:.0f} × {GAR.edges[1].length / 10:.0f} cm, folded to {GAR_W / 10:.0f} × {GAR_H / 10:.0f} cm; on the inside over the zip top, caught in the zip seam (wearer's left)." + PR, True),
                 (f"Hanger loop P04: cut {LOOP_W / 10:.1f} × {LOOP_L / 10:.0f} cm, folded in 4, edge-stitched (pattern); ends caught in the hood-to-facing seam at CB, "
                  "above the main label (T6b)." + PR, True)]:
        n = wrap(o, jx, y, l, 185, 1.35, PROP if p else INK, 2.4); y += n * 2.4 + 0.6
    y += 2; o.append(t(jx, y, "ZIP ORDERING LENGTH PER SIZE (cm)", 1.6, 700)); y += 3.4
    for j, sz in enumerate(kbcore.SIZES):
        o.append(t(jx + j * 19, y, sz, 1.35, 700, MUTED)); o.append(t(jx + j * 19, y + 3, f"{ZIPS[sz] / 10:.1f}", 1.35, 400, MUTED)); o.append(t(jx + j * 19, y + 6, f"{ZIPS[sz] / 10:.0f}", 1.5, 700))
    o.append(t(jx + 7 * 19, y + 3, "pattern", 1.25, 400, MUTED)); o.append(t(jx + 7 * 19, y + 6, "order", 1.25, 700))
    y += 9.5
    wrap(o, jx, y, "Order length = the pattern length (hem-band edge to CF neck − 0.5, T5) rounded to the nearest whole cm (T6). Please tell us if your supplier cuts in other steps.", 185, 1.32, PROP, 2.35)
    return o

# ---------------------------------------------------------------- block page overrides (install)
NOTES = list(ZB.NOTES)
NOTES[2] = ("3", "Zip: 2-way separating, YKK #5 metal, antique brass, navy tape, both sliders open downward; hem-band edge to CF neck; top stop 5 mm below the hood face edge. Detail: CD.", True)
NOTES[3] = ("4", "Welt pockets: CD. Every seam, stitch + topstitch: CS. Facings, body lining, CB pleat + bag-out order: CI.", False)
NOTES += [("9", f"Zip garage P03: folded {GAR_W / 10:.0f} × {GAR_H / 10:.0f} cm, inside over the zip top (chin guard). CD.", True),
          ("10", f"Hanger loop P04: {LOOP_L / 10:.0f} cm, inside the back neck at CB above the main label. CD.", True)]

def p_flats():
    o = H("FLATS + CONSTRUCTION", "Size M, front and back. Body and sleeve are the approved Drum Island jacket; numbered notes are the hoodie changes.", "T2")
    Fl = HF.Flat("M"); pos = []
    for i, (fn, back) in enumerate(((HF.draw_front, False), (HF.draw_back, True))):
        b = HF.bounds(Fl, back); s = 92 / (b[2] - b[0]); ox = 12 + i * 100; o.append(ZB.flat_g(fn(Fl), b, ox, 32, s)); pos.append((b, s, ox))
    def cxy(i, x, y): b, s, ox = pos[i]; return ox + (x - b[0]) * s, 32 + (y - b[1]) * s
    calls = [(0, (0, -(HD.hcm("Q", "M") - 120)), "1"), (0, (Fl.b.neck2 * 0.6, Fl.fnd * 0.55), "2"), (0, (0, Fl.hem_seam - 120), "3"),
             (0, (240, 420), "4"), (0, (-200, Fl.hem_seam + 25), "5"), (1, (-Fl.cuff_out[0] + 30, Fl.cuff_out[1] - 20), "6"), (1, (0, 280), "7"), (1, (0, 40), "8"),
             (0, (-34, Fl.fnd + 14), "9"), (1, (-52, 70), "10")]
    for i, (x, y), n in calls:
        X, Y = cxy(i, x, y)
        o.append(f'<circle cx="{f(X)}" cy="{f(Y)}" r="2.4" fill="#FFFFFF" stroke="{INK}" stroke-width="0.3"/>' + t(X, Y + 0.85, n, 2.1 if len(n) == 1 else 1.8, 700, INK, "middle"))
    y = 34; tx = 214
    for n, s_, p in NOTES:
        o.append(f'<circle cx="{tx}" cy="{f(y - 0.8)}" r="2.0" fill="#FFFFFF" stroke="{INK}" stroke-width="0.25"/>' + t(tx, y, n, 1.8 if len(n) == 1 else 1.5, 700, INK, "middle"))
        k = wrap(o, tx + 4, y, s_, 46, 1.65, PROP if p else INK, 3.1); y += 3.1 * k + 2.4
    o.append(t(tx, y + 2, "Amber = proposed by Haki tech design — confirm.", 1.6, 600, PROP))
    o.append(t(12, 170, "Inside view, bag-out order, seam table and details: CI, CS, CD. Zip garage (9) and hanger loop (10) are inside the jacket.", 1.6, 400, MUTED))
    return o

def ext_rows():
    """D+ / H+ (M6): elastic fully stretched = the band's sew-line length, half, per size (pattern)"""
    d = [round(F.pieces(sz)[1]["hem_band"] / 20, 1) for sz in kbcore.SIZES]
    h = [round(F.pieces(sz)[1]["sleeve_open"] / 20, 1) for sz in kbcore.SIZES]
    return {"D+": ("Bottom sweep, extended", "½, hem edge, elastic fully stretched (= band length)", d, 1.0, "PROPOSED"),
            "H+": ("Sleeve opening, extended", "½, cuff edge, elastic fully stretched (= band length)", h, 0.5, "PROPOSED")}

def dim_a(x1, y1, x2, y2, label, col=INK, off=(0, 0)):
    """dimension along any direction, label at the middle (+ offset)"""
    v = np.array([x2 - x1, y2 - y1]); v = v / (np.linalg.norm(v) or 1); n = np.array([-v[1], v[0]]) * 1.2
    o = (f'<g stroke="{col}" stroke-width="0.18"><line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}"/>'
         f'<line x1="{f(x1 - n[0])}" y1="{f(y1 - n[1])}" x2="{f(x1 + n[0])}" y2="{f(y1 + n[1])}"/>'
         f'<line x1="{f(x2 - n[0])}" y1="{f(y2 - n[1])}" x2="{f(x2 + n[0])}" y2="{f(y2 + n[1])}"/></g>')
    return o + t((x1 + x2) / 2 + off[0], (y1 + y2) / 2 + off[1], label, 1.8, 700, col, "middle")

def p_pom():
    o = H("SIZE CHART + MEASUREMENT CHECK", "Chart in cm. Body + sleeve rows are the approved Drum Island chart, unchanged. Hood + band rows are new (proposed). ½ = half measurement, flat.", "T3")
    Fl = HF.Flat("M"); b = HF.bounds(Fl); s = 64 / (b[2] - b[0]); ox, oy = 10, 40
    o.append(ZB.flat_g(HF.draw_front(Fl), b, ox, oy, s))
    X = lambda x: ox + (x - b[0]) * s; Y = lambda y: oy + (y - b[1]) * s
    o.append(dim_v(Y(0), Y(Fl.hem_edge), X(Fl.ua[0] + 22), "A", 1.8, side=1))
    o.append(dim_h(X(-Fl.ua[0]), X(Fl.ua[0]), Y(Fl.ua[1] + 6), "B", 1.8))
    o.append(dim_h(X(-Fl.sp[0]), X(Fl.sp[0]), Y(Fl.sp[1] - 4), "C", 1.8))
    o.append(dim_h(X(-Fl.sweep2), X(Fl.sweep2), Y(Fl.hem_edge + 16), "D / D+", 1.6))
    o.append(dim_v(Y(-(HD.hcm("Q", "M") - 70)), Y(0), X(-Fl.b.neck2 - 90), "Q", 1.8))
    o.append(dim_v(Y(Fl.hem_seam), Y(Fl.hem_edge), X(-Fl.sweep2 - 14), "S", 1.6))
    o.append(dim_h(X(-Fl.hps[0]), X(Fl.hps[0]), Y(-14), "J", 1.5))
    o.append(dim_v(Y(0), Y(Fl.fnd), X(14), "K", 1.4, side=1))
    sp, ua = np.array(Fl.sp), np.array(Fl.ua)
    o.append(dim_a(X(-sp[0]), Y(sp[1]), X(-ua[0]), Y(ua[1]), "E", off=(-2.2, 0)))
    p0 = ua + Fl.sdir * 25; p1 = p0 + Fl.sperp * drum.m("F", "M")
    o.append(dim_a(X(p0[0]), Y(p0[1]), X(p1[0]), Y(p1[1]), "F", off=(-1.5, 3.2)))
    a0, a1 = sp + Fl.sperp * 14, Fl.cuff_out + Fl.sperp * 14
    o.append(dim_a(X(a0[0]), Y(a0[1]), X(a1[0]), Y(a1[1]), "G", off=(1.6, -1.2)))
    c0, c1 = Fl.cuff_out + Fl.sdir * 8, Fl.cuff_in + Fl.sdir * 8
    o.append(dim_a(X(c0[0]), Y(c0[1]), X(c1[0]), Y(c1[1]), "H / H+", off=(2.5, 2.5)))
    t0, t1 = Fl.cs_out + Fl.sperp * 6, Fl.cuff_out + Fl.sperp * 6
    o.append(dim_a(X(t0[0]), Y(t0[1]), X(t1[0]), Y(t1[1]), "T", off=(1.6, -0.6)))
    tb = 10; ty = oy + (b[3] - b[1]) * s + 12
    for j, l in enumerate(["A–T drawn on the front, size M (½ = flat, half). D + H relaxed; D+ / H+ = elastic fully",
                           "stretched (band length, from the pattern). L back neck drop: HPS line to the CB neck seam.",
                           "P shoulder forward: shoulder seam ahead of the HPS. Measure flat, zip closed.",
                           "Hood (Q, R): zip closed, hood laid flat on its side, sherpa inside; Q = HPS neck seam to the top,",
                           "R = face edge to the back fold at the widest point."]):
        o.append(t(tb, ty + j * 3, l, 1.4, 400, MUTED))
    CH = dict(ZB.CH); CH.update(ext_rows())
    sizes = kbcore.SIZES
    hd = ["", "Point of measure", "How measured"] + sizes + ["Tol", "Source"]; cx = [80, 86, 128, 168, 177, 186, 195, 204, 213, 223, 233, 243]
    for x_, h_ in zip(cx, hd): o.append(t(x_, 31, h_, 1.6, 700, MUTED))
    order = ["A", "B", "C", "D", "D+", "E", "F", "G", "H", "H+", "J", "K", "L", "P", "Q", "R", "S", "T"]
    for i, k in enumerate(order):
        nm, how, vals, tol, src = CH[k][:5]; y = 35.5 + i * 3.9; pr = src == "PROPOSED"
        if i % 2 == 0: o.append(f'<rect x="79" y="{f(y - 2.8)}" width="{SW - 90}" height="3.9" fill="{ALT}"/>')
        col = PROP if pr else INK
        o.append(t(cx[0], y, k, 1.6, 700, col)); o.append(t(cx[1], y, nm[:34], 1.5, 600, col)); o.append(t(cx[2], y, how[:56], 1.25, 400, MUTED))
        for j, v in enumerate(vals): o.append(t(cx[3 + j], y, f"{v:g}", 1.5, 600 if sizes[j] == "M" else 400, col))
        o.append(t(cx[10], y, f"±{tol:g}", 1.42, 400, PROP if k.endswith("+") else MUTED)); o.append(t(cx[11], y, "proposed" if pr else "jacket", 1.42, 600, col))
    y = 35.5 + len(order) * 3.9 + 4
    o.append(t(80, y, "PATTERN CHECK — every size measured off the drafted pattern pieces vs this chart", 1.9, 700)); y += 4.2
    for j, sz in enumerate(sizes):
        ok = ZB.CHECK[sz] and ZB.WALKS_OK[sz] and ZB.SHAPE_OK[sz]
        o.append(t(cx[3 + j], y, "pass" if ok else "FAIL", 1.6, 700, GREEN if ok else RED))
    o.append(t(80, y, "chart · seam walks · shape checks", 1.5, 400, MUTED))
    y += 6
    for l in ["Hood height (Q) and width (R) include 1.5 cm for the sherpa pile (~8 mm) — an unlined hood would be 1.5 cm smaller.",
              "D and H are relaxed: the elastic sets them. D+ and H+ are the stretched bands (= the body hem / sleeve opening); their tolerances are proposed.",
              "Grading: body + sleeve per the jacket chart; hood +0.5 cm height and width per size."]:
        o.append(t(80, y, l, 1.5, 400, MUTED)); y += 3.2
    return o

def install(Z):
    """route the block's T2-T5 page builders to this design's versions (garment.py, after Z.G / Z.HF.Flat are set)"""
    import re
    Z.p_flats = p_flats; Z.p_pom = p_pom
    d0 = Z._draw
    def _draw(o, g, codes, x0, y0, wmax, s, lw=0.3, tm=1.2, gap=4):
        if codes == ["B01", "F01", "F02", "S01"]: codes, s = codes + ["S02"], s * 0.9          # N1: draw S02 too
        return d0(o, g, codes, x0, y0, wmax, s, lw, tm, gap)
    Z._draw = _draw
    pieces0, hood0 = Z.p_pieces, Z.p_hood
    def p_pieces():
        o = pieces0()
        rep = {"Removed from the jacket: collar (C01, C02, IC01) and rib (old R01/R02).": "Not to scale: pieces are drawn to fit the page. Cut from the DXF / 1:1 plot.",
               "Body, sleeve, facings, lining = the jacket pattern.": "Body, sleeve, facings, lining = the jacket pattern. Not to scale."}
        out = []
        for el in o:
            for a, b_ in rep.items(): el = el.replace(a, b_)
            out.append(el)
        return out
    def p_hood():
        o = hood0(); lab = f"{HD.CW / 10:.0f} × {Z.mM['hood']['seam'] / 10:.1f} cm"
        out = []
        for el in o:
            if el.startswith("<text") and f">{lab}<" in el: el = t(112 + HD.CW * 0.25 / 2, 37.6, lab, 1.6, 600, "#0A84D6", "middle")    # N5: off the per-size table
            out.append(el)
        return out
    Z.p_pieces, Z.p_hood = p_pieces, p_hood
