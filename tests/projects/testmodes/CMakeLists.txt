# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Project-declared test modes select test directories through MODES.
cmake_minimum_required(VERSION 4.3)
project(testmodes VERSION 1.0.0 LANGUAGES CXX)
find_package(besa CONFIG REQUIRED)

include(cmake/options.cmake)
include(CTest)

besa_test_add_directory(NAME commit PREFIX commit MODES ci-commit ci-merge)
besa_test_add_directory(NAME merge PREFIX merge MODES ci-merge)
