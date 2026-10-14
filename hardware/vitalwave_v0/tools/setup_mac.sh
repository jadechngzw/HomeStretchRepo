#!/bin/zsh
set -eu
cd "${0:A:h:h}"
VW_PYTHON="${VW_PYTHON:-python3.11}"
if ! "$VW_PYTHON" -c 'import tkinter' >/dev/null 2>&1; then
  echo "A Python installation with Tkinter is required. Set VW_PYTHON to its executable."
  echo "On this Mac use: VW_PYTHON=/opt/homebrew/bin/python3.11 tools/setup_mac.sh"
  exit 1
fi
"$VW_PYTHON" -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
echo 'Setup complete. Launch with ./Launch.command (or ./Launch.command --demo).'
