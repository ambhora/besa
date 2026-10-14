# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
cmake_minimum_required(VERSION 4.3)
project(multilib-consumer LANGUAGES CXX)
include(CTest)
find_package(multilib 1.0 CONFIG REQUIRED)
add_executable(multilib-consumer main.cpp)
target_link_libraries(multilib-consumer PRIVATE multilib::libone multilib::libtwo multilib::libheaders multilib::libdefault)
add_test(NAME multilib-consumer COMMAND multilib-consumer)

# --------------------------------------------------------------------------------------------------
# TESTING
# --------------------------------------------------------------------------------------------------
# Private libraries are buildable but must not appear in the installed package.
if(TARGET multilib::libhidden)
  message(FATAL_ERROR "Build-only library unexpectedly exported")
endif()
