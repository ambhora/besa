# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Test-only assertions for the Fortran example, loaded through CMAKE_PROJECT_INCLUDE.
function(_besa_test_fortran)
  foreach(TEST_NAME IN ITEMS greetf.greet.t greetf.first.t greetf.second.t greetf.stop.fail.t)
    if(NOT TEST "${TEST_NAME}")
      message(FATAL_ERROR "expected the Fortran test '${TEST_NAME}' to be discovered")
    endif()
  endforeach()
endfunction()
cmake_language(DEFER CALL _besa_test_fortran)
