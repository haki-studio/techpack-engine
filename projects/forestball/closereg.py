"""Register close-ups onto the mockup panels with a projective fit of SIFT matches (LESSONS A12; after grand-line closereg).
BACK  <- inputs/closeups/closeup_front_right_a.png (this file shows the BACK scene)  onto inputs/back.png
02R   <- inputs/closeups/closeup_front_right_b.png  onto inputs/front.png (wearer's right panel, left of the zip)
Writes inputs/closeup_<P>_H.npy (close-up px -> mockup px) + inputs/closeup_reg.json."""
import json, sys, numpy as np
from PIL import Image
from skimage.feature import SIFT, match_descriptors
from skimage.measure import ransac
from skimage.transform import ProjectiveTransform
REG = {"BACK": ("inputs/closeups/closeup_front_right_a.png", "inputs/back.png", (60, 60, 680, 720)),
       "02R": ("inputs/closeups/closeup_front_right_b.png", "inputs/front.png", (60, 60, 400, 520))}
CK = 3.0
def feat(a):
    l = a.mean(2); r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return np.clip((l - 0.15) * 1.8, 0, 1) * 0.8 + np.clip((g - r) * 2, 0, 1) * 0.3 + np.clip((b - r) * 2, 0, 1) * 0.3
def register(P):
    cf, mf, c = REG[P]
    im = Image.open(mf).convert("RGB").crop(c)
    A = np.array(im.resize((int((c[2]-c[0])*CK), int((c[3]-c[1])*CK)), Image.LANCZOS)).astype(float) / 255
    Bi = Image.open(cf).convert("RGB"); sB = 1.0
    if max(Bi.size) > 1300: sB = 1300 / max(Bi.size); Bi = Bi.resize((int(Bi.width*sB), int(Bi.height*sB)), Image.LANCZOS)
    B = np.array(Bi).astype(float) / 255
    d1 = SIFT(); d1.detect_and_extract(feat(A)); d2 = SIFT(); d2.detect_and_extract(feat(B))
    m = match_descriptors(d2.descriptors, d1.descriptors, max_ratio=0.85, cross_check=True)
    src = d2.keypoints[m[:, 0]][:, ::-1]; dst = d1.keypoints[m[:, 1]][:, ::-1]
    model, inl = ransac((src, dst), ProjectiveTransform, min_samples=4, residual_threshold=8, max_trials=30000, rng=1)
    S = np.diag([1/CK, 1/CK, 1]); T = np.array([[1, 0, c[0]], [0, 1, c[1]], [0, 0, 1]]); SB_ = np.diag([sB, sB, 1])
    H = T @ S @ model.params @ SB_                      # close-up px -> mockup px
    res = np.linalg.norm(model(src[inl]) - dst[inl], axis=1) / CK      # mockup px (~1 mm)
    np.save(f"inputs/closeup_{P}_H.npy", H)
    return dict(matches=int(len(m)), inliers=int(inl.sum()), resid_px_median=round(float(np.median(res)), 2), resid_px_p90=round(float(np.percentile(res, 90)), 2))
if __name__ == "__main__":
    info = {P: register(P) for P in (sys.argv[1:] or REG)}
    json.dump(info, open("inputs/closeup_reg.json", "w"), indent=1); print(info)
