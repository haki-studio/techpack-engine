# RECAP 2026-10-20: engine M6, the puff / chenille / chain technique plugins (branch engine-m6-puff-chenille-chain)

## What was built and why
- `engine/digitize/techniques/puff.py` (`puff`): satin columns over foam. Rows are 0.20 mm apart. There is no underlay;
  an optional `tack` (an edge run on the cut line) is allowed. Rows are never split. Each open end gets a perforation
  run there and back across the end, then a cap: a small satin across the end that reaches 0.5 mm past it. Rings have no
  ends. Foam spec is 3 mm, colour matched, gate 2-4 mm. Allowed widths are 3-7 mm.
- `engine/digitize/techniques/chenille.py` (`chenille`): a PLAN only. The moss is a spiral of offset rings (holes
  included) or zigzag rows; the chain outline is closed on every edge ring, holes included. The stitch length is a
  constant chord length. Head settings (loop height, yarn, needle heights) are declared. It was promoted from
  projects/wave-jacket/chenille.py; Wave's files are untouched.
- `engine/digitize/techniques/chain.py`: `chain` is a true chain on a chenille head (plan only, constant chord length).
  `faux_chain` is the lock-stitch fallback for the Brother heads: an oval loop per link plus a hidden advance, with
  stitches of about 1.3 mm.
- `engine/digitize/techniques/specialty.py`:
  - `machine_of` and `isolate_foam`.
  - Gates: `plan_gates` (puff_no_fill, foam_stop), `puff_gates` and `faux_chain_gates` (both on the WRITTEN file's
    segments), `chenille_gates` and `chain_gates` (on the plan).
  - `export_chenille` raises `FactoryFormatNeeded` (F1); `write_chenille_plan` writes the neutral json.
  - `swatch_png` previews.
- `engine/digitize/swatch_m6.py` + `engine/digitize/swatches/m6.yaml`: the swatch run, with toggles as in a run.yaml.
- Shared files, additive blocks tagged `--- M6 ---`:
  - techniques/__init__ load hook.
  - config.DEFAULTS toggles (puff on, chenille on, chain OFF, faux_chain on).
  - house.yaml: 4 technique specs + kinds puff_column / chenille_fill / chain_line.
  - compile.write refuses chenille-head parts (`OtherMachine`).
  - test_digitize_m1 SYNTH: 4 entries.
  - factory.py F1 page section 5 (chenille machine + format).
  - factory.json: `chenille_format: null` + `open_questions`.
  - LESSONS: 4 rows `B?? (M6)`.

## Decisions (and the reasons, which the code does not show)
- **Puff max width is 7 mm, not the 10-12 mm in the brief.** The swatch showed it on the file: dst2.make_pattern splits
  every sewn stitch over 7.4 mm (LESSONS B7 / B17). On a 9 mm puff column that puts a needle point in the middle of
  every row, which perforates the foam mid-column. Changing dst2 is out of scope and would not preserve the defaults. Wider
  art becomes side-by-side columns. To raise the cap, the factory must accept longer stitches on puff AND make_pattern
  needs a puff exemption.
- **Chain default OFF.** A true chain needs the chenille head, and its file format is unknown. With default toggles
  chain_line sews faux_chain on the Brother heads. Turning chain on routes it to the chenille plan, and compile refuses it
  in a lock-stitch file.
- **Chenille has no lock-stitch fallback** (moss loops cannot be imitated). chenille off = RulebookError, as for every kind.
- **The format is never guessed.** export_chenille raises even if a format is set (there is no writer yet) and
  says so.
- Puff ends do BOTH perforation (Ignition) and cap (EmbPunch / Wilcom 0.5 mm past). The sources disagree, and doing
  both satisfies "closed ends" plus "cut-through edge".
- Puff stitches go in their own stop via `isolate_foam` (thread key `<thread>+foam`). Without it, colour batching put a
  same-thread flat part in the same stop, so there was no machine stop to lay the foam.

## Bugs found on the way (each now a gate and a test)
- Arc-length resampling sewed chords up to 27 % short on curves (uneven loops), so it was replaced by a chord walk.
- Wave's `ring_chain` followed only exterior rings, so the moss sewed across holes. Rings round holes are now included.
- The first faux_chain extended links along the tangent, which drifted 0.7 mm off a curved line. Links are now built
  along the line itself.

## Verification
- `python3 -m pytest -q tests`: **151 passed** (main 132 + 19 in tests/test_digitize_m6.py).
- Red->green: `scratchpad/m6/mutate_m6.py` applied 24 code mutations, and the M6 + M1 tests went red 24/24. After
  restoring, they are green. The first pass missed 3 (foam_stop mixed-only, chenille tol default, export
  fall-through); the tests were strengthened, then 24/24.
  - puff: satin_only threshold, density limit, perforation not required, cap not required, width gate, foam
    thickness, puff_no_fill, foam_stop mixed, isolate_foam no-op, caps not planned, check width.
  - faux chain: reads_as_chain always, links flattened.
  - chenille: const-length tolerance, coverage 0, pile-up, chain outline, head settings, spiral ignores holes, arc
    resample.
  - routing and defaults: export writes, compile guard, F1 section, chain default on.
- Default-preserving:
  - dst2 28-region probe: dst 84ff50ea74938675 / pes 1ecd8f657db3f53a (identical).
  - M5 wb svgrun DST: 449c14f6e8f693b6, 15,069 stitches, 161 trims (identical).
  - Castle crop through this branch: DST 0d86f00be8e9f8fa. All 208 gates.json values equal the M2 row except timing and
    path, so there is no bench row (M6 does not touch the crop).
- Swatch: 31/31 gates. Previews were looked at: projects/castle-falls-jacket/bench/swatch_m6_*.png, write-up in BENCH_m6.md.

## Open / next
- Factory (F1): which chenille machine, which format, whether loop and chain height are set in the file or at the
  machine, and which yarns. Puff strike-off: 3 mm foam, the look, and whether long stitches are OK on puff.
- No extractor yet makes puff / chenille / chain parts from art. The SVG path (M5) could map layers to the new kinds via
  a layer-name convention. Splitting wide puff art into columns is not built.
- The chenille plan json is neutral. Once the format is known, write the exporter and replace the raise.
- Previews are schematic, not photoreal.

## Part B: PR #7 review fixes (CHANGES, 20 Oct 2026)
1. **Puff safeguards on the real run path.** `compile.write` now calls `specialty.guard_puff(plan)` (next to the
   OtherMachine guard): it raises `PuffNotIsolated` when any puff plan gate fails: puff_no_fill (a puff KIND sewn as
   anything else - the first version only triggered on technique == "puff", so a tatami puff slipped through; a test
   caught it), foam_stop, **foam_isolated** (new: thread and stop key end in `+foam`), **base_under_puff** (new).
   Tested through the real `digitize.run.Run.make_plan` + `Run.compile` on a tmp project (tests/test_digitize_m6.py
   `test_run_path_*`). `sequence.py` NOT edited.
   **Foam-isolation contract (for M4g):** a puff part's thread / stop key ends in `+foam` (`specialty.FOAM`); that stop
   is the machine stop where the foam is laid and must NEVER be merged with a flat stop of the same colour (merging by hex
   colour would collapse it). Whoever plans puff parts calls `specialty.isolate_foam(plan)` before `sequence.order`;
   `compile.write` refuses the plan otherwise. LESSONS row `B?? (M6)`.
2. **Base under puff: knocked out** (coordinator decision, house rule 6). `specialty.knockout_under_puff(parts, keep)`
   removes the puff footprint minus `cut_keep_mm` (1 mm, house.yaml) from every LOWER lock-stitch part it overlaps (the
   run path already does this through `sequence.cut_under`; the swatch now calls the puff step). Gate
   `base_under_puff` = lower-part needle points inside the puff minus the keep band, on the planned blocks (and in the
   swatch on the DST's planned points too): target 0, swatch 0. Info: 2 base TRAVEL stitches (dst2's hidden travel,
   sewn before the foam) cross the hole; reported as `travel_under_puff`, not gated (changing dst2's router is out of
   scope). Preview `swatch_m6_puff_knockout.png` looked at: hole + 1 mm band visible.
3. **Hashes from the head run** (`scripts/identity_check.sh`, probe now in the repo as `scripts/byteid_probe.py`):
   probe dst 84ff50ea74938675 / pes 1ecd8f657db3f53a, M5 wb 449c14f6e8f693b6, crop 0d86f00be8e9f8fa - all unchanged.
- Nice-to-haves done: puff needle / spm declared PROPOSED (house.yaml, `foam_spec.machine`); factory.json asks about
  > 7.5 mm puff stitches; BENCH marks reads_as_chain as a geometric proxy and the chenille coverage / loop-height
  assumptions.
- pytest **155 passed**; mutations **29 / 29 red** (5 new: guard not called, guard on technique only, foam_isolated
  ignored, base_under_puff never counts, knockout no-op), restored green.
