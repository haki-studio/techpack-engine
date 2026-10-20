"""Zones (ENGINE_PLAN M1): hand-authored (or, later, answered) WINDOWS + the tones that belong to them, per piece:
projects/<style>/bench/zones_<piece>.json. A zone says what a region IS (sky, fall, pool, a stub for things whose
splitter is not built yet); the evidence says which pixels in the window look like it. The traced silhouette is the
window AND those tones, so geometry always comes from input pixels (LESSONS A14), never from the hand-drawn window.

Claims are exclusive: zones claim pixels from the highest z down; the zone marked "rest" takes what is left over.

  zs = zones.load("projects/castle-falls-jacket/bench/zones_BK.json")
  parts, log = zones.claim_and_split(zs, ev, z_of, split)   # split(zone, z, mask) -> (parts, used mask)
"""
import json
import numpy as np
from shapely.geometry import Polygon
from shapely.ops import unary_union


def load(path):
    d = json.load(open(path))
    for z in d["zones"]:
        z["geoms"] = [Polygon(w) for w in z.get("windows", [])]
        if not z.get("rest") and not z["geoms"]: raise ValueError(f"zone {z['id']}: no windows and not the rest zone")
    if sum(1 for z in d["zones"] if z.get("rest")) > 1: raise ValueError("more than one rest zone")
    return d


def window(z):
    return unary_union(z["geoms"]) if z["geoms"] else None


def claim_and_split(zs, ev, z_of, split):
    """Claim pixels zone by zone, highest z first, the rest zone last. split(zone, z, claim_mask) -> (parts, used_mask);
    only the USED pixels (the traced silhouette) are taken: a pixel a zone's tones matched but its splitter did not use
    (a blue rock pixel inside a fall window) goes back to the zones below. Returns (parts, [dict(zone, z, claimed, used)])."""
    order = sorted([z for z in zs["zones"] if not z.get("rest")], key=lambda z: -z_of(z))
    rest = [z for z in zs["zones"] if z.get("rest")]
    taken = np.zeros((ev.H, ev.W), bool); parts, log = [], []
    for z in order + rest:
        m = np.ones_like(taken) if z.get("rest") else ev.mask(window(z))
        if z.get("tones", "all") != "all":
            idx = [ev.keys.index(k) for k in z["tones"] if k in ev.keys]
            m &= np.isin(ev.tone, idx)
        m &= ~taken
        ps, used = split(z, z_of(z), m)
        used = used & ~taken; taken |= used; parts += ps
        log.append(dict(zone=z["id"], z=z_of(z), claimed_mm2=round(float(m.sum()) / ev.ppm ** 2, 1),
                        used_mm2=round(float(used.sum()) / ev.ppm ** 2, 1), parts=len(ps)))
    return parts, log
