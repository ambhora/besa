# Verify that each attachment is represented in the semantic manifest.
# Manifest tracks every attached root, including roots on a single library.
file(READ "${BINARY_DIR}/besa/manifest.json" _json)
string(JSON _count LENGTH "${_json}" units)
if(NOT _count EQUAL 6)
  message(FATAL_ERROR "Expected 6 semantic roots; got ${_count}")
endif()
