# Recap 2026-10-21 — tech pack coordinator pickup (session f8cacc7c)

## Why
The coordinator session 093e980c (detached builders + Konpeito Rev E review) crashed around 20:45 EDT on 20 Oct. Its background workers kept running.

## State found at 01:30 EDT
| Product | PR | Where it is |
|---|---|---|
| wave-jacket | #27 | fix round 3 running (tp-fix-wave-jacket, busy) |
| engine G1 | — | tp-build-engine-g1 busy |
| konpeito-jeans | #34 | review: CHANGES (3 fixable, 3 founder); fix round queued |
| pixel-sky-fleece | #28 | fix round 2 pushed (Rev C); re-review queued |
| keep-clean-our-space-hoodie | #31 | Rev E fix pushed; re-review queued |
| pro profiler | #35 | approved; live session e6ab25a5 owns it |
| svg2dst worker | #32 | stub until S1 |

Queue stalled: 2 idle tp- workers held slots (reaped by `--drain`) and the machine was at 1.7 GB free RAM, paging, load 13/8. The dispatch RAM floor is 6 GB, so nothing could start.

## Bug found + fixed (PR #36)
`dispatch.sh --dry-run --drain` popped every queued job and only printed it. I ran it as a preview and lost the 3 jobs; I re-queued them by hand. Fix + LESSONS E13 + red/green test. (E12 is taken by PR #35.)

## Running
A background loop in this session runs `--drain` every 10 min, for up to 6 h, until the queue is empty.

## Pending
- Founder decisions from 093e980c's note still stand (star haze, soot sprites, Mandy tolerances, API key, company-rule change).
- Main checkout `techpack-engine/` is on an old commit (755faf6) with many uncommitted edits in projects/*. I left it alone; whoever owns those edits should commit them.
