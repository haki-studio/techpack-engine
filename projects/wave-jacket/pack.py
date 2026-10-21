"""Embroidery pack G1-G9 + F1 for the wave jacket (01 wave on BK, FR, FL, SR, SL). Every number comes from the stitch files
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
def mh(r):                       # one lockstitch file per hooping (chenille = plan only until the factory names its format, B33)
    return FA.machine_hours(r.get("total_stitches", r["stitches"]), PROF, trims=r.get("total_trims", r["trims"]), colour_changes=r.get("total_stops", r["stops"]) - 1)
def TS(r): return r.get("total_stitches", r["stitches"])
def one_hoop_ok(P, size_mm):
    """a full file sewn in one hooping: fronts on the factory's confirmed single hooping (factory.json), else the frame"""
    one = PROF.get("single_hooping_confirmed_mm", {}).get("front") if P in ("FR", "FL") else None
    w, h = size_mm
    if one: return (w <= one[0] and h <= one[1]) or (h <= one[0] and w <= one[1])
    return w <= FRAME[0] - 16 and h <= FRAME[1] - 16
def TT(r): return r.get("total_trims", r["trims"])
dst2 = WC.patch_dst2()

REV, DATE = WC.REV_EMB, WC.DATE
SB.FOOT = f"HAKI STUDIOS · {WC.NAME} · EMBROIDERY · {REV} · {DATE}"
D = pickle.load(open("art_M.pkl", "rb")); VF = {P: D[P] for P in WC.PIECES}
CUR = json.load(open("dst_current.json")); ALL = json.load(open("dst_all.json"))
SUM = json.load(open("out/01_wave/summary.json")) if os.path.exists("out/01_wave/summary.json") else {}
PS = WC.PIECES
BB = {p: unary_union([r["geom"] for r in VF[p]]).bounds for p in PS}
OUT_PDF = f"out/HAKI_WAVE_EMBROIDERY-PACK_{REV.replace(' ', '')}.pdf"
SPEC = [f"out/01_wave/HAKI_WAVE_01_wave_SPEC_{REV.replace(' ', '')}.pdf"]       # the current Rev only (a stale Rev A spec was merged before)
def secs(r): return (r.get("splits") or {}).get("sections", {}) or {}
def hoop_files(r):
    """the files a piece is actually sewn from: its split sections, or the full file when it fits one hooping"""
    s = secs(r); return list(s.values()) if s else [r.get("full", r)]
SWT = json.load(open("out/01_wave/M/swatch/result_swatch.json"))
CONT = json.load(open("continuity_M.json")); CONT_OK = {k: v for k, v in CONT.items() if v.get("meet") is not None and v["art_mm"] >= 10}
MMK = json.load(open("out/placement/match_marks_M.json"))
GATES = json.load(open("gates_M.json"))
TM = json.load(open("tonematch_M.json")) if os.path.exists("tonematch_M.json") else []
TMB = [r for r in TM if "band_clean_merged" in r]; TM = [r for r in TM if "seam" in r]
TM_TXT = (f"{sum(r['recoloured'] for r in TM)} stripe regions re-threaded; same thread on both sides (art, 1-4 mm in; after the band merge -> after the handover) " +
          ", ".join(f"{r['seam']} {r['tone_agree_before']}→{r['tone_agree_after']} %" for r in TM if r["tone_agree_before"] is not None and r["tone_agree_before"] != r["tone_agree_after"])) if TM else "not run"
TOT = sum(TS(CUR[p]) for p in PS); TRIMS = sum(TT(CUR[p]) for p in PS)
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

# ---------------------------------------------------------------- layout helpers (PR #27 review: legibility)
# Text sizes: table cells + notes >= 2.2 mm, body notes 2.5 mm, section heads 3.0 mm; row pitch ~1.6 x the font size.
# Long lines are WRAPPED to the right margin (never run off the page); content stops at BOT, a page that no longer
# fits continues on "Gx (2/2)" instead of shrinking the text.
RM, BOT = SW - 12, SH - 14
CWF = 0.47                                  # approx. character width / font size (Noto Sans)
TXT, NOTE, SEC = 2.2, 2.5, 3.0

def _chunks(s, n=150):
    out, cur = [], ""
    for w_ in str(s).split(" "):
        if cur and len(cur) + len(w_) + 1 > n: out.append(cur); cur = w_
        else: cur = (cur + " " + w_) if cur else w_
    return out + ([cur] if cur else [])

def wrap(s, width_mm, size, w=400):
    """split s into lines that fit width_mm at font size `size` (mm); bold runs ~10 % wider"""
    return _chunks(s, max(8, int(width_mm / (CWF * size * (1.1 if w >= 600 else 1.0)))))

def para(o, x, y, s, size=NOTE, w=400, fill=INK, width=None, pitch=1.6):
    """wrapped paragraph from (x, y) to the right margin (or width); returns the y of the next line"""
    for l_ in wrap(s, width or (RM - x), size, w):
        o.append(t(x, y, l_, size, w, fill)); y += size * pitch
    return y

def head(title, sub):
    o = [f'<rect width="{SW}" height="{SH}" fill="#FFFFFF"/>', t(12, 16, title, 4.6, 700)]
    y = 21.8
    for l_ in wrap(sub, RM - 12, 2.3): o.append(t(12, y, l_, 2.3, 400, MUTED)); y += 3.2
    yl = y - 3.2 + 3.3
    o.append(f'<line x1="12" y1="{f(yl)}" x2="{f(RM)}" y2="{f(yl)}" stroke="{INK}" stroke-width="0.3"/>')
    o.append(t(RM, SH - 6, SB.FOOT, 1.9, 400, MUTED, "end"))
    return o, yl + 6.0

class Pager:
    """one G page that continues on (2/N), (3/N) ... when its content does not fit"""
    def __init__(self, key, title, sub):
        self.key, self.title, self.sub, self.pages = key, title, sub, []; self.new()
    def new(self):
        o, y = head(self.title, self.sub)                  # the page label says (2/N)
        self.pages.append(o); self.o, self.y = o, y
    def need(self, h):
        if self.y + h > BOT: self.new(); return True
        return False
    def para(self, x, s, size=NOTE, w=400, fill=INK, width=None, gap=0.0):
        ls = wrap(s, width or (RM - x), size, w); self.need(len(ls) * size * 1.6)
        self.y = para(self.o, x, self.y, s, size, w, fill, width) + gap
    def sec(self, s, fill=INK, size=SEC):
        self.need(size * 1.6 + 6); self.y += 1.0
        for l_ in wrap(s, RM - 12, size, 700): self.o.append(t(12, self.y, l_, size, 700, fill)); self.y += size * 1.6
        self.y += 0.6
    def done(self):
        N = len(self.pages); out = []
        for i, o in enumerate(self.pages):
            lab = self.key if N == 1 else f"{self.key} ({i+1}/{N})"
            o.append(t(RM, 16, lab, 2.4, 600, MUTED, "end")); out.append((lab, o))
        return out

def _cell(c):
    """cell = str | (str, weight, fill) | (str, weight, fill, wrap_width_mm)"""
    if c is None: return None
    if not isinstance(c, tuple): return (str(c), 400, INK, None)
    c = tuple(c) + (400, INK, None)[len(c) - 1:]
    return (str(c[0]), c[1], c[2], c[3] if len(c) > 3 else None)

def table(pg, cols, hd, rows, size=TXT, pitch=None, x1=RM):
    """table on a Pager: header repeated on a continuation page; zebra rows; cells may wrap (4th tuple item)"""
    p = pitch or size * 1.7
    def hdr_():
        for x_, h in zip(cols, hd):
            for k, l_ in enumerate(str(h).split("\n")): pg.o.append(t(x_, pg.y + k * size * 1.3, l_, size, 700, MUTED))
        pg.y += p + (max(str(h).count("\n") for h in hd)) * size * 1.3
    pg.need(p * 3); hdr_()
    for i, r in enumerate(rows):
        cs = [_cell(c) for c in r]
        lines = [wrap(c[0], c[3], size, c[1]) if (c and c[3]) else ([c[0]] if c else []) for c in cs]
        n = max([len(l_) for l_ in lines] + [1])
        if pg.need(n * p): hdr_()
        if i % 2 == 0: pg.o.append(f'<rect x="{f(cols[0]-1)}" y="{f(pg.y - size*1.15)}" width="{f(x1 - cols[0] + 1)}" height="{f(n*p)}" fill="#F5F2EC"/>')
        for x_, c, ls in zip(cols, cs, lines):
            if not c: continue
            for k, l_ in enumerate(ls): pg.o.append(t(x_, pg.y + k * p, l_, size, c[1], c[2]))
        pg.y += n * p
    pg.y += 1.5

def hdr(title, sub, page):                  # single-page variant (G2)
    o, y = head(title, sub); o.append(t(RM, 16, page, 2.4, 600, MUTED, "end")); return o, y

def _bands(im, gap=14, thr=245):
    """row bands of a stacked sheet image separated by white gaps > gap px"""
    import numpy as np
    a = np.asarray(im.convert("L")); wr = (a > thr).mean(1) > 0.995
    segs, s = [], None
    for i, v in enumerate(wr):
        if not v and s is None: s = i
        if v and s is not None: segs.append([s, i]); s = None
    if s is not None: segs.append([s, len(wr)])
    out = []
    for sg in segs:
        if out and sg[0] - out[-1][1] < gap: out[-1][1] = sg[1]
        else: out.append(sg)
    return [im.crop((0, a_, im.width, b_)) for a_, b_ in out]

def _trim_w(im, thr=245):
    import numpy as np
    a = np.asarray(im.convert("L")); cols = np.where((a < thr).any(0))[0]
    return im.crop((0, 0, int(cols.max()) + 2, im.height)) if len(cols) else im

TM_CH = _chunks(TM_TXT)

# ---------------------------------------------------------------- G2
def overview():
    o, _ = hdr("PLACEMENT OVERVIEW — the wave on the five pieces", "Each piece in its own pattern coords (back: x from CB, + = wearer's right, y from CB neck seam; fronts: x from CF, + = wearer's left, y from CF neck; sleeves: x from the sleeve centre line, y from the underarm line).", "G2")
    from PIL import Image, ImageDraw
    SC = 0.118                                                         # one scale for every piece (mm on page per mm)
    lay = {"SL": (12, 30), "BK": (82, 30), "SR": (157, 30), "FR": (82, 114), "FL": (125, 114)}
    right = 0
    for P, (x, y) in lay.items():
        pan = PC.panel("M", P); b = pan.bounds; bb = (b[0] - 4, b[1] - 4, b[2] + 4, b[3] + 4); ppm = 1.4; w = (bb[2] - bb[0]) * SC
        im = SR.render(VF[P], bb, ppm, base=WC.FABRIC)
        msk = Image.new("L", im.size, 0); ImageDraw.Draw(msk).polygon([((xx - bb[0]) * ppm, (yy - bb[1]) * ppm) for xx, yy in pan.exterior.coords], fill=255)
        wh = Image.new("RGB", im.size, (255, 255, 255)); wh.paste(im, (0, 0), msk)
        dd = ImageDraw.Draw(wh); dd.line([((xx - bb[0]) * ppm, (yy - bb[1]) * ppm) for xx, yy in PC.clip_for("M", P).exterior.coords], fill=(255, 90, 90), width=1)
        tag, hh = img_tag(wh, x, y, w); o.append(tag); right = max(right, x + w)
        s = w / (bb[2] - bb[0]); X = lambda xx: x + (xx - bb[0]) * s; Y = lambda yy: y + (yy - bb[1]) * s
        ab = BB[P]
        o.append(f'<rect x="{f(X(ab[0]))}" y="{f(Y(ab[1]))}" width="{f((ab[2]-ab[0])*s)}" height="{f((ab[3]-ab[1])*s)}" fill="none" stroke="{GUIDE}" stroke-width="0.3" stroke-dasharray="1.2 0.8"/>')
        sp = CUR[P].get("splits") or {}
        for yv in sp.get("ys") or ([sp["sy"]] if sp.get("sy") is not None else []):
            o.append(f'<line x1="{f(X(ab[0]-6))}" y1="{f(Y(yv))}" x2="{f(X(ab[2]+6))}" y2="{f(Y(yv))}" stroke="#0A84FF" stroke-width="0.4" stroke-dasharray="2 1"/>')
        for xv in sp.get("xs") or ([sp["sx"]] if sp.get("sx") is not None else []):
            o.append(f'<line x1="{f(X(xv))}" y1="{f(Y(ab[1]-6))}" x2="{f(X(xv))}" y2="{f(Y(ab[3]+6))}" stroke="#0A84FF" stroke-width="0.4" stroke-dasharray="2 1"/>')
        para(o, x, y + hh + 3.2, f"{P} {PC.NAME[P]} ({PC.CODE[P]}) · art {ab[2]-ab[0]:.0f} × {ab[3]-ab[1]:.0f}", TXT, 700, INK, width=max(w, 38))
    # right column: art box table (pieces down, sizes across, so every column fits inside the margin) + keep-outs
    tx = max(right + 4, 222); cw = RM - tx; ty = 32
    ty = para(o, tx, ty, "ART BOX (w × h mm, DST read-back)", 2.6, 700, INK, width=cw) + 1
    colw = 13.0; per = max(1, int((cw - 9) // colw))
    for b0 in range(0, len(WC.DOC_SIZES), per):
        szs = WC.DOC_SIZES[b0:b0 + per]
        o.append(t(tx, ty, "Piece", TXT, 700, MUTED))
        for j, sz in enumerate(szs): o.append(t(tx + 9 + j * colw, ty, sz, TXT, 700, MUTED))
        ty += 3.7
        for i, P in enumerate(PS):
            if i % 2 == 0: o.append(f'<rect x="{f(tx-1)}" y="{f(ty-2.6)}" width="{f(cw+1)}" height="3.7" fill="#F5F2EC"/>')
            o.append(t(tx, ty, P, TXT, 700))
            for j, sz in enumerate(szs):
                r = ALL.get(sz, {}).get(P)
                o.append(t(tx + 9 + j * colw, ty, f"{r['full']['size_mm'][0]:.0f}×{r['full']['size_mm'][1]:.0f}" if r else "—", TXT))
            ty += 3.7
        ty += 1.5
    ty = para(o, tx, ty + 1, "Other sizes: after the size-M strike-off.", TXT, 400, MUTED, width=cw) + 4
    ty = para(o, tx, ty, "KEEP-OUTS (mm from the sew line)", 2.6, 700, INK, width=cw) + 1
    for k in ["Rev B seam-true wrap: the art stops 3 mm short of every seam it crosses: armhole / cap, side, shoulder, sleeve underarm (no armhole topstitch).",
              "CF zip 15 each side (teeth + tape + topstitch) · hem-rib seam 10 · cuff 10 · welt box 6 · neck 6 (art runs under the collar fall) · rib never embroidered.",
              "!Rib may change: re-check the hem / cuff keep-outs on the new rib [proposed].",
              "Match marks: G7 + the 1:1 placement plot (art placement only)."]:
        ty = para(o, tx, ty, k.lstrip("!"), 2.3, 600 if k.startswith("!") else 400, ORANGE if k.startswith("!") else INK, width=cw) + 1.6
    para(o, tx, ty + 3, f"Red line = keep-out boundary (art may not cross it). Blue dashed box = art box, blue dashed lines = hoop split lines (G6). Size M, all pieces at {SC:.3f}:1.", TXT, 400, MUTED, width=cw)
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

# ---------------------------------------------------------------- G3
def threads():
    pg = Pager("G3", "THREAD + TRIM SUMMARY", "One palette for the whole jacket - 9 threads. Approve a physical thread board (Isacord or Madeira Polyneon) before sampling; hex = on-screen target, render = the render's own pixels of that tone.")
    o = pg.o; RS = render_samples()
    use = {k: {} for k in WC.WV_KEYS}
    for p in PS:
        for c in CUR[p]["colours"]:
            if c in use: use[c][p] = use[c].get(p, 0) + 1
    hd = ["", "Thread", "Target", "Render", "Isacord", "ΔE", "Madeira Polyneon", "ΔE", "Wt", "Used for", "Stops\nBK/FR/FL/SR/SL"]
    cx = [12, 18, 44, 58, 76, 102, 110, 138, 146, 153, 258]
    y = pg.y
    for x, h in zip(cx, hd):
        for k, l_ in enumerate(h.split("\n")): o.append(t(x, y + k * 2.9, l_, TXT, 700, MUTED))
    TH = SB.TH; rh = 5.2; y += 7.5
    def sw_hex(x, y, hx):
        return f'<rect x="{f(x)}" y="{f(y-2.6)}" width="3.6" height="3.2" fill="{hx}" stroke="#999" stroke-width="0.15"/>'
    ALT = WC.FOAM_WHITE_ALT
    rows = WC.WV_KEYS + ["alt"]
    dcol = lambda d: GREEN if d < 3 else (ORANGE if d < 5.5 else RED)
    for i, k in enumerate(rows):
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y-3.6)}" width="{f(RM-10)}" height="{f(rh)}" fill="#F5F2EC"/>')
        if k == "alt":                       # the render's white: ALTERNATE to the primary ecru foam thread (founder 20 Oct)
            m_i, m_p = tech.match(ALT[0], "isacord"), tech.match(ALT[0], "polyneon")
            o.append(sw_hex(cx[0], y, ALT[0])); o.append(t(cx[1], y, ALT[1].split(" (")[0], TXT, 700, ORANGE)); o.append(t(cx[2], y, ALT[0], TXT, 400, MUTED))
            o.append(sw_hex(cx[3], y, ALT[0])); o.append(t(cx[3] + 4.5, y, "= render", 2.0, 400, MUTED))
            o.append(t(cx[4], y, f"{m_i[0]} {m_i[1]}", TXT, 400, ORANGE)); o.append(t(cx[5], y, f"{m_i[3]:.1f}", TXT, 600, dcol(m_i[3])))
            o.append(t(cx[6], y, f"{m_p[0]} {m_p[1]}", TXT, 400, ORANGE)); o.append(t(cx[7], y, f"{m_p[3]:.1f}", TXT, 600, dcol(m_p[3])))
            o.append(t(cx[8], y, "40", TXT)); o.append(t(cx[9], y, "ALTERNATE - the render's white (foam + drops if the ecru is rejected)", TXT, 700, ORANGE))
            o.append(t(cx[10], y, "—", TXT, 400, MUTED))
            y += rh; continue
        iso, pn = TH[k]["isacord"], TH[k]["polyneon"]
        o.append(swatch(cx[0], y, k, 4.5, 3.0)); o.append(t(cx[1], y, PAL[k][1], TXT, 600)); o.append(t(cx[2], y, HEX[k], TXT, 400, MUTED))
        if k in RS: o.append(sw_hex(cx[3], y, RS[k])); o.append(t(cx[3] + 4.5, y, RS[k], 2.0, 400, MUTED))
        o.append(t(cx[4], y, f"{iso[0]} {iso[1]}"[:22], TXT)); o.append(t(cx[5], y, f"{iso[3]:.1f}", TXT, 600, dcol(iso[3])))
        o.append(t(cx[6], y, f"{pn[0]} {pn[1]}"[:24], TXT)); o.append(t(cx[7], y, f"{pn[3]:.1f}", TXT, 600, dcol(pn[3])))
        o.append(t(cx[8], y, "40", TXT))
        ul = wrap(PAL[k][2] + (" - PRIMARY foam thread (founder 20 Oct)" if k == "w1" else ""), cx[10] - cx[9] - 3, TXT)
        o.append(t(cx[9], y, ul[0] + (" …" if len(ul) > 1 else ""), TXT, 600 if k == "w1" else 400, INK if k == "w1" else MUTED))
        o.append(t(cx[10], y, " / ".join(str(use[k].get(p, 0)) for p in PS), TXT, 600))
        y += rh
    pg.y = y + 1.5
    ec = HEX["w1"]; mi, mp = tech.match(ec, "isacord"), tech.match(ec, "polyneon")
    sug = {b: next((r for r in tech.TH[b] if r[0] == c), None) for b, c in (("isacord", "0151"), ("polyneon", "1801"))}
    sh = lambda r: ("#%02X%02X%02X" % tuple(r[2])) if r else "?"
    pg.para(12, "ΔE2000 vs target: green < 3, amber 3-5.5, red > 5.5 - amber / red rows must be picked from the physical card (F1). All targets PROPOSED (read from the low-res render + close-ups).", TXT, 400, MUTED, gap=1.0)
    pg.para(12, f"Foam = {PAL['w1'][1].upper()} {ec} - founder decision 20 Oct: sample ECRU foam + CHENILLE first. The ecru is matched to the nearest thread in each book: "
                f"Isacord {mi[0]} {mi[1]} {mi[2]} (ΔE {mi[3]:.1f}) · Polyneon {mp[0]} {mp[1]} {mp[2]} (ΔE {mp[3]:.1f}). The render's white {ALT[0]} is the ALTERNATE row (orange).", NOTE, 600, INK, gap=1.0)
    si, sp = sug["isacord"], sug["polyneon"]
    pg.para(12, f"QUESTION: the founder's suggested Isacord 0151 is '{si[1] if si else '?'}' ({sh(si)}, much darker than the ecru) and Polyneon 1801 is '{sp[1] if sp else '?'}' ({sh(sp)}, a blue-white): "
                "neither is an ecru - which colour was meant? Until answered, the nearest book match above is used.", NOTE, 600, ORANGE, gap=1.0)
    pg.para(12, "The SHELL COLOUR + hardware colour (and probably the rib) change from the render: every blue + the ecru must be re-checked on the NEW shell before bulk.", NOTE, 700, RED, gap=2.0)
    pg.sec("TRIMS + CONSUMABLES (per jacket)")
    tr = [("Backing", "[proposed] 3.0 oz cutaway (navy / charcoal) + a 1.5 oz tearaway under the padded foam areas (or a 2nd cutaway layer), cut 30 larger than each hooping; trim to 5"),
          ("Topping", "none (canvas surface is firm); optional water-soluble topping on the foam if the loops sink - strike-off decides"),
          ("Needles", "75/11 sharp (canvas)"), ("Bobbin", "60wt navy polyester pre-wound (dark shell) - re-check on the new shell colour"),
          ("Frames", f"{FR_S} (factory.json{'' if PROF['frames_confirmed'] else ', PROPOSED'}): {HOOPS} hoopings per jacket at M (G6); a frame ≥ {max(CUR[p]['size_mm'][0] for p in PS)+30:.0f} × {max(CUR[p]['size_mm'][1] for p in PS)+30:.0f} sews every piece in one"),
          ("Patches / labels", "none on this garment - all artwork is direct embroidery")]
    table(pg, [12, 44], ["Item", "Spec"], [((a, 600, INK), (b, 400, INK, RM - 44)) for a, b in tr], size=2.3)
    return pg.done()

# ---------------------------------------------------------------- G4
def summary():
    pg = Pager("G4", "STITCH SUMMARY + OPEN QUESTIONS", "Size M files. Every count read back from the DST (stitches, trims, stops, max stitch); threads from the PES.")
    hd = ["Element", "Piece", "Art box", "Stitches", "Trims", "Trims/10k", "Stops", "Threads", "Max stitch", "Hoops", "Run time (as hooped)"]
    cx = [12, 34, 80, 104, 124, 140, 160, 174, 192, 214, 230]
    rows = []
    for p in PS:
        r = CUR[p]; sz = r["size_mm"]
        rows.append([("01 Wave", 600, INK), f"{p} {PC.NAME[p]}", f"{sz[0]:.0f} × {sz[1]:.0f}", (f"{TS(r):,}", 600, INK), f"{TT(r):,}", f"{TT(r)/TS(r)*1e4:.0f}",
                     f"{r.get('total_stops', r['stops'])}", f"{len(set(r['colours']))}", f"{r['max_stitch']:.2f} mm", f"{r['hoopings']}", f"{sum(mh(s) for s in hoop_files(r))*60:.0f} min"])
    rows.append([None, None, ("TOTAL", 700, INK), (f"{TOT:,}", 700, INK), (f"{TRIMS:,}", 700, INK), None, None, None, None, (f"{HOOPS}", 700, INK), (f"{MH_HOOP:.1f} h", 700, INK)])
    table(pg, cx, hd, rows, size=2.3, pitch=4.2)
    pg.para(12, f"Run time = factory.machine_hours: {PROF['spm']} spm + 6 s per trim + 4 s per colour change, one head, summed over the files a piece is hooped in (split sections incl. registration).", TXT, 400, MUTED)
    pg.para(12, "Fidelity first (LESSONS A11): every crest, curl and drop of the render is sewn — trims (most are spray drops + curl lines on bare fabric) and run time are reported, cleaned up after the strike-off.", TXT, 400, MUTED, gap=2.0)
    pg.sec("OPEN QUESTIONS — confirm before sampling")
    qs = [f"Hoopings per the factory (19 Oct): fronts ONE hooping each (340 x 505), back TWO, sleeves split for {FR_S} - can a sleeve ({CUR['SR']['size_mm'][0]:.0f} x {CUR['SR']['size_mm'][1]:.0f}) go in one hooping on the 750 mm field?",
          "Foam: CHENILLE in ECRU is the look to sample first (founder 20 Oct). Name your chenille machine + file format: we send a path plan per piece now (chenille_plan/) and write the chenille file once known. The lockstitch files (padded tatami + loops) are the ALTERNATE and sew today.",
          "Threads: the factory uses its supplier's colour book (brand?) - please send it; G3 gives Isacord + Polyneon + hex. SHELL + hardware colour change: re-check every thread on the new shell.",
          "Seamless wave (Rev B): stripes continue across every seam, art 3 mm short of each seam, match notches on both pieces (G7, 1:1 placement plot). No armhole topstitch.",
          "Body: Drum Island block, unchanged (founder). Cuff / hem rib probably change - re-check the hem (10) + cuff (10) keep-outs on the new rib [proposed].",
          "Grading (after the sample): A 92 % (XS-S) · B 100 % (M-XL) · C 108 % (XXL-3XL), one file per size per piece, re-clipped to each size's keep-outs. OK?",
          "Shell dye: piece-dyed + pre-washed shell assumed. If garment-washed after embroidery, wash-test the sew-out (cream foam!).",
          "Reference: the low-res render + the founder's close-ups (back, both fronts, all four sleeve halves), registered onto the mockup (pixel-aligned super-resolved crops): classes, drop silhouettes and stitch-direction grain come from the close-ups inside their footprints; the mockup decides placement + counts. Seam continuations + gap fills near seams are generated/filled from the mockup tones (G7, G8).",
          "DST/PES are production-intent drafts: the factory digitizer checks density + pull on 12 oz duck and edits before the sew-out."]
    for i, q in enumerate(qs):
        ls = wrap(q, RM - 18, NOTE); pg.need(len(ls) * NOTE * 1.6)
        pg.o.append(t(12, pg.y, f"{i+1}.", NOTE, 700)); pg.y = para(pg.o, 18, pg.y, q, NOTE) + 0.8
    return pg.done()

# ---------------------------------------------------------------- G5
def files_page():
    pg = Pager("G5", "PRODUCTION STITCH FILES + HOOP SPLITS", "DST (Tajima) + PES, one set per piece, size M (strike-off). Counts read back from the DST. Origin = centre of each file's design ((+) on the pattern, DXF layer 13).")
    o = pg.o; y0 = pg.y; LX = 186                                   # left: table + notes up to LX, right: what is digitized
    hd = ["Size", "Art", "Piece", "Full file mm", "Stitches", "Trims", "Stops", "Hoopings: section\nstitches / trims", "Fits"]
    cx = [12, 22, 30, 42, 66, 86, 100, 114, 172]
    rows = []; allfit = True
    for sz in WC.DOC_SIZES:
        for p in PS:
            r = ALL.get(sz, {}).get(p)
            row = [(sz if p == "BK" else "", 700, INK), (WC.GRADE[sz][0] if p == "BK" else "", 700, RED), (p, 600, INK)]
            if r and "full" in r:
                fu = r["full"]; ss = secs(r)
                txt = "  ".join(f"{nm.split('_')[0]} {TS(s_)//1000}k/{TT(s_)}" for nm, s_ in ss.items()) if ss else "1 hooping (full file)"
                fits = all(v["fits"] for v in ss.values()) if ss else one_hoop_ok(p, fu["size_mm"])
                allfit &= fits
                row += [f"{fu['size_mm'][0]:.0f} × {fu['size_mm'][1]:.0f}", f"{TS(fu):,}", f"{TT(fu)}", f"{fu['stops']}", (txt, 400, INK, cx[8] - cx[7] - 2), ("yes" if fits else "CHECK", 700, GREEN if fits else RED)]
            else:
                row += [("pending", 400, MUTED)]; allfit = False
            rows.append(row)
    table(pg, cx, hd, rows, size=2.3, pitch=4.0, x1=LX)
    y = pg.y + 1
    y = para(o, 12, y, f"All files fit their hooping (splits: the {FR_S} frame incl. registration crosses; fronts: the factory's confirmed 340 × 505 single hooping): {'yes' if allfit else 'CHECK'}", NOTE, 700, GREEN if allfit else RED, width=LX - 12) + 2
    y = para(o, 12, y, "Sampling package: size M only. XS-S (grade A 92 %), L-XL (B) and XXL-3XL (C 108 %) are rebuilt from the same art after the strike-off, with any density / pull changes it asks for. The frame is read from factory.json: a bigger frame re-splits every file in one rebuild.", NOTE, 400, MUTED, width=LX - 12) + 3
    y = para(o, 12, y, "SEWING A SPLIT PIECE: see G6 (order, registration crosses, hooping a cut panel, backing, foam).", NOTE, 700, INK, width=LX - 12) + 3
    y = para(o, 12, y, f"FOAM SWATCH (F1): {os.path.basename(SWT['file'])}.dst", NOTE, 700, ORANGE, width=LX - 12)
    para(o, 12, y, f"{SWT['stitches']:,} st · {SWT['trims']} trims · {SWT['size_mm'][0]:.0f} × {SWT['size_mm'][1]:.0f} mm · 1 hooping", NOTE, 400, ORANGE, width=LX - 12)
    bx = LX + 8; bw = RM - bx; y2 = y0
    y2 = para(o, bx, y2, "WHAT IS DIGITIZED", SEC, 700, INK, width=bw) + 1
    notes = [("Stripes", f"tatami rows ALONG the stripe (one flow field per piece from the stripe edges + rope cords), {WC.CORD_TWIST:.0f}° cord twist alternating per tone; narrow stripes too (no across-satin). Render patches < 150 mm² merged into their band = one continuous cord each."),
             ("Rope lines", "continuous 2.4 mm cream cords (traced fragments joined), turning satin."),
             ("Foam", "CHENILLE first (path plan, chenille_plan/); lockstitch alternate in these files: padded tatami, rows parallel to the crest outline, spiral curl cord + loop spiral, grey hollows = thin ridges."),
             ("Seams", "one smooth warp per piece side lines the stripes up across every seam; 3 mm short; art under the collar fall (G7)."),
             ("Ties", f"3-stitch tie-on/off at every trim + colour change; max sewn stitch ≤ 7.5 mm; ≤ {FA.max_threads(PROF)} colours per file incl. registration.")]
    for a, l_ in notes:
        o.append(t(bx, y2, a, NOTE, 700)); y2 += NOTE * 1.6
        y2 = para(o, bx, y2, l_, 2.3, width=bw) + 1.4
    return pg.done()

# ---------------------------------------------------------------- G6
def hooping_page():
    pg = Pager("G6", "HOOPING TABLE — split lines + needle starts per file (size M strike-off)",
               f"Frame {FR_S} mm (factory.json{'' if PROF['frames_confirmed'] else ', PROPOSED'}). Coordinates in mm on each piece's pattern (see G2). DXF layer 13 = these points.")
    hd = ["Size", "Piece", "Hoops", "Split x / y", "Needle start per file (x, y) · file mm", "Fit", "Machine time"]
    cx = [12, 24, 38, 52, 80, 238, 254]
    rows = []
    for sz in WC.DOC_SIZES:
        for P in PS:
            r = ALL.get(sz, {}).get(P)
            if not r: continue
            sp = r.get("splits") or {}; ss = secs(r)
            xs_ = sp.get("xs") or ([sp["sx"]] if sp.get("sx") is not None else []); ys_ = sp.get("ys") or ([sp["sy"]] if sp.get("sy") is not None else [])
            sxy = (",".join(f"{v:.0f}" for v in xs_) or "—") + " / " + (",".join(f"{v:.0f}" for v in ys_) or "—") if ss else "—"
            if ss:
                txt = "  ·  ".join(f"{nm.split('_')[0]} ({s_['origin'][0]:+.0f}, {s_['origin'][1]:.0f}) {s_['size_mm'][0]:.0f}×{s_['size_mm'][1]:.0f}" for nm, s_ in ss.items())
                ok = all(v["fits"] for v in ss.values())
            else:
                fo = r["full"]["origin"]; txt = f"full ({fo[0]:+.0f}, {fo[1]:.0f}) {r['full']['size_mm'][0]:.0f}×{r['full']['size_mm'][1]:.0f}"; ok = True
            rows.append([(sz if P == "BK" else "", 700, INK), (P, 600, INK), f"{r['hoopings']}", (sxy, 700, RED if ss else MUTED), (txt, 400, INK, cx[5] - cx[4] - 3),
                         ("yes" if ok else "NO", 700, GREEN if ok else RED), f"{sum(mh(s) for s in hoop_files(r))*60:.0f} min"])
    table(pg, cx, hd, rows, size=2.3, pitch=4.0)
    pg.sec("HOOPING ORDER + RE-REGISTRATION (review item 7)")
    for P in PS:
        r = CUR[P]; ss = secs(r)
        if not ss: pg.para(14, f"{P}: one hooping (full file).", NOTE); continue
        seen = []; parts = []
        for nm, s_ in ss.items():
            mk = [tuple(m) for m in s_.get("marks", [])]
            shared = [m for m in mk if any(abs(m[0] - q[0]) < 0.6 and abs(m[1] - q[1]) < 0.6 for q in seen)]
            parts.append(f"{nm.split('_')[0]}" + (f" (re-register on {len(shared)} cross{'es' if len(shared) != 1 else ''} at " + ", ".join(f"({m[0]:+.0f}, {m[1]:.0f})" for m in shared[:3]) + ")" if shared else " (first)"))
            seen += mk
        pg.para(14, f"{P}: " + "  →  ".join(parts), NOTE)
    pg.y += 1.5
    pg.sec("HOOPING A CUT PANEL + BACKING [proposed - the strike-off confirms]")
    for l_ in ["• Chalk CF / CB, the split lines, the needle starts and the match notches on the cut piece from the 1:1 placement plot (out/placement, art placement only).",
               "• Hoop the BACKING only (adhesive-backed cutaway, or cutaway + temporary spray) and float the cut panel on it, aligned on the chalk marks; pin only inside the seam allowance.",
               "• Section 2+ : never clamp the hoop ring over foam that is already sewn (it crushes the padding) - float again on a freshly hooped backing, or use a magnetic frame.",
               "• Align each new hooping on the registration crosses its file shares with the previous one (above): the machine sews the crosses first - check they land on the sewn ones.",
               "• Backing for dense padded foam on 12 oz duck: 3.0 oz cutaway + 1.5 oz tearaway under the foam areas (or two cutaway layers). 2.5 oz alone is too light for this density.",
               "• No armhole topstitch (Rev B): the wave runs to 3 mm from the armhole seam on body + sleeve; press the seam open or to the body, do not topstitch over the art."]:
        pg.para(14, l_, NOTE, gap=0.4)
    pg.y += 1.5
    pg.para(12, "Split lines are chosen where they cut the least art inside the frame; curls/drops under 70 mm go whole to one file, larger fills overlap 1.2 mm across the line. "
                f"Needle start = centre of each file's design (origin of the DST/PES). Registration crosses sew at the start of stop 1 in that stop's thread (factory: max {FA.max_threads(PROF)} colours per file, "
                "no separate basting colour); the next hooping re-registers on the crosses on its split line; pick them out after the last hooping. Machine time incl. trims + colour changes.", TXT, 400, MUTED)
    return pg.done()

# ---------------------------------------------------------------- G7
def seams_page():
    pg = Pager("G7", "SEAM CONTINUITY + MATCH MARKS — the seamless wave (Rev B)",
               "Measured on the shipped DSTs (continuity.py): along every seam, art 1-3 mm inside each side's keep-out; meet = the other side also has art there (±2 mm), tone = same thread group (±4 mm).")
    import wrap as WR
    hd = ["Seam", "Pieces (A / B)", "Length A / B mm", "Art on seam", "Meet", "Same tone", "Match marks", "Tone agrees"]
    cx = [12, 48, 90, 124, 150, 170, 196, 222]
    col = (lambda v: MUTED if v is None else (GREEN if v >= 85 else (ORANGE if v >= 70 else RED)))
    rows = []
    for sm in WR.seams("M"):
        nm = sm["name"]; c = CONT.get(nm, {}); m = MMK.get(nm); mt = c.get("meet"); tn = c.get("tone")
        if c.get("art_mm", 0) < 10: mt = tn = None                  # < 10 mm of art on the seam: not graded (named below)
        rows.append([(nm, 700, INK), f"{sm['A'][0]} / {sm['B'][0]}" + (" (no seam)" if sm["kind"] == "internal" else ""), f"{sm['len_A']:.0f} / {sm['len_B']:.0f}", f"{c.get('art_mm', 0)} mm",
                     ("—" if mt is None else f"{mt} %", 700, col(mt)), ("—" if tn is None else f"{tn} %", 700, col(tn)),
                     f"{len(m['marks'])}" if m else "—", f"{m['agree']}/{len(m['marks'])}" if m else "—"])
    table(pg, cx, hd, rows, size=2.3, pitch=3.9, x1=250)
    pg.para(12, "Meet / same tone: green ≥ 85 %, amber ≥ 70 %, red below; — = under 10 mm of art on the seam (not graded).", TXT, 400, MUTED, gap=1.0)
    small = [(nm, v["art_mm"]) for nm, v in CONT.items() if 0 < v.get("art_mm", 0) < 10]
    for nm, a_ in small:
        pg.para(12, f"{nm}: {a_} mm of art on the whole seam - one spray drop at the underarm corner; the back render is bare along this armhole, so there is nothing to continue (checked on the render, not a mapping fault).", 2.3, 400, INK, gap=0.4)
    SE = json.load(open("seamedge_M.json")) if os.path.exists("seamedge_M.json") else {}
    if SE:
        pg.para(12, "ONE-SIDED runs (the partner piece is bare in the mockup, e.g. shoulder L: the front wave runs over the shoulder, the back render shows bare fabric there): nothing is invented on the bare piece; "
                    "the foam now ENDS IN LOBES there (seamedge.py, generated) instead of a straight cut along the seam: " + "; ".join(f"{k} {v['mm']} mm" for k, v in SE.items()) +
                    ". Meet / tone on those seams stay low BY DESIGN of the mockup - founder: say if the back should carry the wave over the shoulder instead.", 2.3, 600, ORANGE, gap=1.2)
    pg.sec("How the wave crosses a seam (wrap.py + seamwarp.py, from each size's own pattern seams)", size=2.7)
    for l_ in ["• both sides are compared along the seam by SEAM LENGTH (the eased cap fraction to fraction); art stops 3 mm short of the sew line on both pieces;",
               "• each piece side is moved by ONE smooth displacement field (thin-plate spline, fading to zero ~100 mm in, fixed on armhole / CF / hem / neck / cuff): first so its art reaches the seam, then along the seam so its stripes line up with the other piece's (matched tone runs) - no band is pasted, nothing is cut;",
               "• a stripe that meets bare fabric on the other piece continues and tapers to a point there; curls + drops move whole (never sliced);",
               "• TONE handover (tonematch.py, Rev B fix round): the leader side keeps its threads (body over sleeve; CF zip / underarm / sleeve centre: more stripe on the seam), every follower stripe that meets it takes the leader's thread, whole region (no tone step inside a stripe): " + TM_TXT + ";",
               "• the sleeve centre line is not a seam: the back-view half and the front-view half are joined into one continuous trace (no fold line)."]:
        pg.para(14, l_, 2.4, gap=0.5)
    pg.para(12, "Seam alignment + tapers + the art under the collar fall are GENERATED (no reference shows them), not traced - G9 shows the check + before / after.", 2.4, 700, ORANGE)
    # match marks: own page, four column groups
    pg.new(); pg.sec("MATCH MARKS (notch on both pieces, mm along the seam from its top end; orange = the two sides differ in tone)", size=2.8)
    rows = [mk for nm, s_ in MMK.items() for mk in s_["marks"]]
    nm_ = {k: v[1].split()[0] for k, v in WC.WV_PAL.items()}
    p = 3.7; ng = 4; gw = (RM - 12) / ng; i = 0
    while i < len(rows):
        y0 = pg.y
        per = int((BOT - y0 - p) / p)
        if per < 4: pg.new(); continue
        per = min(per, -(-(len(rows) - i) // ng))
        for c in range(ng):
            xx = 12 + c * gw
            for x_, h in ((0, "id"), (14, "on A"), (25, "on B"), (36, "tone A / B")): pg.o.append(t(xx + x_, y0, h, TXT, 700, MUTED))
        for c in range(ng):
            xx = 12 + c * gw
            for jj in range(per):
                if i >= len(rows): break
                mk = rows[i]; yy = y0 + p + jj * p; bad = mk["tone_A"] != mk["tone_B"]
                if jj % 2 == 0: pg.o.append(f'<rect x="{f(xx-1)}" y="{f(yy-2.6)}" width="{f(gw-2)}" height="{f(p)}" fill="#F5F2EC"/>')
                pg.o.append(t(xx, yy, mk["id"], TXT, 700)); pg.o.append(t(xx + 14, yy, f"{mk['s_A']:.0f}", TXT)); pg.o.append(t(xx + 25, yy, f"{mk['s_B']:.0f}", TXT))
                pg.o.append(t(xx + 36, yy, f"{nm_.get(mk['tone_A'], '-')} / {nm_.get(mk['tone_B'], '-')}", TXT, 600 if bad else 400, ORANGE if bad else INK))
                i += 1
        pg.y = y0 + p + per * p + 2
        if i < len(rows): pg.new()
    pg.para(12, f"{len(rows)} match marks, all from out/placement/match_marks_M.json; notch them on both pieces (1:1 placement plot).", TXT, 400, MUTED)
    # seam strips: own page, one sheet per seam (out/continuity_<seam>.png, side A above, side B below), one scale for all
    from PIL import Image
    pg.new(); pg.sec("SEAM STRIPS — every seam rendered from the shipped DSTs (side A above, side B below, seam closed up; red ticks = match marks; one scale)", size=2.6)
    shs = []
    for sm in WR.seams("M"):
        fn = f"out/continuity_{sm['name'].replace(' ', '_')}.png"
        if os.path.exists(fn):
            im = Image.open(fn); shs.append((sm["name"], CONT.get(sm["name"], {}), im.crop((0, 28, im.width, im.height))))   # the sheet's own 1-line caption is replaced by ours
    y0 = pg.y; avail = BOT - 5 - y0; cap = TXT * 1.6; gap = 5.0; mw = max(im.width for _, _, im in shs); best = None
    def lay(ncol, sc):
        cw = (RM - 12 - (ncol - 1) * gap) / ncol; c, yy, pos = 0, y0, []
        for k, (_, _, im) in enumerate(shs):
            h = cap + im.height * sc + 2.0
            if yy + h > y0 + avail: c += 1; yy = y0
            if c >= ncol: return None
            pos.append((12 + c * (cw + gap), yy)); yy += h
        return pos
    for ncol in (1, 2, 3):
        sc = ((RM - 12 - (ncol - 1) * gap) / ncol) / mw
        while sc > 0.005 and lay(ncol, sc) is None: sc *= 0.97
        if lay(ncol, sc) and (best is None or sc > best[0]): best = (sc, lay(ncol, sc))
    sc, pos = best
    for (nm, c, im), (x, yy) in zip(shs, pos):
        mt, tn = c.get("meet"), c.get("tone")
        pg.o.append(t(x, yy + TXT, f"{nm}" + (f"  ·  meet {mt} %  ·  same tone {tn} %" if mt is not None else "  ·  no art on this seam"), TXT, 700))
        tag, _ = img_tag(im, x, yy + cap, im.width * sc); pg.o.append(tag)
    para(pg.o, 12, BOT + 1, f"Scale {sc * 1000:.0f} mm per 1000 px of the sheets; each sheet at full size: out/continuity_<seam>.png (+ _art.png = the art before stitching).", TXT, 400, MUTED)
    return pg.done()

# ---------------------------------------------------------------- G8
def gates_page():
    pg = Pager("G8", "FIDELITY GATES — LESSONS A14 (motif match) + A15 (coverage), shipped DSTs vs the reference",
               "Reference = the mockup's tone classes, and inside the founder close-ups' footprints the close-up's own pixels (re-trace, 20 Oct); garment details + keep-outs masked out (A15). One row per piece and motif family.")
    hd = ["Piece", "Family", "Ref. motifs", "DST motifs", "Pass", "Fail (open)", "Moved > 3 mm (max)", "IoU median", "Uncovered ≥ 25 mm²", "Unexplained"]
    cx = [12, 26, 46, 68, 88, 102, 126, 160, 182, 222]
    is_un = lambda u: not str(u.get("why", "")).startswith("keep-out edge")
    rows = []; seen = set(); n_open = 0; tot_un = 0
    for r in GATES["summary"]:
        P, fam = r["piece"], r["family"]; g = GATES["pieces"].get(P, {}); gf = g.get(fam, {})
        fl = r.get("failed", 0); n_open += fl
        row = [(P if P not in seen else "", 700, INK), fam, f"{r.get('motifs', '-')}", f"{gf.get('dst_count', '-')}", (f"{r.get('passed', '-')}", 600, GREEN),
               (f"{fl}", 700, RED if fl else MUTED), f"{r.get('moved', 0)} ({r.get('max_move', 0):.0f} mm)", f"{r.get('iou_median', '-')}"]
        if P not in seen:
            un = g.get("uncovered", []); ue = [u for u in un if is_un(u)]; tot_un += len(ue)
            row += [f"{len(un)} ({sum(u.get('area_mm2', 0) for u in un):.0f} mm²)", (f"{len(ue)}", 700, RED if ue else GREEN)]
        seen.add(P); rows.append(row)
    table(pg, cx, hd, rows, size=2.3, pitch=3.8)
    ppm_d = next((x.get("gate_ppm") for P in PS for x in GATES["pieces"].get(P, {}).get("drops", {}).get("rows", []) if x.get("gate_ppm")), None)
    for l_ in ["• Motif gate (A14, qa.motif_match) reads the VISIBLE top layer of the written DST: hidden travel runs no longer merge crests. Pass = IoU ≥ 0.70 and width + height each ≥ 80 % of the reference motif (a stand-in of the right size but the wrong silhouette fails).",
               f"• Drops are graded at {ppm_d or 12:g} ppm against their traced silhouette (close-up resolution where covered) : the sewn drop = the z-buffer of every stitch (a pixel counts when its TOP thread is that drop's), fabric pull-in modelled (fix round 3: the re-centred visible segments used before left false holes in satin). Each drop is ONE satin at one declared angle (the close-up grain on the drop where clear, else its long axis), pull compensation at the stitch ends only.",
               "• Uncovered (A15, qa.uncovered) = mockup-embroidered areas ≥ 25 mm² the DST leaves bare. The art fills every gap from the mockup / close-up tones (gapfill.py): only a 'keep-out edge' may stay bare - anything else is UNEXPLAINED (red).",
               "• Every motif (crest, drop, wave mass) is compared with the stitches within 1-1.5 mm of IT (LESSONS A21), so a thin sewn bridge to a neighbour no longer scores the neighbour against it (wave masses since fix round 3).",
               "• CURLS = cream + grey crests ≥ 100 mm² (one row per crest), DROPS = cream motifs 4-100 mm², STRIPES = the blue band regions. Moved: the Rev B wrap moves art near seams on purpose; each motif is matched at its best local shift within ±40 mm and the shift is reported."]:
        pg.para(12, l_, 2.3, gap=0.4)
    ok = not n_open and not tot_un
    pg.y += 2.5
    pg.para(12, f"Result: {n_open} failing motif rows (open), {tot_un} unexplained bare areas — " + ("PASS" if ok else "OPEN: see the rows below (positions on the compare sheets)"), SEC, 700, GREEN if ok else RED, gap=1.0)
    pg.sec("FAILING MOTIF ROWS per piece + family (every failing row is open)", size=2.6)
    rows3 = []
    for P in PS:
        g = GATES["pieces"].get(P, {}); why = {}; cnt = {}
        for fam in ("curls", "drops", "stripes"):
            fr = [x for x in g.get(fam, {}).get("rows", []) if not x.get("ok", True)]; cnt[fam] = len(fr)
            for x in fr: why[x.get("why", "no reason given")] = why.get(x.get("why", "no reason given"), 0) + 1
        un = g.get("uncovered", []); ke = sum(1 for u in un if not is_un(u))
        rows3.append([(P, 700, INK)] + [(f"{cnt[k]}", 700, RED if cnt[k] else GREEN) for k in ("curls", "drops", "stripes")] + [f"{ke}",
                     (" · ".join(f"{k} {v}" for k, v in sorted(why.items(), key=lambda kv: -kv[1])) or "—", 400, INK, RM - 112)])
    table(pg, [12, 28, 44, 60, 82, 112], ["Piece", "Curls", "Drops", "Stripes", "Bare: keep-out\nedge (allowed)", "Reasons (gates_M.json 'why')"], rows3, size=2.3, pitch=3.8)
    pg.para(12, "Per-piece tables with the position of every failing / uncovered row: out/compare_<piece>.png (under the side-by-side) and gates_M.json.", TXT, 400, MUTED)
    ds = [GATES["pieces"][P].get("direction") for P in PS if GATES["pieces"].get(P, {}).get("direction")]
    ppm = next((d.get("ref_ppm") for d in ds if d.get("ref_ppm")), None)
    pg.new()                                                          # direction gets its own page (legibility)
    pg.sec(f"STITCH DIRECTION (A16/A17) vs the CLOSE-UP grain ({ppm or 12:g} ppm); tiles with no close-up are masked, not judged; target ≥ 85 % OK per family", size=2.8)
    fams = [("stripes", "Stripes"), ("foam", "Foam (alt.)"), ("drops", "Drops")]
    hd2 = ["Piece", "All visible"] + [x for _, n in fams for x in (n + " % OK", "masked")] + ["Close-up share", "Heat-map"]
    cx2 = [12, 26, 54, 80, 96, 122, 138, 160, 176, 206]
    rows2 = []
    for P in PS:
        dr = GATES["pieces"].get(P, {}).get("direction")
        if not dr: continue
        bf = dr.get("by_family", {}); row = [(P, 700, INK), f"{dr.get('pct_ok', '-')} % of {dr.get('tiles', '-')}"]
        for k, _ in fams:
            v = bf.get(k)
            if not v or not v.get("tiles"): row += [("—", 400, MUTED), ""]; continue
            row += [(f"{v['pct_ok']} %", 700, GREEN if v["pct_ok"] >= 85 else RED), f"{v.get('masked', 0)}"]
        cs = dr.get("closeup_share"); row += [f"{cs*100:.0f} %" if isinstance(cs, (int, float)) else "—", (f"out/compare_{P}.png", 400, MUTED)]
        rows2.append(row)
    table(pg, cx2, hd2, rows2, size=2.3, pitch=3.8)
    pg.para(12, "Foam: the files sew the lockstitch ALTERNATE; the primary look is chenille (path plan), so the foam row grades the alternate only.", 2.4, 600, ORANGE, gap=1.5)
    return pg.done()

# ---------------------------------------------------------------- G9
def treatment_page():
    pg = Pager("G9", "SEAM TREATMENT CHECK — internal discontinuities + before / after (founder review 19 Oct)",
               "discont.py on the shipped DSTs: probe lines 8-120 mm from every seam; a stripe edge must continue across each probe (jump ≤ 1 mm) and no straight cut line may run along a seam.")
    A = json.load(open("discont_M.json")); B = json.load(open("discont_M_before.json"))
    def summ(d):
        n = sum(r["edges"] for v in d.values() for k, r in v.items() if k != "straight_cuts"); j = sum(r["jump_gt1"] for v in d.values() for k, r in v.items() if k != "straight_cuts")
        par = sum(1 for v in d.values() for c in v["straight_cuts"]["lines"] if c[0] == "parallel")
        return n, j, par
    nb, jb, pb = summ(B); na, ja, pa = summ(A)
    rows = [("edges probed", nb, na), ("edges jumping > 1 mm", f"{jb} ({100*jb/max(nb,1):.1f} %)", f"{ja} ({100*ja/max(na,1):.1f} %)"),
            ("straight cut lines along a seam (≥ 12 mm, constant depth)", pb, pa)]
    tr = []
    for i, (a, b, c) in enumerate(rows):
        # PR #27 review 4: the rule is "no straight cut line may run along a seam", so any cut line left is RED and listed (never green
        # for being fewer than before); jumping edges above the 8 % noise floor are orange
        cc = (RED if pa else GREEN) if i == 2 else ((ORANGE if ja / max(na, 1) > 0.08 else GREEN) if i == 1 else INK)
        tr.append([a, (f"{b}", 600, INK), (f"{c}" + ("  OPEN - listed below" if i == 2 and pa else ""), 700, cc)])
    table(pg, [12, 130, 190], ["Stripe edges followed across probe lines (all seams, DST)", "Before (seamfill band)", "After (smooth warp)"], tr, size=2.5, pitch=4.2)
    pg.para(12, "Noise floor: the trace's own tone boundaries wobble (flecks, tone steps), so ~5-10 % of edges 'jump' > 1 mm everywhere, also 100 mm+ from any seam; a cut line shows as a straight edge at constant depth (the old band ends). "
                "Per seam in out/discont_<seam>_<side>.png: magenta = straight cut lines, red rings = edge jumps > 1 mm. Before / after crops: next page.", TXT, 400, MUTED, gap=2.0)
    cut = {k: v["straight_cuts"] for k, v in A.items() if v["straight_cuts"]["lines"]}
    ntot = sum(v.get("n", len(v["lines"])) for v in cut.values())
    pg.sec(f"STRAIGHT CUT LINES STILL OPEN (after) — {pa} along a seam (parallel, the table row) + {ntot - pa} across it, on {len(cut)} seam sides (discont_M.json)", RED if cut else GREEN, size=2.8)
    if cut:
        pg.para(12, "parallel = a straight tone edge running along the seam at that depth (mm in from the seam), over that stretch (mm along the seam from its top end); "
                    "across = a straight tone edge crossing the probe band at that position along the seam, starting that deep. Each must be removed or explained before the sew-out.", TXT, 400, MUTED, gap=1.0)
    for k, v in cut.items():
        ls = sorted(v["lines"], key=lambda c: (c[0], c[2]))
        txt = " · ".join((f"parallel {c[1]:.0f} mm in, {c[2]:.0f}-{c[3]:.0f} along" if c[0] == "parallel" else f"across at {c[2]:.0f}, from {c[1]:.0f} in") for c in ls)
        if v.get("n", len(ls)) > len(ls): txt += f" · + {v['n'] - len(ls)} more (not stored)"
        lines = wrap(txt, RM - 62, TXT); pg.need(len(lines) * TXT * 1.6)
        pg.o.append(t(12, pg.y, f"{k} ({v.get('n', len(ls))})", TXT, 700, RED))
        pg.y = para(pg.o, 62, pg.y, txt, TXT, 400, RED) + 0.6
    # before / after crops: their own page, the five areas packed as large as the page allows
    from PIL import Image
    import itertools, crops as CR
    im = Image.open("out/crops_before_after.png")
    pg.new(); pg.sec("BEFORE / AFTER — the areas the founder flagged (crops.py, every stitch of the DST): left = before (seamfill band), right = after (shipped files)", size=2.6)
    items = []; yy = 0; ppm = 3.0
    for P, ar in CR.AREAS.items():
        for name, bb in ar:
            w_, h_ = int((bb[2] - bb[0]) * ppm), int((bb[3] - bb[1]) * ppm)
            items.append((f"{P} {name}", im.crop((0, yy + 26, 2 * w_ + 30, yy + 26 + h_)), (w_ + 30) / (2 * w_ + 30))); yy += h_ + 36
    if yy != im.height:                                   # sheet layout changed: fall back to its row bands (captions stay in the image)
        items = [("", _trim_w(b), 0.5) for b in _bands(im, 20)]
    W = RM - 12; gap = 5.0; cap = 2 * TXT * 1.5 + 1.5; y0 = pg.y; avail = BOT - y0; best = None
    for R in (1, 2, 3):
        for asg in itertools.product(range(R), repeat=len(items)):
            if len(set(asg)) != R: continue
            rws = [[it for it, a in zip(items, asg) if a == r] for r in range(R)]
            hs = [(W - gap * (len(rw) - 1)) / sum(x[1].width / x[1].height for x in rw) for rw in rws]
            k = min(1.0, (avail - R * cap - (R - 1) * 4) / sum(hs)); hs = [h * k for h in hs]
            sc = min(h / x[1].height for h, rw in zip(hs, rws) for x in rw)
            if best is None or sc > best[0]: best = (sc, rws, hs)
    _, rws, hs = best; y = y0
    for rw, h in zip(rws, hs):
        x = 12
        for nm, b, fr in rw:
            w = h * b.width / b.height
            if nm:
                pg.o.append(t(x, y, nm, TXT, 700)); pg.o.append(t(x, y + TXT * 1.5, "BEFORE", TXT, 600, MUTED)); pg.o.append(t(x + w * fr, y + TXT * 1.5, "AFTER", TXT, 700, GREEN))
            tag, _ = img_tag(b, x, y + cap - 1.0, w); pg.o.append(tag); x += w + gap
        y += cap + h + 4
    return pg.done()

def f1_pages():
    import sheet as _SH; _SH.FOOT = SB.FOOT
    so = []
    for p in PS:
        r = CUR[p]
        for s in hoop_files(r):
            nm = os.path.basename(s["file"]); tag = f"{p}" + ("" if s is r else " · " + nm.split("_M_")[-1])
            so.append(dict(file=nm + ".dst", piece=tag + " · lockstitch", stitches=s["stitches"], trims=s["trims"]))
    so.insert(0, dict(file=os.path.basename(SWT["file"]) + ".dst", piece="FOAM SWATCH (sew first)", stitches=SWT["stitches"], trims=SWT["trims"]))
    th = [dict(name=PAL[k][1], code=f"Isacord {SB.TH[k]['isacord'][0]} / Polyneon {SB.TH[k]['polyneon'][0]}", de=min(SB.TH[k]["isacord"][3], SB.TH[k]["polyneon"][3])) for k in WC.WV_KEYS]
    pcs = [dict(piece=f"01 {p} {PC.NAME[p]}", w=CUR[p]["size_mm"][0], h=CUR[p]["size_mm"][1], hoopings=CUR[p]["hoopings"]) for p in PS]
    pages = FA.requests_page(WC.NAME, so, th, pcs, page="F1", prof=PROF)
    # Rev B additions appended to F1 (right column)
    lines = [("6  Foam: CHENILLE in ECRU first (founder 20 Oct)", 1), ("Sample the foam as chenille, ecru thread (Isacord 0184 Pearl).", 0),
             ("Tell us your chenille machine + file format (see 5): we send", 0), ("a PATH PLAN per piece now (chenille_plan/: json in piece mm", 0),
             ("+ preview) and write the chenille file once we know it.", 0), ("ALTERNATE: the lockstitch files here (padded tatami + loops).", 0), ("", 0),
             ("7  Foam swatch - sew first", 1), (f"{os.path.basename(SWT['file'])}.dst ({SWT['stitches']:,} st, 1 hooping): padded", 0),
             ("vs moss look, ecru vs white - confirm the ecru on the shell.", 0), ("", 0),
             ("8  Hoopings (your answer 19 Oct)", 1), ("Fronts: ONE hooping each (340 x 505 confirmed). Back: 2.", 0),
             ("Sleeves: 2 each for 400 x 450 - can a sleeve go in ONE", 0), ("hooping on your 750 mm field? Which frame holds 340 x 505?", 0), ("The full files are REFERENCE only - price + sew the hoopings.", 0), ("", 0),
             ("9  Thread colour book", 1), ("Please send your supplier's book (brand?): we give Isacord +", 0),
             ("Polyneon refs + hex (G3); pick the nearest per colour. Re-check", 0), ("on the NEW shell colour (shell / hardware / rib change).", 0), ("", 0),
             ("10 Backing + seams", 1), ("3.0 oz cutaway + 1.5 oz tearaway under the foam; float cut", 0),
             ("panels, never hoop over sewn foam. Notch the match marks;", 0), ("stripes meet across the seams; no armhole topstitch.", 0)]
    extra = "".join(f'<text x="168" y="{40 + i*4.0:.1f}" font-family="{_SH.FONT}" font-size="{2.6 if h else 2.2}" font-weight="{700 if h else 400}" fill="{ORANGE}">{l}</text>' for i, (l, h) in enumerate(lines))
    return [pg.replace("</svg>", extra + "</svg>") for pg in pages]

# ---------------------------------------------------------------- build
NAMES = {"G2": "Placement overview", "G3": "Thread + trim summary", "G4": "Stitch summary + open questions", "G5": "Production stitch files + hoop splits",
         "G6": "Hooping table, order, backing", "G7": "Seam continuity + match marks", "G8": "Fidelity gates (A14-A17)", "G9": "Seam treatment check + before / after"}
def build():
    secs_ = [("G2", [("G2", overview())]), ("G3", threads()), ("G4", summary()), ("G5", files_page()), ("G6", hooping_page()),
             ("G7", seams_page()), ("G8", gates_page()), ("G9", treatment_page())]
    el = [("01 Wave (element spec)", SPEC[0])]
    index = [("G1 Cover + contents", 1)]; pg = 2; order = []
    for key, lst in secs_:
        n = len(lst); index.append((f"{key} {NAMES[key]}" + (f" ({n} pp)" if n > 1 else ""), f"{pg}" if n == 1 else f"{pg}-{pg + n - 1}"))
        order += lst; pg += n
    for name, path in el:
        n = len(PdfReader(path).pages); index.append((name + f" ({n} pp)", pg)); pg += n
    index.append(("F1 Factory requests", pg))
    order.insert(0, ("G1", cover(index)))
    for old in glob.glob("prev_G[0-9]_[0-9].png") + glob.glob("G[0-9]_[0-9].pdf"): os.remove(old)      # stale continuation pages
    w = PdfWriter()
    for lab, o in order:
        part = lab.split("(")[1].split("/")[0] if "(" in lab else "1"
        fn = lab.split(" ")[0] + ("" if part == "1" else f"_{part}")             # G7, G7_2, G7_3 ...
        svg = doc(o); cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"{fn}.pdf")
        cairosvg.svg2png(bytestring=svg.encode(), write_to=f"prev_{fn}.png", output_width=2400)
        w.append(PdfReader(f"{fn}.pdf"))
    for name, path in el: w.append(PdfReader(path))
    for i, svg in enumerate(f1_pages()):
        cairosvg.svg2pdf(bytestring=svg.encode(), write_to=f"F{i+1}.pdf"); cairosvg.svg2png(bytestring=svg.encode(), write_to=f"prev_F{i+1}.png", output_width=2400)
        w.append(PdfReader(f"F{i+1}.pdf"))
    w.write(OUT_PDF)
    print("pages", pg, [lab for lab, _ in order])

if __name__ == "__main__":
    build()
