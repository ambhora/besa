# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.25)
project(compile)
include(CTest)

find_package(besa REQUIRED COMPONENTS tidy)
add_executable(main.t main.t.cpp)

besa_add_clang_tidy(clang-tidy)
