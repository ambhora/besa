# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
cmake_minimum_required(VERSION 4.3)
project(multilib VERSION 1.0.0 LANGUAGES NONE)
find_package(besa CONFIG REQUIRED)
include(cmake/options.cmake)

besa_add_library(NAME libone TYPE STATIC INSTALL YES)
besa_add_library(NAME libtwo TYPE SHARED INSTALL YES)
besa_add_library(NAME libhidden TYPE STATIC INSTALL NO)
besa_add_library(NAME libheaders TYPE INTERFACE INSTALL YES)

# With no explicit kind, use CMake's BUILD_SHARED_LIBS selection.
besa_add_library(NAME libdefault INSTALL YES)

besa_add_directory(LIBRARY libone ROOT first TYPE cpp)
besa_add_directory(LIBRARY libone ROOT extra TYPE cpp)
besa_add_directory(LIBRARY libtwo ROOT second TYPE cpp)
besa_add_directory(LIBRARY libhidden ROOT hidden TYPE cpp)
besa_add_directory(LIBRARY libheaders ROOT headers TYPE cpp)

besa_add_directory(LIBRARY libdefault ROOT default TYPE cpp)

# --------------------------------------------------------------------------------------------------
# TESTING
# --------------------------------------------------------------------------------------------------
# Verify CMake's BUILD_SHARED_LIBS choice for the library without an explicit TYPE.
# This is a fixture assertion, not part of the normal BESA library declaration.
if(BUILD_SHARED_LIBS)
  set(EXPECTED_LIBRARY_TYPE SHARED_LIBRARY)
else()
  set(EXPECTED_LIBRARY_TYPE STATIC_LIBRARY)
endif()
get_target_property(ACTUAL_LIBRARY_TYPE libdefault TYPE)
if(NOT ACTUAL_LIBRARY_TYPE STREQUAL EXPECTED_LIBRARY_TYPE)
  message(FATAL_ERROR
    "Expected ${EXPECTED_LIBRARY_TYPE} for libdefault, got ${ACTUAL_LIBRARY_TYPE}"
  )
endif()
