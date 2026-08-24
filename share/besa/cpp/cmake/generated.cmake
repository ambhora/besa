# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
include_guard(GLOBAL)
include("${CMAKE_CURRENT_LIST_DIR}/internal.cmake")
include("${CMAKE_CURRENT_LIST_DIR}/api.cmake")

# Register one generator-owned prefix. Generators always write below
#
#   <workspace>/codegen/<name>/
#     bin/
#     include/
#     lib/
#     mod/       # optional
#
# The first three directories are created eagerly. BESA consumes their contents with the same
# conventions as handwritten source prefixes. mod/ is reserved for language-module artifacts and is
# left optional because not every generator or language needs it.
function(besa_generated_prefix_add)
  cmake_parse_arguments(ARG "" "NAME;TARGET;OUTPUT_VARIABLE;API" "" ${ARGN})
  _besa_require_no_unparsed("besa_generated_prefix_add" "${ARG_UNPARSED_ARGUMENTS}")
  _besa_require_value("besa_generated_prefix_add" "NAME" "${ARG_NAME}")

  if(NOT ARG_NAME MATCHES "^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    _besa_fatal(
      "besa_generated_prefix_add"
      "NAME '${ARG_NAME}' must be a single generator-name component using letters, digits, '.', '_', or '-'"
    )
  endif()

  get_property(_names GLOBAL PROPERTY BESA_GENERATED_PREFIX_NAMES)
  if("${ARG_NAME}" IN_LIST _names)
    _besa_fatal("besa_generated_prefix_add" "generator '${ARG_NAME}' is already registered")
  endif()

  if(NOT DEFINED BESA_CODEGEN_DIRECTORY OR "${BESA_CODEGEN_DIRECTORY}" STREQUAL "")
    if(COMMAND besa_workspace_initialize)
      besa_workspace_initialize()
    else()
      set(BESA_CODEGEN_DIRECTORY "${PROJECT_BINARY_DIR}/codegen")
    endif()
  endif()

  if(NOT TARGET besa.generated)
    add_custom_target(besa.generated)
  endif()

  _besa_api_classification_parse("besa_generated_prefix_add" "${ARG_API}" "PUBLIC" _api)

  set(_prefix "${BESA_CODEGEN_DIRECTORY}/${ARG_NAME}")
  foreach(_directory IN ITEMS bin include lib)
    file(MAKE_DIRECTORY "${_prefix}/${_directory}")
  endforeach()

  # The API manifest points at the exact public include root so documentation does not need to know
  # anything about the wider generator-prefix convention.
  file(RELATIVE_PATH _manifest_include "${PROJECT_BINARY_DIR}" "${_prefix}/include")
  _besa_api_register(
    KIND generated-include NAME "${ARG_NAME}" PATH "${_manifest_include}" BASE binary
    API "${_api}" SELECTED
  )

  set_property(GLOBAL APPEND PROPERTY BESA_GENERATED_PREFIX_NAMES "${ARG_NAME}")
  set_property(GLOBAL APPEND PROPERTY BESA_GENERATED_PREFIX_DIRECTORIES "${_prefix}")
  if(ARG_TARGET)
    set_property(GLOBAL APPEND PROPERTY BESA_GENERATED_PREFIX_TARGETS "${ARG_NAME}|${ARG_TARGET}")
  endif()

  if(ARG_OUTPUT_VARIABLE)
    set("${ARG_OUTPUT_VARIABLE}" "${_prefix}" PARENT_SCOPE)
  endif()
endfunction()

# Compatibility/convenience wrapper for generators which only need a public include tree.
function(besa_generated_include_add)
  cmake_parse_arguments(ARG "" "NAME;TARGET;OUTPUT_VARIABLE;API" "" ${ARGN})
  _besa_require_no_unparsed("besa_generated_include_add" "${ARG_UNPARSED_ARGUMENTS}")
  _besa_require_value("besa_generated_include_add" "NAME" "${ARG_NAME}")
  besa_generated_prefix_add(
    NAME "${ARG_NAME}"
    TARGET "${ARG_TARGET}"
    API "${ARG_API}"
    OUTPUT_VARIABLE _prefix
  )
  if(ARG_OUTPUT_VARIABLE)
    set("${ARG_OUTPUT_VARIABLE}" "${_prefix}/include" PARENT_SCOPE)
  endif()
endfunction()

function(_besa_generated_prefixes_finalize)
  get_property(_prefixes GLOBAL PROPERTY BESA_GENERATED_PREFIX_DIRECTORIES)
  if(NOT _prefixes)
    return()
  endif()

  include(GNUInstallDirs)
  set(_library "lib${PROJECT_NAME}")
  list(REMOVE_DUPLICATES _prefixes)

  foreach(_prefix IN LISTS _prefixes)
    file(GLOB_RECURSE _headers LIST_DIRECTORIES FALSE CONFIGURE_DEPENDS "${_prefix}/include/*")
    file(GLOB_RECURSE _library_sources LIST_DIRECTORIES FALSE CONFIGURE_DEPENDS "${_prefix}/lib/*")
    file(GLOB_RECURSE _module_sources LIST_DIRECTORIES FALSE CONFIGURE_DEPENDS "${_prefix}/mod/*")
    file(GLOB _binaries LIST_DIRECTORIES FALSE CONFIGURE_DEPENDS "${_prefix}/bin/*")
    list(FILTER _headers EXCLUDE REGEX "/\\.[^/]+$")
    list(FILTER _library_sources EXCLUDE REGEX "/\\.[^/]+$")
    list(FILTER _module_sources EXCLUDE REGEX "/\\.[^/]+$")
    list(FILTER _binaries EXCLUDE REGEX "/\\.[^/]+$")

    # Header-only generated prefixes augment an existing project library, but must not create one
    # on their own.  This preserves valid configurations such as ~build-source;~toolchain-cpp where
    # metadata is still generated but there is deliberately no compilable project target.
    if((_library_sources OR _module_sources) AND NOT TARGET "${_library}")
      besa_add_library(NAME "${_library}")
    endif()
    if(TARGET "${_library}")
      if(_library_sources OR _module_sources)
        target_sources("${_library}" PRIVATE ${_library_sources} ${_module_sources})
      endif()
      if(_headers)
        target_sources(
          "${_library}" PUBLIC
          FILE_SET HEADERS
          BASE_DIRS "${_prefix}/include"
          FILES ${_headers}
        )
      endif()
      # Include roots are part of the prefix contract even when a build-time generator has not
      # populated them yet at configure time.
      target_include_directories(
        "${_library}" PUBLIC
        $<BUILD_INTERFACE:${_prefix}/include>
        $<INSTALL_INTERFACE:include>
      )
      install(DIRECTORY "${_prefix}/include/" DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}" OPTIONAL)
    endif()

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

    if(IS_DIRECTORY "${_prefix}/mod")
      set_property(GLOBAL APPEND PROPERTY BESA_GENERATED_MODULE_DIRECTORIES "${_prefix}/mod")
    endif()
  endforeach()

  get_property(_generator_targets GLOBAL PROPERTY BESA_GENERATED_PREFIX_TARGETS)
  foreach(_record IN LISTS _generator_targets)
    string(REPLACE "|" ";" _fields "${_record}")
    list(GET _fields 0 _name)
    list(GET _fields 1 _target)
    if(NOT TARGET "${_target}")
      _besa_fatal(
        "besa_generated_prefix_add"
        "generator '${_name}' registered TARGET '${_target}', but that target does not exist"
      )
    endif()
    add_dependencies(besa.generated "${_target}")
    if(TARGET "${_library}")
      add_dependencies("${_library}" "${_target}")
    endif()
  endforeach()
endfunction()
