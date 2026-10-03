# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# The formatting devtool must reject an unformatted source.
cmake_minimum_required(VERSION 3.25)
project(format-broken VERSION 1.0.0 LANGUAGES CXX)
include(CTest)
find_package(besa CONFIG REQUIRED)

besa_configure_complete()

set(CMAKE_CXX_STANDARD 20)
besa_add_executable(NAME untidy SOURCES untidy.cpp)
