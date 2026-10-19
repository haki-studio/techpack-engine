"""Per-seam continuity sheets: both sides of every seam the wave crosses, unrolled along the seam and butted together
(side A above, side B below, the 2 x 3 mm seam gap closed up as it is when sewn), rendered from the SHIPPED DSTs (or from
the art with --art for quick iteration). Match marks are drawn as red ticks on both strips.
Per seam it also MEASURES the continuity (continuity_<size>.json, table on the sheet): along the seam, 1 mm columns where
either side carries art 1-3 mm from its stitch edge; 'meet' = share of those where the other side also carries art within +/-2 mm along the seam, 'tone' = share
where the other side carries the SAME thread group within +/-4 mm (the 6 blues are compared as light b0-b2 / dark b3-b5, creams + grey as foam).
usage: ./py.sh continuity.py [M] [--art]   ->  out/continuity_<seam>.png + out/continuity_<size>[_art].png + json"""
import wavecore as WC
import sys, json, pickle
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import map_coordinates
import wrap as WR, pieces as PC

size = next((a for a in sys.argv[1:] if not a.startswith("-")), "M")
ART = "--art" in sys.argv
PPM = 4.0; DEPTH = 45.0          # mm of each piece shown away from the seam

_IMG = {}
def piece_img(P, art=None):
    """(array HxWx3, bbox) of one piece in its own pattern coords"""
    if P not in _IMG:
        b = PC.panel(size, P).bounds; bb = (b[0] - 5, b[1] - 5, b[2] + 5, b[3] + 5)
        if ART:
            from motifs2 import HEX
            D = art or pickle.load(open(f"art_{size}.pkl", "rb"))
            im = Image.new("RGB", (int((bb[2]-bb[0])*PPM), int((bb[3]-bb[1])*PPM)), WC.FABRIC); dr = ImageDraw.Draw(im)
            for r in sorted(D[P], key=lambda r: r.get("layer", 0)):
                for q in WR.polys_of(r["geom"]):
                    dr.polygon([((x-bb[0])*PPM, (y-bb[1])*PPM) for x, y in q.exterior.coords], fill=HEX[r["col"]])
                    for h in q.interiors: dr.polygon([((x-bb[0])*PPM, (y-bb[1])*PPM) for x, y in h.coords], fill=WC.FABRIC)
        else:
            import compare as C
            im = C.dst_render(P, bb, PPM)
        _IMG[P] = (np.asarray(im.convert("RGB")).astype(float), bb)
    return _IMG[P]

def d0_of(sm): return {"internal": 0.0, "zip": 15.0}.get(sm["kind"], WR.GAP)

def strip(side, flip, d0):
    """unrolled band of one side: rows = distance from the seam line (d0 .. d0+DEPTH), cols = arc length along the seam"""
    import seamfill as SF
    a, bb = piece_img(side.P); L = side.L
    un = SF.Unroll(side, int(round(L * PPM))); ds = np.arange(d0, d0 + DEPTH, 1.0 / PPM)
    X = un.base[None, :, 0] + ds[:, None] * un.nrm[None, :, 0]; Y = un.base[None, :, 1] + ds[:, None] * un.nrm[None, :, 1]
    cx = (X - bb[0]) * PPM; cy = (Y - bb[1]) * PPM
    out = np.stack([map_coordinates(a[..., k], [cy, cx], order=0, mode="nearest") for k in range(3)], -1)
    if flip: out = out[::-1]
    return out.clip(0, 255).astype(np.uint8)

# ---------------------------------------------------------------- measured continuity
def _classes():
    from motifs2 import HEX
    keys = list(WC.WV_PAL); cols = [tuple(int(HEX[k][i:i+2], 16) for i in (1, 3, 5)) for k in keys]
    fab = tuple(int(WC.FABRIC[i:i+2], 16) for i in (1, 3, 5))
    group = {"w1": "foam", "w3": "foam", "g1": "foam", "b0": "light", "b1": "light", "b2": "light", "b3": "dark", "b4": "dark", "b5": "dark"}
    return keys, np.array(cols + [fab], float), group
def classify(rows):
    keys, C, group = _classes()
    d = ((rows[..., None, :].astype(float) - C[None, None]) ** 2).sum(-1); k = d.argmin(-1)
    lab = np.array([group[x] for x in keys] + [None], object)[k]
    # majority over the rows (1-3 mm band), per column
    out = []
    for j in range(lab.shape[1]):
        v = [x for x in lab[:, j] if x is not None]
        out.append(max(set(v), key=v.count) if len(v) * 2 > lab.shape[0] else None)
    return out

def stats(la, lb):
    """columns are 1/PPM mm; resampled to 1 mm"""
    n = min(len(la), len(lb)); idx = np.arange(0, n, int(PPM))
    a = [la[i] for i in idx]; b = [lb[i] for i in idx]
    any_ = [(x, y) for x, y in zip(a, b) if x is not None or y is not None]
    if not any_: return dict(art_mm=0, meet=None, tone=None)
    # tolerance along the seam: a slanted stripe that continues straight is offset by 2 x depth x slope between the two
    # sampled rows (+ the +/-2 mm placement tolerance): meet within +/-2 mm, same tone within +/-4 mm
    def near(lst, i, v, w):
        seg = lst[max(0, i - w):i + w + 1]
        return any(x is not None for x in seg) if v == "any" else v in seg
    n_ = len(a); pairs = [(i, x, y) for i, (x, y) in enumerate(zip(a, b)) if x is not None or y is not None]
    meet = np.mean([(x is None or near(b, i, "any", 2)) and (y is None or near(a, i, "any", 2)) for i, x, y in pairs])
    tone = np.mean([(x is None or near(b, i, x, 4)) and (y is None or near(a, i, y, 4)) for i, x, y in pairs])
    return dict(art_mm=len(any_), meet=round(100 * float(meet)), tone=round(100 * float(tone)))

def sheet(sm, marks):
    A, B = WR.SeamSide(size, sm, "A"), WR.SeamSide(size, sm, "B"); d0 = d0_of(sm)
    sa, sb = strip(A, True, d0), strip(B, False, d0)
    # B is resampled to A's length (the seam is eased: same fraction s = same point when sewn)
    sbr = np.asarray(Image.fromarray(sb).resize((sa.shape[1], sb.shape[0]), Image.NEAREST))
    k0, k1 = int(1.0 * PPM), int(3.0 * PPM)
    st = stats(classify(sa[::-1][k0:k1]), classify(sbr[k0:k1]))
    im = Image.new("RGB", (sa.shape[1] + 20, sa.shape[0] + sbr.shape[0] + 60), "white")
    im.paste(Image.fromarray(sa), (10, 30)); im.paste(Image.fromarray(sbr), (10, 30 + sa.shape[0] + 2))
    d = ImageDraw.Draw(im); y0 = 30 + sa.shape[0]
    d.line([(10, y0 + 1), (10 + sa.shape[1], y0 + 1)], fill=(255, 255, 255), width=1)
    for m in (marks or {}).get("s_mm", []):
        x = 10 + m * PPM; d.line([(x, y0 - 14), (x, y0 + 16)], fill=(230, 40, 40), width=2)
    for k in range(0, int(A.L) + 1, 50):
        x = 10 + k * PPM; d.line([(x, y0 + sbr.shape[0] + 2), (x, y0 + sbr.shape[0] + 8)], fill=(0, 0, 0)); d.text((x + 2, y0 + sbr.shape[0] + 8), f"{k}", fill=(0, 0, 0))
    src = "art" if ART else "shipped DSTs"
    gap = {"internal": "no seam (one piece)", "zip": "zip closed (15 + 15 mm keep-outs)"}.get(sm["kind"], "seam closed up (3 + 3 mm)")
    ms = f"art on the seam {st['art_mm']} mm, both sides meet {st['meet']} %, same tone {st['tone']} %" if st["meet"] is not None else "no art on this seam"
    d.text((10, 8), f"{sm['name']} (size {size}, {src}) - above: {A.P} {A.L:.0f} mm, below: {B.P} {B.L:.0f} mm (eased to the same length), {gap}; red = match marks; {ms}", fill=(0, 0, 0))
    return im, st

def run(art=None):
    D = art or pickle.load(open(f"art_{size}.pkl", "rb")); MK = D.get("marks", {})
    ims = []; table = {}
    for sm in WR.seams(size):
        im, st = sheet(sm, MK.get(sm["name"])); nm = sm["name"].replace(" ", "_")
        im.save(f"out/continuity_{nm}{'_art' if ART else ''}.png"); ims.append(im); table[sm["name"]] = st
        print(f"{sm['name']:<18} {st}", flush=True)
    W = max(i.width for i in ims); H = sum(i.height for i in ims) + 10 * len(ims)
    allim = Image.new("RGB", (W, H), "white"); y = 0
    for i in ims: allim.paste(i, (0, y)); y += i.height + 10
    allim.save(f"out/continuity_{size}{'_art' if ART else ''}.png"); print("sheet", allim.size)
    json.dump(table, open(f"continuity_{size}{'_art' if ART else ''}.json", "w"), indent=1)
    return table

if __name__ == "__main__":
    run()
