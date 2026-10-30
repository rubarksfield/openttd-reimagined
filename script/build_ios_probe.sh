#!/bin/zsh
# Compiles real upstream units; intentionally does not claim a linked engine/app.
set -euo pipefail
cd "${0:A:h:h}"
python3 script/prepare_upstream.py
for VARIANT in device simulator; do
  SDK=iphoneos
  [[ "$VARIANT" == simulator ]] && SDK=iphonesimulator
  .tools/python/bin/cmake -S cmake/ios-portability -B "build/ios-$VARIANT-probe" -G Ninja \
    -DCMAKE_MAKE_PROGRAM="$PWD/.tools/python/bin/ninja" \
    -DCMAKE_SYSTEM_NAME=iOS -DCMAKE_OSX_SYSROOT="$SDK" \
    -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_OSX_DEPLOYMENT_TARGET=17.0 \
    -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY \
    -DUPSTREAM_SOURCE="$PWD/vendor/openttd-15.3" \
    -DHOST_GENERATED="$PWD/build/reference/generated"
  .tools/python/bin/cmake --build "build/ios-$VARIANT-probe" --parallel 2
  xcrun otool -l "build/ios-$VARIANT-probe/libopenttd_core_portability.a" > "evidence/ios-$VARIANT-macho.txt"
done
