"""The reference per motif family, built from the INPUT PIXELS ONLY (LESSONS A14; inputs/front.png = left half of
inputs/flat.png, inputs/closeup_mockup_head.png = its right half): from_inputs() re-runs the colour classification of
trace.py on the input images themselves (no art, no scene data, no trace_M.npz, no hand-drawn motif polygon - the Rev B2
MOUTH fill is gone; the only polygons are GARMENT-detail masks: hood, welt edges, studio background, A15) and caches it
with the sha1 of the three input images. The art builder reads the same classification (trace_M.npz written by trace.py).
Original note: the TRACED reference per motif family on the trace grid (trace_M.npz, 4 px/mm) - one definition shared by the art
builder (scene.py: objects stay on these silhouettes and keep separate motifs separate) and the A14/A15 gates (qa_gates.py).
  3x3 majority vote of the trace labels, 2x2 opening (pixel noise), and in the black ground the enclosed fabric specks
  < 25 mm2 count as black (thread highlights of the close-up read as fabric; scene.fill_ground) - documented, not hidden."""
import numpy as np
from scipy import ndimage as ndi

FAMILY_CODES = {"cream": (4,), "red": (1, 2), "black": (3,)}

def majority(lab):
    cnt = np.stack([ndi.uniform_filter((lab == k).astype(np.float32), 3) for k in range(10)], 0)
    return np.argmax(cnt, 0).astype(np.uint8)

def fill_specks(lab, ppm, max_mm2=25.0):
    art = (lab >= 1) & (lab <= 4)
    holes = ndi.binary_fill_holes(art) & ~art & (lab == 0)
    hl, n = ndi.label(holes)
    if n:
        sz = ndi.sum(np.ones_like(hl), hl, index=np.arange(1, n + 1)) / ppm**2
        lab = lab.copy(); lab[np.isin(hl, 1 + np.nonzero(sz < max_mm2)[0])] = 3
    return lab

def reference(raw, ppm, space="F", speck_mm2=8.0, gap_mm=1.5):
    lab = majority(raw)
    if space == "F": lab = fill_specks(lab, ppm)
    ref = {f: ndi.binary_opening(np.isin(lab, c), structure=np.ones((2, 2))) for f, c in FAMILY_CODES.items()}
    # review item 7 / A8: isolated specks on bare fabric (cluster < 8 mm2, nothing within 1.5 mm) are render noise, not
    # motifs - the art builder drops them too (scene.drop_specks), so the gate does not count them
    allm = np.zeros(lab.shape, bool)
    for m in ref.values(): allm |= m
    cl, n = ndi.label(ndi.binary_dilation(allm, iterations=int(round(gap_mm*ppm/2))))
    if n:
        a = ndi.sum(allm, cl, index=np.arange(1, n + 1)) / ppm**2
        small = np.isin(cl, 1 + np.nonzero(a < speck_mm2)[0])
        ref = {f: m & ~small for f, m in ref.items()}
    return ref

def separation_cut(ref):
    """pixels on the border between the Voronoi cells of DIFFERENT reference motifs (one family): removing them keeps
    two traced motifs apart (a 0.75 mm cut) where the rebuilt objects + pull comp would otherwise bridge them"""
    lb, n = ndi.label(ref)
    if n < 2: return np.zeros(ref.shape, bool)
    _, (iy, ix) = ndi.distance_transform_edt(lb == 0, return_indices=True)
    near = lb[iy, ix]
    mx = ndi.maximum_filter(near, 3); mn = ndi.minimum_filter(near, 3)
    return ndi.binary_dilation(mx != mn)          # 3 px (0.75 mm) wide: survives pull comp + the gate's pull-in model


import hashlib, os
INPUTS = ("inputs/front.png", "inputs/flat.png", "inputs/closeup_mockup_head.png")
def input_hash():
    h = hashlib.sha1()
    for p in INPUTS: h.update(open(p, "rb").read())
    return h.hexdigest()

def from_inputs(space):
    """raw label raster of `space` (F / SR / SL) classified directly from the input images (cached by input hash)"""
    import trace as TR
    cache = f"out/refmask_{space}.npz"; hx = input_hash()
    if os.path.exists(cache):
        z = np.load(cache)
        if str(z["hash"]) == hx: return z["lab"]
    lab = TR.trace_front()[0] if space == "F" else TR.trace_sleeve(space[1])[0]
    os.makedirs("out", exist_ok=True); np.savez_compressed(cache, lab=lab, hash=hx)
    return lab
