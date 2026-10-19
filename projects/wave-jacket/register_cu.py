"""Register inputs/closeup_mockup_foam.png (founder's detail close-up of the wearer's-left shoulder crest) onto the
front render (LESSONS A12): similarity search (rotation, scale, shift) maximising the overlap of the foam (white) and
band (blue) masks, then a projective refinement on the same score. Output: cu_reg.json {H: 3x3 close-up px -> render px}
+ out/trace/closeup_registration.png (render | warped close-up | overlay)."""
import json, math, sys
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.optimize import minimize
import trace as TR

CU = np.asarray(Image.open("inputs/closeup_mockup_foam.png").convert("RGB")).astype(float)
FR = np.asarray(Image.open("inputs/front.png").convert("RGB")).astype(float)
def masks(a):
    L = TR.lab_img(a); white = (L[..., 0] > 72) & (np.hypot(L[..., 1], L[..., 2]) < 14)
    blue = (L[..., 2] < -28) & (L[..., 0] > 15)
    return white.astype(float), blue.astype(float)
# render region of the crest (px) and its masks
BOX = (330, 170, 620, 520)
fw, fb = masks(FR[BOX[1]:BOX[3], BOX[0]:BOX[2]])
fw, fb = ndi.gaussian_filter(fw, 1.0), ndi.gaussian_filter(fb, 1.0)
cw, cb = masks(CU)
cw, cb = ndi.gaussian_filter(cw, 3.0), ndi.gaussian_filter(cb, 3.0)
H_, W_ = fw.shape
YY, XX = np.mgrid[0:H_, 0:W_]; RX, RY = XX + BOX[0], YY + BOX[1]

def warp_inv(H):
    """sample close-up masks at render px through H^-1 (render -> close-up)"""
    Hi = np.linalg.inv(H); P = np.stack([RX.ravel(), RY.ravel(), np.ones(RX.size)])
    q = Hi @ P; u, v = q[0] / q[2], q[1] / q[2]
    inside = (u >= 0) & (u < CU.shape[1] - 1) & (v >= 0) & (v < CU.shape[0] - 1)
    sw = ndi.map_coordinates(cw, [v, u], order=1, mode="constant").reshape(H_, W_)
    sb = ndi.map_coordinates(cb, [v, u], order=1, mode="constant").reshape(H_, W_)
    return sw, sb, inside.reshape(H_, W_)

def score(H):
    sw, sb, ins = warp_inv(H)
    if ins.sum() < 2000: return 0.0
    def ncc(a, b):
        a = a[ins]; b = b[ins]; a = a - a.mean(); b = b - b.mean()
        return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9))
    return ncc(sw, fw) + ncc(sb, fb)

def sim(theta, s, tx, ty):
    c, d = math.cos(theta) * s, math.sin(theta) * s
    return np.array([[c, -d, tx], [d, c, ty], [0, 0, 1.0]])

best = (-9, None)
cx, cy = CU.shape[1] / 2, CU.shape[0] / 2
for th in np.radians(np.arange(10, 75, 5)):
    for s in (0.18, 0.21, 0.24, 0.27, 0.30, 0.34):
        for X in range(370, 560, 10):
            for Y in range(220, 440, 10):
                # centre of the close-up lands at (X, Y)
                c, d = math.cos(th) * s, math.sin(th) * s
                H = sim(th, s, X - (c * cx - d * cy), Y - (d * cx + c * cy))
                sc = score(H)
                if sc > best[0]: best = (sc, H)
print("coarse", round(best[0], 3), flush=True)
p0 = best[1][:2].ravel()
res = minimize(lambda p: -score(np.r_[p, [0, 0, 1]].reshape(3, 3)), p0, method="Powell", options=dict(maxiter=4000, xtol=1e-4, ftol=1e-5))
H = np.r_[res.x, [0, 0, 1]].reshape(3, 3); sc = score(H)
print("refined affine", round(sc, 3), flush=True)
p0 = H.ravel()[:8]
res = minimize(lambda p: -score(np.r_[p, 1].reshape(3, 3)), p0, method="Powell", options=dict(maxiter=4000))
Hp = np.r_[res.x, 1].reshape(3, 3); scp = score(Hp)
if scp > sc + 0.01: H, sc = Hp, scp
print("final", round(sc, 3))
json.dump(dict(H=H.tolist(), score=sc, box=BOX), open("cu_reg.json", "w"), indent=1)
# visual check
sw, sb, ins = warp_inv(H)
Hi = np.linalg.inv(H); P = np.stack([RX.ravel(), RY.ravel(), np.ones(RX.size)]); q = Hi @ P; u, v = q[0] / q[2], q[1] / q[2]
warped = np.stack([ndi.map_coordinates(CU[..., k], [v, u], order=1, mode="constant", cval=255).reshape(H_, W_) for k in range(3)], -1)
reg = FR[BOX[1]:BOX[3], BOX[0]:BOX[2]]
ov = reg.copy(); ov[ins] = 0.5 * reg[ins] + 0.5 * warped[ins]
out = np.concatenate([reg, warped, ov], 1).clip(0, 255).astype(np.uint8)
Image.fromarray(out).resize((out.shape[1] * 2, out.shape[0] * 2), Image.LANCZOS).save("out/trace/closeup_registration.png")
