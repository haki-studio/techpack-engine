# usage: source scripts/env.sh projects/<style>
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJ="${1:-projects/drum-island-plum-pine}"
# python deps (shapely, pyembroidery, cairosvg...): the system python has none of them (LESSONS E5)
if [ -z "$VIRTUAL_ENV" ]; then
  for v in "$ROOT/.venv" "$HOME/.venvs/techpack"; do [ -f "$v/bin/activate" ] && { source "$v/bin/activate"; break; }; done
fi
python3 -c "import shapely, pyembroidery" 2>/dev/null || echo "WARNING: engine deps missing - run scripts/setup_wsl.sh (or: python3 -m venv ~/.venvs/techpack && ~/.venvs/techpack/bin/pip install -r requirements.txt)"
export PYTHONPATH="$ROOT/engine:$ROOT/$PROJ:$PYTHONPATH"
cd "$ROOT/$PROJ"
# project inputs are read from the project dir
for f in inputs/*; do [ -e "$(basename "$f")" ] || ln -s "$f" "$(basename "$f")"; done
echo "PYTHONPATH set; in $(pwd)"
