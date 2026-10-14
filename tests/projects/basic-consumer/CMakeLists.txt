# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Downstream project consuming the installed basic package without BESA.
cmake_minimum_required(VERSION 4.3)
project(basic-consumer LANGUAGES CXX)
include(CTest)
find_package(basic 1.2 CONFIG REQUIRED)

add_executable(consumer main.cpp)
target_link_libraries(consumer PRIVATE basic::libbasic)
add_test(NAME consumer COMMAND consumer)
