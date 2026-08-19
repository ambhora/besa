# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.25)
project(besa.test.ubsan LANGUAGES CXX C)
include(CTest)

find_package(besa REQUIRED COMPONENTS ubsan)

add_executable(ubsan.fail.t ubsan.fail.t.cpp)
add_test(ubsan.fail.t ubsan.fail.t)
target_link_libraries(ubsan.fail.t PRIVATE besa::ubsan)
set_tests_properties(ubsan.fail.t PROPERTIES WILL_FAIL TRUE)

add_executable(ubsan.t ubsan.t.cpp)
add_test(ubsan.t ubsan.t)
target_link_libraries(ubsan.t PRIVATE besa::ubsan)

