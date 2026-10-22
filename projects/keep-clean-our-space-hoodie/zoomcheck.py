"""Rev I: stitch-line zooms (dstzoom, PES read back) of every badge at the previous defect spots, Rev H vs Rev I side by
side, same scale -> out/zoom/<size>_<piece>_<label>.png. Spots = the Rev H frag-gate fragments (out/frag_gate_revH_M.json)
+ one whole-badge view per badge. usage: python3 zoomcheck.py [size] [--old out/old_revH_stitch]"""
import json, sys, os
from PIL import Image, ImageDraw
import dstzoom, kccore

def pair(size, P, box_g, label, old_dir, ppm):
    ims = []
    for tag, d in (("Rev H", old_dir), ("Rev I", "out/stitch")):
        f = json.load(open(f"{d}/{size}/result_{P}.json"))["full"]; ox, oy = f["origin"]
        base = f"{d}/{size}/HAKI_{kccore.SHORT}_{P}_{size}"
        b = (box_g[0] - ox, box_g[1] - oy, box_g[2] - ox, box_g[3] - oy)
        im = dstzoom.zoom(base, b, "/tmp/_z.png", ppm=ppm); dr = ImageDraw.Draw(im); dr.text((6, 4), f"{tag} {P} {size} {label}", fill=(255, 255, 255))
        ims.append(im)
    W = sum(i.width for i in ims) + 10; H = max(i.height for i in ims)
    out = Image.new("RGB", (W, H), (255, 255, 255)); x = 0
    for i in ims: out.paste(i, (x, 0)); x += i.width + 10
    os.makedirs("out/zoom", exist_ok=True); p = f"out/zoom/{size}_{P}_{label}.png"; out.save(p); return p

if __name__ == "__main__":
    a = sys.argv[1:]; size = next((x for x in a if x in kccore.SIZES), "M")
    old = a[a.index("--old") + 1] if "--old" in a else "out/old_revH_stitch"
    import pickle
    from shapely import wkt as WKT
    from shapely.ops import unary_union
    from glyph_gate import placed
    META = pickle.load(open("scene.pkl", "rb"))["meta"]; info = pickle.load(open(f"art_{size}.pkl", "rb"))["info"]
    out = []
    for el, rs in sorted(META["glyphs"].items()):
        P = rs[0]["piece"]; U = unary_union([placed(size, el, WKT.loads(r["wkt"]), info[P]) for r in rs]); b = U.bounds
        out.append(pair(size, P, (b[0] - 4, b[1] - 4, b[2] + 4, b[3] + 4), f"badge{el}", old, 8))
    if size == "M" and os.path.exists("out/frag_gate_revH_M.json"):
        bad = json.load(open("out/frag_gate_revH_M.json"))["sizes"]["M"]
        seen = set()
        for k in ("FL full", "FR full"):
            for f in bad[k]["bad"]:
                x, y = f["at_mm"]; key = (k, round(x / 6), round(y / 6))
                if key in seen: continue
                seen.add(key); g = f["glyph"].split()[1]
                out.append(pair("M", k.split()[0], (x - 7, y - 7, x + 7, y + 7), f"spot_{f['glyph'].split()[0]}_{g}_{x:.0f}_{y:.0f}", old, 30))
    print(len(out), "zoom sheets"); [print(" ", p) for p in out]
