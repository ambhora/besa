# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Test-only assertions for the basic example. The project CMakeLists.txt intentionally contains only
# normal BESA usage; the test harness loads this file through CMAKE_PROJECT_INCLUDE.
function(_besa_test_basic)
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
