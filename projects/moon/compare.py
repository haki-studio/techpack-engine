"""Side-by-side sheets: mockup crop (x4 Lanczos) | stitch-style preview of our art, same scale.
usage: ./py.sh compare.py  -> out/compare_<element>.png"""
import pickle, sys
from PIL import Image, ImageDraw
import moonpal, stitchrender as SR

def sheet(name, mock_img, px_box, vis, mm_box, zooms=(), ppm=4.0):
    x0, y0, x1, y1 = mm_box
    ours = SR.render(vis, mm_box, ppm, base=moonpal.FABRIC)
    m = mock_img.crop(px_box).resize(ours.size, Image.LANCZOS)
    W = ours.width * 2 + 30; H = ours.height
    rows = [(m, ours)]
    for (zm, zp) in zooms:                       # (mm box, px box)
        o = SR.render(vis, zm, 10, base=moonpal.FABRIC); mm = mock_img.crop(zp).resize(o.size, Image.LANCZOS)
        rows.append((mm, o))
    Ht = sum(max(a.height, b.height) for a, b in rows) + 20 * len(rows)
    Wt = max(a.width + b.width for a, b in rows) + 30
    out = Image.new("RGB", (Wt, Ht), "white"); y = 0; d = ImageDraw.Draw(out)
    for a, b in rows:
        out.paste(a, (0, y)); out.paste(b, (a.width + 30, y)); y += max(a.height, b.height) + 20
    d.text((5, 5), f"{name}: MOCKUP (left, x4 Lanczos) | OURS (right, stitch preview, same scale)", fill=(255, 0, 0))
    out.save(f"out/compare_{name}.png"); return out
