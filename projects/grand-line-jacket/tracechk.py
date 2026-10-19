"""TRACE STAGE check (not the shipped files): close-up mapped with the same row fit | traced regions rendered."""
import glcore, pickle, numpy as np, math
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
import stitchrender as SR, closetrace as CT, scene_lim
from shapely.geometry import LineString
D = pickle.load(open('closetrace.pkl', 'rb'))
for P, bb in (("FR", (-300, 60, -5, 345)), ("FL", (5, 80, 300, 345))):
    ppm = 3.0
    st = SR.render(D[P]["regions"], bb, ppm, base=glcore.FABRIC)
    cx, cy, _ = CT.fit(P); A = np.array(Image.open(CT.FILES[P]).convert("RGB")).astype(float); Wc = A.shape[1]
    lim = scene_lim.LIM_ALL["R" if P == "FR" else "L"]
    uA, xA, uE = (955.0, -11.0, 0.0) if P == "FR" else (360.0, 62.0, float(Wc))
    W, H = st.size; ys = bb[1] + (np.arange(H) + .5)/ppm; xs = bb[0] + (np.arange(W) + .5)/ppm
    def outer(y):
        seg = lim.intersection(LineString([(-400, y), (400, y)]))
        if seg.is_empty: return np.nan
        b = seg.bounds; return (b[0] + CT.EDGE_IN) if P == "FR" else (b[2] - CT.EDGE_IN)
    xo = CT.pd_ffill(np.array([outer(y) for y in ys])); sc = (xA - xo)/(uA - uE)
    XX, YY = np.meshgrid(xs, ys); U = uE + (XX - xo[:, None])/sc[:, None]; V = (YY - cy[0])/cy[1]
    w = np.stack([ndi.map_coordinates(A[..., k], [V, U], order=1, mode='constant', cval=30) for k in range(3)], -1).astype('uint8')
    o = Image.new('RGB', (W*2 + 10, H + 24), 'white'); o.paste(Image.fromarray(w), (0, 24)); o.paste(st, (W + 10, 24))
    d = ImageDraw.Draw(o); d.text((4, 4), f"TRACE STAGE {P}: close-up (row fit into the keep-out)", fill=(0, 0, 0)); d.text((W + 14, 4), "traced regions (before stitching)", fill=(0, 0, 0))
    o.save(f'out/trace_{P}.png')
