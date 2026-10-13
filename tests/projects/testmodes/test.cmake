# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Test-only assertions for the test-mode example.
function(_besa_test_testmodes)
  if(NOT TARGET commit.quick.t)
    message(FATAL_ERROR "commit tests must be present in every mode")
  endif()
  besa_test_modes_check(OUTPUT_VARIABLE _expected MODES ci-merge)
  if(_expected AND NOT TARGET merge.slow.t)
    message(FATAL_ERROR "merge tests are missing although ci-merge is enabled")
  elseif(NOT _expected AND TARGET merge.slow.t)
    message(FATAL_ERROR "merge tests are present although ci-merge is disabled")
  endif()
  if(NOT PROJECT_TEST_MODE_CI_MERGE STREQUAL _expected)
    message(FATAL_ERROR "PROJECT_TEST_MODE_CI_MERGE is '${PROJECT_TEST_MODE_CI_MERGE}'")
  endif()
endfunction()
cmake_language(DEFER CALL _besa_test_testmodes)
