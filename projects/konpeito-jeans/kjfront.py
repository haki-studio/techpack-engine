"""Front-leg konpeito stars (07) — PROPOSED placement map + PROPOSED stitch files (the front-leg artwork is to follow).

Rev B (founder review 20 Oct, item 15): the map is re-derived from the garment mockup (1792127150159_image.png) with the
math written into out/front_stars.json["derivation"] and drawn on out/check_07_mockup.png (the pack's C5 page):
  scale   = half relaxed waist of size 32 (33.1 in / 2 = 420.4 mm) / the front waistband width on the mockup, measured on
            the traced silhouette at the waistband's mid-height (px)            -> mm per px
  origin  = top of the waistband at the side seam (wearer's right, image left); y straight down, x in from the side seam
            (the silhouette edge at the star's own height)
  pocket  = the front scoop-pocket opening, traced from the mockup at 5x zoom on a 10 px grid (POCKET_OPENING_PX)
  check   = every star centre must lie BELOW the opening (outside the pocket mouth); the gap is reported per star.
Stars are 10 mm (same size as every konpeito star on the jean)."""
import json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
from shapely.geometry import box, LineString, Point, Polygon
import kjcore
import classify as CL
import kjart as KA
import kjflat as FL

SRC = "inputs/1792127150159_image.png"
HALF_WAIST_MM = 33.1 * 25.4 / 2          # size 32 relaxed waist (HI chart, T3) / 2 = 420.4 mm (the flat shows the front half)
SIDE_KO = 12.0                           # keep-out: finished side seam + topstitch + 3 mm
STAR_D = KA.STAR_D
COLS = {"pink": ("kj_pink", "kj_pink_hi"), "blue": ("kj_blue", "kj_blue_hi"), "yellow": ("kj_yellow", "kj_yellow_hi")}
# front scoop-pocket opening (wearer's right), mockup px, from the side seam to the rivet under the waistband:
# read on the mockup at 5x zoom with a 10 px grid (out/check_07_pocket_grid.png). The coin-pocket patch sits INSIDE it.
POCKET_OPENING_PX = FL.OPENING_PX

def geometry():
    sil = FL.silhouettes()["front"]
    wb_top = min(y for x, y in sil.exterior.coords)
    wb_bot = 88.0                                              # waistband lower seam at the side (mockup px, grid read)
    ymid = (wb_top + wb_bot) / 2
    row = sil.intersection(box(0, ymid - 0.3, 3000, ymid + 0.3)).bounds
    wb_w = row[2] - row[0]
    mmpx = HALF_WAIST_MM / wb_w
    top = sil.intersection(box(0, wb_top + 3.7, 3000, wb_top + 4.3)).bounds   # side seam x at the WB top
    origin = (top[0], wb_top)
    return dict(sil=sil, wb_top=wb_top, wb_mid=ymid, wb_w_px=wb_w, mmpx=mmpx, origin=origin)

def side_x(sil, y):
    r = sil.intersection(box(0, y - 0.3, 3000, y + 0.3))
    return r.bounds[0]

def opening_y(x):
    xs = [p[0] for p in POCKET_OPENING_PX]; ys = [p[1] for p in POCKET_OPENING_PX]
    if x < xs[0] or x > xs[-1]: return None
    return float(np.interp(x, xs, ys))

def trace(G):
    a = np.asarray(Image.open(SRC).convert("RGB")).astype(float)
    h, s, v = CL.hsv(a)
    m = (s > 0.45) & (v > 0.5) & (((h > 300) | (h < 15)) | ((h > 180) & (h < 215)) | ((h > 35) & (h < 65)))
    m[:, :770] = False; m[:, 1000:] = False
    m[60:186, 893:992] = False                         # the coin-pocket patch + its konpeito (elements 01/02)
    lab, n = ndi.label(ndi.binary_dilation(m, iterations=1))
    mmpx = G["mmpx"]; oy = G["wb_top"]
    stars = []
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        mm = lab[sl] == i
        if mm.sum() < 6: continue
        ys, xs = np.nonzero(mm); cy, cx = ys.mean() + sl[0].start, xs.mean() + sl[1].start
        hh = float(np.median(h[sl][mm]))
        col = "pink" if (hh > 300 or hh < 15) else "blue" if 180 < hh < 215 else "yellow"
        ex = side_x(G["sil"], cy)
        x_side = (cx - ex) * mmpx; y_wb = (cy - oy) * mmpx
        x_mock = x_side
        moved = None
        if x_side - STAR_D / 2 < SIDE_KO:
            moved = round(SIDE_KO + STAR_D / 2 - x_side, 1); x_side = SIDE_KO + STAR_D / 2
        oyp = opening_y(cx)
        gap = None if oyp is None else round((cy - oyp) * mmpx - STAR_D / 2, 1)    # star top edge below the opening, mm
        stars.append(dict(col=col, px=(round(cx, 1), round(cy, 1)), size_px=int(sl[1].stop - sl[1].start), side_px=round(ex, 1),
                          x_mockup_mm=round(x_mock, 1), x_from_side_mm=round(x_side, 1), y_from_waist_mm=round(y_wb, 1),
                          moved_in_mm=moved, below_opening_mm=gap,
                          inside_opening=bool(oyp is not None and cy < oyp)))
    stars.sort(key=lambda d: d["y_from_waist_mm"])
    for k, d in enumerate(stars, 1): d["id"] = f"S{k:02d}"
    return stars

def sections(stars, frame=None):
    """group stars into hoopings that fit the factory frame (largest frame - 16 mm margin)."""
    import factory
    fw, fh = factory.largest_frame()
    lim = min(fw, fh) - 16.0 - STAR_D
    secs = []
    for d in stars:
        if secs and d["y_from_waist_mm"] - secs[-1][0]["y_from_waist_mm"] <= lim:
            xs = [q["x_from_side_mm"] for q in secs[-1]] + [d["x_from_side_mm"]]
            if max(xs) - min(xs) <= lim: secs[-1].append(d); continue
        secs.append([d])
    return secs

def section_vis(sec):
    """regions for one hooping, in leg mm (x from side seam, y from waistband top)."""
    vis = []
    for d in sec:
        base, tint = COLS[d["col"]]
        import kjsvg          # founder change 20 Oct: the 02 facing konpeito, same digitising, 10 mm
        vis += kjsvg.konpeito_regions(base, d["x_from_side_mm"], d["y_from_waist_mm"], STAR_D)
    return vis

def overlay(G, stars, out="out/check_07_mockup.png", s=3):
    """the corrected map drawn back onto the mockup: WB scale line, origin, pocket opening, star centres + ids."""
    im = Image.open(SRC).convert("RGB")
    x0, y0, x1, y1 = 790, 20, 1080, 920
    c = im.crop((x0, y0, x1, y1)).resize(((x1 - x0) * s, (y1 - y0) * s), Image.LANCZOS)
    d = ImageDraw.Draw(c)
    try: fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
    except Exception: fnt = ImageFont.load_default()
    P = lambda x, y: ((x - x0) * s, (y - y0) * s)
    # waistband scale line (clipped to the crop) + origin
    d.line([P(G["origin"][0], G["wb_mid"]), P(x1, G["wb_mid"])], fill=(0, 200, 255), width=3)
    d.text(P(G["origin"][0] + 40, G["wb_mid"] - 14), f"WB width {G['wb_w_px']:.1f} px = 420.4 mm", fill=(0, 200, 255), font=fnt)
    ox, oy = P(*G["origin"]); d.ellipse([ox - 9, oy - 9, ox + 9, oy + 9], outline=(0, 255, 0), width=4)
    d.text((ox + 12, oy + 2), "O (0,0)", fill=(0, 255, 0), font=fnt)
    d.line([P(*p) for p in POCKET_OPENING_PX], fill=(255, 140, 0), width=5)
    d.text(P(1026, 160), "pocket\nopening", fill=(255, 140, 0), font=fnt)
    for st in stars:
        cx, cy = P(*st["px"]); r = STAR_D / G["mmpx"] / 2 * s
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255), width=3)
        d.text((cx + r + 4, cy - 12), st["id"], fill=(255, 255, 255), font=fnt)
    c.save(out)
    # grid used to read the pocket opening (kept as evidence)
    x0g, y0g, x1g, y1g = 840, 30, 1060, 240; sg = 5
    g = im.crop((x0g, y0g, x1g, y1g)).resize(((x1g - x0g) * sg, (y1g - y0g) * sg), Image.NEAREST); dg = ImageDraw.Draw(g)
    for x in range(x0g, x1g, 10): dg.line([((x - x0g) * sg, 0), ((x - x0g) * sg, g.height)], fill=(0, 255, 0) if x % 50 == 0 else (0, 90, 0))
    for y in range(y0g, y1g, 10): dg.line([(0, (y - y0g) * sg), (g.width, (y - y0g) * sg)], fill=(0, 255, 0) if y % 50 == 0 else (0, 90, 0))
    dg.line([((x - x0g) * sg, (y - y0g) * sg) for x, y in POCKET_OPENING_PX], fill=(255, 140, 0), width=3)
    g.save("out/check_07_pocket_grid.png")

if __name__ == "__main__":
    G = geometry(); st = trace(G); secs = sections(st)
    der = dict(half_waist_mm=round(HALF_WAIST_MM, 1), wb_width_px=round(G["wb_w_px"], 1), wb_mid_row_px=G["wb_mid"],
               mm_per_px=round(G["mmpx"], 4), origin_px=[round(v, 1) for v in G["origin"]],
               pocket_opening_px=POCKET_OPENING_PX,
               pocket_opening_mm=[[round((x - G["origin"][0]) * G["mmpx"], 1), round((y - G["wb_top"]) * G["mmpx"], 1)] for x, y in POCKET_OPENING_PX],
               stars_inside_opening=[d["id"] for d in st if d["inside_opening"]])
    json.dump(dict(stars=st, sections=[[d["id"] for d in s] for s in secs], mm_per_px=G["mmpx"], derivation=der),
              open("out/front_stars.json", "w"), indent=1)
    overlay(G, st)
    print(json.dumps(der, indent=1))
    for d in st: print(d)
    print([[d["id"] for d in s] for s in secs])
