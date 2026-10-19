"""Garment pages T1-T8 + pattern files for the Red Beast hoodie, on the zip-hoodie block (founder decision 19 Oct 2026:
engine/hoodie.py = Drum Island body + 3-panel sherpa hood + elastic hem/cuff bands).

Reuses the block's own page builders (projects/zip-hoodie-block/build.py + hflat.py, imported, not copied) with this
design's deltas: the moved welt [PROPOSED] (engine per-design override), the embroidery drawn on the flats, embroidery
marks on the DXF (layer 8 outline/box/centre, layer 13 needle start) and the 1:1 plot, design-specific notes/questions.
usage: python3 garment.py   -> out/pattern/*.dxf, *_1to1_PLOT.pdf, out/pages/T*.pdf + prev_T*.png, pattern_qa.json"""
import rbcore
import os, sys, json, pickle, importlib.util
import cairosvg
from pypdf import PdfWriter, PdfReader
from shapely.ops import unary_union
from shapely import affinity
import front as F, hoodie as HD, pattern_out as PO, pattern as PT, emb_place as EP
import sheet as SHT
from sheet import t, doc, INK, MUTED, RED, GREEN, SW, SH
from render import f
from motifs2 import HEX

BLOCK_DIR = os.path.abspath(os.path.join(rbcore.HERE, "..", "zip-hoodie-block"))
sys.path.insert(0, BLOCK_DIR)
import hflat as HF
spec = importlib.util.spec_from_file_location("hblock", os.path.join(BLOCK_DIR, "build.py"))
BM = importlib.util.module_from_spec(spec); spec.loader.exec_module(BM)

STYLE, NAME, REV, DATE = rbcore.STYLE, rbcore.NAME, rbcore.REV_GAR, rbcore.DATE
WELT = json.load(open("welt.json"))
SHT.FOOT = f"HAKI STUDIOS · {NAME} · {STYLE} · GARMENT · {REV} · {DATE}"

class Block(HD.Variant):
    """hoodie.Variant + the module attributes pattern_out needs (ORDER; ENGINE_NOTES 11)"""
    ORDER = HD.ORDER
    def __getattr__(self, k): return getattr(HD, k)
BLK = Block(welt=F.WELT_SPEC)

# ---------------------------------------------------------------- the block module, with this design's data
BM.STYLE, BM.REV, BM.DATE, BM.NAME = STYLE, REV, DATE, NAME
BM.G = {sz: F.pieces(sz) for sz in BM.SIZES}
BM.gM, BM.mM = BM.G["M"]

# welts on the flats = this design's moved welt (front mm from the CF neck seam -> flat mm from the HPS line)
def _welt(self, side=1):
    W = F.WELT_L if side == 1 else F.WELT_R
    return affinity.translate(W, 0, self.fnd)
HF.Flat.welt = _welt

# embroidery on the front flat: the size-M art, one fill per thread (front mm -> flat mm)
ART = pickle.load(open("art_M.pkl", "rb"))
_ART_SVG = {}
def art_svg(Fl):
    if "f" not in _ART_SVG:
        o = []
        for col in rbcore.SEW:
            gs = [r["geom"] for P in ("FR", "FL") for r in ART[P] if r["col"] == col and r["st"] != "bean"]
            if not gs: continue
            u = unary_union([g.buffer(0.15) for g in gs]).simplify(0.35)
            u = affinity.translate(u, 0, Fl.fnd)
            o.append(f'<path d="{HF.poly_path(u)}" fill="{HEX[col]}" stroke="none" fill-rule="evenodd"/>')
        o.append(sleeve_svg(Fl))
        _ART_SVG["f"] = "".join(o)
    return _ART_SVG["f"]
def sleeve_svg(Fl):
    """02 sleeve streaks on the front flat (schematic): sleeve pattern mm (y from the underarm line, cap top -cap_h,
    cuff seam Lu; |x| = across the front half, 0 = top line = the flat's outer silhouette) -> flat mm, along the flat
    sleeve by y and across it by |x| / the front-half width at that y"""
    import numpy as np
    from shapely.ops import transform
    from shapely.geometry import LineString as LS
    g, mt = F.pieces("M"); o = []
    for P, key, sgn in (("SR", "S01", -1), ("SL", "S02", 1)):
        pc = g[key].sew_poly(); x0, ytop, x1, ycuf = pc.bounds
        def W(y):
            seg = pc.intersection(LS([(0, y), (-sgn*400 if key == "S02" else 400, y)]))
            if seg.is_empty: return 1.0
            b = seg.bounds; return max(abs(b[0]), abs(b[2]), 1.0)
        ys = np.linspace(ytop + 0.5, ycuf - 0.5, 120); Ws = np.array([W(y) for y in ys])
        sp, ua, cso, csi = np.array(Fl.sp), np.array(Fl.ua), np.array(Fl.cs_out), np.array(Fl.cs_in)
        def fmap(x, y, z=None):
            x = np.asarray(x); y = np.asarray(y)
            v = (y - ytop)/(ycuf - ytop); outer = sp[:, None] + (cso - sp)[:, None]*v
            inner = np.where(y < 0, sp[:, None] + (ua - sp)[:, None]*((y - ytop)/(-ytop)), ua[:, None] + (csi - ua)[:, None]*(np.maximum(y, 0)/ycuf))
            u = np.clip(np.abs(x)/np.interp(y, ys, Ws), 0, 1)
            p = outer + (inner - outer)*u
            return (sgn*p[0], p[1])
        for col in rbcore.SEW:
            gs = [r["geom"] for r in ART[P] if r["col"] == col and r["st"] != "bean"]
            if not gs: continue
            u_ = transform(fmap, unary_union([q.buffer(0.15) for q in gs]).simplify(0.35)).buffer(0)
            o.append(f'<path d="{HF.poly_path(u_)}" fill="{HEX[col]}" stroke="none" fill-rule="evenodd"/>')
    return "".join(o)

_draw_front = HF.draw_front
def draw_front(Fl):
    s = _draw_front(Fl)
    zp = HF.zip_tape(Fl, Fl.fnd - 2, Fl.hem_edge)
    k = s.rfind(zp) if zp in s else len(s)
    return s[:k] + art_svg(Fl) + s[k:]
HF.draw_front = draw_front
HF.SHELL, HF.SHELL_D = "#4A505B", "#3A3F48"          # washed black shell on the flats (the art reads on it, as on the garment)
CUR = json.load(open("dst_current.json"))

BM.NOTES = [("1", "Hood: 3 panels — side pair + 10 cm centre panel, shell outside, cream sherpa inside, bagged at the face edge; 6 mm topstitch. No drawcord. No embroidery on the hood.", True),
            ("2", "Hood neck: shell hood to body neckline, sherpa hood to front facings + back neck facing — neck seam enclosed. Notch at HPS = shoulder seam.", False),
            ("3", "Zip: 2-way separating, YKK #5 metal, antique brass, hem-band edge to CF neck. Embroidery stops 15 mm each side of CF.", True),
            ("4", f"Welt pockets MOVED {WELT['move_mm'][0]:.0f} mm out + {WELT['move_mm'][1]:.1f} mm down from the render (same angle + length): the render draws the wearer's-left welt under the beast's jaw.", True),
            ("5", f"Hem band: self fabric, {HD.hcm('S','M')/10:.1f} cm finished, folded; {HD.EL_HEM_W/10:.0f} cm elastic, flat {HD.FLAT/10:.0f} cm each side of the zip. Not embroidered.", True),
            ("6", f"Cuff band: self fabric, {HD.hcm('T','M')/10:.1f} cm finished, folded, closed into a loop; {HD.EL_CUFF_W/10:.1f} cm elastic. Not embroidered.", True),
            ("7", "Embroidery: both fronts (01 beast head) + front half of both sleeves (02 streaks), sewn flat on the cut panels BEFORE assembly (G pages).", False),
            ("8", "Lining: flannel body, taffeta sleeves, sherpa hood. Back: plain [proposed]. Main + size label on the back neck facing.", True)]

def p_cover(index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>', t(14, 22, "HAKI STUDIOS", 3.0, 700, MUTED), t(14, 34, NAME, 7.0, 700),
         t(14, 41.5, f"Style {STYLE} · garment {REV} · embroidery {rbcore.REV_EMB} · {DATE} · XS–3XL · base size M · zip-hoodie block (Drum Island body)", 2.5, 400, MUTED),
         f'<line x1="14" y1="45" x2="{SW-14}" y2="45" stroke="{INK}" stroke-width="0.4"/>']
    Fl = HF.Flat("M")
    for i, (fn, back, lab) in enumerate(((HF.draw_front, False, "FRONT (01 beast head, 02 sleeve streaks)"), (HF.draw_back, True, "BACK (plain [proposed])"))):
        b = HF.bounds(Fl, back); s = 88 / (b[2] - b[0]); ox = 14 + i * 96
        o.append(BM.flat_g(fn(Fl), b, ox, 52, s)); o.append(t(ox, 52 + (b[3] - b[1]) * s + 5, lab, 2.0, 700))
    ix = 206; o.append(t(ix, 56, "CONTENTS", 2.8, 700)); y = 62
    for name, pg in index: o.append(t(ix, y, name, 1.85)); o.append(t(SW - 14, y, str(pg), 1.85, 600, MUTED, "end")); y += 3.6
    y += 3; o.append(t(ix, y, "KEY SPECS", 2.4, 700)); y += 4.6
    for a, b_, p in [("Block", "zip hoodie = Drum Island body + sleeve (approved fit)", False), ("Hood", "3 panels, sherpa-lined, no drawcord", True),
                     ("Hem / cuffs", "self fabric + elastic bands", True), ("Zip", "2-way separating, YKK #5 metal", True),
                     ("Shell", "washed black 12 oz cotton duck", True), ("Welts", f"moved {WELT['move_mm'][0]:.0f} out / {WELT['move_mm'][1]:.1f} down", True),
                     ("Embroidery", "fronts + sleeves, 5 threads (G pages)", False), ("Pattern", "XS–3XL, DXF (AAMA) + 1:1 plot", False)]:
        o.append(t(ix, y, a, 1.9, 400, MUTED)); o.append(t(ix + 23, y, b_, 1.85, 600, BM.PROP if p else INK)); y += 3.7
    y += 3
    for l in ["Body, sleeve, facings, lining = the approved Drum Island jacket; hood + bands = the zip-hoodie block.",
              "Sew a blank fit sample of the block before the first embroidered sample (LESSONS C9).",
              "Amber = proposed by Haki tech design — confirm."]:
        o.append(t(ix, y, l, 1.55)); y += 3.1
    o.append(t(SW - 14, SH - 8, SHT.FOOT, 1.8, 400, MUTED, "end"))
    return o

def p_fit():
    o = BM.H("SAMPLE CHECKS + OPEN QUESTIONS (garment)", "Block fit is checked on the blank sample; the embroidered sample checks placement, welts and the hand of the dense head.", "T7")
    checks = ["Block blank fit sample approved first (hood, bands, zip — zip-hoodie block T7).",
              "Embroidery placement: FR + FL head meets across the zip at the same height (±1 mm); 15 mm clear of the zip tape each side.",
              "Welt pockets at the moved position: openings 6 mm or more from the stitching; pocket bags clear of the embroidered area.",
              f"Dense head (FL {CUR['FL']['stitches']:,} stitches, DST): panel lies flat after embroidery, no puckering at the welt or side seam; backing trimmed to 5 mm.",
              "Sleeves: streaks on the front half, 15 mm clear of cap + underarm seams; the sleeve still eases into the armhole (no shrink from embroidery).",
              "Hood + back plain; sherpa hood lining clean at the neck seam."]
    o.append(t(12, 34, "CHECK ON THE EMBROIDERED SAMPLE", 2.4, 700)); y = 40
    for c in checks:
        o.append(f'<rect x="12" y="{f(y - 2.2)}" width="2.6" height="2.6" fill="none" stroke="{INK}" stroke-width="0.25"/>'); o.append(t(16.5, y, c, 1.75)); y += 4.4
    y += 4; o.append(t(12, y, "OPEN QUESTIONS — garment", 2.4, 700)); y += 6
    qs = [f"1. Welts [PROPOSED]: moved {WELT['move_mm'][0]:.0f} mm out + {WELT['move_mm'][1]:.1f} mm down (render: wearer's-left welt under the jaw). OK, or move the art instead?",
          "2. Back + hood: plain (the mockup shows the front only). Confirm, or send a back / hood mockup (hood panels H01/H02 can take embroidery).",
          "3. Hood size, drawcord, hem gather, zip, sherpa weight: as the zip-hoodie block (its T7 questions) — answer once for every hoodie on the block.",
          "4. Shell: washed black 12 oz duck, washed before embroidery; garment-wash after embroidery needs a wash test of the dense head.",
          "5. Labels + care: main + size label on the back neck facing; care label in the left side seam lining."]
    for q in qs: o.append(t(12, y, q, 1.75, 400, BM.PROP)); y += 4.4
    return o

def p_revisions():
    o = BM.H("REVISION LOG + SAMPLE TRACKER", "Every change to this garment, newest last.", "T8")
    revs = [("Emb Rev A", "16 Oct 2026", "Embroidery traced from the mockup + head close-up; 28 stitch files + splits; garment pages waited for the hood decision."),
            ("Emb Rev B", DATE, "Independent review fixes: stroke-structure art (hair, shade and black strokes along the traced flow), raised cords at the traced width with crimson under-edge, teeth as objects, streak bundles cut into fine strips; A14/A15 gates; compare sheets from the DST read-back."),
            ("Garment Rev A", DATE, "Founder chose the zip-hoodie block (Drum Island body + hood + elastic bands). Pattern XS–3XL with the moved welts (per-design override) [PROPOSED]; DXF with embroidery marks; T pages.")]
    y = 36
    for rv, dt, ch in revs:
        o.append(t(12, y, rv, 1.8, 700)); o.append(t(40, y, dt, 1.7))
        words = ch.split(); line, lines = "", []
        for w in words:
            if len(line) + len(w) > 140: lines.append(line); line = w
            else: line = (line + " " + w).strip()
        lines.append(line)
        for j, l in enumerate(lines): o.append(t(64, y + j * 3.2, l, 1.7))
        y += 3.2 * len(lines) + 4
    y += 4; o.append(t(12, y, "SAMPLE TRACKER", 2.4, 700)); y += 5
    for i, sname in enumerate(["Block blank fit sample (M) approved", "Embroidery strike-off, size M files (F1)", "First embroidered sample (M)", "Size set"]):
        yy = y + i * 9
        o.append(f'<rect x="11" y="{f(yy - 4)}" width="{SW - 22}" height="9" fill="{BM.ALT if i % 2 == 0 else "#FFFFFF"}" stroke="#DDD" stroke-width="0.2"/>')
        o.append(t(13, yy + 1, sname, 1.8, 600))
    return o

PAGES = ["T1 Cover", "T2 Flats + construction", "T3 Size chart + measurement check", "T4 Pattern pieces + cut list", "T5 Hood + bands detail",
         "T6 Bill of materials", "T7 Sample checks + open questions", "T8 Revision log + sample tracker"]

# embroidery marks on the pattern (pattern_out.emb_marks reads EMB_ON / EMB_NAME and this project's emb_place)
PO.EMB_ON = {"F01": ["FL"], "F02": ["FR"], "S01": ["SR"], "S02": ["SL"]}
PO.EMB_NAME = {"FL": "01 beast head FL", "FR": "01 beast head FR", "SR": "02 streaks SR", "SL": "02 streaks SL"}

def pattern_files():
    os.makedirs("out/pattern", exist_ok=True)
    for sz in BM.SIZES: PO.write_dxf([sz], f"out/pattern/{STYLE}_pattern_{sz}.dxf", blk=BLK, style=STYLE)
    PO.write_dxf(BM.SIZES, f"out/pattern/{STYLE}_pattern_ALL-SIZES.dxf", blk=BLK, style=STYLE)
    PO.plot_pdf("M", f"out/pattern/{STYLE}_pattern_M_1to1_PLOT.pdf", blk=BLK, style=STYLE)

def qa():
    out = {}
    for sz in BM.SIZES:
        out[sz] = dict(chart=bool(BM.CHECK[sz]), walks=bool(BM.WALKS_OK[sz]), shape=bool(BM.SHAPE_OK[sz]))
        g, _ = BM.G[sz]
        wl = F.keep_geoms(sz, "L")["welt"]; out[sz]["welt_bounds_L"] = [round(v, 1) for v in wl.bounds]
    json.dump(out, open("pattern_qa.json", "w"), indent=1)
    return out

def build():
    q = qa()
    for sz, r in q.items(): assert r["chart"] and r["walks"] and r["shape"], f"pattern QA failed {sz}: {r}"
    pattern_files()
    index = [(n, i + 1) for i, n in enumerate(PAGES)]
    pages = [p_cover(index), BM.p_flats(), BM.p_pom(), BM.p_pieces(), BM.p_hood(), BM.p_bom(), p_fit(), p_revisions()]
    os.makedirs("out/pages", exist_ok=True); w = PdfWriter()
    for i, pg in enumerate(pages, 1):
        svg = doc(pg).replace("⊕ = drill holes", "circles = drill holes"); pdf = f"out/pages/T{i}.pdf"
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=pdf)
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"prev_T{i}.png", output_width=2400)
        w.append(PdfReader(pdf))
    w.write(f"out/HAKI_{rbcore.SHORT}_GARMENT-PAGES_{REV.replace(' ', '')}.pdf")
    print("T pages", len(pages), "QA", {sz: all(v for k, v in r.items() if k != "welt_bounds_L") for sz, r in q.items()})

if __name__ == "__main__":
    build()
