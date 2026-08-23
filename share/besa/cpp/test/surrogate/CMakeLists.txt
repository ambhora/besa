# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.25)
project(besa.test.surrogate LANGUAGES CXX C)
include(CTest)

find_package(besa REQUIRED COMPONENTS surrogate)

add_library(goodlib)
target_sources(goodlib PUBLIC lib/main.cpp)
target_include_directories(goodlib PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_LIST_DIR}/goodlib>)

add_library(badlib)
target_sources(badlib PUBLIC lib/main.cpp)
target_include_directories(badlib PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_LIST_DIR}/badlib>)

besa_surrogate_check(goodlib all PASS)
besa_surrogate_check(badlib all FAIL)
