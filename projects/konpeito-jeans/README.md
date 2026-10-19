# Konpeito black jeans — tech pack (Rev A, 19 Oct 2026)

5-pocket washed-black jean on the Hidden Inventory pants silhouette (no cargo pockets). Waist sizes 24–40.
Brief + assumptions: `inputs/brief.md`. House patch spec: `.claude/skills/embroidery-tech-pack/SKILL.md`.

Build (from the repo root, `source scripts/env.sh projects/konpeito-jeans`):
```
python3 rectify.py && python3 classify.py      # mockups -> finished-mm rectified images + thread-family labels
python3 kjart.py                               # traced art -> out/art.pkl (coin, spill, wb, haki, stars)
python3 kjfront.py                             # PROPOSED front-leg star map -> out/front_stars.json
python3 kjstitch.py                            # DST/PES per element + read-back json + previews
python3 kjcompare.py                           # A14/A15 gates + out/compare_*.png
python3 kjpages.py                             # all pages -> merged PDF (shrunk) + zip with elements/ + README
```
Old 16 Oct scripts (build.py, wb.py, backstars.py, spec*.py) are kept for reference; the Rev A pack does not use them.
