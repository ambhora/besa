# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.25)
project(compile)
include(CTest)

find_package(besa REQUIRED COMPONENTS test)

besa_compile_test_directory(
  DIRECTORY test
  TARGET_LIST ""
  PREFIX "compile"
  LABELS ""
  )

add_test(
  NAME compile
  COMMAND ${CMAKE_COMMAND} -E echo "Compile tests passed."
  )
