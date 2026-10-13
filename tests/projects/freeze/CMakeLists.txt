# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
cmake_minimum_required(VERSION 4.3)
project(freeze VERSION 1.0.0 LANGUAGES NONE)
find_package(besa CONFIG REQUIRED)
include(cmake/options.cmake)
besa_add_feature(late)
