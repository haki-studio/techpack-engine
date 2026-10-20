"""Benchmark harness (ENGINE_PLAN M0): run EVERY gate on a DST clipped to the benchmark crop, append one row to
<project>/bench/SCOREBOARD.json and BENCH.md, and save a panel PNG
(12 ppm reference | live view | direction heat-map | density map).

  python3 engine/digitize/bench.py --baseline                       # the shipped DST named in bench.json
  python3 engine/digitize/bench.py --dst path/to/new.dst --origin X Y --label "M1 skeleton"
  python3 engine/digitize/bench.py --baseline --dry-run             # print the row, write nothing

Reads only the DST (+ its .pes thread colours), the registered input pixels (digitize.extract.register) and, when
present, the scene regions pickle (for angle_coherence, which needs part ids). No Anthropic API calls."""
import argparse, datetime, hashlib, json, math, os, pickle, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.dirname(HERE)
if ENGINE not in sys.path: sys.path.insert(0, ENGINE)

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import qa, dstlive
from digitize.extract import register

ROOT = os.path.dirname(ENGINE)
DEFAULT_PROJECT = os.path.join(ROOT, "projects", "castle-falls-jacket")


def main_checkout():
    """root of the main checkout (worktrees share its .git): where git-ignored build outputs live"""
    try:
        g = subprocess.run(["git", "-C", ROOT, "rev-parse", "--git-common-dir"], capture_output=True, text=True, check=True).stdout.strip()
        return os.path.dirname(os.path.abspath(os.path.join(ROOT, g)))
    except Exception:
        return ROOT


def find(project, rel):
    """a project-relative path, here first, then in the main checkout (out/ and *.pkl are git-ignored)"""
    if os.path.isabs(rel): return rel if os.path.exists(rel) else None
    for base in (project, os.path.join(main_checkout(), os.path.relpath(project, ROOT))):
        p = os.path.join(base, rel)
        if os.path.exists(p): return p
    return None


def _hex(h): h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hue(rgb):
    import colorsys
    r, g, b = [v / 255 for v in rgb]; h, s, v = colorsys.rgb_to_hsv(r, g, b); return h * 360, s, v


def is_red(rgb): h, s, v = _hue(rgb); return (h < 15 or h > 345) and s > 0.45 and v > 0.35
def is_gold(rgb): h, s, v = _hue(rgb); return 30 <= h <= 55 and s > 0.40 and v > 0.45


def run_gates(cfg_b, project, dst, origin, regions_pkl=None):
    t0 = time.time(); crop = tuple(cfg_b["crop"]); view = cfg_b["view"]; ppm = float(cfg_b["ppm"])
    reg = register.load(os.path.join(project, cfg_b["registration"]))
    min_w = register.crop_inside(reg, view, crop, cfg_b["closeup"])
    if min_w <= cfg_b.get("min_weight", 0.6):
        raise SystemExit(f"crop {crop} is not inside close-up {cfg_b['closeup']} (min feather weight {min_w:.2f}); "
                         f"register.fit_crop suggests {register.fit_crop(reg, view, crop, cfg_b['closeup'])}")
    ref = register.reference(reg, view, crop, ppm=ppm)
    runs = qa.dst_runs(dst, origin)
    x0, y0, x1, y1 = crop; m = 8.0                                   # margin: a stitch reaching in from outside still occludes
    def near(s): return max(s[0], s[2]) >= x0 - m and min(s[0], s[2]) <= x1 + m and max(s[1], s[3]) >= y0 - m and min(s[1], s[3]) <= y1 + m
    allsegs = [s for r in runs for s in r["segs"]]
    order = [s for s in allsegs if near(s)]                          # sew order kept
    local = [(a - x0, b - y0, c - x0, d - y0) for a, b, c, d in order]
    clipped = qa.clip_segments(order, crop)
    out = dict(crop=list(crop), crop_min_closeup_weight=round(min_w, 3), stitches_in_crop=len(clipped))

    # direction: the visible top layer (gate) and every stitch (info, the old behaviour)
    dm = qa.direction_match(ref["grey"], ppm, local)
    dm_all = qa.direction_match(ref["grey"], ppm, local, visible=False)
    out["direction"] = dict(tiles=dm["tiles"], pct_ok=dm["pct_ok"], pct_chaos=dm["pct_chaos"], n_dev=len(dm["fail_dev"]),
                            n_chaos=len(dm["fail_chaos"]), pct_ok_all_stitches=dm_all["pct_ok"], pct_chaos_all_stitches=dm_all["pct_chaos"])

    # angle coherence: needs constructed regions with part ids (a DST alone has none)
    ac = dict(ok=False, note="no regions file: a DST carries no part ids, so angle_coherence cannot pass")
    if regions_pkl:
        from shapely.geometry import box
        D = pickle.load(open(regions_pkl, "rb")); B = box(*crop)
        regs = [dict(geom=r["geom"], stype=r.get("st"), angle=r.get("ang"), grp=r.get("grp"), unit=r.get("unit"), part=r.get("part"))
                for r in D["items"] if r.get("grp") in qa.CONSTRUCTED and r["geom"].intersects(B)]
        n_auto = sum(1 for r in regs if r["angle"] is None or r["angle"] == "auto")
        ac = dict(regions_file=os.path.basename(regions_pkl), constructed_in_crop=len(regs), no_part_id=sum(1 for r in regs if r["part"] is None),
                  auto_or_none_angle=n_auto, satin=sum(1 for r in regs if r["stype"] == "satin"))
        try:
            bad = qa.angle_coherence(regs, segs=qa.visible_segments(order, crop, ppm=ppm))
            ac.update(ok=not bad, fails=len(bad), kinds={k: sum(1 for b in bad if b["kind"] == k) for k in {b["kind"] for b in bad}})
        except ValueError as e:
            ac.update(ok=False, error=str(e).split(".")[0])
    out["angle_coherence"] = ac

    dens = qa.density_map(clipped, crop)
    out["density"] = dict(covered_cm2=round(dens["covered_mm2"] / 100, 1), mean=dens["mean"], p95=dens["p95"], max_smoothed=dens["max"],
                          over_cm2=round(dens["over_mm2"] / 100, 2), flags=len(dens["flags"]), threshold=dens["max_mm_per_mm2"])
    tr = qa.trims_per_area(dst, bounds=crop, origin=origin, area_mm2=dens["covered_mm2"])
    out["trims"] = dict(trims=tr["trims"], per_100cm2=tr["per_100cm2"], area_cm2=tr["area_cm2"])
    sat = qa.satin_shape(allsegs)
    inside = lambda p: x0 <= p[0] < x1 and y0 <= p[1] < y1
    sflags = [f for f in sat["flags"] if inside(f["at_mm"])]
    n_sat = sum(1 for r in qa.satin_runs(allsegs) if inside(r["at_mm"]) and not r["fan"])
    out["satin"] = dict(satins=n_sat, fans=sum(1 for r in sat["fans"] if inside(r["at_mm"])), blob=sum(f["kind"] == "blob" for f in sflags), too_wide=sum(f["kind"] == "too-wide" for f in sflags),
                        too_narrow=sum(f["kind"] == "too-narrow" for f in sflags))
    crop_runs = [dict(stop=r["stop"], segs=qa.clip_segments(r["segs"], crop)) for r in runs]
    crop_runs = [r for r in crop_runs if r["segs"]]
    st = qa.stack_map(crop_runs, crop)
    out["stack"] = dict(max=st["max"], over_cm2=round(st["over_mm2"] / 100, 2), flags=len(st["flags"]),
                        pct_cells_over=round(100 * float((st["grid"] > 2).sum()) / max(1, int((st["grid"] > 0).sum())), 1))
    out["runs_in_crop"] = len(crop_runs)

    pes = os.path.splitext(dst)[0] + ".pes"
    cols = [t.hex_color() for t in __import__("pyembroidery").read(pes).threadlist] if os.path.exists(pes) else []
    used = sorted({r["stop"] for r in crop_runs})
    hexes = sorted({cols[min(s, len(cols) - 1)] for s in used}) if cols else []
    out["colours"] = dict(stops_in_crop=len(used), threads_in_crop=len(hexes), threads_in_file=len(set(cols)), hex=hexes,
                          red=any(is_red(_hex(h)) for h in hexes), gold=any(is_gold(_hex(h)) for h in hexes))
    out["secs"] = round(time.time() - t0, 1)
    return out, dict(ref=ref, dm=dm, dens=dens, st=st, cols=cols, order=order)


def verdict(row, T):
    d, s = row["direction"], row["stack"]
    checks = {
        "direction_ok": d["pct_ok"] >= T["direction_pct_ok_min"],
        "direction_chaos": d["pct_chaos"] <= T["direction_pct_chaos_max"],
        "angle_coherence": bool(row["angle_coherence"].get("ok")),
        "density": row["density"]["flags"] <= T["density_flags_max"],
        "trims": row["trims"]["per_100cm2"] <= T["trims_per_100cm2_max"],
        "satin_shape": row["satin"]["blob"] <= T["satin_blobs_max"] and row["satin"]["too_wide"] == 0 and row["satin"]["too_narrow"] == 0,
        "stack": s["max"] <= T["stack_max_layers"],
        "colours": row["colours"]["threads_in_file"] <= T["colours_max"] and row["colours"]["red"] and row["colours"]["gold"],
    }
    return checks


# ------------------------------------------------------------------ panel
def _font(n):
    try: return ImageFont.load_default(size=n)
    except TypeError: return ImageFont.load_default()


RAMP = [(0.0, (22, 24, 34)), (1.0, (40, 60, 110)), (2.5, (40, 120, 170)), (5.0, (70, 190, 120)), (7.0, (240, 220, 60)), (9.0, (230, 40, 40))]
def ramp(v):
    v = np.asarray(v, float); out = np.zeros(v.shape + (3,))
    xs = [a for a, _ in RAMP]
    for c in range(3): out[..., c] = np.interp(v, xs, [col[c] for _, col in RAMP])
    return out.astype(np.uint8)


def panel(row, aux, cfg_b, dst, origin, path):
    P = float(cfg_b["panel_ppm"]); crop = tuple(cfg_b["crop"]); x0, y0, x1, y1 = crop
    W, H = int(round((x1 - x0) * P)), int(round((y1 - y0) * P))
    ref = Image.fromarray(aux["ref"]["rgb"].astype(np.uint8)).resize((W, H), Image.LANCZOS)
    live = dstlive.render(dst, aux["cols"], ppm=P * 2, shell=cfg_b["shell"], bounds=crop, origin=origin).resize((W, H), Image.LANCZOS)
    heat = live.convert("RGBA"); ov = Image.new("RGBA", heat.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov); T = aux["dm"]["tile_mm"]
    def tile(c, col):
        cx, cy = c; d.rectangle([(cx - T / 2) * P, (cy - T / 2) * P, (cx + T / 2) * P - 1, (cy + T / 2) * P - 1], fill=col, outline=col[:3] + (200,))
    for c in aux["dm"]["ok_tiles"]: tile(c, (40, 200, 60, 70))
    for r in aux["dm"]["fail_dev"]: tile(r["at_mm"], (230, 30, 30, 130))
    for r in aux["dm"]["fail_chaos"]: tile(r["at_mm"], (230, 0, 230, 130))
    heat = Image.alpha_composite(heat, ov).convert("RGB")
    den = Image.fromarray(ramp(aux["dens"]["grid"])).resize((W, H), Image.NEAREST); dd = ImageDraw.Draw(den)
    for f in aux["dens"]["flags"]:
        cx, cy = f["at_mm"][0] - x0, f["at_mm"][1] - y0
        dd.rectangle([(cx - f["w_mm"] / 2) * P, (cy - f["h_mm"] / 2) * P, (cx + f["w_mm"] / 2) * P, (cy + f["h_mm"] / 2) * P], outline=(255, 255, 255), width=2)
    dr, de, tr = row["direction"], row["density"], row["trims"]
    titles = [f"12 ppm reference (mockup + back_left close-up, min weight {row['crop_min_closeup_weight']})",
              f"live view (dstlive) - {row['stitches_in_crop']:,} stitches, {tr['trims']} trims ({tr['per_100cm2']}/100 cm2)",
              f"direction (visible layer): {dr['pct_ok']}% OK, {dr['pct_chaos']}% chaotic, {dr['n_dev']} off-grain  [all stitches: {dr['pct_ok_all_stitches']}%]",
              f"density mm/mm2: mean {de['mean']}, p95 {de['p95']}, {de['flags']} areas > {de['threshold']} (white boxes)"]
    pad, top, foot = 12, 34, 40
    im = Image.new("RGB", (4 * W + 5 * pad, H + top + foot), (245, 245, 242)); D = ImageDraw.Draw(im); f = _font(15)
    for i, (p, t) in enumerate(zip((ref, live, heat, den), titles)):
        X = pad + i * (W + pad); im.paste(p, (X, top)); D.text((X, 9), t, fill=(20, 20, 20), font=f)
    legend = ("heat-map: green OK, red off the reference grain > 25 deg, magenta chaotic (R < 0.55); 8 mm tiles.   density ramp: "
              "navy 1, blue 2.5 (one tatami layer), green 5, yellow 7, red 9+ mm/mm2.   "
              f"crop x {x0}..{x1}, y {y0}..{y1} mm (BK, size M, garment mm).   {row['label']}  {row['date']}")
    D.text((pad, H + top + 12), legend, fill=(60, 60, 60), font=_font(13))
    im.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(path, optimize=True)   # ~1 MB, committed
    return path


# ------------------------------------------------------------------ scoreboard
MD_HEAD = """# Benchmark - Castle Falls BK size M crop (ENGINE_PLAN M0)

Every engine milestone is scored on the same crop with the same gates (`engine/digitize/bench.py`). Rows are appended,
never edited. Config: `bench.json` (crop, targets), registration: `registration.json` (config as data).

**Crop.** ENGINE_PLAN asked for x -180...+20, y 370...570 mm. Its bottom 5 mm fell outside the back_left close-up's
registered region (feather weight down to 0.25 against the 0.6 threshold), so the crop is **x -180...+20, y 365...565 mm**
(shifted 5 mm up; min weight 0.647). Garment mm on the BK piece: x from CB (+ = wearer's right), y from the CB neck seam.

**Gates** (qa.py): direction_match on the visible layer at 12 ppm (>= 85 % OK, <= 5 % chaotic), angle_coherence per
part (needs part ids; a DST has none), density_map (areas over 7 mm/mm2), trims_per_area (<= 25 / 100 cm2 of covered
area), satin_shape (0 blobs, nothing > 7 mm), stack_map (<= 2 layers), colours (<= 12 threads, red and gold present).
"Dir all" = the old score over every stitch including underlay, for comparison only.

## Scoreboard

| date | label | dir OK % (visible) | chaotic % | dir all % | angle coh. | density mean / p95 / flags | trims / 100 cm2 | satins / blobs / >7 mm / <1 mm / fans | max stack / cm2 > 2 | threads (red, gold) | gates passed |
|---|---|---|---|---|---|---|---|---|---|---|---|
"""


def md_row(row):
    d, ac, de, tr, sa, st, co = (row[k] for k in ("direction", "angle_coherence", "density", "trims", "satin", "stack", "colours"))
    acs = "pass" if ac.get("ok") else ("FAIL: no part ids" if "error" in ac else f"FAIL ({ac.get('fails', 'n/a')})")
    v = row["verdict"]; npass = sum(v.values())
    return (f"| {row['date']} | {row['label']} | {d['pct_ok']} | {d['pct_chaos']} | {d['pct_ok_all_stitches']} | {acs} | "
            f"{de['mean']} / {de['p95']} / {de['flags']} | {tr['per_100cm2']} ({tr['trims']}) | {sa['satins']} / {sa['blob']} / {sa['too_wide']} / {sa['too_narrow']} / {sa['fans']} | "
            f"{st['max']} / {st['over_cm2']} | {co['threads_in_file']} ({'y' if co['red'] else 'n'}, {'y' if co['gold'] else 'n'}) | "
            f"{npass}/{len(v)} |\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=DEFAULT_PROJECT)
    ap.add_argument("--config", default="bench/bench.json", help="project-relative bench config")
    ap.add_argument("--baseline", action="store_true", help="score the shipped DST named in the config (baseline_dst)")
    ap.add_argument("--dst", help="DST to score (garment-mm origin from --origin or the result json next to it)")
    ap.add_argument("--origin", nargs=2, type=float)
    ap.add_argument("--regions", help="regions pickle for angle_coherence (default: config regions_pkl when found)")
    ap.add_argument("--label")
    ap.add_argument("--dry-run", action="store_true", help="print the row; write nothing")
    a = ap.parse_args(argv)
    project = os.path.abspath(a.project); cfg_b = json.load(open(os.path.join(project, a.config)))
    if a.baseline:
        dst = find(project, cfg_b["baseline_dst"]); res = find(project, cfg_b["result_json"])
        if not dst: raise SystemExit(f"baseline DST {cfg_b['baseline_dst']} not found here or in the main checkout ({main_checkout()})")
        regions = a.regions or (find(project, cfg_b["regions_pkl"]) if cfg_b.get("regions_pkl") else None)
        label = a.label or "baseline: shipped Rev B DST"
    elif a.dst:
        dst = os.path.abspath(a.dst); res = None; regions = a.regions; label = a.label or os.path.basename(dst)
    else:
        raise SystemExit("--baseline or --dst required")
    if a.origin: origin = tuple(a.origin)
    elif res: origin = tuple(json.load(open(res))["full"]["origin"])
    else: raise SystemExit("--origin X Y required (garment mm of the DST's 0,0)")
    print(f"bench {cfg_b['name']}: {dst}\n  origin {origin}, crop {cfg_b['crop']}, regions {regions}", flush=True)
    row, aux = run_gates(cfg_b, project, dst, origin, regions)
    row = dict(date=datetime.date.today().isoformat(), label=label, bench=cfg_b["name"], dst=os.path.relpath(dst, main_checkout()) if dst.startswith(main_checkout()) else dst,
               dst_sha256=hashlib.sha256(open(dst, "rb").read()).hexdigest()[:16], origin=list(origin), **row)
    row["verdict"] = verdict(row, cfg_b["targets"])
    print(json.dumps(row, indent=1, default=float))
    if a.dry_run: return row
    bdir = os.path.join(project, "bench"); os.makedirs(bdir, exist_ok=True)
    slug = "".join(ch if ch.isalnum() else "-" for ch in label.lower()).strip("-")[:40]
    png = os.path.join(bdir, f"panel_{row['date']}_{slug}.png"); panel(row, aux, cfg_b, dst, origin, png); row["panel"] = os.path.basename(png)
    sb = os.path.join(bdir, "SCOREBOARD.json")
    rows = json.load(open(sb)) if os.path.exists(sb) else []
    rows.append(row); json.dump(rows, open(sb, "w"), indent=1, default=float)
    md = os.path.join(bdir, "BENCH.md")
    if not os.path.exists(md): open(md, "w").write(MD_HEAD)
    with open(md, "a") as f: f.write(md_row(row))
    print(f"appended to {sb}, {md}; panel {png}")
    return row


if __name__ == "__main__":
    main()
