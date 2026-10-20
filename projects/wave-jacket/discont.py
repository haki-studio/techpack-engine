"""INTERNAL-DISCONTINUITY CHECK (coordinator, 19 Oct 2026): a seam treatment must not leave a cut line INSIDE a panel.
For every seam the wave crosses (and the sleeve centre line), each side is rendered from its DST (every sewn stitch in its
thread colour), unrolled along the seam (rows = depth from the seam, 0-140 mm) and classed per pixel to the thread groups
(fabric / 6 blues / creams + grey), majority-filtered over 1 mm. Probe lines run parallel to the seam at 8, 15, 25, 40, 60,
80, 100 and 120 mm (the old continuation-band cuts sat at 10-60 mm, the old stretch boundary at 60 mm, the warp fades out
at ~100 mm). At each probe every tone edge that crosses it is followed from 9 mm before the probe to 3 mm before it and
extrapolated straight to 3 mm past it: the distance to the same edge found there is the JUMP. A cut line shows as many
edges jumping (or ending) on one probe. Rule: no edge may jump > 1 mm except where the art itself ends / turns (reported
as the share of edges jumping > 1 mm per probe; a probe with > 8 % of its edges jumping > 1 mm is flagged).
usage: ./py.sh discont.py [--before DIR] [--art]  ->  discont_M[_before].json + out/discont_<seam>.png crops"""
import wavecore as WC
import sys, json, os, pickle
import numpy as np
from scipy import ndimage as ndi
from PIL import Image, ImageDraw
import pyembroidery as pe
import wrap as WR, pieces as PC, seamfill as SF

SIZE = "M"; PPM = 4.0; DEPTH = 140.0; PROBES = [8, 15, 25, 40, 60, 80, 100, 120]
BEFORE = sys.argv[sys.argv.index("--before") + 1] if "--before" in sys.argv else None
ART = "--art" in sys.argv
TAG = "_before" if BEFORE else ("_art" if ART else "")
GROUP = {"w1": 7, "w3": 7, "g1": 7, "b0": 1, "b1": 2, "b2": 3, "b3": 4, "b4": 5, "b5": 6, "w1e": 7}

_IMG = {}
def piece_lab(P):
    """class image (0 fabric, 1-6 blues, 7 cream) of piece P in pattern coords, + bbox"""
    if P in _IMG: return _IMG[P]
    b = PC.panel(SIZE, P).bounds; bb = (b[0] - 5, b[1] - 5, b[2] + 5, b[3] + 5)
    W, H = int((bb[2] - bb[0]) * PPM), int((bb[3] - bb[1]) * PPM)
    im = Image.new("L", (W, H), 0); d = ImageDraw.Draw(im)
    if ART:
        D = pickle.load(open(f"art_{SIZE}.pkl", "rb"))
        for r in sorted(D[P], key=lambda r: r.get("layer", 0)):
            if r["grp"] in ("FM-loop", "FM-curl"): continue
            for q in WR.polys_of(r["geom"]):
                d.polygon([((x - bb[0]) * PPM, (y - bb[1]) * PPM) for x, y in q.exterior.coords], fill=GROUP[r["col"]])
                for h in q.interiors: d.polygon([((x - bb[0]) * PPM, (y - bb[1]) * PPM) for x, y in h.coords], fill=0)
    else:
        root = BEFORE or f"out/01_wave/{SIZE}"
        r = json.load(open(f"{root}/result_{P}.json"))["full"]
        f_ = os.path.join(root, os.path.basename(r["file"]) + ".dst")
        p = pe.read(f_); cols = [s["col"] for s in r["per_stop"]]; ox, oy = r["origin"]; ci = 0; prev = None
        lw = max(1, int(round(0.45 * PPM)))
        for x, y, cmd in p.stitches:
            k = cmd & pe.COMMAND_MASK; q = ((x / 10 + ox - bb[0]) * PPM, (y / 10 + oy - bb[1]) * PPM)
            if k == pe.STITCH:
                if prev is not None: d.line([prev, q], fill=GROUP.get(cols[min(ci, len(cols) - 1)], 7), width=lw)
                prev = q
            elif k == pe.COLOR_CHANGE: ci += 1; prev = None
            else: prev = None
        if r.get("chenille"):
            import live
            rec = dict(r["chenille"]); rec["file"] = os.path.join(root, os.path.basename(rec["file"]))
            live.draw_chenille(im, rec, bb, PPM, flat={"w1": 7, "w3": 7, "w1e": 7})
    a = np.asarray(im).astype(np.int32)
    # majority over 1 mm (stitch-line texture -> regions); fabric only where nothing is sewn within 0.5 mm
    oh = np.stack([ndi.uniform_filter((a == k).astype(np.float32), 5) for k in range(8)], -1)
    lab = oh.argmax(-1); lab = np.where(ndi.binary_dilation(a > 0, iterations=2), np.where(lab == 0, oh[..., 1:].argmax(-1) + 1, lab), 0)
    _IMG[P] = (lab, bb); return _IMG[P]

def unroll(side):
    from scipy.ndimage import map_coordinates
    lab, bb = piece_lab(side.P); un = SF.Unroll(side, int(round(side.L * PPM)))
    ds = np.arange(WR.GAP if side.seam["kind"] != "internal" else 0.0, DEPTH, 1.0 / PPM)
    X = un.base[None, :, 0] + ds[:, None] * un.nrm[None, :, 0]; Y = un.base[None, :, 1] + ds[:, None] * un.nrm[None, :, 1]
    out = map_coordinates(lab, [(Y - bb[1]) * PPM, (X - bb[0]) * PPM], order=0, mode="constant", cval=0)
    import shapely
    inside = shapely.contains_xy(side.region.buffer(-0.5), X, Y)
    return np.where(inside, out, -1), ds

def edges(row):
    """[(x, left, right)] tone transitions along a row (ignores outside-the-piece -1)"""
    out = []
    for i in range(len(row) - 1):
        a, b = row[i], row[i + 1]
        if a != b and a >= 0 and b >= 0: out.append((i + 0.5, a, b))
    return out

def track(U, ds, x_start, pair, mm_from, mm_to, step_mm=1.0, tol_mm=1.6):
    """follow one tone edge (pair = (left, right) class) row by row from depth mm_from to mm_to; returns [(depth, x)]"""
    k = lambda mm: int(round((mm - ds[0]) * PPM))
    pts = []; x = x_start; sgn = 1 if mm_to > mm_from else -1
    for mm in np.arange(mm_from, mm_to + sgn * 1e-6, sgn * step_mm):
        r = k(mm)
        if r < 0 or r >= U.shape[0]: break
        c = [e[0] for e in edges(U[r]) if (e[1], e[2]) == pair and abs(e[0] - x) <= tol_mm * PPM]
        if not c: break
        x = min(c, key=lambda v: abs(v - x)); pts.append((mm, x))
    return pts

def probe(U, ds, dmm):
    """STRIPE edges crossing the probe line at depth dmm: a line fitted to the edge over 1.5-9 mm on the seam side and
    another over 1.5-9 mm on the far side, both evaluated ON the probe: jump = their distance (mm). Curved edges give
    ~0 (two short fits meet), a cut line gives the offset of the cut."""
    k = lambda mm: int(round((mm - ds[0]) * PPM))
    if k(dmm - 9) < 0 or k(dmm + 9) >= U.shape[0]: return None
    out = []
    for x1, a, b in edges(U[k(dmm - 1.5)]):
        if not ((1 <= a <= 6) or (1 <= b <= 6)) or a == 7 or b == 7: continue       # stripe edges only (blue | blue, blue | fabric)
        P1 = track(U, ds, x1, (a, b), dmm - 1.5, dmm - 9)
        if len(P1) < 5: continue
        d1, x_ = np.array(P1).T; m1, c1 = np.polyfit(d1, x_, 1); pred = m1 * (dmm + 1.5) + c1
        c = [e[0] for e in edges(U[k(dmm + 1.5)]) if (e[1], e[2]) == (a, b) and abs(e[0] - pred) <= 4 * PPM]
        if not c: out.append((x1, None)); continue
        P2 = track(U, ds, min(c, key=lambda v: abs(v - pred)), (a, b), dmm + 1.5, dmm + 9)
        if len(P2) < 5: out.append((x1, None)); continue
        d2, x2 = np.array(P2).T; m2, c2 = np.polyfit(d2, x2, 1)
        out.append((x1, abs((m1 * dmm + c1) - (m2 * dmm + c2)) / PPM))
    return out

CUT_MM = 12.0
def straight_cuts(U, ds):
    """straight tone edges along the unrolled grid: a boundary that runs EXACTLY parallel to the seam (constant depth) or
    exactly across it (constant position) for >= CUT_MM, with the same two tones on its sides (1 px wobble allowed). Traced
    art never does that over 12 mm; a pasted band / cut / row-stretch step does. Returns [(kind, depth mm, s0 mm, s1 mm)]"""
    out = []
    V = U >= 0
    for axis in (0, 1):
        A = U if axis == 0 else U.T
        Vv = V if axis == 0 else V.T
        ch = (A[:-1] != A[1:]) & Vv[:-1] & Vv[1:] & ((A[:-1] > 0) | (A[1:] > 0))
        pair = A[:-1] * 16 + A[1:]
        L = int(CUT_MM * PPM)
        for r in range(1, ch.shape[0] - 1):
            row = ch[r - 1] | ch[r] | ch[r + 1]
            if row.sum() < L: continue
            pr = np.where(ch[r], pair[r], np.where(ch[r - 1], pair[r - 1], pair[r + 1]))
            c = 0; start = 0
            for j in range(row.shape[0] + 1):
                ok = j < row.shape[0] and row[j] and (c == 0 or pr[j] == pr[j - 1])
                if ok:
                    if c == 0: start = j
                    c += 1
                else:
                    if c >= L:
                        if axis == 0: out.append(("parallel", round(float(ds[0] + r / PPM), 1), round(start / PPM, 1), round((start + c) / PPM, 1)))
                        else: out.append(("across", round(start / PPM + float(ds[0]), 1), round(r / PPM, 1), round(r / PPM, 1)))
                    c = 1 if (j < row.shape[0] and row[j]) else 0; start = j
    # one entry per line (neighbouring rows of the same line merged)
    out.sort(); mg = []
    for o in out:
        if mg and o[0] == mg[-1][0] and abs(o[1] - mg[-1][1]) <= 0.6 and abs(o[2] - mg[-1][2]) < 3: continue
        mg.append(o)
    return mg

def run():
    res = {}; sheets = []
    for sm in WR.seams(SIZE):
        if sm["kind"] == "zip": continue
        for which in ("A", "B"):
            side = WR.SeamSide(SIZE, sm, which); U, ds = unroll(side); rows = {}
            for dmm in PROBES:
                J = probe(U, ds, dmm)
                if J is None: continue
                vals = [j for x, j in J if j is not None]; lost = sum(1 for x, j in J if j is None)
                big = [x for x, j in J if j is not None and j > 1.0]
                rows[dmm] = dict(edges=len(J), jump_gt1=len(big), lost=lost, share_gt1=round(100 * len(big) / max(1, len(J)), 1),
                                 p95=round(float(np.percentile(vals, 95)), 2) if vals else 0.0, flag=bool(len(J) >= 10 and len(big) / len(J) > 0.08),
                                 at_mm=[round(x / PPM, 1) for x in big][:40])
            cuts = [c for c in straight_cuts(U, ds) if c[1] > (WR.GAP + 1.0 if sm["kind"] != "internal" else 1.0)]
            rows["straight_cuts"] = dict(n=len(cuts), lines=cuts[:30])
            res[f"{sm['name']} {which} ({side.P})"] = rows
            sheets.append((sm, which, side, U, ds, rows))
    json.dump(res, open(f"discont_{SIZE}{TAG}.json", "w"), indent=1)
    # crops: the side with the most flagged / jumping edges of every seam, probes drawn, jumps > 1 mm in red
    pal = np.array([[39, 47, 67], [177, 199, 216], [128, 174, 208], [82, 141, 190], [31, 101, 168], [5, 66, 153], [3, 40, 112], [240, 237, 234]], np.uint8)
    for sm, which, side, U, ds, rows in sheets:
        img = pal[np.clip(U, 0, 7)]; img[U < 0] = 255
        im = Image.fromarray(img[::-1]).convert("RGB"); d = ImageDraw.Draw(im); H = im.height
        for c in rows["straight_cuts"]["lines"]:
            if c[0] == "parallel":
                y = H - 1 - int(round((c[1] - ds[0]) * PPM)); d.line([(c[2] * PPM, y), (c[3] * PPM, y)], fill=(255, 0, 255), width=3)
            else:
                x = c[2] * PPM; y0 = H - 1 - int(round((c[1] - ds[0]) * PPM)); d.line([(x, y0), (x, y0 - CUT_MM * PPM)], fill=(255, 0, 255), width=3)
        for dmm, r in rows.items():
            if dmm == "straight_cuts": continue
            y = H - 1 - int(round((dmm - ds[0]) * PPM)); d.line([(0, y), (im.width, y)], fill=(255, 200, 0) if not r["flag"] else (255, 0, 0), width=1)
            for x in r["at_mm"]: d.ellipse([x * PPM - 4, y - 4, x * PPM + 4, y + 4], outline=(255, 0, 0), width=2)
            d.text((4, y - 11), f"{dmm} mm: {r['jump_gt1']}/{r['edges']} edges jump > 1 mm", fill=(255, 255, 0))
        hdr = Image.new("RGB", (im.width, 22), "white"); ImageDraw.Draw(hdr).text((4, 4), f"{sm['name']} - side {which} ({side.P}), {'DST before (seamfill band)' if BEFORE else ('art' if ART else 'shipped DST')}: unrolled 0-140 mm from the seam (seam at the bottom); probe lines + edge jumps > 1 mm (red)", fill=(0, 0, 0))
        o = Image.new("RGB", (im.width, im.height + 22), "white"); o.paste(hdr, (0, 0)); o.paste(im, (0, 22))
        o.save(f"out/discont_{sm['name'].replace(' ', '_')}_{which}{TAG}.png")
    tot = sum(r["jump_gt1"] for v in res.values() for d, r in v.items() if d != "straight_cuts"); n = sum(r["edges"] for v in res.values() for d, r in v.items() if d != "straight_cuts")
    fl = [(k, d) for k, v in res.items() for d, r in v.items() if d != "straight_cuts" and r["flag"]]
    sc = {k: v["straight_cuts"]["n"] for k, v in res.items() if v["straight_cuts"]["n"]}
    print("straight cut lines (>= 12 mm) per seam side:", sc, "total", sum(sc.values()))
    print(f"edges probed {n}, jumping > 1 mm {tot} ({100 * tot / max(1, n):.1f} %), flagged probes {len(fl)}: {fl[:12]}")
    return res

if __name__ == "__main__":
    run()
