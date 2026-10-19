"""Per-pixel thread-family classification of the rectified mockups (HSV rules tuned on the two patches)."""
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
FAM = {0: ("cream", (242, 233, 216)), 1: ("red", (200, 22, 43)), 2: ("black", (28, 26, 26)), 3: ("pink", (239, 127, 172)),
       4: ("yellow", (245, 194, 48)), 5: ("blue", (53, 166, 214)), 6: ("white", (251, 248, 241)), 7: ("other", (90, 90, 90))}

def hsv(a):
    a = a / 255.0; mx = a.max(-1); mn = a.min(-1); d = mx - mn + 1e-9
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    h = np.where(mx == r, (g - b) / d % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    s = np.where(mx > 0, d / (mx + 1e-9), 0); return h, s, mx

def classify(img):
    a = np.asarray(img.convert("RGB")).astype(float)
    h, s, v = hsv(a)
    lab = np.full(h.shape, 7, np.uint8)
    lab[(s < 0.30) & (v > 0.55)] = 0
    lab[(s < 0.10) & (v > 0.93)] = 6
    lab[(v < 0.30) & (s < 0.75)] = 2
    redish = (h > 335) | (h < 12)
    lab[redish & (s > 0.62) & (v > 0.30)] = 1
    lab[(h > 300) & (h < 350) & (s > 0.25) & (s <= 0.62) & (v > 0.62)] = 3
    lab[(h > 28) & (h < 60) & (s > 0.45) & (v > 0.45)] = 4
    lab[(h > 180) & (h < 215) & (s > 0.35) & (v > 0.25)] = 5
    return lab

def clean(mask, open_px=2, close_px=2):
    st = np.ones((3, 3), bool)
    if close_px: mask = ndi.binary_closing(mask, st, iterations=close_px)
    if open_px: mask = ndi.binary_opening(mask, st, iterations=open_px)
    return ndi.binary_fill_holes(mask) if False else mask

def preview(lab, path):
    pal = np.array([FAM[i][1] for i in range(8)], np.uint8)
    Image.fromarray(pal[lab]).save(path)

if __name__ == "__main__":
    for n in ("wb", "coin"):
        lab = classify(Image.open(f"out/trace/{n}_rect.png")); np.save(f"out/trace/{n}_lab.npy", lab)
        preview(lab, f"out/trace/{n}_lab.png")
