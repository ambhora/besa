# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Exercise BESA's project-defined test-mode configuration independently of the generated template.
# The default workflow explicitly disables the default `ci-commit` mode and enables `ci-manual`.
# The fail workflow selects an undeclared mode and must therefore fail during configuration.

cmake_minimum_required(VERSION 3.26.1)
project(besa.test.testmode LANGUAGES NONE)

include(CTest)
find_package(besa CONFIG REQUIRED)

besa_test_modes_add(
  MODES
    ci-commit
    ci-manual
)

besa_test_modes_default(
  MODES
    ci-commit
)

besa_configure_complete()

if(PROJECT_TEST_MODE_CI_COMMIT)
  message(FATAL_ERROR "ci-commit should have been disabled by TEST_MODES")
endif()

if(NOT PROJECT_TEST_MODE_CI_MANUAL)
  message(FATAL_ERROR "ci-manual should have been enabled by TEST_MODES")
endif()

besa_test_modes_check(
  OUTPUT_VARIABLE _selected
  MODES
    ci-manual
)

if(NOT _selected)
  message(FATAL_ERROR "ci-manual should select this test")
endif()

add_test(
  NAME besa.test.testmode
  COMMAND "${CMAKE_COMMAND}" -E true
)
