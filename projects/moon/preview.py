"""Stitch-style previews of the composed art on the pattern pieces (size given, default M), + mockup side by side.
usage: ./py.sh preview.py [SIZE] [ppm]  -> out/preview_<SIZE>.png, out/compare_<SIZE>.png"""
import sys, pickle, os
from PIL import Image, ImageDraw
import moonpal, scene, stitchrender as SR, pattern as PT
from shapely.ops import unary_union

def piece_img(vis, poly, ppm, extra=None, pad=12):
    b = poly.bounds; bb = (b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad)
    img = SR.render(vis, bb, ppm, base=moonpal.FABRIC)
    T = lambda cs: [((x - bb[0]) * ppm, (y - bb[1]) * ppm) for x, y in cs]
    mask = Image.new("L", img.size, 0); ImageDraw.Draw(mask).polygon(T(poly.exterior.coords), fill=255)
    out = Image.new("RGB", img.size, (255, 255, 255)); out.paste(img, (0, 0), mask)
    d = ImageDraw.Draw(out); d.line(T(poly.exterior.coords), fill=(40, 40, 60), width=2)
    if extra: extra(d, T)
    return out

def render_size(size, ppm=2.0, art=None, graded=None):
    art = art or scene.art_for_size(size); graded = graded or scene.graded_art()
    g, mt = PT.draft(size); info = art["info"]
    def box_draw(d, T):
        x0, y0, x1, y1 = info["box"]
        d.line(T([(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]), fill=(255, 60, 160), width=3)
        d.line(T([(x0, y0), (x1, y1)]), fill=(255, 60, 160), width=1); d.line(T([(x1, y0), (x0, y1)]), fill=(255, 60, 160), width=1)
    bk = piece_img(art["back"], g["B01"].sew_poly(), ppm, box_draw)
    fl = piece_img(art["F03L"] + (graded["02L"] if size == "M" else []), g["F01"].sew_poly(), ppm)
    fr = piece_img(art["F03R"] + (graded["02R"] if size == "M" else []), g["F02"].sew_poly(), ppm)
    s1 = piece_img(graded["04R"], g["S01"].sew_poly(), ppm); s2 = piece_img(graded["04L"], g["S02"].sew_poly(), ppm)
    W = fr.width + fl.width + bk.width + 40; H = max(bk.height, fl.height) + max(s1.height, s2.height) + 30
    sheet = Image.new("RGB", (W, H), (255, 255, 255))
    sheet.paste(fr, (0, 0)); sheet.paste(fl, (fr.width, 0)); sheet.paste(bk, (fr.width + fl.width + 40, 0))
    y2 = max(bk.height, fl.height) + 30
    sheet.paste(s1, (0, y2)); sheet.paste(s2, (s1.width + 20, y2))
    os.makedirs("out", exist_ok=True); sheet.save(f"out/preview_{size}.png")
    return sheet, bk, fl, fr

if __name__ == "__main__":
    size = sys.argv[1] if len(sys.argv) > 1 else "M"; ppm = float(sys.argv[2]) if len(sys.argv) > 2 else 2.0
    sheet, bk, fl, fr = render_size(size, ppm)
    # compare: mockup back | our back ; mockup front | our front (fronts joined at CF)
    mb = Image.open("inputs/back.png").convert("RGB"); mf = Image.open("inputs/front.png").convert("RGB")
    h = 700
    def fit(im): return im.resize((int(im.width * h / im.height), h))
    front = Image.new("RGB", (fr.width + fl.width, max(fr.height, fl.height)), (255, 255, 255)); front.paste(fr, (0, 0)); front.paste(fl, (fr.width, 0))
    ims = [fit(mf), fit(front), fit(mb), fit(bk)]
    cmp_ = Image.new("RGB", (sum(i.width for i in ims) + 30, h), (255, 255, 255)); x = 0
    for i in ims: cmp_.paste(i, (x, 0)); x += i.width + 10
    cmp_.save(f"out/compare_{size}.png"); print("ok", sheet.size)
