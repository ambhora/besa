# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# The coverage devtool must register the per-group and aggregate report tests.
execute_process(
  COMMAND "${CMAKE_CTEST_COMMAND}" --test-dir "${BINARY_DIR}" -N
  OUTPUT_VARIABLE _output
  COMMAND_ERROR_IS_FATAL ANY
)
foreach(_test instrumentation.coverage.unit.t instrumentation.coverage.t)
  string(REPLACE "." "\\." _pattern "${_test}")
  if(NOT _output MATCHES "${_pattern}")
    message(FATAL_ERROR "missing coverage test '${_test}':\n${_output}")
  endif()
endforeach()
