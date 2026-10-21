#!/bin/bash
# Default-preservation hashes for an engine change (wave 3 rule): run from the repo root of the checkout to test.
#   bash scripts/identity_check.sh            (all three; the crop is a heavy job, ~1 min, via scripts/heavy.sh)
# Expected (probe + wb on main since M2/M5):
#   dst2 28-region probe : dst 84ff50ea74938675 / pes 1ecd8f657db3f53a
#   M5 wb svgrun DST     : 449c14f6e8f693b6 (15,069 stitches, 161 trims)
#   Castle crop DST      : 911978994b664110 (126,219 stitches, 154 trims) after G1 / PR #37; main before it b0fcbbf67618a2d3
#                          (M4c). The crop changes on purpose when an engine change moves it: say so in the PR.
R="$(cd "$(dirname "$0")/.." && pwd)"
for v in "$R/.venv" "$HOME/.venvs/techpack"; do [ -f "$v/bin/activate" ] && { source "$v/bin/activate"; break; }; done
export PYTHONPATH="$R/engine"
cd "$R/projects/drum-island-plum-pine" && python3 "$R/scripts/byteid_probe.py"; echo "probe exit $?"
cd "$R"
scripts/heavy.sh python3 -m digitize.svgrun projects/konpeito-jeans/bench/run_wb_svg.yaml --stages extract,plan,compile --no-api 2>&1 | grep -E "^compile|Error|Traceback" | tail -2
echo "wb DST  $(sha256sum projects/konpeito-jeans/out/engine_m5/wb/*.dst | cut -c1-16)"
scripts/heavy.sh python3 -m digitize.run projects/castle-falls-jacket/bench/run_bk_crop.yaml --stages extract,plan,review,compile,gates --no-api 2>&1 | grep -E "^compile|^gates|Error|Traceback" | tail -3
echo "crop DST $(sha256sum projects/castle-falls-jacket/out/digitize/BK_M_crop/BK_M_crop.dst | cut -c1-16)"
