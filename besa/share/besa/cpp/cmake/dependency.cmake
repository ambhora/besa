# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
include_guard(GLOBAL)
include("${CMAKE_CURRENT_LIST_DIR}/internal.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/selector.cmake")

# Declare and resolve a project dependency.
#
# KIND describes why the dependency exists, independently from CMake link visibility:
#   NORMAL  - required by the product and recorded in the generated <project>Config.cmake;
#   BUILD   - required while constructing the project but not by consumers;
#   DEV     - required only by tests/documentation/developer tooling and not by consumers.
#
# PROVIDER describes how BESA resolves the package today.  CMAKE uses find_package(), which can
# consume CMake package configs, Find modules, and CPS as supported by the active CMake version.
# PKGCONFIG uses pkg_check_modules(... IMPORTED_TARGET ...).
function(besa_dependency_add)
  _besa_require_config_complete("besa_dependency_add")
  cmake_parse_arguments(
    ARG
    ""
    "NAME;KIND;PROVIDER;VISIBILITY;VERSION"
    "COMPONENTS;WHEN"
    ${ARGN}
  )
  _besa_require_no_unparsed("besa_dependency_add" "${ARG_UNPARSED_ARGUMENTS}")
  _besa_require_value("besa_dependency_add" "NAME" "${ARG_NAME}")

  if(NOT ARG_KIND)
    set(ARG_KIND NORMAL)
  endif()
  if(NOT ARG_PROVIDER)
    set(ARG_PROVIDER CMAKE)
  endif()
  if(NOT ARG_VISIBILITY)
    set(ARG_VISIBILITY PRIVATE)
  endif()

  if(NOT ARG_KIND MATCHES "^(NORMAL|BUILD|DEV)$")
    _besa_fatal("besa_dependency_add" "KIND must be NORMAL, BUILD, or DEV")
  endif()
  if(NOT ARG_PROVIDER MATCHES "^(CMAKE|PKGCONFIG)$")
    _besa_fatal("besa_dependency_add" "PROVIDER must be CMAKE or PKGCONFIG")
  endif()
  if(NOT ARG_VISIBILITY MATCHES "^(PUBLIC|PRIVATE|INTERFACE)$")
    _besa_fatal("besa_dependency_add" "VISIBILITY must be PUBLIC, PRIVATE, or INTERFACE")
  endif()

  _besa_selector_evaluate("dependency:${ARG_NAME}" "${ARG_WHEN}" _selected)
  if(NOT _selected)
    return()
  endif()

  if(ARG_PROVIDER STREQUAL "CMAKE")
    set(_find_args "${ARG_NAME}")
    if(ARG_VERSION)
      list(APPEND _find_args "${ARG_VERSION}")
    endif()
    list(APPEND _find_args REQUIRED)
    if(ARG_COMPONENTS)
      list(APPEND _find_args COMPONENTS ${ARG_COMPONENTS})
    endif()
    find_package(${_find_args})
  else()
    find_package(PkgConfig REQUIRED)
    _besa_normalize_name("${ARG_NAME}" _pkg_key)
    pkg_check_modules("BESA_PKG_${_pkg_key}" REQUIRED IMPORTED_TARGET "${ARG_NAME}")
  endif()

  if(ARG_KIND STREQUAL "NORMAL")
    # Store a compact record for package finalization.  Normal dependencies are intentionally
    # exported regardless of link visibility; this is conservative and also covers static-library
    # consumers where a nominally private dependency can still be needed at final link time.
    string(REPLACE ";" "," _components "${ARG_COMPONENTS}")
    set(_record "${ARG_NAME}|${ARG_PROVIDER}|${ARG_VERSION}|${_components}")
    get_property(_records GLOBAL PROPERTY BESA_NORMAL_DEPENDENCIES)
    if(NOT "${_record}" IN_LIST _records)
      set_property(GLOBAL APPEND PROPERTY BESA_NORMAL_DEPENDENCIES "${_record}")
    endif()
  endif()
endfunction()
