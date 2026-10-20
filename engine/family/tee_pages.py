"""Tee family page set. Every number on every page is read from the Spec (family.yaml + variant yaml) or computed from
it (the tee block, the placement clearances) — nothing is typed here. Proposed values print amber with the tag.

pages(spec) -> [(code, title, [svg strings])]   (one A4 landscape page per svg)
"""
import base64, io, math
from PIL import Image
import sheet as SHT
from sheet import t, doc, SW, SH, INK, MUTED, RED, GREEN
from render import f
from .spec import V, TAG, val, is_prop, fmt_in, MM_PER
from .draw import PROP, ALT, GUIDE, vt, wrap, para, vpara, path_d, poly_d, dim, badge, ok_text
from . import factory_profile

COLOUR_HEX = {"white": "#FCFCFA", "black": "#1C1C1C", "charcoal": "#3A3A3C", "navy": "#1F2A44", "green": "#3B4A35",
              "maroon": "#5A1F28", "sand": "#CDBB9A", "grey": "#9A9A9A"}


# ----------------------------------------------------------------------------- helpers
def foot(spec):
    return (f"HAKI STUDIOS · {spec.name} · {val(spec.var.get('style'))} · tee family · "
            f"{val(spec.var.get('rev'), val(spec.tree.get('rev')))} · {val(spec.tree.get('date'))}")


def H(spec, title, sub, page):
    SHT.FOOT = foot(spec)
    return SHT.header(title, sub, page)


def body_hex(spec):
    b = spec.var["body"]
    return val(b.get("hex")) or COLOUR_HEX.get(str(val(b.get("colour"))).lower(), "#FFFFFF")


def dark(hexc):
    h = hexc.lstrip("#"); r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.299 * r + 0.587 * g + 0.114 * b < 110


def cm_in(mm):
    """'55.2 cm (21 3/4 in)' from mm — conversions only in code"""
    return f"{mm / 10:.1f} cm ({fmt_in(mm / 25.4)} in)"


def chart_banner(o, spec, x, y, width=SW - 24):
    st = spec.chart.status
    if is_prop(st):
        lines = wrap(f"MEASUREMENTS: {st.v}  {TAG}", width * 0.9, 1.75)   # bold runs wider
        o.append(f'<rect x="{f(x - 1)}" y="{f(y - 3)}" width="{f(width + 2)}" height="{f(1.4 + 2.8 * len(lines))}" fill="#FFF4DD" stroke="{PROP}" stroke-width="0.2"/>')
        for i, l in enumerate(lines): o.append(t(x, y + i * 2.8, l, 1.75, 700, PROP))
        return y + 2.2 + 2.8 * len(lines)
    return y


class Map:
    """flat mm -> page mm"""
    def __init__(self, ox, oy, s): self.ox, self.oy, self.s = ox, oy, s
    def P(self, p): return (self.ox + p[0] * self.s, self.oy + p[1] * self.s)
    def pts(self, pts): return [self.P(p) for p in pts]
    def d(self, g):
        from shapely import affinity
        return poly_d(affinity.affine_transform(g, [self.s, 0, 0, self.s, self.ox, self.oy]))


def img_data(path, max_px=1400):
    im = Image.open(path).convert("RGB"); im.thumbnail((max_px, max_px))
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=86)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(), im.size


def art_in_box(o, deco, X0, Y0, W, Hh, label=True):
    """the decoration's art inside its box (page mm). Missing art file -> a labelled placeholder (never invented art)."""
    p = deco.art_path()
    if p:
        href, _ = img_data(p)
        o.append(f'<image x="{f(X0)}" y="{f(Y0)}" width="{f(W)}" height="{f(Hh)}" preserveAspectRatio="xMidYMid meet" href="{href}"/>')
        o.append(f'<rect x="{f(X0)}" y="{f(Y0)}" width="{f(W)}" height="{f(Hh)}" fill="none" stroke="{GUIDE}" stroke-width="0.2" stroke-dasharray="1 0.6"/>')
    else:
        o.append(f'<rect x="{f(X0)}" y="{f(Y0)}" width="{f(W)}" height="{f(Hh)}" fill="#EAF3FB" fill-opacity="0.85" stroke="{GUIDE}" stroke-width="0.25" stroke-dasharray="1 0.6"/>')
        o.append(f'<line x1="{f(X0)}" y1="{f(Y0)}" x2="{f(X0 + W)}" y2="{f(Y0 + Hh)}" stroke="{GUIDE}" stroke-width="0.12"/>'
                 f'<line x1="{f(X0 + W)}" y1="{f(Y0)}" x2="{f(X0)}" y2="{f(Y0 + Hh)}" stroke="{GUIDE}" stroke-width="0.12"/>')
        if label:
            sz = max(1.2, min(2.2, W / 9))
            o.append(t(X0 + W / 2, Y0 + Hh / 2 + sz * 0.35, f"{deco.code} ART", sz, 700, GUIDE, "middle"))


def draw_flat(o, spec, size, back, M, decos=True, stroke=None, fill=None, seams=True, guides=False):
    fl = spec.flat(size); bh = fill or body_hex(spec); dk = dark(bh)
    st = stroke or ("#000000" if dk else INK); stitch = "#BBBBBB" if dk else "#555555"
    lw = 0.28
    for side in (1, -1):
        o.append(f'<path d="{M.d(fl.sleeve(side))}" fill="{bh}" stroke="{st}" stroke-width="{lw}" stroke-linejoin="round"/>')
    o.append(f'<path d="{M.d(fl.body(back))}" fill="{bh}" stroke="{st}" stroke-width="{lw}" stroke-linejoin="round"/>')
    band = fl.band_poly(back)
    o.append(f'<path d="{M.d(band)}" fill="{bh}" stroke="{st}" stroke-width="{lw * 0.8}"/>')
    if seams:
        from shapely.geometry import LineString
        # visible shoulder sewing line (family construction) + hem stitching
        for sgn in (1, -1):
            a = (sgn * fl.hps[0], fl.hps[1] + 2.5); b = (sgn * fl.sp[0], fl.sp[1] + 2.5)
            o.append(f'<path d="{path_d(M.pts([a, b]), False)}" stroke="{stitch}" stroke-width="0.14" stroke-dasharray="0.6 0.4" fill="none"/>')
            c0 = (sgn * fl.cuff_out[0], fl.cuff_out[1]); c1 = (sgn * fl.cuff_in[0], fl.cuff_in[1])
            u = (sgn * fl.u[0], fl.u[1])
            h = fl.sl_hem_h
            q0 = (c0[0] - u[0] * h, c0[1] - u[1] * h); q1 = (c1[0] - u[0] * h, c1[1] - u[1] * h)
            o.append(f'<path d="{path_d(M.pts([q0, q1]), False)}" stroke="{stitch}" stroke-width="0.14" stroke-dasharray="0.6 0.4" fill="none"/>')
        y = fl.L - fl.hem_h
        o.append(f'<path d="{path_d(M.pts([(-fl.bottom2, y), (fl.bottom2, y)]), False)}" stroke="{stitch}" stroke-width="0.14" stroke-dasharray="0.6 0.4" fill="none"/>')
        nk = fl.neck_curve(back); off = [(x, y_ + fl.band + 1.5) for x, y_ in nk]
        o.append(f'<path d="{path_d(M.pts(fl.mirror(off)[::-1] + off[1:]), False)}" stroke="{stitch}" stroke-width="0.14" stroke-dasharray="0.6 0.4" fill="none"/>')
    if guides:
        X, Y0 = M.P((0, -12)); _, Y1 = M.P((0, fl.L + 12))
        o.append(f'<line x1="{f(X)}" y1="{f(Y0)}" x2="{f(X)}" y2="{f(Y1)}" stroke="{GUIDE}" stroke-width="0.12" stroke-dasharray="1.2 0.6"/>')
        xa, ya = M.P((-fl.sp[0] - 40, 0)); xb, _ = M.P((fl.sp[0] + 40, 0))
        o.append(f'<line x1="{f(xa)}" y1="{f(ya)}" x2="{f(xb)}" y2="{f(ya)}" stroke="{GUIDE}" stroke-width="0.12" stroke-dasharray="1.2 0.6"/>')
        o.append(t(xb + 1, ya + 0.6, "HPS", 1.4, 700, GUIDE))
        o.append(t(X, Y1 + 2.5, "CB" if back else "CF", 1.4, 700, GUIDE, "middle"))
    if decos:
        for d in spec.decorations:
            if (d.view == "back") != back: continue
            x0, y0, x1, y1 = d.box_mm(size); (X0, Y0), (X1, Y1) = M.P((x0, y0)), M.P((x1, y1))
            art_in_box(o, d, X0, Y0, X1 - X0, Y1 - Y0, label=(X1 - X0) > 8)


def fit(spec, size, w_mm, h_mm, back=False):
    """scale so the flat (sleeves included) fits a w x h page box; returns (scale, bounds)"""
    b = spec.flat(size).bounds()
    s = min(w_mm / (b[2] - b[0]), h_mm / (b[3] - b[1] + 20))
    return s, b


def place_flat(o, spec, size, back, x, y, w, h, **kw):
    s, b = fit(spec, size, w, h)
    M = Map(x + (w - (b[2] - b[0]) * s) / 2 - b[0] * s, y - b[1] * s + 6, s)
    draw_flat(o, spec, size, back, M, **kw)
    return M


def table(o, x, y, cols, rows, size=1.6, lh=3.6, head=True, width=None):
    """cols: [(title, x_offset, width_mm)]; rows: [[cell...]] cells are str or V; wraps long cells; returns y"""
    width = width or (cols[-1][1] + cols[-1][2])
    if head:
        for ttl, dx, _ in cols: o.append(t(x + dx, y, ttl, size - 0.05, 700, MUTED))
        y += lh
    for i, r in enumerate(rows):
        lines = [wrap(c.text() if isinstance(c, V) else str(c), cols[j][2], size) for j, c in enumerate(r)]
        n = max(len(l) for l in lines)
        if i % 2 == 0: o.append(f'<rect x="{f(x - 1)}" y="{f(y - lh * 0.72)}" width="{f(width + 2)}" height="{f(lh * n * 0.86 + 0.6)}" fill="{ALT}"/>')
        for j, c in enumerate(r):
            pr = is_prop(c); bold = j == 0
            for k, l in enumerate(lines[j]):
                o.append(t(x + cols[j][1], y + k * lh * 0.86, l, size, 700 if (bold or pr) else 400, PROP if pr else INK))
        y += lh * n * 0.86 + 0.9
    return y


def label_place_text(pv):
    p = val(pv) or {}
    side = {"wearer_left": "wearer's left", "wearer_right": "wearer's right"}.get(p.get("side"), "")
    at = p.get("at")
    if at == "hem": s = f"{p.get('view', 'front')} hem, {side}, {p.get('from_side_cm', 0):g} cm from the side seam, sewn into the hem"
    elif at == "side_seam": s = f"{side} side seam, {p.get('above_hem_cm', 0):g} cm above the hem edge"
    elif at == "cb_neck": s = "centre back neck, under the rib seam"
    else: s = str(p)
    if p.get("inside"): s += " (inside)"
    return V(s, is_prop(pv), path=getattr(pv, "path", ""))


def label_rect(spec, size, lab):
    """(view, x0, y0, x1, y1) in flat mm for a label's placement"""
    fl = spec.flat(size); p = val(lab.get("placement")) or {}
    sz = val(lab.get("size_cm")) or [3, 3]
    w, h = (float(val(sz[0])) * 10, float(val(sz[1])) * 10)
    sgn = 1 if p.get("side", "wearer_left") == "wearer_left" else -1      # front view: wearer's left = +x
    view = p.get("view", "front")
    if view == "back": sgn = -sgn                                          # back view: wearer's left = -x
    at = p.get("at")
    if at == "hem":
        xc = sgn * (fl.bottom2 - float(p.get("from_side_cm", 0)) * 10 - w / 2)
        return view, xc - w / 2, fl.L - h, xc + w / 2, fl.L
    if at == "side_seam":
        y1 = fl.L - float(p.get("above_hem_cm", 0)) * 10
        x = sgn * fl.bottom2
        return view, x - w * 0.5, y1 - h, x + w * 0.5, y1
    nk = fl.neck_seam(True)
    return view, -w / 2, nk - fl.band + 1, w / 2, nk - fl.band + 1 + h


def labels(spec):
    out = []
    for k, lab in (spec.tree.get("labels") or {}).items():
        if not val(lab.get("enabled"), True): continue
        out.append((k, lab))
    return out


# ----------------------------------------------------------------------------- pages
def p_cover(spec, index):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>', t(14, 22, "HAKI STUDIOS", 3.0, 700, MUTED), t(14, 34, spec.name, 7.0, 700)]
    fam = spec.tree; ch = spec.chart
    o.append(t(14, 41.5, f"{val(spec.var.get('rev'))} · {val(fam.get('date'))} · sizes {ch.sizes[0]}–{ch.sizes[-1]} · base size {ch.base} · "
                         f"tee family block · {val(fam['factory']['name'])}", 2.2, 400, MUTED))
    o.append(vt(SW - 14, 41.5, V(f"Style {val(spec.var.get('style'))}", is_prop(spec.var.get("style"))), 2.0, 600, INK, "end"))
    o.append(f'<line x1="14" y1="45" x2="{SW - 14}" y2="45" stroke="{INK}" stroke-width="0.4"/>')
    chart_banner(o, spec, 14, 50, 180)
    M = place_flat(o, spec, ch.base, False, 14, 56, 92, 120)
    place_flat(o, spec, ch.base, True, 104, 56, 92, 120)
    fl = spec.flat(ch.base); yl = max(M.P((0, fl.L))[1], M.P(fl.cuff_in)[1]) + 8
    o.append(t(60, yl, f"FRONT · size {ch.base}", 2.0, 700, INK, "middle")); o.append(t(150, yl, f"BACK · size {ch.base}", 2.0, 700, INK, "middle"))
    ix = 206; o.append(t(ix, 52, "CONTENTS", 2.6, 700)); y = 57.5
    for code, title in index:
        o.append(t(ix, y, code, 1.75, 700)); o.append(t(ix + 9, y, title, 1.75)); y += 3.5
    y += 3; o.append(t(ix, y, "KEY SPECS", 2.4, 700)); y += 4.6
    b = fam["blank"]; body = spec.var["body"]
    rows = [("Factory", V(f"{val(fam['factory']['name'])} ({val(fam['factory']['contact'])})")),
            ("Fabric", V(f"{val(b['fabric'])}, {val(b['weight'])}")), ("Wash", b["wash"]),
            ("Fit", fam["block"]["fit"]), ("Body colour", V(f"{val(body['colour'])}")), ("Body Pantone", body.get("pantone", V("—")))]
    for d in spec.decorations:
        rows.append((d.code, V(f"{d.name} · {d.label} · {d.view}", is_prop(d.method_v))))
    for a, v in rows:
        o.append(t(ix, y, a, 1.7, 400, MUTED)); y = vpara(o, ix + 20, y, v, 60, 1.65, 2.9) + 0.8
    y += 2; o.append(t(ix, y, "Amber = proposed by Haki — please confirm (all listed on F1).", 1.6, 700, PROP))
    o.append(t(SW - 14, SH - 8, foot(spec), 1.8, 400, MUTED, "end"))
    return o


def p_flats(spec):
    ch = spec.chart; sz = ch.base; fl = spec.flat(sz)
    o = H(spec, "FLAT SKETCH — front + back, points of measure", f"Size {sz}, drawn from the POM chart (T3). Letters = POM codes. Dashed = visible stitching.", "T2")
    chart_banner(o, spec, 12, 31, 270)
    s, b = fit(spec, sz, 128, 112)
    w = (b[2] - b[0]) * s
    MF = Map(12 + (136 - w) / 2 - b[0] * s, 44 - b[1] * s, s)
    MB = Map(150 + (136 - w) / 2 - b[0] * s, 44 - b[1] * s, s)
    draw_flat(o, spec, sz, False, MF, decos=False, guides=True); draw_flat(o, spec, sz, True, MB, decos=False, guides=True)
    P, Q = MF.P, MB.P
    L_ = lambda p: (-p[0], p[1])                       # mirror to the left sleeve (viewer's left)
    o.append(dim(P((fl.bottom2 + 18, fl.L)), P((fl.bottom2 + 18, 0)), 0, "A"))
    yb = fl.ua[1] + 25.4
    o.append(dim(P((-fl.chest2, yb)), P((fl.chest2, yb)), 0, "B"))
    o.append(dim(Q((-fl.sp[0], fl.sp[1])), Q((fl.sp[0], fl.sp[1])), 5, "C"))
    o.append(dim(P((-fl.bottom2, fl.L)), P((fl.bottom2, fl.L)), 5, "D"))
    o.append(dim(P(fl.sp), P(fl.cuff_out), 4, "E"))
    o.append(dim(P(fl.ua), P(fl.sp), 4, "F"))
    o.append(dim(P(fl.cuff_out), P(fl.cuff_in), 4, "H"))
    foot_pt = (fl.ua[0] - fl.n[0] * fl.bicep_flat, fl.ua[1] - fl.n[1] * fl.bicep_flat)
    o.append(dim(P(L_(fl.ua)), P(L_(foot_pt)), 0, "G"))
    if "P" in ch.poms: o.append(dim(P(L_(fl.cuff_in)), P(L_(fl.ua)), 4, "P"))
    o.append(dim(P((-fl.neck2, 0)), P((fl.neck2, 0)), -6, "J"))
    o.append(dim(P((0, fl.fnd)), P((0, 0)), -4, "K"))
    o.append(dim(Q((0, fl.bnd)), Q((0, 0)), -4, "L"))
    o.append(dim(Q((fl.neck2 + 4, fl.bnd)), Q((fl.neck2 + 4, fl.bnd + fl.band)), -6, "N"))
    yl = max(P((0, fl.L))[1], P(fl.cuff_in)[1]) + 10
    o.append(t(80, yl, "FRONT", 2.0, 700, INK, "middle")); o.append(t(218, yl, "BACK", 2.0, 700, INK, "middle"))
    # legend: 3 columns under the flats
    y0 = yl + 6; o.append(t(12, y0, f"POM — size {sz}  (½ = half measure, measured flat, LESSONS C2: circumference = 2 x the value)", 1.9, 700))
    items = list(ch.poms.items()); per = math.ceil(len(items) / 3)
    for i, (k, p) in enumerate(items):
        cx = 12 + (i // per) * 92; y = y0 + 4.6 + (i % per) * 3.5
        pr = p.cells[sz].proposed; col = PROP if pr else INK
        o.append(t(cx, y, k, 1.7, 700, col)); o.append(t(cx + 5, y, p.name + (" ½" if val(p.half) else ""), 1.65, 400, col))
        o.append(t(cx + 86, y, f"{p.show(sz)} {p.unit}" + (f"  ({p.cm(sz):.1f} cm)" if p.unit != "cm" else ""), 1.65, 700, col, "end"))
    y = y0 + 4.6 + per * 3.5 + 1
    blk = spec.tree["block"]
    o.append(t(12, y, "Sleeve angle on the sketch is set so the drawn bicep (G) equals the chart; P = inner sleeve (underarm to hem).", 1.5, 400, MUTED))
    o.append(vt(150, y, V(f"Shoulder slope {val(blk['shoulder_slope_cm'])} cm, body / sleeve hem {val(blk['body_hem_cm'])} / {val(blk['sleeve_hem_cm'])} cm",
                          any(is_prop(blk[k]) for k in ("shoulder_slope_cm", "body_hem_cm", "sleeve_hem_cm"))), 1.5))
    return o


def p_pom(spec):
    ch = spec.chart; ss = ch.sizes
    o = H(spec, "POINTS OF MEASURE — graded chart + tolerances", f"Chart unit: {ch.unit}; cm under each value (converted in code). ½ = half, measured flat (LESSONS C2). Amber = proposed / derived.", "T3")
    y = chart_banner(o, spec, 12, 31, 273)
    o.append(t(12, y, f"Base chart: {ch.source}", 1.55, 400, MUTED)); y += 4.5
    cx = [12, 18, 52, 104] + [114 + 17 * i for i in range(len(ss))]
    gx = cx[-1] + 18; tx = gx + 16
    hd = ["", "Point of measure", "How measured", "½?"] + ss
    for x_, h_ in zip(cx, hd): o.append(t(x_, y, h_, 1.6, 700, MUTED))
    o.append(t(gx, y, "Grade", 1.6, 700, MUTED)); o.append(t(tx, y, "Tol ±", 1.6, 700, MUTED)); y += 3.8
    for i, (k, p) in enumerate(ch.poms.items()):
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y - 2.8)}" width="{SW - 22}" height="6.4" fill="{ALT}"/>')
        o.append(t(cx[0], y, k, 1.75, 700)); o.append(t(cx[1], y, p.name, 1.65, 600)); o.append(t(cx[2], y, p.how, 1.4, 400, MUTED))
        hv = p.half
        o.append(t(cx[3], y, "½" if val(hv) else "—", 1.7, 700, PROP if is_prop(hv) else INK))
        for j, sz in enumerate(ss):
            c = p.cells[sz]; col = PROP if c.proposed else INK
            o.append(t(cx[4 + j], y, p.show(sz), 1.7, 700 if sz == ch.base else 500, col))
            if p.unit != "cm": o.append(t(cx[4 + j], y + 2.5, f"{p.cm(sz):.1f}", 1.3, 400, col))
        gr = ch.grade(k)
        o.append(t(gx, y, ("0" if gr == 0 else (fmt_in(gr) if p.unit == "in" else f"{float(gr):g}")) if gr is not None else "varies", 1.5, 400, MUTED))
        if p.tol is not None:
            tm = p.tol_mm(); o.append(t(tx, y, f"{tm / 10:g} cm", 1.55, 700, PROP if is_prop(p.tol) else INK))
            o.append(t(tx, y + 2.5, f"{tm / 25.4:.2f} in", 1.3, 400, PROP if is_prop(p.tol) else MUTED))
        y += 6.4
    y += 2
    if ch.deltas:
        o.append(t(12, y, "NEW-SHAPE CHANGES applied on top of the base chart (recorded at one size; other sizes moved by the same amount = amber)", 1.8, 700)); y += 4
        if ch.delta_source: y = para(o, 12, y, ch.delta_source, 270, 1.45, 2.6, 400, MUTED) + 0.6
        for code, txt, src in ch.deltas:
            o.append(t(14, y, code, 1.6, 700)); o.append(t(20, y, txt, 1.6, 600, PROP)); o.append(t(150, y, src, 1.45, 400, MUTED)); y += 3.2
    y += 1.5
    para(o, 12, y, "Tolerances follow Mandy's own chart format (hoodie spec 57cf6d91: ½ chest ±1, bottom ±1, front neck drop ±0.5); "
                   "the tee tolerances were never recorded — confirm.", 270, 1.5, 2.6, 600, PROP)
    return o


AREA_POS = {   # construction area -> anchor on the front flat (function of the block)
    "neck": lambda fl: (0, fl.fnd + fl.band * 0.5), "neck seam": lambda fl: (fl.neck2 * 0.55, fl.fnd * 0.8 + fl.band),
    "shoulder": lambda fl: ((fl.hps[0] + fl.sp[0]) / 2, fl.sp[1] / 2 + 2), "shoulder tape": lambda fl: (-(fl.hps[0] + fl.sp[0]) / 2, fl.sp[1] / 2 + 2),
    "side seams": lambda fl: (fl.chest2 - 4, (fl.ua[1] + fl.L) / 2), "sleeve": lambda fl: tuple((fl.u * fl.slv * 0.55 + fl.n * fl.open_flat * 0.5) + fl.sp),
    "body hem": lambda fl: (-fl.bottom2 * 0.5, fl.L - fl.hem_h * 0.5),
}


def p_construction(spec):
    ch = spec.chart; fl = spec.flat(ch.base)
    o = H(spec, "CONSTRUCTION + STITCHING", "Seams, stitching and the blank. Numbers on the sketch = rows of the table.", "T4")
    M = place_flat(o, spec, ch.base, False, 12, 30, 100, 120, decos=False)
    rows = []
    for i, c in enumerate(spec.tree.get("construction") or [], 1):
        area = val(c["area"]); rows.append([str(i), area, c["spec"], val(c.get("source"), "")])
        pos = AREA_POS.get(area.lower())
        if pos:
            X, Y = M.P(pos(fl)); o.append(badge(X, Y, i, 2.0, 1.7))
    y = table(o, 118, 33, [("#", 0, 5), ("Area", 6, 22), ("Spec", 29, 90), ("Source", 121, 46)], rows, 1.6, 4.2)
    y += 4; o.append(t(118, y, "BLANK", 2.2, 700)); y += 4.4
    rows = [[k.replace("_", " ").capitalize(), v, val(getattr(v, "source", None), "") or ""] for k, v in spec.tree["blank"].items()]
    table(o, 118, y, [("Item", 0, 22), ("Spec", 24, 96), ("Source", 121, 46)], rows, 1.6, 4.2, head=False)
    return o


def p_bom(spec):
    o = H(spec, "BILL OF MATERIALS", "Per tee, every size. Consumption from the factory's marker (not estimated here).", "T5")
    fam = spec.tree; b = fam["blank"]; body = spec.var["body"]
    rows = [["Body fabric", V(f"{val(b['fabric'])} {val(b['weight'])}, {val(b['knit'])}", is_prop(b["knit"])), V(f"{val(body['colour'])}"), "factory marker"],
            ["Body colour", body.get("pantone", V("—")), body.get("wash", V("")), ""],
            ["Rib (neckband)", b["rib"], V(f"{spec.chart['N'].show(spec.chart.base)} cm finished (chart N)"), "1"]]
    th = next((c["spec"] for c in fam.get("construction", []) if val(c["area"]).lower() == "thread"), V("—"))
    rows.append(["Sewing thread", th, V(f"to match {val(body['colour'])}"), "as needed"])
    for k, lab in labels(spec):
        szc = val(lab.get("size_cm"))
        size_txt = f"{float(val(szc[0])):g} x {float(val(szc[1])):g} cm" if szc else ""
        rows.append([val(lab["item"]), V(f"{val(lab['text'])} · {val(lab.get('material'), '')}", is_prop(lab.get("material"))),
                     V(size_txt, is_prop(lab.get("size_cm"))), "1"])
    ht = fam.get("hang_tag") or {}
    if ht: rows.append([val(ht["item"]), V(val(ht["supplied_by"])), ht.get("attach", V("")), "1"])
    pk = fam.get("packing") or {}
    rows.append(["Poly bag", V(val(pk.get("bag"))), pk.get("bag_note", V("")), "1"])
    rows.append(["Carton", V(val(pk.get("carton"))), pk.get("pcs_per_carton", V("")), "per shipment"])
    for d in spec.decorations:
        rows.append([f"{d.code} decoration", V(f"{d.name} — {d.label}", is_prop(d.method_v)),
                     V(", ".join(val(c.get("name")) for c in d.colours) or "see " + d.code), "1"])
    table(o, 12, 34, [("Item", 0, 32), ("Description", 34, 120), ("Colour / size", 156, 88), ("Qty", 246, 26)], rows, 1.65, 4.6)
    return o


def p_labels(spec):
    ch = spec.chart; sz = ch.base
    o = H(spec, "LABELS + TRIMS — placement", f"Size {sz}. Labels drawn to size on the flat; dashed = inside the garment.", "T6")
    MF = place_flat(o, spec, sz, False, 12, 30, 95, 120, decos=False)
    MB = place_flat(o, spec, sz, True, 105, 30, 95, 120, decos=False)
    fl = spec.flat(sz); yl = max(MF.P((0, fl.L))[1], MF.P(fl.cuff_in)[1]) + 7
    o.append(t(59, yl, "FRONT", 2.0, 700, INK, "middle")); o.append(t(152, yl, "BACK", 2.0, 700, INK, "middle"))
    rows = []
    for i, (k, lab) in enumerate(labels(spec), 1):
        view, x0, y0, x1, y1 = label_rect(spec, sz, lab); M = MF if view == "front" else MB
        (X0, Y0), (X1, Y1) = M.P((x0, y0)), M.P((x1, y1))
        inside = (val(lab.get("placement")) or {}).get("inside")
        o.append(f'<rect x="{f(X0)}" y="{f(Y0)}" width="{f(X1 - X0)}" height="{f(Y1 - Y0)}" fill="#D9363E" fill-opacity="0.75" stroke="#7E1B25" stroke-width="0.2"'
                 + (' stroke-dasharray="0.6 0.4"' if inside else "") + "/>")
        o.append(badge(X1 + 3, Y0 - 2, i, 1.7, 1.5))
        szc = val(lab.get("size_cm"))
        rows.append([str(i), val(lab["item"]), V(val(lab["text"])), V(f"{float(val(szc[0])):g} x {float(val(szc[1])):g} cm" if szc else "—", is_prop(lab.get("size_cm"))),
                     lab.get("material", V("")), label_place_text(lab.get("placement")), V(val(lab.get("source"), ""))])
    ht = spec.tree.get("hang_tag") or {}
    if ht: rows.append([str(len(rows) + 1), val(ht["item"]), V(val(ht["supplied_by"])), "—", "", ht.get("attach", V("")), ""])
    table(o, 12, max(yl + 10, 150), [("#", 0, 4), ("Item", 5, 22), ("Text / content", 28, 56), ("Size", 86, 22), ("Material", 110, 34), ("Placement", 146, 82), ("Source", 230, 43)],
          rows, 1.45, 3.6)
    return o


def p_decoration(spec, d):
    ch = spec.chart; sz = ch.base; fl = spec.flat(sz); back = d.view == "back"
    o = H(spec, f"{d.code} · {d.name.upper()} — {d.label}", f"{d.view.capitalize()} · placement drawn at true proportion on the flat, every size outlined (thin) and the base size {sz} filled.", d.code)
    if d.stub:
        o.append(f'<rect x="118" y="29" width="167" height="9" fill="#FFF4DD" stroke="{PROP}" stroke-width="0.2"/>')
        o.append(t(120, 33, "EMBROIDERY: stitch files are made by the techpack-engine stitch path, not in this pack yet.", 1.65, 700, PROP))
        o.append(t(120, 36.3, "This page fixes placement + size only. DST / PES, thread list and the strike-off request come as G + F pages.", 1.5, 400, PROP))
    # flat: every size outline aligned at HPS / CF, base size filled
    s, b = fit(spec, ch.sizes[-1], 100, 128)
    M = Map(12 + (100 - (b[2] - b[0]) * s) / 2 - b[0] * s, 38, s)
    draw_flat(o, spec, sz, back, M, decos=False, guides=True)
    for z in ch.sizes:
        if z == sz: continue
        f2 = spec.flat(z)
        o.append(f'<path d="{M.d(f2.body(back).union(f2.sleeve(1)).union(f2.sleeve(-1)))}" fill="none" stroke="#9A9A9A" stroke-width="0.12"/>')
        x0, y0, x1, y1 = d.box_mm(z); (X0, Y0), (X1, Y1) = M.P((x0, y0)), M.P((x1, y1))
        o.append(f'<rect x="{f(X0)}" y="{f(Y0)}" width="{f(X1 - X0)}" height="{f(Y1 - Y0)}" fill="none" stroke="{GUIDE}" stroke-width="0.1"/>')
    x0, y0, x1, y1 = d.box_mm(sz); (X0, Y0), (X1, Y1) = M.P((x0, y0)), M.P((x1, y1))
    art_in_box(o, d, X0, Y0, X1 - X0, Y1 - Y0)
    o.append(dim(M.P((x1 + 12, 0)), M.P((x1 + 12, y0)), 0, f"{y0 / 10:.1f} from HPS", 1.4, GUIDE))
    o.append(dim(M.P((x0, y1)), M.P((x1, y1)), 4, f"{(x1 - x0) / 10:.1f}", 1.4, GUIDE))
    o.append(dim(M.P((x0 - 6, y1)), M.P((x0 - 6, y0)), 0, f"{(y1 - y0) / 10:.1f}", 1.4, GUIDE))
    cxm = (x0 + x1) / 2
    if abs(cxm) > 0.5: o.append(dim(M.P((0, y1 + 8)), M.P((cxm, y1 + 8)), 0, f"{cxm / 10:.1f} from {'CB' if back else 'CF'}", 1.4, GUIDE))
    fb = spec.flat(ch.sizes[-1]); yl = max(M.P((0, fb.L))[1], M.P(fb.cuff_in)[1]) + 6
    o.append(t(62, yl, f"cm · scale 1:{1 / s:.0f} · centre {'CB' if back else 'CF'}, top from the HPS line" + ("" if d.top_ref == "hps" else " (set from the neck seam)"), 1.45, 400, MUTED, "middle"))
    # per-size table + clearances
    rules = spec.tree.get("placement_rules") or {}
    keys = list(rules)
    y = 43 if d.stub else 33
    o.append(t(118, y, "PRINT SIZE + POSITION PER SIZE (cm) · CLEARANCE TO SEAMS (mm, min in brackets)", 1.75, 700)); y += 4
    cols = [118, 128, 140, 152, 166, 180] + [196 + 16 * i for i in range(len(keys))]
    hd = ["Size", "Width", "Height", "Top↓HPS", "Top↓neck", f"{'CB' if back else 'CF'}→ctr"] + [f"{k} ({val(rules[k]):g})" for k in keys]
    for x_, h_ in zip(cols, hd): o.append(t(x_, y, h_, 1.3, 700, MUTED))
    y += 3.3; allok = True
    prop_place = d.placement_proposed()
    for j, z in enumerate(ch.sizes):
        x0, y0, x1, y1 = d.box_mm(z); cl = spec.flat(z).clearances((x0, y0, x1, y1), back)
        if j % 2 == 0: o.append(f'<rect x="117" y="{f(y - 2.3)}" width="{SW - 129}" height="3.2" fill="{ALT}"/>')
        col = PROP if prop_place else INK
        vals = [z, f"{(x1 - x0) / 10:.1f}", f"{(y1 - y0) / 10:.1f}", f"{y0 / 10:.1f}", f"{(y0 - d.neck_seam_mm(z)) / 10:.1f}", f"{(x0 + x1) / 20:.1f}"]
        for i, v in enumerate(vals): o.append(t(cols[i], y, v, 1.45, 700 if (i == 0 or z == sz) else 400, INK if i == 0 else col))
        for i, k in enumerate(keys):
            c = cl.get(k); mn = float(val(rules[k]))
            ok = c is not None and c >= mn; allok &= ok
            o.append(t(cols[6 + i], y, "overlap" if c is not None and c < 0 else f"{c:.0f}", 1.45, 700 if not ok else 400, GREEN if ok else RED))
        if "inside body" in cl: allok = False; o.append(t(SW - 12, y, "OFF BODY", 1.4, 700, RED, "end"))
        y += 3.2
    o.append(t(118, y + 1, "ALL SIZES CLEAR OF EVERY SEAM" if allok else "PLACEMENT FAILS A KEEP-OUT ON A SIZE — see red (move or resize the art)", 1.7, 700, GREEN if allok else RED))
    if prop_place: o.append(t(SW - 12, y + 1, f"placement + size {TAG}", 1.5, 700, PROP, "end"))
    y += 6
    # method spec block
    o.append(t(118, y, f"{d.label.upper()} — METHOD SPEC", 1.9, 700)); o.append(vt(SW - 12, y, V(f"method: {d.method}", is_prop(d.method_v)), 1.5, 600, INK, "end")); y += 3.8
    rows = [[lab, v] for lab, v in d.fields()]
    y = table(o, 118, y, [("Item", 0, 32), ("Spec", 34, 133)], rows, 1.45, 3.4, head=False)
    y += 2
    # artwork + colours + notes
    o.append(t(118, y, "ARTWORK + COLOURS", 1.9, 700)); y += 3.5
    ay = y
    p = d.art_path()
    if p:
        href, (iw, ih) = img_data(p, 900); w = 30; h = w * ih / iw
        o.append(f'<image x="118" y="{f(y)}" width="{w}" height="{f(h)}" href="{href}"/>')
    else:
        w = 30; h = 22; art_in_box(o, d, 118, y, w, h)
    lab = d.art.get("label") if d.art else None
    tx = 151
    if lab: ay = para(o, tx, ay + 1.5, val(lab), 132, 1.45, 2.5, 700, INK) + 0.6
    if not p:
        msg = (f"Image not attached to this pack (file '{val(d.art.get('file'))}' missing)" if d.art and d.art.get("file")
               else "No artwork file given in the variant") + " — placeholder box drawn; send the art file with this pack."
        ay = para(o, tx, ay, msg, 132, 1.4, 2.4, 600, RED) + 0.6
    for c in d.colours:
        o.append(t(tx, ay + 0.6, "•", 1.5, 700)); ay = vpara(o, tx + 2.5, ay + 0.6, V(f"{val(c.get('name'))} — {val(c.get('pantone'))}", is_prop(c.get("pantone"))), 130, 1.45, 2.5) + 0.3
    for n in d.notes:
        ay = para(o, tx, ay + 0.6, val(n), 132, 1.45, 2.5, 400, INK) + 0.3
    return o


def p_colourway(spec):
    ch = spec.chart; body = spec.var["body"]; hx = body_hex(spec)
    o = H(spec, "COLOURWAY", "Body colour + every decoration colour. Swatches on screen are a guide only — match to the Pantone / physical standard.", "T7")
    o.append(f'<rect x="14" y="34" width="34" height="22" rx="1" fill="{hx}" stroke="#999" stroke-width="0.25"/>')
    y = 37; tx = 54
    o.append(t(tx, y, f"BODY · {val(body['colour'])}", 2.3, 700)); y += 4.2
    y = vpara(o, tx, y, body.get("pantone", V("—")), 120, 1.7, 2.8, prefix="Pantone: ") + 0.6
    y = vpara(o, tx, y, body.get("wash", V("")), 120, 1.7, 2.8, prefix="Wash: ") + 0.6
    y = vpara(o, tx, y, spec.tree["blank"]["rib"], 120, 1.7, 2.8, prefix="Rib: ") + 0.6
    place_flat(o, spec, ch.base, False, 12, 64, 85, 110); place_flat(o, spec, ch.base, True, 100, 64, 85, 110)
    y = 37; tx = 192
    for d in spec.decorations:
        o.append(t(tx, y, f"{d.code} · {d.name}", 2.0, 700)); y += 3.6
        y = vpara(o, tx, y, V(f"{d.label}, {d.view}", is_prop(d.method_v)), 92, 1.6, 2.7) + 0.4
        for c in d.colours:
            y = vpara(o, tx + 2, y, V(f"• {val(c.get('name'))} — {val(c.get('pantone'))}", is_prop(c.get("pantone"))), 90, 1.55, 2.6) + 0.3
        y += 3
    return o


def p_packing(spec):
    pk = spec.tree.get("packing") or {}
    o = H(spec, "PACKING", "Folding, bagging, cartons.", "T8")
    # simple fold diagram
    o.append(f'<rect x="20" y="40" width="50" height="60" fill="#FFFFFF" stroke="{INK}" stroke-width="0.3"/>')
    o.append(f'<path d="M32,40 L32,100 M58,40 L58,100 M20,72 L70,72" stroke="{GUIDE}" stroke-width="0.25" stroke-dasharray="1 0.6"/>')
    o.append(t(45, 106, "1 · sleeves + sides folded back along the blue lines,", 1.5, 400, MUTED, "middle"))
    o.append(t(45, 109, "2 · folded in half, print side out", 1.5, 400, MUTED, "middle"))
    o.append(f'<rect x="85" y="44" width="40" height="50" fill="#EAF3FB" fill-opacity="0.6" stroke="{INK}" stroke-width="0.3"/>')
    o.append(f'<rect x="88" y="54" width="34" height="38" fill="#FFFFFF" stroke="{MUTED}" stroke-width="0.2"/>')
    o.append(f'<rect x="113" y="47" width="9" height="4" fill="#FFFFFF" stroke="{INK}" stroke-width="0.2"/>'); o.append(t(117.5, 49.8, "SIZE", 1.2, 700, INK, "middle"))
    o.append(t(105, 100, "poly bag + size sticker", 1.5, 400, MUTED, "middle"))
    rows = [[k.replace("_", " ").capitalize(), v] for k, v in pk.items()]
    table(o, 140, 40, [("Item", 0, 30), ("Spec", 32, 112)], rows, 1.7, 4.6)
    return o


GROUPS = [("pom_chart", "Measurements"), ("block", "Block (flat drawing)"), ("blank", "Blank fabric"), ("construction", "Construction"),
          ("labels", "Labels"), ("hang_tag", "Hang tag"), ("packing", "Packing"), ("placement_rules", "Placement keep-outs"),
          ("style", "Style"), ("body", "Body colour"), ("decorations", "Decorations")]


def open_items(spec):
    """[(group, label, V)] — every proposed value, labelled for a person (tolerances + method defaults grouped)"""
    items = []; tol = []; mdef = {}
    for v in spec.proposed():
        p = v.path; top = p.split(".")[0].split("[")[0]
        grp = dict(GROUPS).get(top, top)
        if p.startswith("labels.") and not val(spec.tree["labels"][p.split(".")[1]].get("enabled"), True): continue
        if isinstance(v.v, list): v = V(" x ".join(f"{float(val(x)):g}" for x in v.v) + (" cm" if p.endswith("_cm") else ""), True, note=v.note, path=p)
        if p.endswith(".tol") and (".poms." in p or ".changes." in p):
            code = p.split(".poms." if ".poms." in p else ".changes.")[1].split(".")[0]; tol.append(f"{code} ±{val(v)}"); continue
        if p.startswith("decorations[") and ".spec." in p:
            i = int(p.split("[")[1].split("]")[0]); mdef.setdefault(i, []).append(p.rsplit(".", 1)[1]); continue
        if p.startswith("construction["):
            i = int(p.split("[")[1].split("]")[0]); label = f"{val(spec.tree['construction'][i]['area'])}"
        elif p.startswith("decorations["):
            i = int(p.split("[")[1].split("]")[0]); d = spec.decorations[i]
            rest = p.split("]", 1)[1].strip(".")
            if rest.startswith("colours["):
                j = int(rest.split("[")[1].split("]")[0]); rest = f"ink colour: {val(d.colours[j].get('name'))}"
            rest = rest.replace("_cm", " (cm)").replace("_", " ")
            label = f"{d.code} {d.name} — {rest}"
        elif p.startswith("pom_chart.cells."):
            code = p.rsplit(".", 1)[1]; label = f"POM {code} {spec.chart[code].name} — sizes derived from the recorded change"
        elif ".poms." in p and p.endswith(".half"):
            code = p.split(".poms.")[1].split(".")[0]; label = f"POM {code} {spec.chart[code].name} — half (flat) measure?"
            v = V("yes, half measure, measured flat" if val(v) else "no, full measure", True, note=v.note, path=p)
        elif p.startswith("pom_chart.deltas.changes."):
            code = p.split(".changes.")[1].split(".")[0]; ch_ = spec.tree["pom_chart"]["deltas"]["changes"][code]
            label = f"POM {code} {spec.chart[code].name} — change on every size"
            v = V(f"{float(val(v)):+g} {val(ch_.get('unit'), spec.chart.unit)}", True, note=v.note or val(ch_.get("note")), path=p)
        elif p == "pom_chart.status":
            label = "Measurement chart"
        elif p.startswith("placement_rules."):
            label = f"minimum distance from art to {p.split('.', 1)[1]} (mm)"
        elif p.startswith("labels."):
            parts = p.split("."); label = f"{val(spec.tree['labels'][parts[1]]['item'])} — {parts[2].replace('_cm', ' (cm)')}"
            if parts[2] == "placement": v = label_place_text(v)
        else:
            label = " · ".join(x.replace("_cm", " (cm)").replace("_", " ") for x in p.split(".")[1:]) or top
        items.append((grp, label, v))
    if tol:
        items.insert(0, ("Measurements", "Tolerances (cm)", V(", ".join(tol), True, note="Mandy's format (hoodie spec 57cf6d91); tee tolerances never recorded")))
    for i, ks in mdef.items():
        d = spec.decorations[i]
        items.append(("Decorations", f"{d.code} {d.label} — method spec (page {d.code})",
                      V(f"{len(ks)} of {len(d.fields())} lines are Haki defaults: " + ", ".join(lab for lab, v in d.fields() if v.proposed), True)))
    order = [g for _, g in GROUPS]
    items.sort(key=lambda it: order.index(it[0]) if it[0] in order else 99)
    return items


def p_factory(spec):
    """F1 — open questions for the factory: the top questions + every [proposed — confirm] value. May run to several pages."""
    pages, o, y = [], None, 0
    n = [0]
    def new():
        nonlocal o, y
        n[0] += 1; code = "F1" if n[0] == 1 else f"F1.{n[0]}"
        o = H(spec, "F1 · FACTORY REQUESTS — please answer before the sample", f"{spec.name} · for {val(spec.tree['factory']['name'])} ({val(spec.tree['factory']['contact'])}) · every amber value in this pack, in one list", code)
        pages.append(o); y = 33
    new()
    qs = spec.tree.get("factory_questions") or []
    if qs:
        o.append(t(12, y, "FIRST, PLEASE", 2.4, 700)); y += 4.6
        for i, q in enumerate(qs, 1):
            y = para(o, 16, y, f"{i}. {val(q)}", 268, 1.85, 3.0, 700, PROP) + 0.8
        y += 2
    o.append(t(12, y, "PLEASE CONFIRM OR CORRECT EACH VALUE (we proposed it; it is not recorded)", 2.2, 700)); y += 4.6
    cur = None; k = 0
    for grp, label, v in open_items(spec):
        txt = v.text(tag=False); nt = v.note
        lines = len(wrap(txt, 150, 1.55)) + (len(wrap(nt, 150, 1.35)) if nt else 0)
        if y + lines * 2.7 + (5 if grp != cur else 0) > SH - 12: new()
        if grp != cur:
            o.append(t(12, y + 1, grp.upper(), 1.8, 700, MUTED)); y += 4.2; cur = grp
        k += 1
        o.append(f'<rect x="12" y="{f(y - 2.0)}" width="2.4" height="2.4" fill="none" stroke="{INK}" stroke-width="0.22"/>')
        o.append(t(16, y, f"{k}.", 1.55, 700)); para(o, 21, y, label, 92, 1.55, 2.7, 700, INK)
        yy = para(o, 116, y, txt, 150, 1.55, 2.7, 600, PROP)
        if nt: yy = para(o, 116, yy, nt, 160, 1.35, 2.35, 400, MUTED)
        y = max(yy, y + len(wrap(label, 92, 1.55)) * 2.7) + 0.9
    return pages


def p_revisions(spec):
    o = H(spec, "REVISIONS + APPROVALS", "Every change, newest last. Sample tracker + sign-off.", "R1")
    y = 36
    revs = [V(f"Family block {val(spec.tree.get('rev'))} · {val(spec.tree.get('date'))} · tee family (families/tee/family.yaml)")]
    for r in spec.var.get("revisions") or []:
        revs.append(V(f"{val(r['rev'])} · {val(r['date'])} · {val(r['change'])}"))
    o.append(t(12, y, "REVISIONS", 2.3, 700)); y += 4.6
    for r in revs: y = para(o, 14, y, r.v, 270, 1.75, 3.0) + 1.2
    y += 5; o.append(t(12, y, "SAMPLE TRACKER", 2.3, 700)); y += 5
    for i, sname in enumerate([f"Fit + print sample, size {spec.chart.base}", "Size set (every size, measured vs T3)", "Pre-production sample (bulk fabric, wash, labels)", "Approved for bulk"]):
        yy = y + i * 9
        o.append(f'<rect x="11" y="{f(yy - 4)}" width="{SW - 22}" height="9" fill="{ALT if i % 2 == 0 else "#FFFFFF"}" stroke="#DDD" stroke-width="0.2"/>')
        o.append(t(13, yy + 1, sname, 1.8, 600)); o.append(t(150, yy + 1, "date sent:", 1.5, 400, MUTED)); o.append(t(195, yy + 1, "comments:", 1.5, 400, MUTED))
    y += 4 * 9 + 6
    o.append(t(12, y, "APPROVED BY", 2.0, 700))
    for i, who in enumerate(["Haki Studios", val(spec.tree["factory"]["name"])]):
        o.append(f'<line x1="{12 + i * 140}" y1="{f(y + 12)}" x2="{100 + i * 140}" y2="{f(y + 12)}" stroke="{INK}" stroke-width="0.2"/>')
        o.append(t(12 + i * 140, y + 15, f"{who} — name, signature, date", 1.5, 400, MUTED))
    return o


def pages(spec):
    """[(code, title, [svg_body_lists])] in pack order"""
    deco = [(d.code, f"{d.name} — {d.label}", lambda d=d: [p_decoration(spec, d)]) for d in spec.decorations]
    plan = [("T1", "Cover + summary", None), ("T2", "Flat sketch + POMs", lambda: [p_flats(spec)]),
            ("T3", "Points of measure + grading", lambda: [p_pom(spec)]), ("T4", "Construction + stitching", lambda: [p_construction(spec)]),
            ("T5", "Bill of materials", lambda: [p_bom(spec)]), ("T6", "Labels + trims placement", lambda: [p_labels(spec)])] + deco + \
           [("T7", "Colourway", lambda: [p_colourway(spec)]), ("T8", "Packing", lambda: [p_packing(spec)]),
            ("F1", "Factory requests + open questions", lambda: p_factory(spec)), ("R1", "Revisions + approvals", lambda: [p_revisions(spec)])]
    index = [(c, ttl) for c, ttl, _ in plan]
    out = []
    for code, ttl, fn in plan:
        bodies = [p_cover(spec, index)] if fn is None else fn()
        out.append((code, ttl, [doc(b) for b in bodies]))
    return out
