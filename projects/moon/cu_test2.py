import sys, time
from PIL import Image
import moonpal, stitchrender as SR, closeart as CA, moon2
t = time.time()
vis, disc, n = moon2.build(CA.CB)
im = SR.render(vis, (-125, 119, 125, 369), 4, base=moonpal.FABRIC)
k = moon2.K; cu = CA.CB.crop((int(moon2.CX - 125 / k), int(moon2.CY - 125 / k), int(moon2.CX + 125 / k), int(moon2.CY + 125 / k))).resize(im.size, Image.LANCZOS)
s = Image.new("RGB", (im.width * 2 + 20, im.height), "white"); s.paste(cu, (0, 0)); s.paste(im, (im.width + 20, 0)); s.save("out/cu_test_moon.png")
z = SR.render(vis, (-60, 170, 0, 230), 12, base=moonpal.FABRIC); z.save("out/cu_test_moonz.png")
print("objects", len(vis), "cells", n, f"{time.time()-t:.0f}s")
