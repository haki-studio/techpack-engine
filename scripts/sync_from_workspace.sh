#!/bin/bash
# copy the live workspace (cloud session) into the repo layout. usage: scripts/sync_from_workspace.sh /home/claude/jk
set -e
SRC="${1:-/home/claude/jk}"; R="$(cd "$(dirname "$0")/.." && pwd)"; P="$R/projects/drum-island-plum-pine"
ENG="dst2 tech stitchrender sheet specbase render drum motifs motifs2 qa pattern pattern_draw pattern_out"
SKIP=" back back_spec build_back garment export dst finish build_dst2 postdst back2_revB run_qa dst2_v2 dst2_test dst3_test dbg_route espec_revA spec2_revD pack_revD pack_revE gtp_revA back2_revC back2_revD front_revA finish2 "
for m in $ENG; do cp "$SRC/$m.py" "$R/engine/"; done
sed -i 's|TH = json.load(open("pal/threads.json"))|import os as _os\nTH = json.load(open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "pal", "threads.json")))|' "$R/engine/tech.py"
for f in "$SRC"/*.py; do b=$(basename "$f" .py); case " $ENG " in *" $b "*) continue;; esac; case "$SKIP" in *" $b "*) continue;; esac; cp "$f" "$P/"; done
for f in run_queue.sh final_build.sh; do [ -f "$SRC/$f" ] && cp "$SRC/$f" "$P/"; done
cp "$SRC/wrap_marks.json" "$SRC/emb_boxes.json" "$P/inputs/" 2>/dev/null || true
rm -f "$P/finish2.py"
echo synced
