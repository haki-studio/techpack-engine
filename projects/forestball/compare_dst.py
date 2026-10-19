"""Fidelity sheets from the FINAL stitch files (review Rev C): out/compare_back.png, out/compare_front.png.
Left = mockup crop (x4 Lanczos); right = the grade-B DST read back (stitches drawn in their PES thread colours, 0.4 mm wide,
on the shell colour) at the same scale; plus 3–4 zoomed regions each. Nothing here is drawn from the art regions."""
import json, sys
import numpy as np
import pyembroidery as pe
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import fbcore
import back as B, front as F

CUR = json.load(open("dst_current.json"))
def dst_image(keys, bbox, ppm):
    x0, y0, x1, y1 = bbox; W, H = int((x1 - x0) * ppm), int((y1 - y0) * ppm)
    im = Image.new("RGB", (W, H), tuple(int(fbcore.FABRIC[i:i+2], 16) for i in (1, 3, 5))); d = ImageDraw.Draw(im)
    lw = max(1, int(round(0.42 * ppm)))
    for k in keys:
        f = CUR[k]["file"]; cx, cy = CUR[k]["centre"]
        cols = [t.hex_color() for t in pe.read(f + ".pes").threadlist]
        p = pe.read(f + ".dst"); ci = 0; prev = None
        for x, y, cmd in p.stitches:
            c = cmd & pe.COMMAND_MASK
            if c == pe.COLOR_CHANGE: ci += 1; prev = None; continue
            if c != pe.STITCH: prev = None; continue
            P_ = ((x / 10 + cx - x0) * ppm, (y / 10 + cy - y0) * ppm)
            if prev: d.line([prev, P_], fill=cols[min(ci, len(cols) - 1)], width=lw)
            prev = P_
    return im

def label(im, s):
    d = ImageDraw.Draw(im)
    try: fnt = ImageFont.truetype("DejaVuSans-Bold.ttf", 26)
    except Exception: fnt = None
    d.rectangle([0, 0, im.width, 36], fill=(255, 255, 255)); d.text((8, 4), s, fill=(20, 20, 20), font=fnt); return im

def pair(mock, crop_px, P, keys, h):
    x0, y0, x1, y1 = crop_px
    m = mock.crop(crop_px).resize(((x1-x0)*4, (y1-y0)*4), Image.LANCZOS).filter(ImageFilter.UnsharpMask(1.2, 60))
    a = P(x0, y0); b = P(x1, y1); bx = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
    ppm = h / (bx[3] - bx[1]); r = dst_image(keys, bx, ppm)
    m = m.resize((int(m.width * h / m.height), h)); r = r.resize((m.width, h))
    out = Image.new("RGB", (m.width * 2 + 12, h + 40), (255, 255, 255)); out.paste(m, (0, 40)); out.paste(r, (m.width + 12, 40)); return out

def sheet(name, mock_path, P, keys, whole, zooms, labels):
    mock = Image.open(mock_path).convert("RGB")
    tiles = [label(pair(mock, whole, P, keys, 900), "mockup (left) vs FINAL DST read-back, grade B (right), same scale")]
    for z, lb in zip(zooms, labels): tiles.append(label(pair(mock, z, P, keys, 440), lb))
    W = max(t.width for t in tiles); Hh = sum(t.height + 10 for t in tiles)
    out = Image.new("RGB", (W, Hh), (255, 255, 255)); y = 0
    for t in tiles: out.paste(t, (0, y)); y += t.height + 10
    out.thumbnail((2400, 4800)); out.save(f"out/compare_{name}.png"); print("wrote", f"out/compare_{name}.png", out.size)

if __name__ == "__main__":
    if "back" in sys.argv or len(sys.argv) == 1:
        sheet("back", "inputs/back.png", B.P, ["back"], (95, 90, 640, 700),
              [(150, 230, 330, 360), (380, 470, 600, 610), (200, 560, 400, 700), (480, 100, 660, 260)],
              ["zoom: mossy main limb + leaf sprays", "zoom: bank + pool + licensed placeholder", "zoom: stream rapids, rocks, grass", "zoom: top-right sprays + rays"])
    if "front" in sys.argv or len(sys.argv) == 1:
        sheet("front", "inputs/front.png", F.P, ["02R", "02L"], (95, 90, 650, 470),
              [(110, 110, 270, 450), (240, 190, 380, 360), (390, 180, 640, 330), (420, 330, 650, 470)],
              ["zoom: hanging moss (02R)", "zoom: limb + sprays at the zip (02R)", "zoom: 02L upper twig + sprays", "zoom: 02L limb end + sprays"])
