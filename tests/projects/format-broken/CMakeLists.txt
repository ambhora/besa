# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# The formatting devtool must reject an unformatted source.
cmake_minimum_required(VERSION 4.3)
project(format-broken VERSION 1.0.0 LANGUAGES CXX)
find_package(besa CONFIG REQUIRED)

include(cmake/options.cmake)
include(CTest)

set(CMAKE_CXX_STANDARD 20)
besa_add_executable(NAME untidy SOURCES untidy.cpp)
