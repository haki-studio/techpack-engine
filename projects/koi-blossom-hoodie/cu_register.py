"""Register the close-up (inputs/closeup_mockup_koi.png, 676 x 1088 px) onto the mockup FR upper panel (LESSONS A12).
Matched features (picked on gridded zooms of both images): the two lily centres + head and tail tip of the 4 close-up koi.
The koi assignment is the permutation with the smallest residual (brute force over the 6 FR koi of the mockup).
A global affine and a projective (DLT) fit are both reported. Result: the close-up drifted (mean residual ~12 mockup px
≈ 13 mm, one koi of the mockup is missing in it), so placement stays on the mockup (techpack-pipeline §0b) and every
close-up motif is registered ON ITS OWN onto its mockup counterpart (similarity: centre, heading, size) — that per-motif
transform is what cu_trace / scene / compare use.  Output: trace/closeup_reg.json + out/closeup_registration.png
usage: python3 cu_register.py"""
import json, itertools, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

CU_KOI = [((305, 232), (170, 105)), ((445, 425), (265, 330)), ((455, 665), (310, 480)), ((645, 850), (485, 735))]   # head, tail tip
MK_KOI = [((255, 371), (201, 344)), ((286, 424), (245, 395)), ((343, 483), (297, 450)), ((283, 499), (215, 465)),
          ((322, 565), (277, 515)), ((335, 703), (286, 663))]                                                # scene.KOI 0-5 (FR)
CU_FL = [(95, 415), (250, 680)]          # lily centres (close-up)
MK_FL = [(195, 438), (222, 500)]          # scene FR_vine flower 0 (big pale), flower 1 (mid)

def affine(A, B):
    A = np.asarray(A, float); B = np.asarray(B, float); M = np.c_[A, np.ones(len(A))]
    X = np.linalg.lstsq(M, B, rcond=None)[0]; return X, np.hypot(*(M @ X - B).T)

def homography(A, B):
    rows = []
    for (x, y), (u, v) in zip(A, B):
        rows += [[x, y, 1, 0, 0, 0, -u*x, -u*y, -u], [0, 0, 0, x, y, 1, -v*x, -v*y, -v]]
    H = np.linalg.svd(np.array(rows, float))[2][-1].reshape(3, 3); H /= H[2, 2]
    Q = np.c_[np.asarray(A, float), np.ones(len(A))] @ H.T
    return H, np.hypot(*(Q[:, :2] / Q[:, 2:] - np.asarray(B, float)).T)

def similarity(a0, a1, b0, b1):
    """close-up segment a0->a1 onto mockup segment b0->b1: returns (scale, rot_deg, tx, ty) with p' = s R p + t"""
    a0, a1, b0, b1 = map(lambda v: np.asarray(v, float), (a0, a1, b0, b1))
    da, db = a1 - a0, b1 - b0
    s = np.linalg.norm(db) / np.linalg.norm(da); th = np.arctan2(db[1], db[0]) - np.arctan2(da[1], da[0])
    R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]]); t = b0 - s * R @ a0
    return dict(s=float(s), rot=float(np.degrees(th)), t=t.tolist())

if __name__ == "__main__":
    best = None
    for perm in itertools.permutations(range(len(MK_KOI)), len(CU_KOI)):
        A = list(CU_FL) + [p for k in CU_KOI for p in k]; B = list(MK_FL) + [p for j in perm for p in MK_KOI[j]]
        r = affine(A, B)[1].mean()
        if best is None or r < best[0]: best = (r, perm)
    perm = best[1]
    A = list(CU_FL) + [p for k in CU_KOI for p in k]; B = list(MK_FL) + [p for j in perm for p in MK_KOI[j]]
    X, ra = affine(A, B); H, rh = homography(A, B)
    import mockmap as MM
    mm = lambda r: float(r * MM.S)
    out = dict(features=dict(closeup=A, mockup=B, labels=["lily0", "lily1"] + [f"koi{j}_{e}" for j in perm for e in ("head", "tail")]),
               koi_match={f"cu_koi{i}": f"koi{j}" for i, j in enumerate(perm)},
               missing_in_closeup=[f"koi{j}" for j in range(len(MK_KOI)) if j not in perm],
               affine=dict(X=X.tolist(), resid_px=ra.round(1).tolist(), mean_px=round(float(ra.mean()), 1), mean_mm=round(mm(ra.mean()), 1), max_mm=round(mm(ra.max()), 1)),
               projective=dict(H=H.tolist(), resid_px=rh.round(1).tolist(), mean_px=round(float(rh.mean()), 1), mean_mm=round(mm(rh.mean()), 1), max_mm=round(mm(rh.max()), 1)),
               close_up_mm_per_px=round(float(MM.S * np.sqrt(abs(np.linalg.det(X[:2])))), 3),
               decision="global fit residual too large to take positions from the close-up (generator drift): positions + sizes from the mockup, "
                        "motif structure (petal outlines, tone regions, koi silhouettes, red patches, fins, tails) from the close-up, each motif registered on its own",
               per_motif={})
    for i, j in enumerate(perm):
        out["per_motif"][f"cu_koi{i}"] = dict(target=f"koi{j}", **similarity(CU_KOI[i][1], CU_KOI[i][0], MK_KOI[j][1], MK_KOI[j][0]))
    json.dump(out, open("trace/closeup_reg.json", "w"), indent=1)
    # overlay: close-up warped onto the mockup crop by the projective fit, features + residual vectors
    mk = Image.open("inputs/front.png").convert("RGB"); cu = Image.open("inputs/closeup_mockup_koi.png").convert("RGB")
    Hi = np.linalg.inv(H); Hi /= Hi[2, 2]
    warped = cu.transform(mk.size, Image.PERSPECTIVE, tuple(Hi.flatten()[:8]), Image.BILINEAR)
    wm = Image.new("L", cu.size, 255).transform(mk.size, Image.PERSPECTIVE, tuple(Hi.flatten()[:8]))
    blend = Image.composite(Image.blend(mk, warped, 0.6), mk, wm)
    box = (120, 300, 380, 640); sc = 3
    side = [im.crop(box).resize(((box[2]-box[0])*sc, (box[3]-box[1])*sc), Image.LANCZOS) for im in (mk, blend)]
    W, Hh = side[0].size; sheet = Image.new("RGB", (W*2 + 20, Hh + 50), "white"); d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", 18)
    for k, im in enumerate(side): sheet.paste(im, (k*(W + 20), 50))
    Q = np.c_[np.asarray(A, float), np.ones(len(A))] @ H.T; P = Q[:, :2] / Q[:, 2:]
    for (bx, by), (px, py) in zip(B, P):
        for ox in (0, W + 20):
            u = lambda x, y: (ox + (x - box[0])*sc, 50 + (y - box[1])*sc)
            d.ellipse([*(np.array(u(bx, by)) - 5), *(np.array(u(bx, by)) + 5)], outline=(255, 255, 0), width=2)
            d.line([u(bx, by), u(px, py)], fill=(255, 60, 60), width=3)
    d.text((10, 8), f"Close-up registration: mockup FR upper | close-up warped on it (projective, 10 features). Yellow = mockup feature, red = where the "
                     f"close-up puts it. Mean {out["projective"]["mean_mm"]} mm, max {out["projective"]["max_mm"]} mm.", fill="black", font=f)
    sheet.save("out/closeup_registration.png")
    print(json.dumps({k: out[k] for k in ("koi_match", "missing_in_closeup", "close_up_mm_per_px")}), out["affine"]["mean_mm"], out["projective"]["mean_mm"], out["projective"]["max_mm"])
