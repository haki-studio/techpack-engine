"""The founder's tetra as THE Koi fish reference (founder 2026-10-22: "we want the tetra"; G3 wiring, G4 colour + windows).
For each pose in refmask.fish_ref("FR") (the reference tetra laid onto a mockup fish: the mockup gives position, heading
and count, the founder's 19 Oct decision gives size = 0.82 x the mockup fish length; input pixels only, A14) crop it to
its bbox and save RGBA bench/refs/tetra_<fishN>.png: RGB = the photo's own colours, alpha = the tetra mask. Its box is in
garment mm (bbox px / PPM + BB["FR"] origin, pixel EDGES so refgrade's resize lands back on the same pixels). Each pose
goes to the fish motif (labels_FR_mockup.json: the mockup's koi windows) it overlaps most.

G4: the session (the labeller) also reads the tetra's anatomy off the same template frame, so the fish LABELS follow the
tetra instead of the koi: t = 0 at the template snout .. 1 at its tail tip; the tail fin starts where the red stripe ends
(t >= TAIL_T, read off reference_fish.png), the eye is the darkest blob in the head (t < 0.3). Per fish it writes windows
(garment mm): `fish` (the whole tetra, GROW_MM out), `body` (t < TAIL_T), `tail` (t >= TAIL_T), the tail `root` seed and
the `eye` centre.

Writes bench/refs/tetra_refs.json {fishN: {image, box, windows: {fish, body, tail}, root, eye}}, read by labels_FR_src.py.
  cd projects/koi-blossom-hoodie && python3 bench/make_tetra_refs.py
(no Anthropic API calls)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); PROJ = os.path.dirname(HERE)
os.chdir(PROJ); sys.path.insert(0, PROJ)
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from shapely.geometry import Polygon
from shapely.ops import unary_union
from skimage import measure
import refmask as R

P = "FR"
TAIL_T = 0.80          # template: the red stripe ends and the caudal fin starts at 0.80 of snout -> tail tip
GROW_MM = 0.8          # windows reach a little past the picture, so a claim is never cut on its edge
EYE_LUM = 70           # the eye: photo pixels darker than this in the head (t < 0.3)


def poly(mask, origin):
    """largest component of a bool mask on the piece grid -> [[x, y], ...] garment mm, simplified 0.3 mm"""
    lab, n = ndi.label(mask)
    if not n: return None
    m = lab == 1 + int(np.argmax(np.bincount(lab.ravel())[1:]))
    c = max(measure.find_contours(np.pad(m, 1).astype(float), 0.5), key=len) - 1
    g = Polygon([(origin[0] + (x + 0.5) / R.PPM, origin[1] + (y + 0.5) / R.PPM) for y, x in c]).buffer(0).simplify(0.3)
    if g.geom_type != "Polygon": g = max(g.geoms, key=lambda q: q.area)
    return [[round(x, 2), round(y, 2)] for x, y in list(g.exterior.coords)[:-1]]


def centroid(mask, origin):
    ys, xs = np.nonzero(mask)
    return [round(origin[0] + (xs.mean() + 0.5) / R.PPM, 2), round(origin[1] + (ys.mean() + 0.5) / R.PPM, 2)]


def main():
    labels = json.load(open(os.path.join(HERE, "labels_FR_mockup.json")))
    fish = {m["id"]: unary_union([Polygon(w).buffer(0) for p in m["parts"] for w in p["hint"]["polygons"]])
            for m in labels["motifs"] if m["id"].startswith("fish")}
    win = {k: R.raster([g], P) for k, g in fish.items()}
    bb = R.BB[P]; best = {}
    for i, (pose, mm) in enumerate(R.fish_ref(P, sample=True)):
        ov = {k: int((mm & w).sum()) for k, w in win.items()}
        k = max(ov, key=ov.get)
        if ov[k] == 0: print(f"pose {i} at {np.round(pose['c'], 1).tolist()}: no fish window, skipped"); continue
        if k not in best or ov[k] > best[k][0]: best[k] = (ov[k], i, mm, pose)
    os.makedirs(os.path.join(HERE, "refs"), exist_ok=True); out = {}
    for k in sorted(best):
        _, i, mm, pose = best[k]; ys, xs = np.nonzero(mm); r0, r1, c0, c1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        crop = mm[r0:r1, c0:c1]; rgba = np.zeros(crop.shape + (4,), np.uint8)
        rgba[..., :3] = np.where(crop[..., None], pose["rgb"][r0:r1, c0:c1], 0).clip(0, 255).astype(np.uint8)
        rgba[..., 3] = np.where(crop, 255, 0)
        name = f"refs/tetra_{k}.png"; Image.fromarray(rgba, "RGBA").save(os.path.join(HERE, name))
        box = [round(float(v), 2) for v in (bb[0] + c0 / R.PPM, bb[1] + r0 / R.PPM, bb[0] + c1 / R.PPM, bb[1] + r1 / R.PPM)]
        t = pose["t"]
        dist, near = ndi.distance_transform_edt(~mm, return_indices=True)
        big = dist <= GROW_MM * R.PPM
        tt = t[near[0], near[1]]                                # t of the nearest fish pixel, so grown pixels take a side
        tail, body = big & (tt >= TAIL_T), big & (tt < TAIL_T)
        root = centroid(mm & (t >= TAIL_T) & (t < TAIL_T + 0.03), bb)
        lum = pose["rgb"].mean(-1); eye_m = mm & (t < 0.3) & (lum < EYE_LUM)
        lab, n = ndi.label(eye_m)
        eye = centroid(lab == 1 + int(np.argmax(np.bincount(lab.ravel())[1:])), bb) if n else None
        out[k] = dict(image=name, box=box, windows=dict(fish=poly(big, bb), body=poly(body, bb), tail=poly(tail, bb)), root=root, eye=eye)
        print(k, "pose", i, "overlap px", best[k][0], "box", box, "root", root, "eye", eye)
    json.dump(out, open(os.path.join(HERE, "refs/tetra_refs.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
