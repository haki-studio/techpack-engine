"""out/compare_<element>.png: mockup (resampled into the same piece mm space) vs the size-M stitch render, same scale,
plus zoomed regions (the head zooms also show the registered close-up the art was traced from).
usage: python3 compare.py"""
import rbcore
import pickle, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import mockmap as MM, front as F, stitchrender as SR

A = pickle.load(open("art_M.pkl", "rb"))
g, mt = F.pieces("M")
try: FONT = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 26); FS = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 20)
except Exception: FONT = FS = ImageFont.load_default()

def mock_front(bb, ppm, src="front"):
    xs = bb[0] + (np.arange(int((bb[2]-bb[0])*ppm)) + 0.5)/ppm; ys = bb[1] + (np.arange(int((bb[3]-bb[1])*ppm)) + 0.5)/ppm
    X, Y = np.meshgrid(xs, ys); fx, fy = MM.Pinv(X, Y)
    if src == "close":
        cx, cy = MM.close_px(fx, fy); return Image.fromarray(MM.sample("closeup_mockup_head", cx, cy).astype(np.uint8))
    return Image.fromarray(MM.sample("front", fx, fy).astype(np.uint8))

def mock_sleeve(side, bb, ppm):
    xs = bb[0] + (np.arange(int((bb[2]-bb[0])*ppm)) + 0.5)/ppm; ys = bb[1] + (np.arange(int((bb[3]-bb[1])*ppm)) + 0.5)/ppm
    X, Y = np.meshgrid(xs, ys); px, py, ok = MM.sleeve_to_img(side, X, Y, mt)
    im = MM.sample("front", np.where(ok, px, 0), np.where(ok, py, 0)); im[~ok] = 255
    return Image.fromarray(im.astype(np.uint8))

def outline(im, bb, ppm, geoms, col=(255, 200, 0)):
    d = ImageDraw.Draw(im)
    for gm in geoms:
        for p in getattr(gm, "geoms", [gm]):
            if p.geom_type != "Polygon": continue
            d.line([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in p.exterior.coords], fill=col, width=2)
    return im

def label(im, s, sub=None):
    d = ImageDraw.Draw(im); d.rectangle([0, 0, im.size[0], 34 if not sub else 58], fill=(255, 255, 255))
    d.text((8, 4), s, fill=(20, 20, 20), font=FONT)
    if sub: d.text((8, 34), sub, fill=(90, 90, 90), font=FS)
    return im

def sheet(name, title, full, zooms, path):
    """full = (mock_img, stitch_img); zooms = [(title, [img, img, ...])]"""
    W = full[0].size[0] + full[1].size[0] + 30
    zrows = []
    for zt, ims in zooms:
        h = max(i.size[1] for i in ims); w = sum(i.size[0] for i in ims) + 10*(len(ims) - 1)
        zrows.append((zt, ims, w, h))
    W = max(W, max(z[2] for z in zrows) + 20)
    H = 70 + max(full[0].size[1], full[1].size[1]) + 20 + sum(z[3] + 50 for z in zrows) + 20
    o = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(o)
    d.text((10, 10), title, fill=(10, 10, 10), font=FONT)
    d.text((10, 42), "same scale, size M, garment mm; yellow = keep-out boundary. Every zoom: mockup | stitch render", fill=(90, 90, 90), font=FS)
    o.paste(full[0], (10, 70)); o.paste(full[1], (20 + full[0].size[0], 70))
    y = 90 + max(full[0].size[1], full[1].size[1])
    for zt, ims, w, h in zrows:
        d.text((10, y), zt, fill=(10, 10, 10), font=FS); x = 10; y += 28
        for im in ims: o.paste(im, (x, y)); x += im.size[0] + 10
        y += h + 22
    o.save(path); print(path, o.size)

def render(regs, bb, ppm): return SR.render(regs, bb, ppm, base=rbcore.FABRIC)

if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    # ---------------- 01 fronts
    bb = (-300, -40, 300, 500); ppm = 2.0
    regs = A["FR"] + A["FL"]; clips = [F.clip_for("M", "R"), F.clip_for("M", "L")]
    mk = outline(mock_front(bb, ppm), bb, ppm, clips); st = outline(render(regs, bb, ppm), bb, ppm, clips)
    label(mk, "MOCKUP (inputs/front.png)"); label(st, "STITCH RENDER size M (art_M.pkl)")
    Z = []
    for zt, zb, src in (("Head: jaws, teeth, eye", (95, 150, 285, 330), "close"),
                        ("Lower jaw + streaks (wearer's left)", (20, 280, 230, 475), "close"),
                        ("Mane + flame strands (wearer's right)", (-275, 60, -40, 260), "front"),
                        ("Lightning branches (wearer's right, top)", (-250, -20, -40, 130), "front")):
        zp = 5.0 if (zb[2]-zb[0]) < 200 else 4.0
        ims = [label(mock_front(zb, zp), "mockup")]
        if src == "close": ims.append(label(mock_front(zb, zp, "close"), "close-up (traced)"))
        ims.append(label(outline(render(regs, zb, zp), zb, zp, clips), "stitch"))
        Z.append((zt, ims))
    sheet("01", "01 BEAST HEAD (fronts) — mockup vs stitch", (mk, st), Z, "out/compare_01_beast-head.png")
    # ---------------- 02 sleeves
    bbs = (-260, -110, 260, 470); ppm = 1.4
    fulls = []
    for P in ("SR", "SL"):
        c = F.sleeve_clip("M", P[1])
        fulls.append((outline(mock_sleeve(P[1], bbs, ppm), bbs, ppm, [c]), outline(render(A[P], bbs, ppm), bbs, ppm, [c])))
    mk = Image.new("RGB", (fulls[0][0].size[0]*2 + 10, fulls[0][0].size[1]), "white"); mk.paste(fulls[0][0], (0, 0)); mk.paste(fulls[1][0], (fulls[0][0].size[0] + 10, 0))
    st = Image.new("RGB", mk.size, "white"); st.paste(fulls[0][1], (0, 0)); st.paste(fulls[1][1], (fulls[0][1].size[0] + 10, 0))
    label(mk, "MOCKUP sleeves unwrapped (S01 right | S02 left)"); label(st, "STITCH RENDER size M")
    Z = []
    for zt, P, zb in (("Right sleeve streaks + branch tip", "SR", (0, -60, 240, 230)), ("Left sleeve streaks", "SL", (-235, -80, 0, 330))):
        zp = 3.0
        ms = mock_sleeve(P[1], zb, zp); ss = outline(render(A[P], zb, zp), zb, zp, [F.sleeve_clip("M", P[1])])
        Z.append((zt, [label(ms, "mockup (unwrapped)"), label(ss, "stitch")]))
    sheet("02", "02 SLASH STREAKS (sleeves) — mockup vs stitch", (mk, st), Z, "out/compare_02_sleeve-streaks.png")
