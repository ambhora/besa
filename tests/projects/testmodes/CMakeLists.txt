# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Project-declared test modes select test directories through MODES.
cmake_minimum_required(VERSION 3.25)
project(testmodes VERSION 1.0.0 LANGUAGES CXX)
include(CTest)
find_package(besa CONFIG REQUIRED)

besa_test_modes_add(MODES ci-commit ci-merge)
besa_test_modes_default(MODES ci-commit)
besa_configure_complete()

besa_test_add_directory(NAME commit PREFIX commit MODES ci-commit ci-merge)
besa_test_add_directory(NAME merge PREFIX merge MODES ci-merge)
