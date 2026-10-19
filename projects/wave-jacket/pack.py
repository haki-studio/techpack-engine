"""Embroidery pack G1-G6 + F1 for the wave jacket (01 wave on BK, FR, FL, SR, SL). Every number comes from the stitch files
(dst_current.json / dst_all.json, readback.dst)."""
import wavecore as WC
import os, json, pickle, glob
import cairosvg
from shapely.ops import unary_union
from pypdf import PdfWriter, PdfReader
from sheet import t, swatch, doc, INK, MUTED, RED, ORANGE, GUIDE, GREEN, SW, SH
from render import f
from motifs2 import HEX, PAL
import tech, stitchrender as SR
import specbase as SB
from specbase import img_tag
import pieces as PC, views as VW, emb_place as EP, factory as FA
PROF = FA.load(); FRAME = FA.largest_frame(PROF); FR_S = f"{FRAME[0]:.0f} × {FRAME[1]:.0f}"
def mh(r): return FA.machine_hours(r["stitches"], PROF, trims=r["trims"], colour_changes=r["stops"] - 1)
dst2 = WC.patch_dst2()

REV, DATE = WC.REV_EMB, WC.DATE
SB.FOOT = f"HAKI STUDIOS · {WC.NAME} · EMBROIDERY · {REV} · {DATE}"
D = pickle.load(open("art_M.pkl", "rb")); VF = {P: D[P] for P in WC.PIECES}
CUR = json.load(open("dst_current.json")); ALL = json.load(open("dst_all.json"))
SUM = json.load(open("out/01_wave/summary.json")) if os.path.exists("out/01_wave/summary.json") else {}
PS = WC.PIECES
BB = {p: unary_union([r["geom"] for r in VF[p]]).bounds for p in PS}
OUT_PDF = f"out/HAKI_WAVE_EMBROIDERY-PACK_{REV.replace(' ', '')}.pdf"
SPEC = glob.glob("out/01_wave/*SPEC_*.pdf")
def hdr(title, sub, page): return SB.header(title, sub, page)
def secs(r): return (r.get("splits") or {}).get("sections", {}) or {}
def hoop_files(r):
    """the files a piece is actually sewn from: its split sections, or the full file when it fits one hooping"""
    s = secs(r); return list(s.values()) if s else [r.get("full", r)]
TOT = sum(CUR[p]["stitches"] for p in PS); TRIMS = sum(CUR[p]["trims"] for p in PS)
MH = sum(mh(CUR[p]) for p in PS)
MH_HOOP = sum(mh(s) for p in PS for s in hoop_files(CUR[p]))
HOOPS = sum(CUR[p]["hoopings"] for p in PS)

def cover(index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>']
    o.append(t(14, 24, "HAKI STUDIOS", 3.0, 700, MUTED))
    o.append(t(14, 36, "Wave jacket · washed navy — embroidery", 7.0, 700))
    o.append(t(SW - 14, 30, "EMBROIDERY SAMPLING PACKAGE · size M strike-off", 2.8, 700, RED, "end"))
    o.append(t(SW - 14, 35, WC.GARMENT_NOTE.replace(" - ", " — "), 2.2, 600, ORANGE, "end"))
    o.append(t(14, 44, f"{REV} · {DATE} · Drum Island block, size M base · 1 element (01 wave), 5 pieces · 9 threads · all dimensions mm", 2.6, 400, MUTED))
    o.append(f'<line x1="14" y1="48" x2="{SW-14}" y2="48" stroke="{INK}" stroke-width="0.4"/>')
    bk, _, _ = VW.view_png("back", "M", 1.6); fr, _, _ = VW.view_png("front", "M", 1.6)
    tag, h = img_tag(bk, 14, 54, 88); o.append(tag); o.append(t(14, 54 + h + 3.5, "BACK", 2.2, 700))
    tag, h2 = img_tag(fr, 106, 54, 88); o.append(tag); o.append(t(106, 54 + h2 + 3.5, "FRONT (size M stitch preview on the flat lay)", 2.2, 700))
    ix = 202
    o.append(t(ix, 58, "CONTENTS", 2.8, 700)); y = 64
    for name, pg in index:
        o.append(t(ix, y, name, 2.0)); o.append(t(SW - 14, y, f"{pg}", 2.0, 600, MUTED, "end")); y += 4.2
    y += 4
    o.append(t(ix, y, "TOTALS, SIZE M (read from the DST files)", 2.4, 700)); y += 5
    for a, b in [("Stitches per jacket", f"{TOT:,}"), ("Trims per jacket", f"{TRIMS:,}"),
                 ("Hoopings per jacket", f"{HOOPS} on {FR_S} (G6)"),
                 ("Machine time / jacket", f"{MH_HOOP:.1f} h as hooped, one head"), ("Threads", f"9 (40wt polyester), ≤ {FA.max_threads(PROF)} per file")]:
        o.append(t(ix, y, a, 2.0, 400, MUTED)); o.append(t(SW - 14, y, b, 1.9, 600, INK, "end")); y += 4
    o.append(t(SW - 14, SH - 8, SB.FOOT, 1.9, 400, MUTED, "end"))
    return o

def overview():
    o = hdr("PLACEMENT OVERVIEW — the wave on the five pieces", "Each piece in its own pattern coords (back: x from CB, + = wearer's right, y from CB neck seam; fronts: x from CF, + = wearer's left, y from CF neck; sleeves: x from the sleeve centre line, y from the underarm line).", "G2")
    from PIL import Image, ImageDraw
    import pickle as pk
    SC = 0.128                                                         # one scale for every piece (mm on page per mm)
    lay = {"SL": (12, 30), "BK": (82, 30), "SR": (163, 30), "FR": (82, 116), "FL": (125, 116)}
    for P, (x, y) in lay.items():
        pan = PC.panel("M", P); b = pan.bounds; bb = (b[0] - 4, b[1] - 4, b[2] + 4, b[3] + 4); ppm = 1.4; w = (bb[2] - bb[0]) * SC
        im = SR.render(VF[P], bb, ppm, base=WC.FABRIC)
        msk = Image.new("L", im.size, 0); ImageDraw.Draw(msk).polygon([((xx - bb[0]) * ppm, (yy - bb[1]) * ppm) for xx, yy in pan.exterior.coords], fill=255)
        wh = Image.new("RGB", im.size, (255, 255, 255)); wh.paste(im, (0, 0), msk)
        dd = ImageDraw.Draw(wh); dd.line([((xx - bb[0]) * ppm, (yy - bb[1]) * ppm) for xx, yy in PC.clip_for("M", P).exterior.coords], fill=(255, 90, 90), width=1)
        tag, hh = img_tag(wh, x, y, w); o.append(tag)
        s = w / (bb[2] - bb[0]); X = lambda xx: x + (xx - bb[0]) * s; Y = lambda yy: y + (yy - bb[1]) * s
        ab = BB[P]
        o.append(f'<rect x="{f(X(ab[0]))}" y="{f(Y(ab[1]))}" width="{f((ab[2]-ab[0])*s)}" height="{f((ab[3]-ab[1])*s)}" fill="none" stroke="{GUIDE}" stroke-width="0.3" stroke-dasharray="1.2 0.8"/>')
        sp = CUR[P].get("splits") or {}
        for yv in sp.get("ys") or ([sp["sy"]] if sp.get("sy") is not None else []):
            o.append(f'<line x1="{f(X(ab[0]-6))}" y1="{f(Y(yv))}" x2="{f(X(ab[2]+6))}" y2="{f(Y(yv))}" stroke="#0A84FF" stroke-width="0.4" stroke-dasharray="2 1"/>')
        for xv in sp.get("xs") or ([sp["sx"]] if sp.get("sx") is not None else []):
            o.append(f'<line x1="{f(X(xv))}" y1="{f(Y(ab[1]-6))}" x2="{f(X(xv))}" y2="{f(Y(ab[3]+6))}" stroke="#0A84FF" stroke-width="0.4" stroke-dasharray="2 1"/>')
        o.append(t(x, y + hh + 3, f"{P} {PC.NAME[P]} ({PC.CODE[P]}) · art {ab[2]-ab[0]:.0f} × {ab[3]-ab[1]:.0f}", 1.6, 700))
    o.append(t(12, 199, f"Red line = keep-out boundary (art may not cross it). Blue dashed box = art box, blue dashed lines = hoop split lines (G6). Size M, all pieces at {SC:.3f}:1.", 1.6, 400, MUTED))
    tx = 232; ty = 30
    o.append(t(tx, ty, "ART BOX (w × h mm, DST read-back)", 2.0, 700))
    for j, P in enumerate(PS): o.append(t(tx + 9 + j * 10.5, ty + 5, P, 1.5, 700, MUTED))
    o.append(t(tx, ty + 5, "Size", 1.5, 700, MUTED))
    for i, sz in enumerate(WC.DOC_SIZES):
        y = ty + 9.5 + i * 3.8
        if i % 2 == 0: o.append(f'<rect x="{tx-1}" y="{f(y-2.7)}" width="{SW - tx - 11}" height="3.8" fill="#F5F2EC"/>')
        o.append(t(tx, y, sz, 1.5, 700))
        for j, P in enumerate(PS):
            r = ALL.get(sz, {}).get(P)
            if r: o.append(t(tx + 9 + j * 10.5, y, f"{r['full']['art_box'][2]-r['full']['art_box'][0]:.0f}×{r['full']['art_box'][3]-r['full']['art_box'][1]:.0f}", 1.3))
    o.append(t(tx, ty + 9.5 + len(WC.DOC_SIZES) * 3.8, "Other sizes: after the size-M strike-off.", 1.45, 400, MUTED))
    ky = ty + 9.5 + len(WC.DOC_SIZES) * 3.8 + 7
    o.append(t(tx, ky, "KEEP-OUTS (mm from the sew line)", 2.0, 700))
    for i, k in enumerate(["CF zip 15 each side", "side / shoulder / armhole 15", "sleeve cap + underarm 15", "hem-rib seam 10 · cuff 10",
                           "welt box 6 · collar flat 6 · neck 6", "rib + collar never embroidered", "", "Grade: A 92 % XS–S, B 100 %", "M–XL, C 108 % XXL–3XL: the",
                           "render map is scaled about the", "neck point; art re-clipped to", "each size's own keep-outs;", "one file per size per piece."]):
        o.append(t(tx, ky + 4.2 + i * 3.2, k, 1.55))
    return o

def threads():
    o = hdr("THREAD + TRIM SUMMARY", "One palette for the whole jacket — 9 threads. Approve a physical thread board (Isacord or Madeira Polyneon) before sampling; hex = on-screen target read off the render.", "G3")
    use = {k: {} for k in WC.WV_KEYS}
    for p in PS:
        for c in CUR[p]["colours"]:
            if c in use: use[c][p] = use[c].get(p, 0) + 1
    hd = ["", "Thread", "Hex", "Isacord", "ΔE", "Madeira Polyneon", "ΔE", "Wt", "Used for", "Stops BK/FR/FL/SR/SL"]
    cx = [12, 18, 44, 58, 88, 96, 130, 138, 146, 246]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.75, 700, MUTED))
    TH = SB.TH; rh = 5.2
    for i, k in enumerate(WC.WV_KEYS):
        y = 36 + i * rh
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3.3)}" width="{SW-22}" height="{f(rh)}" fill="#F5F2EC"/>')
        iso, pn = TH[k]["isacord"], TH[k]["polyneon"]
        ci = GREEN if iso[3] < 3 else (ORANGE if iso[3] < 5.5 else RED); cp = GREEN if pn[3] < 3 else (ORANGE if pn[3] < 5.5 else RED)
        o.append(swatch(cx[0], y, k, 4.5, 2.8)); o.append(t(cx[1], y, PAL[k][1], 1.9, 600)); o.append(t(cx[2], y, HEX[k], 1.75, 400, MUTED))
        o.append(t(cx[3], y, f"{iso[0]} {iso[1]}"[:22], 1.75)); o.append(t(cx[4], y, f"{iso[3]:.1f}", 1.7, 600, ci))
        o.append(t(cx[5], y, f"{pn[0]} {pn[1]}"[:24], 1.75)); o.append(t(cx[6], y, f"{pn[3]:.1f}", 1.7, 600, cp))
        o.append(t(cx[7], y, "40", 1.75)); o.append(t(cx[8], y, PAL[k][2][:66], 1.6, 400, MUTED))
        o.append(t(cx[9], y, " / ".join(str(use[k].get(p, 0)) for p in PS), 1.7, 600))
    yb = 36 + len(WC.WV_KEYS) * rh + 3
    o.append(t(12, yb, "ΔE2000 vs target: green < 3, amber 3–5.5, red > 5.5 — amber/red rows must be picked from the physical card (F1). All targets PROPOSED (read from the low-res render).", 1.8, 600, ORANGE))
    o.append(t(12, yb + 7, "TRIMS + CONSUMABLES (per jacket)", 2.2, 700))
    tr = [("Backing", "2.5 oz cutaway, navy/charcoal, cut 30 larger than each hooping; trim to 5 from stitching after embroidery (5 pieces)"),
          ("Topping", "none (canvas surface is firm); optional water-soluble topping on the foam if the loops sink — strike-off decides"),
          ("Needles", "75/11 sharp (canvas)"), ("Bobbin", "60wt navy polyester pre-wound (dark shell)"),
          ("Frames", f"{FR_S} (factory.json{'' if PROF['frames_confirmed'] else ', PROPOSED'}): {HOOPS} hoopings per jacket at M (G6); a frame ≥ {max(BB[p][2]-BB[p][0] for p in PS)+30:.0f} × {max(BB[p][3]-BB[p][1] for p in PS)+30:.0f} sews every piece in one"),
          ("Patches / labels", "none on this garment — all artwork is direct embroidery")]
    for i, (a, b) in enumerate(tr):
        o.append(t(12, yb + 11.5 + i * 3.6, a, 1.85, 600)); o.append(t(42, yb + 11.5 + i * 3.6, b, 1.85))
    return o

def summary():
    o = hdr("STITCH SUMMARY + OPEN QUESTIONS", "Size M files. Every count read back from the DST (stitches, trims, stops, max stitch); threads from the PES.", "G4")
    hd = ["Element", "Piece", "Art box", "Stitches", "Trims", "Trims/10k", "Stops", "Threads", "Max stitch", "Hoops", "Run time (as hooped)"]
    cx = [12, 36, 76, 98, 116, 130, 146, 158, 172, 190, 204]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.75, 700, MUTED))
    for i, p in enumerate(PS):
        r = CUR[p]; b = BB[p]; y = 36 + i * 4.6
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3)}" width="{SW-22}" height="4.6" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, "01 Wave", 1.85, 600)); o.append(t(cx[1], y, f"{p} {PC.NAME[p]}", 1.75))
        o.append(t(cx[2], y, f"{b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}", 1.8)); o.append(t(cx[3], y, f"{r['stitches']:,}", 1.8, 600))
        o.append(t(cx[4], y, f"{r['trims']:,}", 1.8)); o.append(t(cx[5], y, f"{r['trims']/r['stitches']*1e4:.0f}", 1.8)); o.append(t(cx[6], y, f"{r['stops']}", 1.8))
        o.append(t(cx[7], y, f"{len(set(r['colours']))}", 1.8)); o.append(t(cx[8], y, f"{r['max_stitch']:.2f} mm", 1.8))
        o.append(t(cx[9], y, f"{r['hoopings']}", 1.8)); o.append(t(cx[10], y, f"{sum(mh(s) for s in hoop_files(r))*60:.0f} min", 1.8))
    y = 36 + len(PS) * 4.6 + 1
    o.append(t(cx[2], y, "TOTAL", 1.9, 700)); o.append(t(cx[3], y, f"{TOT:,}", 1.9, 700)); o.append(t(cx[4], y, f"{TRIMS:,}", 1.9, 700)); o.append(t(cx[9], y, f"{HOOPS}", 1.9, 700)); o.append(t(cx[10], y, f"{MH_HOOP:.1f} h", 1.9, 700))
    o.append(t(12, y + 4.5, f"Run time = factory.machine_hours: {PROF['spm']} spm + 6 s per trim + 4 s per colour change, one head, summed over the files a piece is hooped in (split sections incl. registration).", 1.65, 400, MUTED))
    o.append(t(12, y + 7.8, "Fidelity first (LESSONS A11): every crest, curl and drop of the render is sewn — trims (most are spray drops + curl lines on bare fabric) and run time are reported, cleaned up after the strike-off.", 1.65, 400, MUTED))
    qy = y + 15
    o.append(t(12, qy, "OPEN QUESTIONS — confirm before sampling", 2.6, 700))
    qs = [f"1. Frame: pieces > {FRAME[0]-16:.0f} mm are split for {FR_S} (G6). A larger frame (jacket-back frame) removes the joins — which frames do you have?",
          "2. Foam curls: the render shows raised looped (chenille-look) foam. Rev A = padded tatami + loop spiral + curl lines on any head. Chenille/moss heads available?",
          "3. Thread board: 9 targets read from a low-res AI render — approve physical colours (G3), especially the 6 blues against the navy shell.",
          "4. Sleeves: the render's sleeves are long + narrow; the wave is placed from the sleeve fold/shoulder (each half stretched to meet the fold), 15 mm short of the armhole. OK?",
          "5. Garment: the jacket body is under revision — placement is on the Drum Island block M; re-check keep-outs when the new body lands.",
          "6. Grading (after the sample): A 92 % (XS–S) · B 100 % (M–XL) · C 108 % (XXL–3XL), one file per size per piece, re-clipped to each size's keep-outs. OK?",
          "7. Shell dye: piece-dyed + pre-washed navy duck assumed. If garment-washed after embroidery, wash-test the sew-out (cream foam!).",
          "8. Reference: traced from the low-res render (~1.4 mm/px) + the founder's shoulder close-up (registered, FL crest). Flat close-ups of the other panels would sharpen the rest.",
          "9. DST/PES are production-intent drafts: the factory digitizer checks density + pull on 12 oz duck and edits before the sew-out."]
    for i, q in enumerate(qs): o.append(t(12, qy + 5 + i * 3.7, q, 1.8))
    return o

def files_page():
    o = hdr("PRODUCTION STITCH FILES + HOOP SPLITS", "DST (Tajima) + PES, one set per piece, size M (strike-off). Counts read back from the DST. Origin = centre of each file's design ((+) on the pattern, DXF layer 13).", "G5")
    hd = ["Size", "Art", "Piece", "Full file mm", "Stitches", "Trims", "Stops", "Hoopings: section stitches / trims", "Fits frame"]
    cx = [12, 22, 30, 40, 62, 80, 92, 104, 192]
    for x_, h in zip(cx, hd): o.append(t(x_, 31, h, 1.55, 700, MUTED))
    y = 35; allfit = True
    for i, sz in enumerate(WC.DOC_SIZES):
        for p in PS:
            r = ALL.get(sz, {}).get(p)
            if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.1)}" width="196" height="2.9" fill="#F5F2EC"/>')
            o.append(t(cx[0], y, sz if p == "BK" else "", 1.4, 700)); o.append(t(cx[1], y, WC.GRADE[sz][0] if p == "BK" else "", 1.4, 700, RED)); o.append(t(cx[2], y, p, 1.4, 600))
            if r and "full" in r:
                fu = r["full"]
                o.append(t(cx[3], y, f"{fu['size_mm'][0]:.0f} × {fu['size_mm'][1]:.0f}", 1.35)); o.append(t(cx[4], y, f"{fu['stitches']:,}", 1.35)); o.append(t(cx[5], y, f"{fu['trims']}", 1.35)); o.append(t(cx[6], y, f"{fu['stops']}", 1.35))
                ss = secs(r)
                txt = "  ".join(f"{nm.split('_')[0]} {s_['stitches']//1000}k/{s_['trims']}" for nm, s_ in ss.items()) if ss else "1 hooping (full file)"
                o.append(t(cx[7], y, txt, 1.3))
                fits = all(v["fits"] for v in ss.values()) if ss else (fu["size_mm"][0] <= FRAME[0] - 16 and fu["size_mm"][1] <= FRAME[1] - 16)
                allfit &= fits; o.append(t(cx[8], y, "yes" if fits else "CHECK", 1.35, 700, GREEN if fits else RED))
            else:
                o.append(t(cx[3], y, "pending", 1.35, 400, MUTED)); allfit = False
            y += 2.9
    o.append(t(12, y + 2, f"All files fit the {FR_S} frame (incl. registration crosses): {'yes' if allfit else 'CHECK'}", 1.7, 700, GREEN if allfit else RED))
    o.append(t(12, y + 6, "Sampling package: size M only. XS-S (grade A 92 %), L-XL (B) and XXL-3XL (C 108 %) are rebuilt from the same art after the strike-off,", 1.6, 400, MUTED))
    o.append(t(12, y + 9, "with any density / pull changes it asks for. The frame is read from factory.json: a bigger frame re-splits every file in one rebuild.", 1.6, 400, MUTED))
    bx = 212; y2 = 31
    o.append(t(bx, y2, "WHAT IS DIGITIZED", 2.0, 700)); y2 += 4.2
    notes = [("Stripes", ["6 blues, one region per traced tone stripe:", "tatami along the stripe (6 mm sections);", "turning satin only < 3 wide w/o holes; after", "the cream rope lines (lines first, B2)."]),
             ("Foam", ["curl details (grey hollow, shade, blue", "claw) first, then the raised foam: padded", "tatami per curl, then curl lines + a", "scalloped loop spiral in Foam shade."]),
             ("Drops", ["blue underside then white satin per drop;", "every drop is its own island (1 trim)."]),
             ("Ties", ["3-stitch tie-on/off at every trim + colour", "change; max sewn stitch ≤ 7.5 mm;", f"≤ {FA.max_threads(PROF)} colours per file incl. registration."])]
    for a, ls in notes:
        o.append(t(bx, y2, a, 1.7, 700)); y2 += 3.2
        for l_ in ls: o.append(t(bx, y2, l_, 1.55)); y2 += 2.9
        y2 += 1.2
    y2 += 2
    o.append(t(bx, y2, "SEWING A SPLIT PIECE", 2.0, 700)); y2 += 4
    for st_ in ["1. Mark CF / CB, split lines + needle starts", "    on the cut piece (DXF layer 13, chalk).",
                "2. Hoop S1. Stop 1 opens with the registration", "    crosses (stop-1 thread). Sew S1.",
                "3. Re-hoop for the next section; align on the", "    shared crosses, sew them (check), then it.",
                "4. Fills crossing a split overlap 1.2; curls +", "    drops < 70 go whole to one file.",
                "5. Pick out the crosses; trim the backing."]:
        o.append(t(bx, y2, st_, 1.55)); y2 += 2.9
    return o

def hooping_page():
    o = hdr("HOOPING TABLE — split lines + needle starts per file (size M strike-off)",
            f"Frame {FR_S} mm (factory.json{'' if PROF['frames_confirmed'] else ', PROPOSED'}). Coordinates in mm on each piece's pattern (see G2). DXF layer 13 = these points.", "G6")
    hd = ["Size", "Piece", "Hoops", "Split x / y", "Needle start per file (x, y) · file mm", "Fit", "Machine time"]
    cx = [12, 22, 32, 42, 64, 250, 262]
    for x_, h in zip(cx, hd): o.append(t(x_, 31, h, 1.55, 700, MUTED))
    y = 35.5
    for i, sz in enumerate(WC.DOC_SIZES):
        for P in PS:
            r = ALL.get(sz, {}).get(P)
            if not r: continue
            if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.1)}" width="{SW-22}" height="2.85" fill="#F5F2EC"/>')
            sp = r.get("splits") or {}; ss = secs(r)
            o.append(t(cx[0], y, sz if P == "BK" else "", 1.4, 700)); o.append(t(cx[1], y, P, 1.4, 600)); o.append(t(cx[2], y, f"{r['hoopings']}", 1.4))
            xs_ = sp.get("xs") or ([sp["sx"]] if sp.get("sx") is not None else []); ys_ = sp.get("ys") or ([sp["sy"]] if sp.get("sy") is not None else [])
            sxy = (",".join(f"{v:.0f}" for v in xs_) or "—") + " / " + (",".join(f"{v:.0f}" for v in ys_) or "—") if ss else "—"
            o.append(t(cx[3], y, sxy, 1.4, 700, RED if ss else MUTED))
            if ss:
                txt = "  ".join(f"{nm.split('_')[0]} ({s_['origin'][0]:+.0f}, {s_['origin'][1]:.0f}) {s_['size_mm'][0]:.0f}×{s_['size_mm'][1]:.0f}" for nm, s_ in ss.items())
                ok = all(v["fits"] for v in ss.values())
            else:
                fo = r["full"]["origin"]; txt = f"full ({fo[0]:+.0f}, {fo[1]:.0f}) {r['full']['size_mm'][0]:.0f}×{r['full']['size_mm'][1]:.0f}"; ok = True
            o.append(t(cx[4], y, txt, 1.3)); o.append(t(cx[5], y, "yes" if ok else "NO", 1.4, 700, GREEN if ok else RED))
            o.append(t(cx[6], y, f"{sum(mh(s) for s in hoop_files(r))*60:.0f} min", 1.35))
            y += 2.85
    y += 2
    for i, l in enumerate(["Split lines are chosen where they cut the least art inside the frame; curls/drops under 70 mm go whole to one file, larger fills overlap 1.2 mm across the line.",
                           "Needle start = centre of each file's design (origin of the DST/PES). Registration crosses sew at the start of stop 1 in that stop's thread (factory: max 12 colours per file,",
                           "no separate basting colour); the next hooping re-registers on the crosses on its split line; pick them out after the last hooping. Machine time incl. trims + colour changes."]):
        o.append(t(12, y + i * 3.2, l, 1.55, 400, MUTED))
    return o

def f1_pages():
    import sheet as _SH; _SH.FOOT = SB.FOOT
    so = []
    for p in PS:
        r = CUR[p]
        for s in hoop_files(r):
            nm = os.path.basename(s["file"]); so.append(dict(file=nm + ".dst", piece=f"{p} {PC.NAME[p]}" + ("" if s is r else " · " + nm.split("_M_")[-1]), stitches=s["stitches"], trims=s["trims"]))
    th = [dict(name=PAL[k][1], code=f"Isacord {SB.TH[k]['isacord'][0]} / Polyneon {SB.TH[k]['polyneon'][0]}", de=min(SB.TH[k]["isacord"][3], SB.TH[k]["polyneon"][3])) for k in WC.WV_KEYS]
    pcs = [dict(piece=f"01 {p} {PC.NAME[p]}", w=CUR[p]["size_mm"][0], h=CUR[p]["size_mm"][1], hoopings=CUR[p]["hoopings"]) for p in PS]
    pages = FA.requests_page(WC.NAME, so, th, pcs, page="F1", prof=PROF)
    # chenille question appended to F1 (quote basis area is the last line)
    lines = ["5  Chenille / loop embroidery", "The foam curls in the render look like chenille (raised loops).",
             "Rev A sews them as padded tatami + a loop-texture spiral on any",
             "multi-needle head. Do you have chenille / moss-stitch heads?",
             "If yes, the same foam outlines (region FM in the ART.svg) can",
             "be sewn as real loops — please quote both ways."]
    extra = "".join(f'<text x="168" y="{40 + i*4.2:.1f}" font-family="{_SH.FONT}" font-size="{2.6 if i == 0 else 2.3}" font-weight="{700 if i == 0 else 400}" fill="{ORANGE}">{l}</text>' for i, l in enumerate(lines))
    return [pg.replace("</svg>", extra + "</svg>") for pg in pages]

def build():
    pages = {"G1": None, "G2": overview(), "G3": threads(), "G4": summary(), "G5": files_page(), "G6": hooping_page()}
    el = [("01 Wave (element spec)", SPEC[0])]
    index = [("G1 Cover + contents", 1), ("G2 Placement overview", 2), ("G3 Thread + trim summary", 3), ("G4 Stitch summary + open questions", 4),
             ("G5 Production stitch files + hoop splits", 5), ("G6 Hooping table (split lines, needle starts)", 6)]
    pg = 7
    for name, path in el:
        n = len(PdfReader(path).pages); index.append((name + f" ({n} pp)", pg)); pg += n
    index.append(("F1 Factory requests", pg))
    pages["G1"] = cover(index)
    w = PdfWriter()
    for k in ("G1", "G2", "G3", "G4", "G5", "G6"):
        svg = doc(pages[k]); cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"{k}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"prev_{k}.png", output_width=2400)
        w.append(PdfReader(f"{k}.pdf"))
    for name, path in el: w.append(PdfReader(path))
    for i, svg in enumerate(f1_pages()):
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"F{i+1}.pdf"); cairosvg.svg2png(bytestring=svg.encode(), write_to=f"prev_F{i+1}.png", output_width=2400)
        w.append(PdfReader(f"F{i+1}.pdf"))
    w.write(OUT_PDF)
    print("pages", pg)

if __name__ == "__main__":
    build()
