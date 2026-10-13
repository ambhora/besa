# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
cmake_minimum_required(VERSION 4.3)
project(multilib VERSION 1.0.0 LANGUAGES NONE)
find_package(besa CONFIG REQUIRED)
besa_configure_complete()

if(TEST_CONFLICTING_LIBRARY_KINDS)
  besa_add_library(NAME libconflict STATIC SHARED INSTALL NO)
endif()
if(TEST_LEGACY_LIBRARY_KIND)
  besa_add_library(NAME liblegacy TYPE STATIC INSTALL NO)
endif()
if(TEST_IMPLICIT_LIBRARY_CREATION)
  besa_add_subdirectory(DIRECTORY first TYPE cpp)
endif()

besa_add_library(NAME libone STATIC INSTALL YES)
besa_add_library(NAME libtwo SHARED INSTALL YES)
besa_add_library(NAME libhidden STATIC INSTALL NO)
besa_add_library(NAME libheaders INTERFACE INSTALL YES)

# With no explicit kind, use CMake's BUILD_SHARED_LIBS selection.
besa_add_library(NAME libdefault INSTALL YES)
if(BUILD_SHARED_LIBS)
  set(_expected_kind SHARED_LIBRARY)
else()
  set(_expected_kind STATIC_LIBRARY)
endif()
get_target_property(_actual_kind libdefault TYPE)
if(NOT _actual_kind STREQUAL _expected_kind)
  message(FATAL_ERROR "Expected ${_expected_kind} for default library, got ${_actual_kind}")
endif()

besa_add_directory(LIBRARY libone ROOT first TYPE cpp)
besa_add_directory(LIBRARY libone ROOT extra TYPE cpp)
besa_add_directory(LIBRARY libtwo ROOT second TYPE cpp)
besa_add_directory(LIBRARY libhidden ROOT hidden TYPE cpp)
besa_add_directory(LIBRARY libheaders ROOT headers TYPE cpp)

besa_add_directory(LIBRARY libdefault ROOT default TYPE cpp)
