"""Fix round 3 (PR #27 review 2 item 3, LESSONS A16): the stripe rows follow the founder close-ups' VISIBLE THREAD GRAIN
where a close-up covers the stripe and shows a clear grain; elsewhere the geometric flow field (flowdir.build_field).

The grain is read from input pixels only: the close-up at 12 px/mm through the same map + seam warp as the A14/A16
references (gates.ref_classes + gates.closeup_grey12), structure tensor at the gate's 8 mm tile scale (threads run across
the intensity gradient, as qa.direction_match reads it). Output per piece (grain_M_<P>.npz, 1 mm grid): thread angle
(deg, garment mm, y down), coherence, close-up weight (share of close-up pixels within 4 mm). flowdir.wv_parts uses the
grain where weight >= 0.6 and coherence >= 0.3, else the geometric field.
usage: ./py.sh grainfield.py [M]   (after the art chain: the warp it reads comes from art_M.pkl)"""
import sys
sys.argv.append("--nodir")
import numpy as np
from scipy import ndimage as ndi
from scipy.ndimage import zoom
import gates as G, wavecore as WC

SIZE = "M"; UP = 3; TILE = 8.0
for P in WC.PIECES:
    cls, bb = G.ref_classes(P)
    g = G.GREY.get(P)
    g = np.where(np.isfinite(g), g, np.nanmean(g))
    g12 = zoom(g, UP, order=1); P12 = G.PPM * UP
    cg, cw = G.closeup_grey12(P, g12.shape, UP)
    g12 = np.where(cw > 0, cg, g12)
    gy, gx = np.gradient(ndi.gaussian_filter(g12, 0.6)); st = int(P12)          # 1 mm grid
    def field(tile):
        sig = tile * P12 / 3.0
        Jxx = ndi.gaussian_filter(gx * gx, sig); Jyy = ndi.gaussian_filter(gy * gy, sig); Jxy = ndi.gaussian_filter(gx * gy, sig)
        jxx, jyy, jxy = Jxx[st // 2::st, st // 2::st], Jyy[st // 2::st, st // 2::st], Jxy[st // 2::st, st // 2::st]
        tr = jxx + jyy; coh = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / np.maximum(tr, 1e-9)
        return np.degrees(0.5 * np.arctan2(2 * jxy, jxx - jyy) + np.pi / 2), coh
    ang, coh = field(TILE); ang4, coh4 = field(4.0)          # 8 mm = the stripe tiles of the gate, 4 mm = drops / foam
    w = ndi.uniform_filter(cw.astype(np.float32), size=int(TILE * P12))[st // 2::st, st // 2::st]
    np.savez_compressed(f"grain_{SIZE}_{P}.npz", ang=ang.astype(np.float32), coh=coh.astype(np.float32), w=w.astype(np.float32),
                        ang4=ang4.astype(np.float32), coh4=coh4.astype(np.float32),
                        x0=bb[0], y0=bb[1], step=1.0)
    use = (w >= 0.6) & (coh >= 0.3)
    print(P, ang.shape, "close-up share", round(float((w >= 0.6).mean()), 3), "usable grain", round(float(use.mean()), 3), flush=True)
