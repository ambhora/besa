# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
cmake_minimum_required(VERSION 4.3)
project(sanitizers-invalid VERSION 1.0.0 LANGUAGES NONE)
find_package(besa CONFIG REQUIRED)
include(cmake/options.cmake)
besa_test_add_directory(NAME tests DEVTOOLS not-a-devtool)
