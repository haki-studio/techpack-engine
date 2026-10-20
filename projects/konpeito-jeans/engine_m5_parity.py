"""ENGINE_PLAN M5 parity: the parts engine (digitize.svgrun, founder SVG) vs the delivered Konpeito Rev A files.

  PYTHONPATH=../../engine python3 engine_m5_parity.py          (after the five bench/run_*_svg.yaml runs)

Both files go through the SAME gates (digitize.svgrun.gate_file: centreline per string, motif IoU per SVG layer on its
own stops near-restricted, A15 uncovered, exposed stitches on the exact geometry at the M5 thresholds, threads, max
stitch). The delivered file's parts are its own regions from out/art.pkl (kjsvg), mapped to the SVG layers by
overlap; its stops are kjstitch's stop plan. Writes out/engine_m5/PARITY.md + parity.json + side-by-side live views.
Read-only on the delivered files (out/stitch/, out/art.pkl)."""
import json, os, pickle, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "..", "..", "engine")
if ENGINE not in sys.path: sys.path.insert(0, ENGINE)
from shapely.ops import unary_union
from digitize import config
from digitize.schema import ObjectPlan, Part, DirSpec
from digitize.rulebook import Rulebook
from digitize import svgrun

RUNS = {"wb": "run_wb_svg.yaml", "coin": "run_coin_svg.yaml", "spill": "run_spill_svg.yaml", "starP": "run_starP_svg.yaml", "starY": "run_starY_svg.yaml"}
KIND = {"TXC": "lettering", "LINE": "line_art", "FL": "petal", "KP": "petal", "KPB": "petal", "FL-hi": "petal_tint", "KP-hi": "petal_tint",
        "KPB-hi": "petal_tint", "KNOT": "knot", "DOT": "dot", "BDOT": "dot", "BFL": "floret", "BAND": "patch_band", "FIELD": "patch_field",
        "EDGE": "patch_edge", "STAR": "star", "STAR-hi": "star_tint"}


def delivered_plan(el, eng, cfg):
    """an ObjectPlan for the delivered file: its regions (art.pkl) as parts in kjstitch's stop order, each tagged with
    the SVG layer of the engine parts it overlaps most (same thread)"""
    A = pickle.load(open(os.path.join(HERE, "out", "art.pkl"), "rb"))
    import kjstitch
    stem, splan = kjstitch.FILES[el]
    if el.startswith("star"):
        import kjsvg
        vis = kjsvg.star_regions(el[-1], 0.0, 0.0, 10.0)
    else:
        vis = [r for r in A[el]["vis"] if not r["geom"].is_empty]
    stops = kjstitch.stops_for(vis, splan)
    lay = {}
    for p in eng.parts: lay.setdefault((p.meta["layer"], p.thread), []).append(p.geom)
    lay = {k: unary_union(v) for k, v in lay.items()}
    rb = Rulebook(); parts = []; pstops = []; n = 0
    for s in stops:
        ids = []
        for r in s["regions"]:
            n += 1; kind = KIND[r["grp"]]
            cand = [(g.intersection(r["geom"]).area, L) for (L, t), g in lay.items() if t == r["col"]]
            layer = max(cand)[1] if cand and max(cand)[0] > 0 else "?"
            p = Part(id=f"d.{n:03d}", kind=kind, geom=r["geom"], thread=r["col"], z=float(n), dir=DirSpec(0.0), zone=layer,
                     meta=dict(layer=layer, thread_wt=cfg["threads"].get("weight", {}).get(r["col"], "40wt")))
            p.technique = rb.technique_for(kind); p.stitch = rb.stitch_spec(kind, p.technique)
            parts.append(p); ids.append(p.id)
        pstops.append(dict(thread=s["col"], parts=ids))
    th = {k: dict(hex=v, weight=cfg["threads"].get("weight", {}).get(k, "40wt")) for k, v in cfg["threads"]["palette"].items()}
    return ObjectPlan(name=stem, parts=parts, threads=th, stops=pstops, meta=dict(eng.meta)), stem


def rowfmt(g):
    f = g["file"]; cl = g["centreline"]; mm = g["motifs"]
    return dict(stitches=f["stitches"], trims=f["trims"], stops=f["stops"], threads=f["threads"], max_stitch=f["max_stitch"],
                machine_min=f.get("machine_min"), cl_pass=f"{sum(r['ok'] for r in cl)}/{len(cl)}",
                cl_worst=max([r["mean_d"] for r in cl if r["mean_d"] is not None], default=None),
                motifs=f"{sum(r['passed'] for r in mm)}/{sum(r['motifs'] for r in mm)}",
                motif_min_iou=min([r["min_iou"] for r in mm if r["min_iou"] is not None], default=None),
                house_min=sum(r["house_min"] for r in mm), exposed=len(g["exposed_stitches"]), uncovered=len(g["uncovered"]))


def main():
    import factory, readback
    out = {}; md = ["# M5 parity: parts engine (founder SVG) vs delivered Konpeito Rev A", "",
                    "Same gates on both files (digitize.svgrun.gate_file). Exposed = stitches >= 0.5 mm with > 0.3 mm on bare fabric "
                    "(outside own stop art + 0.25 mm and not under a later stop). Centreline: mean skeleton distance <= 0.5 mm and "
                    "width within 20 %. Motifs: IoU >= 0.70 + extents >= 80 % per SVG shape (house-min dots counted as pass).", ""]
    hdr = ["element", "file", "stitches", "trims", "stops", "threads", "max st", "min", "centreline", "worst cl mm", "motifs", "min IoU", "house-min", "exposed", "uncovered"]
    md += ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
    for el, y in RUNS.items():
        cfg = config.load(os.path.join(HERE, "bench", y)); eo = config.path(cfg, cfg["out_dir"])
        eng = ObjectPlan.from_json(os.path.join(eo, "plan.json"))
        ge = json.load(open(os.path.join(eo, "gates.json")))
        dplan, stem = delivered_plan(el, eng, cfg)
        dpath = os.path.join(HERE, "out", "stitch", stem)
        dj = json.load(open(dpath + ".json"))
        rb = readback.dst(dpath + ".dst"); prof = factory.load()
        rbk = dict(origin=dj["origin_mm"], readback=rb, threads=factory.check_threads(dpath + ".pes"),
                   machine_min=round(factory.machine_hours(rb["stitches"], prof, trims=rb["trims"], colour_changes=rb["stops"] - 1) * 60, 1))
        gd = svgrun.gate_file(cfg, dplan, dpath + ".dst", rbk)
        out[el] = dict(delivered=gd, engine=ge)
        for who, g, f in (("delivered Rev A", gd, os.path.basename(dpath) + ".dst"), ("engine M5", ge, cfg["name"] + ".dst")):
            r = rowfmt(g)
            md.append("| " + " | ".join(str(v) for v in [el, who, r["stitches"], r["trims"], r["stops"], r["threads"], r["max_stitch"], r["machine_min"],
                                                          r["cl_pass"], r["cl_worst"], r["motifs"], r["motif_min_iou"], r["house_min"], r["exposed"], r["uncovered"]]) + " |")
        side(el, dpath + ".dst", dj["origin_mm"], os.path.join(eo, cfg["name"] + ".dst"), json.load(open(os.path.join(eo, "readback.json")))["origin"],
             cfg, eng, os.path.join(HERE, "out", "engine_m5", f"parity_{el}.png"))
    md += ["", "## Centreline per string", "", "| element | string | delivered mean / width ratio | engine mean / width ratio |", "|---|---|---|---|"]
    for el, v in out.items():
        dm = {r["layer"]: r for r in v["delivered"]["centreline"]}
        for r in v["engine"]["centreline"]:
            d = dm.get(r["layer"], {})
            md.append(f"| {el} | {r['family']} | {d.get('mean_d')} / {d.get('ratio')} {'PASS' if d.get('ok') else 'FAIL'} | {r['mean_d']} / {r['ratio']} {'PASS' if r['ok'] else 'FAIL'} |")
    md += ["", "## Exposed stitches in the delivered files (same gate)", ""]
    for el, v in out.items():
        md.append(f"- {el}: {len(v['delivered']['exposed_stitches'])}" + (": " + ", ".join(f"stop {s} at ({x}, {y}) {l} mm" for s, x, y, l in v['delivered']['exposed_stitches'][:8]) if v['delivered']['exposed_stitches'] else ""))
    os.makedirs(os.path.join(HERE, "out", "engine_m5"), exist_ok=True)
    open(os.path.join(HERE, "out", "engine_m5", "PARITY.md"), "w").write("\n".join(md) + "\n")
    json.dump(out, open(os.path.join(HERE, "out", "engine_m5", "parity.json"), "w"), indent=1, default=float)
    print("\n".join(md))


def side(el, dd, dorig, ed, eorig, cfg, eng, path):
    """delivered | engine live views of the same area, same scale"""
    import dstlive
    from PIL import Image, ImageDraw, ImageFont
    from dst2 import bounds_of
    b = bounds_of([p.geom for p in eng.parts]); bb = (b[0] - 1.5, b[1] - 1.5, b[2] + 1.5, b[3] + 1.5)
    import pyembroidery as pe
    ims = []
    for d, o in ((dd, dorig), (ed, eorig)):
        cols = [t.hex_color() for t in pe.read(d[:-4] + ".pes").threadlist]
        ims.append(dstlive.render(d, cols, ppm=20, shell="#1f1f22", bounds=bb, origin=tuple(o)))
    W, H = ims[0].size; im = Image.new("RGB", (2 * W + 30, H + 40), (245, 245, 242)); D = ImageDraw.Draw(im)
    try: f = ImageFont.load_default(size=22)
    except TypeError: f = ImageFont.load_default()
    for i, (t, x) in enumerate((("delivered Rev A (kjstitch)", 0), ("engine M5 (digitize.svgrun, founder SVG)", W + 30))):
        im.paste(ims[i], (x, 40)); D.text((x + 6, 8), t, fill=(20, 20, 20), font=f)
    im.save(path)


if __name__ == "__main__":
    main()
