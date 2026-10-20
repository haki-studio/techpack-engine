"""Numbers for documents, read back from the written stitch file (LESSONS B8, B9, D3, B20).

Every per-stop, per-file count printed in a pack comes from here, never from region estimates or build-time stats.
Trims are counted from the DST (PES read-back inflates them, B8).

  rb = readback.dst("out/.../HAKI_X_01_back_M.dst")
  rb["stitches"], rb["trims"], rb["stops"]            # file totals
  rb["per_stop"][i] -> {"stop": 1, "stitches": .., "trims": .., "jumps": ..}
"""
import math
import pyembroidery as pe


def dst(path):
    p = pe.read(path)
    per = [dict(stop=1, stitches=0, trims=0, jumps=0)]
    L, prev = [], None
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK
        cur = per[-1]
        if k == pe.STITCH:
            cur["stitches"] += 1
            if prev is not None: L.append(math.hypot(x - prev[0], y - prev[1]) / 10)
            prev = (x, y)
        elif k == pe.TRIM: cur["trims"] += 1; prev = None
        elif k == pe.JUMP: cur["jumps"] += 1; prev = None
        elif k == pe.COLOR_CHANGE:
            per.append(dict(stop=len(per) + 1, stitches=0, trims=0, jumps=0)); prev = None
        elif k == pe.END: break
    while len(per) > 1 and per[-1]["stitches"] == 0:          # trailing change/trim before END is not a stop
        last = per.pop(); per[-1]["trims"] += last["trims"]; per[-1]["jumps"] += last["jumps"]
    ex = p.extents()
    return dict(stitches=sum(s["stitches"] for s in per), trims=sum(s["trims"] for s in per),
                jumps=sum(s["jumps"] for s in per), stops=len(per), per_stop=per,
                max_stitch=round(max(L), 2) if L else 0.0,
                size_mm=(round((ex[2] - ex[0]) / 10, 1), round((ex[3] - ex[1]) / 10, 1)))


def trim_points(path):
    """Needle position (mm, DST frame) of every TRIM in the written file, in sew order: the last stitch before the trim
    (the command's own position when nothing was sewn yet). len(trim_points(f)) == dst(f)["trims"] (tests)."""
    p = pe.read(path); out = []; prev = None
    for x, y, cmd in p.stitches:
        k = cmd & pe.COMMAND_MASK
        if k == pe.STITCH: prev = (x / 10.0, y / 10.0)
        elif k == pe.TRIM: out.append(prev if prev is not None else (x / 10.0, y / 10.0))
        elif k == pe.END: break
    return out
