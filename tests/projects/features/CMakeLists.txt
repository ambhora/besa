# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Feature spaces are finite and enumerable. Feature names describe project capabilities; they are
# intentionally independent of source languages such as C++, CUDA, or HIP.
cmake_minimum_required(VERSION 4.3)
project(features VERSION 1.0.0 LANGUAGES NONE)
find_package(besa CONFIG REQUIRED)

include(cmake/options.cmake)

besa_add_library(NAME libfeatures TYPE STATIC INSTALL YES)
besa_add_directory(LIBRARY libfeatures ROOT alpha TYPE cpp CONDITION alpha)
besa_add_directory(LIBRARY libfeatures ROOT beta TYPE cpp CONDITION beta)

# cpdocs is additive: requesting metadata must not suppress normal targets.
if(BESA_CPDOCS_FEATURE_SETS_OUTPUT AND NOT TARGET libfeatures)
  message(FATAL_ERROR "cpdocs feature-set export suppressed normal target 'libfeatures'")
endif()
