"""Rev I gate (founder 21 Oct 2026, EN badge FL M): in a PUFF glyph no flat-after-foam fragment shorter than 8 mm or
touching a puff stroke (kcgates.flat_fragments, tested red-then-green in tests/test_kcos_gates.py). Every size, every front
file, full files and hoop splits; glyphs from scene META["glyphs"] (the font outlines) moved to each size as glyph_gate.placed.
usage: python3 frag_gate.py [sizes...] [--dst-dir out/stitch] [--json frag_gate.json] -> exit 1 on any bad fragment"""
import kccore
import json, sys, pickle
from shapely import wkt as WKT
import kcgates
from glyph_gate import placed

def run(sizes, dst_dir="out/stitch", results=None):
    META = pickle.load(open("scene.pkl", "rb"))["meta"]
    res = {}; bad = []
    for size in sizes:
        info = pickle.load(open(f"art_{size}.pkl", "rb"))["info"]
        for P in ("FR", "FL"):
            gl = [(f"{el} {r['ch']}", placed(size, el, WKT.loads(r["wkt"]), info[P])) for el, rs in sorted(META.get("glyphs", {}).items()) for r in rs if r["piece"] == P]
            R = json.load(open(f"{dst_dir}/{size}/result_{P}.json"))
            files = [("full", R["full"])] + list(R.get("splits", {}).get("sections", {}).items())
            for nm, f in files:
                r = kcgates.flat_fragments(f["file"].replace("out/stitch", dst_dir) + ".dst", f["per_stop"], gl, f["origin"])
                res.setdefault(size, {})[f"{P} {nm}"] = dict(puff_glyphs=r["puff_glyphs"], top_fragments=len(r["fragments"]), bad=r["bad"])
                bad += [f"{size} {P} {nm} {b}" for b in r["bad"]]
    return res, bad

if __name__ == "__main__":
    a = sys.argv[1:]
    dd = a[a.index("--dst-dir") + 1] if "--dst-dir" in a else "out/stitch"
    js = a[a.index("--json") + 1] if "--json" in a else "frag_gate.json"
    sizes = [x for x in a if x in kccore.SIZES] or kccore.SIZES
    res, bad = run(sizes, dd)
    json.dump(dict(rule=f"puff glyph: no flat-after-foam fragment < {kcgates.FRAG_MIN_MM} mm or touching its puff (within {kcgates.FRAG_TOUCH_MM} mm)",
                   dst_dir=dd, sizes=res, bad=bad), open(js, "w"), indent=1, ensure_ascii=False, default=float)
    for s, d in res.items(): print(s, {k: (v["puff_glyphs"], v["top_fragments"], len(v["bad"])) for k, v in d.items()})
    print("FRAG BAD:", len(bad)); [print("  ", b) for b in bad[:40]]
    sys.exit(1 if bad else 0)
