# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
set(_manifest "${BINARY_DIR}/besa/manifest.json")
file(READ "${_manifest}" _json)
string(JSON _count LENGTH "${_json}" units)
if(NOT _count EQUAL 1)
  message(FATAL_ERROR "expected one generated unit:\n${_json}")
endif()
string(JSON _type GET "${_json}" units 0 type)
string(JSON _source_type GET "${_json}" units 0 source-type)
string(JSON _generated GET "${_json}" units 0 generated)
string(JSON _language GET "${_json}" units 0 language)
string(JSON _parser_language GET "${_json}" units 0 parse language)
if(NOT _type STREQUAL "cpp" OR NOT _source_type STREQUAL "jnum" OR NOT _generated
    OR NOT _language STREQUAL "cpp" OR NOT _parser_language STREQUAL "cpp")
  message(FATAL_ERROR "unexpected generated unit:\n${_json}")
endif()
