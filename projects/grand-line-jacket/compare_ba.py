"""Before / after crops (founder items a + b): out/compare_before_after.png. BEFORE = out/review_E2/compare_M_1411.png (the
14:11 compare_M sheet, shipped-DST render, 2 px/mm); AFTER = out/compare_M.png regenerated from the CURRENT DSTs (same layout);
MOCKUP = the mockup panel of the same sheet. Same mm boxes, same scale.  usage: python3 compare_ba.py"""
from PIL import Image, ImageDraw
BB, PPM, W = (-300, -60, 300, 480), 2.0, 1200
CROPS = [((8, 188, 88, 476), "FL zip-side column, horizon to hem (founder a)"),
         ((60, 370, 190, 432), "FL hem islet (founder b)"),
         ((-175, 400, -55, 455), "FR hem islet (founder b)"),
         ((-130, 300, -40, 370), "FR lower islets (founder b)")]
before = Image.open("out/review_E2/compare_M_1411.png").convert("RGB"); after = Image.open("out/compare_M.png").convert("RGB")
def crop(im, bb, dst):
    X0 = (W + 20) if dst else 0
    return im.crop((int(X0 + (bb[0] - BB[0])*PPM), int(30 + (bb[1] - BB[1])*PPM), int(X0 + (bb[2] - BB[0])*PPM), int(30 + (bb[3] - BB[1])*PPM)))
rows = []
for bb, cap in CROPS:
    s = 3 if (bb[2] - bb[0]) > 100 else 4
    ims = [crop(after, bb, False), crop(before, bb, True), crop(after, bb, True)]
    ims = [i.resize((i.width*s//2, i.height*s//2), Image.LANCZOS) for i in ims]
    rows.append((cap, bb, ims))
Wt = max(sum(i.width for i in ims) + 40 for _, _, ims in rows); Ht = sum(ims[0].height + 40 for _, _, ims in rows) + 30
out = Image.new("RGB", (Wt, Ht), (255, 255, 255)); d = ImageDraw.Draw(out); y = 10
d.text((10, y), "BEFORE / AFTER (size M, same mm box + scale): MOCKUP | BEFORE = 14:11 shipped DST (Rev E2 start) | AFTER = current shipped DST (Rev E3)", fill=(0, 0, 0)); y += 20
for cap, bb, ims in rows:
    d.text((10, y), f"{cap}   x {bb[0]}..{bb[2]}, y {bb[1]}..{bb[3]} mm", fill=(0, 0, 0)); y += 16
    x = 10
    for lab, im in zip(("MOCKUP", "BEFORE 14:11", "AFTER"), ims):
        out.paste(im, (x, y)); d.text((x + 4, y + 4), lab, fill=(255, 255, 0)); x += im.width + 10
    y += ims[0].height + 24
out.save("out/compare_before_after.png"); print(out.size)
