"""Rev C light rays TRACED from the registered close-up a (back): ray pixels = light, low-saturation sage/cream pixels on
open fabric. Ray direction = the angle with the sharpest across-ray histogram; bands = runs of that histogram above a
threshold (>= 12 mm wide); each band's along-ray extent per 10 mm step from the 10th/90th percentile of its pixels, so the
bands keep their real taper and length (they run across the limb + rocks: the overlay is extended through art gaps).
-> rays_trace.json: [{"angle", "pts": [[x, y]...], "w_mean"}] in size-M garment mm."""
import json, math, numpy as np
from PIL import Image
from scipy import ndimage as ndi
import fbcore, back as B
import trace_fb as T
bbox = (-300, -20, 300, 600)
H = np.load("inputs/closeup_BACK_H.npy")
XX, YY = T.grid(bbox); mpx, mpy = T.back_px(XX, YY)
img, valid = T.sample("inputs/closeups/closeup_front_right_a.png", H, mpx, mpy)
img2, _ = T.sample("inputs/back.png", None, mpx, mpy); img = np.where(valid[..., None], img, img2)
l = img.mean(2); mx, mn = img.max(2), img.min(2); sat = (mx - mn) / np.maximum(mx, 1e-3)
ray = (l > 0.36) & (sat < 0.32) & (img[..., 1] >= img[..., 2] - 0.02)
ray = ndi.binary_opening(ray, iterations=1)
ray &= (YY < 330)                                              # read the bands where they cross open fabric (above the bank)
ray &= ~np.asarray(__import__("shapely").contains_xy(B.PH_BOX.buffer(6), XX, YY))
ys, xs = np.nonzero(ray); X = XX[ys, xs]; Y = YY[ys, xs]
best = None
for a in np.arange(40, 50, 0.5):
    th = math.radians(a); u = np.cos(th) * X + np.sin(th) * Y          # across-ray coordinate for rays at angle a+90
    h, _ = np.histogram(u, bins=np.arange(-600, 600, 2.0)); sc = (h.astype(float) ** 2).sum()
    if best is None or sc > best[0]: best = (sc, a)
a = best[1]; th = math.radians(a)
across = lambda x, y: np.cos(th) * x + np.sin(th) * y
along = lambda x, y: -np.sin(th) * x + np.cos(th) * y
u = across(X, Y); v = along(X, Y)
h, edges = np.histogram(u, bins=np.arange(-600, 600, 2.0)); hs = ndi.uniform_filter1d(h.astype(float), 3)
from scipy.signal import find_peaks
pk, _ = find_peaks(hs, height=0.10 * hs.max(), distance=8, prominence=0.05 * hs.max())
merged = []
for p_ in pk:
    lo = p_
    while lo > 0 and hs[lo - 1] > 0.4 * hs[p_] and hs[lo - 1] <= hs[lo] * 1.15: lo -= 1
    hi = p_
    while hi < len(hs) - 1 and hs[hi + 1] > 0.4 * hs[p_] and hs[hi + 1] <= hs[hi] * 1.15: hi += 1
    merged.append([edges[lo], edges[hi + 1]])
# keep the peaks on the ray side (u > 0: the left-hand hump is the hanging moss highlights, not a ray); bands are split at
# the midpoints between neighbouring peaks and held to 25-45 mm (review: broad soft bands)
cs = [edges[p_] + 1.0 for p_ in pk if edges[p_] > 0]
spans = []
for i, c in enumerate(cs):
    lo = (cs[i-1] + c) / 2 if i else c - 22; hi = (cs[i+1] + c) / 2 if i < len(cs) - 1 else c + 22
    a_, b_ = max(lo + 3, c - 22.5), min(hi - 3, c + 22.5)
    if b_ - a_ < 25: a_, b_ = c - 12.5, c + 12.5
    spans.append((a_, b_))
merged = spans
bands = []
for u0, u1 in merged:
    sel = (u >= u0) & (u <= u1); vv = v[sel]; uu = u[sel]
    if sel.sum() < 150: continue
    v0 = np.percentile(vv, 1); v1 = 900.0                      # bands run on down-left across the scene (clipped later)
    left, right = [], []
    for vs in np.arange(v0, v1 + 10, 10.0):
        m = (vv >= vs - 8) & (vv < vs + 8)
        if m.sum() < 15: lo, hi = u0, u1
        else: lo, hi = min(np.percentile(uu[m], 8), u0 + 2), max(np.percentile(uu[m], 92), u1 - 2)
        left.append((lo, vs)); right.append((hi, vs))
    # smooth widths
    L = np.array(left); R_ = np.array(right)
    L[:, 0] = ndi.uniform_filter1d(L[:, 0], 5); R_[:, 0] = ndi.uniform_filter1d(R_[:, 0], 5)
    ring = list(L) + list(R_[::-1])
    pts = [(uu_ * math.cos(th) - vv_ * math.sin(th), uu_ * math.sin(th) + vv_ * math.cos(th)) for uu_, vv_ in ring]
    bands.append(dict(angle=a, pts=[[round(x, 2), round(y, 2)] for x, y in pts], w_mean=round(float((R_[:, 0] - L[:, 0]).mean()), 1),
                      length=round(float(v1 - v0), 1)))
json.dump(bands, open("rays_trace.json", "w"), indent=1)
print("angle", a, [(b["w_mean"], b["length"]) for b in bands])
if __name__ == "__main__":
    Image.fromarray((ray * 255).astype(np.uint8)).resize((600, 620)).save("out/art/raymask.png")
    hh = (hs / hs.max() * 200).astype(int); im = Image.new("L", (len(hh), 210), 0)
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)
    for i, v_ in enumerate(hh): d.line([(i, 210), (i, 210 - v_)], fill=255)
    im.save("out/art/rayhist.png"); print("hist range u", edges[np.nonzero(hs > 0)[0][[0, -1]]])
