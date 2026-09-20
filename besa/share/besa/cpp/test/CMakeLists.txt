# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------

function(testbesa_add_test NAME)
  set(options WILL_FAIL)
  set(one_value_args DIRECTORY PRESET)
  set(multi_value_args LABELS)

  cmake_parse_arguments(
    ARG
    "${options}"
    "${one_value_args}"
    "${multi_value_args}"
    ${ARGN}
  )

  if(NOT ARG_DIRECTORY)
    set(ARG_DIRECTORY "${NAME}")
  endif()

  if(NOT ARG_PRESET)
    set(ARG_PRESET "default")
  endif()

  add_test(
    NAME "${NAME}"
    COMMAND
      "${CMAKE_COMMAND}" -E env
      --unset=CMAKE_PREFIX_PATH
      "BESA_TEST_BUILD_DIR=${PROJECT_BINARY_DIR}/${NAME}"
      "BESA_TEST_CMAKE_PREFIX_PATH=${CMAKE_PREFIX_PATH}"
      "BESA_TEST_CMAKE_C_COMPILER=${CMAKE_C_COMPILER}"
      "BESA_TEST_CMAKE_CXX_COMPILER=${CMAKE_CXX_COMPILER}"
      --
      "${CMAKE_COMMAND}"
      --workflow
      --preset "${ARG_PRESET}"
      --fresh
    WORKING_DIRECTORY "${CMAKE_CURRENT_LIST_DIR}/${ARG_DIRECTORY}"
  )

  if(ARG_LABELS)
    set_tests_properties(
      "${NAME}"
      PROPERTIES LABELS "${ARG_LABELS}"
    )
  endif()

  if(ARG_WILL_FAIL)
    set_tests_properties(
      "${NAME}"
      PROPERTIES WILL_FAIL TRUE
    )
  endif()
endfunction()


testbesa_add_test(asan      LABELS gcc clang)
testbesa_add_test(builder   LABELS gcc clang)
testbesa_add_test(coverage  LABELS gcc clang)

testbesa_add_test(feature       LABELS gcc clang)
testbesa_add_test(feature.fail  DIRECTORY feature PRESET fail WILL_FAIL LABELS gcc clang)

testbesa_add_test(format        LABELS gcc clang)
testbesa_add_test(format.fail   WILL_FAIL LABELS gcc clang)

testbesa_add_test(testmode      LABELS gcc clang)
testbesa_add_test(testmode.fail DIRECTORY testmode PRESET fail WILL_FAIL LABELS gcc clang)

testbesa_add_test(ubsan      LABELS gcc clang)
testbesa_add_test(lsan       LABELS gcc clang)
testbesa_add_test(surrogate  LABELS gcc clang)
testbesa_add_test(unit       LABELS gcc clang)
testbesa_add_test(compile    LABELS gcc clang)

testbesa_add_test(tidy       LABELS clang)
testbesa_add_test(tidy.fail  WILL_FAIL LABELS clang)
