# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Warning policies: the source warns, so essential;error must fail the build.
cmake_minimum_required(VERSION 4.3)
project(warnings VERSION 1.0.0 LANGUAGES CXX)
include(CTest)
find_package(besa CONFIG REQUIRED)

besa_configure_complete()

besa_add_executable(NAME warns SOURCES warns.cpp)
