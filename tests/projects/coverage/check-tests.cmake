# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# The coverage devtool must register the per-group and aggregate report tests.
execute_process(
  COMMAND "${CMAKE_CTEST_COMMAND}" --test-dir "${BINARY_DIR}" -N
  OUTPUT_VARIABLE CTEST_OUTPUT
  COMMAND_ERROR_IS_FATAL ANY
)
foreach(EXPECTED_TEST instrumentation.coverage.unit.t instrumentation.coverage.t)
  string(REPLACE "." "\\." TEST_NAME_PATTERN "${EXPECTED_TEST}")
  if(NOT CTEST_OUTPUT MATCHES "${TEST_NAME_PATTERN}")
    message(FATAL_ERROR "missing coverage test '${EXPECTED_TEST}':\n${CTEST_OUTPUT}")
  endif()
endforeach()
