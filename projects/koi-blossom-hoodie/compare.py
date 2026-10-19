"""Fidelity sheets (LESSONS A11/A12): out/compare_01_front-koi.png + out/compare_02_sleeve-koi.png.
Rev B: the stitch column is drawn from the FINAL production file read back (pyembroidery read of the size-M DST: every
stitch, in the thread colours of the PES), NOT from the art pickle. DST coordinates + the file's recorded origin = piece mm.
Columns: MOCKUP (front.png mapped to the piece's mm) | CLOSE-UP (inputs/closeup_mockup_koi.png, FR only, mapped through
the cu_register projective fit) | STITCHES (DST read-back), same scale. Zooms: mockup x4 Lanczos | close-up registered
on that motif (per-motif similarity, for motifs traced from the close-up; "no close-up" otherwise) | DST stitches.
usage: python3 compare.py [size]"""
import kbcore, json, sys, math, os, pickle
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import pyembroidery as pe
from scipy.ndimage import map_coordinates
import stitchrender as SR, mockmap as MM, front as F

size = sys.argv[1] if len(sys.argv) > 1 else "M"
g, mt = F.pieces(size)
FONT = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 20)
FS = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 15)
BB = {"FR": (-300, -60, 0, 520), "FL": (0, -60, 300, 520), "SR": (-10, -110, 260, 470), "SL": (-260, -110, 10, 470)}
REG = json.load(open("trace/closeup_reg.json")); H = np.array(REG["projective"]["H"]); HI = np.linalg.inv(H)
META = pickle.load(open("scene.pkl", "rb"))["meta"]
CU = np.array(Image.open("inputs/closeup_mockup_koi.png").convert("RGB")).astype(np.float32)

def dst_file(P):
    r = json.load(open(f"{kbcore.outdir(P)}/{size}/result_{P}.json"))["full"]; return r["file"], r["origin"]

_ST = {}
def stitches(P):
    """(segments per colour) from the DST read-back, in piece mm; colours from the PES thread list (same stops)"""
    if P not in _ST:
        base, (ox, oy) = dst_file(P)
        d = pe.read(base + ".dst"); cols = [t.hex_color() for t in pe.read(base + ".pes").threadlist]
        segs = []; ci = 0; prev = None
        for x, y, c in d.stitches:
            k = c & pe.COMMAND_MASK; p = (ox + x / 10.0, oy + y / 10.0)
            if k == pe.STITCH:
                if prev is not None: segs.append((ci, prev, p))
                prev = p
            elif k == pe.COLOR_CHANGE: ci += 1; prev = None
            elif k in (pe.TRIM, pe.JUMP): prev = None
            elif k == pe.END: break
        _ST[P] = (segs, cols)
    return _ST[P]

def hexrgb(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def shade(c, f): return tuple(int(max(0, min(255, v + (255 - v) * f if f > 0 else v * (1 + f)))) for v in c)

def render_dst(P, bb, ppm):
    """thread-width lines for every sewn stitch (2x supersampled), on the fabric texture"""
    segs, cols = stitches(P); ss = 2; k = ppm * ss
    W, Hh = int((bb[2] - bb[0]) * ppm), int((bb[3] - bb[1]) * ppm)
    base = SR.fabric(W * ss, Hh * ss, k, kbcore.FABRIC).convert("RGB"); d = ImageDraw.Draw(base)
    w = max(1, int(round(0.36 * k))); wh = max(1, int(round(0.12 * k)))
    tf = lambda p: ((p[0] - bb[0]) * k, (p[1] - bb[1]) * k)
    for ci, a, b in segs:
        if max(a[0], b[0]) < bb[0] - 8 or min(a[0], b[0]) > bb[2] + 8 or max(a[1], b[1]) < bb[1] - 8 or min(a[1], b[1]) > bb[3] + 8: continue
        c = hexrgb(cols[min(ci, len(cols) - 1)]); A, B = tf(a), tf(b)
        d.line([A, B], fill=shade(c, -0.28), width=w + max(1, ss))
        d.line([A, B], fill=c, width=w)
        if math.hypot(B[0] - A[0], B[1] - A[1]) > 3 * w:
            m0 = (A[0] + (B[0] - A[0]) * 0.3, A[1] + (B[1] - A[1]) * 0.3); m1 = (A[0] + (B[0] - A[0]) * 0.6, A[1] + (B[1] - A[1]) * 0.6)
            d.line([m0, m1], fill=shade(c, 0.25), width=wh)
    return base.resize((W, Hh), Image.LANCZOS)

def closeup_global(P, bb, ppm):
    """close-up mapped into piece mm through mm -> mockup px -> close-up px (inverse projective fit); FR only"""
    W, Hh = int((bb[2] - bb[0]) * ppm), int((bb[3] - bb[1]) * ppm)
    out = np.full((Hh, W, 3), 245, np.float32)
    if P != "FR": return Image.fromarray(out.astype(np.uint8))
    xs = bb[0] + (np.arange(W) + 0.5) / ppm; ys = bb[1] + (np.arange(Hh) + 0.5) / ppm
    XX, YY = np.meshgrid(xs, ys); px, py = MM.Pinv(XX, YY)
    Q = np.stack([px, py, np.ones_like(px)], -1) @ HI.T; cx, cy = Q[..., 0] / Q[..., 2], Q[..., 1] / Q[..., 2]
    ok = (cx >= 0) & (cy >= 0) & (cx < CU.shape[1] - 1) & (cy < CU.shape[0] - 1)
    for c in range(3): out[..., c][ok] = map_coordinates(CU[..., c], [cy[ok], cx[ok]], order=1)
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))

def closeup_motif(mot, bb, ppm):
    """close-up resampled so the traced template lands on the motif's position in the art (per-motif similarity)"""
    W, Hh = int((bb[2] - bb[0]) * ppm), int((bb[3] - bb[1]) * ppm)
    xs = bb[0] + (np.arange(W) + 0.5) / ppm; ys = bb[1] + (np.arange(Hh) + 0.5) / ppm
    XX, YY = np.meshgrid(xs, ys)
    kind, info = mot
    if kind == "lily":
        import kb_traced as KT
        tp = KT.TPL["flowers"][info["template"]]; s = info["R"] / KT.tip_dist(info["template"]); th = -math.radians(info["rot"])
        dx, dy = XX - info["c"][0], YY - info["c"][1]
        u = (dx * math.cos(th) - dy * math.sin(th)) / s; v = (dx * math.sin(th) + dy * math.cos(th)) / s
        if info["mirror"]: u = -u
        cx, cy = tp["c"][0] + u, tp["c"][1] + v
    else:
        import kb_traced as KT
        t = KT.TPL["koi"][info["template"]]; hd, tl = np.array(t["head"], float), np.array(t["tail"], float); mid = (hd + tl) / 2
        a0 = math.atan2(*(hd - tl)[::-1]); s = info["L"] / t["L"]; th = -math.radians(info["ang"])
        dx, dy = XX - info["c"][0], YY - info["c"][1]
        u = (dx * math.cos(th) - dy * math.sin(th)) / s; v = (dx * math.sin(th) + dy * math.cos(th)) / s
        if info["mirror"]: v = -v
        cx = mid[0] + u * math.cos(a0) - v * math.sin(a0); cy = mid[1] + u * math.sin(a0) + v * math.cos(a0)
    out = np.full((Hh, W, 3), 245, np.float32); ok = (cx >= 0) & (cy >= 0) & (cx < CU.shape[1] - 1) & (cy < CU.shape[0] - 1)
    for c in range(3): out[..., c][ok] = map_coordinates(CU[..., c], [cy[ok], cx[ok]], order=1)
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))

ART_INFO = pickle.load(open(f"art_{size}.pkl", "rb"))["info"]
def _moved(info, key):
    """apply the per-size fitting move (art_size: nudge dx, dy) recorded for that unit / cluster"""
    mv = ART_INFO.get(info["piece"], {}).get("moves", {}).get(key)
    c = list(info["c"])
    if mv: c = [c[0] + mv[0], c[1] + mv[1]]
    return dict(info, c=c)

def motif(unit):
    for l in META.get("lilies", []):
        if l["unit"] == unit: return ("lily", _moved(l, unit.rsplit("_", 1)[0]))
    for k in META["koi"]:
        if k["unit"] == unit: return ("koi", _moved(k, unit))
    return None

def outline(im, bb, ppm, P):
    d = ImageDraw.Draw(im); c = F.clip_for(size, P)
    for poly in (c.geoms if c.geom_type == "MultiPolygon" else [c]):
        d.line([((x - bb[0]) * ppm, (y - bb[1]) * ppm) for x, y in poly.exterior.coords], fill=(255, 90, 90), width=1)
    if P in ("FR", "FL"):
        w_ = F.keep_geoms(size, P)["welt"]; d.polygon([((x - bb[0]) * ppm, (y - bb[1]) * ppm) for x, y in w_.exterior.coords], outline=(150, 150, 170))

# zooms: (piece, bbox mm, caption, close-up motif unit or None). Motif positions are the size-M art (art_M.pkl).
ZOOMS = {"01": [("FR", (-245, 78, -125, 198), "FR big lily (close-up flower 1) + vine leaves", "FR_vine_flower0"),
                ("FR", (-225, 150, -125, 250), "FR mid lily (close-up flower 2)", "FR_vine_flower1"),
                ("FR", (-150, 40, -60, 130), "FR koi pair (close-up koi 1 + 2)", "koi1"),
                ("FR", (-120, 190, -30, 280), "FR koi (close-up koi 4)", "koi4"),
                ("FR", (-250, 260, -150, 360), "FR vine leaves (lit edges)", None),
                ("FR", (-100, 400, -10, 490), "FR hem lily + dark leaves", None),
                ("FL", (55, 365, 215, 500), "FL hem lily pair (big lily + dark flower)", None),
                ("FL", (170, 330, 265, 480), "FL dark flower + side vine", None),
                ("FL", (75, 205, 175, 305), "FL koi school", None)],
         "02": [("SR", (20, 55, 110, 145), "SR top koi", None), ("SR", (25, 330, 115, 420), "SR koi + petals", None),
                ("SR", (15, 375, 125, 465), "SR cuff flower cluster", None), ("SL", (-115, 245, -25, 335), "SL long koi", None),
                ("SL", (-155, 330, -65, 420), "SL koi near cuff", None), ("SL", (-155, 105, -65, 195), "SL petals", None)]}

def sheet(el):
    pcs = kbcore.ELEMS[el][2]; ppm = 1.6; cols = []
    for P in pcs:
        bb = BB[P]
        mk = MM.warp_piece(P, bb, ppm, mt); st = render_dst(P, bb, ppm); outline(st, bb, ppm, P)
        cu = closeup_global(P, bb, ppm) if P == "FR" else None
        cols.append((P, [("mockup", mk)] + ([("close-up (registered)", cu)] if cu is not None else []) + [(f"stitches (DST {size})", st)]))
    W0 = sum(sum(im.width + 6 for _, im in c) + 24 for _, c in cols); H0 = max(c[0][1].height for _, c in cols)
    zw = 330; zs = ZOOMS[el]; per = 2; rows = (len(zs) + per - 1) // per; zrow_w = per * (3 * zw + 12 + 30)
    out = Image.new("RGB", (max(W0, zrow_w) + 20, 80 + H0 + 30 + rows * (zw + 60) + 10), "white"); d = ImageDraw.Draw(out)
    files = ", ".join(os.path.basename(dst_file(P)[0]) + ".dst" for P in pcs)
    d.text((10, 6), f"{el} {kbcore.ELEMS[el][1]} — {kbcore.REV_EMB}: mockup | close-up | STITCHES READ BACK FROM THE DST, same scale. Red = keep-outs.", fill="black", font=FONT)
    d.text((10, 34), f"Stitch columns are drawn from {files} (every sewn stitch, thread colours from the PES), not from the art. "
                     f"Close-up registered by a projective fit (mean residual {REG['projective']['mean_mm']} mm: positions follow the mockup, structure the close-up).", fill=(60, 60, 60), font=FS)
    x = 10; pos = {}
    for P, c in cols:
        pos[P] = []
        for lab, im in c:
            out.paste(im, (x, 70)); d.text((x + 4, 74), f"{P} {lab}", fill=(255, 255, 0), font=FS); pos[P].append(x); x += im.width + 6
        x += 24
    y0 = 70 + H0 + 30
    for k, (P, zb, cap, unit) in enumerate(zs):
        zp = zw / (zb[2] - zb[0]); hz = int((zb[3] - zb[1]) * zp)
        mk = MM.warp_piece(P, zb, zp / 4, mt).resize((zw, hz), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
        mot = motif(unit) if unit else None
        if mot: cu = closeup_motif(mot, zb, zp)
        else:
            cu = Image.new("RGB", (zw, hz), (235, 235, 235)); ImageDraw.Draw(cu).text((12, hz // 2 - 10), "no close-up of this motif\n(drawn from the mockup + the\ntraced close-up templates)", fill=(90, 90, 90), font=FS)
        st = render_dst(P, zb, zp)
        cx = 10 + (k % per) * (3 * zw + 12 + 30); cy = y0 + (k // per) * (zw + 60)
        for j, im in enumerate((mk, cu, st)): out.paste(im, (cx + j * (zw + 6), cy + 26))
        d.text((cx, cy + 2), f"{k + 1}. {cap}   (mockup x4 | close-up | DST stitches)", fill="black", font=FS)
        bb = BB[P]
        for X in pos[P]:
            d.rectangle([X + (zb[0] - bb[0]) * 1.6, 70 + (zb[1] - bb[1]) * 1.6, X + (zb[2] - bb[0]) * 1.6, 70 + (zb[3] - bb[1]) * 1.6], outline=(255, 40, 40), width=2)
            d.text((X + (zb[0] - bb[0]) * 1.6 + 3, 70 + (zb[1] - bb[1]) * 1.6 + 2), str(k + 1), fill=(255, 40, 40), font=FONT)
    fn = f"out/compare_{el}_{kbcore.ELEMS[el][0]}.png"; out.save(fn); return fn, out.size

if __name__ == "__main__":
    for el in kbcore.ELEMS: print(el, sheet(el))
