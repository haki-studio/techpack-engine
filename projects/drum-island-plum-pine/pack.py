"""Garment-level pages + merged tech pack."""
import os, json, pickle, glob, shutil
import cairosvg
from PIL import Image, ImageDraw
from shapely.ops import unary_union
from pypdf import PdfWriter, PdfReader
from sheet import t, swatch, doc, INK, MUTED, RED, ORANGE, GUIDE, GREEN, SW, SH
from render import f
from motifs2 import HEX, PAL
import tech, stitchrender as SR
import specbase as SB
from specbase import img_tag
import front as F
import espec

REV = "Rev E"; DATE = "16 Oct 2026"
SB.FOOT = f"HAKI STUDIOS · Drum Island jacket · plum + pine · EMBROIDERY · {REV} · {DATE}"
D = pickle.load(open("back2_vis.pkl", "rb")); VF = pickle.load(open("front_vis.pkl", "rb"))
VB, VS = D["back"], D["sleeve"]
QA_BACK = json.load(open("qa2.json"))
PIECES = [("01", "Back scene", "back panel", VB), ("01", "Back scene", "right sleeve (wrap)", VS),
          ("02", "Chest plum branch", "02R wearer's right front", VF["02R"]), ("02", "Chest plum branch", "02L wearer's left front", VF["02L"]),
          ("03", "Chest white pine + mist", "wearer's left front", VF["03"]), ("04", "Lower-front bamboo + mist", "wearer's right front", VF["04"])]
ST = [sum(s["st"] for s in tech.stops(v)) for *_, v in PIECES]
NST = [len(tech.stops(v)) for *_, v in PIECES]
BB = [unary_union([r["geom"] for r in v]).bounds for *_, v in PIECES]
DST2 = json.load(open("dst2_results.json")); SPL = json.load(open("dst2_splits.json"))
DKEYS = ["back", "sleeve", "02R", "02L", "03", "04"]
SUMS = {e: json.load(open(glob.glob(f"out/{e}_*/summary.json")[0])) for e in ("02", "03", "04")}

def hdr(title, sub, page):
    return SB.header(title, sub, page)

# ---------------------------------------------------------------- cover + index
def cover(index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>']
    o.append(t(14, 24, "HAKI STUDIOS", 3.0, 700, MUTED))
    o.append(t(14, 36, "Drum Island jacket · plum + pine — embroidery", 7.0, 700))
    o.append(t(14, 44, f"{REV} · {DATE} · Drum Island block, size M base · 4 embroidery elements, 6 pieces · 16 threads · all dimensions mm", 2.6, 400, MUTED))
    o.append(f'<line x1="14" y1="48" x2="{SW-14}" y2="48" stroke="{INK}" stroke-width="0.4"/>')
    fv = espec.front_view_png(F, VF, (-325, -25, 325, 625), 2.2, list(VF))
    tag, h = img_tag(fv, 14, 54, 92); o.append(tag); o.append(t(14, 54 + h + 3.5, "FRONT", 2.2, 700))
    bk = Image.open("sr_back_4.png"); tag, h2 = img_tag(bk, 112, 54, 80); o.append(tag); o.append(t(112, 54 + h2 + 3.5, "BACK", 2.2, 700))
    ix = 202
    o.append(t(ix, 58, "CONTENTS", 2.8, 700)); y = 64
    for name, pg in index:
        o.append(t(ix, y, name, 2.1)); o.append(t(SW - 14, y, f"{pg}", 2.1, 600, MUTED, "end")); y += 4.3
    y += 4
    o.append(t(ix, y, "TOTALS (estimates ±20%)", 2.4, 700)); y += 5
    tot = sum(DST2[k]["stitches"] for k in DKEYS); trims = sum(DST2[k].get("trims_dst", DST2[k]["trims_cmd"]) for k in DKEYS)
    for a, b in [("Stitches per jacket (DST v2)", f"{tot/1000:.0f}k"), ("Trims per jacket (DST v2)", f"{trims:,}"),
                 ("Hoopings per jacket", "6 (border frame) or 9 (360² splits)"),
                 ("Machine time / jacket", f"≈ {tot/750/60:.1f} h at 750 spm + stops"), ("Threads", "16 (40wt polyester)")]:
        o.append(t(ix, y, a, 2.0, 400, MUTED)); o.append(t(SW - 14, y, b, 2.0, 600, INK, "end")); y += 4
    o.append(t(SW - 14, SH - 8, SB.FOOT, 1.9, 400, MUTED, "end"))
    return o

# ---------------------------------------------------------------- placement overview
def overview():
    o = hdr("PLACEMENT OVERVIEW — every element on the garment", "Garment coords. Front: x from CF (+ = wearer's left), y down from CF neck seam. Back: x from CB, y down from CB collar seam. Tolerance ±2, rotation ±3°.", "G2")
    fv = espec.front_view_png(F, VF, (-325, -25, 325, 625), 2.6, list(VF))
    w = 128; s = w / 650; ax, ay = 12, 30
    tag, h = img_tag(fv, ax, ay, w); o.append(tag)
    X = lambda x: ax + (x + 325)*s; Y = lambda y: ay + (y + 25)*s
    labels = {"02R": "02R", "02L": "02L", "03": "03", "04": "04"}
    for p, v in VF.items():
        b = unary_union([r["geom"] for r in v]).bounds
        o.append(f'<rect x="{f(X(b[0]))}" y="{f(Y(b[1]))}" width="{f((b[2]-b[0])*s)}" height="{f((b[3]-b[1])*s)}" fill="none" stroke="{RED}" stroke-width="0.3" stroke-dasharray="1.2 0.8"/>')
        o.append(f'<circle cx="{f(X(b[0]))}" cy="{f(Y(b[1]))}" r="2.6" fill="{RED}"/>' + t(X(b[0]), Y(b[1]) + 0.8, labels[p], 1.7, 700, "#FFFFFF", "middle"))
    o.append(t(ax, ay + h + 3.5, "FRONT (0.2:1)", 2.0, 700))
    bk = Image.open("sr_back_4.png"); bw = 100; bx = 146
    tag, hb = img_tag(bk, bx, ay, bw); o.append(tag)
    # back image covers x -290..290, y -20..665
    bs = bw / 580; BX = lambda x: bx + (x + 290)*bs; BY = lambda y: ay + (y + 20)*bs
    b = BB[0]
    o.append(f'<rect x="{f(BX(b[0]))}" y="{f(BY(b[1]))}" width="{f((b[2]-b[0])*bs)}" height="{f((b[3]-b[1])*bs)}" fill="none" stroke="{RED}" stroke-width="0.3" stroke-dasharray="1.2 0.8"/>')
    o.append(f'<circle cx="{f(BX(b[0]))}" cy="{f(BY(b[1]))}" r="2.6" fill="{RED}"/>' + t(BX(b[0]), BY(b[1]) + 0.8, "01", 1.7, 700, "#FFFFFF", "middle"))
    o.append(t(bx, ay + hb + 3.5, "BACK (0.17:1) + right-sleeve wrap piece (see 01 p1)", 2.0, 700))
    # table
    ty = 30; tx = 252
    o.append(t(tx, ty, "ART BOXES", 2.2, 700))
    rows = []
    for (e, name, piece, v), b in zip(PIECES, BB):
        rows.append((e, piece, f"{b[2]-b[0]:.0f}×{b[3]-b[1]:.0f}", f"x {b[0]:+.0f}…{b[2]:+.0f}", f"y {b[1]:.0f}…{b[3]:.0f}"))
    y = ty + 4.5
    for e, piece, sz, xr, yr in rows:
        o.append(t(tx, y, f"{e} {piece}", 1.65, 600)); y += 3.0
        o.append(t(tx + 2, y, f"{sz} · {xr} · {yr}", 1.55, 400, MUTED)); y += 3.8
    o.append(t(tx, y + 2, "Sleeve piece: x/y in armhole-seam", 1.55, 400, MUTED))
    o.append(t(tx, y + 5, "coords (see 01 p1), not garment x/y.", 1.55, 400, MUTED))
    ky = 166
    o.append(t(12, ky, "KEEP-OUTS (all elements)", 2.2, 700))
    ko = [f"CF zip: {F.KEEP_CF:.0f} each side of CF (teeth + tape + topstitch)", f"Armhole, shoulder, side seams: {F.KEEP_SEAM:.0f} (allowance + topstitch + 3)",
          f"Hem seam: {F.KEEP_HEM:.0f} above (rib knit is never embroidered)", f"Collar lying flat: {F.KEEP_COLLAR:.0f} clear · welt pocket box: {F.KEEP_WELT:.0f} clear",
          "Exception: back right armhole — art runs to 3 from the seam and continues on the sleeve (01 wrap)."]
    for i, k in enumerate(ko): o.append(t(12, ky + 4.4 + i*3.4, k, 1.85))
    return o

# ---------------------------------------------------------------- threads + trims
def threads():
    o = hdr("THREAD + TRIM SUMMARY", "One 16-colour palette for the whole jacket. Approve a physical thread board (Isacord or Madeira Polyneon) before sampling; hex = on-screen target.", "G3")
    use = {k: {} for k in PAL}
    for (e, *_ , v) in PIECES:
        for s in tech.stops(v):
            use[s["col"]][e] = use[s["col"]].get(e, 0) + s["st"]
    hd = ["", "Thread", "Hex", "Isacord", "ΔE", "Madeira Polyneon", "ΔE", "Wt", "Used for", "Elements", "Stitches"]
    cx = [12, 18, 44, 58, 88, 96, 130, 138, 146, 220, 262]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.75, 700, MUTED))
    TH = SB.TH; rh = 4.6
    for i, k in enumerate(PAL):
        y = 36 + i*rh
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3)}" width="{SW-22}" height="{f(rh)}" fill="#F5F2EC"/>')
        iso, pn = TH[k]["isacord"], TH[k]["polyneon"]
        ci = GREEN if iso[3] < 3 else (ORANGE if iso[3] < 5.5 else RED); cp = GREEN if pn[3] < 3 else (ORANGE if pn[3] < 5.5 else RED)
        o.append(swatch(cx[0], y, k, 4.5, 2.8)); o.append(t(cx[1], y, PAL[k][1], 1.9, 600)); o.append(t(cx[2], y, HEX[k], 1.75, 400, MUTED))
        o.append(t(cx[3], y, f"{iso[0]} {iso[1]}"[:22], 1.75)); o.append(t(cx[4], y, f"{iso[3]:.1f}", 1.7, 600, ci))
        o.append(t(cx[5], y, f"{pn[0]} {pn[1]}"[:24], 1.75)); o.append(t(cx[6], y, f"{pn[3]:.1f}", 1.7, 600, cp))
        o.append(t(cx[7], y, "40", 1.75)); o.append(t(cx[8], y, PAL[k][2][:46], 1.7, 400, MUTED))
        o.append(t(cx[9], y, ", ".join(sorted(use[k])) or "—", 1.75)); o.append(t(cx[10], y, f"{sum(use[k].values()):,.0f}", 1.75, 600))
    yb = 36 + len(PAL)*rh + 3
    o.append(t(12, yb, "ΔE2000 vs target: green < 3, amber 3–5.5, red > 5.5 — red rows must be picked from the physical card.", 1.8, 400, MUTED))
    o.append(t(12, yb + 7, "TRIMS + CONSUMABLES (per jacket)", 2.2, 700))
    tr = [("Backing", "2.5 oz cutaway, cut 30 larger than each art box; trim to 5 from stitching after embroidery"),
          ("Topping", "none (canvas surface is firm)"), ("Needles", "75/11 sharp (canvas); change every 8 h on the back scene"),
          ("Bobbin", "60wt white polyester pre-wound"), ("Frames", f"01 back: border ≥ {BB[0][2]-BB[0][0]+14:.0f} × {BB[0][3]-BB[0][1]+14:.0f} (single file) or 4 × 360² split files (G5) · 02R/02L/03/04 + sleeve: ≤ 360 × 360"),
          ("Patches / labels", "none on this garment — all artwork is direct embroidery")]
    for i, (a, b) in enumerate(tr):
        o.append(t(12, yb + 11.5 + i*3.6, a, 1.85, 600)); o.append(t(42, yb + 11.5 + i*3.6, b, 1.85))
    return o

# ---------------------------------------------------------------- stitch summary + open questions
def summary():
    o = hdr("STITCH SUMMARY + OPEN QUESTIONS", "", "G4")
    hd = ["Element", "Piece", "Art box", "Stitches", "Trims", "Stops", "Run time", "Width check"]
    cx = [12, 52, 104, 128, 146, 160, 176, 194]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.8, 700, MUTED))
    kb = max(QA_BACK, key=lambda k: QA_BACK[k]["long_pct"]); widths = {"01": (QA_BACK[kb]["long_pct"], kb)}
    for e in ("02", "03", "04"):
        k = max(SUMS[e]["width"], key=lambda k: SUMS[e]["width"][k]); widths[e] = (SUMS[e]["width"][k], k)
    ST2 = [DST2[k]["stitches"] for k in DKEYS]; TR2 = [DST2[k].get("trims_dst", DST2[k]["trims_cmd"]) for k in DKEYS]
    for i, ((e, name, piece, v), b, st, ns, tr) in enumerate(zip(PIECES, BB, ST2, NST, TR2)):
        y = 36 + i*4.6
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3)}" width="225" height="4.6" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, f"{e} {name}", 1.85, 600)); o.append(t(cx[1], y, piece[:30], 1.8))
        o.append(t(cx[2], y, f"{b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}", 1.8)); o.append(t(cx[3], y, f"{st:,.0f}", 1.8, 600))
        o.append(t(cx[4], y, f"{tr:,}", 1.8)); o.append(t(cx[5], y, f"{ns}", 1.8)); o.append(t(cx[6], y, f"{st/750:.0f} min", 1.8))
        wv, wk = widths[e]; wc = GREEN if wv < 1 else ORANGE
        o.append(t(cx[7], y, ("all codes pass" if wv < 1 else f"worst: {wk} {wv:.1f}% — narrow ends; digitizer drops < 0.8"), 1.75, 600, wc))
    y = 36 + len(PIECES)*4.6 + 1
    o.append(t(cx[2], y, "TOTAL", 1.9, 700)); o.append(t(cx[3], y, f"{sum(ST2):,.0f}", 1.9, 700)); o.append(t(cx[4], y, f"{sum(TR2):,}", 1.9, 700)); o.append(t(cx[6], y, f"{sum(ST2)/750/60:.1f} h", 1.9, 700))
    o.append(t(12, y + 8, "Stitches / trims = counted from the v2 DST files (single-file back). Run time at 750 spm, excluding colour changes + hooping.", 1.75, 400, MUTED))
    o.append(t(12, y + 4.5, "Width check = worst region code's share of area below its minimum width (fill/satin 0.8, line 0.6) for > 2.5 mm. All other codes < 3.5%; detail per code on each element's p3.", 1.75, 400, MUTED))
    qy = y + 16
    o.append(t(12, qy, "OPEN QUESTIONS — confirm before sampling", 2.6, 700))
    qs = ["1. Fit + grading: art is placed on the Drum Island size-M block (garment pack T4). 3 art sizes proposed — A 92% (XS–S), B 100% (M–L),",
          "    C 108% (XL–3XL), see T5. Confirm, or one fixed size (cheaper; it shifts relative to seams on XS / 3XL).",
          "2. Pattern: positions are from finished edges on a traced pattern. The factory converts to cut-piece coordinates on their own pattern —",
          "    send their pattern back so the art files can be re-registered if anything moves by > 5.",
          f"3. Back frame: single file needs a border frame ≥ {BB[0][2]-BB[0][0]+14:.0f} × {BB[0][3]-BB[0][1]+14:.0f}. Otherwise sew the 4 split files S1–S4 (360 × 360) with basting crosses (G5).",
          "4. Sleeve wrap: armhole topstitch must sit on the sleeve side so it doesn't cross the branches. Confirm with the sewing room.",
          "5. Zip: chest branch is split 15 each side of CF. Confirm zip tape width (art assumes ≤ 12 tape + topstitch).",
          "6. Thread board: Madeira Polyneon is the closer brand (9 of 16 within ΔE 3, vs 3 for Isacord). Pick the amber/red rows from the physical card (G3).",
          "7. Wash: if the jacket is garment-washed / enzyme-washed after embroidery, run a wash test on the sew-out (whites + golds grey first).",
          "8. Leaves on the plum: kept from the mockup though winter plum is leafless — keep or drop?",
          "9. Reference images supplied (pine/bamboo illustrations) were used for motif language only; nothing traced.",
          "10. DST/PES v2 are production-intent drafts: the factory digitizer opens them, checks density + pull on 12 oz duck and edits before sew-out."]
    for i, q in enumerate(qs): o.append(t(12, qy + 5 + i*3.6, q, 1.85))
    return o

OUT_PDF = "out/HAKI_Drum-Island_plum-pine_EMBROIDERY-PACK_RevE.pdf"
V1_BACK = dict(stitches=254030, trims=4462)      # v1 DRAFT.dst (read back), kept for the before/after line

def files_page():
    o = hdr("PRODUCTION STITCH FILES (v2) + HOOP SPLITS", "DST (Tajima) + PES for every piece. Counts read back from the files. Origin = centre of each file's design; 0.1 mm units.", "G5")
    # ---- file table
    hd = ["File", "Size mm", "Stitches", "Trims", "Stops", "Max st.", "Frame"]; cx = [12, 70, 92, 110, 124, 136, 150]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.75, 700, MUTED))
    rows = []
    lab = {"back": "01_back-scene_BACK_v2  (single field)", "sleeve": "01_back-scene_SLEEVE_v2", "02R": "02_chest-branch_02R_v2",
           "02L": "02_chest-branch_02L_v2", "03": "03_chest-pine_v2", "04": "04_lower-bamboo_v2"}
    for k in DKEYS:
        r = DST2[k]; fr = f"border ≥ {r['size'][0]+14:.0f}×{r['size'][1]+14:.0f}" if k == "back" else "360 × 360"
        rows.append((lab[k], f"{r['size'][0]:.0f} × {r['size'][1]:.0f}", f"{r['stitches']:,}", f"{r.get("trims_dst", r["trims_cmd"]):,}", f"{r['colour_changes']+1}", f"{r['max_stitch']:.1f}", fr))
        if k == "back":
            for nm, sx in SPL["sections"].items():
                rows.append(("   " + nm.replace("_", " ") + "  (split)", f"{sx['size'][0]:.0f} × {sx['size'][1]:.0f}", f"{sx['stitches']:,}", f"{sx.get("trims_dst", sx["trims_cmd"]):,}",
                             f"{sx['colour_changes']+1}", f"{sx['max_stitch']:.1f}", "360 × 360" + ("" if sx["fits"] else " — CHECK")))
    for i, rw in enumerate(rows):
        y = 36 + i*4.1
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.9)}" width="163" height="4.1" fill="#F5F2EC"/>')
        for j, (x, v) in enumerate(zip(cx, rw)): o.append(t(x, y, v, 1.65, 600 if j == 0 and not v.startswith("   ") else 400))
    y = 36 + len(rows)*4.1 + 1.5
    o.append(t(12, y, "Stops = colour stops incl. the basting colour on split files. Max st. = longest sewn stitch (mm); nothing over 7.5.", 1.6, 400, MUTED))
    # ---- what the engine does
    y += 7; o.append(t(12, y, "WHAT IS DIGITIZED IN v2", 2.3, 700)); y += 4.6
    vb = DST2["back"]
    notes = [("Trims", f"back {V1_BACK['trims']:,} (v1 draft) → {vb.get("trims_dst", vb["trims_cmd"]):,}. Travel runs hidden under fill that sews later or under"),
             ("", "the object about to sew (underpath); objects ordered to stay inside one hidden area; slivers < 1.5 mm² dropped."),
             ("Turning satin", "twigs, petals, blades, needles: stitches stay perpendicular to a skeleton centreline, short stitches on"),
             ("", "the inside of tight curves; long fills (trunk, limbs, snow) cut in 6 mm sections, each at its own local angle."),
             ("Underlay", "satin < 2 mm none · 2–4 centre run · > 4 edge run + centre run · tatami edge run (+ 90° 2.0 mm lattice"),
             ("", "if > 30 mm²) · padded snow 2 crossed padding layers + edge run (no foam)."),
             ("Pull comp.", "per region code (01 p3 table), applied as an outward offset across the stitch direction."),
             ("Shading", "each shading tone feathers 1.2–2.5 mm into the tone sewn before it (ragged half-density rows), not a hard edge."),
             ("Ties / trims", "3-stitch tie-on and tie-off at every trim and colour change; exposed moves < 2.5 mm are jumps without a trim.")]
    for a, b in notes:
        o.append(t(12, y, a, 1.75, 700)); o.append(t(32, y, b, 1.7)); y += 3.5
    # ---- 1:1-style detail from the v2 file
    det = Image.open("v2_detail.png"); y += 3
    o.append(t(12, y, "DETAIL — v2 stitch file (back), two crops ≈ 80 × 60 mm each", 2.0, 700)); y += 2.5
    tag, dh = img_tag(det, 12, y, 140); o.append(tag)
    o.append(t(12, y + dh + 3.2, "Turning satin on twigs + buds, radial satin petals with 3-tone feather, padded snow edges, red-pine fan with gold blend.", 1.6, 400, MUTED))
    # ---- split diagram
    from PIL import Image as _I
    bk = _I.open("sr_back_4.png"); bx, by, bw = 170, 30, 115
    tag, bh = img_tag(bk, bx, by, bw); o.append(tag)
    s_ = bw / 610.0; X = lambda x: bx + (x + 305)*s_; Y = lambda y_: by + (y_ + 25)*s_
    sx, sy = SPL["sx"], SPL["sy"]
    b = BB[0]
    if sx is not None: o.append(f'<line x1="{f(X(sx))}" y1="{f(Y(b[1]-12))}" x2="{f(X(sx))}" y2="{f(Y(b[3]+12))}" stroke="{RED}" stroke-width="0.35" stroke-dasharray="1.5 0.8"/>')
    if sy is not None: o.append(f'<line x1="{f(X(b[0]-12))}" y1="{f(Y(sy))}" x2="{f(X(b[2]+12))}" y2="{f(Y(sy))}" stroke="{RED}" stroke-width="0.35" stroke-dasharray="1.5 0.8"/>')
    seen = set()
    for nm, sx_ in SPL["sections"].items():
        bb = sx_["bbox"]; n = nm[:2]
        o.append(f'<rect x="{f(X(bb[0]))}" y="{f(Y(bb[1]))}" width="{f((bb[2]-bb[0])*s_)}" height="{f((bb[3]-bb[1])*s_)}" fill="none" stroke="#0A84FF" stroke-width="0.25"/>')
        cxm, cym = X((bb[0]+bb[2])/2), Y((bb[1]+bb[3])/2)
        o.append(f'<circle cx="{f(cxm)}" cy="{f(cym)}" r="3" fill="#0A84FF"/>' + t(cxm, cym + 1, n, 2.0, 700, "#FFFFFF", "middle"))
        for m in sx_["marks"]:
            if tuple(m) in seen: continue
            seen.add(tuple(m)); mx, my = X(m[0]), Y(m[1])
            o.append(f'<path d="M{f(mx-1.4)} {f(my)} H{f(mx+1.4)} M{f(mx)} {f(my-1.4)} V{f(my+1.4)}" stroke="#00A3FF" stroke-width="0.45"/>')
    o.append(t(bx, by + bh + 3.5, f"Split lines (red) chosen to cut the least art: {SPL['cut_mm']:.0f} mm of fill crosses them.", 1.7, 400, MUTED))
    o.append(t(bx, by + bh + 6.6, "Blue boxes = each file's sewn extent; + = basting registration crosses.", 1.7, 400, MUTED))
    sy0 = by + bh + 12
    o.append(t(bx, sy0, "SEWING THE SPLIT BACK (no border frame)", 2.2, 700))
    steps = ["1. Mark CB + the two split lines on the cut back panel (chalk), from the art box (01 p1).",
             "2. Hoop S1. Stop 1 = basting crosses (water-soluble / contrast). Then sew S1.",
             "3. Re-hoop for S2. Trace; align needle on the S1 crosses it shares; sew its crosses",
             "    over them (check), then S2. Repeat for S3, S4 — each shares crosses with an earlier one.",
             "4. Fills that cross a split line overlap 1.2 mm into the neighbour so no fabric shows.",
             "   Blossoms, buds and motifs under 70 mm are never cut — each goes whole to one section.",
             "5. Remove basting + backing after S4. Sew order S1 → S4 (top first, then bottom)."]
    for i, st_ in enumerate(steps): o.append(t(bx, sy0 + 4.4 + i*3.3, st_, 1.65))
    return o

def build():
    pages = {"G1": None, "G2": overview(), "G3": threads(), "G4": summary(), "G5": files_page()}
    el = [("01 Back scene", sorted(glob.glob("out/01_back-scene/*SPEC_RevE.pdf"))[0]),
          ("02 Chest plum branch", glob.glob("out/02_*/*SPEC_RevB.pdf")[0]),
          ("03 Chest white pine + mist", glob.glob("out/03_*/*SPEC_RevB.pdf")[0]),
          ("04 Lower-front bamboo + mist", glob.glob("out/04_*/*SPEC_RevB.pdf")[0])]
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
    os.makedirs("out", exist_ok=True)
    w.write(OUT_PDF)
    print("pages", pg - 1, "stitches", round(sum(ST)))

if __name__ == "__main__":
    build()
