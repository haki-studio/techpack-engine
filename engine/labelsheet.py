"""Haki standard labels on a garment pack page (engine/labels.py, LESSONS D7): BOM wording + a 1:1 artwork panel.

Main label = the ONE Haki main label (6.5 x 2 cm, white). Care label = labels.care_label(<shell composition>); when the
composition matches no standard care label (no fibre % recorded, or another fibre) the panel and the BOM print
MISSING and name what was recorded. Never the nearest label.
    rows:   main_desc(), care_desc(shell)            -> BOM / placement wording
    page:   o, h = panel(x, y, w, shell, main_where, care_where)
    BOM:    main_bom(), care_bom(shell)               -> short cells (≈ 80 characters)
    zip:    files(shell) / export(dir, shell)         -> the pack's labels/
"""
import os, io, base64, shutil, textwrap
import labels as LB
from sheet import t, INK, MUTED, GREEN
from render import f

AMBER = "#B26A00"
MISSING = "[MISSING — fibre content not confirmed]"
FIBRE = {"100-cotton": "100 % cotton", "90-cotton-10-polyester": "90 % cotton / 10 % polyester"}


def care_fibre(shell):
    """the fibre the standard care label states for this shell, or None (= MISSING)."""
    k = LB.care_key(shell)
    return FIBRE[k] if k else None


def main_desc():
    return "Haki standard main label: woven, flat, 6.5 × 2 cm, white ground, black HAKI STUDIOS logo; sewn down on all 4 sides (labels/" + os.path.basename(LB.MAIN) + ")"


def care_desc(shell):
    fb = care_fibre(shell)
    if fb: return f"Haki standard care label, {fb}: printed satin, 3 × 6.5 cm, printed front + back (labels/{os.path.basename(LB.care_label(shell))})"
    return f"Haki standard care label {MISSING}: shell recorded only as '{shell}'"


def main_bom(ref="T8"):
    return f"Haki standard: woven, flat, 6.5 × 2 cm, sewn down on all 4 sides ({ref} art)"


def care_bom(shell, ref="T8"):
    fb = care_fibre(shell)
    return f"Haki standard, {fb}: printed satin, 3 × 6.5 cm, front + back ({ref} art)" if fb else f"{MISSING} — shell has no fibre %"


def files(shell):
    return LB.files_for(shell)


def export(d, shell):
    """(re)write the label files a pack ships into directory d (emptied first, so no stale care label survives)."""
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    for p in files(shell): shutil.copy(p, d)
    return sorted(os.listdir(d))


def _img(im, x, y, w, h):
    buf = io.BytesIO(); im.convert("RGB").save(buf, "JPEG", quality=90)
    return f'<image x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" href="data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}"/>'


def _dims(x, y, w, h, wl, hl):
    dm = 'stroke="#7A1F2B" stroke-width="0.2"'
    o = [f'<line x1="{f(x)}" y1="{f(y - 2.2)}" x2="{f(x + w)}" y2="{f(y - 2.2)}" {dm}/>']
    for xx in (x, x + w): o.append(f'<line x1="{f(xx)}" y1="{f(y - 3)}" x2="{f(xx)}" y2="{f(y - 1.4)}" {dm}/>')
    o.append(t(x + w / 2, y - 3.2, wl, 1.6, 400, INK, "middle"))
    o.append(f'<line x1="{f(x - 2)}" y1="{f(y)}" x2="{f(x - 2)}" y2="{f(y + h)}" {dm}/>')
    o.append(t(x - 3, y + h / 2 + 0.6, hl, 1.6, 400, INK, "end"))
    return o


def _lines(x, y, s, width_mm, size=1.7, w=400, fill=INK):
    """wrapped text; returns (svg list, y after)."""
    o = []
    for ln in textwrap.wrap(s, max(20, int(width_mm / (size * (0.62 if w >= 600 else 0.55))))):
        o.append(t(x, y, ln, size, w, fill)); y += size * 1.45
    return o, y


def panel(x, y, w, shell, main_where, care_where, title="HAKI STUDIOS STANDARD LABELS"):
    """the Haki standard main + care label artwork at 1:1 (scaled down only if w is too narrow), dimensioned, with the
    placement text; the care label is MISSING (dashed amber box) when care_label(shell) is None. Returns (svg list, height)."""
    o = [f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="4" fill="#F5F2EC"/>',
         t(x + 1.5, y + 2.9, title, 2.0, 700, INK)]
    yy = y + 9
    mw, mh = LB.MAIN_MM; sm = min(1.0, (w - 8) / mw)
    o.append(t(x, yy, f"MAIN LABEL — {'1 : 1' if sm == 1 else f'{sm:.2f} : 1'}", 1.9, 700, GREEN)); yy += 6
    lx = x + 6
    o.append(_img(LB.render(LB.MAIN, dpi=300), lx, yy, mw * sm, mh * sm))
    o.append(f'<rect x="{f(lx)}" y="{f(yy)}" width="{f(mw * sm)}" height="{f(mh * sm)}" fill="none" stroke="#555" stroke-width="0.25"/>')
    o += _dims(lx, yy, mw * sm, mh * sm, f"{mw / 10:g} cm", f"{mh / 10:g} cm"); yy += mh * sm + 4
    s_, yy = _lines(x, yy, "White ground, black HAKI STUDIOS logo + mark. Woven, flat, sewn down on all 4 sides (black thread). " + main_where, w); o += s_
    s_, yy = _lines(x, yy, "Weave (damask) [proposed — confirm]", w, 1.7, 600, AMBER); o += s_
    yy += 3
    cw, ch = LB.CARE_MM; fb = care_fibre(shell)
    sc = min(1.0, (w - 12) / (2 * cw + 4))
    o.append(t(x, yy, f"CARE LABEL — {fb if fb else 'fibre not confirmed'} — {'1 : 1' if sc == 1 else f'{sc:.2f} : 1'}, front + back", 1.9, 700, GREEN if fb else AMBER)); yy += 6
    lx0 = x + 6
    if fb:
        path = LB.care_label(shell)
        for k, side in enumerate(("front", "back")):
            lx = lx0 + k * (cw * sc + 4)
            o.append(_img(LB.render(path, page=k + 1, dpi=300), lx, yy, cw * sc, ch * sc))
            o.append(f'<rect x="{f(lx)}" y="{f(yy)}" width="{f(cw * sc)}" height="{f(ch * sc)}" fill="none" stroke="#555" stroke-width="0.25"/>')
            o.append(t(lx + cw * sc / 2, yy + ch * sc + 3.2, side, 1.7, 600, INK, "middle"))
        o += _dims(lx0, yy, cw * sc, ch * sc, f"{cw / 10:g} cm", f"{ch / 10:g} cm"); yy += ch * sc + 6
        s_, yy = _lines(x, yy, "Printed satin ribbon, white ground; top 0.5 cm goes into the seam. " + care_where, w); o += s_
        s_, yy = _lines(x, yy, "The label prints MADE IN CHINA — tell Haki if the garment is made elsewhere.", w, 1.7, 600, AMBER); o += s_
    else:
        o.append(f'<rect x="{f(lx0)}" y="{f(yy)}" width="{f(cw * sc)}" height="{f(ch * sc)}" fill="#FFF3DC" stroke="{AMBER}" stroke-width="0.35" stroke-dasharray="1 0.6"/>')
        o.append(t(lx0 + cw * sc / 2, yy + ch * sc / 2 - 1, "[MISSING]", 2.0, 700, AMBER, "middle"))
        o.append(t(lx0 + cw * sc / 2, yy + ch * sc / 2 + 2.4, "care label", 1.6, 400, AMBER, "middle"))
        o += _dims(lx0, yy, cw * sc, ch * sc, f"{cw / 10:g} cm", f"{ch / 10:g} cm")
        tx = lx0 + cw * sc + 4; tw = x + w - tx; ty = yy + 2
        for s, wt in [(MISSING, 700), (f"Shell recorded only as '{shell}' — no fibre %.", 400),
                      ("Haki standard care labels exist for 100 % cotton and 90 % cotton / 10 % polyester only.", 400),
                      ("Haki confirms the fibre content, then sends the matching care label. Do not print a care label until then.", 600)]:
            s_, ty = _lines(tx, ty, s, tw, 1.7, wt, AMBER if wt > 400 else INK); o += s_; ty += 1
        yy += ch * sc + 4
        s_, yy = _lines(x, yy, "Size 3 × 6.5 cm, printed satin, front + back. " + care_where, w); o += s_
    yy += 1.5
    names = ", ".join(os.path.basename(p) for p in files(shell)[:2])
    s_, yy = _lines(x, yy, f"Files in the zip, labels/: {names}" + (" (+ .ai)." if fb else " (care label to follow)."), w, 1.6, 400, MUTED); o += s_
    return o, yy - y


PROP = "#8A5A00"; ALT = "#F5F2EC"
HOODIE_ROWS = [("Main label", "back neck facing, centred at CB, 1 cm below the hood seam (zip-hoodie block); flat, sewn down on all 4 sides (black thread)", False),
               ("Size label", "back neck facing, with the main label", True),
               ("Care label", "wearer's left side seam of the lining", True)]


def hoodie_page(H, shell, page="T6b", rows=HOODIE_ROWS):
    """a whole labels page for the zip-hoodie family (block, KCOS, Comet City, Red Beast, Koi): placement table, the care-label
    status in words, and the 1:1 panel. H = the pack's header(title, sub, page) function."""
    o = H("LABELS — Haki standard main + care label", "Main + care label = the Haki standard labels (founder 22 Oct 2026), artwork right at 1 : 1, files in the zip labels/. Positions on the finished garment.", page)
    y = 36; o.append(t(12, 31, "PLACEMENT", 2.2, 700))
    for i, (a, b_, p) in enumerate(rows):
        if i % 2 == 0: o.append(f'<rect x="11" y="{f(y - 3.0)}" width="180" height="4.4" fill="{ALT}"/>')
        o.append(t(12, y, a, 1.75, 700)); o.append(t(36, y, b_ + ("  [proposed — confirm]" if p else ""), 1.6, 400, PROP if p else INK)); y += 4.4
    fb = care_fibre(shell); y += 5
    o.append(t(12, y, "CARE LABEL — " + (f"Haki standard, {fb}" if fb else MISSING), 2.2, 700, GREEN if fb else AMBER)); y += 5
    for l in ([f"Shell: '{shell}'.", "Linings (flannel, taffeta, sherpa hood) and embroidery thread are not on the standard label: Haki confirms if they must be listed."] if fb else
              [f"The shell is recorded only as '{shell}' — no fibre %.",
               "Haki standard care labels exist for 100 % cotton and 90 % cotton / 10 % polyester only; the right one is picked from the fibre, never the nearest.",
               "Haki confirms the shell fibre content, then sends the matching care label artwork. Do not print a care label until then.",
               "Linings (flannel, taffeta, sherpa hood) and embroidery thread are not on the standard label: Haki confirms if they must be listed."]):
        o.append(t(12, y, l, 1.65, 400, INK)); y += 3.6
    o += panel(200, 30, 86, shell, "Position: " + rows[0][1].split(";")[0] + ".", "Position: " + rows[2][1] + " [proposed — confirm height].")[0]
    return o
