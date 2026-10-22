"""ENGINE_PLAN G3 (D2, Koi side): the founder's tetra as per-fish labels references.
For each pose in refmask.fish_ref("FR") (the reference tetra laid onto a mockup fish at 0.82 x its length, input pixels
only, A14) crop the mask to its bbox and save it as RGBA bench/refs/tetra_<fishN>.png (alpha = mask), with its box in
garment mm (bbox px / PPM + BB["FR"] origin, pixel EDGES so refgrade's resize lands back on the same pixels). Each pose
goes to the labels fish motif whose windows (all its parts' polygons) it overlaps most. Writes bench/refs/tetra_refs.json
{fishN: {image, box}}, which labels_FR_src.py --fish-ref tetra reads.

  cd projects/koi-blossom-hoodie && python3 bench/make_tetra_refs.py
(no Anthropic API calls)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); PROJ = os.path.dirname(HERE)
os.chdir(PROJ); sys.path.insert(0, PROJ)
import numpy as np
from PIL import Image
from shapely.geometry import Polygon
from shapely.ops import unary_union
import refmask as R

P = "FR"


def main():
    labels = json.load(open(os.path.join(HERE, "labels_FR.json")))
    fish = {m["id"]: unary_union([Polygon(w).buffer(0) for p in m["parts"] for w in p["hint"]["polygons"]])
            for m in labels["motifs"] if m["id"].startswith("fish")}
    win = {k: R.raster([g], P) for k, g in fish.items()}
    bb = R.BB[P]; best = {}
    for i, (pose, mm) in enumerate(R.fish_ref(P)):
        ov = {k: int((mm & w).sum()) for k, w in win.items()}
        k = max(ov, key=ov.get)
        if ov[k] == 0: print(f"pose {i} at {np.round(pose['c'], 1).tolist()}: no fish window, skipped"); continue
        if k not in best or ov[k] > best[k][0]: best[k] = (ov[k], i, mm)
    os.makedirs(os.path.join(HERE, "refs"), exist_ok=True); out = {}
    for k in sorted(best):
        _, i, mm = best[k]; ys, xs = np.nonzero(mm); r0, r1, c0, c1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        crop = mm[r0:r1, c0:c1]; rgba = np.zeros(crop.shape + (4,), np.uint8); rgba[crop] = (255, 255, 255, 255)
        name = f"refs/tetra_{k}.png"; Image.fromarray(rgba, "RGBA").save(os.path.join(HERE, name))
        box = [round(float(v), 2) for v in (bb[0] + c0 / R.PPM, bb[1] + r0 / R.PPM, bb[0] + c1 / R.PPM, bb[1] + r1 / R.PPM)]
        out[k] = dict(image=name, box=box); print(k, "pose", i, "overlap px", best[k][0], "box", box)
    json.dump(out, open(os.path.join(HERE, "refs/tetra_refs.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
