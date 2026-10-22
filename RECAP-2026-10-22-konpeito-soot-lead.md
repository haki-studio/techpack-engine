# RECAP 2026-10-22 — Konpeito soot sprites (lead session 630b0270)

## Diagnosis (18:50Z)
- Reference = `projects/konpeito-jeans/inputs/1792127150159_image.png` (front leg). Sprites are ~15 px (~1 mm/px).
  There was never a sprite SVG; `kjfront.trace_soot` reads eye positions + body Ø, `soot_regions` draws a generic sprite.
- Limbs: the reference arms (1-px lines to the held candies) sit below the tracer's grey<35 threshold, and the model only
  draws 2 stub legs. Eyes: pupils placed per eye from a 5x5 noisy window → different gaze per eye; white satin shows split lines.
- `kjsoot.py` gate measured centre / cover / blob count → 9/9 PASS on wrong art.
- Evidence: `~/.claude/company/missions/konpeito-soot-sprites/evidence_ref_vs_b7.png`.

## Plan
Hand art table per sprite (limbs + gaze) from the 10x reference, redraw eyes, add gates (limb count, gaze, eye size,
no split gaps) red on B7 / green on B8, visual compare page, reviewer, Rev B8. Builder: builder-konpeito-soot-sprites.
Branch stacked on PR #53 (standard labels).

## Scope added (~19:05Z, Chief): factory summary
Engine-level factory summary + leak gate (Pixel Sky Rev G pattern) + Konpeito factory summary PDF. Second builder
builder-konpeito-factory-summary on ~/te-konpeito-summary (off main). PR #53 merged; #54 is stuck on the standard-labels
branch (not main), flagged.
