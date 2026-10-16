#!/bin/bash
# one-time setup on macOS: system cairo (for cairosvg), venv, python deps, tests
set -e
cd "$(dirname "$0")/.."
command -v brew >/dev/null && brew list cairo >/dev/null 2>&1 || brew install cairo
python3 -m venv .venv && source .venv/bin/activate
pip install -q -r requirements.txt
python3 -m pytest -q tests
echo "ready: source .venv/bin/activate && claude"
