#!/bin/zsh
# Keep upstream regression expectations intact, but isolate test resource search.
set -euo pipefail
ROOT="${0:A:h:h}"
exec "$ROOT/build/reference/openttd" -X -I OpenGFX -S NoSound -M NoMusic "$@"
