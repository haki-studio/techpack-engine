"""Generic primitive recognisers (ENGINE_PLAN G1): a LABELLED part's claimed pixels -> engine Parts, with no subject code.

A recogniser knows a SHAPE, never a subject: a waterfall, a trunk and a fish body are all cords; a sky, a cliff stratum
and a far roof row are all bands. Each one is built on the techniques and geometry the M1-M4 splitters already proved
(fall.cords, trunk.limbs / segments, cloud.lobes, stratum.mass_phase / bands_of, blossom.centres / Voronoi cells,
stratum.cracks' centreline, splitters.partition), called here through the labels contract only.

  recognise(ctx, lp, z, claim) -> (parts, used_mask)
     ctx    digitize.extract.splitters.Ctx (evidence, rulebook, run config, thread map)
     lp     the labelled part, resolved by digitize.labels.compile (dict: pid, motif, primitive, intent, angle, z, colour,
            confidence, params, tones, what)
     claim  the pixels this part may take (its windows AND its tones, minus higher parts' claims, seeds applied)

Directions are DECLARED, never auto (rule 2), and every one is re-derivable by digitize.audit:
  along / across   constructed from the part's own geometry (construct rules axis / column / long_axis), independent
  angle            the labeller's deliberate angle: DirSpec source "label", meta label_angle (audit basis)
  grain            guided fill along the reference grain: source "field" (SELF-DERIVED, LESSONS A24)
  outline          the lobe's long axis (construct rule long_axis, "outline" bucket)
  radial           rays from each centre (construct rule radial)
Kinds are the primitive names (house.yaml): stroke, cord, band, band_grain, lobe, lobe_grain, lobe_shade, plane, radial,
bead, line. Every part carries meta label (the labelled part id), motif, primitive, label_confidence."""
import math
import numpy as np
from digitize.schema import Part, DirSpec

REGISTRY = {}


def register(name):
    def deco(fn):
        REGISTRY[name] = fn; return fn
    return deco


def get(name):
    _load()
    if name not in REGISTRY: raise KeyError(f"no primitive recogniser {name!r} (have {sorted(REGISTRY)})")
    return REGISTRY[name]


def names():
    _load(); return sorted(REGISTRY)


def _load():
    from digitize.primitives import band, cord, stroke, lobe, plane, radial, dot, line  # noqa: F401  (registers)


# ---------------------------------------------------------------- shared helpers
def part(ctx, lp, kind, geom, thread, z, d, mask=None, **meta):
    """an engine Part for a labelled part: id <label>.<n>, zone = the motif (part map / review grouping), meta label"""
    m = dict(label=lp["pid"], motif=lp["motif"], primitive=lp["primitive"], label_confidence=lp["confidence"], splitter="labels")
    m.update(meta)
    rgb = ctx.ev.mean_rgb(mask) if mask is not None and mask.any() else None
    return Part(id=ctx.new_id(lp["pid"]), kind=kind, geom=geom, thread=thread, z=float(z), dir=d, zone=lp["motif"], rgb=rgb, meta=m)


def forced_thread(ctx, lp):
    """the thread for colour: <palette key> (through the run's tone -> thread map), else None (= from the pixels)"""
    c = lp.get("colour", "auto")
    if c in (None, "auto"): return None
    t = ctx.tone_thread.get(c)
    if not t: raise ValueError(f"label {lp['pid']}: colour {c!r} maps to no thread in this run (bare / merged away)")
    return t


def label_dir(lp, angle=None, mode="fixed"):
    """DirSpec for intent 'angle': the labeller's deliberate angle, audited from meta label_angle"""
    a = float(lp["angle"] if angle is None else angle)
    return DirSpec(a, mode=mode, source="label", note=f"label {lp['pid']}: deliberate angle"), {"label_angle": round(a % 180.0, 2)}


def union(gs):
    from shapely.ops import unary_union
    return gs[0] if len(gs) == 1 else unary_union(gs)


def lum(ctx, t):
    ev = ctx.ev; h = ev.hex[ev.keys.index(t)].lstrip("#") if t in ev.keys else "808080"
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4)); return 0.299 * r + 0.587 * g + 0.114 * b


def threads_in(ctx, mask):
    """[(thread, share)] of the mask's pixels, most first"""
    v = ctx.thread_lab[mask]; v = v[v >= 0]
    if not len(v): return []
    cnt = np.bincount(v, minlength=len(ctx.threads)) / len(v)
    return [(ctx.threads[k], float(cnt[k])) for k in np.argsort(-cnt) if cnt[k] > 0]


def silhouette(ctx, claim, close_mm=1.0, open_mm=0.4, fill=True):
    from scipy import ndimage as ndi
    m = claim.copy()
    if close_mm: m = ndi.binary_closing(m, ctx.disk(close_mm)) | m
    if fill: m = ndi.binary_fill_holes(m)
    if open_mm: m = ndi.binary_opening(m, ctx.disk(open_mm))
    return m


def axis_chord(g):
    """the long mid-line of g's minimum rotated rectangle as a construct "axis" line, or None when it does not rebuild
    (digitize.audit rule axis: midpoint on the part, length >= 1.5 x the part's mean width)"""
    from digitize.techniques.turning import long_axis
    from digitize.extract.splitters.construct import basis as cbasis
    gp = g if g.geom_type == "Polygon" else max(g.geoms, key=lambda q: q.area)
    a, b = long_axis(gp)
    line = [[float(a[0]), float(a[1])], [float(b[0]), float(b[1])]]
    probe = Part(id="_", kind="band", geom=g, thread="", z=0, dir=DirSpec(0.0), meta=dict(construct=dict(rule="axis", line=line)))
    ang, why = cbasis(probe)
    return (line, ang) if ang is not None else (None, why)


def long_axis_dir(g, note=""):
    """intent 'outline': the part's own long axis, construct rule long_axis (rebuilt by the audit from the geometry)"""
    from digitize.extract.splitters.construct import basis as cbasis
    gp = g if g.geom_type == "Polygon" else max(g.geoms, key=lambda q: q.area)
    con = dict(rule="long_axis", of=[[round(x, 3), round(y, 3)] for x, y in gp.exterior.coords])   # the traced outline, recorded
    probe = Part(id="_", kind="lobe", geom=g, thread="", z=0, dir=DirSpec(0.0, source="splitter"), meta=dict(construct=con))
    ang, why = cbasis(probe)
    if ang is None: return None, why
    return DirSpec(ang, source="splitter", note=note or "the part's own long axis"), dict(construct=con)
