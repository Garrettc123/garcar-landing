#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "[1/4] Python version"
python --version

echo "[2/4] Compile platform modules"
python -m py_compile server.py digital_delivery.py

echo "[3/4] Unit tests"
python -m unittest discover -s tests -v

echo "[4/4] HTTP smoke tests and catalog integrity"
python smoke_test.py
python ../divisions/validate_catalog.py ../divisions/catalog.json

echo
echo "ALL LOCAL CHECKS PASSED"
