"""quick close-up fidelity test: close-up crop | our render, for the moon and one cloud"""
import sys, time
from PIL import Image
import moonpal, closeart as CA, stitchrender as SR, tracedart as TA
which = sys.argv[1:] or ["moon", "cloud"]
t = time.time()
if "moon" in which:
    vis, disc = CA.moon(); cx, cy, r = CA.CU_MOON; k = TA.MOON_R_PX * TA.K / r
    im = SR.render(vis, (-125, 119, 125, 369), 4, base=moonpal.FABRIC)
    cu = CA.CB.crop((int(cx - 125 / k), int(cy - 125 / k), int(cx + 125 / k), int(cy + 125 / k))).resize(im.size, Image.LANCZOS)
    s = Image.new("RGB", (im.width * 2 + 20, im.height), "white"); s.paste(cu, (0, 0)); s.paste(im, (im.width + 20, 0)); s.save("out/cu_test_moon.png")
    print("moon", len(vis), f"{time.time()-t:.0f}s")
if "cloud" in which:
    bx = (40, 160, 660, 360)
    cs = CA.cloud_comps(CA.CB, bx, CA.MOON + ["m5b"] + CA.POLE + CA.NAVY)
    c = max(cs, key=lambda c: c["px"].area); b = c["px"].bounds; s_ = 0.36
    vis = CA.place(c, (0, 0), s_)
    W = (b[2] - b[0]) * s_ / 2 + 4; H = (b[3] - b[1]) * s_ / 2 + 4
    im = SR.render(vis, (-W, -H, W, H), 5, base=moonpal.FABRIC)
    cxp, cyp = c["px"].centroid.x, c["px"].centroid.y
    cu = CA.CB.crop((int(cxp - W / s_), int(cyp - H / s_), int(cxp + W / s_), int(cyp + H / s_))).resize(im.size, Image.LANCZOS)
    s = Image.new("RGB", (im.width, im.height * 2 + 20), "white"); s.paste(cu, (0, 0)); s.paste(im, (0, im.height + 20)); s.save("out/cu_test_cloud.png")
    print("cloud regions", len(vis), "lines", sum(1 for v in vis if v["grp"] == "CL-line"), f"{time.time()-t:.0f}s")
