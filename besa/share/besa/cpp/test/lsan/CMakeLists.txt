# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.25)
project(besa.test.lsan LANGUAGES CXX C)
include(CTest)

find_package(besa REQUIRED COMPONENTS lsan)

add_executable(lsan.fail.t lsan.fail.t.cpp)
add_test(lsan.fail.t lsan.fail.t)
target_link_libraries(lsan.fail.t PRIVATE besa::lsan)
set_tests_properties(lsan.fail.t PROPERTIES WILL_FAIL TRUE)

add_executable(lsan.t lsan.t.cpp)
add_test(lsan.t lsan.t)
target_link_libraries(lsan.t PRIVATE besa::lsan)

