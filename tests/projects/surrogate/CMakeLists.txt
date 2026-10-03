# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# The surrogate devtool compiles every public header on its own.
cmake_minimum_required(VERSION 3.25)
project(surrogate VERSION 1.0.0 LANGUAGES CXX)
include(CTest)
find_package(besa CONFIG REQUIRED)

besa_configure_complete()

set(CMAKE_CXX_STANDARD 20)
besa_add_library(NAME libfine PUBLIC_INCLUDE_DIRECTORIES "${PROJECT_SOURCE_DIR}/fine")
target_sources(libfine PRIVATE fine.cpp)
