# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Coverage groups: running the tests produces a report through the generated report tests.
cmake_minimum_required(VERSION 4.3)
project(coverage VERSION 1.0.0 LANGUAGES NONE)
find_package(besa CONFIG REQUIRED)

include(cmake/options.cmake)
include(CTest)

besa_add_library(NAME libcoverage TYPE STATIC INSTALL YES)
besa_add_directory(LIBRARY libcoverage ROOT cpp TYPE cpp)
besa_test_add_directory(
  NAME tests PREFIX coverage TARGET_LIST coverage::libcoverage COVERAGE_GROUP unit
)
