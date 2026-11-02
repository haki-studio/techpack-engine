# Dismantle Pants — Black / Tan check (Rev A, 27 Oct 2026) — INTERNAL sampling draft

Trouser on the Hidden Inventory (HI) pants fit + waistband with the founder's black / tan windowpane check. No embroidery.
Brief, sources and every assumption: `inputs/brief.md`. Model: `projects/konpeito-jeans` (same HI block).
PLM link: `plm.json` (product e05f184d-20f9-4aa9-be67-126d0d097344).

Build (from the repo root):
```
source scripts/env.sh projects/dismantle-pants
python3 dmpages.py        # runs dmprint (print measurements -> out/print.json), dmlabels (size labels), all pages,
                          # merged + shrunk PDF "out/Dismantle Pants - Rev A - INTERNAL.pdf" + zip with labels/
rm -f reference           # env.sh symlinks inputs/* into the project dir
```
Pages: T1 cover · T2 flats + mockup placeholders · P1 print spec · T3 POM (HI chart) · T4 pattern + check matching ·
T5 BOM · T6 construction + finish · T7 labels placement · T7b label artwork · Q1 open questions.

Files: `dmprint.py` (repeat / colour estimates from the reference photos, with the working), `dmflat.py` (flats: Konpeito
HI silhouette + check fill, copied not imported), `dmlabels.py` (HI centrefold size labels, copy of kjlabels), `dmpages.py`.
Rev A is internal only: no factory summary copy (LESSONS E15) until Q1 is answered.
