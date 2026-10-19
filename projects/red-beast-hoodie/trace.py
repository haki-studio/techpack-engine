"""Colour-class trace of the mockup into piece mm space (size M), 4 px/mm.
Labels: 0 fabric, 1 red, 2 crimson, 3 black thread, 4 cream, 9 off (other piece / outside the source).
F  = both fronts in front garment mm (sleeve patches of the render excluded); FL inside the close-up footprint is read
     from the close-up (registered, mockmap.close_px), the rest from the mockup.
SR / SL = sleeve patches of the render in S01 / S02 pattern mm.
usage: python3 trace.py   -> trace_M.npz + out/trace/*.png"""
import rbcore
import os, json
import numpy as np
from scipy import ndimage as ndi
from PIL import Image
import mockmap as MM, front as F

PPM = 4.0
SPACES = {"F": (-330.0, -90.0, 330.0, 520.0), "SR": (-260.0, -110.0, 260.0, 470.0), "SL": (-260.0, -110.0, 260.0, 470.0)}
COLS = {0: (43, 48, 57), 1: (201, 31, 50), 2: (142, 22, 38), 3: (10, 10, 12), 4: (234, 223, 203), 9: (255, 255, 255)}
# thresholds per source (the close-up is exposed darker than the mockup)
TH = {"front": dict(red=42, crim_r=105, cream_L=128, cream_rb=48, black_L=22.0),
      "close": dict(red=42, crim_r=118, cream_L=122, cream_rb=55, black_L=19.0)}

def grid(bb):
    x0, y0, x1, y1 = bb; W, H = int((x1-x0)*PPM), int((y1-y0)*PPM)
    xs = x0 + (np.arange(W) + 0.5)/PPM; ys = y0 + (np.arange(H) + 0.5)/PPM
    return np.meshgrid(xs, ys)

def classify(rgb, th, sigma=0.9):
    rgb = np.stack([ndi.gaussian_filter(rgb[..., c], sigma) for c in range(3)], -1)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]; L = rgb @ np.array([0.3, 0.59, 0.11], np.float32)
    rs = r - np.maximum(g, b)
    lab = np.zeros(r.shape, np.uint8)
    red = rs > th["red"]
    lab[red] = 1; lab[red & (r < th["crim_r"])] = 2
    cream = (L > th["cream_L"]) & ((r - b) < th["cream_rb"]) & ~red
    lab[cream] = 4
    return lab, L

def disk(mm):
    r = int(round(mm*PPM)); y, x = np.ogrid[-r:r+1, -r:r+1]; return x*x + y*y <= r*r

def black_in_envelope(lab, L, th, valid, close_mm=3.5, reach_mm=6.0):
    """black thread = inside the closed hair mass and not red / cream. The envelope grows from the RED strokes
    (closing + hole fill), plus red+cream closing within reach_mm of red, so lightning branches over bare fabric
    never get a black ground. Very bright-fabric pixels (L > fabric_hi) inside it stay fabric."""
    red = (lab == 1) | (lab == 2); art = red | (lab == 4)
    e1 = ndi.binary_fill_holes(ndi.binary_closing(red, structure=disk(close_mm)))
    e2 = ndi.binary_fill_holes(ndi.binary_closing(art, structure=disk(close_mm))) & ndi.binary_dilation(red, structure=disk(reach_mm))
    # holes fully enclosed by the art (the mouth between the teeth, the eye socket), up to 900 mm2
    base = art | e1 | e2; hl, nh = ndi.label(ndi.binary_fill_holes(base) & ~base)
    if nh:
        sz = ndi.sum(np.ones_like(hl), hl, index=np.arange(1, nh + 1)) / PPM**2
        e3 = np.isin(hl, 1 + np.nonzero(sz < 900)[0])
    else: e3 = np.zeros_like(base)
    env = ndi.binary_opening((e1 | e2 | e3) & valid, structure=disk(1.0))
    dark = ndi.gaussian_filter(L, 1.0) < th["black_L"] + 14
    blk = env & ~art & dark
    blk = ndi.binary_opening(blk, structure=disk(0.4))
    lab = lab.copy(); lab[blk] = 3
    return lab

HOOD = [(0, 0), (723, 0), (723, 228), (600, 230), (520, 246), (430, 286), (400, 298), (377, 307), (366, 312), (355, 307), (332, 298), (300, 286),
        (210, 248), (150, 232), (0, 228)]                                    # hood (shell + sherpa) above this line: off
WELTS = [[(217, 590), (232, 596), (172, 708), (158, 700)], [(528, 632), (540, 628), (574, 700), (560, 708)]]   # visible welt edges
_BG = None
def bg_mask(px, py):
    """white studio background of front.png: near-white connected to the image border (cream thread is not)"""
    global _BG
    if _BG is None:
        a = MM.img("front"); w = (a.min(-1) > 195) & (a.max(-1) - a.min(-1) < 40)
        lab, n = ndi.label(w); edge = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])) - {0}
        _BG = ndi.binary_dilation(np.isin(lab, list(edge)), iterations=3)
    xi = np.clip(np.round(px).astype(int), 0, _BG.shape[1] - 1); yi = np.clip(np.round(py).astype(int), 0, _BG.shape[0] - 1)
    return _BG[yi, xi]

# open mouth between the upper and lower teeth (front mm, read off the registered close-up): black thread ground
MOUTH = [(6, 211), (60, 206), (126, 220), (168, 241), (216, 256), (228, 274), (210, 295), (168, 304), (120, 286), (75, 268), (30, 244), (5, 235)]

DIM_RED = 16.0
def trace_front():
    X, Y = grid(SPACES["F"]); fx, fy = MM.Pinv(X, Y)
    rgbm = MM.sample("front", fx, fy)
    labm, Lm = classify(rgbm, TH["front"])
    inside = (fx >= 0) & (fx < 723) & (fy >= 0) & (fy < 1085)
    # exclude the render's sleeve patches
    import shapely
    off = np.zeros(X.shape, bool)
    from shapely.geometry import Polygon
    for s in "RL": off |= shapely.contains_xy(MM.sleeve_poly(s), fx, fy)
    off |= shapely.contains_xy(Polygon(HOOD), fx, fy) | bg_mask(fx, fy)
    welt = np.zeros(X.shape, bool)
    for w in WELTS: welt |= shapely.contains_xy(Polygon(w).buffer(5), fx, fy)
    valid = inside & ~off
    labm = black_in_envelope(labm, Lm, TH["front"], valid)
    # close-up on the wearer's left (x > 0), inside its footprint
    cx, cy = MM.close_px(fx, fy); B = MM.img("closeup_mockup_head")
    inc = (cx > 6) & (cx < B.shape[1] - 6) & (cy > 6) & (cy < B.shape[0] - 6) & (X > 0) & valid
    rgbc = MM.sample("closeup_mockup_head", np.where(inc, cx, 0), np.where(inc, cy, 0))
    labc, Lc = classify(rgbc, TH["close"], sigma=0.7)
    labc = black_in_envelope(labc, Lc, TH["close"], inc)
    # Rev B (review item 2): dim red stitches inside the black ground (throat, jaw) are crimson shade strokes, not black
    sm = np.stack([ndi.gaussian_filter(rgbc[..., c], 0.8) for c in range(3)], -1)
    rsc = sm[..., 0] - np.maximum(sm[..., 1], sm[..., 2])
    labc[(labc == 3) & (rsc > DIM_RED)] = 2
    lab = np.where(inc, labc, labm); lab[~valid] = 9
    lab[welt & (lab == 4)] = 0
    lab[(lab == 0) & shapely.contains_xy(Polygon(MOUTH), X, Y)] = 3                                                # welt-edge highlights are not thread
    Lsrc = np.where(inc, Lc, Lm).astype(np.float32)
    return lab, inc, Lsrc

def trace_sleeve(side):
    g, mt = F.pieces("M")
    X, Y = grid(SPACES["S" + side]); px, py, ok = MM.sleeve_to_img(side, X, Y, mt)
    rgb = MM.sample("front", np.where(ok, px, 0), np.where(ok, py, 0))
    lab, L = classify(rgb, TH["front"])
    lab[~ok | bg_mask(px, py)] = 9                    # no black on the sleeves: the dark there is fold shading, not thread
    return lab, L.astype(np.float32)

def png(lab, path):
    im = np.zeros(lab.shape + (3,), np.uint8)
    for k, c in COLS.items(): im[lab == k] = c
    Image.fromarray(im).save(path)

if __name__ == "__main__":
    os.makedirs("out/trace", exist_ok=True)
    labF, inc, LF = trace_front(); labR, LR = trace_sleeve("R"); labL, LL = trace_sleeve("L")
    np.savez_compressed("trace_M.npz", F=labF, SR=labR, SL=labL, F_close=inc, LF=LF, LSR=LR, LSL=LL, ppm=PPM,
                        bbF=SPACES["F"], bbS=SPACES["SR"])
    png(labF, "out/trace/trace_F.png"); png(labR, "out/trace/trace_SR.png"); png(labL, "out/trace/trace_SL.png")
    for k, lab in (("F", labF), ("SR", labR), ("SL", labL)):
        print(k, {n: round(float((lab == v).sum())/PPM**2) for n, v in (("red", 1), ("crimson", 2), ("black", 3), ("cream", 4))}, "mm2")
