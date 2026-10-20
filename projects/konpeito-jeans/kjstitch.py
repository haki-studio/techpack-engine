"""Konpeito jeans — stitch files (DST + PES) per element, read back (LESSONS B8/B20), previews from the DST.
usage: python3 kjstitch.py [coin spill wb starY starP]"""
import sys, json, pickle, math, os
import numpy as np
import kjcore
dst2 = kjcore.patch_dst2()
import pyembroidery as pe
import readback, factory, motifs2
from PIL import Image, ImageDraw
from shapely.ops import unary_union

FILES = {   # element -> (file stem, stop plan [(colour, region codes)])
    "coin":  ("HAKI_KJ_01_coin-pocket-patch", [("kj_red", {"BAND"}), ("kj_cream", {"FIELD"}), ("kj_white", {"BFL", "BDOT"}),
              ("kj_pink", {"KP"}), ("kj_pink_hi", {"KP-hi"}), ("kj_yellow", {"KP"}), ("kj_yellow_hi", {"KP-hi"}),
              ("kj_blue", {"KP"}), ("kj_blue_hi", {"KP-hi"}), ("kj_white", {"KNOT"}), ("kj_red", {"TXC", "DOT"}), ("kj_red", {"EDGE"})]),
    "spill": ("HAKI_KJ_02_coin-spill-facing", [("kj_pink", {"KPB"}), ("kj_pink_hi", {"KPB-hi"}),
              ("kj_yellow", {"KP"}), ("kj_yellow_hi", {"KP-hi"}), ("kj_blue", {"KP"}), ("kj_blue_hi", {"KP-hi"}),
              ("kj_pink", {"KP"}), ("kj_pink_hi", {"KP-hi"}), ("kj_white", {"KNOT"})]),
    "wb":    ("HAKI_KJ_03_waistband-patch", [("kj_red", {"BAND"}), ("kj_cream", {"FIELD"}), ("kj_white", {"BFL", "BDOT"}),
              ("kj_pink", {"FL", "TXC"}), ("kj_yellow", {"FL"}), ("kj_blue", {"FL", "TXC"}), ("kj_white", {"KNOT"}),
              ("kj_rose", {"DOT"}), ("kj_black", {"TXC", "LINE"}), ("kj_red", {"TXC", "DOT"}), ("kj_red", {"EDGE"})]),
    "haki":  ("HAKI_KJ_04_back-pocket-L-haki", [("kj_yellow", {"STAR"}), ("kj_yellow_hi", {"STAR-hi"}), ("kj_blue_hi", {"TXC"}),
              ("kj_pink", {"STAR"}), ("kj_pink_hi", {"STAR-hi"})]),
    "starY": ("HAKI_KJ_06_back-pocket-L-lower-star-yellow", [("kj_yellow", {"STAR"}), ("kj_yellow_hi", {"STAR-hi"})]),
    "starP": ("HAKI_KJ_05_back-pocket-R-star-pink", [("kj_pink", {"STAR"}), ("kj_pink_hi", {"STAR-hi"})]),
}
_FRONT_PLAN = [("kj_yellow", {"STAR"}), ("kj_yellow_hi", {"STAR-hi"}), ("kj_pink", {"STAR"}), ("kj_pink_hi", {"STAR-hi"}),
               ("kj_blue", {"STAR"}), ("kj_blue_hi", {"STAR-hi"})]
FILES["front1"] = ("HAKI_KJ_07a_front-leg-stars-upper_PROPOSED", _FRONT_PLAN)
FILES["front2"] = ("HAKI_KJ_07b_front-leg-stars-lower_PROPOSED", _FRONT_PLAN)
OUT = "out/stitch"

def stops_for(vis, plan):
    used = set(); stops = []
    for col, codes in plan:
        rs = [r for i, r in enumerate(vis) if i not in used and r["col"] == col and r["grp"] in codes]
        used |= {i for i, r in enumerate(vis) if r["col"] == col and r["grp"] in codes}
        if rs: stops.append(dict(col=col, regions=rs))
    left = [r for i, r in enumerate(vis) if i not in used]
    if left: raise ValueError(f"regions not in any stop: {sorted({(r['col'], r['grp']) for r in left})}")
    return stops

def dst_layers(path, ppm=20, w_mm=0.38, pad=2.0):
    """per-thread raster of the sewn stitches (DST read-back) in design mm; returns (img RGB, {hex: mask}, origin mm)."""
    p = pe.read(path); ex = p.extents()
    x0, y0 = ex[0] / 10 - pad, ex[1] / 10 - pad
    Wp, Hp = int((ex[2] - ex[0]) / 10 * ppm + 2 * pad * ppm), int((ex[3] - ex[1]) / 10 * ppm + 2 * pad * ppm)
    cols = [t.hex_color() for t in pe.read(path[:-4] + ".pes").threadlist]
    layers = {}; ci = 0; prev = None; seq = []
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK; P = ((x / 10 - x0) * ppm, (y / 10 - y0) * ppm)
        if k == pe.STITCH:
            if prev is not None: seq.append((ci, prev, P))
            prev = P
        elif k == pe.COLOR_CHANGE: ci += 1; prev = None
        elif k in (pe.TRIM, pe.JUMP): prev = None if k == pe.TRIM else P
        elif k == pe.END: break
    return seq, cols, (x0, y0), (Wp, Hp)

def render_dst(path, png, ppm=20, bg=(52, 52, 56)):
    seq, cols, org, (Wp, Hp) = dst_layers(path, ppm)
    im = Image.new("RGB", (Wp, Hp), bg); d = ImageDraw.Draw(im)
    w = max(2, int(round(0.42 * ppm)))       # 40wt thread lies ~0.4 mm wide
    thin = {i for i, c in enumerate(cols) if c.upper() in ("#1C1A1A", "#34A5D6")}      # 60wt threads lie thinner
    for ci, a, b in seq:          # thread drawn in sew order: dark rim then the thread colour, so later stitches sit on top
        c = cols[min(ci, len(cols) - 1)]
        rgb = tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
        ww = max(2, int(w * 0.72)) if ci in thin else w
        d.line([a, b], fill=c, width=ww)          # thread colour, round ends (thread wraps round the needle hole)
        r_ = ww / 2
        for q in (a, b): d.ellipse([q[0] - r_, q[1] - r_, q[0] + r_, q[1] + r_], fill=c)
        d.line([a, b], fill=tuple(max(0, int(v * 0.80)) for v in rgb), width=1)    # thin shade line: stitch direction
    im.save(png); return org

def colour_masks(path, ppm=20):
    """{hex: bool mask} of the area each thread covers (stitch lines drawn 0.45 mm wide, last colour on top)."""
    seq, cols, org, (Wp, Hp) = dst_layers(path, ppm)
    top = np.full((Hp, Wp), -1, np.int16)
    for ci in range(len(cols)):
        im = Image.new("L", (Wp, Hp), 0); d = ImageDraw.Draw(im)
        for c_, a, b in seq:
            if c_ == ci: d.line([a, b], fill=255, width=max(1, int(0.45 * ppm)))
        m = np.array(im) > 0
        top[m] = ci
    masks = {}
    for ci, c in enumerate(cols):
        masks[c] = masks.get(c, np.zeros((Hp, Wp), bool)) | (top == ci)
    return masks, org

def trim_exposed(pat, stats, stops, origin, halo=0.3, max_ex=0.5):
    """fix pass: a travel run that would lie > max_ex mm on bare fabric (outside its own stop's art + halo and outside
    everything sewn later) is replaced by TRIM + JUMP. The router's raster hides travel under narrow, not-yet-sewn
    satin columns it can overshoot (seen on the face line art and between glyphs)."""
    import pyembroidery as pe
    from shapely.geometry import LineString
    geo = [unary_union([r["geom"] for r in s["regions"]]) for s in stops]
    cover = [unary_union([geo[i].buffer(halo)] + geo[i + 1:]) for i in range(len(geo))]
    ox, oy = origin; S = pat.stitches; pos = 0; n = 0
    def key(p): return ((p[0] - ox) * 10.0, (p[1] - oy) * 10.0)
    for si, pts in stats["runs"]:
        if len(pts) < 2: continue
        if LineString(pts).difference(cover[si]).length <= max_ex: continue
        body = pts[1:-1] if len(pts) > 2 else []
        target = key(pts[-1])
        # find the travel stitches (pts[1:-1]) followed by the block start (pts[-1]) from pos on
        seqk = [key(p) for p in body] + [target]
        j = pos
        while j < len(S):
            ok = all(j + t < len(S) and (S[j + t][2] & pe.COMMAND_MASK) == pe.STITCH and abs(S[j + t][0] - seqk[t][0]) < 1e-6
                     and abs(S[j + t][1] - seqk[t][1]) < 1e-6 for t in range(len(seqk)))
            if ok: break
            j += 1
        if j >= len(S): continue
        for t in range(len(body)): S[j + t][2] = pe.JUMP
        S.insert(j + len(body), [seqk[-1][0], seqk[-1][1], pe.JUMP])      # land ON the block start, then sew
        S.insert(j, [S[j - 1][0], S[j - 1][1], pe.TRIM])
        pos = j + len(seqk) + 2; n += 1
    # every sewn segment: > 0.3 mm on bare fabric (short direct moves between close objects never enter stats["runs"])
    from shapely.prepared import prep
    P = [prep(c) for c in cover]; ci = 0; i = 1; prev = None
    while i < len(S):
        cmd = S[i][2] & pe.COMMAND_MASK; pc = S[i - 1][2] & pe.COMMAND_MASK
        if cmd == pe.COLOR_CHANGE: ci += 1
        if cmd == pe.STITCH and pc == pe.STITCH and ci < len(cover):
            a = (S[i - 1][0] / 10.0 + ox, S[i - 1][1] / 10.0 + oy); b = (S[i][0] / 10.0 + ox, S[i][1] / 10.0 + oy)
            if math.dist(a, b) > 0.5:
                ls = LineString([a, b])
                if not P[ci].contains(ls) and ls.difference(cover[ci]).length > 0.3:
                    S.insert(i, [S[i - 1][0], S[i - 1][1], pe.TRIM]); S.insert(i + 1, [S[i + 1][0], S[i + 1][1], pe.JUMP])
                    n += 1; i += 3; continue
        i += 1
    return n

def build(name):
    A = pickle.load(open("out/art.pkl", "rb"))
    stem, plan = FILES[name]
    if name.startswith("front"):
        import kjfront
        F = json.load(open("out/front_stars.json")); byid = {d["id"]: d for d in F["stars"]}
        vis = kjfront.section_vis([byid[i] for i in F["sections"][int(name[-1]) - 1]])
    else:
        vis = A[name]["vis"]
    vis = [r for r in vis if not r["geom"].is_empty]
    stops = stops_for(vis, plan)
    b = dst2.bounds_of([r["geom"] for r in vis])
    origin = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
    pat, stats = dst2.make_pattern(vis, stops, origin)
    stats["trimmed_exposed"] = trim_exposed(pat, stats, stops, origin)
    os.makedirs(OUT, exist_ok=True); base = f"{OUT}/{stem}"
    dst2.write(pat, base)
    rb = readback.dst(base + ".dst"); vf = dst2.verify(base)
    nthr = factory.check_threads(base + ".pes")
    prof = factory.load()
    hrs = factory.machine_hours(rb["stitches"], prof, trims=rb["trims"], colour_changes=rb["stops"] - 1)
    ex = sorted(dst2.exposed_travel(stops, stats["runs"]))
    res = dict(element=name, file=stem, stitches=rb["stitches"], trims=rb["trims"], jumps=rb["jumps"], stops=rb["stops"],
               threads=nthr, max_stitch=rb["max_stitch"], size_mm=rb["size_mm"], origin_mm=[round(v, 2) for v in origin],
               machine_min=round(hrs * 60, 1), per_stop=[dict(s, col=stops[i]["col"] if i < len(stops) else None,
                                                             codes=sorted({r["grp"] for r in stops[i]["regions"]}) if i < len(stops) else [])
                                                        for i, s in enumerate(rb["per_stop"])],
               exposed_runs_gt1mm=sum(1 for v in ex if v > 1.0), max_exposed=round(ex[-1], 2) if ex else 0.0,
               trims_by=stats.get("by", {}), travel_trimmed=stats.get("trimmed_exposed", 0))
    assert rb["max_stitch"] <= 7.5, f"{stem}: max stitch {rb['max_stitch']}"
    render_dst(base + ".dst", f"{OUT}/{stem}_preview.png")
    json.dump(res, open(f"{OUT}/{stem}.json", "w"), indent=1)
    print(f"{stem}: {rb['stitches']:,} st, {rb['trims']} trims, {rb['stops']} stops, {nthr} threads, max {rb['max_stitch']} mm, "
          f"{rb['size_mm']} mm, {res['machine_min']} min")
    return res

if __name__ == "__main__":
    for n in (sys.argv[1:] or list(FILES)): build(n)
