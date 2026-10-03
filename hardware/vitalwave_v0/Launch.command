#!/bin/zsh
cd "${0:A:h}"
if [[ ! -x .venv/bin/python ]]; then
  echo 'Run tools/setup_mac.sh once first.'
  read '?Press Enter to close'
  exit 1
fi
.venv/bin/python desktop/main.py "$@"
