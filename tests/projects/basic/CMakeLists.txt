# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Minimal semantic project: one C++ library unit and one bin unit.
cmake_minimum_required(VERSION 4.3)
project(basic VERSION 1.2.3 LANGUAGES NONE)
find_package(besa CONFIG REQUIRED)

include(cmake/options.cmake)
include(CTest)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

besa_add_library(NAME libbasic TYPE STATIC INSTALL YES)
besa_add_directory(LIBRARY libbasic ROOT cpp TYPE cpp)
besa_dependency_add(NAME Threads KIND NORMAL)
target_link_libraries(libbasic PRIVATE Threads::Threads)
besa_add_subdirectory(DIRECTORY bin TYPE bin)

if(BUILD_TESTING)
  besa_test_add_directory(NAME tests PREFIX basic TARGET_LIST basic::libbasic LABELS unit)
endif()
