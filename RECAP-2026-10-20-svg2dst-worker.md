# RECAP 2026-10-20 — S2 svg2dst worker (techpack-engine side)

Founder priority 2026-10-20: PLM "SVG → DST" window, ASAP. This repo holds the Python worker; the page is plm PR (svg2dst branch).

## What / why
- `docs/SVG2DST.md` — the CLI contract (`scripts/svg2dst.py` → DST/PES/preview.png/result.json). **S1 has not started on a branch yet** (no `engine-s1-svg`, no doc on 20 Oct), so S2 proposed it; S1 implements or amends it (change contract.py + plm's contract.ts with it).
- `services/svg2dst/` — stdlib HTTP worker (no new deps), shared-secret auth, clean child env, outside-link/DOCTYPE refusal (cairosvg would fetch URLs / read files), 1 concurrent run, Dockerfile + railway.json.
- `stub_engine.py` — same contract, crude fill rows, one real question type (tiny colour → keep/drop) so the answer→re-run loop is testable. Hard gate `engine_real` always fails.

## Verified
- tests/test_svg2dst_worker.py 17 pass; full suite 292 pass. Guards proved red-then-green (secret leak to child env; outside-link refusal).
- NOT verified: the Docker image build (no docker on this box). Railway service NOT created (founder steps in README).

## Next
- S1 lands scripts/svg2dst.py → worker picks it up automatically; then remove SVG2DST_ALLOW_STUB.
