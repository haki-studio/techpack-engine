import numpy as np, pixels as PX, mockmap as MM
from PIL import Image
lab = PX.labels()
def grid(c, ox, oy, xr=(-300, 300), yr=(250, 560)):
    xs = np.arange(xr[0] + ox, xr[1], c); ys = np.arange(yr[0] + oy, yr[1], c)
    out = np.full((len(ys), len(xs)), 6, np.int8)
    for j, y in enumerate(ys):
        for i, x in enumerate(xs):
            px0, py0 = MM.Pinv(x, y); px1, py1 = MM.Pinv(x + c, y + c)
            f, v = PX.frac(px0, py0, px1, py1, lab)
            if v > 0.4: out[j, i] = f.argmax()
    return out
pal = np.array([[128, 174, 247], [241, 234, 226], [20, 20, 20], [255, 230, 0], [200, 140, 0], [255, 0, 255], [255, 0, 255]], np.uint8)
ims = []
a = MM.img().astype(np.uint8); px0, py0 = MM.Pinv(-300, 250); px1, py1 = MM.Pinv(300, 560)
ims.append(Image.fromarray(a[int(py0):int(py1), int(px0):int(px1)]).resize((1200, 620)))
for c in (2.5, 5.0):
    ims.append(Image.fromarray(pal[grid(c, 0, 0)]).resize((1200, 620), Image.NEAREST))
im = Image.new('RGB', (1200, 1880), 'white')
for k, x in enumerate(ims): im.paste(x, (0, 630 * k))
im.save('out/trace_cmp.png')
