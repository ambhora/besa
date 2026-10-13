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

set(CMAKE_CXX_STANDARD 20)
# The user chooses instrumentation only through BUILD_DEVTOOLS. Besa resolves the
# selected tools in cmake/options.cmake; no second sanitizer selector is needed.
foreach(_sanitizer IN ITEMS asan ubsan)
  besa_devtools_check(OUTPUT_VARIABLE _enabled DEVTOOLS "${_sanitizer}")
  if(_enabled)
    besa_test_add_directory(NAME "${_sanitizer}" PREFIX sanitizers)
  endif()
endforeach()

# Verify that only tests for the actually enabled instrumentation have been registered.
besa_devtools_check(OUTPUT_VARIABLE _asan_selected DEVTOOLS asan)
besa_devtools_check(OUTPUT_VARIABLE _ubsan_selected DEVTOOLS ubsan)
if(_asan_selected AND NOT TEST sanitizers.overflow.fail.t)
  message(FATAL_ERROR "asan selected but its test was not registered")
elseif(NOT _asan_selected AND TEST sanitizers.overflow.fail.t)
  message(FATAL_ERROR "asan test registered without selecting asan")
endif()
if(_ubsan_selected AND NOT TEST sanitizers.shift.fail.t)
  message(FATAL_ERROR "ubsan selected but its test was not registered")
elseif(NOT _ubsan_selected AND TEST sanitizers.shift.fail.t)
  message(FATAL_ERROR "ubsan test registered without selecting ubsan")
endif()
