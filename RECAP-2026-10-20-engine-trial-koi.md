# RECAP 2026-10-20: engine trial on Koi Blossom (tag koi, branch engine-trial-koi)

## Goal
Answer the founder's question "is the engine's embroidery better than what we delivered?" on Koi Blossom (the FR upper
panel). The answer had to be a side-by-side the founder can judge by eye, plus the same gates on both written files.

Full write-up: `projects/koi-blossom-hoodie/bench/TRIAL.md`.

## Result in one line
- **Flowers and leaves:** the engine is better.
- **Fish:** the engine is worse.
- **Gates:** neither file passes (Rev B 1 of 8, engine 2 of 8 plus separation).
- **Not ready for a full Koi rebuild.**

## What was built

### Benchmark set-up (`projects/koi-blossom-hoodie/bench/`)
| file | what it is |
|---|---|
| `registration.json` | front.png in mockmap constants; the close-up bent onto the mockup by a TPS through the 10 tie points of `trace/closeup_reg.json` |
| `bench.json` | crop x -220 to -50, y 30 to 300 (170 × 270 mm, close-up weight 0.797) |
| `run_fr_crop.yaml` | the engine run; palette = the Rev B thread card plus 2 bare duck tones |
| `zones_FR.json` | 4 fish, 2 lilies with heart windows, vines, foliage |
| `trial_compare.py` | the comparison: gates, fidelity and PNGs |

### Engine changes
**New files:**
- `extract/splitters/lily.py`: the petal fan.
- `extract/splitters/fish.py`: the founder's tetra template at each fish pose.

**Additive edits under `# --- KOI ---`:**

| file | change |
|---|---|
| `construct.py` | rule `ray` (outline bucket) |
| `run.py` | `zero_bare` for `threads.bare`, and the fish / lily dispatch |
| `bench.py` | `targets.accents` (default: red + gold) |
| `splitters/__init__.py` | `Ctx.tone_thread` |
| `house.yaml` | 5 KOI kinds |

**Tests:** `tests/test_digitize_koi.py` has 10 tests. Each has a red mutation; the script is in the scratchpad at
`koi/mutate.py`:

| mutation | result |
|---|---|
| lily `min_prom` 1.0 | red |
| `RAY_OFF_MM` 10 | red |
| ray dropped from `OUTLINE_RULES` | red |
| peduncle rule inverted | red |
| dorsal sign ignored | red |
| dorsal side not chosen | red |
| `zero_bare` a no-op | red |
| `accents` ignored | red |

All went green again after restoring.

## Decisions and why
- **Crop size.** It is 170 × 270 mm, not 200 × 200. The close-up's frame is rotated, so no 200 mm square sits inside it
  at weight 0.6.
- **Rev B origin.** It was not recorded anywhere for the delivered Rev B build (the `result_FR.json` in out/M is from
  the later Rev C WIP build). I aligned the Rev B stitches on the Rev C stitches: dx -0.5, dy +8 mm, with 0 residual at
  5 px/mm.
- **The tetra, not the koi.** The founder decided on 19 Oct 2026 that the fish are tetras at 0.82 × length. The fish
  splitter takes the SHAPE from `inputs/reference_fish.png` and the POSE (eye, axis, length) from the registered
  close-up.
- **Protected colours.** `kb_cyan` is protected because it has no pixels in the koi close-up, but the tetra needs it.
- **Lily heart.** The heart is a hand-drawn window (where); the centre comes from the stamen pixels inside it (what).
  The first heart window caught the petal highlights and put the centre 12 mm off. It was tightened.
- **Gate references, two of them.** Reference (a) is refmask.py, built from mockup positions. Reference (b) is the
  registered close-up. **They disagree by about 13 mm on positions, so each file wins on its own source.** This is
  surfaced in TRIAL.md as a founder decision.
- **Exposed-travel proxy.** I built it on the DST only. With 0.5 mm cells it aliased against the 0.45 mm tatami rows
  (thousands of false hits). It now uses 1 mm cells, < 0.3 mm/mm² of other thread, and > 1 mm bare.

## Dead ends and what they showed
| what failed | what it showed |
|---|---|
| Lily petals at the default prominence: only 3 and 2 petals found | Overlapping petals have shallow valleys between them; the threshold is now `min_prom` 0.05 |
| Fish dorsal side read from stripe tones that included corn / royal | The template's belly is blue; only cyan marks the dorsal side |
| Fish eye dropped | `merge_specks` (4 mm²) ate the 2 mm² bead; eye and fins are now `keep_small` |
| Fish body in 11-19 pieces each | Caused by the template's anti-aliased navy rim; `edge_tones` now go to the main tone |

## State
| file | stitches | trims | stops | threads | gates |
|---|---|---|---|---|---|
| Engine crop DST (`out/digitize/KOI_FR_M_crop`) | 33,369 | 122 | 16 | 11 | 2 of 8 + separation |
| Rev B FR in the crop | 21,937 | 148 | - | 11 | 1 of 8 |

Full pytest: 212 passed. `scripts/identity_check.sh`: dst2 probe 84ff50ea74938675 / 1ecd8f657db3f53a, M5 wb 449c14f6e8f693b6, Castle crop 1963d24fc2d3d862, all unchanged from main.

## Left for the next session
1. **Fish quality:** silver / lavender body bands, fin-ray satin, lighter stripes, and the pose-source decision.
2. **Lily:** split overlapping petals and smooth the tone-piece edges.
3. **Vines:** the trunk splitter's support test rejected 8 of 9 components.
4. **Gates:** an independent petal rule, or a founder call on organic-only designs; and a Koi trims target.
5. **M7 pack path** for an engine-built design.

---

# Re-run after the founder ruling (2026-10-20, same branch / PR #13)

**Ruling (via the coordinator):** the GARMENT MOCKUP governs; the AI close-up only informs interior detail inside mockup
motifs. The gate references come from MOCKUP pixels.

## What changed

### Registration
- `bench/registration.json`: the close-up entry is now `mode: inform`, with one similarity fit per motif (written by
  `bench/inform_fit.py`).
- `bench/registration_mockup.json` (mockup only) is the gate reference.
- `bench.json` sets `closeup: null`. `bench.run_gates` accepts that: no feather mask.
- `run.yaml` gains `registration:`, the extraction source.

### Engine (each change additive)
| file | change |
|---|---|
| `extract/inform.py` (new) | `composite()` adds close-up detail only inside the mockup's largest silhouette in each window, where the close-up shows embroidery, shifted to the mockup motif's mean colour in Lab (the mean only, so the detail survives a flat 1 px/mm motif); `fit_similarity()` searches rotation × scale × cross-correlated shift |
| `register.reference` | hooks the informing close-ups |
| `sequence.underlap` | `meta tone_group`: tone pieces of one motif overlap by `TONE_SEAM_MM` 0.3 mm instead of 1 mm |
| `fish.py` | silver / lavender body bands (body read against `body_threads` only); tail cut at the peduncle (`tail_mask`); fins and tail as radial satin from the root; stripes ≥ 2 mm become body bands along the axis; thinner lines a light satin column (0.55 mm); eye in eye black (protected thread) |
| `house.yaml` | `fish_fin` uses radial and is added to radial `allowed_kinds` (a rule-4 exception asked for by the founder); `fish_stripe` spacing 0.55 |

### Fit results
| motif | IoU | informed? |
|---|---|---|
| upper lily | 0.66 | yes |
| lower dark flower | 0.41 | no (the mockup wins) |
| lower leaves | 0.40 | no |

### Zones
Re-authored on the MOCKUP layout: 4 fish, the pale upper lily, the dark lower flower, vines and foliage. The fish at the
crop's right edge is not built: its head lies outside the crop.

## Results
Mockup reference, Rev B vs engine:

| gate | Rev B | engine |
|---|---|---|
| fish motif_match | 4/5 | 4/5 |
| flora motif_match | 12/34 | 23/34 |
| uncovered | 741 mm² | 239 mm² |
| stitched on bare duck | 1,934 mm² | 109 mm² |
| satin blobs | 90 | 3 |
| density flags | 19 | 29 |
| max stack | 3 | 3 |
| bench gates | 1/8 | 1/8 |

**Verdict:** the engine is better on layout, the lily, and file cleanliness. Rev B is still better on fish finish (whiter
body, longer fin rays) and on stems: the engine's vine is broken up because the mockup's stems are faint at about
1 px/mm.

## Tests
`tests/test_digitize_koi.py` has 16 tests. Each guard has a red mutation (13 in the scratchpad at `koi/mutate.py`). The
new ones:
- inform: silhouette ignored
- inform: translation not searched
- inform: colour transfer off
- tone_group ignored
- tail cut at the widest section

Full pytest: 216 passed.

## PNGs
Copied to `C:\Users\devin\Desktop\koi-trial\`.

## Left for the next session
1. A vine continuity tracer.
2. Fish: a brighter body, and dorsal / pelvic fin size.
3. The dark lower flower's petals.
4. Gates: an independent organic rule; a Koi trims value from the founder.
5. M7 pack path.

---

# Salvage: generic parts only (branch engine-mockup-governs, 2026-10-20)

Founder decision: the engine must handle ANY mockup with generic shape primitives plus a vision step, never a rule per subject ("we are not going to go through the entire animal kingdom").

## What happened to PR #13
PR #13 had already been merged into main (ad0577c) by the time the salvage instruction arrived, although the plan was to keep it unmerged. This branch therefore works off that main and REMOVES the Koi-specific parts.

## Removed from main
- fish.py and lily.py
- the KOI kinds in house.yaml
- fish_fin in the radial allowed_kinds
- construct rule ray
- Ctx.tone_thread
- the run.py fish/lily dispatch
- tests/test_digitize_koi.py
- the projects/koi-blossom-hoodie/bench/ trial files

The trial record stays on branch engine-trial-koi and PR #13.

## Kept (generic, all with tests)
| part | what it does |
|---|---|
| extract/inform.py + the register.reference hook | informs per motif; the motif test is now colour-agnostic (distance from fabric only; blue/lum filters optional); IoU 0.5 acceptance is enforced inside composite (MIN_IOU) |
| bench.run_gates | accepts closeup: null (mockup-only reference, no feather mask) |
| bench targets.accents | lists the accents a design has |
| run.py | zero_bare / threads.bare; run.yaml registration: as the extraction source |
| sequence.underlap | tone_group plus TONE_SEAM_MM |

Tests: tests/test_digitize_mockup.py, 7 tests; 8 mutations each went red, then green on restore.

LESSONS row numbered A30.
