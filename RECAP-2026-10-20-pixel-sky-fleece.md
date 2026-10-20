# RECAP 2026-10-20 — Pixel Sky fleece tech pack (builder, branch tp-pixel-sky-fleece)

## Decisions
- Block: `projects/pixel-sky-fleece/fleece.py` = Drum Island (pattern.draft) on a swapped chart with pile ease
  (B +2, C +1, E +1, F +1, G +2, J +1 cm; D = chest because the hem is bound, not ribbed). Engine untouched (chart swap
  inside a context manager). Pattern QA passes XS–3XL (chart, seam walks, shape checks).
- Mockup scale: S = 0.601 mm/px from CF neck seam (y 368) → hem edge (y 1308) = A − K = 565 mm. The render is slimmer
  than the block (shoulder ~46 vs 53 cm): art keeps mockup sizes / heights; hidden body sides are generated.
- The AI render's pixel grid is NOT regular (edge-phase concentration ~0.2), so the jacquard is redrawn on our own grid.

## State
- inventory, pattern stages done + committed.
- In progress: jacquard cell maps (fronts, sleeves, back) + sparkle / bird embroidery.

## Next
1. jacquard grid per panel + mill files; 2. sparkle + bird SVG → digitize.svgrun → DST/PES + gates;
3. pages (J, G, F1, T) → merged PDF + zip; 4. PR + review dispatch.

## Progress (update 2)
- `pixels.py` colour classes + garment-detail masks (zip, pockets, bindings, collar; background = border-connected bright).
- `jacquard.py`: 2.5 mm cells, clouds traced on a 5 mm grid (global phase 1.25/1.25, purity 0.93), detail cells filled
  by 2-D neighbour majority (FILLED), hidden sides reflected (GENERATED), back = front mirrored (GENERATED), sleeves via
  `mockmap.sleeve_to_img` (back half mirrored). `python3 jacquard.py M` ~22 s. `jq_view.py` draws maps back into the mockup.
- `emb_art.py`: 20 sparkles traced (E1 F02 6, E2 F01 10, E3 S02 4) on own 1.8 mm staircase grids; bird = jacquard cells
  (E1B = bird + E1 sparkles, option B). SVG per file in out/art; `bench/run_E*.yaml` -> digitize.svgrun (sherpa_fill
  kind: tatami 0 deg, 0.40, pull 0.30). E1/E3 all gates pass; E2/E1B exposed-stitch + E1B tiny bird islands (fixed by
  widening the bird sample box to x -20) -> rerun with exact_travel max_ex 0.2.
- Gotcha: `cat > file` with no heredoc blocks forever in a backgrounded Bash call (lost 10 min).
