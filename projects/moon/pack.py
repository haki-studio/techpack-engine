"""Embroidery pack G1–G5 + element specs -> out/HAKI_moon_EMBROIDERY-PACK_RevC.pdf.
All counts from out/results/all.json (DST/PES read-back); stitches per thread colour counted from the PES files."""
import os, json, glob, pickle, collections
import cairosvg
import pyembroidery as pe
from PIL import Image
from shapely.ops import unary_union
from pypdf import PdfWriter, PdfReader
import moonpal
from sheet import t, swatch, doc, INK, MUTED, RED, ORANGE, GUIDE, GREEN, SW, SH
from render import f
from motifs2 import HEX, PAL
import tech, specbase as SB
from specbase import img_tag
import drum, emb_place as EP, moonstitch as MS, factory, readback, sheet as _SH
import techflat as TF

REV = "Rev C"; DATE = "19 Oct 2026"
SB.FOOT = f"HAKI STUDIOS · Drum Island jacket · moon · EMBROIDERY · {REV} · {DATE}"; _SH.FOOT = SB.FOOT
PROF = factory.load()
def hours(r): return factory.machine_hours(r["stitches"], PROF, trims=r["trims_dst"], colour_changes=max(0, r["stops"] - 1))
def hoopings(k, r):
    if k == "back": return len(M["splits"]["sections"])
    return len(r["sections"]) if "sections" in r else 1
ALL = json.load(open("out/results/all.json")); M = ALL["sizes"]["M"]; B = ALL["grades"]["B"]
CLR = json.load(open("out/results/clearances.json"))
A = pickle.load(open("art_M.pkl", "rb")); G = pickle.load(open("art_graded.pkl", "rb"))
ELEMENTS = [("01", "Back scene + placeholder", "back", "back panel B01", M["back"]),
            ("01b", "Moon-in-box (before figure)", "moonbox", "B01, inside the box", M["moonbox"]),
            ("02", "Chest clouds", "02R", "wearer's right front F02", B["02R"]), ("02", "Chest clouds", "02L", "wearer's left front F01", B["02L"]),
            ("03", "Lower front pole + wires", "03L", "wearer's left front F01", M["03L"]), ("03", "Lower front wires", "03R", "wearer's right front F02", M["03R"]),
            ("04", "Sleeve clouds", "04R", "right sleeve S01", B["04R"]), ("04", "Sleeve clouds", "04L", "left sleeve S02", B["04L"])]
# every per-file number on G1-G5 / cover / F1 from the DST read-back (LESSONS B20) — the same numbers T15 prints
def _rb(r):
    b = readback.dst(r["file"] + ".dst"); return dict(r, stitches=b["stitches"], trims_dst=b["trims"], stops=b["stops"], max_stitch=b["max_stitch"])
ELEMENTS = [(e, nm, k, pc, _rb(r)) for e, nm, k, pc, r in ELEMENTS]
OUT_PDF = "out/HAKI_moon_EMBROIDERY-PACK_RevC.pdf"
HEX2KEY = {v[0].upper(): k for k, v in PAL.items()}

def per_colour(base):
    """stitches per thread colour, counted from the PES file"""
    p = pe.read(base + ".pes"); cols = [t_.hex_color().upper() for t_ in p.threadlist]; ci = 0; out = collections.Counter()
    for x, y, c in p.stitches:
        k = c & pe.COMMAND_MASK
        if k == pe.COLOR_CHANGE: ci += 1
        elif k == pe.STITCH: out[cols[min(ci, len(cols) - 1)]] += 1
    return out

def hdr(title, sub, page): return SB.header(title, sub, page)

def cover(index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>']
    o.append(t(14, 24, "HAKI STUDIOS", 3.0, 700, MUTED)); o.append(t(14, 36, "Drum Island jacket · moon — embroidery", 7.0, 700))
    o.append(t(14, 44, f"{REV} · {DATE} · Drum Island pattern, size M base · 4 elements (+ 01b moon-in-box), 7 pieces · ≤ 12 threads per file · all dimensions mm", 2.6, 400, MUTED))
    o.append(f'<line x1="14" y1="48" x2="{SW-14}" y2="48" stroke="{INK}" stroke-width="0.4"/>')
    tag, h = img_tag(Image.open("cover_front.png"), 14, 54, 90); o.append(tag); o.append(t(14, 54 + h + 3.5, "FRONT", 2.2, 700))
    tag, h2 = img_tag(Image.open("cover_back.png"), 108, 54, 90); o.append(tag); o.append(t(108, 54 + h2 + 3.5, "BACK (pink box = licensed-figure placeholder)", 2.2, 700))
    ix = 204; o.append(t(ix, 58, "CONTENTS", 2.8, 700)); y = 64
    for name, pg in index: o.append(t(ix, y, name, 2.0)); o.append(t(SW - 14, y, f"{pg}", 2.0, 600, MUTED, "end")); y += 4.2
    y += 4; o.append(t(ix, y, "TOTALS, SIZE M (from the DST files)", 2.4, 700)); y += 5
    tot = sum(e[4]["stitches"] for e in ELEMENTS); trims = sum(e[4]["trims_dst"] for e in ELEMENTS)
    hp = sum(hoopings(e[2], e[4]) for e in ELEMENTS if e[2] != "moonbox") + 1
    for a, b in [("Stitches per jacket", f"{tot:,}"), ("Trims per jacket", f"{trims:,}"), ("Hoopings per jacket", f"{hp} on {factory.largest_frame(PROF)[0]:.0f}² frames (01b in the box hooping)"),
                 ("Machine time / jacket", f"≈ {sum(hours(e[4]) for e in ELEMENTS):.1f} h ({PROF['spm']} spm + trims + changes)"), ("Threads", "12 per file (14-tone palette, 40wt poly)")]:
        o.append(t(ix, y, a, 2.0, 400, MUTED)); o.append(t(SW - 14, y, b, 2.0, 600, INK, "end")); y += 4
    y += 3; o.append(t(ix, y, "Licensed figure on the pole: placeholder box only —", 1.9, 700, RED)); o.append(t(ix, y + 3.4, "licence confirmed by client 2026-10-16; factory adds", 1.9, 400)); o.append(t(ix, y + 6.8, "the figure from the licensor-approved art (G4).", 1.9, 400))
    o.append(t(SW - 14, SH - 8, SB.FOOT, 1.9, 400, MUTED, "end"))
    return o

def overview():
    o = hdr("G2 · PLACEMENT OVERVIEW — every element on the garment", "Garment coords. Front: x from CF (+ = wearer's left), y down from CF neck seam. Back: x from CB, y down from CB neck seam. Sleeves: S01/S02 pattern coords. Tolerance ±2, rotation ±3°.", "G2")
    F = TF.Flat("M"); b = TF.bounds_front(F); ppm = 3.0
    fr = Image.open("cover_front.png"); w = 120; s = w / (b[2] - b[0] + 20); ax, ay = 12, 30
    tag, h = img_tag(fr, ax, ay, w); o.append(tag)
    X = lambda x: ax + (x - b[0] + 10) * s; Y = lambda y: ay + (y - b[1] + 10) * s
    pl = EP.place("M")[0]
    for k in ("02R", "02L", "03L", "03R"):
        bb = pl[k][1].bounds; y0 = bb[1] + F.fnd; y1 = bb[3] + F.fnd
        o.append(f'<rect x="{f(X(bb[0]))}" y="{f(Y(y0))}" width="{f((bb[2]-bb[0])*s)}" height="{f((y1-y0)*s)}" fill="none" stroke="{RED}" stroke-width="0.3" stroke-dasharray="1.2 0.8"/>')
        o.append(f'<circle cx="{f(X(bb[0]))}" cy="{f(Y(y0))}" r="2.6" fill="{RED}"/>' + t(X(bb[0]), Y(y0) + 0.8, k, 1.4, 700, "#FFFFFF", "middle"))
    o.append(t(ax, ay + h + 3.5, "FRONT (04 sleeve clouds indicative on the flat sleeves; exact on T13 / element 04)", 1.8, 700))
    bx_ = 138; tag, hb = img_tag(Image.open("cover_back.png"), bx_, ay, w); o.append(tag)
    BX = lambda x: bx_ + (x - b[0] + 10) * s
    for k, lab in (("back", "01"), ("box", "LF")):
        bb = pl[k][1].bounds; y0 = bb[1] + F.bnd; y1 = bb[3] + F.bnd
        o.append(f'<rect x="{f(BX(bb[0]))}" y="{f(Y(y0))}" width="{f((bb[2]-bb[0])*s)}" height="{f((y1-y0)*s)}" fill="none" stroke="{RED}" stroke-width="0.3" stroke-dasharray="1.2 0.8"/>')
        o.append(f'<circle cx="{f(BX(bb[0]))}" cy="{f(Y(y0))}" r="2.6" fill="{RED}"/>' + t(BX(bb[0]), Y(y0) + 0.8, lab, 1.6, 700, "#FFFFFF", "middle"))
    o.append(t(bx_, ay + hb + 3.5, "BACK — LF = licensed-figure placeholder box (factory insert)", 1.8, 700))
    tx = 262; o.append(t(tx, 31, "ART BOXES (M)", 2.1, 700)); y = 35.5
    for k in ("back", "box", "02R", "02L", "03L", "03R", "04R", "04L"):
        bb = pl[k][1].bounds
        o.append(t(tx, y, f"{k}  {bb[2]-bb[0]:.0f}×{bb[3]-bb[1]:.0f}", 1.6, 600)); y += 2.9
        o.append(t(tx + 2, y, f"x {bb[0]:+.0f}…{bb[2]:+.0f} · y {bb[1]:.0f}…{bb[3]:.0f}", 1.45, 400, MUTED)); y += 3.6
    ky = 122
    o.append(t(12, ky, "KEEP-OUTS (all elements, every size — checked on that size's pattern, T13)", 2.1, 700))
    ko = ["CF zip 15 each side · armhole + shoulder 15 · side seams 15 · hem-rib seam 10 (rib never embroidered) · welt box 6 · collar lying flat 6.",
          "Sleeves: cap seam + underarm seam 15, cuff seam 10.",
          "Exception — WIRES: bean lines run to 3 mm from the side seam on BOTH back and front and meet at the same height above the hem seam",
          "(match marks = side-seam notches, listed per size on T13). Wires crossing the CF zip stop 15 each side on the same curve.",
          "Licensed-figure box: nothing of ours is stitched inside it; its outline is run in Moon cream (covered by 01b) to mark it for the factory insert."]
    for i, k in enumerate(ko): o.append(t(12, ky + 4.4 + i * 3.4, k, 1.75))
    y = ky + 4.4 + len(ko) * 3.4 + 3
    res = []
    for sz in drum.SIZES:
        c = CLR[sz]; bad = EP.failures(c); res.append(f"{sz}: {'pass' if not bad else 'FAIL'} · wires {c['wrap']['aligned']}/{c['wrap']['total']}")
    o.append(t(12, y, "Per size: " + "   ".join(res), 1.75, 700, GREEN if all("pass" in r for r in res) else RED))
    return o

def threads():
    o = hdr("G3 · THREAD + TRIM SUMMARY", "14-tone palette from the close-ups; every file ≤ 12 colours (manufacturer): violet → periwinkle, pole light grey → cloud white-pink. Approve a thread board before sampling.", "G3")
    use = {k: collections.Counter() for k in PAL}
    for e, nm, k, piece, r in ELEMENTS:
        for hx, n in per_colour(r["file"]).items():
            key = HEX2KEY.get(hx)
            if key: use[key][k] += n
    keys = [k for k in moonpal.ORDER]
    hd = ["", "Thread", "Hex", "Isacord", "ΔE", "Madeira Polyneon", "ΔE", "Wt", "Used for", "Pieces", "Stitches (M)"]
    cx = [12, 18, 46, 60, 88, 96, 130, 138, 146, 214, 262]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.75, 700, MUTED))
    TH = SB.TH; rh = 5.0
    for i, k in enumerate(keys):
        y = 36 + i * rh
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3.2)}" width="{SW-22}" height="{f(rh)}" fill="#F5F2EC"/>')
        iso, pn = TH[k]["isacord"], TH[k]["polyneon"]
        ci = GREEN if iso[3] < 3 else (ORANGE if iso[3] < 5.5 else RED); cp = GREEN if pn[3] < 3 else (ORANGE if pn[3] < 5.5 else RED)
        o.append(swatch(cx[0], y, k, 4.5, 2.8)); o.append(t(cx[1], y, PAL[k][1], 1.85, 600)); o.append(t(cx[2], y, HEX[k], 1.7, 400, MUTED))
        o.append(t(cx[3], y, f"{iso[0]} {iso[1]}"[:22], 1.7)); o.append(t(cx[4], y, f"{iso[3]:.1f}", 1.7, 600, ci))
        o.append(t(cx[5], y, f"{pn[0]} {pn[1]}"[:24], 1.7)); o.append(t(cx[6], y, f"{pn[3]:.1f}", 1.7, 600, cp))
        o.append(t(cx[7], y, "40", 1.7)); o.append(t(cx[8], y, PAL[k][2][:44], 1.65, 400, MUTED))
        mg = moonpal.FILE_MERGE.get(k)
        o.append(t(cx[9], y, (", ".join(sorted(use[k])) or "—") if not mg else f"merged → {PAL[mg][1]} in every file", 1.65, 400 if not mg else 600, INK if not mg else ORANGE)); o.append(t(cx[10], y, f"{sum(use[k].values()):,}", 1.7, 600))
    y = 36 + len(keys) * rh
    o.append(t(cx[1], y, "No separate basting thread (12-colour limit): registration crosses run in Pole grey, the placeholder outline in Moon cream — both picked out / covered after sewing.", 1.7, 600))
    yb = y + 6
    o.append(t(12, yb, "ΔE2000 vs target: green < 3, amber 3–5.5, red > 5.5 — red rows (moon taupe, cloud lavender on Polyneon) must be picked from the physical card. Stitch counts per colour read from the PES files.", 1.75, 400, MUTED))
    o.append(t(12, yb + 7, "TRIMS + CONSUMABLES (per jacket)", 2.2, 700))
    ab = unary_union([r["geom"] for r in A["back"]]).bounds
    tr = [("Backing", "2.5 oz cutaway, black/navy (dark ground), cut 30 larger than each art box; trim to 5 from stitching after embroidery"),
          ("Topping", "none (canvas surface is firm)"), ("Needles", "75/11 sharp (canvas)"), ("Bobbin", "60wt polyester, navy (dark ground) pre-wound"),
          ("Frames", f"01 back: border frame ≥ {ab[2]-ab[0]+14:.0f} × {ab[3]-ab[1]+14:.0f} (M, single file) or the 360² split files (G5); 04 sleeves: split per the frame (G5); 02/03: 360²"),
          ("Patches / labels", "none on this garment — all artwork is direct embroidery")]
    for i, (a, b) in enumerate(tr): o.append(t(12, yb + 11.5 + i * 3.6, a, 1.8, 600)); o.append(t(42, yb + 11.5 + i * 3.6, b, 1.8))
    return o

EMB_Q = ["1. Licensed figure: licence confirmed by client 2026-10-16. Placeholder box 68 × 79 mm (M) = mockup figure + 3 mm, on the pole top, centred on CB;",
         "    nothing of ours inside it. Moon-in-box: Haki supplies 01b (our moon fill in the box) [proposed — confirm]; the factory digitizer adds the figure on top.",
         "2. Rev C is FIDELITY-FIRST (client direction 2026-10-16): art traced from the close-ups at production density; stitch count, trims, density and run time",
         "    are reported, not limited. Clean-up (density, trims, stops) after the size-M sew-out — see F1.",
         "3. Grading: A 92 % (XS–S), B 100 % (M–XL), C 108 % (XXL–3XL) for motifs; 01 back + 03 lower fronts one file per size (wires meet the side seams).",
         "4. Wires wrap back ↔ front across the SIDE SEAMS only (mockup draws them over the hanging sleeves); side seams not topstitched — confirm (Q3, client).",
         "5. Front: two hoopings per panel (02 chest clouds, then 03 pole/wires) — the full front art is taller than the frame.",
         "6. Thread board: rows with ΔE > 3 (F1) — pick from the physical card; closer Isacord / Polyneon alternative listed per thread.",
         "7. Frames + machines from factory.json (unconfirmed): back = 6 hoopings (moon + box whole, pole whole); sleeves 2 each.",
         "8. Wash: if garment-washed after embroidery, run a wash test on the sew-out (cream moon + white-pink caps grey first).",
         "9. DST/PES are production-intent drafts: the factory digitizer opens them, checks density + pull on 12 oz duck and edits before sew-out."]

def summary():
    o = hdr("G4 · STITCH SUMMARY + OPEN QUESTIONS", "", "G4")
    hd = ["Element", "Piece", "Art box", "Stitches", "Trims", "Stops", "Threads", "Hoop.", "Machine h", "Width check"]
    cx = [12, 62, 104, 126, 144, 156, 168, 180, 192, 214]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.8, 700, MUTED))
    sums = {e: json.load(open(glob.glob(f"out/{e}_*/summary.json")[0])) for e in ("01", "02", "03", "04")}
    for i, (e, nm, k, piece, r) in enumerate(ELEMENTS):
        y = 36 + i * 4.6
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3)}" width="{SW-22}" height="4.6" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, f"{e} {nm}"[:40], 1.8, 600)); o.append(t(cx[1], y, f"{k} · {piece}"[:30], 1.7))
        o.append(t(cx[2], y, f"{r['size'][0]:.0f} × {r['size'][1]:.0f}", 1.75)); o.append(t(cx[3], y, f"{r['stitches']:,}", 1.75, 600))
        o.append(t(cx[4], y, f"{r['trims_dst']:,}", 1.75)); o.append(t(cx[5], y, f"{r['stops']}", 1.75)); o.append(t(cx[6], y, f"{r['threads']}", 1.75))
        o.append(t(cx[7], y, f"{hoopings(k, r)}", 1.75)); o.append(t(cx[8], y, f"{hours(r):.2f}", 1.75))
        w = sums[e[:2]]["width"]; wk = max(w, key=lambda q: w[q]); wv = w[wk]
        o.append(t(cx[9], y, "all codes pass" if wv < 1 else f"worst {wk} {wv:.1f}% (short tips)", 1.7, 600, GREEN if wv < 1 else ORANGE))
    y = 36 + len(ELEMENTS) * 4.6 + 1
    tot = sum(e[4]["stitches"] for e in ELEMENTS); tr = sum(e[4]["trims_dst"] for e in ELEMENTS)
    o.append(t(cx[2], y, "TOTAL", 1.9, 700)); o.append(t(cx[3], y, f"{tot:,}", 1.9, 700)); o.append(t(cx[4], y, f"{tr:,}", 1.9, 700)); o.append(t(cx[8], y, f"{sum(hours(e[4]) for e in ELEMENTS):.1f} h", 1.9, 700))
    o.append(t(12, y + 4.5, f"Size M (01, 03 per size) / grade B (02, 04). Counts from the DST read-back (LESSONS B8/B20). Machine h = factory.machine_hours at {PROF['spm']} spm + 6 s/trim + 4 s/colour change, one head, excl. hooping.", 1.7, 400, MUTED))
    o.append(t(12, y + 8, "Stops include the placeholder basting stop (01). Max stitch ≤ 7.5 mm and ≤ 12 thread colours in every file (factory.check_threads) (gate checked on all 7 sizes + 3 grades + every split file).", 1.7, 400, MUTED))
    qy = y + 16; o.append(t(12, qy, "OPEN QUESTIONS — embroidery (confirm before sampling)", 2.6, 700))
    for i, q in enumerate(EMB_Q): o.append(t(12, qy + 5 + i * 3.6, q, 1.85))
    return o

def files_page():
    o = hdr("G5 · PRODUCTION STITCH FILES + HOOP SPLITS", "DST (Tajima) + PES. Counts read back from the files; trims from the DST. Origin = centre of each file's design (= the ⊕ on the pattern). Thread chart .txt next to every file.", "G5")
    o.append(t(12, 31, "01 BACK + 03 LOWER FRONTS — one file per size (wires re-run to that size's side seams)", 2.0, 700))
    hd = ["Size", "Art", "01 back mm", "Stitches", "Trims", "Stops", "03L st / tr", "03R st / tr", "Frame splits (stitches · all fit)"]; cx = [12, 22, 30, 52, 68, 80, 92, 116, 138]
    for x_, h in zip(cx, hd): o.append(t(x_, 35.5, h, 1.55, 700, MUTED))
    y = 39.5
    for i, sz in enumerate(drum.SIZES):
        r = ALL["sizes"][sz]; b_ = r["back"]
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.7)}" width="{SW-22}" height="3.8" fill="#F5F2EC"/>')
        o.append(t(cx[0], y, sz, 1.55, 700)); o.append(t(cx[1], y, EP.GRADE[sz][0], 1.55, 700, RED))
        o.append(t(cx[2], y, f"{b_['size'][0]:.0f} × {b_['size'][1]:.0f}", 1.5)); o.append(t(cx[3], y, f"{b_['stitches']:,}", 1.5))
        o.append(t(cx[4], y, f"{b_['trims_dst']}", 1.5)); o.append(t(cx[5], y, f"{b_['stops']}", 1.5))
        o.append(t(cx[6], y, f"{r['03L']['stitches']:,} / {r['03L']['trims_dst']}", 1.5)); o.append(t(cx[7], y, f"{r['03R']['stitches']:,} / {r['03R']['trims_dst']}", 1.5))
        secs = r["splits"]["sections"]
        o.append(t(cx[8], y, f"{r['splits']['grid'][0]}×{r['splits']['grid'][1]}: " + " · ".join(f"{v['stitches']/1000:.0f}k" for v in secs.values()) + ("  ✓" if all(v["fits"] for v in secs.values()) else "  CHECK") + f"  · box in {r['splits']['box_section'][:40]}", 1.45))
        y += 3.8
    y += 3; o.append(t(12, y, "02 CHEST + 04 SLEEVE CLOUDS — one file per art grade: A = XS–S (92 %), B = M–XL (100 %), C = XXL–3XL (108 %)", 2.0, 700)); y += 4.5
    hd = ["Piece", "A stitches / trims", "B stitches / trims", "C stitches / trims", "Stops", "Hoopings (B)"]; cx2 = [12, 30, 62, 94, 126, 138]
    for x_, h in zip(cx2, hd): o.append(t(x_, y, h, 1.55, 700, MUTED))
    y += 4
    for i, k in enumerate(("02R", "02L", "04R", "04L")):
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-2.7)}" width="168" height="3.8" fill="#F5F2EC"/>')
        o.append(t(cx2[0], y, k, 1.55, 700))
        for j, G_ in enumerate("ABC"):
            r = ALL["grades"][G_][k]; o.append(t(cx2[1 + j], y, f"{r['stitches']:,} / {r['trims_dst']}", 1.5))
        rb = ALL["grades"]["B"][k]; o.append(t(cx2[4], y, f"{rb['stops']}", 1.5))
        o.append(t(cx2[5], y, ("2 × 360²: " + " · ".join(f"{v['size'][0]:.0f}×{v['size'][1]:.0f}" for v in rb["sections"].values())) if "sections" in rb else "1 × 360²", 1.45))
        y += 3.8
    y += 3; o.append(t(12, y, "WHAT IS DIGITIZED", 2.0, 700)); y += 4.2
    notes = [("Density", "production density everywhere (tatami 0.45, satin 0.42) — Rev C fidelity first; DST mm/mm² per code on each element p3."),
             ("Travel", "hidden travel under later fills + underpath (engine PR #1); trims only where a move is exposed (> 2.5 mm)."),
             ("Wires", "satin cord 1.6 mm with a wrap at each insulator; ends 3 mm short of every side seam (both pieces), 15 from CF."),
             ("Placeholder", "01 last stop = outline of the licensed-figure box in Moon cream (covered by 01b moon-in-box); nothing else inside it."),
             ("Ties / max", "3-stitch tie-on/off at every trim + colour change; max stitch < 7.5 mm (read back); ≤ 12 colours per file.")]
    for a, b_ in notes: o.append(t(12, y, a, 1.55, 700)); o.append(t(34, y, b_, 1.5)); y += 3.3
    # split diagram M
    bk = Image.open("cover_back.png"); F = TF.Flat("M"); b = TF.bounds_front(F)
    bx, by, bw = 186, 112, 100; tag, bh = img_tag(bk, bx, by, bw); o.append(tag)
    s_ = bw / (b[2] - b[0] + 20); X = lambda x: bx + (x - b[0] + 10) * s_; Y = lambda y_: by + (y_ + F.bnd - b[1] + 10) * s_
    sp = M["splits"]
    for nm, v in sp["sections"].items():
        bb = v["bbox"]
        o.append(f'<rect x="{f(X(bb[0]))}" y="{f(Y(bb[1]))}" width="{f((bb[2]-bb[0])*s_)}" height="{f((bb[3]-bb[1])*s_)}" fill="none" stroke="#0A84FF" stroke-width="0.3"/>')
        cxm, cym = X((bb[0] + bb[2]) / 2), Y((bb[1] + bb[3]) / 2)
        o.append(f'<circle cx="{f(cxm)}" cy="{f(cym)}" r="2.6" fill="#0A84FF"/>' + t(cxm, cym + 0.9, nm[:2], 1.8, 700, "#FFFFFF", "middle"))
        for m in v["marks"]:
            mx, my = X(m[0]), Y(m[1]); o.append(f'<path d="M{f(mx-1.4)} {f(my)} H{f(mx+1.4)} M{f(mx)} {f(my-1.4)} V{f(my+1.4)}" stroke="#00A3FF" stroke-width="0.45"/>')
    for x_ in sp["xs"]: o.append(f'<line x1="{f(X(x_))}" y1="{f(Y(100))}" x2="{f(X(x_))}" y2="{f(Y(590))}" stroke="{RED}" stroke-width="0.3" stroke-dasharray="1.5 0.8"/>')
    for y_ in sp["ys"]: o.append(f'<line x1="{f(X(-305))}" y1="{f(Y(y_))}" x2="{f(X(305))}" y2="{f(Y(y_))}" stroke="{RED}" stroke-width="0.3" stroke-dasharray="1.5 0.8"/>')
    o.append(t(bx, by - 2, "Size M back splits: blue = each file's extent, + = basting crosses, red = split lines", 1.5, 700))
    sy0 = 118; sx0 = 12
    o.append(t(sx0 + 120, 31 + 0, "", 1))
    steps = ["SEWING THE SPLIT BACK (no border frame)",
             "1. Mark CB + the split lines on the cut back (chalk), from the pattern (B01) — x / y per size on 01 p6.",
             "2. Hoop S1. Stop 1 = basting crosses. Sew S1.",
             "3. Re-hoop for the next section; align the needle on the crosses it shares; sew its",
             "    crosses over them (check), then the art. Order S1 → Sn (top row, then bottom).",
             "4. Fills crossing a split overlap 1.2 mm; motif clusters < 70 mm go whole to one section.",
             "5. The placeholder outline is basted in the section(s) listed above; remove basting + trim backing at the end.",
             "Every size has its own split set (by-size/<size>/splits): 3 × 2, moon + box whole in S2, pole whole in S5."]
    for i, st_ in enumerate(steps): o.append(t(12, y + 3 + i * 3.1, st_, 1.5, 700 if i == 0 else 400))
    return o

def f1_pages():
    so = []
    for e, nm, k, piece, r in ELEMENTS:
        so.append(dict(file=os.path.basename(r["file"]) + ".dst", piece=f"{e} {piece}", stitches=r["stitches"], trims=r["trims_dst"]))
    th = []
    for k in moonpal.ORDER:
        iso, pn = SB.TH[k]["isacord"], SB.TH[k]["polyneon"]
        best = min((("Isacord", iso), ("Polyneon", pn)), key=lambda q: q[1][3])
        other = pn if best[0] == "Isacord" else iso
        th.append(dict(name=f"{PAL[k][1]} {HEX[k]}", code=f"{best[0]} {best[1][0]} (alt. {'Polyneon' if best[0] == 'Isacord' else 'Isacord'} {other[0]} ΔE {other[3]:.1f})", de=best[1][3]))
    ab = M["back"]["size"]
    pcs = [dict(piece="01 back (moon, clouds, pole, wires)", w=ab[0], h=ab[1], hoopings=len(M["splits"]["sections"]))]
    for k in ("04R", "04L"):
        r = B[k]; pcs.append(dict(piece=f"04 sleeve clouds {k}", w=r["size"][0], h=r["size"][1], hoopings=len(r.get("sections", {})) or 1))
    return factory.requests_page("Drum Island jacket — Moon (HK-JK-DRUM-MOON)", so, th, pcs, page="F1", prof=PROF)

def build():
    pages = {"G2": overview(), "G3": threads(), "G4": summary(), "G5": files_page()}
    el = [("01 Back scene", glob.glob("out/01_back-scene/*SPEC_RevC.pdf")[0]), ("02 Chest clouds", glob.glob("out/02_*/*SPEC_RevC.pdf")[0]),
          ("03 Lower front pole + wires", glob.glob("out/03_*/*SPEC_RevC.pdf")[0]), ("04 Sleeve clouds", glob.glob("out/04_*/*SPEC_RevC.pdf")[0])]
    index = [("G1 Cover + contents", 1), ("G2 Placement overview", 2), ("G3 Thread + trim summary", 3), ("G4 Stitch summary + open questions", 4), ("G5 Production stitch files + hoop splits", 5), ("F1 Factory requests", 6)]
    pg = 7
    for name, path in el:
        n = len(PdfReader(path).pages); index.append((name + f" ({n} pp)", pg)); pg += n
    pages["G1"] = cover(index)
    w = PdfWriter()
    for k in ("G1", "G2", "G3", "G4", "G5"):
        svg = doc(pages[k]); cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"out/_{k}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"out/prev_{k}.png", output_width=2400)
        w.append(PdfReader(f"out/_{k}.pdf"))
    for svg in f1_pages():
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to="out/_F1.pdf"); cairosvg.svg2png(bytestring=svg.encode(), write_to="out/prev_F1.png", output_width=2400)
        w.append(PdfReader("out/_F1.pdf"))
    for name, path in el: w.append(PdfReader(path))
    w.write(OUT_PDF); print("embroidery pack pages", pg - 1, OUT_PDF)
    return index

if __name__ == "__main__":
    build()
