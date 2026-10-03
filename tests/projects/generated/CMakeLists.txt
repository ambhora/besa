# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# A custom generated type resolves to the built-in cpp layout. BESA owns the output prefix and the
# shared codegen target; the generator only describes how to populate it.
cmake_minimum_required(VERSION 3.25)
project(generated VERSION 0.4.0 LANGUAGES NONE)
find_package(besa CONFIG REQUIRED)

include(jnum.cmake)
besa_register_subdirectory_type(
  jnum
  FUNCTION jnum_add_subdirectory
  RESOLVES_TO cpp
  GENERATED
)

besa_configure_complete()
besa_add_subdirectory(DIRECTORY schema TYPE jnum ARGS LINK_TYPE STATIC)
