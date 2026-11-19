"""Embroidery pack G1-G6 + F1 for the Comet City hoodie (01 front scene FR + FL, 02 sleeves SR + SL).
Every count comes from the stitch files (dst_current.json / dst_all.json = readback.dst of the written DSTs)."""
import cccore
import json
import os, json, pickle, glob
import cairosvg
from PIL import Image, ImageDraw
from shapely.ops import unary_union
from shapely.geometry import LineString
from pypdf import PdfWriter, PdfReader
from sheet import t, swatch, doc, INK, MUTED, RED, ORANGE, GUIDE, GREEN, SW, SH
from render import f
import labelsheet as LS
from motifs2 import HEX, PAL
import tech, stitchrender as SR
import specbase as SB
from specbase import img_tag
import front as F, espec, emb_place as EP, factory as FA
PROF = FA.load(); FRAME = FA.largest_frame(PROF); FR_S = f"{FRAME[0]:.0f} × {FRAME[1]:.0f}"
def mh(r): return FA.machine_hours(r["stitches"], PROF, trims=r["trims"], colour_changes=r["stops"] - 1)
dst2 = cccore.patch_dst2()

REV, DATE = cccore.REV_EMB, cccore.DATE
SB.FOOT = f"HAKI STUDIOS · {cccore.NAME} · EMBROIDERY · {REV} · {DATE}"
D = pickle.load(open("art_M.pkl", "rb")); V = {p: D[p] for p in cccore.PIECES}
CUR = json.load(open("dst_current.json")); ALL = json.load(open("dst_all.json")); META = json.load(open("scene_meta.json"))
P4 = cccore.PIECES
BB = {p: unary_union([r["geom"] for r in V[p]]).bounds for p in P4}
OUT_PDF = f"out/HAKI_{cccore.SHORT}_EMBROIDERY-PACK_{REV.replace(' ', '')}.pdf"
SPEC = {e: (glob.glob(f"out/{e}_{cccore.ELEMS[e][0]}/*SPEC_*.pdf") or [None])[0] for e in cccore.ELEMS}
def hdr(title, sub, page): return SB.header(title, sub, page)
TOT = sum(CUR[p]["stitches"] for p in P4); TRIMS = sum(CUR[p]["trims"] for p in P4)
MH = sum(mh(CUR[p]) for p in P4)
MH_SPLIT = sum(mh(s) for p in P4 for s in CUR[p]["splits"]["sections"].values())
HOOPS = sum(len(CUR[p]["splits"]["sections"]) or 1 for p in P4)
ELN = {"01": "01 Front scene", "02": "02 Sleeves"}
USED = sorted({c for p in P4 for c in CUR[p]["colours"]}, key=cccore.CC_ORDER.index)
SPLIT_NAMES = ("S1_top", "S2_bottom")

def sleeves_png(ppm=2.0):
    import run_spec
    return run_spec.sleeve_view(V)[0]

def cover(index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>']
    o.append(t(14, 24, "HAKI STUDIOS", 3.0, 700, MUTED))
    o.append(t(14, 36, "Comet City hooded jacket · washed navy — embroidery", 7.0, 700))
    o.append(t(14, 44, f"{REV} · {DATE} · Drum Island body + hood, size M base · 2 elements (01 front scene, 02 sleeves), 4 pieces · {len(USED)} threads · all dimensions mm", 2.6, 400, MUTED))
    o.append(f'<line x1="14" y1="48" x2="{SW-14}" y2="48" stroke="{INK}" stroke-width="0.4"/>')
    fv = espec.front_view_png(F, {p: V[p] for p in cccore.FRONTS}, (-325, -105, 325, 560), 2.2, list(cccore.FRONTS))
    tag, h = img_tag(fv, 14, 54, 100); o.append(tag)
    sv = sleeves_png(); tag2, h2 = img_tag(sv, 118, 54, 76); o.append(tag2)
    o.append(t(14, 54 + max(h, h2) + 3.5, "FRONT + both SLEEVES (size M stitch render). Back + hood: no embroidery [proposed — confirm].", 2.2, 700))
    ix = 202
    o.append(t(ix, 58, "CONTENTS", 2.8, 700)); y = 64
    for name, pg in index:
        o.append(t(ix, y, name, 2.0)); o.append(t(SW - 14, y, f"{pg}", 2.0, 600, MUTED, "end")); y += 4.1
    y += 4
    o.append(t(ix, y, "TOTALS, SIZE M (read from the DST files)", 2.4, 700)); y += 5
    for a, b in [("Stitches per jacket", f"{TOT:,}"), ("Trims per jacket", f"{TRIMS:,}"),
                 ("Hoopings per jacket", f"{HOOPS} on {FR_S} (split files)"),
                 ("Machine time / jacket", f"{MH_SPLIT:.1f} h split files ({MH:.1f} h full files)"), ("Threads", f"{len(USED)} over the jacket, ≤ {FA.max_threads(PROF)} per file")]:
        o.append(t(ix, y, a, 2.0, 400, MUTED)); o.append(t(SW - 14, y, b, 1.85, 600, INK, "end")); y += 4
    o.append(t(SW - 14, SH - 8, SB.FOOT, 1.9, 400, MUTED, "end"))
    return o

def overview():
    o = hdr("PLACEMENT OVERVIEW — front scene + sleeves on the garment", "Fronts: x from CF (+ = wearer's left), y down from the CF neck seam. Sleeves: x from the sleeve centre line, y down from the underarm line. Tolerance ±2, rotation ±2°.", "G2")
    fv = espec.front_view_png(F, {p: V[p] for p in cccore.FRONTS}, (-325, -105, 325, 560), 2.6, list(cccore.FRONTS))
    w = 118; s = w / 650; ax, ay = 12, 30
    tag, h = img_tag(fv, ax, ay, w); o.append(tag)
    X = lambda x: ax + (x + 325)*s; Y = lambda y: ay + (y + 105)*s
    for p in cccore.FRONTS:
        b = BB[p]
        o.append(f'<rect x="{f(X(b[0]))}" y="{f(Y(b[1]))}" width="{f((b[2]-b[0])*s)}" height="{f((b[3]-b[1])*s)}" fill="none" stroke="{RED}" stroke-width="0.3" stroke-dasharray="1.2 0.8"/>')
        o.append(f'<circle cx="{f(X(b[0]))}" cy="{f(Y(b[1]))}" r="2.6" fill="{RED}"/>' + t(X(b[0]), Y(b[1]) + 0.8, p, 1.6, 700, "#FFFFFF", "middle"))
        sy = CUR[p]["splits"].get("sy")
        if sy is not None:
            o.append(f'<line x1="{f(X(b[0]-6))}" y1="{f(Y(sy))}" x2="{f(X(b[2]+6))}" y2="{f(Y(sy))}" stroke="#0A84FF" stroke-width="0.4" stroke-dasharray="2 1"/>')
    for m in D["info"]["marks"]:
        o.append(f'<circle cx="{f(X(m["x"]))}" cy="{f(Y(m["y"]))}" r="0.8" fill="#00A3FF"/>')
    o.append(t(ax, ay + h + 3.5, "FRONT, size M. Red = art boxes; blue dots = CF match marks; dashed blue = hoop split lines (G6).", 1.75, 700))
    SLV_Y = 128; sv = sleeves_png(); tag2, h2 = img_tag(sv, 140, SLV_Y, 104); o.append(tag2)
    o.append(t(140, SLV_Y + h2 + 3.2, "SLEEVES flat, size M (left sleeve S02 left, right sleeve S01 right): art on the front-facing half.", 1.75, 700))
    tx = 140; ty = 30
    o.append(t(tx, ty, "ART BOX PER SIZE (mm) — fronts x/y from CF/neck, sleeves x/y from centre line/underarm", 2.0, 700))
    hd = ["Size", "Art", "FR x", "FR y", "FL x", "FL y", "SR x", "SR y", "SL x", "SL y"]
    cx = [tx, tx + 9, tx + 16, tx + 32, tx + 48, tx + 64, tx + 80, tx + 96, tx + 112, tx + 128]
    for x_, hh in zip(cx, hd): o.append(t(x_, ty + 5, hh, 1.55, 700, MUTED))
    for i, sz in enumerate(cccore.SIZES):
        pl = EP.place(sz)[0]; y = ty + 9.5 + i*4.0
        if i % 2 == 0: o.append(f'<rect x="{tx-1}" y="{f(y-2.8)}" width="{SW - tx - 11}" height="4" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, sz, 1.6, 700)); o.append(t(cx[1], y, cccore.GRADE[sz][0], 1.6, 700, RED))
        for j, p in enumerate(P4):
            b = pl[p][1].bounds
            o.append(t(cx[2 + 2*j], y, f"{b[0]:+.0f}…{b[2]:+.0f}", 1.45)); o.append(t(cx[3 + 2*j], y, f"{b[1]:.0f}…{b[3]:.0f}", 1.45))
    ky = ty + 9.5 + 7*4.0 + 5
    o.append(t(tx, ky, "KEEP-OUTS (all sizes, measured on the pattern pieces — T7)", 2.1, 700))
    ko = [f"CF zip: {F.KEEP_CF:.0f} each side of CF (teeth + tape + topstitch)", f"Armhole, shoulder, side seams: {F.KEEP_SEAM:.0f} · hem-band seam: {F.KEEP_HEM:.0f}",
          f"Hood neck seam: {F.KEEP_NECK:.0f} [proposed] · welt pocket box: {F.KEEP_WELT:.0f} (6 + 2 cut-out margin) [proposed]",
          f"Sleeves: cap {F.SKEEP['cap']:.0f}, underarm seams {F.SKEEP['underarm front']:.0f}, cuff seam {F.SKEEP['cuff']:.0f}; art on the front half + {F.SLEEVE_BACK_REACH:.0f} past the centre line",
          "Back + hood: no embroidery [proposed — confirm]."]
    for i, k in enumerate(ko): o.append(t(tx, ky + 4.4 + i*3.4, k, 1.7))
    my = ky + 4.4 + 5*3.4 + 4
    o.append(t(tx, my, "MATCHING ACROSS THE ZIP (size M marks; every size scales about the CF neck)", 2.1, 700))
    for i, m in enumerate(D["info"]["marks"]):
        o.append(t(tx + (i % 2)*64, my + 4.2 + (i // 2)*3.2, f"{m['name']}: x {m['x']:+.0f}, y {m['y']:.1f}", 1.65))
    yy = my + 4.2 + ((len(D["info"]["marks"]) + 1)//2)*3.2 + 2
    for i, l in enumerate(["Hoop to the marked CF + top rail line; after the zip is set the comet, the top rail and the kerb must read",
                           "as one line (±1 mm). The sleeves are independent (no wrap across the armhole)."]):
        o.append(t(tx, yy + i*3.2, l, 1.65))
    return o

def threads():
    o = hdr("THREAD + TRIM SUMMARY", f"One palette for the whole jacket — {len(USED)} threads, ≤ {FA.max_threads(PROF)} per file (factory.json). Approve a physical thread board before sampling; hex = on-screen target.", "G3")
    use = {k: {} for k in USED}
    for p in P4:
        for c in CUR[p]["colours"]: use[c][p] = use[c].get(p, 0) + 1
    hd = ["", "Thread", "Hex", "Isacord", "ΔE", "Madeira Polyneon", "ΔE", "Wt", "Used for", "Stops FR / FL / SR / SL"]
    cx = [12, 18, 42, 56, 86, 94, 128, 136, 144, 232]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.75, 700, MUTED))
    TH = SB.TH; rh = 4.8
    for i, k in enumerate(USED):
        y = 36 + i*rh
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3.2)}" width="{SW-22}" height="{f(rh)}" fill="#F5F2EC"/>')
        iso, pn = TH[k]["isacord"], TH[k]["polyneon"]
        ci = GREEN if iso[3] < 3 else (ORANGE if iso[3] < 5.5 else RED); cp = GREEN if pn[3] < 3 else (ORANGE if pn[3] < 5.5 else RED)
        o.append(swatch(cx[0], y, k, 4.5, 2.8)); o.append(t(cx[1], y, PAL[k][1], 1.85, 600)); o.append(t(cx[2], y, HEX[k], 1.7, 400, MUTED))
        o.append(t(cx[3], y, f"{iso[0]} {iso[1]}"[:22], 1.7)); o.append(t(cx[4], y, f"{iso[3]:.1f}", 1.7, 600, ci))
        o.append(t(cx[5], y, f"{pn[0]} {pn[1]}"[:24], 1.7)); o.append(t(cx[6], y, f"{pn[3]:.1f}", 1.7, 600, cp))
        o.append(t(cx[7], y, "40", 1.7)); o.append(t(cx[8], y, PAL[k][2][:62], 1.6, 400, MUTED))
        o.append(t(cx[9], y, " / ".join(str(use[k].get(p, 0)) for p in P4), 1.7, 600))
    yb = 36 + len(USED)*rh + 3
    o.append(t(12, yb, "ΔE2000 vs target: green < 3, amber 3–5.5, red > 5.5 — amber/red rows must be picked from the physical card. All targets are PROPOSED (read from the mockup).", 1.75, 600, ORANGE))
    per = " · ".join(f"{p} {CUR[p]['threads']}" for p in P4)
    o.append(t(12, yb + 3.6, f"Distinct thread colours per file (PES read-back, size M): {per} — limit {FA.max_threads(PROF)} incl. registration (crosses sew in stop 1's thread).", 1.75, 600))
    o.append(t(12, yb + 9, "TRIMS + CONSUMABLES (per jacket)", 2.2, 700))
    tr = [("Backing", "2.5 oz cutaway, black/charcoal (navy shell), cut 30 larger than each hooping; trim to 5 from stitching after embroidery"),
          ("Topping", "none (washed duck surface is firm)"), ("Needles", "75/11 sharp"), ("Bobbin", "60wt black or navy polyester pre-wound (dark shell)"),
          ("Frames", f"{FR_S} (factory.json{'' if PROF['frames_confirmed'] else ', PROPOSED'}): {HOOPS} hoopings per jacket (split files, G5/G6)"),
          ("Patches / labels", LS.pack_patches_row(os.path.dirname(os.path.abspath(__file__))))]
    for i, (a, b) in enumerate(tr):
        o.append(t(12, yb + 13.5 + i*3.6, a, 1.85, 600)); o.append(t(42, yb + 13.5 + i*3.6, b, 1.85, 400, LS.AMBER if LS.flagged(b) else INK))
    return o

def summary():
    o = hdr("STITCH SUMMARY + OPEN QUESTIONS", "Size M files. Every count read back from the DST (stitches, trims, stops, max stitch).", "G4")
    hd = ["Element", "Piece", "Art box", "Stitches", "Trims", "Trims/10k", "Stops", "Threads", "Max stitch", "Run time (full)", "Run time (splits)"]
    cx = [12, 40, 84, 104, 122, 136, 152, 164, 178, 196, 222]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.75, 700, MUTED))
    for i, p in enumerate(P4):
        r = CUR[p]; b = BB[p]; y = 36 + i*4.6
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3)}" width="{SW-22}" height="4.6" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, ELN[cccore.ELEM_OF[p]], 1.8, 600)); o.append(t(cx[1], y, f"{p} {cccore.PIECE_NAME[p]}", 1.7))
        o.append(t(cx[2], y, f"{b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}", 1.75)); o.append(t(cx[3], y, f"{r['stitches']:,}", 1.75, 600))
        o.append(t(cx[4], y, f"{r['trims']:,}", 1.75)); o.append(t(cx[5], y, f"{r['trims']/max(r['stitches'],1)*1e4:.1f}", 1.75))
        o.append(t(cx[6], y, f"{r['stops']}", 1.75)); o.append(t(cx[7], y, f"{r['threads']}", 1.75))
        o.append(t(cx[8], y, f"{r['max_stitch']:.2f} mm", 1.75, 600, GREEN if r['max_stitch'] <= 7.5 else RED)); o.append(t(cx[9], y, f"{mh(r):.2f} h", 1.75))
        o.append(t(cx[10], y, f"{sum(mh(s) for s in r['splits']['sections'].values()):.2f} h ({len(r['splits']['sections'])} hoopings)", 1.75))
    y = 36 + len(P4)*4.6 + 1
    o.append(t(cx[2], y, "TOTAL", 1.9, 700)); o.append(t(cx[3], y, f"{TOT:,}", 1.9, 700)); o.append(t(cx[4], y, f"{TRIMS:,}", 1.9, 700))
    o.append(t(cx[9], y, f"{MH:.1f} h", 1.9, 700)); o.append(t(cx[10], y, f"{MH_SPLIT:.1f} h", 1.9, 700))
    o.append(t(12, y + 4.5, f"Run time = factory.machine_hours: {PROF['spm']} spm + 6 s per trim + 4 s per colour change, one head, per hooping, excl. hooping time. Rev B is built for fidelity (LESSONS A11):", 1.65, 400, MUTED))
    o.append(t(12, y + 7.6, "stitches, trims and run time are reported, not limited — density / trim clean-up happens after the size-M strike-off.", 1.65, 400, MUTED))
    qy = y + 15
    o.append(t(12, qy, "OPEN QUESTIONS — confirm before sampling", 2.6, 700))
    qs = [f"1. IP: the comet-over-city-with-figure scene evokes the film 'Your Name' (CoMix Wave). We drew our own skyline, comet bundle and figure pose — founder to decide.",
          f"2. Frame: every piece needs 2 hoopings on {FR_S} (split S1/S2 with registration crosses, G5/G6). A larger frame removes the joins — what frames does the factory have?",
          "3. Back + hood: the mockup shows only the front; plain back and hood assumed. Sleeves: art on the front-facing half only, back half plain. Confirm.",
          "4. Hood block: CLOSED 19 Oct — zip-hoodie block (engine/hoodie.py, elastic hem + cuff bands), founder decision. Welt position = engine welt override [proposed].",
          "5. Thread board: all targets are read from a low-res AI mockup — approve physical colours (G3), esp. the comet blues/violets and window gold on navy.",
          "6. Grading: A 92% (XS–S) · B 100% (M–XL) · C 108% (XXL–3XL), one file per size per piece; fronts scale about the CF neck so the comet + rail meet at the zip.",
          "7. Welts: at the mockup position (centre 21.8 cm from CF, 35.2 cm below the neck, 54°), Drum Island welt 1.4 × 13. Confirm.",
          "8. References: the comet is traced from the founder's close-up (registered on the fronts); clouds/placement from the mockup; per-panel close-ups would still sharpen city + sleeves.",
          "9. DST/PES are production-intent drafts: the factory digitizer checks density + pull on the washed duck and edits before the sew-out."]
    for i, q in enumerate(qs): o.append(t(12, qy + 5 + i*3.6, q, 1.75))
    # fidelity gates (LESSONS A14 / A15) on the shipped size-M DSTs - fidelity.json (tables on out/compare_<piece>.png)
    fy = qy + 5 + len(qs)*3.6 + 6
    FD = json.load(open("fidelity.json"))
    ok = not (FD["failing_motifs"] or FD["unexplained"])
    o.append(t(12, fy, f"FIDELITY GATES (LESSONS A14 / A15) — {FD['mode']}, size M: " + ("PASS" if ok else "BLOCKED"), 2.6, 700, GREEN if ok else RED))
    fy += 5
    from collections import Counter
    for grp in ("fronts", "sleeves"):
        for P, d in FD[grp].items():
            fam = "  ·  ".join(f"{k} {sum(r['ok'] for r in v)}/{len(v)} traced motifs match" for k, v in d.items() if k in ("clouds", "comet"))
            why = Counter(g["why"].split(":")[0] for g in d["gaps"])
            o.append(t(12, fy, f"{P}: {fam}  ·  uncovered gaps >= 25 mm²: {len(d['gaps'])} (" + ", ".join(f"{n} {k}" for k, n in why.items()) + ")", 1.7)); fy += 3.6
    o.append(t(12, fy + 1, "motif_match: IoU >= 0.70 and width/height >= 80 % per traced motif. uncovered: mockup design area (garment details masked: zip, welts, seams) not stitched; every gap explained.", 1.6, 400, MUTED))
    o.append(t(12, fy + 4.2, "Generated, not traced: skyline + figure (original on purpose, IP), lamp, bicycle, railing, bush, star shapes, comet strand texture, sleeve leaves (see element specs p5).", 1.6, 400, MUTED))
    return o

def files_page():
    o = hdr("PRODUCTION STITCH FILES + HOOP SPLITS", "DST (Tajima) + PES, one set per size per piece. Counts read back from the DST files. Origin = centre of each file's design ((+) on the pattern, G6).", "G5")
    hd = ["Size", "Art", "Piece", "Full file mm", "Stitches", "Trims", "Stops", "S1 top: st / trims / mm", "S2 bottom: st / trims / mm", "Fits"]
    cx = [12, 22, 30, 40, 62, 78, 90, 102, 148, 194]
    for x_, h in zip(cx, hd): o.append(t(x_, 31, h, 1.5, 700, MUTED))
    y = 35; allfit = True
    for i, sz in enumerate(cccore.SIZES):
        for p in P4:
            r = ALL.get(sz, {}).get(p)
            if (i % 2 == 0): o.append(f'<rect x="11" y="{f(y-2.4)}" width="196" height="3.2" fill="#F5F2EC"/>')
            o.append(t(cx[0], y, sz if p == "FR" else "", 1.45, 700)); o.append(t(cx[1], y, cccore.GRADE[sz][0] if p == "FR" else "", 1.45, 700, RED)); o.append(t(cx[2], y, p, 1.45, 600))
            if r and "full" in r:
                fu = r["full"]
                o.append(t(cx[3], y, f"{fu['size_mm'][0]:.0f} × {fu['size_mm'][1]:.0f}", 1.42)); o.append(t(cx[4], y, f"{fu['stitches']:,}", 1.42)); o.append(t(cx[5], y, f"{fu['trims']}", 1.42)); o.append(t(cx[6], y, f"{fu['stops']}", 1.42))
                secs = r.get("splits", {}).get("sections", {})
                for j, nm in enumerate(SPLIT_NAMES):
                    s_ = secs.get(nm)
                    if s_: o.append(t(cx[7 + j], y, f"{s_['stitches']:,} / {s_['trims']} / {s_['size_mm'][0]:.0f}×{s_['size_mm'][1]:.0f}", 1.42))
                fits = bool(secs) and all(v["fits"] for v in secs.values()); allfit &= fits
                o.append(t(cx[9], y, "yes" if fits else "CHECK", 1.42, 700, GREEN if fits else RED))
            else:
                o.append(t(cx[3], y, "pending", 1.42, 400, MUTED)); allfit = False
            y += 3.2
    y += 2.5
    o.append(t(12, y, "WHAT IS DIGITIZED", 1.9, 700)); y += 3.8
    notes = [("City", "lit windows (satin blocks, 4 colours) sewn first; far blocks (dusk) and near blocks (night, vertical tatami) sew around them and hide the travel."),
             ("Comet", "tapered turning-satin strands (royal / azure / violet / lilac) + white core; the clouds in front of it sew later and knock it out."),
             ("Clouds", "the mockup's 3 tone areas (dusk → cloud → ice) as short-row tatami 0° / 8°; tones abut, no fabric gaps inside a cloud."),
             ("Lines", "railing (satin rails + balusters), bicycle (bean frame, satin tyres), figure folds: sewn last, on top (no knockout)."),
             ("Sleeves", "palm fronds = two-tone satin leaflets on a satin rib; fireflies = satin dots; ≤ 7.5 mm stitches, 3-stitch ties at every trim.")]
    for a, b_ in notes:
        o.append(t(12, y, a, 1.5, 700)); o.append(t(28, y, b_, 1.42)); y += 3.1
    sp = CUR["FL"].get("splits") or {}
    bx, by, bw = 214, 31, 70; b0 = BB["FL"]
    img = SR.render(V["FL"], (b0[0]-14, b0[1]-14, b0[2]+14, b0[3]+14), 1.6, base=cccore.FABRIC)
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
    o.append(t(bx, by + bh + 3, f"FL size M: red = split line (y {sp.get('sy') or 0:.0f}), blue = files, + = registration crosses.", 1.4, 400, MUTED))
    sy0 = by + bh + 8
    o.append(t(bx, sy0, "SEWING A SPLIT PIECE", 2.0, 700))
    steps = ["1. Mark CF / centre line + split line on the", "    cut panel (chalk) from the pattern.",
             "2. Hoop S1 (top). Stop 1 opens with the", "    registration crosses (stop-1 thread). Sew S1.",
             "3. Re-hoop for S2; align the needle on the", "    shared crosses, sew them (check), then S2.",
             "4. Fills crossing the split overlap 1.2;", "    stars, plants, windows < 70 go whole to one file.",
             "5. Pick out the crosses, trim backing after S2.", f"Fits the frame on every size: {'yes' if allfit else 'CHECK'}."]
    for i, st_ in enumerate(steps): o.append(t(bx, sy0 + 4 + i*3.0, st_, 1.45, 700 if i == len(steps) - 1 else 400, (GREEN if allfit else RED) if i == len(steps) - 1 else INK))
    return o

def split_cut(sz, P):
    """mm of fill outline (clouds, buildings, comet, leaves) the split line crosses — a joint the strike-off must check"""
    sp = ALL[sz][P]["splits"]; sy = sp.get("sy")
    if sy is None: return 0.0
    D_ = pickle.load(open(f"art_{sz}.pkl", "rb"))
    u = unary_union([r["geom"] for r in D_[P] if r["grp"].startswith(("CL", "BLD", "COM", "LF"))])
    return u.intersection(LineString([(-400, sy), (400, sy)])).length

def hooping_page():
    o = hdr("HOOPING TABLE — split line + needle start per file, every size", f"Frame {FR_S} mm (factory.json{'' if PROF['frames_confirmed'] else ', PROPOSED'}). Fronts: x from CF, y down from the CF neck; sleeves: x from the centre line, y down from the underarm line. DXF layer 13 = these points.", "G6")
    hd = ["Size", "Piece", "Split y", "S1 needle start (x, y)", "S1 file mm", "S2 needle start (x, y)", "S2 file mm", "Full file start", "Fill crossed by split", "Hours (S1+S2)", "Fit"]
    cx = [12, 22, 32, 46, 80, 100, 134, 154, 182, 218, 246]
    for x_, h in zip(cx, hd): o.append(t(x_, 31, h, 1.5, 700, MUTED))
    y = 35.5
    for i, sz in enumerate(cccore.SIZES):
        for P in P4:
            r = ALL[sz][P]; sp = r["splits"]; secs = sp["sections"]
            if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.4)}" width="{SW-22}" height="3.3" fill="#F5F2EC"/>')
            o.append(t(cx[0], y, sz if P == "FR" else "", 1.45, 700)); o.append(t(cx[1], y, P, 1.45, 600))
            o.append(t(cx[2], y, f"{sp['sy']:.1f}" if sp.get("sy") is not None else "—", 1.45, 700, RED))
            for j, nm in enumerate(SPLIT_NAMES):
                s_ = secs.get(nm)
                if s_:
                    o.append(t(cx[3 + 2*j], y, f"({s_['origin'][0]:+.1f}, {s_['origin'][1]:.1f})", 1.42)); o.append(t(cx[4 + 2*j], y, f"{s_['size_mm'][0]:.0f} × {s_['size_mm'][1]:.0f}", 1.42))
            fo = r["full"]["origin"]; o.append(t(cx[7], y, f"({fo[0]:+.1f}, {fo[1]:.1f})", 1.42))
            cc = split_cut(sz, P)
            o.append(t(cx[8], y, f"{cc:.0f} mm" + (" — check joint" if cc > 1 else ""), 1.42, 600 if cc > 1 else 400, ORANGE if cc > 1 else INK))
            o.append(t(cx[9], y, f"{sum(mh(s) for s in secs.values()):.2f} h", 1.42))
            ok = bool(secs) and all(v["fits"] for v in secs.values()); o.append(t(cx[10], y, "yes" if ok else "NO", 1.42, 700, GREEN if ok else RED))
            y += 3.3
    y += 2.5
    notes = ["The split line is chosen where it cuts the least art inside the frame (searched 12–88 % of the art height). Where it still crosses a fill",
             "(amber), motifs under 70 mm go whole to one file and larger fills overlap 1.2 mm — check that joint on the strike-off photos.",
             "Needle start = centre of each file's design (origin of the DST/PES). Mark it on the cut panel from the pattern (DXF layer 13 + layer 8 cross).",
             f"Registration crosses sew at the start of stop 1 in that stop's thread (factory: max {FA.max_threads(PROF)} colours per file, no separate basting thread);",
             "long stitches on bare fabric 4 mm outside the art — S2 re-registers on the crosses S1 sewed; pick them out after S2."]
    for i, l in enumerate(notes): o.append(t(12, y + i*3.3, l, 1.55, 400, MUTED))
    return o

def f1_pages():
    import sheet as _SH; _SH.FOOT = SB.FOOT
    so = [dict(file=os.path.basename(CUR[p]["file"]) + ".dst", piece=f"{p} {cccore.PIECE_NAME[p]} (full)", stitches=CUR[p]["stitches"], trims=CUR[p]["trims"]) for p in P4]
    so += [dict(file=os.path.basename(s["file"]) + ".dst", piece=f"{p} split {nm}", stitches=s["stitches"], trims=s["trims"]) for p in P4 for nm, s in CUR[p]["splits"]["sections"].items()]
    th = [dict(name=PAL[k][1], code=f"Isacord {SB.TH[k]['isacord'][0]} / Polyneon {SB.TH[k]['polyneon'][0]}", de=min(SB.TH[k]["isacord"][3], SB.TH[k]["polyneon"][3])) for k in USED]
    pcs = [dict(piece=f"{cccore.ELEM_OF[p]} {p}", w=CUR[p]["size_mm"][0], h=CUR[p]["size_mm"][1], hoopings=len(CUR[p]["splits"]["sections"]) or 1) for p in P4]
    return FA.requests_page(cccore.NAME, so, th, pcs, page="F1", prof=PROF)

def build():
    pages = {"G1": None, "G2": overview(), "G3": threads(), "G4": summary(), "G5": files_page(), "G6": hooping_page()}
    el = [(ELN[e] + " (element spec)", SPEC[e]) for e in cccore.ELEMS if SPEC[e]]
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
    print("pages", pg, OUT_PDF)

if __name__ == "__main__":
    build()
