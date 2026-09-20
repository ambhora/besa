# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.25)
project(unit)
include(CTest)

find_package(besa REQUIRED COMPONENTS test)

besa_test_directory(
  DIRECTORY test
  TARGET_LIST ""
  PREFIX "unit"
  LABELS ""
  COVERAGE NO
  COVERAGE_GROUP "unit"
  CMDLINE ""
  )

