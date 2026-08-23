# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Every unit-test executable gets the same Prova/Catch2 entry point through this interface target.
# Individual .t.cpp files therefore contain only test cases.
target_sources(
  vorlage.test.unit
  INTERFACE
    "${CMAKE_CURRENT_SOURCE_DIR}/cpp/main.cpp"
)

besa_test_add_directory(
  NAME cpp/vorlage
  PREFIX unit
  LABELS unit production
  COVERAGE_GROUP unit
  TARGET_LIST vorlage.test.unit
  CMDLINE
    --input "${PROJECT_SOURCE_DIR}/test"
    --output "${PROJECT_BINARY_DIR}/test"
  MODES ci-commit
)
