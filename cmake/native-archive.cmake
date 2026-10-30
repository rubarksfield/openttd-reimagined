# Native content parsing is independent of the OpenTTD simulation and Apple UI.
function(openttd_add_native_archive project_root)
 if(TARGET archive_static)
  return()
 endif()
 set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
 foreach(feature TAR CPIO CAT UNZIP TEST INSTALL COVERAGE ACL XATTR OPENSSL
                 MBEDTLS NETTLE MD LIBB2 LZ4 LZO ZSTD BZip2 LIBXML2 BSDXML
                 EXPAT WIN32_XMLLITE PCREPOSIX PCRE2POSIX LIBGCC)
  set(ENABLE_${feature} OFF CACHE BOOL "" FORCE)
 endforeach()
 set(ENABLE_WERROR OFF CACHE BOOL "" FORCE)
 set(ENABLE_ZLIB ON CACHE BOOL "" FORCE)
 # ZIP/TAR/GZIP are import containers; XZ saves remain supported by the engine's
 # separate native liblzma. Avoid finding an undeclared system codec for import.
 set(ENABLE_LZMA OFF CACHE BOOL "" FORCE)
 set(DONT_FAIL_ON_CRC_ERROR OFF CACHE BOOL "" FORCE)
 if(CMAKE_SYSTEM_NAME STREQUAL "iOS")
  # CheckFunctionExists requires a real SDK link. With STATIC_LIBRARY every
  # undeclared system symbol incorrectly appears available during cross builds.
  set(CMAKE_TRY_COMPILE_TARGET_TYPE EXECUTABLE)
  set(CMAKE_XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED NO)
  list(APPEND CMAKE_TRY_COMPILE_PLATFORM_VARIABLES CMAKE_XCODE_ATTRIBUTE_CODE_SIGNING_ALLOWED)
  if(NOT OPENTTD_ARCHIVE_LINK_CHECKS_V1)
   get_cmake_property(cache_variables CACHE_VARIABLES)
   foreach(variable IN LISTS cache_variables)
    if(variable MATCHES "^HAVE_" OR variable STREQUAL "__stub")
     unset(${variable} CACHE)
    endif()
   endforeach()
   set(OPENTTD_ARCHIVE_LINK_CHECKS_V1 TRUE CACHE INTERNAL "Archive capabilities checked with an SDK link")
  endif()
 endif()
 add_subdirectory("${project_root}/vendor/native-deps/libarchive-3.8.10"
                  "${CMAKE_CURRENT_BINARY_DIR}/native-archive" EXCLUDE_FROM_ALL)
 if(CMAKE_SYSTEM_NAME STREQUAL "iOS")
  # An Xcode project can select either mobile SDK at build time. Absolute
  # configure-time device .tbd paths would incorrectly link into Simulator.
  get_target_property(archive_dependencies archive_static INTERFACE_LINK_LIBRARIES)
  set(sdk_dependencies)
  foreach(dependency IN LISTS archive_dependencies)
   if(dependency MATCHES "^/.+\\.sdk/usr/lib/lib(z|iconv|charset)\\.tbd$")
    list(APPEND sdk_dependencies "${CMAKE_MATCH_1}")
   else()
    list(APPEND sdk_dependencies "${dependency}")
   endif()
  endforeach()
  set_property(TARGET archive_static PROPERTY INTERFACE_LINK_LIBRARIES "${sdk_dependencies}")
 endif()
endfunction()
