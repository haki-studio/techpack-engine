"""Pattern outputs: AAMA-style DXF (per size + all sizes), 1:1 plot PDF (one page per piece), pattern QA."""
import os, json, math, io
import numpy as np
import ezdxf, cairosvg
from pypdf import PdfWriter, PdfReader
from shapely.geometry import Point, LineString, Polygon
import pattern as PT, pattern_draw as PD, emb_place as EP, drum

STYLE = "HK-JK-DRUM-PP"; OUTD = "out/pattern"; os.makedirs(OUTD, exist_ok=True)
EMB_ON = {"B01": ["back"], "F01": ["02L", "03"], "F02": ["02R", "04"], "S01": ["sleeve"]}
EMB_NAME = {"back": "01 back scene", "sleeve": "01 sleeve wrap", "02R": "02R chest branch", "02L": "02L chest branch", "03": "03 chest pine", "04": "04 lower bamboo"}

def emb_marks(size, pl=None):
    """{piece_code: [(name, pts, kind)]} — art outline, art box and design centre (= DST origin / needle start)."""
    pl = pl or EP.place(size)[0]; out = {}
    for pc, elems in EMB_ON.items():
        lst = []
        for e in elems:
            _, geom = pl[e]
            polys = [geom] if geom.geom_type == "Polygon" else [q for q in getattr(geom, "geoms", []) if q.geom_type == "Polygon"]
            for q in polys:
                if q.area > 4: lst.append((EMB_NAME[e], list(q.simplify(0.8).exterior.coords), "outline"))
            b = geom.bounds
            lst.append((EMB_NAME[e] + " art box", [(b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3])], "box"))
            lst.append((EMB_NAME[e] + " centre", [((b[0]+b[2])/2, (b[1]+b[3])/2)], "cross"))
        out[pc] = lst
    return out

# ---------------------------------------------------------------- DXF (AAMA layer convention)
def add_block(doc, pc, size, emb=()):
    name = f"{pc.code}_{size}"; blk = doc.blocks.new(name=name)
    F = lambda pts: [(x, -y) for x, y in pts]
    cut = PT.cut_poly(pc)
    blk.add_polyline2d(F(list(cut.exterior.coords)), close=True, dxfattribs={"layer": "1"})
    if not getattr(pc, "inset", 0):
        blk.add_polyline2d(F(pc.sew()), close=True, dxfattribs={"layer": "14"})
        for a, b in pc.notch_marks():
            blk.add_line(F([a])[0], F([b])[0], dxfattribs={"layer": "4"})
        for nm, pts in pc.internal:
            blk.add_polyline2d(F(pts), dxfattribs={"layer": "8"})
        for x, y in pc.drills:
            blk.add_point((x, -y), dxfattribs={"layer": "13"})
    (g0, g1) = pc.grain
    blk.add_line(F([g0])[0], F([g1])[0], dxfattribs={"layer": "7"})
    for nm, pts, kind in emb:
        if kind == "cross":
            (x, y), = pts
            blk.add_line((x - 8, -y), (x + 8, -y), dxfattribs={"layer": "8"}); blk.add_line((x, -y - 8), (x, -y + 8), dxfattribs={"layer": "8"})
            blk.add_point((x, -y), dxfattribs={"layer": "13"})
        else:
            blk.add_polyline2d(F(pts), close=True, dxfattribs={"layer": "8"})
    c = cut.representative_point(); tx, ty = c.x, -c.y
    lines = [f"Piece Name: {pc.code} {pc.name}", f"Size: {size}", f"Quantity: {pc.qty}", f"Material: {pc.material}",
             f"Category: {pc.category}", f"Style Name: {STYLE}", "Units: mm"]
    if pc.fuse: lines.append("Fuse: yes")
    for i, l in enumerate(lines):
        blk.add_text(l, dxfattribs={"layer": "15", "height": 6, "insert": (tx - 60, ty - i * 9)})
    return name, cut.bounds

def write_dxf(sizes, path, pieces=None):
    doc = ezdxf.new("R12"); msp = doc.modelspace()
    for ln in ("1", "4", "7", "8", "13", "14", "15"): doc.layers.add(ln)
    y0 = 0.0
    for size in sizes:
        g, mt = PT.draft(size); em = emb_marks(size) if size else {}
        x0 = 0.0; rowh = 0.0
        for code in (pieces or PT.ORDER):
            pc = g[code]; name, b = add_block(doc, pc, size, em.get(code, ()))
            w, h = b[2] - b[0], b[3] - b[1]
            msp.add_blockref(name, (x0 - b[0], y0 + b[3]))      # y flipped: top of piece at y0
            x0 += w + 60; rowh = max(rowh, h)
        msp.add_text(f"{STYLE} size {size}", dxfattribs={"layer": "15", "height": 25, "insert": (0, y0 + 60)})
        y0 -= rowh + 200
    doc.saveas(path)

# ---------------------------------------------------------------- 1:1 plot PDF: one page per piece (cut quantity on the page)
def plot_pdf(size, path):
    g, mt = PT.draft(size); em = emb_marks(size); w = PdfWriter()
    for code in PT.ORDER:
        pc = g[code]; b = PT.cut_poly(pc).bounds; m = 25.0
        W = (b[2] - b[0]) + 2*m; H = (b[3] - b[1]) + 2*m + 40
        X = lambda x: x - b[0] + m; Y = lambda y: y - b[1] + m + 40
        o = [f'<rect width="{W:.1f}" height="{H:.1f}" fill="#FFFFFF"/>']
        o += PD.piece_svg(pc, X, Y, 1.0, label=True, size=size, emb=em.get(code, ()), lw=1.0, text_mm=7)
        o.append(f'<rect x="{m}" y="8" width="100" height="25" fill="none" stroke="#000" stroke-width="0.4"/>')
        o.append(f'<text x="{m + 2}" y="18" font-size="5" font-family="Helvetica">TEST: 100 mm</text>')
        o.append(f'<text x="{m + 2}" y="28" font-size="4" font-family="Helvetica">print at 100 % — no scaling</text>')
        o.append(f'<text x="{m + 110}" y="18" font-size="6" font-weight="700" font-family="Helvetica">{STYLE} · {pc.code} {pc.name.replace("&", "+")} · size {size} · cut {pc.qty}</text>')
        o.append(f'<text x="{m + 110}" y="28" font-size="4.5" font-family="Helvetica">{pc.material} · seam allowance included (dashed = sew line) · notches = slits · ⊕ = drill holes</text>')
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}mm" height="{H:.1f}mm" viewBox="0 0 {W:.1f} {H:.1f}">' + "".join(o) + "</svg>"
        buf = io.BytesIO(); cairosvg.svg2pdf(bytestring=svg.encode(), write_to=buf); buf.seek(0); w.append(PdfReader(buf))
    w.write(path)

# ---------------------------------------------------------------- QA: pattern measured vs chart + seam walks
def measure(size):
    g, mt = PT.draft(size); b = mt["block"]
    S = g["S01"]; cap_e = S.edges[0]
    def sleeve_width(yy):
        u = LineString(S.sew()).intersection(LineString([(-1000, yy), (1000, yy)]))
        xs = [p.x for p in (u.geoms if hasattr(u, "geoms") else [u])]; return max(xs) - min(xs)
    R01, R02 = g["R01"], g["R02"]
    m = {"A": (mt["hem_b"] - (mt["hps_b"][1] + PT.FWD) + PT.HEM_RIB),
         "B": 2 * mt["ua_f"][0], "C": 2 * mt["sp_b"][0], "D": R01.edges[0].length / 2,
         "E": math.hypot(b.chest2 - b.sh2, mt["ua_b"][1] - b.b_sp[1]),
         "F": sleeve_width(25.0) / 2, "G": mt["cap_h"] + mt["Lu"] + PT.CUFF_RIB, "H": R02.edges[0].length / 2,
         "J": 2 * mt["hps_f"][0], "K": -(mt["hps_f"][1] - PT.FWD), "L": -(mt["hps_b"][1] + PT.FWD),
         "M": drum.m("M", size), "N": next(e.length for e in g["C02"].edges if e.name == "front R"), "P": PT.FWD}
    walks = [("Shoulder: back vs front", next(e.length for e in g["B01"].edges if e.name == "shoulder R"), next(e.length for e in g["F01"].edges if e.name == "shoulder"), 1.5),
             ("Side seam: back vs front", next(e.length for e in g["B01"].edges if e.name == "side R"), next(e.length for e in g["F01"].edges if e.name == "side"), 1.5),
             ("Sleeve cap vs armhole (ease)", cap_e.length, mt["AH"], None),
             ("Underarm: front vs back", S.edges[1].length, S.edges[3].length, 1.0),
             ("Collar neck vs body neckline", next(e.length for e in g["C02"].edges if e.name == "neck"), 2 * (mt["neck_b"] + mt["neck_f"]), 2.0),
             ("Top vs under collar outer", next(e.length for e in g["C01"].edges if e.name == "outer"), next(e.length for e in g["C02"].edges if e.name == "outer"), None),
             ("Facing CF vs front CF", g["K01"].edges[0].length, g["F01"].edges[0].length, 1.0),
             ("Lining side vs shell side (front)", next(e.length for e in g["L01"].edges if e.name == "side"), next(e.length for e in g["F01"].edges if e.name == "side"), 1.0),
             ("Hem rib vs body hem (ratio)", R01.edges[0].length, 2 * g["F01"].edges[-1].length + g["B01"].edges[4].length, None),
             ("Cuff rib vs shell sleeve opening (ratio)", R02.edges[0].length, S.edges[2].length, None)]
    return m, walks, mt

def qa_table():
    rows = {}
    for sz in PT.SIZES:
        m, walks, mt = measure(sz); rows[sz] = dict(meas=m, walks=walks, cap_h=mt["cap_h"], ease=mt["cap"] - mt["AH"])
    return rows

if __name__ == "__main__":
    import sys
    if "qa" in sys.argv or len(sys.argv) == 1:
        rows = qa_table()
        for sz, r in rows.items():
            dev = {k: round(r["meas"][k]/10 - drum.POM_CM[k][2][drum.SIZES.index(sz)], 2) for k in drum.POM_CM}
            print(sz, "dev cm", {k: v for k, v in dev.items() if abs(v) > 0.05}, "cap h", round(r["cap_h"]), "ease", round(r["ease"], 1))
            for nm, a, b, tol in r["walks"]:
                flag = "" if tol is None or abs(a - b) <= tol else "  <-- CHECK"
                print("   ", nm, round(a, 1), round(b, 1), flag)
    if "dxf" in sys.argv:
        for sz in PT.SIZES: write_dxf([sz], f"{OUTD}/{STYLE}_pattern_{sz}.dxf")
        write_dxf(PT.SIZES, f"{OUTD}/{STYLE}_pattern_ALL-SIZES.dxf"); print("dxf ok")
    if "pdf" in sys.argv:
        plot_pdf("M", f"{OUTD}/{STYLE}_pattern_M_1to1_PLOT.pdf"); print("pdf ok")
