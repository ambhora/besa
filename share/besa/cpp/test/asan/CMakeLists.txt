# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.25)
project(besa.test.asan LANGUAGES CXX C)
include(CTest)

find_package(besa REQUIRED COMPONENTS asan)

add_executable(asan.fail.t asan.fail.t.cpp)
add_test(asan.fail.t asan.fail.t)
target_link_libraries(asan.fail.t PRIVATE besa::asan)
set_tests_properties(asan.fail.t PROPERTIES WILL_FAIL TRUE)

add_executable(asan.t asan.t.cpp)
add_test(asan.t asan.t)
target_link_libraries(asan.t PRIVATE besa::asan)

