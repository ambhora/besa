# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Test-only assertions for the basic example. The project CMakeLists.txt intentionally contains only
# normal BESA usage; the test harness loads this file through CMAKE_PROJECT_INCLUDE.
function(_besa_test_basic)
  foreach(TARGET_TO_VERIFY IN ITEMS libbasic basic-cli)
    if(NOT TARGET "${TARGET_TO_VERIFY}")
      message(FATAL_ERROR "expected target '${TARGET_TO_VERIFY}' to exist")
    endif()
  endforeach()
  get_target_property(ACTUAL_OUTPUT_NAME libbasic OUTPUT_NAME)
  if(NOT ACTUAL_OUTPUT_NAME STREQUAL "basic")
    message(FATAL_ERROR "libbasic OUTPUT_NAME is '${ACTUAL_OUTPUT_NAME}', expected 'basic'")
  endif()
endfunction()
cmake_language(DEFER CALL _besa_test_basic)
