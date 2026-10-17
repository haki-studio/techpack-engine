"""Embroidery pack for the Keep Clean Our Space jacket: G1-G6, element specs E01-E05, stop sequences S1-S2, region table
R1, F1 factory requests -> out/HAKI_KCOS_EMBROIDERY-PACK_RevA.pdf. Every count is read back from the DST files
(dst_current.json / dst_all.json, refreshed by make_current.py from readback.dst)."""
import kccore
import os, json, pickle, glob, math
import numpy as np
import cairosvg
from PIL import Image
from shapely.ops import unary_union
from shapely.geometry import box
from pypdf import PdfWriter, PdfReader
import sheet as SHT
from sheet import t, swatch, doc, dim_h, dim_v, INK, MUTED, RED, ORANGE, GUIDE, GREEN, SW, SH
from render import f, geom_to_path
from motifs2 import HEX, PAL
import tech, stitchrender as SR, qa
import specbase as SB
from specbase import img_tag
import front as F, sleeve as SV, factory as FA, mockmap as MM
import kcdoc as KD
from kcdoc import PROF, FRAME, FR_S, mh
dst2 = kccore.patch_dst2()

REV, DATE = kccore.REV_EMB, kccore.DATE
SB.FOOT = SHT.FOOT = f"HAKI STUDIOS · {kccore.NAME} · EMBROIDERY · {REV} · {DATE}"
CUR, ALL, META, D = KD.load()
P4 = kccore.PIECES
BB = {p: unary_union([r["geom"] for r in D[p]]).bounds for p in P4}
OUT_PDF = f"out/HAKI_{kccore.SHORT}_EMBROIDERY-PACK_{REV.replace(' ', '')}.pdf"
PROP = "[proposed — confirm]"
TOT = sum(CUR[p]["stitches"] for p in P4); TRIMS = sum(CUR[p]["trims"] for p in P4)
MH = sum(mh(CUR[p]) for p in P4)
MH_SPLIT = sum(mh(s) for p in P4 for s in CUR[p]["splits"]["sections"].values()) if all(CUR[p]["splits"]["sections"] for p in P4) else MH
HOOP = {p: max(1, len(CUR[p]["splits"]["sections"])) for p in P4}
ELN = {"01": "JP badge", "02": "EN badge", "03": "CN badge", "04": "KR oval", "05": "Star field"}
def hdr(title, sub, page): return SB.header(title, sub, page)
def fv(x): return glob.glob(x)

def stripe(o, y, h, x0=11, w=None):
    o.append(f'<rect x="{x0}" y="{f(y)}" width="{SW - 22 if w is None else w}" height="{f(h)}" fill="#F5F2EC"/>')

def garment_view(ppm=2.0, show=P4, fade=None):
    """size-M fronts in place + both sleeves beside them, stitch render on drawn pieces. Returns (image, bbox, offsets)."""
    from PIL import ImageDraw
    OFF = {"SR": (-600, 110), "SL": (600, 110), "FR": (0, 0), "FL": (0, 0)}
    bb = (-870, -105, 870, 600)
    vis = []
    for p in show:
        dx, dy = OFF[p]
        from shapely import affinity
        vis += [dict(r, geom=affinity.translate(r["geom"], dx, dy)) for r in D[p]]
    im = SR.render(vis, bb, ppm, base=kccore.FABRIC)
    W, H = im.size
    mask = Image.new("L", (W, H), 0); d = ImageDraw.Draw(mask)
    g, mt = F.pieces("M")
    polys = {"FR": g["F02"].sew_poly(), "FL": g["F01"].sew_poly(), "SR": SV.piece("M", "SR").sew_poly(), "SL": SV.piece("M", "SL").sew_poly()}
    T = lambda cs, o: [((x + o[0] - bb[0])*ppm, (y + o[1] - bb[1])*ppm) for x, y in cs]
    for p, pg in polys.items(): d.polygon(T(pg.exterior.coords, OFF[p]), fill=255)
    out = Image.new("RGB", (W, H), (255, 255, 255)); out.paste(im, (0, 0), mask)
    d2 = ImageDraw.Draw(out)
    for p, pg in polys.items(): d2.line(T(pg.exterior.coords, OFF[p]), fill=(90, 90, 90), width=2)
    for s_ in "RL":
        w_ = F.keep_geoms("M", s_)["welt"]; d2.polygon(T(w_.exterior.coords, (0, 0)), fill=(46, 50, 62), outline=(150, 150, 150))
    d2.rectangle([(-6 - bb[0])*ppm, (0 - bb[1])*ppm, (6 - bb[0])*ppm, (F.HEM - bb[1])*ppm], fill=(160, 125, 60))
    return out, bb, OFF

# ================================================================ G1 cover
def cover(index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>']
    o.append(t(14, 24, "HAKI STUDIOS", 3.0, 700, MUTED))
    o.append(t(14, 36, "Keep Clean Our Space hooded jacket · washed black — embroidery", 6.6, 700))
    o.append(t(14, 44, f"{REV} · {DATE} · Drum Island body (hooded), size M base · 5 elements on 4 pieces · {len(kccore.KC_KEYS)} threads · mm", 2.6, 400, MUTED))
    o.append(f'<line x1="14" y1="48" x2="{SW-14}" y2="48" stroke="{INK}" stroke-width="0.4"/>')
    im, bb, OFF = garment_view(1.6)
    tag, h = img_tag(im, 14, 54, 178); o.append(tag)
    o.append(t(14, 54 + h + 3.5, "FRONTS + SLEEVES, size M stitch render (sleeves laid flat beside the body). Back + hood: no embroidery " + PROP + ".", 2.0, 700))
    o.append(t(14, 54 + h + 7, "Art redrawn from the low-res AI mockup (~1 px/mm, no close-ups yet). Text set from real fonts with the exact characters of the brief.", 1.9, 400, ORANGE))
    ix = 200
    o.append(t(ix, 58, "CONTENTS", 2.8, 700)); y = 64
    for name, pg in index:
        o.append(t(ix, y, name, 1.95)); o.append(t(SW - 14, y, f"{pg}", 1.95, 600, MUTED, "end")); y += 3.9
    y += 3
    o.append(t(ix, y, "TOTALS, SIZE M (read from the DST files)", 2.3, 700)); y += 4.6
    for a, b in [("Stitches per jacket", f"{TOT:,}"), ("Trims per jacket", f"{TRIMS:,}"),
                 ("Hoopings per jacket", f"{sum(HOOP.values())} on {FR_S} (fronts {HOOP['FR']}+{HOOP['FL']}, sleeves {HOOP['SR']}+{HOOP['SL']})"),
                 ("Machine time / jacket", f"{MH_SPLIT:.1f} h split files, {MH:.1f} h full files"), ("Threads", f"{len(kccore.KC_KEYS)} (40wt polyester), max {FA.max_threads(PROF)} per file"),
                 ("3D puff", "JP + EN badges, 3 mm foam " + PROP)]:
        o.append(t(ix, y, a, 1.9, 400, MUTED)); o.append(t(SW - 14, y, b, 1.8, 600, INK, "end")); y += 3.8
    o.append(t(SW - 14, SH - 8, SB.FOOT, 1.9, 400, MUTED, "end"))
    return o

# ================================================================ G2 placement overview
def overview():
    o = hdr("G2 · PLACEMENT OVERVIEW — four badges + the star field on the garment",
            "Fronts: x from CF (+ = wearer's left), y down from the CF neck seam. Sleeves: pattern coords (x across, 0 = sleeve centre line; y down from the underarm line). Tolerance ±2, rotation ±2°.", "G2")
    im, bb, OFF = garment_view(1.8)
    w = 180; s = w / (bb[2] - bb[0]); ax, ay = 12, 30
    tag, h = img_tag(im, ax, ay, w); o.append(tag)
    X = lambda x, p="FR": ax + (x + OFF[p][0] - bb[0])*s; Y = lambda y, p="FR": ay + (y + OFF[p][1] - bb[1])*s
    for el in ("01", "02", "03", "04"):
        P = kccore.ELEMENTS[el][2]; u = unary_union([r["geom"] for r in D[P] if r["el"] == el and not r.get("nok")]).bounds
        o.append(f'<rect x="{f(X(u[0]))}" y="{f(Y(u[1]))}" width="{f((u[2]-u[0])*s)}" height="{f((u[3]-u[1])*s)}" fill="none" stroke="{RED}" stroke-width="0.3" stroke-dasharray="1.2 0.8"/>')
        o.append(f'<circle cx="{f(X(u[0]))}" cy="{f(Y(u[1]))}" r="2.4" fill="{RED}"/>' + t(X(u[0]), Y(u[1]) + 0.8, el, 1.7, 700, "#FFFFFF", "middle"))
    for p in ("SR", "SL"):
        b_ = BB[p]; o.append(f'<circle cx="{f(X((b_[0]+b_[2])/2, p))}" cy="{f(Y(b_[1] - 12, p))}" r="2.4" fill="{RED}"/>' + t(X((b_[0]+b_[2])/2, p), Y(b_[1] - 12, p) + 0.8, "05", 1.7, 700, "#FFFFFF", "middle"))
    o.append(t(ax, ay + h + 3.5, f"Size M ({s:.2f}:1). Red = element boxes. 05 star field covers FR, FL, SR (right sleeve), SL (left sleeve). Grey = welt pockets, gold = zip.", 1.8, 700))
    tx = 198; ty = 30
    o.append(t(tx, ty, "BADGE POSITION PER SIZE (box centre x, y; mm)", 2.1, 700))
    hd = ["Size", "Gr.", "01 JP (FR)", "03 CN (FR)", "02 EN (FL)", "04 KR (FL)"]; cx = [tx, tx + 9, tx + 16, tx + 34, tx + 52, tx + 70]
    for x_, hh in zip(cx, hd): o.append(t(x_, ty + 5, hh, 1.55, 700, MUTED))
    for i, sz in enumerate(kccore.SIZES):
        A = pickle.load(open(f"art_{sz}.pkl", "rb")); y = ty + 9 + i*3.7
        if i % 2 == 0: stripe(o, y - 2.7, 3.7, tx - 1, SW - tx - 11)
        o.append(t(cx[0], y, sz, 1.6, 700)); o.append(t(cx[1], y, kccore.GRADE[sz][0], 1.6, 700, RED))
        for j, el in enumerate(("01", "03", "02", "04")):
            P = kccore.ELEMENTS[el][2]; u = unary_union([r["geom"] for r in A[P] if r["el"] == el and not r.get("nok")]).bounds
            o.append(t(cx[2 + j], y, f"{(u[0]+u[2])/2:+.0f}, {(u[1]+u[3])/2:.0f}", 1.5))
    ky = ty + 9 + 7*3.7 + 3
    o.append(t(tx, ky, "Grade scale: A 92 % (XS–S) · B 100 % (M–XL) · C 106 % (XXL–3XL) " + PROP, 1.6, 400, ORANGE))
    ky += 6
    o.append(t(tx, ky, "KEEP-OUTS (all sizes, from the drafted pieces)", 2.1, 700))
    ko = [f"CF zip {F.KEEP_CF:.0f} · side, armhole, shoulder seams {F.KEEP_SEAM:.0f}", f"Hem-band seam {F.KEEP_HEM:.0f} · neck (hood) seam {F.KEEP_NECK:.0f} " + PROP,
          f"Welt pocket box {F.KEEP_WELT:.0f}", "Sleeves: cap seam 15 · underarm seam 15 · cuff seam 10",
          "Self-fabric hem band, cuffs, hood, back: no embroidery " + PROP]
    for i, k in enumerate(ko): o.append(t(tx, ky + 4 + i*3.3, k, 1.6, 400, ORANGE if PROP in k else INK))
    my = ky + 4 + 5*3.3 + 3
    o.append(t(tx, my, "CLEARANCE CHECK (min distance, every size)", 2.1, 700))
    import emb_place as EP
    worst = EP.worst()
    for i, (k, v, mn, ok) in enumerate(worst):
        o.append(t(tx, my + 4 + i*3.1, f"{k}", 1.55)); o.append(t(tx + 52, my + 4 + i*3.1, f"{v:.1f} (min {mn:.0f})", 1.55, 700, GREEN if ok else RED))
    return o

# ================================================================ G3 threads
def threads():
    o = hdr("G3 · THREAD + TRIM SUMMARY", f"One palette for the whole jacket — {len(kccore.KC_KEYS)} threads. Approve a physical thread board (Isacord or Madeira Polyneon) before sampling; hex = on-screen target.", "G3")
    use = {k: {} for k in kccore.KC_KEYS}
    for p in P4:
        for c in CUR[p]["colours"]: use[c][p] = use[c].get(p, 0) + 1
    hd = ["", "Thread", "Hex", "Isacord", "ΔE", "Madeira Polyneon", "ΔE", "Wt", "Used for", "Stops FR / FL / SR / SL"]
    cx = [12, 18, 44, 58, 88, 96, 130, 138, 146, 240]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.75, 700, MUTED))
    TH = SB.TH; rh = 5.2
    for i, k in enumerate(kccore.KC_KEYS):
        y = 36 + i*rh
        if i % 2 == 0: stripe(o, y - 3.3, rh)
        iso, pn = TH[k]["isacord"], TH[k]["polyneon"]
        ci = GREEN if iso[3] < 3 else (ORANGE if iso[3] < 5.5 else RED); cp = GREEN if pn[3] < 3 else (ORANGE if pn[3] < 5.5 else RED)
        o.append(swatch(cx[0], y, k, 4.5, 2.8)); o.append(t(cx[1], y, PAL[k][1], 1.9, 600)); o.append(t(cx[2], y, HEX[k], 1.75, 400, MUTED))
        o.append(t(cx[3], y, f"{iso[0]} {iso[1]}"[:22], 1.75)); o.append(t(cx[4], y, f"{iso[3]:.1f}", 1.7, 600, ci))
        o.append(t(cx[5], y, f"{pn[0]} {pn[1]}"[:24], 1.75)); o.append(t(cx[6], y, f"{pn[3]:.1f}", 1.7, 600, cp))
        o.append(t(cx[7], y, "40", 1.75)); o.append(t(cx[8], y, PAL[k][2][:62], 1.7, 400, MUTED))
        o.append(t(cx[9], y, " / ".join(str(use[k].get(p, 0)) for p in P4), 1.75, 600))
    yb = 36 + len(kccore.KC_KEYS)*rh + 2
    o.append(t(12, yb, "ΔE2000 vs target: green < 3, amber 3–5.5, red > 5.5 — amber/red rows must be picked from the physical card (F1). Neon mint / lemon / electric blue are", 1.75, 600, ORANGE))
    o.append(t(12, yb + 3.3, "brighter than most standard polyester shades: ask for the nearest fluorescent / high-chroma shade. All targets PROPOSED (read from the mockup).", 1.75, 600, ORANGE))
    o.append(t(12, yb + 10, "TRIMS + CONSUMABLES (per jacket)", 2.2, 700))
    tr = [("Backing", "2.5 oz cutaway, black (washed black shell), 30 larger than each hooping; trim to 5 from stitching after embroidery"),
          ("3D puff foam", "3 mm embroidery foam, BLACK, one sheet over each puff badge (01 JP, 02 EN) at the pause stop; tear away after the puff stops " + PROP),
          ("Topping", "none (duck surface is firm; foam acts as topping under the puff satin)"), ("Needles", "75/11 sharp (duck); 80/12 for the puff stops"),
          ("Bobbin", "60wt black polyester pre-wound"),
          ("Frames", f"{FR_S} (factory.json{'' if PROF['frames_confirmed'] else ', PROPOSED'}): fronts {HOOP['FR']} + {HOOP['FL']} hoopings, sleeves {HOOP['SR']} + {HOOP['SL']} (split files, G5/G6)"),
          ("Patches / labels", "none — all artwork is direct embroidery on the cut pieces")]
    for i, (a, b) in enumerate(tr):
        o.append(t(12, yb + 14.5 + i*3.6, a, 1.85, 600)); o.append(t(42, yb + 14.5 + i*3.6, b, 1.8, 400, ORANGE if PROP in b else INK))
    return o

# ================================================================ G4 summary + questions
def width_check(vis):
    groups = {}
    for r in vis:
        if r.get("nok"): continue
        groups.setdefault(tech.rule_for(r["grp"]), []).append(r)
    out = {}
    for code, rs in groups.items():
        line = rs[0]["st"] in ("bean", "run")
        A = L = 0.0
        for r in rs:
            for p in SR.polys(r["geom"]):
                if p.area < 0.05: continue
                res = qa.check_geom(p, 0.6 if line else 0.8, 0.35 if line else 0.5, 0.45 if line else 0.6)
                if res: A += res["area"]; L += res["long_area"]
        out[code] = 100*L/max(A, 1e-9)
    return out
WC = width_check([r for p in P4 for r in D[p]])

def summary():
    o = hdr("G4 · STITCH SUMMARY + OPEN QUESTIONS", "Size M files. Every count read back from the written DST (stitches, trims, stops, max stitch).", "G4")
    hd = ["Piece", "Elements", "Art box", "Stitches", "Trims", "Trims/10k", "Stops", "Threads", "Max stitch", "Hoopings", "Run time (1 head)"]
    cx = [12, 44, 82, 104, 122, 136, 152, 164, 178, 194, 210]
    for x, h in zip(cx, hd): o.append(t(x, 31, h, 1.8, 700, MUTED))
    for i, p in enumerate(P4):
        r = CUR[p]; b = BB[p]; y = 36 + i*4.6
        if i % 2 == 0: stripe(o, y - 3, 4.6)
        els = sorted({ps_ for s in r["per_stop"] for ps_ in s.get("elements", [])})
        o.append(t(cx[0], y, f"{p} {kccore.PIECE_NAME[p]}", 1.8, 600)); o.append(t(cx[1], y, " + ".join(els), 1.8))
        o.append(t(cx[2], y, f"{b[2]-b[0]:.0f} × {b[3]-b[1]:.0f}", 1.8)); o.append(t(cx[3], y, f"{r['stitches']:,}", 1.8, 600))
        o.append(t(cx[4], y, f"{r['trims']:,}", 1.8)); o.append(t(cx[5], y, f"{r['trims']/max(r['stitches'],1)*1e4:.0f}", 1.8))
        o.append(t(cx[6], y, f"{r['stops']}", 1.8)); o.append(t(cx[7], y, f"{r['threads']}", 1.8))
        o.append(t(cx[8], y, f"{r['max_stitch']:.2f} mm", 1.8, 600, GREEN if r["max_stitch"] <= 7.5 else RED))
        o.append(t(cx[9], y, f"{HOOP[p]}", 1.8)); o.append(t(cx[10], y, f"{mh(r)*60:.0f} min full file" + (f" (+ foam pause)" if r.get("foam_pause_before_stop") else ""), 1.8))
    y = 36 + 4*4.6 + 1
    o.append(t(cx[2], y, "TOTAL", 1.9, 700)); o.append(t(cx[3], y, f"{TOT:,}", 1.9, 700)); o.append(t(cx[4], y, f"{TRIMS:,}", 1.9, 700))
    o.append(t(cx[10], y, f"{MH:.1f} h full · {MH_SPLIT:.1f} h split", 1.9, 700))
    bad = {k: v for k, v in WC.items() if v >= 1.0}
    o.append(t(12, y + 5, "Width check (share of each code's area thinner than its minimum: satin 0.8, run 0.6): " +
               ("all codes < 1 %" if not bad else ", ".join(f"{k} {v:.1f} %" for k, v in sorted(bad.items(), key=lambda kv: -kv[1]))) +
               " — tips of stars / sparkles taper to 0.8 by design.", 1.7, 400, GREEN if not bad else ORANGE))
    o.append(t(12, y + 8.4, f"Run time = factory.machine_hours: {PROF['spm']} spm + 6 s per trim + 4 s per colour change, one hooping; puff pause (lay foam ~2 min) and tear-away not included.", 1.7, 400, MUTED))
    o.append(t(12, y + 11.8, "Fidelity first (Rev A): every badge part, star and glow line of the mockup is built; trims (mostly one per star speckle — each is an island on bare fabric) are reported, not cut.", 1.7, 400, MUTED))
    qy = y + 19
    o.append(t(12, qy, "OPEN QUESTIONS — confirm before sampling", 2.6, 700))
    qs = ["1. Text (the mockup's glyphs are AI-garbled): Chinese 不要污染地球, Korean 우주를 깨끗하게 (set upright, not mirrored), Japanese 宇宙をきれいに, English KEEP CLEAN OUR SPACE. Confirm the wording.",
          "2. 3D puff: JP + EN text, JP spark bars / hearts / stars and the EN star border are digitized for 3 mm puff (dense satin, no underlay, foam pause). Can the factory sew puff? Fallback: same files without foam (flat).",
          "3. Back and hood: the mockup shows only the front. Proposed: back + hood plain; star field on both fronts and all round both sleeves (back half of the sleeves seeded at the mockup's density).",
          f"4. Frame: fronts are ~265 × 500 and sleeves ~480 × 560 → {sum(HOOP.values())} hoopings per jacket on {FR_S}. A bigger frame (≥ 300 × 520 for fronts) removes the front joins. Which frames?",
          "5. Thread board: 7 neon targets read from a low-res AI render — approve physical colours (G3), especially mint / lemon / blue (likely fluorescent shades).",
          "6. Welt pockets: drawn at the mockup's steep slash angle (58°, centre 245 from CF) instead of Drum Island's 38° — the CN badge needs the space. Confirm with the pattern (hood PR).",
          "7. Badge grade: A 92 % / B 100 % / C 106 %; badges keep their shape and move with the panel. Or one badge size for all sizes?",
          "8. Close-ups: art is redrawn from the ~1 px/mm mockup (inputs/closeup_request.md has the prompts). Close-ups would let us match star shapes / glow exactly.",
          "9. DST/PES are production-intent drafts: the factory digitizer checks density, pull and puff end caps on the washed duck and edits before the sew-out."]
    for i, q in enumerate(qs): o.append(KD.auto(12, qy + 5 + i*3.9, q, 1.75))
    return o

# ================================================================ G5 files
def files_page():
    o = hdr("G5 · PRODUCTION STITCH FILES + HOOP SPLITS", f"DST (Tajima) + PES per size per piece. Counts read back from the files; trims counted from the DST. Frame {FR_S} (factory.json).", "G5")
    hd = ["Size", "Gr.", "Piece", "Full file mm", "Stitches", "Trims", "Stops", "Split sections: stitches / trims / mm", "Fits"]
    cx = [12, 21, 28, 38, 58, 72, 82, 92, 274]
    for x_, h in zip(cx, hd): o.append(t(x_, 31, h, 1.55, 700, MUTED))
    y = 35; allfit = True
    for i, sz in enumerate(kccore.SIZES):
        for p in P4:
            r = ALL.get(sz, {}).get(p)
            if i % 2 == 0: stripe(o, y - 2.3, 2.95)
            o.append(t(cx[0], y, sz if p == "FR" else "", 1.45, 700)); o.append(t(cx[1], y, kccore.GRADE[sz][0] if p == "FR" else "", 1.45, 700, RED)); o.append(t(cx[2], y, p, 1.45, 600))
            if r and "full" in r:
                fu = r["full"]
                o.append(t(cx[3], y, f"{fu['size_mm'][0]:.0f} × {fu['size_mm'][1]:.0f}", 1.4)); o.append(t(cx[4], y, f"{fu['stitches']:,}", 1.4)); o.append(t(cx[5], y, f"{fu['trims']}", 1.4)); o.append(t(cx[6], y, f"{fu['stops']}", 1.4))
                secs = r.get("splits", {}).get("sections", {})
                o.append(t(cx[7], y, "   ".join(f"{nm.split('_')[0]} {s_['stitches']:,} / {s_['trims']} / {s_['size_mm'][0]:.0f}×{s_['size_mm'][1]:.0f}" for nm, s_ in secs.items()), 1.35))
                fits = bool(secs) and all(v["fits"] for v in secs.values()); allfit &= fits
                o.append(t(cx[8], y, "yes" if fits else "CHECK", 1.4, 700, GREEN if fits else RED))
            else:
                o.append(t(cx[3], y, "pending", 1.4, 400, MUTED)); allfit = False
            y += 2.95
    y += 2.5
    o.append(t(12, y, "WHAT IS DIGITIZED", 2.0, 700)); y += 4
    notes = [("Order", "per file: glow (sheer run) → white stars → flat badge parts (CN text + dots, KR oval + text, red star) → PAUSE: lay 3 mm foam → puff stops → tear foam → star centre."),
             ("Text", "set from fonts (E01–E04), one turning satin per stroke, cut at corners; puff text 0.30 spacing, no underlay; flat text 0.40 with centre-run underlay."),
             ("Stars", "4-point sparkles (one 45° satin object) + satin dots Ø 1.45–2.0 — each speckle is one island on bare fabric = one trim (reported, fidelity first)."),
             ("Splits", f"objects < 70 mm go whole to one section; fills crossing a split overlap 1.2 mm; registration crosses sew in stop 1's thread. Every section fits: {'yes' if allfit else 'CHECK'}.")]
    for a, b_ in notes:
        o.append(t(12, y, a, 1.6, 700)); o.append(t(26, y, b_, 1.5)); y += 3.2
    return o

# ================================================================ G6 hooping
def hooping_page():
    o = hdr("G6 · HOOPING TABLE — split lines + needle start per file, every size",
            f"Frame {FR_S} (factory.json{'' if PROF['frames_confirmed'] else ', PROPOSED'}). Front coords: x from CF, y from the CF neck seam. Sleeve coords: x from the sleeve centre line, y from the underarm line.", "G6")
    hd = ["Size", "Piece", "Split x", "Split y", "Sections: needle start (x, y) + file mm", "Full file start", "Badge crossed by a split", "Fit"]
    cx = [12, 22, 32, 44, 56, 206, 232, 272]
    for x_, h in zip(cx, hd): o.append(t(x_, 31, h, 1.5, 700, MUTED))
    y = 35
    for i, sz in enumerate(kccore.SIZES):
        A = pickle.load(open(f"art_{sz}.pkl", "rb"))
        for P in P4:
            r = ALL.get(sz, {}).get(P)
            if not r: continue
            sp = r.get("splits", {}); secs = sp.get("sections", {})
            if i % 2 == 0: stripe(o, y - 2.3, 2.95)
            o.append(t(cx[0], y, sz if P == "FR" else "", 1.45, 700)); o.append(t(cx[1], y, P, 1.45, 600))
            o.append(t(cx[2], y, f"{sp['sx']:+.0f}" if sp.get("sx") is not None else "—", 1.45, 700, RED)); o.append(t(cx[3], y, f"{sp['sy']:.0f}" if sp.get("sy") is not None else "—", 1.45, 700, RED))
            o.append(t(cx[4], y, "  ".join(f"{nm.split('_')[0]} ({s_['origin'][0]:+.0f}, {s_['origin'][1]:.0f}) {s_['size_mm'][0]:.0f}×{s_['size_mm'][1]:.0f}" for nm, s_ in secs.items()), 1.3))
            fo = r["full"]["origin"]; o.append(t(cx[5], y, f"({fo[0]:+.0f}, {fo[1]:.0f})", 1.4))
            cut = []
            from shapely.geometry import LineString
            for el in ("01", "02", "03", "04"):
                rs = [q["geom"] for q in A[P] if q["el"] == el and not q.get("nok")]
                if not rs: continue
                u = unary_union(rs)
                for ln in ([LineString([(-900, sp["sy"]), (900, sp["sy"])])] if sp.get("sy") is not None else []) + ([LineString([(sp["sx"], -900), (sp["sx"], 900)])] if sp.get("sx") is not None else []):
                    if u.intersects(ln): cut.append(el)
            o.append(t(cx[6], y, ", ".join(sorted(set(cut))) or "none", 1.4, 700 if cut else 400, ORANGE if cut else GREEN))
            ok = bool(secs) and all(v["fits"] for v in secs.values()); o.append(t(cx[7], y, "yes" if ok else "NO", 1.45, 700, GREEN if ok else RED))
            y += 2.95
    y += 2
    for i, l in enumerate(["Split lines are searched where they cut the least art (fronts 15–85 % of the height, sleeves 25–75 % / 15–85 %); whole motifs < 70 mm (stars, dots, bars, glyph strokes)",
                           "never split — a badge crossed by a split (amber) has its glyphs / dots kept whole on one side; check that joint on the strike-off. Needle start = centre of each file (DST origin):",
                           "mark it on the cut piece from the pattern. Registration crosses: stop 1 thread, long 4 mm stitches on bare fabric outside the art; the next section re-registers on them; pick out after."]):
        o.append(t(12, y + i*3.2, l, 1.55, 400, MUTED))
    return o

# ================================================================ element specs
def badge_page(el):
    slug, title, P = kccore.ELEMENTS[el]; b = META["badges"][el]
    vis = [r for r in D[P] if r["el"] == el]
    u = unary_union([r["geom"] for r in vis if not r.get("nok")]).bounds
    o = hdr(f"E{el} · {ELN[el].upper()} — {kccore.PIECE_NAME[P]} ({P}, pattern {kccore.PIECE_CODE[P]})",
            "Direct embroidery on the cut front panel before zip + welts · mm, finished size · stitch render of the size-M file art · numbers from the files", f"E{el}")
    bb = (u[0] - 4, u[1] - 4, u[2] + 4, u[3] + 4)
    im = SR.render([r for r in D[P] if r["el"] in (el, "05")], bb, 6.0, base=kccore.FABRIC)
    wmax, hmax = 150, 150; sc = min(wmax / (bb[2]-bb[0]), hmax / (bb[3]-bb[1]))
    ax, ay = 14, 32
    tag, h = img_tag(im, ax, ay, (bb[2]-bb[0])*sc); o.append(tag)
    X = lambda x: ax + (x - bb[0])*sc; Y = lambda y: ay + (y - bb[1])*sc
    o.append(dim_h(X(u[0]), X(u[2]), ay - 1.5, f"{u[2]-u[0]:.0f}", 1.9))
    o.append(dim_v(Y(u[1]), Y(u[3]), ax + (bb[2]-bb[0])*sc + 3, f"{u[3]-u[1]:.0f}", 1.9, side=1))
    o.append(t(ax, ay + h + 4, f"Size M, shown {sc:.2f}:1. Art box {u[2]-u[0]:.0f} × {u[3]-u[1]:.0f} (badge only; field stars around it belong to E05).", 1.75, 400, MUTED))
    rx = 172; y = 33
    o.append(t(rx, y, "TEXT — exact characters, set from the font (do not re-type or trace)", 2.1, 700)); y += 3
    key = {"01": "jp", "02": "en", "03": "cn", "04": "kr"}[el]
    txt = kccore.TEXT[el] if el != "02" else "KEEP CLEAN OUR SPACE"
    o.append(text_big(rx, y + 9, txt, key, 8.5 if el != "02" else 6.5)); y += 13
    mean = {"01": "'Make space clean' (uchū o kirei ni)", "02": "KEEP / OUR SPACE in mint, CLEAN in lemon, 2 lines", "03": "'Don't pollute the Earth' (bù yào wūrǎn dìqiú), vertical",
            "04": "'Keep space clean' (ujureul kkaekkeuthage)"}[el]
    rows = [("Meaning / layout", mean), ("Font", KD.FONT_NAME[key] + " (OFL, inputs/fonts)"), ("Em height (M)", f"{b['em']:.1f} mm" + (f" · line pitch 27" if el == "02" else "")),
            ("Angle", f"{b['angle']:+.1f}° (y down: + = clockwise)"), ("Process", "3D puff, 3 mm black foam " + PROP if el in ("01", "02") else "flat satin")]
    if el == "03": rows.append(("Ring", f"{b['dots']} dots Ø 12.4 alternating blue / mint, sparkles inside"))
    if el == "04": rows.append(("Oval ring", f"outer {2*b['axes'][0]:.0f} × {2*b['axes'][1]:.0f}, ring {b['axes'][2]:.1f} gold + 1.1 lemon highlight"))
    for a_, b_ in rows:
        o.append(t(rx, y, a_, 1.8, 400, MUTED)); o.append(t(rx + 30, y, b_, 1.75, 600, ORANGE if PROP in b_ else INK)); y += 3.5
    y += 2
    o.append(t(rx, y, "PARTS (size M art)", 2.1, 700)); y += 4
    comp = {}
    for r in vis:
        k = (tech.rule_for(r["grp"]), r["col"]); comp.setdefault(k, set()).add(r.get("unit"))
    hdx = [rx, rx + 15, rx + 50, rx + 64, rx + 100]
    for x_, hh in zip(hdx, ["Code", "Part", "Thread", "Units", "Stitch"]): o.append(t(x_, y, hh, 1.5, 700, MUTED))
    y += 3.2
    for (code, col), us in sorted(comp.items(), key=lambda kv: tech.COLOUR_ORDER.index(kv[0][1])):
        rr = tech.RULES[code]
        o.append(t(hdx[0], y, code, 1.55, 700)); o.append(t(hdx[1], y, rr[0][:24], 1.5)); o.append(swatch(hdx[2], y, col, 3, 2)); o.append(t(hdx[2] + 4, y, PAL[col][1], 1.45))
        o.append(t(hdx[3], y, f"{len(us)}", 1.5)); o.append(t(hdx[4], y, rr[1][:22], 1.45)); y += 3.0
    y += 2
    wc = width_check(vis)
    o.append(t(rx, y, "STITCH CHECK: " + ("all parts ≥ min width (satin 0.8, run 0.6)" if all(v < 1 for v in wc.values()) else
                                        "thin share " + ", ".join(f"{k} {v:.1f} %" for k, v in wc.items() if v >= 1) + " (tapered tips)"), 1.7, 700, GREEN if all(v < 1 for v in wc.values()) else ORANGE))
    y += 4
    # mockup vs art (same scale)
    import compare as CP
    mk = CP.mock_local(el, bb, 3.0)
    room = SH - 14 - (y + 4) - len(CHANGES[el]) * 3.0; wpair = min(52, room * mk.width / mk.height)
    tag2, h2 = img_tag(mk, rx, y + 2, wpair); o.append(tag2)
    st2 = SR.render([r for r in D[P] if r["el"] in (el, "05")], bb, 3.0, base=kccore.FABRIC); tag3, _ = img_tag(st2, rx + wpair + 4, y + 2, wpair); o.append(tag3)
    o.append(t(rx, y + 1, "MOCKUP (low-res AI render)", 1.6, 700)); o.append(t(rx + wpair + 4, y + 1, "THIS FILE (same scale)", 1.6, 700))
    yy = y + 4 + h2
    for i, c in enumerate(CHANGES[el]): o.append(KD.auto(rx, yy + i*3.0, c.lstrip("!"), 1.6, ORANGE if c.startswith("!") else INK, 700 if i == 0 else 400))
    return o

def text_big(x, y, txt, key, h):
    if key == "en": return t(x, y, txt, h*0.9, 800, HEX["kc_mint"].replace("#6FE3CC", "#2a9d8a"))
    return KD.text_path(x, y, txt, key, h, "#1A1A1A")

CHANGES = {
 "01": ["WHAT CHANGED vs MOCKUP", "Text set from Zen Maru Gothic Black (the render's glyphs are", "  correct here but re-set, not traced). 17 spark bars, 2 hearts,",
        "  4 stars, 1 dot counted + placed from the mockup; neon halo = sheer", "  glow run (sewn first, under the puff).", "!Reference: low-res mockup only (no close-up)."],
 "02": ["WHAT CHANGED vs MOCKUP", "18 gold stars counted + placed from the mockup (the render hides", "  2 behind 'N'; not added). Text Nunito ExtraBold, 2 lines at 50°.",
        "Badge moved 6–9 toward CF per size: it clears the 15 armhole", "  keep-out of the Drum Island front.", "!Reference: low-res mockup only (no close-up)."],
 "03": ["WHAT CHANGED vs MOCKUP", "!Text: the render shows 7 garbled glyphs (木不要涞球汚染); set as", "!  不要污染地球 (6 characters, brief) — confirm wording.",
        "22 ring dots + 22 inner sparkles from the mockup. Moved 14 toward", "  CF: clears the 6 welt keep-out (steep slash welt).", "!Reference: low-res mockup only (no close-up)."],
 "04": ["WHAT CHANGED vs MOCKUP", "!Text: the render's Hangul is mirrored + upside down and garbled;", "!  set upright as 우주를 깨끗하게 (brief) — confirm wording.",
        "Oval ring 4.0 gold satin + 1.1 lemon highlight, tilted 6.9°", "  as in the mockup. Decorative marks inside the render are dropped.", "!Reference: low-res mockup only (no close-up)."],
}

def star_page():
    o = hdr("E05 · STAR FIELD — white speckles on both fronts and all round both sleeves",
            "Direct embroidery on the cut pieces · 4-point sparkles + satin dots · positions from the mockup, star size constant over sizes", "E05")
    from sheet import t as T_
    hd = ["Size", "FR stars", "FL stars", "SR stars", "SL stars", "moved out of a keep-out", "dropped (no free spot ≤ 8)"]
    cx = [14, 30, 48, 66, 84, 104, 146]
    for x_, h in zip(cx, hd): o.append(t(x_, 32, h, 1.6, 700, MUTED))
    for i, sz in enumerate(kccore.SIZES):
        A = pickle.load(open(f"art_{sz}.pkl", "rb")); y = 36.5 + i*3.6
        if i % 2 == 0: stripe(o, y - 2.6, 3.6, 13, 176)
        o.append(t(cx[0], y, sz, 1.6, 700))
        for j, p in enumerate(P4): o.append(t(cx[1 + j], y, f"{A['info'][p]['stars']}", 1.6))
        o.append(t(cx[5], y, f"{sum(A['info'][p].get('stars_nudged', 0) for p in P4)}", 1.6)); o.append(t(cx[6], y, f"{sum(A['info'][p]['stars_dropped'] for p in P4)}", 1.6))
    y = 36.5 + 7*3.6 + 3
    c = META["counts"]
    lines = [f"Fronts: {c['FR_field']} + {c['FL_field']} speckles detected on the mockup fronts (white specks, badges excluded) and mapped to the Drum Island panel;",
             "  a speckle that lands in a keep-out is moved to the nearest free spot (≤ 8 mm; further would line stars up along the keep-out edge) so the mockup's star count is kept (A2).",
             f"Sleeves: front half mapped from the mockup sleeves ({c['SR_front_mapped']} + {c['SL_front_mapped']}); back half seeded at the same density + size mix " + PROP + ".",
             "Size: speck extent ≥ 5 px → sparkle span 3.6–8.0 mm; smaller → satin dot Ø 1.45 / 1.7 / 2.0. One thread (Star white).",
             "Each speckle is an island on bare fabric: 1 trim each (jumps < 2.5 mm are kept as jumps). Trims are reported, not reduced (fidelity first)."]
    for i, l in enumerate(lines): o.append(t(14, y + i*3.4, l, 1.7, 400, ORANGE if PROP in l else INK))
    y += 5*3.4 + 4
    # zoom: sparkle + dots
    zb = None
    for r in D["FL"]:
        if r["el"] == "05" and r["grp"] == "STAR":
            c0 = r["geom"].centroid; zb = (c0.x - 6, c0.y - 6, c0.x + 6, c0.y + 6); break
    if zb:
        im = SR.render(D["FL"], zb, 30, base=kccore.FABRIC); tag, h = img_tag(im, 14, y, 36); o.append(tag)
        o.append(t(14, y + h + 3, "Sparkle 4:1 (concave 4-point, flat 0.8 tips)", 1.6, 400, MUTED))
        dm = SB.direction_map([r for r in D["FL"] if r["el"] == "05"], zb, 30, label_min=1e9); tag, h = img_tag(dm, 54, y, 36); o.append(tag)
        o.append(t(54, y + h + 3, "Stitch direction: 45° satin, one object", 1.6, 400, MUTED))
    import compare as CP
    sl = Image.open("out/compare_05_sleeves.png"); tag, h = img_tag(sl, 196, 32, 90); o.append(tag)
    o.append(t(196, 32 + h + 3, "Sleeves: mockup | SR | SL stitch render (size M)", 1.6, 400, MUTED))
    fr = Image.open("out/compare_front_M.png"); tag, h = img_tag(fr, 100, y, 90); o.append(tag)
    o.append(t(100, y + h + 3, "Fronts: mockup (mapped) | stitch render (size M)", 1.6, 400, MUTED))
    return o

# ================================================================ stop tables (read back)
def stops_page(pieces, page):
    o = hdr(f"{page} · COLOUR STOP SEQUENCE (size M, read back from the DST) — {' + '.join(pieces)}",
            "Stitches / trims per stop counted in the written .dst. PAUSE rows = programme a machine stop: lay 3 mm foam / tear the foam. 'Sews' = region codes in the stop.", page)
    colx = [12, 154]
    for ci, p in enumerate(pieces):
        x0 = colx[ci]; r = CUR[p]; ps = r["per_stop"]
        o.append(t(x0, 30.5, f"{p} — {os.path.basename(r['file'])}.dst", 2.0, 700))
        hc = [x0, x0 + 7, x0 + 30, x0 + 52, x0 + 74, x0 + 110, x0 + 126]
        for x, hd in zip(hc, ["Stop", "Thread", "Isacord", "Polyneon", "Sews (codes · elements)", "Stitches", "Trims"]): o.append(t(x, 34.5, hd, 1.5, 700, MUTED))
        y = 38.5; rh = 4.0
        for s_ in ps:
            if r.get("foam_pause_before_stop") == s_["stop"] or r.get("foam_tear_before_stop") == s_["stop"]:
                lab = "PAUSE — lay 3 mm black foam over badge " + ("01" if p == "FR" else "02") if r.get("foam_pause_before_stop") == s_["stop"] else "PAUSE — tear away the foam, then continue"
                o.append(f'<rect x="{x0-1}" y="{f(y-2.6)}" width="138" height="3.6" fill="#FFE9D6"/>'); o.append(t(x0 + 7, y, lab, 1.5, 700, ORANGE)); y += rh
            k = s_["col"]; iso, pn = SB.TH[k]["isacord"], SB.TH[k]["polyneon"]
            if s_["stop"] % 2: o.append(f'<rect x="{x0-1}" y="{f(y-2.6)}" width="138" height="{rh}" fill="#F5F2EC"/>')
            o.append(t(hc[0], y, f"{s_['stop']:02d}", 1.5, 700)); o.append(swatch(hc[1], y, k, 2.8, 2.0)); o.append(t(hc[1] + 3.6, y, PAL[k][1], 1.45))
            o.append(t(hc[2], y, f"{iso[0]} {iso[1]}"[:15], 1.35)); o.append(t(hc[3], y, f"{pn[0]} {pn[1]}"[:15], 1.35))
            o.append(t(hc[4], y, (", ".join(s_.get("codes", [])) + " · " + "+".join(s_.get("elements", [])))[:34], 1.3, 400, MUTED))
            o.append(t(hc[5], y, f"{s_['stitches']:,}", 1.5, 600)); o.append(t(hc[6], y, f"{s_['trims']}", 1.5)); y += rh
        y += 1
        o.append(t(hc[4], y, "FILE TOTAL (sum of stops)", 1.5, 700)); o.append(t(hc[5], y, f"{sum(q['stitches'] for q in ps):,}", 1.5, 700)); o.append(t(hc[6], y, f"{sum(q['trims'] for q in ps)}", 1.5, 700))
        o.append(t(hc[4], y + 3.2, f"= DST {r['stitches']:,} stitches / {r['trims']} trims · {r['threads']} colours · max {r['max_stitch']:.2f} mm", 1.4, 400, MUTED))
    return o

def region_page():
    o = hdr("R1 · REGION STITCH TABLE — digitizing parameters per region code",
            "Density = row spacing (mm). Pull comp = added width per side (mm). Width = share of the code's area below its minimum width. Objects = regions in the size-M art (all pieces).", "R1")
    allv = [r for p in P4 for r in D[p]]
    stats = {}
    for r in allv:
        k = tech.rule_for(r["grp"]); s_ = stats.setdefault(k, dict(n=0, cols=set())); s_["n"] += 1; s_["cols"].add(r["col"])
    hdr_ = ["Code", "Region", "Thread(s)", "Stitch", "Angle", "Dens.", "Len.", "Underlay", "Pull", "Notes", "Width", "Obj."]
    cx = [12, 26, 64, 88, 122, 152, 164, 174, 206, 216, 262, 274]
    for x, hd in zip(cx, hdr_): o.append(t(x, 31, hd, 1.7, 700, MUTED))
    y = 35.5
    for i, k in enumerate([k for k in kccore.KC_RULES if k in stats]):
        if i % 2 == 0: stripe(o, y - 2.6, 4.0)
        name, st, ang, dens, ln, ul, pull, note = tech.RULES[k]; s_ = stats[k]
        o.append(t(cx[0], y, k, 1.65, 700)); o.append(t(cx[1], y, name[:26], 1.6))
        xs = cx[2]
        for c in sorted(s_["cols"], key=lambda c: tech.COLOUR_ORDER.index(c))[:5]: o.append(swatch(xs, y, c, 3.2, 2.2)); xs += 4.2
        for j, v in enumerate((st, ang, dens, ln, ul, pull, note)): o.append(t(cx[3 + j], y, v[:34] if j == 6 else v[:24], 1.5))
        q = WC.get(k, 0.0); o.append(t(cx[10], y, f"{q:.1f}%", 1.55, 600, GREEN if q < 1 else (ORANGE if q < 3.5 else RED)))
        o.append(t(cx[11], y, f"{s_['n']}", 1.55, 400, MUTED)); y += 4.0
    y += 3
    for i, l in enumerate(["Globals: 40wt polyester, 75/11 sharp (80/12 for puff), 2.5 oz black cutaway, no topping. Satin > 7.0 wide → split satin. Tie-in/off every object; trim moves > 2.5 mm on bare fabric.",
                           "Puff (PF-*): satin rows 0.30 apart, no underlay, pull 0.35, sewn over 3 mm foam after the PAUSE; the digitizer adds foam-cutting end caps if the sew-out shows foam at the column ends.",
                           "Text strokes (TXF / PF-TX): each glyph is split into strokes (skeleton, cut at junctions + corners), one turning satin per stroke; do not re-set the text from another font.",
                           "Stitch counts are never estimated per region: per-file and per-stop counts (G4, G5, S1, S2) are read back from the DST files."]):
        o.append(t(12, y + i*3.3, l, 1.6, 400, MUTED))
    return o

def f1_pages():
    so = [dict(file=os.path.basename(CUR[p]["file"]) + ".dst", piece=f"{p} {kccore.PIECE_NAME[p]} (full file)", stitches=CUR[p]["stitches"], trims=CUR[p]["trims"]) for p in P4]
    so += [dict(file=os.path.basename(s["file"]) + ".dst", piece=f"{p} split {nm}", stitches=s["stitches"], trims=s["trims"]) for p in ("FR", "FL") for nm, s in CUR[p]["splits"]["sections"].items()]
    th = [dict(name=PAL[k][1], code=f"Isacord {SB.TH[k]['isacord'][0]} / Polyneon {SB.TH[k]['polyneon'][0]}", de=min(SB.TH[k]["isacord"][3], SB.TH[k]["polyneon"][3])) for k in kccore.KC_KEYS]
    pcs = [dict(piece=f"{p} {kccore.PIECE_NAME[p]}", w=CUR[p]["size_mm"][0], h=CUR[p]["size_mm"][1], hoopings=HOOP[p]) for p in P4]
    svgs = FA.requests_page(kccore.NAME, so, th, pcs, page="F1", prof=PROF)
    extra = ('<text x="16" y="196" font-family="Liberation Sans" font-size="2.4" font-weight="700" fill="#C25000">5  3D puff: can you sew 3 mm foam puff on the JP + EN badges (pause stop marked on S1/S2)? Which foam colours / brands? Price per puff hooping.</text>')
    return [s.replace("</svg>", extra + "</svg>") for s in svgs]

def build():
    pages = [("G1", None), ("G2", overview()), ("G3", threads()), ("G4", summary()), ("G5", files_page()), ("G6", hooping_page()),
             ("E01", badge_page("01")), ("E02", badge_page("02")), ("E03", badge_page("03")), ("E04", badge_page("04")), ("E05", star_page()),
             ("S1", stops_page(["FR", "FL"], "S1")), ("S2", stops_page(["SR", "SL"], "S2")), ("R1", region_page())]
    names = {"G1": "Cover + contents", "G2": "Placement overview", "G3": "Thread + trim summary", "G4": "Stitch summary + open questions",
             "G5": "Production stitch files + hoop splits", "G6": "Hooping table", "E01": "JP badge (FR chest)", "E02": "EN badge (FL chest)",
             "E03": "CN badge (FR lower)", "E04": "KR oval (FL lower)", "E05": "Star field (fronts + sleeves)", "S1": "Stop sequence FR + FL", "S2": "Stop sequence SR + SL", "R1": "Region stitch table"}
    index = [(f"{k} {names[k]}", i + 1) for i, (k, _) in enumerate(pages)] + [("F1 Factory requests", len(pages) + 1)]
    pages[0] = ("G1", cover(index))
    w = PdfWriter(); os.makedirs("out/pages", exist_ok=True)
    for k, o in pages:
        svg = doc(o); cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"out/pages/{k}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"out/pages/prev_{k}.png", output_width=2400)
        w.append(PdfReader(f"out/pages/{k}.pdf"))
    for i, svg in enumerate(f1_pages()):
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"out/pages/F{i+1}.pdf"); cairosvg.svg2png(bytestring=svg.encode(), write_to=f"out/pages/prev_F{i+1}.png", output_width=2400)
        w.append(PdfReader(f"out/pages/F{i+1}.pdf"))
    w.write(OUT_PDF)
    print("pages", len(PdfReader(OUT_PDF).pages), OUT_PDF)

if __name__ == "__main__":
    build()
