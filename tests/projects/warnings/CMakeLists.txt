# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Warning policies: the source warns, so essential;error must fail the build.
cmake_minimum_required(VERSION 3.25)
project(warnings VERSION 1.0.0 LANGUAGES CXX)
include(CTest)
find_package(besa CONFIG REQUIRED)

besa_configure_complete()

besa_add_executable(NAME warns SOURCES warns.cpp)
