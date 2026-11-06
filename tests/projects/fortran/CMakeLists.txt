# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Fortran semantic project: one library whose public module uses a private one, tests written in
# Fortran, and an installed package that a downstream Fortran program can use.
cmake_minimum_required(VERSION 4.3)
project(greetf VERSION 1.0.0 LANGUAGES NONE)
find_package(besa CONFIG REQUIRED)

include(cmake/options.cmake)
include(CTest)

besa_add_library(NAME libgreetf TYPE STATIC INSTALL YES)
besa_add_directory(LIBRARY libgreetf ROOT fortran TYPE fortran)

if(BUILD_TESTING)
  besa_test_add_directory(NAME tests PREFIX greetf TARGET_LIST greetf::libgreetf LABELS unit)
endif()
