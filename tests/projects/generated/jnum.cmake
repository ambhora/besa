# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Example implementation of a generated BESA subdirectory type. The project only registers this
# function and then uses TYPE jnum like any built-in type.
function(jnum_add_subdirectory)
  cmake_parse_arguments(
    ARG "" "SOURCE_DIR;BUILD_DIR;OUTPUT_DIR;OUTPUT_TARGET_VARIABLE;LINK_TYPE" "" ${ARGN}
  )

  file(MAKE_DIRECTORY "${ARG_OUTPUT_DIR}/include/generated" "${ARG_OUTPUT_DIR}/lib")
  file(WRITE "${ARG_OUTPUT_DIR}/include/generated/table.hpp"
    "#pragma once\nnamespace generated { int answer(); constexpr int late = 42; }\n"
  )
  file(WRITE "${ARG_OUTPUT_DIR}/lib/table.cpp"
    "#include <generated/table.hpp>\nnamespace generated { int answer() { return 42; } }\n"
  )

  file(WRITE "${ARG_BUILD_DIR}/codegen.stamp.in" "generated\n")
  add_custom_command(
    OUTPUT "${ARG_BUILD_DIR}/codegen.stamp"
    COMMAND "${CMAKE_COMMAND}" -E copy
      "${ARG_BUILD_DIR}/codegen.stamp.in" "${ARG_BUILD_DIR}/codegen.stamp"
    DEPENDS "${ARG_SOURCE_DIR}/input.jnum"
    VERBATIM
  )
  add_custom_target(jnum.generate DEPENDS "${ARG_BUILD_DIR}/codegen.stamp")
  set("${ARG_OUTPUT_TARGET_VARIABLE}" jnum.generate PARENT_SCOPE)
endfunction()
