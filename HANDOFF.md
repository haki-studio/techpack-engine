# HANDOFF — /techpack batch (written 2026-10-19; previous coordinator session 98f15cbf)

Start a fresh coordinator session, read `LESSONS.md` (esp. A11 fidelity first, A12 trace from registered close-ups,
A13 trace stitch STRUCTURE not just tones, B5 ≤12 distinct colours per file, B20 numbers via `readback.dst`), then this file.
All builder work is committed on `main` (WIP commits "saved at session handoff"). No builder is running.

## How to continue each product
Launch one `techpack-builder` per product with: `Continue projects/<slug> from its current revision. Open fixes:
projects/<slug>/REVIEW_OPEN.md.` When it reports, launch a `reviewer` (fidelity first, private render dir), send
findings back, repeat until the reviewer says "reviewed". Builders don't pull (rule 1f31518); the coordinator syncs main.

| Product | State | Next |
|---|---|---|
| grand-line-jacket | Rev D delivered (clouds traced); Rev E in progress (WIP committed) | finish Rev E per REVIEW_OPEN.md, re-review |
| forestball | Rev B delivered; Rev C in progress (WIP) | finish Rev C per REVIEW_OPEN.md |
| moon | Rev B delivered; Rev C in progress (stitch-structure tracing, WIP) | finish Rev C per REVIEW_OPEN.md |
| comet-city-hoodie | Rev A delivered; Rev B art in progress (traced from closeups/closeup_mockup_comet.png) | finish Rev B per REVIEW_OPEN.md |
| castle-falls-jacket | Rev A rebuild in progress (close-up registration) | finish Rev A, deliver, first review |
| wave-jacket | stitch files done (132), in QA | finish QA + documents, deliver, first review |
| red-beast-hoodie, koi-blossom-hoodie, keep-clean-our-space-hoodie | embroidery Rev A delivered, not yet reviewed; pattern waiting on hood decision | first review; pattern after decisions below |

## Founder decisions pending
1. Hood block: keep the other session's `engine/hoodie.py` on main (coordinator's recommendation; elastic bands, body unchanged)
   or merge https://github.com/haki-studio/techpack-engine/pull/2 (narrower cuffs). Close the loser.
2. Hooded designs need a per-design welt (pocket) override: the mockups put welts at ~54–61°, further out than Drum Island's 38°.
3. Keep Clean text: proposed 不要污染地球 (CN) / 우주를 깨끗하게 (KR).
4. IP resemblance: Comet city ↔ 'Your Name'; Castle falls ↔ One Piece Wano. Built as original compositions.
5. Hooded backs / hoods / back half of sleeves plain?
6. Factory: frame sizes, puff (Keep Clean), chenille (Wave), thread board.

## Housekeeping
- Stash holds two autostash backups (3b55f3fe, e71be49) from shared-tree incidents; drop once builders confirm nothing is missing.
- Close-ups exist for: Grand Line (both fronts), Moon (back/front/sleeves), Forestball (front-right + one back view), Comet/Red beast/Koi/Castle/Wave (detail views from the mockups). Prompts for the rest: `projects/<slug>/inputs/closeup_request.md`.
