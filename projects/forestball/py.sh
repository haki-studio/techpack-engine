#!/bin/bash
# run a project script with the engine on the path and the techpack venv:  ./py.sh back_build.py ...
D="$(cd "$(dirname "$0")" && pwd)"; R="$(cd "$D/../.." && pwd)"
cd "$D"
PY="${TECHPACK_PY:-/home/devinubuntu/.venvs/techpack-grand-line/bin/python3}"
[ -x "$PY" ] || PY=python3
PYTHONPATH="$R/engine:$D" exec "$PY" "$@"
