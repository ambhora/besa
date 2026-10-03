# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Each sanitizer test is expected to fail at run time, which only happens when the instrumentation
# requested through PROJECT_DEVTOOLS is applied.
cmake_minimum_required(VERSION 3.25)
project(sanitizers VERSION 1.0.0 LANGUAGES CXX)
include(CTest)
find_package(besa CONFIG REQUIRED)

besa_configure_complete()

set(CMAKE_CXX_STANDARD 20)
besa_test_add_directory(NAME "${SANITIZER}" PREFIX sanitizers)
