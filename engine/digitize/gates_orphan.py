"""Orphan fragments, read from the WRITTEN stitch file (PES; DST with its thread list). An orphan is a tiny stitch block
sewn in a DIFFERENT colour stop (pass) from a bigger block of the SAME thread that it touches: the machine sews the
sliver alone, after a trim, often on top of the wrong layer (KCOS Rev H, founder 21 Oct 2026: flat slivers of the EN
badge sewn after the foam next to their puffed letter, FL M 8, FR M 21). It belongs in the pass of the block it touches.

Why a file gate and not a project gate: the bug lived in project code (kcsatin / kcmotifs), which had been copied to
konpeito kjsatin and engine/digitize/techniques/column.py. A project fix does not reach the copies; a gate on the written
file of every product does (scripts/orphan_fragments.py --products).

  r = gates_orphan.orphan_fragments("out/.../HAKI_X_FL_M.pes")
  r["n"], r["ok"], r["hits"][i] -> {"stop": 7, "hex": "#ffffff", "stitches": 9, "at_mm": (x, y), "big_stop": 3, ...}

No Anthropic API calls."""
import pyembroidery as pe
from shapely.geometry import MultiPoint
from shapely.strtree import STRtree

# Why these numbers (scripts/orphan_fragments.py audit, coordinator 9487d766, 21 Oct 2026; re-measured in this PR):
# - max_stitches 60 / max_extent_mm 8: a sliver is a few stitches across a few mm. The Rev H slivers are 4-40 stitches
#   and < 6 mm; a real small motif sewn in its own stop (a star dot, a glint) touches nothing of its own colour.
# - ratio 3: the touching block must be clearly the main body (> 3x the stitches), not a sibling fragment.
# - touch_mm 0.3: hulls touching or overlapping (pull comp 0.2 mm + rounding); 0 on Konpeito / Grand Line / Forestball /
#   Red Beast / Koi / Comet and Rev I, so it does not need to be looser to be quiet on good files.
ORPHAN_DEFAULTS = dict(max_stitches=60, max_extent_mm=8.0, ratio=3.0, touch_mm=0.3, target=0)


def blocks(path, colours=None):
    """the file as stitch blocks: [(stop index 0.., thread hex lower, [(x, y) mm, ...])], a block = the stitches between
    two trims / jumps / colour changes (>= 2 stitches). PES carries its threads; a DST does not, so pass colours
    (one hex per stop, e.g. from the thread chart) or the gate raises: without threads 'same thread' is unknowable."""
    p = pe.read(path)
    if p is None: raise ValueError(f"gates_orphan: cannot read {path}")
    cols = [c.lower() for c in colours] if colours else [t.hex_color().lower() for t in p.threadlist]
    if not cols: raise ValueError(f"gates_orphan: {path} has no thread list; pass colours= (one hex per stop)")
    ci, out, cur = 0, [], []

    def flush():
        if len(cur) > 1: out.append((ci, cols[min(ci, len(cols) - 1)], list(cur)))
        cur.clear()
    for x, y, c in p.stitches:
        k = c & pe.COMMAND_MASK
        if k == pe.STITCH: cur.append((x / 10, y / 10))
        elif k == pe.COLOR_CHANGE: flush(); ci += 1
        elif k in (pe.TRIM, pe.JUMP): flush()
        elif k == pe.END: break
    flush()
    return out


def orphan_fragments(path, colours=None, exempt=None, **kw):
    """every tiny block touching a bigger same-thread block sewn in another stop. exempt(hit) -> reason or None: a hit
    with a reason is moved to r["exempt"] (each exemption needs its own guard test). Returns dict(n, hits, exempt, blocks,
    ok, params). Raises on a file with no stitch blocks: a gate that saw nothing cannot pass."""
    P = dict(ORPHAN_DEFAULTS, **kw)
    B = blocks(path, colours)
    if not B: raise ValueError(f"gates_orphan: no stitch blocks in {path}; a gate that saw nothing cannot pass")
    G = [MultiPoint(pts).convex_hull for _, _, pts in B]
    tree = STRtree(G)
    hits, ex = [], []
    for i, (s, c, pts) in enumerate(B):
        n = len(pts); g = G[i]; x0, y0, x1, y1 = g.bounds
        if n > P["max_stitches"] or max(x1 - x0, y1 - y0) > P["max_extent_mm"]: continue
        near = sorted(j for j in tree.query(g.buffer(P["touch_mm"])) if j != i)
        for j in near:
            s2, c2, pts2 = B[j]
            if s2 != s and c2 == c and len(pts2) > P["ratio"] * n and g.distance(G[j]) < P["touch_mm"]:
                h = dict(stop=s + 1, hex=c, stitches=n, extent_mm=round(max(x1 - x0, y1 - y0), 2),
                         at_mm=(round(g.centroid.x, 1), round(g.centroid.y, 1)), big_stop=s2 + 1, big_stitches=len(pts2),
                         sewn_after=s > s2)
                why = exempt(h) if exempt else None
                (ex if why else hits).append(dict(h, exempt=why) if why else h)
                break
    return dict(n=len(hits), hits=hits, exempt=ex, n_exempt=len(ex), blocks=len(B), ok=len(hits) <= P["target"], params=P)


# not production files (a directory under out/ that matches): package copies (pkg*, used only when a product has nothing
# else, e.g. moon), superseded revisions and backups, scratch and calibration runs, engine bench outputs (judged by
# digitize.run's own gates)
NOT_PRODUCTION = ("pkg", "old", "_", "before", "gate_cal", "engine_m", "digitize", "revc")
NOT_PRODUCTION_HAS = ("backup", "superseded")


def _production(rel):
    """rel: path under out/ (dirs + file name)"""
    dirs = rel.replace("\\", "/").split("/")[:-1]
    return not any(d.lower().startswith(NOT_PRODUCTION) or any(k in d.lower() for k in NOT_PRODUCTION_HAS) for d in dirs)


def product_files(root, slugs=None):
    """{slug: [written production PES under projects/<slug>/out, full files AND hoop splits, sorted]}; a product whose
    only files are its package copy (out/pkg*) is judged on that copy"""
    import glob, os
    proj = os.path.join(root, "projects")
    if not slugs and not os.path.isdir(proj): return {}                 # wrong root: nothing judged, the caller refuses it
    slugs = slugs or sorted(d for d in os.listdir(proj) if os.path.isdir(os.path.join(proj, d, "out")))
    res = {}
    for s in slugs:
        base = os.path.join(proj, s, "out")
        allf = sorted(f for f in glob.glob(os.path.join(base, "**", "*"), recursive=True) if f.lower().endswith(".pes"))
        rel = {f: os.path.relpath(f, base) for f in allf}
        prod = [f for f in allf if _production(rel[f])]
        if not prod:
            prod = [f for f in allf if rel[f].split(os.sep)[0].lower().startswith("pkg") and _production(os.sep.join(rel[f].split(os.sep)[1:]))]
        res[s] = prod
    return res


# --- ratchet (lead, 22 Oct 2026): products at 0 block on any orphan; the rest may not get WORSE than their committed
# baseline (orphan_baseline.json, per product = the sum over its production files). When a count drops, lower the baseline
# in the same PR (--update-baseline only ever lowers). A product missing from the baseline is held to 0.
BASELINE = __file__.rsplit("/", 1)[0] + "/orphan_baseline.json"


def load_baseline(path=BASELINE):
    import json
    return json.load(open(path))


def ratchet(counts, baseline):
    """counts {slug: orphans}; baseline {"products": {slug: max}} -> dict(ok, rows {slug: dict(count, limit, status,
    below)}). status: 'block' (limit 0, any orphan fails), 'over' (above baseline: fails), 'ok', 'lower' (below the
    baseline: passes, lower the baseline)."""
    rows = {}
    for s, n in sorted(counts.items()):
        lim = int(baseline.get("products", {}).get(s, 0))
        st = ("block" if n else "ok") if lim == 0 else "over" if n > lim else "lower" if n < lim else "ok"
        rows[s] = dict(count=n, limit=lim, status=st, below=lim - n)
    return dict(ok=not any(r["status"] in ("block", "over") for r in rows.values()), rows=rows)


def lowered(baseline, counts):
    """the baseline with every product's limit lowered to its count where the count is lower (never raised)"""
    b = dict(baseline, products=dict(baseline.get("products", {})))
    for s, n in counts.items():
        if s in b["products"] and n < b["products"][s]: b["products"][s] = n
    return b


def unjudged(judged, baseline, asked=()):
    """products the gate must refuse to pass because it judged NO file of them (a gate that saw nothing cannot pass, per
    product too: a wrong --root, an emptied out/ or a typo'd slug would otherwise turn a held-to-0 product green).
    judged {slug: files judged}. A product counts if it is in the baseline or was asked for by name; a product folder
    with no stitch files that nobody asked about (e.g. a pattern-only block) is not an error."""
    want = set(baseline.get("products", {})) | set(asked)
    return sorted(s for s in want if judged.get(s, 0) == 0)
