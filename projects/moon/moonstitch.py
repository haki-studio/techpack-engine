"""Shared stitch-file helpers for the moon jacket (wraps engine/dst2.py): stops, pattern, write + verify + preview,
the licensed-figure PLACEHOLDER basting stop, trims counted from the DST read-back (LESSONS B8)."""
import collections, json, os
import pyembroidery as pe
from shapely.ops import unary_union
from shapely.geometry import box
import moonpal
import dst2, tech
moonpal.patch_dst2()
U = dst2.U
PH_HEX = "#FF2D9B"      # on-page marking colour only (the file sews the outline in moon cream, see moonpal.PH_COL)
PH_LABEL = "PLACEHOLDER licensed figure area - outline run in Moon cream (covered by 01b moon-in-box); licensed insert sews here"

def stops_for(vis):
    st = tech.stops(vis); n0 = len(st); return dst2.merge_stops(st), n0

def add_placeholder(pat, bx, origin):
    """append a basting stop that outlines the placeholder box (run 3 mm), before END."""
    ox, oy = origin
    while pat.stitches and (pat.stitches[-1][2] & pe.COMMAND_MASK) in (pe.END, pe.TRIM): pat.stitches.pop()
    pat.add_command(pe.TRIM); pat.add_command(pe.COLOR_CHANGE)
    th = pe.EmbThread(); th.set_hex_color(moonpal.HEXK(moonpal.PH_COL)); th.description = PH_LABEL; th.catalog_number = "PH"; pat.add_thread(th)
    if len(bx) == 4 and not isinstance(bx[0], (list, tuple)):
        x0, y0, x1, y1 = bx; i_ = 1.5     # 1.5 mm inside the box edge: the 01b moon-in-box fill covers it
        x0, y0, x1, y1 = x0 + i_, y0 + i_, x1 - i_, y1 - i_; paths = [[(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]]
    else:
        paths = bx                      # part of the outline (box split across hoopings)
    for k, ring in enumerate(paths):
        if k: pat.add_command(pe.TRIM)
        pat.add_stitch_absolute(pe.JUMP, (ring[0][0] - ox) * U, (ring[0][1] - oy) * U)
        for x, y in dst2.path_resample(ring, 3.0, tol=0): pat.add_stitch_absolute(pe.STITCH, (x - ox) * U, (y - oy) * U)
    pat.add_command(pe.TRIM); pat.add_command(pe.END)

def ph_bounds(ph):
    if len(ph) == 4 and not isinstance(ph[0], (list, tuple)): return ph
    xs = [p[0] for r in ph for p in r]; ys = [p[1] for r in ph for p in r]; return (min(xs), min(ys), max(xs), max(ys))

def dst_trims(base):
    p = pe.read(base + ".dst"); return collections.Counter(s[2] & pe.COMMAND_MASK for s in p.stitches)[pe.TRIM]

def thread_count(base):
    return len(pe.read(base + ".pes").threadlist)

def make(vis, base, scale_preview=0.5, placeholder=None, reg_marks=None, origin=None):
    """vis -> DST + PES + preview. Returns result dict (counts from the files)."""
    stops, n0 = stops_for(vis)
    ub = unary_union([r["geom"] for r in vis]).bounds
    if placeholder is not None:
        pb = ph_bounds(placeholder); ub = (min(ub[0], pb[0]), min(ub[1], pb[1]), max(ub[2], pb[2]), max(ub[3], pb[3]))
    c = origin or ((ub[0] + ub[2]) / 2, (ub[1] + ub[3]) / 2)
    pat, st = dst2.make_pattern(vis, stops, c, reg_marks=reg_marks)
    if reg_marks:            # registration crosses in a thread the file already uses (12-colour limit): wire grey, pick out after
        t0 = pat.threadlist[0]; t0.set_hex_color(moonpal.HEXK(moonpal.REG_COL)); t0.description = "REGISTRATION crosses - Pole grey run, pick out after the last hooping"
    if placeholder is not None: add_placeholder(pat, placeholder, c)
    os.makedirs(os.path.dirname(base), exist_ok=True)
    dst2.write(pat, base); v = dst2.verify(base)
    import factory; factory.check_threads(base + ".pes")
    dst2.render(base, base + "_preview.png", bg=(37, 48, 77), s=scale_preview)
    pt = pe.read(base + ".pes")
    lines = [os.path.basename(base), "stop  thread", "-" * 60] + [f"{i:>3}   {t.hex_color()}  {t.description}" for i, t in enumerate(pt.threadlist, 1)]
    open(base + "_thread-chart.txt", "w").write("\n".join(lines) + "\n")
    return dict(v, trims_cmd=st["trims"], trims_dst=dst_trims(base), travel=st["travel"], stops=len(stops) + (1 if placeholder else 0) + (1 if reg_marks else 0),
                stops_before_merge=n0, threads=len({t.hex_color() for t in pt.threadlist}), centre=c, art_box=ub, file=base,
                worst=sorted(st.get("by", {}).items(), key=lambda kv: -kv[1])[:8])
