#!/bin/bash
# one-time setup on WSL 2 (Ubuntu): system libs for cairo + PDF tools, a venv, python deps, tests.
# Keep the repo in the Linux filesystem (~/...), not under /mnt/c — file I/O there is many times slower.
set -e
cd "$(dirname "$0")/.."
case "$(pwd)" in /mnt/*) echo "WARNING: repo is under $(pwd) — move it to ~/ for speed (git clone into ~/techpack-engine)";; esac
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv python3-pip libcairo2 libcairo2-dev pkg-config poppler-utils git zip >/dev/null
python3 -m venv .venv && source .venv/bin/activate
pip install -q --upgrade pip && pip install -q -r requirements.txt
python3 -m pytest -q tests
echo "cores available to WSL: $(nproc)  (raise in %UserProfile%\\.wslconfig: [wsl2] processors=N memory=XGB)"
echo "ready: source .venv/bin/activate && claude"
