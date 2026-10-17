"""Zoomed render of a written stitch file (reads the .pes back): every stitch drawn as a line, thread colour.
usage: python3 dstzoom.py <base> <x0> <y0> <x1> <y1> <out.png> [px_per_mm]   (coords in mm relative to the file origin)"""
import sys
import pyembroidery as pe
from PIL import Image, ImageDraw
def zoom(base, box, out, ppm=12, bg=(25, 28, 36)):
    p = pe.read(base + ".pes"); x0, y0, x1, y1 = box
    im = Image.new("RGB", (int((x1-x0)*ppm), int((y1-y0)*ppm)), bg); d = ImageDraw.Draw(im)
    cols = [t.hex_color() for t in p.threadlist]; ci = 0; prev = None
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK; P = ((x/10 - x0)*ppm, (y/10 - y0)*ppm)
        if k == pe.STITCH:
            if prev: d.line([prev, P], fill=cols[min(ci, len(cols)-1)], width=max(1, int(ppm*0.12)))
            prev = P
        elif k == pe.COLOR_CHANGE: ci += 1; prev = None
        elif k == pe.TRIM: prev = None
        else: prev = P
    im.save(out); return im
if __name__ == "__main__":
    a = sys.argv; zoom(a[1], tuple(map(float, a[2:6])), a[6], float(a[7]) if len(a) > 7 else 12)
