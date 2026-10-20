# Konpeito black jeans — tech pack (Rev A, 19 Oct 2026)

5-pocket washed-black jean on the Hidden Inventory pants silhouette (no cargo pockets). Waist sizes 24–40.
Brief + assumptions: `inputs/brief.md`. House patch spec: `.claude/skills/embroidery-tech-pack/SKILL.md`.

Build (from the repo root, `source scripts/env.sh projects/konpeito-jeans`):
```
python3 rectify.py && python3 classify.py      # mockups -> finished-mm rectified images + thread-family labels
python3 kjart.py                               # art -> out/art.pkl: 01/02/03 + stars from the founder's SVGs (kjsvg), haki traced
python3 kjfront.py                             # PROPOSED front-leg star map -> out/front_stars.json
python3 kjstitch.py                            # DST/PES per element + read-back json + previews
python3 kjcompare.py                           # gates vs the SVG (cairosvg per layer): centreline + motif_match + A15 + exposed stitches; compare sheets with live view
python3 kjpages.py                             # all pages -> merged PDF (shrunk) + zip with elements/ + README
```
Old 16 Oct scripts (build.py, wb.py, backstars.py, spec*.py) are kept for reference; the Rev A pack does not use them.

Fix pass 19 Oct (evening): founder change — stitch files digitised from inputs/svg (kjsvg.py); kjletter.py holds the column / petal / bead / gate helpers; kjstitch.trim_exposed trims every travel float. Before/after: out/fixpass_before_after_{wb,coin}.png.
