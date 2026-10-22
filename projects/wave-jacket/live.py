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
    rec = chen_rec(P, size, root) if os.path.exists(f"{root or f'out/01_wave/{size}'}/result_{P}.json") else None
    if rec: draw_chenille(out, rec, bb, ppm)                         # primary foam: the chenille file on top
    return out

# ---------------------------------------------------------------- chenille overlay (primary foam, factory 19 Oct)
CHEN_W = 2.2           # a chenille loop row is ~2.2 mm wide (loop / moss rows 1.8 mm apart cover the foam)
def chenille_paths(rec):
    """[(colour key, [(x, y) ...])] in piece coords from a chenille readback record (rec = result['chenille'])"""
    if not rec: return []
    p = pe.read(rec["file"] + ".dst"); ox, oy = rec["origin"]; cols = rec.get("colours", ["w1", "w3"])
    out = []; ci = 0; cur = []
    for x, y, c in p.stitches:
        k = c & pe.COMMAND_MASK
        if k == pe.STITCH: cur.append((x / 10 + ox, y / 10 + oy)); continue
        if len(cur) > 1: out.append((cols[min(ci, len(cols) - 1)], cur))
        cur = []
        if k == pe.COLOR_CHANGE: ci += 1
    if len(cur) > 1: out.append((cols[min(ci, len(cols) - 1)], cur))
    return out

def draw_chenille(im, rec, bb, ppm, flat=None, live=True):
    """draw the chenille file on a piece image: loop rows CHEN_W wide (cream, small shadow dots = loops in the live view),
    chain cords 1.0 mm in shade. flat = {colour key: fill value} draws plain class values instead (for metrics)"""
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    for col, pts in chenille_paths(rec):
        q = [((x - bb[0]) * ppm, (y - bb[1]) * ppm) for x, y in pts]
        w = max(1, int(round((CHEN_W if col == "w1" or col == "w1e" else 1.0) * ppm)))
        if flat is not None: d.line(q, fill=flat.get(col, 7), width=w); continue
        base = tuple(int(motifs2.HEX[col][i:i + 2], 16) for i in (1, 3, 5))
        d.line(q, fill=base, width=w, joint="curve")
        if live and col in ("w1", "w1e"):
            sh = tuple(int(v * 0.78) for v in base)
            for (x0, y0), (x1, y1) in zip(q[::2], q[1::2]): d.ellipse([x1 - w * 0.22, y1 - w * 0.22, x1 + w * 0.22, y1 + w * 0.22], fill=sh)
    return im

def chen_rec(P, size="M", root=None):
    root = root or f"out/01_wave/{size}"
    return json.load(open(f"{root}/result_{P}.json"))["full"].get("chenille")
