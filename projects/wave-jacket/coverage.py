"""QA gate (ENGINE_NOTES 7): how much of each stitch code's art the SHIPPED DST actually covers. Every sewn stitch is drawn
as a 0.75 mm line (thread width, generous) at 4 px/mm and compared with the art regions of that code, eroded 0.25 mm (edge tolerance:
pull comp + raster). Fill + satin codes must
reach MIN_COV; run/bean codes are reported only. Writes coverage.json.  usage: ./py.sh coverage.py [sizes...]"""
import wavecore as WC
import sys, json, pickle
import numpy as np, pyembroidery as pe
from scipy import ndimage as ndi
from PIL import Image, ImageDraw
dst2 = WC.patch_dst2()
MIN_COV = 98.0; PPM = 4

def raster(geoms, x0, y0, W, H):
    A = Image.new("L", (W, H)); d = ImageDraw.Draw(A)
    for G in geoms:
        for p in dst2.polys(G):
            d.polygon([((x-x0)*PPM, (y-y0)*PPM) for x, y in p.exterior.coords], fill=255)
            for h in p.interiors: d.polygon([((x-x0)*PPM, (y-y0)*PPM) for x, y in h.coords], fill=0)
    return np.asarray(A) > 0

def piece(size, P, D):
    r = json.load(open(f"out/01_wave/{size}/result_{P}.json"))["full"]; p = pe.read(r["file"] + ".dst"); ox, oy = r["origin"]
    b = r["art_box"]; x0, y0 = b[0] - 5, b[1] - 5; W, H = int((b[2]-x0+5)*PPM), int((b[3]-y0+5)*PPM)
    S = Image.new("L", (W, H)); ds = ImageDraw.Draw(S); prev = None
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK; q = ((x/10+ox-x0)*PPM, (y/10+oy-y0)*PPM)
        if k == pe.STITCH:
            if prev: ds.line([prev, q], fill=255, width=3)
            prev = q
        else: prev = None
    if r.get("chenille"):                                  # primary foam = the chenille file (loop rows ~2 mm wide)
        import live
        live.draw_chenille(S, r["chenille"], (x0, y0, 0, 0), PPM, flat={"w1": 255, "w3": 255, "w1e": 255})
    s = np.asarray(S) > 0; out = {}
    vis = dst2.merge_colours(D[P])
    for key in sorted({(g["grp"], g["st"]) for g in vis}):
        a = ndi.binary_erosion(raster([g["geom"] for g in vis if (g["grp"], g["st"]) == key], x0, y0, W, H))   # 0.25 mm edge tolerance
        if a.sum(): out[f"{key[0]}/{key[1]}"] = dict(mm2=round(a.sum()/PPM**2), cov=round(100*(a & s).sum()/a.sum(), 1))
    return out

if __name__ == "__main__":
    sizes = sys.argv[1:] or WC.SIZES; res = {}; bad = []
    try: res = json.load(open("coverage.json"))
    except Exception: pass
    for sz in sizes:
        D = pickle.load(open(f"art_{sz}.pkl", "rb"))
        for P in WC.PIECES:
            c = piece(sz, P, D); res.setdefault(sz, {})[P] = c
            fills = {k: v for k, v in c.items() if k.split("/")[1] in ("tatami", "padded", "satin")}
            worst = min(fills.items(), key=lambda kv: kv[1]["cov"])
            ok = all(v["cov"] >= MIN_COV or v["mm2"] < 200 for v in fills.values())
            if not ok: bad.append((sz, P, worst))
            print(sz, P, "worst fill/satin code", worst[0], worst[1], "PASS" if ok else "FAIL", flush=True)
    json.dump(res, open("coverage.json", "w"), indent=1)
    print("COVERAGE PASS" if not bad else f"COVERAGE FAIL {bad}")
