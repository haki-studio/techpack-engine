"""Trace sheets: out/trace_FR.png + out/trace_FL.png = the close-up mapped into size-M mm with the same row fit as closetrace |
the SHIPPED size-M DST of that piece rendered stitch by stitch (review E10: regenerated from the final DSTs).
usage: python3 tracechk.py            (from the DSTs, for the pack)
       python3 tracechk.py regions    (trace stage: the traced regions before stitching, for iterating)"""
import glcore, pickle, sys, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
import stitchrender as SR, closetrace as CT

MODE = sys.argv[1] if len(sys.argv) > 1 else "dst"
if MODE == "dst":
    sys.argv = ["compare.py", "M"]
    import compare as CMP
for P, bb in (("FR", (-300, 60, -5, 345)), ("FL", (5, 80, 300, 345))):
    ppm = 3.0
    if MODE == "dst": st = CMP.dst_render(bb, ppm)
    else: st = SR.render(pickle.load(open("closetrace.pkl", "rb"))[P]["regions"], bb, ppm, base=glcore.FABRIC)
    A = np.array(Image.open(CT.FILES[P]).convert("RGB")).astype(float); Wc = A.shape[1]
    W, H = st.size; ys = bb[1] + (np.arange(H) + .5)/ppm; xs = bb[0] + (np.arange(W) + .5)/ppm
    XX, YY = np.meshgrid(xs, ys); U, V, _ = CT.mapping(P, XX, YY, Wc)
    w = np.stack([ndi.map_coordinates(A[..., k], [V, U], order=1, mode='constant', cval=30) for k in range(3)], -1).astype('uint8')
    o = Image.new('RGB', (W*2 + 10, H + 24), 'white'); o.paste(Image.fromarray(w), (0, 24)); o.paste(st, (W + 10, 24))
    d = ImageDraw.Draw(o); d.text((4, 4), f"CLOSE-UP {P} (registered, row fit into the keep-out, size-M mm)", fill=(0, 0, 0))
    d.text((W + 14, 4), "SHIPPED DST size M, stitch by stitch (same scale)" if MODE == "dst" else "traced regions (before stitching)", fill=(0, 0, 0))
    o.save(f'out/trace_{P}.png' if MODE == "dst" else f'out/trace_{P}_regions.png')
    print(P, o.size)
