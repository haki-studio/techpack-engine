"""Reference masks for fidelity.py, written by sleeve_scene.py (sleeve_ref.pkl): mockup cloud + design-coverage masks on the
sleeve-pattern grid (4 px/mm, sew-poly bounds), garment details masked out (outside the readable front half / keep-outs)."""
import pickle
_d = pickle.load(open("sleeve_ref.pkl", "rb"))
def masks(side, bb, ppm):
    r = _d["SR" if side == "R" else "SL"]
    assert ppm == 4.0 and all(abs(a - b) < 1e-6 for a, b in zip(r["bb"], bb)), "sleeve_ref grid mismatch"
    return r
GLOWS = {P: _d[P + "_glow"] for P in ("SR", "SL")}
EDGE = {P: _d[P + "_edge"] for P in ("SR", "SL")}
