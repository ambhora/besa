# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Coverage groups: running the tests produces a report through the generated report tests.
cmake_minimum_required(VERSION 3.25)
project(coverage VERSION 1.0.0 LANGUAGES NONE)
include(CTest)
find_package(besa CONFIG REQUIRED)

besa_configure_complete()

set(CMAKE_CXX_STANDARD 20)
besa_add_subdirectory(DIRECTORY cpp TYPE cpp)
besa_test_add_directory(
  NAME tests PREFIX coverage TARGET_LIST coverage::libcoverage COVERAGE_GROUP unit
)
