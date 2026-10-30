#!/bin/zsh
# Full engine + original interface. No simulation or visual stand-ins.
set -euo pipefail
cd "${0:A:h:h}"
TARGET="${1:-simulator}"
case "$TARGET" in
 simulator) SDK=iphonesimulator ;;
 device|xcode) SDK=iphoneos ;;
 *) print -u2 'Usage: build_ipad_app.sh [simulator|device|xcode]'; exit 2 ;;
esac
[[ -x .tools/python/bin/cmake ]] || ./script/bootstrap_tools.sh
if [[ ! -f build/reference/compile_commands.json || ! -f build/reference/generated/table/strings.h ]]; then
 ./script/build_reference.sh
fi
python3 script/prepare_upstream.py
python3 script/prepare_upstream.py --reference
python3 script/prepare_graphics.py
python3 script/prepare_ipad_sources.py
CONFIGURE=( -S cmake/ipad-app -B "build/ipad-$TARGET"
 -DCMAKE_SYSTEM_NAME=iOS -DCMAKE_OSX_SYSROOT="$SDK"
 -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_OSX_DEPLOYMENT_TARGET=17.0
 -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY )
if [[ "$TARGET" = xcode ]]; then
 .tools/python/bin/cmake "${CONFIGURE[@]}" -G Xcode \
  -DOPENTTD_DEVELOPMENT_TEAM="${OPENTTD_DEVELOPMENT_TEAM:-}"
 print 'Generated build/ipad-xcode/OpenTTDPad.xcodeproj. Select your team before installing on a device.'
else
 .tools/python/bin/cmake "${CONFIGURE[@]}" -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo \
  -DCMAKE_MAKE_PROGRAM="$PWD/.tools/python/bin/ninja"
 .tools/python/bin/cmake --build "build/ipad-$TARGET" --target OpenTTDPad --parallel 3
fi
