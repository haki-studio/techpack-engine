# usage: source scripts/env.sh projects/<style>
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJ="${1:-projects/drum-island-plum-pine}"
export PYTHONPATH="$ROOT/engine:$ROOT/$PROJ:$PYTHONPATH"
cd "$ROOT/$PROJ"
# project inputs are read from the project dir
for f in inputs/*; do [ -e "$(basename "$f")" ] || ln -s "$f" "$(basename "$f")"; done
echo "PYTHONPATH set; in $(pwd)"
