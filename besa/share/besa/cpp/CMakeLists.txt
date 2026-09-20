# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.26.1)

if(NOT DEFINED CMAKE_PREFIX_PATH AND DEFINED ENV{CMAKE_PREFIX_PATH})
  cmake_path(
    CONVERT "$ENV{CMAKE_PREFIX_PATH}"
    TO_CMAKE_PATH_LIST _cmake_prefix_path
  )
  set(CMAKE_PREFIX_PATH "${_cmake_prefix_path}" CACHE STRING "CMake prefix search path")
endif()

# Make the in-tree BESA CMake package discoverable by the nested component tests.
list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")

project(besa.cpp LANGUAGES CXX C)

include(CTest)
if(BUILD_TESTING)
  add_subdirectory(test)
endif()
