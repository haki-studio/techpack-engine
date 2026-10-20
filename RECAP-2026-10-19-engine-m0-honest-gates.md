# RECAP 2026-10-19: ENGINE_PLAN M0 (honest gates, registration, benchmark)

## What was built and why
- **qa.visible_segments** (promoted from the castle `gates_dir.py`, which was never committed): z-buffer in sew order, so underlay and buried travel drop out. Signature `(segs, bounds, ppm=12, width_mm=0.42)`, absolute mm in and out.
- **qa.direction_match**: `visible=True` by default; raises below `min_ppm=12`. Also returns `ok_tiles` and `pct_chaos`.
- **qa.angle_coherence**: `key="part"`. It raises when a constructed region has no part id, fails `undeclared-angle` for "auto"/None, groups by (part, grp), and with `segs=` measures the spread on visible DST stitches.
- **New gates:** `density_map`, `trims_per_area` (via the new `readback.trim_points`), `satin_runs`/`satin_shape`, `stack_map`, plus the helpers `dst_runs` and `clip_segments`.
- **dstlive.render** takes `bounds=`/`origin=` for crops (defaults unchanged).
- **engine/digitize/extract/register.py:** registration as data (`projects/castle-falls-jacket/bench/registration.json`). It samples each close-up's own pixels for every output pixel, so a 12 ppm crop carries close-up detail rather than an upscaled mockup.
- **engine/digitize/bench.py --baseline:** writes `bench/SCOREBOARD.json`, `BENCH.md` and a panel PNG.

## Decisions
- **Crop shifted 5 mm up:** x −180…+20, y 365…565. In the requested crop, feather weight fell to 0.25 along the bottom 5 mm.
- **Satin detection** had to accept dst2's form (across stitch, 0.42 mm edge step, across stitch). The first detector missed nearly all real satins, and a test built from dst2's generators now guards this.
- **Radial fans** are counted but don't fail satin_shape: florets are legitimate fans, and telling one from a window fan needs the part map.
- **stack_map** counts a sewn run as a layer where its own thread reaches 1.5 mm/mm². It can under-count (objects joined by travel share a run) but never over-counts.

## Baseline numbers
In BENCH.md. Every gate fails. Direction is 11.7 % OK with 77.9 % chaotic (2.4 % on the old all-stitch score).

## Next (M1)
- The part map gives part ids to angle_coherence and decides whether each fan is a floret.
- Panel PNG is ~4 MB. Lower `panel_ppm` if it grows.
- Callers that now raise at ppm < 12: wave-jacket/gates.py and konpeito-jeans/kjcompare.py (tracked), plus untracked scripts in the main checkout.
