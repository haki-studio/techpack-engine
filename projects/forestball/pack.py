"""Embroidery pack G1–G5 + element specs -> out/HAKI_FB_EMBROIDERY-PACK_RevA.pdf. Every count is read from the DST results."""
import os, json, pickle, glob
import fbcore
import cairosvg
from PIL import Image
from shapely.ops import unary_union
from pypdf import PdfWriter, PdfReader
from sheet import t, swatch, doc, INK, MUTED, RED, ORANGE, GUIDE, GREEN, SW, SH
from render import f
from motifs2 import HEX, PAL
import tech, stitchrender as SR
import specbase as SB
from specbase import img_tag
import front as F, back as B
import spec_front as SPF
import emb_place as EP

REV = fbcore.REV_EMB; DATE = fbcore.DATE
FOOT = f"HAKI STUDIOS · {fbcore.NAME} · EMBROIDERY · {REV} · {DATE}"
VB = pickle.load(open("back_vis.pkl", "rb"))["back"]; VF = pickle.load(open("front_vis.pkl", "rb"))
PIECES = [("01", "Back scene", "back panel", VB, "back"), ("02", "Chest mossy branch", "02R wearer's right front + hanging moss", VF["02R"], "02R"),
          ("02", "Chest mossy branch", "02L wearer's left front", VF["02L"], "02L")]
BB = [unary_union([r["geom"] for r in v]).bounds for *_, v, _ in PIECES]
CUR = json.load(open("dst_current.json")); SPL = json.load(open("dst_current_splits.json")); ALL = json.load(open("dst_all.json"))
QA = json.load(open("qa_width.json"))
PH = B.PH_BOX.bounds
OUT_PDF = f"out/HAKI_FB_EMBROIDERY-PACK_{REV.replace(' ', '')}.pdf"

def hdr(title, sub, page):
    SB.FOOT = FOOT; return SB.header(title, sub, page)

def back_png(ppm=2.0):
    p = "out/art/sr_back_pack.png"
    if not os.path.exists(p) or os.path.getmtime(p) < os.path.getmtime("back_vis.pkl"):
        from PIL import ImageDraw
        bx = (-305, -30, 305, 590); img = SR.render(VB, bx, ppm, base=fbcore.FABRIC)
        mask = Image.new("L", img.size, 0); ImageDraw.Draw(mask).polygon([((x-bx[0])*ppm, (y-bx[1])*ppm) for x, y in B.PANEL.exterior.coords], fill=255)
        bg = Image.new("RGB", img.size, (255, 255, 255)); bg.paste(img, (0, 0), mask)
        d = ImageDraw.Draw(bg)
        d.line([((x-bx[0])*ppm, (y-bx[1])*ppm) for x, y in B.PANEL.exterior.coords], fill=(40, 40, 40), width=2)
        d.rectangle([((PH[0]-bx[0])*ppm, (PH[1]-bx[1])*ppm), ((PH[2]-bx[0])*ppm, (PH[3]-bx[1])*ppm)], outline=(220, 40, 40), width=3)
        bg.save(p)
    return Image.open(p)       # covers x -305..305, y -30..590

def cover(index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>']
    o.append(t(14, 24, "HAKI STUDIOS", 3.0, 700, MUTED))
    o.append(t(14, 36, f"{fbcore.NAME} — embroidery", 7.0, 700))
    o.append(t(14, 44, f"{REV} · {DATE} · Drum Island block, size M base · 2 elements, 3 pieces · ≤ 15 threads per file · all dimensions mm", 2.6, 400, MUTED))
    o.append(f'<line x1="14" y1="48" x2="{SW-14}" y2="48" stroke="{INK}" stroke-width="0.4"/>')
    fv = SPF.front_view_png(VF, (-325, -110, 325, 540), 2.0)
    tag, h = img_tag(fv, 14, 54, 92); o.append(tag); o.append(t(14, 54 + h + 3.5, "FRONT", 2.2, 700))
    tag, h2 = img_tag(back_png(), 112, 54, 86); o.append(tag); o.append(t(112, 54 + h2 + 3.5, "BACK (red box = licensed-figure placeholder)", 2.2, 700))
    ix = 206; o.append(t(ix, 58, "CONTENTS", 2.8, 700)); y = 64
    for name, pg in index:
        o.append(t(ix, y, name, 2.0)); o.append(t(SW - 14, y, f"{pg}", 2.0, 600, MUTED, "end")); y += 4.2
    y += 4; o.append(t(ix, y, "TOTALS (size M, read from the DST)", 2.3, 700)); y += 5
    keys = ["back", "02R", "02L"]
    tot = sum(CUR[k]["stitches"] for k in keys); trims = sum(CUR[k]["trims_dst"] for k in keys)
    for a, b in [("Stitches per jacket", f"{tot:,}"), ("Trims per jacket", f"{trims:,}"), ("Hoopings per jacket", "3 (border frame) or 6 (360² splits)"),
                 ("Machine time / jacket", f"≈ {tot/750/60:.1f} h at 750 spm + stops"), ("Threads", f"{len(PAL) - 1} + 1 placement basting")]:
        o.append(t(ix, y, a, 1.95, 400, MUTED)); o.append(t(SW - 14, y, b, 1.95, 600, INK, "end")); y += 4
    y += 3
    for l in ["LICENSED element: the stream orb is NOT in these files —", "placeholder box only (G2, element 01 p1). The factory",
              "digitizer adds it from licensor-approved art."]:
        o.append(t(ix, y, l, 1.9, 600, RED)); y += 3.4
    o.append(t(SW - 14, SH - 8, FOOT, 1.9, 400, MUTED, "end"))
    return o

def overview():
    o = hdr("PLACEMENT OVERVIEW — every element on the garment", "Garment coords. Front: x from CF (+ = wearer's left), y down from the CF neck seam. Back: x from CB, y down from the CB neck seam. Tolerance ±2, rotation ±3°. Size M; per size: T13.", "G2")
    fv = SPF.front_view_png(VF, (-325, -110, 325, 540), 2.6)
    w = 126; s = w / 650; ax, ay = 12, 30
    tag, h = img_tag(fv, ax, ay, w); o.append(tag)
    X = lambda x: ax + (x + 325)*s; Y = lambda y: ay + (y + 110)*s
    for p in ("02R", "02L"):
        b = unary_union([r["geom"] for r in VF[p]]).bounds
        o.append(f'<rect x="{f(X(b[0]))}" y="{f(Y(b[1]))}" width="{f((b[2]-b[0])*s)}" height="{f((b[3]-b[1])*s)}" fill="none" stroke="{RED}" stroke-width="0.3" stroke-dasharray="1.2 0.8"/>')
        o.append(f'<circle cx="{f(X(b[0]))}" cy="{f(Y(b[1]))}" r="2.8" fill="{RED}"/>' + t(X(b[0]), Y(b[1]) + 0.8, p, 1.6, 700, "#FFFFFF", "middle"))
    o.append(t(ax, ay + h + 3.5, "FRONT (0.19:1)", 2.0, 700))
    bk = back_png(); bw = 104; bx = 144
    tag, hb = img_tag(bk, bx, ay, bw); o.append(tag)
    bs = bw / 610; BX = lambda x: bx + (x + 305)*bs; BY = lambda y: ay + (y + 30)*bs
    b = BB[0]
    o.append(f'<rect x="{f(BX(b[0]))}" y="{f(BY(b[1]))}" width="{f((b[2]-b[0])*bs)}" height="{f((b[3]-b[1])*bs)}" fill="none" stroke="{RED}" stroke-width="0.3" stroke-dasharray="1.2 0.8"/>')
    o.append(f'<circle cx="{f(BX(b[0]))}" cy="{f(BY(b[1]))}" r="2.6" fill="{RED}"/>' + t(BX(b[0]), BY(b[1]) + 0.8, "01", 1.7, 700, "#FFFFFF", "middle"))
    o.append(t(bx, ay + hb + 3.5, "BACK (0.17:1) · red box in the stream = LICENSED placeholder", 2.0, 700))
    tx = 252; o.append(t(tx, 30, "ART BOXES", 2.2, 700)); y = 34.5
    for (e, name, piece, v, k), b in zip(PIECES, BB):
        o.append(t(tx, y, f"{e} {piece}"[:30], 1.6, 600)); y += 3.0
        o.append(t(tx + 2, y, f"{b[2]-b[0]:.0f}×{b[3]-b[1]:.0f} · x {b[0]:+.0f}…{b[2]:+.0f}", 1.5, 400, MUTED)); y += 3.0
        o.append(t(tx + 2, y, f"y {b[1]:.0f}…{b[3]:.0f}", 1.5, 400, MUTED)); y += 4
    o.append(t(tx, y, "PLACEHOLDER (01)", 1.7, 700, RED)); y += 3.2
    o.append(t(tx, y, f"{PH[2]-PH[0]:.0f}×{PH[3]-PH[1]:.0f} · x {PH[0]:+.0f}…{PH[2]:+.0f}", 1.5, 400, RED)); y += 3.0
    o.append(t(tx, y, f"y {PH[1]:.0f}…{PH[3]:.0f}  [proposed]", 1.5, 400, RED))
    ky = 166; o.append(t(12, ky, "KEEP-OUTS (all elements, measured from the pattern seams)", 2.2, 700))
    for i, k in enumerate([f"CF zip: {F.KEEP_CF:.0f} each side of CF (teeth + tape + topstitch)",
                           f"Armhole, shoulder, side seams: {F.KEEP_SEAM:.0f} (allowance + topstitch + 3) — back AND front; nothing wraps onto the sleeves",
                           f"Hem-rib seam: {F.KEEP_HEM:.0f} above (rib knit is never embroidered) · welt pocket box: {F.KEEP_WELT:.0f} clear",
                           f"Collar: front {F.KEEP_COLLAR:.0f} clear of the collar lying flat; back {B.KEEP_COLLAR:.0f} below the collar fall ({B.COLLAR_FALL:.0f} below CB neck, proposed)",
                           "Licensed placeholder: nothing stitched inside the box; neighbouring art 1 mm clear of its outline."]):
        o.append(t(12, ky + 4.4 + i*3.4, k, 1.85, 600 if "Licensed" in k else 400, RED if "Licensed" in k else INK))
    return o

def threads():
    o = hdr("THREAD + TRIM SUMMARY", "One palette for the whole jacket. Approve a physical thread board (Isacord or Madeira Polyneon) before sampling; hex = on-screen target read from the mockup [proposed — confirm].", "G3")
    use = {k: {} for k in PAL}
    for (e, name, piece, v, key) in PIECES:
        for s in fbcore.stitch_stops(v):
            use[s["col"]][key] = use[s["col"]].get(key, 0) + s["st"]
    hd = ["", "Thread", "Hex", "Isacord", "ΔE", "Madeira Polyneon", "ΔE", "Wt", "Used for", "Pieces", "Est. st."]
    cx = [12, 18, 46, 60, 90, 98, 132, 140, 148, 222, 262]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.75, 700, MUTED))
    rh = 4.6
    for i, k in enumerate(PAL):
        y = 36 + i*rh
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3)}" width="{SW-22}" height="{f(rh)}" fill="#F5F2EC"/>')
        iso, pn = SB.TH[k]["isacord"], SB.TH[k]["polyneon"]
        o.append(swatch(cx[0], y, k, 4.5, 2.8)); o.append(t(cx[1], y, PAL[k][1], 1.85, 600)); o.append(t(cx[2], y, HEX[k], 1.7, 400, MUTED))
        if k == "basting":
            o.append(t(cx[3], y, "water-soluble basting thread, contrast colour — removed after the licensed figure is sewn", 1.7, 600, RED))
        else:
            ci = GREEN if iso[3] < 3 else (ORANGE if iso[3] < 5.5 else RED); cp = GREEN if pn[3] < 3 else (ORANGE if pn[3] < 5.5 else RED)
            o.append(t(cx[3], y, f"{iso[0]} {iso[1]}"[:22], 1.7)); o.append(t(cx[4], y, f"{iso[3]:.1f}", 1.7, 600, ci))
            o.append(t(cx[5], y, f"{pn[0]} {pn[1]}"[:24], 1.7)); o.append(t(cx[6], y, f"{pn[3]:.1f}", 1.7, 600, cp))
            o.append(t(cx[7], y, "40", 1.7)); o.append(t(cx[8], y, PAL[k][2][:46], 1.65, 400, MUTED))
        o.append(t(cx[9], y, ", ".join(sorted(use[k])) or "—", 1.7)); o.append(t(cx[10], y, f"{sum(use[k].values()):,.0f}", 1.7, 600))
    yb = 36 + len(PAL)*rh + 3
    o.append(t(12, yb, "ΔE2000 vs target: green < 3, amber 3–5.5, red > 5.5 — amber/red rows must be picked from the physical card. Est. st. = area estimate; DST counts on G4/G5.", 1.75, 400, MUTED))
    o.append(t(12, yb + 7, "TRIMS + CONSUMABLES (per jacket)", 2.2, 700))
    for i, (a, b) in enumerate([("Backing", "2.5 oz cutaway, cut 30 larger than each art box; trim to 5 from stitching after embroidery"),
                                ("Topping", "none (canvas surface is firm)"), ("Needles", "75/11 sharp (canvas); change every 8 h on the back scene"),
                                ("Bobbin", "60wt white polyester pre-wound (black bobbin optional under the dark moss)"),
                                ("Frames", f"01 back: border ≥ {BB[0][2]-BB[0][0]+14:.0f} × {BB[0][3]-BB[0][1]+14:.0f} (single file) or 4 × 360² split files (G5) · 02R / 02L: ≤ 360 × 360"),
                                ("Patches / labels", "none on this garment — all artwork is direct embroidery")]):
        o.append(t(12, yb + 11.5 + i*3.6, a, 1.85, 600)); o.append(t(42, yb + 11.5 + i*3.6, b, 1.85))
    return o

def summary():
    o = hdr("STITCH SUMMARY + OPEN QUESTIONS", "", "G4")
    hd = ["Element", "Piece", "Art box", "Stitches", "Trims", "Stops", "Threads", "Run time", "Width check"]
    cx = [12, 50, 112, 134, 152, 166, 180, 196, 214]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.8, 700, MUTED))
    rows = []
    for i, ((e, name, piece, v, k), b) in enumerate(zip(PIECES, BB)):
        d = CUR[k]; y = 36 + i*4.6
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3)}" width="{SW-22}" height="4.6" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, f"{e} {name}", 1.8, 600)); o.append(t(cx[1], y, piece[:34], 1.7))
        o.append(t(cx[2], y, f"{b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}", 1.8)); o.append(t(cx[3], y, f"{d['stitches']:,}", 1.8, 600))
        o.append(t(cx[4], y, f"{d['trims_dst']:,}", 1.8)); o.append(t(cx[5], y, f"{d['stops']}", 1.8)); o.append(t(cx[6], y, f"{d['threads']}", 1.8))
        o.append(t(cx[7], y, f"{d['stitches']/750:.0f} min", 1.8))
        q = QA[k]; wk = max(q, key=lambda c: q[c]["long_pct"]); wv = q[wk]["long_pct"]
        o.append(t(cx[8], y, "all codes pass (< 1 %)" if wv < 1 else f"worst: {wk} {wv:.1f}% — tapered tips; digitizer drops < 0.8", 1.7, 600, GREEN if wv < 1 else ORANGE))
    keys = [p[4] for p in PIECES]; y = 36 + len(PIECES)*4.6 + 1
    tot = sum(CUR[k]["stitches"] for k in keys); tr = sum(CUR[k]["trims_dst"] for k in keys)
    o.append(t(cx[2], y, "TOTAL", 1.9, 700)); o.append(t(cx[3], y, f"{tot:,}", 1.9, 700)); o.append(t(cx[4], y, f"{tr:,}", 1.9, 700)); o.append(t(cx[7], y, f"{tot/750/60:.1f} h", 1.9, 700))
    o.append(t(12, y + 4.5, "Stitches / trims counted from the DST files (grade B = sizes M–XL; trims from the DST read-back). Run time at 750 spm, excluding colour changes + hooping. Max stitch ≤ 7.5 mm in every file.", 1.7, 400, MUTED))
    o.append(t(12, y + 7.8, "Width check = worst region code's share of area below its minimum width (fill/satin 0.8, line 0.6) for > 2.5 mm. Detail per code on each element's p3.", 1.7, 400, MUTED))
    qy = y + 15; o.append(t(12, qy, "OPEN QUESTIONS — confirm before sampling", 2.6, 700))
    qs = [f"1. LICENSED orb: placeholder box {PH[2]-PH[0]:.0f} × {PH[3]-PH[1]:.0f} at the mockup position (stream). Confirm final size + position from the licensor-approved art, who digitizes it, and that",
          "    the licence approval is in place before production (not verified by Haki tech). The figure's stitch file is NOT part of this pack.",
          "2. Grading: A 90 % (XS–S), B 100 % (M–XL), C 108 % (XXL–3XL); one file per grade per piece; every size checked on its pattern (T13). The placeholder grades with the art.",
          f"3. Back frame: single file needs a border frame ≥ {BB[0][2]-BB[0][0]+14:.0f} × {BB[0][3]-BB[0][1]+14:.0f}. Otherwise sew the 4 split files S1–S4 (360 × 360) with basting crosses (G5).",
          "4. Shell: washed forest green duck — piece-dyed + pre-washed before embroidery, or garment-washed after? Wash-test the sew-out (cream, leaf yellow-green shift first).",
          "5. Thread palette read from the mockup (14 + basting) — approve a physical thread board; amber/red ΔE rows picked from the card (G3).",
          "6. Light rays: specced sheer (serpentine run, rows 1.9 apart) per the brief. Approve on the sew-out — denser would read as solid bands.",
          "7. Back collar fall: art stays 6 below a 45 mm collar fall at CB (proposed) — confirm with the sample collar.",
          "8. Retail name 'Forestball': confirm it is not meant to echo Dragon Ball before retail use.",
          "9. DST/PES are production-intent drafts: the factory digitizer opens them, checks density + pull on 12 oz duck and edits before sew-out."]
    for i, q in enumerate(qs): o.append(t(12, qy + 5 + i*3.6, q, 1.75, 600 if i < 2 else 400, RED if i < 2 else INK))
    return o

def files_page():
    o = hdr("PRODUCTION STITCH FILES + HOOP SPLITS", "DST (Tajima) + PES. Counts read back from the files; trims counted from the DST. Origin = centre of each file's design (= the ⊕ on the pattern).", "G5")
    o.append(t(12, 31, "ONE FILE PER ART GRADE: A = XS–S (90 %), B = M–XL (100 %), C = XXL–3XL (108 %)", 2.0, 700))
    hd = ["Piece", "A stitches / trims", "B stitches / trims", "C stitches / trims", "Stops (B)", "Threads", "Max st."]; cx = [12, 34, 72, 110, 148, 162, 174]
    for x_, h in zip(cx, hd): o.append(t(x_, 35.5, h, 1.6, 700, MUTED))
    y = 39.5
    for i, k in enumerate(("back", "02R", "02L")):
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.7)}" width="170" height="3.8" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, "01 back" if k == "back" else k, 1.6, 700))
        for j, G in enumerate("ABC"):
            r = ALL["grades"].get(G, {}).get(k)
            o.append(t(cx[1 + j], y, f"{r['stitches']:,} / {r['trims_dst']}" if r else "pending", 1.55))
        rb = ALL["grades"]["B"][k]; o.append(t(cx[4], y, f"{rb['stops']}", 1.55)); o.append(t(cx[5], y, f"{rb['threads']}", 1.55))
        o.append(t(cx[6], y, f"{max(ALL['grades'][G][k]['max_stitch'] for G in ALL['grades'] if k in ALL['grades'][G]):.1f}", 1.55))
        y += 3.8
    y += 3; o.append(t(12, y, "01 BACK — 360 × 360 SPLITS per grade (stop 1 = basting crosses)", 2.0, 700)); y += 4.5
    hd = ["Grade", "S1", "S2", "S3", "S4", "Fit 344²", "Cut mm"]; cx2 = [12, 26, 56, 86, 116, 148, 164]
    for x_, h in zip(cx2, hd): o.append(t(x_, y, h, 1.6, 700, MUTED))
    y += 4
    for i, G in enumerate("ABC"):
        s = ALL["splits"].get(G)
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.7)}" width="170" height="3.8" fill="#F5F2EC"/>')
        o.append(t(cx2[0], y, G, 1.6, 700))
        if s:
            secs = s["sections"]
            for j, nm in enumerate(sorted(secs)):
                v = secs[nm]; o.append(t(cx2[1 + j], y, f"{v['stitches']/1000:.0f}k / {v['trims_dst']} tr" + (" ▣" if v.get("placeholder") else ""), 1.55))
            o.append(t(cx2[5], y, "✓ all" if all(v["fits"] for v in secs.values()) else "CHECK", 1.55, 700, GREEN if all(v["fits"] for v in secs.values()) else RED))
            o.append(t(cx2[6], y, f"{s['cut_mm']:.0f}", 1.55))
        y += 3.8
    o.append(t(12, y + 1, "▣ = the section that carries the licensed-placeholder basting box (its stop 2, after the crosses).", 1.5, 400, RED)); y += 6
    o.append(t(12, y, "WHAT IS DIGITIZED", 2.0, 700)); y += 4.2
    for a, b_ in [("Density", "tatami 0.45, satin 0.42, padded moss 1 padding layer (> 3 mm wide), lattice underlay > 60 mm², 7 mm hidden travel."),
                  ("Light rays", "one continuous serpentine run per ray tone (no trims inside a ray), sewn first so every fill covers its travel."),
                  ("Trims", "hidden travel + underpath; objects ordered inside hidden areas; trims counted from the DST read-back."),
                  ("Threads / stops", "≤ 15 per file (fits a 15-needle head); repeated colours merged into the earliest safe stop."),
                  ("Placeholder", "basting box outline = first stop; nothing stitched inside; water stops 1 mm outside."),
                  ("Ties", "3-stitch tie-on/off at every trim + colour change; max stitch 7.5 mm.")]:
        o.append(t(12, y, a, 1.6, 700)); o.append(t(36, y, b_, 1.5)); y += 3.3
    det = Image.open(glob.glob("out/01_back-scene/B_M-XL/HAKI_FB_01_back-scene_B-M-XL_preview.png")[0])
    tag, dh = img_tag(det, 12, y + 2, 70); o.append(tag)
    o.append(t(86, y + 5, "DST read-back preview, 01 back grade B", 1.5, 400, MUTED))
    bk = back_png(); bx, by, bw = 184, 30, 101
    tag, bh = img_tag(bk, bx, by, bw); o.append(tag)
    s_ = bw / 610.0; X = lambda x: bx + (x + 305)*s_; Y = lambda y_: by + (y_ + 30)*s_
    sx, sy = SPL["sx"], SPL["sy"]; b = BB[0]
    if sx is not None: o.append(f'<line x1="{f(X(sx))}" y1="{f(Y(b[1]-12))}" x2="{f(X(sx))}" y2="{f(Y(b[3]+12))}" stroke="{RED}" stroke-width="0.35" stroke-dasharray="1.5 0.8"/>')
    if sy is not None: o.append(f'<line x1="{f(X(b[0]-12))}" y1="{f(Y(sy))}" x2="{f(X(b[2]+12))}" y2="{f(Y(sy))}" stroke="{RED}" stroke-width="0.35" stroke-dasharray="1.5 0.8"/>')
    seen = set()
    for nm, v in SPL["sections"].items():
        bb = v["bbox"]
        o.append(f'<rect x="{f(X(bb[0]))}" y="{f(Y(bb[1]))}" width="{f((bb[2]-bb[0])*s_)}" height="{f((bb[3]-bb[1])*s_)}" fill="none" stroke="#0A84FF" stroke-width="0.25"/>')
        cxm, cym = X((bb[0]+bb[2])/2), Y((bb[1]+bb[3])/2)
        o.append(f'<circle cx="{f(cxm)}" cy="{f(cym)}" r="3" fill="#0A84FF"/>' + t(cxm, cym + 1, nm[:2], 2.0, 700, "#FFFFFF", "middle"))
        for m in v["marks"]:
            if tuple(m) in seen: continue
            seen.add(tuple(m)); mx, my = X(m[0]), Y(m[1])
            o.append(f'<path d="M{f(mx-1.4)} {f(my)} H{f(mx+1.4)} M{f(mx)} {f(my-1.4)} V{f(my+1.4)}" stroke="#00A3FF" stroke-width="0.45"/>')
    o.append(t(bx, by + bh + 3.5, f"Size M splits. Red = split lines ({SPL['cut_mm']:.0f} mm of fill crosses them); blue = file extents; + = basting crosses.", 1.45, 400, MUTED))
    sy0 = by + bh + 9; o.append(t(bx, sy0, "SEWING THE SPLIT BACK (no border frame)", 2.0, 700))
    for i, st_ in enumerate(["1. Mark CB + both split lines on the cut back (chalk), from B01.",
                             "2. Hoop S1. Stop 1 = basting crosses. Sew S1.",
                             "3. Re-hoop for S2; align on the shared S1 crosses; sew its",
                             "    crosses over them (check), then S2. Same for S3, S4.",
                             "4. Fills crossing a split overlap 1.2 mm; motifs < 70 mm",
                             "    (leaf sprays, rocks) are never cut between hoopings.",
                             "5. Licensed figure: sewn by the factory after S1–S4, in",
                             "    the basting box; then remove basting + backing.",
                             "Every grade has its own S1–S4 (folder <grade>/splits)."]):
        o.append(t(bx, sy0 + 4 + i*3.1, st_, 1.5, 600 if "Licensed" in st_ else 400, RED if "Licensed" in st_ else INK))
    return o

def build():
    pages = {"G2": overview(), "G3": threads(), "G4": summary(), "G5": files_page()}
    el = [("01 Back scene", glob.glob("out/01_back-scene/*SPEC_*.pdf")[0]), ("02 Chest mossy branch", glob.glob("out/02_*/*SPEC_*.pdf")[0])]
    index = [("G1 Cover + contents", 1), ("G2 Placement overview", 2), ("G3 Thread + trim summary", 3), ("G4 Stitch summary + open questions", 4),
             ("G5 Production stitch files + hoop splits", 5)]
    pg = 6
    for name, path in el:
        n = len(PdfReader(path).pages); index.append((name + f" ({n} pp)", pg)); pg += n
    pages["G1"] = cover(index)
    w = PdfWriter()
    for k in ("G1", "G2", "G3", "G4", "G5"):
        svg = doc(pages[k]); cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"{k}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"prev_{k}.png", output_width=2400)
        w.append(PdfReader(f"{k}.pdf"))
    for name, path in el: w.append(PdfReader(path))
    w.write(OUT_PDF); print("embroidery pages", pg - 1)
    return index

if __name__ == "__main__":
    build()
