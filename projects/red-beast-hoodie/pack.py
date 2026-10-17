"""Embroidery pack G1-G6 + element specs + F1 for the Red Beast hoodie (01 beast head FR+FL, 02 sleeve streaks SR+SL).
Every count comes from the stitch files (dst_current.json / dst_all.json, re-read by make_current.py)."""
import rbcore
import os, json, pickle, glob
import cairosvg
from shapely.ops import unary_union
from shapely.geometry import LineString
from pypdf import PdfWriter, PdfReader
from sheet import t, swatch, doc, INK, MUTED, RED, ORANGE, GUIDE, GREEN, SW, SH
from render import f
from motifs2 import HEX, PAL
import tech, stitchrender as SR
import specbase as SB
from specbase import img_tag
import front as F, espec, emb_place as EP, factory as FA
PROF = FA.load(); FRAME = FA.largest_frame(PROF); FR_S = f"{FRAME[0]:.0f} × {FRAME[1]:.0f}"
def mh(r): return FA.machine_hours(r["stitches"], PROF, trims=r["trims"], colour_changes=r["stops"] - 1)
dst2 = rbcore.patch_dst2()

REV, DATE = rbcore.REV_EMB, rbcore.DATE
SB.FOOT = f"HAKI STUDIOS · {rbcore.NAME} · EMBROIDERY · {REV} · {DATE}"
D = pickle.load(open("art_M.pkl", "rb")); V = {P: D[P] for P in rbcore.PIECES}
CUR = json.load(open("dst_current.json")); ALL = json.load(open("dst_all.json"))
PL = json.load(open("place_check.json")); WELT = json.load(open("welt.json"))
P4 = rbcore.PIECES
BB = {p: unary_union([r["geom"] for r in V[p]]).bounds for p in P4}
OUT_PDF = f"out/HAKI_{rbcore.SHORT}_EMBROIDERY-PACK_{REV.replace(' ', '')}.pdf"
SPEC = {e: glob.glob(f"out/{e}_{rbcore.ELEMS[e][0]}/*SPEC_*.pdf")[0] for e in rbcore.ELEMS}
def hdr(title, sub, page): return SB.header(title, sub, page)
TOT = sum(CUR[p]["stitches"] for p in P4); TRIMS = sum(CUR[p]["trims"] for p in P4)
MH = sum(mh(CUR[p]) for p in P4)
def secs(p): return CUR[p]["splits"].get("sections", {}) or {}
def hoopings(p, d=None): s = (d or CUR[p])["splits"].get("sections", {}); return len(s) if s else 1
MH_SPLIT = sum((sum(mh(s) for s in secs(p).values()) if secs(p) else mh(CUR[p])) for p in P4)
NH = sum(hoopings(p) for p in P4)
NTH = len({c for p in P4 for c in CUR[p]["colours"]})
ENAME = {"01": "01 Beast head", "02": "02 Sleeve streaks"}

def cover(index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>']
    o.append(t(14, 24, "HAKI STUDIOS", 3.0, 700, MUTED))
    o.append(t(14, 36, "Red Beast hooded jacket · washed black — embroidery", 7.0, 700))
    o.append(t(14, 44, f"{REV} · {DATE} · Drum Island body (hooded variant), size M base · 2 elements, 4 pieces · {NTH} threads · all dimensions mm", 2.6, 400, MUTED))
    o.append(f'<line x1="14" y1="48" x2="{SW-14}" y2="48" stroke="{INK}" stroke-width="0.4"/>')
    fv = espec.piece_view_png("01", V, 2.0); tag, h = img_tag(fv, 14, 54, 100); o.append(tag)
    sv = espec.piece_view_png("02", V, 1.2); tag2, h2 = img_tag(sv, 118, 54, 78); o.append(tag2)
    o.append(t(14, 54 + h + 3.5, "01 FRONTS (size M stitch render)", 2.1, 700)); o.append(t(118, 54 + h2 + 3.5, "02 SLEEVES (S01 right | S02 left, front halves)", 2.1, 700))
    o.append(t(14, 54 + h + 7.5, "Back + hood: no embroidery [PROPOSED — the mockup shows the front only].", 1.9, 600, ORANGE))
    ix = 202
    o.append(t(ix, 58, "CONTENTS", 2.8, 700)); y = 64
    for name, pg in index:
        o.append(t(ix, y, name, 2.0)); o.append(t(SW - 14, y, f"{pg}", 2.0, 600, MUTED, "end")); y += 4.1
    y += 4
    o.append(t(ix, y, "TOTALS, SIZE M (read from the DST files)", 2.4, 700)); y += 5
    for a, b in [("Stitches per jacket", f"{TOT:,}"), ("Trims per jacket", f"{TRIMS:,}"),
                 ("Hoopings per jacket", f"{NH} on {FR_S} (fronts 2 each, sleeves {hoopings('SR')} + {hoopings('SL')})"),
                 ("Machine time / jacket", f"{MH_SPLIT:.1f} h split files ({MH:.1f} h full files)"), ("Threads", f"{NTH} in use (40wt); factory max {FA.max_threads(PROF)} per file")]:
        o.append(t(ix, y, a, 1.9, 400, MUTED)); o.append(t(SW - 14, y, b, 1.8, 600, INK, "end")); y += 4
    o.append(t(SW - 14, SH - 8, SB.FOOT, 1.9, 400, MUTED, "end"))
    return o

def overview():
    o = hdr("PLACEMENT OVERVIEW — the art on every piece", "Fronts: x from CF (+ = wearer's left), y down from the CF neck seam. Sleeves: sleeve pattern coords (y = 0 underarm line). Tolerance ±2, rotation ±2°.", "G2")
    fv = espec.piece_view_png("01", V, 2.4); w = 118; tag, h = img_tag(fv, 12, 30, w); o.append(tag)
    bb = espec.view_bbox("01"); s = w / (bb[2] - bb[0]); X = lambda x: 12 + (x - bb[0])*s; Y = lambda y: 30 + (y - bb[1])*s
    for p in ("FR", "FL"):
        b = BB[p]; sy = CUR[p]["splits"].get("sy")
        o.append(f'<rect x="{f(X(b[0]))}" y="{f(Y(b[1]))}" width="{f((b[2]-b[0])*s)}" height="{f((b[3]-b[1])*s)}" fill="none" stroke="{RED}" stroke-width="0.3" stroke-dasharray="1.2 0.8"/>')
        o.append(f'<circle cx="{f(X(b[0]))}" cy="{f(Y(b[1]))}" r="2.6" fill="{RED}"/>' + t(X(b[0]), Y(b[1]) + 0.8, p, 1.6, 700, "#FFFFFF", "middle"))
        if sy is not None:
            o.append(f'<line x1="{f(X(b[0]-6))}" y1="{f(Y(sy))}" x2="{f(X(b[2]+6))}" y2="{f(Y(sy))}" stroke="#0A84FF" stroke-width="0.4" stroke-dasharray="2 1"/>')
            o.append(t(X(b[0]) + 1, Y(sy) - 1, f"{p} split y {sy:.0f}", 1.5, 700, "#0A84FF"))
    sv = espec.piece_view_png("02", V, 1.6); tag, h2 = img_tag(sv, 12, 30 + h + 6, 118); o.append(tag)
    o.append(t(12, 30 + h + 6 + h2 + 3.5, "Size M. Red = art boxes; blue dashed = hoop split lines (G6); orange = keep-out boundary.", 1.8, 700))
    tx = 140; ty = 30
    o.append(t(tx, ty, "ART BOX PER SIZE (mm) + KEEP-OUT CHECK (every rule, every size: emb_place.py)", 2.1, 700))
    hd = ["Size", "Grade", "FR x / y", "FL x / y", "SR x / y", "SL x / y", "Keep-outs"]; cx = [tx, tx + 10, tx + 20, tx + 52, tx + 84, tx + 116, tx + 146]
    for x_, hh in zip(cx, hd): o.append(t(x_, ty + 5, hh, 1.6, 700, MUTED))
    for i, sz in enumerate(rbcore.SIZES):
        pl = EP.place(sz)[0]; y = ty + 9.5 + i*4.0
        if i % 2 == 0: o.append(f'<rect x="{tx-1}" y="{f(y-2.8)}" width="{SW - tx - 11}" height="4" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, sz, 1.7, 700)); o.append(t(cx[1], y, f"{rbcore.GRADE[sz][0]} {rbcore.GRADE[sz][1]*100:.0f}%", 1.6, 700, RED))
        for j, p in enumerate(P4):
            b = pl[p][1].bounds; o.append(t(cx[2 + j], y, f"{b[0]:+.0f}…{b[2]:+.0f} / {b[1]:.0f}…{b[3]:.0f}", 1.45))
        bad = {p: d["fail"] for p, d in PL["sizes"][sz].items() if d["fail"]}
        o.append(t(cx[6], y, "all pass" if not bad else "FAIL " + str(bad)[:30], 1.55, 700, GREEN if not bad else RED))
    ky = ty + 9.5 + 7*4.0 + 5
    o.append(t(tx, ky, "KEEP-OUTS (mm from the sew line, measured on each size's pattern piece, LESSONS A3/C8)", 2.1, 700))
    ko = [f"Fronts: CF zip {F.KEEP_CF:.0f} each side · armhole, shoulder, side {F.KEEP_SEAM:.0f} · hem band seam {F.KEEP_HEM:.0f} · hood/neck seam {F.KEEP_NECK:.0f} [PROPOSED] · welt box {F.KEEP_WELT:.0f}",
          f"Sleeves: cap seam {F.KEEP_SEAM:.0f} · front + back underarm {F.KEEP_SEAM:.0f} · cuff seam {F.KEEP_CUFF:.0f} (self-fabric cuff never embroidered)",
          "Hem band, cuffs, hood (shell + sherpa lining) and back: no embroidery.",
          f"Welts [PROPOSED]: moved {WELT['move_mm'][0]:.0f} out / {WELT['move_mm'][1]:.1f} down from the render (FL welt drawn under the lower jaw)."]
    for i, k in enumerate(ko): o.append(t(tx, ky + 4.4 + i*3.4, k, 1.7))
    my = ky + 4.4 + 4*3.4 + 4
    o.append(t(tx, my, "MINIMUM CLEARANCE, SIZE M (mm; min in brackets)", 2.1, 700))
    for i, p in enumerate(P4):
        c = PL["sizes"]["M"][p]["clear"]; mn = F.piece_min(p)
        o.append(t(tx, my + 4.2 + i*3.3, f"{p}: " + " · ".join(f"{k} {v:.1f} ({mn[k]:.0f})" for k, v in c.items()), 1.55))
    zy = my + 4.2 + 4*3.3 + 4
    o.append(t(tx, zy, "MATCHING ACROSS THE ZIP", 2.1, 700))
    for i, l in enumerate(["FR + FL are graded about the CF neck point (0, 0): the jaw, outline and strands reach the zip keep-out lines at the",
                           "same height on both halves. Hoop to the marked CF line; after the zip is set the head must read continuous (±1 mm)."]):
        o.append(t(tx, zy + 4.2 + i*3.2, l, 1.65))
    return o

def threads():
    o = hdr("THREAD + TRIM SUMMARY", f"One palette for the whole jacket — {NTH} threads (factory limit {FA.max_threads(PROF)} per file). Approve a physical thread board (Isacord or Madeira Polyneon) before sampling; hex = on-screen target read from the mockup.", "G3")
    use = {k: {} for k in rbcore.RB_KEYS}
    for p in P4:
        for c in CUR[p]["colours"]: use[c][p] = use[c].get(p, 0) + 1
    hd = ["", "Thread", "Hex", "Isacord", "ΔE", "Madeira Polyneon", "ΔE", "Wt", "Used for", "Stops FR / FL / SR / SL"]
    cx = [12, 18, 44, 58, 88, 96, 130, 138, 146, 236]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.75, 700, MUTED))
    TH = SB.TH; rh = 5.5
    for i, k in enumerate(rbcore.RB_KEYS):
        y = 36 + i*rh
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3.4)}" width="{SW-22}" height="{f(rh)}" fill="#F5F2EC"/>')
        iso, pn = TH[k]["isacord"], TH[k]["polyneon"]
        ci = GREEN if iso[3] < 3 else (ORANGE if iso[3] < 5.5 else RED); cp = GREEN if pn[3] < 3 else (ORANGE if pn[3] < 5.5 else RED)
        o.append(swatch(cx[0], y, k, 4.5, 2.8)); o.append(t(cx[1], y, PAL[k][1], 1.9, 600)); o.append(t(cx[2], y, HEX[k], 1.75, 400, MUTED))
        o.append(t(cx[3], y, f"{iso[0]} {iso[1]}"[:22], 1.75)); o.append(t(cx[4], y, f"{iso[3]:.1f}", 1.7, 600, ci))
        o.append(t(cx[5], y, f"{pn[0]} {pn[1]}"[:24], 1.75)); o.append(t(cx[6], y, f"{pn[3]:.1f}", 1.7, 600, cp))
        o.append(t(cx[7], y, "40", 1.75)); o.append(t(cx[8], y, PAL[k][2][:62], 1.65, 400, MUTED))
        o.append(t(cx[9], y, " / ".join(str(use[k].get(p, 0)) for p in P4), 1.75, 600))
    yb = 36 + len(rbcore.RB_KEYS)*rh + 3
    o.append(t(12, yb, "ΔE2000 vs target: green < 3, amber 3–5.5, red > 5.5 — amber/red rows must be picked from the physical card. All targets are PROPOSED (read from the mockup).", 1.8, 600, ORANGE))
    o.append(t(12, yb + 3.5, "Shadow black on washed black duck reads as texture, not colour (as in the mockup's detail panel): judge it on the strike-off, in raking light.", 1.8, 400, MUTED))
    o.append(t(12, yb + 10, "TRIMS + CONSUMABLES (per jacket)", 2.2, 700))
    fw = max(BB[p][2]-BB[p][0] for p in P4) + 14; fh = max(BB[p][3]-BB[p][1] for p in P4) + 14
    tr = [("Backing", "2.5 oz cutaway, black, cut 30 larger than each hooping; trim to 5 from stitching after embroidery (dense head: consider 3 oz on FL)"),
          ("Topping", "none (canvas surface is firm)"), ("Needles", "75/11 sharp (canvas)"), ("Bobbin", "60wt black polyester pre-wound (dark shell)"),
          ("Frames", f"{FR_S} (factory.json{'' if PROF['frames_confirmed'] else ', PROPOSED'}): {NH} hoopings per jacket (split files, G5) · one hooping per piece needs ≥ {fw:.0f} × {fh:.0f} (M)"),
          ("Patches / labels", "none on this garment — all artwork is direct embroidery")]
    for i, (a, b) in enumerate(tr):
        o.append(t(12, yb + 14.5 + i*3.6, a, 1.85, 600)); o.append(t(42, yb + 14.5 + i*3.6, b, 1.85))
    return o

def summary():
    o = hdr("STITCH SUMMARY + OPEN QUESTIONS", "Size M files. Every count read back from the DST (stitches, trims, stops, max stitch).", "G4")
    hd = ["Element", "Piece", "Art box", "Stitches", "Trims", "Trims/10k", "Stops", "Threads", "Max stitch", "Machine time", "Hoopings"]
    cx = [12, 44, 86, 106, 124, 138, 154, 166, 180, 198, 220]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.8, 700, MUTED))
    for i, p in enumerate(P4):
        r = CUR[p]; b = BB[p]; y = 36 + i*4.6
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3)}" width="{SW-22}" height="4.6" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, ENAME[rbcore.PIECE_ELEM[p]], 1.85, 600)); o.append(t(cx[1], y, f"{p} {rbcore.PIECE_NAME[p]}", 1.75))
        o.append(t(cx[2], y, f"{b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}", 1.8)); o.append(t(cx[3], y, f"{r['stitches']:,}", 1.8, 600))
        o.append(t(cx[4], y, f"{r['trims']:,}", 1.8)); o.append(t(cx[5], y, f"{r['trims']/r['stitches']*1e4:.1f}", 1.8)); o.append(t(cx[6], y, f"{r['stops']}", 1.8))
        o.append(t(cx[7], y, f"{r['threads']}", 1.8)); o.append(t(cx[8], y, f"{r['max_stitch']:.2f} mm", 1.8)); o.append(t(cx[9], y, f"{mh(r)*60:.0f} min", 1.8))
        o.append(t(cx[10], y, f"{hoopings(p)}", 1.8))
    y = 36 + len(P4)*4.6 + 1
    o.append(t(cx[2], y, "TOTAL", 1.9, 700)); o.append(t(cx[3], y, f"{TOT:,}", 1.9, 700)); o.append(t(cx[4], y, f"{TRIMS:,}", 1.9, 700)); o.append(t(cx[9], y, f"{MH:.1f} h", 1.9, 700)); o.append(t(cx[10], y, f"{NH}", 1.9, 700))
    o.append(t(12, y + 4.5, "Width check (spec p3): every region code has < 1 % of its area under 0.8 mm (hair tips grown to ≥ 1.0 mm along their skeleton). Max stitch ≤ 7.5 on every file of every size (G5).", 1.7, 400, MUTED))
    o.append(t(12, y + 7.8, f"Machine time = factory.machine_hours: {PROF['spm']} spm + 6 s per trim + 4 s per colour change, one hooping (split files: {MH_SPLIT:.1f} h per jacket). Rev A is built for fidelity: trims + time are reported, cleaned up after the sew-out.", 1.7, 400, MUTED))
    qy = y + 15
    o.append(t(12, qy, "OPEN QUESTIONS — confirm before sampling", 2.6, 700))
    qs = [f"1. Welt pockets [PROPOSED]: the render draws the FL welt under the beast's lower jaw. Both welts moved {WELT['move_mm'][0]:.0f} mm out + {WELT['move_mm'][1]:.1f} mm down (same angle + length). OK, or move the art?",
          "2. Back + hood: plain (the mockup shows the front only). Confirm, or send a back / hood mockup.",
          "3. Armhole crossing: streaks + branch tips end 15 short of the seam on front and sleeve (no wrap). Wrap them across with match marks (3 mm short, Drum Island A4) instead?",
          "4. Hood pattern: body = Drum Island; the hood block is pending in the engine (pattern pages + DXF follow). Neck/hood seam keep-out 10 mm [PROPOSED].",
          f"5. Frame: fronts need 2 hoopings each on {FR_S} (split S1/S2 + registration crosses, G6); a ≥ 300 × 520 frame takes each front in one. Which frames do you have?",
          "6. Thread board: all targets read from an AI mockup — approve physical colours (G3). Shadow black is black-on-black texture: keep it, or drop it to save stitches?",
          "7. Shell: washed black 12 oz duck assumed, washed before embroidery. If garment-washed after embroidery, wash-test the sew-out (dense FL head).",
          "8. Grading: A 92% (XS–S) · B 100% (M–XL) · C 108% (XXL–3XL), one file per size per piece, fronts scaled about the CF neck so the halves meet at the zip.",
          "9. Fidelity first: hair strokes, black ground and 4-thread texture built as in the detail panel; stitches + trims are reported, cleaned up after the sew-out.",
          "10. DST/PES are production-intent drafts: the factory digitizer checks density + pull on the shell and edits before the sew-out."]
    for i, q in enumerate(qs): o.append(t(12, qy + 5 + i*3.6, q, 1.75))
    return o

def files_page():
    o = hdr("PRODUCTION STITCH FILES + HOOP SPLITS", "DST (Tajima) + PES, one set per size per piece. Counts read back from the files; trims counted from the DST. Origin = centre of each file's design.", "G5")
    hd = ["Size", "Gr.", "Piece", "Full file mm", "Stitches", "Trims", "Stops", "Max", "S1 top: st / trims / mm", "S2 bottom: st / trims / mm", "Fits"]
    cx = [12, 22, 29, 39, 58, 73, 84, 93, 104, 152, 200]
    for x_, h in zip(cx, hd): o.append(t(x_, 31.5, h, 1.5, 700, MUTED))
    y = 35.3; allfit = True; maxst = 0.0
    for i, sz in enumerate(rbcore.SIZES):
        for p in P4:
            r = ALL.get(sz, {}).get(p)
            if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.3)}" width="198" height="3.05" fill="#F5F2EC"/>')
            o.append(t(cx[0], y, sz if p == "FR" else "", 1.45, 700)); o.append(t(cx[1], y, rbcore.GRADE[sz][0] if p == "FR" else "", 1.45, 700, RED)); o.append(t(cx[2], y, p, 1.45, 600))
            if r and "full" in r:
                fu = r["full"]; maxst = max(maxst, fu["max_stitch"])
                o.append(t(cx[3], y, f"{fu['size_mm'][0]:.0f} × {fu['size_mm'][1]:.0f}", 1.4)); o.append(t(cx[4], y, f"{fu['stitches']:,}", 1.4)); o.append(t(cx[5], y, f"{fu['trims']}", 1.4))
                o.append(t(cx[6], y, f"{fu['stops']}", 1.4)); o.append(t(cx[7], y, f"{fu['max_stitch']:.2f}", 1.4))
                ss = r.get("splits", {}).get("sections", {})
                for j, nm in enumerate(("S1_top", "S2_bottom")):
                    s_ = ss.get(nm)
                    if s_: o.append(t(cx[8 + j], y, f"{s_['stitches']:,} / {s_['trims']} / {s_['size_mm'][0]:.0f}×{s_['size_mm'][1]:.0f}", 1.4))
                if not ss: o.append(t(cx[8], y, "one hooping (full file)", 1.4, 400, MUTED))
                fits = all(v["fits"] for v in ss.values()) if ss else (fu["size_mm"][0] <= FRAME[0] - 16 and fu["size_mm"][1] <= FRAME[1] - 16)
                allfit &= fits; o.append(t(cx[10], y, "yes" if fits else "CHECK", 1.4, 700, GREEN if fits else RED))
            else:
                o.append(t(cx[3], y, "pending", 1.4, 400, MUTED)); allfit = False
            y += 3.05
    y += 2.5
    o.append(t(12, y, f"All files: max sewn stitch {maxst:.2f} mm (limit 7.5) · ≤ {FA.max_threads(PROF)} thread colours per file (factory.check_threads on every PES) · every split section fits {FR_S} − 16: {'yes' if allfit else 'CHECK'}.", 1.55, 700, GREEN if allfit else RED))
    bx = 214; o.append(t(bx, 31.5, "WHAT IS DIGITIZED", 2.0, 700)); yy = 35.5
    notes = ["Order per file: red hair strokes + streaks →", "crimson shadow strokes → black ground →", "cream outlines, teeth + lightning (on top).",
             "", "Thin strokes: satin columns turning along", "each skeleton branch (forks = separate", "columns), ≥ 1.0 wide, split satin > 7.",
             "", "Wide masses: tatami along the traced stroke", "flow, 14 mm cells with their own angle", "(long-and-short look), lattice underlay > 60 mm².",
             "", "Ties: 3-stitch tie-on/off at every trim +", "colour change; trims on jumps ≥ 2.5 mm.",
             "", "SEWING A SPLIT PIECE", "1. Mark CF / sleeve centre + split line.", "2. Hoop S1; stop 1 opens with the", "   registration crosses (stop-1 thread).",
             "3. Re-hoop for S2, align on the crosses.", "4. Fills crossing the split overlap 1.2;", "   motifs < 70 go whole to one file.", "5. Pick out the crosses after S2."]
    for l in notes:
        o.append(t(bx, yy, l, 1.55, 700 if l.startswith("SEWING") else 400)); yy += 3.1
    return o

def split_head_cut(sz, P):
    """mm of cream outline the split line crosses (a joint to check on the strike-off)"""
    sp = ALL[sz][P]["splits"]; sy = sp.get("sy")
    if sy is None: return 0.0
    D_ = pickle.load(open(f"art_{sz}.pkl", "rb"))
    u = unary_union([r["geom"] for r in D_[P] if r["col"] == "rb_cream"])
    return u.intersection(LineString([(-600, sy), (600, sy)])).length if not u.is_empty else 0.0

def hooping_page():
    o = hdr("HOOPING TABLE — split line + needle start per file, every size", f"Frame {FR_S} mm (factory.json{'' if PROF['frames_confirmed'] else ', PROPOSED'}). Fronts: x from CF, y from the CF neck seam. Sleeves: sleeve pattern coords. DXF layer 13 = these points.", "G6")
    hd = ["Size", "Piece", "Split y", "S1 top: needle start (x, y)", "S1 mm", "S2 bottom: needle start (x, y)", "S2 mm", "Full file start (x, y)", "Cream outline crossed", "Machine time", "Trims", "Fit"]
    cx = [12, 22, 32, 46, 84, 102, 140, 158, 192, 222, 244, 262]
    for x_, h in zip(cx, hd): o.append(t(x_, 31.5, h, 1.5, 700, MUTED))
    y = 35.3
    for i, sz in enumerate(rbcore.SIZES):
        for P in P4:
            r = ALL[sz][P]; sp = r["splits"]; ss = sp.get("sections", {})
            if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.3)}" width="{SW-22}" height="3.05" fill="#F5F2EC"/>')
            o.append(t(cx[0], y, sz if P == "FR" else "", 1.45, 700)); o.append(t(cx[1], y, P, 1.45, 600))
            o.append(t(cx[2], y, f"{sp['sy']:.1f}" if sp.get("sy") is not None else "—", 1.45, 700, RED))
            for j, nm in enumerate(("S1_top", "S2_bottom")):
                s_ = ss.get(nm)
                if s_:
                    o.append(t(cx[3 + 2*j], y, f"({s_['origin'][0]:+.1f}, {s_['origin'][1]:.1f})", 1.4)); o.append(t(cx[4 + 2*j], y, f"{s_['size_mm'][0]:.0f} × {s_['size_mm'][1]:.0f}", 1.4))
            if not ss: o.append(t(cx[3], y, "one hooping", 1.4, 400, MUTED))
            fo = r["full"]["origin"]; o.append(t(cx[7], y, f"({fo[0]:+.1f}, {fo[1]:.1f})", 1.4))
            cc = split_head_cut(sz, P)
            o.append(t(cx[8], y, f"{cc:.0f} mm" + (" — check joint" if cc > 1 else ""), 1.4, 600 if cc > 1 else 400, ORANGE if cc > 1 else INK))
            hrs = sum(mh(s) for s in ss.values()) if ss else mh(r["full"]); trm = sum(s["trims"] for s in ss.values()) if ss else r["full"]["trims"]
            o.append(t(cx[9], y, f"{hrs*60:.0f} min", 1.4)); o.append(t(cx[10], y, f"{trm}", 1.4))
            ok = all(v["fits"] for v in ss.values()) if ss else True
            o.append(t(cx[11], y, "yes" if ok else "NO", 1.45, 700, GREEN if ok else RED))
            y += 3.05
    y += 3
    notes = ["The split line is chosen where it cuts the least art inside the frame (searched 12–88 % of the art height). Where it crosses a cream",
             "outline (amber), fills larger than 70 mm overlap 1.2 mm across the line — check that joint on the strike-off photos.",
             "Machine time + trims per piece = sum over its hoopings (split files), factory.machine_hours; hooping time not included.",
             "Registration crosses sew at the start of stop 1 in that stop's thread (factory: max 12 colours per file, no separate basting thread);",
             "long 4 mm stitches on bare fabric 12 mm outside the art — S2 re-registers on the crosses S1 sewed; pick them out after S2."]
    for i, l in enumerate(notes): o.append(t(12, y + i*3.3, l, 1.55, 400, MUTED))
    return o

def f1_pages():
    import sheet as _SH; _SH.FOOT = SB.FOOT
    so = [dict(file=os.path.basename(CUR[p]["file"]) + ".dst", piece=f"{p} {rbcore.PIECE_NAME[p]}", stitches=CUR[p]["stitches"], trims=CUR[p]["trims"]) for p in P4]
    so += [dict(file=os.path.basename(s["file"]) + ".dst", piece=f"{p} split {nm}", stitches=s["stitches"], trims=s["trims"]) for p in P4 for nm, s in secs(p).items()]
    th = [dict(name=PAL[k][1], code=f"Isacord {SB.TH[k]['isacord'][0]} / Polyneon {SB.TH[k]['polyneon'][0]}", de=min(SB.TH[k]["isacord"][3], SB.TH[k]["polyneon"][3])) for k in rbcore.RB_KEYS]
    pcs = [dict(piece=f"{rbcore.PIECE_ELEM[p]} {p}", w=CUR[p]["size_mm"][0], h=CUR[p]["size_mm"][1], hoopings=hoopings(p)) for p in P4]
    return FA.requests_page(rbcore.NAME, so, th, pcs, page="F1", prof=PROF)

def build():
    pages = {"G1": None, "G2": overview(), "G3": threads(), "G4": summary(), "G5": files_page(), "G6": hooping_page()}
    index = [("G1 Cover + contents", 1), ("G2 Placement overview + keep-outs", 2), ("G3 Thread + trim summary", 3), ("G4 Stitch summary + open questions", 4),
             ("G5 Production stitch files + hoop splits", 5), ("G6 Hooping table (split lines, needle starts)", 6)]
    pg = 7
    for e, path in SPEC.items():
        n = len(PdfReader(path).pages); index.append((f"{ENAME[e]} element spec ({n} pp)", pg)); pg += n
    index.append(("F1 Factory requests", pg))
    pages["G1"] = cover(index)
    w = PdfWriter()
    for k in ("G1", "G2", "G3", "G4", "G5", "G6"):
        svg = doc(pages[k]); cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"{k}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"prev_{k}.png", output_width=2400)
        w.append(PdfReader(f"{k}.pdf"))
    for e, path in SPEC.items(): w.append(PdfReader(path))
    for i, svg in enumerate(f1_pages()):
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"F{i+1}.pdf"); cairosvg.svg2png(bytestring=svg.encode(), write_to=f"prev_F{i+1}.png", output_width=2400)
        w.append(PdfReader(f"F{i+1}.pdf"))
    w.write(OUT_PDF)
    print("pages", pg, OUT_PDF)

if __name__ == "__main__":
    build()
