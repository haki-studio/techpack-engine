"""Side-by-side: mockup (warped to garment mm) vs stitch render of the size-M art.  usage: python3 compare.py [size]"""
import glcore, pickle, sys
from PIL import Image, ImageDraw
import stitchrender as SR, mockmap as MM, front as F
size = sys.argv[1] if len(sys.argv) > 1 else "M"
D = pickle.load(open(f"front_{size}.pkl", "rb")); bb = (-300, -60, 300, 480); ppm = 2.0
st = SR.render(D["FR"] + D["FL"], bb, ppm, base=glcore.FABRIC)
mk = MM.warp(bb, ppm)
W, H = st.size; out = Image.new("RGB", (W*2 + 20, H + 30), (255, 255, 255)); out.paste(mk, (0, 30)); out.paste(st, (W + 20, 30))
d = ImageDraw.Draw(out); d.text((10, 8), "MOCKUP (mapped to size M mm)", fill=(0, 0, 0)); d.text((W + 30, 8), f"STITCH RENDER size {size}", fill=(0, 0, 0))
out.save(f"out/compare_{size}.png"); st.save(f"out/render_{size}.png"); print(out.size)
