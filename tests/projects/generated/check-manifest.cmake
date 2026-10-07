# --------------------------------------------------------------------------------------------------
# SPDX-FileCopyrightText: 2026 BESA developers
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
execute_process(
  COMMAND "${CMAKE_COMMAND}" --build "${BINARY_DIR}" --target besa.cpdocs
  RESULT_VARIABLE _cpdocs_result
  OUTPUT_VARIABLE _cpdocs_output
  ERROR_VARIABLE _cpdocs_output
)
if(NOT _cpdocs_result EQUAL 0)
  message(FATAL_ERROR "besa.cpdocs target failed:\n${_cpdocs_output}")
endif()
if(NOT EXISTS "${BINARY_DIR}/besa/subdirectories/schema/codegen.stamp")
  message(FATAL_ERROR "besa.cpdocs did not run the registered code generator")
endif()
if(NOT EXISTS "${BINARY_DIR}/cpdocs-manifest.json")
  message(FATAL_ERROR "besa.cpdocs manifest was not written")
endif()

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
