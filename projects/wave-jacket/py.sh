#!/bin/bash
# run a python script of this project with the engine env: ./py.sh script.py args...
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/../../scripts/env.sh" projects/wave-jacket >/dev/null
exec python3 "$@"
