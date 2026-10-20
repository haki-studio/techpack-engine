"""Live view (engine dstlive.render, like Hatch's 3D view - LESSONS A16) of a shipped DST, placed on the piece's pattern
coordinates: live_piece(P, bbox, ppm) -> PIL image covering bbox (mm) at ppm px/mm. Used by the compare + continuity sheets."""
import wavecore as WC
import json, os, functools
import numpy as np
import pyembroidery as pe
from PIL import Image
import dstlive, motifs2

def result(P, size="M", root=None):
    root = root or f"out/01_wave/{size}"
    r = json.load(open(f"{root}/result_{P}.json"))["full"]
    return os.path.join(root, os.path.basename(r["file"]) + ".dst"), [motifs2.HEX[s["col"]] for s in r["per_stop"]], r["origin"]

@functools.lru_cache(maxsize=None)
def _render(P, ppm, size="M", root=None):
    f_, cols, (ox, oy) = result(P, size, root)
    im = dstlive.render(f_, colours=cols, ppm=ppm, shell=WC.FABRIC)
    p = pe.read(f_); xs = [x / 10 for x, y, c in p.stitches if (c & pe.COMMAND_MASK) == pe.STITCH]; ys = [y / 10 for x, y, c in p.stitches if (c & pe.COMMAND_MASK) == pe.STITCH]
    x0, y0 = min(xs) - 3.0 + ox, min(ys) - 3.0 + oy                 # dstlive pads 3 mm
    return im, x0, y0

def live_piece(P, bb, ppm, size="M", root=None):
    im, x0, y0 = _render(P, ppm, size, root)
    W, H = int(round((bb[2] - bb[0]) * ppm)), int(round((bb[3] - bb[1]) * ppm))
    out = Image.new("RGB", (W, H), tuple(int(WC.FABRIC[i:i + 2], 16) for i in (1, 3, 5)))
    out.paste(im, (int(round((x0 - bb[0]) * ppm)), int(round((y0 - bb[1]) * ppm))))
    return out
