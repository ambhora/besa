# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 besa developers
# --------------------------------------------------------------------------------------------------
execute_process(
  COMMAND "${CMAKE_COMMAND}" --build "${BINARY_DIR}" --target besa.cpdocs
  RESULT_VARIABLE CPDOCS_RESULT
  OUTPUT_VARIABLE CPDOCS_OUTPUT
  ERROR_VARIABLE CPDOCS_OUTPUT
)
if(NOT CPDOCS_RESULT EQUAL 0)
  message(FATAL_ERROR "besa.cpdocs target failed:\n${CPDOCS_OUTPUT}")
endif()
if(NOT EXISTS "${BINARY_DIR}/besa/subdirectories/schema/codegen.stamp")
  message(FATAL_ERROR "besa.cpdocs did not run the registered code generator")
endif()
if(NOT EXISTS "${BINARY_DIR}/cpdocs-manifest.json")
  message(FATAL_ERROR "besa.cpdocs manifest was not written")
endif()

set(MANIFEST_PATH "${BINARY_DIR}/besa/manifest.json")
file(READ "${MANIFEST_PATH}" MANIFEST_JSON)
string(JSON UNIT_COUNT LENGTH "${MANIFEST_JSON}" units)
if(NOT UNIT_COUNT EQUAL 1)
  message(FATAL_ERROR "expected one generated unit:\n${MANIFEST_JSON}")
endif()
string(JSON UNIT_TYPE GET "${MANIFEST_JSON}" units 0 type)
string(JSON UNIT_SOURCE_TYPE GET "${MANIFEST_JSON}" units 0 source-type)
string(JSON UNIT_GENERATED GET "${MANIFEST_JSON}" units 0 generated)
string(JSON UNIT_LANGUAGE GET "${MANIFEST_JSON}" units 0 language)
string(JSON UNIT_PARSER_LANGUAGE GET "${MANIFEST_JSON}" units 0 parse language)
if(NOT UNIT_TYPE STREQUAL "cpp" OR NOT UNIT_SOURCE_TYPE STREQUAL "jnum" OR NOT UNIT_GENERATED
    OR NOT UNIT_LANGUAGE STREQUAL "cpp" OR NOT UNIT_PARSER_LANGUAGE STREQUAL "cpp")
  message(FATAL_ERROR "unexpected generated unit:\n${MANIFEST_JSON}")
endif()
