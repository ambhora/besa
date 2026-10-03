# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Test-only assertions for the test-mode example.
function(_besa_test_testmodes)
  if(NOT TARGET commit.quick.t)
    message(FATAL_ERROR "commit tests must be present in every mode")
  endif()
  if(EXPECT_MERGE_TESTS AND NOT TARGET merge.slow.t)
    message(FATAL_ERROR "merge tests are missing although ci-merge is enabled")
  elseif(NOT EXPECT_MERGE_TESTS AND TARGET merge.slow.t)
    message(FATAL_ERROR "merge tests are present although ci-merge is disabled")
  endif()
  if(EXPECT_MERGE_TESTS)
    set(_expected TRUE)
  else()
    set(_expected FALSE)
  endif()
  if(NOT PROJECT_TEST_MODE_CI_MERGE STREQUAL _expected)
    message(FATAL_ERROR "PROJECT_TEST_MODE_CI_MERGE is '${PROJECT_TEST_MODE_CI_MERGE}'")
  endif()
endfunction()
cmake_language(DEFER CALL _besa_test_testmodes)
