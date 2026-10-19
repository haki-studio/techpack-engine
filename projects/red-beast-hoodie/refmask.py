"""The TRACED reference per motif family on the trace grid (trace_M.npz, 4 px/mm) - one definition shared by the art
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
