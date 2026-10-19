"""out/compare_<element>.png: mockup (resampled into the same piece mm space) vs the size-M STITCH FILE, same scale,
plus zoomed regions. Rev B (review item 1): the stitch panels are drawn from the DST read-back of the final size-M files
(every stitch of out/<el>/M/*.dst, placed with the file's origin from result_<piece>.json; thread colours from the
per-stop table), not from the region art. Zooms show the registered close-up wherever it covers the zoom (outside its
footprint: white, no stretched edge pixels - item 9); sleeve zooms add the raw front-view crop (item 9).
usage: python3 compare.py"""
import rbcore
import json, os, math, random
import numpy as np
import pyembroidery as pe
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import mockmap as MM, front as F
from motifs2 import HEX

g, mt = F.pieces("M")
try: FONT = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 26); FS = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 20)
except Exception: FONT = FS = ImageFont.load_default()
FAB = tuple(int(rbcore.FABRIC[i:i+2], 16) for i in (1, 3, 5))

# ------------------------------------------------------------------ DST read-back -> stitches in garment mm
_ST = {}
def stitches(P, size="M"):
    if (P, size) in _ST: return _ST[(P, size)]
    res = json.load(open(f"{rbcore.outdir(P, size)}/result_{P}.json"))["full"]
    ox, oy = res["origin"]; cols = [ps.get("col") for ps in res["per_stop"]]
    p = pe.read(res["file"] + ".dst"); segs = []; ci = 0; prev = None
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK
        if k == pe.STITCH:
            q = (x/10 + ox, y/10 + oy)
            if prev is not None: segs.append((prev, q, ci))
            prev = q
        elif k == pe.COLOR_CHANGE: ci += 1; prev = None
        elif k in (pe.TRIM, pe.JUMP): prev = None
        elif k == pe.END: break
    out = dict(segs=segs, cols=cols, file=res["file"] + ".dst", stitches=res["stitches"], trims=res["trims"])
    _ST[(P, size)] = out; return out

def fabric(W, H, ppm, seed=1):
    rng = np.random.default_rng(seed); b = np.array(FAB, float)
    arr = np.clip(b + rng.normal(0, 4.0, (H, W, 1)), 0, 255).astype(np.uint8)
    return Image.fromarray(np.repeat(arr, 3, 2) if arr.shape[2] == 1 else arr)

def dst_img(pieces, bb, ppm, xform=None, ss=2):
    """stitch-by-stitch render of the DST read-back (supersampled), thread width 0.4 mm, a dark edge per stitch"""
    W, H = int((bb[2]-bb[0])*ppm), int((bb[3]-bb[1])*ppm)
    S = ppm*ss; im = fabric(W*ss, H*ss, S).convert("RGB"); d = ImageDraw.Draw(im)
    rng = random.Random(2); lw = max(1, int(round(0.42*S))); lw2 = max(1, int(round(0.26*S)))
    for P in pieces:
        st = stitches(P)
        for a, b, ci in st["segs"]:
            if xform: a, b = xform(P, a), xform(P, b)
            if max(a[0], b[0]) < bb[0] or min(a[0], b[0]) > bb[2] or max(a[1], b[1]) < bb[1] or min(a[1], b[1]) > bb[3]: continue
            col = st["cols"][min(ci, len(st["cols"]) - 1)]
            c = tuple(int(HEX[col][i:i+2], 16) for i in (1, 3, 5)) if col in HEX else (0, 160, 255)
            A = ((a[0]-bb[0])*S, (a[1]-bb[1])*S); B = ((b[0]-bb[0])*S, (b[1]-bb[1])*S)
            k = rng.uniform(0.82, 1.08)
            d.line([A, B], fill=tuple(int(v*0.55) for v in c), width=lw)
            d.line([A, B], fill=tuple(min(255, int(v*k)) for v in c), width=lw2)
    return im.resize((W, H), Image.LANCZOS)

# ------------------------------------------------------------------ references
def grid(bb, ppm):
    xs = bb[0] + (np.arange(int((bb[2]-bb[0])*ppm)) + 0.5)/ppm; ys = bb[1] + (np.arange(int((bb[3]-bb[1])*ppm)) + 0.5)/ppm
    return np.meshgrid(xs, ys)

def mock_front(bb, ppm, src="front"):
    X, Y = grid(bb, ppm); fx, fy = MM.Pinv(X, Y)
    if src == "close":
        cx, cy = MM.close_px(fx, fy); B = MM.img("closeup_mockup_head")
        ok = (cx >= 2) & (cx < B.shape[1] - 3) & (cy >= 2) & (cy < B.shape[0] - 3)
        im = MM.sample("closeup_mockup_head", np.where(ok, cx, 0), np.where(ok, cy, 0)); im[~ok] = 255
        return Image.fromarray(im.astype(np.uint8)), float(ok.mean())
    return Image.fromarray(MM.sample("front", fx, fy).astype(np.uint8))

def mock_sleeve(side, bb, ppm):
    X, Y = grid(bb, ppm); px, py, ok = MM.sleeve_to_img(side, X, Y, mt)
    im = MM.sample("front", np.where(ok, px, 0), np.where(ok, py, 0)); im[~ok] = 255
    return Image.fromarray(im.astype(np.uint8))

def raw_sleeve_crop(side, bb, h_px):
    """the sleeve zoom as it appears in front.png (no unwrap), Lanczos-upscaled to h_px tall: the reference the eye reads"""
    X, Y = np.meshgrid(np.linspace(bb[0], bb[2], 40), np.linspace(bb[1], bb[3], 40))
    px, py, ok = MM.sleeve_to_img(side, X, Y, mt)
    if not ok.any(): return None
    x0, x1, y0, y1 = px[ok].min() - 4, px[ok].max() + 4, py[ok].min() - 4, py[ok].max() + 4
    im = Image.open("inputs/front.png").convert("RGB").crop((int(x0), int(y0), int(x1), int(y1)))
    k = h_px / im.size[1]
    return im.resize((max(1, int(im.size[0]*k)), h_px), Image.LANCZOS).filter(ImageFilter.UnsharpMask(1.2, 60, 2))

def outline(im, bb, ppm, geoms, col=(255, 200, 0), xf=None):
    d = ImageDraw.Draw(im)
    for gm in geoms:
        for p in getattr(gm, "geoms", [gm]):
            if p.geom_type != "Polygon": continue
            cs = [xf(c) if xf else c for c in p.exterior.coords]
            d.line([((x - bb[0])*ppm, (y - bb[1])*ppm) for x, y in cs], fill=col, width=2)
    return im

def label(im, s, sub=None):
    d = ImageDraw.Draw(im); d.rectangle([0, 0, im.size[0], 34 if not sub else 58], fill=(255, 255, 255))
    d.text((8, 4), s, fill=(20, 20, 20), font=FONT)
    if sub: d.text((8, 34), sub, fill=(90, 90, 90), font=FS)
    return im

def sheet(title, sub, full, zooms, path):
    W = sum(i.size[0] for i in full) + 10*(len(full) + 1)
    zrows = []
    for zt, ims in zooms:
        h = max(i.size[1] for i in ims); w = sum(i.size[0] for i in ims) + 10*(len(ims) - 1)
        zrows.append((zt, ims, w, h))
    W = max(W, max(z[2] for z in zrows) + 20)
    H = 76 + max(i.size[1] for i in full) + 20 + sum(z[3] + 50 for z in zrows) + 20
    o = Image.new("RGB", (W, H), (255, 255, 255)); d = ImageDraw.Draw(o)
    d.text((10, 10), title, fill=(10, 10, 10), font=FONT); d.text((10, 44), sub, fill=(90, 90, 90), font=FS)
    x = 10
    for im in full: o.paste(im, (x, 76)); x += im.size[0] + 10
    y = 96 + max(i.size[1] for i in full)
    for zt, ims, w, h in zrows:
        d.text((10, y), zt, fill=(10, 10, 10), font=FS); x = 10; y += 28
        for im in ims: o.paste(im, (x, y)); x += im.size[0] + 10
        y += h + 22
    o.save(path); print(path, o.size)

def fsub(P): s = stitches(P); return f"{os.path.basename(s['file'])}: {s['stitches']:,} st / {s['trims']} trims (read back)"

if __name__ == "__main__":
    os.makedirs("out", exist_ok=True)
    SUB = "same scale, size M, garment mm; yellow = keep-out boundary. Stitch panels = every stitch of the size-M DST files (read back), not the art."
    # ---------------- 01 fronts
    bb = (-300, -40, 300, 500); ppm = 2.0
    clips = [F.clip_for("M", "R"), F.clip_for("M", "L")]
    mk = outline(mock_front(bb, ppm), bb, ppm, clips); st = outline(dst_img(("FR", "FL"), bb, ppm), bb, ppm, clips)
    label(mk, "MOCKUP (inputs/front.png)"); label(st, "STITCH FILES size M (DST read-back)", f"FR {stitches('FR')['stitches']:,} st · FL {stitches('FL')['stitches']:,} st")
    Z = []
    for zt, zb in (("Head: jaws, teeth, eye (close-up = tracing reference)", (95, 150, 285, 330)),
                   ("Throat + lower jaw: directional black / red / crimson strokes", (10, 270, 200, 420)),
                   ("Lower jaw + slash streaks (wearer's left)", (20, 330, 245, 480)),
                   ("Mane + flame strands (wearer's right; close-up covers only its CF edge)", (-275, 60, -40, 260)),
                   ("Lightning branches (wearer's right, top): 2.5 mm root -> 1.0 mm tip", (-250, -20, -40, 130)),
                   ("Shoulder streaks (wearer's left, top)", (40, -40, 300, 180))):
        zp = 5.0 if (zb[2]-zb[0]) < 200 else 4.0
        ims = [label(mock_front(zb, zp), "mockup")]
        ci, cov = mock_front(zb, zp, "close")
        if cov > 0.15: ims.append(label(ci, "close-up (traced)", f"covers {cov*100:.0f} % of this zoom"))
        ims.append(label(outline(dst_img(("FR", "FL"), zb, zp), zb, zp, clips), "stitch file (DST)"))
        Z.append((zt, ims))
    sheet("01 BEAST HEAD (fronts) — mockup vs stitch file, Rev B", SUB, (mk, st), Z, "out/compare_01_beast-head.png")
    # ---------------- 02 sleeves
    bbs = (-260, -110, 260, 470); ppm = 1.4
    fulls = []
    for P in ("SR", "SL"):
        c = F.sleeve_clip("M", P[1])
        fulls.append((outline(mock_sleeve(P[1], bbs, ppm), bbs, ppm, [c]), outline(dst_img((P,), bbs, ppm), bbs, ppm, [c])))
    w0, h0 = fulls[0][0].size
    mk = Image.new("RGB", (w0*2 + 10, h0), "white"); mk.paste(fulls[0][0], (0, 0)); mk.paste(fulls[1][0], (w0 + 10, 0))
    st = Image.new("RGB", mk.size, "white"); st.paste(fulls[0][1], (0, 0)); st.paste(fulls[1][1], (w0 + 10, 0))
    label(mk, "MOCKUP sleeves unwrapped (S01 right | S02 left)"); label(st, "STITCH FILES size M (DST read-back)", f"SR {stitches('SR')['stitches']:,} st · SL {stitches('SL')['stitches']:,} st")
    Z = []
    for zt, P, zb in (("Right sleeve: upper bundle at the cap, branch tip, lower bundles", "SR", (0, -80, 245, 230)),
                      ("Left sleeve: upper + lower streak bundles", "SL", (-245, -90, 0, 340))):
        zp = 3.0
        ms = mock_sleeve(P[1], zb, zp); ss = outline(dst_img((P,), zb, zp), zb, zp, [F.sleeve_clip("M", P[1])])
        raw = raw_sleeve_crop(P[1], zb, ms.size[1])
        ims = ([label(raw, "mockup as rendered (front view)")] if raw is not None else []) + [label(ms, "mockup (unwrapped)"), label(ss, "stitch file (DST)")]
        Z.append((zt, ims))
    sheet("02 SLASH STREAKS (sleeves) — mockup vs stitch file, Rev B", SUB + " No sleeve close-up exists: traced from the mockup.", (mk, st), Z, "out/compare_02_sleeve-streaks.png")
