"""Register the close-ups onto the mockup (inputs/front.png) with a projective fit of SIFT matches (LESSONS A12).
closeup_front_right -> FR (image-left of the zip), closeup_front_left -> FL. Writes inputs/closeup_<P>_H.npy (close-up px -> front.png px)
and closeup_reg.json (matches, inliers, residual mm)."""
import glcore, json, numpy as np
from PIL import Image
from skimage.feature import SIFT, match_descriptors
from skimage.measure import ransac
from skimage.transform import ProjectiveTransform
import mockmap as MM
CROPS = {"FR": (90, 100, 385, 700), "FL": (365, 100, 660, 700)}
FILES = {"FR": "inputs/closeups/closeup_front_right.png", "FL": "inputs/closeups/closeup_front_left.png"}
CK = 3.0
def feat(a):
    l = a.mean(2); r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return np.clip((l - 0.25) * 1.6, 0, 1) * 0.8 + np.clip((g - r) * 2, 0, 1) * 0.4
def register(P):
    c = CROPS[P]; im = Image.open("inputs/front.png").convert("RGB").crop(c)
    A = np.array(im.resize((int((c[2]-c[0])*CK), int((c[3]-c[1])*CK)), Image.LANCZOS)).astype(float) / 255
    Bi = Image.open(FILES[P]).convert("RGB"); B = np.array(Bi).astype(float) / 255
    d1 = SIFT(); d1.detect_and_extract(feat(A)); d2 = SIFT(); d2.detect_and_extract(feat(B))
    m = match_descriptors(d2.descriptors, d1.descriptors, max_ratio=0.85, cross_check=True)
    src = d2.keypoints[m[:, 0]][:, ::-1]; dst = d1.keypoints[m[:, 1]][:, ::-1]
    model, inl = ransac((src, dst), ProjectiveTransform, min_samples=4, residual_threshold=6, max_trials=20000, rng=1)
    S = np.diag([1/CK, 1/CK, 1]); T = np.array([[1, 0, c[0]], [0, 1, c[1]], [0, 0, 1]])
    H = T @ S @ model.params                              # close-up px -> front.png px
    res = np.linalg.norm(model(src[inl]) - dst[inl], axis=1) / CK * MM.S
    np.save(f"inputs/closeup_{P}_H.npy", H)
    return dict(matches=int(len(m)), inliers=int(inl.sum()), resid_mm_median=round(float(np.median(res)), 2), resid_mm_p90=round(float(np.percentile(res, 90)), 2))
if __name__ == "__main__":
    info = {P: register(P) for P in ("FR", "FL")}
    json.dump(info, open("inputs/closeup_reg.json", "w"), indent=1); print(info)

def warp_mm(P, bbox, ppm):
    """close-up resampled into garment mm (size M): array HxWx3 (0-255) + valid mask"""
    from scipy.ndimage import map_coordinates
    H = np.linalg.inv(np.load(f"inputs/closeup_{P}_H.npy"))
    x0, y0, x1, y1 = bbox; W, Hh = int((x1-x0)*ppm), int((y1-y0)*ppm)
    XX, YY = np.meshgrid(x0 + (np.arange(W)+0.5)/ppm, y0 + (np.arange(Hh)+0.5)/ppm)
    fx, fy = MM.Pinv(XX, YY)
    w = H[2,0]*fx + H[2,1]*fy + H[2,2]; cx = (H[0,0]*fx + H[0,1]*fy + H[0,2])/w; cy = (H[1,0]*fx + H[1,1]*fy + H[1,2])/w
    B = np.array(Image.open(FILES[P]).convert("RGB")).astype(np.float32)
    out = np.zeros((Hh, W, 3), np.float32)
    for k in range(3): out[..., k] = map_coordinates(B[..., k], [cy, cx], order=1, mode="nearest")
    valid = (cx >= 0) & (cy >= 0) & (cx < B.shape[1]-1) & (cy < B.shape[0]-1)
    return out, valid
