# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
include_guard(GLOBAL)
include("${CMAKE_CURRENT_LIST_DIR}/internal.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/selector.cmake")

function(besa_add_directory)
  _besa_require_config_complete("besa_add_directory")
  cmake_parse_arguments(ARG "" "NAME" "WHEN" ${ARGN})
  _besa_require_no_unparsed("besa_add_directory" "${ARG_UNPARSED_ARGUMENTS}")
  _besa_require_value("besa_add_directory" "NAME" "${ARG_NAME}")
  _besa_selector_evaluate("directory:${ARG_NAME}" "${ARG_WHEN}" _selected)
  if(_selected)
    add_subdirectory("${ARG_NAME}")
  endif()
endfunction()

function(_besa_language_loaded LANGUAGE OUTPUT_VARIABLE)
  get_property(_languages GLOBAL PROPERTY BESA_ENABLED_LANGUAGES)
  if("${LANGUAGE}" IN_LIST _languages)
    set(_loaded TRUE)
  else()
    set(_loaded FALSE)
  endif()
  set("${OUTPUT_VARIABLE}" "${_loaded}" PARENT_SCOPE)
endfunction()

# Add one language-specific source root.  The directory convention is deliberately small:
#
#   <name>/include/        public headers
#   <name>/lib/<library>/  library implementation sources grouped by logical library
#   <name>/bin/            one executable source per file (file stem becomes target name)
#   <name>/mod/            reserved for Fortran module-oriented source organization
#
# Multiple language roots may contribute to the same `lib<project>` target. The template keeps that
# target's sources under `lib/<project>/`. BESA currently collects all files below `lib/` into
# `lib<project>`; the subdirectory boundary is organizational until explicit multi-library
# source-directory support is introduced.
function(besa_add_source_directory)
  _besa_require_config_complete("besa_add_source_directory")
  cmake_parse_arguments(ARG "" "NAME;LANGUAGE" "WHEN" ${ARGN})
  _besa_require_no_unparsed("besa_add_source_directory" "${ARG_UNPARSED_ARGUMENTS}")
  _besa_require_value("besa_add_source_directory" "NAME" "${ARG_NAME}")
  _besa_require_value("besa_add_source_directory" "LANGUAGE" "${ARG_LANGUAGE}")

  _besa_selector_evaluate("source-directory:${ARG_NAME}" "${ARG_WHEN}" _selected)
  if(NOT _selected)
    return()
  endif()

  _besa_language_loaded("${ARG_LANGUAGE}" _loaded)
  if(NOT _loaded)
    _besa_fatal(
      "besa_add_source_directory"
      "LANGUAGE '${ARG_LANGUAGE}' is not enabled. Enable the corresponding toolchain-* feature."
    )
  endif()

  set(_root "${CMAKE_CURRENT_SOURCE_DIR}/${ARG_NAME}")
  if(NOT IS_DIRECTORY "${_root}")
    _besa_fatal("besa_add_source_directory" "directory does not exist: ${_root}")
  endif()

  set(_library "lib${PROJECT_NAME}")
  file(GLOB_RECURSE _library_sources LIST_DIRECTORIES FALSE CONFIGURE_DEPENDS "${_root}/lib/*")
  file(GLOB_RECURSE _headers LIST_DIRECTORIES FALSE CONFIGURE_DEPENDS "${_root}/include/*")

  # Template source roots use hidden marker files to keep intentionally empty directories in source
  # control. They are project metadata, not source/header inputs.
  list(FILTER _library_sources EXCLUDE REGEX "/\\.[^/]+$")
  list(FILTER _headers EXCLUDE REGEX "/\\.[^/]+$")

  if(_library_sources OR _headers)
    if(NOT TARGET "${_library}")
      besa_add_library(NAME "${_library}")
    endif()
    if(_library_sources)
      target_sources("${_library}" PRIVATE ${_library_sources})
    endif()
    if(_headers)
      target_sources(
        "${_library}" PUBLIC
        FILE_SET HEADERS
        BASE_DIRS "${_root}/include"
        FILES ${_headers}
      )
      target_include_directories(
        "${_library}" PUBLIC
        $<BUILD_INTERFACE:${_root}/include>
        $<INSTALL_INTERFACE:include>
      )
    endif()
  endif()

  file(GLOB _binaries LIST_DIRECTORIES FALSE CONFIGURE_DEPENDS "${_root}/bin/*")
  list(FILTER _binaries EXCLUDE REGEX "/\\.[^/]+$")
  foreach(_source IN LISTS _binaries)
    get_filename_component(_target "${_source}" NAME_WE)
    if(TARGET "${_target}")
      target_sources("${_target}" PRIVATE "${_source}")
    else()
      set(_links)
      if(TARGET "${_library}")
        list(APPEND _links "${PROJECT_NAME}::${_library}")
      endif()
      besa_add_executable(NAME "${_target}" SOURCES "${_source}" LINK_LIBRARIES ${_links})
    endif()
  endforeach()
endfunction()
