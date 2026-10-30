#!/bin/bash
# GPL-2.0: Xcode's expanded target directory keeps device/simulator products apart.
set -euo pipefail
project_root="${1:?Pass the project root}"
cmake_bin="${2:?Pass CMake}"
if [[ "${WRAPPER_NAME:-}" != OpenTTDPad.app ]]; then
  echo 'Expected the OpenTTDPad app target' >&2
  exit 1
fi
bundle_dir="${TARGET_BUILD_DIR:?Xcode target directory is required}/${WRAPPER_NAME}"
"$cmake_bin" -E copy_directory "$project_root/build/ipad-resources" "$bundle_dir/GameData"
"$cmake_bin" -E copy_directory "$project_root/native/apple/AppIcons" "$bundle_dir"
