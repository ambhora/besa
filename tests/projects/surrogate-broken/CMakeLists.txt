# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
cmake_minimum_required(VERSION 4.3)
project(surrogate-broken VERSION 1.0.0 LANGUAGES CXX)
find_package(besa CONFIG REQUIRED)
include(cmake/options.cmake)
include(CTest)
besa_add_library(NAME liboops TYPE STATIC INSTALL NO)
target_include_directories(liboops PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}/../surrogate/oops")
target_sources(liboops PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/../surrogate/oops.cpp")
