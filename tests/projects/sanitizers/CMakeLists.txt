# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Each sanitizer test is expected to fail at run time, which only happens when the instrumentation
# requested through BUILD_DEVTOOLS is applied.
cmake_minimum_required(VERSION 4.3)
project(sanitizers VERSION 1.0.0 LANGUAGES CXX)
find_package(besa CONFIG REQUIRED)

include(cmake/options.cmake)
include(CTest)

# The user chooses instrumentation only through BUILD_DEVTOOLS in cmake/options.cmake.
# Register test directories for the selected tools without another configuration selector.
foreach(DEVTOOL_NAME IN ITEMS asan ubsan)
  besa_devtools_check(OUTPUT_VARIABLE DEVTOOL_ENABLED DEVTOOLS "${DEVTOOL_NAME}")
  if(DEVTOOL_ENABLED)
    besa_test_add_directory(NAME "${DEVTOOL_NAME}" PREFIX sanitizers)
  endif()
endforeach()

# --------------------------------------------------------------------------------------------------
# TESTING
# --------------------------------------------------------------------------------------------------
# Verify that the registered tests reflect the resolved BUILD_DEVTOOLS selection.
besa_devtools_check(OUTPUT_VARIABLE ASAN_ENABLED DEVTOOLS asan)
besa_devtools_check(OUTPUT_VARIABLE UBSAN_ENABLED DEVTOOLS ubsan)
if(ASAN_ENABLED AND NOT TEST sanitizers.overflow.fail.t)
  message(FATAL_ERROR "asan selected but its test was not registered")
elseif(NOT ASAN_ENABLED AND TEST sanitizers.overflow.fail.t)
  message(FATAL_ERROR "asan test registered without selecting asan")
endif()
if(UBSAN_ENABLED AND NOT TEST sanitizers.shift.fail.t)
  message(FATAL_ERROR "ubsan selected but its test was not registered")
elseif(NOT UBSAN_ENABLED AND TEST sanitizers.shift.fail.t)
  message(FATAL_ERROR "ubsan test registered without selecting ubsan")
endif()
