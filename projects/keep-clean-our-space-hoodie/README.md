# Keep Clean Our Space hooded jacket (washed black, four neon text badges + star field)
Built by the /techpack command. Inputs + brief in inputs/, outputs in out/ (git-ignored).

Run order (`source scripts/env.sh projects/keep-clean-our-space-hoodie`; fonts: `./get_fonts.sh`):
1. `python3 specks.py` — star speckles detected on the mockup
2. `python3 scene.py` — badges (text set from fonts, kclettering) + star field on the size-M pieces
3. `python3 art_size.py` — per-size art (badge nudge solver, star placement), `python3 compare.py M` — fidelity sheets
4. `scripts/heavy.sh python3 kcstitch.py <size>` — FR / FL / SR / SL stitch files + hoop splits (puff pause stops)
5. `python3 emb_place.py` — keep-out clearances, every size
6. `scripts/heavy.sh python3 build_all.py` — numbers from the DSTs → embroidery pack → merged + shrunk PDF; `python3 finish.py` — zip
Pattern + garment pages wait for the hooded block (ENGINE_NOTES 10).
