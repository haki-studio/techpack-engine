"""Register the founder's close-ups (inputs/closeups/, 20 Oct 2026) onto the mockup views (LESSONS A12; founder rule: the
MOCKUP governs what / where / how many, close-ups only inform detail inside each motif).

Each close-up (or quadrant of the 2x2 sleeve composite) is matched to inputs/back.png or front.png with SIFT + RANSAC
(homography, 4 render-px tolerance on a 3x upscaled render). The close-ups turn out to be super-resolved crops of the same
render: the fits are pure scale + shift with 92-98 % inliers, so they line up with the mockup pixel for pixel.
A fit is only accepted with >= 100 inliers and >= 80 % of the matches; the overlay is written for a visual check.
Runs on the system python (OpenCV), not the engine env:  python3 register_closeups.py  ->  cu_regs.json + out/trace/cureg_<name>.png"""
import json, os
import numpy as np
import cv2
from PIL import Image

CU = [  # name, file, crop [x0, y0, x1, y1] in the file (None = whole), view
    ("back", "inputs/closeups/closeup_back.png", None, "back"),
    ("front_left", "inputs/closeups/closeup_front_left.png", None, "front"),
    ("front_right", "inputs/closeups/closeup_front_right.png", None, "front"),
    ("sleeve_SR_front", "inputs/closeups/closeup_sleeves.png", [0, 0, 1572, 1692], "front"),      # composite TL
    ("sleeve_SL_front", "inputs/closeups/closeup_sleeves.png", [1628, 0, 3200, 1692], "front"),   # TR
    ("sleeve_SL_back", "inputs/closeups/closeup_sleeves.png", [0, 1728, 1572, 3420], "back"),     # BL
    ("sleeve_SR_back", "inputs/closeups/closeup_sleeves.png", [1628, 1728, 3200, 3420], "back"),  # BR
]

def fit(cu, view):
    V = np.asarray(Image.open(f"inputs/{view}.png").convert("RGB"))
    up = 3; Vb = cv2.resize(V, None, fx=up, fy=up, interpolation=cv2.INTER_CUBIC)
    k = 0.35; Cs = cv2.resize(cu, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    s = cv2.SIFT_create(nfeatures=8000); g = lambda a: cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)
    ka, da = s.detectAndCompute(g(Cs), None); kb, db = s.detectAndCompute(g(Vb), None)
    good = [a for a, b in cv2.BFMatcher().knnMatch(da, db, k=2) if a.distance < 0.8 * b.distance]
    src = np.float32([ka[a.queryIdx].pt for a in good]) / k; dst = np.float32([kb[a.trainIdx].pt for a in good]) / up
    H, inl = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
    return H, len(good), int(inl.sum()), V

if __name__ == "__main__":
    os.makedirs("out/trace", exist_ok=True); out = []
    for name, f, crop, view in CU:
        a = np.asarray(Image.open(f).convert("RGB"))
        if crop: a = a[crop[1]:crop[3], crop[0]:crop[2]]
        H, n, ni, V = fit(a, view)
        ok = ni >= 100 and ni >= 0.8 * n
        h, w = a.shape[:2]
        corners = cv2.perspectiveTransform(np.float32([[[0, 0]], [[w, 0]], [[w, h]], [[0, h]]]), H).reshape(-1, 2)
        sc = float(np.sqrt(abs(np.linalg.det(H[:2, :2]))))
        out.append(dict(name=name, file=f, crop=crop, view=view, H=H.tolist(), matches=n, inliers=ni, ok=ok,
                        cu_px_per_render_px=round(1 / sc, 2), footprint_render_px=[[round(float(x), 1), round(float(y), 1)] for x, y in corners]))
        print(name, view, "matches", n, "inliers", ni, "ok", ok, "close-up px per render px", round(1 / sc, 2), flush=True)
        # overlay check: close-up warped into the render frame, blended 50 %
        Wp = cv2.warpPerspective(a, H, (V.shape[1], V.shape[0]))
        m = cv2.warpPerspective(np.ones(a.shape[:2], np.uint8), H, (V.shape[1], V.shape[0])) > 0
        ov = V.copy(); ov[m] = (0.5 * V[m] + 0.5 * Wp[m]).astype(np.uint8)
        x0, y0 = np.floor(corners.min(0)).astype(int).clip(0); x1, y1 = np.ceil(corners.max(0)).astype(int)
        strip = np.concatenate([V[y0:y1, x0:x1], Wp[y0:y1, x0:x1], ov[y0:y1, x0:x1]], 1)
        Image.fromarray(strip).resize((strip.shape[1] * 3, strip.shape[0] * 3), Image.LANCZOS).save(f"out/trace/cureg_{name}.png")
    json.dump(out, open("cu_regs.json", "w"), indent=1)
