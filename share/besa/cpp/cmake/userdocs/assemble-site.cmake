# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Assemble the canonical publication tree. ProperDocs owns the root; the Sphinx/Breathe API output
# is mounted below API_PATH as a separate versioned documentation surface.

foreach(_required PROPERDOCS_DIRECTORY API_DIRECTORY OUTPUT_DIRECTORY API_PATH)
  if(NOT DEFINED ${_required} OR "${${_required}}" STREQUAL "")
    message(FATAL_ERROR "assemble-site: ${_required} is required")
  endif()
endforeach()

if(NOT EXISTS "${PROPERDOCS_DIRECTORY}/index.html")
  message(FATAL_ERROR "assemble-site: ProperDocs output is missing ${PROPERDOCS_DIRECTORY}/index.html")
endif()
if(NOT EXISTS "${API_DIRECTORY}/versions.json")
  message(FATAL_ERROR "assemble-site: API metadata is missing ${API_DIRECTORY}/versions.json")
endif()

file(REMOVE_RECURSE "${OUTPUT_DIRECTORY}")
file(MAKE_DIRECTORY "${OUTPUT_DIRECTORY}")
file(COPY "${PROPERDOCS_DIRECTORY}/" DESTINATION "${OUTPUT_DIRECTORY}")

set(_besa_api_destination "${OUTPUT_DIRECTORY}/${API_PATH}")
file(MAKE_DIRECTORY "${_besa_api_destination}")
file(COPY "${API_DIRECTORY}/" DESTINATION "${_besa_api_destination}")

# Disable Jekyll for the entire assembled site so Sphinx's underscore-prefixed static directories are
# served correctly when the tree is uploaded to GitHub Pages.
file(WRITE "${OUTPUT_DIRECTORY}/.nojekyll" "")
