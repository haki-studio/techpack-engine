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
SWT = json.load(open("out/01_wave/M/swatch/result_swatch.json"))
CONT = json.load(open("continuity_M.json")); CONT_OK = {k: v for k, v in CONT.items() if v.get("meet") is not None and v["art_mm"] >= 10}
MMK = json.load(open("out/placement/match_marks_M.json"))
GATES = json.load(open("gates_M.json"))
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
    o.append(t(14, 44, f"{REV} · {DATE} · Drum Island block (body unchanged), size M · collar (no hood) · 1 element (01 wave), 5 pieces, seam-true wrap · 9 threads · mm", 2.6, 400, MUTED))
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
                 ("Machine time / jacket", f"{MH_HOOP:.1f} h as hooped, one head"), ("Threads", f"9 (40wt polyester), ≤ {FA.max_threads(PROF)} per file"),
                 ("Foam swatch (F1)", f"{SWT['stitches']:,} st · {SWT['trims']} trims · 1 hooping"),
                 ("Seams with art", f"{len(CONT_OK)} measured, art meets across {min(v['meet'] for v in CONT_OK.values())}-{max(v['meet'] for v in CONT_OK.values())} % (G7)")]:
        o.append(t(ix, y, a, 2.0, 400, MUTED)); o.append(t(SW - 14, y, b, 1.9, 600, INK, "end")); y += 4
    y += 4
    for l_ in ["!Rev B (founder 19 Oct): SEAMLESS wave - every stripe that crosses a seam", "!continues into the next piece (armholes by seam length, sides,",
               "!shoulders, sleeve underarm + centre line), art 3 mm short of each", "!seam, match notches on both pieces (G7 + 1:1 placement plot).",
               "!Shell colour, hardware colour and cuff / hem rib will change:", "!re-check the thread board (G3) + hem / cuff keep-outs on them."]:
        o.append(t(ix, y, l_.lstrip("!"), 1.75, 600, ORANGE)); y += 3.3
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
    tx = 226; ty = 30
    o.append(t(tx, ty, "ART BOX (w × h mm, DST read-back)", 2.0, 700))
    for j, P in enumerate(PS): o.append(t(tx + 8 + j * 12.0, ty + 5, P, 1.5, 700, MUTED))
    o.append(t(tx, ty + 5, "Size", 1.5, 700, MUTED))
    for i, sz in enumerate(WC.DOC_SIZES):
        y = ty + 9.5 + i * 3.8
        if i % 2 == 0: o.append(f'<rect x="{tx-1}" y="{f(y-2.7)}" width="{SW - tx - 9}" height="3.8" fill="#F5F2EC"/>')
        o.append(t(tx, y, sz, 1.5, 700))
        for j, P in enumerate(PS):
            r = ALL.get(sz, {}).get(P)
            if r: o.append(t(tx + 8 + j * 12.0, y, f"{r['full']['size_mm'][0]:.0f}×{r['full']['size_mm'][1]:.0f}", 1.25))
    o.append(t(tx, ty + 9.5 + len(WC.DOC_SIZES) * 3.8, "Other sizes: after the size-M strike-off.", 1.45, 400, MUTED))
    ky = ty + 9.5 + len(WC.DOC_SIZES) * 3.8 + 7
    o.append(t(tx, ky, "KEEP-OUTS (mm from the sew line)", 2.0, 700))
    for i, k in enumerate(["Rev B seam-true wrap: the art stops", "3 mm short of every seam it crosses:", "armhole / cap, side, shoulder, sleeve",
                           "underarm (no armhole topstitch)", "CF zip 15 each side (teeth + tape +", "  topstitch) · hem-rib seam 10 · cuff 10",
                           "welt box 6 · collar flat 6 · neck 6", "rib + collar never embroidered", "!Rib may change: re-check hem / cuff",
                           "!keep-outs on the new rib [proposed].", "", "Match marks: G7 + the 1:1 placement", "plot (art placement only)."]):
        o.append(t(tx, ky + 4.2 + i * 3.2, k.lstrip("!"), 1.55, 600 if k.startswith("!") else 400, ORANGE if k.startswith("!") else INK))
    return o

def render_samples():
    """median render colour of the pixels the tracer classed as each thread tone (back + front views): the 'render sample'
    next to every target hex (review item 6)"""
    import numpy as np, wavetrace as WT, mockmap as MM
    from PIL import Image
    p_ = "out/render_samples.json"
    if os.path.exists(p_): return json.load(open(p_))
    acc = {}
    for view in ("back", "front"):
        lab, up, b = WT.classify(view)
        img = np.asarray(MM.image(view).crop(b).resize(((b[2] - b[0]) * up, (b[3] - b[1]) * up), Image.NEAREST)).astype(float)
        for k in WC.WV_KEYS + ["w2"]:
            m = lab == WT.NAMES.index(k)
            if m.any(): acc.setdefault(k, []).append(img[m])
    out = {k: "#%02X%02X%02X" % tuple(int(v) for v in np.median(np.concatenate(v_), 0)) for k, v_ in acc.items()}
    json.dump(out, open(p_, "w")); return out

ECRU = ("#D3CAC1", "Foam ecru (candidate)")
def threads():
    o = hdr("THREAD + TRIM SUMMARY", "One palette for the whole jacket - 9 threads. Approve a physical thread board (Isacord or Madeira Polyneon) before sampling; hex = on-screen target, render = the render's own pixels of that tone.", "G3")
    RS = render_samples()
    use = {k: {} for k in WC.WV_KEYS}
    for p in PS:
        for c in CUR[p]["colours"]:
            if c in use: use[c][p] = use[c].get(p, 0) + 1
    hd = ["", "Thread", "Target", "Render", "Isacord", "ΔE", "Madeira Polyneon", "ΔE", "Wt", "Used for", "Stops BK/FR/FL/SR/SL"]
    cx = [12, 18, 42, 58, 76, 104, 111, 141, 148, 154, 250]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.75, 700, MUTED))
    TH = SB.TH; rh = 5.0
    def sw_hex(x, y, hx):
        return f'<rect x="{f(x)}" y="{f(y-2.6)}" width="3.6" height="3.2" fill="{hx}" stroke="#999" stroke-width="0.15"/>'
    rows = WC.WV_KEYS + ["ecru"]
    for i, k in enumerate(rows):
        y = 36 + i * rh
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3.3)}" width="{SW-22}" height="{f(rh)}" fill="#F5F2EC"/>')
        if k == "ecru":
            import tech
            m_i, m_p = tech.match(ECRU[0], "isacord"), tech.match(ECRU[0], "polyneon")
            o.append(sw_hex(cx[0], y, ECRU[0])); o.append(t(cx[1], y, ECRU[1], 1.8, 700, ORANGE)); o.append(t(cx[2], y, ECRU[0], 1.7, 400, MUTED))
            o.append(sw_hex(cx[3], y, ECRU[0])); o.append(t(cx[3] + 4.5, y, "close-up avg", 1.4, 400, MUTED))
            o.append(t(cx[4], y, f"{m_i[0]} {m_i[1]}", 1.75)); o.append(t(cx[5], y, f"{m_i[3]:.1f}", 1.7, 600, ORANGE))
            o.append(t(cx[6], y, f"{m_p[0]} {m_p[1]}", 1.75)); o.append(t(cx[7], y, f"{m_p[3]:.1f}", 1.7, 600, ORANGE))
            o.append(t(cx[8], y, "40", 1.75)); o.append(t(cx[9], y, "PROPOSED alternative to Foam white for foam + drops: sewn in the F1 swatch (tiles C/D)", 1.55, 600, ORANGE))
            continue
        iso, pn = TH[k]["isacord"], TH[k]["polyneon"]
        ci = GREEN if iso[3] < 3 else (ORANGE if iso[3] < 5.5 else RED); cp = GREEN if pn[3] < 3 else (ORANGE if pn[3] < 5.5 else RED)
        o.append(swatch(cx[0], y, k, 4.5, 2.8)); o.append(t(cx[1], y, PAL[k][1], 1.9, 600)); o.append(t(cx[2], y, HEX[k], 1.75, 400, MUTED))
        if k in RS: o.append(sw_hex(cx[3], y, RS[k])); o.append(t(cx[3] + 4.5, y, RS[k], 1.5, 400, MUTED))
        o.append(t(cx[4], y, f"{iso[0]} {iso[1]}"[:20], 1.75)); o.append(t(cx[5], y, f"{iso[3]:.1f}", 1.7, 600, ci))
        o.append(t(cx[6], y, f"{pn[0]} {pn[1]}"[:22], 1.75)); o.append(t(cx[7], y, f"{pn[3]:.1f}", 1.7, 600, cp))
        o.append(t(cx[8], y, "40", 1.75)); o.append(t(cx[9], y, PAL[k][2][:64], 1.55, 400, MUTED))
        o.append(t(cx[10], y, " / ".join(str(use[k].get(p, 0)) for p in PS), 1.7, 600))
    yb = 36 + len(rows) * rh + 2
    for i, l_ in enumerate([
        "ΔE2000 vs target: green < 3, amber 3-5.5, red > 5.5 - amber/red rows must be picked from the physical card (F1). All targets PROPOSED (read from the low-res render).",
        f"Foam white {HEX['w1']} is lighter + cooler than the render's lit foam ({RS.get('w1', '?')}); the close-up average incl. its shadows is ~{ECRU[0]} (warm ecru). Reviewer's Isacord 0151 Cloud is darker",
        "still (#BAAA9E); Polyneon 1801 is 'Barely Blue' (#E4E8FF) - a blue-white, NOT an ecru: do not use it. The F1 swatch sews both creams; pick on the real shell.",
        "!The SHELL COLOUR + hardware colour (and probably the rib) change from the render: every blue + both creams must be re-checked on the NEW shell before bulk."]):
        o.append(t(12, yb + i * 3.4, l_.lstrip("!"), 1.65, 700 if l_.startswith("!") else 600, RED if l_.startswith("!") else ORANGE))
    yb += 4 * 3.4 + 3
    o.append(t(12, yb, "TRIMS + CONSUMABLES (per jacket)", 2.2, 700))
    tr = [("Backing", "[proposed] 3.0 oz cutaway (navy / charcoal) + a 1.5 oz tearaway under the padded foam areas (or a 2nd cutaway layer), cut 30 larger than each hooping; trim to 5"),
          ("Topping", "none (canvas surface is firm); optional water-soluble topping on the foam if the loops sink - strike-off decides"),
          ("Needles", "75/11 sharp (canvas)"), ("Bobbin", "60wt navy polyester pre-wound (dark shell) - re-check on the new shell colour"),
          ("Frames", f"{FR_S} (factory.json{'' if PROF['frames_confirmed'] else ', PROPOSED'}): {HOOPS} hoopings per jacket at M (G6); a frame ≥ {max(CUR[p]['size_mm'][0] for p in PS)+30:.0f} × {max(CUR[p]['size_mm'][1] for p in PS)+30:.0f} sews every piece in one"),
          ("Patches / labels", "none on this garment - all artwork is direct embroidery")]
    for i, (a, b) in enumerate(tr):
        o.append(t(12, yb + 4.5 + i * 3.5, a, 1.8, 600)); o.append(t(38, yb + 4.5 + i * 3.5, b, 1.75))
    return o

def summary():
    o = hdr("STITCH SUMMARY + OPEN QUESTIONS", "Size M files. Every count read back from the DST (stitches, trims, stops, max stitch); threads from the PES.", "G4")
    hd = ["Element", "Piece", "Art box", "Stitches", "Trims", "Trims/10k", "Stops", "Threads", "Max stitch", "Hoops", "Run time (as hooped)"]
    cx = [12, 36, 76, 98, 116, 130, 146, 158, 172, 190, 204]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.75, 700, MUTED))
    for i, p in enumerate(PS):
        r = CUR[p]; b = (0, 0) + tuple(r["size_mm"]); y = 36 + i * 4.6
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
    qs = [f"1. Frame: pieces > {FRAME[0]-16:.0f} mm are split for {FR_S} (G6). The seam-true wrap carries art to every seam, so sleeves need 2 x 2 hoopings - a jacket-back frame removes the joins.",
          "2. Foam: production files = padded tatami + loop spiral + continuous curl cords + grey ridges. The F1 foam swatch also sews a moss / chenille look - chenille heads available?",
          "3. Thread board: 9 targets from a low-res render + an ecru foam candidate (G3). The SHELL colour + hardware change: re-check every thread on the new shell before bulk.",
          "4. Seamless wave (Rev B): stripes continue across every seam, art 3 mm short of each seam, match notches on both pieces (G7, 1:1 placement plot). No armhole topstitch.",
          "5. Body: Drum Island block, unchanged (founder). Cuff / hem rib probably change - re-check the hem (10) + cuff (10) keep-outs on the new rib [proposed].",
          "6. Grading (after the sample): A 92 % (XS-S) · B 100 % (M-XL) · C 108 % (XXL-3XL), one file per size per piece, re-clipped to each size's keep-outs. OK?",
          "7. Shell dye: piece-dyed + pre-washed shell assumed. If garment-washed after embroidery, wash-test the sew-out (cream foam!).",
          "8. Reference: traced from the low-res render (~1.4 mm/px) + the founder's shoulder close-up (registered, FL crest). Seam continuations are generated (G7), not traced.",
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
    notes = [("Stripes", ["6 blues as twisted cords: tatami rows at", "28° to the stripe (alternating per tone);", "turning satin only < 3 wide w/o holes;", "sub-2 mm render flecks dropped."]),
             ("Rope lines", ["continuous 2.4 mm cream cords (traced", "fragments joined), turning satin."]),
             ("Foam", ["grey hollows -> thin 1.1 mm grey ridges", "(rest of the hollow in shade), then the", "padded foam per curl, then ONE continuous", "spiral curl cord + loop spiral (shade)."]),
             ("Seams", ["stripes continue across every seam", "(join / taper / abut, G7); 3 mm short."]),
             ("Ties", ["3-stitch tie-on/off at every trim + colour", "change; max sewn stitch ≤ 7.5 mm;", f"≤ {FA.max_threads(PROF)} colours per file incl. registration."])]
    for a, ls in notes:
        o.append(t(bx, y2, a, 1.7, 700)); y2 += 3.0
        for l_ in ls: o.append(t(bx, y2, l_, 1.5)); y2 += 2.7
        y2 += 0.8
    y2 += 2
    o.append(t(bx, y2, "SEWING A SPLIT PIECE: see G6 (order, crosses,", 1.8, 700)); y2 += 3
    o.append(t(bx, y2, "hooping a cut panel, backing, foam).", 1.8, 700)); y2 += 4
    o.append(t(bx, y2, f"FOAM SWATCH (F1): {os.path.basename(SWT['file'])}.dst", 1.55, 700, ORANGE)); y2 += 2.8
    o.append(t(bx, y2, f"{SWT['stitches']:,} st · {SWT['trims']} trims · {SWT['size_mm'][0]:.0f} × {SWT['size_mm'][1]:.0f} mm · 1 hoop", 1.5, 400, ORANGE))
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
    y += 3
    o.append(t(12, y, "HOOPING ORDER + RE-REGISTRATION (review item 7)", 2.2, 700)); y += 4
    for P in PS:
        r = CUR[P]; ss = secs(r)
        if not ss: o.append(t(14, y, f"{P}: one hooping (full file).", 1.55)); y += 3; continue
        seen = []; parts = []
        for nm, s_ in ss.items():
            mk = [tuple(m) for m in s_.get("marks", [])]
            shared = [m for m in mk if any(abs(m[0] - q[0]) < 0.6 and abs(m[1] - q[1]) < 0.6 for q in seen)]
            parts.append(f"{nm.split('_')[0]}" + (f" (re-register on {len(shared)} cross{'es' if len(shared) != 1 else ''} at " + ", ".join(f"({m[0]:+.0f}, {m[1]:.0f})" for m in shared[:3]) + ")" if shared else " (first)"))
            seen += mk
        o.append(t(14, y, f"{P}: " + "  →  ".join(parts), 1.45)); y += 3
    y += 1.5
    o.append(t(12, y, "HOOPING A CUT PANEL + BACKING [proposed - the strike-off confirms]", 2.2, 700)); y += 4
    for l_ in ["• Chalk CF / CB, the split lines, the needle starts and the match notches on the cut piece from the 1:1 placement plot (out/placement, art placement only).",
               "• Hoop the BACKING only (adhesive-backed cutaway, or cutaway + temporary spray) and float the cut panel on it, aligned on the chalk marks; pin only inside the seam allowance.",
               "• Section 2+ : never clamp the hoop ring over foam that is already sewn (it crushes the padding) - float again on a freshly hooped backing, or use a magnetic frame.",
               "• Align each new hooping on the registration crosses its file shares with the previous one (above): the machine sews the crosses first - check they land on the sewn ones.",
               "• Backing for dense padded foam on 12 oz duck: 3.0 oz cutaway + 1.5 oz tearaway under the foam areas (or two cutaway layers). 2.5 oz alone is too light for this density.",
               "• No armhole topstitch (Rev B): the wave runs to 3 mm from the armhole seam on body + sleeve; press the seam open or to the body, do not topstitch over the art."]:
        o.append(t(14, y, l_, 1.5)); y += 3
    y += 1.5
    for i, l in enumerate(["Split lines are chosen where they cut the least art inside the frame; curls/drops under 70 mm go whole to one file, larger fills overlap 1.2 mm across the line.",
                           "Needle start = centre of each file's design (origin of the DST/PES). Registration crosses sew at the start of stop 1 in that stop's thread (factory: max 12 colours per file,",
                           "no separate basting colour); the next hooping re-registers on the crosses on its split line; pick them out after the last hooping. Machine time incl. trims + colour changes."]):
        o.append(t(12, y + i * 3.2, l, 1.55, 400, MUTED))
    return o

def seams_page():
    o = hdr("SEAM CONTINUITY + MATCH MARKS — the seamless wave (Rev B)",
            "Measured on the shipped DSTs (continuity.py): along every seam, art 1-3 mm inside each side's keep-out; meet = the other side also has art there (±2 mm), tone = same thread group (±4 mm).", "G7")
    hd = ["Seam", "Pieces (A / B)", "Length A / B mm", "Art on seam", "Meet", "Same tone", "Match marks", "Tone agrees"]
    cx = [12, 40, 66, 92, 110, 122, 138, 156]
    for x_, h in zip(cx, hd): o.append(t(x_, 31, h, 1.55, 700, MUTED))
    import wrap as WR
    y = 35.5
    for i, sm in enumerate(WR.seams("M")):
        nm = sm["name"]; c = CONT.get(nm, {}); m = MMK.get(nm)
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.2)}" width="160" height="3.0" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, nm, 1.45, 700)); o.append(t(cx[1], y, f"{sm['A'][0]} / {sm['B'][0]}" + (" (no seam)" if sm["kind"] == "internal" else ""), 1.4))
        o.append(t(cx[2], y, f"{sm['len_A']:.0f} / {sm['len_B']:.0f}", 1.4)); o.append(t(cx[3], y, f"{c.get('art_mm', 0)} mm", 1.4))
        mt = c.get("meet"); tn = c.get("tone")
        col = (lambda v: MUTED if v is None else (GREEN if v >= 85 else (ORANGE if v >= 70 else RED)))
        o.append(t(cx[4], y, "—" if mt is None else f"{mt} %", 1.45, 700, col(mt))); o.append(t(cx[5], y, "—" if tn is None else f"{tn} %", 1.45, 700, col(tn)))
        o.append(t(cx[6], y, f"{len(m['marks'])}" if m else "—", 1.45)); o.append(t(cx[7], y, f"{m['agree']}/{len(m['marks'])}" if m else "—", 1.45))
        y += 3.0
    y += 2
    for l_ in ["How the wave crosses a seam (wrap.py + seamfill.py, from each size's own pattern seams):",
               "• both sides are unrolled along the seam by SEAM LENGTH (the eased cap is matched fraction to fraction), art stops 3 mm short of the sew line on both pieces;",
               "• every stripe / rope line that crosses the seam on the side with more art continues straight on into the other piece at its own angle and tone: it JOINS a",
               "  stripe of the same tone there, or TAPERS to a point over 2.5 x its width (bare fabric ahead), or ABUTS the other piece's own art; then the other way round;",
               "• curls + drops are discrete raised motifs: moved whole out of a keep-out, never sliced; a curl that really crosses the armhole continues on the sleeve;",
               "• the sleeve centre line is not a seam: the back-view half and the front-view half are joined into one continuous trace (no fold line).",
               "!Seam continuations are GENERATED (the render shows each piece in a different view), not traced - listed here so the factory knows what was redrawn."]:
        o.append(t(12, y, l_.lstrip("!"), 1.5, 600 if l_.startswith("!") else 400, ORANGE if l_.startswith("!") else INK)); y += 2.9
    # match mark table (right)
    mx = 176; my = 31
    o.append(t(mx, my, "MATCH MARKS (notch on both pieces, mm along the seam from its top end)", 1.7, 700)); my += 3.6
    o.append(t(mx, my, "id", 1.35, 700, MUTED)); o.append(t(mx + 10, my, "on A", 1.35, 700, MUTED)); o.append(t(mx + 22, my, "on B", 1.35, 700, MUTED)); o.append(t(mx + 34, my, "tone A / B", 1.35, 700, MUTED))
    o.append(t(mx + 62, my, "id", 1.35, 700, MUTED)); o.append(t(mx + 72, my, "on A", 1.35, 700, MUTED)); o.append(t(mx + 84, my, "on B", 1.35, 700, MUTED)); o.append(t(mx + 96, my, "tone A / B", 1.35, 700, MUTED))
    my += 2.8; rows = [(mk, s_) for nm, s_ in MMK.items() for mk in s_["marks"]]; half = (len(rows) + 1) // 2
    nm_ = {k: v[1].split()[0] for k, v in WC.WV_PAL.items()}
    for j, (mk, s_) in enumerate(rows[:2 * 52]):
        col_ = 0 if j < min(half, 52) else 1; jj = j if col_ == 0 else j - min(half, 52); xx = mx + col_ * 62; yy = my + jj * 2.45
        bad = mk["tone_A"] != mk["tone_B"]
        o.append(t(xx, yy, mk["id"], 1.3, 700)); o.append(t(xx + 10, yy, f"{mk['s_A']:.0f}", 1.3)); o.append(t(xx + 22, yy, f"{mk['s_B']:.0f}", 1.3))
        o.append(t(xx + 34, yy, f"{nm_.get(mk['tone_A'], '-')} / {nm_.get(mk['tone_B'], '-')}", 1.25, 600 if bad else 400, ORANGE if bad else INK))
    if len(rows) > 104: o.append(t(mx, my + 52 * 2.45 + 2, f"+ {len(rows) - 104} more in out/placement/match_marks_M.json and on the plot", 1.3, 400, MUTED))
    # strips
    from PIL import Image
    im = Image.open("out/continuity_M.png"); w0 = im.width
    crop = im.crop((0, 0, w0, min(im.height, int(w0 * 0.42))))
    tag, hh = img_tag(crop, 12, y + 2, 160); o.append(tag)
    o.append(t(12, y + 2 + hh + 3, "First seams of out/continuity_M.png (all seams, rendered from the shipped DSTs; one sheet per seam in out/continuity_*.png): side A above, side B below, seam closed up.", 1.4, 400, MUTED))
    return o

def gates_page():
    o = hdr("FIDELITY GATES — LESSONS A14 (motif match) + A15 (coverage), shipped DSTs vs the mockup",
            "Reference = the mockup's own tone classes mapped into each piece with the art's map; garment details + keep-outs masked out (A15). One row per piece and motif family.", "G8")
    hd = ["Piece", "Family", "Render motifs", "DST motifs", "Pass", "Fail", "Moved > 3 mm (max)", "IoU median", "Uncovered ≥ 25 mm²", "Unexplained"]
    cx = [12, 26, 46, 68, 88, 100, 112, 142, 162, 196]
    for x_, h in zip(cx, hd): o.append(t(x_, 31, h, 1.55, 700, MUTED))
    y = 35.5; tot_fail = 0; tot_un = 0
    for i, r in enumerate(GATES["summary"]):
        P, fam = r["piece"], r["family"]; g = GATES["pieces"][P]
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.2)}" width="{SW-22}" height="3.0" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, P if fam == "curls" else "", 1.45, 700)); o.append(t(cx[1], y, fam, 1.45))
        o.append(t(cx[2], y, f"{r['motifs']}", 1.45)); o.append(t(cx[3], y, f"{g[fam].get('dst_count', '-')}", 1.45))
        o.append(t(cx[4], y, f"{r['passed']}", 1.45, 600, GREEN)); o.append(t(cx[5], y, f"{r['failed']}", 1.45, 700, RED if r["failed"] else MUTED))
        o.append(t(cx[6], y, f"{r['moved']} ({r['max_move']:.0f} mm)", 1.45)); o.append(t(cx[7], y, f"{r['iou_median']}", 1.45))
        tot_fail += r["failed"]
        if fam == "curls":
            un = g["uncovered"]; ue = [u for u in un if u["why"] == "UNEXPLAINED"]; tot_un += len(ue)
            o.append(t(cx[8], y, f"{len(un)} ({sum(u['area_mm2'] for u in un):.0f} mm²)", 1.45)); o.append(t(cx[9], y, f"{len(ue)}", 1.45, 700, RED if ue else GREEN))
        y += 3.0
    y += 2
    o.append(t(12, y, f"Result: {tot_fail} failing motif rows, {tot_un} unexplained bare areas — " + ("PASS" if not tot_fail and not tot_un else "see the rows above (each listed with position on the compare sheet)"), 2.0, 700, GREEN if not tot_fail and not tot_un else RED)); y += 5
    for l_ in ["Pass = qa.motif_match: IoU ≥ 0.70 and width + height each ≥ 80 % of the reference motif (a stand-in of the right size but the wrong silhouette fails).",
               "CURLS = cream + grey crests ≥ 100 mm² (one row per crest), DROPS = cream motifs 4-100 mm², STRIPES = the blue band regions (with their crests over them).",
               "Moved: the Rev B wrap moves art near seams on purpose (stretched to the seam, curls moved whole out of a keep-out); each reference motif is matched at its best",
               "  local shift within ±40 mm and the shift is reported. Uncovered (qa.uncovered): mockup-embroidered areas ≥ 25 mm² the DST leaves bare, each explained as",
               "  'keep-out edge' (inside 6 mm of the art limit) or 'moved by the wrap' (inside 45 mm of a seam, art present nearby) — anything else is UNEXPLAINED and blocks delivery.",
               "Per-piece tables with the positions of every failing / uncovered row: out/compare_<piece>.png (under the side-by-side) and gates_M.json."]:
        o.append(t(12, y, l_, 1.5)); y += 2.9
    return o

def f1_pages():
    import sheet as _SH; _SH.FOOT = SB.FOOT
    so = []
    for p in PS:
        r = CUR[p]
        for s in hoop_files(r):
            nm = os.path.basename(s["file"]); so.append(dict(file=nm + ".dst", piece=f"{p}" + ("" if s is r else " · " + nm.split("_M_")[-1]), stitches=s["stitches"], trims=s["trims"]))
    so.insert(0, dict(file=os.path.basename(SWT["file"]) + ".dst", piece="FOAM SWATCH (sew first)", stitches=SWT["stitches"], trims=SWT["trims"]))
    th = [dict(name=PAL[k][1], code=f"Isacord {SB.TH[k]['isacord'][0]} / Polyneon {SB.TH[k]['polyneon'][0]}", de=min(SB.TH[k]["isacord"][3], SB.TH[k]["polyneon"][3])) for k in WC.WV_KEYS]
    pcs = [dict(piece=f"01 {p} {PC.NAME[p]}", w=CUR[p]["size_mm"][0], h=CUR[p]["size_mm"][1], hoopings=CUR[p]["hoopings"]) for p in PS]
    pages = FA.requests_page(WC.NAME, so, th, pcs, page="F1", prof=PROF)
    # Rev B additions appended to F1 (right column)
    lines = [("5  Foam swatch - sew FIRST", 1), (f"{os.path.basename(SWT['file'])}.dst ({SWT['stitches']:,} st, {SWT['trims']} trims, 1 hooping)", 0),
             ("sews one crest 4 times: A padded + loops (production), B moss /", 0), ("chenille look, C = A and D = B in the ecru candidate (#D3CAC1).", 0),
             ("Real chenille heads? Then the FM outlines (ART.svg) are the", 0), ("chenille regions - please quote both ways.", 0), ("", 0),
             ("6  Full files are reference only", 1), ("Sew and price the HOOPING files listed in 1 (split sections).", 0),
             ("The 5 full files (one per piece) are for checking only.", 0), ("", 0),
             ("7  Backing + hooping (G6)", 1), ("Dense padded foam on 12 oz duck: we propose 3.0 oz cutaway +", 0),
             ("1.5 oz tearaway under the foam. Float the cut panel on hooped", 0), ("backing; never clamp a hoop over sewn foam. Tell us your way.", 0), ("", 0),
             ("8  New shell colour", 1), ("Shell + hardware colour (and probably the rib) change from the", 0),
             ("render: dip / card every thread on the NEW shell; re-check the", 0), ("hem + cuff keep-outs on the new rib.", 0), ("", 0),
             ("9  Seam match marks", 1), ("Notch the match marks (1:1 placement plot) on both pieces; the", 0),
             ("stripes must meet across armhole, side, shoulder + underarm.", 0), ("No armhole topstitch.", 0)]
    extra = "".join(f'<text x="168" y="{40 + i*4.0:.1f}" font-family="{_SH.FONT}" font-size="{2.6 if h else 2.2}" font-weight="{700 if h else 400}" fill="{ORANGE}">{l}</text>' for i, (l, h) in enumerate(lines))
    return [pg.replace("</svg>", extra + "</svg>") for pg in pages]

def build():
    pages = {"G1": None, "G2": overview(), "G3": threads(), "G4": summary(), "G5": files_page(), "G6": hooping_page(), "G7": seams_page(), "G8": gates_page()}
    el = [("01 Wave (element spec)", SPEC[0])]
    index = [("G1 Cover + contents", 1), ("G2 Placement overview", 2), ("G3 Thread + trim summary", 3), ("G4 Stitch summary + open questions", 4),
             ("G5 Production stitch files + hoop splits", 5), ("G6 Hooping table, order, backing", 6), ("G7 Seam continuity + match marks", 7), ("G8 Fidelity gates (A14 / A15)", 8)]
    pg = 9
    for name, path in el:
        n = len(PdfReader(path).pages); index.append((name + f" ({n} pp)", pg)); pg += n
    index.append(("F1 Factory requests", pg))
    pages["G1"] = cover(index)
    w = PdfWriter()
    for k in ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"):
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
