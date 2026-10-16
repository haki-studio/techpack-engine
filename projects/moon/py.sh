#!/bin/bash
# run a project script with the engine on the path and the techpack venv: ./py.sh script.py args
D="$(cd "$(dirname "$0")" && pwd)"; R="$(cd "$D/../.." && pwd)"
PY="${TECHPACK_PY:-$HOME/techpack-engine/.venv/bin/python}"
export PYTHONPATH="$R/engine:$D:$PYTHONPATH"
cd "$D"
for f in inputs/*; do [ -e "$(basename "$f")" ] || ln -s "$f" "$(basename "$f")"; done
exec "$PY" "$@"
