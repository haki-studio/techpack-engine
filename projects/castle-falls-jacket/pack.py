"""Embroidery pack G1-G6 + element specs + F1 for the Castle Falls jacket. Every number comes from the stitch files
(dst_current.json / dst_all.json, re-read by make_current.py)."""
import cfcore
import os, json, pickle, glob
import cairosvg
from PIL import Image
from shapely.ops import unary_union
from pypdf import PdfWriter, PdfReader
from sheet import t, swatch, doc, INK, MUTED, RED, ORANGE, GUIDE, GREEN, SW, SH
from render import f
from motifs2 import HEX, PAL
import tech
import specbase as SB
from specbase import img_tag
import factory as FA, views as VW, keepout as KO, emb_place as EP
PROF = FA.load(); FRAME = FA.largest_frame(PROF); FR_S = f"{FRAME[0]:.0f} × {FRAME[1]:.0f}"
def mh(r): return FA.machine_hours(r["stitches"], PROF, trims=r["trims"], colour_changes=r["stops"] - 1)

REV, DATE = cfcore.REV_EMB, cfcore.DATE
SB.FOOT = f"HAKI STUDIOS · {cfcore.NAME} · EMBROIDERY · {REV} · {DATE}"
ART = pickle.load(open("art_M.pkl", "rb"))
CUR = json.load(open("dst_current.json")); ALL = json.load(open("dst_all.json"))
PLAN = json.load(open("merge_plan.json"))
PC = cfcore.PIECES
OUT_PDF = f"out/HAKI_{cfcore.SHORT}_EMBROIDERY-PACK_{REV.replace(' ', '')}.pdf"
SPECS = {e: glob.glob(f"out/{e}_{cfcore.ELEMS[e][0]}/*SPEC_*.pdf")[0] for e in cfcore.ELEMS}
def hdr(title, sub, page): return SB.header(title, sub, page)
TOT = sum(CUR[p]["stitches"] for p in PC); TRIMS = sum(CUR[p]["trims"] for p in PC)
MH_FULL = sum(mh(CUR[p]) for p in PC)
MH_SPLIT = sum(mh(s) for p in PC for s in CUR[p]["splits"]["sections"].values())
HOOP = sum(len(CUR[p]["splits"]["sections"]) for p in PC)
_V = {}
def views():
    if not _V:
        _V["front"] = VW.front_view(ART, 2.0)[0]; _V["back"] = VW.back_view(ART, 2.0)[0]
    return _V["front"], _V["back"]

def cover(index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>']
    o.append(t(14, 24, "HAKI STUDIOS", 3.0, 700, MUTED))
    o.append(t(14, 36, "Castle Falls jacket · washed navy — embroidery", 7.0, 700))
    o.append(t(14, 44, f"{REV} · {DATE} · Drum Island block, size M base · 3 elements on 5 pieces · {cfcore.board_text()}, ≤ 12 per file · all dimensions mm", 2.6, 400, MUTED))
    o.append(f'<line x1="14" y1="48" x2="{SW-14}" y2="48" stroke="{INK}" stroke-width="0.4"/>')
    fv, bv = views()
    tag, h = img_tag(fv, 14, 54, 90); o.append(tag); tag, h2 = img_tag(bv, 106, 54, 90); o.append(tag)
    o.append(t(14, 54 + h + 3.5, "FRONT + BACK, size M stitch render on the technical flat.", 2.0, 700))
    ix = 202
    o.append(t(ix, 58, "CONTENTS", 2.8, 700)); y = 64
    for name, pg in index:
        o.append(t(ix, y, name, 1.95)); o.append(t(SW - 14, y, f"{pg}", 1.95, 600, MUTED, "end")); y += 4.0
    y += 3
    o.append(t(ix, y, "TOTALS PER JACKET, SIZE M (read from the DST files)", 2.2, 700)); y += 5
    for a, b in [("Stitches", f"{TOT:,}"), ("Trims", f"{TRIMS:,}"), ("Hoopings", f"{HOOP} on {FR_S} (split files)"),
                 ("Machine time / jacket", f"{MH_SPLIT:.1f} h one head (split files)"), ("Threads", f"{len(cfcore.sewn_threads())} sewn (board), ≤ 12 per file")]:
        o.append(t(ix, y, a, 1.9, 400, MUTED)); o.append(t(SW - 14, y, b, 1.9, 600, INK, "end")); y += 3.9
    o.append(t(ix, y + 2, "Fidelity first (Rev B): cost is reported, not limited —", 1.75, 600, ORANGE))
    o.append(t(ix, y + 5.3, "clean-up after the strike-off (F1).", 1.75, 600, ORANGE))
    o.append(t(SW - 14, SH - 8, SB.FOOT, 1.9, 400, MUTED, "end"))
    return o

def overview():
    o = hdr("PLACEMENT OVERVIEW — five embroidered pieces", "Each piece is embroidered flat on its cut pattern piece. Coordinates per piece on T13 / DXF layer 8. Tolerance ±2, rotation ±2° (art meets across the zip and the armholes).", "G2")
    fv, bv = views()
    tag, h = img_tag(fv, 12, 30, 92); o.append(tag); tag, h2 = img_tag(bv, 106, 30, 92); o.append(tag)
    o.append(t(12, 30 + h + 3.5, "FRONT: FR + FL fronts, front halves of SR (viewer's left) + SL.", 1.7, 600))
    o.append(t(106, 30 + h + 3.5, "BACK: BK, back halves of SL (viewer's left) + SR.", 1.7, 600))
    tx = 202; ty = 30
    o.append(t(tx, ty, "ART BOX PER SIZE (w × h mm)", 2.2, 700))
    hd = ["Size", "Art"] + PC; cx = [tx, tx + 8, tx + 13, tx + 27, tx + 41, tx + 55, tx + 69]
    for x_, hh in zip(cx, hd): o.append(t(x_, ty + 5, hh, 1.6, 700, MUTED))
    for i, sz in enumerate(cfcore.SIZES):
        y = ty + 9.5 + i * 4.0
        if i % 2 == 0: o.append(f'<rect x="{tx-1}" y="{f(y-2.8)}" width="{SW - tx - 11}" height="4" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, sz, 1.65, 700)); o.append(t(cx[1], y, cfcore.GRADE[sz][0], 1.65, 700, RED))
        for j, P in enumerate(PC):
            r = ALL.get(sz, {}).get(P)
            o.append(t(cx[2 + j], y, f"{r['full']['size_mm'][0]:.0f}×{r['full']['size_mm'][1]:.0f}" if r else "—", 1.4))
    ky = ty + 9.5 + 7 * 4.0 + 5
    o.append(t(tx, ky, "KEEP-OUTS (mm from the sew line, all sizes, T13)", 2.0, 700))
    for i, k in enumerate(["CF / zip 15 · side seams 15 · shoulders 15", "Hem-rib seam 10 · welt box 6 · collar lying flat 6",
                           "  (back: collar falls 70 below the back neck)", "Armholes / sleeve caps: WRAP seam 3 each side,",
                           "  armhole sewn without topstitch (LESSONS A4)", "Sleeve underarm seams 15 · cuff seam 10",
                           "Rib, collar, zip: never embroidered."]):
        o.append(t(tx, ky + 4.2 + i * 3.3, k, 1.65))
    my = ky + 4.2 + 7 * 3.3 + 4
    o.append(t(tx, my, "MATCHING ACROSS SEAMS", 2.0, 700))
    for i, l in enumerate(["Zip: FR + FL are traced from the same mockup columns;", "  the bridge, sky + clouds meet across the 30 mm zip gap.",
                           "Armholes: body + sleeve art is traced from the same", "  mockup pixels each side of the seam; art reaches the",
                           "  3 mm wrap line on both pieces (no limb crossings).",
                           "Graded A/B/C per size: body about CB/CF + hem, sleeves", "  about the cuff-seam centre (T5)."]):
        o.append(t(tx, my + 4.2 + i * 3.2, l, 1.6))
    return o

def threads():
    o = hdr("THREAD + TRIM SUMMARY", f"{len(cfcore.CF_KEYS)} tones traced from the mockup; {len(cfcore.sewn_threads())} threads are sewn (read back from all 35 files) — the board to buy; every stitch file uses ≤ 12 of them (factory limit). Approve a physical thread board (Isacord or Madeira Polyneon) before sampling; hex = on-screen target.", "G3")
    use = {k: {} for k in cfcore.CF_KEYS}
    for p in PC:
        for c in CUR[p]["colours"]: use[c][p] = use[c].get(p, 0) + 1
    hd = ["", "Thread", "Hex", "Isacord", "ΔE", "Madeira Polyneon", "ΔE", "Used for", "Stops"]
    cx = [12, 18, 42, 56, 84, 92, 124, 132, 222]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.7, 700, MUTED))
    for j, p in enumerate(PC): o.append(t(cx[8] + 11 + j * 6.5, 31, p, 1.7, 700, MUTED, "middle"))
    SEWN = set(cfcore.sewn_threads())
    TH = SB.TH; rh = 7.4 if False else 6.9
    BUY = cfcore.sewn_threads(); rh = min(7.2, 128 / len(BUY))
    for i, k in enumerate(BUY):
        y = 35.5 + i * rh
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3.0)}" width="{SW-22}" height="{f(rh)}" fill="#F5F2EC"/>')
        iso, pn = TH[k]["isacord"], TH[k]["polyneon"]
        ci = GREEN if iso[3] < 3 else (ORANGE if iso[3] < 5.5 else RED); cp = GREEN if pn[3] < 3 else (ORANGE if pn[3] < 5.5 else RED)
        o.append(swatch(cx[0], y, k, 4.5, 2.8)); o.append(t(cx[1], y, PAL[k][1], 1.8, 600)); o.append(t(cx[2], y, HEX[k], 1.65, 400, MUTED))
        o.append(t(cx[3], y, f"{iso[0]} {iso[1]}"[:22], 1.65)); o.append(t(cx[4], y, f"{iso[3]:.1f}", 1.6, 600, ci))
        o.append(t(cx[5], y, f"{pn[0]} {pn[1]}"[:24], 1.65)); o.append(t(cx[6], y, f"{pn[3]:.1f}", 1.6, 600, cp))
        o.append(t(cx[7], y, PAL[k][2][:62] if k in SEWN else "NOT SEWN in any file — merged into a neighbouring thread (no need to buy)", 1.6, 400 if k in SEWN else 600, MUTED if k in SEWN else ORANGE))
        for j, p in enumerate(PC):
            n = use[k].get(p, 0); m = PLAN[p].get(k)
            o.append(t(cx[8] + 11 + j * 6.5, y, str(n) if n else ("→" if m else "·"), 1.6, 600 if n else 400, INK if n else MUTED, "middle"))
    yb = 35.5 + len(BUY) * rh + 2
    o.append(t(12, yb, ("Not sewn in any file (merged into a neighbour, do NOT buy): " + ", ".join(PAL[k][1] for k in cfcore.CF_KEYS if k not in BUY) + ".  " if len(BUY) < len(cfcore.CF_KEYS) else "") + "ΔE2000 vs target: green < 3, amber 3–5.5, red > 5.5 — amber / red rows must be picked from the physical card. All targets are PROPOSED (read from the mockup).  '→' = this tone is sewn in a neighbouring thread on that piece (G5, spec p4).", 1.6, 600, ORANGE))
    mg = [f"{p}: " + ", ".join(f"{PAL[a][1]}→{PAL[b][1]}" for a, b in PLAN[p].items()) for p in PC]
    o.append(t(12, yb + 3.6, "Per-piece merges (≤ 12 colours): " + "  |  ".join(mg[:3]), 1.4, 400, MUTED)); o.append(t(12, yb + 6.0, "  |  ".join(mg[3:]) + "   ·  '·' = tone not in that piece's art.", 1.4, 400, MUTED))
    o.append(t(12, yb + 9.5, "TRIMS + CONSUMABLES", 2.0, 700))
    tr = [("Backing", "2.5 oz cutaway, black/charcoal (navy shell), 30 larger than each hooping; trim to 5 from stitching. Very dense art: test a second layer on the strike-off."),
          ("Needles / bobbin", "75/11 sharp (canvas) · 60wt navy polyester pre-wound bobbin"),
          ("Frames", f"{FR_S} (factory.json{'' if PROF['frames_confirmed'] else ', PROPOSED'}): back 4, each front 2, each sleeve 4 hoopings (split files, G5/G6)"),
          ("Patches / labels", "none — all artwork is direct embroidery")]
    for i, (a, b) in enumerate(tr):
        o.append(t(12, yb + 14 + i * 3.4, a, 1.75, 600)); o.append(t(40, yb + 14 + i * 3.4, b, 1.7))
    return o

def summary():
    o = hdr("STITCH SUMMARY + OPEN QUESTIONS", "Size M files. Every count read back from the DST. Run time = factory.machine_hours (factory.json speed + 6 s per trim + 4 s per colour change).", "G4")
    hd = ["Element", "Piece", "Art box", "Stitches", "Trims", "Trims/10k", "Stops", "Colours", "Max stitch", "Full file h", "Split files h", "Hoopings"]
    cx = [12, 44, 92, 110, 128, 142, 160, 172, 186, 204, 222, 242]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.7, 700, MUTED))
    for i, p in enumerate(PC):
        r = CUR[p]; y = 36 + i * 4.6; secs = r["splits"]["sections"].values()
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3)}" width="{SW-22}" height="4.6" fill="#F5F2EC"/>')
        e = cfcore.PIECE_ELEM[p]
        o.append(t(cx[0], y, f"{e} {cfcore.ELEMS[e][0].replace('-', ' ')}", 1.75, 600)); o.append(t(cx[1], y, f"{p} {cfcore.PIECE_NAME[p]}", 1.65))
        o.append(t(cx[2], y, f"{r['size_mm'][0]:.0f} × {r['size_mm'][1]:.0f}", 1.7)); o.append(t(cx[3], y, f"{r['stitches']:,}", 1.7, 600))
        o.append(t(cx[4], y, f"{r['trims']:,}", 1.7)); o.append(t(cx[5], y, f"{10000*r['trims']/r['stitches']:.0f}", 1.7))
        o.append(t(cx[6], y, f"{r['stops']}", 1.7)); o.append(t(cx[7], y, f"{r['threads']}", 1.7))
        o.append(t(cx[8], y, f"{r['max_stitch']:.2f} mm", 1.7)); o.append(t(cx[9], y, f"{mh(r):.1f}", 1.7)); o.append(t(cx[10], y, f"{sum(mh(s) for s in secs):.1f}", 1.7))
        o.append(t(cx[11], y, f"{len(r['splits']['sections'])}", 1.7))
    y = 36 + len(PC) * 4.6 + 1
    o.append(t(cx[2], y, "TOTAL / JACKET", 1.85, 700)); o.append(t(cx[3], y, f"{TOT:,}", 1.85, 700)); o.append(t(cx[4], y, f"{TRIMS:,}", 1.85, 700))
    o.append(t(cx[9], y, f"{MH_FULL:.1f}", 1.85, 700)); o.append(t(cx[10], y, f"{MH_SPLIT:.1f}", 1.85, 700)); o.append(t(cx[11], y, f"{HOOP}", 1.85, 700))
    o.append(t(12, y + 5, "Fidelity first (LESSONS A11): tonal trace of the mockup + founder close-ups, with motif references (lobes, clumps, florets, buildings as objects) — very dense, many trims.", 1.65, 600, ORANGE))
    o.append(t(12, y + 8.4, "These numbers are REPORTED, not limits; the clean-up pass (density, trims, stop merges) happens after the size-M strike-off shows what is needed.", 1.65, 600, ORANGE))
    qy = y + 15
    o.append(t(12, qy, "OPEN QUESTIONS — confirm before sampling", 2.5, 700))
    qs = [f"1. Frame: on {FR_S} size M needs {HOOP} hoopings (back 4, fronts 2 each, sleeves 4 each; 3XL back 6). Larger frames (e.g. 600 × 400 jacket-back) remove most joins. Which frames exist?",
          "2. Cost: ~" + f"{MH_SPLIT:.0f}" + " h of one head per jacket at the factory speed. Confirm the price basis (F1) before bulk; a clean-up pass can cut trims + density after the sew-out.",
          "3. IP — CLOSED. Founder decision 2026-10-19: follow the reference composition (castle on the falls, closed arching tree, karamon, pagoda, gate tower, bridge).",
          f"4. Thread board: {len(cfcore.sewn_threads())} threads sewn ({len(cfcore.CF_KEYS)} targets read from a low-res AI mockup) — approve physical colours (G3); each file sews ≤ 12 (merges per piece on G3 / spec p4).",
          "5. Armholes as wrap seams (art 3 mm each side, no armhole topstitch) — OK for construction (T7)?",
          "6. Grading A 92 % / B 100 % / C 108 %, one file per size per piece; body about CB/CF + hem, sleeves about the cuff seam. OK?",
          "7. Shell: piece-dyed + pre-washed navy duck assumed. Dense embroidery on all five pieces will shrink panels — measure on the strike-off (F1).",
          "8. Reference: mockup (placement + scale) + founder close-ups (inputs/closeups/, registered TPS, traced) + reference.png (structure where the AI close-up is garbled). Gate tower (SL) + village houses are redrawn objects, low-res mockup only.",
          "9. DST/PES are production-intent drafts: the factory digitizer checks density + pull on 12 oz duck and edits before the sew-out."]
    for i, q in enumerate(qs): o.append(t(12, qy + 5 + i * 3.7, q, 1.7))
    return o

def files_page():
    o = hdr("PRODUCTION STITCH FILES + HOOP SPLITS — every size", "DST (Tajima) + PES, one full file + split files per size per piece. Counts read back from the files (trims from the DST). Origin = centre of each file's design.", "G5")
    hd = ["Size", "Art", "Piece", "Full file mm", "Stitches", "Trims", "Stops", "Col.", "Split files: stitches / trims (size mm)", "Fit", "h (split)"]
    cx = [12, 21, 28, 38, 58, 74, 85, 94, 102, 262, 272]
    for x_, h in zip(cx, hd): o.append(t(x_, 31, h, 1.5, 700, MUTED))
    y = 35; allfit = True; rh = 4.05
    for i, sz in enumerate(cfcore.SIZES):
        for j, P in enumerate(PC):
            r = ALL.get(sz, {}).get(P)
            if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.6)}" width="{SW-22}" height="{rh}" fill="#F5F2EC"/>')
            o.append(t(cx[0], y, sz if j == 0 else "", 1.5, 700)); o.append(t(cx[1], y, cfcore.GRADE[sz][0] if j == 0 else "", 1.5, 700, RED)); o.append(t(cx[2], y, P, 1.5, 600))
            if r and "full" in r:
                fu = r["full"]; secs = r.get("splits", {}).get("sections", {})
                o.append(t(cx[3], y, f"{fu['size_mm'][0]:.0f} × {fu['size_mm'][1]:.0f}", 1.45)); o.append(t(cx[4], y, f"{fu['stitches']:,}", 1.45))
                o.append(t(cx[5], y, f"{fu['trims']}", 1.45)); o.append(t(cx[6], y, f"{fu['stops']}", 1.45)); o.append(t(cx[7], y, f"{fu['threads']}", 1.45))
                s = "   ".join(f"{nm[:2]} {v['stitches']/1000:.0f}k/{v['trims']} ({v['size_mm'][0]:.0f}×{v['size_mm'][1]:.0f})" for nm, v in secs.items())
                o.append(t(cx[8], y, s, 1.4))
                fits = bool(secs) and all(v["fits"] for v in secs.values()); allfit &= fits
                o.append(t(cx[9], y, "yes" if fits else "CHECK", 1.45, 700, GREEN if fits else RED))
                o.append(t(cx[10], y, f"{sum(mh(v) for v in secs.values()):.1f}", 1.45))
            else:
                o.append(t(cx[3], y, "pending", 1.45, 400, MUTED)); allfit = False
            y += rh
    y += 2
    o.append(t(12, y, f"All split files fit {FR_S} minus 16 mm margin, crosses included: {'YES' if allfit else 'CHECK'}.  S1..S4 = top-left, top-right, bottom-left, bottom-right (S1/S2 = top/bottom on the fronts). k = thousand stitches.", 1.55, 700, GREEN if allfit else RED))
    o.append(t(12, y + 3.4, "Thread chart per file: <file>_thread-chart.txt in the zip. Registration crosses sew at the start of stop 1 in stop 1's thread (no separate basting colour, factory limit 12).", 1.5, 400, MUTED))
    return o

def hooping_page():
    o = hdr("HOOPING TABLE — split lines + needle starts, size M (all sizes in result_<piece>.json)", f"Frame {FR_S} mm (factory.json{'' if PROF['frames_confirmed'] else ', PROPOSED'}). Coordinates in mm on each pattern piece (G2 / T13). DXF layer 13 = these points, layer 8 = split lines.", "G6")
    hd = ["Piece", "Split x", "Split y", "Section", "Needle start (x, y)", "File mm", "Stitches", "Trims", "Stops", "h", "Fits"]
    cx = [12, 26, 40, 54, 76, 108, 132, 152, 166, 178, 190]
    for x_, h in zip(cx, hd): o.append(t(x_, 31, h, 1.6, 700, MUTED))
    y = 36; i = 0
    for P in PC:
        sp = CUR[P]["splits"]
        for k, (nm, s) in enumerate(sp["sections"].items()):
            if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.7)}" width="190" height="3.8" fill="#F5F2EC"/>')
            if k == 0:
                o.append(t(cx[0], y, P, 1.6, 700))
                o.append(t(cx[1], y, f"{sp['sx']:.1f}" if sp.get("sx") is not None else "—", 1.55, 700, RED))
                o.append(t(cx[2], y, f"{sp['sy']:.1f}" if sp.get("sy") is not None else "—", 1.55, 700, RED))
            o.append(t(cx[3], y, nm, 1.5)); o.append(t(cx[4], y, f"({s['origin'][0]:+.1f}, {s['origin'][1]:.1f})", 1.5))
            o.append(t(cx[5], y, f"{s['size_mm'][0]:.0f} × {s['size_mm'][1]:.0f}", 1.5)); o.append(t(cx[6], y, f"{s['stitches']:,}", 1.5))
            o.append(t(cx[7], y, f"{s['trims']}", 1.5)); o.append(t(cx[8], y, f"{s['stops']}", 1.5)); o.append(t(cx[9], y, f"{mh(s):.1f}", 1.5))
            o.append(t(cx[10], y, "yes" if s["fits"] else "NO", 1.5, 700, GREEN if s["fits"] else RED)); y += 3.8; i += 1
        y += 1.2
    bx = 206; o.append(t(bx, 33, "SEWING A SPLIT PIECE", 2.0, 700))
    steps = ["1. Mark CB / CF / sleeve centre line, the split", "   lines + needle starts on the cut piece (chalk,", "   from the DXF / 1:1 plot).",
             "2. Hoop S1. Stop 1 opens with the registration", "   crosses (stop-1 thread). Sew S1.",
             "3. Re-hoop the next section; align the needle on", "   the shared crosses, sew them (check), then the", "   section. Repeat for S3, S4.",
             "4. Fills crossing a split overlap 1.2 mm; florets,", "   petals and small motifs < 70 mm go whole to", "   one file.",
             "5. Pick out the crosses, trim backing after the", "   last section.",
             "", "Split lines are searched (30-70 % across, 15-85 %", "down) for the least art cut that still fits the", "frame with the crosses; check the joins on the", "strike-off photos (F1)."]
    for k, st_ in enumerate(steps): o.append(t(bx, 38 + k * 3.2, st_, 1.55))
    return o

def f1_pages():
    import sheet as _SH; _SH.FOOT = SB.FOOT
    so = [dict(file=os.path.basename(CUR[p]["file"]) + ".dst", piece=f"{p} {cfcore.PIECE_NAME[p]} (full file)", stitches=CUR[p]["stitches"], trims=CUR[p]["trims"]) for p in PC]
    th = [dict(name=PAL[k][1], code=f"Isacord {SB.TH[k]['isacord'][0]} / Polyneon {SB.TH[k]['polyneon'][0]}", de=min(SB.TH[k]["isacord"][3], SB.TH[k]["polyneon"][3])) for k in cfcore.sewn_threads()]
    pcs = [dict(piece=f"{cfcore.PIECE_ELEM[p]} {p}", w=CUR[p]["size_mm"][0], h=CUR[p]["size_mm"][1], hoopings=len(CUR[p]["splits"]["sections"])) for p in PC]
    return FA.requests_page(cfcore.NAME, so, th, pcs, page="F1", prof=PROF)

def build():
    pages = {"G1": None, "G2": overview(), "G3": threads(), "G4": summary(), "G5": files_page(), "G6": hooping_page()}
    index = [("G1 Cover + contents", 1), ("G2 Placement overview", 2), ("G3 Thread + trim summary", 3), ("G4 Stitch summary + open questions", 4),
             ("G5 Production stitch files + hoop splits", 5), ("G6 Hooping table (split lines, needle starts)", 6)]
    pg = 7
    for e, path in SPECS.items():
        n = len(PdfReader(path).pages); index.append((f"{e} {cfcore.ELEMS[e][0].replace('-', ' ')} spec ({n} pp)", pg)); pg += n
    index.append(("F1 Factory requests", pg))
    pages["G1"] = cover(index)
    w = PdfWriter()
    for k in ("G1", "G2", "G3", "G4", "G5", "G6"):
        svg = doc(pages[k]); cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"{k}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"prev_{k}.png", output_width=2400)
        w.append(PdfReader(f"{k}.pdf"))
    for e, path in SPECS.items(): w.append(PdfReader(path))
    for i, svg in enumerate(f1_pages()):
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"F{i+1}.pdf"); cairosvg.svg2png(bytestring=svg.encode(), write_to=f"prev_F{i+1}.png", output_width=2400)
        w.append(PdfReader(f"F{i+1}.pdf"))
    w.write(OUT_PDF)
    print("pages", pg)
    return index

if __name__ == "__main__":
    build()
