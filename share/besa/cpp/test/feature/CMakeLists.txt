# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.25)
project(besa.test.feature LANGUAGES CXX C)
include(CTest)

find_package(besa REQUIRED COMPONENTS feature)

set(FEATURE "feature" CACHE STRING "Feature to test")
set(FEATURE_ARRAY "feature;nofeature" CACHE STRING "Feature array to test")

besa_feature(FEATURE VALUES "${FEATURE_ARRAY}" DESCRIPTION "Feature Array")


add_test(NAME besa.test.feature COMMAND echo 0)
