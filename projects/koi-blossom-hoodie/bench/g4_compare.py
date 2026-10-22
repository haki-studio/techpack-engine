"""ENGINE_PLAN G4 compare (founder 2026-10-22, "we want the tetra"): Rev B delivered vs G3 (fish from the mockup koi) vs
G4 (the tetra governs the fish), SAME crop, SAME gates as g2/g3_compare (imported, unchanged), plus per-fish refgrade:
  - vs the TETRA: bench/labels_FR.json (reference governs silhouette + colour): shape AND sewn colours (refgrade.colour_grade);
  - vs the MOCKUP koi: bench/labels_FR_mockup.json (the G3 labels): shape only.
Each file's thread per stop comes from its own PES thread list, so Rev B is graded the same way as the engine files.

  PYTHONPATH=engine python3 projects/koi-blossom-hoodie/bench/g4_compare.py
Reads only written files + input pixels. Writes bench/g4_gates.json, bench/g4_table.md, bench/g4_side_by_side.png,
bench/g4_zoom_fish.png (no Anthropic API calls)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); PROJ = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import g2_compare as G                      # chdir(PROJ), engine path, art modules blocked
import g3_compare as G3
import numpy as np
import qa
from digitize import bench, config, gates_orphan
from digitize.extract import register, evidence
from digitize.labels import schema as LS, refgrade as RG

G3_DIR = os.path.join(PROJ, "out/digitize/KOI_FR_M_labels_g3")      # G3 run (labels_FR_mockup.json), copied from ~/te-g3
G.FILES = {"revB": G.REVB,
           "g3": (os.path.join(G3_DIR, "KOI_FR_M_labels.dst"), tuple(json.load(open(os.path.join(G3_DIR, "readback.json")))["origin"])),
           "engine": G.ENG}
G.NAMES = {"revB": "Rev B delivered", "g3": "G3 (fish = mockup koi)", "engine": "G4 (fish = founder tetra)"}


def fish_rows(rows):
    return [r for r in rows if r["motif"].startswith("fish")]


def main():
    cfg = config.load(os.path.join(HERE, "run_fr_labels.yaml")); T = cfg["threads"]; bare = tuple(T.get("bare") or ())
    lab_t = LS.load(os.path.join(HERE, "labels_FR.json"), palette=T["palette"])
    lab_m = LS.load(os.path.join(HERE, "labels_FR_mockup.json"), palette=T["palette"])
    reg_mock = register.load(os.path.join(PROJ, G.CFG["registration"]))
    ev = evidence.build(register.reference(reg_mock, "F", G.CROP, ppm=float(G.CFG["ppm"])), T["palette"], **cfg["evidence"])
    P, flora, fishes, fish_mock = G.refmasks(reg_mock)
    res = {"crop": list(G.CROP), "files": {}}
    for k, (dst, o) in G.FILES.items():
        row, _ = bench.run_gates(G.CFG, PROJ, dst, o)
        out = G.dst_mask(dst, o, flora.shape, P)
        ms = qa.dst_stop_masks(dst, o, (ev.H, ev.W), ev.ppm, to_mm=lambda x, y: (x - ev.bounds[0], y - ev.bounds[1]))
        hexes = G.colours(dst)
        if ms and max(ms) >= len(hexes): raise SystemExit(f"{dst}: {max(ms) + 1} stops but {len(hexes)} PES threads")
        out_ev = np.any(list(ms.values()), axis=0)
        rt = fish_rows(RG.grade(lab_t, HERE, ev, out_ev, bare=bare, stops=(ms, hexes), palette=T["palette"]))
        rm = fish_rows(RG.grade(lab_m, HERE, ev, out_ev, bare=bare))
        res["files"][k] = dict(dst=os.path.relpath(dst, PROJ), counts=G.file_counts(dst, o), gates=row, verdict=bench.verdict(row, G.CFG["targets"]),
                               fidelity=G.fidelity(P, flora, fishes, out, fish_mock),
                               orphans={kk: v for kk, v in gates_orphan.orphan_fragments(os.path.splitext(dst)[0] + ".pes").items() if kk != "hits"},
                               fish_tetra=rt, fish_mockup=rm, threads=hexes)
        print(k, [(r["unit"], r["iou"], r.get("colour_match"), r["ok"]) for r in rt], [(r["unit"], r["iou"], r["ok"]) for r in rm], flush=True)
    json.dump(res, open(os.path.join(HERE, "g4_gates.json"), "w"), indent=1, default=float)
    tables(res)
    G.sheet(G.views(G.CROP, 4.0, reg_mock), os.path.join(HERE, "g4_side_by_side.png"),
            f"Koi Blossom FR size M, crop x {G.CROP[0]}..{G.CROP[2]}, y {G.CROP[1]}..{G.CROP[3]} mm, 4 px/mm - Rev B | G3 (koi) | G4 (the founder's tetra governs the fish)")
    box = (-165, 150, -85, 210)
    G.sheet(G.views(box, 10.0, reg_mock), os.path.join(HERE, "g4_zoom_fish.png"),
            f"zoom (middle fish): x {box[0]}..{box[2]}, y {box[1]}..{box[3]} mm, 10 px/mm - Rev B | G3 (koi) | G4 (tetra)")


def tables(res):
    F = res["files"]; ks = list(G.FILES)
    def c(fn): return " | ".join(fn(F[k]) for k in ks)
    def ok(rows): return f"{sum(r['ok'] for r in rows)}/{len(rows)}"
    def mean(rows, key): return round(float(np.mean([r[key] for r in rows])), 2)
    lines = [f"| gate | {' | '.join(G.NAMES[k] for k in ks)} |", "|---" * (len(ks) + 1) + "|"]
    for name, fn in [
        ("fish vs the tetra: shape + colour (G4 refgrade)", lambda f: f"{ok(f['fish_tetra'])} (shape {sum(r['shape_ok'] for r in f['fish_tetra'])}/5, colour {sum(r['colour_ok'] for r in f['fish_tetra'])}/5)"),
        ("  shape IoU / colour match (mean)", lambda f: f"{mean(f['fish_tetra'], 'iou')} / {mean(f['fish_tetra'], 'colour_match')}"),
        ("  cyan stripe recall (min over fish)", lambda f: str(min(next((v['recall'] for g, v in r['groups'].items() if g == 'kb_cyan'), 0.0) for r in f['fish_tetra']))),
        ("  red recall (min over fish)", lambda f: str(min(next((v['recall'] for g, v in r['groups'].items() if g == 'kb_red'), 0.0) for r in f['fish_tetra']))),
        ("fish vs the mockup koi: shape (refgrade, labels_FR_mockup)", lambda f: f"{ok(f['fish_mockup'])}, IoU {mean(f['fish_mockup'], 'iou')}"),
        ("fish vs tetra mask @0.82 (A14 fidelity, shape only)", lambda f: f"{f['fidelity']['fish']['ok']}/{f['fidelity']['fish']['n']}, IoU {f['fidelity']['fish']['mean_iou']}"),
        ("flora motif_match (A14)", lambda f: f"{f['fidelity']['flora']['ok']}/{f['fidelity']['flora']['n']}, IoU {f['fidelity']['flora']['mean_iou']}"),
        ("uncovered >= 25 mm2 vs mockup (A15)", lambda f: f"{f['fidelity']['uncovered']['n']} gaps, {f['fidelity']['uncovered']['mm2']} mm2"),
        ("orphan fragments", lambda f: str(f["orphans"]["n"])),
        ("direction OK / chaos", lambda f: f"{f['gates']['direction']['pct_ok']} % / {f['gates']['direction']['pct_chaos']} %"),
        ("density flags (p95)", lambda f: f"{f['gates']['density']['flags']} ({f['gates']['density']['p95']})"),
        ("trims /100 cm2", lambda f: f"{f['gates']['trims']['per_100cm2']} ({f['gates']['trims']['trims']} trims)"),
        ("stitches in crop", lambda f: f"{f['counts']['stitches_in_crop']:,}"),
        ("bench verdict", lambda f: f"{sum(map(bool, f['verdict'].values()))}/{len(f['verdict'])} ({', '.join(k for k, v in f['verdict'].items() if v)})"),
    ]:
        try: lines.append(f"| {name} | {c(fn)} |")
        except Exception as e: lines.append(f"| {name} | (n/a: {type(e).__name__} {e}) |")
    t = "\n".join(lines); open(os.path.join(HERE, "g4_table.md"), "w").write(t + "\n"); print(t)


if __name__ == "__main__":
    main()
