# Recap 2026-10-16 — engine trim reduction (hidden-travel router, ROADMAP item 6)

Branch `engine-trim-reduction`. Engine only (`engine/dst2.py`), no project files changed.

## Method
- Built size-M / grade-B art fresh in this worktree (GL `scene.py` + `art_size.py M`, FB `flat_back.py` + `flat_front.py`,
  Moon `art_size.py M graded`), then the project build scripts (`build_size.py M nosplit`, `build_dst.py B ... nosplit`,
  `build_size.py M nosplit` + `build_grade.py B`) → baseline matches the batch numbers (GL 513, FB 950 / 419k, Moon 612).
- For A/B runs: a scratch bench (scratchpad `bench.py`) that rebuilds each full piece exactly as its project script
  does, against a frozen copy of the engine per variant (feature flags flipped), counts trims from the DST read-back.
  Lesson: never benchmark against the live `engine/` while editing it — later jobs import the edited file.
- Diagnostics added to `make_pattern` stats: `why` (trim = `island`: no hidden connection, vs `route`: same hidden
  area but the router gave up) and `runs` (every travel polyline) for the new `exposed_travel()` QA helper.

## Findings that drove the choices
- Baseline FB back: 686 trims, 287 of them `route` (router gave up inside a hidden area); 162 router calls refused
  only because the window was > 900k px. Moon: almost all `island` — clouds in 2-3 abutting tones, each later stop
  inset 0.25 mm on its own leaves a 0.5 mm strip on every tone seam.
- Kept: (a) merged later-stop mask (B21), coarse routing of big windows (B22), cell-by-cell tatami rows (B23).
- `exposed_travel()` found pre-existing exposure in the BASELINE too: travel routed through the 0.6 mm `own` halo
  (`p.buffer(0.6)`) of the object being sewn runs along its edge on top of the neighbouring earlier fill. Fixed:
  `OWN_HALO = 0.25` (B24), costs ~27 FB trims, halves runs exposed > 1 mm.

## State / numbers (size M / grade B full files, DST read-back, scratch bench)
| Project | Trims before → after | Stitches before → after | Machine h @750 spm |
|---|---|---|---|
| Grand Line (FR+FL) | 513 → 496 | 220,858 → 210,590 | 4.91 → 4.68 |
| Forestball (back+02R+02L) | 950 → 840 | 419,300 → 395,554 | 9.32 → 8.79 |
| Moon (back, 03L/R, 02L/R, 04L/R) | 612 → 260 | 298,325 → 265,467 | 6.63 → 5.90 |
Official project builds re-run with the new engine (incl. splits): all gates pass (max stitch ≤ 7.42, ≤ 14 threads,
every split section fits, placeholder boxes 0 stitches inside). Art untouched → keep-outs unchanged.
Tried and dropped: OWN_HALO 0.6 (variant c) had 27 fewer FB trims but twice the exposed travel; kept 0.25.
Delivered Rev A stitch files were NOT reissued — rebuild a product's files to pick up the savings. 
Tests: `tests/test_trims.py` (4 golden + helper), proven red with the old
behaviour (flags off) and green with the new.

## Could do later
- Remaining exposed runs (> 1 mm) are mostly straight moves within an object's own halo / over same-colour fill; a
  per-piece budget gate on `exposed_travel()` could go into the build scripts.
- Most remaining trims are `island` (no hidden connection): art/colour-order work (LESSONS B14), e.g. Grand Line sea dashes.
- (b) native `ko=False` overlays and (d) dashed-run: belong to the scene builders / need design input; not engine-router.
- (e) failed-route cache: only needed if the coarse router makes builds slow (measure FB back time).
