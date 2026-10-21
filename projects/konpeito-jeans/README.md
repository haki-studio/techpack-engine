# Konpeito black jeans — tech pack (Rev B, 20 Oct 2026)

5-pocket washed-black jean on the Hidden Inventory pants silhouette (no cargo pockets). Waist sizes 26 28 29 30 31 32 33 34 36 38 40.
Brief + assumptions: `inputs/brief.md`. House patch spec: `.claude/skills/embroidery-tech-pack/SKILL.md`.

Build (from the repo root, `source scripts/env.sh projects/konpeito-jeans`):
```
python3 rectify.py && python3 classify.py      # mockups -> finished-mm rectified images + thread-family labels
python3 kjart.py                               # art -> out/art.pkl: 01/02/03 + stars from the founder's SVGs (kjsvg), haki traced
python3 kjfront.py                             # PROPOSED front-leg star map from the mockup (scale, origin, pocket opening) -> out/front_stars.json + out/check_07_mockup.png
python3 kjstitch.py                            # DST/PES per element + read-back json + previews
python3 kjsoot.py                              # 07 soot sprites (founder 21 Oct: kept): gates + out/compare_soot.png (after kjstitch front1 front2)
python3 kjcompare.py                           # gates vs the SVG (cairosvg per layer): centreline + motif_match + A15 + exposed stitches; compare sheets with live view
python3 kjstitch.py front1 front2 && python3 kjpages.py   # pages -> merged PDF (shrunk) + zip with elements/ + labels/ (kjlabels.py size loop labels) + README
```
Old 16 Oct scripts (build.py, wb.py, backstars.py, spec*.py) are kept for reference; the Rev A pack does not use them.

Fix pass 19 Oct (evening): founder change — stitch files digitised from inputs/svg (kjsvg.py); kjletter.py holds the column / petal / bead / gate helpers; kjstitch.trim_exposed trims every travel float. Before/after: out/fixpass_before_after_{wb,coin}.png.
