# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Integration of generated semantic directories with CMake code generation.
#
# Generated-directory callbacks are declared with besa_register_subdirectory_type()
# and used through besa_add_directory() (see subdirectory.cmake). This module
# owns the generator-target bookkeeping, the CMake CODEGEN dependencies, and
# generated include roots. It does not define a separate user-facing API.
#
# Generated outputs live under BESA_CODEGEN_DIRECTORY, never under the source
# tree. CMake 4.3 provides the reserved `codegen` build target. Finalization
# integrates generated metadata headers into the project library if it exists.

include_guard(GLOBAL)
include("${CMAKE_CURRENT_LIST_DIR}/workspace.cmake")
cmake_policy(SET CMP0171 NEW)

# --------------------------------------------------------------------------------------------------
# Internal implementation
# --------------------------------------------------------------------------------------------------

# Associate a generated semantic unit with its producing CMake target.
# The CODEGEN custom command makes the generated unit visible to the reserved
# CMake codegen target; its stamp is not itself a generated source file.
function(_besa_codegen_register_target NAME TARGET_NAME)
  cmake_policy(SET CMP0171 NEW)
  if(NOT TARGET "${TARGET_NAME}")
    _besa_fatal("generated subdirectory '${NAME}'" "unknown generator target '${TARGET_NAME}'")
  endif()
  set_property(GLOBAL APPEND PROPERTY BESA_INTERNAL_CODEGEN_TARGETS "${TARGET_NAME}")
  set(_stamp "${BESA_CODEGEN_DIRECTORY}/${NAME}.stamp")
  get_filename_component(_directory "${_stamp}" DIRECTORY)
  file(MAKE_DIRECTORY "${_directory}")
  add_custom_command(
    OUTPUT "${_stamp}"
    COMMAND "${CMAKE_COMMAND}" -E touch "${_stamp}"
    DEPENDS "${TARGET_NAME}"
    CODEGEN
    VERBATIM
  )
endfunction()

# Allocate and register a generated include root for metadata headers.
# Used by version.cmake; the roots are consumed at project finalization.
function(_besa_codegen_include NAME OUTPUT_VARIABLE)
  if(NOT DEFINED BESA_CODEGEN_DIRECTORY OR "${BESA_CODEGEN_DIRECTORY}" STREQUAL "")
    besa_workspace_initialize()
  endif()
  set(_include "${BESA_CODEGEN_DIRECTORY}/${NAME}/include")
  file(MAKE_DIRECTORY "${_include}")
  set_property(GLOBAL APPEND PROPERTY BESA_INTERNAL_GENERATED_INCLUDE_ROOTS "${_include}")
  set("${OUTPUT_VARIABLE}" "${_include}" PARENT_SCOPE)
endfunction()

# Attach registered generated include roots to the conventional project
# library, when it exists, and install generated public headers.
function(_besa_codegen_finalize)
  get_property(_roots GLOBAL PROPERTY BESA_INTERNAL_GENERATED_INCLUDE_ROOTS)
  if(NOT _roots OR NOT TARGET "lib${PROJECT_NAME}")
    return()
  endif()
  include(GNUInstallDirs)
  list(REMOVE_DUPLICATES _roots)
  foreach(_root IN LISTS _roots)
    file(GLOB_RECURSE _headers LIST_DIRECTORIES FALSE CONFIGURE_DEPENDS "${_root}/*")
    if(_headers)
      target_sources("lib${PROJECT_NAME}" PUBLIC FILE_SET HEADERS BASE_DIRS "${_root}" FILES ${_headers})
    endif()
    target_include_directories(
      "lib${PROJECT_NAME}" PUBLIC
      $<BUILD_INTERFACE:${_root}>
      $<INSTALL_INTERFACE:include>
    )
    install(DIRECTORY "${_root}/" DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}" OPTIONAL)
  endforeach()
endfunction()
