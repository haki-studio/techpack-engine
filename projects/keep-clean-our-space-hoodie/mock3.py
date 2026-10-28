"""Rev M (2026-10-27, Nick approved "Mockups 3"): read the star field off the approved mockup and map every star to its
spot on the pattern pieces. usage: python3 mock3.py [SIZE] -> out/pv/<SIZE>/mock3_targets.json (+ overlay PNG)

The mockup (2403 x 1255 px, front view x 49-1176, back view x 1205-2350) is NOT to scale: its body is ~1.4x taller than
wide, our Come Over block is about square. So positions are mapped by PROPORTION inside each panel's landmarks, never by
one px->mm factor:
- body (front / back): y from the HPS line to the hem-rib seam (shoulder point = 45 mm below HPS fixes the scale),
  x as a share of the body half width at the hem rib, times the block's net half width at that height.
- kangaroo pocket: share of the mockup pocket trapezoid -> the block pocket trapezoid.
- sleeves: share along the sleeve (shoulder point -> cuff seam) and across it (outer fold = sleeve centre line ->
  underarm seam). Front view = front half of the sleeve, back view = back half.
- hood: back view by share from the hood CB seam to the silhouette; front view = the strip just behind the face turn-back.
Stars come from the bright-blob detector (missions/kcos-hoodie-pivot/revm/det2.py); badge / script / hood-V glint pixels
are excluded. A blob >= 6 px on its longer side is a plus star (SPK), smaller is a dot."""
import sys, json, os, math
import numpy as np
from shapely.geometry import Polygon, Point, LineString
import pv_block as B

SIZE = next((a for a in sys.argv[1:] if a in B.CHART), "M")
MOCK = "/mnt/c/Users/devin/Desktop/HakiStop/Designs/Playtime/Keep Clean Our Space/Mockups 3.png"
STARS = "inputs/mockups-3-stars.json"   # from inputs/mockups-3-det2.py (bright-blob detector on Mockups 3)
OUT = f"out/pv/{SIZE}"; os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------------ landmarks (mockup px, read off the 50 px grid)
EXCL = [(1470, 340, 1760, 570), (1510, 605, 1660, 890), (1790, 830, 2075, 915), (1895, 370, 2110, 630),   # JP CN KR EN
        (625, 985, 880, 1015), (596, 285, 626, 310)]                                                       # script, hood-V
BADGE_BOX = {"01": (1470, 340, 1760, 570), "02": (1895, 370, 2110, 630), "03": (1510, 605, 1660, 890), "04": (1790, 830, 2075, 915)}
FRONT = dict(cx=617, half=306, hps=232, hem=1032, shoulder_pt=294)          # hem rib 319-931 at y 1100
BACK = dict(cx=1783, half=325, hps=238, hem=1035, shoulder_pt=300)         # hem rib 1458-2108 at y 1100
POCKET = [(431, 737), (800, 737), (910, 1032), (327, 1032)]                 # top L, top R, bottom R, bottom L
HOOD_F = Polygon([(400, 205), (437, 56), (812, 50), (850, 205), (700, 281), (606, 306), (525, 275)])
HOOD_B = Polygon([(1531, 206), (1575, 50), (1781, 25), (1987, 50), (2031, 206), (1950, 306), (1781, 340), (1612, 306)])
HOOD_B_CB, HOOD_B_TOP, HOOD_B_BOT = 1781, 25, 330
CUFF = dict(front=1119, back=1100)                                          # sleeve / cuff-rib seam

mask = None
def silhouette(y, x0, x1):
    """outer garment edge on a row, scanning from x0 towards x1"""
    global mask
    if mask is None:
        from PIL import Image
        from scipy import ndimage as nd
        g = np.array(Image.open(MOCK).convert("L")).astype(float)
        m = nd.binary_opening(nd.binary_closing(g < 150, iterations=2), iterations=2)
        lab, n = nd.label(m); sz = nd.sum(m, lab, range(1, n + 1)); mask = nd.binary_fill_holes(np.isin(lab, np.argsort(sz)[-2:] + 1))
    row = mask[int(round(y))]; step = 1 if x1 > x0 else -1
    for x in range(x0, x1, step):
        if row[x]: return x
    return x1

net = {P: g.buffer(-B.SA, join_style=2) for P, g in B.pieces(SIZE).items()}
def half_w(P, y):
    b = net[P].bounds; seg = net[P].intersection(LineString([(b[0] - 5, y), (b[2] + 5, y)]))
    return (seg.bounds[2] - seg.bounds[0]) / 2 if not seg.is_empty else None

m = B.poms(SIZE); L = m["body_length"] - B.P["rib_hem"]
SLV_LEN = m["sleeve"] - B.P["rib_cuff"] + B.P["cap_h"]
HW_CAP = math.hypot(m["shoulder"] / 2 - m["chest"] / 2, B.P["armhole"]) + 8.0

def body(v, x, y):
    yy = (y - v["hps"]) / (v["shoulder_pt"] - v["hps"]) * B.P["shoulder_drop"]
    yy = (y - v["hps"]) * (L - B.P["shoulder_drop"]) / (v["hem"] - v["shoulder_pt"])
    hw = half_w("FR" if v is FRONT else "BK", min(max(yy, 1), L - 1)) or m["chest"] / 2
    return (x - v["cx"]) / v["half"] * hw, yy

def pocket(x, y):
    (tlx, ty), (trx, _), (brx, by), (blx, _) = POCKET
    v = (y - ty) / (by - ty); l = tlx + (blx - tlx) * v; r = trx + (brx - trx) * v
    u = (x - (l + r) / 2) / ((r - l) / 2)
    w = B.P["pocket_top"] / 2 + (B.P["pocket_bot"] - B.P["pocket_top"]) / 2 * v
    return u * w, v * B.P["pocket_h"]

def sleeve(view, side, x, y):
    """side = 'L' / 'R' of the image. The outer edge is the sleeve fold (centre line), the inner edge the underarm."""
    V = FRONT if view == "front" else BACK
    v = min(max((y - V["shoulder_pt"]) / (CUFF[view] - V["shoulder_pt"]), 0), 1)
    if side == "L":
        xo = silhouette(y, 0 if view == "front" else 1195, 2403); xi = V["cx"] - V["half"]
    else:
        xo = silhouette(y, 1194 if view == "front" else 2402, 0); xi = V["cx"] + V["half"]
    u = min(max(abs(x - xo) / max(abs(xi - xo), 1), 0), 1)
    hw = HW_CAP + (B.P["cuff_half"] - HW_CAP) * v
    # front view: image L = wearer's right sleeve (SR); back view: image L = wearer's left (SL).
    P = {("front", "L"): "SR", ("front", "R"): "SL", ("back", "L"): "SL", ("back", "R"): "SR"}[(view, side)]
    # SL is SR mirrored; front half of SR = -x, front half of SL = +x [proposed: single notch = front]
    sgn = (-1 if P == "SR" else 1) * (1 if view == "front" else -1)
    return P, sgn * u * hw, v * SLV_LEN

def hood_back(x, y):
    P = "HL" if x < HOOD_B_CB else "HR"          # back view mirrors: image left = wearer's left
    edge = silhouette(y, 1195 if x < HOOD_B_CB else 2402, HOOD_B_CB)
    u = min(abs(x - HOOD_B_CB) / max(abs(edge - HOOD_B_CB), 1), 1)
    hx = B.P["hood_w"] - u * (B.P["hood_w"] - 110.0)                 # silhouette edge = ~110 mm behind the face [proposed]
    hy = (y - HOOD_B_TOP) / (HOOD_B_BOT - HOOD_B_TOP) * B.P["hood_h"]
    return P, (hx if P == "HR" else -hx), hy

def hood_front(x, y):
    P = "HR" if x < 617 else "HL"                # front view: image left = wearer's right
    hy = (y - 50) / (306 - 50) * B.P["hood_h"]
    return P, (70.0 if P == "HR" else -70.0), hy

def classify(s):
    x, y = s["x"], s["y"]
    if any(a <= x <= c and b <= y <= d for a, b, c, d in EXCL): return None
    if x < 1195:
        if HOOD_F.contains(Point(x, y)): return hood_front(x, y)
        if Polygon(POCKET).contains(Point(x, y)): return ("PK", *pocket(x, y))
        if abs(x - FRONT["cx"]) <= FRONT["half"] and y >= FRONT["hps"]: return ("FR", *body(FRONT, x, y))
        return sleeve("front", "L" if x < FRONT["cx"] else "R", x, y)
    if HOOD_B.contains(Point(x, y)): return hood_back(x, y)
    if abs(x - BACK["cx"]) <= BACK["half"] and y >= BACK["hps"]: return ("BK", *body(BACK, x, y))
    return sleeve("back", "L" if x < BACK["cx"] else "R", x, y)

def badge_targets():
    """badge centres on the back panel, mm (same proportional mapping as the stars)"""
    return {el: [round(v, 1) for v in body(BACK, (a + c) / 2, (b + d) / 2)] for el, (a, b, c, d) in BADGE_BOX.items()}

def script_target():
    a, b, c, d = EXCL[4]
    return [round(v, 1) for v in pocket((a + c) / 2, (b + d) / 2)]

if __name__ == "__main__":
    S = json.load(open(STARS)); out = []; dropped = []
    for s in S:
        r = classify(s)
        if r is None: dropped.append(s); continue
        P, x, y = r
        out.append(dict(piece=P, x=round(x, 1), y=round(y, 1), kind="SPK" if max(s["w"], s["h"]) >= 6 else "DOT",
                        px=[s["x"], s["y"]], size_px=max(s["w"], s["h"]), area_px=s["area"]))
    for k in ("SPK", "DOT"):                     # size rank inside each kind (0 = smallest)
        ks = sorted([o for o in out if o["kind"] == k], key=lambda o: (o["area_px"], o["size_px"]))
        for i, o in enumerate(ks): o["q"] = round((i + 0.5) / len(ks), 3)
    from collections import Counter
    res = dict(source=MOCK, detected=len(S), excluded=len(dropped), stars=len(out),
               per_piece=dict(Counter(o["piece"] for o in out)), per_kind=dict(Counter(o["kind"] for o in out)),
               badges_mm=badge_targets(), script_mm=script_target(), targets=out)
    json.dump(res, open(f"{OUT}/mock3_targets.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "targets"}))
