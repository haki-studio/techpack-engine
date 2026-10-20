"""Fit the Koi close-up onto the MOCKUP motif by motif (founder ruling 2026-10-20: the mockup governs, the close-up only
informs detail inside mockup motifs; engine/digitize/extract/inform.py). Writes the `fr_upper` close-up entry of
bench/registration.json as mode "inform" with one similarity per motif window, and prints each fit.

  PYTHONPATH=engine python3 projects/koi-blossom-hoodie/bench/inform_fit.py

Windows are mockup px around motifs the MOCKUP has (read off the mockup crop, bench/TRIAL.md). Initial guess = the
global affine of trace/closeup_reg.json, pinned at the motif's tie point when it has one. Fish are NOT informed: the
founder's fish are tetras (inputs/reference_fish.png); the close-up shows koi. Floating petals are not informed either
(each is a few mockup pixels; their close-up counterparts sit elsewhere)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); PROJ = os.path.dirname(HERE); ROOT = os.path.dirname(os.path.dirname(PROJ))
os.chdir(PROJ); sys.path.insert(0, os.path.join(ROOT, "engine"))
import numpy as np
from PIL import Image
from digitize.extract import inform

V = dict(ox=368.0, oy=308.0, sx=1.12, sy=510.0 / 475.0)
def mm2px(x, y): return x / V["sx"] + V["ox"], y / V["sy"] + V["oy"]

REG = json.load(open("trace/closeup_reg.json"))
TIE = {lab: (cu, mk) for lab, cu, mk in zip(REG["features"]["labels"], REG["features"]["closeup"], REG["features"]["mockup"])}
MIN_IOU = 0.5     # a close-up motif informs a mockup motif only when their silhouettes overlay this well after the fit
MOTIFS = [   # name, window in garment mm (x0, y0, x1, y1) around the MOCKUP motif, tie point label (or None)
    ("lily_upper", (-222, 88, -150, 176), "lily0", [(-196, 161, -150, 182)]),   # exclude: the fish tail touching the lily
    ("lily_lower", (-216, 174, -128, 236), "lily1", []),
    ("leaves_lower", (-222, 236, -150, 300), None, []),
]


def main():
    flat = np.asarray(Image.open("inputs/front.png").convert("RGB")).astype(float)
    cu = np.asarray(Image.open("inputs/closeup_mockup_koi.png").convert("RGB")).astype(float)
    out = []; dropped = []
    for name, (x0, y0, x1, y1), tie, excl in MOTIFS:
        (px0, py0), (px1, py1) = mm2px(x0, y0), mm2px(x1, y1)
        win = [round(px0, 1), round(py0, 1), round(px1, 1), round(py1, 1)]
        init = inform.init_from_affine(REG["affine"]["X"], TIE[tie] if tie else None)
        f = inform.fit_similarity(flat, cu, win, init, rot_deg=45.0, rot_step=3.0, scale_rel=0.3, scale_step=0.05, max_shift=25)
        print(name, win, {k: f[k] for k in ("iou_init", "iou", "rot", "scale", "shift_px")})
        rec = dict(name=name, window=win, sim=f["sim"], fit={k: f[k] for k in ("iou_init", "iou", "rot", "scale", "shift_px")},
                   tie=tie, window_mm=[x0, y0, x1, y1],
                   exclude=[[round(v, 1) for v in (*mm2px(a, b), *mm2px(c, d))] for a, b, c, d in excl])
        if f["iou"] < MIN_IOU:                      # the close-up's motif does not match the mockup's: the mockup wins, no detail
            rec["informed"] = False; rec["why"] = f"best per-motif fit IoU {f['iou']} < {MIN_IOU}: the close-up does not show this mockup motif"
            dropped.append(rec); continue
        out.append(rec)
    rp = os.path.join(HERE, "registration.json"); r = json.load(open(rp))
    r["closeups"] = [dict(name="fr_upper", view="F", file="inputs/closeup_mockup_koi.png", mode="inform", motifs=out, not_informed=dropped,
                          _doc="founder ruling 2026-10-20: the mockup governs; this close-up only informs interior detail inside the "
                               "mockup's own motif silhouettes, one similarity per motif (bench/inform_fit.py), colours transferred "
                               "to the mockup motif's. Fish and floating petals are not informed.")]
    r["_doc"] = ("Koi Blossom registration as DATA (engine/digitize/extract/register.py + inform.py). flat = the front-view mockup "
                 "inputs/front.png; view F (fronts, size M): x mm = (px - 368) * 1.12, y mm = (py - 308) * 510/475 (mockmap). The "
                 "MOCKUP governs every position, silhouette and colour (founder ruling 2026-10-20); the close-up informs "
                 "detail inside three mockup motifs (mode inform).")
    json.dump(r, open(rp, "w"), indent=1)
    print("wrote", rp)


if __name__ == "__main__":
    main()
