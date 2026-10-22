# SVG → DST — the CLI contract (`scripts/svg2dst.py`)

Status: **implemented by S1, 2026-10-22** (`scripts/svg2dst.py`, `engine/digitize/extract/svg_auto.py`; parity and
open findings: `projects/konpeito-jeans/bench/PARITY_S1.md`). Proposed by S2 (PLM window), 2026-10-20. Until S1 lands, `services/svg2dst/stub_engine.py` implements this same contract with a
deliberately crude fill so the PLM window and the worker can be built and tested end to end. The stub
**always fails the hard gate `engine_real`**, so nothing it makes can be mistaken for a production file.

If S1 needs a different shape, change this file and `services/svg2dst/contract.py` in the same PR; the
PLM side parses `result.json` with a strict schema (`lib/embroidery/svg2dst/contract.ts` in plm) and
refuses anything it does not recognise, so a silent drift shows up as a clear error, not a wrong page.

No Anthropic API calls anywhere in this path. `--no-api` is accepted (and passed by the worker) so the
CLI matches the rest of the engine; it changes nothing here.

## Invocation

```
python3 scripts/svg2dst.py --svg IN.svg --width-mm 90 --fabric twill --hoop 300x300 \
    --out OUT_DIR [--answers answers.json] [--name design] --no-api
```

| flag | meaning |
| --- | --- |
| `--svg` | the founder's vector art (any SVG; no run.yaml) |
| `--width-mm` | finished width of the design in mm (height follows the art's aspect ratio) |
| `--fabric` | one of `twill`, `denim`, `jersey`, `fleece`, `pique`, `sherpa` → underlay / density / pull comp |
| `--hoop` | `WxH` in mm, e.g. `300x300`, `400x450` (factory.json `frames_mm`) |
| `--answers` | JSON object `{question_id: option}` from a previous run's `questions` (re-run with answers) |
| `--name` | base file name for outputs (default `design`) |
| `--out` | output directory (created) |

Exit codes: **0** files written (the design may still fail gates — read `ok`); **2** input refused
(message on stderr, and `result.json` with `error` if the out dir was writable); **1** engine crash.

## Outputs in `OUT_DIR`

`<name>.dst`, `<name>.pes`, `preview.png` (stitch simulation on fabric), and `result.json`:

```json
{
  "contract": "svg2dst/1",
  "engine": "svg2dst",              // or "stub"
  "engine_version": "git sha or semver",
  "ok": true,                       // every hard gate passed
  "inputs": {"width_mm": 90, "fabric": "twill", "hoop": "300x300", "answers": {}},
  "size_mm": {"w": 90.0, "h": 61.2},
  "stats": {"stitches": 12840, "trims": 14, "colour_changes": 3, "jumps": 40,
            "machine_minutes": 18.6, "max_stitch_mm": 7.0},
  "threads": [{"index": 1, "hex": "#1b2a4a", "name": "Isacord 3543", "brand": "Isacord",
               "code": "3543", "delta_e": 1.8}],
  "gates": [{"id": "fits_hoop", "label": "Fits the 300x300 hoop", "value": "90 x 61 mm",
             "limit": "300 x 300 mm", "pass": true, "hard": true}],
  "questions": [{"id": "q001", "text": "Layer 'stars' — fill or satin column?",
                 "options": ["fill", "column"], "default": "column"}],
  "warnings": ["..."],
  "files": {"dst": "design.dst", "pes": "design.pes", "preview": "preview.png"}
}
```

Rules the caller relies on:

- `threads` is in sewing order; `index` is 1-based and matches the colour stops in the DST.
- `stats.machine_minutes` uses `factory.machine_hours` (factory.json `spm`, trims, colour changes).
- `gates[].pass` is a boolean; `value` / `limit` are display strings. `hard: true` gates decide `ok`.
- `questions[].id` is stable across re-runs of the same SVG + inputs, so an answer can be passed back.
  An answered question disappears from the next run's `questions` (or the run says why it is back).
- `threads.length <= factory needles` (12) is a hard gate, never a silent merge.

## The worker (`services/svg2dst`)

An HTTP wrapper around this CLI for PLM. `POST /v1/convert` with
`Authorization: Bearer $SVG2DST_SHARED_SECRET` and JSON
`{svg, file_name, width_mm, fabric, hoop, answers}` → `{result, files: {dst, pes, preview_png} (base64),
duration_ms, log_tail}`. `GET /healthz` (no auth) → `{ok, engine}`. See `services/svg2dst/README.md`.
