"""Dismantle Pants — vector flats (front + back) on the Hidden Inventory silhouette.

The silhouette + construction-line positions are the Konpeito jeans flats (projects/konpeito-jeans/kjflat.py), which were
traced from a flat lay of the same Hidden Inventory (HI) pants block with the cargo pockets removed. Copied, not
imported, so a Konpeito change cannot move this pack. Changes for Dismantle:
  * fill = the black / tan windowpane check (P1), drawn at its estimated true scale and matched across pieces
  * plain HI coin pocket (no embroidered patch); no embroidery anywhere
  * back label = Haki standard main label OUTSIDE at CB of the waistband  [proposed]
  * belt loops: HI CB loop replaced by two loops either side of the back label  [proposed]
"""
import json, os
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import measure
from shapely.geometry import Polygon
from shapely import affinity
from render import f, geom_to_path

SRC = "inputs/reference/hi-silhouette-source_konpeito-flat-lay.png"
MM = (33.1 * 25.4 / 2) / 436.8      # as Konpeito: half relaxed waist HI size 32 (420.4 mm) / front waistband width on the flat lay (px)
INK = "#1A1A1A"
CON = "#F2F2F2"         # construction lines drawn light so they read on the black check
STITCH = "#BDBDBD"      # topstitch: thread is DTM black; DRAWN light grey dashes so the flat reads
PR = json.load(open("out/print.json")) if os.path.exists("out/print.json") else {"square_cm_proposed": 1.27}
REPEAT = PR["square_cm_proposed"] * 10           # mm, estimated (P1)
GROUND = "#151513"; LINE = "#9A8F7B"             # mean of the two refs (P1); approximate
LINE_W = 1.3                                     # mm, estimated (P1)
CB_PX = 380                                      # back flat CB x (px)
BACK_LOOPS_PX = (185, 323, 437, 578)             # side-back loops as HI (185, 578) + two flanking the back label, 15 mm clear of its ends (proposed)
FRONT_LOOPS_PX = (1020, 1190)
LABEL_MM = (65.0, 20.0)
WB_TOP_PX, WB_BOT_PX = 47, 95                    # waistband top / waist seam on the flat (px)
COIN_TL_PX = (902, 122); COIN_MM = (76.0, 56.0)  # HI coin-pocket position on the front-right facing (as Konpeito); size per HI pattern


def check_defs(pid="chk", repeat=None, line_w=None):
    r = repeat or REPEAT; w = line_w or LINE_W; h = w / 2
    da = f'{f(r / 14)} {f(r / 28)}'                  # broken / beaded line look (drawing convention; real yarn look = P1)
    return (f'<defs><pattern id="{pid}" patternUnits="userSpaceOnUse" width="{f(r)}" height="{f(r)}">'
            f'<rect width="{f(r)}" height="{f(r)}" fill="{GROUND}"/>'
            f'<line x1="0" y1="{f(h)}" x2="{f(r)}" y2="{f(h)}" stroke="{LINE}" stroke-width="{f(w)}" stroke-dasharray="{da}"/>'
            f'<line x1="{f(h)}" y1="0" x2="{f(h)}" y2="{f(r)}" stroke="{LINE}" stroke-width="{f(w)}" stroke-dasharray="{da}"/>'
            f'</pattern></defs>')


def silhouettes():
    a = np.asarray(Image.open(SRC).convert("RGB")).astype(float)
    v = a.max(-1) / 255; s = (a.max(-1) - a.min(-1)) / (a.max(-1) + 1e-6)
    m = (v < 0.45) | ((s > 0.4) & (v > 0.3))
    m = ndi.binary_closing(m, iterations=3); m = ndi.binary_fill_holes(m); m = ndi.binary_opening(m, iterations=4)
    out = {}
    for name, (x0, x1) in (("back", (0, 760)), ("front", (760, a.shape[1]))):
        mm = np.zeros_like(m); mm[:, x0:x1] = m[:, x0:x1]
        lab, n = ndi.label(mm); big = np.argmax(np.bincount(lab.ravel())[1:]) + 1
        c = max(measure.find_contours((lab == big).astype(float), 0.5), key=len)
        out[name] = Polygon([(x, y) for y, x in c]).simplify(1.5)
    return out


def T(px_pts, ox):
    return [((x - ox) * MM, y * MM) for x, y in px_pts]


def path(pts, stroke=CON, w=0.6, dash=None, fill="none", close=False):
    d = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts) + (" Z" if close else "")
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{w}"{da} stroke-linejoin="round" stroke-linecap="round"/>'


def bez(p0, p1, p2, p3, n=24):
    t = np.linspace(0, 1, n)[:, None]; p0, p1, p2, p3 = map(np.array, (p0, p1, p2, p3))
    return ((1-t)**3*p0 + 3*(1-t)**2*t*p1 + 3*(1-t)*t**2*p2 + t**3*p3).tolist()


def topst(pts):
    return path(pts, STITCH, 0.35, "1.2 0.8")


def loop(bx, ox, y0, y1):
    return path(T([(bx - 7, y0), (bx + 7, y0), (bx + 7, y1), (bx - 7, y1)], ox), close=True, fill="url(#chk)", w=0.5)


def back_label_rect():
    """mm rect (x, y, w, h) of the back label on the back flat: centred on CB and on the waistband height."""
    w, h = LABEL_MM; cy = (WB_TOP_PX + WB_BOT_PX) / 2 * MM
    return CB_PX * MM - w / 2, cy - h / 2, w, h


def back_svg(sil, label_href=None):
    ox = 0
    P = affinity.scale(sil, MM, MM, origin=(0, 0))
    o = [check_defs(), f'<path d="{geom_to_path(P)}" fill="url(#chk)" stroke="{INK}" stroke-width="0.7"/>']
    o.append(path(T([(165, WB_BOT_PX), (CB_PX, 98), (597, WB_BOT_PX)], ox)))
    o.append(topst(T([(166, 51), (CB_PX, 53), (595, 51)], ox))); o.append(topst(T([(167, 90), (CB_PX, 93), (596, 90)], ox)))
    o.append(path(T([(CB_PX, 40), (CB_PX, 98)], ox), w=0.4, dash="1.4 0.8"))          # waistband CB seam (2 pieces, as HI)
    for bx in BACK_LOOPS_PX: o.append(loop(bx, ox, 38, 102))
    # back label OUTSIDE at CB (proposed): Haki standard main label 65 x 20, sewn down on all 4 sides
    x, y, w, h = back_label_rect()
    o.append(f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="#FFFFFF" stroke="{INK}" stroke-width="0.4"/>')
    if label_href: o.append(f'<image x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" href="{label_href}"/>')
    o.append(f'<rect x="{f(x + 1.2)}" y="{f(y + 1.2)}" width="{f(w - 2.4)}" height="{f(h - 2.4)}" fill="none" stroke="#777" stroke-width="0.35" stroke-dasharray="1.2 0.8"/>')
    # NO back yoke (as HI): CB (seat) seam from the waistband to the crotch, 2 rows of topstitch
    o.append(path(T([(CB_PX, 98), (CB_PX, 470)], ox))); o.append(topst(T([(385, 99), (385, 465)], ox))); o.append(topst(T([(390, 99), (390, 462)], ox)))
    for x0, x1 in ((160, 340), (423, 603)):      # HI pointed back patch pockets, centred on each leg
        cx = (x0 + x1) / 2
        pk = [(x0, 183), (x1, 183), (x1 - 8, 352), (cx, 372), (x0 + 8, 352)]
        o.append(path(T(pk, ox), close=True))          # no own fill: the body check shows through = matched (and no darker aliasing)
        o.append(topst(T([(x0, 198), (x1, 198)], ox)))
        inner = Polygon(T(pk, ox)).buffer(-2.0, join_style="mitre")
        o.append(path(list(inner.exterior.coords), STITCH, 0.35, "1.2 0.8"))
        for rx in (x0 + 4, x1 - 4):                # horizontal bartacks at the top corners (HI p. 2)
            o.append(f'<line x1="{f(rx * MM - 4)}" y1="{f(186 * MM)}" x2="{f(rx * MM + 4)}" y2="{f(186 * MM)}" stroke="#D9D9D9" stroke-width="2.0" stroke-linecap="round"/>')
    o.append(path(T([(CB_PX, 470), (372, 500)], ox)))
    return "\n".join(o), P.bounds


def front_svg(sil):
    ox = 760
    P = affinity.translate(affinity.scale(sil, MM, MM, origin=(0, 0)), -ox * MM, 0)
    o = [check_defs(), f'<path d="{geom_to_path(P)}" fill="url(#chk)" stroke="{INK}" stroke-width="0.7"/>']
    o.append(path(T([(886, WB_BOT_PX), (1105, 98), (1322, WB_BOT_PX)], ox)))
    o.append(topst(T([(888, 51), (1105, 53), (1320, 51)], ox))); o.append(topst(T([(887, 90), (1105, 93), (1321, 90)], ox)))
    for bx in FRONT_LOOPS_PX: o.append(loop(bx, ox, 42, 104))
    o.append(f'<circle cx="{f((1112 - ox) * MM)}" cy="{f(72 * MM)}" r="8.5" fill="#1E1E20" stroke="#8A8A8E" stroke-width="0.4"/>')
    o.append(path(T([(1105, 98), (1100, 470)], ox)))
    o.append(topst(T(bez((1075, 98), (1072, 250), (1070, 330), (1100, 368)), ox)))
    zt, zb = 100 * MM, 100 * MM + 152.4             # 6 in zip under the fly (hidden, dashed)
    o.append(f'<line x1="{f((1092 - ox) * MM)}" y1="{f(zt)}" x2="{f((1092 - ox) * MM)}" y2="{f(zb)}" stroke="{STITCH}" stroke-width="1.6" stroke-dasharray="0.5 0.5"/>')
    # coin pocket (plain, self fabric, check matched) on the wearer's right facing
    cx0, cy0 = (COIN_TL_PX[0] - ox) * MM, COIN_TL_PX[1] * MM; cw, ch = COIN_MM
    o.append(f'<rect x="{f(cx0)}" y="{f(cy0)}" width="{f(cw)}" height="{f(ch)}" fill="none" stroke="{CON}" stroke-width="0.6"/>')
    o.append(topst([(cx0 + 2, cy0 + 2), (cx0 + 2, cy0 + ch - 2), (cx0 + cw - 2, cy0 + ch - 2), (cx0 + cw - 2, cy0 + 2)]))
    o.append(topst([(cx0, cy0 + 4), (cx0 + cw, cy0 + 4)]))
    for rx in (cx0 + 4.25, cx0 + cw - 4.25):
        o.append(f'<circle cx="{f(rx)}" cy="{f(cy0 + 4.25)}" r="2.2" fill="#1E1E20" stroke="#8A8A8E" stroke-width="0.3"/>')
    R = [(870, 172)] + OPENING_PX + [(1024, 98)]
    L = [(2210 - x, y) for x, y in R]
    for pts in (R, L):
        o.append(path(T(pts, ox)))
        o.append(topst(T([(x, y + 6) if i < len(pts) - 1 else (x + (6 if x < 1105 else -6), y) for i, (x, y) in enumerate(pts)], ox)))
    for rx, ry in ((1021, 130), (1189, 130)):
        o.append(f'<circle cx="{f((rx - ox) * MM)}" cy="{f(ry * MM)}" r="2.2" fill="#1E1E20" stroke="#8A8A8E" stroke-width="0.3"/>')
    o.append(path(T([(1100, 470), (1092, 500)], ox)))
    return "\n".join(o), P.bounds


OPENING_PX = [(878, 173), (904, 179), (930, 183), (960, 184), (980, 180), (1000, 168), (1012, 152), (1021, 130)]   # = Konpeito scoop opening
