"""Garment pages T1-T8 + pattern (DXF per size + all sizes, 1:1 plot PDF size M) for the blossom tetra hoodie.
Block = zip-hoodie (engine/hoodie.py: Drum Island body + 3-panel sherpa hood + elastic self-fabric hem / cuff bands;
founder decision 19 Oct 2026, hood option 1) with this design's welt override (mockup welts, 60°, PROPOSED).
Pages T2-T6 reuse the zip-hoodie block pages (projects/zip-hoodie-block/build.py), fed with THIS design's pattern;
T1, T7 (embroidery placement per size) and T8 (questions + revisions) are this design's. Every number is read from the
pattern (hoodie.draft / measure) or the stitch files (dst_all.json).  usage: python3 garment.py"""
import kbcore
import os, sys, json, pickle, math
import cairosvg
from pypdf import PdfWriter, PdfReader
from shapely import affinity
from shapely.ops import unary_union
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "projects", "zip-hoodie-block"))
import sheet as SHT
from sheet import t, doc, INK, MUTED, RED, GREEN, ORANGE, SW, SH
from render import f
import hoodie as HD, pattern as PT, pattern_out as PO, pattern_draw as PD, drum
import front as F, emb_place as EP, espec, factory as FA
import stitchrender as SR
from specbase import img_tag
import hflat as HF
import build as ZB                     # the block's page builders (module-level data replaced below)

STYLE = kbcore.STYLE; REV = kbcore.REV_GAR; DATE = kbcore.DATE; NAME = kbcore.NAME.split("  #")[0]
SHT.FOOT = f"HAKI STUDIOS · {NAME} · {STYLE} · GARMENT · {REV} · {DATE}"
PROP = ZB.PROP; ALT = ZB.ALT
OUT = "out/garment"; os.makedirs(f"{OUT}/pattern", exist_ok=True)
SIZES = HD.SIZES
ALLR = json.load(open("dst_all.json"))

class Blk:
    """pattern_out block: hoodie.draft with this design's welt (hoodie.Variant has no ORDER — ENGINE_NOTES 11)"""
    ORDER = HD.ORDER
    @staticmethod
    def draft(size): return F.pieces(size)

class Flat(HF.Flat):
    def welt(self, side=1):          # this design's welt (mockup position + angle), not the jacket default
        W = affinity.translate(F.WELT_L, 0, self.fnd)
        return self._m(W, side)

# feed the block pages this design's pattern
ZB.G = {sz: F.pieces(sz) for sz in SIZES}; ZB.gM, ZB.mM = ZB.G["M"]; ZB.HF.Flat = Flat
ZB.STYLE = STYLE

def mh(r): return FA.machine_hours(r["stitches"], FA.load(), trims=r["trims"], colour_changes=r["stops"] - 1)

def masked(vis, ppm=4.8):
    """stitch render of vis with a transparent background (only stitched pixels), + its bounds"""
    from PIL import Image, ImageDraw
    u = unary_union([r["geom"] for r in vis]); b = u.bounds
    im = SR.render(vis, b, ppm, base="#000000")
    mask = Image.new("L", im.size, 0); d = ImageDraw.Draw(mask)
    for p in (u.geoms if hasattr(u, "geoms") else [u]):
        d.polygon([((x - b[0]) * ppm, (y - b[1]) * ppm) for x, y in p.exterior.coords], fill=255)
        for h in p.interiors: d.polygon([((x - b[0]) * ppm, (y - b[1]) * ppm) for x, y in h.coords], fill=0)
    im = im.convert("RGBA"); im.putalpha(mask)
    return im, b

def img_at(im, x, y, w, h):
    import io, base64
    buf = io.BytesIO(); im.save(buf, "PNG")
    return f'<image x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" href="data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"/>'

def art_on_flat(Fl):
    """size-M embroidery (front pieces) placed on the front flat: flat y = garment y + front neck drop"""
    D = pickle.load(open("art_M.pkl", "rb"))
    return masked([dict(r, geom=affinity.translate(r["geom"], 0, Fl.fnd)) for P in ("FR", "FL") for r in D[P]])

def front_flat_with_art(ox, oy, w):
    Fl = Flat("M"); b = HF.bounds(Fl, False); s = w / (b[2] - b[0])
    o = [ZB.flat_g(HF.draw_front(Fl), b, ox, oy, s)]
    im, ab = art_on_flat(Fl)
    o.append(img_at(im, ox + (ab[0] - b[0]) * s, oy + (ab[1] - b[1]) * s, (ab[2] - ab[0]) * s, (ab[3] - ab[1]) * s))
    return o, (b[3] - b[1]) * s

def p_cover(index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>', t(14, 22, "HAKI STUDIOS", 3.0, 700, MUTED), t(14, 34, NAME, 7.0, 700),
         t(14, 41.5, f"Style {STYLE} · garment {REV} / embroidery {kbcore.REV_EMB} · {DATE} · sizes XS–3XL · base M · cm unless marked mm", 2.5, 400, MUTED),
         f'<line x1="14" y1="45" x2="{SW-14}" y2="45" stroke="{INK}" stroke-width="0.4"/>']
    fo, h = front_flat_with_art(14, 52, 92); o += fo; o.append(t(14, 52 + h + 5, "FRONT (size M, embroidery from the size-M art)", 2.0, 700))
    Fl = Flat("M"); b = HF.bounds(Fl, True); s = 88 / (b[2] - b[0])
    o.append(ZB.flat_g(HF.draw_back(Fl), b, 112, 52, s)); o.append(t(112, 52 + (b[3] - b[1]) * s + 5, "BACK (plain) [proposed — confirm]", 2.0, 700, PROP))
    ix = 206; o.append(t(ix, 56, "CONTENTS", 2.8, 700)); y = 62
    for name, pg in index: o.append(t(ix, y, name, 1.85)); o.append(t(SW - 14, y, str(pg), 1.85, 600, MUTED, "end")); y += 3.7
    y += 3; o.append(t(ix, y, "KEY SPECS", 2.4, 700)); y += 4.6
    tot = sum(ALLR["M"][P]["full"]["stitches"] for P in kbcore.PIECES)
    for a, b_, p in [("Block", "zip hoodie = Drum Island body + sleeve (approved)", False), ("Hood", "3 panels, sherpa-lined (block)", True),
                     ("Hem / cuffs", "self fabric + elastic (block)", True), ("Welts", f"mockup position, {F.WELT_ANG:.0f}°, 1.4 × 13", True),
                     ("Shell", "washed navy 12 oz duck", True), ("Embroidery", f"fronts + sleeves, {tot:,} st (M, DST)", False),
                     ("Pattern", "XS–3XL, DXF (AAMA) + 1:1 plot (M)", False)]:
        o.append(t(ix, y, a, 1.9, 400, MUTED)); o.append(t(ix + 21, y, b_, 1.8, 600, PROP if p else INK)); y += 3.7
    o.append(t(SW - 14, SH - 8, SHT.FOOT, 1.8, 400, MUTED, "end"))
    return o

def p_placement():
    o = SHT.header("EMBROIDERY PLACEMENT ON THE PATTERN — every size", "Art is placed per size on that size's pattern pieces (hoodie block + mockup welts). Clearances measured on the pattern (LESSONS A3/C8). Files: G5/G6.", "T7")
    D = pickle.load(open("art_M.pkl", "rb"))
    g, mt = F.pieces("M")
    x = 12
    for P in kbcore.PIECES:
        pc = g[F.CODE[P]]; b = PT.cut_poly(pc).bounds; s = (40 if P in ("FR", "FL") else 34) / (b[2] - b[0])
        X = (lambda xx0, b0: (lambda q: xx0 + (q - b0) * s))(x, b[0]); Y = (lambda b1: (lambda q: 34 + (q - b1) * s))(b[1])
        o.append(f'<path d="M' + " L".join(f"{f(X(x_))} {f(Y(y_))}" for x_, y_ in pc.sew_poly().exterior.coords) + f' Z" fill="{kbcore.FABRIC}" stroke="none"/>')
        im, ab = masked(D[P], 4.0); o.append(img_at(im, X(ab[0]), Y(ab[1]), (ab[2] - ab[0]) * s, (ab[3] - ab[1]) * s))
        o += PD.piece_svg(pc, X, Y, s, label=False, size="M", lw=0.25, text_mm=1.0)
        if P in ("FR", "FL"):
            w_ = F.keep_geoms("M", P)["welt"]
            o.append(f'<path d="M' + " L".join(f"{f(X(x_))} {f(Y(y_))}" for x_, y_ in w_.exterior.coords) + '" fill="none" stroke="#E0C080" stroke-width="0.35"/>')
        o.append(t(x, 34 + (b[3] - b[1]) * s + 4, f"{F.CODE[P]} {P} — {kbcore.PIECE_NAME[P]}", 1.6, 700))
        x += (b[2] - b[0]) * s + 6
    ty = 120
    o.append(t(12, ty, "SMALLEST CLEARANCE TO EACH KEEP-OUT (mm, measured on the pattern; minimum in brackets)", 2.0, 700)); ty += 4.5
    keys = [("FR", k) for k in F.MIN("FR")] + [("SR", k) for k in F.MIN("SR")]
    cx = 12; o.append(t(cx, ty, "Size", 1.5, 700, MUTED))
    hdrs = [f"{k} [{F.MIN('FR' if k in F.MIN('FR') else 'SR')[k]:.0f}]" for _, k in keys]
    for j, h in enumerate(hdrs): o.append(t(26 + j * 24, ty, h, 1.4, 700, MUTED))
    allok = True
    for i, sz in enumerate(SIZES):
        c = EP.clearances(sz); y = ty + 4 + i * 3.4
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y - 2.4)}" width="{SW - 22}" height="3.4" fill="{ALT}"/>')
        o.append(t(cx, y, sz, 1.5, 700))
        for j, (Pk, k) in enumerate(keys):
            pair = ("FR", "FL") if Pk == "FR" else ("SR", "SL")
            v = min(c[p][k] for p in pair if k in c[p]); mn = F.MIN(Pk)[k]; ok = v >= mn - 0.3; allok &= ok
            o.append(t(26 + j * 24, y, f"{v:.1f}", 1.45, 600 if not ok else 400, GREEN if ok else RED))
    y = ty + 4 + 7 * 3.4 + 2
    o.append(t(12, y, "All keep-outs pass on every size (fronts: min of FR/FL; sleeves: min of SR/SL)." if allok else "KEEP-OUT FAILURE", 1.7, 700, GREEN if allok else RED))
    y += 6
    o.append(t(12, y, "EMBROIDERY PER GARMENT (read back from the DST files)", 2.0, 700)); y += 4
    hd = ["Size", "FR st / trims", "FL st / trims", "SR st / trims", "SL st / trims", "Total st", "Hoopings", "Machine h (split files)"]
    cxs = [12, 24, 52, 80, 108, 136, 156, 174]
    for x_, h in zip(cxs, hd): o.append(t(x_, y, h, 1.45, 700, MUTED))
    for i, sz in enumerate(SIZES):
        yy = y + 3.6 + i * 3.0; r = ALLR[sz]
        o.append(t(cxs[0], yy, sz, 1.45, 700))
        for j, P in enumerate(kbcore.PIECES): o.append(t(cxs[1 + j], yy, f"{r[P]['full']['stitches']:,} / {r[P]['full']['trims']}", 1.4))
        o.append(t(cxs[5], yy, f"{sum(r[P]['full']['stitches'] for P in kbcore.PIECES):,}", 1.4, 600))
        o.append(t(cxs[6], yy, f"{sum(max(1, len(r[P]['splits']['sections'])) for P in kbcore.PIECES)}", 1.4))
        o.append(t(cxs[7], yy, f"{sum(mh(s) for P in kbcore.PIECES for s in r[P]['splits']['sections'].values()):.1f}", 1.4))
    yb = y + 3.6 + 7 * 3.0 + 2
    for l in ["Embroider the cut panels flat before assembly (fronts before zip + welts, sleeves before the underarm seam + cuff band).",
              "Backing 2.5 oz navy cutaway; welt boxes, zip and hem band are not embroidered; hood + back plain [proposed — confirm]."]:
        o.append(t(12, yb, l, 1.5, 400, MUTED)); yb += 3.1
    return o

def p_questions():
    o = SHT.header("OPEN QUESTIONS + REVISION LOG", "Everything still to confirm for the garment, in one place (embroidery questions: G4).", "T8")
    qs = ["1. Hood: block option 1 (engine hoodie block, 3-panel sherpa hood, elastic bands) — decided by the founder 19 Oct 2026; sizes Q/R still proposed (T3, T5).",
          f"2. Welts: at the mockup position + angle ({F.WELT_ANG:.0f}° from horizontal, centre {F.WELT_C[0]:.0f} from CF / {F.WELT_C[1]:.0f} below the CF neck at M), 1.4 × 13 — confirm.",
          "3. Shell: washed navy 12 oz duck, pre-washed before embroidery; wash-test the embroidered sample.",
          "4. Back + hood: no embroidery (the mockup shows the front only) — confirm.",
          "5. Hem band + cuff bands: the mockup flowers run over them; the art stops 10 above the band seams. OK?",
          "6. Sample plan: blank fit sample of the hoodie block (zip-hoodie-block T7) first, then the embroidered M sample.",
          "7. Product name: 'Blossom Tetra' (the fish are tetras, not koi) — slug + style code kept. Confirm the name."]
    y = 36
    for q in qs: o.append(t(12, y, q, 1.75, 400, PROP)); y += 4.6
    y += 6; o.append(t(12, y, "REVISION LOG", 2.4, 700)); y += 5
    import textwrap
    revs = [("Garment Rev A", DATE, "Garment pages + pattern: zip-hoodie block (founder decision 19 Oct, hood option 1) with this design's welt override (mockup welts, 60°)."),
            ] + [(f"Embroidery {rv}", dt, txt) for rv, dt, txt in kbcore.REV_LOG]
    for rv, dt, txt in revs:
        o.append(t(12, y, rv, 1.8, 700)); o.append(t(46, y, dt, 1.7))
        ls = textwrap.wrap(txt, 140)
        for j, l in enumerate(ls): o.append(t(70, y + j * 3.2, l, 1.7, 600 if "FOUNDER" in l else 400, RED if "FOUNDER" in l else INK))
        y += 3.2 * len(ls) + 3
    return o

PAGES = ["T1 Cover", "T2 Flats + construction", "T3 Size chart + measurement check", "T4 Pattern pieces + cut list", "T5 Hood + bands detail",
         "T6 Bill of materials", "T7 Embroidery placement on the pattern (all sizes)", "T8 Open questions + revision log"]

def build():
    fails = [sz for sz in SIZES if not (ZB.CHECK[sz] and ZB.WALKS_OK[sz] and ZB.SHAPE_OK[sz])]
    assert not fails, f"pattern QA failed: {fails}"
    PO.EMB_ON = {"F02": ["FR"], "F01": ["FL"], "S01": ["SR"], "S02": ["SL"]}
    PO.EMB_NAME = {"FR": "01 front fish FR", "FL": "01 front fish FL", "SR": "02 sleeve fish SR", "SL": "02 sleeve fish SL"}
    for sz in SIZES: PO.write_dxf([sz], f"{OUT}/pattern/{STYLE}_pattern_{sz}.dxf", blk=Blk, style=STYLE, emb=True)
    PO.write_dxf(SIZES, f"{OUT}/pattern/{STYLE}_pattern_ALL-SIZES.dxf", blk=Blk, style=STYLE, emb=True)
    PO.plot_pdf("M", f"{OUT}/pattern/{STYLE}_pattern_M_1to1_PLOT.pdf", blk=Blk, style=STYLE, emb=True)
    index = [(n, i + 1) for i, n in enumerate(PAGES)]
    pages = [p_cover(index), ZB.p_flats(), ZB.p_pom(), ZB.p_pieces(), ZB.p_hood(), ZB.p_bom(), p_placement(), p_questions()]
    w = PdfWriter()
    for i, pg in enumerate(pages, 1):
        svg = doc(pg); pdf = f"{OUT}/T{i}.pdf"
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=pdf)
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"{OUT}/prev_T{i}.png", output_width=2400)
        w.append(PdfReader(pdf))
    pdf = f"{OUT}/HAKI_{kbcore.SHORT}_GARMENT_{REV.replace(' ', '')}.pdf"; w.write(pdf)
    print("garment pages", len(pages), pdf, {sz: (ZB.CHECK[sz], ZB.WALKS_OK[sz], ZB.SHAPE_OK[sz]) for sz in SIZES})
    return pdf

if __name__ == "__main__":
    build()
