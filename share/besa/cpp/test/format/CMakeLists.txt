# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.25)
project(besa.test.format LANGUAGES CXX C)
include(CTest)

find_package(besa REQUIRED COMPONENTS format)

besa_add_clang_format(test.format)
