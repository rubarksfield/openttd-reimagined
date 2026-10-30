#!/bin/zsh
# Build the unmodified checksum-pinned source, never the mobile-patched tree.
set -euo pipefail
cd "${0:A:h:h}"
[[ -x .tools/python/bin/cmake ]] || ./script/bootstrap_tools.sh
REFERENCE="$(python3 script/prepare_upstream.py --reference)"
[[ -f "$REFERENCE/CMakeLists.txt" ]] || { print -u2 'Missing audited reference source tree'; exit 1; }
mkdir -p build/reference evidence
.tools/python/bin/cmake -S "$REFERENCE" -B build/reference -G Ninja \
  -DCMAKE_MAKE_PROGRAM="$PWD/.tools/python/bin/ninja" \
  -DCMAKE_BUILD_TYPE=RelWithDebInfo -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DOPTION_DEDICATED=ON -DOPTION_USE_ASSERTS=ON \
  -DGRFCODEC_EXECUTABLE=GRFCODEC_EXECUTABLE-NOTFOUND -DNFORENUM_EXECUTABLE=NFORENUM_EXECUTABLE-NOTFOUND
.tools/python/bin/cmake --build build/reference --target openttd openttd_test --parallel 3
