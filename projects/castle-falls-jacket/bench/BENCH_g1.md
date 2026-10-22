# BENCH G1 — Castle crop through the labels contract (ENGINE_PLAN G1), 21 Oct 2026

Bench: castle-bk-m (crop x -180..20, y 365..565, BK size M, 12 ppm reference). Every number below is read from the WRITTEN
DST (compile.labelled_dst + bench.run_gates), recomputed in this session; no number is quoted from an older row.

- **main (8a6a58d, recomputed)**: `scripts/identity_check.sh` on origin/main at the branch base 8a6a58d: crop DST b0fcbbf67618a2d3,
  identical to the M4c SCOREBOARD row, so the rebuild is reproducible (the PR #37 reviewer rebuilt origin/main 796c4fc: same DST). BENCH_m4s.md quotes pre-#14 numbers (stale): this column replaces them.
- **main zones + G1 engine fixes**: the same zones + subject splitters, compiled with this branch's shared fixes (B39 join guard,
  split_satin declared column sewn once, no centre run on narrow strokes). Rebuilt at the branch head f229d0c with
  `scripts/identity_check.sh` (`digitize.run run_bk_crop.yaml`), 21 Oct 2026. The first version of this column (DST 8f7d5301,
  126,239 stitches) was built before 0db583c and e6e43fc and is replaced (PR #37 review).
- **G1 labels**: `bench/labels_BK.json`, written by the session by looking at `digitize.labels.sheet` (no API call), compiled by
  the generic primitives (no subject code). `bench/run_bk_crop_labels.yaml`.

| | main (8a6a58d, recomputed) | main zones + G1 engine fixes | G1 labels (session-written) |
|---|---|---|---|
| DST | b0fcbbf67618a2d3 | 911978994b664110 | 30df3600f5976174 |
| gates | 2/11 | 3/11 | 3/11 |
| dir OK on independent tiles (coverage) | 51.0 of 194 (31 %) | 51.0 of 194 (31 %) | 64.6 of 254 (41 %) |
| dir OK all | 64.6 | 64.8 | 67.8 |
| chaos % | 23.8 | 23.8 | 17.1 |
| random angles | 0 | 0 | 0 |
| coherence fails | 81 | 81 | 49 |
| density flags / mean | 174 / 5.26 | 164 / 5.26 | 139 / 4.88 |
| trims in the file (compile line) | 156 | 154 | 146 |
| trims in the crop (gate) (/100 cm2) | 152 (38.0) | 150 (37.5) | 143 (35.8) |
| satin blobs / cord flags | 1 / 0 | 0 / 0 | 0 / 0 |
| max stack / cm2 > 2 | 5 / 12.97 | 5 / 13.03 | 4 / 8.1 |
| stack by parts /100 cm2 | 1.08 | 0.0 | 0.0 |
| separation close | 25 | 25 | 8 |
| travel on sewn fill mm | 5776.6 | 6680.4 | 6384.3 |
| stitches (file) | 123,820 | 126,219 | 116,480 |
| parts | 980 | 980 | 962 |
| label-angle tiles (in independent) | - | - | 69 tiles, 59.4 % OK |

Trim counts. Both rows are read from the DST read-back (`readback.trim_points`). "In the file" is every trim in the DST (the
compile line, `gates.json` file.trims), the number a machine sews. "In the crop" is the bench gate (`qa.trims_per_area` with the
crop bounds): it keeps only trims whose needle position lies inside [x0, x1) x [y0, y1) and divides by the covered area. The
3-4 trims between them sit on the crop edge (<= 0.2 mm outside, e.g. x = 20.1 on the right edge x1 = 20): 4 on main zones + fixes,
3 on G1 labels, 4 on main. The gate's per-area number is the one every SCOREBOARD row uses, so the columns compare on it; the
file count is the true total. Main's file count (156) is the M4c SCOREBOARD row's `file.trims` for the same DST hash.

Verdict lines passed: main colours, stack_parts (2/11); main + fixes and G1 labels: satin_shape, colours, stack_parts (3/11).
**G1 labels matches the gate count of the subject splitters with the same engine and beats main (2/11)**, and is better on
every numeric gate except travel on sewn fill (+0.6 m vs main, -0.3 m vs main + fixes: the B39 short runs along the rows are
travel on fill by design; the gate counts them).

Reading it:
- Chaos 23.8 -> 17.1 %, coherence fails 81 -> 49, density flags 174 -> 139, stack 12.97 -> 8.1 cm2, rule 3 close pairs 25 -> 8.
- direction_ok still fails: independent tiles cover 41 % (< 50 %) at 64.6 % OK. 69 of those tiles are label angles (59.4 % OK):
  the labeller's plane angles for roofs / walls are the weakest; the rock (band grain, self-derived) stays 82 % OK.
- **Fidelity caveat (looked at the live view, BENCH_g1_side_by_side.png):** the falls, rock, foliage and blossoms read like
  main; the castle and pagoda read FLATTER than main's building fitter (planes and bands per tone, fewer red wall / window /
  member details). The generic primitives have no "window row" or "eave" yet: in G2 a building is a plane + stroke rows +
  dots labelled finer, or an expert behind the contract. Founder to judge.

## Experiments
Trim numbers here are file counts (compile line), measured during the session before 0db583c / e6e43fc; they show the
size of each switch, not the final column.

| run | result |
|---|---|
| `unsewn_only` hidden travel on the zones crop (`run_bk_crop_unsewn.yaml`, `compile: exact_travel unsewn_only`) | travel on sewn fill 5.8 -> 1.6 m, chaos 23.8 -> 19.2 %, coherence 81 -> 45, but trims x3 (441 /100 cm2 with the then-strict join guard; ~+645 trims from unsewn_only alone): NOT turned on by default. Run.yaml switch kept for the founder's call. |
| B39 strict join guard (`join_guard: all`) | trims 156 -> 1,445 (trim) / 1,158 (routed) / 722 (row ends excluded); default `parallel` (short runs along the rows) costs 0 trims. |
| strokes as `column_satin` | 19 curved limbs read back as satin blobs: strokes stay split satin (column mode). |

Side by side: `BENCH_g1_side_by_side.png` (top main zones + fixes rebuilt at f229d0c, bottom G1 labels: reference | part map |
live view | direction | density; half size, committed). The live view captions count stitches and trims inside the crop.

Generic, with one limit stated plainly: the primitives' own code has no subject words (AST guard test), but they call
existing helpers that live in subject-named modules (`fall.cords`, `cloud.lobes`, `blossom.centres`, `trunk`, `stratum`).
The guard ignores import paths, so "no subject code" holds for the primitives, not for those helpers. Moving the helpers
into neutral modules is a follow-up (G2).
