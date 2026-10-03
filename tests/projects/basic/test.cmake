# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Test-only assertions for the basic example. The project CMakeLists.txt intentionally contains only
# normal BESA usage; the test harness loads this file through CMAKE_PROJECT_INCLUDE.
function(_besa_test_basic)
  if(FREEZE_VIOLATION)
    besa_add_feature(late)
  endif()

  foreach(_target IN ITEMS libbasic basic-cli)
    if(NOT TARGET "${_target}")
      message(FATAL_ERROR "expected target '${_target}' to exist")
    endif()
  endforeach()
  get_target_property(_output_name libbasic OUTPUT_NAME)
  if(NOT _output_name STREQUAL "basic")
    message(FATAL_ERROR "libbasic OUTPUT_NAME is '${_output_name}', expected 'basic'")
  endif()
endfunction()
cmake_language(DEFER CALL _besa_test_basic)
