"""Embroidery pack G1-G6 + element specs + F1 for the blossom tetra hoodie (slug koi-blossom-hoodie) (01 front FR/FL, 02 sleeves SR/SL).
Every count comes from the stitch files (dst_current.json / dst_all.json, readback.dst)."""
import kbcore
import os, json, pickle, glob
import cairosvg
from shapely.ops import unary_union
from shapely import affinity
from pypdf import PdfWriter, PdfReader
from sheet import t, swatch, doc, INK, MUTED, RED, ORANGE, GUIDE, GREEN, SW, SH
from render import f
from motifs2 import HEX, PAL
import stitchrender as SR
import specbase as SB
from specbase import img_tag
import front as F, espec, emb_place as EP, factory as FA
PROF = FA.load(); FRAME = FA.largest_frame(PROF); FR_S = f"{FRAME[0]:.0f} × {FRAME[1]:.0f}"
def mh(r): return FA.machine_hours(r["stitches"], PROF, trims=r["trims"], colour_changes=r["stops"] - 1)

REV, DATE = kbcore.REV_EMB, kbcore.DATE
SB.FOOT = f"HAKI STUDIOS · {kbcore.NAME} · EMBROIDERY · {REV} · {DATE}"
D = pickle.load(open("art_M.pkl", "rb")); V = {p: D[p] for p in kbcore.PIECES}
CUR = json.load(open("dst_current.json")); ALL = json.load(open("dst_all.json")); META = json.load(open("scene_meta.json"))
SUMS = {el: json.load(open(f"out/{el}_{kbcore.ELEMS[el][0]}/summary.json")) for el in kbcore.ELEMS}
PS = kbcore.PIECES
BB = {p: unary_union([r["geom"] for r in V[p]]).bounds for p in PS}
OUT_PDF = f"out/HAKI_{kbcore.SHORT}_EMBROIDERY-PACK_{REV.replace(' ', '')}.pdf"
SPEC = {el: glob.glob(f"out/{el}_{kbcore.ELEMS[el][0]}/*SPEC_*.pdf")[0] for el in kbcore.ELEMS}
def hdr(title, sub, page): return SB.header(title, sub, page)
TOT = sum(CUR[p]["stitches"] for p in PS); TRIMS = sum(CUR[p]["trims"] for p in PS)
MH = sum(mh(CUR[p]) for p in PS)
MH_SPLIT = sum(mh(s) for p in PS for s in CUR[p]["splits"]["sections"].values())
HOOPS = sum(max(1, len(CUR[p]["splits"]["sections"])) for p in PS)
EL_OF = kbcore.ELEM_OF

def views(ppm):
    a, _, _ = espec.view_png("01", V, ppm); b, _, _ = espec.view_png("02", V, ppm * 0.8)
    return a, b

def cover(index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>']
    o.append(t(14, 24, "HAKI STUDIOS", 3.0, 700, MUTED))
    o.append(t(14, 36, "Blossom tetra hooded jacket · washed navy — embroidery", 7.0, 700))
    o.append(t(14, 44, f"{REV} · {DATE} · Drum Island body, size M base · 2 elements (01 front, 02 sleeves), 4 pieces · 12 threads · all dimensions mm", 2.6, 400, MUTED))
    o.append(f'<line x1="14" y1="48" x2="{SW-14}" y2="48" stroke="{INK}" stroke-width="0.4"/>')
    a, b = views(2.0)
    tag, h = img_tag(a, 14, 54, 92); o.append(tag); o.append(t(14, 54 + h + 3.5, "FRONT (size M stitch render)", 2.0, 700))
    tag, h2 = img_tag(b, 110, 62, 86); o.append(tag); o.append(t(110, 62 + h2 + 3.5, "SLEEVES (pattern pieces, front half embroidered)", 2.0, 700))
    o.append(t(14, 54 + h + 8, "Back + hood: no embroidery [proposed — confirm, the mockup shows the front only].", 1.9, 600, ORANGE))
    REG = json.load(open("trace/closeup_reg.json"))
    gl = [f"REFERENCE: lilies + petals traced from the AI close-up of the FR upper panel (registered, drift {REG['projective']['mean_mm']} mm -> positions from the mockup).",
          "NO close-up for: FR hem lily, the whole FL panel, both sleeves — redrawn from the low-res mockup with the traced templates. FISH: tetras from inputs/reference_fish.png.",
          f"GRADING [proposed — confirm]: XS–S 92 %, M–XL 100 % (L + XL sew the M art: FR {ALL['L']['FR']['full']['size_mm'][0]:.0f} × {ALL['L']['FR']['full']['size_mm'][1]:.0f}, "
          f"{ALL['L']['FR']['full']['stitches']:,} / {ALL['XL']['FR']['full']['stitches']:,} st, only re-fitted to their keep-outs), XXL–3XL 108 %."]
    for i, l in enumerate(gl): o.append(t(14, 54 + h + 12 + i*3.4, l, 1.75, 600, ORANGE if i == 2 else INK))
    ry = 54 + h + 12 + len(gl)*3.4 + 3
    o.append(t(14, ry, "REVISION LOG", 2.2, 700))
    import textwrap
    for rv, dt, txt in kbcore.REV_LOG:
        ls = textwrap.wrap(txt, 150)
        o.append(t(14, ry + 4, f"{rv} · {dt}", 1.75, 700))
        for j, l in enumerate(ls): o.append(t(36, ry + 4 + j*3.0, l, 1.7, 600 if "FOUNDER" in l else 400, RED if "FOUNDER" in l else INK))
        ry += 4 + 3.0*(len(ls) - 1) + 1.5
    ix = 204
    o.append(t(ix, 58, "CONTENTS", 2.8, 700)); y = 64
    for name, pg in index:
        o.append(t(ix, y, name, 1.95)); o.append(t(SW - 14, y, f"{pg}", 1.95, 600, MUTED, "end")); y += 4.0
    y += 4
    o.append(t(ix, y, "TOTALS, SIZE M (read from the DST files)", 2.3, 700)); y += 5
    for a_, b_ in [("Stitches per jacket", f"{TOT:,}"), ("Trims per jacket", f"{TRIMS:,}"),
                   ("Hoopings per jacket", f"{HOOPS} on {FR_S} (split files)"),
                   ("Machine time / jacket", f"{MH_SPLIT:.1f} h split ({MH:.1f} h full files)"), ("Threads", f"12 (40wt polyester), ≤ {FA.max_threads(PROF)} per file")]:
        o.append(t(ix, y, a_, 1.9, 400, MUTED)); o.append(t(SW - 14, y, b_, 1.85, 600, INK, "end")); y += 4
    o.append(t(SW - 14, SH - 8, SB.FOOT, 1.9, 400, MUTED, "end"))
    return o

def overview():
    o = hdr("PLACEMENT OVERVIEW — art on the garment pieces", "Fronts: x from CF (+ = wearer's left), y down from the CF neck seam. Sleeves: x from the sleeve centre line, y down from the underarm line. Tolerance ±2, rotation ±2°.", "G2")
    for el, (x, y, w) in (("01", (12, 30, 104)), ("02", (120, 30, 76))):
        im, pcs, bbox = espec.view_png(el, V, 2.0); tag, h = img_tag(im, x, y, w); o.append(tag)
        s = w / (bbox[2] - bbox[0]); X = lambda xx: x + (xx - bbox[0])*s; Y = lambda yy: y + (yy - bbox[1])*s
        for p, dx in pcs:
            b = BB[p]
            o.append(f'<rect x="{f(X(b[0] + dx))}" y="{f(Y(b[1]))}" width="{f((b[2]-b[0])*s)}" height="{f((b[3]-b[1])*s)}" fill="none" stroke="{RED}" stroke-width="0.3" stroke-dasharray="1.2 0.8"/>')
            o.append(f'<circle cx="{f(X(b[0] + dx))}" cy="{f(Y(b[1]))}" r="2.4" fill="{RED}"/>' + t(X(b[0] + dx), Y(b[1]) + 0.7, p, 1.5, 700, "#FFFFFF", "middle"))
            sy = CUR[p]["splits"].get("sy")
            if sy is not None and len(CUR[p]["splits"]["sections"]) > 1:
                o.append(f'<line x1="{f(X(b[0] + dx - 4))}" y1="{f(Y(sy))}" x2="{f(X(b[2] + dx + 4))}" y2="{f(Y(sy))}" stroke="#0A84FF" stroke-width="0.4" stroke-dasharray="2 1"/>')
        o.append(t(x, y + h + 3.2, ("FRONT, size M" if el == "01" else "SLEEVES, size M (SR left, SL right)") + " — red = art boxes, blue dashed = hoop split", 1.6, 700))
    tx = 200; ty = 30
    o.append(t(tx, ty, "ART BOX PER SIZE (mm, piece coords)", 2.1, 700))
    hd = ["Size", "Art", "FR x / y", "FL x / y", "SR x / y", "SL x / y"]; cx = [tx, tx + 9, tx + 16, tx + 36, tx + 56, tx + 75]
    for x_, hh in zip(cx, hd): o.append(t(x_, ty + 5, hh, 1.5, 700, MUTED))
    for i, sz in enumerate(kbcore.SIZES):
        pl = EP.place(sz)[0]; y = ty + 9.5 + i*6.2
        if i % 2 == 0: o.append(f'<rect x="{tx-1}" y="{f(y-2.8)}" width="{SW - tx - 11}" height="6.2" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, sz, 1.6, 700)); o.append(t(cx[1], y, kbcore.GRADE[sz][0], 1.6, 700, RED))
        for j, p in enumerate(PS):
            b = pl[p][1].bounds
            o.append(t(cx[2 + j], y, f"{b[0]:+.0f}…{b[2]:+.0f}", 1.4)); o.append(t(cx[2 + j], y + 2.6, f"{b[1]:.0f}…{b[3]:.0f}", 1.4, 400, MUTED))
    ky = ty + 9.5 + 7*6.2 + 4
    o.append(t(tx, ky, "KEEP-OUTS (all sizes, measured: G2 table below + T13)", 2.0, 700))
    ko = [f"CF zip {F.KEEP_CF:.0f} each side · side, armhole, shoulder {F.KEEP_SEAM:.0f}", f"Hem-band seam {F.KEEP_HEM:.0f} · welt box {F.KEEP_WELT:.0f} · hood neck seam {F.KEEP_NECK:.0f}",
          f"Sleeves: cap {F.KEEP_CAP:.0f}, underarm seams {F.KEEP_SEAM:.0f}, cuff seam {F.KEEP_CUFF:.0f}", "Back half of the sleeves, back, hood: no embroidery."]
    for i, k in enumerate(ko): o.append(t(tx, ky + 4.2 + i*3.2, k, 1.6))
    # min clearance per size table
    my = ky + 4.2 + 4*3.2 + 4
    o.append(t(tx, my, "SMALLEST CLEARANCE PER PIECE (mm, min in brackets)", 2.0, 700)); my += 4.5
    allok = True
    for i, sz in enumerate(kbcore.SIZES):
        c = EP.clearances(sz); row = []
        for p in PS:
            k, v = min(((k, v - F.MIN(p)[k]) for k, v in c[p].items()), key=lambda kv: kv[1])
            row.append(f"{p} {c[p][k]:.1f} {k[:6]}"); allok &= v >= -0.3
        o.append(t(tx, my + i*3.1, sz, 1.45, 700)); o.append(t(tx + 8, my + i*3.1, " · ".join(row), 1.3))
    o.append(t(tx, my + 7*3.1 + 1.5, "All keep-outs pass on every size." if allok else "KEEP-OUT FAILURE — see T13", 1.7, 700, GREEN if allok else RED))
    return o

def threads():
    o = hdr("THREAD + TRIM SUMMARY", "One palette for the whole jacket — 12 threads. Approve a physical thread board (Isacord or Madeira Polyneon) before sampling; hex = on-screen target read from the mockup.", "G3")
    use = {k: {} for k in kbcore.KB_KEYS}
    for p in PS:
        for c in CUR[p]["colours"]: use[c][p] = use[c].get(p, 0) + 1
    hd = ["", "Thread", "Hex", "Isacord", "ΔE", "Madeira Polyneon", "ΔE", "Wt", "Used for", "Stops FR / FL / SR / SL"]
    cx = [12, 18, 44, 58, 88, 96, 130, 138, 146, 232]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.75, 700, MUTED))
    TH = SB.TH; rh = 5.0
    for i, k in enumerate(kbcore.KB_KEYS):
        y = 36 + i*rh
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3.2)}" width="{SW-22}" height="{f(rh)}" fill="#F5F2EC"/>')
        iso, pn = TH[k]["isacord"], TH[k]["polyneon"]
        ci = GREEN if iso[3] < 3 else (ORANGE if iso[3] < 5.5 else RED); cp = GREEN if pn[3] < 3 else (ORANGE if pn[3] < 5.5 else RED)
        o.append(swatch(cx[0], y, k, 4.5, 2.8)); o.append(t(cx[1], y, PAL[k][1], 1.9, 600)); o.append(t(cx[2], y, HEX[k], 1.75, 400, MUTED))
        o.append(t(cx[3], y, f"{iso[0]} {iso[1]}"[:22], 1.75)); o.append(t(cx[4], y, f"{iso[3]:.1f}", 1.7, 600, ci))
        o.append(t(cx[5], y, f"{pn[0]} {pn[1]}"[:24], 1.75)); o.append(t(cx[6], y, f"{pn[3]:.1f}", 1.7, 600, cp))
        o.append(t(cx[7], y, "40", 1.75)); o.append(t(cx[8], y, PAL[k][2][:58], 1.65, 400, MUTED))
        o.append(t(cx[9], y, " / ".join(str(use[k].get(p, 0)) for p in PS) if any(use[k].values()) else f"spare — not in {REV} files", 1.75, 600, INK if any(use[k].values()) else MUTED))
    yb = 36 + len(kbcore.KB_KEYS)*rh + 3
    o.append(t(12, yb, "ΔE2000 vs target: green < 3, amber 3–5.5, red > 5.5 — amber/red rows must be picked from the physical card. All targets are PROPOSED (read from a low-res AI mockup).", 1.8, 600, ORANGE))
    o.append(t(12, yb + 7, "TRIMS + CONSUMABLES (per jacket)", 2.2, 700))
    tr = [("Backing", "2.5 oz cutaway, navy/black (dark shell), cut 30 larger than each hooping; trim to 5 from stitching after embroidery"),
          ("Topping", "none (canvas surface is firm)"), ("Needles", "75/11 sharp (canvas)"), ("Bobbin", "60wt navy or black polyester pre-wound (dark shell)"),
          ("Frames", f"{FR_S} (factory.json{'' if PROF['frames_confirmed'] else ', PROPOSED'}): {HOOPS} hoopings per jacket, size M (" + ", ".join(f"{p} {len(CUR[p]['splits']['sections'])}" for p in PS) + "; G5/G6)"),
          ("Patches / labels", "none on this garment — all artwork is direct embroidery")]
    for i, (a, b) in enumerate(tr):
        o.append(t(12, yb + 11.5 + i*3.6, a, 1.85, 600)); o.append(t(42, yb + 11.5 + i*3.6, b, 1.85))
    return o

def summary():
    o = hdr("STITCH SUMMARY + OPEN QUESTIONS", "Size M files. Every count read back from the DST. Run time = factory.machine_hours (factory.json speed + 6 s per trim + 4 s per colour change), one hooping.", "G4")
    hd = ["Element", "Piece", "Art box", "Stitches", "Trims", "Trims/10k", "Stops", "Threads", "Max stitch", "Run time", "Width check (worst fill/satin code)"]
    cx = [12, 40, 82, 102, 120, 133, 150, 162, 176, 194, 212]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.7, 700, MUTED))
    for i, p in enumerate(PS):
        r = CUR[p]; b = BB[p]; y = 36 + i*4.6; el = EL_OF[p]
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3)}" width="{SW-22}" height="4.6" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, f"{el} {kbcore.ELEMS[el][0]}", 1.8, 600)); o.append(t(cx[1], y, f"{p} {kbcore.PIECE_NAME[p]}", 1.7))
        o.append(t(cx[2], y, f"{b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}", 1.8)); o.append(t(cx[3], y, f"{r['stitches']:,}", 1.8, 600))
        o.append(t(cx[4], y, f"{r['trims']:,}", 1.8)); o.append(t(cx[5], y, f"{r['trims']/r['stitches']*1e4:.0f}", 1.8))
        o.append(t(cx[6], y, f"{r['stops']}", 1.8)); o.append(t(cx[7], y, f"{len(set(r['colours']))}", 1.8))
        o.append(t(cx[8], y, f"{r['max_stitch']:.2f} mm", 1.8)); o.append(t(cx[9], y, f"{mh(r)*60:.0f} min", 1.8))
        wc = {k: v for k, v in SUMS[el]["width"].items() if k not in ("KO-ray", "LF-vein")}; wk = max(wc, key=wc.get)
        o.append(t(cx[10], y, ("all < 1 %" if wc[wk] < 1 else f"{wk} {wc[wk]:.1f}% (tapered tips)"), 1.6, 600, GREEN if wc[wk] < 1 else ORANGE))
    y = 36 + len(PS)*4.6 + 1
    o.append(t(cx[2], y, "TOTAL", 1.9, 700)); o.append(t(cx[3], y, f"{TOT:,}", 1.9, 700)); o.append(t(cx[4], y, f"{TRIMS:,}", 1.9, 700)); o.append(t(cx[9], y, f"{MH:.1f} h", 1.9, 700))
    o.append(t(12, y + 4.5, f"Split files ({HOOPS} hoopings per jacket): {MH_SPLIT:.1f} h per jacket. Width check = share of a code's area below its minimum width (satin 0.8, run 0.6). Fin/tail rays + leaf midribs are single-run lines by design.", 1.65, 400, MUTED))
    o.append(t(12, y + 7.8, f"{REV} is built for fidelity (LESSONS A11): trims, stops and run time are reported, not limited — clean-up after the strike-off.", 1.65, 400, MUTED))
    qy = y + 15
    o.append(t(12, qy, "OPEN QUESTIONS — confirm before sampling", 2.6, 700))
    qs = [f"1. Frame: on {FR_S} the taller pieces need 2 hoopings (split S1/S2 with registration crosses, G5/G6); a larger / jacket frame removes the joins — which frames do you have?",
          "2. Thread board: all 12 targets are read from a low-res AI mockup — approve physical colours (G3), especially the 6 blues against the washed navy shell.",
          "3. Shell: assumed washed navy 12 oz duck, piece-dyed and pre-washed before embroidery. If the jacket is garment-washed after embroidery, wash-test the sew-out.",
          "4. Back, hood and the back half of the sleeves: the mockup shows the front only — assumed plain. Confirm (or send a back / hood mockup).",
          "5. Hem band + cuffs: the mockup flowers run over the band / cuff seams; the art stops 10 above them (band + cuffs not embroidered). OK, or embroider the band?",
          f"6. Grading: A 92 % (XS–S) · B 100 % (M–XL) · C 108 % (XXL–3XL). L + XL sew the M art at 100 % (FR {ALL['L']['FR']['full']['stitches']:,} / {ALL['XL']['FR']['full']['stitches']:,} st vs M {ALL['M']['FR']['full']['stitches']:,}) — OK, or scale L/XL (e.g. 104 %)?",
          "6b. Zip: the mockup lilies touch the zip; the art keeps 15 off CF on both fronts (FR hem lily moved ~15 mm). OK?",
          "7. Hood pattern: the hooded Drum Island variant is not drafted yet — pattern + garment pages (T*) follow; placements here use the Drum Island body.",
          "8. Welt pockets: at the mockup position and angle (60°), Drum Island welt size 1.4 × 13. Confirm before the art is frozen.",
          "9. Reference: lilies traced from ONE AI close-up (FR upper); FL, the FR hem lily and the sleeves are redrawn from the low-res mockup with those templates. Fish = tetras from the founder's reference_fish.png (one reference image; sizes + headings from the mockup).",
          "9b. Product name: shown as 'Blossom Tetra' now that the fish are not koi (slug + style code HK-HD-KOIB-NV kept). Confirm the name.",
          "10. DST/PES are production-intent drafts: the factory digitizer checks density + pull on the shell and edits before the strike-off."]
    for i, q in enumerate(qs): o.append(t(12, qy + 5 + i*3.6, q, 1.75))
    return o

def files_page():
    o = hdr("PRODUCTION STITCH FILES + HOOP SPLITS", "DST (Tajima) + PES, one set per size per piece. Counts read back from the files; trims counted from the DST. Origin = centre of each file's design.", "G5")
    hd = ["Size", "Art", "Piece", "Full file mm", "Stitches", "Trims", "Stops", "S1 top: st / trims / mm", "S2 bottom: st / trims / mm", "Fits"]
    cx = [12, 21, 28, 38, 58, 73, 83, 93, 140, 188]
    for x_, h in zip(cx, hd): o.append(t(x_, 31, h, 1.5, 700, MUTED))
    y = 34.5; allfit = True
    for i, sz in enumerate(kbcore.SIZES):
        for p in PS:
            r = ALL.get(sz, {}).get(p)
            if (i % 2 == 0): o.append(f'<rect x="11" y="{f(y-2.3)}" width="188" height="3.05" fill="#F5F2EC"/>')
            o.append(t(cx[0], y, sz if p == "FR" else "", 1.45, 700)); o.append(t(cx[1], y, kbcore.GRADE[sz][0] if p == "FR" else "", 1.45, 700, RED)); o.append(t(cx[2], y, p, 1.45, 600))
            if r and "full" in r:
                fu = r["full"]
                o.append(t(cx[3], y, f"{fu['size_mm'][0]:.0f} × {fu['size_mm'][1]:.0f}", 1.4)); o.append(t(cx[4], y, f"{fu['stitches']:,}", 1.4)); o.append(t(cx[5], y, f"{fu['trims']}", 1.4)); o.append(t(cx[6], y, f"{fu['stops']}", 1.4))
                secs = r.get("splits", {}).get("sections", {})
                for j, nm in enumerate(("S1_top", "S2_bottom")):
                    s_ = secs.get(nm)
                    if s_: o.append(t(cx[7 + j], y, f"{s_['stitches']:,} / {s_['trims']} / {s_['size_mm'][0]:.0f}×{s_['size_mm'][1]:.0f}", 1.4))
                fits = bool(secs) and all(v["fits"] for v in secs.values()); allfit &= fits
                o.append(t(cx[9], y, "yes" if fits else "CHECK", 1.4, 700, GREEN if fits else RED))
            else:
                o.append(t(cx[3], y, "pending", 1.4, 400, MUTED)); allfit = False
            y += 3.05
    y += 2.5
    notes = [("Order", "per piece: stems → leaves (dark tones first) → lilies (petal tones dark → light → throat → stamen lines → anthers) → petals → fish (tail + fins → body facets → cyan line + red stripe → pectoral fin → eye ring → eye)."),
             ("Ties", f"3-stitch tie-on/off at every trim + colour change; max sewn stitch ≤ 7.5 mm; ≤ {FA.max_threads(PROF)} thread colours per file (registration in stop 1's thread).")]
    for a, b_ in notes:
        o.append(t(12, y, a, 1.5, 700)); o.append(t(24, y, b_, 1.4)); y += 3.1
    sp = CUR["FR"].get("splits") or {}
    bx, by, bw = 214, 31, 70; b0 = BB["FR"]
    img = SR.render(V["FR"], (b0[0]-14, b0[1]-14, b0[2]+14, b0[3]+14), 1.6, base=kbcore.FABRIC)
    tag, bh = img_tag(img, bx, by, bw); o.append(tag)
    s_ = bw / (b0[2] - b0[0] + 28); X = lambda x: bx + (x - b0[0] + 14)*s_; Y = lambda y_: by + (y_ - b0[1] + 14)*s_
    if sp.get("sy") is not None:
        o.append(f'<line x1="{f(X(b0[0]-12))}" y1="{f(Y(sp["sy"]))}" x2="{f(X(b0[2]+12))}" y2="{f(Y(sp["sy"]))}" stroke="{RED}" stroke-width="0.35" stroke-dasharray="1.5 0.8"/>')
    for nm, sx_ in sp.get("sections", {}).items():
        bb = sx_["bbox"]
        o.append(f'<rect x="{f(X(bb[0]))}" y="{f(Y(bb[1]))}" width="{f((bb[2]-bb[0])*s_)}" height="{f((bb[3]-bb[1])*s_)}" fill="none" stroke="#0A84FF" stroke-width="0.25"/>')
        o.append(t(X(bb[0]) + 1, Y(bb[1]) + 3, nm[:2], 2.0, 700, "#0A84FF"))
        for m in sx_["marks"]:
            mx, my = X(m[0]), Y(m[1]); o.append(f'<path d="M{f(mx-1.4)} {f(my)} H{f(mx+1.4)} M{f(mx)} {f(my-1.4)} V{f(my+1.4)}" stroke="#00E0FF" stroke-width="0.45"/>')
    o.append(t(bx, by + bh + 3, f"FR size M: red = split line (y {sp.get('sy', 0):.0f}), blue = files, + = registration crosses.", 1.4, 400, MUTED))
    sy0 = by + bh + 8
    o.append(t(bx, sy0, "SEWING A SPLIT PIECE", 2.0, 700))
    steps = ["1. Mark CF / sleeve centre + split line on the", "    cut panel (chalk) from the pattern.",
             "2. Hoop S1 (top). Stop 1 starts with the", "    registration crosses (stop-1 thread). Sew S1.",
             "3. Re-hoop for S2; align the needle on the", "    shared crosses, sew them (check), then S2.",
             "4. Motifs < 70 go whole to one file; larger", "    fills overlap 1.2 across the split.",
             "5. Pick out the crosses, trim backing after S2.", f"Fits the frame on every size: {'yes' if allfit else 'CHECK'}."]
    for i, st_ in enumerate(steps): o.append(t(bx, sy0 + 4 + i*3.0, st_, 1.45, 700 if i == len(steps) - 1 else 400, (GREEN if allfit else RED) if i == len(steps) - 1 else INK))
    return o

def split_cut(sz, P):
    """mm of motif outline the split line crosses (joints the strike-off must check)"""
    from shapely.geometry import LineString
    sp = ALL[sz][P]["splits"]; sy = sp.get("sy")
    if sy is None or len(sp["sections"]) < 2: return 0.0
    D_ = pickle.load(open(f"art_{sz}.pkl", "rb"))
    u = unary_union([r["geom"] for r in D_[P]])
    return u.intersection(LineString([(-600, sy), (600, sy)])).length

def hooping_page():
    o = hdr("HOOPING TABLE — split line + needle start per file, every size", f"Frame {FR_S} mm (factory.json{'' if PROF['frames_confirmed'] else ', PROPOSED'}). Piece coords in mm (fronts: x from CF, y from the CF neck; sleeves: x from the sleeve centre line, y from the underarm line). DXF layer 13 = these points.", "G6")
    hd = ["Size", "Piece", "Split y", "S1 needle start", "S1 mm", "S2 needle start", "S2 mm", "Full-file start", "Art on split line", "Fit", "h / piece (split)", "Trims S1+S2"]
    cx = [12, 22, 32, 46, 76, 96, 126, 146, 176, 204, 216, 244]
    for x_, h in zip(cx, hd): o.append(t(x_, 31, h, 1.45, 700, MUTED))
    y = 35
    for i, sz in enumerate(kbcore.SIZES):
        for P in PS:
            r = ALL[sz][P]; sp = r["splits"]; secs = sp["sections"]
            if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.2)}" width="{SW-22}" height="3.05" fill="#F5F2EC"/>')
            o.append(t(cx[0], y, sz if P == "FR" else "", 1.4, 700)); o.append(t(cx[1], y, P, 1.4, 600))
            o.append(t(cx[2], y, f"{sp['sy']:.1f}" if (sp.get("sy") is not None and len(secs) > 1) else "1 hooping", 1.4, 700, RED))
            for j, nm in enumerate(("S1_top", "S2_bottom")):
                s_ = secs.get(nm)
                if s_:
                    o.append(t(cx[3 + 2*j], y, f"({s_['origin'][0]:+.1f}, {s_['origin'][1]:.1f})", 1.35)); o.append(t(cx[4 + 2*j], y, f"{s_['size_mm'][0]:.0f} × {s_['size_mm'][1]:.0f}", 1.35))
            fo = r["full"]["origin"]; o.append(t(cx[7], y, f"({fo[0]:+.1f}, {fo[1]:.1f})", 1.35))
            cc = split_cut(sz, P)
            o.append(t(cx[8], y, f"{cc:.0f} mm" + (" — check joint" if cc > 1 else ""), 1.35, 600 if cc > 1 else 400, ORANGE if cc > 1 else INK))
            ok = all(v["fits"] for v in secs.values()); o.append(t(cx[9], y, "yes" if ok else "NO", 1.4, 700, GREEN if ok else RED))
            o.append(t(cx[10], y, f"{sum(mh(v) for v in secs.values()):.2f}", 1.35)); o.append(t(cx[11], y, f"{sum(v['trims'] for v in secs.values())}", 1.35))
            y += 3.05
    y += 2.5
    notes = ["The split line is chosen where it cuts the least art inside the frame (searched 12–88 % of the art height). Motifs under 70 mm (fish, petals, leaves)",
             "go whole to one file; larger fills that still cross it overlap 1.2 mm (amber) — check that joint on the strike-off photos.",
             "Needle start = centre of each file's design (origin of the DST/PES). Mark it on the cut panel from the pattern (DXF layer 13 + layer 8 cross).",
             "Registration crosses sew at the start of stop 1 in that stop's thread (max 12 colours per file); S2 re-registers on the crosses S1 sewed; pick out after S2.",
             "h / piece = machine hours of both split files (factory.machine_hours incl. trims + colour changes), + 2 hoopings."]
    for i, l in enumerate(notes): o.append(t(12, y + i*3.2, l, 1.5, 400, MUTED))
    return o

def f1_pages():
    import sheet as _SH; _SH.FOOT = SB.FOOT
    so = [dict(file=os.path.basename(CUR[p]["file"]) + ".dst", piece=f"{p} {kbcore.PIECE_NAME[p]}", stitches=CUR[p]["stitches"], trims=CUR[p]["trims"]) for p in PS]
    so += [dict(file=os.path.basename(s["file"]) + ".dst", piece=f"{p} split {nm}", stitches=s["stitches"], trims=s["trims"]) for p in PS for nm, s in CUR[p]["splits"]["sections"].items()]
    th = [dict(name=PAL[k][1], code=f"Isacord {SB.TH[k]['isacord'][0]} / Polyneon {SB.TH[k]['polyneon'][0]}", de=min(SB.TH[k]["isacord"][3], SB.TH[k]["polyneon"][3])) for k in kbcore.KB_KEYS]
    pcs = [dict(piece=f"{EL_OF[p]} {p}", w=CUR[p]["size_mm"][0], h=CUR[p]["size_mm"][1], hoopings=len(CUR[p]["splits"]["sections"])) for p in PS]
    return FA.requests_page(kbcore.NAME, so, th, pcs, page="F1", prof=PROF)

def build():
    pages = {"G1": None, "G2": overview(), "G3": threads(), "G4": summary(), "G5": files_page(), "G6": hooping_page()}
    index = [("G1 Cover + contents", 1), ("G2 Placement overview + keep-outs", 2), ("G3 Thread + trim summary", 3), ("G4 Stitch summary + open questions", 4),
             ("G5 Production stitch files + hoop splits", 5), ("G6 Hooping table (split lines, needle starts)", 6)]
    pg = 7
    for el in kbcore.ELEMS:
        n = len(PdfReader(SPEC[el]).pages); index.append((f"{el} {kbcore.ELEMS[el][1].split(' — ')[0].title()} (element spec, {n} pp)", pg)); pg += n
    index.append(("F1 Factory requests", pg))
    pages["G1"] = cover(index)
    w = PdfWriter()
    for k in ("G1", "G2", "G3", "G4", "G5", "G6"):
        svg = doc(pages[k]); cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"out/{k}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"out/prev_{k}.png", output_width=2400)
        w.append(PdfReader(f"out/{k}.pdf"))
    for el in kbcore.ELEMS: w.append(PdfReader(SPEC[el]))
    for i, svg in enumerate(f1_pages()):
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"out/F{i+1}.pdf"); cairosvg.svg2png(bytestring=svg.encode(), write_to=f"out/prev_F{i+1}.png", output_width=2400)
        w.append(PdfReader(f"out/F{i+1}.pdf"))
    w.write(OUT_PDF)
    print("pages", pg, OUT_PDF)
    return index

if __name__ == "__main__":
    build()
