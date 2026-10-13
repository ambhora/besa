# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# A feature selects project topology; TYPE independently states the language of the selected unit.
cmake_minimum_required(VERSION 4.3)
project(languages VERSION 1.0.0 LANGUAGES NONE)
find_package(besa CONFIG REQUIRED)

include(cmake/options.cmake)

besa_add_library(NAME liblanguages TYPE STATIC INSTALL YES)
besa_add_directory(LIBRARY liblanguages ROOT host TYPE cpp CONDITION host)
besa_add_directory(LIBRARY liblanguages ROOT device TYPE cpp CONDITION gpu)
