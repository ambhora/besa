# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Downstream Fortran program using the installed greetf package without BESA.
cmake_minimum_required(VERSION 4.3)
project(greetf-consumer LANGUAGES Fortran)
include(CTest)
find_package(greetf 1.0 CONFIG REQUIRED)

add_executable(consumer main.f90)
target_link_libraries(consumer PRIVATE greetf::libgreetf)
add_test(NAME consumer COMMAND consumer)
