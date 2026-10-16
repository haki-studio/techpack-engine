# techpack-engine — Haki Studios

Turns garment mockups (often AI renders) into factory-ready tech packs: embroidery art, production stitch files
(DST/PES), hoop splits, a graded pattern (DXF + 1:1 PDF) and the garment tech pack PDF.

**Before any work: read `LESSONS.md`.** Every rule there came from a real mistake; the checks named there must
pass before anything is delivered.

## Layout
- `engine/` — reusable: stitch engine (`dst2.py`), stitch rules + thread matching + colour stops (`tech.py`),
  renderers (`stitchrender.py`, `render.py`), A4 sheet helpers (`sheet.py`, `specbase.py`), region QA (`qa.py`),
  motif library (`motifs.py`, `motifs2.py`), block from a POM chart (`drum.py`), pattern drafting + outputs
  (`pattern.py`, `pattern_draw.py`, `pattern_out.py`), thread palettes (`pal/`).
- `projects/<style>/` — one folder per garment: its scene/art builders, spec + pack page builders, run scripts,
  `inputs/` (mockups, references, fixed json). Outputs go to `projects/<style>/out/` (git-ignored).
- `.claude/skills/` — `techpack-pipeline` (end-to-end procedure) and `embroidery-tech-pack` (patches/labels house spec).
- `docs/ROADMAP.md` — what's generic vs project-specific today, and the plan to make batch runs possible.

## Running
```bash
source scripts/env.sh projects/drum-island-plum-pine      # sets PYTHONPATH=engine:<project>, cd into the project
python3 back_size.py XS S M L XL XXL 3XL                  # per-size back + sleeve art
python3 build_dst3.py B 02R 02L 03 04 nosplit             # graded front stitch files (A/B/C)
python3 build_size.py M                                   # per-size back + sleeve stitch files + 360² splits
python3 pattern_out.py qa dxf pdf                         # pattern QA, DXF per size + all sizes, 1:1 plot PDF
python3 build_all.py                                      # embroidery pack + garment pack -> merged PDF
```
Long jobs: background them; 2 at a time on a 2-core box, more locally (`xargs -P`).

## Conventions
- Units mm. Internal coords y DOWN. Garment coords: back = x from CB (+ = wearer's right on a back view), y from the
  CB neck seam; fronts = x from CF (+ = wearer's left), y from the CF neck seam. Pattern pieces use the same coords.
- Fit charts give HALF measurements for chest, sweep, bicep, opening — convert explicitly (LESSONS C2).
- Anything not given by the client is PROPOSED and printed in amber "[proposed — confirm]".
- Every number in a document is read from a generated file (stitch counts from the DST, measurements from the
  pattern), never estimated or typed.
- Render every page/preview to PNG and look at it before delivering.
- ≤ 15 threads per stitch file; DST trims are counted from the DST read-back.

## Delivery
One merged PDF (garment pages T*, then embroidery G* + element specs) + a zip with `elements/`, `pattern/`, README.
Recompress PDFs (`shrink.py`) before sending.

## Tests
`python3 -m pytest -q tests` — pattern vs chart for every size, seam walks, shape checks, stitch-engine smoke test. Run before every push.

## Learning loop (how this repo gets smarter)
- Sessions start with a `git pull` (hook in `.claude/settings.json`), so every session runs the latest engine + LESSONS.
- When you hit and fix a new problem: add a row to `LESSONS.md` (problem → rule → check), add or extend a test in
  `tests/`, and commit it with the fix. A lesson without a check is a TODO, not a lesson.
- One session per product, working in `projects/<style>/` on its own branch. Changes to `engine/` go in their own
  commit with tests passing, then merge to `main` (PR when several sessions are running) — never edit `engine/` in two
  sessions at once without merging between.
- New motifs go into the motif library with a render test, so the next product can reuse them.
