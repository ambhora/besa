# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.25)
project(besa.test.coverage LANGUAGES CXX C)
include(CTest)

set(BESA_COVERAGE_ENABLED ON CACHE BOOL "Enable coverage testing")
find_package(besa REQUIRED COMPONENTS coverage)

besa_coverage_initialize_group(A)

add_executable(a.1.t a.1.t.cpp)
add_test(NAME a.1.t COMMAND a.1.t)
target_link_libraries(a.1.t PRIVATE besa::coverage)
target_include_directories(a.1.t PRIVATE ${PROJECT_SOURCE_DIR}/include)
target_sources(a.1.t PRIVATE ${CMAKE_CURRENT_LIST_DIR}/lib/math.cpp)
besa_coverage_register_test_noinit(A a.1.t a.1.t)


add_executable(a.2 a.2.t.cpp)
add_test(NAME a.2.t COMMAND a.2)
target_link_libraries(a.2 PRIVATE besa::coverage)
target_include_directories(a.2 PRIVATE ${PROJECT_SOURCE_DIR}/include)
target_sources(a.2 PRIVATE ${CMAKE_CURRENT_LIST_DIR}/lib/math.cpp)
besa_coverage_register_test_noinit(A a.2.t a.2)

