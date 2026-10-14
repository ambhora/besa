# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Release policy and the generated <project>/version.hpp header.
cmake_minimum_required(VERSION 4.3)
project(relinfo VERSION 1.2.3 LANGUAGES NONE)
find_package(besa CONFIG REQUIRED)

include(cmake/options.cmake)
include(CTest)

besa_add_library(NAME librelinfo TYPE STATIC INSTALL YES)
besa_add_directory(LIBRARY librelinfo ROOT cpp TYPE cpp)
besa_test_add_directory(NAME tests PREFIX relinfo TARGET_LIST relinfo::librelinfo)
