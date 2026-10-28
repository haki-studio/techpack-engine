# RECAP 2026-10-27/28 · KCOS pullover, Rev M from "Mockups 3" (lead-product-kcos-hoodie-pivot, session b2cf3b8a)

Nick approved the founder's "Mockups 3" (Desktop/HakiStop/Designs/Playtime/Keep Clean Our Space/Mockups 3.png) on 27 Oct.
Rev L (rule-based halving) is superseded and must NOT be sent. Rev M = stitch files + pack that match Mockups 3.

## Approach
- `mock3.py` (new): reads the star detector output (missions/kcos-hoodie-pivot/revm/stars.json, 225 blobs), drops badge /
  script / hood-V glint pixels, and maps every star to garment mm **by panel proportion** (body: HPS line → hem-rib seam,
  share of half width; pocket: trapezoid share; sleeves: along + across, front view = front half; hood: share from CB seam).
  The mockup is not to scale (its body is ~1.4x taller than wide; our Come Over block is about square), so one px→mm factor
  would have pushed stars off the pieces.
- `pv_art.py`: Rev M mode is now the only mode. Badges + script centred where Mockups 3 has them (badges still the Rev J
  art, translated only). Each mockup star → Rev J library unit of its kind (plus ≥ 6 px blob, else dot) at its size rank.
  Keep-out / split conflict → nudge ≤ 10 mm, else dropped and counted. Hoop cells cover only the art actually there.
  DENS_BY / random placement / zoned fallback removed.

## Gotchas
- Python env: `~/.venvs/techpack/bin/python`, `PYTHONPATH=<wt>/engine:<wt>`; copy art_M.pkl + inputs/fonts from ~/te-kcos-revl.
- Mockup star blobs include render glow: plus stars read ~8 mm, library plus units are 3.8-6.3 mm. Kept the library sizes.
