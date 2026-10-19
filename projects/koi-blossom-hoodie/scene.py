"""Blossom tetra scene (slug koi-blossom-hoodie), Rev C — composed on the size-M pieces (garment / pattern mm).

Everything is traced from the input pixels (LESSONS A12-A15, Rev B review items 2-5):
  flora   floratrace.py -> trace/flora.pkl: 6 lilies (2 from the close-up, 4 from the mockup, each its own petal fan),
          every leaf, stem and floating petal traced one by one (outline, axis, length, tones from the pixels).
  fish    fishtrace.py -> trace/fish_template.pkl: the founder's reference tetra (reference_fish.png pixels: silhouette +
          cel-shaded facets) laid onto every mockup fish pose MEASURED FROM THE MOCKUP PIXELS (refmask.fish_poses:
          centre, principal axis, head end = away from the peduncle), at 0.82 x the mockup fish length
          (founder decision 19 Oct 2026: "82 % is fine").
No typed motif positions, no templates copied between flowers, no random numbers.
Output: scene.pkl = {"items": {piece: [...]}, "meta": {...}}.   usage: python3 scene.py"""
import kbcore
import pickle, math
import numpy as np
from shapely.ops import unary_union
import refmask as RM, fishtrace as FT, kbvis

FISH_SCALE = 0.82                    # founder decision 19 Oct 2026
FL = pickle.load(open("trace/flora.pkl", "rb"))
LAYER = {"stem": 20, "leaf": 21, "flower": 22, "petal": 23}
ITEMS = {P: [] for P in kbcore.PIECES}; UNITS = {}

def add(P, r, zbase, layer):
    g = kbvis.fix(r["geom"])
    if g.is_empty: return
    sub = r.get("sub", 0)
    out = dict(col=r["col"], geom=g, st=r["st"], ang=r["ang"], grp=r["grp"], sub=sub, unit=r["unit"], cluster=r.get("cluster"),
               el=kbcore.ELEM_OF[P], kob=0.0, ko=r.get("ko", r["grp"] not in ("FL-line",)))
    out["z"] = zbase + sub + len(ITEMS[P]) * 1e-4
    out["layer"] = layer if r.get("kind") != "fish" else 24.0 + sub / 10.0
    if r.get("kind") == "flower" and r["grp"] in ("FL-eye", "FL-line", "FL-stamen"): out["layer"] = 22.2
    ITEMS[P].append(out)
    UNITS.setdefault(r["unit"], dict(kind=r.get("kind"), piece=P, cluster=r.get("cluster")))

fish_info, lily_info, counts = [], [], {}
for P in kbcore.PIECES:
    t = FL[P]
    zb = {"stem": 1000, "leaf": 2000, "flower": 3000, "petal": 4000}
    for i, r in enumerate(t["regs"]):
        add(P, r, zb[r["kind"]] + (i % 1000) * 0.5, LAYER[r["kind"]])
    for L_ in t["info"]["lilies"]: lily_info.append(L_)
    # fish
    for k, pose in enumerate(RM.fish_poses(P)):
        u = f"fish_{P}{k}"; L = pose["L"] * FISH_SCALE
        regs, sil = FT.place(pose, L, unit=u)
        for r in regs: add(P, dict(r, kind="fish"), 5000 + k * 10, 24)
        fish_info.append(dict(piece=P, unit=u, c=pose["c"], ang=pose["ang"], L=round(L, 1), L_mockup=round(pose["L"], 1)))
    inf = t["info"]
    counts[P] = dict(fish=sum(1 for f in fish_info if f["piece"] == P), petals=inf["petals"], flowers=len(inf["lilies"]),
                     leaves=inf["leaves"], stems=inf["stems"])

META = dict(fish=fish_info, lilies=lily_info, counts=counts, fish_scale=FISH_SCALE,
            traced=dict(flora="floratrace.py (trace/flora.pkl)", fish="fishtrace.py (trace/fish_template.pkl) at refmask.fish_poses"),
            units=UNITS)
pickle.dump(dict(items=ITEMS, meta=META), open("scene.pkl", "wb"))
print({P: len(v) for P, v in ITEMS.items()}, counts)
