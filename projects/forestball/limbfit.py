"""02R placement of close-up b (Rev C): b has drifted from the mockup (coordinator), so it is placed by fitting its LIMB
centreline onto the mockup's limb centreline (both extracted automatically: dark blue/navy limb mass, per-column median),
matched by normalised arc length -> least-squares projective fit. Writes inputs/closeup_02R_H.npy + limbfit.json."""
import json, numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.transform import ProjectiveTransform
def limb_mask(a, black=True):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]; l = a.mean(2)
    m = ((b > r + 0.06) & (l < 0.45)) | ((l < 0.13) if black else False)
    m = ndi.binary_opening(m, iterations=2); m = ndi.binary_closing(m, iterations=4)
    lab, n = ndi.label(m); sz = ndi.sum(m, lab, range(1, n+1)); return lab == (1 + int(np.argmax(sz)))
def centre(m, xs):
    pts = []
    for x in xs:
        ys = np.nonzero(m[:, x])[0]
        if len(ys) > 3: pts.append((x, float(np.median(ys)), float(ys.max() - ys.min())))
    return np.array(pts)
B = np.asarray(Image.open("inputs/closeups/closeup_front_right_b.png").convert("RGB")).astype(float) / 255
M = np.asarray(Image.open("inputs/front.png").convert("RGB")).astype(float) / 255
mb = limb_mask(B[:, 150:])                     # skip the hanging-moss strip at the far left of b
cb = centre(mb, range(0, B.shape[1] - 150, 8)); cb[:, 0] += 150
sub = M[100:380, 180:372]; mm = limb_mask(sub, black=False)
cm = centre(mm, range(0, sub.shape[1], 2)); cm[:, 0] += 180; cm[:, 1] += 100
def arc(c): d = np.r_[0, np.cumsum(np.hypot(np.diff(c[:, 0]), np.diff(c[:, 1])))]; return d / d[-1]
ab, am = arc(cb), arc(cm); t = np.linspace(0.03, 0.97, 25)
src = np.c_[np.interp(t, ab, cb[:, 0]), np.interp(t, ab, cb[:, 1])]; dst = np.c_[np.interp(t, am, cm[:, 0]), np.interp(t, am, cm[:, 1])]
wb = np.interp(t, ab, cb[:, 2]); wm = np.interp(t, am, cm[:, 2])
# width pairs: points offset across the limb (normal) so the fit also matches the limb thickness
def nrm(c, tt, a):
    x = np.interp(tt, a, c[:, 0]); y = np.interp(tt, a, c[:, 1]); d = np.gradient(np.c_[x, y], axis=0); d /= np.linalg.norm(d, axis=1)[:, None]
    return np.c_[-d[:, 1], d[:, 0]]
nb, nm_ = nrm(cb, t, ab), nrm(cm, t, am)
S = np.r_[src, src + nb * wb[:, None] * 0.35, src - nb * wb[:, None] * 0.35]
D = np.r_[dst, dst + nm_ * wm[:, None] * 0.35, dst - nm_ * wm[:, None] * 0.35]
T = ProjectiveTransform(); T.estimate(S, D)
res = np.linalg.norm(T(S) - D, axis=1)
np.save("inputs/closeup_02R_H.npy", T.params)
json.dump(dict(pairs=len(S), resid_px_median=round(float(np.median(res)), 2), resid_px_p90=round(float(np.percentile(res, 90)), 2),
               limb_width_b_px=round(float(np.median(wb)), 1), limb_width_mockup_px=round(float(np.median(wm)), 1)), open("limbfit.json", "w"), indent=1)
print(open("limbfit.json").read())
if __name__ == "__main__":
    from PIL import ImageDraw
    a = Image.fromarray((mm*255).astype(np.uint8)).convert("RGB").resize((sub.shape[1]*3, sub.shape[0]*3)); d = ImageDraw.Draw(a)
    for x, y, w in cm: d.ellipse([(x-180)*3-2, (y-100)*3-2, (x-180)*3+2, (y-100)*3+2], fill=(255, 0, 0))
    b = Image.fromarray((mb*255).astype(np.uint8)).convert("RGB").resize((400, 500)); a.save("out/art/lf_m.png"); b.save("out/art/lf_b.png")
