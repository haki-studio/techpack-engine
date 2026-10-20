"""Hard production gates on EVERY written stitch file (all sizes, full files + hoop sections), read back from the files:
max stitch < 7.5 mm, <= factory.max_threads() colours (factory.json, basting included: check_threads on the PES), each
hoop section fits the largest frame minus 2 x 8 mm, foam isolation + house rule 6 under puff (kcstitch.foam_gates), and the
keep-out clearances of every size (emb_place). Writes prod_gates.json + the size-M table; exits 1 on any failure.
usage: python3 prod_gates.py   (after make_current.py)"""
import kccore
import json, sys, os
import readback, factory
import emb_place as EP

PROF = factory.load(); FRAME = factory.largest_frame(PROF); LIM = factory.max_threads(PROF)
ALL = json.load(open("dst_all.json"))
fails = []; files = 0; rows = {}

SHEER = {"GLOW", "HAZE", "REG crosses"}
def straight_chains(path, per_stop, min_len=15.0, tol_deg=10.0):
    """straight lines inside sheer stipple stops (glow / haze): chains of >= 4 near-collinear stitches >= min_len mm
    (ENGINE_NOTES 22: Rev B FR M had 13, up to 57 mm) made of short stitches (0.5-2 mm: a stipple bridge; router travel
    is longer and is measured by dst2.exposed_travel). Returns [(stop, length mm)]."""
    import math, pyembroidery as pe
    sheer = {ps["stop"] for ps in per_stop if ps.get("codes") and set(ps["codes"]) <= SHEER}
    out = []; stop = 1; ch = []
    def flush():
        if len(ch) >= 4 and stop in sheer:
            d = math.dist(ch[0], ch[-1])
            if d >= min_len: out.append((stop, round(d, 1)))
    for x, y, c in pe.read(path).stitches:
        k = c & pe.COMMAND_MASK; P = (x / 10, y / 10)
        if k != pe.STITCH:
            flush(); ch = []
            if k == pe.COLOR_CHANGE: stop += 1
            continue
        if len(ch) >= 2:
            a = math.atan2(ch[-1][1] - ch[-2][1], ch[-1][0] - ch[-2][0]); b = math.atan2(P[1] - ch[-1][1], P[0] - ch[-1][0])
            if abs((b - a + math.pi) % (2 * math.pi) - math.pi) > math.radians(tol_deg) or not 0.5 <= math.dist(P, ch[-1]) <= 2.0: flush(); ch = [ch[-1]]
        ch.append(P)
    flush(); return out

def check(label, r, section=False):
    global files
    files += 1
    rb = readback.dst(r["file"] + ".dst")
    thr = factory.check_threads(r["file"] + ".pes", PROF)            # raises over the limit
    bad = []; sc = []
    if rb["max_stitch"] >= 7.5: bad.append(f"max stitch {rb['max_stitch']}")
    if thr > LIM: bad.append(f"{thr} colours")
    if section and not (rb["size_mm"][0] <= FRAME[0] - 16 and rb["size_mm"][1] <= FRAME[1] - 16): bad.append(f"section {rb['size_mm']} > frame {FRAME}")
    fm = r.get("foam", {})
    if fm.get("puff") and not (fm["foam_stop_ok"] and fm["base_under_puff_ok"]): bad.append(f"foam {fm}")
    if rb["stitches"] != r["stitches"]: bad.append("result json != DST read-back")
    sc = straight_chains(r["file"] + ".dst", r.get("per_stop", []))
    if sc: bad.append(f"straight lines in sheer stops {sc}")
    if bad: fails.append((label, bad))
    return dict(stitches=rb["stitches"], trims=rb["trims"], colours=thr, runs_exposed_gt1mm=r.get("runs_exposed_gt1mm"), max_exposed_mm=r.get("max_exposed_mm"), straight_sheer_chains=len(sc), max_stitch=rb["max_stitch"], size_mm=rb["size_mm"],
                foam=(None if not fm.get("puff") else dict(pause_before_stop=fm["pause_before_stop"], foam_stop_ok=fm["foam_stop_ok"],
                                                           flat_points_inside_foam=sum(fm["base_under_puff"].values()))))

for sz, d in ALL.items():
    for P, r in d.items():
        rows.setdefault(sz, {})[P] = dict(full=check(f"{sz} {P} full", r["full"]),
                                          sections={k: check(f"{sz} {P} {k}", s, True) for k, s in r.get("splits", {}).get("sections", {}).items()})
ko = EP.worst()
for lab, v, m, ok in ko:
    if not ok: fails.append((f"keep-out {lab}", [f"{v:.1f} < {m}"]))
out = dict(frame=FRAME, max_threads=LIM, files=files, keepouts=[dict(kind=a, min_mm=round(b, 1), required=c, ok=bool(o)) for a, b, c, o in ko],
           sizes=rows, fails=fails, ok=not fails)
json.dump(out, open("prod_gates.json", "w"), indent=1, default=float)
print(f"{files} files checked on frame {FRAME}, max {LIM} colours")
for P, v in rows.get("M", {}).items():
    f_ = v["full"]
    print(f"M {P}: {f_['stitches']:,} st, {f_['trims']} trims, {f_['colours']} colours, max {f_['max_stitch']} mm, exposed travel runs > 1 mm {f_['runs_exposed_gt1mm']} (max {f_['max_exposed_mm']} mm), hoopings {max(1, len(v['sections']))}, foam {f_['foam']}")
print("keep-outs:", ", ".join(f"{a} {b:.1f}/{c}" for a, b, c, o in ko))
print("FAILS:", fails if fails else "none")
sys.exit(1 if fails else 0)
