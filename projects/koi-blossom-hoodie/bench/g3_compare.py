"""ENGINE_PLAN G3 compare: Rev B delivered vs G2 run 3 vs G3 (per-petal label windows on the upper lily), SAME crop,
SAME gates as g2_compare (imported, unchanged), plus:
  - motif_match per LABELLED motif for all three files (digitize.labels.refgrade on bench/labels_FR.json: the
    reference each motif names, default the mockup), so every file is graded on the same units;
  - the lily read: inside the upper-lily windows, how many 15-degree stitch-angle bins hold >= 8 % of the stitch
    length (a flat slab sews one or two; petals each along their own axis sew several) and the parts the plan made.
  - --labels <file>: grade against another labels file (e.g. bench/labels_FR_tetra.json: fish vs the founder's tetra)

  PYTHONPATH=engine python3 projects/koi-blossom-hoodie/bench/g3_compare.py [--labels bench/labels_FR_tetra.json]
Reads only written files + input pixels. Writes bench/g3_gates.json, bench/g3_side_by_side.png, bench/g3_zoom_lily.png
(no Anthropic API calls)."""
import argparse, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); PROJ = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import g2_compare as G                      # chdir(PROJ), engine path, art modules blocked
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union
import qa
from digitize import bench, config, gates_orphan
from digitize.extract import register, evidence
from digitize.labels import schema as LS, refgrade as RG

G.FILES = {"revB": G.REVB,
           "g2run3": (os.path.join(PROJ, "out/g2run3/KOI_FR_M_labels.dst"), tuple(json.load(open(os.path.join(PROJ, "out/g2run3/readback.json")))["origin"])),
           "engine": G.ENG}
G.NAMES = {"revB": "Rev B delivered", "g2run3": "G2 run 3 (one lily window)", "engine": "G3 (one window per petal)"}
LILY = "flower_upper"


def lily_read(dst, origin, labels):
    m = next(m for m in labels["motifs"] if m["id"] == LILY)
    zone = unary_union([Polygon(w).buffer(0) for p in m["parts"] for w in p["hint"]["polygons"]])
    hist = np.zeros(12); n = 0
    for x0, y0, x1, y1 in qa.dst_segments(dst, origin):
        L = math.hypot(x1 - x0, y1 - y0)
        if L < 0.5 or L > 12 or not zone.contains(Point((x0 + x1) / 2, (y0 + y1) / 2)): continue
        hist[int((math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180) // 15) % 12] += L; n += 1
    share = hist / max(hist.sum(), 1e-9)
    return dict(stitches=n, angle_bins_ge8pct=int((share >= 0.08).sum()), top_bin_pct=round(100 * float(share.max()), 1),
                share_by_15deg=[round(100 * float(s), 1) for s in share])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--labels", default="bench/labels_FR.json"); a = ap.parse_args()
    cfg = config.load(os.path.join(HERE, "run_fr_labels.yaml")); T = cfg["threads"]
    lpth = os.path.join(PROJ, a.labels); labels = LS.load(lpth, palette=T["palette"])
    reg_mock = register.load(os.path.join(PROJ, G.CFG["registration"]))
    ev = evidence.build(register.reference(reg_mock, "F", G.CROP, ppm=float(G.CFG["ppm"])), T["palette"], **cfg["evidence"])
    P, flora, fishes, fish_mock = G.refmasks(reg_mock)
    res = {"crop": list(G.CROP), "labels": a.labels, "files": {}}
    for k, (dst, o) in G.FILES.items():
        row, _ = bench.run_gates(G.CFG, PROJ, dst, o)
        out = G.dst_mask(dst, o, flora.shape, P)
        ms = qa.dst_stop_masks(dst, o, (ev.H, ev.W), ev.ppm, to_mm=lambda x, y: (x - ev.bounds[0], y - ev.bounds[1]))
        out_ev = np.any(list(ms.values()), axis=0)
        rows = RG.grade(labels, os.path.dirname(lpth), ev, out_ev, bare=tuple(T.get("bare") or ()))
        res["files"][k] = dict(dst=os.path.relpath(dst, PROJ), counts=G.file_counts(dst, o), gates=row, verdict=bench.verdict(row, G.CFG["targets"]),
                               fidelity=G.fidelity(P, flora, fishes, out, fish_mock),
                               orphans={kk: v for kk, v in gates_orphan.orphan_fragments(os.path.splitext(dst)[0] + ".pes").items() if kk != "hits"},
                               motif_reference=dict(summary=RG.summary(rows), rows=rows), lily=lily_read(dst, o, labels))
        f = res["files"][k]
        print(k, f["fidelity"]["fish"], f["fidelity"]["fish_mockup"], f["fidelity"]["flora"], f["motif_reference"]["summary"],
              {r["unit"]: (r["reference"], r["iou"], r["ok"]) for r in rows if r["unit"] in (LILY,) or r["unit"].startswith("fish")},
              f["lily"]["angle_bins_ge8pct"], f["lily"]["top_bin_pct"], flush=True)
    pj = json.load(open(os.path.join(G.ENG_DIR, "parts.json")))
    res["engine_lily_parts"] = [dict(id=q["id"], kind=q["kind"], thread=q["thread"], area_mm2=q["area_mm2"], piece=q["meta"].get("label_piece"))
                                for q in pj["parts"] if q["meta"].get("motif") == LILY]
    json.dump(res, open(os.path.join(HERE, "g3_gates.json"), "w"), indent=1, default=float)
    tables(res)
    if a.labels == "bench/labels_FR.json":
        G.sheet(G.views(G.CROP, 4.0, reg_mock), os.path.join(HERE, "g3_side_by_side.png"),
                f"Koi Blossom FR size M, crop x {G.CROP[0]}..{G.CROP[2]}, y {G.CROP[1]}..{G.CROP[3]} mm, 4 px/mm - Rev B | G2 run 3 | G3 per-petal windows")
        box = (-226, 96, -146, 186)
        G.sheet(G.views(box, 10.0, reg_mock), os.path.join(HERE, "g3_zoom_lily.png"),
                f"zoom (upper lily): x {box[0]}..{box[2]}, y {box[1]}..{box[3]} mm, 10 px/mm - Rev B | G2 run 3 (one window) | G3 (one window per petal)")


def tables(res):
    F = res["files"]; ks = list(G.FILES)
    def c(fn): return " | ".join(fn(F[k]) for k in ks)
    lines = [f"| gate | {' | '.join(G.NAMES[k] for k in ks)} |", "|---" * (len(ks) + 1) + "|"]
    for name, fn in [
        ("fish vs founder tetra @0.82 (A14)", lambda f: f"{f['fidelity']['fish']['ok']}/{f['fidelity']['fish']['n']}, IoU {f['fidelity']['fish']['mean_iou']}"),
        ("fish vs mockup fish (A14)", lambda f: f"{f['fidelity']['fish_mockup']['ok']}/{f['fidelity']['fish_mockup']['n']}, IoU {f['fidelity']['fish_mockup']['mean_iou']}"),
        ("flora motif_match (A14)", lambda f: f"{f['fidelity']['flora']['ok']}/{f['fidelity']['flora']['n']}, IoU {f['fidelity']['flora']['mean_iou']}"),
        ("labelled motifs vs their reference (G3 refgrade)", lambda f: "; ".join(f"{k} {v['ok']}/{v['n']} IoU {v['mean_iou']}" for k, v in f["motif_reference"]["summary"].items())),
        ("upper lily vs mockup (refgrade unit)", lambda f: next((f"IoU {r['iou']}, w {r['w_ratio']} h {r['h_ratio']}, {'ok' if r['ok'] else 'FAIL'}" for r in f["motif_reference"]["rows"] if r["unit"] == LILY), "-")),
        ("upper lily: 15-deg angle bins >= 8 % / top bin", lambda f: f"{f['lily']['angle_bins_ge8pct']} / {f['lily']['top_bin_pct']} %"),
        ("uncovered >= 25 mm2 (A15)", lambda f: f"{f['fidelity']['uncovered']['n']} gaps, {f['fidelity']['uncovered']['mm2']} mm2"),
        ("sewn off the reference", lambda f: f"{f['fidelity']['sewn_off_reference_mm2']} mm2"),
        ("orphan fragments", lambda f: str(f["orphans"]["n"])),
        ("direction OK / chaos", lambda f: f"{f['gates']['direction']['pct_ok']} % / {f['gates']['direction']['pct_chaos']} %"),
        ("density flags (p95)", lambda f: f"{f['gates']['density']['flags']} ({f['gates']['density']['p95']})"),
        ("trims /100 cm2", lambda f: f"{f['gates']['trims']['per_100cm2']} ({f['gates']['trims']['trims']} trims)"),
        ("stitches in crop", lambda f: f"{f['counts']['stitches_in_crop']:,}"),
        ("bench verdict", lambda f: f"{sum(map(bool, f['verdict'].values()))}/{len(f['verdict'])} ({', '.join(k for k, v in f['verdict'].items() if v)})"),
    ]:
        try: lines.append(f"| {name} | {c(fn)} |")
        except Exception as e: lines.append(f"| {name} | (n/a: {type(e).__name__} {e}) |")
    t = "\n".join(lines); open(os.path.join(HERE, "g3_table.md"), "w").write(t + "\n"); print(t)


if __name__ == "__main__":
    main()
