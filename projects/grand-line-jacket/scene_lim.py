"""Size-independent keep-out areas in size-M coords (intersection of every size's clip scaled back by its grade)."""
import glcore
from shapely import affinity
import front as F
CLIP_M = {s: F.clip_for("M", s) for s in "RL"}
LIM_ALL = {}
for _s in "RL":
    _g = CLIP_M[_s]
    for _sz in glcore.SIZES:
        _k = glcore.GRADE[_sz][1]; _g = _g.intersection(affinity.scale(F.clip_for(_sz, _s), 1/_k, 1/_k, origin=(0, 0)))
    LIM_ALL[_s] = _g.buffer(0)
