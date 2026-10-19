"""Front-leg konpeito trail — PROPOSED placement map + PROPOSED stitch files (the founder's artwork is MISSING).

Traced from the front flat (1792127150159_image.png, ~1 px per mm): every coloured candy star on the wearer's right
front leg. The black soot-sprite characters in that trail are a licensed-character lookalike (LESSONS A7): not traced,
not drawn, left for the founder's original artwork. Scale: the flat's waistband (432 px) = half relaxed waist of size 32
(33.1 in / 2 = 420 mm) -> 0.97 mm/px, PROPOSED. Stars are 10 mm (same size as every konpeito star on the jean)."""
import json, math
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
import kjcore
import classify as CL
import kjart as KA

SRC = "inputs/1792127150159_image.png"
MMPX = 420.0 / 432.0          # PROPOSED scale (size 32)
WAIST_Y = 40                  # px row of the front waistband top
SIDE_KO = 12.0                # keep-out: finished side seam + topstitch + 3 mm
STAR_D = KA.STAR_D
COLS = {"pink": ("kj_pink", "kj_pink_hi"), "blue": ("kj_blue", "kj_blue_hi"), "yellow": ("kj_yellow", "kj_yellow_hi")}

def trace():
    a = np.asarray(Image.open(SRC).convert("RGB")).astype(float)
    h, s, v = CL.hsv(a)
    m = (s > 0.45) & (v > 0.5) & (((h > 300) | (h < 15)) | ((h > 180) & (h < 215)) | ((h > 35) & (h < 65)))
    m[:, :770] = False; m[:, 1000:] = False
    m[60:186, 893:992] = False                         # the coin-pocket patch + its konpeito (elements 01/02)
    dark = v < 0.42
    lab, n = ndi.label(ndi.binary_dilation(m, iterations=1))
    stars = []
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        mm = lab[sl] == i
        if mm.sum() < 6: continue
        ys, xs = np.nonzero(mm); cy, cx = ys.mean() + sl[0].start, xs.mean() + sl[1].start
        hh = float(np.median(h[sl][mm]))
        col = "pink" if (hh > 300 or hh < 15) else "blue" if 180 < hh < 215 else "yellow"
        row = int(round(cy)); edge = np.nonzero(dark[row, 760:1000])[0]
        ex = (edge.min() + 760) if len(edge) else 790
        x_side = (cx - ex) * MMPX; y_wb = (cy - WAIST_Y) * MMPX
        moved = None
        if x_side - STAR_D / 2 < SIDE_KO:
            moved = round(SIDE_KO + STAR_D / 2 - x_side, 1); x_side = SIDE_KO + STAR_D / 2
        stars.append(dict(col=col, px=(round(cx, 1), round(cy, 1)), size_px=int(sl[1].stop - sl[1].start),
                          x_from_side_mm=round(x_side, 1), y_from_waist_mm=round(y_wb, 1), moved_in_mm=moved))
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
        g, hi = KA.puffy_star(d["x_from_side_mm"], d["y_from_waist_mm"], STAR_D, rot=0)
        vis += [KA.radial_region(base, g, "STAR", (d["x_from_side_mm"], d["y_from_waist_mm"])),
                KA.radial_region(tint, hi, "STAR-hi", (hi.centroid.x, hi.centroid.y))]
    return vis

if __name__ == "__main__":
    st = trace(); secs = sections(st)
    json.dump(dict(stars=st, sections=[[d["id"] for d in s] for s in secs], mm_per_px=MMPX), open("out/front_stars.json", "w"), indent=1)
    for d in st: print(d)
    print([[d["id"] for d in s] for s in secs])
