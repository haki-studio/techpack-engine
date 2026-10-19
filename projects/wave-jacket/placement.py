"""ART PLACEMENT ONLY - garment pattern to follow (review item 1, Rev B).
Size M, the five embroidered pieces of the Drum Island block (body unchanged, founder 19 Oct 2026), drawn 1:1:
cut line + sew line, keep-out line, art outline, hoop split lines, registration-cross positions, the needle start (origin)
of every stitch file, reference lines (CB / CF, sleeve centre line, the sleeve's y-origin = the underarm line) and the
seam MATCH MARKS (one notch per stripe that crosses a seam, same number + tone on both mating edges).
Outputs (out/placement/): HK-..._ART-PLACEMENT_M.pdf (one 1:1 page per piece), one DXF per piece + one with all five,
match_marks_M.json (also read by the spec + pack pages), preview PNGs.   usage: ./py.sh placement.py"""
import wavecore as WC
import os, io, json, pickle, math
import numpy as np
import ezdxf, cairosvg
from pypdf import PdfWriter, PdfReader
from shapely.geometry import Point, LineString
from shapely.ops import unary_union
import pattern as PT, pieces as PC, wrap as WR

SIZE = "M"; OUT = "out/placement"; os.makedirs(OUT, exist_ok=True)
D = pickle.load(open(f"art_{SIZE}.pkl", "rb"))
G, MT = PC.draft(SIZE)
LABEL = "ART PLACEMENT ONLY - garment pattern to follow"
SEAM_CODE = {"CF zip": "Z", "armhole back L": "AB-L", "armhole front L": "AF-L", "side L": "SD-L", "shoulder L": "SH-L",
             "underarm L": "UA-L", "armhole back R": "AB-R", "armhole front R": "AF-R", "side R": "SD-R", "shoulder R": "SH-R",
             "underarm R": "UA-R"}
TONE = {k: v[1] for k, v in WC.WV_PAL.items()}

def result(P): return json.load(open(f"out/01_wave/{SIZE}/result_{P}.json"))
def outline(P): return unary_union([r["geom"].buffer(0.3) for r in D[P]]).buffer(-0.3).simplify(0.3)

# ---------------------------------------------------------------- match marks: one per stripe crossing a seam
def match_marks(min_w=3.0):
    """for every seam (not the sleeve centre - it is not a seam): tone runs 1.5 mm inside the keep-out on the side with
    more art; one mark at the centre of each run >= min_w mm, at the same seam fraction on both pieces (the eased seam is
    sewn fraction to fraction). Tone = the thread at the mark on each side (they agree when the seam is continuous)."""
    out = {}
    for sm in WR.seams(SIZE):
        if sm["kind"] == "internal": continue
        A, B = WR.SeamSide(SIZE, sm, "A"), WR.SeamSide(SIZE, sm, "B")
        d0 = (15.0 if sm["kind"] == "zip" else WR.GAP + 0.4) + 1.5
        band = lambda P: [r for r in D[P] if r["grp"] in ("WV", "RP", "FM", "FM-sh", "FM-gr", "DR")]
        la = WR.labels(band(A.P), A, d0, step=1.0); lb = WR.labels(band(B.P), B, d0, step=1.0 * B.L / A.L)
        n = min(len(la), len(lb)); la, lb = la[:n], lb[:n]
        lead = la if sum(x is not None for x in la) >= sum(x is not None for x in lb) else lb
        marks = []; i = 0
        while i < n:
            k = lead[i]
            if k is None: i += 1; continue
            j = i
            while j + 1 < n and lead[j + 1] == k: j += 1
            if j - i + 1 >= min_w and k not in ("w3", "g1"):
                m = 0.5 * (i + j); u = min(m / A.L, 1.0)
                pa, pb = A.point(u, 0), B.point(u, 0)
                ta, tb = la[int(round(m))], lb[int(round(m))]
                marks.append(dict(u=round(u, 4), s_A=round(u * A.L, 1), s_B=round(u * B.L, 1), w=j - i + 1, tone_A=ta, tone_B=tb,
                                  pt_A=[round(pa[0], 1), round(pa[1], 1)], pt_B=[round(pb[0], 1), round(pb[1], 1)],
                                  n_A=[round(float(x), 4) for x in A.normal_in(u)], n_B=[round(float(x), 4) for x in B.normal_in(u)]))
            i = j + 1
        if marks:
            code = SEAM_CODE[sm["name"]]
            for q, mk in enumerate(marks, 1): mk["id"] = f"{code}{q}"
            out[sm["name"]] = dict(code=code, A=A.P, B=B.P, len_A=round(A.L, 1), len_B=round(B.L, 1), marks=marks,
                                   agree=sum(1 for mk in marks if mk["tone_A"] == mk["tone_B"]))
    return out

def marks_on(P, MM):
    """[(id, tone, point, inward normal)] on piece P"""
    lst = []
    for nm, s in MM.items():
        for mk in s["marks"]:
            if s["A"] == P: lst.append((mk["id"], mk["tone_A"], mk["pt_A"], mk["n_A"]))
            if s["B"] == P: lst.append((mk["id"], mk["tone_B"], mk["pt_B"], mk["n_B"]))
    return lst

def refs(P):
    """reference lines [(name, pts)] in piece coords"""
    pc = G[PC.CODE[P]]; b = PT.cut_poly(pc).bounds
    if P == "BK": return [("CB", [(0, b[1]), (0, b[3])]), ("CB neck seam level y = 0", [(-40, 0), (40, 0)])]
    if P in ("FR", "FL"): return [("CF (x = 0)", [(0, b[1]), (0, b[3])]), ("CF neck seam level y = 0", [(-30 if P == "FR" else 0, 0), (0 if P == "FR" else 30, 0)])]
    return [("sleeve centre line (x = 0)", [(0, b[1]), (0, b[3])]), ("underarm line (y = 0, sleeve y-origin)", [(b[0], 0), (b[2], 0)])]

def section_items(P):
    r = result(P); sp = r.get("splits") or {}; out = []
    out.append(("full file", r["full"]["origin"], r["full"]["file"]))
    for nm, s in sp.get("sections", {}).items(): out.append((nm, s["origin"], s["file"]))
    crosses = [tuple(m) for s in sp.get("sections", {}).values() for m in s.get("marks", [])]
    lines = [("split", [(r["full"]["art_box"][0] - 8, y), (r["full"]["art_box"][2] + 8, y)]) for y in sp.get("ys", [])] + \
            [("split", [(x, r["full"]["art_box"][1] - 8), (x, r["full"]["art_box"][3] + 8)]) for x in sp.get("xs", [])]
    return out, sorted(set(crosses)), lines

# ---------------------------------------------------------------- DXF
def dxf_piece(doc, P, MM, dx=0.0, dy=0.0):
    pc = G[PC.CODE[P]]; msp = doc.modelspace()
    F = lambda pts: [(x + dx, -(y + dy)) for x, y in pts]
    cut = PT.cut_poly(pc)
    msp.add_polyline2d(F(list(cut.exterior.coords)), close=True, dxfattribs={"layer": "1"})
    msp.add_polyline2d(F(pc.sew()), close=True, dxfattribs={"layer": "14"})
    for a, b in pc.notch_marks(): msp.add_line(F([a])[0], F([b])[0], dxfattribs={"layer": "4"})
    g0, g1 = pc.grain; msp.add_line(F([g0])[0], F([g1])[0], dxfattribs={"layer": "7"})
    for q in WR.polys_of(PC.clip_for(SIZE, P)): msp.add_polyline2d(F(list(q.exterior.coords)), close=True, dxfattribs={"layer": "KEEP-OUT"})
    for q in WR.polys_of(outline(P)):
        if q.area > 4: msp.add_polyline2d(F(list(q.exterior.coords)), close=True, dxfattribs={"layer": "8"})
    secs, crosses, lines = section_items(P)
    for nm, pts in lines: msp.add_line(*F(pts), dxfattribs={"layer": "8"})
    for x, y in crosses:
        msp.add_line(*F([(x - 6, y), (x + 6, y)]), dxfattribs={"layer": "8"}); msp.add_line(*F([(x, y - 6), (x, y + 6)]), dxfattribs={"layer": "8"})
    for nm, (x, y), f_ in secs:
        msp.add_point(F([(x, y)])[0], dxfattribs={"layer": "13"})
        msp.add_line(*F([(x - 10, y), (x + 10, y)]), dxfattribs={"layer": "13"}); msp.add_line(*F([(x, y - 10), (x, y + 10)]), dxfattribs={"layer": "13"})
        msp.add_text(f"{os.path.basename(f_)} start", dxfattribs={"layer": "15", "height": 4, "insert": F([(x + 3, y - 3)])[0]})
    for mid, tone, (x, y), (nx, ny) in marks_on(P, MM):
        msp.add_line(*F([(x - nx * 4, y - ny * 4), (x + nx * 6, y + ny * 6)]), dxfattribs={"layer": "4"})
        msp.add_text(f"{mid} {tone or ''}", dxfattribs={"layer": "15", "height": 3, "insert": F([(x + nx * 8, y + ny * 8)])[0]})
    for nm, pts in refs(P):
        msp.add_line(*F(pts), dxfattribs={"layer": "REF"})
    b = cut.bounds
    for i, l in enumerate([f"Piece Name: {pc.code} {pc.name}", f"Size: {SIZE}", f"Style Name: {WC.STYLE}", LABEL, "Units: mm",
                           "Layers: 1 cut, 14 sew, 4 notches + MATCH MARKS, 7 grain, 8 art outline + split lines + reg crosses,",
                           "13 file origins (needle start), KEEP-OUT art limit, REF reference lines, 15 text"]):
        msp.add_text(l, dxfattribs={"layer": "15", "height": 5, "insert": F([(b[0], b[1] - 40 + i * 7)])[0]})
    return b

def write_dxfs(MM):
    paths = []
    def new():
        doc = ezdxf.new("R12")
        for ln in ("1", "4", "7", "8", "13", "14", "15", "KEEP-OUT", "REF"): doc.layers.add(ln)
        return doc
    for P in WC.PIECES:
        doc = new(); dxf_piece(doc, P, MM); p = f"{OUT}/{WC.STYLE}_ART-PLACEMENT_{SIZE}_{P}.dxf"; doc.saveas(p); paths.append(p)
    doc = new(); x = 0.0
    for P in WC.PIECES:
        b = PT.cut_poly(G[PC.CODE[P]]).bounds; dxf_piece(doc, P, MM, dx=x - b[0], dy=0.0); x += (b[2] - b[0]) + 80
    p = f"{OUT}/{WC.STYLE}_ART-PLACEMENT_{SIZE}_ALL.dxf"; doc.saveas(p); paths.append(p)
    return paths

# ---------------------------------------------------------------- 1:1 PDF
def path_d(pts, close=True):
    return "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts) + (" Z" if close else "")

def svg_piece(P, MM, scale=1.0, for_png=False):
    pc = G[PC.CODE[P]]; cut = PT.cut_poly(pc); b = cut.bounds; m = 30.0
    W = (b[2] - b[0]) + 2 * m; H = (b[3] - b[1]) + 2 * m + 60
    X = lambda x: x - b[0] + m; Y = lambda y: y - b[1] + m + 60
    T = lambda pts: [(X(x), Y(y)) for x, y in pts]
    o = [f'<rect width="{W:.1f}" height="{H:.1f}" fill="#FFFFFF"/>']
    o.append(f'<path d="{path_d(T(cut.exterior.coords))}" fill="none" stroke="#000" stroke-width="0.6"/>')
    o.append(f'<path d="{path_d(T(pc.sew()))}" fill="none" stroke="#000" stroke-width="0.35" stroke-dasharray="4 2"/>')
    for a, b_ in pc.notch_marks(): o.append(f'<path d="{path_d(T([a, b_]), False)}" stroke="#000" stroke-width="0.6"/>')
    for q in WR.polys_of(PC.clip_for(SIZE, P)): o.append(f'<path d="{path_d(T(q.exterior.coords))}" fill="none" stroke="#E07B00" stroke-width="0.35" stroke-dasharray="2 1.5"/>')
    for q in WR.polys_of(outline(P)):
        if q.area > 4:
            o.append(f'<path d="{path_d(T(q.exterior.coords))}" fill="#1F65A8" fill-opacity="0.10" stroke="#1F65A8" stroke-width="0.4"/>')
            for h in q.interiors:
                if Polygon_area(h) > 30: o.append(f'<path d="{path_d(T(h.coords))}" fill="none" stroke="#1F65A8" stroke-width="0.2"/>')
    for nm, pts in refs(P):
        o.append(f'<path d="{path_d(T(pts), False)}" stroke="#7A2BB5" stroke-width="0.35" stroke-dasharray="8 3 1 3"/>')
        x0, y0 = T(pts)[0]; o.append(f'<text x="{x0 + 2:.1f}" y="{y0 + 6:.1f}" font-size="4" fill="#7A2BB5" font-family="Liberation Sans">{nm}</text>')
    secs, crosses, lines = section_items(P)
    for nm, pts in lines:
        o.append(f'<path d="{path_d(T(pts), False)}" stroke="#C8162B" stroke-width="0.5" stroke-dasharray="6 3"/>')
        x0, y0 = T(pts)[0]; o.append(f'<text x="{x0:.1f}" y="{y0 - 2:.1f}" font-size="4" fill="#C8162B" font-family="Liberation Sans">hoop split line</text>')
    for x, y in crosses:
        (x_, y_), = T([(x, y)])
        o.append(f'<path d="M{x_-6:.1f},{y_:.1f} L{x_+6:.1f},{y_:.1f} M{x_:.1f},{y_-6:.1f} L{x_:.1f},{y_+6:.1f}" stroke="#C8162B" stroke-width="0.4"/>')
    for nm, (x, y), f_ in secs:
        (x_, y_), = T([(x, y)])
        o.append(f'<circle cx="{x_:.1f}" cy="{y_:.1f}" r="3" fill="none" stroke="#0A7D3B" stroke-width="0.5"/><path d="M{x_-8:.1f},{y_:.1f} L{x_+8:.1f},{y_:.1f} M{x_:.1f},{y_-8:.1f} L{x_:.1f},{y_+8:.1f}" stroke="#0A7D3B" stroke-width="0.5"/>')
        o.append(f'<text x="{x_ + 4:.1f}" y="{y_ - 4:.1f}" font-size="3.6" fill="#0A7D3B" font-family="Liberation Sans">{nm} start ({x:.1f}, {y:.1f})</text>')
    for mid, tone, (x, y), (nx, ny) in marks_on(P, MM):
        a = T([(x - nx * 4, y - ny * 4)])[0]; c = T([(x + nx * 7, y + ny * 7)])[0]; tt = T([(x + nx * 10, y + ny * 10)])[0]
        o.append(f'<path d="M{a[0]:.1f},{a[1]:.1f} L{c[0]:.1f},{c[1]:.1f}" stroke="#D1007A" stroke-width="0.7"/>')
        o.append(f'<text x="{tt[0]:.1f}" y="{tt[1]:.1f}" font-size="3.2" fill="#D1007A" font-family="Liberation Sans" text-anchor="middle">{mid}</text>')
    o.append(f'<rect x="{m}" y="8" width="100" height="25" fill="none" stroke="#000" stroke-width="0.4"/>')
    o.append(f'<text x="{m + 2}" y="18" font-size="5" font-family="Liberation Sans">TEST: 100 mm</text>')
    o.append(f'<text x="{m + 2}" y="28" font-size="4" font-family="Liberation Sans">print at 100 % - no scaling</text>')
    o.append(f'<text x="{m + 110}" y="16" font-size="7" font-weight="700" fill="#C8162B" font-family="Liberation Sans">{LABEL}</text>')
    o.append(f'<text x="{m + 110}" y="25" font-size="5" font-weight="700" font-family="Liberation Sans">{WC.STYLE} - {pc.code} {PC.NAME[P]} ({P}) - size {SIZE} - embroidery {WC.REV_EMB}</text>')
    o.append(f'<text x="{m + 110}" y="32" font-size="3.8" font-family="Liberation Sans">Drum Island block (body unchanged). Solid = cut line, dashed = sew line, orange = art limit (keep-outs), blue = art outline,</text>')
    o.append(f'<text x="{m + 110}" y="37" font-size="3.8" font-family="Liberation Sans">red dashed = hoop split line, red + = registration crosses, green (+) = needle start (origin) of each file, magenta ticks = seam MATCH MARKS</text>')
    o.append(f'<text x="{m + 110}" y="42" font-size="3.8" font-family="Liberation Sans">(same id on both mating pieces: the stripe crossing there must meet its partner when sewn). Coordinates: G2 / G6. Mark ids + tones: G7.</text>')
    w_, h_ = (W * scale, H * scale)
    unit = "" if for_png else "mm"
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w_:.1f}{unit}" height="{h_:.1f}{unit}" viewBox="0 0 {W:.1f} {H:.1f}">' + "".join(o) + "</svg>"

def Polygon_area(ring):
    from shapely.geometry import Polygon
    return Polygon(ring).area

def build():
    MM = match_marks()
    json.dump(MM, open(f"{OUT}/match_marks_{SIZE}.json", "w"), indent=1)
    w = PdfWriter()
    for P in WC.PIECES:
        buf = io.BytesIO(); cairosvg.svg2pdf(bytestring=svg_piece(P, MM).encode(), write_to=buf); buf.seek(0); w.append(PdfReader(buf))
        cairosvg.svg2png(bytestring=svg_piece(P, MM, scale=2.0, for_png=True).encode(), write_to=f"{OUT}/placement_{SIZE}_{P}.png")
    pdf = f"{OUT}/{WC.STYLE}_ART-PLACEMENT_{SIZE}_1to1.pdf"; w.write(pdf)
    paths = write_dxfs(MM)
    tot = sum(len(s["marks"]) for s in MM.values()); agree = sum(s["agree"] for s in MM.values())
    print("placement", pdf, paths[-1], f"match marks {tot} on {len(MM)} seams, tone agrees on both sides {agree}/{tot}")
    return MM

if __name__ == "__main__":
    build()
