"""Orphan fragments (engine gate digitize.gates_orphan): a tiny stitch block sewn in a DIFFERENT pass from a bigger block of
the SAME thread that it touches (e.g. a flat sliver sewn after the foam next to its puffed letter, KCOS Rev H).
usage:
  python3 scripts/orphan_fragments.py file.pes ...                 # the files given: exit 1 on any orphan
  python3 scripts/orphan_fragments.py --products [slug ...]        # the PROD GATE: every product's written production PES
        (gates_orphan.product_files), ratcheted against engine/digitize/orphan_baseline.json: a product at 0 fails on any
        orphan, the others fail only above their baseline
  options: --root DIR (checkout whose projects/*/out to sweep; default this one), --json out.json, --list (every hit),
           --baseline FILE (default engine/digitize/orphan_baseline.json),
           --update-baseline (lower the baseline to today's counts; never raises it)
exit 1 when the gate fails; 2 when a file cannot be judged."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))
from digitize import gates_orphan as GO


def judge(files, root, show):
    res, err = {}, 0
    for fn in files:
        try: r = GO.orphan_fragments(fn)
        except ValueError as e: print(f" ERR  {fn}: {e}"); err += 1; continue
        res[os.path.relpath(fn, root)] = {k: r[k] for k in ("n", "n_exempt", "blocks", "hits", "exempt")}
        if show or r["n"]: print(f"{r['n']:4d}  {os.path.relpath(fn, root)}")
        if show:
            for h in r["hits"]: print("        ", h)
    return res, err


if __name__ == "__main__":
    a = sys.argv[1:]
    opt = {k: a[a.index(k) + 1] for k in ("--json", "--root", "--baseline") if k in a}
    js, root = opt.get("--json"), os.path.abspath(opt.get("--root", ROOT))
    rest = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or a[i - 1] not in opt)]
    if "--products" not in a:
        if not rest: sys.exit(__doc__)
        res, err = judge(rest, root, "--list" in a)
        bad = sum(1 for r in res.values() if r["n"])
        print(f"ORPHAN files with orphans: {bad} of {len(res)}" + (f", {err} not judged" if err else ""))
        if js: json.dump(dict(params=GO.ORPHAN_DEFAULTS, files=res), open(js, "w"), indent=1, default=float)
        sys.exit(2 if err else 1 if bad else 0)
    bfile = opt.get("--baseline", GO.BASELINE); base = GO.load_baseline(bfile)
    by, counts, files, judged, err = GO.product_files(root, rest or None), {}, {}, {}, 0
    if not rest: by.update({s: [] for s in base.get("products", {}) if s not in by})   # a baseline product with no out/ at all
    for s, fs in by.items():
        res, e = judge(fs, root, "--list" in a); err += e
        counts[s] = sum(r["n"] for r in res.values()); files.update(res); judged[s] = len(res)
    blind = GO.unjudged(judged, base if not rest else {"products": {}}, rest)
    for s in blind: print(f" ERR  {s}: no production PES judged under {os.path.join(root, 'projects', s, 'out')}; a gate that saw nothing cannot pass")
    err += len(blind)
    for s in [s for s in counts if not judged[s] and s not in blind]: counts.pop(s)          # no stitch files, not asked for
    rk = GO.ratchet(counts, base)
    for s, r in rk["rows"].items():
        note = {"block": "FAIL (held to 0)", "over": f"FAIL ({-r['below']} over the baseline)", "ok": "ok",
                "lower": f"ok, {r['below']} below the baseline: lower it (--update-baseline)"}[r["status"]]
        print(f"ORPHAN {s:32s} files {len(by[s]):4d}  orphans {r['count']:6d}  limit {r['limit']:6d}  {note}")
    print("ORPHAN GATE", "PASS" if rk["ok"] else "FAIL")
    if "--update-baseline" in a and err:
        print("baseline NOT updated: some files or products could not be judged (an unjudged file is not a 0)")
    elif "--update-baseline" in a:
        json.dump(GO.lowered(base, counts), open(bfile, "w"), indent=1); print("baseline lowered where counts dropped:", bfile)
    if js: json.dump(dict(params=GO.ORPHAN_DEFAULTS, ratchet=rk, files=files), open(js, "w"), indent=1, default=float)
    sys.exit(2 if err else 0 if rk["ok"] else 1)
