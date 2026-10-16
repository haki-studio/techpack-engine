import numpy as np
from scipy import ndimage as ndi
import stitchcheck as S
def metrics(text, font, h, target):
    ink0 = S.raster(text, font, h)
    dt = ndi.distance_transform_edt(ink0)
    sk = (dt >= ndi.maximum_filter(dt, size=3)) & (dt > 2)
    p10 = np.percentile(2 * dt[sk] / S.PXMM, 10)
    grow = max(0.0, (target - p10) / 2)
    ink = ndi.binary_dilation(ink0, structure=S.disk(2 * grow)) if grow > 0.01 else ink0
    thin = ink & ~ndi.binary_opening(ink, structure=S.disk(S.MIN_STROKE))
    # enclosed counters
    bg = ~ink
    lab, n = ndi.label(bg)
    border = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    bdt = ndi.distance_transform_edt(bg)
    holes = [2 * bdt[lab == i].max() / S.PXMM for i in range(1, n + 1) if i not in border]
    # strokes merging under MIN_GAP closing
    n_before = ndi.label(ink)[1]
    n_after = ndi.label(ndi.binary_closing(ink, structure=S.disk(S.MIN_GAP)) | ink)[1]
    return dict(p10=p10, grow=grow, thin=100 * thin.sum() / ink.sum(),
                hole_min=min(holes) if holes else None, holes=len(holes), merges=n_before - n_after)
