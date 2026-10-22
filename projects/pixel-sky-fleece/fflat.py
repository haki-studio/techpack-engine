"""Coloured flats drawn FROM THE PATTERN (size M): front + back panels filled with their jacquard cell maps, sleeves
hanging from the shoulder point (visible half = front half on the front view, back half on the back view), stand
collar, navy bindings, CF zip, pocket zips, embroidery from the stitch art. Garment mm -> PNG at PPM px/mm.
Front view: front coords (x from CF, + = wearer's left = viewer's right). Back view: back coords (+ = wearer's right =
viewer's right on a back view)."""
import math, pickle
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Polygon, LineString
from shapely import affinity
import fleece as FL, jacquard as JQ, pattern as PT, pixels as PX

PPM = 2.0
NAVY, ZIPC, PULL, SKYC, CREAMC, TASLAN = (27, 38, 66), (30, 30, 30), (110, 160, 240), JQ.COL[0], JQ.COL[1], JQ.COL[0]   # collar outer = sky taslan matched to the sky sherpa (founder 21 Oct)
ANG = math.radians(78)              # sleeve hangs 78 deg from horizontal (drop shoulder, as the mockup)
COLS = {"yellow": (246, 226, 58), "gold": (217, 165, 33), "black": (35, 31, 30)}

class Canvas:
    def __init__(self, bounds, ppm=PPM):
        self.b = bounds; self.ppm = ppm
        self.W, self.H = int((bounds[2] - bounds[0]) * ppm) + 1, int((bounds[3] - bounds[1]) * ppm) + 1
        self.im = Image.new("RGB", (self.W, self.H), (255, 255, 255)); self.d = ImageDraw.Draw(self.im)
    def T(self, pts): return [((x - self.b[0]) * self.ppm, (y - self.b[1]) * self.ppm) for x, y in pts]
    def poly(self, g, fill, outline=(40, 40, 40), w=1):
        for q in (g.geoms if hasattr(g, "geoms") else [g]):
            self.d.polygon(self.T(q.exterior.coords), fill=fill, outline=outline)
            for h in q.interiors: self.d.polygon(self.T(h.coords), fill=(255, 255, 255))
    def line(self, pts, col, w_mm): self.d.line(self.T(pts), fill=col, width=max(1, int(round(w_mm * self.ppm))))

def sleeve_tf(side, mt, view="front"):
    """sleeve pattern (x, y) -> garment view mm, solved from the pattern: the cap top (0, -h) sits on the shoulder point
    and the underarm point (W, 0) on the body's underarm point, so the cap follows the armhole; the sleeve top line
    (x = 0) is the outer silhouette and the visible half folds toward the body (|x|)."""
    h, W = mt["cap_h"], mt["W"]
    sp = np.array(mt["sp_f"] if view == "front" else mt["sp_b"], float); ua = np.array(mt["ua_f"] if view == "front" else mt["ua_b"], float)
    sp[0], ua[0] = abs(sp[0]), abs(ua[0])
    sx = -1 if side == "R" else 1                       # front view: wearer's right sleeve on the viewer's left
    if view == "back": sx = -sx
    v = ua - sp; th = math.atan2(v[1], v[0]) - math.atan2(W, h)     # rotation that maps (h, W) onto sp -> ua
    axis = np.array([math.cos(th), math.sin(th)]); perp = np.array([-math.sin(th), math.cos(th)])
    k = math.hypot(*v) / math.hypot(h, W)                           # small scale so the underarm lands exactly
    def f(x, y):
        p = sp + (axis * (y + h) + perp * abs(x) * k)
        return np.array([sx * p[0], p[1]])
    return f

def visible_half(pc, tf, half):
    """the half of a sleeve that faces the viewer (sign(x) == half), closed along the sleeve top line x = 0, in view mm"""
    from shapely.geometry import box as _box
    sp = pc.sew_poly(); b = sp.bounds
    hb = _box(0, b[1] - 1, b[2] + 1, b[3] + 1) if half > 0 else _box(b[0] - 1, b[1] - 1, 0, b[3] + 1)
    h = sp.intersection(hb)
    if h.geom_type != "Polygon": h = max(h.geoms, key=lambda q: q.area)
    return Polygon([tuple(tf(x, y)) for x, y in h.exterior.coords]).buffer(0)

def draw_panel_cells(C, P, tf=None, half=None):
    """paint a jacquard panel's cells (in panel coords, optionally transformed); half = +1/-1 keeps only that x side"""
    g = P["grid"]; C_ = JQ.CELL
    for r in range(g.shape[0]):
        j = P["j1"] - 1 - r; y0 = P["hem"] - (j + 1) * C_
        for c in range(g.shape[1]):
            v = g[r, c]
            if v == JQ.OUTSIDE: continue
            x0 = (P["i0"] + c) * C_
            if half is not None and np.sign(x0 + C_ / 2) != half: continue
            pts = [(x0, y0), (x0 + C_, y0), (x0 + C_, y0 + C_), (x0, y0 + C_)]
            if tf: pts = [tuple(tf(*p)) for p in pts]
            C.d.polygon(C.T(pts), fill=JQ.COL[v])

def mask_outside(C, keep):
    """white-out everything outside `keep` (union of shapes in view mm)"""
    m = Image.new("L", (C.W, C.H), 0); dm = ImageDraw.Draw(m)
    for q in (keep.geoms if hasattr(keep, "geoms") else [keep]):
        dm.polygon(C.T(q.exterior.coords), fill=255)
    white = Image.new("RGB", (C.W, C.H), (255, 255, 255)); C.im = Image.composite(C.im, white, m); C.d = ImageDraw.Draw(C.im)

def front(opt="A", size="M", emb=True):
    g, mt = FL.draft(size); art = pickle.load(open("out/art/art.pkl", "rb"))
    F01, F02 = g["F01"].sew_poly(), g["F02"].sew_poly()
    sleeves = {}
    for code, side in (("S01", "R"), ("S02", "L")):
        tf = sleeve_tf(side, mt); half = 1 if side == "R" else -1
        sew = g[code].sew(); fh = [p for p in sew]
        P = Polygon([tuple(tf(x, y)) for x, y in sew if np.sign(x + 1e-9) == half or abs(x) < 1e-6]).convex_hull
        sleeves[code] = (tf, half, visible_half(g[code], tf, half))
    U = F01.union(F02).union(sleeves["S01"][2]).union(sleeves["S02"][2])
    b = U.bounds; C = Canvas((b[0] - 30, b[1] - FL.COLLAR_H - 40, b[2] + 30, b[3] + 40))
    body = Canvas(C.b, C.ppm)
    for code in ("F01", "F02"): draw_panel_cells(body, JQ.panel(code, size, opt))
    for code, side in (("S01", "R"), ("S02", "L")):
        tf, half, poly = sleeves[code]
        layer = Canvas(C.b, C.ppm); draw_panel_cells(layer, JQ.panel(code, size), tf=tf, half=half)
        m = Image.new("L", (C.W, C.H), 0); ImageDraw.Draw(m).polygon(C.T(poly.exterior.coords), fill=255)
        C.im.paste(layer.im, (0, 0), m); C.d = ImageDraw.Draw(C.im); C.poly(poly, None)
        cuff = [tuple(tf(x, mt["Lu"] - 6)) for x in (0, half * mt["Ww"])] ; C.line(cuff, NAVY, 12)
        if emb and code == "S02":
            for col, geom, _ in art["E3"]:
                q = Polygon([tuple(tf(x, y)) for x, y in geom.exterior.coords]) if geom.geom_type == "Polygon" else None
                if q is not None: C.poly(q, COLS[col], outline=COLS[col])
    mb = Image.new("L", (C.W, C.H), 0); ImageDraw.Draw(mb).polygon(C.T(F01.union(F02).exterior.coords), fill=255)
    C.im.paste(body.im, (0, 0), mb); C.d = ImageDraw.Draw(C.im); C.poly(F01, None); C.poly(F02, None)
    # collar (stand, outer taslan) + piping + hem binding + zip + pockets
    neck = [(x, y) for x, y in g["F02"].edges[1].pts][::-1] + g["F01"].edges[1].pts[1:]
    neck = g["F02"].edges[1].pts[::-1][:-1] + g["F01"].edges[1].pts if False else None
    nl = [p for p in reversed(g["F02"].edges[1].pts)] + list(g["F01"].edges[1].pts)
    nl = sorted(set(nl), key=lambda p: p[0])
    top = [(x, y - FL.COLLAR_H) for x, y in nl]
    C.poly(Polygon(nl + top[::-1]).buffer(0), TASLAN)
    C.line(nl, NAVY, FL.PIPE_W)
    hem = mt["hem_f"]; ch = mt["block"].chest2
    C.line([(-ch, hem - 6), (ch, hem - 6)], NAVY, FL.BIND_W)
    C.line([(0, -FL.COLLAR_H + 4), (0, hem)], ZIPC, 9)
    C.d.rectangle([(-6 - C.b[0]) * C.ppm, (40 - C.b[1]) * C.ppm, (6 - C.b[0]) * C.ppm, (75 - C.b[1]) * C.ppm], fill=PULL)
    for side in (1, -1):
        t_, b_ = FL.pocket_line(size, side); C.line([t_, b_], NAVY, 7)
        C.d.rectangle([(t_[0] - 5 - C.b[0]) * C.ppm, (t_[1] - C.b[1]) * C.ppm, (t_[0] + 5 - C.b[0]) * C.ppm, (t_[1] + 40 - C.b[1]) * C.ppm], fill=PULL)
    if emb:
        for F in ("E2",) + (("E1",) if opt == "A" else ("E1B",)):
            for col, geom, _ in art[F]: C.poly(geom, COLS[col], outline=COLS[col])
    return C

def back(size="M"):
    g, mt = FL.draft(size); B = g["B01"].sew_poly(); sleeves = {}
    for code, side in (("S01", "R"), ("S02", "L")):
        tf = sleeve_tf(side, dict(mt, sp_b=mt["sp_b"]), view="back"); half = -1 if side == "R" else 1
        sleeves[code] = (tf, half, visible_half(g[code], tf, half))
    U = B.union(sleeves["S01"][2]).union(sleeves["S02"][2]); b = U.bounds
    C = Canvas((b[0] - 30, b[1] - FL.COLLAR_H - 40, b[2] + 30, b[3] + 40))
    body = Canvas(C.b, C.ppm); draw_panel_cells(body, JQ.panel("B01", size))
    for code, side in (("S01", "R"), ("S02", "L")):
        tf, half, poly = sleeves[code]
        layer = Canvas(C.b, C.ppm); draw_panel_cells(layer, JQ.panel(code, size), tf=tf, half=half)
        m = Image.new("L", (C.W, C.H), 0); ImageDraw.Draw(m).polygon(C.T(poly.exterior.coords), fill=255)
        C.im.paste(layer.im, (0, 0), m); C.d = ImageDraw.Draw(C.im); C.poly(poly, None)
        C.line([tuple(tf(x, mt["Lu"] - 6)) for x in (0, half * mt["Ww"])], NAVY, 12)
    mb = Image.new("L", (C.W, C.H), 0); ImageDraw.Draw(mb).polygon(C.T(B.exterior.coords), fill=255)
    C.im.paste(body.im, (0, 0), mb); C.d = ImageDraw.Draw(C.im); C.poly(B, None)
    nl = g["B01"].edges[0].pts; top = [(x, y - FL.COLLAR_H) for x, y in nl]
    C.poly(Polygon(list(nl) + top[::-1]).buffer(0), TASLAN); C.line(nl, NAVY, FL.PIPE_W)
    hem = mt["hem_b"]; ch = mt["block"].chest2; C.line([(-ch, hem - 6), (ch, hem - 6)], NAVY, FL.BIND_W)
    return C

def measure_key(size="M"):
    """numbered-point key for the size chart (TD PS-14): the front flat greyed, each point of measure drawn as a red line
    with its chart letter, at the pattern's own landmarks (HPS, shoulder / underarm points, hem, sleeve cap + cuff)."""
    from PIL import ImageFont
    C = front("A", size, emb=False); g, mt = FL.draft(size)
    C.im = Image.blend(C.im, Image.new("RGB", C.im.size, (255, 255, 255)), 0.55); C.d = ImageDraw.Draw(C.im)
    try: F = ImageFont.truetype("DejaVuSans-Bold.ttf", 30)
    except Exception: F = ImageFont.load_default()
    hps, sp, ua, hem, ch = mt["hps_f"], mt["sp_f"], mt["ua_f"], mt["hem_f"], mt["block"].chest2
    tf = sleeve_tf("R", mt); h, W, Ww, Lu = mt["cap_h"], mt["W"], mt["Ww"], mt["Lu"]
    pk = FL.pocket_line(size, 1)
    lines = {"A": [(hps[0], hps[1]), (hps[0], hem)], "B": [(-ch, ua[1]), (ch, ua[1])], "C": [(-sp[0], sp[1]), (sp[0], sp[1])],
             "D": [(-ch, hem - 3), (ch, hem - 3)], "E": [(sp[0], sp[1]), (ua[0], ua[1])], "J": [(-hps[0], hps[1]), (hps[0], hps[1])],
             "K": [(12, hps[1]), (12, 0)], "M": [(-hps[0] - 25, hps[1] + 5), (-hps[0] - 25, hps[1] + 5 - FL.COLLAR_H)],
             "G": [tuple(tf(0, -h)), tuple(tf(0, Lu))], "F": [tuple(tf(0, 25)), tuple(tf(W * 0.98, 25))],
             "H": [tuple(tf(0, Lu - 6)), tuple(tf(Ww, Lu - 6))], "R": [pk[0], pk[1]]}
    RED_ = (200, 30, 30)
    for k, pts in lines.items():
        P = C.T(pts); C.d.line(P, fill=RED_, width=5)
        for q in P: C.d.ellipse([q[0] - 6, q[1] - 6, q[0] + 6, q[1] + 6], fill=RED_)
        f = {"C": 0.3, "K": 0.8, "A": 0.6}.get(k, 0.5)                   # keep labels apart where lines cross at CF
        mx, my = P[0][0] + (P[-1][0] - P[0][0]) * f, P[0][1] + (P[-1][1] - P[0][1]) * f
        C.d.ellipse([mx - 22, my - 22, mx + 22, my + 22], fill=(255, 255, 255), outline=RED_, width=4)
        C.d.text((mx, my), k, fill=RED_, font=F, anchor="mm")
    return C

def labels_key(size="M"):
    """label positions on the back flat (T6): 1 main + size label and hanger loop at CB on the neck tape (inside),
    2 care / content / COO label in the wearer's left side seam, 100 mm above the hem [proposed]; back view: wearer's
    left = viewer's left."""
    from PIL import ImageFont
    C = back(size); g, mt = FL.draft(size); ch = mt["block"].chest2
    C.im = Image.blend(C.im, Image.new("RGB", C.im.size, (255, 255, 255)), 0.5); C.d = ImageDraw.Draw(C.im)
    try: F = ImageFont.truetype("DejaVuSans-Bold.ttf", 34)
    except Exception: F = ImageFont.load_default()
    RED_ = (200, 30, 30)
    for n, (x, y) in (("1", (0, 12)), ("2", (-ch, mt["hem_b"] - 100))):
        (px, py), = C.T([(x, y)])
        C.d.rectangle([px - 22, py - 10, px + 22, py + 10], outline=RED_, width=5)
        C.d.ellipse([px + 26, py - 52, px + 74, py - 4], fill=(255, 255, 255), outline=RED_, width=4)
        C.d.text((px + 50, py - 28), n, fill=RED_, font=F, anchor="mm")
    return C

if __name__ == "__main__":
    for opt in ("A", "B"): front(opt).im.save(f"out/flat_front_{opt}.png")
    back().im.save("out/flat_back.png"); measure_key().im.save("out/measure_key.png"); labels_key().im.save("out/labels_key.png"); print("ok")
