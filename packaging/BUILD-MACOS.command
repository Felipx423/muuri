#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "Execute em um Mac Apple Silicon, com o Terminal fora do Rosetta."
  exit 1
fi
if command -v python3.12 >/dev/null 2>&1; then
  MUURI_PYTHON="$(command -v python3.12)"
else
  echo "Instale Python 3.12 para macOS em https://www.python.org/downloads/macos/ e execute novamente."
  exit 1
fi
"$MUURI_PYTHON" -m venv .venv
.venv/bin/python -m pip install -r packaging/requirements-macos.txt
.venv/bin/python packaging/run_tests.py
.venv/bin/python packaging/build_macos.py --dmg
echo "Pacote criado em dist/macos. Confira também packaging/MACOS.md."
