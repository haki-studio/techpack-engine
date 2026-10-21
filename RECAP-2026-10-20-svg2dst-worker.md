# RECAP 2026-10-20 — S2 svg2dst worker (techpack-engine side)

Founder priority 2026-10-20: PLM "SVG → DST" window, ASAP. This repo holds the Python worker; the page is plm PR (svg2dst branch).

## What / why
- `docs/SVG2DST.md` — the CLI contract (`scripts/svg2dst.py` → DST/PES/preview.png/result.json). **S1 has not started on a branch yet** (no `engine-s1-svg`, no doc on 20 Oct), so S2 proposed it; S1 implements or amends it (change contract.py + plm's contract.ts with it).
- `services/svg2dst/` — stdlib HTTP worker (no new deps), shared-secret auth, clean child env, outside-link/DOCTYPE text check as a 2nd layer (the real defence is cairosvg>=2.7.1 with unsafe=False, pinned + tested), 1 concurrent run, Dockerfile + railway.json.
- `stub_engine.py` — same contract, crude fill rows, one real question type (tiny colour → keep/drop) so the answer→re-run loop is testable. Hard gate `engine_real` always fails.

## Verified
- tests/test_svg2dst_worker.py 17 pass; full suite 292 pass. Guards proved red-then-green (secret leak to child env; outside-link refusal).
- NOT verified: the Docker image build (no docker on this box). Railway service NOT created (founder steps in README).

## Next
- S1 lands scripts/svg2dst.py → worker picks it up automatically; then remove SVG2DST_ALLOW_STUB.

## Review round 1 (reviewer-svg2dst, CHANGES 6afea3a0) — fixed
- Bind "::" dual-stack (Railway private DNS may be IPv6-only).
- Pin cairosvg>=2.7.1; listener test proves no remote fetch for href / @import / url() / CSS-escape / nested data: payloads.
- check_result tightened to match plm contract.ts (size_mm, thread index/hex, question lengths, warnings, jumps).

## Approved
- REVIEW: APPROVE 02970449 (reviewer-svg2dst). S1 follow-up: point the remote_payloads no-fetch test at the real engine renderer when scripts/svg2dst.py lands.
