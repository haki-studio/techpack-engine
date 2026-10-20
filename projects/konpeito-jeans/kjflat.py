"""Vector flats (front + back) drawn to the mockup (1792127150159_image.png): silhouette traced from the flat lay,
construction lines placed from the flat (px -> mm at the PROPOSED 0.97 mm/px), embroidery drawn at true size."""
import math
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import measure
from shapely.geometry import Polygon, LineString, Point
from shapely import affinity
import kjcore
from render import f, geom_to_path

SRC = "inputs/1792127150159_image.png"
MM = 420.0 / 432.0
STITCH = "#141416"      # DTM black topstitch (founder 19 Oct), drawn just darker than the denim
INK = "#1A1A1A"; DENIM = "#3A3B3F"; DENIM_LT = "#4A4B50"

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
        P = Polygon([(x, y) for y, x in c]).simplify(1.5)
        out[name] = P
    return out

def T(px_pts, ox):
    return [((x - ox) * MM, y * MM) for x, y in px_pts]

def path(pts, stroke=INK, w=0.6, dash=None, fill="none", close=False):
    d = "M" + " L".join(f"{f(x)} {f(y)}" for x, y in pts) + (" Z" if close else "")
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{w}"{da} stroke-linejoin="round" stroke-linecap="round"/>'

def bez(p0, p1, p2, p3, n=24):
    t = np.linspace(0, 1, n)[:, None]; p0, p1, p2, p3 = map(np.array, (p0, p1, p2, p3))
    return ((1-t)**3*p0 + 3*(1-t)**2*t*p1 + 3*(1-t)*t**2*p2 + t**3*p3).tolist()

def topst(pts, off=(0, 0)):
    return path([(x + off[0], y + off[1]) for x, y in pts], STITCH, 0.35, "1.2 0.8")

def back_svg(sil, emb=True, callouts=True):
    ox = 0
    P = affinity.scale(sil, MM, MM, origin=(0, 0))
    o = [f'<path d="{geom_to_path(P)}" fill="{DENIM}" stroke="{INK}" stroke-width="0.7"/>']
    X = lambda x: x * MM; Y = lambda y: y * MM
    # waistband
    o.append(path(T([(165, 95), (380, 98), (597, 95)], ox)))
    o.append(topst(T([(166, 47), (380, 49), (595, 47)], ox))); o.append(topst(T([(167, 90), (380, 93), (596, 90)], ox)))
    for bx in (185, 380, 578):          # belt loops
        o.append(path(T([(bx - 7, 38), (bx + 7, 38), (bx + 7, 102), (bx - 7, 102)], ox), close=True, fill=DENIM_LT))
    # yoke (V to CB) + CB seam
    o.append(path(T([(150, 135), (380, 168), (612, 135)], ox))); o.append(topst(T([(150, 141), (380, 174), (612, 141)], ox)))
    o.append(path(T([(380, 98), (380, 470)], ox))); o.append(topst(T([(386, 168), (386, 465)], ox)))
    # back pockets (pentagon) + double topstitch + rivets
    for x0, x1 in ((160, 340), (423, 603)):
        cx = (x0 + x1) / 2
        pk = [(x0, 183), (x1, 183), (x1 - 8, 352), (cx, 372), (x0 + 8, 352)]
        o.append(path(T(pk, ox), close=True, fill=DENIM_LT))
        o.append(topst(T([(x0, 198), (x1, 198)], ox)))
        inner = Polygon(T(pk, ox)).buffer(-2.0, join_style="mitre")
        o.append(path(list(inner.exterior.coords), STITCH, 0.35, "1.2 0.8"))
        for rx, sg in ((x0 + 3, 1), (x1 - 3, -1)):      # bartacks at the top corners (founder 19 Oct, as HI): 8 mm, along the pocket side
            o.append(f'<line x1="{f(X(rx))}" y1="{f(Y(185))}" x2="{f(X(rx + sg * 0.4))}" y2="{f(Y(185) + 10)}" stroke="#B4B4B8" stroke-width="2.4" stroke-linecap="round"/>')
    # inseam / crotch hint
    o.append(path(T([(380, 470), (372, 500)], ox)))
    return "\n".join(o), P.bounds

def front_svg(sil):
    ox = 760
    P = affinity.translate(affinity.scale(sil, MM, MM, origin=(0, 0)), -ox * MM, 0)
    o = [f'<path d="{geom_to_path(P)}" fill="{DENIM}" stroke="{INK}" stroke-width="0.7"/>']
    o.append(path(T([(886, 95), (1105, 98), (1322, 95)], ox)))
    o.append(topst(T([(888, 51), (1105, 53), (1320, 51)], ox))); o.append(topst(T([(887, 90), (1105, 93), (1321, 90)], ox)))
    for bx in (1040, 1190):
        o.append(path(T([(bx - 7, 42), (bx + 7, 42), (bx + 7, 104), (bx - 7, 104)], ox), close=True, fill=DENIM_LT))
    # shank button + fly (zip fly, founder 19 Oct: YKK #4.5 close-end, 6 in; J topstitch) + CF
    o.append(f'<circle cx="{f((1112 - ox) * MM)}" cy="{f(72 * MM)}" r="8.5" fill="#1E1E20" stroke="#8A8A8E" stroke-width="0.4"/>')
    o.append(path(T([(1105, 98), (1100, 470)], ox)))
    o.append(topst(T(bez((1075, 98), (1072, 250), (1070, 330), (1100, 368)), ox)))
    zt, zb = 100 * MM, 100 * MM + 152.4             # 6 in zip under the fly (hidden, shown dashed) + slider at the top
    o.append(f'<line x1="{f((1092 - ox) * MM)}" y1="{f(zt)}" x2="{f((1092 - ox) * MM)}" y2="{f(zb)}" stroke="{STITCH}" stroke-width="1.6" stroke-dasharray="0.5 0.5"/>')
    o.append(f'<rect x="{f((1092 - ox) * MM - 2.2)}" y="{f(zt + 1)}" width="4.4" height="7" rx="1" fill="none" stroke="{STITCH}" stroke-width="0.35" stroke-dasharray="0.8 0.6"/>')
    # front pockets: wearer's right (image left) scoop with the coin pocket; wearer's left scoop
    o.append(path(T(bez((1012, 96), (995, 170), (940, 215), (868, 232)), ox)))
    o.append(topst(T(bez((1020, 96), (1003, 175), (946, 222), (870, 240)), ox)))
    o.append(path(T(bez((1198, 96), (1215, 160), (1270, 190), (1338, 200)), ox)))
    o.append(topst(T(bez((1190, 96), (1207, 166), (1264, 197), (1340, 208)), ox)))
    for rx, ry in ((1016, 130), (1200, 128)):
        o.append(f'<circle cx="{f((rx - ox) * MM)}" cy="{f(ry * MM)}" r="2.2" fill="#1E1E20" stroke="#8A8A8E" stroke-width="0.3"/>')
    o.append(path(T([(1100, 470), (1092, 500)], ox)))
    return "\n".join(o), P.bounds

# garment positions (mm, on these flats) of the embroidery, for placement drawings: x from the flat's left edge of each view
COIN_TL_PX = (902, 122)        # coin-pocket patch top-left on the front flat (px)
WB_TL_PX = (478, 37)           # waistband patch top-left on the back flat (px)
