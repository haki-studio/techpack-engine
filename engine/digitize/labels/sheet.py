"""Vision sheet (ENGINE_PLAN G1): the image the VISION STEP looks at before it writes parts.labels.json.

The reference crop (the same 12 ppm reference the gates grade: mockup + registered close-ups, extract/register.py) is
drawn at `scale` px/mm with a garment-mm grid (thin lines every `step` mm, labelled every `label_every` mm), so whoever
writes the labels (today the Claude Code session, later the PLM vision call) reads seeds and polygon hints straight off
the sheet in garment mm. Optional: an overlay of an existing labels file (each part's hint polygon / seed in its colour)
to check the labels against the picture before running the compiler. No Anthropic API calls.

  python3 -m digitize.labels.sheet <run.yaml> <out.png> [--scale 4] [--step 5] [--window x0 y0 x1 y1] [--labels f.json]
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(os.path.dirname(HERE))
if ENGINE not in sys.path: sys.path.insert(0, ENGINE)

import numpy as np
from PIL import Image, ImageDraw


def draw(rgb, bounds, ppm, out, scale=4.0, step=5.0, label_every=10.0, window=None, labels=None):
    x0, y0, x1, y1 = bounds
    im = Image.fromarray(np.asarray(rgb).clip(0, 255).astype(np.uint8))
    W, H = int(round((x1 - x0) * scale)), int(round((y1 - y0) * scale))
    im = im.resize((W, H), Image.LANCZOS)
    if window:                                                       # a zoomed window (garment mm)
        wx0, wy0, wx1, wy1 = window
        im = im.crop((int((wx0 - x0) * scale), int((wy0 - y0) * scale), int((wx1 - x0) * scale), int((wy1 - y0) * scale)))
        x0, y0, x1, y1 = wx0, wy0, wx1, wy1; W, H = im.size
    pad = 34; sheet = Image.new("RGB", (W + 2 * pad, H + 2 * pad), (255, 255, 255)); sheet.paste(im, (pad, pad))
    d = ImageDraw.Draw(sheet)
    P = lambda x, y: (pad + (x - x0) * scale, pad + (y - y0) * scale)
    import math
    gx = math.ceil(x0 / step) * step
    while gx <= x1 + 1e-9:
        major = abs(gx / label_every - round(gx / label_every)) < 1e-6
        d.line([P(gx, y0), P(gx, y1)], fill=(255, 255, 0) if major else (120, 120, 120), width=1)
        if major:
            d.text((P(gx, y0)[0] - 8, 4), f"{gx:g}", fill=(0, 0, 0)); d.text((P(gx, y1)[0] - 8, H + pad + 8), f"{gx:g}", fill=(0, 0, 0))
        gx += step
    gy = math.ceil(y0 / step) * step
    while gy <= y1 + 1e-9:
        major = abs(gy / label_every - round(gy / label_every)) < 1e-6
        d.line([P(x0, gy), P(x1, gy)], fill=(255, 255, 0) if major else (120, 120, 120), width=1)
        if major:
            d.text((2, P(x0, gy)[1] - 5), f"{gy:g}", fill=(0, 0, 0)); d.text((W + pad + 2, P(x0, gy)[1] - 5), f"{gy:g}", fill=(0, 0, 0))
        gy += step
    if labels:                                                       # hint polygons / seeds of an existing labels file
        from digitize.labels import schema as LS
        L = LS.load(labels) if isinstance(labels, str) else labels
        pal = [(255, 60, 60), (60, 200, 255), (255, 160, 0), (160, 255, 60), (255, 60, 255), (0, 255, 160)]
        for i, (m, p) in enumerate(LS.iter_parts(L)):
            c = pal[i % len(pal)]
            for w in p.get("hint", {}).get("polygons", []):
                d.line([P(*q) for q in w] + [P(*w[0])], fill=c, width=2)
            for s in p.get("hint", {}).get("seeds", []):
                a, b = P(*s); d.ellipse([a - 4, b - 4, a + 4, b + 4], outline=c, width=2)
            w0 = (p.get("hint", {}).get("polygons") or [[None]])[0][0]
            if w0: d.text(P(*w0), p["id"], fill=c)
    sheet.save(out)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_yaml"); ap.add_argument("out")
    ap.add_argument("--scale", type=float, default=4.0); ap.add_argument("--step", type=float, default=5.0)
    ap.add_argument("--label-every", type=float, default=10.0)
    ap.add_argument("--window", type=float, nargs=4); ap.add_argument("--labels")
    a = ap.parse_args(argv)
    from digitize import config
    from digitize.extract import register
    cfg = config.load(a.run_yaml); b = json.load(open(config.path(cfg, cfg["bench"])))
    reg = register.load(config.path(cfg, cfg.get("registration") or b["registration"]))
    ref = register.reference(reg, b["view"], tuple(b["crop"]), ppm=float(b["ppm"]))
    labels = config.path(cfg, a.labels) if a.labels else None
    print(draw(ref["rgb"], ref["bounds"], ref["ppm"], a.out, a.scale, a.step, a.label_every, a.window, labels))


if __name__ == "__main__":
    main()
