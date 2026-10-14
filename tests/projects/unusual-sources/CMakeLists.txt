# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# TYPE cpp selects the language even when sources have unconventional names.
# TYPE bin never selects a language or adds an implicit library dependency.
cmake_minimum_required(VERSION 4.3)
project(unusual-sources VERSION 1.0.0 LANGUAGES NONE)
find_package(besa CONFIG REQUIRED)
include(cmake/options.cmake)

besa_add_library(NAME libodd TYPE STATIC INSTALL NO)
besa_add_directory(LIBRARY libodd ROOT unusual TYPE cpp)
besa_add_subdirectory(DIRECTORY bin TYPE bin)

# --------------------------------------------------------------------------------------------------
# TESTING
# --------------------------------------------------------------------------------------------------
# Verify the two independent executable/library targets were created.
if(NOT TARGET standalone OR NOT TARGET libodd)
  message(FATAL_ERROR "Expected independent standalone and libodd targets")
endif()
