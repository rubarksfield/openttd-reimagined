#!/bin/zsh
# Prepare a distribution archive. Upload/submission is deliberately separate.
set -euo pipefail
cd "${0:A:h:h}"
: "${OPENTTD_DEVELOPMENT_TEAM:?Set your Apple Developer team}"
: "${OPENTTD_BUNDLE_IDENTIFIER:?Set your registered personal bundle identifier}"
./script/build_reference.sh
python3 script/prepare_graphics.py
python3 script/prepare_ipad_sources.py
store_root="$HOME/Library/Developer/Xcode/DerivedData/OpenTTDReimaginedDistribution"
.tools/python/bin/cmake -S cmake/ipad-app -B build/ipad-store-xcode -G Xcode \
 -DCMAKE_SYSTEM_NAME=iOS -DCMAKE_OSX_SYSROOT=iphoneos -DCMAKE_OSX_ARCHITECTURES=arm64 \
 -DCMAKE_OSX_DEPLOYMENT_TARGET=17.0 -DCMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY \
 -DOPENTTD_RUNTIME_EVIDENCE=OFF -DOPENTTD_DEVELOPMENT_TEAM="$OPENTTD_DEVELOPMENT_TEAM" \
 -DOPENTTD_BUNDLE_IDENTIFIER="$OPENTTD_BUNDLE_IDENTIFIER" \
 -DOPENTTD_XCODE_PRODUCTS_DIR="$store_root/Products"
xcodebuild -project build/ipad-store-xcode/OpenTTDPad.xcodeproj -scheme OpenTTDPad \
 -configuration Release -destination 'generic/platform=iOS' \
 -archivePath "$store_root/OpenTTDReimagined.xcarchive" \
 -allowProvisioningUpdates DEVELOPMENT_TEAM="$OPENTTD_DEVELOPMENT_TEAM" -jobs 3 archive
# Custom DerivedData products avoid File Provider signing problems, but CMake
# leaves the generated dSYM there instead of collecting it into the archive.
python3 script/stage_archive_symbols.py "$store_root/OpenTTDReimagined.xcarchive" "$store_root/Products/Release-iphoneos/OpenTTDPad.app.dSYM"
python3 script/verify_store_archive.py "$store_root/OpenTTDReimagined.xcarchive" --bundle-identifier "$OPENTTD_BUNDLE_IDENTIFIER"
