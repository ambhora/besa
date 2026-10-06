# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
set(_manifest "${BINARY_DIR}/cpdocs-manifest.json")
if(NOT EXISTS "${_manifest}")
  message(FATAL_ERROR "missing ${_manifest}")
endif()
file(READ "${_manifest}" _json)
string(JSON _count LENGTH "${_json}" units)
if(NOT _count EQUAL 1)
  message(FATAL_ERROR "expected one selected unit:\n${_json}")
endif()
string(JSON _type GET "${_json}" units 0 type)
string(JSON _language GET "${_json}" units 0 language)
string(JSON _parser_language GET "${_json}" units 0 parse language)
if(NOT _type STREQUAL "cpp" OR NOT _language STREQUAL "cpp" OR NOT _parser_language STREQUAL "cpp")
  message(FATAL_ERROR "feature 'gpu' did not independently resolve to the declared C++ language:\n${_json}")
endif()

# The manifest describes this build only; feature-set availability is tracked by cpdocs from the
# feature-set object it supplied, not duplicated into the manifest.
string(FIND "${_json}" "\"features\"" _features_position)
if(NOT _features_position EQUAL -1)
  message(FATAL_ERROR "cpdocs manifest must not duplicate the selected feature set:\n${_json}")
endif()
