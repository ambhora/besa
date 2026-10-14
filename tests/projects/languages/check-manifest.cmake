# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
set(MANIFEST_PATH "${BINARY_DIR}/cpdocs-manifest.json")
if(NOT EXISTS "${MANIFEST_PATH}")
  message(FATAL_ERROR "missing ${MANIFEST_PATH}")
endif()
file(READ "${MANIFEST_PATH}" MANIFEST_JSON)
string(JSON UNIT_COUNT LENGTH "${MANIFEST_JSON}" units)
if(NOT UNIT_COUNT EQUAL 1)
  message(FATAL_ERROR "expected one selected unit:\n${MANIFEST_JSON}")
endif()
string(JSON UNIT_TYPE GET "${MANIFEST_JSON}" units 0 type)
string(JSON UNIT_LANGUAGE GET "${MANIFEST_JSON}" units 0 language)
string(JSON UNIT_PARSER_LANGUAGE GET "${MANIFEST_JSON}" units 0 parse language)
if(NOT UNIT_TYPE STREQUAL "cpp" OR NOT UNIT_LANGUAGE STREQUAL "cpp" OR NOT UNIT_PARSER_LANGUAGE STREQUAL "cpp")
  message(FATAL_ERROR "feature 'gpu' did not independently resolve to the declared C++ language:\n${MANIFEST_JSON}")
endif()

# The manifest describes this build only; feature-set availability is tracked by cpdocs from the
# feature-set object it supplied, not duplicated into the manifest.
string(FIND "${MANIFEST_JSON}" "\"features\"" FEATURES_POSITION)
if(NOT FEATURES_POSITION EQUAL -1)
  message(FATAL_ERROR "cpdocs manifest must not duplicate the selected feature set:\n${MANIFEST_JSON}")
endif()
