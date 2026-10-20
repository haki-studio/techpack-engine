"""Lily centres + petal guides = READINGS of the input images (Rev C). No pixels of the art, no masks.
Close-up lilies: close-up px read on 2x gridded zooms of inputs/closeup_mockup_koi.png, mapped through the close-up
registration (trace/closeup_reg.json). Mockup lilies: mockup px read on 8-10x gridded zooms of inputs/front.png.
Used by floratrace.py (petal split of each traced silhouette) and fidelity.py (lily disc = centre + median tip distance)."""
import numpy as np
from scipy.interpolate import griddata
import refmask as R, mockmap as MM, front as F

# ---------------------------------------------------------------- lily guides (source px): centre, [(tip, width px)] back -> front
# close-up lilies: close-up px (cu_trace FLOWERS, read on 2x gridded zooms of the close-up)
CU_GUIDES = {
 "lily0": dict(c=(95, 415), petals=[((118, 232), 46), ((-12, 330), 58), ((-25, 470), 62), ((282, 413), 58), ((182, 537), 72), ((176, 298), 74)]),
 "lily1": dict(c=(250, 680), petals=[((105, 598), 42), ((228, 558), 56), ((108, 712), 52), ((222, 803), 48), ((378, 790), 58), ((357, 640), 58)]),
}
# mockup lilies: mockup px, read on 8-10x gridded zooms of front.png (Rev C) — each flower's own fan
MK_GUIDES = {
 "FR_hem":  dict(piece="FR", c=(346, 757), petals=[((358, 733), 8), ((356, 779), 8), ((312, 749), 9), ((330, 789), 14), ((347, 714), 15)]),
 "FL_big":  dict(piece="FL", c=(483, 754), petals=[((523, 724), 18), ((518, 782), 20), ((470, 798), 20), ((437, 743), 20), ((483, 705), 22)]),
 "FL_dark": dict(piece="FL", c=(567, 746), petals=[((598, 738), 9), ((560, 782), 10), ((583, 770), 13), ((538, 728), 13), ((573, 719), 12)]),
 "SR_cuff": dict(piece="SR", c=(46, 883), petals=[((17, 858), 12), ((60, 912), 16), ((16, 898), 18), ((82, 869), 18), ((46, 846), 16)]),
}

def to_mm(P, xs, ys):
    """source px -> piece mm (vectorised): fronts linear, sleeves through the mockmap cylinder grid"""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    if P in ("FR", "FL"):
        return (xs - MM.CFX) * MM.SX, (ys - MM.NECKY) * MM.SY
    mt = F.pieces("M")[1]; pts, tu = MM._grid(P, mt)
    t_u = griddata(pts, tu, np.c_[xs, ys], method="linear")
    bad = np.isnan(t_u[:, 0])
    if bad.any(): t_u[bad] = griddata(pts, tu, np.c_[xs, ys][bad], method="nearest")
    t, u = t_u[:, 0], t_u[:, 1]
    y = (-mt["cap_h"] + t * (mt["Lu"] + mt["cap_h"])) * (1 - u) + t * mt["Lu"] * u
    hw = mt["W"] + (mt["Ww"] - mt["W"]) * np.clip(y, 0, None) / mt["Lu"]
    x = u * hw
    return (x if P == "SR" else -x), y

def cu_to_mock(name, xs, ys):
    return R.cu_to_mock(xs, ys)          # one continuous close-up -> mockup map (refmask: affine + blended lily residuals)

def lanceolate(c, tip, w, n=30, wmax_at=0.42):
    c = np.array(c, float); t = np.array(tip, float); d = t - c; L = np.hypot(*d); u = d / L; nv = np.array([-u[1], u[0]])
    s = np.linspace(0, 1, n)
    hw = w / 2 * np.where(s < wmax_at, np.clip(np.sin(np.pi / 2 * s / wmax_at), 0, 1) ** 0.7,
                          np.clip(np.cos(np.pi / 2 * np.clip(s - wmax_at, 0, None) / (1 - wmax_at)), 0, 1) ** 0.9)
    hw[0] = w * 0.12
    return np.array([c + u * L * si + nv * h for si, h in zip(s, hw)] + [c + u * L * si - nv * h for si, h in zip(s, hw)][::-1])

def lily_specs(P):
    out = []
    if P == "FR":
        for nm, g in CU_GUIDES.items():
            cx, cy = cu_to_mock(nm, [g["c"][0]], [g["c"][1]])
            pet = []
            for tip, w in g["petals"]:
                ring = lanceolate(g["c"], tip, w); mx, my = cu_to_mock(nm, ring[:, 0], ring[:, 1])
                pet.append((np.c_[mx, my], cu_to_mock(nm, [tip[0]], [tip[1]])))
            out.append(dict(name=f"cu_{nm}", src="close-up", c=(float(cx[0]), float(cy[0])), petals=pet))
    for nm, g in MK_GUIDES.items():
        if g["piece"] != P: continue
        out.append(dict(name=nm, src="mockup", c=g["c"], petals=[(lanceolate(g["c"], tip, w), ([tip[0]], [tip[1]])) for tip, w in g["petals"]]))
    return out

