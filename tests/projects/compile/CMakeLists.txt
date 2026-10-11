# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Compile-only checks: .t.cpp must compile, .fail.t.cpp must fail to compile.
cmake_minimum_required(VERSION 4.3)
project(compile VERSION 1.0.0 LANGUAGES CXX)
include(CTest)
find_package(besa CONFIG REQUIRED)

besa_configure_complete()

set(CMAKE_CXX_STANDARD 20)
besa_compile_test_add_directory(NAME checks PREFIX compile LABELS compile)
