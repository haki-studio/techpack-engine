"""Embroidery pack G1-G5 for the Grand Line jacket (01 front scene, pieces FR + FL). Numbers come from the stitch files."""
import glcore
import os, json, pickle, glob
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
import front as F, espec, emb_place as EP, factory as FA
PROF = FA.load(); FRAME = FA.largest_frame(PROF); FR_S = f"{FRAME[0]:.0f} × {FRAME[1]:.0f}"
def mh(r): return FA.machine_hours(r["stitches"], PROF, trims=r["trims"], colour_changes=r["stops"] - 1)
dst2 = glcore.patch_dst2()

REV, DATE = glcore.REV_EMB, glcore.DATE
SB.FOOT = f"HAKI STUDIOS · {glcore.NAME} · EMBROIDERY · {REV} · {DATE}"
D = pickle.load(open("front_M.pkl", "rb")); VF = {"FR": D["FR"], "FL": D["FL"]}
CUR = json.load(open("dst_current.json")); ALL = json.load(open("dst_all.json")); META = json.load(open("scene_meta.json"))
SUM = json.load(open(glob.glob("out/01_front-scene/summary.json")[0])) if glob.glob("out/01_front-scene/summary.json") else {}
P2 = glcore.PIECES
BB = {p: unary_union([r["geom"] for r in VF[p]]).bounds for p in P2}
OUT_PDF = f"out/HAKI_GRLN_EMBROIDERY-PACK_{REV.replace(' ', '')}.pdf"
SPEC = glob.glob("out/01_front-scene/*SPEC_*.pdf")
def hdr(title, sub, page): return SB.header(title, sub, page)
TOT = sum(CUR[p]["stitches"] for p in P2); TRIMS = sum(CUR[p]["trims"] for p in P2)
MH = sum(mh(CUR[p]) for p in P2)                                   # full files (one hooping each)
MH_SPLIT = sum(mh(s) for p in P2 for s in CUR[p]["splits"]["sections"].values())

def cover(index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>']
    o.append(t(14, 24, "HAKI STUDIOS", 3.0, 700, MUTED))
    o.append(t(14, 36, "Grand Line jacket · washed navy — embroidery", 7.0, 700))
    o.append(t(14, 44, f"{REV} · {DATE} · Drum Island block, size M base · 1 element (01 front scene), 2 pieces · 12 threads · all dimensions mm", 2.6, 400, MUTED))
    o.append(f'<line x1="14" y1="48" x2="{SW-14}" y2="48" stroke="{INK}" stroke-width="0.4"/>')
    fv = espec.front_view_png(F, VF, (-325, -105, 325, 560), 2.2, list(VF))
    tag, h = img_tag(fv, 14, 54, 110); o.append(tag); o.append(t(14, 54 + h + 3.5, "FRONT (size M stitch render). Back + sleeves: no embroidery.", 2.2, 700))
    ix = 202
    o.append(t(ix, 58, "CONTENTS", 2.8, 700)); y = 64
    for name, pg in index:
        o.append(t(ix, y, name, 2.1)); o.append(t(SW - 14, y, f"{pg}", 2.1, 600, MUTED, "end")); y += 4.3
    y += 4
    o.append(t(ix, y, "TOTALS, SIZE M (read from the DST files)", 2.4, 700)); y += 5
    for a, b in [("Stitches per jacket", f"{TOT:,}"), ("Trims per jacket", f"{TRIMS:,}"),
                 ("Hoopings per jacket", f"4 on {FR_S} (2 per piece), or 2 on a ≥ 300 × 520 frame"),
                 ("Machine time / jacket", f"{MH_SPLIT:.1f} h split files ({MH:.1f} h full files), incl. trims + colour changes"), ("Threads", "12 (40wt polyester), ≤ 15 per file")]:
        o.append(t(ix, y, a, 2.0, 400, MUTED)); o.append(t(SW - 14, y, b, 1.9, 600, INK, "end")); y += 4
    o.append(t(SW - 14, SH - 8, SB.FOOT, 1.9, 400, MUTED, "end"))
    return o

def overview():
    o = hdr("PLACEMENT OVERVIEW — the front scene on the garment", "Garment coords: x from CF (+ = wearer's left), y down from the CF neck seam. Tolerance ±2, rotation ±2° (the halves must meet at the zip).", "G2")
    fv = espec.front_view_png(F, VF, (-325, -105, 325, 560), 2.6, list(VF))
    w = 150; s = w / 650; ax, ay = 12, 30
    tag, h = img_tag(fv, ax, ay, w); o.append(tag)
    X = lambda x: ax + (x + 325)*s; Y = lambda y: ay + (y + 105)*s
    for p in P2:
        b = BB[p]
        o.append(f'<rect x="{f(X(b[0]))}" y="{f(Y(b[1]))}" width="{f((b[2]-b[0])*s)}" height="{f((b[3]-b[1])*s)}" fill="none" stroke="{RED}" stroke-width="0.3" stroke-dasharray="1.2 0.8"/>')
        o.append(f'<circle cx="{f(X(b[0]))}" cy="{f(Y(b[1]))}" r="2.6" fill="{RED}"/>' + t(X(b[0]), Y(b[1]) + 0.8, p, 1.6, 700, "#FFFFFF", "middle"))
    for p in P2:
        sy = CUR[p]["splits"].get("sy")
        if sy is not None:
            b_ = BB[p]; o.append(f'<line x1="{f(X(b_[0]-6))}" y1="{f(Y(sy))}" x2="{f(X(b_[2]+6))}" y2="{f(Y(sy))}" stroke="#0A84FF" stroke-width="0.4" stroke-dasharray="2 1"/>')
            o.append(t(X(b_[0]) + 1, Y(sy) - 1, f"{p} split y {sy:.0f}", 1.5, 700, "#0A84FF"))
    hz = D["info"]["marks"][0]["y"]
    o.append(f'<line x1="{f(X(-40))}" y1="{f(Y(hz))}" x2="{f(X(40))}" y2="{f(Y(hz))}" stroke="#00A3FF" stroke-width="0.6"/>')
    o.append(t(ax, ay + h + 3.5, f"FRONT, size M (0.23:1). Red = art boxes (corner label = piece). Blue = horizon match mark at the zip (y {hz:.1f}); dashed blue = hoop split lines (G6).", 1.9, 700))
    tx = 170; ty = 30
    o.append(t(tx, ty, "ART BOX PER SIZE (mm, x from CF / y from CF neck)", 2.2, 700))
    hd = ["Size", "Art", "FR x", "FR y", "FL x", "FL y", "Horizon y"]; cx = [tx, tx + 10, tx + 18, tx + 40, tx + 60, tx + 82, tx + 102]
    for x_, hh in zip(cx, hd): o.append(t(x_, ty + 5, hh, 1.6, 700, MUTED))
    for i, sz in enumerate(glcore.SIZES):
        pl = EP.place(sz)[0]; y = ty + 9.5 + i*4.0
        if i % 2 == 0: o.append(f'<rect x="{tx-1}" y="{f(y-2.8)}" width="{SW - tx - 11}" height="4" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, sz, 1.7, 700)); o.append(t(cx[1], y, glcore.GRADE[sz][0], 1.7, 700, RED))
        for j, p in enumerate(P2):
            b = pl[p][1].bounds
            o.append(t(cx[2 + 2*j], y, f"{b[0]:+.0f}…{b[2]:+.0f}", 1.55)); o.append(t(cx[3 + 2*j], y, f"{b[1]:.0f}…{b[3]:.0f}", 1.55))
        o.append(t(cx[6], y, f"{META['horizon']*glcore.GRADE[sz][1] + 0.6*glcore.GRADE[sz][1]:.1f}", 1.55))
    ky = ty + 9.5 + 7*4.0 + 5
    o.append(t(tx, ky, "KEEP-OUTS (all sizes, measured on T13)", 2.2, 700))
    ko = [f"CF zip: {F.KEEP_CF:.0f} each side of CF (teeth + tape + topstitch)", f"Armhole, shoulder, side seams: {F.KEEP_SEAM:.0f}",
          f"Hem-rib seam: {F.KEEP_HEM:.0f} above (rib is never embroidered)", f"Collar lying flat: {F.KEEP_COLLAR:.0f} · welt pocket box: {F.KEEP_WELT:.0f}",
          "Back + sleeves: no embroidery."]
    for i, k in enumerate(ko): o.append(t(tx, ky + 4.4 + i*3.4, k, 1.75))
    my = ky + 4.4 + 5*3.4 + 4
    o.append(t(tx, my, "MATCHING ACROSS THE ZIP", 2.2, 700))
    for i, l in enumerate(["Both pieces are graded about the CF neck point: the horizon and", "every ray hit the zip keep-out lines at the same y on FR and FL.",
                           "Hoop to the marked CF + horizon line; after the zip is set the", "horizon must read as one line (±1 mm)."]):
        o.append(t(tx, my + 4.2 + i*3.2, l, 1.7))
    return o

def threads():
    o = hdr("THREAD + TRIM SUMMARY", "One palette for the whole jacket — 12 threads. Approve a physical thread board (Isacord or Madeira Polyneon) before sampling; hex = on-screen target.", "G3")
    use = {k: {} for k in glcore.GL_KEYS}
    for p in P2:
        for c in CUR[p]["colours"]: use[c][p] = use[c].get(p, 0) + 1
    hd = ["", "Thread", "Hex", "Isacord", "ΔE", "Madeira Polyneon", "ΔE", "Wt", "Used for", "Stops FR / FL"]
    cx = [12, 18, 44, 58, 88, 96, 130, 138, 146, 236]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.75, 700, MUTED))
    TH = SB.TH; rh = 5.0
    for i, k in enumerate(glcore.GL_KEYS):
        y = 36 + i*rh
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3.2)}" width="{SW-22}" height="{f(rh)}" fill="#F5F2EC"/>')
        iso, pn = TH[k]["isacord"], TH[k]["polyneon"]
        ci = GREEN if iso[3] < 3 else (ORANGE if iso[3] < 5.5 else RED); cp = GREEN if pn[3] < 3 else (ORANGE if pn[3] < 5.5 else RED)
        o.append(swatch(cx[0], y, k, 4.5, 2.8)); o.append(t(cx[1], y, PAL[k][1], 1.9, 600)); o.append(t(cx[2], y, HEX[k], 1.75, 400, MUTED))
        o.append(t(cx[3], y, f"{iso[0]} {iso[1]}"[:22], 1.75)); o.append(t(cx[4], y, f"{iso[3]:.1f}", 1.7, 600, ci))
        o.append(t(cx[5], y, f"{pn[0]} {pn[1]}"[:24], 1.75)); o.append(t(cx[6], y, f"{pn[3]:.1f}", 1.7, 600, cp))
        o.append(t(cx[7], y, "40", 1.75)); o.append(t(cx[8], y, PAL[k][2][:60], 1.7, 400, MUTED))
        o.append(t(cx[9], y, f"{use[k].get('FR', 0)} / {use[k].get('FL', 0)}", 1.75, 600))
    yb = 36 + len(glcore.GL_KEYS)*rh + 3
    o.append(t(12, yb, "ΔE2000 vs target: green < 3, amber 3–5.5, red > 5.5 — amber/red rows must be picked from the physical card. All targets are PROPOSED (read from the mockup).", 1.8, 600, ORANGE))
    o.append(t(12, yb + 7, "TRIMS + CONSUMABLES (per jacket)", 2.2, 700))
    tr = [("Backing", "2.5 oz cutaway, black/charcoal (navy shell), cut 30 larger than each hooping; trim to 5 from stitching after embroidery"),
          ("Topping", "none (canvas surface is firm)"), ("Needles", "75/11 sharp (canvas)"), ("Bobbin", "60wt black or navy polyester pre-wound (dark shell)"),
          ("Frames", f"{FR_S} (factory.json{'' if PROF['frames_confirmed'] else ', PROPOSED'}): 2 hoopings per piece (split files, G5) · single file per piece needs ≥ {max(BB[p][2]-BB[p][0] for p in P2)+14:.0f} × {max(BB[p][3]-BB[p][1] for p in P2)+14:.0f} (M)"),
          ("Patches / labels", "none on this garment — all artwork is direct embroidery")]
    for i, (a, b) in enumerate(tr):
        o.append(t(12, yb + 11.5 + i*3.6, a, 1.85, 600)); o.append(t(42, yb + 11.5 + i*3.6, b, 1.85))
    return o

def summary():
    o = hdr("STITCH SUMMARY + OPEN QUESTIONS", "Size M files. Every count read back from the DST (trims) and PES (stitches).", "G4")
    hd = ["Element", "Piece", "Art box", "Stitches", "Trims", "Stops", "Threads", "Max stitch", "Run time", "Width check"]
    cx = [12, 44, 86, 108, 126, 140, 152, 166, 182, 198]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.8, 700, MUTED))
    import tech as _T
    HAIR = [k for k in SUM.get("width", {}) if _T.RULES.get(k, ("", "Run"))[1].startswith("Run")]
    wc = {k: v for k, v in SUM.get("width", {}).items() if k not in HAIR}; wk = max(wc, key=wc.get) if wc else None
    for i, p in enumerate(P2):
        r = CUR[p]; b = BB[p]; y = 36 + i*4.6
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3)}" width="{SW-22}" height="4.6" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, "01 Front scene", 1.85, 600)); o.append(t(cx[1], y, f"{p} {glcore.PIECE_NAME[p]}", 1.8))
        o.append(t(cx[2], y, f"{b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}", 1.8)); o.append(t(cx[3], y, f"{r['stitches']:,}", 1.8, 600))
        o.append(t(cx[4], y, f"{r['trims']:,}", 1.8)); o.append(t(cx[5], y, f"{r['stops']}", 1.8)); o.append(t(cx[6], y, f"{len(set(r['colours']))}", 1.8))
        o.append(t(cx[7], y, f"{r['max_stitch']:.2f} mm", 1.8)); o.append(t(cx[8], y, f"{mh(r)*60:.0f} min", 1.8))
        if wk is not None:
            v = wc[wk]; o.append(t(cx[9], y, ("fills/satins < 1 %" if v < 1 else f"worst {wk} {v:.1f}% (tapered ends)") + f"; hairline runs: {', '.join(HAIR)}", 1.6, 600, GREEN if v < 1 else ORANGE))
    y = 36 + len(P2)*4.6 + 1
    o.append(t(cx[2], y, "TOTAL", 1.9, 700)); o.append(t(cx[3], y, f"{TOT:,}", 1.9, 700)); o.append(t(cx[4], y, f"{TRIMS:,}", 1.9, 700)); o.append(t(cx[8], y, f"{MH:.1f} h", 1.9, 700))
    o.append(t(12, y + 4.5, "Width check = share of a code's area below its minimum width (fill/satin 0.8, bean 0.6). Hairline runs (glow, scale dashes) are single-run lines by design (fidelity) — check on the sew-out.", 1.7, 400, MUTED))
    o.append(t(12, y + 7.8, f"Run time = factory.machine_hours: {PROF['spm']} spm + 6 s per trim + 4 s per colour change, one hooping (split files: {MH_SPLIT:.1f} h per jacket). Rev B is built for fidelity; cost is cleaned up after the sew-out.", 1.7, 400, MUTED))
    qy = y + 16
    o.append(t(12, qy, "OPEN QUESTIONS — confirm before sampling", 2.6, 700))
    qs = [f"1. Frame: each piece is ~420–505 tall → 2 hoopings on {FR_S} (split S1/S2, registration crosses, G5/G6), or 1 hooping on a ≥ 300 × 520 frame (full files). Which?",
          "2. Thread board: all 12 targets are read from a low-res AI mockup — approve physical colours (G3), especially sea teals vs the navy shell.",
          "3. Shell dye: embroidery assumes piece-dyed, pre-washed navy duck. If the jacket is garment-dyed/washed after embroidery, wash-test the sew-out first.",
          "4. Grading: A 92% (XS–S) · B 100% (M–XL) · C 108% (XXL–3XL), one file per size per piece, scaled about the CF neck so the horizon meets at CF. OK?",
          "5. Zip: art stops 15 each side of CF (assumes ≤ 12 tape + 10 mm topstitch). Confirm tape width.",
          "6. Welts: placed at the mockup position (moved 18 toward CF), Drum Island welt size 1.4 × 13. Confirm before the art is frozen.",
          "7. Fidelity first (Devin): dashed rays, dash-field sea, soft florets and hairline glow are built as in the close-ups; trims + run time are reported, clean up after the sew-out.",
          "8. Reference: layout from the mockup, detail from AI close-ups (inputs/closeups) - not originals. Real artwork files would still be better.",
          "9. Name: 'Grand Line' is a One Piece term (Shueisha/Toei) — internal slug only; the art itself is generic (no characters/logos).",
          "10. DST/PES are production-intent drafts: the factory digitizer checks density + pull on 12 oz duck and edits before the sew-out."]
    for i, q in enumerate(qs): o.append(t(12, qy + 5 + i*3.6, q, 1.8))
    return o

def files_page():
    o = hdr("PRODUCTION STITCH FILES + HOOP SPLITS", "DST (Tajima) + PES, one set per size per piece. Counts read back from the files; trims counted from the DST. Origin = centre of each file's design ((+) on the pattern).", "G5")
    o.append(t(12, 31, "01 FRONT SCENE — one file per size per piece (art re-clipped to each size's keep-outs)", 2.0, 700))
    hd = ["Size", "Art", "Piece", "Full file mm", "Stitches", "Trims", "Stops", "S1 top: st / trims / mm", "S2 bottom: st / trims / mm", "Fits frame"]
    cx = [12, 22, 30, 40, 62, 78, 90, 102, 148, 194]
    for x_, h in zip(cx, hd): o.append(t(x_, 35.5, h, 1.55, 700, MUTED))
    y = 39.5; allfit = True
    for i, sz in enumerate(glcore.SIZES):
        for p in P2:
            r = ALL.get(sz, {}).get(p)
            if (i % 2 == 0): o.append(f'<rect x="11" y="{f(y-2.6)}" width="196" height="3.5" fill="#F5F2EC"/>')
            o.append(t(cx[0], y, sz if p == "FR" else "", 1.55, 700)); o.append(t(cx[1], y, glcore.GRADE[sz][0] if p == "FR" else "", 1.55, 700, RED)); o.append(t(cx[2], y, p, 1.55, 600))
            if r and "full" in r:
                fu = r["full"]
                o.append(t(cx[3], y, f"{fu['size_mm'][0]:.0f} × {fu['size_mm'][1]:.0f}", 1.5)); o.append(t(cx[4], y, f"{fu['stitches']:,}", 1.5)); o.append(t(cx[5], y, f"{fu['trims']}", 1.5)); o.append(t(cx[6], y, f"{fu['stops']}", 1.5))
                secs = r.get("splits", {}).get("sections", {})
                for j, nm in enumerate(("S1_top", "S2_bottom")):
                    s_ = secs.get(nm)
                    if s_: o.append(t(cx[7 + j], y, f"{s_['stitches']:,} / {s_['trims']} / {s_['size_mm'][0]:.0f}×{s_['size_mm'][1]:.0f}", 1.5))
                fits = bool(secs) and all(v["fits"] for v in secs.values()); allfit &= fits
                o.append(t(cx[9], y, "yes" if fits else "CHECK", 1.5, 700, GREEN if fits else RED))
            else:
                o.append(t(cx[3], y, "pending", 1.5, 400, MUTED)); allfit = False
            y += 3.5
    y += 3
    o.append(t(12, y, "WHAT IS DIGITIZED", 2.0, 700)); y += 4.2
    notes = [("Sea", "light dashes (foam / light teal / teal, tatami 0°) sewn first; the dark sea field (tatami 0°, 45 × 30 cells) last, around them."),
             ("Clouds", "per bank: lit rims → shade bands → lobe bodies (turning satin) → dark edge band on top; neighbouring lobes touch, no fabric gaps."),
             ("Sun + rays", "radial satin sun, tapered satin burst; rays + horizon are 0.8 bean lines sewn over the sea (no knockout)."),
             ("Stars", "single-thread crosses + dots; big sparkles gold arms + pale centre. Halo: run-stitch arcs."),
             ("Ties", "3-stitch tie-on/off at every trim + colour change; max sewn stitch ≤ 7.5 mm; ≤ 15 threads per file.")]
    for a, b_ in notes:
        o.append(t(12, y, a, 1.6, 700)); o.append(t(30, y, b_, 1.5)); y += 3.3
    # split diagram (size M, FR)
    sp = CUR["FR"].get("splits") or {}
    bx, by, bw = 214, 31, 72
    img = SR.render(VF["FR"], (BB["FR"][0]-14, BB["FR"][1]-14, BB["FR"][2]+14, BB["FR"][3]+14), 1.6, base=glcore.FABRIC)
    tag, bh = img_tag(img, bx, by, bw); o.append(tag)
    s_ = bw / (BB["FR"][2] - BB["FR"][0] + 28); X = lambda x: bx + (x - BB["FR"][0] + 14)*s_; Y = lambda y_: by + (y_ - BB["FR"][1] + 14)*s_
    if sp.get("sy") is not None:
        o.append(f'<line x1="{f(X(BB["FR"][0]-12))}" y1="{f(Y(sp["sy"]))}" x2="{f(X(BB["FR"][2]+12))}" y2="{f(Y(sp["sy"]))}" stroke="{RED}" stroke-width="0.35" stroke-dasharray="1.5 0.8"/>')
    for nm, sx_ in sp.get("sections", {}).items():
        bb = sx_["bbox"]
        o.append(f'<rect x="{f(X(bb[0]))}" y="{f(Y(bb[1]))}" width="{f((bb[2]-bb[0])*s_)}" height="{f((bb[3]-bb[1])*s_)}" fill="none" stroke="#0A84FF" stroke-width="0.25"/>')
        o.append(t(X(bb[0]) + 1, Y(bb[1]) + 3, nm[:2], 2.0, 700, "#0A84FF"))
        for m in sx_["marks"]:
            mx, my = X(m[0]), Y(m[1]); o.append(f'<path d="M{f(mx-1.4)} {f(my)} H{f(mx+1.4)} M{f(mx)} {f(my-1.4)} V{f(my+1.4)}" stroke="#00E0FF" stroke-width="0.45"/>')
    o.append(t(bx, by + bh + 3, f"FR size M: red = split line (y {sp.get('sy', 0):.0f}), blue = files, + = registration crosses (stop-1 thread).", 1.45, 400, MUTED))
    sy0 = by + bh + 8
    o.append(t(bx, sy0, "SEWING A SPLIT PIECE", 2.0, 700))
    steps = ["1. Mark CF, horizon + split line on the cut", "    panel (chalk) from the pattern.",
             "2. Hoop S1 (top). Stop 1 starts with the", "    registration crosses (stop-1 thread). Sew S1.",
             "3. Re-hoop for S2; align the needle on the", "    shared crosses, sew them (check), then S2.",
             "4. Fills crossing the split overlap 1.2;", "    lobes, stars, islets < 70 go whole to one file.",
             "5. Pick out the crosses, trim backing after S2.", f"Fits the frame on every size: {'yes' if allfit else 'CHECK'}."]
    for i, st_ in enumerate(steps): o.append(t(bx, sy0 + 4 + i*3.0, st_, 1.5, 700 if i == len(steps) - 1 else 400, (GREEN if allfit else RED) if i == len(steps) - 1 else INK))
    return o

def split_cloud_cut(sz, P):
    """mm of cloud outline the split line crosses (a cloud joint the strike-off must check)"""
    from shapely.geometry import LineString
    sp = ALL[sz][P]["splits"]; sy = sp.get("sy")
    if sy is None: return 0.0
    D_ = pickle.load(open(f"front_{sz}.pkl", "rb"))
    u = unary_union([r["geom"] for r in D_[P] if r["grp"].startswith(("CL", "ISL"))])
    return u.intersection(LineString([(-400, sy), (400, sy)])).length

def hooping_page():
    o = hdr("HOOPING TABLE — split line + needle start per file, every size", f"Frame {FR_S} mm (factory.json{'' if PROF['frames_confirmed'] else ', PROPOSED'}). Coordinates in mm on the garment / pattern: x from CF (+ = wearer's left), y down from the CF neck seam. DXF layer 13 = these points.", "G6")
    hd = ["Size", "Piece", "Split line y", "S1 top: needle start (x, y)", "S1 file mm", "S2 bottom: needle start (x, y)", "S2 file mm", "Full file start (x, y)", "Cloud crossed by split", "Fit"]
    cx = [12, 24, 36, 56, 100, 124, 168, 192, 232, 272]
    for x_, h in zip(cx, hd): o.append(t(x_, 31, h, 1.55, 700, MUTED))
    y = 36; flags = []
    for i, sz in enumerate(glcore.SIZES):
        for P in P2:
            r = ALL[sz][P]; sp = r["splits"]; secs = sp["sections"]
            if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.6)}" width="{SW-22}" height="3.6" fill="#F5F2EC"/>')
            o.append(t(cx[0], y, sz if P == "FR" else "", 1.55, 700)); o.append(t(cx[1], y, P, 1.55, 600))
            o.append(t(cx[2], y, f"{sp['sy']:.1f}" if sp.get("sy") is not None else "—", 1.55, 700, RED))
            for j, nm in enumerate(("S1_top", "S2_bottom")):
                s_ = secs.get(nm)
                if s_:
                    o.append(t(cx[3 + 2*j], y, f"({s_['origin'][0]:+.1f}, {s_['origin'][1]:.1f})", 1.5)); o.append(t(cx[4 + 2*j], y, f"{s_['size_mm'][0]:.0f} × {s_['size_mm'][1]:.0f}", 1.5))
            fo = r["full"]["origin"]; o.append(t(cx[7], y, f"({fo[0]:+.1f}, {fo[1]:.1f})", 1.5))
            cc = split_cloud_cut(sz, P); flags.append(cc)
            o.append(t(cx[8], y, f"{cc:.0f} mm" + (" — check joint" if cc > 1 else ""), 1.5, 600 if cc > 1 else 400, ORANGE if cc > 1 else INK))
            ok = all(v["fits"] for v in secs.values()); o.append(t(cx[9], y, "yes" if ok else "NO", 1.5, 700, GREEN if ok else RED))
            y += 3.6
    y += 3
    notes = ["The split line is chosen where it cuts the least art inside the frame (searched 12–88 % of the art height). Where it still crosses a cloud",
             "bank (amber), lobes under 70 mm go whole to one file and larger fills overlap 1.2 mm — check that joint on the strike-off photos.",
             "Needle start = centre of each file's design (origin of the DST/PES). Mark it on the cut panel from the pattern (DXF layer 13 + layer 8 cross).",
             "Registration crosses sew at the start of stop 1 in that stop's thread (factory: max 12 colours per file, no separate basting thread);",
             "long 4 mm stitches on bare fabric 4 mm outside the art — S2 re-registers on the crosses S1 sewed; pick them out after S2."]
    for i, l in enumerate(notes): o.append(t(12, y + i*3.4, l, 1.6, 400, MUTED))
    return o

def f1_pages():
    import sheet as _SH; _SH.FOOT = SB.FOOT
    so = [dict(file=os.path.basename(CUR[p]["file"]) + ".dst", piece=f"{p} {glcore.PIECE_NAME[p]}", stitches=CUR[p]["stitches"], trims=CUR[p]["trims"]) for p in P2]
    so += [dict(file=os.path.basename(s["file"]) + ".dst", piece=f"{p} split {nm}", stitches=s["stitches"], trims=s["trims"]) for p in P2 for nm, s in CUR[p]["splits"]["sections"].items()]
    th = [dict(name=PAL[k][1], code=f"Isacord {SB.TH[k]['isacord'][0]} / Polyneon {SB.TH[k]['polyneon'][0]}", de=min(SB.TH[k]["isacord"][3], SB.TH[k]["polyneon"][3])) for k in glcore.GL_KEYS]
    pcs = [dict(piece=f"01 {p}", w=CUR[p]["size_mm"][0], h=CUR[p]["size_mm"][1], hoopings=len(CUR[p]["splits"]["sections"])) for p in P2]
    return FA.requests_page(glcore.NAME, so, th, pcs, page="F1", prof=PROF)

def build():
    pages = {"G1": None, "G2": overview(), "G3": threads(), "G4": summary(), "G5": files_page(), "G6": hooping_page()}
    el = [("01 Front scene", SPEC[0])]
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
    print("pages", pg - 1)

if __name__ == "__main__":
    build()
