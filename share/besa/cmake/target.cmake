# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
include_guard(GLOBAL)
include("${CMAKE_CURRENT_LIST_DIR}/internal.cmake")

function(_besa_register_install_target TARGET_NAME)
  get_property(_targets GLOBAL PROPERTY BESA_INSTALL_TARGETS)
  if(NOT "${TARGET_NAME}" IN_LIST _targets)
    set_property(GLOBAL APPEND PROPERTY BESA_INSTALL_TARGETS "${TARGET_NAME}")
  endif()
endfunction()

function(_besa_target_common TARGET_NAME)
  get_target_property(_target_type "${TARGET_NAME}" TYPE)
  if(_target_type STREQUAL "INTERFACE_LIBRARY")
    # An interface target has no compilation step to instrument.
    return()
  endif()
  _besa_devtools_activate()
  # ``projectdocs`` is a BESA/Doxygen alias used in C++ documentation comments. Clang otherwise
  # diagnoses it as an unknown documentation command when -Wdocumentation is enabled (for example
  # by the ``everything`` warning policy). Register only the custom command instead of suppressing
  # unknown-command diagnostics globally, so misspelled standard Doxygen commands still warn.
  target_compile_options(
    "${TARGET_NAME}" PRIVATE
    $<$<COMPILE_LANG_AND_ID:CXX,Clang,AppleClang>:-fcomment-block-commands=projectdocs>
  )

  _besa_target_apply_warning_policy("${TARGET_NAME}")
  _besa_target_apply_devtools("${TARGET_NAME}")
endfunction()

# Add a CMake library target, using BESA's output name and installation conventions.
# Source and public-header discovery is handled separately by besa_add_directory().
# NAME libfoo produces libfoo.a/.so (rather than liblibfoo.a/.so).
function(besa_add_library)
  _besa_require_config_complete("besa_add_library")
  # TYPE is optional. Without it, CMake chooses STATIC or SHARED using
  # BUILD_SHARED_LIBS, just as add_library(NAME) does.
  cmake_parse_arguments(ARG "" "NAME;TYPE;INSTALL" "" ${ARGN})
  _besa_require_no_unparsed("besa_add_library" "${ARG_UNPARSED_ARGUMENTS}")
  _besa_require_value("besa_add_library" "NAME" "${ARG_NAME}")
  if("TYPE" IN_LIST ARG_KEYWORDS_MISSING_VALUES)
    _besa_fatal("besa_add_library" "TYPE requires STATIC, SHARED, MODULE, OBJECT, or INTERFACE")
  endif()
  if(DEFINED ARG_TYPE AND
      NOT ARG_TYPE MATCHES "^(STATIC|SHARED|MODULE|OBJECT|INTERFACE)$")
    _besa_fatal("besa_add_library" "unsupported TYPE '${ARG_TYPE}'; expected STATIC, SHARED, MODULE, OBJECT, or INTERFACE")
  endif()

  if(NOT DEFINED ARG_INSTALL OR ARG_INSTALL STREQUAL "")
    set(ARG_INSTALL YES)
  endif()
  if(NOT ARG_INSTALL STREQUAL "YES" AND NOT ARG_INSTALL STREQUAL "NO")
    _besa_fatal("besa_add_library" "INSTALL must be YES or NO")
  endif()

  if(ARG_TYPE)
    add_library("${ARG_NAME}" "${ARG_TYPE}")
  else()
    add_library("${ARG_NAME}")
  endif()

  if(ARG_NAME MATCHES "^lib(.+)$")
    set_target_properties("${ARG_NAME}" PROPERTIES OUTPUT_NAME "${CMAKE_MATCH_1}")
  endif()
  if(NOT TARGET "${PROJECT_NAME}::${ARG_NAME}")
    add_library("${PROJECT_NAME}::${ARG_NAME}" ALIAS "${ARG_NAME}")
  endif()

  # The project may start with LANGUAGES NONE; besa_add_directory() enables the
  # required language later. Apply compiler-sensitive policies after configuration.
  cmake_language(EVAL CODE
    "cmake_language(DEFER DIRECTORY [[${PROJECT_SOURCE_DIR}]] CALL _besa_target_common [[${ARG_NAME}]])"
  )
  if(ARG_INSTALL STREQUAL "YES")
    _besa_register_install_target("${ARG_NAME}")
  endif()
  if(BUILD_TESTING AND BUILD_DEVTOOLS_SURROGATE AND NOT ARG_TYPE STREQUAL "INTERFACE")
    besa_surrogate_check(TARGET "${ARG_NAME}" LABELS instrumentation surrogate)
  endif()
endfunction()

function(besa_add_executable)
  _besa_require_config_complete("besa_add_executable")
  cmake_parse_arguments(ARG "" "NAME;INSTALL" "SOURCES;LINK_LIBRARIES" ${ARGN})
  _besa_require_no_unparsed("besa_add_executable" "${ARG_UNPARSED_ARGUMENTS}")
  _besa_require_value("besa_add_executable" "NAME" "${ARG_NAME}")
  if(NOT DEFINED ARG_INSTALL OR ARG_INSTALL STREQUAL "")
    set(ARG_INSTALL TRUE)
  endif()

  add_executable("${ARG_NAME}" ${ARG_SOURCES})
  if(ARG_LINK_LIBRARIES)
    target_link_libraries("${ARG_NAME}" PRIVATE ${ARG_LINK_LIBRARIES})
  endif()
  _besa_target_common("${ARG_NAME}")
  if(ARG_INSTALL)
    _besa_register_install_target("${ARG_NAME}")
  endif()
endfunction()
