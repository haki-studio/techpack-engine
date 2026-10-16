#!/bin/bash
# scaffold a new product: scripts/new_project.sh <style-slug>   (then drop mockups + size chart into projects/<slug>/inputs/)
set -e
R="$(cd "$(dirname "$0")/.." && pwd)"; S="$1"; [ -z "$S" ] && { echo "usage: $0 <style-slug>"; exit 1; }
P="$R/projects/$S"; mkdir -p "$P/inputs"
cat > "$P/README.md" <<EOR
# $S
Inputs: put mockups (front/back flats, element close-ups), the size chart (POM) and fabric/trim notes in inputs/.
Then in Claude Code: "Run the techpack-pipeline skill for projects/$S."
EOR
cat > "$P/inputs/brief.md" <<EOR
# Brief — $S
- Garment / fit block:
- Size range:
- Shell fabric + weight:
- Hardware / trims:
- Embroidery / print elements (where, process):
- Factory: frame sizes, needles per head:
- Deadline / sample stage:
EOR
git -C "$R" checkout -b "product/$S" 2>/dev/null || true
echo "created $P on branch product/$S"
