cmake_minimum_required(VERSION 3.24)
project(OpenTTDCorePortability LANGUAGES CXX)
if(NOT CMAKE_SYSTEM_NAME STREQUAL "iOS")
  message(FATAL_ERROR "This probe must target iOS; it is not a desktop or full-engine build.")
endif()
if(NOT UPSTREAM_SOURCE OR NOT HOST_GENERATED)
  message(FATAL_ERROR "Set UPSTREAM_SOURCE to the pinned patched tree and HOST_GENERATED to native generated files.")
endif()
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED YES)
set(CMAKE_CXX_EXTENSIONS NO)
set(CMAKE_EXPORT_COMPILE_COMMANDS YES)
# Real upstream translation units, not reimplementations. This archive is intentionally
# an unresolved compilation probe, not a runnable or fully linked engine library.
set(ENGINE_UNITS
  core/math_func.cpp core/random_func.cpp core/geometry_func.cpp core/utf8.cpp
  map.cpp economy.cpp command.cpp rail_cmd.cpp train_cmd.cpp order_cmd.cpp
  network/network_command.cpp saveload/saveload.cpp script/script_instance.cpp
  viewport.cpp gfx.cpp spritecache.cpp spriteloader/grf.cpp gfxinit.cpp
  window.cpp widget.cpp rail_gui.cpp vehicle_gui.cpp order_gui.cpp)
list(TRANSFORM ENGINE_UNITS PREPEND "${UPSTREAM_SOURCE}/src/")
add_library(openttd_core_portability STATIC ${ENGINE_UNITS})
target_compile_definitions(openttd_core_portability PRIVATE
  UNIX POINTER_IS_64BIT WITH_ASSERT WITH_ZLIB DEDICATED)
target_include_directories(openttd_core_portability PRIVATE
  "${UPSTREAM_SOURCE}/src" "${UPSTREAM_SOURCE}/src/3rdparty/squirrel/include"
  "${HOST_GENERATED}" "${HOST_GENERATED}/script" "${HOST_GENERATED}/script/api"
  "${HOST_GENERATED}/script/api/ai" "${HOST_GENERATED}/script/api/game"
  "${HOST_GENERATED}/script/api/template" "${UPSTREAM_SOURCE}/src/script/api")
