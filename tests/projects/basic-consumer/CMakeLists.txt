# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Downstream project consuming the installed basic package without BESA.
cmake_minimum_required(VERSION 3.25)
project(basic-consumer LANGUAGES CXX)
include(CTest)
find_package(basic 1.2 CONFIG REQUIRED)

add_executable(consumer main.cpp)
target_compile_features(consumer PRIVATE cxx_std_20)
target_link_libraries(consumer PRIVATE basic::libbasic)
add_test(NAME consumer COMMAND consumer)
