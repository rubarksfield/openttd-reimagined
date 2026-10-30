#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
if [[ ! -x .tools/python/bin/python ]]; then
  python3 -m venv .tools/python
fi
.tools/python/bin/python -m pip install 'cmake==3.31.10' 'ninja==1.13.2'
