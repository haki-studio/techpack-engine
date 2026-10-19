"""choose which panel edge is the sleeve fold: correlate the close-up mapping (both options) with the mockup warp per half"""
import cfcore, itertools
import numpy as np
import mockmap as MM, keepout as KO
from scipy import ndimage as ndi
MM.TPS_ON = False
for P in ("SR", "SL"):
    b = KO.panel("M", P).bounds; ppm = 1.0
    base = MM.warp(P, b, ppm, up=1)
    for view in ("front", "back"):
        res = {}
        for s in (1, -1):
            fs = dict(MM.SLEEVE_CU["fold_sign"]); fs[(P, view)] = s
            out = MM.sleeve_closeup(P, b, ppm, base.copy(), fold_sign=fs)
            H, W = base.shape[:2]; XX, YY = np.meshgrid(b[0] + np.arange(W) + .5, b[1] + np.arange(H) + .5)
            fr = (XX > 0) if P == "SR" else (XX < 0); m = fr if view == "front" else ~fr
            L1 = ndi.gaussian_filter(base.mean(2), 6)[m]; L2 = ndi.gaussian_filter(out.mean(2), 6)[m]
            res[s] = float(np.corrcoef(L1, L2)[0, 1])
        print(P, view, res, "->", max(res, key=res.get))
