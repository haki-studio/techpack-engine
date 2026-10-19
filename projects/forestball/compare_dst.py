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

def pair_src(src_png, src_bbox, crop_mm, keys, h):
    """the traced SOURCE (registered close-up composited in garment mm, 4 px/mm: out/art/trace_src_*.png) vs the DST, same mm crop"""
    im = Image.open(src_png).convert("RGB"); x0, y0 = src_bbox[0], src_bbox[1]; a, b, c, d = crop_mm
    m = im.crop((int((a - x0) * 4), int((b - y0) * 4), int((c - x0) * 4), int((d - y0) * 4)))
    m = m.resize((int(m.width * h / m.height), h), Image.LANCZOS); r = dst_image(keys, crop_mm, h / (d - b)).resize((m.width, h))
    out = Image.new("RGB", (m.width * 2 + 12, h + 40), (255, 255, 255)); out.paste(m, (0, 40)); out.paste(r, (m.width + 12, 40)); return out

def ray_angle_png(path="out/dbg/ray_angles.png"):
    """per-ray angle table: mockup stripe axis vs the DST's sewn axis (fidelity_qa.json)"""
    import os
    if not os.path.exists("fidelity_qa.json"): return None
    q = json.load(open("fidelity_qa.json"))["back"]; A = [a for a in q.get("ray_angles", []) if a["length"] >= 25]
    A.sort(key=lambda a: -a["length"]); R = json.load(open("rays_trace2.json"))
    try: fnt = ImageFont.truetype("DejaVuSansMono.ttf", 18)
    except Exception: fnt = None
    lines = [f"LIGHT RAYS: angle below horizontal, mockup stripe vs DST (stripes >= 25 mm; {len(A)} of {len(R['stripes'])}); fitted source (VP) x {R['vp'][0]:.0f}, y {R['vp'][1]:.0f} mm"]
    row = ""
    for i, a in enumerate(A):
        row += f"#{a['stripe']:<3d}{a['length']:4.0f}mm  {a['mockup_deg']:5.1f}° vs {('%5.1f°' % a['dst_deg']) if a['dst_deg'] is not None else '  -  '}   "
        if i % 4 == 3: lines.append(row); row = ""
    if row: lines.append(row)
    d_ = [abs(a["dst_deg"] - a["mockup_deg"]) for a in A if a["dst_deg"] is not None]
    if d_: lines.append(f"max |difference| {max(d_):.1f}°, median {sorted(d_)[len(d_)//2]:.1f}°")
    im = Image.new("RGB", (2300, 28 * len(lines) + 20), (255, 255, 255)); dr = ImageDraw.Draw(im)
    for i, l in enumerate(lines): dr.text((10, 10 + 28 * i), l, fill=(120, 0, 0) if i == 0 else (20, 20, 20), font=fnt)
    im.save(path); return path

def sheet(name, mock_path, P, keys, whole, zooms, labels, src=(), tables=()):
    mock = Image.open(mock_path).convert("RGB")
    tiles = [label(pair(mock, whole, P, keys, 900), "mockup (left) vs FINAL DST read-back, grade B (right), same scale")]
    for z, lb in zip(zooms, labels): tiles.append(label(pair(mock, z, P, keys, 440), lb))
    for (png, bb, crop, lb) in src: tiles.append(label(pair_src(png, bb, crop, keys, 440), lb))
    import os
    for tp in tables:
        if tp and os.path.exists(tp): tiles.append(Image.open(tp).convert("RGB"))
    W = max(t.width for t in tiles); Hh = sum(t.height + 10 for t in tiles)
    out = Image.new("RGB", (W, Hh), (255, 255, 255)); y = 0
    for t in tiles: out.paste(t, (0, y)); y += t.height + 10
    out.thumbnail((2400, 4800)); out.save(f"out/compare_{name}.png"); print("wrote", f"out/compare_{name}.png", out.size)

if __name__ == "__main__":
    if "back" in sys.argv or len(sys.argv) == 1:
        sheet("back", "inputs/back.png", B.P, ["back"], (95, 90, 640, 700),
              [(150, 230, 330, 360), (380, 470, 600, 610), (200, 560, 400, 700), (480, 100, 660, 260), (300, 90, 640, 470)],
              ["zoom: mossy main limb + leaf sprays", "zoom: bank + pool + licensed placeholder", "zoom: stream rapids, rocks, grass", "zoom: top-right sprays + rays", "zoom: light rays — the mockup's stripes, traced one by one (fan, own angles, end at the bank)"],
              tables=[ray_angle_png(), "out/dbg/fqa_back.png"],
              src=[("out/art/trace_src_back.png", (-300, -20), (-200, 120, -20, 260), "TRACED SOURCE close-up a (left) vs DST: chain limb links, crevices, moss, cream highlights"),
                   ("out/art/trace_src_back.png", (-300, -20), (20, 330, 240, 470), "TRACED SOURCE close-up a (left) vs DST: bank, root loops, pool ripples, rapids")])
    if "front" in sys.argv or len(sys.argv) == 1:
        sheet("front", "inputs/front.png", F.P, ["02R", "02L"], (95, 90, 650, 470),
              [(110, 110, 270, 450), (240, 190, 380, 360), (390, 180, 640, 330), (420, 330, 650, 470)],
              ["zoom: hanging moss (02R)", "zoom: limb + sprays at the zip (02R)", "zoom: 02L upper twig + sprays", "zoom: 02L limb end + sprays"],
              src=[("out/art/trace_src_02R.png", (-289.5, -64.08), (-250, 20, -90, 160), "TRACED SOURCE close-up c (left) vs DST: hanging moss ropes + limb (02R)")],
              tables=["out/dbg/fqa_02R.png", "out/dbg/fqa_02L.png"])
