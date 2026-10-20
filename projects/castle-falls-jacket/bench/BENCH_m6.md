# BENCH M6: puff, chenille and chain technique plugins (swatch results)

M6 adds technique plugins; it changes nothing on the Castle crop (no crop kind uses them). The results here come from the
swatch run, not the crop:

```
PYTHONPATH=engine python3 -m digitize.swatch_m6 engine/digitize/swatches/m6.yaml --no-api
```

Every number below comes from `engine/digitize/swatches/out/m6/gates_m6.json`. Puff and faux chain are judged on the
written DST (`compile.labelled_dst`). Chenille and true chain are judged on their plan, because there is no machine
file for them until the factory answers F1.

## Swatch (toggles: puff on, chenille on, chain OFF, faux_chain on)

The lock-stitch file `m6_lock.dst` has 2,394 stitches, 3 trims and 3 stops: navy base, cream+foam puff, red chain. Its
longest stitch is 6.80 mm. All 2,296 planned segments were found in the file, plus 20 tie stitches the writer added.
The base is KNOCKED OUT under the puff (house rule 6, 1 mm kept under the puff edge, 102 mm2 removed; PR #7 review).

| part | gate | value | limit | result |
|---|---|---|---|---|
| plan | puff_no_fill | [] | puff parts are sewn by the puff plugin | ok |
| plan | foam_stop | no mixed stops, no flat part sewn after puff | own stop, after the flat work | ok |
| plan | foam_isolated | puff thread + stop key end in `+foam` | the foam-isolation contract | ok |
| plan + file | base_under_puff | 0 base stitches inside the puff minus the 1 mm band (planned blocks AND the DST's planned points) | 0 | ok |
| puff.straight (5 mm) | width / foam / satin_only / density / ends / row_len | 5.0 / 3 mm / 0.0 / 0.200 / 2 of 2 ends perforated + capped / 5.32 | 3-7 / 2-4 / <= 0.03 / <= 0.30 / all / <= 7.5 | ok |
| puff.arc (6 mm, curved) | same | 6.0 / 3 mm / 0.0 / 0.200 / 2 of 2 / 6.37 | same | ok |
| puff.ring (4 mm, closed) | same | 4.0 / 3 mm / 0.0 / 0.198 / no ends / 4.11 | same | ok |
| chain.line, resolved to **faux_chain** by toggles | on_line / short_stitches / reads_as_chain / no_gaps | 0.50 / 1.84 / 1.00 / 1.27 | <= 0.65 / <= 3.0 / >= 0.9 / <= 2.5 | ok |
| chenille.blob (plan) | const_stitch_len / moss_coverage / moss_no_pileup / chain_outline / head_settings | moss 0 %, chain 7 % / 0.937 / 0.0 / outline + hole closed / loop 4.0 mm, yarn [proposed] | +-10 % (chain +-15 %) / >= 0.90 / <= 0.05 / every ring / declared | ok |
| chain.true (plan, chenille head) | const_stitch_len / on_line | 0 % / 0.001 | +-15 % / <= 0.3 | ok |

**34 of 34 gates pass.** Info, not a gate: 2 base TRAVEL stitches (dst2's hidden travel, sewn before the foam is laid,
under the puff) cross the knocked-out area (`travel_under_puff`; visible in `swatch_m6_puff_knockout.png`). The chenille export raised `FactoryFormatNeeded: factory format needed (F1) ...`, as intended.

## Previews (looked at)

| file | what it shows |
|---|---|
| `swatch_m6_puff.png` | Rendered from the written DST. The three columns cover the foam completely, so no foam colour shows through. Both open ends have a cap that reaches 0.5 mm past the end. The ring has no ends. |
| `swatch_m6_puff_knockout.png` | The base alone over the puff footprint (light): the knockout hole, the 1 mm band kept under the puff edge, and the 2 travel stitches across it. |
| `swatch_m6_puff_end.png` | A 60 ppm close-up of one end. The cap runs ALONG the column across the cut edge. The perforation run sits under the cap and does not show. |
| `swatch_m6_chain.png` | Top: the faux_chain line read back from the DST (at 70 ppm it reads as crossed strokes, a rope / braid, more than discrete ovals - see the proxy note below). Bottom: the true-chain plan, drawn as links at a constant 2.0 mm. |
| `swatch_m6_chain_zoom.png` | Faux-chain links at 70 ppm. Each link is a closed oval of 4 stitches (~1.3 mm each) plus a hidden advance along the line. |
| `swatch_m6_chenille.png` | Moss spiral (loops) inside a chain outline. The hole has its own chain ring, and the moss goes round the hole without crossing it. |

The previews are schematic. They show paths, links and loops, not a photoreal render of yarn height.

## Red cases: each gate has a broken plan that fails it (tests/test_digitize_m6.py)

| broken plan | gate that fails | value |
|---|---|---|
| Puff column sewn as tatami | satin_only and plan puff_no_fill | > 0.3 interior points |
| Puff at flat density (0.42) | density | > 0.4 |
| No cap / no perforation (each alone) | ends_closed | - |
| Centre-run underlay over the foam (a tack on the edge is allowed and stays green) | satin_only | - |
| 2.5 mm column / 6 mm foam | width_in_range / foam_spec | - |
| 9 mm column: dst2 splits every row (LESSONS B17), which puts a split point in the foam | width_in_range + satin_only | > 0.3 |
| Puff in the same thread as a touching base, and separately a NON-touching part (mixed stop alone) | foam_stop, foam_isolated (compile refuses) | - |
| Real run path (`Run.make_plan` + `Run.compile`) without the `+foam` key / with keep 10 mm instead of 1 | compile raises PuffNotIsolated (foam_isolated / base_under_puff) | - |
| No knockout under the puff | base_under_puff (compile refuses) | > 50 planned base points |
| Faux chain replaced by run or by bean | reads_as_chain | < 0.2 |
| Arc-length resample of moss or chain | const_stitch_len | moss > 0.10 |
| Every other moss path / paths sewn twice / hole chain missing / no loop height | coverage / pile-up / chain_outline / head_settings | - |

On top of these, the code mutations in `scratchpad/m6/mutate_m6.py` turned the M6 and M1 tests red 29 of 29 times (24 + 5 for the review fixes). All
are listed in RECAP-2026-10-20-engine-m6.md.

## House practice behind the numbers (cited; [proposed - confirm] at the factory strike-off)

- **Satin only, never fill, on foam.** The satin's edges cut the foam, and fill flattens it. "Fill stitching will
  flatten the foam ... the thread is what cuts through the foam" ([Ignition Drawing, puff part 2](https://blog.ignitiondrawing.com/working-with-3d-puff-embroidery-part-2/print/)).
  Drawstitch warns that dense underlay flattens and slices the foam ([Drawstitch](https://www.drawstitch.com/blog/?p=2982)).
- **Density.** The house default is 0.20 mm and the gate is <= 0.30. Wilcom's webinar digitiser sews 0.18 mm with **no
  underlay**, uses 3 mm minimum / 12 mm maximum satin, foam of 3-4 mm and never over 4, and end caps ~0.5 mm past the
  satin end ([Wilcom: Q&A from 3D Puff Embroidery Webinar](https://wilcom.com/resources/blog/qa-from-3d-puff-embroidery-webinar)).
  Impressions gives about 2x flat density ([Impressions](https://impressionsmagazine.com/?p=170457)).
- **Ends.** Ignition: open ends need perforating. EmbPunch: close open ends with a small column across them, so the foam
  does not lift ([EmbPunch](https://www.embpunch.com/blog/What-is-3D-Puff-embroidery)). The plugin does both:
  perforation first, then the cap.
- **Width cap.** Published practice allows 10-12 mm. The house caps puff at 7 mm because of LESSONS B7 / B17 (no sewn stitch
  over 7.5 mm, and make_pattern splits at 7.4). This is a deliberate departure, and the swatch measured it (see LESSONS B?? (M6)).
- **Foam.** 3 mm, matched to the thread colour. Madeira E-Zee 3D foam is 3 mm and comes in colours ([Madeira E-Zee](https://www.madeirausa.com/e-zee-3d-foam/),
  [Madeira: creating 3D embroidery](https://www.madeirausa.com/resources/creating-3d-embroidery-with-3d-foam/)).
- **Chenille.** Loop height is set by the needle height of the chenille head, not by a stitch, and the stitch length must
  stay constant or the loop height varies ([Wilcom: controlling needle heights](https://docs.wilcom.com/embroiderystudio/28/en/OnlineHelp/Chenille/chenille_digitizing/chenille_digitizing-14.htm),
  [Wilcom: other settings](https://docs.wilcom.com/embroiderystudio/26/en/OnlineHelp/Chenille/chenille_digitizing/Other_settings.htm)).
  Open spiral / offset fills avoid yarn pile-up ([Wilcom: chain-stitch fills](https://docs.wilcom.com/embroiderystudio/26/en/OnlineHelp/Chenille/chenille_digitizing/Creating_chain-stitch_fills.htm)).
  Formats and needle-height codes differ by machine: Melco uses A-Z codes, and Barudan / Tajima use their own
  ([Wilcom: needle height](https://docs.wilcom.com/embroiderystudio/26/en/OnlineHelp/Chenille/chenille_basics/Needle_height.htm)).
  So the format is NOT guessed (F1).

## What the factory must answer (F1 page section 5, factory.json open_questions)

Which chenille machine they use, which file format it reads, whether loop/chain mode and needle (loop) height are set in
the file or at the machine, and which chenille yarns and colours they stock. Puff strike-off: confirm 3 mm foam and the
column look on their Brother heads, and whether they would sew stitches longer than 7.5 mm on puff.

## Assumptions and proxies (PR #7 review)
- `faux_chain` `reads_as_chain` is a GEOMETRIC PROXY: it counts needle points on both sides of the line in every link
  window, so a plain zigzag or braid at that spacing would pass too. At 70 ppm the sewn result reads as crossed strokes
  (a rope / braid) more than discrete ovals, and at 0.9 mm wide it may read as a twisted cord at real size. Needs a
  Brother strike-off before bulk.
- Chenille `moss_coverage` models a loop as 1.2 x spacing wide (2.4 mm at 2.0 mm spacing); the declared loop height
  (4.0 mm) is not checked against spacing. Both are assumptions until the factory's chenille head sews a swatch.
- Puff needle (75/11 sharp), speed (600 spm) and pull_comp 0 on foam are PROPOSED (house.yaml puff params), reported in
  the `foam_spec` gate as `machine` - confirm at the strike-off. factory.json open_questions asks whether Brother heads
  accept > 7.5 mm stitches on puff (the only blocker for wider columns).

## Default-preservation hashes (head run, `bash scripts/identity_check.sh`)
| check | value | expected |
|---|---|---|
| dst2 28-region probe (`scripts/byteid_probe.py`) | dst 84ff50ea74938675 / pes 1ecd8f657db3f53a | same |
| M5 wb svgrun DST | 449c14f6e8f693b6 (15,069 stitches, 161 trims) | same |
| Castle crop DST | 0d86f00be8e9f8fa (93,036 stitches, 111 trims, 3/9 gates) | same |
