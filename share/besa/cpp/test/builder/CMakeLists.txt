# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.25)
project(besa.test.builder LANGUAGES CXX)
include(CTest)

find_package(besa REQUIRED COMPONENTS builder)

add_library(besa.test.builder)

besa_target_header_directory(besa.test.builder PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
besa_target_source_directory(besa.test.builder PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/lib)

add_executable(builder.t builder.t.cpp)
add_test(builder.t builder.t)
target_link_libraries(builder.t PRIVATE besa.test.builder)

