#!/usr/bin/env python3
"""Disk use of the techpack engine, and a safe cleanup.

  storage.py                 report: free space, size per product (deliverables vs regenerable), biggest files
  storage.py clean           DRY RUN: list what `clean --apply` would delete and how much it frees
  storage.py clean --apply   delete it
  storage.py clean --deep    also art caches (*.pkl — minutes to rebuild) and inbox/_done originals (copies live in inputs/)

What `clean` removes (all regenerable or duplicated; deliverables are kept):
  - superseded revisions in projects/*/out: for every PDF/zip family only the newest Rev is kept
  - projects/*/out/pkg/ (the unzipped copy of the delivery zip) and out/pages/ (page PDFs/PNGs already merged)
  - page previews prev_*.png / T*.pdf / G*.pdf fragments in project folders
Products that are still building (STATUS stage before 'delivered') are skipped unless --all.
"""
import os, re, sys, json, glob, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_FREE_GB = float(os.environ.get("TECHPACK_MIN_FREE_GB", "5"))
DONE = ("delivered", "review", "reviewed")

def size(p):
    if os.path.isfile(p): return os.path.getsize(p)
    return sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(p) for f in fs if not os.path.islink(os.path.join(r, f)))

def free_gb(path=ROOT):
    st = shutil.disk_usage(path); return st.free / 1e9, st.total / 1e9

def gb(b): return f"{b/1e9:6.2f} GB" if b >= 1e8 else f"{b/1e6:6.0f} MB"

REV = re.compile(r"_Rev([A-Z](?:-[A-Z])?)", re.I)

def superseded(files):
    """files of one folder -> the ones replaced by a newer Rev of the same family (name with the Rev token removed)."""
    fam = {}
    for f in files:
        m = REV.search(os.path.basename(f))
        if not m: continue
        key = (os.path.dirname(f), REV.sub("_Rev", os.path.basename(f)))
        fam.setdefault(key, []).append((m.group(1).upper(), f))
    old = []
    for k, v in fam.items():
        v.sort(); old += [f for _, f in v[:-1]]
    return old

def stage(proj):
    try: return json.load(open(os.path.join(proj, "STATUS.json"))).get("stage", "")
    except Exception: return "delivered"          # no status file = not a running batch product

def plan(deep=False, all_=False):
    out = []    # (path, bytes, why)
    for proj in sorted(glob.glob(os.path.join(ROOT, "projects", "*"))):
        if not os.path.isdir(proj): continue
        st = stage(proj)
        if not all_ and st not in DONE: continue
        o = os.path.join(proj, "out")
        files = [os.path.join(r, f) for r, _, fs in os.walk(o) for f in fs] if os.path.isdir(o) else []
        for f in superseded([f for f in files if f.lower().endswith((".pdf", ".zip"))]):
            out.append((f, size(f), "superseded revision"))
        for d in (os.path.join(o, "pkg"), os.path.join(o, "pages")):
            if os.path.isdir(d): out.append((d, size(d), "duplicate of the delivered zip/PDF"))
        for pat in ("prev_*.png", "prev2_*.png", "T[0-9]*.pdf", "G[0-9].pdf", "q[0-9].pdf"):
            for f in glob.glob(os.path.join(proj, pat)): out.append((f, size(f), "page fragment / preview"))
        if deep:
            for f in glob.glob(os.path.join(proj, "*.pkl")): out.append((f, size(f), "art cache (rebuild: minutes)"))
    if deep:
        d = os.path.join(ROOT, "inbox", "_done")
        if os.path.isdir(d): out.append((d, size(d), "inbox originals (copies are in projects/*/inputs)"))
    return out

def report():
    fr, tot = free_gb()
    print(f"Disk: {fr:.1f} GB free of {tot:.0f} GB" + ("   ⚠ LOW — builds pause below %.0f GB (TECHPACK_MIN_FREE_GB)" % MIN_FREE_GB if fr < MIN_FREE_GB else ""))
    rows = []
    for proj in sorted(glob.glob(os.path.join(ROOT, "projects", "*"))):
        if os.path.isdir(proj): rows.append((size(proj), os.path.basename(proj), stage(proj)))
    print(f"\n{'product':34s} {'size':>9s}  stage")
    for b, n, st in sorted(rows, reverse=True): print(f"{n[:34]:34s} {gb(b)}  {st}")
    for extra in ("inbox", ".git"):
        p = os.path.join(ROOT, extra)
        if os.path.exists(p): print(f"{extra:34s} {gb(size(p))}")
    print(f"{'TOTAL techpack-engine':34s} {gb(size(ROOT))}")
    pl = plan(); pd = plan(deep=True)
    print(f"\n`storage.py clean --apply` frees {gb(sum(b for _, b, _ in pl)).strip()}; with --deep {gb(sum(b for _, b, _ in pd)).strip()}.")

def clean(apply=False, deep=False, all_=False):
    pl = plan(deep, all_)
    for p, b, why in sorted(pl, key=lambda x: -x[1]): print(f"{gb(b)}  {os.path.relpath(p, ROOT)}   ({why})")
    tot = sum(b for _, b, _ in pl)
    if not apply:
        print(f"\nDRY RUN — would free {gb(tot).strip()}. Run with --apply to delete."); return tot
    for p, _, _ in pl:
        if os.path.isdir(p): shutil.rmtree(p, ignore_errors=True)
        elif os.path.exists(p): os.remove(p)
    print(f"\nfreed {gb(tot).strip()}; {free_gb()[0]:.1f} GB free now.")
    return tot

if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "clean": clean("--apply" in a, "--deep" in a, "--all" in a)
    elif a and a[0] == "free-ok":                   # used by heavy.sh: exit 1 when the disk is too full to start a build
        fr, _ = free_gb(); sys.exit(0 if fr >= MIN_FREE_GB else 1)
    else: report()
