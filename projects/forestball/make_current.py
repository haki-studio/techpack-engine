"""Collect stitch-file results -> dst_all.json (every grade) + dst_current.json (grade B = size M set), trims counted from
the DST read-back (LESSONS B8). Also checks the gates: max stitch ≤ 7.5, ≤ 15 threads, splits fit the frame."""
import json, os, collections
import pyembroidery as pe

def colour_counts(base):
    """stitches per thread colour (hex) read from the DST, colours from the PES thread list"""
    cols = [t.hex_color().upper() for t in pe.read(base + ".pes").threadlist]; p = pe.read(base + ".dst"); ci = 0; out = {}
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK
        if k == pe.COLOR_CHANGE: ci += 1
        elif k == pe.STITCH: h = cols[min(ci, len(cols)-1)]; out[h] = out.get(h, 0) + 1
    return out

def dst_count(base):
    rb = readback.dst(base + ".dst"); return rb["trims"], rb["stitches"]

import fbcore, back as B, factory, readback
from shapely.geometry import box as _box, Point
from shapely import affinity
SCALE = {"A": 0.90, "B": 1.0, "C": 1.08}
def placeholder_check(base, centre, G, origin=None):
    """licensed box: every stitch inside it must belong to the basting colour (LESSONS: nothing stitched in the box).
    Returns (stitches of other colours inside the box shrunk 1.5 mm, basting stitches on the box outline)."""
    c = tuple(centre); origin = tuple(origin or centre)
    ph = affinity.scale(B.PH_BOX, SCALE[G], SCALE[G], origin=c)
    inner = ph.buffer(-1.5); ring = ph.exterior.buffer(1.0)
    p = pe.read(base + ".dst"); bad = 0; bast = 0          # any colour: nothing inside, the outline on the ring
    for x, y, cmd in p.stitches:
        if cmd & pe.COMMAND_MASK != pe.STITCH: continue
        q = Point(x/10 + origin[0], y/10 + origin[1])
        if inner.contains(q): bad += 1
        elif ring.contains(q): bast += 1
    return bad, bast
allr = {"grades": {}, "splits": {}}; gates = []
for G in ("A", "B", "C"):
    p = f"dst_results_{G}.json"
    if os.path.exists(p):
        r = json.load(open(p))
        for k, v in r.items():
            rb = readback.dst(v["file"] + ".dst"); v.update(stitches=rb["stitches"], trims_dst=rb["trims"], stops=rb["stops"], max_stitch=rb["max_stitch"])
            v.pop("trims_cmd", None); v.pop("trims", None)       # one definition: engine readback.dst (DST)
            v["per_colour"] = colour_counts(v["file"])
            v["threads"] = factory.check_threads(v["file"] + ".pes")
            gates.append((f"{G} {k}", v["max_stitch"] <= 7.5, v["threads"] <= factory.max_threads()))
            if k == "back":
                v["ph_inside"], v["ph_basting"] = placeholder_check(v["file"], v["centre"], G)
                gates.append((f"{G} back placeholder empty ({v['ph_inside']} st inside, {v['ph_basting']} basting)", v["ph_inside"] == 0, v["ph_basting"] > 10))
        allr["grades"][G] = r
    p = f"dst_splits_{G}.json"
    if os.path.exists(p):
        s = json.load(open(p))
        for nm, v in s["sections"].items():
            rb = readback.dst(v["file"] + ".dst"); v.update(stitches=rb["stitches"], trims_dst=rb["trims"], stops=rb["stops"], max_stitch=rb["max_stitch"])
            v.pop("trims_cmd", None); v.pop("trims", None)
            v["threads"] = factory.check_threads(v["file"] + ".pes")
            gates.append((f"{G} {nm}", v["max_stitch"] <= 7.5 and v["fits"], v["threads"] <= factory.max_threads()))
            if v.get("placeholder"):
                ctr = allr["grades"].get(G, {}).get("back", {}).get("centre")
                if ctr:
                    v["ph_inside"], v["ph_basting"] = placeholder_check(v["file"], ctr, G, origin=v["centre"])
                    gates.append((f"{G} {nm} placeholder empty ({v['ph_inside']} inside)", v["ph_inside"] == 0, v["ph_basting"] > 10))
        allr["splits"][G] = s
json.dump(allr, open("dst_all.json", "w"), default=float, indent=1)
B = allr["grades"].get("B", {})
json.dump({k: B.get(k) for k in ("back", "02R", "02L")}, open("dst_current.json", "w"), default=float, indent=1)
if "B" in allr["splits"]: json.dump(allr["splits"]["B"], open("dst_current_splits.json", "w"), default=float, indent=1)
for G, r in allr["grades"].items():
    print(G, {k: (v["stitches"], v["trims_dst"], v["stops"], v["threads"], v["max_stitch"]) for k, v in r.items()})
for G, s in allr["splits"].items():
    print(G, "splits", {nm: (v["stitches"], v["trims_dst"], v["fits"]) for nm, v in s["sections"].items()})
bad = [g for g in gates if not (g[1] and g[2])]
print("GATES", "all pass" if not bad else bad, len(gates))
for g in gates:
    if "placeholder" in g[0]: print("  ", g)
