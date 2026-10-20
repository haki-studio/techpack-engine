"""Per-glyph text gate (Rev C, review of PR #20 item 1): every stitched character is compared with the FONT's own glyph.

Reference = the font outline as placed on the garment (scene META["glyphs"], recorded where the text is set; the fonts'
nonzero fill, kclettering.nonzero), moved to each size exactly as art_size.place_front moves the badge. Never the stroke
columns or any art geometry: a column builder that drops a stroke (Rev B/C: the centre vertical of 界) must fail here.
Stitched = the shipped DST read back (dstview.mask_as_sewn, only the glyph's own threads), closed 0.3 mm (satin rows
into a surface), counted within 1.0 mm of the glyph (neighbouring motifs in the same thread are not the glyph).
Gate per glyph, every size, full files: IoU >= 0.80, no missing piece > MISS_LIMIT mm2, every font counter matched by its
own stitched counter. Any failing glyph blocks delivery.

  glyph_check(ref_geom, stitched_mask, bb, ppm) -> IoU         (pure function, tested in tests/test_kcos_gates.py)
usage: python3 glyph_gate.py [sizes...] [--dst-dir out/stitch] -> glyph_gate.json + table; exit 1 on any failure"""
import kccore
import json, sys, pickle, os
import numpy as np
from scipy import ndimage as ndi
from shapely import wkt as WKT, affinity

PPM = 8.0

from kcgates import raster, holes, glyph_check, GLYPH_IOU, GLYPH_MISS      # tested in tests/test_kcos_gates.py

def placed(size, el, g, info):
    """the scene glyph (size-M garment mm) moved to `size` exactly as art_size.place_front moves badge `el`"""
    import drum
    S = pickle.load(open("scene.pkl", "rb"))["meta"]
    grade, s = kccore.GRADE[size]; b = drum.Block(size); BM = drum.Block("M")
    kx, ky = b.chest2 / BM.chest2, b.f_hem / BM.f_hem
    ax, ay = S["badges"][el]["centre"]; tx, ty = ax * kx, ay * ky
    mv = info.get("moves", {}).get(el, (0.0, 0.0)); mv = mv if isinstance(mv, (tuple, list)) else (0.0, 0.0)
    return affinity.translate(affinity.scale(g, s, s, origin=(ax, ay)), tx - ax + mv[0], ty - ay + mv[1])

def run(sizes, dst_dir="out/stitch"):
    import dstview as DV
    from motifs2 import HEX
    META = pickle.load(open("scene.pkl", "rb"))["meta"]
    res = {}; fails = []
    for size in sizes:
        info = pickle.load(open(f"art_{size}.pkl", "rb"))["info"]
        for el, gl in sorted(META.get("glyphs", {}).items()):
            for i, r in enumerate(gl):
                P = r["piece"]; g = placed(size, el, WKT.loads(r["wkt"]), info[P])
                b = g.bounds; bb = (b[0] - 2, b[1] - 2, b[2] + 2, b[3] + 2)
                base = f"{dst_dir}/{size}/HAKI_{kccore.SHORT}_{P}_{size}"
                st = DV.mask_as_sewn(base, bb, PPM, only=[HEX[k] for k in r["threads"]])
                c = glyph_check(g, st, bb, PPM)
                res.setdefault(size, {}).setdefault(el, []).append(dict(ch=r["ch"], **c))
                if not c["ok"]: fails.append(f"{size} {el} {r['ch']} {c}")
    return res, fails

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dd = sys.argv[sys.argv.index("--dst-dir") + 1] if "--dst-dir" in sys.argv else "out/stitch"
    if dd in args: args.remove(dd)
    sizes = args or kccore.SIZES
    res, fails = run(sizes, dd)
    if dd == "out/stitch": json.dump(dict(limit=dict(iou=GLYPH_IOU, miss_mm2=GLYPH_MISS), ppm=PPM, sizes=res, fails=fails), open("glyph_gate.json", "w"), indent=1, ensure_ascii=False)
    for size, d in res.items():
        print(size, " ".join(f"{el}: " + " ".join(f"{q['ch']}{q['iou']:.2f}/{q['miss_mm2']:.1f}/{q['counters'][1]}of{q['counters'][0]}" for q in v) for el, v in d.items()))
    print("GLYPH FAILS:", fails or "none")
    sys.exit(1 if fails else 0)
