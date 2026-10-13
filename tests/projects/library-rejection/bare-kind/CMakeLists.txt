# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
cmake_minimum_required(VERSION 4.3)
project(library-rejection VERSION 1.0.0 LANGUAGES NONE)
find_package(besa CONFIG REQUIRED)
besa_finalize_options()

besa_add_library(NAME libbare STATIC INSTALL NO)
