# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# The surrogate devtool compiles every public header on its own.
cmake_minimum_required(VERSION 4.3)
project(surrogate VERSION 1.0.0 LANGUAGES CXX)
find_package(besa CONFIG REQUIRED)

include(cmake/options.cmake)
include(CTest)

set(CMAKE_CXX_STANDARD 20)
besa_add_library(NAME libfine TYPE STATIC INSTALL NO)
target_include_directories(libfine PUBLIC "${PROJECT_SOURCE_DIR}/fine")
target_sources(libfine PRIVATE fine.cpp)
