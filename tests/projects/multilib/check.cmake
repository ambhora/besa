# Verify that each attachment is represented in the semantic manifest.
# Manifest tracks every attached root, including roots on a single library.
file(READ "${BINARY_DIR}/besa/manifest.json" MANIFEST_JSON)
string(JSON UNIT_COUNT LENGTH "${MANIFEST_JSON}" units)
if(NOT UNIT_COUNT EQUAL 6)
  message(FATAL_ERROR "Expected 6 semantic roots; got ${UNIT_COUNT}")
endif()
