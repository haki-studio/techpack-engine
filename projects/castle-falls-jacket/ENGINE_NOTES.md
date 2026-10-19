# Engine notes from the Castle Falls jacket (16 Oct 2026)

Problems hit while building this product, worked around in project code only. Each: problem → proposed fix → check.

## 1. Studio background read as thread (white clouds at the sleeve fold and back shoulders)
- **Problem:** the mockup background (#E9E7E2) is the same colour as the cloud white. Any mapping that samples just outside the
  garment silhouette (sleeve folds, the render's sloping shoulders, bleed past the side seams) traced background as cloud white:
  a white wedge down both sleeve folds and white corners above the back shoulders.
- **Workaround:** `mockmap.no_background()` flood-fills light, low-saturation pixels connected to the image border and paints them
  the shell colour before any sampling.
- **Proposed fix:** `engine/mockup.py: load(path)` returns the mockup with a background mask; every tracer samples through it.
- **Check:** warp a sleeve whose outer edge lies 5 px outside the silhouette → 0 % white thread in the result.

## 2. Dark pixels: bare shell vs shadow thread
- **Problem:** treating every dark cluster as "fabric if the area is large" punched holes in dark rock / foliage shadows (FL castle
  rock was 30 % holes). The navy shell is BLUISH dark (b* < -4); shadows inside the art are neutral / greenish dark.
- **Workaround:** `trace.CLUSTER_THREAD`: bluish darks = shell candidates (fabric only where a 2.6 mm opening survives AND the area
  is mostly dark), neutral darks = `SHADOW` (never fabric; take the darkest thread of the neighbouring tone). Fabric-wash speckle
  (navy / slate inside a 12 mm window that is > 80 % shell) becomes shell.
- **Proposed fix:** an engine tonal tracer (moon `trace.py` + this `trace.py` are two copies of the same idea) with `fabric_lab`
  (the shell colour) + a hue rule for shell vs shadow.
- **Check:** a crop of dark rock next to bare shell → rock 100 % thread, shell 100 % fabric.

## 3. Automatic colour merge (≤ 12 per file) sacrificed the hero details
- **Problem:** merging by ΔE × sqrt(area) merged the castle gold into bark tan and the cloud cream into white (small areas are the
  important details).
- **Workaround:** hand-set `merge_plan.json` per piece (keeps gold / vermilion / three cloud tones where they matter), recorded on G3
  and each spec p4. `build_size.py` asserts ≤ `factory.max_threads()`.
- **Proposed fix:** `tech.merge_plan(vis, limit, keep=[...])` with a per-project "protected tones" list.
- **Check:** a protected tone is never merged; distinct colours ≤ limit on every file.

## 4. Gold never became a cluster
- **Problem:** gold trims are < 1 % of pixels, so 40-cluster k-means had no gold centre; gold traced as tan.
- **Workaround:** an explicit Lab rule before clustering (L > 52, b* > 27, -4 < a* < 22 → gold).
- **Proposed fix:** tracer accepts "named tones" (Lab boxes) that win over the clusters.

## 5. Jobs queued with `( heavy.sh ... & )` from a tool call died when that shell exited
- **Problem:** four of five size-M builds waiting for a slot never ran (empty logs); only the one that got a slot at once finished.
- **Workaround:** `run_build.sh` = `xargs -P` over `heavy.sh` started as one background job that stays alive.
- **Proposed fix:** document in CLAUDE.md "Running": launch queues through one long-lived background command (or `nohup`/`setsid`).
- **LESSON proposal (E8):** "Queued heavy jobs must belong to a process that outlives the launching shell; check every log has a
  first line within a minute." Check: `run_build.sh` prints `finished <size> <piece>` per job.

## 6. Sleeves traced from a flat lay + garment views on the technical flat
- `mockmap.sleeve_px()`: a sleeve pattern point maps by length fraction (cap top → cuff seam) and lateral fraction (centre fold =
  flat-lay silhouette, underarm = armhole seam / sleeve-body boundary) onto the front view (front half) or back view (back half).
  The render's sleeves are ~1.7× narrower than the pattern, so shapes stretch across; motif sizes stay library mm.
- `views.py`: the same parametric map in reverse puts the stitch render of each sleeve half on the technical flat sleeve. A 4-point
  perspective warp was badly wrong for the cap region (clouds smeared into a streak) — use the fold / underarm parametrisation.
- **Proposed fix:** move both to the engine (`engine/sleeve_map.py`), used by every wrap-around design.
- **Check:** a test sleeve with a grid → front view grid lines stay straight between fold and underarm.

## 7. split_clip search ranges (again)
- Same as Grand Line note 8: 40-60 % search range; this build execs a copy searching 30-70 % across and 15-85 % down
  (`build_size.split_clip_wide`, asserts if the engine source changes). Proposed: parameters on `split_clip`.

## 8. New motifs (in `cf_motifs.py`)
- 5-petal notched cherry floret (radial satin + centre dot, overlay on a traced blossom ground), notched falling petal,
  original 3-tier castle (flared hip roofs with tile lines + gold eaves, chidori gables, white walls with windows + studs, battered
  stone base with course lines). Proposed for the motif library with a render test each.

## 9. Fidelity-first cost (numbers for the record)
- A tone-for-tone trace of a dense AI render is very dense and has many trims (each traced tone island that later fills cannot
  hide is a trim). See G4 for the size-M numbers. Clean-up ideas for after the strike-off: merge tone islands < 6 mm² into their
  neighbour (now 2.5 mm²), drop the 90° lattice underlay under traced fills (density), order traced tones dark → light per area.

## 10. Stitch-level keep-out gate (new check, proposed LESSON)
- **Problem:** the art-outline clearance check (`emb_place`) passed while the FR stitch files of every size had ~11,000 stitches
  inside the welt keep-out (an earlier art build of FR filled the welt hole; the files were built from it, the outline check was
  run on a later, clean rebuild of the art). The documents would have certified files that sew over the pocket opening.
- **Fix (project):** `check_dst.py` reads every full DST back, places it by its origin on that size's pattern piece and counts
  stitches inside every keep-out (min - 0.5 mm). Run after every build; the pipeline (`run_all.sh`) stops on a failure.
- **Proposed engine fix + LESSON (A13/B25):** "Keep-outs are certified on the stitch files, not the art": `qa.dst_keepouts(dst,
  origin, keepout_lines)` + a test; packs print its result on T13.

## 11. Detail close-ups that are re-renders (LESSONS A12)
- Template matching of the strip panels against the mockup scored ~0.45 at wrong places: the panels are re-rendered
  compositions, not crops. Only the waterfall-mountain panel matched a mockup area well enough to register by hand
  (3 features, similarity scale 0.82) — it is blended into the source (`mockmap.CLOSEUPS`, elliptical feathered mask) and traced.
  The castle (IP-redrawn), blossom and cloud/petal panels became motif references (floret centres, petal bases, roof tiles).
- **Proposed:** `engine/closeup.py: register(panel, mockup, points)` + the feathered composite; reviewer overlay of the panel
  on the trace.

## 12. Close-up colour match + enclosed bare shell
- The registered close-up is darker / more contrasty than the mockup: its rock face classified as bare shell. Fix: per-channel
  mean/std match to the mockup under the blend mask before compositing (`mockmap.with_closeups`).
- Bare shell ENCLOSED by art (not connected to the open shell, < 4,000 mm²) is never a hole: it takes the neighbouring tone
  (light neighbours → their shadow tone). Rock faces and deep shadows stay stitched. (`trace.tone_map`)

## 13. Killing jobs on a shared box (E2 / E6 again)
- **Problem:** while stopping this project's pipeline I filtered `xargs` processes by an argv grep that included `build_size`,
  which matches every builder's queue — another project's `xargs` queue may have been killed with mine (wave-jacket had fresh
  jobs a minute later, so it may only have lost queued items).
- **Rule proposal (E8):** select processes by their working directory (`readlink /proc/<pid>/cwd` inside the project) AND an
  exact argv, never by a substring that other projects share. Better: each launcher writes its PIDs to `out/pids` and stops
  only those. Check: a stop helper `scripts/stop_project.sh <slug>` that only touches PIDs whose cwd is in the project.
