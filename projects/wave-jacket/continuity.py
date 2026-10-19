"""Per-seam continuity sheets: both sides of every seam the wave crosses, unrolled along the seam and butted together
(side A above, side B below, the 2 x 3 mm seam gap closed up as it is when sewn), rendered from the SHIPPED DSTs (or from
the art with --art for quick iteration). Match marks are drawn as red ticks on both strips.
usage: ./py.sh continuity.py [M] [--art]   ->  out/continuity_<seam>.png + out/continuity_M.png (all seams)"""
import wavecore as WC
import sys, json, pickle
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import map_coordinates
import wrap as WR, pieces as PC

size = next((a for a in sys.argv[1:] if not a.startswith("-")), "M")
ART = "--art" in sys.argv
PPM = 4.0; DEPTH = 45.0          # mm of each piece shown away from the seam

_IMG = {}
def piece_img(P):
    """(array HxWx3, bbox, ppm) of one piece in its own pattern coords"""
    if P not in _IMG:
        b = PC.panel(size, P).bounds; bb = (b[0] - 5, b[1] - 5, b[2] + 5, b[3] + 5)
        if ART:
            from motifs2 import HEX
            D = pickle.load(open(f"art_{size}.pkl", "rb"))
            im = Image.new("RGB", (int((bb[2]-bb[0])*PPM), int((bb[3]-bb[1])*PPM)), WC.FABRIC); dr = ImageDraw.Draw(im)
            for r in sorted(D[P], key=lambda r: r.get("layer", 0)):
                for q in WR.polys_of(r["geom"]):
                    dr.polygon([((x-bb[0])*PPM, (y-bb[1])*PPM) for x, y in q.exterior.coords], fill=HEX[r["col"]])
                    for h in q.interiors: dr.polygon([((x-bb[0])*PPM, (y-bb[1])*PPM) for x, y in h.coords], fill=WC.FABRIC)
        else:
            import compare as C
            im = C.dst_render(P, bb, PPM)
        _IMG[P] = (np.asarray(im.convert("RGB")).astype(float), bb)
    return _IMG[P]

def strip(side, flip):
    """unrolled band of one side: rows = distance from the seam line (0 .. DEPTH), cols = arc length along the seam"""
    a, bb = piece_img(side.P); L = side.L
    ss = np.arange(0, L, 1.0 / PPM); ds = np.arange(WR.GAP, WR.GAP + DEPTH, 1.0 / PPM)
    P = np.array([[side.point(s / L, d) for s in ss] for d in ds])          # (nd, ns, 2)
    cx = (P[..., 0] - bb[0]) * PPM; cy = (P[..., 1] - bb[1]) * PPM
    out = np.stack([map_coordinates(a[..., k], [cy, cx], order=1, mode="nearest") for k in range(3)], -1)
    if flip: out = out[::-1]
    return out.clip(0, 255).astype(np.uint8)

def sheet(sm, marks):
    A, B = WR.SeamSide(size, sm, "A"), WR.SeamSide(size, sm, "B")
    sa, sb = strip(A, True), strip(B, False)
    w = max(sa.shape[1], sb.shape[1])
    # B is resampled to A's length (the seam is eased: same fraction s = same point when sewn)
    sbr = np.asarray(Image.fromarray(sb).resize((sa.shape[1], sb.shape[0]), Image.BILINEAR))
    im = Image.new("RGB", (sa.shape[1] + 20, sa.shape[0] + sbr.shape[0] + 60), "white")
    im.paste(Image.fromarray(sa), (10, 30)); im.paste(Image.fromarray(sbr), (10, 30 + sa.shape[0] + 2))
    d = ImageDraw.Draw(im); y0 = 30 + sa.shape[0]
    d.line([(10, y0 + 1), (10 + sa.shape[1], y0 + 1)], fill=(255, 255, 255), width=1)
    for m in (marks or {}).get("s_mm", []):
        x = 10 + m * PPM; d.line([(x, y0 - 14), (x, y0 + 16)], fill=(230, 40, 40), width=2)
    for k in range(0, int(A.L) + 1, 50):
        x = 10 + k * PPM; d.line([(x, y0 + sbr.shape[0] + 2), (x, y0 + sbr.shape[0] + 8)], fill=(0, 0, 0)); d.text((x + 2, y0 + sbr.shape[0] + 8), f"{k}", fill=(0, 0, 0))
    src = "art" if ART else "shipped DSTs"
    d.text((10, 8), f"{sm['name']} (size {size}, {src}) — above: {A.P} {A.L:.0f} mm, below: {B.P} {B.L:.0f} mm (eased to the same length), seam closed up; red = match marks", fill=(0, 0, 0))
    return im

if __name__ == "__main__":
    D = pickle.load(open(f"art_{size}.pkl", "rb")); MK = D.get("marks", {})
    ims = []
    for sm in WR.seams(size):
        im = sheet(sm, MK.get(sm["name"])); nm = sm["name"].replace(" ", "_")
        im.save(f"out/continuity_{nm}.png"); ims.append(im); print(sm["name"], im.size)
    W = max(i.width for i in ims); H = sum(i.height for i in ims) + 10 * len(ims)
    allim = Image.new("RGB", (W, H), "white"); y = 0
    for i in ims: allim.paste(i, (0, y)); y += i.height + 10
    allim.save(f"out/continuity_{size}{'_art' if ART else ''}.png"); print("sheet", allim.size)
