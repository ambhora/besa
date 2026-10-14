# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
# Test-only assertions for the feature-space example. Keeping them here makes CMakeLists.txt a useful
# copyable example of the public BESA API.
function(_besa_test_features)
  set(ACTUAL_FEATURES ${BESA_ENABLED_FEATURES})
  list(SORT ACTUAL_FEATURES)
  set(EXPECTED_FEATURES ${PROJECT_FEATURE})
  list(SORT EXPECTED_FEATURES)
  if(NOT ACTUAL_FEATURES STREQUAL EXPECTED_FEATURES)
    message(FATAL_ERROR "enabled features are '${ACTUAL_FEATURES}', expected '${EXPECTED_FEATURES}'")
  endif()

  get_property(UNIT_COUNT GLOBAL PROPERTY BESA_MANIFEST_UNIT_COUNT)
  if(NOT UNIT_COUNT EQUAL 1)
    message(FATAL_ERROR "expected exactly one implementation unit, got ${UNIT_COUNT}")
  endif()
  get_property(ACTUAL_UNIT GLOBAL PROPERTY BESA_MANIFEST_UNIT_0_ID)
  if("alpha" IN_LIST EXPECTED_FEATURES)
    set(EXPECTED_UNIT alpha)
  else()
    set(EXPECTED_UNIT beta)
  endif()
  if(NOT ACTUAL_UNIT STREQUAL EXPECTED_UNIT)
    message(FATAL_ERROR "selected unit is '${ACTUAL_UNIT}', expected '${EXPECTED_UNIT}'")
  endif()
endfunction()
cmake_language(DEFER CALL _besa_test_features)
