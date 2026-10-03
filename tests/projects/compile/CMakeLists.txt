# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Compile-only checks: .t.cpp must compile, .fail.t.cpp must fail to compile.
cmake_minimum_required(VERSION 3.25)
project(compile VERSION 1.0.0 LANGUAGES CXX)
include(CTest)
find_package(besa CONFIG REQUIRED)

besa_configure_complete()

set(CMAKE_CXX_STANDARD 20)
besa_compile_test_add_directory(NAME checks PREFIX compile LABELS compile)
