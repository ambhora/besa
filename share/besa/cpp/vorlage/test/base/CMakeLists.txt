# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Project-local test support.  This library is intentionally not installed.  It provides the
# reusable Prova data/command-line helpers and the Catch2 runner used by tests that supply their own
# main function.

besa_add_library(
  NAME libtestvorlage
  TYPE STATIC
  INSTALL FALSE
  SOURCES
    cpp/lib/testvorlage/prova/cmdline.cpp
    cpp/lib/testvorlage/prova/data.cpp
    cpp/lib/testvorlage/prova/detail/runner.cpp
  PUBLIC_INCLUDE_DIRECTORIES
    "${CMAKE_CURRENT_SOURCE_DIR}/cpp/include"
  LINK_LIBRARIES
    vorlage::libvorlage
    Catch2::Catch2
)
