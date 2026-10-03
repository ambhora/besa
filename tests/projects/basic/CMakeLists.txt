# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Minimal semantic project: one C++ library unit and one bin unit.
cmake_minimum_required(VERSION 3.25)
project(basic VERSION 1.2.3 LANGUAGES NONE)
include(CTest)
find_package(besa CONFIG REQUIRED)

besa_configure_complete()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

besa_add_subdirectory(DIRECTORY cpp TYPE cpp)
besa_dependency_add(NAME Threads KIND NORMAL)
target_link_libraries(libbasic PRIVATE Threads::Threads)
besa_add_subdirectory(DIRECTORY bin TYPE bin)

if(BUILD_TESTING)
  besa_test_add_directory(NAME tests PREFIX basic TARGET_LIST basic::libbasic LABELS unit)
endif()
