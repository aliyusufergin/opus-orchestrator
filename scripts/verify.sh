#!/bin/sh
# Runs everything CI runs: the wrapper tests against the fake Codex, then the package checks.
set -eu
cd "$(dirname "$0")/.."
python3 -m unittest discover --start-directory tests --top-level-directory tests
python3 scripts/check_package.py
