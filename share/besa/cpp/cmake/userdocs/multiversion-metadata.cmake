# --------------------------------------------------------------------------------------------------
# SPDX-License-Identifier: Apache-2.0
# --------------------------------------------------------------------------------------------------
# Generate machine-readable API-version metadata next to the sphinx-multiversion output.  ProperDocs
# owns reference/api/index.html; this script therefore deliberately does not create an HTML landing
# page at the multiversion root.

if(NOT DEFINED OUTPUT_DIRECTORY OR "${OUTPUT_DIRECTORY}" STREQUAL "")
  message(FATAL_ERROR "multiversion-metadata: OUTPUT_DIRECTORY is required")
endif()
if(NOT DEFINED DEFAULT_VERSION OR "${DEFAULT_VERSION}" STREQUAL "")
  set(DEFAULT_VERSION "main")
endif()

# A version root is identified by the Sphinx _static directory rather than by recursively finding
# index.html. The latter would incorrectly classify nested pages named index.rst as API versions.
# This also supports branch names containing '/', because the _static marker is relative to the
# actual Sphinx site root no matter how deeply the ref name nests the output directory.
file(
  GLOB_RECURSE _besa_static_directories
  LIST_DIRECTORIES TRUE
  RELATIVE "${OUTPUT_DIRECTORY}"
  "${OUTPUT_DIRECTORY}/*/_static"
)
set(_besa_versions "")
foreach(_besa_static IN LISTS _besa_static_directories)
  if(_besa_static MATCHES "(^|/)_static$" AND IS_DIRECTORY "${OUTPUT_DIRECTORY}/${_besa_static}")
    string(REGEX REPLACE "/_static$" "" _besa_version "${_besa_static}")
    if(EXISTS "${OUTPUT_DIRECTORY}/${_besa_version}/index.html")
      list(APPEND _besa_versions "${_besa_version}")
    endif()
  endif()
endforeach()
list(REMOVE_DUPLICATES _besa_versions)
list(SORT _besa_versions COMPARE NATURAL ORDER DESCENDING)

# Put the configured default first when it was actually generated. Avoid IN_LIST here because this
# file also runs in standalone `cmake -P` script mode, where no project() call has initialized policy
# CMP0057.
list(FIND _besa_versions "${DEFAULT_VERSION}" _besa_default_index)
if(NOT _besa_default_index EQUAL -1)
  list(REMOVE_ITEM _besa_versions "${DEFAULT_VERSION}")
  list(PREPEND _besa_versions "${DEFAULT_VERSION}")
endif()

function(_besa_json_escape INPUT OUTPUT_VARIABLE)
  set(_value "${INPUT}")
  string(REPLACE "\\" "\\\\" _value "${_value}")
  string(REPLACE "\"" "\\\"" _value "${_value}")
  set("${OUTPUT_VARIABLE}" "${_value}" PARENT_SCOPE)
endfunction()

_besa_json_escape("${DEFAULT_VERSION}" _besa_default_json)
set(_besa_json "{\n  \"default\": \"${_besa_default_json}\",\n  \"versions\": [")
set(_besa_separator "")
foreach(_besa_version IN LISTS _besa_versions)
  _besa_json_escape("${_besa_version}" _besa_name_json)
  _besa_json_escape("${_besa_version}/" _besa_url_json)

  file(
    GLOB_RECURSE _besa_html_pages
    LIST_DIRECTORIES FALSE
    RELATIVE "${OUTPUT_DIRECTORY}/${_besa_version}"
    "${OUTPUT_DIRECTORY}/${_besa_version}/*.html"
  )
  list(SORT _besa_html_pages)
  set(_besa_pages_json "[")
  set(_besa_page_separator "")
  foreach(_besa_page IN LISTS _besa_html_pages)
    _besa_json_escape("${_besa_page}" _besa_page_json)
    string(APPEND _besa_pages_json "${_besa_page_separator}\"${_besa_page_json}\"")
    set(_besa_page_separator ", ")
  endforeach()
  string(APPEND _besa_pages_json "]")

  string(
    APPEND _besa_json
    "${_besa_separator}\n    {\"name\": \"${_besa_name_json}\", \"url\": \"${_besa_url_json}\", \"pages\": ${_besa_pages_json}}"
  )
  set(_besa_separator ",")
endforeach()
if(_besa_versions)
  string(APPEND _besa_json "\n  ")
endif()
string(APPEND _besa_json "]\n}\n")
file(WRITE "${OUTPUT_DIRECTORY}/versions.json" "${_besa_json}")
