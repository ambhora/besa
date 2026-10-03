# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Test-only assertions for the feature-space example. Keeping them here makes CMakeLists.txt a useful
# copyable example of the public BESA API.
if(WRITE_CPDOCS_FEATURE_SETS)
  set(BESA_CPDOCS_FEATURE_SETS_OUTPUT "${PROJECT_BINARY_DIR}/feature-sets.json")
endif()

function(_besa_test_features)
  set(_actual ${BESA_ENABLED_FEATURES})
  list(SORT _actual)
  if(DEFINED EXPECTED_FEATURES)
    set(_expected ${EXPECTED_FEATURES})
  else()
    set(_expected alpha)
  endif()
  list(SORT _expected)
  if(NOT _actual STREQUAL _expected)
    message(FATAL_ERROR "enabled features are '${_actual}', expected '${_expected}'")
  endif()

  get_property(_unit_count GLOBAL PROPERTY BESA_MANIFEST_UNIT_COUNT)
  if(NOT _unit_count EQUAL 1)
    message(FATAL_ERROR "expected exactly one implementation unit, got ${_unit_count}")
  endif()
  get_property(_unit GLOBAL PROPERTY BESA_MANIFEST_UNIT_0_ID)
  if("alpha" IN_LIST _expected)
    set(_expected_unit alpha)
  else()
    set(_expected_unit beta)
  endif()
  if(NOT _unit STREQUAL _expected_unit)
    message(FATAL_ERROR "selected unit is '${_unit}', expected '${_expected_unit}'")
  endif()
endfunction()
cmake_language(DEFER CALL _besa_test_features)
