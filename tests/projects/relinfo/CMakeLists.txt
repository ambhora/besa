# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Release policy and the generated <project>/version.hpp header.
cmake_minimum_required(VERSION 3.25)
project(relinfo VERSION 1.2.3 LANGUAGES NONE)
include(CTest)
find_package(besa CONFIG REQUIRED)

besa_configure_complete()

set(CMAKE_CXX_STANDARD 20)
besa_add_subdirectory(DIRECTORY cpp TYPE cpp)
besa_test_add_directory(NAME tests PREFIX relinfo TARGET_LIST relinfo::librelinfo)
