"""Fidelity sheets (LESSONS A11-A15), Rev C: out/compare_01_front-fish.png + out/compare_02_sleeve-fish.png.
Columns: MOCKUP (front.png mapped to the piece mm) | CLOSE-UP (FR: the close-up lilies in their registration discs) |
STITCHES = the size-M DST read back (every sewn stitch, PES thread colours), same scale.
Zooms (4 panes, same scale): mockup x4 | REFERENCE (close-up disc / the founder's reference tetra laid on the mockup
fish pose) | DST stitches | REFERENCE OUTLINE (yellow, refmask.py = input pixels only) over the DST stitches.
Gate tables (fidelity.py) printed under the sheet.   usage: python3 compare.py [size]"""
import kbcore, json, sys, math, os, pickle
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import pyembroidery as pe
from scipy.ndimage import map_coordinates
from scipy import ndimage as ndi
import stitchrender as SR, mockmap as MM, front as F

size = sys.argv[1] if len(sys.argv) > 1 else "M"
g, mt = F.pieces(size)
FONT = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 20)
FS = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 15)
BB = {"FR": (-300, -60, 0, 520), "FL": (0, -60, 300, 520), "SR": (-10, -110, 260, 470), "SL": (-260, -110, 10, 470)}
REG = json.load(open("trace/closeup_reg.json")); H = np.array(REG["projective"]["H"]); HI = np.linalg.inv(H)
META = pickle.load(open("scene.pkl", "rb"))["meta"]
import refmask as RM
CU = np.array(Image.open("inputs/closeup_mockup_koi.png").convert("RGB")).astype(np.float32)
RF = np.array(Image.open("inputs/reference_fish.png").convert("RGB")).astype(np.float32)

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

def resample(img, P, bb, ppm):
    """an image on refmask's piece grid (RM.BB[P], RM.PPM) resampled to bbox bb at ppm"""
    W, Hh = int((bb[2] - bb[0]) * ppm), int((bb[3] - bb[1]) * ppm); B = RM.BB[P]
    xs = (bb[0] + (np.arange(W) + 0.5) / ppm - B[0]) * RM.PPM - 0.5; ys = (bb[1] + (np.arange(Hh) + 0.5) / ppm - B[1]) * RM.PPM - 0.5
    XX, YY = np.meshgrid(xs, ys); img = np.asarray(img, np.float32)
    if img.ndim == 2: return map_coordinates(img, [YY, XX], order=1, cval=0)
    return np.stack([map_coordinates(img[..., c], [YY, XX], order=1, cval=245) for c in range(img.shape[2])], -1)

def reference_pane(P, bb, ppm, kind):
    """close-up disc (lily zooms) or the reference tetra laid on the mockup fish poses (fish zooms)"""
    if kind == "fish":
        rf = RM.ref_fish_mask(); XX, YY = RM.grid(P); out = np.full(XX.shape + (3,), 245, np.float32)
        out[:] = np.array([12, 16, 38], np.float32)
        sn, tt = np.array(RM.RF_SNOUT), np.array(RM.RF_TAILTIP); Lr = np.hypot(*(sn - tt)); er = (sn - tt) / Lr
        nr = np.array([-er[1], er[0]]); nr = nr if nr[1] > 0 else -nr; midr = (sn + tt) / 2
        for pose, m in RM.fish_ref(P):
            L = pose["L_ref"]; a = math.radians(pose["ang"]); e = np.array([math.cos(a), math.sin(a)]); nrm = np.array([-e[1], e[0]]); nrm = nrm if nrm[1] >= 0 else -nrm
            c = np.array(pose["c"]); dx, dy = XX - c[0], YY - c[1]
            u = (dx * e[0] + dy * e[1]) / L; v = (dx * nrm[0] + dy * nrm[1]) / L
            cx = midr[0] + u * Lr * er[0] + v * Lr * nr[0]; cy = midr[1] + u * Lr * er[1] + v * Lr * nr[1]
            ok = m
            for ch in range(3): out[..., ch][ok] = map_coordinates(rf["im"][..., ch], [cy[ok], cx[ok]], order=1)
        return Image.fromarray(resample(out, P, bb, ppm).clip(0, 255).astype(np.uint8))
    rgb, zone, _ = RM.source(P)
    img = np.where(zone[..., None], rgb, 235.0)
    return Image.fromarray(resample(img, P, bb, ppm).clip(0, 255).astype(np.uint8))

def ref_outline(im, P, bb, ppm):
    """yellow outline of the gate reference (flora + fish, refmask.py) drawn over a pane"""
    ref = RM.flora(P) | np.any([m for _, m in RM.fish_ref(P)] or [np.zeros_like(RM.flora(P))], axis=0)
    r = resample(ref.astype(np.float32), P, bb, ppm) > 0.5
    edge = r & ~ndi.binary_erosion(r, iterations=1)
    a = np.array(im); a[edge] = (255, 230, 0); return Image.fromarray(a)

def outline(im, bb, ppm, P):
    d = ImageDraw.Draw(im); c = F.clip_for(size, P)
    for poly in (c.geoms if c.geom_type == "MultiPolygon" else [c]):
        d.line([((x - bb[0]) * ppm, (y - bb[1]) * ppm) for x, y in poly.exterior.coords], fill=(255, 90, 90), width=1)
    if P in ("FR", "FL"):
        w_ = F.keep_geoms(size, P)["welt"]; d.polygon([((x - bb[0]) * ppm, (y - bb[1]) * ppm) for x, y in w_.exterior.coords], outline=(150, 150, 170))

# zooms: (piece, bbox mm, caption, reference kind: "closeup" | "fish" | None)
ZOOMS = {"01": [("FR", (-250, 85, -135, 200), "FR big lily (close-up lily 1) + vine leaves", "closeup"),
                ("FR", (-225, 150, -110, 265), "FR mid lily (close-up lily 2)", "closeup"),
                ("FR", (-195, 15, -95, 115), "FR fish (tetra)", "fish"),
                ("FR", (-125, 195, -25, 295), "FR fish (tetra)", "fish"),
                ("FR", (-265, 255, -150, 370), "FR vine leaves + stems (traced leaf by leaf)", None),
                ("FR", (-95, 400, -10, 485), "FR hem lily (traced from the mockup)", None),
                ("FL", (60, 395, 190, 495), "FL hem big lily (traced from the mockup)", None),
                ("FL", (175, 360, 280, 495), "FL dark flower + side vine (traced)", None),
                ("FL", (85, 150, 245, 290), "FL fish school", "fish")],
         "02": [("SR", (35, 20, 135, 110), "SR top fish", "fish"), ("SR", (55, 160, 160, 260), "SR fish", "fish"),
                ("SR", (5, 380, 125, 480), "SR cuff lily + leaves (traced from the mockup)", None), ("SL", (-125, 235, -20, 340), "SL fish", "fish"),
                ("SL", (-195, 385, -90, 480), "SL fish near cuff (head down-left, as the mockup)", "fish"), ("SL", (-175, 90, -60, 205), "SL petals", None)]}

def sheet(el):
    pcs = kbcore.ELEMS[el][2]; ppm = 1.6; cols = []
    for P in pcs:
        bb = BB[P]
        mk = MM.warp_piece(P, bb, ppm, mt); st = render_dst(P, bb, ppm); outline(st, bb, ppm, P)
        cu = reference_pane(P, bb, ppm, "closeup") if P == "FR" else None
        cols.append((P, [("mockup", mk)] + ([("close-up lilies (registered)", cu)] if cu is not None else []) + [(f"stitches (DST {size})", st)]))
    W0 = sum(sum(im.width + 6 for _, im in c) + 24 for _, c in cols); H0 = max(c[0][1].height for _, c in cols)
    zw = 300; zs = ZOOMS[el]; per = 2; rows = (len(zs) + per - 1) // per; zrow_w = per * (4 * zw + 18 + 30)
    out = Image.new("RGB", (max(W0, zrow_w) + 20, 80 + H0 + 30 + rows * (zw + 70) + 10), "white"); d = ImageDraw.Draw(out)
    files = ", ".join(os.path.basename(dst_file(P)[0]) + ".dst" for P in pcs)
    d.text((10, 6), f"{el} {kbcore.ELEMS[el][1]} — {kbcore.REV_EMB}: mockup | close-up | STITCHES READ BACK FROM THE DST, same scale. Red = keep-outs.", fill="black", font=FONT)
    d.text((10, 34), f"Stitch columns are drawn from {files} (every sewn stitch, thread colours from the PES), not from the art. Yellow outline in the 4th zoom pane = the gate reference "
                     f"(refmask.py: input pixels only). Fish = reference_fish.png tetra at the mockup fish poses, 0.82 x the mockup length (founder decision 19 Oct).", fill=(60, 60, 60), font=FS)
    x = 10; pos = {}
    for P, c in cols:
        pos[P] = []
        for lab, im in c:
            out.paste(im, (x, 70)); d.text((x + 4, 74), f"{P} {lab}", fill=(255, 255, 0), font=FS); pos[P].append(x); x += im.width + 6
        x += 24
    y0 = 70 + H0 + 30
    for k, (P, zb, cap, kind) in enumerate(zs):
        zp = zw / (zb[2] - zb[0]); hz = int((zb[3] - zb[1]) * zp)
        mk = MM.warp_piece(P, zb, zp / 4, mt).resize((zw, hz), Image.LANCZOS).filter(ImageFilter.UnsharpMask(2, 60, 2))
        if kind: rf = reference_pane(P, zb, zp, kind)
        else:
            rf = Image.new("RGB", (zw, hz), (235, 235, 235)); ImageDraw.Draw(rf).text((12, hz // 2 - 20), "no close-up of this motif:\ntraced from the mockup pixels\n(1 px/mm; guides read on 8-10x zooms)", fill=(90, 90, 90), font=FS)
        st = render_dst(P, zb, zp); ov = ref_outline(st, P, zb, zp)
        cx = 10 + (k % per) * (4 * zw + 18 + 30); cy = y0 + (k // per) * (zw + 70)
        for j, im in enumerate((mk, rf, st, ov)): out.paste(im, (cx + j * (zw + 6), cy + 26))
        d.text((cx, cy + 2), f"{k + 1}. {cap}   (mockup x4 | " + ({"fish": "FISH REFERENCE at the mockup pose", "closeup": "close-up"}.get(kind, "-")) + " | DST stitches | reference outline on DST)", fill="black", font=FS)
        bb = BB[P]
        for X in pos[P]:
            d.rectangle([X + (zb[0] - bb[0]) * 1.6, 70 + (zb[1] - bb[1]) * 1.6, X + (zb[2] - bb[0]) * 1.6, 70 + (zb[3] - bb[1]) * 1.6], outline=(255, 40, 40), width=2)
            d.text((X + (zb[0] - bb[0]) * 1.6 + 3, 70 + (zb[1] - bb[1]) * 1.6 + 2), str(k + 1), fill=(255, 40, 40), font=FONT)
    FDJ = json.load(open(f"out/fidelity_{size}.json"))
    lines = gate_lines(FDJ, pcs)
    yy = out.height; ext = Image.new("RGB", (out.width, out.height + 22 * len(lines) + 20), "white"); ext.paste(out, (0, 0)); d2 = ImageDraw.Draw(ext)
    for i, l in enumerate(lines): d2.text((10, yy + 8 + 22 * i), l, fill=(180, 0, 0) if ("FAIL" in l or "GAP" in l) else (0, 0, 0), font=FONT if i == 0 else FS)
    fn = f"out/compare_{el}_{kbcore.ELEMS[el][0]}.png"; ext.save(fn); return fn, ext.size

def gate_lines(FDJ, pcs):
    L = ["FIDELITY GATES (LESSONS A13/A14/A15) on the shipped DSTs — reference masks from INPUT PIXELS ONLY (refmask.py); qa.motif_match IoU >= 0.70, w + h >= 80 %; qa.uncovered gaps >= 25 mm2"]
    for P in pcs:
        r = FDJ[P]; fams = r["rows"]
        summ = "  ".join(f"{fam}: {sum(x['ok'] for x in rs)}/{len(rs)} pass, min IoU {min([x['iou'] for x in rs] or [1]):.2f}" for fam, rs in fams.items() if rs)
        L.append(f"{P} ({os.path.basename(r['dst'])}): {summ}  |  bare gaps >= 25 mm2: {len(r['gaps'])}  |  mockup blue in the band keep-out strip: {r['band_zone_mm2']} mm2 (asked, item 6)")
        for x in fams.get("lilies", []):
            t = x.get("tone") or {}
            L.append(f"   lily {x['motif']} ({x['ref']}): IoU {x['iou']}, w {x['w_ratio']}, h {x['h_ratio']}; tone r {t.get('r')}, quartiles exact {t.get('exact')} / within one {t.get('within1')}; "
                     f"stitch rows vs petal axis: median {x['row_dir_median_deg']} deg, {x['rows_along_pct']} % within 30 deg")
        ft = [x.get("tone") for x in fams.get("fish", []) if x.get("tone")]
        if ft: L.append(f"   fish facets: tone r {np.mean([t['r'] for t in ft]):.2f} (min {min(t['r'] for t in ft):.2f}), quartiles within one {np.mean([t['within1'] for t in ft]):.2f} (mean of {len(ft)} fish)")
        ct = [x.get("tone") for x in fams.get("clusters", []) if x.get("tone")]
        if ct: L.append(f"   clusters: tone r {np.mean([t['r'] for t in ct]):.2f} (min {min(t['r'] for t in ct):.2f}), quartiles within one {np.mean([t['within1'] for t in ct]):.2f}")
        for fam, rs in fams.items():
            for x in rs:
                if not x["ok"]: L.append(f"   FAIL {fam} at ({x['x_mm']}, {x['y_mm']}) {x['area_mm2']} mm2: IoU {x['iou']}, w {x['w_ratio']}, h {x['h_ratio']}")
        for g_ in r["gaps"]: L.append(f"   GAP at ({g_['x_mm']}, {g_['y_mm']}) {g_['w_mm']} x {g_['h_mm']} mm, {g_['area_mm2']} mm2")
    L.append("Reference masks: flora = mockup pixels (close-up pixels in the 2 FR lily discs), garment details + mockup fish masked first, stems included, no art; "
             "fish = reference_fish.png pixels at the pose measured on the mockup fish pixels. DST masks: every stitch as a 0.2 mm line (needle points), closed 0.6 mm, no hole filling. Tone r = rank correlation of reference vs stitched luminance.")
    return L

if __name__ == "__main__":
    for el in kbcore.ELEMS: print(el, sheet(el))
