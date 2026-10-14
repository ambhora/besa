# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
set(FEATURE_SETS_PATH "${BINARY_DIR}/feature-sets.json")
if(NOT EXISTS "${FEATURE_SETS_PATH}")
  message(FATAL_ERROR "missing ${FEATURE_SETS_PATH}")
endif()
file(READ "${FEATURE_SETS_PATH}" FEATURE_SETS_JSON)

string(JSON GENERATOR_NAME GET "${FEATURE_SETS_JSON}" generator)
if(NOT GENERATOR_NAME STREQUAL "besa")
  message(FATAL_ERROR "expected generator 'besa', got '${GENERATOR_NAME}':\n${FEATURE_SETS_JSON}")
endif()

string(JSON PROJECT_NAME_IN_FILE GET "${FEATURE_SETS_JSON}" project name)
if(NOT PROJECT_NAME_IN_FILE STREQUAL "features")
  message(FATAL_ERROR "expected project name 'features', got '${PROJECT_NAME_IN_FILE}':\n${FEATURE_SETS_JSON}")
endif()

string(JSON PROJECT_VERSION_IN_FILE GET "${FEATURE_SETS_JSON}" project version)
if(NOT PROJECT_VERSION_IN_FILE STREQUAL "1.0.0")
  message(FATAL_ERROR "expected project version '1.0.0', got '${PROJECT_VERSION_IN_FILE}':\n${FEATURE_SETS_JSON}")
endif()
string(JSON FEATURE_SET_COUNT LENGTH "${FEATURE_SETS_JSON}" feature-sets)
if(NOT FEATURE_SET_COUNT EQUAL 8)
  message(FATAL_ERROR "expected 8 feature sets, got ${FEATURE_SET_COUNT}:\n${FEATURE_SETS_JSON}")
endif()

# Concrete feature sets are deliberately unnamed. Each row is just the features in that build.
math(EXPR LAST_FEATURE_SET_INDEX "${FEATURE_SET_COUNT} - 1")
foreach(FEATURE_SET_INDEX RANGE 0 ${LAST_FEATURE_SET_INDEX})
  string(JSON FEATURE_SET_ENTRY GET "${FEATURE_SETS_JSON}" feature-sets ${FEATURE_SET_INDEX})
  string(FIND "${FEATURE_SET_ENTRY}" "\"name\"" NAME_POSITION)
  if(NOT NAME_POSITION EQUAL -1)
    message(FATAL_ERROR "feature sets must not have synthetic names:\n${FEATURE_SET_ENTRY}")
  endif()

  string(JSON FEATURE_COUNT LENGTH "${FEATURE_SETS_JSON}" feature-sets ${FEATURE_SET_INDEX} features)
  set(IMPLEMENTATION_COUNT 0)
  if(FEATURE_COUNT GREATER 0)
    math(EXPR LAST_FEATURE_INDEX "${FEATURE_COUNT} - 1")
    foreach(FEATURE_INDEX RANGE 0 ${LAST_FEATURE_INDEX})
      string(JSON FEATURE_NAME GET "${FEATURE_SETS_JSON}" feature-sets ${FEATURE_SET_INDEX} features ${FEATURE_INDEX})
      if(FEATURE_NAME MATCHES "^(alpha|beta)$")
        math(EXPR IMPLEMENTATION_COUNT "${IMPLEMENTATION_COUNT} + 1")
      endif()
    endforeach()
  endif()
  if(NOT IMPLEMENTATION_COUNT EQUAL 1)
    message(FATAL_ERROR "feature set must contain exactly one implementation:\n${FEATURE_SETS_JSON}")
  endif()
endforeach()
