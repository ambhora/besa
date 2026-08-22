# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
include_guard(GLOBAL)
include("${CMAKE_CURRENT_LIST_DIR}/internal.cmake")

# Register one generator-owned public include tree.
#
# Every generator receives the conventional build-tree location
#
#   <binary>/generated/<name>/include
#
# and may write public headers below it using the normal installed include namespace. BESA attaches
# all registered roots to the project's main library during finalization, so they participate in
# compilation, compile_commands.json, installation, editor discovery, and API documentation without
# subsystem-specific knowledge of individual generators.
#
# NAME
#   Stable generator name and build-tree namespace. It must be one path component.
#
# TARGET
#   Optional build target which materializes this generator's headers. BESA adds it to the common
#   `besa.generated` target and makes the main library depend on it.
#
# OUTPUT_VARIABLE
#   Optional variable receiving the absolute generated include root.
function(besa_generated_include_add)
  cmake_parse_arguments(ARG "" "NAME;TARGET;OUTPUT_VARIABLE" "" ${ARGN})
  _besa_require_no_unparsed("besa_generated_include_add" "${ARG_UNPARSED_ARGUMENTS}")
  _besa_require_value("besa_generated_include_add" "NAME" "${ARG_NAME}")

  if(NOT ARG_NAME MATCHES "^[A-Za-z0-9][A-Za-z0-9_.-]*$")
    _besa_fatal(
      "besa_generated_include_add"
      "NAME '${ARG_NAME}' must be a single generator-name component using letters, digits, '.', '_', or '-'"
    )
  endif()

  get_property(_names GLOBAL PROPERTY BESA_GENERATED_INCLUDE_NAMES)
  if("${ARG_NAME}" IN_LIST _names)
    _besa_fatal("besa_generated_include_add" "generator '${ARG_NAME}' is already registered")
  endif()

  if(NOT TARGET besa.generated)
    add_custom_target(besa.generated)
  endif()

  set(_include_directory "${PROJECT_BINARY_DIR}/generated/${ARG_NAME}/include")
  file(MAKE_DIRECTORY "${_include_directory}")
  set_property(GLOBAL APPEND PROPERTY BESA_GENERATED_INCLUDE_NAMES "${ARG_NAME}")
  set_property(GLOBAL APPEND PROPERTY BESA_GENERATED_INCLUDE_DIRECTORIES "${_include_directory}")
  if(ARG_TARGET)
    set_property(GLOBAL APPEND PROPERTY BESA_GENERATED_INCLUDE_TARGETS "${ARG_NAME}|${ARG_TARGET}")
  endif()

  if(ARG_OUTPUT_VARIABLE)
    set("${ARG_OUTPUT_VARIABLE}" "${_include_directory}" PARENT_SCOPE)
  endif()
endfunction()

function(_besa_generated_includes_finalize)
  get_property(_directories GLOBAL PROPERTY BESA_GENERATED_INCLUDE_DIRECTORIES)
  if(NOT _directories)
    return()
  endif()

  include(GNUInstallDirs)
  set(_library "lib${PROJECT_NAME}")
  list(REMOVE_DUPLICATES _directories)

  foreach(_include_directory IN LISTS _directories)
    if(TARGET "${_library}")
      target_include_directories(
        "${_library}" PUBLIC
        $<BUILD_INTERFACE:${_include_directory}>
        $<INSTALL_INTERFACE:include>
      )

      # Install the directory itself rather than a configure-time file glob. That also supports
      # generators whose public headers are materialized by a build target after CMake configuration.
      install(
        DIRECTORY "${_include_directory}/"
        DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}"
        OPTIONAL
      )
    endif()
  endforeach()

  get_property(_generator_targets GLOBAL PROPERTY BESA_GENERATED_INCLUDE_TARGETS)
  foreach(_record IN LISTS _generator_targets)
    string(REPLACE "|" ";" _fields "${_record}")
    list(GET _fields 0 _name)
    list(GET _fields 1 _target)
    if(NOT TARGET "${_target}")
      _besa_fatal(
        "besa_generated_include_add"
        "generator '${_name}' registered TARGET '${_target}', but that target does not exist"
      )
    endif()
    add_dependencies(besa.generated "${_target}")
    if(TARGET "${_library}")
      add_dependencies("${_library}" "${_target}")
    endif()
  endforeach()
endfunction()
