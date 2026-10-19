"""Rectify the two patch mockups onto their finished-size mm frames (projective fit on the patch / field corners).
Output: out/trace/<name>_rect.png at PPM px per mm, covering the full patch W x H."""
import numpy as np
from PIL import Image
PPM = 20
SRC = {
    # waistband patch: outer corners (red-mask diagonal extremes, pushed out by the R2.5 corner rounding)
    "wb": ("inputs/1792126245750_image.png", 80.0, 54.0,
           [(52, 87), (1391, 35), (1415, 1003), (33, 1021)],
           # outer corners land so that the mockup's cream field (5.2-75.65 x 4.85-49.5 in the plain fit) registers on the
           # house field 6.5-73.5 x 6.5-47.5 (x 0.951, y 0.918): the traced field art is placed on the house border as drawn
           [(1.555, 2.048), (77.627, 2.048), (77.627, 51.62), (1.555, 51.62)]),
    # coin pocket: cream FIELD corners (top two visible; bottom two where the side bands meet the pocket mouth,
    # 2 mm above the field's lower edge — the mockup tucks the patch's lower part into the pocket)
    "coin": ("inputs/1792126222329_image.png", 76.0, 56.0,
             [(150, 172), (603, 262), (560, 492), (112, 470)], [(6.5, 6.5), (69.5, 6.5), (69.5, 47.5), (6.5, 47.5)]),
}
# konpeito spilling out above the coin pocket: same fit, canvas from y = -22 mm to +6 mm (patch top edge = 0)
SRC["spill"] = SRC["coin"][:1] + (76.0, 28.0) + SRC["coin"][3:] + ((0.0, -22.0),)

def homography(src, dst):
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u]); A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, Vt = np.linalg.svd(np.array(A, float)); return Vt[-1].reshape(3, 3) / Vt[-1][-1]

def rectify(name):
    path, W, H, src, dst = SRC[name][:5]
    X0, Y0 = SRC[name][5] if len(SRC[name]) > 5 else (0.0, 0.0)
    Hm = homography([((u - X0) * PPM, (v - Y0) * PPM) for u, v in dst], src)       # out px -> source px
    im = Image.open(path).convert("RGB")
    coeffs = (Hm / Hm[2, 2]).flatten()[:8]
    out = im.transform((int(W * PPM), int(H * PPM)), Image.PERSPECTIVE, tuple(coeffs), Image.BICUBIC)
    out.save(f"out/trace/{name}_rect.png"); return out

if __name__ == "__main__":
    for n in SRC: rectify(n)
