"""compare_<element>.png from the FINAL stitch files (size M / grade B): close-up (tracing reference) | the DST itself
drawn stitch by stitch (thread colours, 0.42 mm thread width), same scale, same framing; plus a row of zoomed regions
(close-up | DST pairs at 3x the sheet scale). Back: one registration (moon) for close-up px -> mm.
Front / sleeves: the close-up and our placement differ (mockup placement), so zooms are framed per object."""
import json, math
import numpy as np
import pyembroidery as pe
from PIL import Image, ImageDraw
import moonpal, closeart as CA

A = json.load(open("out/results/all.json")); M = A["sizes"]["M"]; B = A["grades"]["B"]
_cache = {}
def dst_img(entries, mmbox, ppm, bg=(37, 48, 77)):
    x0, y0, x1, y1 = mmbox
    im = Image.new("RGB", (int((x1 - x0) * ppm), int((y1 - y0) * ppm)), bg); d = ImageDraw.Draw(im)
    w = max(1, int(round(0.42 * ppm)))
    for r in entries:
        if r["file"] not in _cache: _cache[r["file"]] = pe.read(r["file"] + ".pes")
        p = _cache[r["file"]]; cx, cy = r["centre"]; cols = [t.hex_color() for t in p.threadlist]; ci = 0; prev = None
        for x, y, c in p.stitches:
            k = c & pe.COMMAND_MASK; P = ((x / 10 + cx - x0) * ppm, (y / 10 + cy - y0) * ppm)
            if k == pe.STITCH:
                if prev: d.line([prev, P], fill=cols[min(ci, len(cols) - 1)], width=w)
                prev = P
            elif k == pe.COLOR_CHANGE: ci += 1; prev = None
            else: prev = None
    return im
cx, cy, r = CA.CU_MOON; s0 = 120.0 / r
def bmm(px, py): return ((px - cx) * s0, 244 + (py - cy) * s0)

import os
QA = json.load(open("out/qa_fidelity.json")) if os.path.exists("out/qa_fidelity.json") else {}
FAM = {"01_moon": ("01", ("moon", "stars", "uncovered")), "01_pole": ("01", ("pole", "wires", "wires_missing", "uncovered")),
       "01_clouds_left": ("01", ("clouds", "uncovered")), "01_clouds_right": ("01", ("clouds", "uncovered")),
       "02_03_front": ("02_03", ("clouds", "pole", "wires", "wires_missing", "uncovered")), "04_04R": ("04R", ("clouds", "uncovered")), "04_04L": ("04L", ("clouds", "uncovered"))}
def qa_lines(name):
    if name not in FAM or FAM[name][0] not in QA: return ["FIDELITY GATES: qa_fidelity.py not run"]
    el, fams = FAM[name]; R_ = QA[el]
    L = [f"FIDELITY GATES ({el}, shipped DST vs close-up pixels; qa.motif_match IoU >= 0.70, w/h >= 80 %; qa.uncovered gaps >= 25 mm2; LESSONS A14/A15)"]
    for f in fams:
        rr = R_.get(f, [])
        if f in ("uncovered", "wires_missing"):
            what = "uncovered (qa.uncovered)" if f == "uncovered" else "close-up wire not stitched (qa.uncovered on wire pixels outside every stitched wire)"
            L.append(f"  {what}: {len(rr)} gap(s) >= 25 mm2" + ("" if rr else " - PASS"))
            for r in rr[:12]:
                why = r.get("why"); L.append(f"      {'explained' if why else 'FAIL'} ({r['x_mm']}, {r['y_mm']}) {r['area_mm2']} mm2" + (f": {why}" if why else ""))
        elif f == "wires":
            tr = [r for r in rr if not r.get("generated")]; gen = [r for r in rr if r.get("generated")]
            L.append(f"  wires: {sum(r['ok'] for r in tr)}/{len(tr)} traced wires pass (per wire: IoU >= 0.70 = stitched path within ~1.6 mm of the close-up wire)")
            for r in tr:
                L.append(f"      {'ok  ' if r['ok'] else 'FAIL'} {r['motif']}: IoU {r['iou']}, w {r['w_ratio']}, h {r['h_ratio']} ({r.get('stretches', 1)} visible stretch(es))")
            if gen: L.append("      generated, not traced (no close-up wire in the corridor): " + ", ".join(r["motif"] for r in gen))
        else:
            ok = sum(r["ok"] for r in rr)
            L.append(f"  {f}: {ok}/{len(rr)} motifs pass" + "".join(f" | #{r['motif']} ({r['x_mm']}, {r['y_mm']}) {r['area_mm2']} mm2 IoU {r['iou']} w {r['w_ratio']} h {r['h_ratio']} {'ok' if r['ok'] else 'FAIL'}" for r in rr[:4]))
            for r in [r for r in rr if not r["ok"]][:10]:
                L.append(f"      FAIL #{r['motif']} at ({r['x_mm']}, {r['y_mm']}) {r['area_mm2']} mm2: IoU {r['iou']}, w {r['w_ratio']}, h {r['h_ratio']}")
    return L

def sheet(name, img, pxbox, entries, mmbox, ppm, zooms=(), note="", zf=3):
    """zooms: [(label, close-up px box, mm box)] — each drawn at 3x ppm"""
    ours = dst_img(entries, mmbox, ppm); cu = img.crop(pxbox).resize(ours.size, Image.LANCZOS)
    W = ours.width * 2 + 20
    zs = []
    for lab, zb, mb in zooms:
        zo = dst_img(entries, mb, ppm * zf); zc = img.crop(zb).resize(zo.size, Image.LANCZOS); zs.append((lab, zc, zo))
    zh = max([z[1].height for z in zs], default=0)
    # fit the zoom pairs in rows of the sheet width
    rows, cur, cw = [], [], 0
    for z in zs:
        w_ = z[1].width * 2 + 30
        if cur and cw + w_ > W: rows.append(cur); cur, cw = [], 0
        cur.append(z); cw += w_
    if cur: rows.append(cur)
    QL = qa_lines(name)
    H = ours.height + 30 + sum(max(z[1].height for z in rw) + 26 for rw in rows) + 14 * len(QL) + 20
    out = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(out)
    d.text((4, 4), f"{name}: CLOSE-UP (left) | FINAL DST size M / grade B, drawn stitch by stitch (right), same scale {ppm:g} px/mm. {note}", fill=(200, 0, 0))
    out.paste(cu, (0, 24)); out.paste(ours, (ours.width + 20, 24))
    y = ours.height + 30
    for rw in rows:
        x = 0
        for lab, zc, zo in rw:
            d.text((x + 2, y), f"zoom {lab} (x{zf:g}): close-up | DST", fill=(200, 0, 0))
            out.paste(zc, (x, y + 14)); out.paste(zo, (x + zc.width + 6, y + 14)); x += zc.width * 2 + 30
        y += max(z[1].height for z in rw) + 26
    for i, l in enumerate(QL): d.text((6, y + 6 + 14 * i), l, fill=(0, 0, 0) if "FAIL" not in l else (200, 0, 0))
    out.save(f"out/compare_{name}.png")

def bz(lab, px0, py0, px1, py1):
    a = bmm(px0, py0); b = bmm(px1, py1); return (lab, (px0, py0, px1, py1), (a[0], a[1], b[0], b[1]))

back = [M["back"], M["moonbox"]]
def bsheet(nm, box, zooms, ppm=4):
    a = bmm(box[0], box[1]); b = bmm(box[2], box[3]); sheet(nm, CA.CB, box, back, (a[0], a[1], b[0], b[1]), ppm, zooms)
bsheet("01_moon", (440, 10, 1010, 580), [bz("star crater", 600, 80, 700, 180), bz("cell rim ring", 450, 240, 550, 340),
                                          bz("star + centre", 800, 190, 900, 290), bz("swirl ground", 650, 330, 750, 430)])
bsheet("01_pole", (430, 480, 1040, 1086), [bz("pins + crossarm", 790, 520, 950, 640), bz("coil + spool", 450, 720, 610, 820),
                                            bz("drum transformer", 750, 660, 870, 870), bz("cone insulator", 760, 890, 880, 980),
                                            bz("traced wires, lower left", 40, 820, 520, 1080), bz("wire wrap + right wires", 980, 620, 1440, 900)])
bsheet("01_clouds_left", (20, 160, 660, 740), [bz("dome + scales", 270, 180, 450, 280), bz("tail", 40, 250, 240, 320),
                                                bz("lower cloud", 150, 560, 400, 680)])
bsheet("01_clouds_right", (880, 260, 1448, 660), [bz("dome", 1100, 270, 1300, 380), bz("lower dome", 1080, 480, 1280, 580),
                                                  bz("tail", 1250, 560, 1440, 620)])
sheet("02_03_front", CA.CF, (0, 0, 1448, 1086), [M["03L"], M["03R"], B["02R"], B["02L"]], (-300, 60, 300, 512), 2.5,
      note="Front: our placement follows the mockup (close-up is framed differently) - compare shapes, not positions.", zf=1.6,
      zooms=[("02R chest clouds", (0, 0, 640, 446), (-290, 60, -10, 255)), ("02L chest clouds", (880, 100, 1448, 373), (15, 120, 285, 250)),
             ("03L pole + hardware", (930, 470, 1400, 1091), (148, 320, 288, 505)),
             ("fan wires across the zip", (300, 650, 1000, 1040), (-59.5, 373, 168.7, 507))])
import moonpattern, pattern as PT
g, mt = PT.draft("M")
for k, half in (("04R", (0, 0, 724, 1086)), ("04L", (724, 0, 1448, 1086))):
    sp = g["S01" if k == "04R" else "S02"].sew_poly().bounds
    hx0, hy0, hx1, hy1 = half; hm = (hx0 + hx1) / 2
    zz = [("upper back half (approx. framing)", (hx0, 60, hm, 420), (sp[0], sp[1], (sp[0] + sp[2]) / 2, sp[1] + (sp[3] - sp[1]) * 0.36)),
          ("upper front half (approx. framing)", (hm, 60, hx1, 420), ((sp[0] + sp[2]) / 2, sp[1], sp[2], sp[1] + (sp[3] - sp[1]) * 0.36))]
    sheet(f"04_{k}", CA.CS, half, [B[k]], sp, 2.5, note="Sleeve: 2 close-up views per sleeve -> one sleeve piece (back half | front half).", zooms=zz, zf=1.6)
print("ok")
